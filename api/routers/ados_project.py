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
from datetime import date as _date
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


def _touch_doc(doc) -> Any:
    """Like ``_touch``, but for a Document's own ``updated_at`` — separate
    from the Project's, since a client that only watches whether *this*
    document changed (e.g. to re-check its requirement findings) must see
    its timestamp move on every one of its own mutations, not just on
    whichever unrelated document in the project last changed."""
    import datetime as _dt

    return doc.model_copy(update={"updated_at": _dt.datetime.now(_dt.timezone.utc)})


def _resolve_ref_project(ref_id: str):
    """``brand.project.content_resolution``'s injected project lookup —
    this repo's own accessor, so a referenced project resolves against
    whichever storage root this deployment (or this test) actually uses."""
    from brand.project.store import ProjectNotFound

    try:
        return _repo().get(ref_id)
    except ProjectNotFound:
        return None


def _document_content_model(doc, project):
    """Thin call-through — the real merge logic (own content, the
    project's shared pool, portfolio references) now lives in
    ``brand.project.content_resolution`` so ``brand/design_state/build.py``
    can reuse it without duplicating it (ADOS-M2.5)."""
    from brand.project.content_resolution import resolve_document_content

    return resolve_document_content(doc, project, resolve_project=_resolve_ref_project)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    #: Merged into the existing project_data, not replacing it -- the same
    #: PATCH-merges-a-bag posture UpdateDocumentRequest.metadata already
    #: has, for the same reason (ADOS-M2.5 §4).
    project_data: Optional[dict[str, Any]] = None


class AttachBrandRequest(BaseModel):
    brand_id: str
    brand_version: Optional[str] = Field(default=None, max_length=20)


class CreateDocumentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    #: None = "use the document type's composition_profile" when a type is
    #: given, else the M2.1 default of editorial-quiet. Explicit always wins.
    direction_id: Optional[str] = Field(default=None, max_length=40)
    #: A brand.project.document_types id, or "" for an untyped, free-form
    #: document — exactly M2.1's shape.
    document_type_id: str = Field(default="", max_length=40)
    #: The document brief (subtitle, author, date, audience, purpose,
    #: location, client, ...) — a plain bag, since which of these apply
    #: is a document-type concern, not a fixed schema (Document.metadata).
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateDocumentRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    direction_id: Optional[str] = Field(default=None, max_length=40)
    #: Merged into the existing metadata, not replacing it — a PATCH that
    #: sets one brief field must not silently blank the others.
    metadata: Optional[dict[str, Any]] = None


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


class CreateSectionRequest(BaseModel):
    kind: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=120)
    order: Optional[int] = None


class UpdateSectionRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    order: Optional[int] = None
    content_item_ids: Optional[list[str]] = None


class AddProjectRefRequest(BaseModel):
    project_id: str


class ExportRequest(BaseModel):
    #: None = export the document's current state, saving a fresh Version
    #: first. A given number must name a real, already-saved Version — an
    #: export never targets a state that was never actually reviewed.
    version_number: Optional[int] = None
    #: "pdf" (Chromium print) or "html" (ADOS-M2.5's Website projection --
    #: the exact same render_page_plan output, written out directly
    #: instead of printed). Never a second renderer: html_to_pdf is simply
    #: skipped for this format, not replaced by one.
    format: str = Field(default="pdf", pattern=r"^(pdf|html)$")


class AddPresentationOptionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    status: str = "proposed"


class AddDecisionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    selected_option_id: Optional[str] = None
    date: Optional[_date] = None


class AddActionItemRequest(BaseModel):
    description: str = Field(min_length=1, max_length=400)
    responsible: str = Field(default="", max_length=120)
    deadline: Optional[_date] = None
    status: str = "open"


class AddParticipantRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="", max_length=120)


class AddMeetingRequest(BaseModel):
    #: Meetings are recorded whole, not built up field by field — the
    #: minimal shape that still holds a real record (ADOS-M2.2.1 P4): no
    #: sub-resource CRUD for one meeting's own participants/agenda/
    #: decisions/action_items, since nothing in the master prompt asked
    #: for that and it would be most of a project-management application.
    title: str = Field(min_length=1, max_length=120)
    date: Optional[_date] = None
    location: str = Field(default="", max_length=200)
    participants: list[AddParticipantRequest] = Field(default_factory=list)
    agenda: list[str] = Field(default_factory=list)
    decisions: list[AddDecisionRequest] = Field(default_factory=list)
    action_items: list[AddActionItemRequest] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Document types (ADOS-M2.2) — declarative, listed before /{project_id} so
