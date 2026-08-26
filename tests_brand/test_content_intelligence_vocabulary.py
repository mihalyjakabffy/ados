"""ADOS-M3.2 — brand/llm/content/vocabulary.py."""

from __future__ import annotations

from brand.llm.content.vocabulary import TRUTH_BEARING_STATUSES, EntityType, FactStatus, SourceType


def test_entity_type_matches_ados_m3_2():
    assert {t.value for t in EntityType} == {
        "project", "building", "site", "client", "architect", "organization",
        "location", "person", "material", "space", "program", "phase",
    }


def test_source_type_matches_ados_m3_2():
    assert {t.value for t in SourceType} == {
        "project_state", "project_metadata", "structured_project_data",
        "uploaded_document", "uploaded_image", "ados_document", "brand_context",
        "design_state", "user_statement", "llm_inference",
    }


def test_fact_status_matches_ados_m3_2():
    assert {s.value for s in FactStatus} == {"verified", "inferred", "ambiguous", "missing", "conflicting"}


def test_missing_is_not_truth_bearing():
    assert FactStatus.MISSING not in TRUTH_BEARING_STATUSES


def test_verified_inferred_ambiguous_conflicting_are_truth_bearing():
    for status in (FactStatus.VERIFIED, FactStatus.INFERRED, FactStatus.AMBIGUOUS, FactStatus.CONFLICTING):
        assert status in TRUTH_BEARING_STATUSES
