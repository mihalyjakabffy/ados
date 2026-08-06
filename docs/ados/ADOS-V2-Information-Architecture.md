# Volume 2 — Information Architecture

**ADOS 1.0 · Volume 2 · The structure of a documentation set.**

Volume 2 defines *what the set is made of, how the parts relate, how a reader moves between
them, and how the whole thing changes over time*. It is the schema layer. Volumes 3 and 4
define how an individual artefact looks; Volume 2 defines what artefacts exist and why.

---

## 2.1 The information model

### 2.1.1 Why an explicit model

**Problem.** Practices talk about "the drawings" as an undifferentiated pile. Without named
entities and defined relationships, it is impossible to state where a fact belongs, what a
reference means, or what must be true after a change.

**Rationale (A, I).** Every rule about placement, reference, revision and validation is a
statement about entities and their relations. Those statements can only be checked if the
entities exist formally.

### ADOS-2.1.010 — Entity model ⚠

**Purpose.** Provide the vocabulary and structure on which all Volume 2–8 rules operate.

**Background.** The documentation set is a directed graph, not a list. Sheets contain views;
views project model content; references connect sheets; documents supersede documents.

**Problem.** Undefined structure produces facts filed in arbitrary places and references that
cannot be validated.

**Decision.** Every ADOS-conforming documentation system shall implement the following entity
model. Names are normative; attribute names are normative for machine artefacts.

| Entity | Definition | Key attributes |
|---|---|---|
| **Project** | The commission. Root of all identifiers. | `project_code`, `project_name`, `jurisdiction`, `units`, `standards_claim` |
| **Set** | All information containers produced for a Project by one Originator. | `originator_code` |
| **Package** | A group of containers issued together for one purpose at one time. | `package_id`, `purpose`, `issue_date`, `status`, `recipients` |
| **Container** | An individually identified information artefact: a sheet, a document, a model, a schedule export. | `container_id`, `type`, `status`, `revision`, `author`, `checker`, `approver` |
| **Sheet** | A Container of type *drawing sheet*: a fixed-size printable surface. | `sheet_size`, `scale_set`, `zoning_template` |
| **View** | A projection of model content onto a Sheet at a stated scale. | `view_id`, `view_type`, `scale`, `level`, `orientation`, `detail_level` |
| **Region** | A named zone of a Sheet (`ADOS-3.3`). | `region_id`, `role`, `bounds` |
| **Annotation** | A text, dimension, tag, leader, symbol or note object. | `anno_id`, `class`, `anchor`, `source_ref` |
| **Reference** | A directed link from a source location to a target Container/View. | `ref_id`, `source`, `target`, `kind`, `reciprocal_of` |
| **Fact** | An atomic assertion (a value, a property, a requirement). | `fact_id`, `class`, `value`, `carrier`, `provenance` |
| **Revision** | A recorded state change of a Container. | `rev_code`, `date`, `description`, `author`, `affected_regions` |
| **Issue** | The act of transmitting a Package to recipients. | `issue_id`, `package_id`, `date`, `medium`, `record` |

**Implementation.** The model is expressed formally in
[`machine/ados-sheet-schema.json`](machine/ados-sheet-schema.json). Authoring tools map their
native objects onto these entities via the mapping tables in `ADOS-6.2`.

**Exceptions.** None. A system that cannot express these entities cannot claim conformance
above Class C.

**Validation.** `V-2.1.010`: the exported set manifest validates against the sheet schema; every
Container has a unique `container_id`; every Reference resolves.

**Examples.** *Conforming:* a Revit sheet mapped to Container, its viewports to Views, its
title block fields to Container attributes. *Non-conforming:* PDFs with no manifest, where
`container_id` exists only inside the page image.

**Common mistakes.** Treating the file name as the identity (file names are copied and renamed);
treating a view as a sheet (one sheet may carry many views, and a view may appear on more than
one sheet).

**Automation notes.** The manifest is the generator's input and output contract
(`ADOS-7.3.010`). All QA metrics are computed over this model, not over pixels.

### 2.1.2 The containment and reference graph

```
Project
 └── Set (one per Originator)
      └── Package (issued together)
           └── Container
                ├── Sheet ── Region ── View ── Annotation
                └── Document ── Section ── Clause

References (cross-cutting, directed):
   Sheet ──callout──▶ View            (detail / section / elevation callouts)
   Annotation ──tag──▶ Fact           (type marks, room tags, level markers)
   Container ──supersedes──▶ Container
   Container ──depends_on──▶ Container (must be read with)
   Fact ──carried_by──▶ Container      (single authoritative carrier)
```

**ADOS-2.1.020 — Graph acyclicity.** The `supersedes` relation shall form a directed acyclic
graph. The `depends_on` relation may contain cycles only where both directions are
`read_with`; a cycle in `derived_from` is a defect.
*Validation `V-2.1.020`: topological sort of `supersedes` and `derived_from` succeeds.*

---

## 2.2 Single source of truth: fact carriers

### 2.2.1 The problem restated

`ADOS-0.3.020` requires one authoritative location per fact. Volume 2 makes that operational by
enumerating fact classes and binding each to a carrier.

### ADOS-2.2.010 — Fact carrier assignment ⚠

**Purpose.** Make "where does this information belong?" answerable without judgement.

**Background.** Every documentation dispute about duplication reduces to an unassigned fact
class.

**Problem.** Without an assignment table, the same fact is recorded by whoever thinks of it
first, in whatever document they are working on.

**Decision.** Each fact class shall have exactly one authoritative carrier, per the table below.
Other documents may reference it; they shall not restate its value.

