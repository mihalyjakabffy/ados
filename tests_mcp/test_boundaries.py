"""
tests_mcp/test_boundaries.py

ADOS-M4's own boundary (docs/architecture/m4-claude-connector.md §3 rule
1): ``ados_mcp`` is a client of ``api/main.py`` and ``ados-service/main.py``
over HTTP, never a second entry point into ``brand/`` or ``api/routers/``.
Checked by AST inspection from the very first resource this package
ships — the same technique ``tests_brand/test_loop_boundaries.py`` uses to
keep ``brand/llm/loop/`` from drifting into a second execution path for
``compose()``/``apply_intent()``. A rule this cheap to check should never
regress silently.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_ADOS_MCP_DIR = Path(__file__).resolve().parent.parent / "ados_mcp"
_BANNED_ROOTS = {"brand", "api"}


def _module_files() -> list[Path]:
    return sorted(_ADOS_MCP_DIR.rglob("*.py"))


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:  # ignore relative (`from . import x`)
                roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize(
    "path", _module_files(), ids=lambda p: str(p.relative_to(_ADOS_MCP_DIR.parent))
)
def test_no_direct_import_of_brand_or_api(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hit = _imported_roots(tree) & _BANNED_ROOTS
    assert not hit, (
        f"{path}: imports {sorted(hit)} directly — ados_mcp must reach ADOS "
        "only over HTTP via ados_mcp.client.AdosClient, never by importing "
        "brand/ or api/ in-process (docs/architecture/m4-claude-connector.md §3)"
    )


def test_only_client_module_constructs_an_httpx_client() -> None:
    """Every resource/tool reaches the network through
    ``ados_mcp.client``'s one shared construction point — mirrors
    ``brand.llm.providers.claude_provider``'s own "do not create a second
    client" rule — so a future tool cannot open a second, unconfigured
    connection that ignores ``ADOS_API_BASE_URL``/``ADOS_SERVICE_BASE_URL``."""
    offenders = []
    for path in _module_files():
        if path.name == "client.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {"AsyncClient", "Client"}:
                offenders.append(str(path.relative_to(_ADOS_MCP_DIR.parent)))
    assert not offenders, f"httpx client constructed outside ados_mcp/client.py: {offenders}"


def test_ados_service_backend_has_no_write_methods() -> None:
    """ados-service (the ADOS 1.0 rule registry, docs/ados/machine/) is
    read-only by design — it has no write endpoint to wrap, and never
    should: it documents the specification, not project state. ADOS-M4.2
    added post_api/patch_api/put_api/delete_api for api/main.py; this
    fails the moment a *_service write method is added by analogy,
    which would need its own design discussion, not a copy-paste of the
    api write helpers (docs/architecture/m4-claude-connector.md §3)."""
    from ados_mcp.client import AdosClient

    service_write_methods = {
        f"{verb}_service" for verb in ("post", "put", "patch", "delete")
    } & set(dir(AdosClient))
    assert not service_write_methods, (
        f"AdosClient defines write method(s) against ados-service: {service_write_methods}"
    )


def test_every_tool_module_calls_get_client_for_its_writes() -> None:
    """Every write tool must go through ``ados_mcp.client.get_client()`` —
    the same single-construction-point rule
    ``test_only_client_module_constructs_an_httpx_client`` enforces at
    the transport level, checked here at the call-site level: a
    ``tools/*.py`` module that never calls ``get_client()`` is either
    dead code or a tool that forgot to reach ADOS at all."""
    tools_dir = _ADOS_MCP_DIR / "tools"
    for path in sorted(tools_dir.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "get_client" in calls, f"{path}: no tool in this module calls get_client()"
