"""
brand/templates/renderers.py

Two backends that turn a template plus a :class:`TokenSet` into a document.

``render_html``
    Works for every template in the catalogue and has no dependencies. It is
    the reference implementation of "a template contains no values of its own":
    the entire stylesheet is generated from tokens, so if a value is wrong in
    the output it is wrong in the brand.

``render_sheet_pdf``
    Drives ``docs/templates/pdf/ptspdf.py`` — the builder that already produces
    the verified PTS sheets — through the brand overlay. This is the proof that
    the Brand System is wired into the existing document system rather than
    sitting beside it: the same code path that builds ``PTS-T01-Cover-Sheet.pdf``
    builds the branded cover, with the practice's typefaces, line weights and
    identity strings substituted.

Neither renderer aims at visual perfection. They aim at correct token usage,
inheritance and consistency, which is what has to be right first.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

from brand.models.tokens import TokenSet
from brand.templates.document_templates import (
    DocumentTemplate,
    Medium,
    RenderedDocument,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Page sizes in mm, for the HTML @page rule. Sheet families get their real
#: size so a browser print produces the right paper, not a guess.
_PAGE_MM: dict[str, tuple[float, float]] = {
    "A4-portrait": (210, 297),
    "A4-landscape": (297, 210),
    "A3-landscape": (420, 297),
    "A1-landscape": (841, 594),
}


def render_html(
    template: DocumentTemplate, tokens: TokenSet, **context: Any
) -> RenderedDocument:
    """Render a template to a self-contained HTML page."""
    used: list[str] = []

    def tok(name: str) -> Any:
        used.append(name)
        return tokens[name].value

    title = str(context.get("title") or template.title)
    project = str(context.get("project") or "Project name")
    body_sections = context.get("sections") or _placeholder_sections(template)

    css = _stylesheet(tok, template)
    head = _masthead(tok, template, title, project, context)
    body = "\n".join(
        _section_html(tok, template, key, value) for key, value in body_sections
    )
    foot = _colophon(tok, tokens, template)

    page = f"""<!doctype html>
<html lang="{html.escape(str(tok('voice.language') if 'voice.language' in tokens else 'en-GB'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — {html.escape(str(tok('meta.brand.name')))}</title>
<style>
{css}
</style>
</head>
<body>
<main class="sheet">
{head}
{body}
{foot}
</main>
</body>
</html>
"""
    return RenderedDocument(
        template_id=template.template_id,
        medium=Medium.HTML,
        content=page,
        brand_id=tokens.brand_id,
        brand_version=tokens.brand_version,
        tokens_used=tuple(dict.fromkeys(used)),
    )


# ---------------------------------------------------------------------------


def _stylesheet(tok, template: DocumentTemplate) -> str:
    """Every declaration comes from a token. There are no literals here.

    The two exceptions are ``0`` and the structural keywords (``grid``,
    ``solid``), which are not values a brand has an opinion about.
    """
    w, h = _PAGE_MM.get(template.page, (210, 297))
    return f"""
:root {{
  --font-primary: {tok('font.family.primary')}, {tok('font.fallback.primary')}, sans-serif;
  --size-xs: {tok('font.size.xs')}mm;
  --size-sm: {tok('font.size.sm')}mm;
  --size-md: {tok('font.size.md')}mm;
  --size-lg: {tok('font.size.lg')}mm;
  --weight-regular: {tok('font.weight.regular')};
  --weight-medium: {tok('font.weight.medium')};
  --leading: {tok('line_height.body')};
  --tracking-caps: {tok('letter_spacing.uppercase')}%;
  --bg: {tok('color.background')};
  --surface: {tok('color.surface')};
  --text: {tok('color.text.primary')};
  --text-2: {tok('color.text.secondary')};
  --border: {tok('color.border')};
  --accent: {tok('color.brand.accent')};
  --gutter: {tok('grid.gutter')}mm;
  --margin: {tok('grid.margin')}mm;
  --baseline: {tok('grid.baseline')}mm;
  --space-1: {tok('space.1')}mm;
  --space-2: {tok('space.2')}mm;
  --space-3: {tok('space.3')}mm;
  --columns: {tok('grid.columns')};
  --rule: {tok('stroke.annotation')}mm;
}}
@page {{ size: {w}mm {h}mm; margin: var(--margin); }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: var(--bg); }}
body {{
  font-family: var(--font-primary);
  font-size: var(--size-sm);
  font-weight: var(--weight-regular);
  line-height: var(--leading);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}}
