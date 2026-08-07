# Practice Template System — Part 3: Implementation

**PTS 1.0 · Archicad · InDesign · Word.**

The system is defined in millimetres and is tool-independent. This part maps it onto the three
applications the practice uses, in the order the templates should be built. Nothing here changes a
decision; it only states how each decision is expressed in a given application.

Numeric constants are in [`machine/pts-tokens.json`](machine/pts-tokens.json). Build from the token
file, not from the prose — the prose is the explanation, the token file is the source.

---

## 1 Before anything is built

### 1.1 Calibrate the typeface

Point sizes in this system are **derived from cap height**, and the cap-height-to-em ratio differs
between families by up to 8 %. Building templates from the point sizes in the table without checking
will put the whole set off the type scale.

```
1. Set the chosen family at 100 pt.
2. Measure the cap height of "H" in millimetres.        → h100
3. For each step:   pt = cap_mm × 100 / h100
4. Round to 0.5 pt. Record the table in the practice overlay.
```

For a family with cap/em = 0.72 the table is:

| Step | Cap | pt |
|---|---|---|
| `t1` | 1.8 mm | 7.0 |
| `t2` | 2.5 mm | 10.0 |
| `t3` | 3.5 mm | 14.0 |
| `t4` | 5.0 mm | 19.5 |
| `t5` | 7.0 mm | 27.5 |
| `t6` | 10 mm | 39.5 |
| `t7` | 14 mm | 55.0 |
| `t8` | 20 mm | 78.5 |

Line spacing is set **exactly**, never at a multiple, in every application:

| Cap | Pitch | Points |
|---|---|---|
| 1.8 / 2.5 mm | 5 mm | 14.2 pt |
| 3.5 / 5.0 mm | 10 mm | 28.35 pt |
| 7.0 mm | 15 mm | 42.5 pt |
| 10 mm | 20 mm | 56.7 pt |

### 1.2 Fix the font strategy

| Deliverable | Family | Reason |
|---|---|---|
| Archicad, InDesign, PDF issue | Licensed primary | Full character set, true italic, small capitals |
| Word documents that leave the practice as `.docx` | Open fallback (Inter / IBM Plex) | Renders identically on the recipient's machine |
| Machine identifiers everywhere | Monospace | A transposed character is visible |

Never rely on a system font. Substitution changes metrics silently, which moves every baseline and
breaks the density and collision checks with no warning.

---

## 2 Archicad

Build order: pen sets → master layouts → title block object → view settings → layout book →
publisher.

### 2.1 Pen sets

Pen number encodes its own width and purpose: `pen = group × 10 + width index`.

| Width index | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| Width mm | 0.13 | **0.18** | 0.25 | **0.35** | 0.50 | **0.70** | 1.00 | 1.40 | 2.00 |

| Group | Pens | Use |
|---|---|---|
| 0 | 01–09 | New building fabric — the tier set. `06` = cut, `04` = seen, `02` = beyond |
| 1 | 11–19 | Background / existing to remain, printed at `T1` grey |
| 2 | 21–29 | Annotation, dimensions, text, leaders |
| 3 | 31–39 | Demolition and temporary |
| 4 | 41–49 | Other disciplines' reference content |
| 5 | 51–59 | Sheet apparatus: frame, title block, markers, grid |
| 9 | 91–99 | Non-printing: construction lines, working geometry |

Three pen sets: **PTS Issue** (as above), **PTS Coordination** (discipline colours on screen, same
widths), **PTS Screen** (0.13 mm permitted, non-printing pens visible).

An operator choosing pen `24` cannot accidentally get a cut-weight line for an annotation. That is
the point of the formula.

### 2.2 Master layouts

One master per format. Draw the frame, zones and grid references once; place the title block object.

| Master | Sheet | Frame offsets | Title block | Notes |
|---|---|---|---|---|
| `PTS A1 L` | 841 × 594 | 20 / 10 / 10 / 10 | TB-L at 651, 15 | Right band 180 |
| `PTS A0 L` | 1189 × 841 | 20 / 10 / 10 / 10 | TB-L at 999, 15 | Right band 180 |
| `PTS A2 L` | 594 × 420 | 20 / 10 / 10 / 10 | TB-S at 404, 10 | Bottom band 60 |
| `PTS A3 L` | 420 × 297 | 20 / 10 / 10 / 10 | TB-S at 230, 10 | Bottom band 60 |
| `PTS A1 BOARD` | 841 × 594 | 35 all round | TB-B | 6 × 120 |

