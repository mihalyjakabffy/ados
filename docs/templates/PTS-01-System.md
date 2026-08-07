# Practice Template System — Part 1: The System

**PTS 1.0 · Design philosophy, visual language, hierarchy, layout, typography, title block,
spacing, relationships.**

Part 2 ([`PTS-02-Templates.md`](PTS-02-Templates.md)) specifies the twelve templates.
Part 3 ([`PTS-03-Implementation.md`](PTS-03-Implementation.md)) maps the system onto Archicad,
InDesign and Word.

PTS is the **practice overlay and template layer** of the Architectural Documentation Operating
System held in [`../ados/`](../ados/README.md). ADOS states *why* a value is what it is; PTS states
*what the value is on our sheets*. Every number below either cites its ADOS derivation or derives
itself here. Nothing is asserted.

---

## 1 Design philosophy

### 1.1 The position

> A document is not a designed object that happens to carry information. It is an instrument that
> happens to be looked at.

Everything in this system follows from taking that literally. The templates are calm not because
calm is a style, but because every mark that does not carry meaning has been removed, and what
remains has nowhere to fight with anything else. Elegance here is a residue, not a goal. If the
system is beautiful, it is beautiful the way a well-cut section is beautiful — as a by-product of
being correct.

### 1.2 Five commitments

**C1 — The page is a fixed instrument, not a canvas.**
Position carries meaning. A reader who has learned one sheet can read every other sheet with no
further learning, because the title block, the scale, the north point and the status sit at
identical coordinates on all of them, to the millimetre. Layout invariance is worth more than any
individual sheet's best composition (`ADOS-0.3.050`). The template is therefore not a starting
point to be adjusted. It is the deliverable's skeleton.

**C2 — Restraint is a budget, not a taste.**
A reader can reliably identify about five states on any one visual channel and hold about four
things at once. That is a hard limit, and it is why this system permits three line weights, four
tones per sheet, five type sizes per sheet, two weights and no colour. Restraint is not a mood.
It is arithmetic (`ADOS-1.2`).

**C3 — White space is structure.**
Space is the strongest grouping signal available and it costs no ink, survives every reproduction,
and cannot be misread. Where other systems reach for a rule, a box or a tint, this one reaches for
distance. The single governing ratio is 2:1 — the gap between groups is twice the largest gap
within a group, applied identically to views on a sheet, blocks in a column, columns in a table
and paragraphs in a specification (`ADOS-3.5.020`).

**C4 — Design for the worst-placed reader.**
Not the principal at a calibrated display. The site supervisor with sixty seconds, a folded
third-generation photocopy, and 200 lux. Every minimum in this system — 2.5 mm cap height, 0.18 mm
line, 1.25 mm clear zone around text — is set at that condition, not at the author's
(`ADOS-0.3.060`). A document that works there works everywhere; the reverse is not true.

**C5 — Identity lives in the system, not on the page.**
The practice's signature is that its documents are unmistakably orderly: the same grid, the same
scale ladder, the same restraint, project after project. It is not a logo lockup, a rule under the
title, or a signature tint. Identity is confined to a 180 × 20 mm strip in the title block and is
absent everywhere else (`ADOS-3.9.070`). This is the discipline most practices abandon first and it
is the one that reads as confidence.

### 1.3 What this system refuses

| Refused | Because |
|---|---|
| Accent colour as a system element | Site prints are monochrome; hue of similar luminance collapses to one tone |
| Rules, boxes and tints used to separate | Space separates better, for free, and cannot be misread |
| A second display typeface | Weight and size already establish every level the system has |
| Icons in documents | A word is faster to read than a glyph you have to learn |
| Full-bleed images in technical documents | Trim tolerance is ±2 mm; a bleed that fails looks like an error |
| Centred body text or justified rag | Ragged-right left-aligned is faster to scan and has no rivers |
| Per-project template variants | Reader learning stops transferring; template investment stops compounding |
| Golden-ratio composition | No functional justification exists; it breaks the lattice (`ADOS-1.4.2`) |

---

## 2 Visual language

### 2.1 The channel budget

Six channels carry meaning. Each carries exactly one dimension of meaning, and no more states than
a reader can reliably identify (`ADOS-3.1.010`).

| Channel | States | Carries | Never carries |
|---|---|---|---|
| **Position** | continuous | Document identity, zone role, reading order | Emphasis |
| **Line weight** | 3 semantic + 2 refinement | Depth relative to the cut plane | Object category |
| **Line type** | 4 | Visibility state | Category |
| **Tone** | 6 defined, 4 per sheet | Material class, phase, figure/ground | Emphasis |
| **Type size** | 8 defined, 5 per sheet | Hierarchy level | Importance |
| **Type weight** | 2 | One declared structural role per document class | Ad-hoc emphasis |

