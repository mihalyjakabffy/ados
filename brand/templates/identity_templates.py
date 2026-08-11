"""
brand/templates/identity_templates.py

The second catalogue: stationery, presentation, marketing and the drawing
apparatus.

Split from ``document_templates.py`` because these are a different kind of
artefact. A report is a container for text someone writes; a business card, a
slide and a title block are *fixed compositions* — the content is short, known
in advance, and the design is the arrangement. So each one here carries a
``layout`` renderer that composes it, rather than a section list that a writer
fills.

They bind to the same tokens and go through the same ``DocumentTemplate``
contract, so ``coverage()`` and the consistency check see them exactly as they
see a report.
"""

from __future__ import annotations

import html
from typing import Any

from brand.assets.logo import text_outline
from brand.models.tokens import TokenSet
from brand.templates.document_templates import (
    DocumentTemplate,
    Family,
    Medium,
    RenderedDocument,
    Section,
    _t,
)

# The stationery and marketing set all need the mark, so the logo tokens join
# the shared bindings for this catalogue.
_MARK = ("asset.logo.field", "asset.logo.cap", "asset.logo.clear_space",
         "asset.logo.min_width", "asset.logo.monogram", "graphic.frame",
         "graphic.rule")


def _b(*extra: str) -> tuple[str, ...]:
    return _t(*(_MARK + extra))


# ---------------------------------------------------------------------------
# Layout helper — one page-shaped HTML document, styled entirely from tokens
# ---------------------------------------------------------------------------


def _page(
    template: DocumentTemplate, tokens: TokenSet, body: str, *,
    width_mm: float, height_mm: float, extra_css: str = "",
) -> RenderedDocument:
    v = tokens.value
    css = f"""
:root {{
  --font: {v('font.family.primary')}, {v('font.fallback.primary')}, sans-serif;
  --mono: {v('font.family.mono', v('font.family.primary'))}, monospace;
  --xs: {v('font.size.xs')}mm; --sm: {v('font.size.sm')}mm;
  --md: {v('font.size.md')}mm; --lg: {v('font.size.lg')}mm;
  --xl: {v('font.size.xl')}mm; --display: {v('font.size.display')}mm;
  --w-reg: {v('font.weight.regular')}; --w-med: {v('font.weight.medium')};
  --lead: {v('line_height.body')}; --track: {v('letter_spacing.uppercase')}%;
  --ink: {v('color.text.primary')}; --ink-2: {v('color.text.secondary')};
  --paper: {v('color.background')}; --surface: {v('color.surface')};
  --line: {v('color.border')}; --accent: {v('color.brand.accent')};
  --s1: {v('space.1')}mm; --s2: {v('space.2')}mm; --s3: {v('space.3')}mm;
  --margin: {v('grid.margin')}mm; --gutter: {v('grid.gutter')}mm;
  --rule: {v('graphic.rule')}mm; --frame: {v('graphic.frame')}mm;
  --clear: {v('asset.logo.clear_space')};
}}
@page {{ size: {width_mm}mm {height_mm}mm; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: var(--paper); }}
body {{ font-family: var(--font); font-size: var(--sm); color: var(--ink);
        line-height: var(--lead); font-weight: var(--w-reg); }}
.page {{ width: {width_mm}mm; height: {height_mm}mm; padding: var(--margin);
         background: var(--paper); position: relative; overflow: hidden;
         page-break-after: always; }}
.caps {{ text-transform: uppercase; letter-spacing: var(--track); }}
.med {{ font-weight: var(--w-med); }}
.mono {{ font-family: var(--mono); }}
.dim {{ color: var(--ink-2); }}
.rule {{ border: 0; border-top: var(--rule) solid var(--ink); margin: var(--s1) 0; }}
.hair {{ border: 0; border-top: var(--rule) solid var(--line); margin: var(--s1) 0; }}
.frame {{ border: var(--frame) solid var(--ink); }}
.imgbox {{ border: var(--frame) solid var(--line); background: var(--surface);
           display: flex; align-items: center; justify-content: center;
           color: var(--ink-2); font-size: var(--xs); }}
.wordmark {{ font-size: var(--md); font-weight: var(--w-med);
             text-transform: uppercase; letter-spacing: var(--track); }}
{extra_css}
"""
    doc = f"""<!doctype html>
<html lang="{v('voice.language', 'en-GB')}"><head><meta charset="utf-8">
<title>{html.escape(template.title)} — {html.escape(str(v('meta.brand.name')))}</title>
<style>{css}</style></head><body>{body}</body></html>
"""
    return RenderedDocument(
        template_id=template.template_id, medium=Medium.HTML, content=doc,
        brand_id=tokens.brand_id, brand_version=tokens.brand_version,
        tokens_used=tuple(template.bindings),
    )


