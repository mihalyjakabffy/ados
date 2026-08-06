# Volume 3 — Visual Language

**ADOS 1.0 · Volume 3 · Typography, grid, tone, composition.**

Volume 3 specifies the appearance of every mark that is not a drawn building element. Volume 4
specifies the drawn elements themselves. All values here derive from Volume 1; each rule cites
the derivation.

---

## 3.1 Visual encoding channels

### ADOS-3.1.010 — Channel inventory ⚠

**Purpose.** Establish the complete set of channels available for encoding meaning, so that a
channel is never used twice for unrelated distinctions and never left unused while a distinction
goes unencoded.

**Background.** Volume 1 §1.2 establishes that each channel supports a limited number of reliably
identifiable states, and §1.3 establishes that channels differ in survival through reproduction.

**Problem.** Practices encode meaning ad hoc: a distinction is expressed by whatever looked
available at the time. The result is channels overloaded with two meanings and readers unable to
decode either.

**Decision.** The following channels, and only these, may carry meaning in ADOS documentation.
Each row states the reliable state count under the adverse reference condition and the rank in
the robustness ordering of `ADOS-0.3.030`.

| Rank | Channel | States | Reserved for | Rule |
|---|---|---|---|---|
| 1 | **Position** | continuous | Geometry, zoning, fixed-position identity | `ADOS-3.3` |
| 2 | **Line weight** | 5 (3 semantic tiers) | Depth relative to the cut plane | `ADOS-4.1` |
| 3 | **Line type** | 4 | Visibility state and category | `ADOS-4.1.050` |
| 4 | **Tone** | 6 | Material class, phase, background rank | `ADOS-3.8` |
| 5 | **Symbol** | unbounded, ≤ 30 per set | Object class and reference | `ADOS-4.7`, `ADOS-4.9` |
| 6 | **Text size** | 5 | Hierarchy level | `ADOS-3.4.030` |
| 7 | **Text weight** | 2 | Emphasis within a level | `ADOS-3.4.040` |
| 8 | **Text case** | 2 | Register (labels vs prose) | `ADOS-3.4.060` |
| 9 | **Enclosure** | 3 | Reference markers, revision areas, grid bubbles | `ADOS-4.7` |
| 10 | **Colour** | — | Redundant only | `ADOS-3.10` |

**Implementation.** Each project's encoding table (`ADOS-3.1.050`) instantiates this inventory
with the actual states used.

**Exceptions.** None. A distinction that cannot be encoded within this inventory shall be encoded
in text.

**Validation.** `V-3.1.010`: every distinct visual state observed in the set maps to exactly one
row and one declared meaning; unmapped states = 0; channels with two declared meanings = 0.

**Common mistakes.** Using line type both for visibility (hidden/visible) and for category (fire
line, grid line) without reserving distinct patterns; using text size both for hierarchy and for
"importance".

**Automation notes.** The renderer's style dictionary is generated from the encoding table; an
undeclared style is a build error (`ADOS-7.6.020`).

### ADOS-3.1.020 — One channel, one meaning ⚠

**Decision.** Within a document set, a channel shall carry exactly one dimension of meaning. Two
distinctions shall not share a channel.

**Rationale (C).** Shared channels require conjunction search, which is serial and error-prone
(§1.2.5), and they make the encoding non-invertible: the reader cannot tell which meaning a state
carries without external context.

**Validation.** `V-3.1.020`: encoding table has exactly one `meaning_dimension` per channel.

### ADOS-3.1.030 — Channel assignment order

**Decision.** When assigning channels to distinctions, distinctions shall be ranked by the cost of
being missed and assigned to channels in robustness order (`ADOS-0.3.030`), strongest to weakest.

**Validation.** `V-3.1.030`: the encoding table's `criticality` column is non-increasing as
channel rank increases.

### ADOS-3.1.040 — Redundant encoding for critical distinctions

**Decision.** A distinction whose misreading has life-safety consequences shall be encoded in at
least two channels, at least one of which is rank ≤ 4.

**Validation.** `V-3.1.040`: every distinction with `criticality = life_safety` has ≥ 2 channels
assigned, with `min(rank) ≤ 4`.

### ADOS-3.1.050 — The encoding table ⚠

**Decision.** Every project shall carry an encoding table as a machine-readable artefact and as a
printed legend sheet (`ADOS-5.3`). Columns: channel, state, meaning, criticality, rule reference,
example graphic.

**Validation.** `V-3.1.050`: table exists, validates against schema, and covers every state
detected in the set by the style audit.

---

## 3.2 Sheet sizes

### ADOS-3.2.010 — Sheet size series ⚠

**Purpose.** Fix the physical substrate so that reduction, folding, filing and the √2 scale
invariance of §1.4.3 all hold.

**Background (I).** ISO 216 A-series sheets have the ratio 1:√2, so that halving the long side
produces the next size with the same aspect ratio. This is the property that makes the ADOS type
and line series scale-invariant.

**Decision.** Sheets shall be ISO 216 A-series, trimmed size:

| Size | mm | Typical use |
|---|---|---|
| A0 | 841 × 1189 | Site plans at large scale; rarely justified (see `ADOS-3.2.030`) |
| A1 | 594 × 841 | Default for general arrangement and detail sheets |
| A2 | 420 × 594 | Small projects; interior packages |
| A3 | 297 × 420 | Reduced sets, reports, schedules, details |
| A4 | 210 × 297 | Documents, schedules, correspondence, reports |

Orientation shall be landscape for drawing sheets and portrait for document sheets.

**Exceptions.**
1. Elongated site sections may use an A-series size with a defined extension (`A1 × 1.5`), which
   shall fold to A4 (`ADOS-3.2.070`).

**Validation.** `V-3.2.010`: sheet dimensions match a table row within ±0.5 mm.

**Common mistakes.** ANSI/Arch sizes mixed into an A-series set (breaks the √2 relationship and
the fold module); "custom" sheet sizes for a single drawing.

### ADOS-3.2.020 — Default drawing sheet size

**Decision.** The default drawing sheet size shall be A1. A project shall declare a single sheet
size for its drawing set (`ADOS-2.11.020`).

**Rationale (R, C).** A1 is the largest size that (a) fits on a standard site table and a normal
desk, (b) folds to A4 in a repeatable pattern, (c) can be handled by one person in wind, and (d)
reduces to A3 at exactly ×½. A0 fails (a) and (c); A2 usually fails the density floor
(`ADOS-3.7.010`) for building-scale drawings.

**Validation.** `V-3.2.020`: distinct drawing sheet sizes in the set ≤ 2 (`ADOS-2.11.020`).

### ADOS-3.2.030 — Justification for A0

**Decision.** A0 shall be used only where a required view at a required scale does not fit on A1
and cannot be split without severing a continuous condition (for example a single-span structural
grid). The justification shall be recorded.

