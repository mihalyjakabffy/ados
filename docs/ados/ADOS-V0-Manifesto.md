# Volume 0 — Manifesto

**ADOS 1.0 · Volume 0 · Normative except where marked *Informative*.**

---

## 0.1 Why documentation matters

### 0.1.1 The building is not built from the design

A building is not built from a design. It is built from a *description of a design*. The
description is the only part of the architect's work that leaves the office. Everything the
architect knows that is not in the description is, for practical purposes, not part of the
project.

This is the single fact from which the whole of ADOS follows. It has four consequences.

**Consequence 1 — The document is the product.** The model, the sketch, the conversation and
the intent are inputs. The issued document is the output, and it is the only output that
carries legal, financial and physical force.

**Consequence 2 — Loss is silent.** When information fails to transfer, nobody is notified.
The contractor does not receive an error message; they receive a drawing that appears
complete, make a reasonable assumption, and build it. The cost surfaces weeks later as
rework, a variation, or a defect that is discovered after handover.

**Consequence 3 — Ambiguity is resolved by the cheapest reading.** Where documentation
permits two interpretations, the interpretation that is cheaper or faster to build will be
selected, and will be defensible. Ambiguity is therefore not a neutral state; it is a
systematic bias against the design.

**Consequence 4 — The reader is not the author.** The reader is under time pressure, on a
noisy site, holding a folded and degraded copy, in poor light, possibly reading in a second
language, and looking for exactly one fact. Every rule in this specification is written for
that reader, not for the author at a colour-calibrated screen.

### 0.1.2 The measurable cost of documentation failure

Documentation defects propagate into the physical world with an amplification factor. The
cost of correcting an error rises by roughly an order of magnitude at each stage boundary:

| Stage at which an error is caught | Relative correction cost |
|---|---|
| Author's own review, before issue | 1 |
| Internal coordination review | 3–10 |
| Consultant / cross-discipline review | 10–30 |
| Tender query (pre-contract) | 30–100 |
| RFI during construction | 100–1 000 |
| Discovered during installation | 1 000–5 000 |
| Discovered after completion | 5 000+ |

*Informative.* The exact multipliers vary by project type and procurement route. The ratio
between the ends of the table does not: the same defect costs three to four orders of
magnitude more to correct on site than at the desk. This is the economic justification for
every check, gate and metric in Volume 8. A quality assurance activity that costs one hour
and prevents one site-discovered error has an extraordinary return; the only reason not to
perform it is that it is not systematised. ADOS systematises it.

### 0.1.3 Documentation as institutional memory

A project outlives the people who worked on it. A building outlives the practice that
designed it. Refurbishment, adaptation, fire investigation, dispute resolution and
decarbonisation retrofit all depend on documents read by people who cannot ask the author a
question, sometimes decades later.

This produces a design requirement that has nothing to do with the current project: **the
document shall be interpretable without its author.** Every convention that relies on
implicit shared knowledge — an unlabelled hatch, a private abbreviation, a colour whose
meaning lives in someone's head — is a time bomb with an unknown fuse length.

Rules `ADOS-2.8`, `ADOS-4.9.010` (legend completeness) and `ADOS-8.4` (information
completeness) exist for this reason alone.

---

## 0.2 Philosophy

### 0.2.1 First statement

> Architectural documentation is an information system whose purpose is to transfer decisions
> from the party that made them to the party that must act on them, with minimum cognitive
> cost and minimum probability of misinterpretation.

Each clause of this statement is load-bearing.

**"information system"** — not a drawing set, not a graphic artefact, not a portfolio. A
system: with a schema, a hierarchy, referential integrity, a lifecycle, and defined
consistency guarantees. Anything true of information systems is true here: normalisation
prevents contradiction; a single source of truth prevents drift; unvalidated input propagates
errors; the interface is not the data.

**"transfer decisions"** — the unit of content is a *decision*, not a line. A drawing that
shows a wall without answering *which wall type, why here, and to what tolerance* has drawn
geometry without transferring a decision. Volume 5 defines, per document type, the decision
set each document is responsible for carrying.

**"the party that must act on them"** — the audience is enumerable. Each document has a
defined primary user (Volume 5). Content that no defined user needs is noise, and noise is
not free: it consumes search time, print area and review attention.

**"minimum cognitive cost"** — the resource being economised is the reader's working memory
and search time, not the author's production time, and not sheet area.

**"minimum probability of misinterpretation"** — the objective is not beauty and not even
correctness alone. A correct document that is reliably misread has failed.

