"""
brand/llm/command/observability.py

Extends ADOS-M3.1/M3.2/M3.3/M3.4's exact in-memory, bounded trace
pattern to command generation: one trace per ``plan_commands`` call.

**This is also this milestone's regeneration mechanism** (same as every
prior M3 layer): a ``CommandPlan`` is not written into any project/
document store — every ``plan_commands`` call produces an independent,
fully-formed plan with its own id, and this trace list is how a
previous compilation remains inspectable (a different DesignIntent
revision, a DesignState that has since moved on) without recomputing it.
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from brand.llm.command.model import CommandPlan

logger = logging.getLogger(__name__)

_MAX_TRACES = 200


@dataclass(frozen=True)
class CommandPlanTrace:
    request_id: str
    project_id: str
    design_intent_id: str
    design_state_version: Optional[int]
    generator: str
    command_plan: dict[str, Any]
    command_count: int
    skipped_count: int
    error: Optional[str]
    latency_ms: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "design_intent_id": self.design_intent_id,
            "design_state_version": self.design_state_version,
            "generator": self.generator,
            "command_plan": self.command_plan,
            "command_count": self.command_count,
            "skipped_count": self.skipped_count,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat(),
        }


_recent: deque[CommandPlanTrace] = deque(maxlen=_MAX_TRACES)
_by_id: dict[str, CommandPlanTrace] = {}


def record_command_trace(
    plan: CommandPlan,
    *,
    request_id: Optional[str] = None,
    latency_ms: float = 0.0,
    error: Optional[str] = None,
) -> CommandPlanTrace:
    trace = CommandPlanTrace(
        request_id=request_id or uuid.uuid4().hex,
        project_id=plan.project_id, design_intent_id=plan.design_intent_id,
        design_state_version=plan.design_state_version,
        generator=str(plan.metadata.get("generator", "")),
        command_plan=plan.to_dict(),
        command_count=len(plan.commands), skipped_count=len(plan.skipped),
        error=error, latency_ms=latency_ms,
    )
    _recent.append(trace)
    _by_id[trace.request_id] = trace
    logger.info(
        "command_plan request_id=%s project_id=%s commands=%d skipped=%d latency_ms=%.1f",
        trace.request_id, trace.project_id, trace.command_count, trace.skipped_count, latency_ms,
    )
    return trace


def recent_command_traces(limit: int = 50) -> list[CommandPlanTrace]:
    return list(reversed(list(_recent)))[:limit]


def get_command_trace(request_id: str) -> Optional[CommandPlanTrace]:
    return _by_id.get(request_id)


def clear_command_traces() -> None:
    _recent.clear()
    _by_id.clear()
