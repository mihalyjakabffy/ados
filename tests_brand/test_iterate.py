"""
The closed-loop iteration layer: brand/creative/iterate.py.

Mirrors tests_brand/test_intent.py and tests_brand/test_scope.py's posture:
these tests are about this module's own contract (a finding maps to a
recommendation deterministically, an iteration is genuinely page-scoped,
a command that does not help fails cleanly) — not about the Composer or
the review checks themselves, which their own suites already cover. Every
recommendation produced here is also run all the way through
compose_scoped(), because a mapping that merely looks right on paper
would be a false confidence.
"""

from __future__ import annotations

import pytest

from brand.creative.composer import compose
from brand.creative.directions import get_direction
from brand.creative.evaluate import evaluate
from brand.creative.finding_registry import FINDING_REGISTRY
from brand.creative.iterate import (
    CAPABILITIES,
    CAPABILITIES_BY_FINDING_CODE,
    IterationHistoryEntry,
    IterationNoImprovementError,
    IterationOutcome,
    NoRecommendationError,
    Recommendation,
    explain,
    iterate,
    recommend,
    select_recommendation,
)
from brand.examples.malthouse import malthouse_content
from brand.validation.brand_validator import Category, Finding, Severity


@pytest.fixture(scope="module")
def content():
    return malthouse_content()


@pytest.fixture(scope="module")
def studio_nord():
    from brand.examples.studio_nord import studio_nord as build

    return build()


@pytest.fixture()
def direction():
    return get_direction("editorial-quiet")


@pytest.fixture(scope="module")
def base_plan(content, studio_nord):
    return compose(content, get_direction("editorial-quiet"), studio_nord)


@pytest.fixture()
def fill_ratio_low_finding(base_plan, direction, studio_nord):
    ev = evaluate(base_plan, direction, studio_nord.resolve_tokens())
    return next(f for f in ev.report.findings if f.code == "FILL_RATIO_LOW")


# ---------------------------------------------------------------------------
# recommend() — finding -> recommendation, deterministically
# ---------------------------------------------------------------------------


def test_a_fill_ratio_low_finding_maps_to_a_recommendation(fill_ratio_low_finding):
    rec = recommend(fill_ratio_low_finding)
    assert isinstance(rec, Recommendation)
    assert rec.finding_code == "FILL_RATIO_LOW"
    assert rec.target_page == fill_ratio_low_finding.page_index
    assert rec.expected_direction == "increase"


def test_recommend_is_a_pure_function_of_the_finding(fill_ratio_low_finding):
    r1 = recommend(fill_ratio_low_finding)
    r2 = recommend(fill_ratio_low_finding)
    assert r1 == r2


def test_an_unmapped_finding_code_has_no_recommendation():
    finding = Finding(
        Severity.WARN, Category.CONSISTENCY, "page 1", "not a real problem",
        code="SOME_UNMAPPED_CODE", page_index=0,
    )
    with pytest.raises(NoRecommendationError, match="no deterministic command mapping"):
        recommend(finding)


def test_a_finding_with_no_code_has_no_recommendation():
    finding = Finding(Severity.WARN, Category.CONSISTENCY, "plan", "a plain, code-less finding", page_index=0)
    with pytest.raises(NoRecommendationError):
        recommend(finding)


def test_a_document_level_finding_has_no_page_to_target():
    finding = Finding(
        Severity.WARN, Category.CONSISTENCY, "plan", "no single page",
        code="FILL_RATIO_LOW",
    )
    with pytest.raises(NoRecommendationError, match="does not name a target page"):
        recommend(finding)


def test_fill_ratio_high_is_a_real_code_with_no_mapping_yet(base_plan):
    """H13's ceiling finding is wired (brand/creative/evaluate.py) but
    deliberately unmapped — see brand/creative/iterate.py's module
    docstring. A finding existing is not the same as it being actionable."""
    finding = Finding(
        Severity.ERROR, Category.STRUCTURAL, "page 1", "over the ceiling",
        code="FILL_RATIO_HIGH", metric="fill_ratio", actual=0.9, threshold=0.85, page_index=0,
    )
    with pytest.raises(NoRecommendationError):
        recommend(finding)


# ---------------------------------------------------------------------------
# iterate() — the full loop, through the real Composer
# ---------------------------------------------------------------------------


