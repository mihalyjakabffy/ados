"""
The Creative Layer: content model → direction → page plan → document.

The test that matters is at the bottom: one content model, three directions,
three documents, and each one **byte-identical on a second run**. That is the
difference between a creative system and a random one, and it is the property
every other decision in ``brand/creative`` was made to protect.

Everything above it exists to make that claim mean something — that the three
documents genuinely differ, that they conform, and that the layer refuses the
two things it must refuse: a direction that restates the brand, and a metric
with no provenance.
"""

from __future__ import annotations

import json
import re

import pytest

from brand.content.model import (
    BlockRole,
    BlockType,
    ContentBlock,
    ContentModel,
    format_value,
)
from brand.creative.archetypes import ARCHETYPE_NAMES
from brand.creative.composer import compose, order_blocks, page_format
from brand.creative.direction import CreativeDirection, DirectionError
from brand.creative.directions import DIRECTIONS, get_direction
from brand.creative.evaluate import evaluate
from brand.creative.plan import RejectionKind
from brand.examples.malthouse import malthouse_content
from brand.templates.renderers import render_page_plan


@pytest.fixture(scope="module")
def content():
    return malthouse_content()


@pytest.fixture(scope="module")
def studio_om():
    from brand.examples.studio_om import studio_om as build

    return build()


@pytest.fixture(scope="module")
def om_tokens(studio_om):
    return studio_om.resolve_tokens()


@pytest.fixture(scope="module")
def plans(content, studio_om):
    return {d.id: compose(content, d, studio_om) for d in DIRECTIONS.values()}


# ---------------------------------------------------------------------------
# The content model
# ---------------------------------------------------------------------------


def test_a_metric_without_provenance_cannot_be_constructed():
    """The rule the whole model exists to enforce."""
    with pytest.raises(ValueError, match="provenance"):
        ContentBlock(
            id="met-01", type=BlockType.METRIC, role=BlockRole.EVIDENCE,
            priority=2, label="Embodied carbon", value=412.0,
            unit="kgCO2e/m2",
        )


def test_a_figure_without_an_aspect_cannot_be_placed():
    with pytest.raises(ValueError, match="aspect"):
        ContentBlock(
            id="img-01", type=BlockType.IMAGE, role=BlockRole.CONTEXT,
            priority=1, path="a.jpg",
        )


def test_extraction_is_deterministic(content):
    """Same state, same model — including the same block ids."""
    again = malthouse_content()
    assert again.content_hash == content.content_hash
    assert [b.id for b in again.blocks] == [b.id for b in content.blocks]


def test_the_facts_carry_where_they_came_from(content):
    metrics = content.of_type(BlockType.METRIC)
    assert metrics, "the design state has constraints; none reached the model"
    assert all(m.provenance for m in metrics)
    assert any("constraints.budget" in m.provenance for m in metrics)
    assert any("design_state 8f3a1c04" in m.provenance for m in metrics)


def test_the_prose_is_authored_and_says_so(content):
    prose = content.of_type(BlockType.NARRATIVE)
    assert prose
    assert all("authored" in b.provenance for b in prose)


def test_numbers_are_formatted_for_a_reader_not_a_machine():
    from brand.content.model import THIN_SPACE

    assert format_value(4_074_000.0) == THIN_SPACE.join(("4", "074", "000"))
    assert " " not in format_value(4_074_000.0), "an ordinary space would wrap"
    assert format_value(412.5) == "412.5"
    assert format_value(None) == ""


def test_a_content_model_holds_no_appearance():
    """The line the layer is built on: content knows nothing about pages."""
    forbidden = ("colour", "color", "font", "size", "margin", "column", "page")
    for name in ContentBlock.model_fields:
        assert not any(f in name for f in forbidden), name


# ---------------------------------------------------------------------------
# The direction
# ---------------------------------------------------------------------------


def test_a_direction_may_not_name_a_colour():
    base = DIRECTIONS["editorial-quiet"].model_dump()
    with pytest.raises(ValueError, match="may not name a colour"):
        CreativeDirection.model_validate({**base, "note": "set the rule in #8a2f2f"})


def test_a_direction_may_not_name_a_dimension_or_a_typeface():
    base = DIRECTIONS["editorial-quiet"].model_dump()
    with pytest.raises(ValueError, match="may not name a dimension"):
        CreativeDirection.model_validate({**base, "note": "20 mm margin"})
    with pytest.raises(ValueError, match="may not name a typeface"):
        CreativeDirection.model_validate({**base, "note": "set in Helvetica"})