Colour is not in the table. It may be added on top of a distinction already fully carried by one of
the six, and it may never be the only carrier (`ADOS-3.10.010`).

### 2.2 Ink

The system is monochrome. Two values only:

| Value | Specification | Use |
|---|---|---|
| **Ink** | 100 % K, single channel | All text, all linework |
| **Paper** | 0 % | Ground |

Text is single-channel black so that it needs no registration and stays crisp on every device.
Areas are not solid black; they use the tone ladder, whose top step is 88 % coverage precisely
because a 100 % flood causes set-off, toner scatter and a drying penalty for no legibility gain.

### 2.3 Tone ladder

Six steps, spaced 18 ΔL\*, which is the spacing at which two tones remain separately identifiable
after two generations of monochrome copying (`ADOS-3.8.010`). No sheet uses more than four.

| Token | L\* | Coverage | Reserved for |
|---|---|---|---|
| `T0` | 100 | 0 % | Paper, void, not applicable |
| `T1` | 82 | 12 % | Background: context, other disciplines, existing to remain, watermarks, table header bands |
| `T2` | 64 | 26 % | Secondary fill |
| `T3` | 46 | 42 % | Primary fill, poché, key plan current area |
| `T4` | 28 | 60 % | Emphasis fill |
| `T5` | 10 | 88 % | Cut elements too thin to read filled at `T3` |

Text sits on `T0` or `T1` only. Reversed text does not exist in this system: its counters fill in
after one copy generation, and it cannot be marked up with a pen on site.

### 2.4 Line

Three semantic weights at a factor of two, which is the separation at which a weight can be
identified in isolation rather than by comparison (`ADOS-4.1.020`).

| Tier | Width | Means |
|---|---|---|
| **W3** | 0.70 mm | Cut by this view's cut plane |
| **W2** | 0.35 mm | Seen, in front of the cut plane |
| **W1** | 0.18 mm | Beyond, hidden, reference, or apparatus |

`0.25` and `0.50 mm` refine *within* a tier and never distinguish one tier from another.
`1.00` and `1.40 mm` belong to sheet apparatus — frame, section cut line, match line — and never to
building fabric. Weight is a depth cue and is a monotonic function of distance from the observer.
It is never assigned by object category and never used for emphasis.

Four line types, defined in printed millimetres so that the pattern is identical at every scale:
continuous; dash 4.0 / gap 2.0; dot 0.5 / gap 1.5; long-dash-dot 12.0 / 2.0 / 0.5 / 2.0.

### 2.5 Rules and boxes

A rule is permitted in exactly four places, and in each it does structural work that space cannot:

| Rule | Weight | Where | Work it does |
|---|---|---|---|
| Sheet frame | 1.00 mm | Frame boundary | Defines the printable field; a trim reference |
| Title block division | 0.35 mm | Between title block rows | Field boundaries in a dense data block where space is unavailable |
| Table group rule | 0.18 mm | Between row groups only | Banding at the group boundary; never between every row |
| Header/footer hairline | 0.18 mm | A4 documents | Separates page apparatus from content across a page turn |

There are no other rules. No rule under a heading, no box around a note, no border on an image.

### 2.6 The absence of icons

This system uses no icons in documents. It uses the thirty drawing symbols of `ADOS-4.16.010` on
drawings and nothing else. The reason is measurable: a familiar word is read faster than an
unfamiliar glyph, and every glyph added to a set reduces the recognisability of the others. Status,
severity and type are set typographically — in small caps or upper case, in the position reserved
for them. A document that needs an icon legend has replaced reading with lookup.

The one exception is the north point, which is a direction and cannot be written.

---

## 3 Information hierarchy

### 3.1 Three reading modes, three depths

Every document supports three modes in sequence, and the hierarchy exists to serve them in order
(`ADOS-0.5.020`).

| Mode | Time | Question | Served by |
|---|---|---|---|
| **Orientation** | ≤ 5 s | What is this and where does it sit? | Fixed-position identity: sheet number, title, status, scale, key plan |
| **Search** | ≤ 60 s | Where is the thing I need? | Zoning, view titles, grid references, the register |
| **Extraction** | ≤ 10 min | What exactly does it say? | Dimensions, annotation, references onward |

A sheet that requires content reading to establish its own identity has failed before it is read.

### 3.2 The four levels, and only four

