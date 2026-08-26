"""
ADOS-M3.4 — api/routers/design_intent.py.

POST /{project_id}/design/intent produces a validated DesignIntent and
nothing else; GET .../design/schema and GET .../design/traces are the
developer-facing surfaces ADOS-M3.4 §46/§61 ask for. Mirrors
test_narrative_api.py's own shape.
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
    from api.routers import design_intent as design_intent_router

    app = FastAPI()
    app.include_router(ados_project_router.router, prefix="/api/v2", tags=["ados-projects"])
    app.include_router(brand_router.router, prefix="/api/v2", tags=["brand"])
    app.include_router(design_intent_router.router, prefix="/api/v2/ados-projects", tags=["design-intent"])
    return app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import api.routers.ados_project as ados_project_router
    import api.routers.brand as brand_router

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ados_project_router, "_PROJECT_STORAGE_ROOT", str(tmp_path / "ados-projects"))
    monkeypatch.setattr(brand_router, "_BRAND_ROOT", str(tmp_path / "brands"))

    from brand.llm.design.observability import clear_design_traces

    clear_design_traces()

    with TestClient(_app()) as c:
        yield c


def _create_project(client) -> str:
    return client.post("/api/v2/ados-projects", json={"name": "Riverside"}).json()["id"]


def test_plan_returns_design_intent_narrative_content_and_validation(client):
    project_id = _create_project(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/design/intent",
        json={
            "semantic_intent": {"explicit": {"audience": "prospective_client", "purpose": "introduce_project"}},
            "document_type_id": "portfolio",
            "raw_documents": [{"source_id": "brief", "text": "84 apartments. GFA of 13,100 m²."}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"design_intent", "narrative_plan", "content", "validation", "request_id"}
    assert len(body["design_intent"]["section_designs"]) > 0
    assert body["validation"]["ok"] is True
    assert body["design_intent"]["brand_id"] is None  # no brand attached to this project


def test_plan_with_a_real_brand_reads_its_personality_and_direction(client):
    project_id = _create_project(client)
    r0 = client.put(f"/api/v2/ados-projects/{project_id}/brand", json={"brand_id": BRAND_ID})
    assert r0.status_code == 200, r0.text
    doc = client.post(
        f"/api/v2/ados-projects/{project_id}/documents", json={"name": "D", "document_type_id": "portfolio"},
    ).json()

    r = client.post(
        f"/api/v2/ados-projects/{project_id}/design/intent",
        json={
            "semantic_intent": {"explicit": {"audience": "prospective_client"}},
            "document_id": doc["id"], "document_type_id": "portfolio",
            "raw_documents": [{"source_id": "brief", "text": "84 apartments. GFA of 13,100 m²."}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["design_intent"]["brand_id"] == BRAND_ID
    assert len(body["design_intent"]["visual_language"]) > 0


def test_plan_never_returns_a_page_plan_or_command_intent(client):
    project_id = _create_project(client)
    r = client.post(f"/api/v2/ados-projects/{project_id}/design/intent", json={"semantic_intent": {}})
    body = r.json()
    assert "plan" not in body
    assert "command_intent" not in body
    assert "pages" not in body["design_intent"]


def test_unknown_project_id_404s(client):
    r = client.post("/api/v2/ados-projects/does-not-exist/design/intent", json={"semantic_intent": {}})
    assert r.status_code == 404


def test_unknown_document_id_404s(client):
    project_id = _create_project(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/design/intent",
        json={"semantic_intent": {}, "document_id": "does-not-exist"},
    )
    assert r.status_code == 404


def test_malformed_semantic_intent_422s(client):
    project_id = _create_project(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/design/intent",
        json={"semantic_intent": {"ambiguous": ["not-a-real-field"]}},
    )
    assert r.status_code == 422


def test_unknown_compression_422s(client):
    project_id = _create_project(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/design/intent",
        json={"semantic_intent": {}, "compression": "very-long"},
    )
    assert r.status_code == 422


def test_schema_endpoint_returns_a_real_json_schema(client):
    r = client.get("/api/v2/ados-projects/design/schema")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "3.4"
    assert body["schema"]["title"] == "DesignIntent"


def test_traces_endpoint_lists_recent_designs(client):
    project_id = _create_project(client)
    client.post(f"/api/v2/ados-projects/{project_id}/design/intent", json={"semantic_intent": {}})
    client.post(f"/api/v2/ados-projects/{project_id}/design/intent", json={"semantic_intent": {}})

    r = client.get("/api/v2/ados-projects/design/traces")
    assert r.status_code == 200
    assert len(r.json()["traces"]) == 2


def test_single_trace_lookup(client):
    project_id = _create_project(client)
    posted = client.post(f"/api/v2/ados-projects/{project_id}/design/intent", json={"semantic_intent": {}}).json()
    r = client.get(f"/api/v2/ados-projects/design/traces/{posted['request_id']}")
    assert r.status_code == 200
    assert r.json()["request_id"] == posted["request_id"]


def test_unknown_trace_id_404s(client):
    r = client.get("/api/v2/ados-projects/design/traces/does-not-exist")
    assert r.status_code == 404
