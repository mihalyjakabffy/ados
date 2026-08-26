"""
brand/design_state/build.py

The one function that assembles a real ``DesignState`` — a pure read,
never a second composition engine. Every number, name and id below comes
from calling existing, unmodified code:

* ``brand.project.content_resolution`` for what a document's content
  actually is.
* ``brand.project.versioning`` for resolving a specific saved Version
  (the exact machinery ADOS-M2.2.1's export pipeline already built).
* ``brand.creative.direction.get_direction`` for the projection's visual
  language.
* ``brand.project.requirements`` for its constraints.
* ``brand.creative.plan.PagePlan`` (reconstructed from either the
  document's live ``latest_plan`` or a saved Version) for pages/
  components/layout.

Nothing here calls ``compose()`` — a DesignState reflects whatever the
last real composition produced, exactly the same "never invent a page
the Composer didn't produce" rule ``Document.latest_plan`` has always
followed (ADOS-M2.1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from brand.design_state.model import (
    AssetState,
    BrandState,
    ComponentState,
    ConstraintLevel,
    ConstraintRule,
    ConstraintState,
    ContentItemState,
    ContentState,
    DesignState,
    DocumentState,
    LayoutState,
    PageState,
    ProjectState,
    VersionState,
    VisualLanguageState,
)

if TYPE_CHECKING:
    from brand.models.brand import Brand
    from brand.project.model import Document, Project
    from brand.project.versioning import ProjectResolver as _ProjectResolverAlias  # noqa: F401

#: Slot-component name (brand.creative.archetypes.SlotSpec's own
#: vocabulary) -> the semantic component kind ADOS-M2.5 §9 asks for. Not
#: exhaustive by design — anything unlisted falls back to "Text", the
#: safest default for a slot that is, structurally, always some kind of
#: type-set content.
_COMPONENT_KIND: dict[str, str] = {
    "project-title": "Heading",
    "section-label": "SectionHeader",
    "hero": "Image",
    "figure": "Image",
    "figure-a": "Image",
    "figure-b": "Image",
    "view": "Diagram",
    "lead-value": "Metric",
    "metric": "Metric",
    "standfirst": "Text",
    "body": "Text",
    "notes": "Text",
    "issue": "Caption",
    "entry": "Card",
}


def _semantic_component_kind(component: str) -> str:
    return _COMPONENT_KIND.get(component, "Text")


def _preview(item) -> str:
    from brand.project.model import ContentItemKind

    text = {
        ContentItemKind.TEXT: item.text,
        ContentItemKind.FACT: f"{item.label}: {item.value}" if item.label else str(item.value),
        ContentItemKind.METRIC: f"{item.label}: {item.value}{item.unit}" if item.label else str(item.value),
        ContentItemKind.IMAGE: item.caption or item.asset_id or "(image)",
    }.get(item.kind, "")
    return text[:160]


def _content_item_state(item, *, shared: bool) -> ContentItemState:
    return ContentItemState(id=item.id, kind=item.kind.value, preview=_preview(item), shared=shared)


def build_design_state(
    project: "Project",
    document: "Document",
    brand: Optional["Brand"] = None,
    *,
    version_number: Optional[int] = None,
    resolve_project: Optional["_ProjectResolverAlias"] = None,
) -> DesignState:
    """Assemble the DesignState for ``document`` inside ``project``.

    ``brand`` is optional — a project may not have one attached yet
    (ADOS-M2.1's own "compose without a brand is rejected" state); a
    DesignState without an output is still a real, inspectable state.
    ``version_number`` reads a specific saved Version's frozen content/
    plan instead of the document's current live state — the same
    read-only lookup ``GET .../versions`` already exposes, never an
    auto-save (see ``brand.project.versioning.find_version``).
    """
    from brand.creative.directions import get_direction
    from brand.creative.plan import PagePlan
    from brand.project.content_resolution import resolve_document_content
    from brand.project.document_types import UnknownDocumentTypeError, get_document_type
    from brand.project.requirements import check_requirements
    from brand.project.versioning import find_version, plan_from_version, snapshot_document_at_version

    version_state = VersionState(
        available_versions=tuple(
            sorted((v.number for v in project.versions if v.document_id == document.id), reverse=True)
        ),
    )

    working_document = document
    if version_number is not None:
        version = find_version(project, document, version_number)
        working_document = snapshot_document_at_version(document, version)
        version_state = version_state.model_copy(update={
            "number": version.number, "label": version.label, "created_at": version.created_at,
        })

    plan = None
    plan_source = working_document.latest_plan
    if plan_source is not None:
        data = dict(plan_source)
        data.pop("plan_hash", None)
        plan = PagePlan.model_validate(data)

    project_state = ProjectState(
        id=project.id, name=project.name, description=project.description,
        project_data=project.project_data,
        document_ids=tuple(d.id for d in project.documents),
        created_at=project.created_at, updated_at=project.updated_at,
    )

    brand_state = BrandState()
    if brand is not None:
        brand_state = BrandState(
            id=str(brand.brand_id), version=brand.version, name=brand.identity.name,
            tokens=brand.resolve_tokens().flat(),
        )

    own_state = tuple(_content_item_state(i, shared=False) for i in working_document.content_items)
    shared_state = tuple(_content_item_state(i, shared=True) for i in project.content_items)
    content_state = ContentState(
        own=own_state, shared_pool=shared_state, selected_shared_ids=working_document.content_selection,
    )

    document_type = None
    if working_document.document_type_id:
        try:
            document_type = get_document_type(working_document.document_type_id)
        except UnknownDocumentTypeError:
            document_type = None

    document_state = DocumentState(
        id=working_document.id, name=working_document.name,
        output_type=working_document.document_type_id,
        direction_id=working_document.direction_id,
        audience=document_type.audience if document_type else None,
        purpose=document_type.purpose if document_type else None,
        requested_structure=tuple(s.kind for s in working_document.sections),
        metadata=working_document.metadata,
        project_refs=working_document.project_refs,
    )

    direction = get_direction(working_document.direction_id)
    visual_language = VisualLanguageState(
        direction_id=direction.id, audience=direction.audience.value, goal=direction.goal.value,
        lead_with=direction.lead_with.value, narrative_order=tuple(r.value for r in direction.narrative_order),
        emphasis_ceiling=direction.emphasis_ceiling, text_density=direction.text_density,
        words_per_page_max=direction.words_per_page_max, image_ratio=direction.image_ratio,
        pacing=direction.pacing, display_step=direction.display_step, body_step=direction.body_step,
    )

    pages: tuple[PageState, ...] = ()
    components: tuple[ComponentState, ...] = ()
    layout = None
    if plan is not None:
        page_states = []
        component_states = []
        for page in plan.pages:
            component_ids = []
            for slot_index, slot in enumerate(page.slots):
                cid = f"{page.index}-{slot_index}"
                component_ids.append(cid)
                component_states.append(ComponentState(
                    id=cid, kind=_semantic_component_kind(slot.component), page_index=page.index,
                    block_id=slot.block, asset_id=slot.path if slot.component in
                    ("hero", "figure", "figure-a", "figure-b", "view") else "",
                ))
            page_states.append(PageState(
                id=f"page-{page.index}", index=page.index, purpose=page.archetype,
                width_mm=page.grid.page_width_mm, height_mm=page.grid.page_height_mm,
                component_ids=tuple(component_ids),
            ))
        pages = tuple(page_states)
        components = tuple(component_states)
        g = plan.pages[0].grid
        layout = LayoutState(
            columns=g.columns, gutter_mm=g.gutter_mm, margin_mm=g.margin_mm,
            baseline_mm=g.margin_mm, page_width_mm=g.page_width_mm, page_height_mm=g.page_height_mm,
        )

    findings = check_requirements(working_document, project)
    violated_ids = {f.rule for f in findings if f.rule}
    rules = []
    from brand.project.requirements import requirements_for
    from brand.validation.brand_validator import Severity

    _LEVEL = {Severity.BLOCK: ConstraintLevel.MUST, Severity.ERROR: ConstraintLevel.MUST,
              Severity.WARN: ConstraintLevel.SHOULD, Severity.INFO: ConstraintLevel.MAY}
    for requirement in requirements_for(working_document.document_type_id):
        rules.append(ConstraintRule(
            id=requirement.id, level=_LEVEL[requirement.severity], description=requirement.message,
            source="requirement", satisfied=requirement.id not in violated_ids,
        ))
    constraints = ConstraintState(rules=tuple(rules))

    assets = tuple(
        AssetState(id=a.id, filename=a.filename, content_type=a.content_type,
                   width_px=a.width_px, height_px=a.height_px)
        for a in project.assets
    )

    return DesignState(
        project=project_state, brand=brand_state, content=content_state, document=document_state,
        pages=pages, components=components, layout=layout, visual_language=visual_language,
        assets=assets, constraints=constraints, version=version_state,
    )
