"""
api/routers/ados_project.py

The ADOS Project API (M2.1) — the product-level boundary a real user's
frontend talks to: Projects, their Brand, Documents, Assets, Content, and
Versions. This router holds no composition, review or iteration logic of
its own; it orchestrates ``brand.project`` (the new Project domain) and
calls straight into the existing, unmodified engine
(``brand.creative.composer.compose``, ``brand.creative.evaluate.evaluate``)
for the one operation — composing a Document — that needs it. Everything
past that (applying a command, running an iteration) is the existing
``POST /brands/{id}/intent`` / ``POST /brands/{id}/iterate`` routes,
called directly by the frontend; this router does not wrap or duplicate
them.

Mounted at ``/api/v2/ados-projects`` — deliberately not ``/projects`` or
``/api/v2/projects``, both already owned by REVELATION's own, unrelated
3D-render ``Project`` aggregate (``api/routers/projects.py``,
``api/routers/v2_projects.py``). Sharing a path (or, worse, a storage
directory) with a different domain's "Project" by coincidence of naming
is exactly the collision ADOS's independence from REVELATION exists to
avoid — see ``brand/project/store.py``'s docstring for the storage side
of the same decision.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ados-projects", tags=["ados-projects"])

_PROJECT_STORAGE_ROOT = os.environ.get("ADOS_PROJECT_STORAGE_ROOT", "storage/ados-projects")

#: A conservative allow-list, not a general upload service. M2.1's asset
#: layer is "bring your project images in and use them", not a DAM
#: (ADOS-M2.1 §11) — nothing here parses or transcodes a file, so nothing
#: past extension/size needs to be checked.
_ALLOWED_ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
_MAX_ASSET_BYTES = 25 * 1024 * 1024


def _repo():
    from brand.project.store import FileProjectRepository

    return FileProjectRepository(_PROJECT_STORAGE_ROOT)


def _brand_repo():
    """The same store api/routers/brand.py's own endpoints use — including
    its lazy seeding of the Studio Nord worked example on an otherwise-empty
    store. A fresh deployment (or a fresh CI checkout) has no brands yet;
    building a second, unseeded FileBrandRepository here would make every
    brand-attach 404 until someone happened to hit a brand.py endpoint
    first — reusing brand.py's own seeded accessor is what avoids that."""
    from api.routers import brand as brand_router

    return brand_router._seeded_repo()


def _load(project_id: str):
    from brand.project.store import ProjectNotFound

    try:
        return _repo().get(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _brand_name(brand_id: Optional[str]) -> Optional[str]:
    """Best-effort — a project may point at a brand that was since
    removed from the store; that is a fact to surface, not a 500."""
    if not brand_id:
        return None
    try:
        brand = _brand_repo().get(brand_id)
        return brand.identity.name
    except Exception:                                        # noqa: BLE001
        return None


def _touch(project) -> Any:
    import datetime as _dt

    return project.model_copy(update={"updated_at": _dt.datetime.now(_dt.timezone.utc)})


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)


class AttachBrandRequest(BaseModel):
    brand_id: str
    brand_version: Optional[str] = Field(default=None, max_length=20)


class CreateDocumentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    direction_id: str = Field(default="editorial-quiet", max_length=40)
    document_type: str = Field(default="", max_length=60)


class UpdateDocumentRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    direction_id: Optional[str] = Field(default=None, max_length=40)


class AddContentItemRequest(BaseModel):
    kind: str
    label: str = Field(default="", max_length=120)
    text: str = Field(default="", max_length=8000)
    value: float | str | None = None
    unit: str = Field(default="", max_length=24)
    provenance: str = Field(default="", max_length=200)
    asset_id: Optional[str] = None
    caption: str = Field(default="", max_length=400)
    aspect: str = Field(default="", max_length=10)


class SaveVersionRequest(BaseModel):
    document_id: str
    label: str = Field(default="", max_length=120)
    #: The plan/evaluation the workspace currently has on screen, if any —
    #: a version should capture what the user actually reviewed, not force
    #: a silent recompose that could differ from what they saw.
    plan: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@router.get("")