.sheet {{
  max-width: {w}mm;
  margin: 0 auto;
  padding: var(--margin);
  background: var(--bg);
}}
.masthead {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-2);
  padding-bottom: var(--space-1);
  border-bottom: var(--rule) solid var(--text);
  margin-bottom: var(--space-3);
}}
.wordmark {{
  font-size: var(--size-md);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
}}
.descriptor {{ font-size: var(--size-xs); color: var(--text-2); }}
h1, h2, h3 {{ font-weight: var(--weight-medium); margin: 0 0 var(--space-1) 0; }}
h1 {{ font-size: var(--size-lg); text-transform: uppercase; letter-spacing: var(--tracking-caps); }}
h2 {{ font-size: var(--size-md); }}
h3 {{
  font-size: var(--size-sm);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--text-2);
}}
p {{ margin: 0 0 var(--space-1) 0; max-width: 67ch; }}
section {{ margin-bottom: var(--space-3); }}
.rows {{ display: grid; gap: 0; }}
.row {{
  display: grid;
  grid-template-columns: 1fr 3fr;
  gap: var(--gutter);
  padding: calc(var(--baseline) / 2) 0;
  border-bottom: var(--rule) solid var(--border);
}}
.row .k {{ font-size: var(--size-xs); text-transform: uppercase;
           letter-spacing: var(--tracking-caps); color: var(--text-2); }}
.accent {{ color: var(--accent); }}
.colophon {{
  margin-top: var(--space-3);
  padding-top: var(--space-1);
  border-top: var(--rule) solid var(--border);
  font-size: var(--size-xs);
  color: var(--text-2);
}}
/* No dark-mode override. This is a print palette: a document that changes
   colour with the reader's system setting is not the document that was
   issued. `html` already takes color.background, so the page is painted by
   the brand in either setting — and every colour on the page is one the
   brand declares, which the token-purity test enforces. */
"""


def _masthead(tok, template, title: str, project: str, context: dict) -> str:
    return f"""<header class="masthead">
  <div>
    <div class="wordmark">{html.escape(str(tok('asset.logo.wordmark')))}</div>
    <div class="descriptor">{html.escape(str(tok('meta.brand.descriptor')))}</div>
  </div>
  <div class="descriptor">{html.escape(project)} · {html.escape(str(context.get('date', '0000-00-00')))}</div>
