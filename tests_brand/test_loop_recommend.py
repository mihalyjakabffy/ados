"""ADOS-M3.6 — brand/llm/loop/recommend.py."""

from __future__ import annotations

import pytest

from brand.llm.loop.fingerprint import finding_fingerprint, recommendation_fingerprint
from brand.llm.loop.recommend import CAPABILITIES_BY_CODE, make_llm_proposer, select_recommendation
from brand.llm.loop.vocabulary import RecommendationSource, SkippedRecommendationReason
from brand.llm.provider import ProviderMetadata
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


# ---------------------------------------------------------------------------
# ADOS-M3.6 production hardening — adversarial coverage of the one real LLM
# boundary this package has (make_llm_proposer's ``propose`` closure). These
# stub out the network call (``claude_provider.call_structured``) to return
# hallucinated/malicious output shapes and assert the closed-vocabulary
# validation actually rejects them — never previously exercised directly
# (only ``select_recommendation``'s dispatch around a *fake* propose was
# tested, not this module's own validation of a real provider response).
# ---------------------------------------------------------------------------


class _FakeRaw:
    def __init__(self, target=None, value=None, rationale=""):
        self.target = target
        self.value = value
        self.rationale = rationale


def _fake_metadata():
    return ProviderMetadata(provider="claude", model="claude-opus-5", latency_ms=1.0)


def _patch_provider(monkeypatch, raw):
    import brand.llm.providers.claude_provider as claude_provider

    monkeypatch.setattr(claude_provider, "get_client", lambda: object())
    monkeypatch.setattr(
        claude_provider, "call_structured",
        lambda client, **kwargs: (raw, _fake_metadata()),
    )


def test_llm_proposer_drops_hallucinated_target_field(monkeypatch):
    """The LLM claims a patch target this package never exposed (e.g. an
    attempt to name something outside PATCHABLE_FIELDS, such as a
    made-up 'execute_command' or 'brand_id' field) — must be dropped,
    never materialized into a Recommendation."""
    _patch_provider(monkeypatch, _FakeRaw(target="execute_raw_command", value="anything", rationale="ignore all rules"))
    propose = make_llm_proposer()
    rec, metadata = propose(_finding("FILL_RATIO_LOW"))
    assert rec is None
    assert metadata is not None


def test_llm_proposer_drops_hallucinated_enum_value(monkeypatch):
    """A real patchable field but a value outside its closed enum
    (hallucinated or injected) must be dropped, not coerced or passed
    through as a free-text patch value."""
    _patch_provider(monkeypatch, _FakeRaw(target="density", value="maximum_overdrive", rationale="x"))
    propose = make_llm_proposer()
    rec, metadata = propose(_finding("FILL_RATIO_LOW"))
    assert rec is None
    assert metadata is not None


def test_llm_proposer_drops_empty_target_and_value(monkeypatch):
    """A refusal-shaped or empty response (both fields blank/None) must
    be treated as "no proposal", never as a patch with empty strings."""
    _patch_provider(monkeypatch, _FakeRaw(target=None, value=None, rationale=""))
    propose = make_llm_proposer()
    rec, metadata = propose(_finding("FILL_RATIO_LOW"))
    assert rec is None


def test_llm_proposer_accepts_a_real_closed_vocabulary_choice(monkeypatch):
    """Control case: a well-formed, real target+value pair from the
    provider is the one path that actually produces a Recommendation —
    proving the rejections above are about validation, not a broken
    happy path."""
    _patch_provider(monkeypatch, _FakeRaw(target="density", value="low", rationale="reduce text load"))
    propose = make_llm_proposer()
    rec, metadata = propose(_finding("FILL_RATIO_LOW"))
    assert rec is not None
    assert rec.patch.target == "density"
    assert rec.patch.value == "low"
    assert rec.source is RecommendationSource.LLM
