# Volume 4 — Drawing Language

**ADOS 1.0 · Volume 4 · The representation of building information in orthographic drawing.**

Volume 3 governs marks that describe the sheet. Volume 4 governs marks that describe the
building. Every value here derives from Volume 1; every rule states its derivation.

---

## 4.1 Line hierarchy

### 4.1.1 The central encoding of orthographic drawing

An orthographic drawing is a projection of three-dimensional information onto a plane. The
projection destroys depth. Line weight restores it.

This is the single most important encoding in architectural documentation, and it is the reason
line weight is allocated the second-strongest channel (`ADOS-3.1.010`). A drawing whose line
hierarchy is wrong is not a drawing with a cosmetic problem; it is a drawing that has lost its
third dimension.

### ADOS-4.1.010 — Minimum line width ⚠

**Purpose.** Guarantee that every line survives the reproduction chain.

**Background.** §1.3.2: a 600 dpi device requires 3 pixels (0.13 mm) for consistent rendering;
two generations of monochrome copying erode 0.02–0.05 mm.

**Problem.** Fine linework specified on screen disappears on the copy that reaches site. The
information is not degraded — it is absent, with no indication that anything is missing.

**Decision.** At the smallest nominated issue size, no printed line shall be narrower than
**0.18 mm**. Lines carrying fire, escape or setting-out information shall be no narrower than
**0.25 mm**. Hairline, "0", "by device" and "thinnest available" widths shall not be used.

**Implementation.** Where the nominated size is smaller than the authored size, the authored width
is the minimum divided by the reduction factor (A1 authored, A3 nominated ⇒ 0.35 mm minimum at
A1).

**Exceptions.**
1. Screen-only deliverables may use 0.13 mm.

**Validation.** `V-4.1.010`: minimum stroke width in the rendered PDF at nominated size ≥ 0.18 mm;
count of zero-width or device-dependent strokes = 0.

**Common mistakes.** A CAD layer set to "defpoints" or width 0; imported consultant drawings
retaining their own width table; a plot style table that maps colour to width being replaced by
direct widths halfway through a set.

**Automation notes.** The renderer shall resolve all widths to absolute values at publication and
shall fail on any width below the floor rather than clamping silently.

### ADOS-4.1.020 — The three semantic tiers ⚠

**Purpose.** Restore depth information destroyed by projection, using the minimum number of
reliably distinguishable states.

**Background.** §1.2.3: absolute identification of line width requires a factor-2 separation
between adjacent semantic categories; the floor is 0.18 mm; the ISO 128 √2 series supplies
0.18 / 0.35 / 0.70 as the factor-2 subset.

**Problem.** Practices use five to nine weights whose meanings overlap, so readers cannot infer
depth and must read the geometry instead — which is slower and frequently wrong.

**Decision.** Three semantic tiers shall be used, and line weight shall be a **monotonic function
of proximity to the observer**:

| Tier | Width | Meaning | Applies to |
|---|---|---|---|
| **W3** | 0.70 mm | Cut | Any element intersected by the cut plane of the view |
| **W2** | 0.35 mm | Seen | Element surfaces and edges in front of the cut plane, visible |
| **W1** | 0.18 mm | Beyond / reference / hidden | Elements behind the cut plane, above the cut plane, hidden, or non-building reference geometry |

Intra-tier refinement widths **0.25 mm** and **0.50 mm** may be used to distinguish elements
*within* a tier (for example, a secondary visible edge within W2), but shall never distinguish
one tier from another.

Widths **1.00 mm** and **1.40 mm** are reserved for the sheet frame, section cut lines
(`ADOS-4.7.030`) and match lines, which are sheet apparatus rather than building content.

**Implementation.** In a model-derived workflow the tier is computed, not assigned: an element's
tier is a function of its relationship to the view's cut plane and view range. See
`ADOS-6.7.010`.

**Exceptions.**
1. At scales of 1:200 and smaller, W3 and W2 may be merged into a single 0.35 mm weight where the
   cut element's thickness is below the resolvable feature size (`ADOS-4.2.030`) — the distinction
   cannot be perceived and the heavier weight closes the element.
2. Presentation drawings (`ADOS-5.28`) may use additional weights, provided they are not issued as
   technical documentation.

**Validation.** `V-4.1.020`: for every drawn element, `tier(element) = f(depth relative to cut
plane)`; monotonicity violations = 0. Distinct widths per sheet ≤ 5 (`ADOS-4.1.030`).

**Examples.** *Conforming:* a plan where the cut walls are 0.70, the visible floor pattern and
furniture 0.35, and the ceiling grid and elements above 0.18 dashed. *Non-conforming:* a plan
where furniture is drawn heavier than walls because it was imported from a supplier's file.

**Common mistakes.** Weight assigned by object category (all doors 0.25) rather than by depth;
heavy weights used for emphasis of a design feature; a "poché outline" drawn heavier than the
cut it outlines.

**Automation notes.** Emit tier as an explicit attribute in the intermediate representation
(`ADOS-7.3.020`) so that the validator can check monotonicity without re-deriving geometry.

### ADOS-4.1.030 — Weight count per sheet

**Decision.** At most five distinct line widths shall appear within the drawing area of one
sheet, of which at most three carry semantic tiers.

**Rationale.** ROOT 2 (absolute identification saturates at 4–6 states).

**Validation.** `V-4.1.030`: distinct widths within `Z-DRAW` ≤ 5.

### ADOS-4.1.040 — Weight and scale

**Decision.** Line widths are printed widths and shall not vary with drawing scale. The same
element drawn at 1:100 and at 1:20 carries the same tier and therefore the same width.

**Rationale.** The tier encodes depth, not size. Scaling widths with the drawing would make the
encoding scale-dependent and destroy the reader's calibration between sheets.

**Consequence.** Because widths are constant and geometry is not, the *ratio* of line width to
element size changes with scale. At 1:200 a 100 mm partition is 0.5 mm wide on paper and a 0.70 mm
cut line would over-fill it — which is why `ADOS-4.1.020` Exception 1 exists.

**Validation.** `V-4.1.040`: width of a given tier is constant across all views of all scales.

### ADOS-4.1.050 — Line types ⚠

**Decision.** Four line types shall be used, and only these:

| Type | Pattern (printed) | Meaning |
|---|---|---|
| **L-CONT** | continuous | Visible edge; cut edge |
| **L-DASH** | dash 4.0 mm, gap 2.0 mm | Hidden, or above the cut plane |
| **L-DOT** | dot 0.5 mm, gap 1.5 mm | Below the cut plane (below-slab, underground, drainage) |
| **L-CENT** | long dash 12.0 mm, gap 2.0 mm, dot 0.5 mm, gap 2.0 mm | Centre line, grid line, axis of symmetry |

Additional categorical distinctions (fire compartment lines, zone boundaries, contract boundaries)
shall be formed by combining a line type with a tier and a legend entry, not by inventing new
patterns.

**Rationale.** §1.2.3 applies to pattern identification as it does to width: four patterns are
reliably identifiable; more are not, particularly at short line lengths where only one or two
period repetitions are visible.

Dash geometry is stated in *printed* millimetres so that the pattern is identical at every scale.
The 4.0/2.0 mm dash gives at least two full periods on a 12 mm line — the shortest line on which a
pattern needs to be identified.

**Exceptions.**
1. Jurisdiction overlays may add up to two statutory patterns (for example a mandated fire line),
   which shall be added to the encoding table and the legend.

**Validation.** `V-4.1.050`: distinct dash patterns in the set ≤ 4 (+ declared overlay patterns);
pattern geometry matches the table within ±5 %; every line shorter than one pattern period is
drawn continuous with a legend note (`ADOS-4.1.060`).

**Common mistakes.** Dash patterns defined in model units, so that the pattern is invisible at
1:200 and enormous at 1:5; twelve custom line types inherited from a template.

### ADOS-4.1.060 — Short line degeneracy

**Decision.** A patterned line shorter than 1.5 pattern periods shall be drawn with at least one
complete visible segment at each end, or drawn continuous and disambiguated by an adjacent tag.

**Rationale (P, V).** A dashed line 5 mm long may render as a single dash or as nothing, depending
on phase. The reader cannot distinguish it from a continuous line, and the encoding fails silently.

**Validation.** `V-4.1.060`: for every patterned line, `length ≥ 1.5 × period` or phase-locked
endpoints are present.

