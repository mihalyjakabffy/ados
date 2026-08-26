"""
brand/llm/design/validation.py

Deterministic validation for a :class:`DesignIntent` (ADOS-M3.4 §32) —
this package's equivalent of ADOS-M3.2/M3.3's own
``brand.llm.content.validation``/``brand.llm.narrative.validation``.
Reuses the same ``brand.validation.brand_validator`` ``Finding``/
``Severity``/``Category``/``ValidationReport`` convention every other
ADOS validator already uses.

**Numbering is adapted from the master prompt's own DES-001..012 list**
(ADOS-M3.4 §32 itself invites this: "adapt numbering to existing
repository conventions. Do not duplicate an existing validation
framework"). Ten checks below cover every *deterministically checkable*
concept the master prompt names; two of its literal items are covered
without a distinct code: "unknown visual vocabulary" (§32 DES-004) is
structurally impossible once a `DesignIntent` exists at all — every
enum-like field is a closed pydantic enum, so an unrecognised value
never survives construction (`_materialize`'s own `_coerce_enum` is
where that would be caught, before a `DesignIntent` exists to
validate) — and "unsupported visual inference" (§32 DES-012) has no
deterministic signature beyond the reference/brand-token checks
already covered by DES-001..004: the only channel through which a
generator could assert something concrete is a section/asset
reference or a brand-token name, both independently checked.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from brand.validation.brand_validator import Category, Finding, Severity, ValidationReport

if TYPE_CHECKING:
    from brand.llm.content.model import ContentIntelligenceModel
    from brand.llm.design.context import BrandCapabilities
    from brand.llm.design.model import DesignIntent
    from brand.llm.narrative.model import NarrativePlan

#: Mirrors ``brand.creative.direction``'s own dimension/hex detection —
#: the same "a design decision must not smuggle in geometry" concern,
#: applied here to free-text fields (rationale, constraint/issue/
#: exclusion descriptions, diagram_strategy) rather than a
#: CreativeDirection's note field.
_DIMENSION = re.compile(r"\b\d+(?:\.\d+)?\s?(mm|cm|pt|px|em|rem|%)\b", re.I)
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_COORDINATE = re.compile(r"\b[xy]\s*=\s*-?\d+(?:\.\d+)?\b", re.I)
_COLUMN_COUNT = re.compile(r"\b\d+\s*-?\s*column\b", re.I)

#: Personality traits a "strong/expressive" typographic or colour
#: choice is coherent with — anything else on a quiet/restrained/
#: precise brand is a conflict worth flagging (ADOS-M3.4 §53).
_EXPRESSIVE_COMPATIBLE_TRAITS = frozenset({"expressive", "playful", "experimental", "monumental"})
_RESTRAINED_TRAITS = frozenset({"quiet", "precise", "pragmatic"})


def validate_design_intent(
    design_intent: "DesignIntent",
    narrative_plan: "NarrativePlan",
    content: Optional["ContentIntelligenceModel"] = None,
    brand: Optional["BrandCapabilities"] = None,
) -> ValidationReport:
    findings: list[Finding] = []

    findings.extend(_check_section_refs_resolve(design_intent, narrative_plan))
    if content is not None:
        findings.extend(_check_asset_refs_resolve(design_intent, content))
    if brand is not None:
        findings.extend(_check_brand_typography_tokens(design_intent, brand))
        findings.extend(_check_brand_visual_language(design_intent, brand))
    findings.extend(_check_no_duplicate_coverage(design_intent))
    findings.extend(_check_no_section_silently_omitted(design_intent, narrative_plan))
    findings.extend(_check_contradictory_density(design_intent))
    findings.extend(_check_hero_asset_priority_mismatch(design_intent))
    if brand is not None:
        findings.extend(_check_brand_consistency(design_intent, brand))
    findings.extend(_check_layout_leakage(design_intent))

    return ValidationReport(brand_label=f"design:{design_intent.project_id}", findings=findings)


def _check_section_refs_resolve(design_intent: "DesignIntent", plan: "NarrativePlan") -> list[Finding]:
    known = {s.id for s in plan.all_sections()}
    findings = []
    for sd in design_intent.section_designs:
        if sd.section_id not in known:
            findings.append(Finding(
                Severity.ERROR, Category.STRUCTURAL, f"section_design:{sd.id}",
                f"SectionDesign references section {sd.section_id!r}, which does not "
                f"exist in this NarrativePlan.", code="DES-001",
            ))
    for ex in design_intent.excluded_sections:
        if ex.section_id not in known:
            findings.append(Finding(
                Severity.ERROR, Category.STRUCTURAL, f"exclusion:{ex.section_id}",
                f"exclusion references section {ex.section_id!r}, which does not exist "
                f"in this NarrativePlan.", code="DES-001",
            ))
    return findings


def _check_asset_refs_resolve(design_intent: "DesignIntent", content: "ContentIntelligenceModel") -> list[Finding]:
    known = {a.asset_id for a in content.assets}
    findings = []
    for sd in design_intent.section_designs:
        for ref in sd.asset_refs:
            if ref.asset_id not in known:
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL, f"section_design:{sd.id}",
                    f"asset reference {ref.asset_id!r} does not exist in this "
                    f"ContentIntelligenceModel.", code="DES-002",
                ))
    return findings


def _check_brand_typography_tokens(design_intent: "DesignIntent", brand: "BrandCapabilities") -> list[Finding]:
    findings = []
    for sd in design_intent.section_designs:
        for field_name, role, allowed in (
            ("heading_role", sd.heading_role, brand.heading_roles),
            ("body_role", sd.body_role, brand.body_roles),
            ("caption_role", sd.caption_role, brand.body_roles),
        ):
            if role is not None and allowed and role not in allowed:
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL, f"section_design:{sd.id}",
                    f"{field_name} {role!r} is not a real type role this brand defines "
                    f"({', '.join(allowed)}).", code="DES-003",
                ))
    return findings


def _check_brand_visual_language(design_intent: "DesignIntent", brand: "BrandCapabilities") -> list[Finding]:
    if not brand.personality:
        return []
    findings = []
    for trait in design_intent.visual_language:
        if trait.value not in brand.personality:
            findings.append(Finding(
                Severity.ERROR, Category.STRUCTURAL, "visual_language",
                f"visual_language names {trait.value!r}, which this brand's own "
                f"Identity.personality does not claim ({', '.join(brand.personality)}).",
                code="DES-004",
            ))
    return findings


def _check_no_duplicate_coverage(design_intent: "DesignIntent") -> list[Finding]:
    designed = {sd.section_id for sd in design_intent.section_designs}
    excluded = {ex.section_id for ex in design_intent.excluded_sections}
    overlap = designed & excluded
    return [
        Finding(
            Severity.ERROR, Category.CONSISTENCY, f"section:{section_id}",
            f"section {section_id!r} appears in both section_designs and "
            f"excluded_sections — a section is one or the other, never both.",
            code="DES-005",
        )
        for section_id in overlap
    ]


def _check_no_section_silently_omitted(design_intent: "DesignIntent", plan: "NarrativePlan") -> list[Finding]:
    """ADOS-M3.4 §27, re-checked independently of the generator's own
    materialization guarantee — the same "two layers that don't share
    code" discipline ADOS-M3.2 §8's hallucination guard established."""
    known = {s.id for s in plan.all_sections()}
    covered = {sd.section_id for sd in design_intent.section_designs} | {
        ex.section_id for ex in design_intent.excluded_sections
    }
    return [
        Finding(
            Severity.BLOCK, Category.STRUCTURAL, f"section:{section_id}",
            f"narrative section {section_id!r} has neither a SectionDesign nor an "
            f"explicit exclusion — no narrative section may silently disappear.",
            code="DES-006",
        )
        for section_id in (known - covered)
    ]


