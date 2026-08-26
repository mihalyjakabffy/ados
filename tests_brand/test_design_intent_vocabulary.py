"""ADOS-M3.4 — brand/llm/design/vocabulary.py."""

from __future__ import annotations

from brand.creative.direction import Audience
from brand.models.identity import PersonalityAxis
from brand.llm.design.vocabulary import (
    AssetImportance,
    ColorStrategy,
    CompositionStrategy,
    ConstraintStrength,
    ContrastLevel,
    DesignChangeType,
    DesignExclusionReason,
    GridStrategy,
    ImageRole,
    Rhythm,
    TextDensity,
    TypographyHierarchy,
    VisualPriority,
    VisualRole,
    WhitespaceStrategy,
)


def test_audience_and_personality_axis_are_reused_not_redeclared():
    from brand.llm.design import vocabulary

    assert vocabulary.Audience is Audience
    assert vocabulary.PersonalityAxis is PersonalityAxis


def test_composition_strategy_matches_master_prompt_ss11():
    assert {c.value for c in CompositionStrategy} == {
        "image_led", "text_led", "diagram_led", "data_led", "balanced",
        "asymmetric", "modular", "sequential", "immersive", "dense", "sparse",
    }


def test_visual_role_matches_master_prompt_ss13():
    assert {r.value for r in VisualRole} == {
        "hero", "intro", "contextual", "diagram", "comparison", "evidence",
        "technical", "gallery", "quote", "data", "process", "detail", "closing",
    }


def test_visual_priority_matches_master_prompt_ss12():
    assert {p.value for p in VisualPriority} == {"dominant", "secondary", "supporting", "minimal"}


def test_text_density_matches_master_prompt_ss15():
    assert {d.value for d in TextDensity} == {"minimal", "low", "medium", "high", "very_high"}


def test_image_role_matches_master_prompt_ss16():
    assert {r.value for r in ImageRole} == {
        "hero_image", "supporting_image", "image_sequence", "gallery", "comparison",
        "full_bleed", "detail", "diagram_support", "background", "thumbnail",
    }


def test_asset_importance_matches_master_prompt_ss18():
    assert {a.value for a in AssetImportance} == {"hero", "primary", "supporting", "optional"}


def test_typography_hierarchy_matches_master_prompt_ss19():
    assert {t.value for t in TypographyHierarchy} == {
        "strong", "restrained", "editorial", "technical", "expressive",
    }


def test_color_strategy_matches_master_prompt_ss20():
    assert {c.value for c in ColorStrategy} == {
        "neutral_dominant", "accent_for_emphasis", "monochrome",
        "brand_accent", "high_contrast", "restrained",
    }


def test_grid_strategy_matches_master_prompt_ss21():
    assert {g.value for g in GridStrategy} == {
        "strict", "modular", "editorial", "asymmetric", "fluid", "dense", "open",
    }


def test_whitespace_strategy_matches_master_prompt_ss22():
    assert {w.value for w in WhitespaceStrategy} == {
        "generous", "moderate", "compact", "dramatic", "continuous", "sectional",
    }


def test_rhythm_matches_master_prompt_ss23():
    assert {r.value for r in Rhythm} == {
        "steady", "alternating", "progressive", "dramatic", "calm",
        "dense_to_sparse", "sparse_to_dense",
    }


def test_contrast_level_is_a_three_step_scale():
    assert {c.value for c in ContrastLevel} == {"low", "medium", "high"}


def test_constraint_strength_matches_master_prompt_ss30():
    assert {c.value for c in ConstraintStrength} == {"hard", "soft"}


def test_design_change_type_matches_master_prompt_ss54():
    assert {c.value for c in DesignChangeType} == {"preserve", "modify", "introduce", "remove"}


def test_design_exclusion_reason_is_small_and_closed():
    assert {e.value for e in DesignExclusionReason} == {
        "redundant", "insufficient_content", "out_of_scope", "other",
    }
