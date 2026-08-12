"""
brand/creative/scope.py — the composition-scope layer.

These tests are about the boundary this module draws: that page scope is
*genuinely* bounded (every other page is byte-for-byte untouched, not just
disclosed as unchanged), that region scope is honestly refused rather than
faked, that contentBlock scope resolves to its containing page rather than
pretending independent block layout exists, and that a scoped recomposition
that no longer fits on one page fails loudly instead of spilling into pages
it was never asked to touch.
"""

from __future__ import annotations

import pytest

from brand.creative.composer import compose
from brand.creative.direction import CreativeDirection
from brand.creative.directions import get_direction
from brand.creative.plan import PagePlan
from brand.creative.scope import (
    CompositionScope,
    PagePlanDiff,
    ScopeInfeasibleError,
    ScopeType,
    UnsupportedScopeError,
    compose_scoped,
    diff_pageplans,
    resolve_scope,
)
from brand.examples.malthouse import malthouse_content


@pytest.fixture(scope="module")
def content():
    return malthouse_content()


@pytest.fixture(scope="module")
def studio_om():
    from brand.examples.studio_om import studio_om as build

    return build()


@pytest.fixture()
def direction():
    return get_direction("editorial-quiet")


@pytest.fixture(scope="module")
def base_plan(content, studio_om):
    return compose(content, get_direction("editorial-quiet"), studio_om)


# ---------------------------------------------------------------------------
# resolve_scope
# ---------------------------------------------------------------------------


def test_document_scope_resolves_to_itself(base_plan):
    scope = CompositionScope(type=ScopeType.DOCUMENT)
    assert resolve_scope(base_plan, scope) == scope


def test_region_scope_is_refused_outright(base_plan):
    with pytest.raises(UnsupportedScopeError, match="[Rr]egion"):
        resolve_scope(base_plan, CompositionScope(type=ScopeType.REGION, id="hero"))


def test_a_valid_page_scope_resolves_and_normalises(base_plan):
    resolved = resolve_scope(base_plan, CompositionScope(type=ScopeType.PAGE, id="4"))
    assert resolved == CompositionScope(type=ScopeType.PAGE, id="4")


def test_an_out_of_range_page_is_infeasible(base_plan):
    with pytest.raises(ScopeInfeasibleError, match="does not exist"):
        resolve_scope(base_plan, CompositionScope(type=ScopeType.PAGE, id="99"))


def test_a_non_numeric_page_id_is_infeasible(base_plan):
    with pytest.raises(ScopeInfeasibleError):
        resolve_scope(base_plan, CompositionScope(type=ScopeType.PAGE, id="cover"))


def test_a_content_block_scope_resolves_to_its_containing_page(base_plan):
    # met-01 is placed on the metric-band page (index 4 for this fixture).
    target_page = next(p.index for p in base_plan.pages if "met-01" in p.block_ids)
    resolved = resolve_scope(base_plan, CompositionScope(type=ScopeType.CONTENT_BLOCK, id="met-01"))
    assert resolved == CompositionScope(type=ScopeType.PAGE, id=str(target_page))


def test_an_unknown_content_block_is_infeasible(base_plan):
    with pytest.raises(ScopeInfeasibleError, match="not on any page"):
        resolve_scope(base_plan, CompositionScope(type=ScopeType.CONTENT_BLOCK, id="nope-99"))


# ---------------------------------------------------------------------------
# diff_pageplans
# ---------------------------------------------------------------------------


def test_diffing_a_plan_against_itself_reports_nothing_changed(base_plan):
    diff = diff_pageplans(base_plan, base_plan)
    assert diff.changed_pages == ()
    assert diff.unchanged_pages == tuple(range(len(base_plan.pages)))
    assert diff.changed_blocks == ()
    assert diff.pages_affected == 0


def test_diff_reports_exactly_the_pages_that_differ(base_plan):
    target = 4
    inflated_page = base_plan.pages[target].model_copy(
        update={"slots": base_plan.pages[target].slots + base_plan.pages[1].slots[:1]}
    )
    pages = list(base_plan.pages)
    pages[target] = inflated_page
    other = base_plan.model_copy(update={"pages": tuple(pages)})

    diff = diff_pageplans(base_plan, other)
    assert diff.changed_pages == (target,)
    assert diff.unchanged_pages == tuple(i for i in range(len(base_plan.pages)) if i != target)
    assert diff.pages_affected == 1
    # every block on the changed page appears on the changed side, and no
    # block that only ever appears on an unchanged page leaks into it.
    assert set(base_plan.pages[target].block_ids) <= set(diff.changed_blocks)
    assert not set(diff.changed_blocks) & set(diff.unchanged_blocks)


# ---------------------------------------------------------------------------
# compose_scoped — document scope delegates, unchanged
# ---------------------------------------------------------------------------


def test_document_scope_is_exactly_compose(content, direction, studio_om, base_plan):
    scope = CompositionScope(type=ScopeType.DOCUMENT)
    new_plan, diff, resolved = compose_scoped(base_plan, scope, content, direction, studio_om)
    direct = compose(content, direction, studio_om)
    assert new_plan.plan_hash == direct.plan_hash
    assert resolved.type is ScopeType.DOCUMENT


# ---------------------------------------------------------------------------
# compose_scoped — page scope: the mandatory isolation property
# ---------------------------------------------------------------------------


