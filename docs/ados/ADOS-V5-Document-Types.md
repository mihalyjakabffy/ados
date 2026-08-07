# Volume 5 — Document Types (Part A: Drawings)

**ADOS 1.0 · Volume 5 · Chapters 5.0–5.18.**
Part B (`ADOS-5.19` to `ADOS-5.34`: schedules, specifications, packages and project records) is
in [`ADOS-V5B-Document-Types.md`](ADOS-V5B-Document-Types.md).

---

## 5.0 How to read this volume

### 5.0.1 The document type template

Every document type is specified in the following eight fields.

| Field | Meaning |
|---|---|
| **Purpose** | The single sentence that justifies the document's existence. If two types share a purpose, one is redundant. |
| **Users** | Enumerated. Each user is listed with the question they bring. Content serving no listed user is noise (`ADOS-0.5.040`). |
| **Answers** | Which of the five questions (`ADOS-0.5.010`) this type is responsible for. |
| **Required content** | Normative. Absence is a completeness defect (`ADOS-8.4`). |
| **Optional content** | Permitted; included only when a listed user needs it on this project. |
| **Hierarchy** | The salience ordering the sheet shall present (`ADOS-3.6.010`). |
| **Layout logic** | Where things go and why. |
| **Quality checklist** | Binary checks, each with a validation ID, run before issue. |

### ADOS-5.0.010 — Type registry ⚠

**Purpose.** Make the set of permissible document types closed, so that "what kind of document is
this?" is always answerable and every container can be validated against a schema.

**Decision.** Every container shall declare a type from the registry in this volume. Ad-hoc
document types shall not be issued. A new type shall be added to the registry by the procedure in
`ADOS-1.11.010` before first use.

**Validation.** `V-5.0.010`: every container's `type` field resolves to a registry entry; unknown
types = 0.

### ADOS-5.0.020 — Universal sheet requirements ⚠

**Decision.** Every drawing sheet, of every type, shall satisfy the following. These are not
repeated in each type's required content.

| # | Requirement | Rule |
|---|---|---|
| 1 | Conforming zoning template | `ADOS-3.3.010` |
| 2 | Complete title block, all mandatory fields populated | `ADOS-3.9.020` |
| 3 | Status code, banner and watermark where applicable | `ADOS-2.6.010`, `ADOS-3.9.060` |
| 4 | Revision code and register | `ADOS-2.6.020`, `ADOS-2.6.030` |
| 5 | Scope statement in `Z-NOTES` | `ADOS-0.3.090`, `ADOS-3.3.070` |
| 6 | `Read with` list | `ADOS-2.8.020` |
| 7 | Legend covering every graphic state used | `ADOS-4.9.010` |
| 8 | Key plan where the view is partial | `ADOS-2.4.060` |
| 9 | Scale label per view and a graphic scale bar | `ADOS-3.9.040`, `ADOS-4.2.050` |
| 10 | Do-not-scale statement | `ADOS-3.9.050` |
| 11 | Reciprocal references resolved | `ADOS-2.4.030`, `ADOS-2.4.040` |
| 12 | Density within limits | `ADOS-3.7` |
| 13 | Readability at the nominated issue size | `ADOS-8.2` |

**Validation.** `V-5.0.020`: the universal checklist passes on every sheet.

### 5.0.2 Type registry summary

| Chapter | Type code | Name | Series | Part |
|---|---|---|---|---|
| 5.1 | `CS` | Cover Sheet | 0 | A |
| 5.2 | `IX` | Drawing Register / Index | 0 | A |
| 5.3 | `GN` | General Notes, Legends, Abbreviations | 0 | A |
| 5.4 | `GA-P` | General Arrangement Floor Plan | 3 | A |
| 5.5 | `SO` | Setting-Out Plan | 3 | A |
| 5.6 | `EX` / `DM` | Existing Condition / Demolition Plan | 1 | A |
| 5.7 | `PH` | Phasing Plan | 1 / 9 | A |
| 5.8 | `SL` / `SP` | Site Location Plan / Site Plan | 2 | A |
| 5.9 | `FS` | Fire Strategy Drawing | 9 | A |
| 5.10 | `AS` | Access and Inclusive Design Strategy | 9 | A |
| 5.11 | `RP` | Roof Plan | 3 | A |
| 5.12 | `RCP` | Reflected Ceiling Plan | 3 | A |
| 5.13 | `EL` | Elevation | 4 | A |
| 5.14 | `SE` | Section | 4 | A |
| 5.15 | `EN` / `IE` | Enlarged Plan / Interior Elevation | 5 | A |
| 5.16 | `WT` | Wall / Floor / Roof Type Sheet | 6 | A |
| 5.17 | `TS` | Type Schedule | 6 / 8 | A |
| 5.18 | `DT` | Detail | 7 | A |
| 5.19 | `RS` | Room and Finishes Schedule | 8 | B |
| 5.20 | `DS` | Door Schedule | 8 | B |
| 5.21 | `WS` | Window Schedule | 8 | B |
| 5.22 | `SP-SPEC` | Specification | — | B |
| 5.23 | `AR` | Area Schedule | 8 | B |
| 5.24 | `TP` | Tender Package | — | B |
| 5.25 | `RFI` | Request for Information | — | B |
| 5.26 | `CO` | Change Order / Instruction | — | B |
| 5.27 | `DD` | Design-Stage Document | — | B |
| 5.28 | `PR` | Presentation Document | — | B |
| 5.29 | `MM` | Meeting Minutes | — | B |
| 5.30 | `DR` | Design Record / Decision Log | — | B |
| 5.31 | `SR` | Site Report / Inspection Record | — | B |
| 5.32 | `CI` | Construction Issue Package | — | B |
| 5.33 | `AB` | As-Built Record | — | B |
| 5.34 | `OM` | O&M and Asset Information | — | B |

---

## 5.1 Cover Sheet (`CS`)

**Purpose.** Identify the set, state its status and the terms on which it may be used, and provide
the entry point to navigation.

**Users.**

| User | Question |
|---|---|
| Any recipient | What is this set, whose is it, and may I build from it? |
| Site manager | Which revision and status do I hold? |
| Authority | Who is responsible and under what standards was this produced? |
| Archivist | What is this, when was it issued, and what does it contain? |

**Answers.** None of the five directly. The cover sheet is metadata.

**Required content.**

1. Project name, project code, and site address.
2. Client name.
3. Originator name, address, contact, and responsible individual.
4. Document set title and package identifier.
5. Status code and status name, at ≥ 10 mm cap height.
6. Issue date and revision.
7. Conformance claim (`ADOS-0.3.2`), including edition and class.
8. Declared units, declared decimal separator, declared primary language.
9. Declared smallest nominated issue size (`ADOS-3.2.040`).
10. Declared north orientation statement and datum statement.
11. Consultant list with disciplines and their originator codes.
12. Copyright and confidentiality statement.
13. Reference to the drawing register (`ADOS-5.2`).
14. Do-not-scale statement.

**Optional content.** A single locator image (site aerial or building elevation) at ≤ 30 % of the
sheet area; a stage/programme statement; statutory approval references.

**Hierarchy.** (1) Project name; (2) status; (3) set title; (4) originator; (5) administrative
content.

