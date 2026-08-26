"""ADOS-M3.5 — brand/llm/command/planning.py."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from brand.content.model import BlockRole, BlockType, ContentBlock, ContentModel
from brand.creative.intent import CommandIntent, IntentTarget, IntentType, TargetType
from brand.llm.command.generation import CommandGenerator
from brand.llm.command.model import GeneratedCommand, SkippedLever
from brand.llm.command.planning import _default_generator, plan_commands
from brand.llm.command.vocabulary import CommandProvenance, CommandRejectionReason, CommandSafetyLevel
from brand.llm.design.model import DesignIntent
from brand.llm.design.vocabulary import CompositionStrategy, TextDensity


def _content() -> ContentModel:
    return ContentModel(project_id=uuid.uuid4(), project_name="Test", blocks=(
        ContentBlock(id="txt-01", type=BlockType.NARRATIVE, role=BlockRole.CONTEXT, priority=1, text="hello " * 20),
    ))


def _fake_state(*, version=3, direction_id="editorial-quiet", text_density=0.45, image_ratio=0.5, pages=2):
    return SimpleNamespace(
        version=SimpleNamespace(number=version),
        document=SimpleNamespace(direction_id=direction_id),
        visual_language=SimpleNamespace(text_density=text_density, image_ratio=image_ratio),
        pages=tuple(SimpleNamespace() for _ in range(pages)),
    )


def test_stale_design_state_version_blocks_generation_entirely():
    di = DesignIntent(
        project_id="p1", composition_strategy=CompositionStrategy.IMAGE_LED, density=TextDensity.MEDIUM,
        design_state_version=1,
    )
    plan = plan_commands(di, _content(), design_state=_fake_state(version=5))
    assert plan.commands == ()
    assert len(plan.skipped) == 1
    assert plan.skipped[0].reason is CommandRejectionReason.STALE_DESIGN_STATE


def test_matching_design_state_version_generates_normally():
    di = DesignIntent(
        project_id="p1", composition_strategy=CompositionStrategy.IMAGE_LED, density=TextDensity.MEDIUM,
        design_state_version=3,
    )
    plan = plan_commands(di, _content(), design_state=_fake_state(version=3, direction_id="editorial-quiet"))
    assert any(c.intent.type is IntentType.CHANGE_PAGE_DIRECTION for c in plan.commands)


def test_regeneration_is_idempotent_for_the_same_inputs():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.IMAGE_LED, density=TextDensity.HIGH)
    state = _fake_state(version=1, direction_id="editorial-quiet", text_density=0.4, image_ratio=0.3)
    plan_a = plan_commands(di, _content(), design_state=state)
    plan_b = plan_commands(di, _content(), design_state=state)
    types_a = sorted(c.intent.type.value for c in plan_a.commands)
    types_b = sorted(c.intent.type.value for c in plan_b.commands)
    assert types_a == types_b


class _InvalidGenerator(CommandGenerator):
    """Proposes a command validate_intent() itself rejects (a page
    target index with no base_plan/page_count context to justify it) —
    proves plan_commands() drops it rather than trusting its own
    generator blindly."""

    def generate(self, context):
        bad = GeneratedCommand(
            intent=CommandIntent(
                type=IntentType.PRESERVE_CONTENT,
                target=IntentTarget(type=TargetType.DOCUMENT),
                parameters={"content_ids": ["does-not-exist"]},
                source="future_llm",
            ),
            safety_level=CommandSafetyLevel.SAFE,
            provenance=CommandProvenance.STRUCTURAL_DIFF,
            source_field="test",
        )
        return (bad,), (), None


def test_a_command_that_fails_validate_intent_is_dropped_not_returned():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM)
    plan = plan_commands(di, _content(), generator=_InvalidGenerator())
    assert plan.commands == ()
    assert any(s.reason is CommandRejectionReason.VALIDATION_FAILED for s in plan.skipped)


def test_default_generator_is_rule_based_without_an_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from brand.llm.command.generation import RuleBasedCommandGenerator

    assert isinstance(_default_generator(), RuleBasedCommandGenerator)


def test_default_generator_is_rule_based_when_llm_disabled(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    monkeypatch.setenv("COMMAND_GENERATION_LLM_ENABLED", "false")
    from brand.llm.command.generation import RuleBasedCommandGenerator

    assert isinstance(_default_generator(), RuleBasedCommandGenerator)
