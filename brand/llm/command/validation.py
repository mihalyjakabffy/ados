"""
brand/llm/command/validation.py

Deterministic validation for a :class:`CommandPlan` — this package's
equivalent of ADOS-M3.2/M3.3/M3.4's own content/narrative/design
validators. Reuses the same ``brand.validation.brand_validator``
``Finding``/``Severity``/``Category``/``ValidationReport`` convention.

**CMD-001 is the load-bearing check**: it re-runs the real, existing
``brand.creative.intent.validate_intent`` against every command on the
plan, independently of whatever ``brand.llm.command.planning.plan_commands``
already did — the same "two layers that don't share code" discipline
ADOS-M3.2's hallucination guard established, applied here to the one
property that matters most: a command this package produced must still
be a command the pre-existing, already-shipped validator accepts.
Everything else below (CMD-002..010) is this package's own policy on
top of that: duplication, destructive-by-implication, safety-label
integrity, staleness, and layout leakage.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from brand.creative.intent import IntentType, TargetType, validate_intent
from brand.llm.command.vocabulary import SAFETY_BY_INTENT_TYPE, CommandSafetyLevel
from brand.validation.brand_validator import Category, Finding, Severity, ValidationReport

if TYPE_CHECKING:
    from brand.content.model import ContentModel
    from brand.llm.command.model import CommandPlan

_DIMENSION = re.compile(r"\b\d+(?:\.\d+)?\s?(mm|cm|pt|px|em|rem|%)\b", re.I)
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_COORDINATE = re.compile(r"\b[xy]\s*=\s*-?\d+(?:\.\d+)?\b", re.I)

_INCREASE_DECREASE_PAIRS: tuple[tuple[IntentType, IntentType], ...] = (
    (IntentType.INCREASE_TEXT_DENSITY, IntentType.REDUCE_TEXT_DENSITY),
    (IntentType.INCREASE_IMAGE_EMPHASIS, IntentType.DECREASE_IMAGE_EMPHASIS),
)

#: Above this many non-SAFE commands in one plan, a reviewer is being
#: asked to sign off on a lot at once — a minimality nudge (CMD-010),
#: not a hard limit this package enforces by refusing to generate more.
_MAX_REVIEW_BURDEN = 4


def validate_command_plan(
    plan: "CommandPlan",
    content: "ContentModel",
    page_count: Optional[int] = None,
    current_design_state_version: Optional[int] = None,
) -> ValidationReport:
    findings: list[Finding] = []

    findings.extend(_check_revalidate_against_intent_api(plan, content, page_count))
    findings.extend(_check_no_contradictory_pair(plan))
    findings.extend(_check_no_destructive_by_implication(plan))
    findings.extend(_check_page_target_in_range(plan, page_count))
    findings.extend(_check_design_state_not_stale(plan, current_design_state_version))
    findings.extend(_check_no_forbidden_parameters(plan))
    findings.extend(_check_rationale_present(plan))
    findings.extend(_check_no_layout_leakage(plan))
    findings.extend(_check_safety_label_integrity(plan))
    findings.extend(_check_review_burden(plan))

    return ValidationReport(brand_label=f"command:{plan.project_id}", findings=findings)


def _check_revalidate_against_intent_api(
    plan: "CommandPlan", content: "ContentModel", page_count: Optional[int],
) -> list[Finding]:
    findings = []
    for command in plan.commands:
        errors = validate_intent(content, command.intent, page_count=page_count)
        if errors:
            findings.append(Finding(
                Severity.BLOCK, Category.STRUCTURAL, f"command:{command.id}",
                f"{command.intent.type.value} fails the existing validate_intent(): "
                f"{'; '.join(errors)}", code="CMD-001",
            ))
    return findings


def _check_no_contradictory_pair(plan: "CommandPlan") -> list[Finding]:
    present = {c.intent.type for c in plan.commands}
    findings = []
    for a, b in _INCREASE_DECREASE_PAIRS:
        if a in present and b in present:
            findings.append(Finding(
                Severity.ERROR, Category.CONSISTENCY, "commands",
                f"plan contains both {a.value!r} and {b.value!r} — a single lever "
                f"cannot be pushed in two directions at once.", code="CMD-002",
            ))
    return findings


def _check_no_destructive_by_implication(plan: "CommandPlan") -> list[Finding]:
    findings = []
    for command in plan.commands:
        if command.intent.type is IntentType.REMOVE_CONTENT and not command.rationale.strip():
            findings.append(Finding(
                Severity.BLOCK, Category.STRUCTURAL, f"command:{command.id}",
                "remove_content carries no rationale — content may never be removed "
                "by implication; every destructive command must name what it is "
                "responding to.", code="CMD-003",
            ))
    return findings


def _check_page_target_in_range(plan: "CommandPlan", page_count: Optional[int]) -> list[Finding]:
    if page_count is None:
        return []
    findings = []
    for command in plan.commands:
        target = command.intent.target
        if target.type is TargetType.PAGE and target.id:
            try:
                idx = int(target.id)
            except ValueError:
                continue
            if not (0 <= idx < page_count):
                findings.append(Finding(
                    Severity.BLOCK, Category.STRUCTURAL, f"command:{command.id}",
                    f"targets page {idx}, which does not exist in a {page_count}-page "
                    f"document.", code="CMD-004",
                ))
    return findings


def _check_design_state_not_stale(plan: "CommandPlan", current_version: Optional[int]) -> list[Finding]:
    if plan.design_state_version is None or current_version is None:
        return []
    if plan.design_state_version != current_version and plan.commands:
        return [Finding(
            Severity.BLOCK, Category.STRUCTURAL, "design_state_version",
            f"this plan was compiled against DesignState version "
            f"{plan.design_state_version}, but the state it would be applied to is "
            f"now at version {current_version} — recompile before applying.",
            code="CMD-005",
        )]
    return []


def _check_no_forbidden_parameters(plan: "CommandPlan") -> list[Finding]:
    findings = []
    for command in plan.commands:
        for key, value in command.intent.parameters.items():
            if not isinstance(value, str):
                continue
            for pattern, label in ((_HEX, "a colour"), (_DIMENSION, "a dimension")):
                if pattern.search(value):
                    findings.append(Finding(
                        Severity.BLOCK, Category.STRUCTURAL, f"command:{command.id}",
                        f"parameter {key!r} names {label} ({value!r}) — a command may "
                        f"never carry geometry or colour.", code="CMD-006",
                    ))
    return findings


def _check_rationale_present(plan: "CommandPlan") -> list[Finding]:
    return [
        Finding(
            Severity.WARN, Category.CONSISTENCY, f"command:{c.id}",
            f"{c.intent.type.value} carries no rationale — a reviewer cannot see why "
            f"it was proposed.", code="CMD-007",
        )
        for c in plan.commands if not c.rationale.strip()
    ]


def _check_no_layout_leakage(plan: "CommandPlan") -> list[Finding]:
    findings = []
    for command in plan.commands:
        for pattern, label in ((_DIMENSION, "a dimension"), (_HEX, "a colour"), (_COORDINATE, "a coordinate")):
            if pattern.search(command.rationale):
                findings.append(Finding(
                    Severity.ERROR, Category.STRUCTURAL, f"command:{command.id}",
                    f"rationale names {label} ({command.rationale!r}) — a command's "
                    f"justification is semantic, never geometric.", code="CMD-008",
                ))
    return findings


def _check_safety_label_integrity(plan: "CommandPlan") -> list[Finding]:
    findings = []
    for command in plan.commands:
        expected = SAFETY_BY_INTENT_TYPE.get(command.intent.type)
        if expected is not None and command.safety_level is not expected:
            findings.append(Finding(
                Severity.BLOCK, Category.STRUCTURAL, f"command:{command.id}",
                f"{command.intent.type.value} is labelled {command.safety_level.value!r}, "
                f"but this IntentType is always {expected.value!r}.", code="CMD-009",
            ))
    return findings


def _check_review_burden(plan: "CommandPlan") -> list[Finding]:
    non_safe = sum(1 for c in plan.commands if c.safety_level is not CommandSafetyLevel.SAFE)
    if non_safe > _MAX_REVIEW_BURDEN:
        return [Finding(
            Severity.WARN, Category.CONSISTENCY, "commands",
            f"{non_safe} non-safe commands in one plan — consider whether this "
            f"compilation could be split into smaller, independently reviewable "
            f"steps.", code="CMD-010",
        )]
    return []
