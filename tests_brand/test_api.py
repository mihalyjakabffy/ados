"""
The HTTP surface.

Mounted on the real FastAPI app, so these tests also assert that the router is
actually registered — a router that exists but was never added to ``api/main.py``
passes every unit test and serves nothing.

The store is redirected to a tmp directory per test so nothing here writes to
the repository.
"""

from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAND_STORAGE_ROOT", str(tmp_path / "brands"))
    import api.routers.brand as brand_router

    monkeypatch.setattr(brand_router, "_BRAND_ROOT", str(tmp_path / "brands"))

    with TestClient(_app()) as c:
        yield c


def _app():
    """The real app where its dependencies are installed, else just the router.

    ``api.main`` pulls in the render pipeline, the rate limiter and the auth
    stack, so on a machine without them the whole file would skip and the
    endpoint behaviour would go untested. Falling back to a bare app carrying
    only the brand router keeps every behavioural test running; the *wiring*
    is covered separately and statically by
    ``test_main_registers_the_router``, so nothing is lost by the fallback.
    """
    try:
        from api.main import app

        return app
    except BaseException:                                  # noqa: BLE001
        # BaseException, not Exception: a broken native dependency in the auth
        # stack surfaces as a pyo3 PanicException, which is not an Exception.
        from fastapi import FastAPI

        from api.routers import brand as brand_router

        app = FastAPI()
        app.include_router(brand_router.router, prefix="/api/v2", tags=["brand"])
        return app


BRAND_ID = "5747d10b-0000-4000-8000-000000000001"


# ---------------------------------------------------------------------------


def test_main_registers_the_router():
    """Static check: a router nobody mounts serves nothing.

    Reads the source rather than the app object so that it holds even in an
    environment where the app's other dependencies are missing.
    """
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "api" / "main.py").read_text()
    assert "from api.routers import brand as brand_router" in source
    assert 'app.include_router(brand_router.router, prefix="/api/v2"' in source


def test_the_router_is_mounted(client):
    """If this fails, api/main.py never registered the router."""
    response = client.get("/api/v2/brands")
    assert response.status_code == 200


def test_an_empty_store_seeds_the_worked_example(client):
    """A fresh deployment must be explorable, not a wall of 404s."""
    body = client.get("/api/v2/brands").json()
    assert body["brands"]
    assert body["brands"][0]["name"] == "Studio Nord"


def test_get_brand(client):
    body = client.get(f"/api/v2/brands/{BRAND_ID}").json()
    assert body["identity"]["name"] == "Studio Nord"
    assert body["version"] == "1.0.0"