def _check_contradictory_density(design_intent: "DesignIntent") -> list[Finding]:
    """ADOS-M3.4 §31 — an obviously self-contradictory combination on
    one section (both text and image density minimal on a section the
    plan says should visually dominate)."""
    findings = []
    for sd in design_intent.section_designs:
        if (
            sd.visual_priority.value == "dominant"
            and sd.text_density.value == "minimal"
            and sd.image_density.value == "minimal"
        ):
            findings.append(Finding(
                Severity.WARN, Category.CONSISTENCY, f"section_design:{sd.id}",
                f"section {sd.section_id!r} is visually dominant but carries minimal "
                f"text and image density — nothing is left to dominate with.",
                code="DES-007",
            ))
    return findings


def _check_hero_asset_priority_mismatch(design_intent: "DesignIntent") -> list[Finding]:
    """ADOS-M3.4 §31 — a hero-importance asset in a minimally
    prioritised section is a contradiction the deterministic composer
    should not have to silently resolve."""
    findings = []
    for sd in design_intent.section_designs:
        for ref in sd.asset_refs:
            if ref.importance.value == "hero" and sd.visual_priority.value in ("minimal", "supporting"):
                findings.append(Finding(
                    Severity.WARN, Category.CONSISTENCY, f"section_design:{sd.id}",
                    f"asset {ref.asset_id!r} is marked hero-importance in a section "
                    f"whose visual_priority is {sd.visual_priority.value!r}.",
                    code="DES-008",
                ))
    return findings


