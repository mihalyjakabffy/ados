# ADOS-M4 — The Claude Connector

## 1. What this milestone is, in one sentence

Expose the ADOS API that already exists — Project, Brand, Content, Document,
DesignState, and the M3.1–M3.6 generation/closed-loop pipeline — as an MCP
server, so a person can work an entire practice's documentation set by
talking to Claude, with ADOS remaining the single deterministic system of
record and Claude never gaining a write path that bypasses it.

This is not a new engine. It is the thing M2.5 §10 named and deliberately
left undone — *"a future LLM layer sits above this architecture — `User →
LLM → CommandIntent → deterministic ADOS engine → DesignState` — never
inside it"* — built now that `DesignState`, the content-sharing model, the
Brand System, and the closed loop all exist to sit underneath it.

## 2. What already exists that this milestone must not duplicate

Reconnaissance first, per this repository's own convention (see
`m3.6-closed-loop.md` §3):

- **`DesignState`** (`brand/design_state/`) is already "a single, versioned,
  JSON-serializable, renderer-independent, LLM-vendor-independent object"
  (M2.5 §10) — exactly the shape an LLM context needs, already built, already
  tested. M4 exposes it; it does not re-derive it.
- **"One fact, one place"** (`ADOS-0.3.020`) already has a real mechanism:
  `Project.content_items` (the shared pool) + `Document.content_selection` +
  `resolve_document_content()` (`brand/project/content_resolution.py`). Two
  documents already *can* share one fact today. What is missing is not the
  fact model — it's the fan-out that recomposes every document holding a
  selection after the shared item changes (§6 below).
- **Brand as the identity layer** (`brand/`) already resolves to tokens,
  validates architecturally, and is immutable per published version
  (`bump()` is the only way forward). M4 does not re-implement brand
  handling; it exposes `propose`/`approve`/`resolve_tokens`/`audit` as tools.
- **Creative, multi-output-from-one-input** already works exactly as
  envisioned: `brand/examples/build_malthouse.py` turns one project's content
  into three documents (`editorial-quiet`, `technical-dense`, `image-led`),
  byte-identical on rebuild. M4 exposes *choosing* a `DocumentType` +
  `CreativeDirection` pair as a tool; it does not touch `compose()`.
- **Claude already talks to ADOS** — but only *inward*, as one of two
  swappable `LLMProvider`s (`brand/llm/providers/claude_provider.py`),
  called by `brand.llm.*` generation stages, always with a deterministic
  rule-based fallback. That integration is unchanged by M4. M4 adds an
  *outward*-facing surface: Claude as the orchestrating client sitting where
  a human at `ados-web` sits today, per the M2.5 §10 diagram. The two
  Claudes have no code path in common; conflating them would be the
  "second implementation" mistake this repository has refused at every
  milestone so far.
- **The closed loop** (`brand/llm/loop/`) already is "observe, find,
  recommend, patch, act, repeat" for *one document*. M4 needs the same
  discipline (LLM proposes, deterministic code decides; every stop
  condition is a plain comparison) applied to the *fan-out* case, not a new
  philosophy.

## 3. Non-negotiables (the AST-verified boundary, restated for this layer)

Every milestone since M3.5 has enforced its own boundary with a
`test_*_boundaries.py` module. M4's is the most important one in the
repository, because it is the first layer a general-purpose model — not a
narrow, schema-constrained structured-output call — sits directly behind:

1. **No MCP tool calls `compose()`, `apply_intent()`, or any store's `save()`
   directly.** Every tool is a thin wrapper around an existing, tested
   `api/v2` endpoint (or, for the one new module this milestone adds, a
   function that itself only calls existing endpoint-level functions). The
   connector is a new *client* of the API, exactly the relationship
   `ados-web` already has — not a backdoor into `brand/`.
2. **No tool accepts free-form code, SQL, or a file path.** The tool schema
   surface is a closed, named list, the same discipline `ADOS-7.2.020`
   applies to normative vocabulary and `brand.creative.direction`'s
   `extra="forbid"` applies to creative parameters. One narrow, stated
   exception: `audit_brand`'s `package_dir` (§4.2, M4.5) is a server-local
   filesystem path — accepted only because this whole phase already runs
   under the same local-trust boundary as running `uvicorn` on the same
   machine (§12), it only *reads* (never writes) the directory named, and
   what it returns is bounded to `ConsistencyChecker`'s own findings
   (colours/fonts/layout values/inventory records it recognises), never
   arbitrary file content. Any parameter accepting a path must justify
   itself this explicitly, not slip in by analogy to this one.
3. **The LLM proposes, deterministic code decides — restated for chat.**
   Nothing Claude says in conversation mutates a document directly. Every
   write tool's arguments are validated by the same Pydantic models and the
   same `validate_intent()`/`validate_design_intent()`/`validate_command_plan()`
   functions the REST API already runs. A malformed or unsafe request fails
   the tool call with a structured error, the same shape `api/routers`
   already returns.
4. **"AI proposes, the user approves" (`brand/README.md` Rule 3) extends
   unchanged.** `propose_brand` returns a `BrandProposal`; only an explicit
   `approve_brand(approved_by=...)` tool call — naming a real person —
   commits it. A chat message is not consent; a named approval call is.
5. **Nothing is silent.** Every write tool's result states what changed,
   what was recomposed, and what findings now exist — mirroring
   `ADOS-0.7.030`'s binary quality gate and the closed loop's own
   `Iteration.stage_log` audit trail. Claude relays this to the user in
   prose; the connector never discards it.

A `tests_mcp/test_tool_boundaries.py`, AST-based like
`test_loop_boundaries.py`, is the mechanism that keeps rule 1 true as the
tool surface grows.

## 4. Tool and resource surface

MCP separates **resources** (read, pulled into context) from **tools**
(actions, explicitly invoked). ADOS maps onto this cleanly because the API
already separates `GET` (read, side-effect-free) from mutating verbs.

### 4.1 Resources — read-only, ship first

| Resource URI | Backed by | Why it matters |
|---|---|---|
| `ados://projects` | `GET /{}/ados-projects` (list) | orientation |
| `ados://projects/{id}` | `GET /{project_id}` | project facts, `project_data` |
| `ados://projects/{id}/design-state` | `GET /{project_id}/documents/{document_id}/design-state` | **the single source of truth** — see §5 |
| `ados://projects/{id}/content` | `GET /{project_id}/content` | the shared fact pool |
| `ados://brands/{id}` | `GET /brands/{id}` + `resolve_tokens()` | identity, with provenance per token |
| `ados://rules` | `ados-service`'s `ados-rules.yaml` reader | lets Claude cite a real `ADOS-x.y.zzz` rule instead of inventing a justification |

