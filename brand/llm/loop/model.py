"""
brand/llm/loop/model.py

ADOS-M3.6's domain objects. ``Iteration`` is the canonical, immutable
iteration record (ADOS-M3.6 §5/§6): every object that fed or resulted
from one loop step is embedded in full (the real ``DesignIntent``,
``CommandPlan``, composed ``PagePlan``, and evaluation), never a
reference that could later resolve to something different — the whole
point of "what changed between iteration 3 and 4" (§6) is that both
iterations remain exactly what they were.

Nothing here duplicates an existing model. ``findings`` wraps the real
``brand.validation.brand_validator.Finding`` (serialized, since that
type is a plain frozen dataclass, not a pydantic model); a
``Recommendation`` carries a ``DesignIntentPatch``, never a
``CommandIntent`` (that remains M3.5's own output, produced from the
*patched* ``DesignIntent`` this record already holds).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from brand.llm.loop.vocabulary import (
    AutonomyLevel,
    FindingResolutionStatus,
    IterationStatus,
    IterationTrigger,
    PatchOperation,
    RecommendationSource,
    SkippedRecommendationReason,
    StopReason,
)

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Bumped when the shape changes in a way a stored Iteration or trace
#: would notice — every prior M3 layer's own convention.
SCHEMA_VERSION = "3.6"

#: The only DesignIntent fields a patch may target — the real,
#: document-scoped decision surface brand.llm.command's own compiler
#: already reads (see fingerprint.design_intent_fingerprint). Naming
#: this once, here, is what lets patch.py and recommend.py both refuse
#: an out-of-vocabulary target the same way.
PATCHABLE_FIELDS: tuple[str, ...] = (
    "composition_strategy", "density", "typography_hierarchy",
    "color_strategy", "grid_strategy", "whitespace_strategy", "rhythm",
)


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DesignIntentPatch(BaseModel):
    """A minimal, targeted revision to one real ``DesignIntent`` field —
    ADOS-M3.6 §19. Never a competing schema: ``target`` must be one of
    ``PATCHABLE_FIELDS`` and ``value`` must be a real member of that
    field's own enum, both checked in ``patch.py`` before this is ever
    applied, not trusted here."""

    model_config = _Frozen

    target: str = Field(min_length=1, max_length=40)
    operation: PatchOperation = PatchOperation.SET
    value: str = Field(min_length=1, max_length=40)
    rationale: str = Field(default="", max_length=400)
    #: Free-text notes on what this patch deliberately leaves alone —
    #: descriptive only, the same posture DesignConstraint.source takes.
    constraints: tuple[str, ...] = ()


class Recommendation(BaseModel):
    """Finding -> Recommendation, ADOS-M3.6 §15. Not a ``CommandIntent``
    — a higher-level design correction, expressed as one
    ``DesignIntentPatch``. Command generation remains M3.5's job,
    applied to the ``DesignIntent`` this recommendation's patch
    produces."""

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    finding_fingerprint: str
    action: str = Field(min_length=1, max_length=40)
    rationale: str = Field(default="", max_length=400)
    priority: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    expected_effect: str = Field(default="", max_length=200)
    executable: bool = True
    source: RecommendationSource
    patch: DesignIntentPatch


class SkippedRecommendation(BaseModel):
    """A finding this package considered and did not turn into a
    recommendation — ADOS-M3.6 §55: recorded, never silently dropped."""

    model_config = _Frozen

    finding_fingerprint: str
    reason: SkippedRecommendationReason
    detail: str = Field(default="", max_length=400)


class FindingRecord(BaseModel):
    """One real ``Finding`` (serialized), plus the cross-iteration
    bookkeeping ADOS-M3.6 §68/§69/§70 needs. ``status`` is set by
    ``findings.py``'s classification against the parent iteration's own
    records — never inferred from "a command executed" (§68's own
    explicit rule)."""

    model_config = _Frozen

    fingerprint: str
    finding: dict[str, Any]
    status: FindingResolutionStatus
    first_seen_sequence: int
    last_seen_sequence: int


class IterationMetrics(BaseModel):
    """ADOS-M3.6 §28, the metrics every iteration computes."""

    model_config = _Frozen

    total_findings: int = 0
    blocking_findings: int = 0
    error_findings: int = 0
    warning_findings: int = 0
    resolved_findings: int = 0
    unresolved_findings: int = 0
    new_findings: int = 0
    regression_findings: int = 0
    command_count: int = 0
    changed_entity_count: int = 0
    constraint_violations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class IterationPolicy(BaseModel):
    """ADOS-M3.6 §33/§38/§63/§64 — every configurable budget/policy
    knob in one place, with conservative defaults."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_iterations: int = Field(default=5, ge=1, le=50)
    autonomy: AutonomyLevel = AutonomyLevel.SAFE
    max_llm_calls: int = Field(default=10, ge=0, le=100)
    allow_llm_recommendation: bool = True
    #: A recommendation fingerprint that has already FAILED (produced no
    #: improvement) this many times in the current lineage is retired —
    #: ADOS-M3.6 §36.
    max_repeated_recommendation_attempts: int = Field(default=2, ge=1, le=10)


