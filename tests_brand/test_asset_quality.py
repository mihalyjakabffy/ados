"""
ADOS-M2.2.1 P5 -- asset quality checks (IMG-001..004).

Real images (via Pillow) uploaded through the real /assets endpoint, so
Asset.width_px/height_px are the file's own genuine pixel dimensions, not
a stubbed value -- the same discipline as the export tests: nothing here
is mocked.
"""

from __future__ import annotations

import io

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

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


def _upload_png(client, project_id, filename, width, height, color="red"):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="PNG")
    buf.seek(0)
    r = client.post(f"/api/v2/ados-projects/{project_id}/assets", files={"file": (filename, buf, "image/png")})
    assert r.status_code == 201, r.text
    return r.json()


def _typed_doc(client, project_id, document_type_id="case-study"):
    return client.post(
        f"/api/v2/ados-projects/{project_id}/documents",
        json={"name": "Doc", "document_type_id": document_type_id},
    ).json()


def _codes(client, project_id, document_id):
    return [f["code"] for f in client.get(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/requirements").json()["findings"]]


def test_upload_reads_real_pixel_dimensions(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    asset = _upload_png(client, p["id"], "photo.png", 1024, 768)
    assert asset["width_px"] == 1024
    assert asset["height_px"] == 768


def test_upload_of_a_non_raster_file_leaves_dimensions_none(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/assets",
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 not a real pdf"), "application/pdf")},
    )
    assert r.status_code == 201
    assert r.json()["width_px"] is None
    assert r.json()["height_px"] is None


def test_img001_flags_a_missing_caption(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    asset = _upload_png(client, p["id"], "a.png", 1600, 1200)
    doc = _typed_doc(client, p["id"])
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "image", "asset_id": asset["id"], "aspect": "4:3", "provenance": "Practice archive"},
    )
    codes = _codes(client, p["id"], doc["id"])
    assert "IMG-001" in codes
    assert "IMG-002" not in codes  # provenance was set


def test_img002_flags_a_missing_credit(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    asset = _upload_png(client, p["id"], "a.png", 1600, 1200)
    doc = _typed_doc(client, p["id"])
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "image", "asset_id": asset["id"], "aspect": "4:3", "caption": "Site photo"},
    )
    codes = _codes(client, p["id"], doc["id"])
    assert "IMG-002" in codes
    assert "IMG-001" not in codes  # caption was set


def test_img003_flags_a_low_resolution_image(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    small = _upload_png(client, p["id"], "small.png", 400, 300)
    doc = _typed_doc(client, p["id"])
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "image", "asset_id": small["id"], "aspect": "4:3", "caption": "x", "provenance": "y"},
    )
    assert "IMG-003" in _codes(client, p["id"], doc["id"])


def test_img003_does_not_flag_a_high_resolution_image(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    big = _upload_png(client, p["id"], "big.png", 1600, 1200)
    doc = _typed_doc(client, p["id"])
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "image", "asset_id": big["id"], "aspect": "4:3", "caption": "x", "provenance": "y"},
    )
    assert "IMG-003" not in _codes(client, p["id"], doc["id"])


def test_img003_does_not_guess_at_a_non_raster_asset(client):
    """A PDF's dimensions are unknown, not zero -- IMG-003 must not treat
    "unknown" as "too small" (the whole point of not trusting file size)."""
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    pdf = client.post(
        f"/api/v2/ados-projects/{p['id']}/assets",
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")},
    ).json()
    doc = _typed_doc(client, p["id"])
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "image", "asset_id": pdf["id"], "aspect": "4:3", "caption": "x", "provenance": "y"},
    )
    assert "IMG-003" not in _codes(client, p["id"], doc["id"])


def test_img004_flags_a_dangling_asset_reference(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = _typed_doc(client, p["id"])
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "image", "asset_id": "does-not-exist", "aspect": "4:3", "caption": "x", "provenance": "y"},
    )
    codes = _codes(client, p["id"], doc["id"])
    assert "IMG-004" in codes


def test_a_well_formed_image_trips_no_img_finding(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    big = _upload_png(client, p["id"], "big.png", 1600, 1200)
    doc = _typed_doc(client, p["id"])
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={
            "kind": "image", "asset_id": big["id"], "aspect": "4:3",
            "caption": "Site photograph, looking north", "provenance": "Practice archive",
        },
    )
    codes = [c for c in _codes(client, p["id"], doc["id"]) if c.startswith("IMG")]
    assert codes == []


def test_untyped_documents_are_unaffected_by_asset_quality_checks(client):
    """M2.1's own invariant: an untyped document has no requirements at
    all -- IMG-* must not become a silent exception to that."""
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    small = _upload_png(client, p["id"], "small.png", 100, 100)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Untyped"}).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "image", "asset_id": small["id"], "aspect": "4:3"},
    )
    findings = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/requirements").json()["findings"]
    assert findings == []
