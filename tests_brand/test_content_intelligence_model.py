"""
ADOS-M3.2 — brand/llm/content/model.py.

The domain model's own invariants: the hallucination guard (a
truth-bearing status requires provenance), the conflicting-fact shape
(no single value, at least two distinct alternatives), and JSON
round-tripping.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from brand.llm.content.model import (
    SCHEMA_VERSION,
    AssetContent,
    Claim,
    ConflictingValue,
    ContentIntelligenceModel,
    Entity,
    Fact,
    MissingInformation,
    Relationship,
    SourceReference,
)
from brand.llm.content.vocabulary import EntityType, FactStatus, SourceType

_REF = SourceReference(source_id="s1", source_type=SourceType.PROJECT_METADATA, extraction_method="structured_data")


def test_fact_with_truth_bearing_status_requires_source_refs():
    with pytest.raises(ValidationError, match="no source_refs"):
        Fact(key="apartments", value=84, status=FactStatus.VERIFIED)


def test_claim_with_truth_bearing_status_requires_source_refs():
    with pytest.raises(ValidationError, match="no source_refs"):
        Claim(text="A strong connection to the landscape.", status=FactStatus.INFERRED)


def test_entity_with_truth_bearing_status_requires_source_refs():
    with pytest.raises(ValidationError, match="no source_refs"):
        Entity(type=EntityType.PROJECT, name="Riverside", status=FactStatus.VERIFIED)


def test_relationship_with_truth_bearing_status_requires_source_refs():
    with pytest.raises(ValidationError, match="no source_refs"):
        Relationship(subject_entity_id="a", predicate="located_in", object_entity_id="b", status=FactStatus.VERIFIED)


def test_valid_fact_with_source_refs_constructs():
    fact = Fact(key="apartments", value=84, status=FactStatus.VERIFIED, source_refs=(_REF,))
    assert fact.value == 84
    assert fact.is_metric


def test_string_fact_is_not_a_metric():
    fact = Fact(key="program", value="residential", status=FactStatus.VERIFIED, source_refs=(_REF,))
    assert not fact.is_metric


def test_conflicting_fact_has_no_single_value():
    cv1 = ConflictingValue(value=12400, unit="m2", source_refs=(_REF,))
    cv2 = ConflictingValue(value=13100, unit="m2", source_refs=(_REF,))
    fact = Fact(key="gfa", status=FactStatus.CONFLICTING, conflicting_values=(cv1, cv2), source_refs=(_REF,))
    assert fact.value is None
    assert len(fact.conflicting_values) == 2


def test_conflicting_fact_cannot_also_carry_a_value():
    cv1 = ConflictingValue(value=12400, unit="m2", source_refs=(_REF,))
    cv2 = ConflictingValue(value=13100, unit="m2", source_refs=(_REF,))
    with pytest.raises(ValidationError, match="no single value"):
        Fact(key="gfa", value=12400, status=FactStatus.CONFLICTING, conflicting_values=(cv1, cv2), source_refs=(_REF,))


def test_conflicting_fact_needs_at_least_two_distinct_values():
    cv1 = ConflictingValue(value=12400, unit="m2", source_refs=(_REF,))
    with pytest.raises(ValidationError, match="fewer than two"):
        Fact(key="gfa", status=FactStatus.CONFLICTING, conflicting_values=(cv1,), source_refs=(_REF,))


def test_non_conflicting_fact_cannot_carry_conflicting_values():
    cv1 = ConflictingValue(value=12400, unit="m2", source_refs=(_REF,))
    cv2 = ConflictingValue(value=13100, unit="m2", source_refs=(_REF,))
    with pytest.raises(ValidationError, match="not conflicting"):
        Fact(key="gfa", value=12400, status=FactStatus.VERIFIED, conflicting_values=(cv1, cv2), source_refs=(_REF,))


def test_content_intelligence_model_round_trips_through_json():
    fact = Fact(key="apartments", value=84, status=FactStatus.VERIFIED, source_refs=(_REF,))
    entity = Entity(type=EntityType.PROJECT, name="Riverside", status=FactStatus.VERIFIED, source_refs=(_REF,))
    cm = ContentIntelligenceModel(project_id="p1", entities=(entity,), facts=(fact,), sources=(_REF,))
    payload = json.loads(json.dumps(cm.to_dict()))
    rebuilt = ContentIntelligenceModel.model_validate(payload)
    assert rebuilt.project_id == cm.project_id
    assert rebuilt.facts[0].key == "apartments"
    assert payload["schema_version"] == SCHEMA_VERSION


def test_metrics_property_filters_numeric_facts_only():
    numeric = Fact(key="apartments", value=84, status=FactStatus.VERIFIED, source_refs=(_REF,))
    stringy = Fact(key="program", value="residential", status=FactStatus.VERIFIED, source_refs=(_REF,))
    cm = ContentIntelligenceModel(project_id="p1", facts=(numeric, stringy))
    assert [f.key for f in cm.metrics] == ["apartments"]


def test_fact_lookup_skips_superseded_facts():
    old = Fact(key="gfa", value=12400, status=FactStatus.VERIFIED, source_refs=(_REF,), superseded_by="new-id")
    new = Fact(id="new-id", key="gfa", value=13100, status=FactStatus.VERIFIED, source_refs=(_REF,))
    cm = ContentIntelligenceModel(project_id="p1", facts=(old, new))
    current = cm.fact("gfa")
    assert current is not None
    assert current.value == 13100


def test_missing_information_is_a_distinct_shape_from_a_fact():
    gap = MissingInformation(key="construction_cost", required_for="client_presentation", reason="no source")
    assert gap.key == "construction_cost"
    # MissingInformation has no `value` field at all -- there is nothing
    # to accidentally read as a guessed answer.
    assert not hasattr(gap, "value")


def test_asset_content_does_not_duplicate_real_asset_fields():
    asset = AssetContent(asset_id="a1", caption="North elevation")
    # No filename/content_type/width_px/height_px on this model at all --
    # those already live on brand.project.model.Asset.
    for forbidden_field in ("filename", "content_type", "width_px", "height_px"):
        assert not hasattr(asset, forbidden_field)


def test_models_are_frozen():
    fact = Fact(key="apartments", value=84, status=FactStatus.VERIFIED, source_refs=(_REF,))
    with pytest.raises(ValidationError):
        fact.value = 90  # type: ignore[misc]


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        Fact.model_validate({"key": "x", "value": 1, "status": "verified", "source_refs": [], "bogus": True})
