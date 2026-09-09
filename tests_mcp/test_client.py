"""
tests_mcp/test_client.py

AdosClient against a mocked HTTP transport — no live api/main.py or
ados-service/main.py needed. Proves the URL construction, the
api-vs-service routing, and the error messages a chat session would
actually see when a backend is down or returns an error.
"""

from __future__ import annotations

import asyncio
import json

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


# -- write verbs (ADOS-M4.2) -------------------------------------------


def test_post_api_sends_json_body_and_returns_the_response() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["body"] = request.content
        return httpx.Response(201, json={"id": "p1"})

    result = asyncio.run(_client_with(handler).post_api("/ados-projects", json={"name": "X"}))

    assert seen["method"] == "POST"
    assert seen["url"] == "http://localhost:8000/api/v2/ados-projects"
    assert b'"name":"X"' in seen["body"] or b'"name": "X"' in seen["body"]
    assert result == {"id": "p1"}


def test_post_api_sends_query_params_alongside_the_body() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["query"] = dict(request.url.params)
        seen["body"] = json.loads(request.content) if request.content else {}
        return httpx.Response(201, json={"ok": True})

    result = asyncio.run(
        _client_with(handler).post_api(
            "/brand-proposals/approve", json={"brand": {}}, params={"approved_by": "Jane Doe"}
        )
    )

    assert seen["query"] == {"approved_by": "Jane Doe"}
    assert seen["body"] == {"brand": {}}
    assert result == {"ok": True}


def test_patch_put_delete_use_the_expected_verb() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.method)
        return httpx.Response(200, json={"ok": True})

    client = _client_with(handler)
    asyncio.run(client.patch_api("/ados-projects/p1", json={"name": "Y"}))
    asyncio.run(client.put_api("/ados-projects/p1/brand", json={"brand_id": "b1"}))
    asyncio.run(client.delete_api("/ados-projects/p1/content/c1"))

    assert seen == ["PATCH", "PUT", "DELETE"]


def test_empty_response_body_becomes_an_empty_dict() -> None:
    """DELETE /ados-projects/{id} (not wrapped by any tool yet) replies
    204 with no body — proves the client doesn't choke on that shape
    once a future tool does wrap it."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    result = asyncio.run(_client_with(handler).delete_api("/ados-projects/p1"))

    assert result == {}


def test_write_error_surfaces_the_structured_detail() -> None:
    """ADOS's own routers reply to a rejected write with a real
    ``{"detail": {"error": ..., ...}}`` body — the exact information a
    chat session needs to explain the refusal. Proves it survives into
    the raised error rather than being replaced by a generic message."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422, json={"detail": {"error": "invalid_content_item", "errors": ["value required"]}}
        )

    with pytest.raises(AdosConnectionError, match="invalid_content_item"):
        asyncio.run(_client_with(handler).post_api("/ados-projects/p1/content", json={}))
