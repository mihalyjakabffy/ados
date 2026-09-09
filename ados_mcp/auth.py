"""
ados_mcp/auth.py

ADOS-M4.6 — the bearer-token guard for the remote (HTTP) transport.

**Not OAuth, deliberately.** ADOS is a single-practice tool, not a
multi-tenant service: there is no user directory, no client to register,
no consent screen to build. The MCP Python SDK's own auth mechanism
(``TokenVerifier`` + ``AuthSettings``) is shaped for a real OAuth
resource-server / authorization-server pair (it requires an
``issuer_url``, advertises OAuth discovery metadata, expects a token to
have come from somewhere). Half-configuring that machinery around a
single shared secret would either fake OAuth metadata that doesn't back
a real authorization flow — actively misleading to a client that tries
to follow it — or ship it half-built, exactly the "designed on its own,
never retrofitted under schedule pressure" failure mode
docs/architecture/m4-claude-connector.md §9 decision 2 named for this
phase. So this module is plain ASGI middleware wrapping FastMCP's own
``streamable_http_app()`` / ``sse_app()`` (both plain Starlette apps,
independent of the SDK's OAuth path) with one check: does the
``Authorization`` header carry the one configured bearer token. Fully
owned, five lines long, and easy to verify correct — the more honest
boundary for what this actually is.

**The token is a master key, not a scoped credential.** Every
authenticated caller gets the exact same full read/write access to
every project this ADOS instance can reach — there is no per-project or
per-user scoping anywhere in this milestone's tool surface. Generate one
with ``python -m ados_mcp.auth generate``, store it like any other
production secret, and never run this transport without TLS in front of
it (``ados_mcp/README.md``'s deployment notes) — a bearer token sent over
plaintext HTTP is a token handed to anyone on the network path.
"""

from __future__ import annotations

import hmac
import os
import secrets
import sys

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

TOKEN_ENV_VAR = "ADOS_MCP_TOKEN"


class MissingTokenError(RuntimeError):
    """Raised at process startup, not at request time — refusing to bind
    a remote transport with no configured secret is a fail-closed
    default, never a silently-open server."""


def _configured_token() -> str:
    token = os.environ.get(TOKEN_ENV_VAR, "")
    if not token:
        raise MissingTokenError(
            f"{TOKEN_ENV_VAR} is not set. Generate one with "
            "`python -m ados_mcp.auth generate` and set it in the environment "
            "both this server and every client read from — a remote transport "
            "never starts without a configured token."
        )
    return token


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Rejects any request whose ``Authorization: Bearer <token>`` header
    does not match the configured secret, before it reaches the wrapped
    app at all. Uses ``hmac.compare_digest`` — a timing-observable plain
    string compare would leak the token one correct prefix at a time to
    an attacker who can measure response latency."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next):
        scheme, _, presented = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(presented, self._token):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def protect(app: Starlette, *, token: str | None = None) -> Starlette:
    """Wrap an MCP ASGI app (``FastMCP.streamable_http_app()`` /
    ``.sse_app()``) with the bearer-token guard. ``token`` defaults to
    :data:`TOKEN_ENV_VAR` from the environment; raises
    :class:`MissingTokenError` if neither is given — called once, at
    process startup, never per request, so a missing token fails loudly
    before the server ever binds a port."""
    app.add_middleware(BearerTokenMiddleware, token=token or _configured_token())
    return app


def generate_token() -> str:
    """A fresh, cryptographically random token — 256 bits, URL-safe."""
    return secrets.token_urlsafe(32)


def _cli() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "generate":
        print("usage: python -m ados_mcp.auth generate", file=sys.stderr)
        return 2
    print(generate_token())
    print(
        f"\nSet this as {TOKEN_ENV_VAR} in both the server's own environment "
        "and whatever client config supplies it as a Bearer token. Treat it "
        "like any other production secret — it grants full read/write access "
        "to every project this ADOS instance can reach.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
