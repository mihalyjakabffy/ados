"""
ADOS-M2.2.1 §28 -- regression coverage for the ``_touch_doc`` fix
(api/routers/ados_project.py): every one of a Document's own mutations
must move ITS OWN ``updated_at``, not just the Project's. A client polling
a single document (to re-check its requirement findings, or to know
whether it needs re-fetching) that misses this on any mutation path is
the exact bug ADOS-M2.2 fixed once already.

test_document_workflows_api.py already covers content and section
mutations; this file is the fuller sweep §28 asks for -- project
references, metadata, and the ADOS-M2.2.1 P3/P4 structured-data
endpoints, each checked in isolation so a regression on any one of them
fails on its own line, not buried in one long chain.
"""

from __future__ import annotations

import pytest

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


def _get_doc(client, project_id, document_id):
    return client.get(f"/api/v2/ados-projects/{project_id}/documents/{document_id}").json()


def test_project_reference_mutations_touch_the_document(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    ref = client.post("/api/v2/ados-projects", json={"name": "Ref"}).json()
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Portfolio", "document_type_id": "portfolio"},
    ).json()
    t0 = doc["updated_at"]

    after_add = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/project-refs",
        json={"project_id": ref["id"]},
    ).json()
    assert after_add["updated_at"] != t0

    after_remove = client.delete(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/project-refs/{ref['id']}",
    ).json()
    assert after_remove["updated_at"] != after_add["updated_at"]


def test_metadata_patch_touches_the_document(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    t0 = doc["updated_at"]

    after_patch = client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}",
        json={"metadata": {"location": "Leeds"}},
    ).json()
    assert after_patch["updated_at"] != t0


def test_presentation_option_mutations_touch_the_document(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Deck", "document_type_id": "client-presentation"},
    ).json()
    t0 = doc["updated_at"]

    after_add = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/options",
        json={"title": "Option A"},
    ).json()
    assert after_add["updated_at"] != t0

    option_id = after_add["presentation_options"][0]["id"]
    after_remove = client.delete(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/options/{option_id}",
    ).json()
    assert after_remove["updated_at"] != after_add["updated_at"]


def test_decision_mutations_touch_the_document(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Deck", "document_type_id": "client-presentation"},
    ).json()
    t0 = doc["updated_at"]

    after_add = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/decisions",
        json={"title": "Proceed"},
    ).json()
    assert after_add["updated_at"] != t0

    decision_id = after_add["decisions"][0]["id"]
    after_remove = client.delete(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/decisions/{decision_id}",
    ).json()
    assert after_remove["updated_at"] != after_add["updated_at"]


def test_action_item_mutations_touch_the_document(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Deck", "document_type_id": "client-presentation"},
    ).json()
    t0 = doc["updated_at"]

    after_add = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/action-items",
        json={"description": "Send fee proposal"},
    ).json()
    assert after_add["updated_at"] != t0

    item_id = after_add["action_items"][0]["id"]
    after_remove = client.delete(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/action-items/{item_id}",
    ).json()
    assert after_remove["updated_at"] != after_add["updated_at"]


def test_meeting_mutations_touch_the_document(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Minutes", "document_type_id": "internal-documentation"},
    ).json()
    t0 = doc["updated_at"]

    after_add = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/meetings",
        json={"title": "Design review"},
    ).json()
    assert after_add["updated_at"] != t0

    meeting_id = after_add["meetings"][0]["id"]
    after_remove = client.delete(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/meetings/{meeting_id}",
    ).json()
    assert after_remove["updated_at"] != after_add["updated_at"]


def test_compose_touches_the_document(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "Some narrative."},
    )
    t0 = _get_doc(client, p["id"], doc["id"])["updated_at"]

    composed = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose").json()
    assert composed["document"]["updated_at"] != t0


def test_export_does_not_touch_a_different_documents_updated_at(client):
    """A per-document poller must never see a false-positive move: exporting
    Document A must not touch Document B's own ``updated_at`` in the same
    project (only the aggregate Project timestamp is shared)."""
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    doc_a = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "A"}).json()
    doc_b = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "B"}).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc_a['id']}/content",
        json={"kind": "text", "text": "Some narrative."},
    )
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc_a['id']}/compose")
    t0_b = _get_doc(client, p["id"], doc_b["id"])["updated_at"]

    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc_a['id']}/export", json={})

    assert _get_doc(client, p["id"], doc_b["id"])["updated_at"] == t0_b
