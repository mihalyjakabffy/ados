"""
api/routers/ados_project.py's two ADOS-M4.3 endpoints:
``POST .../content/{item_id}/propagate`` and
``POST .../brand/propagate`` — the HTTP shell around
``brand.project.propagation``, exercised the same isolated-tmp_path way
tests_brand/test_project_api.py already tests the rest of this router.
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


def _new_project_with_brand(client, *, name: str = "Malthouse") -> str:
    project = client.post("/api/v2/ados-projects", json={"name": name}).json()
    client.put(f"/api/v2/ados-projects/{project['id']}/brand", json={"brand_id": BRAND_ID})
    return project["id"]


def _new_document(client, project_id: str, *, name: str = "Doc") -> str:
    return client.post(f"/api/v2/ados-projects/{project_id}/documents", json={"name": name}).json()["id"]


def test_propagate_content_recomposes_only_the_referencing_document(client):
    project_id = _new_project_with_brand(client)

    shared = client.post(
        f"/api/v2/ados-projects/{project_id}/content",
        json={"kind": "text", "text": "shared context " * 20},
    ).json()["content_items"][-1]

    referencing = _new_document(client, project_id, name="Uses the shared item")
    client.put(
        f"/api/v2/ados-projects/{project_id}/documents/{referencing}/content-selection",
        json={"content_item_ids": [shared["id"]]},
    )

    unrelated = _new_document(client, project_id, name="Has nothing to do with it")
    client.post(
        f"/api/v2/ados-projects/{project_id}/documents/{unrelated}/content",
        json={"kind": "text", "text": "unrelated own content " * 20},
    )

    r = client.post(f"/api/v2/ados-projects/{project_id}/content/{shared['id']}/propagate")
    assert r.status_code == 200
    body = r.json()

    touched_ids = {t["document_id"] for t in body["touched"]}
    assert touched_ids == {referencing}
    assert body["unaffected"] == [unrelated]
    assert body["touched"][0]["recomposed"] is True

    doc = client.get(f"/api/v2/ados-projects/{project_id}/documents/{referencing}").json()
    assert doc["latest_plan"] is not None


def test_propagate_content_without_a_brand_is_a_422(client):
    project = client.post("/api/v2/ados-projects", json={"name": "No brand yet"}).json()
    r = client.post(f"/api/v2/ados-projects/{project['id']}/content/whatever/propagate")
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "no_brand_attached"


def test_propagate_content_dangling_item_reports_no_content(client):
    """A document that selected an item since removed from the pool is
    recomposed and honestly reports no_content if that leaves it with
    nothing -- never a 500, never silently skipped."""
    project_id = _new_project_with_brand(client)
    shared = client.post(
        f"/api/v2/ados-projects/{project_id}/content",
        json={"kind": "text", "text": "will be removed " * 20},
    ).json()["content_items"][-1]

    doc_id = _new_document(client, project_id)
    client.put(
        f"/api/v2/ados-projects/{project_id}/documents/{doc_id}/content-selection",
        json={"content_item_ids": [shared["id"]]},
    )
    client.delete(f"/api/v2/ados-projects/{project_id}/content/{shared['id']}")

    r = client.post(f"/api/v2/ados-projects/{project_id}/content/{shared['id']}/propagate")
    assert r.status_code == 200
    body = r.json()
    assert body["touched"][0]["document_id"] == doc_id
    assert body["touched"][0]["recomposed"] is False
    assert body["touched"][0]["reason"] == "no_content"


def test_propagate_brand_moves_the_project_and_recomposes_every_document(client):
    import api.routers.brand as brand_router
    from brand.examples.studio_nord import studio_nord

    project_id = _new_project_with_brand(client)

    doc_a = _new_document(client, project_id, name="A")
    client.post(
        f"/api/v2/ados-projects/{project_id}/documents/{doc_a}/content",
        json={"kind": "text", "text": "first document content " * 20},
    )
    doc_b = _new_document(client, project_id, name="B")
    client.post(
        f"/api/v2/ados-projects/{project_id}/documents/{doc_b}/content",
        json={"kind": "text", "text": "second document content " * 20},
    )

    new_version = studio_nord().bump("minor", changelog="new palette").approved().published()
    brand_router._seeded_repo().save(new_version)

    r = client.post(
        f"/api/v2/ados-projects/{project_id}/brand/propagate",
        json={"brand_version": new_version.version},
    )
    assert r.status_code == 200
    body = r.json()

    assert body["brand_version"] == new_version.version
    assert body["unaffected"] == []
    assert {t["document_id"] for t in body["touched"]} == {doc_a, doc_b}
    assert all(t["recomposed"] for t in body["touched"])

    project = client.get(f"/api/v2/ados-projects/{project_id}").json()
    assert project["brand_version"] == new_version.version


def test_propagate_brand_unknown_version_is_a_404(client):
    project_id = _new_project_with_brand(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/brand/propagate",
        json={"brand_version": "9.9.9"},
    )
    assert r.status_code == 404


def test_propagate_brand_never_creates_a_project_version(client):
    project_id = _new_project_with_brand(client)
    doc_id = _new_document(client, project_id)
    client.post(
        f"/api/v2/ados-projects/{project_id}/documents/{doc_id}/content",
        json={"kind": "text", "text": "content " * 20},
    )

    import api.routers.brand as brand_router
    from brand.examples.studio_nord import studio_nord

    new_version = studio_nord().bump("patch").approved().published()
    brand_router._seeded_repo().save(new_version)

    client.post(
        f"/api/v2/ados-projects/{project_id}/brand/propagate",
        json={"brand_version": new_version.version},
    )

    versions = client.get(f"/api/v2/ados-projects/{project_id}/versions").json()["versions"]
    assert versions == []
