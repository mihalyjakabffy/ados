"""
api/routers/brand.py

Brand System HTTP surface.
Prefix: /api/v2   Tags: ["brand"]

    GET  /brands                          list brands in the store
    POST /brands                          create a brand from a payload
    GET  /brands/{id}                     latest usable version
    GET  /brands/{id}/versions            the published lineage
    GET  /brands/{id}/versions/{version}  one exact version
    POST /brands/{id}/versions/{v}/approve
    POST /brands/{id}/versions/{v}/publish
    GET  /brands/{id}/tokens              resolved design tokens
    GET  /brands/{id}/validate            the validation report
    POST /brands/{id}/audit               audit a generated package on disk against this brand
    GET  /brands/{id}/preview             the brand preview, as HTML
    GET  /brands/{id}/templates           which documents this brand can render
    POST /brands/{id}/render/{template}   render one, HTML or PDF
    POST /brands/{id}/compose             ContentModel + direction → PagePlan
    POST /brands/{id}/intent              CommandIntent → PagePlan (M1.2, scoped since M1.3)
    POST /brands/{id}/iterate             review finding → recommended command → PagePlan (M1.4)
    POST /brand-proposals                 brief → BrandAgent proposal (no write)
    POST /brand-proposals/approve         a named human turns a proposal into a stored, approved brand
    GET  /brand-schema                    the JSON Schema

Two things this router does not do, deliberately:

* ``POST /brand-proposals`` **does not save**. The agent proposes; a human
  approves. Wiring the proposal endpoint straight into the store would make
  the approval step decorative.
* Nothing mutates a published version. The store raises and the handler turns
  that into a 409, because the alternative is a reprint that silently differs
  from what was issued.
* ``POST /brands/{id}/compose`` **does not compose**. It validates the
  request, resolves the Brand and its version, and calls
  ``brand.creative.composer.compose`` — the same deterministic function
  ``tests_brand/test_creative.py`` proves is byte-identical on rerun. This
  route is an adapter, not a second composition engine; if a plan looks
  wrong, the defect is in ``brand/creative/``, not here.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["brand"])

#: Where the file-backed store lives when no database is configured. The
#: Brand System is useful to a designer with no Postgres, and the API should
#: not be the reason they need one.
_BRAND_ROOT = os.environ.get("BRAND_STORAGE_ROOT", "storage/brands")


def _repo():
    from brand.store.brand_repo import FileBrandRepository

    return FileBrandRepository(_BRAND_ROOT)


def _seeded_repo():
    """The store, with the worked example present if it is otherwise empty.

    A fresh deployment with an empty brand store makes every endpoint 404 and
    the surface impossible to explore. Seeding the example once makes the API
    self-demonstrating; it is skipped as soon as a real brand exists.
    """
    repo = _repo()
    try:
        if not repo.list_brands():
            from brand.examples.studio_nord import STUDIO_NORD

            repo.save(STUDIO_NORD)
    except OSError as exc:                                 # read-only volume
        logger.info("brand store not writable (%s); serving read-only", exc)
    return repo


def _load(brand_id: str, version: Optional[str] = None):
    from brand.store.brand_repo import BrandNotFound

    try:
        return _seeded_repo().get(brand_id, version)
    except (BrandNotFound, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class BriefRequest(BaseModel):
    brief: str = Field(min_length=1, max_length=4000)
    name: Optional[str] = Field(default=None, max_length=120)


class ApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=120)
    changelog: str = Field(default="", max_length=1000)


class RenderRequest(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-project token overrides. May change a value, never "
        "introduce a token the brand does not define.",
    )


class ComposeRequest(BaseModel):
    """Input to ``brand.creative.composer.compose``, over the wire.

    ``content_model`` is the whole project's content, inline. There is no
    ContentModel store yet (``brand/content/extract.py`` only turns a
    DesignState into one in-process), so the caller supplies it directly —
    the same shape ``brand.content.model.ContentModel.model_validate``
    already accepts, not a shape invented for this endpoint.

    ``direction_id`` selects one of the three shipped, reviewed directions
    (``brand.creative.directions.DIRECTIONS``) rather than accepting an
    arbitrary inline ``CreativeDirection`` — directions are meant to be
    "a starting set to be edited and locked, not a menu browsed per
    document" (``brand/creative/directions.py``), and opening free-form
    direction authoring through this route is a separate decision.
    """

    content_model: dict[str, Any] = Field(
        description="A brand.content.model.ContentModel payload."
    )
    direction_id: str = Field(min_length=1, max_length=40)
    document: str = Field(
        default="", max_length=60,
        description="Which of the direction's applies_to document types this "
        "run is for. Defaults to the direction's first.",
    )
    page_format_name: str = Field(default="A4", max_length=20)
    max_pages: int = Field(default=40, ge=1, le=200)


class IntentRequest(BaseModel):
    """Input to ``brand.creative.intent`` — a structured command, not a compose call.

    Exactly one of ``base_direction_id`` / ``base_direction`` must be set:
    the former starts from one of the three shipped directions, the
    latter carries forward a direction a *previous* intent call already
    returned (``resulting_direction`` in that response), so a sequence of
    commands can chain — "reduce density" then "increase image emphasis"
    on top of the result — without this route storing any session state.
    """

    content_model: dict[str, Any]
    base_direction_id: Optional[str] = Field(default=None, max_length=40)
    base_direction: Optional[dict[str, Any]] = None
    intent: dict[str, Any] = Field(description="A brand.creative.intent.CommandIntent payload.")
    previous_plan_hash: str = Field(default="", max_length=64)
    document: str = Field(default="", max_length=60)
    page_format_name: str = Field(default="A4", max_length=20)
    max_pages: int = Field(default=40, ge=1, le=200)
    base_plan: Optional[dict[str, Any]] = Field(
        default=None,
        description="A previous call's 'plan' payload (PagePlan.to_dict()). "
        "When present, the intent's target — read from intent.target, not "
        "from a separate field — genuinely bounds the recomposition via "
        "brand.creative.scope: a page target leaves every other page "
        "byte-identical, instead of the whole-document recomposition M1.2 "
        "always did. Omit it to keep exactly that M1.2 behaviour.",
    )


class IterateRequest(BaseModel):
    """Input to ``brand.creative.iterate`` — one review-driven iteration.

    Unlike ``IntentRequest``, ``base_plan`` is required: an iteration only
    exists in response to something a review of an actual PagePlan found.
    The server re-reviews ``base_plan`` itself and looks up the matching
    ``brand.validation.brand_validator.Finding`` — the client points at a
    finding, it does not assert one.

    ``finding_code`` + ``target_page`` (M1.4): name one specific finding
    explicitly. Both or neither — naming only one is a 422.

    Omitting both (M1.5): the server picks deterministically, across
    *every* finding the review of ``base_plan`` produced, via
    ``brand.creative.iterate.select_recommendation`` — the same ranking
    (severity, then deviation from threshold, then finding code, then
    page index) either way; explicit mode just narrows the candidate pool
    to one finding first.

    ``history`` (M1.5, optional): the lineage's own prior
    ``IterationHistoryEntry`` results, carried by the caller the same way
    ``base_plan`` already is — there is no server-side session. Passing it
    lets ``select_recommendation`` skip a capability already proven
    ``no_improvement``/``failed`` for this exact finding, instead of
    recommending the same ineffective command again. Omitting it (or
    leaving it empty) reproduces exactly M1.4's behaviour: nothing is
    excluded.
    """

    content_model: dict[str, Any]
    base_direction_id: Optional[str] = Field(default=None, max_length=40)
    base_direction: Optional[dict[str, Any]] = None
    base_plan: dict[str, Any] = Field(
        description="A previous call's 'plan' payload (PagePlan.to_dict())."
    )
    finding_code: Optional[str] = Field(default=None, min_length=1, max_length=60)
    target_page: Optional[int] = Field(default=None, ge=0)
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Prior IterationHistoryEntry results for this lineage, oldest first.",
    )
    previous_plan_hash: str = Field(default="", max_length=64)
    page_format_name: str = Field(default="A4", max_length=20)


# ---------------------------------------------------------------------------
# Brands
# ---------------------------------------------------------------------------


@router.get("/brands")
def list_brands() -> dict[str, Any]:
    rows = _seeded_repo().list_brands()
    return {
        "brands": [
            {"brand_id": bid, "name": name, "latest_version": version}
            for bid, name, version in rows
        ]
    }


@router.post("/brands", status_code=201)
def create_brand(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    from brand.models.brand import Brand
    from brand.schemas.brand_schema import SchemaValidationError, validate_payload

    try:
        validate_payload(payload)
        brand = Brand.model_validate(payload).with_content_hash()
    except SchemaValidationError as exc:
        raise HTTPException(status_code=422, detail={"schema_errors": exc.errors}) from exc
    except Exception as exc:                               # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    report = brand.check()
    try:
        _repo().save(brand)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "brand_id": str(brand.brand_id),
        "version": brand.version,
        "status": brand.status.value,
        "validation": report.to_dict(),
    }


@router.get("/brands/{brand_id}")
def get_brand(brand_id: str, version: Optional[str] = Query(default=None)) -> dict:
    return _load(brand_id, version).model_dump(mode="json")


@router.get("/brands/{brand_id}/versions")
def list_versions(brand_id: str) -> dict[str, Any]:
    from brand.store.brand_repo import BrandNotFound

    try:
        history = _seeded_repo().history(brand_id)
    except (BrandNotFound, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    latest = history.latest()
    return {
        "brand_id": brand_id,
        "versions": [
            {
                "version": v,
                "status": history.get(v).status.value,
                "content_hash": history.get(v).content_hash,
                "changelog": history.get(v).changelog,
            }
            for v in history.versions()
        ],
        "latest_usable": latest.version if latest else None,
    }


@router.get("/brands/{brand_id}/versions/{version}")
def get_version(brand_id: str, version: str) -> dict:
    return _load(brand_id, version).model_dump(mode="json")


@router.post("/brands/{brand_id}/versions/{version}/approve")
def approve_version(brand_id: str, version: str, body: ApprovalRequest) -> dict:
    brand = _load(brand_id, version)
    report = brand.check()
    if not report.ok:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "brand does not validate and cannot be approved",
                "validation": report.to_dict(),
            },
        )
    approved = brand.approved(changelog=body.changelog)
    _repo().save(approved)
    logger.info("brand %s %s approved by %s", brand_id, version, body.approved_by)
    return {"brand_id": brand_id, "version": version,
            "status": approved.status.value}


@router.post("/brands/{brand_id}/versions/{version}/publish")
def publish_version(brand_id: str, version: str) -> dict:
    brand = _load(brand_id, version)
    try:
        published = brand.published()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _repo().save(published)
    return {"brand_id": brand_id, "version": version,
            "status": published.status.value}


# ---------------------------------------------------------------------------
# Tokens, validation, preview
# ---------------------------------------------------------------------------


@router.get("/brands/{brand_id}/tokens")
def get_tokens(
    brand_id: str,
    version: Optional[str] = Query(default=None),
    flat: bool = Query(default=False, description="Values only, no provenance."),
) -> dict:
    tokens = _load(brand_id, version).resolve_tokens()
    return tokens.flat() if flat else tokens.to_json_dict()


@router.get("/brands/{brand_id}/validate")
def validate_brand(brand_id: str, version: Optional[str] = Query(default=None)) -> dict:
    return _load(brand_id, version).check().to_dict()


class AuditPackageRequest(BaseModel):
    #: A server-local directory of already-generated brand artefacts
    #: (the output of e.g. ``python -m brand.cli package`` / ``export``) —
    #: the same posture the CLI's own ``audit <package-dir> --brand``
    #: command already has, and the same trust boundary every endpoint in
    #: this milestone runs under (docs/architecture/m4-claude-connector.md
    #: §12: no auth yet, local-equivalent trust only).
    package_dir: str = Field(min_length=1, max_length=500)


@router.post("/brands/{brand_id}/audit")
def audit_brand_package(
    brand_id: str, body: AuditPackageRequest, version: Optional[str] = Query(default=None)
) -> dict:
    """Audits a *generated package on disk* against this brand
    (``brand.validation.consistency.audit_package``, unchanged) —
    a separable, later question from ``GET .../validate``'s "is the
    brand itself sound": this checks that files already on disk (colour,
    font, layout custom properties, the asset inventory) actually derive
    from the brand they claim to come from, catching planted colours,
    undeclared font families and assets missing an inventory record."""
    from pathlib import Path

    from brand.validation.consistency import audit_package

    brand = _load(brand_id, version)
    package_root = Path(body.package_dir)
    if not package_root.is_dir():
        raise HTTPException(
            status_code=404, detail={"error": "package_dir_not_found", "path": body.package_dir},
        )
    return audit_package(package_root, brand).to_dict()


@router.get("/brands/{brand_id}/preview", response_class=HTMLResponse)
def preview(brand_id: str, version: Optional[str] = Query(default=None)) -> HTMLResponse:
    from brand.preview.brand_preview import render_preview

    return HTMLResponse(content=render_preview(_load(brand_id, version)))


@router.get("/brands/{brand_id}/templates")
def brand_templates(brand_id: str, version: Optional[str] = Query(default=None)) -> dict:
    from brand.templates.document_templates import TEMPLATES, coverage

    tokens = _load(brand_id, version).resolve_tokens()
    cov = coverage(tokens)
    return {
        "templates": [
            {
                "template_id": tid,
                "title": TEMPLATES[tid].title,
                "family": TEMPLATES[tid].family.value,
                "medium": TEMPLATES[tid].medium.value,
                "renders": not missing,
                "missing_tokens": missing,
            }
            for tid, missing in sorted(cov.items())
        ]
    }


@router.post("/brands/{brand_id}/render/{template_id}")
def render_document(
    brand_id: str,
    template_id: str,
    body: RenderRequest,
    version: Optional[str] = Query(default=None),
) -> Response:
    from brand.models.tokens import UndefinedTokenError
    from brand.templates.document_templates import Medium, get_template
    from brand.templates.renderers import render_sheet_pdf

    brand = _load(brand_id, version)
    try:
        template = get_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        tokens = brand.resolve_tokens(**body.overrides)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        if template.medium is Medium.PDF:
            doc = render_sheet_pdf(template, tokens, brand=brand, **body.context)
        else:
            doc = template.render(tokens, **body.context)
    except UndefinedTokenError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    content = doc.content if isinstance(doc.content, bytes) else doc.content.encode()
    return Response(content=content, media_type=doc.media_type)


# ---------------------------------------------------------------------------
# Composition — the Creative Layer, exposed
# ---------------------------------------------------------------------------


@router.post("/brands/{brand_id}/compose")
def compose_document(
    brand_id: str,
    body: ComposeRequest,
    version: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """Compose a PagePlan. See the module docstring: this holds no layout logic.

    Pipeline: resolve Brand + version (``_load``, existing) → validate the
    ContentModel → resolve the CreativeDirection by id → ``compose()``
    (``brand.creative.composer``, existing, deterministic) → ``evaluate()``
    (``brand.creative.evaluate``, existing) → response.

    The response separates the deterministic payload from request-scoped
    metadata: ``plan`` is exactly ``PagePlan.to_dict()`` — the same bytes for
    the same inputs, always — and ``meta`` carries only things that must
    *not* affect that determinism, such as when this particular call was
    made. Nothing in ``meta`` is folded into ``plan_hash``.
    """
    import datetime as _dt

    from pydantic import ValidationError

    from brand.content.model import ContentModel
    from brand.creative.composer import CompositionError, compose
    from brand.creative.directions import get_direction
    from brand.creative.evaluate import evaluate

    brand = _load(brand_id, version)

    try:
        content = ContentModel.model_validate(body.content_model)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_content_model", "errors": exc.errors()},
        ) from exc

    try:
        direction = get_direction(body.direction_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_direction", "detail": str(exc)},
        ) from exc

    if body.document and direction.applies_to and body.document not in direction.applies_to:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "document_not_in_direction",
                "detail": (
                    f"direction {direction.id!r} applies to "
                    f"{list(direction.applies_to)}, not {body.document!r}."
                ),
            },
        )

    try:
        plan = compose(
            content,
            direction,
            brand,
            document=body.document,
            page_format_name=body.page_format_name,
            max_pages=body.max_pages,
        )
    except CompositionError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "composition_infeasible", "detail": str(exc)},
        ) from exc

    evaluation = evaluate(plan, direction, brand.resolve_tokens())

    return {
        "plan": plan.to_dict(),
        "evaluation": evaluation.to_dict(),
        "meta": {
            "requested_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "brand_id": str(brand.brand_id),
            "brand_version": brand.version,
            "composer": "brand.creative.composer.compose",
        },
    }


# ---------------------------------------------------------------------------
# Intent — a structured command applied through the existing Composer
#
# User command -> CommandIntent -> validate_intent -> apply_intent ->
# compose() (existing, unmodified) -> evaluate() (existing, unmodified).
# This handler holds no layout logic; brand/creative/intent.py holds no
# layout logic either — see its module docstring.
# ---------------------------------------------------------------------------


@router.post("/brands/{brand_id}/intent")
def execute_intent(
    brand_id: str,
    body: IntentRequest,
    version: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """Apply one structured CommandIntent and recompose.

    On any validation failure — the intent, the content, the target, or
    the resulting direction — nothing is composed and no plan is
    returned; the caller keeps whatever PagePlan it already had. A
    ``CompositionError`` from ``compose()`` is reported the same way, with
    ``previous_plan_hash`` echoed back so the frontend knows unambiguously
    which plan is still current.

    When ``body.base_plan`` is supplied, the intent's ``target`` is resolved
    to a real :class:`brand.creative.scope.CompositionScope` and
    ``brand.creative.scope.compose_scoped`` is used instead of a raw
    ``compose()`` call: a ``page`` (or ``contentBlock``, which resolves to
    its page) target then leaves every other page of the plan byte-for-byte
    unchanged, and the response carries the resolved scope plus a
    ``PagePlanDiff`` so the caller never has to infer what changed by
    comparing plans itself. A ``region`` target is refused with
    ``unsupported_scope`` — there is no smaller addressable unit than a page
    to resolve it to — and a scope that cannot stay inside its bound (the
    target page's content no longer fits as one page under the change) is
    refused with ``scope_infeasible``, both leaving the previous plan
    untouched. Omitting ``base_plan`` keeps exactly the M1.2 behaviour: the
    whole document is recomposed, with no scope, resolved_scope or diff in
    the response.
    """
    import datetime as _dt

    from pydantic import ValidationError

    from brand.content.model import ContentModel
    from brand.creative.composer import CompositionError, compose
    from brand.creative.direction import CreativeDirection
    from brand.creative.directions import get_direction
    from brand.creative.evaluate import evaluate
    from brand.creative.intent import (
        CommandIntent,
        IntentValidationError,
        apply_intent,
        validate_intent,
    )
    from brand.creative.plan import PagePlan
    from brand.creative.scope import (
        CompositionScope,
        ScopeInfeasibleError,
        ScopeType,
        UnsupportedScopeError,
        compose_scoped,
    )

    brand = _load(brand_id, version)

    try:
        content = ContentModel.model_validate(body.content_model)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_content_model", "errors": exc.errors()},
        ) from exc

    base_plan_obj: Optional[PagePlan] = None
    if body.base_plan is not None:
        # PagePlan.to_dict() adds a derived 'plan_hash' key the frozen,
        # extra="forbid" schema does not itself declare — the same
        # round-trip pitfall ContentModel.to_dict() has; drop it rather
        # than asking every caller to remember to strip it.
        payload = dict(body.base_plan)
        payload.pop("plan_hash", None)
        try:
            base_plan_obj = PagePlan.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail={"error": "invalid_base_plan", "errors": exc.errors()},
            ) from exc

    if bool(body.base_direction_id) == bool(body.base_direction):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_base_direction",
                "detail": "exactly one of base_direction_id or base_direction is required",
            },
        )

    try:
        if body.base_direction_id:
            base_direction = get_direction(body.base_direction_id)
        else:
            base_direction = CreativeDirection.model_validate(body.base_direction)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_direction", "detail": str(exc)},
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_base_direction", "errors": exc.errors()},
        ) from exc

    try:
        intent = CommandIntent.model_validate(body.intent)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_intent", "errors": exc.errors()},
        ) from exc

    domain_errors = validate_intent(
        content, intent,
        page_count=len(base_plan_obj.pages) if base_plan_obj is not None else None,
    )
    if domain_errors:
        raise HTTPException(
            status_code=422,
            detail={"error": "intent_validation_failed", "errors": domain_errors},
        )

    try:
        new_content, new_direction, resolution = apply_intent(content, base_direction, intent)
    except IntentValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "intent_validation_failed", "errors": exc.errors},
        ) from exc

    scope: Optional[CompositionScope] = None
    resolved_scope: Optional[CompositionScope] = None
    diff = None

    if base_plan_obj is not None:
        scope = CompositionScope(type=ScopeType(intent.target.type.value), id=intent.target.id)
        try:
            plan, diff, resolved_scope = compose_scoped(
                base_plan_obj,
                scope,
                new_content,
                new_direction,
                brand,
                page_format_name=body.page_format_name,
            )
        except UnsupportedScopeError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "unsupported_scope",
                    "detail": str(exc),
                    "previous_plan_hash": body.previous_plan_hash,
                },
            ) from exc
        except ScopeInfeasibleError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "scope_infeasible",
                    "detail": str(exc),
                    "previous_plan_hash": body.previous_plan_hash,
                },
            ) from exc
        except CompositionError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "composition_infeasible",
                    "detail": str(exc),
                    "previous_plan_hash": body.previous_plan_hash,
                },
            ) from exc

        if resolved_scope.type is ScopeType.PAGE:
            # apply_intent's own note is honestly true of compose() alone —
            # compose_scoped just made it false for this call by actually
            # bounding the change to the target page.
            resolution = resolution.model_copy(
                update={
                    "notes": tuple(
                        n for n in resolution.notes if "applies document-wide" not in n
                    )
                }
            )
    else:
        try:
            plan = compose(
                new_content,
                new_direction,
                brand,
                document=body.document,
                page_format_name=body.page_format_name,
                max_pages=body.max_pages,
            )
        except CompositionError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "composition_infeasible",
                    "detail": str(exc),
                    "previous_plan_hash": body.previous_plan_hash,
                },
            ) from exc

    evaluation = evaluate(plan, new_direction, brand.resolve_tokens())

    return {
        "intent": intent.model_dump(mode="json"),
        "resolution": resolution.model_dump(mode="json"),
        "resulting_direction": new_direction.model_dump(mode="json"),
        "plan": plan.to_dict(),
        "scope": scope.model_dump(mode="json") if scope is not None else None,
        "resolved_scope": resolved_scope.model_dump(mode="json") if resolved_scope is not None else None,
        "diff": diff.model_dump(mode="json") if diff is not None else None,
        "evaluation": evaluation.to_dict(),
        "meta": {
            "requested_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "brand_id": str(brand.brand_id),
            "brand_version": brand.version,
            "previous_plan_hash": body.previous_plan_hash,
            "composer": (
                "brand.creative.intent.apply_intent + brand.creative.scope.compose_scoped"
                if base_plan_obj is not None
                else "brand.creative.intent.apply_intent + brand.creative.composer.compose"
            ),
        },
    }


# ---------------------------------------------------------------------------
# Iterate — one review-driven closed-loop iteration (M1.4), generalised to
# many findings and a caller-carried history (M1.5)
#
# PagePlan -> evaluate() -> Finding(s) -> select_recommendation()
#          -> CommandIntent -> validate_intent() -> apply_intent()
#          -> compose_scoped() -> PagePlan' -> evaluate()
#
# This handler holds no layout, review, ranking or recommendation logic of
# its own — see brand/creative/iterate.py's module docstring. It re-reviews
# base_plan itself rather than trusting a client-supplied finding, and every
# step past selection is the same brand.creative.intent +
# brand.creative.scope pipeline POST /intent already uses; there is no
# second mutation engine.
# ---------------------------------------------------------------------------


@router.post("/brands/{brand_id}/iterate")
def execute_iteration(
    brand_id: str,
    body: IterateRequest,
    version: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """Apply one deterministic, review-recommended CommandIntent and recompose.

    ``finding_code`` + ``target_page`` name a finding from reviewing
    ``base_plan`` — the server re-runs that review itself and looks up the
    matching finding, rather than accepting one the client asserts. On any
    failure — an unknown finding, one with no command mapping, a domain
    validation error, an unsupported or infeasible scope, or a command that
    executed but did not move the finding's own metric in the promised
    direction — nothing is composed and no plan is returned; the caller
    keeps whatever PagePlan it already had, with ``previous_plan_hash``
    echoed back so it knows unambiguously which plan is still current.
    """
    import datetime as _dt

    from pydantic import ValidationError

    from brand.content.model import ContentModel
    from brand.creative.composer import CompositionError
    from brand.creative.direction import CreativeDirection
    from brand.creative.directions import get_direction
    from brand.creative.evaluate import evaluate
    from brand.creative.intent import IntentValidationError
    from brand.creative.iterate import (
        IterationHistoryEntry,
        IterationNoImprovementError,
        NoRecommendationError,
        explain,
        iterate,
        select_recommendation,
    )
    from brand.creative.plan import PagePlan
    from brand.creative.scope import ScopeInfeasibleError, UnsupportedScopeError

    brand = _load(brand_id, version)

    try:
        content = ContentModel.model_validate(body.content_model)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_content_model", "errors": exc.errors()},
        ) from exc

    # Same round-trip pitfall as /intent's base_plan: PagePlan.to_dict()
    # adds a derived 'plan_hash' key the frozen, extra="forbid" schema does
    # not itself declare.
    plan_payload = dict(body.base_plan)
    plan_payload.pop("plan_hash", None)
    try:
        base_plan = PagePlan.model_validate(plan_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_base_plan", "errors": exc.errors()},
        ) from exc

    if bool(body.base_direction_id) == bool(body.base_direction):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_base_direction",
                "detail": "exactly one of base_direction_id or base_direction is required",
            },
        )

    try:
        if body.base_direction_id:
            base_direction = get_direction(body.base_direction_id)
        else:
            base_direction = CreativeDirection.model_validate(body.base_direction)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_direction", "detail": str(exc)},
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_base_direction", "errors": exc.errors()},
        ) from exc

    if bool(body.finding_code) != bool(body.target_page is not None):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_target",
                "detail": "finding_code and target_page must both be set (name one finding) "
                "or both omitted (let the server pick, M1.5)",
                "previous_plan_hash": body.previous_plan_hash,
            },
        )

    try:
        history = tuple(IterationHistoryEntry.model_validate(h) for h in body.history)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_history", "errors": exc.errors()},
        ) from exc

    tokens = brand.resolve_tokens()
    before_evaluation = evaluate(base_plan, base_direction, tokens)
    findings = before_evaluation.report.findings

    if body.finding_code is not None:
        pool = [f for f in findings if f.code == body.finding_code and f.page_index == body.target_page]
        if not pool:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "finding_not_found",
                    "detail": (
                        f"no finding {body.finding_code!r} on page {body.target_page} "
                        f"in the current review of base_plan"
                    ),
                    "previous_plan_hash": body.previous_plan_hash,
                },
            )
    else:
        # M1.5 auto-select: rank across every finding the review produced,
        # not just one the caller already picked out.
        pool = findings

    try:
        recommendation = select_recommendation(pool, history=history)
    except NoRecommendationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_recommendation",
                "detail": str(exc),
                "previous_plan_hash": body.previous_plan_hash,
            },
        ) from exc

    finding = next(
        f for f in findings
        if f.code == recommendation.finding_code and f.page_index == recommendation.target_page
    )

    try:
        result = iterate(
            base_plan, finding, content, base_direction, brand,
            tokens=tokens, page_format_name=body.page_format_name,
        )
    except NoRecommendationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_recommendation",
                "detail": str(exc),
                "previous_plan_hash": body.previous_plan_hash,
            },
        ) from exc
    except IntentValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "intent_validation_failed",
                "errors": exc.errors,
                "previous_plan_hash": body.previous_plan_hash,
            },
        ) from exc
    except UnsupportedScopeError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "unsupported_scope",
                "detail": str(exc),
                "previous_plan_hash": body.previous_plan_hash,
            },
        ) from exc
    except ScopeInfeasibleError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "scope_infeasible",
                "detail": str(exc),
                "previous_plan_hash": body.previous_plan_hash,
            },
        ) from exc
    except CompositionError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "composition_infeasible",
                "detail": str(exc),
                "previous_plan_hash": body.previous_plan_hash,
            },
        ) from exc
    except IterationNoImprovementError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_improvement",
                "detail": str(exc),
                "outcome": exc.outcome.value,
                # The attempted recommendation, echoed back — the caller
                # was never returned one (the call failed), but needs it to
                # record an accurate IterationHistoryEntry so this exact
                # capability is not blindly retried (ADOS-M1.5 §13).
                "recommendation": recommendation.model_dump(mode="json"),
                "before_metric": exc.before,
                "after_metric": exc.after,
                "previous_plan_hash": body.previous_plan_hash,
            },
        ) from exc

    return {
        # Every finding the review produced, not only the one acted on —
        # ADOS-M1.5 §16: the non-selected findings are never hidden.
        "findings": [f.to_dict() for f in findings],
        "finding": result.finding,
        "recommendation": result.recommendation.model_dump(mode="json"),
        "explanation": explain(finding, result.recommendation),
        "intent": result.intent.model_dump(mode="json"),
        "resolution": result.resolution.model_dump(mode="json"),
        "resolved_scope": result.resolved_scope.model_dump(mode="json"),
        "diff": result.diff.model_dump(mode="json"),
        "metric": result.metric,
        "before_metric": result.before_metric,
        "after_metric": result.after_metric,
        "outcome": result.outcome.value,
        "plan": result.plan.to_dict(),
        "before_evaluation": result.before_evaluation,
        "after_evaluation": result.after_evaluation,
        "meta": {
            "requested_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "brand_id": str(brand.brand_id),
            "brand_version": brand.version,
            "previous_plan_hash": body.previous_plan_hash,
            "composer": "brand.creative.iterate.iterate",
        },
    }


# ---------------------------------------------------------------------------
# Dev utilities — content examples
#
# Not a ContentModel store (that is a separate, later decision — M2.2's
# project-content graph). This exists so a caller can exercise POST
# /compose with a real, repository-shipped ContentModel instead of hand
# -authoring one, while nothing here persists anything.
# ---------------------------------------------------------------------------

_CONTENT_EXAMPLES = ("malthouse",)


@router.get("/dev/content-examples/{name}")
def dev_content_example(name: str) -> dict[str, Any]:
    """Returns a round-trippable ContentModel payload.

    Deliberately ``model_dump``, not ``to_dict()`` — ``to_dict()`` adds the
    derived ``content_hash`` field for display, and the frozen ContentModel
    schema (``extra="forbid"``) rejects it back on the way into ``/compose``.
    This endpoint's contract is "valid input", not "human-readable record".
    """
    if name not in _CONTENT_EXAMPLES:
        raise HTTPException(
            status_code=404,
            detail=f"unknown example {name!r}. Known: {', '.join(_CONTENT_EXAMPLES)}",
        )

    from brand.examples.malthouse import malthouse_content

    return malthouse_content().model_dump(mode="json")


# ---------------------------------------------------------------------------
# Proposals
# ---------------------------------------------------------------------------


@router.post("/brand-proposals")
def propose_brand(body: BriefRequest) -> dict:
    """Brief in, structured proposal out. Nothing is written.

    The response carries the proposal's validation report so the caller can
    show a human what they would be approving, which is the entire point of
    separating this endpoint from ``POST /brands``.
    """
    from brand.agents.brand_agent import BrandAgent, BrandProposalError

    try:
        proposal = BrandAgent().generate_proposal(body.brief, name=body.name)
    except BrandProposalError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return proposal.to_dict()


@router.post("/brand-proposals/approve", status_code=201)
def approve_proposal(
    payload: dict[str, Any] = Body(...),
    approved_by: str = Query(..., min_length=1),
) -> dict:
    """Turn a proposal payload into a stored, approved brand.

    Split from ``/brand-proposals`` so that approval is a separate, explicitly
    attributed act rather than a flag on the generation call.
    """
    from brand.models.brand import Brand, BrandStatus

    try:
        brand = Brand.model_validate(payload.get("brand") or payload)
    except Exception as exc:                               # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    report = brand.check()
    if not report.ok:
        raise HTTPException(
            status_code=409,
            detail={"message": "proposal does not validate",
                    "validation": report.to_dict()},
        )
    approved = brand.model_copy(
        update={
            "status": BrandStatus.APPROVED,
            "origin": "agent",
            "changelog": f"Proposed from brief; approved by {approved_by}.",
        }
    ).with_content_hash()
    _repo().save(approved)
    return {"brand_id": str(approved.brand_id), "version": approved.version,
            "status": approved.status.value}


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@router.get("/brand-schema")
def brand_schema() -> JSONResponse:
    from brand.schemas.brand_schema import brand_json_schema

    return JSONResponse(content=brand_json_schema())
