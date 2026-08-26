"""
api/routers/closed_loop.py

ADOS-M3.6's API boundary: the orchestrator (``brand.llm.loop.orchestrator``)
exposed over HTTP, following the same conventions
``api/routers/design_intent.py``/``api/routers/command.py`` already
established. Mirrors ``api/routers/ados_project.py``'s own
``compose_document``/``save_version`` persistence pattern exactly — a
new ``PagePlan`` and ``ProjectVersion`` are saved via the same
``_repo().save(project)`` call every other Project-mutating endpoint
uses, never a second write path.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

router = APIRouter(tags=["closed-loop"])


class UserCorrectionRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: float | str | bool
    unit: str = ""


class RawDocumentRequest(BaseModel):
    source_id: str = Field(default="", max_length=200)
    source_type: str = "uploaded_document"
    label: str = ""
    text: str = Field(min_length=1, max_length=20000)


class PolicyRequest(BaseModel):
    max_iterations: int = Field(default=5, ge=1, le=50)
    autonomy: str = "safe"
    max_llm_calls: int = Field(default=10, ge=0, le=100)
    allow_llm_recommendation: bool = True
    max_repeated_recommendation_attempts: int = Field(default=2, ge=1, le=10)


class StartLoopRequest(BaseModel):
    semantic_intent: dict[str, Any] = Field(default_factory=dict)
    document_type_id: str = ""
    compression: str = "medium"
    raw_documents: list[RawDocumentRequest] = Field(default_factory=list)
    user_corrections: list[UserCorrectionRequest] = Field(default_factory=list)
    policy: PolicyRequest = Field(default_factory=PolicyRequest)
    dry_run: bool = False


class ContinueLoopRequest(BaseModel):
    policy: PolicyRequest = Field(default_factory=PolicyRequest)
    dry_run: bool = False


class RunLoopRequest(StartLoopRequest):
    pass


class ApproveLoopRequest(BaseModel):
    command_ids: Optional[list[str]] = None


def _load_project_and_document(project_id: str, document_id: str):
    from api.routers import ados_project as ados_project_router
    from brand.project.store import ProjectNotFound

    try:
        project = ados_project_router._repo().get(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    idx = ados_project_router._document_index(project, document_id)
    return project, project.documents[idx]


def _load_brand(project) -> Any:
    from api.routers import ados_project as ados_project_router
    from brand.store.brand_repo import BrandNotFound

    if not project.brand_id:
        raise HTTPException(status_code=422, detail={"error": "no_brand_attached"})
    try:
        return ados_project_router._brand_repo().get(project.brand_id, project.brand_version)
    except BrandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _load_direction(document):
    from brand.creative.directions import get_direction

    try:
        return get_direction(document.direction_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "unknown_direction", "detail": str(exc)}) from exc


def _policy(body: PolicyRequest):
    from brand.llm.loop.model import IterationPolicy
    from brand.llm.loop.vocabulary import AutonomyLevel

    try:
        autonomy = AutonomyLevel(body.autonomy)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"unknown autonomy {body.autonomy!r} — expected one of {[a.value for a in AutonomyLevel]}",
        ) from exc
    return IterationPolicy(
        max_iterations=body.max_iterations, autonomy=autonomy, max_llm_calls=body.max_llm_calls,
        allow_llm_recommendation=body.allow_llm_recommendation,
        max_repeated_recommendation_attempts=body.max_repeated_recommendation_attempts,
    )


def _semantic_intent(raw: dict[str, Any]):
    from brand.llm.semantic_intent import SemanticIntent

    try:
        return SemanticIntent.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _compression(value: str):
    from brand.llm.narrative.vocabulary import NarrativeCompression

    try:
        return NarrativeCompression(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"unknown compression {value!r} — expected one of {[c.value for c in NarrativeCompression]}",
        ) from exc


def _initial_inputs(body: StartLoopRequest):
    from brand.llm.loop.orchestrator import InitialInputs

    return InitialInputs(
        semantic_intent=_semantic_intent(body.semantic_intent), document_type_id=body.document_type_id,
        compression=_compression(body.compression),
        raw_documents=tuple(d.model_dump() for d in body.raw_documents),
        user_corrections=tuple(c.model_dump() for c in body.user_corrections),
    )


def _persist(project) -> None:
    from api.routers import ados_project as ados_project_router

    ados_project_router._repo().save(project)


@router.post("/{project_id}/documents/{document_id}/loop/start")
def start_loop(project_id: str, document_id: str, body: StartLoopRequest) -> dict[str, Any]:
    """Runs the first iteration of a fresh lineage. 409s if this
    document already has one — use ``/loop/continue`` or ``/loop/run``,
    or start a lineage against a different document."""
    from brand.llm.loop.observability import get_lineage, record_iteration
    from brand.llm.loop.orchestrator import run_iteration

    project, document = _load_project_and_document(project_id, document_id)
    if get_lineage(project_id, document_id):
        raise HTTPException(status_code=409, detail={"error": "lineage_already_started"})

    brand = _load_brand(project)
    direction = _load_direction(document)
    iteration, new_project, _new_document = run_iteration(
        project, document, brand, direction,
        lineage=(), initial=_initial_inputs(body), policy=_policy(body.policy), dry_run=body.dry_run,
    )
    if not body.dry_run:
        record_iteration(iteration)
        _persist(new_project)
    return iteration.to_dict()


@router.post("/{project_id}/documents/{document_id}/loop/continue")
def continue_loop(project_id: str, document_id: str, body: ContinueLoopRequest) -> dict[str, Any]:
    """Runs the next iteration in an existing, still-open lineage."""
    from brand.llm.loop.observability import get_lineage, record_iteration
    from brand.llm.loop.orchestrator import run_iteration
    from brand.llm.loop.vocabulary import IterationStatus

    project, document = _load_project_and_document(project_id, document_id)
    lineage = get_lineage(project_id, document_id)
    if not lineage:
        raise HTTPException(status_code=404, detail={"error": "no_lineage", "detail": "call /loop/start first"})
    last = lineage[-1]
    if last.stop_reason is not None or last.status is IterationStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail={"error": "loop_not_continuable", "status": last.status.value,
                    "stop_reason": last.stop_reason.value if last.stop_reason else None},
        )

    brand = _load_brand(project)
    direction = _load_direction(document)
    iteration, new_project, _new_document = run_iteration(
        project, document, brand, direction,
        lineage=lineage, policy=_policy(body.policy), dry_run=body.dry_run,
    )
    if not body.dry_run:
        record_iteration(iteration)
        _persist(new_project)
    return iteration.to_dict()


@router.post("/{project_id}/documents/{document_id}/loop/run")
def run_full_loop(project_id: str, document_id: str, body: RunLoopRequest) -> dict[str, Any]:
    """Starts a fresh lineage and runs it to completion (ADOS-M3.6 §32) —
    the convenience "just do the whole loop" endpoint. 409s if a
    lineage already exists; call ``/loop/continue`` repeatedly instead."""
    from brand.llm.loop.observability import get_lineage, record_lineage
    from brand.llm.loop.orchestrator import run_loop

    project, document = _load_project_and_document(project_id, document_id)
    if get_lineage(project_id, document_id):
        raise HTTPException(status_code=409, detail={"error": "lineage_already_started"})

    brand = _load_brand(project)
    direction = _load_direction(document)
    iterations, new_project, _new_document = run_loop(
        project, document, brand, direction, initial=_initial_inputs(body), policy=_policy(body.policy),
    )
    record_lineage(iterations)
    _persist(new_project)
    last = iterations[-1]
    return {
        "iterations": [it.to_dict() for it in iterations],
        "final_status": last.status.value,
        "stop_reason": last.stop_reason.value if last.stop_reason else None,
        "total_llm_calls": sum(it.llm_calls for it in iterations),
    }


@router.post("/{project_id}/documents/{document_id}/loop/approve")
def approve_loop(project_id: str, document_id: str, body: ApproveLoopRequest) -> dict[str, Any]:
    """Approves and executes some or all of a pending
    ``AWAITING_APPROVAL`` iteration's commands (ADOS-M3.6 §37/§39)."""
    from brand.llm.loop.observability import get_lineage, replace_last_iteration
    from brand.llm.loop.orchestrator import resume_iteration
    from brand.llm.loop.vocabulary import IterationStatus

    project, document = _load_project_and_document(project_id, document_id)
    lineage = get_lineage(project_id, document_id)
    if not lineage or lineage[-1].status is not IterationStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=409, detail={"error": "nothing_awaiting_approval"})

    pending = lineage[-1]
    pending_ids = {c["id"] for c in pending.command_plan.get("commands", [])}
    approved = frozenset(body.command_ids) if body.command_ids is not None else frozenset(pending_ids)
    unknown = approved - pending_ids
    if unknown:
        raise HTTPException(status_code=404, detail={"error": "unknown_command_ids", "ids": sorted(unknown)})

    brand = _load_brand(project)
    direction = _load_direction(document)
    try:
        iteration, new_project, _new_document = resume_iteration(
            project, document, brand, direction, pending=pending, lineage=lineage, approved_command_ids=approved,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    replace_last_iteration(iteration)
    _persist(new_project)
    return iteration.to_dict()


@router.post("/{project_id}/documents/{document_id}/loop/stop")
def stop_loop(project_id: str, document_id: str) -> dict[str, Any]:
    """Marks the current lineage as user-stopped — ``/loop/continue``
    refuses to advance it further. Does not undo anything already
    executed and composed."""
    from datetime import datetime, timezone

    from brand.llm.loop.observability import get_lineage, replace_last_iteration
    from brand.llm.loop.vocabulary import IterationStatus, StopReason

    lineage = get_lineage(project_id, document_id)
    if not lineage:
        raise HTTPException(status_code=404, detail={"error": "no_lineage"})
    last = lineage[-1]
    if last.stop_reason is not None:
        return last.to_dict()
    stopped = last.model_copy(update={
        "status": IterationStatus.STOPPED, "stop_reason": StopReason.SUCCESS,
        "completed_at": datetime.now(timezone.utc),
    })
    replace_last_iteration(stopped)
    return stopped.to_dict()


@router.get("/{project_id}/documents/{document_id}/loop")
def loop_history(project_id: str, document_id: str) -> dict[str, Any]:
    from brand.llm.loop.observability import get_lineage

    _load_project_and_document(project_id, document_id)
    lineage = get_lineage(project_id, document_id)
    return {"iterations": [it.to_dict() for it in lineage]}


@router.get("/{project_id}/documents/{document_id}/loop/{iteration_id}")
def loop_iteration(project_id: str, document_id: str, iteration_id: str) -> dict[str, Any]:
    from brand.llm.loop.observability import get_iteration

    iteration = get_iteration(project_id, document_id, iteration_id)
    if iteration is None:
        raise HTTPException(status_code=404, detail=f"no iteration {iteration_id!r} in this process's memory")
    return iteration.to_dict()


@router.get("/{project_id}/documents/{document_id}/loop/{iteration_id}/trace")
def loop_iteration_trace(project_id: str, document_id: str, iteration_id: str) -> dict[str, Any]:
    """The decision trace ADOS-M3.6 §41 asks for: what this iteration
    knew, decided, and why — without the full embedded DesignIntent/
    CommandPlan/PagePlan payloads ``GET .../loop/{id}`` already returns
    in full."""
    from brand.llm.loop.observability import get_iteration

    iteration = get_iteration(project_id, document_id, iteration_id)
    if iteration is None:
        raise HTTPException(status_code=404, detail=f"no iteration {iteration_id!r} in this process's memory")
    return {
        "iteration_id": iteration.id,
        "sequence": iteration.sequence,
        "parent_iteration_id": iteration.parent_iteration_id,
        "trigger": iteration.trigger.value,
        "status": iteration.status.value,
        "stop_reason": iteration.stop_reason.value if iteration.stop_reason else None,
        "stage_log": list(iteration.stage_log),
        "design_intent_fingerprint": iteration.design_intent_fingerprint,
        "applied_recommendation": iteration.applied_recommendation.model_dump(mode="json") if iteration.applied_recommendation else None,
        "recommendations": [r.model_dump(mode="json") for r in iteration.recommendations],
        "skipped_recommendations": [s.model_dump(mode="json") for s in iteration.skipped_recommendations],
        "metrics": iteration.metrics.to_dict(),
        "llm_calls": iteration.llm_calls,
        "input_design_state_version": iteration.input_design_state_version,
        "output_design_state_version": iteration.output_design_state_version,
    }


@router.get("/loop/schema")
def loop_schema() -> dict[str, Any]:
    from brand.llm.loop.model import SCHEMA_VERSION, Iteration

    return {"schema_version": SCHEMA_VERSION, "iteration_schema": Iteration.model_json_schema()}
