"""ADOS-M3.6 — brand/llm/loop/recommend.py."""

from __future__ import annotations

from brand.llm.loop.fingerprint import finding_fingerprint, recommendation_fingerprint
from brand.llm.loop.recommend import CAPABILITIES_BY_CODE, select_recommendation
from brand.llm.loop.vocabulary import RecommendationSource, SkippedRecommendationReason
from brand.validation.brand_validator import Category, Finding, Severity


def _finding(code="FILL_RATIO_LOW", severity=Severity.ERROR, field="page 1", metric="fill_ratio") -> Finding:
    return Finding(severity, Category.STRUCTURAL, field, "message", code=code, metric=metric)


def test_fill_ratio_low_maps_to_image_led():
    rec, skipped = select_recommendation((_finding("FILL_RATIO_LOW"),))
    assert rec is not None
    assert rec.patch.target == "composition_strategy"
    assert rec.patch.value == "image_led"
    assert rec.source is RecommendationSource.DETERMINISTIC
    assert rec.confidence == 1.0
    assert skipped == ()


def test_fill_ratio_high_maps_to_low_density():
    rec, _ = select_recommendation((_finding("FILL_RATIO_HIGH"),))
    assert rec is not None
    assert rec.patch.target == "density"
    assert rec.patch.value == "low"


def test_brand_conflict_maps_to_restrained_typography():
    rec, _ = select_recommendation((_finding("DESIGN_ISSUE_BRAND_CONFLICT", severity=Severity.WARN, metric=""),))
    assert rec is not None
    assert rec.patch.target == "typography_hierarchy"
    assert rec.patch.value == "restrained"


def test_uncoded_finding_is_skipped_as_unsupported_scope():
    f = Finding(Severity.ERROR, Category.STRUCTURAL, "page 1 · Text", "off lattice")
    rec, skipped = select_recommendation((f,))
    assert rec is None
    assert skipped[0].reason is SkippedRecommendationReason.UNSUPPORTED_SCOPE


def test_asset_scarcity_has_no_capability_and_is_skipped():
    f = _finding("DESIGN_ISSUE_ASSET_SCARCITY", severity=Severity.WARN, metric="")
    assert f.code not in CAPABILITIES_BY_CODE
    rec, skipped = select_recommendation((f,))
    assert rec is None
    assert skipped[0].reason is SkippedRecommendationReason.NO_SAFE_COMMAND_EXISTS


def test_info_severity_findings_are_never_actionable():
    f = _finding("FILL_RATIO_LOW", severity=Severity.INFO)
    rec, skipped = select_recommendation((f,))
    assert rec is None
    assert skipped == ()


def test_higher_severity_finding_is_selected_first():
    error_f = _finding("FILL_RATIO_LOW", severity=Severity.ERROR)
    warn_f = _finding("DESIGN_ISSUE_BRAND_CONFLICT", severity=Severity.WARN, metric="")
    rec, _ = select_recommendation((warn_f, error_f))
    assert rec.patch.target == "composition_strategy"


def test_already_tried_recommendation_is_skipped():
    f = _finding("FILL_RATIO_LOW")
    fp = finding_fingerprint(f)
    from brand.llm.loop.model import DesignIntentPatch

    rec_fp = recommendation_fingerprint(fp, DesignIntentPatch(target="composition_strategy", value="image_led"))
    rec, skipped = select_recommendation((f,), tried_recommendation_fingerprints=frozenset({rec_fp}))
    assert rec is None
    assert any(s.reason is SkippedRecommendationReason.ALREADY_ATTEMPTED for s in skipped)


def test_no_recommendation_and_no_findings_returns_empty():
    rec, skipped = select_recommendation(())
    assert rec is None
    assert skipped == ()


def test_llm_propose_is_only_called_for_the_top_uncapable_finding():
    calls = []

    def fake_propose(finding):
        calls.append(finding.code)
        return None, None

    f1 = _finding("DESIGN_ISSUE_ASSET_SCARCITY", severity=Severity.WARN, metric="")
    f2 = _finding("DESIGN_ISSUE_CONTRADICTORY_DENSITY", severity=Severity.WARN, metric="")
    select_recommendation((f1, f2), llm_propose=fake_propose)
    assert calls == ["DESIGN_ISSUE_ASSET_SCARCITY"]
