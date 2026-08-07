# Practice Template System (PTS)

**Edition 1.0 · A document template system for a contemporary architecture practice.**

---

## What this is

A complete, buildable design system from which every document a practice issues can be generated
consistently — twelve templates across A4, A3, A2 and A1, sharing one module, one type scale, one
tone ladder and one title block.

It is deliberately not a style. It is a set of decisions, each with a reason, from which the visual
result follows. The templates look calm because everything that does not carry meaning has been
removed, not because calm was the objective.

## Structure

| Part | File | Contents |
|---|---|---|
| 1 | [`PTS-01-System.md`](PTS-01-System.md) | Design philosophy · visual language · information hierarchy · layout system · typography · title block · spacing, alignment and grid · how the templates relate |
| 2 | [`PTS-02-Templates.md`](PTS-02-Templates.md) | The twelve templates, each in fourteen fields |
| 3 | [`PTS-03-Implementation.md`](PTS-03-Implementation.md) | Archicad · InDesign · Word · build order · acceptance test |
| — | [`machine/pts-tokens.json`](machine/pts-tokens.json) | Every constant, buildable. **Build from this, not from the prose.** |

## The twelve templates

| | Template | Family | Format |
|---|---|---|---|
| T01 | Cover Sheet | Sheet | A1 |
| T02 | Project Information Sheet | Sheet | A1 |
| T03 | Drawing Sheet — plans, sections, elevations | Sheet | A1 |
| T04 | Detail Drawing Sheet | Sheet | A1 / A3 |
| T05 | Specification Sheet | Document | A4 |
| T06 | Door / Window Schedule | Sheet | A3 |
| T07 | Meeting Minutes | Document | A4 |
| T08 | Site Visit Report | Document | A4 |
| T09 | Request for Information | Document | A4 |
| T10 | Revision Log | Sheet | A3 |
| T11 | Transmittal Sheet | Document | A4 |
| T12 | Presentation Board | Board | A1 |

## The system in one page

| | |
|---|---|
| **Module** | 10 mm; 5 mm sub-module is the placement lattice and the text baseline |
| **Margins** | Sheets 20 binding / 10 others · A4 20 L / 40 R / 25 T / 17 B |
| **Drawing area** | A0 969 × 806 · A1 621 × 559 · A2 564 × 325 · A3 390 × 202 |
| **Columns** | A0 5 × 185 · A1 6 × 95 · A2 6 × 85 · A3 4 × 90 · board 6 × 120, gutters 10 |
| **Type** | One grotesque family, √2 scale, 1.8 → 20 mm cap; body 2.5 mm; five sizes per sheet |
| **Measure** | 120 mm ≈ 67 characters, set by a 25 mm marginal column |
| **Line** | Three tiers at factor 2: 0.70 cut · 0.35 seen · 0.18 beyond |
| **Tone** | Six steps at 18 ΔL\*, four per sheet; text on `T0`/`T1` only |
| **Ink** | Monochrome. Colour may only be redundant |
| **Spacing** | 5 / 10 / 20 / 40 mm; between-group gap ≥ 2 × within-group gap |
| **Title block** | 180 mm wide at every format; four variants; no field ever typed |
| **Icons** | None in documents; the 30-symbol drawing set on drawings |

## Relationship to the standard

PTS is the **practice overlay and template layer** of the Architectural Documentation Operating
System in [`../ados/`](../ados/README.md).

- ADOS states *why* a value is what it is, and holds the derivations, the rule registry and the
  quality metrics.
- PTS states *what the value is on our sheets*, and is buildable.

Every number in PTS either cites its ADOS derivation or derives itself in Part 1. One deviation from
the standard is taken and recorded: A2 uses the small-format zoning template rather than the
large-format one, because at A2 the 180 mm band consumes 32 % of the frame width
(`machine/pts-tokens.json` → `pts.sheet.formats.A2.deviation`). The underlying ADOS rule is a
candidate for amendment; it has not been changed unilaterally.

## Using it

**To build the templates:** follow Part 3 §5, in order. Phase 1 is typeface calibration — do not
skip it, because every point size in the system is derived from a measured cap height and families
differ by up to 8 %.

**To specify a new template:** it inherits its family from Part 1 and is defined only by its
differences. Fill in the fourteen fields of Part 2. If the list of differences is long, the template
probably belongs to a family that does not exist yet.

**To check a set before issue:** run the acceptance test in Part 3 §5.1. Fourteen automated checks
and one ninety-second test with a person who has not seen the sheet.