def list_projects() -> dict[str, Any]:
    from brand.project.model import ProjectSummary

    projects = _repo().list_projects()
    return {
        "projects": [
            ProjectSummary.from_project(p, _brand_name(p.brand_id)).model_dump(mode="json")
            for p in sorted(projects, key=lambda p: p.updated_at, reverse=True)
        ]
    }


@router.post("", status_code=201)
def create_project(body: CreateProjectRequest) -> dict[str, Any]:
    from brand.project.model import Project

    project = Project(name=body.name, description=body.description)
    _repo().save(project)
    return project.model_dump(mode="json")


@router.get("/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    project = _load(project_id)
    return {**project.model_dump(mode="json"), "brand_name": _brand_name(project.brand_id)}


@router.patch("/{project_id}")
def update_project(project_id: str, body: UpdateProjectRequest) -> dict[str, Any]:
    project = _load(project_id)
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    project = _touch(project.model_copy(update=updates))
    _repo().save(project)
    return project.model_dump(mode="json")


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str) -> None:
    from brand.project.store import ProjectNotFound

    try:
        _repo().delete(project_id)
    except ProjectNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{project_id}/brand")
def attach_brand(project_id: str, body: AttachBrandRequest) -> dict[str, Any]:
    from brand.store.brand_repo import BrandNotFound

    project = _load(project_id)
    try:
        _brand_repo().get(body.brand_id, body.brand_version)
    except BrandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    project = _touch(project.model_copy(update={"brand_id": body.brand_id, "brand_version": body.brand_version}))
    _repo().save(project)
    return {**project.model_dump(mode="json"), "brand_name": _brand_name(project.brand_id)}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


def _document_index(project, document_id: str) -> int:
    for i, doc in enumerate(project.documents):
        if doc.id == document_id:
            return i
    raise HTTPException(status_code=404, detail=f"no document {document_id!r} in project {project.id!r}")


@router.post("/{project_id}/documents", status_code=201)
def create_document(project_id: str, body: CreateDocumentRequest) -> dict[str, Any]:
    from brand.creative.directions import get_direction
    from brand.project.model import Document

    project = _load(project_id)
    try:
        get_direction(body.direction_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "unknown_direction", "detail": str(exc)}) from exc

    doc = Document(
        project_id=project.id, name=body.name,
        direction_id=body.direction_id, document_type=body.document_type,
    )
    project = _touch(project.model_copy(update={"documents": project.documents + (doc,)}))
    _repo().save(project)
    return doc.model_dump(mode="json")


@router.get("/{project_id}/documents/{document_id}")
def get_document(project_id: str, document_id: str) -> dict[str, Any]:
    project = _load(project_id)
    idx = _document_index(project, document_id)
    return project.documents[idx].model_dump(mode="json")


@router.patch("/{project_id}/documents/{document_id}")
def update_document(project_id: str, document_id: str, body: UpdateDocumentRequest) -> dict[str, Any]:
    from brand.creative.directions import get_direction

    project = _load(project_id)
    idx = _document_index(project, document_id)
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "direction_id" in updates:
        try:
            get_direction(updates["direction_id"])
        except KeyError as exc:
            raise HTTPException(status_code=404, detail={"error": "unknown_direction", "detail": str(exc)}) from exc

    import datetime as _dt

    docs = list(project.documents)
    docs[idx] = docs[idx].model_copy(update={**updates, "updated_at": _dt.datetime.now(_dt.timezone.utc)})
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return project.documents[idx].model_dump(mode="json")


@router.delete("/{project_id}/documents/{document_id}", status_code=204)
def delete_document(project_id: str, document_id: str) -> None:
    project = _load(project_id)
    _document_index(project, document_id)  # 404s if absent
    remaining = tuple(d for d in project.documents if d.id != document_id)
    project = _touch(project.model_copy(update={"documents": remaining}))
    _repo().save(project)


