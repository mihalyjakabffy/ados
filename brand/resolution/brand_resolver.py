"""
brand/resolution/brand_resolver.py

Brand → design tokens.

This is the bridge in ``Brand → Tokens → Outputs``, and the reason nothing
downstream is allowed to read a ``Brand`` object directly. Three things happen
here that a consumer must not have to do for itself:

1. **Derivation.** Point sizes are computed from cap height and the face's
   measured cap-height ratio; the spacing scale is multiplied out; screen
   sizes come from the millimetre values. A consumer that derived these itself
   would be a second implementation of the type scale.

2. **Constraint binding.** Where ADOS bounds a value, the token records which
   rule bounded it. That is what lets a document explain itself.

3. **Flattening.** A nested brand becomes a flat namespace a template engine,
   a JSON exporter or an Archicad attribute mapper can consume without knowing
   the brand's shape.

Resolution is pure: same brand in, same tokens out, no I/O beyond reading the
ADOS artefacts. That is what makes a document reproducible from a version pin.
"""

from __future__ import annotations

from typing import Any

from brand import ados
from brand.models.brand import Brand
from brand.models.tokens import TokenBuilder, TokenSet, Unit
from brand.models.visual_identity import FontFace

_MM_PER_PT = 25.4 / 72.0

#: Role name → the type-scale step used when the brand has not bound the role.
#: Chosen to match the PTS document family, so an unbound role still produces a
#: document that conforms rather than one that fails validation.
DEFAULT_TYPE_ROLES: dict[str, str] = {
    "font.size.xs": "t1",
    "font.size.sm": "t2",
    "font.size.md": "t3",
    "font.size.lg": "t4",
    "font.size.xl": "t5",
    "font.size.display": "t7",
}


