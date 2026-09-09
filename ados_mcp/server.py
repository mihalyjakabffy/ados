"""
ados_mcp/server.py

ADOS-M4 entrypoint (docs/architecture/m4-claude-connector.md) — the MCP
server a Claude Code / Claude Desktop session, or a remote MCP client
such as claude.ai's custom connectors, adds as a connector.

**Transport defaults to stdio** (§9 decision 2) — the same trust
boundary as running any other local process. ADOS-M4.6 adds a remote
mode, selected explicitly via ``ADOS_MCP_TRANSPORT`` (never the
default), which binds an HTTP server and requires every request to
carry the bearer token ``ados_mcp.auth`` guards it with
(``ADOS_MCP_TOKEN`` — generate one with
``python -m ados_mcp.auth generate``). Streamable HTTP
(``ADOS_MCP_TRANSPORT=http``) is the current MCP spec's recommended
remote transport and this module's primary one; SSE
(``ADOS_MCP_TRANSPORT=sse``) is kept only for a client that has not
moved off the older transport — the design doc's original "HTTP+SSE"
phrasing conflated the two; see ados_mcp/README.md's deployment notes
for the correction and the reasoning.

Run directly:

    python -m ados_mcp.server                              # stdio (default)
    ADOS_MCP_TRANSPORT=http ADOS_MCP_TOKEN=... python -m ados_mcp.server

or point a Claude Code / Claude Desktop MCP config at this module — see
ados_mcp/README.md for the exact config block and the remote-deployment
notes (TLS, host binding, what the bearer token does and does not
protect).
"""

from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

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
        "render a saved Version. Editing the shared content pool or "
        "bumping a project's brand version does NOT automatically "
        "recompose documents that reference it — call "
        "propagate_content_change or propagate_brand_change explicitly "
        "afterward (ADOS-M4.3), and tell the user what it reports "
        "(which documents were recomposed, which were left alone, and "
        "any new findings) rather than assuming the change already "
        "reached every document on its own. "
        "The generation chain (ADOS-M4.4) is generate_semantic_intent -> "
        "generate_narrative / generate_design_intent -> generate_commands "
        "-> apply_commands: each stage's output is the next stage's input "
        "(generate_commands and apply_commands additionally need a "
        "content_model, from compose_document's own response). Every "
        "stage may call a real LLM on the ADOS server, or its "
        "deterministic rule-based fallback if no API key is configured "
        "there — only generate_semantic_intent's response names which "
        "one ran; say so honestly if asked, and treat every stage as "
        "potentially real latency and API cost, not a free local "
        "computation. apply_commands computes a result but saves "
        "nothing — pass its final_plan to save_version to keep it. "
        "The closed loop (start_loop/continue_loop/run_loop/approve_loop/"
        "stop_loop) DOES persist, and is gated by its own autonomy "
        "policy (default 'safe': only SAFE-labelled commands execute "
        "without approval) — never pass autonomy='full' unless the user "
        "explicitly asked for unattended execution, and read "
        "ados://projects/{project_id}/documents/{document_id}/loop "
        "before calling approve_loop so the approval is grounded in what "
        "the loop actually found. "
        "propose_brand (ADOS-M4.5) never saves anything — it is a candidate "
        "identity for the user to review. approve_brand is the one call "
        "that writes it, and approved_by MUST be a real person's name the "
        "user actually gave you — never your own name, never a "
        "placeholder; an approval you invented defeats the entire point of "
        "this gate. audit_brand checks an already-built package directory "
        "on the ADOS server's own filesystem against a brand — a separate "
        "question from whether the brand itself validates."
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


#: ADOS_MCP_TRANSPORT values -> the FastMCP ASGI app factory each one
#: serves. "http" is the friendly name for what the MCP spec calls
#: Streamable HTTP — the transport this module treats as primary.
_REMOTE_APP_FACTORIES = {"http": "streamable_http_app", "sse": "sse_app"}


def run_remote(transport: str) -> None:
    """Serve ``mcp`` over HTTP, behind the bearer-token guard
    (``ados_mcp.auth.protect``). Never called by ``main()`` unless
    ``ADOS_MCP_TRANSPORT`` explicitly asks for it — stdio stays the
    default every other entry point in this module takes."""
    import uvicorn

    from ados_mcp import auth

    host = os.environ.get("ADOS_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("ADOS_MCP_PORT", "8100"))

    if host not in ("127.0.0.1", "localhost", "::1"):
        # FastMCP auto-enables DNS-rebinding protection scoped to
        # loopback Host/Origin values the moment it sees a non-default
        # host at construction time — but `mcp` above was constructed
        # with no `host=`, so that protection is still loopback-scoped
        # even though we are about to bind elsewhere. A real remote
        # client's Host header will never match it, so every request
        # would be refused regardless of the bearer token being
        # correct. Disabling it here is a deliberate trade, not an
        # oversight: the bearer token is this transport's real
        # boundary, and DNS-rebinding protection specifically defends
        # a loopback-trusting server against a browser-based attack —
        # a threat model that doesn't apply once every request already
        # needs a token no browser page can know. See
        # ados_mcp/README.md's deployment notes for what this does and
        # does not defend against, and why TLS in front of this is not
        # optional.
        from mcp.server.transport_security import TransportSecuritySettings

        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )
        logger.warning(
            "binding to %s (not loopback) — make sure TLS terminates in front "
            "of this process (a reverse proxy or tunnel); never serve plaintext "
            "%s bearer-token traffic directly to the open internet",
            host, auth.TOKEN_ENV_VAR,
        )

    factory_name = _REMOTE_APP_FACTORIES[transport]
    app = auth.protect(getattr(mcp, factory_name)())
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    transport = os.environ.get("ADOS_MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport in _REMOTE_APP_FACTORIES:
        run_remote(transport)
    else:
        raise SystemExit(
            f"unknown ADOS_MCP_TRANSPORT {transport!r} — expected 'stdio', 'http', or 'sse'"
        )


if __name__ == "__main__":
    main()
