"""
ADOS-M3.2 — api/routers/content_intelligence.py.

POST /{project_id}/content/resolve produces a validated
ContentIntelligenceModel and nothing else; GET .../content/schema and
GET .../content/traces are the developer-facing surfaces ADOS-M3.2
§25/§33 ask for. Mirrors test_semantic_intent_api.py's own shape.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


def _app():
    from fastapi import FastAPI

    from api.routers import ados_project as ados_project_router
    from api.routers import content_intelligence as content_intelligence_router

    app = FastAPI()
    app.include_router(ados_project_router.router, prefix="/api/v2", tags=["ados-projects"])
    app.include_router(content_intelligence_router.router, prefix="/api/v2/ados-projects", tags=["content-intelligence"])
    return app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import api.routers.ados_project as ados_project_router

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ados_project_router, "_PROJECT_STORAGE_ROOT", str(tmp_path / "ados-projects"))

    from brand.llm.content.observability import clear_content_traces

    clear_content_traces()

    with TestClient(_app()) as c:
        yield c


def test_resolve_returns_content_validation_and_request_id(client):
    p = client.post("/api/v2/ados-projects", json={"name": "Riverside"}).json()
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/content/resolve",
        json={"raw_documents": [{"source_id": "brief", "text": "84 apartments. GFA of 13,100 m²."}]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"content", "validation", "request_id"}
    facts = {f["key"]: f for f in body["content"]["facts"]}
    assert facts["apartments"]["value"] == 84
    assert body["validation"]["ok"] is True


def test_resolve_never_returns_a_plan_or_command_intent(client):
    p = client.post("/api/v2/ados-projects", json={"name": "Riverside"}).json()
    r = client.post(f"/api/v2/ados-projects/{p['id']}/content/resolve", json={})
    body = r.json()
    assert "plan" not in body
    assert "command_intent" not in body
    assert "pages" not in body["content"]


def test_unknown_project_id_404s(client):
    r = client.post("/api/v2/ados-projects/does-not-exist/content/resolve", json={})
    assert r.status_code == 404


def test_unknown_document_id_404s(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/content/resolve",
        json={"document_id": "does-not-exist"},
    )
    assert r.status_code == 404


def test_conflicting_sources_are_surfaced_not_silently_resolved(client):
    p = client.post("/api/v2/ados-projects", json={"name": "Riverside"}).json()
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/content/resolve",
        json={"raw_documents": [
            {"source_id": "brief.pdf", "text": "GFA of 12,400 m²."},
            {"source_id": "deck.pdf", "text": "GFA of 13,100 m²."},
        ]},
    )
    body = r.json()
    gfa = next(f for f in body["content"]["facts"] if f["key"] == "gross_floor_area")
    assert gfa["status"] == "conflicting"
    assert gfa["value"] is None


def test_user_correction_supersedes_without_overwriting(client):
    p = client.post(
        "/api/v2/ados-projects", json={"name": "Riverside"},
    ).json()
    client_r = client.patch(f"/api/v2/ados-projects/{p['id']}", json={"project_data": {"gross_floor_area": 12400}})
    assert client_r.status_code == 200, client_r.text
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/content/resolve",
        json={"user_corrections": [{"key": "gross_floor_area", "value": 13100}]},
    )
    body = r.json()
    gfa_facts = [f for f in body["content"]["facts"] if f["key"] == "gross_floor_area"]
    assert len(gfa_facts) == 2
    current = next(f for f in gfa_facts if f["superseded_by"] is None)
    assert current["value"] == 13100


def test_schema_endpoint_returns_a_real_json_schema(client):
    r = client.get("/api/v2/ados-projects/content/schema")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "3.2"
    assert body["schema"]["title"] == "ContentIntelligenceModel"


def test_traces_endpoint_lists_recent_resolutions(client):
    p = client.post("/api/v2/ados-projects", json={"name": "Riverside"}).json()
    client.post(f"/api/v2/ados-projects/{p['id']}/content/resolve", json={})
    client.post(f"/api/v2/ados-projects/{p['id']}/content/resolve", json={})

    r = client.get("/api/v2/ados-projects/content/traces")
    assert r.status_code == 200
    traces = r.json()["traces"]
    assert len(traces) == 2


def test_single_trace_lookup(client):
    p = client.post("/api/v2/ados-projects", json={"name": "Riverside"}).json()
    posted = client.post(f"/api/v2/ados-projects/{p['id']}/content/resolve", json={}).json()
    r = client.get(f"/api/v2/ados-projects/content/traces/{posted['request_id']}")
    assert r.status_code == 200
    assert r.json()["request_id"] == posted["request_id"]


def test_unknown_trace_id_404s(client):
    r = client.get("/api/v2/ados-projects/content/traces/does-not-exist")
    assert r.status_code == 404
