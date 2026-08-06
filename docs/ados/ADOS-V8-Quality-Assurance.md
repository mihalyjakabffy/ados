# Volume 8 — Quality Assurance

**ADOS 1.0 · Volume 8 · Measurable quality with objective pass/fail criteria.**

Volume 8 converts the quality definition of `ADOS-0.7.010` into nine metrics, each with sub-metrics,
formulas, thresholds and a gate. Everything here is computed, not judged. Where human judgement is
required, Volume 8 specifies the *procedure* for obtaining it so that the result is repeatable.

---

## 8.1 Principles of measurement

### ADOS-8.1.010 — Every requirement has a check ⚠

**Purpose.** `ADOS-0.3.070` restated as an operational obligation on this volume.

**Decision.** Every `shall` rule in this specification shall have exactly one primary validation
procedure, identified by a `V-` identifier, defined in `machine/ados-validation.yaml` with: the
input source (`ir` or `raster` or `model`), the computation, the threshold, the severity, and the
gate at which it is applied.

**Validation.** `V-8.1.010`: registry coverage = 100 %; validations without a computation = 0.

### ADOS-8.1.020 — Metric properties ⚠

**Decision.** A metric shall be:

| Property | Meaning |
|---|---|
| **Objective** | Two evaluators obtain the same value |
| **Deterministic** | Two runs obtain the same value |
| **Sourced** | Computed from a declared artefact (IR, raster, model), not from an opinion |
| **Thresholded** | Has a numeric pass/fail boundary, not a range of acceptability |
| **Attributable** | Reports the container, view and element responsible |
| **Actionable** | The failure implies a specific remedy |

A proposed metric lacking any property shall not be adopted.

**Validation.** `V-8.1.020`: every metric in the registry declares all six.

### ADOS-8.1.030 — Metric scope ⚠

**Decision.** Every metric is computed at two scopes: **sheet** and **set**. Where they differ, the
set-level threshold governs (`ADOS-0.7.020`).

### ADOS-8.1.040 — What metrics do not measure ⚠

**Decision.** The metric set measures whether documentation *communicates*. It does not measure
whether the documented design is *correct*. Design correctness is established by the check and
approval states of `ADOS-2.9.030` and by discipline-specific review, and shall not be inferred from
a passing metric set.

**Rationale.** A generator can produce a perfectly conforming set of drawings of a building that
will not stand up. Stating this boundary explicitly prevents the metric set from being used as a
substitute for professional review (`ADOS-7.10.030`).

---

## 8.2 M1 — Readability

**Question.** Can the marks be resolved at all, under the adverse reference condition?

**Source.** IR for M1.1–M1.5; raster for M1.6–M1.7.

### ADOS-8.2.010 — M1 sub-metrics and thresholds ⚠

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M1.1 | Minimum cap height | `min(cap_height)` over all text at nominated size | ≥ 2.5 mm (≥ 1.8 mm for objects tagged `secondary`) | S1 |
| M1.2 | Minimum stroke width | `min(width)` over all strokes at nominated size | ≥ 0.18 mm; ≥ 0.25 mm for safety-critical classes | S1 |
| M1.3 | Text clear-zone violations | count of text bboxes whose expanded zone intersects an unmasked mark | 0 | S1 |
| M1.4 | Tone separation | `min(ΔL*)` over meaning-bearing tone pairs used adjacently | ≥ 18; ≥ 36 for critical pairs | S2 |
| M1.5 | Hatch pitch | `min(printed pitch)` | ≥ 0.5 mm and ≥ width + 0.30 mm | S2 |
| M1.6 | Degraded character recovery | see `ADOS-8.2.030` | CER ≤ 0.02 | S1 |
| M1.7 | Degraded stroke survival | see `ADOS-8.2.040` | ≥ 0.99 of strokes present | S1 |

**Validation.** `V-8.2.010`: all sub-metrics computed and within threshold.

### ADOS-8.2.020 — Nominated-size evaluation ⚠

