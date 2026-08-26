"""
ADOS-M3.5 — brand/llm/command/evaluation.py, run against the
deterministic RuleBasedCommandGenerator. CI-safe: no ANTHROPIC_API_KEY,
no network. Mirrors test_design_intent_evaluation.py's own shape.
"""

from __future__ import annotations

from brand.llm.command.evaluation import evaluate, load_dataset
from brand.llm.command.generation import RuleBasedCommandGenerator


def test_dataset_loads_and_has_all_ten_scenarios():
    cases = load_dataset()
    ids = {c["id"] for c in cases}
    assert len(cases) >= 10
    for scenario in (
        "case_a_confident_direction_no_current_state", "case_b_already_matching_no_commands",
        "case_c_density_increase_needed", "case_d_density_decrease_needed",
        "case_e_ambiguous_composition_strategy_no_hallucination",
        "case_f_stale_design_state_blocks_everything", "case_g_image_emphasis_from_section_signal",
        "case_h_brand_conflict_recorded_not_auto_fixed",
        "case_i_composite_three_simultaneous_levers_all_pass_validate_intent",
        "case_j_no_design_state_at_all_direction_only",
    ):
        assert scenario in ids


def test_rule_based_generator_scores_zero_hallucination_and_zero_unsafe():
    metrics = evaluate(RuleBasedCommandGenerator())
    assert metrics.hallucination_rate == 0.0
    assert metrics.unsafe_execution_rate == 0.0
    assert metrics.layout_leakage_rate == 0.0


def test_rule_based_generator_passes_every_case():
    metrics = evaluate(RuleBasedCommandGenerator())
    for result in metrics.case_results:
        assert result.case_correct, (result.case_id, sorted(result.actual_types), sorted(result.expected_types))
        assert result.is_schema_valid, result.case_id
        assert result.expected_skip_reason_present, result.case_id


def test_rule_based_generator_scores_perfectly_on_structural_metrics():
    metrics = evaluate(RuleBasedCommandGenerator())
    assert metrics.case_accuracy == 1.0
    assert metrics.schema_validity_rate == 1.0
