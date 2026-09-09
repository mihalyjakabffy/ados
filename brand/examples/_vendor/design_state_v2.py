"""
brand/examples/_vendor/design_state_v2.py

Vendored from the source monorepo's ``schemas/v2_models.py`` at the point
ADOS was split into its own repository (see the ADOS-migration commit this
file was introduced in). Only the five Pydantic sub-state models
``brand/examples/malthouse.py`` actually needs — plus the two more
(``VisualState``, ``ReviewState``) that ``DesignState``'s own field
annotations require to exist in the same module — are kept; the
SQLAlchemy ORM mappings, the BIM-source models, and the Postgres/SQLite
dialect switching from the original file are dropped, since nothing in
ADOS ever persisted through that layer.

This is REVELATION's own "Design State Runtime v2" domain model, not
ADOS's own ``brand.design_state`` module — ``malthouse.py`` uses it only
to build one worked-example fixture in the shape an early cross-system
integration expected. Kept for that fixture's sake, not because ADOS
depends on this schema going forward.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ApprovalStatus(str, Enum):
    """Lifecycle status of a ``DesignState`` from a stakeholder's perspective."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class StateLockLevel(str, Enum):
    """How strongly a state is frozen."""

    UNLOCKED = "unlocked"
    SOFT = "soft"
    HARD = "hard"


class CodeComplianceStatus(str, Enum):
    UNKNOWN = "unknown"
    PASSING = "passing"
    WARNING = "warning"
    FAILING = "failing"


# ---------------------------------------------------------------------------
# Sub-state domain models (Pydantic, frozen)
# ---------------------------------------------------------------------------

_FrozenModel = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class GeometryState(BaseModel):
    """The geometric basis of the design — references to BIM data, not the bytes."""

    model_config = _FrozenModel

    bim_source_id: Optional[uuid.UUID] = Field(default=None)
    mesh_relative_path: Optional[str] = Field(default=None)
    mesh_sha256: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    bounding_box: Optional[dict[str, list[float]]] = Field(default=None)
    storey_count: Optional[int] = Field(default=None, ge=0)
    space_count: Optional[int] = Field(default=None, ge=0)
    gross_floor_area_m2: Optional[float] = Field(default=None, ge=0.0)
    extras: dict[str, Any] = Field(default_factory=dict)


class VisualState(BaseModel):
    """Camera, lighting scenario, render settings — what the viewer sees."""

    model_config = _FrozenModel

    camera: dict[str, Any] = Field(default_factory=dict)
    render_settings: dict[str, Any] = Field(default_factory=dict)
    lighting: dict[str, Any] = Field(default_factory=dict)
    extras: dict[str, Any] = Field(default_factory=dict)


class SemanticState(BaseModel):
    """Materials, style, mood, composition — the intent of the design."""

    model_config = _FrozenModel

    style: Optional[str] = None
    mood: Optional[str] = None
    materials: dict[str, Optional[str]] = Field(default_factory=dict)
    composition: dict[str, Any] = Field(default_factory=dict)
    positive_override: Optional[str] = None
    negative_override: Optional[str] = None
    extras: dict[str, Any] = Field(default_factory=dict)


class ConstraintItem(BaseModel):
    """A single constraint check result."""

    model_config = _FrozenModel

    name: str
    target: float
    achieved: Optional[float] = None
    unit: str = ""
    status: CodeComplianceStatus = CodeComplianceStatus.UNKNOWN
    note: Optional[str] = None


class ConstraintState(BaseModel):
    """Hard / soft constraints the design must satisfy."""

    model_config = _FrozenModel

    budget_target: Optional[float] = Field(default=None)
    budget_currency: str = "EUR"
    budget_achieved: Optional[float] = Field(default=None)
    energy_target_kwh_m2_yr: Optional[float] = Field(default=None)
    energy_achieved_kwh_m2_yr: Optional[float] = Field(default=None)
    code_checks: list[ConstraintItem] = Field(default_factory=list)
    area_targets: list[ConstraintItem] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)


class ReviewComment(BaseModel):
    """A single piece of stakeholder feedback attached to a state."""

    model_config = _FrozenModel

    comment_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    author: str
    body: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    anchor: Optional[dict[str, Any]] = Field(default=None)


class ReviewState(BaseModel):
    """Human-facing review status and comment thread."""

    model_config = _FrozenModel

    status: ApprovalStatus = ApprovalStatus.DRAFT
    reviewers: list[str] = Field(default_factory=list)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    comments: list[ReviewComment] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# DesignState aggregate
# ---------------------------------------------------------------------------


class DesignState(BaseModel):
    """A single immutable snapshot of an architectural design (REVELATION v2 schema)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    design_state_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    parent_state_id: Optional[uuid.UUID] = Field(default=None)
    branch_name: str = Field(default="main", max_length=120)
    content_hash: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    geometry: GeometryState = Field(default_factory=GeometryState)
    visual: VisualState = Field(default_factory=VisualState)
    semantic: SemanticState = Field(default_factory=SemanticState)
    constraints: ConstraintState = Field(default_factory=ConstraintState)
    review: ReviewState = Field(default_factory=ReviewState)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = Field(default=None, max_length=120)
    owner_id: Optional[uuid.UUID] = Field(default=None)
    lock_level: StateLockLevel = StateLockLevel.UNLOCKED
    tags: list[str] = Field(default_factory=list)
    message: Optional[str] = Field(default=None)

    def compute_content_hash(self) -> str:
        canonical = {
            "geometry": self.geometry.model_dump(mode="json"),
            "visual": self.visual.model_dump(mode="json"),
            "semantic": self.semantic.model_dump(mode="json"),
            "constraints": self.constraints.model_dump(mode="json"),
            "review": self.review.model_dump(mode="json"),
        }
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def with_content_hash(self) -> "DesignState":
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
