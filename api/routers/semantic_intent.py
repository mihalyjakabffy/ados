"""
api/routers/semantic_intent.py

ADOS-M3.1 §12's API boundary — natural language in, a validated
``SemanticIntent`` out, nothing executed. This router holds no
extraction or validation logic of its own; it only resolves the
optional real context (a Project, its Brand, a Document's DesignState)
from ids the same way ``api/routers/ados_project.py``'s own
``get_design_state`` does, then calls straight into
``brand.llm.extractor.SemanticIntentExtractor`` — the one orchestrator,
not duplicated here.

Mounted at ``/api/v2`` root (this repository's convention for a
capability that is not itself project- or brand-scoped — see
``api/routers/brand.py``'s ``/brand-proposals``, the closest existing
sibling: brief in, structured proposal out, nothing written).
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["semantic-intent"])


class ConversationTurnRequest(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    text: str


class SemanticIntentRequest(BaseModel):
    #: The natural-language request to interpret. Required — there is no
    #: SemanticIntent without one.
    request: str = Field(min_length=1, max_length=4000)
    #: Real context, all optional. A bare request with none of these is
    #: an entirely ordinary M3.1 input (ADOS-M3.1 §7).
    project_id: Optional[str] = None
    document_id: Optional[str] = None
    #: Reads a specific saved Version's DesignState the same read-only
    #: way ``GET .../design-state`` does — never an auto-save.
    version: Optional[int] = None
    conversation: list[ConversationTurnRequest] = Field(default_factory=list)


def _resolve_context_objects(body: SemanticIntentRequest):
    """Real objects only — mirrors ados_project.get_design_state's own
    "brand is optional, project/document must exist if named" contract.
    Returns (project, brand, design_state), any of which may be None."""
    if not body.project_id:
        return None, None, None

    from api.routers import ados_project as ados_project_router
    from brand.project.store import ProjectNotFound

    try:
        project = ados_project_router._repo().get(body.project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    brand = None
    if project.brand_id:
        from brand.store.brand_repo import BrandNotFound

        try:
            brand = ados_project_router._brand_repo().get(project.brand_id, project.brand_version)
        except BrandNotFound:
            brand = None

    if not body.document_id:
        return project, brand, None

    from brand.design_state.build import build_design_state
    from brand.project.versioning import VersionNotFoundError

    idx = ados_project_router._document_index(project, body.document_id)
    document = project.documents[idx]
    try:
        design_state = build_design_state(
            project, document, brand, version_number=body.version,
            resolve_project=ados_project_router._resolve_ref_project,
        )
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return project, brand, design_state


@router.post("/intent/semantic")
def extract_semantic_intent(body: SemanticIntentRequest) -> dict[str, Any]:
    """Interpret one request. Never mutates anything, never executes a
    CommandIntent (ADOS-M3.1 §11) — the response is the validated
    SemanticIntent and its validation report, full stop."""
    from brand.llm.context import ConversationTurn
    from brand.llm.extractor import SemanticIntentExtractor

    project, brand, design_state = _resolve_context_objects(body)

    extractor = SemanticIntentExtractor()
    result = extractor.extract(
        body.request,
        project=project,
        brand=brand,
        design_state=design_state,
        conversation=tuple(
            ConversationTurn(role=t.role, text=t.text) for t in body.conversation
        ),
    )
    return {
        "intent": result.intent.to_dict(),
        "validation": result.validation.to_dict(),
        "request_id": result.trace.request_id,
        "provider": result.metadata.provider,
        "model": result.metadata.model,
    }


@router.get("/intent/semantic/schema")
def semantic_intent_schema() -> dict[str, Any]:
    """The JSON Schema for SemanticIntent — the same "generated from the
    model, not hand-duplicated" convention as ``GET /brand-schema``."""
    from brand.llm.semantic_intent import SCHEMA_VERSION, SemanticIntent

    return {"schema_version": SCHEMA_VERSION, "schema": SemanticIntent.model_json_schema()}


@router.get("/intent/semantic/traces")
def list_semantic_intent_traces(limit: int = 50) -> dict[str, Any]:
    """Developer-facing inspection (ADOS-M3.1 §20) — the most recent
    extractions this process has performed, newest first. In-memory
    only; see ``brand.llm.observability``'s own docstring for why."""
    from brand.llm.observability import recent_traces

    return {"traces": [t.to_dict() for t in recent_traces(limit=limit)]}


@router.get("/intent/semantic/traces/{request_id}")
def get_semantic_intent_trace(request_id: str) -> dict[str, Any]:
    from brand.llm.observability import get_trace

    trace = get_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"no trace {request_id!r} in this process's memory")
    return trace.to_dict()