**Layout logic.** The cover is the only sheet where the drawing area is not used for views. It uses
the cover template: title block retained in position (`ADOS-3.3.010` Ex. 1) so that the sheet
number and revision remain findable in a stack; the remaining area carries the identity block at
the top third, the declarations in the middle third, and the consultant list at the bottom third.
Declarations are grouped because they are read together, once, at the start of a project.

**Quality checklist.**

- [ ] `V-5.1.001` All fourteen required items present and non-empty.
- [ ] `V-5.1.002` Status on cover equals status on every container in the package.
- [ ] `V-5.1.003` Conformance claim states edition and class.
- [ ] `V-5.1.004` Consultant originator codes match those used in container identifiers.
- [ ] `V-5.1.005` Locator image, if present, ≤ 30 % of sheet area and labelled per
      `ADOS-4.11.060`.
- [ ] `V-5.1.006` Nominated issue size stated and consistent with the set's minima.

### ADOS-5.1.010 — Cover status precedence ⚠

**Decision.** The cover sheet status shall equal the lowest status of any container in the package.
A package containing a single `S1` container is an `S1` package.

**Rationale.** A cover stating `A1` over a package containing preliminary information invites
construction from preliminary information. Status is a property of what may be relied on, and
reliance is limited by the weakest member.

**Validation.** `V-5.1.010`: `cover.status = min(container.status)` under the status ordering.

---

## 5.2 Drawing Register / Index (`IX`)

**Purpose.** Enumerate every container in the set with its current revision and status, so that a
recipient can determine whether they hold a complete and current set.

**Users.**

| User | Question |
|---|---|
| Recipient | Do I have everything, and is it current? |
| Site manager | Which drawing covers this part of the work? |
| Cost consultant | What is the scope of the priced information? |
| Checker | Which containers changed in this issue? |

**Answers.** Where is it? (at the set level).

**Required content.**

1. One row per container, with: container identifier (full form), sheet number (short form), title,
   type, sheet size, current revision, status, and issue date.
2. Columns per issue, showing the revision issued at each issue date (an issue matrix).
3. Total container count.
4. A list of containers withdrawn since the previous issue, with `WD` status.
5. A list of external references (`ADOS-5.2.040`).
6. Generation timestamp and the statement that the register is machine-generated.

**Optional content.** Scale, level, zone, discipline columns; hyperlinks in the digital version;
a filter statement where the register covers a subset.

**Hierarchy.** (1) Register title and set identity; (2) column headers; (3) rows grouped by series;
(4) issue matrix.

**Layout logic.** A4 or A3 portrait, or a large-format sheet where the issue matrix is wide. Rows
grouped by series (`ADOS-2.5.030`) with a group heading, because that matches both the physical
order of the set and the reader's mental model. The issue matrix is placed to the right of the
identity columns so that the identity columns remain visible when the matrix is wide and the sheet
is folded.

### ADOS-5.2.010 — Register generation ⚠

**Decision.** The register shall be generated from the container database at publication time. A
manually maintained register shall not be issued.

**Rationale.** A hand-maintained register is a duplicate of the set's own state (`ADOS-0.3.020`) and
diverges at exactly the moment it matters: a rushed issue.

**Validation.** `V-5.2.010`: register content equals the package manifest; row count equals
container count; differences = 0.

### ADOS-5.2.020 — Register completeness ⚠

**Decision.** The register shall list every container in the set, including those not issued in the
current package, with their last-issued revision and status.

**Rationale.** The recipient's question is "do I have everything?", which cannot be answered by a
list of what was sent today.

**Validation.** `V-5.2.020`: register rows = all live containers, not only the current package.

### ADOS-5.2.030 — Issue matrix

**Decision.** The register shall carry an issue matrix with one column per issue date, showing the
revision of each container at that issue, so that a recipient can reconstruct what they should
hold.

**Validation.** `V-5.2.030`: matrix column count = issue count; each cell matches the issue record.

### ADOS-5.2.040 — External reference list

**Decision.** The register shall list every document referenced by the set but not part of it:
standards, statutory documents, consultant documents, client documents — each with its identifier,
title, version/date and source.

**Rationale.** `ADOS-2.4.030` Exception 1: references out of the set are one-way, so the reader
needs an explicit list to resolve them.

**Validation.** `V-5.2.040`: every external reference string appearing in the set resolves to a list
entry.

**Quality checklist.**

- [ ] `V-5.2.001` Row count equals live container count.
- [ ] `V-5.2.002` Every revision matches the container's current revision.
- [ ] `V-5.2.003` Withdrawn containers listed with `WD`.
- [ ] `V-5.2.004` External reference list complete.
- [ ] `V-5.2.005` Generated, timestamped, and marked as generated.

---

## 5.3 General Notes, Legends and Abbreviations (`GN`)

**Purpose.** Carry, once, every convention and general requirement that applies across the set, so
that no sheet repeats them and no convention is unexplained.

**Users.** Every reader, once at the start; then on demand for symbol resolution.

**Answers.** Why / under what condition?

**Required content.**

1. General notes, numbered, grouped by subject, each ≤ 25 words (`ADOS-0.5.050`).
2. The full encoding table as a printed legend (`ADOS-3.1.050`): line tiers, line types, tones,
   hatches, symbols, with each graphic shown at actual size.
3. Abbreviation list, complete for the set (`ADOS-0.5.070`).
4. Level type prefixes (`ADOS-4.5.100`) and dimension provenance tokens (`ADOS-4.5.090`).
5. Dimension reference face convention (`ADOS-4.5.060`).
6. Units, decimal separator, datum and coordinate system statements.
7. Grid convention statement.
8. Phase encoding legend (`ADOS-4.12.010`).
9. Statement of the standards to which the set conforms.

**Optional content.** Statutory notes required by the jurisdiction overlay; health and safety
information required by construction design regulations; a materials palette reference.

**Hierarchy.** (1) Section headings; (2) legend graphics; (3) note text.

**Layout logic.** Legend graphics are placed in the left column and their meanings in the right,
because the reader arrives with the graphic and needs the meaning — the graphic is the search key
and belongs in the scanned column. Notes are grouped by subject with headings, at ≤ 7 notes per
group (`ADOS-3.5.020` grouping and §1.2.4 group size).

### ADOS-5.3.010 — General notes shall be general ⚠

**Decision.** A note on the general notes sheet shall apply to every sheet in the set. A note that
applies to some sheets shall be a sheet note on those sheets.

**Rationale.** General notes that do not apply universally train readers to ignore general notes,
which then also ignores the ones that do apply.

**Validation.** `V-5.3.010`: every general note is tagged with its applicability, and applicability
= `set` for all notes on this sheet.

### ADOS-5.3.020 — Legend actual-size requirement

**Decision.** Legend graphics shall be drawn at the size and weight at which they appear in the
drawings.

**Validation.** `V-5.3.020`: legend graphic width/pitch/weight equals the drawing instance within
±5 %.

**Quality checklist.**

- [ ] `V-5.3.001` Every graphic state used anywhere in the set has a legend entry.
- [ ] `V-5.3.002` No legend entry describes a state not used in the set.
- [ ] `V-5.3.003` Every abbreviation used in the set is listed; none unused.
- [ ] `V-5.3.004` All notes ≤ 25 words, active voice, single requirement.
- [ ] `V-5.3.005` Notes contain no prohibited content (`ADOS-4.8.040`).

