#!/usr/bin/env python3
"""
report/build_report.py - builds the Lab 2 report from the project itself.

    make report            (both reports; make_figures.py runs first)
    make full-report       (only this one)

Inputs   report/cover.json          cover-page fields - replace the [..] placeholders
         test_examples/             outputs of the programs (make examples, make demo)
         report/build/fig/          diagrams, chart and trimmed screenshots
         src/ tests/ docker/ ...    code excerpts and Appendix A
Output   report/DES_Lab2_Report.docx and report/DES_Lab2_Report.pdf

The table of contents carries real page numbers: the document is built, converted
to PDF with LibreOffice, the page of every heading is read back from the PDF and
the document is built again with those numbers.
"""
import csv
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EX = os.path.join(ROOT, "test_examples")
BUILD = os.path.join(HERE, "build")
FIG = os.path.join(BUILD, "fig")
DOCX = os.path.join(HERE, "DES_Lab2_Report.docx")
PDF = os.path.join(HERE, "DES_Lab2_Report.pdf")

FONT, MONO = "Arial", "Courier New"
ACCENT = RGBColor(0x1F, 0x4E, 0x8C)
GRAY = RGBColor(0x59, 0x59, 0x59)
HEADER_FILL, CODE_FILL, NOTE_FILL = "DCE6F2", "F4F4F2", "FFF4D6"
TEXT_WIDTH = 17.0   # cm, A4 with 2 cm margins

# --------------------------------------------------------------------------- #
#  Data from the project                                                       #
# --------------------------------------------------------------------------- #


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def example(name):
    with open(os.path.join(EX, name), encoding="utf-8") as f:
        return f.read()


def csv_rows(name):
    with open(os.path.join(EX, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def c_function(path, name):
    """A C function with the comment right above it."""
    lines = read(path).split("\n")
    start = next(i for i, l in enumerate(lines)
                 if re.match(rf"^[A-Za-z][\w \*]*\b{name}\(", l) and not l.rstrip().endswith(";"))
    first = start
    while first > 0 and re.match(r"^(/\*| \*|//)", lines[first - 1]):
        first -= 1
    end = start
    while not lines[end].startswith("}"):
        end += 1
    return "\n".join(lines[first:end + 1])


def c_block(path, start_pattern, end_pattern):
    lines = read(path).split("\n")
    start = next(i for i, l in enumerate(lines) if re.search(start_pattern, l))
    end = next(i for i in range(start, len(lines)) if re.search(end_pattern, lines[i]))
    return "\n".join(lines[start:end + 1])


def trace(name="trace_textbook_encrypt.csv"):
    return csv_rows(name)


def pick(rows, method=None, rounds=None, step=None, lab=None, detail=None):
    out = []
    for r in rows:
        if method and r["method"] != method:
            continue
        if rounds is not None and int(r["round"]) not in rounds:
            continue
        if step and step not in r["des_step"]:
            continue
        if lab and not r["lab_item"].startswith(lab):
            continue
        if detail is not None and int(r["detail"]) != detail:
            continue
        out.append(r)
    return out


def step_table_rows(rows):
    return [[r["round"] if r["round"] != "0" else "-", r["input"], r["method"], r["output"],
             breakable(f'{r["lab_item"]} {r["des_step"]}')] for r in rows]


def breakable(text):
    """Allow a line break after '/' (zero-width space) in narrow table cells."""
    return text.replace("/", "/\u200b")


def parse_summary(name):
    """Rows of the Table 4.2 style summary printed by des_trace -f summary."""
    rows = []
    for line in example(name).splitlines():
        m = re.match(r"^\s*(IP-1|IP)\s+([0-9a-f]{8})\s+([0-9a-f]{8})$", line)
        if m:
            rows.append((m.group(1), "", "", m.group(2), m.group(3)))
            continue
        m = re.match(r"^\s*(\d+)\s+(K\d+)\s+([0-9a-f]{16})\s+([0-9a-f]{8})\s+([0-9a-f]{8})$", line)
        if m:
            rows.append(m.groups())
    return rows


def first_payload_from_capture():
    """(src, dst, payload bytes) of the first data packet in the tcpdump -X dump."""
    text = example("docker_run/des_lan_capture.txt")
    packets, current = [], None
    for line in text.splitlines():
        if re.match(r"^\d\d:\d\d:\d\d", line):
            current = {"head": line, "hex": ""}
            packets.append(current)
        elif current and re.match(r"^\s+0x[0-9a-f]{4}:", line):
            current["hex"] += "".join(line.split(":", 1)[1][:41].split())
    for p in packets:
        if "length 0" in p["head"]:
            continue
        data = bytes.fromhex(p["hex"])
        ihl = (data[0] & 0x0F) * 4
        tcp_len = (data[ihl + 12] >> 4) * 4
        m = re.search(r"IP (\S+) > (\S+):", p["head"])
        return m.group(1), m.group(2), data[ihl + tcp_len:]
    raise ValueError("no data packet in the capture")


# The DES example as printed in the lab handout (typing errors included)
HANDOUT_42 = [
    ("IP", "", "5a005a00", "3cf03c0f"),
    ("1", "1e030f03080d2930", "3cf03c0f", "bad22845"),
    ("2", "0a31293432242318", "bad22845", "99e9b723"),
    ("3", "23072318201d0c1d", "99e9b723", "0bae3b9e"),
    ("4", "05261d3824311a20", "0bae3b9e", "42415649"),
    ("5", "3325340136002c25", "42415649", "18b3fa41"),
    ("6", "123a2d0d04262alc", "18b3fa41", "9616fe23"),
    ("7", "021f120blc130611", "9616fe23", "67117cf2"),
    ("8", "1c10372a2832002b", "67117cf2", "c11bfc09"),
    ("9", "04292a380c341f03", "c11bfc09", "887fbc6c"),
    ("10", "2703212607280403", "887fbc6c", "600f7e8b"),
    ("11", "2826390c31261504", "600f7e8b", "f596506e"),
    ("12", "12071c241a0a0f08", "f596506e", "738538b8"),
    ("13", "300935393c0d100b", "738538b8", "c6a62c4e"),
    ("14", "311e09231321182a", "c6a62c4e", "56b0bd75"),
    ("15", "283d3e0227072528", "56b0bd75", "75e8fd8f"),
    ("16", "2921080b13143025", "75e8fd8f", "25896490"),
    ("IP-1", "", "25896490", "89ecac3b"),
]

SUBMISSION_LAYOUT = """\
Lab2_DES/
|-- report/
|   |-- DES_Lab2_Report.pdf         this report
|   |-- DES_Lab2_Report.docx        the same report, editable
|   |-- figures/                    the original screenshots (tools/screenshots.py)
|   `-- build_report.py, make_figures.py, cover.json    regenerate it: make report
|-- src/                            C source code (Appendix A)
|-- tests/                          unit tests, cross-check, loopback network test
|-- debug/des_watch.py              GDB script of Section 2.6
|-- docker/                         Dockerfile, demo.sh
|-- docker-compose.yml              the two machines and the virtual LAN
|-- Makefile, README.md
|-- .vscode/                        debugger configurations for Visual Studio Code
|-- tools/                          screenshots.py, make_examples.sh, package.sh
|-- bin/                            executables, Linux x86-64 (built on Debian 12)
|   |-- tcpServer, tcpClient        the distributed application (Machine B, Machine A)
|   |-- des_trace, des_avalanche    step tables, avalanche tables
|   `-- des_test                    unit tests
|-- test_examples/                  inputs and outputs of every test
|   |-- messages_machine_a.txt, messages_machine_b.txt    scripted conversation
|   |-- trace_*.txt|csv|md, summary_*.txt                 step tables
|   |-- avalanche_*.txt|csv                               Tables 4.3 and 4.4
|   |-- unit_tests.txt, crosscheck.txt, loopback_test.txt, gdb_watch_steps.txt
|   |-- loopback/                   logs of the loopback test
|   `-- docker_run/                 logs, network settings, packet capture (.pcap)
`-- starter_original/               the unmodified starter code, for comparison

Build and test (Linux; gcc, make; python3 + pycryptodome and openssl for the cross-check)
    make                build bin/
    make test           unit tests of every DES step
    make check          + cross-check and loopback network test
    make examples       regenerate test_examples/

Two machines (Docker)
    docker compose up -d --build
    docker exec -it machine-b tcpServer                       # Machine B
    docker exec -it machine-a tcpClient -s 172.28.10.20       # Machine A
    make demo           scripted conversation + packet capture + checks
    docker compose down

One step table / avalanche table
    bin/des_trace -k 0f1571c947d9e859 -i 02468aceeca86420 [-s] [-d] [-f table|csv|md|summary]
    bin/des_avalanche -P 4        bin/des_avalanche -K 4
"""

# --------------------------------------------------------------------------- #
#  docx helpers                                                                #
# --------------------------------------------------------------------------- #


def set_rfonts(rpr, name):
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rfonts.get(qn(attr)) is not None:
            del rfonts.attrib[qn(attr)]
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def run_font(run, name, size=None):
    run.font.name = name
    set_rfonts(run._r.get_or_add_rPr(), name)
    if size:
        run.font.size = Pt(size)


def style_color(style, rgb):
    style.font.color.rgb = rgb
    color = style.element.rPr.find(qn("w:color"))
    for attr in ("w:themeColor", "w:themeShade", "w:themeTint"):
        if color is not None and color.get(qn(attr)) is not None:
            del color.attrib[qn(attr)]


def shade_cell(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.insert_element_before(shd, "w:noWrap", "w:tcMar", "w:textDirection",
                               "w:tcFitText", "w:vAlign", "w:hideMark")


PPR_AFTER_BORDER = ("w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
                    "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
                    "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
                    "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
                    "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
                    "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
                    "w:pPrChange")


def shade_paragraph_style(style, fill):
    """Background colour plus a border of the same colour (as padding)."""
    ppr = style.element.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    for side, space in (("top", "3"), ("left", "4"), ("bottom", "3"), ("right", "4")):
        el = OxmlElement(f"w:{side}")
        for k, v in (("w:val", "single"), ("w:sz", "4"), ("w:space", space), ("w:color", fill)):
            el.set(qn(k), v)
        bdr.append(el)
    ppr.insert_element_before(bdr, *PPR_AFTER_BORDER)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    ppr.insert_element_before(shd, *PPR_AFTER_BORDER[1:])


def table_margins(table, top=30, bottom=30, left=70, right=70):
    tblpr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(value))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblpr.insert_element_before(mar, "w:tblLook", "w:tblCaption", "w:tblDescription")


def repeat_header(row):
    trpr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trpr.append(el)


def cant_split(row):
    trpr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    trpr.insert(0, el)


def paragraph_border_bottom(p, color="1F4E8C", size=8):
    ppr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", str(size)), ("w:space", "4"), ("w:color", color)):
        bottom.set(qn(k), v)
    bdr.append(bottom)
    ppr.insert_element_before(bdr, "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku",
                              "w:wordWrap", "w:overflowPunct", "w:topLinePunct",
                              "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd",
                              "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing",
                              "w:mirrorIndents", "w:suppressOverlap", "w:jc")


def add_field(paragraph, instruction):
    run = paragraph.add_run()
    r = run._r
    for kind, text in (("begin", None), ("instr", instruction), ("separate", None),
                       ("value", "1"), ("end", None)):
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" {text} "
        elif kind == "value":
            el = OxmlElement("w:t")
            el.text = text
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        r.append(el)
    return run


def norm(text):
    text = re.sub(r"[\^_]\{([^}]*)\}", r"\1", text)
    return re.sub(r"[^a-z0-9]", "", text.lower())


def norm_nosup(text):
    """Like norm(), without superscript/subscript text (the PDF may move it)."""
    return norm(re.sub(r"[\^_]\{[^}]*\}", "", text))


TOKENS = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\^\{[^}]+\}|_\{[^}]+\})")


