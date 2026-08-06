# Architectural Documentation Operating System (ADOS)

**Edition 1.0 · Normative Specification · Publication status: Released**

---

## Front Matter

### 0.1 Title

Architectural Documentation Operating System — Specification for the production,
structure, representation, verification and automated generation of architectural
project documentation.

Short designation: **ADOS 1.0**

### 0.2 Scope

This specification defines the complete rule set governing every document produced by an
architectural practice across the whole project lifecycle, from first strategic definition
to post-occupancy handover.

It specifies:

- the information architecture of a documentation set;
- the visual and drawing language used to encode information;
- the mandatory content, structure and layout logic of each document type;
- the BIM authoring configuration required to produce conforming output deterministically;
- a machine-executable rule format enabling automated generation and validation;
- objective, measurable quality criteria with pass/fail thresholds.

This specification does **not** define:

- design methodology or architectural style;
- contractual allocation of responsibility between parties;
- national statutory content requirements (these are referenced as *jurisdiction overlays*,
  see `ADOS-2.7`);
- the internal file format of any authoring tool.

### 0.3 Field of application

ADOS applies to any organisation producing architectural documentation, at any scale, in any
jurisdiction, using any authoring tool, whether documents are produced by human operators,
by automated pipelines, or by both.

### 0.4 Normative principle

> **Architectural documentation is not graphic design. Architectural documentation is an
> information system.**

Every page exists to transfer a decision from the party that made it to the party that must
act on it, at the lowest achievable cognitive cost, with the lowest achievable probability of
misinterpretation.

Consequently: **no rule in this specification exists for aesthetic reasons.** Every rule
carries a functional justification, stated in its `Purpose` and `Background` fields. A rule
whose justification cannot be stated in terms of communication performance is not a rule and
shall be removed at the next revision.

---

## 1 Structure of the specification

| Volume | Title | File | Subject |
|---|---|---|---|
| 0 | Manifesto | [`ADOS-V0-Manifesto.md`](ADOS-V0-Manifesto.md) | Purpose, ethics, quality definition |
| 1 | Design Philosophy | [`ADOS-V1-Design-Philosophy.md`](ADOS-V1-Design-Philosophy.md) | Derivation of all downstream decisions |
| 2 | Information Architecture | [`ADOS-V2-Information-Architecture.md`](ADOS-V2-Information-Architecture.md) | Hierarchy, sequence, navigation, lifecycle |
| 3 | Visual Language | [`ADOS-V3-Visual-Language.md`](ADOS-V3-Visual-Language.md) | Typography, grid, scale, contrast, composition |
| 4 | Drawing Language | [`ADOS-V4-Drawing-Language.md`](ADOS-V4-Drawing-Language.md) | Line hierarchy, annotation, symbols, hatch |
| 5A | Document Types — Drawings | [`ADOS-V5-Document-Types.md`](ADOS-V5-Document-Types.md) | Chapters 5.0–5.18: every drawing type, with checklists |
| 5B | Document Types — Documents | [`ADOS-V5B-Document-Types.md`](ADOS-V5B-Document-Types.md) | Chapters 5.19–5.34: schedules, specification, packages, records |
| 6 | BIM Standards | [`ADOS-V6-BIM-Standards.md`](ADOS-V6-BIM-Standards.md) | Archicad, Revit, IFC, naming, publishing |
| 7 | AI Generation Specification | [`ADOS-V7-AI-Generation.md`](ADOS-V7-AI-Generation.md) | Deterministic machine-executable rules |
| 8 | Quality Assurance | [`ADOS-V8-Quality-Assurance.md`](ADOS-V8-Quality-Assurance.md) | Metrics, thresholds, audit procedure |
| A | Appendix | [`ADOS-APX-Appendix.md`](ADOS-APX-Appendix.md) | Glossary, decision trees, checklists, anti-patterns |

Machine-readable artefacts (normative, see `ADOS-7.1`):

| Artefact | File | Content |
|---|---|---|
| Design tokens | [`machine/ados-tokens.json`](machine/ados-tokens.json) | All numeric constants |
| Rule registry | [`machine/ados-rules.yaml`](machine/ados-rules.yaml) | Every rule ID, level, validator |
| Sheet schema | [`machine/ados-sheet-schema.json`](machine/ados-sheet-schema.json) | JSON Schema for a sheet definition |
| Naming grammar | [`machine/ados-naming.ebnf`](machine/ados-naming.ebnf) | EBNF for identifiers |
| Validation profile | [`machine/ados-validation.yaml`](machine/ados-validation.yaml) | QA metrics and thresholds |

---

## 2 Rule identification

### 2.1 Rule ID grammar

```
RULE-ID  ::= "ADOS-" VOLUME "." CHAPTER "." ORDINAL
VOLUME   ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "A"
CHAPTER  ::= 1*2DIGIT
ORDINAL  ::= 3DIGIT
```

