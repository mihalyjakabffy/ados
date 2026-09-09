"""
ados_mcp/tools/brand.py

ADOS-M4.5 — the brand proposal loop in chat, plus auditing an
already-generated package against a brand. Each tool is a thin wrapper
around one endpoint in api/routers/brand.py; ``audit_brand`` is backed by
a new endpoint (``POST /brands/{brand_id}/audit``) added alongside this
tool, wrapping ``brand.validation.consistency.audit_package`` — already
real, tested domain code with no HTTP door before now, the same posture
ADOS-M4.3's propagation endpoints took for `brand/project/propagation.py`.

**"AI proposes, the user approves" (brand/README.md Rule 3) is the whole
point of splitting these into two tools.** `propose_brand` never writes
anything; `approve_brand` is the one call that does, and it requires a
named human — never let the calling model supply its own name or a
placeholder for `approved_by`.

**Correction from the design doc's original M4.5 plan**
(docs/architecture/m4-claude-connector.md §10): "guidelines/export
tools" were mentioned in the phase description but never given a
concrete shape in the §4.2 tool table, and no endpoint exists for either
today (`brand.guidelines.generator`/`brand.export.exporters` are
CLI-only). Rather than design a new endpoint shape for them
speculatively, this phase ships exactly what §4.2 specified —
`propose_brand`, `approve_brand`, `audit_brand` — and leaves
guidelines/export as a stated, deferred gap (see the design doc).
"""

from __future__ import annotations

from typing import Any, Optional

from mcp.types import ToolAnnotations

from ados_mcp.client import get_client
from ados_mcp.server import mcp


@mcp.tool(
    description=(
        "Generate a candidate brand identity from a brief — personality, "
        "typography, colour, architectural language (brand/README.md) — "
        "using ADOS's own BrandAgent. Returns the proposed brand, its "
        "rationale, confidence, assumptions, open questions, and its "
        "validation report. NOTHING IS SAVED. Present the proposal (and "
        "especially its open_questions) to the user; never call "
        "approve_brand on your own initiative — only once they have "
        "actually reviewed and agreed to it."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def propose_brand(brief: str, name: Optional[str] = None) -> dict:
    """POST /api/v2/brand-proposals."""
    body: dict[str, Any] = {"brief": brief}
    if name is not None:
        body["name"] = name
    return await get_client().post_api("/brand-proposals", json=body)


@mcp.tool(
    description=(
        "Turn a proposal from propose_brand into a stored, approved "
        "brand — the one step that writes anything. approved_by MUST be "
        "the real name of the person approving it; ask the user for "
        "their name if it isn't already in the conversation, and never "
        "fill in your own name or a placeholder — an unnamed approval is "
        "refused by ADOS itself, and a fabricated one defeats the whole "
        "point of this gate. Refused (409) if the proposal does not "
        "validate. Pass proposal exactly as propose_brand returned it "
        "(or just its 'brand' field), unmodified unless the user asked "
        "for a specific change."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def approve_brand(proposal: dict[str, Any], approved_by: str) -> dict:
    """POST /api/v2/brand-proposals/approve?approved_by=..."""
    return await get_client().post_api(
        "/brand-proposals/approve", json=proposal, params={"approved_by": approved_by}
    )


@mcp.tool(
    description=(
        "Audit a generated package of brand artefacts already on disk "
        "against a brand — checks that the files (colours, fonts, "
        "layout, the asset inventory) actually derive from the brand "
        "they claim to come from. A separate, later question from "
        "whether the brand itself validates (ados://brands/{brand_id} "
        "carries that report already). package_dir is a path on the "
        "machine running the ADOS API server — the same local trust "
        "boundary this whole connector runs under today."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
)
async def audit_brand(brand_id: str, package_dir: str, version: Optional[str] = None) -> dict:
    """POST /api/v2/brands/{brand_id}/audit."""
    params = {"version": version} if version is not None else None
    return await get_client().post_api(
        f"/brands/{brand_id}/audit", json={"package_dir": package_dir}, params=params
    )
