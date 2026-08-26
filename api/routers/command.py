"""
api/routers/command.py

ADOS-M3.5's API boundary: a real ``DesignIntent`` (compiled fresh, the
same way ``api/routers/design_intent.py`` does) plus a real
``brand.content.model.ContentModel`` in, a validated
:class:`~brand.llm.command.model.CommandPlan` out — generation
separated from execution, exactly as the master prompt requires.

**Two different "content" objects meet at this boundary, and this
router is where that becomes visible.** ``brand.llm.content.model
.ContentIntelligenceModel`` (facts/claims/assets extracted from raw
text, M3.2's own output) is what ``plan_narrative``/``plan_design_intent``
consume — it has no id space in common with
``brand.content.model.ContentModel`` (the block model
``validate_intent``/``apply_intent``/``compose`` operate on; see
``brand/llm/command/__init__.py``'s own docstring for why no bridge
between the two exists yet). There is also no ``ContentModel`` store in
this repository (``api/routers/brand.py`` accepts one inline in every
request body for the same reason) — so ``/commands/generate`` and
``/commands/apply`` both require the caller to supply
``content_model`` explicitly, the same convention ``brand.py``'s
``/intent``/``/iterate`` endpoints already establish.

**Generation never applies.** ``/commands/generate`` calls
``brand.llm.command.planning.plan_commands`` and
``brand.llm.command.validation.validate_command_plan`` only.
``/commands/apply`` is the only endpoint in this router that calls the
real ``brand.creative.intent.apply_intent`` and
``brand.creative.composer.compose`` — the same two functions
``api/routers/brand.py``'s own ``/intent`` endpoint already calls, not a
second execution path.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

router = APIRouter(tags=["command-generation"])


class UserCorrectionRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: float | str | bool
    unit: str = ""


class RawDocumentRequest(BaseModel):
    source_id: str = Field(default="", max_length=200)
    source_type: str = "uploaded_document"
    label: str = ""
    text: str = Field(min_length=1, max_length=20000)


class GenerateCommandsRequest(BaseModel):
    semantic_intent: dict[str, Any] = Field(default_factory=dict)
    content_model: dict[str, Any] = Field(
        description="A brand.content.model.ContentModel payload — the real content "
        "blocks validate_intent()/apply_intent()/compose() operate on."
    )
    document_id: Optional[str] = None
    document_type_id: str = ""
    version: Optional[int] = None
    compression: str = "medium"
    user_corrections: list[UserCorrectionRequest] = Field(default_factory=list)
    raw_documents: list[RawDocumentRequest] = Field(default_factory=list)


class ValidateCommandPlanRequest(BaseModel):
    command_plan: dict[str, Any]
    content_model: dict[str, Any]
    page_count: Optional[int] = None
    current_design_state_version: Optional[int] = None


class ApplyCommandsRequest(BaseModel):
    command_plan: dict[str, Any]
    content_model: dict[str, Any]
    base_direction_id: Optional[str] = None
    base_direction: Optional[dict[str, Any]] = None
    base_plan: Optional[dict[str, Any]] = None
    page_format_name: str = "A4"
    #: Apply a subset, in the order given, rather than the whole plan —
    #: omit to apply every command on the plan, in its own order.
    command_ids: Optional[list[str]] = None


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


def _load_design_state(project, document, brand) -> Optional[Any]:
    from brand.design_state.build import build_design_state

    if document is None:
        return None
    try:
        return build_design_state(project, document, brand)
    except Exception:                                          # noqa: BLE001
        return None


@router.post("/{project_id}/commands/generate")
def generate_project_commands(project_id: str, body: GenerateCommandsRequest) -> dict[str, Any]:
    """Compile a freshly-resolved DesignIntent into a validated
    CommandPlan. Never applies a command, never calls compose() —
    ADOS-M3.5's own generation/execution separation."""
    import uuid as _uuid

    from brand.content.model import ContentModel
    from brand.llm.command.planning import plan_commands
    from brand.llm.command.validation import validate_command_plan
    from brand.llm.content.resolution import resolve_content
    from brand.llm.design.context import resolve_brand_capabilities
    from brand.llm.design.planning import plan_design_intent
    from brand.llm.design.validation import validate_design_intent
    from brand.llm.narrative.planning import plan_narrative
    from brand.llm.narrative.vocabulary import NarrativeCompression
    from brand.llm.semantic_intent import SemanticIntent
    from brand.creative.directions import get_direction

    project, document = _load_project_and_document(project_id, body.document_id)
    request_id = _uuid.uuid4().hex

    try:
        content_model = ContentModel.model_validate(body.content_model)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"error": "invalid_content_model", "errors": exc.errors()},
        ) from exc

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
    try:
        creative_direction = get_direction(document.direction_id) if document is not None else None
    except KeyError:
        creative_direction = None
    design_state = _load_design_state(project, document, brand)

    design_intent = plan_design_intent(
        project, content, narrative_plan, brand=brand, creative_direction=creative_direction,
        design_state=design_state, request_id=request_id,
    )
    design_validation = validate_design_intent(
        design_intent, narrative_plan, content, resolve_brand_capabilities(brand),
    )

    command_plan = plan_commands(
        design_intent, content_model, design_state=design_state, request_id=request_id,
    )
    page_count = len(design_state.pages) if design_state is not None else None
    current_version = design_state.version.number if design_state is not None else None
    command_validation = validate_command_plan(
        command_plan, content_model, page_count=page_count, current_design_state_version=current_version,
    )

    return {
        "command_plan": command_plan.to_dict(),
        "command_validation": command_validation.to_dict(),
        "design_intent": design_intent.to_dict(),
        "design_validation": design_validation.to_dict(),
        "request_id": request_id,
    }


