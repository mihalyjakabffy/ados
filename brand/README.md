# ADOS Brand System

The identity layer of the ADOS design-system stack.

```
ADOS tokens  ──constrain──►  BRAND  ──resolve──►  design tokens
(what is legal)          (what this practice chooses)      │
                                                           │
                      ┌────────────────────────────────────┼──────────────┐
                      ▼                                    ▼              ▼
                  DOCUMENTS                            DRAWINGS       RENDERS
             PTS PDF · Word · HTML                    (Archicad)     (pipeline)
```

The repository already had two layers of this stack. `docs/ados/machine/ados-tokens.json`
holds the standard — the type scale, the line tiers, the tone ladder, the contrast floors, each
derived from a root fact about vision, memory, print or paper. `docs/templates/machine/pts-tokens.json`
holds the practice geometry, and two builders consume it to produce real documents.

The Brand System is the layer between them: what a practice *chooses* inside what the standard
*permits*. That is why `BrandValidator` can check a lineweight hierarchy against `line.tier_ratio`
and an accent colour against `colour.min_delta_L_between_meanings` instead of matching strings.

## Quick start

```bash
python -m brand.cli demo                # the whole flow, end to end
python -m brand.cli validate            # the worked example
python -m brand.cli tokens --flat
python -m brand.cli preview --out preview.html
python -m brand.cli render BT05-project-cover --out cover.pdf
python -m brand.cli propose "A quiet, material practice doing adaptive reuse."

python -m brand.cli logo --brand studio-om --out logo/
python -m brand.cli guidelines --brand studio-om --pdf
python -m brand.cli export --brand studio-om
python -m brand.cli package                  # the whole STUDIO OM package
python -m brand.cli audit brand/examples/studio-om --brand studio-om
```

```python
from brand import Brand, BrandAgent

brand  = Brand.create(name="Studio Nord", primary_font="Inter")
report = brand.check()                  # structural · consistency · architectural
tokens = brand.resolve_tokens()         # every value with its provenance
doc    = brand.apply_to(template)

proposal = BrandAgent().generate_proposal(brief)
brand    = proposal.approve(approved_by="MJ")   # the human step
```

## What is here

| Path | Contents |
|---|---|
| `models/` | The `Brand` aggregate — identity, visual identity, architectural language, communication, and the token model |
| `ados.py` | The binding to the standard. The only place the Brand System reads ADOS |
| `colour.py` | sRGB → L\*a\*b\*, contrast, monochrome collapse. ADOS states its limits in L\*, brands are authored in hex |
| `validation/` | Three categories of check, each finding naming a field, a cause and a fix |
| `resolution/` | `BrandResolver` (brand → tokens) and `pts_bridge` (tokens → the PTS builders) |
| `versioning/` | Semantic versions, lineage, and the immutability of a published version |
| `agents/` | `BrandAgent`, subclassing the repository's `BaseAgent` |
| `templates/` | Twenty-six declarative templates in two catalogues, and three renderers |
| `preview/` | A self-contained HTML preview — the artefact a human approves against |
| `store/` | File-backed and SQL-backed repositories behind one protocol |
| `schemas/` | JSON Schema, generated from the models |
| `assets/` | The logo system — SVG variants generated from the brand's own typeface and module |
| `export/` | CSS variables, JSON, YAML, the colour table, PNG/PDF via the browser, and the asset inventory |
| `guidelines/` | The eighteen-section brand guidelines, generated from the tokens |
| `consumers.py` | Phase-5 interfaces: Archicad attributes, render parameters |
| `examples/studio_nord.py` | A small worked example |
| `examples/studio_om.py` | **STUDIO OM** — a full practice identity |
| `examples/build_studio_om.py` | Builds the complete STUDIO OM package |
| `examples/studio-om/` | That package: 48 assets, audited |

Persistence lives in `schemas/brand_models.py` and `alembic/versions/011_brand_system.py`, following
the repository's convention that ORM classes share one `Base` under `schemas/`. The HTTP surface is
`api/routers/brand.py`, mounted at `/api/v2`.

## Five rules the code enforces

**1. The brand is the source of truth.** No module keeps its own copy of a brand value. If you find
yourself writing `"#111111"` outside `examples/`, the token layer has been bypassed.

**2. Tokens are the only bridge.** A template binds to `color.text.primary`; it never sees a `Brand`.
`test_html_render_contains_no_hard_coded_identity` fails the build if a literal colour appears in a
rendered document, and `DocumentTemplate.bindings` makes a template's dependencies checkable without
rendering it.

