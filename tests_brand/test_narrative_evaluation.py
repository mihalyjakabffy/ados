"""
ADOS-M3.3 §41/§42 — brand/llm/narrative/evaluation.py, run against the
deterministic RuleBasedNarrativeGenerator. Same CI-determinism posture
as tests_brand/test_content_intelligence_evaluation.py: no
ANTHROPIC_API_KEY, no network, runs on every CI job.
"""

from __future__ import annotations

from brand.llm.narrative.evaluation import evaluate, load_dataset
from brand.llm.narrative.generation import RuleBasedNarrativeGenerator


def test_dataset_loads_and_has_all_ten_acceptance_scenarios():
    cases = load_dataset()
    ids = {c["id"] for c in cases}
    assert len(cases) >= 10
    for scenario in (
        "case_a_portfolio_concept_driven",
        "case_b_client_presentation_problem_solution_value",
        "case_c_competition_question_to_outcome",
        "case_d_technical_report_requirements_to_solution",
        "case_e_missing_information_surfaced",
        "case_f_conflicting_sources_surfaced",
        "case_g_unsupported_claim_trap",
        "case_h_audience_transformation_client",
        "case_h_audience_transformation_jury",
        "case_i_compression_short",
        "case_i_compression_long",
    ):
        assert scenario in ids


def test_rule_based_generator_scores_zero_hallucination_rate():
    metrics = evaluate(RuleBasedNarrativeGenerator())
    assert metrics.hallucination_rate == 0.0


def test_rule_based_generator_passes_every_case():
    metrics = evaluate(RuleBasedNarrativeGenerator())
    for result in metrics.case_results:
        assert result.case_correct, result.case_id
        assert result.dangling_refs == 0, result.case_id
        assert result.validation_matches_expectation, result.case_id
        assert result.is_schema_valid


def test_rule_based_generator_scores_perfectly_on_grounding_and_schema():
    metrics = evaluate(RuleBasedNarrativeGenerator())
    assert metrics.grounding_rate == 1.0
    assert metrics.content_reference_validity == 1.0
    assert metrics.strategy_fit_rate == 1.0
    assert metrics.audience_accuracy == 1.0
    assert metrics.missing_information_detection_rate == 1.0
    assert metrics.conflict_detection_rate == 1.0
    assert metrics.schema_validity_rate == 1.0
    assert metrics.domain_validation_success_rate == 1.0