**Decision.** M1 shall be computed on the document rendered at the smallest nominated issue size
(`ADOS-3.2.040`), never at the authored size.

**Validation.** `V-8.2.020`: the evaluation record states the size used; it equals the nominated
size.

### ADOS-8.2.030 — Character recovery test ⚠

**Purpose.** Measure legibility with an instrument rather than an opinion.

**Decision.** The degraded render (`ADOS-8.2.040`) shall be processed by an OCR engine and the
recovered text compared, per text object, against the known content from the IR. The character error
rate shall not exceed 0.02.

```
CER = (substitutions + insertions + deletions) / total_characters_in_IR
```

**Rationale.** OCR is a conservative but repeatable proxy for human character recognition under
degradation. It is deliberately harsher than a human reader, who has context; the 2 % allowance
absorbs OCR's own error floor on technical strings.

**Implementation.** The engine, its version and its configuration shall be declared and pinned, so
that the metric is reproducible. Text objects rotated 90° are evaluated after a 90° rotation of the
crop.

**Exceptions.**
1. Text over hatch is excluded only if the hatch is masked; unmasked text is an M1.3 failure and is
   not excluded here.

**Validation.** `V-8.2.030`: CER computed per container and per set; both ≤ 0.02.

### ADOS-8.2.040 — Degradation simulation ⚠

**Purpose.** Reproduce the adverse reference condition deterministically.

**Decision.** The degradation pipeline shall be:

```
1. Render the page to greyscale at 600 dpi from the vector source.
2. Scale to the nominated issue size (if different from authored).
3. Generation 1:  Gaussian blur σ = 0.5 device pixels
                  → gamma adjust to simulate dot gain per the declared transfer curve
                  → threshold at 50 % with a 2 % dither
4. Generation 2:  repeat step 3 on the output of step 3.
5. Add uniform sensor noise at σ = 2 grey levels.
```

Every parameter is fixed by this rule so that the simulation is deterministic and comparable across
projects and implementations.

**Validation.** `V-8.2.040`: simulation parameters logged; running twice produces identical output.

### ADOS-8.2.050 — Digital reference condition

**Decision.** For screen-only deliverables (`ADOS-0.3.060` Ex. 1), M1 is evaluated at 100 % zoom on a
1920 × 1080 display model with the page fitted to height, with thresholds: minimum rendered cap
height 8 device pixels; minimum stroke 1.5 device pixels; no degradation simulation.

**Validation.** `V-8.2.050`: screen-only containers evaluated under this condition and watermarked
(`ADOS-0.3.060` Ex. 1).

### ADOS-8.2.060 — Note text complexity ⚠

**Purpose.** Bound the reading difficulty of note text, language-independently.

**Decision.** For every note:

| Measure | Threshold |
|---|---|
| Words per sentence | ≤ 25 (`ADOS-0.5.050`) |
| Sentences per note | ≤ 2 |
| Subordinate clause depth | ≤ 1 |
| Negations per sentence | ≤ 1 |
| Unregistered abbreviations | 0 |
| Terms outside the controlled vocabulary | 0 |

**Rationale.** Syllable-based readability formulas are calibrated to English prose and are invalid
for technical notes and for other languages. Clause depth, negation count and sentence length are
language-neutral and are the actual drivers of misinterpretation in second-language reading
(`ADOS-0.5.090`).

**Validation.** `V-8.2.060`: all six measures within threshold for every note.

---

## 8.3 M2 — Consistency, and M3 — Hierarchy

**Question (M2).** Does the reader's learned template hold across the set?
**Question (M3).** Is importance visible before content is read?

### ADOS-8.3.010 — M2 sub-metrics ⚠

