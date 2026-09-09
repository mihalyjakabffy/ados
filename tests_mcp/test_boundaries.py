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


def test_no_write_verbs_in_client_module() -> None:
    """ADOS-M4.1 is read-only by design (design doc §10) — ``AdosClient``
    exposes only GET wrappers. This fails loudly the moment a POST/PUT/
    PATCH/DELETE helper is added, which should happen deliberately in
    M4.2, with its own tests and its own AST boundary update — not as a
    side effect of an unrelated change."""
    client_source = (_ADOS_MCP_DIR / "client.py").read_text(encoding="utf-8")
    tree = ast.parse(client_source, filename="client.py")
    method_names = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    banned = {"post", "put", "patch", "delete"} & method_names
    assert not banned, f"ados_mcp/client.py calls write verb(s) {banned} — M4.1 must stay read-only"
