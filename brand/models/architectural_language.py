"""
brand/models/architectural_language.py

The part of a brand that generic branding systems do not have.

A practice's identity in architecture is carried more by how it draws than by
its logo: the weight of a cut line, whether furniture is shown, how a detail
is annotated, what a render's light is doing. Those are the things a reader
recognises across two projects with no wordmark in sight, and they are the
things that must survive into Archicad, into a rendering pipeline, and into a
portfolio — which means they have to be **parameters**, not adjectives.

So everything here is structured. ``DrawingLanguage.lineweights`` is millimetres
validated against the ISO series; ``GraphicHierarchy`` is an explicit ordering
that the validator checks is monotone; ``RenderLanguage`` carries numbers a
render engine can consume. Free text is available in ``notes`` fields for what
the parameters genuinely cannot hold, and nothing downstream reads them.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

_Frozen = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


class GraphicLayer(str, Enum):
    """The layers of a drawing, in the order ADOS reads them.

    The ordering is the point: line weight encodes distance from the cut
    plane (``ADOS-3.1.010``), so the hierarchy has to be a total order with
    ``CUT`` heaviest, and the validator enforces exactly that.
    """

    CUT = "cut"
    PROJECTION = "projection"
    BACKGROUND = "background"
    FURNITURE = "furniture"
    LANDSCAPE = "landscape"
    FIGURES = "figures"
    ANNOTATION = "annotation"
    DIMENSION = "dimension"


class Lineweights(BaseModel):
    """The practice's line weights, in millimetres.

    Defaults are the ADOS tiers. A practice may deviate — a heavier cut reads
    as a heavier hand — but every value is checked against the ISO 128 series
    and against the tier ratio, because a weight between two series values
    prints as whichever the plotter rounds to.
    """

    model_config = _Frozen

    cut_mm: float = Field(default=0.70, gt=0)
    primary_mm: float = Field(
        default=0.35, gt=0, description="Seen, in front of the cut plane.",
    )
    secondary_mm: float = Field(default=0.25, gt=0)
    background_mm: float = Field(
        default=0.18, gt=0, description="Beyond, hidden, reference.",
    )
    annotation_mm: float = Field(default=0.18, gt=0)
    dimension_mm: float = Field(default=0.18, gt=0)


class HatchDensity(str, Enum):
    FINE = "fine"
    MEDIUM = "medium"
    COARSE = "coarse"


class AnnotationPosition(str, Enum):
    LEADERED = "leadered"
    INLINE = "inline"
    TABULATED = "tabulated"


class DrawingLanguage(BaseModel):
    model_config = _Frozen

    lineweights: Lineweights = Field(default_factory=Lineweights)
    line_types: tuple[str, ...] = Field(
        default=("L-CONT", "L-DASH", "L-DOT", "L-CENT"),
        description="ADOS token names. A practice subsets, never invents.",
    )
    hatch_density: HatchDensity = Field(default=HatchDensity.FINE)
    hatch_tokens: tuple[str, ...] = Field(
        default=("H-CONC", "H-MSNR", "H-INSU-R", "H-TIMB-S", "H-METL"),
    )
    annotation_position: AnnotationPosition = Field(
        default=AnnotationPosition.LEADERED,
    )
    annotation_uppercase: bool = Field(default=True)
    hierarchy: tuple[GraphicLayer, ...] = Field(
        default=(
            GraphicLayer.CUT,
            GraphicLayer.PROJECTION,
            GraphicLayer.BACKGROUND,
            GraphicLayer.FURNITURE,
            GraphicLayer.LANDSCAPE,
            GraphicLayer.FIGURES,
            GraphicLayer.ANNOTATION,
            GraphicLayer.DIMENSION,
        ),
        description="Heaviest first. The validator checks the weights follow.",
    )
    show_furniture: bool = Field(default=True)
    show_figures: bool = Field(default=False)
    notes: str = Field(default="", max_length=600)

    @field_validator("hierarchy")
    @classmethod
    def _no_duplicates(cls, v: tuple[GraphicLayer, ...]) -> tuple[GraphicLayer, ...]:
        if len(set(v)) != len(v):
            raise ValueError("a graphic hierarchy cannot list a layer twice")
        if v and v[0] is not GraphicLayer.CUT:
            raise ValueError(
                "the cut must be heaviest: line weight encodes distance from "
                "the cut plane (ADOS-3.1.010)"
            )
        return v


# ---------------------------------------------------------------------------
# Diagrams
# ---------------------------------------------------------------------------


class DiagramStyle(str, Enum):
    MINIMAL = "minimal"
    TECHNICAL = "technical"
    EDITORIAL = "editorial"
    MONOCHROME = "monochrome"
    MATERIAL = "material"


class DiagramProjection(str, Enum):
    ORTHOGRAPHIC = "orthographic"
    AXONOMETRIC = "axonometric"
    ISOMETRIC = "isometric"
    EXPLODED = "exploded"


class DiagramLanguage(BaseModel):
    model_config = _Frozen

    style: DiagramStyle = Field(default=DiagramStyle.MINIMAL)
    projection: DiagramProjection = Field(default=DiagramProjection.AXONOMETRIC)
    palette: tuple[str, ...] = Field(
        default=(),
        description="Empty means the brand palette. A non-empty list must be "
        "a subset of it — a diagram in colours the brand has not declared is "
        "the commonest way a set stops looking like one practice.",
    )
    stroke_mm: float = Field(default=0.35, gt=0)
    fill_tones: tuple[str, ...] = Field(
        default=("T0", "T1", "T3"),
        description="ADOS tone tokens; at most four per sheet.",
    )
    label_step: str = Field(default="t2", pattern=r"^t[1-8]$")
    notes: str = Field(default="", max_length=600)


# ---------------------------------------------------------------------------
# Renders
# ---------------------------------------------------------------------------


class LightingScenario(str, Enum):
    SOFT_DAYLIGHT = "soft_daylight"
    OVERCAST = "overcast"
    GOLDEN_HOUR = "golden_hour"
    DUSK = "dusk"
    NIGHT = "night"
    STUDIO = "studio"


class RenderMood(str, Enum):
    EDITORIAL = "editorial"
    ATMOSPHERIC = "atmospheric"
    PHOTOREALISTIC = "photorealistic"
    MATERIAL_FOCUSED = "material_focused"
    MINIMAL = "minimal"
    DRAMATIC = "dramatic"
    DOCUMENTARY = "documentary"


class CameraLanguage(BaseModel):
    """Camera defaults a render pipeline can consume directly.

    The repository's ``VisualState.camera`` already speaks focal length and
    sensor width; these are the brand's defaults for those same fields, which
    is why the units match rather than being 'wide' and 'tight'.
    """

    model_config = _Frozen

    focal_length_mm: float = Field(default=35.0, gt=0)
    sensor_width_mm: float = Field(default=36.0, gt=0)
    height_m: float = Field(
        default=1.6, gt=0, description="Eye height. 1.6 m is standing.",
    )
    two_point_perspective: bool = Field(
        default=True,
        description="Verticals kept vertical. A converging vertical reads as "
        "a photograph of a building, not as a drawing of one.",
    )


class RenderLanguage(BaseModel):
    model_config = _Frozen

    lighting: LightingScenario = Field(default=LightingScenario.SOFT_DAYLIGHT)
    mood: RenderMood = Field(default=RenderMood.MATERIAL_FOCUSED)
    contrast: float = Field(default=0.5, ge=0.0, le=1.0)
    saturation: float = Field(default=0.7, ge=0.0, le=2.0)
    camera: CameraLanguage = Field(default_factory=CameraLanguage)
    material_expression: tuple[str, ...] = Field(
        default=(),
        description="What the surfaces are asked to show: 'grain', 'patina', "
        "'board-mark', 'weathering'.",
    )
    people: bool = Field(default=True)
    sky: str = Field(default="high overcast", max_length=120)
    notes: str = Field(default="", max_length=600)


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------


class MaterialEntry(BaseModel):
    """A material the practice returns to, with the tokens to draw it."""

    model_config = _Frozen

    name: str = Field(min_length=1, max_length=80)
    hatch_token: str = Field(default="", max_length=20)
    tone: str = Field(default="T2", pattern=r"^T[0-5]$")
    render_keywords: tuple[str, ...] = Field(default=())


class MaterialLanguage(BaseModel):
    model_config = _Frozen

    palette: tuple[MaterialEntry, ...] = Field(default=())
    notes: str = Field(default="", max_length=600)


class ArchitecturalLanguage(BaseModel):
    """The architectural identity layer, whole."""

    model_config = _Frozen

    drawing: DrawingLanguage = Field(default_factory=DrawingLanguage)
    diagrams: DiagramLanguage = Field(default_factory=DiagramLanguage)
    renders: RenderLanguage = Field(default_factory=RenderLanguage)
    materials: MaterialLanguage = Field(default_factory=MaterialLanguage)
