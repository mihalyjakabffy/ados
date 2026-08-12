"""
brand/creative/scope.py

Where a command is allowed to act, and what actually changed.

Two things live here:

``resolve_scope`` / ``compose_scoped``
    Turns a requested :class:`CompositionScope` into an actual, bounded
    recomposition. For ``page`` scope this holds every page except the
    target frozen — copied byte-for-byte from the plan being scoped
    against — and recomposes only the target page's own original content,
    by calling :func:`brand.creative.composer._compose_one_page`, the same
    per-page step ``compose()`` itself uses. There is still exactly one
    Composer; this module calls its existing primitive a second time
    rather than building a second one.

``diff_pageplans``
    A structural comparison of two plans — which pages actually changed,
    which did not, which content blocks moved. Domain-level and reusable,
    not a testing utility: it is what a review UI, a version history or an
    audit trail would read from later.

**The honest boundary this module draws:** ``compose()``'s pagination is a
single sequential pass — page 5's content is only known because pages 1–4
already consumed what came before it. A scoped page recomposition is
therefore only *exact* (every other page provably unchanged) when the
target page's own original set of blocks still fits as one page after the
change; if it would now need two, or one and a half, this module refuses
rather than silently letting the change ripple into pages it was not asked
to touch. That refusal is :class:`ScopeInfeasibleError`, not a bug to be
worked around later. Region scope is refused outright, for a different
reason: ``PagePlan`` has no ``Region`` grouping between a ``Page`` and its
``Slot``s in the Creative Layer today, so there is nothing to resolve a
region target *to*.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from brand import ados
from brand.content.model import ContentModel
from brand.creative.composer import (
    CompositionError,
    TypeMetrics,
    _Context,
    _compose_one_page,
    _promote_lead,
    compose,
    order_blocks,
    page_format,
)
from brand.creative.direction import CreativeDirection
from brand.creative.plan import PagePlan
from brand.models.brand import Brand
from brand.models.tokens import TokenSet

_Frozen = ConfigDict(frozen=True, extra="forbid")


class ScopeType(str, Enum):
    DOCUMENT = "document"
    PAGE = "page"
    REGION = "region"
    CONTENT_BLOCK = "contentBlock"


class CompositionScope(BaseModel):
    model_config = _Frozen

    type: ScopeType
    id: str = ""


class UnsupportedScopeError(RuntimeError):
    """A scope type the Creative Layer has no addressable unit for yet."""


class ScopeInfeasibleError(RuntimeError):
    """The scope resolved, but the requested change cannot stay inside it."""


class PagePlanDiff(BaseModel):
    """A structural comparison of two plans. Page identity is ``Page.index``
    (already stable and deterministic — see the module docstring; no new
    identity scheme was introduced for this)."""

    model_config = _Frozen

    changed_pages: tuple[int, ...]
    unchanged_pages: tuple[int, ...]
    changed_blocks: tuple[str, ...]
    unchanged_blocks: tuple[str, ...]

    @property
    def pages_affected(self) -> int:
        return len(self.changed_pages)


def diff_pageplans(before: PagePlan, after: PagePlan) -> PagePlanDiff:
    """Page-by-page equality. A page is "changed" if its full Page object
    (archetype, grid, every slot's geometry and content) differs at all."""
    n = max(len(before.pages), len(after.pages))
    changed: list[int] = []
    unchanged: list[int] = []
    for i in range(n):
        b = before.pages[i] if i < len(before.pages) else None
        a = after.pages[i] if i < len(after.pages) else None
        (changed if a != b else unchanged).append(i)

    changed_blocks: set[str] = set()
    unchanged_blocks: set[str] = set()
    for i in changed:
        if i < len(after.pages):
            changed_blocks.update(after.pages[i].block_ids)
        if i < len(before.pages):
            changed_blocks.update(before.pages[i].block_ids)
    for i in unchanged:
        if i < len(after.pages):
            unchanged_blocks.update(after.pages[i].block_ids)
    unchanged_blocks -= changed_blocks

    return PagePlanDiff(
        changed_pages=tuple(changed),
        unchanged_pages=tuple(unchanged),
        changed_blocks=tuple(sorted(changed_blocks)),
        unchanged_blocks=tuple(sorted(unchanged_blocks)),
    )


def resolve_scope(base_plan: PagePlan, scope: CompositionScope) -> CompositionScope:
    """Validate and normalise a requested scope against a real plan.

    A ``contentBlock`` scope resolves to the ``page`` scope of the page
    that currently carries it — the Composer's smallest addressable
    recomposition unit is a page, not a block, and this function says so
    by the value it returns rather than by a comment a caller might miss.
    """
    if scope.type is ScopeType.DOCUMENT:
        return scope

    if scope.type is ScopeType.REGION:
        raise UnsupportedScopeError(
            "region-scoped composition is not supported: PagePlan has no Region "
            "grouping between Page and Slot in the Creative Layer today. Use "
            "page or document scope."
        )

    if scope.type is ScopeType.PAGE:
        try:
            idx = int(scope.id)
        except ValueError:
            raise ScopeInfeasibleError(f"page scope id {scope.id!r} is not a page index") from None
        if not (0 <= idx < len(base_plan.pages)):
            raise ScopeInfeasibleError(
                f"page {idx} does not exist in the current {len(base_plan.pages)}-page plan"
            )
        return CompositionScope(type=ScopeType.PAGE, id=str(idx))

    if scope.type is ScopeType.CONTENT_BLOCK:
        for page in base_plan.pages:
            if scope.id in page.block_ids:
                return CompositionScope(type=ScopeType.PAGE, id=str(page.index))
        raise ScopeInfeasibleError(f"content block {scope.id!r} is not on any page of the current plan")

    raise UnsupportedScopeError(f"unknown scope type {scope.type!r}")  # pragma: no cover


def compose_scoped(
    base_plan: PagePlan,
    scope: CompositionScope,
    content: ContentModel,
    direction: CreativeDirection,
    brand: Brand,
    *,
    tokens: TokenSet | None = None,
    page_format_name: str = "A4",
) -> tuple[PagePlan, PagePlanDiff, CompositionScope]:
    """Recompose ``content`` under ``direction``, bounded by ``scope``.

    Returns ``(new_plan, diff, resolved_scope)``. Raises
    :class:`UnsupportedScopeError` / :class:`ScopeInfeasibleError` /
    :class:`~brand.creative.composer.CompositionError` — the caller (the
    API route) maps each to its own error, and none of them return a
    partial or invalid plan.
    """
    resolved = resolve_scope(base_plan, scope)
    tokens = tokens or brand.resolve_tokens()

    if resolved.type is ScopeType.DOCUMENT:
        new_plan = compose(
            content, direction, brand,
            tokens=tokens, document=base_plan.document, page_format_name=page_format_name,
        )
        return new_plan, diff_pageplans(base_plan, new_plan), resolved

    # -- page scope -----------------------------------------------------
    idx = int(resolved.id)
    target_ids = [b for b in base_plan.pages[idx].block_ids]
    available = {b.id for b in content.blocks}
    local_ids = [b for b in target_ids if b in available]
    local_blocks = tuple(content.by_id(b) for b in local_ids)

    fmt = page_format(brand, page_format_name)
    ctx = _Context(
        content=content,
        direction=direction,
        fmt=fmt,
        type_metrics=TypeMetrics.from_tokens(tokens),
        document=base_plan.document,
        ladder=sorted(ados.type_steps(), key=lambda k: ados.type_steps()[k]),
    )

    local_content = ContentModel(
        project_id=content.project_id, project_name=content.project_name, blocks=local_blocks
    )
    ordered = order_blocks(local_content, direction)
    if idx == 0:
        ordered, _note = _promote_lead(ordered, direction)

    queue = list(ordered)
    try:
        new_page, consumed, page_rejected = _compose_one_page(queue, ctx, idx)
    except CompositionError as exc:
        raise ScopeInfeasibleError(
            f"page {idx}'s content does not compose under the requested change: {exc}"
        ) from exc

    if consumed != len(queue):
        raise ScopeInfeasibleError(
            f"page {idx}'s original {len(queue)} block(s) no longer fit on a single page "
            f"under the requested change ({consumed} placed) — a scoped composition must "
            f"leave the page count unchanged. Try a smaller strength, or recompose the "
            f"whole document instead."
        )

    new_pages = list(base_plan.pages)
    new_pages[idx] = new_page
    new_rejected = tuple(r for r in base_plan.rejected if r.page != idx) + tuple(page_rejected)

    notes = list(base_plan.notes)
    if direction.id != base_plan.direction:
        notes.append(
            f"page {idx} was recomposed under direction {direction.id!r}; every other page "
            f"remains composed under {base_plan.direction!r} — compose() has no page-scoped "
            f"direction, only a page-scoped recomposition of content already assigned to it."
        )

    new_plan = base_plan.model_copy(
        update={
            "pages": tuple(new_pages),
            "rejected": new_rejected,
            "direction": direction.id,
            "content_hash": content.content_hash,
            "notes": tuple(notes),
        }
    )
    return new_plan, diff_pageplans(base_plan, new_plan), resolved
