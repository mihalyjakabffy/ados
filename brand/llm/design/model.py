"""
brand/llm/design/model.py

ADOS-M3.4's canonical domain object: :class:`DesignIntent`. Adapted
from the master prompt's own conceptual schema (§5/§14) to repository
convention.

**Consolidations made against the master prompt's own field list**
(documented here rather than silently dropped, per this repository's
established practice — see ADOS-M3.2/M3.3 for the same discipline):

* No separate top-level ``image_strategy`` field. The master prompt's
  own examples of it (image-led, hero/supporting distinction) are
  already exactly what
  :class:`~brand.llm.design.vocabulary.CompositionStrategy` (document
  level) and each section's own ``asset_refs`` /
  :class:`~brand.llm.design.vocabulary.ImageRole` (section level)
  express. A third field name for the same decision would fragment the
  vocabulary the master prompt itself warns against (§43).
* No ``content_emphasis`` field on :class:`SectionDesign` duplicating
  ``brand.llm.narrative.model.NarrativeSection.emphasis`` — a
  ``SectionDesign`` references ``section_id``; the narrative's own
  emphasis list is already reachable through it.
* ``hierarchy`` is represented two ways, deliberately not merged:
  :attr:`SectionDesign.visual_priority` (relative dominance between
  sections, driven by ``NarrativePlan`` priority) and
  :attr:`SectionDesign.typography_hierarchy` (how strongly *within* a
  section the type hierarchy reads). These answer different questions
  — "which section wins" vs. "how much internal contrast" — and
  collapsing them would lose one.

**Brand-token fields stay plain strings, validated after the fact.**
``heading_role``/``body_role``/``caption_role``/``color_role`` are not
closed enums: a real brand's own type-role names
(``brand.models.visual_identity.Typography.heading_styles`` etc.) are
per-brand data, not a fixed ADOS vocabulary — the same reasoning
``brand.llm.content.extraction.RawEntity.type`` already applies to a
value that must be checked against something outside this module (a
real ``Brand``, in ``brand.llm.design.validation``) rather than
accepted as free text.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from brand.llm.design.vocabulary import (
    AssetImportance,
    ColorStrategy,
    CompositionStrategy,
    ConstraintStrength,
    ContrastLevel,
    DesignChangeType,
    DesignExclusionReason,
    GridStrategy,
    ImageRole,
    PersonalityAxis,
    Rhythm,
    TextDensity,
    TypographyHierarchy,
    VisualPriority,
    VisualRole,
    WhitespaceStrategy,
)

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Bumped when the shape changes in a way a stored DesignIntent or
#: trace would notice — brand/llm/narrative/model.py's own convention.
SCHEMA_VERSION = "3.4"


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DesignIssueType(str, Enum):
    """What a :class:`DesignIssue` is flagging — ADOS-M3.4 §39/§52."""

    BRAND_CONFLICT = "brand_conflict"
    ASSET_SCARCITY = "asset_scarcity"
    CONTRADICTORY_DENSITY = "contradictory_density"
    UNSUPPORTED_VISUAL_INFERENCE = "unsupported_visual_inference"
    MISSING_CONTENT_ACKNOWLEDGED = "missing_content_acknowledged"


class AssetDesignRef(BaseModel):
    """One real M3.2 asset, given a semantic role in this section's
    composition — ADOS-M3.4 §16/§17. ``asset_id`` must be a real
    ``brand.llm.content.model.AssetContent.asset_id``; resolving that
    is ``brand.llm.design.validation``'s job, not this model's — the
    same split ADOS-M3.2/M3.3 already draw between "shape" and
    "resolves against a real object"."""

    model_config = _Frozen

    asset_id: str = Field(min_length=1)
    role: ImageRole
    importance: AssetImportance = AssetImportance.SUPPORTING


class DesignConstraint(BaseModel):
    """A semantic design constraint — ADOS-M3.4 §29/§30. Never an
    execution command: a hard constraint says what must hold, not how
    the deterministic Composer achieves it."""

    model_config = _Frozen

    description: str = Field(min_length=1, max_length=300)
    strength: ConstraintStrength
    #: Free text naming where this came from — "brand_dna",
    #: "ados_hard_constraint", "generated_preference" — descriptive
    #: only, the same posture ``brand.llm.content.model.SourceReference
    #: .extraction_method`` takes.
    source: str = Field(default="", max_length=80)


class DesignIssue(BaseModel):
    """Something the design planner flagged rather than silently
    resolved — ADOS-M3.4 §39's own worked example
    (``DesignFinding: type = brand_conflict``)."""

    model_config = _Frozen

    type: DesignIssueType
    description: str = Field(min_length=1, max_length=400)
    section_id: Optional[str] = None


class DesignExclusion(BaseModel):
    """Why a narrative section received no :class:`SectionDesign` —
    ADOS-M3.4 §27: no narrative section may silently disappear."""

    model_config = _Frozen

    section_id: str = Field(min_length=1)
    reason: DesignExclusionReason
    description: str = Field(default="", max_length=300)


class SectionDesign(BaseModel):
    """The visual design strategy for one real
    ``brand.llm.narrative.model.NarrativeSection`` — ADOS-M3.4 §14.
    References ``section_id``; never restates the section's narrative
    content."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    section_id: str = Field(min_length=1)
    visual_role: tuple[VisualRole, ...] = Field(min_length=1)
    visual_priority: VisualPriority
    composition_mode: CompositionStrategy
    asset_refs: tuple[AssetDesignRef, ...] = ()
    text_density: TextDensity
    #: Reuses ``TextDensity``'s own scale for image density rather than
    #: a second, near-identical five-step enum (ADOS-M3.4 §14 names the
    #: field but gives it no distinct vocabulary of its own).
    image_density: TextDensity = TextDensity.MEDIUM
    #: Free text, capped — the master prompt names the field but gives
    #: no closed vocabulary for it (unlike every other strategy field
    #: here); a diagram strategy is closer to a short design note
    #: ("exploded axonometric", "annotated section") than a semantic
    #: category with a handful of members.
    diagram_strategy: Optional[str] = Field(default=None, max_length=200)
    whitespace: WhitespaceStrategy
    contrast: ContrastLevel
    #: What repeats — ADOS-M3.4 §25 — as short motif phrases, e.g.
    #: "consistent caption treatment". What repeats, never its pixel
    #: dimensions.
    repetition: tuple[str, ...] = Field(default=(), max_length=8)
    #: Brand type-role names (e.g. "h2", "caption") — real per-brand
    #: data, validated against the given Brand's own
    #: ``Typography.heading_styles``/``body_styles``/``numeric_styles``
    #: keys downstream, never a closed enum here.
    heading_role: Optional[str] = Field(default=None, max_length=40)
    body_role: Optional[str] = Field(default=None, max_length=40)
    caption_role: Optional[str] = Field(default=None, max_length=40)
    typography_hierarchy: TypographyHierarchy
    color_strategy: Optional[ColorStrategy] = None
    #: How this section relates to an existing DesignState, when one
    #: was given — ADOS-M3.4 §54. Defaults to INTRODUCE: with no prior
    #: state, there is nothing yet to preserve, modify, or remove.
    change_type: DesignChangeType = DesignChangeType.INTRODUCE
    #: Optional, capped — ADOS-M3.4 §28: useful for review, never
    #: required everywhere, and never itself an execution instruction.
    rationale: Optional[str] = Field(default=None, max_length=400)


