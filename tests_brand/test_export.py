"""
api/routers/ados_project.py's Export endpoints -- ADOS-M2.2.1 P0/P1.

Production PDF export through the real, existing pipeline
(brand.templates.renderers.render_page_plan -> brand.export.exporters.html_to_pdf,
Chromium's own print path). These tests exercise the actual renderer and the
actual browser -- nothing here is mocked -- because a PDF export capability is
only real if it was actually produced and actually opens.

Mounted on the real FastAPI app, storage redirected to a tmp dir per test,
exactly test_project_api.py's own convention.
"""

from __future__ import annotations

import io

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from brand.export.exporters import browser_available  # noqa: E402

BRAND_ID = "5747d10b-0000-4000-8000-000000000001"

#: Chromium is confirmed present in the dev/CI environment
#: (requirements.txt + ci.yml's "Install Chromium" step), but a real export
#: test suite must not crash-fail everywhere else Chromium happens to be
#: absent -- it should say so, once, and skip.
requires_browser = pytest.mark.skipif(
    not browser_available(), reason="Chromium/Playwright not available in this environment",
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


def _project_with_brand(client) -> dict:
    p = client.post("/api/v2/ados-projects", json={"name": "P"}).json()
    client.put(f"/api/v2/ados-projects/{p['id']}/brand", json={"brand_id": BRAND_ID})
    return p


def _composed_document(client, project, *, document_type_id: str = "", text: str = "A narrative paragraph.") -> dict:
    doc = client.post(
        f"/api/v2/ados-projects/{project['id']}/documents",
        json={"name": "Doc", "document_type_id": document_type_id},
    ).json()
    client.post(
        f"/api/v2/ados-projects/{project['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": text},
    )
    r = client.post(f"/api/v2/ados-projects/{project['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 200, r.text
    return doc


# ---------------------------------------------------------------------------
# P0 -- a real PDF, or an honest reason there isn't one
# ---------------------------------------------------------------------------


@requires_browser
def test_successful_export_produces_a_real_pdf(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p)

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})
    assert r.status_code == 201, r.text
    export = r.json()["export"]
    assert export["status"] == "completed"
    assert export["page_count"] > 0
    assert export["version_number"] == 1
    assert export["error"] == ""

    downloaded = client.get(f"/api/v2/ados-projects/{p['id']}/exports/{export['id']}/file")
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    assert downloaded.content[:4] == b"%PDF"
    assert len(downloaded.content) > 500  # not a truncated/corrupted stub


@requires_browser
def test_export_without_composing_first_is_rejected(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "no_content"


def test_export_auto_saves_a_version_when_none_is_given(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p)
    assert client.get(f"/api/v2/ados-projects/{p['id']}/versions").json()["versions"] == []

    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})

    versions = client.get(f"/api/v2/ados-projects/{p['id']}/versions").json()["versions"]
    assert len(versions) == 1
    assert versions[0]["number"] == 1


# ---------------------------------------------------------------------------
# P1 -- validation gating: ERROR/BLOCK prevents a final export
# ---------------------------------------------------------------------------


def test_blocked_export_produces_no_pdf(client):
    """design-report (DES-001) requires a design-drivers section -- a document
    that never populated one must not be exportable, and must say why."""
    p = _project_with_brand(client)
    doc = _composed_document(client, p, document_type_id="design-report")

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["export"]["status"] == "blocked"
    assert body["export"]["validation_state"] == "blocked"
    assert body["export"]["path"] == ""
    assert any(f["code"] == "DES-001" for f in body["findings"])


def test_blocked_export_is_not_downloadable(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p, document_type_id="design-report")
    export = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={}).json()["export"]

    r = client.get(f"/api/v2/ados-projects/{p['id']}/exports/{export['id']}/file")
    assert r.status_code == 409
    assert r.json()["detail"]["status"] == "blocked"