### ADOS-4.1.070 — Line joins and endpoints

**Decision.** Line joins shall be mitred; endpoints shall be butt-capped except for terminators and
leader tails, which are round-capped. Overshoot at corners shall be 0.

**Rationale (P).** Round caps add half a line width at each end, which at W3 is 0.35 mm — a visible
overshoot at a corner and a change in apparent dimension.

**Validation.** `V-4.1.070`: rendered corner geometry shows no overshoot > 0.1 mm.

---

## 4.2 Scales

### ADOS-4.2.010 — Permitted scales ⚠

**Decision.** Only the following scales shall be used:

```
1:1  1:2  1:5  1:10  1:20  1:50  1:100  1:200  1:500  1:1000  1:2000  1:5000
```

**Rationale.** §1.5.1: instrument availability, exact mental conversion, and perceptible steps.

**Exceptions.**
1. `1:1250` and `1:2500` where a national mapping product is at those scales (class **I**).

**Validation.** `V-4.2.010`: every view's scale is a permitted value.

**Common mistakes.** 1:75 to make a plan fit — the correct action is `ADOS-3.7.040`; "not to
scale" views that are in fact measurable and will be measured.

### ADOS-4.2.020 — Scale by drawing class ⚠

**Decision.** Each drawing class shall use the scale in the following table. A project may select
the alternative where the building size requires it, but shall then use that scale for the whole
class (`ADOS-4.2.040`).

| Drawing class | Default | Alternative | Content level |
|---|---|---|---|
| Site location plan | 1:1000 | 1:2000, 1:500 | L1 |
| Site plan | 1:500 | 1:200 | L1 |
| General arrangement plan | 1:100 | 1:200 (large buildings), 1:50 (small) | L2 |
| Roof plan | 1:100 | 1:200 | L2 |
| Reflected ceiling plan | 1:100 | 1:50 | L2 |
| Elevations | 1:100 | 1:200, 1:50 | L2 |
| Sections | 1:100 | 1:50 | L2 |
| Enlarged plans, cores, sanitary | 1:50 | 1:20 | L3 |
| Interior elevations | 1:50 | 1:20 | L3 |
| Wall / floor / roof types | 1:20 | 1:10 | L4 |
| Typical junction details | 1:5 | 1:10 | L4 |
| Component details | 1:2 | 1:5, 1:1 | L5 |
| Setting-out plan | 1:100 | 1:200 | L2 |
| Fire and access strategy | 1:200 | 1:100 | L2 overlay |

**Validation.** `V-4.2.020`: every view's scale matches its class row.

### ADOS-4.2.030 — Resolvable feature size ⚠

**Purpose.** Prevent content migrating to the wrong level (`ADOS-2.3.010`).

**Background.** §1.3.3: the smallest resolvable *pair* of marks requires a 0.5 mm printed gap plus
the two line widths; the smallest resolvable *feature* is therefore ~0.5 mm printed.

**Decision.** A view shall not attempt to depict, as distinct geometry, any element whose smallest
real-world dimension is below `0.5 mm × scale_denominator`.

| Scale | Resolvable real dimension |
|---|---|
| 1:1000 | 500 mm |
| 1:500 | 250 mm |
| 1:200 | 100 mm |
| 1:100 | 50 mm |
| 1:50 | 25 mm |
| 1:20 | 10 mm |
| 1:10 | 5 mm |
| 1:5 | 2.5 mm |
| 1:2 | 1 mm |
| 1:1 | 0.5 mm |

Elements below the threshold shall be represented symbolically, omitted with an exclusion note, or
deferred to a larger-scale view with a callout.

**Exceptions.**
1. Symbolic representation at any scale (a door leaf line, a drainage run) is permitted and is not
   subject to this rule, because it is not claiming to depict geometry.

**Validation.** `V-4.2.030`: for every view, the minimum drawn feature dimension ≥ threshold; count
of sub-threshold geometry = 0.

**Examples.** *Non-conforming:* a 12 mm plasterboard layer hatched separately at 1:100 (needs
50 mm); a 3 mm sealant joint drawn at 1:20 (needs 10 mm). *Conforming:* the same at 1:5.

**Automation notes.** This is enforceable directly by the model's level-of-detail setting per view
(`ADOS-6.7.030`); the validator checks the rendered geometry independently.

### ADOS-4.2.040 — One scale per class per project ⚠

**Decision.** Within a project, all views of a given drawing class shall use the same scale.

**Rationale.** §1.2.6: the reader calibrates size perception from the first drawings of a class and
applies it to the rest. A class with mixed scales forces per-view recalibration, and comparisons
between drawings of the class become invalid.

**Exceptions.**
1. A single view whose subject does not fit, provided the scale is stated at ≥ 1.4× the surrounding
   text height adjacent to the view title and the deviation is registered.

**Validation.** `V-4.2.040`: `|distinct scales per class| = 1` unless a registered deviation exists.

### ADOS-4.2.050 — Scale bar

**Decision.** Every sheet containing a scaled view shall carry a graphic scale bar per distinct
scale, in the drawing area adjacent to the view or in the notes zone, with divisions at round
real-world intervals and a labelled zero.

**Rationale.** `ADOS-3.9.040`.

**Validation.** `V-4.2.050`: scale bar count = distinct scale count on the sheet.

### ADOS-4.2.060 — Not-to-scale views

**Decision.** Diagrams that are not to scale shall be labelled `NTS` adjacent to the view title, at
the view title's size, and shall not carry dimensions that could be scaled. A view labelled `NTS`
shall not depict measurable building geometry.

**Rationale.** `ADOS-0.4.030`: an unlabelled non-scaled view will be scaled.

**Validation.** `V-4.2.060`: `NTS` views carry no dimension objects; `NTS` label present.

---

## 4.3 Projection and orientation

### ADOS-4.3.010 — Projection method ⚠

**Decision.** First-angle projection shall be used, and the projection method shall be stated by
symbol in the title block. Third-angle projection is permitted where the jurisdiction requires it,
and shall then be used throughout the set.

**Rationale (I).** The two methods produce mirror-image arrangements; a set mixing them is
systematically misread. The symbol makes the method explicit rather than assumed.

**Validation.** `V-4.3.010`: projection symbol present; view arrangement consistent with the
declared method.

### ADOS-4.3.020 — Plan cut plane ⚠

**Decision.** The plan cut plane shall be at 1200 mm above the finished floor level of the level
shown, unless the level's openings require otherwise, in which case the cut height shall be stated
on the sheet. The view range (how far below and above the cut plane is visible) shall be declared
per view and shall be constant across the set.

**Rationale (R).** 1200 mm cuts standard window openings and door openings while remaining below
typical high-level joinery and above worktops. A stated cut height converts an assumption into
information (`ADOS-0.4.020`).

**Exceptions.**
1. Where a level's openings all sit above 1200 mm, a raised cut plane is permitted; the height
   shall be stated and a note shall identify the affected elements.

**Validation.** `V-4.3.020`: cut plane height stated on every plan; view range constant across the
set unless declared.

### ADOS-4.3.030 — Orientation invariance ⚠

**Decision.** All plans of a project shall use the same orientation. North shall be within 45° of
sheet-up where the site geometry permits; where it does not, a single project orientation shall be
declared and used on every plan without exception.

**Rationale.** §1.2.6. Rotating one plan to fit the sheet invalidates the reader's spatial model
and is a leading cause of left/right errors in setting out.

**Validation.** `V-4.3.030`: north vector identical across all plan views (±0°).

### ADOS-4.3.040 — North point

**Decision.** Every plan shall carry a north point in a fixed position, minimum 15 mm diameter,
indicating true north, with grid north shown additionally where the project uses a projected
coordinate system and the two differ by more than 0.5°.

**Validation.** `V-4.3.040`: north point present on every plan at the fixed position; both norths
shown where required.

### ADOS-4.3.050 — Elevation and section view direction

**Decision.** Elevations shall be named by the direction they face (`NORTH ELEVATION` faces north).
Section view direction shall be indicated by the section marker arrows; the drawn view shall show
what is seen looking in the arrow direction.

**Rationale.** Naming elevations by the facing direction is the convention that matches how a
person standing outside describes them, and is unambiguous for non-orthogonal buildings when
combined with the key plan.