class Report:
    def __init__(self, cover, labels=None, headings=None, pages=None):
        self.doc = Document()
        self.cover = cover
        self.labels = labels or {}
        self.toc_entries = headings or []
        self.pages = pages or {}
        self.new_labels = {}
        self.headings = []
        self.n_fig = 0
        self.n_tab = 0
        self._styles()
        self._page()

    # ---- setup ----
    def _styles(self):
        styles = self.doc.styles
        defaults = styles.element.find(qn("w:docDefaults"))
        rpr_default = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
        set_rfonts(rpr_default, FONT)

        normal = styles["Normal"]
        normal.font.name = FONT
        normal.font.size = Pt(10.5)
        set_rfonts(normal.element.get_or_add_rPr(), FONT)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.15

        for level, size, before, after in ((1, 16, 16, 8), (2, 13, 14, 6), (3, 11.5, 12, 4)):
            h = styles[f"Heading {level}"]
            h.font.name = FONT
            set_rfonts(h.element.get_or_add_rPr(), FONT)
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.italic = False
            style_color(h, ACCENT)
            h.paragraph_format.space_before = Pt(before)
            h.paragraph_format.space_after = Pt(after)
            h.paragraph_format.keep_with_next = True
            h.paragraph_format.line_spacing = 1.0

        cap = styles["Caption"]
        cap.font.name = FONT
        set_rfonts(cap.element.get_or_add_rPr(), FONT)
        cap.font.size = Pt(9)
        cap.font.bold = False
        cap.font.italic = False
        style_color(cap, GRAY)
        cap.paragraph_format.space_before = Pt(3)
        cap.paragraph_format.space_after = Pt(10)

        code = styles.add_style("Code", WD_STYLE_TYPE.PARAGRAPH)
        code.base_style = normal
        code.font.name = MONO
        set_rfonts(code.element.get_or_add_rPr(), MONO)
        code.font.size = Pt(7.5)
        code.paragraph_format.space_before = Pt(0)
        code.paragraph_format.space_after = Pt(0)
        code.paragraph_format.line_spacing = 1.0
        code.paragraph_format.left_indent = Cm(0.15)
        code.paragraph_format.right_indent = Cm(0.15)
        code.paragraph_format.widow_control = False
        shade_paragraph_style(code, CODE_FILL)

        for level in (1, 2, 3):
            t = styles.add_style(f"TOC Line {level}", WD_STYLE_TYPE.PARAGRAPH)
            t.base_style = normal
            t.font.size = Pt(10.5 if level == 1 else 10)
            t.font.bold = level == 1
            t.paragraph_format.left_indent = Cm(0.6 * (level - 1))
            t.paragraph_format.space_before = Pt(5 if level == 1 else 0)
            t.paragraph_format.space_after = Pt(1)
            t.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH), WD_TAB_ALIGNMENT.RIGHT,
                                                      WD_TAB_LEADER.DOTS)

    def _page(self):
        s = self.doc.sections[0]
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)
        s.left_margin = s.right_margin = Cm(2.0)
        s.top_margin, s.bottom_margin = Cm(2.0), Cm(1.8)
        s.header_distance, s.footer_distance = Cm(0.9), Cm(0.8)
        s.different_first_page_header_footer = True

        hp = s.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run("CMPE455/CMSE456  -  Lab 2: DES on Two Computers")
        r.font.size = Pt(8.5)
        r.font.color.rgb = GRAY
        paragraph_border_bottom(hp, "BFBFBF", 4)

        fp = s.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for part in ("Page ", "PAGE", " of ", "NUMPAGES"):
            run = add_field(fp, part) if part.isupper() else fp.add_run(part)
            run.font.size = Pt(8.5)
            run.font.color.rgb = GRAY

    # ---- text ----
    def resolve(self, text):
        def sub(m):
            label = m.group(1)
            kind = "Figure" if label.startswith("fig") else "Table"
            return self.labels.get(label, f"{kind} ??")
        return re.sub(r"\{((?:fig|tab):[\w-]+)\}", sub, text)

    def runs(self, p, text, size=None, color=None, bold=None):
        for part in TOKENS.split(self.resolve(text)):
            if not part:
                continue
            if part.startswith("**"):
                r = p.add_run(part[2:-2])
                r.bold = True
            elif part.startswith("`"):
                r = p.add_run(part[1:-1])
                run_font(r, MONO, (size or 10.5) - 1.2)
            elif part.startswith("^{"):
                r = p.add_run(part[2:-1])
                r.font.superscript = True
            elif part.startswith("_{"):
                r = p.add_run(part[2:-1])
                r.font.subscript = True
            else:
                r = p.add_run(part)
            if size and not part.startswith("`"):
                r.font.size = Pt(size)
            if color is not None:
                r.font.color.rgb = color
            if bold is not None and not part.startswith("**"):
                r.bold = bold
        return p

    def para(self, text, size=None, align=None, after=None, before=None, keep=False,
             color=None, bold=None, indent=None, style=None):
        p = self.doc.add_paragraph(style=style)
        self.runs(p, text, size=size, color=color, bold=bold)
        if align is not None:
            p.alignment = align
        if after is not None:
            p.paragraph_format.space_after = Pt(after)
        if before is not None:
            p.paragraph_format.space_before = Pt(before)
        if indent is not None:
            p.paragraph_format.left_indent = Cm(indent)
        if keep:
            p.paragraph_format.keep_with_next = True
        return p

    def bullets(self, items, size=None):
        for item in items:
            p = self.doc.add_paragraph(style="List Bullet")
            self.runs(p, item, size=size)
            p.paragraph_format.space_after = Pt(3)

    def steps(self, items):
        for i, item in enumerate(items, 1):
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.7)
            p.paragraph_format.first_line_indent = Cm(-0.5)
            p.paragraph_format.space_after = Pt(3)
            self.runs(p, f"{i}.  " + item)

    def heading(self, text, level, new_page=False, toc=True):
        p = self.doc.add_paragraph(style=f"Heading {level}")
        if new_page:
            p.paragraph_format.page_break_before = True
        self.runs(p, text)
        if toc:
            self.headings.append((level, text))
        return p

    def note(self, text):
        t = self.doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.rows[0].cells[0]
        cell.width = Cm(TEXT_WIDTH)
        shade_cell(cell, NOTE_FILL)
        table_margins(t, 80, 80, 140, 140)
        p = cell.paragraphs[0]
        self.runs(p, text, size=9.5)
        p.paragraph_format.space_after = Pt(0)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # ---- numbered objects ----
    def caption(self, kind, text, label=None, keep=False):
        if kind == "Figure":
            self.n_fig += 1
            number = self.n_fig
        else:
            self.n_tab += 1
            number = self.n_tab
        if label:
            self.new_labels[label] = f"{kind} {number}"
        p = self.doc.add_paragraph(style="Caption")
        r = p.add_run(f"{kind} {number}.  ")
        r.bold = True
        self.runs(p, text)
        if keep:
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_after = Pt(3)
        return p

    def figure(self, name, width, caption=None, label=None):
        """The image, centred; caption=None leaves out the "Figure N." line."""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = caption is not None
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(0 if caption is not None else 10)
        p.add_run().add_picture(os.path.join(FIG, name), width=Cm(width))
        if caption is not None:
            self.caption("Figure", caption, label)

    def table(self, header, rows, widths, caption=None, label=None, mono=(), size=8,
              center=(), bold_col0=False, fills=None, keep_together=None):
        assert abs(sum(widths) - TEXT_WIDTH) < 0.6 or sum(widths) < TEXT_WIDTH, widths
        if caption:
            self.caption("Table", caption, label, keep=True)
        t = self.doc.add_table(rows=1, cols=len(header))
        t.style = self.doc.styles["Table Grid"]
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        table_margins(t)
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(w)
        for i, text in enumerate(header):
            cell = t.rows[0].cells[i]
            cell.width = Cm(widths[i])
            shade_cell(cell, HEADER_FILL)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            self.runs(p, text, size=size, bold=True)
            p.paragraph_format.keep_with_next = True
        repeat_header(t.rows[0])
        together = keep_together if keep_together is not None else len(rows) <= 12
        for n, row in enumerate(rows):
            tr = t.add_row()
            cant_split(tr)
            for i, value in enumerate(row):
                cell = tr.cells[i]
                cell.width = Cm(widths[i])
                if fills and fills.get((n, i)):
                    shade_cell(cell, fills[(n, i)])
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                if together and n < len(rows) - 1:
                    p.paragraph_format.keep_with_next = True
                if i in center:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                value = str(value)
                if i in mono:
                    r = p.add_run(value)
                    run_font(r, MONO, size - 0.5)
                else:
                    self.runs(p, value, size=size, bold=True if (bold_col0 and i == 0) else None)
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(4)
        spacer.paragraph_format.line_spacing = 1.0
        return t

    def code(self, text, size=7.5):
        lines = text.expandtabs(4).rstrip("\n").split("\n")
        short = len(lines) <= 20
        for i, line in enumerate(lines):
            p = self.doc.add_paragraph(style="Code")
            r = p.add_run(line if line else " ")
            r.font.size = Pt(size)
            if short and i < len(lines) - 1:
                p.paragraph_format.keep_with_next = True
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(4)
        spacer.paragraph_format.line_spacing = 1.0

    def page_break(self):
        self.doc.add_page_break()

    # ---- table of contents ----
    def toc(self):
        for level, text in self.toc_entries:
            p = self.doc.add_paragraph(style=f"TOC Line {level}")
            self.runs(p, text)
            p.add_run("\t" + str(self.pages.get(norm(text), "00")))

    def save(self, path):
        # python-docx's template has <w:zoom> without the required w:percent
        zoom = self.doc.settings.element.find(qn("w:zoom"))
        if zoom is not None and zoom.get(qn("w:percent")) is None:
            zoom.set(qn("w:percent"), "100")
        self.doc.save(path)


# --------------------------------------------------------------------------- #
#  The report                                                                  #
# --------------------------------------------------------------------------- #

STEP_HEADER = ["Round", "Input to method", "Method name", "Method output", "Current DES step"]
STEP_WIDTHS = [1.1, 4.3, 5.0, 3.8, 2.8]


def step_table(R, rows, caption, label):
    R.table(STEP_HEADER, step_table_rows(rows), STEP_WIDTHS, caption=caption, label=label,
            mono=(1, 2, 3), size=7.5, center=(0,))