| Level | Expressed by | Example |
|---|---|---|
| **L0 Identity** | Fixed position + largest type on the sheet | Sheet number `A3.104` |
| **L1 Subject** | Type size step + position at the top of its region | Sheet title, view title |
| **L2 Content** | The drawing or the body text itself | Plan, clause, schedule row |
| **L3 Support** | Smallest type, subordinate position | Notes, provenance, legal line |

Within any one region at most three of these appear (`ADOS-3.6.020`). A step between adjacent
levels changes **one** channel — size, or weight, or position — never several at once. Changing
three channels to express one step spends the whole budget on the first distinction and leaves
nothing for the next.

### 3.3 The emphasis budget

Emphasised content — bold text, `T4`/`T5` fill, the heaviest weight, enclosure — occupies at most
**10 %** of the drawing or text area. Above roughly that figure the emphasised set becomes the
field rather than the figure and the effect inverts (`ADOS-3.6.040`).

### 3.4 What the hierarchy is *not* allowed to do

It does not rank importance. Importance is a property of content and is the reader's to judge. The
hierarchy ranks **order of use**: what must be read first to make the rest interpretable. A note
that is critically important still sits at L3 if it is read last.

---

## 4 Layout system

### 4.1 Two page families

| Family | Orientation | Formats | Structure |
|---|---|---|---|
| **Sheet** | Landscape | A0, A1, A2, A3 | Framed field + title block band; content is views |
| **Document** | Portrait | A4 | Margins + marginal column + text column; content is prose or tables |

Schedules are sheets whose single view is a table. Presentation boards are a third, deliberately
separate family (§4.6) because their reader stands three metres away.

### 4.2 The module

One quantum governs every position in the system:

```
module M      = 10 mm     one grid square = 1.000 m at 1:100, 0.500 m at 1:50
sub-module m  =  5 mm     the placement lattice; also the text baseline pitch
```

Every zone boundary, view origin, annotation block origin, table row and text baseline sits on the
5 mm lattice. Nothing is placed at an arbitrary coordinate. This is what makes alignment free
rather than a matter of care (`ADOS-3.3.030`).

### 4.3 Sheet geometry — margins and zones

Margins are constant across every format: **binding edge 20 mm, all other edges 10 mm.** Twenty
absorbs punch holes and binding strips; ten absorbs the non-printable margin of a large-format
plotter (3–5 mm) plus trim tolerance (±2 mm) with margin to spare (`ADOS-3.3.020`).

Two zoning templates:

**Large format — A0, A1.** A 180 mm band on the right edge, 10 mm clear of the drawing area.

```
┌────────────────────────────────────────────────────┬──────────────┐
│ Z-BANNER   status band                       h 10  │  Z-KEY       │  key plan   ≥60×60
├────────────────────────────────────────────────────┤              │
│                                                    ├──────────────┤
│                                                    │              │
│                  Z-DRAW                            │  Z-NOTES     │  2 sub-columns
│                  views, on the column grid         │              │  85 + 10 + 85
│                                                    │              │
│                                                    ├──────────────┤
│                                                    │  Z-REV       │  ≥60, grows up
├────────────────────────────────────────────────────┼──────────────┤
│ Z-GRIDREF  frame zone references             h  5  │  Z-TITLE     │  180 × 90
└────────────────────────────────────────────────────┴──────────────┘
◄─── 20 binding ────                        ─── 180 ───►◄ 10 ►
```

**Small format — A2, A3.** A 60 mm band across the foot: title block 180 × 60 at the right, notes
and key plan to its left.

*Deviation note.* `ADOS-3.3.010` places A2 in the large-format group. At A2 the right band consumes
32 % of the frame width and leaves a nearly square 374 × 385 drawing area, which fails the fill
ratio on most A2 subjects. PTS therefore assigns A2 to the small-format template and records this
in the Deviation Register with that reason. The underlying rule is a candidate for amendment at the
next ADOS revision; it has not been changed unilaterally.

### 4.4 Sheet geometry — the numbers

All figures in millimetres, at authored size. Residual is the unused strip at the right edge of the
drawing area; it carries no content.

| Format | Sheet | Frame | Template | Z-DRAW | Columns | Gutter | Residual |
|---|---|---|---|---|---|---|---|
| **A0** | 1189 × 841 | 1159 × 821 | right band | **969 × 806** | 5 × 185 | 10 | 4 |
| **A1** | 841 × 594 | 811 × 574 | right band | **621 × 559** | 6 × 95 | 10 | 1 |
| **A2** | 594 × 420 | 564 × 400 | bottom band | **564 × 325** | 6 × 85 | 10 | 4 |
| **A3** | 420 × 297 | 390 × 277 | bottom band | **390 × 202** | 4 × 90 | 10 | 0 |