### 0.2.2 The document as an interface

A drawing sheet is a user interface. It has affordances, an information scent, a scan path, a
default state and failure modes. The disciplines of interface design apply directly:

- **Consistency beats novelty.** A reader who has learned one sheet should be able to read
  every other sheet with zero additional learning. Layout invariance across a set is worth
  more than local optimisation of any single sheet (`ADOS-3.3.010`).
- **Recognition beats recall.** Symbols shall be resolvable on the sheet where they are used,
  not from a legend in a different document (`ADOS-4.9.020`).
- **Progressive disclosure.** The sheet answers the general question; the callout answers the
  specific one. Detail placed at the wrong level of the hierarchy is invisible at the level
  that needs it and obstructive at the level that does not (`ADOS-2.3`).
- **Error prevention beats error messages.** A sheet cannot warn the reader. Prevention must
  therefore be structural: closed dimension chains, unique identifiers, mandatory
  cross-reference reciprocity (`ADOS-4.5.030`, `ADOS-2.4.040`).

### 0.2.3 The document as a database projection

In a BIM-based practice, the drawing is not authored; it is *derived*. The model is the
database, the view is the query, and the sheet is the report. This reframing has strict
consequences, which Volume 6 develops:

- A fact shall exist in exactly one place and be projected wherever needed. Duplicated facts
  drift (`ADOS-2.2.030`).
- Manual overrides of a derived value are data corruption with a delay fuse
  (`ADOS-6.7.050`).
- Graphic appearance shall be a function of data, applied by rule, not by selection
  (`ADOS-6.7.010`).
- If the appearance rule cannot be expressed as a query over the model, either the model
  lacks the data or the convention is arbitrary. Both are defects.

### 0.2.4 The document as legal instrument

Documentation is evidence. It is read adversarially in disputes, by people looking for the
reading most favourable to their client. This imposes requirements that no purely
communicative analysis would produce:

- **Status shall be unambiguous.** A reader shall never have to infer whether a document may
  be built from (`ADOS-2.6`).
- **Change shall be visible and attributable.** Revision clouding, revision registers and
  issue records exist so that *what changed, when, and on whose authority* is answerable
  years later (`ADOS-2.6.050`).
- **Superseded information shall be unavailable, not merely marked.** Marking relies on the
  reader looking; removal does not (`ADOS-2.6.070`).
- **Silence shall be distinguishable from omission.** "Not shown" and "not required" are
  different statements with different liabilities (`ADOS-4.8.060`).

### 0.2.5 Longevity over currency

A documentation standard that must be revised when fashion changes was never a standard. ADOS
selects, at every decision point, the option that will still be correct in fifty years:

- monochrome-first, because reproduction technology changes and greyscale is the floor;
- geometry-derived conventions, because human vision does not change;
- standard-derived numeric series, because they are stable and internationally shared;
- explicit legends, because shared tacit knowledge decays;
- open formats for archive, because proprietary formats become unreadable.

---

## 0.3 Core principles

The following nine principles are normative. Every rule in Volumes 1–8 shall be traceable to
at least one of them, and the rule registry records the mapping. A proposed rule that cannot
be traced to a principle shall be rejected (`ADOS-8.10.040`).

### ADOS-0.3.010 — Principle 1: Function precedes form ⚠

**Purpose.** Prevent the accumulation of graphic conventions that cost production effort and
reader attention without improving communication.

**Background.** Graphic decisions in documentation are not free. Every distinct line weight,
tone, typeface style or symbol the reader must discriminate consumes discrimination capacity
that is finite (see `ADOS-1.2`). Spending it on decoration reduces the capacity available for
meaning.

**Problem.** Practices accumulate house-style conventions — a distinctive title block, a
signature hatch, a preferred typeface — that are defended on identity grounds and never
audited for communicative value. Over time these consume both production time and reader
capacity.

**Decision.** Every graphic property of a document (weight, tone, colour, typeface, size,
spacing, position) shall encode information or serve a stated functional purpose. A graphic
property that encodes nothing shall be removed.

**Implementation.** Each graphic variable used in a document set shall appear in the
practice's *encoding table* (`ADOS-3.1.050`) with the column: variable, states, meaning of
each state, rule ID. A variable with fewer than two states encodes nothing and shall be
constant across the set.

**Exceptions.**
1. The practice identity block (`ADOS-3.9.070`), limited to the area defined there.
2. Sheet-edge fold and registration marks, which serve handling rather than communication.