def cover_page(R):
    c = R.cover
    placeholder = lambda v: str(v).startswith("[")

    def line(text, size, bold=False, color=None, after=4, before=0):
        p = R.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.space_before = Pt(before)
        r = p.add_run(text)
        r.font.size = Pt(size)
        r.bold = bold
        if color is not None:
            r.font.color.rgb = color
        if placeholder(text):
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        return p

    line(c["university"], 16, True, before=30, after=4)
    line(c["department"], 13, after=2)
    line(c["program"], 13, after=26)
    line(c["course"], 13, True, ACCENT, after=26)
    line("Lab 2 Report", 14, after=6)
    line("DES on Two Computers", 28, True, ACCENT, after=6)
    sub = line("A distributed DES application: create, encrypt, send, receive, decrypt "
               "and display messages between two machines", 11, color=GRAY, after=36)
    paragraph_border_bottom(sub, "1F4E8C", 8)

    fields = [("University", c["university"]), ("Department", c["department"]),
              ("Program", c["program"]), ("Course", c["course"]), ("Lab", c["lab"]),
              ("Subject", c["subject"]), ("Team members", "\n".join(c["team_members"])),
              ("Lecturer", c["lecturer"]), ("Lab Assistant", c["lab_assistant"]),
              ("Year", c["year"]), ("Semester", c["semester"]), ("City", c["city"]),
              ("Country", c["country"])]
    t = R.doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    table_margins(t, 50, 50, 100, 100)
    for label, value in fields:
        cells = t.add_row().cells
        cells[0].width, cells[1].width = Cm(4.2), Cm(9.8)
        p = cells[0].paragraphs[0]
        r = p.add_run(label)
        r.bold = True
        r.font.size = Pt(10.5)
        r.font.color.rgb = ACCENT
        p.paragraph_format.space_after = Pt(0)
        for i, part in enumerate(str(value).split("\n")):
            p = cells[1].paragraphs[0] if i == 0 else cells[1].add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(part)
            r.font.size = Pt(10.5)
            if placeholder(part):
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW


def build(R):
    tr = trace()
    tr_s = trace("trace_textbook_encrypt_with_sboxes.csv")

    cover_page(R)

    # ------------------------------------------------------------------ outline
    R.heading("Outline", 1, new_page=True, toc=False)
    R.para("This report documents Lab 2 of CMPE455/CMSE456: the Data Encryption Standard "
           "(DES) implemented in C as a distributed application that runs on two computers. "
           "Section 1 defines the problem. Section 2 describes the work done: the structure "
           "of the program (one C function per DES step), the verification of every DES "
           "transformation with the debugger and with the example of the lab handout, the "
           "distributed application and the settings of the two-machine network, the tests, "
           "and a comparison of the choices we tried. Section 3 concludes, Section 4 lists "
           "the references and the appendices contain the source code, the complete step "
           "table and the contents of the submission.")
    R.toc()

    # ------------------------------------------------------------------ 1
    R.heading("1  Problem definition", 1, new_page=True)
    R.para("The task is to implement the DES block cipher [1, 2] as a distributed "
           "application. Two processes run on two different computers. Each process must be "
           "able to **create** a message, **encrypt** it with DES, **send** it to the other "
           "process, **receive** a message from the other process, **decrypt** it and "
           "**display** it. The displayed text must be identical to the plaintext that was "
           "typed on the other computer (lab items 2.10 and 2.11).")
    R.para("The implementation must be checked transformation by transformation: the initial "
           "permutation (2.1) and its inverse (2.2), the expansion/permutation E (2.3), the "
           "round-key generation with permuted choice 1, the schedule of left circular shifts "
           "and permuted choice 2 (2.4), the XOR with the round key (2.5), the S-boxes (2.6), "
           "the permutation P (2.7), the XOR with the left half (2.8) and the swap of the "
           "halves (2.9). The checks are shown with the debugger in step mode with the tested "
           "variables watched. In addition, the lecturer asked that every DES step be "
           "implemented as **its own function** and that the report show, for every function, "
           "a table with the **input to the method, the method name, the method output and "
           "the current DES step**.")
    R.para("The starting point is the course's starter code, `tcpServer.c` and `tcpClient.c` "
           "[14]: a plain TCP chat without encryption in which both programs use the address "
           "127.0.0.1. From the task we derived these requirements:")
    R.bullets([
        "**R1 - Correct DES.** DES as specified in FIPS 46-3 [1]: 64-bit blocks, a 64-bit key "
        "with 56 effective bits, 16 rounds. The example of the handout [3] must be reproduced: "
        "key `0f1571c947d9e859`, plaintext `02468aceeca86420`, ciphertext `da02ce3a89ecac3b`.",
        "**R2 - One function per step.** Every transformation of item 2 is a separate C "
        "function that takes its input as parameters and returns its output, so that it can "
        "be watched in the debugger and listed in the input/method/output/step table.",
        "**R3 - Messages of any length.** Typed messages are longer than 8 bytes, so a padding "
        "scheme and a mode of operation are needed on top of the block cipher.",
        "**R4 - Two computers.** Two processes on two machines communicate over TCP/IP; each "
        "one can create/encrypt/send and receive/decrypt/display.",
        "**R5 - Only ciphertext on the network.** Both sides share the secret key in advance; "
        "key distribution is outside the scope of this lab.",
        "**R6 - Evidence.** Debugger screenshots of every step, screenshots of the six stages "
        "of a message, test examples, executables and the source code.",
    ])
    R.para("As agreed for this lab, the two computers are two Docker containers connected to "
           "the same virtual Ethernet network. Each container has its own host name, network "
           "interface, MAC and IP address, routing table and processes (Section 2.9). The same "
           "executables run unchanged on two physical computers (Section 2.9.3).")

    # ------------------------------------------------------------------ 2
    R.heading("2  Work done", 1, new_page=True)

    R.heading("2.1  DES in brief", 2)
    R.para("DES encrypts a 64-bit block under a 64-bit key, of which 56 bits are used: every "
           "eighth bit is a parity bit [1, 2]. {fig:structure} shows the algorithm exactly as "
           "it is implemented. The block passes the initial permutation IP and is split into "
           "two 32-bit halves L0 and R0, which go through 16 identical rounds. After the last "
           "round the halves are swapped back, and the inverse permutation IP^{-1} produces the "
           "ciphertext. In parallel, the key schedule derives sixteen 48-bit round keys "
           "K1 ... K16: permuted choice 1 selects 56 key bits and splits them into two 28-bit "
           "halves C0 and D0; before every round both halves are rotated left by one or two "
           "positions, and permuted choice 2 selects 48 of the 56 bits as the round key.")
    R.figure("des_structure.png", 13.0, "Structure of DES as implemented. Every box is one C "
             "function of `src/des.c`; the numbers in brackets are the items of the lab sheet.",
             "fig:structure")
    R.para("A round ({fig:round}) computes Li = R(i-1) and Ri = L(i-1) XOR f(R(i-1), Ki). The "
           "Feistel function f expands the right half to 48 bits (E), mixes in the round key "
           "with XOR, reduces the result back to 32 bits with the eight S-boxes and permutes "
           "it with P. Decryption is the same algorithm with the round keys used in reverse "
           "order, K16 first.")
    R.figure("des_round.png", 10.5, "One DES round as implemented in `des_round()` and "
             "`des_feistel()`.", "fig:round")

    R.heading("2.2  Environment and project structure", 2)
    R.table(["Item", "Used"], [
        ["Host computer", "EndeavourOS (Arch Linux based), Linux kernel 7.2, x86-64"],
        ["Compiler", "GCC 16.2 on the host, GCC 12 in the containers (Debian 12); flags "
                     "`-std=c11 -Wall -Wextra -Wpedantic -O0 -g3` (no optimisation, so every "
                     "variable stays visible in the debugger)"],
        ["Debugger", "GNU gdb 18.1: TUI (step) mode for the screenshots, Python API for "
                     "`debug/des_watch.py`; launch configurations for Visual Studio Code in "
                     "`.vscode/`"],
        ["Two computers", "Docker Engine 29.9 with Docker Compose 2.40; image based on "
                          "`debian:bookworm-slim` with iproute2, ping, tcpdump and gdb"],
        ["Reference implementations", "pycryptodome 4.4 (Python 3.14) and OpenSSL 4.1 "
                                      "(legacy provider), used only by the tests"],
    ], [3.6, 13.4], caption="Development environment.", label="tab:env", size=9)

    files = [
        ("src/des.h, src/des.c", "the DES cipher: tables, one function per step, key schedule, rounds, block"),
        ("src/des_trace.h, .c", "turns the steps into the input / method / output / step table"),
        ("src/des_modes.h, .c", "messages of any length: PKCS#7 padding, ECB and CBC modes"),
        ("src/des_util.h, .c", "hex parsing and printing, bit strings, random bytes"),
        ("src/des_chat.h, .c", "create / encrypt / send and receive / decrypt / display (2.10, 2.11)"),
        ("src/net.h, .c", "TCP helpers: send and receive exactly n bytes, addresses"),
        ("src/tcpServer.c", "Machine B: the starter server extended with DES"),
        ("src/tcpClient.c", "Machine A: the starter client extended with DES"),
        ("src/des_trace_main.c", "bin/des_trace: step table of one block (text, CSV, Markdown, summary)"),
        ("src/des_avalanche.c", "bin/des_avalanche: avalanche tables (handout Tables 4.3, 4.4)"),
        ("tests/test_des.c", "bin/des_test: unit tests of every step and known-answer tests"),
        ("tests/crosscheck.py", "comparison with pycryptodome and OpenSSL on random inputs"),
        ("tests/test_loopback.sh", "network test on one computer, wrong-key test, ECB vs CBC"),
        ("docker/Dockerfile, docker-compose.yml", "the two machines and the virtual LAN"),
        ("docker/demo.sh", "scripted two-machine run with packet capture and automatic checks"),
        ("debug/des_watch.py", "GDB script: reads every step's input and output with breakpoints"),
        ("tools/, report/", "screenshots, test examples and this report are generated from the project"),
    ]
    R.table(["File", "Purpose"], [[f"`{a}`", b] for a, b in files], [5.6, 11.4],
            caption="Project files (Appendix A lists the source code).", label="tab:files",
            size=8.5)
    R.para("`make` builds all programs into `bin/`, `make test` runs the unit tests, `make "
           "check` adds the cross-check and the network tests, and `make demo` starts the two "
           "machines and runs a scripted conversation (Appendix C).")

    R.heading("2.3  Design: one function per DES step", 2)
    R.para("Following the lecturer's instruction, each transformation of the lab sheet is a "
           "separate function in `src/des.c` ({tab:map}). Every step function is pure: it "
           "receives its input as parameters, returns its output and has no side effects. It "
           "keeps the result in a named local variable before returning it, so a debugger "
           "stopped on the return line shows the input (the parameter) and the output (the "
           "local variable) at the same time. The screenshots in Section 2.4 were taken this "
           "way.")
    R.para("Values are held in unsigned integers, right-aligned: a 64-bit block in a "
           "`uint64_t`, a 48-bit round key in the low 48 bits of a `uint64_t`, a 28-bit key "
           "half in a `uint32_t`. Bit 1 is the most significant bit, as in FIPS 46-3, so the "
           "permutation tables are copied from the standard unchanged. A debugger then shows "
           "every intermediate value as one hexadecimal number that can be compared directly "
           "with the textbook. The six permutations IP, IP^{-1}, E, P, PC-1 and PC-2 all use "
           "one table-driven helper, `des_permute()`; they differ only in their table and in "
           "the widths of input and output.")
    R.code(c_function("src/des.c", "des_permute") + "\n\n" +
           c_function("src/des.c", "des_initial_permutation"))
    R.table(["Lab item", "DES step", "C function", "Bits in -> out", "Called by"], [
        ["2.1", "Initial permutation", "`des_initial_permutation(block)`", "64 -> 64", "`des_process_block`"],
        ["2.2", "Inverse initial permutation", "`des_inverse_initial_permutation(block)`", "64 -> 64", "`des_process_block`"],
        ["2.3", "Expansion/permutation E", "`des_expansion_permutation(right)`", "32 -> 48", "`des_feistel`"],
        ["2.4", "Round-key generation", "`des_generate_round_keys(key, ks)`", "64 -> 16 x 48", "`main`, `chat_generate_keys`"],
        ["2.4.1", "Permuted choice 1", "`des_permuted_choice_1(key)`", "64 -> 56", "`des_generate_round_keys`"],
        ["2.4.2", "Left circular shifts", "`des_left_circular_shift(half, amount)`, `des_shift_amount(round)`", "28 -> 28", "`des_generate_round_keys`"],
        ["2.4.3", "Permuted choice 2", "`des_permuted_choice_2(cd)`", "56 -> 48", "`des_generate_round_keys`"],
        ["2.5", "XOR with round key", "`des_xor_round_key(expanded, subkey)`", "48, 48 -> 48", "`des_feistel`"],
        ["2.6", "S-boxes", "`des_sbox_substitution(input48)`, `des_sbox_lookup(box, six_bits)`", "48 -> 32 (6 -> 4 per box)", "`des_feistel`"],
        ["2.7", "Permutation P", "`des_permutation_p(input)`", "32 -> 32", "`des_feistel`"],
        ["2.8", "XOR with left half", "`des_xor_left_half(left, f_output)`", "32, 32 -> 32", "`des_round`"],
        ["2.9", "Swap of the halves", "`des_swap_halves(block)`", "64 -> 64", "`des_round`, `des_process_block`"],
        ["-", "Feistel function f", "`des_feistel(right, subkey)`", "32, 48 -> 32", "`des_round`"],
        ["-", "One round", "`des_round(state, subkey)`", "64 -> 64", "`des_process_block`"],
        ["-", "One block", "`des_process_block(block, ks, dir, states)`", "64 -> 64", "`des_encrypt_block`, `des_decrypt_block`"],
        ["2.10", "Create, encrypt, send", "`create_message`, `encrypt_message`, `send_message`", "text -> frame", "`chat_send_turn`"],
        ["2.11", "Receive, decrypt, display", "`receive_message`, `decrypt_message`, `display_message`", "frame -> text", "`chat_receive_turn`"],
    ], [1.3, 3.0, 6.0, 2.6, 4.1], caption="Lab items and the functions that implement them.",
        label="tab:map", size=8)
    R.para("**Tracing.** The functions that call the steps (`des_generate_round_keys`, "
           "`des_feistel`, `des_round`, `des_process_block`) call `des_trace(step, a, b, out)` "
           "after every step. When a trace sink is installed, `src/des_trace.c` turns each call "
           "into one row of the table the lecturer asked for: input to method, method name, "
           "method output and current DES step. `bin/des_trace` prints that table for any key "
           "and block as text, CSV or Markdown; the CSV files in `test_examples/` are the "
           "source of every step table in this report. Without a sink `des_trace()` returns "
           "immediately, so the chat programs pay nothing for it. The complete table of the "
           "textbook example (148 rows) is in Appendix B.")

    # ------------------------------------------------------------------ 2.4 steps
    R.heading("2.4  Verification of the DES steps (lab items 2.1 - 2.9)", 2)
    R.para("All values in this section belong to the example of the lab handout (Table 4.2 of "
           "[2, 3]): key K = `0f1571c947d9e859`, plaintext P = `02468aceeca86420`. Each step "
           "has a table taken from the program's trace, the code of the step and a screenshot "
           "of the debugger. The screenshots show GDB in TUI (step) mode [11] stopped on the "
           "return line of the step function, with the parameter and the result added as "
           "watch expressions (`display`). The upper half shows the source with the current "
           "line highlighted, the lower half the watched values. `display/z` prints hexadecimal "
           "with leading zeros, so a 48-bit value appears as `0x0000...` in a 64-bit variable. "
           "In the tables `^` means XOR and `|` means concatenation of the two halves.")

    # 2.1
    R.heading("2.4.1  Initial permutation IP (lab item 2.1)", 3)
    R.para("IP rearranges the 64 bits of the block: output bit 1 is input bit 58, output bit 2 "
           "is input bit 50, and so on (`IP_TABLE`, copied from FIPS 46-3). The result is split "
           "into L0 (left 32 bits) and R0. For the textbook plaintext the result "
           "`5a005a00 3cf03c0f` is exactly the IP row of Table 4.2.")
    R.code(c_block("src/des.c", r"^/\* 2\.1 Initial permutation IP", r"^};") + "\n\n" +
           c_function("src/des.c", "des_initial_permutation"))
    step_table(R, pick(tr, method="des_initial_permutation"),
               "Initial permutation of the textbook plaintext.", "tab:ip")
    R.figure("dbg_05_ip.png", 15.5, "Debugger stopped in `des_initial_permutation()`: input "
             "`block` = 02468aceeca86420, output `permuted` = 5a005a00 3cf03c0f.", "fig:dbg-ip")

    # 2.2
    R.heading("2.4.2  Inverse initial permutation IP^{-1} (lab item 2.2)", 3)
    R.para("IP^{-1} undoes IP. It is applied after the final swap to R16|L16 = "
           "`25896490 75e8fd8f` and gives the ciphertext `da02ce3a89ecac3b`, the expected "
           "result of the handout. The unit tests also check that IP^{-1}(IP(x)) = x for "
           "10 000 random blocks and for every block with a single 1-bit (Section 2.10.1).")
    R.code(c_function("src/des.c", "des_inverse_initial_permutation"))
    step_table(R, pick(tr, method="des_swap_halves", step="32-bit") +
               pick(tr, method="des_inverse_initial_permutation"),
               "The last two steps of the encryption: 32-bit swap and IP^{-1}.", "tab:ipinv")
    R.figure("dbg_14_inverse_ip.png", 15.5, "Debugger stopped in "
             "`des_inverse_initial_permutation()`: R16|L16 = 2589649075e8fd8f becomes the "
             "ciphertext da02ce3a89ecac3b.", "fig:dbg-ipinv")
    R.figure("dbg_15_result.png", 15.5, "Back in `main()`: the watched `input`, `key` and "
             "`output` show the complete encryption 02468aceeca86420 -> da02ce3a89ecac3b.",
             "fig:dbg-result")

    # 2.3
    R.heading("2.4.3  Expansion/permutation E (lab item 2.3)", 3)
    R.para("E expands the 32-bit right half to 48 bits. Every 4-bit group is extended by the "
           "neighbouring bit on each side (`E_TABLE`), so each S-box input shares two bits with "
           "its neighbours; 16 of the 32 input bits are used twice. In round 1, R0 = "
           "`3cf03c0f` becomes E(R0) = `9f97a01f805e`.")
    R.code(c_block("src/des.c", r"^/\* 2\.3 Expansion/permutation E", r"^};") + "\n\n" +
           c_function("src/des.c", "des_expansion_permutation"))
    step_table(R, pick(tr, method="des_expansion_permutation", rounds=(1, 2, 16)),
               "Expansion E in rounds 1, 2 and 16.", "tab:e")
    R.figure("dbg_06_expansion.png", 15.5, "Debugger in `des_expansion_permutation()`, round 1: "
             "`right` = 3cf03c0f, `expanded` = 9f97a01f805e.", "fig:dbg-e")

    # 2.4
    R.heading("2.4.4  Round-key generation (lab item 2.4)", 3)
    R.para("**Permuted choice 1 (2.4.1)** selects the 56 key bits that are not parity bits "
           "and splits them into C0 and D0. For K = `0f1571c947d9e859` this gives C0 = "
           "`68fc44a` and D0 = `1113e96`. Because the parity bits are discarded, changing bit 8 "
           "of the key does not change the ciphertext at all (Section 2.10.4).")
    R.para("**Left circular shifts (2.4.2).** Before each round C and D are rotated left by "
           "`des_shift_amount(i)` positions: 1 in rounds 1, 2, 9 and 16, otherwise 2. That is "
           "28 positions in total, so C16 = C0 and D16 = D0, which can be seen in "
           "{tab:keys}.")
    R.para("**Permuted choice 2 (2.4.3)** selects 48 of the 56 bits of Ci|Di as the round key "
           "Ki. K1 = `7833c320da70`; written as eight 6-bit groups, the notation of the handout, "
           "this is `1e 03 0f 03 08 0d 29 30`, the K1 of Table 4.2.")
    R.code(c_function("src/des.c", "des_shift_amount") + "\n\n" +
           c_function("src/des.c", "des_left_circular_shift") + "\n\n" +
           c_function("src/des.c", "des_generate_round_keys"))
    step_table(R, pick(tr, lab="2.4", rounds=(0, 1, 2, 3, 16)),
               "Key schedule: PC-1, then shifts and PC-2 for rounds 1, 2, 3 and 16.", "tab:keys")
    R.figure("dbg_01_pc1.png", 15.5, "Debugger in `des_permuted_choice_1()`: the 64-bit `key` "
             "becomes `cd` = C0|D0 = 68fc44a 1113e96 (56 bits).", "fig:dbg-pc1")
    R.figure("dbg_02_shift.png", 15.5, "Debugger in `des_left_circular_shift()`, round 1: C0 = "
             "68fc44a rotated by `amount` = 1 gives C1 = d1f8894.", "fig:dbg-shift")
    R.figure("dbg_03_pc2.png", 15.5, "Debugger in `des_permuted_choice_2()`, round 1: C1|D1 "
             "becomes K1 = 7833c320da70.", "fig:dbg-pc2")
    R.figure("dbg_04_all_round_keys.png", 15.5, "After `des_generate_round_keys()` the watched "
             "array `ks.subkey` holds all 16 round keys K1 ... K16.", "fig:dbg-keys")

    ours = parse_summary("summary_textbook_table_4_2.txt")
    key_rows, fills = [], {}
    handout_keys = {r[0]: r[1] for r in HANDOUT_42}
    for n, (rnd, kname, k, l, r) in enumerate([x for x in ours if x[1]]):
        printed = handout_keys[rnd]
        same = printed == k
        key_rows.append([rnd, k, printed, "identical" if same else
                         "typing error in the handout (letter l instead of digit 1)"])
        if not same:
            fills[(n, 2)] = NOTE_FILL
    R.table(["Round", "Ki computed (6-bit groups)", "Ki printed in the handout", "Comparison"],
            key_rows, [1.4, 4.6, 4.6, 6.4], caption="All 16 round keys compared with Table 4.2 "
            "of the handout.", label="tab:keycmp", mono=(1, 2), size=8, center=(0,),
            fills=fills, keep_together=True)

    # 2.5
    R.heading("2.4.5  XOR with the round key (lab item 2.5)", 3)
    R.para("E(R(i-1)) is combined with the 48-bit round key by XOR: in round 1 "
           "`9f97a01f805e` XOR `7833c320da70` = `e7a4633f5a2e`. During decryption, round i "
           "uses K(17-i) (Section 2.5).")
    R.code(c_function("src/des.c", "des_xor_round_key"))
    step_table(R, pick(tr, method="des_xor_round_key", rounds=(1, 2, 16)),
               "XOR with the round key in rounds 1, 2 and 16.", "tab:xork")
    R.figure("dbg_07_xor_round_key.png", 15.5, "Debugger in `des_xor_round_key()`, round 1: "
             "`expanded` XOR `subkey` = `mixed`.", "fig:dbg-xork")

    # 2.6
    R.heading("2.4.6  S-boxes (lab item 2.6)", 3)
    R.para("The 48-bit result is cut into eight 6-bit groups B1 ... B8, and group j goes into "
           "S-box Sj. The outer bits b1 b6 select the row (0-3) and the inner bits b2 b3 b4 b5 "
           "the column (0-15); the entry of the S-box is the 4-bit output. The eight 4-bit "
           "outputs form 32 bits again: this is the 48 -> 32-bit reduction of the round, done "
           "by substitution, not by truncation. {tab:sbox} lists the eight look-ups of "
           "round 1. For example, B1 = 111001 selects row 3 (binary 11) and column 12 (1100) of "
           "S1, which contains 10 = 1010. {fig:dbg-sloop} shows the loop in step mode: the "
           "debugger stops once per S-box, and the watched variables show the box number, its "
           "6-bit input, its 4-bit output and the 32-bit output growing by 4 bits per box.")
    R.code(c_block("src/des.c", r"^/\* 2\.6 The eight S-boxes", r"/\* S2 \*/").rsplit("\n", 1)[0]
           + "\n    ...\n\n" + c_function("src/des.c", "des_sbox_lookup") + "\n\n" +
           c_function("src/des.c", "des_sbox_substitution"))
    sbox_rows = pick(tr_s, method="des_sbox_lookup", rounds=(1,)) + \
        pick(tr_s, method="des_sbox_substitution", rounds=(1,))
    step_table(R, sbox_rows, "The eight S-box look-ups of round 1 and the 32-bit result "
               "(from `des_trace -s`).", "tab:sbox")
    R.figure("dbg_08_sbox_loop.png", 15.5, "S-box loop in step mode: stops for S1, S2 and S3 "
             "with `box`, `six_bits` (binary; GDB drops leading zeros), `four_bits` and "
             "`output`.", "fig:dbg-sloop")
    R.figure("dbg_09_sbox_result.png", 15.5, "End of `des_sbox_substitution()`: 48-bit input "
             "e7a4633f5a2e -> 32-bit output a32f11c2.", "fig:dbg-sbox")

    # 2.7
    R.heading("2.4.7  Permutation P (lab item 2.7)", 3)
    R.para("P permutes the 32 output bits of the S-boxes; the result is the value of the "
           "Feistel function f(R(i-1), Ki). In round 1, f = `e0d27245`. The handout does not "
           "print f, but f follows from Table 4.2: f(R0, K1) = L0 XOR R1 = `5a005a00` XOR "
           "`bad22845` = `e0d27245` (checked by the unit tests).")
    R.code(c_function("src/des.c", "des_permutation_p") + "\n\n" +
           c_function("src/des.c", "des_feistel"))
    step_table(R, pick(tr, method="des_permutation_p", rounds=(1, 2, 16)),
               "Permutation P in rounds 1, 2 and 16.", "tab:p")
    R.figure("dbg_10_permutation_p.png", 15.5, "Debugger in `des_permutation_p()`, round 1: "
             "a32f11c2 -> e0d27245 = f(R0, K1).", "fig:dbg-p")

    # 2.8
    R.heading("2.4.8  XOR with the left half (lab item 2.8)", 3)
    R.para("The new right half is L(i-1) XOR f: `5a005a00` XOR `e0d27245` = `bad22845`, which "
           "is R1 in Table 4.2.")
    R.code(c_function("src/des.c", "des_xor_left_half"))
    step_table(R, pick(tr, method="des_xor_left_half", rounds=(1, 2, 16)),
               "XOR with the left half in rounds 1, 2 and 16.", "tab:xorl")
    R.figure("dbg_11_xor_left_half.png", 15.5, "Debugger in `des_xor_left_half()`, round 1: "
             "`left` XOR `f_output` = `new_right` = bad22845.", "fig:dbg-xorl")

    # 2.9
    R.heading("2.4.9  Swap of the halves (lab item 2.9)", 3)
    R.para("`des_round()` joins (L XOR f) and R and swaps the two halves, which gives "
           "Li|Ri = R(i-1) | (L(i-1) XOR f). Round 1 ends with `3cf03c0f bad22845`, the L1 and "
           "R1 of Table 4.2. After round 16 the halves are swapped once more (the 32-bit swap "
           "in {fig:structure}), which cancels the exchange of the last round, so IP^{-1} "
           "receives R16|L16. {fig:dbg-step} shows `des_round()` in step mode: after one "
           "`next` the watched `after_swap` changes from leftover stack content "
           "(0x0000000100000001) to 0x3cf03c0fbad22845.")
    R.code(c_function("src/des.c", "des_swap_halves") + "\n\n" +
           c_function("src/des.c", "des_round") + "\n\n" +
           c_function("src/des.c", "des_process_block"))
    step_table(R, pick(tr, method="des_swap_halves", rounds=(1, 2, 16), step="Swap of"),
               "Swap of the halves at the end of rounds 1, 2 and 16.", "tab:swap")
    R.figure("dbg_12_swap.png", 15.5, "Debugger in `des_swap_halves()`, round 1: `block` = "
             "bad228453cf03c0f becomes `swapped` = 3cf03c0fbad22845 = L1|R1.", "fig:dbg-swap")
    R.figure("dbg_13_round_step_mode.png", 15.5, "Step mode in `des_round()`: six watched "
             "variables of round 1 before and after `next`.", "fig:dbg-step")

    # ------------------------------------------------------------------ 2.5
    R.heading("2.5  The complete example and decryption", 2, new_page=True)
    rows, fills = [], {}
    printed = {r[0]: r for r in HANDOUT_42}
    for n, (rnd, kname, k, l, r) in enumerate(ours):
        h = printed[rnd]
        diffs = []
        if k != h[1]:
            diffs.append("Ki")
        if l != h[2]:
            diffs.append("Li")
        if r != h[3]:
            diffs.append("Ri")
        remark = "identical" if not diffs else "handout: " + ", ".join(
            f"{name} printed as {h[i]}" for name, i in (("Ki", 1), ("Li", 2), ("Ri", 3))
            if name in diffs)
        rows.append([rnd, k or "", l, r, remark])
        if diffs:
            fills[(n, 4)] = NOTE_FILL
    R.para("{tab:t42} compares the output of the program for all 16 rounds with Table 4.2 "
           "of the handout. All 16 round keys, all 34 halves and the ciphertext agree. The "
           "three highlighted differences are typing errors in the handout, not differences "
           "in the computation:")
    R.bullets([
        "K6 and K7 contain the letter **l** instead of the digit **1** (`...2alc` and "
        "`...0blc...`); `l` is not a hexadecimal digit.",
        "In the IP^{-1} row the handout prints `25896490` as the left half. That value is "
        "R16, the left half of the input of IP^{-1}; the left half of the ciphertext is "
        "`da02ce3a`, as the handout itself states (ciphertext `da02ce3a89ecac3b`).",
    ])
    R.table(["Round", "Ki (6-bit groups)", "Li", "Ri", "Comparison with the handout"], rows,
            [1.3, 4.0, 2.4, 2.4, 6.9], caption="Our computation of the textbook example "
            "(`des_trace -f summary`) compared with Table 4.2 of the handout.",
            label="tab:t42", mono=(1, 2, 3), size=8, center=(0,), fills=fills,
            keep_together=True)
    dec = parse_summary("summary_textbook_decrypt.txt")
    R.para("**Decryption.** `des_process_block()` with `DES_DECRYPT` runs the same rounds but "
           "uses K16 in round 1 and K1 in round 16 ({tab:dec}). IP applied to the ciphertext "
           "gives `25896490 75e8fd8f` = R16|L16 of the encryption, so the decryption meets the "
           "intermediate values of the encryption in reverse order (its round 1 output "
           "`75e8fd8f 56b0bd75` is R15, L15 of the encryption) and ends with the plaintext "
           "`02468aceeca86420`.")
    R.table(["Round", "Key used", "Ki (6-bit groups)", "Li", "Ri"],
            [[a, b, c, d, e] for a, b, c, d, e in dec], [1.5, 2.0, 5.2, 4.1, 4.2],
            caption="Decryption of `da02ce3a89ecac3b` with the same key "
            "(`des_trace -d -f summary`).", label="tab:dec", mono=(2, 3, 4), size=8,
            center=(0, 1), keep_together=True)

    # ------------------------------------------------------------------ 2.6
    R.heading("2.6  Values observed by the debugger", 2)
    R.para("The tables above are produced by the program itself. As an independent check, "
           "`debug/des_watch.py` uses GDB's Python API: a breakpoint on every step function "
           "reads its arguments when the function is entered, and a finish breakpoint reads "
           "the value it returns. The program is not modified, so these are the values the "
           "debugger sees in the running process. {tab:gdb} shows the first call of every "
           "step (round 1) and the final IP^{-1}; every value agrees with the trace tables and "
           "with the handout. Command: `gdb -q -batch -x debug/des_watch.py --args bin/des_trace -q`.")
    gdb_rows = []
    for line in example("gdb_watch_steps.txt").splitlines():
        m = re.match(r"^(\d[\d.]*)\s+(.+?)\s{2,}(des_\w+)\s+(.+?)\s{2,}([0-9a-f]+)$", line)
        if m:
            gdb_rows.append([m.group(1), m.group(4), m.group(3), m.group(5),
                             breakable(m.group(2))])
    R.table(["Item", "Input to method (arguments)", "Method name", "Method output (returned)",
             "Current DES step"], gdb_rows, [1.0, 5.0, 5.0, 3.1, 2.9],
            caption="Input and output of every step function as read by GDB breakpoints.",
            label="tab:gdb", mono=(1, 2, 3), size=7.5, center=(0,))

    # ------------------------------------------------------------------ 2.7
    R.heading("2.7  Messages of any length: padding and modes", 2)
    R.para("DES encrypts exactly 8 bytes, while a chat message has any length. "
           "`src/des_modes.c` therefore adds PKCS#7 padding [8]: n bytes of value n with "
           "1 <= n <= 8. There is always at least one padding byte, so the receiver can remove "
           "the padding without ambiguity. On top of that it implements two modes of "
           "operation [5, 6]:")
    R.bullets([
        "**ECB:** every block is encrypted independently.",
        "**CBC (default):** each plaintext block is XORed with the previous ciphertext block "
        "before encryption; the first block is XORed with a random 64-bit initialisation "
        "vector (IV), which is new for every message and is sent with it.",
    ])
    R.para("{tab:ecb} shows why CBC is the default. The 32-character message "
           "`AAAA...A` consists of four identical blocks. ECB turns them into four identical "
           "ciphertext blocks, which an eavesdropper can see. In CBC all four differ, and the "
           "same message sent twice gives a different ciphertext each time. Both modes "
           "reproduce the examples of FIPS 81 [5] (Section 2.10.1).")
    R.code(c_function("src/des_modes.c", "des_encrypt_message") + "\n\n" +
           c_function("src/des_modes.c", "des_decrypt_message"))
    blocks = {}
    for mode in ("ecb", "cbc"):
        log = example(f"loopback/{mode}-client.log")
        start = log.index('"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"')
        seg = log[start:]
        cipher = re.search(r"ciphertext\s+\d+ B  ([0-9a-f ]+)\n\s+([0-9a-f ]+)", seg)
        blocks[mode] = (cipher.group(1) + " " + cipher.group(2)).split()
    labels = ["block 1 (AAAAAAAA)", "block 2 (AAAAAAAA)", "block 3 (AAAAAAAA)",
              "block 4 (AAAAAAAA)", "block 5 (padding 08 x 8)"]
    R.table(["Plaintext block", "ECB ciphertext", "CBC ciphertext"],
            [[labels[i], blocks["ecb"][i], blocks["cbc"][i]] for i in range(5)],
            [5.0, 6.0, 6.0], caption="The message `AAAA...A` (32 bytes) in ECB and in CBC mode "
            "(from `tests/test_loopback.sh`).", label="tab:ecb", mono=(1, 2), size=8.5,
            fills={(i, 1): NOTE_FILL for i in range(4)})

    # ------------------------------------------------------------------ 2.8
    R.heading("2.8  The distributed application (items 2.10, 2.11)", 2, new_page=True)
    R.para("The application consists of two programs that share all DES and messaging code: "
           "`tcpServer` (Machine B) and `tcpClient` (Machine A). They are the starter programs "
           "extended with DES. After the TCP connection is set up, the conversation is "
           "turn-based, as in the starter: the client sends first, then each side alternately "
           "creates, encrypts and sends a message and receives, decrypts and displays the "
           "answer. Typing `:exit` (or reaching the end of the input) sends an encrypted "
           "`:exit` message, and both programs close the connection.")
    R.heading("2.8.1  From the starter code to the DES application", 3)
    R.para("Besides adding DES, several problems of the starter code had to be fixed. Some of "
           "them make a connection between two computers impossible; others break as soon as "
           "binary ciphertext is sent ({tab:starter}).")
    R.table(["Starter code", "Effect", "Our program"], [
        ["`bind()` and `connect()` use the fixed address 127.0.0.1",
         "only processes on the same computer can connect",
         "server binds 0.0.0.0 (all interfaces); client takes the server address (IP or host name) as `-s`"],
        ["messages sent with `strlen()` and printed with `%s`",
         "ciphertext containing a 0x00 byte is cut off; recv() does not add a terminating zero",
         "binary-safe frames with an explicit length (Section 2.8.2)"],
        ["one `recv()` per message",
         "TCP is a byte stream: a message can arrive in pieces, or two messages together",
         "`net_recv_all()` reads exactly the announced number of bytes"],
        ["`scanf(\"%s\")` into a 1024-byte buffer",
         "only the first word of a line is sent; long input overflows the buffer",
         "`fgets()` with the buffer size: whole lines, at most 4095 bytes"],
        ["`addr_size` not initialised before `accept()`", "undefined behaviour",
         "`addr_size = sizeof(newAddr)` before every `accept()`"],
        ["server ignores the return value of `recv()`",
         "after the client disconnects the server loops forever with an empty buffer",
         "0 (closed) and -1 (error) end the session"],
        ["client tests `:exit` on the received buffer after clearing the typed one",
         "the client never leaves on `:exit`", "`:exit` is checked on the message typed"],
        ["`fork()` for every client; the child continues into the accept loop",
         "several conversations would share one keyboard; zombie processes",
         "one client at a time; `-1` exits after the first client"],
        ["plain text on the network", "anyone on the LAN can read the messages",
         "DES-CBC with a new random IV for every message"],
    ], [5.2, 5.6, 6.2], caption="Problems of the starter code and how our programs solve them.",
        label="tab:starter", size=8)

    R.heading("2.8.2  Message format on the wire", 3)
    src, dst, payload = first_payload_from_capture()
    length = int.from_bytes(payload[:4], "big")
    R.para("TCP delivers a stream of bytes, not messages, so every message is sent as a frame: "
           "a 4-byte length in network byte order, a mode byte and the 8-byte IV, followed by "
           "the ciphertext ({tab:frame}). The receiver first reads the 13-byte header and then "
           "exactly the announced number of bytes. The frame contains neither the key nor any "
           "plaintext. The example values are the first message of the scripted two-machine "
           f"run, captured on the network ({src} -> {dst}).")
    R.table(["Offset", "Size", "Field", "Example (captured)"], [
        ["0", "4 B", "length of the rest of the frame (1 + 8 + ciphertext)",
         f"{payload[:4].hex()}  (= {length})"],
        ["4", "1 B", "mode: 1 = ECB, 2 = CBC", f"{payload[4]:02x}"],
        ["5", "8 B", "initialisation vector (zero in ECB mode)", payload[5:13].hex()],
        ["13", f"{length - 9} B", "DES ciphertext, a multiple of 8 bytes",
         payload[13:21].hex() + " ..."],
    ], [1.5, 1.4, 7.3, 6.8], caption="Frame of one message.", label="tab:frame",
        mono=(3,), size=8.5, center=(0, 1))

    R.heading("2.8.3  Create, encrypt and send (lab item 2.10)", 3)
    R.para("`chat_send_turn()` calls the three stages one after the other. Each stage prints a "
           "tagged line, so that every stage can be seen in the screenshots:")
    R.bullets([
        "**[CREATE]** `create_message()` reads one line from the keyboard (or from a script "
        "file) and shows the message and its length.",
        "**[ENCRYPT]** `encrypt_message()` draws a random IV from /dev/urandom, shows the "
        "plaintext bytes, the padded plaintext and the ciphertext. With option `-t` it also "
        "prints the full step table of the first block.",
        "**[SEND]** `send_message()` builds the frame and sends it with `net_send_all()`, "
        "which repeats `send()` until every byte is written.",
    ])
    R.code(c_function("src/des_chat.c", "chat_send_turn") + "\n\n" +
           c_function("src/des_chat.c", "encrypt_message") + "\n\n" +
           c_function("src/des_chat.c", "send_message"))
    R.figure("net_03_server_listening.png", 12.5, "Machine B (`machine-b`, 172.28.10.20) starts "
             "`tcpServer`: round keys, socket, bind to 0.0.0.0:9000, listening, and the "
             "connection from Machine A.", "fig:net-listen")
    R.figure("net_04_machine-a_create_encrypt_send.png", 14.5, "Machine A: the message is "
             "**created** (typed), **encrypted** (IV, plaintext, PKCS#7 padding, ciphertext) "
             "and **sent** to 172.28.10.20:9000.", "fig:net-a-send")

    R.heading("2.8.4  Receive, decrypt and display (lab item 2.11)", 3)
    R.bullets([
        "**[RECEIVE]** `receive_message()` reads the 13-byte header, checks the length and "
        "reads the ciphertext with `net_recv_all()`.",
        "**[DECRYPT]** `decrypt_message()` decrypts with the IV from the frame and checks and "
        "removes the padding. A wrong key is detected here: the padding check fails and "
        "nothing is displayed.",
        "**[DISPLAY]** `display_message()` prints the recovered text.",
    ])
    R.code(c_function("src/des_chat.c", "chat_receive_turn") + "\n\n" +
           c_function("src/des_chat.c", "decrypt_message"))
    R.para("The ciphertext received by Machine B ({fig:net-b-recv}) is byte for byte the "
           "ciphertext sent by Machine A ({fig:net-a-send}). After decryption and removal of the "
           "5 padding bytes, Machine B displays exactly the 35 bytes typed on Machine A. The "
           "answer contains the Turkish letters ş and ü: DES works on bytes, so any UTF-8 text "
           "is transferred unchanged.")
    R.figure("net_05_machine-b_receive_decrypt_display.png", 14.5, "Machine B **receives** "
             "the frame, **decrypts** it and **displays** the message typed on Machine A.",
             "fig:net-b-recv")
    R.figure("net_06_machine-b_create_encrypt_send.png", 14.5, "Machine B answers: create, "
             "encrypt and send.", "fig:net-b-send")
    R.figure("net_07_machine-a_receive_decrypt_display.png", 14.5, "Machine A receives, "
             "decrypts and displays the answer of Machine B.", "fig:net-a-recv")
    R.figure("net_09_machine-a_exit.png", 14.5, "Machine A types `:exit`; the encrypted exit "
             "message ends the conversation on both machines.", "fig:net-exit")

    R.heading("2.8.5  What travels over the network", 3)
    R.para("{fig:capture} was recorded on the bridge that connects the two machines while "
           "the two messages above were exchanged: the optional `sniffer` container runs "
           "tcpdump on the bridge `des-lan0`, like a mirror port on a switch. After the 20-byte "
           "IP header and the 32-byte TCP header (offset 0x34) the payload starts with the "
           "frame header (length `00000031`, mode `02`, then the IV printed by Machine A) "
           "followed by the ciphertext. The ASCII column contains no readable text. The "
           "scripted run (`docker/demo.sh`) checks this automatically for every message: none of "
           "the ten plaintext messages occurs in the capture, and every ciphertext printed in "
           "the logs is found in it byte for byte (Section 2.10.3).")
    R.figure("net_08_packet_capture.png", 17.0, "The two frames captured on the virtual LAN "
             "(tcpdump -X on `des-lan0`): only the header, the IV and the ciphertext are "
             "visible.", "fig:capture")

    # ------------------------------------------------------------------ 2.9
    R.heading("2.9  Settings of the distributed system", 2, new_page=True)
    R.heading("2.9.1  Two computers as two Docker containers", 3)
    R.para("A Docker container is a group of isolated processes with its own network "
           "namespace: its own network interface `eth0` with its own MAC and IP address, its "
           "own routing table, host name, process list and file system [10]. Two containers "
           "attached to the same user-defined bridge network behave like two computers "
           "plugged into one Ethernet switch: frames between them pass through the Linux "
           "bridge `des-lan0` on the host, where they can be captured. Unlike virtual "
           "machines the containers share the host's kernel, which does not matter for TCP/IP "
           "communication between processes. {fig:network} and {tab:net} show the setup. Both "
           "containers run the same image; the key is given to both machines as the "
           "environment variable `DES_KEY`.")
    R.figure("network.png", 16.5, "The two machines on the virtual LAN.", "fig:network")
    mac = {}
    for m in ("machine-a", "machine-b"):
        text = example(f"docker_run/{m}_network.txt")
        found = re.search(r"([0-9a-f]{2}(?::[0-9a-f]{2}){5})", text)
        mac[m] = found.group(1) if found else "assigned by Docker"
    R.table(["Setting", "machine-a", "machine-b"], [
        ["Role", "Machine A: `tcpClient`, sends first", "Machine B: `tcpServer`, receives first"],
        ["Host name / container name", "machine-a", "machine-b"],
        ["IP address (static)", "172.28.10.10/24", "172.28.10.20/24"],
        ["MAC address (example run)", mac["machine-a"], mac["machine-b"]],
        ["Network", "des_lan: bridge `des-lan0`, 172.28.10.0/24, gateway 172.28.10.1",
         "same network"],
        ["TCP port", "ephemeral port chosen by the OS", "9000, listening on 0.0.0.0"],
        ["DES key", "DES_KEY=0f1571c947d9e859 (pre-shared)", "the same key"],
        ["Programs", "/opt/des-lab/bin (built in the image, Debian 12)", "the same image"],
    ], [4.2, 6.4, 6.4], caption="Settings of the two machines.", label="tab:net", size=8.5,
        bold_col0=True)
    R.code(c_block("docker-compose.yml", r"^services:", r"^\s+init: true") + "\n  ...\n" +
           c_block("docker-compose.yml", r"^networks:", r"gateway"))
    R.figure("net_01_settings_machine-a.png", 13.0, "machine-a: host name, address "
             "172.28.10.10/24, route, and ping to machine-b.", "fig:net-a")
    R.figure("net_02_settings_machine-b.png", 13.0, "machine-b: host name, address "
             "172.28.10.20/24, route, and ping to machine-a.", "fig:net-b")

    R.heading("2.9.2  Running the application", 3)
    R.code("docker compose up -d --build                    # start machine-a and machine-b\n"
           "docker exec -it machine-b tcpServer             # terminal 1: Machine B (server)\n"
           "docker exec -it machine-a tcpClient -s 172.28.10.20   # terminal 2: Machine A\n"
           "docker compose --profile capture up sniffer     # terminal 3 (optional): packets\n"
           "docker compose down                             # stop everything\n\n"
           "make demo      # scripted conversation between the containers with automatic checks",
           size=8)
    R.table(["Option", "Program", "Meaning (default)"], [
        ["`-s server`", "tcpClient", "IP address or host name of Machine B (127.0.0.1)"],
        ["`-p port`", "both", "TCP port (9000, as in the starter code)"],
        ["`-b address`", "tcpServer", "local address to listen on (0.0.0.0 = all interfaces)"],
        ["`-k key`", "both", "DES key, 16 hex digits (`$DES_KEY`, else 0f1571c947d9e859)"],
        ["`-m cbc|ecb`", "both", "mode of operation (cbc)"],
        ["`-t`", "both", "print the DES step table for the first block of every message"],
        ["`-1`", "tcpServer", "exit after the first client has disconnected"],
        ["`-r n`", "tcpClient", "connection attempts while the server starts (10)"],
        ["`-n`", "both", "no colours"],
    ], [2.6, 2.4, 12.0], caption="Command-line options.", label="tab:opts", size=8.5)

    R.heading("2.9.3  Two physical computers or virtual machines", 3)
    R.para("The programs do not depend on Docker. On two computers in one network:")
    R.steps([
        "Connect both computers to the same LAN or Wi-Fi network and find the IPv4 address "
        "of Machine B (`ip -4 addr` on Linux, `ipconfig` on Windows). `tcpServer` also prints "
        "every address it can be reached at when it starts.",
        "Allow incoming TCP connections to port 9000 on Machine B, for example "
        "`sudo ufw allow 9000/tcp` or `sudo firewall-cmd --add-port=9000/tcp`.",
        "Machine B: `./bin/tcpServer -k <key>`; Machine A: "
        "`./bin/tcpClient -s <IP of Machine B> -k <same key>`.",
        "With virtual machines (VirtualBox, VMware, QEMU) use a bridged or host-only network "
        "adapter so that both machines are in one subnet; with NAT a port forwarding rule is "
        "needed.",
    ])
    R.para("Many campus and public Wi-Fi networks isolate wireless clients from each other "
           "(client isolation). The connection then times out although both computers reach "
           "the Internet; a cable, a private router or a phone hotspot avoids this.")

    # ------------------------------------------------------------------ 2.10
    R.heading("2.10  Testing", 2, new_page=True)
    R.heading("2.10.1  Unit tests of every step", 3)
    R.para("`tests/test_des.c` (`make test`) tests every step function on its own and the "
           "whole cipher. Expected values come only from sources independent of our code: "
           "[T] the handout's Tables 4.2 and 4.3 [3], [G] Grabbe's step-by-step example [4], "
           "which lists the result of every step of round 1, [S] the S-box example of [2], "
           "[F] the ECB and CBC examples of FIPS 81 [5] and [N] the variable-plaintext "
           "known-answer vectors of NIST SP 800-17 [7]. Properties that need no reference data "
           "are tested on thousands of reproducible pseudo-random inputs: IP^{-1}(IP(x)) = x, "
           "every row of every S-box is a permutation of 0 ... 15, the 16 shifts add up to "
           "28, D(E(x)) = x, encryption with the four weak keys is its own inverse, and the "
           "complementation property E(~K, ~P) = ~E(K, P). All 25 080 checks pass, both on the "
           "host and inside the Docker build.")
    R.code(example("unit_tests.txt"), size=7.5)
    R.heading("2.10.2  Cross-check with independent implementations", 3)
    R.para("`tests/crosscheck.py` encrypts and decrypts 300 random key/block pairs with our "
           "program and with pycryptodome, and 50 of them also with the OpenSSL command line "
           "[13]. An error in any table entry would make some of these results differ.")
    R.code(example("crosscheck.txt"), size=7.5)
    R.heading("2.10.3  Network tests", 3)
    R.para("`tests/test_loopback.sh` runs both programs on one computer with the scripted "
           "messages of `test_examples/messages_machine_a.txt` and `..._b.txt`. It checks that "
           "every message is displayed unchanged by the other program, that a client with a "
           "wrong key is rejected (the padding check fails and nothing is displayed), and the "
           "ECB/CBC behaviour of {tab:ecb}. `docker/demo.sh` runs the same conversation between "
           "the two containers while tcpdump records the bridge, then checks the logs and the "
           "capture; its logs and the capture file are in `test_examples/docker_run/`.")
    R.code(example("loopback_test.txt"), size=7.5)
    demo = example("docker_run/demo_output.txt")
    checks = demo[demo.index("==> Checks"):].strip() if "==> Checks" in demo else demo
    R.code(checks, size=7.5)

    R.heading("2.10.4  Avalanche effect (handout Tables 4.3, 4.4)", 3)
    plain = csv_rows("avalanche_plaintext_bit4.csv")
    keyc = csv_rows("avalanche_key_bit4.csv")
    R.para("`bin/des_avalanche` runs two encryptions that differ in one bit and counts the "
           "differing bits of Li|Ri after every round. With plaintext bit 4 flipped "
           "(`02468ace...` -> `12468ace...`) the result reproduces Table 4.3 of the handout "
           "exactly, in all 18 rows: 1, 1, 5, 18, 34 bits after round 4, and 32 bits in the "
           "ciphertext. The handout's Table 4.4 (change in the key) has a title but no data, "
           f"so {{tab:aval}} gives our result: with key bit 4 flipped (`0f15...` -> `1f15...`) "
           f"the ciphertexts differ in {keyc[-1]['differing_bits']} bits. In both cases about "
           "half of the 64 bits differ after only four rounds ({fig:aval}). Flipping key bit "
           "8, a parity bit, changes nothing (0 bits), because PC-1 discards it.")
    R.note("The text of the handout says that a 1-bit change in the plaintext gives 34 "
           "differing bits and a 1-bit change in the key 35. This contradicts the handout's "
           "own Table 4.3 (32 bits), which our program reproduces, and our key result (30 "
           "bits, confirmed with pycryptodome). The numbers in the text probably belong to "
           "another example.")
    av_rows = []
    for p_row, k_row in zip(plain, keyc):
        rnd = p_row["round"]
        av_rows.append([rnd, p_row["first"], p_row["second"], p_row["differing_bits"],
                        k_row["second"], k_row["differing_bits"]])
    R.table(["Round", "Original Li|Ri", "Plaintext bit 4 flipped", "Bits", "Key bit 4 flipped",
             "Bits"], av_rows, [1.4, 4.0, 4.0, 1.4, 4.0, 1.4],
            caption="Avalanche effect: Li|Ri after every round (round 0 = the plaintext, "
            "IP-1 = the ciphertext).", label="tab:aval", mono=(1, 2, 4), size=8,
            center=(0, 3, 5), keep_together=True)
    R.figure("avalanche.png", 15.0, "Number of differing bits after each round for a 1-bit "
             "change of the plaintext and of the key.", "fig:aval")

    # ------------------------------------------------------------------ 2.11
    R.heading("2.11  Comparison of the choices we tried", 2, new_page=True)
    R.para("**Network setup.** We used two setups and considered two more ({tab:setups}). "
           "During development both programs ran on one computer over the loopback address; "
           "this is fast and is used by the automatic test, but it is not two computers, and "
           "the traffic never leaves the kernel. For the demonstration we chose two Docker "
           "containers on a user-defined bridge: each has its own network stack, the setup is "
           "one command and gives the same result on every computer with Docker, the "
           "addresses are fixed, and the traffic can be recorded on the bridge. Virtual "
           "machines or two real computers would add separate kernels and real network "
           "hardware but need much more setup; our programs would run on them unchanged "
           "(Section 2.9.3).")
    R.table(["", "Loopback (one computer)", "Docker bridge (used)", "Virtual machines",
             "Two physical computers"], [
        ["Separate network stack, IP, MAC", "no", "yes", "yes", "yes"],
        ["Separate operating system kernel", "no", "no", "yes", "yes"],
        ["Setup effort", "none", "one command", "high (install OS twice)", "two machines, firewall"],
        ["Same result on every computer", "yes", "yes", "partly", "no"],
        ["Traffic can be recorded", "only as root", "yes, on des-lan0", "yes", "with a mirror port or on a host"],
        ["Used for", "development, `make loopback`", "demonstration, `make demo`", "not used", "not used (instructions in 2.9.3)"],
    ], [3.8, 3.1, 3.3, 3.2, 3.6], caption="Network setups compared.", label="tab:setups",
        size=8, bold_col0=True)
    R.para("**Mode of operation.** We implemented and ran both ECB and CBC. ECB is simpler but "
           "leaks repeated blocks ({tab:ecb}); CBC hides them at the cost of an 8-byte IV per "
           "message, so CBC is the default and ECB remains selectable with `-m ecb` for the "
           "comparison. Neither mode protects integrity: an attacker who flips a bit of a CBC "
           "ciphertext block flips the same bit of the next plaintext block, so a real system "
           "would add a message authentication code.")
    R.para("**Representation of the data.** We considered storing bits in arrays of 64 bytes "
           "(one byte per bit), which is common in teaching code, and chose integers instead. "
           "In the debugger an integer is one hexadecimal number that can be compared with "
           "the textbook at a glance, whereas a bit array is 64 separate elements. One "
           "table-driven `des_permute()` for all six permutations also means that a wrong "
           "permutation can only be a wrong table entry, and the cross-check would detect it.")
    R.para("**Testing.** Each method shows something the others do not. The debugger in step "
           "mode (Section 2.4) shows the values inside the running program and is what the lab "
           "asks for, but it is manual and covers one example. The trace table produces every "
           "intermediate value of a block at once and makes the comparison with the textbook "
           "a table comparison. The unit tests check every step against independent data in "
           "less than a second after every change. The cross-check with pycryptodome and "
           "OpenSSL finds errors that no worked example covers. The packet capture is the only "
           "test that proves what really leaves the machine.")
    R.para("**Our opinion.** Splitting DES into one function per step, as the lecturer asked, "
           "paid off: when every step has a name, an input and an output, verifying the "
           "cipher is a comparison of table rows with the textbook, and the same structure "
           "makes the debugger session short. The most error-prone part of the lab was not the "
           "cipher but the networking around it: the starter code works for short words "
           "typed on one computer, but needs explicit framing, binding to all interfaces and "
           "careful handling of partial reads before encrypted binary data can travel "
           "between two machines. Docker turned the two-computer requirement into a "
           "reproducible setup that every team member can start with one command.")

    # ------------------------------------------------------------------ 3, 4
    R.heading("3  Conclusion", 1, new_page=True)
    R.para("We implemented DES in C with one function per transformation and verified every "
           "transformation in four independent ways: with the debugger in step mode, against "
           "the example of the lab handout, against Grabbe's step-by-step example and against "
           "two independent DES implementations. On top of the cipher we built an encrypted "
           "chat between two machines, deployed as two Docker containers on a virtual LAN.")
    R.bullets([
        "All 16 round keys, all intermediate halves and the ciphertext `da02ce3a89ecac3b` of "
        "the handout are reproduced. Three values of the handout are typing errors "
        "(Section 2.5).",
        "The debugger, the program's own trace table and 25 080 unit-test checks agree; 700 "
        "random comparisons with pycryptodome and OpenSSL show no difference.",
        "The avalanche experiment reproduces Table 4.3 exactly; a 1-bit change of the key "
        "changes 30 of the 64 ciphertext bits.",
        "Each machine creates, encrypts, sends, receives, decrypts and displays messages; the "
        "displayed text is identical to the typed text, including non-ASCII characters. "
        "Only IVs and ciphertexts cross the network, as the packet capture shows.",
    ])
    R.para("DES itself must not be used to protect data today. Its 56-bit key was found by "
           "exhaustive search within days already in 1998 [12], and NIST withdrew FIPS 46-3 "
           "in 2005. A real system would use AES in an authenticated mode such as GCM, would "
           "detect modified messages (our CBC frames can be changed unnoticed), and would agree "
           "on fresh keys with a key-exchange protocol instead of a key stored in a "
           "configuration file. For learning how a block cipher works, however, DES is ideal: "
           "every step is small enough to watch in a debugger, and the whole algorithm fits in "
           "about 400 lines of C.")

    R.heading("4  References", 1)
    refs = [
        "National Institute of Standards and Technology, *FIPS PUB 46-3: Data Encryption "
        "Standard (DES)*, 25 October 1999 (withdrawn 19 May 2005).",
        "W. Stallings, *Cryptography and Network Security: Principles and Practice*, 8th ed., "
        "Pearson, 2020, Chapter 4 (Tables 4.2 - 4.4).",
        "CMPE455/CMSE456 lab handouts: *Lab 2 Task. DES on Two Computers* and *A DES Example* "
        "(DES_LAB_example), 2026.",
        "J. Orlin Grabbe, *The DES Algorithm Illustrated*, online article.",
        "National Bureau of Standards, *FIPS PUB 81: DES Modes of Operation*, 2 December 1980.",
        "M. Dworkin, *NIST SP 800-38A: Recommendation for Block Cipher Modes of Operation - "
        "Methods and Techniques*, NIST, December 2001.",
        "S. Keller and M. Smid, *NIST SP 800-17: Modes of Operation Validation System (MOVS) - "
        "Requirements and Procedures*, NIST, February 1998.",
        "R. Housley, *RFC 5652: Cryptographic Message Syntax (CMS)*, IETF, September 2009, "
        "Section 6.3 (padding).",
        "W. R. Stevens, B. Fenner and A. M. Rudoff, *UNIX Network Programming, Volume 1: The "
        "Sockets Networking API*, 3rd ed., Addison-Wesley, 2003.",
        "Docker Inc., *Bridge network driver*, Docker documentation (docs.docker.com).",
        "R. Stallman, R. Pesch, S. Shebs et al., *Debugging with GDB*, Free Software "
        "Foundation (sections on the TUI and the Python API).",
        "Electronic Frontier Foundation, *Cracking DES: Secrets of Encryption Research, "
        "Wiretap Politics & Chip Design*, O'Reilly, 1998.",
        "pycryptodome documentation (DES module); OpenSSL 3 documentation, legacy provider.",
        "Course starter code tcpServer.c and tcpClient.c (DES_tcp_server_client_program).",
    ]
    references(R, refs)

    # ------------------------------------------------------------------ appendices
    R.heading("Appendix A  Source code", 1, new_page=True)
    R.para("The complete source code of the programs, the tests and the deployment files. The "
           "helper scripts that generate the screenshots, the test examples and this report "
           "(`tools/`, `report/`) are included in the submission but not printed here.")
    sources = ["src/des.h", "src/des.c", "src/des_trace.h", "src/des_trace.c",
               "src/des_modes.h", "src/des_modes.c", "src/des_util.h", "src/des_util.c",
               "src/net.h", "src/net.c", "src/des_chat.h", "src/des_chat.c",
               "src/tcpServer.c", "src/tcpClient.c", "src/des_trace_main.c",
               "src/des_avalanche.c", "tests/test_des.c", "tests/crosscheck.py",
               "tests/test_loopback.sh", "debug/des_watch.py", "Makefile",
               "docker/Dockerfile", "docker-compose.yml", "docker/demo.sh"]
    for path in sources:
        text = read(path)
        R.heading(f"A.{sources.index(path) + 1}  {path}", 2)
        R.code(text, size=7)

    R.heading("Appendix B  Step table of the textbook example", 1, new_page=True)
    R.para("Every step of the encryption of `02468aceeca86420` with key `0f1571c947d9e859`, "
           "in the order of execution: the key schedule (rows 1 - 49), IP (row 50), the 16 "
           "rounds (rows 51 - 146), the 32-bit swap and IP^{-1} (rows 147 - 148). Generated by "
           "`bin/des_trace -f csv`; the same table with the 128 individual S-box look-ups is "
           "`test_examples/trace_textbook_encrypt_with_sboxes.csv`.")
    R.table(["#", "Round", "Input to method", "Method name", "Method output", "Current DES step"],
            [[r["seq"], r["round"] if r["round"] != "0" else "-", r["input"], r["method"],
              r["output"], breakable(f'{r["lab_item"]} {r["des_step"]}')] for r in tr],
            [0.8, 0.9, 4.1, 5.0, 3.6, 2.6], mono=(2, 3, 4), size=7.5, center=(0, 1),
            keep_together=False)

    R.heading("Appendix C  Submission contents and how to run", 1, new_page=True)
    R.code(SUBMISSION_LAYOUT, size=8)


