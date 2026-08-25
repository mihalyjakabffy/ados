"""
ADOS-M2.2.1 §29 -- explicit version-integrity tests.

A ProjectVersion is meant to be a true, frozen snapshot: content, sections,
document_type_id and plan as they stood the moment it was saved. Creating
a later version -- or continuing to edit the live document afterward --
must never reach back and change an earlier version's own stored fields.
test_export.py already proves this at the PDF-byte level (the end
product); this file proves the same invariant at the data level the
export pipeline is built on.
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


def _version(client, project_id, number):
    versions = client.get(f"/api/v2/ados-projects/{project_id}/versions").json()["versions"]
    return next(v for v in versions if v["number"] == number)


def test_version_1_content_and_plan_unchanged_after_version_2_is_saved(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "Version one content, the original brief."},
    )
    plan_1 = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose").json()["plan"]
    client.post(f"/api/v2/ados-projects/{p['id']}/versions", json={"document_id": doc["id"], "plan": plan_1})

    v1_before = _version(client, p["id"], 1)
    assert len(v1_before["content_items"]) == 1
    assert v1_before["content_items"][0]["text"] == "Version one content, the original brief."
    assert v1_before["plan"]["plan_hash"] == plan_1["plan_hash"]

    # Now change the live document substantially and save a second version.
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "A second, unrelated paragraph describing a different chapter entirely."},
    )
    plan_2 = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose").json()["plan"]
    client.post(f"/api/v2/ados-projects/{p['id']}/versions", json={"document_id": doc["id"], "plan": plan_2})

    v1_after = _version(client, p["id"], 1)
    v2 = _version(client, p["id"], 2)

    # Version 1 is byte-identical to what it was before Version 2 existed.
    assert v1_after == v1_before
    assert len(v1_after["content_items"]) == 1
    assert v1_after["plan"]["plan_hash"] == plan_1["plan_hash"]

    # Version 2 genuinely reflects the new state.
    assert len(v2["content_items"]) == 2
    assert v2["plan"]["plan_hash"] == plan_2["plan_hash"]
    assert v2["plan"]["plan_hash"] != v1_after["plan"]["plan_hash"]


def test_version_1_document_type_and_sections_unchanged_after_version_2(client):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Doc", "document_type_id": "case-study"},
    ).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "Original narrative."},
    )
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    client.post(f"/api/v2/ados-projects/{p['id']}/versions", json={"document_id": doc["id"]})

    v1_sections = _version(client, p["id"], 1)["sections"]
    v1_type = _version(client, p["id"], 1)["document_type_id"]
    assert v1_type == "case-study"
    assert len(v1_sections) > 0

    # Add a new section to the live document and save a second version.
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections",
        json={"kind": "custom-section", "name": "Custom Section"},
    )
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    client.post(f"/api/v2/ados-projects/{p['id']}/versions", json={"document_id": doc["id"]})

    v1_after = _version(client, p["id"], 1)
    v2_after = _version(client, p["id"], 2)
    assert v1_after["sections"] == v1_sections
    assert v1_after["document_type_id"] == "case-study"
    assert len(v2_after["sections"]) == len(v1_sections) + 1


def test_each_export_references_its_own_versions_content(client):
    """The export pipeline's version_number is not a label -- it must
    genuinely name the version whose plan was actually rendered."""
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "First state."},
    )
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    export_1 = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={},
    ).json()["export"]

    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "Second, much longer state describing something else entirely."},
    )
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    export_2 = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={},
    ).json()["export"]

    assert export_1["version_number"] == 1
    assert export_2["version_number"] == 2

    v1 = _version(client, p["id"], 1)
    v2 = _version(client, p["id"], 2)
    # plan.page_count isn't a stored dict key -- cross-check via pages length.
    assert export_1["page_count"] == len(v1["plan"]["pages"])
    assert export_2["page_count"] == len(v2["plan"]["pages"])
