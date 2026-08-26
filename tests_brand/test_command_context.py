"""ADOS-M3.5 — brand/llm/command/context.py."""

from __future__ import annotations

from types import SimpleNamespace

from brand.llm.command.context import assemble_command_context, resolve_current_visual_state
from brand.llm.design.model import DesignIntent
from brand.llm.design.vocabulary import CompositionStrategy, TextDensity


def _fake_state(*, version=3, direction_id="editorial-quiet", text_density=0.45, image_ratio=0.5, pages=2):
    return SimpleNamespace(
        version=SimpleNamespace(number=version),
        document=SimpleNamespace(direction_id=direction_id),
        visual_language=SimpleNamespace(text_density=text_density, image_ratio=image_ratio),
        pages=tuple(SimpleNamespace() for _ in range(pages)),
    )


def _design_intent(**overrides) -> DesignIntent:
    defaults = dict(project_id="p1", narrative_plan_id="n1", composition_strategy=CompositionStrategy.IMAGE_LED, density=TextDensity.HIGH)
    defaults.update(overrides)
    return DesignIntent(**defaults)


def test_resolve_current_visual_state_with_no_design_state():
    state = resolve_current_visual_state(None)
    assert state.has_state is False
    assert state.version_number is None
    assert state.page_count == 0


def test_resolve_current_visual_state_reads_real_fields():
    state = resolve_current_visual_state(_fake_state(version=5, direction_id="image-led", text_density=0.6, image_ratio=0.7, pages=3))
    assert state.has_state is True
    assert state.version_number == 5
    assert state.direction_id == "image-led"
    assert state.text_density == 0.6
    assert state.image_ratio == 0.7
    assert state.page_count == 3


def test_assemble_command_context_carries_project_id_from_design_intent():
    ctx = assemble_command_context(_design_intent(project_id="proj-42"), None)
    assert ctx.project_id == "proj-42"
    assert ctx.design_intent.composition_strategy is CompositionStrategy.IMAGE_LED
    assert ctx.current.has_state is False