**Rationale (R).** A0 sheets cannot be read on a site table, are difficult to fold, and are
frequently reduced to A1 or A3 for use — at which point the derivation of `ADOS-3.2.040` applies
and the sheet usually fails.

### ADOS-3.2.040 — Smallest nominated issue size ⚠

**Purpose.** Prevent the most common systemic documentation failure: sets designed at A1 and
consumed at A3.

**Background.** §1.3.5. Reduction from A1 to A3 halves every printed dimension.

**Problem.** Text at the 2.5 mm minimum becomes 1.25 mm; lines at 0.18 mm become 0.09 mm. Both are
below their floors. The reader receives an unreadable document with no indication that it was
never intended to be reduced.

**Decision.** Every set shall declare a **smallest nominated issue size** in the title block. All
minimum-dimension rules in Volumes 3 and 4 apply at that size. Where the nominated size is smaller
than the authored size, the minima at the authored size shall be scaled by the reduction factor.

**Implementation.** Two conforming configurations:

| Configuration | Nominated size | Min cap height at A1 | Min line width at A1 | Annotation capacity |
|---|---|---|---|---|
| **A1-only** | A1 | 2.5 mm | 0.18 mm | 100 % (reference) |
| **A1 + A3 dual** | A3 | 5.0 mm | 0.35 mm | ≈ 60 % |

Under A1-only, A3 prints shall carry the watermark
`REDUCED COPY — DO NOT SCALE — REFERENCE ONLY` applied at print time.

**Exceptions.** None.

**Validation.** `V-3.2.040`: the nominated size field is populated; the rendered set at the
nominated size passes all `ADOS-8.2` readability metrics.

**Common mistakes.** Declaring dual issue and then authoring at A1 minima; issuing an A3 PDF of an
A1-only set without the watermark.

**Automation notes.** The generator takes nominated size as a build parameter and scales all
minima; the QA gate runs at the nominated size.

### ADOS-3.2.050 — Document sheet size

**Decision.** Prose documents (specifications, reports, minutes, schedules in tabular form) shall
be A4 portrait. Schedules too wide for A4 shall be A3 landscape, folded to A4.

**Rationale (R).** A4 is the universal filing, printing and scanning size. Deviating costs the
reader a folding or filing operation on every use.

### ADOS-3.2.060 — Imperial output

**Decision.** Where a project's jurisdiction requires imperial sheet sizes, the ARCH series shall
be used (ARCH D 610 × 914 mm as the A1 equivalent), the smallest nominated issue size rule applies
unchanged, and the type and line series shall be retained in millimetres. Mixing series within a
set is prohibited.

**Rationale.** The ARCH series ratio is 2:3, not 1:√2, so the scale-invariance property of §1.4.3
is lost. Retaining the metric type and line series preserves the semantic tiers even though the
reduction mapping no longer aligns.

### ADOS-3.2.070 — Folding

**Decision.** Drawing sheets shall fold to A4 (210 × 297) with the title block visible on the top
face and the sheet number legible without unfolding. The fold pattern shall be identical across
the set.

**Rationale (R).** Filed sets are folded. If the fold obscures the title block, every retrieval
requires unfolding.

**Implementation.** The fold-safe zone is defined in `ADOS-3.3.100`: no critical content within
5 mm of a fold line, because folds crack, smudge and are photocopied as dark bands.

**Validation.** `V-3.2.070`: fold line positions computed from sheet size; no text, dimension or
reference marker intersects a fold-safe zone.

---

## 3.3 Sheet structure: frame, zones and grid

### ADOS-3.3.010 — Fixed zoning ⚠

**Purpose.** Guarantee that every sheet in a set presents its fixed elements in identical
positions, so that the reader's learned template holds (§1.2.6).

**Background.** Orientation is performed by saccade to remembered positions. If positions vary,
orientation reverts to search, which is 3–10× slower.

**Problem.** Templates copied and adjusted per project, or per sheet, place the north point, key
plan and scale in different places, and the reader must find them each time.

**Decision.** Every sheet shall use the zoning template for its size. Zone positions shall be
identical on every sheet of the set to within 0 mm.

**Implementation — large format template (A0–A2), landscape:**

```
┌──────────────────────────────────────────────────────────────┬────────────┐
│ ← 20 mm binding margin                     10 mm margin →    │            │
│  ┌────────────────────────────────────────────────────────┐  │            │
│  │ Z-BANNER   status / watermark band (h = 10 mm)          │  │  Z-KEY     │
│  ├────────────────────────────────────────────────────────┤  │  key plan  │
│  │                                                        │  │  (60×60)   │
│  │                                                        │  ├────────────┤
│  │                  Z-DRAW                                │  │            │
│  │                  drawing area                          │  │  Z-NOTES   │
│  │                  (views, at grid positions)            │  │  notes,    │
│  │                                                        │  │  legends,  │
│  │                                                        │  │  scope,    │
│  │                                                        │  │  read-with │
│  │                                                        │  │            │
│  │                                                        │  ├────────────┤
│  │                                                        │  │  Z-REV     │
│  │                                                        │  │  revision  │
│  │                                                        │  │  register  │
│  ├────────────────────────────────────────────────────────┤  ├────────────┤
│  │ Z-GRIDREF  frame zone references (A B C … / 1 2 3 …)   │  │  Z-TITLE   │
│  └────────────────────────────────────────────────────────┘  │  180 × 90  │
└──────────────────────────────────────────────────────────────┴────────────┘
                                                                ← 180 mm →
```

Zone dimensions (printed, at authored size):

| Zone | Role | Width | Height | Rule |
|---|---|---|---|---|
| `Z-DRAW` | Views | sheet width − 20 − 10 − 180 − 10 | sheet height − 20 − 10 − 10 | `ADOS-3.3.030` |
| `Z-TITLE` | Title block | 180 | 90 | `ADOS-3.9` |
| `Z-REV` | Revision register | 180 | 60 min, grows upward | `ADOS-2.6.030` |
| `Z-NOTES` | Notes, legends, scope | 180 (2 sub-columns of 85, 10 gutter) | remainder | `ADOS-3.3.070` |
| `Z-KEY` | Key plan | 180 | 60 min | `ADOS-2.4.060` |
| `Z-BANNER` | Status banner / watermark | drawing area width | 10 | `ADOS-3.9.060` |
| `Z-GRIDREF` | Frame zone reference marks | drawing area width | 5 | `ADOS-3.3.050` |

**Implementation — small format template (A3–A4), landscape or portrait:** the right-hand band is
replaced by a bottom band of height 90 mm containing `Z-TITLE` (180 × 60) at the right and
`Z-NOTES` (remaining width) at the left; `Z-KEY` sits above `Z-TITLE` at 40 × 40 mm minimum.

