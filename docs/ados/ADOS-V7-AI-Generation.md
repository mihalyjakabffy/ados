# Volume 7 — AI Generation Specification

**ADOS 1.0 · Volume 7 · Deterministic, machine-executable rules for automated documentation
generation.**

Volume 7 assumes documentation is produced by software: a model-driven generator, a layout solver,
a renderer, and a validator. Its rules are written so that two independent conforming
implementations, given the same input, produce **byte-identical output**.

---

## 7.0 Rule format in this volume

Volume 7 rules use the six-field machine format required for executable rules. The mapping to the
twelve-field format of the front matter is:

| Volume 7 field | Twelve-field equivalent |
|---|---|
| **Intent** | Purpose + Background + Problem |
| **Input** | (new) the data the rule consumes |
| **Output** | (new) the artefact or mutation the rule produces |
| **Constraints** | Decision + Implementation |
| **Exceptions** | Exceptions |
| **Validation** | Validation + Automation notes |

Examples and common mistakes are collected in `ADOS-A.7` rather than repeated per rule.

---

## 7.1 Machine-readable artefacts

### ADOS-7.1.010 — The five normative artefacts ⚠

**Intent.** Give the generator a single, versioned, machine-readable source for every constant,
rule, schema, grammar and threshold in this specification, so that no value is transcribed from
prose into code.

**Input.** This specification.

**Output.** Five artefacts under `machine/`:

| Artefact | Content | Consumed by |
|---|---|---|
| `ados-tokens.json` | Every numeric constant, keyed by token path | Renderer, solver |
| `ados-rules.yaml` | Every rule: ID, level, principle refs, evidence class, validation ID, dependencies | Validator, documentation build |
| `ados-sheet-schema.json` | JSON Schema for the sheet/package manifest (`ADOS-7.3`) | Generator, validator |
| `ados-naming.ebnf` | Grammar for every identifier and reference string | Parser, validator |
| `ados-validation.yaml` | Every metric, its formula, threshold, severity and gate | QA pipeline |

**Constraints.**
1. Prose and artefact shall not disagree. Where they do, the artefact is authoritative for machine
   consumption and the disagreement is a Severity 1 defect in the specification.
2. Every token referenced in prose as `{ados.…}` shall resolve.
3. Artefacts shall be versioned with the specification edition.

**Exceptions.** None.

**Validation.** `V-7.1.010`: token reference resolution = 100 %; every `shall` rule in the prose has
a registry entry; every registry entry has a prose rule; schema and grammar parse.

### ADOS-7.1.020 — Token namespace ⚠

**Intent.** Make constants addressable and prevent duplicate definitions of the same value.

**Input.** —

**Output.** A token tree with the top-level namespaces:

```
ados.sheet.*      sizes, margins, zones, module, fold
ados.type.*       faces, sizes, pitch, clear zone, measure
ados.line.*       widths, tiers, patterns, joins
ados.tone.*       ladder, targets, coverage
ados.scale.*      ladder, class map, resolvable feature size
ados.dim.*        offsets, terminators, chain spacing
ados.marker.*     bubble sizes, leader geometry
ados.density.*    fill, coverage, annotation counts
ados.hatch.*      pitch, angles, inventory
ados.qa.*         metric thresholds
```

**Constraints.**
1. A value shall appear once. Derived values shall be expressed as an expression over other tokens,
   with the derivation recorded, not as a literal.
2. Token paths are immutable across MINOR editions.

**Validation.** `V-7.1.020`: no duplicate literal values across the tree where one derives from
another; all derivations evaluate.

---

## 7.2 Determinism

### ADOS-7.2.010 — Determinism requirement ⚠

**Intent.** Make generated documentation reproducible, auditable and diffable. A generator whose
output varies between runs cannot be validated, cannot be reviewed by diff, and cannot be trusted
to have produced the approved artefact.

**Input.** Model state, project configuration, ADOS artefacts, generator version.

**Output.** A published package.

**Constraints.**
1. Given identical inputs, the generator shall produce byte-identical output.
2. No stochastic process shall influence layout, content selection, ordering or naming. Random seeds
   shall not be used, not even fixed ones, because a fixed seed makes output depend on library
   internals.
3. Iteration over collections shall use a defined total order, never hash or insertion order.
4. Floating-point results affecting placement shall be quantised to the sub-module lattice
   (`ADOS-3.3.030`) before use, so that platform floating-point differences cannot change output.
5. Timestamps and other environment-derived values shall be confined to declared metadata fields and
   shall be excludable for the purposes of the byte-identity check.
6. Where a language model or other non-deterministic component contributes content, its output shall
   be materialised into the input set as a reviewed, versioned artefact **before** generation, so
   that generation itself remains deterministic (`ADOS-7.9.030`).

**Exceptions.** None.