A1 worked in full, as the reference case:

```
frame width   841 − 20 (binding) − 10 (right)                    = 811
Z-DRAW width  811 − 180 (band) − 10 (gutter)                     = 621
frame height  594 − 10 (top) − 10 (bottom)                       = 574
Z-DRAW height 574 − 10 (Z-BANNER) − 5 (Z-GRIDREF)                = 559
columns       6 × 95 + 5 × 10 = 620, residual 1
origins       0 · 105 · 210 · 315 · 420 · 525    all on the 5 mm lattice
```

A1 is the default. It is the largest sheet that fits a site table, folds to A4 in a repeatable
pattern, can be handled by one person outdoors, and halves exactly to A3. A0 is permitted only
where a required view at a required scale cannot be split without severing a continuous condition,
and the justification is recorded.

### 4.5 Document geometry — A4

```
        0    20        45  50                    170              210
        │    │         │   │                      │                │
   0  ──┼────┼─────────┼───┼──────────────────────┼────────────────┤
        │    │         │   │                      │                │
  15  ──┤    │  header: project · code      ┊  container ID        │   t2
  20  ──┤    ├──────────────────────────────────── hairline 0.18   │
        │    │ marginal│   │  text column         │  right margin  │
  30  ──┤    │  column │ g │  120 mm              │   40 mm        │  ← first baseline
        │    │  25 mm  │ 5 │  ≈ 67 characters     │                │
        │    │         │   │  49 baselines @ 5    │                │
 270  ──┤    │         │   │                      │                │  ← last baseline
 272  ──┤    ├──────────────────────────────────── hairline 0.18   │
 280  ──┤    │  container ID · rev · status   ┊  Page n / m        │   t2
 297  ──┴────┴──────────────────────────────────────────────────────┘
```

| Element | Value | Reason |
|---|---|---|
| Left margin | 20 mm | Binding and punch clearance |
| Marginal column | 25 mm, at 20–45 | Clause numbers, revision bars, reviewer marks |
| Gutter | 5 mm | One sub-module |
| Text column | 120 mm, at 50–170 | 120 / 1.8 mm average advance ≈ 67 characters, inside the 45–75 band |
| Right margin | 40 mm | The residue; also the reader's annotation space |
| Top margin | 25 mm | First baseline at 30 |
| Baselines | 49 at 5 mm, 30 → 270 | Sub-module rhythm |
| Footer baseline | 280 | On the lattice; 17 mm clear of the trim |

The marginal column is not decoration and not a fashionable wide margin. Without it the measure is
160 mm — 89 characters — which is beyond the point at which the eye reliably finds the start of the
next line. The column pays for itself twice: it fixes the measure and it holds the clause numbers
that make every requirement citable from a drawing.

### 4.6 Presentation board geometry

A board is read standing, at 1.5–3 m. Applying the legibility derivation `h = d × 4.945 × 10⁻³`
(`ADOS-1.2.1`) at those distances gives 7.4 mm and 14.8 mm cap heights — which is why a board
cannot use sheet typography and needs its own family.

| Property | Value |
|---|---|
| Format | A1 landscape (A0 for exhibition) |
| Margins | 35 mm all round — a board is pinned, not bound; symmetry reads as composure |
| Frame | 771 × 524 |
| Columns | 6 × 120, gutter 10, residual 1 |
| Baseline | 5 mm, 104 lines |
| Body text | 7 mm cap (`t5`) minimum |
| Section headings | 14 mm cap (`t7`) |
| Board title | 20 mm cap (`t8`) |
| Images | Aligned to column boundaries; no bleed; no border; no drop shadow |

### 4.7 Fill and density

Three independent limits, all measured, all two-sided where two-sided makes sense
(`ADOS-3.7`):

| Measure | Range | Failure it prevents |
|---|---|---|
| Fill ratio (view bounding boxes ÷ drawing area) | 0.40 – 0.85 | Under: the sheet does not justify its own navigation cost. Over: views collide with the frame |
| Local ink coverage, any 20 × 20 mm window | ≤ 0.25 | Strokes merge into a grey field after two copy generations |
| Annotation objects per search region | ≤ 50 | Search time exceeds its budget |

When a limit is breached the remedy order is fixed: move content to its correct level → remove
duplicates of an authoritative value → split the view → split the sheet → change the sheet size.
Reducing text size, line weight or spacing is not on the list and is not permitted. A sheet with
small text is a sheet that should have been split.

---

## 5 Typography

### 5.1 Selection, not preference