@requires_browser
def test_warning_only_export_is_allowed(client):
    """A short, single-paragraph document trips the composer's own fill-ratio
    WARN (see the P0 smoke run) but carries no ERROR/BLOCK -- it must still
    export, exactly the "WARN does not block" rule the rest of the system
    already applies (brand.validation.brand_validator.ValidationReport.ok)."""
    p = _project_with_brand(client)
    doc = _composed_document(client, p, text="Short.")

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})
    assert r.status_code == 201, r.text
    export = r.json()["export"]
    assert export["status"] == "completed"
    assert export["validation_state"] in ("warnings", "passed")


# ---------------------------------------------------------------------------
# P1 -- version-tied export: "Version N's PDF must not silently change"
# ---------------------------------------------------------------------------


@requires_browser
def test_export_a_and_export_b_stay_tied_to_their_own_version(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p, text="Version one content, the original brief.")
    export_a = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={}).json()["export"]
    pdf_a = client.get(f"/api/v2/ados-projects/{p['id']}/exports/{export_a['id']}/file").content

    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "A second, substantially different paragraph describing a new chapter."},
    )
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    export_b = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={}).json()["export"]

    assert export_a["version_number"] == 1
    assert export_b["version_number"] == 2

    pdf_a_again = client.get(f"/api/v2/ados-projects/{p['id']}/exports/{export_a['id']}/file").content
    assert pdf_a_again == pdf_a, "Version 1's PDF changed after Version 2 was created"


@requires_browser
def test_export_targets_an_explicit_version_number(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p)
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})  # version 1

    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "More content for a second version."},
    )
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})  # version 2

    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={"version_number": 1},
    )
    assert r.status_code == 201
    assert r.json()["export"]["version_number"] == 1


def test_export_of_unknown_version_number_404s(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p)
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={"version_number": 99},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# P1 -- missing-asset handling: a dangling image reference degrades, not crashes
# ---------------------------------------------------------------------------


@requires_browser
def test_export_with_an_unresolvable_asset_reference_degrades_gracefully(client):
    p = _project_with_brand(client)
    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "image", "asset_id": "does-not-exist", "aspect": "4:3", "caption": "Missing photo"},
    )
    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 200, r.text

    export = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})
    assert export.status_code == 201
    assert export.json()["export"]["status"] == "completed"  # a wireframe box, not a crash


@requires_browser
def test_export_with_a_real_uploaded_image_asset_succeeds(client):
    p = _project_with_brand(client)
    asset = client.post(
        f"/api/v2/ados-projects/{p['id']}/assets",
        files={"file": ("photo.jpg", io.BytesIO(b"\xff\xd8\xfffakejpegbytes"), "image/jpeg")},
    ).json()

    doc = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc"}).json()
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "text", "text": "A short caption paragraph to accompany the photograph."},
    )
    client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/content",
        json={"kind": "image", "asset_id": asset["id"], "aspect": "4:3", "caption": "Site photo"},
    )
    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/compose")
    assert r.status_code == 200, r.text

    export = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})
    assert export.status_code == 201, export.text
    assert export.json()["export"]["status"] == "completed"


# ---------------------------------------------------------------------------
# P1 -- renderer failure: no fake success, no corrupted artifact
# ---------------------------------------------------------------------------


def test_renderer_failure_produces_failed_status_with_a_useful_error(client, monkeypatch):
    import brand.export.exporters as exporters
    from brand.export.exporters import RasterResult

    def _always_unavailable(*args, **kwargs):
        return RasterResult(None, False, "simulated Chromium failure for this test")

    monkeypatch.setattr(exporters, "html_to_pdf", _always_unavailable)
    import api.routers.ados_project as ados_project_router

    # the router imports html_to_pdf inside the function body (from
    # brand.export.exporters import html_to_pdf), so patching the module
    # attribute above is what the router's own import resolves to.

    p = _project_with_brand(client)
    doc = _composed_document(client, p)

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})
    assert r.status_code == 201
    export = r.json()["export"]
    assert export["status"] == "failed"
    assert "simulated Chromium failure" in export["error"]
    assert export["path"] == ""

    # no corrupted artifact left behind, and the file endpoint says so honestly
    download = client.get(f"/api/v2/ados-projects/{p['id']}/exports/{export['id']}/file")
    assert download.status_code == 409


