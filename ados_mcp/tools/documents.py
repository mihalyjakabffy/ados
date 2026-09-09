"""
ados_mcp/tools/documents.py

ADOS-M4.2 — document lifecycle write tools: create a document (choosing a
DocumentType projection, docs/architecture/m4-claude-connector.md §7),
compose it through the real, unmodified, deterministic Composer
(``brand.creative.composer.compose``, reached only via the existing
``POST .../compose`` endpoint — never imported directly here), save an
immutable Version, and export a PDF or Website.
"""

from __future__ import annotations

from typing import Any, Optional

from mcp.types import ToolAnnotations

from ados_mcp.client import get_client
from ados_mcp.server import mcp


@mcp.tool(
    description=(
        "Create a document inside a project. document_type_id selects a "
        "projection from the document-type registry (GET "
        "/api/v2/ados-projects/document-types lists them — e.g. "
        "'project-report', 'investor-deck', 'tender-document'); pick the "
        "one matching what the document is for, or leave it empty for an "
        "untyped, free-form document. direction_id overrides the type's "
        "own default composition profile ('editorial-quiet' / "
        "'technical-dense' / 'image-led'); omit it to use the type's "
        "default (or 'editorial-quiet' if untyped). metadata is a free bag "
        "for the brief — subtitle, author, date, audience, client, and "
        "so on. Returns the created document; it has no content yet — add "
        "some with add_document_content or select_content_for_document "
        "before calling compose_document."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def create_document(
    project_id: str,
    name: str,
    document_type_id: str = "",
    direction_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/documents."""
    body: dict[str, Any] = {
        "name": name,
        "document_type_id": document_type_id,
        "metadata": metadata or {},
    }
    if direction_id is not None:
        body["direction_id"] = direction_id
    return await get_client().post_api(f"/ados-projects/{project_id}/documents", json=body)


@mcp.tool(
    description=(
        "Compose a document: run ADOS's real, deterministic layout engine "
        "over its current content and creative direction, under the "
        "project's attached brand, then evaluate the result. Requires a "
        "brand attached (attach_brand) and at least one content item "
        "(add_document_content or select_content_for_document). Returns "
        "the composed plan, its evaluation findings, and requirement "
        "findings (e.g. a document type's required section missing). "
        "Nothing is persisted as a Version until save_version is called — "
        "recomposing again before that simply discards the previous, "
        "unsaved result."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def compose_document(project_id: str, document_id: str) -> dict:
    """POST /api/v2/ados-projects/{project_id}/documents/{document_id}/compose."""
    return await get_client().post_api(f"/ados-projects/{project_id}/documents/{document_id}/compose")


@mcp.tool(
    description=(
        "Save the document's current composed state as a new, immutable "
        "Version — the only thing export_document can render. Pass the "
        "exact plan compose_document just returned as `plan` to capture "
        "precisely what was reviewed; omit it to save the document's "
        "already-cached last-composed plan instead. label is a short, "
        "human note (e.g. 'first draft for client review')."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def save_version(
    project_id: str, document_id: str, label: str = "", plan: Optional[dict[str, Any]] = None
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/versions."""
    body: dict[str, Any] = {"document_id": document_id, "label": label}
    if plan is not None:
        body["plan"] = plan
    return await get_client().post_api(f"/ados-projects/{project_id}/versions", json=body)


@mcp.tool(
    description=(
        "Render a saved Version to a production artefact: 'pdf' (printed "
        "through Chromium) or 'html' (the Website projection — the same "
        "composed output, written out directly, no Chromium involved). "
        "Pass version_number to export a specific already-saved Version; "
        "omit it to export the document's current state (a fresh Version "
        "is saved first). A blocking finding (ERROR/BLOCK severity) "
        "produces a BLOCKED export with no file, never a silently "
        "incomplete one — check the findings in the response. Returns the "
        "Export record (id, status, findings); the rendered file itself "
        "stays in ADOS's own storage, not inlined into this response."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def export_document(
    project_id: str,
    document_id: str,
    version_number: Optional[int] = None,
    format: str = "pdf",
) -> dict:
    """POST /api/v2/ados-projects/{project_id}/documents/{document_id}/export."""
    body: dict[str, Any] = {"format": format}
    if version_number is not None:
        body["version_number"] = version_number
    return await get_client().post_api(
        f"/ados-projects/{project_id}/documents/{document_id}/export", json=body
    )