class BrandResolver:
    """Turns a :class:`Brand` into a :class:`TokenSet`."""

    def resolve(self, brand: Brand, **overrides: Any) -> TokenSet:
        """Resolve ``brand``.

        ``overrides`` are applied last and are for *project* overlays — a
        competition board that needs a larger display size, say. They cannot
        introduce a token the brand does not define: an overlay is a change of
        value, never a change of vocabulary.
        """
        b = TokenBuilder()
        self._meta(b, brand)
        self._typography(b, brand)
        self._colour(b, brand)
        self._spacing(b, brand)
        self._grid(b, brand)
        self._stroke(b, brand)
        self._tone(b, brand)
        self._surface(b, brand)
        self._render(b, brand)
        self._diagram(b, brand)
        self._voice(b, brand)
        self._assets(b, brand)

        tokens = b.build(
            brand_id=str(brand.brand_id), brand_version=brand.version
        )
        if overrides:
            tokens = self._apply_overrides(tokens, overrides)
        return tokens

    # ------------------------------------------------------------------

    @staticmethod
    def _apply_overrides(tokens: TokenSet, overrides: dict[str, Any]) -> TokenSet:
        from brand.models.tokens import Token

        unknown = [k for k in overrides if k not in tokens]
        if unknown:
            raise ValueError(
                "override names a token the brand does not define: "
                + ", ".join(sorted(unknown))
                + ". An overlay changes a value, not the vocabulary."
            )
        patched = dict(tokens)
        for k, v in overrides.items():
            base = tokens[k]
            patched[k] = Token(
                name=k, value=v, unit=base.unit,
                source=f"{base.source} (project override)",
                constraint=base.constraint,
            )
        return TokenSet(
            patched, brand_id=tokens.brand_id, brand_version=tokens.brand_version
        )

    # -- namespaces ----------------------------------------------------

    def _meta(self, b: TokenBuilder, brand: Brand) -> None:
        b.add("meta.brand.name", brand.identity.name, Unit.STRING, source="identity.name")
        b.add("meta.brand.version", brand.version, Unit.STRING, source="version")
        b.add("meta.brand.status", brand.status.value, Unit.STRING, source="status")
        b.add("meta.brand.id", str(brand.brand_id), Unit.STRING, source="brand_id")
        b.add(
            "meta.ados.edition", brand.ados_edition, Unit.STRING,
            source="ados_edition",
            constraint="a brand conforms relative to an edition",
        )
        b.add(
            "meta.brand.descriptor", brand.identity.descriptor, Unit.STRING,
            source="identity.descriptor",
        )
        b.add("meta.brand.tagline", brand.identity.tagline, Unit.STRING,
              source="identity.tagline")

    def _typography(self, b: TokenBuilder, brand: Brand) -> None:
        typo = brand.visual_identity.typography
        faces: dict[str, FontFace | None] = {
            "primary": typo.primary_font,
            "secondary": typo.secondary_font,
            "mono": typo.mono_font,
        }
        for role, face in faces.items():
            if face is None:
                continue
            b.add(f"font.family.{role}", face.family, Unit.STRING,
                  source=f"visual_identity.typography.{role}_font.family")
            b.add(f"font.fallback.{role}", face.fallback, Unit.STRING,
                  source=f"visual_identity.typography.{role}_font.fallback")
            b.add(f"font.cap_ratio.{role}", face.cap_height_ratio, Unit.RATIO,
                  source=f"visual_identity.typography.{role}_font.cap_height_ratio")

        steps = ados.type_steps()
        bound = self._bound_roles(brand)
        primary_ratio = typo.primary_font.cap_height_ratio

        for token_name, default_step in DEFAULT_TYPE_ROLES.items():
            role_name = token_name.rsplit(".", 1)[1]
            role = bound.get(role_name)
            step = role.step if role else default_step
            cap_mm = steps[step]
            face_ratio = self._ratio_for(typo, role.face if role else "primary",
                                         primary_ratio)
            b.add(token_name, cap_mm, Unit.MM,
                  source=f"typography role {role_name} → ADOS step {step}",
                  constraint="ADOS-2.4.020 type scale")
            b.add(f"{token_name}.pt", round(cap_mm / face_ratio / _MM_PER_PT, 2),
                  Unit.PT,
                  source=f"derived: {cap_mm} mm cap ÷ {face_ratio} cap-ratio",
                  constraint="ADOS-2.4.020 — point size is derived, never chosen")
            b.add(f"{token_name}.step", step, Unit.STRING,
                  source=f"typography role {role_name}")

        for weight_name, value in (("regular", 400), ("medium", 500), ("bold", 700)):
            available = typo.primary_font.weights
            resolved = value if value in available else min(
                available, key=lambda w: abs(w - value)
            )
            b.add(f"font.weight.{weight_name}", resolved, Unit.COUNT,
                  source="visual_identity.typography.primary_font.weights")

        b.add("line_height.body", typo.line_height_factor, Unit.RATIO,
              source="visual_identity.typography.line_height_factor")
        b.add("line_height.baseline", typo.baseline_mm, Unit.MM,
              source="visual_identity.typography.baseline_mm",
              constraint="ADOS-3.3.030 sub-module lattice")
        b.add("letter_spacing.uppercase",
              self._uppercase_tracking(brand), Unit.PERCENT,
              source="typography roles with uppercase=True")
        b.add("letter_spacing.body", 0.0, Unit.PERCENT, source="constant")

    @staticmethod
    def _bound_roles(brand: Brand) -> dict[str, Any]:
        typo = brand.visual_identity.typography
        merged: dict[str, Any] = {}
        for group in (typo.body_styles, typo.heading_styles, typo.numeric_styles):
            merged.update(group)
        return merged

    @staticmethod
    def _ratio_for(typo, face_name: str, default: float) -> float:
        face = {
            "primary": typo.primary_font,
            "secondary": typo.secondary_font,
            "mono": typo.mono_font,
        }.get(face_name)
        return face.cap_height_ratio if face is not None else default

    @staticmethod
    def _uppercase_tracking(brand: Brand) -> float:
        roles = BrandResolver._bound_roles(brand).values()
        upper = [r.tracking_percent for r in roles if r.uppercase]
        return max(upper) if upper else 2.0

    def _colour(self, b: TokenBuilder, brand: Brand) -> None:
        c = brand.visual_identity.colour
        pairs = {
            "color.brand.primary": ("primary", c.primary),
            "color.brand.secondary": ("secondary", c.secondary),
            "color.brand.accent": ("accent", c.accent),
            "color.background": ("background", c.background),
            "color.surface": ("surface", c.surface),
            "color.text.primary": ("text_primary", c.text_primary),
            "color.text.secondary": ("text_secondary", c.text_secondary),
            "color.border": ("border", c.border),
            "color.semantic.success": ("semantic.success", c.semantic.success),
            "color.semantic.warning": ("semantic.warning", c.semantic.warning),
            "color.semantic.error": ("semantic.error", c.semantic.error),
            "color.semantic.info": ("semantic.info", c.semantic.info),
        }
        for name, (field_path, value) in pairs.items():
            b.add(name, value, Unit.HEX,
                  source=f"visual_identity.colour.{field_path}")
        for i, value in enumerate(c.neutral):
            b.add(f"color.neutral.{i}", value, Unit.HEX,
                  source=f"visual_identity.colour.neutral[{i}]")

        # Monochrome equivalents. Every ADOS drawing output is greyscale, so a
        # consumer that plots must be able to ask for the grey a brand colour
        # becomes rather than deriving it — and getting it wrong.
        from brand import colour as _c

        for name in ("color.brand.primary", "color.brand.accent",
                     "color.text.primary", "color.text.secondary"):
            b.add(f"{name}.mono", _c.to_greyscale_hex(pairs[name][1]), Unit.HEX,
                  source=f"derived from {name}",
                  constraint="ADOS-3.8.010 — drawings are monochrome")

    def _spacing(self, b: TokenBuilder, brand: Brand) -> None:
        s = brand.visual_identity.spacing
        b.add("space.base", s.base_unit_mm, Unit.MM,
              source="visual_identity.spacing.base_unit_mm",
              constraint="ADOS-3.3.030 sub-module")
        for i, factor in enumerate(s.scale, start=1):
            b.add(f"space.{i}", round(s.base_unit_mm * factor, 3), Unit.MM,
                  source=f"visual_identity.spacing.scale[{i - 1}] × base")
        b.add("space.margin", s.margin_mm, Unit.MM,
              source="visual_identity.spacing.margin_mm")

    def _grid(self, b: TokenBuilder, brand: Brand) -> None:
        g = brand.visual_identity.grid
        b.add("grid.columns", g.columns, Unit.COUNT, source="visual_identity.grid.columns")
        b.add("grid.gutter", g.gutter_mm, Unit.MM, source="visual_identity.grid.gutter_mm")
        b.add("grid.margin", g.margin_mm, Unit.MM, source="visual_identity.grid.margin_mm")
        b.add("grid.baseline", g.baseline_mm, Unit.MM,
              source="visual_identity.grid.baseline_mm",
              constraint="ADOS-3.3.030")
        b.add("grid.module", g.module_mm, Unit.MM, source="visual_identity.grid.module_mm")

    def _stroke(self, b: TokenBuilder, brand: Brand) -> None:
        lw = brand.architectural_language.drawing.lineweights
        mapping = {
            "stroke.cut": ("cut_mm", lw.cut_mm),
            "stroke.primary": ("primary_mm", lw.primary_mm),
            "stroke.secondary": ("secondary_mm", lw.secondary_mm),
            "stroke.background": ("background_mm", lw.background_mm),
            "stroke.annotation": ("annotation_mm", lw.annotation_mm),
            "stroke.dimension": ("dimension_mm", lw.dimension_mm),
        }
        for name, (field_path, value) in mapping.items():
            b.add(name, value, Unit.MM,
                  source=f"architectural_language.drawing.lineweights.{field_path}",
                  constraint="ADOS-3.1.010 line tiers; ISO 128 series")
        # tertiary is an alias the generic token vocabulary of §4 asks for; it
        # is the same physical weight as `background`, named for consumers that
        # do not know what a cut plane is.
        b.add("stroke.tertiary", lw.background_mm, Unit.MM,
              source="alias of stroke.background")

    def _tone(self, b: TokenBuilder, brand: Brand) -> None:
        for token, l_star in ados.tone_ladder().items():
            b.add(f"tone.{token}", l_star, Unit.L_STAR,
                  source="ADOS tone ladder",
                  constraint="ADOS-3.7.010 — six steps at 18 ΔL*")
        b.add("tone.max_per_sheet", ados.max_tones_per_sheet(), Unit.COUNT,
              source="ADOS", constraint="ADOS-3.7.030")

    def _surface(self, b: TokenBuilder, brand: Brand) -> None:
        """Radius, shadow and opacity.

        All three are flat by default and that is a decision, not an omission:
        a rounded corner, a shadow and a translucency are three ways of
        implying depth that a printed sheet cannot reproduce, so the drawing
        family gets none of them and the screen family inherits the same
        restraint unless a practice overrides it.
        """
        b.add("radius.none", 0.0, Unit.MM, source="constant")
        b.add("radius.sm", 0.0, Unit.MM,
              source="constant — ADOS documents have square corners")
        b.add("shadow.none", "none", Unit.STRING, source="constant")
        b.add("opacity.full", 1.0, Unit.RATIO, source="constant")
        b.add("opacity.muted", 0.6, Unit.RATIO, source="constant")
        b.add("opacity.watermark", 0.12, Unit.RATIO,
              source="ADOS tone T1 coverage", constraint="ADOS-3.7.010")

    def _render(self, b: TokenBuilder, brand: Brand) -> None:
        r = brand.architectural_language.renders
        b.add("render.lighting", r.lighting.value, Unit.STRING,
              source="architectural_language.renders.lighting")
        b.add("render.mood", r.mood.value, Unit.STRING,
              source="architectural_language.renders.mood")
        b.add("render.contrast", r.contrast, Unit.RATIO,
              source="architectural_language.renders.contrast")
        b.add("render.saturation", r.saturation, Unit.RATIO,
              source="architectural_language.renders.saturation")
        b.add("render.camera.focal_length", r.camera.focal_length_mm, Unit.MM,
              source="architectural_language.renders.camera.focal_length_mm")
        b.add("render.camera.sensor_width", r.camera.sensor_width_mm, Unit.MM,
              source="architectural_language.renders.camera.sensor_width_mm")
        b.add("render.camera.height", r.camera.height_m, Unit.STRING,
              source="architectural_language.renders.camera.height_m")
        b.add("render.camera.two_point", r.camera.two_point_perspective, Unit.STRING,
              source="architectural_language.renders.camera.two_point_perspective")
        b.add("render.people", r.people, Unit.STRING,
              source="architectural_language.renders.people")
        b.add("render.sky", r.sky, Unit.STRING,
              source="architectural_language.renders.sky")
        b.add("render.material_expression", list(r.material_expression), Unit.STRING,
              source="architectural_language.renders.material_expression")

    def _diagram(self, b: TokenBuilder, brand: Brand) -> None:
        d = brand.architectural_language.diagrams
        b.add("diagram.style", d.style.value, Unit.STRING,
              source="architectural_language.diagrams.style")
        b.add("diagram.projection", d.projection.value, Unit.STRING,
              source="architectural_language.diagrams.projection")
        b.add("diagram.stroke", d.stroke_mm, Unit.MM,
              source="architectural_language.diagrams.stroke_mm")
        b.add("diagram.fill_tones", list(d.fill_tones), Unit.STRING,
              source="architectural_language.diagrams.fill_tones",
              constraint="ADOS-3.7.030 — at most four tones per sheet")
        palette = list(d.palette) or [
            brand.visual_identity.colour.primary,
            brand.visual_identity.colour.accent,
        ]
        b.add("diagram.palette", palette, Unit.HEX,
              source="architectural_language.diagrams.palette "
                     "(brand palette where empty)")

    def _voice(self, b: TokenBuilder, brand: Brand) -> None:
        c = brand.communication
        b.add("voice.tone", c.tone.value, Unit.STRING, source="communication.tone")
        b.add("voice.person", c.person.value, Unit.STRING, source="communication.person")
        b.add("voice.sentence_max", c.sentence_length_max, Unit.COUNT,
              source="communication.sentence_length_max")
        b.add("voice.language", c.primary_language, Unit.STRING,
              source="communication.primary_language")
        b.add("voice.date_format", c.date_format, Unit.STRING,
              source="communication.date_format")
        b.add("voice.forbidden", list(c.forbidden_words), Unit.STRING,
              source="communication.forbidden_words")
        b.add("voice.terminology", dict(c.terminology), Unit.STRING,
              source="communication.terminology")

    def _assets(self, b: TokenBuilder, brand: Brand) -> None:
        logo = brand.visual_identity.logo
        b.add("asset.logo.primary", logo.primary.path, Unit.STRING,
              source="visual_identity.logo.primary.path")
        b.add("asset.logo.min_width", logo.primary.min_width_mm, Unit.MM,
              source="visual_identity.logo.primary.min_width_mm")
        b.add("asset.logo.clear_space", logo.usage_rules.clear_space_factor,
              Unit.RATIO, source="visual_identity.logo.usage_rules.clear_space_factor",
              constraint="ADOS-3.4.080 clear zone")
        b.add("asset.logo.wordmark", logo.wordmark_text or brand.identity.name,
              Unit.STRING, source="visual_identity.logo.wordmark_text")
        b.add("asset.logo.monochrome_only", logo.usage_rules.monochrome_only,
              Unit.STRING, source="visual_identity.logo.usage_rules.monochrome_only")
