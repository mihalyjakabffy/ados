"""
brand/llm/design/context.py

The deterministic context-assembly layer ADOS-M3.4 §37 asks for:

    SemanticIntent + NarrativePlan + relevant ContentIntelligenceModel
        + Brand DNA + CreativeDirection + DesignState
        -> scoped DesignGenerationContext

This module never fetches anything on a generator's behalf — every
input is a real object the caller already has (a `NarrativePlan`
already resolved by M3.3, a `ContentIntelligenceModel` already resolved
by M3.2, a `Brand` and `CreativeDirection` the caller already loaded).
It only shrinks and organises them into what a design generator
actually needs to see (§37: "do not blindly serialize the entire
repository").

**Precedence (ADOS-M3.4 §38), as data, not code here.** This module
does not itself enforce precedence — it only exposes what each layer
actually says. Resolving a conflict between a generated preference and
a higher-priority layer is ``brand.llm.design.planning``'s job (the
step that has both the generated `DesignIntent` and this context in
hand); baking precedence into context assembly would make it
unverifiable by the same deterministic validation ADOS-M3.2/M3.3 apply
to everything else this system produces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from brand.creative.direction import CreativeDirection
    from brand.design_state.model import DesignState
    from brand.llm.content.model import ContentIntelligenceModel
    from brand.llm.narrative.model import NarrativePlan
    from brand.models.brand import Brand


#: The real, fixed field names ``brand.models.visual_identity.ColourSystem``
#: declares — unlike typography roles (per-brand dict keys), these are
#: part of the model itself, so they are a genuine ADOS-wide constant.
COLOR_ROLE_NAMES: tuple[str, ...] = (
    "primary", "secondary", "accent", "background", "surface",
    "text_primary", "text_secondary", "border", "neutral",
    "semantic.success", "semantic.warning", "semantic.error", "semantic.info",
)


@dataclass(frozen=True)
class BrandCapabilities:
    """The subset of a real ``Brand`` a design generator can actually
    reference — ADOS-M3.4 §6/§34: real personality axes and real
    per-brand type-role names, never a duplicated colour/font/spacing
    system."""

    brand_id: str = ""
    brand_version: str = ""
    personality: tuple[str, ...] = ()
    heading_roles: tuple[str, ...] = ()
    body_roles: tuple[str, ...] = ()
    numeric_roles: tuple[str, ...] = ()
    color_roles: tuple[str, ...] = COLOR_ROLE_NAMES
    #: Short, descriptive-only notes — never a value this package
    #: validates a design decision against.
    photography_note: str = ""
    colour_treatment: str = ""


def resolve_brand_capabilities(brand: Optional["Brand"]) -> BrandCapabilities:
    if brand is None:
        return BrandCapabilities()
    typo = brand.visual_identity.typography
    imagery = brand.visual_identity.imagery
    return BrandCapabilities(
        brand_id=str(brand.brand_id), brand_version=brand.version,
        personality=tuple(p.value for p in brand.identity.personality),
        heading_roles=tuple(typo.heading_styles), body_roles=tuple(typo.body_styles),
        numeric_roles=tuple(typo.numeric_styles), color_roles=COLOR_ROLE_NAMES,
        photography_note=imagery.photography, colour_treatment=imagery.colour_treatment.value,
    )


@dataclass(frozen=True)
class CreativeDirectionCapabilities:
    """The subset of a real ``CreativeDirection`` relevant to design
    reasoning — ADOS-M3.4 §8: consumed, never redeclared."""

    id: str = ""
    audience: str = ""
    goal: str = ""
    lead_with: str = ""
    emphasis_ceiling: Optional[int] = None
    text_density: Optional[float] = None
    image_ratio: Optional[float] = None


def resolve_creative_direction_capabilities(
    direction: Optional["CreativeDirection"],
) -> CreativeDirectionCapabilities:
    if direction is None:
        return CreativeDirectionCapabilities()
    return CreativeDirectionCapabilities(
        id=direction.id, audience=direction.audience.value, goal=direction.goal.value,
        lead_with=direction.lead_with.value, emphasis_ceiling=direction.emphasis_ceiling,
        text_density=direction.text_density, image_ratio=direction.image_ratio,
    )


@dataclass(frozen=True)
class DesignStateSummary:
    """What, if anything, already exists — ADOS-M3.4 §9/§54. Never the
    full DesignState (a design generator has no use for every page's
    literal content); enough to know whether this is a fresh design or
    a transformation of an existing one."""

    has_state: bool = False
    version_number: Optional[int] = None
    existing_direction_id: str = ""
    existing_page_count: int = 0


def resolve_design_state_summary(design_state: Optional["DesignState"]) -> DesignStateSummary:
    if design_state is None:
        return DesignStateSummary()
    return DesignStateSummary(
        has_state=True, version_number=design_state.version.number,
        existing_direction_id=design_state.document.direction_id,
        existing_page_count=len(design_state.pages),
    )


def summarize_narrative_plan(plan: "NarrativePlan") -> tuple[dict[str, Any], ...]:
    """Section ids, purposes, and content references only — never the
    plan's own draft prose, which a design generator has no use for."""
    return tuple(
        {
            "id": s.id, "role": s.role.value, "purpose": s.purpose,
            "priority": s.priority.value, "requirement": s.requirement.value,
            "sequence": s.sequence,
            "fact_ids": list(s.content_refs.fact_ids), "claim_ids": list(s.content_refs.claim_ids),
            "asset_ids": list(s.content_refs.asset_ids),
        }
        for s in plan.all_sections()
    )


def summarize_available_assets(content: "ContentIntelligenceModel") -> tuple[dict[str, Any], ...]:
    return tuple(
        {"id": a.asset_id, "type": a.type, "caption": a.caption, "subject": a.subject}
        for a in content.assets
    )


@dataclass(frozen=True)
class DesignGenerationContext:
    """Everything a ``DesignIntentGenerator`` actually receives —
    ADOS-M3.4 §37. Built only from real objects a caller already has."""

    narrative_plan: "NarrativePlan"
    narrative_sections: tuple[dict[str, Any], ...]
    available_assets: tuple[dict[str, Any], ...]
    brand: BrandCapabilities = field(default_factory=BrandCapabilities)
    creative_direction: CreativeDirectionCapabilities = field(default_factory=CreativeDirectionCapabilities)
    design_state: DesignStateSummary = field(default_factory=DesignStateSummary)
    project_id: str = ""
    project_name: str = ""


def assemble_design_context(
    narrative_plan: "NarrativePlan",
    content: "ContentIntelligenceModel",
    *,
    brand: Optional["Brand"] = None,
    creative_direction: Optional["CreativeDirection"] = None,
    design_state: Optional["DesignState"] = None,
    project_name: str = "",
) -> DesignGenerationContext:
    return DesignGenerationContext(
        narrative_plan=narrative_plan,
        narrative_sections=summarize_narrative_plan(narrative_plan),
        available_assets=summarize_available_assets(content),
        brand=resolve_brand_capabilities(brand),
        creative_direction=resolve_creative_direction_capabilities(creative_direction),
        design_state=resolve_design_state_summary(design_state),
        project_id=narrative_plan.project_id, project_name=project_name,
    )