class DesignIntent(BaseModel):
    """The root object ADOS-M3.4 exists to produce. Semantic, never
    geometric (ADOS-M3.4 §4/§58): every field here answers "how should
    this be communicated visually" — never "where on the page"."""

    model_config = _Frozen

    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=_short_id)
    project_id: str
    narrative_plan_id: str = ""

    # -- Versioning (ADOS-M3.4 §60) ---------------------------------------
    content_model_version: Optional[int] = None
    brand_id: Optional[str] = None
    brand_version: Optional[str] = None
    #: The ``brand.design_state.model.VersionState.number`` of the
    #: DesignState this was resolved against, if any — ``None`` when no
    #: DesignState was given at all (every SectionDesign then defaults
    #: to ``change_type=INTRODUCE``).
    design_state_version: Optional[int] = None

    # -- Document-level strategy -------------------------------------------
    #: A subset of the real Brand's own ``Identity.personality`` —
    #: ADOS-M3.4 §10, never a value the brand does not itself claim
    #: (checked in ``brand.llm.design.validation``).
    visual_language: tuple[PersonalityAxis, ...] = ()
    composition_strategy: CompositionStrategy
    rhythm: Rhythm = Rhythm.STEADY
    density: TextDensity = TextDensity.MEDIUM
    typography_hierarchy: TypographyHierarchy = TypographyHierarchy.RESTRAINED
    color_strategy: ColorStrategy = ColorStrategy.RESTRAINED
    grid_strategy: GridStrategy = GridStrategy.EDITORIAL
    whitespace_strategy: WhitespaceStrategy = WhitespaceStrategy.MODERATE

    # -- Section-level strategy --------------------------------------------
    section_designs: tuple[SectionDesign, ...] = ()
    excluded_sections: tuple[DesignExclusion, ...] = ()

    # -- Constraints and issues ---------------------------------------------
    constraints: tuple[DesignConstraint, ...] = ()
    design_issues: tuple[DesignIssue, ...] = ()

    #: Small, free-form bag — document_type_id, the generator that
    #: produced this, requested brand/creative-direction ids. Never
    #: read by anything this package validates against; purely
    #: descriptive, like ``brand.project.model.Document.metadata``.
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)

    def section_design(self, section_id: str) -> Optional[SectionDesign]:
        for sd in self.section_designs:
            if sd.section_id == section_id:
                return sd
        return None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
