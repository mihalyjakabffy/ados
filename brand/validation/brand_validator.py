"""
brand/validation/brand_validator.py

Checks a brand against itself, against good practice, and against ADOS.

Three categories, in increasing order of what they know:

``structural``
    The brand is incomplete or internally contradictory. A missing primary
    font, a duplicate token, a hierarchy that lists a layer twice. Cheap,
    certain, and mostly caught by pydantic already — what remains here is what
    a type system cannot say.

``consistency``
    The brand is well-formed but will not hold together in use. An accent that
    is not distinct from the primary, a spacing scale that does not separate
    groups from members, a heading hierarchy where two levels share a step.

``architectural``
    The brand contradicts the standard it claims to conform to. A cut line
    lighter than a projection line, body text below the cap-height floor, a
    diagram palette outside the declared brand palette, text contrast below
    the ADOS floor. These are the ones a generic branding tool cannot see,
    and they are the ones that produce an unreadable drawing.

Severity follows ``core/rules/dsl.py`` so that brand findings and standards
findings can be presented in one list.

Every finding names the field, says what is wrong, and proposes a fix. A
validator that reports a problem without a remedy just moves the work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from brand import ados
from brand import colour as _colour
from brand.models.brand import Brand
from brand.models.identity import Identity


class Severity(str, Enum):
    """Aligned with ``core.rules.dsl.Severity``."""

    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    BLOCK = "BLOCK"


class Category(str, Enum):
    STRUCTURAL = "structural"
    CONSISTENCY = "consistency"
    ARCHITECTURAL = "architectural"


_ORDER = {Severity.BLOCK: 0, Severity.ERROR: 1, Severity.WARN: 2, Severity.INFO: 3}


@dataclass(frozen=True)
class Finding:
    """One thing wrong with a brand."""

    severity: Severity
    category: Category
    field: str
    message: str
    suggestion: str = ""
    rule: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.severity.value.lower(),
            "severity": self.severity.value,
            "category": self.category.value,
            "field": self.field,
            "message": self.message,
            "suggestion": self.suggestion,
            "rule": self.rule,
        }


@dataclass
class ValidationReport:
    """The result of validating one brand."""

    brand_label: str = ""
    findings: list[Finding] = field(default_factory=list)

    # -- predicates -----------------------------------------------------
    @property
    def ok(self) -> bool:
        """True when nothing blocks publication.

        ``WARN`` does not block: a practice is allowed to make a considered
        choice the system would not have made, and a validator that refuses
        that is a validator people route around.
        """
        return not any(f.severity in (Severity.BLOCK, Severity.ERROR) for f in self.findings)

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.BLOCK]

    def by_severity(self, severity: Severity) -> list[Finding]:
        return [f for f in self.findings if f.severity is severity]

    def by_category(self, category: Category) -> list[Finding]:
        return [f for f in self.findings if f.category is category]

    def sorted(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: (_ORDER[f.severity], f.field))

    # -- output ---------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "brand": self.brand_label,
            "ok": self.ok,
            "counts": {
                s.value: len(self.by_severity(s)) for s in Severity
            },
            "findings": [f.to_dict() for f in self.sorted()],
        }

    def summary(self) -> str:
        if not self.findings:
            return f"{self.brand_label}: clean."
        counts = ", ".join(
            f"{len(self.by_severity(s))} {s.value.lower()}"
            for s in Severity
            if self.by_severity(s)
        )
        return f"{self.brand_label}: {counts}."

    def __len__(self) -> int:                              # pragma: no cover
        return len(self.findings)


class BrandValidator:
    """Runs every check. Stateless; safe to reuse."""

    def validate(self, brand: Brand) -> ValidationReport:
        report = ValidationReport(brand_label=brand.label)
        add = report.findings.append
        for finding in self._all_checks(brand):
            add(finding)
        return report

    def _all_checks(self, brand: Brand) -> Iterable[Finding]:
        yield from self._structural(brand)
        yield from self._consistency(brand)
        yield from self._architectural(brand)

    # ==================================================================
    # Structural
    # ==================================================================

    def _structural(self, brand: Brand) -> Iterable[Finding]:
        ident: Identity = brand.identity
        typo = brand.visual_identity.typography

        if not typo.primary_font.family.strip():
            yield Finding(
                Severity.BLOCK, Category.STRUCTURAL,
                "visual_identity.typography.primary_font.family",
                "No primary font family.",
                "Every derived point size comes from a face's measured cap "
                "height; without a face there is no type scale to resolve.",
            )

        if not ident.descriptor and not ident.positioning:
            yield Finding(
                Severity.WARN, Category.STRUCTURAL, "identity",
                "Neither a descriptor nor a positioning statement is set.",
                "A cover sheet and a proposal both need one line saying what "
                "the practice does; without it the templates render a gap.",
            )

        if not ident.personality:
            yield Finding(
                Severity.INFO, Category.STRUCTURAL, "identity.personality",
                "No personality axes declared.",
                "The render and diagram languages take their defaults from "
                "these; without them the defaults are generic.",
            )
        elif len(ident.personality) > 4:
            yield Finding(
                Severity.WARN, Category.CONSISTENCY, "identity.personality",
                f"{len(ident.personality)} personality axes declared.",
                "Two to four. A practice that is eight things is none of them, "
                "and downstream generators weight every axis equally.",
            )

        if not brand.visual_identity.logo.primary.path:
            yield Finding(
                Severity.INFO, Category.STRUCTURAL,
                "visual_identity.logo.primary.path",
                "No primary logo asset.",
                "Templates fall back to the wordmark set in the primary face, "
                "which is valid but is not a mark.",
            )

        if typo.mono_font is None:
            yield Finding(
                Severity.WARN, Category.STRUCTURAL,
                "visual_identity.typography.mono_font",
                "No monospace face declared.",
                "Container identifiers and clause numbers are set in it. In a "
                "proportional face two identifiers of equal length look "
                "unequal, which is how a transmittal gets misread.",
            )

        if not typo.primary_font.licensed:
            yield Finding(
                Severity.ERROR, Category.STRUCTURAL,
                "visual_identity.typography.primary_font.licensed",
                f"{typo.primary_font.family} is marked unlicensed.",
                "Embed-and-issue requires a licence that covers document "
                "embedding. Substitute a licensed face before publishing.",
            )

    # ==================================================================
    # Consistency
    # ==================================================================

    def _consistency(self, brand: Brand) -> Iterable[Finding]:
        c = brand.visual_identity.colour

        # Accent must be distinguishable from primary, or it is not an accent.
        d_accent = _colour.delta_l(c.primary, c.accent)
        min_dl = ados.min_delta_l_between_meanings()
        if d_accent < min_dl:
            yield Finding(
                Severity.WARN, Category.CONSISTENCY,
                "visual_identity.colour.accent",
                f"Accent is ΔL* {d_accent:.1f} from primary, below the "
                f"{min_dl:g} the standard asks of two colours that mean "
                f"different things.",
                "Move the accent's lightness, not only its hue: the pair has "
                "to survive a monochrome plot, where hue is discarded.",
                rule="ADOS colour.min_delta_L_between_meanings",
            )

        # Two brand colours that collapse to the same grey carry no information
        # on a plotted sheet.
        mono_primary = _colour.to_greyscale_hex(c.primary)
        mono_accent = _colour.to_greyscale_hex(c.accent)
        if _colour.delta_l(mono_primary, mono_accent) < ados.min_discriminable_delta_l():
            yield Finding(
                Severity.WARN, Category.CONSISTENCY,
                "visual_identity.colour",
                "Primary and accent collapse to nearly the same grey "
                f"({mono_primary} vs {mono_accent}).",
                "Every drawing output is monochrome. Separate them by "
                "lightness so the distinction survives the plotter.",
                rule="ADOS tone.delta_L_min_discriminable",
            )

        # Spacing scale must separate groups from members (ADOS-3.3.040).
        scale = brand.visual_identity.spacing.scale
        ratios = [b / a for a, b in zip(scale, scale[1:])]
        if ratios and min(ratios) < 2.0:
            worst = min(ratios)
            yield Finding(
                Severity.WARN, Category.CONSISTENCY,
                "visual_identity.spacing.scale",
                f"Adjacent spacing steps differ by only ×{worst:.2f}.",
                "A between-group gap must be at least twice a within-group "
                "gap or the grouping is not read as grouping. Use a doubling "
                "scale.",
                rule="ADOS-3.3.040",
            )

        # Heading hierarchy: two levels on the same step are one level.
        headings = brand.visual_identity.typography.heading_styles
        steps_used: dict[str, list[str]] = {}
        for name, role in headings.items():
            steps_used.setdefault(role.step, []).append(name)
        for step, names in steps_used.items():
            if len(names) > 1:
                yield Finding(
                    Severity.WARN, Category.CONSISTENCY,
                    "visual_identity.typography.heading_styles",
                    f"Heading levels {', '.join(sorted(names))} all sit on "
                    f"step {step}.",
                    "Levels the reader cannot tell apart are one level. Move "
                    "them onto separate steps of the scale, or merge them.",
                )

        # Baseline and grid baseline must agree.
        typo_baseline = brand.visual_identity.typography.baseline_mm
        grid_baseline = brand.visual_identity.grid.baseline_mm
        if abs(typo_baseline - grid_baseline) > 1e-6:
            yield Finding(
                Severity.ERROR, Category.CONSISTENCY,
                "visual_identity.grid.baseline_mm",
                f"Typography baseline is {typo_baseline} mm but the grid "
                f"baseline is {grid_baseline} mm.",
                "They are the same quantity held twice. Set both to the "
                "sub-module, or text will not sit on the grid it is set against.",
            )

        # Forbidden words that the brand itself uses.
        forbidden = {w.lower() for w in brand.communication.forbidden_words}
        if forbidden:
            prose = " ".join(
                [
                    brand.identity.descriptor,
                    brand.identity.tagline,
                    brand.identity.positioning,
                    brand.identity.mission,
                    brand.identity.vision,
                ]
            ).lower()
            used = sorted(w for w in forbidden if w and w in prose)
            if used:
                yield Finding(
                    Severity.WARN, Category.CONSISTENCY,
                    "communication.forbidden_words",
                    f"The brand's own copy uses forbidden words: {', '.join(used)}.",
                    "Either rewrite the copy or drop the words from the list. "
                    "A rule the source of truth breaks will not be kept "
                    "anywhere downstream.",
                )

    # ==================================================================
    # Architectural — the checks a generic branding tool cannot make
    # ==================================================================

    def _architectural(self, brand: Brand) -> Iterable[Finding]:
        yield from self._check_lineweights(brand)
        yield from self._check_type_against_ados(brand)
        yield from self._check_contrast(brand)
        yield from self._check_diagram_palette(brand)
        yield from self._check_tones(brand)
        yield from self._check_grid_lattice(brand)
        yield from self._check_render_coherence(brand)

    def _check_lineweights(self, brand: Brand) -> Iterable[Finding]:
        lw = brand.architectural_language.drawing.lineweights
        f = "architectural_language.drawing.lineweights"

        # The hierarchy must be monotone: weight encodes distance from the cut.
        ordered = [
            ("cut_mm", lw.cut_mm),
            ("primary_mm", lw.primary_mm),
            ("secondary_mm", lw.secondary_mm),
            ("background_mm", lw.background_mm),
        ]
        for (name_a, a), (name_b, b) in zip(ordered, ordered[1:]):
            if b > a:
                yield Finding(
                    Severity.BLOCK, Category.ARCHITECTURAL, f"{f}.{name_b}",
                    f"{name_b} ({b} mm) is heavier than {name_a} ({a} mm): the "
                    f"hierarchy is reversed.",
                    "Line weight encodes distance from the cut plane and must "
                    "decrease monotonically away from it. A reversed pair "
                    "makes the drawing say the opposite of what is built.",
                    rule="ADOS-3.1.010",
                )
            elif b == a:
                yield Finding(
                    Severity.ERROR, Category.ARCHITECTURAL, f"{f}.{name_b}",
                    f"{name_b} equals {name_a} ({a} mm): no hierarchy between them.",
                    f"Separate them by the tier ratio ({ados.line_tier_ratio():g}×). "
                    "Two weights the eye cannot separate are one weight.",
                    rule="ADOS-3.1.020",
                )

        # Every weight on the ISO series.
        series = ados.line_iso_series_mm()
        for name, value in [
            ("cut_mm", lw.cut_mm), ("primary_mm", lw.primary_mm),
            ("secondary_mm", lw.secondary_mm), ("background_mm", lw.background_mm),
            ("annotation_mm", lw.annotation_mm), ("dimension_mm", lw.dimension_mm),
        ]:
            if not any(abs(value - s) < 1e-9 for s in series):
                nearest = min(series, key=lambda s: abs(s - value))
                yield Finding(
                    Severity.WARN, Category.ARCHITECTURAL, f"{f}.{name}",
                    f"{value} mm is not on the ISO 128 line series.",
                    f"Use {nearest} mm. A weight between two series values is "
                    f"rounded by the plotter, so the drawn hierarchy is not "
                    f"the plotted one.",
                    rule="ADOS line.iso_series_mm",
                )
            if value < ados.min_issued_line_mm():
                yield Finding(
                    Severity.ERROR, Category.ARCHITECTURAL, f"{f}.{name}",
                    f"{value} mm is below the {ados.min_issued_line_mm()} mm "
                    f"minimum for an issued line.",
                    "Thinner strokes are eroded by copying and disappear by "
                    "the second generation.",
                    rule="ADOS-3.1.030",
                )

        # Ratio between the two ends of the semantic range.
        want = ados.line_tier_ratio()
        if lw.background_mm > 0:
            spread = lw.cut_mm / lw.background_mm
            if spread < want:
                yield Finding(
                    Severity.WARN, Category.ARCHITECTURAL, f"{f}.cut_mm",
                    f"Cut is only ×{spread:.2f} the background weight.",
                    f"The standard separates adjacent tiers by ×{want:g}; across "
                    f"the full semantic range the spread should be larger, not "
                    f"smaller.",
                    rule="ADOS-3.1.020",
                )

        # Layers the practice says it does not draw, still weighted.
        drawing = brand.architectural_language.drawing
        if not drawing.show_figures and "figures" in [
            layer.value for layer in drawing.hierarchy
        ]:
            yield Finding(
                Severity.INFO, Category.ARCHITECTURAL,
                "architectural_language.drawing.hierarchy",
                "Figures appear in the graphic hierarchy but show_figures is off.",
                "Harmless, but the hierarchy is the thing an Archicad pen set "
                "is generated from — leaving the layer in generates a pen "
                "nothing uses.",
            )

    def _check_type_against_ados(self, brand: Brand) -> Iterable[Finding]:
        typo = brand.visual_identity.typography
        steps = ados.type_steps()
        floor = ados.min_cap_height_mm()
        absolute = ados.absolute_cap_floor_mm()

        all_roles = {
            **{f"body_styles.{k}": v for k, v in typo.body_styles.items()},
            **{f"heading_styles.{k}": v for k, v in typo.heading_styles.items()},
            **{f"numeric_styles.{k}": v for k, v in typo.numeric_styles.items()},
        }
        from brand.models.visual_identity import RoleClass

        for path, role in all_roles.items():
            cap = steps.get(role.step)
            if cap is None:                                # pragma: no cover
                continue
            if cap < absolute:                             # pragma: no cover
                yield Finding(
                    Severity.BLOCK, Category.ARCHITECTURAL,
                    f"visual_identity.typography.{path}",
                    f"Step {role.step} = {cap} mm is below the absolute floor "
                    f"of {absolute} mm.",
                    "Nothing may be set smaller than this at any size, for any "
                    "purpose.",
                    rule="ADOS-2.4.010",
                )
            elif role.role_class is RoleClass.PRIMARY and cap < floor:
                yield Finding(
                    Severity.ERROR, Category.ARCHITECTURAL,
                    f"visual_identity.typography.{path}",
                    f"Content role on step {role.step} = {cap} mm cap, below "
                    f"the {floor} mm floor for content.",
                    f"Either move it to t2 ({steps['t2']} mm) or larger, or — "
                    f"if it really is provenance rather than content — declare "
                    f"role_class='tertiary', which lowers the floor to "
                    f"{absolute} mm.",
                    rule="ADOS-2.4.010",
                )

            if role.face == "secondary" and typo.secondary_font is None:
                yield Finding(
                    Severity.ERROR, Category.STRUCTURAL,
                    f"visual_identity.typography.{path}.face",
                    f"Role {path} is set in the secondary face, which is not "
                    f"declared.",
                    "Declare a secondary_font or move the role to the primary.",
                )
            if role.face == "mono" and typo.mono_font is None:
                yield Finding(
                    Severity.ERROR, Category.STRUCTURAL,
                    f"visual_identity.typography.{path}.face",
                    f"Role {path} is set in the mono face, which is not declared.",
                    "Declare a mono_font or move the role to the primary.",
                )

        if abs(typo.baseline_mm % ados.submodule_mm()) > 1e-6:
            yield Finding(
                Severity.WARN, Category.ARCHITECTURAL,
                "visual_identity.typography.baseline_mm",
                f"Baseline {typo.baseline_mm} mm is not a whole sub-module "
                f"({ados.submodule_mm():g} mm).",
                "Text will drift off the placement lattice down the page, "
                "which is visible as a page that will not settle.",
                rule="ADOS-3.3.030",
            )

    def _check_contrast(self, brand: Brand) -> Iterable[Finding]:
        c = brand.visual_identity.colour
        want = ados.text_contrast_ratio_min()
        for label, fg, bg in [
            ("text.primary on background", c.text_primary, c.background),
            ("text.secondary on background", c.text_secondary, c.background),
            ("text.primary on surface", c.text_primary, c.surface),
        ]:
            ratio = _colour.contrast_ratio(fg, bg)
            if ratio < want:
                yield Finding(
                    Severity.ERROR if ratio < 4.5 else Severity.WARN,
                    Category.ARCHITECTURAL, "visual_identity.colour",
                    f"{label}: contrast {ratio:.1f}:1, below the {want:g}:1 floor.",
                    f"Darken {fg} or lighten {bg}. The floor is set for a "
                    f"document read under site lighting and photocopied, not "
                    f"for a screen in an office.",
                    rule="ADOS colour.text_contrast_ratio_min",
                )

        # Text on the brand's own primary — a cover, a banner.
        ratio = _colour.contrast_ratio(c.background, c.primary)
        if ratio < 4.5:
            yield Finding(
                Severity.WARN, Category.ARCHITECTURAL,
                "visual_identity.colour.primary",
                f"Background on primary is only {ratio:.1f}:1.",
                "Reversed-out type on the brand colour will not hold. Either "
                "darken the primary or do not set type on it.",
            )

    def _check_diagram_palette(self, brand: Brand) -> Iterable[Finding]:
        d = brand.architectural_language.diagrams
        if not d.palette:
            return
        c = brand.visual_identity.colour
        declared = {
            c.primary, c.secondary, c.accent, c.background, c.surface,
            c.text_primary, c.text_secondary, c.border,
            *c.neutral,
            c.semantic.success, c.semantic.warning, c.semantic.error, c.semantic.info,
        }
        stray = [p for p in d.palette if p.lower() not in declared]
        if stray:
            yield Finding(
                Severity.ERROR, Category.ARCHITECTURAL,
                "architectural_language.diagrams.palette",
                f"Diagram palette uses colours the brand does not declare: "
                f"{', '.join(stray)}.",
                "Add them to the brand palette or remove them. A diagram in "
                "undeclared colours is the commonest way a set stops looking "
                "like one practice.",
            )

    def _check_tones(self, brand: Brand) -> Iterable[Finding]:
        d = brand.architectural_language.diagrams
        ladder = ados.tone_ladder()
        maximum = ados.max_tones_per_sheet()
        if len(set(d.fill_tones)) > maximum:
            yield Finding(
                Severity.ERROR, Category.ARCHITECTURAL,
                "architectural_language.diagrams.fill_tones",
                f"{len(set(d.fill_tones))} fill tones declared; the standard "
                f"permits {maximum} per sheet.",
                "Working memory holds about four states per channel. A fifth "
                "tone is not read as a fifth meaning.",
                rule="ADOS-3.7.030",
            )
        unknown = [t for t in d.fill_tones if t not in ladder]
        if unknown:                                        # pragma: no cover
            yield Finding(
                Severity.ERROR, Category.ARCHITECTURAL,
                "architectural_language.diagrams.fill_tones",
                f"Unknown tone tokens: {', '.join(unknown)}.",
                f"Use the ladder: {', '.join(sorted(ladder))}.",
            )

        # The brand's neutral ramp against the ladder.
        for i, hex_value in enumerate(brand.visual_identity.colour.neutral):
            token, distance = _colour.nearest_tone_token(hex_value, ladder)
            if distance > 8.0:
                yield Finding(
                    Severity.INFO, Category.ARCHITECTURAL,
                    f"visual_identity.colour.neutral[{i}]",
                    f"{hex_value} sits ΔL* {distance:.0f} from the nearest "
                    f"ladder step ({token}).",
                    "Greys that land between rungs reproduce as neither. Snap "
                    "the ramp to the ladder if these greys are used as fills.",
                    rule="ADOS-3.7.010",
                )

    def _check_grid_lattice(self, brand: Brand) -> Iterable[Finding]:
        g = brand.visual_identity.grid
        sub = ados.submodule_mm()
        for name, value in [
            ("gutter_mm", g.gutter_mm), ("margin_mm", g.margin_mm),
            ("module_mm", g.module_mm),
        ]:
            if value and abs(value % sub) > 1e-6:
                yield Finding(
                    Severity.WARN, Category.ARCHITECTURAL,
                    f"visual_identity.grid.{name}",
                    f"{value} mm is not a whole sub-module ({sub:g} mm).",
                    "Everything placed on the sheet is placed on this lattice; "
                    "a grid off the lattice puts every column off it too.",
                    rule="ADOS-3.3.030",
                )
        s = brand.visual_identity.spacing
        if abs(s.base_unit_mm % sub) > 1e-6:
            yield Finding(
                Severity.WARN, Category.ARCHITECTURAL,
                "visual_identity.spacing.base_unit_mm",
                f"Spacing base {s.base_unit_mm} mm is not a whole sub-module.",
                f"Use {sub:g} mm or a multiple.",
                rule="ADOS-3.3.030",
            )

    def _check_render_coherence(self, brand: Brand) -> Iterable[Finding]:
        """Does the render language contradict the stated visual language?

        These are judgements, so they are all WARN or INFO. They exist because
        the contradiction is easy to author and hard to see: a practice writes
        'quiet' in its personality and then sets dramatic, high-contrast,
        fully-saturated renders, and the portfolio does not look like the
        stationery.
        """
        from brand.models.architectural_language import RenderMood
        from brand.models.identity import PersonalityAxis

        r = brand.architectural_language.renders
        axes = set(brand.identity.personality)

        if PersonalityAxis.QUIET in axes and r.mood is RenderMood.DRAMATIC:
            yield Finding(
                Severity.WARN, Category.ARCHITECTURAL,
                "architectural_language.renders.mood",
                "Render mood is 'dramatic' but the practice describes itself "
                "as 'quiet'.",
                "The renders are the most-shared artefact a practice has. "
                "Either the mood or the personality axis is the one that is "
                "not true.",
            )
        if PersonalityAxis.MATERIAL in axes and r.saturation < 0.25:
            yield Finding(
                Severity.WARN, Category.ARCHITECTURAL,
                "architectural_language.renders.saturation",
                f"Saturation {r.saturation} is near-monochrome, but the "
                f"practice describes itself as 'material'.",
                "Material identity is carried largely by colour temperature "
                "and hue variation in the surfaces. Desaturating removes it.",
            )
        if PersonalityAxis.PRECISE in axes and not r.camera.two_point_perspective:
            yield Finding(
                Severity.INFO, Category.ARCHITECTURAL,
                "architectural_language.renders.camera.two_point_perspective",
                "Converging verticals with a 'precise' personality.",
                "Keeping verticals vertical is the render equivalent of an "
                "orthographic drawing, and reads as measured rather than "
                "photographed.",
            )
        if brand.visual_identity.imagery.bleed and brand.applications.drawings:
            yield Finding(
                Severity.WARN, Category.ARCHITECTURAL,
                "visual_identity.imagery.bleed",
                "Imagery is set to bleed, and the brand covers drawings.",
                "A sheet is read by its frame; an image running to the trim "
                "removes it. Turn bleed off for the sheet family.",
                rule="ADOS-3.5.040",
            )
