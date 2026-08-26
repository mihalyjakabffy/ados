"""
brand/llm/design/vocabulary.py

The controlled vocabularies ADOS-M3.4 asks for (master prompt §10-§25,
§29-§30), each kept as small as the master prompt itself allows and
reusing an existing ADOS vocabulary wherever one already covers the
concept.

**Reused, not redeclared:**

* :class:`~brand.models.identity.PersonalityAxis` — the brand's own
  closed personality vocabulary (precise/quiet/material/editorial/
  warm/rigorous/experimental/civic/craft/pragmatic/monumental/playful).
  Its own docstring states directly that "the render language... [is]
  derived from it" — this *is* ADOS's canonical visual-language
  vocabulary (ADOS-M3.4 §10: "prefer existing ADOS vocabulary"), so
  :class:`DesignIntent.visual_language` is a subset of a real brand's
  own ``Identity.personality`` — never a value the brand does not
  itself claim.
* :class:`~brand.creative.direction.Audience` — read from the
  ``NarrativePlan``/``CreativeDirection`` this package consumes, not a
  new field here.

**New vocabulary, and why.** None of ``CreativeDirection``'s
enums (``Goal``, ``LeadWith``) are reused directly for
:class:`CompositionStrategy` or :class:`VisualRole`: ``LeadWith`` names
only four whole-direction values (image/statement/metric/drawing) and
operates at the level of "what the reader meets first" for an entire
``CreativeDirection``, not a per-``NarrativeSection`` composition
choice; a full mapping would either lose the master prompt's own list
or force ``CreativeDirection`` itself to grow M3.4-specific values it
has no other use for. Likewise :class:`~brand.content.model.BlockRole`
(context/problem/intervention/outcome/evidence/detail/provenance) names
a single already-composed *block's* role, not a whole section's visual
treatment — the same distinction ADOS-M3.3 already drew between
``SectionRole`` and ``BlockRole``, drawn again here between
:class:`VisualRole` and both of those.
"""

from __future__ import annotations

from enum import Enum

from brand.creative.direction import Audience
from brand.models.identity import PersonalityAxis

__all__ = [
    "Audience",
    "PersonalityAxis",
    "CompositionStrategy",
    "VisualRole",
    "VisualPriority",
    "TextDensity",
    "ImageRole",
    "AssetImportance",
    "TypographyHierarchy",
    "ColorStrategy",
    "GridStrategy",
    "WhitespaceStrategy",
    "Rhythm",
    "ContrastLevel",
    "ConstraintStrength",
    "DesignChangeType",
    "DesignExclusionReason",
]


class CompositionStrategy(str, Enum):
    """How a section (or the document overall) is composed —
    ADOS-M3.4 §11. Semantic, never geometric."""

    IMAGE_LED = "image_led"
    TEXT_LED = "text_led"
    DIAGRAM_LED = "diagram_led"
    DATA_LED = "data_led"
    BALANCED = "balanced"
    ASYMMETRIC = "asymmetric"
    MODULAR = "modular"
    SEQUENTIAL = "sequential"
    IMMERSIVE = "immersive"
    DENSE = "dense"
    SPARSE = "sparse"


class VisualRole(str, Enum):
    """The visual treatment one narrative section receives —
    ADOS-M3.4 §13's own list, verbatim. A section may combine roles
    (represented as a tuple on ``SectionDesign``, not a single value)."""

    HERO = "hero"
    INTRO = "intro"
    CONTEXTUAL = "contextual"
    DIAGRAM = "diagram"
    COMPARISON = "comparison"
    EVIDENCE = "evidence"
    TECHNICAL = "technical"
    GALLERY = "gallery"
    QUOTE = "quote"
    DATA = "data"
    PROCESS = "process"
    DETAIL = "detail"
    CLOSING = "closing"


class VisualPriority(str, Enum):
    """ADOS-M3.4 §12 — the visual analogue of
    ``brand.llm.narrative.vocabulary.SectionPriority``, deliberately a
    separate field: a narrative's communication priority and a
    section's visual dominance are related but not required to be
    identical (a supporting-priority section can still carry a
    dominant image if the narrative calls for it)."""

    DOMINANT = "dominant"
    SECONDARY = "secondary"
    SUPPORTING = "supporting"
    MINIMAL = "minimal"