def test_page_scoped_composition_leaves_every_other_page_byte_identical(
    content, direction, studio_om, base_plan
):
    target = 4
    denser = CreativeDirection.model_validate(
        {**direction.model_dump(mode="json"), "id": "editorial-quiet-denser", "text_density": 0.5}
    )

    new_plan, diff, resolved = compose_scoped(
        base_plan, CompositionScope(type=ScopeType.PAGE, id=str(target)), content, denser, studio_om
    )

    assert resolved == CompositionScope(type=ScopeType.PAGE, id=str(target))
    for i, page in enumerate(base_plan.pages):
        if i == target:
            continue
        assert new_plan.pages[i] == page, f"page {i} must be byte-identical but changed"
    assert diff.changed_pages == (target,)
    assert diff.unchanged_pages == tuple(i for i in range(len(base_plan.pages)) if i != target)
    assert len(new_plan.pages) == len(base_plan.pages)


def test_page_scoped_composition_actually_changes_the_target_page(
    content, direction, studio_om, base_plan
):
    target = 4
    denser = CreativeDirection.model_validate(
        {**direction.model_dump(mode="json"), "id": "editorial-quiet-denser2", "text_density": 0.55}
    )
    new_plan, diff, _ = compose_scoped(
        base_plan, CompositionScope(type=ScopeType.PAGE, id=str(target)), content, denser, studio_om
    )
    assert new_plan.pages[target] != base_plan.pages[target]
    assert target in diff.changed_pages


def test_recompose_at_page_scope_with_unchanged_inputs_is_a_no_op(
    content, direction, studio_om, base_plan
):
    """recompose_page's whole point: same content, same direction, same page."""
    new_plan, diff, _ = compose_scoped(
        base_plan, CompositionScope(type=ScopeType.PAGE, id="4"), content, direction, studio_om
    )
    assert new_plan.pages[4] == base_plan.pages[4]
    assert new_plan == base_plan
    assert diff.changed_pages == ()


def test_a_direction_change_at_page_scope_is_disclosed_in_a_note(
    content, direction, studio_om, base_plan
):
    other = CreativeDirection.model_validate(
        {**direction.model_dump(mode="json"), "id": "image-led-ish", "image_ratio": min(1.0, direction.image_ratio + 0.2)}
    )
    new_plan, _, _ = compose_scoped(
        base_plan, CompositionScope(type=ScopeType.PAGE, id="4"), content, other, studio_om
    )
    assert any("page 4" in n and "every other page" in n for n in new_plan.notes)
    assert new_plan.direction == other.id


# ---------------------------------------------------------------------------
# compose_scoped — contentBlock scope resolves through to its page
# ---------------------------------------------------------------------------


def test_content_block_scope_recomposes_only_its_page(content, direction, studio_om, base_plan):
    target = next(p.index for p in base_plan.pages if "met-01" in p.block_ids)
    denser = CreativeDirection.model_validate(
        {**direction.model_dump(mode="json"), "id": "editorial-quiet-denser3", "text_density": 0.55}
    )
    new_plan, diff, resolved = compose_scoped(
        base_plan, CompositionScope(type=ScopeType.CONTENT_BLOCK, id="met-01"), content, denser, studio_om
    )
    assert resolved == CompositionScope(type=ScopeType.PAGE, id=str(target))
    for i, page in enumerate(base_plan.pages):
        if i == target:
            continue
        assert new_plan.pages[i] == page


# ---------------------------------------------------------------------------
# compose_scoped — region is refused, not faked
# ---------------------------------------------------------------------------


def test_region_scope_raises_instead_of_composing(content, direction, studio_om, base_plan):
    with pytest.raises(UnsupportedScopeError):
        compose_scoped(
            base_plan, CompositionScope(type=ScopeType.REGION, id="hero"), content, direction, studio_om
        )


# ---------------------------------------------------------------------------
# compose_scoped — determinism
# ---------------------------------------------------------------------------


def test_page_scoped_composition_is_deterministic(content, direction, studio_om, base_plan):
    denser = CreativeDirection.model_validate(
        {**direction.model_dump(mode="json"), "id": "editorial-quiet-denser4", "text_density": 0.5}
    )
    scope = CompositionScope(type=ScopeType.PAGE, id="4")
    p1, d1, _ = compose_scoped(base_plan, scope, content, denser, studio_om)
    p2, d2, _ = compose_scoped(base_plan, scope, content, denser, studio_om)
    assert p1 == p2
    assert p1.plan_hash == p2.plan_hash
    assert d1 == d2


# ---------------------------------------------------------------------------
# compose_scoped — a target page that no longer fits as one page must fail
# honestly, not spill into neighbouring pages.
# ---------------------------------------------------------------------------


def test_a_target_page_that_no_longer_fits_on_one_page_is_scope_infeasible(
    content, direction, studio_om, base_plan
):
    """Construct a base plan whose page 4 claims far more blocks than any
    archetype can place on one page — a deliberate fixture, not a hope that
    some real content happens to overflow, per the module's own contract:
    refuse rather than let the change ripple past the scope."""
    inflated = base_plan.pages[4].model_copy(
        update={"slots": base_plan.pages[4].slots + base_plan.pages[1].slots + base_plan.pages[3].slots}
    )
    pages = list(base_plan.pages)
    pages[4] = inflated
    swollen_base = base_plan.model_copy(update={"pages": tuple(pages)})

    # sanity: the fixture really does claim more blocks than the real page did
    assert len(inflated.block_ids) > len(base_plan.pages[4].block_ids)

    with pytest.raises(ScopeInfeasibleError):
        compose_scoped(
            swollen_base, CompositionScope(type=ScopeType.PAGE, id="4"), content, direction, studio_om
        )

    # the real base_plan (frozen; never mutated by building the fixture or by
    # the failed attempt) still reproduces byte-for-byte from a fresh compose.
    assert compose(content, direction, studio_om).plan_hash == base_plan.plan_hash
