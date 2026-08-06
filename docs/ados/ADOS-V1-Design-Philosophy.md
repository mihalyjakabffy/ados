# Volume 1 — Design Philosophy

**ADOS 1.0 · Volume 1 · The derivation of every downstream value.**

Volume 1 explains **why**. Volumes 3–6 state **how**. No value appears in Volumes 3–6 that is
not derived here or in an external standard cited here.

Each derivation is presented in a fixed form:

> **Problem** — what fails without a rule.
> **Rationale** — the physical, perceptual, cognitive or procedural fact that constrains the
> answer.
> **Derivation** — the arithmetic from that fact to the value.
> **Consequences** — what else is now determined.
> **Trade-offs** — what is given up, and why that price is acceptable.

---

## 1.1 Method

### 1.1.1 Why derive rather than adopt

**Problem.** A standard assembled by collecting the current practice of admired offices
inherits their accidents. It cannot answer "why 0.35 mm?" and therefore cannot be extended,
automated, taught quickly, or defended when challenged. Worse, it cannot be *corrected*: with
no derivation, there is no way to tell a mistake from a convention.

**Rationale.** A rule set with stated derivations has three properties an assembled one lacks:

1. **Extensibility.** A new case (a new document type, a new medium, a new scale) can be
   resolved by re-running the derivation instead of guessing.
2. **Falsifiability.** If the underlying fact is wrong, the rule can be shown to be wrong.
3. **Compressibility.** Twenty derived values are one principle plus arithmetic; twenty
   adopted values are twenty things to memorise.

**Decision.** ADOS derives. Where an international standard already encodes the correct
derivation (ISO 216, ISO 128, ISO 3098), ADOS adopts the standard *and states the derivation
anyway*, so that the reasoning survives independently of the citation.

**Trade-offs.** Derivation produces values that occasionally differ from long-established
office habit. Where the difference is small and the habit is widespread, ADOS adopts the habit
and records that the derivation permits it (a *tolerance adoption*). Where the difference is
large, ADOS follows the derivation and states the conflict.

### 1.1.2 The six evidence classes

Repeated from the front matter for use in this volume:

| Class | Symbol | Basis | Example value |
|---|---|---|---|
| Physical | **P** | Reproduction physics, optics, materials | minimum line width 0.18 mm |
| Perceptual | **V** | Acuity, contrast sensitivity, discrimination | minimum cap height 2.5 mm |
| Cognitive | **C** | Working memory, search, error rates | ≤ 7 regions per sheet |
| Procedural | **R** | Actual conditions of use | fold-safe zone width |
| Interoperability | **I** | External system requirement | A-series sheet sizes |
| Arithmetic | **A** | Derived from another value | 10 mm grid module |

### 1.1.3 The derivation chain

Every quantity in ADOS traces to one of four **root facts**. This is the entire foundation:

```
ROOT FACT 1 (V)  Human foveal acuity: ~1 arcmin resolution; fluent reading of
                 technical text requires characters subtending ≥ 17 arcmin.

ROOT FACT 2 (C)  Working memory holds ~4 chunks; reliable categorical
                 discrimination on one visual channel is ~4–6 states.

ROOT FACT 3 (P)  Office reproduction (600 dpi laser, one to two generations of
                 copying, scanning) erodes stroke edges by 0.02–0.05 mm per
                 generation and collapses tones below ~10 % and above ~85 %.

ROOT FACT 4 (I)  ISO 216 paper scales by √2 between adjacent sizes; ISO 5455
                 scales, ISO 3098 lettering and ISO 128 line widths all follow
                 √2 or 1-2-5 progressions.
```

Everything else follows.

```
ROOT 1 ──► minimum cap height ──► type scale ──► line spacing ──► text block height
   │                                  │
   │                                  └──► minimum symbol size ──► marker diameters
   │
ROOT 3 ──► minimum line width ──► line width series ──► pen sets ──► hatch spacing
   │                                  │
   │                                  └──► tone ladder ──► fill assignments
   │
ROOT 2 ──► channel state limits ──► 3-tier line hierarchy, 5-tone ladder,
   │                                4-level sheet hierarchy, ≤7 sheet regions
   │
ROOT 4 ──► √2 modular scale ──► scale-invariant type and line series
                              ──► sheet sizes, margins, grid module
```

---

## 1.2 The human reader

### 1.2.1 Acuity and the minimum legible character

**Problem.** Text too small to resolve is worse than absent text: it occupies area, implies
information exists, and invites guessing.

**Rationale (V).** Normal corrected acuity (6/6, 20/20) resolves detail subtending 1 arcmin.
Character *recognition* requires more than detail resolution: a Latin character must subtend
roughly 10 arcmin at the absolute threshold and 16–20 arcmin for fluent, error-free reading
of unfamiliar strings (which is what dimension text and codes are). ADOS adopts **17 arcmin**
as the fluent-reading target.

**Derivation.** Character height *h* at viewing distance *d* subtending angle θ:

