# Volume 5 — Document Types (Part B: Schedules, Specifications, Packages and Records)

**ADOS 1.0 · Volume 5 · Chapters 5.19–5.34.**
Part A (`ADOS-5.0` to `ADOS-5.18`: drawings) is in
[`ADOS-V5-Document-Types.md`](ADOS-V5-Document-Types.md). The template, the universal sheet
requirements (`ADOS-5.0.020`) and the type registry are defined there and are not repeated.

---

## 5.19 Room and Finishes Schedule (`RS`)

**Purpose.** Carry, authoritatively, every fact about every space: its identity, its area, its
environmental requirements and its finishes.

**Users.**

| User | Question |
|---|---|
| Finishing subcontractors | What goes on each surface of each room? |
| Services engineer | What are the environmental requirements of each space? |
| Cost consultant | What is the quantity of each finish? |
| Client / FM | What is each space and what is it for? |
| Certifier | Do the finishes meet the required classifications? |

**Answers.** What is it? · Why / under what condition?

**Required content.**

1. Room number (the key, matching the plan tag) and room name.
2. Level and zone.
3. Floor area and, where relevant, volume and perimeter — generated, marked as generated.
4. Occupancy figure where used by fire or services design (referenced, not restated, where the fire
   strategy is the carrier).
5. Finishes by surface: floor, skirting, walls (by orientation where they differ), ceiling — each by
   reference to a finish code, not a description.
6. Finished ceiling level (FCL) and finished floor level (FFL).
7. Environmental requirements by reference: temperature, ventilation, lighting level, acoustic
   criterion.
8. Fire classification requirement of each finish, by reference.
9. Special requirements: slip resistance, cleanability, impact resistance, containment.
10. Notes column referencing enlarged plans and interior elevations where they exist.

**Optional content.** Occupancy type classification; cleaning regime; asset tagging references.

**Hierarchy.** (1) Room number column; (2) room name; (3) finish columns; (4) requirement columns;
(5) notes.

**Layout logic.** Rooms are ordered by level, then by room number. Room number is leftmost because
it is the search key (`ADOS-3.12.020`). Finish codes rather than descriptions keep the row height at
one line, which preserves the constant row pitch (`ADOS-3.5.030`) that makes horizontal tracking
possible across a wide table.

### ADOS-5.19.010 — Finish codes, not descriptions ⚠

**Decision.** Finishes shall be recorded by code, resolving to a finishes legend that references the
specification. Product names, colours and manufacturers shall not appear in the schedule.

**Rationale.** `ADOS-0.3.020`; also, product substitution during procurement then requires one
change instead of hundreds.

**Validation.** `V-5.19.010`: every finish cell matches the code grammar; free-text finish cells = 0.

### ADOS-5.19.020 — Room number authority ⚠

**Decision.** Room numbers shall be assigned in the model and shall be identical in the schedule, on
the plans, in the door schedule and in the specification. Numbers shall not be reused between
levels.

**Validation.** `V-5.19.020`: room number sets across all carriers are identical; duplicates = 0.

**Quality checklist.**

- [ ] `V-5.19.001` Every room on every plan appears exactly once.
- [ ] `V-5.19.002` No empty cells (`ADOS-3.12.040`).
- [ ] `V-5.19.003` Every finish code resolves to the finishes legend and a specification clause.
- [ ] `V-5.19.004` Areas generated from the model and marked as generated.
- [ ] `V-5.19.005` FFL and FCL stated for every room.
- [ ] `V-5.19.006` Fire classification stated for every finish in escape routes.
- [ ] `V-5.19.007` Generated, timestamped, and consistent with the model.

---

## 5.20 Door Schedule (`DS`)

**Purpose.** Carry every fact about every door, as the authoritative source for procurement,
manufacture, fire certification and installation.

**Users.** Door subcontractor; ironmongery supplier; fire certifier; site supervisor; cost
consultant; access assessor; security consultant.

**Answers.** What is it? · How big is it? · Why / under what condition?

**Required content, per door.**

1. Door mark (the key), matching the plan tag.
2. Location: room from, room to, level, grid reference.
3. Door type reference (leaf configuration, material, finish — by type code).
4. Structural opening size and finished clear opening width and height.
5. Leaf size(s) and thickness.
6. Handing, stated by an unambiguous convention declared on the schedule.
7. Frame type reference and frame material.
8. Fire resistance rating and smoke control requirement (`FD30S`), where applicable.
9. Acoustic performance requirement, where applicable.
10. Security rating, where applicable.
11. Ironmongery set reference (`ADOS-5.25` in the schedule family) — never an ironmongery list.
12. Glazing reference and vision panel position, where applicable.
13. Threshold condition reference.
14. Access requirements: opening force, clear width compliance, visibility panel height.
15. Signage requirement reference.
16. Specification clause reference.
17. Elevation reference where the door has a non-standard elevation.

**Optional content.** Access control zone; door closer power size; undercut for ventilation.

**Hierarchy.** (1) Door mark; (2) location; (3) size; (4) performance; (5) ironmongery and
accessories.