def test_a_direction_may_not_use_the_banned_lexicon():
    """ADOS-7.2.020 applies to anything that reaches a normative position."""
    base = DIRECTIONS["editorial-quiet"].model_dump()
    with pytest.raises(ValueError, match="ADOS-7.2.020"):
        CreativeDirection.model_validate(
            {**base, "note": "clean and balanced"}
        )


def test_the_direction_errors_are_one_type():
    """So a caller can catch the layer's refusals without catching everything."""
    assert issubclass(DirectionError, ValueError)


def test_the_schema_cannot_grow_a_field_that_restates_the_brand():
    """The import-time guard, exercised rather than trusted."""
    from brand.creative.direction import FORBIDDEN_FIELD_STEMS

    for name in CreativeDirection.model_fields:
        assert not any(stem in name for stem in FORBIDDEN_FIELD_STEMS), name


def test_a_direction_cannot_target_a_density_ados_forbids():
    base = DIRECTIONS["editorial-quiet"].model_dump()
    with pytest.raises(ValueError, match="fill-ratio range"):
        CreativeDirection.model_validate({**base, "text_density": 0.95})


def test_a_direction_whose_hierarchy_does_not_read_is_refused():
    base = DIRECTIONS["editorial-quiet"].model_dump()
    with pytest.raises(ValueError, match="scale_jump_min"):
        CreativeDirection.model_validate(
            {**base, "display_step": "t3", "body_step": "t2"}
        )


def test_pacing_must_name_real_archetypes():
    base = DIRECTIONS["editorial-quiet"].model_dump()
    with pytest.raises(ValueError, match="do not exist"):
        CreativeDirection.model_validate({**base, "pacing": ["splash"]})


def test_the_three_directions_are_shipped_as_data():
    assert set(DIRECTIONS) == {"editorial-quiet", "technical-dense", "image-led"}
    for d in DIRECTIONS.values():
        assert set(d.pacing) <= set(ARCHETYPE_NAMES)
        assert get_direction(d.id) is d


# ---------------------------------------------------------------------------
# Ordering and composition
# ---------------------------------------------------------------------------


def test_ordering_is_total(content):
    """Without a total order two runs could swap two equal blocks."""
    direction = DIRECTIONS["editorial-quiet"]
    once = [b.id for b in order_blocks(content, direction)]
    shuffled = ContentModel(
        project_id=content.project_id,
        project_name=content.project_name,
        blocks=tuple(reversed(content.blocks)),
    )
    twice = [b.id for b in order_blocks(shuffled, direction)]
    assert once == twice


def test_the_direction_changes_the_reading_order(content):
    editorial = [b.role for b in order_blocks(content, DIRECTIONS["editorial-quiet"])]
    technical = [b.role for b in order_blocks(content, DIRECTIONS["technical-dense"])]
    assert editorial[0] is BlockRole.CONTEXT
    assert technical[0] is BlockRole.PROBLEM


def test_every_block_is_placed_exactly_once(content, plans):
    for plan in plans.values():
        placed = list(plan.placed_blocks)
        assert sorted(placed) == sorted(b.id for b in content.blocks), plan.direction
        assert len(placed) == len(set(placed))


def test_the_page_geometry_comes_from_ados_and_the_brand(studio_om):
    fmt = page_format(studio_om, "A4")
    assert (fmt.width_mm, fmt.height_mm) == (210.0, 297.0)   # ISO 216
    cfg = studio_om.visual_identity.grid.for_format("A4")
    assert fmt.columns == cfg.columns                        # the brand's
    assert fmt.span_width_mm(fmt.columns) == pytest.approx(fmt.content_width_mm)


def test_the_hard_constraints_hold_on_every_page(plans):
    from brand import ados

    _, high = ados.fill_ratio_bounds()
    lattice = ados.submodule_mm()
    for plan in plans.values():
        for page in plan.pages:
            assert page.fill_ratio <= high, f"{plan.direction} p{page.index} H13"
            assert page.ink_coverage_max <= ados.local_coverage_max() + 1e-9
            assert page.alignment_edges_x <= ados.alignment_edges_max_per_axis()
            for slot in page.slots:
                assert abs(slot.y_mm % lattice) < 1e-6, "H6"
                assert abs(slot.height_mm % lattice) < 1e-6, "H6"
                assert (
                    slot.x_mm + slot.width_mm
                    <= page.grid.content_width_mm + 1e-6
                ), "H7"
                if slot.text:
                    assert slot.cap_mm >= ados.absolute_cap_floor_mm(), "H15"