---

## 5.4 General Arrangement Floor Plan (`GA-P`)

**Purpose.** Show, for one level, the location and identity of every space and every enclosing and
dividing element, and provide the reference frame from which all other information about that level
is located.

**Users.**

| User | Question |
|---|---|
| Contractor | Where does each element go? |
| Setting-out engineer | What is the position relative to the grid? |
| Consultants | What is the spatial framework I am coordinating into? |
| Cost consultant | What is the extent and quantity? |
| Authority | Does the layout comply? |
| Client | What is each space, and how big is it? |

**Answers.** Where is it? · How big is it? (framework only) · What is it? (by reference)

**Required content.**

1. All elements cut by the plan cut plane, at tier W3 (`ADOS-4.1.020`).
2. All visible elements below the cut plane, at W2.
3. Elements above the cut plane relevant to the level (overhead structure, bulkheads, mezzanines),
   at W1 `L-DASH`.
4. Setting-out grid with bubbles at both ends (`ADOS-4.4.020`).
5. Room tags: room number and name (`ADOS-5.19`).
6. Door marks and window marks (`ADOS-5.20`, `ADOS-5.21`).
7. Wall type marks at every distinct wall type run (`ADOS-5.16`).
8. Level annotations: FFL at every level change, and SSL where the structure differs.
9. Dimensions: three chains per side, closed (`ADOS-4.5.030`).
10. Section and elevation markers for every section and elevation cutting this level
    (`ADOS-4.7`).
11. Detail markers for every detail taken from this level.
12. North point (`ADOS-4.3.040`).
13. Cut plane height statement (`ADOS-4.3.020`).
14. Stair and ramp direction arrows with going/rise counts and up/down labels.
15. Fixed furniture and sanitaryware where they affect compliance or coordination.
16. Match lines and overlap where the level is split (`ADOS-4.7.060`, `ADOS-4.7.070`).

**Optional content.** Loose furniture layout (only where it is part of the deliverable, and then at
tone `T1`); floor finish zones (only where not carried by the room schedule); fire compartment
lines (only where the fire strategy is not a separate drawing, which is permitted only on Class C
projects).

**Hierarchy.** (1) Cut elements; (2) grid; (3) room tags; (4) visible elements; (5) dimensions;
(6) marks and markers; (7) elements above.

**Layout logic.** One level per sheet unless the level requires splitting. Plan positioned in the
upper-left of the drawing area (`ADOS-2.10.020`) with dimension chains outside the building
envelope on all four sides. Dimension chains outside, never inside, because internal chains cross
the content the reader is trying to see; internal dimensions are used only for elements that cannot
be referenced to an external chain.

### ADOS-5.4.010 — One level per plan ⚠

**Decision.** A GA plan shall show exactly one level. Content from other levels appears only as
`L-DASH` W1 reference where it is required to understand this level.

**Validation.** `V-5.4.010`: distinct levels in the view range ≤ 1 plus declared reference content.

### ADOS-5.4.020 — Dimension chain structure ⚠

**Decision.** Every GA plan shall carry three dimension chains on each of two orthogonal sides
minimum: openings and element positions (innermost), grid-to-grid (middle), overall (outermost).
All chains shall close (`ADOS-4.5.030`).

**Validation.** `V-5.4.020`: chain count per side ≥ 3; closure holds; chain spacing 10 mm.

### ADOS-5.4.030 — Orientation ⚠

**Decision.** Every GA plan in the project shall use the identical orientation (`ADOS-4.3.030`).

**Validation.** `V-5.4.030`: north vector identical across all plans.

### ADOS-5.4.040 — Room tag completeness ⚠

**Decision.** Every enclosed space shall carry a room tag. Circulation, plant, risers, voids and
external areas within the building envelope are enclosed spaces for this purpose.

**Rationale.** An untagged space cannot be scheduled, cannot be referenced in an RFI, and will be
omitted from finishes.

**Validation.** `V-5.4.040`: model space count = tag count; untagged spaces = 0.

### ADOS-5.4.050 — Wall type marking ⚠

**Decision.** Every wall shall be marked with its type code at least once per continuous run, and
at every change of type. Runs longer than 15 m shall be marked at least twice.

**Validation.** `V-5.4.050`: for every wall run, ≥ 1 type mark; unmarked runs = 0.

**Quality checklist.**

- [ ] `V-5.4.001` All sixteen required content items present.
- [ ] `V-5.4.002` Line tiers monotonic with depth (`ADOS-4.1.020`).
- [ ] `V-5.4.003` All dimension chains closed.
- [ ] `V-5.4.004` Every space tagged; every tag resolves to a room schedule row.
- [ ] `V-5.4.005` Every door and window tagged; every mark resolves to a schedule row.
- [ ] `V-5.4.006` Every wall run type-marked.
- [ ] `V-5.4.007` Every section/elevation/detail marker reciprocal and resolving.
- [ ] `V-5.4.008` Cut plane height stated; view range consistent with the set.
- [ ] `V-5.4.009` North point present, orientation matches the set.
- [ ] `V-5.4.010` Stair direction and counts shown.
- [ ] `V-5.4.011` Density within limits; annotation count per region ≤ 50.
- [ ] `V-5.4.012` Match lines reciprocal with overlap ≥ threshold.

---

## 5.5 Setting-Out Plan (`SO`)

**Purpose.** Provide the single dimensional instruction by which the building is positioned on the
site and its primary elements are positioned relative to each other.

**Users.** Setting-out engineer; groundworks contractor; structural engineer; surveyor.

**Answers.** How big is it? · Where is it? (in absolute terms)

**Required content.**

1. Setting-out origin with project and national coordinates (`ADOS-4.4.050`).
2. Grid, fully dimensioned: grid-to-grid dimensions and coordinates of grid intersections.
3. Site boundary with bearings and distances, referenced to the national coordinate system.
4. Building envelope position relative to boundaries, at the declared reference face.
5. Levels: datum statement, site datum benchmark position and value, FFL of each level.
6. Positions of all primary structural elements relative to the grid.
7. Positions of below-ground elements affecting setting out.
8. Tolerance statement for setting out.
9. Declaration of which faces the dimensions refer to (`ADOS-4.5.060`).

**Optional content.** Existing features to be retained with survey provenance (`ADOS-4.5.090`);
temporary works reference points.

**Hierarchy.** (1) Grid; (2) coordinates and origin; (3) boundary; (4) building envelope;
(5) levels.

**Layout logic.** The setting-out plan carries no content that is not dimensional. Room names,
furniture, finishes and non-structural elements are omitted, because they add annotation objects to
the drawing whose density budget is entirely consumed by dimensions and coordinates. This is the
clearest case in the system of a drawing defined by what it excludes.

### ADOS-5.5.010 — Setting-out is a separate drawing ⚠

**Decision.** Setting-out information shall be issued on a dedicated drawing, not combined with the
GA plan.

**Rationale.** Density. A GA plan already carries three dimension chains per side and full
annotation; adding coordinates, bearings and structural positions exceeds every density limit. The
consequence of a density failure here is a setting-out error, which is the most expensive class of
construction error.

**Exceptions.**
1. Class C projects below 500 m² may combine, with the combination registered.

**Validation.** `V-5.5.010`: setting-out container exists in packages at stage 4 and beyond.

