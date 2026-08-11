# Practice Template System — Part 2: Template Specifications

**PTS 1.0 · Twelve templates.**

Each template is specified in fourteen fields. Where a field says *family default*, the value is
inherited unchanged from [Part 1](PTS-01-System.md) and is not repeated; only overrides and
additions are stated. This is the point of the system: a template is a short list of differences,
not a fresh design.

**Family defaults, for reference**

| Field | Sheet family | Document family | Board family |
|---|---|---|---|
| Format | A1 landscape (A0/A2/A3 per §4.4) | A4 portrait | A1 landscape |
| Margins | 20 binding / 10 others | 20 L / 40 R / 25 T / 17 B | 35 all round |
| Grid | Per §4.4 table | 25 marginal + 5 + 120 text | 6 × 120, gutter 10 |
| Lattice | 5 mm | 5 mm | 5 mm |
| Body type | `t2` 2.5 mm | `t2` 2.5 mm | `t5` 7 mm |
| Title block | TB-L (A0/A1) · TB-S (A2/A3) | TB-D | TB-B |
| Footer | Within title block | Hairline y272, baseline y280 | Foot strip |
| Numbering | Sheet number, no page number | `Page n / m` | Board `n / m` |
| Revision | Register in `Z-REV` + clouds | Bar in marginal column | Revision code only |
| Icons | ADOS 30-symbol set on drawings | None | North point only |

---

## T01 · Cover Sheet

**Purpose.** Identify the set, state the terms on which it may be used, and provide the entry point
to everything else. It is the only sheet whose content is entirely metadata.

**Required information.**

1. Project name, project code, site address
2. Client name
3. Set title and package identifier
4. Status code and status name, at `t6` (10 mm)
5. Issue date and revision
6. Originator: name, address, responsible individual, contact
7. Consultant list with disciplines and originator codes
8. Standards conformance claim, with edition and class
9. Declared units, decimal separator, primary language
10. Declared smallest nominated issue size
11. North orientation statement and datum statement
12. Reference to the drawing register
13. Copyright and confidentiality statement
14. Do-not-scale statement

**Optional information.** One locator image (site aerial or single elevation) at ≤ 30 % of sheet
area, labelled with source and date; stage or programme statement; statutory approval references.

**Information hierarchy.** L0 project name · L1 status · L2 set title, originator · L3
declarations, consultants, legal.

Status sits at L1, above the set title, because the first question any recipient asks is not *what
is this* but *may I build from it*.

**Layout structure.** The cover is the only sheet where `Z-DRAW` carries no views. It is divided
into three horizontal bands separated by 40 mm, the major-part spacing:

```
band 1   top third      identity: project name t7 · code · client · address
band 2   middle third   set title t6 · status t6 · package · issue date · revision
band 3   bottom third   consultants (left column) · declarations (right column) · legal t1
```

Bands are ranged left to the first column boundary. Nothing is centred: centring gives the eye no
constant edge to return to.

**Grid.** Family default. Bands span the full drawing area width; within band 3, consultants occupy
columns 1–3 and declarations columns 4–6.
**Margins.** Family default.
**Typography.** `t7` project name · `t6` set title and status · `t3` band headings · `t2`
declarations and consultant list · `t1` legal line.
**Title block.** TB-L, in its normal position and unchanged — this is the one element the cover
shares with every other sheet, so that a cover found in a stack is identifiable by the same corner.
**Footer.** Within the title block.
**Page numbering.** None. The cover carries the set's container ID.
**Revision handling.** The cover carries the *package* revision, and its status equals the **lowest**
status of any container in the package. A cover claiming `A1` over a package containing a
preliminary drawing invites construction from preliminary information.
**White space.** The cover is the calmest sheet in the set and should look almost empty. Target fill
ratio 0.25–0.45 — deliberately below the sheet floor, because the cover's content is genuinely
small and padding it would be decoration.
**Icons.** None.

---

## T02 · Project Information Sheet

**Purpose.** Carry, once, every project-wide convention and declaration, so that no other document
restates them and no convention is left implicit.

**Required information.**

1. Project directory: every party, role, contact, originator code
2. Site information: address, parcel identifier, boundaries reference, survey reference and date
3. Datum: project datum value and its relation to the national datum
4. Coordinate system and the setting-out origin, in both project and national coordinates
5. Grid convention statement
6. Units, precision, decimal separator, angle notation
7. Dimension reference-face convention
8. Level type prefixes and dimension provenance tokens
9. Abbreviation list, complete for this set
10. The encoding table as a printed legend: line tiers, line types, tones, hatches, symbols, each
    graphic shown at actual printed size