**Exceptions.**
1. Cover sheets (`ADOS-5.1`) use the cover template, which retains `Z-TITLE` position only.

**Validation.** `V-3.3.010`: zone origin coordinates identical across all sheets of a size (exact
equality); every fixed element lies wholly within its zone.

**Common mistakes.** A "wide" title block on one sheet to fit a long project name; moving the key
plan when a view is large.

**Automation notes.** Zones are defined once in `machine/ados-tokens.json` under
`ados.sheet.zones`; the generator instantiates from the token file and never per sheet.

### ADOS-3.3.020 — Margins ⚠

**Decision.** Margins from trimmed edge to frame shall be: **binding edge (left) 20 mm; all other
edges 10 mm**.

**Rationale.**
- *Binding 20 mm (R, I):* filing punch holes and binding strips consume 12–15 mm; 20 mm leaves a
  safe margin and matches ISO 5457.
- *Other edges 10 mm (P, R):* large-format printers have a non-printable margin of 3–5 mm; trimming
  tolerance on a plotter is ±2 mm; a 10 mm margin absorbs both with margin and prevents content
  loss on any device.

**Validation.** `V-3.3.020`: no mark outside the frame; frame offsets equal 20/10/10/10 ±0.5 mm.

### ADOS-3.3.030 — Base module and grid ⚠

**Purpose.** Provide a single spatial quantum to which all placement snaps, making layout
deterministic and alignment automatic.

**Background.** Alignment is a strong grouping cue and a strong signal of systematic production.
Manual alignment is unreliable; a module makes it free.

**Derivation (A).** The module shall satisfy three constraints:

1. It shall divide the baseline pitch of body text, so that text and graphics share a rhythm.
   Baseline pitch = 5 mm (`ADOS-3.4.070`).
2. It shall map to a round real-world dimension at the primary drawing scales:
   at 1:100, 10 mm = 1.000 m; at 1:50, 10 mm = 0.500 m; at 1:200, 10 mm = 2.000 m.
3. It shall be large enough that snapping is visible (≥ 2× the minimum discriminable offset,
   ~1 mm at 500 mm viewing) and small enough not to distort placement (≤ 2 % of sheet width).

```
M = 10 mm      (satisfies 1: 2 × 5 mm; satisfies 2; satisfies 3: 10 ≥ 2 and 10 ≤ 0.02 × 841)
sub-module m = 5 mm
```

**Decision.** The sheet grid module shall be **10 mm**, with a 5 mm sub-module. All zone
boundaries, view origins, annotation block origins, table row heights and text baselines shall
snap to the sub-module.

**Exceptions.**
1. Drawn geometry inside a view is positioned by the model, not by the grid.
2. Dimension and leader endpoints are positioned by their anchors.

**Validation.** `V-3.3.030`: for every placeable object origin, `x mod 5 = 0` and `y mod 5 = 0`
(within ±0.1 mm).

**Automation notes.** The solver's placement domain is the sub-module lattice; this makes
placement a discrete problem with a deterministic tie-break (`ADOS-7.5.050`).

### ADOS-3.3.040 — Drawing area column structure

**Decision.** The drawing area shall be treated as a column grid whose column count is chosen so
that column width ≥ 60 mm and the residual is ≤ 1 sub-module. For A1 with the standard template
(drawing area 631 × 574 mm), the conforming structures are 6 columns of 100 mm with 10 mm gutters
(residual 1 mm) or 4 columns of 154 mm with 10 mm gutters (residual 1 mm).

**Rationale.** Views placed on a column grid align automatically, and view widths become
predictable across the set, which supports the template effect.

**Validation.** `V-3.3.040`: every view's bounding box left and right edges coincide with column
boundaries within ±1 mm.

### ADOS-3.3.050 — Frame zone references

**Decision.** The frame shall carry zone reference marks: letters along the vertical edges and
numbers along the horizontal edges, at 50 mm intervals, at 3.5 mm cap height, with the origin at
the lower-left of the frame.

**Rationale (R, I).** Zone references allow a location on a sheet to be communicated verbally and
in writing ("the door head detail at C4") without a grid line nearby. This is used constantly in
RFIs and site queries, and its absence forces verbose location descriptions. ISO 5457 defines the
convention; ADOS fixes the interval at 50 mm so that zone count is manageable
(A1: 12 × 11 zones).

**Validation.** `V-3.3.050`: zone marks present on all four edges; interval 50 mm ±0.5; letters
skip `I` and `O`.

### ADOS-3.3.060 — Key plan zone

**Decision.** `Z-KEY` shall contain the key plan defined in `ADOS-2.4.060`, at a printed size of
at least 60 × 60 mm on large formats and 40 × 40 mm on small formats, with north up and identical
geometry across the set.

**Validation.** `V-3.3.060`: key plan bounding box ≥ minimum; geometry hash identical set-wide;
north vector identical to the drawing-area north vector.

### ADOS-3.3.070 — Notes zone content and order ⚠

**Decision.** `Z-NOTES` shall contain the following blocks, in this order, top to bottom, each
with a 3.5 mm heading:

1. **Scope of this sheet** — mandatory (`ADOS-0.3.090`), ≤ 40 words.
2. **Read with** — the `read_with` containers (`ADOS-2.8.020`).
3. **Sheet-specific notes** — numbered `01`, `02`…, referenced from the drawing by tag.
4. **Legend** — only symbols and hatches used on this sheet (`ADOS-4.9.020`).
5. **Standard notes reference** — a reference to the general notes sheet; the notes themselves
   shall not be repeated.

**Rationale.** Fixed order means the reader can jump to the block they need without reading the
column. Scope first because it determines whether the reader is on the right sheet at all.

**Exceptions.** Blocks 3 and 4 are omitted when empty; blocks 1, 2 and 5 are never omitted.

**Validation.** `V-3.3.070`: blocks present in order; block 1 non-empty on every sheet; legend
contains exactly the symbol set used on the sheet (no more, no fewer).

**Common mistakes.** Repeating the practice's full standard notes on every sheet (consumes
80–120 mm of column for content nobody reads twice); a legend inherited from the template listing
symbols not present.

### ADOS-3.3.080 — Revision zone

**Decision.** `Z-REV` shall contain the revision register (`ADOS-2.6.030`) with the most recent
revision in the top row, growing upward as revisions are added, with a minimum of 6 visible rows.

**Rationale.** Most recent first matches the reader's most frequent question. Growing upward keeps
the newest row adjacent to the title block, where the current revision is also stated.

### ADOS-3.3.090 — Prohibited content in fixed zones

**Decision.** Drawing content shall not enter `Z-TITLE`, `Z-REV`, `Z-KEY`, `Z-BANNER` or the
margins. Notes shall not enter `Z-DRAW` except as sheet-note tags anchored to drawing content.

**Validation.** `V-3.3.090`: geometric intersection between drawing content and fixed zones = ∅.

