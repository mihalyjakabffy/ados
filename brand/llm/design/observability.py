"""
brand/llm/design/observability.py

ADOS-M3.4 §61 — extends ADOS-M3.1/M3.2/M3.3's exact in-memory, bounded
trace pattern to design-intent generation: one trace per
``plan_design_intent`` call, capturing what §61 lists. See those
modules' own docstrings for why this is a debugging aid, not a durable
audit store.

**This is also ADOS-M3.4 §55's regeneration mechanism**, the same way
``brand.llm.narrative.observability`` is ADOS-M3.3's: a ``DesignIntent``
is not written into any project/document store by this milestone —
every ``plan_design_intent`` call produces an independent,
fully-formed intent with its own id, and the trace list is how a
previous one remains inspectable after a regeneration (a different
Brand, a different narrative depth, more assets).
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from brand.llm.design.model import DesignIntent
from brand.validation.brand_validator import ValidationReport

logger = logging.getLogger(__name__)

_MAX_TRACES = 200


@dataclass(frozen=True)
class DesignIntentTrace:
    request_id: str
    project_id: str
    narrative_plan_id: str
    content_model_version: Optional[int]
    brand_id: Optional[str]
    brand_version: Optional[str]
    design_state_version: Optional[int]
    model: str
    prompt_version: str
    design_intent: dict[str, Any]
    validation_ok: bool
    finding_codes: tuple[str, ...]
    latency_ms: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "narrative_plan_id": self.narrative_plan_id,
            "content_model_version": self.content_model_version,
            "brand_id": self.brand_id,
            "brand_version": self.brand_version,
            "design_state_version": self.design_state_version,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "design_intent": self.design_intent,
            "validation_ok": self.validation_ok,
            "finding_codes": list(self.finding_codes),
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat(),
        }


_recent: deque[DesignIntentTrace] = deque(maxlen=_MAX_TRACES)
_by_id: dict[str, DesignIntentTrace] = {}


def record_design_trace(
    *,
    design_intent: DesignIntent,
    validation: ValidationReport,
    model: str,
    prompt_version: str,
    latency_ms: float,
    request_id: Optional[str] = None,
) -> DesignIntentTrace:
    trace = DesignIntentTrace(
        request_id=request_id or uuid.uuid4().hex,
        project_id=design_intent.project_id, narrative_plan_id=design_intent.narrative_plan_id,
        content_model_version=design_intent.content_model_version,
        brand_id=design_intent.brand_id, brand_version=design_intent.brand_version,
        design_state_version=design_intent.design_state_version,
        model=model, prompt_version=prompt_version, design_intent=design_intent.to_dict(),
        validation_ok=validation.ok, finding_codes=tuple(f.code for f in validation.findings),
        latency_ms=latency_ms,
    )
    _recent.append(trace)
    _by_id[trace.request_id] = trace
    logger.info(
        "design_intent request_id=%s project_id=%s sections=%d ok=%s latency_ms=%.1f",
        trace.request_id, trace.project_id, len(design_intent.section_designs), validation.ok, latency_ms,
    )
    return trace


def recent_design_traces(limit: int = 50) -> list[DesignIntentTrace]:
    return list(reversed(list(_recent)))[:limit]


def get_design_trace(request_id: str) -> Optional[DesignIntentTrace]:
    return _by_id.get(request_id)


def clear_design_traces() -> None:
    _recent.clear()
    _by_id.clear()
