# Volume 6 — BIM Standards

**ADOS 1.0 · Volume 6 · The authoring and publishing configuration required to produce conforming
documentation deterministically.**

Volume 6 is the **tool overlay** layer (`ADOS-0.6.020`). Volumes 0–5 and 7–8 do not depend on it. A
practice changing authoring tool changes only this volume's implementation clauses; the decisions
remain.

---

## 6.1 The model as the source of truth

### ADOS-6.1.010 — Derivation requirement ⚠

**Purpose.** Make `ADOS-0.3.020` (one fact, one place) structurally enforced rather than
individually disciplined.

**Background.** §1.8. In a derived workflow, geometry and properties exist once and are projected;
consistency is a property of the mechanism rather than of the operator.

**Problem.** Hand-drawn 2-D content in a BIM project produces a second, invisible source of truth
that diverges silently at the first change.

**Decision.** Geometry and component property information in issued documentation shall be derived
from the project model. Manually drawn 2-D content shall be permitted only in the cases enumerated
in `ADOS-6.1.020`.

**Implementation.** Every view on every sheet is a live view of the model. 2-D detail content is
placed in *detail views* that are anchored to model locations, not in free-floating drawings.

**Exceptions.** See `ADOS-6.1.020`.

**Validation.** `V-6.1.010`: for every sheet, the ratio of model-derived geometry to total geometry
≥ the threshold in the project's BIM execution plan (default 0.90 for GA sheets, 0.50 for detail
sheets); free 2-D content outside permitted classes = 0.

**Common mistakes.** "Exploding" a view to fix a graphic problem — this converts a live projection
into a stale copy, and the copy will not be updated; drawing a missing element in 2-D on the sheet
rather than modelling it.

**Automation notes.** The audit is a model query; it shall run in CI on the authoring file, not on
the PDF.

### ADOS-6.1.020 — Permitted 2-D content ⚠

**Decision.** Manually drawn 2-D content is permitted only for:

1. **Detail enrichment**: fixings, sealants, membranes, laps and small components in details at
   1:10 and larger, where modelling them would exceed the level of information need
   (`ADOS-6.3.030`).
2. **Standard details** not derived from this project's model, subject to verification
   (`ADOS-5.16.040`).
3. **Diagrams** whose subject is not building geometry (strategy diagrams, process diagrams,
   assembly sequences).
4. **Survey and existing information** received in 2-D and not yet modelled, marked with its
   provenance (`ADOS-5.6.020`).
5. **Symbols and annotation**, which are 2-D by nature.

**Validation.** `V-6.1.020`: every 2-D element carries a class tag from the list; untagged 2-D
elements = 0.

### ADOS-6.1.030 — No geometry editing for graphic effect ⚠

**Decision.** Model geometry shall not be modified to improve a drawing's appearance. Where a view
requires a different representation, a *representation override* shall be used (`ADOS-6.7.020`).

**Rationale.** §1.9 T7. A geometry change made for one drawing propagates to every other drawing,
to quantities, to clash detection and to the IFC export.

**Validation.** `V-6.1.030`: model change records show no geometry change whose stated reason is
graphic.

---

## 6.2 Entity mapping

### ADOS-6.2.010 — Tool-to-ADOS entity map ⚠

**Purpose.** Bind the abstract entity model of `ADOS-2.1.010` to concrete tool objects so that
validation and generation can operate on either.

**Decision.** The following mapping shall be implemented. Where a tool has no equivalent, the
practice shall implement the entity by convention and document it.

| ADOS entity | Archicad | Revit | IFC (ISO 16739) |
|---|---|---|---|
| Project | Project + Project Info | Project Information | `IfcProject` |
| Set | Publisher Set root | Sheet set / Browser organisation | — (document management) |
| Package | Publisher Set | Sheet set + Transmittal | `IfcDocumentInformation` group |
| Container (sheet) | Layout | Sheet | `IfcAnnotation` / document reference |
| Container (document) | External document | External document | `IfcDocumentInformation` |
| View | Viewpoint / View Map entry placed on Layout | View placed on Sheet (viewport) | `IfcAnnotation` context |
| Region (sheet zone) | Master Layout element | Title block family region | — |
| Annotation | Text / Label / Dimension / Marker | Text / Tag / Dimension / Symbol | `IfcAnnotation` |
| Reference | Marker object with linked view | Callout / Section / Elevation / Reference | — |
| Fact (geometry) | Element | Element | `IfcProduct` |
| Fact (property) | Element property / IFC property | Parameter | `IfcPropertySet` |
| Revision | Change / Issue in Change Manager | Revision on Sheet | `IfcDocumentInformation.Revision` |
| Issue | Publisher run + Issue record | Transmittal | — |
| Level | Story | Level | `IfcBuildingStorey` |
| Zone | Zone / Renovation filter zone | Area / Scope box | `IfcSpatialZone` |
| Space | Zone | Room | `IfcSpace` |
| Type | Composite / Complex Profile / Object type | Family Type | `IfcTypeObject` |
| View template | View Setting combination (Model View Options, Layer Combination, Pen Set, Graphic Override, Renovation Filter) | View Template | — |
| Pen set | Pen Set | Line Weights table + Object Styles | — |
| Graphic override | Graphic Override Rule | Filter + View Override | — |
| Favorite | Favorite | Type + saved settings | — |
| Schedule | Interactive Schedule | Schedule/Quantities | `IfcElementQuantity` |

