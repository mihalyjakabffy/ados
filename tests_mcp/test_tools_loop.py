"""
tests_mcp/test_tools_loop.py

ados_mcp.tools.loop against a mocked HTTP transport.
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
    monkeypatch.setattr(tools.loop, "get_client", lambda: fake)


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content) if request.content else {}


def test_start_loop_default_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"status": "COMPLETED"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.loop.start_loop("p1", "d1", {"style": "quiet"}))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/loop/start"
    assert seen["body"] == {
        "semantic_intent": {"style": "quiet"},
        "document_type_id": "",
        "compression": "medium",
        "policy": {
            "max_iterations": 5,
            "autonomy": "safe",
            "max_llm_calls": 10,
            "allow_llm_recommendation": True,
            "max_repeated_recommendation_attempts": 2,
        },
        "dry_run": False,
    }
    assert result["status"] == "COMPLETED"


def test_start_loop_dry_run_and_custom_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _body(request)
        return httpx.Response(200, json={})

    _patch_client(monkeypatch, handler)

    asyncio.run(
        tools.loop.start_loop(
            "p1", "d1", {}, autonomy="full", max_iterations=1, dry_run=True,
        )
    )

    assert seen["body"]["policy"]["autonomy"] == "full"
    assert seen["body"]["policy"]["max_iterations"] == 1
    assert seen["body"]["dry_run"] is True


def test_continue_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(200, json={"status": "COMPLETED"})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.loop.continue_loop("p1", "d1"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/loop/continue"


def test_continue_loop_surfaces_not_continuable(monkeypatch: pytest.MonkeyPatch) -> None:
    from ados_mcp.client import AdosConnectionError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": {"error": "loop_not_continuable"}})

    _patch_client(monkeypatch, handler)

    with pytest.raises(AdosConnectionError, match="loop_not_continuable"):
        asyncio.run(tools.loop.continue_loop("p1", "d1"))


def test_run_loop_has_no_dry_run_field(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"iterations": [], "final_status": "COMPLETED", "total_llm_calls": 0})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.loop.run_loop("p1", "d1", {}))

    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/loop/run"
    assert "dry_run" not in seen["body"]
    assert result["total_llm_calls"] == 0


def test_approve_loop_with_specific_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"status": "COMPLETED"})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.loop.approve_loop("p1", "d1", command_ids=["c1", "c2"]))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/loop/approve"
    assert seen["body"] == {"command_ids": ["c1", "c2"]}


def test_approve_loop_without_command_ids_sends_empty_body(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _body(request)
        return httpx.Response(200, json={})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.loop.approve_loop("p1", "d1"))

    assert seen["body"] == {}


def test_stop_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(200, json={"status": "STOPPED"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.loop.stop_loop("p1", "d1"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/loop/stop"
    assert result["status"] == "STOPPED"
