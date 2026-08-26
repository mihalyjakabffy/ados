"""
brand/llm/narrative/validation.py

Deterministic validation for a :class:`NarrativePlan` (ADOS-M3.3 §24) —
this package's equivalent of ADOS-M3.2's ``brand.llm.content.validation``.
Reuses the same ``brand.validation.brand_validator`` ``Finding``/
``Severity``/``Category``/``ValidationReport`` convention every other
ADOS validator already uses.

This checks internal consistency of a plan *against the
ContentIntelligenceModel it claims to be resolved from* — a
``NarrativePlan`` alone cannot be checked for dangling references (it
has no content to check them against), so ``content`` is a required
argument here, unlike ``brand.llm.content.validation.validate_content_model``'s
optional one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from brand.validation.brand_validator import Category, Finding, Severity, ValidationReport

if TYPE_CHECKING:
    from brand.llm.content.model import ContentIntelligenceModel
    from brand.llm.narrative.model import ContentReferenceSet, NarrativePlan


def validate_narrative_plan(
    plan: "NarrativePlan", content: "ContentIntelligenceModel",
) -> ValidationReport:
    findings: list[Finding] = []

    findings.extend(_check_no_duplicate_section_ids(plan))
    findings.extend(_check_sequence_is_valid(plan))
    findings.extend(_check_refs_resolve(plan, content))
    findings.extend(_check_conflicting_content_is_flagged(plan, content))
    findings.extend(_check_generated_claims_are_grounded(plan))
    findings.extend(_check_thesis_is_supported(plan))
    findings.extend(_check_required_sections_have_purpose(plan))
    findings.extend(_check_factual_sections_have_content(plan))

    return ValidationReport(brand_label=f"narrative:{plan.project_id}", findings=findings)


def _all_ref_ids(refs: "ContentReferenceSet") -> tuple[tuple[str, str], ...]:
    """Every id in a ContentReferenceSet, tagged with which bucket it
    came from — for error messages that say *which* kind of id is
    dangling."""
    out: list[tuple[str, str]] = []
    out.extend(("fact", i) for i in refs.fact_ids)
    out.extend(("claim", i) for i in refs.claim_ids)
    out.extend(("asset", i) for i in refs.asset_ids)
    out.extend(("entity", i) for i in refs.entity_ids)
    return tuple(out)


def _check_no_duplicate_section_ids(plan: "NarrativePlan") -> list[Finding]:
    seen: set[str] = set()
    findings = []
    for section in plan.all_sections():
        if section.id in seen:
            findings.append(Finding(
                Severity.ERROR, Category.STRUCTURAL, f"section:{section.id}",
                f"more than one section carries the id {section.id!r}.",
                code="NAR-001",
            ))
        seen.add(section.id)
    return findings


def _check_sequence_is_valid(plan: "NarrativePlan") -> list[Finding]:
    findings = []
    for parent_sections in (plan.sections, *(s.subsections for s in plan.sections)):
        seen: set[int] = set()
        for section in parent_sections:
            if section.sequence in seen:
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL, f"section:{section.id}",
                    f"sequence {section.sequence} is used by more than one section "
                    f"at the same level — a sequence cannot order two sections into "
                    f"the same position.",
                    code="NAR-002",
                ))
            seen.add(section.sequence)
    return findings


def _check_refs_resolve(plan: "NarrativePlan", content: "ContentIntelligenceModel") -> list[Finding]:
    known_facts = {f.id for f in content.facts}
    known_claims = {c.id for c in content.claims}
    known_assets = {a.asset_id for a in content.assets}
    known_entities = {e.id for e in content.entities}
    known = {"fact": known_facts, "claim": known_claims, "asset": known_assets, "entity": known_entities}

    findings = []

    def _check(refs: "ContentReferenceSet", where: str) -> None:
        for kind, ref_id in _all_ref_ids(refs):
            if ref_id not in known[kind]:
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL, where,
                    f"{where} references {kind} {ref_id!r}, which does not exist in "
                    f"this ContentIntelligenceModel.",
                    code="NAR-003",
                ))

    for section in plan.all_sections():
        _check(section.content_refs, f"section:{section.id}")
    if plan.thesis is not None:
        _check(plan.thesis.supporting_refs, "thesis")
    for claim in plan.generated_claims:
        _check(claim.supporting_refs, f"generated_claim:{claim.id}")
    for issue in plan.narrative_issues:
        _check(issue.content_refs, f"narrative_issue:{issue.type.value}")
    for exclusion in plan.exclusions:
        _check(exclusion.excluded_refs, f"exclusion:{exclusion.reason.value}")

    return findings


def _check_conflicting_content_is_flagged(
    plan: "NarrativePlan", content: "ContentIntelligenceModel",
) -> list[Finding]:
    """ADOS-M3.3 §20/§24: content used in the plan whose own M3.2 status
    is CONFLICTING must be named in a ``narrative_issue`` — never used
    as if it were settled."""
    conflicting_ids = {f.id for f in content.facts if f.status.value == "conflicting"}
    if not conflicting_ids:
        return []
    flagged = {
        ref_id for issue in plan.narrative_issues
        for kind, ref_id in _all_ref_ids(issue.content_refs) if kind == "fact"
    }
    findings = []
    for section in plan.all_sections():
        used_conflicting = set(section.content_refs.fact_ids) & conflicting_ids
        unflagged = used_conflicting - flagged
        if unflagged:
            findings.append(Finding(
                Severity.ERROR, Category.CONSISTENCY, f"section:{section.id}",
                f"section references conflicting fact(s) {sorted(unflagged)} without "
                f"a matching narrative_issue — ADOS-M3.3 §20: conflicting content "
                f"must be flagged, never used as if it were settled.",
                code="NAR-004",
            ))
    return findings


def _check_generated_claims_are_grounded(plan: "NarrativePlan") -> list[Finding]:
    """The model's own validator already forbids an empty-refs generated
    claim from being constructed at all (ADOS-M3.3 §15) — this is the
    independent, "two layers that don't share code" re-check, the same
    posture ADOS-M3.2 §8's hallucination guard takes."""
    findings = []
    for claim in plan.generated_claims:
        if claim.supporting_refs.is_empty:
            findings.append(Finding(
                Severity.BLOCK, Category.STRUCTURAL, f"generated_claim:{claim.id}",
                f"generated claim {claim.text[:60]!r} has no supporting_refs.",
                code="NAR-005",
            ))
    return findings


