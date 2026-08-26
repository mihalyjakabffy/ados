"""
ADOS-M3.3 — brand/llm/narrative/generation.py.

RuleBasedNarrativeGenerator's own shape, LLMNarrativeGenerator's error
contract (no live network call in this suite), and the structural
anti-hallucination mechanism: an id the LLM invents must never survive
materialization.
"""

from __future__ import annotations

import pytest

from brand.llm.content.resolution import resolve_content
from brand.llm.narrative.context import assemble_narrative_context
from brand.llm.narrative.generation import (
    LLMNarrativeGenerator,
    RawContentRefs,
    RawNarrativePlan,
    RawSection,
    RawThesis,
    RuleBasedNarrativeGenerator,
    _materialize,
)
from brand.llm.narrative.vocabulary import NarrativeCompression, SectionRole
from brand.llm.provider import ProviderError
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.project.model import Project


def _context(compression=NarrativeCompression.MEDIUM, document_type_id="portfolio"):
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "84 apartments. GFA of 13,100 m². The project creates a strong connection to the landscape."},
    ))
    intent = SemanticIntent(explicit=SemanticFieldValues(audience="prospective_client", purpose="introduce_project"))
    return assemble_narrative_context(intent, content, document_type_id=document_type_id, compression=compression)


def test_rule_based_generator_produces_a_plan_with_no_network_call():
    ctx = _context()
    plan, metadata = RuleBasedNarrativeGenerator().generate(ctx)
    assert metadata is None
    assert len(plan.sections) > 0
    assert plan.project_id == ctx.project_id
    assert plan.audience_label == "prospective_client"


def test_rule_based_generator_respects_compression_shape():
    # No document_type_id -- so no fixed per-type strategy overrides
    # compression (ADOS-M3.3 §22 vs. §21: these are two independent axes).
    short_plan, _ = RuleBasedNarrativeGenerator().generate(
        _context(compression=NarrativeCompression.SHORT, document_type_id=""),
    )
    long_plan, _ = RuleBasedNarrativeGenerator().generate(
        _context(compression=NarrativeCompression.LONG, document_type_id=""),
    )
    assert len(short_plan.sections) < len(long_plan.sections)


def test_rule_based_generator_flags_conflicting_facts_as_narrative_issues():
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "a.pdf", "text": "GFA of 12,400 m²."},
        {"source_id": "b.pdf", "text": "GFA of 13,100 m²."},
    ))
    intent = SemanticIntent()
    ctx = assemble_narrative_context(intent, content)
    plan, _ = RuleBasedNarrativeGenerator().generate(ctx)
    assert any(i.type.value == "conflicting_information" for i in plan.narrative_issues)
    conflicting_fact_ids = {f["id"] for f in ctx.content_summary.facts if f["status"] == "conflicting"}
    for section in plan.sections:
        assert not (set(section.content_refs.fact_ids) & conflicting_fact_ids)


def test_llm_generator_raises_provider_error_without_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(ProviderError):
        LLMNarrativeGenerator().generate(_context())


def test_llm_generator_default_model_is_opus_5(monkeypatch):
    monkeypatch.delenv("NARRATIVE_MODEL", raising=False)
    assert LLMNarrativeGenerator()._model == "claude-opus-5"


# ---------------------------------------------------------------------------
# _materialize -- the structural anti-hallucination mechanism
# ---------------------------------------------------------------------------


def test_materialize_drops_invented_ids():
    ctx = _context()
    real_fact_id = ctx.content_summary.facts[0]["id"]
    raw = RawNarrativePlan(
        objective="introduce",
        sections=(RawSection(
            role="context", purpose="explain context",
            content_refs=RawContentRefs(fact_ids=(real_fact_id, "invented-id-that-does-not-exist")),
        ),),
    )
    plan = _materialize(raw, ctx)
    assert plan.sections[0].content_refs.fact_ids == (real_fact_id,)


def test_materialize_drops_thesis_with_no_valid_support():
    ctx = _context()
    raw = RawNarrativePlan(
        objective="introduce",
        thesis=RawThesis(statement="a bold claim", supporting_refs=RawContentRefs(claim_ids=("invented",))),
        sections=(RawSection(role="context", purpose="x"),),
    )
    plan = _materialize(raw, ctx)
    assert plan.thesis is None


def test_materialize_omits_generated_claims_with_no_valid_support():
    from brand.llm.narrative.generation import RawGeneratedClaim

    ctx = _context()
    raw = RawNarrativePlan(
        objective="introduce",
        sections=(RawSection(role="context", purpose="x"),),
        generated_claims=(RawGeneratedClaim(text="invented claim", supporting_refs=RawContentRefs(fact_ids=("nope",))),),
    )
    plan = _materialize(raw, ctx)
    assert plan.generated_claims == ()


def test_materialize_coerces_unknown_role_to_a_safe_default():
    ctx = _context()
    raw = RawNarrativePlan(objective="introduce", sections=(RawSection(role="not-a-real-role", purpose="x"),))
    plan = _materialize(raw, ctx)
    assert plan.sections[0].role is SectionRole.CONTEXT


def test_materialize_falls_back_to_objective_hint_when_llm_string_is_invalid():
    ctx = _context()
    raw = RawNarrativePlan(objective="not-a-real-objective", sections=(RawSection(role="context", purpose="x"),))
    plan = _materialize(raw, ctx)
    assert plan.objective == ctx.objective_hint


def test_materialize_assigns_sequence_deterministically_by_order():
    ctx = _context()
    raw = RawNarrativePlan(
        objective="introduce",
        sections=(
            RawSection(role="opening", purpose="a"),
            RawSection(role="context", purpose="b"),
            RawSection(role="concept", purpose="c"),
        ),
    )
    plan = _materialize(raw, ctx)
    assert [s.sequence for s in plan.sections] == [0, 1, 2]


def test_materialize_never_lets_the_llm_set_audience():
    """RawNarrativePlan has no audience field at all -- the plan's
    audience always comes from context, never from the model."""
    assert "audience" not in RawNarrativePlan.model_fields