The drawing face is chosen against a requirement list, because technical documents are dominated by
strings whose content cannot be guessed from context — `D-1108`, `FD30S`, `A3.104`, `+12.450`. A
misread character cannot be recovered.

| # | Requirement | Reason |
|---|---|---|
| 1 | Grotesque or humanist sans, upright | Uniform stroke survives reproduction |
| 2 | `1` `l` `I` distinct at 2.5 mm | Sheet and mark identifiers |
| 3 | `0` distinguishable from `O` — slashed, dotted or clearly ovoid | Levels and dimensions |
| 4 | `5`/`S`, `2`/`Z`, `6`/`8`/`9` distinct | Identifier reading |
| 5 | Tabular lining figures | Column alignment in every schedule |
| 6 | x-height ≥ 0.52 em | Legibility at small sizes |
| 7 | Open apertures on `c e s a` | Resists fill-in under ink spread |
| 8 | Stroke contrast ≤ 1.3 : 1 | Thin strokes survive edge erosion |
| 9 | True italic and small capitals | Defined terms and emphasis in prose |
| 10 | ≥ 2 weights | The weight channel |
| 11 | Embeddable licence, outline-embeddable in PDF | Fixed rendering off-site |

**Recommendation: one family, plus one monospace.** A single grotesque carrying a true italic and
small capitals satisfies both the drawing and the document requirement, and one family is strictly
better than two — it removes a switching cue that carries no meaning.

| Role | Recommended | Alternative | Open fallback |
|---|---|---|---|
| Primary | **Söhne** (Klim) | Neue Haas Grotesk Text · Univers Next · ABC Diatype | **Inter** (SIL OFL) |
| Monospace | **Söhne Mono** | IBM Plex Mono | **IBM Plex Mono** (SIL OFL) |

Monospace is used for one thing only: machine identifiers — container IDs, file paths, coordinates.
It signals *this string is exact* and its fixed advance makes a transposed character visible.

The open fallback is not a compromise to be embarrassed about. It is the version that renders
identically on a consultant's machine, in a Word document opened by a client, and in an Archicad
file on a site laptop. Specify the licensed family for InDesign and PDF issue; specify the fallback
for Word and for any file that leaves the practice as an editable document.

### 5.2 The scale

Eight sizes on a √2 progression. √2 is not chosen for looks: ISO paper scales by √2, so a sheet
reduced one size maps every type size onto the next valid size and the hierarchy survives the
reduction intact. Every second step is a factor of two — the separation needed to identify a size
in isolation (`ADOS-1.4`).

Point values assume cap height / em = 0.72. **Measure the cap height of the chosen family and
recalculate; do not trust the point size.**

| Step | Cap | ≈ pt | Role | Pitch |
|---|---|---|---|---|
| `t1` | 1.8 mm | 7 | Legal line, provenance, tertiary annotation (A1+ only) | 5 |
| `t2` | **2.5 mm** | 10 | **Body.** Notes, dimensions, tags, schedule cells, footers | 5 |
| `t3` | 3.5 mm | 14 | View titles, block headings, schedule column headers | 10 |
| `t4` | 5.0 mm | 20 | Sheet title, document section headings, status | 10 |
| `t5` | 7.0 mm | 28 | Sheet number, status banner, board body | 15 |
| `t6` | 10 mm | 39 | Cover document title, watermark | 20 |
| `t7` | 14 mm | 55 | Cover project title, board headings | 30 |
| `t8` | 20 mm | 79 | Board title | 40 |

**2.5 mm is the floor for anything a reader must read to act.** It comes from 17 arcmin of visual
angle at 500 mm — the angle at which unfamiliar strings are read fluently rather than deciphered.
1.8 mm is permitted only for secondary annotation on A1 and larger, where the reader leans in to
350 mm. Below 1.8 mm nothing is set, ever.

At most five steps appear on one sheet.

### 5.3 Setting

| Property | Value | Reason |
|---|---|---|
| Alignment | Left, ragged right | Justification produces rivers at a 67-character measure and forces hyphenation of technical strings |
| Baseline pitch | 2.0 × cap, rounded up to the sub-module | 1.4 em; puts every line on the 5 mm lattice |
| Paragraph separation | One baseline (5 mm), no indent | An indent and a space do the same job; using both is redundant |
| Measure | 45–75 characters | Below 45 the eye returns too often; above 75 it loses the line |
| Case | Upper for labels ≤ 40 characters; sentence case for everything longer | Upper case removes word-shape cues and costs 10–15 % reading speed |
| Weight | Regular; medium for exactly one declared role per document class | Two states is the reliable limit |
| Tracking | Unmodified, except +2 % on upper-case runs at `t1`–`t2` | Capitals set at text tracking close up at small sizes |
| Figures | Tabular lining throughout | Column alignment |
| Clear zone | `max(0.5 × cap, 1.0 mm)` around every text object, masked where it overlies linework | Crowding impairs character identification within half a cap height |

