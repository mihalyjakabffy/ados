"""
brand/llm/command/generation.py

The generator abstraction ADOS-M3.5 asks for, mirroring
``brand.llm.design.generation``'s own shape. Two implementations:

* :class:`RuleBasedCommandGenerator` — deterministic, no network call,
  and the *only* generator this package needs for its actual job:
  comparing three real, closed-form ``DesignIntent`` signals
  (``composition_strategy``, ``density``, and the mode of every
  ``SectionDesign.image_density``) against the real, already-composed
  ``DesignState`` those signals are meant to move, and emitting the one
  existing ``CommandIntent`` each real gap calls for. Every candidate
  this compares is either turned into a :class:`GeneratedCommand` or
  recorded as a :class:`SkippedLever` with a reason — never silently
  dropped.
* :class:`LLMCommandGenerator` — reuses the shared Claude client
  (``brand.llm.providers.claude_provider``) for exactly one bounded,
  genuinely ambiguous decision the deterministic pass cannot make on its
  own: when ``composition_strategy`` has no single confident
  ``CreativeDirection`` mapping (``BALANCED``/``ASYMMETRIC``/``MODULAR``/
  ``SEQUENTIAL``/``IMMERSIVE``), the LLM may choose one of the three
  already-registered direction ids, or explicitly decline. Its
  structured-output schema (:class:`RawDirectionChoice`) can name
  nothing else — not a new ``IntentType``, not a parameter, not a
  target — so a hallucinated answer has nowhere to go: any id outside
  the closed, already-known set is dropped by :func:`_materialize_choice`
  exactly as the deterministic pass would have, and generation falls
  back to leaving the lever skipped.

**Every command either generator proposes is re-validated, unconditionally,
by the real ``brand.creative.intent.validate_intent`` before it is ever
returned** — see ``planning.py``. Nothing in this module calls
``apply_intent`` or ``compose`` itself.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from brand import ados
from brand.creative.direction import DirectionError
from brand.creative.directions import DIRECTIONS, get_direction
from brand.creative.intent import CommandIntent, IntentTarget, IntentType, TargetType
from brand.llm.command.context import CommandGenerationContext
from brand.llm.command.model import CommandPlan, GeneratedCommand, SkippedLever
from brand.llm.command.vocabulary import (
    DIRECTION_BY_COMPOSITION_STRATEGY,
    NEGLIGIBLE_GAP,
    TARGET_IMAGE_RATIO_BY_LEVEL,
    TARGET_TEXT_DENSITY_BY_LEVEL,
    CommandProvenance,
    CommandRejectionReason,
    CommandSafetyLevel,
)
from brand.llm.design.vocabulary import CompositionStrategy, TextDensity
from brand.llm.provider import ProviderMetadata

logger = logging.getLogger(__name__)


class CommandGenerator(ABC):
    """One call: a scoped context in, an ordered ``(commands, skipped)``
    pair and provider metadata out. Mirrors
    ``brand.llm.design.generation.DesignIntentGenerator``'s own shape."""

    @abstractmethod
    def generate(
        self, context: CommandGenerationContext,
    ) -> tuple[tuple[GeneratedCommand, ...], tuple[SkippedLever, ...], Optional[ProviderMetadata]]:
        """Raise :class:`~brand.llm.provider.ProviderError` on any
        failure — never a vendor-specific exception."""


# ---------------------------------------------------------------------------
# Deterministic rule-based generator — the primary, always-available path
# ---------------------------------------------------------------------------


