"""
brand/llm/loop/prompt.py

The versioned prompt for the loop's one bounded LLM call: proposing a
single :class:`~brand.llm.loop.model.DesignIntentPatch` for a finding
that has no deterministic capability (``recommend.py``). Mirrors
``brand.llm.command.prompt``'s exact narrowness — the model may only
name one of the seven real, patchable ``DesignIntent`` fields and one
real value for it, nothing else.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from brand.llm.loop.model import PATCHABLE_FIELDS

if TYPE_CHECKING:
    from brand.validation.brand_validator import Finding

PROMPT_VERSION = "3.6.0"

_FIELD_VALUES = {
    "composition_strategy": "image_led, text_led, diagram_led, data_led, balanced, asymmetric, modular, sequential, immersive, dense, sparse",
    "density": "minimal, low, medium, high, very_high",
    "typography_hierarchy": "strong, restrained, editorial, technical, expressive",
    "color_strategy": "monochrome, restrained, accent_driven, bold, brand_saturated, muted",
    "grid_strategy": "editorial, modular, asymmetric, symmetric, column_heavy, full_bleed, technical",
    "whitespace_strategy": "generous, moderate, compact, dense, breathing_room, tight",
    "rhythm": "steady, accelerating, decelerating, syncopated, uniform, alternating, climactic",
}

_SYSTEM_PROMPT = f"""You are ADOS's closed-loop recommendation assistant (prompt v{PROMPT_VERSION}).

A finding has been raised about a composed document, and a deterministic
capability registry has no automatic fix for it. Your only job is to propose
ONE small, targeted revision to the document's DesignIntent that would
plausibly address it.

Rules:
- You may only name one of these seven fields as your target:
  {', '.join(PATCHABLE_FIELDS)}
- The value you propose must be a real member of that field's own vocabulary
  (given to you below for each field) — never invent a value.
- Propose exactly one field/value pair, or decline if no real field would
  plausibly help.
- Give one short, concrete reason tied to the actual finding you were given.
- You are not proposing a command, a coordinate, a colour, or a font — only
  a semantic design-intent field and value."""


def build_loop_system_prompt() -> str:
    return _SYSTEM_PROMPT


def build_loop_user_message(finding: "Finding") -> str:
    lines = [
        f"finding code: {finding.code or '(uncoded)'}",
        f"finding message: {finding.message}",
        f"finding field: {finding.field}",
        "",
        "patchable fields and their real values:",
    ]
    for field_name, values in _FIELD_VALUES.items():
        lines.append(f"  {field_name}: {values}")
    return "\n".join(lines)
