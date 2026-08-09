"""
Document integration: token binding, undefined-token detection, and the
PTS bridge that drives the existing PDF builder.

The last group is the one that matters most. It is easy to build a brand model
that nothing consumes; these tests assert that a change to the brand reaches an
actual document produced by ``docs/templates/pdf/ptspdf.py`` — the same builder
that makes the verified PTS sheets.
"""

from __future__ import annotations

import re

import pytest

from brand.models.brand import Brand
from brand.models.tokens import UndefinedTokenError
from brand.templates.document_templates import (
    TEMPLATES,
    Family,
    Medium,
    coverage,
    get_template,
)


# ---------------------------------------------------------------------------
# The catalogue
# ---------------------------------------------------------------------------


def test_the_ten_document_categories_exist():
    titles = {t.title for t in TEMPLATES.values()}
    assert titles >= {
        "A4 Report", "A3 Technical Document", "Presentation", "Portfolio Page",
        "Project Cover", "Meeting Minutes", "Project Report", "Proposal",
        "Invoice", "Email Signature",
    }


def test_the_identity_catalogue_is_registered():
    """Two files, one registry — coverage() and the API must see both."""
    from brand.templates.identity_templates import IDENTITY_TEMPLATES

    assert set(IDENTITY_TEMPLATES) <= set(TEMPLATES)
    assert {t.title for t in IDENTITY_TEMPLATES.values()} >= {
        "Business Card", "Letterhead", "Presentation Deck", "Portfolio Spread",
        "Competition Board", "Social Post", "Website Homepage",
    }


def test_template_ids_are_unique_and_prefixed():
    for tid in TEMPLATES:
        assert re.fullmatch(r"B[TI]\d{2}-[a-z0-9-]+", tid), tid


def test_every_template_declares_a_family_and_a_purpose():
    for t in TEMPLATES.values():
        assert isinstance(t.family, Family)
        assert len(t.purpose) > 20, f"{t.template_id} has no stated purpose"


def test_unknown_template_id_lists_the_known_ones():
    with pytest.raises(KeyError, match="BT01-a4-report"):
        get_template("nope")


# ---------------------------------------------------------------------------
# Token binding
# ---------------------------------------------------------------------------


def test_html_render_contains_no_hard_coded_identity(studio_nord, tokens):
    """The test that keeps the token layer honest.

    Every colour in the output must be one the brand declares. A literal that
    crept into a template would show up here as a hex the brand has never
    heard of.
    """
    doc = get_template("BT01-a4-report").render(tokens, title="T", project="P")
    html = str(doc.content)

    declared = {
        str(t.value).lower()
        for t in tokens.values()
        if isinstance(t.value, str) and t.value.startswith("#")
    }
    found = {m.lower() for m in re.findall(r"#[0-9a-fA-F]{6}\b", html)}
    stray = found - declared
    assert not stray, f"template contains colours the brand does not define: {stray}"


def test_render_reports_the_tokens_it_used(tokens):
    doc = get_template("BT01-a4-report").render(tokens)
    assert len(doc.tokens_used) > 20
    assert "color.text.primary" in doc.tokens_used
    assert all(name in tokens for name in doc.tokens_used)


def test_render_carries_the_brand_version(studio_nord, tokens):
    doc = get_template("BT01-a4-report").render(tokens)
    assert doc.brand_version == studio_nord.version
    assert studio_nord.version in str(doc.content)


def test_undefined_token_is_caught_before_rendering(minimal_brand):
    """A template needing a token the brand lacks must fail by name."""
    tokens = minimal_brand.resolve_tokens()
    invoice = get_template("BT09-invoice")
    assert invoice.check_bindings(tokens) == ["font.family.mono"]
    with pytest.raises(UndefinedTokenError, match="font.family.mono"):
        invoice.render(tokens)


def test_coverage_reports_before_anything_is_attempted(tokens):
    cov = coverage(tokens)
    assert set(cov) == set(TEMPLATES)
    assert all(missing == [] for missing in cov.values())


def test_every_html_template_renders(tokens):
    for tid, template in TEMPLATES.items():
        if template.medium is Medium.PDF:
            continue
        doc = template.render(tokens)
        assert doc.content and len(str(doc.content)) > 500, tid
        assert doc.media_type.startswith("text/html")


