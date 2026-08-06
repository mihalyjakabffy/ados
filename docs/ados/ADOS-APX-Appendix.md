# Appendix

**ADOS 1.0 · Appendix A · Glossary, registers, decision trees, checklists, anti-patterns,
reference layouts.**

---

## A.1 Conventions of this specification

### ADOS-A.1.010 — Rule ID immutability ⚠

**Purpose.** Preserve the value of every citation of a rule ID, in every QA report, drawing-issue
record, template and generation log ever produced.

**Background.** Rule IDs leave this document. They are quoted in build reports, deviation registers
and audit findings that outlive the edition in which they were written.

**Problem.** Renumbering breaks audit trails retroactively and silently: an old report citing
`ADOS-3.4.010` now refers to a different rule.

**Decision.** Rule IDs shall be immutable across all editions. A withdrawn rule retains its ID and is
marked `Status: Withdrawn (superseded by <ID>)`. Ordinals are allocated in tens so that insertions
never force renumbering.

**Implementation.** The registry (`machine/ados-rules.yaml`) is append-only for IDs.

**Exceptions.** None.

**Validation.** `V-A.1.010`: the registry's ID set from edition *n* is a subset of the ID set from
edition *n+1*; removed IDs = 0.

**Examples.** *Conforming:* inserting a rule between `ADOS-3.4.010` and `ADOS-3.4.020` as
`ADOS-3.4.015` (an illustrative identifier, not a defined rule). *Non-conforming:* renumbering `ADOS-3.4.020` to make room.

**Common mistakes.** Regenerating IDs from a table of contents.

**Automation notes.** A CI check diffs the registry against the previous edition and fails on any
removed or reassigned ID.

### A.1.2 Notation

| Notation | Meaning |
|---|---|
| `ADOS-x.y.zzz` | Rule identifier |
| `V-x.y.zzz` | Validation procedure identifier |
| `M<n>.<m>` | Metric sub-metric identifier |
| `E-<CLASS>-<nnn>` | Generator error code |
| `{ados.a.b.c}` | Token reference into `machine/ados-tokens.json` |
| `⚠` | Rule whose violation is Severity 1 |
| `[C]` | Rule applies at Class C conformance |
| **P V C R I A** | Evidence classes: physical, perceptual, cognitive, procedural, interoperability, arithmetic |

### A.1.3 Requirement verbs

`shall` = requirement · `should` = recommendation · `may` = permission · `can` = possibility.
The words *must*, *ought*, *ideally*, *preferably*, *best practice* do not appear in normative text
(`ADOS-7.2.020`).

---

## A.2 Glossary

Terms are defined as used in this specification. Where a term has a different meaning in general
usage, the ADOS meaning governs within ADOS.

| Term | Definition |
|---|---|
| **Adverse reference condition** | The design and verification target: printed at the smallest nominated issue size, reproduced twice monochrome, viewed at 500 mm in 200 lux (`ADOS-0.3.060`). |
| **Annotation** | Any text, dimension, tag, leader, symbol or marker object (`ADOS-2.1.010`). |
| **Authoritative carrier** | The single container that holds a fact class; all other appearances are references (`ADOS-2.2.010`). |
| **Background information** | Content shown for orientation that is not the subject of the sheet; rendered at `T1`/W1 (`ADOS-3.8.050`). |
| **Balance error** | Normalised distance between the ink centroid and the drawing area centre (`ADOS-3.11.020`). |
| **Class A / B / C** | Conformance classes: automated, studio, minimal (`ADOS-0.3.1`). |
| **Clear zone** | Mark-free margin around a text object, `max(0.5 × cap height, 1.0 mm)` (`ADOS-3.4.080`). |
| **Container** | An individually identified information artefact: a sheet, document, model or export. |
| **Content level (L1–L5)** | Context, whole building, part, assembly, component (`ADOS-2.3.010`). |
| **Cut** | Intersected by the view's cut plane; drawn at tier W3. |
| **Defect** | A failed `shall` rule, an undocumented deviation, or a metric outside threshold (`ADOS-8.9.010`). |
| **Deviation Register** | The record of approved departures from `shall` rules (`ADOS-0.3.3`). |
| **Encoding table** | The project's declared mapping of visual states to meanings (`ADOS-3.1.050`). |
| **Escape rate** | Defects found after issue as a fraction of all defects found (`ADOS-8.9.030`). |
| **Evidence class** | The basis of a numeric value: P, V, C, R, I or A (`ADOS-0.8`). |
| **Fact** | An atomic assertion carried by exactly one container. |
| **Fill ratio** | Union of view bounding boxes divided by drawing area (`ADOS-3.7.010`). |
| **Gate** | The binary pass/fail decision before issue (`ADOS-8.10.050`). |
| **Hold** | A marked unresolved item with an owner and resolution date (`ADOS-2.6.080`). |
| **IR (ADOS-IR)** | The intermediate representation: the contract between generation, rendering and validation (`ADOS-7.3`). |
| **Issue** | The act of transmitting a package to recipients, with a record. |
| **Level of information need** | The model content required by the documents that project it (`ADOS-6.3.010`). |
| **Nominated issue size** | The smallest size at which the set is issued; governs every minimum (`ADOS-3.2.040`). |
| **Noise** | Content no defined user needs (`ADOS-0.5.030`). |
| **Overlay** | A declarative layer adding or tightening rules for a jurisdiction, client or practice (`ADOS-2.7.010`). |
| **Package** | Containers issued together for one purpose at one time. |
| **Poché** | Solid fill of cut material at small scales (`ADOS-4.10.050`). |
| **Provenance** | The recorded origin of a value or content item (`ADOS-4.5.090`, `ADOS-7.9.030`). |
| **Reciprocity** | The requirement that every reference has a back-reference (`ADOS-2.4.030`). |
| **Redundancy (purposeful)** | Signal repeated in another channel to protect against loss; permitted only under `ADOS-0.5.030`. |
| **Region** | A named zone of a sheet (`Z-DRAW`, `Z-TITLE`, …). |
| **Resolvable feature size** | `0.5 mm × scale denominator`: the smallest real dimension a scale can depict (`ADOS-4.2.030`). |
| **Salience** | The computed attention-capture proxy used to verify hierarchy (`ADOS-8.3.040`). |
| **Series** | The first digit of a container number, encoding its place in the reading order (`ADOS-2.5.030`). |
| **Set** | All containers produced for a project by one originator. |
| **Status** | Permitted use of a container (`ADOS-2.6.010`), orthogonal to revision. |
| **Sub-module** | 5 mm; the placement lattice (`ADOS-3.3.030`). |
| **Tier (W1/W2/W3)** | The three semantic line weights encoding depth (`ADOS-4.1.020`). |
| **Tone (T0–T5)** | The six-step lightness ladder (`ADOS-3.8.010`). |
| **Type code** | The reference by which an assembly or component type is cited (`ADOS-5.16.010`). |
| **View** | A projection of model content onto a sheet at a stated scale. |
| **Zone (sheet)** | See Region. **Zone (building)** | A spatial subdivision used in container identifiers. |

