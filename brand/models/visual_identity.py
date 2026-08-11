"""
brand/models/visual_identity.py

The visual half of a brand: logo, typography, colour, spacing, grid, imagery.

Every dimensional field here is in **millimetres**, matching ADOS and PTS.
Screen sizes are derived at resolve time, not authored — a brand that carries
both a millimetre and a pixel value for the same thing has two sources of
truth for it, and they diverge.

Typography is authored as **cap height**, never as point size. Point size is a
property of a font file, cap height is a property of the reader's eye, and
ADOS derives everything from the latter (``ADOS-2.4.020``). The resolver
converts.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from brand import colour as _colour

_Frozen = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


def _validate_hex(v: str) -> str:
    if not _colour.is_hex(v):
        raise ValueError(f"expected a hex colour like '#111111', got {v!r}")
    return v.lower()


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------


class LogoAsset(BaseModel):
    """One logo file plus the geometry needed to place it correctly."""

    model_config = _Frozen

    path: str = Field(
        default="",
        description="Repository- or storage-relative path. Empty = not supplied "
        "yet; the brand is still valid, the asset check reports it.",
    )
    format: str = Field(default="svg", pattern=r"^(svg|pdf|eps|png)$")
    min_width_mm: float = Field(
        default=20.0, gt=0,
        description="Below this the mark stops resolving in print.",
    )
    aspect_ratio: float | None = Field(default=None, gt=0)


class LogoUsageRules(BaseModel):
    """The rules that keep a mark legible wherever it lands."""

    model_config = _Frozen

    clear_space_factor: float = Field(
        default=1.0, ge=0,
        description="Clear space as a multiple of the mark's cap height or "
        "x-dimension. ADOS-3.4.080 applies the same idea to text.",
    )
    permitted_backgrounds: tuple[str, ...] = Field(default=("T0", "T1"))
    monochrome_only: bool = Field(
        default=True,
        description="True for every ADOS drawing output; a colour mark on a "
        "plotted sheet is a mark that prints as an indeterminate grey.",
    )
    prohibited: tuple[str, ...] = Field(
        default=("rotation", "outline", "shadow", "gradient", "stretch"),
    )


class LogoConstruction(BaseModel):
    """The geometry the logo generator draws from.

    These live on the brand rather than inside the generator because a mark
    whose proportions are hard-coded in the code that draws it is a mark the
    practice does not own. Everything is expressed in **modules** — the same
    lattice the sheets are set on — so the logo is constructed on the grid the
    rest of the identity uses rather than on a private one.
    """

    model_config = _Frozen

    module_mm: float = Field(
        default=5.0, gt=0,
        description="The construction unit. Defaults to the ADOS sub-module.",
    )
    cap_modules: float = Field(
        default=2.0, gt=0,
        description="Wordmark cap height, in modules.",
    )
    field_modules: float = Field(
        default=6.0, gt=0,
        description="Side of the square field the symbol is constructed in.",
    )
    aperture_stroke_modules: float = Field(
        default=1.0, gt=0,
        description="Wall thickness of the aperture device, in modules.",
    )
    letter_gap_modules: float = Field(
        default=1.0, ge=0,
        description="Gap between the symbol and the wordmark.",
    )
    tracking_percent: float = Field(
        default=6.0, ge=-5.0, le=40.0,
        description="Wordmark tracking. Looser than body tracking: a wordmark "
        "is read as a shape once, not as words repeatedly.",
    )


class Logo(BaseModel):
    model_config = _Frozen

    primary: LogoAsset = Field(default_factory=LogoAsset)
    secondary: LogoAsset | None = Field(default=None)
    symbol: LogoAsset | None = Field(
        default=None, description="The mark without the wordmark.",
    )
    wordmark_text: str = Field(default="", max_length=120)
    monogram_text: str = Field(
        default="", max_length=8,
        description="The short form. Empty means the initials of the wordmark.",
    )
    construction: LogoConstruction = Field(default_factory=LogoConstruction)
    concept: str = Field(
        default="", max_length=600,
        description="What the mark is doing, in one paragraph. Carried on the "
        "brand so the guidelines are generated rather than written twice.",
    )
    incorrect_uses: tuple[str, ...] = Field(
        default=(
            "Do not rotate the mark.",
            "Do not outline, emboss or shadow it.",
            "Do not stretch or condense it.",
            "Do not re-set the wordmark in another face.",
            "Do not place it on a tone darker than the permitted backgrounds.",
            "Do not reduce it below the stated minimum width.",
        ),
    )
    usage_rules: LogoUsageRules = Field(default_factory=LogoUsageRules)


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------


class FontClass(str, Enum):
    GROTESK = "grotesk"
    NEO_GROTESK = "neo-grotesk"
    GEOMETRIC = "geometric"
    HUMANIST = "humanist"
    TRANSITIONAL_SERIF = "transitional-serif"
    EDITORIAL_SERIF = "editorial-serif"
    SLAB = "slab"
    MONO = "mono"


class FontFace(BaseModel):
    """A family the practice has licensed, with what is needed to set it."""

    model_config = _Frozen

    family: str = Field(min_length=1, max_length=120)
    classification: FontClass = Field(default=FontClass.GROTESK)
    cap_height_ratio: float = Field(
        default=0.72, gt=0.4, lt=1.0,
        description="Cap height as a fraction of the em. Measured from the "
        "font binary (OS/2.sCapHeight ÷ unitsPerEm), not guessed: families "
        "differ by up to 8 %% and every point size is derived from it.",
    )
    fallback: str = Field(
        default="Arial",
        description="Substituted when the family is absent. Word has no "
        "fallback chain, so an unstated fallback becomes a serif.",
    )
    weights: tuple[int, ...] = Field(default=(400, 500, 700))
    licensed: bool = Field(default=True)


class RoleClass(str, Enum):
    """What a typographic role carries, which sets its legibility floor.

    ADOS has two floors, not one (``ADOS-2.4.010``): 2.5 mm cap for anything
    the reader must be able to act on, and 1.8 mm for provenance — the
    copyright line, the conformance statement, a photo credit. A role has to
    declare which it is, because the floor cannot be inferred from a name: one
    practice's ``caption`` is a figure legend and another's is a credit.
    """

    PRIMARY = "primary"        # content: 2.5 mm cap floor
    TERTIARY = "tertiary"      # provenance and legal: 1.8 mm floor


class TypeRole(BaseModel):
    """One typographic role bound to a step of the ADOS type scale."""

    model_config = _Frozen

    role_class: RoleClass = Field(
        default=RoleClass.PRIMARY,
        description="Sets which ADOS cap-height floor applies. Default is the "
        "stricter one: a role that has not thought about it is content.",
    )
    step: str = Field(
        pattern=r"^t[1-8]$",
        description="A step of the ADOS type scale (ADOS-2.4.020). The cap "
        "height comes from the standard; the brand chooses which step a role "
        "sits on, not what the step measures.",
    )
    face: str = Field(
        default="primary", pattern=r"^(primary|secondary|mono)$",
    )
    weight: int = Field(default=400, ge=100, le=900)
    uppercase: bool = Field(default=False)
    tracking_percent: float = Field(default=0.0, ge=-5.0, le=20.0)


class Typography(BaseModel):
    model_config = _Frozen

    primary_font: FontFace
    secondary_font: FontFace | None = Field(default=None)
    mono_font: FontFace | None = Field(
        default=None,
        description="Identifiers, container IDs, clause numbers. A "
        "proportional face makes two identifiers of equal length look unequal.",
    )
    heading_styles: dict[str, TypeRole] = Field(default_factory=dict)
    body_styles: dict[str, TypeRole] = Field(default_factory=dict)
    numeric_styles: dict[str, TypeRole] = Field(default_factory=dict)
    baseline_mm: float = Field(
        default=5.0, gt=0,
        description="Baseline pitch. Defaults to the ADOS sub-module.",
    )
    line_height_factor: float = Field(default=1.42, ge=1.0, le=2.5)


# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------


class SemanticColours(BaseModel):
    """Status colours. ADOS permits colour only where it is redundant."""

    model_config = _Frozen

    success: str = Field(default="#2f6f4f")
    warning: str = Field(default="#8a6a1f")
    error: str = Field(default="#8a2f2f")
    info: str = Field(default="#2f5f8a")

    _v = field_validator("success", "warning", "error", "info")(_validate_hex)


class ColourSystem(BaseModel):
    """The palette.

    ``primary`` is the ink the practice signs its name in; on a drawing it is
    black, and the brand primary is what appears on everything that is not a
    drawing. ``neutral`` is the grey ramp; it is checked against the ADOS tone
    ladder rather than being free.
    """

    model_config = _Frozen

    primary: str = Field(default="#111111")
    secondary: str = Field(default="#5a5a5a")
    accent: str = Field(default="#b8a88a")
    background: str = Field(default="#ffffff")
    surface: str = Field(default="#f6f5f2")
    text_primary: str = Field(default="#111111")
    text_secondary: str = Field(default="#5a5a5a")
    border: str = Field(default="#d8d5cf")
    neutral: tuple[str, ...] = Field(
        default=("#ffffff", "#e8e6e1", "#c4c1ba", "#8d8a84", "#4c4a46", "#1c1b19"),
        description="Light to dark. Checked against the ADOS tone ladder.",
    )
    semantic: SemanticColours = Field(default_factory=SemanticColours)

    _v = field_validator(
        "primary", "secondary", "accent", "background", "surface",
        "text_primary", "text_secondary", "border",
    )(_validate_hex)

    @field_validator("neutral")
    @classmethod
    def _check_ramp(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for c in v:
            _validate_hex(c)
        return tuple(c.lower() for c in v)


# ---------------------------------------------------------------------------
# Spacing and grid
# ---------------------------------------------------------------------------


class Spacing(BaseModel):
    """The spacing scale.

    Authored as multipliers of a base unit rather than as absolute values, so
    that the whole scale moves coherently when the base does.
    """

    model_config = _Frozen

    base_unit_mm: float = Field(default=5.0, gt=0)
    scale: tuple[float, ...] = Field(
        default=(1, 2, 4, 8),
        description="Multipliers of the base unit. ADOS-3.3.040 wants a "
        "between-group gap of at least twice the within-group gap, which a "
        "doubling scale gives for free.",
    )
    margin_mm: float = Field(default=10.0, ge=0)

    @field_validator("scale")
    @classmethod
    def _ascending(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if len(v) < 2:
            raise ValueError("a spacing scale needs at least two steps")
        if list(v) != sorted(v) or len(set(v)) != len(v):
            raise ValueError("spacing scale must be strictly ascending")
        return v


class GridConfig(BaseModel):
    """One format's column configuration.

    A single column count cannot serve A4 and a competition board: at A4 six
    columns give a 20 mm measure that nothing fits in, and at A1 four columns
    give a measure no one can read a line of. The system is one lattice with
    per-format column counts, not one grid stretched.
    """

    model_config = _Frozen

    columns: int = Field(ge=1, le=24)
    gutter_mm: float = Field(ge=0)
    margin_mm: float = Field(ge=0)
    measure_mm: float | None = Field(
        default=None, gt=0,
        description="Target text measure. ADOS-3.6.010 wants 45-75 characters; "
        "at a 2.5 mm cap that is roughly 90-150 mm.",
    )


class Grid(BaseModel):
    model_config = _Frozen

    columns: int = Field(default=6, ge=1, le=24)
    gutter_mm: float = Field(default=10.0, ge=0)
    margin_mm: float = Field(default=20.0, ge=0)
    baseline_mm: float = Field(default=5.0, gt=0)
    module_mm: float = Field(default=10.0, gt=0)
    configurations: dict[str, GridConfig] = Field(
        default_factory=dict,
        description="Per-format overrides, keyed by format name (A4, A3, "
        "slide, board, portfolio). The fields above are the default.",
    )

    def for_format(self, name: str) -> GridConfig:
        """The configuration for a format, falling back to the default."""
        if name in self.configurations:
            return self.configurations[name]
        return GridConfig(
            columns=self.columns, gutter_mm=self.gutter_mm,
            margin_mm=self.margin_mm,
        )


# ---------------------------------------------------------------------------
# Imagery
# ---------------------------------------------------------------------------


class GraphicPrimitive(BaseModel):
    """One repeatable mark in the identity's graphic vocabulary.

    The test of an identity is whether it is recognisable with the logo
    removed. That recognition comes from a small set of marks used
    consistently — a frame, a rule, a corner tick — not from the mark itself,
    which appears once per document.
    """

    model_config = _Frozen

    key: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=300)
    stroke_tier: str = Field(
        default="secondary",
        pattern=r"^(cut|primary|secondary|background|annotation|dimension)$",
        description="Which lineweight it is drawn at. Named rather than "
        "measured so the primitive follows the drawing language.",
    )
    modules: float = Field(
        default=1.0, gt=0, description="Size in modules where it has one.",
    )


class CornerTreatment(str, Enum):
    SQUARE = "square"
    ROUNDED = "rounded"


class GraphicLanguage(BaseModel):
    """The identity with the logo taken away.

    Everything here is a *rule about marks*, not a mark: the stroke tiers come
    from the drawing language so that a rule on a report and a rule on a plan
    are the same weight, and the corner treatment is one decision applied
    everywhere rather than a per-artefact choice.
    """

    model_config = _Frozen

    corner: CornerTreatment = Field(
        default=CornerTreatment.SQUARE,
        description="Square by default. A radius is a value that has to be "
        "held identical in six output formats and never is.",
    )
    rule_tier: str = Field(default="annotation", max_length=20)
    emphasis_rule_tier: str = Field(default="primary", max_length=20)
    frame_stroke_tier: str = Field(default="secondary", max_length=20)
    image_frame: bool = Field(
        default=True,
        description="Images sit inside a drawn frame rather than bleeding. "
        "A sheet is read by its frame.",
    )
    image_caption_position: str = Field(
        default="below-left", pattern=r"^(below-left|below-right|inside|none)$",
    )
    separator_spacing_modules: float = Field(default=2.0, gt=0)
    primitives: tuple[GraphicPrimitive, ...] = Field(default=())
    notes: str = Field(default="", max_length=600)


class ColourTreatment(str, Enum):
    NATURAL = "natural"
    DESATURATED = "desaturated"
    MONOCHROME = "monochrome"
    WARM = "warm"
    COOL = "cool"


class Imagery(BaseModel):
    """How photographs and renders are made and treated."""

    model_config = _Frozen

    photography: str = Field(default="", max_length=400)
    render_style: str = Field(default="", max_length=400)
    composition: tuple[str, ...] = Field(default=())
    colour_treatment: ColourTreatment = Field(default=ColourTreatment.NATURAL)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)
    aspect_ratios: tuple[str, ...] = Field(default=("3:2", "1:1"))
    perspective: str = Field(
        default="frontal", max_length=80,
        description="The default viewpoint. 'frontal' and 'one-point' read as "
        "measured; a three-quarter view reads as a photograph of an object.",
    )
    verticals_corrected: bool = Field(
        default=True,
        description="Converging verticals read as a snapshot of a building "
        "rather than a record of one.",
    )
    human_presence: str = Field(
        default="incidental",
        pattern=r"^(none|incidental|inhabited|staged)$",
    )
    cropping: str = Field(
        default="full-frame", max_length=120,
        description="How images are cut. 'full-frame' means the frame is the "
        "photographer's, not the layout's.",
    )
    sequencing: tuple[str, ...] = Field(
        default=(),
        description="The order a project is shown in — context, approach, "
        "threshold, interior, detail. A portfolio spread is a sequence, and "
        "an unstated sequence is re-invented per project.",
    )
    detail_ratio: float = Field(
        default=0.25, ge=0.0, le=1.0,
        description="Share of images that are detail shots. Materiality is "
        "carried by the close view; a set of only wide shots reads as CGI.",
    )
    bleed: bool = Field(
        default=False,
        description="False on every technical sheet: an image running to the "
        "trim has no frame, and a sheet is read by its frame.",
    )


class VisualIdentity(BaseModel):
    model_config = _Frozen

    logo: Logo = Field(default_factory=Logo)
    typography: Typography
    colour: ColourSystem = Field(default_factory=ColourSystem)
    spacing: Spacing = Field(default_factory=Spacing)
    grid: Grid = Field(default_factory=Grid)
    imagery: Imagery = Field(default_factory=Imagery)
    graphic_language: GraphicLanguage = Field(default_factory=GraphicLanguage)