```
h = 2 · d · tan(θ / 2)      ≈ d · θ_rad   for small θ

θ = 17 arcmin = 17 / 60 deg = 0.2833° = 4.945 × 10⁻³ rad
```

| Use case | Viewing distance *d* | Derived *h* | ADOS value |
|---|---|---|---|
| Sheet on a site table, whole-sheet scan | 700 mm | 3.46 mm | 3.5 mm (view titles) |
| Sheet read at normal working distance | 500 mm | 2.47 mm | **2.5 mm (body minimum)** |
| Close reading, sheet held or leaned over | 350 mm | 1.73 mm | 1.8 mm (absolute floor) |
| Wall-mounted set, 1.5 m | 1500 mm | 7.42 mm | 7 mm (sheet number) |

These are the ISO 3098 lettering heights, re-derived. That agreement is evidence that the
derivation is sound rather than a coincidence of tradition.

**Consequences.**
- `ADOS-3.4.010` sets 2.5 mm as the minimum printed cap height for any text a user must read
  to act, and 1.8 mm as the absolute floor for secondary annotation on sheets of A1 or larger
  (where the reader leans in).
- Text below 1.8 mm printed is prohibited outright: it fails at every realistic distance and
  does not survive reproduction (ROOT 3).
- The type scale must therefore start at 1.8 and the second step must be 2.5 — a ratio of
  1.39, close to √2 = 1.414. This is the origin of the √2 type scale (§1.4).

**Trade-offs.** Enforcing 2.5 mm on a busy A1 plan reduces the number of annotations that fit.
This is the intended effect: `ADOS-1.7` shows that the density at which smaller text becomes
necessary is already past the density at which the sheet fails on search time. Small text is a
symptom of a sheet that should have been split, not a solution.

### 1.2.2 Contrast and tone discrimination

**Problem.** Tonal encodings (hatch fills, shaded zones, greyed background information)
collapse into each other after reproduction, converting a categorical distinction into noise.

**Rationale (V, P).** Lightness discrimination is approximately uniform in CIE L*. Under
optimal viewing, ΔL* ≈ 2 is detectable side by side. Under the adverse reference condition
(`ADOS-0.3.060`) — degraded reproduction, non-adjacent samples, 200 lux — reliable
*categorical* identification requires **ΔL* ≥ 15**. Reproduction (ROOT 3) additionally
collapses coverage below ~10 % and above ~85 % toward the extremes.

**Derivation.** Usable L* range after reproduction: approximately L* 10 to L* 100. With ΔL*
spacing of 18 (15 required + 20 % margin):

```
number of steps n = floor((100 − 10) / 18) + 1 = 6
```

giving the ADOS tone ladder:

| Token | L* target | Nominal ink coverage (600 dpi laser, 106 lpi) | Use |
|---|---|---|---|
| `T0` | 100 | 0 % | Paper / void |
| `T1` | 82 | 12 % | Background / existing to remain |
| `T2` | 64 | 26 % | Secondary fill |
| `T3` | 46 | 42 % | Primary fill |
| `T4` | 28 | 60 % | Emphasis fill |
| `T5` | 10 | 88 % | Solid poché |

**Consequences.**
- Exactly six tones are available (`ADOS-3.8.010`). A seventh is not "one more option"; it
  reduces the reliability of all the others by shrinking spacing.
- Adjacent tones may be used together only where the distinction is not
  meaning-critical; meaning-critical tone pairs shall be non-adjacent (ΔL* ≥ 36,
  `ADOS-3.8.030`).
- Text over tone: contrast ratio requirements in `ADOS-3.8.040` derive from the same table.

**Trade-offs.** Six tones is fewer than most CAD tools offer and fewer than designers want. The
alternative — more tones — produces sets that read correctly on the author's screen and fail
on the contractor's copy, with no warning at the point of failure.

### 1.2.3 Line width discrimination

**Problem.** Line hierarchy is the primary carrier of meaning in orthographic drawing
(`ADOS-0.3.030`). If adjacent weights are not reliably distinguishable, the drawing's core
encoding fails.

**Rationale (V, P).** Width discrimination follows Weber's law with a fraction of roughly
0.05–0.10 for side-by-side comparison of long straight lines under good conditions. But
drawing reading is not side-by-side comparison: it is *absolute identification of a category*
from a line seen in isolation, among other marks, on a degraded copy. Absolute identification
is far coarser. The literature on absolute judgement (ROOT 2) gives 4–6 reliably identifiable
categories on a single unidimensional channel, and requires a category spacing well above the
discrimination threshold.

**Derivation.** Two constraints:

```
(a) minimum width w_min  (from ROOT 3, §1.3.2)      = 0.18 mm
(b) adjacent semantic tiers separated by factor 2   (absolute identification margin)
```

Three semantic tiers therefore span 0.18 → 0.36 → 0.72, and with the ISO 128 series
(0.13, 0.18, 0.25, 0.35, 0.50, 0.70, 1.00, 1.40, 2.00 — ratio √2) the realisable triple is:

```
0.18  ·2→  0.35  ·2→  0.70
```

