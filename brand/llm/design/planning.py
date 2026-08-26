"""
brand/llm/design/planning.py

ADOS-M3.4's one orchestrator: a real ``NarrativePlan`` (M3.3) + real
``ContentIntelligenceModel`` (M3.2) + real ``Brand``/``CreativeDirection``/
``DesignState`` (existing ADOS systems) in, one validated, traced
``DesignIntent`` out.

    NarrativePlan + Brand + CreativeDirection + DesignState
        -> assemble_design_context (scoped, ADOS-M3.4 §37)
        -> DesignIntentGenerator.generate (LLM, falling back to rule-based)
        -> stamp version metadata (ADOS-M3.4 §60)
        -> validate_design_intent
        -> record_design_trace
        -> DesignIntent

This module never resolves a NarrativePlan, a ContentIntelligenceModel,
a Brand, or a DesignState itself — every one of them is a required or
optional argument, produced by the systems that already own producing
them (M3.2/M3.3's own resolution pipelines, the project's brand store,
``brand.design_state.build``). Not a second resolution system, per
ADOS-M3.4's own explicit instruction (§3: "reuse existing concepts").
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Optional

from brand.llm.design.context import assemble_design_context
from brand.llm.design.generation import (
    DesignIntentGenerator,
    LLMDesignIntentGenerator,
    RuleBasedDesignIntentGenerator,
)
from brand.llm.design.model import DesignIntent
from brand.llm.provider import ProviderError

if TYPE_CHECKING:
    from brand.creative.direction import CreativeDirection
    from brand.design_state.model import DesignState
    from brand.llm.content.model import ContentIntelligenceModel
    from brand.llm.narrative.model import NarrativePlan
    from brand.models.brand import Brand
    from brand.project.model import Project

_DESIGN_INTENT_LLM_ENABLED_ENV = "DESIGN_INTENT_LLM_ENABLED"


def _default_generator() -> DesignIntentGenerator:
    """LLM when configured and enabled, the deterministic rule-based
    generator otherwise — the identical gating
    ``brand.llm.narrative.planning._default_generator`` already
    applies, applied here to design-intent generation."""
    enabled = os.environ.get(_DESIGN_INTENT_LLM_ENABLED_ENV, "true").lower() != "false"
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not enabled or not api_key:
        return RuleBasedDesignIntentGenerator()
    return LLMDesignIntentGenerator()


def plan_design_intent(
    project: "Project",
    content: "ContentIntelligenceModel",
    narrative_plan: "NarrativePlan",
    *,
    brand: Optional["Brand"] = None,
    creative_direction: Optional["CreativeDirection"] = None,
    design_state: Optional["DesignState"] = None,
    generator: Optional[DesignIntentGenerator] = None,
    request_id: Optional[str] = None,
) -> DesignIntent:
    """Resolve one ``DesignIntent`` for ``project`` from
    ``narrative_plan`` and the given Brand/CreativeDirection/
    DesignState context. Never mutates any of its arguments, never
    touches ``brand.creative.composer``/``brand.creative.intent``, and
    never calls a renderer — ADOS-M3.4's own boundary."""
    from brand.llm.design.observability import record_design_trace
    from brand.llm.design.prompt import PROMPT_VERSION
    from brand.llm.design.validation import validate_design_intent

    start = time.perf_counter()
    gen = generator or _default_generator()
    context = assemble_design_context(
        narrative_plan, content, brand=brand, creative_direction=creative_direction,
        design_state=design_state, project_name=project.name,
    )

    try:
        design_intent, metadata = gen.generate(context)
    except ProviderError:
        design_intent, metadata = RuleBasedDesignIntentGenerator().generate(context)

    validation = validate_design_intent(design_intent, narrative_plan, content, context.brand)
    record_design_trace(
        design_intent=design_intent, validation=validation,
        model=metadata.model if metadata else "rule-based", prompt_version=PROMPT_VERSION,
        latency_ms=(time.perf_counter() - start) * 1000, request_id=request_id,
    )
    return design_intent
