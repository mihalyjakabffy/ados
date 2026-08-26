"""
ADOS-M3.1 — api/routers/semantic_intent.py.

POST /intent/semantic never executes anything and never leaks a
provider-specific object; GET .../schema and GET .../traces are the
developer-facing surfaces ADOS-M3.1 §12/§20 ask for.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

BRAND_ID = "5747d10b-0000-4000-8000-000000000001"


def _app():
    from fastapi import FastAPI

    from api.routers import ados_project as ados_project_router
    from api.routers import brand as brand_router
    from api.routers import semantic_intent as semantic_intent_router

    app = FastAPI()
    app.include_router(ados_project_router.router, prefix="/api/v2", tags=["ados-projects"])
    app.include_router(brand_router.router, prefix="/api/v2", tags=["brand"])
    app.include_router(semantic_intent_router.router, prefix="/api/v2", tags=["semantic-intent"])
    return app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import api.routers.ados_project as ados_project_router
    import api.routers.brand as brand_router

    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ados_project_router, "_PROJECT_STORAGE_ROOT", str(tmp_path / "ados-projects"))
    monkeypatch.setattr(brand_router, "_BRAND_ROOT", str(tmp_path / "brands"))

    from brand.llm.observability import clear_traces

    clear_traces()

    with TestClient(_app()) as c:
        yield c


def test_bare_request_returns_intent_and_validation(client):
    r = client.post("/api/v2/intent/semantic", json={"request": "Create a new case study."})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"intent", "validation", "request_id", "provider", "model"}
    assert body["intent"]["explicit"]["action"] == "create"
    assert body["intent"]["explicit"]["document_type"] == "case-study"
    assert body["validation"]["ok"] is True
    assert body["provider"] == "rule-based"


def test_request_is_required(client):
    r = client.post("/api/v2/intent/semantic", json={})
    assert r.status_code == 422


def test_blank_request_is_rejected(client):
    r = client.post("/api/v2/intent/semantic", json={"request": ""})
    assert r.status_code == 422


def test_unknown_project_id_404s(client):
    r = client.post("/api/v2/intent/semantic", json={"request": "anything", "project_id": "does-not-exist"})
    assert r.status_code == 404


def test_unknown_document_id_404s(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    r = client.post(
        "/api/v2/intent/semantic",
        json={"request": "anything", "project_id": p["id"], "document_id": "does-not-exist"},
    )
    assert r.status_code == 404


def test_real_project_context_changes_the_resolved_intent(client):
    """ADOS-M3.1 §17 context sensitivity, at the API boundary this time."""
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "D", "document_type_id": "design-report"},
    ).json()

    text = "Turn this into something I can send to the client."
    without_context = client.post("/api/v2/intent/semantic", json={"request": text}).json()
    with_context = client.post(
        "/api/v2/intent/semantic",
        json={"request": text, "project_id": p["id"], "document_id": doc["id"]},
    ).json()

    assert "target" in without_context["intent"]["ambiguous"]
    assert with_context["intent"]["inferred"]["target"] == "document"


def test_no_command_intent_or_pageplan_is_ever_returned(client):
    """The response shape itself proves nothing was executed — there is
    no plan, no document mutation, nothing but intent + validation."""
    r = client.post("/api/v2/intent/semantic", json={"request": "Create a case study."})
    body = r.json()
    assert "plan" not in body
    assert "document" not in body
    assert "command_intent" not in body


def test_schema_endpoint_returns_a_real_json_schema(client):
    r = client.get("/api/v2/intent/semantic/schema")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "3.1"
    assert body["schema"]["title"] == "SemanticIntent"
    assert "explicit" in body["schema"]["properties"]


def test_traces_endpoint_lists_recent_extractions(client):
    client.post("/api/v2/intent/semantic", json={"request": "Create a case study."})
    client.post("/api/v2/intent/semantic", json={"request": "Review the current draft."})

    r = client.get("/api/v2/intent/semantic/traces")
    assert r.status_code == 200
    traces = r.json()["traces"]
    assert len(traces) == 2
    assert traces[0]["request_preview"] == "Review the current draft."  # newest first


def test_single_trace_lookup(client):
    posted = client.post("/api/v2/intent/semantic", json={"request": "Create a case study."}).json()
    r = client.get(f"/api/v2/intent/semantic/traces/{posted['request_id']}")
    assert r.status_code == 200
    assert r.json()["request_id"] == posted["request_id"]


def test_unknown_trace_id_404s(client):
    r = client.get("/api/v2/intent/semantic/traces/does-not-exist")
    assert r.status_code == 404