---

## A.3 Abbreviation register

Only abbreviations in this register may be used (`ADOS-0.5.070`). Practices may extend the register
through their practice overlay; ad-hoc abbreviation is prohibited.

### A.3.1 Levels and dimensions

| Abbreviation | Meaning |
|---|---|
| `FFL` | Finished floor level |
| `SSL` | Structural slab level |
| `SFL` | Structural floor level |
| `FCL` | Finished ceiling level |
| `TOS` | Top of steel |
| `TOW` | Top of wall |
| `TOC` | Top of concrete |
| `SOF` | Soffit level |
| `IL` | Invert level |
| `CLR` | Clear dimension |
| `NOM` | Nominal |
| `TBC` | To be confirmed (requires a hold reference) |
| `TYP` | Typical (requires an applicability statement) |
| `NTS` | Not to scale |
| `(S)` | Survey-derived dimension |
| `(V)` | To be verified on site |
| `EQ` | Equal |
| `MIN` / `MAX` | Minimum / maximum |
| `Ø` | Diameter |
| `R` | Radius |
| `C/C` | Centre to centre |

### A.3.2 Elements and systems

| Abbreviation | Meaning |
|---|---|
| `DPC` | Damp-proof course |
| `DPM` | Damp-proof membrane |
| `AVCL` | Air and vapour control layer |
| `WP` | Waterproofing |
| `INS` | Insulation |
| `CB` | Cavity barrier |
| `FS` | Fire stopping |
| `MJ` | Movement joint |
| `RWP` | Rainwater pipe |
| `RWO` | Rainwater outlet |
| `SVP` | Soil vent pipe |
| `AP` | Access panel |
| `BW` | Blockwork |
| `CW` | Cavity wall |
| `SFS` | Steel framing system |
| `PB` | Plasterboard |
| `SS` | Stainless steel |
| `MS` | Mild steel |
| `RC` | Reinforced concrete |
| `GL` | Glazing |
| `FD30` / `FD60` | Fire door, 30 / 60 minutes |
| `S` (suffix) | Smoke control (as in `FD30S`) |

### A.3.3 Documentation and process

| Abbreviation | Meaning |
|---|---|
| `GA` | General arrangement |
| `RCP` | Reflected ceiling plan |
| `IE` | Interior elevation |
| `WT` | Wall type |
| `RFI` | Request for information |
| `CO` | Change order / instruction |
| `O&M` | Operation and maintenance |
| `CDE` | Common data environment |
| `IDS` | Information delivery specification |
| `BCF` | BIM collaboration format |
| `DSO` | Documentation Standard Owner |
| `IR` | Intermediate representation (ADOS-IR) |

### ADOS-A.3.010 — Register discipline ⚠

**Decision.** An abbreviation used in a set shall appear in the set's abbreviation list, which shall
be a subset of this register plus the practice overlay. Abbreviations shall not be created on a
drawing.

**Validation.** `V-A.3.010`: abbreviations detected in the set ⊆ registered set.

---

## A.4 Code registers

### A.4.1 Discipline codes

| Code | Discipline |
|---|---|
| `A` | Architecture |
| `S` | Structural engineering |
| `M` | Mechanical services |
| `E` | Electrical services |
| `P` | Public health / plumbing |
| `C` | Civil engineering |
| `L` | Landscape |
| `F` | Fire engineering |
| `I` | Interior design |
| `Q` | Cost / quantity surveying |
| `X` | Multi-disciplinary / coordination |

### A.4.2 Container type codes

| Code | Type |
|---|---|
| `DR` | Drawing |
| `SC` | Schedule |
| `SP` | Specification |
| `RP` | Report |
| `MO` | Model |
| `MI` | Minutes |
| `RI` | RFI |
| `CO` | Change order / instruction |
| `IR` | Inspection record |
| `RG` | Register |
| `PH` | Photograph set |
| `CA` | Calculation |

### A.4.3 Level codes

| Code | Level |
|---|---|
| `B2`, `B1` | Basements, descending |
| `00` | Ground |
| `01`…`nn` | Upper levels |
| `MZ` | Mezzanine (suffixed to the level below: `01MZ`) |
| `RF` | Roof |
| `ZZ` | Multiple levels |
| `XX` | Not applicable |

### A.4.4 Zone codes

`ZZ` = whole site/building. Otherwise two characters assigned per project and declared on the cover
sheet. Zone codes shall be spatial, not organisational.

### A.4.5 Status codes

See `ADOS-2.6.010`. The closed set is: `S0 S1 S2 S3 S4 S6 S7 A1..An B1..Bn WD`.

### A.4.6 Element mark prefixes

| Prefix | Element class |
|---|---|
| `D-` | Door |
| `W-` | Window |
| `WT-` | Wall type |
| `FT-` | Floor type |
| `RT-` | Roof type |
| `CT-` | Ceiling type |
| `RM-` | Room (where a prefix is used; otherwise bare room numbers) |
| `IM-` | Ironmongery set |
| `SN-` | Sanitaryware |
| `JN-` | Joinery item |
| `BAL-` | Balustrade |
| `LV-` | Louvre |
| `SG-` | Signage |

---

## A.5 Stage mapping