### ADOS-3.3.100 — Fold-safe zones

**Decision.** No text, dimension text, reference marker or revision tag shall lie within 5 mm of a
fold line of the declared fold pattern.

**Rationale (P, R).** Folds crack toner, collect dirt, and photocopy as dark lines. Content on a
fold is lost after a few handlings — exactly the content on the sheets that are handled most.

**Validation.** `V-3.3.100`: fold lines computed from sheet size and pattern; intersection with
text bounding boxes = ∅.

---

## 3.4 Typography

### ADOS-3.4.010 — Minimum text size ⚠

**Purpose.** Guarantee legibility under the adverse reference condition.

**Background.** §1.2.1: 17 arcmin at 500 mm ⇒ 2.5 mm cap height.

**Problem.** Text is reduced to fit content, which shifts the failure from the author (who would
have had to split the sheet) to the reader (who cannot read it and is not warned).

**Decision.** At the smallest nominated issue size:

| Text class | Minimum cap height |
|---|---|
| Any text a user must read to act (dimensions, tags, notes, titles, schedules) | **2.5 mm** |
| Secondary annotation on sheets of A1 or larger, read at close range | 1.8 mm |
| Any text at all | 1.8 mm absolute floor |

**Exceptions.**
1. Screen-only deliverables (`ADOS-0.3.060` Ex. 1) may use 1.8 mm.
2. Statutory stamps and signatures reproduced as supplied.

**Validation.** `V-3.4.010`: minimum cap height across all text objects, measured at the nominated
size, ≥ 2.5 mm (or 1.8 mm for objects tagged `secondary`). Count of violations = 0.

**Common mistakes.** Shrinking dimension text to fit between witness lines — the correct action is
to place the dimension outside or restructure the chain (`ADOS-4.5.050`); leaving imported
consultant content at its original scale.

**Automation notes.** The generator shall never scale text to fit; overflow is a solver failure
that escalates to a layout change (`ADOS-7.5.070`).

### ADOS-3.4.020 — Typeface selection ⚠

**Purpose.** Ensure characters are unambiguous under degradation and that documents render
identically everywhere.

**Background.** Technical documentation is dominated by strings whose content cannot be predicted
from context: `D-1108`, `FD30S`, `A3.104`, `+12.450`. Contextual recovery of a misread character
is impossible, so glyph disambiguation matters far more than in prose.

**Problem.** Typefaces chosen for appearance frequently confuse `1/l/I`, `0/O`, `5/S`, `2/Z`,
`6/8`, and use proportional figures that destroy column alignment in schedules.

**Decision.** A project shall use at most two typefaces: one **drawing face** and one **document
face**. Each shall satisfy its requirement set below. The specific families are a practice overlay
choice (`ADOS-2.7.030`).

*Drawing face — mandatory properties:*

| # | Requirement | Reason |
|---|---|---|
| 1 | Grotesque or humanist sans, upright | Highest stroke uniformity survives reproduction |
| 2 | Unambiguous `1`, `l`, `I` (distinct forms) | Sheet and mark identifiers |
| 3 | Slashed or dotted zero, or clearly ovoid `0` vs circular `O` | Level and dimension values |
| 4 | Distinct `5`/`S`, `2`/`Z`, `6`/`8`/`9` | Identifier reading |
| 5 | Tabular (fixed-width) lining figures | Schedule and dimension alignment |
| 6 | x-height ≥ 0.52 em | Legibility at small sizes |
| 7 | Open apertures (`c`, `e`, `s`, `a`) | Resists fill-in under ink spread |
| 8 | Stroke contrast ≤ 1.3 : 1 | Thin strokes survive erosion (§1.3.2) |
| 9 | ≥ 2 weights (regular, medium/bold) | Emphasis channel (`ADOS-3.4.040`) |
| 10 | Full Latin coverage plus the project's required scripts | Multilingual sets |
| 11 | Embeddable licence, and available as a PDF-embeddable outline font | Fixed rendering |

*Document face — mandatory properties:* items 2–5 and 10–11 above, plus a true italic, small
capitals, and both lining and text figures.

**Rationale for permitting a second face.** Prose documents are read continuously, use emphasis
and defined terms, and require italics and small capitals — features absent from most technical
drawing faces. The second face is therefore functional, not stylistic. A single face satisfying
both requirement sets is permitted and preferred.

**Exceptions.**
1. Monospaced text is permitted for code, file paths and machine identifiers, as a third face,
   used only for those classes.

**Validation.** `V-3.4.020`: distinct embedded font families in the set ≤ 2 (≤ 3 with monospace);
each embedded; glyph disambiguation test passes (render the confusable set at 2.5 mm, degrade,
compare glyph bounding-box hashes).

**Common mistakes.** Relying on a system font that is substituted on another machine — substitution
changes metrics and can break the density and collision metrics silently.

### ADOS-3.4.030 — Type scale and role assignment ⚠

**Decision.** Text shall use only the following heights (printed cap height at the nominated size)
with the assigned roles:

| Step | Cap height | Role | Notes |
|---|---|---|---|
| t1 | 1.8 mm | Tertiary annotation (large sheets only) | Grid bubble subscripts, minor tags |
| t2 | **2.5 mm** | Body: notes, dimension text, tags, schedule cells | Default for everything |
| t3 | 3.5 mm | View titles, note-block headings, schedule column headers | |
| t4 | 5 mm | Sheet title, document section headings | |
| t5 | 7 mm | Sheet number (short form), status banner | |
| t6 | 10 mm | Cover sheet document title, watermark | |
| t7 | 14 mm | Cover sheet project title | Cover only |
| t8 | 20 mm | Reserved | Presentation documents only |

**Rationale.** §1.4: the √2 series; at most five steps on a sheet (`ADOS-3.6.020`) because absolute
size identification saturates (§1.2.3, ROOT 2).

**Validation.** `V-3.4.030`: every text object's cap height matches a step within ±2 %; distinct
steps per sheet ≤ 5.

### ADOS-3.4.040 — Weight

**Decision.** Two weights only: regular and medium/bold. Bold shall be used for exactly one
purpose per document class, declared in the encoding table — normally the current-level heading or
the schedule header row. Bold shall not be used for arbitrary emphasis within body text.

**Rationale.** Weight is a strong pre-attentive channel with only two reliable states in text
(§1.2.5); spending it on ad-hoc emphasis destroys its use for structure.

**Validation.** `V-3.4.040`: distinct weights ≤ 2; bold usage matches its declared role.

### ADOS-3.4.050 — Prohibited type treatments

**Decision.** The following shall not be used in technical documentation: italic for emphasis on
drawings; underline; letter-spacing changes for emphasis; outlined, shadowed or filled text;
condensed or expanded variants applied by horizontal scaling; text on a curve except where the
annotated element is curved; text rotated to any angle other than 0° or 90° counter-clockwise.

