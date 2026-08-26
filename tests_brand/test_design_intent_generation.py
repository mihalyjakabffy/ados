"""
ADOS-M3.4 — brand/llm/design/generation.py.

RuleBasedDesignIntentGenerator's own shape, LLMDesignIntentGenerator's
error contract (no live network call in this suite), and the
structural anti-hallucination mechanism: an invented section id, asset
id, or brand token must never survive materialization, and every real
narrative section must end up covered.
"""

from __future__ import annotations

import pytest

from brand.creative.directions import EDITORIAL_QUIET
from brand.examples.studio_nord import studio_nord
from brand.llm.content.resolution import resolve_content
from brand.llm.design.context import assemble_design_context
from brand.llm.design.generation import (
    LLMDesignIntentGenerator,
    RawAssetRef,
    RawDesignIntent,
    RawSectionDesign,
    RuleBasedDesignIntentGenerator,
    _materialize,
)
from brand.llm.design.vocabulary import PersonalityAxis
from brand.llm.narrative.planning import plan_narrative
from brand.llm.provider import ProviderError
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.project.model import Asset, Project


def _context(with_brand: bool = True, with_asset: bool = True):
    project = Project(name="Riverside")
    if with_asset:
        asset = Asset(filename="render.png", content_type="image/png", size_bytes=100, path="a.png")
        project = project.model_copy(update={"assets": (asset,)})
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "84 apartments. GFA of 13,100 m². The project creates a strong connection to the landscape."},
    ))
    intent = SemanticIntent(explicit=SemanticFieldValues(audience="prospective_client", purpose="introduce_project"))
    plan = plan_narrative(project, content, intent, document_type_id="portfolio")
    brand = studio_nord() if with_brand else None
    return assemble_design_context(plan, content, brand=brand, creative_direction=EDITORIAL_QUIET, project_name=project.name)


def test_rule_based_generator_produces_a_design_with_no_network_call():
    ctx = _context()
    di, metadata = RuleBasedDesignIntentGenerator().generate(ctx)
    assert metadata is None
    assert len(di.section_designs) == len(ctx.narrative_sections)
    assert di.excluded_sections == ()


def test_rule_based_generator_covers_every_real_section():
    ctx = _context()
    di, _ = RuleBasedDesignIntentGenerator().generate(ctx)
    covered = {sd.section_id for sd in di.section_designs} | {ex.section_id for ex in di.excluded_sections}
    assert covered == {s["id"] for s in ctx.narrative_sections}


def test_rule_based_generator_flags_asset_scarcity_without_assets():
    ctx = _context(with_asset=False)
    di, _ = RuleBasedDesignIntentGenerator().generate(ctx)
    assert any(i.type.value == "asset_scarcity" for i in di.design_issues)
    for sd in di.section_designs:
        assert sd.asset_refs == ()


def test_rule_based_generator_reads_real_brand_personality():
    ctx = _context(with_brand=True)
    di, _ = RuleBasedDesignIntentGenerator().generate(ctx)
    assert set(v.value for v in di.visual_language) <= set(ctx.brand.personality)
    assert di.visual_language != ()


def test_rule_based_generator_produces_nothing_without_a_brand():
    ctx = _context(with_brand=False)
    di, _ = RuleBasedDesignIntentGenerator().generate(ctx)
    assert di.visual_language == ()
    assert di.brand_id is None


def test_llm_generator_raises_provider_error_without_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(ProviderError):
        LLMDesignIntentGenerator().generate(_context())


def test_llm_generator_default_model_is_opus_5(monkeypatch):
    monkeypatch.delenv("DESIGN_INTENT_MODEL", raising=False)
    assert LLMDesignIntentGenerator()._model == "claude-opus-5"


# ---------------------------------------------------------------------------
# _materialize -- the structural anti-hallucination mechanism
# ---------------------------------------------------------------------------


def test_materialize_drops_invented_section_and_covers_the_real_ones():
    ctx = _context()
    real_id = ctx.narrative_sections[0]["id"]
    raw = RawDesignIntent(
        composition_strategy="image led",
        section_designs=(RawSectionDesign(section_id=real_id, visual_role=("hero",)),
                          RawSectionDesign(section_id="invented-section", visual_role=("hero",))),
    )
    di = _materialize(raw, ctx)
    assert [sd.section_id for sd in di.section_designs] == [real_id]
    covered = {sd.section_id for sd in di.section_designs} | {ex.section_id for ex in di.excluded_sections}
    assert covered == {s["id"] for s in ctx.narrative_sections}


def test_materialize_drops_invented_asset_reference():
    ctx = _context()
    real_id = ctx.narrative_sections[0]["id"]
    raw = RawDesignIntent(section_designs=(RawSectionDesign(
        section_id=real_id, visual_role=("hero",),
        asset_refs=(RawAssetRef(asset_id="invented-asset-999"),),
    ),))
    di = _materialize(raw, ctx)
    assert di.section_designs[0].asset_refs == ()


def test_materialize_drops_unrecognised_brand_typography_role():
    ctx = _context(with_brand=True)
    real_id = ctx.narrative_sections[0]["id"]
    raw = RawDesignIntent(section_designs=(RawSectionDesign(
        section_id=real_id, visual_role=("hero",), heading_role="not-a-real-role", body_role="body",
    ),))
    di = _materialize(raw, ctx)
    assert di.section_designs[0].heading_role is None
    assert di.section_designs[0].body_role == "body"


def test_materialize_drops_visual_language_the_brand_does_not_claim():
    ctx = _context(with_brand=True)
    real_id = ctx.narrative_sections[0]["id"]
    raw = RawDesignIntent(
        visual_language=("editorial", "playful"),  # brand does not claim "playful"
        section_designs=(RawSectionDesign(section_id=real_id, visual_role=("hero",)),),
    )
    di = _materialize(raw, ctx)
    assert PersonalityAxis.PLAYFUL not in di.visual_language
    assert PersonalityAxis.EDITORIAL in di.visual_language


def test_materialize_normalizes_spaced_and_hyphenated_tokens():
    ctx = _context()
    real_id = ctx.narrative_sections[0]["id"]
    raw = RawDesignIntent(
        composition_strategy="image-led",
        section_designs=(RawSectionDesign(section_id=real_id, visual_role=("hero",), composition_mode="text led"),),
    )
    di = _materialize(raw, ctx)
    assert di.composition_strategy.value == "image_led"
    assert di.section_designs[0].composition_mode.value == "text_led"
