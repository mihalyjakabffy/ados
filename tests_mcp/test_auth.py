"""
tests_mcp/test_auth.py

ados_mcp.auth — the bearer-token guard for the remote transport (ADOS-M4.6).
Tested against a trivial Starlette app wrapped by `protect()`, not a live
FastMCP server: the middleware's job is the same regardless of what it
wraps, and a dummy app keeps these tests fast and independent of the MCP
protocol itself.
"""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from ados_mcp import auth


def _dummy_app() -> Starlette:
    async def handler(request):
        return JSONResponse({"ok": True})

    return Starlette(routes=[Route("/ping", handler)])


def test_request_without_authorization_header_is_rejected():
    app = auth.protect(_dummy_app(), token="secret-token")
    client = TestClient(app)

    r = client.get("/ping")

    assert r.status_code == 401
    assert r.json() == {"error": "unauthorized"}


def test_request_with_wrong_token_is_rejected():
    app = auth.protect(_dummy_app(), token="secret-token")
    client = TestClient(app)

    r = client.get("/ping", headers={"Authorization": "Bearer wrong-token"})

    assert r.status_code == 401


def test_request_with_non_bearer_scheme_is_rejected():
    app = auth.protect(_dummy_app(), token="secret-token")
    client = TestClient(app)

    r = client.get("/ping", headers={"Authorization": "Basic secret-token"})

    assert r.status_code == 401


def test_request_with_correct_token_reaches_the_app():
    app = auth.protect(_dummy_app(), token="secret-token")
    client = TestClient(app)

    r = client.get("/ping", headers={"Authorization": "Bearer secret-token"})

    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_token_comparison_is_case_sensitive_and_exact():
    app = auth.protect(_dummy_app(), token="secret-token")
    client = TestClient(app)

    r = client.get("/ping", headers={"Authorization": "Bearer secret-tokenX"})
    assert r.status_code == 401

    r = client.get("/ping", headers={"Authorization": "Bearer Secret-Token"})
    assert r.status_code == 401


def test_protect_reads_token_from_environment_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(auth.TOKEN_ENV_VAR, "from-env")
    app = auth.protect(_dummy_app())
    client = TestClient(app)

    assert client.get("/ping").status_code == 401
    assert client.get("/ping", headers={"Authorization": "Bearer from-env"}).status_code == 200


def test_protect_raises_without_a_configured_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(auth.TOKEN_ENV_VAR, raising=False)

    with pytest.raises(auth.MissingTokenError, match=auth.TOKEN_ENV_VAR):
        auth.protect(_dummy_app())


def test_generate_token_is_long_and_unique():
    tokens = {auth.generate_token() for _ in range(20)}

    assert len(tokens) == 20  # no collisions across 20 draws
    assert all(len(t) >= 32 for t in tokens)


def test_cli_generate_prints_a_token(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("sys.argv", ["ados_mcp.auth", "generate"])

    exit_code = auth._cli()

    out = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert len(out) >= 32


def test_cli_without_generate_argument_prints_usage(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("sys.argv", ["ados_mcp.auth"])

    exit_code = auth._cli()

    assert exit_code == 2
    assert "usage" in capsys.readouterr().err
