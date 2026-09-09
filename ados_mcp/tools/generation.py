"""
ados_mcp/tools/generation.py

ADOS-M4.4 — the M3.1-M3.5 generation pipeline as MCP tools: natural
language in, a validated, structured intermediate object out, at each
stage, never anything executed early. Each tool is a thin wrapper around
one already-shipped, already-tested endpoint; the real generation logic
(and the LLM-vs-deterministic-fallback choice) lives entirely on the
ADOS API side, not here.

**The chain, and what each tool needs from the one before it**:

    generate_semantic_intent   text -> SemanticIntent
            |
            v  (semantic_intent)
    generate_narrative         -> NarrativePlan  (not required downstream)
    generate_design_intent     -> DesignIntent    (not required downstream)
    generate_commands          -> CommandPlan     (needs content_model, below)
            |
            v  (command_plan)
    apply_commands              -> a new plan, NOT persisted (see its own
                                    docstring for how to keep it)

``generate_commands`` and ``apply_commands`` additionally need a
``content_model`` — a ``brand.content.model.ContentModel`` payload, which
is a *different* object from anything ``ados_mcp.tools.content`` produces
(api/routers/command.py's own docstring: "no bridge between the two
exists yet"). The one place to get one is ``compose_document``'s own
response (``ados_mcp.tools.documents.compose_document``), which already
returns ``content_model`` alongside the composed plan — call that first.

**Correction from the design doc's original M4.4 table**
(docs/architecture/m4-claude-connector.md §4.2, §9): the table named
generate_narrative/generate_design_intent/generate_commands/
apply_commands, but every one of them requires a ``semantic_intent`` the
table gave no way to produce. ``generate_semantic_intent`` (wrapping the
M3.1 endpoint, ``POST /intent/semantic``) is added here for the same
reason ``attach_brand`` was added in M4.2: without it, the rest of the
chain has no real input.
"""

from __future__ import annotations

from typing import Any, Optional

from mcp.types import ToolAnnotations

from ados_mcp.client import get_client
from ados_mcp.server import mcp

_CORRECTIONS_DESCRIPTION = (
    "user_corrections: optional list of {key, value, unit?} — a fact the "
    "user has explicitly stated that should override whatever the "
    "pipeline would otherwise infer."
)
_RAW_DOCUMENTS_DESCRIPTION = (
    "raw_documents: optional list of {source_id?, source_type?, label?, "
    "text} — simulated source material (a brief, an email, notes) to "
    "extract additional content from, alongside the project's own stored "
    "content."
)