**Validation.** `V-7.2.010`: run the generator twice on identical inputs in different processes;
compare outputs excluding declared timestamp fields; differing bytes = 0.

### ADOS-7.2.020 — Banned subjective lexicon ⚠

**Intent.** Prevent rules that cannot be executed.

**Input.** Rule text.

**Output.** Pass/fail.

**Constraints.** Normative rule text (the `Decision` / `Constraints` fields) shall not contain:

```
appropriate, appropriately, as necessary, as required, adequate, balanced,
clean, clear (as a quality), elegant, generally, good practice, harmonious,
if possible, legible (unqualified), neat, pleasing, reasonable, sensible,
suitable, tidy, visually, well-organised, where practicable, wherever possible
```

Each shall be replaced by a measurable condition. `legible` is permitted only when immediately
qualified by a metric reference.

**Exceptions.** The words may appear in `Background`, `Problem` and informative text.

**Validation.** `V-7.2.020`: lexicon scan over normative fields; matches = 0.

### ADOS-7.2.030 — Total ordering ⚠

**Intent.** Remove ordering ambiguity everywhere it could affect output.

**Input.** Any collection processed by the generator.

**Output.** A deterministic sequence.

**Constraints.** The canonical orderings are:

| Collection | Order |
|---|---|
| Containers | By container identifier, lexicographic (ASCII) |
| Views on a sheet | By reading order: `(row, column)` from `ADOS-2.10.020`, then by view identifier |
| Elements within a view | By `(y descending, x ascending, GUID ascending)` in sheet coordinates |
| Annotations | By anchor position under the element order, then by annotation class ordinal, then GUID |
| Schedule rows | By the schedule's declared sort keys, then by GUID |
| Dimension chains | Outermost first; within a chain, by increasing coordinate along the chain axis |
| Legend entries | By channel ordinal (`ADOS-3.1.010`), then by declared meaning order |
| Notes | By note number |

Ties beyond these keys shall be broken by GUID ascending. GUID is always the final tie-break, and it
is stable (`ADOS-6.2.020`).

**Validation.** `V-7.2.030`: ordering functions are total (no ties remain); property-based test over
shuffled inputs produces identical output.

### ADOS-7.2.040 — Numeric determinism

**Intent.** Prevent platform-dependent output.

**Constraints.**
1. All lengths in the intermediate representation are integers in micrometres (µm).
2. Angles are integers in millidegrees.
3. Conversions to output units occur once, at render time, with round-half-away-from-zero.
4. Comparisons use exact integer arithmetic. Tolerances are explicit integer values, never epsilon
   comparisons on floats.

**Validation.** `V-7.2.040`: IR schema enforces integer types; no float appears in the IR.

---

## 7.3 The intermediate representation (ADOS-IR)

### ADOS-7.3.010 — IR as the contract ⚠

**Intent.** Separate *what the document contains* from *how it is drawn*, so that content generation,
layout and rendering can be independently implemented, tested and validated.

**Input.** Model, project configuration, ADOS artefacts.

**Output.** A single IR document per package, validating against `ados-sheet-schema.json`.

**Constraints.**
1. The IR is the sole input to the renderer. The renderer shall not query the model.
2. The IR is the sole input to the validator for all structural metrics. Only the pixel-level
   metrics of `ADOS-8.2` and `ADOS-8.7` operate on rendered output.
3. The IR is complete: no default may be applied at render time that is not present in the IR.
   Defaults are resolved during generation and materialised.
4. The IR is serialisable, diffable and human-readable (JSON or YAML, UTF-8, sorted keys, stable
   formatting).

**Validation.** `V-7.3.010`: schema validation passes; rendering the IR twice produces identical
output; no renderer-side default resolution occurs (instrumented check).

### ADOS-7.3.020 — IR object model ⚠

**Intent.** Define the IR precisely enough to implement.

**Output.** The following structure. Types are given as `name: type` with `µm` for integer
micrometres.