def test_apply_to_is_the_documented_entry_point(studio_nord):
    doc = studio_nord.apply_to(get_template("BT10-email-signature"))
    assert "STUDIO NORD" in str(doc.content)


def test_a_brand_change_changes_the_document(studio_nord):
    """The whole premise: change the brand, the documents follow."""
    before = str(studio_nord.apply_to(get_template("BT01-a4-report")).content)
    recoloured = studio_nord.model_copy(
        update={
            "visual_identity": studio_nord.visual_identity.model_copy(
                update={
                    "colour": studio_nord.visual_identity.colour.model_copy(
                        update={"accent": "#3b5b8c"}
                    )
                }
            )
        }
    )
    after = str(recoloured.apply_to(get_template("BT01-a4-report")).content)
    assert "#3b5b8c" in after
    assert "#3b5b8c" not in before


# ---------------------------------------------------------------------------
# The PTS bridge
# ---------------------------------------------------------------------------


def test_overlay_only_touches_whitelisted_paths(studio_nord):
    from brand.resolution.pts_bridge import ALLOWED_OVERLAY_PATHS, build_overlay

    overlay = build_overlay(studio_nord)
    assert set(overlay.paths()) <= ALLOWED_OVERLAY_PATHS
    assert overlay.paths(), "an overlay that sets nothing is not a bridge"


def test_overlay_never_moves_derived_geometry(studio_nord):
    """Sheet geometry carries ADOS rule numbers and is not a brand's to choose."""
    from brand.resolution.pts_bridge import merged_pts_tokens
    from brand import ados

    merged = merged_pts_tokens(studio_nord)
    base = ados.pts_tokens()
    assert merged["sheet"] == base["sheet"]
    assert merged["type"]["steps"] == base["type"]["steps"]
    assert merged["ink"] == base["ink"]


def test_brand_line_weights_reach_the_pts_tiers(studio_nord):
    from brand.resolution.pts_bridge import merged_pts_tokens

    heavier = studio_nord.model_copy(
        update={
            "architectural_language": studio_nord.architectural_language.model_copy(
                update={
                    "drawing": studio_nord.architectural_language.drawing.model_copy(
                        update={
                            "lineweights": studio_nord.architectural_language
                            .drawing.lineweights.model_copy(
                                update={"cut_mm": 1.0}
                            )
                        }
                    )
                }
            )
        }
    )
    assert merged_pts_tokens(heavier)["line"]["tiers"]["W3"] == 1.0
    assert merged_pts_tokens(studio_nord)["line"]["tiers"]["W3"] == 0.70


def test_off_series_weight_is_snapped_and_reported(studio_nord):
    from brand.models.architectural_language import Lineweights
    from brand.resolution.pts_bridge import build_overlay

    odd = studio_nord.model_copy(
        update={
            "architectural_language": studio_nord.architectural_language.model_copy(
                update={
                    "drawing": studio_nord.architectural_language.drawing.model_copy(
                        update={
                            "lineweights": Lineweights(
                                cut_mm=0.62, primary_mm=0.35,
                                secondary_mm=0.25, background_mm=0.18,
                            )
                        }
                    )
                }
            )
        }
    )
    overlay = build_overlay(odd)
    assert overlay.tokens["line"]["tiers"]["W3"] == 0.7
    assert any("snapped" in w for w in overlay.warnings)


def test_a_missing_font_file_warns_rather_than_substituting_silently(studio_nord):
    from brand.resolution.pts_bridge import build_overlay

    overlay = build_overlay(studio_nord)
    assert any("Source Serif 4" in w for w in overlay.warnings)