@router.post("/{project_id}/documents/{document_id}/duplicate", status_code=201)
def duplicate_document(project_id: str, document_id: str) -> dict[str, Any]:
    import uuid as _uuid

    project = _load(project_id)
    idx = _document_index(project, document_id)
    source = project.documents[idx]
    copy = source.model_copy(update={
        "id": str(_uuid.uuid4()),
        "name": f"{source.name} (copy)",
    })
    project = _touch(project.model_copy(update={"documents": project.documents + (copy,)}))
    _repo().save(project)
    return copy.model_dump(mode="json")


# -- content ------------------------------------------------------------


@router.post("/{project_id}/documents/{document_id}/content", status_code=201)
def add_content_item(project_id: str, document_id: str, body: AddContentItemRequest) -> dict[str, Any]:
    from pydantic import ValidationError

    from brand.project.model import ContentItem

    project = _load(project_id)
    idx = _document_index(project, document_id)
    try:
        item = ContentItem.model_validate(body.model_dump())
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_content_item", "errors": exc.errors(include_url=False, include_context=False)},
        ) from exc

    doc = project.documents[idx]
    doc = doc.model_copy(update={"content_items": doc.content_items + (item,)})

    # Fail before saving: the same pipeline the Composer would refuse must
    # refuse here too, with the Composer's own message — not a laxer,
    # second content validation.
    _validate_document_content(doc, project.name)

    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return doc.model_dump(mode="json")


@router.delete("/{project_id}/documents/{document_id}/content/{item_id}")
def remove_content_item(project_id: str, document_id: str, item_id: str) -> dict[str, Any]:
    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    remaining = tuple(i for i in doc.content_items if i.id != item_id)
    if len(remaining) == len(doc.content_items):
        raise HTTPException(status_code=404, detail=f"no content item {item_id!r} on this document")
    doc = doc.model_copy(update={"content_items": remaining})
    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return doc.model_dump(mode="json")


def _validate_document_content(doc, project_name: str) -> None:
    from pydantic import ValidationError

    try:
        doc.content_model(project_name)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_content", "errors": exc.errors(include_url=False, include_context=False)},
        ) from exc


# -- compose --------------------------------------------------------------


@router.post("/{project_id}/documents/{document_id}/compose")
def compose_document(project_id: str, document_id: str) -> dict[str, Any]:
    """The one place this router calls the real Composer — everything past
    the first compose (applying a command, iterating) goes through the
    existing ``POST /brands/{id}/intent`` / ``/iterate`` directly; this
    router only caches whatever plan those calls last produced, via
    ``PATCH .../content`` and ``POST .../versions``."""
    from brand.creative.composer import CompositionError, compose
    from brand.creative.directions import get_direction
    from brand.creative.evaluate import evaluate
    from brand.store.brand_repo import BrandNotFound

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]

    if not project.brand_id:
        raise HTTPException(status_code=422, detail={"error": "no_brand_attached"})

    try:
        brand = _brand_repo().get(project.brand_id, project.brand_version)
    except BrandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    direction = get_direction(doc.direction_id)
    content = doc.content_model(project.name)
    if not content.blocks:
        raise HTTPException(status_code=422, detail={"error": "no_content", "detail": "add content before composing"})

    try:
        plan = compose(content, direction, brand)
    except CompositionError as exc:
        raise HTTPException(status_code=422, detail={"error": "composition_infeasible", "detail": str(exc)}) from exc

    evaluation = evaluate(plan, direction, brand.resolve_tokens())

    doc = doc.model_copy(update={"latest_plan": plan.to_dict(), "latest_evaluation": evaluation.to_dict()})
    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)

    return {
        "document": doc.model_dump(mode="json"),
        "content_model": content.model_dump(mode="json"),
        "plan": plan.to_dict(),
        "evaluation": evaluation.to_dict(),
    }


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


