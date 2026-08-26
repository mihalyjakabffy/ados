"""
ADOS-M2.5 §24/§25 -- the cross-projection acceptance test.

The master prompt's central assertion for this milestone: "Consider it
complete only when the repository demonstrates that one DesignState can
genuinely drive multiple different document/output projections through
the same underlying composition infrastructure without duplicating the
core engine." This file builds exactly ONE project, attaches ONE brand,
seeds ONE shared content item at the project level, then creates seven
documents of seven different Document Types (projections) inside that
same project -- Investor Deck, Competition Book, Planning Report,
Portfolio, Case Study, Tender Document and a Custom (free-form) document
-- and composes every one of them through the same, unmodified
brand.creative.composer.compose / brand.creative.evaluate.evaluate calls
every other document type already goes through (see
test_nine_document_types.py). Every one of them also includes the same
shared content item, proving "same content, multiple projections", and
every one of them resolves to a DesignState sharing the same
ProjectState -- proving the projections really do sit on top of one
underlying state rather than nine independent little engines.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from brand.design_state.build import build_design_state  # noqa: E402
from brand.project.document_types import DOCUMENT_TYPES  # noqa: E402

BRAND_ID = "5747d10b-0000-4000-8000-000000000001"

#: The seven projections the master prompt names by example (Mission,
#: §24) that exist in this repository today -- "Website" is deliberately
#: excluded from this list because it is an export *format* choice
#: (ADOS-M2.5 §15/§16, see tests_brand/test_export.py), not a Document
#: Type, so it has nothing to add to a "which projections exist" list.
PROJECTIONS = (
    "investor-deck",       # Investor Deck
    "competition-document",  # Competition Book
    "planning-submission",   # Planning Report
    "portfolio",              # Portfolio
    "case-study",             # Case Study
    "tender-document",        # Tender Document
    "",                        # Custom Document -- free-form, no DocumentType
)


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


def _one_project_with_shared_content(client, tmp_root):
    p = client.post(
        "/api/v2/ados-projects", json={"name": "One Real Project", "description": "A single design state."},
    ).json()
    client.patch(f"/api/v2/ados-projects/{p['id']}", json={"project_data": {"client": "Acme", "location": "Berlin"}})
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    shared = client.post(
        f"/api/v2/ados-projects/{p['id']}/content",
        json={"kind": "text", "text": "A fact shared across every projection of this one project."},
    ).json()["content_items"][0]
    return p["id"], shared["id"]


def _create_and_compose(client, project_id: str, type_id: str, shared_item_id: str) -> str:
    """Create one document of ``type_id`` in the shared project, pull in
    the shared content item, satisfy whatever that type minimally needs to
    compose, and compose it through the real, shared engine. Returns the
    document id."""
    doc = client.post(
        f"/api/v2/ados-projects/{project_id}/documents",
        json={"name": f"Doc ({type_id or 'custom'})", "document_type_id": type_id},
    ).json()
    client.put(
        f"/api/v2/ados-projects/{project_id}/documents/{doc['id']}/content-selection",
        json={"content_item_ids": [shared_item_id]},
    )

    doc_type = DOCUMENT_TYPES.get(type_id) if type_id else None
    if doc_type and doc_type.supports_multi_project:
        ref = client.post("/api/v2/ados-projects", json={"name": f"Referenced for {type_id}"}).json()
        client.post(
            f"/api/v2/ados-projects/{project_id}/documents/{doc['id']}/project-refs",
            json={"project_id": ref["id"]},
        )
    else:
        client.post(
            f"/api/v2/ados-projects/{project_id}/documents/{doc['id']}/content",
            json={"kind": "text", "text": f"A narrative paragraph unique to this {type_id or 'custom'} document."},
        )

    r = client.post(f"/api/v2/ados-projects/{project_id}/documents/{doc['id']}/compose")
    assert r.status_code == 200, f"{type_id!r} failed to compose: {r.text}"
    return doc["id"]


# ---------------------------------------------------------------------------
# The cross-projection assertion
# ---------------------------------------------------------------------------


def test_one_design_state_drives_every_projection(client, tmp_path):
    tmp_root = str(tmp_path / "ados-projects")
    project_id, shared_item_id = _one_project_with_shared_content(client, tmp_root)

    document_ids = {
        type_id: _create_and_compose(client, project_id, type_id, shared_item_id)
        for type_id in PROJECTIONS
    }

    project = _load(tmp_root, project_id)
    brand = _seeded_brand(project)

    states = {}
    for type_id, doc_id in document_ids.items():
        document = project.document(doc_id)
        states[type_id] = build_design_state(project, document, brand)

    # Every projection composed through the same shared engine and
    # produced a real, non-empty plan -- no bespoke per-type generator.
    for type_id, state in states.items():
        assert len(state.pages) > 0, f"{type_id!r} produced no pages"
        assert len(state.components) > 0, f"{type_id!r} produced no components"

    # They all derive from the same underlying DesignState's Project layer
    # -- same id, same name, same project_data, same document roster --
    # not nine independent little states that happen to share a name.
    reference = states[PROJECTIONS[0]].project
    for type_id, state in states.items():
        assert state.project.id == reference.id, f"{type_id!r} diverged on project id"
        assert state.project.name == reference.name
        assert state.project.project_data == {"client": "Acme", "location": "Berlin"}
        assert state.project.document_ids == reference.document_ids

    # Same brand everywhere -- the Brand layer is shared state, not a
    # property of any one projection (ADOS-M2.5 §5).
    for type_id, state in states.items():
        assert state.brand.id == states[PROJECTIONS[0]].brand.id
        assert state.brand.tokens == states[PROJECTIONS[0]].brand.tokens

    # The shared content item is genuinely shared -- present in every
    # projection's content, not copied per-type.
    for type_id, state in states.items():
        shared_ids = {i.id for i in state.content.shared_pool}
        assert shared_item_id in shared_ids, f"{type_id!r} lost the shared pool"
        assert shared_item_id in state.content.selected_shared_ids, f"{type_id!r} did not select the shared item"

    # ...but the projections are genuinely different outputs, not the same
    # document under nine names -- each names its own real output_type and
    # (except the untyped custom document) its own audience/purpose.
    output_types = {type_id: state.document.output_type for type_id, state in states.items()}
    assert output_types == {t: t for t in PROJECTIONS}
    typed = [t for t in PROJECTIONS if t]
    for t in typed:
        assert states[t].document.audience, f"{t!r} has no audience"
        assert states[t].document.purpose, f"{t!r} has no purpose"
    # Not every projection is worded identically for the same audience --
    # a real range of audiences across the roster, not one label repeated.
    assert len({states[t].document.audience for t in typed}) > 1


def test_removing_the_shared_item_would_affect_every_projection_equally(client, tmp_path):
    """Not "each projection has its own copy of the content" -- one pool,
    referenced by id, from every projection at once (ADOS-M2.5 §6)."""
    tmp_root = str(tmp_path / "ados-projects")
    project_id, shared_item_id = _one_project_with_shared_content(client, tmp_root)

    doc_a = _create_and_compose(client, project_id, "investor-deck", shared_item_id)
    doc_b = _create_and_compose(client, project_id, "case-study", shared_item_id)

    project = _load(tmp_root, project_id)
    assert project.document(doc_a).content_selection == (shared_item_id,)
    assert project.document(doc_b).content_selection == (shared_item_id,)
    assert len(project.content_items) == 1  # one pool item, two references to it


# ---------------------------------------------------------------------------
# Determinism (ADOS-M2.5 §24): identical inputs -> identical composition,
# even after composing several *different* projections of the same
# project in between -- no projection leaks state into the next.
# ---------------------------------------------------------------------------


def test_composition_is_deterministic_across_interleaved_projections(client, tmp_path):
    tmp_root = str(tmp_path / "ados-projects")
    project_id, shared_item_id = _one_project_with_shared_content(client, tmp_root)

    doc_id = _create_and_compose(client, project_id, "planning-submission", shared_item_id)
    project = _load(tmp_root, project_id)
    plan_a = project.document(doc_id).latest_plan

    # Compose two unrelated projections in the same project in between.
    _create_and_compose(client, project_id, "portfolio", shared_item_id)
    _create_and_compose(client, project_id, "tender-document", shared_item_id)

    r = client.post(f"/api/v2/ados-projects/{project_id}/documents/{doc_id}/compose")
    assert r.status_code == 200, r.text
    plan_b = r.json()["plan"]

    plan_a_clean = {k: v for k, v in plan_a.items() if k != "plan_hash"}
    plan_b_clean = {k: v for k, v in plan_b.items() if k != "plan_hash"}
    assert plan_a_clean == plan_b_clean


def test_design_state_is_deterministic_across_interleaved_projections(client, tmp_path):
    """Building another projection's DesignState in between must not leave
    any shared mutable state behind that corrupts the next one -- both
    documents already exist and are already composed, so the project
    itself is not mutated between the two reads of ``doc_id``."""
    tmp_root = str(tmp_path / "ados-projects")
    project_id, shared_item_id = _one_project_with_shared_content(client, tmp_root)

    doc_id = _create_and_compose(client, project_id, "competition-document", shared_item_id)
    other_doc_id = _create_and_compose(client, project_id, "case-study", shared_item_id)

    project = _load(tmp_root, project_id)
    brand = _seeded_brand(project)

    state_a = build_design_state(project, project.document(doc_id), brand).to_dict()
    build_design_state(project, project.document(other_doc_id), brand)  # a different projection, read in between
    state_b = build_design_state(project, project.document(doc_id), brand).to_dict()
    assert state_a == state_b