**Validation.** `V-4.3.050`: elevation name matches the outward normal of the depicted façade
within ±45°; section geometry matches the marker direction.

### ADOS-4.3.060 — Level datum

**Decision.** All vertical positions shall be expressed relative to a single project datum, stated
on every section and elevation with its relationship to the national datum. Level values shall be
given to three decimal places in metres with an explicit sign (`+12.450`, `−3.200`).

**Rationale (R).** Two datums on one project is one of the most expensive errors in construction.
An explicit sign prevents the transcription error `12.450` → `−12.450` from being invisible.

**Validation.** `V-4.3.060`: single datum declared; all level values signed and to three decimals;
national datum relationship stated.

---

## 4.4 Grids and setting-out

### ADOS-4.4.010 — Grid purpose

**Decision.** Every project shall have a setting-out grid, shown on all plans, sections and
elevations, and dimensioned on the setting-out drawing (`ADOS-5.5`). The grid is the shared
coordinate system between disciplines and between drawing and site.

### ADOS-4.4.020 — Grid graphics

**Decision.** Grid lines shall be drawn `L-CENT` at tier W1, terminating in a circular bubble of
10 mm diameter at tier W2, with the label at 3.5 mm cap height centred in the bubble. Bubbles shall
appear at both ends of every grid line on every view where the grid appears.

**Rationale.** Enclosure (rank 9) marks the grid as apparatus rather than building content; the
centre-line pattern is the standard axis convention; bubbles at both ends allow the label to be
read from either edge of the sheet without tracing the line.

**Validation.** `V-4.4.020`: bubble diameter 10 mm ±0.5; label height 3.5 mm; both ends present.

### ADOS-4.4.030 — Grid labelling

**Decision.** Per `ADOS-2.5.050`: letters on the longer axis omitting `I` and `O`, numbers on the
shorter axis, both increasing left-to-right and bottom-to-top in the project orientation.

### ADOS-4.4.040 — Grid extension and secondary grids

**Decision.** Secondary or partial grids shall be labelled with the parent grid label plus a
decimal suffix (`B.1`, `B.2`), not with new letters. Grid labels shall never be reused between
levels.

**Rationale.** A suffix preserves the ordering relation, so `B.1` is unambiguously between `B` and
`C`. A new letter destroys it.

**Validation.** `V-4.4.040`: secondary labels match `^[A-Z]\.\d+$` or `^\d+\.\d+$`; ordering
consistent with geometry.

### ADOS-4.4.050 — Setting-out origin

**Decision.** A single setting-out origin shall be declared, given in the project coordinate system
and in the national coordinate system, marked on the setting-out drawing with a coordinate symbol
and stated numerically.

**Validation.** `V-4.4.050`: origin present with both coordinate pairs; model shared coordinates
match (`ADOS-6.5.030`).

---

## 4.5 Dimensions

### 4.5.1 Dimensioning philosophy

Dimensions are the instructions by which the building is set out. They are not measurements of the
drawing; they are commitments. Three consequences follow:

1. **Every dimension shall be intentional.** A dimension exists because someone must set that
   distance out. Dimensions produced by automatic tagging of everything are noise and are
   prohibited.
2. **Dimension the requirement, not the residue.** Dimension what must be achieved; let the
   remainder absorb tolerance. Over-dimensioning creates unsatisfiable chains.
3. **Every chain shall close.** An open chain is an unverifiable instruction.

### ADOS-4.5.010 — Units ⚠

**Decision.** A project shall declare one length unit for drawings and use it exclusively.
Millimetres shall be the default for building drawings; metres shall be used for site plans at
1:500 and smaller and for level values. Unit symbols shall be omitted on drawings where the unit is
declared in the title block, and shall be present wherever a value uses a non-default unit.

**Rationale.** Mixed units are a documented source of order-of-magnitude error. Omitting the symbol
for the declared unit reduces annotation object width and count; requiring it for exceptions makes
exceptions visible.

**Validation.** `V-4.5.010`: unit declaration present; values in non-default units carry a symbol;
no value carries a symbol matching the default unit.

### ADOS-4.5.020 — Dimension line geometry ⚠

**Decision.** Dimension geometry, in printed millimetres at the nominated size:

| Element | Value | Tier |
|---|---|---|
| Extension line offset from the object | 2.0 mm | W1 |
| Extension line projection beyond the dimension line | 2.0 mm | W1 |
| First dimension line offset from the object | 10.0 mm | W1 |
| Spacing between parallel dimension chains | 10.0 mm | W1 |
| Terminator: oblique stroke at 45°, length | 3.5 mm | W2 (0.35 mm) |
| Text cap height | 2.5 mm | — |
| Text offset above the dimension line | 1.0 mm | — |

**Rationale.**
- Offsets of 2.0 and 10.0 mm sit on the sub-module grid (`ADOS-3.3.030`), so chains align across a
  drawing automatically.
- The 2.0 mm object offset exceeds the text clear zone floor (1.0 mm) and prevents the extension
  line reading as part of the building.
- 10.0 mm chain spacing gives 5 mm clear between the 2.5 mm text of adjacent chains — twice the
  text clear zone, satisfying `ADOS-3.5.020`.
- The oblique stroke is preferred over the arrowhead because a filled arrowhead at architectural
  scales occupies 3–4 mm of the dimension it terminates and fills in under reproduction, while an
  oblique stroke is a single line at a discriminable angle.

**Exceptions.**
1. Radial, diameter, angular and leader dimensions use a filled arrowhead of 3.5 mm length and
   1.0 mm width, because an oblique stroke cannot indicate direction.

**Validation.** `V-4.5.020`: measured geometry within ±0.3 mm of the table.

### ADOS-4.5.030 — Chain closure ⚠

**Purpose.** Make dimensional errors detectable on the drawing.

**Background.** A chain of sub-dimensions plus an overall dimension is a redundant system: the
overall is the sum. Redundancy converts an undetectable error into a detectable contradiction.

**Problem.** Chains without an overall dimension propagate a single wrong sub-dimension into the
built work with no check.

**Decision.** Every dimension chain shall be closed: the sum of the sub-dimensions shall equal the
overall dimension exactly. Where the sum cannot be exact because a component absorbs tolerance,
that component shall be dimensioned as the tolerance-absorbing element and marked, and the overall
shall still be stated.

**Implementation.** Three chain levels per side, outermost first:

```
chain 3 (outermost)  overall building dimension
chain 2              grid-to-grid dimensions
chain 1 (innermost)  opening and element dimensions relative to grid
```

**Exceptions.**
1. Detail views at 1:10 and larger may use a single chain where the overall is dimensioned
   elsewhere and referenced.

**Validation.** `V-4.5.030`: for every chain, `|Σ sub − overall| = 0` (integer millimetres) or the
tolerance-absorbing element is marked; open chains = 0.

**Common mistakes.** Rounding each sub-dimension to 5 mm and leaving the overall as the true sum;
a chain that stops at the last opening and never reaches the building face.

**Automation notes.** Chain closure is checkable from the model without rendering; it shall be a
build-blocking check.

### ADOS-4.5.040 — Dimension text placement

**Decision.** Dimension text shall be placed above the dimension line, centred, reading
left-to-right for horizontal dimensions and bottom-to-top for vertical dimensions. Where the space
between extension lines is less than the text width plus 2 mm, the text shall be placed outside the
extension lines with a leader, or the dimension line shall be broken. Text shall never be reduced
in size to fit (`ADOS-3.4.010`).

**Validation.** `V-4.5.040`: no dimension text below its line; no text overlapping extension lines;
no dimension text below 2.5 mm.

### ADOS-4.5.050 — Dimension necessity

**Decision.** A dimension shall be present where, and only where, a party must set that distance
out. Dimensions duplicated between chains, dimensions derivable from a grid plus one offset, and
dimensions of standard components carried in a schedule shall not be shown.

**Rationale.** `ADOS-0.3.020` and the density budget. Redundant dimensions also create
contradictions when one is revised.

**Validation.** `V-4.5.050`: duplicate dimension detection reports 0 duplicated distances between
the same two references on the same view.

### ADOS-4.5.060 — Reference faces ⚠

**Decision.** Every dimension shall state its reference faces unambiguously. The project shall
declare a single convention for wall dimensioning — to structural face, to finished face, or to
centre line — and shall apply it throughout, with the convention stated on the general notes sheet
and on every plan.

