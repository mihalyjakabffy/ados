"""
ADOS-M2.5 -- brand/design_state/model.py + build.py.

DesignState is a read model over the real, existing domain objects
(Project/Document/Brand/PagePlan/CreativeDirection/Requirements) -- these
tests build one from a real, composed project through the real API and
check every sub-state, plus round-trip serialization and determinism.
"""

from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from brand.design_state.build import build_design_state  # noqa: E402
from brand.design_state.model import DesignState  # noqa: E402

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


def _load(tmp_root: str, project_id: str):
    from brand.project.store import FileProjectRepository

    return FileProjectRepository(tmp_root).get(project_id)


def _seeded_brand(project):
    from api.routers import brand as brand_router

    return brand_router._seeded_repo().get(project.brand_id, project.brand_version)


def _composed_project_and_doc(client, tmp_root, *, document_type_id="design-report"):
    p = client.post("/api/v2/ados-projects", json={"name": "P", "description": "d"}).json()
    client.patch(f"/api/v2/ados-projects/{p['id']}", json={"project_data": {"client": "Acme"}})
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    shared = client.post(
        f"/api/v2/ados-projects/{p['id']}/content", json={"kind": "text", "text": "Shared fact."},
    ).json()["content_items"][0]
    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Doc", "document_type_id": document_type_id},
    ).json()
    client.put(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content-selection",
        json={"content_item_ids": [shared["id"]]},
    )
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "Own narrative."},
    )
    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 200, r.text

    project = _load(tmp_root, p["id"])
    document = project.document(doc["id"])
    return project, document, shared


# ---------------------------------------------------------------------------
# Model-level: serialization
# ---------------------------------------------------------------------------