**Layout logic.** A door schedule is wide. It shall be A3 landscape or a large format sheet with the
mark and location columns repeated at each page break so that a row can be identified on any page
(`ADOS-3.12.030`). Where the column count exceeds twelve, the schedule shall be split into a
*door schedule* (identity, size, performance) and a *door specification schedule* (ironmongery,
finishes, accessories), with the mark as the shared key — never by hiding columns.

### ADOS-5.20.010 — Clear opening width mandatory ⚠

**Decision.** Every door shall state its finished clear opening width, measured with the door open
at 90°, in addition to its structural opening and leaf sizes.

**Rationale.** Clear opening width is the dimension that determines accessibility compliance, and it
is not derivable from the leaf size without knowing the frame, the stop, the ironmongery projection
and the opening angle. Its omission is the most common accessibility documentation defect.

**Validation.** `V-5.20.010`: clear width populated for every door; doors on the accessible route
compared to the standard's minimum and flagged where below.

### ADOS-5.20.020 — Fire rating consistency ⚠

**Decision.** Every door in a fire-rated wall shall have a rating consistent with the fire strategy
and the wall type. The check shall be automated across the three carriers.

**Validation.** `V-5.20.020`: for every door, `rating(door) ≥ required(wall type, fire strategy)`;
violations = 0.

### ADOS-5.20.030 — Handing convention ⚠

**Decision.** The handing convention shall be declared on the schedule with a diagram, and shall be
applied uniformly. Handing shall additionally be derivable from the plan geometry.

**Rationale.** Handing conventions differ by country and by manufacturer; an undeclared convention
guarantees a proportion of doors arrive wrong.

**Validation.** `V-5.20.030`: convention diagram present; schedule handing matches model geometry
for every door.

**Quality checklist.**

- [ ] `V-5.20.001` Every door on every plan appears exactly once; every schedule row has a plan
      instance.
- [ ] `V-5.20.002` Clear opening width stated for every door.
- [ ] `V-5.20.003` Fire and smoke ratings consistent with the wall type and fire strategy.
- [ ] `V-5.20.004` Handing convention declared and consistent with geometry.
- [ ] `V-5.20.005` Ironmongery referenced by set, not listed.
- [ ] `V-5.20.006` No empty cells.
- [ ] `V-5.20.007` Specification clause referenced for every row.
- [ ] `V-5.20.008` Accessible route doors verified against the standard.

---

## 5.21 Window Schedule (`WS`)

**Purpose.** Carry every fact about every window and external glazed element.

**Users.** Window subcontractor; façade engineer; thermal assessor; cost consultant; cleaning and
maintenance planner.

**Answers.** What is it? · How big is it? · Why / under what condition?

**Required content, per window.**

1. Window mark; location (room, level, elevation, grid).
2. Type reference; elevation drawing reference showing the configuration.
3. Structural opening size; frame size; glazing sizes.
4. Cill and head levels relative to FFL and to the datum.
5. Opening lights: which, how they open, restrictors, and the free opening area.
6. Glazing specification reference: build-up, safety glazing requirement, solar and thermal
   performance, acoustic performance — by reference.
7. Frame material and finish, by reference.
8. Thermal transmittance requirement of the whole element.
9. Ventilation provision: free area, background ventilation, and the requirement it satisfies.
10. Fall protection: guarding requirement where the cill is below the threshold height.
11. Cleaning and maintenance access reference.
12. Fire performance where the window is in a compartment wall or near a boundary.
13. Specification clause reference.

**Hierarchy and layout logic.** As `ADOS-5.20`.

### ADOS-5.21.010 — Free opening area mandatory ⚠

**Decision.** Every window with an opening light shall state the free opening area and the
requirement it satisfies (ventilation, escape, purge).

**Rationale.** Free area is the compliance quantity and is not derivable from the leaf size.

**Validation.** `V-5.21.010`: free area stated wherever an opening light exists; compared to the
stated requirement.

### ADOS-5.21.020 — Guarding trigger ⚠

**Decision.** Every window whose cill is below the guarding threshold of the jurisdiction shall
state its guarding provision or the reason none is required.

**Validation.** `V-5.21.020`: for every window with `cill_height < threshold`, guarding field
populated.

**Quality checklist.**

- [ ] `V-5.21.001` Every window on every elevation appears exactly once.
- [ ] `V-5.21.002` Cill and head levels stated relative to FFL and datum.
- [ ] `V-5.21.003` Free opening area stated and compared to requirement.
- [ ] `V-5.21.004` Safety glazing identified in all critical locations.
- [ ] `V-5.21.005` Guarding resolved for every low cill.
- [ ] `V-5.21.006` Thermal and acoustic performance referenced.
- [ ] `V-5.21.007` No empty cells; specification clause referenced.

---

## 5.22 Specification (`SP-SPEC`)

**Purpose.** Carry, authoritatively, every requirement of materials, products, workmanship,
performance, testing and completion that is not a geometric fact.

**Users.** Contractor and every subcontractor; cost consultant; certifier; client; the parties to
any dispute.

**Answers.** What is it? · Why / under what condition?

**Required content.**