**Validation.** `V-6.2.010`: the practice's template exposes every row; missing implementations are
recorded as deviations.

### ADOS-6.2.020 — Round-trip identity ⚠

**Decision.** Every element shall carry a persistent, globally unique identifier that survives
export, re-import and federation (`IfcGloballyUniqueId` / GUID). Identifiers shall not be
regenerated by routine operations.

**Rationale.** Reference integrity, change tracking, clash resolution and asset handover all depend
on stable identity across the model's life.

**Validation.** `V-6.2.020`: GUID stability check between consecutive model versions; regenerated
GUIDs on unchanged elements = 0.

---

## 6.3 Level of information need

### ADOS-6.3.010 — Information need is defined by the document ⚠

**Purpose.** Bound modelling effort by documentation requirement rather than by ambition.

**Background.** Modelling effort is unbounded; documentation requirement is not. Effort spent on
model content that no document projects is invisible and is therefore pure cost.

**Problem.** Practices model to a "level of detail" defined by stage convention rather than by
output, producing both over-modelling (fixings modelled, never drawn) and under-modelling (a
required schedule field that no element carries).

**Decision.** Model content shall be determined by the *level of information need* table, which is
derived from the document set: each document type's required content (Volume 5) generates the
geometric and property requirements for the elements it projects.

**Implementation.** The table has one row per element class and one column per stage, containing:
geometric resolution required, property set required, and the documents that consume it.

**Validation.** `V-6.3.010`: every required content item in Volume 5 maps to a model requirement;
every model requirement maps to at least one consuming document. Unconsumed requirements = 0.

### ADOS-6.3.020 — Geometric resolution by scale ⚠

**Decision.** Element geometric resolution shall be sufficient for the largest scale at which the
element is drawn, and no greater. The binding value is `ADOS-4.2.030` (resolvable feature size).

| Largest drawn scale | Required geometric resolution |
|---|---|
| 1:200 | Mass and footprint |
| 1:100 | Element extents, single-layer |
| 1:50 | Element extents, layered where layers are drawn |
| 1:20 | Full layer build-up |
| 1:5 and larger | Layer build-up in the model; components and fixings by 2-D enrichment (`ADOS-6.1.020`) |

**Rationale.** Modelling below the resolvable feature size produces geometry that can never be seen
and costs performance, file size and coordination time.

**Validation.** `V-6.3.020`: for each element class, model resolution matches its largest drawn
scale row.

### ADOS-6.3.030 — Property requirements ⚠

**Decision.** Every property required by a schedule (Volume 5) shall exist as a model parameter on
the relevant element class, in the declared property set, with a declared data type and unit. A
schedule field that is not backed by a model parameter shall not exist.

**Validation.** `V-6.3.030`: schedule field set ⊆ model parameter set; unbacked fields = 0; type and
unit declared for every parameter.

---

## 6.4 Naming conventions

### ADOS-6.4.010 — File and container naming ⚠

**Decision.** Published container files shall be named:

```
<container_id>-<status>-<revision>.<ext>
2317-JKA-ZZ-02-DR-A-3104-A1-C03.pdf
```

Authoring files shall be named:

```
<project>-<originator>-<zone>-<discipline>-<model role>.<ext>
2317-JKA-ZZ-A-M3.pln
```

**Rationale.** The container identifier is already systematic and sortable (`ADOS-2.5.010`). Adding
status and revision to the file name makes the current state visible in a file listing, which is how
most recipients actually manage received documents.

**Validation.** `V-6.4.010`: file names match the grammar in `machine/ados-naming.ebnf`; name fields
equal the container's attributes.

**Common mistakes.** Spaces, non-ASCII characters, and `FINAL_v2_rev3_USE THIS ONE` suffixes. All
are prohibited: the revision field is the revision.

### ADOS-6.4.020 — View naming ⚠

**Decision.** Views shall be named:

```
<level or subject> - <view type> - <variant>
02 - GA PLAN - CONSTRUCTION
02 - RCP - COORDINATION
```

Names shall be systematic, sortable, and shall not contain the sheet number (views may move between
sheets).

**Validation.** `V-6.4.020`: view names match the grammar; names containing sheet numbers = 0.

### ADOS-6.4.030 — Type naming ⚠

**Decision.** Element types shall be named:

```
<type code>_<class>_<defining property>
WT-01_EXT WALL_CAVITY 300
DR-04_INT DOOR_SINGLE FD30S
```