| Fact class | Authoritative carrier | Referenced from | Rule |
|---|---|---|---|
| Building geometry, position, size | Project model | All drawings (as projection) | `ADOS-6.1.010` |
| Setting-out origin, grid, levels | Setting-out drawing + model shared coordinates | All plans and sections | `ADOS-5.5` |
| Element type and its properties | Type schedule (derived from model types) | Plans, sections via type marks | `ADOS-5.17` |
| Element instance identity | Model instance mark | Plans, schedules | `ADOS-2.5.060` |
| Room identity, name, area, finish | Room schedule (derived) | Plans via room tag | `ADOS-5.19` |
| Door/window properties | Door / window schedule | Plans via mark | `ADOS-5.20`, `ADOS-5.21` |
| Wall / floor / roof build-up | Wall type sheet | Plans and sections via type code | `ADOS-5.16` |
| Materials, workmanship, performance, standards | Specification | Drawings via clause reference | `ADOS-5.22` |
| Fire performance requirement | Fire strategy + specification | Fire plans, schedules | `ADOS-5.9` |
| Tolerances | Specification (general), detail drawing (local) | — | `ADOS-4.5.070` |
| Quantities | Model-derived schedule | Cost documents | `ADOS-6.10.050` |
| Survey / existing condition | Survey record | Existing/demolition drawings | `ADOS-5.6` |
| Programme, sequence, phasing | Phasing drawing + programme document | GA drawings via phase tag | `ADOS-5.7` |
| Design decisions and their reasons | Design record / decision log | — | `ADOS-5.30` |
| Instructions and changes | Change order / instruction | Superseding revisions | `ADOS-5.26` |
| Queries and answers | RFI register | Revisions | `ADOS-5.25` |

**Implementation.** The project's *Information Delivery Plan* (`ADOS-2.9.020`) instantiates this
table with named documents and responsible parties.

**Exceptions.**
1. Safety-critical duplication under `ADOS-2.2.040`.
2. A statutory submission that requires restatement in a prescribed form; the restatement is
   machine-generated and the deviation is registered.

**Validation.** `V-2.2.010`: each fact class in the project's plan has exactly one carrier; the
duplicate-value scan (`ADOS-8.4.050`) reports zero unresolved duplicates.

**Common mistakes.** Dimensioning a door width on the plan *and* scheduling it; writing a
performance requirement as a drawing note; restating a specification clause in a general note.

**Automation notes.** The generator resolves references at publication; a value that appears in
two containers with different content is a build error, not a warning.

### ADOS-2.2.020 — Reference in place of restatement

**Decision.** Where a document needs a fact it does not carry, it shall include a reference of
the form `<mark or code>` plus, where the target is not obvious from the code, an explicit
container reference. It shall not include the value.

**Implementation.** Reference forms are defined in `ADOS-2.4.020`.

**Validation.** `V-2.2.020`: no annotation on a location drawing contains a value belonging to a
fact class carried elsewhere (checked by pattern rules per class, e.g. fire rating tokens on
plans).

### ADOS-2.2.030 — Prohibition of manual restatement ⚠

**Decision.** A value that is available from an authoritative carrier shall not be entered
manually into another container.

**Validation.** `V-2.2.030`: in the authoring model, the count of text annotations whose content
matches a schedulable parameter value shall be 0 (tool query defined in `ADOS-6.7.050`).

### ADOS-2.2.040 — Controlled safety duplication

**Decision.** Duplication is permitted only where all of: (a) the fact is life-safety critical;
(b) the duplicate is generated by the same publication run from the same source; (c) the
duplicate carries a source token (e.g. `[FS-01]`); and (d) the duplication is listed in the
project plan.

**Validation.** `V-2.2.040`: every duplicated value carries a source token and appears in the
declared duplication list.

---

## 2.3 Content hierarchy: what belongs at which level

### 2.3.1 Levels of a documentation set

**Rationale (C).** Readers approach documentation with questions at different granularity, and
each granularity has a matching artefact. Placing content at the wrong granularity makes it both
invisible (to the reader who needs it) and obstructive (to the reader who does not).

### ADOS-2.3.010 — The five content levels ⚠

**Decision.** Content shall be placed at exactly one of five levels, defined by the question it
answers and bounded by scale:

| Level | Name | Question | Typical scale | Example content |
|---|---|---|---|---|
| L1 | Context | Where is the project? | 1:1000–1:500 | Site location, boundaries, access, constraints |
| L2 | Whole building | How is it organised? | 1:200–1:100 | GA plans, sections, elevations, strategies |
| L3 | Part | How is this part arranged? | 1:50–1:20 | Enlarged plans, core plans, interior elevations |
| L4 | Assembly | How is this built up? | 1:20–1:5 | Wall types, junctions, typical details |
| L5 | Component | What exactly is this item? | 1:5–1:1, or tabular | Component details, schedules, specification clauses |

**Implementation.** `ADOS-4.2.030` binds resolvable feature size to scale; together the two rules
determine placement mechanically: content whose smallest meaningful feature is below the
resolvable size of the current level belongs at the next level down.

**Exceptions.**
1. Strategy drawings (fire, access, acoustic) may present L2 content at L1 scales where the
   strategy is site-wide.

**Validation.** `V-2.3.010`: every view declares a level; no view contains geometry whose
smallest dimension is below its scale's resolvable feature size (`ADOS-4.2.030`).

**Common mistakes.** Insulation layers hatched at 1:100; door swings dimensioned on a 1:200 GA;
site-wide drainage shown at 1:50.

**Automation notes.** Level is a view property in the manifest; the generator selects model
detail level and visibility from it (`ADOS-6.7.030`).

### ADOS-2.3.020 — Lowest sufficient level

**Purpose.** Prevent both content inflation and unnecessary sheets.

**Decision.** Information shall be placed at the *highest* (coarsest) level at which it can be
communicated completely and legibly, and shall be repeated at lower levels only by reference.

**Rationale.** Every additional level a reader must descend costs a navigation event. Content
that can be resolved at L2 should not force a trip to L4.

**Validation.** `V-2.3.020`: for each detail callout, the target detail contains at least one
fact class not resolvable at the calling level. A detail that adds nothing is a defect.

### ADOS-2.3.030 — Typical versus specific