Title block origin is the frame's inner bottom-right corner minus the block size. For A1:
frame right edge at 831, bottom at 10; block 180 × 90 → origin (651, 10). Verify by placing a
temporary 180 × 90 rectangle and snapping.

Zone rectangles are drawn on a non-printing layer (`PTS-ZONES`, pen 92) so that operators can see
the boundaries while placing views and the boundaries never print.

### 2.3 Title block object

Build TB-L and TB-S as **library parts** with parameters bound to Project Info and Layout
parameters, using autotext. Do not build the title block as a group of text elements: a group can be
edited on one layout and will be.

| Field | Autotext source |
|---|---|
| Project name, code, client | Project Info |
| Sheet title, number, ID | Layout parameters |
| Scale | Drawing scale, or literal `AS SHOWN` |
| Status, revision, date | Layout parameters, driven by the Change Manager |
| Drawn / checked / approved | Layout parameters |
| Originator, conformance, legal | Library part defaults, locked |

Lock every parameter that is not project-specific. A locked field cannot become wrong.

### 2.4 View settings

One saved View Setting combination per view type × scale × purpose. A view without a template
inherits whatever the last operator left set, which is how a set becomes inconsistent one view at a
time.

Each combination binds: scale · model view options · layer combination · pen set · graphic override
combination · renovation filter · dimension style · view range.

| Combination | Scale | Detail | Overrides |
|---|---|---|---|
| `GA PLAN 1:100 ISSUE` | 1:100 | Medium | Cut = `T3` poché, no pattern |
| `GA PLAN 1:50 ISSUE` | 1:50 | Detailed | Single pattern per element |
| `SECTION 1:100 ISSUE` | 1:100 | Medium | Background at `T1` / pen 12 |
| `DETAIL 1:5 ISSUE` | 1:5 | Detailed | Layers with patterns, W2 outlines |
| `RCP 1:100 ISSUE` | 1:100 | Medium | Reflected; grid labels unmirrored |
| `COORDINATION` | any | Medium | Discipline colours, screen pen set |

### 2.5 Graphic overrides

Appearance is a **function of data**, expressed as override rules driven by classification and
properties. Per-element overrides are prohibited and are detectable.

| Rule | Criterion | Effect |
|---|---|---|
| `Existing to remain` | Renovation status | Pen group 1, fill `T1` |
| `To be demolished` | Renovation status | Pen group 3, dashed |
| `Other discipline` | Classification ≠ architectural | Pen group 4, fill `T1` |
| `Cut structure` | Structural function + cut | Fill `T3`, pen 06 |
| `Cut non-structure` | Non-structural + cut | Fill `T1`, pen 06 |

If an appearance rule cannot be written as a query over the model, either the model is missing data
or the convention is arbitrary. Both are defects, and this is the point at which they surface.

### 2.6 Hatches, favorites, publisher

**Hatches** are defined in *sheet* units, not model units, except for real coursing at 1:20 and
larger. A hatch defined in model units conforms at one scale and fails at every other. Minimum
printed pitch 0.5 mm and ≥ line width + 0.30 mm.

**Favorites** carry every element type in the practice library. Placement-time configuration is how
non-standard types proliferate, each one then needing a schedule row, a clause and a graphic rule
nobody wrote.

**Publisher sets**, one per package, with saved format and naming rules:

```
<container_id>-<status>-<revision>.pdf
2317-JKA-ZZ-02-DR-A-3104-A1-C03.pdf
```

Output: PDF, vector, fonts embedded, no rasterisation, page size = sheet size, no scaling. One
publisher run produces the whole package; per-sheet export produces silent variation.

---

## 3 InDesign

Build order: document presets → master pages → baseline grid → paragraph and character styles →
object and table styles → text variables → export presets.

### 3.1 Document setup

| Setting | Sheet templates | Document templates | Board |
|---|---|---|---|
| Page size | Per format | 210 × 297 | 841 × 594 |
| Facing pages | Off | Off | Off |
| Margins | 20 / 10 / 10 / 10 | T 25 · B 17 · L 20 · R 40 | 35 |
| Columns | Per §4.4 table, gutter 10 | 2 uneven, set as guides | 6, gutter 10 |
| Bleed | 0 | 0 | 0 |
| Units | Millimetres | Millimetres | Millimetres |

Bleed is zero throughout. Nothing in this system bleeds, so a bleed setting can only produce a
misregistered edge.