1. Preliminaries: the project, the parties, the scope, the standards, the general requirements.
2. Work sections, structured by a recognised classification (`ADOS-6.6`), each containing:
   - scope of the section and its interfaces with other sections;
   - products, by performance requirement, by prescription, or by reference to a named product with
     the substitution rule stated;
   - execution: preparation, installation, tolerance, protection;
   - completion: testing, commissioning, records, warranties.
3. General tolerances (`ADOS-4.5.070`).
4. A definitions section carrying the project's controlled vocabulary (`ADOS-0.5.060`).
5. A references section listing every standard cited, with the version and date.
6. A clause numbering system that permits every requirement to be cited individually
   (`ADOS-3.13.020`).

**Optional content.** Sustainability requirements; a schedule of samples and mock-ups; a schedule of
tests.

**Hierarchy.** (1) Section; (2) clause group; (3) clause; (4) sub-clause. Maximum four levels
(`ADOS-3.13.020`).

**Layout logic.** Per `ADOS-3.13`: A4, marginal column carrying clause numbers and revision bars,
measure ≤ 135 mm, running heads on every page. Requirements are one per clause, so that a clause
citation is unambiguous.

### ADOS-5.22.010 — One requirement per clause ⚠

**Decision.** A numbered clause shall contain exactly one requirement. A clause containing two
requirements shall be split.

**Rationale.** A clause is the unit of citation, of compliance and of dispute. Two requirements in
one clause cannot be separately accepted, rejected or varied.

**Validation.** `V-5.22.010`: clauses containing more than one modal verb of obligation = 0.

### ADOS-5.22.020 — Specification/drawing boundary ⚠

**Decision.** The specification shall carry no geometry and no location; drawings shall carry no
performance requirement, material description or workmanship requirement.

**Rationale.** `ADOS-2.2.010`. The boundary is a hard one because the two documents are revised on
different cycles by different people.

**Validation.** `V-5.22.020`: dimension patterns in specification text = 0 (excluding tolerances and
product sizes); specification-content patterns on drawings = 0.

### ADOS-5.22.030 — Performance versus prescription

**Decision.** Each specified item shall be declared as *performance* (the contractor selects and is
responsible for compliance) or *prescription* (the designer selects and is responsible), and the
declaration shall be explicit. Mixed clauses that prescribe a product and also require a performance
the product may not meet are prohibited.

**Rationale.** The declaration allocates design responsibility. Ambiguity here is the origin of a
large fraction of construction disputes.

**Validation.** `V-5.22.030`: every product clause carries a `performance` or `prescription` tag.

### ADOS-5.22.040 — Standards citation

**Decision.** Every standard cited shall be cited with its number, year and title on first use and
listed in the references section. Undated citations ("to the current standard") shall not be used.

**Rationale.** Standards change. An undated citation changes the contractual requirement without a
variation.

**Validation.** `V-5.22.040`: undated standard citations = 0.

**Quality checklist.**

- [ ] `V-5.22.001` Every drawing reference to a clause resolves.
- [ ] `V-5.22.002` Every specified item is either performance or prescription, declared.
- [ ] `V-5.22.003` One requirement per clause.
- [ ] `V-5.22.004` No geometry or location in the specification.
- [ ] `V-5.22.005` All standards dated and listed.
- [ ] `V-5.22.006` Controlled vocabulary defined and used consistently.
- [ ] `V-5.22.007` General tolerances stated once.
- [ ] `V-5.22.008` Every work section has an interface statement.

---

## 5.23 Area Schedule (`AR`)

**Purpose.** State the areas of the project on a declared measurement basis, as the quantitative
record used for briefing compliance, valuation, planning and taxation.

**Users.** Client; cost consultant; planning authority; valuer; agent; design team.

**Answers.** How big is it?

**Required content.**

1. The declared measurement standard and its version.
2. Areas by level and by category (gross internal, net internal, net lettable, circulation, plant,
   as the standard defines).
3. Efficiency ratios where the brief states them.
4. Comparison against the brief target, with variance.
5. Areas by unit or tenancy where the project has them.
6. External areas, separately.
7. Generation timestamp, model source and model version.
8. A statement of the exclusions and inclusions applied.

**Layout logic.** Levels as rows, categories as columns, totals as a final row, with the brief
comparison alongside. The comparison column is required because the area schedule's function is not
to state areas but to answer whether the design meets the brief.

### ADOS-5.23.010 — Measurement basis declared ⚠

**Decision.** The area schedule shall declare the measurement standard, version and the treatment of
every boundary condition it does not resolve.

**Rationale.** Areas measured on different bases differ by 5–15 %. An undeclared basis makes the
schedule unusable for the decisions it exists to support.

**Validation.** `V-5.23.010`: standard, version and exclusions statement present.

### ADOS-5.23.020 — Areas are generated ⚠

**Decision.** Areas shall be generated from the model, never measured from drawings or maintained by
hand.

**Validation.** `V-5.23.020`: schedule equals the model query; timestamped.

**Quality checklist.**

