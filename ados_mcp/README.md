# ados_mcp — the ADOS Claude connector

ADOS-M4.1. Design: [`docs/architecture/m4-claude-connector.md`](../docs/architecture/m4-claude-connector.md).

An MCP server exposing ADOS's own `DesignState`, projects, shared content
pool, brand identity and the ADOS 1.0 rule registry as **read-only
resources** to any MCP client — Claude Code, Claude Desktop, or a custom
client. It is a new *client* of `api/main.py` and `ados-service/main.py`,
talking to both over plain HTTP GET, exactly the relationship `ados-web`
already has to `api/main.py`. It does not import `brand/` or
`api/routers/`, and it has no tool that changes anything yet — see
`docs/architecture/m4-claude-connector.md` §3 for why, and the phased
rollout (§10) for what M4.2 onward adds.

## Install

```bash
pip install -r ados_mcp/requirements.txt
```

(`mcp` is pinned below 2.x — see the comment in `ados_mcp/requirements.txt`.)

## Run standalone

```bash
# in one terminal: the backends this server reads from
uvicorn api.main:app --reload --port 8000
cd ados-service && uvicorn main:app --reload --port 8010

# in another: the MCP server itself, over stdio
python -m ados_mcp.server
```

A stdio MCP server has no independent "running" state to observe — it
speaks the MCP protocol over its own stdin/stdout, so it is normally
launched by an MCP client (below), not run standalone except to smoke-test
that it starts without error.

## Add to Claude Code

```bash
claude mcp add ados -- python -m ados_mcp.server
```

(run from the repository root, with `ados_mcp`'s dependencies installed in
the same Python environment `python` resolves to).

## Add to Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ados": {
      "command": "python",
      "args": ["-m", "ados_mcp.server"],
      "cwd": "/absolute/path/to/this/repository"
    }
  }
}
```

## Resources

| URI | Backed by | Content |
|---|---|---|
| `ados://projects` | `GET /api/v2/ados-projects` | every project, most recently updated first |
| `ados://projects/{project_id}` | `GET /api/v2/ados-projects/{project_id}` | one project's facts |
| `ados://projects/{project_id}/content` | `GET /api/v2/ados-projects/{project_id}/content` | the shared `ContentItem` pool |
| `ados://projects/{project_id}/documents/{document_id}/design-state` | `GET .../documents/{document_id}/design-state` | the deterministic single source of truth for one document |
| `ados://brands/{brand_id}` | `GET /api/v2/brands/{brand_id}` + `.../tokens` | identity + resolved design tokens with provenance |
| `ados://rules` | `ados-service`'s `GET /api/rules` | the ADOS 1.0 476-rule registry |

## Environment

| Variable | Default | Description |
|---|---|---|
| `ADOS_API_BASE_URL` | `http://localhost:8000/api/v2` | where `api/main.py` is reachable |
| `ADOS_SERVICE_BASE_URL` | `http://localhost:8010` | where `ados-service/main.py` is reachable |

## What this is not (yet)

Read-only, stdio-only, single-user, no auth — the same trust boundary as
running `uvicorn` locally already has. No tool creates, edits, composes,
exports, or propagates anything; that starts at M4.2. A remote (HTTP+SSE)
transport for a claude.ai custom connector is M4.6, and needs an auth
layer ADOS does not have today. See the design doc's §9–§12 for the
reasoning and the open decisions.

## Tests

```bash
python -m pytest tests_mcp -q
```

`tests_mcp/test_boundaries.py` is an AST check, the same technique
`tests_brand/test_loop_boundaries.py` uses for `brand/llm/loop/`: no
module under `ados_mcp/` may import `brand` or `api` directly, and only
`ados_mcp/client.py` may construct an `httpx` client. `tests_mcp/test_resources.py`
exercises every resource function against a mocked HTTP transport — no
live server required.