# --------------------------------------------------------------------------- #
#  Two-pass build with page numbers                                            #
# --------------------------------------------------------------------------- #


def to_pdf(docx_path, outdir, env=None):
    profile = tempfile.mkdtemp(prefix="des-report-lo-")
    # LibreOffice probes OpenCL at start-up; on some GPU drivers (here: AMD ROCm)
    # that probe crashes. A text document needs neither OpenCL nor a GPU.
    env = dict(env or os.environ, SAL_DISABLE_OPENCL="1", SAL_USE_VCLPLUGIN="svp")
    try:
        subprocess.run(["soffice", f"-env:UserInstallation={pathlib.Path(profile).as_uri()}",
                        "--headless", "--convert-to", "pdf", "--outdir", outdir, docx_path],
                       check=True, capture_output=True, timeout=600, env=env)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    return os.path.join(outdir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")


def heading_pages(pdf, headings):
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], check=True,
                          capture_output=True, text=True).stdout
    pages = [[norm(line) for line in page.splitlines()
              if line.strip() and "...." not in line]          # skip TOC lines
             for page in text.split("\f")]
    result, start = {}, 0
    for level, title in headings:
        key, alt = norm(title), norm_nosup(title)
        for i in range(start, len(pages)):
            if key in pages[i] or alt in pages[i]:
                result[key] = i + 1
                start = i
                break
        else:
            print(f"warning: page of heading not found: {title}", file=sys.stderr)
    return result


