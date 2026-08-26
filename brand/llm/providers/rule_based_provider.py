"""
brand/llm/providers/rule_based_provider.py

The deterministic fallback every existing ADOS agent already has
(``services.agents.base_agent.BaseAgent``'s own "the pipeline degrades,
it does not break" contract, applied here). Used whenever no LLM is
configured or reachable — including every automated test run in this
repository, since CI carries no ``ANTHROPIC_API_KEY``.

This is deliberately conservative, not a small language model in
disguise: where a real LLM would use judgement, this provider either
matches an unambiguous keyword cue or marks the field ambiguous. It is
not expected to reproduce ADOS-M3.1's nuanced worked examples (§14-16) —
those are precisely the cases a probabilistic reader is for. What it
must do, always, is produce a schema-valid, self-consistent
SemanticIntent that never claims more certainty than a keyword match
actually earns.
"""

from __future__ import annotations

import re
import time

from brand.llm.context import SemanticContext
from brand.llm.provider import LLMProvider, ProviderMetadata
from brand.llm.semantic_intent import SemanticIntent, SemanticFieldValues
from brand.llm.vocabulary import Action, SemanticField, Target

#: (Action, cues) in priority order — first match wins. "create" is
#: checked before "modify" so "Create X... make it feel like Y" resolves
#: to create, not to a spurious modify hit on "make it" (ADOS-M3.1 §14).
_ACTION_CUES: tuple[tuple[Action, tuple[str, ...]], ...] = (
    (Action.CREATE, ("create", "make a ", "make me ", "generate a", "build a", "new document")),
    (Action.TRANSFORM, ("turn this into", "turn it into", "transform", "convert to")),
    (Action.COMPARE, ("compare", " versus ", " vs ", " vs. ")),
    (Action.SUMMARIZE, ("summarize", "summarise", "condense", "shorten")),
    (Action.REGENERATE, ("regenerate", "start over", "recreate")),
    (Action.REVISE, ("revise", "revision")),
    (Action.EXTEND, ("extend", "expand", "add more to")),
    (Action.REVIEW, ("review", "critique", "assess", "check over")),
    (Action.MODIFY, ("modify", "change the", "update the", "edit the")),
)

#: (Target, cues) — checked only when no document_type resolves (a
#: resolved document_type always implies target=document; see below).
_TARGET_CUES: tuple[tuple[Target, tuple[str, ...]], ...] = (
    (Target.BRAND, ("brand",)),
    (Target.SECTION, ("section",)),
    (Target.PAGE, ("page ", "pages")),
    (Target.CONTENT, ("content",)),
    (Target.PROJECT, ("project",)),
    (Target.PRESENTATION, ("presentation", "deck", "pitch")),
    (Target.PORTFOLIO, ("portfolio",)),
    (Target.REPORT, ("report",)),
    (Target.TEMPLATE, ("template",)),
)

_REFERENTIAL_PRONOUNS = ("this", "it", "the document")

_AUDIENCE_CUES = ("client", "investor", "public", "authority", "peer", "internal", "board", "team")

_QUALITY_CUES = (
    "premium", "minimal", "minimalist", "bold", "restrained", "professional",
    "playful", "elegant", "polished", "simple", "sophisticated",
)

_STYLE_REFERENCE_PATTERN = re.compile(
    r"(?:feel like|same (?:branding|style|look) as)\s+(?:our\s+|the\s+)?"
    r"(.+?)(?:\s+but\b|\.|,|$)",
    re.IGNORECASE,
)
_SUBJECT_PATTERN = re.compile(
    r"\babout\s+(?:the\s+)?(.+?)(?:\.|,|\s+make\b|\s+with\b|$)",
    re.IGNORECASE,
)
_AUDIENCE_PATTERN = re.compile(
    r"\b(?:send to|for)\s+(?:the\s+)?(client|investor|public|authority|peer|team|board)\b",
    re.IGNORECASE,
)
_DESIGN_DIRECTION_PATTERN = re.compile(r"\bmore\s+(\w+)\b", re.IGNORECASE)


