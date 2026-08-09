"""
brand/preview/brand_preview.py

The brand preview: one page that shows what the identity actually looks like.

A brand definition is a few hundred structured values, and nobody can read one
and know whether it is right. The preview is the artefact a human approves
against, so it shows the resolved tokens rendered rather than listed — the type
scale set in the face, the palette as swatches with their measured contrast,
the line weights drawn at true size, the graphic hierarchy as a strip.

It is a single self-contained HTML file with no external requests, because the
thing being previewed is a brand whose whole point is that it does not depend
on what the reader happens to have installed. Where a face is not available
the fallback is shown and labelled, which is itself information.

The validation findings are on the page too. A preview that shows only the
happy path is a preview that gets approved with two errors in it.
"""

from __future__ import annotations

import html
from typing import Any

from brand import colour as _colour
from brand.models.brand import Brand
from brand.models.tokens import TokenSet
from brand.templates.document_templates import TEMPLATES, coverage
from brand.validation.brand_validator import Severity


def render_preview(brand: Brand, *, tokens: TokenSet | None = None) -> str:
    """The whole preview, as one HTML document."""
    tokens = tokens or brand.resolve_tokens()
    report = brand.check()

    v = lambda k, d=None: tokens.value(k, d)               # noqa: E731

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(brand.identity.name)} — brand {html.escape(brand.version)}</title>
<style>{_css(tokens)}</style>
</head>
<body>
<div class="wrap">
{_header(brand, tokens)}
{_status(report)}
{_typography(brand, tokens)}
{_palette(brand)}
{_grid_block(tokens)}
{_architectural(brand, tokens)}
{_communication(brand)}
{_documents(tokens)}
{_findings(report)}
{_footer(brand, tokens)}
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------


def _css(tokens: TokenSet) -> str:
    v = tokens.value
    return f"""
:root {{
  --font: {v('font.family.primary')}, {v('font.fallback.primary')}, sans-serif;
  --mono: {v('font.family.mono', 'monospace')}, monospace;
  --bg: {v('color.background')};
  --surface: {v('color.surface')};
  --text: {v('color.text.primary')};
  --text-2: {v('color.text.secondary')};
  --border: {v('color.border')};
  --accent: {v('color.brand.accent')};
  --unit: {v('space.1')}mm;
  --gap: {v('space.2')}mm;
  --block: {v('space.3')}mm;
  --tracking: {v('letter_spacing.uppercase')}%;
}}
* {{ box-sizing: border-box; }}
html {{ background: var(--bg); }}
body {{
  margin: 0; font-family: var(--font); color: var(--text);
  background: var(--bg); line-height: {v('line_height.body')};
  font-size: 15px;
}}
.wrap {{ max-width: 1100px; margin: 0 auto; padding: var(--block) var(--gap) 40mm; }}
h1 {{ font-size: 34px; font-weight: {v('font.weight.medium')}; margin: 0;
      text-transform: uppercase; letter-spacing: var(--tracking); }}
h2 {{ font-size: 12px; text-transform: uppercase; letter-spacing: var(--tracking);
      color: var(--text-2); font-weight: {v('font.weight.medium')};
      margin: var(--block) 0 var(--unit); padding-bottom: 4px;
      border-bottom: 1px solid var(--border); }}
p {{ margin: 0 0 var(--unit); max-width: 62ch; }}
.muted {{ color: var(--text-2); }}
.mono {{ font-family: var(--mono); font-size: 13px; }}
.row {{ display: flex; gap: var(--gap); flex-wrap: wrap; align-items: baseline; }}
.card {{ background: var(--surface); border: 1px solid var(--border); padding: var(--gap); }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
td, th {{ text-align: left; padding: 5px 8px 5px 0; border-bottom: 1px solid var(--border);
          vertical-align: baseline; }}
th {{ font-size: 11px; text-transform: uppercase; letter-spacing: var(--tracking);
      color: var(--text-2); font-weight: {v('font.weight.medium')}; }}
.swatches {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
             gap: var(--unit); }}
.swatch .chip {{ height: 56px; border: 1px solid var(--border); }}
.swatch .label {{ font-size: 11px; margin-top: 4px; }}
.swatch .mono {{ font-size: 11px; color: var(--text-2); }}
.specimen {{ margin-bottom: 6px; white-space: nowrap; overflow: hidden;
             text-overflow: ellipsis; }}
.weights {{ display: grid; gap: 6px; }}
.weightrow {{ display: grid; grid-template-columns: 120px 1fr 90px; gap: var(--unit);
              align-items: center; font-size: 12px; }}
.rule {{ background: var(--text); }}
.hier {{ display: flex; gap: 2px; align-items: flex-end; height: 60px; }}
.hier div {{ flex: 1; background: var(--text); position: relative; }}
.hier span {{ position: absolute; bottom: -18px; left: 0; font-size: 10px;
              color: var(--text-2); text-transform: uppercase; }}
.pill {{ display: inline-block; padding: 2px 8px; border: 1px solid var(--border);
         font-size: 11px; text-transform: uppercase; letter-spacing: var(--tracking); }}
.ok {{ border-color: var(--accent); }}
.f-BLOCK, .f-ERROR {{ border-left: 3px solid {v('color.semantic.error')}; }}
.f-WARN {{ border-left: 3px solid {v('color.semantic.warning')}; }}
.f-INFO {{ border-left: 3px solid var(--border); }}
.finding {{ padding: 6px 0 6px 10px; margin-bottom: 6px; font-size: 13px; }}
.finding .where {{ font-family: var(--mono); font-size: 11px; color: var(--text-2); }}
/* Not inverted, and no dark-mode ground: this is a print identity, and
   previewing it against a colour the brand has not declared previews a brand
   the practice does not have. */
"""


