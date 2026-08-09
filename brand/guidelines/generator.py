"""
brand/guidelines/generator.py

The brand guidelines document, generated from the brand.

A guidelines PDF is normally the place where a design system goes to die: it
is authored once, by hand, from the same decisions that are also encoded
somewhere else, and within a year the two disagree and nobody knows which is
right. Here the document has no content of its own. Every number, colour,
weight and rule on these eighteen pages is read from the resolved tokens or
from the brand, so the guidelines cannot drift from the system — they *are*
the system, printed.

Eighteen sections, in the order a reader needs them: what the practice is,
then what it looks like, then how it draws, then how it writes, then where all
of that gets applied.

Output is one self-contained HTML document with print CSS. ``brand/export``
turns it into a PDF through the browser's own print path.
"""

from __future__ import annotations

import html
from typing import Any, Callable

from brand import colour as _colour
from brand.assets.logo import LogoSystem, Variant
from brand.models.brand import Brand
from brand.models.tokens import TokenSet
from brand.templates.document_templates import TEMPLATES, coverage

#: The eighteen sections, in order. The list is the table of contents and the
#: build order at once, so a section cannot be added to one and not the other.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("01", "Brand"),
    ("02", "Positioning"),
    ("03", "Personality"),
    ("04", "Logo"),
    ("05", "Logo usage"),
    ("06", "Typography"),
    ("07", "Colours"),
    ("08", "Grid"),
    ("09", "Graphic language"),
    ("10", "Photography"),
    ("11", "Architectural drawings"),
    ("12", "Diagrams"),
    ("13", "Render language"),
    ("14", "Communication"),
    ("15", "Documents"),
    ("16", "Presentation"),
    ("17", "Digital"),
    ("18", "Social media"),
)


def render_guidelines(brand: Brand, *, tokens: TokenSet | None = None) -> str:
    """The whole document."""
    tokens = tokens or brand.resolve_tokens()
    logos = LogoSystem(brand, tokens)
    ctx = _Ctx(brand, tokens, logos)

    builders: dict[str, Callable[[_Ctx], str]] = {
        "01": _s_brand, "02": _s_positioning, "03": _s_personality,
        "04": _s_logo, "05": _s_logo_usage, "06": _s_typography,
        "07": _s_colours, "08": _s_grid, "09": _s_graphic,
        "10": _s_photography, "11": _s_drawings, "12": _s_diagrams,
        "13": _s_renders, "14": _s_communication, "15": _s_documents,
        "16": _s_presentation, "17": _s_digital, "18": _s_social,
    }
    pages = [_cover(ctx), _contents(ctx)]
    for number, title in SECTIONS:
        pages.append(_page(number, title, builders[number](ctx)))

    return f"""<!doctype html>
<html lang="{tokens.value('voice.language', 'en-GB')}">
<head><meta charset="utf-8">
<title>{html.escape(brand.identity.name)} — Brand Guidelines {html.escape(brand.version)}</title>
<style>{_css(tokens)}</style></head>
<body>{''.join(pages)}</body></html>
"""


class _Ctx:
    def __init__(self, brand: Brand, tokens: TokenSet, logos: LogoSystem) -> None:
        self.brand = brand
        self.t = tokens
        self.v = tokens.value
        self.logos = logos


# ---------------------------------------------------------------------------
# Page furniture
# ---------------------------------------------------------------------------