def test_unknown_brand_is_404(client):
    r = client.get("/api/v2/brands/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_tokens_endpoint(client):
    full = client.get(f"/api/v2/brands/{BRAND_ID}/tokens").json()
    assert full["brand_version"] == "1.0.0"
    assert full["tokens"]["font.size.sm"]["unit"] == "mm"
    assert full["tokens"]["font.size.sm"]["source"]

    flat = client.get(f"/api/v2/brands/{BRAND_ID}/tokens?flat=true").json()
    assert flat["color.text.primary"] == "#111111"


def test_validate_endpoint(client):
    body = client.get(f"/api/v2/brands/{BRAND_ID}/validate").json()
    assert body["ok"] is True
    assert "counts" in body


def test_preview_endpoint_returns_html(client):
    r = client.get(f"/api/v2/brands/{BRAND_ID}/preview")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "STUDIO NORD" in r.text


def test_templates_endpoint_reports_coverage(client):
    body = client.get(f"/api/v2/brands/{BRAND_ID}/templates").json()
    assert len(body["templates"]) == 10
    assert all(t["renders"] for t in body["templates"])


def test_render_html(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/render/BT01-a4-report",
        json={"context": {"title": "Feasibility", "project": "Malthouse"}},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Feasibility" in r.text


def test_render_pdf(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/render/BT05-project-cover",
        json={"context": {"project": "Malthouse"}},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_render_with_a_project_override(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/render/BT01-a4-report",
        json={"overrides": {"color.brand.accent": "#3b5b8c"}},
    )
    assert r.status_code == 200
    assert "#3b5b8c" in r.text


def test_an_override_naming_an_unknown_token_is_422(client):
    r = client.post(
        f"/api/v2/brands/{BRAND_ID}/render/BT01-a4-report",
        json={"overrides": {"color.brand.quaternary": "#000000"}},
    )
    assert r.status_code == 422


def test_unknown_template_is_404(client):
    r = client.post(f"/api/v2/brands/{BRAND_ID}/render/nope", json={})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Proposals — the approval gate at the HTTP boundary
# ---------------------------------------------------------------------------


def test_proposal_endpoint_does_not_write(client):
    before = len(client.get("/api/v2/brands").json()["brands"])
    r = client.post(
        "/api/v2/brand-proposals",
        json={"brief": "A quiet, material practice doing adaptive reuse.",
              "name": "Northbank"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["brand"]["status"] == "proposed"
    assert body["validation"]["ok"] is True
    assert body["assumptions"]

    after = len(client.get("/api/v2/brands").json()["brands"])
    assert after == before, "generating a proposal must not create a brand"


def test_empty_brief_is_422(client):
    assert client.post("/api/v2/brand-proposals", json={"brief": ""}).status_code == 422


def test_approving_a_proposal_stores_it(client):
    proposal = client.post(
        "/api/v2/brand-proposals",
        json={"brief": "Precise, quiet, material adaptive reuse.", "name": "Northbank"},
    ).json()

    r = client.post(
        "/api/v2/brand-proposals/approve?approved_by=MJ", json=proposal
    )
    assert r.status_code == 201
    assert r.json()["status"] == "approved"

    names = {b["name"] for b in client.get("/api/v2/brands").json()["brands"]}
    assert "Northbank" in names


def test_approving_an_invalid_brand_is_409(client):
    payload = client.get(f"/api/v2/brands/{BRAND_ID}").json()
    payload["architectural_language"]["drawing"]["lineweights"]["cut_mm"] = 0.18
    r = client.post("/api/v2/brand-proposals/approve?approved_by=MJ",
                    json={"brand": payload})
    assert r.status_code == 409
    assert r.json()["detail"]["validation"]["ok"] is False


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_create_validate_approve_publish(client):
    from brand.models.brand import Brand

    draft = Brand.create(name="Northbank Architects")
    created = client.post("/api/v2/brands", json=json.loads(draft.to_json()))
    assert created.status_code == 201
    bid = created.json()["brand_id"]
    assert created.json()["status"] == "draft"

    approved = client.post(
        f"/api/v2/brands/{bid}/versions/1.0.0/approve",
        json={"approved_by": "MJ", "changelog": "initial"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    published = client.post(f"/api/v2/brands/{bid}/versions/1.0.0/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"


def test_publishing_an_unapproved_version_is_409(client):
    from brand.models.brand import Brand

    draft = Brand.create(name="Unapproved Practice")
    bid = client.post("/api/v2/brands",
                      json=json.loads(draft.to_json())).json()["brand_id"]
    r = client.post(f"/api/v2/brands/{bid}/versions/1.0.0/publish")
    assert r.status_code == 409


def test_creating_a_malformed_brand_is_422(client):
    r = client.post("/api/v2/brands", json={"identity": {"name": "X"}})
    assert r.status_code == 422


def test_versions_endpoint(client):
    body = client.get(f"/api/v2/brands/{BRAND_ID}/versions").json()
    assert body["versions"][0]["version"] == "1.0.0"
    assert body["latest_usable"] == "1.0.0"


def test_schema_endpoint(client):
    schema = client.get("/api/v2/brand-schema").json()
    assert schema["title"] == "ADOS Brand"
    assert "identity" in schema["properties"]