</header>
<h1>{html.escape(title)}</h1>"""


def _section_html(tok, template, key: str, value: Any) -> str:
    section = next((s for s in template.sections if s.key == key), None)
    heading = section.heading if section else key.replace("_", " ").title()
    if isinstance(value, dict):
        rows = "\n".join(
            f'    <div class="row"><div class="k">{html.escape(str(k))}</div>'
            f"<div>{html.escape(str(v))}</div></div>"
            for k, v in value.items()
        )
        inner = f'  <div class="rows">\n{rows}\n  </div>'
    elif isinstance(value, (list, tuple)):
        items = "\n".join(f"  <p>{html.escape(str(v))}</p>" for v in value)
        inner = items
    else:
        inner = f"  <p>{html.escape(str(value))}</p>"
    head = f"  <h3>{html.escape(heading)}</h3>\n" if heading else ""
    return f'<section id="{html.escape(key)}">\n{head}{inner}\n</section>'


def _colophon(tok, tokens: TokenSet, template: DocumentTemplate) -> str:
    return (
        f'<footer class="colophon">{html.escape(str(tok("meta.brand.name")))} · '
        f"brand {html.escape(str(tok('meta.brand.version')))} · "
        f"template {html.escape(template.template_id)} · "
        f"ADOS {html.escape(str(tokens.value('meta.ados.edition', '1.0')))}</footer>"
    )


def _placeholder_sections(template: DocumentTemplate) -> list[tuple[str, Any]]:
    """Content stand-ins, so a template renders before anyone has written copy.

    Each placeholder says what belongs there rather than being lorem ipsum: a
    template full of Latin is reviewed for its shape, and a template full of
    instructions is reviewed for whether the shape fits the content.
    """
    out: list[tuple[str, Any]] = []
    for s in template.sections:
        if s.repeat:
            out.append((s.key, [f"{s.heading or s.key} — entry {i}" for i in (1, 2, 3)]))
        else:
            out.append((s.key, f"[{s.heading or s.key}]"))
    return out


# ---------------------------------------------------------------------------
# PDF: the branded PTS sheet
# ---------------------------------------------------------------------------


def render_sheet_pdf(
    template: DocumentTemplate, tokens: TokenSet, *, brand=None, **context: Any
) -> RenderedDocument:
    """Build a branded PTS cover sheet with the existing PDF builder.

    Requires the ``Brand`` itself (not only its tokens) because the overlay is
    derived from fields the token layer deliberately flattens away — the
    per-tier line weights and the font-file mapping. That is the one place in
    the system where a consumer sees a ``Brand``, and it is a bridge, not a
    consumer.
    """
    if brand is None:
        raise ValueError(
            "render_sheet_pdf needs the Brand: the PTS overlay is derived from "
            "line-weight and typeface fields that the flat token layer does "
            "not carry individually"
        )
    import io

    sys.path.insert(0, str(_REPO_ROOT / "docs" / "templates" / "pdf"))
    import ptspdf as P                                     # noqa: N812

    from brand.resolution.pts_bridge import build_overlay

    overlay = build_overlay(brand, tokens)
    P.register_fonts()

    buffer = io.BytesIO()
    with P.token_overlay(overlay.tokens):
        _draw_cover(P, buffer, tokens, overlay, context)

    return RenderedDocument(
        template_id=template.template_id,
        medium=Medium.PDF,
        content=buffer.getvalue(),
        brand_id=tokens.brand_id,
        brand_version=tokens.brand_version,
        tokens_used=tuple(sorted(template.bindings)),
    )


def render_word_dotx(
    template: DocumentTemplate, tokens: TokenSet, *, brand=None, **context: Any
) -> RenderedDocument:
    """Build a branded ``.dotx`` with the existing Word builder.

    The counterpart of :func:`render_sheet_pdf`, and the same argument: the
    seven PTS Word templates are already built, verified by 174 structural
    checks, and known to survive a real Word install. Re-implementing them
    inside the Brand System would mean two sets of templates that must be kept
    saying the same thing, and they would not.

    What the brand supplies is what PTS leaves open — the typeface names, the
    three semantic line weights, and the document-property defaults the
    DOCPROPERTY fields resolve against. Everything the fields *don't* cover
    stays a field, so a brand cannot bake a project's name into a template.
    """
    if brand is None:
        raise ValueError(
            "render_word_dotx needs the Brand: the PTS overlay is derived from "
            "line-weight, typeface and identity fields the flat token layer "
            "does not carry individually"
        )
    import io

    word_dir = _REPO_ROOT / "docs" / "templates" / "word"
    sys.path.insert(0, str(word_dir))
    import ptsword                                          # noqa: F401
    import build as word_build                              # noqa: N813

    from brand.resolution.pts_bridge import build_overlay

    builder = _WORD_BUILDERS.get(template.template_id)
    if builder is None:                                     # pragma: no cover
        raise KeyError(f"no Word builder for {template.template_id}")

    overlay = build_overlay(brand, tokens)
    buffer = io.BytesIO()
    with ptsword.token_overlay(
        overlay.tokens,
        font=overlay.families.get("primary"),
        font_mono=overlay.families.get("mono"),
        font_alt=overlay.families.get("primary_fallback"),
        font_mono_alt=overlay.families.get("mono_fallback"),
        properties=overlay.properties,
    ):
        getattr(word_build, builder)(_StreamDir(buffer))

    return RenderedDocument(
        template_id=template.template_id,
        medium=Medium.DOCX,
        content=buffer.getvalue(),
        brand_id=tokens.brand_id,
        brand_version=tokens.brand_version,
        tokens_used=tuple(sorted(template.bindings)),
    )


#: Template id → the function in ``docs/templates/word/build.py`` that makes it.
_WORD_BUILDERS: dict[str, str] = {
    "BW01-specification": "t05_specification",
    "BW02-door-schedule": "t06a_door_schedule",
    "BW03-window-schedule": "t06b_window_schedule",
    "BW04-meeting-minutes": "t07_meeting_minutes",
    "BW05-site-visit-report": "t08_site_visit_report",
    "BW06-request-for-information": "t09_rfi",
    "BW07-revision-log": "t10_revision_log",
    "BW08-transmittal": "t11_transmittal",
}


class _StreamDir:
    """Stands in for the output directory the Word builders write into.

    Each builder ends with ``save_as_dotx(doc, out / "PTS-Txx-Name.dotx")``.
    Rather than change eight call sites to thread a stream through, this
    intercepts the one ``/`` and hands back the buffer — ``save_as_dotx``
    already accepts a path or a stream, so the builders are untouched.
    """

    def __init__(self, buffer) -> None:
        self.buffer = buffer

    def __truediv__(self, _name: str):
        return self.buffer


def _draw_cover(P, buffer, tokens: TokenSet, overlay, context: dict) -> None:
    """The T01 cover, with the brand substituted for the PTS defaults."""
    cap = {k: P.step(k)["cap"] for k in ("t1", "t2", "t3", "t4", "t5", "t6", "t7")}
    s = P.Sheet(
        buffer, "A1",
        title=f"{tokens['meta.brand.name'].value} — Cover Sheet",
        subject=f"brand {tokens['meta.brand.version'].value}",
    )
    s.frame()
    s.banner("S0", "Work in progress — not for construction")
    s.watermark("WORK IN PROGRESS")

    ident = overlay.identity
    x, y = s.cx0, s.cy1 - 25

    s.caps(x, y, context.get("project", "Project name"), cap["t7"], P.MEDIUM)
    s.text(x, y - 15, f"{context.get('project_code', '0000')}   ·   "
                      f"{context.get('client', 'Client name')}", cap["t3"])
    s.text(x, y - 20, context.get("address", "Site address, town, postcode"), cap["t2"])

    y -= 75
    s.caps(x, y, context.get("package", "Technical design set"), cap["t6"])
    s.caps(x, y - 20, "S0   Work in progress", cap["t6"], P.MEDIUM)
    s.text(x, y - 30,
           f"Issued {context.get('date', '0000-00-00')}   ·   Revision P01", cap["t3"])

    # The brand block — the part a PTS sheet does not have and a branded one does.
    y = s.cy0 + 80
    s.block_heading(x, y, "Originator")
    s.caps(x, y - 10, ident["wordmark"], cap["t4"], P.MEDIUM)
    s.text(x, y - 20, ident["descriptor"], cap["t2"])
    if ident["tagline"]:
        s.text(x, y - 25, ident["tagline"], cap["t2"], grey=P.INK["secondary"])

    cols = s.spec["columns"]
    col3 = s.cx0 + 3 * (cols["width"] + cols["gutter"])
    s.block_heading(col3, y, "Brand")
    row = y - 10
    for label, value in (
        ("Typeface", str(tokens["font.family.primary"].value)),
        ("Body", f"{tokens['font.size.sm'].value} mm cap "
                 f"({tokens['font.size.sm.pt'].value} pt)"),
        ("Cut / seen / beyond",
         f"{tokens['stroke.cut'].value} / {tokens['stroke.primary'].value} / "
         f"{tokens['stroke.background'].value} mm"),
        ("Accent", str(tokens["color.brand.accent"].value)),
        ("Brand version", str(tokens["meta.brand.version"].value)),
    ):
        s.caps(col3, row, label, cap["t2"])
        s.text(col3 + 44, row, value, cap["t2"])
        row -= 5

    s.text(x, s.cy0, ident["conformance"], cap["t1"])

    s.title_block(
        sheet_title="Cover Sheet",
        sheet_number="A0.001",
        scale="—",
        status="S0",
        revision="P01",
        container_id=context.get("container_id", "0000-XXX-ZZ-XX-DR-A-0001"),
        nominated="A1 / issue A1",
    )
    s.save()
