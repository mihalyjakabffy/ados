"""
ADOS-M3.2 — brand/llm/content/extraction.py.

Each extractor in isolation: StructuredDataExtractor and
ImageMetadataExtractor (deterministic, no LLM), RuleBasedContentExtractor
(deterministic fallback — what every CI run actually exercises), and
LLMContentExtractor's error contract (no live network call in this
suite; see test_content_intelligence_evaluation.py for the
provider-agnostic evaluation harness).
"""

from __future__ import annotations

import pytest

from brand.llm.content.extraction import (
    ContentExtractionContext,
    ContentSource,
    ImageMetadataExtractor,
    LLMContentExtractor,
    RuleBasedContentExtractor,
    StructuredDataExtractor,
    default_trust_level,
)
from brand.llm.content.vocabulary import FactStatus, SourceType
from brand.llm.provider import ProviderError

_CTX = ContentExtractionContext(project_name="Riverside")


def test_default_trust_level_ranks_user_statement_highest():
    assert default_trust_level(SourceType.USER_STATEMENT) < default_trust_level(SourceType.UPLOADED_DOCUMENT)
    assert default_trust_level(SourceType.ADOS_DOCUMENT) > default_trust_level(SourceType.STRUCTURED_PROJECT_DATA)
    assert default_trust_level(SourceType.LLM_INFERENCE) == max(
        default_trust_level(t) for t in SourceType
    )


def test_content_source_trust_level_defaults_by_type():
    src = ContentSource(source_id="s1", source_type=SourceType.USER_STATEMENT)
    assert src.trust_level == 0


def test_content_source_trust_level_override():
    src = ContentSource(source_id="s1", source_type=SourceType.USER_STATEMENT, explicit_trust_level=9)
    assert src.trust_level == 9


# ---------------------------------------------------------------------------
# StructuredDataExtractor
# ---------------------------------------------------------------------------


def test_structured_data_extractor_reads_project_metadata_as_verified():
    src = ContentSource(
        source_id="proj-meta", source_type=SourceType.PROJECT_METADATA,
        structured_payload={"client": "Acme Holdings", "empty_field": ""},
    )
    result, meta = StructuredDataExtractor().extract(src, _CTX)
    assert meta is None
    keys = {f.key: f for f in result.facts}
    assert keys["client"].value == "Acme Holdings"
    assert keys["client"].status == FactStatus.VERIFIED
    assert keys["client"].confidence == 1.0
    assert "empty_field" not in keys  # blank values are not facts


def test_structured_data_extractor_reads_content_item_metrics():
    src = ContentSource(
        source_id="items", source_type=SourceType.STRUCTURED_PROJECT_DATA,
        structured_payload={"content_items": [
            {"kind": "metric", "label": "GFA", "value": 13100, "unit": "m2"},
            {"kind": "text", "text": "ignored -- not fact/metric"},
        ]},
    )
    result, _ = StructuredDataExtractor().extract(src, _CTX)
    assert len(result.facts) == 1
    assert result.facts[0].key == "gfa"
    assert result.facts[0].unit == "m2"


def test_structured_data_extractor_rejects_wrong_source_type():
    src = ContentSource(source_id="x", source_type=SourceType.UPLOADED_IMAGE)
    with pytest.raises(ValueError):
        StructuredDataExtractor().extract(src, _CTX)


# ---------------------------------------------------------------------------
# ImageMetadataExtractor
# ---------------------------------------------------------------------------


def test_image_metadata_extractor_never_fabricates_beyond_given_metadata():
    src = ContentSource(
        source_id="asset-1", source_type=SourceType.UPLOADED_IMAGE, asset_id="asset-1",
        structured_payload={"caption": "North elevation"},
    )
    result, meta = ImageMetadataExtractor().extract(src, _CTX)
    assert meta is None
    asset = result.assets[0]
    assert asset.asset_id == "asset-1"
    assert asset.caption == "North elevation"
    assert asset.description == ""  # not given, not invented


# ---------------------------------------------------------------------------
# RuleBasedContentExtractor
# ---------------------------------------------------------------------------


def test_rule_based_extractor_finds_apartments_and_gfa():
    src = ContentSource(
        source_id="brief", source_type=SourceType.UPLOADED_DOCUMENT,
        text="Residential development in Budapest. 84 apartments. GFA of 13,100 m².",
    )
    result, meta = RuleBasedContentExtractor().extract(src, _CTX)
    assert meta is None
    facts = {f.key: f for f in result.facts}
    assert facts["apartments"].value == 84
    assert facts["gross_floor_area"].value == 13100
    assert facts["gross_floor_area"].unit == "m2"
    assert facts["location"].value == "Budapest"
    assert all(f.status == FactStatus.VERIFIED for f in result.facts)


def test_rule_based_extractor_finds_a_claim():
    src = ContentSource(
        source_id="brief", source_type=SourceType.UPLOADED_DOCUMENT,
        text="The project creates a strong connection between housing and landscape.",
    )
    result, _ = RuleBasedContentExtractor().extract(src, _CTX)
    assert len(result.claims) == 1
    assert result.claims[0].status == FactStatus.INFERRED


def test_rule_based_extractor_produces_nothing_for_unintelligible_text():
    src = ContentSource(source_id="x", source_type=SourceType.UPLOADED_DOCUMENT, text="asdkjaslkdj gibberish")
    result, _ = RuleBasedContentExtractor().extract(src, _CTX)
    assert result.facts == ()
    assert result.entities == ()
    assert result.claims == ()


def test_rule_based_extractor_does_not_double_match_gfa():
    src = ContentSource(
        source_id="x", source_type=SourceType.UPLOADED_DOCUMENT, text="GFA of 13,100 m².",
    )
    result, _ = RuleBasedContentExtractor().extract(src, _CTX)
    gfa_facts = [f for f in result.facts if f.key == "gross_floor_area"]
    assert len(gfa_facts) == 1


def test_rule_based_extractor_every_fact_has_provenance():
    src = ContentSource(
        source_id="brief", source_type=SourceType.UPLOADED_DOCUMENT,
        text="84 apartments in Budapest.",
    )
    result, _ = RuleBasedContentExtractor().extract(src, _CTX)
    for fact in result.facts:
        assert len(fact.source_refs) >= 1
        assert fact.source_refs[0].source_id == "brief"


# ---------------------------------------------------------------------------
# LLMContentExtractor -- error contract only (no live network call)
# ---------------------------------------------------------------------------


def test_llm_content_extractor_raises_provider_error_without_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    src = ContentSource(source_id="brief", source_type=SourceType.UPLOADED_DOCUMENT, text="84 apartments.")
    with pytest.raises(ProviderError):
        LLMContentExtractor().extract(src, _CTX)


def test_llm_content_extractor_default_model_is_opus_5(monkeypatch):
    monkeypatch.delenv("CONTENT_INTELLIGENCE_MODEL", raising=False)
    assert LLMContentExtractor()._model == "claude-opus-5"
