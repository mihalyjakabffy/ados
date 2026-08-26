"""
ADOS-M3.5 — api/routers/command.py.

POST /{project_id}/commands/generate compiles a freshly-resolved
DesignIntent into a validated CommandPlan and nothing else — generation
never applies. POST .../commands/apply is the one endpoint that calls
the real apply_intent/compose. Mirrors test_design_intent_api.py's own
shape.
"""

from __future__ import annotations

import uuid

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

BRAND_ID = "5747d10b-0000-4000-8000-000000000001"


def _app():
    from fastapi import FastAPI

    from api.routers import ados_project as ados_project_router
    from api.routers import brand as brand_router
    from api.routers import command as command_router

    app = FastAPI()
    app.include_router(ados_project_router.router, prefix="/api/v2", tags=["ados-projects"])
    app.include_router(brand_router.router, prefix="/api/v2", tags=["brand"])
    app.include_router(command_router.router, prefix="/api/v2/ados-projects", tags=["command-generation"])
    return app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import api.routers.ados_project as ados_project_router
    import api.routers.brand as brand_router

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ados_project_router, "_PROJECT_STORAGE_ROOT", str(tmp_path / "ados-projects"))
    monkeypatch.setattr(brand_router, "_BRAND_ROOT", str(tmp_path / "brands"))

    from brand.llm.command.observability import clear_command_traces

    clear_command_traces()

    with TestClient(_app()) as c:
        yield c


def _content_model() -> dict:
    return {
        "project_id": str(uuid.uuid4()),
        "project_name": "Riverside",
        "blocks": [
            {"id": "txt-01", "type": "narrative", "role": "context", "priority": 1, "text": "hello world " * 20},
        ],
    }


def _create_project_with_brand(client) -> tuple[str, str]:
    project_id = client.post("/api/v2/ados-projects", json={"name": "Riverside"}).json()["id"]
    r0 = client.put(f"/api/v2/ados-projects/{project_id}/brand", json={"brand_id": BRAND_ID})
    assert r0.status_code == 200, r0.text
    doc = client.post(
        f"/api/v2/ados-projects/{project_id}/documents", json={"name": "D", "document_type_id": "portfolio"},
    ).json()
    return project_id, doc["id"]


def test_generate_returns_a_validated_command_plan_never_applies(client):
    project_id, document_id = _create_project_with_brand(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/commands/generate",
        json={
            "semantic_intent": {"explicit": {"audience": "prospective_client"}},
            "document_id": document_id, "document_type_id": "portfolio",
            "content_model": _content_model(),
            "raw_documents": [{"source_id": "brief", "text": "84 apartments. GFA of 13,100 m²."}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"command_plan", "command_validation", "design_intent", "design_validation", "request_id"}
    assert "pages" not in body["command_plan"]
    assert "plan" not in body["command_plan"]
    for command in body["command_plan"]["commands"]:
        assert command["intent"]["type"] in {
            "reduce_text_density", "increase_text_density", "increase_image_emphasis",
            "decrease_image_emphasis", "recompose_page", "preserve_content",
            "remove_content", "change_page_direction",
        }


def test_generate_with_invalid_content_model_422s(client):
    project_id = client.post("/api/v2/ados-projects", json={"name": "P"}).json()["id"]
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/commands/generate",
        json={"semantic_intent": {}, "content_model": {"project_id": "not-a-uuid", "project_name": "x", "blocks": []}},
    )
    assert r.status_code == 422


def test_unknown_project_id_404s(client):
    r = client.post(
        f"/api/v2/ados-projects/does-not-exist/commands/generate",
        json={"semantic_intent": {}, "content_model": _content_model()},
    )
    assert r.status_code == 404


def test_validate_endpoint_reruns_validation_independently(client):
    project_id, document_id = _create_project_with_brand(client)
    generated = client.post(
        f"/api/v2/ados-projects/{project_id}/commands/generate",
        json={
            "semantic_intent": {"explicit": {"audience": "prospective_client"}},
            "document_id": document_id, "document_type_id": "portfolio",
            "content_model": _content_model(),
        },
    ).json()

    r = client.post(
        f"/api/v2/ados-projects/{project_id}/commands/validate",
        json={"command_plan": generated["command_plan"], "content_model": _content_model()},
    )
    assert r.status_code == 200, r.text
    assert r.json()["validation"]["ok"] is True


def test_apply_endpoint_composes_via_the_existing_apply_intent_and_compose(client):
    project_id, document_id = _create_project_with_brand(client)
    content_model = _content_model()
    generated = client.post(
        f"/api/v2/ados-projects/{project_id}/commands/generate",
        json={
            "semantic_intent": {"explicit": {"audience": "prospective_client"}},
            "document_id": document_id, "document_type_id": "portfolio",
            "content_model": content_model,
        },
    ).json()
    plan = generated["command_plan"]
    if not plan["commands"]:
        pytest.skip("no commands were generated for this fixture — nothing to apply")

    r = client.post(
        f"/api/v2/ados-projects/{project_id}/commands/apply",
        json={"command_plan": plan, "content_model": content_model, "base_direction_id": "editorial-quiet"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["steps"]) == len(plan["commands"])
    assert body["final_plan"] is not None
    assert "pages" in body["final_plan"]


def test_apply_requires_exactly_one_base_direction_source(client):
    project_id, document_id = _create_project_with_brand(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/commands/apply",
        json={"command_plan": {"project_id": project_id, "commands": []}, "content_model": _content_model()},
    )
    assert r.status_code == 422


def test_schema_endpoint_returns_command_plan_and_command_intent_schemas(client):
    r = client.get("/api/v2/ados-projects/commands/schema")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "3.5"
    assert body["command_plan_schema"]["title"] == "CommandPlan"
    assert body["command_intent_schema"]["title"] == "CommandIntent"


def test_traces_endpoint_lists_recent_generations(client):
    project_id, document_id = _create_project_with_brand(client)
    for _ in range(2):
        client.post(
            f"/api/v2/ados-projects/{project_id}/commands/generate",
            json={"semantic_intent": {}, "document_id": document_id, "content_model": _content_model()},
        )
    r = client.get("/api/v2/ados-projects/commands/traces")
    assert r.status_code == 200
    assert len(r.json()["traces"]) == 2


def test_unknown_trace_id_404s(client):
    r = client.get("/api/v2/ados-projects/commands/traces/does-not-exist")
    assert r.status_code == 404