Prohibited: underline; italic for emphasis on drawings; letter-spacing as emphasis; outlined,
shadowed or filled text; horizontal scaling to fake a condensed cut; rotation at any angle other
than 0° or 90° counter-clockwise.

---

## 6 Title block system

### 6.1 One object, four variants

The title block is a single parametric object whose fields are bound to project and container data.
**No field is ever typed on a sheet.** A typed title block field is a hand-maintained copy of a fact
held elsewhere, and it is the most frequently wrong content in any drawing set.

| Variant | Size | Used on |
|---|---|---|
| **TB-L** | 180 × 90 | A0, A1 sheets |
| **TB-S** | 180 × 60 | A2, A3 sheets, schedules |
| **TB-D** | header + footer strip | A4 documents |
| **TB-B** | 180 × 40, foot right | Presentation boards |

180 mm is the ISO 7200 data field width. Holding it constant across every variant means one set of
field positions, one object to maintain, and a reader who finds the same fact in the same place at
every format.

### 6.2 TB-L — 180 × 90

Rows on the 5 mm lattice. Divisions are 0.35 mm rules; the outer boundary is 1.00 mm.

```
 ◄──────────────── 135 ─────────────────►◄──────── 45 ────────►
┌───────────────────────────────────────┬──────────────────────┐  0
│ RIVERSIDE WORKSHOPS               t3  │                      │
│ 2317 · Client name                t2  │                      │  15
├───────────────────────────────────────┤                      │
│ LEVEL 02                              │                      │
│ GENERAL ARRANGEMENT PLAN          t4  │                      │  35
├──────────────────┬────────────────────┼──────────────────────┤
│ SCALE  1:100 t3  │ STATUS  A1     t4  │  A3.104          t5  │  50
├──────────────────┴────────────────────┤                      │
│ KV · MT · AN · 2026-03-14         t2  │  C03             t4  │  65
├───────────────────────────────────────┤  A1 / issue A1   t2  │
│ 2317-JKA-ZZ-02-DR-A-3104     t2 mono  │                      │  75
├───────────────────────────────────────┴──────────────────────┤
│ ORIGINATOR · address · contact                           t2  │  85
│ ADOS 1.0 Class B · DO NOT SCALE · WORK TO FIGURED DIMS   t1  │  90
└──────────────────────────────────────────────────────────────┘
```

**Field order is by frequency of use, most frequent nearest the sheet corner.** In a stack of
sheets only the corner is visible, so the sheet number and revision sit there and a drawing can be
found without extracting it. This is the whole reason for the layout and it is why the arrangement
is not negotiable.

| Row | y | Content | Size |
|---|---|---|---|
| 1 | 0–15 | Project name / project code · client | `t3` / `t2` |
| 2 | 15–35 | Sheet title, up to two lines at 10 mm pitch | `t4` |
| 3 | 35–50 | Scale · Status | `t3` / `t4` |
| 4 | 50–65 | Drawn · Checked · Approved · Date | `t2` |
| 5 | 65–75 | Container identifier | `t2` mono |
| 6 | 75–85 | Originator, address, contact | `t2` |
| 7 | 85–90 | Conformance · do-not-scale · copyright | `t1` |
| R | 35–75 | Sheet number / revision / size · nominated issue size | `t5` / `t4` / `t2` |

### 6.3 TB-S — 180 × 60

The same fields, compressed by dropping the second title line and merging the parties row into the
identifier row. Rows at 0 / 10 / 25 / 35 / 45 / 60.

### 6.4 TB-D — A4 documents

There is no title block on a document page; there is an identity strip, repeated on every page,
because pages are photocopied and separated and a page without identity is unusable as evidence.

```
header  y 15   left: PROJECT NAME · 2317        right: container ID (mono)     t2
        y 20   hairline 0.18 mm, T5, 20 → 190
footer  y 272  hairline 0.18 mm, T5, 20 → 190
        y 280  left: container ID · C03 · A1    right: Page 3 / 12             t2
```

Page 1 additionally carries the full data block in the first 40 mm of the text column: title,
status, revision, date, author, checker, approver, distribution.

### 6.5 Fields — the closed set

Every variant draws from one field list. A field is either present or explicitly `—`; it is never
blank (`ADOS-3.12.040`).