### ADOS-5.5.020 — Coordinate statement

**Decision.** At least three grid intersections, not collinear, shall be given as coordinate pairs
in both the project and the national coordinate systems.

**Rationale.** Two points define a line; three non-collinear points define the transformation
unambiguously and allow the setting-out engineer to check it.

**Validation.** `V-5.5.020`: ≥ 3 non-collinear coordinate annotations present with both systems.

**Quality checklist.**

- [ ] `V-5.5.001` Origin stated in both coordinate systems.
- [ ] `V-5.5.002` ≥ 3 non-collinear grid intersections coordinated.
- [ ] `V-5.5.003` Grid fully dimensioned, chains closed.
- [ ] `V-5.5.004` Boundary bearings and distances stated.
- [ ] `V-5.5.005` Reference face convention declared on the sheet.
- [ ] `V-5.5.006` Tolerance stated.
- [ ] `V-5.5.007` No non-dimensional content present.

---

## 5.6 Existing Condition and Demolition Plans (`EX`, `DM`)

**Purpose.** `EX`: record the existing building as surveyed, with provenance. `DM`: instruct
precisely what is removed, what is retained, and what is protected.

**Users.** Demolition contractor; structural engineer; principal designer; surveyor; cost
consultant; the future reader of the archive.

**Answers.** Where is it? · What is it? · Why / under what condition?

**Required content — Existing (`EX`).**

1. Existing fabric as surveyed, with phase encoding `existing to remain` (`ADOS-4.12.010`).
2. Survey provenance: method, date, surveyor, and accuracy statement.
3. Dimension provenance tokens `(S)` on all survey-derived dimensions (`ADOS-4.5.090`).
4. Explicit statement of areas not surveyed, with the reason (`ADOS-0.3.090`).
5. Assumed elements, clearly marked as assumed, with the assumption stated (`ADOS-0.4.060`).
6. Existing levels with datum relationship.
7. Known services and structure, with source and confidence.

**Required content — Demolition (`DM`).**

1. Elements to be removed, at `L-DASH` W1 (`ADOS-4.12.010`).
2. Elements to be retained, at `T1` W1 continuous.
3. Elements to be temporarily removed and reinstated, distinctly marked and scheduled.
4. Elements to be protected, marked and scheduled with the protection requirement referenced.
5. Structural elements whose removal requires temporary support, marked, with a reference to the
   structural engineer's document.
6. Extent of removal in three dimensions: where a partial removal is instructed, its limit shall be
   dimensioned and levelled.
7. Hazardous material locations, referenced to the survey (never restated).
8. Sequence constraints where removal order matters.

**Optional content.** Photographic references keyed to positions; salvage schedule references.

**Hierarchy.** `EX`: (1) surveyed fabric; (2) provenance annotation; (3) levels.
`DM`: (1) removals; (2) retained fabric; (3) protection; (4) support requirements.

**Layout logic.** Demolition plans are the clearest case where the *removed* content is the figure
and the retained content is the ground, inverting the normal figure/ground relationship of a
proposal drawing. The encoding is therefore explicitly redundant (`ADOS-4.12.010`) and the legend
is mandatory on every sheet.

### ADOS-5.6.010 — Separation of existing, demolition and proposal ⚠

**Decision.** Existing, demolition and proposal information shall be on separate drawings
(`ADOS-4.12.020`).

**Validation.** `V-5.6.010`: no container carries more than one of the three phases as its subject.

### ADOS-5.6.020 — Survey provenance mandatory ⚠

**Decision.** Every existing-condition drawing shall state its survey method, date and accuracy, and
shall mark every element not derived from survey as assumed.

**Rationale.** `ADOS-0.4.060`. The most expensive refurbishment failures follow from treating an
assumed existing condition as a measured one.

**Validation.** `V-5.6.020`: provenance block present; assumed elements marked; unmarked non-survey
elements = 0.

### ADOS-5.6.030 — Demolition extent shall be three-dimensional

**Decision.** Where a removal is partial, the plan shall be accompanied by a section or elevation
showing the vertical extent, or the extent shall be dimensioned and levelled on the plan.

**Rationale.** "Remove wall" on a plan does not state to what level. This is a frequent and
irreversible error.

**Validation.** `V-5.6.030`: every partial removal has a vertical extent statement.

**Quality checklist.**

- [ ] `V-5.6.001` Phase legend present on every sheet.
- [ ] `V-5.6.002` Survey provenance stated; assumptions marked.
- [ ] `V-5.6.003` Every removal has a defined three-dimensional extent.
- [ ] `V-5.6.004` Temporary support requirements marked and referenced.
- [ ] `V-5.6.005` Protected elements marked and scheduled.
- [ ] `V-5.6.006` Hazardous materials referenced, not restated.
- [ ] `V-5.6.007` No proposal content on a demolition drawing.

---

## 5.7 Phasing Plan (`PH`)

**Purpose.** State which parts of the work occur in which phase, and what the state of the building
is at each phase boundary.

**Users.** Contractor; client operations; building control; fire officer (for occupied phased
works); cost consultant.

**Answers.** Where is it? · Why / under what condition?

**Required content.**

1. One plan per phase per level, or one plan per level with phase zones tonally distinguished where
   phases do not overlap spatially.
2. Phase boundary lines, with the boundary condition (hoarding, temporary wall, fire separation)
   identified and referenced.
3. Occupied areas during each phase, marked.
4. Temporary access, escape routes and services routes for each phase.
5. Phase start and end references to the programme document (never restated dates).
6. Interfaces between phases, with the responsible party.

**Optional content.** Temporary works layouts; site logistics.

**Hierarchy.** (1) Phase zones; (2) boundaries; (3) occupied areas; (4) temporary provisions.

**Layout logic.** Where phases are shown on a single plan, tone encodes the phase and the tone
ladder limit of four per sheet (`ADOS-3.8.020`) bounds the number of phases per sheet at three plus
`T0`. Projects with more phases use one plan per phase — which is also clearer, because the reader's
question is always about one phase at a time.

**Quality checklist.**

- [ ] `V-5.7.001` Every area of every level is allocated to a phase or explicitly excluded.
- [ ] `V-5.7.002` Escape provision shown for every phase in which the building is occupied.
- [ ] `V-5.7.003` Phase boundary construction identified and referenced.
- [ ] `V-5.7.004` Tones per sheet ≤ 4.
- [ ] `V-5.7.005` Programme references resolve; no dates restated.

---

## 5.8 Site Location Plan and Site Plan (`SL`, `SP`)

**Purpose.** `SL`: identify the site unambiguously in its geographic context. `SP`: show the
building in its site with all external works, levels and boundary relationships.

**Users.** Authority; emergency services; contractor; utilities; visitor.

**Answers.** Where is it?

**Required content — Site Location Plan (`SL`).**

1. Site boundary outlined, at a scale of 1:1000 or 1:1250, on a current mapping base.
2. North point.
3. Mapping source, licence and date.
4. Site address and, where the jurisdiction uses one, the land parcel identifier.
5. Access point from the public highway.
6. Scale bar (mandatory: mapping bases are frequently reproduced at altered scale).

**Required content — Site Plan (`SP`).**