def _css(t: TokenSet) -> str:
    v = t.value
    return f"""
:root {{
  --font: {v('font.family.primary')}, {v('font.fallback.primary')}, sans-serif;
  --mono: {v('font.family.mono', 'monospace')}, monospace;
  --xs: {v('font.size.xs')}mm; --sm: {v('font.size.sm')}mm;
  --md: {v('font.size.md')}mm; --lg: {v('font.size.lg')}mm;
  --xl: {v('font.size.xl')}mm;
  --w-reg: {v('font.weight.regular')}; --w-med: {v('font.weight.medium')};
  --lead: {v('line_height.body')}; --track: {v('letter_spacing.uppercase')}%;
  --ink: {v('color.text.primary')}; --ink-2: {v('color.text.secondary')};
  --paper: {v('color.background')}; --surface: {v('color.surface')};
  --line: {v('color.border')}; --accent: {v('color.brand.accent')};
  --s1: {v('space.1')}mm; --s2: {v('space.2')}mm; --s3: {v('space.3')}mm;
  --margin: {v('grid.margin')}mm; --gutter: {v('grid.gutter')}mm;
  --rule: {v('graphic.rule')}mm;
}}
@page {{ size: A4 portrait; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; background: var(--paper); }}
body {{ font-family: var(--font); font-size: var(--sm); line-height: var(--lead);
        color: var(--ink); font-weight: var(--w-reg); }}
.pg {{ width: 210mm; min-height: 297mm; padding: var(--margin);
       background: var(--paper); position: relative;
       page-break-after: always; display: flex; flex-direction: column; }}
.pg > .body {{ flex: 1; }}
.num {{ font-family: var(--mono); font-size: var(--xs); color: var(--ink-2); }}
h1 {{ font-size: var(--xl); font-weight: var(--w-med); margin: 0 0 var(--s2);
      text-transform: uppercase; letter-spacing: var(--track); }}
h2 {{ font-size: var(--lg); font-weight: var(--w-med); margin: 0 0 var(--s2);
      text-transform: uppercase; letter-spacing: var(--track); }}
h3 {{ font-size: var(--xs); font-weight: var(--w-med); margin: var(--s2) 0 var(--s1);
      text-transform: uppercase; letter-spacing: var(--track); color: var(--ink-2); }}
p {{ margin: 0 0 var(--s1); max-width: 130mm; }}
.lede {{ font-size: var(--md); max-width: 130mm; }}
ul {{ margin: 0 0 var(--s1); padding-left: var(--s2); }}
li {{ margin-bottom: 1mm; }}
table {{ border-collapse: collapse; width: 100%; font-size: var(--xs); }}
th, td {{ text-align: left; padding: 2.5mm 5mm 2.5mm 0;
          border-bottom: var(--rule) solid var(--line); vertical-align: baseline; }}
th {{ text-transform: uppercase; letter-spacing: var(--track);
      color: var(--ink-2); font-weight: var(--w-med); }}
.mono {{ font-family: var(--mono); }}
.dim {{ color: var(--ink-2); }}
.head {{ display: flex; justify-content: space-between; align-items: baseline;
         border-bottom: var(--rule) solid var(--ink); padding-bottom: var(--s1);
         margin-bottom: var(--s2); }}
.foot {{ display: flex; justify-content: space-between; font-size: var(--xs);
         color: var(--ink-2); border-top: var(--rule) solid var(--line);
         padding-top: var(--s1); margin-top: var(--s2); }}
.swatches {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--s1); }}
.chip {{ height: 24mm; border: var(--rule) solid var(--line); }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: var(--gutter); }}
.three {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--gutter); }}
.spec {{ background: var(--surface); padding: var(--s2); }}
.rulebar {{ background: var(--ink); }}
.cols {{ display: flex; gap: var(--s1); }}
.cols div {{ flex: 1; height: 30mm; background: var(--surface);
             border: var(--rule) solid var(--line); }}
.do-dont {{ display: grid; grid-template-columns: 1fr 1fr; gap: var(--gutter);
            font-size: var(--xs); }}
.cover {{ justify-content: space-between; }}
.cover .big {{ font-size: calc(var(--xl) * 1.4); font-weight: var(--w-med);
               text-transform: uppercase; letter-spacing: var(--track); }}
@media screen {{
  body {{ padding: var(--s2); }}
  .pg {{ margin: 0 auto var(--s2); box-shadow: 0 0 0 var(--rule) var(--line); }}
}}
"""


def _page(number: str, title: str, body: str) -> str:
    return f"""<section class="pg">
  <div class="head"><span class="num">{number}</span>
    <span class="num">{html.escape(title)}</span></div>
  <div class="body"><h1>{html.escape(title)}</h1>{body}</div>
  <div class="foot"><span>Brand guidelines</span><span>{number}</span></div>
</section>"""


