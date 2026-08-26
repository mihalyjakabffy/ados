"""
brand/llm/narrative/planning.py

ADOS-M3.3's one orchestrator: real ``SemanticIntent`` + real
``ContentIntelligenceModel`` in, one validated, traced ``NarrativePlan``
out.

    SemanticIntent + ContentIntelligenceModel
        -> assemble_narrative_context (scoped, ADOS-M3.3 §33)
        -> NarrativeGenerator.generate (LLM, falling back to rule-based)
        -> stamp content-model version/timestamp (ADOS-M3.3 §46)
        -> validate_narrative_plan
        -> record_narrative_trace
        -> NarrativePlan

This module never resolves content itself — the
``ContentIntelligenceModel`` is a required argument, produced by
``brand.llm.content.resolution.resolve_content`` (M3.2) before this
function is ever called (the API router does exactly that). Not a
second content-resolution system, per ADOS-M3.3's own explicit
instruction.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Optional

from brand.llm.narrative.context import assemble_narrative_context
from brand.llm.narrative.generation import (
    LLMNarrativeGenerator,
    NarrativeGenerator,
    RuleBasedNarrativeGenerator,
)
from brand.llm.narrative.model import NarrativePlan
from brand.llm.narrative.vocabulary import NarrativeCompression
from brand.llm.provider import ProviderError

if TYPE_CHECKING:
    from brand.llm.content.model import ContentIntelligenceModel
    from brand.llm.semantic_intent import SemanticIntent
    from brand.project.model import Project

_NARRATIVE_LLM_ENABLED_ENV = "NARRATIVE_LLM_ENABLED"


def _default_generator() -> NarrativeGenerator:
    """LLM when configured and enabled, the deterministic rule-based
    generator otherwise — the identical gating
    ``brand.llm.content.resolution._default_text_extractor`` already
    applies, applied here to narrative generation."""
    enabled = os.environ.get(_NARRATIVE_LLM_ENABLED_ENV, "true").lower() != "false"
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not enabled or not api_key:
        return RuleBasedNarrativeGenerator()
    return LLMNarrativeGenerator()


def _semantic_intent_summary(semantic_intent: "SemanticIntent") -> dict[str, list[str]]:
    """Field names only, never values — the same "never store
    unnecessary sensitive source content" posture
    ``brand.llm.content.observability``'s own docstring commits to."""
    return {
        "explicit_fields": sorted(f.value for f in semantic_intent.explicit.set_fields()),
        "inferred_fields": sorted(f.value for f in semantic_intent.inferred.set_fields()),
        "ambiguous_fields": sorted(f.value for f in semantic_intent.ambiguous),
    }


def plan_narrative(
    project: "Project",
    content: "ContentIntelligenceModel",
    semantic_intent: "SemanticIntent",
    *,
    document_type_id: str = "",
    compression: NarrativeCompression = NarrativeCompression.MEDIUM,
    brand_name: str = "",
    generator: Optional[NarrativeGenerator] = None,
    request_id: Optional[str] = None,
) -> NarrativePlan:
    """Resolve one ``NarrativePlan`` for ``project`` from
    ``semantic_intent`` and the already-resolved ``content``. Never
    mutates ``project``, never touches
    ``brand.creative.composer``/``brand.creative.intent`` — ADOS-M3.3's
    own boundary."""
    from brand.llm.narrative.observability import record_narrative_trace
    from brand.llm.narrative.prompt import PROMPT_VERSION
    from brand.llm.narrative.validation import validate_narrative_plan

    start = time.perf_counter()
    gen = generator or _default_generator()
    context = assemble_narrative_context(
        semantic_intent, content, document_type_id=document_type_id,
        compression=compression, brand_name=brand_name, project_name=project.name,
    )

    try:
        plan, metadata = gen.generate(context)
    except ProviderError:
        plan, metadata = RuleBasedNarrativeGenerator().generate(context)

    plan = plan.model_copy(update={
        "content_model_version": content.version_number,
        "content_resolved_at": content.resolved_at,
    })

    validation = validate_narrative_plan(plan, content)
    record_narrative_trace(
        plan=plan, validation=validation,
        semantic_intent_summary=_semantic_intent_summary(semantic_intent),
        document_type_id=document_type_id,
        model=metadata.model if metadata else "rule-based",
        prompt_version=PROMPT_VERSION,
        latency_ms=(time.perf_counter() - start) * 1000,
        request_id=request_id,
    )
    return plan
