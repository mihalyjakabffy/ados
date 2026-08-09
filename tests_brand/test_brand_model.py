"""Brand model: construction, serialisation, content addressing, lifecycle."""

from __future__ import annotations

import json

import pytest

from brand.models.brand import Brand, BrandStatus
from brand.models.identity import PersonalityAxis
from brand.models.visual_identity import ColourSystem, FontFace


def test_create_from_a_name_alone():
    """A brand with only a name must be valid and resolvable.

    The system is worth nothing if it demands forty fields before producing
    anything; this is the floor.
    """
    b = Brand.create(name="Minimal Practice")
    assert b.identity.name == "Minimal Practice"
    assert b.visual_identity.typography.primary_font.family == "Inter"
    assert b.content_hash and len(b.content_hash) == 64
    assert len(b.resolve_tokens()) > 50


def test_create_accepts_a_font_face_or_a_family_name():
    by_name = Brand.create(name="A", primary_font="Söhne")
    by_face = Brand.create(
        name="A", primary_font=FontFace(family="Söhne", cap_height_ratio=0.71)
    )
    assert by_name.visual_identity.typography.primary_font.family == "Söhne"
    assert by_face.visual_identity.typography.primary_font.cap_height_ratio == 0.71


def test_json_round_trip_is_lossless(studio_nord):
    again = Brand.from_json(studio_nord.to_json())
    assert again.is_equivalent_to(studio_nord)
    assert again.model_dump(mode="json") == studio_nord.model_dump(mode="json")


def test_content_hash_ignores_record_metadata(studio_nord):
    """Two brands differing only in status or timestamp are the same brand."""
    other = studio_nord.model_copy(
        update={"status": BrandStatus.DRAFT, "changelog": "different note"}
    )
    assert other.compute_content_hash() == studio_nord.compute_content_hash()


def test_content_hash_changes_with_content(studio_nord):
    changed = studio_nord.model_copy(
        update={
            "visual_identity": studio_nord.visual_identity.model_copy(
                update={
                    "colour": studio_nord.visual_identity.colour.model_copy(
                        update={"accent": "#ff0000"}
                    )
                }
            )
        }
    )
    assert changed.compute_content_hash() != studio_nord.compute_content_hash()


def test_brand_is_frozen(studio_nord):
    with pytest.raises(Exception):
        studio_nord.version = "9.9.9"      # type: ignore[misc]


def test_extra_fields_are_rejected():
    """``extra='forbid'`` is what turns a hallucinated field into an error."""
    payload = json.loads(Brand.create(name="A").to_json())
    payload["vibe"] = "moody"
    with pytest.raises(Exception):
        Brand.model_validate(payload)


def test_publish_requires_approval():
    b = Brand.create(name="A")
    assert b.status is BrandStatus.DRAFT
    with pytest.raises(ValueError, match="approve it first"):
        b.published()
    assert b.approved().published().status is BrandStatus.PUBLISHED


def test_is_usable_only_when_approved_or_published():
    b = Brand.create(name="A")
    assert not b.is_usable
    assert b.approved().is_usable
    assert b.approved().published().is_usable


def test_invalid_hex_is_rejected_at_construction():
    with pytest.raises(ValueError, match="hex colour"):
        ColourSystem(primary="not-a-colour")


def test_personality_is_a_closed_vocabulary():
    from brand.models.identity import Identity

    ident = Identity(name="A", personality=(PersonalityAxis.QUIET,))
    assert ident.personality == (PersonalityAxis.QUIET,)
    with pytest.raises(ValueError):
        Identity(name="A", personality=("vibey",))         # type: ignore[arg-type]


def test_spacing_scale_must_ascend():
    from brand.models.visual_identity import Spacing

    with pytest.raises(ValueError, match="ascending"):
        Spacing(scale=(4, 2, 1))


def test_hierarchy_must_start_at_the_cut():
    from brand.models.architectural_language import DrawingLanguage, GraphicLayer

    with pytest.raises(ValueError, match="cut must be heaviest"):
        DrawingLanguage(
            hierarchy=(GraphicLayer.PROJECTION, GraphicLayer.CUT)
        )


def test_label_is_readable(studio_nord):
    assert studio_nord.label == "Studio Nord 1.0.0 (published)"
