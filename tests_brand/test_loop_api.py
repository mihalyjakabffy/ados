"""
ADOS-M3.6 — api/routers/closed_loop.py. End-to-end: create a real
project + brand + document, drive the loop through HTTP, exactly as the
dev page and a real client would.
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
    from api.routers import closed_loop as closed_loop_router

    app = FastAPI()
    app.include_router(ados_project_router.router, prefix="/api/v2", tags=["ados-projects"])
    app.include_router(brand_router.router, prefix="/api/v2", tags=["brand"])
    app.include_router(closed_loop_router.router, prefix="/api/v2/ados-projects", tags=["closed-loop"])
    return app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import api.routers.ados_project as ados_project_router
    import api.routers.brand as brand_router

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ados_project_router, "_PROJECT_STORAGE_ROOT", str(tmp_path / "ados-projects"))
    monkeypatch.setattr(brand_router, "_BRAND_ROOT", str(tmp_path / "brands"))

    from brand.llm.loop.observability import clear_lineages

    clear_lineages()

    with TestClient(_app()) as c:
        yield c


def _project_with_document(client) -> tuple[str, str]:
    project_id = client.post("/api/v2/ados-projects", json={"name": "Riverside"}).json()["id"]
    r0 = client.put(f"/api/v2/ados-projects/{project_id}/brand", json={"brand_id": BRAND_ID})
    assert r0.status_code == 200, r0.text
    doc = client.post(
        f"/api/v2/ados-projects/{project_id}/documents", json={"name": "Case Study", "document_type_id": "portfolio"},
    ).json()
    document_id = doc["id"]
    # The loop composes against this document's own real content_items
    # (brand.project.content_resolution.resolve_document_content), not
    # against the inline raw_documents text — those only feed the M3.2
    # narrative pipeline. Without at least one real content item there
    # is nothing for compose() to place.
    r_content = client.post(
        f"/api/v2/ados-projects/{project_id}/documents/{document_id}/content",
        json={"kind": "text", "text": "A residential development of 84 apartments on the riverside, "
                                       "with a strong connection to the landscape." * 3},
    )
    assert r_content.status_code == 201, r_content.text
    return project_id, document_id


def _start_body(**overrides):
    body = {
        "semantic_intent": {"explicit": {"audience": "prospective_client"}},
        "document_type_id": "portfolio",
        "raw_documents": [{"source_id": "brief", "text": "84 apartments. GFA of 13,100 m². Strong connection to the landscape."}],
    }
    body.update(overrides)
    return body


def test_start_runs_the_first_iteration_and_persists_a_version(client):
    project_id, document_id = _project_with_document(client)
    r = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/start", json=_start_body())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sequence"] == 1
    assert body["output_design_state_version"] == 1
    assert "pages" not in body  # never a raw PagePlan at the top level
    assert body["page_plan"]["pages"]


def test_double_start_conflicts(client):
    project_id, document_id = _project_with_document(client)
    client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/start", json=_start_body())
    r = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/start", json=_start_body())
    assert r.status_code == 409


def test_continue_without_a_lineage_404s(client):
    project_id, document_id = _project_with_document(client)
    r = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/continue", json={})
    assert r.status_code == 404


def test_run_full_loop_returns_a_lineage_with_a_final_status(client):
    project_id, document_id = _project_with_document(client)
    r = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/run", json=_start_body())
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["iterations"]) >= 1
    assert body["final_status"] in ("completed", "stopped", "blocked", "failed", "awaiting_approval")


def test_none_autonomy_awaits_approval_then_approve_completes(client):
    project_id, document_id = _project_with_document(client)
    body = _start_body(policy={"autonomy": "none", "max_iterations": 3})
    r = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/start", json=body)
    it1 = r.json()
    assert it1["status"] == "awaiting_approval"

    r2 = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/approve", json={})
    assert r2.status_code == 200, r2.text
    it1b = r2.json()
    assert it1b["status"] in ("completed", "blocked")
    assert it1b["output_design_state_version"] == 1


def test_approve_with_nothing_pending_409s(client):
    project_id, document_id = _project_with_document(client)
    r = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/approve", json={})
    assert r.status_code == 409


def test_history_and_trace_and_single_iteration_endpoints(client):
    project_id, document_id = _project_with_document(client)
    posted = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/start", json=_start_body()).json()

    r_hist = client.get(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop")
    assert r_hist.status_code == 200
    assert len(r_hist.json()["iterations"]) == 1

    r_one = client.get(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/{posted['id']}")
    assert r_one.status_code == 200
    assert r_one.json()["id"] == posted["id"]

    r_trace = client.get(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/{posted['id']}/trace")
    assert r_trace.status_code == 200
    assert "stage_log" in r_trace.json()


def test_unknown_iteration_id_404s(client):
    project_id, document_id = _project_with_document(client)
    r = client.get(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/does-not-exist")
    assert r.status_code == 404


def test_stop_marks_the_lineage_stopped(client):
    """If the started iteration already concluded with a stop_reason of
    its own (e.g. SUCCESS — no blocking findings remained), /stop is a
    harmless no-op on an already-terminal lineage: it must not relabel
    a successful iteration as "stopped". continue must still 409
    either way, since the lineage is not continuable."""
    project_id, document_id = _project_with_document(client)
    started = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/start", json=_start_body()).json()
    r = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/stop", json={})
    assert r.status_code == 200
    if started["stop_reason"] is None:
        assert r.json()["status"] == "stopped"
    else:
        assert r.json()["status"] == started["status"]

    r2 = client.post(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/continue", json={})
    assert r2.status_code == 409


def test_dry_run_start_does_not_persist(client):
    project_id, document_id = _project_with_document(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/start",
        json=_start_body(dry_run=True),
    )
    assert r.status_code == 200
    assert r.json()["dry_run"] is True

    r_hist = client.get(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop")
    assert r_hist.json()["iterations"] == []

    doc = client.get(f"/api/v2/ados-projects/{project_id}/documents/{document_id}").json()
    assert doc.get("latest_plan") is None


def test_unknown_project_404s(client):
    r = client.post(
        "/api/v2/ados-projects/does-not-exist/documents/does-not-exist/loop/start", json=_start_body(),
    )
    assert r.status_code == 404


def test_unknown_autonomy_value_422s(client):
    project_id, document_id = _project_with_document(client)
    r = client.post(
        f"/api/v2/ados-projects/{project_id}/documents/{document_id}/loop/start",
        json=_start_body(policy={"autonomy": "not-a-real-level"}),
    )
    assert r.status_code == 422


def test_schema_endpoint(client):
    r = client.get("/api/v2/ados-projects/loop/schema")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "3.6"
    assert body["iteration_schema"]["title"] == "Iteration"
