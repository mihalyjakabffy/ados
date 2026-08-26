"""ADOS-M3.6 — brand/llm/loop/execution.py."""

from __future__ import annotations

import uuid

import pytest

from brand.content.model import BlockRole, BlockType, ContentBlock, ContentModel
from brand.creative.directions import EDITORIAL_QUIET, IMAGE_LED
from brand.creative.intent import CommandIntent, IntentTarget, IntentType, TargetType
from brand.examples.studio_nord import studio_nord
from brand.llm.command.model import GeneratedCommand
from brand.llm.command.vocabulary import CommandProvenance, CommandSafetyLevel
from brand.llm.loop.execution import gate_commands
from brand.llm.loop.vocabulary import AutonomyLevel


def _command(intent_type=IntentType.CHANGE_PAGE_DIRECTION, safety=CommandSafetyLevel.REVIEW_RECOMMENDED, cid="c1") -> GeneratedCommand:
    return GeneratedCommand(
        id=cid,
        intent=CommandIntent(type=intent_type, target=IntentTarget(type=TargetType.DOCUMENT),
                              parameters={"direction_id": "image-led"} if intent_type is IntentType.CHANGE_PAGE_DIRECTION else {"strength": 0.5},
                              source="future_llm"),
        safety_level=safety, provenance=CommandProvenance.STRUCTURAL_DIFF, source_field="test",
    )


def test_gate_commands_none_autonomy_gates_everything():
    safe_cmd = _command(IntentType.INCREASE_TEXT_DENSITY, CommandSafetyLevel.SAFE, "c1")
    to_execute, pending = gate_commands((safe_cmd,), AutonomyLevel.NONE)
    assert to_execute == ()
    assert pending == (safe_cmd,)


def test_gate_commands_safe_autonomy_executes_only_safe():
    safe_cmd = _command(IntentType.INCREASE_TEXT_DENSITY, CommandSafetyLevel.SAFE, "c1")
    review_cmd = _command(IntentType.CHANGE_PAGE_DIRECTION, CommandSafetyLevel.REVIEW_RECOMMENDED, "c2")
    to_execute, pending = gate_commands((safe_cmd, review_cmd), AutonomyLevel.SAFE)
    assert to_execute == (safe_cmd,)
    assert pending == (review_cmd,)


def test_gate_commands_full_autonomy_executes_everything():
    review_cmd = _command(IntentType.CHANGE_PAGE_DIRECTION, CommandSafetyLevel.REVIEW_RECOMMENDED, "c2")
    to_execute, pending = gate_commands((review_cmd,), AutonomyLevel.FULL)
    assert to_execute == (review_cmd,)
    assert pending == ()


def test_gate_commands_explicit_approval_overrides_autonomy():
    review_cmd = _command(IntentType.CHANGE_PAGE_DIRECTION, CommandSafetyLevel.REVIEW_RECOMMENDED, "c2")
    to_execute, pending = gate_commands((review_cmd,), AutonomyLevel.NONE, approved_command_ids=frozenset({"c2"}))
    assert to_execute == (review_cmd,)
    assert pending == ()


def _content() -> ContentModel:
    return ContentModel(project_id=uuid.uuid4(), project_name="Test", blocks=(
        ContentBlock(id="txt-01", type=BlockType.NARRATIVE, role=BlockRole.CONTEXT, priority=1, text="hello " * 30),
    ))


def test_execute_commands_runs_validate_apply_compose_in_order():
    from brand.llm.loop.execution import execute_commands

    brand = studio_nord()
    content = _content()
    command = _command(IntentType.CHANGE_PAGE_DIRECTION, CommandSafetyLevel.REVIEW_RECOMMENDED, "c1")
    new_content, new_direction, plan, steps = execute_commands((command,), content, EDITORIAL_QUIET, brand)
    assert plan is not None
    assert new_direction.id.startswith("image-led")
    assert len(steps) == 1
    assert steps[0]["command_id"] == "c1"
    assert steps[0]["plan_hash_after"] == plan.plan_hash


def test_execute_commands_raises_on_invalid_intent():
    from brand.llm.loop.execution import ExecutionFailedError, execute_commands

    brand = studio_nord()
    content = _content()
    bad = GeneratedCommand(
        id="bad", intent=CommandIntent(
            type=IntentType.PRESERVE_CONTENT, target=IntentTarget(type=TargetType.DOCUMENT),
            parameters={"content_ids": ["does-not-exist"]}, source="future_llm",
        ),
        safety_level=CommandSafetyLevel.SAFE, provenance=CommandProvenance.STRUCTURAL_DIFF, source_field="test",
    )
    with pytest.raises(ExecutionFailedError):
        execute_commands((bad,), content, EDITORIAL_QUIET, brand)


def test_save_new_version_updates_document_and_appends_version():
    from brand.llm.loop.execution import save_new_version
    from brand.project.model import Document, Project

    brand = studio_nord()
    content = _content()
    plan = None
    from brand.creative.composer import compose

    plan = compose(content, IMAGE_LED, brand)

    project_id = str(uuid.uuid4())
    doc = Document(project_id=project_id, name="X")
    project = Project(id=project_id, name="P", documents=(doc,))

    new_project, new_document, version = save_new_version(project, doc, plan)
    assert len(new_project.versions) == 1
    assert new_document.latest_plan is not None
    assert version.number == 1