1. Site boundary with dimensions and bearings.
2. Building footprint with distances to all boundaries at the declared reference face.
3. Existing and proposed levels across the site, with datum.
4. Access, parking, servicing and refuse routes, with dimensions and gradients.
5. External works: paving, kerbs, steps, ramps, walls, fences, with type references.
6. Drainage principle and connection points, referenced to the engineer's drawings.
7. Trees and vegetation to be retained or removed, with protection zones referenced.
8. Utilities entry points and easements.
9. Fire appliance access and hydrant positions (`ADOS-5.9`).
10. Adjacent buildings and their relationship, at tone `T1`.

**Optional content.** Landscape planting (usually a separate discipline's drawing — reference it
rather than duplicate); site sections.

**Hierarchy.** (1) Boundary; (2) building footprint; (3) levels; (4) access and external works;
(5) context.

**Layout logic.** The site plan is the only architectural drawing whose primary content is the space
*around* the building; the building is therefore treated as a single mass at W3, and the site
elements receive the annotation budget.

### ADOS-5.8.010 — Boundary distances mandatory ⚠

**Decision.** The distance from the building envelope to every site boundary shall be dimensioned at
the closest point of each boundary segment.

**Rationale (R).** Boundary distance determines statutory compliance (fire spread, rights of light,
planning) and is the single most-checked dimension on a site plan.

**Validation.** `V-5.8.010`: for each boundary segment, ≥ 1 dimension to the envelope exists.

**Quality checklist.**

- [ ] `V-5.8.001` Mapping source, licence and date stated (`SL`).
- [ ] `V-5.8.002` Scale bar present.
- [ ] `V-5.8.003` Boundary fully dimensioned with bearings.
- [ ] `V-5.8.004` Building-to-boundary distances dimensioned on every segment.
- [ ] `V-5.8.005` Levels stated with datum and provenance.
- [ ] `V-5.8.006` Access gradients stated where they affect compliance.
- [ ] `V-5.8.007` Fire appliance access shown.
- [ ] `V-5.8.008` Adjacent context at `T1`, clearly subordinate.

---

## 5.9 Fire Strategy Drawings (`FS`)

**Purpose.** State the fire safety strategy in spatial terms: compartmentation, escape, access,
suppression and detection, so that the design can be assessed and built correctly.

**Users.** Approving authority; fire engineer; contractor; building manager; fire and rescue
service.

**Answers.** Where is it? · Why / under what condition?

**Required content.**

1. Compartment lines with fire resistance period, encoded per `ADOS-3.1.040` (redundant channels).
2. Protected escape routes, stairs and lobbies, with their resistance period.
3. Escape distances: travel distance measurements from the most remote point of each area, with
   the permitted maximum stated.
4. Occupancy figures per space and exit capacity per exit.
5. Fire doors with their rating and self-closing/hold-open requirement, by mark reference.
6. Cavity barriers and fire stopping lines.
7. Detection and alarm zones.
8. Suppression coverage where present.
9. Smoke control provision and its extents.
10. Fire and rescue service access, dry/wet riser positions, firefighting shaft.
11. Assembly point (on the site plan version).
12. Reference to the fire strategy report; all performance requirements carried there, never
    restated on the drawing.

**Optional content.** Phased evacuation zoning; refuge positions where not statutory.

**Hierarchy.** (1) Compartment lines; (2) escape routes; (3) travel distances; (4) equipment;
(5) base plan (which is background at `T1`).

**Layout logic.** The fire strategy drawing inverts the normal figure/ground: the building plan is
background (`T1`, W1), and the strategy overlay is the figure. This is the correct treatment because
the reader is checking the strategy, not the building.

### ADOS-5.9.010 — Base plan as background ⚠

**Decision.** On a strategy drawing, the base building plan shall be rendered at `T1` W1 and shall
carry no annotation other than room numbers and grid.

**Rationale.** `ADOS-3.8.050`. A full GA plan under a strategy overlay exceeds the density limit and
buries the strategy.

**Validation.** `V-5.9.010`: base plan elements at `T1`/W1; base annotation limited to room numbers
and grid.

### ADOS-5.9.020 — Redundant encoding of compartmentation ⚠

**Decision.** Compartment lines shall be encoded in at least two channels of rank ≤ 4, and shall
remain fully distinguishable in monochrome (`ADOS-0.3.030`).

**Validation.** `V-5.9.020`: greyscale render distinguishes all compartment classes; ΔL* ≥ 36 or a
distinct line type and tier.

### ADOS-5.9.030 — Travel distance annotation

**Decision.** Travel distances shall be annotated with the measured value, the permitted maximum,
and the route shown as a drawn path from the most remote point.

**Rationale.** A stated distance without the drawn route cannot be checked, and a distance without
the permitted maximum cannot be assessed by anyone who does not have the code open.

**Validation.** `V-5.9.030`: every escape route has a drawn path, a measured value and a limit.

**Quality checklist.**

- [ ] `V-5.9.001` Every compartment line has a stated resistance period.
- [ ] `V-5.9.002` Every fire door on a compartment line appears in the door schedule with a matching
      rating.
- [ ] `V-5.9.003` Travel distances drawn, measured and compared with limits.
- [ ] `V-5.9.004` Occupancy and exit capacity stated per space and exit.
- [ ] `V-5.9.005` Monochrome legibility verified.
- [ ] `V-5.9.006` Base plan is background only.
- [ ] `V-5.9.007` No performance requirement restated from the fire strategy report.
- [ ] `V-5.9.008` Line widths ≥ 0.25 mm (`ADOS-4.1.010` safety-critical minimum).

---

## 5.10 Access and Inclusive Design Strategy (`AS`)

**Purpose.** Demonstrate the accessible route and accessible provision through the building and
site, spatially.

**Users.** Approving authority; access consultant; client; contractor.

**Answers.** Where is it? · Why / under what condition?

**Required content.**

1. Accessible approach route from the site boundary and from accessible parking, with gradients and
   widths dimensioned.
2. Accessible entrances, with door clear opening widths by reference to the door schedule.
3. Horizontal circulation: corridor widths, turning circles, passing places, dimensioned.
4. Vertical circulation: lifts with car dimensions, stairs with going/rise, ramps with gradient and
   landings.
5. Accessible sanitary accommodation with layout references to enlarged plans.
6. Refuges and evacuation provision, coordinated with `ADOS-5.9`.
7. Wayfinding and signage strategy reference.
8. Statement of the standard against which compliance is claimed, and any departures with
   justification.

**Hierarchy.** (1) Accessible route; (2) dimensional constraints; (3) provisions; (4) base plan at
`T1`.

**Layout logic.** As `ADOS-5.9`: overlay on a background base plan. The accessible route is drawn as
a continuous path so that its continuity can be verified visually — a discontinuity is the failure
mode this drawing exists to expose.

**Quality checklist.**

- [ ] `V-5.10.001` The accessible route is continuous from boundary to every accessible space.
- [ ] `V-5.10.002` Every gradient, width and turning space dimensioned.
- [ ] `V-5.10.003` Every departure from the standard stated with justification.
- [ ] `V-5.10.004` Coordinated with the fire strategy for refuges.
- [ ] `V-5.10.005` Base plan is background only.

---

## 5.11 Roof Plan (`RP`)

**Purpose.** Show the roof as a surface: its falls, drainage, penetrations, edges and access.

