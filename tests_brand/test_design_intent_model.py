"""
ADOS-M3.4 — brand/llm/design/model.py.

The domain model's own invariants: JSON round-tripping, frozen models,
extra-fields rejection, and the shape distinctness the master prompt
asks for (SectionDesign references section_id rather than duplicating
narrative content; AssetDesignRef references real asset ids).
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from brand.llm.design.model import (
    SCHEMA_VERSION,
    AssetDesignRef,
    DesignConstraint,
    DesignExclusion,
    DesignIntent,
    DesignIssue,
    DesignIssueType,
    SectionDesign,
)
from brand.llm.design.vocabulary import (
    AssetImportance,
    ColorStrategy,
    CompositionStrategy,
    ConstraintStrength,
    ContrastLevel,
    DesignExclusionReason,
    ImageRole,
    PersonalityAxis,
    TypographyHierarchy,
    VisualPriority,
    VisualRole,
    WhitespaceStrategy,
)


def _section_design(**kw) -> SectionDesign:
    kw.setdefault("section_id", "sec1")
    kw.setdefault("visual_role", (VisualRole.HERO,))
    kw.setdefault("visual_priority", VisualPriority.DOMINANT)
    kw.setdefault("composition_mode", CompositionStrategy.IMAGE_LED)
    kw.setdefault("text_density", "low")
    kw.setdefault("whitespace", WhitespaceStrategy.GENEROUS)
    kw.setdefault("contrast", ContrastLevel.HIGH)
    kw.setdefault("typography_hierarchy", TypographyHierarchy.STRONG)
    return SectionDesign(**kw)


def _design_intent(**kw) -> DesignIntent:
    kw.setdefault("project_id", "p1")
    kw.setdefault("composition_strategy", CompositionStrategy.IMAGE_LED)
    return DesignIntent(**kw)


def test_section_design_references_section_id_not_content():
    sd = _section_design()
    assert sd.section_id == "sec1"
    assert not hasattr(sd, "content_emphasis")  # not duplicated from NarrativeSection


def test_visual_role_requires_at_least_one():
    with pytest.raises(ValidationError):
        SectionDesign(
            section_id="s", visual_role=(), visual_priority=VisualPriority.SECONDARY,
            composition_mode=CompositionStrategy.BALANCED, text_density="medium",
            whitespace=WhitespaceStrategy.MODERATE, contrast=ContrastLevel.MEDIUM,
            typography_hierarchy=TypographyHierarchy.RESTRAINED,
        )


def test_section_design_supports_combined_visual_roles():
    sd = _section_design(visual_role=(VisualRole.HERO, VisualRole.DIAGRAM))
    assert sd.visual_role == (VisualRole.HERO, VisualRole.DIAGRAM)


def test_asset_design_ref_carries_a_real_looking_id_and_role():
    ref = AssetDesignRef(asset_id="asset_07", role=ImageRole.HERO_IMAGE, importance=AssetImportance.HERO)
    assert ref.asset_id == "asset_07"
    assert not hasattr(ref, "description")  # never a duplicated description of the asset


def test_design_constraint_distinguishes_hard_and_soft():
    hard = DesignConstraint(description="preserve_brand_minimalism", strength=ConstraintStrength.HARD, source="brand_dna")
    soft = DesignConstraint(description="prefer_image_dominance", strength=ConstraintStrength.SOFT, source="generated_preference")
    assert hard.strength is ConstraintStrength.HARD
    assert soft.strength is ConstraintStrength.SOFT


def test_design_issue_carries_a_type_and_optional_section():
    issue = DesignIssue(type=DesignIssueType.BRAND_CONFLICT, description="expressive request on a quiet brand")
    assert issue.section_id is None


def test_design_exclusion_requires_a_reason():
    exclusion = DesignExclusion(section_id="sec2", reason=DesignExclusionReason.REDUNDANT)
    assert exclusion.reason is DesignExclusionReason.REDUNDANT


def test_design_intent_round_trips_through_json():
    sd = _section_design(asset_refs=(AssetDesignRef(asset_id="asset_07", role=ImageRole.HERO_IMAGE),))
    di = _design_intent(section_designs=(sd,), visual_language=(PersonalityAxis.EDITORIAL,))
    payload = json.loads(json.dumps(di.to_dict()))
    rebuilt = DesignIntent.model_validate(payload)
    assert rebuilt.project_id == di.project_id
    assert rebuilt.section_designs[0].section_id == "sec1"
    assert payload["schema_version"] == SCHEMA_VERSION


def test_section_design_lookup_helper():
    sd = _section_design()
    di = _design_intent(section_designs=(sd,))
    assert di.section_design("sec1") is not None
    assert di.section_design("does-not-exist") is None


def test_models_are_frozen():
    sd = _section_design()
    with pytest.raises(ValidationError):
        sd.visual_priority = VisualPriority.MINIMAL  # type: ignore[misc]


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        SectionDesign.model_validate({
            "section_id": "s", "visual_role": ["hero"], "visual_priority": "dominant",
            "composition_mode": "image_led", "text_density": "low",
            "whitespace": "generous", "contrast": "high",
            "typography_hierarchy": "strong", "bogus": True,
        })