`ADOS-2.9.010` defines seven stages. Mapping to common national and institutional frameworks:

| ADOS | RIBA Plan of Work | AIA phases | ISO 19650 | Common description |
|---|---|---|---|---|
| 1 Definition | 0–1 Strategic definition, Preparation and briefing | Pre-design | Assessment and need | Brief and feasibility |
| 2 Concept | 2 Concept design | Schematic design | Invitation to tender / appointment | Concept |
| 3 Developed design | 3 Spatial coordination | Design development | Mobilisation | Coordinated design |
| 4 Technical design | 4 Technical design | Construction documents | Collaborative production | Construction information |
| 5 Construction | 5 Manufacturing and construction | Construction administration | Collaborative production | Construction |
| 6 Handover | 6 Handover | Project closeout | Information model delivery | Completion |
| 7 In use | 7 Use | Facility management | Asset information model | Operation |

*Informative.* Where a project uses a framework not listed, the mapping shall be recorded in the
project's Information Delivery Plan.

---

## A.6 Decision trees

### A.6.1 Where does this information belong?

```
Is it geometry (position, size, shape)?
├─ YES → The model. Projected into views. → ADOS-6.1.010
└─ NO
   Is it a property of a component type?
   ├─ YES → Type schedule / wall type sheet. Referenced by code. → ADOS-2.2.010
   └─ NO
      Is it a property of one instance?
      ├─ YES → Instance schedule (door, window, room). Referenced by mark. → ADOS-2.5.060
      └─ NO
         Is it a requirement for material, workmanship, performance or testing?
         ├─ YES → Specification. Referenced by clause. → ADOS-5.22
         └─ NO
            Is it a condition, exclusion or instruction specific to one sheet?
            ├─ YES → Sheet note in Z-NOTES, tagged from the drawing. → ADOS-4.8.020
            └─ NO
               Does it apply to the whole set?
               ├─ YES → General notes sheet. → ADOS-5.3.010
               └─ NO → It is a decision or a query.
                        Decision → design record.  → ADOS-5.30
                        Query    → RFI.            → ADOS-5.25
```

### A.6.2 At what scale, on what drawing?

```
What is the smallest real dimension that must be distinguishable?
   d mm
       │
       ├─ Compute required scale: denominator ≤ d / 0.5      (ADOS-4.2.030)
       ├─ Round DOWN to the next permitted scale              (ADOS-4.2.010)
       └─ Look up the content level for that scale            (ADOS-2.3.010)
              L1 → site drawings
              L2 → GA plans, sections, elevations, strategies
              L3 → enlarged plans, interior elevations
              L4 → wall types, typical details
              L5 → component details, schedules

Is the class already fixed at another scale on this project?
├─ YES → Use the project scale for the class.                 (ADOS-4.2.040)
│         If content does not fit: it belongs at another level, not another scale.
└─ NO  → Fix it now, for the whole class, and record it.
```

### A.6.3 This sheet is too dense. What do I do?

```
Which limit is breached?
├─ Fill ratio > 0.85, or coverage > 0.25, or annotations > 50 per region
│
└─ Apply remedies IN ORDER; stop at the first that resolves:      (ADOS-3.7.040)
   1. Is any content at the wrong content level?
      → Move it. (Most common cause.)
   2. Is any content duplicating an authoritative carrier?
      → Remove it and reference instead.
   3. Can the view be split by area, system or information class?
      → Split it. Add a match line with overlap.
   4. Can the sheet be split?
      → Split it. Allocate the next serial.
   5. Change sheet size? → Set-level decision only.

   NEVER: reduce text size · reduce line width · reduce spacing ·
          remove required content · reduce the clear zone.
```

### A.6.4 May I use colour?

```
Is the distinction already fully carried by weight, type, tone, symbol or text?
├─ NO  → Then colour is the sole carrier. PROHIBITED.  → ADOS-3.10.010
│         Encode it properly first, then reconsider.
└─ YES → Is the deliverable screen-only, markup, or a statutory colour requirement?
         ├─ NO  → Colour adds nothing that survives the reproduction chain. Omit it.
         └─ YES → Permitted as redundant encoding.
                  Verify: ΔL* ≥ 18 between meanings, CVD simulation ΔE ≥ 20,
                  greyscale render passes M1–M4.    → ADOS-3.10.030, ADOS-8.8.010
```

### A.6.5 Is this ready to issue?

```
1. Automated suite run?              NO → run it.
2. S1 defects = 0?                   NO → correct. No exceptions, no registration.
3. S2 defects within the status row? NO → correct or register with an approver.
4. Document type checklist complete? NO → complete it.
5. Checker ≠ author, check recorded? NO → check it properly.
6. Deviations registered & approved? NO → register or correct.
7. Holds current, register issued?   NO → update.
8. References resolve both ways?     NO → fix. Blocking.
9. Approver has reviewed the report? NO → obtain approval.
                                     ALL YES → publish (one automated run).
```

### A.6.6 An RFI has arrived. What is the correct response?

```
Does the issued documentation already answer it?
├─ YES → Answer with the container and clause reference. No document change.
│         Record as a "documentation findability" cause. → ADOS-8.9.040
└─ NO
   Does the answer change the documented design?
   ├─ NO  → Answer with the clarification. Record. Consider whether a note is needed.
   └─ YES → 1. Answer.
            2. Revise the affected containers.       (ADOS-2.6)
            3. Issue them.                            (ADOS-5.32)
            4. Cite the revision in the RFI record.
            5. Only then close the RFI.               (ADOS-5.25.020)
            6. Classify the cause; if it is a documentation defect,
               map it to the rule that would have prevented it. (ADOS-8.9.040)
```

---

## A.7 Anti-patterns

Each anti-pattern names an observed practice, its cost, and the rule that prohibits it. New
anti-patterns are added when RFI cause analysis (`ADOS-8.9.040`) identifies a failure no existing
rule prevented.

### A.7.1 Structural anti-patterns

