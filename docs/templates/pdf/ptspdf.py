#!/usr/bin/env python3
"""PTS 1.0 — PDF sheet builder library.

Draws the sheet- and board-family templates from machine/pts-tokens.json.

PDF is the right medium for these five: they need absolute placement to the
millimetre, real line weights as a depth encoding, and greyscale fills from the
tone ladder. Word can do none of those, which is why they are not Word
templates (see ../word/README.md).

Coordinates are millimetres from the lower-left corner of the page, matching
the token file. Text y is the baseline.
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.utils import ImageReader  # noqa: F401  (kept for callers)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

HERE = Path(__file__).resolve().parent
TOKENS = json.loads((HERE.parent / "machine" / "pts-tokens.json").read_text())
T = TOKENS["pts"]
FONT_DIR = HERE / "fonts"

MM = 72.0 / 25.4          # points per millimetre
PT = 25.4 / 72.0          # millimetres per point

REGULAR, MEDIUM, MONO = "Inter", "Inter-Medium", "PlexMono"

# Measured from the embedded faces at registration; the fallbacks are the
# published values. Point size is derived from cap height, never chosen
# (PTS-03 §1.1), so a wrong ratio puts the whole set off the type scale.
CAP_EM = {REGULAR: 0.7275, MEDIUM: 0.7275, MONO: 0.6980}


def register_fonts() -> None:
    faces = {REGULAR: "Inter-Regular.ttf",
             MEDIUM: "Inter-Medium.ttf",
             MONO: "IBMPlexMono-Regular.ttf"}
    for name, filename in faces.items():
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
        try:
            from fontTools.ttLib import TTFont as FTFont
            ft = FTFont(FONT_DIR / filename)
            cap = getattr(ft["OS/2"], "sCapHeight", None)
            if cap:
                CAP_EM[name] = cap / ft["head"].unitsPerEm
        except Exception:      # noqa: BLE001 — published value stands
            pass


def pt_for(cap_mm: float, font: str = REGULAR) -> float:
    """Point size that renders the given cap height in the given face."""
    return cap_mm / CAP_EM[font] / PT


def step(name: str) -> dict:
    return T["type"]["steps"][name]


def tone(token: str) -> float:
    """Tone token to a PDF grey level (1.0 = paper).

    The ladder is defined in CIE L* so that it converts for any output space
    rather than being asserted as a percentage (PTS-01 §2.3).
    """
    lstar = T["ink"]["tones"][token]["L"]
    y = ((lstar + 16) / 116) ** 3 if lstar > 8 else lstar / 903.3
    c = 1.055 * (y ** (1 / 2.4)) - 0.055 if y > 0.0031308 else 12.92 * y
    return max(0.0, min(1.0, c))


TIER = {"W1": T["line"]["tiers"]["W1"],
        "W2": T["line"]["tiers"]["W2"],
        "W3": T["line"]["tiers"]["W3"],
        "FRAME": T["line"]["permitted_rules"]["sheet_frame"],
        "DIV": T["line"]["permitted_rules"]["title_block_division"],
        "HAIR": T["line"]["permitted_rules"]["table_group_rule"]}

# Ink levels. Every mark on a sheet is set at one of these four, and each of
# the three non-black levels is a step of the tone ladder rather than a grey
# chosen at the moment of drawing. A system that permits an arbitrary grey
# acquires eleven of them within a year, and the reader stops being able to
# tell a rank from a rendering accident (PTS-01 §2.3, ADOS-3.7.010).
INK = {
    "primary": 0.0,          # content: all issued line work and text
    "secondary": tone("T4"),  # annotation subordinate to the content it labels
    "tertiary": tone("T3"),   # placeholder text standing in for project content
    "guide": tone("T2"),      # production apparatus, not part of an issued sheet
}


class Sheet:
    """A page with the PTS apparatus. All arguments in millimetres."""

    def __init__(self, path: Path, fmt: str, family: str = "sheet",
                 title: str = "", subject: str = ""):
        self.fmt = fmt
        self.family = family
        if family == "board":
            b = T["board"]
            self.w, self.h = b["size"]
            m = b["margins"]["all"]
            self.margins = {"left": m, "right": m, "top": m, "bottom": m}
        else:
            f = T["sheet"]["formats"][fmt]
            self.w, self.h = f["size"]
            m = T["sheet"]["margins"]
            self.margins = {"left": m["binding"], "right": m["right"],
                            "top": m["top"], "bottom": m["bottom"]}
            self.spec = f

        self.c = rl_canvas.Canvas(str(path), pagesize=(self.w * MM, self.h * MM))
        self.c.setPageCompression(0)      # keep the content stream inspectable
        self.c.setTitle(title)
        self.c.setSubject(subject)
        self.c.setAuthor("Originator name")
        self.c.setCreator("PTS 1.0 pdf builder")
        self.c.setKeywords("PTS 1.0, ADOS 1.0 Class B, template, monochrome")

        # Frame extents
        self.fx0 = self.margins["left"]
        self.fx1 = self.w - self.margins["right"]
        self.fy0 = self.margins["bottom"]
        self.fy1 = self.h - self.margins["top"]

        if family == "sheet":
            self._zones()

    # ---------------------------------------------------------------- zones
    def _zones(self) -> None:
        f = self.spec
        banner = T["sheet"]["banner_height"]
        gridref = T["sheet"]["gridref_height"]
        if f["template"] == "large":
            band = f["band_width"]
            self.bx0 = self.fx1 - band                 # right band
            self.dx0, self.dx1 = self.fx0, self.bx0 - T["sheet"]["band_gutter"]
            self.dy0 = self.fy0 + gridref
            self.dy1 = self.fy1 - banner
            self.tb = (self.bx0, self.fy0, band, 90)   # x, y, w, h
            self.rev = (self.bx0, self.fy0 + 90, band, 60)
            self.key = (self.bx0, self.fy1 - 60, band, 60)
            self.notes = (self.bx0, self.fy0 + 150, band, self.fy1 - 60 - (self.fy0 + 150))
            self.gy0 = self.fy0
        else:
            band_h = f["band_height"]
            self.dx0, self.dx1 = self.fx0, self.fx1
            self.dy0 = self.fy0 + band_h + gridref
            self.dy1 = self.fy1 - banner
            self.tb = (self.fx1 - 180, self.fy0, 180, band_h)
            self.notes = (self.fx0, self.fy0, self.fx1 - 180 - self.fx0, band_h)
            self.rev = None
            self.key = None
            self.gy0 = self.dy0 - gridref

        # Content keeps the mandated 10 mm clear of the drawing-area boundary
        # (ADOS-3.5.040), which also clears the zone-reference ring.
        clear = T["density"]["view_boundary_clearance_min"]
        self.cx0, self.cx1 = self.dx0 + clear, self.dx1 - clear
        self.cy0, self.cy1 = self.dy0 + clear, self.dy1 - clear

    # ------------------------------------------------------------ primitives
    def line(self, x1, y1, x2, y2, tier="W1", grey=0.0, dash=None):
        self.c.setLineWidth(TIER[tier] * MM)
        self.c.setStrokeGray(grey)
        self.c.setLineCap(0)
        self.c.setDash([d * MM for d in dash], 0) if dash else self.c.setDash()
        self.c.line(x1 * MM, y1 * MM, x2 * MM, y2 * MM)
        self.c.setDash()

    def rect(self, x, y, w, h, tier=None, fill_tone=None, dash=None):
        if fill_tone is not None:
            self.c.setFillGray(tone(fill_tone))
        if tier:
            self.c.setLineWidth(TIER[tier] * MM)
            self.c.setStrokeGray(0)
            self.c.setDash([d * MM for d in dash], 0) if dash else self.c.setDash()
        self.c.rect(x * MM, y * MM, w * MM, h * MM,
                    stroke=1 if tier else 0, fill=1 if fill_tone is not None else 0)
        self.c.setDash()
        self.c.setFillGray(0)

    def text(self, x, y, s, cap=None, font=REGULAR, align="left", grey=0.0,
             tracking=0.0):
        """Draw a string with its baseline at y. Alignment is computed from the
        measured width so that tracking is included in it."""
        cap = cap if cap is not None else step("t2")["cap"]
        size = pt_for(cap, font)
        w_pt = pdfmetrics.stringWidth(s, font, size)
        if tracking:
            w_pt += tracking * size * max(len(s) - 1, 0)
        if align == "right":
            xp = x * MM - w_pt
        elif align == "centre":
            xp = x * MM - w_pt / 2
        else:
            xp = x * MM
        t = self.c.beginText(xp, y * MM)
        t.setFont(font, size)
        t.setFillGray(grey)
        if tracking:
            t.setCharSpace(tracking * size)
        t.textOut(s)
        self.c.drawText(t)
        self.c.setFillGray(0)

    def width_of(self, s, cap, font=REGULAR, tracking=0.0) -> float:
        """Rendered width in millimetres, tracking included."""
        size = pt_for(cap, font)
        w = pdfmetrics.stringWidth(s, font, size)
        if tracking:
            w += tracking * size * max(len(s) - 1, 0)
        return w * PT

    def fit_cap(self, s, width_mm, cap, font=REGULAR, tracking=0.0) -> float:
        """The largest step on the ladder at or below `cap` whose rendering of
        `s` fits `width_mm`.

        Type is never scaled to fit (PTS-01 §5.3): a scaled step is off the
        ladder, so the reader loses the size-to-rank mapping that makes the
        ladder legible. It steps down instead, which is what a scale is for.
        The floor is t2 — below that a sheet title would fall under the
        2.5 mm cap-height minimum of ADOS-3.2.010 and stop being readable at
        arm's length, which is a worse failure than an overlong title.
        """
        ladder = sorted((v["cap"] for v in T["type"]["steps"].values()),
                        reverse=True)
        floor = step("t2")["cap"]
        for c in (v for v in ladder if v <= cap + 1e-9 and v >= floor - 1e-9):
            if self.width_of(s, c, font, tracking) <= width_mm:
                return c
        return floor

    def caps(self, x, y, s, cap=None, font=REGULAR, align="left", grey=0.0):
        """A label in capitals. Capitals set at text tracking close up at small
        sizes, so the 2 % of PTS-01 §5.3 is applied here."""
        self.text(x, y, s.upper(), cap, font, align, grey,
                  tracking=T["type"]["uppercase_tracking_percent"] / 100)

    # -------------------------------------------------------------- apparatus
    def frame(self) -> None:
        self.rect(self.fx0, self.fy0, self.fx1 - self.fx0, self.fy1 - self.fy0,
                  tier="FRAME")

    def grid_references(self) -> None:
        """Zone marks let a location be quoted verbally without a grid line
        nearby, which is how RFIs and site queries name a place.

        They sit in the outermost 5 mm of the drawing area — the ring that the
        view clearance of ADOS-3.5.040 keeps free — not at the page edge, which
        on a small-format sheet is the title block band.
        """
        if self.family != "sheet":
            return
        interval = T["sheet"]["gridref_interval"]
        ring = T["sheet"]["gridref_height"]
        letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"          # no I, no O
        cap = step("t2")["cap"]

        y = self.gy0 + ring / 2 - cap / 2
        n, x = 0, self.dx0
        while x + interval <= self.dx1:
            self.text(x + interval / 2, y, str(n + 1), cap, align="centre", grey=INK["secondary"])
            self.line(x + interval, self.gy0, x + interval, self.gy0 + ring,
                      "W1", grey=INK["guide"])
            n, x = n + 1, x + interval

        i, yy = 0, self.dy0
        while yy + interval <= self.dy1:
            self.text(self.dx0 + ring / 2, yy + interval / 2 - cap / 2,
                      letters[i], cap, align="centre", grey=INK["secondary"])
            self.line(self.dx0, yy + interval, self.dx0 + ring, yy + interval,
                      "W1", grey=INK["guide"])
            i, yy = i + 1, yy + interval

    def banner(self, status_code: str, status_name: str) -> None:
        """Any status other than authorised carries a banner and a watermark.
        The title block field is small and is missed; a watermark cannot be."""
        y = self.dy1
        sub = T["module"]["sub"]
        self.line(self.dx0, y, self.dx1, y, "W1", grey=INK["guide"])
        # Inset one sub-module: set at dx0 the first glyph sits on the frame
        # line, and a stroke touching a letter is read as part of the letter.
        self.caps(self.dx0 + sub, y + 3, f"{status_code}   {status_name}",
                  step("t3")["cap"], MEDIUM, grey=INK["secondary"])

    def watermark(self, text: str) -> None:
        self.c.saveState()
        self.c.setFillGray(tone("T1"))
        size = pt_for(step("t6")["cap"])
        self.c.setFont(MEDIUM, size)
        self.c.translate((self.dx0 + self.dx1) / 2 * MM, (self.dy0 + self.dy1) / 2 * MM)
        self.c.rotate(30)
        self.c.drawCentredString(0, 0, text)
        self.c.restoreState()

    def title_block(self, *, sheet_title, sheet_number, scale="1:100",
                    status="S0", status_name="Work in progress", revision="P01",
                    container_id="0000-XXX-ZZ-XX-DR-A-0000", nominated="A1 / issue A1",
                    north=False) -> None:
        """TB-L (180 × 90) or TB-S (180 × 60), per PTS-01 §6.2.

        Field order is by frequency of use, most frequent nearest the sheet
        corner: in a stack only the corner is visible, so the sheet number and
        revision sit there and a drawing can be found without extracting it.
        """
        x, y, w, h = self.tb
        large = h >= 90
        rows = [0, 15, 35, 50, 65, 75, 85, 90] if large else [0, 10, 25, 35, 45, 60]
        left_w = 135
        self.rect(x, y, w, h, tier="FRAME")
        # The right sub-column carries the sheet number and revision, which are
        # the two fields a stacked set is searched by. Its rows do not coincide
        # with the left column's, so a divider is drawn to the full width only
        # where it is also a boundary on the right; below that it stops at the
        # sub-column. A rule crossing an identifier reads as a strikethrough.
        r_top = y + h - (rows[2] if large else rows[1])
        r_bot = y + h - rows[5] if large else y
        eps = 1e-9
        for r in rows[1:-1]:
            yy = y + h - r
            inside = r_bot + eps < yy < r_top - eps
            self.line(x, yy, x + left_w if inside else x + w, yy, "DIV")
        self.line(x + left_w, r_bot, x + left_w, r_top, "DIV")
        if large:                               # number | revision | nominated
            for r in (rows[3], rows[4]):
                self.line(x + left_w, y + h - r, x + w, y + h - r, "DIV")

        def band(i):
            return y + h - rows[i + 1] + 2.5      # baseline inside row i

        t1, t2, t3, t4, t5 = (step(k)["cap"] for k in ("t1", "t2", "t3", "t4", "t5"))
        pad = 2.5
        trk = T["type"]["uppercase_tracking_percent"] / 100
        # The two variable-length fields step down the ladder rather than
        # overrun their column: a title is written by a project, not by the
        # system, and no length can be assumed.
        t_title = self.fit_cap(sheet_title.upper(), left_w - 2 * pad, t4,
                               REGULAR, trk)
        t_num = self.fit_cap(sheet_number.upper(), w - left_w - 2 * pad, t5,
                             MEDIUM, trk)
        if large:
            self.caps(x + pad, band(0) + 5, "PROJECT NAME", t3, MEDIUM)
            self.text(x + pad, band(0), "0000  ·  Client name", t2)
            self.caps(x + pad, band(1) + 5, sheet_title, t_title)
            self.caps(x + pad, band(2), f"SCALE   {scale}", t3)
            self.caps(x + 70, band(2), f"STATUS   {status}", t4)
            self.text(x + pad, band(3), "Drawn XX  ·  Checked XX  ·  Approved XX  ·  0000-00-00", t2)
            self.text(x + pad, band(4), container_id, t2, MONO)
            self.text(x + pad, band(5), "ORIGINATOR  ·  address  ·  contact", t2)
            self.text(x + pad, band(6),
                      "Conforms to ADOS 1.0 Class B · PTS 1.0 · DO NOT SCALE FROM THIS DRAWING · "
                      "WORK TO FIGURED DIMENSIONS ONLY · © Originator", t1)
            self.caps(x + left_w + pad, band(2), sheet_number, t_num, MEDIUM)
            self.caps(x + left_w + pad, band(3), revision, t4)
            self.text(x + left_w + pad, band(4), nominated, t2)
        else:
            self.caps(x + pad, band(0), "PROJECT NAME  ·  0000", t3, MEDIUM)
            self.caps(x + pad, band(1) + 5, sheet_title, t_title)
            self.caps(x + pad, band(2), f"SCALE   {scale}     STATUS   {status}", t3)
            self.text(x + pad, band(3), container_id, t2, MONO)
            self.text(x + pad, band(4),
                      "ORIGINATOR · Conforms to ADOS 1.0 Class B · PTS 1.0 · DO NOT SCALE", t1)
            # right column: number over revision, in the lower 35 mm
            self.line(x + left_w, y + 14, x + w, y + 14, "DIV")
            self.caps(x + left_w + pad, y + 20, sheet_number, t_num, MEDIUM)
            self.caps(x + left_w + pad, y + 5, revision, t4)
        if north:
            self.north(x + w - 14, y + h - 14, 5)

    def north(self, cx, cy, r) -> None:
        """A direction cannot be written, which is why this is the one
        pictorial mark the system permits in a document."""
        self.c.setLineWidth(TIER["W2"] * MM)
        self.c.setStrokeGray(0)
        self.c.circle(cx * MM, cy * MM, r * MM, stroke=1, fill=0)
        self.c.setFillGray(0)
        p = self.c.beginPath()
        p.moveTo(cx * MM, (cy + r) * MM)
        p.lineTo((cx - r * 0.4) * MM, (cy - r * 0.5) * MM)
        p.lineTo(cx * MM, (cy - r * 0.15) * MM)
        p.close()
        self.c.drawPath(p, stroke=0, fill=1)
        self.text(cx, cy + r + 1.5, "N", step("t2")["cap"], MEDIUM, align="centre")

    def scale_bar(self, x, y, denominator=100, divisions=5, unit_mm=10) -> None:
        """The stated ratio becomes false on reduction; a bar reduces with the
        drawing and stays true. Both are given (PTS-02 T03)."""
        for i in range(divisions):
            self.rect(x + i * unit_mm, y, unit_mm, 2,
                      tier=None, fill_tone="T5" if i % 2 == 0 else "T0")
        self.rect(x, y, divisions * unit_mm, 2, tier="W1")
        real = unit_mm * denominator / 1000
        self.text(x, y - 4, "0", step("t1")["cap"])
        self.text(x + divisions * unit_mm, y - 4,
                  f"{real * divisions:g} m", step("t1")["cap"], align="right")
        self.text(x, y + 6, f"1:{denominator}", step("t1")["cap"])

    def block_heading(self, x, y, label) -> None:
        self.caps(x, y, label, step("t3")["cap"], MEDIUM)

    def notes_zone(self, blocks) -> None:
        """Z-NOTES carries a fixed block order so a reader can jump to the block
        they need without reading the column (PTS-01 §4.3)."""
        if self.key is None:
            return
        x, y, w, h = self.notes
        cursor = y + h - 6
        for heading, lines in blocks:
            self.block_heading(x + 2.5, cursor, heading)
            cursor -= step("t3")["pitch"]
            for ln in lines:
                self.text(x + 2.5, cursor, ln, step("t2")["cap"])
                cursor -= 5
            cursor -= 5          # 10 mm between blocks against 5 mm within
        return cursor

    def revision_register(self, rows=6) -> None:
        if self.rev is None:
            return
        x, y, w, h = self.rev
        self.rect(x, y, w, h, tier="FRAME")
        self.caps(x + 2.5, y + h - 6, "REVISION", step("t3")["cap"], MEDIUM)
        cols = [0, 18, 44, 150, 165, 180]
        top = y + h - 10
        self.line(x, top, x + w, top, "DIV")
        for label, cx in zip(["Rev", "Date", "Description", "Aut", "Chk"], cols[:-1]):
            self.caps(x + cx + 1.5, top - 6, label, step("t1")["cap"], MEDIUM, grey=INK["secondary"])
        pitch = (top - 6 - y) / rows
        for i in range(rows):
            yy = top - 6 - i * pitch
            self.line(x, yy, x + w, yy, "HAIR", grey=INK["guide"])
        for cx in cols[1:-1]:
            self.line(x + cx, y, x + cx, top - 6, "HAIR", grey=INK["guide"])

    def key_plan(self) -> None:
        if self.key is None:
            return
        x, y, w, h = self.key
        self.rect(x, y, w, h, tier="FRAME")
        self.caps(x + 2.5, y + h - 6, "KEY PLAN", step("t3")["cap"], MEDIUM)
        # 60 x 60 minimum graphic; the current portion at T3, the rest at T1
        gx, gy, gw, gh = x + 2.5, y + 3, 60, 40
        self.rect(gx, gy, gw, gh, tier="W1", fill_tone="T1")
        self.rect(gx, gy, gw * 0.45, gh, tier="W2", fill_tone="T3")
        self.north(x + w - 14, y + h / 2 - 6, 5)

    def column_guides(self, label=True) -> None:
        """Setup guides. They locate views during production and are removed
        from an issued sheet; they are drawn here because this is a template."""
        f = self.spec if self.family == "sheet" else None
        cols = (f["columns"] if f else T["board"]["columns"])
        x = self.dx0 if f else self.fx0
        for i in range(cols["count"]):
            x0 = x + i * (cols["width"] + cols["gutter"])
            self.rect(x0, self.dy0 if f else self.fy0, cols["width"],
                      (self.dy1 - self.dy0) if f else (self.fy1 - self.fy0),
                      tier="W1", dash=[1, 2])
        if label:
            self.text(x, (self.dy0 if f else self.fy0) - 0,
                      "", step("t1")["cap"])

    def save(self) -> None:
        self.c.showPage()
        self.c.save()