- [ ] `V-5.23.001` Measurement standard and version declared.
- [ ] `V-5.23.002` Generated from the model, timestamped, model version recorded.
- [ ] `V-5.23.003` Every room in the room schedule is included or explicitly excluded.
- [ ] `V-5.23.004` Brief comparison present with variance.
- [ ] `V-5.23.005` Totals reconcile: Σ categories = gross.

---

## 5.24 Tender Package (`TP`)

**Purpose.** Provide tenderers with a complete, unambiguous and equal basis on which to price the
work.

**Users.** Tenderers; cost consultant; client; the party who later administers the contract.

**Answers.** All five, through its constituents.

**Required content.**

1. Invitation and instructions to tenderers, stating the return date, format and query mechanism.
2. The drawing register listing exactly the containers in the package, with revisions
   (`ADOS-5.2`).
3. The full drawing set at the declared status.
4. The specification.
5. The schedules.
6. Preliminaries and any pricing document.
7. Site information: survey, ground investigation, existing records, with provenance and reliance
   statements.
8. The hold register (`ADOS-2.6.080`) listing every unresolved item.
9. The exclusions and provisional items list.
10. The programme constraints.
11. A statement of the standards to which the documentation conforms.

**Layout logic.** The package is an assembly, not a document; its quality is the completeness and
consistency of its constituents plus the correctness of its register.

### ADOS-5.24.010 — Tender package completeness ⚠

**Decision.** A tender package shall contain no unresolved reference, no `TBC` without a hold
register entry, and no container at a status below the declared package status.

**Rationale.** Every gap becomes either a tender query (cost: days of programme) or a priced risk
allowance (cost: money, invisibly).

**Validation.** `V-5.24.010`: unresolved references = 0; unregistered `TBC` = 0; status floor
satisfied.

### ADOS-5.24.020 — Equal information ⚠

**Decision.** Every tenderer shall receive an identical package. Any information issued to one
tenderer during the tender period shall be issued to all, as a numbered addendum recorded in the
issue record.

**Validation.** `V-5.24.020`: issue records show identical container sets per recipient; addenda
distributed to all.

**Quality checklist.**

- [ ] `V-5.24.001` Register matches the package exactly.
- [ ] `V-5.24.002` No unresolved references or unregistered holds.
- [ ] `V-5.24.003` Site information provenance and reliance stated.
- [ ] `V-5.24.004` Exclusions and provisional items listed.
- [ ] `V-5.24.005` Identical distribution to all tenderers, recorded.
- [ ] `V-5.24.006` Status consistent across every container.

---

## 5.25 Request for Information (`RFI`)

**Purpose.** Obtain a decision or clarification that the issued documentation does not provide, and
record it.

**Users.** Contractor (raiser); design team (responder); cost consultant; contract administrator;
the archive.

**Answers.** Why / under what condition?

**Required content.**

1. RFI number (sequential, project-unique) and revision.
2. Date raised and date response required, with the justification for the date.
3. Raiser and responder.
4. Subject and location: container reference, grid, level, room.
5. The question, stated as one question.
6. The context: what the documentation says, and why it is insufficient.
7. The raiser's proposed answer, where they have one.
8. Cost and programme implication, as assessed by the raiser.
9. The response, with its author and date.
10. The consequence of the response: containers to be revised, instructions to be issued.
11. Status: open, answered, closed.

**Layout logic.** One RFI per document, A4, with the question and response on the first page. An RFI
that requires attachments references them; it does not embed drawings, because embedded drawings
become uncontrolled copies.

### ADOS-5.25.010 — One question per RFI ⚠

**Decision.** An RFI shall contain exactly one question.

**Rationale.** A multi-question RFI receives a partial answer, is closed, and the unanswered parts
are lost. Tracking, cost attribution and programme impact all require one question per record.

**Validation.** `V-5.25.010`: RFIs with more than one interrogative = 0.

### ADOS-5.25.020 — RFI closure requires document action ⚠

**Decision.** An RFI whose answer changes the documented design shall not be closed until the
affected containers have been revised and issued. The RFI record shall cite the revision.

**Rationale.** An answered RFI is not documentation. The next reader of the drawing does not have
the RFI. Without this rule, the drawing and the built work diverge permanently.

**Validation.** `V-5.25.020`: for every closed RFI with `changes_design = true`, a container
revision citing the RFI exists.

### ADOS-5.25.030 — RFI trend analysis

**Decision.** The RFI register shall be analysed at each project stage for concentration by
container, by subject and by cause; concentrations shall be fed back into the documentation
standard as anti-patterns (`ADOS-A.7`).

**Rationale.** RFIs are the direct measurement of documentation failure. A practice that answers
RFIs without analysing them pays for the same defect on every project.

**Validation.** `V-5.25.030`: analysis record exists per stage; top causes recorded.

**Quality checklist.**

- [ ] `V-5.25.001` One question, stated as a question.
- [ ] `V-5.25.002` Location and container references present and resolving.
- [ ] `V-5.25.003` Context states what the documentation currently says.
- [ ] `V-5.25.004` Response has an author and a date.
- [ ] `V-5.25.005` Design-changing responses cite the resulting revision before closure.
- [ ] `V-5.25.006` Cost and programme implications recorded.

---

