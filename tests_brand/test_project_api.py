"""
api/routers/ados_project.py -- the M2.1 Project HTTP surface.

Mounted on the real FastAPI app, so these tests also assert the router is
actually registered. The store is redirected to a tmp directory per test so
nothing here writes to the repository's real storage/ados-projects.
"""

from __future__ import annotations

import io

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

BRAND_ID = "5747d10b-0000-4000-8000-000000000001"


def _app():
    """See tests_brand/test_api.py's _app() for why this falls back to a bare
    app carrying only the router under test when the full app's other
    dependencies (render pipeline, auth stack) are unavailable."""
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
    # _PROJECT_STORAGE_ROOT is read from the environment once at import time
    # (the same convention api/routers/brand.py already uses for _BRAND_ROOT),
    # so isolating a test means patching the module attribute directly --
    # monkeypatch.setenv alone would have no effect on an already-imported module.
    import api.routers.ados_project as ados_project_router
    import api.routers.brand as brand_router

    monkeypatch.setattr(ados_project_router, "_PROJECT_STORAGE_ROOT", str(tmp_path / "ados-projects"))
    # A fresh checkout's brand store is empty until _seeded_repo() (reused
    # from brand.py -- see _brand_repo() in ados_project.py) seeds Studio
    # Nord into it. Isolating this to tmp_path reproduces exactly that
    # "nothing seeded yet" starting condition, the same way test_api.py's
    # own fixture does for brand.py's tests.
    monkeypatch.setattr(brand_router, "_BRAND_ROOT", str(tmp_path / "brands"))

    with TestClient(_app()) as c:
        yield c


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


def test_main_registers_the_router():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "api" / "main.py").read_text()
    assert "from api.routers import ados_project as ados_project_router" in source
    assert 'app.include_router(ados_project_router.router, prefix="/api/v2"' in source


def test_the_router_is_mounted(client):
    r = client.get("/api/v2/ados-projects")
    assert r.status_code == 200


def test_ados_projects_does_not_collide_with_revelations_own_projects_router(client):
    """REVELATION's unrelated /api/v2/projects (v2_projects.py) must be untouched."""
    r = client.get("/api/v2/ados-projects")
    assert r.status_code == 200
    assert "projects" in r.json()


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------


def test_create_and_get_project(client):
    created = client.post("/api/v2/ados-projects", json={"name": "Smoke Test", "description": "d"}).json()
    assert created["name"] == "Smoke Test"

    fetched = client.get(f"/api/v2/ados-projects/{created['id']}").json()
    assert fetched["id"] == created["id"]


