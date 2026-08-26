"""ADOS-M3.6 — brand/llm/loop/fingerprint.py."""

from __future__ import annotations

from brand.llm.design.model import DesignIntent
from brand.llm.design.vocabulary import CompositionStrategy, TextDensity
from brand.llm.loop.fingerprint import (
    design_intent_fingerprint,
    finding_fingerprint,
    recommendation_fingerprint,
)
from brand.llm.loop.model import DesignIntentPatch
from brand.validation.brand_validator import Category, Finding, Severity


def _di(**overrides) -> DesignIntent:
    defaults = dict(project_id="p1", composition_strategy=CompositionStrategy.IMAGE_LED, density=TextDensity.MEDIUM)
    defaults.update(overrides)
    return DesignIntent(**defaults)


def test_design_intent_fingerprint_ignores_id_and_created_at():
    a = _di()
    b = _di()
    assert a.id != b.id
    assert design_intent_fingerprint(a) == design_intent_fingerprint(b)


def test_design_intent_fingerprint_changes_with_composition_strategy():
    a = _di(composition_strategy=CompositionStrategy.IMAGE_LED)
    b = _di(composition_strategy=CompositionStrategy.TEXT_LED)
    assert design_intent_fingerprint(a) != design_intent_fingerprint(b)


def test_finding_fingerprint_ignores_page_index_and_message():
    f1 = Finding(Severity.ERROR, Category.STRUCTURAL, "page 1", "fill ratio low here", code="FILL_RATIO_LOW", metric="fill_ratio", page_index=0)
    f2 = Finding(Severity.ERROR, Category.STRUCTURAL, "page 4", "a completely different message", code="FILL_RATIO_LOW", metric="fill_ratio", page_index=3)
    assert finding_fingerprint(f1) == finding_fingerprint(f2)


def test_finding_fingerprint_differs_by_code():
    f1 = Finding(Severity.ERROR, Category.STRUCTURAL, "page 1", "x", code="FILL_RATIO_LOW", metric="fill_ratio")
    f2 = Finding(Severity.ERROR, Category.STRUCTURAL, "page 1", "x", code="FILL_RATIO_HIGH", metric="fill_ratio")
    assert finding_fingerprint(f1) != finding_fingerprint(f2)


def test_uncoded_findings_fingerprint_by_field():
    f1 = Finding(Severity.ERROR, Category.STRUCTURAL, "page 1 · Text", "off lattice")
    f2 = Finding(Severity.ERROR, Category.STRUCTURAL, "page 2 · Text", "off lattice")
    assert finding_fingerprint(f1) != finding_fingerprint(f2)


def test_uncoded_findings_sharing_a_field_but_different_category_or_message_do_not_collide():
    """Regression test for a real bug caught by the M3.6 live browser
    smoke test: brand.creative.evaluate.evaluate() raises more than one
    document-level, codeless finding under the identical field="plan"
    (its own pacing-match and rejected-candidate checks) — these are
    genuinely different findings and must never fingerprint the same,
    or a UI list keyed by fingerprint silently drops one."""
    f1 = Finding(Severity.INFO, Category.CONSISTENCY, "plan", "1 of 5 pacing positions matched")
    f2 = Finding(Severity.INFO, Category.STRUCTURAL, "plan", "no rejected candidates were recorded")
    assert finding_fingerprint(f1) != finding_fingerprint(f2)


def test_recommendation_fingerprint_is_deterministic():
    patch = DesignIntentPatch(target="density", value="low")
    assert recommendation_fingerprint("fp1", patch) == recommendation_fingerprint("fp1", patch)


def test_recommendation_fingerprint_differs_by_value():
    p1 = DesignIntentPatch(target="density", value="low")
    p2 = DesignIntentPatch(target="density", value="high")
    assert recommendation_fingerprint("fp1", p1) != recommendation_fingerprint("fp1", p2)