**Rationale (R).** "Is this to the blockwork or to the plaster?" is one of the most frequent site
queries and one of the most expensive to resolve after the fact. The convention is a project-level
decision because mixing conventions within a set is unresolvable by the reader.

**Implementation.** ADOS default: dimension to **structural face** on GA plans, with finished
openings dimensioned to **finished face** and marked `CLR` where a clear dimension is required.

**Validation.** `V-4.5.060`: convention declared; `CLR` dimensions present at every location where
a clear dimension is required by the specification.

### ADOS-4.5.070 — Tolerances

**Decision.** Where a dimension has a permitted deviation different from the general tolerance in
the specification, the deviation shall be stated with the dimension in the form `2400 ±5`. Where a
dimension is a maximum or minimum, it shall be stated as `≤ 2400` or `≥ 2400`. General tolerances
shall be in the specification, not on drawings.

**Rationale.** `ADOS-0.4.020` and `ADOS-2.2.010` (tolerance carrier).

**Validation.** `V-4.5.070`: tolerance tokens match the permitted grammar; general tolerance
statement absent from drawings and present in the specification.

### ADOS-4.5.080 — Provisional dimensions

**Decision.** A dimension not yet fixed shall be shown as `TBC` with a hold reference
(`ADOS-2.6.080`), never as a value. A provisional value with a marker is permitted only where a
value is required for coordination and shall be shown as `(2400) TBC/H-014`.

**Rationale.** `ADOS-0.4.020`. An unmarked provisional dimension will be procured against.

**Validation.** `V-4.5.080`: every `TBC` resolves to a live hold entry.

### ADOS-4.5.090 — Dimension provenance

**Decision.** Dimensions derived from survey rather than from design intent shall carry the token
`(S)`; dimensions to be verified on site shall carry `(V)`. The tokens shall be explained in the
legend.

**Rationale.** `ADOS-0.4.050`, `ADOS-0.4.060`. On refurbishment projects the distinction between a
designed dimension and a surveyed one determines who bears the risk of it being wrong.

**Validation.** `V-4.5.090`: tokens present on all survey-derived dimensions in existing-fabric
views; legend entry present.

### ADOS-4.5.100 — Level annotation

**Decision.** Levels shall be annotated with a level symbol (a 3.5 mm filled/half-filled triangle
on plans, a horizontal line with the value on sections and elevations) and the value per
`ADOS-4.3.060`, prefixed with the level type: `FFL` (finished floor), `SSL` (structural slab),
`SFL` (structural floor), `TOS` (top of steel), `TOW` (top of wall), `SOF` (soffit).

**Validation.** `V-4.5.100`: every level annotation carries a type prefix from the closed set and a
signed three-decimal value.

---

## 4.6 Leaders and tags

### ADOS-4.6.010 — Leader geometry ⚠

**Decision.** A leader shall consist of: a terminator at the referenced element, a single straight
segment, and at most one horizontal landing of 3.0 mm before the text. Curved, multi-segment and
zero-length leaders shall not be used.

| Element | Value |
|---|---|
| Terminator at element: filled dot | 1.5 mm diameter |
| Terminator at an edge: arrowhead | 3.5 × 1.0 mm |
| Leader line tier | W1 (0.18 mm) |
| Landing length | 3.0 mm |
| Permitted leader angles | 30°, 45°, 60° from horizontal |
| Minimum leader length | 8.0 mm |
| Maximum leader length | 60.0 mm |

**Rationale.**
- A dot terminator inside a region and an arrow at an edge distinguish "this area" from "this
  line", which readers otherwise infer wrongly.
- Restricting angles to three values makes leaders visually parallel in groups, which reduces the
  crossing-detection load; arbitrary angles produce a visual thicket.
- Maximum length 60 mm because a longer leader crosses more content than the annotation is worth;
  beyond it, the note belongs in the notes zone with a tag.

**Validation.** `V-4.6.010`: leader angle ∈ {30, 45, 60}° ±1°; segment count = 1; landing = 3 mm
±0.3; length within bounds.

### ADOS-4.6.020 — Leader crossing ⚠

**Decision.** Leaders shall not cross each other, shall not cross dimension lines, and shall not
cross drawn building edges except where unavoidable, in which case the crossing count shall be
minimised and the leader shall not be broken.

**Validation.** `V-4.6.020`: leader–leader crossings = 0; leader–dimension crossings = 0;
leader–geometry crossings minimised by the solver and reported.

### ADOS-4.6.030 — Tag content ⚠

**Decision.** A tag shall contain a reference (a mark or type code), never a restated value
(`ADOS-2.2.020`). Tag content shall be derived from the model, never typed.

**Validation.** `V-4.6.030`: tags containing numeric values with units = 0 (except level and
dimension annotations, which are not tags).

### ADOS-4.6.040 — Tag placement

**Decision.** Tags shall be placed inside the tagged element where it is large enough to contain
the tag plus its clear zone; otherwise outside with a leader. Tags for elements of the same class
on one view shall be aligned where the geometry permits.

**Rationale.** Alignment converts a set of tags into a scannable column, which supports the
"find all doors" task directly.

**Validation.** `V-4.6.040`: no tag overlaps geometry without a mask; alignment clusters detected.

### ADOS-4.6.050 — Note tags

**Decision.** Sheet-specific notes shall be referenced from the drawing by a numbered tag enclosed
in a 5 mm hexagon, matching the note number in `Z-NOTES`. Notes shall not be written on the drawing
itself except where they are shorter than 30 characters and refer to a single element.

**Rationale.** Long notes in the drawing area consume drawing space, compete with content for
attention, and cannot be revised without re-laying-out the drawing. The tag costs one small symbol.

**Validation.** `V-4.6.050`: every note tag resolves to a note in `Z-NOTES`; every note in
`Z-NOTES` has at least one tag; drawing-area text runs > 30 characters = 0.

---

## 4.7 Reference markers

### ADOS-4.7.010 — Marker inventory ⚠

**Decision.** Four reference markers shall be used, and only these:

| Marker | Form | Purpose |
|---|---|---|
| **Section marker** | Cut line with direction arrows and a bubble at each end | Locate a section view |
| **Detail marker** | Circle or rounded rectangle enclosing the area, with a leader to a bubble | Locate a detail view |
| **Elevation marker** | Circle divided into four quadrants with direction arrows | Locate interior elevations |
| **Match line** | Heavy dashed line with a bubble | Continuation between sheets |

**Validation.** `V-4.7.010`: marker forms match the definitions; undefined marker forms = 0.

### ADOS-4.7.020 — Marker bubble content ⚠

**Decision.** Every reference bubble shall be a **20 mm** diameter circle divided by a horizontal
line on the centre, carrying the **view identifier above** at 3.5 mm cap height and the **container
identifier below** at 2.5 mm cap height (`ADOS-2.4.020`). Each field's baseline shall sit 5 mm from
the centre line.

**Rationale.** Fixed field positions mean the reader does not parse; they saccade to a known
position. Upper = which view, lower = which sheet, matching the search sequence. The upper field
carries the larger step because it is the field the reader searches on.

**Derivation of the diameter.** The lower field is the constraint. A container short form
(`ADOS-2.5.020`) is six characters; at the 2.5 mm cap of `ADOS-2.4.020` that is 11.5 mm of set
width in a normal-width grotesque. Text inside a circle is bounded not by the diameter but by the
chord at the **baseline**, which is the narrowest line the glyph box touches. With the baseline at
0.25 d below the centre, that chord is

```
c = 2 · √( (d/2)² − (0.25 d)² ) = 0.866 d
```

Requiring `c ≥ 11.5 + 2 × 1.25` — the string plus the clear zone `ADOS-3.4.080` puts round it,
which at a 2.5 mm cap is `0.5 × 2.5 = 1.25 mm` — gives `d ≥ 16.1 mm`. The next value on the 5 mm
sub-module lattice
(`ADOS-3.3.030`) is **20 mm**, which is also two whole modules; 14 mm was neither on the lattice nor
large enough, and a 14 mm bubble containing a six-character identifier at 3.5 mm cap (16.1 mm of set
width) cannot be drawn at all.

**Validation.** `V-4.7.020`: bubble diameter 20 mm ±0.5; two fields present; upper field 3.5 mm cap,
lower field 2.5 mm cap; the set width of each field is at least 2.5 mm shorter than the chord at its
own baseline; both fields resolve.

