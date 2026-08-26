"""ADOS-M3.6 — brand/llm/loop/vocabulary.py."""

from __future__ import annotations

from brand.llm.command.vocabulary import CommandSafetyLevel
from brand.llm.loop.vocabulary import (
    TERMINAL_STATUSES,
    AutonomyLevel,
    FindingResolutionStatus,
    IterationStatus,
    IterationTrigger,
    PatchOperation,
    RecommendationSource,
    SkippedRecommendationReason,
    StopReason,
)


def test_terminal_statuses_are_the_documented_five():
    assert TERMINAL_STATUSES == {
        IterationStatus.COMPLETED, IterationStatus.STOPPED,
        IterationStatus.FAILED, IterationStatus.BLOCKED, IterationStatus.AWAITING_APPROVAL,
    }


def test_every_enum_value_is_unique():
    for enum_cls in (
        IterationStatus, StopReason, IterationTrigger, AutonomyLevel,
        FindingResolutionStatus, RecommendationSource, SkippedRecommendationReason, PatchOperation,
    ):
        values = [e.value for e in enum_cls]
        assert len(values) == len(set(values))


def test_autonomy_levels_map_conceptually_onto_command_safety_levels():
    # Not a literal value equality — a documentation-level sanity check
    # that this package's autonomy vocabulary and M3.5's own safety
    # vocabulary are the same size class of concept (three real levels
    # plus a "do nothing" level), not an accidental drift.
    assert len(list(AutonomyLevel)) == len(list(CommandSafetyLevel)) + 1
