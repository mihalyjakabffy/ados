"""ADOS-M3.4 — brand/llm/design/validation.py."""

from __future__ import annotations

from brand.llm.content.model import AssetContent, ContentIntelligenceModel
from brand.llm.design.context import BrandCapabilities
from brand.llm.design.model import (
    AssetDesignRef,
    DesignExclusion,
    DesignIntent,
    DesignIssue,
    DesignIssueType,
    SectionDesign,
)
from brand.llm.design.validation import validate_design_intent
from brand.llm.design.vocabulary import (
    AssetImportance,
    ColorStrategy,
    CompositionStrategy,
    ContrastLevel,
    DesignExclusionReason,
    ImageRole,
    PersonalityAxis,
    TextDensity,
    TypographyHierarchy,
    VisualPriority,
    VisualRole,
    WhitespaceStrategy,
)
from brand.llm.narrative.model import NarrativePlan, NarrativeSection
from brand.llm.narrative.vocabulary import Audience, NarrativeObjective, SectionRole


def _plan(**kw) -> NarrativePlan:
    kw.setdefault("project_id", "p1")
    kw.setdefault("objective", NarrativeObjective.INTRODUCE)
    kw.setdefault("audience", Audience.CLIENT)
    return NarrativePlan(**kw)


def _section(**kw) -> NarrativeSection:
    kw.setdefault("role", SectionRole.CONTEXT)
    kw.setdefault("purpose", "x")
    kw.setdefault("sequence", 0)
    return NarrativeSection(**kw)


def _sd(section_id: str, **kw) -> SectionDesign:
    kw.setdefault("visual_role", (VisualRole.CONTEXTUAL,))
    kw.setdefault("visual_priority", VisualPriority.SECONDARY)
    kw.setdefault("composition_mode", CompositionStrategy.BALANCED)
    kw.setdefault("text_density", TextDensity.MEDIUM)
    kw.setdefault("whitespace", WhitespaceStrategy.MODERATE)
    kw.setdefault("contrast", ContrastLevel.MEDIUM)
    kw.setdefault("typography_hierarchy", TypographyHierarchy.RESTRAINED)
    return SectionDesign(section_id=section_id, **kw)


def _di(**kw) -> DesignIntent:
    kw.setdefault("project_id", "p1")
    kw.setdefault("composition_strategy", CompositionStrategy.BALANCED)
    return DesignIntent(**kw)


def test_valid_design_intent_has_no_findings():
    sec = _section()
    plan = _plan(sections=(sec,))
    di = _di(section_designs=(_sd(sec.id),))
    report = validate_design_intent(di, plan)
    assert report.ok
    assert report.findings == []


def test_des_001_dangling_section_reference():
    plan = _plan(sections=(_section(),))
    di = _di(section_designs=(_sd("does-not-exist"),))
    report = validate_design_intent(di, plan)
    assert "DES-001" in {f.code for f in report.findings}


def test_des_002_dangling_asset_reference():
    sec = _section()
    plan = _plan(sections=(sec,))
    content = ContentIntelligenceModel(project_id="p1", assets=(
        AssetContent(asset_id="real-asset"),
    ))
    di = _di(section_designs=(_sd(sec.id, asset_refs=(AssetDesignRef(asset_id="fake-asset", role=ImageRole.HERO_IMAGE),)),))
    report = validate_design_intent(di, plan, content)
    assert "DES-002" in {f.code for f in report.findings}


def test_des_003_unknown_typography_role():
    sec = _section()
    plan = _plan(sections=(sec,))
    brand = BrandCapabilities(heading_roles=("h1",), body_roles=("body",))
    di = _di(section_designs=(_sd(sec.id, heading_role="not-real"),))
    report = validate_design_intent(di, plan, brand=brand)
    assert "DES-003" in {f.code for f in report.findings}


def test_des_004_unclaimed_visual_language():
    sec = _section()
    plan = _plan(sections=(sec,))
    brand = BrandCapabilities(personality=("quiet", "precise"))
    di = _di(visual_language=(PersonalityAxis.PLAYFUL,), section_designs=(_sd(sec.id),))
    report = validate_design_intent(di, plan, brand=brand)
    assert "DES-004" in {f.code for f in report.findings}


def test_des_005_duplicate_coverage():
    sec = _section()
    plan = _plan(sections=(sec,))
    di = _di(section_designs=(_sd(sec.id),), excluded_sections=(DesignExclusion(section_id=sec.id, reason=DesignExclusionReason.OTHER),))
    report = validate_design_intent(di, plan)
    assert "DES-005" in {f.code for f in report.findings}


def test_des_006_section_silently_omitted():
    sec = _section()
    plan = _plan(sections=(sec,))
    di = _di()
    report = validate_design_intent(di, plan)
    assert "DES-006" in {f.code for f in report.findings}
    assert not report.ok


def test_des_007_contradictory_density():
    sec = _section()
    plan = _plan(sections=(sec,))
    di = _di(section_designs=(_sd(sec.id, visual_priority=VisualPriority.DOMINANT, text_density=TextDensity.MINIMAL, image_density=TextDensity.MINIMAL),))
    report = validate_design_intent(di, plan)
    assert "DES-007" in {f.code for f in report.findings}


def test_des_008_hero_asset_in_minimal_section():
    sec = _section()
    plan = _plan(sections=(sec,))
    di = _di(section_designs=(_sd(sec.id, visual_priority=VisualPriority.MINIMAL, asset_refs=(AssetDesignRef(asset_id="a1", role=ImageRole.HERO_IMAGE, importance=AssetImportance.HERO),)),))
    report = validate_design_intent(di, plan)
    assert "DES-008" in {f.code for f in report.findings}


def test_des_009_brand_conflict_not_flagged():
    sec = _section()
    plan = _plan(sections=(sec,))
    brand = BrandCapabilities(personality=("quiet", "precise"))
    di = _di(section_designs=(_sd(sec.id, typography_hierarchy=TypographyHierarchy.EXPRESSIVE),))
    report = validate_design_intent(di, plan, brand=brand)
    assert "DES-009" in {f.code for f in report.findings}


def test_des_009_is_suppressed_when_flagged_as_a_design_issue():
    sec = _section()
    plan = _plan(sections=(sec,))
    brand = BrandCapabilities(personality=("quiet", "precise"))
    issue = DesignIssue(type=DesignIssueType.BRAND_CONFLICT, description="expressive request", section_id=sec.id)
    di = _di(section_designs=(_sd(sec.id, typography_hierarchy=TypographyHierarchy.EXPRESSIVE),), design_issues=(issue,))
    report = validate_design_intent(di, plan, brand=brand)
    assert "DES-009" not in {f.code for f in report.findings}


def test_des_010_layout_leakage_in_rationale():
    sec = _section()
    plan = _plan(sections=(sec,))
    di = _di(section_designs=(_sd(sec.id, rationale="make the hero image 640px wide"),))
    report = validate_design_intent(di, plan)
    assert "DES-010" in {f.code for f in report.findings}


def test_des_010_layout_leakage_hex_colour():
    sec = _section()
    plan = _plan(sections=(sec,))
    di = _di(section_designs=(_sd(sec.id, diagram_strategy="use #ff5500 for the diagram fill"),))
    report = validate_design_intent(di, plan)
    assert "DES-010" in {f.code for f in report.findings}
