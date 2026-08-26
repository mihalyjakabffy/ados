"""
ADOS-M2.5 §6 -- shared, project-level content.

The central acceptance test for "content is no longer document-scoped":
two different documents (a typed Project Report and an untyped document)
compose successfully from the SAME shared content item, with neither
holding a private copy of it. Editing/removing the shared item is a
project-level operation, not something either document owns.
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


def _project_with_brand(client) -> dict:
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    return p


def test_project_data_patch_merges_not_replaces(client):
    p = _project_with_brand(client)
    client.patch(f"/api/v2/ados-projects/{p['id']}", json={"project_data": {"client": "Acme"}})
    r = client.patch(f"/api/v2/ados-projects/{p['id']}", json={"project_data": {"location": "Leeds"}})
    assert r.json()["project_data"] == {"client": "Acme", "location": "Leeds"}


def test_add_list_remove_shared_content_item(client):
    p = _project_with_brand(client)
    added = client.post(f"/api/v2/ados-projects/{p['id']}/content", json={"kind": "text", "text": "Shared fact."})
    assert added.status_code == 201
    item = added.json()["content_items"][0]

    listed = client.get(f"/api/v2/ados-projects/{p['id']}/content").json()
    assert len(listed["content_items"]) == 1

    removed = client.delete(f"/api/v2/ados-projects/{p['id']}/content/{item['id']}")
    assert removed.status_code == 200
    assert removed.json()["content_items"] == []


def test_invalid_shared_content_item_is_422(client):
    p = _project_with_brand(client)
    r = client.post(f"/api/v2/ados-projects/{p['id']}/content", json={"kind": "metric", "label": "Area", "value": 5, "unit": "m2", "provenance": ""})
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "invalid_content_item"


def test_content_selection_rejects_unknown_ids(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    r = client.put(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content-selection",
        json={"content_item_ids": ["not-a-real-id"]},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "unknown_shared_content_item"


def test_two_documents_share_one_content_item(client):
    """The core M2.5 claim: one project-level fact, two independent
    documents composing from it, neither holding a private copy."""
    p = _project_with_brand(client)
    shared = client.post(
        f"/api/v2/ados-projects/{p['id']}/content",
        json={"kind": "text", "text": "The Malthouse is a converted Victorian brewery."},
    ).json()["content_items"][0]

    doc_a = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Report", "document_type_id": "project-report"},
    ).json()
    doc_b = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Free-form"}).json()

    for doc in (doc_a, doc_b):
        sel = client.put(
            f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content-selection",
            json={"content_item_ids": [shared["id"]]},
        )
        assert sel.status_code == 200
        assert sel.json()["content_selection"] == [shared["id"]]
        assert sel.json()["content_items"] == []  # no private copy was made

    for doc in (doc_a, doc_b):
        composed = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
        assert composed.status_code == 200, composed.text
        assert len(composed.json()["plan"]["pages"]) > 0


def test_removing_a_shared_item_does_not_break_a_document_that_selected_it(client):
    """A dangling selection is fail-soft (skip), not a 500 -- the same
    posture Portfolio's stale project_refs already has."""
    p = _project_with_brand(client)
    shared = client.post(
        f"/api/v2/ados-projects/{p['id']}/content",
        json={"kind": "text", "text": "A fact that will be deleted."},
    ).json()["content_items"][0]
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.put(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content-selection",
        json={"content_item_ids": [shared["id"]]},
    )
    client.delete(f"/api/v2/ados-projects/{p['id']}/content/{shared['id']}")

    r = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}")
    assert r.status_code == 200
    assert r.json()["content_selection"] == [shared["id"]]  # not silently cleaned up

    composed = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert composed.status_code == 422  # no content at all now -- an honest error, not a crash
    assert composed.json()["detail"]["error"] == "no_content"


def test_a_selected_shared_item_is_sectionable(client):
    p = _project_with_brand(client)
    shared = client.post(
        f"/api/v2/ados-projects/{p['id']}/content",
        json={"kind": "text", "text": "Design concept narrative."},
    ).json()["content_items"][0]
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Report", "document_type_id": "project-report"},
    ).json()
    client.put(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content-selection",
        json={"content_item_ids": [shared["id"]]},
    )
    section = next(s for s in doc["sections"] if s["kind"] == "design-concept")
    r = client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections/{section['id']}",
        json={"content_item_ids": [shared["id"]]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["sections"][0]["content_item_ids"] == [shared["id"]] or any(
        s["content_item_ids"] == [shared["id"]] for s in r.json()["sections"]
    )


def test_unselected_shared_item_cannot_be_assigned_to_a_section(client):
    p = _project_with_brand(client)
    shared = client.post(
        f"/api/v2/ados-projects/{p['id']}/content",
        json={"kind": "text", "text": "Not yet selected."},
    ).json()["content_items"][0]
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Report", "document_type_id": "project-report"},
    ).json()
    section = doc["sections"][0]
    r = client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections/{section['id']}",
        json={"content_item_ids": [shared["id"]]},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "unknown_content_item"