**Validation.** `V-0.3.010`: for each graphic variable observed in the set, an entry exists in
the encoding table. Count of unmapped variables shall be 0.

**Examples.** *Conforming:* three line weights, each mapped to a depth tier. *Non-conforming:*
five line weights of which two are used interchangeably.

**Common mistakes.** Treating "it looks better" as a justification; introducing a second
typeface for headings when weight already establishes the hierarchy.

**Automation notes.** A generator emits only variables declared in the encoding table; the
renderer shall reject an undeclared style token at build time rather than substituting a
default.

---

### ADOS-0.3.020 — Principle 2: One fact, one place ⚠

**Purpose.** Eliminate the class of defect in which two documents state different values for
the same fact.

**Background.** Duplicated data diverges under revision. The probability that all copies are
updated together falls with the number of copies and with time pressure — precisely the
conditions under which revisions occur.

**Problem.** A door width appears on the plan, in the door schedule and in the specification.
Two are updated. The third is built.

**Decision.** Each fact shall have exactly one authoritative location. All other appearances
shall be references or derived projections of that location, never independent restatements.

**Implementation.** Volume 2 §2.2 assigns an authoritative carrier to each fact class:
geometry → model; component properties → schedules derived from the model; performance and
workmanship → specification; site conditions → survey. Drawings annotate by *reference*
(type code, mark), not by restated value.

**Exceptions.**
1. Safety-critical values may be duplicated where the duplicate is machine-generated from the
   authoritative source in the same publication run and is labelled with its source
   (`ADOS-2.2.040`).

**Validation.** `V-0.3.020`: for each fact class, exactly one authoritative carrier is
declared; automated cross-check of duplicated values reports 0 mismatches.

**Examples.** *Conforming:* plan annotates `D-12`; the schedule carries width, fire rating,
ironmongery set. *Non-conforming:* plan annotates `900 × 2100 FD30`, schedule says
`926 × 2040 FD60`.

**Common mistakes.** Typing a dimension as text because the derived value is inconvenient;
copying a note between sheets instead of referencing a shared note block.

**Automation notes.** The generator shall resolve all references at publication time and fail
the build on unresolved or conflicting references (`ADOS-7.6.030`).

---

### ADOS-0.3.030 — Principle 3: Encode meaning in the strongest available channel

**Purpose.** Ensure that the most important distinctions are carried by the visual channels
humans discriminate fastest and most reliably.

**Background.** Visual variables differ in discriminability, in whether they are perceived
pre-attentively, and in whether they survive reproduction. Position and line weight survive
photocopying, faxing, folding and poor light. Colour and fine tone do not.

**Problem.** Critical distinctions encoded in weak channels (a light tone difference, a hue)
disappear in the reproduction chain, and the reader is not warned that they have disappeared.

**Decision.** Distinctions shall be encoded in channels ranked by robustness. The ranking,
strongest first, is: **position → line weight → line type → tone → symbol → text → colour**.
Colour shall never be the sole carrier of any distinction.

**Implementation.** See `ADOS-3.1.030` (channel table) and `ADOS-4.1` (line hierarchy). The
primary structural distinction of any drawing — what is cut versus what is seen — is carried
by line weight, the second-strongest channel, because position is already committed to
geometry.

**Exceptions.** None.

**Validation.** `V-0.3.030`: convert the issued document to 8-bit greyscale and re-run the
full readability metric set (`ADOS-8.2`). All thresholds shall pass.

**Examples.** *Conforming:* fire compartment lines drawn as a distinct heavy dashed line type
*and* tinted red. *Non-conforming:* fire compartment lines distinguished only by red.

**Common mistakes.** Assuming issue-as-PDF means colour is preserved; site prints are
monochrome, and photocopies of site prints are worse.

**Automation notes.** The renderer shall support a `--greyscale` build target and the QA gate
shall run against it.

---

### ADOS-0.3.040 — Principle 4: Hierarchy shall be explicit and shallow

**Purpose.** Keep the reader's orientation cost bounded.

**Background.** Search cost in a hierarchical structure grows with depth; the number of items
a reader can hold while descending is small (`ADOS-1.2.020`). Empirically, orientation fails
when a reader must hold more than about four levels of containment.

**Problem.** Deep, implicit hierarchies produce readers who can find nothing and authors who
file things where nobody looks.

**Decision.** Every document set shall present a hierarchy of at most four navigational
levels, and each level shall be explicitly labelled on the artefact itself.