```yaml
package:
  package_id: string
  project: {code, name, jurisdiction, units, language, decimal_separator}
  set: {originator_code, nominated_issue_size, conformance_class, edition}
  status: enum(S0,S1,S2,S3,S4,S6,S7,A1..An,B1..Bn,WD)
  issue: {date, medium, recipients[]}
  generator: {name, version, artefact_versions{}}
  containers: [Container]

Container:
  container_id: string          # ADOS-2.5.010
  short_id: string              # ADOS-2.5.020
  type: enum(registry)          # ADOS-5.0.010
  sheet: {size, orientation, zoning_template}
  status, revision: string
  parties: {author, checker, approver}
  revisions: [{code, date, description, author, checker, affected_regions[]}]
  regions: [Region]
  references_out: [Reference]
  references_in: [Reference]
  scope_statement: string       # ADOS-0.3.090
  read_with: [container_id]

Region:
  region_id: enum(Z-DRAW,Z-TITLE,Z-REV,Z-NOTES,Z-KEY,Z-BANNER,Z-GRIDREF)
  bounds: {x: µm, y: µm, w: µm, h: µm}
  content: [View | Block]

View:
  view_id: string
  view_type: enum(plan, rcp, elevation, section, detail, interior_elevation,
                  schedule, diagram, key_plan)
  level: enum(L1..L5)
  scale_denominator: int
  origin: {x: µm, y: µm}        # on the sub-module lattice
  extent: {w: µm, h: µm}
  north_vector_mdeg: int
  cut_plane_height: µm | null
  view_range: {below: µm, above: µm} | null
  title: {text, position, size_token}
  geometry: [Stroke | Fill | Symbol]
  annotations: [Annotation]

Stroke:
  path: [{x: µm, y: µm}]        # already projected to sheet space
  tier: enum(W1,W2,W3)
  width_um: int                 # resolved, ADOS-4.1.010
  line_type: enum(L-CONT,L-DASH,L-DOT,L-CENT)
  pattern_phase_um: int         # ADOS-4.1.060
  tone: enum(T0..T5)
  depth_class: enum(cut, seen, beyond, hidden, background)
  source_guid: string

Fill:
  boundary: [[{x,y}]]           # outer ring, then holes
  tone: enum(T0..T5)
  hatch: {token, pitch_um, angle_mdeg, width_um} | null
  source_guid: string

Annotation:
  anno_id: string
  class: enum(text, dimension, tag, leader, note_tag, marker, level, grid_label)
  anchor: {x: µm, y: µm}
  placement: {x: µm, y: µm, rotation_mdeg: 0|90000}
  size_token: enum(t1..t8)
  cap_height_um: int
  weight: enum(regular, bold)
  case: enum(upper, sentence)
  content: string               # resolved; never a template
  source_ref: {kind, target} | null   # ADOS-4.6.030
  clear_zone_um: int
  mask: bool
  collision_group: string

Dimension(Annotation):
  chain_id: string
  chain_level: 1|2|3
  from_ref: {guid, face: enum(structural, finished, centre)}
  to_ref:   {guid, face}
  value_um: int
  displayed_value: string       # derived; ADOS-6.7.050 forbids override
  prefix, suffix: string        # CLR, ±5, (S)
  terminator: enum(oblique, arrow)

Reference:
  ref_id: string
  kind: enum(callout_section, callout_detail, callout_elevation, match_line,
             read_with, supersedes, spec_clause, external)
  source: {container_id, view_id?, anno_id?}
  target: {container_id, view_id?} | external_ref
  reciprocal_of: ref_id | null
```

**Constraints.**
1. Every field is mandatory unless marked nullable.
2. Coordinates in a `View` are sheet coordinates: projection and scaling occur before IR emission.
3. `tier` and `depth_class` are both present and shall be consistent (`ADOS-7.4.030`).
4. `content` strings are fully resolved: no templates, no placeholders, no unresolved references.

**Validation.** `V-7.3.020`: schema validation; consistency checks between paired fields; unresolved
placeholder pattern matches = 0.

### ADOS-7.3.030 — IR completeness ⚠

**Intent.** Guarantee that everything the validator needs is in the IR.

**Constraints.** The IR shall carry every fact required to evaluate every Volume 8 metric except
those explicitly defined over rendered pixels (`M1` sub-metrics for stroke rendering, `M7` print
metrics).

**Validation.** `V-7.3.030`: every metric in `ados-validation.yaml` declares its source (`ir` or
`raster`); `ir`-sourced metrics compute without model access.

---

## 7.4 The generation pipeline

### ADOS-7.4.010 — Pipeline stages ⚠

**Intent.** Fix the order of operations so that behaviour is predictable and each stage is
independently testable.

**Input.** Model, configuration, artefacts.

**Output.** Package.

**Constraints.** The pipeline shall have exactly these stages, in this order:

```
1  EXTRACT     Query the model. Produce a typed element set with properties.
2  CLASSIFY    Assign depth class, phase, discipline, content level to every element.
3  SELECT      Determine which containers exist and what each contains (Volume 2, Volume 5).
4  PROJECT     Project geometry to sheet space per view: scale, crop, cut plane, view range.
5  STYLE       Resolve tier, width, line type, tone, hatch from data by rule (ADOS-6.7.010).
6  ANNOTATE    Generate dimensions, tags, markers, notes, titles as unplaced objects with anchors.
7  LAYOUT      Solve placement: views on sheets, annotations within views (ADOS-7.5).
8  RESOLVE     Resolve every reference; generate reciprocals; fail on unresolved (ADOS-7.6).
9  EMIT        Serialise the IR.
10 VALIDATE    Run all IR-sourced checks. Block on failure.
11 RENDER      Produce PDF from the IR.
12 VERIFY      Run raster-sourced checks on the render. Block on failure.
13 PUBLISH     Write files, metadata, issue record, supersession (ADOS-6.11).
```

