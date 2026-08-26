"""
ADOS-M3.1 §18 — the evaluation suite, run against the deterministic
rule-based provider (no network, no credentials — every CI run gets
this). ``scripts/run_semantic_intent_eval.py`` runs the identical
dataset against the real Claude provider for a human to read, whenever
a key is actually available.

Thresholds below are floors, not the observed score — the point is to
catch a real regression in either the provider or the dataset, not to
pin today's exact numbers.
"""

from __future__ import annotations

from brand.llm.evaluation import evaluate, load_dataset
from brand.llm.providers.rule_based_provider import RuleBasedProvider


def test_dataset_loads_and_has_every_required_field():
    cases = load_dataset()
    assert len(cases) >= 10
    for case in cases:
        assert case["id"]
        assert case["input"]
        assert "context" in case
        assert "expected_intent" in case
        assert "acceptable_variants" in case
        assert "forbidden_inferences" in case
        assert "expect_validation_ok" in case


def test_schema_validity_is_always_100_percent():
    """Every provider output that reaches this harness is already a real
    SemanticIntent — a schema-invalid response never gets this far
    (brand.llm.provider.ProviderError is raised inside extract() instead)."""
    metrics = evaluate(RuleBasedProvider())
    assert metrics.schema_validity_rate == 1.0


def test_hallucination_rate_is_zero_for_the_rule_based_provider():
    """The rule-based provider must never contradict a case's own
    forbidden_inferences — it is conservative by construction (ADOS-M3.1
    §6), so this is a hard floor, not an aspiration."""
    metrics = evaluate(RuleBasedProvider())
    assert metrics.hallucination_rate == 0.0


def test_domain_validation_success_rate_is_high():
    metrics = evaluate(RuleBasedProvider())
    assert metrics.domain_validation_success_rate >= 0.85


def test_action_classification_accuracy_is_high():
    metrics = evaluate(RuleBasedProvider())
    assert metrics.field_accuracy.get("action", 0.0) >= 0.8


def test_document_type_resolution_accuracy_is_high():
    metrics = evaluate(RuleBasedProvider())
    assert metrics.field_accuracy.get("document_type", 0.0) >= 0.6


def test_every_case_result_carries_a_real_semantic_intent():
    from brand.llm.semantic_intent import SemanticIntent

    metrics = evaluate(RuleBasedProvider())
    for result in metrics.case_results:
        assert isinstance(result.intent, SemanticIntent)
