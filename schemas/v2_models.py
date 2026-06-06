"""
schemas/v2_models.py

Design State Runtime — v2 schema.

Phase 1 of the AI-Native Architectural State Platform.  Replaces the v1
``RenderState`` with a structured aggregate of five orthogonal sub-states
(geometry / visual / semantic / constraint / review) that together describe
the architectural design at a single point in its evolution.

Two layers in this module
-------------------------
1. **Pydantic domain models** (the public type system).  Frozen and validated;
   used by FastAPI, the pipeline, and the diff engine.  These are the only
   types the rest of the codebase should depend on.

2. **SQLAlchemy 2.x ORM models** (persistence).  Map the Pydantic shapes onto
   Postgres.  The sub-states live as JSONB columns so they can evolve without
   schema migrations; the outer row carries only structural metadata.  Both
   directions of the round-trip (``to_domain`` / ``from_domain``) are wired up.

Coexistence with v1
-------------------
This module does *not* replace ``schemas/models.py``.  It lives alongside it
for the migration window.  An adapter (not in this file — see
``services/state_migration.py`` in the roadmap) bridges v1 ``RenderState``
into v2 ``DesignState`` for read paths during Phase 1; write paths land in v2
directly once the API surface is updated.

Content addressing
------------------
Every committed ``DesignState`` carries a ``content_hash`` (SHA-256 over the
canonical JSON of its sub-states).  Equivalence is hash-equivalence: two
states with identical sub-states *are* the same state.  This is how the
state cache, diff engine, and lineage collapse work.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# SQLAlchemy is an optional dependency: the Pydantic domain models below work
# in any Python environment, while the ORM mappings at the bottom of this
# file require SQLAlchemy + psycopg2.  Importing them lazily lets demos /
# CLI tools / unit tests run without a DB stack installed.
try:
    from sqlalchemy import (
        Boolean,
        DateTime,
        Float,
        ForeignKey,
        Index,
        String,
        Text,
        func,
    )
    import os as _os
    from sqlalchemy.types import JSON
    # Use JSONB on PostgreSQL for GIN index support; fall back to JSON on SQLite
    _db_url = _os.environ.get("DATABASE_URL", "sqlite")
    if "postgresql" in _db_url or "postgres" in _db_url:
        from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
    else:
        JSONB = JSON  # type: ignore[assignment,misc]
        from sqlalchemy import Uuid as PG_UUID  # type: ignore[assignment]
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

    _SQLA_AVAILABLE = True
except ImportError:
    _SQLA_AVAILABLE = False


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
    """
    How strongly a state is frozen.

    A ``DesignState`` becomes immutable once anything depends on it (a render,
    a child branch, an approval).  The lock level lets the API give precise
    errors — e.g. "cannot modify visual_state: locked because a render exists".
    """

    UNLOCKED = "unlocked"         # draft, no descendants, no renders, no review
    SOFT = "soft"                 # has children but no renders
    HARD = "hard"                 # has renders or approvals — fully frozen


class CodeComplianceStatus(str, Enum):
    UNKNOWN = "unknown"
    PASSING = "passing"
    WARNING = "warning"
    FAILING = "failing"


# ---------------------------------------------------------------------------
# Sub-state domain models  (Pydantic, frozen)
# ---------------------------------------------------------------------------
#
# Each sub-state captures one orthogonal aspect of the design.  They're
# orthogonal so the diff engine can compute per-aspect deltas and so storage
# is targeted (each lands in its own JSONB column).
#
# Field strategy: typed Pydantic for the fields we know matter today; an
# ``extras`` dict on each sub-state for future fields that haven't earned a
# named slot yet.  Adding an ``extras`` key is free; promoting a hot key to
# a typed field is a one-line change.


_FrozenModel = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class GeometryState(BaseModel):
    """
    The geometric basis of the design.

    Holds *references* to BIM data, not the bytes — a ``DesignState`` is
    light; the heavy artefacts (the IFC, the tessellated mesh, the control
    maps) live in object storage and are addressed by hash.
    """

    model_config = _FrozenModel

    bim_source_id: Optional[uuid.UUID] = Field(
        default=None,
        description="FK to BIMSource (parsed IFC).  None ⇒ no semantic geometry yet.",
    )
    mesh_relative_path: Optional[str] = Field(
        default=None,
        description="Path under storage_root to a tessellated mesh (OBJ/GLB).",
    )
    mesh_sha256: Optional[str] = Field(
        default=None, pattern=r"^[0-9a-f]{64}$", description="Hex SHA-256 of the mesh."
    )
    bounding_box: Optional[dict[str, list[float]]] = Field(
        default=None,
        description="{'min': [x,y,z], 'max': [x,y,z]} in world meters.",
    )
    storey_count: Optional[int] = Field(default=None, ge=0)
    space_count: Optional[int] = Field(default=None, ge=0)
    gross_floor_area_m2: Optional[float] = Field(default=None, ge=0.0)
    extras: dict[str, Any] = Field(default_factory=dict)


class VisualState(BaseModel):
    """Camera, lighting scenario, render settings — what the viewer sees."""

    model_config = _FrozenModel

    # We reuse the v1 camera/render schemas verbatim; they're stable.
    camera: dict[str, Any] = Field(default_factory=dict)
    render_settings: dict[str, Any] = Field(default_factory=dict)
    lighting: dict[str, Any] = Field(
        default_factory=dict,
        description="Sun position, sky model, time-of-day. "
        "Lifted out of the v1 DSL where it was nested under .lighting.",
    )
    extras: dict[str, Any] = Field(default_factory=dict)


class SemanticState(BaseModel):
    """Materials, style, mood, composition — the *intent* of the design."""

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
    """
    Hard / soft constraints the design must satisfy.

    Budget, energy use, code compliance, area targets.  These are checked
    against the *semantic* and *geometric* states by external analysers; the
    state itself stores the targets and the latest results.
    """

    model_config = _FrozenModel

    budget_target: Optional[float] = Field(default=None, description="Target cost.")
    budget_currency: str = "EUR"
    budget_achieved: Optional[float] = Field(
        default=None, description="Latest estimated cost (from QTO or estimator)."
    )

    energy_target_kwh_m2_yr: Optional[float] = Field(
        default=None, description="Annual primary energy target."
    )
    energy_achieved_kwh_m2_yr: Optional[float] = Field(default=None)

    code_checks: list[ConstraintItem] = Field(
        default_factory=list,
        description="Building-code / regulatory checks (egress, daylight, etc.).",
    )
    area_targets: list[ConstraintItem] = Field(
        default_factory=list,
        description="Programme area targets per space type.",
    )
    extras: dict[str, Any] = Field(default_factory=dict)


class ReviewComment(BaseModel):
    """A single piece of stakeholder feedback attached to a state."""

    model_config = _FrozenModel

    comment_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    author: str
    body: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    anchor: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional anchor pointing at what the comment references — "
            "e.g. {'kind': 'sub_state_field', 'path': 'semantic.materials.glazing'} "
            "or {'kind': 'image_region', 'render_id': '...', 'bbox': [x,y,w,h]}."
        ),
    )


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
    """
    A single immutable snapshot of an architectural design.

    Carries all five sub-states plus the structural metadata that lets it sit
    in a versioned DAG (parent_id, branch_name, content_hash).  The
    ``content_hash`` is the canonical fingerprint of the sub-states — two
    states with identical sub-states are the same state by definition.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # ---- Identity ------------------------------------------------------
    design_state_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    parent_state_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Parent in the state DAG.  None for the root state.",
    )
    branch_name: str = Field(default="main", max_length=120)
    content_hash: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        description=(
            "SHA-256 of the canonical JSON of the five sub-states.  Computed "
            "by ``compute_content_hash()``; persistence layer must populate "
            "before insert."
        ),
    )

    # ---- Sub-states ----------------------------------------------------
    geometry: GeometryState = Field(default_factory=GeometryState)
    visual: VisualState = Field(default_factory=VisualState)
    semantic: SemanticState = Field(default_factory=SemanticState)
    constraints: ConstraintState = Field(default_factory=ConstraintState)
    review: ReviewState = Field(default_factory=ReviewState)

    # ---- Audit + lock --------------------------------------------------
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = Field(default=None, max_length=120)
    owner_id: Optional[uuid.UUID] = Field(
        default=None,
        description="FK to users.id — the User who committed this state (multi-tenant).",
    )
    lock_level: StateLockLevel = StateLockLevel.UNLOCKED
    tags: list[str] = Field(default_factory=list)
    message: Optional[str] = Field(
        default=None,
        description="Free-text commit message — same role as a Git commit message.",
    )

    # ------------------------------------------------------------------
    # Content addressing
    # ------------------------------------------------------------------

    def compute_content_hash(self) -> str:
        """
        Compute the SHA-256 over a canonical JSON projection of the sub-states.

        ``content_hash`` is the addressable identity of the state.  Two states
        with identical sub-states *are* the same state, regardless of when or
        by whom they were created.  Audit fields and the lock level are *not*
        part of the hash — they're metadata about the state, not the state.
        """
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
        """Return a copy with ``content_hash`` populated."""
        return self.model_copy(update={"content_hash": self.compute_content_hash()})


