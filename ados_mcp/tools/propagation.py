"""
ados_mcp/tools/propagation.py

ADOS-M4.3 — the "one fact, one place, update everywhere" tools
(docs/architecture/m4-claude-connector.md §6, §9 decision 1). Each wraps
one endpoint in api/routers/ados_project.py that itself calls the new
brand.project.propagation module — no logic here, no direct import of
brand/ or api/routers/, same as every other tool in this package.

Explicit, not automatic (§9 decision 1): neither add_shared_content,
remove_shared_content nor attach_brand triggers either tool below by
itself. A content edit is instant and scoped to the item; propagation is
a second, visible call — so relay what changed as a distinct step
("3 documents reference this fact — recompose them?"), never imply it
already happened.
"""

from __future__ import annotations

from mcp.types import ToolAnnotations

from ados_mcp.client import get_client
from ados_mcp.server import mcp


@mcp.tool(
    description=(
        "Recompose every document in a project that references a shared "
        "content item — call this right after editing that fact (today: "
        "remove_shared_content + add_shared_content, since there is no "
        "in-place update yet) or removing it outright, so every document "
        "that selected it picks up the change instead of silently "
        "drifting until its own next compose_document call. Returns "
        "which documents were recomposed (with their new findings) and "
        "which don't reference the item and were left alone. A document "
        "left with no content after the change is reported as "
        "recomposed=false, reason='no_content' — never a crash, and "
        "never silently skipped. Nothing is saved as a Version; call "
        "save_version per document afterward for an immutable snapshot."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def propagate_content_change(project_id: str, item_id: str) -> dict:
    """POST /api/v2/ados-projects/{project_id}/content/{item_id}/propagate."""
    return await get_client().post_api(f"/ados-projects/{project_id}/content/{item_id}/propagate")


@mcp.tool(
    description=(
        "Move a project onto an already-published version of its own "
        "brand and recompose every one of its documents against it. "
        "Brands are immutable per published version — this never edits "
        "a brand in place, it only moves the project's pointer to a "
        "version that must already exist and be published (see "
        "ados://brands/{brand_id} for what's available). Every document "
        "in the project shares the one brand, so every document is "
        "recomposed — there is no 'unaffected' set for this operation, "
        "unlike propagate_content_change. Nothing is saved as a "
        "Version; call save_version per document afterward for an "
        "immutable snapshot."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def propagate_brand_change(project_id: str, brand_version: str) -> dict:
    """POST /api/v2/ados-projects/{project_id}/brand/propagate."""
    return await get_client().post_api(
        f"/ados-projects/{project_id}/brand/propagate", json={"brand_version": brand_version}
    )
