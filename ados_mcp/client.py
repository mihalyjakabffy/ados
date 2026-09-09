"""
ados_mcp/client.py

The one shared, low-level path every resource and tool in this package
uses to reach ADOS — the ``ados_mcp`` analogue of
``brand.llm.providers.claude_provider.get_client()``: a single
construction point, so no resource module opens its own, differently
configured connection (``tests_mcp/test_boundaries.py`` checks this by
AST inspection the same way that module's own docstring checks "do not
create a second Claude client").

ADOS-M4.1 talks to two independently-deployable, already-shipped
backends, both read-only here — never to ``brand/`` or ``api/routers/``
directly:

    ADOS_API_BASE_URL      api/main.py, mounted at /api/v2 — projects,
                            brand, shared content, DesignState.
    ADOS_SERVICE_BASE_URL  ados-service/main.py — the ADOS 1.0
                            specification's own 476-rule registry.

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
    backend, how it is configured, and how to start it."""


def _base_url(env_var: str, default: str) -> str:
    return os.environ.get(env_var, default).rstrip("/")


class AdosClient:
    """A thin async JSON-GET wrapper. No POST/PUT/DELETE yet — ADOS-M4.1
    is read-only by design (docs/architecture/m4-claude-connector.md
    §10); write tools are M4.2 and later, once the AST boundary test in
    §3 has something to guard against.

    ``transport`` is an injection seam for tests
    (``httpx.MockTransport``) — production code never passes it, so the
    real network path (``transport=None``) is exactly what ``httpx``
    would otherwise do on its own.
    """

    def __init__(self, *, transport: Optional[httpx.BaseTransport] = None) -> None:
        self._api_base = _base_url("ADOS_API_BASE_URL", _DEFAULT_API_BASE)
        self._service_base = _base_url("ADOS_SERVICE_BASE_URL", _DEFAULT_SERVICE_BASE)
        self._transport = transport

    async def get_api(self, path: str, *, params: Optional[dict[str, Any]] = None) -> dict:
        """GET against ``api/main.py``'s ``/api/v2`` surface."""
        return await self._get(
            self._api_base,
            path,
            params,
            env_var="ADOS_API_BASE_URL",
            run_hint="api/main.py (`uvicorn api.main:app --port 8000`, from the repo root)",
        )

    async def get_service(self, path: str, *, params: Optional[dict[str, Any]] = None) -> dict:
        """GET against ``ados-service/main.py``'s rule-registry surface."""
        return await self._get(
            self._service_base,
            path,
            params,
            env_var="ADOS_SERVICE_BASE_URL",
            run_hint="ados-service/main.py (`uvicorn main:app --port 8010`, from ados-service/)",
        )

    async def _get(
        self,
        base: str,
        path: str,
        params: Optional[dict[str, Any]],
        *,
        env_var: str,
        run_hint: str,
    ) -> dict:
        url = f"{base}{path}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, transport=self._transport) as client:
                response = await client.get(url, params=params)
        except httpx.ConnectError as exc:
            raise AdosConnectionError(
                f"could not reach {url} — is {run_hint} running? "
                f"(override the address with {env_var})"
            ) from exc
        if response.status_code == 404:
            raise AdosConnectionError(f"not found: {url}")
        if response.is_error:
            raise AdosConnectionError(
                f"{url} returned HTTP {response.status_code}: {response.text[:500]}"
            )
        return response.json()


_client: Optional[AdosClient] = None


def get_client() -> AdosClient:
    """The shared, lazily-constructed :class:`AdosClient` every resource
    calls through. A fresh instance re-reads ``ADOS_API_BASE_URL`` /
    ``ADOS_SERVICE_BASE_URL`` from the environment, so tests that need a
    different configuration construct ``AdosClient`` directly rather than
    going through this cache."""
    global _client
    if _client is None:
        _client = AdosClient()
    return _client