The type code is the reference used on drawings (`ADOS-5.16.010`) and shall be the first field so
that types sort by code.

**Validation.** `V-6.4.030`: every type name starts with a registered type code; codes unique.

### ADOS-6.4.040 — Layer and classification ⚠

**Decision.** Layers (where the tool uses them) shall be used only for visibility control by
discipline and by phase, never for graphic control. Graphic control shall be by rule
(`ADOS-6.7.010`).

**Rationale.** Layer-driven graphics bind appearance to an editable, per-element property that no
rule governs. It is the mechanism by which a set becomes graphically inconsistent one element at a
time.

**Validation.** `V-6.4.040`: elements whose graphic properties are set by layer rather than by
rule = 0.

### ADOS-6.4.050 — Material naming

**Decision.** Materials shall be named `<classification code>_<material>_<variant>` and shall map to
a specification clause and to a hatch token (`ADOS-4.10.030`).

**Validation.** `V-6.4.050`: every material maps to a clause and a hatch token.

---

## 6.5 Coordinates, units and levels

### ADOS-6.5.010 — Units ⚠

**Decision.** The model shall use millimetres as its length unit with a display precision of 1 mm,
and shall not use rounded display of unrounded geometry. Angular precision shall be 0.01°. Area
precision 0.01 m². Volume precision 0.001 m³.

**Rationale.** Rounded display of unrounded geometry is the mechanism by which a model appears
dimensionally correct and is not: a wall at 2999.6 mm displays as 3000 and schedules as 3000, and
the error accumulates along a chain until a dimension fails to close.

**Validation.** `V-6.5.010`: unit and precision settings match; geometry snap audit reports
sub-millimetre coordinates on modelled elements = 0.

### ADOS-6.5.020 — Model origin ⚠

**Decision.** The model's internal origin shall be within 1 km of the modelled geometry. Geometry
placed at large distances from the origin shall be relocated.

**Rationale (P).** Floating-point precision degrades with distance from the origin; at tens of
kilometres, tools exhibit snapping failures, visual artefacts and unstable geometry. This is a
mechanical consequence of single-precision coordinate storage in graphics pipelines.

**Validation.** `V-6.5.020`: `max(|coordinate|) ≤ 1 000 000 mm` in the internal coordinate system.

### ADOS-6.5.030 — Shared coordinates ⚠

**Decision.** The project shall declare a survey point (a real-world coordinate and elevation) and a
project base point, and every model in the federation shall use the identical pair. The declaration
shall match the setting-out drawing (`ADOS-4.4.050`).

**Validation.** `V-6.5.030`: survey point coordinates identical across all federated models
(±0 mm); match the setting-out drawing values.

### ADOS-6.5.040 — Levels ⚠

**Decision.** Levels shall be defined once, named per `ADOS-2.5.050`, with elevations relative to the
project datum. Level names shall be identical across all federated models. Levels shall be created
only where they are a real building level; working planes shall not be created as levels.

**Rationale.** Level names and elevations are the primary federation key; a mismatch between
disciplines' levels makes cross-discipline views and clash detection unreliable.

**Validation.** `V-6.5.040`: level name and elevation sets identical across federated models.

### ADOS-6.5.050 — True north and project north

**Decision.** Both true north and project north shall be set in the model; project north shall equal
the declared drawing orientation (`ADOS-4.3.030`); the angle between them shall be recorded.

**Validation.** `V-6.5.050`: both set; project north matches the drawing orientation; angle recorded
and equal across the federation.

---

## 6.6 Classification and property sets

### ADOS-6.6.010 — Classification ⚠

**Decision.** Every element shall carry a classification code from the project's declared
classification system (a system conforming to ISO 12006-2, resolvable through bSDD where available),
recorded in a declared parameter.

**Rationale.** Classification is the key that binds an element to its specification clause, its cost
item, its maintenance regime and its statutory requirement. Without it, each of those bindings is
made by hand and by name-matching, which fails.

**Validation.** `V-6.6.010`: classification parameter populated on every element; codes resolve
against the declared system; unclassified elements = 0.

### ADOS-6.6.020 — Property sets ⚠

**Decision.** Properties shall be carried in declared property sets with declared names, data types
and units. The project shall publish its property set definitions as a machine-readable artefact,
and shall map them to standard IFC property sets where an equivalent exists.

**Validation.** `V-6.6.020`: property set definitions published and schema-valid; element properties
conform; unmapped custom properties recorded with a justification.

### ADOS-6.6.030 — Property provenance

**Decision.** Every property shall record its source class: design, manufacturer, test, survey, or
assumed. Assumed values shall carry the assumption.

**Rationale.** `ADOS-0.4.050`. This becomes critical at handover, where a manufacturer-declared
value and an assumed value look identical in a schedule.

**Validation.** `V-6.6.030`: source class populated for every property in the handover set.

---

## 6.7 Graphic control

### ADOS-6.7.010 — Appearance is a function of data ⚠

**Purpose.** Make graphic conformance automatic and auditable.