# ---------------------------------------------------------------------------
# BIMSource — the parsed semantic graph of a single IFC file
# ---------------------------------------------------------------------------


class BIMSourceMetadata(BaseModel):
    """Light header info about a parsed IFC file."""

    model_config = _FrozenModel

    schema_version: str = Field(description="e.g. 'IFC4', 'IFC2X3'.")
    application: Optional[str] = Field(
        default=None, description="Originating CAD app per IfcApplication."
    )
    project_name: Optional[str] = None
    site_name: Optional[str] = None
    storey_count: int = 0
    space_count: int = 0
    element_count: int = 0


class BIMSource(BaseModel):
    """
    A parsed IFC file represented as a semantic graph plus metadata.

    The graph itself (``services.ifc_parser.SemanticGraph``) is stored as a
    JSONB blob on the persistence layer; this Pydantic shape is the in-process
    representation that the diff engine and analysers consume.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    bim_source_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    ifc_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    metadata_: BIMSourceMetadata = Field(alias="metadata")
    graph: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Serialised SemanticGraph (nodes + edges + indexes).  Opaque to "
            "Pydantic; the typed view is in services.ifc_parser."
        ),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# SQLAlchemy 2.x ORM mappings
# ---------------------------------------------------------------------------
#
# Two tables:
#   bim_sources   — one row per parsed IFC, addressed by sha256
#   design_states — one row per committed state, FK parent_id for the DAG
#
# Sub-states live as JSONB.  Hot path indexes are added below; everything
# else can be reached via JSONB path expressions ad hoc.


if _SQLA_AVAILABLE:
    class Base(DeclarativeBase):  # type: ignore[misc, no-redef]
        """Declarative base for v2 ORM models."""
else:
    # ---- Stubs for SQLAlchemy-less environments (demos, unit tests) ----
    # The ORM class bodies below execute at import time, so every name they
    # reference (column types, mapped_column, relationship, …) must resolve
    # to *something*.  The stubs are intentionally non-functional: calling
    # any method on a stubbed ORM class will hit an AttributeError, which
    # is the right failure mode — "you tried to use the DB layer without
    # installing SQLAlchemy".  The Pydantic domain models above are
    # unaffected and remain fully usable.
    class Base:  # type: ignore[no-redef]
        """Stub Base when SQLAlchemy isn't installed — DB ops will fail."""

    def _sqla_stub(*args: Any, **kwargs: Any) -> Any:
        return None

    # Functions / factories used as expressions inside class bodies.
    Boolean = DateTime = Float = ForeignKey = Index = String = Text = _sqla_stub  # type: ignore[assignment]
    JSONB = PG_UUID = _sqla_stub                                                  # type: ignore[assignment]
    mapped_column = relationship = _sqla_stub                                     # type: ignore[assignment]

    class _FuncStub:  # type: ignore[no-redef]
        def __getattr__(self, _: str) -> Any:
            return _sqla_stub
    func = _FuncStub()  # type: ignore[assignment]

    # Mapped[...] only appears as a type annotation, and `from __future__
    # import annotations` defers their evaluation, so we don't strictly
    # need a runtime stub — but provide one anyway for safety against
    # tools that introspect annotations.
    class Mapped:  # type: ignore[no-redef]
        def __class_getitem__(cls, _item: Any) -> type:
            return cls