def test_the_rejected_list_shows_the_layout_was_chosen(plans):
    """An empty rejection list is an unauditable plan."""
    for plan in plans.values():
        assert plan.rejected, plan.direction
        kinds = {r.kind for r in plan.rejected}
        assert kinds & {RejectionKind.INFEASIBLE, RejectionKind.OUTRANKED}
        for rejection in plan.rejected:
            assert rejection.reason
            if rejection.kind is RejectionKind.INFEASIBLE:
                assert rejection.rule, "an infeasible candidate must name its rule"


def test_a_real_hard_constraint_rejection_is_recorded(plans):
    """Not a synthetic one — the cover genuinely overfills before it is trimmed."""
    reasons = [
        r for plan in plans.values() for r in plan.rejected
        if r.kind is RejectionKind.INFEASIBLE
    ]
    assert reasons, "no candidate was ever ruled out by a constraint"
    assert {r.rule for r in reasons} <= {"H1", "H6", "H7", "H12", "H13", "H14",
                                         "H15", "direction.emphasis_ceiling"}


def test_the_cover_is_the_first_page_and_only_the_first(plans):
    for plan in plans.values():
        assert plan.pages[0].archetype == "cover"
        assert "cover" not in [p.archetype for p in plan.pages[1:]]


def test_lead_with_decides_what_the_cover_opens_on(content, studio_om):
    """editorial-quiet leads on a photograph; technical-dense on a statement."""
    image_led = compose(content, DIRECTIONS["editorial-quiet"], studio_om)
    statement = compose(content, DIRECTIONS["technical-dense"], studio_om)
    assert any(s.component == "hero" for s in image_led.pages[0].slots)
    assert not any(s.component == "hero" for s in statement.pages[0].slots)
    assert any(s.component == "standfirst" for s in statement.pages[0].slots)


def test_the_section_label_names_the_role_of_its_page(plans):
    """A structural device that encodes something true, not an eyebrow."""
    roles = {r.value.upper() for r in BlockRole}
    for plan in plans.values():
        for page in plan.pages:
            for slot in page.slots:
                if slot.component == "section-label":
                    assert slot.text in roles, slot.text


def test_a_page_plan_carries_no_appearance_of_its_own(plans, om_tokens):
    """Every colour and face on the page comes from the brand, not the plan."""
    blob = json.dumps([p.to_dict() for p in plans.values()])
    assert not re.search(r"#[0-9a-fA-F]{6}\b", blob)
    family = om_tokens.value("font.family.primary")
    assert family not in blob


# ---------------------------------------------------------------------------
# The three directions genuinely differ
# ---------------------------------------------------------------------------


def test_the_same_content_makes_three_different_documents(plans):
    counts = {k: p.page_count for k, p in plans.items()}
    sequences = {k: p.archetype_sequence for k, p in plans.items()}
    fills = {k: tuple(pg.fill_ratio for pg in p.pages) for k, p in plans.items()}

    assert len(set(counts.values())) == 3, f"page counts collapsed: {counts}"
    assert len(set(sequences.values())) == 3, "archetype sequences collapsed"
    assert len(set(fills.values())) == 3, "fill ratios collapsed"


def test_the_image_led_direction_gives_more_of_the_page_to_pictures(plans):
    def mean_image_ratio(plan):
        return sum(p.image_ratio for p in plan.pages) / plan.page_count

    assert mean_image_ratio(plans["image-led"]) > mean_image_ratio(
        plans["technical-dense"]
    )


def test_all_three_conform_and_report_their_coverage(plans, om_tokens):
    for direction_id, plan in plans.items():
        ev = evaluate(plan, DIRECTIONS[direction_id], om_tokens)
        assert ev.ok, [f.message for f in ev.report.sorted() if not ev.ok]
        assert ev.checked
        assert "were not assessed" in ev.coverage
        assert "audience fit" in ev.coverage


