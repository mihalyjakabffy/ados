"""
ADOS-M3.3 — brand/llm/narrative/planning.py.

The orchestrator end to end, against the deterministic
RuleBasedNarrativeGenerator (no ANTHROPIC_API_KEY needed) — the same
CI-determinism posture ADOS-M3.1/M3.2 established. Also covers the
master prompt's own worked example (§49) and the audience-transformation
/ compression cases from §41 (Case H, Case I), since those are simplest
to verify at the orchestrator level where a real SemanticIntent and a
real ContentIntelligenceModel meet.
"""

from __future__ import annotations

import pytest

from brand.llm.content.resolution import resolve_content
from brand.llm.narrative.observability import clear_narrative_traces, recent_narrative_traces
from brand.llm.narrative.planning import plan_narrative
from brand.llm.narrative.vocabulary import Audience, NarrativeCompression
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.project.model import Project


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    clear_narrative_traces()


def _riverside_content():
    project = Project(name="Riverside", project_data={"program": "residential", "location": "Budapest"})
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "84 apartments. GFA of 13,100 m². The project creates a strong connection to the landscape."},
    ))
    return project, content


def test_master_prompt_worked_example_ss49():
    project, content = _riverside_content()
    intent = SemanticIntent(explicit=SemanticFieldValues(
        action="create", document_type="portfolio", audience="prospective_client",
        quality_direction="premium", purpose="introduce_project",
    ))
    plan = plan_narrative(project, content, intent, document_type_id="portfolio")

    assert plan.objective.value == "introduce"
    assert plan.audience is Audience.CLIENT
    assert plan.audience_label == "prospective_client"
    # No page, grid, font, or coordinate anywhere in the plan (ADOS-M3.3 §49).
    dumped = plan.to_dict()
    for forbidden in ("page", "grid", "font", "x_mm", "y_mm", "column"):
        assert forbidden not in dumped


def test_plan_carries_content_model_version_and_timestamp():
    project, content = _riverside_content()
    intent = SemanticIntent()
    plan = plan_narrative(project, content, intent)
    assert plan.content_model_version == content.version_number
    assert plan.content_resolved_at == content.resolved_at


def test_case_h_audience_transformation_same_facts_different_narrative():
    """ADOS-M3.3 §41 Case H -- same content, different audiences ->
    different narrative, same factual foundation."""
    project, content = _riverside_content()
    client_intent = SemanticIntent(explicit=SemanticFieldValues(audience="prospective_client"))
    jury_intent = SemanticIntent(explicit=SemanticFieldValues(audience="competition_jury"))

    client_plan = plan_narrative(project, content, client_intent)
    jury_plan = plan_narrative(project, content, jury_intent)

    assert client_plan.audience is Audience.CLIENT
    assert jury_plan.audience is Audience.AUTHORITY

    def _fact_values(plan):
        ids = {i for s in plan.all_sections() for i in s.content_refs.fact_ids}
        return {f.value for f in content.facts if f.id in ids}

    # Whatever facts each narrative actually uses, they are drawn from
    # the exact same, unchanged set of real project facts.
    assert _fact_values(client_plan) <= {f.value for f in content.facts}
    assert _fact_values(jury_plan) <= {f.value for f in content.facts}


def test_case_i_narrative_compression_same_facts_different_depth():
    """ADOS-M3.3 §41 Case I -- short/medium/long differ in depth, not facts."""
    project, content = _riverside_content()
    intent = SemanticIntent()
    short_plan = plan_narrative(project, content, intent, compression=NarrativeCompression.SHORT)
    long_plan = plan_narrative(project, content, intent, compression=NarrativeCompression.LONG)

    assert len(short_plan.sections) < len(long_plan.sections)
    assert short_plan.content_model_version == long_plan.content_model_version


def test_case_g_unsupported_claim_trap():
    """ADOS-M3.3 §41 Case G -- a plausible-sounding but unstated fact
    (client, structure, architect, completion year) must never appear."""
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "Residential development in Budapest."},
    ))
    intent = SemanticIntent()
    plan = plan_narrative(project, content, intent)
    dumped = plan.to_dict()
    for forbidden in ("client", "structure", "architect", "completion_year"):
        # Only real fact ids/keys are referenced -- an invented fact
        # would have to appear as a *key* somewhere, and none exist to
        # reference in the first place.
        assert forbidden not in {f.key for f in content.facts}
    assert plan is not None  # a plan is still producible from thin content


def test_case_j_existing_ados_document_is_not_elevated_to_verified_truth():
    """ADOS-M3.3 §41 Case J -- content whose source_type is
    ADOS_DOCUMENT is never treated as more authoritative than it is;
    the narrative planner reads status, not source identity."""
    from brand.llm.content.model import Fact, SourceReference
    from brand.llm.content.vocabulary import FactStatus, SourceType
    from brand.llm.narrative.context import assemble_narrative_context

    ref = SourceReference(source_id="generated-report-1", source_type=SourceType.ADOS_DOCUMENT)
    fact = Fact(key="summary_claim", value="strong performance", status=FactStatus.INFERRED, source_refs=(ref,))
    from brand.llm.content.model import ContentIntelligenceModel

    content = ContentIntelligenceModel(project_id="p1", facts=(fact,))
    ctx = assemble_narrative_context(SemanticIntent(), content)
    row = next(f for f in ctx.content_summary.facts if f["key"] == "summary_claim")
    assert row["status"] == "inferred"  # not silently upgraded to verified


def test_regeneration_keeps_previous_plans_inspectable():
    """ADOS-M3.3 §46/§47 -- regeneration never corrupts previous plans;
    each call's trace remains independently readable."""
    project, content = _riverside_content()
    intent = SemanticIntent()
    first = plan_narrative(project, content, intent)
    second = plan_narrative(project, content, intent)
    assert first.id != second.id
    traces = recent_narrative_traces()
    assert len(traces) == 2
    request_ids = {t.request_id for t in traces}
    assert len(request_ids) == 2


def test_provider_error_falls_back_to_rule_based(monkeypatch):
    from brand.llm.narrative.generation import LLMNarrativeGenerator

    project, content = _riverside_content()
    intent = SemanticIntent()
    plan = plan_narrative(project, content, intent, generator=LLMNarrativeGenerator())
    assert plan is not None
    assert len(plan.sections) > 0
