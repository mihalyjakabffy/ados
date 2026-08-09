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
```

```python
from brand import Brand, BrandAgent

brand  = Brand.create(name="Studio Nord", primary_font="Inter")
report = brand.check()                  # structural · consistency · architectural
tokens = brand.resolve_tokens()         # 122 tokens, each with provenance
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
| `templates/` | Ten declarative template categories and two renderers |
| `preview/` | A self-contained HTML preview — the artefact a human approves against |
| `store/` | File-backed and SQL-backed repositories behind one protocol |
| `schemas/` | JSON Schema, generated from the models |
| `consumers.py` | Phase-5 interfaces: Archicad attributes, render parameters |
| `examples/studio_nord.py` | The worked example |

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

Sixteen closed namespaces (`brand/models/tokens.py`). A resolver emitting a name outside them raises,
which is what stops the vocabulary drifting into near-synonyms.

```
font.*     line_height.*  letter_spacing.*  color.*   space.*   grid.*
stroke.*   tone.*         radius.*          shadow.*  opacity.*
render.*   diagram.*      voice.*           asset.*   meta.*
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

`BT05` is the load-bearing one. It is built by `docs/templates/pdf/ptspdf.py` — the same code that
produces the verified PTS sheets — driven by a brand overlay. Change the brand's cut weight and the
plotted line changes.

## The PTS overlay

Six paths, whitelisted in `resolution/pts_bridge.py`:

```
line.tiers.W1  line.tiers.W2  line.tiers.W3
type.uppercase_tracking_percent
module.M  module.sub
```

Nothing else. Sheet geometry, the type scale and the tone ladder are derived from ADOS root facts
and carry rule numbers; a brand that could move them could produce a non-conformant sheet while the
sheet still claimed conformance. An overlay touching anything else raises.

`ptspdf.token_overlay()` is a context manager, not a setter, because the module's tokens are global
and an overlay that outlived its build would brand the next one.

## Tests

```bash
python -m pytest tests_brand -q      # 157 tests
```

Runs in CI alongside `tests_rules` and `construmind/tests`. No database, no storage, no API key: the
agent's deterministic path is the one CI exercises, which is also the one every deployment without a
key actually gets.

## Known limitations

- **No Next.js brand page.** The preview is server-rendered HTML at
  `GET /api/v2/brands/{id}/preview`. A page in `archstate-web/` is the natural next step; it was not
  built because `node_modules` is not installed in this environment and shipping an unverifiable
  `.tsx` would be worse than not shipping one.
- **Word templates are not yet brand-aware.** `ptsword.py` has the same overlay-shaped seam as
  `ptspdf.py` but has not been wired; the PDF path was done first because it is the one with a
  verifier behind it.
- **Font files are not resolved from a brand.** A brand naming a family with no file in
  `docs/templates/pdf/fonts/` keeps the bundled face and gets a warning rather than a silent
  substitution.
- **`_detect_name` is a regex.** Fine for "We are called X"; it will miss most other phrasings, and
  the CLI takes `--name` for exactly that reason.