11. Phase encoding legend
12. General notes, numbered, grouped, ≤ 25 words each
13. Standards to which the set conforms
14. Statutory and health-and-safety notes required by the jurisdiction

**Optional information.** Classification system reference; BIM execution plan reference; materials
palette reference.

**Information hierarchy.** L1 block headings · L2 legend graphics and declaration values · L3 note
text.

Legend graphics are the search key and sit in the left column of each legend pair; the reader
arrives holding the graphic and needs the meaning.

**Layout structure.** Six columns, each block occupying a whole number of columns, blocks ordered by
frequency of consultation: legends first (consulted constantly), declarations second, directory
third, general notes last.

**Grid.** Family default. Legend pairs: graphic in a 20 mm sub-column, meaning in the remainder.
**Margins.** Family default.
**Typography.** `t3` block headings · `t2` everything else · `t1` nothing.
**Title block.** TB-L.
**Footer.** Within the title block.
**Page numbering.** None; continues as `A0.011`, `A0.012` if it exceeds one sheet.
**Revision handling.** Standard register. A change here affects the whole set, so the revision
description names the convention changed, and the transmittal flags it as a set-wide change.
**White space.** 10 mm between legend entries, 20 mm between blocks. Legends are read by scanning a
column; constant pitch matters more here than on any other sheet.
**Icons.** This sheet *defines* the symbol set. It shows every symbol at actual printed size, which
is the only place in the set where a symbol appears without carrying meaning.

---

## T03 · Drawing Sheet — Plans, Sections, Elevations

**Purpose.** Show the location and identity of every element of one level or one view direction, and
provide the reference frame from which all other information about it is located.

**Required information.**

| # | Content | Encoding |
|---|---|---|
| 1 | Elements cut by the cut plane | W3 |
| 2 | Elements seen in front of the cut plane | W2 |
| 3 | Elements above / beyond / hidden | W1, dashed or dotted |
| 4 | Setting-out grid, bubbles at both ends | `L-CENT` W1, 10 mm bubbles |
| 5 | Room tags: number and name | `t2` |
| 6 | Door and window marks | `t2` |
| 7 | Assembly type marks, at every run and every change | `t2` |
| 8 | Levels at every change, with type prefix and signed value | `t2` |
| 9 | Three closed dimension chains per side | `t2`, offsets 10 / 20 / 30 |
| 10 | Section, elevation and detail markers | 20 mm bubbles |
| 11 | North point (plans) | ≥ 15 mm |
| 12 | Cut plane height statement (plans) | `t2` |
| 13 | Stair and ramp direction, going, rise, up/down | `t2` |
| 14 | Ground lines existing and proposed, with levels (sections, elevations) | phase encoded |
| 15 | Match lines with overlap, where the view is split | 1.00 mm dashed |
| 16 | Scope statement and read-with list | `Z-NOTES` |

**Optional information.** Fixed furniture where it affects compliance; loose furniture only if
contracted, and then at `T1`; fire compartment lines only on Class C projects where no separate
strategy drawing exists.

**Information hierarchy.** L0 sheet number · L1 view title · L2 cut elements → grid → room tags →
seen elements → dimensions → marks → elements above · L3 notes.

**Layout structure.** Primary view in the upper-left of `Z-DRAW` (initial fixation lands there),
secondary views left-to-right then top-to-bottom. Dimension chains outside the building envelope on
all four sides; internal chains only for elements that cannot reference an external chain.

**Grid.** Family default; each view's bounding box aligns to column boundaries.
**Margins.** Family default. View-to-view separation ≥ 20 mm; view-to-boundary ≥ 10 mm.
**Typography.** `t3` view titles and grid labels · `t2` all annotation · `t1` nothing.
**Title block.** TB-L. Scale field states the view scale, or `AS SHOWN` where views differ — in which
case each view carries its own scale at `t3` beside its title, plus a graphic scale bar.
**Footer.** Within the title block.
**Page numbering.** None. The sheet number is the address.
**Revision handling.** Register in `Z-REV`, newest at top, growing upward, minimum six visible rows,
each row carrying code · date · description · author · checker. Changed areas clouded and tagged
with the current revision code. **Clouds from superseded revisions are removed** — after three
revisions a sheet that keeps them is uniformly clouded and the current change is invisible.
Descriptions state what changed and where, in ≤ 20 words, with a grid or room reference. Generic
descriptions are a defect.
**White space.** 20 mm between views; 10 mm between annotation clusters; 5 mm within a cluster. Fill
ratio 0.40–0.85.
**Icons.** ADOS symbol set only: north point, grid bubble, section, detail and elevation markers,
level symbols, door swing, stair direction, match line, scale bar.