### 4.2 Tools — write, ship behind explicit confirmation

Shipped in M4.2 (`ados_mcp/tools/`), each a 1:1 wrapper with no logic of
its own:

| Tool | Wraps | Domain |
|---|---|---|
| `create_project`, `update_project_data` | `POST/PATCH .../ados-projects` | project |
| `attach_brand` | `PUT .../ados-projects/{id}/brand` | link an existing, already-approved brand to a project — added beyond the original table below, because without it `compose_document`/`export_document` can never leave `no_brand_attached` for anything MCP created |
| `add_document_content`, `remove_document_content` | `POST/DELETE .../documents/{id}/content` | a document's own private content — added beyond the original table below, for the same "content CRUD" scope M4.2's phase entry (§10) already named |
| `add_shared_content`, `remove_shared_content` | `POST/DELETE .../content` | the fact layer |
| `select_content_for_document` | `PUT .../content-selection` | wiring a document to shared facts |
| `create_document` (`document_type_id`, `direction_id?`) | `POST .../documents` + `document_types` registry | choosing a projection, §7 |
| `compose_document`, `save_version`, `export_document` | existing endpoints of the same name | turning content into an issued artefact |
| `download_export` | `GET .../exports/{export_id}/file` | **added later**, see below — the file itself, base64-encoded |

**A second addition, found by actually walking a create-to-delivery
workflow through this connector rather than only through per-endpoint
tests**: `export_document` names an Export record, but nothing in the
original M4.2 surface could turn that into the file bytes a person
actually asked for. `download_export` closes that — the same
already-shipped `GET .../exports/{export_id}/file` endpoint, given an
MCP door and base64-encoded since a PDF/HTML file is not JSON. Confirmed
against two real, downloaded, valid files (a 3-page PDF and a Website
HTML export) in one live run.

**Correction from the original draft of this table**: there is no
`update_shared_content` tool. `api/routers/ados_project.py` has no PATCH
for a single shared `ContentItem` — only add (`POST`) and remove
(`DELETE`). Inventing an update path here, ahead of the endpoint that
would back it, would violate §3 rule 1. The real update path a practice
actually wants — "edit this fact, recompose whatever used it" — is
exactly ADOS-M4.3's job; its own PATCH endpoint is built together with
`propagate_content_change`, not guessed at in M4.2.