| # | Anti-pattern | Cost | Prohibited by |
|---|---|---|---|
| AP-01 | **The same fact in three documents** | Divergence on revision; the wrong one is built | `ADOS-0.3.020` |
| AP-02 | **Typed-over dimension** | Silent divergence from the model; discovered on site | `ADOS-6.7.050` |
| AP-03 | **Exploded view** | A live projection becomes a stale copy nobody updates | `ADOS-6.1.030` |
| AP-04 | **Register maintained by hand** | Wrong at the moment of issue, which is when it is read | `ADOS-5.2.010` |
| AP-05 | **Schedule in a spreadsheet** | Diverges from the model within one revision | `ADOS-6.10.010` |
| AP-06 | **Renumbered doors after a layout change** | Every reference in every document becomes wrong | `ADOS-2.5.070` |
| AP-07 | **Location-encoded element marks** | Wrong the moment an element moves | `ADOS-2.5.060` |
| AP-08 | **One-way references** | Change impact is unknowable; details are orphaned | `ADOS-2.4.030` |
| AP-09 | **Superseded drawings left in the current folder** | Construction from superseded information | `ADOS-2.6.070` |
| AP-10 | **"General updates" as a revision description** | The revision register answers nothing | `ADOS-2.6.040` |

### A.7.2 Graphic anti-patterns

| # | Anti-pattern | Cost | Prohibited by |
|---|---|---|---|
| AP-11 | **Nine line weights** | Depth encoding unreadable; reader falls back to geometry | `ADOS-4.1.020` |
| AP-12 | **Line weight by category, not by depth** | The projection's third dimension is lost | `ADOS-4.1.020` |
| AP-13 | **Text shrunk to fit** | Illegible at issue size; the density problem is hidden, not solved | `ADOS-3.4.010` |
| AP-14 | **Unmasked text over hatch** | Both are unreadable after one photocopy | `ADOS-3.4.080` |
| AP-15 | **Model-unit hatch** | Conforms at one scale and fails at every other | `ADOS-6.7.040` |
| AP-16 | **Colour-coded fire strategy with no line differentiation** | Meaningless on the site's monochrome print | `ADOS-3.10.010` |
| AP-17 | **Rotated plan to fit the sheet** | Left/right setting-out errors | `ADOS-4.3.030` |
| AP-18 | **Continuous section line across the plan** | A heavy line through the content, for no gain | `ADOS-4.7.030` |
| AP-19 | **Historical revision clouds retained** | The current change becomes invisible | `ADOS-2.6.050` |
| AP-20 | **Golden-ratio sheet composition** | No functional justification; breaks lattice and template | `ADOS-0.3.010`, §1.4.2 |
| AP-21 | **Seven tones on one sheet** | Adjacent tones merge after reproduction | `ADOS-3.8.020` |
| AP-22 | **Reversed (light on dark) text** | Counters fill in; cannot be marked up on site | `ADOS-3.8.040` |

### A.7.3 Content anti-patterns

| # | Anti-pattern | Cost | Prohibited by |
|---|---|---|---|
| AP-23 | **"Contractor to coordinate"** | A design obligation transferred without the information to discharge it | `ADOS-4.8.040` |
| AP-24 | **"As required" / "to suit"** | The cheapest reading wins | `ADOS-4.8.040`, `ADOS-0.4.030` |
| AP-25 | **Specification text on a drawing** | Duplicate, stale, and outside the specification's revision cycle | `ADOS-5.22.020` |
| AP-26 | **Empty schedule cells** | Omission and non-applicability are indistinguishable | `ADOS-3.12.040` |
| AP-27 | **Unmarked provisional dimension** | Procured against as though fixed | `ADOS-4.5.080` |
| AP-28 | **Assumed existing condition shown as surveyed** | The most expensive class of refurbishment failure | `ADOS-0.4.060` |
| AP-29 | **Detail with two options** | The choice is transferred without the criteria | `ADOS-5.18.020` |
| AP-30 | **Detail with no context** | Applied to the wrong condition | `ADOS-4.11.010` |
| AP-31 | **Open dimension chain** | A single wrong sub-dimension propagates undetected | `ADOS-4.5.030` |
| AP-32 | **Undeclared dimension reference face** | "Blockwork or plaster?" — the most common site query | `ADOS-4.5.060` |
| AP-33 | **Demolition and proposal on one drawing** | Irreversible removal of the wrong element | `ADOS-4.12.020` |
| AP-34 | **Untagged spaces** | Omitted from finishes, unschedulable, unreferenceable | `ADOS-5.4.040` |
| AP-35 | **Standard detail reused unverified** | A correct detail for the wrong project | `ADOS-5.16.040` |
| AP-36 | **Multi-question RFI** | Partial answer, closed record, lost questions | `ADOS-5.25.010` |
| AP-37 | **RFI closed without revising the drawing** | The next reader has the wrong information permanently | `ADOS-5.25.020` |
| AP-38 | **Narrative meeting minutes** | Decisions buried in prose; disputes about what was agreed | `ADOS-5.29.010` |
| AP-39 | **A1 set consumed at A3** | Everything below the legibility floor, with no warning | `ADOS-3.2.040` |
| AP-40 | **Rendering in a construction package** | It will be built from | `ADOS-5.28.010` |

### A.7.4 Process anti-patterns

| # | Anti-pattern | Cost | Prohibited by |
|---|---|---|---|
| AP-41 | **Self-checking** | The mental model that made the error looks for it | `ADOS-8.10.020` |
| AP-42 | **Threshold relaxed to make the set pass** | The gate becomes negotiable exactly when it matters | `ADOS-8.10.080` |
| AP-43 | **Partial issue "to keep site moving"** | Uncontrolled information in circulation | `ADOS-0.7.030` |
| AP-44 | **Per-sheet manual export** | Silent variation, omissions, mismatched names | `ADOS-6.11.010` |
| AP-45 | **Per-project documentation standard** | Reader learning does not transfer; no template investment | §1.10.4 |
| AP-46 | **Health checks run only before issue** | 400 failures the day before an issue cannot be fixed | `ADOS-6.12.020` |
| AP-47 | **Generated content approved by the generator** | Accountability diffused into software | `ADOS-0.4.090` |
| AP-48 | **Language model output consumed directly by the pipeline** | Non-deterministic, unreviewed content in issued documents | `ADOS-7.7.020` |
| AP-49 | **Metrics used as a substitute for design review** | Conforming documentation of an incorrect design | `ADOS-8.1.040` |
| AP-50 | **Deviation taken without registration** | An undocumented defect, indistinguishable from an error | `ADOS-0.3.3` |