def test_the_evaluation_reports_findings_and_not_a_score(om_tokens, plans):
    ev = evaluate(plans["technical-dense"], DIRECTIONS["technical-dense"], om_tokens)
    payload = ev.to_dict()
    assert "score" not in payload
    assert payload["coverage"]
    assert isinstance(payload["findings"], list)


# ---------------------------------------------------------------------------
# The binding assertion
# ---------------------------------------------------------------------------


def test_a_second_run_is_byte_identical(content, studio_om):
    """The claim the whole layer rests on.

    Compose and render from scratch — fresh content model, fresh brand, fresh
    token set — and the bytes must match. Anything that sampled, or iterated a
    dict whose order was not fixed, or stamped a timestamp, fails here.
    """
    for direction in DIRECTIONS.values():
        first = render_page_plan(
            compose(content, direction, studio_om), studio_om.resolve_tokens()
        )
        from brand.examples.studio_om import studio_om as rebuild

        brand2 = rebuild()
        second = render_page_plan(
            compose(malthouse_content(), direction, brand2), brand2.resolve_tokens()
        )
        assert str(first.content) == str(second.content), direction.id


def test_the_plan_hash_is_stable(content, studio_om, plans):
    for direction in DIRECTIONS.values():
        assert (
            compose(content, direction, studio_om).plan_hash
            == plans[direction.id].plan_hash
        )


def test_a_brand_change_reaches_the_composed_document(content, studio_om):
    """Change the brand, the document follows — the Brand System's premise,
    now holding for a document nobody wrote a template for."""
    before = str(
        render_page_plan(
            compose(content, DIRECTIONS["editorial-quiet"], studio_om),
            studio_om.resolve_tokens(),
        ).content
    )
    recoloured = studio_om.model_copy(
        update={
            "visual_identity": studio_om.visual_identity.model_copy(
                update={
                    "colour": studio_om.visual_identity.colour.model_copy(
                        update={"accent": "#3b5b8c"}
                    )
                }
            )
        }
    )
    after = str(
        render_page_plan(
            compose(content, DIRECTIONS["editorial-quiet"], recoloured),
            recoloured.resolve_tokens(),
        ).content
    )
    assert "#3b5b8c" in after and "#3b5b8c" not in before


# ---------------------------------------------------------------------------
# The rendered document
# ---------------------------------------------------------------------------


def test_the_rendered_document_declares_only_the_brands_colours(plans, om_tokens):
    declared = {
        str(t.value).lower()
        for t in om_tokens.values()
        if isinstance(t.value, str) and t.value.startswith("#")
    }
    for plan in plans.values():
        html = str(render_page_plan(plan, om_tokens).content)
        found = {m.lower() for m in re.findall(r"#[0-9a-fA-F]{6}\b", html)}
        assert not found - declared, f"{plan.direction}: {found - declared}"


def test_the_rendered_document_makes_no_external_requests(plans, om_tokens):
    html = str(render_page_plan(plans["image-led"], om_tokens).content)
    assert "http://" not in html and "https://" not in html
    assert "<script" not in html


def test_paged_media_rules_stay_in_paged_media(plans, om_tokens):
    """A page-break property on screen made Chromium paginate a screenshot and
    stamp a second running foot at the top of every page. Found by looking."""
    html = str(render_page_plan(plans["image-led"], om_tokens).content)
    before, _, inside = html.partition("@media print")
    assert "break-after: page;" in inside
    assert "break-after: page;" not in before


def test_the_composed_package_passes_the_consistency_audit(
    tmp_path, plans, studio_om, om_tokens
):
    """The audit that already guards the STUDIO OM package, over a package
    nobody hand-made: three documents composed from one content model."""
    from brand.export.exporters import AssetInventory
    from brand.validation.consistency import audit_package

    inventory = AssetInventory(studio_om, tmp_path)
    for direction_id, plan in plans.items():
        path = render_page_plan(plan, om_tokens).write(
            tmp_path / "documents" / f"malthouse-{direction_id}.html"
        )
        inventory.add(
            path, type="document", name=f"Malthouse — {direction_id}",
            direction=direction_id, pages=plan.page_count,
            plan_hash=plan.plan_hash,
        )
    inventory.write()

    audit = audit_package(tmp_path, studio_om, om_tokens)
    blocking = [f for f in audit.report.sorted() if f.severity.value in
                ("ERROR", "BLOCK")]
    assert not blocking, [f.message for f in blocking]
    assert audit.files_checked == 4
