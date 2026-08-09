# PTS 1.0 — Word templates

Eight `.dotx` templates generated from [`../machine/pts-tokens.json`](../machine/pts-tokens.json).
Not hand-styled: a change to the system is a change to the token file and a rebuild.

```
python3 docs/templates/word/build.py      # writes templates/*.dotx
python3 docs/templates/word/verify.py     # 174 checks against the token file
```

## What is here

| File | PTS | Format |
|---|---|---|
| `PTS-T05-Specification.dotx` | T05 | A4 portrait |
| `PTS-T06a-Door-Schedule.dotx` | T06 | A3 landscape |
| `PTS-T06b-Window-Schedule.dotx` | T06 | A3 landscape |
| `PTS-T07-Meeting-Minutes.dotx` | T07 | A4 portrait |
| `PTS-T08-Site-Visit-Report.dotx` | T08 | A4 portrait |
| `PTS-T09-Request-for-Information.dotx` | T09 | A4 portrait |
| `PTS-T10-Revision-Log.dotx` | T10 | A3 landscape |
| `PTS-T11-Transmittal.dotx` | T11 | A4 portrait |

The door and window schedules are separate files because T06 splits a schedule that exceeds twelve
columns rather than hiding columns to fit.

## What is deliberately not here

`T01 Cover Sheet`, `T02 Project Information Sheet`, `T03 Drawing Sheet`, `T04 Detail Sheet` and
`T12 Presentation Board` are **not** Word templates and should not be made into them. They are
sheet- and board-family documents whose content is model-derived views at A1, positioned to the
millimetre against a drawn title block. Word can produce an A1 page, but it cannot place a block at
an absolute coordinate, cannot hold a view live against a model, and cannot carry line weights as a
depth encoding. Building them in Word would produce a document that looks like the system and
breaks every rule underneath it.

They are Archicad deliverables (drawings) and InDesign deliverables (cover, board). See
[`../PTS-03-Implementation.md`](../PTS-03-Implementation.md) §2 and §3. All five are drawn to true
printed size as PDFs in [`../pdf/`](../pdf/README.md), which is what an Archicad or InDesign
implementation should be measured against.

## Installing

