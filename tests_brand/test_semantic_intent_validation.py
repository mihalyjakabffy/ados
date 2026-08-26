"""
ADOS-M3.1 — brand/llm/validation.py.

Every deterministic check ADOS-M3.1 §10 asks for, and that findings are
real ``brand.validation.brand_validator.Finding`` objects — the same
convention every other ADOS validator already uses.
"""

from __future__ import annotations

from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.llm.validation import validate_semantic_intent
from brand.llm.vocabulary import SemanticField
from brand.validation.brand_validator import Severity


def _codes(report):
    return [f.code for f in report.findings]


def test_a_fully_resolved_valid_intent_has_no_findings():
    si = SemanticIntent(explicit=SemanticFieldValues(
        action="create", target="document", document_type="portfolio", subject="Riverside",
    ))
    report = validate_semantic_intent(si)
    assert report.ok
    assert report.findings == []


def test_missing_action_is_a_block():
    si = SemanticIntent(explicit=SemanticFieldValues(target="document"))
    report = validate_semantic_intent(si)
    assert not report.ok
    assert "SIN-001" in _codes(report)
    assert report.blocking


def test_missing_target_is_a_block():
    si = SemanticIntent(explicit=SemanticFieldValues(action="create"))
    report = validate_semantic_intent(si)
    assert "SIN-002" in _codes(report)


def test_action_marked_ambiguous_satisfies_the_presence_requirement():
    si = SemanticIntent(
        explicit=SemanticFieldValues(target="document"),
        ambiguous=(SemanticField.ACTION,),
    )
    report = validate_semantic_intent(si)
    assert "SIN-001" not in _codes(report)


def test_unsupported_action_is_an_error():
    """The schema itself permits any string for action (§10's own checks —
    not pydantic's Enum — are what catch an unsupported value)."""
    si = SemanticIntent(explicit=SemanticFieldValues(action="delete", target="document"))
    report = validate_semantic_intent(si)
    assert "SIN-003" in _codes(report)
    assert any(f.severity is Severity.ERROR for f in report.findings)


def test_unsupported_target_is_an_error():
    si = SemanticIntent(explicit=SemanticFieldValues(action="create", target="galaxy"))
    report = validate_semantic_intent(si)
    assert "SIN-004" in _codes(report)


def test_unknown_document_type_is_an_error():
    si = SemanticIntent(explicit=SemanticFieldValues(
        action="create", target="document", document_type="not-a-real-type",
    ))
    report = validate_semantic_intent(si)
    assert "SIN-005" in _codes(report)


def test_document_type_ambiguous_is_not_flagged_as_unknown():
    si = SemanticIntent(
        explicit=SemanticFieldValues(action="create", target="document"),
        ambiguous=(SemanticField.DOCUMENT_TYPE,),
    )
    report = validate_semantic_intent(si)
    assert "SIN-005" not in _codes(report)


def test_blank_list_entry_is_malformed():
    si = SemanticIntent(explicit=SemanticFieldValues(
        action="create", target="document", references=("real reference", "   "),
    ))
    report = validate_semantic_intent(si)
    assert "SIN-006" in _codes(report)


def test_overlong_list_entry_is_malformed():
    si = SemanticIntent(explicit=SemanticFieldValues(
        action="create", target="document", constraints=("x" * 501,),
    ))
    report = validate_semantic_intent(si)
    assert "SIN-006" in _codes(report)


def test_document_type_with_non_document_target_is_contradictory():
    si = SemanticIntent(explicit=SemanticFieldValues(
        action="create", target="brand", document_type="portfolio",
    ))
    report = validate_semantic_intent(si)
    assert "SIN-007" in _codes(report)


def test_document_type_with_document_like_target_is_not_contradictory():
    for target in ("document", "presentation", "portfolio", "report", "template"):
        si = SemanticIntent(explicit=SemanticFieldValues(
            action="create", target=target, document_type="portfolio",
        ))
        report = validate_semantic_intent(si)
        assert "SIN-007" not in _codes(report), target


def test_compare_with_nothing_to_compare_is_impossible():
    si = SemanticIntent(explicit=SemanticFieldValues(action="compare", target="document"))
    report = validate_semantic_intent(si)
    assert "SIN-008" in _codes(report)


def test_compare_with_a_subject_is_valid():
    si = SemanticIntent(explicit=SemanticFieldValues(
        action="compare", target="document", subject="option A vs option B",
    ))
    report = validate_semantic_intent(si)
    assert "SIN-008" not in _codes(report)


def test_compare_with_references_ambiguous_is_valid():
    si = SemanticIntent(
        explicit=SemanticFieldValues(action="compare", target="document"),
        ambiguous=(SemanticField.REFERENCES,),
    )
    report = validate_semantic_intent(si)
    assert "SIN-008" not in _codes(report)


def test_create_document_missing_document_type_warns_not_blocks():
    si = SemanticIntent(explicit=SemanticFieldValues(action="create", target="document"))
    report = validate_semantic_intent(si)
    assert "SIN-009" in _codes(report)
    assert report.ok  # WARN never blocks


def test_create_document_with_ambiguous_document_type_does_not_warn():
    si = SemanticIntent(
        explicit=SemanticFieldValues(action="create", target="document"),
        ambiguous=(SemanticField.DOCUMENT_TYPE,),
    )
    report = validate_semantic_intent(si)
    assert "SIN-009" not in _codes(report)


def test_modify_action_never_triggers_the_create_document_type_warning():
    si = SemanticIntent(explicit=SemanticFieldValues(action="modify", target="document"))
    report = validate_semantic_intent(si)
    assert "SIN-009" not in _codes(report)


def test_high_confidence_with_heavy_inference_is_flagged_for_review():
    si = SemanticIntent(
        explicit=SemanticFieldValues(action="create", target="document"),
        inferred=SemanticFieldValues(
            audience="client", quality_direction="premium", style_reference="prior work",
        ),
        confidence=0.9,
    )
    report = validate_semantic_intent(si)
    assert "SIN-010" in _codes(report)
    assert report.ok  # still just a WARN


def test_low_confidence_with_heavy_inference_is_not_flagged():
    si = SemanticIntent(
        explicit=SemanticFieldValues(action="create", target="document"),
        inferred=SemanticFieldValues(
            audience="client", quality_direction="premium", style_reference="prior work",
        ),
        confidence=0.5,
    )
    report = validate_semantic_intent(si)
    assert "SIN-010" not in _codes(report)
