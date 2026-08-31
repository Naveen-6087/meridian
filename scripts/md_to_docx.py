"""Markdown -> professional, research-paper-styled Word (.docx) converter.

Handles: title page, #/##/### headers with numbered-paper styling,
**bold**, `inline code`, fenced code blocks, pipe tables (styled with a
shaded header row), bullet/numbered lists, blockquotes, horizontal rules
(rendered as a section break), and ![caption](path) images (embedded,
scaled to the page width, with a centered italic caption below).

Not a general-purpose converter -- built to match this project's specific
docs/*.md and report/*.md style.
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY = RGBColor(0x1B, 0x2A, 0x4A)
ACCENT = RGBColor(0x1F, 0x4E, 0x8C)
CODE_RED = RGBColor(0xA0, 0x22, 0x22)
HEADER_FILL = "1F4E8C"
BAND_FILL = "EAF1FB"

BODY_FONT = "Cambria"
HEAD_FONT = "Cambria"
MONO_FONT = "Consolas"


def set_cell_background(cell, hex_color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def add_page_number_field(paragraph):
    run = paragraph.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run._r.append(fld)


def setup_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for level, size, color in [(1, 20, NAVY), (2, 15, ACCENT), (3, 12.5, ACCENT), (4, 11, ACCENT)]:
        try:
            h = doc.styles[f"Heading {level}"]
        except KeyError:
            continue
        h.font.name = HEAD_FONT
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.color.rgb = color
        h.paragraph_format.space_before = Pt(14 if level == 1 else 10)
        h.paragraph_format.space_after = Pt(6)

    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.3)
    section.right_margin = Cm(2.3)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)


def add_footer_page_numbers(doc, footer_text):
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"{footer_text}  ·  Page ")
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    add_page_number_field(p)


def add_header_running_title(doc, title_text):
    section = doc.sections[0]
    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(title_text)
    run.font.size = Pt(8.5)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)


def add_title_page(doc, title, subtitle, meta_lines):
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    run.font.size = Pt(26)
    run.font.bold = True
    run.font.color.rgb = NAVY
    run.font.name = HEAD_FONT

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = p2.add_run(subtitle)
    run2.font.size = Pt(14)
    run2.font.color.rgb = ACCENT
    run2.font.italic = True

    doc.add_paragraph()
    rule = doc.add_paragraph()
    rule.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rrun = rule.add_run("─" * 40)
    rrun.font.color.rgb = ACCENT

    doc.add_paragraph()
    for line in meta_lines:
        p3 = doc.add_paragraph()
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r3 = p3.add_run(line)
        r3.font.size = Pt(11.5)
        r3.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    for _ in range(6):
        doc.add_paragraph()
    doc.add_page_break()


def add_bold_runs(paragraph, text):
    tokens = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            run = paragraph.add_run(tok[2:-2])
            run.bold = True
        elif tok.startswith("`") and tok.endswith("`"):
            run = paragraph.add_run(tok[1:-1])
            run.font.name = MONO_FONT
            run.font.size = Pt(9.5)
            run.font.color.rgb = CODE_RED
        else:
            paragraph.add_run(tok)


def parse_table_rows(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        line = lines[i].strip()
        if re.match(r"^\|[\s:\-|]+\|$", line):
            i += 1
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
        i += 1
    return rows, i


def add_styled_table(doc, rows):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for r, row in enumerate(rows):
        for c, cell_text in enumerate(row):
            if c >= len(table.columns):
                continue
            cell = table.cell(r, c)
            cell.text = ""
            p = cell.paragraphs[0]
            add_bold_runs(p, cell_text)
            for run in p.runs:
                run.font.size = Pt(9.5)
            if r == 0:
                set_cell_background(cell, HEADER_FILL)
                for run in p.runs:
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    run.bold = True
            elif r % 2 == 0:
                set_cell_background(cell, BAND_FILL)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def add_image_with_caption(doc, md_path: Path, image_ref: str, caption: str):
    img_path = (md_path.parent / image_ref).resolve()
    if not img_path.exists():
        # try resolving relative to the docx script's project root
        alt = (Path(__file__).resolve().parent.parent / image_ref).resolve()
        img_path = alt if alt.exists() else img_path
    if not img_path.exists():
        p = doc.add_paragraph()
        r = p.add_run(f"[missing image: {image_ref}]")
        r.italic = True
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(img_path), width=Inches(6.0))
    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cr = cap.add_run(caption)
        cr.font.size = Pt(9.5)
        cr.font.italic = True
        cr.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    doc.add_paragraph()


def convert(md_path: Path, docx_path: Path, title: str, subtitle: str, meta_lines: list):
    doc = Document()
    setup_styles(doc)
    add_header_running_title(doc, title)
    add_footer_page_numbers(doc, "P14 — Configuration Drift Ranking")
    add_title_page(doc, title, subtitle, meta_lines)

    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    in_code = False
    code_buf = []

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Pt(10)
                shading_elm = OxmlElement("w:shd")
                shading_elm.set(qn("w:fill"), "F4F6F8")
                p._p.get_or_add_pPr().append(shading_elm)
                run = p.add_run("\n".join(code_buf))
                run.font.name = MONO_FONT
                run.font.size = Pt(9)
                p.paragraph_format.space_after = Pt(10)
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        img_match = re.match(r"^!\[(.*?)\]\((.*?)\)", stripped)
        if img_match:
            add_image_with_caption(doc, md_path, img_match.group(2), img_match.group(1))
            i += 1
            continue

        if stripped.startswith("#"):
            m = re.match(r"^(#{1,4})\s+(.*)", stripped)
            if m:
                level = len(m.group(1))
                doc.add_heading(m.group(2), level=level)
            i += 1
            continue

        if stripped.startswith("|"):
            rows, i = parse_table_rows(lines, i)
            if rows:
                add_styled_table(doc, rows)
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            p = doc.add_paragraph(style="List Bullet")
            add_bold_runs(p, stripped[2:])
            i += 1
            continue

        m = re.match(r"^\d+\.\s+(.*)", stripped)
        if m:
            p = doc.add_paragraph(style="List Number")
            add_bold_runs(p, m.group(1))
            i += 1
            continue

        if stripped.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(18)
            shading_elm = OxmlElement("w:shd")
            shading_elm.set(qn("w:fill"), "EAF1FB")
            p._p.get_or_add_pPr().append(shading_elm)
            add_bold_runs(p, stripped.lstrip("> ").strip())
            i += 1
            continue

        if stripped == "---":
            doc.add_paragraph()
            i += 1
            continue

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_bold_runs(p, stripped)
        i += 1

    doc.save(str(docx_path))
    print(f"Wrote {docx_path}")


if __name__ == "__main__":
    md_file = Path(sys.argv[1])
    out_file = Path(sys.argv[2])
    doc_title = sys.argv[3] if len(sys.argv) > 3 else md_file.stem
    doc_subtitle = sys.argv[4] if len(sys.argv) > 4 else "BCSE408L Cloud Computing — Project P14"
    convert(md_file, out_file, doc_title, doc_subtitle,
            ["BCSE408L — Cloud Computing", "Project P14: Risk-Ranked Detection and Remediation of Configuration Drift in IaC",
             "2026"])