@mcp.tool(
    description=(
        "Interpret one natural-language request into a validated, "
        "structured SemanticIntent — the typed input every other "
        "generate_* tool needs. Pass project_id (and optionally "
        "document_id) to ground the interpretation in that project's "
        "real state; a bare request with neither is also a normal input. "
        "Returns the intent, its validation report, and which provider "
        "(a real LLM, or the deterministic rule-based fallback used when "
        "no API key is configured on the ADOS server) produced it — say "
        "which one honestly if the user asks, never imply an LLM ran "
        "when the fallback did or vice versa."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def generate_semantic_intent(
    request: str,
    project_id: Optional[str] = None,
    document_id: Optional[str] = None,
    version: Optional[int] = None,
    conversation: Optional[list[dict[str, str]]] = None,
) -> dict:
    """POST /api/v2/intent/semantic."""
    body: dict[str, Any] = {"request": request}
    if project_id is not None:
        body["project_id"] = project_id
    if document_id is not None:
        body["document_id"] = document_id
    if version is not None:
        body["version"] = version
    if conversation is not None:
        body["conversation"] = conversation
    return await get_client().post_api("/intent/semantic", json=body)


def _generation_body(
    semantic_intent: dict[str, Any],
    document_id: Optional[str],
    document_type_id: str,
    version: Optional[int],
    compression: str,
    user_corrections: Optional[list[dict[str, Any]]],
    raw_documents: Optional[list[dict[str, Any]]],
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "semantic_intent": semantic_intent,
        "document_type_id": document_type_id,
        "compression": compression,
    }
    if document_id is not None:
        body["document_id"] = document_id
    if version is not None:
        body["version"] = version
    if user_corrections is not None:
        body["user_corrections"] = user_corrections
    if raw_documents is not None:
        body["raw_documents"] = raw_documents
    return body


@mcp.tool(
    description=(
        "Plan a NarrativePlan — an audience-aware communication strategy "
        "grounded in this project's real, sourced content — from a "
        "SemanticIntent (generate_semantic_intent). Never mutates "
        "anything and never produces a CommandPlan or a PagePlan; purely "
        "a planning stage. compression is 'brief'/'medium'/'extended'. "
        + _CORRECTIONS_DESCRIPTION + " " + _RAW_DOCUMENTS_DESCRIPTION
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def generate_narrative(
    project_id: str,
    semantic_intent: dict[str, Any],
    document_id: Optional[str] = None,
    document_type_id: str = "",
    version: Optional[int] = None,
    compression: str = "medium",
    user_corrections: Optional[list[dict[str, Any]]] = None,
    raw_documents: Optional[list[dict[str, Any]]] = None,
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/narrative/plan."""
    body = _generation_body(
        semantic_intent, document_id, document_type_id, version, compression,
        user_corrections, raw_documents,
    )
    return await get_client().post_api(f"/ados-projects/{project_id}/narrative/plan", json=body)


@mcp.tool(
    description=(
        "Plan a DesignIntent — a brand-consistent visual communication "
        "strategy grounded in the project's real brand and creative "
        "direction — from a SemanticIntent. Internally also plans the "
        "NarrativePlan it's grounded in (both are returned). Requires "
        "document_id if the project's brand/creative-direction context "
        "should be used; without one, brand/direction context is empty. "
        "Never mutates anything, never produces a CommandPlan or PagePlan. "
        "compression is 'brief'/'medium'/'extended'. "
        + _CORRECTIONS_DESCRIPTION + " " + _RAW_DOCUMENTS_DESCRIPTION
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def generate_design_intent(
    project_id: str,
    semantic_intent: dict[str, Any],
    document_id: Optional[str] = None,
    document_type_id: str = "",
    version: Optional[int] = None,
    compression: str = "medium",
    user_corrections: Optional[list[dict[str, Any]]] = None,
    raw_documents: Optional[list[dict[str, Any]]] = None,
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/design/intent."""
    body = _generation_body(
        semantic_intent, document_id, document_type_id, version, compression,
        user_corrections, raw_documents,
    )
    return await get_client().post_api(f"/ados-projects/{project_id}/design/intent", json=body)


@mcp.tool(
    description=(
        "Compile a freshly-resolved DesignIntent (planned internally from "
        "the given semantic_intent) into a validated CommandPlan — never "
        "applies a command, never composes anything. Requires "
        "content_model: a brand.content.model.ContentModel payload, NOT "
        "the same shape as a document's own content items — get one from "
        "compose_document's response (its 'content_model' field) for the "
        "same document_id, called first. document_id should name the "
        "document this plan targets. Returns the command_plan (and its "
        "validation report) plus the design_intent it was compiled from."
        + " " + _CORRECTIONS_DESCRIPTION + " " + _RAW_DOCUMENTS_DESCRIPTION
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def generate_commands(
    project_id: str,
    semantic_intent: dict[str, Any],
    content_model: dict[str, Any],
    document_id: Optional[str] = None,
    document_type_id: str = "",
    version: Optional[int] = None,
    compression: str = "medium",
    user_corrections: Optional[list[dict[str, Any]]] = None,
    raw_documents: Optional[list[dict[str, Any]]] = None,
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/commands/generate."""
    body = _generation_body(
        semantic_intent, document_id, document_type_id, version, compression,
        user_corrections, raw_documents,
    )
    body["content_model"] = content_model
    return await get_client().post_api(f"/ados-projects/{project_id}/commands/generate", json=body)


@mcp.tool(
    description=(
        "Apply some or all of a CommandPlan's commands (generate_commands) "
        "through ADOS's real validate-then-apply-then-compose pipeline, "
        "in order — the first failure stops the sequence and reports "
        "everything applied up to that point. Requires the SAME "
        "content_model passed to generate_commands, and exactly one of "
        "base_direction_id (an existing CreativeDirection id, e.g. "
        "'editorial-quiet') or base_direction (a full CreativeDirection "
        "payload). command_ids optionally restricts which commands to "
        "apply and in what order; omit it to apply the whole plan. "
        "IMPORTANT: this does NOT save anything to the project or "
        "document — it is a preview computation. To keep the result, "
        "call save_version(project_id, document_id, plan=<this result's "
        "final_plan>) afterward, the same way any other composed plan is "
        "kept (docs/architecture/m3.5-command-generation.md: no "
        "CommandPlan is persisted by this stage itself)."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def apply_commands(
    project_id: str,
    command_plan: dict[str, Any],
    content_model: dict[str, Any],
    base_direction_id: Optional[str] = None,
    base_direction: Optional[dict[str, Any]] = None,
    base_plan: Optional[dict[str, Any]] = None,
    page_format_name: str = "A4",
    command_ids: Optional[list[str]] = None,
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/commands/apply."""
    body: dict[str, Any] = {
        "command_plan": command_plan,
        "content_model": content_model,
        "page_format_name": page_format_name,
    }
    if base_direction_id is not None:
        body["base_direction_id"] = base_direction_id
    if base_direction is not None:
        body["base_direction"] = base_direction
    if base_plan is not None:
        body["base_plan"] = base_plan
    if command_ids is not None:
        body["command_ids"] = command_ids
    return await get_client().post_api(f"/ados-projects/{project_id}/commands/apply", json=body)