Consistency is measured by **exact identity**, not by percentage similarity, because the cost of
inconsistency is incurred by a single deviation (§1.2.6).

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M2.1 | Zone origin variance | `max` deviation of any zone origin from the set mode | 0 mm | S2 |
| M2.2 | Title block field position variance | as above, per field | 0 mm | S2 |
| M2.3 | North vector variance across plans | `max(|θ − mode(θ)|)` | 0° | S1 |
| M2.4 | Scale set cardinality per drawing class | `|distinct scales|` | 1 (unless registered) | S2 |
| M2.5 | Distinct line widths per sheet | count | ≤ 5 | S2 |
| M2.6 | Distinct text sizes per sheet | count | ≤ 5 | S2 |
| M2.7 | Distinct tones per sheet | count | ≤ 4 | S2 |
| M2.8 | Distinct hatch patterns in set | count | ≤ 8 | S2 |
| M2.9 | Distinct symbols in set | count | ≤ 30 | S3 |
| M2.10 | Distinct font families | count | ≤ 2 (≤ 3 with monospace) | S2 |
| M2.11 | View template coverage | `views with template / views` | 1.00 | S2 |
| M2.12 | Per-element graphic overrides | count | 0 | S2 |
| M2.13 | Key plan geometry identity | hash equality across the set | identical | S3 |
| M2.14 | Encoding table coverage | `mapped states / observed states` | 1.00 | S1 |
| M2.15 | Dimension style variance | count of distinct dimension styles | 1 | S3 |

**Validation.** `V-8.3.010`: all sub-metrics within threshold.

### ADOS-8.3.020 — Consistency baseline

**Decision.** Where a threshold is "the set mode", the mode shall be computed over the set and any
sheet deviating shall be reported individually, not averaged.

**Rationale.** An average conceals the single deviating sheet, which is the entire subject of the
metric.

### ADOS-8.3.030 — Grouping ratio ⚠

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M2.16 | Grouping ratio | `min(gap_between) / max(gap_within)` per declared group | ≥ 2.0 | S3 |

**Validation.** `V-8.3.030`: computed per group; violations reported with the group identifier.

### ADOS-8.3.040 — M3 salience ordering ⚠

**Purpose.** Verify that the visual hierarchy matches the required reading sequence
(`ADOS-3.6.010`), objectively.

**Decision.** Compute a salience score for every annotation and view title:

```
salience(text)   = cap_height_mm × weight_factor × (1 + 0.5·is_upper)
                   weight_factor = 1.0 regular, 1.6 bold
salience(fill)   = sqrt(area_mm²) × (L*_paper − L*_fill) / 100
salience(stroke) = width_mm × sqrt(length_mm) × 3
```

Rank the elements of each class and compare with the required order:

```
required order (descending salience):
  sheet number  >  sheet title  >  status  >  view title  >  view content  >  annotation
```

**Threshold.** Rank inversions between adjacent required levels = 0. Inversions between non-adjacent
levels = 0.

**Rationale.** The salience proxy is crude but monotonic in the properties that actually drive
attention capture (size, contrast, weight). Its purpose is to catch inversions — a bold 5 mm note
competing with the sheet title — not to model perception precisely.

**Validation.** `V-8.3.040`: inversion count = 0.

### ADOS-8.3.050 — M3 emphasis budget ⚠

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M3.2 | Emphasis area ratio | `emphasised area / drawing area` | ≤ 0.10 | S3 |
| M3.3 | Hierarchy levels per region | count | ≤ 3 | S3 |
| M3.4 | Channels differing per hierarchy step | count | 1 (or ≥ 2 for life-safety) | S3 |

---

## 8.4 M4 — Information completeness

**Question.** Are all the questions this document is responsible for actually answered?