@router.post("/{project_id}/commands/validate")
def validate_project_command_plan(project_id: str, body: ValidateCommandPlanRequest) -> dict[str, Any]:
    """Re-validate a CommandPlan the caller already has (e.g. one
    fetched from a trace) against a current content model / page count
    / DesignState version — the same independent re-check
    ``brand.llm.command.validation`` performs, callable on demand."""
    from brand.content.model import ContentModel
    from brand.llm.command.model import CommandPlan
    from brand.llm.command.validation import validate_command_plan

    try:
        content_model = ContentModel.model_validate(body.content_model)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"error": "invalid_content_model", "errors": exc.errors()},
        ) from exc
    try:
        plan = CommandPlan.model_validate(body.command_plan)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"error": "invalid_command_plan", "errors": exc.errors()},
        ) from exc

    validation = validate_command_plan(
        plan, content_model, page_count=body.page_count,
        current_design_state_version=body.current_design_state_version,
    )
    return {"validation": validation.to_dict()}


@router.post("/{project_id}/commands/apply")
def apply_project_commands(project_id: str, body: ApplyCommandsRequest) -> dict[str, Any]:
    """Apply some or all of a CommandPlan's commands, in order, via the
    real, existing ``validate_intent`` -> ``apply_intent`` -> ``compose``
    pipeline — the same two functions ``api/routers/brand.py``'s own
    ``/intent`` endpoint calls. Every command is re-validated
    immediately before it is applied; the first failure stops the
    sequence and returns everything applied up to that point, never a
    partial, unvalidated result silently swallowed."""
    from brand.content.model import ContentModel
    from brand.creative.composer import CompositionError, compose
    from brand.creative.direction import CreativeDirection
    from brand.creative.directions import get_direction
    from brand.creative.intent import IntentValidationError, apply_intent, validate_intent
    from brand.creative.plan import PagePlan
    from brand.llm.command.model import CommandExecutionStep, CommandPlan

    try:
        content = ContentModel.model_validate(body.content_model)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"error": "invalid_content_model", "errors": exc.errors()},
        ) from exc
    try:
        plan = CommandPlan.model_validate(body.command_plan)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"error": "invalid_command_plan", "errors": exc.errors()},
        ) from exc

    if bool(body.base_direction_id) == bool(body.base_direction):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_base_direction", "detail": "exactly one of base_direction_id or base_direction is required"},
        )
    try:
        direction = get_direction(body.base_direction_id) if body.base_direction_id else CreativeDirection.model_validate(body.base_direction)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "unknown_direction", "detail": str(exc)}) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_base_direction", "errors": exc.errors()}) from exc

    commands = plan.commands
    if body.command_ids is not None:
        by_id = {c.id: c for c in commands}
        missing = [cid for cid in body.command_ids if cid not in by_id]
        if missing:
            raise HTTPException(status_code=404, detail={"error": "unknown_command_ids", "ids": missing})
        commands = tuple(by_id[cid] for cid in body.command_ids)

    from api.routers import ados_project as ados_project_router
    brand = None
    if project_id:
        try:
            project = ados_project_router._repo().get(project_id)
            brand = _load_brand(project)
        except Exception:                                       # noqa: BLE001
            brand = None
    if brand is None:
        raise HTTPException(status_code=422, detail={"error": "no_brand", "detail": "the project has no resolvable brand to compose against"})

    current_plan_hash = ""
    if body.base_plan is not None:
        payload = dict(body.base_plan)
        payload.pop("plan_hash", None)
        try:
            current_plan_hash = PagePlan.model_validate(payload).plan_hash
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail={"error": "invalid_base_plan", "errors": exc.errors()}) from exc

    steps: list[CommandExecutionStep] = []
    new_plan: Optional[PagePlan] = None
    for command in commands:
        errors = validate_intent(content, command.intent, page_count=None)
        if errors:
            raise HTTPException(
                status_code=422,
                detail={"error": "intent_validation_failed", "command_id": command.id, "errors": errors},
            )
        try:
            new_content, new_direction, resolution = apply_intent(content, direction, command.intent)
        except IntentValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": "intent_validation_failed", "command_id": command.id, "errors": exc.errors},
            ) from exc

        content, direction = new_content, new_direction
        try:
            new_plan = compose(content, direction, brand, page_format_name=body.page_format_name)
        except CompositionError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": "composition_infeasible", "command_id": command.id, "detail": str(exc)},
            ) from exc

        steps.append(CommandExecutionStep(
            command_id=command.id, direction_changed=resolution.direction_changed,
            content_changed=resolution.content_changed, notes=resolution.notes,
            changed_pages=tuple(range(len(new_plan.pages))),
            plan_hash_before=current_plan_hash, plan_hash_after=new_plan.plan_hash,
        ))
        current_plan_hash = new_plan.plan_hash

    return {
        "steps": [s.model_dump(mode="json") for s in steps],
        "final_plan": new_plan.to_dict() if new_plan is not None else None,
        "final_direction_id": direction.id,
    }


@router.get("/commands/schema")
def commands_schema() -> dict[str, Any]:
    from brand.creative.intent import CommandIntent
    from brand.llm.command.model import SCHEMA_VERSION, CommandPlan

    return {
        "schema_version": SCHEMA_VERSION,
        "command_plan_schema": CommandPlan.model_json_schema(),
        "command_intent_schema": CommandIntent.model_json_schema(),
    }


@router.get("/commands/traces")
def list_command_traces(limit: int = 50) -> dict[str, Any]:
    from brand.llm.command.observability import recent_command_traces

    return {"traces": [t.to_dict() for t in recent_command_traces(limit=limit)]}


@router.get("/commands/traces/{request_id}")
def get_command_trace_by_id(request_id: str) -> dict[str, Any]:
    from brand.llm.command.observability import get_command_trace

    trace = get_command_trace(request_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"no trace {request_id!r} in this process's memory")
    return trace.to_dict()