**Background.** §0.2.3. If appearance is set per element, conformance depends on every operator on
every element, which does not scale and cannot be verified. If appearance is derived by rule from
data, conformance is a property of the rule set.

**Problem.** Per-element overrides produce sets that are 95 % consistent, where the 5 % is
invisible until printed and impossible to find systematically.

**Decision.** The graphic appearance of every element in every view shall be determined by rule from
element data (class, type, phase, function, discipline, relationship to the cut plane). Per-element
graphic overrides shall not be used.

**Implementation.** Archicad: Graphic Override Rules driven by element classification and properties,
saved in Graphic Override Combinations bound to View Settings. Revit: View Filters driven by
parameters, saved in View Templates. In both, the rule set is defined once at template level.

**Exceptions.**
1. A per-view override applied to a *class* of elements (not to instances) via a filter, recorded in
   the view template.

**Validation.** `V-6.7.010`: per-element graphic override count = 0 (tool query); every observed
graphic state traces to a rule.

**Common mistakes.** Selecting three walls and changing their pen because they "read badly" — the
correct action is to fix the rule or the data.

**Automation notes.** The generator emits rules, never instance properties; the validator enumerates
instance overrides and fails on any.

### ADOS-6.7.020 — Representation overrides, not geometry edits ⚠

**Decision.** Where a view requires a different representation of an element (simplified, symbolic,
hidden, or shown beyond its true extent), it shall be achieved by view-level representation control:
detail level, view range, filters, cut plane settings, override rules. Geometry shall not change.

**Validation.** `V-6.7.020`: as `ADOS-6.1.030`.

### ADOS-6.7.030 — Detail level by scale ⚠

**Decision.** Each view's detail level shall be set from its scale per the table in `ADOS-6.3.020`,
by the view template, not per view.

**Validation.** `V-6.7.030`: detail level equals the template value for the view's scale on every
view; manual detail-level settings = 0.

### ADOS-6.7.040 — Scale-aware hatch ⚠

**Decision.** Hatch patterns shall be defined so that their *printed* pitch conforms to
`ADOS-4.10.020` at the scale at which they are used. Patterns defined in model units shall be used
only where the pattern represents real coursing (masonry at 1:20 and larger); all other patterns
shall be defined in sheet units.

**Rationale.** §1.3.3. A model-unit pattern is a real dimension and its printed pitch is
scale-dependent, so it conforms at one scale only.

**Validation.** `V-6.7.040`: for every hatch instance, printed pitch at the view's scale ≥ 0.5 mm and
≥ width + 0.30 mm.

### ADOS-6.7.050 — No manual override of derived values ⚠

**Purpose.** Prevent data corruption with a delayed fuse.

**Background.** Every major tool permits a dimension's text, a tag's content or a schedule cell to be
replaced with typed text. The result looks correct and is no longer connected to the model.

**Problem.** The overridden value does not update when the model changes. It is indistinguishable
from a live value on the printed sheet. It is found only when the discrepancy causes a site error.

**Decision.** Dimension text, tag content and schedule cell values shall not be manually overridden.
Where the derived value is wrong, the model shall be corrected.

**Exceptions.**
1. Dimension *prefixes and suffixes* that add information without replacing the value (`CLR`, `±5`,
   `(S)`) are permitted and shall be applied through the tool's prefix/suffix mechanism, never by
   replacing the text.

**Validation.** `V-6.7.050`: count of dimensions with replaced text = 0; count of tags with
overridden content = 0; count of schedule cells with typed content in derived fields = 0. All three
are direct tool queries and shall be build-blocking.

**Common mistakes.** Typing `3000` over a dimension reading `2996` instead of fixing the wall;
typing a room name into a tag.

### ADOS-6.7.060 — Pen sets ⚠

**Purpose.** Bind the Volume 4 line hierarchy to the tool's numeric pen system, systematically.

**Decision.** The pen table shall be structured so that the pen number encodes both its width and its
semantic group:

```
pen number = (group × 10) + width index
```

| Width index | Width (mm) |
|---|---|
| 1 | 0.13 (screen only) |
| 2 | 0.18 (W1) |
| 3 | 0.25 |
| 4 | 0.35 (W2) |
| 5 | 0.50 |
| 6 | 0.70 (W3) |
| 7 | 1.00 |
| 8 | 1.40 |
| 9 | 2.00 |

| Group | Pens | Use |
|---|---|---|
| 0 | 01–09 | New building fabric — the primary tier set |
| 1 | 11–19 | Background / existing to remain (printed at `T1` grey) |
| 2 | 21–29 | Annotation, dimensions, text, leaders |
| 3 | 31–39 | Demolition and temporary |
| 4 | 41–49 | Other disciplines' reference content |
| 5 | 51–59 | Sheet apparatus: frame, title block, markers, grid |
| 9 | 91–99 | Non-printing: construction lines, working geometry |

So pen 06 is 0.70 mm new-fabric cut; pen 24 is 0.35 mm annotation; pen 42 is 0.18 mm reference
content; pen 92 never prints.

