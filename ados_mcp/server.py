"""
ados_mcp/server.py

ADOS-M4 entrypoint (docs/architecture/m4-claude-connector.md) — the MCP
server a Claude Code / Claude Desktop session adds as a connector. Ships
stdio-only (§9 decision 2 of the design doc); the remote HTTP+SSE
transport for a claude.ai custom connector is deferred to M4.6, once an
auth layer exists — ADOS itself has none today, and exposing this server
over the network before then would expose every project it can read and
write to anyone who can reach the port.

Run directly:

    python -m ados_mcp.server

or point a Claude Code / Claude Desktop MCP config at this module — see
ados_mcp/README.md for the exact config block.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="ados",
    instructions=(
        "ADOS is an architectural practice's deterministic, versioned system "
        "of record: projects, brand identity, a shared pool of project facts, "
        "and the composed documents built from them. Before answering a "
        "question about a specific project, read "
        "ados://projects/{project_id}/documents/{document_id}/design-state — "
        "its DesignState is the single source of truth, assembled fresh from "
        "real persisted state on every read, never a snapshot from an earlier "
        "turn. ados://rules holds the ADOS 1.0 specification's own rule "
        "registry (ADOS-x.y.zzz ids) — cite a real rule from it rather than "
        "inventing a justification for a formatting or process question. "
        "Tools exist (ADOS-M4.2) to create and modify projects, documents "
        "and content, and to compose/save/export a document — every one is a "
        "thin wrapper around an already-validated ADOS API endpoint, so a "
        "malformed or unsafe request is refused by ADOS itself, not silently "
        "accepted; relay a refusal's real reason rather than retrying blindly. "
        "compose_document does not persist anything by itself — call "
        "save_version to keep a composed result, then export_document to "
        "render a saved Version. Editing the shared content pool does NOT "
        "yet recompose documents that selected the changed item (that "
        "fan-out is ADOS-M4.3, not built yet) — call compose_document again "
        "on each document that should pick up the change, and say so "
        "explicitly rather than implying it happened automatically."
    ),
)

# Registers every @mcp.resource / @mcp.tool in these modules against the
# `mcp` instance above — the only reason these imports exist. Placed
# after `mcp` is defined, since both modules import it back
# (`from ados_mcp.server import mcp`); Python resolves this fine because
# the name already exists on this (partially-initialised) module by the
# time each import runs its own.
from ados_mcp import resources  # noqa: E402,F401
from ados_mcp import tools  # noqa: E402,F401


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
