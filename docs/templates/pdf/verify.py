#!/usr/bin/env python3
"""PTS 1.0 — verify the produced PDF sheets against the token file.

    python3 docs/templates/pdf/verify.py [dir]

The subject of every check is the *produced file*, not the code that wrote it.
A builder change that silently drops a setting is then caught, which a test of
the builder's own intentions would not be. The content streams are written
uncompressed for exactly this reason.

Exit status is 0 when every check passes.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ptspdf as P
from ptspdf import CAP_EM, INK, T, register_fonts, tone

TOL = 0.05          # mm, geometry
TOL_PT = 0.15       # pt
EPS = 1e-3          # grey level


# --------------------------------------------------------------- pdf reading

class Page:
    """Just enough PDF to inspect one uncompressed single-page document."""

    def __init__(self, path: Path):
        self.path = path
        self.raw = path.read_bytes()
        self.text = self.raw.decode("latin-1")
        self.media = self._media_box()
        self.stream = self._content_stream()
        self.ops = self._tokenise()

    def _media_box(self) -> tuple[float, float, float, float]:
        m = re.search(r"/MediaBox\s*\[\s*([\d.\-]+)\s+([\d.\-]+)\s+"
                      r"([\d.\-]+)\s+([\d.\-]+)\s*\]", self.text)
        if not m:
            raise ValueError("no MediaBox")
        return tuple(float(g) for g in m.groups())          # type: ignore[return-value]

    def _content_stream(self) -> str:
        ref = re.search(r"/Contents\s+(\d+)\s+0\s+R", self.text)
        if not ref:
            raise ValueError("no /Contents")
        obj = re.search(rf"(?<![\d]){ref.group(1)}\s+0\s+obj(.*?)endobj",
                        self.text, re.S)
        if not obj:
            raise ValueError("content object missing")
        body = obj.group(1)
        if "/Filter" in body.split("stream", 1)[0]:
            raise ValueError("content stream is filtered; build with "
                             "setPageCompression(0)")
        return body.split("stream", 1)[1].rsplit("endstream", 1)[0]

    def _tokenise(self) -> list[tuple[str, list]]:
        """(operator, operands) pairs. Strings become one operand each."""
        out: list[tuple[str, list]] = []
        operands: list = []
        for tok in re.finditer(
                r"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]*>|\[[^\]]*\]|"
                r"/[^\s/\[\]<>()]+|[-+]?[\d.]+|[A-Za-z'\"*]+",
                self.stream):
            s = tok.group(0)
            if re.fullmatch(r"[-+]?[\d.]+", s):
                try:
                    operands.append(float(s))
                except ValueError:
                    operands.append(s)
            elif s[0] in "(/<[":
                operands.append(s)
            else:
                out.append((s, operands))
                operands = []
        return out

    # -- derived views ----------------------------------------------------
    def state_walk(self):
        """Yield (op, operands, state) with the graphics state that applies.

        The CTM is tracked because the watermark is drawn in a translated and
        rotated space; without it every glyph in it reads as off the page.
        """
        st = {"w": None, "g": 0.0, "G": 0.0, "font": None, "size": None,
              "x": 0.0, "y": 0.0, "ctm": (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)}
        stack: list[dict] = []
        for op, a in self.ops:
            if op == "q":
                stack.append(dict(st))
            elif op == "Q" and stack:
                st = stack.pop()
            elif op == "cm" and len(a) >= 6:
                st["ctm"] = mat_mul(tuple(a[-6:]), st["ctm"])   # type: ignore[arg-type]
            elif op == "w" and a:
                st["w"] = a[-1]
            elif op == "g" and a:
                st["g"] = a[-1]
            elif op == "G" and a:
                st["G"] = a[-1]
            elif op == "Tf" and len(a) >= 2:
                st["font"], st["size"] = a[-2], a[-1]
            elif op == "Tm" and len(a) >= 6:
                st["x"], st["y"] = a[-2], a[-1]
            elif op == "Td" and len(a) >= 2:
                st["x"], st["y"] = st["x"] + a[-2], st["y"] + a[-1]
            yield op, a, dict(st)


def mat_mul(m: tuple, n: tuple) -> tuple:
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D,
            c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


def apply(ctm: tuple, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = ctm
    return a * x + c * y + e, b * x + d * y + f


def embedded_stems(pg: "Page") -> set[str]:
    """PostScript names of the faces whose glyph programs are in the file.

    A face named in a resource dictionary but not embedded is a font the
    reader has to find, and the document is then no longer the one that was
    designed (PTS-03 §1.1).
    """
    out = set()
    for m in re.finditer(r"/FontDescriptor\b", pg.text):
        obj_start = pg.text.rfind("obj", 0, m.start())
        obj_end = pg.text.find("endobj", m.start())
        body = pg.text[obj_start:obj_end]
        base = re.search(r"/FontName\s*/([A-Za-z0-9+\-]+)", body)
        if base and "/FontFile2" in body:
            out.add(base.group(1).split("+")[-1])
    return out


def decode_pdf_string(s: str) -> str:
    body = s[1:-1]
    return re.sub(r"\\([()\\])", r"\1", body)


# ------------------------------------------------------------------- checks

class Report:
    def __init__(self):
        self.rows: list[tuple[str, str, str, bool]] = []

    def add(self, sheet: str, check: str, ok: bool, detail: str = ""):
        self.rows.append((sheet, check, detail, ok))

    @property
    def failures(self):
        return [r for r in self.rows if not r[3]]

    def print(self):
        by_check: dict[str, list] = {}
        for sheet, check, detail, ok in self.rows:
            by_check.setdefault(check, []).append((sheet, detail, ok))
        for check in sorted(by_check, key=lambda c: int(re.match(r"P(\d+)", c).group(1))):
            rows = by_check[check]
            bad = [r for r in rows if not r[2]]
            mark = "FAIL" if bad else "PASS"
            print(f"[{mark}] {check}  ({len(rows) - len(bad)}/{len(rows)})")
            for sheet, detail, ok in rows:
                if not ok:
                    print(f"         {sheet}: {detail}")


LADDER = sorted(v["cap"] for v in T["type"]["steps"].values())
TIERS = sorted(set(P.TIER.values()))
TONES = sorted({tone(k) for k in T["ink"]["tones"]})
INKS = sorted(set(INK.values()) | set(TONES) | {0.0, 1.0})


# The PostScript names inside the embedded faces, mapped to the builder's
# handles so that a cap height can be recovered from a rendered point size.
FACES = {"Inter-Regular": P.REGULAR, "Inter-Medium": P.MEDIUM,
         "IBMPlexMono": P.MONO, "IBMPlexMono-Regular": P.MONO}


def expected_size(name: str) -> tuple[float, float]:
    """Page size in mm, from the token file, by what the filename declares."""
    if "Board" in name:
        return tuple(T["board"]["size"])                    # type: ignore[return-value]
    fmt = "A3" if name.endswith("-A3") else "A1"
    return tuple(T["sheet"]["formats"][fmt]["size"])        # type: ignore[return-value]


def check_sheet(path: Path, rep: Report) -> None:
    name = path.stem
    pg = Page(path)

    # P1 — page geometry is the ISO size the filename claims, landscape.
    w_mm, h_mm = pg.media[2] * P.PT, pg.media[3] * P.PT
    ew, eh = expected_size(name)
    ok = abs(w_mm - ew) < TOL and abs(h_mm - eh) < TOL
    rep.add(name, "P1 page size matches the token file", ok,
            f"{w_mm:.2f} × {h_mm:.2f} mm, expected {ew} × {eh}")

    # P2 — one page only. A sheet is one sheet.
    n_pages = len(re.findall(r"/Type\s*/Page(?![sB])", pg.text))
    rep.add(name, "P2 exactly one page", n_pages == 1, f"{n_pages} pages")

    # P3 — every face that actually sets glyphs is an embedded PTS face.
    used = set()
    for op, a, st in pg.state_walk():
        if op in ("Tj", "TJ", "'", '"') and st["font"]:
            used.add(st["font"].lstrip("/"))
    resources = dict(re.findall(r"/(F\d+(?:\+\d+)?)\s+(\d+)\s+0\s+R", pg.text))

    def face_of(tag: str) -> str:
        obj = resources.get((tag or "").lstrip("/"))
        body = re.search(rf"(?<![\d]){obj}\s+0\s+obj(.*?)endobj", pg.text, re.S)
        base = re.search(r"/BaseFont\s*/([A-Za-z0-9+\-]+)", body.group(1)) if body else None
        return (base.group(1) if base else "?").split("+")[-1]

    bad_faces = [f"{t}={face_of(t)}" for t in sorted(used)
                 if face_of(t) not in FACES or face_of(t) not in embedded_stems(pg)]
    rep.add(name, "P3 only the embedded PTS faces set glyphs", not bad_faces,
            ", ".join(bad_faces))

    # P4 — every rendered cap height is a step of the type scale, and none is
    #      below the 1.8 mm floor of the ladder.
    off_scale, too_small = [], []
    for op, a, st in pg.state_walk():
        if op in ("Tj", "TJ", "'", '"') and st["size"]:
            handle = FACES.get(face_of(st["font"] or ""), P.REGULAR)
            cap = st["size"] * P.PT * CAP_EM[handle]
            if not any(abs(cap - c) < 0.02 for c in LADDER):
                off_scale.append(f"{cap:.3f} mm")
            if cap < LADDER[0] - 0.02:
                too_small.append(f"{cap:.3f} mm")
    rep.add(name, "P4 every cap height is a step of the type scale",
            not off_scale, ", ".join(sorted(set(off_scale))[:6]))
    rep.add(name, "P5 no text below the smallest step", not too_small,
            ", ".join(sorted(set(too_small))[:6]))

    # P6 — every stroke width is one of the permitted tiers.
    widths = []
    for op, a, st in pg.state_walk():
        if op in ("S", "s", "B", "B*") and st["w"]:
            widths.append(st["w"] * P.PT)
    off_tier = [f"{w:.3f} mm" for w in widths
                if not any(abs(w - t) < 0.01 for t in TIERS)]
    rep.add(name, "P6 every stroke is a permitted line tier", not off_tier,
            ", ".join(sorted(set(off_tier))[:6]))

    # P7 — monochrome, and every ink level is a declared one.
    colour_ops = {op for op, _ in pg.ops} & {"rg", "RG", "k", "K", "sc", "scn",
                                             "SC", "SCN", "cs", "CS"}
    rep.add(name, "P7 greyscale only", not colour_ops, ", ".join(sorted(colour_ops)))
    off_ink = set()
    for op, a in pg.ops:
        if op in ("g", "G") and a:
            v = a[-1]
            if not any(abs(v - i) < EPS for i in INKS):
                off_ink.add(f"{v:.4f}")
    rep.add(name, "P8 every ink level is on the tone ladder", not off_ink,
            ", ".join(sorted(off_ink)[:6]))

    # P9 — nothing is drawn outside the sheet frame.
    if "Board" in name:
        m = T["board"]["margins"]["all"]
        fx0, fy0, fx1, fy1 = m, m, ew - m, eh - m
    else:
        mg = T["sheet"]["margins"]
        fx0, fy0 = mg["binding"], mg["bottom"]
        fx1, fy1 = ew - mg["right"], eh - mg["top"]
    outside = []
    for op, a, st in pg.state_walk():
        pts: list[tuple[float, float]] = []
        if op in ("m", "l") and len(a) >= 2:
            pts = [(a[-2], a[-1])]
        elif op == "re" and len(a) >= 4:
            x, y, w, h = a[-4:]
            pts = [(x, y), (x + w, y + h)]
        elif op == "c" and len(a) >= 6:
            pts = [(a[-6], a[-5]), (a[-4], a[-3]), (a[-2], a[-1])]
        elif op in ("Tj", "TJ") and st["font"]:
            pts = [(st["x"], st["y"])]
        for px, py in pts:
            ux, uy = apply(st["ctm"], px, py)
            x, y = ux * P.PT, uy * P.PT
            if not (fx0 - TOL <= x <= fx1 + TOL and fy0 - TOL <= y <= fy1 + TOL):
                outside.append(f"{op} at {x:.1f},{y:.1f}")
    rep.add(name, "P9 every mark is inside the frame", not outside,
            "; ".join(outside[:4]) + (f" (+{len(outside) - 4})" if len(outside) > 4 else ""))

    # P10 — the title block is where the token file puts it, at 180 mm.
    if "Board" not in name:
        fmt = "A3" if name.endswith("-A3") else "A1"
        spec = T["sheet"]["formats"][fmt]
        tb_h = 90 if spec["template"] == "large" else spec["band_height"]
        tx = (ew - T["sheet"]["margins"]["right"] - 180)
        ty = T["sheet"]["margins"]["bottom"]
        found = any(op == "re" and len(a) >= 4
                    and abs(a[-4] * P.PT - tx) < TOL and abs(a[-3] * P.PT - ty) < TOL
                    and abs(a[-2] * P.PT - 180) < TOL and abs(a[-1] * P.PT - tb_h) < TOL
                    for op, a in pg.ops)
        rep.add(name, "P10 title block is 180 mm at the sheet corner", found,
                f"expected {tx:.0f},{ty:.0f} 180×{tb_h}")

    # P11 — the identity fields a reader searches on are actually present.
    strings = "".join(decode_pdf_string(a[-1])
                      for op, a in pg.ops
                      if op == "Tj" and a and isinstance(a[-1], str)
                      and a[-1].startswith("("))
    if "Board" in name:
        wanted = ["P01", "2317"]
    else:
        wanted = ["P01", "S0", "2317-JKA"]
    missing = [w for w in wanted if w not in strings]
    rep.add(name, "P11 identity fields present", not missing, ", ".join(missing))

    # P12 — no text sits on a fill dark enough to lose it (PTS-01 §2.3: text
    #       on T0 or T1 only). Filled rects are compared against text origins.
    fills = []
    pending_rect = None
    for op, a, st in pg.state_walk():
        if op == "re" and len(a) >= 4:
            pending_rect = a[-4:]
        elif op in ("f", "f*", "B", "B*", "b", "b*"):
            if pending_rect:
                x, y, w, h = (v * P.PT for v in pending_rect)
                fills.append((min(x, x + w), min(y, y + h),
                              max(x, x + w), max(y, y + h), st["g"]))
            pending_rect = None
        elif op in ("S", "s", "n", "W", "W*"):
            # A path painted without a fill must not leave its rectangle
            # behind to be paired with the next fill operator.
            pending_rect = None
    dark = [f for f in fills if f[4] < tone("T1") - EPS]
    clash = []
    for op, a, st in pg.state_walk():
        if op in ("Tj", "TJ") and st["font"]:
            ux, uy = apply(st["ctm"], st["x"], st["y"])
            x, y = ux * P.PT, uy * P.PT
            for x0, y0, x1, y1, g in dark:
                if x0 - TOL <= x <= x1 + TOL and y0 - TOL <= y <= y1 + TOL:
                    clash.append(f"text at {x:.0f},{y:.0f} on grey {g:.2f}")
    rep.add(name, "P12 no text on a tone below T1", not clash,
            "; ".join(clash[:4]))

    # P13 — baseline pitch. PTS-01 §7.2 sets the vertical rhythm as a 5 mm
    #       sub-module, which is a statement about the distance between
    #       consecutive baselines in a column, not about an absolute lattice
    #       the whole sheet is pinned to. Baselines are grouped by their left
    #       edge and consecutive gaps measured.
    sub = T["module"]["sub"]
    cols: dict[int, list[float]] = {}
    for op, a, st in pg.state_walk():
        if op in ("Tj", "TJ") and st["font"]:
            ux, uy = apply(st["ctm"], st["x"], st["y"])
            cols.setdefault(round(ux * P.PT, 1), []).append(uy * P.PT)
    gaps, off = 0, []
    for x, ys in cols.items():
        ys = sorted(set(round(v, 2) for v in ys))
        for lo, hi in zip(ys, ys[1:]):
            d = hi - lo
            if d > 60:          # a different block, not the next line
                continue
            gaps += 1
            if abs(d / sub - round(d / sub)) * sub > 0.3:
                off.append(f"{d:.2f} mm at x={x:.0f}")
    frac = len(off) / max(gaps, 1)
    rep.add(name, "P13 baseline pitch is a whole sub-module", not off,
            f"{len(off)} of {gaps} gaps off pitch: "
            + "; ".join(sorted(set(off))[:5]))


def main() -> int:
    register_fonts()
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "sheets"
    sheets = sorted(root.glob("*.pdf"))
    if not sheets:
        print(f"no PDFs in {root}")
        return 1
    rep = Report()
    for s in sheets:
        check_sheet(s, rep)
    rep.print()
    total, bad = len(rep.rows), len(rep.failures)
    print(f"\n{total - bad} of {total} checks pass across {len(sheets)} sheets.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