Stages shall not be reordered or merged. A stage shall not read data produced by a later stage.

**Exceptions.** Stage 7 may iterate internally (`ADOS-7.5.070`), and may request a re-run of stage 3
under the escalation rule, which shall be logged and bounded.

**Validation.** `V-7.4.010`: stage boundaries instrumented; out-of-order data access = 0; escalation
count within bounds and logged.

### ADOS-7.4.020 — Stage contracts

**Constraints.** Each stage has a typed input and output and shall be independently runnable from a
serialised intermediate:

| Stage | Consumes | Produces |
|---|---|---|
| EXTRACT | model | `elements.json` |
| CLASSIFY | `elements.json` | `elements.classified.json` |
| SELECT | classified elements, config | `containers.plan.json` |
| PROJECT | classified elements, plan | `views.geometry.json` |
| STYLE | views.geometry, style rules | `views.styled.json` |
| ANNOTATE | views.styled, content rules | `annotations.unplaced.json` |
| LAYOUT | views.styled, annotations.unplaced | `layout.json` |
| RESOLVE | layout, plan | `references.json` |
| EMIT | all | `package.ir.json` |
| RENDER | package.ir.json | `*.pdf` |

**Validation.** `V-7.4.020`: each stage runs standalone from its serialised input and produces
identical output to the full pipeline.

### ADOS-7.4.030 — Depth classification ⚠

**Intent.** Compute the line hierarchy of `ADOS-4.1.020` mechanically rather than assigning it.

**Input.** Element geometry, view cut plane, view range, view direction.

**Output.** `depth_class` and `tier` per stroke.

**Constraints.**

```
for each element E projected into view V:
    if E intersects V.cut_plane and E is a solid          → cut       → W3
    elif E is between V.cut_plane and V.view_range.below
         and E is visible from the view direction         → seen      → W2
    elif E is above V.cut_plane and within V.view_range.above → beyond → W1 + L-DASH
    elif E is below V.view_range.below                    → beyond    → W1 + L-DOT
    elif E is occluded by a nearer element                → hidden    → W1 + L-DASH
    elif E.discipline ≠ V.discipline or E.phase = existing_retained
                                                          → background → W1 + T1
    else                                                  → error E-STYLE-001
```

Exception per `ADOS-4.1.020` Ex. 1: at `scale_denominator ≥ 200`, `cut` maps to W2 when the element's
projected thickness < 700 µm on the sheet.

**Validation.** `V-7.4.030`: for every stroke, `tier = f(depth_class, scale)`; monotonicity holds;
`E-STYLE-001` count = 0.

### ADOS-7.4.040 — Content selection ⚠

**Intent.** Determine container existence and content from rules rather than from a hand-maintained
list.

**Input.** Model, stage, package purpose, Volume 5 required content.

**Output.** Container plan.

**Constraints.**
1. For each level in the model, emit the container set required by `ADOS-2.12.010` for the declared
   stage.
2. For each container type, emit the required content items of its Volume 5 chapter; each item maps
   to a query over the element set.
3. Where a required item's query returns empty and the condition is present in the model, raise
   `E-CONTENT-001` (missing content) and block.
4. Where a required item's query returns empty and the condition is absent, emit the exclusion
   statement required by `ADOS-0.3.090`.
5. Where a view exceeds the density limits after annotation, apply the remedy order of
   `ADOS-3.7.040` mechanically: (1) reclassify content level; (2) drop duplicates of authoritative
   values; (3) split view; (4) split sheet; escalate to `E-DENSITY-001` if none resolves.

**Validation.** `V-7.4.040`: required content coverage = 100 %; exclusion statements present for all
absent conditions; density limits satisfied.

### ADOS-7.4.050 — Annotation generation ⚠

**Intent.** Generate the annotation set deterministically from the model and the document type rules,
rather than tagging everything.

**Input.** Classified elements, view, document type requirements.

**Output.** Unplaced annotations with anchors.

**Constraints.**

*Tags.* For each element class required to be tagged by the view's document type: emit exactly one
tag per instance, anchored at the instance's projected centroid; content = the element's mark or
type code, never a property value (`ADOS-4.6.030`).

*Dimension chains.* For each plan view:

```
for each of the two principal axes:
    chain 3 := overall extent of the building envelope
    chain 2 := grid line positions along the axis
    chain 1 := for each external wall run: openings and element changes, referenced to
               the nearest grid line
    verify closure: Σ(chain 1 within a grid bay) = bay dimension        (ADOS-4.5.030)
                    Σ(chain 2) = chain 3
    if closure fails → E-DIM-001 (blocking; indicates model geometry error)
```