**Rationale.** A pen number that encodes its own width and purpose is self-documenting; an operator
choosing a pen cannot choose a wrong width for a purpose without choosing an obviously wrong number.
Arbitrary pen tables require memorisation and produce errors.

**Validation.** `V-6.7.060`: pen table matches the formula; pens used per element class match the
class's group; non-printing pens produce no output.

### ADOS-6.7.070 — View templates ⚠

**Decision.** Every view shall be controlled by a view template. View settings shall not be modified
per view. The template set shall cover every view type × scale × purpose combination the project
uses, and shall be defined in the practice template, not per project.

**Implementation.** A view template binds: scale, detail level, model view options, layer/visibility
combination, pen set, graphic override combination, phase/renovation filter, annotation visibility,
view range and cut plane.

**Validation.** `V-6.7.070`: every view has a template assigned; views with local overrides = 0;
template count ≤ the declared set.

### ADOS-6.7.080 — Favorites and standard content ⚠

**Decision.** Element placement shall use Favorites (Archicad) or configured Types (Revit) drawn from
the practice library. Ad-hoc element configuration at placement time shall not be used.

**Rationale.** Placement-time configuration is how non-standard types proliferate; each one then
requires a schedule row, a specification clause and a graphic rule that nobody wrote.

**Validation.** `V-6.7.080`: element types not in the project type register = 0.

---

## 6.8 IFC and exchange

### ADOS-6.8.010 — IFC export as a deliverable ⚠

**Decision.** Every issued package shall include an IFC export (ISO 16739) of the model at the
package's status, conforming to the declared model view definition, with the declared property sets
mapped.

**Rationale.** The IFC export is the only deliverable readable without the authoring tool. It is the
archival and interoperability record (`ADOS-0.6.030`).

**Validation.** `V-6.8.010`: export present; schema-valid; element count matches the model within the
declared filter; property sets present.

### ADOS-6.8.020 — Export mapping declaration ⚠

**Decision.** The project shall declare its IFC mapping: element class → IFC entity + predefined
type; property → property set + property name + data type + unit; classification → classification
reference. The mapping shall be published with the export.

**Validation.** `V-6.8.020`: every exported element's entity and predefined type matches the mapping;
`IfcBuildingElementProxy` count = 0 (a proxy indicates an unmapped class).

### ADOS-6.8.030 — Export validation ⚠

**Decision.** Every export shall be validated before issue against: schema conformance, the project's
IDS (information delivery specification), geometric integrity (no missing or degenerate solids),
spatial containment (every element assigned to a storey and a space or a declared exception), and
GUID stability against the previous export.

**Validation.** `V-6.8.030`: all five checks pass; results recorded with the export.

### ADOS-6.8.040 — Federation ⚠

**Decision.** Federated models shall share the coordinate system (`ADOS-6.5.030`), level definitions
(`ADOS-6.5.040`) and grid, and shall be federated by reference, never by copying content between
discipline models.

**Validation.** `V-6.8.040`: coordinate, level and grid identity checks pass; copied cross-discipline
content = 0.

### ADOS-6.8.050 — Coordination records

**Decision.** Coordination issues shall be exchanged in BCF (BIM Collaboration Format) with a
viewpoint, a location, an assignee and a due date, and shall be tracked to closure. Coordination
comments shall not be recorded only in meeting minutes.

**Validation.** `V-6.8.050`: open issue count and age reported per package; issues without an
assignee = 0.

---

## 6.9 Sheets and views

### ADOS-6.9.010 — Sheet set structure ⚠

**Decision.** Sheets shall be organised in the tool's browser by series (`ADOS-2.5.030`) and the
browser organisation shall be defined in the template. Sheet numbers shall be generated from
container attributes, not typed.

**Validation.** `V-6.9.010`: browser structure matches the series definition; sheet number fields are
parameter-driven.

### ADOS-6.9.020 — Title block as a data-driven object ⚠

**Decision.** The title block shall be a single parametric object whose fields are bound to project
and container parameters. No title block field shall be typed on the sheet.

**Rationale.** A typed title block field is a manual restatement of a fact carried elsewhere
(`ADOS-2.2.030`) and is the most frequently wrong content in any set.

**Validation.** `V-6.9.020`: typed text objects within `Z-TITLE` = 0.

### ADOS-6.9.030 — One view, one purpose

**Decision.** A view shall be placed on at most one sheet. Where the same content is needed on two
sheets, a second view with its own template shall be created, or the sheets shall be reorganised.

**Rationale.** A view placed twice has one set of view settings serving two purposes and will
eventually be adjusted for one and broken for the other.

**Validation.** `V-6.9.030`: views with more than one placement = 0.

### ADOS-6.9.040 — View placement on the grid ⚠

**Decision.** Viewport origins shall be placed on the sub-module grid (`ADOS-3.3.030`) and view
extents shall align to the column structure (`ADOS-3.3.040`).