def _mark(tokens: TokenSet, *, size_mm: float | None = None) -> str:
    """The aperture + wordmark lockup as a single SVG.

    One element, not a flex row of two: a lockup is an atomic object and its
    internal spacing belongs to the logo construction, not to the page. Built
    as CSS-with-a-gap it would also be a second implementation of the mark's
    geometry, drifting from ``brand/assets/logo.py`` the first time either
    changed — and its internal gap would be measured against the page lattice,
    which is not the lattice it is on.

    Every dimension comes from ``asset.logo.*``; the whole thing scales with
    ``size_mm`` because the proportions are ratios of the construction field.
    """
    v = tokens.value
    field_ref = float(v("asset.logo.field"))
    k = (size_mm / field_ref) if size_mm else 1.0          # uniform scale
    field = field_ref * k
    wall = float(v("asset.logo.aperture_stroke")) * k
    cap = float(v("asset.logo.cap")) * k
    gap = float(v("asset.logo.gap")) * k * 2
    ink = v("color.text.primary")
    raw = str(v("asset.logo.wordmark"))
    tracking = float(v("asset.logo.tracking"))
    inner = field - 2 * wall

    # Set the wordmark as outlines, measured with the real font metrics. An
    # estimated advance clipped "STUDIO OM" to "STUDIO O" in the first build —
    # the letterform is the thing the mark is made of, so it is measured, not
    # guessed, and the same routine the logo files use does the measuring.
    outline = text_outline(
        raw, family=str(v("font.family.primary")),
        weight=int(v("font.weight.medium")), cap_mm=cap,
        tracking_percent=tracking,
    )
    if outline.available:
        advance = outline.advance_mm
        mark = (
            f'<g fill="{ink}" transform="translate({field + gap:.2f} '
            f'{(field + cap) / 2:.2f})">{outline.path}</g>'
        )
    else:
        # No bundled face: live text, and a box wide enough that a wider
        # substitute cannot clip it.
        advance = len(raw) * cap * 1.05
        mark = (
            f'<text x="{field + gap:.2f}" y="{(field + cap) / 2:.2f}" fill="{ink}" '
            f'font-family="{v("font.family.primary")}, '
            f'{v("font.fallback.primary")}, sans-serif" '
            f'font-size="{cap / float(v("font.cap_ratio.primary")):.2f}" '
            f'font-weight="{v("font.weight.medium")}" '
            f'letter-spacing="{cap * tracking / 100:.3f}"'
            f'>{html.escape(raw)}</text>'
        )
    width = field + gap + advance
    return (
        f'<svg width="{width:.2f}mm" height="{field:.2f}mm" '
        f'viewBox="0 0 {width:.2f} {field:.2f}" '
        f'style="vertical-align:middle" role="img" '
        f'aria-label="{html.escape(raw)}">'
        f'<path fill-rule="evenodd" fill="{ink}" '
        f'd="M0 0h{field:.2f}v{field:.2f}h-{field:.2f}z'
        f'M{wall:.2f} {wall:.2f}v{inner:.2f}h{inner:.2f}v-{inner:.2f}z"/>'
        f'{mark}</svg>'
    )


# ---------------------------------------------------------------------------
# Stationery
# ---------------------------------------------------------------------------