---

## A.8 Consolidated checklists

### A.8.1 Universal sheet checklist

Run on every sheet, of every type, before issue.

- [ ] Zoning template applied; all zone origins identical to the set.
- [ ] All title block fields populated; none typed.
- [ ] Status code, banner and watermark correct for the status.
- [ ] Revision code and register current; top row matches the container.
- [ ] Revision clouds present for this revision only.
- [ ] Scope statement present and specific.
- [ ] Read-with list present and reciprocal.
- [ ] Legend covers every graphic state on the sheet, and nothing else.
- [ ] Key plan present where the view is partial; geometry identical set-wide.
- [ ] Scale label per view; graphic scale bar present.
- [ ] North point present, orientation matches the set.
- [ ] Do-not-scale statement present.
- [ ] All references resolve; all reciprocals present.
- [ ] Minimum text 2.5 mm and minimum line 0.18 mm at the nominated issue size.
- [ ] All text masked or in clear zones.
- [ ] Density within all three limits.
- [ ] No content in fold-safe zones.
- [ ] Line tiers monotonic with depth.
- [ ] No manual overrides of derived values.
- [ ] Author, checker and approver recorded; checker ≠ author.

### A.8.2 Set issue checklist

- [ ] Register generated, complete and current.
- [ ] Package composition matches the stage table (`ADOS-2.12.010`).
- [ ] Cover status = lowest container status.
- [ ] Conformance claim present and correct.
- [ ] Nominated issue size declared; minima verified at that size.
- [ ] Every used type code defined; every defined code used.
- [ ] Duplicate-value scan clean.
- [ ] Hold register current; every `TBC` resolves to a hold.
- [ ] Deviation register current, approved, and no entry expired.
- [ ] Exclusions stated at every scope boundary.
- [ ] Greyscale render passes all metrics.
- [ ] Metadata complete on every file.
- [ ] Issue record created; superseded containers moved.
- [ ] Build report retained with matching hashes.

### A.8.3 New project setup checklist

- [ ] Project code, jurisdiction, language, units, decimal separator declared.
- [ ] Overlays selected: jurisdiction, client, practice.
- [ ] Conformance class declared.
- [ ] Sheet size and nominated issue size decided, with the annotation-capacity consequence
      understood (`ADOS-3.2.040`).
- [ ] Plan orientation and datum declared.
- [ ] Dimension reference face convention declared (`ADOS-4.5.060`).
- [ ] Grid convention and setting-out origin established.
- [ ] Classification system declared.
- [ ] Fact carrier assignments made (`ADOS-2.2.010`).
- [ ] Information Delivery Plan created.
- [ ] Trade-off resolutions confirmed or accepted by reference (`ADOS-1.9.010`).
- [ ] Encoding table instantiated.
- [ ] Templates, view templates, pen sets and favorites loaded from the practice standard.
- [ ] Validation configuration loaded, unmodified.
- [ ] Roles assigned: author, checker, approver, DSO, information manager.

### A.8.4 Checker's content checklist

Automated checks verify communication. The checker verifies correctness. This checklist is what the
machine cannot do.

- [ ] Is the design shown actually buildable in the sequence implied?
- [ ] Do the details resolve the conditions that actually occur on this project?
- [ ] Are the interfaces with other disciplines coordinated in fact, not only in reference?
- [ ] Is the fire strategy consistent with what the plans show?
- [ ] Are the dimensions achievable given the tolerances of the materials specified?
- [ ] Does the drawing show what was decided, or what was drawn last time?
- [ ] Would a reader with no context reach the intended conclusion?
- [ ] Is anything shown that the design team has not actually decided?

---

## A.9 Migration and revision control

### ADOS-A.9.010 — Migration table requirement ⚠

**Purpose.** Make a MAJOR edition adoptable without re-auditing every historical document.

**Decision.** A MAJOR edition shall publish a migration table with one row per changed rule:
rule ID, previous requirement, new requirement, affected documents, the action required, and whether
existing conforming documents remain conforming.

**Validation.** `V-A.9.010`: every rule differing between editions has a migration row.

### A.9.2 Migration table format

| Rule ID | Edition n | Edition n+1 | Effect on existing documents | Action |
|---|---|---|---|---|
| *(example)* `ADOS-3.4.010` | min cap 2.5 mm | min cap 3.0 mm | Remain conforming to edition n | Apply to new sets only |

### A.9.3 Document edition citation

Every container cites the edition it was produced under (`ADOS-0.3.2`), and is judged against that
edition (`ADOS-0.3.5`).

---

## A.10 Reference layouts

*Dimensions in millimetres, at authored size. These are the normative geometry of
`ADOS-3.3.010`, expressed graphically.*

### A.10.1 A1 landscape drawing sheet (841 × 594)

```
 ◄──────────────────────────── 841 ───────────────────────────────────────►
┌──────────────────────────────────────────────────────────────────────────┐ ▲
│ 10                                                                       │ │
│  ┌────────────────────────────────────────────────────┬──────────────┐   │ │
│  │ Z-BANNER                                     h=10  │              │   │ │
│  ├────────────────────────────────────────────────────┤   Z-KEY      │   │ │
│  │                                                    │   180 × 60   │   │ │
│  │                                                    ├──────────────┤   │ │
│  │                                                    │              │   │ │
│  │                                                    │   Z-NOTES    │   │ │
│  │              Z-DRAW                                │   180 wide   │   │ 594
│  │              621 × 559                             │   2 columns  │   │ │
│  │                                                    │   85 + 10 +85│   │ │
│  │              column grid:                          │              │   │ │
│  │              6 × 95 + 5 × 10 gutters               ├──────────────┤   │ │
│  │              (residual 1 mm at right)              │   Z-REV      │   │ │
│  │                                                    │   180 × 60+  │   │ │
│  ├────────────────────────────────────────────────────┼──────────────┤   │ │
│  │ Z-GRIDREF  h=5                                     │   Z-TITLE    │   │ │
│  └────────────────────────────────────────────────────┤   180 × 90   │   │ │
│                                                       └──────────────┘   │ │
│ ◄20►                                              ◄────── 180 ──────►◄10► │ │
└──────────────────────────────────────────────────────────────────────────┘ ▼
```

