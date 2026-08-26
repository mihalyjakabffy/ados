"""
brand/llm/content/validation.py

Deterministic validation for a :class:`ContentIntelligenceModel`
(ADOS-M3.2's own equivalent of ADOS-M3.1 §10). Reuses
``brand.validation.brand_validator``'s ``Finding``/``Severity``/
``Category``/``ValidationReport`` — the same convention every other
ADOS validator, including ``brand.llm.validation`` (M3.1), already
uses.

Two things are checked that ``brand.llm.content.model``'s own
per-object validators cannot: cross-references *within* the model
(a relationship or claim naming an entity that does not exist in this
same model) and, optionally, cross-references *outside* it (an asset
naming a real project's asset id). The truth-bearing/source-refs rule
is re-checked here too — deliberately redundant with
``model.py``'s own ``model_validator``s, per that module's own
docstring: ADOS-M3.2 §8's hallucination guard gets two independent
layers, not one.

This module never measures *semantic* hallucination (whether an
extracted fact is actually supported by its source's real content) —
that requires comparing extracted content against source text, which is
what ``brand.llm.content.evaluation``'s dataset-driven harness does.
This module only checks internal consistency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from brand.llm.content.model import ContentIntelligenceModel
from brand.llm.content.vocabulary import TRUTH_BEARING_STATUSES
from brand.validation.brand_validator import Category, Finding, Severity, ValidationReport

if TYPE_CHECKING:
    from brand.project.model import Project


def validate_content_model(
    content: ContentIntelligenceModel, project: Optional["Project"] = None,
) -> ValidationReport:
    findings: list[Finding] = []

    findings.extend(_check_provenance_guard(content))
    findings.extend(_check_relationship_entities_exist(content))
    findings.extend(_check_claim_entities_exist(content))
    findings.extend(_check_missing_info_not_contradicted(content))
    findings.extend(_check_no_duplicate_fact_keys(content))
    findings.extend(_check_verified_confidence(content))
    if project is not None:
        findings.extend(_check_asset_ids_are_real(content, project))

    return ValidationReport(brand_label=f"content:{content.project_id}", findings=findings)


def _check_provenance_guard(content: ContentIntelligenceModel) -> list[Finding]:
    """ADOS-M3.2 §8/§28's hallucination guard, re-checked independently
    of ``model.py``'s own constructor-time validators — the same
    "two layers that don't share code" the model's docstring commits to."""
    findings: list[Finding] = []
    for fact in content.facts:
        if fact.status in TRUTH_BEARING_STATUSES and not fact.source_refs:
            findings.append(Finding(
                Severity.BLOCK, Category.STRUCTURAL, f"fact:{fact.key}",
                f"fact {fact.key!r} has status {fact.status.value!r} but no source_refs.",
                code="CIN-000",
            ))
    for claim in content.claims:
        if claim.status in TRUTH_BEARING_STATUSES and not claim.source_refs:
            findings.append(Finding(
                Severity.BLOCK, Category.STRUCTURAL, f"claim:{claim.id}",
                f"claim {claim.text[:60]!r} has status {claim.status.value!r} but no source_refs.",
                code="CIN-000",
            ))
    return findings


def _check_relationship_entities_exist(content: ContentIntelligenceModel) -> list[Finding]:
    known = {e.id for e in content.entities}
    findings = []
    for rel in content.relationships:
        for role, entity_id in (("subject", rel.subject_entity_id), ("object", rel.object_entity_id)):
            if entity_id not in known:
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL, f"relationship:{rel.id}",
                    f"relationship {role} {entity_id!r} is not a real entity in this ContentIntelligenceModel.",
                    code="CIN-001",
                ))
    return findings


def _check_claim_entities_exist(content: ContentIntelligenceModel) -> list[Finding]:
    known = {e.id for e in content.entities}
    findings = []
    for claim in content.claims:
        for entity_id in claim.related_entity_ids:
            if entity_id not in known:
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL, f"claim:{claim.id}",
                    f"claim references entity {entity_id!r}, which does not exist in this ContentIntelligenceModel.",
                    code="CIN-002",
                ))
    return findings


def _check_missing_info_not_contradicted(content: ContentIntelligenceModel) -> list[Finding]:
    known_keys = {f.key for f in content.facts if f.superseded_by is None}
    findings = []
    for gap in content.missing_information:
        if gap.key in known_keys:
            findings.append(Finding(
                Severity.ERROR, Category.CONSISTENCY, f"missing:{gap.key}",
                f"{gap.key!r} is listed as missing information but a current fact "
                f"with that key already exists — a gap and a known value cannot both be true.",
                code="CIN-003",
            ))
    return findings


def _check_no_duplicate_fact_keys(content: ContentIntelligenceModel) -> list[Finding]:
    seen: set[str] = set()
    findings = []
    for fact in content.facts:
        if fact.superseded_by is not None:
            continue
        if fact.key in seen:
            findings.append(Finding(
                Severity.ERROR, Category.CONSISTENCY, f"fact:{fact.key}",
                f"more than one current (non-superseded) fact carries the key {fact.key!r} "
                f"— facts sharing a key must be merged into one, conflicting or not.",
                code="CIN-004",
            ))
        seen.add(fact.key)
    return findings


def _check_verified_confidence(content: ContentIntelligenceModel) -> list[Finding]:
    """ADOS-M3.2 §22: status is the truth-bearing signal, confidence is
    not — but a status of VERIFIED alongside a low confidence number is
    itself an inconsistency worth a second look: verification is not
    usually a matter of degree."""
    findings = []
    for fact in content.facts:
        if fact.status.value == "verified" and fact.confidence < 0.9:
            findings.append(Finding(
                Severity.WARN, Category.CONSISTENCY, f"fact:{fact.key}",
                f"fact {fact.key!r} is marked verified with confidence "
                f"{fact.confidence:.2f} — verified is not usually a matter of degree; "
                f"consider inferred if there is real uncertainty.",
                code="CIN-005",
            ))
    return findings


def _check_asset_ids_are_real(content: ContentIntelligenceModel, project: "Project") -> list[Finding]:
    known_ids = {a.id for a in project.assets}
    findings = []
    for asset in content.assets:
        if asset.asset_id not in known_ids:
            findings.append(Finding(
                Severity.ERROR, Category.STRUCTURAL, f"asset:{asset.asset_id}",
                f"asset {asset.asset_id!r} does not exist in project {project.id!r}.",
                code="CIN-006",
            ))
    return findings
