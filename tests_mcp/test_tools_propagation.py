"""
tests_mcp/test_tools_propagation.py

ados_mcp.tools.propagation against a mocked HTTP transport.
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
    monkeypatch.setattr(tools.propagation, "get_client", lambda: fake)


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content) if request.content else {}


def test_propagate_content_change(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "touched": [{"document_id": "d1", "recomposed": True}],
                "unaffected": ["d2"],
            },
        )

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.propagation.propagate_content_change("p1", "c1"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/content/c1/propagate"
    assert result["touched"][0]["document_id"] == "d1"
    assert result["unaffected"] == ["d2"]


def test_propagate_content_change_surfaces_no_brand_attached(monkeypatch: pytest.MonkeyPatch) -> None:
    from ados_mcp.client import AdosConnectionError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": {"error": "no_brand_attached"}})

    _patch_client(monkeypatch, handler)

    with pytest.raises(AdosConnectionError, match="no_brand_attached"):
        asyncio.run(tools.propagation.propagate_content_change("p1", "c1"))


def test_propagate_brand_change(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(
            200,
            json={"touched": [{"document_id": "d1"}, {"document_id": "d2"}], "unaffected": [], "brand_version": "1.1.0"},
        )

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.propagation.propagate_brand_change("p1", "1.1.0"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/brand/propagate"
    assert seen["body"] == {"brand_version": "1.1.0"}
    assert result["brand_version"] == "1.1.0"
    assert len(result["touched"]) == 2


def test_propagate_brand_change_unknown_version_is_surfaced(monkeypatch: pytest.MonkeyPatch) -> None:
    from ados_mcp.client import AdosConnectionError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "no such version"})

    _patch_client(monkeypatch, handler)

    with pytest.raises(AdosConnectionError, match="not found"):
        asyncio.run(tools.propagation.propagate_brand_change("p1", "9.9.9"))