Every second member of a √2 series is a factor-2 series. This is why the ISO line width series
is √2: it supplies both a fine-grained series for edge cases and a clean factor-2 subset for
semantic tiers.

**Consequences.**
- The core ADOS pen set is **0.18 / 0.35 / 0.70** (`ADOS-4.1.020`), with 0.25 and 0.50
  available as *intra-tier* refinements that never carry a semantic distinction on their own,
  and 1.00 / 1.40 reserved for sheet-frame and section-cut-line graphics.
- At most **five** weights may appear on one sheet (`ADOS-4.1.030`), of which at most **three**
  carry semantic tiers.
- Because both the type scale and the width series are √2-based, reducing a sheet by one
  ISO size maps each width onto the next lower width and each text height onto the next lower
  height — the drawing degrades *coherently* rather than arbitrarily (§1.4.3).

**Trade-offs.** Three semantic tiers is a coarse instrument; some drawings genuinely have four
or five meaningful depth layers. ADOS resolves this by adding *line type* as a second channel
(`ADOS-4.1.050`) rather than adding weights, because line type is discriminable independently
of width and survives reproduction.

### 1.2.4 Working memory, search and the seven-region limit

**Problem.** A sheet the reader cannot decompose into a small number of parts must be searched
exhaustively, and exhaustive search on a dense sheet exceeds the time budget.

**Rationale (C).** Working memory capacity for unrelated chunks is approximately 4 ± 1. When
items are visually grouped and labelled, the reader holds *group identities* rather than items,
so the practical limit for top-level regions is higher — around 7 — but only if the grouping is
unambiguous (clear separation, consistent labelling).

Visual search for a labelled item among *N* distractors is serial and costs roughly
200–300 ms per item examined; expected examinations are ~*N*/2.

**Derivation.** Search budget within a sheet is 15 s of the 60 s search budget
(`ADOS-0.5.020`); the rest is consumed reaching the right sheet.

```
15 s / 0.25 s per item = 60 items examined
expected examinations = N/2  ⇒  N ≤ 120 items per undifferentiated search field
```

But if the reader can first select the correct region (one decision among ≤ 7) and then search
within it:

```
regions R ≤ 7,  items per region N_r
time = t_region_select + (N_r / 2) · 0.25 s ≤ 15 s
⇒ N_r ≤ ~110 with 1.5 s region selection
```

ADOS sets the operational limits conservatively at **≤ 7 top-level regions per sheet** and
**≤ 50 annotation objects per search region** (`ADOS-3.7.030`), which gives a factor-2 margin
against the derived ceiling to absorb adverse conditions, unfamiliarity and non-uniform label
salience.

**Consequences.**
- Sheet zoning (`ADOS-3.3`) defines the regions explicitly rather than leaving them emergent.
- Annotation density limits (`ADOS-3.7`) are per region, not per sheet.
- Legends are grouped, with ≤ 7 entries per group (`ADOS-4.9.030`).
- Hierarchy depth ≤ 4 (`ADOS-0.3.040`).

**Trade-offs.** Region limits force content off sheets and increase sheet count. Sheet count is
a production and printing cost; failed search is a construction cost. §0.1.2 gives the ratio.

### 1.2.5 Pre-attentive processing and what deserves it

**Problem.** Everything cannot be emphasised. If it is, nothing is.

**Rationale (V, C).** A small set of visual features is processed in parallel across the visual
field before attention is directed: strong differences in luminance, width, orientation,
curvature, and enclosure. Search for a target defined by one such feature is roughly
independent of the number of distractors. Search for a target defined by a *conjunction* of
features is serial.

**Derivation and decision.** Pre-attentive channels are scarce and shall be allocated to the
distinctions with the highest cost of being missed:

| Priority | Distinction | Channel allocated | Rule |
|---|---|---|---|
| 1 | Cut vs. not cut | Line weight (factor 2) | `ADOS-4.1.020` |
| 2 | Existing / new / demolished | Line type + tone | `ADOS-5.6.030` |
| 3 | Fire compartmentation | Line type + weight + (colour, redundant) | `ADOS-5.9.020` |
| 4 | Revision affected area | Enclosure (cloud) | `ADOS-2.6.050` |
| 5 | Grid and setting-out | Enclosure (bubble) + line type | `ADOS-4.4.020` |

**Consequences.** Anything not in this table is found by serial search and must therefore be
supported by labelling and grouping instead of emphasis.

**Trade-offs.** Restricting emphasis makes individual sheets look flatter than a designer would
choose. Flatness is the correct appearance for a sheet whose emphasis budget has not been
spent on decoration.

### 1.2.6 The cost of inconsistency, quantified

**Problem.** Local deviations are individually cheap and collectively expensive, which makes
them hard to argue against case by case.

**Rationale (C).** Readers form a template from the first few sheets. A deviating sheet
imposes: (a) the cost of noticing the deviation, if it is noticed; (b) the cost of rebuilding
the template; (c) a residual increase in checking behaviour on *all* subsequent sheets, because
the reader can no longer trust the template.

