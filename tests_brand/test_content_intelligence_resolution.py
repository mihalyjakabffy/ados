"""
ADOS-M3.2 — brand/llm/content/resolution.py.

The acceptance scenarios from the master prompt's §42, plus the
dedup/entity-resolution/missing-information mechanics that make them
work. Runs entirely against the deterministic RuleBasedContentExtractor
(no ANTHROPIC_API_KEY needed) — the same CI-determinism posture
ADOS-M3.1 established.
"""

from __future__ import annotations

import pytest

from brand.llm.content.observability import clear_content_traces
from brand.llm.content.resolution import resolve_content
from brand.llm.content.vocabulary import FactStatus
from brand.project.model import Project


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    clear_content_traces()


# ---------------------------------------------------------------------------
# Scenario A -- basic project
# ---------------------------------------------------------------------------


def test_scenario_a_basic_project():
    project = Project(name="Riverside", project_data={
        "program": "residential", "location": "Budapest",
    })
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "84 apartments. GFA of 13,100 m²."},
    ))
    facts = {f.key: f for f in content.facts}
    assert facts["program"].value == "residential"
    assert facts["location"].value == "Budapest"
    assert facts["apartments"].value == 84
    assert facts["gross_floor_area"].value == 13100
    assert all(f.source_refs for f in content.facts)
    # No unsupported claim was added for anything not stated.
    assert "client" not in facts
    assert "architect" not in facts


# ---------------------------------------------------------------------------
# Scenario B -- missing information
# ---------------------------------------------------------------------------


def test_scenario_b_missing_information_not_guessed():
    project = Project(name="Riverside")
    content = resolve_content(
        project, document_type_id="client-presentation",
        raw_documents=({"source_id": "brief", "text": "84 apartments."},),
    )
    missing_keys = {m.key for m in content.missing_information}
    # client-presentation's own metadata_requirements name real gaps here --
    # whatever they are, none of them were guessed into a Fact instead.
    for key in missing_keys:
        assert content.fact(key) is None
    assert content.fact("construction_cost") is None


# ---------------------------------------------------------------------------
# Scenario C -- conflict
# ---------------------------------------------------------------------------


def test_scenario_c_conflicting_sources_are_never_silently_resolved():
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief.pdf", "text": "GFA of 12,400 m²."},
        {"source_id": "deck.pdf", "text": "GFA of 13,100 m²."},
    ))
    gfa = content.fact("gross_floor_area")
    assert gfa.status is FactStatus.CONFLICTING
    assert gfa.value is None
    values = {cv.value for cv in gfa.conflicting_values}
    assert values == {12400.0, 13100.0}
    all_sources = {r.source_id for cv in gfa.conflicting_values for r in cv.source_refs}
    assert all_sources == {"brief.pdf", "deck.pdf"}


def test_scenario_c_agreeing_sources_merge_into_one_fact_not_five():
    """ADOS-M3.2 §15 -- the same information from multiple sources
    dedupes into one canonical fact with multiple supporting sources."""
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief.pdf", "text": "84 apartments."},
        {"source_id": "deck.pdf", "text": "84 apartments."},
    ))
    apartment_facts = [f for f in content.facts if f.key == "apartments"]
    assert len(apartment_facts) == 1
    assert len(apartment_facts[0].source_refs) == 2


# ---------------------------------------------------------------------------
# Scenario D -- fact vs claim
# ---------------------------------------------------------------------------


def test_scenario_d_fact_and_claim_are_kept_distinct():
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": (
            "The project contains 84 apartments. "
            "The project creates a strong connection to the landscape."
        )},
    ))
    assert content.fact("apartments").value == 84
    assert len(content.claims) == 1
    assert "connection to the landscape" in content.claims[0].text
    assert content.claims[0].status is FactStatus.INFERRED


# ---------------------------------------------------------------------------
# Scenario E -- unsupported inference
# ---------------------------------------------------------------------------


def test_scenario_e_no_unsupported_inference():
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "Residential development in Budapest."},
    ))
    keys = {f.key for f in content.facts}
    for forbidden in ("client", "structure", "architect", "completion_year", "budget"):
        assert forbidden not in keys


# ---------------------------------------------------------------------------
# Scenario F -- image
# ---------------------------------------------------------------------------


def test_scenario_f_image_asset_is_discoverable_without_fabricated_facts():
    project = Project(name="Riverside")
    from brand.project.model import Asset
    asset = Asset(filename="north-elevation.png", content_type="image/png", size_bytes=100, path="a.png")
    project = project.model_copy(update={"assets": (asset,)})

    content = resolve_content(project)
    assert len(content.assets) == 1
    asset_content = content.assets[0]
    assert asset_content.asset_id == asset.id
    assert asset_content.description == ""  # nothing fabricated from "visual appearance"
    assert asset_content.source_refs


# ---------------------------------------------------------------------------
# Scenario G -- user correction
# ---------------------------------------------------------------------------


def test_scenario_g_user_correction_supersedes_without_overwriting():
    project = Project(name="Riverside", project_data={"gross_floor_area": 12400})
    content = resolve_content(project, user_corrections=(
        {"key": "gross_floor_area", "value": 13100},
    ))
    all_gfa = [f for f in content.facts if f.key == "gross_floor_area"]
    assert len(all_gfa) == 2
    old = next(f for f in all_gfa if f.value == 12400)
    new = next(f for f in all_gfa if f.value == 13100)
    assert old.superseded_by == new.id
    assert new.superseded_by is None
    assert content.fact("gross_floor_area").value == 13100
    assert new.status is FactStatus.VERIFIED


# ---------------------------------------------------------------------------
# Entity resolution (ADOS-M3.2 §16) -- conservative, exact-match only
# ---------------------------------------------------------------------------


def test_entities_with_identical_names_merge_across_sources():
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "a", "text": "The project is located in Budapest."},
        {"source_id": "b", "text": "Also based in Budapest."},
    ))
    budapest_entities = [e for e in content.entities if e.name == "Budapest"]
    assert len(budapest_entities) == 1
    assert len(budapest_entities[0].source_refs) == 2


def test_entities_with_different_names_are_not_auto_merged():
    """ADOS-M3.2 §16 -- ambiguity must remain representable; a
    near-duplicate name is not silently merged without stronger evidence."""
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "a", "text": "Located in Budapest."},
        {"source_id": "b", "text": "Located in Vienna."},
    ))
    names = {e.name for e in content.entities}
    assert "Budapest" in names and "Vienna" in names


# ---------------------------------------------------------------------------
# Sources catalog
# ---------------------------------------------------------------------------


def test_sources_catalog_lists_distinct_contributing_sources():
    project = Project(name="Riverside", project_data={"client": "Acme"})
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "84 apartments."},
    ))
    source_ids = {s.source_id for s in content.sources}
    assert any("project-metadata" in s for s in source_ids)
    assert "brief" in source_ids