**Validation.** `V-6.9.040`: viewport origins satisfy `mod 5 = 0`; extents align to columns.

### ADOS-6.9.050 — Cropping and extents

**Decision.** View crop regions shall be set explicitly and shall be identical for corresponding
views across levels (so that a plan of level 01 and level 02 crop to the same extent and align when
overlaid).

**Rationale.** Non-aligned crops between levels prevent the reader from comparing levels by flipping
between sheets, which is the primary way plans are read.

**Validation.** `V-6.9.050`: crop extents identical across corresponding views; deviation = 0.

---

## 6.10 Schedules and quantities

### ADOS-6.10.010 — Schedules are model views ⚠

**Decision.** Every schedule shall be a live view of the model, placed on a sheet or exported at
publication. Schedules maintained in a spreadsheet shall not be issued as project documentation.

**Validation.** `V-6.10.010`: schedule content equals the model query at publication time.

### ADOS-6.10.020 — Schedule field binding

**Decision.** Every schedule field shall bind to a model parameter (`ADOS-6.3.030`). Calculated
fields shall have their formula recorded in the schedule's definition and shall be reproducible.

**Validation.** `V-6.10.020`: unbound fields = 0; formulas recorded.

### ADOS-6.10.030 — Schedule completeness filters ⚠

**Decision.** Every schedule shall be accompanied by an *exception schedule* listing elements of the
scheduled class excluded by the schedule's filters, so that filtered-out elements are visible rather
than silently absent.

**Rationale.** A filter is a silent omission mechanism (`ADOS-0.3.090`): a door missing from the
schedule because it lacked a parameter value looks exactly like a door that does not exist.

**Validation.** `V-6.10.030`: `|scheduled| + |excepted| = |class population|`.

### ADOS-6.10.040 — Sorting and grouping

**Decision.** Schedule sorting and grouping shall be defined in the schedule definition and shall
match `ADOS-3.12.020` (identifier first, then classification, then properties by frequency).

### ADOS-6.10.050 — Quantities ⚠

**Decision.** Quantities issued for cost purposes shall be generated from the model, shall state the
measurement rules applied, shall state the model version, and shall be accompanied by the exception
schedule of `ADOS-6.10.030`.

**Rationale.** A quantity without its measurement rule is not comparable with any other quantity,
and a quantity without an exception schedule understates by an unknown amount.

**Validation.** `V-6.10.050`: measurement rules stated; model version recorded; exceptions listed.

---

## 6.11 Publishing

### ADOS-6.11.010 — Publication is automated ⚠

**Decision.** Publication shall be executed by a saved, versioned publisher configuration that
produces the whole package in one operation. Manual per-sheet export shall not be used for issued
packages.

**Rationale.** Manual export produces per-sheet variation in settings, omissions, and files whose
names do not match their content — all of which are invisible until a recipient reports them.

**Validation.** `V-6.11.010`: publication log records a single run covering the package; per-file
settings identical.

### ADOS-6.11.020 — Output format ⚠

**Decision.** Issued documents shall be PDF, generated as vector output (never rasterised), with
fonts embedded as subsets, at a resolution of at least 600 dpi for any embedded raster content.
Archive copies shall be PDF/A-2b or PDF/A-3b.

**Validation.** `V-6.11.020`: no page contains a full-page raster image; all fonts embedded; raster
resolution ≥ 600 dpi; archive copies pass PDF/A validation.

### ADOS-6.11.030 — PDF metadata ⚠

**Decision.** Every published PDF shall carry metadata: title (= sheet title), subject (= container
identifier), author (= originator), keywords (= project code, status, revision, type), creation date,
producer (= generator name and version), and the ADOS conformance claim.

**Rationale.** Metadata is how documents are found, sorted and validated after they leave the
originator's system; it is also how automated checks identify what they are checking.

**Validation.** `V-6.11.030`: all fields populated; values match container attributes.

### ADOS-6.11.040 — PDF structure

**Decision.** Published PDFs shall include: searchable text for all text objects (no outlined text),
optional content groups (layers) for discipline and phase where the recipient benefits, document
bookmarks for multi-page documents, and internal hyperlinks for cross-references where the package
is issued digitally.

**Rationale.** `ADOS-0.4.080`. Hyperlinked cross-references reduce the navigation cost of
`ADOS-2.4.050` from tens of seconds to one click, which is the largest single improvement available
to a digital set.

**Validation.** `V-6.11.040`: text extraction returns all annotation text; bookmark count = page
count for documents; internal link count = reference count.

### ADOS-6.11.050 — Tone reproduction ⚠

**Decision.** The publication pipeline shall apply the declared transfer curve so that printed tones
achieve the target L* values of `ADOS-3.8.010` on the declared reference output device. The transfer
curve shall be established by printing and measuring a step wedge, and shall be revalidated annually
or on any change of device.

