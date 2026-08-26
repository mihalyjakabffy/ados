"""
ADOS-M3.1 — brand/llm/providers/claude_provider.py.

No live network calls here (CI carries no ANTHROPIC_API_KEY, and this
suite must not depend on one) — only the provider's own contract: it
never leaks an SDK exception type, never returns a non-SemanticIntent,
and behaves as a plain LLMProvider to any caller.
"""

from __future__ import annotations

import pytest

from brand.llm.context import build_semantic_context
from brand.llm.prompt import build_system_prompt
from brand.llm.provider import LLMProvider, ProviderError
from brand.llm.providers.claude_provider import ClaudeProvider


def test_claude_provider_is_an_llm_provider():
    assert isinstance(ClaudeProvider(), LLMProvider)


def test_default_model_is_opus_5(monkeypatch):
    monkeypatch.delenv("SEMANTIC_INTENT_MODEL", raising=False)
    assert ClaudeProvider()._model == "claude-opus-5"


def test_model_is_overridable_via_env(monkeypatch):
    monkeypatch.setenv("SEMANTIC_INTENT_MODEL", "claude-sonnet-5")
    assert ClaudeProvider()._model == "claude-sonnet-5"


def test_missing_api_key_raises_provider_error_not_an_sdk_exception(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    provider = ClaudeProvider()
    ctx = build_semantic_context("Create a portfolio.")
    with pytest.raises(ProviderError):
        provider.extract(build_system_prompt(), ctx)


def test_provider_error_never_exposes_a_vendor_exception_type(monkeypatch):
    """Whatever the underlying failure, the caller only ever sees
    ProviderError — brand.llm.provider's own contract."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    provider = ClaudeProvider()
    ctx = build_semantic_context("anything")
    try:
        provider.extract(build_system_prompt(), ctx)
        pytest.fail("expected ProviderError")
    except ProviderError:
        pass
    except Exception as exc:                                    # noqa: BLE001
        pytest.fail(f"leaked a non-ProviderError exception: {type(exc).__name__}")
