"""
ados_mcp/tools/projects.py

ADOS-M4.2 — project-level write tools. Each wraps one endpoint in
``api/routers/ados_project.py`` unchanged; see that module's own request
models (``CreateProjectRequest``, ``UpdateProjectRequest``,
``AttachBrandRequest``) for the exact shape each one validates against.
"""

from __future__ import annotations

from typing import Any, Optional

from mcp.types import ToolAnnotations

from ados_mcp.client import get_client
from ados_mcp.server import mcp


@mcp.tool(
    description=(
        "Create a new ADOS project. Returns the created project. A fresh "
        "project has no brand and no documents yet — attach a brand with "
        "attach_brand and create a document with create_document before "
        "anything can be composed."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def create_project(name: str, description: str = "") -> dict:
    """POST /api/v2/ados-projects."""
    return await get_client().post_api("/ados-projects", json={"name": name, "description": description})


@mcp.tool(
    description=(
        "Update a project's name, description and/or project_data. "
        "project_data is merged into the existing bag, never replaces it "
        "wholesale — pass only the keys that changed. Omit a parameter "
        "entirely to leave that field unchanged."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
)
async def update_project_data(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    project_data: Optional[dict[str, Any]] = None,
) -> dict:
    """PATCH /api/v2/ados-projects/{project_id}."""
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if project_data is not None:
        body["project_data"] = project_data
    return await get_client().patch_api(f"/ados-projects/{project_id}", json=body)


@mcp.tool(
    description=(
        "Attach an existing, already-approved brand to a project, by id "
        "and optionally a specific version (omit the version to always "
        "track that brand's latest usable one). A project needs a brand "
        "attached before compose_document or export_document will work. "
        "This does not create or change a brand — read "
        "ados://brands/{brand_id} to find one first."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
)
async def attach_brand(project_id: str, brand_id: str, brand_version: Optional[str] = None) -> dict:
    """PUT /api/v2/ados-projects/{project_id}/brand."""
    body: dict[str, Any] = {"brand_id": brand_id}
    if brand_version is not None:
        body["brand_version"] = brand_version
    return await get_client().put_api(f"/ados-projects/{project_id}/brand", json=body)