def _header(brand: Brand, tokens: TokenSet) -> str:
    i = brand.identity
    return f"""<header>
  <h1>{html.escape(str(tokens.value('asset.logo.wordmark', i.name)))}</h1>
  <p class="muted">{html.escape(i.descriptor or '—')}
     {(' · ' + html.escape(i.tagline)) if i.tagline else ''}</p>
  <p class="mono muted">brand {html.escape(brand.version)} ·
     {html.escape(brand.status.value)} · ADOS {html.escape(brand.ados_edition)} ·
     {html.escape((brand.content_hash or '')[:12])}</p>
</header>"""


def _status(report) -> str:
    counts = {s: len(report.by_severity(s)) for s in Severity}
    pills = " ".join(
        f'<span class="pill">{n} {s.value.lower()}</span>'
        for s, n in counts.items() if n
    ) or '<span class="pill ok">validates clean</span>'
    return f'<div class="row" style="margin-top:8px">{pills}</div>'


def _typography(brand: Brand, tokens: TokenSet) -> str:
    typo = brand.visual_identity.typography
    faces = [("Primary", typo.primary_font), ("Secondary", typo.secondary_font),
             ("Mono", typo.mono_font)]
    face_rows = "".join(
        f"<tr><td>{html.escape(label)}</td><td>{html.escape(f.family)}</td>"
        f"<td>{html.escape(f.classification.value)}</td>"
        f'<td class="mono">{f.cap_height_ratio:.4f}</td>'
        f"<td>{html.escape(f.fallback)}</td></tr>"
        for label, f in faces if f is not None
    )

    specimens = []
    for token, label in (
        ("font.size.display", "display"), ("font.size.xl", "xl"),
        ("font.size.lg", "lg"), ("font.size.md", "md"),
        ("font.size.sm", "sm"), ("font.size.xs", "xs"),
    ):
        cap = tokens.value(token)
        pt = tokens.value(f"{token}.pt")
        step = tokens.value(f"{token}.step")
        # px so the browser shows the relative scale; the mm is the real value.
        px = round(float(pt) * 96 / 72, 1)
        specimens.append(
            f'<div class="specimen" style="font-size:{px}px">'
            f"Aa Bb Cc 0123 — {html.escape(label)}</div>"
            f'<div class="mono muted" style="margin-bottom:10px">{step} · '
            f"{cap} mm cap · {pt} pt</div>"
        )

    return f"""<section>
  <h2>Typography</h2>
  <table><tr><th>Role</th><th>Family</th><th>Class</th><th>Cap ratio</th><th>Fallback</th></tr>
  {face_rows}</table>
  <div style="margin-top:var(--gap)">{''.join(specimens)}</div>
  <p class="mono muted">Point sizes are derived from cap height and the face's
     measured cap-height ratio. They are not chosen.</p>
</section>"""