def _check_thesis_is_supported(plan: "NarrativePlan") -> list[Finding]:
    if plan.thesis is None:
        return []
    if plan.thesis.supporting_refs.is_empty:
        return [Finding(
            Severity.BLOCK, Category.STRUCTURAL, "thesis",
            "the plan states a thesis with no supporting_refs — ADOS-M3.3 §8: a "
            "thesis must be grounded in real content or represented as absent.",
            code="NAR-006",
        )]
    return []


def _check_required_sections_have_purpose(plan: "NarrativePlan") -> list[Finding]:
    """Schema-level ``min_length=1`` already makes an empty purpose
    unconstructible; this checks the more meaningful ADOS-M3.3 §24
    condition: a REQUIRED section whose purpose is a placeholder-length
    stub is a section nobody has actually reasoned about."""
    findings = []
    for section in plan.all_sections():
        if section.requirement.value == "required" and len(section.purpose.strip()) < 10:
            findings.append(Finding(
                Severity.WARN, Category.CONSISTENCY, f"section:{section.id}",
                f"required section {section.id!r} has a purpose too short to "
                f"explain why it exists ({section.purpose!r}).",
                code="NAR-007",
            ))
    return findings


def _check_factual_sections_have_content(plan: "NarrativePlan") -> list[Finding]:
    """A section whose role implies it is carrying project-specific
    material (evidence/technical_explanation/comparison/result/impact)
    but whose content_refs are entirely empty is either mis-labelled or
    thin — worth a WARN, never a hard failure (ADOS-M3.3 §17: missing
    optional content must not block a plan)."""
    _FACTUAL_ROLES = {"evidence", "technical_explanation", "comparison", "result", "impact"}
    findings = []
    for section in plan.all_sections():
        if section.role.value in _FACTUAL_ROLES and section.content_refs.is_empty and section.requirement.value != "optional":
            findings.append(Finding(
                Severity.WARN, Category.CONSISTENCY, f"section:{section.id}",
                f"section {section.id!r} has role {section.role.value!r} but no "
                f"content references — a factual section with nothing behind it.",
                code="NAR-008",
            ))
    return findings
