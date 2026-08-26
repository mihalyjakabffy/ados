"""
ADOS-M3.3 — brand/llm/narrative/model.py.

The domain model's own invariants: generated claims can never be
VERIFIED and can never be unsupported, a thesis is a plain optional
field (represented as None when unsupported — checked at the
validation layer, not the model), sections nest, and the plan survives
JSON round-tripping and stays meaningful with draft fields stripped.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from brand.llm.content.vocabulary import FactStatus
from brand.llm.narrative.model import (
    SCHEMA_VERSION,
    ContentReferenceSet,
    GeneratedClaim,
    NarrativeExclusion,
    NarrativeIssue,
    NarrativeMissingInformationImpact,
    NarrativePlan,
    NarrativeSection,
    NarrativeThesis,
)
from brand.llm.narrative.vocabulary import (
    Audience,
    ExclusionReason,
    MissingImpact,
    NarrativeIssueType,
    NarrativeObjective,
    Relevance,
    SectionRole,
)


def _section(**kw) -> NarrativeSection:
    kw.setdefault("role", SectionRole.CONTEXT)
    kw.setdefault("purpose", "explain the site condition")
    kw.setdefault("sequence", 0)
    return NarrativeSection(**kw)


def _plan(**kw) -> NarrativePlan:
    kw.setdefault("project_id", "p1")
    kw.setdefault("objective", NarrativeObjective.INTRODUCE)
    kw.setdefault("audience", Audience.CLIENT)
    return NarrativePlan(**kw)


def test_generated_claim_rejects_verified_status():
    with pytest.raises(ValidationError, match="can never be VERIFIED"):
        GeneratedClaim(
            text="x", status=FactStatus.VERIFIED,
            supporting_refs=ContentReferenceSet(fact_ids=("f1",)),
        )


def test_generated_claim_rejects_conflicting_or_missing_status():
    for status in (FactStatus.CONFLICTING, FactStatus.MISSING):
        with pytest.raises(ValidationError):
            GeneratedClaim(text="x", status=status, supporting_refs=ContentReferenceSet(fact_ids=("f1",)))


def test_generated_claim_rejects_empty_supporting_refs():
    with pytest.raises(ValidationError, match="must be omitted"):
        GeneratedClaim(text="x", status=FactStatus.INFERRED)


def test_generated_claim_accepts_inferred_or_ambiguous_with_refs():
    for status in (FactStatus.INFERRED, FactStatus.AMBIGUOUS):
        gc = GeneratedClaim(text="x", status=status, supporting_refs=ContentReferenceSet(claim_ids=("c1",)))
        assert gc.status is status


def test_content_reference_set_is_empty_detects_no_refs():
    assert ContentReferenceSet().is_empty
    assert not ContentReferenceSet(fact_ids=("f1",)).is_empty


def test_content_reference_set_all_ids():
    refs = ContentReferenceSet(fact_ids=("f1",), claim_ids=("c1",), asset_ids=("a1",), entity_ids=("e1",))
    assert set(refs.all_ids()) == {"f1", "c1", "a1", "e1"}


def test_sections_support_hierarchical_expansion():
    parent = _section(
        role=SectionRole.CONCEPT, sequence=0,
        subsections=(
            _section(role=SectionRole.STRATEGY, sequence=0, purpose="site strategy"),
            _section(role=SectionRole.STRATEGY, sequence=1, purpose="massing strategy"),
        ),
    )
    plan = _plan(sections=(parent,))
    assert len(plan.all_sections()) == 3
    assert plan.section(parent.subsections[0].id) is not None


def test_plan_round_trips_through_json():
    section = _section(content_refs=ContentReferenceSet(fact_ids=("f1",)))
    plan = _plan(sections=(section,))
    payload = json.loads(json.dumps(plan.to_dict()))
    rebuilt = NarrativePlan.model_validate(payload)
    assert rebuilt.project_id == plan.project_id
    assert rebuilt.sections[0].role is SectionRole.CONTEXT
    assert payload["schema_version"] == SCHEMA_VERSION


def test_plan_remains_meaningful_with_every_draft_field_deleted():
    """ADOS-M3.3 §36 — the critical architectural test."""
    section = _section(draft="Some polished sentence.", content_refs=ContentReferenceSet(fact_ids=("f1",)))
    plan = _plan(sections=(section,))
    stripped = plan.model_copy(update={
        "sections": tuple(s.model_copy(update={"draft": None}) for s in plan.sections),
    })
    assert stripped.sections[0].purpose == section.purpose
    assert stripped.sections[0].content_refs.fact_ids == ("f1",)
    assert stripped.sections[0].draft is None


def test_thesis_none_represents_unsupportable_thesis():
    plan = _plan(thesis=None)
    assert plan.thesis is None


def test_missing_information_impact_has_no_value_field():
    gap = NarrativeMissingInformationImpact(key="construction_cost", impact=MissingImpact.BLOCKING)
    assert not hasattr(gap, "value")


def test_narrative_issue_carries_content_refs():
    issue = NarrativeIssue(
        type=NarrativeIssueType.CONFLICTING_INFORMATION, description="gfa disagreement",
        content_refs=ContentReferenceSet(fact_ids=("f1",)), impact=Relevance.HIGH,
    )
    assert issue.content_refs.fact_ids == ("f1",)


def test_exclusion_carries_a_reason():
    exclusion = NarrativeExclusion(
        reason=ExclusionReason.UNSUPPORTED_CLAIM, description="no evidence for this claim",
    )
    assert exclusion.reason is ExclusionReason.UNSUPPORTED_CLAIM


def test_models_are_frozen():
    section = _section()
    with pytest.raises(ValidationError):
        section.title = "x"  # type: ignore[misc]


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        NarrativeSection.model_validate({"role": "context", "purpose": "x", "sequence": 0, "bogus": True})


def test_thesis_requires_a_statement():
    with pytest.raises(ValidationError):
        NarrativeThesis(statement="")
