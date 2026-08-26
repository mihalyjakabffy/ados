"""
api/routers/content_intelligence.py

ADOS-M3.2 §25's API boundary — real project sources in, a validated
``ContentIntelligenceModel`` out, nothing executed. Mirrors
``api/routers/semantic_intent.py``'s own shape exactly: this router
holds no resolution logic of its own, only resolves real context
(a Project, optionally one of its Documents) from ids the same way
``ados_project.py``'s ``get_design_state`` does, then calls straight
into ``brand.llm.content.resolution.resolve_content`` — the one
orchestrator, not duplicated here.

Mounted at the same ``/api/v2/ados-projects`` prefix
``api/routers/ados_project.py`` itself uses (ADOS-M3.2 §25: "follow the
repository's architecture rather than blindly copying" the master
prompt's own suggested route) — a project's content is exactly as
project-scoped a concept as its DesignState.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["content-intelligence"])


class UserCorrectionRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: float | str | bool
    unit: str = ""


class RawDocumentRequest(BaseModel):
    """A source this repository has no real PDF/text-extraction pipeline
    for yet — a caller (a test, a future upload-and-extract flow) that
    already has plain text can still resolve content from it. See
    ``brand.llm.content.resolution``'s own docstring for the scoping
    this represents honestly rather than pretending to solve."""

    source_id: str = Field(default="", max_length=200)
    source_type: str = "uploaded_document"
    label: str = ""
    text: str = Field(min_length=1, max_length=20000)


class ResolveContentRequest(BaseModel):
    document_id: Optional[str] = None
    document_type_id: str = ""
    version: Optional[int] = None
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


@router.post("/{project_id}/content/resolve")
def resolve_project_content(project_id: str, body: ResolveContentRequest) -> dict[str, Any]:
    """Resolve everything ADOS actually knows about this project (and,
    when given, one of its documents) into a ContentIntelligenceModel.
    Never mutates anything, never produces a NarrativePlan, a
    DesignIntent, or a CommandIntent — ADOS-M3.2's own boundary."""
    import uuid as _uuid

    from brand.llm.content.resolution import resolve_content
    from brand.llm.content.validation import validate_content_model

    project, document = _load_project_and_document(project_id, body.document_id)
    request_id = _uuid.uuid4().hex

    content = resolve_content(
        project, document=document, document_type_id=body.document_type_id,
        version_number=body.version,
        user_corrections=tuple(c.model_dump() for c in body.user_corrections),
        raw_documents=tuple(d.model_dump() for d in body.raw_documents),
        request_id=request_id,
    )
    validation = validate_content_model(content, project)

    return {
        "content": content.to_dict(),
        "validation": validation.to_dict(),
        "request_id": request_id,
    }


@router.get("/content/schema")
def content_intelligence_schema() -> dict[str, Any]:
    from brand.llm.content.model import SCHEMA_VERSION, ContentIntelligenceModel

    return {"schema_version": SCHEMA_VERSION, "schema": ContentIntelligenceModel.model_json_schema()}


@router.get("/content/traces")
def list_content_traces(limit: int = 50) -> dict[str, Any]:
    from brand.llm.content.observability import recent_content_traces

    return {"traces": [t.to_dict() for t in recent_content_traces(limit=limit)]}


@router.get("/content/traces/{request_id}")
def get_content_trace_by_id(request_id: str) -> dict[str, Any]:
    from brand.llm.content.observability import get_content_trace

    trace = get_content_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"no trace {request_id!r} in this process's memory")
    return trace.to_dict()