## 5.26 Change Order / Instruction (`CO`)

**Purpose.** Instruct a change to the works, with its scope, its authority, and its cost and
programme consequence, and to bind that change to the documents that record it.

**Users.** Contractor; cost consultant; client; contract administrator; auditor.

**Answers.** What is it? · Why / under what condition?

**Required content.**

1. Instruction number and date.
2. The authority under which it is issued (the contract clause).
3. The originator and the approver, with the approval record.
4. Description of the change, stated as an instruction.
5. The reason for the change, classified (design development, client change, statutory, error,
   unforeseen condition, coordination).
6. The containers affected, with their revisions before and after.
7. Cost effect: agreed, estimated, or to be agreed, with the basis.
8. Programme effect: agreed, estimated, or to be agreed.
9. The instruction's effect on other instructions, where they interact.

**Layout logic.** A4, one instruction per document, with the cost and programme consequences on the
first page because they are the fields most frequently retrieved.

### ADOS-5.26.010 — Change classification ⚠

**Decision.** Every change shall be classified by cause from the closed set above.

**Rationale.** Classification enables the practice to measure how much of its change volume
originates in its own documentation, which is the only route to reducing it.

**Validation.** `V-5.26.010`: every instruction has a cause from the closed set.

### ADOS-5.26.020 — Instruction and document revision are coupled ⚠

**Decision.** An instruction changing the design shall reference the container revisions that
implement it, and those revisions shall reference the instruction in their revision description.

**Validation.** `V-5.26.020`: bidirectional reference exists for every design-changing instruction.

**Quality checklist.**

- [ ] `V-5.26.001` Authority cited.
- [ ] `V-5.26.002` Cause classified.
- [ ] `V-5.26.003` Affected containers listed with before/after revisions.
- [ ] `V-5.26.004` Cost and programme effects stated, even if "to be agreed".
- [ ] `V-5.26.005` Bidirectional reference with the implementing revisions.
- [ ] `V-5.26.006` Approver recorded.

---

## 5.27 Design-Stage Documents (`DD`)

**Purpose.** Communicate a developing proposition, its options and its rationale, at a stage where
the design is not yet a set of instructions.

**Users.** Client; design team; stakeholders; authorities in pre-application discussion.

**Answers.** Where is it? · Why / under what condition?

**Required content.**

1. Status `S0`–`S2` and the explicit statement `NOT FOR CONSTRUCTION`.
2. A statement of what is fixed and what is open at this stage.
3. The options considered and the criteria against which they are compared, where the document
   presents options.
4. The recommendation and its rationale, where the document recommends.
5. The decision required from the reader, and by when.
6. Any dimensional information marked as indicative.

**Layout logic.** Design-stage documents may use presentation conventions (`ADOS-5.28`) but shall
retain the identity, status and revision apparatus of `ADOS-5.0.020` items 2–4, because they are
issued, referenced and archived like any other container.

### ADOS-5.27.010 — Explicit decision request ⚠

**Decision.** Every design-stage document issued to a client shall state the decision it requires
and the date by which it is required.

**Rationale.** Design-stage documents that present without asking produce silence, which is later
interpreted as approval by one party and as non-approval by the other.

**Validation.** `V-5.27.010`: decision request block present and non-empty.

### ADOS-5.27.020 — Indicative content marking ⚠

**Decision.** Dimensional and quantitative content in a design-stage document shall be marked
indicative, or the document shall state its overall precision.

**Rationale.** `ADOS-0.4.020`. Concept-stage areas and dimensions are quoted in business cases and
become targets.

**Validation.** `V-5.27.020`: indicative marking or precision statement present.

**Quality checklist.**

- [ ] `V-5.27.001` Status and `NOT FOR CONSTRUCTION` statement present.
- [ ] `V-5.27.002` Fixed/open statement present.
- [ ] `V-5.27.003` Decision request stated with a date.
- [ ] `V-5.27.004` Options presented against stated criteria.
- [ ] `V-5.27.005` Quantitative content marked indicative.
- [ ] `V-5.27.006` Identity, status and revision apparatus present.

---

## 5.28 Presentation Documents (`PR`)

**Purpose.** Communicate the experience and intent of a design to a non-technical audience.

**Users.** Client; public; planning committee; investors; jury.

**Answers.** None of the five. Presentation documents are not technical documentation and shall not
be relied on as such.

**Required content.**

1. A status statement and the explicit label `ILLUSTRATIVE — NOT A CONSTRUCTION DOCUMENT`.
2. Source and date of every image; a generated-image statement where applicable
   (`ADOS-4.11.060`).
3. Where an image depicts a condition that is not yet resolved, a statement to that effect.
4. Identity and revision apparatus.

**Permitted deviations.** Presentation documents are the single class exempt from the visual
constraints of Volume 3 §§3.4–3.8 and the drawing constraints of Volume 4, on the condition that
they are not issued as part of a technical package and are watermarked accordingly.

### ADOS-5.28.010 — Segregation from technical documentation ⚠

**Decision.** Presentation documents shall not be included in a technical package, shall not be
referenced by a technical container as a source of requirement, and shall carry the illustrative
label.

