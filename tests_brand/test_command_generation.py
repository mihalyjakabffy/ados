"""ADOS-M3.5 — brand/llm/command/generation.py."""

from __future__ import annotations

from types import SimpleNamespace

from brand.creative.intent import IntentType
from brand.llm.command.context import CommandGenerationContext, CurrentVisualState
from brand.llm.command.generation import (
    RawDirectionChoice,
    RuleBasedCommandGenerator,
    _materialize_choice,
)
from brand.llm.command.vocabulary import CommandRejectionReason, CommandSafetyLevel
from brand.llm.design.model import DesignIntent, SectionDesign
from brand.llm.design.vocabulary import (
    CompositionStrategy,
    ContrastLevel,
    TextDensity,
    TypographyHierarchy,
    VisualPriority,
    VisualRole,
    WhitespaceStrategy,
)


def _section(image_density=TextDensity.MEDIUM) -> SectionDesign:
    return SectionDesign(
        section_id="s1", visual_role=(VisualRole.HERO,), visual_priority=VisualPriority.DOMINANT,
        composition_mode=CompositionStrategy.IMAGE_LED, text_density=TextDensity.HIGH,
        image_density=image_density, whitespace=WhitespaceStrategy.MODERATE,
        contrast=ContrastLevel.HIGH, typography_hierarchy=TypographyHierarchy.RESTRAINED,
    )


def _context(design_intent: DesignIntent, current: CurrentVisualState) -> CommandGenerationContext:
    return CommandGenerationContext(design_intent=design_intent, current=current, project_id=design_intent.project_id)


def test_no_design_state_still_proposes_a_direction_for_a_confident_strategy():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.IMAGE_LED, density=TextDensity.MEDIUM)
    commands, skipped, _ = RuleBasedCommandGenerator().generate(_context(di, CurrentVisualState()))
    types = [c.intent.type for c in commands]
    assert IntentType.CHANGE_PAGE_DIRECTION in types
    assert any(c.intent.parameters.get("direction_id") == "image-led" for c in commands)


def test_direction_already_matching_is_skipped_not_repeated():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.IMAGE_LED, density=TextDensity.MEDIUM)
    current = CurrentVisualState(has_state=True, version_number=1, direction_id="image-led", text_density=0.62, image_ratio=0.72, page_count=3)
    commands, skipped, _ = RuleBasedCommandGenerator().generate(_context(di, current))
    assert not any(c.intent.type is IntentType.CHANGE_PAGE_DIRECTION for c in commands)
    assert any(s.reason is CommandRejectionReason.NO_CHANGE_NEEDED and s.source_field == "composition_strategy" for s in skipped)


def test_ambiguous_composition_strategy_is_skipped_never_guessed():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM)
    current = CurrentVisualState(has_state=True, version_number=1, direction_id="editorial-quiet", text_density=0.45, image_ratio=0.5, page_count=2)
    commands, skipped, _ = RuleBasedCommandGenerator().generate(_context(di, current))
    assert not any(c.intent.type is IntentType.CHANGE_PAGE_DIRECTION for c in commands)
    assert any(s.reason is CommandRejectionReason.AMBIGUOUS_MAPPING for s in skipped)


def test_density_gap_produces_increase_with_safe_label():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.VERY_HIGH)
    current = CurrentVisualState(has_state=True, version_number=1, direction_id="editorial-quiet", text_density=0.30, image_ratio=0.5, page_count=2)
    commands, _, _ = RuleBasedCommandGenerator().generate(_context(di, current))
    density_cmds = [c for c in commands if c.intent.type is IntentType.INCREASE_TEXT_DENSITY]
    assert len(density_cmds) == 1
    assert density_cmds[0].safety_level is CommandSafetyLevel.SAFE
    assert 0.0 < density_cmds[0].intent.parameters["strength"] <= 1.0