def _cover(c: _Ctx) -> str:
    logo = c.logos.build(Variant.PRIMARY)
    return f"""<section class="pg cover">
  <div>{logo.svg}</div>
  <div>
    <div class="big">Brand<br>guidelines</div>
    <p class="dim" style="margin-top:var(--s2)">
      {html.escape(c.brand.identity.descriptor)}</p>
  </div>
  <div class="num">
    Version {html.escape(c.brand.version)} ·
    {html.escape(c.brand.status.value)} ·
    ADOS {html.escape(c.brand.ados_edition)} ·
    {html.escape((c.brand.content_hash or '')[:12])}<br>
    Generated by the ADOS Brand System. Every value in this document is
    resolved from the brand definition; it is not maintained by hand.
  </div>
</section>"""


def _contents(c: _Ctx) -> str:
    rows = "".join(
        f'<tr><td class="mono">{n}</td><td>{html.escape(title)}</td></tr>'
        for n, title in SECTIONS
    )
    return f"""<section class="pg">
  <div class="head"><span class="num">—</span><span class="num">Contents</span></div>
  <div class="body"><h1>Contents</h1><table>{rows}</table></div>
  <div class="foot"><span>{html.escape(c.brand.identity.name)}</span>
    <span>{html.escape(c.brand.version)}</span></div>
</section>"""


def _table(rows: list[tuple[str, Any]]) -> str:
    return "<table>" + "".join(
        f"<tr><th>{html.escape(str(k))}</th><td>{v}</td></tr>" for k, v in rows
    ) + "</table>"


# ---------------------------------------------------------------------------
# The eighteen sections
# ---------------------------------------------------------------------------


def _s_brand(c: _Ctx) -> str:
    i = c.brand.identity
    values = "".join(f"<li>{html.escape(v)}</li>" for v in i.values)
    return f"""
<p class="lede">{html.escape(i.positioning or i.descriptor)}</p>
<h3>Mission</h3><p>{html.escape(i.mission or '—')}</p>
<h3>Vision</h3><p>{html.escape(i.vision or '—')}</p>
<h3>Values</h3><ul>{values or '<li>—</li>'}</ul>
<h3>Story</h3><p>{html.escape(c.brand.visual_identity.logo.concept or '—')}</p>
{_table([
    ("Practice", html.escape(i.name)),
    ("Descriptor", html.escape(i.descriptor)),
    ("Founded", i.founded or '—'),
    ("Locations", html.escape(', '.join(i.locations) or '—')),
    ("Scale", html.escape(i.practice_scale.value)),
])}"""


def _s_positioning(c: _Ctx) -> str:
    i = c.brand.identity
    kw = " · ".join(html.escape(k) for k in i.keywords)
    return f"""
<p class="lede">{html.escape(i.positioning)}</p>
<h3>Promise</h3><p>{html.escape(i.tagline or '—')}</p>
<h3>Keywords</h3><p class="dim">{kw or '—'}</p>
<h3>What this rules out</h3>
<p>Positioning is only useful where it excludes something. The keywords above
are the vocabulary of the practice; the words in section 14 under
<em>not used</em> are the ones it has decided against.</p>"""


def _s_personality(c: _Ctx) -> str:
    axes = c.brand.identity.personality
    primary = "".join(f"<li>{html.escape(a.value)}</li>" for a in axes[:4])
    secondary = "".join(f"<li>{html.escape(a.value)}</li>" for a in axes[4:])
    return f"""
<div class="two">
  <div><h3>Primary traits</h3><ul>{primary or '<li>—</li>'}</ul></div>
  <div><h3>Secondary traits</h3><ul>{secondary or '<li>—</li>'}</ul></div>
</div>
<h3>How the traits are used</h3>
<p>These are not adjectives for a mood board. Each one is read by the system:
the render language, the diagram style and the writing tone are derived from
them, and the validator reports when an output contradicts one — a
&ldquo;quiet&rdquo; practice with dramatic renders, for instance.</p>
{_table([
    ("Renders", html.escape(str(c.v('render.mood')).replace('_', ' '))),
    ("Diagrams", html.escape(str(c.v('diagram.style')))),
    ("Tone", html.escape(str(c.v('voice.tone')))),
])}"""