**Rationale.** `ADOS-0.4.040`. A rendering in a construction package will be built from.

**Validation.** `V-5.28.010`: presentation containers in technical packages = 0; references from
technical containers = 0.

### ADOS-5.28.020 — Honesty constraints still apply

**Decision.** `ADOS-0.4.040` to `ADOS-0.4.060` apply in full to presentation documents. Depicting an
unresolved condition as resolved, or an assumed existing condition as surveyed, is prohibited
regardless of the document's status.

**Quality checklist.**

- [ ] `V-5.28.001` Illustrative label present.
- [ ] `V-5.28.002` Every image sourced and dated; generated images labelled.
- [ ] `V-5.28.003` Unresolved conditions stated.
- [ ] `V-5.28.004` Not included in or referenced from technical packages.

---

## 5.29 Meeting Minutes (`MM`)

**Purpose.** Record decisions, actions and information exchanged, so that the project has a single
authoritative account of what was agreed.

**Users.** Attendees; absentees; the design team; the archive; the parties to any dispute.

**Answers.** Why / under what condition?

**Required content.**

1. Meeting identifier, series, number, date, time, location or platform.
2. Attendees, apologies, and distribution list.
3. Reference to the previous minutes and confirmation of their acceptance.
4. Items, each numbered with a persistent number carried forward until closed, each recording:
   the discussion in one or two sentences, the **decision** (or "no decision"), the **action**, the
   **owner**, and the **due date**.
5. Actions carried forward from previous meetings, with status.
6. Decisions register: decisions made at this meeting, listed separately for retrieval.
7. Next meeting details.

**Layout logic.** A4, item number in the marginal column, action owner and date in a right-hand
column so that a reader can scan for their own actions in one vertical pass. This is the layout's
whole purpose: minutes are read by people looking for their own name.

### ADOS-5.29.010 — Decision and action separation ⚠

**Decision.** Each item shall separately record what was decided and what is to be done. An item
with neither shall be recorded as information only.

**Rationale.** Narrative minutes bury decisions in prose and produce disputes about whether
something was agreed. The structural separation makes the decision retrievable.

**Validation.** `V-5.29.010`: every item has a decision field and an action field, each populated or
explicitly marked "none".

### ADOS-5.29.020 — Persistent item numbering ⚠

**Decision.** An item number shall be assigned once and carried forward unchanged until the item is
closed, with the closing meeting recorded.

**Rationale.** Renumbering each meeting destroys the ability to trace an issue's history, which is
the primary use of minutes months later.

**Validation.** `V-5.29.020`: item numbers stable across the series; closure recorded.

### ADOS-5.29.030 — Minutes are not instructions

**Decision.** Minutes shall not instruct a change to the works. Where a meeting decision requires a
change, an instruction shall be issued (`ADOS-5.26`) and the minute shall reference it.

**Rationale.** Minutes are distributed to people who are not parties to the contract, are not
formally issued as controlled documents, and are frequently unread. Change instruction requires a
controlled document.

**Validation.** `V-5.29.030`: minutes containing instruction language without an instruction
reference = 0.

**Quality checklist.**

- [ ] `V-5.29.001` Attendees, apologies and distribution recorded.
- [ ] `V-5.29.002` Every item has decision, action, owner and due date fields.
- [ ] `V-5.29.003` Item numbers persistent; carried-forward items listed with status.
- [ ] `V-5.29.004` Decisions register present.
- [ ] `V-5.29.005` No instruction language without an instruction reference.
- [ ] `V-5.29.006` Issued within the declared period after the meeting.

---

## 5.30 Design Record / Decision Log (`DR`)

**Purpose.** Record why the design is as it is: the decisions, their alternatives, their criteria and
their constraints, so that a future reader can distinguish a deliberate choice from an accident.

**Users.** The design team over the project's life; the practice's future projects; the client's
future advisers; anyone adapting the building; anyone investigating a failure.

**Answers.** Why / under what condition?

**Required content, per decision.**

1. Decision identifier and date.
2. The question decided, stated as a question.
3. The options considered.
4. The criteria applied and their weighting or priority.
5. The decision and the decider.
6. The constraints that bound the decision (statutory, budget, brief, site, structural).
7. The consequences accepted, including known disadvantages.
8. The containers that implement the decision.
9. Review trigger: the condition under which the decision should be revisited.

**Layout logic.** One record per decision, chronological, with an index by subject. The disadvantage
field is mandatory because a decision record listing only advantages is a justification, not a
record, and is useless to the future reader.

### ADOS-5.30.010 — Consequences accepted ⚠

**Decision.** Every decision record shall state the disadvantages accepted. A record with none is
non-conforming.

**Rationale.** Every real decision has a cost. Recording only the benefits produces a document that
cannot be used to reassess the decision when circumstances change — which is the purpose of keeping
it.

**Validation.** `V-5.30.010`: `consequences_accepted` non-empty for every record.

### ADOS-5.30.020 — Decision-to-container binding

**Decision.** Every decision record shall list the containers that implement it, and significant
containers shall list the decisions that govern them.

