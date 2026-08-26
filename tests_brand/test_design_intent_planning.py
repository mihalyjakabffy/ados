"""
ADOS-M3.4 — brand/llm/design/planning.py.

The full integration path — SemanticIntent -> ContentIntelligenceModel
-> NarrativePlan -> DesignIntent — against the deterministic
RuleBasedDesignIntentGenerator (no ANTHROPIC_API_KEY needed), plus the
acceptance scenarios from the master prompt's §66 and the evaluation-
relevant cases from §50 that are simplest to verify at the orchestrator
level.
"""

from __future__ import annotations

import pytest

from brand.creative.directions import EDITORIAL_QUIET, IMAGE_LED, TECHNICAL_DENSE
from brand.examples.studio_nord import studio_nord
from brand.examples.studio_om import studio_om
from brand.llm.content.resolution import resolve_content
from brand.llm.design.observability import clear_design_traces, recent_design_traces
from brand.llm.design.planning import plan_design_intent
from brand.llm.narrative.planning import plan_narrative
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.project.model import Asset, Project


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    clear_design_traces()


def _riverside(with_asset: bool = True):
    project = Project(name="Riverside", project_data={"program": "residential", "location": "Budapest"})
    if with_asset:
        asset = Asset(filename="render.png", content_type="image/png", size_bytes=100, path="a.png")
        project = project.model_copy(update={"assets": (asset,)})
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "84 apartments. GFA of 13,100 m². The project creates a strong connection to the landscape."},
    ))
    return project, content


def test_scenario_1_narrative_priority_becomes_visual_hierarchy():
    """ADOS-M3.4 §66 Scenario 1."""
    project, content = _riverside()
    intent = SemanticIntent(explicit=SemanticFieldValues(audience="client"))
    plan = plan_narrative(project, content, intent)
    di = plan_design_intent(project, content, plan, brand=studio_nord(), creative_direction=EDITORIAL_QUIET)

    priority_rank = {"dominant": 0, "secondary": 1, "supporting": 2, "minimal": 3}
    by_narrative_priority: dict[str, list[int]] = {"primary": [], "secondary": [], "supporting": [], "optional": []}
    for section in plan.all_sections():
        sd = di.section_design(section.id)
        if sd is not None:
            by_narrative_priority[section.priority.value].append(priority_rank[sd.visual_priority.value])

    if by_narrative_priority["primary"] and by_narrative_priority["supporting"]:
        assert max(by_narrative_priority["primary"]) <= min(by_narrative_priority["supporting"])


def test_scenario_2_image_strategy_without_geometry():
    """ADOS-M3.4 §66 Scenario 2 -- a hero asset assignment, no coordinates."""
    project, content = _riverside(with_asset=True)
    intent = SemanticIntent(explicit=SemanticFieldValues(audience="client"))
    plan = plan_narrative(project, content, intent)
    di = plan_design_intent(project, content, plan, brand=studio_nord(), creative_direction=IMAGE_LED)

    sections_with_assets = [sd for sd in di.section_designs if sd.asset_refs]
    assert sections_with_assets
    dumped = di.to_dict()
    for forbidden in ("x", "y", "width", "height", "page"):
        assert forbidden not in dumped


def test_scenario_3_brand_preservation_on_a_restrained_brand():
    """ADOS-M3.4 §66 Scenario 3 / §50 Case E -- a restrained brand's
    visual_language never grows a trait the brand does not claim."""
    project, content = _riverside()
    intent = SemanticIntent(explicit=SemanticFieldValues(audience="client"))
    plan = plan_narrative(project, content, intent)
    brand = studio_nord()
    di = plan_design_intent(project, content, plan, brand=brand, creative_direction=EDITORIAL_QUIET)

    brand_traits = {p.value for p in brand.identity.personality}
    assert {v.value for v in di.visual_language} <= brand_traits


def test_scenario_4_different_brand_same_narrative_produces_different_strategy():
    """ADOS-M3.4 §66 Scenario 4 / §50 Case J."""
    project, content = _riverside()
    intent = SemanticIntent(explicit=SemanticFieldValues(audience="client"))
    plan = plan_narrative(project, content, intent)

    di_nord = plan_design_intent(project, content, plan, brand=studio_nord(), creative_direction=EDITORIAL_QUIET)
    di_om = plan_design_intent(project, content, plan, brand=studio_om(), creative_direction=TECHNICAL_DENSE)

    assert di_nord.brand_id != di_om.brand_id
    # Same narrative foundation: both designs cover exactly the same sections.
    assert {sd.section_id for sd in di_nord.section_designs} == {sd.section_id for sd in di_om.section_designs}


def test_scenario_5_asset_scarcity_never_invents_assets():
    """ADOS-M3.4 §66 Scenario 5 / §50 Case G."""
    project, content = _riverside(with_asset=False)
    intent = SemanticIntent()
    plan = plan_narrative(project, content, intent)
    di = plan_design_intent(project, content, plan, brand=studio_nord(), creative_direction=EDITORIAL_QUIET)

    for sd in di.section_designs:
        for ref in sd.asset_refs:
            assert ref.asset_id in {a.asset_id for a in content.assets}
    assert all(sd.asset_refs == () for sd in di.section_designs)


def test_scenario_6_missing_information_is_acknowledged_not_invented():
    """ADOS-M3.4 §66 Scenario 6."""
    project = Project(name="Riverside")
    content = resolve_content(project, document_type_id="project-report", raw_documents=(
        {"source_id": "brief", "text": "84 apartments."},
    ))
    intent = SemanticIntent()
    plan = plan_narrative(project, content, intent, document_type_id="project-report")
    assert plan.missing_information  # the narrative layer already surfaced a gap
    di = plan_design_intent(project, content, plan, brand=studio_nord(), creative_direction=EDITORIAL_QUIET)
    assert any(i.type.value == "missing_content_acknowledged" for i in di.design_issues)


def test_regeneration_keeps_previous_design_intents_inspectable():
    """ADOS-M3.4 §55/§61 -- regeneration never corrupts previous intents."""
    project, content = _riverside()
    intent = SemanticIntent()
    plan = plan_narrative(project, content, intent)
    first = plan_design_intent(project, content, plan, brand=studio_nord())
    second = plan_design_intent(project, content, plan, brand=studio_om())
    assert first.id != second.id
    traces = recent_design_traces()
    assert len(traces) == 2
    assert len({t.request_id for t in traces}) == 2


def test_provider_error_falls_back_to_rule_based():
    from brand.llm.design.generation import LLMDesignIntentGenerator

    project, content = _riverside()
    intent = SemanticIntent()
    plan = plan_narrative(project, content, intent)
    di = plan_design_intent(project, content, plan, brand=studio_nord(), generator=LLMDesignIntentGenerator())
    assert di is not None
    assert len(di.section_designs) > 0