def _business_card(t, tokens, **ctx) -> RenderedDocument:
    v = tokens.value
    person = ctx.get("person", "Name Surname")
    role = ctx.get("role", "Architect")
    body = f"""
<div class="page card">
  {_mark(tokens, size_mm=8)}
  <div class="details">
    <div class="med">{html.escape(person)}</div>
    <div class="dim">{html.escape(role)}</div>
    <div class="dim" style="margin-top:var(--s1)">
      {html.escape(ctx.get('email', 'name@studio.example'))}<br>
      {html.escape(ctx.get('phone', '+00 000 000 0000'))}
    </div>
  </div>
  <div class="foot caps dim">{html.escape(str(v('meta.brand.descriptor')))}</div>
</div>"""
    return _page(t, tokens, body, width_mm=85, height_mm=55, extra_css="""
.card { display: flex; flex-direction: column; justify-content: space-between;
        padding: var(--s1); }
.card .details { font-size: var(--xs); line-height: 1.5; }
.card .foot { font-size: var(--xs); }
""")


def _letterhead(t, tokens, **ctx) -> RenderedDocument:
    v = tokens.value
    letter_body = ctx.get(
        "body",
        "Letter body. The measure is set by the grid, not by the page: 120 mm "
        "holds roughly 67 characters at the body cap height.",
    )
    body = f"""
<div class="page">
  <header style="display:flex;justify-content:space-between;align-items:flex-start">
    {_mark(tokens, size_mm=10)}
    <div class="dim" style="font-size:var(--xs);text-align:right">
      {html.escape(ctx.get('address', 'Street 1 · 1000 City'))}<br>
      {html.escape(ctx.get('email', 'studio@example.com'))}
    </div>
  </header>
  <hr class="rule">
  <div style="margin-top:var(--s3);max-width:120mm">
    <p class="dim mono" style="font-size:var(--xs)">
      {html.escape(ctx.get('reference', 'REF 0000-000'))} ·
      {html.escape(ctx.get('date', '0000-00-00'))}</p>
    <p>{html.escape(letter_body)}</p>
  </div>
  <footer class="dim caps" style="position:absolute;left:var(--margin);
          right:var(--margin);bottom:var(--margin);font-size:var(--xs);
          border-top:var(--rule) solid var(--line);padding-top:var(--s1)">
    {html.escape(str(v('meta.brand.name')))} ·
    {html.escape(str(v('meta.brand.descriptor')))}
  </footer>
</div>"""
    return _page(t, tokens, body, width_mm=210, height_mm=297)


def _email_signature(t, tokens, **ctx) -> RenderedDocument:
    """Deliberately table-based: email clients do not do flexbox."""
    v = tokens.value
    body = f"""
<table cellpadding="0" cellspacing="0" style="font-family:{v('font.family.primary')},
  {v('font.fallback.primary')},sans-serif;font-size:11px;color:{v('color.text.primary')};
  line-height:1.5">
  <tr><td style="padding-bottom:4px;font-weight:{v('font.weight.medium')};
      text-transform:uppercase;letter-spacing:{v('letter_spacing.uppercase')}%">
      {html.escape(str(v('asset.logo.wordmark')))}</td></tr>
  <tr><td style="color:{v('color.text.secondary')};padding-bottom:6px">
      {html.escape(str(v('meta.brand.descriptor')))}</td></tr>
  <tr><td style="border-top:1px solid {v('color.border')};padding-top:6px">
      {html.escape(ctx.get('person', 'Name Surname'))} ·
      {html.escape(ctx.get('role', 'Architect'))}</td></tr>
  <tr><td style="color:{v('color.text.secondary')}">
      {html.escape(ctx.get('email', 'name@studio.example'))} ·
      {html.escape(ctx.get('phone', '+00 000 000 0000'))}</td></tr>
</table>"""
    return _page(t, tokens, body, width_mm=90, height_mm=40, extra_css="""
.page { display:none } body { padding: var(--s2); }
""")


# ---------------------------------------------------------------------------
# Presentation — six slide kinds, one deck
# ---------------------------------------------------------------------------


_SLIDE_W, _SLIDE_H = 338.7, 190.5          # 16:9 at A4 width


def _slide_shell(inner: str, *, kind: str) -> str:
    return f'<div class="page slide {kind}">{inner}</div>'