def test_unknown_project_is_404(client):
    r = client.get("/api/v2/ados-projects/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_update_project(client):
    p = client.post("/api/v2/ados-projects", json={"name": "Original"}).json()
    r = client.patch(f"/api/v2/ados-projects/{p['id']}", json={"name": "Renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"


def test_delete_project(client):
    p = client.post("/api/v2/ados-projects", json={"name": "To delete"}).json()
    r = client.delete(f"/api/v2/ados-projects/{p['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/v2/ados-projects/{p['id']}").status_code == 404


def test_attach_brand_validates_against_the_real_brand_store(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()

    ok = client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    assert ok.status_code == 200
    assert ok.json()["brand_id"] == BRAND_ID

    bad = client.put(
        f"/api/v2/ados-projects/{p['id']}/brand",
        json={"brand_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert bad.status_code == 404


# ---------------------------------------------------------------------------
# Documents + content
# ---------------------------------------------------------------------------


def _project_with_brand(client) -> dict:
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    return p


def test_create_document_validates_direction(client):
    p = _project_with_brand(client)
    ok = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc", "direction_id": "editorial-quiet"})
    assert ok.status_code == 201

    bad = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc", "direction_id": "not-a-direction"})
    assert bad.status_code == 404


def test_add_valid_content_items_of_each_kind(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    doc_url = f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content"

    text = client.post(doc_url, json={"kind": "text", "text": "Some narrative."})
    assert text.status_code == 201

    fact = client.post(doc_url, json={"kind": "fact", "label": "Location", "value": "Leeds"})
    assert fact.status_code == 201

    metric = client.post(
        doc_url,
        json={"kind": "metric", "label": "Floor area", "value": 1200, "unit": "m2", "provenance": "brief"},
    )
    assert metric.status_code == 201
    assert len(metric.json()["content_items"]) == 3


def test_add_invalid_content_item_is_rejected_with_the_composers_reason(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()

    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "metric", "label": "Bad", "value": 5, "unit": "m2", "provenance": ""},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "invalid_content"
    assert "provenance" in str(r.json()["detail"]["errors"])


def test_remove_content_item(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "x"},
    ).json()
    item_id = doc["content_items"][0]["id"]

    r = client.delete(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content/{item_id}")
    assert r.status_code == 200
    assert r.json()["content_items"] == []


def test_duplicate_document(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/duplicate")
    assert r.status_code == 201
    assert r.json()["id"] != doc["id"]
    assert "copy" in r.json()["name"]


# ---------------------------------------------------------------------------
# Compose -- the one endpoint that calls the real Composer directly
# ---------------------------------------------------------------------------


def test_compose_produces_a_real_pageplan(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "The Malthouse is a converted brewery."},
    )

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 200
    body = r.json()
    assert len(body["plan"]["pages"]) > 0
    assert body["evaluation"] is not None


def test_compose_without_a_brand_is_rejected(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "no_brand_attached"


def test_compose_without_content_is_rejected(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "no_content"


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


def test_upload_list_download_delete_asset(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()

    upload = client.post(
        f"/api/v2/ados-projects/{p['id']}/assets",
        files={"file": ("test.png", io.BytesIO(b"\x89PNGfakebytes"), "image/png")},
    )
    assert upload.status_code == 201
    asset = upload.json()

    listed = client.get(f"/api/v2/ados-projects/{p['id']}/assets").json()
    assert len(listed["assets"]) == 1

    downloaded = client.get(f"/api/v2/ados-projects/{p['id']}/assets/{asset['id']}/file")
    assert downloaded.status_code == 200
    assert downloaded.content == b"\x89PNGfakebytes"

    deleted = client.delete(f"/api/v2/ados-projects/{p['id']}/assets/{asset['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v2/ados-projects/{p['id']}/assets/{asset['id']}/file").status_code == 404


def test_upload_rejects_unsupported_file_type(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/assets",
        files={"file": ("virus.exe", io.BytesIO(b"x"), "application/octet-stream")},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "unsupported_file_type"


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


def test_save_list_and_restore_version(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "original text"},
    )
    compose_body = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose").json()

    saved = client.post(
        f"/api/v2/ados-projects/{p['id']}/versions",
        json={"document_id": doc["id"], "label": "v1", "plan": compose_body["plan"]},
    )
    assert saved.status_code == 201
    assert saved.json()["number"] == 1

    versions = client.get(f"/api/v2/ados-projects/{p['id']}/versions").json()
    assert len(versions["versions"]) == 1

    # mutate the document, then restore to the saved snapshot
    item_id = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}").json()["content_items"][0]["id"]
    client.delete(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content/{item_id}")
    assert client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}").json()["content_items"] == []

    restored = client.post(f"/api/v2/ados-projects/{p['id']}/versions/1/restore")
    assert restored.status_code == 200
    assert len(restored.json()["content_items"]) == 1
    assert restored.json()["content_items"][0]["text"] == "original text"


def test_restore_unknown_version_is_404(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    r = client.post(f"/api/v2/ados-projects/{p['id']}/versions/99/restore")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Data isolation -- a manipulated id must never cross a project boundary
# ---------------------------------------------------------------------------


def test_a_document_id_from_one_project_is_invisible_through_another(client):
    a = client.post("/api/v2/ados-projects", json={"name": "Project A"}).json()
    b = client.post("/api/v2/ados-projects", json={"name": "Project B"}).json()
    doc_a = client.post(f"/api/v2/ados-projects/{a['id']}/documents", json={"name": "A doc"}).json()

    assert client.get(f"/api/v2/ados-projects/{b['id']}/documents/{doc_a['id']}").status_code == 404
    assert client.patch(
        f"/api/v2/ados-projects/{b['id']}/documents/{doc_a['id']}", json={"name": "hacked"}
    ).status_code == 404
    assert client.delete(f"/api/v2/ados-projects/{b['id']}/documents/{doc_a['id']}").status_code == 404

    # the original, reached through its real project, must be untouched
    intact = client.get(f"/api/v2/ados-projects/{a['id']}/documents/{doc_a['id']}")
    assert intact.status_code == 200
    assert intact.json()["name"] == "A doc"


def test_an_asset_id_from_one_project_is_invisible_through_another(client):
    a = client.post("/api/v2/ados-projects", json={"name": "Project A"}).json()
    b = client.post("/api/v2/ados-projects", json={"name": "Project B"}).json()
    asset_a = client.post(
        f"/api/v2/ados-projects/{a['id']}/assets",
        files={"file": ("test.png", io.BytesIO(b"bytes"), "image/png")},
    ).json()

    assert client.get(f"/api/v2/ados-projects/{b['id']}/assets/{asset_a['id']}/file").status_code == 404
    assert client.delete(f"/api/v2/ados-projects/{b['id']}/assets/{asset_a['id']}").status_code == 404

    # the original asset must survive the failed cross-project delete attempt
    intact = client.get(f"/api/v2/ados-projects/{a['id']}/assets/{asset_a['id']}/file")
    assert intact.status_code == 200
