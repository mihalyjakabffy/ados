#!/usr/bin/env python3
"""PTS 1.0 — build the sheet and board templates as PDF.

    python3 docs/templates/pdf/build.py [outdir]

T01 Cover · T02 Project Information · T03 Drawing Sheet · T04 Detail Sheet ·
T12 Presentation Board. These five need absolute placement, real line weights
and greyscale fills, which is why they are PDFs and not Word templates.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ptspdf as P
from ptspdf import MEDIUM, MONO, REGULAR, Sheet, T, register_fonts, step, tone

CAP = {k: step(k)["cap"] for k in ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8")}


# ------------------------------------------------------------------ T01 ----

def t01_cover(out: Path) -> Path:
    s = Sheet(out / "PTS-T01-Cover-Sheet.pdf", "A1", title="Cover Sheet",
              subject="PTS 1.0 T01")
    s.frame()
    s.banner("S0", "Work in progress — not for construction")
    s.watermark("WORK IN PROGRESS")

    x = s.cx0
    # Band 1 — identity. 40 mm between bands: the major-part spacing.
    y = s.cy1 - 25
    s.caps(x, y, "Riverside Workshops", CAP["t7"], MEDIUM)
    s.text(x, y - 15, "2317   ·   Client name", CAP["t3"])
    s.text(x, y - 20, "Site address, town, postcode", CAP["t2"])

    # Band 2 — what this is and whether it may be used.
    y -= 75
    s.caps(x, y, "Technical Design Set", CAP["t6"])
    s.caps(x, y - 20, "S0   Work in progress", CAP["t6"], MEDIUM)
    s.text(x, y - 30, "Package 2317-PKG-0000   ·   Issued 0000-00-00   ·   Revision P01", CAP["t3"])

    # Band 3 — consultants left, declarations right, held at the foot.
    cols = s.spec["columns"]
    col = lambda i: s.cx0 + i * (cols["width"] + cols["gutter"])  # noqa: E731
    y = s.cy0 + 80

    s.block_heading(col(0), y, "Consultants")
    row = y - 10
    for role, org, code in [("Architect", "Originator name", "JKA"),
                            ("Structural", "—", "XXX"),
                            ("Services", "—", "XXX"),
                            ("Fire", "—", "XXX"),
                            ("Cost", "—", "XXX"),
                            ("Principal designer", "—", "XXX")]:
        s.caps(col(0), row, role, CAP["t2"])
        s.text(col(1), row, org, CAP["t2"])
        s.text(col(2) + 60, row, code, CAP["t2"], MONO, align="right")
        row -= 5

    s.block_heading(col(3), y, "Declarations")
    row = y - 10
    for label, value in [("Units", "millimetres; metres on site plans"),
                         ("Decimal separator", "full stop"),
                         ("Language", "en-GB"),
                         ("Sheet size", "A1"),
                         ("Smallest nominated issue size", "A1"),
                         ("Orientation", "north within 45° of sheet-up"),
                         ("Datum", "project +0.000 = 118.450 Baltic"),
                         ("Coordinate system", "EOV (EPSG:23700)"),
                         ("Dimension reference face", "structural; CLR where stated"),
                         ("Classification", "ISO 12006-2 conformant"),
                         ("Conformance", "ADOS 1.0 Class B · PTS 1.0")]:
        s.caps(col(3), row, label, CAP["t2"])
        s.text(col(4) + 34, row, value, CAP["t2"])
        row -= 5

    s.text(x, s.cy0,
           "This set is issued for the purpose stated above and for no other. Read with the drawing "
           "register. Do not scale from any drawing; work to figured dimensions only. "
           "© Originator name. Confidential.", CAP["t1"])

    s.title_block(sheet_title="Cover Sheet", sheet_number="A0.001",
                  scale="—", status="S0", revision="P01",
                  container_id="2317-JKA-ZZ-XX-DR-A-0001", nominated="A1 / issue A1")
    s.save()
    return Path(s.c._filename)


# ------------------------------------------------------------------ T02 ----

def t02_project_information(out: Path) -> Path:
    s = Sheet(out / "PTS-T02-Project-Information-Sheet.pdf", "A1",
              title="Project Information Sheet", subject="PTS 1.0 T02")
    s.frame()
    s.grid_references()
    s.banner("S0", "Work in progress — not for construction")

    cols = s.spec["columns"]
    col = lambda i: s.cx0 + i * (cols["width"] + cols["gutter"])  # noqa: E731
    top = s.cy1

    # --- line tiers, drawn at the widths they specify ----------------------
    y = top
    s.block_heading(col(0), y, "Line tiers")
    y -= 10
    for tier, meaning in [("W3", "cut by this view's cut plane"),
                          ("W2", "seen, in front of the cut plane"),
                          ("W1", "beyond, hidden, reference")]:
        s.line(col(0), y + 1, col(0) + 22, y + 1, tier)
        s.text(col(0) + 26, y, f"{tier}  {P.TIER[tier]:.2f}", CAP["t2"], MONO)
        s.text(col(0), y - 5, meaning, CAP["t1"], grey=P.INK["secondary"])
        y -= 15

    # --- line types, at printed dash geometry ------------------------------
    y -= 5
    s.block_heading(col(0), y, "Line types")
    y -= 10
    for name, pattern, meaning in [
            ("L-CONT", None, "visible or cut edge"),
            ("L-DASH", [4.0, 2.0], "hidden, or above the cut plane"),
            ("L-DOT", [0.5, 1.5], "below the cut plane"),
            ("L-CENT", [12.0, 2.0, 0.5, 2.0], "centre line, grid, axis")]:
        s.line(col(0), y + 1, col(0) + 60, y + 1, "W2", dash=pattern)
        s.text(col(0), y - 5, f"{name} — {meaning}", CAP["t1"], grey=P.INK["secondary"])
        y -= 10

    # --- tones, as swatches ------------------------------------------------
    y -= 5
    s.block_heading(col(0), y, "Tone ladder")
    y -= 10
    for token in ("T0", "T1", "T2", "T3", "T4", "T5"):
        s.rect(col(0), y - 2, 18, 9, tier="W1", fill_tone=token)
        s.text(col(0) + 22, y + 1, token, CAP["t2"], MONO)
        s.text(col(0) + 34, y + 1,
               f"L* {T['ink']['tones'][token]['L']}   "
               f"{T['ink']['tones'][token]['use']}", CAP["t1"], grey=P.INK["secondary"])
        y -= 10

    # --- hatches, at printed pitch ----------------------------------------
    y = top
    s.block_heading(col(2), y, "Hatches")
    y -= 10
    for token, angle, pitch in [("H-CONC", 45, 1.5), ("H-MSNR", 45, 2.0),
                                ("H-INSU-R", 45, 1.5), ("H-INSU-Q", 0, 3.0),
                                ("H-TIMB-S", 30, 1.0), ("H-TIMB-E", 45, 2.5),
                                ("H-METL", 0, 0), ("H-EART", 45, 2.0)]:
        _hatch_swatch(s, col(2), y - 2, 34, 9, angle, pitch, token)
        s.text(col(2) + 38, y + 1, token, CAP["t2"], MONO)
        s.text(col(2) + 74, y + 1, f"{pitch:g} mm" if pitch else "solid",
               CAP["t1"], grey=P.INK["secondary"])
        y -= 10

    # --- symbols, at printed size -----------------------------------------
    y -= 5
    s.block_heading(col(2), y, "Symbols")
    y -= 10
    _symbols(s, col(2), y)

    # --- declarations and abbreviations ------------------------------------
    y = top
    s.block_heading(col(4), y, "Declarations")
    y -= 10
    for label, value in [("Units", "mm"), ("Precision", "1 mm"),
                         ("Angles", "decimal degrees, 3 places"),
                         ("Datum", "+0.000 = 118.450 Baltic"),
                         ("Coordinates", "EOV (EPSG:23700)"),
                         ("Grid", "letters on the long axis, no I or O"),
                         ("Reference face", "structural; CLR where stated"),
                         ("Level prefixes", "FFL SSL SFL FCL TOS TOW SOF IL"),
                         ("Provenance", "(S) surveyed   (V) verify on site"),
                         ("Provisional", "TBC + hold reference")]:
        s.caps(col(4), y, label, CAP["t2"])
        s.text(col(4) + 44, y, value, CAP["t2"])
        y -= 5

    y -= 10
    s.block_heading(col(4), y, "Abbreviations")
    y -= 10
    abbrevs = ["FFL finished floor level", "SSL structural slab level",
               "FCL finished ceiling level", "SOF soffit level",
               "CLR clear dimension", "NOM nominal", "TBC to be confirmed",
               "TYP typical", "NTS not to scale", "DPC damp-proof course",
               "AVCL air and vapour control layer", "CB cavity barrier",
               "MJ movement joint", "RWO rainwater outlet",
               "FD30 fire door, 30 minutes", "AP access panel"]
    for i, a in enumerate(abbrevs):
        s.text(col(4) + (0 if i % 2 == 0 else 66), y - (i // 2) * 5, a, CAP["t2"])
    y -= (len(abbrevs) // 2) * 5 + 10

    s.block_heading(col(4), y, "Phase encoding")
    y -= 10
    for label, tier, dash, tn in [("Existing to remain", "W1", None, "T1"),
                                  ("To be removed", "W1", [4.0, 2.0], None),
                                  ("New", "W3", None, "T3"),
                                  ("Temporary", "W2", [4.0, 2.0], "T2")]:
        if tn:
            s.rect(col(4), y - 1.5, 16, 6, tier=None, fill_tone=tn)
        s.line(col(4), y - 1.5, col(4) + 16, y - 1.5, tier, dash=dash)
        s.line(col(4), y + 4.5, col(4) + 16, y + 4.5, tier, dash=dash)
        s.text(col(4) + 20, y, label, CAP["t2"])
        y -= 10

    s.notes_zone([
        ("Scope of this sheet",
         ["Project-wide conventions and declarations.", "Read before any other sheet in the set."]),
        ("General notes",
         ["01  Verify all dimensions on site before", "     fabrication.",
          "02  Report any discrepancy to the", "     originator before proceeding.",
          "03  Work to figured dimensions only."]),
        ("Read with", ["A0.001 cover", "A0.002 drawing register", "Specification"]),
    ])
    s.revision_register()
    s.key_plan()
    s.title_block(sheet_title="Project Information", sheet_number="A0.010",
                  scale="—", status="S0", revision="P01",
                  container_id="2317-JKA-ZZ-XX-DR-A-0010")
    s.save()
    return Path(s.c._filename)


def _hatch_swatch(s, x, y, w, h, angle_deg, pitch, token):
    """Draw a hatch at its printed pitch, clipped to the swatch."""
    import math
    s.c.saveState()
    p = s.c.beginPath()
    p.rect(x * P.MM, y * P.MM, w * P.MM, h * P.MM)
    s.c.clipPath(p, stroke=0, fill=0)
    if token == "H-METL":
        s.rect(x, y, w, h, tier=None, fill_tone="T5")
    elif pitch:
        s.c.setLineWidth(P.TIER["W1"] * P.MM)
        s.c.setStrokeGray(0)
        a = math.radians(angle_deg)
        span = w + h
        n = int(span / pitch) + 2
        for i in range(-n, n):
            off = i * pitch
            if angle_deg == 0:
                s.c.line(x * P.MM, (y + off) * P.MM, (x + w) * P.MM, (y + off) * P.MM)
            else:
                x0 = x + off / math.sin(a) if math.sin(a) else x
                s.c.line(x0 * P.MM, y * P.MM,
                         (x0 + h / math.tan(a)) * P.MM, (y + h) * P.MM)
        if token == "H-INSU-R":
            for i in range(-n, n):
                off = i * pitch
                x0 = x + off / math.sin(a)
                s.c.line(x0 * P.MM, (y + h) * P.MM,
                         (x0 + h / math.tan(a)) * P.MM, y * P.MM)
    s.c.restoreState()
    s.rect(x, y, w, h, tier="W2")


def _symbols(s, x, y):
    """The symbol set at printed size. A legend graphic at the wrong size does
    not match what the reader is looking for (PTS-02 T02)."""
    # grid bubble, 10 mm
    s.c.setLineWidth(P.TIER["W2"] * P.MM)
    s.c.setStrokeGray(0)
    s.c.circle((x + 5) * P.MM, y * P.MM, 5 * P.MM, stroke=1, fill=0)
    s.text(x + 5, y - 1.5, "A", CAP["t3"], align="centre")
    s.text(x + 13, y - 1.5, "SY-GRID  grid reference, 10 mm", CAP["t1"], grey=P.INK["secondary"])

    # reference bubble, 20 mm, two fields (ADOS-4.7.020)
    yy = y - 19
    s.c.circle((x + 10) * P.MM, yy * P.MM, 10 * P.MM, stroke=1, fill=0)
    s.line(x, yy, x + 20, yy, "W2")
    s.text(x + 10, yy + 5, "D3", CAP["t3"], align="centre")
    # The container field is the longer of the two and sits on the narrowing
    # chord of the lower half, so it is set a step down. Ranking it below the
    # view identifier is also correct: the reader looks for the view first.
    s.text(x + 10, yy - 5, "A7.014", CAP["t2"], align="centre")
    s.text(x + 24, yy - 1.5, "SY-DET  view above, container below", CAP["t1"], grey=P.INK["secondary"])

    # note tag, 5 mm hexagon
    import math
    yy = y - 38
    p = s.c.beginPath()
    for i in range(6):
        a = math.radians(60 * i - 30)
        px, py = x + 2.5 + 2.5 * math.cos(a), yy + 2.5 * math.sin(a)
        p.moveTo(px * P.MM, py * P.MM) if i == 0 else p.lineTo(px * P.MM, py * P.MM)
    p.close()
    s.c.setLineWidth(P.TIER["W1"] * P.MM)
    s.c.drawPath(p, stroke=1, fill=0)
    s.text(x + 2.5, yy - 1.2, "01", CAP["t1"], align="centre")
    s.text(x + 9, yy - 1.5, "SY-NOTE  sheet note tag, 5 mm", CAP["t1"], grey=P.INK["secondary"])

    # level symbol
    yy = y - 50
    p = s.c.beginPath()
    p.moveTo(x * P.MM, (yy + 3.5) * P.MM)
    p.lineTo((x + 3.5) * P.MM, (yy + 3.5) * P.MM)
    p.lineTo((x + 1.75) * P.MM, yy * P.MM)
    p.close()
    s.c.setFillGray(0)
    s.c.drawPath(p, stroke=0, fill=1)
    s.text(x + 6, yy, "FFL +7.200", CAP["t2"], MONO)
    s.text(x + 40, yy, "SY-LEVEL-P  signed, three decimals", CAP["t1"], grey=P.INK["secondary"])

    # north point
    s.north(x + 5, y - 66, 5)
    s.text(x + 13, y - 61.5, "SY-NORTH  the one pictorial mark", CAP["t1"], grey=P.INK["secondary"])


# ------------------------------------------------------------------ T03 ----

def t03_drawing_sheet(out: Path, fmt: str = "A1") -> Path:
    suffix = "" if fmt == "A1" else f"-{fmt}"
    s = Sheet(out / f"PTS-T03-Drawing-Sheet{suffix}.pdf", fmt,
              title=f"Drawing Sheet ({fmt})", subject="PTS 1.0 T03")
    s.frame()
    s.grid_references()
    s.banner("S0", "Work in progress — not for construction")
    s.watermark("WORK IN PROGRESS")
    s.column_guides()

    cols = s.spec["columns"]
    s.text(s.cx0, s.dy0 + 1,
           f"Setup guides: {cols['count']} columns × {cols['width']} mm, "
           f"{cols['gutter']} mm gutters, residual {cols['residual']} mm at the right. "
           "Guides locate views during production and do not appear on an issued sheet.",
           CAP["t1"], grey=P.INK["tertiary"])
    s.north(s.cx1 - 6, s.cy1 - 6, 5)

    if s.key is not None:
        s.notes_zone([
            ("Scope of this sheet",
             ["State what this sheet covers and what", "it excludes, and who owns the exclusion."]),
            ("Read with",
             ["A3.204 reflected ceiling plan", "A8.010 door schedule",
              "A8.020 room schedule", "A6.010 wall types"]),
            ("Sheet notes",
             ["01  ", "02  ", "03  "]),
            ("Legend",
             ["Only the states used on this sheet.", "Everything else on A0.010."]),
            ("Standard notes",
             ["See A0.010. Not repeated here."]),
        ])
        s.revision_register()
        s.key_plan()
    else:
        x, y, w, h = s.notes
        s.rect(x, y, w, h, tier="FRAME")
        s.block_heading(x + 2.5, y + h - 5, "Scope · read with · notes · legend")
        s.text(x + 2.5, y + h - 15,
               "Small-format template: the notes, key plan and revision register share "
               "the bottom band to the left of the title block.", CAP["t2"])
        s.scale_bar(x + 2.5, y + 9, 100)

    if s.key is not None:
        s.scale_bar(s.cx0, s.cy0, 100)

    s.title_block(sheet_title="Level 02 General Arrangement Plan",
                  sheet_number="A3.104", scale="1:100", status="S0",
                  revision="P01", container_id="2317-JKA-ZZ-02-DR-A-3104",
                  nominated=f"{fmt} / issue {fmt}")
    s.save()
    return Path(s.c._filename)


# ------------------------------------------------------------------ T04 ----

def t04_detail_sheet(out: Path) -> Path:
    s = Sheet(out / "PTS-T04-Detail-Sheet.pdf", "A1", title="Detail Sheet",
              subject="PTS 1.0 T04")
    s.frame()
    s.grid_references()
    s.banner("S0", "Work in progress — not for construction")
    s.watermark("WORK IN PROGRESS")

    # Three detail cells across, two down: 3 × 200 + 2 × 10 = 620 of 621.
    gap = 20.0                                   # view-to-view separation
    cell_w = (s.cx1 - s.cx0 - 2 * gap) / 3
    cell_h = (s.cy1 - s.cy0 - gap) / 2
    rows_y = [s.cy1 - cell_h, s.cy0]
    ids = [("D1", "Base and threshold", "1:5"), ("D2", "Window head", "1:5"),
           ("D3", "Window jamb", "1:5"), ("D4", "Window cill", "1:5"),
           ("D5", "Parapet", "1:5"), ("D6", "Roof edge", "1:5")]
    for i, (vid, title, scale) in enumerate(ids):
        cx = s.cx0 + (i % 3) * (cell_w + gap)
        cy = rows_y[i // 3]
        s.rect(cx, cy, cell_w, cell_h, tier="W1", dash=[1, 2])
        # view title: identifier bubble, title, scale (PTS-02 T04)
        by = cy + 10
        s.c.setLineWidth(P.TIER["W2"] * P.MM)
        s.c.setStrokeGray(0)
        s.c.circle((cx + 7.5) * P.MM, by * P.MM, 7.5 * P.MM, stroke=1, fill=0)
        s.text(cx + 7.5, by - 2, vid, CAP["t3"], MEDIUM, align="centre")
        s.caps(cx + 20, by + 2, title, CAP["t3"], MEDIUM)
        s.text(cx + 20, by - 3, f"{scale}   ·   TYPICAL — applies where the condition occurs",
               CAP["t1"], grey=P.INK["secondary"])
        s.line(cx, cy + 20, cx + cell_w, cy + 20, "HAIR", grey=P.INK["guide"])
        s.text(cx + 3, cy + cell_h - 5,
               "Context ≥ 100 mm beyond the junction, one datum, every layer annotated by "
               "reference,", CAP["t1"], grey=P.INK["tertiary"])
        s.text(cx + 3, cy + cell_h - 10,
               "and the five continuity lines — water, air, vapour, thermal, fire — each "
               "resolved or", CAP["t1"], grey=P.INK["tertiary"])
        s.text(cx + 3, cy + cell_h - 15,
               "explicitly terminated with a reference to where it continues.",
               CAP["t1"], grey=P.INK["tertiary"])

    s.notes_zone([
        ("Scope of this sheet",
         ["Typical envelope junctions.", "Assembly build-ups on A6.010."]),
        ("Read with",
         ["A6.010 wall types", "A4.001 elevations", "Specification"]),
        ("Referenced from",
         ["A3.100  ·  A3.102  ·  A3.104", "A4.001  ·  A4.010"]),
        ("Legend",
         ["Continuity lines are annotated,", "not distinguished by weight."]),
        ("Standard notes", ["See A0.010."]),
    ])
    s.revision_register()
    s.key_plan()
    s.title_block(sheet_title="Envelope Details — Openings",
                  sheet_number="A7.014", scale="AS SHOWN", status="S0",
                  revision="P01", container_id="2317-JKA-ZZ-XX-DR-A-7014")
    s.save()
    return Path(s.c._filename)


# ------------------------------------------------------------------ T12 ----

def t12_board(out: Path) -> Path:
    s = Sheet(out / "PTS-T12-Presentation-Board.pdf", "A1", family="board",
              title="Presentation Board", subject="PTS 1.0 T12")
    b = T["board"]
    cols = b["columns"]
    col = lambda i: s.fx0 + i * (cols["width"] + cols["gutter"])  # noqa: E731
    span = lambda n: n * cols["width"] + (n - 1) * cols["gutter"]  # noqa: E731

    # Title band, 40 mm. Type is derived from a 1.5-3 m viewing distance, which
    # is why a board cannot use sheet typography (PTS-01 §4.6).
    s.caps(s.fx0, s.fy1 - 20, "Board title", CAP["t8"], MEDIUM)
    s.line(s.fx0, s.fy1 - 30, s.fx1, s.fy1 - 30, "W1", grey=P.INK["guide"])

    # Primary image, 4 columns; text, 2 columns.
    top = s.fy1 - 50
    img_h = 250.0
    s.rect(col(0), top - img_h, span(4), img_h, tier="W1", dash=[2, 3])
    s.text(col(0) + 5, top - img_h / 2, "Primary image — 4 columns", CAP["t5"], grey=P.INK["tertiary"])

    s.caps(col(4), top - 10, "Section heading", CAP["t7"], MEDIUM)
    ty = top - 30
    for ln in ["One idea per board. A board carrying",
               "three arguments carries none: at three",
               "metres a viewer reads one thing and",
               "walks on.",
               "",
               "Body text is 7 mm cap, derived from",
               "h = d × 4.945 × 10⁻³ at 1.5 m."]:
        s.text(col(4), ty, ln, CAP["t5"])
        ty -= 15

    # Secondary images, three pairs of two columns.
    sec_top = top - img_h - 20
    sec_h = 130.0
    for i in range(3):
        s.rect(col(i * 2), sec_top - sec_h, span(2), sec_h, tier="W1", dash=[2, 3])
        s.text(col(i * 2) + 5, sec_top - sec_h / 2, f"Image {i + 2} — 2 columns",
               CAP["t5"], grey=P.INK["tertiary"])
        s.text(col(i * 2), sec_top - sec_h - 20, "Caption at 7 mm cap.", CAP["t5"])
        s.text(col(i * 2), sec_top - sec_h - 30,
               "Source · date · generated-image statement where applicable",
               CAP["t2"], grey=P.INK["tertiary"])

    # TB-B, 180 × 40, foot right.
    tx, ty2, tw_, th_ = s.fx1 - 180, s.fy0, 180, 40
    s.rect(tx, ty2, tw_, th_, tier="FRAME")
    s.caps(tx + 3, ty2 + th_ - 10, "Riverside Workshops", CAP["t3"], MEDIUM)
    s.text(tx + 3, ty2 + th_ - 15, "2317  ·  Concept design  ·  Board 1 / 4", CAP["t2"])
    s.text(tx + 3, ty2 + th_ - 20, "2317-JKA-ZZ-XX-PR-A-0001", CAP["t2"], MONO)
    s.text(tx + 3, ty2 + th_ - 25, "S0  ·  P01  ·  0000-00-00  ·  Originator name", CAP["t2"])
    s.caps(tx + 3, ty2 + 5, "Illustrative — not a construction document",
           CAP["t1"], MEDIUM)

    s.text(s.fx0, s.fy0 + 4,
           "Images align to column boundaries and to the 5 mm lattice. No bleed, no border, "
           "no shadow. A rendering is never included in a technical package and is never cited "
           "as a source of requirement.", CAP["t2"], grey=P.INK["tertiary"])
    s.save()
    return Path(s.c._filename)


BUILDERS = [t01_cover, t02_project_information, t03_drawing_sheet,
            t04_detail_sheet, t12_board]


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    register_fonts()
    made = [fn(out) for fn in BUILDERS]
    made.append(t03_drawing_sheet(out, "A3"))     # proves the small-format zoning
    for f in sorted(out.glob("*.pdf")):
        print(f"{f.name:44} {f.stat().st_size / 1024:7.1f} KB")
    print(f"\n{len(list(out.glob('*.pdf')))} sheets built in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