def test_iterate_recomposes_only_the_target_page(base_plan, content, direction, studio_nord, fill_ratio_low_finding):
    result = iterate(base_plan, fill_ratio_low_finding, content, direction, studio_nord)
    target = fill_ratio_low_finding.page_index
    for i, page in enumerate(base_plan.pages):
        if i == target:
            continue
        assert result.plan.pages[i] == page, f"page {i} must be byte-identical but changed"
    assert result.plan.pages[target] != base_plan.pages[target]
    assert result.diff.changed_pages == (target,)
    assert result.diff.unchanged_pages == tuple(i for i in range(len(base_plan.pages)) if i != target)


def test_iterate_moves_the_metric_in_the_expected_direction(
    base_plan, content, direction, studio_nord, fill_ratio_low_finding
):
    result = iterate(base_plan, fill_ratio_low_finding, content, direction, studio_nord)
    assert result.metric == "fill_ratio"
    assert result.after_metric > result.before_metric
    assert result.before_metric == fill_ratio_low_finding.actual
    # Real content: genuinely improved, still short of the 0.40 guideline —
    # ADOS-M1.4 §12 / M1.5 §11's explicitly distinct, still-successful state.
    assert result.outcome is IterationOutcome.IMPROVED_BUT_THRESHOLD_NOT_REACHED


def test_iterate_produces_a_valid_resulting_pageplan(
    base_plan, content, direction, studio_nord, fill_ratio_low_finding
):
    result = iterate(base_plan, fill_ratio_low_finding, content, direction, studio_nord)
    assert len(result.plan.pages) == len(base_plan.pages)
    assert result.plan.plan_hash
    assert result.plan.plan_hash != base_plan.plan_hash


def test_a_second_review_sees_the_improved_state(
    base_plan, content, direction, studio_nord, fill_ratio_low_finding
):
    """ADOS-M1.4 §12 accepts either outcome: PASS, or an improved WARN —
    the same finding may legitimately still fire (0.29 is still under the
    0.40 guideline) as long as its own reported number moved. Silently
    patching the metric is what §12 actually forbids; re-reviewing the
    real post-compose plan is what this asserts."""
    result = iterate(base_plan, fill_ratio_low_finding, content, direction, studio_nord)
    target = fill_ratio_low_finding.page_index
    still_low = [
        f for f in result.after_evaluation["findings"]
        if f["code"] == "FILL_RATIO_LOW" and f["page_index"] == target
    ]
    if still_low:
        assert still_low[0]["actual"] > fill_ratio_low_finding.actual
    assert result.after_evaluation["plan_hash"] == result.plan.plan_hash


def test_iterate_carries_the_intent_and_scope_used(
    base_plan, content, direction, studio_nord, fill_ratio_low_finding
):
    result = iterate(base_plan, fill_ratio_low_finding, content, direction, studio_nord)
    assert result.intent.type.value == "change_page_direction"
    assert result.intent.target.type.value == "page"
    assert result.intent.target.id == str(fill_ratio_low_finding.page_index)
    assert result.resolved_scope.type.value == "page"
    assert result.resolved_scope.id == str(fill_ratio_low_finding.page_index)


# ---------------------------------------------------------------------------
# Scope invariant — the mandatory byte-identical-elsewhere property,
# tested explicitly by hash rather than only by equality (ADOS-M1.4 §10).
# ---------------------------------------------------------------------------