### ADOS-8.4.010 — M4 sub-metrics ⚠

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M4.1 | Required content coverage | `present required items / required items` per document type | 1.00 | S1 |
| M4.2 | Package composition | required containers present for the stage (`ADOS-2.12.010`) | 1.00 | S1 |
| M4.3 | Scope statement presence | sheets with a non-empty scope statement / sheets | 1.00 | S2 |
| M4.4 | Exclusion completeness | scope boundaries with an exclusion note / boundaries | 1.00 | S1 |
| M4.5 | Empty schedule cells | count | 0 | S2 |
| M4.6 | Untagged instances | elements of a tagged class without a tag | 0 | S1 |
| M4.7 | Undefined type codes | codes used without a definition | 0 | S1 |
| M4.8 | Unused type definitions | codes defined without use | 0 | S3 |
| M4.9 | Unresolved holds | `TBC` tokens without a hold register entry | 0 | S1 |
| M4.10 | Dimension chain closure | chains with `Σ sub ≠ overall` | 0 | S1 |
| M4.11 | Detail condition coverage | conditions mapped to a detail / conditions | 1.00 | S1 |
| M4.12 | Section coverage | `ADOS-5.14.020` rules met | all | S2 |
| M4.13 | Legend completeness | states with a legend entry / states used | 1.00 | S2 |
| M4.14 | Provenance completeness | survey/assumed content marked | 1.00 | S1 |

**Validation.** `V-8.4.010`: all sub-metrics within threshold.

### ADOS-8.4.020 — Question coverage ⚠

**Decision.** For each document type, the questions it is responsible for (`ADOS-0.5.010`) shall be
demonstrably answered: each question maps to required content items, and M4.1 covers them. A document
type whose questions cannot be mapped to content items is misspecified.

**Validation.** `V-8.4.020`: question-to-content mapping complete for every registered type.

### ADOS-8.4.030 — Noise measurement ⚠

**Decision.** Content present but not required by any listed user shall be reported.

```
noise_ratio = (annotation objects not traceable to a required content item) / (annotation objects)
threshold: ≤ 0.02
```

**Rationale.** A hard 0 is unachievable because some legitimate content is project-specific and not
enumerable in advance; 2 % bounds accumulation while allowing genuine exceptions, each of which is
listed for review.

**Validation.** `V-8.4.030`: noise ratio ≤ 0.02; the unmatched objects are listed.

### ADOS-8.4.040 — Reference integrity ⚠

| ID | Sub-metric | Threshold | Severity |
|---|---|---|---|
| M4.15 | Unresolved references | 0 | S1 |
| M4.16 | Missing reciprocals | 0 | S2 |
| M4.17 | References to superseded containers | 0 | S1 |
| M4.18 | External references not listed | 0 | S2 |

### ADOS-8.4.050 — Duplicate value scan ⚠

**Purpose.** Enforce `ADOS-0.3.020` by measurement.

**Decision.** For every fact class with an authoritative carrier, scan all containers for values of
that class appearing outside the carrier. Report: duplicates that agree (a `ADOS-2.2.030` violation)
and duplicates that disagree (a Severity 1 defect).

```
threshold: disagreeing duplicates = 0
           agreeing duplicates    = 0, except declared safety duplications (ADOS-2.2.040)
```

**Validation.** `V-8.4.050`: scan executed over the whole set; both counts within threshold.

### ADOS-8.4.060 — Stale derived content ⚠

**Purpose.** Detect the failure mode that derived workflows introduce: a view or value that is no
longer connected to its source.

**Decision.** Detect and report:

1. Manual overrides of derived values (`ADOS-6.7.050`) — threshold 0.
2. Exploded or detached views — threshold 0.
3. Views whose last regeneration precedes the model's last relevant change — threshold 0.
4. Schedules whose content differs from a fresh query — threshold 0.
5. Imported 2-D content whose source file version differs from the recorded version — threshold 0.

**Validation.** `V-8.4.060`: all five counts = 0.

---

## 8.5 M5 — Visual balance and composition

**Question.** Is attention distributed as intended, and is the sheet used well?

### ADOS-8.5.010 — M5 sub-metrics ⚠

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M5.1 | Balance error | `\|centroid(ink) − centre(Z-DRAW)\| / diagonal` | ≤ 0.10 | S3 |
| M5.2 | Fill ratio | union of view bboxes / drawing area | 0.40–0.85 | S3 |
| M5.3 | Local ink coverage | max over 20 mm windows | ≤ 0.25 | S2 |
| M5.4 | Annotation density | max per search region | ≤ 50 | S2 |
| M5.5 | Alignment edges | distinct clustered edges per axis | ≤ 6 | S3 |
| M5.6 | Lattice conformance | placeable origins on the 5 mm lattice | 1.00 | S3 |
| M5.7 | View separation | min pairwise gap | ≥ 20 mm | S3 |
| M5.8 | Boundary clearance | min view-to-boundary gap | ≥ 10 mm | S3 |
| M5.9 | Fold-zone intrusions | count | 0 | S2 |

