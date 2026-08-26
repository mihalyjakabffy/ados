"""
brand/llm/providers/claude_provider.py

The concrete, real-model ``LLMProvider`` (ADOS-M3.1 §8/§9). Uses
``client.messages.parse(output_format=SemanticIntent)`` — the strongest
structured-output mechanism the Claude API has, per ADOS-M3.1 §9's
"schema validity is not sufficient" instruction: pydantic validates the
shape on the way back (raising if the model returns something
schema-invalid), and this module's caller
(``brand.llm.extractor.SemanticIntentExtractor``) runs the deeper domain
validation (``brand.llm.validation``) afterwards.

No Anthropic SDK type ever crosses back out of :meth:`extract` — only
``SemanticIntent`` and ``ProviderMetadata``, both plain ADOS domain
types (``brand.llm.provider``'s own contract).
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

from brand.llm.context import SemanticContext
from brand.llm.prompt import build_user_message
from brand.llm.provider import LLMProvider, ProviderError, ProviderMetadata
from brand.llm.semantic_intent import SemanticIntent

#: claude-api skill: "ALWAYS use claude-opus-5 unless the user explicitly
#: names a different model" — configurable via env var for the same
#: reason ``services.agents.base_agent.BaseAgent`` reads ``AGENT_MODEL``,
#: never hardcoded past that one override point.
_DEFAULT_MODEL = "claude-opus-5"
_DEFAULT_MAX_TOKENS = 4096


class ClaudeProvider(LLMProvider):
    """Reads ``ANTHROPIC_API_KEY`` (or an ``ant auth login`` profile) via
    the SDK's own zero-arg client — never asks for a key directly."""

    def __init__(self, model: str = _DEFAULT_MODEL, max_tokens: int = _DEFAULT_MAX_TOKENS) -> None:
        self._model = os.environ.get("SEMANTIC_INTENT_MODEL", model)
        self._max_tokens = int(os.environ.get("SEMANTIC_INTENT_MAX_TOKENS", max_tokens))
        self._client: Optional[Any] = None

    def extract(
        self, system_prompt: str, context: SemanticContext,
    ) -> tuple[SemanticIntent, ProviderMetadata]:
        client = self._get_client()
        user_message = build_user_message(context)

        start = time.perf_counter()
        try:
            response = client.messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                output_format=SemanticIntent,
            )
        except Exception as exc:                               # noqa: BLE001
            # Deliberately uniform, not a missed distinction: the SDK
            # already retries the retryable cases (429/5xx/connection)
            # before raising, and every remaining failure — auth, schema,
            # refusal, a 400 — gets the exact same treatment from the
            # extractor (fall back to the rule-based provider), the same
            # posture services.agents.base_agent.BaseAgent already takes.
            raise ProviderError(f"Claude call failed: {exc}") from exc
        latency_ms = (time.perf_counter() - start) * 1000

        if getattr(response, "stop_reason", None) == "refusal":
            raise ProviderError(
                f"Claude declined the request (stop_details={getattr(response, 'stop_details', None)})"
            )

        intent = getattr(response, "parsed_output", None)
        if intent is None:
            raise ProviderError("Claude response carried no parsed_output")
        if not isinstance(intent, SemanticIntent):
            # Defensive: parse() is documented to return the requested type,
            # but this provider never hands a raw dict back to the caller —
            # see this module's own docstring.
            try:
                intent = SemanticIntent.model_validate(intent)
            except Exception as exc:                           # noqa: BLE001
                raise ProviderError(f"Claude response did not validate as SemanticIntent: {exc}") from exc

        usage = getattr(response, "usage", None)
        metadata = ProviderMetadata(
            provider="claude",
            model=self._model,
            model_version=getattr(response, "model", self._model),
            latency_ms=latency_ms,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )
        return intent, metadata

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError(
                "the `anthropic` package is not installed. Run: pip install anthropic"
            ) from exc
        try:
            self._client = anthropic.Anthropic()
        except Exception as exc:                                # noqa: BLE001
            raise ProviderError(f"could not construct an Anthropic client: {exc}") from exc
        return self._client