def references(R, refs):
    """Numbered reference list; *text* is printed in italics."""
    for i, ref in enumerate(refs, 1):
        p = R.doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.9)
        p.paragraph_format.first_line_indent = Cm(-0.9)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.05
        r = p.add_run(f"[{i}]\t")
        r.font.size = Pt(10)
        for k, part in enumerate(re.split(r"\*(.+?)\*", ref)):
            r = p.add_run(part)
            r.italic = k % 2 == 1
            r.font.size = Pt(10)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(0.9))


def make(builder, cover, labels, headings, pages, path, report=Report):
    R = report(cover, labels, headings, pages)
    builder(R)
    R.save(path)
    return R


def build_document(builder, docx_path, pdf_path, report=Report, env=None):
    """Build twice so that the table of contents gets real page numbers.

    report: the class that writes the document; env: environment for LibreOffice"""
    with open(os.path.join(HERE, "cover.json"), encoding="utf-8") as f:
        cover = json.load(f)
    os.makedirs(BUILD, exist_ok=True)
    tmp_docx = os.path.join(BUILD, "pass_" + os.path.basename(docx_path))

    first = make(builder, cover, {}, [], {}, tmp_docx, report)       # labels + headings
    second = make(builder, cover, first.new_labels, first.headings, {}, tmp_docx, report)
    pages = heading_pages(to_pdf(tmp_docx, BUILD, env), second.headings)
    make(builder, cover, second.new_labels, second.headings, pages, docx_path, report)   # final
    pdf = to_pdf(docx_path, BUILD, env)
    shutil.move(pdf, pdf_path)
    for tmp in (tmp_docx, os.path.splitext(tmp_docx)[0] + ".pdf"):   # intermediate files
        if os.path.exists(tmp):
            os.remove(tmp)
    final_pages = heading_pages(pdf_path, second.headings)
    moved = [t for l, t in second.headings if final_pages.get(norm(t)) != pages.get(norm(t))]
    if moved:
        print("warning: page numbers moved for:", moved, file=sys.stderr)
    count = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True).stdout
    n = re.search(r"Pages:\s+(\d+)", count)
    print(f"report written: {os.path.relpath(docx_path, ROOT)}, "
          f"{os.path.relpath(pdf_path, ROOT)} ({n.group(1) if n else '?'} pages)")


def main():
    build_document(build, DOCX, PDF)


if __name__ == "__main__":
    main()
