"""
brand/llm/command/planning.py

The orchestrator: assembles context, runs a generator, and — the one
non-negotiable step regardless of which generator ran —
**re-validates every proposed command through the real, existing**
``brand.creative.intent.validate_intent`` **before it is ever placed on
the returned** ``CommandPlan``. A command that fails that check is
dropped and recorded as a :class:`~brand.llm.command.model.SkippedLever`
with reason ``VALIDATION_FAILED`` — this package never returns a command
its own compiler produced but the existing validator would reject.

A stale ``design_state_version`` (the ``DesignIntent`` was computed
against a ``DesignState`` version the caller's current ``DesignState``
has since moved past) short-circuits generation entirely: every lever
this package could compute from a stale diff is suspect, not just one of
them, so nothing is generated and the plan carries a single
``STALE_DESIGN_STATE`` skip explaining why.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Optional

from brand.creative.intent import validate_intent
from brand.llm.command.context import assemble_command_context
from brand.llm.command.generation import CommandGenerator, RuleBasedCommandGenerator
from brand.llm.command.model import CommandPlan, GeneratedCommand, SkippedLever
from brand.llm.command.observability import record_command_trace
from brand.llm.command.vocabulary import CommandRejectionReason
from brand.llm.provider import ProviderError

if TYPE_CHECKING:
    from brand.content.model import ContentModel
    from brand.design_state.model import DesignState
    from brand.llm.design.model import DesignIntent


def _default_generator() -> CommandGenerator:
    """LLM-backed disambiguation only when explicitly enabled and
    configured — otherwise the deterministic compiler, which is always
    correct and always available (ADOS-M3.5's own "deterministic-first"
    principle, mirroring every prior M3 milestone's ``_default_generator``)."""
    if os.environ.get("COMMAND_GENERATION_LLM_ENABLED", "true").lower() in ("0", "false", "no"):
        return RuleBasedCommandGenerator()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return RuleBasedCommandGenerator()
    from brand.llm.command.generation import LLMCommandGenerator

    return LLMCommandGenerator()


def plan_commands(
    design_intent: "DesignIntent",
    content: "ContentModel",
    *,
    design_state: Optional["DesignState"] = None,
    generator: Optional[CommandGenerator] = None,
    request_id: Optional[str] = None,
) -> CommandPlan:
    start = time.monotonic()
    context = assemble_command_context(design_intent, design_state)

    if (
        design_intent.design_state_version is not None
        and context.current.has_state
        and context.current.version_number != design_intent.design_state_version
    ):
        plan = CommandPlan(
            project_id=design_intent.project_id,
            design_intent_id=design_intent.id,
            narrative_plan_id=design_intent.narrative_plan_id,
            design_state_version=design_intent.design_state_version,
            brand_id=design_intent.brand_id,
            brand_version=design_intent.brand_version,
            commands=(),
            skipped=(SkippedLever(
                source_field="design_state_version",
                reason=CommandRejectionReason.STALE_DESIGN_STATE,
                detail=(
                    f"DesignIntent was computed against DesignState version "
                    f"{design_intent.design_state_version}, but the current DesignState is "
                    f"at version {context.current.version_number} — regenerate the "
                    f"DesignIntent against the current state before compiling commands"
                ),
            ),),
            metadata={"generator": "none", "reason": "stale_design_state_version"},
        )
        record_command_trace(plan, request_id=request_id, latency_ms=(time.monotonic() - start) * 1000, error=None)
        return plan

    active_generator = generator or _default_generator()
    generator_name = type(active_generator).__name__
    error: Optional[str] = None

    try:
        raw_commands, skipped, _metadata = active_generator.generate(context)
    except ProviderError as exc:
        raw_commands, skipped, _metadata = RuleBasedCommandGenerator().generate(context)
        generator_name = f"{generator_name}->RuleBasedCommandGenerator (fallback)"
        error = str(exc)

    page_count = context.current.page_count
    accepted: list[GeneratedCommand] = []
    extra_skips: list[SkippedLever] = []
    for command in raw_commands:
        errors = validate_intent(content, command.intent, page_count=page_count or None)
        if errors:
            extra_skips.append(SkippedLever(
                source_field=command.source_field,
                reason=CommandRejectionReason.VALIDATION_FAILED,
                detail=f"{command.intent.type.value} failed validate_intent(): {'; '.join(errors)}",
            ))
            continue
        accepted.append(command)

    plan = CommandPlan(
        project_id=design_intent.project_id,
        design_intent_id=design_intent.id,
        narrative_plan_id=design_intent.narrative_plan_id,
        design_state_version=design_intent.design_state_version,
        brand_id=design_intent.brand_id,
        brand_version=design_intent.brand_version,
        commands=tuple(accepted),
        skipped=tuple(skipped) + tuple(extra_skips),
        metadata={"generator": generator_name},
    )
    record_command_trace(plan, request_id=request_id, latency_ms=(time.monotonic() - start) * 1000, error=error)
    return plan