# "document-types" is never swallowed by that path parameter.
# ---------------------------------------------------------------------------


@router.get("/document-types")
def list_document_types_endpoint() -> dict[str, Any]:
    from brand.project.document_types import list_document_types

    return {"document_types": [t.model_dump(mode="json") for t in list_document_types()]}


@router.get("/document-types/{type_id}")
def get_document_type_endpoint(type_id: str) -> dict[str, Any]:
    from brand.project.document_types import UnknownDocumentTypeError, get_document_type
    from brand.project.requirements import requirements_for

    try:
        doc_type = get_document_type(type_id)
    except UnknownDocumentTypeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        **doc_type.model_dump(mode="json"),
        "requirements": [r.model_dump(mode="json") for r in requirements_for(type_id)],
    }


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
    if "project_data" in updates:
        updates["project_data"] = {**project.project_data, **updates["project_data"]}
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
    from brand.project.document_types import UnknownDocumentTypeError, get_document_type
    from brand.project.model import Document, Section

    project = _load(project_id)

    document_type = None
    if body.document_type_id:
        try:
            document_type = get_document_type(body.document_type_id)
        except UnknownDocumentTypeError as exc:
            raise HTTPException(
                status_code=404, detail={"error": "unknown_document_type", "detail": str(exc)}
            ) from exc

    direction_id = body.direction_id or (
        document_type.composition_profile if document_type else "editorial-quiet"
    )
    try:
        get_direction(direction_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "unknown_direction", "detail": str(exc)}) from exc

    # The wizard's Step 5 ("Generate Structure") — a document created with a
    # type starts with that type's default skeleton as empty Sections, which
    # the user can then add to, reorder or remove (ADOS-M2.2 §5).
    sections = tuple(
        Section(kind=kind, name=document_type.section_label(kind), order=i)
        for i, kind in enumerate(document_type.default_structure)
    ) if document_type else ()

    doc = Document(
        project_id=project.id, name=body.name,
        direction_id=direction_id, document_type_id=body.document_type_id,
        sections=sections, metadata=body.metadata,
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
    if "metadata" in updates:
        updates["metadata"] = {**project.documents[idx].metadata, **updates["metadata"]}

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


# -- sections (ADOS-M2.2) -------------------------------------------------


def _section_index(doc, section_id: str) -> int:
    for i, section in enumerate(doc.sections):
        if section.id == section_id:
            return i
    raise HTTPException(status_code=404, detail=f"no section {section_id!r} on this document")


@router.post("/{project_id}/documents/{document_id}/sections", status_code=201)
def create_section(project_id: str, document_id: str, body: CreateSectionRequest) -> dict[str, Any]:
    from brand.project.model import Section

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    order = body.order if body.order is not None else len(doc.sections)
    section = Section(kind=body.kind, name=body.name, order=order)
    doc = _touch_doc(doc.model_copy(update={"sections": doc.sections + (section,)}))
    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return doc.model_dump(mode="json")


@router.patch("/{project_id}/documents/{document_id}/sections/{section_id}")
def update_section(
    project_id: str, document_id: str, section_id: str, body: UpdateSectionRequest,
) -> dict[str, Any]:
    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    s_idx = _section_index(doc, section_id)

    updates: dict[str, Any] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.order is not None:
        updates["order"] = body.order
    if body.content_item_ids is not None:
        # A document's own items, plus whichever shared items it has
        # actually selected (ADOS-M2.5 §6) -- a selected shared item is
        # sectionable exactly like a private one; one not yet selected is
        # not, so this cannot be used to smuggle an unselected item in.
        known_ids = {item.id for item in doc.content_items} | set(doc.content_selection)
        unknown = [i for i in body.content_item_ids if i not in known_ids]
        if unknown:
            raise HTTPException(
                status_code=422,
                detail={"error": "unknown_content_item", "ids": unknown},
            )
        updates["content_item_ids"] = tuple(body.content_item_ids)

    sections = list(doc.sections)
    sections[s_idx] = sections[s_idx].model_copy(update=updates)
    doc = _touch_doc(doc.model_copy(update={"sections": tuple(sections)}))
    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return doc.model_dump(mode="json")


@router.delete("/{project_id}/documents/{document_id}/sections/{section_id}")
def delete_section(project_id: str, document_id: str, section_id: str) -> dict[str, Any]:
    """Removes the Section, not the content it grouped — the content items
    become unsectioned and are still composed, appended at the end
    (Document._ordered_content_items), never silently dropped."""
    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    _section_index(doc, section_id)  # 404s if absent
    remaining = tuple(s for s in doc.sections if s.id != section_id)
    doc = _touch_doc(doc.model_copy(update={"sections": remaining}))
    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return doc.model_dump(mode="json")


# -- requirements (ADOS-M2.2 §19) -----------------------------------------


@router.get("/{project_id}/documents/{document_id}/requirements")
def get_document_requirements(project_id: str, document_id: str) -> dict[str, Any]:
    from brand.project.requirements import check_requirements

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    findings = check_requirements(doc, project)
    return {
        "findings": [f.to_dict() for f in findings],
        "ok": not any(f.severity.value in ("ERROR", "BLOCK") for f in findings),
    }


# -- project references (ADOS-M2.2 §10 — Portfolio) -----------------------


@router.post("/{project_id}/documents/{document_id}/project-refs", status_code=201)
def add_project_ref(project_id: str, document_id: str, body: AddProjectRefRequest) -> dict[str, Any]:
    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]

    if body.project_id == project.id:
        raise HTTPException(status_code=422, detail={"error": "cannot_reference_own_project"})
    try:
        _repo().get(body.project_id)
    except Exception as exc:                                  # noqa: BLE001
        raise HTTPException(status_code=404, detail={"error": "referenced_project_not_found"}) from exc

    if body.project_id not in doc.project_refs:
        doc = _touch_doc(doc.model_copy(update={"project_refs": doc.project_refs + (body.project_id,)}))
        docs = list(project.documents)
        docs[idx] = doc
        project = _touch(project.model_copy(update={"documents": tuple(docs)}))
        _repo().save(project)
    return doc.model_dump(mode="json")


