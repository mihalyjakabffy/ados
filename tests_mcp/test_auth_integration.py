"""
tests_mcp/test_auth_integration.py

ados_mcp.auth.protect() wrapping a real FastMCP ASGI app (not a bare
dummy Starlette app) — proves the bearer-token guard actually sits in
front of the real MCP transport, not just a stand-in. Never completes a
full MCP protocol handshake (that would need a real client session); an
unauthenticated request being refused before it reaches the MCP app at
all is the thing this test needs to prove.

Uses a throwaway FastMCP instance per test, not the shared
``ados_mcp.server.mcp`` singleton — its own ``streamable_http_app()``
lazily creates and caches one ``StreamableHTTPSessionManager``, which
refuses to run more than once per process; a fresh instance per test
avoids that shared-state trap without needing the real tool/resource set
registered (the guard operates at the ASGI layer, independent of what
tools exist behind it).
"""

from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP
from starlette.testclient import TestClient

from ados_mcp import auth


def test_unauthenticated_request_to_a_real_streamable_http_app_is_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "test-token")
    app = auth.protect(FastMCP(name="test").streamable_http_app())

    with TestClient(app) as client:
        r = client.post("/mcp", json={"jsonrpc": "2.0", "method": "ping", "id": 1})

    assert r.status_code == 401


def test_authenticated_request_reaches_past_the_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Doesn't assert a successful MCP response (that needs a real
    session handshake) — only that the guard itself stops rejecting once
    the token is correct, i.e. the request reaches the MCP app's own
    logic instead of being turned away at 401."""
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "test-token")
    app = auth.protect(FastMCP(name="test").streamable_http_app())

    with TestClient(app) as client:
        r = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "ping", "id": 1},
            headers={"Authorization": "Bearer test-token", "Accept": "application/json, text/event-stream"},
        )

    assert r.status_code != 401