---

## T04 · Detail Drawing Sheet

**Purpose.** Resolve a junction to the point where it can be built, coordinated and priced without
further interpretation.

**Required information.**

1. The junction at 1:10, 1:5, 1:2 or 1:1
2. Context: ≥ 100 mm real extent beyond the junction, and at least one recognisable datum
3. Every material layer annotated **by reference**, never described
4. Dimensions that must be set out: cavity widths, upstand heights, laps, overlaps
5. Levels at every change
6. Fixing and support: type, spacing, specification reference
7. Movement provision: joint width and the movement accommodated
8. **Continuity lines** — water, air, vapour, thermal, fire — each drawn continuously across the
   detail and either explicitly connected or explicitly terminated with a reference to where it
   continues
9. Tolerance where it differs from the general tolerance
10. Typical applicability statement, or specific location
11. View title: identifier bubble · title · scale · applicability
12. Reciprocal *referenced from* list

**Optional information.** Assembly sequence; photographic reference to a mock-up.

**Information hierarchy.** L0 sheet number · L1 detail identifier and title · L2 cut elements →
continuity lines → dimensions → layer references · L3 context, notes.

Continuity lines rank above dimensions. Envelope failures are overwhelmingly continuity failures at
junctions, and a detail that shows the materials but not the continuity has not answered the
question it exists to answer.

**Layout structure.** Details arranged by their position in the building — ground up, outside in —
so that a reader following the envelope from foundation to parapet finds them in order. Each detail
occupies a whole number of grid columns. Drawn in built orientation; never rotated to fit.

**Grid.** Family default. At A1, 6 × 95 mm suits details at 1:5; at A3, 4 × 90 mm suits two details
per row.
**Margins.** Family default.
**Typography.** `t3` detail titles · `t2` all annotation.
**Title block.** TB-L or TB-S. Scale field reads `AS SHOWN`; each detail carries its own scale.
**Footer.** Within the title block.
**Page numbering.** None.
**Revision handling.** Standard register and clouding. Additionally, because details are reused, the
revision description states whether the change affects the typical condition or one location — the
distinction determines how many other sheets are affected.
**White space.** 20 mm between details; the annotation of one detail never enters the 20 mm belt of
the next. Detail sheets are the densest in the set and the belt is what keeps them readable.
**Icons.** Break line, level symbol, detail identifier bubble, north point where the detail is
orientation-dependent.

---

## T05 · Specification Sheet

**Purpose.** Carry, authoritatively, every requirement of materials, workmanship, performance and
testing that is not a geometric fact.

**Required information.**

1. Section number and title, decimal, ≤ 4 levels
2. Scope of the section and its interfaces with other sections
3. Clauses, individually numbered so that each is citable from a drawing
4. Each product declared **performance** or **prescription** — the declaration allocates design
   responsibility and its absence is the origin of most specification disputes
5. Execution: preparation, installation, tolerance, protection
6. Completion: testing, commissioning, records, warranties
7. Every standard cited with number, year and title; undated citations are prohibited
8. Running head: project · container ID · section title
9. Footer: container ID · revision · status · `Page n / m`

**Optional information.** Samples and mock-up schedule; test schedule; sustainability requirements.

**Information hierarchy.** L1 section heading · L2 clause group headings · L3 clause text · marginal
column: clause numbers.

**Layout structure.** Document family. Clause numbers sit in the 25 mm marginal column, not in the
text column — so the text edge stays straight and the numbers form a scannable vertical index.

**Grid.** Document default: 25 marginal + 5 gutter + 120 text. One column only; a specification is
read linearly.
**Margins.** Document default.
**Typography.** `t4` section headings · `t3` clause group headings · `t2` body and clause numbers ·
italic for defined terms on first use · small capitals for cross-referenced section names.
**Title block.** TB-D.
**Footer.** Hairline at y 272; baseline y 280: container ID · revision · status at left, `Page n / m`
at right.
**Page numbering.** `Page n / m`, right-aligned, on every page including the first.
**Revision handling.** Vertical revision bar in the marginal column beside changed text, carrying
the revision code. Bars from superseded revisions are removed. A revision table on page 1 lists
code · date · sections affected · author.
**White space.** One baseline (5 mm) between paragraphs, no indent. Two baselines (10 mm) before a
clause group heading, one after. Four baselines (20 mm) before a section heading. Headings are never
orphaned: a heading with fewer than three following lines moves to the next page.
**Icons.** None.

---

## T06 · Door / Window Schedule