Example: `ADOS-3.4.020` — Volume 3, Chapter 4, rule 020.

### 2.2 Ordinal allocation

Ordinals are allocated in increments of 10 (`010`, `020`, `030`…). Intermediate values
(`015`) are reserved for rules inserted at a later revision, so that **a rule ID is never
reused and never renumbered**. A withdrawn rule keeps its ID and is marked
`Status: Withdrawn (superseded by <ID>)`.

### 2.3 Rule ID stability contract

A rule ID is a permanent public identifier. Downstream systems — BIM template metadata, QA
reports, drawing-issue records, AI generation logs — cite rule IDs. Renumbering breaks audit
trails retroactively. Therefore:

- **ADOS-A.1.010** — Rule IDs are immutable across all revisions of this specification.

### 2.4 Requirement levels

This specification uses ISO drafting conventions:

| Verb | Meaning | Conformance effect |
|---|---|---|
| **shall** / **shall not** | Requirement | Non-compliance = non-conforming document |
| **should** / **should not** | Recommendation | Non-compliance requires a recorded justification |
| **may** | Permission | No conformance effect |
| **can** / **cannot** | Statement of possibility | Informative only |

The words *must*, *ought*, *it is recommended that*, *best practice*, *ideally* and
*preferably* are not used in normative text.

### 2.5 Rule block format

Every normative rule is expressed in the following twelve-field block. Fields marked *(o)*
may be omitted when not applicable; all others are mandatory.

```
### ADOS-x.y.zzz — <Name>

**Purpose.**         What communication failure this rule prevents.
**Background.**      The physical, perceptual, procedural or legal fact the rule rests on.
**Problem.**         The concrete failure mode observed when the rule is absent.
**Decision.**        The normative statement. Contains "shall" / "shall not".
**Implementation.**  How to satisfy it, with numeric values and tool-level instruction.
**Exceptions.**      Enumerated, closed set. "None." if none.
**Validation.**      The check that proves compliance. Deterministic and automatable.
**Examples.**        Conforming and non-conforming instances.
**Common mistakes.** Observed failure patterns.
**Automation notes.**How a generator satisfies it and what it must emit.
```

A rule whose `Validation` field cannot be expressed as a deterministic procedure is
classified as a **recommendation**, never a requirement (see `ADOS-8.1.010`).

---

## 3 Conformance

### 3.1 Conformance classes

| Class | Name | Applies to | Requirement |
|---|---|---|---|
| **A** | Automated | Documentation generated or validated by machine | All `shall` rules in Volumes 0–8 + all Volume 7 determinism rules |
| **B** | Studio | Practice-wide manual production | All `shall` rules in Volumes 0–6 and 8 |
| **C** | Minimal | Single-project or legacy adoption | All `shall` rules marked **[C]** in the rule registry |

A document set claiming conformance shall state the class and edition, e.g.:

```
Documentation conforms to ADOS 1.0 Class B.
```

### 3.2 Conformance claim placement

The conformance claim appears in the *Standards and Conventions* block of the Cover Sheet
(`ADOS-5.1`) and in the metadata of every issued PDF (`ADOS-6.11.030`).

### 3.3 Deviation register

Any deviation from a `shall` rule shall be recorded in a **Deviation Register** carried with
the document set, with the fields: rule ID, deviating documents, reason, approver, date, and
expiry or remediation milestone. An undocumented deviation is a defect (`ADOS-8.9.010`).

### 3.4 Precedence

Where sources conflict, the following precedence applies, highest first:

1. Statutory requirement of the project jurisdiction.
2. Contract or client documentation standard, where explicitly incorporated.
3. This specification (ADOS 1.0).
4. Practice-level overlay (`ADOS-2.7.030`).
5. Authoring-tool default behaviour.

Rule `ADOS-2.7.010` requires every deviation arising from precedence levels 1–2 to be
recorded in the Deviation Register.

### 3.5 Versioning of this specification

ADOS uses semantic versioning: `MAJOR.MINOR`.

- **MINOR** increment: rules added, recommendations tightened, editorial correction. Existing
  conforming documents remain conforming.
- **MAJOR** increment: a `shall` rule changed or withdrawn in a way that invalidates existing
  conforming documents. A migration table is mandatory (`ADOS-A.9`).

Documents cite the edition they were produced under. A document is judged against the edition
cited on it, not against the current edition.

---

## 4 Reading paths

This specification is long by necessity. It is not intended to be read linearly by all users.

| Role | Read | Reference |
|---|---|---|
| Practice principal / QA lead | V0, V1, V8 §1–3, §3 of this file | V2 |
| Project architect | V0 §4, V2, V5 (relevant types), V8 checklists | V3, V4 |
| Technician / production | V3, V4, V5, V6 | V8 |
| BIM manager | V6 in full, V2 §4–6, V7 §2 | V3, V4 |
| Software / AI engineer | V7 in full, `machine/*`, V8 | V2, V3, V4 |
| New employee, week 1 | V0, V1 §1–4, V4 §1–3, the Appendix checklists | — |

