"""
ados_mcp/resources.py

ADOS-M4.1 (docs/architecture/m4-claude-connector.md §4.1, §10) — the
read-only MCP resource surface. Every function below is a thin GET
wrapper around one already-shipped, already-tested endpoint; none of them
mutate anything, and none of them import ``brand`` or ``api.routers``
directly — only ``ados_mcp.client.AdosClient`` (``tests_mcp/test_boundaries.py``).

A resource whose URI contains a ``{param}`` becomes an MCP *resource
template*: the connected client resolves the id (e.g. by reading
``ados://projects`` first, or from a project the user already named) and
requests the templated URI with it filled in — see ``FastMCP.resource``'s
own docstring for the mechanics.
"""

from __future__ import annotations

from ados_mcp.client import get_client
from ados_mcp.server import mcp


@mcp.resource(
    "ados://projects",
    name="ADOS projects",
    description="Every ADOS project, most recently updated first.",
    mime_type="application/json",
)
async def list_projects() -> dict:
    """GET /api/v2/ados-projects."""
    return await get_client().get_api("/ados-projects")


@mcp.resource(
    "ados://projects/{project_id}",
    name="ADOS project",
    description="One project's facts: name, description, project_data, brand link, document ids.",
    mime_type="application/json",
)
async def get_project(project_id: str) -> dict:
    """GET /api/v2/ados-projects/{project_id}."""
    return await get_client().get_api(f"/ados-projects/{project_id}")


@mcp.resource(
    "ados://projects/{project_id}/content",
    name="ADOS shared content pool",
    description=(
        "The project-level shared ContentItem pool — the real mechanism behind "
        "ADOS-0.3.020 'one fact, one place': a fact recorded here can be "
        "selected into more than one document (brand/README.md, "
        "docs/architecture/m2.5-design-state.md §5)."
    ),
    mime_type="application/json",
)
async def get_shared_content(project_id: str) -> dict:
    """GET /api/v2/ados-projects/{project_id}/content."""
    return await get_client().get_api(f"/ados-projects/{project_id}/content")


@mcp.resource(
    "ados://projects/{project_id}/documents/{document_id}/design-state",
    name="ADOS DesignState",
    description=(
        "The single deterministic source of truth for one document: Project, "
        "Brand, Content, Document, Page/Component/Layout, VisualLanguage, "
        "Asset, Constraint and Version state, assembled fresh from real "
        "persisted state on every read (docs/architecture/m2.5-design-state.md). "
        "Read this before answering any question about a specific document."
    ),
    mime_type="application/json",
)
async def get_design_state(project_id: str, document_id: str) -> dict:
    """GET /api/v2/ados-projects/{project_id}/documents/{document_id}/design-state."""
    return await get_client().get_api(
        f"/ados-projects/{project_id}/documents/{document_id}/design-state"
    )


@mcp.resource(
    "ados://brands/{brand_id}",
    name="ADOS brand",
    description=(
        "A brand's identity fields plus its fully resolved design tokens, "
        "each carrying its provenance and, where ADOS bounded it, the rule "
        "(brand/README.md's token-namespace example)."
    ),
    mime_type="application/json",
)
async def get_brand(brand_id: str) -> dict:
    """GET /api/v2/brands/{brand_id} + GET /api/v2/brands/{brand_id}/tokens."""
    client = get_client()
    brand = await client.get_api(f"/brands/{brand_id}")
    tokens = await client.get_api(f"/brands/{brand_id}/tokens")
    return {"brand": brand, "tokens": tokens}


@mcp.resource(
    "ados://rules",
    name="ADOS 1.0 rule registry",
    description=(
        "The ADOS 1.0 specification's own 476-rule registry (docs/ados/), "
        "so a real ADOS-x.y.zzz rule can be cited instead of an invented "
        "justification. Served by ados-service, not duplicated here."
    ),
    mime_type="application/json",
)
async def get_rules() -> dict:
    """GET /api/rules on ados-service."""
    return await get_client().get_service("/api/rules")


# ---------------------------------------------------------------------------
# Closed-loop lineage (ADOS-M4.4) — read-only inspection of what
# ados_mcp.tools.loop's tools have produced. Added alongside those tools
# (not in the original M4.1 resource table) because approve_loop's own
# tool description tells the connecting model to check these before
# approving anything — a reference that needs something real to resolve
# to.
# ---------------------------------------------------------------------------


@mcp.resource(
    "ados://projects/{project_id}/documents/{document_id}/loop",
    name="ADOS closed-loop lineage",
    description=(
        "The full iteration history for one document's closed-loop lineage "
        "(started by start_loop/run_loop) — every Iteration in full, in "
        "order. Empty if no lineage has been started. Read this before "
        "calling continue_loop or approve_loop so a decision is grounded "
        "in what the loop actually found, not assumed."
    ),
    mime_type="application/json",
)
async def get_loop_history(project_id: str, document_id: str) -> dict:
    """GET /api/v2/ados-projects/{project_id}/documents/{document_id}/loop."""
    return await get_client().get_api(f"/ados-projects/{project_id}/documents/{document_id}/loop")


@mcp.resource(
    "ados://projects/{project_id}/documents/{document_id}/loop/{iteration_id}/trace",
    name="ADOS closed-loop iteration trace",
    description=(
        "One iteration's condensed decision trace: what stage it reached, "
        "why it stopped (or didn't), its findings/recommendations/skipped "
        "recommendations, and its LLM call count — without the full "
        "embedded DesignIntent/CommandPlan/PagePlan payloads the lineage "
        "resource carries for the same iteration. Prefer this for "
        "explaining a loop's outcome to a person; use the lineage "
        "resource when the full objects are actually needed."
    ),
    mime_type="application/json",
)
async def get_loop_iteration_trace(project_id: str, document_id: str, iteration_id: str) -> dict:
    """GET /api/v2/ados-projects/{project_id}/documents/{document_id}/loop/{iteration_id}/trace."""
    return await get_client().get_api(
        f"/ados-projects/{project_id}/documents/{document_id}/loop/{iteration_id}/trace"
    )