@router.post("/{project_id}/assets", status_code=201)
async def upload_asset(project_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    from brand.project.model import Asset

    project = _load(project_id)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_ASSET_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail={"error": "unsupported_file_type", "allowed": sorted(_ALLOWED_ASSET_EXTENSIONS)},
        )

    data = await file.read()
    if len(data) > _MAX_ASSET_BYTES:
        raise HTTPException(status_code=422, detail={"error": "file_too_large", "max_bytes": _MAX_ASSET_BYTES})

    asset_id = uuid.uuid4().hex[:12]
    asset = Asset(
        id=asset_id,
        filename=file.filename or "upload",
        content_type=file.content_type or "",
        size_bytes=len(data),
        path=f"{asset_id}{ext}",
    )

    asset_dir = _repo().asset_storage_dir(project.id)
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / asset.path).write_bytes(data)

    project = _touch(project.model_copy(update={"assets": project.assets + (asset,)}))
    _repo().save(project)
    return asset.model_dump(mode="json")


@router.get("/{project_id}/assets")
def list_assets(project_id: str) -> dict[str, Any]:
    project = _load(project_id)
    return {"assets": [a.model_dump(mode="json") for a in project.assets]}


@router.get("/{project_id}/assets/{asset_id}/file")
def download_asset(project_id: str, asset_id: str):
    project = _load(project_id)
    try:
        asset = project.asset(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    path = _repo().asset_storage_dir(project.id) / asset.path
    if not path.exists():
        raise HTTPException(status_code=404, detail="asset file missing from storage")
    return FileResponse(path, media_type=asset.content_type or "application/octet-stream", filename=asset.filename)


@router.delete("/{project_id}/assets/{asset_id}", status_code=204)
def delete_asset(project_id: str, asset_id: str) -> None:
    project = _load(project_id)
    try:
        asset = project.asset(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    path = _repo().asset_storage_dir(project.id) / asset.path
    path.unlink(missing_ok=True)
    remaining = tuple(a for a in project.assets if a.id != asset_id)
    project = _touch(project.model_copy(update={"assets": remaining}))
    _repo().save(project)


# ---------------------------------------------------------------------------
# Versions — explicit, immutable, never confused with autosave
# ---------------------------------------------------------------------------


@router.post("/{project_id}/versions", status_code=201)
def save_version(project_id: str, body: SaveVersionRequest) -> dict[str, Any]:
    from brand.project.model import ProjectVersion

    project = _load(project_id)
    idx = _document_index(project, body.document_id)
    doc = project.documents[idx]

    plan = body.plan if body.plan is not None else doc.latest_plan
    version = ProjectVersion(
        number=project.next_version_number,
        label=body.label,
        document_id=doc.id,
        document_name=doc.name,
        direction_id=doc.direction_id,
        content_items=doc.content_items,
        plan=plan,
    )
    # A version also updates the document's own cached plan, so reopening
    # the project later shows what was actually saved, not a stale compose.
    if body.plan is not None:
        docs = list(project.documents)
        docs[idx] = doc.model_copy(update={"latest_plan": body.plan})
        project = project.model_copy(update={"documents": tuple(docs)})

    project = _touch(project.model_copy(update={"versions": project.versions + (version,)}))
    _repo().save(project)
    return version.model_dump(mode="json")


@router.get("/{project_id}/versions")
def list_versions(project_id: str) -> dict[str, Any]:
    project = _load(project_id)
    return {"versions": [v.model_dump(mode="json") for v in sorted(project.versions, key=lambda v: v.number, reverse=True)]}


@router.post("/{project_id}/versions/{version_number}/restore")
def restore_version(project_id: str, version_number: int) -> dict[str, Any]:
    project = _load(project_id)
    version = next((v for v in project.versions if v.number == version_number), None)
    if version is None:
        raise HTTPException(status_code=404, detail=f"no version {version_number} in project {project_id!r}")

    try:
        idx = _document_index(project, version.document_id)
    except HTTPException as exc:
        raise HTTPException(
            status_code=409,
            detail="the document this version belonged to no longer exists in this project",
        ) from exc

    import datetime as _dt

    docs = list(project.documents)
    docs[idx] = docs[idx].model_copy(update={
        "content_items": version.content_items,
        "direction_id": version.direction_id,
        "latest_plan": version.plan,
        "updated_at": _dt.datetime.now(_dt.timezone.utc),
    })
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return project.documents[idx].model_dump(mode="json")
