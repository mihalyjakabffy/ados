# ados_mcp — the ADOS Claude connector

ADOS-M4.1–M4.6. Design: [`docs/architecture/m4-claude-connector.md`](../docs/architecture/m4-claude-connector.md).

An MCP server exposing ADOS's own `DesignState`, projects, shared content
pool, brand identity, the ADOS 1.0 rule registry, and closed-loop
lineages as resources, plus tools to create and edit
projects/documents/content, compose/save/export a document, propagate a
changed shared fact or brand version to every document that references
it, run the M3.1–M3.5 generation pipeline (semantic intent → narrative /
design intent → commands → apply), drive the M3.6 closed loop, and
propose/approve a brand identity in chat, to any MCP client — Claude
Code, Claude Desktop, or a custom client. It is a new *client* of
`api/main.py` and `ados-service/main.py`, talking to both over plain
HTTP, exactly the relationship `ados-web` already has to `api/main.py`.
It does not import `brand/` or `api/routers/` — every tool is a thin
wrapper around one already-validated ADOS endpoint, so a malformed or
unsafe request is refused by ADOS itself, never silently accepted
(design doc §3). Ships over stdio by default (Claude Code / Claude
Desktop); a bearer-token-guarded remote HTTP transport for a claude.ai
custom connector is also available (ADOS-M4.6) — see below.

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

## Remote transport (ADOS-M4.6)

For a remote MCP client — a claude.ai custom connector, or any MCP
client that isn't running on the same machine — the connector can serve
Streamable HTTP (the current MCP spec's recommended remote transport;
the design doc's original "HTTP+SSE" phrasing conflated it with the
older SSE transport, kept here only for a client that hasn't moved off
it) behind a required bearer token. **Never run this without generating
a token and putting TLS in front of it** — see "Security notes" below.

```bash
# once: generate a token and put it wherever this server reads
# ADOS_MCP_TOKEN from (a secrets manager, a local .env, ...)
python -m ados_mcp.auth generate

# run the remote transport
ADOS_MCP_TRANSPORT=http ADOS_MCP_TOKEN=<the generated token> \
  python -m ados_mcp.server
# -> serves Streamable HTTP on http://127.0.0.1:8100/mcp by default
```

A client then connects with `Authorization: Bearer <the same token>` on
every request. In Claude Code / Claude Desktop's own MCP config, a
remote server is added with a `url` (and, where the client supports it,
a static bearer token) instead of a `command`; consult your MCP client's
own current documentation for the exact config shape it expects — this
changes across clients and versions faster than this file should try to
track.

### Security notes — read before running this anywhere but your own laptop

- **The token is a master key, not a scoped credential.** Every
  authenticated request gets full read/write access to every project
  this ADOS instance can reach — there is no per-project or per-user
  access control anywhere in this tool surface (design doc §12).
- **This is a bearer-token guard, not OAuth.** `ados_mcp/auth.py`
  explains why: ADOS is a single-practice tool, and half-configuring the
  MCP SDK's OAuth-shaped auth machinery around one shared secret would
  be worse than a plain, fully-understood header check. If a client
  specifically requires a real OAuth authorization flow to add a remote
  connector at all, this server does not provide one today.
- **TLS is not optional.** This server speaks plain HTTP; a bearer token
  sent over it in cleartext is a token handed to anyone on the network
  path. Put a reverse proxy or tunnel that terminates TLS in front of it
  (nginx, Caddy, Cloudflare Tunnel, Tailscale Funnel, an SSH tunnel for
  personal use) — never expose `ADOS_MCP_PORT` directly to the open
  internet.
- **`ADOS_MCP_HOST` defaults to loopback (`127.0.0.1`)** even in remote
  mode, so binding anywhere reachable from another machine is an
  explicit opt-in, not an accident. If you do set it to a non-loopback
  address, `run_remote()` disables FastMCP's own DNS-rebinding
  protection (which is scoped to loopback Host/Origin values and would
  otherwise reject every real remote request) — the bearer token is this
  transport's actual boundary once that trade is made; see the comment
  in `ados_mcp/server.py::run_remote` for the full reasoning.
- **`api/main.py` and `ados-service/main.py` stay local-only, unchanged.**
  Only run `ados_mcp` itself in remote mode; point `ADOS_API_BASE_URL`/
  `ADOS_SERVICE_BASE_URL` at their normal loopback addresses. This
  connector is the one thing meant to be network-facing — nothing else
  in this repository's HTTP surface has been reviewed for that.