def _s_logo(c: _Ctx) -> str:
    primary = c.logos.build(Variant.PRIMARY)
    symbol = c.logos.build(Variant.SYMBOL)
    compact = c.logos.build(Variant.COMPACT)
    stacked = c.logos.build(Variant.STACKED)
    return f"""
<p>{html.escape(c.brand.visual_identity.logo.concept or
                'The mark is the practice name set in the primary face beside '
                'the constructed symbol.')}</p>
<h3>Primary</h3><div style="max-width:120mm">{primary.svg}</div>
<div class="three" style="margin-top:var(--s2)">
  <div><h3>Symbol</h3><div style="max-width:30mm">{symbol.svg}</div></div>
  <div><h3>Compact</h3><div style="max-width:30mm">{compact.svg}</div></div>
  <div><h3>Stacked</h3><div style="max-width:45mm">{stacked.svg}</div></div>
</div>
<h3>Construction</h3>
{_table([
    ("Module", f"{c.v('asset.logo.module')} mm"),
    ("Symbol field", f"{c.v('asset.logo.field')} mm square"),
    ("Aperture wall", f"{c.v('asset.logo.aperture_stroke')} mm"),
    ("Wordmark cap", f"{c.v('asset.logo.cap')} mm"),
    ("Tracking", f"{c.v('asset.logo.tracking')} %"),
    ("Typeface", html.escape(str(c.v('font.family.primary')))),
])}
<p class="dim">The mark is constructed on the same lattice the sheets are set
on. It is generated from the brand, not drawn: change the module and it
rebuilds.</p>"""


def _s_logo_usage(c: _Ctx) -> str:
    reversed_logo = c.logos.build(Variant.REVERSED)
    dont = "".join(
        f"<li>{html.escape(x)}</li>"
        for x in c.brand.visual_identity.logo.incorrect_uses
    )
    return f"""
<h3>Clear space</h3>
<p>{c.logos.clear_space_mm():g} mm on all sides — the wordmark cap height ×
{c.v('asset.logo.clear_space')}. Nothing enters this zone: not a rule, not an
image edge, not a page number.</p>
<h3>Minimum width</h3>
<p>{c.v('asset.logo.min_width')} mm for the primary lockup. Below this use the
compact mark, which is drawn for it.</p>
<h3>Reversed</h3><div style="max-width:120mm">{reversed_logo.svg}</div>
<p class="dim">The reversed lockup carries its clear space in the panel. A
reversed mark with type against the edge of its ground is a black bar.</p>
<h3>Permitted backgrounds</h3>
<p>{html.escape(', '.join(c.brand.visual_identity.logo.usage_rules.permitted_backgrounds))}
— tone {html.escape(str(c.brand.visual_identity.logo.usage_rules.permitted_backgrounds[0]))}
and lighter. On anything darker, use the reversed mark.</p>
<h3>Incorrect use</h3><ul>{dont}</ul>"""