def _presentation(t, tokens, **ctx) -> RenderedDocument:
    v = tokens.value
    project = html.escape(ctx.get("project", "Project name"))
    slide_text = ctx.get(
        "text",
        "One idea per slide. A slide carrying three arguments carries none.",
    )
    slides = [
        _slide_shell(
            f'<div class="title-block">{_mark(tokens, size_mm=12)}'
            f'<h1>{project}</h1>'
            f'<p class="dim">{html.escape(ctx.get("subtitle", "Design review"))} · '
            f'{html.escape(ctx.get("date", "0000-00-00"))}</p></div>',
            kind="title"),
        _slide_shell(
            f'<div class="section"><span class="num mono">01</span>'
            f'<h2 class="caps">{html.escape(ctx.get("section", "Site"))}</h2></div>',
            kind="section"),
        _slide_shell(
            f'<div class="two"><div class="imgbox">Image — 3:2</div>'
            f'<div><h3 class="caps">{html.escape(ctx.get("heading", "Proposal"))}</h3>'
            f'<p>{html.escape(slide_text)}</p></div></div>',
            kind="project"),
        _slide_shell('<div class="imgbox full">Full-bleed image — framed, not bled</div>',
                     kind="image"),
        _slide_shell(
            '<div class="two"><div class="imgbox">Diagram — axonometric</div>'
            '<div><h3 class="caps">Diagram</h3>'
            '<p class="dim">Diagrams use the brand diagram palette and stroke, '
            'not slide-software defaults.</p></div></div>',
            kind="diagram"),
        _slide_shell(
            f'<div class="title-block">{_mark(tokens, size_mm=12)}'
            f'<p class="dim">{html.escape(str(v("meta.brand.descriptor")))}</p>'
            f'<p class="mono dim">{html.escape(ctx.get("email", "studio@example.com"))}</p>'
            f'</div>',
            kind="closing"),
    ]
    return _page(t, tokens, "".join(slides), width_mm=_SLIDE_W, height_mm=_SLIDE_H,
                 extra_css=f"""
.slide {{ display:flex; flex-direction:column; justify-content:center;
          padding: calc(var(--margin) * 1.5); }}
.slide h1 {{ font-size: var(--display); font-weight: var(--w-med); margin: var(--s2) 0 var(--s1);
             text-transform: uppercase; letter-spacing: var(--track); }}
.slide h2 {{ font-size: var(--xl); font-weight: var(--w-med); margin: 0; }}
.slide h3 {{ font-size: var(--md); font-weight: var(--w-med); margin: 0 0 var(--s1); }}
.slide .num {{ color: var(--ink-2); font-size: var(--sm); display:block;
               margin-bottom: var(--s1); }}
.slide .two {{ display:grid; grid-template-columns: 2fr 1fr; gap: var(--gutter);
               height: 100%; align-items: stretch; }}
.slide .imgbox {{ min-height: 60mm; }}
.slide .imgbox.full {{ height: 100%; }}
.slide.section {{ justify-content: flex-end; }}
""")


# ---------------------------------------------------------------------------
# Marketing
# ---------------------------------------------------------------------------


def _portfolio_spread(t, tokens, **ctx) -> RenderedDocument:
    v = tokens.value
    lead_text = ctx.get(
        "text", "Two sentences. What was there, and what was done about it."
    )
    seq = v("photo.sequence") or ["context", "approach", "interior", "detail"]
    tiles = "".join(
        f'<div class="imgbox">{html.escape(str(s))}</div>' for s in seq[:4]
    )
    body = f"""
<div class="page">
  <header style="display:flex;justify-content:space-between;align-items:baseline">
    <h1 class="caps">{html.escape(ctx.get('project', 'Project name'))}</h1>
    <span class="mono dim">{html.escape(ctx.get('code', '0000'))}</span>
  </header>
  <hr class="hair">
  <div class="lead">
    <p>{html.escape(lead_text)}</p>
    <dl class="facts">
      <dt>Location</dt><dd>{html.escape(ctx.get('location', 'City'))}</dd>
      <dt>Year</dt><dd>{html.escape(ctx.get('year', '0000'))}</dd>
      <dt>Area</dt><dd>{html.escape(ctx.get('area', '000 m²'))}</dd>
      <dt>Status</dt><dd>{html.escape(ctx.get('status', 'Completed'))}</dd>
    </dl>
  </div>
  <div class="tiles">{tiles}</div>
  <footer class="dim caps">{html.escape(str(v('meta.brand.name')))} ·
    {html.escape(str(v('meta.brand.descriptor')))}</footer>
</div>"""
    return _page(t, tokens, body, width_mm=420, height_mm=297, extra_css="""
h1 { font-size: var(--xl); font-weight: var(--w-med); margin: 0; }
.lead { display:grid; grid-template-columns: 2fr 1fr; gap: var(--gutter);
        margin: var(--s2) 0; }
.facts { display:grid; grid-template-columns: auto 1fr; gap: 0 var(--s1);
         margin:0; font-size: var(--xs); }
.facts dt { text-transform:uppercase; letter-spacing:var(--track); color:var(--ink-2); }
.facts dd { margin:0; }
.tiles { display:grid; grid-template-columns: repeat(4, 1fr); gap: var(--gutter);
         height: 150mm; }
footer { position:absolute; left:var(--margin); right:var(--margin);
         bottom:var(--margin); font-size:var(--xs); }
""")