Cost (c) is the important one and it is why consistency is a set-level property. A single
deviating sheet in a set of 200 raises the per-sheet reading cost of the other 199.

**Derivation.** If template-based reading of a sheet costs *t* and template-less reading costs
*k·t* with *k* ≈ 1.3–1.6 for orientation tasks, then one deviation in a set of *n* sheets that
destroys template trust costs approximately:

```
Δcost ≈ (k − 1) · t · n
```

For *n* = 200, *k* = 1.4, *t* = 5 s, that is 400 s of pure orientation overhead per full read
of the set, per reader, before any error is made. A set is read by many parties many times.

**Consequences.** `ADOS-0.3.050`; the zero-tolerance framing of the consistency metric `M2`
(`ADOS-8.3`), where the threshold is exact identity, not a percentage.

**Trade-offs.** Rigidity. Some sheets would genuinely read better with a bespoke layout. ADOS
accepts a worse individual sheet for a better set, and provides the Deviation Register for the
rare case where the individual sheet's advantage is large and can be argued in writing.

---

## 1.3 The reproduction chain

### 1.3.1 What actually happens to a document

**Problem.** Documents are designed in a lossless environment and consumed after lossy
transformations that the author never sees.

**Rationale (P, R).** The realistic chain is:

```
model → vector view → PDF → (a) 600 dpi laser print at issue size
                          → (b) print reduced to A3
                          → (c) photocopy of (a) or (b)
                          → (d) photograph of (c) on a phone, sent by messaging app
                          → (e) print of (d)
```

Each stage loses. Stage (d) is now the dominant real-world consumption path for a site query
and is the harshest: perspective distortion, uneven illumination, JPEG artefacts at low
quality, and re-thresholding.

**Decision.** The **adverse reference condition** (`ADOS-0.3.060`) is defined as stage (c) —
two generations of monochrome reproduction at the smallest nominated issue size. Stage (d) is
not a design target (it cannot be, reliably) but the metrics of `ADOS-8.7` include a
photograph-robustness check for safety-critical documents.

### 1.3.2 Derivation of the minimum line width

**Rationale (P).** A 600 dpi device has a nominal addressable pitch of 25.4/600 = 0.0423 mm.
Consistent rendering of a line requires the line to be at least 3 device pixels wide; below
that, quantisation causes visible width variation along the line and drop-outs at shallow
angles.

```
w_device_min = 3 × 0.0423 mm = 0.127 mm ≈ 0.13 mm    (ISO 128 smallest width)
```

Each generation of monochrome copying erodes 0.02–0.05 mm from stroke width (toner scatter and
re-thresholding). Two generations, worst case:

```
w_issue_min = 0.13 + 2 × 0.025 (typical) = 0.18 mm   → ADOS floor, normal documents
w_issue_min = 0.13 + 2 × 0.05  (worst)   = 0.23 mm   → 0.25 mm, safety-critical documents
```

**Decision.** `ADOS-4.1.010`: minimum issued line width 0.18 mm; 0.25 mm for fire, escape and
structural setting-out information. 0.13 mm may be used only for screen-only deliverables.

**Consequences.** The thinnest usable weight is fixed, which fixes the whole pen set by the
factor-2 tiering of §1.2.3.

### 1.3.3 Derivation of minimum hatch spacing and minimum gap

**Rationale (P).** Two parallel lines merge visually when the white gap between them falls
below the reproduction threshold. Empirically the gap must exceed roughly 3× the erosion per
generation plus the device pitch:

```
gap_min = 2 × 0.025 (erosion, two generations, both edges) + 0.0423 (pitch) ≈ 0.09 mm
```

with a perceptual margin of 3× for reliable separation under 200 lux at 500 mm:

```
gap_min_adopted = 0.30 mm
```

For a hatch of line width *w* and pitch *p*: `p ≥ w + 0.30 mm`. With *w* = 0.18 mm the minimum
hatch pitch is **0.5 mm printed** (`ADOS-4.10.020`).

**Consequences.**
- Hatch patterns are specified in *printed* pitch, not model pitch, and therefore depend on
  drawing scale. A hatch defined in model units is scale-dependent and will fail at some
  scale; ADOS requires scale-aware hatch definitions (`ADOS-6.7.040`).
- The number of visually distinct hatch patterns available is limited (`ADOS-4.10.030`
  permits 8), for the same absolute-identification reason as tones.

### 1.3.4 Derivation of the text clear zone

**Rationale (P, V).** Text placed on or near linework loses legibility through two mechanisms:
crowding (flanking marks impair character identification) and merging (ink spread closes the
gap). Crowding effects extend to roughly 0.5× character height in the fovea.

**Derivation.**

```
clear_zone = max(0.5 × cap_height, 1.0 mm)
```

At the 2.5 mm minimum cap height this is 1.25 mm of clear space around every text object.

**Decision.** `ADOS-3.4.080`: every text object shall have a mask or clear zone of
`max(0.5 × cap height, 1.0 mm)` on all sides, free of any other mark. This is why text masking
("opaque background") is mandatory rather than optional in ADOS.