**Validation.** `V-8.5.010`: all within threshold.

### ADOS-8.5.020 — Whitespace distribution

**Decision.** Report the coefficient of variation of inter-view gaps. A high value indicates
inconsistent grouping and shall be investigated, but is not a gate.

```
CV = σ(gaps) / μ(gaps)      report only; investigate above 0.5
```

---

## 8.6 M6 — Navigation

**Question.** Can the reader move through the set without loss?

### ADOS-8.6.010 — M6 sub-metrics ⚠

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M6.1 | Index completeness | register rows / live containers | 1.00 | S1 |
| M6.2 | Index currency | rows whose revision matches the container | 1.00 | S1 |
| M6.3 | Navigation depth | longest shortest-path index → fact carrier | ≤ 3 | S3 |
| M6.4 | Key plan presence | partial views with a key plan / partial views | 1.00 | S2 |
| M6.5 | Identifier grammar conformance | identifiers parsing / identifiers | 1.00 | S1 |
| M6.6 | Identifier uniqueness | duplicate identifiers | 0 | S1 |
| M6.7 | Series conformance | containers whose series matches their type | 1.00 | S3 |
| M6.8 | Match-line reciprocity | reciprocal match lines / match lines | 1.00 | S2 |
| M6.9 | Marker resolution | markers resolving to an existing view | 1.00 | S1 |
| M6.10 | Marker density | max markers per view | ≤ 12 | S3 |
| M6.11 | Reference bubble completeness | bubbles with both fields | 1.00 | S2 |
| M6.12 | Orientation test | see `ADOS-8.6.020` | ≤ 5 s, 100 % correct | S2 |

### ADOS-8.6.020 — Orientation test ⚠

**Purpose.** Measure the sheet's ability to identify itself, with a repeatable human procedure.

**Decision.** Procedure:

```
1. Select 5 sheets at random from the set, using a seeded, recorded selection.
2. Present each to a participant unfamiliar with the sheet, printed at the nominated size.
3. Start a timer. Ask three questions:
     a. What type of document is this?
     b. What part of the building does it show?
     c. At what scale?
4. Stop the timer when all three are answered.
5. Record time and correctness.
```

**Threshold.** Median time ≤ 5 s and correctness = 100 % across the sample.

**Machine proxy** (run on every sheet; the human test is run per set per stage): all fixed-position
identity elements (sheet number, title, scale, status, key plan, north point) are present, within
their zones, unobstructed, and at or above their minimum sizes. The proxy is necessary but not
sufficient; the human test governs.

**Validation.** `V-8.6.020`: proxy passes on 100 % of sheets; human test recorded per set per stage
with the sample, times and correctness.

### ADOS-8.6.030 — Digital navigation

| ID | Sub-metric | Threshold | Severity |
|---|---|---|---|
| M6.13 | Internal hyperlink coverage (digital issue) | ≥ 0.95 of references | S3 |
| M6.14 | Bookmark presence in multi-page documents | 1.00 | S3 |
| M6.15 | Text searchability | extracted text / IR text | 1.00 | S2 |

---

## 8.7 M7 — Print quality

**Question.** Does the document survive the reproduction chain?

