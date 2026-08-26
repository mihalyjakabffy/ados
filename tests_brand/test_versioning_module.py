"""
brand/project/versioning.py -- ADOS-M2.5 P2b.

Two layers of coverage: the pure domain functions in isolation (no
FastAPI, no HTTP), and the API-level guarantee that a Version's content
survives the shared pool it was resolved from being edited or emptied
out from under it after the fact.
"""

from __future__ import annotations

import pytest

from brand.project.model import ContentItem, ContentItemKind, Document, Project
from brand.project.versioning import (
    NoComposedPlanError,
    VersionDocumentMismatchError,
    VersionHasNoPlanError,
    VersionNotFoundError,
    build_version,
    plan_from_version,
    resolve_full_content,
    resolve_version,
    snapshot_document_at_version,
)


def _project_and_doc(*, shared_text="Shared.", own_text="Own.", select_shared=True):
    shared = ContentItem(kind=ContentItemKind.TEXT, text=shared_text)
    project = Project(name="P", content_items=(shared,))
    own = ContentItem(kind=ContentItemKind.TEXT, text=own_text)
    doc = Document(
        project_id=project.id, name="Doc", content_items=(own,),
        content_selection=(shared.id,) if select_shared else (),
    )
    project = project.model_copy(update={"documents": (doc,)})
    return project, doc, shared


def test_resolve_full_content_merges_own_and_shared():
    project, doc, shared = _project_and_doc()
    resolved = resolve_full_content(doc, project)
    texts = {i.text for i in resolved}
    assert texts == {"Own.", "Shared."}


def test_resolve_full_content_skips_a_dangling_selection():
    project, doc, _ = _project_and_doc()
    project = project.model_copy(update={"content_items": ()})  # shared item vanished
    resolved = resolve_full_content(doc, project)
    assert [i.text for i in resolved] == ["Own."]


def test_build_version_freezes_the_resolved_union():
    project, doc, _ = _project_and_doc()
    version = build_version(doc, project, label="v1")
    assert {i.text for i in version.content_items} == {"Own.", "Shared."}
    assert version.number == 1
    assert version.label == "v1"


def test_resolve_version_with_no_plan_raises():
    project, doc, _ = _project_and_doc()
    with pytest.raises(NoComposedPlanError):
        resolve_version(project, doc, None)


def test_resolve_version_unknown_number_raises():
    project, doc, _ = _project_and_doc()
    with pytest.raises(VersionNotFoundError):
        resolve_version(project, doc, 99)


def test_resolve_version_wrong_document_raises():
    project, doc, _ = _project_and_doc()
    version = build_version(doc, project, plan={"pages": [], "plan_hash": "x"})
    project = project.model_copy(update={"versions": (version,)})
    other_doc = Document(project_id=project.id, name="Other")
    with pytest.raises(VersionDocumentMismatchError):
        resolve_version(project, other_doc, version.number)


def test_resolve_version_auto_builds_from_latest_plan():
    project, doc, _ = _project_and_doc()
    doc = doc.model_copy(update={"latest_plan": {"pages": [], "plan_hash": "abc"}})
    project = project.model_copy(update={"documents": (doc,)})
    new_project, version = resolve_version(project, doc, None)
    assert version.number == 1
    assert len(new_project.versions) == 1


def test_plan_from_version_strips_the_derived_plan_hash_key():
    project, doc, _ = _project_and_doc()
    version = build_version(doc, project, plan={
        "document": "x", "project_name": "P", "brand_id": "b", "brand_version": "1.0.0",
        "direction": "editorial-quiet", "content_hash": "h", "ados_edition": "1.0",
        "pages": [], "rejected": [], "notes": [], "plan_hash": "should-be-stripped",
    })
    plan = plan_from_version(version)
    assert plan.page_count == 0


def test_plan_from_version_with_no_plan_raises():
    project, doc, _ = _project_and_doc()
    version = build_version(doc, project)
    assert version.plan is None
    with pytest.raises(VersionHasNoPlanError):
        plan_from_version(version)


def test_snapshot_document_at_version_clears_content_selection():
    project, doc, _ = _project_and_doc()
    version = build_version(doc, project, plan={"pages": [], "plan_hash": "x"})
    snapshot = snapshot_document_at_version(doc, version)
    assert snapshot.content_selection == ()
    assert {i.text for i in snapshot.content_items} == {"Own.", "Shared."}
    assert snapshot.latest_plan == version.plan


# ---------------------------------------------------------------------------
# API-level: the version-freezes-shared-content guarantee end to end
# ---------------------------------------------------------------------------

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

BRAND_ID = "5747d10b-0000-4000-8000-000000000001"


def _app():
    try:
        from api.main import app

        return app
    except BaseException:                                  # noqa: BLE001
        from fastapi import FastAPI

        from api.routers import ados_project as ados_project_router

        app = FastAPI()
        app.include_router(ados_project_router.router, prefix="/api/v2", tags=["ados-projects"])
        return app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import api.routers.ados_project as ados_project_router
    import api.routers.brand as brand_router

    monkeypatch.setattr(ados_project_router, "_PROJECT_STORAGE_ROOT", str(tmp_path / "ados-projects"))
    monkeypatch.setattr(brand_router, "_BRAND_ROOT", str(tmp_path / "brands"))

    with TestClient(_app()) as c:
        yield c


def test_version_survives_the_shared_item_it_referenced_being_deleted(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    shared = client.post(
        f"/api/v2/ados-projects/{p['id']}/content", json={"kind": "text", "text": "Original fact."},
    ).json()["content_items"][0]
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.put(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content-selection",
        json={"content_item_ids": [shared["id"]]},
    )
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    v1 = client.post(f"/api/v2/ados-projects/{p['id']}/versions", json={"document_id": doc["id"]}).json()
    assert len(v1["content_items"]) == 1

    client.delete(f"/api/v2/ados-projects/{p['id']}/content/{shared['id']}")

    versions = client.get(f"/api/v2/ados-projects/{p['id']}/versions").json()["versions"]
    v1_after = next(v for v in versions if v["number"] == 1)
    assert v1_after == v1

    export = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={"version_number": 1},
    )
    assert export.status_code == 201
    assert export.json()["export"]["status"] == "completed"


def test_restore_clears_content_selection(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    shared = client.post(
        f"/api/v2/ados-projects/{p['id']}/content", json={"kind": "text", "text": "Shared."},
    ).json()["content_items"][0]
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.put(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content-selection",
        json={"content_item_ids": [shared["id"]]},
    )
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    client.post(f"/api/v2/ados-projects/{p['id']}/versions", json={"document_id": doc["id"]})

    restored = client.post(f"/api/v2/ados-projects/{p['id']}/versions/1/restore")
    assert restored.status_code == 200
    assert restored.json()["content_selection"] == []
    assert len(restored.json()["content_items"]) == 1
