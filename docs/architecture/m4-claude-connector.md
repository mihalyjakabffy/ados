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
   `extra="forbid"` applies to creative parameters.
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

Deferred to later phases, unchanged from the original plan:

| Tool | Wraps | Domain | Phase |
|---|---|---|---|
| `propose_brand`, `approve_brand`, `audit_brand` | `BrandAgent.generate_proposal`, `.approve()`, `brand.validation.consistency` | identity, human-gated | M4.5 |
| `generate_narrative`, `generate_design_intent`, `generate_commands`, `apply_commands` | M3.3–M3.5 endpoints | letting Claude invoke ADOS's *own*, validated generation stages instead of freehanding prose that skips them | M4.4 |
| `start_loop`, `continue_loop`, `approve_loop`, `stop_loop` | `api/routers/closed_loop.py` | bounded, auditable self-correction, §8 | M4.4 |

Every generative tool (`generate_*`, `start_loop`) states in its result
whether ADOS's own Claude-backed path ran or the deterministic fallback did
(`ProviderMetadata` already carries this) — the chat-facing Claude should
never present a rule-based extraction as if a second LLM call happened, or
vice versa.

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
3. **Open**: whether `generate_*` tools default to ADOS's own Claude-backed
   path or the deterministic fallback. Calling Claude-via-chat, which then
   calls ADOS, which then calls Claude again, is real latency and real API
   cost stacked twice. Recommendation, not yet decided: default to the
   deterministic fallback, and only take the LLM path on an explicit user
   ask ("write a persuasive version") — revisit once M4.4 is being built
   and real latency/cost numbers exist.

## 10. Phased rollout

| Phase | Scope | Risk |
|---|---|---|
| **M4.1** | Resources only (§4.1) — read `DesignState`, Project, Brand, Rules, over **stdio** (Claude Code / Claude Desktop; §9 decision 2). Zero write tools. **Shipped.** | Near zero — no new mutation path exists yet. |
| **M4.2** | Write tools that wrap one existing endpoint 1:1: project (`create_project`, `update_project_data`, `attach_brand`), content CRUD (document-private and shared pool), document lifecycle (`create_document`, `compose_document`, `save_version`, `export_document`). AST boundary tests extended (write verbs confined to `client.py`, every write tool calls `get_client()`, `ados-service` stays write-free). **Shipped** — verified against a real `api/main.py` end to end (create → attach brand → content → compose → save version → export), not only against mocks. | Low — every tool already had REST-level tests; MCP tests assert the wrapper, not the logic. |
| **M4.3** | `brand/project/propagation.py` + its two endpoints (`.../content/{id}/propagate`, `.../brand/propagate`) + two MCP tools, called explicitly per §9 decision 1 — never as a side effect of the edit tools in M4.2. Its own AST boundary suite (`tests_brand/test_propagation_boundaries.py`, mirroring `test_loop_boundaries.py`). **Shipped** — pure-domain tests, API tests, MCP-tool tests, and a live end-to-end run against a real `api/main.py` (shared item → select on one of two documents → propagate → only the referencing document recomposes, the other is reported `unaffected`). | Medium — first genuinely new backend logic this milestone added; mitigated by matching M3.6's own boundary-testing discipline from the first commit. |
| **M4.4** | Generative tools (`generate_narrative`, `generate_design_intent`, `generate_commands`, `apply_commands`) and the closed-loop tools, gated by explicit confirmation for non-`SAFE` autonomy. | Medium — cost/latency-visible, but reuses M3.1–M3.6 unchanged. |
| **M4.5** | Brand proposal loop in chat (`propose_brand`/`approve_brand`/`audit_brand`), guidelines/export tools. | Low — human-approval gate already exists; this only relays it. |
| **M4.6** | Remote (HTTP+SSE) transport + bearer-token auth for the claude.ai custom-connector case. | Highest — the one genuinely new piece of infrastructure (ADOS has no auth today). |

## 11. Proposed layout

```
ados_mcp/
  server.py        # tool/resource registration; stdio + HTTP+SSE entrypoints
  client.py         # one httpx wrapper around api/v2 — the ados_mcp/ analogue
                     # of claude_provider.py's get_client(): the one shared,
                     # low-level path every tool call goes through
  resources.py
  tools/
    projects.py  content.py  documents.py  propagation.py  brand.py  generation.py  loop.py
                 #  ^ M4.2      ^ M4.2         ^ M4.3        ^ M4.5    ^ M4.4        ^ M4.4
  auth.py          # bearer-token guard, M4.6 only
tests_mcp/
  test_boundaries.py        # AST: no module imports brand/ or api/routers/
                             # directly, only client.py touches httpx, every
                             # tools/* module calls get_client()
  test_client.py  test_resources.py  test_tools_projects.py  test_tools_content.py
  test_tools_documents.py  test_tools_propagation.py  ...  # one per resources/tools module
docs/architecture/m4-claude-connector.md   # this document
brand/project/propagation.py   # M4.3 — lives under brand/, not ados_mcp/;
                                # see §6 for why the fan-out is domain logic,
                                # not a connector concern
tests_brand/
  test_propagation.py            # pure-domain unit tests
  test_propagation_boundaries.py # AST: only propagation.py calls compose()/
                                  # evaluate() within brand/project/
  test_propagation_api.py        # the two new api/routers/ados_project.py endpoints
```

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

- **No auth exists in ADOS today.** M4.1–M4.5 are safe to run locally
  (stdio, same trust boundary as running `uvicorn` on a laptop already is)
  but are not safe to expose over the network until M4.6 lands.
- **Propagation is document-scoped, not cross-project.** A shared fact
  duplicated by hand across two *different* projects (not the shared pool)
  is out of scope — the same boundary `ADOS-0.3.020`'s own carrier-per-fact-
  class table draws.
- **No per-section correction**, inherited directly from M3.5/M3.6: every
  patch and every propagation target is document-level, because no
  structural bridge from content-reference ids to `ContentModel.ContentBlock.id`
  exists yet anywhere in the shipped system (M3.6 §16). M4 does not invent
  one either.
- **This document does not choose §9's open decisions.** Implementation
  should not start on M4.3 or M4.6 until they are settled.
