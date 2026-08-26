"""
brand/llm/command/model.py

ADOS-M3.5's own domain objects, wrapping — never replacing — the real,
shipped :class:`~brand.creative.intent.CommandIntent`. A
:class:`GeneratedCommand` carries one real ``CommandIntent`` plus the
audit trail this milestone requires (why it exists, how safe it is,
whether it is idempotent); a :class:`CommandPlan` is the ordered result
of compiling one ``DesignIntent`` into zero or more of them, with every
lever this package considered and did *not* act on recorded as a
:class:`SkippedLever`, never silently dropped.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from brand.creative.intent import CommandIntent
from brand.llm.command.vocabulary import (
    CommandProvenance,
    CommandRejectionReason,
    CommandSafetyLevel,
)

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Bumped when the shape changes in a way a stored CommandPlan or trace
#: would notice — brand/llm/design/model.py's own convention.
SCHEMA_VERSION = "3.5"


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GeneratedCommand(BaseModel):
    """One real ``CommandIntent``, plus why this package produced it.

    ``source_field`` names the exact ``DesignIntent`` field (or a
    ``design_issues``/``constraints`` index) that drove this command —
    the same "reference, never restate" discipline M3.2-M3.4 apply to
    content, applied here to *justification*. ``idempotent`` is computed
    deterministically per intent type at generation time (see
    ``generation.py``): a density/emphasis nudge computed from a real
    gap is not idempotent (it moves a continuous value and a second,
    identical run over an *already-moved* state would compute a smaller
    or zero gap); ``recompose_page`` and a ``change_page_direction`` onto
    a direction already reached are.
    """

    model_config = _Frozen

    id: str = Field(default_factory=_short_id)
    intent: CommandIntent
    safety_level: CommandSafetyLevel
    provenance: CommandProvenance
    source_field: str = Field(min_length=1, max_length=80)
    rationale: str = Field(default="", max_length=400)
    idempotent: bool = True


class SkippedLever(BaseModel):
    """A semantic decision in the ``DesignIntent`` that this package
    considered and did **not** turn into a command — ADOS-M3.5's own
    "no decision by implication" principle: an unmapped or already-
    satisfied lever is real information for a reviewer, not a gap to
    hide by omission."""

    model_config = _Frozen

    source_field: str = Field(min_length=1, max_length=80)
    reason: CommandRejectionReason
    detail: str = Field(default="", max_length=400)


class CommandPlan(BaseModel):
    """The root object this package exists to produce: an ordered,
    provenanced, safety-classified compilation of one ``DesignIntent``
    into the existing ``CommandIntent`` vocabulary. Never applied by
    this package itself — see the ``__init__`` docstring."""

    model_config = _Frozen

    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=_short_id)
    project_id: str
    design_intent_id: str = ""
    narrative_plan_id: str = ""
    #: Copied from the source DesignIntent — the version this plan's
    #: commands were computed against. CMD-005 (validation.py) blocks a
    #: plan whose commands are applied against a DesignState that has
    #: since moved to a different version number.
    design_state_version: Optional[int] = None
    brand_id: Optional[str] = None
    brand_version: Optional[str] = None
    commands: tuple[GeneratedCommand, ...] = ()
    skipped: tuple[SkippedLever, ...] = ()
    #: Small, free-form bag — the generator that produced this, the
    #: document/base_plan ids it was resolved against. Same posture as
    #: brand.llm.design.model.DesignIntent.metadata.
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)

    def command(self, command_id: str) -> Optional[GeneratedCommand]:
        for c in self.commands:
            if c.id == command_id:
                return c
        return None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class CommandExecutionStep(BaseModel):
    """One applied command's before/after evidence. Built only by the
    API's ``/commands/apply`` route, from the real
    ``brand.creative.intent.IntentResolution`` and
    ``brand.creative.scope.PagePlanDiff`` those existing functions
    already return — never re-derived or approximated here."""

    model_config = _Frozen

    command_id: str
    direction_changed: bool
    content_changed: bool
    notes: tuple[str, ...] = ()
    changed_pages: tuple[int, ...] = ()
    plan_hash_before: str
    plan_hash_after: str
