# PTS 1.0 — PDF sheet templates

The five sheet- and board-family templates, drawn from
[`../machine/pts-tokens.json`](../machine/pts-tokens.json). Not hand-drawn: a change to the system
is a change to the token file and a rebuild.

```
python3 docs/templates/pdf/build.py      # writes sheets/*.pdf
python3 docs/templates/pdf/verify.py     # 77 checks against the produced files
```

## What is here

| File | PTS | Format |
|---|---|---|
| `sheets/PTS-T01-Cover-Sheet.pdf` | T01 | A1 landscape |
| `sheets/PTS-T02-Project-Information-Sheet.pdf` | T02 | A1 landscape |
| `sheets/PTS-T03-Drawing-Sheet.pdf` | T03 | A1 landscape |
| `sheets/PTS-T03-Drawing-Sheet-A3.pdf` | T03 | A3 landscape |
| `sheets/PTS-T04-Detail-Sheet.pdf` | T04 | A1 landscape |
| `sheets/PTS-T12-Presentation-Board.pdf` | T12 | A1 landscape |

T03 is built at two formats from one function, which is the point of the format table: the
large-format sheet puts the apparatus in a 180 mm band down the right-hand edge, the small-format
sheet puts it in a 60 mm band along the foot, and nothing else about the sheet changes.

## Why these five are PDFs and the other seven are Word templates

These are the documents whose content is model-derived views positioned to the millimetre against a
drawn title block. They need three things Word cannot do: absolute placement, line weight as a depth
encoding, and greyscale fills taken from a tone ladder. See
[`../word/README.md`](../word/README.md) for the other side of the same decision.

A PDF is the right *proof* of these templates, not the right *production tool* for them. On a real
project T01 and T12 are InDesign documents and T03/T04 are Archicad layouts — see
[`../PTS-03-Implementation.md`](../PTS-03-Implementation.md) §2 and §3. What these PDFs give you is
the specification made literal: every zone, weight, tone, cap height and baseline at its true
printed size, so an implementation can be measured against something rather than argued about.

Print at 100 % — no "fit to page". A sheet printed at 94 % is a sheet whose 0.18 mm lines are
0.17 mm and whose 2.5 mm text is 2.35 mm, and the whole derivation stops holding.

## Fonts

**Inter** for text and **IBM Plex Mono** for identifiers, both under the SIL Open Font Licence, are
embedded as subsets in `fonts/`. Nothing needs installing to read or print these files.

Point sizes are not chosen. `ptspdf.register_fonts()` reads `OS/2.sCapHeight` from each face at
build time and derives the point size from the required cap height, so swapping in the practice's
licensed family (PTS-01 §5.1 recommends Söhne) is a matter of changing `REGULAR`/`MEDIUM`/`MONO`
and the filenames at the top of `ptspdf.py` — the sizes recalibrate themselves.

## Ink

Every mark is set at one of four ink levels, and the three that are not black are steps of the tone
ladder:

| Level | Tone | Use |
|---|---|---|
| `primary` | black | all issued line work and text |
| `secondary` | `T4` | annotation subordinate to the content it labels |
| `tertiary` | `T3` | placeholder text standing in for project content |
| `guide` | `T2` | production apparatus that is not part of an issued sheet |

This exists because the first version of the builder had eleven different greys in it, each chosen
at the moment of drawing and none of them meaning anything. Check P8 now fails the build if a grey
appears that is not one of these.

## Verification

`verify.py` parses the produced PDFs — the content streams are written uncompressed for exactly
that reason — rather than testing the builder's intentions.

| | Check |
|---|---|
| P1 | Page size matches the token file for its family |
| P2 | Exactly one page |
| P3 | Only the embedded PTS faces set glyphs |
| P4 | Every rendered cap height is a step of the type scale |
| P5 | No text below the smallest step |
| P6 | Every stroke is one of the permitted line tiers |
| P7 | Greyscale only — no `rg`, `k` or colour space operators |
| P8 | Every ink level is on the tone ladder |
| P9 | Every mark is inside the sheet frame |
| P10 | The title block is 180 mm at the sheet corner |
| P11 | The identity fields a reader searches on are present |
| P12 | No text sits on a tone below `T1` |
| P13 | Consecutive baselines in a column are a whole sub-module apart |

Current state: **77 checks pass across 6 sheets.**

P13 is the check that earned its place. Every other check passed while the sheets were built with
gaps of 4, 6, 7, 11, 12, 14 and 18 mm between baselines — a 5 mm lattice asserted in the
specification and nowhere present in the artefact. Nothing about that is visible in a screenshot;
it shows up as a page that feels slightly unresolved and cannot be said why. The check measures the
gap between consecutive baselines in a column rather than pinning every baseline to an absolute
grid, because the 5 mm sub-module is a statement about rhythm, not about registration.

## Two defects this work found in the standard itself

Drawing a specification is a good way to discover that it does not close. Both of these were
corrected in ADOS rather than worked around here:

| Found | Was | Now |
|---|---|---|
| A two-field reference bubble cannot be drawn | `ADOS-4.7.020`: 14 mm circle, both fields at 3.5 mm cap. A six-character container short form is 16.1 mm wide at that cap, in a 14 mm circle | 20 mm, upper field 3.5 mm, lower field 2.5 mm, with the diameter derived from the chord at the lower field's baseline |
| `H-INSU-R` exceeded the density ceiling | 1.0 mm cross-hatch pitch at 0.18 mm — about 33 % coverage against the 25 % ceiling of `ADOS-3.7.020` | 1.5 mm pitch |

The bubble is the more instructive of the two. The binding dimension for text inside a circle is not
the diameter but the chord at the text's own baseline, which is the narrowest line the glyph box
touches — `0.866 d` for a field placed at a quarter-diameter off centre. A rule can be internally
consistent, cited throughout, and still specify something no one can draw.

## Language

English (`en-GB`), matching the specification. The geometry is language-independent: for a
Hungarian set, translate the field labels in `build.py` and rebuild.