## Resources

| URI | Backed by | Content |
|---|---|---|
| `ados://projects` | `GET /api/v2/ados-projects` | every project, most recently updated first |
| `ados://projects/{project_id}` | `GET /api/v2/ados-projects/{project_id}` | one project's facts |
| `ados://projects/{project_id}/content` | `GET /api/v2/ados-projects/{project_id}/content` | the shared `ContentItem` pool |
| `ados://projects/{project_id}/documents/{document_id}/design-state` | `GET .../documents/{document_id}/design-state` | the deterministic single source of truth for one document |
| `ados://brands/{brand_id}` | `GET /api/v2/brands/{brand_id}` + `.../tokens` | identity + resolved design tokens with provenance |
| `ados://rules` | `ados-service`'s `GET /api/rules` | the ADOS 1.0 476-rule registry |
| `ados://projects/{project_id}/documents/{document_id}/loop` | `GET .../loop` | full closed-loop iteration history for one document |
| `ados://projects/{project_id}/documents/{document_id}/loop/{iteration_id}/trace` | `GET .../loop/{id}/trace` | one iteration's condensed decision trace |

## Tools

Every tool is a thin wrapper around one endpoint; none of them contain
business logic of their own.

### Project, content, document lifecycle (ADOS-M4.2/M4.3)

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
| `export_document(project_id, document_id, version_number?, format="pdf")` | `POST .../documents/{id}/export` | `format` is `pdf` or `html`; names an export id, doesn't return the file |
| `download_export(project_id, export_id)` | `GET .../exports/{id}/file` | the actual file, base64-encoded — decode before handing it to the person |
| `propagate_content_change(project_id, item_id)` | `POST .../content/{id}/propagate` | recomposes every document referencing `item_id`; reports which and which were left alone |
| `propagate_brand_change(project_id, brand_version)` | `POST .../brand/propagate` | moves the project onto an already-published brand version and recomposes everything in it |