def _check_brand_consistency(design_intent: "DesignIntent", brand: "BrandCapabilities") -> list[Finding]:
    """ADOS-M3.4 §39/§53 — an expressive design choice on a brand that
    claims none of the traits that would justify it, with no matching
    ``brand_conflict`` design_issue already acknowledging the tension."""
    if not brand.personality:
        return []
    brand_is_restrained = any(t in brand.personality for t in _RESTRAINED_TRAITS)
    if not brand_is_restrained:
        return []
    brand_allows_expressive = any(t in brand.personality for t in _EXPRESSIVE_COMPATIBLE_TRAITS)
    if brand_allows_expressive:
        return []

    flagged_sections = {i.section_id for i in design_intent.design_issues if i.type.value == "brand_conflict"}
    findings = []
    for sd in design_intent.section_designs:
        if sd.typography_hierarchy.value == "expressive" and sd.section_id not in flagged_sections:
            findings.append(Finding(
                Severity.ERROR, Category.CONSISTENCY, f"section_design:{sd.id}",
                f"section {sd.section_id!r} requests an expressive typography "
                f"hierarchy on a brand whose personality is restrained "
                f"({', '.join(sorted(brand.personality))}) — flag this as a "
                f"brand_conflict design_issue rather than silently overriding the "
                f"brand.", code="DES-009",
            ))
    return findings


def _check_layout_leakage(design_intent: "DesignIntent") -> list[Finding]:
    """ADOS-M3.4 §48/§58 — a free-text field that has started to
    describe geometry (a pixel width, a hex colour, an x/y coordinate,
    a column count) is layout leaking into what must stay a semantic
    design intent."""
    findings = []
    texts: list[tuple[str, str]] = []
    for sd in design_intent.section_designs:
        if sd.rationale:
            texts.append((f"section_design:{sd.id}.rationale", sd.rationale))
        if sd.diagram_strategy:
            texts.append((f"section_design:{sd.id}.diagram_strategy", sd.diagram_strategy))
    for c in design_intent.constraints:
        texts.append((f"constraint:{c.description[:30]}", c.description))
    for i in design_intent.design_issues:
        texts.append((f"design_issue:{i.type.value}", i.description))

    for where, text in texts:
        for pattern, label in ((_DIMENSION, "a dimension"), (_HEX, "a colour"), (_COORDINATE, "a coordinate"), (_COLUMN_COUNT, "a column count")):
            if pattern.search(text):
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL, where,
                    f"{where} names {label} ({text!r}) — DesignIntent is semantic; "
                    f"geometry belongs to the deterministic Composer, not this layer.",
                    code="DES-010",
                ))
    return findings
