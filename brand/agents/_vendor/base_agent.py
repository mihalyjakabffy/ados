"""
brand/agents/_vendor/base_agent.py

Vendored from the source monorepo's ``services/agents/base_agent.py`` at the
point ADOS was split into its own repository. ``brand/agents/brand_agent.py``
is the only ADOS agent that subclasses it; kept here verbatim rather than
dropped, since the alternative was deleting the 27 tests in
``tests_brand/test_brand_agent.py`` that exercise it.

BaseAgent — shared LLM client and rule-based fallback.

All agents subclass this.  The Gemini client is initialised lazily on
first use so the module imports cleanly without an API key.  If the key is
absent (or the `google-generativeai` package is not installed), every agent
falls back to deterministic rule-based logic — the pipeline degrades
gracefully rather than raising at startup.

Environment variables:
    GEMINI_API_KEY      — API key (required for LLM mode)
    AGENT_MODEL         — Gemini model ID (default: gemini-2.0-flash-lite)
    AGENT_MAX_TOKENS    — max tokens per agent call (default: 1024)
    AGENT_LLM_ENABLED   — set to "false" to force rule-based mode even with a key
"""

from __future__ import annotations

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.0-flash-lite"
_DEFAULT_MAX_TOKENS = 1024
_LLM_ENABLED = os.environ.get("AGENT_LLM_ENABLED", "true").lower() != "false"


class AgentError(RuntimeError):
    """Raised when an agent cannot produce a valid output after all retries."""


class BaseAgent(ABC):
    """
    Abstract base for all Phase-2 agents.

    Subclasses implement:
        system_prompt (property)  — cached system prompt string
        _run_llm(messages)        — build the message list for this agent
        _run_rules(state)         — deterministic fallback

    The public entry point is always `run(state) → AgentState`.
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self._model = os.environ.get("AGENT_MODEL", model)
        self._max_tokens = int(os.environ.get("AGENT_MAX_TOKENS", max_tokens))
        self._client: Optional[Any] = None   # lazy Anthropic client

    # ------------------------------------------------------------------
    # Subclass contract
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Long, stable system prompt — eligible for Anthropic prompt caching."""

    @abstractmethod
    def _build_user_message(self, state: Any) -> str:
        """Render the per-call user message from the current AgentState."""

    @abstractmethod
    def _parse_llm_response(self, response_text: str, state: Any) -> Any:
        """Parse the raw LLM text into the updated AgentState."""

    @abstractmethod
    def _run_rules(self, state: Any) -> Any:
        """Deterministic fallback — must not call the LLM."""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, state: Any) -> Any:
        """
        Execute the agent on the current state.

        Tries the LLM path first (if enabled and API key present).
        Falls back to rule-based logic on any error.
        """
        if not _LLM_ENABLED:
            logger.debug("%s: LLM disabled — using rule-based fallback", self.__class__.__name__)
            return self._run_rules(state)

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.debug("%s: no GEMINI_API_KEY — using rule-based fallback", self.__class__.__name__)
            return self._run_rules(state)

        try:
            return self._run_llm(state)
        except Exception as exc:
            logger.warning(
                "%s: LLM call failed (%s) — falling back to rule-based logic",
                self.__class__.__name__, exc,
            )
            return self._run_rules(state)

    # ------------------------------------------------------------------
    # LLM call (shared machinery)
    # ------------------------------------------------------------------

    def _run_llm(self, state: Any) -> Any:
        model = self._get_client()
        user_message = self._build_user_message(state)

        response = model.generate_content(user_message)
        raw = response.text

        logger.debug(
            "%s LLM response (%d chars): %s…",
            self.__class__.__name__, len(raw), raw[:200],
        )
        return self._parse_llm_response(raw, state)

    def _get_client(self) -> Any:
        """Return a configured Gemini GenerativeModel (cached after first call)."""
        if self._client is not None:
            return self._client
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise AgentError(
                "The `google-generativeai` package is not installed. "
                "Run: pip install google-generativeai"
            ) from exc

        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self._client = genai.GenerativeModel(
            model_name=self._model,
            system_instruction=self.system_prompt,
            generation_config={"max_output_tokens": self._max_tokens},
        )
        return self._client

    # ------------------------------------------------------------------
    # Intent sanitisation
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_intent(intent: str) -> str:
        """
        Sanitize user_intent before inserting into LLM prompt.
        - Truncate to 500 chars
        - Remove common injection patterns
        - Strip leading/trailing whitespace
        """
        if not intent:
            return ""
        # Truncate
        intent = intent[:500]
        # Remove injection patterns (case-insensitive)
        _INJECTION_PATTERNS = [
            r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions?",
            r"system\s*:?\s*override",
            r"you\s+are\s+now\s+(in\s+)?(unrestricted|jailbreak|developer|DAN)",
            r"forget\s+(all\s+)?(previous|your)\s+(instructions?|training)",
            r"disregard\s+(all\s+)?(previous|prior)\s+instructions?",
            r"new\s+instruction[s:]",
            r"---+\s*(system|prompt|instruction)",
            r"\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>",
            r"act\s+as\s+(if\s+you\s+are|a\s+)",
        ]
        for pattern in _INJECTION_PATTERNS:
            intent = re.sub(pattern, "[FILTERED]", intent, flags=re.IGNORECASE)
        return intent.strip()

    # ------------------------------------------------------------------
    # JSON parsing helper
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> dict:
        """
        Extract the first JSON object from an LLM response string.

        The LLM may wrap JSON in markdown fences or add prose around it.
        This method is tolerant of both.
        """
        # Try raw first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try stripping markdown fences
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Last resort: find the FIRST properly matched { ... } block using bracket counting
        start = text.find("{")
        if start != -1:
            depth = 0
            end = -1
            for i, ch in enumerate(text[start:], start=start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass

        raise AgentError(
            f"Could not extract valid JSON from LLM response:\n{text[:500]}"
        )