**Implementation.** Levels: **Set → Volume/Package → Sheet → Region**. Within a sheet, at most
three levels of visual hierarchy shall be used (`ADOS-3.6.020`).

**Exceptions.**
1. Specification documents may use five levels where mandated by a national specification
   framework (class **I**).

**Validation.** `V-0.3.040`: maximum containment depth ≤ 4; every artefact carries a label
identifying its position at each level.

**Common mistakes.** Sub-sub-packages created for administrative convenience; sheets whose
only locator is a file name.

**Automation notes.** Depth is computable from the sheet register; the generator shall reject
a register whose depth exceeds the limit.

---

### ADOS-0.3.050 — Principle 5: Consistency outranks local optimisation ⚠

**Purpose.** Make learning transferable across the whole set.

**Background.** A reader builds a mental template of "how a sheet works" from the first few
sheets and applies it to the rest. A sheet that deviates costs far more than the local gain,
because it silently invalidates the template and the reader does not know which template to
apply.

**Problem.** A technician moves a title block, changes a north orientation, or uses a
different scale for one plan "because it fits better". The reader's calibration breaks and
subsequent misreadings are attributed to carelessness rather than to the layout.

**Decision.** Layout structure, orientation, symbol meaning, scale selection and annotation
conventions shall be invariant across a document set. A deviation shall be justified in the
Deviation Register and flagged on the sheet.

**Implementation.** Fixed sheet zoning (`ADOS-3.3`), fixed plan orientation across all levels
(`ADOS-5.4.030`), one scale per drawing class per project (`ADOS-4.2.040`).

**Exceptions.**
1. A drawing whose subject cannot fit at the set scale may use the next scale in the ladder,
   provided the scale is stated adjacent to the view title at ≥ 1.4× the surrounding text
   size and the deviation is registered.

**Validation.** `V-0.3.050`: title block origin identical on all sheets (±0 mm); north vector
identical on all plan views (±0°); scale set per drawing class has cardinality 1 unless
registered.

**Common mistakes.** Rotating a plan to fit the sheet; a "special" sheet inherited from
another project.

**Automation notes.** Layout is applied from a single template object; per-sheet overrides
require an explicit, logged exception token.

---

### ADOS-0.3.060 — Principle 6: The reader's context is adverse

**Purpose.** Set the design target at the real conditions of use rather than the author's
conditions of production.

**Background.** Documents are consumed folded, reduced, photocopied, in low light, in weather,
on a phone screen, at speed, and by non-native readers. The author's environment — a large
calibrated display, unlimited zoom, full context in working memory — is unrepresentative.

**Problem.** Choices validated at 200 % zoom (fine hatch, 1.5 mm text, subtle tones) fail
under real conditions and the failure is invisible to the author.

**Decision.** Every document shall be designed and verified against the **adverse reference
condition**: printed at the smallest nominated issue size, reproduced twice on a monochrome
office device, viewed at 500 mm in 200 lux illumination.

**Implementation.** Minimum text height, minimum line width, minimum tone separation and
minimum symbol size in Volume 3 and Volume 4 are all derived from this condition, not from
screen viewing.

**Exceptions.**
1. Documents formally issued as *screen-only* (e.g. a coordination viewpoint export) may use
   the digital reference condition (`ADOS-8.2.050`), and shall be watermarked `SCREEN ONLY —
   NOT FOR PRINT`.

**Validation.** `V-0.3.060`: the QA gate renders at the adverse reference condition and
applies the readability metrics of `ADOS-8.2`.

**Common mistakes.** Approving a drawing only on screen; specifying a hatch whose spacing is
below the reproduction threshold at issue scale.

**Automation notes.** The QA pipeline shall include a degradation simulation stage
(`ADOS-8.2.040`): downsample, threshold, add noise, then measure.

---

### ADOS-0.3.070 — Principle 7: Every rule shall be checkable ⚠

**Purpose.** Make the standard enforceable rather than aspirational.

**Background.** A rule that cannot be checked is not enforced, and an unenforced rule degrades
the credibility of the rules that are enforced.

**Problem.** Standards documents full of "drawings should be clear and well organised" produce
no measurable change in output and provide no defence in a dispute.

**Decision.** Every `shall` rule in this specification shall carry a deterministic validation
procedure with an objective pass/fail criterion. A rule without one shall be published as a
recommendation.

**Implementation.** Validation IDs `V-x.y.zzz` map to executable checks in
`machine/ados-validation.yaml`. Volume 8 defines the metric definitions and thresholds.