def _s_typography(c: _Ctx) -> str:
    typo = c.brand.visual_identity.typography
    faces = [("Primary", typo.primary_font), ("Secondary", typo.secondary_font),
             ("Technical", typo.mono_font)]
    rows = "".join(
        f"<tr><td>{label}</td><td>{html.escape(f.family)}</td>"
        f"<td>{html.escape(f.classification.value)}</td>"
        f'<td class="mono">{f.cap_height_ratio:.4f}</td>'
        f"<td>{html.escape(f.fallback)}</td></tr>"
        for label, f in faces if f is not None
    )
    scale = "".join(
        f"<tr><td>{k}</td><td class='mono'>{c.v(f'font.size.{k}.step')}</td>"
        f"<td class='mono'>{c.v(f'font.size.{k}')} mm</td>"
        f"<td class='mono'>{c.v(f'font.size.{k}.pt')} pt</td></tr>"
        for k in ("display", "xl", "lg", "md", "sm", "xs")
    )
    roles = "".join(
        f"<tr><td>{html.escape(name)}</td><td class='mono'>{r.step}</td>"
        f"<td>{html.escape(r.face)}</td><td>{r.weight}</td>"
        f"<td>{'caps' if r.uppercase else 'sentence'}</td></tr>"
        for group in (typo.heading_styles, typo.body_styles, typo.numeric_styles)
        for name, r in group.items()
    )
    return f"""
<table><tr><th>Role</th><th>Family</th><th>Class</th><th>Cap ratio</th>
<th>Fallback</th></tr>{rows}</table>
<h3>Scale</h3>
<table><tr><th>Token</th><th>Step</th><th>Cap</th><th>Size</th></tr>{scale}</table>
<p class="dim">Point size is derived from cap height and the face's measured
cap-height ratio. It is never chosen: families differ by up to 8 %, and a
chosen point size silently mis-sizes every document.</p>
<h3>Hierarchy</h3>
<table><tr><th>Style</th><th>Step</th><th>Face</th><th>Weight</th><th>Case</th></tr>
{roles}</table>
<h3>Leading and tracking</h3>
{_table([
    ("Baseline", f"{c.v('line_height.baseline')} mm"),
    ("Line height", f"× {c.v('line_height.body')}"),
    ("Uppercase tracking", f"{c.v('letter_spacing.uppercase')} %"),
    ("Body tracking", f"{c.v('letter_spacing.body')} %"),
])}"""


def _s_colours(c: _Ctx) -> str:
    from brand.export.exporters import to_colour_table

    rows = to_colour_table(c.t)
    chips = "".join(
        f'<div><div class="chip" style="background:{r["hex"]}"></div>'
        f'<div class="num">{html.escape(r["token"].split(".", 1)[1])}</div>'
        f'<div class="num">{r["hex"]}</div></div>'
        for r in rows if r["token"].count(".") <= 2
    )
    table = "".join(
        f'<tr><td class="mono">{html.escape(r["token"])}</td>'
        f'<td class="mono">{r["hex"]}</td><td class="mono">{r["rgb"]}</td>'
        f'<td class="mono">{r["cmyk_uncalibrated"]}</td>'
        f'<td class="mono">{r["L_star"]}</td>'
        f'<td class="mono">{r["mono"]}</td></tr>'
        for r in rows
    )
    ratio = _colour.contrast_ratio(
        str(c.v("color.text.primary")), str(c.v("color.background"))
    )
    return f"""
<div class="swatches">{chips}</div>
<h3>Specification</h3>
<table><tr><th>Token</th><th>Hex</th><th>RGB</th><th>CMYK*</th><th>L*</th>
<th>Mono</th></tr>{table}</table>
<p class="dim">* CMYK is an uncalibrated conversion, given as a starting point
for a printer. Final separations come from a profiled conversion against the
actual press and stock.</p>
<h3>Contrast</h3>
<p>Text on background is {ratio:.1f}:1 against a {c.v('meta.ados.edition') and 7}:1
floor. The <em>Mono</em> column is what each colour becomes on a plotted
drawing — every drawing output is greyscale.</p>"""


def _s_grid(c: _Ctx) -> str:
    grid = c.brand.visual_identity.grid
    configs = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{cfg.columns}</td>"
        f"<td>{cfg.gutter_mm} mm</td><td>{cfg.margin_mm} mm</td>"
        f"<td>{cfg.measure_mm or '—'}</td></tr>"
        for name, cfg in sorted(grid.configurations.items())
    ) or (
        f"<tr><td>default</td><td>{grid.columns}</td><td>{grid.gutter_mm} mm</td>"
        f"<td>{grid.margin_mm} mm</td><td>—</td></tr>"
    )
    bars = "".join("<div></div>" for _ in range(grid.columns))
    spacing = "".join(
        f'<tr><td class="mono">space.{i}</td><td class="mono">'
        f'{c.v(f"space.{i}")} mm</td></tr>'
        for i in range(1, len(c.brand.visual_identity.spacing.scale) + 1)
    )
    return f"""
<div class="cols">{bars}</div>
<h3>Configurations</h3>
<table><tr><th>Format</th><th>Columns</th><th>Gutter</th><th>Margin</th>
<th>Measure</th></tr>{configs}</table>
<h3>Spacing scale</h3>
<table><tr><th>Token</th><th>Value</th></tr>{spacing}</table>
<h3>Lattice</h3>
{_table([
    ("Module", f"{c.v('grid.module')} mm"),
    ("Sub-module / baseline", f"{c.v('grid.baseline')} mm"),
    ("Base unit", f"{c.v('space.base')} mm"),
])}
<p class="dim">Everything is placed on the sub-module. A between-group gap is
at least twice a within-group gap, which is what makes grouping read as
grouping.</p>"""


