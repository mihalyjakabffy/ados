"""
brand/creative/direction.py

What varies between two documents made from the same content and the same brand.

Note what is **absent**: there is no typography field, no colour field, no
grid field and no spacing field. Those belong to the brand, which already
holds them, versioned, validated against ADOS and consumed by twenty-six
templates. A direction that could name a colour would be a second declaration
of the palette, and two declarations of one value diverge — the repository
already carries the scars of that (a planted ``#8a2f2f`` in a preview, a font
table whose fallback disagreed with the brand's).

So the schema is closed in three ways, each enforced rather than documented:

1. ``extra="forbid"`` — a field the schema does not declare cannot be added at
   the call site.
2. :data:`FORBIDDEN_FIELD_STEMS` — checked at import against the declared
   fields, so adding ``colour:`` to this class fails on the way in, not in
   review.
3. :func:`_reject_brand_values` — the two free-text fields are scanned for
   hexes, dimensions and font declarations, because a direction that says
   "set it in Söhne at 12 pt" in its note has made the same mistake in prose.

The second constraint on this file comes from the standard. ``ADOS-7.2.020``
prohibits *appropriate, adequate, balanced, clean, elegant, harmonious,
legible (unqualified), neat, pleasing, reasonable, suitable, tidy, visually,
well-organised* in any normative field, and ``check_ados.py`` C7 scans for
them. Every field below is therefore a number, an enum, or a reference to a
step of the brand's own scale — nothing a validator cannot check.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from brand import ados
from brand.content.model import BlockRole
from brand.creative.archetypes import ARCHETYPE_NAMES

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Field-name stems that would mean the direction had started to restate the
#: brand. Checked against the model's declared fields at import time.
FORBIDDEN_FIELD_STEMS: tuple[str, ...] = (
    "colour", "color", "palette", "hex", "ink",
    "font", "typeface", "family", "weight",
    "grid", "column", "gutter", "margin",
    "spacing", "space", "size_mm", "point_size",
)

_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_DIMENSION = re.compile(r"\b\d+(?:\.\d+)?\s?(mm|cm|pt|px|em|rem|%)\b", re.I)
_FONT_TALK = re.compile(
    r"\b(font-family|typeface|sans-serif|serif|monospace|helvetica|inter|"
    r"söhne|sohne|arial|times)\b",
    re.I,
)

#: ADOS-7.2.020's banned lexicon, as it applies here. The full list lives in
#: the standard and is checked by ``check_ados.py``; this is the subset a
#: creative direction is most likely to reach for.
_SUBJECTIVE = re.compile(
    r"\b(appropriate|adequate|balanced|clean|elegant|harmonious|neat|"
    r"pleasing|reasonable|suitable|tidy|visually|well.organised|"
    r"well.organized)\b",
    re.I,
)


class Audience(str, Enum):
    CLIENT = "client"
    PEER = "peer"
    AUTHORITY = "authority"
    PUBLIC = "public"
    INTERNAL = "internal"


class Goal(str, Enum):
    INFORM = "inform"
    PERSUADE = "persuade"
    RECORD = "record"
    INSTRUCT = "instruct"


class LeadWith(str, Enum):
    """What the reader meets first."""

    IMAGE = "image"
    STATEMENT = "statement"
    METRIC = "metric"
    DRAWING = "drawing"


class DirectionError(ValueError):
    """A direction tried to do the brand's job."""


