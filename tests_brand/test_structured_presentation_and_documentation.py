"""
ADOS-M2.2.1 P3/P4 -- structured Client Presentation and Internal
Documentation data (PresentationOption/Decision/ActionItem/Meeting/
Participant) and their Requirements-Engine checks (CLI-001/002/003,
INT-001/002).

Same client/fixture convention as test_project_api.py -- storage
redirected to a tmp dir, brand store isolated per test.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

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


def _codes(findings, prefix):
    return [f["code"] for f in findings if f["code"].startswith(prefix)]


def _client_presentation_doc(client) -> tuple[dict, dict]:
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Deck", "document_type_id": "client-presentation"},
    ).json()
    return p, doc


def _internal_doc(client) -> tuple[dict, dict]:
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Minutes", "document_type_id": "internal-documentation"},
    ).json()
    return p, doc


def _findings(client, project_id, document_id):
    return client.get(f"/api/v2/ados-projects/{project_id}/documents/{document_id}/requirements").json()["findings"]


# ---------------------------------------------------------------------------
# P3 -- PresentationOption / Decision / ActionItem
# ---------------------------------------------------------------------------


def test_add_and_remove_presentation_option(client):
    p, doc = _client_presentation_doc(client)
    added = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/options",
        json={"title": "Option A", "description": "Retain facade", "status": "proposed"},
    )
    assert added.status_code == 201
    options = added.json()["presentation_options"]
    assert len(options) == 1
    assert options[0]["status"] == "proposed"

    removed = client.delete(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/options/{options[0]['id']}")
    assert removed.status_code == 200
    assert removed.json()["presentation_options"] == []


def test_invalid_option_status_is_422(client):
    p, doc = _client_presentation_doc(client)
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/options",
        json={"title": "Option A", "status": "not-a-status"},
    )
    assert r.status_code == 422


def test_cli001_only_fires_once_options_exist_and_none_is_recommended(client):
    p, doc = _client_presentation_doc(client)
    assert "CLI-001" not in _codes(_findings(client, p["id"], doc["id"]), "CLI")

    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/options",
        json={"title": "Option A", "status": "proposed"},
    )
    assert "CLI-001" in _codes(_findings(client, p["id"], doc["id"]), "CLI-001")

    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/options",
        json={"title": "Option B", "status": "recommended"},
    )
    assert "CLI-001" not in _codes(_findings(client, p["id"], doc["id"]), "CLI-001")


def test_cli002_flags_a_decision_referencing_a_missing_option(client):
    p, doc = _client_presentation_doc(client)
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/decisions",
        json={"title": "Go with A", "selected_option_id": "does-not-exist"},
    )
    assert "CLI-002" in _codes(_findings(client, p["id"], doc["id"]), "CLI-002")


def test_cli002_passes_when_the_option_exists(client):
    p, doc = _client_presentation_doc(client)
    option = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/options",
        json={"title": "Option A", "status": "recommended"},
    ).json()["presentation_options"][0]
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/decisions",
        json={"title": "Go with A", "selected_option_id": option["id"], "date": "2026-08-25"},
    )
    findings = _findings(client, p["id"], doc["id"])
    assert "CLI-002" not in [f["code"] for f in findings]


def test_cli003_warns_on_an_undated_decision(client):
    p, doc = _client_presentation_doc(client)
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/decisions",
        json={"title": "Go with A"},
    )
    findings = _findings(client, p["id"], doc["id"])
    cli003 = [f for f in findings if f["code"] == "CLI-003"]
    assert len(cli003) == 1
    assert cli003[0]["severity"] == "WARN"


def test_action_item_crud(client):
    p, doc = _client_presentation_doc(client)
    added = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/action-items",
        json={"description": "Send fee proposal", "responsible": "Mihaly", "deadline": "2026-09-01"},
    )
    assert added.status_code == 201
    item = added.json()["action_items"][0]
    assert item["status"] == "open"

    removed = client.delete(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/action-items/{item['id']}")
    assert removed.status_code == 200
    assert removed.json()["action_items"] == []


def test_invalid_deadline_is_422(client):
    p, doc = _client_presentation_doc(client)
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/action-items",
        json={"description": "x", "deadline": "not-a-date"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# P4 -- Meeting / Participant, reusing Decision/ActionItem
# ---------------------------------------------------------------------------


def test_add_and_remove_meeting(client):
    p, doc = _internal_doc(client)
    added = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/meetings",
        json={
            "title": "Design review", "date": "2026-08-20", "location": "Studio",
            "participants": [{"name": "A. Architect", "role": "Lead"}],
            "agenda": ["Review facade options"],
            "decisions": [{"title": "Proceed with brick retention"}],
            "action_items": [{"description": "Circulate minutes", "responsible": "A. Architect"}],
        },
    )
    assert added.status_code == 201
    meetings = added.json()["meetings"]
    assert len(meetings) == 1
    assert meetings[0]["participants"][0]["name"] == "A. Architect"
    assert meetings[0]["decisions"][0]["title"] == "Proceed with brick retention"
    assert meetings[0]["action_items"][0]["responsible"] == "A. Architect"

    removed = client.delete(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/meetings/{meetings[0]['id']}")
    assert removed.status_code == 200
    assert removed.json()["meetings"] == []


def test_int001_requires_a_date_from_a_meeting_or_metadata(client):
    p, doc = _internal_doc(client)
    assert "INT-001" in _codes(_findings(client, p["id"], doc["id"]), "INT-001")

    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/meetings",
        json={"title": "Design review", "date": "2026-08-20"},
    )
    assert "INT-001" not in _codes(_findings(client, p["id"], doc["id"]), "INT-001")


def test_int001_satisfied_by_document_metadata_date_without_a_meeting(client):
    p, doc = _internal_doc(client)
    client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}",
        json={"metadata": {"date": "2026-08-20"}},
    )
    assert "INT-001" not in _codes(_findings(client, p["id"], doc["id"]), "INT-001")


def test_int002_flags_action_items_with_no_responsible_person(client):
    p, doc = _internal_doc(client)
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/meetings",
        json={
            "title": "Design review", "date": "2026-08-20",
            "action_items": [{"description": "Circulate minutes"}],
        },
    )
    assert "INT-002" in _codes(_findings(client, p["id"], doc["id"]), "INT-002")


def test_int002_passes_when_every_action_item_has_an_owner(client):
    p, doc = _internal_doc(client)
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/meetings",
        json={
            "title": "Design review", "date": "2026-08-20",
            "action_items": [{"description": "Circulate minutes", "responsible": "A. Architect"}],
        },
    )
    assert "INT-002" not in _codes(_findings(client, p["id"], doc["id"]), "INT-002")


def test_meeting_with_invalid_nested_deadline_is_422(client):
    p, doc = _internal_doc(client)
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/meetings",
        json={
            "title": "Design review",
            "action_items": [{"description": "x", "deadline": "not-a-date"}],
        },
    )
    assert r.status_code == 422
