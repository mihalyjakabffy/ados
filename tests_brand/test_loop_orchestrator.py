"""
ADOS-M3.6 — brand/llm/loop/orchestrator.py. Integration-level: real
Project/Document/Brand objects, the deterministic RuleBasedCommandGenerator
and RuleBasedDesignIntentGenerator path (no ANTHROPIC_API_KEY).
"""

from __future__ import annotations

import uuid

import pytest

from brand.creative.directions import get_direction
from brand.examples.studio_nord import studio_nord
from brand.llm.loop.model import Iteration, IterationPolicy
from brand.llm.loop.orchestrator import InitialInputs, resume_iteration, run_iteration, run_loop
from brand.llm.loop.vocabulary import AutonomyLevel, IterationStatus, IterationTrigger, StopReason
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.project.model import ContentItem, ContentItemKind, Document, Project


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from brand.llm.loop.observability import clear_lineages

    clear_lineages()


def _project_and_document(direction_id="editorial-quiet", text="A residential development of 84 apartments on the riverside." * 3):
    project_id = str(uuid.uuid4())
    doc = Document(
        project_id=project_id, name="Case Study", document_type_id="portfolio", direction_id=direction_id,
        content_items=(ContentItem(kind=ContentItemKind.TEXT, text=text),),
    )
    project = Project(id=project_id, name="Riverside", documents=(doc,))
    return project, doc


def _initial() -> InitialInputs:
    return InitialInputs(
        semantic_intent=SemanticIntent(explicit=SemanticFieldValues(audience="client")),
        document_type_id="portfolio",
    )


def test_first_iteration_runs_all_stages_and_persists_a_version():
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    it, new_project, new_document = run_iteration(project, doc, brand, direction, initial=_initial())
    assert it.sequence == 1
    assert it.trigger is IterationTrigger.INITIAL
    assert it.status in (IterationStatus.COMPLETED, IterationStatus.BLOCKED)
    assert it.input_design_state_version is None
    assert it.output_design_state_version == 1
    assert len(new_project.versions) == 1
    assert new_document.latest_plan is not None
    assert "planning" in it.stage_log
    assert "evaluating" in it.stage_log


def test_no_initial_inputs_on_first_iteration_fails_cleanly():
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    it, _p, _d = run_iteration(project, doc, brand, direction, initial=None)
    assert it.status is IterationStatus.FAILED
    assert it.stop_reason is StopReason.DESIGN_INVALID


def test_max_iterations_is_enforced_before_planning():
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    fake_parent = Iteration(
        project_id=project.id, document_id=doc.id, sequence=1, trigger=IterationTrigger.INITIAL,
        status=IterationStatus.COMPLETED, stop_reason=None, output_design_state_version=1,
        recommendations=(), design_intent_fingerprint="fp1",
    )
    policy = IterationPolicy(max_iterations=1)
    it, _p, _d = run_iteration(project, doc, brand, direction, lineage=(fake_parent,), policy=policy)
    assert it.status is IterationStatus.STOPPED
    assert it.stop_reason is StopReason.MAX_ITERATIONS


def test_stale_state_detected_when_parent_expects_a_different_version():
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    fake_parent = Iteration(
        project_id=project.id, document_id=doc.id, sequence=1, trigger=IterationTrigger.INITIAL,
        status=IterationStatus.COMPLETED, stop_reason=None, output_design_state_version=99,
        recommendations=(), design_intent_fingerprint="fp1",
    )
    it, _p, _d = run_iteration(project, doc, brand, direction, lineage=(fake_parent,))
    assert it.status is IterationStatus.BLOCKED
    assert it.stop_reason is StopReason.STALE_STATE


def test_continuation_with_no_recommendation_is_blocked():
    """A COMPLETED, stop_reason=None parent always carries a
    recommendation in real orchestrator flow (that is exactly what
    "keep going" means) — this exercises the defensive check for the
    case anyway, with a syntactically real, minimal NarrativePlan."""
    from brand.llm.narrative.model import NarrativePlan

    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    empty_plan = NarrativePlan(project_id=project.id, objective="introduce", audience="client")
    fake_parent = Iteration(
        project_id=project.id, document_id=doc.id, sequence=1, trigger=IterationTrigger.INITIAL,
        status=IterationStatus.COMPLETED, stop_reason=None, output_design_state_version=None,
        recommendations=(), design_intent_fingerprint="fp1", narrative_plan=empty_plan.to_dict(),
    )
    it, _p, _d = run_iteration(project, doc, brand, direction, lineage=(fake_parent,))
    assert it.status is IterationStatus.BLOCKED
    assert it.stop_reason is StopReason.NO_ACTIONABLE_RECOMMENDATION


