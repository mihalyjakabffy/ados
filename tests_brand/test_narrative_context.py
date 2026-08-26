"""ADOS-M3.3 — brand/llm/narrative/context.py."""

from __future__ import annotations

from brand.llm.content.resolution import resolve_content
from brand.llm.narrative.context import (
    assemble_narrative_context,
    resolve_audience,
    resolve_objective_hint,
)
from brand.llm.narrative.vocabulary import Audience, NarrativeObjective
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.project.model import Project


def _intent(**explicit) -> SemanticIntent:
    return SemanticIntent(explicit=SemanticFieldValues(**explicit))


def test_resolve_audience_maps_free_text_to_the_closed_vocabulary():
    assert resolve_audience(_intent(audience="prospective_client")) == (Audience.CLIENT, "prospective_client")
    assert resolve_audience(_intent(audience="investor"))[0] is Audience.CLIENT
    assert resolve_audience(_intent(audience="competition_jury"))[0] is Audience.AUTHORITY
    assert resolve_audience(_intent(audience="architect"))[0] is Audience.PEER
    assert resolve_audience(_intent(audience="internal_team"))[0] is Audience.INTERNAL
    assert resolve_audience(_intent(audience="general_audience"))[0] is Audience.PUBLIC


def test_resolve_audience_defaults_to_public_when_unstated():
    audience, label = resolve_audience(SemanticIntent())
    assert audience is Audience.PUBLIC
    assert label == ""


def test_resolve_objective_hint_from_purpose_keywords():
    assert resolve_objective_hint(_intent(purpose="introduce_project")) is NarrativeObjective.INTRODUCE
    assert resolve_objective_hint(_intent(purpose="pitch to investors")) is NarrativeObjective.PERSUADE
    assert resolve_objective_hint(_intent(purpose="summarize progress")) is NarrativeObjective.SUMMARIZE


def test_resolve_objective_hint_from_action_when_no_purpose_keyword_matches():
    assert resolve_objective_hint(_intent(action="compare")) is NarrativeObjective.COMPARE
    assert resolve_objective_hint(_intent(action="summarize")) is NarrativeObjective.SUMMARIZE


def test_resolve_objective_hint_is_none_when_nothing_matches():
    assert resolve_objective_hint(SemanticIntent()) is None


def test_assemble_narrative_context_scopes_content_to_ids_and_summaries():
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "84 apartments. The project creates a strong connection to the landscape."},
    ))
    ctx = assemble_narrative_context(_intent(audience="client"), content, document_type_id="portfolio")

    assert ctx.project_id == project.id
    assert any(f["key"] == "apartments" for f in ctx.content_summary.facts)
    assert len(ctx.content_summary.claims) == 1
    assert ctx.document_type.id == "portfolio"
    assert "cover" in ctx.document_type.default_structure


def test_assemble_narrative_context_omits_superseded_facts():
    project = Project(name="Riverside", project_data={"gross_floor_area": 12400})
    content = resolve_content(project, user_corrections=({"key": "gross_floor_area", "value": 13100},))
    ctx = assemble_narrative_context(_intent(), content)
    gfa_rows = [f for f in ctx.content_summary.facts if f["key"] == "gross_floor_area"]
    assert len(gfa_rows) == 1
    assert gfa_rows[0]["value"] == 13100


def test_assemble_narrative_context_represents_conflicting_facts_without_a_single_value():
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "a.pdf", "text": "GFA of 12,400 m²."},
        {"source_id": "b.pdf", "text": "GFA of 13,100 m²."},
    ))
    ctx = assemble_narrative_context(_intent(), content)
    gfa_row = next(f for f in ctx.content_summary.facts if f["key"] == "gross_floor_area")
    assert gfa_row["status"] == "conflicting"
    assert "value" not in gfa_row
    assert {v["value"] for v in gfa_row["conflicting_values"]} == {12400.0, 13100.0}


def test_unknown_document_type_id_yields_empty_capabilities():
    project = Project(name="Riverside")
    content = resolve_content(project)
    ctx = assemble_narrative_context(_intent(), content, document_type_id="does-not-exist")
    assert ctx.document_type.id == ""
    assert ctx.document_type.default_structure == ()
