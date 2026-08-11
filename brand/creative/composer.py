"""
brand/creative/composer.py

The Composer: content + direction + brand → a :class:`PagePlan`.

**It does not generate. It enumerates, filters and ranks.** ``ADOS-7.5.010``
specifies the layout solver and says so outright — "no randomised restarts, no
time-based termination, no parallel non-deterministic reduction" — and the
Creative Layer extends that solver to document pages rather than replacing it
with something that samples. The practical consequence is the property the
whole system rests on: the same content, brand and direction produce the same
document every time, so changing the direction is a decision somebody made
rather than an outcome somebody got.

For each page the composer:

1. enumerates every (archetype × consumption count) candidate that accepts the
   content at the head of the queue — at most eight archetypes by ten counts;
2. lays each one out on the brand's grid, in millimetres;
3. discards the infeasible ones against the hard constraints, recording the
   rule that killed each;
4. scores the survivors against the direction's declared targets;
5. takes the best, breaking ties by ``ADOS-7.5.050``.

Which hard constraints apply
----------------------------
``ADOS-7.5.020`` lists fifteen. Ten of them are about drawing sheets and have
no document analogue; applying them anyway would produce findings nobody could
act on, which is how a check suite trains people to ignore it.

============  ===========================================================
H1  applied   No content outside the content region
H6  applied   Vertical origins and baselines on the sub-module lattice
H7  applied   Horizontal extents on the column grid
H12 applied   Local ink coverage ≤ 0.25, over typeset content
H13 partly    Fill ratio ≤ 0.85 hard; the 0.40 floor is advisory — see below
H14 applied   Distinct alignment edges ≤ 6, on the x axis
H15 applied   Cap height ≥ the floor for the slot's role class
H2,H3         Annotation clear zones and text masks — drawing-only
H4            Fold-safe zones — large-format sheets only
H5,H7*        View separation — a document page has no views
H8,H9,H10     Leaders and dimension chains — drawing-only
H11           Annotations per search region — drawing-only
============  ===========================================================

Two deliberate narrowings, stated rather than quietly applied:

* **H14 is checked on the x axis only.** On a drawing sheet both axes carry
  free placement. A document page is a vertical flow, where one alignment edge
  per row is the structure and not a defect; counting them would fail every
  page with more than three rows.
* **H12 excludes figures.** ``ADOS-3.7.020`` bounds *ink* — line work and
  type. A photograph is not ink work, and a check that failed every page with
  a picture on it would be deleted within a week.
* **H13 is split.** The ceiling stays hard: an overfull page is a legibility
  failure, and legibility is not negotiable. The floor becomes advisory,
  because on a sheet an underfilled surface is waste and in a document it is a
  device — ``editorial-quiet`` asks for a fill ratio of 0.45 on purpose, and
  the last page of any document is underfull by arithmetic. The floor is
  carried instead by the objective, where ADOS already weights fill-ratio
  deviation at 20000, the heaviest term it has, and reported by
  :func:`evaluate` as a finding.

``ADOS-3.7.030``'s ``emphasis_area_max`` is **not** applied. It bounds
emphasis among ordinary content on a sheet; on a cover the title is the page.
The direction's ``emphasis_ceiling`` — a count of emphasised blocks per page —
does that job here instead.

Escalation
----------
An infeasible page follows ``ADOS-7.5.070``: the composer reduces what the
page takes and re-solves, which is step 4 of the escalation order (*split the
sheet*) in document terms. It never applies a prohibited remedy — text size
and line width are not the solver's to trade away. If nothing is feasible at
any consumption count it raises :class:`CompositionError` naming the rule,
which is ``E-LAYOUT-001``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from brand import ados
from brand.content.model import (
    FIGURE_TYPES,
    BlockRole,
    BlockType,
    ContentBlock,
    ContentModel,
    CHARS_PER_WORD,
)
from brand.creative.archetypes import (
    ARCHETYPES,
    COVER,
    GLYPH_INK,
    Archetype,
    Rank,
    SlotSpec,
)
from brand.creative.direction import CreativeDirection, LeadWith
from brand.creative.plan import (
    Page,
    PageGrid,
    PagePlan,
    Rejection,
    RejectionKind,
    Slot,
)
from brand.models.brand import Brand
from brand.models.tokens import TokenSet

#: Average character advance as a fraction of the em, for latin text. Like
#: ``GLYPH_INK`` this is a property of typesetting rather than of ADOS, so it
#: is stated once here and used to estimate how many characters fit a measure.
AVERAGE_ADVANCE_EM: float = 0.5

#: Objective weights. The first three are ADOS-7.5.040's own, read from the
#: standard rather than copied. The rest are terms a document has and a
#: drawing sheet does not; their weights are declared here, in one table, at
#: magnitudes that keep them subordinate to fill ratio — the term ADOS
#: weights most heavily.
DOCUMENT_WEIGHTS: dict[str, float] = {
    "words_over_max": 50.0,
    "image_ratio_deviation": 2000.0,
    "pacing_mismatch": 500.0,
}

#: Characters per line ADOS-3.6.010 wants for continuous text. Reported by the
#: evaluation, not enforced: a caption legitimately runs short.
MEASURE_CHARS = (45, 75)


class CompositionError(RuntimeError):
    """No feasible page could be composed. ``E-LAYOUT-001``."""


# ---------------------------------------------------------------------------
# The metrics the composer measures in
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypeMetrics:
    """Everything about the brand's type the composer needs, in millimetres.

    Derived from the token set, never from a font file at compose time: the
    plan has to be reproducible on a machine that has no fonts installed.
    """

    cap_ratio: float
    line_height_factor: float
    lattice_mm: float
    steps: dict[str, float]

    @classmethod
    def from_tokens(cls, tokens: TokenSet) -> "TypeMetrics":
        cap_mm = float(tokens.value("font.size.sm"))
        pt = float(tokens.value("font.size.sm.pt"))
        em_mm = pt * 25.4 / 72.0
        return cls(
            cap_ratio=cap_mm / em_mm,
            line_height_factor=float(tokens.value("line_height.body")),
            lattice_mm=ados.submodule_mm(),
            steps=ados.type_steps(),
        )

    def em_mm(self, cap_mm: float) -> float:
        return cap_mm / self.cap_ratio

    def leading_mm(self, cap_mm: float) -> float:
        """Baseline pitch, snapped up to the sub-module — ``H6``.

        Snapped rather than rounded: rounding down would put two baselines
        closer than the face's own line height and set the text solid.
        """
        raw = self.line_height_factor * self.em_mm(cap_mm)
        return _ceil_to(raw, self.lattice_mm)

    def chars_per_line(self, cap_mm: float, measure_mm: float) -> float:
        return measure_mm / (AVERAGE_ADVANCE_EM * self.em_mm(cap_mm))

    def text_height_mm(self, text: str, cap_mm: float, measure_mm: float) -> float:
        if not text:
            return 0.0
        words = len(text.split())
        chars = max(1.0, words * CHARS_PER_WORD)
        lines = max(1, math.ceil(chars / self.chars_per_line(cap_mm, measure_mm)))
        return lines * self.leading_mm(cap_mm)

    def ink(self, cap_mm: float) -> float:
        """Estimated local ink coverage of typeset text at this size."""
        return GLYPH_INK * cap_mm / self.leading_mm(cap_mm)


@dataclass(frozen=True)
class PageFormat:
    """The page and its grid, resolved from ADOS and the brand."""

    name: str
    width_mm: float
    height_mm: float
    columns: int
    gutter_mm: float
    margin_mm: float

    @property
    def content_width_mm(self) -> float:
        return self.width_mm - 2 * self.margin_mm

    @property
    def content_height_mm(self) -> float:
        return self.height_mm - 2 * self.margin_mm

    @property
    def column_width_mm(self) -> float:
        return (
            self.content_width_mm - (self.columns - 1) * self.gutter_mm
        ) / self.columns

    def span_width_mm(self, columns: int) -> float:
        return columns * self.column_width_mm + (columns - 1) * self.gutter_mm

    def column_x_mm(self, index: int) -> float:
        return index * (self.column_width_mm + self.gutter_mm)

    def to_grid(self) -> PageGrid:
        return PageGrid(
            format=self.name,
            page_width_mm=self.width_mm,
            page_height_mm=self.height_mm,
            columns=self.columns,
            gutter_mm=self.gutter_mm,
            margin_mm=self.margin_mm,
            column_width_mm=round(self.column_width_mm, 4),
            content_width_mm=round(self.content_width_mm, 4),
            content_height_mm=round(self.content_height_mm, 4),
        )


def page_format(brand: Brand, name: str = "A4") -> PageFormat:
    """The page size from ADOS, the column configuration from the brand.

    The split is the whole discipline in one function: paper is ISO 216 and
    nobody's to choose, columns are the practice's and ADOS has no opinion.
    """
    sizes = ados.ados_tokens()["sheet"]["sizes_mm"]
    key = name.split("-", 1)[0]
    if key not in sizes:
        raise CompositionError(
            f"unknown page format {name!r}. ADOS defines: {', '.join(sorted(sizes))}"
        )
    short, long = float(sizes[key][0]), float(sizes[key][1])
    landscape = name.endswith("landscape")
    cfg = brand.visual_identity.grid.for_format(key)
    return PageFormat(
        name=name,
        width_mm=long if landscape else short,
        height_mm=short if landscape else long,
        columns=cfg.columns,
        gutter_mm=cfg.gutter_mm,
        margin_mm=cfg.margin_mm,
    )


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def order_blocks(
    content: ContentModel, direction: CreativeDirection
) -> tuple[ContentBlock, ...]:
    """The reading order this direction asks for.

    Role first (the direction's declared narrative order), then the author's
    priority, then the block id. The third key is not decoration: without a
    total order two blocks with the same role and priority could swap between
    runs, and the document would not be reproducible.
    """
    return tuple(
        sorted(
            content.blocks,
            key=lambda b: (direction.role_rank(b.role), b.priority, b.id),
        )
    )


#: What each ``lead_with`` value asks the cover to open with.
_LEAD_TYPE: dict[LeadWith, BlockType] = {
    LeadWith.IMAGE: BlockType.IMAGE,
    LeadWith.DRAWING: BlockType.DRAWING,
    LeadWith.METRIC: BlockType.METRIC,
    LeadWith.STATEMENT: BlockType.NARRATIVE,
}


def _promote_lead(
    blocks: Sequence[ContentBlock], direction: CreativeDirection
) -> tuple[tuple[ContentBlock, ...], str]:
    """Move the block the direction wants to open with to the front.

    One block moves, and only one. Everything after it keeps the order the
    direction declared, so ``lead_with`` changes the opening rather than
    rearranging the argument.
    """
    wanted = _LEAD_TYPE[direction.lead_with]
    candidates = [b for b in blocks if b.type is wanted]
    if not candidates:
        return tuple(blocks), (
            f"lead_with={direction.lead_with.value} could not be honoured: the "
            f"content model has no {wanted.value} block. The cover opens with "
            f"the first block in narrative order instead."
        )
    lead = min(candidates, key=lambda b: (b.priority, b.id))
    return (lead, *[b for b in blocks if b.id != lead.id]), ""


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    archetype: Archetype
    index: int                       # position in ARCHETYPES — the tie-break
    slots: tuple[Slot, ...]
    consumed: int
    fill_ratio: float
    ink_coverage_max: float
    alignment_edges_x: int
    words: int
    image_ratio: float
    balance_error: float
    height_mm: float
    emphasised: int


def _capacity(archetype: Archetype) -> int:
    return sum(s.repeat for s in archetype.slots if not s.is_fixed)


@dataclass(frozen=True)
class _Fill:
    """One of an archetype's slots, with the blocks that went into it.

    Carries the row and column index rather than the ``SlotSpec`` alone,
    because two slots in different rows can be identical by value — a
    metric band has four of them — and grouping by value would put a row's
    slots in the wrong row.
    """

    row: int
    order: int
    spec: SlotSpec
    blocks: tuple[ContentBlock, ...]


def _assign(
    archetype: Archetype, queue: Sequence[ContentBlock], cap: int
) -> tuple[list[_Fill], int] | None:
    """Fill the archetype's slots from the head of the queue, taking ≤ ``cap``.

    Strictly from the head: a slot that would have to reach past an unplaced
    block to find something it accepts does not match. Reaching past would
    silently reorder the argument, which is the direction's business and not
    the archetype's.

    A ``repeat`` slot takes several blocks and stacks them *within* its own
    column — three paragraphs in the measure, not three columns of one
    paragraph each.
    """
    fills: list[_Fill] = []
    j = used = 0
    for r, row in enumerate(archetype.rows):
        if row.balance:
            capacity = sum(s.repeat for s in row.slots if not s.is_fixed)
            accepted = {t for s in row.slots for t in s.accepts}
            pool: list[ContentBlock] = []
            while (
                len(pool) < capacity
                and used < cap
                and j < len(queue)
                and queue[j].type in accepted
            ):
                pool.append(queue[j])
                j += 1
                used += 1
            if not pool:
                if any(s.required for s in row.slots):
                    return None
                continue
            # Deal across every slot the row declares, not only as many as
            # there are blocks. The row's column structure belongs to the
            # archetype: a metric band is two columns wide whether it holds
            # four metrics or one, and a lone metric that grew to fill the
            # page would make the band a different thing.
            live = [(k, s) for k, s in enumerate(row.slots) if not s.is_fixed]
            dealt: list[list[ContentBlock]] = [[] for _ in live]
            for i, block in enumerate(pool):
                dealt[i % len(live)].append(block)
            for (k, spec), blocks in zip(live, dealt):
                if blocks:
                    fills.append(_Fill(r, k, spec, tuple(blocks)))
            continue

        for k, spec in enumerate(row.slots):
            if spec.is_fixed:
                fills.append(_Fill(r, k, spec, ()))
                continue
            taken: list[ContentBlock] = []
            while (
                len(taken) < spec.repeat
                and used < cap
                and j < len(queue)
                and queue[j].type in spec.accepts
            ):
                taken.append(queue[j])
                j += 1
                used += 1
            if not taken:
                if spec.required:
                    return None
                continue
            fills.append(_Fill(r, k, spec, tuple(taken)))
    return (fills, used) if used else None


def _step_for(rank: Rank, direction: CreativeDirection, ladder: list[str]) -> str:
    """Map a slot's rank onto a step of the brand's scale.

    Only ``DISPLAY`` and ``BODY`` are the direction's to state. ``LEAD`` sits
    the direction's own declared jump above body so the hierarchy reads at the
    interval it asked for, and ``CAPTION`` one below — subordinate, and the
    only rank permitted under the 2.5 mm primary-content floor.
    """
    body = ladder.index(direction.body_step)
    display = ladder.index(direction.display_step)
    if rank is Rank.DISPLAY:
        return ladder[display]
    if rank is Rank.LEAD:
        return ladder[min(body + direction.scale_jump_min, display)]
    if rank is Rank.CAPTION:
        return ladder[max(body - 1, 0)]
    return ladder[body]


def _fixed_text(component: str, ctx: "_Context", blocks: Sequence[ContentBlock]) -> str:
    """Text for a slot the content model feeds rather than a block.

    ``section-label`` names the *role* of what is on the page. That is a
    structural device carrying something true about the content — which part
    of the argument this page is — rather than a decorative eyebrow. It reads
    the whole page and not its own row, because on a metric band the label
    sits in a row of its own and would otherwise describe nothing.
    """
    if component == "project-title":
        return ctx.content.project_name
    if component == "issue":
        return f"{ctx.document} · {ctx.content.content_hash[:8]}"
    if component == "section-label":
        role = blocks[0].role if blocks else BlockRole.CONTEXT
        return role.value.replace("_", " ").upper()
    return ""


@dataclass
class _Context:
    content: ContentModel
    direction: CreativeDirection
    fmt: PageFormat
    type_metrics: TypeMetrics
    document: str
    ladder: list[str]


def _lay_out(
    archetype: Archetype,
    index: int,
    fills: Sequence[_Fill],
    consumed: int,
    ctx: _Context,
) -> Candidate | None:
    """Turn an assignment into placed slots, or ``None`` if it will not fit."""
    fmt, tm = ctx.fmt, ctx.type_metrics
    lattice = tm.lattice_mm
    gap = _ceil_to(fmt.gutter_mm, lattice)

    placed: list[Slot] = []
    figure_ids: set[str] = set()
    page_blocks = [b for f in fills for b in f.blocks]
    y = 0.0
    for r, row in enumerate(archetype.rows):
        entries = {f.order: f for f in fills if f.row == r}
        if not entries:
            continue

        # Distribute whole columns across every slot the row declares — not
        # only the filled ones — so the page's column structure comes from the
        # archetype and does not change with how much content arrived. The
        # remainder goes to the earlier slots, so a 4-column grid splitting 1:3
        # gives 1 and 3 and never 0.
        counts = _distribute(fmt.columns, [s.weight for s in row.slots])
        if any(c < 1 for c in counts):
            return None

        row_height = 0.0
        col = 0
        for k, spec in enumerate(row.slots):
            n_cols = counts[k]
            box_width = fmt.span_width_mm(n_cols)
            x = fmt.column_x_mm(col)
            col += n_cols
            fill = entries.get(k)
            if fill is None:
                continue                         # declared, unfilled, left blank

            step = _step_for(spec.rank, ctx.direction, ctx.ladder)
            cap_mm = tm.steps[step]
            stack = fill.blocks or (None,)
            inner_y = 0.0

            for block in stack:
                width = box_width
                if block is None:
                    text = _fixed_text(spec.component, ctx, page_blocks)
                    height = _ceil_to(
                        max(tm.text_height_mm(text, cap_mm, width),
                            spec.min_rows * lattice),
                        lattice,
                    )
                    ink = tm.ink(cap_mm) if text else 0.0
                elif block.type in FIGURE_TYPES:
                    figure_ids.add(block.id)
                    text = block.display_text
                    width, height = _fit_figure(
                        block, spec, n_cols, fmt, tm, cap_mm,
                        available_mm=fmt.content_height_mm - y - inner_y,
                    )
                    ink = 0.0                    # a photograph is not ink work
                else:
                    text = block.display_text
                    height = _ceil_to(
                        max(tm.text_height_mm(text, cap_mm, width),
                            spec.min_rows * lattice),
                        lattice,
                    )
                    ink = tm.ink(cap_mm) if text else 0.0

                placed.append(
                    Slot(
                        component=spec.component,
                        block=block.id if block else "",
                        text=text,
                        label=block.label if block else "",
                        provenance=(
                            block.provenance
                            if block is not None and block.type is BlockType.METRIC
                            else ""
                        ),
                        path=block.path if block else "",
                        rank=spec.rank.value,
                        step=step,
                        cap_mm=cap_mm,
                        emphasis=spec.emphasis,
                        x_mm=round(x, 4),
                        y_mm=round(y + inner_y, 4),
                        width_mm=round(width, 4),
                        height_mm=round(height, 4),
                        columns=n_cols,
                        ink=round(ink, 4),
                    )
                )
                inner_y += height + lattice

            row_height = max(row_height, inner_y - lattice)
        y += row_height + gap

    total_height = y - gap
    if total_height > fmt.content_height_mm + 1e-9:
        return None                              # H1: taller than the page

    content_area = fmt.content_width_mm * fmt.content_height_mm
    used_area = sum(s.area_mm2 for s in placed)
    figure_area = sum(s.area_mm2 for s in placed if s.block in figure_ids)

    edges = {round(s.x_mm, 1) for s in placed} | {
        round(s.x_mm + s.width_mm, 1) for s in placed
    }
    centroid = (
        sum((s.x_mm + s.width_mm / 2) * s.area_mm2 for s in placed) / used_area
        if used_area
        else 0.0
    )

    return Candidate(
        archetype=archetype,
        index=index,
        slots=tuple(placed),
        consumed=consumed,
        fill_ratio=round(used_area / content_area, 4),
        ink_coverage_max=round(max((s.ink for s in placed), default=0.0), 4),
        alignment_edges_x=len(edges),
        words=sum(b.words for f in fills for b in f.blocks),
        image_ratio=round(figure_area / content_area, 4),
        balance_error=round(
            abs(centroid - fmt.content_width_mm / 2) / fmt.content_width_mm, 4
        ),
        height_mm=round(total_height, 4),
        emphasised=sum(1 for s in placed if s.emphasis),
    )


# ---------------------------------------------------------------------------
# Feasibility and objective
# ---------------------------------------------------------------------------


def _violations(cand: Candidate, ctx: _Context) -> list[tuple[str, str]]:
    """``(rule, reason)`` for every hard constraint this candidate breaks."""
    out: list[tuple[str, str]] = []
    fmt, tm = ctx.fmt, ctx.type_metrics
    _, high = ados.fill_ratio_bounds()

    # H13's *ceiling* is hard and its *floor* is not, and the asymmetry is
    # deliberate. An overfull page is a legibility failure: there is nowhere
    # for the eye to rest and nothing can be found on it. An underfull page is
    # an editorial judgement — whitespace is the device `text_density: 0.45`
    # explicitly asks for, and the last page of any document is underfull by
    # arithmetic rather than by choice. So the floor is carried by the
    # objective, where ADOS already weights fill-ratio deviation most heavily
    # of all its terms, and reported by the evaluation as an advisory finding.
    if cand.fill_ratio > high:
        out.append((
            "H13",
            f"fill ratio {cand.fill_ratio:.2f} above {high:.2f} — the page has "
            f"no room left to read in",
        ))

    ceiling = ados.local_coverage_max()
    if cand.ink_coverage_max > ceiling + 1e-9:
        out.append((
            "H12",
            f"local ink coverage {cand.ink_coverage_max:.2f} above {ceiling:.2f} "
            f"in a {ados.coverage_window_mm():g} mm window",
        ))

    max_edges = ados.alignment_edges_max_per_axis()
    if cand.alignment_edges_x > max_edges:
        out.append((
            "H14",
            f"{cand.alignment_edges_x} distinct alignment edges on the x axis, "
            f"above {max_edges}",
        ))

    primary_floor = ados.min_cap_height_mm()
    absolute_floor = ados.absolute_cap_floor_mm()
    for slot in cand.slots:
        if not slot.text:
            continue
        floor = absolute_floor if slot.rank == Rank.CAPTION.value else primary_floor
        if slot.cap_mm < floor - 1e-9:
            out.append((
                "H15",
                f"{slot.component} sets {slot.cap_mm} mm cap, below the "
                f"{floor} mm floor for {slot.rank} content",
            ))

    lattice = tm.lattice_mm
    for slot in cand.slots:
        if abs(slot.y_mm % lattice) > 1e-6 or abs(slot.height_mm % lattice) > 1e-6:
            out.append((
                "H6",
                f"{slot.component} is off the {lattice:g} mm sub-module lattice "
                f"(y {slot.y_mm}, height {slot.height_mm})",
            ))
            break
    for slot in cand.slots:
        if slot.x_mm + slot.width_mm > fmt.content_width_mm + 1e-6:
            out.append((
                "H7",
                f"{slot.component} runs {slot.x_mm + slot.width_mm:.1f} mm wide "
                f"on a {fmt.content_width_mm:.1f} mm column grid",
            ))
            break

    if cand.emphasised > ctx.direction.emphasis_ceiling:
        out.append((
            "direction.emphasis_ceiling",
            f"{cand.emphasised} emphasised blocks, above the direction's "
            f"ceiling of {ctx.direction.emphasis_ceiling}",
        ))
    return out


def _objective(cand: Candidate, ctx: _Context, page_index: int) -> float:
    """Distance from what the direction asked for. Lower is better."""
    w = ados.solver_objective_weights()
    d = ctx.direction
    score = 0.0

    score += w["fill_ratio_deviation"] * abs(cand.fill_ratio - d.text_density)
    score += w["balance_error"] * cand.balance_error
    # ADOS prices alignment per millimetre of deviation; on a page whose
    # placement is quantised to the lattice, one surplus edge is one lattice
    # step of deviation, so the per-mm weight is applied over the lattice.
    surplus = max(0, cand.alignment_edges_x - 2)
    score += w["alignment_deviation_per_mm"] * ados.solver_lattice_mm() * surplus

    score += DOCUMENT_WEIGHTS["words_over_max"] * max(
        0, cand.words - d.words_per_page_max
    )
    score += DOCUMENT_WEIGHTS["image_ratio_deviation"] * abs(
        cand.image_ratio - d.image_ratio
    )
    wanted = d.pacing_for(page_index)
    if wanted and wanted != cand.archetype.name:
        score += DOCUMENT_WEIGHTS["pacing_mismatch"]
    return round(score, 4)


def _tie_break(cand: Candidate, score: float) -> tuple:
    """``ADOS-7.5.050`` in document terms.

    The standard's first key is "lower total leader length" — the drawing's
    measure of how much apparatus a layout needs to hold itself together. The
    page equivalent is how much of the queue the page absorbs: a layout that
    says more per page needs fewer pages to say it. The second key, *earlier
    candidate index*, is the standard's own and is why the archetype order is
    part of the specification.
    """
    return (score, -cand.consumed, cand.index, cand.archetype.name)


# ---------------------------------------------------------------------------
# The composer
# ---------------------------------------------------------------------------


def compose(
    content: ContentModel,
    direction: CreativeDirection,
    brand: Brand,
    *,
    tokens: TokenSet | None = None,
    document: str = "",
    page_format_name: str = "A4",
    max_pages: int = 40,
) -> PagePlan:
    """Compose ``content`` under ``direction`` for ``brand``."""
    tokens = tokens or brand.resolve_tokens()
    fmt = page_format(brand, page_format_name)
    ctx = _Context(
        content=content,
        direction=direction,
        fmt=fmt,
        type_metrics=TypeMetrics.from_tokens(tokens),
        document=document or (
            direction.applies_to[0] if direction.applies_to else direction.id
        ),
        ladder=sorted(ados.type_steps(), key=lambda k: ados.type_steps()[k]),
    )

    ordered, note = _promote_lead(order_blocks(content, direction), direction)
    notes: list[str] = [note] if note else []
    if direction.brand_version and direction.brand_version != brand.version:
        notes.append(
            f"direction was authored against brand {direction.brand_version}, "
            f"composed against {brand.version}"
        )

    queue: list[ContentBlock] = list(ordered)
    pages: list[Page] = []
    rejected: list[Rejection] = []

    while queue and len(pages) < max_pages:
        page_index = len(pages)
        # Page 0 is the cover and only page 0 is: a cover is the one page
        # whose job does not depend on what is in the queue.
        pool = (COVER,) if page_index == 0 else tuple(
            a for a in ARCHETYPES if a is not COVER
        )

        feasible, page_rejections = _candidates(pool, queue, ctx, page_index)
        if not feasible:
            rejected.extend(page_rejections)
            raise CompositionError(
                f"E-LAYOUT-001: no feasible page {page_index} for "
                f"{len(queue)} remaining block(s) under direction "
                f"{direction.id!r}. Rejections: "
                + "; ".join(f"{r.archetype} {r.rule} {r.reason}"
                            for r in page_rejections[:4])
                + ". Reducing text size or line width to make it fit is a "
                  "prohibited remedy (ADOS-7.5.070); change the direction's "
                  "density target or the content."
            )

        best_score, best = min(feasible, key=lambda pair: pair[0])
        pages.append(
            Page(
                index=page_index,
                archetype=best.archetype.name,
                grid=fmt.to_grid(),
                slots=best.slots,
                fill_ratio=best.fill_ratio,
                ink_coverage_max=best.ink_coverage_max,
                alignment_edges_x=best.alignment_edges_x,
                words=best.words,
                image_ratio=best.image_ratio,
                objective=best_score[0],
            )
        )
        rejected.extend(page_rejections)
        rejected.extend(
            Rejection(
                page=page_index,
                archetype=cand.archetype.name,
                kind=RejectionKind.OUTRANKED,
                reason=(
                    f"feasible, objective {score[0]:.0f} against "
                    f"{best_score[0]:.0f} for {best.archetype.name}"
                ),
            )
            for score, cand in _best_per_archetype(feasible)
            if cand.archetype is not best.archetype
        )
        del queue[: best.consumed]

    if queue:                                                # pragma: no cover
        raise CompositionError(
            f"E-LAYOUT-001: {len(queue)} block(s) unplaced after {max_pages} "
            f"pages. Omitting required content is a prohibited remedy "
            f"(ADOS-7.5.070)."
        )

    return PagePlan(
        document=ctx.document,
        project_name=content.project_name,
        brand_id=str(brand.brand_id),
        brand_version=brand.version,
        direction=direction.id,
        content_hash=content.content_hash,
        ados_edition=brand.ados_edition,
        pages=tuple(pages),
        rejected=tuple(rejected),
        notes=tuple(notes),
    )


def _candidates(
    pool: Iterable[Archetype],
    queue: Sequence[ContentBlock],
    ctx: _Context,
    page_index: int,
) -> tuple[list[tuple[tuple, Candidate]], list[Rejection]]:
    """Enumerate, lay out, filter. Returns the feasible set and the rejections."""
    feasible: list[tuple[tuple, Candidate]] = []
    rejections: list[Rejection] = []
    seen_infeasible: set[tuple[str, str]] = set()
    seen_shape: set[tuple] = set()

    allowed = {a.name for a in pool}
    for index, archetype in enumerate(ARCHETYPES):
        if archetype.name not in allowed:
            continue
        for cap in range(1, _capacity(archetype) + 1):
            assignment = _assign(archetype, queue, cap)
            if assignment is None:
                continue
            fills, consumed = assignment
            shape = (
                archetype.name,
                tuple(b.id for f in fills for b in f.blocks),
            )
            if shape in seen_shape:
                continue                       # a larger cap the queue cannot fill
            seen_shape.add(shape)

            cand = _lay_out(archetype, index, fills, consumed, ctx)
            if cand is None:
                key = (archetype.name, "H1")
                if key not in seen_infeasible:
                    seen_infeasible.add(key)
                    rejections.append(Rejection(
                        page=page_index, archetype=archetype.name,
                        kind=RejectionKind.INFEASIBLE, rule="H1",
                        reason="content is taller than the page",
                    ))
                continue

            broken = _violations(cand, ctx)
            if broken:
                rule, reason = broken[0]
                key = (archetype.name, rule)
                if key not in seen_infeasible:
                    seen_infeasible.add(key)
                    rejections.append(Rejection(
                        page=page_index, archetype=archetype.name,
                        kind=RejectionKind.INFEASIBLE, rule=rule, reason=reason,
                    ))
                continue

            score = _tie_break(cand, _objective(cand, ctx, page_index))
            feasible.append((score, cand))

    return feasible, rejections


def _best_per_archetype(
    feasible: Sequence[tuple[tuple, Candidate]]
) -> list[tuple[tuple, Candidate]]:
    best: dict[str, tuple[tuple, Candidate]] = {}
    for score, cand in feasible:
        current = best.get(cand.archetype.name)
        if current is None or score < current[0]:
            best[cand.archetype.name] = (score, cand)
    return [best[name] for name in sorted(best)]


# ---------------------------------------------------------------------------


def _fit_figure(
    block: ContentBlock,
    spec: SlotSpec,
    n_cols: int,
    fmt: PageFormat,
    tm: TypeMetrics,
    cap_mm: float,
    *,
    available_mm: float,
) -> tuple[float, float]:
    """Width and height for a figure plus its caption, fitted to whole columns.

    A portrait photograph run to the full width of an A4 page is 255 mm tall
    and does not fit on it. The remedy is not to crop the picture or to shrink
    the page: it is to place it across fewer columns, which is what a person
    laying out the page would do and what ``H7`` — extents aligned to the
    column grid — already requires. So the figure steps down a column at a
    time until it fits the height that is left, and stops at one column.

    Nothing here reduces text size or line width; those are prohibited
    remedies (``ADOS-7.5.070``). Only the picture moves.
    """
    lattice = tm.lattice_mm
    width = fmt.span_width_mm(n_cols)
    height = 0.0
    for cols in range(n_cols, 0, -1):
        width = fmt.span_width_mm(cols)
        caption_h = tm.text_height_mm(block.caption, cap_mm, width)
        height = _ceil_to(width / block.aspect_ratio + caption_h, lattice)
        if height <= available_mm + 1e-9:
            break
    return width, max(height, spec.min_rows * lattice)


def _ceil_to(value: float, step: float) -> float:
    return math.ceil(value / step - 1e-9) * step


def _distribute(total: int, weights: Sequence[int]) -> list[int]:
    """Split ``total`` columns by ``weights``, remainder to the earlier slots."""
    if not weights:
        return []
    sum_w = sum(weights)
    base = [total * w // sum_w for w in weights]
    remainder = total - sum(base)
    for i in range(remainder):
        base[i % len(base)] += 1
    return base