@router.delete("/{project_id}/documents/{document_id}/project-refs/{ref_project_id}")
def remove_project_ref(project_id: str, document_id: str, ref_project_id: str) -> dict[str, Any]:
    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    doc = _touch_doc(doc.model_copy(update={"project_refs": tuple(p for p in doc.project_refs if p != ref_project_id)}))
    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return doc.model_dump(mode="json")


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
    doc = _touch_doc(doc.model_copy(update={"content_items": doc.content_items + (item,)}))

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
    doc = _touch_doc(doc.model_copy(update={"content_items": remaining}))
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


# ---------------------------------------------------------------------------
# Shared project-level content (ADOS-M2.5 §6) — the pool a Document's own
# ``content_selection`` draws from. This is a second place a ContentItem
# is stored (the project, rather than a document), never a second content
# *model* — every endpoint below reuses ContentItem/AddContentItemRequest
# unchanged.
# ---------------------------------------------------------------------------


class SetContentSelectionRequest(BaseModel):
    #: The complete set of shared item ids this document includes —
    #: replaces the prior selection outright, the same "PUT the whole
    #: list" shape ``update_section``'s ``content_item_ids`` already uses,
    #: rather than incremental add/remove calls for what is, in practice,
    #: usually edited as one list in the UI.
    content_item_ids: list[str] = Field(default_factory=list)


class PropagateBrandRequest(BaseModel):
    #: The already-published version to move this project onto — never
    #: an in-place brand edit (brand/README.md Rule 5: published versions
    #: are immutable). The caller bumps the brand elsewhere first
    #: (``POST /brands/{id}/versions/{version}/approve`` +
    #: ``.../publish``), then names that version here.
    brand_version: str = Field(min_length=1, max_length=20)


@router.post("/{project_id}/content", status_code=201)
def add_shared_content_item(project_id: str, body: AddContentItemRequest) -> dict[str, Any]:
    from pydantic import ValidationError

    from brand.project.model import ContentItem
    from brand.project.model import Document as _Document

    project = _load(project_id)
    try:
        item = ContentItem.model_validate(body.model_dump())
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_content_item", "errors": exc.errors(include_url=False, include_context=False)},
        ) from exc

    # A shared item belongs to no one document, so there is no
    # doc.content_model() to fail loudly through as add_content_item's
    # own document-scoped path does -- validate it the same way, against
    # a throwaway single-item Document, so a metric with no provenance
    # (a per-ContentBlock rule, not a per-ContentItem one) is refused here
    # too, not accepted into the pool and only discovered on first compose.
    try:
        _Document(project_id=project.id, name="_", content_items=(item,)).content_model(project.name)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_content_item", "errors": exc.errors(include_url=False, include_context=False)},
        ) from exc

    project = _touch(project.model_copy(update={"content_items": project.content_items + (item,)}))
    _repo().save(project)
    return project.model_dump(mode="json")


@router.get("/{project_id}/content")
def list_shared_content_items(project_id: str) -> dict[str, Any]:
    project = _load(project_id)
    return {"content_items": [i.model_dump(mode="json") for i in project.content_items]}


