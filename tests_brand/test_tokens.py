"""Token resolution: derivation, provenance, namespace discipline, overlays."""

from __future__ import annotations

import pytest

from brand import ados
from brand.models.brand import Brand
from brand.models.tokens import TokenBuilder, TokenSet, UndefinedTokenError, Unit


def test_resolution_is_deterministic(studio_nord):
    """Same brand in, same tokens out — this is what makes a pin reproducible."""
    a = studio_nord.resolve_tokens().flat()
    b = studio_nord.resolve_tokens().flat()
    assert a == b


def test_point_size_is_derived_from_cap_height(studio_nord, tokens):
    """The one derivation the whole type system rests on.

    ``pt = cap_mm ÷ cap_height_ratio ÷ (25.4/72)``. If this drifts, every
    document is set at the wrong size while looking plausible.
    """
    ratio = studio_nord.visual_identity.typography.primary_font.cap_height_ratio
    cap = tokens["font.size.sm"].value
    expected = cap / ratio / (25.4 / 72.0)
    assert tokens["font.size.sm.pt"].value == pytest.approx(expected, abs=0.01)


def test_type_sizes_are_steps_of_the_ados_scale(tokens):
    scale = set(ados.type_scale_mm())
    for name in ("font.size.xs", "font.size.sm", "font.size.md",
                 "font.size.lg", "font.size.xl", "font.size.display"):
        assert tokens[name].value in scale, f"{name} is off the ADOS type scale"


def test_spacing_scale_is_multiplied_out(studio_nord, tokens):
    base = studio_nord.visual_identity.spacing.base_unit_mm
    for i, factor in enumerate(studio_nord.visual_identity.spacing.scale, start=1):
        assert tokens[f"space.{i}"].value == pytest.approx(base * factor)


def test_every_token_carries_provenance(tokens):
    """A token with no source cannot be debugged when a document is wrong."""
    sourceless = [
        t.name for t in tokens.values() if not t.source and not t.constraint
    ]
    assert sourceless == []


def test_constrained_tokens_cite_their_rule(tokens):
    assert "ADOS" in tokens["font.size.sm"].constraint
    assert "ADOS" in tokens["stroke.cut"].constraint
    assert "ADOS" in tokens["tone.T3"].constraint


def test_monochrome_equivalents_are_emitted(tokens):
    """Drawings are greyscale; a consumer must not derive the grey itself."""
    mono = tokens["color.brand.accent.mono"].value
    assert mono.startswith("#")
    assert mono[1:3] == mono[3:5] == mono[5:7], "not a neutral grey"


def test_undefined_token_names_itself(tokens):
    with pytest.raises(UndefinedTokenError) as exc:
        tokens["color.brand.tertiary"]
    assert "color.brand.tertiary" in str(exc.value)
    assert "color." in str(exc.value), "the hint should list the namespace"


def test_namespace_is_closed():
    b = TokenBuilder()
    with pytest.raises(ValueError, match="outside the declared namespaces"):
        b.add("vibe.mood", "moody")


def test_duplicate_tokens_are_refused():
    b = TokenBuilder().add("color.x", "#000", Unit.HEX, source="a")
    with pytest.raises(ValueError, match="duplicate token"):
        b.add("color.x", "#fff", Unit.HEX, source="b")


def test_overrides_change_values_not_vocabulary(studio_nord):
    over = studio_nord.resolve_tokens(**{"grid.columns": 4})
    assert over["grid.columns"].value == 4
    assert "project override" in over["grid.columns"].source
    with pytest.raises(ValueError, match="does not define"):
        studio_nord.resolve_tokens(**{"grid.rows": 9})


def test_token_set_is_a_mapping(tokens):
    assert "font.family.primary" in tokens
    assert len(list(tokens)) == len(tokens)
    assert tokens.value("nope.nope", "fallback") == "fallback"


def test_namespace_slice(tokens):
    colours = tokens.namespace("color")
    assert colours and all(k.startswith("color.") for k in colours)


def test_serialisation_keeps_unit_and_source(tokens):
    payload = tokens.to_json_dict()
    entry = payload["tokens"]["font.size.sm"]
    assert entry["unit"] == "mm"
    assert entry["source"]
    assert payload["brand_version"] == tokens.brand_version


def test_merge_prefers_the_overlay():
    from brand.models.tokens import Token

    a = TokenSet({"color.x": Token(name="color.x", value="#000")}, brand_id="a",
                 brand_version="1.0.0")
    b = TokenSet({"color.x": Token(name="color.x", value="#fff")}, brand_id="b",
                 brand_version="2.0.0")
    merged = a.merged_with(b)
    assert merged["color.x"].value == "#fff"
    assert merged.brand_version == "2.0.0"


def test_every_template_binding_resolves(tokens):
    """The catalogue's contract against the resolver's output.

    A template that binds a token the resolver never emits is a document that
    cannot render, and this is far cheaper to catch here.
    """
    from brand.templates.document_templates import all_bound_tokens

    missing = sorted(all_bound_tokens() - set(tokens))
    assert missing == [], f"templates bind unresolvable tokens: {missing}"


def test_a_minimal_brand_reports_what_it_cannot_render(minimal_brand):
    """An incomplete brand degrades to a coverage report, not a crash.

    ``Brand.create(name=...)`` declares no monospace face, so the invoice —
    the one template that sets figures in mono — cannot render. The right
    behaviour is for ``coverage()`` to say so before anything is attempted,
    and for every other template to be unaffected. A system that instead
    substituted a proportional face would produce an invoice whose columns do
    not align, which is worse than one that was never produced.
    """
    from brand.templates.document_templates import coverage

    cov = coverage(minimal_brand.resolve_tokens())
    assert cov["BT09-invoice"] == ["font.family.mono"]
    assert all(not missing for tid, missing in cov.items() if tid != "BT09-invoice")


def test_a_complete_brand_renders_every_template(tokens):
    from brand.templates.document_templates import coverage

    assert all(not missing for missing in coverage(tokens).values())


def test_brand_without_mono_face_omits_mono_tokens():
    b = Brand.create(name="A")
    assert b.visual_identity.typography.mono_font is None
    assert "font.family.mono" not in b.resolve_tokens()
