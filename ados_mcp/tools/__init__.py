"""
ados_mcp/tools — ADOS-M4.2 write tools.

Each module below is a thin MCP wrapper around one already-shipped,
already-tested ``api/routers/ados_project.py`` endpoint — no new business
logic, and no direct import of ``brand`` or ``api.routers``
(docs/architecture/m4-claude-connector.md §3 rule 1;
``tests_mcp/test_boundaries.py`` enforces both by AST inspection).

Importing this package registers every ``@mcp.tool`` in it against the
shared ``mcp`` instance in ``ados_mcp.server``.
"""

from __future__ import annotations

from ados_mcp.tools import content, documents, generation, loop, projects, propagation  # noqa: F401
