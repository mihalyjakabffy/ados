"""ADOS-M3.4 — brand/llm/design/context.py."""

from __future__ import annotations

from brand.creative.directions import EDITORIAL_QUIET
from brand.examples.studio_nord import studio_nord
from brand.llm.content.resolution import resolve_content
from brand.llm.design.context import (
    assemble_design_context,
    resolve_brand_capabilities,
    resolve_creative_direction_capabilities,
    resolve_design_state_summary,
)
from brand.llm.narrative.planning import plan_narrative
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.project.model import Asset, Project


def _project_with_asset():
    project = Project(name="Riverside")
    asset = Asset(filename="render.png", content_type="image/png", size_bytes=100, path="a.png")
    return project.model_copy(update={"assets": (asset,)})


def test_resolve_brand_capabilities_reads_real_typography_and_personality():
    brand = studio_nord()
    caps = resolve_brand_capabilities(brand)
    assert "editorial" in caps.personality
    assert "h1" in caps.heading_roles
    assert "body" in caps.body_roles
    assert "primary" in caps.color_roles


def test_resolve_brand_capabilities_handles_no_brand():
    caps = resolve_brand_capabilities(None)
    assert caps.personality == ()
    assert caps.heading_roles == ()


def test_resolve_creative_direction_capabilities_reads_real_fields():
    caps = resolve_creative_direction_capabilities(EDITORIAL_QUIET)
    assert caps.id == "editorial-quiet"
    assert caps.lead_with in ("image", "statement", "metric", "drawing")


def test_resolve_creative_direction_capabilities_handles_none():
    caps = resolve_creative_direction_capabilities(None)
    assert caps.id == ""


def test_resolve_design_state_summary_handles_none():
    summary = resolve_design_state_summary(None)
    assert summary.has_state is False
    assert summary.version_number is None


def test_assemble_design_context_scopes_narrative_and_assets():
    project = _project_with_asset()
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "84 apartments. The project creates a strong connection to the landscape."},
    ))
    intent = SemanticIntent(explicit=SemanticFieldValues(audience="client"))
    plan = plan_narrative(project, content, intent)
    brand = studio_nord()

    ctx = assemble_design_context(plan, content, brand=brand, creative_direction=EDITORIAL_QUIET, project_name=project.name)

    assert ctx.project_id == project.id
    assert len(ctx.narrative_sections) == len(plan.all_sections())
    assert len(ctx.available_assets) == 1
    assert ctx.brand.brand_id == str(brand.brand_id)
    assert ctx.creative_direction.id == "editorial-quiet"
