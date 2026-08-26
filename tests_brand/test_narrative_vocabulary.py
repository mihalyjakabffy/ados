"""ADOS-M3.3 — brand/llm/narrative/vocabulary.py."""

from __future__ import annotations

from brand.creative.direction import Audience
from brand.llm.narrative.vocabulary import (
    ExclusionReason,
    MissingImpact,
    NarrativeCompression,
    NarrativeIssueType,
    NarrativeObjective,
    NarrativeVoice,
    Relevance,
    Requirement,
    SectionPriority,
    SectionRole,
    Tone,
)


def test_audience_is_reused_from_creative_direction():
    from brand.llm.narrative import vocabulary

    assert vocabulary.Audience is Audience


def test_narrative_objective_matches_master_prompt_intent():
    assert {o.value for o in NarrativeObjective} == {
        "introduce", "explain", "persuade", "document",
        "present", "compare", "summarize", "demonstrate",
    }


def test_section_role_matches_master_prompt_ss11():
    assert {r.value for r in SectionRole} == {
        "opening", "context", "problem", "question", "concept", "strategy",
        "analysis", "development", "evidence", "comparison", "result",
        "impact", "technical_explanation", "conclusion", "call_to_action", "closing",
    }


def test_section_priority_matches_master_prompt_ss16():
    assert {p.value for p in SectionPriority} == {"primary", "secondary", "supporting", "optional"}


def test_requirement_matches_master_prompt_ss17():
    assert {r.value for r in Requirement} == {"required", "recommended", "optional"}


def test_relevance_is_a_three_step_scale():
    assert {r.value for r in Relevance} == {"low", "medium", "high"}


def test_tone_matches_master_prompt_ss29():
    assert {t.value for t in Tone} == {
        "precise", "confident", "restrained", "technical",
        "editorial", "persuasive", "academic", "accessible",
    }


def test_narrative_voice_matches_master_prompt_ss30():
    assert {v.value for v in NarrativeVoice} == {
        "first_person_studio", "third_person", "neutral", "editorial", "technical",
    }


def test_missing_impact_matches_master_prompt_ss18():
    assert {m.value for m in MissingImpact} == {"blocking", "important", "optional", "irrelevant"}


def test_exclusion_reason_matches_master_prompt_ss19():
    assert {e.value for e in ExclusionReason} == {
        "unsupported_claim", "conflicting_metric", "irrelevant_detail",
        "internal_only", "obsolete_version", "other",
    }


def test_narrative_issue_type_includes_conflicting_information():
    assert NarrativeIssueType.CONFLICTING_INFORMATION.value == "conflicting_information"


def test_narrative_compression_matches_master_prompt_ss22():
    assert {c.value for c in NarrativeCompression} == {"short", "medium", "long"}