**Users.** Roofing contractor; drainage engineer; services contractor; maintenance.

**Answers.** Where is it? · How big is it? · What is it? (by reference)

**Required content.**

1. Roof areas with build-up type references (`ADOS-5.16`).
2. Falls: direction arrows with gradients stated, for every plane.
3. Drainage: outlets, gutters, overflows, with positions dimensioned and sizes referenced.
4. Levels at every high point, low point, outlet and threshold.
5. Upstands, parapets and edges with heights and type references.
6. Penetrations: every plant item, flue, vent, rooflight and mast, with position dimensioned and a
   detail reference.
7. Movement joints.
8. Access provision: hatches, walkways, mansafe/fall arrest reference.
9. Plant zones with reference to the services drawings.
10. Perimeter guarding.

**Optional content.** Photovoltaic layout (usually a separate discipline; reference it); maintenance
zoning.

**Hierarchy.** (1) Roof outline and areas; (2) falls; (3) drainage; (4) penetrations; (5) levels.

**Layout logic.** The roof plan is a plan of a *surface*, so the encoding of falls (direction plus
gradient) is the primary content and receives the emphasis normally given to cut elements. Every
penetration is a detail callout, so the marker density limit (`ADOS-4.7.050`, 12 per view) is
frequently the binding constraint: roofs with many penetrations require enlarged plans.

**Quality checklist.**

- [ ] `V-5.11.001` Every roof plane has a stated fall direction and gradient.
- [ ] `V-5.11.002` Every low point has an outlet; every outlet has an overflow or a stated reason
      why not.
- [ ] `V-5.11.003` Every penetration is dimensioned and has a detail reference.
- [ ] `V-5.11.004` Levels stated at all high points, low points and thresholds.
- [ ] `V-5.11.005` Build-up type referenced for every area.
- [ ] `V-5.11.006` Access and fall protection shown.
- [ ] `V-5.11.007` Marker count ≤ 12 per view.

---

## 5.12 Reflected Ceiling Plan (`RCP`)

**Purpose.** Show the ceiling as seen looking up, with its setting-out, elements and services
interfaces.

**Users.** Ceiling contractor; services contractor; lighting designer; site manager.

**Answers.** Where is it? · How big is it? · What is it? (by reference)

**Required content.**

1. Ceiling zones with type references and finished ceiling levels (FCL) for each.
2. Ceiling grid setting-out, dimensioned from a stated origin per room.
3. Services elements in the ceiling plane: luminaires, diffusers, grilles, detectors, sprinklers,
   speakers, access panels — each by symbol with a schedule reference.
4. Bulkheads, upstands and level changes, with dimensions and levels.
5. Perimeter conditions: shadow gaps, cornices, curtain pockets, with detail references.
6. Structural elements visible in the ceiling plane.
7. Reference to the services drawings as the authoritative carrier of services positions where the
   architect is not the originator.

**Optional content.** Lighting circuit or control zoning (services discipline); acoustic treatment
zones.

**Hierarchy.** (1) Ceiling zones and levels; (2) grid setting-out; (3) elements; (4) perimeter.

**Layout logic.** The reflected plan is a mirror of the floor plan, which is a persistent source of
left/right error. Two controls: the view is labelled `REFLECTED CEILING PLAN` at the view title
size, and the grid labels remain in the same positions as the floor plan (they are not mirrored),
so the reader's grid reference remains valid.

### ADOS-5.12.010 — Reflected projection statement ⚠

**Decision.** Every RCP shall carry the word `REFLECTED` in its view title and a statement of the
projection in the notes, and grid labels shall retain their floor-plan positions.

**Validation.** `V-5.12.010`: title contains `REFLECTED`; grid label positions match the
corresponding GA plan.

### ADOS-5.12.020 — Ceiling grid origin ⚠

**Decision.** Ceiling grid setting-out shall be dimensioned from a stated origin in each room, and
the origin rule (centred, or aligned to a stated edge) shall be declared.

**Rationale.** "Centre the grid" is ambiguous when the room is not rectangular, and the resulting
margin tiles are the most visible quality failure in a finished interior.

**Validation.** `V-5.12.020`: every gridded ceiling has a dimensioned origin and a declared rule.

**Quality checklist.**

- [ ] `V-5.12.001` FCL stated for every ceiling zone.
- [ ] `V-5.12.002` Ceiling type referenced for every zone.
- [ ] `V-5.12.003` Grid setting-out dimensioned from a declared origin.
- [ ] `V-5.12.004` Every ceiling element symbol appears in the legend and resolves to a schedule.
- [ ] `V-5.12.005` `REFLECTED` stated; grid labels match the GA plan.
- [ ] `V-5.12.006` Coordination with services confirmed and the authoritative carrier stated.
- [ ] `V-5.12.007` Access panel provision shown for every concealed serviceable item.

---

## 5.13 Elevations (`EL`)

**Purpose.** Show the external appearance and the vertical arrangement of the envelope, with
material extents, openings and levels.

**Users.** Contractor; cladding subcontractor; authority; client.

**Answers.** Where is it? · How big is it? · What is it? (by reference)

**Required content.**

1. All visible external faces, with elements at W2 and the ground/section cut at W3.
2. Material and cladding type extents, by reference to type codes, with change lines.
3. Openings with marks; opening lights and their direction where visible.
4. Levels: every floor level, roof level, parapet, cill and head level of typical openings, and
   ground level at both ends and at each change.
5. Vertical dimension chains: floor to floor, and overall height.
6. Horizontal dimension references to grid.
7. Existing ground line and proposed ground line, distinguished.
8. Rainwater goods, vents, flues, louvres, external lighting, signage.
9. Movement joints.
10. Detail markers for typical envelope conditions.
11. Adjacent building profiles where they affect the reading, at `T1`.

**Optional content.** Shadow projection (presentation only, and then at `T1`); material sample
references.

**Hierarchy.** (1) Building outline and ground line; (2) material extents; (3) openings; (4) levels
and dimensions; (5) components.

**Layout logic.** Elevations of one building are placed on the sheet in their relative orientation
where possible (north above, south below, east right, west left) so that the reader can construct
the building mentally. Where they do not fit, they are placed in the compass order N, E, S, W in
reading order, which matches the numbering in `ADOS-2.5.040`.

### ADOS-5.13.010 — Ground line mandatory ⚠

**Decision.** Every elevation shall show existing and proposed ground lines, distinguished by phase
encoding, with levels at both ends and at every change.

**Rationale.** The relationship between the building and the ground determines threshold levels,
damp-proof course positions, retaining requirements and accessibility. Its omission is a common and
consequential defect.

**Validation.** `V-5.13.010`: both ground lines present; levels ≥ 2 per line plus changes.

### ADOS-5.13.020 — Material extent completeness ⚠

**Decision.** Every area of every elevation shall be attributed to a material or cladding type by
reference. Unattributed areas = 0.

**Validation.** `V-5.13.020`: elevation area coverage by type references = 100 %.

**Quality checklist.**

- [ ] `V-5.13.001` All faces present; naming matches facing direction.
- [ ] `V-5.13.002` Every area attributed to a type reference.
- [ ] `V-5.13.003` Every opening marked and resolving to a schedule.
- [ ] `V-5.13.004` All required levels annotated with prefixes and signs.
- [ ] `V-5.13.005` Existing and proposed ground lines distinguished.
- [ ] `V-5.13.006` Vertical dimension chain closes to the overall height.
- [ ] `V-5.13.007` Detail markers present for each typical envelope condition and reciprocal.
- [ ] `V-5.13.008` Line tiers monotonic with depth.

