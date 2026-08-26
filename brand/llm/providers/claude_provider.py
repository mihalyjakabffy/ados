"""
brand/llm/providers/claude_provider.py

The concrete, real-model ``LLMProvider`` (ADOS-M3.1 §8/§9). Uses
``client.messages.parse(output_format=...)`` — the strongest
structured-output mechanism the Claude API has, per ADOS-M3.1 §9's
"schema validity is not sufficient" instruction: pydantic validates the
shape on the way back (raising if the model returns something
schema-invalid), and each caller runs its own deeper domain validation
afterwards.

No Anthropic SDK type ever crosses back out of :func:`call_structured`
or :meth:`ClaudeProvider.extract` — only plain ADOS domain types and
``ProviderMetadata`` (``brand.llm.provider``'s own contract).

:func:`get_client` and :func:`call_structured` are the one shared,
low-level path to Claude every structured extractor in this repository
uses — ``ClaudeProvider`` (M3.1, ``SemanticIntent``) and
``brand.llm.content.extraction.LLMContentExtractor`` (M3.2, content
extraction) both call through here rather than each constructing their
own ``anthropic.Anthropic()`` client (ADOS-M3.2 §11: "do not create a
second Claude client").
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional, TypeVar

from pydantic import BaseModel

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

_OutputT = TypeVar("_OutputT", bound=BaseModel)


def get_client() -> Any:
    """A fresh Anthropic client. Callers cache their own instance (see
    ``ClaudeProvider._get_client``) — this function makes no assumption
    about a caller's lifecycle, so two extractors caching independently
    still only ever depend on this one construction path."""
    try:
        import anthropic
    except ImportError as exc:
        raise ProviderError(
            "the `anthropic` package is not installed. Run: pip install anthropic"
        ) from exc
    try:
        return anthropic.Anthropic()
    except Exception as exc:                                    # noqa: BLE001
        raise ProviderError(f"could not construct an Anthropic client: {exc}") from exc


def call_structured(
    client: Any,
    *,
    model: str,
    max_tokens: int,
    system_prompt: str,
    user_message: str,
    output_format: type[_OutputT],
    provider_name: str = "claude",
) -> tuple[_OutputT, ProviderMetadata]:
    """One structured-output call, typed by whatever pydantic model the
    caller passes as ``output_format`` — ``SemanticIntent``,
    ``RawExtraction``, or any future structured extraction schema."""
    start = time.perf_counter()
    try:
        response = client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            output_format=output_format,
        )
    except Exception as exc:                               # noqa: BLE001
        # Deliberately uniform, not a missed distinction: the SDK
        # already retries the retryable cases (429/5xx/connection)
        # before raising, and every remaining failure — auth, schema,
        # refusal, a 400 — gets the exact same treatment from the
        # extractor (fall back to a deterministic provider), the same
        # posture services.agents.base_agent.BaseAgent already takes.
        raise ProviderError(f"Claude call failed: {exc}") from exc
    latency_ms = (time.perf_counter() - start) * 1000

    if getattr(response, "stop_reason", None) == "refusal":
        raise ProviderError(
            f"Claude declined the request (stop_details={getattr(response, 'stop_details', None)})"
        )

    parsed = getattr(response, "parsed_output", None)
    if parsed is None:
        raise ProviderError("Claude response carried no parsed_output")
    if not isinstance(parsed, output_format):
        # Defensive: parse() is documented to return the requested type,
        # but no caller of this function ever hands a raw dict onward.
        try:
            parsed = output_format.model_validate(parsed)
        except Exception as exc:                           # noqa: BLE001
            raise ProviderError(
                f"Claude response did not validate as {output_format.__name__}: {exc}"
            ) from exc

    usage = getattr(response, "usage", None)
    metadata = ProviderMetadata(
        provider=provider_name,
        model=model,
        model_version=getattr(response, "model", model),
        latency_ms=latency_ms,
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
    )
    return parsed, metadata


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
        return call_structured(
            client, model=self._model, max_tokens=self._max_tokens,
            system_prompt=system_prompt, user_message=user_message,
            output_format=SemanticIntent,
        )

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = get_client()
        return self._client
