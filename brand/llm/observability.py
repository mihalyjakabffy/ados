"""
brand/llm/observability.py

ADOS-M3.1 §19 — every semantic interpretation must be traceable. This is
a lightweight, in-memory recorder, not a database: M3.1's own scope is
"developer-facing inspection of intent" (§20), not a permanent audit
store, and the repository has no existing per-request tracing
infrastructure this could plug into (the only existing pattern,
``api.main``'s ``audit_log_middleware``, logs method/path/user for
mutating HTTP requests generically — it has no concept of a model call
or a SemanticIntent). A later phase that needs durable traces can
replace :func:`record_trace`'s storage without changing its signature.

Deliberately does *not* store the full assembled
``brand.llm.context.SemanticContext`` — that can carry a project
description, a brand's full identity, and more (ADOS-M3.1 §19: "do not
store sensitive raw context unnecessarily"). Only a short, truncated
preview of the request text is kept, plus ids — enough to find the trace
again, not enough to reconstruct the project from it.
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from brand.llm.context import SemanticContext
from brand.llm.provider import ProviderMetadata
from brand.llm.semantic_intent import SemanticIntent
from brand.validation.brand_validator import ValidationReport

logger = logging.getLogger(__name__)

_REQUEST_PREVIEW_MAX = 500
_MAX_TRACES = 200


@dataclass(frozen=True)
class SemanticIntentTrace:
    request_id: str
    project_id: Optional[str]
    document_id: Optional[str]
    provider: str
    model: str
    model_version: str
    prompt_version: str
    context_version: str
    request_preview: str
    semantic_intent: dict[str, Any]
    validation: dict[str, Any]
    latency_ms: float
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "document_id": self.document_id,
            "provider": self.provider,
            "model": self.model,
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
            "context_version": self.context_version,
            "request_preview": self.request_preview,
            "semantic_intent": self.semantic_intent,
            "validation": self.validation,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "created_at": self.created_at.isoformat(),
        }


#: Bounded ring buffer — a debugging aid, not a log store. Oldest traces
#: are silently dropped past `_MAX_TRACES`; nothing here is ever purged
#: for content reasons.
_recent: deque[SemanticIntentTrace] = deque(maxlen=_MAX_TRACES)
_by_id: dict[str, SemanticIntentTrace] = {}


def record_trace(
    *,
    intent: SemanticIntent,
    validation: ValidationReport,
    metadata: ProviderMetadata,
    context: SemanticContext,
    prompt_version: str,
    project_id: Optional[str] = None,
    document_id: Optional[str] = None,
) -> SemanticIntentTrace:
    trace = SemanticIntentTrace(
        request_id=uuid.uuid4().hex,
        project_id=project_id,
        document_id=document_id,
        provider=metadata.provider,
        model=metadata.model,
        model_version=metadata.model_version,
        prompt_version=prompt_version,
        context_version=context.context_version,
        request_preview=context.request[:_REQUEST_PREVIEW_MAX],
        semantic_intent=intent.to_dict(),
        validation=validation.to_dict(),
        latency_ms=metadata.latency_ms,
        input_tokens=metadata.input_tokens,
        output_tokens=metadata.output_tokens,
    )
    _recent.append(trace)
    _by_id[trace.request_id] = trace
    logger.info(
        "semantic_intent request_id=%s provider=%s model=%s ok=%s latency_ms=%.1f",
        trace.request_id, trace.provider, trace.model, validation.ok, trace.latency_ms,
    )
    return trace


def recent_traces(limit: int = 50) -> list[SemanticIntentTrace]:
    """Newest first — what a developer opening the inspection view wants."""
    return list(reversed(list(_recent)))[:limit]


def get_trace(request_id: str) -> Optional[SemanticIntentTrace]:
    return _by_id.get(request_id)


def clear_traces() -> None:
    """Test-only reset — a real deployment never needs to call this."""
    _recent.clear()
    _by_id.clear()
