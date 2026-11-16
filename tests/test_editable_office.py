"""Editable Office modes must contain real text (not a page picture)."""
import pymupdf as fitz
import pytest
from docx import Document
from docx.oxml.ns import qn
from openpyxl import load_workbook
from pptx import Presentation
from datetime import date

from src.config import FONTS_DIR
from src.engine.conversion import export_pdf

FONT = str(FONTS_DIR / "NotoNaskhArabic-Regular.ttf")


def _text_pdf(path, lines):
    """PDF built with TextWriter: real Unicode text, not an image."""
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=400)
        writer = fitz.TextWriter(page.rect)
        y = 90
        for text, fontfile in lines:
            font = fitz.Font(fontfile=fontfile) if fontfile else fitz.Font("helv")
            writer.append((40, y), text, font=font)
            y += 50
        writer.write_text(page)
        doc.save(path)
    return path


def test_editable_docx_reconstructs_arabic_and_keeps_latin(tmp_path):
    source = _text_pdf(tmp_path / "source.pdf", [
        ("مرحبا بالعالم", FONT),
        ("INVOICE TOTAL", None),
    ])
    with fitz.open(source) as doc:
        data = doc.tobytes()
    target = tmp_path / "editable.docx"
    export_pdf(data, str(target), [1], "docx_editable")
    paragraphs = [p.text for p in Document(target).paragraphs if p.text.strip()]
    assert "مرحبا بالعالم" in paragraphs
    assert "INVOICE TOTAL" in paragraphs
    arabic = next(p for p in Document(target).paragraphs if "مرحبا" in p.text)
    assert arabic._p.find(qn("w:pPr")).find(qn("w:bidi")) is not None
    assert arabic.runs[0]._element.find(qn("w:rPr")).find(qn("w:rtl")) is not None


def test_editable_pptx_reconstructs_arabic_text_box(tmp_path):
    source = _text_pdf(tmp_path / "source.pdf", [("مرحبا بالعالم", FONT)])
    with fitz.open(source) as doc:
        data = doc.tobytes()
    target = tmp_path / "editable.pptx"
    export_pdf(data, str(target), [1], "pptx_editable")
    presentation = Presentation(target)
    texts = [shape.text_frame.text for shape in presentation.slides[0].shapes
             if shape.has_text_frame and shape.text_frame.text.strip()]
    assert "مرحبا بالعالم" in texts
    box = next(shape for shape in presentation.slides[0].shapes
               if shape.has_text_frame and "مرحبا" in shape.text_frame.text)
    assert box.left >= 0 and box.top >= 0
    paragraph = box.text_frame.paragraphs[0]
    assert paragraph._p.find(qn("a:pPr")).get("rtl") == "1"


def test_editable_export_refuses_mixed_or_damaged_visual_arabic(tmp_path):
    """Mixed Latin/digits and damaged maps must be refused, not reversed blindly."""
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=200)
        writer = fitz.TextWriter(page.rect)
        writer.append((40, 100), "رقم الفاتورة INV-2026-105", font=fitz.Font(fontfile=FONT))
        writer.write_text(page)
        data = doc.tobytes()
    for suffix in ("docx_editable", "pptx_editable"):
        target = tmp_path / ("refused." + suffix.split("_")[0])
        with pytest.raises(ValueError):
            export_pdf(data, str(target), [1], suffix)
        assert not target.exists()


def test_editable_export_refuses_damaged_tounicode():
    from src.engine.conversion import _logical_text
    with pytest.raises(ValueError):
        _logical_text("ﻡﻝﺍﻉĦﻝﺍﺏ")  # shaped Arabic plus leaked Latin-Extended junk
    with pytest.raises(ValueError):
        _logical_text("ﻡﻝﺍﻉ 15,750")  # digits in visual order are ambiguous
    assert _logical_text("LOGICAL ARABIC") == "LOGICAL ARABIC"


def test_excel_writes_recognized_dates_and_numbers(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page(width=420, height=260)
        xs = (30, 160, 290, 400)
        ys = (30, 70, 110, 150)
        for x in xs:
            page.draw_line((x, ys[0]), (x, ys[-1]))
        for y in ys:
            page.draw_line((xs[0], y), (xs[-1], y))
        rows = (("Item", "Date", "Amount"), ("INV-1", "2026-11-14", "15750"),
                ("INV-2", "14/11/2026", "2026"))
        for r, values in enumerate(rows):
            for c, text in enumerate(values):
                page.insert_text((xs[c] + 8, ys[r] + 26), text, fontsize=11)
        data = doc.tobytes()
    target = tmp_path / "dated.xlsx"
    export_pdf(data, str(target), [1], "xlsx")
    book = load_workbook(target)
    try:
        sheet = book.active
        assert sheet.cell(2, 2).value.date() == date(2026, 11, 14)
        assert sheet.cell(2, 2).number_format == "yyyy-mm-dd"
        assert sheet.cell(2, 3).value == 15750
        assert sheet.cell(3, 2).value.date() == date(2026, 11, 14)
        assert sheet.cell(3, 2).number_format == "dd/mm/yyyy"
    finally:
        book.close()