**Decision.** Content shall be classified as **typical** (applies wherever the condition occurs)
or **specific** (applies at one identified location). Typical content shall state its
applicability condition; specific content shall state its location. Content that states neither
is a defect.

**Implementation.** Typical details carry the token `TYPICAL — applies where <condition>`;
specific details carry the grid/level location.

**Validation.** `V-2.3.030`: every detail view carries either a typical-applicability statement
or a location reference. Count of details with neither = 0.

**Common mistakes.** A detail marked "typical" that is only valid at one junction; a
project-specific detail reused from another project without a location statement.

---

## 2.4 Navigation

### 2.4.1 The navigation problem

**Rationale (C, R).** A set of 200 sheets is a database with no query interface. The reader's
only tools are: the index, the sheet numbering, key plans, and cross-references. Each is a
navigation instrument and each has a failure mode.

### ADOS-2.4.010 — The four navigation instruments ⚠

**Decision.** Every conforming set shall provide all four instruments:

| Instrument | Answers | Requirement | Rule |
|---|---|---|---|
| **Index (drawing register)** | What exists? | Complete, current, machine-generated | `ADOS-5.2` |
| **Identifier system** | Where does this sit? | Systematic, sortable, speakable | `ADOS-2.5` |
| **Key plan** | Where on the building am I? | On every sheet whose view covers part of a level | `ADOS-3.3.060` |
| **Cross-reference** | Where is the related information? | Reciprocal and resolvable | `ADOS-2.4.030` |

**Validation.** `V-2.4.010`: all four present; index count equals container count; every sheet
requiring a key plan has one.

### ADOS-2.4.020 — Reference notation

**Purpose.** One notation, learnable once, resolvable without ambiguity.

**Decision.** A cross-reference shall be written as:

```
<TARGET-ID> [ / <VIEW-ID> ]

TARGET-ID = the container identifier of the target sheet or document
VIEW-ID   = the view number on that sheet, where the sheet has more than one view
```

Graphic reference markers (section, detail, elevation) shall carry the same two fields in a
fixed position within the marker: **view identifier above, container identifier below**
(`ADOS-4.7.020`).

**Rationale.** Two fields, fixed order, fixed position. The upper field answers "which view",
the lower "which sheet" — matching the reader's search sequence: find the sheet, then the view.

**Validation.** `V-2.4.020`: all reference strings match the grammar in
[`machine/ados-naming.ebnf`](machine/ados-naming.ebnf).

### ADOS-2.4.030 — Reference reciprocity ⚠

**Purpose.** Eliminate one-way references, which strand the reader.

**Background.** A detail sheet that does not say where its details are used cannot be checked,
cannot be coordinated, and forces the reader back to a search of the whole set.

**Problem.** Callouts point down the hierarchy; nothing points back up. When a detail changes,
nobody knows which sheets are affected.

**Decision.** Every reference shall be reciprocal. A callout from view A to view B shall be
accompanied by a *referenced-from* entry on B naming A. Both directions shall be maintained
automatically.

**Implementation.** In a model-derived workflow the reciprocal is generated from the callout
object. In manual workflows a *reference matrix* container is maintained and issued with the
set.

**Exceptions.**
1. References to external documents outside the Set (standards, statutory documents) are
   one-way; they shall be listed in the set's external reference list (`ADOS-5.2.040`).

**Validation.** `V-2.4.030`: for every Reference with `kind = callout`, a Reference with
`reciprocal_of` pointing to it exists. Orphan count shall be 0.

**Examples.** *Conforming:* detail `07-014/D3` carries `Referenced from: 03-101, 03-102, 04-201`.
*Non-conforming:* a detail sheet with no back-references.

**Common mistakes.** Deleting a callout without updating the target; copying a detail sheet
between projects with its old back-references intact.

**Automation notes.** Back-reference blocks are generated at publication, never typed.

### ADOS-2.4.040 — Broken reference prohibition ⚠

**Decision.** An issued container shall contain no reference to a container that is not in the
issued Package or in a previously issued Package that remains current.

**Validation.** `V-2.4.040`: unresolved reference count = 0, computed against the union of the
current Package and the live register.

### ADOS-2.4.050 — Navigation depth

**Decision.** A reader shall be able to reach any fact from the index in at most three
navigation events (index → sheet → view → referenced target).

**Rationale (C).** Each event costs 10–60 s and one context reload; three events is the point at
which readers begin to abandon the search and guess or telephone.

**Validation.** `V-2.4.050`: the reference graph's longest shortest-path from the index to any
Fact carrier ≤ 3.

### ADOS-2.4.060 — Key plan requirement

**Decision.** Any sheet carrying a view that shows less than the whole extent of its level or
elevation shall carry a key plan in the designated region, showing the whole extent with the
current portion emphasised.

**Implementation.** Key plan: identical geometry, orientation and position on every sheet of the
set; current portion filled at tone `T3`; remainder at `T1`; minimum printed size 30 × 30 mm;
north point included (`ADOS-3.3.060`).

**Validation.** `V-2.4.060`: for every view with `extent < level_extent`, a key plan object
exists in region `KEY`; key plan geometry hash is identical across the set.

---

## 2.5 Identification systems

### 2.5.1 Design requirements for an identifier

**Rationale (C, R, I).** An identifier is used for: sorting (finding in a stack), speaking (on
the telephone, on site), filing (in a CDE), and machine processing. These impose:

1. **Uniqueness** within the project.
2. **Sortability**: lexical sort shall equal the intended reading order.
3. **Speakability**: pronounceable in under 3 s, distinguishable over a noisy phone line.
4. **Systematic decomposition**: each field answers one query.
5. **Fixed width** per field, so that identifiers align in columns and sort correctly.
6. **Stability**: an identifier is never reused and never renumbered.

These requirements conflict: a fully decomposed identifier is not speakable. ADOS therefore
defines **two** identifiers with a deterministic mapping between them.