def test_design_state_round_trips_through_json(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    brand = _seeded_brand(project)
    ds = build_design_state(project, document, brand)

    payload = json.loads(json.dumps(ds.to_dict()))
    rebuilt = DesignState.model_validate(payload)
    assert rebuilt == ds
    assert payload["schema_version"] == "2.5"


def test_design_state_is_deterministic(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    brand = _seeded_brand(project)
    a = build_design_state(project, document, brand).to_dict()
    b = build_design_state(project, document, brand).to_dict()
    assert a == b


# ---------------------------------------------------------------------------
# Sub-states
# ---------------------------------------------------------------------------


def test_project_state_carries_project_data_independent_of_document(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    ds = build_design_state(project, document, _seeded_brand(project))
    assert ds.project.project_data == {"client": "Acme"}
    assert ds.project.id == project.id
    assert document.id in ds.project.document_ids


def test_content_state_distinguishes_own_from_shared(client, tmp_path):
    project, document, shared = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    ds = build_design_state(project, document, _seeded_brand(project))
    assert len(ds.content.own) == 1
    assert ds.content.own[0].shared is False
    assert len(ds.content.shared_pool) == 1
    assert ds.content.shared_pool[0].shared is True
    assert ds.content.selected_shared_ids == (shared["id"],)


def test_document_state_resolves_audience_and_purpose_from_the_type(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    ds = build_design_state(project, document, _seeded_brand(project))
    assert ds.document.output_type == "design-report"
    assert ds.document.audience is not None
    assert ds.document.purpose is not None


def test_document_state_untyped_has_no_audience_or_purpose(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"), document_type_id="")
    ds = build_design_state(project, document, _seeded_brand(project))
    assert ds.document.output_type == ""
    assert ds.document.audience is None
    assert ds.document.purpose is None


def test_visual_language_reflects_the_real_direction(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    ds = build_design_state(project, document, _seeded_brand(project))
    assert ds.visual_language.direction_id == document.direction_id
    assert 0 < ds.visual_language.text_density < 1


def test_pages_and_components_derived_from_the_composed_plan(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    ds = build_design_state(project, document, _seeded_brand(project))
    assert len(ds.pages) > 0
    assert len(ds.components) > 0
    # every component belongs to a real page
    page_indices = {p.index for p in ds.pages}
    assert all(c.page_index in page_indices for c in ds.components)
    # a real page's own component_ids match the components pointing at it
    for page in ds.pages:
        expected = {c.id for c in ds.components if c.page_index == page.index}
        assert set(page.component_ids) == expected


def test_layout_derived_from_the_plans_own_grid(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    ds = build_design_state(project, document, _seeded_brand(project))
    assert ds.layout is not None
    assert ds.layout.page_width_mm == 210.0
    assert ds.layout.page_height_mm == 297.0


def test_uncomposed_document_has_no_pages_layout_or_components(client, tmp_path):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "D"}).json()
    project = _load(str(tmp_path / "ados-projects"), p["id"])
    document = project.document(doc["id"])
    ds = build_design_state(project, document, None)
    assert ds.pages == ()
    assert ds.components == ()
    assert ds.layout is None
    assert ds.brand.id is None


def test_constraints_reflect_a_real_unsatisfied_requirement(client, tmp_path):
    """The design-drivers content was added without a section, so DES-001
    (required_section_present) is genuinely unsatisfied."""
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    ds = build_design_state(project, document, _seeded_brand(project))
    rule = next(r for r in ds.constraints.rules if r.id == "DES-001")
    assert rule.level.value == "must"
    assert rule.satisfied is False


def test_constraints_become_satisfied_once_the_requirement_is_met(client, tmp_path):
    tmp_root = str(tmp_path / "ados-projects")
    project, document, _ = _composed_project_and_doc(client, tmp_root)
    section_id = next(s.id for s in document.sections if s.kind == "design-drivers")
    item_id = document.content_items[-1].id
    r = client.patch(
        f"/api/v2/ados-projects/{project.id}/documents/{document.id}/sections/{section_id}",
        json={"content_item_ids": [item_id]},
    )
    assert r.status_code == 200, r.text

    project_after = _load(tmp_root, project.id)
    document_after = project_after.document(document.id)
    ds = build_design_state(project_after, document_after, _seeded_brand(project_after))
    rule = next(rr for rr in ds.constraints.rules if rr.id == "DES-001")
    assert rule.satisfied is True


def test_asset_state_mirrors_project_assets(client, tmp_path):
    import io

    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    asset = client.post(
        f"/api/v2/ados-projects/{p['id']}/assets",
        files={"file": ("a.png", io.BytesIO(b"\x89PNGfakebytes"), "image/png")},
    ).json()
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "D"}).json()
    project = _load(str(tmp_path / "ados-projects"), p["id"])
    document = project.document(doc["id"])
    ds = build_design_state(project, document, None)
    assert len(ds.assets) == 1
    assert ds.assets[0].id == asset["id"]
    assert ds.assets[0].filename == "a.png"


# ---------------------------------------------------------------------------
# Version-scoped reads
# ---------------------------------------------------------------------------


def test_version_scoped_design_state_matches_the_saved_snapshot(client, tmp_path):
    tmp_root = str(tmp_path / "ados-projects")
    project, document, _ = _composed_project_and_doc(client, tmp_root)
    client.post(f"/api/v2/ados-projects/{project.id}/versions", json={"document_id": document.id})

    project_after = _load(tmp_root, project.id)
    document_after = project_after.document(document.id)
    ds = build_design_state(project_after, document_after, _seeded_brand(project_after), version_number=1)
    assert ds.version.number == 1
    assert ds.version.available_versions == (1,)
    # the version-scoped content_selection is cleared (already resolved into content_items)
    assert ds.content.selected_shared_ids == ()
    assert len(ds.content.own) == 2  # own narrative + the resolved shared item, merged


def test_version_scoped_design_state_unknown_version_raises(client, tmp_path):
    from brand.project.versioning import VersionNotFoundError

    tmp_root = str(tmp_path / "ados-projects")
    project, document, _ = _composed_project_and_doc(client, tmp_root)
    with pytest.raises(VersionNotFoundError):
        build_design_state(project, document, _seeded_brand(project), version_number=99)


# ---------------------------------------------------------------------------
# API -- GET .../design-state (ADOS-M2.5 §21)
# ---------------------------------------------------------------------------


def test_get_design_state_endpoint_returns_a_real_design_state(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))

    r = client.get(f"/api/v2/ados-projects/{project.id}/documents/{document.id}/design-state")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["schema_version"] == "2.5"
    assert body["project"]["id"] == project.id
    assert body["project"]["project_data"] == {"client": "Acme"}
    assert body["document"]["id"] == document.id
    assert len(body["pages"]) > 0


def test_get_design_state_endpoint_accepts_a_version_query_param(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))
    client.post(f"/api/v2/ados-projects/{project.id}/versions", json={"document_id": document.id})

    r = client.get(
        f"/api/v2/ados-projects/{project.id}/documents/{document.id}/design-state", params={"version": 1},
    )
    assert r.status_code == 200, r.text
    assert r.json()["version"]["number"] == 1


def test_get_design_state_endpoint_unknown_version_404s(client, tmp_path):
    project, document, _ = _composed_project_and_doc(client, str(tmp_path / "ados-projects"))

    r = client.get(
        f"/api/v2/ados-projects/{project.id}/documents/{document.id}/design-state", params={"version": 99},
    )
    assert r.status_code == 404


def test_get_design_state_endpoint_works_without_a_brand_attached(client, tmp_path):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "D"}).json()

    r = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/design-state")
    assert r.status_code == 200, r.text
    assert r.json()["brand"]["id"] is None


def test_get_design_state_endpoint_unknown_document_404s(client, tmp_path):
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    r = client.get(f"/api/v2/ados-projects/{p['id']}/documents/does-not-exist/design-state")
    assert r.status_code == 404
