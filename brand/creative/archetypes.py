"""
brand/creative/archetypes.py

The closed set of page shapes the composer may produce.

Eight, deliberately. Enough to give a document genuine variety — a cover, an
image spread, a metric band and a credit page do not look like one another —
and few enough that a person can hold the whole set in mind and say which one
a page is. Forty archetypes would be a maintenance problem and would produce
slop: the appearance of variety with no argument behind any of it.

An archetype is **structure only**. It says how many things sit beside each
other and what kind of content each place accepts. It does not name a
typeface, a colour, a millimetre or a point size — those come from the brand,
and a page shape that carried its own copy of them would be the second source
of truth the whole system is arranged to prevent.

Sizes are expressed two ways, both relative:

``weight``
    A slot's share of its row. Resolved to whole columns against whatever
    column count the brand's grid declares for the format, so the same
    archetype works on a four-column A4 and a six-column A3.

``rank``
    Which step of the brand's type scale the slot's text is set at, named by
    what it *is* rather than how big it is. The direction chooses the display
    and body steps; the ranks in between are derived from them.

The order of :data:`ARCHETYPES` is load-bearing: it is the candidate order,
and *earlier candidate index* is the second tie-break in ``ADOS-7.5.050``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from brand.content.model import BlockType

#: Fraction of a cap-height band covered by ink in continuous latin text.
#: Not an ADOS value — the standard sets the ceiling (``local_coverage_max``)
#: and not the ink a face puts down — so it is stated here once, measured over
#: body copy at normal word spacing, and used by the H12 estimate. A practice
#: with a notably heavier face should measure its own and change it here.
GLYPH_INK: float = 0.36


class Rank(str, Enum):
    """A slot's place in the hierarchy, named by role rather than by size.

    ``DISPLAY`` and ``BODY`` come straight from the direction. ``LEAD`` and
    ``CAPTION`` are derived from ``BODY`` on the brand's own scale, so a brand
    with a different scale still gets a hierarchy that reads.
    """

    DISPLAY = "display"
    LEAD = "lead"
    BODY = "body"
    LABEL = "label"
    CAPTION = "caption"


@dataclass(frozen=True)
class SlotSpec:
    """One place on a page, and what may go in it."""

    component: str
    accepts: tuple[BlockType, ...] = ()
    weight: int = 1
    rank: Rank = Rank.BODY
    repeat: int = 1
    required: bool = True
    emphasis: bool = False
    min_rows: int = 1

    @property
    def is_fixed(self) -> bool:
        """A slot fed by the content model itself, not by a content block.

        The project's name on a cover is not a block: it is the identity of
        the thing the blocks are about, and making it a block would let a
        composer drop it.
        """
        return not self.accepts


@dataclass(frozen=True)
class RowSpec:
    """Slots that sit beside one another.

    ``balance`` deals the row's blocks round-robin across its slots instead of
    filling the first one before starting the second. A metric band wants two
    columns of three, not one column of six and an empty column beside it.
    """

    slots: tuple[SlotSpec, ...]
    balance: bool = False


@dataclass(frozen=True)
class Archetype:
    """One page shape."""

    name: str
    purpose: str
    rows: tuple[RowSpec, ...]

    @property
    def slots(self) -> tuple[SlotSpec, ...]:
        return tuple(s for row in self.rows for s in row.slots)

    def accepts(self, block_type: BlockType) -> bool:
        return any(block_type in s.accepts for s in self.slots)


_FIGURES = (BlockType.IMAGE, BlockType.DRAWING, BlockType.DIAGRAM)
_PROSE = (BlockType.NARRATIVE, BlockType.QUOTE)
_VALUES = (BlockType.METRIC, BlockType.FACT)
_BACK_MATTER = (BlockType.CREDIT, BlockType.REFERENCE, BlockType.FACT)

#: What a running text column will absorb. Prose and short labelled values,
#: because a fact set as a label-and-value row belongs in running text and a
#: metric set large does not. Figures are excluded: a photograph interrupts a
#: column rather than continuing it, which is why the archetypes that carry
#: one say so in their name.
_FLOW = _PROSE + (BlockType.FACT,)

#: How many blocks a flowing column will take before the page is considered
#: full. High, because the binding limit should be the page (``H1``) and not
#: an arbitrary count — the composer enumerates every count from one upwards
#: and the objective picks the one closest to the direction's density.
_FLOW_MAX = 14


COVER = Archetype(
    name="cover",
    purpose=(
        "What this document is about and who issued it. One page, and the "
        "only one where the practice's own identity outranks the project's."
    ),
    rows=(
        RowSpec((
            SlotSpec("project-title", rank=Rank.DISPLAY, emphasis=True, min_rows=4),
        )),
        RowSpec((
            SlotSpec("hero", _FIGURES, rank=Rank.CAPTION, required=False, min_rows=8),
        )),
        RowSpec((
            SlotSpec("lead-value", _VALUES, rank=Rank.LEAD, required=False,
                     min_rows=5),
        )),
        RowSpec((
            SlotSpec("standfirst", _PROSE, rank=Rank.LEAD, required=False, min_rows=3),
        )),
        RowSpec((
            SlotSpec("issue", rank=Rank.LABEL, min_rows=2),
        )),
    ),
)

FULL_IMAGE = Archetype(
    name="full-image",
    purpose=(
        "One photograph at the largest size the page allows. The page a "
        "portfolio is bought on, and the page a technical report has none of."
    ),
    rows=(
        RowSpec((SlotSpec("figure", _FIGURES, rank=Rank.CAPTION, min_rows=12),)),
    ),
)

TEXT_LED = Archetype(
    name="text-led",
    purpose=(
        "Running argument: a marginal column that says which part of the "
        "argument this is, and up to three paragraphs in the measure beside "
        "it. The same two-column body the PTS Word templates already use, so "
        "a generated report and a typed one set text at the same width."
    ),
    rows=(
        RowSpec((
            SlotSpec("section-label", weight=1, rank=Rank.LABEL, min_rows=2),
            SlotSpec("body", _FLOW, weight=3, rank=Rank.BODY,
                     repeat=_FLOW_MAX, min_rows=4),
        )),
        # A figure may close the page. Without it a paragraph followed by a
        # photograph becomes two pages — the text page a tenth full and the
        # picture page on its own — which is not how anybody lays out a
        # report. The slot is optional, so the objective decides whether the
        # picture is better here or leading a page of its own.
        RowSpec((
            SlotSpec("figure", _FIGURES, rank=Rank.CAPTION,
                     required=False, min_rows=8),
        )),
    ),
)

TEXT_IMAGE = Archetype(
    name="text-image",
    purpose="A photograph and the paragraphs that explain it, side by side.",
    rows=(
        RowSpec((
            SlotSpec("figure", _FIGURES, weight=1, rank=Rank.CAPTION, min_rows=10),
            SlotSpec("body", _FLOW, weight=1, rank=Rank.BODY,
                     repeat=_FLOW_MAX, min_rows=10),
        )),
    ),
)

IMAGE_PAIR = Archetype(
    name="image-pair",
    purpose=(
        "Two photographs read against each other — before and after, or two "
        "moments of the same space. The comparison is the content."
    ),
    rows=(
        RowSpec((
            SlotSpec("figure-a", _FIGURES, weight=1, rank=Rank.CAPTION, min_rows=8),
            SlotSpec("figure-b", _FIGURES, weight=1, rank=Rank.CAPTION, min_rows=8),
        )),
    ),
)

METRIC_BAND = Archetype(
    name="metric-band",
    purpose=(
        "The numbers, set large enough to be read across a table. Each one "
        "carries its provenance, because a number without one is a claim."
    ),
    rows=(
        RowSpec((SlotSpec("section-label", rank=Rank.LABEL, min_rows=2),)),
        RowSpec(
            (
                SlotSpec("metric", _VALUES, weight=1, rank=Rank.LEAD,
                         repeat=6, min_rows=5),
                SlotSpec("metric", _VALUES, weight=1, rank=Rank.LEAD,
                         repeat=6, required=False, min_rows=5),
            ),
            balance=True,
        ),
    ),
)

DRAWING = Archetype(
    name="drawing",
    purpose=(
        "A model-derived view at a stated scale. Distinct from a photograph "
        "because it is issued information, not illustration."
    ),
    rows=(
        RowSpec((
            SlotSpec("view", (BlockType.DRAWING, BlockType.DIAGRAM),
                     rank=Rank.CAPTION, min_rows=14),
        )),
        RowSpec((SlotSpec("notes", _FLOW, rank=Rank.BODY, repeat=4,
                          required=False, min_rows=3),)),
    ),
)

CREDIT = Archetype(
    name="credit",
    purpose="Who did what, and what this document points at. The last page.",
    rows=(
        RowSpec((
            SlotSpec("section-label", weight=1, rank=Rank.LABEL, min_rows=2),
            SlotSpec("entry", _BACK_MATTER, weight=3, rank=Rank.CAPTION,
                     repeat=_FLOW_MAX, min_rows=2),
        )),
    ),
)


#: Candidate order. Earlier is preferred when two candidates score equally,
#: which is the second entry of the ``ADOS-7.5.050`` tie-break, so this
#: sequence is part of the specification of the output and not a listing
#: convenience. It runs from the most structurally committed shape to the
#: least: a cover can only ever be a cover, whereas text-led will accept
#: almost anything with words in it and would otherwise absorb the document.
ARCHETYPES: tuple[Archetype, ...] = (
    COVER,
    METRIC_BAND,
    IMAGE_PAIR,
    DRAWING,
    FULL_IMAGE,
    TEXT_IMAGE,
    CREDIT,
    TEXT_LED,
)

ARCHETYPE_NAMES: tuple[str, ...] = tuple(a.name for a in ARCHETYPES)

BY_NAME: dict[str, Archetype] = {a.name: a for a in ARCHETYPES}


def get_archetype(name: str) -> Archetype:
    try:
        return BY_NAME[name]
    except KeyError:
        raise KeyError(
            f"unknown archetype {name!r}. The set is closed: "
            + ", ".join(ARCHETYPE_NAMES)
        ) from None