### 1.3.5 Reduction and the smallest nominated size

**Rationale (R, I).** Sets issued at A1 are routinely printed at A3 for meetings and site
folders. A3 is A1 reduced by a factor of 2 in linear dimension (two √2 steps).

**Derivation.** A drawing issued at A1 and printed at A3 has all printed lengths halved:

```
2.5 mm text at A1  →  1.25 mm at A3   (below the 1.8 mm absolute floor: FAILS)
0.18 mm line at A1 →  0.09 mm at A3   (below 0.13 mm device floor: FAILS)
```

**Decision.** `ADOS-3.2.040`: a document set shall declare a **smallest nominated issue size**,
and all minimum-size rules apply *at that size*. Two conforming strategies:

1. **A1-only issue** (nominated size A1): minima as derived; the set may not be issued at A3,
   and A3 prints shall be watermarked `REDUCED — DO NOT SCALE — NOT FOR CONSTRUCTION`.
2. **A1/A3 dual issue** (nominated size A3): text minimum becomes 5 mm at A1 (so that it is
   2.5 mm at A3) and line minimum becomes 0.35 mm at A1 (so that it is 0.18 mm at A3).

Strategy 2 costs roughly 40 % of the annotation capacity of a sheet. That cost is the true
price of dual-size issue and shall be decided explicitly at project setup, not discovered at
issue.

**Consequences.** This single rule resolves the most common and least-discussed documentation
failure in practice: sets designed for A1 and consumed at A3.

---

## 1.4 The modular scale

### 1.4.1 Why a modular scale at all

**Problem.** Arbitrary sizes produce three failures: values too close together to read as
distinct (wasted distinction), values inconsistent between documents (broken template), and
values that do not survive scaling.

**Rationale (C, A).** A geometric progression provides constant *ratio* between adjacent steps,
and human discrimination of size is ratio-based (Weber). Constant ratio therefore produces
constant perceived difference across the whole range — the only progression that does.

### 1.4.2 Why the ratio is √2

**Rationale (I, A).** Four independent requirements converge on √2:

1. **ISO 216 compatibility.** A-series sheets scale by √2. A type or line series with ratio √2
   maps exactly onto itself under one sheet-size change.
2. **Two-step factor of 2.** Every second step is a factor of 2, which is the ratio required
   for absolute identification of semantic tiers (§1.2.3). A series with a single ratio serving
   both fine gradation and semantic tiering is strictly better than two series.
3. **Existing standards.** ISO 3098 lettering (1.8, 2.5, 3.5, 5, 7, 10, 14, 20) and ISO 128
   line widths (0.13 … 2.00) are already √2 series. Adopting √2 aligns ADOS with both at no
   cost.
4. **Step count.** Over the useful text range 1.8–20 mm, √2 gives 8 steps — enough for a full
   hierarchy, few enough to memorise.

**Rejected alternatives.**

| Ratio | Why rejected |
|---|---|
| 1.2 (minor third) | Too fine: adjacent steps not reliably distinguishable under adverse conditions; 14 steps over the range |
| 1.25 / 1.333 | Same problem; no relation to sheet scaling |
| 1.5 | No two-step factor-of-2 subset; breaks ISO alignment |
| 1.618 (golden) | No functional justification whatsoever; only 5 steps over the range; misaligned with sheet scaling. Its use in documentation systems is decorative and is prohibited by `ADOS-0.3.010`. |
| 2.0 | Too coarse: only 4 steps; forces large jumps that waste sheet area |

**Derivation.** The ADOS modular scale, rounded to ISO 3098 preferred values:

```
1.8, 2.5, 3.5, 5, 7, 10, 14, 20   (mm, printed)
ratio: 1.389, 1.400, 1.429, 1.400, 1.429, 1.400, 1.429   (mean 1.411 ≈ √2)
```

The rounding is what makes the series memorable; the deviation from exact √2 (max 1.8 %) is far
below the discrimination threshold and therefore free.

### 1.4.3 Scale invariance: the key property

**Consequence.** Because sheet sizes, text heights and line widths all step by √2:

```
A1 → A2 reduction (× 1/√2):
   text 5.0 mm  → 3.5 mm   (still a valid series member)
   text 3.5 mm  → 2.5 mm   (still valid)
   line 0.70 mm → 0.50 mm  (still valid)
   line 0.35 mm → 0.25 mm  (still valid)
```

A reduced drawing remains a conforming drawing at a lower tier, with the hierarchy intact and
the ratios preserved. No other ratio has this property with the A series.

**Trade-offs.** The √2 series is not visually "designed"; the numbers are inherited and the
increments feel large. This is the correct trade: predictability and scale invariance beat
fine-tuned appearance.

---

## 1.5 The drawing scale ladder

### 1.5.1 Why a fixed ladder

**Problem.** Arbitrary scales (1:75, 1:30, 1:150) produce: measurement error when read with a
standard scale rule; mental-arithmetic error when converting; and inconsistent detail
resolution across a set.