class BIMSourceORM(Base):
    __tablename__ = "bim_sources"

    bim_source_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    ifc_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    graph: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_domain(self) -> BIMSource:
        return BIMSource(
            bim_source_id=self.bim_source_id,
            project_id=self.project_id,
            ifc_sha256=self.ifc_sha256,
            metadata=BIMSourceMetadata.model_validate(self.metadata_),
            graph=self.graph,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, src: BIMSource) -> "BIMSourceORM":
        return cls(
            bim_source_id=src.bim_source_id,
            project_id=src.project_id,
            ifc_sha256=src.ifc_sha256,
            metadata_=src.metadata_.model_dump(mode="json"),
            graph=dict(src.graph),
            created_at=src.created_at,
        )


class DesignStateORM(Base):
    __tablename__ = "design_states"

    design_state_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    parent_state_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("design_states.design_state_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    branch_name: Mapped[str] = mapped_column(String(120), nullable=False, default="main")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    geometry: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    visual: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    semantic: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    review: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    lock_level: Mapped[str] = mapped_column(
        String(16), nullable=False, default=StateLockLevel.UNLOCKED.value
    )
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    # ---- Multi-tenant ownership ------------------------------------------
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Self-referential FK for the DAG.  ``passive_deletes`` lets Postgres
    # handle cascade behaviour declared in ondelete.
    children: Mapped[list["DesignStateORM"]] = relationship(
        "DesignStateORM",
        backref="parent",
        remote_side="DesignStateORM.design_state_id",
        passive_deletes=True,
    )

    __table_args__ = (
        # Uniqueness on (project, content_hash) makes commit-deduplication
        # a single INSERT ... ON CONFLICT, no Python-side check needed.
        Index("ix_design_states_project_hash", "project_id", "content_hash", unique=True),
        # GIN indexes on hot JSONB paths.  Postgres supports per-path indexes
        # with the jsonb_path_ops operator class for fast `@>` containment
        # queries.  Add more as query patterns emerge.
        Index(
            "ix_design_states_semantic_gin",
            "semantic",
            postgresql_using="gin",
            postgresql_ops={"semantic": "jsonb_path_ops"},
        ),
        Index(
            "ix_design_states_constraints_gin",
            "constraints",
            postgresql_using="gin",
            postgresql_ops={"constraints": "jsonb_path_ops"},
        ),
    )

    # -- round-trip with the Pydantic domain ---------------------------

    def to_domain(self) -> DesignState:
        return DesignState(
            design_state_id=self.design_state_id,
            project_id=self.project_id,
            parent_state_id=self.parent_state_id,
            branch_name=self.branch_name,
            content_hash=self.content_hash,
            geometry=GeometryState.model_validate(self.geometry),
            visual=VisualState.model_validate(self.visual),
            semantic=SemanticState.model_validate(self.semantic),
            constraints=ConstraintState.model_validate(self.constraints),
            review=ReviewState.model_validate(self.review),
            lock_level=StateLockLevel(self.lock_level),
            tags=list(self.tags or []),
            message=self.message,
            created_at=self.created_at,
            created_by=self.created_by,
            owner_id=self.owner_id,
        )

    @classmethod
    def from_domain(cls, state: DesignState) -> "DesignStateORM":
        if state.content_hash is None:
            raise ValueError(
                "DesignState.content_hash must be set before persisting. "
                "Call state.with_content_hash() first."
            )
        return cls(
            design_state_id=state.design_state_id,
            project_id=state.project_id,
            parent_state_id=state.parent_state_id,
            branch_name=state.branch_name,
            content_hash=state.content_hash,
            geometry=state.geometry.model_dump(mode="json"),
            visual=state.visual.model_dump(mode="json"),
            semantic=state.semantic.model_dump(mode="json"),
            constraints=state.constraints.model_dump(mode="json"),
            review=state.review.model_dump(mode="json"),
            lock_level=state.lock_level.value,
            tags=list(state.tags),
            message=state.message,
            created_at=state.created_at,
            created_by=state.created_by,
            owner_id=state.owner_id,
        )


