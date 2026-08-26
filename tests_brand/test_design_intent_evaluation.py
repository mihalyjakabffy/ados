"""
ADOS-M3.4 §50/§51 — brand/llm/design/evaluation.py, run against the
deterministic RuleBasedDesignIntentGenerator. Same CI-determinism
posture as tests_brand/test_narrative_evaluation.py: no
ANTHROPIC_API_KEY, no network, runs on every CI job.
"""

from __future__ import annotations

from brand.llm.design.evaluation import evaluate, load_dataset
from brand.llm.design.generation import RuleBasedDesignIntentGenerator


def test_dataset_loads_and_has_all_ten_acceptance_scenarios():
    cases = load_dataset()
    ids = {c["id"] for c in cases}
    assert len(cases) >= 10
    for scenario in (
        "case_a_editorial_portfolio", "case_b_technical_report", "case_c_client_presentation",
        "case_d_competition_presentation", "case_e_minimal_brand_preserved",
        "case_f_image_rich_project", "case_g_asset_poor_project",
        "case_h_brand_conflict_never_silently_overridden",
        "case_i_missing_information_acknowledged", "case_j_same_narrative_different_brand",
    ):
        assert scenario in ids


def test_rule_based_generator_scores_zero_hallucination_and_leakage():
    metrics = evaluate(RuleBasedDesignIntentGenerator())
    assert metrics.hallucination_rate == 0.0
    assert metrics.layout_leakage_rate == 0.0


def test_rule_based_generator_passes_every_case():
    metrics = evaluate(RuleBasedDesignIntentGenerator())
    for result in metrics.case_results:
        assert result.case_correct, result.case_id
        assert result.is_schema_valid
        assert result.coverage_ratio == 1.0


def test_rule_based_generator_scores_perfectly_on_structural_metrics():
    metrics = evaluate(RuleBasedDesignIntentGenerator())
    assert metrics.schema_validity_rate == 1.0
    assert metrics.coverage_rate == 1.0
    assert metrics.content_reference_validity == 1.0
    assert metrics.asset_reference_validity == 1.0
    assert metrics.brand_token_validity == 1.0
    assert metrics.constraint_compliance_rate == 1.0
    assert metrics.brand_consistency_rate == 1.0