class CreativeDirection(BaseModel):
    """Emphasis, density and pacing. Never appearance."""

    model_config = _Frozen

    id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,39}$")
    applies_to: tuple[str, ...] = Field(default=(), max_length=12)
    audience: Audience
    goal: Goal

    # -- Emphasis: which roles lead, and how hard -------------------------
    narrative_order: tuple[BlockRole, ...] = Field(min_length=1)
    lead_with: LeadWith
    emphasis_ceiling: int = Field(
        ge=0, le=4,
        description="Blocks per page that may take a display step. A page on "
        "which everything is emphasised has no hierarchy.",
    )

    # -- Density: bounded by ADOS -----------------------------------------
    text_density: float = Field(
        gt=0, lt=1,
        description="Target fill ratio. Bounded by ADOS-3.7.010 / H13.",
    )
    words_per_page_max: int = Field(ge=20, le=2000)
    image_ratio: float = Field(
        ge=0.0, le=1.0,
        description="Target share of page area given to figures.",
    )
    pacing: tuple[str, ...] = Field(
        min_length=1,
        description="The archetype sequence this direction reaches for. A "
        "preference measured by the objective, not a hard constraint: content "
        "that does not fit the sequence produces a different page, not a "
        "failure.",
    )

    # -- Type behaviour: steps of the brand's scale, never sizes ----------
    display_step: str = Field(pattern=r"^t[1-8]$")
    body_step: str = Field(pattern=r"^t[1-8]$")
    scale_jump_min: int = Field(
        ge=1, le=6,
        description="Steps between adjacent ranks, so the hierarchy reads.",
    )

    # -- Provenance --------------------------------------------------------
    brand_version: str = Field(default="", pattern=r"^$|^\d+\.\d+\.\d+$")
    note: str = Field(
        default="", max_length=400,
        description="Informative only. Nothing downstream reads it — see "
        "ADOS-7.2.020, which is why nothing downstream may.",
    )

    # ------------------------------------------------------------------

    @field_validator("text_density")
    @classmethod
    def _density_within_ados(cls, v: float) -> float:
        low, high = ados.fill_ratio_bounds()
        if not (low <= v <= high):
            raise DirectionError(
                f"text_density {v} is outside the ADOS fill-ratio range "
                f"[{low}, {high}] (ADOS-3.7.010 / H13). A direction cannot "
                f"target a density the standard forbids."
            )
        return v

    @field_validator("pacing")
    @classmethod
    def _pacing_names_real_archetypes(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        unknown = [n for n in v if n not in ARCHETYPE_NAMES]
        if unknown:
            raise DirectionError(
                f"pacing names archetypes that do not exist: "
                f"{', '.join(unknown)}. The set is closed: "
                + ", ".join(ARCHETYPE_NAMES)
            )
        return v

    @field_validator("narrative_order")
    @classmethod
    def _roles_appear_once(cls, v: tuple[BlockRole, ...]) -> tuple[BlockRole, ...]:
        if len(set(v)) != len(v):
            raise DirectionError(
                "narrative_order repeats a role. An order in which a role "
                "appears twice does not order anything."
            )
        return v

    @model_validator(mode="after")
    def _hierarchy_reads(self) -> "CreativeDirection":
        ladder = _ladder()
        gap = ladder.index(self.display_step) - ladder.index(self.body_step)
        if gap < self.scale_jump_min:
            raise DirectionError(
                f"display_step {self.display_step} is {gap} step(s) above "
                f"body_step {self.body_step}, below the declared "
                f"scale_jump_min of {self.scale_jump_min}. Two ranks a single "
                f"√2 step apart read as one rank set unevenly "
                f"(ADOS-2.4.020)."
            )
        floor = ados.min_cap_height_mm()
        body_cap = ados.type_steps()[self.body_step]
        if body_cap < floor:
            raise DirectionError(
                f"body_step {self.body_step} is {body_cap} mm cap, below the "
                f"{floor} mm floor for primary content (ADOS-2.4.010). "
                f"Reducing text size is also a prohibited remedy "
                f"(ADOS-7.5.070)."
            )
        _reject_brand_values(self.id, self.note)
        return self

    # ------------------------------------------------------------------

    def role_rank(self, role: BlockRole) -> int:
        """Position of ``role`` in the declared order; unlisted roles last."""
        try:
            return self.narrative_order.index(role)
        except ValueError:
            return len(self.narrative_order)

    def pacing_for(self, page_index: int) -> str:
        """The archetype this direction reaches for at ``page_index``.

        The sequence does not loop. Past its end there is no preference, and
        the objective's pacing term goes quiet rather than pushing a long
        document back to the start of a short rhythm.
        """
        if page_index < len(self.pacing):
            return self.pacing[page_index]
        return ""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------


def _ladder() -> list[str]:
    """Step names, ascending by cap height."""
    steps = ados.type_steps()
    return sorted(steps, key=lambda k: steps[k])


def _reject_brand_values(*texts: str) -> None:
    """Refuse a direction that has started to describe appearance."""
    for text in texts:
        if not text:
            continue
        if _HEX.search(text):
            raise DirectionError(
                f"a direction may not name a colour ({text!r}). Colour is the "
                f"brand's: set it on visual_identity.colour and reference the "
                f"token."
            )
        if _DIMENSION.search(text):
            raise DirectionError(
                f"a direction may not name a dimension ({text!r}). Sizes are "
                f"derived from the brand's scale — say which step, not how "
                f"many millimetres."
            )
        if _FONT_TALK.search(text):
            raise DirectionError(
                f"a direction may not name a typeface ({text!r}). The face is "
                f"the brand's: visual_identity.typography."
            )
        if _SUBJECTIVE.search(text):
            raise DirectionError(
                f"ADOS-7.2.020 prohibits this vocabulary in a field that "
                f"affects output ({text!r}). Replace it with a measurable "
                f"condition — a ratio, a count, or a step of the scale."
            )


def _assert_schema_stays_out_of_the_brands_business() -> None:
    """Run at import. A field named like the brand's would be a second copy."""
    for name in CreativeDirection.model_fields:
        for stem in FORBIDDEN_FIELD_STEMS:
            if stem in name:
                raise DirectionError(
                    f"CreativeDirection declares a field named {name!r}, which "
                    f"restates part of the Brand. Typography, colour, grid and "
                    f"spacing are the Brand's and are already versioned, "
                    f"validated and consumed by the template catalogue. A "
                    f"direction selects from them and decides emphasis; it "
                    f"does not declare them."
                )


_assert_schema_stays_out_of_the_brands_business()