Chains are placed outside the envelope at 10 mm, 20 mm and 30 mm printed offsets.

*Level annotations.* One per distinct level value per view, at the leftmost occurrence in reading
order, plus one at every change.

*Markers.* One per reference; position derived from the referenced view's geometry
(`ADOS-4.7.040` extent matching).

*Notes.* Sheet notes are emitted only where a rule requires them: scope statement, read-with,
exclusions, phase legend, cut plane statement. Free-text notes are supplied as input data, never
generated.

**Validation.** `V-7.4.050`: tag count = required instance count; chain closure holds; no duplicate
dimensions between the same reference pair (`ADOS-4.5.050`).

---

## 7.5 The layout solver

### ADOS-7.5.010 — Solver formulation ⚠

**Intent.** Turn placement into a decidable problem with a unique answer.

**Input.** Views with extents; annotations with anchors and clear zones; sheet zoning; tokens.

**Output.** Placement coordinates for every view and annotation.

**Constraints.**
1. The placement domain is the sub-module lattice: all coordinates ∈ 5 mm ℤ² within the region
   bounds (`ADOS-3.3.030`).
2. The problem is expressed as: minimise the objective (`ADOS-7.5.040`) subject to the hard
   constraints (`ADOS-7.5.020`), with ties broken by `ADOS-7.5.050`.
3. The solver shall be deterministic: no randomised restarts, no time-based termination, no
   parallel non-deterministic reduction.
4. Termination is by exhaustion or by a fixed iteration bound; on reaching the bound, the solver
   escalates (`ADOS-7.5.070`) rather than returning a best-effort result silently.

**Validation.** `V-7.5.010`: repeated solves produce identical coordinates; all hard constraints
satisfied; escalations logged.

### ADOS-7.5.020 — Hard constraints ⚠

**Intent.** Enumerate the conditions that a layout shall satisfy, in a form a solver can enforce.

**Constraints.** In priority order (all are hard; the order governs which is reported first on
infeasibility):

| # | Constraint | Rule |
|---|---|---|
| H1 | No content outside its region | `ADOS-3.3.090` |
| H2 | No annotation overlaps another annotation's clear zone | `ADOS-3.4.080` |
| H3 | No text overlaps geometry without a mask | `ADOS-3.4.080` |
| H4 | No content within a fold-safe zone | `ADOS-3.3.100` |
| H5 | View-to-view separation ≥ 20 mm; view-to-boundary ≥ 10 mm | `ADOS-3.5.040` |
| H6 | Origins on the sub-module lattice | `ADOS-3.3.030` |
| H7 | View extents aligned to the column grid | `ADOS-3.3.040` |
| H8 | Leader angle ∈ {30°,45°,60°}; length ∈ [8,60] mm; single segment | `ADOS-4.6.010` |
| H9 | No leader–leader and no leader–dimension crossings | `ADOS-4.6.020` |
| H10 | Dimension chain offsets 10/20/30 mm; text above line | `ADOS-4.5.020` |
| H11 | Annotation count per search region ≤ 50 | `ADOS-3.7.030` |
| H12 | Local ink coverage ≤ 0.25 in any 20 mm window | `ADOS-3.7.020` |
| H13 | Fill ratio ∈ [0.40, 0.85] | `ADOS-3.7.010` |
| H14 | Distinct alignment edges ≤ 6 per axis | `ADOS-3.11.040` |
| H15 | Text cap height ≥ minimum at nominated size | `ADOS-3.4.010` |

**Validation.** `V-7.5.020`: post-solve check of H1–H15; violations = 0.

### ADOS-7.5.030 — Annotation candidate positions ⚠

**Intent.** Bound the search space and make placement preference explicit.

**Input.** Annotation, anchor, geometry.

**Output.** An ordered candidate list.

**Constraints.** For a tag anchored at a point, candidate positions are generated in this fixed
order and the first feasible candidate is taken:

```
1. Inside the anchored element, centred                  (if element bbox ⊇ text bbox + clear zone)
2. Inside the element, at the lattice point nearest the centroid
3. Outside: East, at 8 mm, on the lattice, with a 0° leader
4. Outside: North-East at 45°, 8 mm
5. Outside: North at 90°… then E→NE→N→NW→W→SW→S→SE at 8 mm
6. Same sequence at 16 mm, 24 mm, … up to 60 mm (ADOS-4.6.010 max)
7. Infeasible → escalate (ADOS-7.5.070)
```

The compass sequence starts at East and proceeds counter-clockwise. This is an arbitrary but fixed
choice; its only requirement is that it is the same in every implementation.

**Validation.** `V-7.5.030`: given a fixture, the produced placement equals the reference placement
in the conformance suite (`ADOS-7.10`).

### ADOS-7.5.040 — Objective function ⚠

