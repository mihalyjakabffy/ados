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
from brand.creative.iterate import (
    IterationNoImprovementError,
    NoRecommendationError,
    Recommendation,
    iterate,
    recommend,
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
