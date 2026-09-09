"""
tests_mcp/test_tools_brand.py

ados_mcp.tools.brand against a mocked HTTP transport.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from ados_mcp import tools
from ados_mcp.client import AdosClient


def _patch_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    fake = AdosClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(tools.brand, "get_client", lambda: fake)


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content) if request.content else {}


def test_propose_brand(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(
            200,
            json={"brand": {"id": "b1"}, "confidence": 0.7, "open_questions": ["what typeface?"]},
        )

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.brand.propose_brand("A quiet, material practice."))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/brand-proposals"
    assert seen["body"] == {"brief": "A quiet, material practice."}
    assert result["confidence"] == 0.7


def test_propose_brand_with_name(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _body(request)
        return httpx.Response(200, json={})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.brand.propose_brand("brief text", name="Studio X"))

    assert seen["body"] == {"brief": "brief text", "name": "Studio X"}


def test_approve_brand_sends_approved_by_as_query_param(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["query"] = dict(request.url.params)
        seen["body"] = _body(request)
        return httpx.Response(201, json={"brand_id": "b1", "status": "approved"})

    _patch_client(monkeypatch, handler)

    proposal = {"brand": {"id": "b1", "name": "X"}, "rationale": "..."}
    result = asyncio.run(tools.brand.approve_brand(proposal, "Mihály Jakabffy"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/brand-proposals/approve"
    assert seen["query"] == {"approved_by": "Mihály Jakabffy"}
    assert seen["body"] == proposal
    assert result["status"] == "approved"


def test_approve_brand_surfaces_validation_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from ados_mcp.client import AdosConnectionError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": {"message": "proposal does not validate"}})

    _patch_client(monkeypatch, handler)

    with pytest.raises(AdosConnectionError, match="does not validate"):
        asyncio.run(tools.brand.approve_brand({"brand": {}}, "Someone"))


def test_audit_brand(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["query"] = dict(request.url.params)
        seen["body"] = _body(request)
        return httpx.Response(200, json={"ok": True, "files_checked": 48})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.brand.audit_brand("b1", "/tmp/studio-om-package"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/brands/b1/audit"
    assert seen["query"] == {}
    assert seen["body"] == {"package_dir": "/tmp/studio-om-package"}
    assert result["files_checked"] == 48


def test_audit_brand_with_version(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["query"] = dict(request.url.params)
        return httpx.Response(200, json={"ok": True})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.brand.audit_brand("b1", "/tmp/pkg", version="2.0.0"))

    assert seen["query"] == {"version": "2.0.0"}


def test_audit_brand_missing_directory_is_surfaced(monkeypatch: pytest.MonkeyPatch) -> None:
    from ados_mcp.client import AdosConnectionError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": {"error": "package_dir_not_found"}})

    _patch_client(monkeypatch, handler)

    with pytest.raises(AdosConnectionError, match="package_dir_not_found"):
        asyncio.run(tools.brand.audit_brand("b1", "/no/such/dir"))
