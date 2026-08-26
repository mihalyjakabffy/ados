"""
api/routers/design_intent.py

ADOS-M3.4's API boundary: a real ``SemanticIntent`` + real project
sources in, a validated ``DesignIntent`` out, nothing executed. Mirrors
``api/routers/narrative.py``'s own shape: this router holds no design
logic of its own, resolves content through the M3.2 pipeline, a
narrative plan through the M3.3 pipeline, and real Brand/
CreativeDirection/DesignState the same way ``ados_project.py`` already
does — then calls straight into
``brand.llm.design.planning.plan_design_intent``.

Mounted at the same ``/api/v2/ados-projects`` prefix
``content_intelligence.py``/``narrative.py`` already use.

**No ``GET /{project_id}/design/intent`` "current design intent"
endpoint.** Following ADOS-M3.3's own scoping decision (no
``NarrativePlan`` persistence — see that milestone's architecture doc),
a ``DesignIntent`` is not written into any project/document store by
this milestone either; every ``POST .../design/intent`` call is
independent, and the trace endpoints below are how a previous one
remains inspectable.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

router = APIRouter(tags=["design-intent"])


class UserCorrectionRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: float | str | bool
    unit: str = ""


class RawDocumentRequest(BaseModel):
    """See ``api.routers.content_intelligence.RawDocumentRequest`` —
    the identical shape, since this endpoint resolves content through
    the same M3.2 pipeline."""

    source_id: str = Field(default="", max_length=200)
    source_type: str = "uploaded_document"
    label: str = ""
    text: str = Field(min_length=1, max_length=20000)


class PlanDesignIntentRequest(BaseModel):
    semantic_intent: dict[str, Any] = Field(default_factory=dict)
    document_id: Optional[str] = None
    document_type_id: str = ""
    version: Optional[int] = None
    compression: str = "medium"
    user_corrections: list[UserCorrectionRequest] = Field(default_factory=list)
    raw_documents: list[RawDocumentRequest] = Field(default_factory=list)


def _load_project_and_document(project_id: str, document_id: Optional[str]):
    from api.routers import ados_project as ados_project_router
    from brand.project.store import ProjectNotFound

    try:
        project = ados_project_router._repo().get(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not document_id:
        return project, None

    idx = ados_project_router._document_index(project, document_id)
    return project, project.documents[idx]


def _load_brand(project) -> Optional[Any]:
    from api.routers import ados_project as ados_project_router
    from brand.store.brand_repo import BrandNotFound

    if not project.brand_id:
        return None
    try:
        return ados_project_router._brand_repo().get(project.brand_id, project.brand_version)
    except BrandNotFound:
        return None


def _load_creative_direction(document) -> Optional[Any]:
    from brand.creative.directions import get_direction

    if document is None:
        return None
    try:
        return get_direction(document.direction_id)
    except KeyError:
        return None


def _load_design_state(project, document, brand) -> Optional[Any]:
    from brand.design_state.build import build_design_state

    if document is None:
        return None
    try:
        return build_design_state(project, document, brand)
    except Exception:                                          # noqa: BLE001
        return None


@router.post("/{project_id}/design/intent")
def plan_project_design_intent(project_id: str, body: PlanDesignIntentRequest) -> dict[str, Any]:
    """Resolve a DesignIntent for this project's real narrative,
    brand, and creative direction. Never mutates anything, never
    produces or executes a CommandIntent, never produces a PagePlan,
    and never calls the Composer or a renderer — ADOS-M3.4's own
    boundary."""
    import uuid as _uuid

    from brand.llm.content.resolution import resolve_content
    from brand.llm.design.context import resolve_brand_capabilities
    from brand.llm.design.planning import plan_design_intent
    from brand.llm.design.validation import validate_design_intent
    from brand.llm.narrative.planning import plan_narrative
    from brand.llm.narrative.vocabulary import NarrativeCompression
    from brand.llm.semantic_intent import SemanticIntent

    project, document = _load_project_and_document(project_id, body.document_id)
    request_id = _uuid.uuid4().hex

    try:
        semantic_intent = SemanticIntent.model_validate(body.semantic_intent)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        compression = NarrativeCompression(body.compression)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"unknown compression {body.compression!r} — expected one of "
                   f"{[c.value for c in NarrativeCompression]}",
        ) from exc

    content = resolve_content(
        project, document=document, document_type_id=body.document_type_id,
        version_number=body.version,
        user_corrections=tuple(c.model_dump() for c in body.user_corrections),
        raw_documents=tuple(d.model_dump() for d in body.raw_documents),
        request_id=f"{request_id}-content",
    )
    narrative_plan = plan_narrative(
        project, content, semantic_intent, document_type_id=body.document_type_id,
        compression=compression, request_id=f"{request_id}-narrative",
    )

    brand = _load_brand(project)
    creative_direction = _load_creative_direction(document)
    design_state = _load_design_state(project, document, brand)

    design_intent = plan_design_intent(
        project, content, narrative_plan, brand=brand, creative_direction=creative_direction,
        design_state=design_state, request_id=request_id,
    )
    validation = validate_design_intent(
        design_intent, narrative_plan, content, resolve_brand_capabilities(brand),
    )

    return {
        "design_intent": design_intent.to_dict(),
        "narrative_plan": narrative_plan.to_dict(),
        "content": content.to_dict(),
        "validation": validation.to_dict(),
        "request_id": request_id,
    }


@router.get("/design/schema")
def design_intent_schema() -> dict[str, Any]:
    from brand.llm.design.model import SCHEMA_VERSION, DesignIntent

    return {"schema_version": SCHEMA_VERSION, "schema": DesignIntent.model_json_schema()}


@router.get("/design/traces")
def list_design_traces(limit: int = 50) -> dict[str, Any]:
    from brand.llm.design.observability import recent_design_traces

    return {"traces": [t.to_dict() for t in recent_design_traces(limit=limit)]}


@router.get("/design/traces/{request_id}")
def get_design_trace_by_id(request_id: str) -> dict[str, Any]:
    from brand.llm.design.observability import get_design_trace

    trace = get_design_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"no trace {request_id!r} in this process's memory")
    return trace.to_dict()
