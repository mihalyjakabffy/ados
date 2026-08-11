"""
brand/content/model.py

A project's content as typed blocks, independent of any document.

Three properties make the model work, and each exists for a reason a document
generator without them cannot satisfy:

**Typed.** A block declares what it *is* — narrative, metric, image, drawing —
so a composer can choose a component for it. An untyped string can only be
poured into a slot somebody chose in advance, which is what a template does.

**Roled.** A block declares where it sits in the argument — context, problem,
intervention, outcome, evidence. That is what lets one content model be
ordered three different ways into three different documents. A portfolio
spread leads with context; a technical report leads with the intervention;
neither is a different set of facts.

**Prioritised.** Emphasis is an *authored* fact, ranked 1 (lead) to 5
(supporting). A composer that guesses which block matters produces a document
whose emphasis is an accident. Priority is the one thing in this file a machine
must not infer.

Metrics additionally carry **provenance**. A number in a client report whose
origin nobody can state is a liability, and the platform already knows where
its numbers come from — a design state, an agent, a precedent — so it costs
nothing to carry it and a great deal not to.

Nothing here knows about pages, typefaces, colours or millimetres. A field in
this file that described appearance would be a template in disguise.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from enum import Enum
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

_Frozen = ConfigDict(frozen=True, extra="forbid")

#: Average characters per word, including the trailing space. Used only to
#: estimate how much vertical space a narrative block needs; it is an English
#: convention, stated here rather than buried in the composer so a Hungarian
#: or German set can change it in one place.
CHARS_PER_WORD: float = 6.0


class BlockType(str, Enum):
    """What a block *is*. Closed, because a composer switches on it."""

    NARRATIVE = "narrative"      # prose: runs in the measure
    FACT = "fact"                # a labelled short value, set as a row
    METRIC = "metric"            # a number with a unit, set large
    IMAGE = "image"              # a photograph
    DRAWING = "drawing"          # a model-derived view
    DIAGRAM = "diagram"          # an explanatory figure
    TABLE = "table"              # tabulated rows
    QUOTE = "quote"              # attributed speech
    CREDIT = "credit"            # who did what
    REFERENCE = "reference"      # a pointer to another document


class BlockRole(str, Enum):
    """Where a block sits in the argument the document is making."""

    CONTEXT = "context"
    PROBLEM = "problem"
    INTERVENTION = "intervention"
    OUTCOME = "outcome"
    EVIDENCE = "evidence"
    DETAIL = "detail"
    PROVENANCE = "provenance"


#: Types that carry running prose and therefore need a measure.
TEXT_TYPES: frozenset[BlockType] = frozenset(
    {BlockType.NARRATIVE, BlockType.QUOTE}
)

#: Types that occupy a rectangle whose height comes from an aspect ratio.
FIGURE_TYPES: frozenset[BlockType] = frozenset(
    {BlockType.IMAGE, BlockType.DRAWING, BlockType.DIAGRAM}
)


class ContentBlock(BaseModel):
    """One addressable piece of a project's content."""

    model_config = _Frozen

    id: str = Field(pattern=r"^[a-z]{3}-\d{2,3}$")
    type: BlockType
    role: BlockRole
    priority: int = Field(ge=1, le=5)

    # Prose ---------------------------------------------------------------
    text: str = Field(default="", max_length=8000)

    # Labelled values -----------------------------------------------------
    label: str = Field(default="", max_length=120)
    value: float | str | None = None
    unit: str = Field(default="", max_length=24)

    # Figures -------------------------------------------------------------
    path: str = Field(default="", max_length=400)
    aspect: str = Field(default="", pattern=r"^$|^\d{1,3}:\d{1,3}$")
    caption: str = Field(default="", max_length=400)
    sequence_position: str = Field(default="", max_length=40)

    # Everything, where it is known ---------------------------------------
    provenance: str = Field(
        default="",
        max_length=200,
        description="Where this came from: a design state, an agent, a "
        "precedent, or a named author.",
    )

    @model_validator(mode="after")
    def _require_what_the_type_needs(self) -> "ContentBlock":
        """A block that cannot be rendered must not be constructible.

        The alternative is a composer full of ``if block.text:`` guards and a
        document with a hole where a caption should be.
        """
        if self.type in TEXT_TYPES and not self.text.strip():
            raise ValueError(f"{self.id}: a {self.type.value} block needs text")
        if self.type is BlockType.METRIC:
            if not self.label or self.value is None:
                raise ValueError(
                    f"{self.id}: a metric needs a label and a value — an "
                    f"unlabelled number is not evidence"
                )
            if not self.provenance:
                raise ValueError(
                    f"{self.id}: a metric needs provenance. A number in a "
                    f"client document whose origin nobody can state is a "
                    f"liability, and the platform already knows the origin."
                )
        if self.type in FIGURE_TYPES:
            if not self.path:
                raise ValueError(f"{self.id}: a {self.type.value} block needs a path")
            if not self.aspect:
                raise ValueError(
                    f"{self.id}: a {self.type.value} block needs an aspect "
                    f"ratio. Its height on the page is derived from it, so a "
                    f"figure without one cannot be placed."
                )
        if self.type is BlockType.FACT and not self.label:
            raise ValueError(f"{self.id}: a fact needs a label")
        return self

    # ------------------------------------------------------------------

    @property
    def words(self) -> int:
        """Word count of the block's prose. 0 for anything that is not prose."""
        return len(self.text.split())

    @property
    def aspect_ratio(self) -> float:
        """Width ÷ height. Raises for a block that has no aspect."""
        if not self.aspect:
            raise ValueError(f"{self.id} has no aspect ratio")
        w, h = self.aspect.split(":")
        return float(w) / float(h)

    @property
    def display_text(self) -> str:
        """What a renderer puts on the page for this block, as one string.

        The *value* only — the label travels separately, because a composer
        sets a label and a value at different ranks and a renderer that had to
        split a string back apart would be guessing where.
        """
        if self.type is BlockType.METRIC:
            formatted = format_value(self.value)
            return f"{formatted}{(' ' + self.unit) if self.unit else ''}"
        if self.type is BlockType.FACT:
            return format_value(self.value)
        if self.type in FIGURE_TYPES:
            return self.caption
        return self.text