def _competition_board(t, tokens, **ctx) -> RenderedDocument:
    v = tokens.value
    board_text = ctx.get(
        "text",
        "A board carrying three arguments carries none: at three metres a "
        "viewer reads one thing.",
    )
    body = f"""
<div class="page">
  <header><h1 class="caps">{html.escape(ctx.get('title', 'Board title'))}</h1>
    <span class="mono dim">{html.escape(ctx.get('code', 'ENTRY 0000'))}</span></header>
  <hr class="rule">
  <div class="grid">
    <div class="imgbox big">Primary image — 4 columns</div>
    <div class="text"><h3 class="caps">One argument</h3>
      <p>{html.escape(board_text)}</p></div>
    <div class="imgbox">Plan</div><div class="imgbox">Section</div>
    <div class="imgbox">Detail</div>
  </div>
  <footer class="caps dim">{html.escape(str(v('meta.brand.name')))} ·
    illustrative — not a construction document</footer>
</div>"""
    return _page(t, tokens, body, width_mm=841, height_mm=594, extra_css="""
header { display:flex; justify-content:space-between; align-items:baseline; }
h1 { font-size: calc(var(--display) * 1.6); font-weight: var(--w-med); margin:0; }
.grid { display:grid; grid-template-columns: repeat(6, 1fr);
        grid-auto-rows: minmax(120mm, auto); gap: var(--gutter); margin-top: var(--s3); }
.imgbox.big { grid-column: span 4; grid-row: span 2; }
.text { grid-column: span 2; }
.text h3 { font-size: var(--xl); margin:0 0 var(--s1); }
.text p { font-size: var(--lg); }
.imgbox { grid-column: span 2; }
footer { position:absolute; left:var(--margin); right:var(--margin);
         bottom:var(--margin); font-size: var(--sm); }
""")


def _social_post(t, tokens, **ctx) -> RenderedDocument:
    v = tokens.value
    body = f"""
<div class="page">
  <div class="imgbox">{html.escape(ctx.get('kind', 'project announcement'))}</div>
  <div class="foot">
    {_mark(tokens, size_mm=7)}
    <span class="mono dim">{html.escape(ctx.get('code', '0000'))}</span>
  </div>
</div>"""
    return _page(t, tokens, body, width_mm=100, height_mm=100, extra_css="""
.page { display:flex; flex-direction:column; gap: var(--s1); padding: var(--s2); }
.imgbox { flex:1; }
.foot { display:flex; justify-content:space-between; align-items:center;
        font-size: var(--xs); }
""")


