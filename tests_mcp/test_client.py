"""
tests_mcp/test_client.py

AdosClient against a mocked HTTP transport — no live api/main.py or
ados-service/main.py needed. Proves the URL construction, the
api-vs-service routing, and the error messages a chat session would
actually see when a backend is down or returns an error.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from ados_mcp.client import AdosClient, AdosConnectionError


def _client_with(handler) -> AdosClient:
    return AdosClient(transport=httpx.MockTransport(handler))


def test_get_api_hits_the_api_base_and_returns_json() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"projects": []})

    result = asyncio.run(_client_with(handler).get_api("/ados-projects"))

    assert seen["url"] == "http://localhost:8000/api/v2/ados-projects"
    assert result == {"projects": []}


def test_get_service_hits_the_service_base() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"rules": []})

    result = asyncio.run(_client_with(handler).get_service("/api/rules"))

    assert seen["url"] == "http://localhost:8010/api/rules"
    assert result == {"rules": []}


def test_404_raises_a_readable_ados_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "no such project"})

    with pytest.raises(AdosConnectionError, match="not found"):
        asyncio.run(_client_with(handler).get_api("/ados-projects/does-not-exist"))


def test_server_error_includes_status_and_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    with pytest.raises(AdosConnectionError, match="500"):
        asyncio.run(_client_with(handler).get_api("/ados-projects"))


def test_connect_error_names_the_backend_and_the_override_variable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(AdosConnectionError, match="ADOS_API_BASE_URL"):
        asyncio.run(_client_with(handler).get_api("/ados-projects"))


def test_base_url_is_configurable_via_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADOS_API_BASE_URL", "http://example.internal:9999/api/v2")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={})

    asyncio.run(_client_with(handler).get_api("/ados-projects"))

    assert seen["url"] == "http://example.internal:9999/api/v2/ados-projects"