**Rationale.** Underline collides with descenders and with drawing lines; artificial condensing
changes stroke weight non-uniformly, breaking the reproduction floor on the thin axis; free
rotation forces head-tilt and breaks automated text extraction.

**Validation.** `V-3.4.050`: text transformation matrix is a pure translation or a 90° rotation;
no synthetic bold/italic/condense flags in the PDF.

### ADOS-3.4.060 — Case

**Decision.** Upper case shall be used for: sheet titles, view titles, level markers, grid labels,
type marks and status banners. Sentence case shall be used for: notes, schedule cell content,
descriptions and all prose. Full upper case shall not be used for text longer than 40 characters.

**Rationale (V, C).** Upper case removes ascender/descender word-shape cues and slows continuous
reading by roughly 10–15 %; for short labels this cost is negligible and the gain in uniform
height and unambiguous baseline alignment is real. Above ~40 characters the reading cost dominates.

**Validation.** `V-3.4.060`: no upper-case run > 40 characters outside the permitted label classes.

### ADOS-3.4.070 — Line spacing and the baseline grid ⚠

**Derivation (A, V).** Line pitch for technical text: 1.35–1.45 em; with cap height ≈ 0.70 em,
pitch ≈ 1.93–2.07 × cap height. At the 2.5 mm body size:

```
pitch = 2.0 × 2.5 mm = 5.0 mm = the sub-module (ADOS-3.3.030)
```

**Decision.** Body text line pitch shall be 5.0 mm and all text baselines shall lie on the 5 mm
sub-module grid. Larger text steps use pitch = 2 × cap height rounded up to the next sub-module.

| Cap height | Pitch |
|---|---|
| 1.8 mm | 5.0 mm |
| 2.5 mm | 5.0 mm |
| 3.5 mm | 10.0 mm |
| 5.0 mm | 10.0 mm |
| 7.0 mm | 15.0 mm |
| 10.0 mm | 20.0 mm |

**Validation.** `V-3.4.070`: baseline y-coordinates satisfy `y mod 5 = 0` ±0.1 mm; measured pitch
matches the table.

### ADOS-3.4.080 — Text clear zone and masking ⚠

**Decision.** Every text object shall be surrounded by a clear zone of `max(0.5 × cap height,
1.0 mm)` containing no other mark. Where text overlies drawing content, an opaque mask of the
clear-zone extent shall be applied.

**Rationale.** §1.3.4 (crowding and merging).

**Exceptions.** None. Text placed over hatch without a mask is a Severity 1 defect.

**Validation.** `V-3.4.080`: for every text bounding box expanded by the clear zone, the count of
intersecting non-masked marks = 0.

**Automation notes.** Masking is applied by the renderer as a white-filled rectangle behind the
glyph run, drawn in the same z-order group; masks shall not obscure dimension lines they annotate
(the dimension line is broken instead, `ADOS-4.5.040`).

### ADOS-3.4.090 — Measure (line length)

**Derivation (V, C).** Continuous reading is most reliable at 45–75 characters per line. Average
character advance for a technical sans at cap height *c* is ≈ 0.72 × *c*. For *c* = 2.5 mm:

```
advance ≈ 1.8 mm
45 chars → 81 mm ;  75 chars → 135 mm
```

**Decision.** Prose measure shall be 45–75 characters. The notes sub-column width of 85 mm
(`ADOS-3.3.010`) yields ≈ 47 characters and conforms. Prose documents (A4) shall use a text column
of 100–135 mm.

**Validation.** `V-3.4.090`: mean characters per line within [45, 75] for every prose block.

### ADOS-3.4.100 — Numerals and units

**Decision.** Numerals shall be tabular lining figures. Decimal separator shall be declared once
per project and used consistently. Thousands separators shall not be used in dimensions; a thin
space may be used in schedules and quantities. Values shall be right-aligned in numeric columns
and aligned on the decimal separator.

**Rationale.** Column scanning of numbers is a magnitude comparison task; right/decimal alignment
converts it into a position comparison, which is pre-attentive.

**Validation.** `V-3.4.100`: numeric columns pass the decimal alignment check (x-coordinate of
separator constant within ±0.2 mm).

---

## 3.5 White space and rhythm

### ADOS-3.5.010 — White space is an encoding channel

**Decision.** Separation shall be used as the primary grouping cue. Enclosure (boxes, rules) shall
be used only where separation is insufficient because space is unavailable.

**Rationale (V).** Proximity is the strongest grouping cue in vision. Boxes add ink, add line
weights competing with the drawing hierarchy, and are frequently misread as enclosure semantics
(`ADOS-3.1.010` rank 9).

**Validation.** `V-3.5.010`: count of decorative rules and boxes not declared in the encoding
table = 0.

### ADOS-3.5.020 — The 2:1 grouping ratio ⚠

**Derivation (V).** §1.7.2: unambiguous grouping requires the between-group gap to exceed the
largest within-group gap by the absolute-identification margin, factor 2.

**Decision.**

```
gap_between_groups ≥ 2 × gap_within_group
```

applied at every level: between views, between annotation clusters, between note blocks, between
schedule column groups, between paragraphs.

**Implementation.** With the 5 mm sub-module: within-group 5 mm, between-group 10 mm; or
within-group 10 mm, between-group 20 mm.

**Validation.** `V-3.5.020`: for every declared group, `min(between) / max(within) ≥ 2.0`.

**Common mistakes.** Equal spacing everywhere (no grouping signal at all); decorative equal gaps
between views that belong to different subjects.

### ADOS-3.5.030 — Rhythm

**Decision.** Repeating elements (note lines, schedule rows, legend entries, revision rows) shall
have constant pitch on the sub-module grid. Variable row heights are permitted only where content
requires wrapping, and then only in whole sub-module increments.

**Rationale (V).** Constant pitch allows the eye to track across a row without re-fixating, which
is the dominant cost in table reading; it also allows row position to be computed rather than
searched.

**Validation.** `V-3.5.030`: row pitch is constant or an integer multiple of the base pitch;
non-conforming rows = 0.

### ADOS-3.5.040 — Margins around views

**Decision.** Every view shall have a clear margin of ≥ 10 mm from the drawing area boundary and
≥ 20 mm from any other view's bounding box (including its annotation).

**Rationale.** Views are the top-level groups on a sheet; `ADOS-3.5.020` therefore requires the
between-view gap to be twice the largest within-view gap, and 10 mm is the largest permitted
within-view annotation gap.

**Validation.** `V-3.5.040`: pairwise view bounding-box separation ≥ 20 mm; boundary clearance
≥ 10 mm.

---

## 3.6 Hierarchy

### ADOS-3.6.010 — Hierarchy is a function of the reader's sequence