@router.delete("/{project_id}/content/{item_id}")
def remove_shared_content_item(project_id: str, item_id: str) -> dict[str, Any]:
    """Removing a shared item does not chase down and clean up every
    document's own ``content_selection`` — a dangling selected id is
    exactly the "reference to something that no longer exists" state
    ``resolve_document_content`` already treats as fail-soft (skip, don't
    500), the same posture Portfolio's stale ``project_refs`` already
    has. Nothing here quietly rewrites a document that did not change."""
    project = _load(project_id)
    remaining = tuple(i for i in project.content_items if i.id != item_id)
    if len(remaining) == len(project.content_items):
        raise HTTPException(status_code=404, detail=f"no shared content item {item_id!r} in this project")
    project = _touch(project.model_copy(update={"content_items": remaining}))
    _repo().save(project)
    return project.model_dump(mode="json")


@router.put("/{project_id}/documents/{document_id}/content-selection")
def set_content_selection(project_id: str, document_id: str, body: SetContentSelectionRequest) -> dict[str, Any]:
    from brand.project.content_resolution import resolve_document_content
    from pydantic import ValidationError

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]

    known_ids = {i.id for i in project.content_items}
    unknown = [i for i in body.content_item_ids if i not in known_ids]
    if unknown:
        raise HTTPException(status_code=422, detail={"error": "unknown_shared_content_item", "ids": unknown})

    doc = doc.model_copy(update={"content_selection": tuple(body.content_item_ids)})
    try:
        resolve_document_content(doc, project, resolve_project=_resolve_ref_project)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_content", "errors": exc.errors(include_url=False, include_context=False)},
        ) from exc

    doc = _touch_doc(doc)
    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return doc.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Propagation (ADOS-M4.3) — the fan-out this router was missing between
# "a shared fact changed" and "every document that carries it reflects
# that" (docs/architecture/m4-claude-connector.md §6). Both endpoints
# below are the one place in this router that calls
# ``brand.project.propagation`` -- a thin I/O shell around it, the same
# split every other endpoint here already keeps between "this router
# loads/saves" and "brand.project.* decides". Neither endpoint saves a
# Version: recomposing refreshes each touched document's cached
# ``latest_plan``/``latest_evaluation`` exactly as ``.../compose``
# already does, and leaves an explicit ``POST .../versions`` call, per
# document, to whoever wants an immutable snapshot of the result.
# ---------------------------------------------------------------------------


def _propagation_response(result: Any) -> dict[str, Any]:
    return {
        "touched": [
            {
                "document_id": r.document_id,
                "document_name": r.document_name,
                "recomposed": r.recomposed,
                "reason": r.reason,
                "findings": list(r.findings),
                "requirement_findings": list(r.requirement_findings),
            }
            for r in result.touched
        ],
        "unaffected": list(result.unaffected),
    }


@router.post("/{project_id}/content/{item_id}/propagate")
def propagate_content_item(project_id: str, item_id: str) -> dict[str, Any]:
    """Recompose every document in this project whose own content or
    ``content_selection`` references ``item_id`` — call this right after
    editing that shared fact (today: remove + re-add, until a real
    in-place update endpoint exists) so every consuming document picks
    up the change instead of silently drifting until its own next
    ``.../compose`` call. A dangling ``item_id`` (already removed) is not
    an error here either — a document that still selects it is
    recomposed and honestly reports ``no_content`` if that was its only
    content, the same fail-soft posture ``resolve_document_content``
    already has."""
    from brand.project.propagation import propagate_content_change
    from brand.store.brand_repo import BrandNotFound

    project = _load(project_id)
    if not project.brand_id:
        raise HTTPException(status_code=422, detail={"error": "no_brand_attached"})
    try:
        brand = _brand_repo().get(project.brand_id, project.brand_version)
    except BrandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result = propagate_content_change(project, brand, item_id)
    _repo().save(result.project)
    return _propagation_response(result)


@router.post("/{project_id}/brand/propagate")
def propagate_brand(project_id: str, body: PropagateBrandRequest) -> dict[str, Any]:
    """Move this project onto an already-published version of its own
    brand and recompose every one of its documents against it. Never an
    in-place brand edit — bump/approve/publish the new version first
    (``api/routers/brand.py``), then call this. Every document in the
    project shares the one brand, so every document is recomposed;
    there is no ``unaffected`` set for this operation."""
    from brand.project.propagation import propagate_brand_change
    from brand.store.brand_repo import BrandNotFound

    project = _load(project_id)
    if not project.brand_id:
        raise HTTPException(status_code=422, detail={"error": "no_brand_attached"})
    try:
        new_brand = _brand_repo().get(project.brand_id, body.brand_version)
    except BrandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result = propagate_brand_change(project, new_brand)
    _repo().save(result.project)
    return {**_propagation_response(result), "brand_version": result.project.brand_version}


