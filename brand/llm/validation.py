"""
brand/llm/validation.py

Deterministic validation for a :class:`~brand.llm.semantic_intent.SemanticIntent`
(ADOS-M3.1 §10). This is the second of the two gates ADOS-M3.1 §9
describes — schema validity (pydantic, already enforced by
``SemanticIntent`` itself) is necessary but not sufficient; a
schema-valid intent can still say something ADOS cannot act on, and this
module is what catches that.

Reuses ``brand.validation.brand_validator``'s ``Finding``/``Severity``/
``Category``/``ValidationReport`` — the same structures
``brand.creative.evaluate`` and ``brand.project.requirements`` already
report through — rather than inventing a second validation framework
(ADOS-M3.1 §10's own instruction).

Nothing here executes anything: this module reads a ``SemanticIntent``
and a ``SemanticContext`` and returns a report. It never reaches
``brand.creative.intent`` or ``brand.creative.composer``.
"""

from __future__ import annotations

from brand.llm.context import SemanticContext
from brand.llm.semantic_intent import SemanticIntent
from brand.llm.vocabulary import (
    Action,
    Target,
    SemanticField,
    known_document_type_ids,
)
from brand.validation.brand_validator import Category, Finding, Severity, ValidationReport

#: A document-type only makes sense against one of these — the "target
#: names a document-shaped thing" subset of Target (ADOS-M3.1 §5).
_DOCUMENT_LIKE_TARGETS = frozenset({
    Target.DOCUMENT, Target.PRESENTATION, Target.PORTFOLIO,
    Target.REPORT, Target.TEMPLATE,
})

_MAX_ITEM_LENGTH = 500

_LIST_FIELDS = (
    SemanticField.CONTENT_REQUIREMENTS, SemanticField.STYLE_REQUIREMENTS,
    SemanticField.DESIGN_REQUIREMENTS, SemanticField.CONSTRAINTS,
    SemanticField.REFERENCES, SemanticField.MODIFIERS,
)


def validate_semantic_intent(
    intent: SemanticIntent, context: SemanticContext | None = None,
) -> ValidationReport:
    """Everything pydantic's schema alone cannot say about one intent.

    ``context`` is optional — most checks here are self-contained
    (unsupported action, malformed reference), but a couple use it where
    real information changes the answer (e.g. no document-type mismatch
    check has anything to compare against without knowing what the
    request actually named).
    """

    findings: list[Finding] = []

    findings.extend(_check_action_present(intent))
    findings.extend(_check_target_present(intent))
    findings.extend(_check_action_valid(intent))
    findings.extend(_check_target_valid(intent))
    findings.extend(_check_document_type_valid(intent))
    findings.extend(_check_malformed_list_entries(intent))
    findings.extend(_check_document_type_target_contradiction(intent))
    findings.extend(_check_compare_has_something_to_compare(intent))
    findings.extend(_check_create_document_type_missing(intent))
    findings.extend(_check_confidence_vs_inference_load(intent))

    label = (context.request[:80] if context is not None else "") or "semantic-intent"
    return ValidationReport(brand_label=label, findings=findings)


# ---------------------------------------------------------------------------
# Individual checks — one function, one rule, so a failure names exactly
# which of ADOS-M3.1 §10's bullet points fired.
# ---------------------------------------------------------------------------


def _check_action_present(intent: SemanticIntent) -> list[Finding]:
    if intent.resolved(SemanticField.ACTION) is not None or intent.is_ambiguous(SemanticField.ACTION):
        return []
    return [Finding(
        Severity.BLOCK, Category.STRUCTURAL, "action",
        "no action was resolved or marked ambiguous — a SemanticIntent must "
        "state what it doesn't know, never simply omit it.",
        suggestion="Set explicit.action, inferred.action, or add 'action' to ambiguous.",
        code="SIN-001",
    )]


def _check_target_present(intent: SemanticIntent) -> list[Finding]:
    if intent.resolved(SemanticField.TARGET) is not None or intent.is_ambiguous(SemanticField.TARGET):
        return []
    return [Finding(
        Severity.BLOCK, Category.STRUCTURAL, "target",
        "no target was resolved or marked ambiguous — the same rule as "
        "action: a missing target must be flagged, not left blank.",
        suggestion="Set explicit.target, inferred.target, or add 'target' to ambiguous.",
        code="SIN-002",
    )]


def _check_action_valid(intent: SemanticIntent) -> list[Finding]:
    value = intent.resolved(SemanticField.ACTION)
    if value is None or value in {a.value for a in Action}:
        return []
    return [Finding(
        Severity.ERROR, Category.STRUCTURAL, "action",
        f"unsupported action {value!r} — not one of the ADOS-M3.1 vocabulary's "
        f"{', '.join(a.value for a in Action)}.",
        suggestion="Use a value from the controlled Action vocabulary.",
        code="SIN-003",
    )]