def _palette(brand: Brand) -> str:
    c = brand.visual_identity.colour
    entries = [
        ("Primary", c.primary), ("Secondary", c.secondary), ("Accent", c.accent),
        ("Background", c.background), ("Surface", c.surface),
        ("Text", c.text_primary), ("Text 2", c.text_secondary), ("Border", c.border),
    ]
    swatches = "".join(
        f'<div class="swatch"><div class="chip" style="background:{v}"></div>'
        f'<div class="label">{html.escape(k)}</div>'
        f'<div class="mono">{v} · L* {_colour.l_star(v):.0f}</div></div>'
        for k, v in entries
    )
    neutral = "".join(
        f'<div style="flex:1;height:36px;background:{v}"></div>'
        for v in brand.visual_identity.colour.neutral
    )
    ratio = _colour.contrast_ratio(c.text_primary, c.background)
    ratio2 = _colour.contrast_ratio(c.text_secondary, c.background)
    mono = "".join(
        f'<div style="flex:1;height:36px;'
        f'background:{_colour.to_greyscale_hex(v)}"></div>'
        for _, v in entries[:3]
    )
    return f"""<section>
  <h2>Colour</h2>
  <div class="swatches">{swatches}</div>
  <p class="mono muted" style="margin-top:var(--unit)">
     text on background {ratio:.1f}:1 · secondary {ratio2:.1f}:1 · floor 7:1</p>
  <h2>Neutral ramp</h2>
  <div style="display:flex">{neutral}</div>
  <h2>As plotted (monochrome)</h2>
  <div style="display:flex">{mono}</div>
  <p class="mono muted">Every drawing output is greyscale. Two brand colours
     that collapse to the same grey carry no information on a plotted sheet.</p>
</section>"""


def _grid_block(tokens: TokenSet) -> str:
    cols = int(tokens.value("grid.columns"))
    bars = "".join(
        '<div style="flex:1;background:var(--surface);'
        'border:1px solid var(--border);height:110px"></div>'
        for _ in range(cols)
    )
    return f"""<section>
  <h2>Grid</h2>
  <div style="display:flex;gap:calc({tokens.value('grid.gutter')}mm / 2)">{bars}</div>
  <p class="mono muted" style="margin-top:var(--unit)">
     {cols} columns · gutter {tokens.value('grid.gutter')} mm ·
     margin {tokens.value('grid.margin')} mm ·
     baseline {tokens.value('grid.baseline')} mm ·
     module {tokens.value('grid.module')} mm</p>
</section>"""


def _architectural(brand: Brand, tokens: TokenSet) -> str:
    lw = brand.architectural_language.drawing.lineweights
    weights = [
        ("Cut", lw.cut_mm), ("Seen", lw.primary_mm), ("Secondary", lw.secondary_mm),
        ("Beyond", lw.background_mm), ("Annotation", lw.annotation_mm),
        ("Dimension", lw.dimension_mm),
    ]
    # Drawn at ×4 so a 0.18 mm line is visible on screen; the label is the truth.
    rows = "".join(
        f'<div class="weightrow"><span>{html.escape(k)}</span>'
        f'<div class="rule" style="height:{v * 4:.2f}mm"></div>'
        f'<span class="mono">{v} mm</span></div>'
        for k, v in weights
    )
    hierarchy = brand.architectural_language.drawing.hierarchy
    n = max(len(hierarchy), 1)
    bars = "".join(
        f'<div style="height:{100 - i * (70 / n):.0f}%">'
        f"<span>{html.escape(layer.value)}</span></div>"
        for i, layer in enumerate(hierarchy)
    )
    r = brand.architectural_language.renders
    d = brand.architectural_language.diagrams
    materials = ", ".join(m.name for m in brand.architectural_language.materials.palette)
    return f"""<section>
  <h2>Drawing language</h2>
  <div class="weights">{rows}</div>
  <p class="mono muted" style="margin-top:6px">Shown at ×4. Weight encodes
     distance from the cut plane and must decrease monotonically.</p>

  <h2>Graphic hierarchy</h2>
  <div class="hier">{bars}</div>

  <h2>Diagrams and renders</h2>
  <table>
    <tr><th>Diagram</th><td>{html.escape(d.style.value)} ·
        {html.escape(d.projection.value)} · stroke {d.stroke_mm} mm ·
        tones {html.escape(', '.join(d.fill_tones))}</td></tr>
    <tr><th>Lighting</th><td>{html.escape(r.lighting.value.replace('_', ' '))}</td></tr>
    <tr><th>Mood</th><td>{html.escape(r.mood.value.replace('_', ' '))}</td></tr>
    <tr><th>Contrast / saturation</th><td>{r.contrast} / {r.saturation}</td></tr>
    <tr><th>Camera</th><td>{r.camera.focal_length_mm} mm at
        {r.camera.height_m} m{', verticals held' if r.camera.two_point_perspective else ''}</td></tr>
    <tr><th>Materials</th><td>{html.escape(materials or '—')}</td></tr>
  </table>
</section>"""


