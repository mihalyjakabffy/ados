"""
ADOS-M2.2.1 P2 -- the nine-workflow smoke test.

One parameterized test proving all nine Document Types actually compose
through the *same* shared engine (brand.creative.composer.compose /
brand.creative.evaluate.evaluate) -- not nine bespoke generators, exactly
the master prompt's explicit instruction ("DO NOT CREATE NINE CUSTOM TEST
SYSTEMS"). Per-type behavioural detail (Portfolio's project references,
Planning Submission's page ceiling, Competition's COMP-001 ceiling, ...)
already has its own coverage in test_document_workflows_api.py; this file
only proves the shared pipeline itself holds across the full roster.

An API test proves the pipeline, not the product -- it cannot see whether
the wizard, Structure panel or Canvas actually render each type. That is
why this file is paired with a live Playwright pass driving all nine
through the real frontend (recorded in the M2.2.1 final report, not here
-- Playwright is not part of this repo's Python test suite).
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from brand.project.document_types import DOCUMENT_TYPES  # noqa: E402

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


def test_all_nine_document_types_are_registered():
    assert len(DOCUMENT_TYPES) == 9


@pytest.mark.parametrize("type_id", sorted(DOCUMENT_TYPES))
def test_document_type_composes_through_the_shared_engine(client, type_id):
    doc_type = DOCUMENT_TYPES[type_id]

    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})

    doc = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents",
        json={"name": "Doc", "document_type_id": type_id},
    ).json()
    assert doc["document_type_id"] == type_id
    assert doc["direction_id"] == doc_type.composition_profile

    # The wizard's Step 5 default skeleton -- every default_structure kind
    # became a real Section, in order (ADOS-M2.2 §5).
    assert [s["kind"] for s in doc["sections"]] == list(doc_type.default_structure)

    if doc_type.supports_multi_project:
        # Portfolio composes from referenced projects' own content, not its
        # own content_items -- an empty referenced project still yields a
        # chapter (api/routers/ados_project.py's _document_content_model
        # falls back to the project's own description).
        ref = client.post("/api/v2/ados-projects", json={"name": "Referenced Project"}).json()
        client.post(
            f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/project-refs",
            json={"project_id": ref["id"]},
        )
    else:
        added = client.post(
            f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
            json={"kind": "text", "text": f"A narrative paragraph exercising the {doc_type.name} workflow."},
        )
        assert added.status_code == 201, added.text

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 200, r.text
    body = r.json()

    assert len(body["plan"]["pages"]) > 0
    assert body["plan"]["direction"] == doc_type.composition_profile
    assert body["evaluation"]["coverage"]
    # requirement_findings is always present -- possibly non-empty (a bare
    # smoke document rarely satisfies every ERROR-severity requirement),
    # but composing itself must never have failed to produce a real plan.
    assert isinstance(body["requirement_findings"], list)
