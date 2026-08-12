"""
The structured intent layer: brand/creative/intent.py.

These tests are about the intent layer's own contract — that it prepares
valid (ContentModel, CreativeDirection) pairs and refuses to when it
shouldn't — not about composition itself, which
tests_brand/test_creative.py already covers. Every intent produced here is
also run through the real compose(), because a domain object that merely
validates but does not actually compose would be a false confidence.
"""

from __future__ import annotations

import pytest

from brand.creative.composer import CompositionError, compose
from brand.creative.direction import CreativeDirection
from brand.creative.directions import get_direction
from brand.creative.intent import (
    CommandIntent,
    IntentTarget,
    IntentType,
    IntentValidationError,
    PreserveConstraint,
    TargetType,
    apply_intent,
    validate_intent,
)
from brand.examples.malthouse import malthouse_content


@pytest.fixture(scope="module")
def content():
    return malthouse_content()


@pytest.fixture(scope="module")
def studio_om():
    from brand.examples.studio_om import studio_om as build

    return build()


@pytest.fixture()
def base_direction():
    return get_direction("editorial-quiet")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_a_well_formed_intent_validates(content):
    intent = CommandIntent(
        type=IntentType.REDUCE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.PAGE, id="4"),
        parameters={"strength": 0.7},
    )
    assert validate_intent(content, intent, page_count=8) == []


@pytest.mark.parametrize(
    "key,value",
    [("color", "#ff0000"), ("font_family", "Inter"), ("grid_columns", 6)],
)
def test_a_geometry_or_brand_parameter_is_rejected(content, key, value):
    intent = CommandIntent(
        type=IntentType.REDUCE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={key: value},
    )
    errors = validate_intent(content, intent, page_count=8)
    assert errors, f"{key}={value!r} should have been rejected"


def test_a_hex_colour_string_is_rejected_even_under_a_permitted_key(content):
    intent = CommandIntent(
        type=IntentType.REDUCE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"note": "make it #336699"},
    )
    errors = validate_intent(content, intent, page_count=8)
    assert any("colour" in e for e in errors)


def test_a_dimension_string_is_rejected(content):
    intent = CommandIntent(
        type=IntentType.REDUCE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"note": "20mm margin please"},
    )
    errors = validate_intent(content, intent, page_count=8)
    assert any("dimension" in e for e in errors)


def test_strength_out_of_range_is_rejected(content):
    intent = CommandIntent(
        type=IntentType.INCREASE_IMAGE_EMPHASIS,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"strength": 1.7},
    )
    assert validate_intent(content, intent, page_count=8)


def test_a_page_target_out_of_range_is_rejected(content):
    intent = CommandIntent(
        type=IntentType.RECOMPOSE_PAGE,
        target=IntentTarget(type=TargetType.PAGE, id="99"),
    )
    errors = validate_intent(content, intent, page_count=8)
    assert any("does not exist" in e for e in errors)


def test_a_content_block_target_that_does_not_exist_is_rejected(content):
    intent = CommandIntent(
        type=IntentType.PRESERVE_CONTENT,
        target=IntentTarget(type=TargetType.CONTENT_BLOCK, id="nope-99"),
        parameters={"content_ids": ["met-01"]},
    )
    errors = validate_intent(content, intent, page_count=8)
    assert any("does not exist" in e for e in errors)


def test_unknown_content_ids_are_rejected(content):
    intent = CommandIntent(
        type=IntentType.REMOVE_CONTENT,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"content_ids": ["not-a-real-block"]},
    )
    errors = validate_intent(content, intent, page_count=8)
    assert any("unknown content_ids" in e for e in errors)


def test_removing_every_block_is_rejected(content):
    all_ids = [b.id for b in content.blocks]
    intent = CommandIntent(
        type=IntentType.REMOVE_CONTENT,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"content_ids": all_ids},
    )
    errors = validate_intent(content, intent, page_count=8)
    assert any("cannot remove every block" in e for e in errors)


def test_change_page_direction_requires_a_known_direction(content):
    intent = CommandIntent(
        type=IntentType.CHANGE_PAGE_DIRECTION,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"direction_id": "not-a-real-direction"},
    )
    errors = validate_intent(content, intent, page_count=8)
    assert any("unknown direction_id" in e for e in errors)


def test_a_preserve_constraint_with_an_unknown_id_is_rejected(content):
    intent = CommandIntent(
        type=IntentType.RECOMPOSE_PAGE,
        target=IntentTarget(type=TargetType.DOCUMENT),
        constraints=(PreserveConstraint(content_ids=("nope-99",)),),
    )
    errors = validate_intent(content, intent, page_count=8)
    assert any("unknown preserve_content" in e for e in errors)


# ---------------------------------------------------------------------------
# Application — and a real compose() after each, not just apply_intent()
# ---------------------------------------------------------------------------


def test_reduce_text_density_lowers_density_and_still_composes(content, base_direction, studio_om):
    intent = CommandIntent(
        type=IntentType.REDUCE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.PAGE, id="4"),
        parameters={"strength": 0.7},
    )
    new_content, new_direction, resolution = apply_intent(content, base_direction, intent)
    assert new_direction.text_density < base_direction.text_density
    assert resolution.direction_changed and not resolution.content_changed
    plan = compose(new_content, new_direction, studio_om)
    assert plan.pages