class TextDensity(str, Enum):
    """Semantic text density — ADOS-M3.4 §15. Never a word count or a
    font size."""

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ImageRole(str, Enum):
    """How one asset participates visually — ADOS-M3.4 §16's own list,
    verbatim. Semantic role, never a placement."""

    HERO_IMAGE = "hero_image"
    SUPPORTING_IMAGE = "supporting_image"
    IMAGE_SEQUENCE = "image_sequence"
    GALLERY = "gallery"
    COMPARISON = "comparison"
    FULL_BLEED = "full_bleed"
    DETAIL = "detail"
    DIAGRAM_SUPPORT = "diagram_support"
    BACKGROUND = "background"
    THUMBNAIL = "thumbnail"


class AssetImportance(str, Enum):
    """ADOS-M3.4 §18."""

    HERO = "hero"
    PRIMARY = "primary"
    SUPPORTING = "supporting"
    OPTIONAL = "optional"


class TypographyHierarchy(str, Enum):
    """The *character* of a section's type hierarchy — ADOS-M3.4 §19.
    Distinct from which real brand type roles are used (a plain,
    brand-validated string — see ``SectionDesign.heading_role`` et al.,
    not this enum): this says how strongly the hierarchy should read,
    never which face or step realises it."""

    STRONG = "strong"
    RESTRAINED = "restrained"
    EDITORIAL = "editorial"
    TECHNICAL = "technical"
    EXPRESSIVE = "expressive"


class ColorStrategy(str, Enum):
    """ADOS-M3.4 §20 — semantic use of the brand's existing palette,
    never a new colour."""

    NEUTRAL_DOMINANT = "neutral_dominant"
    ACCENT_FOR_EMPHASIS = "accent_for_emphasis"
    MONOCHROME = "monochrome"
    BRAND_ACCENT = "brand_accent"
    HIGH_CONTRAST = "high_contrast"
    RESTRAINED = "restrained"


class GridStrategy(str, Enum):
    """ADOS-M3.4 §21 — semantic grid behaviour. The deterministic
    Composer remains responsible for actual column counts and
    gutters."""

    STRICT = "strict"
    MODULAR = "modular"
    EDITORIAL = "editorial"
    ASYMMETRIC = "asymmetric"
    FLUID = "fluid"
    DENSE = "dense"
    OPEN = "open"


class WhitespaceStrategy(str, Enum):
    """ADOS-M3.4 §22."""

    GENEROUS = "generous"
    MODERATE = "moderate"
    COMPACT = "compact"
    DRAMATIC = "dramatic"
    CONTINUOUS = "continuous"
    SECTIONAL = "sectional"


class Rhythm(str, Enum):
    """Document-level pacing across sections — ADOS-M3.4 §23."""

    STEADY = "steady"
    ALTERNATING = "alternating"
    PROGRESSIVE = "progressive"
    DRAMATIC = "dramatic"
    CALM = "calm"
    DENSE_TO_SPARSE = "dense_to_sparse"
    SPARSE_TO_DENSE = "sparse_to_dense"


class ContrastLevel(str, Enum):
    """ADOS-M3.4 §24. The master prompt names several contrast *axes*
    (scale, density, image/text, light/dark, detail/overview,
    technical/editorial) but only ever gives a single low/medium/high
    reading per section in its own examples — this package follows the
    examples rather than inventing an unused multi-axis structure; a
    :class:`~brand.llm.design.model.SectionDesign`'s own ``role`` and
    ``composition_mode`` already say *which* axis is in play."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConstraintStrength(str, Enum):
    """ADOS-M3.4 §30 — hard constraints are never overridden by a
    generated preference; soft ones are preferences the deterministic
    Composer may trade off against other goals."""

    HARD = "hard"
    SOFT = "soft"


class DesignChangeType(str, Enum):
    """How a section's design relates to an existing DesignState —
    ADOS-M3.4 §54. ``INTRODUCE`` is the default when no DesignState is
    given at all (there is nothing yet to preserve, modify, or
    remove)."""

    PRESERVE = "preserve"
    MODIFY = "modify"
    INTRODUCE = "introduce"
    REMOVE = "remove"


class DesignExclusionReason(str, Enum):
    """Why a narrative section received no ``SectionDesign`` —
    ADOS-M3.4 §27: no section may silently disappear."""

    REDUNDANT = "redundant"
    INSUFFICIENT_CONTENT = "insufficient_content"
    OUT_OF_SCOPE = "out_of_scope"
    OTHER = "other"