def test_non_target_pages_are_byte_identical_by_hash(
    base_plan, content, direction, studio_nord, fill_ratio_low_finding
):
    import hashlib
    import json

    def page_hash(page) -> str:
        payload = json.dumps(page.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    before_hashes = [page_hash(p) for p in base_plan.pages]
    result = iterate(base_plan, fill_ratio_low_finding, content, direction, studio_nord)
    after_hashes = [page_hash(p) for p in result.plan.pages]

    target = fill_ratio_low_finding.page_index
    for i in range(len(before_hashes)):
        if i == target:
            assert after_hashes[i] != before_hashes[i]
        else:
            assert after_hashes[i] == before_hashes[i], f"page {i} hash changed but should not have"


# ---------------------------------------------------------------------------
# Determinism — ADOS-M1.4 §20, the critical acceptance criterion
# ---------------------------------------------------------------------------


def test_the_same_iteration_run_twice_is_byte_identical(
    base_plan, content, direction, studio_nord, fill_ratio_low_finding
):
    result_a = iterate(base_plan, fill_ratio_low_finding, content, direction, studio_nord)
    result_b = iterate(base_plan, fill_ratio_low_finding, content, direction, studio_nord)
    assert result_a.plan == result_b.plan
    assert result_a.plan.plan_hash == result_b.plan.plan_hash
    assert result_a.recommendation == result_b.recommendation
    assert result_a.before_metric == result_b.before_metric
    assert result_a.after_metric == result_b.after_metric


# ---------------------------------------------------------------------------
# Failure behaviour — ADOS-M1.4 §17: fail cleanly, never fake success
# ---------------------------------------------------------------------------


def test_a_command_that_does_not_improve_the_metric_fails_cleanly(
    base_plan, content, direction, studio_nord
):
    """The spec's own illustrative mapping (FILL_RATIO_LOW ->
    increase_image_emphasis) is a real, reproducible case of this: that
    command never changes a page-scoped fixed block set's fill ratio in
    this content (see iterate.py's module docstring). Reproduced here
    directly against brand.creative.scope.compose_scoped, then fed through
    iterate()'s own improvement check via a rigged 'actual' value, so the
    failure path is exercised without depending on a second real command
    mapping existing."""
    finding = Finding(
        Severity.WARN, Category.CONSISTENCY, "page 5", "rigged so the real, working "
        "recommendation cannot look like an improvement",
        code="FILL_RATIO_LOW", metric="fill_ratio", actual=0.99, threshold=0.4, page_index=4,
    )
    with pytest.raises(IterationNoImprovementError) as excinfo:
        iterate(base_plan, finding, content, direction, studio_nord)
    assert excinfo.value.before == 0.99
    assert excinfo.value.after < 0.99
    # ADOS-M1.5 §19: movement in the wrong direction is FAILED, not the
    # same NO_IMPROVEMENT an unchanged metric would report.
    assert excinfo.value.outcome is IterationOutcome.FAILED


def test_no_improvement_failure_does_not_mutate_the_base_plan(
    base_plan, content, direction, studio_nord
):
    before_hash = base_plan.plan_hash
    finding = Finding(
        Severity.WARN, Category.CONSISTENCY, "page 5", "rigged",
        code="FILL_RATIO_LOW", metric="fill_ratio", actual=0.99, threshold=0.4, page_index=4,
    )
    with pytest.raises(IterationNoImprovementError):
        iterate(base_plan, finding, content, direction, studio_nord)
    assert base_plan.plan_hash == before_hash


def test_increase_image_emphasis_genuinely_does_not_move_fill_ratio_on_real_content(
    base_plan, content, direction, studio_nord, fill_ratio_low_finding
):
    """Ground truth for the module docstring's architectural claim,
    verified independently of iterate() itself: on the real target page,
    the spec's illustrative command is a same-hash no-op under page scope."""
    from brand.creative.intent import CommandIntent, IntentTarget, IntentType, TargetType, apply_intent
    from brand.creative.scope import CompositionScope, ScopeType, compose_scoped

    target = fill_ratio_low_finding.page_index
    intent = CommandIntent(
        type=IntentType.INCREASE_IMAGE_EMPHASIS,
        target=IntentTarget(type=TargetType.PAGE, id=str(target)),
        parameters={"strength": 1.0},
    )
    new_content, new_direction, _ = apply_intent(content, direction, intent)
    scope = CompositionScope(type=ScopeType.PAGE, id=str(target))
    new_plan, _, _ = compose_scoped(base_plan, scope, new_content, new_direction, studio_nord)
    assert new_plan.pages[target].fill_ratio == base_plan.pages[target].fill_ratio


# ---------------------------------------------------------------------------
# ADOS-M1.5 — RecommendationCapability registry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("capability", CAPABILITIES, ids=lambda c: "|".join(sorted(c.finding_codes)))
def test_every_capability_references_valid_finding_codes(capability):
    for code in capability.finding_codes:
        assert code in FINDING_REGISTRY, f"capability references unregistered finding code {code!r}"


@pytest.mark.parametrize("capability", CAPABILITIES, ids=lambda c: "|".join(sorted(c.finding_codes)))
def test_every_capability_declares_metric_direction_and_scope(capability):
    assert capability.metric
    assert capability.expected_direction in ("increase", "decrease")
    assert capability.scope is not None
    assert capability.command_type is not None
    assert capability.description


def test_capabilities_by_finding_code_is_derived_not_duplicated():
    """One capability, one dict built from it — not two hand-kept mappings
    that could drift apart."""
    for code, capability in CAPABILITIES_BY_FINDING_CODE.items():
        assert code in capability.finding_codes


def test_a_capability_precondition_rejects_a_mismatched_metric(base_plan):
    """The built-in _metric_matches precondition: a finding claiming a
    different metric than the capability it would otherwise match must
    not be recommended — a real structural guard, not a placeholder."""
    mismatched = Finding(
        Severity.WARN, Category.CONSISTENCY, "page 5", "wrong metric on purpose",
        code="FILL_RATIO_LOW", metric="image_ratio", actual=0.1, threshold=0.4, page_index=4,
    )
    with pytest.raises(NoRecommendationError, match="does not match capability metric"):
        recommend(mismatched)


# ---------------------------------------------------------------------------
# ADOS-M1.5 — multi-finding deterministic ranking
# ---------------------------------------------------------------------------


def _low(page_index: int, actual: float, code: str = "FILL_RATIO_LOW") -> Finding:
    return Finding(
        Severity.WARN, Category.CONSISTENCY, f"page {page_index + 1}", f"synthetic finding on page {page_index + 1}",
        code=code, metric="fill_ratio", actual=actual, threshold=0.4, page_index=page_index,
    )


def test_multiple_findings_rank_by_largest_deviation_from_threshold():
    closer = _low(0, actual=0.35)   # |0.35-0.40| = 0.05
    further = _low(1, actual=0.10)  # |0.10-0.40| = 0.30
    rec = select_recommendation([closer, further])
    assert rec.target_page == 1


def test_ranking_ignores_input_order():
    closer = _low(0, actual=0.35)
    further = _low(1, actual=0.10)
    rec_forward = select_recommendation([closer, further])
    rec_backward = select_recommendation([further, closer])
    assert rec_forward == rec_backward


def test_a_higher_severity_finding_outranks_a_larger_deviation_at_lower_severity():
    warn_far = Finding(
        Severity.WARN, Category.CONSISTENCY, "page 2", "far but only WARN",
        code="FILL_RATIO_LOW", metric="fill_ratio", actual=0.0, threshold=0.4, page_index=1,
    )
    # No ERROR-severity actionable finding exists today, so this proves the
    # *mechanism* with a constructed fixture rather than real content —
    # exactly ADOS-M1.5 §21's carve-out for ranking criteria live content
    # cannot naturally exercise.
    error_close = Finding(
        Severity.ERROR, Category.STRUCTURAL, "page 1", "close but ERROR",
        code="FILL_RATIO_LOW", metric="fill_ratio", actual=0.39, threshold=0.4, page_index=0,
    )
    rec = select_recommendation([warn_far, error_close])
    assert rec.target_page == 0


def test_ties_break_on_finding_code_then_page_index():
    a = Finding(
        Severity.WARN, Category.CONSISTENCY, "page 2", "tie a",
        code="FILL_RATIO_LOW", metric="fill_ratio", actual=0.2, threshold=0.4, page_index=1,
    )
    b = Finding(
        Severity.WARN, Category.CONSISTENCY, "page 1", "tie b — identical severity and deviation",
        code="FILL_RATIO_LOW", metric="fill_ratio", actual=0.2, threshold=0.4, page_index=0,
    )
    # Same code, so the final tie-break is page_index — must be stable
    # regardless of which one is listed first.
    assert select_recommendation([a, b]).target_page == select_recommendation([b, a]).target_page == 0


def test_a_finding_with_no_capability_is_never_selected():
    unmapped = Finding(
        Severity.BLOCK, Category.STRUCTURAL, "page 1", "highest severity, but nothing can act on it",
        code="SOME_UNMAPPED_CODE", page_index=0,
    )
    actionable = _low(1, actual=0.10)
    rec = select_recommendation([unmapped, actionable])
    assert rec.finding_code == "FILL_RATIO_LOW"


def test_selecting_from_no_findings_at_all_raises_no_recommendation():
    with pytest.raises(NoRecommendationError):
        select_recommendation([])


def test_repeated_selection_over_identical_findings_is_identical():
    findings = [_low(0, actual=0.35), _low(1, actual=0.10)]
    assert select_recommendation(findings) == select_recommendation(findings)


# ---------------------------------------------------------------------------
# ADOS-M1.5 — iteration history / no-blind-repeats
# ---------------------------------------------------------------------------


def test_a_capability_with_a_recorded_no_improvement_is_excluded():
    finding = _low(4, actual=0.2678)
    capability = CAPABILITIES_BY_FINDING_CODE["FILL_RATIO_LOW"]
    history = (
        IterationHistoryEntry(
            finding_code="FILL_RATIO_LOW", target_page=4,
            command_type=capability.command_type, parameters=capability.parameters,
            outcome=IterationOutcome.NO_IMPROVEMENT,
        ),
    )
    with pytest.raises(NoRecommendationError):
        select_recommendation([finding], history=history)


def test_a_capability_with_a_recorded_failed_outcome_is_also_excluded():
    finding = _low(4, actual=0.2678)
    capability = CAPABILITIES_BY_FINDING_CODE["FILL_RATIO_LOW"]
    history = (
        IterationHistoryEntry(
            finding_code="FILL_RATIO_LOW", target_page=4,
            command_type=capability.command_type, parameters=capability.parameters,
            outcome=IterationOutcome.FAILED,
        ),
    )
    with pytest.raises(NoRecommendationError):
        select_recommendation([finding], history=history)


def test_a_recorded_improvement_does_not_block_the_same_capability():
    """History only excludes *ineffective* prior attempts — a capability
    that already helped is not something to hide from ranking (a second,
    still-underfull page with the same finding code must remain
    recommendable)."""
    finding = _low(4, actual=0.2678)
    capability = CAPABILITIES_BY_FINDING_CODE["FILL_RATIO_LOW"]
    history = (
        IterationHistoryEntry(
            finding_code="FILL_RATIO_LOW", target_page=4,
            command_type=capability.command_type, parameters=capability.parameters,
            outcome=IterationOutcome.IMPROVED_BUT_THRESHOLD_NOT_REACHED,
        ),
    )
    rec = select_recommendation([finding], history=history)
    assert rec.target_page == 4


def test_history_only_excludes_the_exact_same_page_and_parameters():
    """A no_improvement recorded against page 4 must not exclude the same
    finding code on a different page — history is keyed by the full
    (finding_code, target_page, command_type, parameters) tuple, not just
    the code."""
    finding_on_other_page = _low(6, actual=0.222)
    capability = CAPABILITIES_BY_FINDING_CODE["FILL_RATIO_LOW"]
    history = (
        IterationHistoryEntry(
            finding_code="FILL_RATIO_LOW", target_page=4,
            command_type=capability.command_type, parameters=capability.parameters,
            outcome=IterationOutcome.NO_IMPROVEMENT,
        ),
    )
    rec = select_recommendation([finding_on_other_page], history=history)
    assert rec.target_page == 6


def test_identical_history_produces_identical_recommendation():
    findings = [_low(0, actual=0.35), _low(1, actual=0.10)]
    capability = CAPABILITIES_BY_FINDING_CODE["FILL_RATIO_LOW"]
    history = (
        IterationHistoryEntry(
            finding_code="FILL_RATIO_LOW", target_page=1,
            command_type=capability.command_type, parameters=capability.parameters,
            outcome=IterationOutcome.NO_IMPROVEMENT,
        ),
    )
    rec_a = select_recommendation(findings, history=history)
    rec_b = select_recommendation(findings, history=history)
    assert rec_a == rec_b
    assert rec_a.target_page == 0  # page 1's only capability is now excluded


# ---------------------------------------------------------------------------
# ADOS-M1.5 — explain(): structured, deterministic WHY/WHAT/WHERE
# ---------------------------------------------------------------------------


def test_explain_is_structured_and_deterministic(base_plan, content, direction, studio_nord, fill_ratio_low_finding):
    recommendation = recommend(fill_ratio_low_finding)
    e1 = explain(fill_ratio_low_finding, recommendation)
    e2 = explain(fill_ratio_low_finding, recommendation)
    assert e1 == e2
    assert set(e1) == {"why", "what", "where", "expected_result"}
    assert e1["why"] == fill_ratio_low_finding.message
    assert "image-led" in e1["what"]
    assert e1["where"] == f"page {fill_ratio_low_finding.page_index + 1}"
    assert e1["expected_result"] == "increase fill_ratio"


# ---------------------------------------------------------------------------
# ADOS-M1.5 — scope safety is unchanged by multi-finding selection
# ---------------------------------------------------------------------------


def test_selecting_among_multiple_findings_still_only_ever_scopes_one_page(
    base_plan, content, direction, studio_nord
):
    """Ranking picks one finding; execution still goes through iterate()'s
    single-finding, single-scope path — multi-finding awareness must never
    broaden what one iteration is allowed to touch."""
    ev = evaluate(base_plan, direction, studio_nord.resolve_tokens())
    recommendation = select_recommendation(ev.report.findings)
    finding = next(
        f for f in ev.report.findings
        if f.code == recommendation.finding_code and f.page_index == recommendation.target_page
    )
    result = iterate(base_plan, finding, content, direction, studio_nord)
    assert result.diff.changed_pages == (recommendation.target_page,)
    for i, page in enumerate(base_plan.pages):
        if i != recommendation.target_page:
            assert result.plan.pages[i] == page