**Validation.** `V-5.30.020`: bidirectional mapping exists for every decision classified as
significant.

**Quality checklist.**

- [ ] `V-5.30.001` Question stated as a question.
- [ ] `V-5.30.002` Options and criteria recorded.
- [ ] `V-5.30.003` Decider recorded.
- [ ] `V-5.30.004` Disadvantages accepted recorded.
- [ ] `V-5.30.005` Implementing containers listed.
- [ ] `V-5.30.006` Review trigger stated.

---

## 5.31 Site Report / Inspection Record (`SR`)

**Purpose.** Record the observed state of the works at a point in time, against the documented
design.

**Users.** Client; contractor; contract administrator; certifier; the archive; insurers.

**Answers.** Where is it? · Why / under what condition?

**Required content.**

1. Report number, date, time, weather, and the inspector.
2. Purpose of the visit and the scope inspected, with what was not inspected stated explicitly
   (`ADOS-0.3.090`).
3. Progress observed, against the programme, by area.
4. Observations, each with: location (grid, level, room), the documented requirement with its
   container reference, the observed condition, and the assessment (conforming, non-conforming,
   cannot determine).
5. Photographs, each numbered, located, dated and referenced from the observation.
6. Actions with owners and dates.
7. Items closed since the previous report.
8. A statement of the limitations of the inspection (what could not be seen, what was covered up).

**Layout logic.** Observations are the content; each is a self-contained record with location,
requirement, observation and assessment in a fixed order, so that a reader following up months later
can reconstruct the situation.

### ADOS-5.31.010 — Requirement citation ⚠

**Decision.** Every non-conformity shall cite the container and clause that states the requirement.

**Rationale.** A non-conformity without a citation is an opinion. With a citation it is a
verifiable statement, and the contractor can act on it without a further exchange.

**Validation.** `V-5.31.010`: every observation assessed non-conforming has a resolving reference.

### ADOS-5.31.020 — Scope limitation statement ⚠

**Decision.** Every inspection record shall state what was not inspected and why.

**Rationale.** `ADOS-0.3.090`, and the professional liability consequence: an inspection record
silent on its limits will be read as covering everything.

**Validation.** `V-5.31.020`: limitation statement present and non-empty.

**Quality checklist.**

- [ ] `V-5.31.001` Date, time, weather, inspector recorded.
- [ ] `V-5.31.002` Scope inspected and not inspected stated.
- [ ] `V-5.31.003` Every observation located to grid/level/room.
- [ ] `V-5.31.004` Every non-conformity cites its requirement.
- [ ] `V-5.31.005` Photographs numbered, located, dated, referenced.
- [ ] `V-5.31.006` Actions have owners and dates.
- [ ] `V-5.31.007` Previous items' status updated.

---

## 5.32 Construction Issue Package (`CI`)

**Purpose.** Transmit authorised information to the site, such that the recipient can determine
completeness, currency and permitted use without further enquiry.

**Users.** Contractor; subcontractors; site manager; document controller.

**Required content.**

1. Transmittal listing every container, revision, status and sheet size.
2. The reason for issue.
3. Instructions on superseded material: which containers are superseded and shall be withdrawn from
   use (`ADOS-2.6.070`).
4. The recipient list.
5. The register (`ADOS-5.2`) reflecting the post-issue state.
6. The hold register update.
7. Acknowledgement mechanism.

### ADOS-5.32.010 — Supersession instruction ⚠

**Decision.** Every construction issue shall list the container revisions it supersedes and instruct
their withdrawal.

**Rationale.** `ADOS-2.6.070`: removal is the only reliable control, and removal requires an
instruction naming what to remove.

**Validation.** `V-5.32.010`: for every container revised in the issue, a supersession entry exists.

### ADOS-5.32.020 — Status floor ⚠

**Decision.** A construction issue shall contain only containers at status `A` or `B`. A `B`-status
container shall carry an annotation identifying the parts not authorised.

**Validation.** `V-5.32.020`: container statuses ∈ {A*, B*}; `B` containers carry the annotation.

**Quality checklist.**

- [ ] `V-5.32.001` Transmittal complete and matching the package.
- [ ] `V-5.32.002` All containers at `A` or `B`.
- [ ] `V-5.32.003` Supersession instruction present.
- [ ] `V-5.32.004` Register updated and included.
- [ ] `V-5.32.005` Hold register current.
- [ ] `V-5.32.006` Acknowledgement requested and tracked.

---

## 5.33 As-Built Record (`AB`)

**Purpose.** Record what was actually built, so that the building can be operated, maintained,
adapted and, if necessary, investigated.

**Users.** Building owner and operator; facilities manager; future designers; investigators;
insurers.

**Answers.** All five, as a record rather than an instruction.

**Required content.**

1. The full drawing set updated to reflect the works as executed, at status `S7`/handover, with
   every construction-stage change incorporated.
2. A statement, per container, of the basis of the as-built information: contractor's record,
   surveyed, verified by inspection, or unverified.