**Intent.** Choose among feasible layouts deterministically and in accordance with the trade-off
register (`ADOS-1.9.010`).

**Constraints.** Minimise:

```
J = w1·Σ leader_length
  + w2·balance_error                       (ADOS-3.11.020)
  + w3·Σ alignment_deviation               (distance from the nearest shared alignment edge)
  + w4·count(annotations outside their element)
  + w5·Σ |fill_ratio − 0.65|               (target mid-band)
  + w6·count(leader–geometry crossings)

with fixed weights:
  w1 = 1        (per mm)
  w2 = 10000
  w3 = 2        (per mm)
  w4 = 50       (per annotation)
  w5 = 20000
  w6 = 200      (per crossing)
```

Weights are fixed by this specification and shall not be exposed as user parameters
(`ADOS-1.9.010` automation note). They are expressed in commensurable units by the multipliers
above; the absolute scale is irrelevant, only the ratios.

**Validation.** `V-7.5.040`: objective evaluates identically across implementations on the
conformance fixtures; the reported optimum matches.

### ADOS-7.5.050 — Tie-break ⚠

**Intent.** Guarantee a unique result when two layouts have equal objective value.

**Constraints.** Ties are broken by, in order:

1. Lower total leader length.
2. Placement earlier in the candidate order (`ADOS-7.5.030`).
3. Lower y-coordinate of the placement (nearer the sheet bottom).
4. Lower x-coordinate.
5. Lower GUID, ASCII ordering.

Rule 5 is total, so the result is always unique.

**Validation.** `V-7.5.050`: constructed tie fixtures resolve identically across implementations.

### ADOS-7.5.060 — View placement ⚠

**Intent.** Place views deterministically in reading order on the column grid.

**Constraints.**

```
1. Sort views by (document-type-defined ordinal, view_id).
2. Compute each view's placement box = extent + annotation bleed + 10 mm margin.
3. Assign to columns by first-fit in reading order (left→right, top→bottom),
   with each box occupying a whole number of columns.
4. If the last row is under-filled, distribute the residual space equally between rows,
   quantised to the sub-module, so that inter-view gaps remain ≥ 20 mm and equal.
5. If any view does not fit: escalate (ADOS-7.5.070).
```

Views are never rotated (`ADOS-4.3.030`, `ADOS-4.11.030`) and never scaled to fit
(`ADOS-4.2.040`).

**Validation.** `V-7.5.060`: placement equals the reference for the conformance fixtures; no
rotation; no scale deviation.

### ADOS-7.5.070 — Escalation ⚠

**Intent.** Ensure that an unsolvable layout produces a structural change or a hard failure, never a
degraded document.

**Constraints.** On infeasibility, the solver shall apply the following, in order, and re-solve;
each application is logged with the rule that triggered it:

```
1. Move a duplicate-value annotation to its authoritative carrier and remove it   (ADOS-2.2.010)
2. Reclassify content to the correct content level and remove it from this view   (ADOS-2.3.010)
3. Split the view along the declared split axis                                    (ADOS-3.7.040/3)
4. Split the sheet, generating a new container with the next serial                (ADOS-3.7.040/4)
5. Fail with E-LAYOUT-001
```

The solver shall never: reduce text size, reduce line width, reduce clear zones, reduce leader
minimums, place text without a mask, or omit required content.

**Validation.** `V-7.5.070`: escalation log present for every escalation; prohibited remedies never
applied (instrumented); `E-LAYOUT-001` handled as a blocking error.

---

## 7.6 Reference resolution and integrity

### ADOS-7.6.010 — Reference resolution ⚠

**Intent.** Guarantee `ADOS-2.4.030` and `ADOS-2.4.040` structurally.

**Input.** Container plan, views, markers, external reference list.

**Output.** Resolved reference graph; reciprocal references generated.

**Constraints.**
1. Every callout shall resolve to an existing view on an existing container in the package or in the
   live register.
2. For every resolved callout, a reciprocal `references_in` entry shall be generated on the target.
3. Reciprocal entries shall be rendered in the target view's title block area or notes region as a
   `Referenced from:` list.
4. External references shall resolve against the external reference list (`ADOS-5.2.040`).
5. Unresolved references → `E-REF-001`, blocking.

**Validation.** `V-7.6.010`: orphan callouts = 0; missing reciprocals = 0; external references
resolved = 100 %.

### ADOS-7.6.020 — Style dictionary closure ⚠

**Intent.** Prevent undeclared graphic states from reaching output.

**Constraints.** The renderer shall accept only style tokens present in the project's encoding table
(`ADOS-3.1.050`). An undeclared token is a build error `E-STYLE-002`, never a substituted default.

**Validation.** `V-7.6.020`: rendered style set ⊆ declared style set; `E-STYLE-002` = 0 at publish.

### ADOS-7.6.030 — Value resolution ⚠