def _website_home(t, tokens, **ctx) -> RenderedDocument:
    v = tokens.value
    nav = "".join(
        f'<a href="#">{html.escape(str(s))}</a>' for s in v("web.sections")
    )
    cards = "".join(
        f'<figure><div class="imgbox">Project {i}</div>'
        f'<figcaption><span class="med">Project {i}</span> '
        f'<span class="dim">· 202{i} · {html.escape(str(v("meta.brand.descriptor")))}'
        f'</span></figcaption></figure>'
        for i in (1, 2, 3, 4)
    )
    body = f"""
<div class="site">
  <nav>{_mark(tokens, size_mm=7)}<div class="links">{nav}</div></nav>
  <section class="hero"><div class="imgbox">{html.escape(str(v('web.hero')))}</div></section>
  <section class="projects">{cards}</section>
  <footer><span class="caps">{html.escape(str(v('meta.brand.name')))}</span>
    <span class="dim">{html.escape(str(v('meta.brand.descriptor')))}</span></footer>
</div>"""
    return _page(t, tokens, body, width_mm=360, height_mm=520, extra_css=f"""
.page {{ display:none }}
body {{ background: var(--paper); }}
.site {{ max-width: {v('web.max_width')}px; margin:0 auto; padding: var(--s2); }}
nav {{ display:flex; justify-content:space-between; align-items:center;
       padding-bottom: var(--s2); }}
nav .links a {{ margin-left: var(--s2); color: var(--ink); text-decoration:none;
                font-size: var(--sm); text-transform:uppercase;
                letter-spacing: var(--track); }}
nav .links a:hover {{ opacity:.7; transition: opacity {v('web.transition_ms')}ms; }}
.hero .imgbox {{ height: 180mm; }}
.projects {{ display:grid; grid-template-columns: repeat(2, 1fr);
             gap: var(--gutter); margin-top: var(--s3); }}
.projects figure {{ margin:0 }}
.projects .imgbox {{ height: 90mm; }}
.projects figcaption {{ font-size: var(--xs); padding-top: var(--s1); }}
footer {{ display:flex; gap: var(--s1); margin-top: var(--s3);
          border-top: var(--rule) solid var(--line); padding-top: var(--s1);
          font-size: var(--xs); }}
""")


# ---------------------------------------------------------------------------
# The catalogue
# ---------------------------------------------------------------------------


def _tpl(tid, title, family, page, purpose, renderer, bindings, sections=()):
    return DocumentTemplate(
        template_id=tid, title=title, family=family, page=page, purpose=purpose,
        sections=sections, bindings=bindings, medium=Medium.HTML,
        renderer=renderer,
    )


BUSINESS_CARD = _tpl(
    "BI01-business-card", "Business Card", Family.CORRESPONDENCE, "85×55",
    "The mark at its smallest credible size, and four facts.",
    _business_card, _b(),
    (Section("name", "Name"), Section("contact", "Contact", role="caption")),
)

LETTERHEAD = _tpl(
    "BI02-letterhead", "Letterhead", Family.CORRESPONDENCE, "A4-portrait",
    "Correspondence on the practice's own paper: mark, measure, footer.",
    _letterhead, _b("voice.language"),
    (Section("body", "Body"),),
)

EMAIL_SIGNATURE_HTML = _tpl(
    "BI03-email-signature", "Email Signature (HTML)", Family.CORRESPONDENCE,
    "inline",
    "Table-based because email clients do not do flexbox. The most-issued "
    "artefact a practice has.",
    _email_signature, _b(),
)

PRESENTATION_DECK = _tpl(
    "BI04-presentation-deck", "Presentation Deck", Family.PRESENTATION, "16:9",
    "Six slide kinds — title, section, project, image, diagram, closing — as "
    "one deck so the sequence is designed rather than assembled.",
    _presentation, _b("font.size.display", "photo.sequence"),
    tuple(Section(k, k.title()) for k in
          ("title", "section", "project", "image", "diagram", "closing")),
)

PORTFOLIO_SPREAD = _tpl(
    "BI05-portfolio-spread", "Portfolio Spread", Family.BOARD, "A3-landscape",
    "One project across one spread, in the practice's declared image sequence.",
    _portfolio_spread, _b("photo.sequence"),
)

COMPETITION_BOARD = _tpl(
    "BI06-competition-board", "Competition Board", Family.BOARD, "A1-landscape",
    "One argument at three metres, with the type sized for that distance.",
    _competition_board, _b("font.size.display"),
)

SOCIAL_POST = _tpl(
    "BI07-social-post", "Social Post", Family.CORRESPONDENCE, "1:1",
    "A square post with the mark small and the image doing the work.",
    _social_post, _b("social.formats"),
)