class UserORM(Base):
    """
    User account — the leaf entity for multi-tenant auth.

    Multi-tenant design
    ───────────────────
    tenant_id is a plain string (e.g. "acme-architects").  All users with the
    same tenant_id belong to the same organisation.  There is no separate
    Tenant table in Phase A — the string IS the tenant identifier.  A Tenant
    table with billing/config can be added in Phase B without touching this model.

    Foreign-key relationships
    ─────────────────────────
    DesignStateORM.owner_id → users.id (nullable, SET NULL on user delete)
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship: states owned by this user
    owned_states: Mapped[list["DesignStateORM"]] = relationship(
        "DesignStateORM",
        back_populates="_owner",
        passive_deletes=True,
        foreign_keys="[DesignStateORM.owner_id]",
    )


# Wire the back-reference on DesignStateORM
if _SQLA_AVAILABLE:
    DesignStateORM._owner = relationship(  # type: ignore[attr-defined]
        "UserORM",
        back_populates="owned_states",
        foreign_keys=[DesignStateORM.owner_id],
    )


class DesignStateConstraintORM(Base):
    """
    A soft constraint attached to a DesignState by CONSTRUMIND.

    These are NOT stored inside the ``design_states`` sub-state JSON — they are
    an independent, append-only feed written by the REVELATION-side consumer of
    CONSTRUMIND's ``constraint.signal`` Redis channel.  A ``BLOCK``-severity
    active constraint gates render dispatch.

    ``design_state_id`` is a plain indexed UUID (no hard FK): signals may arrive
    for a state before/after its row exists, and the two services are
    deliberately decoupled.
    """

    __tablename__ = "design_state_constraints"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    design_state_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    signal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False, default="INFO")
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_pillar: Mapped[str] = mapped_column(String(8), nullable=False, default="CIF")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_dsc_state_active_severity", "design_state_id", "is_active", "severity"),
    )


# Backward-compat alias used by api/routers/v2_projects.py
LockLevel = StateLockLevel

__all__ = [
    # Enums
    "ApprovalStatus",
    "StateLockLevel",
    "LockLevel",
    "CodeComplianceStatus",
    # Sub-state models
    "GeometryState",
    "VisualState",
    "SemanticState",
    "ConstraintItem",
    "ConstraintState",
    "ReviewComment",
    "ReviewState",
    # Aggregates
    "DesignState",
    "BIMSourceMetadata",
    "BIMSource",
    # ORM
    "Base",
    "BIMSourceORM",
    "DesignStateORM",
    "UserORM",
    "DesignStateConstraintORM",
]