---

## 5.14 Sections (`SE`)

**Purpose.** Show the vertical relationship of spaces, structure and envelope through the building,
and the build-up of the elements the section cuts.

**Users.** Contractor; structural engineer; services engineer; authority; client.

**Answers.** Where is it? · How big is it? · How is it made? (at reference level)

**Required content.**

1. All elements cut, at W3; visible elements beyond, at W2; distant background at W1/`T1`.
2. Levels at every floor, structural soffit, ceiling, roof, parapet and ground.
3. Vertical dimension chains: structural zone, ceiling void, clear height, floor-to-floor, overall.
4. Grid references with bubbles at the section's grid intersections.
5. Room names of the spaces cut and the spaces beyond.
6. Type references for every cut element (wall, floor, roof, ceiling).
7. Detail markers for every condition detailed from this section.
8. Ground line, existing and proposed, with levels.
9. Foundations to the extent required for coordination, referenced to the structural drawings.
10. Stairs cut or seen, with going, rise and handrail heights.

**Required section coverage.**

- At least two sections, orthogonal to each other.
- At least one section through every stair and every lift shaft.
- At least one section through every double-height or level-change space.
- At least one section through every distinct envelope condition.

**Hierarchy.** (1) Cut elements; (2) levels; (3) dimensions; (4) elements beyond; (5) references.

**Layout logic.** Sections are drawn with the ground line at a constant height on the sheet across
the set, so that levels align visually between sections placed on the same sheet — which allows
direct comparison and makes a level error visible as a misalignment.

### ADOS-5.14.010 — Clear height dimensioning ⚠

**Decision.** Every occupied space cut by a section shall have its clear height dimensioned (FFL to
the lowest point of the ceiling or soffit), separately from the floor-to-floor dimension.

**Rationale.** Clear height is the constraint that determines compliance, coordination and
usability; floor-to-floor is the constraint that determines the structure. Conflating them is a
frequent coordination failure.

**Validation.** `V-5.14.010`: each occupied space in a section has both dimensions.

### ADOS-5.14.020 — Section coverage ⚠

**Decision.** The set shall satisfy the required section coverage above; the coverage shall be
demonstrable from the section marker positions on the plans.

**Validation.** `V-5.14.020`: coverage rules evaluated against the plan marker set; unmet rules = 0.

**Quality checklist.**

- [ ] `V-5.14.001` Coverage rules met.
- [ ] `V-5.14.002` Every cut element carries a type reference.
- [ ] `V-5.14.003` Clear height and floor-to-floor dimensioned for every occupied space.
- [ ] `V-5.14.004` All levels annotated with prefix and sign.
- [ ] `V-5.14.005` Grid bubbles present.
- [ ] `V-5.14.006` Ground lines shown with levels.
- [ ] `V-5.14.007` Vertical chain closes.
- [ ] `V-5.14.008` Section geometry matches the marker direction on the plan.

---

## 5.15 Enlarged Plans and Interior Elevations (`EN`, `IE`)

**Purpose.** Resolve, at a scale where they can be dimensioned and specified, the parts of the
building whose complexity exceeds the GA plan's resolution: cores, stairs, sanitary
accommodation, kitchens, and any repeated or critical room type.

**Users.** Contractor; joinery and fit-out subcontractors; services contractor; accessibility
assessor.

**Answers.** Where is it? · How big is it? · What is it? (by reference)

**Required content — Enlarged plan (`EN`).**

1. The subject area at 1:50 or 1:20, with full dimensional resolution to finished faces.
2. All fixed elements: sanitaryware, joinery, equipment, grab rails, with marks.
3. Clear dimensions for compliance-critical distances, marked `CLR`.
4. Setting-out of tiling, flooring and ceiling grids where they are visible in this space.
5. Interior elevation markers covering every wall of the space (`ADOS-4.7.010`).
6. Levels, falls and drainage points.
7. Services outlets and switches with heights (or a reference to the services drawings).

**Required content — Interior elevation (`IE`).**

1. The wall as seen, with all fixed elements in elevation.
2. Heights of every fixed element from FFL.
3. Finishes extents by reference to the room schedule.
4. Joinery and tiling setting-out.
5. Detail markers for junctions.

**Hierarchy.** (1) Enclosing elements; (2) fixed elements; (3) dimensions; (4) references.

**Layout logic.** The enlarged plan and its interior elevations are placed on the same sheet
wherever they fit, in their relative orientation (elevations unfolded around the plan), because the
reader uses them together and cross-sheet navigation between them would be constant.

### ADOS-5.15.010 — Elevation coverage of enlarged spaces ⚠

**Decision.** Every wall of an enlarged space that carries a fixed element shall have an interior
elevation.

**Validation.** `V-5.15.010`: for each wall with fixed elements, an `IE` view exists and is
reciprocally referenced.

**Quality checklist.**

- [ ] `V-5.15.001` Dimensions to finished faces; `CLR` marked where required.
- [ ] `V-5.15.002` Every fixed element marked and scheduled.
- [ ] `V-5.15.003` Every wall with fixed elements has an interior elevation.
- [ ] `V-5.15.004` Heights stated from FFL for all fixed elements.
- [ ] `V-5.15.005` Tiling and grid setting-out dimensioned from declared origins.
- [ ] `V-5.15.006` Accessibility clearances dimensioned and compared to the standard.

---

## 5.16 Wall, Floor and Roof Type Sheets (`WT`)

**Purpose.** Define, once per type, the build-up, performance references and graphic representation
of every constructional assembly, so that plans and sections can reference a type code instead of
restating its content.

**Users.** Contractor; subcontractors; cost consultant; building control; certifier.

**Answers.** What is it? · How is it made?

**Required content, per type.**

1. Type code (the reference used everywhere else).
2. Section through the assembly at 1:10 or 1:20, drawn with each layer distinguished.
3. Layer table: layer number, material reference (to the specification clause), nominal thickness,
   and function (structure, insulation, barrier, finish).
4. Overall nominal thickness, and the tolerance-absorbing layer identified.
5. Performance references: fire resistance, acoustic performance, thermal transmittance, and any
   other performance the specification assigns to this assembly — as *references to the clause*,
   with the value shown only where the value is the type's defining property.
6. Applicability statement: where this type is used.
7. Junction references: the details in which this type's junctions are resolved.
8. Fixing and support principle.
9. Standard variants of the type (a `WT-01a` with a different finish) as explicit separate codes,
   never as unlabelled variation.

**Optional content.** Certification references; test evidence references; a photograph of the
assembly.

**Hierarchy.** (1) Type code; (2) section; (3) layer table; (4) performance; (5) junction
references.

**Layout logic.** Types are laid out in a fixed grid, one cell per type, with the code at the same
position in every cell and the section and table in the same relative positions. This makes the
sheet a lookup table: the reader arrives with a code and finds it by position, not by reading.

### ADOS-5.16.010 — Type code as the only cross-reference ⚠