### ADOS-8.7.010 — M7 sub-metrics ⚠

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M7.1 | Page size | rendered page dimensions vs. declared | ±0.5 mm | S2 |
| M7.2 | Scaling flags | count of scale-to-fit or shrink flags | 0 | S2 |
| M7.3 | Vector integrity | pages containing a full-page raster | 0 | S1 |
| M7.4 | Font embedding | embedded fonts / used fonts | 1.00 | S1 |
| M7.5 | Raster resolution | min effective dpi of embedded images | ≥ 600 | S3 |
| M7.6 | Tone accuracy | measured L* vs. target on the reference device | ±4 | S2 |
| M7.7 | Transfer curve currency | age of the calibration record | ≤ 12 months | S3 |
| M7.8 | Degraded stroke survival | see M1.7 | ≥ 0.99 | S1 |
| M7.9 | Margin conformance | marks outside the frame | 0 | S2 |
| M7.10 | Greyscale equivalence | all M1–M3 metrics pass on the greyscale render | pass | S1 |
| M7.11 | PDF/A conformance (archive copies) | validator result | pass | S2 |

### ADOS-8.7.020 — Photograph robustness (safety-critical documents)

**Decision.** For fire strategy, escape and setting-out drawings, an additional check simulates
photographic capture: perspective warp of ±5°, illumination gradient of 30 %, JPEG quality 60, then
re-threshold. M1.6 (character recovery) is re-run with a relaxed threshold of CER ≤ 0.05.

**Rationale.** These documents are the ones most often consulted by phone photograph in urgent
circumstances.

**Validation.** `V-8.7.020`: applied to the declared document classes; CER ≤ 0.05.

### ADOS-8.7.030 — Link and reference checker

**Decision.** A checker shall resolve every reference string in the published PDFs — cross-references,
specification clause citations, standard citations, container identifiers — against the register and
the external reference list, and report unresolved strings.

**Validation.** `V-8.7.030`: unresolved reference strings = 0.

---

## 8.8 M8 — Accessibility

**Question.** Is the document usable by all defined users, and by machines?

### ADOS-8.8.010 — M8 sub-metrics ⚠

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M8.1 | Colour independence | greyscale render passes M1–M4 | pass | S1 |
| M8.2 | Colour-only encodings | distinctions carried by colour alone | 0 | S1 |
| M8.3 | CVD distinguishability | min ΔE between meaning-bearing colours under protanopia, deuteranopia, tritanopia simulation | ≥ 20 | S2 |
| M8.4 | Text contrast | min contrast ratio of text against its background | ≥ 7:1 | S1 |
| M8.5 | Reversed text | count | 0 | S2 |
| M8.6 | Text extraction | extracted characters / IR characters | 1.00 | S2 |
| M8.7 | Document language tag | present and correct | pass | S3 |
| M8.8 | Logical structure (documents) | tagged PDF with heading structure | pass | S3 |
| M8.9 | Metadata completeness | fields of `ADOS-6.11.030` populated | 1.00 | S2 |
| M8.10 | Machine-readable data delivery | structured export present where required | pass | S2 |
| M8.11 | Minimum interactive target (digital) | hyperlink hot-zone size | ≥ 6 mm | S4 |

**Validation.** `V-8.8.010`: all within threshold.

### ADOS-8.8.020 — Accessibility applies to the reader, not only to compliance

**Decision.** M8 shall be evaluated on issued documentation, not only on documents that a regulation
requires to be accessible. `ADOS-0.4.070` and `ADOS-0.4.080` make this an ethical requirement
independent of statute.

---

## 8.9 M9 — Automation readiness, and defect classification

### ADOS-8.9.010 — Defect definition and severity ⚠

**Purpose.** Give "defect" a precise meaning and a consistent response.

**Decision.** A **defect** is any of: a failed `shall` rule; an undocumented deviation from a `shall`
rule; a metric outside its threshold; or a recommendation not followed without a recorded
justification.

Severity classes:

| Severity | Definition | Response | Gate effect |
|---|---|---|---|
| **S1** | Could cause a construction error, a safety consequence, or renders information unusable | Correct before issue | Blocks all issues |
| **S2** | Degrades reliability or breaks the reader's template | Correct before issue at `S3` and above | Blocks `S3`+ |
| **S3** | Reduces efficiency; no correctness consequence | Correct before the next issue | Blocks `A`/`B` |
| **S4** | Refinement | Log; correct opportunistically | No gate |

