"""
brand/llm/extractor.py

``SemanticIntentExtractor`` — the one public entry point for ADOS-M3.1.
Orchestrates exactly the pipeline ADOS-M3.1 §9/§11 describes and no
further:

    request + real context
        -> LLMProvider.extract()      (schema validation happens inside
                                        this call — a schema-invalid
                                        response never becomes a Python
                                        SemanticIntent)
        -> validate_semantic_intent() (domain validation)
        -> record_trace()             (observability)
        -> ExtractionResult

It never calls ``brand.creative.intent`` or
``brand.creative.composer.compose`` — ADOS-M3.1 §11's "no execution"
rule is enforced by this module simply not importing them, not by a
runtime check.

Provider selection mirrors ``services.agents.base_agent.BaseAgent``'s
own contract exactly: LLM first when enabled and configured, a
deterministic fallback on anything else — disabled, no credentials, or
a failed call. The pipeline degrades, it does not break.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from brand.llm.context import ConversationTurn, SemanticContext, build_semantic_context
from brand.llm.observability import SemanticIntentTrace, record_trace
from brand.llm.prompt import PROMPT_VERSION, build_system_prompt
from brand.llm.provider import LLMProvider, ProviderError, ProviderMetadata
from brand.llm.semantic_intent import SemanticIntent
from brand.llm.validation import validate_semantic_intent
from brand.validation.brand_validator import ValidationReport

if TYPE_CHECKING:
    from brand.design_state.model import DesignState
    from brand.models.brand import Brand
    from brand.project.model import Project

logger = logging.getLogger(__name__)

_LLM_ENABLED_ENV = "SEMANTIC_INTENT_LLM_ENABLED"


@dataclass(frozen=True)
class ExtractionResult:
    intent: SemanticIntent
    validation: ValidationReport
    metadata: ProviderMetadata
    context: SemanticContext
    trace: SemanticIntentTrace

    def to_dict(self) -> dict:
        return {
            "intent": self.intent.to_dict(),
            "validation": self.validation.to_dict(),
            "request_id": self.trace.request_id,
        }


class SemanticIntentExtractor:
    """``provider``/``fallback_provider`` are injectable for tests — the
    default resolution (real provider if configured, rule-based
    otherwise) is what every non-test caller gets."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        fallback_provider: Optional[LLMProvider] = None,
    ) -> None:
        self._provider = provider
        self._fallback = fallback_provider or _default_fallback()

    def extract(
        self,
        request: str,
        *,
        project: Optional["Project"] = None,
        brand: Optional["Brand"] = None,
        design_state: Optional["DesignState"] = None,
        conversation: tuple[ConversationTurn, ...] = (),
    ) -> ExtractionResult:
        context = build_semantic_context(
            request, project=project, brand=brand, design_state=design_state,
            conversation=conversation,
        )
        system_prompt = build_system_prompt()

        provider = self._provider or _resolve_default_provider()
        try:
            intent, metadata = provider.extract(system_prompt, context)
        except ProviderError as exc:
            logger.warning(
                "SemanticIntentExtractor: provider %s failed (%s) — falling "
                "back to the deterministic rule-based provider",
                type(provider).__name__, exc,
            )
            intent, metadata = self._fallback.extract(system_prompt, context)

        validation = validate_semantic_intent(intent, context)
        trace = record_trace(
            intent=intent, validation=validation, metadata=metadata, context=context,
            prompt_version=PROMPT_VERSION,
            project_id=project.id if project is not None else None,
            document_id=design_state.document.id if design_state is not None else None,
        )
        return ExtractionResult(
            intent=intent, validation=validation, metadata=metadata,
            context=context, trace=trace,
        )


def _default_fallback() -> LLMProvider:
    from brand.llm.providers.rule_based_provider import RuleBasedProvider

    return RuleBasedProvider()


def _resolve_default_provider() -> LLMProvider:
    """LLM if enabled and configured, the rule-based provider otherwise —
    ``services.agents.base_agent.BaseAgent.run``'s exact gating, applied
    to this package's own provider abstraction instead of a hardcoded
    Gemini client."""

    enabled = os.environ.get(_LLM_ENABLED_ENV, "true").lower() != "false"
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not enabled or not api_key:
        return _default_fallback()

    from brand.llm.providers.claude_provider import ClaudeProvider

    return ClaudeProvider()
