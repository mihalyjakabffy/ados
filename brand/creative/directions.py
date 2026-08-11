"""
brand/creative/directions.py

Three directions, shipped as data.

They exist as data and not as code because that is the claim being made: the
difference between a portfolio spread and a technical report is a *set of
numbers a person chose*, not a different renderer, a different template or a
different prompt. Everything below could be authored in a form.

Three rather than one because one is not a system, and three rather than
twelve because a practice that generates a fresh direction for every document
stops looking like one practice. The architecture proposal's position (§K) is
that direction exploration belongs at brand-creation time and ends in a
commitment — so this module is a starting set to be edited and locked, not a
menu to be browsed per document.
"""

from __future__ import annotations

from brand.content.model import BlockRole
from brand.creative.direction import (
    Audience,
    CreativeDirection,
    Goal,
    LeadWith,
)

R = BlockRole


EDITORIAL_QUIET = CreativeDirection(
    id="editorial-quiet",
    applies_to=("portfolio-spread", "project-sheet", "case-study"),
    audience=Audience.CLIENT,
    goal=Goal.PERSUADE,
    narrative_order=(R.CONTEXT, R.PROBLEM, R.INTERVENTION, R.OUTCOME,
                     R.EVIDENCE, R.DETAIL, R.PROVENANCE),
    lead_with=LeadWith.IMAGE,
    emphasis_ceiling=1,
    text_density=0.45,
    words_per_page_max=320,
    image_ratio=0.50,
    pacing=("cover", "full-image", "text-image", "metric-band", "credit"),
    display_step="t7",
    body_step="t2",
    scale_jump_min=2,
    note=(
        "Reads at arm's length, one argument per page, and lets a photograph "
        "carry the opening. The lowest density of the three."
    ),
)

TECHNICAL_DENSE = CreativeDirection(
    id="technical-dense",
    applies_to=("project-report", "condition-survey", "stage-report"),
    audience=Audience.AUTHORITY,
    goal=Goal.RECORD,
    narrative_order=(R.PROBLEM, R.INTERVENTION, R.EVIDENCE, R.OUTCOME,
                     R.CONTEXT, R.DETAIL, R.PROVENANCE),
    lead_with=LeadWith.STATEMENT,
    emphasis_ceiling=1,
    text_density=0.78,
    words_per_page_max=900,
    image_ratio=0.12,
    pacing=("cover", "text-led", "text-led", "metric-band", "drawing",
            "text-led", "credit"),
    display_step="t5",
    body_step="t2",
    scale_jump_min=2,
    note=(
        "For a reader who has to find one fact and cite it. Dense, ordered by "
        "the problem, and it puts the evidence before the outcome."
    ),
)

IMAGE_LED = CreativeDirection(
    id="image-led",
    applies_to=("portfolio-spread", "competition-board", "monograph"),
    audience=Audience.PEER,
    goal=Goal.PERSUADE,
    narrative_order=(R.CONTEXT, R.INTERVENTION, R.OUTCOME, R.PROBLEM,
                     R.DETAIL, R.EVIDENCE, R.PROVENANCE),
    lead_with=LeadWith.IMAGE,
    emphasis_ceiling=2,
    text_density=0.62,
    words_per_page_max=140,
    image_ratio=0.72,
    pacing=("cover", "full-image", "image-pair", "full-image", "text-led",
            "credit"),
    display_step="t8",
    body_step="t2",
    scale_jump_min=3,
    note=(
        "The photographs are the argument and the text annotates them. "
        "Fewest words per page of the three, largest display step."
    ),
)


#: The starting set, by id.
DIRECTIONS: dict[str, CreativeDirection] = {
    d.id: d for d in (EDITORIAL_QUIET, TECHNICAL_DENSE, IMAGE_LED)
}


def get_direction(direction_id: str) -> CreativeDirection:
    try:
        return DIRECTIONS[direction_id]
    except KeyError:
        raise KeyError(
            f"unknown direction {direction_id!r}. Known: "
            + ", ".join(sorted(DIRECTIONS))
        ) from None
