"""ADOS-M3.6 — brand/llm/loop/patch.py."""

from __future__ import annotations

import pytest

from brand.llm.content.resolution import resolve_content
from brand.llm.design.planning import plan_design_intent
from brand.llm.loop.model import DesignIntentPatch
from brand.llm.loop.patch import PatchTargetError, PatchValueError, apply_design_intent_patch
from brand.llm.narrative.planning import plan_narrative
from brand.llm.semantic_intent import SemanticFieldValues, SemanticIntent
from brand.project.model import Project


@pytest.fixture()
def fixture():
    project = Project(name="Riverside")
    content = resolve_content(project, raw_documents=(
        {"source_id": "brief", "text": "84 apartments. GFA of 13,100 m². A strong connection to the landscape."},
    ))
    narrative_plan = plan_narrative(project, content, SemanticIntent(explicit=SemanticFieldValues(audience="client")))
    design_intent = plan_design_intent(project, content, narrative_plan)
    return design_intent, narrative_plan


def test_apply_patch_changes_only_the_targeted_field(fixture):
    di, narrative_plan = fixture
    patched = apply_design_intent_patch(di, DesignIntentPatch(target="density", value="low"), narrative_plan)
    assert patched.density.value == "low"
    assert patched.composition_strategy == di.composition_strategy
    assert patched.id != di.id


def test_apply_patch_rejects_unknown_target(fixture):
    di, narrative_plan = fixture
    with pytest.raises(PatchTargetError):
        apply_design_intent_patch(di, DesignIntentPatch(target="not_a_real_field", value="x"), narrative_plan)


def test_apply_patch_rejects_unknown_value(fixture):
    di, narrative_plan = fixture
    with pytest.raises(PatchValueError):
        apply_design_intent_patch(di, DesignIntentPatch(target="density", value="extremely_high"), narrative_plan)


def test_patched_design_intent_passes_full_schema_validation(fixture):
    di, narrative_plan = fixture
    patched = apply_design_intent_patch(di, DesignIntentPatch(target="typography_hierarchy", value="restrained"), narrative_plan)
    assert patched.typography_hierarchy.value == "restrained"


def test_apply_patch_records_provenance_in_metadata(fixture):
    di, narrative_plan = fixture
    patched = apply_design_intent_patch(di, DesignIntentPatch(target="density", value="high"), narrative_plan)
    assert patched.metadata["patched_from"] == di.id
    assert patched.metadata["patch_target"] == "density"
    assert patched.metadata["patch_value"] == "high"
