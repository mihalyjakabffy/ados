"""
ados_mcp/tools/loop.py

ADOS-M4.4 — the ADOS-M3.6 closed loop (observe, find, recommend, patch,
act, repeat) as MCP tools. Every tool is a thin wrapper around one
already-shipped, already-tested api/routers/closed_loop.py endpoint; the
loop's own safety machinery (bounded iterations/LLM calls, the autonomy
gate, the stale-state check) is entirely on the ADOS side, unchanged and
unbypassable from here.

**autonomy is the real safety gate, already built (ADOS-M3.6 §37/§38) —
this package adds no second one.** It defaults to 'safe' here, exactly
the API's own default: 'safe' auto-executes only SAFE-labelled commands
and stops every REVIEW_RECOMMENDED/DESTRUCTIVE one at AWAITING_APPROVAL
for approve_loop to resume explicitly. Pass 'full' only when the user has
explicitly asked for unattended execution — it auto-executes everything
M3.5's own validator accepts, never a relaxation of that validation
itself, only of who has to say yes. 'none' never auto-executes anything;
'recommend' generates commands but always requires approval regardless of
their safety label.

Unlike the M4.4 generation tools, every loop tool DOES persist — a
successful start/continue/run/approve saves the composed plan and an
updated iteration lineage the same way compose_document/save_version
already do (api/routers/closed_loop.py's own docstring). dry_run=True on
start/continue/run computes everything in memory and saves nothing, for
a genuine preview.
"""

from __future__ import annotations

from typing import Any, Optional

from mcp.types import ToolAnnotations

from ados_mcp.client import get_client
from ados_mcp.server import mcp

_POLICY_DESCRIPTION = (
    "max_iterations (default 5), autonomy ('none'/'recommend'/'safe' "
    "default/'full'), max_llm_calls (default 10), "
    "allow_llm_recommendation (default true), "
    "max_repeated_recommendation_attempts (default 2) — every budget in "
    "one place; pass only the ones that differ from the default."
)


def _policy_body(
    max_iterations: int,
    autonomy: str,
    max_llm_calls: int,
    allow_llm_recommendation: bool,
    max_repeated_recommendation_attempts: int,
) -> dict[str, Any]:
    return {
        "max_iterations": max_iterations,
        "autonomy": autonomy,
        "max_llm_calls": max_llm_calls,
        "allow_llm_recommendation": allow_llm_recommendation,
        "max_repeated_recommendation_attempts": max_repeated_recommendation_attempts,
    }