**Intent.** Guarantee `ADOS-0.3.020` at build time.

**Constraints.**
1. Every annotation whose content derives from a fact shall resolve that fact from its authoritative
   carrier at generation time.
2. Where the same fact resolves to different values from two carriers, raise `E-FACT-001`, blocking.
3. Manual override of a resolved value is not representable in the IR (`ADOS-6.7.050`); the schema
   has no field for it.

**Validation.** `V-7.6.030`: cross-carrier consistency scan; conflicts = 0.

---

## 7.7 Content rules for generated text

### ADOS-7.7.010 — Generated text constraints ⚠

**Intent.** Bound what a generator may write, so that generated prose cannot introduce requirements,
opinions or unverifiable claims.

**Input.** Model facts, templates, the controlled vocabulary.

**Output.** Annotation and note strings.

**Constraints.**
1. Generated text shall be produced from declared templates with slots filled by resolved facts.
   Free-form generation of normative text is prohibited.
2. Templates shall be versioned artefacts, reviewed and approved like any other project content.
3. Generated text shall use only the project's controlled vocabulary (`ADOS-0.5.060`) and registered
   abbreviations (`ADOS-0.5.070`).
4. Generated notes shall satisfy `ADOS-0.5.050` (≤ 25 words, active voice, one requirement) and
   shall not contain prohibited content (`ADOS-4.8.040`).
5. A generator shall not create a requirement. Requirements originate in the specification and are
   referenced (`ADOS-4.8.010`).

**Validation.** `V-7.7.010`: every generated string matches a template instantiation; vocabulary and
abbreviation checks pass; banned-phrase matches = 0; word counts within limits.

### ADOS-7.7.020 — Language model output handling ⚠

**Intent.** Permit language models to assist without introducing non-determinism or unreviewed
content into issued documentation.

**Constraints.**
1. Language model output shall not be consumed directly by the generation pipeline.
2. Where a language model produces candidate content (a scope statement, a note, a decision-record
   summary), the output shall be written to a reviewed, versioned input artefact, approved by a
   named person, and only then consumed (`ADOS-7.2.010` constraint 6).
3. The artefact shall record: model identity and version, prompt reference, timestamp, reviewer,
   and approval.
4. Language model output shall never populate a value that has an authoritative carrier in the
   model. Facts come from the model; only prose comes from elsewhere.

**Validation.** `V-7.7.020`: no pipeline stage holds a network dependency on a generative service;
every generated-prose artefact carries a complete provenance record and an approval.

### ADOS-7.7.030 — Numeric formatting ⚠

**Constraints.**

| Value class | Format |
|---|---|
| Dimensions | Integer millimetres, no unit symbol, no thousands separator |
| Levels | Signed, three decimals, metres, with type prefix (`FFL +12.450`) |
| Areas | Two decimals, m², with unit |
| Angles | One decimal, degrees, with symbol |
| Percentages | Integer, with symbol |
| Ratios (scale) | `1:n` |

Rounding is round-half-away-from-zero, applied once, at formatting.

**Validation.** `V-7.7.030`: formatted strings match the class pattern; double-rounding = 0.

---

## 7.8 Error taxonomy

### ADOS-7.8.010 — Error classes and behaviour ⚠

**Intent.** Make failures loud, specific and actionable, and prevent degraded output.

**Constraints.**

| Code | Meaning | Behaviour |
|---|---|---|
| `E-MODEL-001` | Model health check failed (`ADOS-6.12.010`) | Block |
| `E-CONTENT-001` | Required content missing for the document type | Block |
| `E-CONTENT-002` | Content present but not required by any user | Warn, list |
| `E-STYLE-001` | Element could not be depth-classified | Block |
| `E-STYLE-002` | Undeclared style token | Block |
| `E-DIM-001` | Dimension chain does not close | Block |
| `E-DIM-002` | Duplicate dimension between the same references | Warn, auto-remove |
| `E-REF-001` | Unresolved reference | Block |
| `E-REF-002` | Missing reciprocal (auto-generable) | Auto-fix, log |
| `E-FACT-001` | Same fact, different values across carriers | Block |
| `E-DENSITY-001` | Density limits unsatisfiable after all remedies | Block |
| `E-LAYOUT-001` | Layout infeasible after all escalations | Block |
| `E-RENDER-001` | Rendered output fails a raster metric | Block |
| `E-META-001` | Missing or inconsistent metadata | Block |
| `E-PROV-001` | Missing provenance for generated content | Block |

**Constraints.**
1. A blocking error shall stop publication. Partial publication is prohibited (`ADOS-0.7.030`).
2. Every error shall report: code, container, view, element GUID, rule ID, and the measured value
   against the threshold.
3. Warnings shall be listed in the build report and counted; a warning count above the declared
   budget escalates to blocking.