**Rationale (R, C).** Three constraints:

1. **Instrument availability.** Physical and digital scale rules carry 1:1, 1:2, 1:5, 1:10,
   1:20, 1:50, 1:100, 1:200, 1:500, 1:1000, 1:1250, 1:2500. A drawing at 1:75 cannot be
   measured directly.
2. **Mental conversion.** Dividing by 1, 2, 5 and powers of 10 is exact and single-step in
   decimal. Dividing by 3, 7 or 75 is not.
3. **Discrimination between adjacent scales.** Adjacent steps in a 1-2-5 ladder differ by ×2 or
   ×2.5 in linear terms, ×4 to ×6.25 in area — a clearly perceptible change of information
   level. A ×1.5 step is not perceptibly a different level and adds a scale to the set for no
   informational gain.

**Derivation.** The 1-2-5 preferred-number ladder, restricted to values with instrument support:

```
1:1  1:2  1:5  1:10  1:20  1:50  1:100  1:200  1:500  1:1000  1:2000  1:5000
```

**Decision.** `ADOS-4.2.010`: only ladder values may be used. `ADOS-4.2.020` maps each drawing
class to its scale, and `ADOS-4.2.040` permits exactly one scale per drawing class per project.

### 1.5.2 Scale as an information-level declaration

**Rationale (C).** Scale is not a zoom factor; it is a statement about *which decisions this
drawing carries*. A 1:100 plan that shows 1:20 content is not "more informative": it exceeds
its density budget, and the 1:20 content will be missed because readers do not look for
assembly information on a location drawing.

**Derivation.** Each scale has a **resolvable feature size**: the smallest real-world dimension
that produces a printed mark above the reproduction floor plus a discriminable gap
(§1.3.3, 0.5 mm printed as the minimum resolvable feature *pair*):

| Scale | 0.5 mm printed = | Smallest meaningfully drawn element | Content level |
|---|---|---|---|
| 1:1000 | 500 mm | building masses | context |
| 1:500 | 250 mm | building footprint, roads | site |
| 1:200 | 100 mm | wall thickness (just) | whole-building location |
| 1:100 | 50 mm | wall layers (marginal) | location, general arrangement |
| 1:50 | 25 mm | wall layers | enlarged GA, room layouts |
| 1:20 | 10 mm | board thickness, cavity | assembly |
| 1:10 | 5 mm | membrane, sheet layers | assembly detail |
| 1:5 | 2.5 mm | seals, tolerances | junction detail |
| 1:2 | 1 mm | fixings, profiles | component detail |
| 1:1 | 0.5 mm | tolerance bands | full-size detail |

**Decision.** `ADOS-4.2.030`: a drawing shall not depict an element whose real dimension is
below the resolvable feature size for its scale; such elements shall be represented
symbolically or deferred to a larger-scale drawing with a callout.

**Consequences.** This rule, applied strictly, eliminates the most common density failure:
detail migrating up into location drawings. It is directly checkable in a BIM environment via
level-of-detail settings (`ADOS-6.7.030`).

**Trade-offs.** Strictness forces more callouts and more detail sheets. The alternative is
drawings that appear to answer assembly questions but cannot be measured or trusted.

---

## 1.6 Why monochrome-first

**Problem.** Colour is the most seductive and least reliable encoding channel in documentation.

**Rationale (P, V, R).** Four independent failures:

1. **Reproduction.** Site printing is monochrome. Colour becomes tone, and hues of similar
   luminance become the *same* tone. Red (L* ≈ 53) and green (L* ≈ 46) are 7 ΔL* apart —
   indistinguishable after conversion (§1.2.2 requires ≥ 15).
2. **Vision.** ~8 % of male readers cannot reliably distinguish the most commonly used pair
   (red/green).
3. **Cost and behaviour.** Colour printing at large format is slow and expensive, so it does
   not happen, so colour-encoded documents are consumed in greyscale by default.
4. **Semantics.** Colour has no intrinsic ordering. Line weight does (thicker = nearer/more
   important). An ordered meaning encoded in an unordered channel must be memorised.

**Decision.** `ADOS-3.10.010`: documentation shall be designed monochrome-first. Colour may be
added only as **redundant** encoding, on top of a distinction that is already fully carried by
weight, type, tone, symbol or text.

**Permitted colour uses** (`ADOS-3.10.020`), all redundant:
- discipline identification on coordination views (screen use);
- status marking on non-issued working prints;
- clash and comment markup, which is transient and never issued;
- fire strategy plans, where colour is a statutory expectation in some jurisdictions and is
  *added to* a fully monochrome-legible base;
- accessibility and wayfinding studies, where colour is the subject matter.

**Trade-offs.** Monochrome-first sets look austere and take more effort to structure, because
distinctions that colour would carry cheaply must be carried by weight and type, which are
scarcer. That effort is the price of a document that works everywhere.

---

## 1.7 Information density

### 1.7.1 The density trade-off

**Problem.** Density has two opposed costs. Too dense: search time and error rise, marks merge.
Too sparse: the reader must consult more sheets, and cross-sheet navigation is where context is
lost.