@mcp.tool(
    description=(
        "Start a fresh closed-loop lineage on one document: plan a "
        "DesignIntent from semantic_intent, compile and (per autonomy) "
        "execute commands, compose, evaluate, and record one Iteration. "
        "409s if this document already has a lineage — use continue_loop "
        "or run_loop instead, or stop_loop first to abandon it. Requires "
        "a brand attached (attach_brand) and real content on the "
        "document already (add_document_content / "
        "select_content_for_document) — content is resolved from the "
        "project's own real state, not supplied inline. Set dry_run=true "
        "to compute everything without saving anything. " + _POLICY_DESCRIPTION
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def start_loop(
    project_id: str,
    document_id: str,
    semantic_intent: dict[str, Any],
    document_type_id: str = "",
    compression: str = "medium",
    raw_documents: Optional[list[dict[str, Any]]] = None,
    user_corrections: Optional[list[dict[str, Any]]] = None,
    max_iterations: int = 5,
    autonomy: str = "safe",
    max_llm_calls: int = 10,
    allow_llm_recommendation: bool = True,
    max_repeated_recommendation_attempts: int = 2,
    dry_run: bool = False,
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/documents/{document_id}/loop/start."""
    body: dict[str, Any] = {
        "semantic_intent": semantic_intent,
        "document_type_id": document_type_id,
        "compression": compression,
        "policy": _policy_body(
            max_iterations, autonomy, max_llm_calls,
            allow_llm_recommendation, max_repeated_recommendation_attempts,
        ),
        "dry_run": dry_run,
    }
    if raw_documents is not None:
        body["raw_documents"] = raw_documents
    if user_corrections is not None:
        body["user_corrections"] = user_corrections
    return await get_client().post_api(
        f"/ados-projects/{project_id}/documents/{document_id}/loop/start", json=body
    )


@mcp.tool(
    description=(
        "Run the next iteration in an existing, still-open lineage — "
        "404s if none exists (call start_loop first), 409s if the last "
        "iteration already stopped or is awaiting approval (call "
        "approve_loop or stop_loop first). " + _POLICY_DESCRIPTION
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def continue_loop(
    project_id: str,
    document_id: str,
    max_iterations: int = 5,
    autonomy: str = "safe",
    max_llm_calls: int = 10,
    allow_llm_recommendation: bool = True,
    max_repeated_recommendation_attempts: int = 2,
    dry_run: bool = False,
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/documents/{document_id}/loop/continue."""
    body: dict[str, Any] = {
        "policy": _policy_body(
            max_iterations, autonomy, max_llm_calls,
            allow_llm_recommendation, max_repeated_recommendation_attempts,
        ),
        "dry_run": dry_run,
    }
    return await get_client().post_api(
        f"/ados-projects/{project_id}/documents/{document_id}/loop/continue", json=body
    )


@mcp.tool(
    description=(
        "Start a fresh lineage AND run it to completion in one call — "
        "the convenience 'just do the whole loop' tool, equivalent to "
        "start_loop followed by continue_loop until a terminal status. "
        "409s if a lineage already exists (call continue_loop/stop_loop "
        "instead). Always persists (no dry_run — for a preview, use "
        "start_loop with dry_run=true first). Returns every iteration, "
        "the final status/stop_reason, and the total LLM call count "
        "across all of them — report that count if the user is tracking "
        "cost. " + _POLICY_DESCRIPTION
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def run_loop(
    project_id: str,
    document_id: str,
    semantic_intent: dict[str, Any],
    document_type_id: str = "",
    compression: str = "medium",
    raw_documents: Optional[list[dict[str, Any]]] = None,
    user_corrections: Optional[list[dict[str, Any]]] = None,
    max_iterations: int = 5,
    autonomy: str = "safe",
    max_llm_calls: int = 10,
    allow_llm_recommendation: bool = True,
    max_repeated_recommendation_attempts: int = 2,
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/documents/{document_id}/loop/run."""
    body: dict[str, Any] = {
        "semantic_intent": semantic_intent,
        "document_type_id": document_type_id,
        "compression": compression,
        "policy": _policy_body(
            max_iterations, autonomy, max_llm_calls,
            allow_llm_recommendation, max_repeated_recommendation_attempts,
        ),
    }
    if raw_documents is not None:
        body["raw_documents"] = raw_documents
    if user_corrections is not None:
        body["user_corrections"] = user_corrections
    return await get_client().post_api(
        f"/ados-projects/{project_id}/documents/{document_id}/loop/run", json=body
    )


@mcp.tool(
    description=(
        "Approve and execute some or all of a pending AWAITING_APPROVAL "
        "iteration's commands — 409s if nothing is awaiting approval. "
        "command_ids restricts approval to specific commands; omit it to "
        "approve everything pending. This is the human-in-the-loop step "
        "for anything a 'safe' (or stricter) autonomy policy held back — "
        "only call it once the user has actually reviewed and agreed to "
        "what loop_history / the last iteration's findings describe, "
        "never as a reflexive follow-up to start_loop/continue_loop."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def approve_loop(
    project_id: str, document_id: str, command_ids: Optional[list[str]] = None
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/documents/{document_id}/loop/approve."""
    body: dict[str, Any] = {}
    if command_ids is not None:
        body["command_ids"] = command_ids
    return await get_client().post_api(
        f"/ados-projects/{project_id}/documents/{document_id}/loop/approve", json=body
    )


@mcp.tool(
    description=(
        "Mark the current lineage as user-stopped — continue_loop refuses "
        "to advance it further afterward. Does not undo anything already "
        "executed and composed; it only ends the lineage. A no-op "
        "(returns the same terminal state) if the lineage already "
        "stopped for any reason."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
)
async def stop_loop(project_id: str, document_id: str) -> dict:
    """POST /api/v2/ados-projects/{project_id}/documents/{document_id}/loop/stop."""
    return await get_client().post_api(
        f"/ados-projects/{project_id}/documents/{document_id}/loop/stop"
    )