### ADOS-2.5.010 — Container identifier (full form) ⚠

**Purpose.** Provide a unique, sortable, machine-parseable identity for every container, aligned
with ISO 19650 container naming.

**Decision.** The full container identifier shall be:

```
<Project>-<Originator>-<Zone>-<Level>-<Type>-<Discipline>-<Number>
```

| Field | Width | Content | Query answered |
|---|---|---|---|
| `Project` | 4–6 | Project code | Which project? |
| `Originator` | 2–3 | Organisation code | Who is responsible? |
| `Zone` | 2 | Volume/zone code, `ZZ` = all | Which part of the site/building? |
| `Level` | 2 | Level code, `ZZ` = multiple, `XX` = n/a | Which level? |
| `Type` | 2 | Container type (DR, SC, SP, RP, MO…) | What kind of document? |
| `Discipline` | 1–2 | Discipline code (A, S, M, E, C…) | Which discipline? |
| `Number` | 4 | Series digit + 3-digit serial | Unique within the above |

Example: `2317-JKA-ZZ-02-DR-A-3104`.

**Implementation.** Codes are defined in `ADOS-A.4`. Level codes use two digits with `B1`,`B2`
for basements, `00` for ground, `01`… for upper levels, `RF` for roof, `MZ` for mezzanine.

**Exceptions.** Where a client CDE mandates a different container naming convention, that
convention governs (precedence level 2) and the mapping to ADOS fields shall be recorded.

**Validation.** `V-2.5.010`: all container identifiers match the EBNF grammar; uniqueness holds;
lexical sort equals register order.

**Common mistakes.** Variable-width fields; omitting `ZZ`/`XX` placeholders (breaks alignment
and sorting); embedding revision in the identifier (revision is an attribute, not identity).

**Automation notes.** The identifier is composed by the generator from container attributes,
never typed. Round-trip test: parse(compose(attrs)) == attrs.

### ADOS-2.5.020 — Sheet number (short form) ⚠

**Purpose.** Provide a speakable, human-facing identifier for use on site and in conversation.

**Decision.** The short form shall be:

```
<Discipline><Series>.<Serial>          e.g.  A3.104
```

derived deterministically from the full identifier's `Discipline` and `Number` fields. The short
form shall appear in the sheet number region at ≥ 7 mm cap height; the full identifier shall
appear in the title block at ≥ 2.5 mm.

**Rationale.** "A three one oh four" is four syllables of payload and survives a phone line. The
full container ID is not speakable and is not needed on site.

**Validation.** `V-2.5.020`: short form is a pure function of the full form; both appear on every
sheet; short form uniqueness holds within the discipline.

### ADOS-2.5.030 — Series allocation ⚠

**Purpose.** Make the physical order of a set match the reader's mental model, so that the set
can be navigated by thumbing.

**Background.** Readers approach a set by decreasing scope: understand the context, then the
existing condition, then the site, then the building, then its parts, then how they are built,
then the tabulated data.

**Decision.** The first digit of `Number` shall be allocated as:

| Series | Content | Level (`ADOS-2.3.010`) |
|---|---|---|
| `0` | General: cover, index, notes, legends, abbreviations, standards | — |
| `1` | Existing, survey, demolition, phasing of existing | L1–L2 |
| `2` | Site, external works, drainage, landscape interface | L1 |
| `3` | General arrangement plans, roof plan, reflected ceiling plans | L2 |
| `4` | Elevations and sections | L2 |
| `5` | Enlarged plans, cores, sanitary, interior elevations | L3 |
| `6` | Assemblies: wall, floor, roof and ceiling types | L4 |
| `7` | Details and junctions | L4–L5 |
| `8` | Schedules | L5 |
| `9` | Strategy and compliance drawings: fire, access, acoustic, thermal, phasing of works | overlay |

**Rationale for placing schedules at 8 and strategies at 9.** Schedules are consulted with the
drawings and are ordered last among the *object* documents. Strategy drawings are *overlays* on
the whole building and are consulted as a group; placing them at the end keeps them contiguous
and keeps the object series uninterrupted.

**Validation.** `V-2.5.030`: every container's series digit matches its declared type per the
type→series map in `machine/ados-rules.yaml`.

### ADOS-2.5.040 — Serial allocation and gaps

**Decision.** Serials within a series shall be allocated in ascending order of level for plans,
and in ascending order of the compass sequence N, E, S, W for elevations. Gaps shall be left:
serials increment by 1 within a group, and groups start at multiples of 10.

**Rationale.** Insertions are certain; renumbering is prohibited (`ADOS-2.5.070`); therefore gaps
must be planned.

**Validation.** `V-2.5.040`: no renumbering event appears in the container history.

### ADOS-2.5.050 — Level and grid designation

**Decision.** Levels shall be designated by code and by absolute datum value, both stated in the
title block region and on every section and elevation. Grid lines shall be lettered `A, B, C…`
in one direction (omitting `I` and `O`) and numbered `1, 2, 3…` in the orthogonal direction,
with letters running in the direction of the longer building dimension.

**Rationale.** Omission of `I` and `O` prevents confusion with `1` and `0` — a documented and
recurring source of setting-out error. Letters on the long axis reduces the count of letters
needed and keeps the numeric sequence, which extends more comfortably, on the shorter axis.

**Validation.** `V-2.5.050`: grid label set contains no `I` or `O`; every level appears with both
code and datum.

### ADOS-2.5.060 — Element marks

**Decision.** Element instance marks shall be `<TypeCode>-<Serial>` where `TypeCode` identifies
the element class and type, and `Serial` is unique within the project. Marks shall not encode
location, because elements move.

**Rationale.** Location-encoded marks (`D-02-14` for level 02, door 14) become wrong when the
element moves, and correcting them breaks every reference. Marks are identities, not addresses.

**Validation.** `V-2.5.060`: mark uniqueness across the project; no mark contains a level or grid
token.

**Common mistakes.** Renumbering doors after a layout change; re-using a mark freed by a deleted
element.

