"""ADOS-M3.6 — brand/llm/loop/model.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brand.llm.loop.model import (
    PATCHABLE_FIELDS,
    DesignIntentPatch,
    FindingRecord,
    Iteration,
    IterationMetrics,
    IterationPolicy,
    Recommendation,
    SkippedRecommendation,
)
from brand.llm.loop.vocabulary import (
    FindingResolutionStatus,
    IterationStatus,
    IterationTrigger,
    RecommendationSource,
    SkippedRecommendationReason,
)


def test_patchable_fields_are_real_design_intent_fields():
    from brand.llm.design.model import DesignIntent

    for field_name in PATCHABLE_FIELDS:
        assert field_name in DesignIntent.model_fields


def test_design_intent_patch_is_frozen():
    patch = DesignIntentPatch(target="density", value="low")
    with pytest.raises(ValidationError):
        patch.value = "high"


def test_recommendation_requires_a_patch():
    with pytest.raises(ValidationError):
        Recommendation(
            finding_fingerprint="x", action="density", priority=0, confidence=1.0,
            source=RecommendationSource.DETERMINISTIC,
        )


def test_iteration_policy_defaults_are_conservative():
    policy = IterationPolicy()
    assert policy.max_iterations == 5
    assert policy.max_llm_calls <= 10


def test_iteration_metrics_default_to_zero():
    metrics = IterationMetrics()
    assert metrics.total_findings == 0
    assert metrics.command_count == 0


def _iteration(**overrides) -> Iteration:
    defaults = dict(
        project_id="p1", document_id="d1", sequence=1, trigger=IterationTrigger.INITIAL,
        status=IterationStatus.COMPLETED,
    )
    defaults.update(overrides)
    return Iteration(**defaults)


def test_iteration_is_frozen_and_serializable():
    it = _iteration()
    with pytest.raises(ValidationError):
        it.status = IterationStatus.FAILED
    payload = it.to_dict()
    assert payload["project_id"] == "p1"
    assert payload["sequence"] == 1


def test_iteration_first_iteration_has_no_parent():
    it = _iteration()
    assert it.parent_iteration_id is None


def test_finding_record_and_skipped_recommendation_round_trip():
    record = FindingRecord(
        fingerprint="fp1", finding={"severity": "WARN", "code": "X"},
        status=FindingResolutionStatus.OPEN, first_seen_sequence=1, last_seen_sequence=1,
    )
    it = _iteration(findings=(record,), skipped_recommendations=(
        SkippedRecommendation(finding_fingerprint="fp1", reason=SkippedRecommendationReason.NO_SAFE_COMMAND_EXISTS),
    ))
    payload = it.to_dict()
    assert payload["findings"][0]["fingerprint"] == "fp1"
    assert payload["skipped_recommendations"][0]["reason"] == "no_safe_command_exists"
