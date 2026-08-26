"""
brand/llm/narrative/observability.py

ADOS-M3.3 §40 — extends ``brand.llm.observability``/
``brand.llm.content.observability``'s exact pattern to narrative
planning: one trace per ``plan_narrative`` call, capturing what §40
lists. The same in-memory, bounded recorder — see those modules' own
docstrings for why this is a debugging aid, not a durable audit store.

**This is also ADOS-M3.3 §46/§47's regeneration mechanism.** A
``NarrativePlan`` is not written into any project/document store by
this milestone (see this package's architecture doc for that scoping
decision) — every ``plan_narrative`` call produces an independent,
fully-formed plan, and the trace list is how a previous plan remains
inspectable after a regeneration: nothing here is overwritten, each
call gets its own ``request_id``.
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from brand.llm.narrative.model import NarrativePlan
from brand.validation.brand_validator import ValidationReport

logger = logging.getLogger(__name__)

_MAX_TRACES = 200


@dataclass(frozen=True)
class NarrativePlanTrace:
    request_id: str
    project_id: str
    content_model_version: Optional[int]
    semantic_intent_summary: dict[str, Any]
    document_type_id: str
    model: str
    prompt_version: str
    narrative_plan: dict[str, Any]
    validation_ok: bool
    finding_codes: tuple[str, ...]
    latency_ms: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "content_model_version": self.content_model_version,
            "semantic_intent_summary": self.semantic_intent_summary,
            "document_type_id": self.document_type_id,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "narrative_plan": self.narrative_plan,
            "validation_ok": self.validation_ok,
            "finding_codes": list(self.finding_codes),
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat(),
        }


_recent: deque[NarrativePlanTrace] = deque(maxlen=_MAX_TRACES)
_by_id: dict[str, NarrativePlanTrace] = {}


def record_narrative_trace(
    *,
    plan: NarrativePlan,
    validation: ValidationReport,
    semantic_intent_summary: dict[str, Any],
    document_type_id: str,
    model: str,
    prompt_version: str,
    latency_ms: float,
    request_id: Optional[str] = None,
) -> NarrativePlanTrace:
    trace = NarrativePlanTrace(
        request_id=request_id or uuid.uuid4().hex,
        project_id=plan.project_id,
        content_model_version=plan.content_model_version,
        semantic_intent_summary=semantic_intent_summary,
        document_type_id=document_type_id,
        model=model,
        prompt_version=prompt_version,
        narrative_plan=plan.to_dict(),
        validation_ok=validation.ok,
        finding_codes=tuple(f.code for f in validation.findings),
        latency_ms=latency_ms,
    )
    _recent.append(trace)
    _by_id[trace.request_id] = trace
    logger.info(
        "narrative_plan request_id=%s project_id=%s sections=%d ok=%s latency_ms=%.1f",
        trace.request_id, trace.project_id, len(plan.sections), validation.ok, latency_ms,
    )
    return trace


def recent_narrative_traces(limit: int = 50) -> list[NarrativePlanTrace]:
    return list(reversed(list(_recent)))[:limit]


def get_narrative_trace(request_id: str) -> Optional[NarrativePlanTrace]:
    return _by_id.get(request_id)


def clear_narrative_traces() -> None:
    _recent.clear()
    _by_id.clear()