def _communication(brand: Brand) -> str:
    c = brand.communication
    forbidden = ", ".join(c.forbidden_words) or "—"
    terms = "".join(
        f"<tr><td>{html.escape(k)}</td><td class='muted'>not: {html.escape(v)}</td></tr>"
        for k, v in c.terminology.items()
    ) or "<tr><td class='muted'>—</td><td></td></tr>"
    sample_heading = brand.identity.tagline or brand.identity.descriptor or brand.identity.name
    sample_body = brand.identity.positioning or "No positioning statement set."
    return f"""<section>
  <h2>Communication</h2>
  <div class="card">
    <div style="font-size:22px;margin-bottom:8px">{html.escape(sample_heading)}</div>
    <p>{html.escape(sample_body)}</p>
  </div>
  <table style="margin-top:var(--unit)">
    <tr><th>Tone</th><td>{html.escape(c.tone.value)} · {html.escape(c.person.value.replace('_', ' '))}</td></tr>
    <tr><th>Sentence cap</th><td>{c.sentence_length_max} words</td></tr>
    <tr><th>Language</th><td>{html.escape(c.primary_language)}</td></tr>
    <tr><th>Not used</th><td>{html.escape(forbidden)}</td></tr>
  </table>
  <table style="margin-top:var(--unit)"><tr><th>Preferred term</th><th></th></tr>{terms}</table>
</section>"""


def _documents(tokens: TokenSet) -> str:
    cov = coverage(tokens)
    rows = "".join(
        f"<tr><td>{html.escape(TEMPLATES[tid].title)}</td>"
        f"<td class='mono'>{html.escape(tid)}</td>"
        f"<td>{html.escape(TEMPLATES[tid].family.value)}</td>"
        f"<td>{'renders' if not missing else html.escape('missing: ' + ', '.join(missing))}</td></tr>"
        for tid, missing in sorted(cov.items())
    )
    return f"""<section>
  <h2>Documents this brand can produce</h2>
  <table><tr><th>Template</th><th>Id</th><th>Family</th><th>State</th></tr>{rows}</table>
</section>"""


def _findings(report) -> str:
    if not report.findings:
        return ('<section><h2>Validation</h2><p class="muted">'
                "No findings. The brand conforms to ADOS.</p></section>")
    items = "".join(
        f'<div class="finding f-{f.severity.value}">'
        f'<div class="where">{html.escape(f.severity.value)} · '
        f"{html.escape(f.category.value)} · {html.escape(f.field)}"
        f"{(' · ' + html.escape(f.rule)) if f.rule else ''}</div>"
        f"<div>{html.escape(f.message)}</div>"
        + (f'<div class="muted">{html.escape(f.suggestion)}</div>' if f.suggestion else "")
        + "</div>"
        for f in report.sorted()
    )
    return f"<section><h2>Validation</h2>{items}</section>"


def _footer(brand: Brand, tokens: TokenSet) -> str:
    return f"""<footer style="margin-top:var(--block);padding-top:var(--unit);
      border-top:1px solid var(--border)" class="mono muted">
  {len(tokens)} resolved tokens · brand {html.escape(brand.version)} ·
  {html.escape(brand.status.value)} · generated by the ADOS Brand System
</footer>"""


def write_preview(brand: Brand, path: Any) -> Any:
    """Convenience: render and write. Returns the path."""
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_preview(brand))
    return p
