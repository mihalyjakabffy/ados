"""
brand/llm/command/prompt.py

The versioned system/user prompt pair for
:class:`~brand.llm.command.generation.LLMCommandGenerator`'s one bounded
call. Deliberately narrow: the model is asked to resolve exactly one
ambiguity (which, if any, of three named ``CreativeDirection`` ids best
fits an already-computed, already-summarized composition strategy) —
never to propose a command, a parameter, or a target itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brand.llm.command.context import CommandGenerationContext

#: Bumped whenever the wording changes in a way that could change model
#: behaviour — brand/llm/design/prompt.py's own convention.
PROMPT_VERSION = "3.5.0"

_SYSTEM_PROMPT = f"""You are ADOS's command-generation disambiguator (prompt v{PROMPT_VERSION}).

A deterministic compiler has already compared a DesignIntent's
composition_strategy against the three CreativeDirections ADOS ships
(editorial-quiet, technical-dense, image-led) and found no single,
confident match. Your only job is to say which of those three ids — if
any — best fits the composition strategy and section-level signals you
are given, or to decline.

Rules:
- You may only name one of the three ids already listed above, or leave
  your answer empty. Naming any other id, inventing a new direction, or
  proposing a command, parameter, or target is not part of this task and
  will be discarded.
- Decline (leave chosen_direction_id empty) if the signals genuinely
  point in different directions rather than guessing.
- Give one short, concrete reason for your choice, referencing the
  actual signals you were given — never invented content."""


def build_command_system_prompt() -> str:
    return _SYSTEM_PROMPT


def build_command_user_message(context: "CommandGenerationContext") -> str:
    intent = context.design_intent
    section_modes = [sd.composition_mode.value for sd in intent.section_designs]
    lines = [
        f"composition_strategy: {intent.composition_strategy.value}",
        f"visual_language (brand personality subset): {[p.value for p in intent.visual_language]}",
        f"section composition_mode values: {section_modes}",
        f"current DesignState direction_id: {context.current.direction_id or '(none yet)'}",
        "known direction ids: editorial-quiet, technical-dense, image-led",
    ]
    return "\n".join(lines)
