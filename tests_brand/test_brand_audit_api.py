"""
tests_brand/test_brand_audit_api.py

api/routers/brand.py's ADOS-M4.5 ``POST /brands/{brand_id}/audit``
endpoint — a thin HTTP shell around
``brand.validation.consistency.audit_package``, already tested at the
domain level in ``test_identity_system.py``. This file only proves the
routing: brand loaded by id/version, the package directory resolved,
a 404 on a missing directory or an unknown brand, and the real audit
result passed straight through.
"""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from brand.examples.studio_om import studio_om


def _app():
    try:
        from api.main import app

        return app
    except BaseException:                                  # noqa: BLE001
        from fastapi import FastAPI

        from api.routers import brand as brand_router

        app = FastAPI()
        app.include_router(brand_router.router, prefix="/api/v2", tags=["brand"])
        return app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAND_STORAGE_ROOT", str(tmp_path / "brands"))
    import api.routers.brand as brand_router

    monkeypatch.setattr(brand_router, "_BRAND_ROOT", str(tmp_path / "brands"))

    with TestClient(_app()) as c:
        yield c


@pytest.fixture(scope="module")
def om():
    return studio_om()


@pytest.fixture(scope="module")
def package(tmp_path_factory, om):
    """A real, fully-built STUDIO OM package — expensive, so built once
    per module and reused, the same posture test_identity_system.py's
    own ``package`` fixture already takes."""
    from brand.examples.build_studio_om import build

    out = tmp_path_factory.mktemp("studio-om-api-audit")
    build(out, om)
    return out


@pytest.fixture()
def seeded(client, om):
    """The brand this test's own isolated store needs, so ``_load``
    inside the endpoint can find it — the built ``package`` fixture is
    independent of any one test's store."""
    import api.routers.brand as brand_router

    brand_router._repo().save(om)
    return client


def test_audit_a_clean_package_reports_ok(seeded, package, om):
    r = seeded.post(f"/api/v2/brands/{om.brand_id}/audit", json={"package_dir": str(package)})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["files_checked"] > 0
    assert body["brand"] == om.label


def test_audit_missing_directory_is_a_404(seeded, om):
    r = seeded.post(
        f"/api/v2/brands/{om.brand_id}/audit",
        json={"package_dir": "/no/such/directory/at/all"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "package_dir_not_found"


def test_audit_unknown_brand_is_a_404(client, package):
    r = client.post("/api/v2/brands/does-not-exist/audit", json={"package_dir": str(package)})
    assert r.status_code == 404


def test_audit_router_is_mounted():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "api" / "routers" / "brand.py").read_text()
    assert '@router.post("/brands/{brand_id}/audit")' in source