Frame offsets: left 20 (binding), top/right/bottom 10 → frame 811 × 574.
`Z-DRAW` width  = 811 − 180 (right band) − 10 (gutter) = **621**.
`Z-DRAW` height = 574 − 10 (`Z-BANNER`) − 5 (`Z-GRIDREF`) = **559**.
Column grid: 6 × 95 + 5 × 10 = 620, residual 1 mm at the right edge, carrying no content.
All origins on the 5 mm lattice (`ADOS-3.3.030`).

### A.10.2 Title block (180 × 90)

```
┌────────────────────────────────────────────────────────────┬──────────────┐
│ PROJECT NAME                              2.5 mm           │              │
│ Project code · Client                     2.5 mm           │   A3.104     │  ← 7 mm
├────────────────────────────────────────────────────────────┤              │
│ SHEET TITLE                               5.0 mm           │   C03        │  ← 5 mm
│                                                            │   A1 · ISS A3│
├──────────────────────────┬─────────────────────────────────┼──────────────┤
│ Scale  1:100      3.5 mm │ Status  A1  AUTHORISED   5.0 mm │  ⊕ N         │
├──────────────────────────┴─────────────────────────────────┤              │
│ Drawn XY · Checked ZW · Approved QQ · 2026-03-14   2.5 mm   │              │
│ 2317-JKA-ZZ-02-DR-A-3104                          2.5 mm    │              │
├─────────────────────────────────────────────────────────────┴──────────────┤
│ ORIGINATOR NAME · address · contact                              2.5 mm    │
│ Conforms to ADOS 1.0 Class B · DO NOT SCALE · © notice           1.8 mm    │
└────────────────────────────────────────────────────────────────────────────┘
```

Field order follows `ADOS-3.9.030`: sheet number and revision at the outer corner.

### A.10.3 Dimension geometry

```
        ├────────── 2400 ──────────┤        ← text 2.5 mm cap, 1.0 mm above the line
        │                          │
   ─────┼──────────────────────────┼─────   ← dimension line, W1 (0.18)
       ╱                          ╱         ← oblique terminators, 45°, 3.5 mm, W2
        │                          │
        │  ← 2.0 extension beyond  │
        │                          │
   ═════╧══════════════════════════╧═════   ← object, W3
        ◄─2.0─►  offset from object

   first chain offset from object: 10.0
   chain-to-chain spacing:         10.0
```

### A.10.4 Reference bubble (14 mm)

```
        ╭──────────╮
        │    D3    │  ← view identifier, 3.5 mm cap
        ├──────────┤  ← divider, W2
        │  07-014  │  ← container identifier, 3.5 mm cap
        ╰──────────╯
         ◄── 14 ──►
```

### A.10.5 Leader geometry

```
     ●──────────────╱─────── 3.0 ──── D-1108
     ▲              ▲                 ▲
  1.5 dot      45° single         landing, then text
  terminator   segment            (clear zone 1.25 all round)

  permitted angles 30° / 45° / 60°;  length 8–60 mm;  W1
```

### A.10.6 Line tier reference

```
W3  0.70  ████████████████████   cut
W2  0.35  ██████████             seen
W1  0.18  ████                   beyond / hidden / reference

L-CONT   ──────────────────────
L-DASH   ────  ────  ────  ────      dash 4.0, gap 2.0
L-DOT    ·  ·  ·  ·  ·  ·  ·  ·      dot 0.5, gap 1.5
L-CENT   ──────── · ──────── · ─     dash 12.0, gap 2.0, dot 0.5, gap 2.0
```

### A.10.7 Tone ladder

```
T0  L*100  ░░░░░░░░  0 %    paper / void
T1  L* 82  ▒▒▒▒▒▒▒▒  12 %   background, existing to remain
T2  L* 64  ▓▓▓▓▓▓▓▓  26 %   secondary fill
T3  L* 46  ▓▓▓▓▓▓▓▓  42 %   primary fill / poché
T4  L* 28  ████████  60 %   emphasis
T5  L* 10  ████████  88 %   thin cut elements only
```

---

## A.11 Implementation artefact list

A practice adopting ADOS produces the following artefacts once, then reuses them on every project.

| # | Artefact | Derived from | Owner |
|---|---|---|---|
| 1 | Practice overlay (typefaces, identity, library) | `ADOS-2.7.030` | DSO |
| 2 | Jurisdiction overlay(s) | `ADOS-2.7.010` | DSO |
| 3 | Sheet templates per size, per zoning template | `ADOS-3.3.010` | DSO |
| 4 | Title block object, fully parametric | `ADOS-6.9.020` | BIM manager |
| 5 | Pen sets per output purpose | `ADOS-6.7.060` | BIM manager |
| 6 | View template set | `ADOS-6.7.070` | BIM manager |
| 7 | Graphic override rule set | `ADOS-6.7.010` | BIM manager |
| 8 | Hatch and symbol libraries | `ADOS-4.9`, `ADOS-4.10` | DSO |
| 9 | Favorites / type library | `ADOS-6.7.080` | BIM manager |
| 10 | Schedule definitions per document type | Volume 5 | BIM manager |
| 11 | IFC translators / export setups | `ADOS-6.8.020` | BIM manager |
| 12 | Publisher configurations | `ADOS-6.11.010` | BIM manager |
| 13 | Model health check configuration | `ADOS-6.12.010` | BIM manager |
| 14 | Validation configuration (unmodified thresholds) | `machine/ados-validation.yaml` | DSO |
| 15 | Document type checklists | Volume 5 | DSO |
| 16 | Abbreviation and symbol registers | `ADOS-A.3`, `ADOS-4.9.050` | DSO |
| 17 | Standard detail library with verification records | `ADOS-5.16.040` | Technical lead |
| 18 | Specification master | `ADOS-5.22` | Technical lead |
| 19 | Deviation register template | `ADOS-0.3.3` | DSO |
| 20 | Generator conformance fixtures | `ADOS-7.10.010` | Software lead |