def _direction_candidate(
    context: CommandGenerationContext,
) -> tuple[Optional[GeneratedCommand], Optional[SkippedLever]]:
    """The one lever a whole-document strategy swap actually is:
    ``CreativeDirection`` bundles narrative order, lead-with, density and
    image ratio together, so a confident ``composition_strategy`` match
    is compiled to a single ``change_page_direction`` rather than to a
    handful of separate nudges that would only approximate it."""
    intent = context.design_intent
    target_id = DIRECTION_BY_COMPOSITION_STRATEGY.get(intent.composition_strategy)

    if target_id is None:
        return None, SkippedLever(
            source_field="composition_strategy",
            reason=CommandRejectionReason.AMBIGUOUS_MAPPING,
            detail=(
                f"composition_strategy={intent.composition_strategy.value!r} has no single, "
                f"confident CreativeDirection mapping among the shipped set "
                f"({', '.join(sorted(DIRECTIONS))})"
            ),
        )

    if context.current.has_state and context.current.direction_id == target_id:
        return None, SkippedLever(
            source_field="composition_strategy",
            reason=CommandRejectionReason.NO_CHANGE_NEEDED,
            detail=f"the current DesignState is already composed under {target_id!r}",
        )

    current_label = repr(context.current.direction_id) if context.current.direction_id else "(none yet)"
    command = GeneratedCommand(
        intent=CommandIntent(
            type=IntentType.CHANGE_PAGE_DIRECTION,
            target=IntentTarget(type=TargetType.DOCUMENT),
            parameters={"direction_id": target_id},
            source="future_llm",
        ),
        safety_level=CommandSafetyLevel.REVIEW_RECOMMENDED,
        provenance=CommandProvenance.STRUCTURAL_DIFF,
        source_field="composition_strategy",
        rationale=(
            f"composition_strategy={intent.composition_strategy.value!r} maps to the "
            f"{target_id!r} direction; the current DesignState is composed under "
            f"{current_label}"
        ),
        idempotent=True,
    )
    return command, None


def _density_candidate(
    context: CommandGenerationContext,
) -> tuple[Optional[GeneratedCommand], Optional[SkippedLever]]:
    intent = context.design_intent
    if context.current.text_density is None:
        return None, SkippedLever(
            source_field="density",
            reason=CommandRejectionReason.NO_CHANGE_NEEDED,
            detail="no current DesignState text_density to compare against — nothing composed yet",
        )

    target = TARGET_TEXT_DENSITY_BY_LEVEL[intent.density]
    current = context.current.text_density
    gap = target - current
    if abs(gap) <= NEGLIGIBLE_GAP:
        return None, SkippedLever(
            source_field="density",
            reason=CommandRejectionReason.NO_CHANGE_NEEDED,
            detail=f"current text_density {current:.3f} already within {NEGLIGIBLE_GAP} of target {target:.3f}",
        )

    low, high = ados.fill_ratio_bounds()
    if gap > 0:
        span = max(high - current, 1e-6)
        strength = max(0.0, min(1.0, gap / span))
        intent_type = IntentType.INCREASE_TEXT_DENSITY
    else:
        span = max(current - low, 1e-6)
        strength = max(0.0, min(1.0, -gap / span))
        intent_type = IntentType.REDUCE_TEXT_DENSITY

    command = GeneratedCommand(
        intent=CommandIntent(
            type=intent_type,
            target=IntentTarget(type=TargetType.DOCUMENT),
            parameters={"strength": round(strength, 3)},
            source="future_llm",
        ),
        safety_level=CommandSafetyLevel.SAFE,
        provenance=CommandProvenance.STRUCTURAL_DIFF,
        source_field="density",
        rationale=(
            f"density={intent.density.value!r} targets text_density {target:.3f}; "
            f"current DesignState is at {current:.3f}"
        ),
        idempotent=False,
    )
    return command, None