# ---------------------------------------------------------------------------
# DesignState (ADOS-M2.5 §21) — a read model, not a second store. There is
# no design-state id to create: it is assembled fresh, on every request,
# from the same Project/Document/Brand/Version objects every endpoint above
# already reads and writes. ``version`` reads a specific saved Version's
# frozen state the same read-only way ``GET .../versions`` lists them,
# never an auto-save.
# ---------------------------------------------------------------------------


@router.get("/{project_id}/documents/{document_id}/design-state")
def get_design_state(project_id: str, document_id: str, version: Optional[int] = None) -> dict[str, Any]:
    from brand.design_state.build import build_design_state
    from brand.project.versioning import VersionNotFoundError
    from brand.store.brand_repo import BrandNotFound

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]

    brand = None
    if project.brand_id:
        try:
            brand = _brand_repo().get(project.brand_id, project.brand_version)
        except BrandNotFound:
            brand = None

    try:
        state = build_design_state(
            project, doc, brand, version_number=version, resolve_project=_resolve_ref_project,
        )
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return state.to_dict()


# ---------------------------------------------------------------------------
# Structured decisions & actions (ADOS-M2.2.1 P3/P4) — Client Presentation's
# options/decisions/action_items, and Internal Documentation's meetings.
# create+delete only, mirroring content items' own add/remove shape; no
# update endpoint, since nothing here is edited in place today.
# ---------------------------------------------------------------------------


def _replace_document_field(project, idx: int, field: str, value: tuple) -> Any:
    doc = _touch_doc(project.documents[idx].model_copy(update={field: value}))
    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return doc


def _validated(model_cls, error_code: str, **kwargs):
    from pydantic import ValidationError

    try:
        return model_cls(**kwargs)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": error_code, "errors": exc.errors(include_url=False, include_context=False)},
        ) from exc


@router.post("/{project_id}/documents/{document_id}/options", status_code=201)
def add_presentation_option(project_id: str, document_id: str, body: AddPresentationOptionRequest) -> dict[str, Any]:
    from brand.project.model import PresentationOption

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    option = _validated(
        PresentationOption, "invalid_option",
        title=body.title, description=body.description, status=body.status,
    )
    doc = _replace_document_field(project, idx, "presentation_options", doc.presentation_options + (option,))
    return doc.model_dump(mode="json")


@router.delete("/{project_id}/documents/{document_id}/options/{option_id}")
def remove_presentation_option(project_id: str, document_id: str, option_id: str) -> dict[str, Any]:
    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    remaining = tuple(o for o in doc.presentation_options if o.id != option_id)
    if len(remaining) == len(doc.presentation_options):
        raise HTTPException(status_code=404, detail=f"no option {option_id!r} on this document")
    doc = _replace_document_field(project, idx, "presentation_options", remaining)
    return doc.model_dump(mode="json")


@router.post("/{project_id}/documents/{document_id}/decisions", status_code=201)
def add_decision(project_id: str, document_id: str, body: AddDecisionRequest) -> dict[str, Any]:
    from brand.project.model import Decision

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    decision = _validated(
        Decision, "invalid_decision",
        title=body.title, description=body.description,
        selected_option_id=body.selected_option_id, date=body.date,
    )
    doc = _replace_document_field(project, idx, "decisions", doc.decisions + (decision,))
    return doc.model_dump(mode="json")


@router.delete("/{project_id}/documents/{document_id}/decisions/{decision_id}")
def remove_decision(project_id: str, document_id: str, decision_id: str) -> dict[str, Any]:
    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    remaining = tuple(d for d in doc.decisions if d.id != decision_id)
    if len(remaining) == len(doc.decisions):
        raise HTTPException(status_code=404, detail=f"no decision {decision_id!r} on this document")
    doc = _replace_document_field(project, idx, "decisions", remaining)
    return doc.model_dump(mode="json")


@router.post("/{project_id}/documents/{document_id}/action-items", status_code=201)
def add_action_item(project_id: str, document_id: str, body: AddActionItemRequest) -> dict[str, Any]:
    from brand.project.model import ActionItem

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    item = _validated(
        ActionItem, "invalid_action_item",
        description=body.description, responsible=body.responsible,
        deadline=body.deadline, status=body.status,
    )
    doc = _replace_document_field(project, idx, "action_items", doc.action_items + (item,))
    return doc.model_dump(mode="json")


