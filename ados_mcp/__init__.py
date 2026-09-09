"""
ados_mcp — the ADOS Claude connector (ADOS-M4).

Design: docs/architecture/m4-claude-connector.md.

M4.1 (this phase): read-only MCP resources over stdio — DesignState,
projects, the shared content pool, brand identity, and the ADOS 1.0 rule
registry. No tool can mutate anything yet; see server.py's own
``instructions`` string, which states this to the connecting model too.

Every module here reaches ADOS only over HTTP, through ``ados_mcp.client``
— never by importing ``brand`` or ``api.routers`` in-process
(``tests_mcp/test_boundaries.py`` enforces this by AST inspection). That
boundary is the whole point of this package: it is a new *client* of
``api/main.py`` and ``ados-service/main.py``, exactly the relationship
``ados-web`` already has, not a second way into the domain.
"""

from __future__ import annotations
