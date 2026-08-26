"""
ADOS-M3.3 — api/routers/narrative.py.

POST /{project_id}/narrative/plan produces a validated NarrativePlan and
nothing else; GET .../narrative/schema and GET .../narrative/traces are
the developer-facing surfaces ADOS-M3.3 §38/§40 ask for. Mirrors
test_content_intelligence_api.py's own shape.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


def _app():
    from fastapi import FastAPI

    from api.routers import ados_project as ados_project_router
    from api.routers import narrative as narrative_router

    app = FastAPI()
    app.include_router(ados_project_router.router, prefix="/api/v2", tags=["ados-projects"])
    app.include_router(narrative_router.router, prefix="/api/v2/ados-projects", tags=["narrative"])
    return app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import api.routers.ados_project as ados_project_router

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ados_project_router, "_PROJECT_STORAGE_ROOT", str(tmp_path / "ados-projects"))

    from brand.llm.narrative.observability import clear_narrative_traces

    clear_narrative_traces()

    with TestClient(_app()) as c:
        yield c


def _create_project(client) -> str:
    return client.post("/api/v2/ados-projects", json={"name": "Riverside"}).json()["id"]


def test_plan_returns_narrative_content_and_validation(client):
    project_id = _create_project(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/narrative/plan",
        json={
            "semantic_intent": {"explicit": {"audience": "prospective_client", "purpose": "introduce_project"}},
            "document_type_id": "portfolio",
            "raw_documents": [{"source_id": "brief", "text": "84 apartments. GFA of 13,100 m²."}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"narrative_plan", "content", "validation", "request_id"}
    assert body["narrative_plan"]["audience"] == "client"
    assert body["narrative_plan"]["audience_label"] == "prospective_client"
    assert len(body["narrative_plan"]["sections"]) > 0
    assert body["validation"]["ok"] is True


def test_plan_never_returns_a_page_plan_or_command_intent(client):
    project_id = _create_project(client)
    r = client.post(f"/api/v2/ados-projects/{project_id}/narrative/plan", json={"semantic_intent": {}})
    body = r.json()
    assert "plan" not in body  # no PagePlan-shaped top-level key
    assert "command_intent" not in body
    assert "pages" not in body["narrative_plan"]


def test_unknown_project_id_404s(client):
    r = client.post("/api/v2/ados-projects/does-not-exist/narrative/plan", json={"semantic_intent": {}})
    assert r.status_code == 404


def test_unknown_document_id_404s(client):
    project_id = _create_project(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/narrative/plan",
        json={"semantic_intent": {}, "document_id": "does-not-exist"},
    )
    assert r.status_code == 404


def test_malformed_semantic_intent_422s(client):
    project_id = _create_project(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/narrative/plan",
        # "ambiguous" may only name a real SemanticField -- SemanticIntent's
        # own model_validator rejects this, unlike a free-text field value.
        json={"semantic_intent": {"ambiguous": ["not-a-real-field"]}},
    )
    assert r.status_code == 422


def test_unknown_compression_422s(client):
    project_id = _create_project(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/narrative/plan",
        json={"semantic_intent": {}, "compression": "very-long"},
    )
    assert r.status_code == 422


def test_conflicting_sources_are_surfaced_not_silently_resolved(client):
    project_id = _create_project(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/narrative/plan",
        json={
            "semantic_intent": {},
            "raw_documents": [
                {"source_id": "a.pdf", "text": "GFA of 12,400 m²."},
                {"source_id": "b.pdf", "text": "GFA of 13,100 m²."},
            ],
        },
    )
    body = r.json()
    gfa = next(f for f in body["content"]["facts"] if f["key"] == "gross_floor_area")
    assert gfa["status"] == "conflicting"
    assert any(i["type"] == "conflicting_information" for i in body["narrative_plan"]["narrative_issues"])


def test_schema_endpoint_returns_a_real_json_schema(client):
    r = client.get("/api/v2/ados-projects/narrative/schema")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "3.3"
    assert body["schema"]["title"] == "NarrativePlan"


def test_traces_endpoint_lists_recent_plans(client):
    project_id = _create_project(client)
    client.post(f"/api/v2/ados-projects/{project_id}/narrative/plan", json={"semantic_intent": {}})
    client.post(f"/api/v2/ados-projects/{project_id}/narrative/plan", json={"semantic_intent": {}})

    r = client.get("/api/v2/ados-projects/narrative/traces")
    assert r.status_code == 200
    assert len(r.json()["traces"]) == 2


def test_single_trace_lookup(client):
    project_id = _create_project(client)
    posted = client.post(f"/api/v2/ados-projects/{project_id}/narrative/plan", json={"semantic_intent": {}}).json()
    r = client.get(f"/api/v2/ados-projects/narrative/traces/{posted['request_id']}")
    assert r.status_code == 200
    assert r.json()["request_id"] == posted["request_id"]


def test_unknown_trace_id_404s(client):
    r = client.get("/api/v2/ados-projects/narrative/traces/does-not-exist")
    assert r.status_code == 404