### 3.2 Baseline grid

```
Start:              30 mm from top of page       (A4; = first baseline)
Relative to:        Top of page
Increment every:    5 mm
View threshold:     75 %
Colour:             light grey, non-printing
```

Every text frame has *Align to Baseline Grid* enabled on its body paragraph styles. Snap-to-document
grid at 5 mm; guides at every column boundary.

### 3.3 Style naming

A flat, sortable, self-documenting scheme. The prefix is the size token, so the style list sorts
into the type scale and a wrong style is visible in the panel.

```
PTS / Text /
  t1 legal
  t2 body
  t2 body first          (no space before)
  t2 label caps
  t2 mono id
  t3 heading block
  t3 view title
  t4 heading section
  t4 sheet title
  t5 sheet number
  t6 document title
  t7 project title
  t8 board title

PTS / Table /
  th header
  td text
  td number
  td number decimal
  td empty                (renders "—")

PTS / Char /
  small caps label
  italic term
  mono inline
  revision code
```

Every paragraph style sets: font, size, exact leading, alignment left, hyphenation off, space before
and after in whole 5 mm increments, align to baseline grid, and a *Next Style*. Setting *Next Style*
correctly on every heading is what makes the templates fast to use.

### 3.4 Object and table styles

| Style | Definition |
|---|---|
| `PTS / Obj / view frame` | No stroke, no fill, text wrap off, anchored to column boundaries |
| `PTS / Obj / image` | No stroke, no effects, fitting = fill frame proportionally, alignment to lattice |
| `PTS / Obj / rule hairline` | 0.18 mm stroke, `T5`, no fill |
| `PTS / Table / schedule` | No vertical strokes; horizontal stroke 0.18 mm at group boundaries only; header row fill `T1`; row height exactly 5 mm; cell insets 1.25 mm left and right, 0 top and bottom |

Cell inset 1.25 mm is the text clear zone at `t2` — half a cap height. It is not a stylistic
decision; it is the crowding threshold.

### 3.5 Text variables and master pages

Text variables carry every field that repeats: project name, project code, container ID, revision,
status, issue date, page number, page count. A field typed into a text frame is a hand-maintained
copy and will eventually be wrong.

| Master | Contents |
|---|---|
| `A-Document` | Header strip, hairlines, footer with variables, marginal column guide |
| `B-Document first` | As A, plus the page-1 data block frame |
| `C-Schedule A3` | Sheet frame, TB-S, table frame in `Z-DRAW` |
| `D-Board` | Board frame, 6-column guides, TB-B |

### 3.6 Export presets

| Preset | Use | Settings |
|---|---|---|
| `PTS Issue` | Every issued PDF | Vector; fonts embedded as subsets; images ≥ 600 ppi, no downsampling below it; no colour conversion; page size = document size; no scaling; marks off; layers exported where discipline layers are useful |
| `PTS Archive` | Archive copy | PDF/A-2b; all of the above; metadata populated |
| `PTS Greyscale check` | QA only | Convert to greyscale, then re-run the readability checks |

The greyscale preset is not optional housekeeping. It is the check that proves the set is
monochrome-first, and it is run before every issue.

---

## 4 Word

Word is the weakest of the three tools for this system and is used only where the recipient needs an
editable document: minutes, site reports, RFIs, transmittals. Three constraints cannot be met and
are stated rather than pretended away.

| Constraint | Status in Word | Mitigation |
|---|---|---|
| 5 mm baseline grid | Not supported | Set every paragraph to exact line spacing 14.2 pt and space-before/after in multiples of 14.2 pt; the grid holds within a page |
| Marginal column | No true side-column | Use a two-column borderless table for the page body, 25 mm + 120 mm, header row repeated |
| Optical alignment | Not available | Accept; the deviation is below the perceptual threshold at these sizes |

### 4.1 Page setup

| Setting | Value |
|---|---|
| Paper | A4 |
| Margins | Top 25 · Bottom 17 · Left 20 · Right 40 mm |
| Header from edge | 15 mm |
| Footer from edge | 17 mm |
| Different first page | On |

### 4.2 Styles

Word styles use the same names as InDesign, so that content moves between them without
reinterpretation. Build them by **modifying the built-in styles** where an equivalent exists —
`Normal`, `Heading 1`–`Heading 3` — because Word's automatic features attach to the built-ins.