### ADOS-2.5.070 — Identifier immutability ⚠

**Decision.** Once a container or element identifier has appeared in an issued Package, it shall
not be reused for different content and shall not be renumbered. Withdrawn containers keep their
identifier and receive status `S-WD` (withdrawn).

**Validation.** `V-2.5.070`: identifier-to-content binding is injective over the project history.

---

## 2.6 Status, revision and issue control

### 2.6.1 Why status is separate from revision

**Problem.** "Rev C" tells the reader what generation they hold. It does not tell them whether
they may build from it. These are orthogonal facts and conflating them causes construction from
non-construction information.

**Decision principle.** **Status** = permitted use. **Revision** = generation. Both shall appear
on every container, in fixed positions.

### ADOS-2.6.010 — Status codes ⚠

**Purpose.** Make permitted use explicit and unambiguous at a glance.

**Decision.** Every container shall carry one status code from the following closed set, aligned
with ISO 19650:

| Code | Name | Permitted use |
|---|---|---|
| `S0` | Work in progress | Internal only. Not shared. Not to be relied on. |
| `S1` | Shared for coordination | Coordination and comment. Not for construction, pricing or approval. |
| `S2` | Shared for information | Reference only. |
| `S3` | Shared for review and comment | Formal review. Not for construction. |
| `S4` | Shared for stage approval | Client/authority approval. Not for construction. |
| `S6` | Shared for PIM authorisation | As defined by the appointment. |
| `S7` | Shared for AIM acceptance | Handover. |
| `A1`…`An` | Authorised and accepted | Fit for construction as defined by the appointment. |
| `B1`…`Bn` | Partially authorised | Fit for construction except where annotated. |
| `WD` | Withdrawn | Shall not be used. Superseded or cancelled. |

**Implementation.** The status code appears (a) in the title block status field, (b) as a
watermark or banner for all non-construction statuses (`ADOS-3.9.060`), and (c) in the PDF
metadata and file name suffix.

**Exceptions.** Where a jurisdiction or client mandates its own status vocabulary, the mapping to
this set shall be published with the set.

**Validation.** `V-2.6.010`: status field non-empty and within the closed set on every container;
watermark present for every non-`A`/`B` status.

**Common mistakes.** Issuing `S0` work externally "informally"; leaving a preliminary watermark
on an authorised issue; a status field that says "Tender" (a purpose, not a status).

**Automation notes.** Status drives watermark, file naming and distribution rules; it is an input
to the publication pipeline, not a manual stamp.

### ADOS-2.6.020 — Revision coding ⚠

**Decision.** Revisions shall use two sequences:

```
Preliminary (pre-authorisation):  P01, P02, P03 …
Authorised (construction):        C01, C02, C03 …
```

A container transitions from `Pnn` to `C01` at first authorisation. Sub-revisions
(`P01.1`) shall not be used.

**Rationale.** A single sequence cannot express the transition from "developing" to "contractual"
— the most consequential event in the life of a document. Two sequences make it visible in the
revision code itself, which is present everywhere the code is quoted.

**Validation.** `V-2.6.020`: revision codes match `^(P|C)\d{2}$`; each container's history is
monotonic; no `Pnn` follows a `Cnn`.

### ADOS-2.6.030 — Revision register on the container ⚠

**Decision.** Every drawing sheet shall carry a revision register listing, for every revision:
code, date, description of the change, and initials of author and checker. The register shall be
in the fixed revision region (`ADOS-3.3.080`), most recent at the top.

**Rationale (R).** The reader's most frequent question about a superseded drawing is "what
changed?". A register on the sheet answers it without recourse to a separate document, which may
not be present on site.

**Validation.** `V-2.6.030`: register row count equals revision count; each row has all four
fields non-empty; the top row's code equals the container's current revision.

**Common mistakes.** "General updates" as a description — this is a defect, since it answers
nothing; missing rows after a rebuild of the sheet.

### ADOS-2.6.040 — Change description quality

**Decision.** A revision description shall state *what changed* and *where*, in ≤ 20 words, using
the grid or region reference. Descriptions consisting only of generic terms
(`updated`, `revised`, `as noted`, `coordination`) are non-conforming.

**Validation.** `V-2.6.040`: description does not match the banned-phrase list; contains at least
one location token (grid ref, level, room, region).

### ADOS-2.6.050 — Revision marking on the drawing ⚠

**Decision.** Areas changed in the current revision shall be marked with a revision cloud and a
revision tag carrying the revision code. Clouds from superseded revisions shall be removed at the
next revision.

**Rationale (V).** Enclosure is a pre-attentive channel (§1.2.5) and is the only channel not
already committed on a dense drawing. Retaining historical clouds destroys the channel: after
three revisions the sheet is covered and the current change is invisible.

**Exceptions.**
1. First issue of a container (`P01`) is not clouded.
2. Where more than 40 % of the drawing area would be clouded, the whole view is marked
   `EXTENSIVELY REVISED` and the register carries the description.

**Validation.** `V-2.6.050`: for every revision after the first, cloud count ≥ 1 or the extensive
revision token is present; no cloud carries a tag other than the current revision code.

### ADOS-2.6.060 — Issue record ⚠

**Decision.** Every Issue shall be recorded with: package identifier, container list with
revisions and statuses, recipients, date, medium, and the sender. The record is a container in
its own right and is retained for the project's retention period.

**Validation.** `V-2.6.060`: for every issued container revision, an issue record exists that
includes it.

### ADOS-2.6.070 — Superseded information removal ⚠

**Decision.** Superseded containers shall be removed from the current distribution location and
placed in an archive location that is not the working location. Marking a superseded document as
superseded is necessary but not sufficient.

**Rationale (R).** Marking depends on the reader looking at the mark. On site, drawings are read
from the middle of a pinned-up sheet. Physical removal is the only reliable control.