### ADOS-4.7.030 — Section marker geometry

**Decision.** The section cut line shall be drawn at 1.00 mm width, `L-CONT`, shown only at the ends
of the cut and at direction changes (not continuously across the drawing), with a length of 15 mm
at each end. Direction arrows of 5 mm length shall be placed at the inner end of each segment,
pointing in the view direction. The bubble sits at the outer end.

**Rationale.** A continuous section line across a plan adds a heavy line through the drawing
content, obscuring it, for no informational gain: the reader needs the cut's position and
direction, which the end segments give.

**Validation.** `V-4.7.030`: cut line segments ≤ 15 mm except at direction changes; arrows present;
line width 1.00 mm.

### ADOS-4.7.040 — Detail marker geometry

**Decision.** The detail marker shall enclose the detailed area with a `L-CONT` W1 boundary
(circle, or rounded rectangle with 5 mm corner radius), with a leader from the boundary to the
bubble. The enclosed area shall correspond to the extent shown in the referenced detail within
±10 %.

**Rationale.** A marker whose extent does not match the detail misleads the reader about what the
detail covers, which is the most common cause of a detail being applied to the wrong condition.

**Validation.** `V-4.7.040`: enclosed real-world extent vs detail view extent within ±10 %.

### ADOS-4.7.050 — Marker density

**Decision.** No more than 12 reference markers shall appear on one view.

**Rationale.** Markers are enclosure-channel objects and are pre-attentively salient (§1.2.5);
beyond about a dozen they form a texture and lose salience, and the view's own content is obscured.

**Validation.** `V-4.7.050`: marker count per view ≤ 12.

### ADOS-4.7.060 — Match lines

**Decision.** Where a level is split across sheets, a match line shall be drawn at 1.00 mm `L-DASH`,
labelled with the continuation sheet identifier on both sides, at an identical real-world position
on both sheets, and coinciding with a grid line where possible.

**Rationale.** A match line at a grid line gives the reader a shared reference for aligning the two
sheets mentally; an arbitrary match line does not.

**Validation.** `V-4.7.060`: match line positions on the two sheets are identical in project
coordinates; labels reciprocal (`ADOS-2.4.030`).

### ADOS-4.7.070 — Overlap at match lines

**Decision.** Adjacent sheets shall overlap by at least one structural bay or 3 m, whichever is
greater, with the overlap area shown at tone `T1` on the non-primary sheet and labelled
`OVERLAP — SEE <ref>`.

**Rationale (R).** A zero-overlap split forces the reader to hold the edge condition in memory
across a sheet change. An overlap costs area and removes the memory load; toning it prevents
double-counting in take-off.

**Validation.** `V-4.7.070`: overlap extent ≥ threshold; overlap content at `T1`; label present.

---

## 4.8 Annotation philosophy

### ADOS-4.8.010 — Annotation is reference, not description ⚠

**Decision.** Drawing annotation shall identify and locate; it shall not describe. Description
belongs to the specification and the schedules (`ADOS-2.2.010`).

**Rationale.** A description on a drawing is a duplicate of an authoritative value
(`ADOS-0.3.020`), occupies drawing area, and is the first thing to go stale.

**Examples.** *Conforming:* `W-14`. *Non-conforming:* `Powder-coated aluminium window, RAL 7016,
double glazed with argon fill, U ≤ 1.2`.

**Validation.** `V-4.8.010`: annotation strings matching specification-content patterns
(materials, performance values, standards references) = 0 on drawings.

### ADOS-4.8.020 — Note classes

**Decision.** Notes shall be classified and placed accordingly:

| Class | Content | Location |
|---|---|---|
| **General notes** | Apply to the whole set | General notes sheet only (`ADOS-5.3`) |
| **Sheet notes** | Apply to this sheet | `Z-NOTES`, numbered, tagged from the drawing |
| **Local notes** | Apply to one element, ≤ 30 characters | Adjacent to the element with a leader |
| **Scope notes** | What this sheet excludes | `Z-NOTES` block 1 |

**Validation.** `V-4.8.020`: every note is classified; general notes appear once in the set;
duplicated note text across sheets = 0.

### ADOS-4.8.030 — Note numbering

**Decision.** Sheet notes shall be numbered `01`, `02`… within the sheet, and shall be renumbered
only when a note is added or removed; existing tags shall be updated in the same operation.

**Validation.** `V-4.8.030`: tag-to-note mapping is bijective.

### ADOS-4.8.040 — Prohibited note content ⚠

**Decision.** Notes shall not contain: instructions to the reader to determine the design
("contractor to coordinate", "as required", "to suit"), disclaimers of the drawing's own accuracy,
or requirements duplicated from the specification.

**Rationale.** `ADOS-0.4.030`. "Contractor to coordinate" without stating what, with whom, and to
what criterion, transfers a design obligation without transferring the information needed to
discharge it.

**Exceptions.**
1. A coordination note that names the parties, the interface, the criterion and the resolution
   mechanism is permitted and is not a disclaimer.

**Validation.** `V-4.8.040`: banned-phrase list produces 0 matches outside Exception 1's structured
form.

### ADOS-4.8.050 — Note language

**Decision.** Per `ADOS-0.5.050` to `ADOS-0.5.090`: active voice, one requirement per note, ≤ 25
words, controlled vocabulary, registered abbreviations only.

**Validation.** `V-4.8.050`: word count per note ≤ 25; unregistered abbreviations = 0; readability
index within the band defined in `ADOS-8.2.060`.

### ADOS-4.8.060 — Exclusion notation ⚠

**Decision.** Content deliberately not shown shall be marked `NOT SHOWN — SEE <ref>` or
`BY OTHERS — <party>` at the location, or, for an area, by a `T1` hatch with a legend entry naming
the excluded scope and the responsible party.

**Rationale.** `ADOS-0.3.090`.

**Validation.** `V-4.8.060`: every scope boundary in the model has a corresponding exclusion
annotation on the drawings covering it.

---

## 4.9 Legends and symbols

### ADOS-4.9.010 — Legend completeness ⚠

**Decision.** Every symbol, hatch, line type and tone that carries meaning on a sheet shall appear
in a legend accessible to the reader of that sheet: either in `Z-NOTES` on the sheet, or on the
legend sheet (`ADOS-5.3`) which is referenced from `Z-NOTES`.

**Rationale.** `ADOS-0.1.3`: interpretability without the author. A symbol whose meaning exists
only in the office is information that expires when the staff change.

**Validation.** `V-4.9.010`: for every distinct graphic state detected on a sheet, a legend entry
exists; unexplained states = 0.

### ADOS-4.9.020 — Local legend preference

**Decision.** Symbols used on a sheet shall be explained on that sheet where the legend fits within
`Z-NOTES`. Only where the symbol set exceeds the available space shall the sheet reference the
legend sheet.

**Rationale (C).** Recognition beats recall, and on-sheet beats off-sheet: resolving a symbol from
another sheet costs a navigation event (10–60 s) and a context reload.

**Validation.** `V-4.9.020`: sheets with ≤ 12 distinct symbols carry a local legend.

### ADOS-4.9.030 — Legend structure

**Decision.** Legends shall be grouped by channel (symbols, line types, hatches, tones), each group
with ≤ 7 entries, each entry showing the graphic at its actual printed size adjacent to its
meaning, in a two-column layout with the graphic left.

**Rationale.** §1.2.4 (group size); actual size because a legend graphic at the wrong size does not
match what the reader is looking for.

**Validation.** `V-4.9.030`: entries per group ≤ 7; legend graphic dimensions equal the drawing's
within ±5 %.

### ADOS-4.9.040 — Symbol design requirements

**Decision.** Symbols shall satisfy:

| # | Requirement | Reason |
|---|---|---|
| 1 | Distinguishable at 3 mm printed | Reproduction and density |
| 2 | Distinguishable by shape alone, without fill | Fill collapses on reproduction |
| 3 | Distinguishable from every other symbol in the set at 3 mm after two copy generations | Absolute identification |
| 4 | Constructed from the tone ladder and line tiers only | `ADOS-3.1.010` |
| 5 | Rotation-invariant meaning, or explicit orientation | Symbols are read at any angle on site |
| 6 | Derived from the applicable national or ISO symbol set where one exists | Interoperability |

**Validation.** `V-4.9.040`: pairwise symbol confusion test at 3 mm under degradation; confusable
pairs = 0.

