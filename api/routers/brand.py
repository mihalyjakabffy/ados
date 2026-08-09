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
    GET  /brands/{id}/preview             the brand preview, as HTML
    GET  /brands/{id}/templates           which documents this brand can render
    POST /brands/{id}/render/{template}   render one, HTML or PDF
    POST /brand-proposals                 brief → BrandAgent proposal (no write)
    GET  /brand-schema                    the JSON Schema

Two things this router does not do, deliberately:

* ``POST /brand-proposals`` **does not save**. The agent proposes; a human
  approves. Wiring the proposal endpoint straight into the store would make
  the approval step decorative.
* Nothing mutates a published version. The store raises and the handler turns
  that into a 409, because the alternative is a reprint that silently differs
  from what was issued.
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
