"""
brand/llm/provider.py

``LLMProvider`` — the abstraction ADOS-M3.1 §8 asks for, so the ADOS
domain never becomes coupled to one model vendor. Every concrete
provider (``brand.llm.providers.claude_provider.ClaudeProvider``, and
the deterministic ``brand.llm.providers.rule_based_provider.RuleBasedProvider``
used when no LLM is configured) implements exactly this interface, and
returns exactly these two domain types — never an Anthropic/OpenAI/
Gemini response object. A caller of :meth:`LLMProvider.extract` cannot
tell which vendor answered, or whether one answered at all.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from brand.llm.context import SemanticContext
from brand.llm.semantic_intent import SemanticIntent


class ProviderError(RuntimeError):
    """The provider could not produce a SemanticIntent.

    Raised for anything from "the SDK is not installed" to "the model
    call failed" to "the response didn't validate against the schema" —
    the caller (``brand.llm.extractor.SemanticIntentExtractor``) treats
    every one of these identically: fall back, don't crash, exactly the
    existing ``services.agents.base_agent.BaseAgent`` convention.
    """


@dataclass(frozen=True)
class ProviderMetadata:
    """What ADOS-M3.1 §19's observability needs about *how* an intent was
    produced — never what it was produced from (that's the trace's own
    ``context_version`` field, not this provider-level one)."""

    provider: str
    model: str
    model_version: str = ""
    latency_ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    extra: dict[str, Any] | None = None


class LLMProvider(ABC):
    """One call: system prompt + context in, a validated SemanticIntent
    and its metadata out. No conversation state, no tool loop, no
    retries beyond whatever the concrete provider's own client already
    does — a SemanticIntent extraction is one request, not an agent."""

    @abstractmethod
    def extract(
        self, system_prompt: str, context: SemanticContext,
    ) -> tuple[SemanticIntent, ProviderMetadata]:
        """Raise :class:`ProviderError` on any failure — network, schema,
        missing credentials, refusal. Never raises a vendor-specific
        exception type to the caller."""