**Decision.** Plans, sections and elevations shall reference assemblies by type code only. Layer
descriptions, thicknesses and performance values shall not appear outside the type sheet and the
specification.

**Rationale.** `ADOS-0.3.020`. This is the highest-value application of the single-source rule: a
wall build-up appears in dozens of locations.

**Validation.** `V-5.16.010`: assembly descriptions on non-`WT` drawings = 0.

### ADOS-5.16.020 — Every type used shall be defined ⚠

**Decision.** Every type code appearing anywhere in the set shall have a definition on a type sheet,
and every type defined shall be used at least once.

**Validation.** `V-5.16.020`: set difference between used codes and defined codes = ∅ in both
directions.

### ADOS-5.16.030 — Layer completeness

**Decision.** Every layer contributing thickness shall appear in the layer table, including air
gaps, membranes and finishes, with air gaps stated as nominal cavity dimensions.

**Validation.** `V-5.16.030`: Σ layer thicknesses = stated overall thickness.

### ADOS-5.16.040 — Standard detail verification ⚠

**Decision.** A type or detail imported from a standard library shall be verified against the
project's conditions before issue, and the verification shall be recorded with the verifier and
date. An unverified library item shall not be issued.

**Rationale.** §1.9 T8. Library reuse is efficient and is the largest single source of
project-inappropriate documentation; the control is verification, not prohibition.

**Validation.** `V-5.16.040`: every library-sourced container carries a verification record.

**Quality checklist.**

- [ ] `V-5.16.001` Every used code defined; every defined code used.
- [ ] `V-5.16.002` Layer thicknesses sum to the stated overall.
- [ ] `V-5.16.003` Performance stated by reference, not restated.
- [ ] `V-5.16.004` Applicability statement present for every type.
- [ ] `V-5.16.005` Junction detail references present and reciprocal.
- [ ] `V-5.16.006` Library items verified and recorded.
- [ ] `V-5.16.007` Graphic layer representation matches the layer table order.

---

## 5.17 Type Schedules (`TS`)

**Purpose.** Tabulate, for a class of elements, every type's defining properties, as the
authoritative carrier of type-level facts (`ADOS-2.2.010`).

**Users.** Contractor; cost consultant; subcontractors; procurement.

**Answers.** What is it?

**Required content.**

1. One row per type; the type code as the leftmost column.
2. Columns for each defining property of the class, in decreasing frequency of use.
3. Classification reference (`ADOS-6.6`).
4. Specification clause reference for each type.
5. Quantity of instances (generated from the model), as an information field marked as generated.
6. Source of each property value, where sources differ (design, manufacturer, test).

**Layout logic.** Per `ADOS-3.12`: no vertical rules, constant row pitch, alignment by column type,
no empty cells.

### ADOS-5.17.010 — Type schedules are generated ⚠

**Decision.** Type schedules shall be generated from the model. A hand-maintained type schedule
shall not be issued.

**Validation.** `V-5.17.010`: schedule content equals the model query result; differences = 0.

**Quality checklist.**

- [ ] `V-5.17.001` Generated from the model and timestamped.
- [ ] `V-5.17.002` Every type used in the set appears; no unused types.
- [ ] `V-5.17.003` No empty cells (`ADOS-3.12.040`).
- [ ] `V-5.17.004` Specification clause reference present for every row.
- [ ] `V-5.17.005` Classification reference present for every row.

---

## 5.18 Details (`DT`)

**Purpose.** Resolve a junction or a component to the level at which it can be built, coordinated
and priced without further interpretation.

**Users.** Subcontractors; site supervisor; cost consultant; certifier; checker.

**Answers.** How is it made? · How big is it? · What is it? (by reference)

**Required content.**

1. The junction at 1:10, 1:5, 1:2 or 1:1 per `ADOS-4.2.020`.
2. Context: ≥ 100 mm real extent beyond the junction and ≥ 1 datum (`ADOS-4.11.010`).
3. Every layer annotated by reference (`ADOS-4.11.020`).
4. Dimensions that must be set out, including cavity widths, upstand heights, laps and overlaps.
5. Levels at any change.
6. Fixing and support: type, spacing, and a specification reference.
7. Movement provision: joint widths and the movement they accommodate.
8. Water, air and vapour control lines shown continuously across the junction, with their continuity
   explicit.
9. Thermal continuity: insulation shown continuous, or the bridge identified and referenced to the
   thermal assessment.
10. Fire continuity: cavity barriers and stopping shown, with references.
11. Tolerance where it differs from the general tolerance.
12. Typical applicability or specific location (`ADOS-2.3.030`).
13. Detail title with view identifier, scale and applicability (`ADOS-4.11.040`).

**Optional content.** Sequence of assembly; alternative conditions as separate details, never as
alternatives within one detail.

**Hierarchy.** (1) Cut elements; (2) continuity lines (water, air, vapour, thermal, fire);
(3) dimensions; (4) annotation references; (5) context.

**Layout logic.** Details are arranged on a sheet by their position in the building, reading from
the ground up and from outside in, so that a reader following the envelope from foundation to
parapet finds them in order. Each detail occupies a whole number of grid columns.

### ADOS-5.18.010 — Continuity lines mandatory ⚠

**Decision.** Every envelope detail shall show the continuity of the water barrier, the air barrier,
the vapour control layer, the thermal layer and, where applicable, the fire barrier — each shown
across the full extent of the detail and explicitly connected or explicitly terminated with a
reference to where it continues.

**Rationale.** Envelope failures are overwhelmingly continuity failures at junctions, and a detail
that shows the materials but not the continuity does not answer the question the detail exists to
answer.

**Validation.** `V-5.18.010`: for each of the five continuity classes present in the assembly, a
continuous annotated line exists across the detail, or an explicit termination reference exists.

### ADOS-5.18.020 — One condition per detail ⚠

**Decision.** A detail shall show one condition. Alternatives, options and "or similar approved"
constructions shall not appear within a detail.

**Rationale.** A detail with two options requires the reader to choose, which transfers a design
decision to the builder without transferring the criteria (`ADOS-0.4.030`).

**Validation.** `V-5.18.020`: details containing option annotations = 0.

### ADOS-5.18.030 — Detail necessity ⚠

**Decision.** A detail shall exist for every condition that cannot be built correctly from the type
sheets and the general arrangement alone. The detail schedule shall enumerate the conditions and
map them to details, so that missing details are visible.

**Validation.** `V-5.18.030`: the condition-to-detail matrix has no unmapped condition.

**Quality checklist.**

- [ ] `V-5.18.001` Context ≥ 100 mm and ≥ 1 datum present.
- [ ] `V-5.18.002` Every layer annotated by reference; no descriptions.
- [ ] `V-5.18.003` All five continuity classes resolved or explicitly terminated.
- [ ] `V-5.18.004` Setting-out dimensions present; chains closed.
- [ ] `V-5.18.005` Fixings specified by reference with spacing.
- [ ] `V-5.18.006` Movement provision stated.
- [ ] `V-5.18.007` Applicability or location stated.
- [ ] `V-5.18.008` Reciprocally referenced from every calling view.
- [ ] `V-5.18.009` One condition only.
- [ ] `V-5.18.010` Drawn in built orientation, not rotated.

---

*Continue to [Volume 5 Part B — Schedules, Specifications, Packages and Records](ADOS-V5B-Document-Types.md).*