**Purpose.** Carry every fact about every door and window, as the single source for procurement,
manufacture, certification and installation.

**Required information — per door.** Mark · location (room from, room to, level, grid) · type
reference · structural opening · **finished clear opening width and height** · leaf size and
thickness · handing · frame type and material · fire rating and smoke control · acoustic
requirement · security rating · ironmongery set reference · glazing reference and vision panel
position · threshold reference · accessibility data (opening force, clear width) · signage
reference · specification clause · elevation reference where non-standard.

**Required information — per window.** Mark · location · type reference and elevation reference ·
structural opening · frame and glazing sizes · cill and head levels relative to FFL and to datum ·
opening lights, method, restrictors and **free opening area** · glazing specification reference ·
frame material and finish · thermal transmittance requirement · ventilation provision and the
requirement it satisfies · fall protection where the cill is low · cleaning access reference ·
fire performance where applicable · specification clause.

Clear opening width and free opening area are singled out because neither is derivable from the
leaf size, and both are the quantity a code is checked against. Their omission is the most common
defect in schedules that otherwise look complete.

**Optional information.** Access control zone; closer power size; ventilation undercut; supplier
reference after procurement.

**Information hierarchy.** L1 column headers · L2 mark column · L3 data cells.

The mark column is leftmost because it is the search key and must be scannable in one vertical pass.

**Layout structure.** A sheet whose single view is a table. A3 landscape, small-format template, the
table occupying `Z-DRAW` (390 × 202). Header row 10 mm, data rows 5 mm → **38 rows per sheet**.
Where the column count exceeds twelve, the schedule splits into *identity, size, performance* and
*ironmongery, finishes, accessories*, sharing the mark as key. Columns are never hidden to fit.

**Grid.** Table columns on the 5 mm lattice; row pitch constant at 5 mm; group rule every 10 rows.
**Margins.** Sheet family default.
**Typography.** `t3` bold column headers on a `T1` band · `t2` cells · tabular figures throughout ·
text left-aligned, integers right-aligned, decimals aligned on the separator.
**Title block.** TB-S.
**Footer.** Within the title block. Continuation sheets repeat the header row and carry
`continued` markers at the break.
**Page numbering.** Sheet numbers within the `8` series; a multi-sheet schedule reads
`A8.010`, `A8.011`.
**Revision handling.** A revision column at the right of each row carrying the code in which that row
last changed. This is more useful than clouding on a table: it lets a supplier diff the schedule
against the copy they already priced.
**White space.** **No vertical rules.** Columns are separated by a 5 mm gap; the 2:1 rule groups
related columns at 10 mm. Horizontal rules only at group boundaries. A gridded table reads as a
grid; a spaced table reads as data. Empty cells are prohibited: every cell carries a value, `—`,
`TBC` with a hold reference, or `SEE <ref>`.
**Icons.** None. Handing is shown by a diagram in the header block defining the convention, once.

---

## T07 · Meeting Minutes

**Purpose.** Record decisions and actions so that the project has one authoritative account of what
was agreed.

**Required information.**

1. Meeting series, number, date, time, location or platform
2. Attendees, apologies, distribution list
3. Reference to the previous minutes and confirmation of acceptance
4. Items, each with a **persistent number** carried forward until closed, each recording:
   discussion in one or two sentences · **decision** (or `no decision`) · **action** · **owner** ·
   **due date**
5. Actions carried forward, with status
6. Decisions register: decisions taken at this meeting, listed separately
7. Next meeting details

**Optional information.** Attachments list; photographs keyed to items.

**Information hierarchy.** L1 agenda section headings · L2 item text · L3 owner and date.

**Layout structure.** Document family with the text column subdivided: item number in the marginal
column, discussion and decision in a 90 mm sub-column, owner and due date in a 30 mm right
sub-column ranged right.

```
│ 4.12 │ Rooflight upstand height to be confirmed against   │ MT   │
│      │ the parapet detail.                                │ 21-03│
│      │ DECISION  Upstand raised to 300 above finished     │      │
│      │ roof level.                                        │      │
│      │ ACTION    Revise A7.020 and reissue.               │      │
```

Owner and date range right in their own column so that a reader scans one vertical strip for their
own name. That is how minutes are actually read, and it is the only reason for this layout.