| # | Field | Bound to | TB-L | TB-S | TB-D | TB-B |
|---|---|---|---|---|---|---|
| 1 | Project name | Project | ● | ● | ● | ● |
| 2 | Project code | Project | ● | ● | ● | ● |
| 3 | Client | Project | ● | ● | ● | ○ |
| 4 | Sheet / document title | Container | ● | ● | ● | ● |
| 5 | Sheet number, short form | Container | ● | ● | — | ● |
| 6 | Container identifier, full | Container | ● | ● | ● | ● |
| 7 | Scale, per view or `AS SHOWN` | View | ● | ● | — | ○ |
| 8 | Sheet size · nominated issue size | Set | ● | ● | ● | ● |
| 9 | Status code and name | Container | ● | ● | ● | ● |
| 10 | Revision code | Container | ● | ● | ● | ● |
| 11 | Date of issue | Issue | ● | ● | ● | ● |
| 12 | Drawn by | Container | ● | ● | ● | ○ |
| 13 | Checked by | Container | ● | ● | ● | ○ |
| 14 | Approved by | Container | ● | ● | ● | ○ |
| 15 | Originator name and contact | Set | ● | ● | ● | ● |
| 16 | North point / projection statement | View | ● | ● | — | ○ |
| 17 | Conformance claim | Set | ● | ● | ● | — |
| 18 | Do-not-scale statement | Fixed | ● | ● | — | ● |
| 19 | Copyright / confidentiality | Practice | ● | ● | ● | ● |
| 20 | Page number | Container | — | — | ● | — |

### 6.6 Status marking

Status is *permitted use* and is orthogonal to revision, which is *generation*. Both are always
visible. Any status other than authorised carries a banner in `Z-BANNER` **and** a diagonal
watermark across the drawing area at `T1`, ≥ 10 mm cap. The title block field alone is too small
and is missed; a watermark cannot be.

| Code | Name | Watermark |
|---|---|---|
| `S0` | Work in progress | ● |
| `S1` | Shared for coordination | ● |
| `S2` | Shared for information | ● |
| `S3` | Shared for review and comment | ● |
| `S4` | Shared for stage approval | ● |
| `A1…` | Authorised and accepted | — |
| `B1…` | Partially authorised | annotated exceptions only |
| `WD` | Withdrawn | ● |

### 6.7 Practice identity

Name, mark and contact occupy row 6 of TB-L and its equivalents: a strip of **180 × 20 mm maximum**,
monochrome, and they appear nowhere else on the sheet. Identity is expressed by the consistency of
the whole set, not by repetition of a mark.

---

## 7 Spacing, alignment and grid rules

### 7.1 The spacing scale

Four values, each twice the last, so that any two adjacent levels satisfy the grouping ratio
automatically:

```
5 mm    within a group      — lines of a note, cells of a row, dimension text to its line
10 mm   between groups      — note blocks, annotation clusters, table column groups
20 mm   between sections    — views on a sheet, sections of a document
40 mm   between major parts — the cover's identity block to its declarations
```

No other spacing value exists. If a gap needs to be 13 mm, either the grouping is wrong or the
content belongs somewhere else.

### 7.2 The 2:1 rule

```
gap between groups  ≥  2 × largest gap within a group
```

One ratio, applied at every scale: views on a sheet, blocks in the notes column, columns in a
schedule, paragraphs in a specification, images on a board. Grouping by proximity is the strongest
signal available to the eye, and it is unambiguous only when the between-gap clearly dominates
(`ADOS-3.5.020`).

Equal spacing everywhere — the most common default — communicates nothing, because everything is
equally related to everything else.

### 7.3 Alignment

| Rule | Value |
|---|---|
| Everything snaps to the 5 mm lattice | `x mod 5 = 0`, `y mod 5 = 0` |
| Distinct alignment edges per axis, per sheet | ≤ 6 |
| Optical alignment where it differs from the box by > 0.5 mm | Circles overshoot straight edges by 1–2 % of diameter; text aligns on baseline and cap line, not the em box |
| Numeric columns | Right-aligned, or aligned on the decimal separator |
| Text columns | Left-aligned |

The six-edge limit matters: each distinct alignment edge is a line the visual system detects, and
past about six the structure reads as noise rather than order.

### 7.4 White space principles

1. **Space before rules.** Reach for distance; reach for a rule only when there is no distance to
   spend.
2. **Space is proportional to the break.** The size of a gap states the size of the conceptual
   jump — that is its entire job.
3. **Margins are not empty.** The A4 right margin holds the reader's pen. The sheet margin holds
   the binding and the plotter's non-printable edge. Filling them destroys a function.
