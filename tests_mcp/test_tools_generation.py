"""
tests_mcp/test_tools_generation.py

ados_mcp.tools.generation against a mocked HTTP transport.
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
    monkeypatch.setattr(tools.generation, "get_client", lambda: fake)


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content) if request.content else {}


def test_generate_semantic_intent_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"intent": {}, "validation": {}, "provider": "rule_based"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.generation.generate_semantic_intent("Make me an investor deck"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/intent/semantic"
    assert seen["body"] == {"request": "Make me an investor deck"}
    assert result["provider"] == "rule_based"


def test_generate_semantic_intent_with_context(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _body(request)
        return httpx.Response(200, json={})

    _patch_client(monkeypatch, handler)

    asyncio.run(
        tools.generation.generate_semantic_intent(
            "Tighten the density", project_id="p1", document_id="d1", version=2,
            conversation=[{"role": "user", "text": "hi"}],
        )
    )

    assert seen["body"] == {
        "request": "Tighten the density",
        "project_id": "p1",
        "document_id": "d1",
        "version": 2,
        "conversation": [{"role": "user", "text": "hi"}],
    }


def test_generate_narrative(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"narrative_plan": {}, "request_id": "r1"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.generation.generate_narrative("p1", {"style": "quiet"}, document_id="d1"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/narrative/plan"
    assert seen["body"] == {
        "semantic_intent": {"style": "quiet"},
        "document_type_id": "",
        "compression": "medium",
        "document_id": "d1",
    }
    assert result["request_id"] == "r1"


def test_generate_design_intent_passes_corrections_and_raw_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"design_intent": {}})

    _patch_client(monkeypatch, handler)

    asyncio.run(
        tools.generation.generate_design_intent(
            "p1", {}, document_id="d1", compression="brief",
            user_corrections=[{"key": "client", "value": "Acme"}],
            raw_documents=[{"text": "brief text"}],
        )
    )

    assert seen["path"] == "/api/v2/ados-projects/p1/design/intent"
    assert seen["body"]["compression"] == "brief"
    assert seen["body"]["user_corrections"] == [{"key": "client", "value": "Acme"}]
    assert seen["body"]["raw_documents"] == [{"text": "brief text"}]


def test_generate_commands_includes_content_model(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"command_plan": {"commands": []}})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(
        tools.generation.generate_commands("p1", {}, {"blocks": []}, document_id="d1")
    )

    assert seen["path"] == "/api/v2/ados-projects/p1/commands/generate"
    assert seen["body"]["content_model"] == {"blocks": []}
    assert result["command_plan"] == {"commands": []}


def test_apply_commands_with_direction_id(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(200, json={"final_plan": {}, "steps": []})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(
        tools.generation.apply_commands(
            "p1", {"commands": []}, {"blocks": []}, base_direction_id="editorial-quiet",
        )
    )

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/commands/apply"
    assert seen["body"] == {
        "command_plan": {"commands": []},
        "content_model": {"blocks": []},
        "page_format_name": "A4",
        "base_direction_id": "editorial-quiet",
    }
    assert result["final_plan"] == {}


def test_apply_commands_surfaces_missing_base_direction(monkeypatch: pytest.MonkeyPatch) -> None:
    from ados_mcp.client import AdosConnectionError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": {"error": "invalid_base_direction"}})

    _patch_client(monkeypatch, handler)

    with pytest.raises(AdosConnectionError, match="invalid_base_direction"):
        asyncio.run(tools.generation.apply_commands("p1", {"commands": []}, {"blocks": []}))
