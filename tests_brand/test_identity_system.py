"""
The identity layer: logo generation, exports, guidelines, the STUDIO OM
package and the consistency audit.

The theme running through these is the same one as the rest of the suite: an
artefact must be *derived*, and the test is that changing the brand changes the
artefact. A generator that produced a handsome mark from constants inside
itself would pass a visual review and fail every test here.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from brand.assets.logo import LogoSystem, Variant, text_outline
from brand.examples.studio_om import STUDIO_OM, studio_om
from brand.models.brand import Brand


@pytest.fixture(scope="module")
def om() -> Brand:
    return studio_om()


@pytest.fixture(scope="module")
def om_tokens(om):
    return om.resolve_tokens()


# ---------------------------------------------------------------------------
# STUDIO OM as a brand
# ---------------------------------------------------------------------------


def test_studio_om_validates(om):
    report = om.check()
    assert report.ok, report.summary()
    assert not report.blocking


def test_the_heavier_cut_is_legal_and_reaches_the_sheet(om):
    """The one deliberate deviation from the ADOS default tiers."""
    from brand.resolution.pts_bridge import merged_pts_tokens

    assert om.architectural_language.drawing.lineweights.cut_mm == 1.00
    assert om.check().ok, "1.00 mm is on the ISO series and must validate"
    assert merged_pts_tokens(om)["line"]["tiers"]["W3"] == 1.00


def test_the_accent_lands_on_a_tone_ladder_rung(om):
    """So it reproduces as a defined tone on a monochrome plot."""
    from brand import ados
    from brand.colour import nearest_tone_token

    token, distance = nearest_tone_token(
        om.visual_identity.colour.accent, ados.tone_ladder()
    )
    assert token == "T3"
    assert distance < 1.0, f"accent is ΔL* {distance:.1f} off the ladder"


def test_the_neutral_ramp_is_snapped_to_the_ladder(om):
    from brand import ados
    from brand.colour import nearest_tone_token

    ladder = ados.tone_ladder()
    for value in om.visual_identity.colour.neutral:
        _, distance = nearest_tone_token(value, ladder)
        assert distance < 1.0, f"{value} is ΔL* {distance:.1f} off the ladder"


def test_personality_is_capped_at_four(om):
    """Eight characteristics in the brief, four axes in the brand.

    The rest are carried as keywords. Downstream generators weight every axis
    equally, so a personality of eight is a personality of none.
    """
    assert len(om.identity.personality) == 4
    for extra in ("contextual", "experimental", "minimal", "human"):
        assert extra in om.identity.keywords


def test_per_format_grids_resolve(om_tokens):
    for fmt in ("A4", "A3", "slide", "portfolio", "board"):
        assert f"grid.{fmt}.columns" in om_tokens
        assert f"grid.{fmt}.gutter" in om_tokens


def test_the_new_namespaces_are_populated(om_tokens):
    for prefix in ("graphic", "photo", "web", "social"):
        assert om_tokens.namespace(prefix), f"{prefix}.* is empty"


# ---------------------------------------------------------------------------
# The logo system
# ---------------------------------------------------------------------------


def test_every_variant_builds(om):
    logos = {logo.variant: logo for logo in LogoSystem(om).build_all()}
    # HORIZONTAL is an alias of PRIMARY and collapses to one file by design.
    assert set(logos) >= {
        Variant.PRIMARY, Variant.SECONDARY, Variant.MONOGRAM, Variant.SYMBOL,
        Variant.COMPACT, Variant.STACKED, Variant.REVERSED,
    }


def test_the_wordmark_is_real_outlines_not_live_text(om):
    """The mark must be the typeface, not a request for it."""
    svg = LogoSystem(om).build(Variant.PRIMARY).svg
    assert "<path" in svg
    assert "<text" not in svg, "a wordmark set as live text is not self-contained"
    assert LogoSystem(om).build(Variant.PRIMARY).outlined


def test_the_mark_is_built_from_the_brand_not_from_constants(om):
    """Change the module, and the mark rebuilds at the new size."""
    before = LogoSystem(om).build(Variant.SYMBOL)
    bigger = om.model_copy(
        update={
            "visual_identity": om.visual_identity.model_copy(
                update={
                    "logo": om.visual_identity.logo.model_copy(
                        update={
                            "construction": om.visual_identity.logo.construction
                            .model_copy(update={"module_mm": 10.0})
                        }
                    )
                }
            )
        }
    )
    after = LogoSystem(bigger).build(Variant.SYMBOL)
    assert after.width_mm == before.width_mm * 2


def test_the_wordmark_follows_the_typeface(om):
    """A different face gives different path data, not scaled path data."""
    inter = LogoSystem(om).build(Variant.SECONDARY).svg
    other = om.model_copy(
        update={
            "visual_identity": om.visual_identity.model_copy(
                update={
                    "typography": om.visual_identity.typography.model_copy(
                        update={
                            "primary_font": om.visual_identity.typography
                            .mono_font
                        }
                    )
                }
            )
        }
    )
    plex = LogoSystem(other).build(Variant.SECONDARY).svg
    assert inter != plex


def test_an_unbundled_face_falls_back_and_says_so(om):
    """Silence would ship a mark that is simply the wrong typeface."""
    from brand.models.visual_identity import FontFace

    unknown = om.model_copy(
        update={
            "visual_identity": om.visual_identity.model_copy(
                update={
                    "typography": om.visual_identity.typography.model_copy(
                        update={"primary_font": FontFace(family="Söhne")}
                    )
                }
            )
        }
    )
    logo = LogoSystem(unknown).build(Variant.SECONDARY)
    assert not logo.outlined
    assert any("not bundled" in n for n in logo.notes)


def test_the_compact_monogram_fits_inside_the_aperture(om):
    """The defect the first build had: "OM" touching the aperture walls."""
    system = LogoSystem(om)
    inner = system.field - 2 * system.wall
    probe = text_outline(
        system.monogram, family=system.family, weight=system.weight,
        cap_mm=inner * 0.5, tracking_percent=0.0,
    )
    logo = system.build(Variant.COMPACT)
    # Recover the drawn cap from the SVG scale factor and check the advance.
    scale = float(re.search(r'scale\(([\d.]+) ', logo.svg).group(1))
    drawn_cap = scale * 2048 * 0.727           # units → mm, Inter cap ratio
    drawn_advance = probe.advance_mm * drawn_cap / (inner * 0.5)
    assert drawn_advance <= inner - system.wall, (
        "the monogram must clear the aperture wall on both sides"
    )


def test_reversed_is_constructed_not_string_replaced(om):
    """A replacement that stops matching ships a mark that is not reversed."""
    system = LogoSystem(om)
    reversed_logo = system.build(Variant.REVERSED)
    ink = str(system.tokens.value("color.text.primary"))
    paper = str(system.tokens.value("color.background"))
    assert reversed_logo.background == "dark"
    assert f'fill="{ink}"' in reversed_logo.svg          # the ground
    assert f'fill="{paper}"' in reversed_logo.svg        # the mark
    # and it is bigger than the primary, because the ground carries clear space
    assert reversed_logo.width_mm > system.build(Variant.PRIMARY).width_mm


def test_logo_metadata_is_complete(om):
    for logo in LogoSystem(om).build_all():
        meta = logo.metadata(om.identity.name)
        for key in ("name", "type", "variant", "background", "format",
                    "brand", "brand_version"):
            assert meta.get(key) not in (None, ""), f"{logo.slug}: {key}"


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


def test_css_variables_carry_units(om_tokens):
    from brand.export import to_css_variables

    css = to_css_variables(om_tokens)
    assert "--color-text-primary: #1a1a18;" in css
    assert re.search(r"--space-1: [\d.]+mm;", css), "a length needs its unit"
    assert re.search(r"--font-size-sm-pt: [\d.]+pt;", css)


def test_yaml_round_trips(om):
    from brand.export import to_yaml

    text = to_yaml(om)
    assert om.identity.name in text
    yaml = pytest.importorskip("yaml")
    again = Brand.model_validate(
        yaml.safe_load(text.split("\n", 2)[2] if text.startswith("#") else text)
    )
    assert again.is_equivalent_to(om)


def test_colour_table_reports_every_representation(om_tokens):
    from brand.export import to_colour_table

    rows = {r["token"]: r for r in to_colour_table(om_tokens)}
    row = rows["color.brand.accent"]
    assert row["hex"] == "#64726b"
    assert re.fullmatch(r"\d+ \d+ \d+", row["rgb"])
    assert re.fullmatch(r"\d+ \d+ \d+ \d+", row["cmyk_uncalibrated"])
    assert row["mono"].startswith("#")


def test_every_colour_has_a_monochrome_equivalent(om_tokens):
    """A consumer that plots must never derive the grey itself."""
    colours = {
        k for k, t in om_tokens.namespace("color").items()
        if isinstance(t.value, str) and t.value.startswith("#")
        and not k.endswith(".mono")
    }
    missing = sorted(k for k in colours if f"{k}.mono" not in om_tokens)
    assert missing == []


# ---------------------------------------------------------------------------
# Guidelines
# ---------------------------------------------------------------------------


def test_guidelines_have_all_eighteen_sections(om):
    from brand.guidelines import SECTIONS, render_guidelines

    html = render_guidelines(om)
    for number, title in SECTIONS:
        assert f">{title}</h1>" in html, f"section {number} {title} is missing"
    assert len(SECTIONS) == 18


def test_guidelines_are_generated_not_authored(om):
    """Change a brand value and the document says the new thing."""
    from brand.guidelines import render_guidelines

    before = render_guidelines(om)
    assert "1.0 mm" in before or "1.0mm" in before or "1.0" in before

    changed = om.model_copy(
        update={
            "identity": om.identity.model_copy(
                update={"tagline": "Cut once"}
            )
        }
    )
    after = render_guidelines(changed)
    assert "Cut once" in after
    assert "Cut once" not in before


def test_guidelines_are_self_contained(om):
    """No network at render time.

    ``xmlns="http://www.w3.org/2000/svg"`` is a namespace *name*, not a
    fetch, so the test looks for things that actually load: a src, an href, an
    @import, or a url() pointing off the machine.
    """
    from brand.guidelines import render_guidelines

    html = render_guidelines(om)
    assert not re.search(r'(?:src|href)\s*=\s*["\']https?://', html)
    assert "@import" not in html
    assert not re.search(r"url\(\s*[\"\']?https?://", html)
    assert "<script" not in html


# ---------------------------------------------------------------------------
# The package and its audit
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def package(tmp_path_factory, om):
    from brand.examples.build_studio_om import build

    out = tmp_path_factory.mktemp("studio-om")
    return build(out, om), out


def test_the_package_builds(package):
    result, out = package
    assert result["assets"] >= 30
    assert (out / "asset-inventory.json").exists()
    assert (out / "brand/tokens.json").exists()
    assert (out / "brand-guidelines").is_dir()
    assert len(list((out / "logo").glob("*.svg"))) >= 7
    assert len(list((out / "documents").glob("*"))) == 18


def test_the_package_audits_clean(package):
    result, _ = package
    audit = result["audit"]
    assert audit.ok, audit.report.summary()
    assert not [f for f in audit.report.findings if f.severity.value == "ERROR"]


def test_every_file_is_in_the_inventory(package):
    """Every *asset* — the manifest does not list itself or its own audit."""
    from brand.validation.consistency import _SELF_REFERENTIAL

    _, out = package
    payload = json.loads((out / "asset-inventory.json").read_text())
    recorded = {a["path"] for a in payload["assets"]}
    on_disk = {
        str(p.relative_to(out)).replace("\\", "/")
        for p in out.rglob("*")
        if p.is_file() and p.name not in _SELF_REFERENTIAL
    }
    assert not (on_disk - recorded), sorted(on_disk - recorded)


def test_inventory_records_carry_the_brand_version(package, om):
    _, out = package
    payload = json.loads((out / "asset-inventory.json").read_text())
    assert payload["brand_version"] == om.version
    assert payload["content_hash"] == om.content_hash
    assert all(a["brand_version"] == om.version for a in payload["assets"])


def test_the_agent_proposal_is_recorded_but_not_adopted(package, om):
    """AI proposes, the user approves — visible in the package itself."""
    _, out = package
    payload = json.loads((out / "brand/agent-proposal.json").read_text())
    assert payload["proposed_brand"]["status"] == "proposed"
    assert payload["difference_from_approved"]["cut_mm"]["approved"] == 1.0
    assert json.loads((out / "brand/studio-om.json").read_text())["status"] == "published"


# ---------------------------------------------------------------------------
# The consistency checker itself
# ---------------------------------------------------------------------------


def test_the_checker_catches_a_planted_colour(tmp_path, om, om_tokens):
    from brand.validation.consistency import audit_package

    (tmp_path / "documents").mkdir()
    (tmp_path / "documents/rogue.html").write_text(
        "<style>body{color:#ff00ff}</style><p>hello</p>"
    )
    audit = audit_package(tmp_path, om, om_tokens)
    assert any("#ff00ff" in f.message for f in audit.report.findings)
    assert not audit.ok


def test_the_checker_catches_a_planted_font(tmp_path, om, om_tokens):
    from brand.validation.consistency import audit_package

    (tmp_path / "a.html").write_text("<style>p{font-family: Comic Sans MS}</style>")
    audit = audit_package(tmp_path, om, om_tokens)
    assert any("comic sans ms" in f.message for f in audit.report.findings)


def test_the_checker_catches_a_dangling_custom_property(tmp_path, om, om_tokens):
    from brand.validation.consistency import audit_package

    (tmp_path / "a.css").write_text("p { margin: var(--nope); }")
    audit = audit_package(tmp_path, om, om_tokens)
    assert any("--nope" in f.message for f in audit.report.findings)


def test_the_checker_does_not_flag_data_files(tmp_path, om, om_tokens):
    """A hex in a JSON file is data. Flagging it trains people to ignore the check."""
    from brand.validation.consistency import audit_package

    (tmp_path / "data.json").write_text(json.dumps({"other_brand": "#ff00ff"}))
    audit = audit_package(tmp_path, om, om_tokens)
    assert not any("#ff00ff" in f.message for f in audit.report.findings)


def test_the_checker_distinguishes_padding_from_placement(tmp_path, om, om_tokens):
    """Placement is on the sub-module; internal clearance on the half."""
    from brand.validation.consistency import audit_package

    (tmp_path / "a.css").write_text("a{padding:2.5mm}b{gap:2.5mm}")
    findings = audit_package(tmp_path, om, om_tokens).report.findings
    lattice = [f for f in findings if "lattice" in f.message]
    assert lattice, "a 2.5 mm gap is off the placement lattice"
    assert "gap: 2.5mm" in lattice[0].message
    assert "padding" not in lattice[0].message


def test_the_checker_notices_a_missing_logo_variant(tmp_path, om, om_tokens):
    from brand.validation.consistency import audit_package

    (tmp_path / "logo").mkdir()
    (tmp_path / "logo/studio-om-primary.svg").write_text("<svg/>")
    audit = audit_package(tmp_path, om, om_tokens)
    assert any("declared variants with no file" in f.message
               for f in audit.report.findings)


# ---------------------------------------------------------------------------
# The Word family — the same overlay, a different builder
# ---------------------------------------------------------------------------


def test_all_eight_word_templates_are_registered():
    from brand.templates.document_templates import TEMPLATES, Medium

    word = {t for t in TEMPLATES.values() if t.medium is Medium.DOCX}
    assert len(word) == 8
    assert {t.template_id for t in word} == {
        "BW01-specification", "BW02-door-schedule", "BW03-window-schedule",
        "BW04-meeting-minutes", "BW05-site-visit-report",
        "BW06-request-for-information", "BW07-revision-log", "BW08-transmittal",
    }


def test_a_branded_dotx_is_a_valid_word_template(om, om_tokens):
    import zipfile
    from brand.templates.document_templates import get_template
    from brand.templates.renderers import render_word_dotx

    doc = render_word_dotx(
        get_template("BW01-specification"), om_tokens, brand=om
    )
    assert doc.medium.value == "dotx"
    zf = zipfile.ZipFile(__import__("io").BytesIO(doc.content))
    content_types = zf.read("[Content_Types].xml").decode()
    assert "template.main+xml" in content_types, "a .dotx, not a .docx"
    assert "docProps/custom.xml" in zf.namelist()


def test_the_brand_reaches_the_word_typeface_and_its_substitute(om):
    """Both halves: the face Word asks for, and what it falls back to.

    Word has no fallback chain, so ``w:altName`` is the only mechanism there
    is — and a hard-coded Arial would contradict whatever the brand declared.
    """
    import io
    import zipfile

    from brand.models.visual_identity import FontFace
    from brand.templates.document_templates import get_template
    from brand.templates.renderers import render_word_dotx

    def font_table(brand):
        doc = render_word_dotx(
            get_template("BW01-specification"), brand.resolve_tokens(),
            brand=brand,
        )
        return zipfile.ZipFile(io.BytesIO(doc.content)).read(
            "word/fontTable.xml"
        ).decode()

    assert 'w:altName w:val="Arial"' in font_table(om)

    changed = om.model_copy(
        update={
            "visual_identity": om.visual_identity.model_copy(
                update={
                    "typography": om.visual_identity.typography.model_copy(
                        update={
                            "primary_font": FontFace(
                                family="Söhne", fallback="Helvetica"
                            )
                        }
                    )
                }
            )
        }
    )
    table = font_table(changed)
    assert "Söhne" in table
    assert 'w:altName w:val="Helvetica"' in table


def test_the_practice_reaches_the_document_properties(om, om_tokens):
    """Identity arrives as a field default, and stays a field."""
    import io
    import zipfile

    from brand.templates.document_templates import get_template
    from brand.templates.renderers import render_word_dotx

    doc = render_word_dotx(
        get_template("BW08-transmittal"), om_tokens, brand=om
    )
    zf = zipfile.ZipFile(io.BytesIO(doc.content))
    props = zf.read("docProps/custom.xml").decode()
    assert om.identity.name in props
    assert f"brand {om.version}" in props
    # Project-level facts are NOT baked in: they belong to a document.
    assert "PROJECT NAME" in props, "a stale project name is worse than a blank"


def test_the_word_overlay_does_not_leak(om, om_tokens):
    """A leaked overlay would brand the next, unrelated build."""
    import sys
    from pathlib import Path

    sys.path.insert(
        0, str(Path(__file__).resolve().parents[1] / "docs/templates/word")
    )
    import ptsword

    from brand.templates.document_templates import get_template
    from brand.templates.renderers import render_word_dotx

    before = (ptsword.FONT, ptsword.FONT_ALT, dict(ptsword.DOC_PROPERTIES))
    render_word_dotx(get_template("BW01-specification"), om_tokens, brand=om)
    assert (ptsword.FONT, ptsword.FONT_ALT, dict(ptsword.DOC_PROPERTIES)) == before


def test_branded_word_templates_pass_the_pts_verifier(tmp_path, om, om_tokens):
    """The 174 structural checks, run against the *branded* output.

    The verifier inspects the produced packages rather than the code, so this
    is the real assurance that branding a template did not break it.
    """
    import subprocess
    import sys
    from pathlib import Path

    from brand.templates.document_templates import TEMPLATES, Medium
    from brand.templates.renderers import render_word_dotx

    #: The verifier keys its per-template geometry off the filename.
    names = {
        "BW01-specification": "PTS-T05-Specification",
        "BW02-door-schedule": "PTS-T06a-Door-Schedule",
        "BW03-window-schedule": "PTS-T06b-Window-Schedule",
        "BW04-meeting-minutes": "PTS-T07-Meeting-Minutes",
        "BW05-site-visit-report": "PTS-T08-Site-Visit-Report",
        "BW06-request-for-information": "PTS-T09-Request-for-Information",
        "BW07-revision-log": "PTS-T10-Revision-Log",
        "BW08-transmittal": "PTS-T11-Transmittal",
    }
    for tid, template in TEMPLATES.items():
        if template.medium is not Medium.DOCX:
            continue
        doc = render_word_dotx(template, om_tokens, brand=om)
        (tmp_path / f"{names[tid]}.dotx").write_bytes(doc.content)

    verifier = Path(__file__).resolve().parents[1] / "docs/templates/word/verify.py"
    result = subprocess.run(
        [sys.executable, str(verifier), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout[-2000:]
    assert "All 174 checks passed" in result.stdout


def test_the_package_contains_the_word_templates(package):
    _, out = package
    assert len(list((out / "word").glob("*.dotx"))) == 8


# ---------------------------------------------------------------------------
# Font embedding — the difference between requesting a typeface and setting one
# ---------------------------------------------------------------------------


def _dotx(brand, template_id="BW01-specification"):
    import io
    import zipfile

    from brand.templates.document_templates import get_template
    from brand.templates.renderers import render_word_dotx

    doc = render_word_dotx(
        get_template(template_id), brand.resolve_tokens(), brand=brand
    )
    return zipfile.ZipFile(io.BytesIO(doc.content))


def test_the_obfuscation_round_trips_to_the_source_font():
    """ECMA-376 §17.8.1, checked without a copy of Word.

    The scheme is an XOR, so it is its own inverse: de-obfuscating must return
    the original bytes, magic number and all. That does not prove Word accepts
    it, but it proves the transform is self-consistent and that the file is a
    whole TrueType font rather than a truncated one.
    """
    import sys
    from pathlib import Path

    sys.path.insert(
        0, str(Path(__file__).resolve().parents[1] / "docs/templates/word")
    )
    import ptsword

    source = (
        Path(__file__).resolve().parents[1]
        / "docs/templates/pdf/fonts/Inter-Regular.ttf"
    ).read_bytes()
    key = "{1D9D4F1A-7C5B-4E2A-9A31-6B0E5C7A2D40}"
    obfuscated = ptsword.obfuscate_font(source, key)
    assert obfuscated[:4] != source[:4], "the first bytes must be scrambled"
    assert ptsword.obfuscate_font(obfuscated, key) == source
    assert source[:4] == b"\x00\x01\x00\x00"


def test_a_branded_dotx_embeds_its_fonts(om):
    """Without this the file is a *request* for Inter, not a document set in it.

    On a machine that does not have the face — a phone previewing an
    attachment — the reader substitutes, and ``w:altName`` is advisory: some
    readers honour it and give a sans, some ignore it and give a serif. Either
    way every measurement shifts.
    """
    zf = _dotx(om)
    fonts = [n for n in zf.namelist() if n.startswith("word/fonts/")]
    assert len(fonts) == 2, "the text face and the mono face"
    assert "word/_rels/fontTable.xml.rels" in zf.namelist()
    assert 'Extension="odttf"' in zf.read("[Content_Types].xml").decode()

    table = zf.read("word/fontTable.xml").decode()
    assert table.count("w:embedRegular") == 2
    assert "xmlns:r=" in table, "r:id needs the relationship namespace declared"
    assert "embedTrueTypeFonts" in zf.read("word/settings.xml").decode()


def test_the_embedded_font_is_the_declared_face(om):
    """Not just *a* font — the one the brand names."""
    import re
    import sys
    from pathlib import Path

    sys.path.insert(
        0, str(Path(__file__).resolve().parents[1] / "docs/templates/word")
    )
    import ptsword

    zf = _dotx(om)
    table = zf.read("word/fontTable.xml").decode()
    key = re.search(r'w:fontKey="(\{[^"]+\})"', table).group(1)
    recovered = ptsword.obfuscate_font(zf.read("word/fonts/font1.odttf"), key)
    expected = (
        Path(__file__).resolve().parents[1]
        / "docs/templates/pdf/fonts/Inter-Regular.ttf"
    ).read_bytes()
    assert recovered == expected


def test_an_unbranded_build_embeds_nothing(tmp_path):
    """The PTS pack ships as a template a practice installs fonts for.

    Embedding is what a *brand* adds, and the unbranded default must stay the
    file the 174 checks were written against.
    """
    import sys
    import zipfile
    from pathlib import Path

    word_dir = Path(__file__).resolve().parents[1] / "docs/templates/word"
    sys.path.insert(0, str(word_dir))
    import build as word_build

    word_build.t05_specification(tmp_path)
    zf = zipfile.ZipFile(tmp_path / "PTS-T05-Specification.dotx")
    assert not [n for n in zf.namelist() if n.startswith("word/fonts/")]


def test_the_practice_appears_on_the_page(om):
    """In the footer, as a field — not only in a property nothing displays.

    This is the defect the first pass shipped: the brand was *in* the file and
    not *on* it, which for a reader is the same as not being there.
    """
    zf = _dotx(om, "BW06-request-for-information")
    footer = zf.read("word/footer1.xml").decode()
    assert "PTS_Originator" in footer
    assert "DOCPROPERTY" in footer, "a field, so it follows the property"
    props = zf.read("docProps/custom.xml").decode()
    assert f"<vt:lpwstr>{om.identity.name}</vt:lpwstr>" in props


def test_the_footer_originator_stays_short(om):
    """A page footer is one line.

    The address belongs on the letterhead, which is one page and has room for
    it; in a footer beside the container id, revision and status it wraps every
    page in the document.
    """
    from brand.resolution.pts_bridge import build_overlay

    originator = build_overlay(om).properties["PTS_Originator"]
    assert originator == om.identity.name
    assert len(originator) <= 40


def test_font_files_do_not_leak_between_builds(om):
    import sys
    from pathlib import Path

    sys.path.insert(
        0, str(Path(__file__).resolve().parents[1] / "docs/templates/word")
    )
    import ptsword

    before = dict(ptsword.FONT_FILES)
    _dotx(om)
    assert ptsword.FONT_FILES == before