def _image_emphasis_candidate(
    context: CommandGenerationContext,
) -> tuple[Optional[GeneratedCommand], Optional[SkippedLever]]:
    intent = context.design_intent
    if context.current.image_ratio is None:
        return None, SkippedLever(
            source_field="section_designs[].image_density",
            reason=CommandRejectionReason.NO_CHANGE_NEEDED,
            detail="no current DesignState image_ratio to compare against — nothing composed yet",
        )
    if not intent.section_designs:
        return None, SkippedLever(
            source_field="section_designs[].image_density",
            reason=CommandRejectionReason.AMBIGUOUS_MAPPING,
            detail="no section designs to aggregate an image-density signal from",
        )

    levels = [sd.image_density for sd in intent.section_designs]
    mode_level, _count = Counter(levels).most_common(1)[0]
    target = TARGET_IMAGE_RATIO_BY_LEVEL[mode_level]
    current = context.current.image_ratio
    gap = target - current
    if abs(gap) <= NEGLIGIBLE_GAP:
        return None, SkippedLever(
            source_field="section_designs[].image_density",
            reason=CommandRejectionReason.NO_CHANGE_NEEDED,
            detail=f"current image_ratio {current:.3f} already within {NEGLIGIBLE_GAP} of target {target:.3f}",
        )

    low, high = ados.fill_ratio_bounds()
    if gap > 0:
        span = max(high - current, 1e-6)
        strength = max(0.0, min(1.0, gap / span))
        intent_type = IntentType.INCREASE_IMAGE_EMPHASIS
    else:
        span = max(current - low, 1e-6)
        strength = max(0.0, min(1.0, -gap / span))
        intent_type = IntentType.DECREASE_IMAGE_EMPHASIS

    command = GeneratedCommand(
        intent=CommandIntent(
            type=intent_type,
            target=IntentTarget(type=TargetType.DOCUMENT),
            parameters={"strength": round(strength, 3)},
            source="future_llm",
        ),
        safety_level=CommandSafetyLevel.SAFE,
        provenance=CommandProvenance.STRUCTURAL_DIFF,
        source_field="section_designs[].image_density",
        rationale=(
            f"the modal section image_density is {mode_level.value!r} (target image_ratio "
            f"{target:.3f}); current DesignState is at {current:.3f}"
        ),
        idempotent=False,
    )
    return command, None


def _design_issue_skips(context: CommandGenerationContext) -> tuple[SkippedLever, ...]:
    """Every real ``DesignIssue`` is real information a reviewer should
    see, even where — especially where — this compiler has no safe,
    automatic command for it. Recorded, never silently ignored."""
    skips = []
    for i, issue in enumerate(context.design_intent.design_issues):
        skips.append(SkippedLever(
            source_field=f"design_issues[{i}]",
            reason=CommandRejectionReason.NO_SAFE_COMMAND_EXISTS,
            detail=f"{issue.type.value}: {issue.description}",
        ))
    return tuple(skips)


class RuleBasedCommandGenerator(CommandGenerator):
    """Deterministic, no network call. The primary and normally
    sufficient generator: every command it can ever propose is a direct
    read of a real gap between a ``DesignIntent`` field and the current
    ``DesignState``, via the fixed lookup tables in
    ``brand.llm.command.vocabulary``."""

    def generate(
        self, context: CommandGenerationContext,
    ) -> tuple[tuple[GeneratedCommand, ...], tuple[SkippedLever, ...], Optional[ProviderMetadata]]:
        commands: list[GeneratedCommand] = []
        skipped: list[SkippedLever] = []

        for candidate_fn in (_direction_candidate, _density_candidate, _image_emphasis_candidate):
            command, skip = candidate_fn(context)
            if command is not None:
                commands.append(command)
            if skip is not None:
                skipped.append(skip)

        skipped.extend(_design_issue_skips(context))
        return tuple(commands), tuple(skipped), None


# ---------------------------------------------------------------------------
# LLM tie-breaker (ADOS-M3.5 — bounded, closed-set disambiguation only)
# ---------------------------------------------------------------------------


class RawDirectionChoice(BaseModel):
    """The *only* thing the LLM tie-breaker may say: one of the three
    already-registered direction ids, or nothing. It cannot name a
    parameter, a target, or a new IntentType — there is no field for
    any of those here."""

    model_config = ConfigDict(extra="forbid")

    chosen_direction_id: Optional[str] = None
    reason: str = ""


