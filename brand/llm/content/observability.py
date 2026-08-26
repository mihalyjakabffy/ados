"""
brand/llm/content/observability.py

ADOS-M3.2 §33 — extends ``brand.llm.observability``'s pattern to
content resolution: one trace per ``resolve_content`` call, answering
exactly the questions §33 lists (which sources, which extractors, which
model, which prompt/context version, when, which validation ran, and
the resulting status mix). The same in-memory, bounded recorder — see
that module's own docstring for why this is a debugging aid, not a
durable audit store, and why it never stores full raw source text.
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from brand.llm.content.model import ContentIntelligenceModel
from brand.validation.brand_validator import ValidationReport

logger = logging.getLogger(__name__)

_MAX_TRACES = 200
_SOURCE_LABEL_PREVIEW_MAX = 120


@dataclass(frozen=True)
class ContentResolutionTrace:
    request_id: str
    project_id: str
    document_id: Optional[str]
    #: source_id -> the extractor/provider/model that actually produced
    #: something from it, e.g. "rule-based:keyword-v1" or "claude:claude-opus-5".
    source_extractors: dict[str, str]
    prompt_version: str
    status_counts: dict[str, int]
    validation_ok: bool
    finding_codes: tuple[str, ...]
    latency_ms: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "document_id": self.document_id,
            "source_extractors": self.source_extractors,
            "prompt_version": self.prompt_version,
            "status_counts": self.status_counts,
            "validation_ok": self.validation_ok,
            "finding_codes": list(self.finding_codes),
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat(),
        }


_recent: deque[ContentResolutionTrace] = deque(maxlen=_MAX_TRACES)
_by_id: dict[str, ContentResolutionTrace] = {}


def _status_counts(content: ContentIntelligenceModel) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fact in content.facts:
        counts[fact.status.value] = counts.get(fact.status.value, 0) + 1
    return counts


def record_content_trace(
    *,
    content: ContentIntelligenceModel,
    validation: ValidationReport,
    source_extractors: dict[str, str],
    prompt_version: str,
    latency_ms: float,
    document_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> ContentResolutionTrace:
    trace = ContentResolutionTrace(
        request_id=request_id or uuid.uuid4().hex,
        project_id=content.project_id,
        document_id=document_id,
        source_extractors=source_extractors,
        prompt_version=prompt_version,
        status_counts=_status_counts(content),
        validation_ok=validation.ok,
        finding_codes=tuple(f.code for f in validation.findings),
        latency_ms=latency_ms,
    )
    _recent.append(trace)
    _by_id[trace.request_id] = trace
    logger.info(
        "content_resolution request_id=%s project_id=%s sources=%d ok=%s latency_ms=%.1f",
        trace.request_id, trace.project_id, len(source_extractors), validation.ok, latency_ms,
    )
    return trace


def recent_content_traces(limit: int = 50) -> list[ContentResolutionTrace]:
    return list(reversed(list(_recent)))[:limit]


def get_content_trace(request_id: str) -> Optional[ContentResolutionTrace]:
    return _by_id.get(request_id)


def clear_content_traces() -> None:
    _recent.clear()
    _by_id.clear()