**Validation.** `V-2.6.070`: the current-issue location contains exactly one revision of each live
container; count of superseded containers in the current location = 0.

### ADOS-2.6.080 — Hold and provisional information

**Decision.** Information that is present but not yet fixed shall be marked `HOLD` with a hold
identifier, a reason, and a resolution owner and date. A hold register shall be issued with each
package listing all live holds.

**Rationale.** `ADOS-0.4.020`. An unmarked provisional value is indistinguishable from a fixed
one and will be procured against.

**Validation.** `V-2.6.080`: every `HOLD` token on a drawing resolves to an entry in the hold
register; no hold is past its resolution date without an updated entry.

---

## 2.7 Overlays: jurisdiction, client, practice

### ADOS-2.7.010 — Overlay mechanism ⚠

**Purpose.** Absorb local and contractual requirements without forking the core standard.

**Background.** Statutory content, national symbol conventions, language and client CDE rules
vary. A standard that cannot absorb them is abandoned on the first project that needs them.

**Decision.** Variation shall be expressed only as an **overlay**: a declarative document that
*adds* requirements, *tightens* thresholds, or *maps* vocabularies. An overlay shall not relax a
core `shall` rule; where a statutory requirement conflicts with a core rule, the conflict is
resolved by precedence (`ADOS-0.3.4`) and recorded in the Deviation Register.

**Implementation.** Overlay file structure:

```yaml
overlay:
  id: HU-2026
  kind: jurisdiction          # jurisdiction | client | practice
  applies_to: [ADOS-1.0]
  adds:        [ ... rules ... ]
  tightens:    { ADOS-3.4.010: { min_cap_height_mm: 3.5 } }
  maps:        { status_codes: { A1: "Kivitelezésre" } }
  conflicts:   [ { rule: ADOS-3.10.010, reason: "...", authority: "..." } ]
```

**Exceptions.** None.

**Validation.** `V-2.7.010`: overlay validates against the overlay schema; no overlay entry
relaxes a `shall`; every `conflicts` entry has a Deviation Register record.

**Automation notes.** Overlays are composed at build time in the order core → jurisdiction →
client → practice; later layers may only tighten.

### ADOS-2.7.020 — Language

**Decision.** A set shall declare a primary language. Where a second language is required, the
set shall be bilingual by *parallel field*, not by mixed text: every label carries both languages
in a fixed order with the primary first, or the set is issued in two complete language variants.
Mixed-language sheets are non-conforming.

**Rationale (C).** Mixed-language documents force language switching mid-scan, which measurably
slows reading and increases error, and they break text search.

**Validation.** `V-2.7.020`: language tagging present on all text; no container contains text in
an undeclared language.

### ADOS-2.7.030 — Practice overlay

**Decision.** Practice-level choices permitted by the core (typeface selection within the
constraints of `ADOS-3.4.020`, identity block content, standard detail library) shall be recorded
in a single practice overlay, versioned, and cited by every project.

---

## 2.8 Relationships between documents

### ADOS-2.8.010 — The document relationship types ⚠

**Decision.** The following closed set of relationships shall be used; each has defined
semantics and validation:

| Relation | Meaning | Constraint |
|---|---|---|
| `contains` | Structural containment | Tree; no cycles |
| `derived_from` | Target generated from source | DAG; source must be current |
| `references` | Reader is directed to target | Must be reciprocal (`ADOS-2.4.030`) |
| `read_with` | Neither is complete alone | Symmetric; both must be in the same Package |
| `supersedes` | Target is no longer valid | DAG; triggers `ADOS-2.6.070` |
| `implements` | Target satisfies a requirement in source | Requirement must be identified |
| `conflicts_with` | Known unresolved conflict | Must have an owner and resolution date |

**Validation.** `V-2.8.010`: all relations are typed; constraints per row hold; `conflicts_with`
count in an `A`-status package = 0.

### ADOS-2.8.020 — Read-with sets

**Decision.** Where a document is incomplete without another (a plan and its schedule; a detail
and its specification clause), the relationship shall be declared `read_with` and stated on both
documents in the notes region.

**Rationale.** Documents are separated in transmission, printing and filing. A `read_with`
statement is the only mechanism that survives separation.

**Validation.** `V-2.8.020`: symmetric closure holds; both containers present in the Package.

### ADOS-2.8.030 — Discipline interfaces

**Decision.** At every interface between disciplines, one discipline shall be declared the
*owner* of the interface geometry and the other the *recipient*. The owner documents it; the
recipient references it and states the exclusion (`ADOS-0.3.090`).

**Implementation.** The interface ownership table is part of the project's Information Delivery
Plan and lists, per interface: element class, owner, recipient, exchange mechanism, frequency.

**Validation.** `V-2.8.030`: for each interface in the table, both an owner document and a
recipient exclusion note exist.

---

## 2.9 Lifecycle

### 2.9.1 Stages

**ADOS-2.9.010 — Stage model.** ADOS uses a seven-stage model, mapped to national frameworks in
`ADOS-A.5`:

| Stage | Name | Question the documentation answers | Dominant document types |
|---|---|---|---|
| 1 | Definition | What is required? | Brief, site information, feasibility |
| 2 | Concept | What is the proposition? | Concept plans, sections, strategies, area schedules |
| 3 | Developed design | Does it work? | Coordinated GA set, strategies, outline specification |
| 4 | Technical design | How is it built? | Construction set, details, full specification, schedules |
| 5 | Construction | What is being built now, and what changed? | Issued packages, RFIs, instructions, site reports |
| 6 | Handover | What was built? | As-built set, O&M, warranties, asset data |
| 7 | In use | How is it operated and adapted? | Asset information model, maintenance record |

**Validation.** `V-2.9.010`: every container declares the stage at which it was authored; package
composition matches the stage table in `ADOS-2.12`.

### ADOS-2.9.020 — Information Delivery Plan

**Decision.** Every project shall maintain an Information Delivery Plan declaring, per stage: the
containers to be produced, their type, responsible party, status target, due date, and the fact
carrier assignments (`ADOS-2.2.010`).

