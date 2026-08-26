"""
brand/design_state/model.py

The canonical semantic model ADOS-M2.5 asks for: a single ``DesignState``
naming a project, its brand, its content, one document/projection over
that content, the pages and components that projection last composed,
the layout and visual language that produced them, the assets it draws
on, the constraints that apply to it, and the version it corresponds to.

**This is a read model, not a second source of truth.** Every field here
is derived from something that already exists and is already persisted
(``brand.project.model.Project``/``Document``, ``brand.models.brand.Brand``,
``brand.creative.plan.PagePlan``, ``brand.creative.direction.CreativeDirection``,
``brand.project.requirements``). Nothing in this module is written back
to storage on its own — ``brand/design_state/build.py`` only ever reads.
A future LLM (or any other caller) that wants to *change* something acts
through the same commands that already exist
(``brand.creative.intent.CommandIntent`` against ``ContentModel``/
``PagePlan``, the Project API's content/section/version endpoints) —
never by mutating a ``DesignState`` object and expecting it to persist.

Every sub-state below is deliberately thin: an id, a kind, a handful of
scalars — not a restatement of the object it derives from. Where a
richer view already exists (a Document's own content, a Brand's full
token set), the DesignState carries a reference and a short summary, not
a duplicate.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Bumped only if a field is added, removed or renamed in a way that
#: breaks a consumer reading this shape — additive, backward-compatible
#: changes (a new optional field) do not require a bump. Carried on the
#: object itself (not inferred from context) so a serialized DesignState
#: — including one an LLM has been handed — is self-describing.
SCHEMA_VERSION = "2.5"


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class ProjectState(BaseModel):
    """What a project is, independent of any one document — ADOS-M2.5 §4."""

    model_config = _Frozen

    id: str
    name: str
    description: str
    #: The generic project-facts bag (client, location, typology, ...) —
    #: brand.project.model.Project.project_data, unchanged.
    project_data: dict[str, Any] = Field(default_factory=dict)
    document_ids: tuple[str, ...] = ()
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------


class BrandState(BaseModel):
    """An input to composition, not a property of any one output —
    ADOS-M2.5 §5. ``tokens`` is the flat, resolved value map
    (``TokenSet.flat()``) actually used to derive Layout/VisualLanguage
    below — a summary of what the Brand resolved to, never a second
    declaration of it."""

    model_config = _Frozen

    id: Optional[str] = None
    version: Optional[str] = None
    name: Optional[str] = None
    tokens: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------


class ContentItemState(BaseModel):
    """A thin, addressable pointer to one real ``ContentItem`` — enough
    to inspect and select from without duplicating authored text into
    every DesignState read."""

    model_config = _Frozen

    id: str
    kind: str
    preview: str = Field(max_length=160)
    #: True if this item lives in the project's shared pool
    #: (``Project.content_items``) rather than the document's own.
    shared: bool


class ContentState(BaseModel):
    """Content addressable independently of layout — ADOS-M2.5 §6. ``own``
    is this document's private items; ``shared_pool`` is every item the
    *project* makes available; ``selected_shared_ids`` is the subset of
    the pool this specific document/projection actually includes."""

    model_config = _Frozen

    own: tuple[ContentItemState, ...] = ()
    shared_pool: tuple[ContentItemState, ...] = ()
    selected_shared_ids: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Document (the projection instance)
# ---------------------------------------------------------------------------


class DocumentState(BaseModel):
    """A projection definition over the DesignState — ADOS-M2.5 §7.
    ``output_type`` is a ``brand.project.document_types.DocumentType`` id,
    or ``""`` for the Custom projection (an untyped, free-form document —
    M2.1's original shape, still fully supported, never a special case
    requiring its own domain model)."""

    model_config = _Frozen

    id: str
    name: str
    output_type: str = ""
    direction_id: str
    audience: Optional[str] = None
    purpose: Optional[str] = None
    requested_structure: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)
    project_refs: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Pages / Components
# ---------------------------------------------------------------------------


class ComponentState(BaseModel):
    """WHAT a placed element is — ADOS-M2.5 §9. Derived from one real
    ``brand.creative.plan.Slot``; ``kind`` is a semantic name (Text,
    Heading, Image, Metric, ...), never the archetype's own internal
    slot-component string, which is a layout implementation detail, not
    a vocabulary a future LLM should have to learn."""

    model_config = _Frozen

    id: str
    kind: str
    page_index: int
    block_id: str
    asset_id: str = ""


class PageState(BaseModel):
    """One page of the last real composition — ADOS-M2.5 §8. A page does
    not know it belongs to an Investor Deck; it belongs to a Document,
    which belongs to a DesignState."""

    model_config = _Frozen

    id: str
    index: int
    purpose: str
    width_mm: float
    height_mm: float
    component_ids: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


class LayoutState(BaseModel):
    """WHERE/HOW a component is placed — ADOS-M2.5 §10. Derived read-only
    from the brand's own grid tokens and (once composed) the actual
    PagePlan grid; the deterministic layout solver in
    ``brand.creative.composer`` remains the sole authority for resolving
    it — nothing here recomputes or overrides a placement."""

    model_config = _Frozen

    columns: int
    gutter_mm: float
    margin_mm: float
    baseline_mm: float
    page_width_mm: float
    page_height_mm: float


# ---------------------------------------------------------------------------
# Visual Language
# ---------------------------------------------------------------------------


class VisualLanguageState(BaseModel):
    """HOW composition looks, never appearance itself — ADOS-M2.5 §11.
    A direct, field-for-field view of a real
    ``brand.creative.direction.CreativeDirection``; its own docstring
    already states this exact boundary ("Emphasis, density and pacing.
    Never appearance."), which is precisely what this sub-state is."""

    model_config = _Frozen

    direction_id: str
    audience: str
    goal: str
    lead_with: str
    narrative_order: tuple[str, ...] = ()
    emphasis_ceiling: int
    text_density: float
    words_per_page_max: int
    image_ratio: float
    pacing: tuple[str, ...] = ()
    display_step: str
    body_step: str


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


class AssetState(BaseModel):
    """A stable-id reference a component points at, never embedded file
    information — ADOS-M2.5 §12. A direct view of a real
    ``brand.project.model.Asset``; ``role``/``tags`` are intentionally
    absent — nothing in the system tracks either today, and inventing
    them here would be exactly the kind of field with no current use
    case ADOS-M2.5 §4 warns against."""

    model_config = _Frozen

    id: str
    filename: str
    content_type: str
    width_px: Optional[int] = None
    height_px: Optional[int] = None


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


class ConstraintLevel(str, Enum):
    """ADOS-M2.5 §13's MUST/SHOULD/MAY, mapped from the Requirements
    Engine's own, already-existing severities
    (``brand.validation.brand_validator.Severity``): ERROR/BLOCK -> MUST,
    WARN -> SHOULD, INFO -> MAY. Not a new severity scale — a rename of
    the one that already exists, for the vocabulary this milestone asks
    for."""

    MUST = "must"
    SHOULD = "should"
    MAY = "may"


class ConstraintRule(BaseModel):
    """One machine-readable rule and, when it has actually been checked,
    whether it currently holds. ``satisfied`` is ``None`` when the rule
    could not yet be evaluated (nothing has been composed for a check
    that needs a plan) — never coerced to ``True`` or ``False`` for a
    question that was not actually answered."""

    model_config = _Frozen

    id: str
    level: ConstraintLevel
    description: str
    #: "requirement" — from brand.project.requirements's per-type rules.
    source: str = "requirement"
    satisfied: Optional[bool] = None


class ConstraintState(BaseModel):
    model_config = _Frozen

    rules: tuple[ConstraintRule, ...] = ()


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class VersionState(BaseModel):
    """ADOS-M2.5 §14 — reuses ``brand.project.model.ProjectVersion``
    entirely; this is a pointer into that immutable history, not a
    second version model. ``number`` is ``None`` when the DesignState
    reflects the document's current, live (not-yet-versioned) state."""

    model_config = _Frozen

    number: Optional[int] = None
    label: str = ""
    created_at: Optional[datetime] = None
    #: Every version number saved for this document, newest first — so a
    #: caller can answer "what versions exist" without a second request.
    available_versions: tuple[int, ...] = ()


# ---------------------------------------------------------------------------
# DesignState — the root
# ---------------------------------------------------------------------------


class DesignState(BaseModel):
    """The canonical root domain object (ADOS-M2.5 §3). Independent of
    any renderer, any LLM provider, any single output format — see this
    module's own docstring for what "independent" means in practice
    (read model, not a second store)."""

    model_config = _Frozen

    schema_version: str = SCHEMA_VERSION
    project: ProjectState
    brand: BrandState
    content: ContentState
    document: DocumentState
    pages: tuple[PageState, ...] = ()
    components: tuple[ComponentState, ...] = ()
    layout: Optional[LayoutState] = None
    visual_language: VisualLanguageState
    assets: tuple[AssetState, ...] = ()
    constraints: ConstraintState
    version: VersionState

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