### ADOS-4.9.050 — Symbol set size

**Decision.** A project shall use at most 30 distinct symbols. The set shall be declared in the
project symbol register.

**Rationale.** Beyond about 30, symbols cease to be recognised and become items to look up, at
which point a text label is faster and less error-prone.

**Validation.** `V-4.9.050`: distinct symbols in the set ≤ 30; all registered.

---

## 4.10 Hatch and material representation

### ADOS-4.10.010 — Hatch purpose

**Decision.** Hatch shall indicate material class of cut elements, or a zone condition. Hatch shall
not be used for emphasis, shading or texture.

**Rationale.** `ADOS-0.3.010` and the density budget: hatch is the largest consumer of ink coverage
on a drawing (`ADOS-3.7.020`) and therefore the most expensive channel to spend on decoration.

**Validation.** `V-4.10.010`: every hatch instance maps to a declared material class or zone.

### ADOS-4.10.020 — Hatch geometry ⚠

**Decision.** Hatch shall be defined in printed dimensions and shall satisfy:

```
line width       ≥ 0.18 mm  (W1)
pitch            ≥ 0.50 mm  and  pitch ≥ line width + 0.30 mm
resulting coverage ≤ 0.25   (counted toward ADOS-3.7.020)
```

Hatch angles shall be 0°, 30°, 45°, 60° or 90°. Hatch shall not align with a drawn element edge
within ±5°.

**Rationale.** §1.3.3 for pitch; angle restriction gives five reliably distinguishable orientations;
the ±5° rule prevents moiré and prevents the hatch reading as an edge.

**Validation.** `V-4.10.020`: pitch and width within bounds at the nominated size; angles in the
permitted set; no hatch within ±5° of a bounding edge.

**Common mistakes.** Hatch defined in model units, so the pitch is 50 mm real, which is 0.5 mm at
1:100 (conforming) and 10 mm at 1:5 (a striped pattern that reads as geometry).

### ADOS-4.10.030 — Hatch inventory ⚠

**Decision.** At most eight distinct hatch patterns shall be used in a set. The ADOS default set:

| Token | Pattern | Material class |
|---|---|---|
| `H-CONC` | 45° single at 1.5 mm pitch with random aggregate dots | In-situ concrete |
| `H-MSNR` | Coursed rectangles at scale, or 45° double at 2.0 mm below 1:50 | Masonry |
| `H-INSU-R` | Cross-hatch 45°/135° at 1.5 mm pitch | Rigid insulation |
| `H-INSU-Q` | Continuous wave, 3 mm amplitude | Quilt insulation |
| `H-TIMB-S` | Diagonal 30° at 1.0 mm with end-grain circles at section | Timber, sawn |
| `H-TIMB-E` | Two crossed diagonals in a rectangle | Timber, engineered |
| `H-METL` | Solid `T5` | Metal |
| `H-EART` | Broken 45° with dots below a ground line | Earth / fill |

**Rationale.** Eight is the reliable identification limit for patterns of this complexity under
degradation; the set covers the material classes that appear as *cut* elements in architectural
drawings. Finishes are not hatched — they are scheduled.

**Exceptions.**
1. Jurisdiction overlays may substitute nationally mandated patterns for equivalent classes.

**Validation.** `V-4.10.030`: distinct patterns ≤ 8; each maps to a material class in the register.

### ADOS-4.10.040 — Hatch by scale ⚠

**Decision.** Hatch application shall vary with scale:

| Scale | Cut element representation |
|---|---|
| 1:200 and smaller | Solid `T3` poché; no pattern |
| 1:100 | Solid `T3` poché for structure, `T1` for non-structure; no pattern |
| 1:50 | Single pattern per element, no layers |
| 1:20 | Layers shown, each with its pattern |
| 1:10 and larger | Layers shown with patterns and outlines at W2 |

**Rationale.** §1.3.3 and `ADOS-4.2.030`: patterns whose pitch would fall below 0.5 mm printed
cannot be resolved and become a grey field. Poché carries the same information (this is solid
material) at a fraction of the ink.

**Validation.** `V-4.10.040`: hatch usage matches the scale row; patterned hatch at ≤ 1:100 = 0.

### ADOS-4.10.050 — Poché

**Decision.** Poché (solid fill of cut material) shall use `T3` for primary structure and `T5` only
where the element is thinner than 1.0 mm printed. Poché shall be bounded by a W3 outline.

**Rationale.** `T5` at large areas produces a page that is expensive to print, slow to dry, and
prone to set-off; it also reduces the contrast available for `T4` emphasis. `T5` is reserved for
elements too thin to read as filled at `T3`.

**Validation.** `V-4.10.050`: `T5` fill area per sheet ≤ 5 % of drawing area unless all instances
are below the thinness threshold.

### ADOS-4.10.060 — Hatch boundaries

**Decision.** Every hatch region shall be bounded by a closed boundary at the tier of the element
it fills. Unbounded, "picked-point" hatch that can leak is prohibited.

**Rationale.** A leaking hatch is a silent failure that appears only on the printed sheet and often
only after a geometry change.

**Validation.** `V-4.10.060`: every hatch has a closed boundary; hatch area outside its element
geometry = 0.

---

## 4.11 Detail graphics

### ADOS-4.11.010 — Detail extent

**Decision.** A detail shall show enough surrounding context for the reader to locate it without
reference to another drawing: at least one recognisable datum (a floor line, a grid, a structural
element) and at least 100 mm of real-world extent beyond the junction on each side.

**Rationale (C).** A detail without context cannot be oriented, and the most common misuse of
details — applying them to the wrong condition — follows directly from missing context.

**Validation.** `V-4.11.010`: every detail view contains ≥ 1 datum annotation; extent beyond the
junction ≥ 100 mm real.

### ADOS-4.11.020 — Detail annotation completeness ⚠

**Decision.** Every detail shall annotate: each material layer with a reference (not a
description), the dimensions that must be set out, the levels at any change, the fixing or
connection principle, and the tolerance where it differs from the general tolerance.

**Validation.** `V-4.11.020`: for every distinct layer in the detail geometry, an annotation
reference exists; unannotated layers = 0.

### ADOS-4.11.030 — Detail orientation

**Decision.** Details shall be drawn in their built orientation: horizontal sections viewed from
above, vertical sections viewed with up as up. A detail shall not be rotated to fit the sheet.

**Validation.** `V-4.11.030`: detail view rotation = 0° relative to the source geometry.

### ADOS-4.11.040 — Detail identification

**Decision.** Every detail shall carry a title in the form:

```
<view id>   <TITLE IN UPPER CASE>            <scale>
            <typical applicability or location>   ADOS-2.3.030
```

with the view identifier in a **15 mm** bubble at the left of the title.

The three bubble sizes are a family and are distinguishable at a glance without being read:
10 mm carries a grid reference (`ADOS-4.4.020`), 15 mm names a view on the sheet the reader is
holding, 20 mm sends the reader to another sheet (`ADOS-4.7.020`). Only the last carries two fields,
which is why only the last needs the diameter derived; the other two are sized to be told apart.
All three are whole sub-modules of `ADOS-3.3.030`.

**Validation.** `V-4.11.040`: title block-per-view present with all fields.

### ADOS-4.11.050 — Break lines

**Decision.** Where a detail omits a length of a continuous element, a break line shall be used:
a `L-CONT` W2 line with a single zig-zag of 4 mm amplitude. Both sides of the break shall remain
dimensionally referenced to a datum.

**Rationale.** An unbroken omission implies a dimension that does not exist. The break symbol is
the explicit statement that length has been removed (`ADOS-0.3.090`).

### ADOS-4.11.060 — Photographs and generated images

**Decision.** Photographs and machine-generated images included in technical documentation shall be
labelled with: source, date, and, for generated images, the statement `GENERATED IMAGE —
ILLUSTRATIVE ONLY — NOT A CONSTRUCTION INSTRUCTION` at ≥ 2.5 mm cap height within the image bounds.

**Rationale.** `ADOS-0.4.040`. A rendered image adjacent to technical content is read as
authoritative unless it says otherwise.

**Validation.** `V-4.11.060`: every raster image has a source label; generated images carry the
statement.

---

## 4.12 Representation of existing, new and removed fabric

### ADOS-4.12.010 — Phase encoding ⚠