---

## 5 Relationship to existing standards

ADOS is written to be compatible with, and where possible derived from, the following. Where
ADOS is stricter, it states so and gives the reason.

| Reference | Subject | ADOS relationship |
|---|---|---|
| ISO 216 | Paper sizes (A series) | Adopted as the sheet size basis (`ADOS-3.2`) |
| ISO 5457 | Technical drawing sheet layout, frames, zones | Adopted with additions (`ADOS-3.3`) |
| ISO 7200 | Title block data fields | Adopted as the minimum field set (`ADOS-3.9`) |
| ISO 128 (series) | General principles of presentation, lines, views, sections | Adopted; ADOS narrows the permitted line-type set (`ADOS-4.1`) |
| ISO 3098 (series) | Lettering | Adopted as the height series basis (`ADOS-3.4`) |
| ISO 129-1 | Dimensioning | Adopted with a stricter chain-closure requirement (`ADOS-4.5`) |
| ISO 5455 | Scales | Adopted as the scale ladder basis (`ADOS-4.2`) |
| ISO 6284 | Indication of limit deviations | Referenced (`ADOS-4.5.070`) |
| ISO 4157 (series) | Designation systems for buildings and parts | Basis for level/room designation (`ADOS-2.5`) |
| ISO 9431 | Spaces for drawing, text and title block | Basis for sheet zoning (`ADOS-3.3`) |
| ISO 19650 (series) | Information management using BIM | Adopted for status/revision and container naming (`ADOS-2.6`, `ADOS-6.4`) |
| ISO 16739 (IFC) | Data model for exchange | Adopted as the exchange target (`ADOS-6.8`) |
| ISO 12006-2 / bSDD | Classification framework | Adopted for classification fields (`ADOS-6.6`) |
| ISO 32000 / PDF/A-2b, PDF/A-3b | Portable document archival | Adopted as the issue format (`ADOS-6.11`) |
| ISO 15489 | Records management | Basis for retention and archive rules (`ADOS-2.9`) |
| ISO 9241-3xx | Ergonomics of human–system interaction | Basis for legibility thresholds (`ADOS-3.1`) |
| WCAG 2.2 | Web content accessibility | Adopted for digital deliverables (`ADOS-8.8`) |
| ISO 2848 / ISO 1006 | Modular coordination, basic module M = 100 mm | Basis for the sheet grid module (`ADOS-3.3.020`) |

Where a national standard (for example a BS, DIN, NF, ANSI/NCS, or NBS convention) conflicts
with ADOS, precedence clause `ADOS-0.3.4` applies.

---

## 6 Document conventions used in this specification

- Dimensions are in millimetres (mm) unless stated. Where imperial output is required, see
  `ADOS-3.2.060`.
- Lengths on a *sheet* are stated as printed sizes at 1:1 on the nominated sheet size.
- Lengths in a *model* are stated as real-world sizes.
- `[C]` after a rule name marks a Class C (minimal) requirement.
- `⚠` marks a rule whose violation is classified **Severity 1** in `ADOS-8.9`.
- Token references appear as `{ados.type.body.height}` and resolve against
  `machine/ados-tokens.json`.
- Cross-references are given as bare rule IDs and are resolvable by the link checker
  (`ADOS-8.7.030`).

---

## 7 Maintenance

### 7.1 Custodian

The specification is maintained by a single named custodian role within the adopting
practice: the **Documentation Standard Owner (DSO)**. Responsibilities are defined in
`ADOS-8.10`.

### 7.2 Change procedure

1. Change request raised with: observed failure, proposed rule text, affected rule IDs.
2. Impact analysis against the rule registry (`machine/ados-rules.yaml` dependency graph).
3. Validation: the proposed rule shall have a deterministic check or be demoted to a
   recommendation.
4. Publication with a revision entry and, if MAJOR, a migration table.

### 7.3 Revision history

| Edition | Date | Change |
|---|---|---|
| 1.0 | 2026 | First publication. |

---

## 8 Notes on the derivation method

Every quantitative value in this specification is derived from one of six classes of
evidence, and each rule states which:

| Class | Symbol | Basis |
|---|---|---|
| Physical | **P** | Optics, reproduction physics, material behaviour |
| Perceptual | **V** | Human visual acuity, contrast sensitivity, discrimination thresholds |
| Cognitive | **C** | Working memory, search behaviour, error rates |
| Procedural | **R** | How the document is actually used on site or in review |
| Interoperability | **I** | Requirement of an external system or standard |
| Arithmetic | **A** | Consequence of another value, by derivation |

A value with no evidence class is a defect in this specification, not a rule.

Values inherited unchanged from an external standard carry class **I** and cite the source.
Values derived from a stated threshold carry class **A** and cite the derivation.

---

*End of front matter. Continue to [Volume 0 — Manifesto](ADOS-V0-Manifesto.md).*