def _s_graphic(c: _Ctx) -> str:
    g = c.brand.visual_identity.graphic_language
    prims = "".join(
        f"<tr><td>{html.escape(p.name)}</td><td class='mono'>{html.escape(p.key)}</td>"
        f"<td>{html.escape(p.description)}</td>"
        f"<td class='mono'>{p.stroke_tier}</td></tr>"
        for p in g.primitives
    ) or "<tr><td colspan='4' class='dim'>None declared.</td></tr>"
    return f"""
<p>The identity with the mark removed. These are the marks that make a page
recognisable when the logo is not on it.</p>
<h3>Primitives</h3>
<table><tr><th>Name</th><th>Key</th><th>Use</th><th>Weight</th></tr>{prims}</table>
<h3>Rules</h3>
<div style="max-width:120mm">
  <div class="rulebar" style="height:{c.v('graphic.rule.emphasis')}mm;margin:var(--s1) 0"></div>
  <div class="num">emphasis · {c.v('graphic.rule.emphasis')} mm</div>
  <div class="rulebar" style="height:{c.v('graphic.rule')}mm;margin:var(--s1) 0"></div>
  <div class="num">standard · {c.v('graphic.rule')} mm</div>
</div>
<h3>Decisions</h3>
{_table([
    ("Corners", html.escape(str(c.v('graphic.corner')))),
    ("Frame weight", f"{c.v('graphic.frame')} mm"),
    ("Images", "framed" if c.v('graphic.image_frame') else "unframed"),
    ("Captions", html.escape(str(c.v('graphic.caption_position')))),
    ("Separator spacing", f"{c.v('graphic.separator')} mm"),
])}
<p class="dim">{html.escape(g.notes or
  'Corners are square. A radius is a value that must be held identical in six '
  'output formats and never is.')}</p>"""


def _s_photography(c: _Ctx) -> str:
    im = c.brand.visual_identity.imagery
    seq = " → ".join(html.escape(s) for s in im.sequencing) or "—"
    return f"""
<p>{html.escape(im.photography or '—')}</p>
{_table([
    ("Treatment", html.escape(str(c.v('photo.treatment')))),
    ("Saturation", c.v('photo.saturation')),
    ("Perspective", html.escape(str(c.v('photo.perspective')))),
    ("Verticals", "corrected" if c.v('photo.verticals_corrected') else "as shot"),
    ("People", html.escape(str(c.v('photo.human_presence')))),
    ("Cropping", html.escape(str(c.v('photo.cropping')))),
    ("Detail share", f"{c.v('photo.detail_ratio'):.0%}"),
    ("Ratios", html.escape(', '.join(im.aspect_ratios))),
    ("Bleed", "yes" if im.bleed else "no — images are framed"),
])}
<h3>Sequence</h3><p>{seq}</p>
<p class="dim">A portfolio spread is a sequence, not a selection. An unstated
sequence is re-invented per project, and the set stops reading as one
practice.</p>"""