There is still no `update_shared_content` — `api/routers/ados_project.py`
has no endpoint for editing one shared `ContentItem` in place. Editing a
shared item today is remove + re-add (a new id — every document's
`content_selection` referencing the old one goes stale and must be
re-selected); `propagate_content_change` operates on "this item id
changed or is gone", so it doesn't need an update endpoint to do its job
(design doc §6, §9). Neither propagation tool is called automatically by
any other tool — an edit is instant and scoped to the item; propagating
it is always a second, explicit call, so relay what it reports ("3
documents recomposed, 1 left alone") rather than assuming a write already
reached every document.

### Generation pipeline (ADOS-M4.4, M3.1–M3.5)

| Tool | Wraps | Notes |
|---|---|---|
| `generate_semantic_intent(request, project_id?, document_id?, version?, conversation?)` | `POST /intent/semantic` | interprets natural language into the typed input every other `generate_*` tool needs |
| `generate_narrative(project_id, semantic_intent, document_id?, ...)` | `POST .../narrative/plan` | audience-aware NarrativePlan |
| `generate_design_intent(project_id, semantic_intent, document_id?, ...)` | `POST .../design/intent` | brand-consistent DesignIntent (plans a NarrativePlan internally too) |
| `generate_commands(project_id, semantic_intent, content_model, document_id?, ...)` | `POST .../commands/generate` | needs `content_model` from `compose_document`'s response |
| `apply_commands(project_id, command_plan, content_model, base_direction_id\|base_direction, ...)` | `POST .../commands/apply` | computes a new plan, **does not persist** — pass its `final_plan` to `save_version` to keep it |

Only `generate_semantic_intent`'s response names which provider produced
it (a real LLM, or the deterministic fallback used when the ADOS server
has no `ANTHROPIC_API_KEY`/`GEMINI_API_KEY` configured) — the downstream
stages don't carry that field. Every stage may be a real LLM call with
real latency and cost; report it as such, never as a free local
computation (design doc §9 decision 3).

### Closed loop (ADOS-M4.4, M3.6)

| Tool | Wraps | Notes |
|---|---|---|
| `start_loop(project_id, document_id, semantic_intent, ..., autonomy="safe", dry_run=False)` | `.../loop/start` | first iteration of a fresh lineage; 409 if one exists |
| `continue_loop(project_id, document_id, ...)` | `.../loop/continue` | next iteration of an open lineage |
| `run_loop(project_id, document_id, semantic_intent, ...)` | `.../loop/run` | start + run to completion in one call, always persists |
| `approve_loop(project_id, document_id, command_ids?)` | `.../loop/approve` | resumes an `AWAITING_APPROVAL` iteration |
| `stop_loop(project_id, document_id)` | `.../loop/stop` | ends the lineage; a no-op if already terminal |

`autonomy` (`none`/`recommend`/`safe` default/`full`) is the loop's own,
already-built safety gate (ADOS-M3.6 §37/§38) — `safe` auto-executes only
`SAFE`-labelled commands and stops everything else at
`AWAITING_APPROVAL`; nothing here adds a second gate on top of it. Pass
`full` only when the user has explicitly asked for unattended execution.
Unlike the generation tools above, every loop tool (except a `dry_run`
call) **does** persist — read the loop-history resource before calling
`approve_loop` so the decision is grounded in what the loop actually
found.

### Brand proposal loop (ADOS-M4.5)

| Tool | Wraps | Notes |
|---|---|---|
| `propose_brand(brief, name?)` | `POST /brand-proposals` | a candidate `Brand` from `BrandAgent` — **nothing is saved** |
| `approve_brand(proposal, approved_by)` | `POST /brand-proposals/approve` | the one write; `approved_by` must be a real person's name, never invented |
| `audit_brand(brand_id, package_dir, version?)` | `POST /brands/{id}/audit` | audits an already-built package directory (server-local path) against the brand |

`audit_brand` is backed by a new endpoint added alongside it
(`POST /brands/{brand_id}/audit`, wrapping the already-real
`brand.validation.consistency.audit_package`) — it is this connector's
one tool that accepts a filesystem path, a stated, narrow exception to
the "no tool accepts a file path" rule (design doc §3 rule 2), justified
there because it only *reads* the named directory and this whole phase
already runs under the same local trust boundary as running `uvicorn` on
the same machine. There are still no `guidelines`/`export` tools —
`brand.guidelines.generator`/`brand.export.exporters` remain CLI-only;
no endpoint was designed for either without a concrete tool spec to
build against (design doc §4.2, §12).

## Environment

| Variable | Default | Description |
|---|---|---|
| `ADOS_API_BASE_URL` | `http://localhost:8000/api/v2` | where `api/main.py` is reachable |
| `ADOS_SERVICE_BASE_URL` | `http://localhost:8010` | where `ados-service/main.py` is reachable |
| `ADOS_MCP_TRANSPORT` | `stdio` | `stdio` (default) / `http` (Streamable HTTP) / `sse` (legacy) |
| `ADOS_MCP_TOKEN` | *(required for `http`/`sse`)* | the bearer token every remote request must carry — `python -m ados_mcp.auth generate` |
| `ADOS_MCP_HOST` | `127.0.0.1` | remote-transport bind address; non-loopback is an explicit opt-in (see security notes above) |
| `ADOS_MCP_PORT` | `8100` | remote-transport port |

## What this is not (yet)

Single-user — the bearer token is a master key with no per-project or
per-user scoping, and there is no OAuth authorization flow, only a
resource-server-style token check (see the security notes above). No
guidelines/export tools (`brand.guidelines.generator`/
`brand.export.exporters` remain CLI-only). See the design doc's §9–§12
for the full reasoning and what remains genuinely open.

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
every write and generation path has also been run end to end against a
real `api/main.py` during development: create project → attach brand →
two documents → shared content selected on one of them → propagate →
only the referencing document recomposes, the other reported
`unaffected` (M4.2/M4.3); semantic intent → narrative → design intent →
compose → commands → apply → save_version, plus a full closed-loop
start → history → stop, in one run (M4.4); and propose → approve (by a
named human) → seed a real STUDIO OM brand → build its real package →
audit it clean, then confirm a missing `package_dir` surfaces its
structured detail rather than a bare "not found" (M4.5 — this last check
caught and fixed a real bug in `AdosClient._request`'s own 404 handling);
and, over the real remote transport (M4.6), a full MCP `initialize`
handshake — refused with 401 for no token or the wrong one, and
succeeding, with the server's real capabilities and instructions in the
response, for the correct one. `test_auth.py` and
`test_auth_integration.py` cover `ados_mcp/auth.py` itself: the
bearer-token middleware against a mocked app and against a real (if
tool-less) FastMCP `streamable_http_app()`. See `brand/README.md`'s own
testing section, `tests_brand/test_propagation*.py` and
`tests_brand/test_brand_audit_api.py` for that domain-level and
API-level coverage — that logic lives under `brand/` and `api/routers/`,
not here.
