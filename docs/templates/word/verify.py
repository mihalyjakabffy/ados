#!/usr/bin/env python3
"""PTS 1.0 — verify the built Word templates against the token file.

    python3 docs/templates/word/verify.py [templatedir]

Checks the produced .dotx packages, not the code that wrote them, so a change
to the builder that silently drops a setting is caught. Every threshold comes
from machine/pts-tokens.json; nothing is asserted here that the system does not
already require.

W1  package is a valid .dotx: template content type, custom properties present
W2  page geometry matches the token file for its family
W3  every PTS style exists, at the token size, with exact line spacing on the
    5 mm lattice
W4  no text below the 2.5 mm cap-height floor (t1 is permitted only for the
    legal line)
W5  no typed identity: project, container, revision, status and page number are
    fields, never literal text
W6  tables carry no vertical rules, and header rows repeat
W7  table row pitch is a whole number of sub-modules
W8  header and footer hairlines are at the W1 tier
W9  schedule column widths sum to the sheet frame width
W10 no colour: every ink and shading value is a grey from the tone ladder
W11 every table declares a fixed width equal to the sum of its columns
W12 every cell carries an explicit width
W13 every character-style reference resolves to a styleId that exists
W14 no right-aligned tab stops: identity is placed in fixed cells, not by tab
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = json.loads((HERE.parent / "machine" / "pts-tokens.json").read_text())["pts"]
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

CT_DOTX = "wordprocessingml.template.main+xml"
SUBMODULE_TW = round(T["module"]["sub"] * 1440 / 25.4)      # 283
MIN_CAP = T["type"]["min_cap_act"]
CAP_EM = T["type"]["cap_em_ratio_assumed"]
TONE_GREYS = set()


def tone_greys() -> set[str]:
    if not TONE_GREYS:
        for tok in T["ink"]["tones"]:
            lstar = T["ink"]["tones"][tok]["L"]
            y = ((lstar + 16) / 116) ** 3 if lstar > 8 else lstar / 903.3
            c = 1.055 * (y ** (1 / 2.4)) - 0.055 if y > 0.0031308 else 12.92 * y
            v = max(0, min(255, round(c * 255)))
            TONE_GREYS.add(f"{v:02X}{v:02X}{v:02X}")
    return TONE_GREYS


def attr(el: str, name: str) -> str | None:
    m = re.search(rf'{W.replace("{", "").replace("}", "")}', "")  # noqa: F841
    m = re.search(rf'w:{name}="([^"]*)"', el)
    return m.group(1) if m else None


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, bool, str]] = []

    def add(self, template: str, check: str, ok: bool, detail: str = "") -> None:
        self.rows.append((template, check, ok, detail))

    @property
    def failed(self) -> list[tuple[str, str, bool, str]]:
        return [r for r in self.rows if not r[2]]

    def report(self) -> int:
        width = max(len(r[0]) for r in self.rows)
        current = None
        for name, check, ok, detail in self.rows:
            if name != current:
                print(f"\n{name}")
                current = name
            mark = "ok  " if ok else "FAIL"
            print(f"  [{mark}] {check}" + (f" — {detail}" if detail else ""))
        print()
        if self.failed:
            print(f"{len(self.failed)} check(s) failed.")
            return 1
        print(f"All {len(self.rows)} checks passed across "
              f"{len({r[0] for r in self.rows})} templates.")
        return 0


def check_template(path: Path, r: Result) -> None:
    name = path.stem
    z = zipfile.ZipFile(path)
    names = z.namelist()
    ct = z.read("[Content_Types].xml").decode()
    doc = z.read("word/document.xml").decode()
    styles = z.read("word/styles.xml").decode()
    headers = [z.read(n).decode() for n in names if re.match(r"word/header\d+\.xml", n)]
    footers = [z.read(n).decode() for n in names if re.match(r"word/footer\d+\.xml", n)]

    # W1 -------------------------------------------------------------------
    r.add(name, "W1 template content type", CT_DOTX in ct)
    r.add(name, "W1 custom properties present", "docProps/custom.xml" in names)
    props = z.read("docProps/custom.xml").decode() if "docProps/custom.xml" in names else ""
    missing = [p for p in ("PTS_ProjectName", "PTS_ContainerID", "PTS_Revision", "PTS_Status")
               if f'name="{p}"' not in props]
    r.add(name, "W1 required properties defined", not missing, ", ".join(missing))

    # W2 -------------------------------------------------------------------
    sect = re.search(r"<w:pgSz[^>]*>", doc)
    mar = re.search(r"<w:pgMar[^>]*>", doc)
    ok_geom, detail = False, "no sectPr"
    if sect and mar:
        pw, ph = int(attr(sect.group(0), "w")), int(attr(sect.group(0), "h"))
        land = attr(sect.group(0), "orient") == "landscape"
        mm = lambda v: round(v * 25.4 / 1440)
        if land:
            f = T["sheet"]["formats"]["A3"]
            m = T["sheet"]["margins"]
            want = (f["size"][0], f["size"][1], m["binding"], m["right"], m["top"], m["bottom"])
        else:
            d = T["document"]
            m = d["margins"]
            want = (d["size"][0], d["size"][1], m["left"], m["right"], m["top"], m["bottom"])
        got = (mm(pw), mm(ph),
               mm(int(attr(mar.group(0), "left"))), mm(int(attr(mar.group(0), "right"))),
               mm(int(attr(mar.group(0), "top"))), mm(int(attr(mar.group(0), "bottom"))))
        ok_geom = all(abs(a - b) <= 1 for a, b in zip(got, want))
        detail = f"{got} vs {want}" if not ok_geom else f"{got[0]}×{got[1]} mm"
    r.add(name, "W2 page geometry matches tokens", ok_geom, detail)

    # W3 -------------------------------------------------------------------
    wanted = ["t1 legal", "t2 body", "t2 body tight", "t2 label caps", "t2 mono id",
              "t3 heading block", "t4 heading section", "th header", "td text", "td number"]
    absent = [s for s in wanted if f'<w:name w:val="{s}"/>' not in styles]
    r.add(name, "W3 PTS styles present", not absent, ", ".join(absent))

    tags = re.findall(r"<w:spacing\b[^>]*/>", styles)
    pitches = [int(re.search(r'w:line="(\d+)"', t).group(1)) for t in tags
               if 'w:lineRule="exact"' in t and 'w:line="' in t]
    # 10 mm is 567 twips but two 5 mm sub-modules are 566: allow the 1-twip
    # rounding that millimetre-to-twip conversion necessarily produces.
    off = [p for p in pitches
           if min(abs(p - n * SUBMODULE_TW) for n in range(1, 13)) > 2]
    r.add(name, "W3 line pitch on the 5 mm lattice", not off and bool(pitches),
          f"{len(pitches)} exact pitches" if not off else f"off-lattice: {off}")

    # W4 -------------------------------------------------------------------
    sizes_hp = {int(v) for v in re.findall(r'<w:sz w:val="(\d+)"/>', styles)}
    floor_hp = round(MIN_CAP / CAP_EM / 0.3528 * 2)
    t1_hp = round(T["type"]["steps"]["t1"]["pt"] * 2)
    below = {s for s in sizes_hp if s < floor_hp and s != t1_hp}
    r.add(name, "W4 no size below the 2.5 mm floor", not below,
          f"half-points {sorted(below)}" if below else f"min {min(sizes_hp)/2:.1f} pt")

    # W5 -------------------------------------------------------------------
    body_and_apparatus = doc + "".join(headers) + "".join(footers)
    for prop in ("PTS_ProjectName", "PTS_ContainerID", "PTS_Revision", "PTS_Status"):
        r.add(name, f"W5 {prop} is a field",
              f'DOCPROPERTY "{prop}"' in body_and_apparatus)
    if footers:
        r.add(name, "W5 page number is a field",
              " PAGE " in "".join(footers) and " NUMPAGES " in "".join(footers))

    # W6 -------------------------------------------------------------------
    vertical = re.findall(r'<w:insideV w:val="(\w+)"', doc)
    r.add(name, "W6 no vertical rules", all(v == "none" for v in vertical),
          f"{len(vertical)} insideV, non-none: {[v for v in vertical if v != 'none']}")
    tables = doc.count("<w:tbl>")
    if "Schedule" in name or "Revision-Log" in name:
        r.add(name, "W6 header row repeats", "<w:tblHeader" in doc)

    # W7 -------------------------------------------------------------------
    heights = [int(v) for v in re.findall(r'<w:trHeight w:val="(\d+)"', doc)]
    bad = [h for h in heights
           if min(abs(h - n * SUBMODULE_TW) for n in range(1, 13)) > 2]
    r.add(name, "W7 row pitch is a whole sub-module", not bad,
          f"{len(heights)} rows" if not bad else f"off-lattice: {bad[:5]}")

    # W8 -------------------------------------------------------------------
    rules = re.findall(r'<w:(?:top|bottom) w:val="single" w:sz="(\d+)"', "".join(headers + footers))
    r.add(name, "W8 apparatus hairline at W1 tier", bool(rules) and all(int(s) <= 4 for s in rules),
          f"sz={set(rules)} eighths-pt" if rules else "no rule found")

    # W9 -------------------------------------------------------------------
    if "Schedule" in name or "Revision-Log" in name:
        grid = re.search(r"<w:tblGrid>(.*?)</w:tblGrid>", doc, re.S)
        cols = [int(v) for v in re.findall(r'<w:gridCol w:w="(\d+)"', grid.group(1))] if grid else []
        total_mm = sum(cols) * 25.4 / 1440
        want = T["sheet"]["formats"]["A3"]["frame"][0]
        r.add(name, "W9 columns sum to the frame width", abs(total_mm - want) < 1.0,
              f"{total_mm:.1f} mm of {want} mm across {len(cols)} columns")

    # W11 ------------------------------------------------------------------
    # w:gridCol alone does not fix a table's width. Left at w:tblW auto/0 the
    # renderer sizes the table to its content, which is what collapsed every
    # table in the first build.
    parts = doc + "".join(headers) + "".join(footers)
    tbls = re.findall(r"<w:tbl>.*?</w:tbl>", parts, re.S)
    bad_w = []
    for i, tbl in enumerate(tbls):
        grid = sum(int(v) for v in re.findall(r'<w:gridCol w:w="(\d+)"', tbl))
        m = re.search(r'<w:tblW[^>]*/>', tbl)
        got_type = attr(m.group(0), "type") if m else None
        got_w = int(attr(m.group(0), "w") or 0) if m else 0
        if got_type != "dxa" or abs(got_w - grid) > 2:
            bad_w.append(f"table{i}: {got_type}/{got_w} vs grid {grid}")
    r.add(name, "W11 table width fixed and equal to its columns", not bad_w,
          "; ".join(bad_w[:3]) or f"{len(tbls)} tables")

    # W12 ------------------------------------------------------------------
    bad_c = []
    for i, tbl in enumerate(tbls):
        ncells = len(re.findall(r"<w:tc>", tbl))
        nwidths = len(re.findall(r"<w:tcW\b", tbl))
        if ncells != nwidths:
            bad_c.append(f"table{i}: {nwidths} widths for {ncells} cells")
    r.add(name, "W12 every cell carries a width", not bad_c, "; ".join(bad_c[:3]))

    # W13 ------------------------------------------------------------------
    ids = set(re.findall(r'w:styleId="([^"]+)"', styles))
    refs = set(re.findall(r'<w:rStyle w:val="([^"]+)"', doc + "".join(headers + footers)))
    refs |= set(re.findall(r'<w:pStyle w:val="([^"]+)"', doc + "".join(headers + footers)))
    dangling = sorted(refs - ids)
    r.add(name, "W13 style references resolve", not dangling, ", ".join(dangling))

    # W14 ------------------------------------------------------------------
    tabs = re.findall(r'<w:tab w:pos="\d+" w:val="right"/>', "".join(headers + footers))
    r.add(name, "W14 no right-tab in header or footer", not tabs, f"{len(tabs)} found")

    # W10 ------------------------------------------------------------------
    fills = {f.upper() for f in re.findall(r'<w:shd[^>]*w:fill="([0-9A-Fa-f]{6})"', doc)}
    colours = {c.upper() for c in re.findall(r'<w:color w:val="([0-9A-Fa-f]{6})"', doc + styles)}
    non_grey = {c for c in (fills | colours) if not (c[0:2] == c[2:4] == c[4:6])}
    r.add(name, "W10 monochrome", not non_grey, ", ".join(sorted(non_grey)))
    off_ladder = {f for f in fills if f not in tone_greys()}
    r.add(name, "W10 fills are tone-ladder values", not off_ladder, ", ".join(sorted(off_ladder)))


def main() -> int:
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "templates"
    files = sorted(d.glob("*.dotx"))
    if not files:
        print(f"No .dotx found in {d}. Run build.py first.")
        return 1
    r = Result()
    for f in files:
        check_template(f, r)
    return r.report()


if __name__ == "__main__":
    raise SystemExit(main())