def _materialize_choice(
    raw: RawDirectionChoice, context: CommandGenerationContext,
) -> tuple[Optional[GeneratedCommand], Optional[SkippedLever]]:
    if not raw.chosen_direction_id:
        return None, SkippedLever(
            source_field="composition_strategy",
            reason=CommandRejectionReason.AMBIGUOUS_MAPPING,
            detail="the LLM tie-breaker also declined to choose a direction",
        )
    try:
        chosen = get_direction(raw.chosen_direction_id)
    except KeyError:
        logger.warning("command generation: LLM chose unknown direction id %r, dropping", raw.chosen_direction_id)
        return None, SkippedLever(
            source_field="composition_strategy",
            reason=CommandRejectionReason.UNKNOWN_DIRECTION,
            detail=f"LLM proposed {raw.chosen_direction_id!r}, which is not a registered CreativeDirection",
        )

    if context.current.has_state and context.current.direction_id == chosen.id:
        return None, SkippedLever(
            source_field="composition_strategy",
            reason=CommandRejectionReason.NO_CHANGE_NEEDED,
            detail=f"the current DesignState is already composed under {chosen.id!r}",
        )

    command = GeneratedCommand(
        intent=CommandIntent(
            type=IntentType.CHANGE_PAGE_DIRECTION,
            target=IntentTarget(type=TargetType.DOCUMENT),
            parameters={"direction_id": chosen.id},
            source="future_llm",
        ),
        safety_level=CommandSafetyLevel.REVIEW_RECOMMENDED,
        provenance=CommandProvenance.LLM_DISAMBIGUATION,
        source_field="composition_strategy",
        rationale=raw.reason or (
            f"composition_strategy={context.design_intent.composition_strategy.value!r} had no "
            f"single confident mapping; the LLM tie-breaker chose {chosen.id!r}"
        ),
        idempotent=True,
    )
    return command, None


class LLMCommandGenerator(CommandGenerator):
    """Runs the deterministic :class:`RuleBasedCommandGenerator` first,
    then — only when it left the direction lever ambiguous — makes one
    bounded, structured-output call to disambiguate among the three
    already-registered direction ids. Reuses
    ``brand.llm.providers.claude_provider``'s shared client; no second
    Claude client, and every other lever (density, image emphasis,
    design-issue skips) is left exactly as the deterministic pass
    computed it — this generator never touches them."""

    _DEFAULT_MODEL = "claude-opus-5"
    _DEFAULT_MAX_TOKENS = 2048

    def __init__(self, model: Optional[str] = None, max_tokens: Optional[int] = None) -> None:
        self._model = model or os.environ.get("COMMAND_GENERATION_MODEL", self._DEFAULT_MODEL)
        self._max_tokens = max_tokens or int(os.environ.get("COMMAND_GENERATION_MAX_TOKENS", self._DEFAULT_MAX_TOKENS))
        self._client: Any = None
        self._deterministic = RuleBasedCommandGenerator()

    def generate(
        self, context: CommandGenerationContext,
    ) -> tuple[tuple[GeneratedCommand, ...], tuple[SkippedLever, ...], Optional[ProviderMetadata]]:
        commands, skipped, _ = self._deterministic.generate(context)

        ambiguous = [
            s for s in skipped
            if s.source_field == "composition_strategy"
            and s.reason is CommandRejectionReason.AMBIGUOUS_MAPPING
        ]
        if not ambiguous:
            return commands, skipped, None

        from brand.llm.command.prompt import build_command_system_prompt, build_command_user_message
        from brand.llm.providers.claude_provider import call_structured, get_client

        if self._client is None:
            self._client = get_client()

        raw, metadata = call_structured(
            self._client, model=self._model, max_tokens=self._max_tokens,
            system_prompt=build_command_system_prompt(),
            user_message=build_command_user_message(context),
            output_format=RawDirectionChoice, provider_name="claude",
        )
        extra_command, replacement_skip = _materialize_choice(raw, context)

        remaining_skipped = tuple(s for s in skipped if s not in ambiguous)
        if replacement_skip is not None:
            remaining_skipped = remaining_skipped + (replacement_skip,)
        new_commands = commands + ((extra_command,) if extra_command is not None else ())
        return new_commands, remaining_skipped, metadata