def test_reduce_text_density_never_crosses_the_ados_floor(content, base_direction):
    from brand import ados

    low, _ = ados.fill_ratio_bounds()
    intent = CommandIntent(
        type=IntentType.REDUCE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"strength": 1.0},
    )
    _, new_direction, _ = apply_intent(content, base_direction, intent)
    assert new_direction.text_density >= low


def test_increase_image_emphasis_raises_image_ratio_and_composes(content, base_direction, studio_om):
    intent = CommandIntent(
        type=IntentType.INCREASE_IMAGE_EMPHASIS,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"strength": 0.6},
    )
    new_content, new_direction, resolution = apply_intent(content, base_direction, intent)
    assert new_direction.image_ratio > base_direction.image_ratio
    plan = compose(new_content, new_direction, studio_om)
    assert plan.pages


def test_decrease_image_emphasis_never_goes_negative(content, base_direction):
    intent = CommandIntent(
        type=IntentType.DECREASE_IMAGE_EMPHASIS,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"strength": 1.0},
    )
    _, new_direction, _ = apply_intent(content, base_direction, intent)
    assert new_direction.image_ratio >= 0.0


def test_recompose_page_leaves_the_direction_untouched(content, base_direction, studio_om):
    intent = CommandIntent(type=IntentType.RECOMPOSE_PAGE, target=IntentTarget(type=TargetType.DOCUMENT))
    new_content, new_direction, resolution = apply_intent(content, base_direction, intent)
    assert new_direction == base_direction
    assert not resolution.direction_changed and not resolution.content_changed
    plan_a = compose(new_content, new_direction, studio_om)
    plan_b = compose(content, base_direction, studio_om)
    assert plan_a.plan_hash == plan_b.plan_hash


def test_preserve_content_boosts_priority_without_changing_block_count(content, base_direction, studio_om):
    ids = ["met-01", "met-02"]
    intent = CommandIntent(
        type=IntentType.PRESERVE_CONTENT,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"content_ids": ids},
    )
    new_content, new_direction, resolution = apply_intent(content, base_direction, intent)
    assert len(new_content.blocks) == len(content.blocks)
    assert resolution.content_changed
    for block_id in ids:
        assert new_content.by_id(block_id).priority == 1
    plan = compose(new_content, new_direction, studio_om)
    assert plan.pages


def test_remove_content_actually_removes_blocks_and_composes(content, base_direction, studio_om):
    intent = CommandIntent(
        type=IntentType.REMOVE_CONTENT,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"content_ids": ["met-01"]},
    )
    new_content, new_direction, resolution = apply_intent(content, base_direction, intent)
    assert len(new_content.blocks) == len(content.blocks) - 1
    assert "met-01" not in {b.id for b in new_content.blocks}
    plan = compose(new_content, new_direction, studio_om)
    assert "met-01" not in plan.placed_blocks


def test_change_page_direction_switches_to_the_requested_direction(content, base_direction, studio_om):
    intent = CommandIntent(
        type=IntentType.CHANGE_PAGE_DIRECTION,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"direction_id": "image-led"},
    )
    new_content, new_direction, resolution = apply_intent(content, base_direction, intent)
    assert new_direction.id == "image-led"
    assert resolution.direction_changed
    plan = compose(new_content, new_direction, studio_om)
    assert plan.direction == "image-led"


def test_a_page_targeted_intent_discloses_it_is_document_wide(content, base_direction):
    intent = CommandIntent(
        type=IntentType.REDUCE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.PAGE, id="2"),
        parameters={"strength": 0.5},
    )
    _, _, resolution = apply_intent(content, base_direction, intent)
    assert any("document-wide" in n for n in resolution.notes)


def test_a_preserve_constraint_alongside_a_density_change_boosts_both(content, base_direction):
    intent = CommandIntent(
        type=IntentType.REDUCE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.PAGE, id="4"),
        parameters={"strength": 0.6},
        constraints=(PreserveConstraint(content_ids=("met-01",)),),
    )
    new_content, new_direction, _ = apply_intent(content, base_direction, intent)
    assert new_content.by_id("met-01").priority == 1
    assert new_direction.text_density < base_direction.text_density


# ---------------------------------------------------------------------------
# Determinism — the property the whole layer exists to protect
# ---------------------------------------------------------------------------


def test_applying_the_same_intent_twice_is_byte_identical(content, base_direction, studio_om):
    intent = CommandIntent(
        type=IntentType.REDUCE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.PAGE, id="4"),
        parameters={"strength": 0.7},
    )
    c1, d1, _ = apply_intent(content, base_direction, intent)
    c2, d2, _ = apply_intent(content, base_direction, intent)
    assert d1 == d2
    plan1 = compose(c1, d1, studio_om)
    plan2 = compose(c2, d2, studio_om)
    assert plan1.plan_hash == plan2.plan_hash


def test_a_derived_direction_still_passes_full_direction_validation(content, base_direction):
    """model_copy would skip validators; _derive must not."""
    intent = CommandIntent(
        type=IntentType.INCREASE_TEXT_DENSITY,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"strength": 1.0},
    )
    _, new_direction, _ = apply_intent(content, base_direction, intent)
    # Re-validating the already-derived direction must succeed identically.
    revalidated = CreativeDirection.model_validate(new_direction.model_dump(mode="json"))
    assert revalidated == new_direction
