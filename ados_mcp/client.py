"""
ados_mcp/client.py

The one shared, low-level path every resource and tool in this package
uses to reach ADOS — the ``ados_mcp`` analogue of
``brand.llm.providers.claude_provider.get_client()``: a single
construction point, so no resource or tool module opens its own,
differently configured connection (``tests_mcp/test_boundaries.py``
checks this by AST inspection the same way that module's own docstring
checks "do not create a second Claude client").

ADOS-M4.1/M4.2 talks to two independently-deployable, already-shipped
backends, never to ``brand/`` or ``api/routers/`` directly:

    ADOS_API_BASE_URL      api/main.py, mounted at /api/v2 — projects,
                            brand, content, documents, compose, versions,
                            export. Read *and* write, from M4.2.
    ADOS_SERVICE_BASE_URL  ados-service/main.py — the ADOS 1.0
                            specification's own 476-rule registry.
                            Read-only: it has no write endpoint to wrap.

Both default to the ports each service's own README already documents
(8000 and 8010) so this module needs no configuration for the common case
of running everything on one machine during development.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

_DEFAULT_API_BASE = "http://localhost:8000/api/v2"
_DEFAULT_SERVICE_BASE = "http://localhost:8010"

_TIMEOUT_SECONDS = 30.0


class AdosConnectionError(RuntimeError):
    """A configured ADOS backend could not be reached, or answered with an
    error. The message is written for the chat session relaying it to a
    person, not for a developer reading a stack trace — it names which
    backend, how it is configured, how to start it and, for a
    request-level error, the structured detail the API itself returned
    (ADOS's own routers already reply with a real ``{"error": ..., ...}``
    body, e.g. ``invalid_content_item`` — that detail is exactly what a
    chat session needs to explain the refusal, not a truncated string)."""


def _base_url(env_var: str, default: str) -> str:
    return os.environ.get(env_var, default).rstrip("/")


class AdosClient:
    """A thin async JSON HTTP wrapper around ADOS's own, already-tested
    endpoints — GET for reads (M4.1), POST/PATCH/PUT/DELETE for the
    ADOS-M4.2 write tools. Every method here maps 1:1 onto a real
    ``api/routers/`` endpoint; this class adds no business logic of its
    own (docs/architecture/m4-claude-connector.md §3 rule 1).

    ``transport`` is an injection seam for tests (``httpx.MockTransport``)
    — production code never passes it, so the real network path
    (``transport=None``) is exactly what ``httpx`` would otherwise do on
    its own.
    """

    def __init__(self, *, transport: Optional[httpx.BaseTransport] = None) -> None:
        self._api_base = _base_url("ADOS_API_BASE_URL", _DEFAULT_API_BASE)
        self._service_base = _base_url("ADOS_SERVICE_BASE_URL", _DEFAULT_SERVICE_BASE)
        self._transport = transport

    # -- reads ----------------------------------------------------------

    async def get_api(self, path: str, *, params: Optional[dict[str, Any]] = None) -> dict:
        """GET against ``api/main.py``'s ``/api/v2`` surface."""
        return await self._request("GET", self._api_base, path, params=params, env_var="ADOS_API_BASE_URL")

    async def get_service(self, path: str, *, params: Optional[dict[str, Any]] = None) -> dict:
        """GET against ``ados-service/main.py``'s rule-registry surface."""
        return await self._request(
            "GET", self._service_base, path, params=params, env_var="ADOS_SERVICE_BASE_URL"
        )

    # -- writes (ADOS-M4.2) — api/main.py only; ados-service has none ---

    async def post_api(self, path: str, *, json: Optional[dict[str, Any]] = None) -> dict:
        return await self._request("POST", self._api_base, path, json=json, env_var="ADOS_API_BASE_URL")

    async def patch_api(self, path: str, *, json: Optional[dict[str, Any]] = None) -> dict:
        return await self._request("PATCH", self._api_base, path, json=json, env_var="ADOS_API_BASE_URL")

    async def put_api(self, path: str, *, json: Optional[dict[str, Any]] = None) -> dict:
        return await self._request("PUT", self._api_base, path, json=json, env_var="ADOS_API_BASE_URL")

    async def delete_api(self, path: str) -> dict:
        return await self._request("DELETE", self._api_base, path, env_var="ADOS_API_BASE_URL")

    # -- shared plumbing --------------------------------------------------

    _RUN_HINTS = {
        "ADOS_API_BASE_URL": "api/main.py (`uvicorn api.main:app --port 8000`, from the repo root)",
        "ADOS_SERVICE_BASE_URL": "ados-service/main.py (`uvicorn main:app --port 8010`, from ados-service/)",
    }

    async def _request(
        self,
        method: str,
        base: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        env_var: str,
    ) -> dict:
        url = f"{base}{path}"
        run_hint = self._RUN_HINTS[env_var]
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, transport=self._transport) as client:
                response = await client.request(method, url, params=params, json=json)
        except httpx.ConnectError as exc:
            raise AdosConnectionError(
                f"could not reach {url} — is {run_hint} running? "
                f"(override the address with {env_var})"
            ) from exc
        if response.status_code == 404:
            raise AdosConnectionError(f"not found: {url}")
        if response.is_error:
            try:
                detail: Any = response.json()
            except ValueError:
                detail = response.text[:500]
            raise AdosConnectionError(f"{method} {url} returned HTTP {response.status_code}: {detail}")
        if not response.content:
            return {}
        return response.json()


_client: Optional[AdosClient] = None


def get_client() -> AdosClient:
    """The shared, lazily-constructed :class:`AdosClient` every resource
    and tool calls through. A fresh instance re-reads
    ``ADOS_API_BASE_URL`` / ``ADOS_SERVICE_BASE_URL`` from the
    environment, so tests that need a different configuration construct
    ``AdosClient`` directly rather than going through this cache."""
    global _client
    if _client is None:
        _client = AdosClient()
    return _client