**Rationale.** Dot gain shifts nominal coverage by 10–20 %. A nominal 42 % fill may print at 55 %,
collapsing the separation between `T3` and `T4`. The tone ladder is defined in L* precisely so that
it can be calibrated rather than assumed.

**Validation.** `V-6.11.050`: measured L* of each tone within ±4 of target on the reference device;
calibration record dated within 12 months.

### ADOS-6.11.060 — Print-time transformations prohibited ⚠

**Decision.** Published files shall be produced at the authored size with no scaling, and recipients
shall be instructed to print at 100 %. Where a reduced size is issued, it shall be produced as a
separate, separately named, watermarked file (`ADOS-3.2.040`).

**Validation.** `V-6.11.060`: PDF page size equals the sheet size; no scaling flags set.

### ADOS-6.11.070 — Distribution record

**Decision.** Every publication shall produce an issue record (`ADOS-2.6.060`) automatically, and the
files shall be placed in the declared current-issue location with superseded files moved to archive
in the same operation (`ADOS-2.6.070`).

**Validation.** `V-6.11.070`: issue record exists and matches; current location contains exactly one
revision per live container.

---

## 6.12 Model quality assurance

### ADOS-6.12.010 — Model health checks ⚠

**Decision.** The following checks shall run before every issue, and shall block issue on failure:

| # | Check | Threshold |
|---|---|---|
| 1 | Elements not assigned to a level | 0 |
| 2 | Elements not classified (`ADOS-6.6.010`) | 0 |
| 3 | Elements with unresolved type (in-place / generic) | ≤ declared allowance, 0 at stage 4+ |
| 4 | Duplicate coincident elements | 0 |
| 5 | Geometry with sub-millimetre coordinates | 0 |
| 6 | Spaces not bounded / unplaced rooms | 0 |
| 7 | Manual overrides of derived values (`ADOS-6.7.050`) | 0 |
| 8 | Per-element graphic overrides (`ADOS-6.7.010`) | 0 |
| 9 | Views without a template (`ADOS-6.7.070`) | 0 |
| 10 | Unresolved references / broken callouts | 0 |
| 11 | Warnings in the tool's own warning list | ≤ declared allowance, trending down |
| 12 | File size and element count against the declared budget | within budget |

**Validation.** `V-6.12.010`: all checks pass or have a recorded, approved deviation.

### ADOS-6.12.020 — Check frequency

**Decision.** Health checks shall run automatically at least weekly during active production, and
before every issue. Results shall be recorded and trended.

**Rationale.** A model that fails 400 checks the day before an issue cannot be fixed. Trending
converts a crisis into maintenance.

### ADOS-6.12.030 — Model ownership

**Decision.** Every model shall have a named owner responsible for its health, its template
conformance and its issue readiness.

---

## 6.13 Tool-specific implementation notes

*Informative. These clauses record how the normative rules above are realised in each tool. They
change with tool versions and carry no independent requirement.*

### 6.13.1 Archicad

| ADOS rule | Archicad mechanism |
|---|---|
| `ADOS-6.7.010` | Graphic Override Rules + Combinations, driven by Classification and Properties; bound in View Settings |
| `ADOS-6.7.060` | Pen Sets, one per output purpose (issue, coordination, screen); pen numbering per the group formula |
| `ADOS-6.7.070` | View Settings combinations in the View Map: Layer Combination, Pen Set, Model View Options, Graphic Override Combination, Renovation Filter, Dimension Style |
| `ADOS-6.7.080` | Favorites, with the practice library as a linked hotlink or library part container |
| `ADOS-4.12.010` | Renovation Filters and Renovation Status; override rules keyed to status |
| `ADOS-6.9.010` | Layout Book organisation mirroring the series; Master Layouts per sheet size |
| `ADOS-6.9.020` | Autotext fields in the Master Layout bound to Project Info and Layout parameters |
| `ADOS-6.10.010` | Interactive Schedules with scheme criteria matching the class filters |
| `ADOS-6.11.010` | Publisher Sets, one per package, with saved format and naming rules |
| `ADOS-6.8.010` | IFC Translators, one per exchange purpose, with the mapping declared in the translator |
| `ADOS-6.2.020` | IFC GlobalId preserved through the translator; not regenerated on export |

### 6.13.2 Revit

| ADOS rule | Revit mechanism |
|---|---|
| `ADOS-6.7.010` | View Filters on parameters, applied in View Templates; Object Styles for class defaults |
| `ADOS-6.7.060` | Line Weights table (1–16) mapped to the ISO widths; Object Styles assigning weights per category and subcategory; Line Styles for annotation |
| `ADOS-6.7.070` | View Templates, assigned and locked; template-controlled properties marked as included |
| `ADOS-6.7.080` | Family Types in a controlled library; type catalogues for parametric variants |
| `ADOS-4.12.010` | Phases and Phase Filters with Graphic Overrides per phase status |
| `ADOS-6.9.010` | Browser Organisation by series; Sheet parameters driving sorting |
| `ADOS-6.9.020` | Title block family with labels bound to Project Information and Sheet parameters |
| `ADOS-6.10.010` | Schedules/Quantities views placed on sheets; calculated values recorded in the schedule definition |
| `ADOS-6.11.010` | Sheet Sets + saved print/export setups; batch export |
| `ADOS-6.8.010` | IFC Export setups with mapping tables; shared parameters mapped to property sets |
| `ADOS-6.5.030` | Survey Point and Project Base Point; shared coordinates acquired, never re-acquired per link |