| PTS style | Word base | Font | Size | Line spacing | Space before / after |
|---|---|---|---|---|---|
| `t2 body` | Normal | Fallback family | 10 pt | Exactly 14.2 pt | 0 / 14.2 pt |
| `t3 heading block` | Heading 3 | Medium | 14 pt | Exactly 28.35 pt | 28.35 / 14.2 pt |
| `t4 heading section` | Heading 2 | Medium | 19.5 pt | Exactly 28.35 pt | 56.7 / 14.2 pt |
| `t2 label caps` | Character style | Regular, small caps, +2 % tracking | 10 pt | — | — |
| `t2 mono id` | Character style | Monospace | 10 pt | — | — |
| `t1 legal` | Paragraph | Regular | 7 pt | Exactly 14.2 pt | 0 / 0 |

Set every style to *left aligned*, *no hyphenation*, *widow/orphan control on*, *keep with next* on
all headings. Turn off *AutoFormat as you type* in the template: it introduces smart quotes,
automatic lists and hyperlink formatting that break the style system.

### 4.3 Fields, not typing

| Field | Word mechanism |
|---|---|
| Project name, code, client | Document properties, inserted as `DocProperty` fields |
| Container ID, revision, status | Custom document properties |
| Date of issue | Custom property, **not** `DATE` — an automatic date changes every time the file is opened, which silently rewrites the record |
| Page number | `PAGE` / `NUMPAGES`, formatted `Page n / m` |

Lock the document with *Restrict Editing → filling in forms* for templates issued to third parties,
so that the apparatus cannot be edited while the content can.

### 4.4 Tables

Schedules in Word use a table with: no borders except a 0.18 pt rule at group boundaries; header row
repeated on every page; *Allow row to break across pages* off; exact row height 5 mm; cell margins
1.25 mm left and right, 0 top and bottom; text left, integers right, decimals right with a tab stop
on the separator.

### 4.5 Export

Export to PDF via *Save as PDF → Standard*, with *Document structure tags* on and *ISO 19005-1
compliant (PDF/A)* on for archive copies. Never print to PDF: the print driver rasterises and
strips structure, which loses text extraction and fails the accessibility checks.

---

## 5 Build order and rollout

Each phase makes the next cheaper. Building them out of order wastes most of the effort.

| Phase | Weeks | Deliverable | Proven by |
|---|---|---|---|
| 1 | 1–2 | Typeface calibration; token file; pen sets | A test sheet printed at A1 and A3, measured |
| 2 | 2–4 | Archicad master layouts and title block object, all four formats | Title block fields all bound, none typed |
| 3 | 4–6 | View settings and graphic override rules | Zero per-element overrides in a test project |
| 4 | 6–8 | InDesign document and board templates, style sheets | A4 specification and A1 board built from styles alone |
| 5 | 8–10 | Word templates for minutes, site report, RFI, transmittal | Round-trip on a recipient machine with the fallback font |
| 6 | 10–12 | Publisher sets, export presets, naming | One-run publication of a full test package |
| 7 | 12+ | Validation configuration wired to the checks | Automated gate blocking on a seeded defect |

### 5.1 Acceptance test

The templates are accepted when a full test package passes, at the nominated issue size, on the
degraded render:

| Check | Threshold |
|---|---|
| Minimum cap height | ≥ 2.5 mm |
| Minimum stroke width | ≥ 0.18 mm |
| Text clear-zone violations | 0 |
| Zone origin variance across the set | 0 mm |
| Title block field position variance | 0 mm |
| Distinct line widths per sheet | ≤ 5 |
| Distinct type sizes per sheet | ≤ 5 |
| Distinct tones per sheet | ≤ 4 |
| Typed title block fields | 0 |
| Per-element graphic overrides | 0 |
| Views without a view setting | 0 |
| Fill ratio | 0.40–0.85 |
| Local ink coverage, 20 mm window | ≤ 0.25 |
| Greyscale render passes all of the above | pass |
| Orientation test: type, location, scale identified | ≤ 5 s, 100 % correct |

The orientation test is run with a person who has not seen the sheet. It is the only check in the
list that measures the thing the whole system exists for, and it takes ninety seconds.

### 5.2 Maintenance

One named owner. Changes to the templates go through the same route as changes to the standard:
observed failure → proposed change → impact check against the token file → validation → publication
with a revision note. A template edited on a project is a fork, and a fork is how a system dies.

---

*Return to [Part 1 — The System](PTS-01-System.md) · [Part 2 — Templates](PTS-02-Templates.md).*