**Grid.** Document default, text column split 90 + 5 + 25.
**Margins.** Document default.
**Typography.** `t3` section headings · `t2` body · `DECISION` and `ACTION` in small capitals, not
bold — they are labels, and bold is reserved for the single declared structural role.
**Title block.** TB-D. Page 1 carries the full meeting data block.
**Footer.** Document default.
**Page numbering.** `Page n / m`.
**Revision handling.** Minutes are not revised. An error is corrected in the next set of minutes as a
numbered item. Minutes **never instruct a change to the works**: where a decision requires a change,
an instruction is issued and the minute references it.
**White space.** One baseline between items within a section; two between sections. Items never
break across a page.
**Icons.** None.

---

## T08 · Site Visit Report

**Purpose.** Record the observed state of the works at a point in time, against the documented
design.

**Required information.**

1. Report number, date, time, weather, inspector
2. Purpose of the visit and the scope inspected
3. **What was not inspected, and why** — an inspection record silent on its limits will be read as
   covering everything
4. Progress observed against the programme, by area
5. Observations, each with: location (grid, level, room) · the documented requirement **with its
   container and clause reference** · the observed condition · assessment
   (`conforming` / `non-conforming` / `cannot determine`)
6. Photographs, numbered, located, dated, referenced from the observation
7. Actions with owners and dates
8. Items closed since the previous report

**Optional information.** Weather record affecting the works; delivery record; labour count.

**Information hierarchy.** L1 section headings · L2 observation blocks · L3 photograph captions.

**Layout structure.** Document family. Each observation is a self-contained block in a fixed field
order, so that a reader following up months later can reconstruct the situation without the
inspector:

```
│ 07  │ LOCATION      Level 02, grid C/4, room 2.14        │
│     │ REQUIREMENT   A7.014/D3 · Spec 25.4.2              │
│     │ OBSERVED      Cavity barrier omitted at the head   │
│     │               of the opening.                      │
│     │ ASSESSMENT    NON-CONFORMING                        │
│     │ ACTION        Install and notify for inspection.    │
│     │               JS · 2026-03-21                       │
│     │ PHOTO         07-01, 07-02                          │
```

**Grid.** Document default; label column 25 mm inside the text column, content 95 mm.
**Margins.** Document default.
**Typography.** `t2` throughout; field labels in small capitals; `NON-CONFORMING` in medium weight —
this is the declared structural role of bold in this template.
**Title block.** TB-D.
**Footer.** Document default.
**Page numbering.** `Page n / m`. Photographs are an appendix with their own continuous numbering.
**Revision handling.** Reports are not revised; each is a dated record. A superseded observation is
closed in a later report, not edited.
**White space.** Two baselines between observations. Photographs sized to the text column width or
half of it; two per row; captions one baseline below; never bordered.
**Icons.** None. Assessment is a word.

---

## T09 · Request for Information (RFI)

**Purpose.** Obtain a decision the issued documentation does not provide, and record it.

**Required information.**

1. RFI number, project-unique and sequential; revision
2. Date raised; date response required, with the justification for that date
3. Raiser and responder
4. Subject and location: container reference, grid, level, room
5. **One question**, stated as a question
6. Context: what the documentation currently says, and why it is insufficient
7. The raiser's proposed answer, where they have one
8. Cost and programme implication as assessed by the raiser
9. Response, with author and date
10. Consequence: containers to be revised, instructions to be issued
11. Status: open · answered · closed

**Optional information.** Sketch, marked as `SK` and not to scale; references to related RFIs.

**Information hierarchy.** L1 the question · L2 context and response · L3 administration.

The question is the largest text on the page, at `t4`. Everything else is apparatus. An RFI whose
question has to be extracted from a paragraph gets an answer to a different question.

**Layout structure.** One page, one question. Administration in a fixed block at the head; question
and context on the upper half; response block on the lower half, left blank at issue.

**Grid.** Document default. The administration block is a two-column list: label 40 mm, value 80 mm.
**Margins.** Document default.
**Typography.** `t4` the question · `t2` everything else · labels in small capitals.
**Title block.** TB-D.
**Footer.** Document default, plus the RFI status at the left.
**Page numbering.** `Page n / m`. Attachments are referenced, never embedded — an embedded drawing
becomes an uncontrolled copy with no supersession mechanism.
**Revision handling.** An RFI is revised only to clarify the question before it is answered; the
revision is recorded. **An RFI whose answer changes the documented design is not closed until the
affected containers have been revised and issued, and the RFI cites that revision.** Without this
rule the drawing and the built work diverge permanently: the next reader has the drawing, not the
RFI.
**White space.** The response block is deliberately generous — 60 mm of clear space. A cramped
response field produces one-line answers to questions that need three.
**Icons.** None.

---

## T10 · Revision Log

**Purpose.** State, for the whole set, what exists, at what revision, at what status, and what
changed at each issue — so that a recipient can determine whether they hold a complete and current
set.