---

## A.12 Rule index

Rules are indexed by ID in `machine/ados-rules.yaml`, which is the authoritative index and carries,
per rule: ID, name, volume, chapter, level (`shall`/`should`/`may`), severity, principle references,
evidence class, validation ID, dependencies, and conformance classes.

### A.12.1 Rules by principle

| Principle | Rules |
|---|---|
| P1 Function precedes form | `ADOS-0.3.010`, `ADOS-3.1.010`, `ADOS-3.5.010`, `ADOS-3.9.070`, `ADOS-4.10.010` |
| P2 One fact, one place | `ADOS-0.3.020`, `ADOS-2.2.*`, `ADOS-4.6.030`, `ADOS-4.8.010`, `ADOS-5.16.010`, `ADOS-5.22.020`, `ADOS-6.7.050`, `ADOS-7.6.030`, `ADOS-8.4.050` |
| P3 Strongest channel | `ADOS-0.3.030`, `ADOS-3.1.030`, `ADOS-3.1.040`, `ADOS-3.10.010`, `ADOS-4.1.020`, `ADOS-5.9.020` |
| P4 Shallow explicit hierarchy | `ADOS-0.3.040`, `ADOS-2.3.010`, `ADOS-2.4.050`, `ADOS-3.6.020`, `ADOS-3.13.020` |
| P5 Consistency | `ADOS-0.3.050`, `ADOS-3.3.010`, `ADOS-4.2.040`, `ADOS-4.3.030`, `ADOS-6.7.070`, `ADOS-8.3.010` |
| P6 Adverse context | `ADOS-0.3.060`, `ADOS-3.2.040`, `ADOS-3.4.010`, `ADOS-4.1.010`, `ADOS-8.2.040` |
| P7 Checkability | `ADOS-0.3.070`, `ADOS-8.1.010`, `ADOS-8.1.020`, `ADOS-8.10.040` |
| P8 Automation readiness | `ADOS-0.3.080`, `ADOS-7.*`, `ADOS-6.7.010`, `ADOS-8.9.020` |
| P9 Explicit absence | `ADOS-0.3.090`, `ADOS-3.3.070`, `ADOS-3.12.040`, `ADOS-4.8.060`, `ADOS-5.6.020`, `ADOS-6.10.030` |

### A.12.2 Severity 1 rules (⚠)

The following 262 rules are Severity 1: their violation blocks every issue. This list is generated
from `machine/ados-rules.yaml`.