4. **A quiet sheet is not an under-used sheet.** The fill ratio floor of 0.40 is the test. Below it,
   merge. Above it, calm is correct and adding content to "balance" the sheet is a defect.
5. **Never buy space by shrinking type.** It is the one remedy this system prohibits outright,
   because it converts a visible problem into an invisible one.

### 7.5 Vertical rhythm

Every baseline sits on the 5 mm lattice. Repeating elements — note lines, table rows, legend
entries, revision rows — hold constant pitch, so that the eye tracks across a row without
re-fixating and a row's position can be computed instead of searched. Where content must wrap, the
row grows in whole sub-module increments.

---

## 8 How the templates relate

### 8.1 Inheritance

```
                        ┌──────────────────────┐
                        │  PTS CORE            │  module · tone · line · type ·
                        │  §2 – §7             │  spacing · alignment · title block
                        └──────────┬───────────┘
                     ┌─────────────┼─────────────┐
              ┌──────▼──────┐ ┌────▼────────┐ ┌──▼─────────────┐
              │ SHEET       │ │ DOCUMENT    │ │ BOARD          │
              │ landscape   │ │ A4 portrait │ │ own type scale │
              │ TB-L / TB-S │ │ TB-D        │ │ TB-B           │
              └──────┬──────┘ └────┬────────┘ └──┬─────────────┘
     ┌───────┬───────┼───────┐     ├──────────┐  │
  Cover  Drawing  Detail  Schedule │          │  Presentation
  Sheet   Sheet    Sheet  (table   │          │  Board
     │      │        │     as view)│          │
  Project  │        │             Specification
  Info     │        │             Meeting Minutes
  Sheet    │        │             Site Visit Report
           │        │             RFI
           │        │             Revision Log
           │        │             Transmittal
```

A template inherits everything from its family and overrides nothing that the family fixes. It may
only *add*: a field, a block, a stricter limit. This is the same overlay discipline the standard
applies to jurisdictions, applied to templates.

### 8.2 Content routing — one fact, one place

The templates form a system because each one owns a class of fact and the others reference it.
Nothing is restated (`ADOS-2.2.010`).

| Fact | Owner | Referenced from |
|---|---|---|
| Geometry, position, size | Model → Drawing Sheet | Detail Sheet, Board |
| Assembly build-up | Detail Sheet, by type code | Drawing Sheet, Specification |
| Door / window properties | Schedule, by mark | Drawing Sheet |
| Materials, workmanship, performance | Specification, by clause | Every drawing |
| Project directory and declarations | Project Information Sheet | Cover Sheet, every document |
| What exists and at what revision | Revision Log | Transmittal, Cover Sheet |
| What was sent, to whom, when | Transmittal Sheet | Revision Log |
| What was decided | Meeting Minutes | RFI, Site Visit Report |
| What was asked and answered | RFI | Revision Log |
| What was observed | Site Visit Report | RFI |

A drawing annotates `D-1108` and stops. It does not say `900 × 2100 FD30S`. Two of those three
would eventually be updated and the third would be built.

### 8.3 The document graph

```
Cover Sheet ─────────► Project Information Sheet ─────► Revision Log
     │                          │                            ▲
     │                          ▼                            │
     └──────────────► Drawing Sheet ◄──────► Detail Sheet ────┤
                           │  ▲                   │           │
                           │  └── Schedule ───────┤           │
                           ▼                      ▼           │
                      Specification ◄─────────────┘           │
                                                              │
   RFI ◄──── Site Visit Report ◄──── Meeting Minutes          │
    │                                                         │
    └──────────────► Transmittal Sheet ──────────────────────┘

   Presentation Board ── draws from the model; references nothing; is referenced by nothing
```

Every arrow is reciprocal: a callout on a drawing produces a *referenced from* entry on the detail,
generated at publication, never typed. A one-way reference strands the reader and makes change
impact unknowable.

The board sits outside the graph deliberately. It is illustrative, is never part of a technical
package, and is never cited as a source of requirement.

### 8.4 What is shared, and what varies

| Shared by every template | Varies by template |
|---|---|
| Module and lattice | Zone dimensions |
| Type scale and setting rules | Which steps are used |
| Tone ladder and line tiers | Which tones appear |
| Spacing scale and 2:1 rule | Grouping structure |
| Title block fields and order | Variant geometry |
| Status and revision mechanics | Where the revision mark sits |
| Footer content model | Page numbering presence |

A new template is defined by filling in the right-hand column. The left-hand column is never
touched, and that is what makes the system a system rather than a folder of files.

---

*Continue to [Part 2 — Template Specifications](PTS-02-Templates.md).*
