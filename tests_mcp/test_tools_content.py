"""
tests_mcp/test_tools_content.py

ados_mcp.tools.content against a mocked HTTP transport.
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
    monkeypatch.setattr(tools.content, "get_client", lambda: fake)


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content)


def test_add_document_content(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(201, json={"id": "d1", "content_items": [{"id": "c1"}]})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(
        tools.content.add_document_content(
            "p1", "d1", kind="metric", label="GFA", value=1200, unit="m2", provenance="survey"
        )
    )

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/content"
    assert seen["body"] == {
        "kind": "metric",
        "label": "GFA",
        "text": "",
        "value": 1200,
        "unit": "m2",
        "provenance": "survey",
        "asset_id": None,
        "caption": "",
        "aspect": "",
    }
    assert result["id"] == "d1"


def test_remove_document_content(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(200, json={"id": "d1"})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.content.remove_document_content("p1", "d1", "c1"))

    assert seen["method"] == "DELETE"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/content/c1"


def test_add_shared_content(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(201, json={"id": "p1", "content_items": []})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.content.add_shared_content("p1", kind="narrative", text="Adaptive reuse of a malthouse."))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/content"
    assert seen["body"]["kind"] == "narrative"
    assert seen["body"]["text"] == "Adaptive reuse of a malthouse."


def test_remove_shared_content(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return httpx.Response(200, json={"id": "p1"})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.content.remove_shared_content("p1", "c1"))

    assert seen["path"] == "/api/v2/ados-projects/p1/content/c1"


def test_select_content_for_document_replaces_the_whole_list(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"id": "d1", "content_selection": ["c1", "c2"]})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.content.select_content_for_document("p1", "d1", ["c1", "c2"]))

    assert seen["method"] == "PUT"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/content-selection"
    assert seen["body"] == {"content_item_ids": ["c1", "c2"]}
    assert result["content_selection"] == ["c1", "c2"]


def test_unknown_selected_id_surfaces_the_real_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    from ados_mcp.client import AdosConnectionError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422, json={"detail": {"error": "unknown_shared_content_item", "ids": ["ghost"]}}
        )

    _patch_client(monkeypatch, handler)

    with pytest.raises(AdosConnectionError, match="unknown_shared_content_item"):
        asyncio.run(tools.content.select_content_for_document("p1", "d1", ["ghost"]))