### 6.13.3 Line weight mapping table

Both tools require a mapping from the tool's weight index to the ADOS widths. The mapping shall be
identical across all practice templates:

| ADOS tier | Width (mm) | Revit weight index | Archicad pen |
|---|---|---|---|
| screen only | 0.13 | 1 | x1 |
| W1 | 0.18 | 2 | x2 |
| intra-tier | 0.25 | 3 | x3 |
| W2 | 0.35 | 4 | x4 |
| intra-tier | 0.50 | 5 | x5 |
| W3 | 0.70 | 6 | x6 |
| apparatus | 1.00 | 7 | x7 |
| apparatus | 1.40 | 8 | x8 |
| reserved | 2.00 | 9 | x9 |

Weight indices 10–16 in Revit shall be left unassigned, so that an element using them is
immediately identifiable as non-conforming.

---

## 6.14 Worksharing

### ADOS-6.14.010 — Single model authority ⚠

**Decision.** Each element class shall be authored in exactly one model. Elements shall not be
duplicated between the models of one discipline, nor copied from another discipline's model
(`ADOS-6.8.040`).

**Rationale.** A duplicated element produces double quantities, spurious clashes, and two versions
of the truth that diverge on the first change.

**Validation.** `V-6.14.010`: cross-model duplicate detection by geometry and classification;
duplicates = 0.

### ADOS-6.14.020 — Model division ⚠

**Decision.** Where a project is divided into several models, the division shall be by *spatial zone*
or by *discipline*, never by drawing package or by team member. The division shall be declared and
shall be stable for the life of the project.

**Rationale.** A division by package binds the model structure to the documentation structure, which
changes; a division by team member binds it to the organisation, which changes faster. A spatial
division is a property of the building and is stable.

**Validation.** `V-6.14.020`: model division declared; changes to the division recorded as a project
event with an impact assessment.

### ADOS-6.14.030 — Ownership and editing ⚠

**Decision.** Every element shall have an owning model and an owning role. Editing an element outside
its ownership is prohibited. Where a change is needed, it shall be requested from the owner.

**Validation.** `V-6.14.030`: change logs show no edits outside ownership.

### ADOS-6.14.040 — Synchronisation discipline

**Decision.** Contributors shall synchronise with the central model at least daily and before any
issue. Local-only work older than one working day is a risk and shall be reported.

**Rationale.** The cost of a synchronisation conflict grows with the divergence period, and the
resolution of a large conflict is a manual merge — exactly the operation the derived workflow exists
to eliminate.

**Validation.** `V-6.14.040`: synchronisation log shows no contributor with local-only work exceeding
one working day during active production.

### ADOS-6.14.050 — Reference model currency ⚠

**Decision.** Every reference (linked) model shall record the version and date of the linked file,
and the record shall appear on any drawing that shows content from it.

**Rationale.** A drawing coordinated against a six-week-old structural model is not coordinated, and
nothing on the drawing says so.

**Validation.** `V-6.14.050`: linked model versions recorded; drawings showing linked content carry
the version and date; links older than the declared currency period reported.

### ADOS-6.14.060 — Federation cadence

**Decision.** The federated model shall be assembled and clash-tested at a declared cadence, at least
at every shared issue, and the results shall be recorded as BCF issues (`ADOS-6.8.050`) with owners
and due dates.

**Validation.** `V-6.14.060`: federation events recorded at the declared cadence; open issue age
trended.

---

## 6.15 Summary of Volume 6

1. Documentation is derived from the model; 2-D content is permitted only in five enumerated classes.
2. The abstract entity model maps to concrete tool objects, with stable GUIDs across the life of the
   project.
3. Modelling effort is bounded by documentation need, and geometric resolution by drawn scale.
4. Naming is systematic for files, views, types, materials; layers control visibility only.
5. Coordinates, levels and grid are federation keys and are identical across all models.
6. Appearance is a function of data, applied by rule; per-element overrides and manual value
   overrides are prohibited and machine-detectable.
7. Pen numbers encode width and semantic group by formula.
8. IFC export is a deliverable, validated against schema, IDS, geometry, containment and GUID
   stability.
9. Publication is a single automated operation producing files, metadata, issue record and
   supersession in one run.
10. Twelve model health checks block issue.
11. Worksharing has one authority per element, a stable spatial or discipline division, enforced
    ownership, daily synchronisation and recorded reference-model currency.

---

*Continue to [Volume 7 — AI Generation Specification](ADOS-V7-AI-Generation.md).*