`ADOS-0.3.010` · `ADOS-0.3.020` · `ADOS-0.3.050` · `ADOS-0.3.070` · `ADOS-0.7.010` ·
`ADOS-0.7.030` · `ADOS-1.9.010` · `ADOS-2.1.010` · `ADOS-2.2.010` · `ADOS-2.2.030` ·
`ADOS-2.3.010` · `ADOS-2.4.010` · `ADOS-2.4.030` · `ADOS-2.4.040` · `ADOS-2.5.010` ·
`ADOS-2.5.020` · `ADOS-2.5.030` · `ADOS-2.5.070` · `ADOS-2.6.010` · `ADOS-2.6.020` ·
`ADOS-2.6.030` · `ADOS-2.6.050` · `ADOS-2.6.060` · `ADOS-2.6.070` · `ADOS-2.7.010` ·
`ADOS-2.8.010` · `ADOS-2.10.010` · `ADOS-2.12.010` · `ADOS-3.1.010` · `ADOS-3.1.020` ·
`ADOS-3.1.050` · `ADOS-3.2.010` · `ADOS-3.2.040` · `ADOS-3.3.010` · `ADOS-3.3.020` ·
`ADOS-3.3.030` · `ADOS-3.3.070` · `ADOS-3.4.010` · `ADOS-3.4.020` · `ADOS-3.4.030` ·
`ADOS-3.4.070` · `ADOS-3.4.080` · `ADOS-3.5.020` · `ADOS-3.6.020` · `ADOS-3.7.010` ·
`ADOS-3.7.020` · `ADOS-3.7.030` · `ADOS-3.7.040` · `ADOS-3.8.010` · `ADOS-3.8.040` ·
`ADOS-3.9.010` · `ADOS-3.9.020` · `ADOS-3.9.040` · `ADOS-3.9.060` · `ADOS-3.10.010` ·
`ADOS-3.11.020` · `ADOS-3.12.010` · `ADOS-3.12.040` · `ADOS-4.1.010` · `ADOS-4.1.020` ·
`ADOS-4.1.050` · `ADOS-4.2.010` · `ADOS-4.2.020` · `ADOS-4.2.030` · `ADOS-4.2.040` ·
`ADOS-4.3.010` · `ADOS-4.3.020` · `ADOS-4.3.030` · `ADOS-4.5.010` · `ADOS-4.5.020` ·
`ADOS-4.5.030` · `ADOS-4.5.060` · `ADOS-4.6.010` · `ADOS-4.6.020` · `ADOS-4.6.030` ·
`ADOS-4.7.010` · `ADOS-4.7.020` · `ADOS-4.8.010` · `ADOS-4.8.040` · `ADOS-4.8.060` ·
`ADOS-4.9.010` · `ADOS-4.10.020` · `ADOS-4.10.030` · `ADOS-4.10.040` · `ADOS-4.11.020` ·
`ADOS-4.12.010` · `ADOS-4.12.020` · `ADOS-5.0.010` · `ADOS-5.0.020` · `ADOS-5.1.010` ·
`ADOS-5.2.010` · `ADOS-5.2.020` · `ADOS-5.3.010` · `ADOS-5.4.010` · `ADOS-5.4.020` ·
`ADOS-5.4.030` · `ADOS-5.4.040` · `ADOS-5.4.050` · `ADOS-5.5.010` · `ADOS-5.6.010` ·
`ADOS-5.6.020` · `ADOS-5.8.010` · `ADOS-5.9.010` · `ADOS-5.9.020` · `ADOS-5.12.010` ·
`ADOS-5.12.020` · `ADOS-5.13.010` · `ADOS-5.13.020` · `ADOS-5.14.010` · `ADOS-5.14.020` ·
`ADOS-5.15.010` · `ADOS-5.16.010` · `ADOS-5.16.020` · `ADOS-5.16.040` · `ADOS-5.17.010` ·
`ADOS-5.18.010` · `ADOS-5.18.020` · `ADOS-5.18.030` · `ADOS-5.19.010` · `ADOS-5.19.020` ·
`ADOS-5.20.010` · `ADOS-5.20.020` · `ADOS-5.20.030` · `ADOS-5.21.010` · `ADOS-5.21.020` ·
`ADOS-5.22.010` · `ADOS-5.22.020` · `ADOS-5.23.010` · `ADOS-5.23.020` · `ADOS-5.24.010` ·
`ADOS-5.24.020` · `ADOS-5.25.010` · `ADOS-5.25.020` · `ADOS-5.26.010` · `ADOS-5.26.020` ·
`ADOS-5.27.010` · `ADOS-5.27.020` · `ADOS-5.28.010` · `ADOS-5.29.010` · `ADOS-5.29.020` ·
`ADOS-5.30.010` · `ADOS-5.31.010` · `ADOS-5.31.020` · `ADOS-5.32.010` · `ADOS-5.32.020` ·
`ADOS-5.33.010` · `ADOS-5.33.020` · `ADOS-5.34.010` · `ADOS-5.34.020` · `ADOS-6.1.010` ·
`ADOS-6.1.020` · `ADOS-6.1.030` · `ADOS-6.2.010` · `ADOS-6.2.020` · `ADOS-6.3.010` ·
`ADOS-6.3.020` · `ADOS-6.3.030` · `ADOS-6.4.010` · `ADOS-6.4.020` · `ADOS-6.4.030` ·
`ADOS-6.4.040` · `ADOS-6.5.010` · `ADOS-6.5.020` · `ADOS-6.5.030` · `ADOS-6.5.040` ·
`ADOS-6.6.010` · `ADOS-6.6.020` · `ADOS-6.7.010` · `ADOS-6.7.020` · `ADOS-6.7.030` ·
`ADOS-6.7.040` · `ADOS-6.7.050` · `ADOS-6.7.060` · `ADOS-6.7.070` · `ADOS-6.7.080` ·
`ADOS-6.8.010` · `ADOS-6.8.020` · `ADOS-6.8.030` · `ADOS-6.8.040` · `ADOS-6.9.010` ·
`ADOS-6.9.020` · `ADOS-6.9.040` · `ADOS-6.10.010` · `ADOS-6.10.030` · `ADOS-6.10.050` ·
`ADOS-6.11.010` · `ADOS-6.11.020` · `ADOS-6.11.030` · `ADOS-6.11.050` · `ADOS-6.11.060` ·
`ADOS-6.12.010` · `ADOS-7.1.010` · `ADOS-7.1.020` · `ADOS-7.2.010` · `ADOS-7.2.020` ·
`ADOS-7.2.030` · `ADOS-7.3.010` · `ADOS-7.3.020` · `ADOS-7.3.030` · `ADOS-7.4.010` ·
`ADOS-7.4.030` · `ADOS-7.4.040` · `ADOS-7.4.050` · `ADOS-7.5.010` · `ADOS-7.5.020` ·
`ADOS-7.5.030` · `ADOS-7.5.040` · `ADOS-7.5.050` · `ADOS-7.5.060` · `ADOS-7.5.070` ·
`ADOS-7.6.010` · `ADOS-7.6.020` · `ADOS-7.6.030` · `ADOS-7.7.010` · `ADOS-7.7.020` ·
`ADOS-7.7.030` · `ADOS-7.8.010` · `ADOS-7.8.020` · `ADOS-7.9.010` · `ADOS-7.9.020` ·
`ADOS-7.9.030` · `ADOS-7.10.010` · `ADOS-7.10.030` · `ADOS-8.1.010` · `ADOS-8.1.020` ·
`ADOS-8.1.030` · `ADOS-8.1.040` · `ADOS-8.2.010` · `ADOS-8.2.020` · `ADOS-8.2.030` ·
`ADOS-8.2.040` · `ADOS-8.2.060` · `ADOS-8.3.010` · `ADOS-8.3.030` · `ADOS-8.3.040` ·
`ADOS-8.3.050` · `ADOS-8.4.010` · `ADOS-8.4.020` · `ADOS-8.4.030` · `ADOS-8.4.040` ·
`ADOS-8.4.050` · `ADOS-8.4.060` · `ADOS-8.5.010` · `ADOS-8.6.010` · `ADOS-8.6.020` ·
`ADOS-8.7.010` · `ADOS-8.8.010` · `ADOS-8.9.010` · `ADOS-8.9.020` · `ADOS-8.9.030` ·
`ADOS-8.9.040` · `ADOS-8.10.010` · `ADOS-8.10.020` · `ADOS-8.10.030` · `ADOS-8.10.040` ·
`ADOS-8.10.050` · `ADOS-8.10.060` · `ADOS-8.10.070` · `ADOS-8.10.080` · `ADOS-A.1.010` ·
`ADOS-A.3.010` · `ADOS-A.9.010`

*Note.* The ⚠ marking in the volume text indicates rules whose violation is classified Severity 1
per `ADOS-8.9.010`. Severity is authoritative in `machine/ados-rules.yaml`; where the marking and
the registry disagree, the registry governs and the discrepancy is a specification defect.

---

## A.13 Closing note

*Informative.*

This specification is long because architectural documentation is a large system and because every
value in it is justified rather than asserted. It is not intended to be memorised. It is intended to
be:

- **read once** for the principles (Volumes 0 and 1),
- **configured once** into templates and validation (Volumes 3, 4, 6 and the machine artefacts),
- **consulted** per document type (Volume 5),
- **executed** automatically thereafter (Volumes 7 and 8).

The measure of its success is not that it is followed. It is that the number of questions a
contractor has to ask falls, and stays fallen, and that in twenty years someone opening the archive
can still read what was meant.

---

*End of the Architectural Documentation Operating System, Edition 1.0.*