**Decision (continued).** An undocumented deviation from a `shall` rule is a defect at the severity
of the rule it deviates from. Documented deviations, recorded in the Deviation Register with an
approver, are not defects.

**Validation.** `V-8.9.010`: every reported failure carries a severity; deviations without a
register entry are counted as defects.

### ADOS-8.9.020 — M9 sub-metrics ⚠

**Question.** Can this documentation be generated and validated deterministically?

| ID | Sub-metric | Formula | Threshold | Severity |
|---|---|---|---|---|
| M9.1 | IR schema validity | validator result | pass | S2 |
| M9.2 | Determinism | byte identity across two runs | pass | S2 |
| M9.3 | Manual value overrides | count (`ADOS-6.7.050`) | 0 | S1 |
| M9.4 | Per-element graphic overrides | count | 0 | S2 |
| M9.5 | View template coverage | 1.00 | S2 |
| M9.6 | Classification coverage | classified elements / elements | 1.00 | S2 |
| M9.7 | Parameter binding | schedule fields bound to parameters | 1.00 | S2 |
| M9.8 | Model health checks | `ADOS-6.12.010` results | all pass | S1 |
| M9.9 | Naming grammar conformance | 1.00 | S2 |
| M9.10 | Encoding table closure | observed states ⊆ declared states | pass | S1 |
| M9.11 | Provenance coverage | non-model content with provenance | 1.00 | S2 |
| M9.12 | Build report presence and hash match | pass | S2 |

**Validation.** `V-8.9.020`: all within threshold.

### ADOS-8.9.030 — Defect escape rate ⚠

**Purpose.** Measure the QA system itself.

**Decision.** For each project, compute:

```
escape_rate = defects found after issue / (defects found before issue + defects found after issue)
```

where post-issue defects are counted from the RFI register (`ADOS-5.25`) classified as documentation
defects, plus instructions classified as cause = "error" (`ADOS-5.26.010`).

**Threshold.** Reported, trended, and reviewed at each stage. A target shall be set by the practice
and reviewed annually; ADOS does not set an absolute value because the base rate depends on project
type. A rising trend is a governance failure requiring action.

**Validation.** `V-8.9.030`: escape rate computed per stage; trend recorded; action recorded where
rising.

### ADOS-8.9.040 — RFI cause analysis ⚠

**Decision.** Every RFI classified as a documentation defect shall be mapped to the rule that would
have prevented it. Where no rule would have prevented it, the case is a candidate for a new rule
(`ADOS-1.11.010`).

**Rationale.** This closes the loop: the standard is improved by the failures it did not prevent.

**Validation.** `V-8.9.040`: mapping complete; unmapped cases raised as change requests.

---

## 8.10 Roles, governance and procedure

### ADOS-8.10.010 — Roles ⚠

| Role | Responsibility |
|---|---|
| **Author** | Produces the container; runs the automated checks; corrects failures |
| **Checker** | Verifies content correctness and completeness against the document type checklist |
| **Approver** | Authorises issue; accountable for status |
| **Documentation Standard Owner (DSO)** | Maintains the standard, the templates, the validation configuration; adjudicates deviations |
| **Information Manager** | Maintains the register, the CDE structure, the issue records |

### ADOS-8.10.020 — Separation of author and checker ⚠

**Decision.** The checker shall not be the author. The approver may be the checker only for Class C
projects, and the combination shall be recorded.

**Rationale.** Self-checking detects a fraction of one's own errors, because the same mental model
that produced the error is used to look for it.

**Validation.** `V-8.10.020`: author ≠ checker on every authorised container; combined roles recorded
where permitted.

### ADOS-8.10.030 — Check evidence ⚠

**Decision.** A check shall produce evidence: the checklist with each item marked, the automated
report, the checker's identity and date. A container with no check evidence shall not be authorised.

**Validation.** `V-8.10.030`: evidence present for every authorised container.

### ADOS-8.10.040 — Rule admission ⚠