def _s_drawings(c: _Ctx) -> str:
    d = c.brand.architectural_language.drawing
    lw = d.lineweights
    weights = [("Cut", lw.cut_mm), ("Primary geometry", lw.primary_mm),
               ("Secondary geometry", lw.secondary_mm),
               ("Background", lw.background_mm),
               ("Annotation", lw.annotation_mm), ("Dimension", lw.dimension_mm)]
    bars = "".join(
        f'<tr><td>{name}</td>'
        f'<td style="width:70%"><div class="rulebar" '
        f'style="height:{w * 4:.2f}mm"></div></td>'
        f'<td class="mono">{w} mm</td></tr>'
        for name, w in weights
    )
    hierarchy = " → ".join(html.escape(x.value) for x in d.hierarchy)
    return f"""
<p>The drawing standard. Line weight encodes distance from the cut plane and
decreases monotonically away from it — this is the practice's most-issued
graphic, and it is the one that has to be right.</p>
<table>{bars}</table>
<p class="dim">Shown at ×4.</p>
<h3>Hierarchy</h3><p class="mono" style="font-size:var(--xs)">{hierarchy}</p>
<h3>Line types</h3>
<p class="mono">{html.escape(', '.join(d.line_types))}</p>
<h3>Hatches</h3>
<p class="mono">{html.escape(', '.join(d.hatch_tokens))} ·
density {html.escape(d.hatch_density.value)}</p>
<h3>Text</h3>
{_table([
    ("Room names", f"{c.v('font.size.sm')} mm cap"),
    ("Dimensions", f"{c.v('font.size.sm')} mm cap"),
    ("Drawing titles", f"{c.v('font.size.md')} mm cap"),
    ("Notes", f"{c.v('font.size.sm')} mm cap"),
    ("Annotation case", "upper" if d.annotation_uppercase else "sentence"),
])}
<p class="dim">{html.escape(d.notes or '')}</p>"""


def _s_diagrams(c: _Ctx) -> str:
    d = c.brand.architectural_language.diagrams
    palette = "".join(
        f'<div class="chip" style="background:{p};height:12mm"></div>'
        for p in (d.palette or ())
    )
    return f"""
<p>Every diagram — concept, site, circulation, programme, environmental,
exploded, sequencing, structural — shares one grammar: the projection below,
the stroke below, and the brand palette. A diagram in another style is a
diagram from another practice.</p>
{_table([
    ("Style", html.escape(str(c.v('diagram.style')))),
    ("Projection", html.escape(str(c.v('diagram.projection')))),
    ("Stroke", f"{c.v('diagram.stroke')} mm"),
    ("Fill tones", html.escape(', '.join(d.fill_tones))),
    ("Labels", f"{c.v('font.size.sm')} mm cap"),
])}
<h3>Palette</h3><div class="swatches">{palette or '<div class="dim">brand palette</div>'}</div>
<p class="dim">{html.escape(d.notes or
  'The palette is a subset of the brand palette. The validator rejects a '
  'diagram colour the brand has not declared.')}</p>"""


def _s_renders(c: _Ctx) -> str:
    r = c.brand.architectural_language.renders
    return f"""
<p>Reusable parameters, not a mood description. These are passed to the
rendering pipeline as they are.</p>
{_table([
    ("Lighting", html.escape(str(c.v('render.lighting')).replace('_', ' '))),
    ("Mood", html.escape(str(c.v('render.mood')).replace('_', ' '))),
    ("Sky", html.escape(str(c.v('render.sky')))),
    ("Contrast", c.v('render.contrast')),
    ("Saturation", c.v('render.saturation')),
    ("Focal length", f"{c.v('render.camera.focal_length')} mm"),
    ("Sensor", f"{c.v('render.camera.sensor_width')} mm"),
    ("Eye height", f"{c.v('render.camera.height')} m"),
    ("Verticals", "held" if c.v('render.camera.two_point') else "converging"),
    ("People", "yes" if c.v('render.people') else "no"),
    ("Material expression",
     html.escape(', '.join(r.material_expression)) or '—'),
])}
<p class="dim">{html.escape(r.notes or
  'The camera fields match the repository VisualState so a brand supplies the '
  'defaults for a design state rather than a parallel vocabulary.')}</p>"""


