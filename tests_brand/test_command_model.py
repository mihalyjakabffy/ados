"""ADOS-M3.5 — brand/llm/command/model.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brand.creative.intent import CommandIntent, IntentTarget, IntentType, TargetType
from brand.llm.command.model import CommandPlan, GeneratedCommand, SkippedLever
from brand.llm.command.vocabulary import CommandProvenance, CommandRejectionReason, CommandSafetyLevel


def _intent() -> CommandIntent:
    return CommandIntent(
        type=IntentType.CHANGE_PAGE_DIRECTION,
        target=IntentTarget(type=TargetType.DOCUMENT),
        parameters={"direction_id": "image-led"},
        source="future_llm",
    )


def test_generated_command_wraps_a_real_command_intent():
    command = GeneratedCommand(
        intent=_intent(), safety_level=CommandSafetyLevel.REVIEW_RECOMMENDED,
        provenance=CommandProvenance.STRUCTURAL_DIFF, source_field="composition_strategy",
    )
    assert command.intent.type is IntentType.CHANGE_PAGE_DIRECTION
    assert command.idempotent is True


def test_generated_command_is_frozen():
    command = GeneratedCommand(
        intent=_intent(), safety_level=CommandSafetyLevel.SAFE,
        provenance=CommandProvenance.STRUCTURAL_DIFF, source_field="density",
    )
    with pytest.raises(ValidationError):
        command.rationale = "changed"


def test_command_plan_command_lookup_by_id():
    command = GeneratedCommand(
        intent=_intent(), safety_level=CommandSafetyLevel.SAFE,
        provenance=CommandProvenance.STRUCTURAL_DIFF, source_field="density",
    )
    plan = CommandPlan(project_id="p1", commands=(command,))
    assert plan.command(command.id) is command
    assert plan.command("does-not-exist") is None


def test_command_plan_to_dict_round_trips():
    plan = CommandPlan(
        project_id="p1", design_intent_id="d1", design_state_version=2,
        skipped=(SkippedLever(source_field="x", reason=CommandRejectionReason.NO_CHANGE_NEEDED),),
    )
    payload = plan.to_dict()
    assert payload["project_id"] == "p1"
    assert payload["skipped"][0]["reason"] == "no_change_needed"
    restored = CommandPlan.model_validate({k: v for k, v in payload.items() if k != "id"} | {"id": plan.id})
    assert restored.design_intent_id == "d1"


def test_skipped_lever_requires_a_source_field():
    with pytest.raises(ValidationError):
        SkippedLever(source_field="", reason=CommandRejectionReason.NO_CHANGE_NEEDED)
