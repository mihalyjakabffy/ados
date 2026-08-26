"""
brand/llm/design/generation.py

The generator abstraction ADOS-M3.4 §36 asks for, mirroring
``brand.llm.narrative.generation``'s own shape (which itself reuses
``brand.llm.providers.claude_provider``'s shared ``get_client()``/
``call_structured()`` seam — no second Claude client, and the domain
(``DesignIntent``) never touches an Anthropic SDK type).

Two implementations:

* :class:`RuleBasedDesignIntentGenerator` — deterministic, no network
  call. ADOS-M3.4 §44 is explicit this is a CI-determinism/schema/
  regression fixture, not a claim of design sophistication: it derives
  a visual role and strategy per section from the real
  ``NarrativePlan`` priority/role it was given, and from real
  ``CreativeDirection``/``Brand`` capabilities when supplied.
* :class:`LLMDesignIntentGenerator` — Claude, via structured output.

**The anti-hallucination mechanism is structural, mirroring
ADOS-M3.2/M3.3's own.** The LLM's structured-output schema
(``RawDesignIntent`` and its nested ``Raw*`` types) may only name a
narrative **section id** and an asset **id** — never restate their
content — and every enum-like field is a plain string, normalized and
coerced to a safe default by code, never trusted as written. After the
call returns, :func:`_materialize`:

* drops any ``section_id``/``asset_id`` that does not actually appear
  in the ``NarrativeGenerationContext`` (an invented section or asset
  is dropped, never trusted);
* guarantees every real narrative section ends up covered — either by
  a ``SectionDesign`` or an explicit ``DesignExclusion`` — even if the
  LLM's own response omitted it entirely (ADOS-M3.4 §27: "no narrative
  section may silently disappear" is enforced by code, not requested
  of the model);
* drops any ``visual_language`` entry, ``heading_role``, ``body_role``,
  or ``caption_role`` that is not a real value the given ``Brand``
  itself claims, when a ``Brand`` was supplied (ADOS-M3.4 §10/§34).
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from brand.llm.design.context import DesignGenerationContext
from brand.llm.design.model import (
    AssetDesignRef,
    DesignConstraint,
    DesignExclusion,
    DesignIntent,
    DesignIssue,
    DesignIssueType,
    SectionDesign,
)
from brand.llm.design.vocabulary import (
    AssetImportance,
    ColorStrategy,
    CompositionStrategy,
    ConstraintStrength,
    ContrastLevel,
    DesignChangeType,
    DesignExclusionReason,
    GridStrategy,
    ImageRole,
    PersonalityAxis,
    Rhythm,
    TextDensity,
    TypographyHierarchy,
    VisualPriority,
    VisualRole,
    WhitespaceStrategy,
)
from brand.llm.provider import ProviderMetadata

logger = logging.getLogger(__name__)


class DesignIntentGenerator(ABC):
    """One call: a scoped context in, a ``DesignIntent`` and its
    metadata out. Mirrors
    ``brand.llm.narrative.generation.NarrativeGenerator``'s own shape."""

    @abstractmethod
    def generate(
        self, context: DesignGenerationContext,
    ) -> tuple[DesignIntent, Optional[ProviderMetadata]]:
        """Raise :class:`~brand.llm.provider.ProviderError` on any
        failure — never a vendor-specific exception."""


# ---------------------------------------------------------------------------
# Normalization and coercion helpers (ADOS-M3.4 §43)
# ---------------------------------------------------------------------------

_NON_ALNUM = re.compile(r"[\s\-]+")


def _normalize_token(value: str) -> str:
    """``"image led"``/``"image-led"``/``"image_led"`` all resolve to
    ``"image_led"`` — ADOS-M3.4 §43: do not allow vocabulary
    fragmentation."""
    return _NON_ALNUM.sub("_", value.strip().lower())


def _coerce_enum(value: Optional[str], enum_cls: type, default: Any) -> Any:
    if not value:
        return default
    try:
        return enum_cls(_normalize_token(value))
    except ValueError:
        logger.warning("design generation: unrecognised %s %r, defaulting to %r", enum_cls.__name__, value, default)
        return default


# ---------------------------------------------------------------------------
# Raw LLM structured-output schema
# ---------------------------------------------------------------------------


class RawAssetRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    role: str = "supporting_image"
    importance: str = "supporting"


class RawSectionDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    visual_role: tuple[str, ...] = Field(min_length=1)
    visual_priority: str = "secondary"
    composition_mode: str = "balanced"
    asset_refs: tuple[RawAssetRef, ...] = ()
    text_density: str = "medium"
    image_density: str = "medium"
    diagram_strategy: Optional[str] = None
    whitespace: str = "moderate"
    contrast: str = "medium"
    repetition: tuple[str, ...] = ()
    heading_role: Optional[str] = None
    body_role: Optional[str] = None
    caption_role: Optional[str] = None
    typography_hierarchy: str = "restrained"
    color_strategy: Optional[str] = None
    change_type: str = "introduce"
    rationale: Optional[str] = None


class RawConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=300)
    strength: str = "soft"
    source: str = ""


class RawIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    description: str = Field(min_length=1, max_length=400)
    section_id: Optional[str] = None


class RawExclusion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    reason: str = "other"
    description: str = ""


class RawDesignIntent(BaseModel):
    """The complete LLM structured-output contract. No brand colour,
    font, or spacing value anywhere in this schema — only semantic
    strategy enums (as plain strings, coerced by code) and references
    to real section/asset ids."""

    model_config = ConfigDict(extra="forbid")

    visual_language: tuple[str, ...] = ()
    composition_strategy: str = "balanced"
    rhythm: str = "steady"
    density: str = "medium"
    typography_hierarchy: str = "restrained"
    color_strategy: str = "restrained"
    grid_strategy: str = "editorial"
    whitespace_strategy: str = "moderate"
    section_designs: tuple[RawSectionDesign, ...] = Field(min_length=1)
    excluded_sections: tuple[RawExclusion, ...] = ()
    constraints: tuple[RawConstraint, ...] = ()
    design_issues: tuple[RawIssue, ...] = ()