**Decision.** The DSO shall reject a proposed rule that: cannot be traced to a principle
(`ADOS-0.3`); has no deterministic validation; duplicates an existing rule; or depends on a fact
whose half-life is shorter than the documentation's intended life (`ADOS-0.6.010`).

**Validation.** `V-8.10.040`: every registry entry has non-empty `principle_refs`, `evidence_class`
and `validation.check_id`.

### ADOS-8.10.050 — The gate ⚠

**Decision.** The gate procedure is:

```
1. Author runs the automated check suite. All S1 and S2 defects corrected or registered.
2. Author completes the document type checklist (Volume 5).
3. Checker verifies content correctness, completeness and coordination.
4. Automated suite re-run after any correction. No manual re-check substitutes.
5. Approver reviews the report, the deviation register entries and the checklist, and authorises.
6. Publication runs (ADOS-6.11.010). Build report retained.
7. Issue record created; superseded containers moved (ADOS-2.6.070).
```

The gate is binary. There is no partial issue (`ADOS-0.7.030`).

**Validation.** `V-8.10.050`: for every issue, all seven steps have evidence in the record.

### ADOS-8.10.060 — Gate thresholds by status ⚠

| Status | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| `S0` internal | — | — | — | — |
| `S1`/`S2` shared | 0 | ≤ 5, listed | — | — |
| `S3`/`S4` review | 0 | 0 | ≤ 10, listed | — |
| `A`/`B` authorised | 0 | 0 | 0 | listed |

**Validation.** `V-8.10.060`: defect counts by severity within the row for the declared status.

### ADOS-8.10.070 — Audit ⚠

**Decision.** The DSO shall audit a sample of issued containers each quarter: 5 % of containers or
20 containers, whichever is greater, selected by a recorded random procedure. The audit re-runs the
full metric set and reviews the check evidence. Findings feed the change procedure
(`ADOS-0.7.2`).

**Validation.** `V-8.10.070`: audit performed, sample recorded, findings recorded and actioned.

### ADOS-8.10.080 — Metric configuration control ⚠

**Decision.** Thresholds are set by this specification and by the practice overlay. They shall not be
changed per project to make a failing set pass. A project requiring a different threshold shall
record it in the Deviation Register with an approver and an expiry.

**Rationale.** A tunable threshold is not a threshold. Without this rule, every gate becomes
negotiable at the moment it is inconvenient, which is exactly when it matters.

**Validation.** `V-8.10.080`: project validation configuration diff against the standard = ∅ or fully
registered.

---

## 8.11 Metric summary table

| Metric | Name | Sub-metrics | Source | Primary gate |
|---|---|---|---|---|
| **M1** | Readability | 7 | IR + raster | S1 |
| **M2** | Consistency | 16 | IR | S2 |
| **M3** | Hierarchy | 4 | IR | S3 |
| **M4** | Information completeness | 18 | IR + model | S1 |
| **M5** | Visual balance | 9 | IR + raster | S3 |
| **M6** | Navigation | 15 | IR + human | S1 |
| **M7** | Print quality | 11 | raster | S1 |
| **M8** | Accessibility | 11 | raster + PDF | S1 |
| **M9** | Automation readiness | 12 | model + IR | S1 |

**Total: 103 sub-metrics**, all defined in `machine/ados-validation.yaml` with formulas, thresholds,
severities and gates.

---

## 8.12 Summary of Volume 8

1. Every `shall` rule has one deterministic validation; a rule without one is a recommendation.
2. Nine metrics, 103 sub-metrics, each objective, deterministic, sourced, thresholded, attributable
   and actionable.
3. Readability is measured with an instrument (OCR on a deterministically degraded render), not by
   opinion.
4. Consistency is measured by exact identity, because one deviation costs the whole set.
5. Completeness is measured against the document type's required content, and noise against it too.
6. Four severity classes with fixed gate thresholds by status; the gate is binary.
7. Thresholds are not tunable per project; deviations are registered, approved and expire.
8. The system measures itself: defect escape rate and RFI cause analysis feed rule admission.

---

*Continue to [Appendix](ADOS-APX-Appendix.md).*