def _s_communication(c: _Ctx) -> str:
    comm = c.brand.communication
    terms = "".join(
        f"<tr><td>{html.escape(k)}</td><td class='dim'>not: {html.escape(v)}</td></tr>"
        for k, v in comm.terminology.items()
    ) or "<tr><td class='dim'>—</td><td></td></tr>"
    return f"""
<p>{html.escape(comm.writing_style or '—')}</p>
{_table([
    ("Tone", html.escape(comm.tone.value)),
    ("Person", html.escape(comm.person.value.replace('_', ' '))),
    ("Sentence cap", f"{comm.sentence_length_max} words"),
    ("Language", html.escape(comm.primary_language)),
    ("Also", html.escape(', '.join(comm.secondary_languages) or '—')),
    ("Dates", html.escape(comm.date_format)),
])}
<h3>Vocabulary</h3><p>{html.escape(', '.join(comm.vocabulary) or '—')}</p>
<h3>Not used</h3><p>{html.escape(', '.join(comm.forbidden_words) or '—')}</p>
<h3>Preferred terms</h3><table>{terms}</table>"""


def _s_documents(c: _Ctx) -> str:
    cov = coverage(c.t)
    rows = "".join(
        f"<tr><td>{html.escape(TEMPLATES[tid].title)}</td>"
        f"<td class='mono'>{html.escape(tid)}</td>"
        f"<td>{html.escape(TEMPLATES[tid].page)}</td>"
        f"<td>{'renders' if not miss else 'missing ' + str(len(miss))}</td></tr>"
        for tid, miss in sorted(cov.items())
        if TEMPLATES[tid].family.value in ("document", "sheet", "correspondence")
    )
    return f"""
<p>Every template binds to token names, never to values. A change to the brand
reaches all of them; none of them can drift.</p>
<table><tr><th>Template</th><th>Id</th><th>Format</th><th>State</th></tr>
{rows}</table>
<h3>Title blocks</h3>
<p>Drawing sheets use the PTS title block at 180 mm, driven by this brand's
line weights and typefaces through the PTS overlay. Sheet geometry is derived
from ADOS and is not the practice's to change.</p>"""


def _s_presentation(c: _Ctx) -> str:
    return f"""
<p>Six slide kinds, one deck: title, section, project, image, diagram, closing.
The sequence is part of the design — a deck assembled from whichever slide was
nearest is not a presentation.</p>
{_table([
    ("Format", "16:9"),
    ("Title size", f"{c.v('font.size.display')} mm cap"),
    ("Heading", f"{c.v('font.size.xl')} mm cap"),
    ("Body", f"{c.v('font.size.md')} mm cap"),
    ("Images", "framed, never bled"),
    ("Margin", f"{c.v('grid.margin')} mm × 1.5"),
])}
<p class="dim">Slide type is larger than document type because the reading
distance is larger. It is the same scale, further up.</p>"""


def _s_digital(c: _Ctx) -> str:
    w = c.brand.digital.web
    return f"""
<p>The site is an architecture studio's site: images, a name, and as little
else as possible.</p>
{_table([
    ("Structure", html.escape(' · '.join(w.sections))),
    ("Navigation", html.escape(w.nav.value)),
    ("Hero", html.escape(w.hero)),
    ("Project card", html.escape(w.project_card)),
    ("Columns", w.grid_columns),
    ("Max width", f"{w.max_content_width_px} px"),
    ("Images", html.escape(w.image_treatment)),
    ("Motion", html.escape(w.motion.value)),
    ("Transition", f"{w.transition_ms} ms"),
    ("Hover", html.escape(w.hover)),
    ("Dark mode", "yes" if w.dark_mode else "no"),
])}
<p class="dim">{html.escape(w.notes or
  'Motion is declared rather than left to a template. A studio whose drawings '
  'do not animate has already made the decision.')}</p>"""


def _s_social(c: _Ctx) -> str:
    s = c.brand.digital.social
    types = "".join(f"<li>{html.escape(t)}</li>" for t in s.post_types)
    return f"""
{_table([
    ("Platforms", html.escape(', '.join(s.platforms))),
    ("Formats", html.escape(', '.join(s.post_formats))),
    ("Caption cap", f"{s.caption_max_words} words"),
    ("Watermark", "yes" if s.watermark else "no"),
    ("Discipline", html.escape(s.grid_discipline)),
])}
<h3>Post types</h3><ul>{types}</ul>
<p class="dim">{html.escape(s.notes or
  'No watermark. A watermark on a photograph of a building says the image is '
  'the asset; the building is.')}</p>"""