**Decision.** The visual hierarchy of a sheet shall follow the reader's required sequence:
(1) sheet identity, (2) view identity, (3) content, (4) supporting annotation. Emphasis shall be
allocated in that order and shall not be reallocated for graphic effect.

**Validation.** `V-3.6.010`: measured salience ordering (`ADOS-8.3.040`) matches the required
sequence.

### ADOS-3.6.020 — Three levels per sheet ⚠

**Decision.** At most three levels of visual hierarchy shall be expressed within any one region,
and at most five distinct text sizes shall appear on any one sheet.

**Rationale (C).** ROOT 2: absolute identification saturates at 4–6 states; below that, the reader
must compare rather than recognise, which requires the states to be simultaneously visible.

**Validation.** `V-3.6.020`: distinct text steps per sheet ≤ 5; distinct hierarchy levels per
region ≤ 3.

### ADOS-3.6.030 — One channel per hierarchy step

**Decision.** A hierarchy step shall be expressed by a change in exactly one channel (size, or
weight, or position), not by simultaneous changes in several.

**Rationale.** Simultaneous changes waste channel capacity: three channels used redundantly for
one distinction leave nothing for the next distinction. They also produce visually loud documents
where each level shouts.

**Exceptions.**
1. Critical distinctions under `ADOS-3.1.040` (redundant encoding required).

**Validation.** `V-3.6.030`: for each adjacent hierarchy pair, the number of differing channels
= 1 (or ≥ 2 where criticality = life_safety).

### ADOS-3.6.040 — Emphasis budget

**Decision.** The total area of emphasised content (bold text, tone `T4`/`T5` fills, heaviest line
weight, enclosure) shall not exceed 10 % of the drawing area.

**Rationale (V).** Emphasis works by contrast against a majority of unemphasised content. Above
roughly 10 % the emphasised set becomes the field rather than the figure and the effect inverts.

**Validation.** `V-3.6.040`: emphasised area / drawing area ≤ 0.10.

---

## 3.7 Information density

### ADOS-3.7.010 — Fill ratio ⚠

**Decision.** The proportion of the drawing area occupied by the union of view bounding boxes
shall satisfy `0.40 ≤ fill ≤ 0.85`.

**Rationale.** §1.7.1.

**Exceptions.**
1. The first and last sheets of a series may fall below 0.40 where the series content does not
   divide evenly; this shall be recorded once per series, not per sheet.

**Validation.** `V-3.7.010`: computed fill ratio within bounds.

### ADOS-3.7.020 — Local ink coverage ⚠

**Decision.** Mean ink coverage within any 20 × 20 mm window of the drawing area shall not exceed
0.25, excluding declared solid fills and poché.

**Rationale.** §1.3.3: above ~25 % coverage, strokes merge after two reproduction generations.

**Validation.** `V-3.7.020`: sliding-window coverage analysis of the rendered greyscale page;
maximum window coverage ≤ 0.25.

### ADOS-3.7.030 — Annotation object density ⚠

**Decision.** The count of annotation objects (text, dimension, tag, leader, symbol) within any
search region shall not exceed 50. A search region is a view, or a 150 × 150 mm area where a view
is larger.

**Rationale.** §1.2.4.

**Validation.** `V-3.7.030`: max annotation count per region ≤ 50.

### ADOS-3.7.040 — Density resolution order ⚠

**Decision.** When a density ceiling is exceeded, the following remedies shall be applied in
order; the first that resolves the breach shall be used:

1. Move content to its correct content level (`ADOS-2.3.010`).
2. Remove content that duplicates an authoritative carrier (`ADOS-2.2.010`).
3. Split the view (by area, by system, or by information class).
4. Split the sheet.
5. Change the sheet size (requires a set-level decision, `ADOS-2.11.020`).

Reducing text size, reducing line weight, reducing spacing, or removing required content are not
remedies and shall not be used.

**Validation.** `V-3.7.040`: no sheet exceeds a ceiling; where a remedy was applied, the record
states which.

### ADOS-3.7.050 — Minimum content

**Decision.** A sheet whose fill ratio is below 0.40 and which is not covered by
`ADOS-3.7.010` Ex. 1 shall be merged with another sheet.

**Rationale.** §1.7.1: cross-sheet navigation costs more than intra-sheet search; an
under-filled sheet imposes that cost for no benefit.

---

## 3.8 Tone and contrast

### ADOS-3.8.010 — The tone ladder ⚠

**Decision.** Only the six tones of the ADOS ladder shall be used:

| Token | Target L* | Nominal coverage | Reserved meaning |
|---|---|---|---|
| `T0` | 100 | 0 % | Void / paper / not applicable |
| `T1` | 82 | 12 % | Background information, existing to remain, out-of-scope context |
| `T2` | 64 | 26 % | Secondary material or zone fill |
| `T3` | 46 | 42 % | Primary material or zone fill |
| `T4` | 28 | 60 % | Emphasis fill, key plan current area |
| `T5` | 10 | 88 % | Poché of cut solid material at small scales |

**Rationale.** §1.2.2: ΔL* = 18 spacing over the reproducible range gives exactly six reliable
states.

**Exceptions.** None. Additional tones reduce the reliability of the whole ladder.

**Validation.** `V-3.8.010`: every fill's measured L* is within ±4 of a ladder value; distinct
fills outside the ladder = 0.

**Automation notes.** Tones are emitted as device grey values computed from the target L* through
the declared output transfer curve, not as nominal percentages, because printer dot gain shifts
nominal coverage by 10–20 % (`ADOS-6.11.050`).

### ADOS-3.8.020 — Maximum tones per sheet

**Decision.** At most four tones shall appear on one sheet, including `T0`.

**Rationale.** Absolute identification (ROOT 2). Six tones exist so that different document
classes can use different subsets; a single sheet requiring five or six tones has exceeded its
encoding budget and shall be split.

**Validation.** `V-3.8.020`: distinct tones per sheet ≤ 4.

### ADOS-3.8.030 — Meaning-critical tone pairs

**Decision.** Two tones carrying distinctions whose confusion has cost shall differ by at least
two ladder steps (ΔL* ≥ 36).

**Validation.** `V-3.8.030`: for every declared critical tone pair, ladder index difference ≥ 2.

### ADOS-3.8.040 — Text on tone ⚠

**Decision.** Text shall be placed only on `T0` or `T1`. Where text must overlie a darker tone, a
`T0` mask shall be applied (`ADOS-3.4.080`). Reversed text (light on dark) shall not be used in
technical documentation.

**Rationale (P, V).** Reversed text fills in under ink spread (the counters close first) and
becomes illegible after one reproduction generation, and it cannot be marked up on site with a
pen.

**Validation.** `V-3.8.040`: for every text object, background L* ≥ 82; reversed text count = 0.

### ADOS-3.8.050 — Background information tone