**Decision.** Fabric phase shall be encoded as:

| Phase | Line type | Tier | Tone |
|---|---|---|---|
| Existing to remain | `L-CONT` | W1 | `T1` |
| Existing to be removed | `L-DASH` | W1 | `T0` |
| New | `L-CONT` | W3 / W2 per `ADOS-4.1.020` | `T3` |
| Temporary | `L-DASH` | W2 | `T2` |

**Rationale.** Three channels are used redundantly because misreading phase is high-cost (demolition
of the wrong element is irreversible), which `ADOS-3.1.040` permits and requires.

**Validation.** `V-4.12.010`: every element carries a phase; graphic state matches the table;
phase encoding legend present on every sheet showing more than one phase.

### ADOS-4.12.020 — Demolition drawings are separate ⚠

**Decision.** Demolition shall be shown on dedicated demolition drawings (`ADOS-5.6`), not combined
with proposal drawings, except on small projects where a single combined drawing is registered as a
deviation.

**Rationale (R).** A combined drawing requires the reader to hold two states of the building
simultaneously while performing an irreversible operation. The error rate is high and the
consequence is unrecoverable.

**Validation.** `V-4.12.020`: drawings containing both removal and new-build annotation = 0 unless
registered.

---

## 4.13 Stairs, ramps and level changes

### 4.13.1 Why they need their own rules

**Problem.** A stair is the element most frequently drawn incorrectly and most frequently the
subject of a statutory failure. It is a three-dimensional object represented in plan by a
convention that discards most of its geometry, and it is governed by dimensional rules with no
tolerance.

**Rationale (R).** Three facts make stairs special: the plan representation is conventional rather
than projective (the cut through a flight is a graphic device); the governing dimensions (going,
rise, headroom, width) are statutory and non-negotiable; and the relationship between the flights
of consecutive levels is the source of most coordination errors.

### ADOS-4.13.010 — Stair plan representation ⚠

**Decision.** A stair in plan shall show:

1. Every tread in the flight, at W2, with the going dimensioned once per flight as
   `n × going = total`.
2. The cut line through the flight at the plan cut plane, drawn as a break line
   (`ADOS-4.11.050`) at W2, with the flight beyond the cut plane at W1.
3. A direction arrow originating at the lower end of the flight, terminating with an arrowhead at
   the upper end, labelled `UP` or `DN` relative to the level shown.
4. Numbered treads at the first, last and every fifth tread of each flight.
5. Landing levels annotated with FFL (`ADOS-4.5.100`).
6. Handrails and balustrades at W2, with their type reference and height stated in section or
   interior elevation.
7. The nosing line where a nosing projects, at W1.

**Rationale.** `UP`/`DN` labels are relative to the level shown, which is why they differ between
consecutive plans of the same stair — a difference that reads as an error unless the convention is
declared. The direction arrow's origin, not its head, carries the "from" information, which is why
the origin is specified.

**Validation.** `V-4.13.010`: every stair in every plan carries all seven items; direction arrow
labels are consistent with the level relationship.

### ADOS-4.13.020 — Stair dimensional annotation ⚠

**Decision.** Every stair shall carry, in plan or section: going, rise, number of risers per flight,
total rise per flight, clear width between finished faces or handrails as applicable, landing
dimensions, and headroom at the critical point.

The going and rise shall be stated as a product: `14 R @ 175 = 2450` and `13 G @ 275 = 3575`, so
that the arithmetic is visible and checkable.

**Rationale.** Stating a product rather than individual dimensions makes the two most common errors
— a miscounted riser and an inconsistent going — visible on the drawing, and it closes the chain
(`ADOS-4.5.030`) against the floor-to-floor dimension.

**Validation.** `V-4.13.020`: `risers × rise = floor-to-floor`; `goings = risers − 1` for a straight
flight; clear width ≥ the statutory minimum for the escape route it serves.

### ADOS-4.13.030 — Headroom ⚠

**Decision.** Headroom shall be dimensioned at the critical point of every stair and ramp: the point
of minimum vertical distance between the pitch line and any element above. The critical point shall
be identified on the section, not assumed.

**Rationale.** Headroom failures are discovered during construction, are expensive to remedy, and
follow from the critical point being at a location nobody drew — typically under an incoming flight
or a structural beam.

**Validation.** `V-4.13.030`: every stair and ramp has a headroom dimension with an identified
critical point; value ≥ the statutory minimum.

### ADOS-4.13.040 — Ramps

**Decision.** A ramp shall be shown with: gradient stated as a ratio (`1:20`), direction of fall
arrow, levels at both ends and at every landing, landing lengths dimensioned, clear width, and
handrail extents. Gradients shall be stated as ratios, never as percentages or degrees, throughout
a project.

**Rationale.** A single gradient notation per project prevents conversion errors. The ratio form is
the one used in accessibility standards and is directly checkable against them.

**Validation.** `V-4.13.040`: all six items present; gradient within the permitted maximum for the
route class; landing spacing within the permitted maximum rise between landings.

### ADOS-4.13.050 — Level changes and thresholds

**Decision.** Every change in finished floor level shall be annotated with levels on both sides and
a reference to the threshold detail. A level change of any magnitude on an accessible route shall be
identified and either dimensioned as compliant or shown as a ramp.

**Rationale (R).** Unannotated small level changes — a 15 mm threshold upstand, a 20 mm finish
change — are the most common accessibility non-conformity found at completion, and they originate in
drawings that show the change but do not state it.

**Validation.** `V-4.13.050`: every level change in the model has annotations on both sides; changes
on the accessible route carry a compliance statement.

---

## 4.14 Curved, sloped and non-orthogonal geometry

### 4.14.1 The setting-out problem

**Problem.** Orthogonal geometry is set out from two chained dimensions. Curved, sloped and
non-orthogonal geometry is not, and drawings that dimension it as though it were produce geometry
that cannot be built to the intended shape.

**Rationale (R).** A curve is set out on site from a centre and a radius, from a chord and an offset,
or from a table of coordinates. Which method is available depends on whether the centre is reachable
and on the accuracy required. The drawing shall therefore state the setting-out method, not only the
shape.

### ADOS-4.14.010 — Curve setting-out ⚠

**Decision.** Every curve in the permanent works shall be dimensioned by one of the following
methods, and the method shall be stated:

| Method | Data required | Use when |
|---|---|---|
| **Centre and radius** | Centre coordinates, radius, start and end angles or tangent points | The centre is within the site and reachable |
| **Chord and offsets** | Chord endpoints, offsets at stated intervals | The centre is unreachable or off site |
| **Coordinate table** | A table of setting-out points at stated intervals with coordinates | Free-form curves, or accuracy better than the offset method allows |
| **Tangent and radius** | Tangent point coordinates, radius, direction of curvature | Curves tangential to straight runs |

Tangent points between a straight and a curve shall always be dimensioned, whichever method is used.

**Rationale.** The tangent point is where a curve error becomes a visible kink. It is also the point
from which the setting-out engineer works, and it is frequently the only point that is not
implicitly defined by the rest of the geometry.

**Validation.** `V-4.14.010`: every curve declares its setting-out method and carries the data that
method requires; every tangent point is dimensioned.

### ADOS-4.14.020 — Coordinate tables

**Decision.** Where a coordinate table is used, it shall state: the coordinate system, the point
interval, the point identifiers, the coordinates to the project's stated precision, and the
tolerance. Points shall be identified on the drawing at the same identifiers.

**Validation.** `V-4.14.020`: table and drawing point sets are identical; coordinate system stated.

### ADOS-4.14.030 — Sloped surfaces ⚠

**Decision.** Every sloped surface shall be defined by: spot levels at every high point, low point
and change of plane; fall direction arrows with the gradient stated for every plane; and the
intersection lines between planes drawn and levelled.

A surface shall not be defined by a single gradient where its boundary conditions require more than
one plane. Where three or more boundary levels are fixed, the surface is over-determined and one
level shall be nominated as the tolerance-absorbing point.

**Rationale.** Three points define a plane. A quadrilateral with four fixed corner levels is a warped
surface, not a plane, and cannot be built from a single tile or slab without twist. Identifying the
tolerance-absorbing point converts an unbuildable instruction into a buildable one.

**Validation.** `V-4.14.030`: for every sloped surface, plane count and fixed level count are
consistent; over-determined surfaces nominate a tolerance-absorbing point.

