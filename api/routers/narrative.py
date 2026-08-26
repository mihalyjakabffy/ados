"""
api/routers/narrative.py

ADOS-M3.3's API boundary: real ``SemanticIntent`` + real project sources
in, a validated ``NarrativePlan`` out, nothing executed. Mirrors
``api/routers/content_intelligence.py``'s own shape exactly: this
router holds no planning logic of its own, only resolves real context
(a Project, optionally one of its Documents) the same way that router
does, resolves content through the one real M3.2 pipeline
(``brand.llm.content.resolution.resolve_content`` — never a second
content-resolution system, ADOS-M3.3 §33), then calls straight into
``brand.llm.narrative.planning.plan_narrative``.

Mounted at the same ``/api/v2/ados-projects`` prefix
``api/routers/ados_project.py``/``content_intelligence.py`` already
use — a project's narrative plan is exactly as project-scoped a concept
as its ContentIntelligenceModel.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

router = APIRouter(tags=["narrative"])


class UserCorrectionRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: float | str | bool
    unit: str = ""


class RawDocumentRequest(BaseModel):
    """See ``api.routers.content_intelligence.RawDocumentRequest`` — the
    identical shape, since this endpoint resolves content through the
    same M3.2 pipeline and accepts the same simulated-source stand-in."""

    source_id: str = Field(default="", max_length=200)
    source_type: str = "uploaded_document"
    label: str = ""
    text: str = Field(min_length=1, max_length=20000)


class PlanNarrativeRequest(BaseModel):
    #: A SemanticIntent (ADOS-M3.1), given as its own JSON shape — this
    #: endpoint consumes an intent, it does not extract one from raw
    #: text (that is POST /intent/semantic's job).
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


@router.post("/{project_id}/narrative/plan")
def plan_project_narrative(project_id: str, body: PlanNarrativeRequest) -> dict[str, Any]:
    """Resolve a NarrativePlan for this project's real content, given a
    real SemanticIntent. Never mutates anything, never produces or
    executes a CommandIntent, never touches the Composer — ADOS-M3.3's
    own boundary."""
    import uuid as _uuid

    from brand.llm.content.resolution import resolve_content
    from brand.llm.narrative.planning import plan_narrative
    from brand.llm.narrative.validation import validate_narrative_plan
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

    plan = plan_narrative(
        project, content, semantic_intent, document_type_id=body.document_type_id,
        compression=compression, request_id=request_id,
    )
    validation = validate_narrative_plan(plan, content)

    return {
        "narrative_plan": plan.to_dict(),
        "content": content.to_dict(),
        "validation": validation.to_dict(),
        "request_id": request_id,
    }


@router.get("/narrative/schema")
def narrative_schema() -> dict[str, Any]:
    from brand.llm.narrative.model import SCHEMA_VERSION, NarrativePlan

    return {"schema_version": SCHEMA_VERSION, "schema": NarrativePlan.model_json_schema()}


@router.get("/narrative/traces")
def list_narrative_traces(limit: int = 50) -> dict[str, Any]:
    from brand.llm.narrative.observability import recent_narrative_traces

    return {"traces": [t.to_dict() for t in recent_narrative_traces(limit=limit)]}


@router.get("/narrative/traces/{request_id}")
def get_narrative_trace_by_id(request_id: str) -> dict[str, Any]:
    from brand.llm.narrative.observability import get_narrative_trace

    trace = get_narrative_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"no trace {request_id!r} in this process's memory")
    return trace.to_dict()