**Validation.** `V-2.9.020`: plan exists; every issued container appears in it; every planned
container has a state.

### ADOS-2.9.030 — Container lifecycle states

```
    ┌─────────┐  create   ┌──────────┐  check   ┌──────────┐  approve  ┌────────────┐
    │ planned │──────────▶│ drafting │─────────▶│ checked  │──────────▶│ authorised │
    └─────────┘           └──────────┘          └──────────┘           └────────────┘
                                │  ▲                  │                       │
                          reject│  │revise            │reject                 │ revise
                                ▼  │                  ▼                       ▼
                            ┌──────────┐         ┌──────────┐          ┌────────────┐
                            │ drafting │         │ drafting │          │ superseded │
                            └──────────┘         └──────────┘          └────────────┘
                                                                              │
                                                                              ▼
                                                                        ┌──────────┐
                                                                        │ archived │
                                                                        └──────────┘
```

**Decision.** A container shall not skip a state. In particular, `drafting → authorised` without
a recorded check is prohibited.

**Validation.** `V-2.9.030`: state history contains no forbidden transition; every authorised
container has a distinct author and checker (`ADOS-8.10.020`).

### ADOS-2.9.040 — Retention and archive

**Decision.** At completion of each stage, the issued packages shall be archived per
`ADOS-0.6.030` and `ADOS-0.6.040`. The archive shall be immutable, checksummed and listed in a
manifest.

**Validation.** `V-2.9.040`: manifest present; checksums verify; archive contains only conforming
formats.

---

## 2.10 Reading sequence

### ADOS-2.10.010 — Set reading order ⚠

**Purpose.** Ensure the physical order of a set matches the order in which its content becomes
interpretable.

**Background.** A reader cannot interpret a detail without knowing the assembly, cannot interpret
the assembly without the building organisation, and cannot interpret the building without the
site. Information has dependencies, and the set order should follow them.

**Decision.** Containers shall be ordered by series (`ADOS-2.5.030`), which is defined so that no
container depends on a later container for its interpretation, except by explicit reference.

**Validation.** `V-2.10.010`: the `depends_on` graph, restricted to interpretation dependencies,
is consistent with series order (no backward interpretation dependency without an explicit
`read_with`).

### ADOS-2.10.020 — Within-sheet reading order

**Decision.** Within a sheet, the primary view shall occupy the upper-left of the drawing area;
secondary views proceed left-to-right then top-to-bottom; notes and legends occupy the right-hand
notes column; the title block occupies the lower-right.

**Rationale (V, R).** For left-to-right scripts, the initial fixation on a large surface falls in
the upper-left quadrant. Placing the primary view there costs the reader nothing. The title block
at lower-right is a strong convention (an interoperability fact) and is also where a rolled or
folded sheet exposes it (`ADOS-3.3.100`, fold rules).

**Exceptions.**
1. Right-to-left script sets mirror the horizontal order; the title block remains lower-right for
   folding compatibility.

**Validation.** `V-2.10.020`: the primary view's centroid lies in the upper-left quadrant of the
drawing area; view ordinal numbering follows the scan order.

### ADOS-2.10.030 — Progressive disclosure

**Decision.** Each sheet shall be interpretable at three depths in sequence: (1) identity and
subject from fixed-position elements alone; (2) organisation from the view titles and key plan;
(3) content from the drawing. A sheet requiring content reading to establish identity is
non-conforming.

**Validation.** `V-2.10.030`: the orientation test (`ADOS-8.6.020`) passes at ≤ 5 s.

---

## 2.11 Set composition and density

### ADOS-2.11.010 — Set-level density

**Decision.** A set shall not rely on a single sheet carrying more than one content level
(`ADOS-2.3.010`). Where a sheet would carry two levels, the content shall be split.

**Rationale.** Mixed-level sheets defeat both the scale rule (`ADOS-4.2.040`, one scale per class)
and the density budget, and they are the primary cause of readers missing detail-level
information.

**Exceptions.**
1. Detail sheets may carry L4 and L5 content together, because assembly and component information
   are read together at the same moment.

**Validation.** `V-2.11.010`: distinct `level` values among views on one sheet ≤ 1, except detail
sheets where ≤ 2 and the pair is {L4, L5}.

### ADOS-2.11.020 — Sheet size uniformity

**Decision.** A set shall use one sheet size. Where a second size is unavoidable (a long site
section), it shall be an ISO A-series size and the set shall declare both, with the smallest
nominated issue size governing all minima (`ADOS-3.2.040`).

**Rationale (R).** Mixed sizes cannot be folded to a common size, do not stack, and defeat the
reduction relationship.

**Validation.** `V-2.11.020`: distinct sheet sizes in the set ≤ 2; all from the A series.

---

## 2.12 Package composition by stage

### ADOS-2.12.010 — Minimum package content ⚠

**Purpose.** Define completeness objectively, so that "is the package complete?" is answerable.

**Decision.** A package issued at a stage shall contain at least the containers marked ● below.
Containers marked ○ are conditional on the project having the relevant condition (for example,
demolition only where existing fabric is removed).

