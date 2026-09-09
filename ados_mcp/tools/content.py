"""
ados_mcp/tools/content.py

ADOS-M4.2 — content write tools: a document's own private content items,
the project-level shared pool (ADOS-0.3.020's "one fact, one place"
carrier — see docs/architecture/m2.5-design-state.md §5), and which of
the pool's items a given document selects.

A shared item can be added and removed here but not yet *updated* in
place — ``api/routers/ados_project.py`` still has no PATCH for one shared
``ContentItem``; ADOS-M4.3 added the recompose-everywhere mechanism
(``ados_mcp.tools.propagation``) without needing one, since it operates
on "this item id changed or is gone", not on the edit itself. Editing a
shared fact today is still remove + re-add (a new id — every document's
``content_selection`` referencing the old one goes stale and must be
re-selected); a real in-place update endpoint remains a gap, tracked in
docs/architecture/m4-claude-connector.md §6, §9.
"""

from __future__ import annotations

from typing import Any, Optional

from mcp.types import ToolAnnotations

from ados_mcp.client import get_client
from ados_mcp.server import mcp

_CONTENT_ITEM_DESCRIPTION = (
    "kind is one of ContentItem's four kinds: 'text' (a prose block, uses "
    "the text field), 'fact' (a short labelled statement, uses text/value), "
    "'metric' (a number with a unit, uses value/unit and should carry "
    "provenance), or 'image' (uses asset_id/caption/aspect). label / text / "
    "value / unit / provenance / asset_id / caption / aspect are all "
    "optional and kind-dependent; a metric should carry provenance, since a "
    "number with no stated origin is refused by the same validation the "
    "Composer itself runs — the refusal happens here, not silently later."
)


def _content_item_body(
    kind: str,
    label: str,
    text: str,
    value: Optional[float | str],
    unit: str,
    provenance: str,
    asset_id: Optional[str],
    caption: str,
    aspect: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "text": text,
        "value": value,
        "unit": unit,
        "provenance": provenance,
        "asset_id": asset_id,
        "caption": caption,
        "aspect": aspect,
    }


@mcp.tool(
    description=(
        "Add a content item to one document's own, private content (not "
        "the project's shared pool — see add_shared_content for a fact "
        "more than one document should carry). " + _CONTENT_ITEM_DESCRIPTION + " "
        "Returns the updated document."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def add_document_content(
    project_id: str,
    document_id: str,
    kind: str,
    label: str = "",
    text: str = "",
    value: Optional[float | str] = None,
    unit: str = "",
    provenance: str = "",
    asset_id: Optional[str] = None,
    caption: str = "",
    aspect: str = "",
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/documents/{document_id}/content."""
    body = _content_item_body(kind, label, text, value, unit, provenance, asset_id, caption, aspect)
    return await get_client().post_api(
        f"/ados-projects/{project_id}/documents/{document_id}/content", json=body
    )


@mcp.tool(
    description="Remove one content item from a document's own private content. Returns the updated document.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False),
)
async def remove_document_content(project_id: str, document_id: str, item_id: str) -> dict:
    """DELETE /api/v2/ados-projects/{project_id}/documents/{document_id}/content/{item_id}."""
    return await get_client().delete_api(
        f"/ados-projects/{project_id}/documents/{document_id}/content/{item_id}"
    )


@mcp.tool(
    description=(
        "Add a content item to the project's shared pool — a fact more than "
        "one document can carry by selecting it (select_content_for_document). "
        "After a document selects it, call propagate_content_change with "
        "this item's id to recompose every document that references it "
        "(ADOS-0.3.020, 'one fact, one place') — nothing recomposes "
        "automatically just because the pool changed. " + _CONTENT_ITEM_DESCRIPTION + " "
        "Returns the updated project."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def add_shared_content(
    project_id: str,
    kind: str,
    label: str = "",
    text: str = "",
    value: Optional[float | str] = None,
    unit: str = "",
    provenance: str = "",
    asset_id: Optional[str] = None,
    caption: str = "",
    aspect: str = "",
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/content."""
    body = _content_item_body(kind, label, text, value, unit, provenance, asset_id, caption, aspect)
    return await get_client().post_api(f"/ados-projects/{project_id}/content", json=body)


@mcp.tool(
    description=(
        "Remove one item from the project's shared content pool. A document "
        "still selecting it keeps a dangling reference that is silently "
        "skipped on its next compose, never a 500 — check "
        "ados://projects/{project_id}/content first if that matters. "
        "Returns the updated project."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False),
)
async def remove_shared_content(project_id: str, item_id: str) -> dict:
    """DELETE /api/v2/ados-projects/{project_id}/content/{item_id}."""
    return await get_client().delete_api(f"/ados-projects/{project_id}/content/{item_id}")


@mcp.tool(
    description=(
        "Replace the complete set of shared content items a document "
        "includes — every id must already exist in the project's shared "
        "pool (ados://projects/{project_id}/content). This replaces the "
        "whole selection at once, not an incremental add/remove: pass every "
        "id the document should keep, not just a new one. Returns the "
        "updated document."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
)
async def select_content_for_document(
    project_id: str, document_id: str, content_item_ids: list[str]
) -> dict:
    """PUT /api/v2/ados-projects/{project_id}/documents/{document_id}/content-selection."""
    return await get_client().put_api(
        f"/ados-projects/{project_id}/documents/{document_id}/content-selection",
        json={"content_item_ids": content_item_ids},
    )