@router.delete("/{project_id}/documents/{document_id}/action-items/{item_id}")
def remove_action_item(project_id: str, document_id: str, item_id: str) -> dict[str, Any]:
    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    remaining = tuple(a for a in doc.action_items if a.id != item_id)
    if len(remaining) == len(doc.action_items):
        raise HTTPException(status_code=404, detail=f"no action item {item_id!r} on this document")
    doc = _replace_document_field(project, idx, "action_items", remaining)
    return doc.model_dump(mode="json")


@router.post("/{project_id}/documents/{document_id}/meetings", status_code=201)
def add_meeting(project_id: str, document_id: str, body: AddMeetingRequest) -> dict[str, Any]:
    from brand.project.model import ActionItem, Decision, Meeting, Participant

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    meeting = Meeting(
        title=body.title, date=body.date, location=body.location,
        participants=tuple(Participant(name=p.name, role=p.role) for p in body.participants),
        agenda=tuple(body.agenda),
        decisions=tuple(
            Decision(title=d.title, description=d.description, selected_option_id=d.selected_option_id, date=d.date)
            for d in body.decisions
        ),
        action_items=tuple(
            ActionItem(description=a.description, responsible=a.responsible, deadline=a.deadline, status=a.status)
            for a in body.action_items
        ),
    )
    doc = _replace_document_field(project, idx, "meetings", doc.meetings + (meeting,))
    return doc.model_dump(mode="json")


@router.delete("/{project_id}/documents/{document_id}/meetings/{meeting_id}")
def remove_meeting(project_id: str, document_id: str, meeting_id: str) -> dict[str, Any]:
    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]
    remaining = tuple(m for m in doc.meetings if m.id != meeting_id)
    if len(remaining) == len(doc.meetings):
        raise HTTPException(status_code=404, detail=f"no meeting {meeting_id!r} on this document")
    doc = _replace_document_field(project, idx, "meetings", remaining)
    return doc.model_dump(mode="json")


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
    content = _document_content_model(doc, project)
    if not content.blocks:
        raise HTTPException(status_code=422, detail={"error": "no_content", "detail": "add content before composing"})

    # Composition is never constrained to a document type's page ceiling —
    # that ceiling is a Requirement (COMP-001), checked against the plan
    # compose() actually produced, below. Capping max_pages here would let
    # the Composer silently truncate content instead of composing it in
    # full and letting the Requirement report the real overage.
    try:
        plan = compose(content, direction, brand)
    except CompositionError as exc:
        logger.warning("composition infeasible for document %s: %s", doc.id, exc)
        raise HTTPException(status_code=422, detail={"error": "composition_infeasible", "detail": str(exc)}) from exc

    evaluation = evaluate(plan, direction, brand.resolve_tokens())

    doc = _touch_doc(doc.model_copy(update={"latest_plan": plan.to_dict(), "latest_evaluation": evaluation.to_dict()}))
    docs = list(project.documents)
    docs[idx] = doc
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)

    from brand.project.requirements import check_requirements

    requirement_findings = check_requirements(doc, project)

    return {
        "document": doc.model_dump(mode="json"),
        "content_model": content.model_dump(mode="json"),
        "plan": plan.to_dict(),
        "evaluation": evaluation.to_dict(),
        "requirement_findings": [f.to_dict() for f in requirement_findings],
    }


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


