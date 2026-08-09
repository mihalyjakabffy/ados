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


class Logo(BaseModel):
    model_config = _Frozen

    primary: LogoAsset = Field(default_factory=LogoAsset)
    secondary: LogoAsset | None = Field(default=None)
    symbol: LogoAsset | None = Field(
        default=None, description="The mark without the wordmark.",
    )
    wordmark_text: str = Field(default="", max_length=120)
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


class Grid(BaseModel):
    model_config = _Frozen

    columns: int = Field(default=6, ge=1, le=24)
    gutter_mm: float = Field(default=10.0, ge=0)
    margin_mm: float = Field(default=20.0, ge=0)
    baseline_mm: float = Field(default=5.0, gt=0)
    module_mm: float = Field(default=10.0, gt=0)


# ---------------------------------------------------------------------------
# Imagery
# ---------------------------------------------------------------------------


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