**Exceptions.** None.

**Validation.** `V-0.3.070`: for every rule with level `shall` in the registry, field
`validation.check_id` is non-empty and resolves to a defined check.

**Common mistakes.** Writing a validation that restates the rule ("the drawing shall be
checked for clarity") instead of defining a measurement.

**Automation notes.** This rule is self-applying: the registry is machine-validated in CI.

---

### ADOS-0.3.080 — Principle 8: Automation-readiness is a design constraint, not a later port

**Purpose.** Ensure the standard produces documentation that can be generated and verified by
machine without reinterpretation.

**Background.** Conventions that depend on human judgement ("place the note where it reads
best") cannot be automated, cannot be validated, and cannot be taught quickly. Conventions
expressed as constraints and priorities can be solved.

**Problem.** Practices adopt a written standard and then discover that no part of it can be
enforced in the authoring tool, so the standard exists only in a PDF nobody opens.

**Decision.** Every convention shall be expressible as a constraint, a priority ordering, or a
deterministic function over declared inputs. Judgement-dependent phrasing shall not appear in
normative text.

**Implementation.** Volume 7 defines the intermediate representation, the constraint set, the
solver contract and tie-break ordering. Where a placement decision is genuinely
under-determined, the tie-break rule shall be stated so that two conforming implementations
produce identical output.

**Exceptions.** None.

**Validation.** `V-0.3.080`: normative text contains no occurrence of the banned subjective
lexicon (`ADOS-7.2.020`); every placement rule declares a tie-break.

**Common mistakes.** "Balanced", "appropriate", "as required", "where necessary", "sensible" —
each of these words in a normative sentence is a defect.

**Automation notes.** A lexicon linter runs over the specification source in CI.

---

### ADOS-0.3.090 — Principle 9: Absence shall be explicit

**Purpose.** Distinguish "this is not here" from "this was not documented".

**Background.** A reader cannot distinguish a deliberate void from an omission. Both look the
same: nothing. Yet their consequences differ completely — one is information, the other is
risk.

**Problem.** A ceiling plan with no services shown may mean *no services* or *services by
others* or *not yet coordinated*. The contractor prices one reading and builds another.

**Decision.** Where a document deliberately excludes information that a reader could
reasonably expect, the exclusion shall be stated explicitly, with the reason and the
responsible party or the document that carries it.

**Implementation.** Standard exclusion statements, scope-of-drawing notes and the
`NOT SHOWN — SEE <ref>` convention (`ADOS-4.8.060`). Every sheet carries a *scope* statement
in the notes region (`ADOS-3.3.070`).

**Exceptions.** None.

**Validation.** `V-0.3.090`: every sheet carries a non-empty scope statement; every drawing
region excluded from a discipline's scope carries an explicit exclusion note or hatch with a
legend entry.

**Common mistakes.** Empty ceiling grids; blank areas at scope boundaries; "by others" without
naming the others.

**Automation notes.** The generator shall emit an exclusion note for every model region whose
discipline ownership differs from the sheet's discipline.

---

## 0.4 Design ethics

### 0.4.1 The asymmetry of expertise

The author knows more than the reader about the design and less than the reader about the
conditions in which the document will be used. Both halves of this asymmetry create
obligations.

**ADOS-0.4.010 — Duty of comprehensibility.** The author shall not rely on knowledge the
reader has no defined means of acquiring. Any convention not defined in this specification,
in the project's stated standards, or on the document itself, shall not be used.

**ADOS-0.4.020 — Duty of disclosure of uncertainty.** Where a dimension, condition or
interface is not yet determined, the document shall say so and state the resolution
mechanism. Documenting a provisional value as though it were fixed transfers risk silently to
a party who cannot see it. Provisional values shall be marked with the provisional token
defined in `ADOS-4.5.080`.

**ADOS-0.4.030 — Duty against defensive obscurity.** Documentation shall not be made
deliberately imprecise in order to preserve later freedom or shift liability. Where scope is
genuinely undefined, `ADOS-0.3.090` requires it to be stated as undefined. Vagueness used as a
risk-transfer device is a professional failure, not a technique.

### 0.4.2 Honesty of representation

**ADOS-0.4.040 — Visualisations shall not overstate certainty.** Any produced image
(rendering, visualisation, or AI-generated illustration) issued alongside technical
documentation shall be labelled with its status and shall not depict as resolved what is not
resolved. Where an image is machine-generated, it shall be labelled as such
(`ADOS-4.11.060`).

**ADOS-0.4.050 — Derived and measured values shall be distinguishable.** A value obtained by
survey, calculation, assumption or estimate shall carry its provenance where the distinction
affects reliance. Volume 4 defines provenance tokens for dimensions (`ADOS-4.5.090`).

**ADOS-0.4.060 — Existing conditions shall not be idealised.** Where the model represents
existing fabric by assumption rather than by survey, drawings derived from it shall state the
assumption and its confidence. This is the most frequently violated ethical rule in
refurbishment work and the most expensive.

### 0.4.3 Accessibility as an ethical requirement

**ADOS-0.4.070 — No information shall be available only to readers with unimpaired colour
vision.** Approximately 8 % of male readers and 0.5 % of female readers have a colour vision
deficiency. `ADOS-0.3.030` already prohibits colour-only encoding on robustness grounds; this
clause restates it as an ethical obligation so that it cannot be traded away when robustness
is not at issue (for example in screen-only deliverables).

**ADOS-0.4.080 — Digital deliverables shall be machine-readable.** Issued PDFs shall carry
searchable text, logical structure and document metadata (`ADOS-6.11`). A scanned image of a
drawing is not a conforming digital deliverable. This serves screen-reader users, search,
automated checking and long-term retrieval simultaneously.

### 0.4.4 Ethics of automation

**ADOS-0.4.090 — Accountability shall not be diffused by automation.** A machine-generated
document is issued under the same professional responsibility as a hand-produced one. The
generator's identity and version shall be recorded in the document metadata
(`ADOS-7.9.020`), and a named person shall be recorded as the approver. "The system produced
it" is not a defence and shall not be made available as one.

**ADOS-0.4.100 — Automated output shall be verifiable, not merely plausible.** Generated
documentation shall be validated against Volume 8 metrics before issue. Plausibility is not
correctness; a generator that produces confident, well-composed, wrong drawings is more
dangerous than one that fails loudly.

**ADOS-0.4.110 — The training and derivation of generated content shall be traceable.** Where
content is derived from precedent projects, standard details or model libraries, the source
shall be recorded so that an error in a source can be traced to every document that inherited
it. Volume 7 §9 defines the provenance record.

---

## 0.5 Communication principles

### 0.5.1 The five questions

Every technical document answers some subset of five questions. Volume 5 assigns the subset to
each document type; a document that answers a question outside its assignment is duplicating
another document and violates `ADOS-0.3.020`.

| Question | Carrier |
|---|---|
| **Where is it?** | Location drawings: site plan, floor plan, RCP, elevations, sections |
| **What is it?** | Schedules, specifications, type sheets |
| **How big is it?** | Dimensions, setting-out drawings, grids |
| **How is it made?** | Assembly and details |
| **Why / under what condition?** | Notes, strategy drawings, specification clauses |

**ADOS-0.5.010 — Question assignment.** Each document type shall declare which of the five
questions it answers, and shall not carry content answering unassigned questions except as a
reference.

### 0.5.2 The three reading modes

Documents are read in three distinct modes. A conforming sheet supports all three.

1. **Orientation** (2–10 s). *Where am I in the set? What is this?* Supported by: sheet
   identity, title, key plan, north point, scale — all in fixed positions.
2. **Search** (10–60 s). *Where is the thing I need?* Supported by: consistent zoning, grid
   references, legible titles, a reliable index, and reference reciprocity.
3. **Extraction** (1–10 min). *What exactly does it say?* Supported by: dimensional
   completeness, annotation precision, and unambiguous references onward.

**ADOS-0.5.020 — Mode support.** Every sheet shall support orientation within 5 s from a cold
start, verified by the orientation test in `ADOS-8.6.020`: a reader unfamiliar with the sheet
shall determine document type, location and scale within 5 s using only fixed-position
elements.

### 0.5.3 Signal, noise and redundancy

**Signal** is content the defined user needs. **Noise** is content that no defined user needs.
**Redundancy** is signal repeated in another channel to protect against loss.

Redundancy is not noise, and the distinction matters: a level marker repeated on section and
plan is redundancy (it protects against a misread); a decorative entourage figure is noise.

**ADOS-0.5.030 — Purposeful redundancy.** Redundancy shall be used only where (a) the
information is safety- or setting-out-critical, and (b) the redundant instance is derived from
the same authoritative source (`ADOS-0.3.020` Exception 1). Uncontrolled redundancy — copies
maintained by hand — is prohibited.

**ADOS-0.5.040 — Noise budget.** The proportion of marked area on a sheet serving no defined
user shall be 0 %. This is checkable through the encoding table (`ADOS-0.3.010`) and the
content schedule per document type (Volume 5).

### 0.5.4 Language

**ADOS-0.5.050 — Sentence form in notes.** Notes shall be written as imperative or declarative
statements in the active voice, one requirement per note, ≤ 25 words per sentence. Passive
constructions that omit the responsible party ("shall be coordinated") are prohibited where
the party matters.

**ADOS-0.5.060 — Controlled vocabulary.** Each project shall use a single controlled term for
each concept, defined in the project glossary. Synonym drift (*soffit / underside / ceiling
face*) creates ambiguity for readers and defeats text search.

**ADOS-0.5.070 — Abbreviations.** Abbreviations shall be drawn from the practice abbreviation
register (`ADOS-A.3`) and every abbreviation used in a set shall appear in that set's
abbreviation list. Ad-hoc abbreviation is prohibited.

**ADOS-0.5.080 — Numbers and units.** Every numeric value shall carry an unambiguous unit
context. The project shall declare a single default length unit for drawings
(`ADOS-4.5.010`), stated in the title block; values in other units shall carry an explicit
unit symbol.

**ADOS-0.5.090 — Second-language readability.** Notes shall avoid idiom, nested subordinate
clauses and negation of negation. Site documentation is routinely read by people working in a
second language; complexity in the note text converts directly into construction error.

---

## 0.6 Timelessness

### 0.6.1 What makes a convention durable

A convention is durable when it depends only on facts that do not change. ADOS ranks its own
dependencies:

| Dependency | Half-life | Use |
|---|---|---|
| Human visual acuity, working-memory capacity | Unbounded | Preferred basis |
| Geometry and arithmetic | Unbounded | Preferred basis |
| Physics of reproduction (ink spread, contrast) | Decades | Acceptable, with margin |
| International standards (ISO series) | Decades | Acceptable, cite explicitly |
| Construction procurement practice | 10–20 years | Isolate into overlays |
| Authoring tool capability | 3–7 years | Never a basis; only an implementation note |
| Fashion in graphic design | 3–5 years | Never a basis |

**ADOS-0.6.010 — Dependency discipline.** A normative rule shall not depend on a fact whose
half-life is shorter than the intended life of the documentation. Tool-specific instruction
shall appear only in `Implementation` and `Automation notes` fields, never in `Decision`.

### 0.6.2 Separation of stable core and volatile overlay

**ADOS-0.6.020 — Layered specification.** The specification is organised in three layers:

1. **Core** (Volumes 0–5, 7, 8): jurisdiction- and tool-independent.
2. **Jurisdiction overlay** (`ADOS-2.7`): statutory content requirements, national symbol
   conventions, language.
3. **Tool overlay** (Volume 6): Archicad, Revit, IFC, publishing configuration.

Changing a tool shall require changes only in layer 3. Changing jurisdiction shall require
changes only in layer 2. If a tool change forces a core change, the core rule was wrongly
specified.

### 0.6.3 Archival requirements

**ADOS-0.6.030 — Archive format.** The archival record of any issued document set shall be
held in formats that are (a) open and fully published, (b) self-contained, and (c) renderable
without the authoring application. The conforming set is: PDF/A-2b or PDF/A-3b for documents,
IFC (ISO 16739) for models, plain UTF-8 text or CSV for tabular data, and PNG or TIFF for
raster images.

**ADOS-0.6.040 — Archive self-description.** Every archive shall include a manifest listing
every file, its role, its checksum (SHA-256), its issue status and its parent revision. An
archive that requires institutional knowledge to interpret is not an archive.

**ADOS-0.6.050 — Retention.** Retention periods shall be set to the longer of the statutory
limitation period of the jurisdiction plus five years, or the expected service life of the
building fabric documented. Retention decisions shall be recorded per set, not per file.

---

## 0.7 Definition of quality

### 0.7.1 Quality is not subjective here

**ADOS-0.7.010 — Quality definition ⚠.** For the purposes of this specification, the quality
of a document is defined as:

> The probability that a defined user, under the adverse reference condition, extracts the
> correct answer to a question the document is responsible for answering, within the time
> budget for that question.

Three terms make this operational:

- **defined user** — enumerated per document type in Volume 5;
- **question the document is responsible for** — the assigned subset of `ADOS-0.5.010`;
- **time budget** — orientation ≤ 5 s, search ≤ 60 s, extraction ≤ 10 min (`ADOS-0.5.020`).

Quality is therefore measurable by proxy metrics that predict this probability. Volume 8
defines nine such metrics with thresholds.

### 0.7.2 The nine quality dimensions

| # | Dimension | Question it answers | Volume 8 reference |
|---|---|---|---|
| 1 | Readability | Can the marks be resolved at all? | `ADOS-8.2` |
| 2 | Consistency | Does the reader's learned template hold? | `ADOS-8.3` |
| 3 | Hierarchy | Is importance visible before content is read? | `ADOS-8.3.040` |
| 4 | Information completeness | Are all assigned questions answered? | `ADOS-8.4` |
| 5 | Visual balance | Is attention distributed as intended? | `ADOS-8.5` |
| 6 | Navigation | Can the reader move between documents without loss? | `ADOS-8.6` |
| 7 | Print quality | Does it survive the reproduction chain? | `ADOS-8.7` |
| 8 | Accessibility | Is it usable by all defined users and by machines? | `ADOS-8.8` |
| 9 | Automation readiness | Can it be generated and validated deterministically? | `ADOS-8.9` |

### 0.7.3 Quality is a property of the set, not the sheet

**ADOS-0.7.020 — Set-level assessment.** Conformance shall be assessed at the level of the
issued set. A sheet that is individually excellent but inconsistent with the set reduces the
quality of the set (`ADOS-0.3.050`). Metrics in Volume 8 are therefore defined at both sheet
and set level, and the set-level threshold governs.

### 0.7.4 What quality is not

*Informative.* The following are frequently mistaken for documentation quality and are
explicitly outside the definition:

- **Density of information.** More lines is not more quality; `ADOS-3.7` sets density limits.
- **Visual sophistication.** A refined-looking sheet that fails the orientation test has
  failed.
- **Completeness of the model.** Model richness that does not reach a reader is invisible.
- **Volume of output.** Sheet count is a cost, not an achievement. `ADOS-2.3.060` requires
  content to be placed at the lowest sufficient level of the hierarchy.
- **Effort expended.** Production time is an input. Reader outcome is the output.

### 0.7.5 The quality gate

**ADOS-0.7.030 — Gate ⚠.** No document shall be issued at status `S3` (shared for
coordination) or above until it has passed the applicable Volume 8 metric set for its status.
The gate is binary; there is no partial issue. Failures shall be either corrected or recorded
in the Deviation Register with an approver.

---

## 0.8 Adoption

*Informative.*

A practice adopting ADOS in full on day one will fail. The following sequence produces
measurable improvement at each step and is the recommended path.

| Phase | Duration | Action | Measured by |
|---|---|---|---|
| 1 | Week 1–2 | Adopt sheet identity, title block, status/revision (`ADOS-2.6`, `ADOS-3.9`) | Navigation metric `M6` |
| 2 | Week 3–6 | Adopt line hierarchy and pen sets (`ADOS-4.1`, `ADOS-6.7`) | Readability metric `M1` |
| 3 | Month 2–3 | Adopt typography and sheet grid (`ADOS-3.3`, `ADOS-3.4`) | Consistency metric `M2` |
| 4 | Month 3–5 | Adopt document type definitions and checklists (Volume 5) | Completeness metric `M4` |
| 5 | Month 5–8 | Adopt BIM templates and publishing (Volume 6) | Automation readiness `M9` |
| 6 | Month 8–12 | Adopt automated validation (Volume 8), then generation (Volume 7) | Defect escape rate |

The ordering is not arbitrary: each phase makes the next cheaper. Identity and status enable
audit; pen sets and typography make templates worth building; templates make document type
enforcement possible; enforcement makes validation meaningful; validation makes generation
safe.

---

## 0.9 Summary of Volume 0

1. The document is the product; everything not in it does not exist.
2. Documentation is an information system, not graphic design.
3. Nine principles govern every rule: function precedes form; one fact one place; strongest
   channel; shallow explicit hierarchy; consistency over local optimisation; adverse reader
   context; checkability; automation-readiness; explicit absence.
4. Ethics: comprehensibility, disclosure of uncertainty, honesty of representation,
   accessibility, accountability under automation.
5. Quality is the probability of correct extraction by a defined user under adverse
   conditions within a time budget — and it is measured, not judged.

---

*Continue to [Volume 1 — Design Philosophy](ADOS-V1-Design-Philosophy.md).*