def _materialize(raw: RawDesignIntent, context: DesignGenerationContext) -> DesignIntent:
    """Attach validated ids and brand tokens, coerce every free-text
    enum-like field, and guarantee full narrative-section coverage —
    the same "the model proposes, code decides" split
    ``brand.llm.content.extraction``/``brand.llm.narrative.generation``
    already establish."""
    valid_section_ids = {s["id"] for s in context.narrative_sections}
    valid_asset_ids = {a["id"] for a in context.available_assets}
    brand = context.brand

    def _valid_role(role: Optional[str], allowed: tuple[str, ...]) -> Optional[str]:
        if role is None:
            return None
        if not allowed:  # no Brand given at all -- nothing to check against
            return role
        if role in allowed:
            return role
        logger.warning("design generation: dropping unrecognised brand role %r", role)
        return None

    section_designs: list[SectionDesign] = []
    covered_ids: set[str] = set()
    for rs in raw.section_designs:
        if rs.section_id not in valid_section_ids:
            logger.warning("design generation: dropping SectionDesign for invented section_id %r", rs.section_id)
            continue
        covered_ids.add(rs.section_id)

        asset_refs = tuple(
            AssetDesignRef(
                asset_id=ra.asset_id, role=_coerce_enum(ra.role, ImageRole, ImageRole.SUPPORTING_IMAGE),
                importance=_coerce_enum(ra.importance, AssetImportance, AssetImportance.SUPPORTING),
            )
            for ra in rs.asset_refs if ra.asset_id in valid_asset_ids
        )
        visual_roles = tuple(
            r for r in (_coerce_enum(v, VisualRole, None) for v in rs.visual_role) if r is not None
        ) or (VisualRole.CONTEXTUAL,)

        section_designs.append(SectionDesign(
            section_id=rs.section_id, visual_role=visual_roles,
            visual_priority=_coerce_enum(rs.visual_priority, VisualPriority, VisualPriority.SECONDARY),
            composition_mode=_coerce_enum(rs.composition_mode, CompositionStrategy, CompositionStrategy.BALANCED),
            asset_refs=asset_refs,
            text_density=_coerce_enum(rs.text_density, TextDensity, TextDensity.MEDIUM),
            image_density=_coerce_enum(rs.image_density, TextDensity, TextDensity.MEDIUM),
            diagram_strategy=rs.diagram_strategy,
            whitespace=_coerce_enum(rs.whitespace, WhitespaceStrategy, WhitespaceStrategy.MODERATE),
            contrast=_coerce_enum(rs.contrast, ContrastLevel, ContrastLevel.MEDIUM),
            repetition=rs.repetition,
            heading_role=_valid_role(rs.heading_role, brand.heading_roles),
            body_role=_valid_role(rs.body_role, brand.body_roles),
            caption_role=_valid_role(rs.caption_role, brand.body_roles),
            typography_hierarchy=_coerce_enum(rs.typography_hierarchy, TypographyHierarchy, TypographyHierarchy.RESTRAINED),
            color_strategy=_coerce_enum(rs.color_strategy, ColorStrategy, None) if rs.color_strategy else None,
            change_type=_coerce_enum(rs.change_type, DesignChangeType, DesignChangeType.INTRODUCE),
            rationale=rs.rationale,
        ))

    exclusions: list[DesignExclusion] = []
    for rx in raw.excluded_sections:
        if rx.section_id not in valid_section_ids or rx.section_id in covered_ids:
            continue
        covered_ids.add(rx.section_id)
        exclusions.append(DesignExclusion(
            section_id=rx.section_id,
            reason=_coerce_enum(rx.reason, DesignExclusionReason, DesignExclusionReason.OTHER),
            description=rx.description,
        ))

    # ADOS-M3.4 §27: no real narrative section may silently disappear,
    # regardless of what the generator returned.
    for section_id in valid_section_ids - covered_ids:
        exclusions.append(DesignExclusion(
            section_id=section_id, reason=DesignExclusionReason.OTHER,
            description="not addressed by the design generator",
        ))

    visual_language = tuple(
        r for r in (_coerce_enum(v, PersonalityAxis, None) for v in raw.visual_language) if r is not None
    )
    if brand.personality:
        dropped = [v for v in visual_language if v.value not in brand.personality]
        if dropped:
            logger.warning("design generation: dropping visual_language values the brand does not claim: %s", dropped)
        visual_language = tuple(v for v in visual_language if v.value in brand.personality)

    constraints = tuple(
        DesignConstraint(
            description=rc.description,
            strength=_coerce_enum(rc.strength, ConstraintStrength, ConstraintStrength.SOFT),
            source=rc.source,
        )
        for rc in raw.constraints
    )
    design_issues = tuple(
        DesignIssue(
            type=_coerce_enum(ri.type, DesignIssueType, DesignIssueType.UNSUPPORTED_VISUAL_INFERENCE),
            description=ri.description,
            section_id=ri.section_id if ri.section_id in valid_section_ids else None,
        )
        for ri in raw.design_issues
    )

    return DesignIntent(
        project_id=context.project_id, narrative_plan_id=context.narrative_plan.id,
        content_model_version=context.narrative_plan.content_model_version,
        brand_id=brand.brand_id or None, brand_version=brand.brand_version or None,
        design_state_version=context.design_state.version_number,
        visual_language=visual_language,
        composition_strategy=_coerce_enum(raw.composition_strategy, CompositionStrategy, CompositionStrategy.BALANCED),
        rhythm=_coerce_enum(raw.rhythm, Rhythm, Rhythm.STEADY),
        density=_coerce_enum(raw.density, TextDensity, TextDensity.MEDIUM),
        typography_hierarchy=_coerce_enum(raw.typography_hierarchy, TypographyHierarchy, TypographyHierarchy.RESTRAINED),
        color_strategy=_coerce_enum(raw.color_strategy, ColorStrategy, ColorStrategy.RESTRAINED),
        grid_strategy=_coerce_enum(raw.grid_strategy, GridStrategy, GridStrategy.EDITORIAL),
        whitespace_strategy=_coerce_enum(raw.whitespace_strategy, WhitespaceStrategy, WhitespaceStrategy.MODERATE),
        section_designs=tuple(section_designs), excluded_sections=tuple(exclusions),
        constraints=constraints, design_issues=design_issues,
        metadata={"generator": "llm"},
    )


# ---------------------------------------------------------------------------
# Deterministic rule-based generator (ADOS-M3.4 §44)
# ---------------------------------------------------------------------------

_ROLE_TO_VISUAL_ROLE: dict[str, VisualRole] = {
    "opening": VisualRole.INTRO, "context": VisualRole.CONTEXTUAL, "problem": VisualRole.CONTEXTUAL,
    "question": VisualRole.CONTEXTUAL, "concept": VisualRole.HERO, "strategy": VisualRole.DIAGRAM,
    "analysis": VisualRole.DATA, "development": VisualRole.PROCESS, "evidence": VisualRole.EVIDENCE,
    "comparison": VisualRole.COMPARISON, "result": VisualRole.EVIDENCE, "impact": VisualRole.EVIDENCE,
    "technical_explanation": VisualRole.TECHNICAL, "conclusion": VisualRole.CLOSING,
    "call_to_action": VisualRole.CLOSING, "closing": VisualRole.CLOSING,
}

