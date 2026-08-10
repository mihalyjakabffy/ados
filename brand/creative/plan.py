"""
brand/creative/plan.py

The composer's output: a page plan.

A ``PagePlan`` is a *data structure*, not a document. It states where things
go and how big they are, in millimetres on the brand's grid, and it is
deliberately renderer-agnostic — the same plan is meant to reach HTML today
and ``ptspdf``/``ptsword`` later, which is only possible if no renderer has to
be consulted to produce it. That is why the architecture proposal argued
against a third engine: the renderers already exist, and what they lacked was
something to render.

Two fields carry more weight than they look:

``rejected``
    Every archetype that was considered for a page and not used, with the
    reason. It is how a reader sees the layout was *chosen* rather than
    defaulted, and it is what makes a ranking auditable rather than an
    assertion. A composer that silently picks the first thing that fits is
    indistinguishable, from the outside, from one that picks at random.

``plan_hash``
    A digest over the whole plan. Two runs of the composer over the same
    content, brand and direction must produce the same hash. If they do not,
    something in the pipeline is sampling, and the document cannot be
    reprinted.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_Frozen = ConfigDict(frozen=True, extra="forbid")


class RejectionKind(str, Enum):
    """Why a candidate did not become a page."""

    INFEASIBLE = "infeasible"    # broke a hard constraint
    OUTRANKED = "outranked"      # feasible, scored worse
    NO_MATCH = "no-match"        # accepted nothing at the head of the queue


class Slot(BaseModel):
    """One placed thing."""

    model_config = _Frozen

    component: str
    block: str = Field(
        default="",
        description="Content block id, or empty for a fixed slot fed by the "
        "content model itself (the project's name, the issue line).",
    )
    text: str = Field(default="", max_length=8000)
    label: str = Field(
        default="", max_length=120,
        description="For a metric or a fact, what the value is. Kept apart "
        "from the value so the renderer sets them at different ranks rather "
        "than splitting a string back apart.",
    )
    provenance: str = Field(
        default="", max_length=200,
        description="Where a metric came from. Carried onto the page: a "
        "number in a client document whose origin nobody can state is a "
        "liability, and hiding the origin in the model does not fix that.",
    )
    path: str = Field(
        default="",
        description="For a figure, where the asset lives. Carried on the plan "
        "so a renderer never has to consult the content model — the plan is "
        "the whole instruction.",
    )
    rank: str
    step: str = Field(pattern=r"^t[1-8]$")
    cap_mm: float = Field(gt=0)
    emphasis: bool = False

    # Geometry, in mm from the content area's top-left, on the lattice.
    x_mm: float = Field(ge=0)
    y_mm: float = Field(ge=0)
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    columns: int = Field(ge=1)

    ink: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Estimated local ink coverage of typeset content. Zero "
        "for figures, which are not ink work — see the composer.",
    )

    @property
    def area_mm2(self) -> float:
        return self.width_mm * self.height_mm


class PageGrid(BaseModel):
    """The lattice a page was composed on. Reported so a plan is checkable."""

    model_config = _Frozen

    format: str
    page_width_mm: float = Field(gt=0)
    page_height_mm: float = Field(gt=0)
    columns: int = Field(ge=1)
    gutter_mm: float = Field(ge=0)
    margin_mm: float = Field(ge=0)
    column_width_mm: float = Field(gt=0)
    content_width_mm: float = Field(gt=0)
    content_height_mm: float = Field(gt=0)


class Page(BaseModel):
    model_config = _Frozen

    index: int = Field(ge=0)
    archetype: str
    grid: PageGrid
    slots: tuple[Slot, ...] = ()

    # Computed, and checked against the hard constraints.
    fill_ratio: float = Field(ge=0.0)
    ink_coverage_max: float = Field(ge=0.0)
    alignment_edges_x: int = Field(ge=0)
    words: int = Field(ge=0)
    image_ratio: float = Field(ge=0.0, le=1.0)
    objective: float = Field(ge=0.0)

    @property
    def block_ids(self) -> tuple[str, ...]:
        return tuple(s.block for s in self.slots if s.block)


class Rejection(BaseModel):
    model_config = _Frozen

    page: int = Field(ge=0)
    archetype: str
    kind: RejectionKind
    reason: str
    rule: str = Field(
        default="",
        description="The ADOS hard constraint that ruled it out, where one did.",
    )


class PagePlan(BaseModel):
    """A composed document, before it is rendered."""

    model_config = _Frozen

    document: str
    project_name: str
    brand_id: str
    brand_version: str
    direction: str
    content_hash: str
    ados_edition: str = ""

    pages: tuple[Page, ...] = ()
    rejected: tuple[Rejection, ...] = ()
    notes: tuple[str, ...] = ()

    # ------------------------------------------------------------------

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def archetype_sequence(self) -> tuple[str, ...]:
        return tuple(p.archetype for p in self.pages)

    @property
    def mean_fill_ratio(self) -> float:
        if not self.pages:
            return 0.0
        return round(sum(p.fill_ratio for p in self.pages) / len(self.pages), 4)

    @property
    def placed_blocks(self) -> tuple[str, ...]:
        return tuple(b for page in self.pages for b in page.block_ids)

    @property
    def plan_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**self.model_dump(mode="json"), "plan_hash": self.plan_hash}

    def summary(self) -> str:
        return (
            f"{self.direction}: {self.page_count} pages "
            f"[{' · '.join(self.archetype_sequence)}] "
            f"fill {self.mean_fill_ratio:.2f} "
            f"({len(self.rejected)} candidates rejected)"
        )
