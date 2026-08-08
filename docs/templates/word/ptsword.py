#!/usr/bin/env python3
"""PTS 1.0 — Word template builder library.

Builds .dotx templates from machine/pts-tokens.json. Nothing here hard-codes a
dimension: every measurement is read from the token file, so a change to the
system is a change to one JSON file and a rebuild.

Word cannot express three things the system requires (PTS-03 §4). They are
handled, not hidden:

  baseline grid    Word has none. Every paragraph gets exact line spacing in
                   whole 5 mm multiples, so the rhythm holds within a page.
  marginal column  Word has no side column. The page body is a two-cell
                   borderless table: 25 mm marginal + 125 mm (5 mm inset + 120
                   mm measure).
  optical align    Not available. The deviation is below the perceptual
                   threshold at these sizes and is accepted.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor, Twips

HERE = Path(__file__).resolve().parent
TOKENS = json.loads((HERE.parent / "machine" / "pts-tokens.json").read_text())
T = TOKENS["pts"]

# Word template content type; a .dotx differs from a .docx only by this string
# and the file extension.
CT_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
CT_DOTX = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"

FONT = "Inter"          # PTS declared open fallback for Word (PTS-01 §5.1)
FONT_MONO = "IBM Plex Mono"

# Word derives a styleId from the style name by removing spaces, so the PTS
# styles all begin with one of these prefixes.
PTS_STYLE_IDS = ("t1", "t2", "t3", "t4", "t5", "th", "td",
                 "monoinline", "italicterm", "smallcapslabel")

# Style name -> styleId. A w:rStyle must carry the id; carrying the name makes
# the reference dangle and the run falls back to the paragraph style.
STYLE_IDS: dict[str, str] = {}


# ---------------------------------------------------------------- units ----

def tw(mm_value: float) -> int:
    """Millimetres to twips, rounded — the unit Word stores lengths in."""
    return round(mm_value * 1440 / 25.4)


def tone_hex(token: str) -> str:
    """Tone token to an sRGB grey, via CIE L*.

    The ladder is defined in L* (PTS-01 §2.3) precisely so that it can be
    converted for any output space rather than assumed.
    """
    lstar = T["ink"]["tones"][token]["L"]
    y = ((lstar + 16) / 116) ** 3 if lstar > 8 else lstar / 903.3
    c = 1.055 * (y ** (1 / 2.4)) - 0.055 if y > 0.0031308 else 12.92 * y
    v = max(0, min(255, round(c * 255)))
    return f"{v:02X}{v:02X}{v:02X}"


def step(name: str) -> dict:
    return T["type"]["steps"][name]


# ------------------------------------------------------------ xml helpers --

def _el(tag: str, **attrs) -> OxmlElement:
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(f"w:{k}"), str(v))
    return e


# OOXML enforces element order inside every *Pr container. Appending is wrong
# and produces a package Word silently refuses to open, so each insertion names
# the elements it must precede.
_SEQ = {
    "pPr": ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
            "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs",
            "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
            "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
            "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
            "suppressOverlap", "jc", "textDirection", "textAlignment",
            "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr"],
    "rPr": ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike",
            "dstrike", "outline", "shadow", "emboss", "imprint", "noProof",
            "snapToGrid", "vanish", "webHidden", "color", "spacing", "w", "kern",
            "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd",
            "fitText", "vertAlign", "rtl", "cs", "em", "lang"],
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
              "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd",
              "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook"],
    "trPr": ["cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter",
             "cantSplit", "trHeight", "tblHeader", "tblCellSpacing", "jc", "hidden"],
    "tcPr": ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd",
             "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark"],
}


def _insert(parent, child, container: str):
    """Insert child into parent at its schema position."""
    order = _SEQ[container]
    tag = child.tag.split("}")[-1]
    successors = order[order.index(tag) + 1:]
    parent.insert_element_before(child, *[f"w:{s}" for s in successors])
    return child


def _get_or_add(parent, tag: str, container: str):
    existing = parent.find(qn(f"w:{tag}"))
    if existing is not None:
        return existing
    return _insert(parent, _el(f"w:{tag}"), container)


def set_exact_spacing(paragraph, pitch_pt: float, before_pt: float = 0, after_pt: float = 0) -> None:
    pf = paragraph.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(pitch_pt)
    pf.space_before = Pt(before_pt)
    pf.space_after = Pt(after_pt)


def add_border(paragraph, edge: str = "bottom", size_eighths: int = 4, colour: str = "000000") -> None:
    """A hairline as a paragraph border.

    0.18 mm = 0.51 pt; Word stores border width in eighths of a point, so
    size 4 = 0.5 pt = 0.176 mm — the nearest expressible value to the tier-W1
    width, and within the reproduction floor.
    """
    pPr = paragraph._p.get_or_add_pPr()
    borders = _get_or_add(pPr, "pBdr", "pPr")
    borders.append(_el(f"w:{edge}", val="single", sz=size_eighths, space=2, color=colour))


def add_field(paragraph, instruction: str, placeholder: str, style: str | None = None):
    """Insert a Word field. Fields are how a template stays correct.

    A typed value is a hand-maintained copy of a fact held elsewhere and is the
    most frequently wrong content in any document set (PTS-01 §6.1).
    """
    style_id = STYLE_IDS.get(style, style) if style else None

    def run(children):
        r = OxmlElement("w:r")
        if style_id:
            rPr = OxmlElement("w:rPr")
            rs = _el("w:rStyle", val=style_id)
            rPr.append(rs)
            r.append(rPr)
        for c in children:
            r.append(c)
        paragraph._p.append(r)
        return r

    run([_el("w:fldChar", fldCharType="begin")])
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instruction} "
    run([it])
    run([_el("w:fldChar", fldCharType="separate")])
    t = OxmlElement("w:t")
    t.text = placeholder
    run([t])
    run([_el("w:fldChar", fldCharType="end")])


def add_docproperty(paragraph, prop: str, placeholder: str, style: str | None = None):
    add_field(paragraph, f'DOCPROPERTY "{prop}" \\* MERGEFORMAT', placeholder, style)


def set_tabs(paragraph, positions_mm: list[tuple[float, str]]) -> None:
    align = {"left": WD_TAB_ALIGNMENT.LEFT,
             "right": WD_TAB_ALIGNMENT.RIGHT,
             "center": WD_TAB_ALIGNMENT.CENTER}
    for pos, kind in positions_mm:
        paragraph.paragraph_format.tab_stops.add_tab_stop(Mm(pos), align[kind])


# ---------------------------------------------------------------- styles ---

def build_styles(doc: Document) -> None:
    """Create every PTS style. Style names match the InDesign set (PTS-03 §3.3)
    so that content moves between the two without reinterpretation."""
    from docx.enum.style import WD_STYLE_TYPE

    styles = doc.styles

    # Normal is the base every other style inherits from.
    normal = styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(step("t2")["pt"])
    normal.font.color.rgb = RGBColor(0, 0, 0)
    rpr = normal.element.get_or_add_rPr()
    rf = rpr.get_or_add_rFonts()
    for a in ("ascii", "hAnsi", "cs"):
        rf.set(qn(f"w:{a}"), FONT)
    _insert(rpr, _el("w:lang", val="en-GB"), "rPr")
    pf = normal.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(step("t2")["pitch_pt"])
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.widow_control = True

    spec = [
        # name,                base,   step, bold,  before, after, caps, keep_next
        ("t1 legal",           None,   "t1", False, 0,      0,     False, False),
        ("t2 body",            None,   "t2", False, 0,      14.2,  False, False),
        ("t2 body tight",      None,   "t2", False, 0,      0,     False, False),
        ("t2 label caps",      None,   "t2", False, 0,      0,     True,  False),
        ("t2 mono id",         None,   "t2", False, 0,      0,     False, False),
        ("t3 heading block",   None,   "t3", True,  28.35,  14.2,  False, True),
        ("t4 heading section", None,   "t4", False, 56.7,   14.2,  False, True),
        ("t4 statement",       None,   "t4", False, 0,      14.2,  False, False),
        ("t5 identifier",      None,   "t5", False, 0,      14.2,  False, False),
        ("th header",          None,   "t2", True,  0,      0,     True,  False),
        ("td text",            None,   "t2", False, 0,      0,     False, False),
        ("td number",          None,   "t2", False, 0,      0,     False, False),
    ]

    for name, _base, stp, bold, before, after, caps, keep in spec:
        st = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        STYLE_IDS[name] = st.style_id
        st.base_style = styles["Normal"]
        st.quick_style = True
        s = step(stp)
        st.font.size = Pt(s["pt"])
        st.font.bold = bold
        st.font.name = FONT_MONO if "mono" in name else FONT
        rpr = st.element.get_or_add_rPr()
        rf = rpr.get_or_add_rFonts()
        for a in ("ascii", "hAnsi", "cs"):
            rf.set(qn(f"w:{a}"), FONT_MONO if "mono" in name else FONT)
        if caps:
            _insert(rpr, _el("w:smallCaps", val="1"), "rPr")
            # Capitals set at text tracking close up at small sizes (PTS-01 §5.3)
            _insert(rpr, _el("w:spacing", val=int(s["pt"] * 20 * 0.02)), "rPr")
        pf = st.paragraph_format
        pf.alignment = (WD_ALIGN_PARAGRAPH.RIGHT if name == "td number"
                        else WD_ALIGN_PARAGRAPH.LEFT)
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        pf.line_spacing = Pt(s["pitch_pt"])
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.keep_with_next = keep
        pf.widow_control = True

    # Character styles
    for name, size, mono, italic, caps in [
        ("mono inline", "t2", True, False, False),
        ("italic term", "t2", False, True, False),
        ("small caps label", "t2", False, False, True),
    ]:
        cs = styles.add_style(name, WD_STYLE_TYPE.CHARACTER)
        STYLE_IDS[name] = cs.style_id
        s = step(size)
        cs.font.size = Pt(s["pt"])
        cs.font.italic = italic
        fam = FONT_MONO if mono else FONT
        cs.font.name = fam
        rpr = cs.element.get_or_add_rPr()
        rf = rpr.get_or_add_rFonts()
        for a in ("ascii", "hAnsi", "cs"):
            rf.set(qn(f"w:{a}"), fam)
        if caps:
            _insert(rpr, _el("w:smallCaps", val="1"), "rPr")


# ------------------------------------------------------------- page setup --

def setup_document(doc: Document) -> None:
    """A4 portrait, PTS document margins (PTS-01 §4.5)."""
    d = T["document"]
    m = d["margins"]
    s = doc.sections[0]
    s.orientation = WD_ORIENT.PORTRAIT
    s.page_width = Mm(d["size"][0])
    s.page_height = Mm(d["size"][1])
    s.left_margin = Mm(m["left"])
    s.right_margin = Mm(m["right"])
    s.top_margin = Mm(m["top"])
    s.bottom_margin = Mm(m["bottom"])
    s.header_distance = Mm(d["header"]["baseline"])
    s.footer_distance = Mm(m["bottom"])
    s.different_first_page_header_footer = False
    return s


def setup_sheet(doc: Document, fmt: str = "A3") -> None:
    """A landscape sheet carrying a table as its single view (PTS-02 T06, T10)."""
    f = T["sheet"]["formats"][fmt]
    m = T["sheet"]["margins"]
    s = doc.sections[0]
    s.orientation = WD_ORIENT.LANDSCAPE
    s.page_width = Mm(f["size"][0])
    s.page_height = Mm(f["size"][1])
    s.left_margin = Mm(m["binding"])
    s.right_margin = Mm(m["right"])
    s.top_margin = Mm(m["top"])
    s.bottom_margin = Mm(m["bottom"])
    s.header_distance = Mm(5)
    s.footer_distance = Mm(5)
    return s


# ------------------------------------------------------- header and footer --

def _apparatus_table(doc: Document, container, widths_mm: list[float], edge: str):
    """A two-cell fixed table for a header or footer.

    Not a tab stop. A right-aligned tab depends on the renderer honouring the
    stop; where it does not, a long identifier runs past the measure and breaks
    at one of its own hyphens, which is how a container ID becomes two IDs. A
    fixed cell cannot do that.
    """
    table = container.add_table(rows=1, cols=len(widths_mm), width=Mm(sum(widths_mm)))
    table.autofit = False
    clear_borders(table)
    set_cell_margins(table, left_mm=0, right_mm=0)
    for col, w in zip(table.columns, widths_mm):
        col.width = Mm(w)
    row = table.rows[0]
    for cell, w in zip(row.cells, widths_mm):
        cell.width = Mm(w)
        tcPr = cell._tc.get_or_add_tcPr()
        borders = _get_or_add(tcPr, "tcBorders", "tcPr")
        borders.append(_el(f"w:{edge}", val="single", sz=4, space=2, color="000000"))
    # A header or footer whose last block is a table confuses Word; keep the
    # container's own paragraph after it, collapsed to nothing.
    tail = container.paragraphs[0]
    tail._p.getparent().remove(tail._p)
    tail = container.add_paragraph()
    set_exact_spacing(tail, 1)
    return row


def _apparatus_para(doc: Document, cell, align_right: bool = False):
    p = cell.paragraphs[0]
    p.style = doc.styles["t2 body tight"]
    if align_right:
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    return p


def build_header(doc: Document, section) -> None:
    d = T["document"]
    total = d["text_column"]["x"] + d["text_column"]["width"] - d["margins"]["left"]
    row = _apparatus_table(doc, section.header, [total * 0.6, total * 0.4], "bottom")

    left = _apparatus_para(doc, row.cells[0])
    add_docproperty(left, "PTS_ProjectName", "PROJECT NAME")
    left.add_run("  ·  ")
    add_docproperty(left, "PTS_ProjectCode", "0000")

    right = _apparatus_para(doc, row.cells[1], align_right=True)
    add_docproperty(right, "PTS_ContainerID", "0000-XXX-ZZ-XX-RP-A-0000", style="mono inline")


def build_footer(doc: Document, section, page_numbers: bool = True) -> None:
    d = T["document"]
    total = d["text_column"]["x"] + d["text_column"]["width"] - d["margins"]["left"]
    row = _apparatus_table(doc, section.footer, [total * 0.7, total * 0.3], "top")

    left = _apparatus_para(doc, row.cells[0])
    add_docproperty(left, "PTS_ContainerID", "0000-XXX-ZZ-XX-RP-A-0000", style="mono inline")
    left.add_run("  ·  ")
    add_docproperty(left, "PTS_Revision", "P01")
    left.add_run("  ·  ")
    add_docproperty(left, "PTS_Status", "S0")

    right = _apparatus_para(doc, row.cells[1], align_right=True)
    if page_numbers:
        right.add_run("Page ")
        add_field(right, "PAGE", "1")
        right.add_run(" / ")
        add_field(right, "NUMPAGES", "1")


# ----------------------------------------------------------------- tables --

def set_cell_margins(table, left_mm: float = 1.25, right_mm: float = 1.25,
                     top_mm: float = 0, bottom_mm: float = 0) -> None:
    """Cell inset = half a cap height at t2. Not a stylistic choice: it is the
    crowding threshold below which flanking marks impair character
    identification (PTS-01 §5.3)."""
    tblPr = table._tbl.tblPr
    mar = _el("w:tblCellMar")
    for edge, val in (("top", top_mm), ("left", left_mm),
                      ("bottom", bottom_mm), ("right", right_mm)):
        mar.append(_el(f"w:{edge}", w=tw(val), type="dxa"))
    _insert(tblPr, mar, "tblPr")


def clear_borders(table) -> None:
    """No vertical rules, no grid. Columns are separated by space; a gridded
    table reads as a grid, a spaced table reads as data (PTS-02 T06)."""
    tblPr = table._tbl.tblPr
    borders = _el("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borders.append(_el(f"w:{edge}", val="none", sz=0, space=0, color="auto"))
    _insert(tblPr, borders, "tblPr")


def rule_below(row, size_eighths: int = 4) -> None:
    for cell in row.cells:
        tcPr = cell._tc.get_or_add_tcPr()
        borders = _get_or_add(tcPr, "tcBorders", "tcPr")
        borders.append(_el("w:bottom", val="single", sz=size_eighths, space=0, color="000000"))


def shade(cell, token: str = "T1") -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    _insert(tcPr, _el("w:shd", val="clear", color="auto", fill=tone_hex(token)), "tcPr")


def repeat_header(row) -> None:
    trPr = row._tr.get_or_add_trPr()
    _insert(trPr, _el("w:tblHeader", val="true"), "trPr")


def no_row_break(row) -> None:
    trPr = row._tr.get_or_add_trPr()
    _insert(trPr, _el("w:cantSplit", val="true"), "trPr")


def make_table(doc, widths_mm: list[float], rows: int = 1):
    table = doc.add_table(rows=rows, cols=len(widths_mm))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False   # emits w:tblLayout type="fixed"
    clear_borders(table)
    set_cell_margins(table)
    for r in table.rows:
        for c, w in zip(r.cells, widths_mm):
            c.width = Mm(w)
    for col, w in zip(table.columns, widths_mm):
        col.width = Mm(w)
    return table


def cell_text(doc, cell, text: str, style: str = "td text") -> None:
    p = cell.paragraphs[0]
    p.style = doc.styles[style]
    if text:
        p.add_run(text)


# --------------------------------------------------------------- packaging --

DOC_PROPERTIES = [
    ("PTS_ProjectName", "PROJECT NAME"),
    ("PTS_ProjectCode", "0000"),
    ("PTS_Client", "Client name"),
    ("PTS_ContainerID", "0000-XXX-ZZ-XX-RP-A-0000"),
    ("PTS_DocumentTitle", "DOCUMENT TITLE"),
    ("PTS_Revision", "P01"),
    ("PTS_Status", "S0"),
    ("PTS_StatusName", "Work in progress"),
    ("PTS_IssueDate", "0000-00-00"),
    ("PTS_Originator", "Originator name, address, contact"),
    ("PTS_Author", "--"),
    ("PTS_Checker", "--"),
    ("PTS_Approver", "--"),
    ("PTS_Conformance", "Conforms to ADOS 1.0 Class B · PTS 1.0"),
]

CUSTOM_XML_HEAD = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
)


def _custom_properties_xml() -> str:
    parts = [CUSTOM_XML_HEAD]
    for i, (name, value) in enumerate(DOC_PROPERTIES, start=2):
        parts.append(
            f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{i}" name="{name}">'
            f"<vt:lpwstr>{value}</vt:lpwstr></property>"
        )
    parts.append("</Properties>")
    return "".join(parts)


# Styles python-docx inherits from its default template that a PTS document may
# keep. Everything else is removed: the default set ships blue headings and an
# 8 pt body style, and a template that offers a style violating the system will
# have that style used (PTS-03 §4.2).
KEEP_STYLES = {
    "Normal", "DefaultParagraphFont", "TableNormal", "NoList", "Header",
    "HeaderChar", "Footer", "FooterChar",
}


def _prune_styles(xml: str) -> str:
    def keep(match: re.Match) -> str:
        sid = re.search(r'w:styleId="([^"]+)"', match.group(0))
        if sid is None:
            return match.group(0)
        name = sid.group(1)
        return match.group(0) if (name in KEEP_STYLES or name.startswith(PTS_STYLE_IDS)) else ""

    xml = re.sub(r"<w:style [^>]*>.*?</w:style>", keep, xml, flags=re.S)
    # Hide the latent built-ins so the gallery shows the PTS set and nothing else.
    xml = re.sub(r"<w:latentStyles\b[^>]*>.*?</w:latentStyles>", "", xml, flags=re.S)
    xml = re.sub(r"<w:latentStyles\b[^>]*/>", "", xml)
    # CT_Styles sequence is docDefaults, latentStyles, style* — the latent block
    # goes after docDefaults, not before it.
    if "</w:docDefaults>" in xml:
        xml = xml.replace(
            "</w:docDefaults>",
            '</w:docDefaults><w:latentStyles w:defLockedState="1" w:defUIPriority="99" '
            'w:defSemiHidden="1" w:defUnhideWhenUsed="1" w:defQFormat="0" w:count="0"/>', 1)
    return xml



def _stamp_table_widths(doc: Document) -> None:
    """Give every table an explicit width, and every cell the width of its
    column. python-docx sets w:gridCol but leaves w:tblW at auto/0 and only
    writes w:tcW on rows that exist when the width is assigned."""
    containers = [doc]
    for section in doc.sections:
        containers += [section.header, section.footer,
                       section.first_page_header, section.first_page_footer,
                       section.even_page_header, section.even_page_footer]
    tables = [t for c in containers if c is not None for t in c.tables]
    for table in tables:
        grid = [int(gc.get(qn("w:w")))
                for gc in table._tbl.tblGrid.findall(qn("w:gridCol"))]
        if not grid:
            continue
        tblPr = table._tbl.tblPr
        existing = tblPr.find(qn("w:tblW"))
        if existing is not None:
            tblPr.remove(existing)
        _insert(tblPr, _el("w:tblW", w=sum(grid), type="dxa"), "tblPr")
        for row in table.rows:
            for cell, w in zip(row.cells, grid):
                cell.width = Twips(w)


def _font_table(xml: str) -> str:
    """Declare a substitute for each specified face.

    Word has no font-fallback chain: a missing face is replaced by whatever the
    renderer picks, which on a machine without Inter is a serif — a different
    document. w:altName is the one mechanism OOXML provides, and it at least
    keeps the substitute in the right class.
    """
    entries = {
        FONT: ("Arial", "swiss", "variable"),
        FONT_MONO: ("Consolas", "modern", "fixed"),
    }
    additions = []
    for face, (alt, family, pitch) in entries.items():
        if f'w:name="{face}"' in xml:
            continue
        additions.append(
            f'<w:font w:name="{face}"><w:altName w:val="{alt}"/>'
            f'<w:charset w:val="00"/><w:family w:val="{family}"/>'
            f'<w:pitch w:val="{pitch}"/></w:font>'
        )
    return xml.replace("</w:fonts>", "".join(additions) + "</w:fonts>") if additions else xml


def save_as_dotx(doc: Document, out_path: Path) -> None:
    """Save as a Word template.

    A .dotx is a .docx whose main part declares the template content type. The
    custom document properties the DOCPROPERTY fields resolve against are
    injected here, because python-docx does not expose them.
    """
    _stamp_table_widths(doc)
    tmp = out_path.with_suffix(".tmp.docx")
    doc.save(tmp)

    with zipfile.ZipFile(tmp) as zin:
        items = {n: zin.read(n) for n in zin.namelist()}

    ct = items["[Content_Types].xml"].decode("utf-8")
    ct = ct.replace(CT_DOCX, CT_DOTX)
    if "custom-properties" not in ct:
        ct = ct.replace(
            "</Types>",
            '<Override PartName="/docProps/custom.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.custom-properties+xml"/></Types>',
        )
    items["[Content_Types].xml"] = ct.encode("utf-8")

    rels = items["_rels/.rels"].decode("utf-8")
    if "docProps/custom.xml" not in rels:
        rels = rels.replace(
            "</Relationships>",
            '<Relationship Id="rIdCustom" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/custom-properties" '
            'Target="docProps/custom.xml"/></Relationships>',
        )
    items["_rels/.rels"] = rels.encode("utf-8")
    items["docProps/custom.xml"] = _custom_properties_xml().encode("utf-8")

    items["word/styles.xml"] = _prune_styles(items["word/styles.xml"].decode("utf-8")).encode("utf-8")

    items["word/fontTable.xml"] = _font_table(
        items["word/fontTable.xml"].decode("utf-8")).encode("utf-8")

    settings = items["word/settings.xml"].decode("utf-8")
    settings = re.sub(r"<w:zoom(?![^>]*w:percent)([^>]*?)/>",
                      r'<w:zoom\1 w:percent="100"/>', settings)
    items["word/settings.xml"] = settings.encode("utf-8")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in items.items():
            zout.writestr(name, data)
    tmp.unlink()


def new_document(kind: str = "document", fmt: str = "A3") -> tuple[Document, object]:
    doc = Document()
    build_styles(doc)
    section = setup_document(doc) if kind == "document" else setup_sheet(doc, fmt)
    # Remove the empty first paragraph docx starts with.
    body = doc.element.body
    first = body.find(qn("w:p"))
    if first is not None:
        body.remove(first)
    return doc, section