def test_density_gap_negative_produces_reduce():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MINIMAL)
    current = CurrentVisualState(has_state=True, version_number=1, direction_id="editorial-quiet", text_density=0.78, image_ratio=0.5, page_count=2)
    commands, _, _ = RuleBasedCommandGenerator().generate(_context(di, current))
    assert any(c.intent.type is IntentType.REDUCE_TEXT_DENSITY for c in commands)
    assert not any(c.intent.type is IntentType.INCREASE_TEXT_DENSITY for c in commands)


def test_negligible_density_gap_is_skipped():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM)
    current = CurrentVisualState(has_state=True, version_number=1, direction_id="editorial-quiet", text_density=0.55, image_ratio=0.5, page_count=2)
    commands, skipped, _ = RuleBasedCommandGenerator().generate(_context(di, current))
    assert not any(c.intent.type in (IntentType.INCREASE_TEXT_DENSITY, IntentType.REDUCE_TEXT_DENSITY) for c in commands)
    assert any(s.source_field == "density" and s.reason is CommandRejectionReason.NO_CHANGE_NEEDED for s in skipped)


def test_image_emphasis_uses_modal_section_image_density():
    di = DesignIntent(
        project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM,
        section_designs=(_section(TextDensity.VERY_HIGH), _section(TextDensity.VERY_HIGH), _section(TextDensity.LOW)),
    )
    current = CurrentVisualState(has_state=True, version_number=1, direction_id="editorial-quiet", text_density=0.55, image_ratio=0.20, page_count=2)
    commands, _, _ = RuleBasedCommandGenerator().generate(_context(di, current))
    assert any(c.intent.type is IntentType.INCREASE_IMAGE_EMPHASIS for c in commands)


def test_no_sections_skips_image_emphasis_as_ambiguous():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM)
    current = CurrentVisualState(has_state=True, version_number=1, direction_id="editorial-quiet", text_density=0.55, image_ratio=0.20, page_count=2)
    _, skipped, _ = RuleBasedCommandGenerator().generate(_context(di, current))
    assert any(s.source_field.startswith("section_designs") and s.reason is CommandRejectionReason.AMBIGUOUS_MAPPING for s in skipped)


def test_design_issues_are_recorded_as_no_safe_command_skips():
    from brand.llm.design.model import DesignIssue, DesignIssueType

    di = DesignIntent(
        project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM,
        design_issues=(DesignIssue(type=DesignIssueType.BRAND_CONFLICT, description="expressive type on a quiet brand"),),
    )
    _, skipped, _ = RuleBasedCommandGenerator().generate(_context(di, CurrentVisualState()))
    assert any(s.reason is CommandRejectionReason.NO_SAFE_COMMAND_EXISTS for s in skipped)


def test_materialize_choice_rejects_unknown_direction_id():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM)
    ctx = _context(di, CurrentVisualState())
    command, skip = _materialize_choice(RawDirectionChoice(chosen_direction_id="invented-direction"), ctx)
    assert command is None
    assert skip.reason is CommandRejectionReason.UNKNOWN_DIRECTION


def test_materialize_choice_accepts_a_real_registered_direction():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM)
    ctx = _context(di, CurrentVisualState(has_state=True, version_number=1, direction_id="editorial-quiet"))
    command, skip = _materialize_choice(RawDirectionChoice(chosen_direction_id="technical-dense", reason="dense sections"), ctx)
    assert command is not None
    assert command.intent.parameters["direction_id"] == "technical-dense"
    assert command.provenance.value == "llm_disambiguation"


def test_materialize_choice_declines_when_llm_also_declines():
    di = DesignIntent(project_id="p1", composition_strategy=CompositionStrategy.BALANCED, density=TextDensity.MEDIUM)
    ctx = _context(di, CurrentVisualState())
    command, skip = _materialize_choice(RawDirectionChoice(chosen_direction_id=None), ctx)
    assert command is None
    assert skip.reason is CommandRejectionReason.AMBIGUOUS_MAPPING