The single sanctioned exception is `resolution/pts_bridge.py`, which takes a `Brand` because it needs
the six individual lineweights and the font-file mapping that the flat layer collapses. It is a
bridge, not a consumer.

**3. AI proposes, the user approves.** `BrandAgent.generate_proposal()` returns a `BrandProposal` —
never a `Brand`. `proposal.approve(approved_by=...)` requires a named human and refuses a proposal
that does not validate. `POST /brand-proposals` writes nothing.

**4. Architecture is first-class.** `architectural_language` is parameters, not adjectives:
millimetres validated against the ISO 128 series, an explicit graphic hierarchy the validator checks
is monotone, camera settings shaped like the repository's own `VisualState`.

**5. Published versions are immutable.** A drawing issued in 2024 was drawn against the 2024 brand.
Both stores refuse to overwrite a published version with different content; `bump()` is the only way
forward.

## The token namespace

Twenty closed namespaces (`brand/models/tokens.py`). A resolver emitting a name outside them raises,
which is what stops the vocabulary drifting into near-synonyms.

```
font.*     line_height.*  letter_spacing.*  color.*   space.*   grid.*
stroke.*   tone.*         radius.*          shadow.*  opacity.*
render.*   diagram.*      graphic.*         photo.*   web.*     social.*
voice.*    asset.*        meta.*
```

Every token carries its unit, the brand field it came from, and — where ADOS bounded it — the rule:

```python
>>> tokens["font.size.sm.pt"]
Token(name='font.size.sm.pt', value=9.74, unit='pt',
      source='derived: 2.5 mm cap ÷ 0.7275 cap-ratio',
      constraint='ADOS-2.4.020 — point size is derived, never chosen')
```

Point size is never authored. It is computed from the cap height the standard specifies and the
cap-height ratio measured from the font binary, because families differ by up to 8 % and a chosen
point size silently mis-sizes every document.

## What the validator catches that a branding tool cannot

| Check | Why it matters |
|---|---|
| Reversed lineweight hierarchy | Weight encodes distance from the cut plane. A reversed pair makes the drawing say the opposite of what is built. **Blocks.** |
| Weight off the ISO 128 series | The plotter rounds it, so the drawn hierarchy is not the plotted one |
| Weight below 0.18 mm | Eroded by copying; gone by the second generation |
| Body text below 2.5 mm cap | Unreadable at arm's length on a site table. Provenance text may use 1.8 mm, and must say so |
| Text contrast below 7:1 | The floor is set for a document read under site lighting and photocopied |
| Accent within ΔL\* 18 of primary | Two colours that mean different things must differ in lightness, because a plotted sheet discards hue |
| Palette collapsing to one grey | Every drawing output is monochrome |
| Diagram colours outside the brand palette | The commonest way a set stops looking like one practice |
| More than four tones per sheet | Working memory holds about four states per channel |
| Grid off the 5 mm lattice | Every column lands off it too |
| Dramatic renders on a "quiet" practice | The portfolio stops looking like the stationery |

`WARN` never blocks. A practice is allowed a considered choice the system would not have made; a
validator that refuses one gets routed around.

## The templates

Ten declarative categories. `coverage(tokens)` reports which a given brand can render before
anything is attempted — a brand with no monospace face cannot produce the invoice, and saying so is
better than substituting a proportional face and shipping an invoice whose columns do not line up.

| Id | Template | Family | Medium |
|---|---|---|---|
| `BT01-a4-report` | A4 Report | document | HTML |
| `BT02-a3-technical` | A3 Technical Document | document | HTML |
| `BT03-presentation` | Presentation | presentation | HTML |
| `BT04-portfolio-page` | Portfolio Page | board | HTML |
| `BT05-project-cover` | Project Cover | sheet | **PDF, via `ptspdf.py`** |
| `BT06-meeting-minutes` | Meeting Minutes | document | HTML |
| `BT07-project-report` | Project Report | document | HTML |
| `BT08-proposal` | Proposal | document | HTML |
| `BT09-invoice` | Invoice | document | HTML |
| `BT10-email-signature` | Email Signature | correspondence | HTML |
| `BI01-business-card` | Business Card | correspondence | HTML |
| `BI02-letterhead` | Letterhead | correspondence | HTML |
| `BI03-email-signature` | Email Signature (table-based) | correspondence | HTML |
| `BI04-presentation-deck` | Presentation Deck — six slide kinds | presentation | HTML |
| `BI05-portfolio-spread` | Portfolio Spread | board | HTML |
| `BI06-competition-board` | Competition Board | board | HTML |
| `BI07-social-post` | Social Post | correspondence | HTML |
| `BI08-website-home` | Website Homepage | presentation | HTML |
| `BW01`–`BW08` | Specification · Door / Window Schedule · Meeting Minutes · Site Visit Report · RFI · Revision Log · Transmittal | document | **`.dotx`, via `ptsword.py`** |

