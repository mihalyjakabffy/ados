"""
api/routers/ados_project.py — the ADOS M2.2 Document Engine's HTTP surface:
document types, sections, requirements, project references, and typed
compose. See tests_brand/test_project_api.py for the plain M2.1 CRUD
surface this extends without changing its behaviour.
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


def _project_with_brand(client) -> dict:
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    return p


# ---------------------------------------------------------------------------
# Document types
# ---------------------------------------------------------------------------


def test_list_document_types_returns_all_nine(client):
    r = client.get("/api/v2/ados-projects/document-types")
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()["document_types"]}
    assert len(ids) == 9
    assert "project-report" in ids and "portfolio" in ids


def test_get_one_document_type_includes_its_requirements(client):
    r = client.get("/api/v2/ados-projects/document-types/competition-document")
    assert r.status_code == 200
    body = r.json()
    assert body["max_pages"] == 12
    codes = {req["id"] for req in body["requirements"]}
    assert "COMP-001" in codes


def test_unknown_document_type_is_404(client):
    r = client.get("/api/v2/ados-projects/document-types/not-a-type")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Creating a typed document auto-generates its structure
# ---------------------------------------------------------------------------


def test_creating_a_typed_document_generates_default_sections_and_direction(client):
    p = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Report", "document_type_id": "project-report"},
    ).json()
    assert doc["document_type_id"] == "project-report"
    assert len(doc["sections"]) == 16
    assert doc["direction_id"] == "technical-dense"  # project-report's composition_profile


def test_explicit_direction_overrides_the_types_default(client):
    p = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Report", "document_type_id": "project-report", "direction_id": "image-led"},
    ).json()
    assert doc["direction_id"] == "image-led"


def test_untyped_document_still_works_exactly_as_m21(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Free"}).json()
    assert doc["document_type_id"] == ""
    assert doc["sections"] == []
    assert doc["direction_id"] == "editorial-quiet"


def test_metadata_can_be_set_on_create_and_merged_on_update(client):
    p = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Report", "document_type_id": "project-report", "metadata": {"location": "Leeds"}},
    ).json()
    assert doc["metadata"] == {"location": "Leeds"}

    updated = client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}",
        json={"metadata": {"client": "City Council"}},
    ).json()
    # merged, not replaced -- the earlier "location" key must survive
    assert updated["metadata"] == {"location": "Leeds", "client": "City Council"}

    requirements = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/requirements").json()
    assert not any(f["code"] == "REP-005" for f in requirements["findings"])


def test_document_updated_at_moves_on_its_own_mutations(client):
    """A client polling only THIS document's updated_at (e.g. to re-check
    its requirement findings) must see it move on every one of its own
    mutations — content, sections, project-refs, compose — not just
    whenever some other document in the project last changed."""
    p = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "D", "document_type_id": "project-report"},
    ).json()
    t0 = doc["updated_at"]

    after_content = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "x"},
    ).json()
    assert after_content["updated_at"] != t0

    section = doc["sections"][0]
    after_section = client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections/{section['id']}",
        json={"name": "Renamed"},
    ).json()
    assert after_section["updated_at"] != after_content["updated_at"]


def test_creating_with_an_unknown_document_type_is_404(client):
    p = _project_with_brand(client)
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "X", "document_type_id": "not-a-type"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def test_add_update_delete_section(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "D"}).json()

    section = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections",
        json={"kind": "concept", "name": "Concept"},
    )
    assert section.status_code == 201
    section_id = section.json()["sections"][0]["id"]

    renamed = client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections/{section_id}",
        json={"name": "Design Concept", "order": 3},
    )
    assert renamed.status_code == 200
    assert renamed.json()["sections"][0]["name"] == "Design Concept"
    assert renamed.json()["sections"][0]["order"] == 3

    deleted = client.delete(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections/{section_id}")
    assert deleted.status_code == 200
    assert deleted.json()["sections"] == []


def test_assigning_an_unknown_content_item_id_to_a_section_is_422(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "D"}).json()
    section = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections",
        json={"kind": "concept", "name": "Concept"},
    ).json()["sections"][0]

    r = client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections/{section['id']}",
        json={"content_item_ids": ["does-not-exist"]},
    )
    assert r.status_code == 422


def test_deleting_a_section_does_not_delete_its_content(client):
    p = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "D", "document_type_id": "project-report"},
    ).json()
    section = doc["sections"][0]
    item = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "kept"},
    ).json()["content_items"][0]
    client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections/{section['id']}",
        json={"content_item_ids": [item["id"]]},
    )
    deleted = client.delete(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections/{section['id']}")
    assert len(deleted.json()["content_items"]) == 1


# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------


def test_requirements_endpoint_reflects_document_state(client):
    p = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Submission", "document_type_id": "planning-submission"},
    ).json()

    before = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/requirements").json()
    assert before["ok"] is False
    assert any(f["code"] == "PLN-014" for f in before["findings"])

    site_plan_section = next(s for s in doc["sections"] if s["kind"] == "site-plan")
    item = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "Site plan drawing reference."},
    ).json()["content_items"][0]
    client.patch(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/sections/{site_plan_section['id']}",
        json={"content_item_ids": [item["id"]]},
    )

    after = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/requirements").json()
    assert not any(f["code"] == "PLN-014" for f in after["findings"])


def test_compose_response_includes_requirement_findings(client):
    p = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Report", "document_type_id": "project-report"},
    ).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "Some content."},
    )
    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 200
    assert "requirement_findings" in r.json()


def test_competition_document_over_the_page_limit_is_flagged(client):
    """ADOS-M2.2 §29 Test B."""
    p = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Comp", "document_type_id": "competition-document"},
    ).json()
    for i in range(30):
        client.post(
            f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
            json={"kind": "text", "text": f"Paragraph {i} word " * 20},
        )
    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 200
    body = r.json()
    assert len(body["plan"]["pages"]) > 12
    codes = [f["code"] for f in body["requirement_findings"]]
    assert "COMP-001" in codes


# ---------------------------------------------------------------------------
# Portfolio / project references (ADOS-M2.2 §10, §29 Test D)
# ---------------------------------------------------------------------------


def test_portfolio_references_project_content_without_duplicating_it(client):
    p = _project_with_brand(client)
    other = _project_with_brand(client)
    other["name"] = other["name"]  # keep for readability
    other_doc = client.post(f"/api/v2/ados-projects/{other['id']}/documents", json={"name": "Notes"}).json()
    client.post(
        f"/api/v2/ados-projects/{other['id']}/documents/{other_doc['id']}/content",
        json={"kind": "text", "text": "Original pavilion description."},
    )

    portfolio = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Portfolio", "document_type_id": "portfolio"},
    ).json()

    before = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}/requirements").json()
    assert any(f["code"] == "PORT-003" for f in before["findings"])

    ref = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}/project-refs",
        json={"project_id": other["id"]},
    )
    assert ref.status_code == 201
    assert other["id"] in ref.json()["project_refs"]

    after = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}/requirements").json()
    assert not any(f["code"] == "PORT-003" for f in after["findings"])

    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}/content",
        json={"kind": "text", "text": "Selected works."},
    )
    composed = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}/compose").json()
    texts = [b.get("text", "") for b in composed["content_model"]["blocks"]]
    assert any("Original pavilion description" in t for t in texts)

    # the portfolio document itself never stored the referenced content
    portfolio_now = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}").json()
    assert all("Original pavilion" not in item.get("text", "") for item in portfolio_now["content_items"])


def test_portfolio_recomposes_with_updated_referenced_project_content(client):
    """ADOS-M2.2 §29 Test D: editing the referenced project changes the
    next composition, proving reference rather than copy."""
    p = _project_with_brand(client)
    other = _project_with_brand(client)
    other_doc = client.post(f"/api/v2/ados-projects/{other['id']}/documents", json={"name": "Notes"}).json()
    client.post(
        f"/api/v2/ados-projects/{other['id']}/documents/{other_doc['id']}/content",
        json={"kind": "text", "text": "Version one."},
    )

    portfolio = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Portfolio", "document_type_id": "portfolio"},
    ).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}/project-refs",
        json={"project_id": other["id"]},
    )
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}/content",
        json={"kind": "text", "text": "Cover."},
    )

    first = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}/compose").json()
    assert any("Version one" in b.get("text", "") for b in first["content_model"]["blocks"])

    client.post(
        f"/api/v2/ados-projects/{other['id']}/documents/{other_doc['id']}/content",
        json={"kind": "text", "text": "Version two."},
    )
    second = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{portfolio['id']}/compose").json()
    texts = [b.get("text", "") for b in second["content_model"]["blocks"]]
    assert any("Version two" in t for t in texts)


def test_cannot_reference_own_project(client):
    p = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Portfolio", "document_type_id": "portfolio"},
    ).json()
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/project-refs",
        json={"project_id": p["id"]},
    )
    assert r.status_code == 422


def test_remove_project_ref(client):
    p = _project_with_brand(client)
    other = _project_with_brand(client)
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Portfolio", "document_type_id": "portfolio"},
    ).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/project-refs",
        json={"project_id": other["id"]},
    )
    r = client.delete(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/project-refs/{other['id']}")
    assert r.status_code == 200
    assert other["id"] not in r.json()["project_refs"]