**Required information.**

1. One row per container: container identifier · sheet number · title · type · size · current
   revision · status · date
2. **Issue matrix**: one column per issue date, each cell holding the revision issued at that date
3. Revision descriptions, per container per revision
4. Containers withdrawn since the previous issue, marked `WD`
5. Total container count
6. Generation timestamp and a statement that the log is machine-generated
7. External reference list: every document referenced by the set but not part of it, with
   identifier, title, version and source

**Optional information.** Level, zone, discipline and scale columns; hyperlinks in the digital
version.

**Information hierarchy.** L1 series group headings · L2 identity columns · L3 issue matrix cells.

**Layout structure.** A3 landscape sheet, table as view. Rows grouped by series with a group
heading, because that matches both the physical order of the set and the reader's mental model.
Identity columns fixed at the left; the issue matrix extends right and is the part that scrolls or
folds.

**Grid.** Row pitch 5 mm, 38 rows per sheet. Identity columns 130 mm; matrix columns 10 mm each,
26 issues per sheet.
**Margins.** Sheet family default.
**Typography.** `t3` group headings and column headers · `t2` rows · monospace for container
identifiers, so that a transposed character is visible.
**Title block.** TB-S.
**Footer.** Within the title block.
**Page numbering.** Sheet numbers within the `0` series.
**Revision handling.** The log is regenerated at every issue and carries its own revision. It is
**never maintained by hand** — a hand-maintained register is a duplicate of the set's own state and
diverges at exactly the moment it matters, which is a rushed issue.
**White space.** 5 mm rows, group rule every group, 10 mm between groups. No vertical rules; matrix
columns separated by 5 mm.
**Icons.** None. `WD` is a word.

---

## T11 · Transmittal Sheet

**Purpose.** Record what was sent, to whom, when, in what form, and what it supersedes.

**Required information.**

1. Transmittal number and date
2. Sender and recipient list, with roles
3. Reason for issue
4. One row per container: identifier · title · revision · status · size · format · copies
5. **Supersession instruction**: which container revisions are superseded and are to be withdrawn
   from use
6. Medium of transmission
7. Acknowledgement request and mechanism
8. Hold register update
9. Reference to the current revision log

**Optional information.** Distribution matrix where recipients receive different subsets; courier
or upload reference.

**Information hierarchy.** L1 reason for issue · L2 container table · L3 administration.

The reason for issue ranks above the container list because it determines how the recipient treats
everything below it.

**Layout structure.** A4 portrait, or A3 where the container list exceeds 38 rows. Recipients block
at the head; container table in the middle; supersession instruction immediately below the table,
never on a second page.

**Grid.** Document default; table columns on the lattice.
**Margins.** Document default.
**Typography.** `t3` reason for issue · `t2` table and administration · monospace for identifiers.
**Title block.** TB-D.
**Footer.** Document default.
**Page numbering.** `Page n / m`.
**Revision handling.** A transmittal is never revised. An error produces a new transmittal
referencing the first.
**White space.** 20 mm between the recipient block, the table and the supersession instruction. The
supersession instruction sits alone in its own band — it is the one part recipients skip, and space
is the only mechanism available to stop them.
**Icons.** None.

---

## T12 · Presentation Board

**Purpose.** Communicate the experience and intent of a design to an audience standing in front of
it.

**Required information.**

1. Board title and board number `n / m`
2. Project name and stage
3. **Status statement and the label `ILLUSTRATIVE — NOT A CONSTRUCTION DOCUMENT`**
4. Source and date of every image; a generated-image statement where applicable
5. A statement wherever an image depicts a condition that is not yet resolved
6. Scale and north for any orthographic drawing shown
7. Originator identity
8. Copyright statement

**Optional information.** Explanatory text ≤ 60 words per block; key plan; material references.

**Information hierarchy.** L0 board title · L1 section headings · L2 images · L3 captions and legal.

**Layout structure.** Six columns. Images align to column boundaries and to the 5 mm baseline
lattice. One idea per board. A board carrying three arguments carries none: at three metres, a
viewer reads one thing and walks on.

```
┌──────────────────────────────────────────────────────────────┐
│  BOARD TITLE                                     t8  20 mm   │  ← 40 mm band
├──────────┬──────────┬──────────┬──────────┬──────────┬───────┤
│          │          │          │          │          │       │
│     primary image, 4 columns              │  text    │ 2 col │
│                                           │  t5 7 mm │       │
├───────────────────────────────────────────┴──────────┴───────┤
│  secondary images, 2 columns each, 20 mm gaps                │
├──────────────────────────────────────────────────────────────┤
│  captions t5 · source and date t2      │  TB-B  180 × 40     │
└──────────────────────────────────────────────────────────────┘
```