def _image_dimensions(data: bytes) -> tuple[Optional[int], Optional[int]]:
    """The file's real pixel dimensions, or ``(None, None)`` — a PDF, a
    corrupt upload, or any file Pillow can't parse. Best-effort and
    read-only: a failure here must never block the upload itself (ADOS-
    M2.2.1 P5's IMG-003 is advisory; the upload endpoint is not)."""
    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(data)) as img:
            return img.width, img.height
    except Exception:                                        # noqa: BLE001
        return None, None


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
    width_px, height_px = _image_dimensions(data)
    asset = Asset(
        id=asset_id,
        filename=file.filename or "upload",
        content_type=file.content_type or "",
        size_bytes=len(data),
        path=f"{asset_id}{ext}",
        width_px=width_px,
        height_px=height_px,
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
    from brand.project.versioning import build_version

    project = _load(project_id)
    idx = _document_index(project, body.document_id)
    doc = project.documents[idx]

    version = build_version(doc, project, label=body.label, plan=body.plan)
    # A version also updates the document's own cached plan, so reopening
    # the project later shows what was actually saved, not a stale compose.
    if body.plan is not None:
        docs = list(project.documents)
        docs[idx] = _touch_doc(doc.model_copy(update={"latest_plan": body.plan}))
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

    docs = list(project.documents)
    docs[idx] = _touch_doc(docs[idx].model_copy(update={
        "content_items": version.content_items,
        # version.content_items is already the fully-resolved own+shared
        # union (brand.project.versioning.resolve_full_content at save
        # time) -- clearing the selection avoids double-applying a
        # (possibly since-changed) shared pool on top of it.
        "content_selection": (),
        "direction_id": version.direction_id,
        "document_type_id": version.document_type_id,
        "sections": version.sections,
        "latest_plan": version.plan,
    }))
    project = _touch(project.model_copy(update={"documents": tuple(docs)}))
    _repo().save(project)
    return project.documents[idx].model_dump(mode="json")


# ---------------------------------------------------------------------------
# Export — production PDF (ADOS-M2.2.1 P0). The one place this router calls
# brand.templates.renderers.render_page_plan / brand.export.exporters.html_to_pdf
# — no second rendering system. Every export is tied to a real, immutable
# ProjectVersion, never to Document.latest_plan directly, so "Version N's
# PDF must not silently change" holds by construction (ADOS-M2.2.1 §7).
# ---------------------------------------------------------------------------


def _resolve_export_version(project, doc, version_number: Optional[int]):
    """Router-layer wrapper over ``brand.project.versioning.resolve_version``
    — the real logic (and the "export the current state = export version
    N once one exists" invariant it establishes) now lives there so
    ``brand/design_state/build.py`` can resolve a version-scoped read the
    same way, without a second implementation of it. This wrapper's only
    job is translating the domain exceptions into the HTTP responses this
    endpoint has always returned."""
    from brand.project.versioning import (
        NoComposedPlanError, VersionDocumentMismatchError, VersionNotFoundError, resolve_version,
    )

    try:
        return resolve_version(project, doc, version_number)
    except VersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VersionDocumentMismatchError as exc:
        raise HTTPException(status_code=422, detail={"error": "version_belongs_to_different_document"}) from exc
    except NoComposedPlanError as exc:
        raise HTTPException(status_code=422, detail={"error": "no_content", "detail": "compose before exporting"}) from exc


def _plan_from_version(version):
    from brand.project.versioning import VersionHasNoPlanError, plan_from_version

    try:
        return plan_from_version(version)
    except VersionHasNoPlanError as exc:
        raise HTTPException(status_code=422, detail={"error": "version_has_no_plan"}) from exc


def _export_snapshot_document(doc, version):
    """Findings are then recomputed fresh against this snapshot rather
    than trusted from whenever the version was saved, which is safe
    because both ``evaluate()`` and ``check_requirements()`` are
    deterministic — recomputing is not "composing against different
    state," it is re-checking the same, frozen state."""
    from brand.project.versioning import snapshot_document_at_version

    return snapshot_document_at_version(doc, version)


def _asset_data_uri_resolver(project):
    """A ``resolve_asset`` for ``render_page_plan``: an Asset id → a
    ``data:`` URI of its real, uploaded bytes, or ``None`` when the id
    doesn't resolve — the exact contract ``render_page_plan`` documents,
    so a missing asset degrades to the honest wireframe box rather than a
    broken export."""
    import base64
    import mimetypes

    asset_dir = _repo().asset_storage_dir(project.id)
    by_id = {a.id: a for a in project.assets}

    def resolve(asset_id: str) -> Optional[str]:
        asset = by_id.get(asset_id)
        if asset is None:
            return None
        path = asset_dir / asset.path
        if not path.exists():
            return None
        content_type = asset.content_type or mimetypes.guess_type(asset.filename)[0] or "application/octet-stream"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    return resolve


@router.post("/{project_id}/documents/{document_id}/export", status_code=201)
def export_document(project_id: str, document_id: str, body: ExportRequest) -> dict[str, Any]:
    """Render Version N of a document to a production PDF.

    Never a fake success (ADOS-M2.2.1 §31): a blocking finding produces a
    ``BLOCKED`` Export and no file; a renderer/Chromium failure produces a
    ``FAILED`` Export with a real reason and no corrupted artifact. Only a
    genuinely rendered PDF is ``COMPLETED``.
    """
    import tempfile
    import uuid as _uuid

    from brand.creative.directions import get_direction
    from brand.creative.evaluate import evaluate
    from brand.export.exporters import html_to_pdf
    from brand.project.model import Export, ExportStatus, ExportValidationState
    from brand.project.requirements import check_requirements
    from brand.store.brand_repo import BrandNotFound
    from brand.templates.renderers import render_page_plan

    project = _load(project_id)
    idx = _document_index(project, document_id)
    doc = project.documents[idx]

    if not project.brand_id:
        raise HTTPException(status_code=422, detail={"error": "no_brand_attached"})
    try:
        brand = _brand_repo().get(project.brand_id, project.brand_version)
    except BrandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    project, version = _resolve_export_version(project, doc, body.version_number)
    plan = _plan_from_version(version)
    direction = get_direction(version.direction_id)
    tokens = brand.resolve_tokens()

    evaluation = evaluate(plan, direction, tokens)
    snapshot = _export_snapshot_document(doc, version)
    requirement_findings = check_requirements(snapshot, project)
    findings = list(evaluation.report.findings) + requirement_findings

    blocking = [f for f in findings if f.severity.value in ("ERROR", "BLOCK")]
    warning = [f for f in findings if f.severity.value == "WARN"]
    validation_state = (
        ExportValidationState.BLOCKED if blocking
        else ExportValidationState.WARNINGS if warning
        else ExportValidationState.PASSED
    )

    export_id = _uuid.uuid4().hex[:12]
    extension = "html" if body.format == "html" else "pdf"
    filename = f"{doc.name}-v{version.number}.{extension}".replace("/", "-")

    def _save(export) -> dict[str, Any]:
        nonlocal project
        project = _touch(project.model_copy(update={"exports": project.exports + (export,)}))
        _repo().save(project)
        return {"export": export.model_dump(mode="json"), "findings": [f.to_dict() for f in findings]}

    if blocking:
        export = Export(
            id=export_id, document_id=doc.id, version_number=version.number,
            format=body.format, filename=filename, page_count=plan.page_count,
            validation_state=validation_state, status=ExportStatus.BLOCKED,
        )
        return _save(export)

    resolver = _asset_data_uri_resolver(project)
    rendered = render_page_plan(plan, tokens, resolve_asset=resolver)

    export_dir = _repo().export_storage_dir(project.id)
    export_dir.mkdir(parents=True, exist_ok=True)

    if body.format == "html":
        # The Website projection: the same render_page_plan HTML every PDF
        # export already prints from, written out directly. No second
        # renderer, no Chromium dependency for this format at all.
        html_out_path = export_dir / f"{export_id}.html"
        html_out_path.write_text(rendered.content, encoding="utf-8")
        export = Export(
            id=export_id, document_id=doc.id, version_number=version.number,
            format="html", filename=filename, page_count=plan.page_count,
            validation_state=validation_state, status=ExportStatus.COMPLETED,
            path=f"{export_id}.html",
        )
        return _save(export)

    pdf_path = export_dir / f"{export_id}.pdf"
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "document.html"
        html_path.write_text(rendered.content, encoding="utf-8")
        result = html_to_pdf(html_path, pdf_path)

    if not result.ok:
        logger.error("export %s failed for document %s: %s", export_id, doc.id, result.reason)
        export = Export(
            id=export_id, document_id=doc.id, version_number=version.number,
            format="pdf", filename=filename, page_count=plan.page_count,
            validation_state=validation_state, status=ExportStatus.FAILED,
            error=result.reason or "PDF rendering failed",
        )
        return _save(export)

    export = Export(
        id=export_id, document_id=doc.id, version_number=version.number,
        format="pdf", filename=filename, page_count=plan.page_count,
        validation_state=validation_state, status=ExportStatus.COMPLETED,
        path=f"{export_id}.pdf",
    )
    return _save(export)


@router.get("/{project_id}/documents/{document_id}/exports")
def list_document_exports(project_id: str, document_id: str) -> dict[str, Any]:
    project = _load(project_id)
    _document_index(project, document_id)  # 404s if absent
    exports = [e for e in project.exports if e.document_id == document_id]
    return {
        "exports": [
            e.model_dump(mode="json") for e in sorted(exports, key=lambda e: e.created_at, reverse=True)
        ]
    }


@router.get("/{project_id}/exports/{export_id}/file")
def download_export(project_id: str, export_id: str):
    project = _load(project_id)
    export = next((e for e in project.exports if e.id == export_id), None)
    if export is None:
        raise HTTPException(status_code=404, detail=f"no export {export_id!r} in project {project_id!r}")
    if export.status.value != "completed" or not export.path:
        raise HTTPException(
            status_code=409, detail={"error": "export_not_available", "status": export.status.value},
        )
    path = _repo().export_storage_dir(project.id) / export.path
    if not path.exists():
        raise HTTPException(status_code=404, detail="export file missing from storage")
    media_type = "text/html" if export.format == "html" else "application/pdf"
    return FileResponse(path, media_type=media_type, filename=export.filename)
