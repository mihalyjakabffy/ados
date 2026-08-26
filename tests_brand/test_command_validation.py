"""ADOS-M3.5 — brand/llm/command/validation.py (CMD-001..010)."""

from __future__ import annotations

import uuid

from brand.content.model import BlockRole, BlockType, ContentBlock, ContentModel
from brand.creative.intent import CommandIntent, IntentTarget, IntentType, TargetType
from brand.llm.command.model import CommandPlan, GeneratedCommand
from brand.llm.command.validation import validate_command_plan
from brand.llm.command.vocabulary import CommandProvenance, CommandSafetyLevel


def _content() -> ContentModel:
    return ContentModel(project_id=uuid.uuid4(), project_name="Test", blocks=(
        ContentBlock(id="txt-01", type=BlockType.NARRATIVE, role=BlockRole.CONTEXT, priority=1, text="hello " * 20),
    ))


def _command(intent_type, parameters=None, safety=CommandSafetyLevel.SAFE, rationale="a real reason", target_type=TargetType.DOCUMENT, target_id="") -> GeneratedCommand:
    return GeneratedCommand(
        intent=CommandIntent(
            type=intent_type, target=IntentTarget(type=target_type, id=target_id),
            parameters=parameters or {}, source="future_llm",
        ),
        safety_level=safety, provenance=CommandProvenance.STRUCTURAL_DIFF,
        source_field="test", rationale=rationale,
    )


def test_valid_plan_has_no_findings():
    plan = CommandPlan(project_id="p1", commands=(
        _command(IntentType.CHANGE_PAGE_DIRECTION, {"direction_id": "image-led"}, safety=CommandSafetyLevel.REVIEW_RECOMMENDED),
    ))
    report = validate_command_plan(plan, _content())
    assert report.ok
    assert report.findings == []


def test_cmd001_flags_a_command_that_fails_validate_intent():
    plan = CommandPlan(project_id="p1", commands=(
        _command(IntentType.PRESERVE_CONTENT, {"content_ids": ["not-a-real-block"]}),
    ))
    report = validate_command_plan(plan, _content())
    assert not report.ok
    assert any(f.code == "CMD-001" for f in report.findings)


def test_cmd002_flags_contradictory_increase_and_reduce_density():
    plan = CommandPlan(project_id="p1", commands=(
        _command(IntentType.INCREASE_TEXT_DENSITY, {"strength": 0.5}),
        _command(IntentType.REDUCE_TEXT_DENSITY, {"strength": 0.5}),
    ))
    report = validate_command_plan(plan, _content())
    assert any(f.code == "CMD-002" for f in report.findings)


def test_cmd003_blocks_remove_content_with_no_rationale():
    plan = CommandPlan(project_id="p1", commands=(
        _command(IntentType.REMOVE_CONTENT, {"content_ids": ["txt-01"]}, safety=CommandSafetyLevel.DESTRUCTIVE, rationale=""),
    ))
    report = validate_command_plan(plan, _content())
    findings = [f for f in report.findings if f.code == "CMD-003"]
    assert findings and findings[0].severity.value == "BLOCK"


def test_cmd004_flags_out_of_range_page_target():
    plan = CommandPlan(project_id="p1", commands=(
        _command(IntentType.RECOMPOSE_PAGE, target_type=TargetType.PAGE, target_id="5"),
    ))
    report = validate_command_plan(plan, _content(), page_count=2)
    assert any(f.code == "CMD-004" for f in report.findings)


def test_cmd005_flags_stale_design_state_version():
    plan = CommandPlan(project_id="p1", design_state_version=1, commands=(
        _command(IntentType.CHANGE_PAGE_DIRECTION, {"direction_id": "image-led"}, safety=CommandSafetyLevel.REVIEW_RECOMMENDED),
    ))
    report = validate_command_plan(plan, _content(), current_design_state_version=4)
    assert any(f.code == "CMD-005" for f in report.findings)


def test_cmd006_flags_a_colour_or_dimension_hidden_in_a_parameter():
    plan = CommandPlan(project_id="p1", commands=(
        _command(IntentType.CHANGE_PAGE_DIRECTION, {"direction_id": "editorial-quiet", "note": "#ff00ff"}, safety=CommandSafetyLevel.REVIEW_RECOMMENDED),
    ))
    report = validate_command_plan(plan, _content())
    assert any(f.code == "CMD-006" for f in report.findings)


def test_cmd007_warns_on_missing_rationale():
    plan = CommandPlan(project_id="p1", commands=(
        _command(IntentType.CHANGE_PAGE_DIRECTION, {"direction_id": "image-led"}, safety=CommandSafetyLevel.REVIEW_RECOMMENDED, rationale=""),
    ))
    report = validate_command_plan(plan, _content())
    findings = [f for f in report.findings if f.code == "CMD-007"]
    assert findings and findings[0].severity.value == "WARN"


def test_cmd008_flags_layout_leakage_in_rationale():
    plan = CommandPlan(project_id="p1", commands=(
        _command(IntentType.CHANGE_PAGE_DIRECTION, {"direction_id": "image-led"}, safety=CommandSafetyLevel.REVIEW_RECOMMENDED, rationale="move the block to x=120"),
    ))
    report = validate_command_plan(plan, _content())
    assert any(f.code == "CMD-008" for f in report.findings)


def test_cmd009_flags_mislabelled_safety_level():
    plan = CommandPlan(project_id="p1", commands=(
        _command(IntentType.REMOVE_CONTENT, {"content_ids": ["txt-01"]}, safety=CommandSafetyLevel.SAFE, rationale="oops"),
    ))
    report = validate_command_plan(plan, _content())
    assert any(f.code == "CMD-009" for f in report.findings)


def test_cmd010_warns_on_review_burden():
    commands = tuple(
        _command(IntentType.CHANGE_PAGE_DIRECTION, {"direction_id": "image-led"}, safety=CommandSafetyLevel.REVIEW_RECOMMENDED)
        for _ in range(5)
    )
    plan = CommandPlan(project_id="p1", commands=commands)
    report = validate_command_plan(plan, _content())
    assert any(f.code == "CMD-010" for f in report.findings)


def test_empty_plan_is_valid():
    plan = CommandPlan(project_id="p1")
    report = validate_command_plan(plan, _content())
    assert report.ok
