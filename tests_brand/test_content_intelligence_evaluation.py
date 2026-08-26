"""
ADOS-M3.2 §28/§42 — brand/llm/content/evaluation.py, run against the
deterministic RuleBasedContentExtractor. Same CI-determinism posture as
tests_brand/test_semantic_intent_evaluation.py: no ANTHROPIC_API_KEY, no
network, runs on every CI job.
"""

from __future__ import annotations

from brand.llm.content.evaluation import evaluate, load_dataset
from brand.llm.content.extraction import RuleBasedContentExtractor


def test_dataset_loads_and_has_all_seven_acceptance_scenarios():
    cases = load_dataset()
    ids = {c["id"] for c in cases}
    assert len(cases) >= 8
    for scenario in (
        "scenario_a_basic_project", "scenario_b_missing_information",
        "scenario_c_conflicting_sources", "scenario_d_fact_vs_claim",
        "scenario_e_unsupported_inference", "scenario_f_image_asset",
        "scenario_g_user_correction",
    ):
        assert scenario in ids


def test_rule_based_extractor_scores_zero_hallucination_rate():
    metrics = evaluate(RuleBasedContentExtractor())
    assert metrics.hallucination_rate == 0.0


def test_rule_based_extractor_passes_every_case():
    metrics = evaluate(RuleBasedContentExtractor())
    for result in metrics.case_results:
        assert not result.hallucinated, result.case_id
        assert all(result.fact_correct.values()), (result.case_id, result.fact_correct)
        assert all(result.claim_correct.values()), (result.case_id, result.claim_correct)
        assert result.resolution_correct, result.case_id
        assert result.validation_matches_expectation, result.case_id
        assert result.is_schema_valid


def test_rule_based_extractor_scores_perfectly_on_every_metric():
    metrics = evaluate(RuleBasedContentExtractor())
    assert metrics.fact_accuracy == 1.0
    assert metrics.claim_detection_rate == 1.0
    assert metrics.conflict_detection_rate == 1.0
    assert metrics.dedup_accuracy == 1.0
    assert metrics.entity_resolution_accuracy == 1.0
    assert metrics.missing_information_detection_rate == 1.0
    assert metrics.schema_validity_rate == 1.0
    assert metrics.domain_validation_success_rate == 1.0
    assert metrics.resolution_accuracy == 1.0