**Rationale (C, R).** Cross-sheet navigation costs far more than intra-sheet search: it
requires reorienting (5 s), locating the referenced sheet (10–60 s in a paper set), and
rebuilding context. Empirically the break-even is high — a sheet should be filled substantially
before content is moved off it.

**Derivation.** Three independent density measures, each with a floor and a ceiling:

**(a) Fill ratio** — proportion of the drawing area occupied by the bounding boxes of drawn
content:

```
0.40 ≤ fill_ratio ≤ 0.85
```

Below 0.40, the sheet does not justify its own navigation cost. Above 0.85, margins collapse
and views collide with the frame and title block.

**(b) Local ink coverage** — mean ink coverage within any 20 × 20 mm window of the drawing
area:

```
coverage ≤ 0.25
```

Above ~25 %, adjacent strokes merge under two-generation reproduction (§1.3.3) and the drawing
becomes a grey field. Poché and solid fills are excluded from this measure and counted
separately.

**(c) Annotation object count** — text objects, dimensions, tags, leaders and symbols per
search region:

```
N_r ≤ 50   (derived in §1.2.4)
```

**Decision.** `ADOS-3.7.010` to `ADOS-3.7.030` adopt these three limits. All three are
machine-measurable from a vector PDF or from the authoring model.

**Consequences.** When a sheet exceeds a ceiling, the resolution order is fixed
(`ADOS-3.7.040`): (1) move content to the correct hierarchy level; (2) split the view; (3)
split the sheet; (4) *only then* consider a larger sheet size. Reducing text size is not on the
list and is prohibited.

**Trade-offs.** Fill-ratio floors can force content onto fewer sheets than a designer would
choose for clarity of composition. This is intended: composition is not a goal of this system;
retrieval is.

### 1.7.2 White space is structural, not decorative

**Rationale (V, C).** Separation is the primary grouping cue in vision — stronger than
similarity, enclosure or common region for spatially arranged content. White space is
therefore an encoding channel, not leftover area.

**Derivation.** For grouping to be unambiguous, the gap *between* groups must exceed the
largest gap *within* a group by a clear margin. Adopting a factor of 2 (the same
absolute-identification margin as §1.2.3):

```
gap_between_groups ≥ 2 × gap_within_group
```

**Decision.** `ADOS-3.5.020`. This single ratio governs: spacing between views on a sheet,
between annotation clusters, between schedule column groups, and between paragraph blocks in
specifications. One rule, applied at every level of scale.

---

## 1.8 Why documents are derived, not drawn

**Problem.** Hand-composed documentation cannot satisfy `ADOS-0.3.020` (one fact, one place) at
scale, because there is no mechanism preventing restatement.

**Rationale (I, R, A).** In a model-derived workflow:

- geometry appears once and is projected into every view;
- properties appear once and are projected into every schedule and tag;
- appearance is a *function* of data, so it is consistent by construction rather than by
  discipline;
- change propagates automatically, and the residual failure mode is a *stale view*, which is
  detectable, rather than a *divergent value*, which is not.

**Trade-offs.** Derivation imposes real costs, which ADOS acknowledges rather than hides:

| Cost | Mitigation in ADOS |
|---|---|
| Model setup effort front-loads the programme | Volume 6 templates; setup is once per practice, not once per project |
| Tool limitations distort output | Volume 6 isolates tool overlays; core rules never depend on tool behaviour |
| Over-modelling: modelling things that do not need to be documented | `ADOS-6.3.030` level-of-information-need table binds modelling effort to document need |
| Detached / overridden views drift silently | `ADOS-6.7.050` prohibits manual override of derived values; `ADOS-8.4.060` detects them |
| Small projects pay disproportionate setup cost | Class C conformance |

**Decision.** `ADOS-6.1.010`: geometry and component property information in issued
documentation shall be derived from the project model. Manually drawn 2-D content is permitted
only for: standard details not project-specific, diagrams whose subject is not building
geometry, and survey-only content pending model integration — each of which is enumerated in
`ADOS-6.1.020`.

---

## 1.9 The trade-off register

*Normative.* Every documentation system embodies unavoidable tensions. Hiding them produces
inconsistent decisions in the field. ADOS states them, resolves each explicitly, and requires
the resolution to be applied uniformly.

### ADOS-1.9.010 — Trade-off resolution table ⚠

**Purpose.** Ensure the same tension is resolved the same way by every author.

**Decision.** The following resolutions are normative. Where a project needs a different
resolution, it shall be recorded in the Deviation Register at project setup, not decided per
sheet.