3. The schedules updated to as-installed products and marks.
4. The specification with substitutions and approved alternatives recorded.
5. The register of instructions and their incorporation.
6. Concealed work records: photographs and measurements of work covered up, indexed to location.
7. Survey of the completed building where accuracy is required for future work.
8. The model, updated, exported to IFC (`ADOS-6.8`).

### ADOS-5.33.010 — As-built provenance ⚠

**Decision.** Every as-built container shall state the basis of its as-built information, per
container or per area. Unverified contractor mark-ups shall be labelled as such.

**Rationale.** `ADOS-0.4.050`. As-built documentation is relied on decades later for irreversible
decisions. The difference between "surveyed" and "the contractor said so" is the difference between
a usable record and a hazard.

**Validation.** `V-5.33.010`: basis statement present on every container; unverified content
labelled.

### ADOS-5.33.020 — Concealed work record ⚠

**Decision.** Work that is covered up and cannot subsequently be inspected shall be recorded before
covering, with dated photographs indexed to grid and level, and measurements of anything whose
position matters (services routes, fixings, reinforcement, cavity barriers, waterproofing laps).

**Rationale.** The cost of exposing concealed work later is orders of magnitude greater than the
cost of photographing it. This is the highest-return documentation activity on any project.

**Validation.** `V-5.33.020`: concealed work register complete against the schedule of concealed
elements; every entry located and dated.

**Quality checklist.**

- [ ] `V-5.33.001` Every instruction incorporated or explicitly excluded with reason.
- [ ] `V-5.33.002` Basis of as-built information stated per container.
- [ ] `V-5.33.003` Concealed work recorded and indexed.
- [ ] `V-5.33.004` Schedules reflect installed products.
- [ ] `V-5.33.005` Substitutions recorded in the specification.
- [ ] `V-5.33.006` Model exported and validated (`ADOS-6.8`).
- [ ] `V-5.33.007` Archive conforming (`ADOS-0.6.030`, `ADOS-0.6.040`).

---

## 5.34 Operation, Maintenance and Asset Information (`OM`)

**Purpose.** Provide the information required to operate, maintain, repair and replace the building
and its components safely and economically.

**Users.** Facilities manager; maintenance contractor; owner; occupier; future project teams.

**Answers.** What is it? · Why / under what condition?

**Required content.**

1. Building description and the as-built set reference.
2. Asset register: every maintainable item with its identifier, location, classification, type,
   manufacturer, model, installation date, expected life and replacement route.
3. Maintenance requirements per asset class, with frequency and the standard applied.
4. Operating instructions for systems the occupier controls.
5. Health and safety file content required by the jurisdiction: residual hazards, structural
   assumptions, hazardous materials, safe access provisions.
6. Warranties and guarantees, with their start dates, durations, conditions and the actions that
   void them.
7. Test and commissioning records.
8. Spares and consumables schedule.
9. Statutory certificates.
10. Contact register for the parties responsible for each system.

### ADOS-5.34.010 — Asset identifiers match the model ⚠

**Decision.** Asset identifiers in the O&M information shall be identical to the element marks used
in the model and the documentation (`ADOS-2.5.060`).

**Rationale.** A separate FM numbering system severs the link between the asset and its
documentation permanently; re-establishing it later requires a full re-survey.

**Validation.** `V-5.34.010`: asset register identifiers ⊆ model mark set; unmatched = 0.

### ADOS-5.34.020 — Residual hazard statement ⚠

**Decision.** The O&M information shall state every residual hazard that a person maintaining,
altering or demolishing the building would not reasonably anticipate, with its location.

**Validation.** `V-5.34.020`: hazard register present; every hazard located; sign-off recorded.

### ADOS-5.34.030 — Machine-readable asset data

**Decision.** The asset register shall be delivered in a machine-readable structured format (IFC
with property sets, or a defined tabular exchange) in addition to any human-readable form.

**Rationale.** `ADOS-0.4.080`. An asset register delivered only as a PDF cannot be loaded into a
maintenance system and will be re-keyed, with errors, or not used.

**Validation.** `V-5.34.030`: structured export present and schema-valid.

**Quality checklist.**

- [ ] `V-5.34.001` Every maintainable asset registered with a model-matching identifier.
- [ ] `V-5.34.002` Maintenance requirement stated per asset class.
- [ ] `V-5.34.003` Residual hazards stated and located.
- [ ] `V-5.34.004` Warranties recorded with conditions and void actions.
- [ ] `V-5.34.005` Certificates complete.
- [ ] `V-5.34.006` Machine-readable export delivered and valid.
- [ ] `V-5.34.007` Archive formats conforming.

---

## 5.35 Summary of Volume 5

1. The type registry is closed; every container declares a registered type.
2. Every type declares its users and the questions it answers; content serving no listed user is
   removed.
3. Schedules are generated, never maintained; every cell is populated; codes replace descriptions.
4. The specification carries requirements, drawings carry geometry, and the boundary is enforced.
5. Project records (RFI, instruction, minutes, decision log, site report) are documentation with
   the same identity, status and reference obligations as drawings.
6. As-built and O&M information carries provenance, because it is relied on longest and checked
   least.

---

*Continue to [Volume 6 — BIM Standards](ADOS-V6-BIM-Standards.md).*