| Container type | S2 Concept | S3 Developed | S4 Technical | S5 Construction | S6 Handover |
|---|---|---|---|---|---|
| Cover sheet | ● | ● | ● | ● | ● |
| Drawing register / index | ● | ● | ● | ● | ● |
| General notes, legends, abbreviations | ● | ● | ● | ● | ● |
| Site location plan | ● | ● | ● | ● | ● |
| Site plan | ● | ● | ● | ● | ● |
| Survey record | ○ | ○ | ○ | ○ | ○ |
| Existing plans | ○ | ○ | ○ | ○ | ○ |
| Demolition plans | — | ○ | ○ | ○ | ○ |
| GA floor plans | ● | ● | ● | ● | ● |
| Roof plan | ● | ● | ● | ● | ● |
| Reflected ceiling plans | — | ● | ● | ● | ● |
| Elevations | ● | ● | ● | ● | ● |
| Sections | ● | ● | ● | ● | ● |
| Enlarged plans | — | ○ | ● | ● | ● |
| Interior elevations | — | ○ | ● | ● | ● |
| Wall / floor / roof types | — | ● | ● | ● | ● |
| Details | — | ○ | ● | ● | ● |
| Door schedule | — | ○ | ● | ● | ● |
| Window schedule | — | ○ | ● | ● | ● |
| Room / finishes schedule | — | ○ | ● | ● | ● |
| Area schedule | ● | ● | ● | ● | ● |
| Fire strategy | ○ | ● | ● | ● | ● |
| Access strategy | ○ | ● | ● | ● | ● |
| Setting-out drawing | — | — | ● | ● | ● |
| Specification | outline | outline | full | full | full |
| Model (IFC) | ● | ● | ● | ● | ● |
| As-built record | — | — | — | — | ● |
| O&M / asset data | — | — | — | — | ● |

**Validation.** `V-2.12.010`: for the declared stage, all ● containers exist with status ≥ the
stage target; every ○ container either exists or has a recorded not-applicable determination.

**Common mistakes.** Issuing a technical package with no setting-out drawing; treating the area
schedule as a concept-stage-only document (it is the earliest and longest-lived quantitative
record and shall be maintained at every stage).

---

## 2.13 The common data environment

### 2.13.1 Why the storage structure is part of the standard

**Problem.** A documentation system with correct containers, statuses and revisions still fails if
the place where those containers live does not enforce the distinction between work in progress,
shared information and published information.

**Rationale (R).** Every control in `ADOS-2.6` — status, supersession, issue records — depends on
there being exactly one location where a recipient looks and exactly one thing they find there. That
is a property of the storage structure, not of the documents.

### ADOS-2.13.010 — CDE state areas ⚠

**Purpose.** Make the permitted use of a container a property of *where it is*, not only of what it
says.

**Decision.** The common data environment shall have four state areas, and a container shall exist in
exactly one of them:

| Area | Contains | Access | Corresponding status |
|---|---|---|---|
| **Work in progress** | Containers under development by their originator | Originator only | `S0` |
| **Shared** | Containers released for coordination, information, review or approval | Project team | `S1`–`S4` |
| **Published** | Containers authorised for use | Team and supply chain | `A`, `B` |
| **Archive** | Every superseded revision, immutably | Read-only, retained | any, historic |

Transition between areas is a controlled act with a recorded approver. A container shall not appear
in two areas.

**Implementation.** Movement to *Published* triggers the supersession operation of `ADOS-2.6.070`
in the same transaction: the previous revision moves to *Archive* and is no longer in *Published*.

**Exceptions.** None.

**Validation.** `V-2.13.010`: each container appears in exactly one area; area membership matches
status; the *Published* area contains exactly one revision of each live container.

**Common mistakes.** A "current" folder containing three revisions of the same drawing; work in
progress shared informally by email, which places an uncontrolled copy outside every area.

### ADOS-2.13.020 — Distribution is by reference ⚠

**Decision.** Containers shall be distributed by reference to the published location, with an issue
record, not by attaching copies. Where a copy must be transmitted (a recipient with no CDE access),
the transmission shall be recorded in the issue record and the copy shall be a complete package, not
an individual container.

**Rationale.** An attached copy has no supersession mechanism. It remains valid-looking on the
recipient's disk indefinitely. Distributing individual containers additionally breaks the
`read_with` relationships of `ADOS-2.8.020`.

**Validation.** `V-2.13.020`: every distribution event has an issue record; individual-container
transmissions = 0.

### ADOS-2.13.030 — Access and confidentiality

**Decision.** Access to each area shall be role-based, and the roles shall match the responsibility
roles of `ADOS-8.10.010`. Confidentiality classification, where a project requires it, shall be a
container attribute and shall appear in the title block and in the file metadata.

**Validation.** `V-2.13.030`: role definitions exist; classification present where declared.

### ADOS-2.13.040 — Immutability of the archive ⚠

**Decision.** Archived containers shall be immutable. A correction to an archived container is a new
revision published through the normal route, never an edit in place.

**Rationale.** The archive is evidence (`ADOS-0.2.4`). An editable archive is not evidence.

**Validation.** `V-2.13.040`: archive checksums stable across audits; modified archive objects = 0.

### ADOS-2.13.050 — Folder structure

**Decision.** Within each area, containers shall be organised by originator, then by container type,
and shall be located by the register (`ADOS-5.2`) rather than by browsing. Folder depth shall not
exceed four levels below the area root (`ADOS-0.3.040`).

**Rationale.** Folder structure is a weak navigation instrument: it supports one hierarchy, while
readers arrive with several different questions. The register is the navigation instrument; the
folder structure exists only to keep the store tractable.

**Validation.** `V-2.13.050`: depth ≤ 4; every container's location derivable from its identifier.

---

## 2.14 Summary of Volume 2

1. The set is a typed graph of Containers, Views, Regions, Annotations, References and Facts.
2. Every fact class has exactly one authoritative carrier; everything else references it.
3. Content sits at one of five levels, chosen by resolvable feature size, at the coarsest level
   that is complete and legible.
4. Four navigation instruments are mandatory, references are reciprocal, and no fact is more
   than three navigation events from the index.
5. Identifiers exist in a full machine form and a short speakable form, are systematic, sortable
   and immutable.
6. Status (permitted use) is orthogonal to revision (generation); both are always visible;
   superseded information is removed, not merely marked.
7. Variation is absorbed by overlays that may only add or tighten.
8. Package completeness by stage is defined as a table, not a judgement.
9. The common data environment has four state areas; a container is in exactly one, and its area
   matches its status.

---

*Continue to [Volume 3 — Visual Language](ADOS-V3-Visual-Language.md).*
