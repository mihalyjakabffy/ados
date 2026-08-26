"""
ADOS-M3.1 — brand/llm/context.py.

SemanticContext must only ever contain real, already-existing data — no
project, brand or design-state field is present unless the caller
actually supplied that real object.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from brand.llm.context import CONTEXT_VERSION, build_semantic_context  # noqa: E402

BRAND_ID = "5747d10b-0000-4000-8000-000000000001"


def _app():
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


def test_bare_request_has_no_fabricated_context():
    ctx = build_semantic_context("Create a portfolio.")
    assert ctx.project_context is None
    assert ctx.brand_context is None
    assert ctx.design_state_context is None
    assert ctx.context_version == CONTEXT_VERSION


def test_available_document_types_is_always_the_real_registry():
    from brand.project.document_types import DOCUMENT_TYPES

    ctx = build_semantic_context("anything")
    assert {dt.id for dt in ctx.available_document_types} == set(DOCUMENT_TYPES)


def test_available_capabilities_matches_the_real_vocabulary():
    from brand.llm.vocabulary import Action, Target

    ctx = build_semantic_context("anything")
    assert set(ctx.available_capabilities["actions"]) == {a.value for a in Action}
    assert set(ctx.available_capabilities["targets"]) == {t.value for t in Target}


def test_conversation_context_passes_through_unmodified():
    from brand.llm.context import ConversationTurn

    turns = (ConversationTurn(role="user", text="hello"), ConversationTurn(role="assistant", text="hi"))
    ctx = build_semantic_context("anything", conversation=turns)
    assert ctx.conversation_context == turns


def test_project_context_reflects_the_real_project(client, tmp_path):
    from brand.project.store import FileProjectRepository

    p = client.post("/api/v2/ados-projects", json={"name": "Riverside", "description": "d"}).json()
    client.patch(f"/api/v2/ados-projects/{p['id']}", json={"project_data": {"client": "Acme"}})
    client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc", "document_type_id": "portfolio"})

    project = FileProjectRepository(str(tmp_path / "ados-projects")).get(p["id"])
    ctx = build_semantic_context("anything", project=project)

    assert ctx.project_context is not None
    assert ctx.project_context["name"] == "Riverside"
    assert ctx.project_context["project_data"] == {"client": "Acme"}
    assert ctx.project_context["document_type_ids"] == ["portfolio"]
    assert ctx.brand_context is None
    assert ctx.design_state_context is None


def test_brand_and_design_state_context_reflect_real_objects(client, tmp_path):
    from brand.design_state.build import build_design_state
    from brand.project.store import FileProjectRepository

    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "D", "document_type_id": "case-study"},
    ).json()

    import api.routers.brand as brand_router

    project = FileProjectRepository(str(tmp_path / "ados-projects")).get(p["id"])
    document = project.document(doc["id"])
    brand = brand_router._seeded_repo().get(project.brand_id, project.brand_version)
    design_state = build_design_state(project, document, brand)

    ctx = build_semantic_context("anything", project=project, brand=brand, design_state=design_state)

    assert ctx.brand_context["name"] == "Studio Nord"
    assert ctx.design_state_context["output_type"] == "case-study"
    assert ctx.design_state_context["document_id"] == doc["id"]