**Decision.** Context information that is present for orientation but is not the subject of the
sheet (adjacent buildings, other disciplines' content, existing fabric on a proposal drawing)
shall be rendered at `T1` with line weight reduced to the thinnest tier.

**Rationale.** Two channels (tone and weight) used redundantly to establish figure/ground is a
permitted redundancy: figure/ground failure is a high-cost misreading (the reader acts on
background information).

**Validation.** `V-3.8.050`: content tagged `background` uses tone `T1` and weight tier 1
exclusively.

---

## 3.9 The title block

### ADOS-3.9.010 — Purpose and position ⚠

**Decision.** The title block shall occupy `Z-TITLE`, 180 × 90 mm, at the lower-right of the
frame, on every sheet, in an identical position.

**Rationale (I, R).** ISO 7200 fixes the data field width at 180 mm; the lower-right position is
exposed by the standard A4 fold and by rolling, and is the position readers have learned.

### ADOS-3.9.020 — Mandatory fields ⚠

**Decision.** The title block shall contain the following fields, all populated. Empty mandatory
fields are a Severity 1 defect.

| # | Field | Source | Min cap height |
|---|---|---|---|
| 1 | Project name and code | Project | 2.5 |
| 2 | Client | Project | 2.5 |
| 3 | Sheet title | Container | 5.0 |
| 4 | Sheet number, short form | Container | 7.0 |
| 5 | Container identifier, full form | Container | 2.5 |
| 6 | Scale(s), stated per view or `AS SHOWN` with per-view scales | View | 3.5 |
| 7 | Sheet size and smallest nominated issue size | Set | 2.5 |
| 8 | Status code and name | Container | 5.0 |
| 9 | Revision code | Container | 5.0 |
| 10 | Date of issue | Issue | 2.5 |
| 11 | Author / drawn by | Container | 2.5 |
| 12 | Checked by | Container | 2.5 |
| 13 | Approved by | Container | 2.5 |
| 14 | Originator name and contact | Set | 2.5 |
| 15 | North point (plans only) or projection statement | View | — |
| 16 | Standards conformance claim | Set | 1.8 |
| 17 | Do-not-scale statement | Fixed | 1.8 |
| 18 | Copyright / confidentiality statement | Practice | 1.8 |

**Validation.** `V-3.9.020`: all fields present and non-empty; field positions identical set-wide;
cap heights ≥ minima.

**Common mistakes.** `Scale: 1:100` in the title block while the sheet carries views at three
scales — the field then states a falsehood; `Checked by` populated with the author's initials.

### ADOS-3.9.030 — Field ordering

**Decision.** Fields shall be ordered by frequency of use, most frequent nearest the sheet corner:
sheet number and revision at the outer corner, then status, then title, then project, then the
administrative block.

**Rationale (R).** In a stack of sheets, only the corner is visible. Placing the identifier and
revision there allows retrieval without extracting the sheet.

### ADOS-3.9.040 — Scale statement ⚠

**Decision.** Each view shall carry its own scale adjacent to its view title. The title block
shall state a single scale only where all views share it; otherwise it shall state `AS SHOWN`. A
graphic scale bar shall be provided on every sheet whose views may be reduced.

**Rationale (R).** The stated ratio becomes false on reduction; a graphic bar reduces with the
drawing and remains true. Both are provided because the ratio is what readers quote and the bar is
what survives.

**Validation.** `V-3.9.040`: every view has a scale label; title block scale field consistent with
the view set; scale bar present when nominated size ≠ authored size.

### ADOS-3.9.050 — Do-not-scale statement

**Decision.** Every drawing sheet shall carry: `DO NOT SCALE FROM THIS DRAWING. WORK TO FIGURED
DIMENSIONS ONLY. REPORT DISCREPANCIES TO THE ORIGINATOR BEFORE PROCEEDING.`

**Rationale.** Reproduction changes scale by up to 2 % through paper distortion and printer
scaling; scaled measurements are unreliable at exactly the precision that matters.

### ADOS-3.9.060 — Status banner ⚠

**Decision.** Every container with a status other than `A`/`B` shall carry a status banner in
`Z-BANNER` and a diagonal watermark across the drawing area, at tone `T1`, cap height ≥ 10 mm,
stating the status name.

**Rationale.** The title block status field is small and is missed. The watermark cannot be missed
and survives photocopying. Tone `T1` keeps it below the drawing content in salience while remaining
legible.

**Validation.** `V-3.9.060`: banner and watermark present for all non-`A`/`B` statuses; absent for
`A`/`B`; watermark tone = `T1`.

**Common mistakes.** A `PRELIMINARY` watermark retained on a construction issue; a watermark dark
enough to interfere with the drawing.

### ADOS-3.9.070 — Practice identity block

**Decision.** Practice identity (name, mark, contact) shall be confined to a region not exceeding
180 × 20 mm within `Z-TITLE`, in tone `T5` monochrome, and shall not appear elsewhere on the
sheet.

**Rationale.** `ADOS-0.3.010` Ex. 1. Identity is permitted, bounded, and prevented from competing
with content.

**Validation.** `V-3.9.070`: identity marks outside the identity region = 0.

---

## 3.10 Colour

### ADOS-3.10.010 — Monochrome-first ⚠

**Decision.** Documentation shall be fully functional in monochrome. Colour shall be redundant
with a distinction already carried by a rank ≤ 6 channel.

**Rationale.** §1.6.

**Validation.** `V-3.10.010`: the greyscale render passes all `ADOS-8.2` metrics; every colour-coded
distinction has a declared non-colour channel in the encoding table.

### ADOS-3.10.020 — Permitted colour uses

**Decision.** Colour may be used only for: discipline identification on screen-only coordination
views; markup and comment (never issued); status marking on working prints; statutory fire
strategy plans; and where colour is the subject matter (wayfinding, finishes studies).

### ADOS-3.10.030 — Colour specification

**Decision.** Where colour is used it shall be specified in a device-independent space (CIE L*a*b*
or sRGB with an embedded profile), shall satisfy ΔL* ≥ 18 between any two colours that carry
different meanings, and shall be chosen from a palette verified against protanopia, deuteranopia
and tritanopia simulation.

**Validation.** `V-3.10.030`: pairwise ΔL* ≥ 18 for meaning-bearing colours; CVD simulation
maintains pairwise ΔE ≥ 20.

### ADOS-3.10.040 — Colour in printing

**Decision.** Where a set is issued both in colour and monochrome, the monochrome version shall be
generated by the declared conversion transform, and its output shall be validated
independently — not assumed.

---

## 3.11 Composition and balance

### ADOS-3.11.010 — Composition is placement, not arrangement

**Decision.** View placement shall be determined by: (1) reading order (`ADOS-2.10.020`),
(2) column grid alignment (`ADOS-3.3.040`), (3) grouping ratio (`ADOS-3.5.020`), (4) density limits
(`ADOS-3.7`). Where these leave freedom, the tie-break of `ADOS-7.5.050` applies. Aesthetic
judgement is not an input.

**Validation.** `V-3.11.010`: placement is reproducible — re-running the solver on the same input
produces identical coordinates.

### ADOS-3.11.020 — Balance metric ⚠

**Purpose.** Give "visual balance" an objective definition so that it can be checked.

**Background.** Perceived balance corresponds closely to the distribution of ink mass. An
off-centre mass distribution makes the sheet appear to have an unused region, which readers
interpret as missing content.

**Decision.** The centroid of ink mass within the drawing area shall lie within 10 % of the drawing
area diagonal from the drawing area's geometric centre.

```
balance_error = |centroid(ink) − centre(Z-DRAW)| / diagonal(Z-DRAW) ≤ 0.10
```

**Exceptions.**
1. Sheets carrying a single view whose subject is inherently asymmetric (a long section).

**Validation.** `V-3.11.020`: computed from the rendered page; `balance_error ≤ 0.10`.

**Automation notes.** The solver includes balance as a soft objective with weight below all
hard constraints (`ADOS-7.5.040`).

### ADOS-3.11.030 — Optical alignment

**Decision.** Elements shall be aligned on their optical edges, not their bounding boxes, where the
two differ by more than 0.5 mm: round symbols overshoot straight edges by 1–2 % of diameter; text
aligns on the baseline and on the cap line, not on the em box.

**Rationale (V).** Bounding-box alignment of a circle against a rectangle reads as misalignment
because the perceived edge of a circle is its widest point.

**Validation.** `V-3.11.030`: alignment audit uses optical edges for circles, triangles and text.

### ADOS-3.11.040 — Alignment edge budget

**Decision.** A sheet shall present at most six distinct vertical alignment edges and six distinct
horizontal alignment edges in its non-drawing content.

**Rationale (V, C).** Each distinct alignment edge is a visual line the reader's system detects.
Beyond about six, the structure reads as noise rather than order.

**Validation.** `V-3.11.040`: distinct alignment x-coordinates (clustered at 1 mm tolerance) ≤ 6;
same for y.

---

## 3.12 Tables and schedules

### ADOS-3.12.010 — Table structure ⚠

**Decision.** Schedules shall use: a header row at 3.5 mm bold on tone `T1`; body rows at 2.5 mm on
`T0`; row pitch a constant multiple of the sub-module; no vertical rules; horizontal rules only
between row groups; left alignment for text, right alignment for integers, decimal alignment for
decimals.

**Rationale (V).** Vertical rules are unnecessary when columns are separated by a gap satisfying
`ADOS-3.5.020`, and they add ink and line weights that compete with the drawing hierarchy.
Horizontal rules only at group boundaries convert the table into visually scannable bands.

**Exceptions.**
1. Tables exceeding 8 columns may use `T1` row banding instead of rules, at a period of 5 rows.

**Validation.** `V-3.12.010`: vertical rule count = 0; row pitch constant; alignment per column
type correct.

### ADOS-3.12.020 — Column order

**Decision.** Columns shall be ordered: identifier, then classification, then the properties in
decreasing frequency of use, then remarks last.

**Rationale (R).** The identifier is the search key and shall be leftmost so that it can be scanned
in one vertical pass. Remarks vary in length and are placed last so that variable width does not
disturb the alignment of the fixed columns.

### ADOS-3.12.030 — Table continuation

**Decision.** A table continued across pages shall repeat its header row on every page, shall carry
`continued` markers at the break, and shall not break a row group across a page.

**Validation.** `V-3.12.030`: header present on every page of a multi-page table; no orphaned group.

### ADOS-3.12.040 — Empty cells ⚠

**Decision.** An empty cell is prohibited. Every cell shall contain a value, `—` (not applicable),
`TBC` with a hold reference (`ADOS-2.6.080`), or `SEE <ref>`.

**Rationale.** `ADOS-0.3.090`: an empty cell cannot be distinguished from an omission.

**Validation.** `V-3.12.040`: empty cell count = 0.

---

## 3.13 Prose documents

### ADOS-3.13.010 — Page structure

**Decision.** A4 portrait; margins 25 mm left (binding), 20 mm right, 20 mm top, 20 mm bottom; a
single text column of 165 mm measure at 2.5 mm cap height (≈ 92 characters) is non-conforming — the
measure shall be reduced to ≤ 135 mm by increasing the left margin to 45 mm, which creates a
marginal column for clause references and revision marks.

**Rationale (V, R).** `ADOS-3.4.090` bounds measure at 75 characters. The 45 mm margin is not
white space: it carries clause numbers, revision bars and reviewer annotation, all of which need a
dedicated column.

**Validation.** `V-3.13.010`: measure ≤ 135 mm; marginal column present.

### ADOS-3.13.020 — Numbering and headings

**Decision.** Sections shall be numbered decimally to at most four levels
(`4.3.2.1`). Every clause that carries a requirement shall be individually numbered so that it can
be referenced from a drawing.

**Rationale.** A specification requirement that cannot be cited by number cannot be referenced from
a drawing, which forces restatement and violates `ADOS-0.3.020`.

**Validation.** `V-3.13.020`: every requirement-bearing paragraph has a unique number; depth ≤ 4.

### ADOS-3.13.030 — Running heads and page identity

**Decision.** Every page shall carry: container identifier, revision, status, page *n* of *m*, and
the current section title.

**Rationale.** Documents are photocopied page-wise and pages are separated. A page without identity
is unusable evidence.

**Validation.** `V-3.13.030`: all five fields present on every page.

### ADOS-3.13.040 — Revision marking in prose

**Decision.** Changed text shall be marked with a vertical revision bar in the marginal column,
carrying the revision code. Bars from superseded revisions shall be removed.

**Validation.** `V-3.13.040`: bar count > 0 for revisions after the first; no bar carries a
superseded code.

---

## 3.14 Summary of Volume 3

1. Ten encoding channels exist; each carries exactly one dimension of meaning; colour carries none
   on its own.
2. Sheets are ISO A-series; the smallest nominated issue size governs every minimum.
3. Zoning is fixed to the millimetre across a set; the module is 10 mm and the sub-module 5 mm.
4. Type: two faces, eight sizes on a √2 ladder, 2.5 mm body minimum, 5 mm baseline grid, mandatory
   clear zones.
5. White space groups; the ratio is 2:1 at every scale.
6. Three hierarchy levels per region, five text sizes per sheet, 10 % emphasis budget.
7. Density is bounded on three independent measures with a fixed remedy order.
8. Six tones, four per sheet, text only on `T0`/`T1`.
9. Composition is solved, not composed; balance is a measurable centroid condition.

---

*Continue to [Volume 4 — Drawing Language](ADOS-V4-Drawing-Language.md).*