**Grid.** 6 × 120 mm, gutter 10, frame 771 × 524, residual 1.
**Margins.** 35 mm all round. A board is pinned, not bound, so the margin is symmetric; asymmetry
would read as an error rather than as structure.
**Typography.** `t8` 20 mm board title · `t7` 14 mm section headings · `t5` 7 mm body — derived from
`h = d × 4.945 × 10⁻³` at 1.5 m and 3 m viewing. Sheet typography is unreadable on a board and board
typography is absurd on a sheet; this is why the board is a separate family.
**Title block.** TB-B, 180 × 40, bottom right: project · board number · status · originator ·
date · illustrative label.
**Footer.** Merged into TB-B.
**Page numbering.** Board `n / m`, at `t5`, in TB-B.
**Revision handling.** Revision code only; no register, no clouding. Boards are superseded whole.
**White space.** The board family permits, and expects, more space than any other template: target
fill 0.35–0.60. Images never bleed, never carry a border, never carry a shadow. A 20 mm gap between
image groups, 10 mm within a group.
**Icons.** North point on orthographic drawings. Nothing else.

**Segregation.** A presentation board is never included in a technical package and is never
referenced by a technical container as a source of requirement. A rendering in a construction
package will be built from. The honesty rules still apply in full: an unresolved condition is not
depicted as resolved, and an assumed existing condition is not depicted as surveyed.

---

## T13 · Site Survey Record

**Purpose.** Record the condition of a site and its existing fabric as established on a visit,
together with the method by which each fact was established, so that every drawing derived from it
can cite its provenance.

**Why this is a separate template from T08.** T08 records the works against a documented design and
assesses conformity. On a first visit no design exists, so there is nothing to assess against and an
assessment column would collect opinion in the shape of finding. T13 precedes the design and is its
factual origin.

**Why it exists at all.** `ADOS-2.2.010` names the **survey record** as the authoritative carrier
for site and existing-condition information. `ADOS-5.6.020` requires every existing-condition
drawing to state its survey method, date and accuracy. `ADOS-4.5.090` requires the `(S)` token on
every survey-derived dimension. Three rules depend on a document the standard's type registry
(`ADOS-5.0.010`) does not list — the practice cannot satisfy them without one. See *Coverage against
the standard* below.

**Required information.**

1. Record number, date, time on and off site, weather and light
2. Who was present, with their role, and who gave access
3. **Method register** — every method used, keyed, with the instrument and its stated accuracy in
   millimetres, and what it was applied to
4. **What was not established, and why**, with the consequence of assuming it
5. Findings, each with: location (level, grid or room, direction of view) · the finding · a
   **provenance token and method key** · the dimension where one was taken · the implication for the
   design, marked as the surveyor's judgement · photograph numbers
6. Photograph register: number, location, direction of view, subject, time
7. Declaration: the token legend, and the statement that anything unmarked was not established
8. Status of the record: `initial` · `supplemented by` · `superseded by`

**Provenance tokens.** A closed set of four. `(S)` established by measurement on this visit, by a
method in the register · `(D)` taken from an existing document, which is cited · `(R)` reported by a
named person · `(A)` assumed, with the basis stated.

`ADOS-4.5.090` defines `(S)` for dimensions. The other three exist because on a first visit most of
what is recorded is not measured, and the standard's own anti-pattern register calls an assumed
existing condition shown as surveyed the most expensive class of refurbishment failure (AP-28). A
token set with only `(S)` in it forces every unmeasured fact to be recorded as though measured, or
not recorded at all.

**Accuracy is stated per method, never once.** A record that mixes a laser distance meter, a tape
and a paced dimension has three accuracies. One blanket statement over all of them is false for two
of the three, and the reader cannot tell which. This is why the method register is a table with
keys, and why every dimension cites one.

**The limitation register comes before the findings.** `ADOS-5.31.020`: an inspection record silent
on its limits will be read as covering everything. On a first visit the roof void that could not be
opened is the risk the project carries, so it is read before the findings and not left to an
appendix. A page break closes the block, so the record always starts on a fresh page and the two
halves — the conditions of the survey, then the survey — are never interleaved.

The promise this template makes is about **sequence**, not about page position. Whether the opening
block happens to fill one page depends on how much the surveyor writes, and Word flows it. A
template cannot promise a page count for content it does not yet contain.

**Information hierarchy.** L1 section headings · L2 finding blocks · L3 photograph captions.