| # | Tension | Resolution | Rule |
|---|---|---|---|
| T1 | Density vs. sheet count | Fill 0.40–0.85; split rather than shrink | `ADOS-3.7` |
| T2 | Consistency vs. best local layout | Consistency wins; deviation requires registration | `ADOS-0.3.050` |
| T3 | Single source vs. reader convenience | Single source wins; convenience is served by machine-generated redundancy only | `ADOS-0.3.020` |
| T4 | Completeness vs. currency | Currency wins: issue accurate partial information with explicit exclusions rather than complete stale information | `ADOS-0.3.090`, `ADOS-2.6` |
| T5 | Precision vs. buildability | State the tolerance, not a false precision; dimensions carry provenance | `ADOS-4.5.070`, `ADOS-4.5.090` |
| T6 | Automation vs. expressiveness | Automation wins for issued technical documents; expressive freedom is confined to presentation documents (`ADOS-5.28`) | `ADOS-0.3.080` |
| T7 | Model fidelity vs. drawing legibility | Legibility wins: the drawing is a communication artefact, not a model dump; use representation overrides, never geometry edits | `ADOS-6.7.020` |
| T8 | Standard detail reuse vs. project specificity | Reuse with mandatory verification and project-specific marking; an unverified standard detail is a defect | `ADOS-5.16.040` |
| T9 | Speed of issue vs. QA gate | Gate wins; there is no partial issue | `ADOS-0.7.030` |
| T10 | Practice identity vs. neutral clarity | Clarity wins; identity is confined to the identity block | `ADOS-0.3.010` Ex. 1 |
| T11 | Paper set vs. digital set | Design for paper (the harder constraint), enhance for digital (hyperlinks, layers, search) | `ADOS-6.11` |
| T12 | Detail quantity vs. coordination effort | Fewer, verified, cross-referenced details beat many unverified ones; `M4` counts *answered questions*, not details | `ADOS-8.4` |

**Validation.** `V-1.9.010`: the project setup record states the resolution adopted for each of
T1–T12, or cites this table by reference.

**Automation notes.** These resolutions are encoded as the solver's objective weighting in
`ADOS-7.5.040`; a generator shall not expose them as user-tunable parameters at sheet level.

---

## 1.10 Rejected approaches

*Informative but binding by reference:* the following approaches were considered and rejected.
Rules elsewhere prohibit them; this section records why, so that they are not re-proposed.

### 1.10.1 Colour as primary encoding
Rejected: §1.6. Fails reproduction, vision, cost and semantics.

### 1.10.2 Free composition (no grid)
Rejected: eliminates layout invariance (`ADOS-0.3.050`), prevents automated placement
(`ADOS-0.3.080`), and makes fill-ratio and region metrics undefinable. Composition quality
gained is not measurable; navigation cost incurred is.

### 1.10.3 Typeface as an expressive channel
Rejected: typeface variation is a weak channel (`ADOS-0.3.030`), does not survive font
substitution in PDF workflows, and consumes a distinction budget better spent on weight. ADOS
permits exactly two typefaces (`ADOS-3.4.020`): one for drawings and one for prose documents,
with a defined reason for each.

### 1.10.4 Per-project documentation standards
Rejected: destroys the transferability of reader learning across projects, prevents template
investment, and multiplies QA configuration. Project-specific requirements are handled as
overlays (`ADOS-2.7`), never as forks.

### 1.10.5 Dual metric/imperial dimensioning throughout
Rejected as a default: doubles annotation object count, exceeding density budgets (§1.7), and
introduces rounding contradictions. Permitted only where contractually required, and then only
on setting-out drawings, with a stated primary unit (`ADOS-4.5.010`).

### 1.10.6 "Design intent" drawings without dimensional commitment
Rejected: violates `ADOS-0.4.030` (defensive obscurity). Where dimensions are genuinely open,
the correct instrument is a stated tolerance or a stated resolution mechanism, not omission.

### 1.10.7 Sheet layouts optimised per sheet by a designer
Rejected: §1.2.6 quantifies the set-level cost. Optimisation is applied at template level,
where it benefits every sheet, not at sheet level, where it harms the set.

### 1.10.8 Aesthetic hand-drawn conventions in technical documents
Rejected: sketch line quality reduces measurement confidence, defeats automated validation, and
mixes the representational registers of exploration and instruction. Sketch conventions belong
to design-stage documents (`ADOS-5.27`), which are explicitly marked as non-constructional.

---

## 1.11 How to extend the system correctly

**ADOS-1.11.010 — Extension procedure.** A new convention shall be introduced only by the
following procedure:

1. **State the communication failure** the convention prevents, with an observed instance.
2. **Identify the channel** (`ADOS-0.3.030`) and check that its state budget (§1.2) is not
   exceeded.
3. **Derive the value** from a root fact (§1.1.3) or from an existing derived value.
4. **Write the validation** before writing the rule. If no deterministic check exists, publish
   as a recommendation.
5. **Check the trade-off register** (§1.9) for an existing resolution that governs.
6. **Allocate a rule ID** and register dependencies in `machine/ados-rules.yaml`.
7. **Add the anti-pattern** it replaces to `ADOS-A.7`.

**Validation.** `V-1.11.010`: every rule in the registry has non-empty `principle_refs`,
`evidence_class`, and `validation.check_id`.

---

*Continue to [Volume 2 — Information Architecture](ADOS-V2-Information-Architecture.md).*
