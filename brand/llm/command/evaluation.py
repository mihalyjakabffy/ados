"""
brand/llm/command/evaluation.py

ADOS-M3.5's evaluation harness — mirrors
``brand.llm.design.evaluation``'s own shape, run against the
deterministic ``RuleBasedCommandGenerator`` so it is CI-safe (no
network, no ``ANTHROPIC_API_KEY``). Each case constructs a real
``DesignIntent`` and a lightweight stand-in for the "current" real
``DesignState`` fields this package actually reads
(``brand.llm.command.context.resolve_current_visual_state`` only ever
touches ``version.number``/``document.direction_id``/
``visual_language.{text_density,image_ratio}``/``len(pages)`` — a
``SimpleNamespace`` exposing exactly those is not a fixture shortcut,
it is the real read surface).

Metrics target the master prompt's own 0% safety thresholds:
``hallucination_rate`` (a command names a direction/parameter this
package's own closed lookup tables never produced) and
``unsafe_execution_rate`` (a command's claimed safety_level disagrees
with ``SAFETY_BY_INTENT_TYPE``) must both be exactly 0 for the
deterministic generator, checked independently of
``brand.llm.command.validation`` rather than trusting that module's own
CMD-006/CMD-009 to catch a regression in this one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from brand.content.model import BlockRole, BlockType, ContentBlock, ContentModel
from brand.creative.directions import DIRECTIONS
from brand.llm.command.generation import CommandGenerator, RuleBasedCommandGenerator
from brand.llm.command.model import CommandPlan
from brand.llm.command.planning import plan_commands
from brand.llm.command.validation import validate_command_plan
from brand.llm.command.vocabulary import SAFETY_BY_INTENT_TYPE
from brand.llm.design.model import DesignIntent

_DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "tests_brand" / "data" / "command_eval.json"


def _fake_content() -> ContentModel:
    import uuid

    return ContentModel(project_id=uuid.uuid4(), project_name="eval", blocks=(
        ContentBlock(id="txt-01", type=BlockType.NARRATIVE, role=BlockRole.CONTEXT, priority=1, text="content " * 20),
    ))


def _fake_state(raw: Optional[dict[str, Any]]):
    if raw is None:
        return None
    return SimpleNamespace(
        version=SimpleNamespace(number=raw.get("version_number")),
        document=SimpleNamespace(direction_id=raw.get("direction_id", "")),
        visual_language=SimpleNamespace(text_density=raw.get("text_density"), image_ratio=raw.get("image_ratio")),
        pages=tuple(SimpleNamespace() for _ in range(raw.get("page_count", 0))),
    )


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    command_plan: CommandPlan
    expected_types: frozenset[str]
    actual_types: frozenset[str]
    case_correct: bool
    is_schema_valid: bool
    hallucinated: bool
    unsafe: bool
    layout_leakage: bool
    expected_skip_reason_present: bool


@dataclass(frozen=True)
class EvaluationMetrics:
    case_results: tuple[CaseResult, ...] = ()

    @property
    def case_accuracy(self) -> float:
        return _rate(r.case_correct for r in self.case_results)

    @property
    def schema_validity_rate(self) -> float:
        return _rate(r.is_schema_valid for r in self.case_results)

    @property
    def hallucination_rate(self) -> float:
        return _rate(r.hallucinated for r in self.case_results)

    @property
    def unsafe_execution_rate(self) -> float:
        return _rate(r.unsafe for r in self.case_results)

    @property
    def layout_leakage_rate(self) -> float:
        return _rate(r.layout_leakage for r in self.case_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_count": len(self.case_results),
            "case_accuracy": self.case_accuracy,
            "schema_validity_rate": self.schema_validity_rate,
            "hallucination_rate": self.hallucination_rate,
            "unsafe_execution_rate": self.unsafe_execution_rate,
            "layout_leakage_rate": self.layout_leakage_rate,
            "cases": [
                {
                    "case_id": r.case_id, "correct": r.case_correct,
                    "expected_types": sorted(r.expected_types), "actual_types": sorted(r.actual_types),
                }
                for r in self.case_results
            ],
        }


def _rate(flags) -> float:
    values = list(flags)
    return (sum(1 for v in values if v) / len(values)) if values else 0.0


def load_dataset(path: Optional[Path] = None) -> list[dict[str, Any]]:
    with open(path or _DEFAULT_DATASET, encoding="utf-8") as fh:
        return json.load(fh)


def run_case(generator: CommandGenerator, case: dict[str, Any]) -> CaseResult:
    design_intent = DesignIntent.model_validate(case["design_intent"])
    current_state = _fake_state(case.get("current_state"))
    content = _fake_content()

    plan = plan_commands(design_intent, content, design_state=current_state, generator=generator)
    validation = validate_command_plan(
        plan, content,
        page_count=(current_state.pages and len(current_state.pages)) if current_state else None,
        current_design_state_version=current_state.version.number if current_state else None,
    )

    actual_types = frozenset(c.intent.type.value for c in plan.commands)
    expected_types = frozenset(case.get("expect_command_types", []))
    case_correct = actual_types == expected_types

    known_direction_ids = set(DIRECTIONS)
    hallucinated = any(
        c.intent.parameters.get("direction_id") not in known_direction_ids
        for c in plan.commands if "direction_id" in c.intent.parameters
    )
    unsafe = any(SAFETY_BY_INTENT_TYPE.get(c.intent.type) is not c.safety_level for c in plan.commands)

    expected_skip_reason = case.get("expect_skip_reason")
    expected_skip_present = (
        expected_skip_reason is None
        or any(s.reason.value == expected_skip_reason for s in plan.skipped)
    )

    return CaseResult(
        case_id=case["id"], command_plan=plan, expected_types=expected_types, actual_types=actual_types,
        case_correct=case_correct, is_schema_valid=validation.ok,
        hallucinated=hallucinated, unsafe=unsafe,
        layout_leakage=any(f.code == "CMD-008" for f in validation.findings),
        expected_skip_reason_present=expected_skip_present,
    )


def evaluate(generator: CommandGenerator, cases: Optional[list[dict[str, Any]]] = None) -> EvaluationMetrics:
    cases = cases if cases is not None else load_dataset()
    return EvaluationMetrics(case_results=tuple(run_case(generator, c) for c in cases))