_PRIORITY_TO_VISUAL_PRIORITY: dict[str, VisualPriority] = {
    "primary": VisualPriority.DOMINANT, "secondary": VisualPriority.SECONDARY,
    "supporting": VisualPriority.SUPPORTING, "optional": VisualPriority.MINIMAL,
}

_PRIORITY_TO_ASSET_IMPORTANCE: dict[VisualPriority, AssetImportance] = {
    VisualPriority.DOMINANT: AssetImportance.HERO, VisualPriority.SECONDARY: AssetImportance.PRIMARY,
    VisualPriority.SUPPORTING: AssetImportance.SUPPORTING, VisualPriority.MINIMAL: AssetImportance.OPTIONAL,
}

_LEAD_WITH_TO_COMPOSITION: dict[str, CompositionStrategy] = {
    "image": CompositionStrategy.IMAGE_LED, "statement": CompositionStrategy.TEXT_LED,
    "metric": CompositionStrategy.DATA_LED, "drawing": CompositionStrategy.DIAGRAM_LED,
}

_HIGH_DENSITY_ROLES = frozenset({"technical_explanation", "analysis"})
_LOW_DENSITY_ROLES = frozenset({"opening", "closing", "concept"})


class RuleBasedDesignIntentGenerator(DesignIntentGenerator):
    """Deterministic, no network call — ADOS-M3.4 §44. Derives a
    ``SectionDesign`` for every real narrative section directly from
    that section's own role and priority, and from the real
    ``CreativeDirection``/``Brand`` capabilities it was given. Not a
    claim of design sophistication: a CI-safe fixture proving the
    pipeline's mechanics (materialization, brand-token filtering,
    validation, evaluation)."""

    def generate(
        self, context: DesignGenerationContext,
    ) -> tuple[DesignIntent, Optional[ProviderMetadata]]:
        brand, direction = context.brand, context.creative_direction

        section_designs = []
        hero_asset_assigned = False
        for section in context.narrative_sections:
            role_value = section["role"]
            priority = _PRIORITY_TO_VISUAL_PRIORITY.get(section["priority"], VisualPriority.SECONDARY)
            visual_role = (_ROLE_TO_VISUAL_ROLE.get(role_value, VisualRole.CONTEXTUAL),)

            asset_ids = section["asset_ids"]
            has_claims = bool(section["claim_ids"])
            if asset_ids:
                composition_mode = CompositionStrategy.IMAGE_LED
            elif has_claims:
                composition_mode = CompositionStrategy.TEXT_LED
            else:
                composition_mode = CompositionStrategy.BALANCED

            text_density = (
                TextDensity.HIGH if role_value in _HIGH_DENSITY_ROLES
                else TextDensity.LOW if role_value in _LOW_DENSITY_ROLES
                else TextDensity.MEDIUM
            )
            image_density = TextDensity.HIGH if asset_ids and role_value in _LOW_DENSITY_ROLES else TextDensity.MEDIUM
            whitespace = (
                WhitespaceStrategy.GENEROUS if role_value in _LOW_DENSITY_ROLES
                else WhitespaceStrategy.COMPACT if role_value in _HIGH_DENSITY_ROLES
                else WhitespaceStrategy.MODERATE
            )
            contrast = (
                ContrastLevel.HIGH if priority is VisualPriority.DOMINANT
                else ContrastLevel.LOW if priority is VisualPriority.MINIMAL
                else ContrastLevel.MEDIUM
            )
            typography_hierarchy = (
                TypographyHierarchy.STRONG if priority is VisualPriority.DOMINANT
                else TypographyHierarchy.TECHNICAL if role_value == "technical_explanation"
                else TypographyHierarchy.RESTRAINED
            )

            # Only the first dominant, asset-bearing section becomes the
            # document's true "hero" moment (ADOS-M3.4 §18/§50 Case F: a
            # hero/supporting *distinction*, not every asset independently
            # claiming top billing) -- later ones downgrade to primary.
            section_asset_refs = []
            for aid in asset_ids:
                if priority is VisualPriority.DOMINANT and not hero_asset_assigned:
                    importance = AssetImportance.HERO
                    hero_asset_assigned = True
                else:
                    importance = (
                        AssetImportance.PRIMARY if priority is VisualPriority.DOMINANT
                        else _PRIORITY_TO_ASSET_IMPORTANCE[priority]
                    )
                section_asset_refs.append(AssetDesignRef(
                    asset_id=aid,
                    role=ImageRole.HERO_IMAGE if importance is AssetImportance.HERO else ImageRole.SUPPORTING_IMAGE,
                    importance=importance,
                ))
            asset_refs = tuple(section_asset_refs)

            heading_role = (brand.heading_roles[0] if priority is VisualPriority.DOMINANT and brand.heading_roles else None)
            body_role = (brand.body_roles[0] if brand.body_roles else None)

            section_designs.append(SectionDesign(
                section_id=section["id"], visual_role=visual_role, visual_priority=priority,
                composition_mode=composition_mode, asset_refs=asset_refs,
                text_density=text_density, image_density=image_density,
                whitespace=whitespace, contrast=contrast,
                heading_role=heading_role, body_role=body_role,
                typography_hierarchy=typography_hierarchy,
                change_type=DesignChangeType.MODIFY if context.design_state.has_state else DesignChangeType.INTRODUCE,
            ))

        design_issues = []
        if not context.available_assets and any(s["priority"] == "primary" for s in context.narrative_sections):
            design_issues.append(DesignIssue(
                type=DesignIssueType.ASSET_SCARCITY,
                description="no assets are available; primary sections rely on typography/diagram strategies instead",
            ))
        if context.narrative_plan.missing_information:
            design_issues.append(DesignIssue(
                type=DesignIssueType.MISSING_CONTENT_ACKNOWLEDGED,
                description="the narrative plan identifies missing information; no placeholder content was invented for it",
            ))

        constraints = [DesignConstraint(
            description="maintain_narrative_progression", strength=ConstraintStrength.SOFT,
            source="generated_preference",
        )]
        if "quiet" in brand.personality or "editorial" in brand.personality:
            constraints.append(DesignConstraint(
                description="preserve_brand_minimalism", strength=ConstraintStrength.HARD, source="brand_dna",
            ))

        composition_strategy = _LEAD_WITH_TO_COMPOSITION.get(direction.lead_with, CompositionStrategy.BALANCED)
        whitespace_strategy = (
            WhitespaceStrategy.GENEROUS if ("quiet" in brand.personality or "editorial" in brand.personality)
            else WhitespaceStrategy.MODERATE
        )
        color_strategy = ColorStrategy.MONOCHROME if brand.colour_treatment == "monochrome" else ColorStrategy.RESTRAINED
        visual_language = tuple(PersonalityAxis(p) for p in brand.personality)

        design_intent = DesignIntent(
            project_id=context.project_id, narrative_plan_id=context.narrative_plan.id,
            content_model_version=context.narrative_plan.content_model_version,
            brand_id=brand.brand_id or None, brand_version=brand.brand_version or None,
            design_state_version=context.design_state.version_number,
            visual_language=visual_language, composition_strategy=composition_strategy,
            density=TextDensity.MEDIUM, typography_hierarchy=TypographyHierarchy.RESTRAINED,
            color_strategy=color_strategy, grid_strategy=GridStrategy.EDITORIAL,
            whitespace_strategy=whitespace_strategy,
            section_designs=tuple(section_designs), constraints=tuple(constraints),
            design_issues=tuple(design_issues), metadata={"generator": "rule-based"},
        )
        return design_intent, None


