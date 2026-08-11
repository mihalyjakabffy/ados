#!/usr/bin/env python3
"""PTS 1.0 — build the Word templates.

    python3 docs/templates/word/build.py [outdir]

Produces ten .dotx templates. Word is used only where the recipient needs an
editable document (PTS-03 §4); the cover, drawing, detail and board templates
are Archicad and InDesign deliverables and are not built here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

import ptsword as P
from ptsword import (T, add_docproperty, add_field, build_footer, build_header,
                     cell_text, make_table, new_document, no_row_break,
                     repeat_header, rule_below, save_as_dotx, set_exact_spacing,
                     set_tabs, shade, tw, _el)

BODY_W = 150.0          # Word text width on A4: 210 - 20 - 40
MARGINAL_W = 30.0       # 25 mm marginal column + 5 mm gutter
MEASURE_W = 120.0       # the measure, unchanged from PTS-01 §4.5
SHEET_W = 390.0         # A3 landscape frame width


# --------------------------------------------------------------- helpers ---

def cell_margins(cell, left=1.25, right=1.25, top=0.0, bottom=0.0):
    tcPr = cell._tc.get_or_add_tcPr()
    mar = _el("w:tcMar")
    for edge, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        mar.append(_el(f"w:{edge}", w=tw(val), type="dxa"))
    P._insert(tcPr, mar, "tcPr")


def row_height(row, mm_value: float, exact: bool = False):
    """Row pitch. 'atLeast' rather than 'exact': at t2 the line box is 14.2 pt
    and a 5 mm row is 14.17 pt, so an exact rule clips the descenders by a
    third of a point. atLeast holds the 5 mm pitch for single-line content —
    which is every row in a conforming schedule — and grows rather than
    truncates if a cell wraps, so a defect is visible instead of hidden."""
    trPr = row._tr.get_or_add_trPr()
    P._insert(trPr, _el("w:trHeight", val=tw(mm_value),
                        hRule="exact" if exact else "atLeast"), "trPr")


def para(doc, style: str, text: str = "", after_mm: float | None = None):
    p = doc.add_paragraph(style=doc.styles[style])
    if text:
        p.add_run(text)
    if after_mm is not None:
        p.paragraph_format.space_after = Pt(after_mm * 72 / 25.4)
    return p


def spacer(doc, mm_value: float):
    """Vertical space as an empty paragraph of exact height — keeps the 5 mm
    rhythm rather than relying on an arbitrary paragraph return."""
    p = doc.add_paragraph(style=doc.styles["t2 body tight"])
    set_exact_spacing(p, mm_value * 72 / 25.4)
    return p


def body_table(doc, widths, rows=1):
    """A body table with the PTS insets: marginal column indented, body column
    flush at the measure edge."""
    t = make_table(doc, widths, rows=rows)
    for r in t.rows:
        cell_margins(r.cells[0], left=1.25, right=0)
        for c in r.cells[1:]:
            cell_margins(c, left=0, right=1.25)
    return t


def page1_block(doc, title_default: str, container_type: str = "RP"):
    """The page-1 data block: title, then the facts a recipient needs before
    reading anything else (PTS-01 §6.4).

    ``container_type`` is the type field of the container identifier the
    placeholder shows. It is a parameter because a placeholder is read as an
    example: a survey record whose identifier reads ``…-RP-…`` teaches the
    roof-plan code to everyone who fills one in.
    """
    p = doc.add_paragraph(style=doc.styles["t4 heading section"])
    p.paragraph_format.space_before = Pt(0)
    add_docproperty(p, "PTS_DocumentTitle", title_default)

    t = make_table(doc, [40, 110], rows=0)
    fields = [
        ("Project", "PTS_ProjectName", "PROJECT NAME"),
        ("Project code", "PTS_ProjectCode", "0000"),
        ("Client", "PTS_Client", "Client name"),
        ("Container", "PTS_ContainerID", f"0000-XXX-ZZ-XX-{container_type}-A-0000"),
        ("Status", "PTS_StatusName", "Work in progress"),
        ("Revision", "PTS_Revision", "P01"),
        ("Date of issue", "PTS_IssueDate", "0000-00-00"),
        ("Author", "PTS_Author", "--"),
        ("Checker", "PTS_Checker", "--"),
        ("Approver", "PTS_Approver", "--"),
    ]
    for label, prop, placeholder in fields:
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        pp = r.cells[1].paragraphs[0]
        pp.style = doc.styles["td text"]
        style = "mono inline" if prop == "PTS_ContainerID" else None
        add_docproperty(pp, prop, placeholder, style=style)
    return t


def schedule_sheet(doc, columns, note: str):
    """A3 landscape schedule: header band, 38 data rows at 5 mm, group rules
    every ten rows (PTS-02 T06)."""
    widths = [w for _, w in columns]
    assert abs(sum(widths) - SHEET_W) < 0.51, f"columns sum to {sum(widths)}, not {SHEET_W}"

    t = make_table(doc, widths, rows=0)
    hdr = t.add_row()
    row_height(hdr, 10)
    repeat_header(hdr)
    no_row_break(hdr)
    for cell, (label, _w) in zip(hdr.cells, columns):
        cell_margins(cell, left=1.25, right=1.25, top=1.25, bottom=1.25)
        shade(cell, "T1")
        cell_text(doc, cell, label, "th header")
    rule_below(hdr)

    cap = T["sheet"]["formats"]["A3"]["table_capacity"]["data_rows"]
    for i in range(cap):
        r = t.add_row()
        row_height(r, cap and 5)
        no_row_break(r)
        for j, cell in enumerate(r.cells):
            cell_margins(cell, left=1.25, right=1.25)
            cell_text(doc, cell, "", "td number" if columns[j][0].startswith(("SO ", "Clear ", "Cill", "Head", "Free")) else "td text")
        if (i + 1) % 10 == 0 and i + 1 < cap:
            rule_below(r)

    spacer(doc, 5)
    para(doc, "t1 legal", note)
    return t


def sheet_footer(doc, section, title_default: str):
    """A3 sheets carry the TB-S field set in the footer: Word cannot place a
    block at an absolute coordinate, so the title block becomes a footer band."""
    row = P._apparatus_table(doc, section.footer, [SHEET_W * 0.8, SHEET_W * 0.2], "top")

    left = P._apparatus_para(doc, row.cells[0])
    add_docproperty(left, "PTS_ProjectName", "PROJECT NAME")
    left.add_run("  ·  ")
    add_docproperty(left, "PTS_DocumentTitle", title_default)
    left.add_run("  ·  ")
    add_docproperty(left, "PTS_ContainerID", "0000-XXX-ZZ-XX-SC-A-0000", style="mono inline")
    left.add_run("  ·  ")
    add_docproperty(left, "PTS_Status", "S0")
    left.add_run("  ·  ")
    add_docproperty(left, "PTS_Revision", "P01")

    right = P._apparatus_para(doc, row.cells[1], align_right=True)
    right.add_run("Sheet ")
    add_field(right, "PAGE", "1")
    right.add_run(" / ")
    add_field(right, "NUMPAGES", "1")


# ------------------------------------------------------------- templates ---

def t05_specification(out: Path):
    doc, section = new_document("document")
    build_header(doc, section)
    build_footer(doc, section)
    page1_block(doc, "SPECIFICATION")
    spacer(doc, 20)

    para(doc, "t3 heading block", "SECTION SCOPE").paragraph_format.space_before = Pt(0)
    t = body_table(doc, [MARGINAL_W, MEASURE_W], rows=0)
    for num, text in [
        ("00.1", "State what this section covers and what it excludes."),
        ("00.2", "State the interfaces with other sections and who owns each."),
    ]:
        r = t.add_row()
        no_row_break(r)
        cell_margins(r.cells[0], left=1.25, right=0)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], num, "t2 mono id")
        cell_text(doc, r.cells[1], text, "td text")

    spacer(doc, 20)
    para(doc, "t3 heading block", "PRODUCTS").paragraph_format.space_before = Pt(0)
    t = body_table(doc, [MARGINAL_W, MEASURE_W], rows=0)
    for num, label, text in [
        ("00.3", "PERFORMANCE",
         "One requirement per clause. The contractor selects and is responsible for compliance."),
        ("00.4", "PRESCRIPTION",
         "One requirement per clause. The designer selects and is responsible for compliance."),
    ]:
        r = t.add_row()
        no_row_break(r)
        cell_margins(r.cells[0], left=1.25, right=0)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], num, "t2 mono id")
        c = r.cells[1].paragraphs[0]
        c.style = doc.styles["td text"]
        c.add_run(label + "  ").style = doc.styles["small caps label"]
        c.add_run(text)

    spacer(doc, 20)
    para(doc, "t3 heading block", "EXECUTION").paragraph_format.space_before = Pt(0)
    t = body_table(doc, [MARGINAL_W, MEASURE_W], rows=0)
    for num, text in [
        ("00.5", "Preparation."),
        ("00.6", "Installation."),
        ("00.7", "Tolerance, where it differs from the general tolerance."),
        ("00.8", "Protection."),
    ]:
        r = t.add_row()
        no_row_break(r)
        cell_margins(r.cells[0], left=1.25, right=0)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], num, "t2 mono id")
        cell_text(doc, r.cells[1], text, "td text")

    spacer(doc, 20)
    para(doc, "t3 heading block", "COMPLETION").paragraph_format.space_before = Pt(0)
    t = body_table(doc, [MARGINAL_W, MEASURE_W], rows=0)
    for num, text in [
        ("00.9", "Testing and commissioning."),
        ("00.10", "Records and warranties."),
    ]:
        r = t.add_row()
        no_row_break(r)
        cell_margins(r.cells[0], left=1.25, right=0)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], num, "t2 mono id")
        cell_text(doc, r.cells[1], text, "td text")

    spacer(doc, 20)
    para(doc, "t1 legal",
         "Every standard cited carries its number, year and title on first use and appears in the "
         "references section. Undated citations are prohibited: a standard changes, and an undated "
         "citation changes the contractual requirement without a variation.")
    save_as_dotx(doc, out / "PTS-T05-Specification.dotx")


def t07_meeting_minutes(out: Path):
    doc, section = new_document("document")
    build_header(doc, section)
    build_footer(doc, section)
    page1_block(doc, "MEETING MINUTES")
    spacer(doc, 10)

    t = make_table(doc, [40, 110], rows=0)
    for label, value in [("Meeting series", ""), ("Meeting number", ""), ("Date and time", ""),
                         ("Location", ""), ("Attendees", ""), ("Apologies", ""),
                         ("Distribution", ""), ("Previous minutes", "accepted / not accepted")]:
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        cell_text(doc, r.cells[1], value, "td text")

    spacer(doc, 20)
    para(doc, "t3 heading block", "ITEMS").paragraph_format.space_before = Pt(0)

    # item number | discussion, decision, action | owner + due date.
    # Owner and date range right in their own column so that a reader scans one
    # vertical strip for their own name (PTS-02 T07).
    t = make_table(doc, [15, 105, 30], rows=0)
    for num in ("0.01", "0.02"):
        for kind, text in [("", "Discussion, in one or two sentences."),
                           ("DECISION", "What was decided, or 'no decision'."),
                           ("ACTION", "What is to be done.")]:
            r = t.add_row()
            no_row_break(r)
            cell_margins(r.cells[0], left=1.25, right=0)
            cell_margins(r.cells[1], left=0, right=1.25)
            cell_margins(r.cells[2], left=0, right=0)
            cell_text(doc, r.cells[0], num if kind == "" else "", "t2 mono id")
            c = r.cells[1].paragraphs[0]
            c.style = doc.styles["td text"]
            if kind:
                c.add_run(kind + "  ").style = doc.styles["small caps label"]
            c.add_run(text)
            pc = r.cells[2].paragraphs[0]
            pc.style = doc.styles["td text"]
            pc.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if kind == "ACTION":
                pc.add_run("XX\n0000-00-00")
        blank = t.add_row()
        row_height(blank, 5)

    spacer(doc, 20)
    para(doc, "t3 heading block", "DECISIONS REGISTER").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body", "Decisions taken at this meeting, listed separately for retrieval.")

    spacer(doc, 10)
    para(doc, "t1 legal",
         "Item numbers are assigned once and carried forward unchanged until the item is closed. "
         "These minutes do not instruct a change to the works: where a decision requires a change, "
         "an instruction is issued and referenced here.")
    save_as_dotx(doc, out / "PTS-T07-Meeting-Minutes.dotx")


def t08_site_visit_report(out: Path):
    doc, section = new_document("document")
    build_header(doc, section)
    build_footer(doc, section)
    page1_block(doc, "SITE VISIT REPORT")
    spacer(doc, 10)

    t = make_table(doc, [40, 110], rows=0)
    for label in ("Report number", "Date and time", "Weather", "Inspector",
                  "Purpose of visit", "Scope inspected"):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        cell_text(doc, r.cells[1], "", "td text")

    spacer(doc, 10)
    para(doc, "t3 heading block", "SCOPE NOT INSPECTED").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body",
         "State what was not inspected and why. An inspection record silent on its limits will be "
         "read as covering everything.")

    spacer(doc, 20)
    para(doc, "t3 heading block", "OBSERVATIONS").paragraph_format.space_before = Pt(0)

    t = make_table(doc, [15, 30, 105], rows=0)
    for num in ("01", "02"):
        for label, text in [("Location", "Grid, level, room."),
                            ("Requirement", "Container and clause reference."),
                            ("Observed", "The condition as found."),
                            ("Assessment", "conforming / non-conforming / cannot determine"),
                            ("Action", "Owner and date."),
                            ("Photo", "Numbers.")]:
            r = t.add_row()
            no_row_break(r)
            cell_margins(r.cells[0], left=1.25, right=0)
            cell_margins(r.cells[1], left=0, right=1.25)
            cell_margins(r.cells[2], left=0, right=1.25)
            cell_text(doc, r.cells[0], num if label == "Location" else "", "t2 mono id")
            cell_text(doc, r.cells[1], label, "t2 label caps")
            cell_text(doc, r.cells[2], text, "td text")
        blank = t.add_row()
        row_height(blank, 10)

    spacer(doc, 10)
    para(doc, "t1 legal",
         "Every non-conformity cites the container and clause that states the requirement. A "
         "non-conformity without a citation is an opinion; with one it is verifiable and can be "
         "acted on without a further exchange.")
    save_as_dotx(doc, out / "PTS-T08-Site-Visit-Report.dotx")


def t13_site_survey_record(out: Path):
    """T13 — the record of a first site visit.

    Not T08. T08 measures the works against a documented design; here no design
    exists yet, so an assessment column would collect opinion in the shape of
    finding. What this template collects instead is *how each fact was
    established*, because ``ADOS-2.2.010`` makes the survey record the
    authoritative carrier for site conditions and ``ADOS-5.6.020`` makes every
    drawing derived from it state its method, date and accuracy.

    Three things carry the design and none of them is decoration:

    * the **method register**, because a record mixing a laser, a tape and a
      paced dimension has three accuracies and one blanket statement is false
      for two of them;
    * the **provenance tokens**, extending ``ADOS-4.5.090``'s ``(S)`` to the
      three cases a first visit actually produces — documented, reported,
      assumed — because a token set with only ``(S)`` in it forces an
      unmeasured fact to be recorded as measured or not at all, which is
      anti-pattern AP-28;
    * the **limitation register before the findings**, because
      ``ADOS-5.31.020`` says a record silent on its limits reads as covering
      everything, and the void nobody could open is the risk the project
      carries. A page break closes the opening block so the record starts
      clean; the promise is the order, not a page count, because a template
      cannot promise a page count for content it does not yet hold.
    """
    doc, section = new_document("document")
    build_header(doc, section)
    build_footer(doc, section)
    # SU is the practice-local type code: the standard's registry has no
    # survey type, which PTS-02 T13 records as a gap in ADOS-5.0.010.
    page1_block(doc, "SITE SURVEY RECORD", container_type="SU")
    spacer(doc, 10)

    # -- the visit ----------------------------------------------------------
    para(doc, "t3 heading block", "THE VISIT").paragraph_format.space_before = Pt(0)
    t = make_table(doc, [40, 110], rows=0)
    for label in ("Record number", "Date", "On site / off site", "Weather and light",
                  "Present, with role", "Access given by", "Purpose of the visit",
                  "Status of this record"):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        # The one field with a closed vocabulary carries it, so that the
        # third option is chosen rather than invented.
        prompt = ("initial   ·   supplemented by   ·   superseded by"
                  if label == "Status of this record" else "")
        cell_text(doc, r.cells[1], prompt, "td text")
    spacer(doc, 5)
    para(doc, "t2 body",
         "Light is recorded because it bounds what could be seen. A survey made at dusk in "
         "November has different coverage from one made at noon in June, and the limitation "
         "register below has to be read against it.")

    spacer(doc, 10)

    # -- method register ----------------------------------------------------
    para(doc, "t3 heading block", "METHOD REGISTER").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body",
         "Every method used, with the accuracy it delivers. Each dimension in the record cites a "
         "key from this table. Accuracy is stated per method and never once for the whole visit: "
         "a record that mixes a laser distance meter, a tape and a paced dimension has three "
         "accuracies, and one statement covering all of them is wrong about two.")
    t = make_table(doc, [15, 60, 30, 45], rows=1)
    head = t.rows[0]
    row_height(head, 5)
    repeat_header(head)
    for cell, label in zip(head.cells, ("Key", "Method or instrument",
                                        "Stated accuracy", "Applied to")):
        cell_margins(cell, left=0, right=1.25)
        cell_text(doc, cell, label, "th header")
    rule_below(head)
    for key in ("M1", "M2", "M3"):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        for cell in r.cells:
            cell_margins(cell, left=0, right=1.25)
        cell_text(doc, r.cells[0], key, "t2 mono id")
        cell_text(doc, r.cells[1], "", "td text")
        # No number here. A form that arrives pre-filled with an accuracy
        # nobody measured is the failure this template exists to stop.
        cell_text(doc, r.cells[2], "±        mm", "td number")
        cell_text(doc, r.cells[3], "", "td text")

    spacer(doc, 10)

    # -- provenance tokens --------------------------------------------------
    para(doc, "t3 heading block", "PROVENANCE TOKENS").paragraph_format.space_before = Pt(0)
    t = make_table(doc, [15, 135], rows=0)
    for token, meaning in (
        ("(S)", "Established by measurement on this visit, by a method in the register above."),
        ("(D)", "Taken from an existing document, which is cited by container and date."),
        ("(R)", "Reported by a named person, who is named."),
        ("(A)", "Assumed. The basis of the assumption is stated."),
    ):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], token, "t2 mono id")
        cell_text(doc, r.cells[1], meaning, "td text")

    spacer(doc, 10)

    # -- limitations, before the findings -----------------------------------
    para(doc, "t3 heading block",
         "WHAT WAS NOT ESTABLISHED").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body",
         "This section precedes the findings and is never left empty. A record silent on its "
         "limits will be read as covering everything, and on a first visit the void that could "
         "not be opened is the risk the project carries.")
    t = make_table(doc, [15, 45, 45, 45], rows=1)
    head = t.rows[0]
    row_height(head, 5)
    repeat_header(head)
    for cell, label in zip(head.cells, ("Ref", "Area or element",
                                        "Why it was not established",
                                        "Consequence if assumed")):
        cell_margins(cell, left=0, right=1.25)
        cell_text(doc, cell, label, "th header")
    rule_below(head)
    for ref in ("L1", "L2", "L3", "L4", "L5"):
        r = t.add_row()
        row_height(r, 10)
        no_row_break(r)
        for cell in r.cells:
            cell_margins(cell, left=0, right=1.25)
        cell_text(doc, r.cells[0], ref, "t2 mono id")
        for cell in r.cells[1:]:
            cell_text(doc, cell, "", "td text")

    doc.add_page_break()

    # -- the findings -------------------------------------------------------
    para(doc, "t3 heading block", "THE RECORD").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body",
         "One block per finding, in a fixed field order, so that a reader coming to it months "
         "later can reconstruct what was known without the surveyor. Where a finding is part "
         "measured and part inferred, PROVENANCE carries both tokens: a single token would make "
         "the whole finding read as one or the other.")
    spacer(doc, 5)

    t = make_table(doc, [15, 30, 105], rows=0)
    for num in ("01", "02"):
        for label, text, style in (
            ("Location", "Level, grid or room, and the direction of view.", "td text"),
            ("Finding", "What is there, as found.", "td text"),
            ("Provenance", "(S) M1   ·   (A) basis stated", "t2 mono id"),
            ("Dimension", "Value and unit, or an em dash where none was taken.", "td text"),
            ("Implication", "The surveyor's judgement, and marked as one.", "td text"),
            ("Photo", "Numbers from the register below.", "td text"),
        ):
            r = t.add_row()
            no_row_break(r)
            cell_margins(r.cells[0], left=1.25, right=0)
            cell_margins(r.cells[1], left=0, right=1.25)
            cell_margins(r.cells[2], left=0, right=1.25)
            cell_text(doc, r.cells[0], num if label == "Location" else "", "t2 mono id")
            cell_text(doc, r.cells[1], label, "t2 label caps")
            cell_text(doc, r.cells[2], text, style)
        blank = t.add_row()
        row_height(blank, 10)

    spacer(doc, 10)

    # -- photograph register ------------------------------------------------
    para(doc, "t3 heading block",
         "PHOTOGRAPH REGISTER").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body",
         "A photograph without a direction of view cannot be located, and one without a time "
         "cannot be read against the light recorded above.")
    t = make_table(doc, [15, 40, 30, 50, 15], rows=1)
    head = t.rows[0]
    row_height(head, 5)
    repeat_header(head)
    for cell, label in zip(head.cells, ("No", "Location", "Direction of view",
                                        "Subject", "Time")):
        cell_margins(cell, left=0, right=1.25)
        cell_text(doc, cell, label, "th header")
    rule_below(head)
    for n in range(1, 9):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        for cell in r.cells:
            cell_margins(cell, left=0, right=1.25)
        cell_text(doc, r.cells[0], f"{n:02d}", "t2 mono id")
        for cell in r.cells[1:4]:
            cell_text(doc, cell, "", "td text")
        cell_text(doc, r.cells[4], "", "td number")

    spacer(doc, 10)
    para(doc, "t1 legal",
         "Anything not marked with a provenance token was not established on this visit and is "
         "not a survey fact. Drawings derived from this record cite it by number and carry the "
         "(S) token only on dimensions traceable to a method in the register (ADOS-4.5.090, "
         "ADOS-5.6.020). This record is dated and is not revised: a later visit produces a new "
         "record that supplements or supersedes it, and this one stays as it was written, "
         "because it is evidence of what was known on this date.")
    save_as_dotx(doc, out / "PTS-T13-Site-Survey-Record.dotx")


def t14_information_request(out: Path):
    """T14 — asking a holder of records for a record that already exists.

    Not T09. An RFI asks the design team for a *decision* the documentation
    does not provide; this asks somebody outside it for a *document* that is
    already written. ``ADOS-2.2.010`` gives every fact class one authoritative
    carrier and forbids any other document from restating its value — so where
    that carrier is held by the client, a utility or a previous consultant, the
    practice has two lawful moves: obtain it and reference it, or record an
    assumption with its basis stated. This template is the instrument for the
    first, and without it the second happens by default.

    Upstream of T13. What arrives here is what a survey finding cites when it
    carries the ``(D)`` token; an item that comes back *does not exist* is what
    licenses ``(A)``, with this request's number as the basis.

    Two fields carry the design and both are the ones a real data request
    leaves out: **what each item is needed for**, named as a container or a
    decision, so the recipient can order the work; and **what happens if it is
    not supplied**, so that a due date has a consequence attached rather than
    being a wish.
    """
    doc, section = new_document("document")
    build_header(doc, section)
    build_footer(doc, section)
    # IR is the practice-local type code; PTS-02 T14 records that the
    # standard's registry has no type for obtaining a third party's records.
    page1_block(doc, "INFORMATION REQUEST", container_type="IR")
    spacer(doc, 10)

    # -- who is asked, and by when ------------------------------------------
    para(doc, "t3 heading block", "THE REQUEST").paragraph_format.space_before = Pt(0)
    t = make_table(doc, [40, 110], rows=0)
    for label, prompt in (
        ("Request number", ""),
        ("To, organisation", ""),
        ("For the attention of", ""),
        # Not decoration: the capacity decides whether an answer is owed at
        # all, and an unanswered request against a duty is a different fact
        # from an unanswered favour.
        ("Asked in the capacity of", "client under the appointment / statutory "
                                     "undertaker / previous consultant"),
        ("Date of request", ""),
        ("Response needed by", ""),
        ("Why that date", "the container or decision that waits on it"),
    ):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        cell_text(doc, r.cells[1], prompt, "td text")

    spacer(doc, 10)
    para(doc, "t3 heading block",
         "WHY THIS IS ASKED").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body",
         "Each fact below has one authoritative carrier, and it is not held by this practice. We "
         "may reference what you hold; we may not restate it. Where an item is not supplied we "
         "record the fact as an assumption, name this request as the basis, and carry the "
         "consequence stated against that item.")

    spacer(doc, 10)

    # -- the closed response vocabulary -------------------------------------
    para(doc, "t3 heading block",
         "RESPONSE VOCABULARY").paragraph_format.space_before = Pt(0)
    t = make_table(doc, [40, 110], rows=0)
    for token, meaning in (
        ("supplied", "The record is attached or issued separately, and referenced below."),
        ("does not exist", "No such record is held. This is an answer, and it is what "
                           "licenses an assumption downstream."),
        ("exists, not released", "Held, and withheld. The reason is stated."),
        ("superseded by", "Replaced. The reference of the replacement is given."),
    ):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], token, "t2 mono id")
        cell_text(doc, r.cells[1], meaning, "td text")
    spacer(doc, 5)
    para(doc, "t2 body",
         "A row left blank is indistinguishable from an item nobody asked about. Every item "
         "carries one of the four.")

    doc.add_page_break()

    # -- the items ----------------------------------------------------------
    para(doc, "t3 heading block", "ITEMS REQUESTED").paragraph_format.space_before = Pt(0)
    t = make_table(doc, [15, 30, 105], rows=0)
    for num in ("01", "02"):
        for label, text, style in (
            ("Item", "The record requested, named as its holder would name it.", "td text"),
            ("Needed for", "The container or the decision that waits on it.", "td text"),
            ("Form", "File format, scale or fidelity, coordinate system where "
                     "one applies.", "td text"),
            ("Holder", "Who is expected to hold it.", "td text"),
            ("If not supplied", "What is done instead, and the consequence carried.", "td text"),
            ("Response", "supplied / does not exist / exists, not released / superseded by",
             "t2 mono id"),
            ("Reference", "Identifier and date of what arrived.", "t2 mono id"),
        ):
            r = t.add_row()
            no_row_break(r)
            cell_margins(r.cells[0], left=1.25, right=0)
            cell_margins(r.cells[1], left=0, right=1.25)
            cell_margins(r.cells[2], left=0, right=1.25)
            cell_text(doc, r.cells[0], num if label == "Item" else "", "t2 mono id")
            cell_text(doc, r.cells[1], label, "t2 label caps")
            cell_text(doc, r.cells[2], text, style)
        blank = t.add_row()
        row_height(blank, 10)

    spacer(doc, 10)

    # -- state ---------------------------------------------------------------
    para(doc, "t3 heading block", "STATE OF THIS REQUEST").paragraph_format.space_before = Pt(0)
    t = make_table(doc, [40, 110], rows=0)
    for label in ("Items requested", "Supplied", "Outstanding"):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        cell_text(doc, r.cells[1], "", "td number")

    spacer(doc, 10)
    para(doc, "t1 legal",
         "This request is revised as items are answered, and it is the only record in the "
         "correspondence family that is: an RFI, a transmittal and a survey record are dated "
         "records of a moment, while this one tracks a state that changes. The superseded "
         "revision stays in the revision log. An item still outstanding at the date above "
         "becomes an assumption in the survey record, marked (A) with this request number as "
         "its basis (ADOS-2.2.010, ADOS-4.5.090).")
    save_as_dotx(doc, out / "PTS-T14-Information-Request.dotx")


def t09_rfi(out: Path):
    doc, section = new_document("document")
    build_header(doc, section)
    build_footer(doc, section)
    page1_block(doc, "REQUEST FOR INFORMATION")
    spacer(doc, 10)

    t = make_table(doc, [40, 110], rows=0)
    for label, value in [("RFI number", ""), ("Date raised", ""), ("Response required by", ""),
                         ("Justification for date", ""), ("Raised by", ""), ("Responder", ""),
                         ("Subject", ""), ("Location", "container, grid, level, room"),
                         ("Status", "open / answered / closed")]:
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        cell_text(doc, r.cells[1], value, "td text")

    spacer(doc, 20)
    # The question is the largest text on the page. An RFI whose question has to
    # be extracted from a paragraph gets an answer to a different question.
    para(doc, "t3 heading block", "QUESTION").paragraph_format.space_before = Pt(0)
    para(doc, "t4 statement", "One question, stated as a question.")

    spacer(doc, 10)
    para(doc, "t3 heading block", "CONTEXT").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body", "What the documentation currently says, and why it is insufficient.")
    para(doc, "t2 body", "Proposed answer, where the raiser has one.")

    spacer(doc, 10)
    t = make_table(doc, [40, 110], rows=0)
    for label in ("Cost implication", "Programme implication"):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        cell_text(doc, r.cells[1], "as assessed by the raiser", "td text")

    spacer(doc, 20)
    para(doc, "t3 heading block", "RESPONSE").paragraph_format.space_before = Pt(0)
    # 60 mm of clear space: a cramped response field produces one-line answers to
    # questions that need three (PTS-02 T09).
    spacer(doc, 60)
    t = make_table(doc, [40, 110], rows=0)
    for label in ("Responded by", "Date of response", "Containers to be revised",
                  "Instruction to be issued"):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        cell_text(doc, r.cells[1], "", "td text")

    spacer(doc, 10)
    para(doc, "t1 legal",
         "An RFI whose answer changes the documented design is not closed until the affected "
         "containers have been revised and issued, and this record cites that revision. Attachments "
         "are referenced, never embedded: an embedded drawing is an uncontrolled copy.")
    save_as_dotx(doc, out / "PTS-T09-Request-for-Information.dotx")


def t11_transmittal(out: Path):
    doc, section = new_document("document")
    build_header(doc, section)
    build_footer(doc, section)
    page1_block(doc, "TRANSMITTAL")
    spacer(doc, 10)

    t = make_table(doc, [40, 110], rows=0)
    for label, value in [("Transmittal number", ""), ("Date", ""), ("Sender", ""),
                         ("Recipients", "name · organisation · role"),
                         ("Medium", ""), ("Acknowledgement", "requested by")]:
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        cell_margins(r.cells[0], left=0, right=1.25)
        cell_margins(r.cells[1], left=0, right=1.25)
        cell_text(doc, r.cells[0], label, "t2 label caps")
        cell_text(doc, r.cells[1], value, "td text")

    spacer(doc, 20)
    para(doc, "t3 heading block", "REASON FOR ISSUE").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body",
         "The reason determines how the recipient treats everything below it.")

    spacer(doc, 20)
    para(doc, "t3 heading block", "CONTAINERS ISSUED").paragraph_format.space_before = Pt(0)
    cols = [("Container identifier", 55), ("Title", 45), ("Rev", 12),
            ("Status", 14), ("Size", 10), ("Format", 14)]
    t = make_table(doc, [w for _, w in cols], rows=0)
    hdr = t.add_row()
    row_height(hdr, 10)
    repeat_header(hdr)
    for cell, (label, _w) in zip(hdr.cells, cols):
        cell_margins(cell, left=0, right=1.25, top=1.25, bottom=1.25)
        shade(cell, "T1")
        cell_text(doc, cell, label, "th header")
    rule_below(hdr)
    for i in range(12):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        for cell in r.cells:
            cell_margins(cell, left=0, right=1.25)
            cell_text(doc, cell, "", "td text")
        if (i + 1) % 10 == 0:
            rule_below(r)

    spacer(doc, 20)
    # Supersession sits alone in its own band. It is the part recipients skip,
    # and space is the only mechanism available to stop them (PTS-02 T11).
    para(doc, "t3 heading block", "SUPERSESSION INSTRUCTION").paragraph_format.space_before = Pt(0)
    para(doc, "t2 body",
         "The container revisions listed below are superseded by this issue and shall be withdrawn "
         "from use.")
    cols = [("Container identifier", 55), ("Superseded revision", 45), ("Action", 50)]
    t = make_table(doc, [w for _, w in cols], rows=0)
    hdr = t.add_row()
    row_height(hdr, 10)
    for cell, (label, _w) in zip(hdr.cells, cols):
        cell_margins(cell, left=0, right=1.25, top=1.25, bottom=1.25)
        shade(cell, "T1")
        cell_text(doc, cell, label, "th header")
    rule_below(hdr)
    for _ in range(6):
        r = t.add_row()
        row_height(r, 5)
        no_row_break(r)
        for cell in r.cells:
            cell_margins(cell, left=0, right=1.25)
            cell_text(doc, cell, "", "td text")

    spacer(doc, 20)
    para(doc, "t1 legal",
         "A transmittal is never revised. An error produces a new transmittal referencing this one.")
    save_as_dotx(doc, out / "PTS-T11-Transmittal.dotx")


def t06a_door_schedule(out: Path):
    doc, section = new_document("sheet", "A3")
    sheet_footer(doc, section, "DOOR SCHEDULE — PART A")
    cols = [("Mark", 22), ("Room from", 63), ("Room to", 63), ("Level", 16), ("Type", 32),
            ("SO width", 24), ("SO height", 24), ("Clear width", 24), ("Clear height", 24),
            ("Leaf size", 38), ("Handing", 22), ("Fire / smoke", 24), ("Rev", 14)]
    schedule_sheet(doc, cols,
                   "Clear opening width is measured with the door open at 90 degrees. It is not "
                   "derivable from the leaf size and it is the dimension a code is checked against. "
                   "Part B carries ironmongery, finishes and accessories, keyed on Mark.")
    save_as_dotx(doc, out / "PTS-T06a-Door-Schedule.dotx")


def t06b_window_schedule(out: Path):
    doc, section = new_document("sheet", "A3")
    sheet_footer(doc, section, "WINDOW SCHEDULE")
    cols = [("Mark", 22), ("Room", 75), ("Level", 16), ("Elevation", 30), ("Type", 32),
            ("SO width", 24), ("SO height", 24), ("Cill FFL", 26), ("Head FFL", 26),
            ("Opening lights", 45), ("Free area", 30), ("U-value", 26), ("Rev", 14)]
    schedule_sheet(doc, cols,
                   "Free opening area is the compliance quantity and is not derivable from the leaf "
                   "size. Every window whose cill falls below the guarding threshold states its "
                   "guarding provision or the reason none is required.")
    save_as_dotx(doc, out / "PTS-T06b-Window-Schedule.dotx")


def t10_revision_log(out: Path):
    doc, section = new_document("sheet", "A3")
    sheet_footer(doc, section, "REVISION LOG")
    fixed = [("Container identifier", 62), ("Sheet", 22), ("Title", 90), ("Type", 16),
             ("Size", 14), ("Rev", 14), ("Status", 18), ("Date", 24)]
    issues = [(f"I{n:02d}", 10) for n in range(1, 14)]
    schedule_sheet(doc, fixed + issues,
                   "This log is regenerated at every issue and is never maintained by hand: a "
                   "hand-maintained register is a duplicate of the set's own state and diverges at "
                   "exactly the moment it matters, which is a rushed issue. Columns I01 onward are "
                   "the issue matrix; each cell holds the revision issued at that date.")
    save_as_dotx(doc, out / "PTS-T10-Revision-Log.dotx")


BUILDERS = [t05_specification, t07_meeting_minutes, t08_site_visit_report, t09_rfi,
            t11_transmittal, t06a_door_schedule, t06b_window_schedule, t10_revision_log,
            t13_site_survey_record, t14_information_request]


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "templates"
    out.mkdir(parents=True, exist_ok=True)
    for fn in BUILDERS:
        fn(out)
    built = sorted(out.glob("*.dotx"))
    for f in built:
        print(f"{f.name:44} {f.stat().st_size / 1024:6.1f} KB")
    print(f"\n{len(built)} templates built in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