Two of these are load-bearing. `BT05` is built by `docs/templates/pdf/ptspdf.py` and the `BW`
family by `docs/templates/word/ptsword.py` — the same code that produces the verified PTS sheets and
the eight `.dotx` templates — each driven by a brand overlay. Change the brand's cut weight and the
plotted line changes; change the typeface and the Word font table follows, `w:altName` included.

A branded `.dotx` also **embeds its fonts** (ECMA-376 §17.8.1 obfuscation) and prints the practice
name in the page footer as a field. Both exist because the first pass had neither: the brand was in
the file — in the font table and a custom property — and not on the page, which for a reader is the
same as not being there, and the document rendered in whatever serif the reader happened to
substitute.

The branded files are checked by the PTS verifier itself: `tests_brand` runs
`docs/templates/word/verify.py` against the *branded* output and requires all 174 checks to pass, so
branding a template cannot quietly break it.

## The PTS overlay

Six paths, whitelisted in `resolution/pts_bridge.py`:

```
line.tiers.W1  line.tiers.W2  line.tiers.W3
type.uppercase_tracking_percent
module.M  module.sub
```

Alongside the token paths the overlay carries three things that are not PTS tokens at all, because
PTS has no opinion about them: the identity strings a title block sets, the typeface **families and
their `w:altName` substitutes** (Word resolves a face by name and has no fallback chain), and
defaults for the Word templates' document properties. Only the fields a *practice* knows are set —
project name, client and container identifier stay blank, because a stale value where the reader
expects a blank is worse than the blank.

Nothing else. Sheet geometry, the type scale and the tone ladder are derived from ADOS root facts
and carry rule numbers; a brand that could move them could produce a non-conformant sheet while the
sheet still claimed conformance. An overlay touching anything else raises.

`ptspdf.token_overlay()` is a context manager, not a setter, because the module's tokens are global
and an overlay that outlived its build would brand the next one.

## The logo system

The mark is **generated**, not drawn. Proportions come from
`visual_identity.logo.construction` in modules — the same lattice the sheets
are set on — and the letterforms are real glyph outlines pulled from the
practice's own font binary with fontTools, so the wordmark *is* the typeface
rather than a `<text>` element that renders differently wherever the font is
missing. Change the module and the mark rebuilds; change the face and the
wordmark is re-set in it.

Seven variants: primary, secondary, monogram, symbol, compact, stacked,
reversed. The reversed lockup is constructed by inverting the palette and
re-drawing, never by string-replacing colours in a finished SVG — a
replacement that stops matching fails silently and ships a mark that is simply
not reversed.

## The consistency check

`brand/validation/consistency.py` audits a *generated package* against the
brand it claims to come from. `BrandValidator` says a brand is sound; this
says the files on disk actually derive from it — separable failures, and the
second only becomes checkable once assets exist.

```bash
python -m brand.cli audit <package-dir> --brand studio-om
```

It catches planted colours, undeclared font families, dangling custom
properties, layout dimensions off the lattice, assets with no inventory
record, missing logo variants, files off the naming pattern, and colours
declared twice.

Two deliberate scope decisions, both learned from false positives in the first
run: colour and font checks apply only to formats that *render* (a hex in a
JSON file is data), and the lattice rule distinguishes placement (`gap`,
`margin` — full sub-module) from internal clearance (`padding` — half), which
is the distinction ADOS itself makes.

## Tests

```bash
python -m pytest tests_brand -q      # 206 tests
```

Runs in CI alongside `tests_rules` and `construmind/tests`. No database, no storage, no API key: the
agent's deterministic path is the one CI exercises, which is also the one every deployment without a
key actually gets.

## Known limitations

- **No Next.js brand page.** The preview is server-rendered HTML at
  `GET /api/v2/brands/{id}/preview`. A page in `archstate-web/` is the natural next step; it was not
  built because `node_modules` is not installed in this environment and shipping an unverifiable
  `.tsx` would be worse than not shipping one.
- **Font files are not resolved from a brand.** A brand naming a family with no file in
  `docs/templates/pdf/fonts/` keeps the bundled face and gets a warning rather than a silent
  substitution.
- **`_detect_name` is a regex.** Fine for "We are called X"; it will miss most other phrasings, and
  the CLI takes `--name` for exactly that reason.
