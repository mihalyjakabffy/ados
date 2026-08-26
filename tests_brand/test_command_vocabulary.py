"""ADOS-M3.5 — brand/llm/command/vocabulary.py."""

from __future__ import annotations

from brand.creative.intent import IntentType
from brand.llm.command.vocabulary import (
    DIRECTION_BY_COMPOSITION_STRATEGY,
    SAFETY_BY_INTENT_TYPE,
    TARGET_IMAGE_RATIO_BY_LEVEL,
    TARGET_TEXT_DENSITY_BY_LEVEL,
    CommandProvenance,
    CommandRejectionReason,
    CommandSafetyLevel,
)
from brand.llm.design.vocabulary import CompositionStrategy, TextDensity


def test_every_intent_type_has_a_safety_level():
    for intent_type in IntentType:
        assert intent_type in SAFETY_BY_INTENT_TYPE


def test_remove_content_is_the_only_destructive_type():
    destructive = {t for t, level in SAFETY_BY_INTENT_TYPE.items() if level is CommandSafetyLevel.DESTRUCTIVE}
    assert destructive == {IntentType.REMOVE_CONTENT}


def test_change_page_direction_is_review_recommended_not_safe():
    assert SAFETY_BY_INTENT_TYPE[IntentType.CHANGE_PAGE_DIRECTION] is CommandSafetyLevel.REVIEW_RECOMMENDED


def test_direction_lookup_only_names_real_shipped_directions():
    from brand.creative.directions import DIRECTIONS

    for target_id in DIRECTION_BY_COMPOSITION_STRATEGY.values():
        assert target_id in DIRECTIONS


def test_ambiguous_composition_strategies_have_no_direction_mapping():
    for strategy in (
        CompositionStrategy.BALANCED, CompositionStrategy.ASYMMETRIC,
        CompositionStrategy.MODULAR, CompositionStrategy.SEQUENTIAL, CompositionStrategy.IMMERSIVE,
    ):
        assert strategy not in DIRECTION_BY_COMPOSITION_STRATEGY


def test_text_density_targets_are_monotonic():
    ordered = [TARGET_TEXT_DENSITY_BY_LEVEL[level] for level in TextDensity]
    assert ordered == sorted(ordered)


def test_image_ratio_targets_are_monotonic():
    ordered = [TARGET_IMAGE_RATIO_BY_LEVEL[level] for level in TextDensity]
    assert ordered == sorted(ordered)


def test_rejection_reasons_and_provenance_are_distinct_values():
    assert len({r.value for r in CommandRejectionReason}) == len(list(CommandRejectionReason))
    assert len({p.value for p in CommandProvenance}) == len(list(CommandProvenance))