**Windows** — copy the `.dotx` files to:
`%APPDATA%\Microsoft\Templates\`
They then appear under **File → New → Personal**.

**macOS** — copy them to:
`~/Library/Group Containers/UBF8T346G9.Office/User Content/Templates/`
They appear under **File → New from Template**.

Double-clicking a `.dotx` creates a new document from it rather than opening the template itself —
which is the point of shipping templates rather than documents. To edit a template, open Word first,
then **File → Open** and select it.

## Fonts

The templates specify **Inter** for text and **IBM Plex Mono** for identifiers. Both are free
(SIL Open Font Licence). **Install them before first use.** Word has no font-fallback chain: without
them a substitute is used, every measurement shifts, and the document is no longer the one that was
designed.

The font table declares `altName` substitutes — Arial for Inter, Consolas for IBM Plex Mono — so an
uninstalled face degrades to a sans rather than to a serif. That is damage limitation, not a
substitute for installing the fonts.

- Inter — https://rsms.me/inter/
- IBM Plex Mono — https://www.ibm.com/plex/

To swap in the practice's licensed family (PTS-01 §5.1 recommends Söhne), change `FONT` and
`FONT_MONO` at the top of `ptsword.py` and rebuild. Do not restyle by hand in Word: recalibrate the
point sizes against the new family's measured cap height first (PTS-03 §1.1), because the
cap-height-to-em ratio differs between families by up to 8 % and the point sizes are derived from
cap height, not chosen.

## Filling in a document

Every identity field — project, code, client, container ID, revision, status, date, author, checker,
approver — is a **field bound to a document property**, not typed text. Set them once per document:

1. **File → Info → Properties → Advanced Properties → Custom**
2. Edit the `PTS_*` values.
3. Back in the document, **Ctrl+A** then **F9** to refresh every field.

To make the refresh automatic on print: **File → Options → Display → Update fields before
printing**.

The point of this is not convenience. A typed title block field is a hand-maintained copy of a fact
held elsewhere, and it is the most frequently wrong content in any document set (PTS-01 §6.1).

## Styles

The style gallery contains the PTS set and nothing else. python-docx's default template ships 179
style definitions including blue headings and an 8 pt body style; the build strips them to 23 — the
PTS styles plus the six built-ins Word requires. A template that offers a style violating the system
will have that style used.

| Style | Use |
|---|---|
| `t2 body` | Body text. 10 pt, exact 14.2 pt leading |
| `t2 body tight` | Body with no space after, for consecutive lines |
| `t2 label caps` | Field labels, small capitals |
| `t2 mono id` | Clause numbers, container identifiers |
| `t3 heading block` | Block headings |
| `t4 heading section` | Document title and section headings |
| `t4 statement` | The RFI question — the largest text on its page |
| `t1 legal` | The closing note. The only style permitted below 2.5 mm cap |
| `th header` / `td text` / `td number` | Table header, text cell, numeric cell |
| `mono inline` / `italic term` / `small caps label` | Character styles |

Do not apply direct formatting. If a document needs something the styles do not offer, the system
needs a new style, not an override.

## What Word cannot do

Three constraints are stated rather than worked around (PTS-03 §4):

| Constraint | Handling |
|---|---|
| No baseline grid | Every paragraph carries exact line spacing in whole 5 mm multiples, so the rhythm holds within a page. It will not survive a mid-page image of arbitrary height. |
| No marginal column | The page body is a borderless two-cell table: 30 mm (25 marginal + 5 gutter) + 120 mm measure. Text starts at 50 mm from the page edge, as specified. |
| No optical alignment | Accepted. The deviation is below the perceptual threshold at these sizes. |

One further concession: schedule row heights use `atLeast` rather than `exact`. At `t2` the line box
is 14.2 pt and a 5 mm row is 14.17 pt, so an exact rule clips descenders by a third of a point.
`atLeast` holds the 5 mm pitch for single-line content — every row in a conforming schedule — and
grows rather than truncates if a cell wraps, so an overlong entry is visible instead of hidden.

## Verification

`verify.py` inspects the produced packages, not the code that wrote them, so a builder change that
silently drops a setting is caught.

| | Check |
|---|---|
| W1 | Valid `.dotx`: template content type, custom properties present |
| W2 | Page geometry matches the token file for its family |
| W3 | Every PTS style exists, at the token size, with exact line spacing on the 5 mm lattice |
| W4 | No text below the 2.5 mm cap-height floor |
| W5 | No typed identity: project, container, revision, status and page number are fields |
| W6 | No vertical rules; schedule header rows repeat |
| W7 | Table row pitch is a whole number of sub-modules |
| W8 | Header and footer hairlines at the W1 tier |
| W9 | Schedule column widths sum to the 390 mm frame |
| W10 | Monochrome, and every fill is a tone-ladder value |
| W11 | Every table declares a fixed width equal to the sum of its columns |
| W12 | Every cell carries an explicit width |
| W13 | Every style reference resolves to a styleId that exists |
| W14 | No right-aligned tab stops in header or footer |

Current state: **174 checks pass across 8 templates**, and all eight pass OOXML schema validation.

W11 to W14 exist because the first build passed every other check and still rendered wrongly. Three
defects were found only by looking at a rendered page:

| Defect | Cause | Now caught by |
|---|---|---|
| Every table collapsed to its content width | `w:tblW` left at `auto`/0, and no cell carried a width — `column.width` only reaches rows that exist, and the tables are built with `rows=0` | W11, W12 |
| Identifiers did not render monospace | `w:rStyle` referenced the style *name* (`mono inline`) instead of its styleId (`monoinline`), so the reference dangled | W13 |
| The container ID broke across two lines mid-identifier | A right-aligned tab stop the renderer did not honour; the header and footer are now fixed two-cell tables | W14 |

The lesson is recorded rather than tidied away: a structural check suite proves the values are
present, not that the page is right. Render a page and look at it.

## Language

The templates are English (`en-GB`), matching the specification. For a Hungarian set, change the
`w:lang` value in `ptsword.py`, translate the field labels in `build.py`, and rebuild — the geometry
is language-independent.
