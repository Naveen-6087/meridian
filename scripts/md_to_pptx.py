"""Markdown -> PowerPoint converter, styled to match the Word-doc reports
(navy/accent color scheme, same section structure). One slide per H1/H2
heading; paragraphs become bullets, pipe tables become native tables,
images are placed on their own slide.

Not committed to git per project convention -- regenerate locally with:
    python scripts/md_to_pptx.py docs/review-1.md "report/pptx/Review 1.pptx" "Review 1" "Problem Formulation and Baseline"
"""
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

NAVY = RGBColor(0x1B, 0x2A, 0x4A)
ACCENT = RGBColor(0x1F, 0x4E, 0x8C)
LIGHT_BG = RGBColor(0xEA, 0xF1, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK_TEXT = RGBColor(0x22, 0x22, 0x22)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def strip_inline_md(text):
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def add_title_slide(prs, title, subtitle, meta):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(1, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    bg.shadow.inherit = False

    tb = slide.shapes.add_textbox(Inches(0.9), Inches(2.4), Inches(11.5), Inches(2.0))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = WHITE

    tb2 = slide.shapes.add_textbox(Inches(0.9), Inches(3.6), Inches(11.5), Inches(1.0))
    p2 = tb2.text_frame.paragraphs[0]
    p2.text = subtitle
    p2.font.size = Pt(20)
    p2.font.italic = True
    p2.font.color.rgb = RGBColor(0xBB, 0xD0, 0xF0)

    tb3 = slide.shapes.add_textbox(Inches(0.9), Inches(5.2), Inches(11.5), Inches(1.4))
    tf3 = tb3.text_frame
    for i, line in enumerate(meta):
        p3 = tf3.paragraphs[0] if i == 0 else tf3.add_paragraph()
        p3.text = line
        p3.font.size = Pt(13)
        p3.font.color.rgb = RGBColor(0xDD, 0xE6, 0xF2)
    return slide


def add_section_header(slide_layout_blank, prs, heading):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.shapes.add_shape(1, 0, 0, SLIDE_W, Inches(1.1))
    bg.fill.solid()
    bg.fill.fore_color.rgb = ACCENT
    bg.line.fill.background()
    bg.shadow.inherit = False
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.18), Inches(12.3), Inches(0.8))
    p = tb.text_frame.paragraphs[0]
    p.text = strip_inline_md(heading)
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = WHITE
    return slide


def add_bullets(slide, bullets, top=Inches(1.35)):
    box = slide.shapes.add_textbox(Inches(0.6), top, Inches(12.1), Inches(5.8))
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for level, text in bullets:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = strip_inline_md(text)
        p.level = min(level, 4)
        p.font.size = Pt(18 if level == 0 else 15)
        p.font.color.rgb = DARK_TEXT
        p.space_after = Pt(8)
    return box


def add_table(slide, rows, top=Inches(1.35)):
    n_rows, n_cols = len(rows), len(rows[0])
    width = Inches(12.1)
    height = Inches(min(0.5 * n_rows, 5.6))
    shape = slide.shapes.add_table(n_rows, n_cols, Inches(0.6), top, width, height)
    table = shape.table
    for r, row in enumerate(rows):
        for c, cell_text in enumerate(row):
            if c >= n_cols:
                continue
            cell = table.cell(r, c)
            cell.text = strip_inline_md(cell_text)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11 if n_rows <= 8 else 9)
                if r == 0:
                    p.font.bold = True
                    p.font.color.rgb = WHITE
                else:
                    p.font.color.rgb = DARK_TEXT
            if r == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = ACCENT
            elif r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT_BG
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE
    return shape


def add_image_slide(prs, heading, img_path: Path):
    slide = add_section_header(None, prs, heading)
    if img_path.exists():
        pic = slide.shapes.add_picture(str(img_path), Inches(1.2), Inches(1.3), height=Inches(5.8))
        if pic.width > Inches(10.9):
            ratio = Inches(10.9) / pic.width
            pic.width = Inches(10.9)
            pic.height = Emu(int(pic.height * ratio))
            pic.left = Inches(1.2)
    return slide


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


def convert(md_path: Path, pptx_path: Path, title: str, subtitle: str, meta: list):
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    add_title_slide(prs, title, subtitle, meta)

    lines = md_path.read_text(encoding="utf-8").splitlines()
    i = 0
    current_slide = None
    bullets_buf = []
    in_code = False
    code_buf = []

    def flush_bullets():
        nonlocal bullets_buf, current_slide
        if bullets_buf and current_slide is not None:
            add_bullets(current_slide, bullets_buf)
        bullets_buf = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                bullets_buf.append((0, "  ".join(code_buf[:6])))
            i += 1
            continue
        if in_code:
            code_buf.append(stripped)
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        img_match = re.match(r"^!\[(.*?)\]\((.*?)\)", stripped)
        if img_match:
            flush_bullets()
            img_ref = img_match.group(2)
            img_path = (md_path.parent / img_ref).resolve()
            if not img_path.exists():
                img_path = (Path(__file__).resolve().parent.parent / img_ref).resolve()
            current_slide = add_image_slide(prs, img_match.group(1) or "Figure", img_path)
            i += 1
            continue

        m = re.match(r"^(#{1,3})\s+(.*)", stripped)
        if m:
            flush_bullets()
            current_slide = add_section_header(None, prs, m.group(2))
            i += 1
            continue

        if stripped.startswith("|"):
            flush_bullets()
            rows, i = parse_table_rows(lines, i)
            if rows and current_slide is not None:
                add_table(current_slide, rows)
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            bullets_buf.append((0, stripped[2:]))
            i += 1
            continue

        mnum = re.match(r"^\d+\.\s+(.*)", stripped)
        if mnum:
            bullets_buf.append((0, mnum.group(1)))
            i += 1
            continue

        if stripped.startswith(">"):
            bullets_buf.append((1, stripped.lstrip("> ").strip()))
            i += 1
            continue

        if stripped == "---":
            i += 1
            continue

        bullets_buf.append((0, stripped))
        i += 1

    flush_bullets()
    prs.save(str(pptx_path))
    print(f"Wrote {pptx_path}")


if __name__ == "__main__":
    md_file = Path(sys.argv[1])
    out_file = Path(sys.argv[2])
    doc_title = sys.argv[3] if len(sys.argv) > 3 else md_file.stem
    doc_subtitle = sys.argv[4] if len(sys.argv) > 4 else "BCSE408L Cloud Computing -- Project P14"
    convert(md_file, out_file, doc_title, doc_subtitle,
            ["BCSE408L -- Cloud Computing",
             "Project P14: Risk-Ranked Detection and Remediation of Configuration Drift in IaC",
             "2026"])