class ContentModel(BaseModel):
    """Everything a project has to say, before anyone decides how to say it."""

    model_config = _Frozen

    project_id: uuid.UUID
    project_name: str = Field(min_length=1, max_length=200)
    source_state: uuid.UUID | None = Field(
        default=None,
        description="The DesignState this was extracted from, where it came "
        "from one. A content model with no source is authored, not derived, "
        "and the distinction matters when a number is questioned.",
    )
    blocks: tuple[ContentBlock, ...] = ()

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "ContentModel":
        seen: set[str] = set()
        for block in self.blocks:
            if block.id in seen:
                raise ValueError(f"duplicate block id {block.id!r}")
            seen.add(block.id)
        return self

    # -- selection --------------------------------------------------------

    def of_type(self, *types: BlockType) -> tuple[ContentBlock, ...]:
        wanted = set(types)
        return tuple(b for b in self.blocks if b.type in wanted)

    def with_role(self, *roles: BlockRole) -> tuple[ContentBlock, ...]:
        wanted = set(roles)
        return tuple(b for b in self.blocks if b.role in wanted)

    def by_id(self, block_id: str) -> ContentBlock:
        for block in self.blocks:
            if block.id == block_id:
                return block
        raise KeyError(
            f"no block {block_id!r}. Known: {', '.join(b.id for b in self.blocks)}"
        )

    @property
    def words(self) -> int:
        return sum(b.words for b in self.blocks)

    # -- identity ---------------------------------------------------------

    @property
    def content_hash(self) -> str:
        """SHA-256 over the content, as the platform hashes a design state.

        Two content models with the same hash compose to the same document
        under the same brand and direction — which is the claim the whole
        Creative Layer rests on, so the hash travels into the output.
        """
        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {**self.model_dump(mode="json"), "content_hash": self.content_hash}


#: Digit-group separator. A thin space, per ISO 31-0 — a comma means a decimal
#: point in half of Europe and this system is used in both halves. Named
#: rather than written as an invisible literal in the middle of an expression.
THIN_SPACE = " "


def format_value(value: float | str | None) -> str:
    """A number as a reader wants it, deterministically.

    Thousands separated, and no trailing ``.0`` on a whole number: a cost
    printed as ``4074000.0`` reads as a machine's idea of a number, and a
    reader who has to count digits to find the millions has been given a
    string rather than a figure. Locale-independent on purpose — the output
    must not change with the machine that produced it.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if float(value).is_integer():
        return f"{int(value):,}".replace(",", THIN_SPACE)
    return f"{value:,.1f}".replace(",", THIN_SPACE)


def block_id(prefix: str, n: int) -> str:
    """``('ctx', 1) → 'ctx-01'`` — the id form the extractor emits."""
    return f"{prefix}-{n:02d}"


def renumber(blocks: Iterable[ContentBlock]) -> tuple[ContentBlock, ...]:
    """Reassign ids per type prefix, in the order given.

    Used by the extractor so that ids are a function of the content and its
    emission order alone. An id that depended on a dict's iteration order
    would make two runs over the same state produce two different models.
    """
    counters: dict[str, int] = {}
    out: list[ContentBlock] = []
    for block in blocks:
        prefix = _PREFIX[block.type]
        counters[prefix] = counters.get(prefix, 0) + 1
        out.append(block.model_copy(update={"id": block_id(prefix, counters[prefix])}))
    return tuple(out)


#: Type → id prefix. Three letters so an id is readable in a log line.
_PREFIX: dict[BlockType, str] = {
    BlockType.NARRATIVE: "nar",
    BlockType.FACT: "fct",
    BlockType.METRIC: "met",
    BlockType.IMAGE: "img",
    BlockType.DRAWING: "drw",
    BlockType.DIAGRAM: "dgm",
    BlockType.TABLE: "tbl",
    BlockType.QUOTE: "quo",
    BlockType.CREDIT: "crd",
    BlockType.REFERENCE: "ref",
}