def _check_target_valid(intent: SemanticIntent) -> list[Finding]:
    value = intent.resolved(SemanticField.TARGET)
    if value is None or value in {t.value for t in Target}:
        return []
    return [Finding(
        Severity.ERROR, Category.STRUCTURAL, "target",
        f"unsupported target {value!r} — not one of the ADOS-M3.1 vocabulary's "
        f"{', '.join(t.value for t in Target)}.",
        suggestion="Use a value from the controlled Target vocabulary.",
        code="SIN-004",
    )]


def _check_document_type_valid(intent: SemanticIntent) -> list[Finding]:
    value = intent.resolved(SemanticField.DOCUMENT_TYPE)
    if value is None or value in known_document_type_ids():
        return []
    return [Finding(
        Severity.ERROR, Category.STRUCTURAL, "document_type",
        f"unknown document_type {value!r} — not in the ADOS Document Type "
        f"registry (brand.project.document_types.DOCUMENT_TYPES).",
        suggestion="Resolve against the real registry, or mark document_type ambiguous.",
        code="SIN-005",
    )]


def _check_malformed_list_entries(intent: SemanticIntent) -> list[Finding]:
    findings: list[Finding] = []
    for bucket_name, bucket in (("explicit", intent.explicit), ("inferred", intent.inferred)):
        for field in _LIST_FIELDS:
            for item in bucket.get(field):
                if not item.strip():
                    findings.append(Finding(
                        Severity.ERROR, Category.STRUCTURAL, field.value,
                        f"{bucket_name}.{field.value} contains a blank entry.",
                        suggestion="Remove empty entries — an unstated requirement is no requirement.",
                        code="SIN-006",
                    ))
                elif len(item) > _MAX_ITEM_LENGTH:
                    findings.append(Finding(
                        Severity.ERROR, Category.STRUCTURAL, field.value,
                        f"{bucket_name}.{field.value} has an entry of {len(item)} "
                        f"characters — longer than a single requirement should be.",
                        suggestion="Split into multiple, shorter entries.",
                        code="SIN-006",
                    ))
    return findings


def _check_document_type_target_contradiction(intent: SemanticIntent) -> list[Finding]:
    doc_type = intent.resolved(SemanticField.DOCUMENT_TYPE)
    target = intent.resolved(SemanticField.TARGET)
    if doc_type is None or target is None:
        return []
    try:
        target_enum = Target(target)
    except ValueError:
        return []  # already reported by _check_target_valid
    if target_enum in _DOCUMENT_LIKE_TARGETS:
        return []
    return [Finding(
        Severity.ERROR, Category.STRUCTURAL, "document_type",
        f"document_type {doc_type!r} is set but target is {target!r}, which "
        f"is not a document-shaped target — a document_type only applies to "
        f"one of {', '.join(t.value for t in _DOCUMENT_LIKE_TARGETS)}.",
        suggestion="Either change target to a document-shaped value, or clear document_type.",
        code="SIN-007",
    )]


def _check_compare_has_something_to_compare(intent: SemanticIntent) -> list[Finding]:
    if intent.resolved(SemanticField.ACTION) != Action.COMPARE.value:
        return []
    has_subject = bool(intent.resolved(SemanticField.SUBJECT))
    has_references = bool(intent.explicit.references) or bool(intent.inferred.references)
    if has_subject or has_references or intent.is_ambiguous(SemanticField.REFERENCES):
        return []
    return [Finding(
        Severity.ERROR, Category.STRUCTURAL, "action",
        "action is 'compare' but nothing to compare against was resolved — "
        "no subject and no references.",
        suggestion="Name what is being compared in 'subject' or 'references', "
                   "or mark 'references' ambiguous.",
        code="SIN-008",
    )]


def _check_create_document_type_missing(intent: SemanticIntent) -> list[Finding]:
    target = intent.resolved(SemanticField.TARGET)
    try:
        target_enum = Target(target) if target is not None else None
    except ValueError:
        target_enum = None
    if (
        intent.resolved(SemanticField.ACTION) != Action.CREATE.value
        or target_enum not in _DOCUMENT_LIKE_TARGETS
        or intent.resolved(SemanticField.DOCUMENT_TYPE) is not None
        or intent.is_ambiguous(SemanticField.DOCUMENT_TYPE)
    ):
        return []
    return [Finding(
        Severity.WARN, Category.STRUCTURAL, "document_type",
        "creating a document but document_type is neither resolved nor "
        "marked ambiguous — if the type genuinely wasn't specified, say so "
        "explicitly rather than leaving the field silently empty.",
        suggestion="Add 'document_type' to ambiguous if it truly cannot be resolved.",
        code="SIN-009",
    )]


def _check_confidence_vs_inference_load(intent: SemanticIntent) -> list[Finding]:
    inferred_count = len(intent.inferred.set_fields())
    if intent.confidence >= 0.85 and inferred_count >= 3:
        return [Finding(
            Severity.WARN, Category.CONSISTENCY, "confidence",
            f"confidence is {intent.confidence:.2f} while {inferred_count} fields "
            f"were inferred rather than stated — a high overall confidence "
            f"alongside many inferences is worth a second look before trusting it.",
            suggestion="Lower confidence, or move genuinely-uncertain inferences to ambiguous.",
            code="SIN-010",
        )]
    return []
