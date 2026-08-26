"""
ADOS-M3.6 §65/§66 — brand/llm/loop/evaluation.py, the 15 closed-loop
scenarios (A-O). CI-safe: no ANTHROPIC_API_KEY, no network.
"""

from __future__ import annotations

import pytest

from brand.llm.loop.evaluation import CASES, evaluate


@pytest.fixture(autouse=True)
def _no_llm_and_clean_state(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from brand.llm.loop.observability import clear_lineages

    clear_lineages()


def test_all_fifteen_scenarios_are_registered():
    assert len(CASES) >= 15
    ids = {c.__name__ for c in CASES}
    for expected in (
        "case_a_already_valid_design", "case_b_single_finding_single_fix",
        "case_c_related_findings_one_recommendation", "case_d_independent_findings_sequential",
        "case_e_no_progress", "case_f_regression", "case_g_oscillation", "case_h_stale_state",
        "case_i_unsupported_scope", "case_j_invalid_command", "case_k_awaiting_approval",
        "case_l_max_iterations", "case_m_provider_failure_safe_fallback",
        "case_n_monotonic_decrease", "case_o_full_end_to_end",
    ):
        assert expected in ids


def test_every_scenario_passes():
    metrics = evaluate()
    for result in metrics.case_results:
        assert result.passed, (result.case_id, result.detail)


def test_safety_metrics_are_zero():
    metrics = evaluate()
    assert metrics.hallucination_rate == 0.0
    assert metrics.unsafe_execution_rate == 0.0
    assert metrics.stale_execution_rate == 0.0
    assert metrics.bypass_rate == 0.0


def test_case_accuracy_is_perfect():
    metrics = evaluate()
    assert metrics.case_accuracy == 1.0