**Layout structure.** Document family. Each finding is a self-contained block in a fixed field
order:

```
│ 04  │ LOCATION      Level 02, room 2.14, viewed north     │
│     │ FINDING       Timber joists at 400 mm centres,      │
│     │               ends built into the north wall.       │
│     │ PROVENANCE    (S) M1 · joist ends (A) not exposed   │
│     │ DIMENSION     405 mm centres, mean of 6             │
│     │ IMPLICATION   Bearing condition to be opened up      │
│     │               before the structural scheme is fixed. │
│     │ PHOTO         04-01, 04-02                           │
```

`PROVENANCE` carries two tokens where the finding is part measured and part inferred, because that
is the common case and a single token would make the whole finding read as one or the other.

**Grid.** Document default; label column 25 mm inside the text column, content 95 mm — as T08, so
the two records read as one family.
**Margins.** Document default.
**Typography.** `t2` throughout; field labels in small capitals; method keys and provenance tokens
in the monospaced face, because they are identifiers and are read as such.
**Title block.** TB-D.
**Footer.** Document default.
**Page numbering.** `Page n / m`. Photographs are an appendix with their own continuous numbering.
**Revision handling.** A record is dated and is not revised. A later visit produces a new record
that supplements or supersedes it by number; the earlier record stays as it was written, because it
is evidence of what was known on that date.
**White space.** Two baselines between findings.
**Icons.** None. A provenance token is a token, not a symbol.

**What this template does not carry.** A sketch field. A first visit produces sketches, and a
sketch needs a ruled lattice to be dimensionable — which Word cannot draw without vertical rules
through a table, and vertical rules are the one thing the schedule rule forbids. The sketch belongs
on the printed field sheet (`T13F`, A3 landscape, PDF), whose lattice is the 5 mm sub-module of
`ADOS-3.3.030`, so that anything sketched on it is already on the standard's own placement grid.

---

## Coverage against the standard

| Template | ADOS type | Volume 5 chapter |
|---|---|---|
| T01 Cover Sheet | `CS` | 5.1 |
| T02 Project Information Sheet | `GN` | 5.3 |
| T03 Drawing Sheet | `GA-P` `EL` `SE` `RCP` `RP` | 5.4, 5.11–5.14 |
| T04 Detail Drawing Sheet | `DT` | 5.18 |
| T05 Specification Sheet | `SP-SPEC` | 5.22 |
| T06 Door / Window Schedule | `DS` `WS` | 5.20, 5.21 |
| T07 Meeting Minutes | `MM` | 5.29 |
| T08 Site Visit Report | `SR` | 5.31 |
| T09 RFI | `RFI` | 5.25 |
| T10 Revision Log | `IX` `RG` | 5.2 |
| T11 Transmittal Sheet | `CI` | 5.32 |
| T12 Presentation Board | `PR` | 5.28 |
| T13 Site Survey Record | *none — see below* | 5.6 (consumer), 5.31 (adjacent) |

Types in the standard that this template set does not yet cover, and that a full practice library
would add: setting-out plan (`SO`), existing and demolition (`EX` `DM`), fire and access strategy
(`FS` `AS`), assembly type sheets (`WT`), room and area schedules (`RS` `AR`), change instruction
(`CO`), as-built and O&M (`AB` `OM`). Each inherits an existing family and is a short list of
differences, exactly as above.

### A gap in the standard, recorded rather than papered over

**T13 has no ADOS type, and it should have one.** The type registry (`ADOS-5.0.010`) lists
thirty-four types. None of them is a survey record. Yet:

- `ADOS-2.2.010` binds the fact class *survey / existing condition* to the authoritative carrier
  **survey record**, and forbids any other document from restating its values;
- `ADOS-5.6.020` requires every existing-condition drawing to state its survey method, date and
  accuracy — a statement that has to come from somewhere;
- `ADOS-5.6` requires an explicit statement of areas not surveyed, with the reason;
- `ADOS-4.5.090` requires the `(S)` token on survey-derived dimensions, which is a reference to a
  survey that has to be identifiable.

A carrier that four rules depend on, that no type defines and no template produces, is a carrier
that gets improvised — which is the condition `ADOS-2.2.010` exists to end.

T13 is therefore defined here at the practice layer, as PTS is entitled to do, and its container
type code is left as the practice's local `SU` pending a standard amendment. The amendment this
points to is small: a row in the `ADOS-5.0.010` registry and a Volume 5 chapter of the same shape as
5.31. It is **not** made here, because amending the standard is a change-control act and not a
by-product of building a template.

---

*Continue to [Part 3 — Implementation](PTS-03-Implementation.md).*