class Iteration(BaseModel):
    """ADOS-M3.6's canonical, immutable iteration record — §5/§6."""

    model_config = _Frozen

    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=_short_id)
    project_id: str
    document_id: str
    parent_iteration_id: Optional[str] = None
    sequence: int = Field(ge=1)
    trigger: IterationTrigger
    status: IterationStatus
    stop_reason: Optional[StopReason] = None
    stage_log: tuple[str, ...] = ()

    # -- version safety (ADOS-M3.6 §7) ------------------------------------
    input_design_state_version: Optional[int] = None
    output_design_state_version: Optional[int] = None

    # -- inputs, preserved in full for reproducibility (ADOS-M3.6 §6) ----
    semantic_intent: dict[str, Any] = Field(default_factory=dict)
    content_fingerprint: str = ""
    narrative_plan: dict[str, Any] = Field(default_factory=dict)
    design_intent: dict[str, Any] = Field(default_factory=dict)
    design_intent_fingerprint: str = ""
    #: The recommendation (and its patch) that PRODUCED this iteration's
    #: DesignIntent from its parent's — ``None`` on the first iteration
    #: of a lineage. Carries ``finding_fingerprint`` so
    #: ``orchestrator.py`` can count repeated attempts per (finding,
    #: patch) pair (ADOS-M3.6 §36) without a separate field.
    applied_recommendation: Optional[Recommendation] = None

    # -- M3.5 + execution --------------------------------------------------
    command_plan: dict[str, Any] = Field(default_factory=dict)
    command_validation: dict[str, Any] = Field(default_factory=dict)
    execution_steps: tuple[dict[str, Any], ...] = ()
    page_plan: dict[str, Any] = Field(default_factory=dict)

    # -- evaluation ----------------------------------------------------
    evaluation: dict[str, Any] = Field(default_factory=dict)
    findings: tuple[FindingRecord, ...] = ()
    recommendations: tuple[Recommendation, ...] = ()
    skipped_recommendations: tuple[SkippedRecommendation, ...] = ()

    metrics: IterationMetrics = Field(default_factory=IterationMetrics)
    llm_calls: int = 0
    #: True when this iteration ran the full plan/generate/validate/
    #: execute/compose/evaluate pipeline in memory only — ADOS-M3.6 §57.
    #: A dry-run iteration is never persisted into a lineage's
    #: continuable history (its ``output_design_state_version`` is
    #: never real) and never written to Project/Document storage.
    dry_run: bool = False
    request_id: str = ""
    created_at: datetime = Field(default_factory=_now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class LoopResult(BaseModel):
    """The result of ``run_loop`` — an ordered lineage of ``Iteration``s
    plus the final decision (ADOS-M3.6 §32/§67)."""

    model_config = _Frozen

    project_id: str
    document_id: str
    iterations: tuple[Iteration, ...] = ()
    final_status: IterationStatus
    stop_reason: Optional[StopReason] = None
    total_llm_calls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
