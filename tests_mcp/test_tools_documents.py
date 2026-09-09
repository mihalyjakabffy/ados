"""
tests_mcp/test_tools_documents.py

ados_mcp.tools.documents against a mocked HTTP transport.
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
    monkeypatch.setattr(tools.documents, "get_client", lambda: fake)


def _body(request: httpx.Request) -> dict:
    return json.loads(request.content)


def test_create_document_with_a_type(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(201, json={"id": "d1", "document_type_id": "investor-deck"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(
        tools.documents.create_document(
            "p1", "Series A deck", document_type_id="investor-deck", metadata={"audience": "investors"}
        )
    )

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents"
    assert seen["body"] == {
        "name": "Series A deck",
        "document_type_id": "investor-deck",
        "metadata": {"audience": "investors"},
    }
    assert result["document_type_id"] == "investor-deck"


def test_create_document_untyped_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _body(request)
        return httpx.Response(201, json={"id": "d1"})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.documents.create_document("p1", "Notes"))

    assert seen["body"] == {"name": "Notes", "document_type_id": "", "metadata": {}}
    assert "direction_id" not in seen["body"]


def test_compose_document(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(200, json={"plan": {}, "evaluation": {}, "requirement_findings": []})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.documents.compose_document("p1", "d1"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/compose"
    assert result["requirement_findings"] == []


def test_compose_document_surfaces_missing_brand(monkeypatch: pytest.MonkeyPatch) -> None:
    from ados_mcp.client import AdosConnectionError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": {"error": "no_brand_attached"}})

    _patch_client(monkeypatch, handler)

    with pytest.raises(AdosConnectionError, match="no_brand_attached"):
        asyncio.run(tools.documents.compose_document("p1", "d1"))


def test_save_version_with_explicit_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(201, json={"number": 1, "label": "first draft"})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(
        tools.documents.save_version("p1", "d1", label="first draft", plan={"pages": []})
    )

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/versions"
    assert seen["body"] == {"document_id": "d1", "label": "first draft", "plan": {"pages": []}}
    assert result["number"] == 1


def test_save_version_without_plan_omits_it(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _body(request)
        return httpx.Response(201, json={"number": 2})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.documents.save_version("p1", "d1"))

    assert seen["body"] == {"document_id": "d1", "label": ""}
    assert "plan" not in seen["body"]


def test_export_document_defaults_to_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = _body(request)
        return httpx.Response(201, json={"export": {"status": "completed"}, "findings": []})

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.documents.export_document("p1", "d1"))

    assert seen["method"] == "POST"
    assert seen["path"] == "/api/v2/ados-projects/p1/documents/d1/export"
    assert seen["body"] == {"format": "pdf"}
    assert result["export"]["status"] == "completed"


def test_export_document_html_with_pinned_version(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = _body(request)
        return httpx.Response(201, json={"export": {"format": "html"}, "findings": []})

    _patch_client(monkeypatch, handler)

    asyncio.run(tools.documents.export_document("p1", "d1", version_number=3, format="html"))

    assert seen["body"] == {"format": "html", "version_number": 3}


def test_export_document_blocked_still_returns_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={
                "export": {"status": "blocked"},
                "findings": [{"severity": "ERROR", "message": "page overflow"}],
            },
        )

    _patch_client(monkeypatch, handler)

    result = asyncio.run(tools.documents.export_document("p1", "d1"))

    assert result["export"]["status"] == "blocked"
    assert result["findings"][0]["severity"] == "ERROR"