class RuleBasedProvider(LLMProvider):
    """No network call, ever — safe to run in any environment, any test."""

    def extract(
        self, system_prompt: str, context: SemanticContext,
    ) -> tuple[SemanticIntent, ProviderMetadata]:
        start = time.perf_counter()
        text = context.request
        lowered = text.lower()

        explicit: dict[str, object] = {}
        inferred: dict[str, object] = {}
        ambiguous: list[SemanticField] = []
        notes: dict[str, str] = {}

        # -- action ---------------------------------------------------
        action = _match_action(lowered)
        if action is not None:
            explicit["action"] = action.value
        else:
            ambiguous.append(SemanticField.ACTION)
            notes["action"] = "no unambiguous action verb found in the request"

        # -- document_type + target ------------------------------------
        doc_type_id = _match_document_type(lowered, context)
        if doc_type_id is not None:
            explicit["document_type"] = doc_type_id
            explicit["target"] = Target.DOCUMENT.value
        else:
            target = _match_target(lowered)
            if target is not None:
                explicit["target"] = target.value
            elif context.design_state_context is not None and any(
                p in lowered for p in _REFERENTIAL_PRONOUNS
            ):
                inferred["target"] = Target.DOCUMENT.value
            else:
                ambiguous.append(SemanticField.TARGET)
                notes["target"] = "no target named, and no open document in context to infer one from"

        # -- audience ---------------------------------------------------
        audience_match = _AUDIENCE_PATTERN.search(text) or _first_cue(lowered, _AUDIENCE_CUES)
        if audience_match:
            value = audience_match.group(1) if isinstance(audience_match, re.Match) else audience_match
            explicit["audience"] = value.lower()

        # -- subject ------------------------------------------------------
        subject_match = _SUBJECT_PATTERN.search(text)
        if subject_match:
            explicit["subject"] = subject_match.group(1).strip()

        # -- style / brand reference --------------------------------------
        style_match = _STYLE_REFERENCE_PATTERN.search(text)
        if style_match:
            reference = style_match.group(1).strip()
            explicit["style_reference"] = reference
            if "brand" in lowered or "same branding" in lowered:
                explicit["brand_reference"] = reference

        # -- quality direction ---------------------------------------------
        quality = _first_cue(lowered, _QUALITY_CUES)
        if quality:
            explicit["quality_direction"] = quality

        # -- design direction ("more visual", "more concise", ...) --------
        design_match = _DESIGN_DIRECTION_PATTERN.search(lowered)
        if design_match and design_match.group(1) not in _QUALITY_CUES:
            explicit["design_direction"] = design_match.group(0).strip()

        intent = SemanticIntent(
            explicit=SemanticFieldValues(**explicit),
            inferred=SemanticFieldValues(**inferred),
            ambiguous=tuple(ambiguous),
            ambiguity_notes=notes,
            confidence=0.4 if ambiguous else 0.6,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        metadata = ProviderMetadata(
            provider="rule-based", model="keyword-v1", latency_ms=latency_ms,
        )
        return intent, metadata


def _match_action(lowered: str) -> Action | None:
    for action, cues in _ACTION_CUES:
        if any(cue in lowered for cue in cues):
            return action
    return None


def _match_target(lowered: str) -> Target | None:
    for target, cues in _TARGET_CUES:
        if any(cue in lowered for cue in cues):
            return target
    return None


def _match_document_type(lowered: str, context: SemanticContext) -> str | None:
    hits = {
        dt.id for dt in context.available_document_types
        if dt.id.replace("-", " ") in lowered or dt.name.lower() in lowered
    }
    if len(hits) == 1:
        return next(iter(hits))
    return None


def _first_cue(lowered: str, cues: tuple[str, ...]) -> str | None:
    for cue in cues:
        if cue in lowered:
            return cue
    return None