def test_the_overlay_is_scoped_to_the_build():
    """A leaked overlay would brand the next, unrelated build."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs" / "templates" / "pdf"))
    import ptspdf as P

    original = P.TIER["W3"]
    with P.token_overlay({"line": {"tiers": {"W3": 1.4}}}):
        assert P.TIER["W3"] == 1.4
    assert P.TIER["W3"] == original


# ---------------------------------------------------------------------------
# The end-to-end demonstration
# ---------------------------------------------------------------------------


def test_brief_to_branded_pdf():
    """brief → proposal → validation → approval → tokens → template → document.

    The single test that proves the Brand System is connected to ADOS rather
    than sitting beside it: the bytes at the end are produced by the same
    builder that makes the verified PTS sheets.
    """
    from brand.agents.brand_agent import BrandAgent
    from brand.templates.document_templates import PROJECT_COVER
    from brand.templates.renderers import render_sheet_pdf

    proposal = BrandAgent().generate_proposal(
        "A small practice doing precise, quiet, material adaptive reuse.",
        name="Studio Nord",
    )
    assert proposal.validation.ok
    published = proposal.approve(approved_by="MJ").published()

    tokens = published.resolve_tokens()
    doc = render_sheet_pdf(
        PROJECT_COVER, tokens, brand=published,
        project="Malthouse", client="Ash Trust",
    )

    assert doc.medium is Medium.PDF
    assert doc.content.startswith(b"%PDF")
    assert len(doc.content) > 20_000
    assert doc.brand_version == published.version
    # A1 landscape: 841 × 594 mm in points, to the ADOS page tolerance.
    assert re.search(rb"/MediaBox \[ 0 0 2383\.\d+ 1683\.\d+ \]", doc.content)


def test_the_branded_pdf_carries_the_practice_and_the_brand_version(studio_nord):
    from brand.templates.document_templates import PROJECT_COVER
    from brand.templates.renderers import render_sheet_pdf

    doc = render_sheet_pdf(PROJECT_COVER, studio_nord.resolve_tokens(),
                           brand=studio_nord)
    # The content stream is uncompressed (ptspdf sets setPageCompression(0)),
    # so the strings are inspectable without a PDF library.
    text = doc.content.decode("latin-1")
    assert "STUDIO NORD" in text
    assert "Studio Nord brand 1.0.0" in text


def test_pdf_render_refuses_tokens_without_the_brand(tokens):
    from brand.templates.document_templates import PROJECT_COVER
    from brand.templates.renderers import render_sheet_pdf

    with pytest.raises(ValueError, match="needs the Brand"):
        render_sheet_pdf(PROJECT_COVER, tokens)


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


def test_preview_renders_and_shows_the_findings(studio_nord):
    from brand.preview.brand_preview import render_preview

    html = render_preview(studio_nord)
    assert "<!doctype html>" in html
    assert "STUDIO NORD" in html
    assert "Validation" in html
    for section in ("Typography", "Colour", "Grid", "Drawing language",
                    "Communication"):
        assert section in html, f"preview is missing the {section} section"


def test_preview_makes_no_external_requests(studio_nord):
    """A brand preview that depends on a CDN is not previewing the brand."""
    from brand.preview.brand_preview import render_preview

    html = render_preview(studio_nord)
    assert "http://" not in html
    assert "https://" not in html
    assert "<script" not in html


# ---------------------------------------------------------------------------
# Phase 5 consumer interfaces
# ---------------------------------------------------------------------------


def test_consumers_need_only_the_token_set(tokens):
    """The discipline: a consumer never sees a Brand.

    If an adapter needed the brand object, the next change to the brand model
    would break it. Passing only tokens is what makes the model free to move.
    """
    from brand.consumers import CONSUMERS, BrandConsumer

    for name, consumer in CONSUMERS.items():
        assert isinstance(consumer, BrandConsumer)
        artefact = consumer.consume(tokens)
        assert artefact["provenance"]["brand_version"] == tokens.brand_version, name


def test_archicad_pens_carry_the_brand_weights(studio_nord, tokens):
    from brand.consumers import ArchicadAttributeMap

    pens = {p["name"]: p["width_mm"] for p in
            ArchicadAttributeMap().consume(tokens)["pens"]}
    lw = studio_nord.architectural_language.drawing.lineweights
    assert pens["ADOS cut"] == lw.cut_mm
    assert pens["ADOS beyond"] == lw.background_mm


def test_render_parameters_match_the_repository_visual_state_shape(tokens):
    """The adapter speaks VisualState's vocabulary, not a parallel one."""
    from brand.consumers import RenderParameters

    params = RenderParameters().consume(tokens)
    assert set(params["camera"]) >= {"focal_length_mm", "sensor_width_mm"}
    assert params["lighting"]["scenario"]
