"""ADOS-M3.3 — brand/llm/narrative/validation.py."""

from __future__ import annotations

from brand.llm.content.model import (
    ContentIntelligenceModel,
    Fact,
    SourceReference,
)
from brand.llm.content.vocabulary import FactStatus, SourceType
from brand.llm.narrative.model import (
    ContentReferenceSet,
    GeneratedClaim,
    NarrativeExclusion,
    NarrativeIssue,
    NarrativePlan,
    NarrativeSection,
    NarrativeThesis,
)
from brand.llm.narrative.validation import validate_narrative_plan
from brand.llm.narrative.vocabulary import (
    Audience,
    ExclusionReason,
    NarrativeIssueType,
    NarrativeObjective,
    Relevance,
    Requirement,
    SectionRole,
)

_REF = SourceReference(source_id="s1", source_type=SourceType.PROJECT_METADATA, extraction_method="structured_data")


def _fact(key="apartments", value=84, status=FactStatus.VERIFIED, **kw) -> Fact:
    return Fact(key=key, value=value, status=status, source_refs=(_REF,), **kw)


def _content(**kw) -> ContentIntelligenceModel:
    kw.setdefault("project_id", "p1")
    return ContentIntelligenceModel(**kw)


def _section(**kw) -> NarrativeSection:
    kw.setdefault("role", SectionRole.CONTEXT)
    kw.setdefault("purpose", "explain the site condition, in enough detail to matter")
    kw.setdefault("sequence", 0)
    return NarrativeSection(**kw)


def _plan(**kw) -> NarrativePlan:
    kw.setdefault("project_id", "p1")
    kw.setdefault("objective", NarrativeObjective.INTRODUCE)
    kw.setdefault("audience", Audience.CLIENT)
    return NarrativePlan(**kw)


def test_valid_plan_has_no_blocking_findings():
    fact = _fact()
    content = _content(facts=(fact,))
    section = _section(content_refs=ContentReferenceSet(fact_ids=(fact.id,)))
    plan = _plan(sections=(section,))
    report = validate_narrative_plan(plan, content)
    assert report.ok


def test_nar_001_duplicate_section_ids():
    content = _content()
    section = _section()
    duplicate = section.model_copy(update={"sequence": 1})
    plan = _plan(sections=(section, duplicate))
    report = validate_narrative_plan(plan, content)
    assert "NAR-001" in {f.code for f in report.findings}


def test_nar_002_duplicate_sequence_numbers():
    content = _content()
    a = _section(sequence=0)
    b = _section(sequence=0)
    plan = _plan(sections=(a, b))
    report = validate_narrative_plan(plan, content)
    assert "NAR-002" in {f.code for f in report.findings}


def test_nar_003_dangling_content_reference():
    content = _content()
    section = _section(content_refs=ContentReferenceSet(fact_ids=("does-not-exist",)))
    plan = _plan(sections=(section,))
    report = validate_narrative_plan(plan, content)
    assert "NAR-003" in {f.code for f in report.findings}
    assert not report.ok


def test_nar_004_conflicting_fact_used_without_being_flagged():
    from brand.llm.content.model import ConflictingValue

    cv1 = ConflictingValue(value=12400, unit="m2", source_refs=(_REF,))
    cv2 = ConflictingValue(value=13100, unit="m2", source_refs=(_REF,))
    conflicting = Fact(key="gfa", status=FactStatus.CONFLICTING, conflicting_values=(cv1, cv2), source_refs=(_REF,))
    content = _content(facts=(conflicting,))
    section = _section(content_refs=ContentReferenceSet(fact_ids=(conflicting.id,)))
    plan = _plan(sections=(section,))
    report = validate_narrative_plan(plan, content)
    assert "NAR-004" in {f.code for f in report.findings}


def test_nar_004_conflicting_fact_used_and_flagged_is_fine():
    from brand.llm.content.model import ConflictingValue

    cv1 = ConflictingValue(value=12400, unit="m2", source_refs=(_REF,))
    cv2 = ConflictingValue(value=13100, unit="m2", source_refs=(_REF,))
    conflicting = Fact(key="gfa", status=FactStatus.CONFLICTING, conflicting_values=(cv1, cv2), source_refs=(_REF,))
    content = _content(facts=(conflicting,))
    section = _section(content_refs=ContentReferenceSet(fact_ids=(conflicting.id,)))
    issue = NarrativeIssue(
        type=NarrativeIssueType.CONFLICTING_INFORMATION, description="gfa disagreement",
        content_refs=ContentReferenceSet(fact_ids=(conflicting.id,)), impact=Relevance.HIGH,
    )
    plan = _plan(sections=(section,), narrative_issues=(issue,))
    report = validate_narrative_plan(plan, content)
    assert "NAR-004" not in {f.code for f in report.findings}


def test_nar_006_thesis_with_no_support():
    """The model itself allows constructing a NarrativeThesis with empty
    refs (validation, not the model, enforces groundedness here, unlike
    GeneratedClaim which the model itself blocks)."""
    content = _content()
    plan = _plan(thesis=NarrativeThesis(statement="a bold claim"))
    report = validate_narrative_plan(plan, content)
    assert "NAR-006" in {f.code for f in report.findings}
    assert not report.ok


def test_nar_007_required_section_with_a_stub_purpose():
    content = _content()
    section = _section(purpose="fill", requirement=Requirement.REQUIRED)
    plan = _plan(sections=(section,))
    report = validate_narrative_plan(plan, content)
    assert "NAR-007" in {f.code for f in report.findings}


def test_nar_008_factual_role_with_no_content_refs():
    content = _content()
    section = _section(role=SectionRole.EVIDENCE, requirement=Requirement.RECOMMENDED)
    plan = _plan(sections=(section,))
    report = validate_narrative_plan(plan, content)
    assert "NAR-008" in {f.code for f in report.findings}


def test_nar_008_is_skipped_for_optional_sections():
    content = _content()
    section = _section(role=SectionRole.EVIDENCE, requirement=Requirement.OPTIONAL)
    plan = _plan(sections=(section,))
    report = validate_narrative_plan(plan, content)
    assert "NAR-008" not in {f.code for f in report.findings}


def test_exclusions_and_generated_claims_are_also_reference_checked():
    content = _content()
    exclusion = NarrativeExclusion(
        reason=ExclusionReason.UNSUPPORTED_CLAIM, description="no evidence",
        excluded_refs=ContentReferenceSet(fact_ids=("nope",)),
    )
    plan = _plan(sections=(_section(),), exclusions=(exclusion,))
    report = validate_narrative_plan(plan, content)
    assert "NAR-003" in {f.code for f in report.findings}