### ADOS-4.14.040 — Non-orthogonal grids

**Decision.** A non-orthogonal grid shall be defined by: the coordinates of at least three
non-collinear intersections, the angle of each grid direction relative to the project north or to
grid line 1, and the spacing along each direction. Angles shall be stated in degrees, minutes and
seconds, or in decimal degrees to three places, consistently across the project.

**Rationale.** An angular error of 0.1° over a 50 m grid is 87 mm at the far end — larger than any
construction tolerance. Angular precision is therefore not a matter of drawing convention but of
setting-out feasibility.

**Validation.** `V-4.14.040`: ≥ 3 non-collinear coordinated intersections; angles stated to the
declared precision; grid closure error computed and ≤ 1 mm over the grid extent.

### ADOS-4.14.050 — Faceting of curved elements

**Decision.** Where a curved element is built as a series of straight facets, the drawing shall show
the facets, dimension the facet length and the angle between facets, and state the maximum deviation
from the true curve. Showing a true curve where facets will be built is prohibited.

**Rationale.** `ADOS-0.4.040`. A drawn true curve is priced and fabricated as a true curve; a faceted
one is not. The difference is a substantial cost and a visible difference in the finished work.

**Validation.** `V-4.14.050`: elements flagged as faceted in the model are drawn faceted; maximum
deviation stated.

---

## 4.15 Cross-discipline representation

### ADOS-4.15.010 — Ownership determines representation ⚠

**Decision.** On any drawing, content owned by another discipline shall be rendered as background
(`ADOS-3.8.050`: `T1`, W1), shall carry a reference to the owning discipline's container, and shall
not be dimensioned or annotated except where the interface requires it.

**Rationale.** `ADOS-2.8.030`. Content drawn at full weight implies authorship and therefore
responsibility. A services run drawn at W2 on an architectural plan is an instruction the architect
did not intend to give and has not coordinated.

**Validation.** `V-4.15.010`: elements whose discipline differs from the container's discipline are
at `T1`/W1 and carry an ownership reference; dimensioned cross-discipline elements are listed and
justified.

### ADOS-4.15.020 — Service zone reservations ⚠

**Decision.** Where the architecture reserves space for another discipline, the reservation shall be
drawn as a zone with dimensioned extents and levels, labelled with the reserving discipline, the
purpose and the reference to the discipline's document. A reservation is an architectural
instruction and is drawn at architectural weight; its *contents* are not.

**Rationale.** The distinction between "space reserved" (the architect's decision, dimensioned) and
"what goes in it" (another discipline's decision, referenced) is the interface, and it is the thing
most often left implicit.

**Validation.** `V-4.15.020`: every declared reservation is dimensioned and levelled and names its
discipline and document.

### ADOS-4.15.030 — Builder's work openings

**Decision.** Every opening in structure or fabric required by another discipline shall be shown on
the architectural drawing with: position dimensioned to grid, size, level, the requiring discipline,
and a reference to the schedule of builder's work. Openings shall not be shown without a size.

**Rationale (R).** Builder's work openings are formed early and are expensive to add later. They are
also the classic case of information owned by one party and executed by another, which is exactly
where `ADOS-2.8.030` applies.

**Validation.** `V-4.15.030`: every builder's work opening carries all five fields and appears in the
schedule; schedule and drawing sets are identical.

### ADOS-4.15.040 — Coordination status annotation

**Decision.** Where a cross-discipline interface is not yet coordinated at the time of issue, it
shall be marked with a hold (`ADOS-2.6.080`) naming the parties and the resolution date. It shall not
be drawn as resolved.

**Validation.** `V-4.15.040`: interfaces listed as uncoordinated in the coordination record carry a
hold marking on every drawing that shows them.

---

## 4.16 Symbol inventory

### ADOS-4.16.010 — The default symbol set ⚠

**Decision.** The following symbol set is the ADOS default. A project's symbol register
(`ADOS-4.9.050`) shall be a subset of this set plus any symbols added by a jurisdiction overlay, to
a total of 30. Every symbol satisfies `ADOS-4.9.040`.

| # | Token | Symbol | Meaning |
|---|---|---|---|
| 1 | `SY-NORTH` | Circle with a filled half-arrow | North point |
| 2 | `SY-GRID` | 10 mm circle with a label | Grid reference |
| 3 | `SY-SECT` | Cut line with arrows and a 20 mm bubble | Section marker |
| 4 | `SY-DET` | Enclosure with leader to a 20 mm bubble | Detail marker |
| 5 | `SY-IELEV` | Quartered circle with arrows | Interior elevation marker |
| 6 | `SY-NOTE` | 5 mm hexagon with a number | Sheet note tag |
| 7 | `SY-REV` | 5 mm triangle with a revision code | Revision tag |
| 8 | `SY-LEVEL-P` | 3.5 mm half-filled triangle with a value | Level, in plan |
| 9 | `SY-LEVEL-S` | Horizontal line with a value and a tick | Level, in section or elevation |
| 10 | `SY-DOOR` | Leaf arc and leaf line | Door swing |
| 11 | `SY-SLIDE` | Leaf line with a direction arrow | Sliding door |
| 12 | `SY-WIN-OP` | Dashed triangle apex at the hinge | Window opening direction |
| 13 | `SY-STAIR-UP` | Arrow with `UP` | Stair direction |
| 14 | `SY-FALL` | Arrow with a gradient value | Fall direction |
| 15 | `SY-RWO` | Circle with a cross | Rainwater outlet |
| 16 | `SY-FD` | Filled square on the door line | Fire door position |
| 17 | `SY-FC` | Heavy dashed line with an end tick | Fire compartment line |
| 18 | `SY-CB` | Short heavy dash across a cavity | Cavity barrier |
| 19 | `SY-MJ` | Double line with an offset tick | Movement joint |
| 20 | `SY-AP` | Square with a diagonal | Access panel |
| 21 | `SY-BWO` | Rectangle with a diagonal cross and a size | Builder's work opening |
| 22 | `SY-RESV` | Dash-dot enclosure with a hatch | Service zone reservation |
| 23 | `SY-SETOUT` | Circle with cross-hairs and coordinates | Setting-out point |
| 24 | `SY-BREAK` | Zig-zag across the element | Break line |
| 25 | `SY-MATCH` | Heavy dashed line with a bubble | Match line |
| 26 | `SY-SCALE` | Divided bar with a labelled zero | Graphic scale bar |
| 27 | `SY-PROJ` | Truncated cone in two views | Projection method |
| 28 | `SY-HOLD` | Enclosed `H-nnn` | Hold marker |
| 29 | `SY-EXCL` | `T1` hatch with a boundary | Excluded scope area |
| 30 | `SY-GEN` | Enclosed `AI` with a corner tick | Machine-generated content marker |

**Validation.** `V-4.16.010`: project symbol register ⊆ default set ∪ overlay; total ≤ 30; every
symbol used appears in the register and in the legend.

### ADOS-4.16.020 — Symbol modification prohibited

**Decision.** A symbol's geometry shall not be modified per project. Where a project needs a
distinction the set does not carry, a symbol shall be added to the register, not an existing one
altered.

**Rationale.** Readers carry symbol recognition between projects. A modified symbol is worse than a
new one because it is confidently misread.

**Validation.** `V-4.16.020`: symbol geometry hashes match the library.

---

## 4.17 Summary of Volume 4

1. Line weight encodes depth, monotonically, in three tiers at factor 2: 0.18 / 0.35 / 0.70.
2. Four line types, defined in printed millimetres, valid at every scale.
3. Twelve scales, one per drawing class per project, with a resolvable feature size that determines
   what may be drawn.
4. Dimensions are commitments: closed chains, declared reference faces, explicit tolerance and
   provenance, no restated values.
5. Leaders and tags reference; they do not describe.
6. Four reference marker types with fixed two-field bubbles and reciprocal references.
7. Eight hatches maximum, defined in printed pitch, applied by scale, with poché below 1:50.
8. Stairs, ramps, curves, slopes and non-orthogonal grids carry their setting-out method, not only
   their shape.
9. Other disciplines' content is background and referenced; reservations and builder's work
   openings are architectural instructions and are dimensioned.
10. Thirty symbols, unmodified, all in the legend, preferably on the sheet.

---

*Continue to [Volume 5 — Document Types](ADOS-V5-Document-Types.md).*