def test_dry_run_never_persists():
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    it, new_project, new_document = run_iteration(project, doc, brand, direction, initial=_initial(), dry_run=True)
    assert it.dry_run is True
    assert it.output_design_state_version is None
    assert new_project is project
    assert new_document is doc
    assert len(new_project.versions) == 0


def test_run_loop_stops_at_a_terminal_condition_and_never_exceeds_max_iterations():
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    policy = IterationPolicy(max_iterations=3, autonomy=AutonomyLevel.SAFE, allow_llm_recommendation=False)
    iterations, new_project, _new_document = run_loop(project, doc, brand, direction, initial=_initial(), policy=policy)
    assert len(iterations) <= 3
    assert iterations[-1].stop_reason is not None
    for i, it in enumerate(iterations, start=1):
        assert it.sequence == i


def test_run_loop_result_sequences_are_a_real_lineage_with_stable_parent_links():
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    policy = IterationPolicy(max_iterations=2, allow_llm_recommendation=False)
    iterations, _p, _d = run_loop(project, doc, brand, direction, initial=_initial(), policy=policy)
    assert iterations[0].parent_iteration_id is None
    for prev, cur in zip(iterations, iterations[1:]):
        assert cur.parent_iteration_id == prev.id


def test_awaiting_approval_and_resume_completes_execution():
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)
    policy = IterationPolicy(autonomy=AutonomyLevel.NONE, allow_llm_recommendation=False)
    it, project, doc = run_iteration(project, doc, brand, direction, initial=_initial(), policy=policy)
    assert it.status is IterationStatus.AWAITING_APPROVAL
    assert it.output_design_state_version is None
    assert len(project.versions) == 0

    all_ids = frozenset(c["id"] for c in it.command_plan["commands"])
    if not all_ids:
        pytest.skip("no commands were generated for this fixture — nothing to approve")

    resumed, new_project, new_document = resume_iteration(
        project, doc, brand, direction, pending=it, lineage=(it,), approved_command_ids=all_ids,
    )
    assert resumed.status in (IterationStatus.COMPLETED, IterationStatus.BLOCKED)
    assert resumed.sequence == it.sequence
    assert resumed.output_design_state_version == 1
    assert len(new_project.versions) == 1


def test_oscillation_detected_when_a_design_intent_repeats():
    project, doc = _project_and_document()
    brand = studio_nord()
    direction = get_direction(doc.direction_id)

    it1, project, doc = run_iteration(project, doc, brand, direction, initial=_initial(),
                                       policy=IterationPolicy(allow_llm_recommendation=False))
    if not it1.recommendations:
        pytest.skip("no recommendation on iteration 1 for this fixture — nothing to oscillate on")

    # Fabricate a lineage where the *next* candidate DesignIntent would
    # repeat an earlier fingerprint by injecting a synthetic ancestor
    # carrying the same fingerprint the real patch will produce.
    from brand.llm.design.model import DesignIntent as _DesignIntent
    from brand.llm.loop.fingerprint import design_intent_fingerprint
    from brand.llm.loop.patch import apply_design_intent_patch
    from brand.llm.narrative.model import NarrativePlan

    narrative_plan = NarrativePlan.model_validate(it1.narrative_plan)
    parent_di = _DesignIntent.model_validate(it1.design_intent)
    next_di = apply_design_intent_patch(parent_di, it1.recommendations[0].patch, narrative_plan)
    next_fp = design_intent_fingerprint(next_di)

    synthetic_ancestor = Iteration(
        project_id=project.id, document_id=doc.id, sequence=0, trigger=IterationTrigger.INITIAL,
        status=IterationStatus.COMPLETED, stop_reason=None, design_intent_fingerprint=next_fp,
    )
    lineage = (synthetic_ancestor, it1)

    it2, _p, _d = run_iteration(project, doc, brand, direction, lineage=lineage,
                                 policy=IterationPolicy(allow_llm_recommendation=False))
    assert it2.status is IterationStatus.STOPPED
    assert it2.stop_reason is StopReason.OSCILLATION_DETECTED