# ---------------------------------------------------------------------------
# Listing + not-found edges
# ---------------------------------------------------------------------------


@requires_browser
def test_list_document_exports(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p)
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={})

    r = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/exports")
    assert r.status_code == 200
    assert len(r.json()["exports"]) == 1


def test_download_unknown_export_404s(client):
    p = _project_with_brand(client)
    r = client.get(f"/api/v2/ados-projects/{p['id']}/exports/does-not-exist/file")
    assert r.status_code == 404


def test_export_version_belonging_to_a_different_document_is_rejected(client):
    p = _project_with_brand(client)
    doc_a = _composed_document(client, p, text="Document A's own content.")
    client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc_a['id']}/export", json={})  # saves version 1

    doc_b = client.post(f"/api/v2/ados-projects/{p['id']}/documents", json={"name": "Doc B"}).json()
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc_b['id']}/export", json={"version_number": 1},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "version_belongs_to_different_document"


# ---------------------------------------------------------------------------
# ADOS-M2.5 -- Website projection: "html" is an export format, not a second
# renderer. No @requires_browser: this path never touches Chromium at all.
# ---------------------------------------------------------------------------


def test_html_export_produces_real_html_with_no_browser_dependency(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p)

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={"format": "html"})
    assert r.status_code == 201, r.text
    export = r.json()["export"]
    assert export["status"] == "completed"
    assert export["format"] == "html"
    assert export["path"].endswith(".html")
    assert export["filename"].endswith(".html")

    downloaded = client.get(f"/api/v2/ados-projects/{p['id']}/exports/{export['id']}/file")
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "text/html; charset=utf-8"
    assert "<html" in downloaded.text.lower()


def test_html_export_is_the_same_render_page_plan_output_the_pdf_pipeline_uses(client):
    """The Website projection reuses render_page_plan's own HTML -- it must
    contain the same document content, proving there is no second renderer."""
    p = _project_with_brand(client)
    doc = _composed_document(client, p, text="A distinctive sentence unique to this export test.")

    export = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={"format": "html"},
    ).json()["export"]
    downloaded = client.get(f"/api/v2/ados-projects/{p['id']}/exports/{export['id']}/file")
    assert "A distinctive sentence unique to this export test." in downloaded.text


def test_blocked_html_export_produces_no_file(client):
    """Format choice never bypasses validation gating -- a blocking finding
    blocks the html projection exactly as it blocks the pdf one."""
    p = _project_with_brand(client)
    doc = _composed_document(client, p, document_type_id="design-report")

    r = client.post(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={"format": "html"})
    assert r.status_code == 201, r.text
    export = r.json()["export"]
    assert export["status"] == "blocked"
    assert export["format"] == "html"
    assert export["path"] == ""

    download = client.get(f"/api/v2/ados-projects/{p['id']}/exports/{export['id']}/file")
    assert download.status_code == 409


@requires_browser
def test_pdf_and_html_exports_of_the_same_document_are_independent_versions(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p)

    html_export = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={"format": "html"},
    ).json()["export"]
    pdf_export = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={"format": "pdf"},
    ).json()["export"]

    assert html_export["format"] == "html"
    assert pdf_export["format"] == "pdf"
    assert html_export["id"] != pdf_export["id"]

    exports = client.get(f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/exports").json()["exports"]
    assert {e["format"] for e in exports} == {"html", "pdf"}


def test_invalid_export_format_is_rejected(client):
    p = _project_with_brand(client)
    doc = _composed_document(client, p)
    r = client.post(
        f"/api/v2/ados-projects/{p['id']}/documents/{doc['id']}/export", json={"format": "docx"},
    )
    assert r.status_code == 422