Shipped in M4.3 (§6), also 1:1 wrappers:

| Tool | Wraps | Domain |
|---|---|---|
| `propagate_content_change(project_id, item_id)` | `POST .../content/{item_id}/propagate` | recompose every document referencing a shared fact that changed or was removed |
| `propagate_brand_change(project_id, brand_version)` | `POST .../brand/propagate` | move a project onto a published brand version and recompose everything in it |

Shipped in M4.4 (`ados_mcp/tools/generation.py`, `ados_mcp/tools/loop.py`):

| Tool | Wraps | Domain |
|---|---|---|
| `generate_semantic_intent(request, project_id?, document_id?, ...)` | `POST /intent/semantic` | **new**, not in the original table — see correction below |
| `generate_narrative(project_id, semantic_intent, ...)` | `POST .../narrative/plan` | M3.3 |
| `generate_design_intent(project_id, semantic_intent, ...)` | `POST .../design/intent` | M3.4 |
| `generate_commands(project_id, semantic_intent, content_model, ...)` | `POST .../commands/generate` | M3.5 generation |
| `apply_commands(project_id, command_plan, content_model, ...)` | `POST .../commands/apply` | M3.5 execution — computes, never persists (see below) |
| `start_loop`, `continue_loop`, `run_loop`, `approve_loop`, `stop_loop` | `api/routers/closed_loop.py` | bounded, auditable self-correction (§8) — `run_loop` is **new**, see below |