WEBSITE_HOME = _tpl(
    "BI08-website-home", "Website Homepage", Family.PRESENTATION, "screen",
    "The homepage art direction, rendered — structure, nav, hero, project "
    "cards and hover, all from the digital tokens.",
    _website_home,
    _b("web.sections", "web.hero", "web.max_width", "web.transition_ms",
       "web.motion", "web.nav"),
)

IDENTITY_TEMPLATES: dict[str, DocumentTemplate] = {
    t.template_id: t
    for t in (
        BUSINESS_CARD, LETTERHEAD, EMAIL_SIGNATURE_HTML, PRESENTATION_DECK,
        PORTFOLIO_SPREAD, COMPETITION_BOARD, SOCIAL_POST, WEBSITE_HOME,
    )
}


# ---------------------------------------------------------------------------
# The Word family
#
# These are not rendered here. They are the eight PTS ``.dotx`` templates in
# ``docs/templates/word/``, built by their own verified builder and branded
# through the same overlay the PDF sheets use. They appear in the catalogue so
# that ``coverage()``, the API and the consistency audit see the whole system —
# a deliverable that is real but invisible to the registry is a deliverable
# nobody checks.
#
# Word is the right medium for exactly these: long-form text somebody edits, on
# a page whose layout is a running header and a measure rather than an absolute
# coordinate. The five sheet-family documents stay PDFs for the opposite reason
# (see ``docs/templates/word/README.md``).
# ---------------------------------------------------------------------------


def _word(tid: str, title: str, page: str, purpose: str,
          extra: tuple[str, ...] = ()) -> DocumentTemplate:
    from brand.templates.renderers import render_word_dotx

    return DocumentTemplate(
        template_id=tid, title=title, family=Family.DOCUMENT, page=page,
        purpose=purpose, medium=Medium.DOCX, renderer=render_word_dotx,
        bindings=_t("font.family.mono", "asset.logo.wordmark", *extra),
    )


WORD_TEMPLATES: dict[str, DocumentTemplate] = {
    t.template_id: t for t in (
        _word("BW01-specification", "Specification (Word)", "A4-portrait",
              "Clause-numbered specification. Every standard cited carries its "
              "number, year and title; an undated citation changes the "
              "contractual requirement without a variation."),
        _word("BW02-door-schedule", "Door Schedule (Word)", "A3-landscape",
              "Twelve columns at A3. A separate file from the window schedule "
              "because T06 splits a schedule that overflows rather than hiding "
              "columns to fit."),
        _word("BW03-window-schedule", "Window Schedule (Word)", "A3-landscape",
              "The window half of the same schedule family, split for the same "
              "reason."),
        _word("BW04-meeting-minutes", "Meeting Minutes (Word)", "A4-portrait",
              "The editable record of what was decided and who owes what by "
              "when. Actions carry an owner and a date or they are not actions."),
        _word("BW05-site-visit-report", "Site Visit Report (Word)", "A4-portrait",
              "What was observed on site, by whom, on what date — the document "
              "a dispute is later reconstructed from."),
        _word("BW06-request-for-information", "Request for Information (Word)",
              "A4-portrait",
              "One question per RFI, set as the largest text on the page, with "
              "the date the answer is needed by."),
        _word("BW07-revision-log", "Revision Log (Word)", "A3-landscape",
              "The permanent record of every revision. A superseded revision is "
              "never deleted."),
        _word("BW08-transmittal", "Transmittal (Word)", "A4-portrait",
              "What was issued, to whom, when, and for what permitted use."),
        _word("BW10-information-request", "Information Request (Word)", "A4-portrait",
              "Asking a holder of records for a record that already exists. "
              "Every item names what it is needed for and what happens if it "
              "does not arrive, and a 'does not exist' is an answer rather "
              "than a blank."),
        _word("BW09-site-survey-record", "Site Survey Record (Word)", "A4-portrait",
              "The first visit: what is there, and how each fact was "
              "established. Carries a method register with an accuracy per "
              "method and a provenance token on every finding, because a "
              "drawing derived from it has to state where its dimensions came "
              "from."),
    )
}
