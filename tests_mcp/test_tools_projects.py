"""
tests_mcp/test_tools_projects.py

ados_mcp.tools.projects against a mocked HTTP transport — proves each
tool sends the right verb, path and body to api/main.py and passes the
response straight through, with no live server needed.
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
    monkeypatch.setattr(tools.projects, "get_client", lambda: fake)


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content)


def test_create_project(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(201, json={"id": "p1", "name": "The Malthouse"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.projects.create_project("The Malthouse", "A quiet adaptive-reuse project"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects"
    assert seen["body"] == {"name": "The Malthouse", "description": "A quiet adaptive-reuse project"}
    assert result["id"] == "p1"


def test_update_project_data_only_sends_provided_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"id": "p1"})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.projects.update_project_data("p1", project_data={"client": "Acme Co"}))

    assert seen["method"] == "PATCH"
    assert seen["path"] == "/api/v2/ados-projects/p1"
    assert seen["body"] == {"project_data": {"client": "Acme Co"}}


def test_attach_brand_without_version(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"id": "p1", "brand_id": "b1"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.projects.attach_brand("p1", "b1"))

    assert seen["method"] == "PUT"
    assert seen["path"] == "/api/v2/ados-projects/p1/brand"
    assert seen["body"] == {"brand_id": "b1"}
    assert result["brand_id"] == "b1"


def test_attach_brand_with_version(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _body(request)
        return httpx.Response(200, json={})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.projects.attach_brand("p1", "b1", brand_version="2.0"))

    assert seen["body"] == {"brand_id": "b1", "brand_version": "2.0"}


def test_create_project_surfaces_a_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from ados_mcp.client import AdosConnectionError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": [{"msg": "name too short"}]})

    _patch_client(monkeypatch, handler)

    with pytest.raises(AdosConnectionError, match="name too short"):
        asyncio.run(tools.projects.create_project(""))