**Correction from the original draft of this table**: every one of
`generate_narrative`/`generate_design_intent`/`generate_commands` requires
a `semantic_intent` payload, and the table gave no tool to produce one.
`generate_semantic_intent` (wrapping the M3.1 endpoint) is added for the
same reason `attach_brand` was added in M4.2 — without it the chain has
no real input. `run_loop` (`POST .../loop/run`, "start a lineage and run
it to completion in one call") existed in the API all along and is the
natural companion to `start_loop`/`continue_loop`; omitting it from the
original table was an oversight, not a decision.

**A second bridge the original table didn't name**: `generate_commands`
and `apply_commands` both require `content_model` — a
`brand.content.model.ContentModel` payload, a *different* object from
anything `ados_mcp.tools.content` produces (`api/routers/command.py`'s
own docstring: "no bridge between the two exists yet"). The one place to
get one is `compose_document`'s own response (already an M4.2 tool),
which already returns a `content_model` field alongside the composed
plan. The tool descriptions say this explicitly; verified against a real
`api/main.py` end to end (§10).

**`apply_commands` computes, it does not persist** — confirmed against
`docs/architecture/m3.5-command-generation.md`: "no `CommandPlan` is
persisted into any Project/Document store." Its tool description tells
the connecting model to call `save_version(..., plan=<final_plan>)`
afterward to keep a result, reusing the M4.2 tool rather than inventing
a new persistence path for LLM-driven output specifically.

Every `generate_*` tool may call a real LLM on the ADOS server, or its
deterministic rule-based fallback if no API key is configured there —
only `generate_semantic_intent`'s response names which one ran
(`ProviderMetadata`); the downstream stages (`NarrativePlan`,
`DesignIntent`, `CommandPlan`) carry no such field today. The connector's
own startup instructions (`ados_mcp/server.py`) tell the connecting model
this, so it never claims a provider it cannot actually see.

Shipped in M4.5 (`ados_mcp/tools/brand.py`):

| Tool | Wraps | Domain |
|---|---|---|
| `propose_brand(brief, name?)` | `POST /brand-proposals` | a candidate `Brand` from `BrandAgent` — never saved |
| `approve_brand(proposal, approved_by)` | `POST /brand-proposals/approve` | the one write, requires a named human (`brand/README.md` Rule 3, §3 rule 4) |
| `audit_brand(brand_id, package_dir, version?)` | `POST /brands/{id}/audit` | **new endpoint**, see below |

`audit_brand` is backed by a genuinely new endpoint —
`POST /brands/{brand_id}/audit`, wrapping
`brand.validation.consistency.audit_package` (already real, tested
domain code with no HTTP door before now) — added the same way M4.3
added `propagate_content_change`'s two endpoints: the underlying
capability already existed and was already load-bearing (`brand/README.md`'s
own "the consistency check" section, `python -m brand.cli audit`), it
simply had no HTTP surface yet. `package_dir` names a directory on the
machine running the ADOS API server — the same local trust boundary this
whole phase already runs under (§12); this is not a new exposure.

**Correction from the original draft of this table** (§10): "guidelines/export
tools" appeared in the phase description but was never given a concrete
shape in this table, and no endpoint exists for either capability today
— `brand.guidelines.generator`/`brand.export.exporters` (the eighteen-section
guidelines document; CSS/JSON/YAML token exports) are CLI-only
(`python -m brand.cli guidelines` / `export`). Designing a new endpoint
shape for them without a concrete tool spec to build against would be
exactly the speculative surface §3's non-negotiables warn against.
Deferred, not shipped — see §12.

## 5. `DesignState` is the connector's spine

`DesignState` was built in M2.5 specifically as "the semantic primitives an
LLM layer needs... with no dependency on Claude/OpenAI/Gemini." It already
carries Project, Brand, Content, Document, Page, Component, Layout,
VisualLanguage, Asset, Constraint, and Version in one frozen, versioned
object. M4's read path is close to trivial *because* M2.5 anticipated it:
fetch `GET .../design-state`, hand it to Claude as a resource, and every
question about "what does this project currently say" is answered from real
persisted state — never from the model's memory of an earlier turn.

This is also the mechanism that keeps a long chat session honest: `?version=N`
already exists on the endpoint, so a tool call can pin a conversation to a
specific saved version and detect drift (`ConstraintState`/`VersionState`
already expose exactly the fields `orchestrator.py`'s own
`output_design_state_version` staleness check uses at §6 of M3.6). M4's
tools should perform the identical check before any write: if the
`DesignState` version Claude last read is not the current one, refuse the
write and ask Claude to re-read first — `StopReason.STALE_STATE`, reused,
not reinvented.

## 6. The gap this milestone had to fill: fan-out propagation (**shipped**)

Before M4.3, editing `Project.content_items[i]` did not touch any
`Document`. The *next* `compose_document()` of a document selecting that
item would pick up the new value — but nothing recomposed the other
documents automatically, and nothing told the user which ones now
differed from what was last issued. That was the literal gap between
what existed and "ha valahol valami változik, minden dokumentumban
frissítse."

**`brand/project/propagation.py`** (pure domain logic, no repository I/O,
no LLM — mirroring `versioning.py`'s own "logic here, I/O in the router"
split):

```
propagate_content_change(project, brand, changed_item_id) -> PropagationResult
    for each Document in project.documents:
        if changed_item_id in document.content_selection
           or changed_item_id in {i.id for i in document.content_items}:
            recompose via the shared _recompose_one() step —
                resolve_document_content() -> compose() -> evaluate()
                -> check_requirements(), the exact sequence
                compose_document's own endpoint runs, factored out so
                both entry points below call it identically
            record: document_id, recomposed?, reason if not, findings, requirement_findings
        else:
            record document_id under `unaffected`
    return PropagationResult(project=<new Project, ready to persist>, touched, unaffected)
```

`propagate_brand_change(project, new_brand)` is the same shape for a
brand `bump()`: moves `project.brand_version` to `new_brand.version` and
recomposes *every* document in the project (they all share the one
brand, so there is no `unaffected` set for this entry point) — never an
in-place edit, since brands stay immutable per published version
(`brand/README.md` Rule 5). "The palette changed" is always "`bump()` a
new version elsewhere, get it approved and published, then propagate",
never a silent mutation of an issued brand.

**Deliberate, stated deviation from `compose_document`'s own
precondition**: a single-document compose treats "no content" as a hard
422 — the caller asked for exactly that document. A fan-out over many
documents must not abort the whole batch because one of them happens to
be an empty scaffold (or just lost its only content to the very change
being propagated); that document is instead reported
`recomposed=false, reason="no_content"` and the rest proceed. This is the
one place propagation's behaviour differs from the endpoint it otherwise
mirrors, and it differs for a stated reason.

Both functions call only `compose()`/`evaluate()` — the same primitives
`brand/llm/loop/execution.py` is already the sole authorised caller of
within `brand/llm/loop/` (§10 of `m3.6-closed-loop.md`).
`brand/project/propagation.py` is the analogous, explicitly-listed
authorised caller within `brand/project/` — verified the same AST way
(`tests_brand/test_propagation_boundaries.py`), scoped to that package
since `api/routers/ados_project.py` itself (outside `brand/`) remains the
original, first caller for a single document's own `.../compose`.
Neither propagation function calls a store's `save()` itself — both
return a new `Project` for the caller (the router, then the MCP tool) to
persist, so "propagate" never becomes a second place that decides how or
whether to write to disk.

**API** (`api/routers/ados_project.py`): `POST /{project_id}/content/{item_id}/propagate`,
`POST /{project_id}/brand/propagate` (body: `{"brand_version": "..."}`).

**Correction from this section's original sketch**: the brand endpoint is
`POST /{project_id}/brand/propagate`, project-scoped under
`ados-projects`, not `POST /brands/{id}/versions/{version}/propagate`
under the brand router as first drafted. A brand can be attached to more
than one project, and the only real index of "which projects use this
brand" is each project's own `brand_id` — there is no reverse index on
the brand side to scan. Scoping the operation to one project at a time
(the same scope `propagate_content_change` already has, and the only
scope `Project`'s one-JSON-file-per-project store makes cheap) avoids
inventing that index for a milestone whose own stated goal (§10) is to
stay "narrow enough to be trustworthy."

**MCP tools** (`ados_mcp/tools/propagation.py`): `propagate_content_change(project_id, item_id)` /
`propagate_brand_change(project_id, brand_version)`, thin wrappers of
those two endpoints exactly per §3 rule 1. Neither is called
automatically by any other tool — `add_shared_content`, `remove_shared_content`
and `attach_brand` never trigger propagation as a side effect (§9
decision 1); the connector's own startup instructions
(`ados_mcp/server.py`) tell the connecting model this explicitly, so it
relays "N documents now differ" as a distinct step rather than implying
a write already reached every document.

Whether an edit auto-propagates or requires this explicit second call was
a real design decision, not a detail — settled in §9 (decision 1,
explicit).

## 7. "Creatively, any output from the same input" — where the creativity actually lives

The Composer is deterministic by rule (`ADOS-7.5.010`). What varies between
two outputs of one project is never layout math; it is which of the 11+
`DocumentType` projections and which `CreativeDirection` (`editorial-quiet`
/ `technical-dense` / `image-led`) is chosen, plus the narrative text M3.3
already generates per-audience. So Claude's actual creative contribution
in M4 is exactly what a good associate's is: reading a brief ("make
something for an investor call next week" vs "I need a technical package for
tender"), picking `document_type` + `direction`, and — through
`generate_narrative` — asking ADOS's own audience-aware narrative stage to
write the copy, never inventing typography, spacing or colour itself. This
is the same separation `brand/README.md` already draws between the Brand
System (how it looks) and the Creative Layer (what goes on the page) — M4
adds "who decides which projection" as a third, conversational layer on
top, without touching either.

## 8. Regeneration on change — reusing the closed loop, not re-deriving it

For "update everything downstream" beyond a single fact edit — e.g. "the
findings say this page's density is wrong, fix it" — M4 does not add a
second correction mechanism. `start_loop`/`continue_loop`/`approve_loop` are
thin MCP wrappers of `api/routers/closed_loop.py`, already: bounded (`max_
iterations`, `max_llm_calls`), auditable (`stage_log`), safe by default
(`autonomy=SAFE` auto-executes only `SAFE`-labelled commands; anything else
returns `AWAITING_APPROVAL` for the chat-facing Claude to relay as a
question, not a silent action). The connector's only job here is transport.

## 9. Decisions

1. **Propagation is explicit, not automatic (decided).** A content edit is
   instant and scoped to the shared item only. `propagate_content_change`
   / `propagate_brand_change` are separate tool calls the chat-facing
   Claude issues as a visible next step — "3 documents reference this fact;
   recompose them?" — never a silent side effect of the edit itself. This
   is the literal reading of `ADOS-0.7.030`'s "nothing silent" gate applied
   to chat: a typo fix does not fire N re-compositions (and, once
   `generate_narrative` is in the loop, N LLM calls) before the user
   finishes a sentence. `PropagationResult` (§6) is what the connector
   hands back so Claude can state exactly what changed, never a bare "done".
2. **v1 target is Claude Code / Claude Desktop over stdio (decided).** No
   auth layer is required — the trust boundary is the same one running
   `uvicorn` locally already has — so M4.1–M4.5 can ship and be used from
   this repository immediately. The remote, HTTP+SSE claude.ai
   custom-connector transport is deferred to M4.6, once the tool surface
   has proven itself locally and the auth model it needs (§12) is designed
   on its own, rather than retrofitted under schedule pressure.
3. **Resolved while building M4.4 — this was never a per-call choice.**
   Every `plan_narrative`/`plan_design_intent`/`plan_commands`/extractor
   call picks its own provider internally, based on whether
   `ANTHROPIC_API_KEY`/`GEMINI_API_KEY` is set in the *ADOS API server's*
   own environment (root `README.md`'s "every LLM-backed generator has a
   deterministic rule-based fallback... set one to exercise the real LLM
   path locally") — none of the M3.3–M3.5 request bodies has a
   provider/`use_llm` field for a caller to set. So there is nothing for
   `ados_mcp` to default: whether a given ADOS deployment answers from a
   real LLM or the deterministic fallback is a deployment-time choice
   (whether that server process has a key configured), not something a
   tool call can request either way. What the connector *can* do, and
   does: `generate_semantic_intent`'s response names which one actually
   ran (§4.2) — relay that honestly rather than guessing.

## 10. Phased rollout

| Phase | Scope | Risk |
|---|---|---|
| **M4.1** | Resources only (§4.1) — read `DesignState`, Project, Brand, Rules, over **stdio** (Claude Code / Claude Desktop; §9 decision 2). Zero write tools. **Shipped.** | Near zero — no new mutation path exists yet. |
| **M4.2** | Write tools that wrap one existing endpoint 1:1: project (`create_project`, `update_project_data`, `attach_brand`), content CRUD (document-private and shared pool), document lifecycle (`create_document`, `compose_document`, `save_version`, `export_document`, and — added once a real create-to-delivery run exposed the gap — `download_export`). AST boundary tests extended (write verbs confined to `client.py`, every write tool calls `get_client()`, `ados-service` stays write-free). **Shipped** — verified against a real `api/main.py` end to end (create → attach brand → content → compose → save version → export), not only against mocks; `download_export` separately verified by downloading two real, valid files (a 3-page PDF and a Website HTML export) from one live workflow. | Low — every tool already had REST-level tests; MCP tests assert the wrapper, not the logic. |
| **M4.3** | `brand/project/propagation.py` + its two endpoints (`.../content/{id}/propagate`, `.../brand/propagate`) + two MCP tools, called explicitly per §9 decision 1 — never as a side effect of the edit tools in M4.2. Its own AST boundary suite (`tests_brand/test_propagation_boundaries.py`, mirroring `test_loop_boundaries.py`). **Shipped** — pure-domain tests, API tests, MCP-tool tests, and a live end-to-end run against a real `api/main.py` (shared item → select on one of two documents → propagate → only the referencing document recomposes, the other is reported `unaffected`). | Medium — first genuinely new backend logic this milestone added; mitigated by matching M3.6's own boundary-testing discipline from the first commit. |
| **M4.4** | Generative tools (`generate_semantic_intent`, `generate_narrative`, `generate_design_intent`, `generate_commands`, `apply_commands`) and the closed-loop tools (`start_loop`/`continue_loop`/`run_loop`/`approve_loop`/`stop_loop`), gated by the loop's own existing autonomy policy (default `safe`) — no second gate invented. Two new read-only resources (loop history, loop iteration trace) added alongside, since `approve_loop`'s own tool description needs something real to point at. **Shipped** — verified end to end against a real `api/main.py`: the full chain semantic intent → narrative → design intent → compose → commands → apply → save_version, plus a full closed-loop start → history → stop, all in one run. | Medium — cost/latency-visible (real LLM calls on the ADOS side are possible, §9 decision 3), but every tool reuses M3.1–M3.6 unchanged; no new backend logic. |
| **M4.5** | Brand proposal loop in chat (`propose_brand`/`approve_brand`), plus `audit_brand` behind a new endpoint. **Shipped** — verified end to end against a real `api/main.py`: proposed a brand, approved it by a named human, seeded a real STUDIO OM brand, built its real package, audited it clean (53 files), then confirmed a missing `package_dir` surfaces its structured 404 detail — catching, and fixing, a real bug in `AdosClient._request` (it had special-cased 404 to a bare "not found: {url}", discarding whatever detail the endpoint actually returned; now it keeps "not found" as a stable substring while still surfacing the JSON detail, for every status code). "Guidelines/export tools" from the original phase description are deferred, undesigned (§4.2, §12) — not shipped as part of this phase. | Low — human-approval gate already exists; this only relays it. `audit_brand` is the one new endpoint, narrow and read-only. |
| **M4.6** | Remote transport (Streamable HTTP, the current MCP spec's recommended one — the phase table's original "HTTP+SSE" conflated it with the older SSE transport, kept only for compatibility) + a bearer-token guard (`ados_mcp/auth.py`), selected via `ADOS_MCP_TRANSPORT` (default stays `stdio`). Deliberately not OAuth — see §12. **Shipped** — verified end to end with the real transport: a full MCP `initialize` handshake over HTTP, refused with 401 with no token or the wrong one, succeeding (real server capabilities + instructions back) with the correct one. | Highest — the one genuinely new piece of infrastructure (ADOS has no auth today); mitigated by keeping the guard itself small enough to read in one sitting rather than half-implementing OAuth. |

## 11. Proposed layout

```
ados_mcp/
  server.py        # tool/resource registration; stdio (default) + the
                     # M4.6 remote entrypoint (run_remote), selected via
                     # ADOS_MCP_TRANSPORT
  client.py         # one httpx wrapper around api/v2 — the ados_mcp/ analogue
                     # of claude_provider.py's get_client(): the one shared,
                     # low-level path every tool call goes through
  resources.py
  tools/
    projects.py  content.py  documents.py  propagation.py  brand.py  generation.py  loop.py
                 #  ^ M4.2      ^ M4.2         ^ M4.3        ^ M4.5    ^ M4.4        ^ M4.4
  auth.py          # M4.6 — the bearer-token ASGI middleware guarding the
                     # remote transport; plain Starlette, deliberately not
                     # the MCP SDK's own OAuth-shaped auth mechanism (§12)
tests_mcp/
  test_boundaries.py        # AST: no module imports brand/ or api/routers/
                             # directly, only client.py touches httpx, every
                             # tools/* module calls get_client()
  test_client.py  test_resources.py  test_tools_projects.py  test_tools_content.py
  test_tools_documents.py  test_tools_propagation.py  ...  # one per resources/tools module
  test_auth.py               # the bearer-token middleware against a mocked app
  test_auth_integration.py   # the same guard wrapping a real (tool-less)
                              # FastMCP streamable_http_app()
docs/architecture/m4-claude-connector.md   # this document
brand/project/propagation.py   # M4.3 — lives under brand/, not ados_mcp/;
                                # see §6 for why the fan-out is domain logic,
                                # not a connector concern
tests_brand/
  test_propagation.py            # pure-domain unit tests
  test_propagation_boundaries.py # AST: only propagation.py calls compose()/
                                  # evaluate() within brand/project/
  test_propagation_api.py        # the two new api/routers/ados_project.py endpoints
  test_brand_audit_api.py        # M4.5 — POST /brands/{id}/audit, against a
                                  # real, fully-built STUDIO OM package
```

`api/routers/brand.py` also gained one new endpoint in M4.5,
`POST /brands/{brand_id}/audit` — a thin HTTP shell around the
already-real, already-tested `brand.validation.consistency.audit_package`
(no new domain module needed this time, unlike M4.3's `propagation.py`,
since the underlying function already lived in `brand/` and needed no new
logic, only a door).

Named `ados_mcp/`, not `mcp/` — the MCP Python SDK is itself the PyPI/import
name `mcp`; a same-named top-level package at the repo root would shadow it
the moment anything under this package writes `import mcp`. This is a
naming correction only, not an architecture change from §3/§4.

`ados_mcp/` sits beside `api/` and `ados-web/` as a third, independent
client of `api/main.py` (plus `ados-service/main.py` for the rule registry)
— not inside `brand/`, and not merged into `api/routers/`, for the same
reason `ados-web`'s dev pages are a frontend concern and not a router: the
MCP layer's job is translation and transport, and giving it its own
top-level package is what makes the AST boundary test in §3 possible to
write and trust.

## 12. Known limitations (stated honestly, per this repository's convention)

- **A remote transport now exists (M4.6), guarded by a bearer token, not
  OAuth.** `ados_mcp/auth.py` wraps `FastMCP.streamable_http_app()`/
  `.sse_app()` with plain ASGI middleware checking `Authorization: Bearer
  <token>` against one shared secret (`ADOS_MCP_TOKEN`) — never the MCP
  SDK's own `TokenVerifier`/`AuthSettings` mechanism, which is shaped for
  a real OAuth resource-server/authorization-server pair (a mandatory
  `issuer_url`, discovery metadata, dynamic client registration). ADOS is
  a single-practice tool with no user directory and no client to
  register; half-configuring that machinery around one shared secret
  would either fake OAuth metadata that doesn't back a real authorization
  flow — actively misleading to a client that tries to follow it — or
  ship it half-built. A plain, five-line header check that does exactly
  what it says is the more honest boundary, and is what shipped. The
  consequence: **there is no interactive "click to authorize" flow** —
  the token is generated once (`python -m ados_mcp.auth generate`) and
  configured on both ends out of band. A future MCP client that
  specifically requires a discoverable OAuth authorization flow to add a
  remote connector at all is not served by this design; revisit then,
  not speculatively now.
- **The DNS-rebinding-protection trade in `run_remote()` is deliberate,
  not an oversight.** FastMCP auto-scopes that protection to loopback
  Host/Origin values the moment it is constructed without an explicit
  non-default `host=`; `ados_mcp.server.mcp` is one process-lifetime
  singleton constructed before any transport is chosen, so it is always
  loopback-scoped at that point. Binding to a non-loopback
  `ADOS_MCP_HOST` therefore disables that specific protection (every real
  remote request's Host header would otherwise be rejected regardless of
  a correct token) — an acceptable trade because DNS rebinding defends a
  *loopback-trusting* server against a browser-based attack, a threat
  model the bearer token already supersedes once every request needs a
  secret no browser page can know. `ADOS_MCP_HOST` still defaults to
  loopback, so this trade is opt-in, not automatic.
- **`audit_brand`'s `package_dir` is sharper now that remote access
  exists, and was reconsidered here, not left as a stale "revisit later"
  note.** Locally (M4.1–M4.5), it added no new capability — whoever ran
  `ados_mcp` already had filesystem access to the same machine. With a
  remote, bearer-token-authenticated caller (M4.6), it becomes a bounded
  filesystem-read oracle on the ADOS API server's own host (bounded to
  what `ConsistencyChecker` parses — colours, fonts, layout custom
  properties, the asset inventory — never arbitrary file content). This
  is judged an accepted consequence of the token already being "a master
  key, not a scoped credential" (`ados_mcp/README.md`'s own security
  notes): a holder of that token already has full read/write access to
  every project and brand this instance can reach, so one more bounded,
  read-only filesystem capability is consistent with, not beyond, that
  model. It is not, and should not become, a reason to treat the token
  as anything less than a full production secret.
- **Propagation is document-scoped, not cross-project.** A shared fact
  duplicated by hand across two *different* projects (not the shared pool)
  is out of scope — the same boundary `ADOS-0.3.020`'s own carrier-per-fact-
  class table draws.
- **No per-section correction**, inherited directly from M3.5/M3.6: every
  patch and every propagation target is document-level, because no
  structural bridge from content-reference ids to `ContentModel.ContentBlock.id`
  exists yet anywhere in the shipped system (M3.6 §16). M4 does not invent
  one either.
- **No guidelines/export tools.** `brand.guidelines.generator` (the
  eighteen-section guidelines document) and `brand.export.exporters`
  (CSS/JSON/YAML token exports) remain CLI-only — no endpoint exists for
  either, and none was designed speculatively for M4.5 (§4.2). A real gap
  if a future phase wants them; not silently pretended-away.
- **No tool assigns content into a document's named Sections.** A
  document created with `create_document(document_type_id=...)` gets that
  type's `default_structure` as empty `Section`s
  (`api/routers/ados_project.py`'s own `create_document`), but nothing in
  `ados_mcp` wraps `PATCH .../sections/{section_id}` to put a content id
  into one. Found live: a `client-presentation`/`case-study` document
  composed and exported through this connector will show its
  `required_section_present` requirement finding, even with real,
  relevant content selected onto the document, because that content was
  never assigned into a named section slot. `project-presentation` and
  untyped documents have no such requirement and export cleanly through
  the tools that exist today (§10, M4.2's live-run note) — this is a real
  gap for the document types that do require sections, not a defect in
  what shipped.
- **No per-project or per-user scoping, at any transport.** Every
  authenticated caller — a local stdio client or a remote bearer-token
  one — gets identical full access to every project and brand this ADOS
  instance can reach. A future multi-practice or multi-seat deployment
  would need real scoping added deliberately; nothing here assumes it
  exists.
- **All of §9's decisions are settled**, including decision 2's own
  scope: M4.6 shipped the transport and the auth guard it named, in the
  form reasoned about above. Nothing in this design remains open.
