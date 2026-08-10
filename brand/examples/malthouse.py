"""
brand/examples/malthouse.py

The Malthouse: one project, as content.

A worked example in the same spirit as ``studio_nord`` and ``studio_om`` — a
real-shaped set of facts, authored once, so that the Creative Layer can be
exercised against something with the texture of an actual project rather than
against three paragraphs of placeholder.

Everything derivable is derived. The design state carries the areas, the code
checks, the budget, the materials and the storey count, and the extractor
lifts them with their provenance attached. The prose and the figure list are
authored, because ``DesignState`` holds neither and inventing them would put
sentences nobody wrote into a client document.

The identifiers are fixed rather than generated. A content model whose hash
changed on every import could not be used to demonstrate that two runs produce
the same document, which is the property the whole layer exists to have.
"""

from __future__ import annotations

import uuid

from brand.content.extract import extract_content
from brand.content.model import BlockRole, ContentModel

PROJECT_ID = uuid.UUID("b1a17400-0000-4000-8000-000000000001")
DESIGN_STATE_ID = uuid.UUID("b1a17400-0000-4000-8000-000000000002")

#: A stand-in content hash. In the platform this is computed by
#: ``DesignState.compute_content_hash``; pinned here so the example is stable.
STATE_HASH = "8f3a1c04b7e25d6190ac4f7b23e8d051c6a9b4f2e7d3081a5c6b9e0f4a2d7c83"


NARRATIVE: tuple[tuple[BlockRole, str], ...] = (
    (
        BlockRole.CONTEXT,
        "A 1904 malthouse on the edge of the town's former industrial quarter, "
        "built to germinate barley on three timber floors and abandoned in "
        "1987. The brick shell is sound and the cast-iron columns are intact. "
        "The roof is not: two bays collapsed in the winter of 2019 and the "
        "remainder was condemned in the survey that followed.",
    ),
    (
        BlockRole.PROBLEM,
        "The building is listed, the floor plates carry a live load of "
        "1.5 kN/m² against the 4.0 required for public assembly, and the "
        "envelope has no insulation of any kind. Any scheme that meets the "
        "brief has to add structure and fabric without concealing the two "
        "things the listing protects: the column grid and the daylight from "
        "the north.",
    ),
    (
        BlockRole.INTERVENTION,
        "A new steel frame stands inside the shell on independent pads, "
        "carrying the new floors clear of the historic masonry. The original "
        "timber floors are retained where sound and read as a second, "
        "lighter layer beneath the new. Insulation is applied internally to "
        "the gables only, leaving the north elevation as found and taking "
        "the heat loss on the plant instead.",
    ),
    (
        BlockRole.INTERVENTION,
        "The roof is rebuilt to the original profile in glue-laminated "
        "timber, with a continuous rooflight along the ridge where the "
        "kiln vents were. The new frame is left exposed and unpainted, so "
        "that what is new is legible as new at a glance and no one has to "
        "consult a drawing to read the building.",
    ),
    (
        BlockRole.OUTCOME,
        "The building reopened as a workshop and exhibition space with a "
        "public route through the full depth of the plan. Measured energy "
        "use in the first full year came in below the design estimate, and "
        "the retained structure avoided the embodied carbon of a "
        "replacement frame.",
    ),
)


FIGURES: tuple[dict, ...] = (
    {
        "path": "projects/malthouse/01-context.jpg",
        "aspect": "3:2",
        "role": "context",
        "priority": 1,
        "caption": "The malthouse from the yard, before work.",
        "sequence_position": "context",
        "provenance": "site photography, 2024-03",
    },
    {
        "path": "projects/malthouse/02-interior-before.jpg",
        "aspect": "2:3",
        "role": "problem",
        "priority": 2,
        "caption": "Second floor before: timber joists, no roof above.",
        "sequence_position": "detail",
        "provenance": "site photography, 2024-03",
    },
    {
        "path": "projects/malthouse/03-interior-after.jpg",
        "aspect": "2:3",
        "role": "outcome",
        "priority": 2,
        "caption": "The same bay with the new frame and rooflight.",
        "sequence_position": "detail",
        "provenance": "site photography, 2026-05",
    },
    {
        "path": "projects/malthouse/04-detail.jpg",
        "aspect": "3:2",
        "role": "detail",
        "priority": 3,
        "caption": "New steel meeting retained cast iron, 40 mm clear.",
        "sequence_position": "detail",
        "provenance": "site photography, 2026-05",
    },
    {
        "type": "drawing",
        "path": "projects/malthouse/A3-201-section.pdf",
        "aspect": "4:3",
        "role": "intervention",
        "priority": 2,
        "caption": "Long section 1:100. New frame shown at the cut weight.",
        "provenance": "design_state 8f3a1c04 · view A3-201",
    },
)


def malthouse_state():
    """The design state the facts are lifted from."""
    from schemas.v2_models import (
        ConstraintItem,
        ConstraintState,
        DesignState,
        GeometryState,
        SemanticState,
    )

    return DesignState(
        design_state_id=DESIGN_STATE_ID,
        project_id=PROJECT_ID,
        content_hash=STATE_HASH,
        created_by="Studio OM",
        message="Malthouse — stage 4 issue",
        geometry=GeometryState(storey_count=3, space_count=24),
        semantic=SemanticState(
            style="Adaptive reuse, structure left legible",
            mood="Quiet, north-lit, material",
            materials={
                "floor": "Reclaimed maple over acoustic deck",
                "frame": "Hot-rolled steel, unpainted",
                "roof": "Glue-laminated spruce",
                "walls": "Retained brick, unlined to the north",
            },
        ),
        constraints=ConstraintState(
            budget_target=4_200_000.0,
            budget_achieved=4_074_000.0,
            budget_currency="GBP",
            area_targets=[
                ConstraintItem(name="gross internal area", target=2180.0,
                               achieved=2164.0, unit="m2"),
                ConstraintItem(name="public floor area", target=900.0,
                               achieved=947.0, unit="m2"),
            ],
            code_checks=[
                ConstraintItem(name="embodied carbon", target=520.0,
                               achieved=412.0, unit="kgCO2e/m2"),
                ConstraintItem(name="operational energy", target=95.0,
                               achieved=78.0, unit="kWh/m2/yr"),
            ],
        ),
    )


def malthouse_content() -> ContentModel:
    """The Malthouse as a :class:`ContentModel`."""
    return extract_content(
        malthouse_state(),
        project_name="The Malthouse",
        narrative=NARRATIVE,
        figures=FIGURES,
        author="Studio OM",
    )


MALTHOUSE_ID = PROJECT_ID