# ---------------------------------------------------------------------------
# LLM generator (ADOS-M3.4 §36/§45)
# ---------------------------------------------------------------------------


class LLMDesignIntentGenerator(DesignIntentGenerator):
    """The real, structured-output design generator. Reuses
    ``brand.llm.providers.claude_provider``'s shared client/call helper."""

    _DEFAULT_MODEL = "claude-opus-5"
    _DEFAULT_MAX_TOKENS = 8192

    def __init__(self, model: Optional[str] = None, max_tokens: Optional[int] = None) -> None:
        self._model = model or os.environ.get("DESIGN_INTENT_MODEL", self._DEFAULT_MODEL)
        self._max_tokens = max_tokens or int(os.environ.get("DESIGN_INTENT_MAX_TOKENS", self._DEFAULT_MAX_TOKENS))
        self._client: Any = None

    def generate(
        self, context: DesignGenerationContext,
    ) -> tuple[DesignIntent, ProviderMetadata]:
        from brand.llm.design.prompt import build_design_system_prompt, build_design_user_message
        from brand.llm.providers.claude_provider import call_structured, get_client

        if self._client is None:
            self._client = get_client()

        system_prompt = build_design_system_prompt()
        user_message = build_design_user_message(context)
        raw, metadata = call_structured(
            self._client, model=self._model, max_tokens=self._max_tokens,
            system_prompt=system_prompt, user_message=user_message,
            output_format=RawDesignIntent, provider_name="claude",
        )
        return _materialize(raw, context), metadata