**Validation.** `V-7.8.010`: error reports contain all six fields; blocking errors never produce
output files.

### ADOS-7.8.020 — Build report ⚠

**Intent.** Make the generation auditable.

**Output.** A build report accompanying every package, containing: generator identity and version;
artefact versions; input model version and hash; the full check results with measured values; every
escalation applied with its trigger; every warning; timing; and the byte hash of every output file.

**Validation.** `V-7.8.020`: report present, schema-valid, and its hashes match the published files.

---

## 7.9 Provenance and accountability

### ADOS-7.9.010 — Named approver ⚠

**Intent.** `ADOS-0.4.090`. Automation does not diffuse responsibility.

**Constraints.** Every published container shall record a named author, checker and approver. A
generator identity shall not populate any of the three. Where content was generated, the approver's
approval covers the generated content.

**Validation.** `V-7.9.010`: all three fields populated with person identifiers; generator strings in
person fields = 0.

### ADOS-7.9.020 — Generator identity in metadata ⚠

**Constraints.** Every published file's metadata shall record the generator name, version, artefact
versions and the input model version and hash (`ADOS-6.11.030`).

**Validation.** `V-7.9.020`: metadata fields present and matching the build report.

### ADOS-7.9.030 — Content provenance ⚠

**Intent.** `ADOS-0.4.110`. Make it possible to find every document affected by an error in a source.

**Constraints.** Every content item that did not originate in this project's model shall record its
origin: standard detail library item and version; precedent project and container; template and
version; generated-prose artefact and approval. The provenance index shall be queryable by source,
so that "which containers used library detail `STD-034 v3`?" is answerable in one query.

**Validation.** `V-7.9.030`: provenance recorded for every non-model content item; reverse index
builds; unattributed items = 0.

---

## 7.10 Generator conformance

### ADOS-7.10.010 — Conformance test suite ⚠

**Intent.** Make "this generator conforms to ADOS" a testable claim.

**Constraints.** A conforming generator shall pass a test suite comprising:

| Class | Content | Pass criterion |
|---|---|---|
| **Determinism** | 20 fixtures, each run twice in separate processes | Byte-identical output |
| **Reference layouts** | 30 fixtures with published reference IR and reference PDF | IR equal; PDF visually identical within the declared raster tolerance |
| **Constraint satisfaction** | 50 fixtures designed to stress H1–H15 | All hard constraints satisfied |
| **Tie-break** | 15 fixtures constructed to produce ties at each tie-break level | Result matches the reference |
| **Escalation** | 12 fixtures that are infeasible at increasing severity | Correct escalation applied, logged, and never a prohibited remedy |
| **Error handling** | One fixture per error code | Correct code, correct blocking behaviour, all six report fields |
| **Metric agreement** | 20 fixtures with published metric values | Computed metrics equal the reference within the declared tolerance |

**Validation.** `V-7.10.010`: suite passes at 100 %; results published with the generator version.

### ADOS-7.10.020 — Reference implementation obligations

**Constraints.** The reference fixtures, reference IR and reference outputs are part of the
specification's artefact set and are versioned with it. A MINOR edition may add fixtures; it shall
not change existing reference outputs. Changing a reference output requires a MAJOR edition and a
migration table.

**Validation.** `V-7.10.020`: fixture hashes stable across MINOR editions.

### ADOS-7.10.030 — Human review remains mandatory ⚠

**Intent.** `ADOS-0.4.100`. A passing generator is not an approved document.

**Constraints.** Automated conformance shall not substitute for the check and approval states of
`ADOS-2.9.030`. The QA gate (`ADOS-0.7.030`) is necessary, not sufficient. The reviewer's obligation
is the content — whether the documented design is correct — which no metric measures.

**Validation.** `V-7.10.030`: every authorised container has a recorded human checker and approver
distinct from each other (`ADOS-8.10.020`).

---

## 7.11 Summary of Volume 7

1. Five machine-readable artefacts are normative; prose never carries a value that code must
   transcribe.
2. Determinism is absolute: no randomness, total orderings everywhere, integer arithmetic, byte
   identity as the test.
3. The IR is the contract between generation, rendering and validation; it is complete, sorted,
   diffable and integer-valued.
4. Thirteen pipeline stages with typed contracts, each independently runnable.
5. Layout is a constrained optimisation with fifteen hard constraints, a fixed objective, a total
   tie-break, and an escalation ladder that never degrades the document.
6. References resolve or the build fails; undeclared styles fail; conflicting facts fail.
7. Language model output is materialised, reviewed and approved before entering the pipeline.
8. Fifteen error codes, all blocking except two, each reporting six fields.
9. Provenance is recorded and reverse-indexed; a named person always approves.

---

*Continue to [Volume 8 — Quality Assurance](ADOS-V8-Quality-Assurance.md).*
