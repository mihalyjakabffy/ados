"""
tests_mcp/test_resources.py

Each ADOS-M4.1 resource function against a mocked HTTP transport — proves
every function requests the right path(s) on the right backend and passes
the response through, without needing api/main.py or ados-service/main.py
running. The @mcp.resource decorator returns the original function
unchanged (mcp.server.fastmcp.FastMCP.resource's own source), so these are
called directly, the same as any other async function.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from ados_mcp import resources
from ados_mcp.client import AdosClient


def _patch_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    fake = AdosClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(resources, "get_client", lambda: fake)


def test_list_projects(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return httpx.Response(200, json={"projects": [{"id": "p1"}]})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(resources.list_projects())

    assert seen["path"] == "/api/v2/ados-projects"
    assert result == {"projects": [{"id": "p1"}]}


def test_get_project(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return httpx.Response(200, json={"id": "p1", "name": "The Malthouse"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(resources.get_project("p1"))

    assert seen["path"] == "/api/v2/ados-projects/p1"
    assert result["name"] == "The Malthouse"


def test_get_shared_content(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return httpx.Response(200, json={"items": []})

    _patch_client(monkeypatch, handler)

    asyncio.run(resources.get_shared_content("p1"))

    assert seen["path"] == "/api/v2/ados-projects/p1/content"


def test_get_design_state(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return httpx.Response(200, json={"schema_version": "2.5"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(resources.get_design_state("p1", "d1"))

    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/design-state"
    assert result == {"schema_version": "2.5"}


def test_get_brand_merges_identity_and_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("/tokens"):
            return httpx.Response(200, json={"font.size.sm.pt": 9.74})
        return httpx.Response(200, json={"id": "b1", "name": "STUDIO OM"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(resources.get_brand("b1"))

    assert paths == ["/api/v2/brands/b1", "/api/v2/brands/b1/tokens"]
    assert result == {
        "brand": {"id": "b1", "name": "STUDIO OM"},
        "tokens": {"font.size.sm.pt": 9.74},
    }


def test_get_rules_uses_the_service_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"rules": []})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(resources.get_rules())

    assert seen["url"] == "http://localhost:8010/api/rules"
    assert result == {"rules": []}


def test_resources_are_registered_on_the_shared_server() -> None:
    from ados_mcp.server import mcp

    templates = {t.uriTemplate for t in asyncio.run(mcp.list_resource_templates())}
    static = {r.uri for r in asyncio.run(mcp.list_resources())}

    assert any(str(u) == "ados://projects" for u in static)
    assert any(str(u) == "ados://rules" for u in static)
    assert "ados://projects/{project_id}" in templates
    assert "ados://projects/{project_id}/content" in templates
    assert "ados://projects/{project_id}/documents/{document_id}/design-state" in templates
    assert "ados://brands/{brand_id}" in templates
