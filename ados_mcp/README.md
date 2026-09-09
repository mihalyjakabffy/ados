# ados_mcp — the ADOS Claude connector

ADOS-M4.1/M4.2. Design: [`docs/architecture/m4-claude-connector.md`](../docs/architecture/m4-claude-connector.md).

An MCP server exposing ADOS's own `DesignState`, projects, shared content
pool, brand identity and the ADOS 1.0 rule registry as resources, plus
tools to create and edit projects/documents/content and to
compose/save/export a document, to any MCP client — Claude Code, Claude
Desktop, or a custom client. It is a new *client* of `api/main.py` and
`ados-service/main.py`, talking to both over plain HTTP, exactly the
relationship `ados-web` already has to `api/main.py`. It does not import
`brand/` or `api/routers/` — every tool is a thin wrapper around one
already-validated ADOS endpoint, so a malformed or unsafe request is
refused by ADOS itself, never silently accepted (design doc §3). See the
phased rollout (§10) for what M4.3 onward still adds — propagation
("edit this fact, recompose everywhere it's used"), the generative and
closed-loop tools, and the remote transport.

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

## Tools

Every tool is a thin wrapper around one endpoint in
`api/routers/ados_project.py`; none of them contain business logic of
their own, and none of them recompose anything beyond the one document
named in the call.

| Tool | Wraps | Notes |
|---|---|---|
| `create_project(name, description="")` | `POST /ados-projects` | |
| `update_project_data(project_id, name?, description?, project_data?)` | `PATCH /ados-projects/{id}` | `project_data` is merged, not replaced |
| `attach_brand(project_id, brand_id, brand_version?)` | `PUT /ados-projects/{id}/brand` | required before compose/export will work |
| `create_document(project_id, name, document_type_id="", direction_id?, metadata?)` | `POST /ados-projects/{id}/documents` | see `document-types` for valid ids |
| `add_document_content(project_id, document_id, kind, ...)` | `POST .../documents/{id}/content` | `kind` is `text`/`fact`/`metric`/`image` |
| `remove_document_content(project_id, document_id, item_id)` | `DELETE .../documents/{id}/content/{item_id}` | |
| `add_shared_content(project_id, kind, ...)` | `POST .../content` | the project-level shared pool |
| `remove_shared_content(project_id, item_id)` | `DELETE .../content/{item_id}` | |
| `select_content_for_document(project_id, document_id, content_item_ids)` | `PUT .../content-selection` | replaces the whole selection |
| `compose_document(project_id, document_id)` | `POST .../documents/{id}/compose` | does not persist — call `save_version` to keep it |
| `save_version(project_id, document_id, label="", plan?)` | `POST .../versions` | immutable once saved |
| `export_document(project_id, document_id, version_number?, format="pdf")` | `POST .../documents/{id}/export` | `format` is `pdf` or `html` |

There is no `update_shared_content` yet — `api/routers/ados_project.py`
has no endpoint for it. That lands in M4.3 together with
`propagate_content_change`, the actual "edit this fact, recompose every
document that uses it" mechanism (design doc §6, §9). Until then, editing
a shared item means remove + re-add (a new id — every document's
`content_selection` referencing the old one goes stale) or editing a
document's own private content instead.

## Environment

| Variable | Default | Description |
|---|---|---|
| `ADOS_API_BASE_URL` | `http://localhost:8000/api/v2` | where `api/main.py` is reachable |
| `ADOS_SERVICE_BASE_URL` | `http://localhost:8010` | where `ados-service/main.py` is reachable |

## What this is not (yet)

stdio-only, single-user, no auth — the same trust boundary as running
`uvicorn` locally already has; do not expose this server's transport
over a network. No propagation (editing a shared fact does not recompose
the documents that selected it — M4.3), no brand authoring (M4.5), no
generative or closed-loop tools (M4.4), no remote transport (M4.6, needs
an auth layer ADOS does not have today). See the design doc's §9–§12 for
the reasoning and the open decisions.

## Tests

```bash
python -m pytest tests_mcp -q
```

`tests_mcp/test_boundaries.py` is an AST check, the same technique
`tests_brand/test_loop_boundaries.py` uses for `brand/llm/loop/`: no
module under `ados_mcp/` may import `brand` or `api` directly, only
`ados_mcp/client.py` may construct an `httpx` client, every tool module
calls `get_client()`, and `ados-service` (the rule registry) stays
write-free even as `api/main.py` gains write methods. `test_client.py`,
`test_resources.py` and `test_tools_*.py` exercise every resource and
tool against a mocked HTTP transport — no live server required, though
the whole M4.2 write path has also been run end to end against a real
`api/main.py` (create project → attach brand → add content → compose →
save version → export) during development.
