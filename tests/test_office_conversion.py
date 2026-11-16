"""Office outputs must reopen with actual images or genuine table cells."""
import csv
import io
import pymupdf as fitz
import pytest
from docx import Document
from pptx import Presentation
from openpyxl import load_workbook
from PIL import Image
from src.engine.conversion import export_pdf
from src.engine.ocr_engine import OCREngine
from src.config import FONTS_DIR


@pytest.mark.parametrize("extension", ["docx", "pptx"])
def test_layout_office_export_contains_page_image(extension, tmp_path):
    with fitz.open() as doc:
        page = doc.new_page(width=500, height=300)
        page.insert_text((40, 100), "OFFICE LAYOUT", fontsize=24)
        page.insert_htmlbox(fitz.Rect(40, 130, 460, 220), "<p dir='rtl'>شركة المستقبل للتقنية</p>",
                            css="@font-face {font-family:A;src:url('NotoNaskhArabic-Regular.ttf');} body{font-family:A;font-size:24px;}",
                            archive=fitz.Archive(str(FONTS_DIR)))
        expected = page.get_pixmap(dpi=150, alpha=False)
        data = doc.tobytes()
    path = tmp_path / ("layout." + extension)
    export_pdf(data, str(path), [1], extension)
    if extension == "docx":
        reopened = Document(path)
        assert len(reopened.inline_shapes) == 1
        blob = reopened.inline_shapes[0]._inline.graphic.graphicData.pic.blipFill.blip.embed
        image_data = reopened.part.related_parts[blob].blob
    else:
        reopened = Presentation(path)
        assert len(reopened.slides) == 1
        image_data = reopened.slides[0].shapes[0].image.blob
    with Image.open(io.BytesIO(image_data)) as image:
        assert image.size == (expected.width, expected.height)
        assert image.convert("RGB").tobytes() == expected.samples


@pytest.mark.parametrize("extension", ["xlsx", "csv"])
def test_genuine_grid_table_exports_cells(extension, tmp_path):
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        for x in (40, 180, 320):
            page.draw_line((x, 40), (x, 160))
        for y in (40, 80, 120, 160):
            page.draw_line((40, y), (320, y))
        for row, values in enumerate((("Item", "Amount"), ("INV-2026-105", "15750"), ("Second", "2026"))):
            for col, value in enumerate(values):
                page.insert_text((50 + col * 140, 65 + row * 40), value, fontsize=12)
        data = doc.tobytes()
    target = tmp_path / ("table." + extension)
    export_pdf(data, str(target), [1], extension)
    if extension == "xlsx":
        book = load_workbook(target)
        rows = list(book.active.values)
        book.close()
        assert rows[1] == ("INV-2026-105", 15750)
    else:
        with target.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream))
        assert rows[1] == ["INV-2026-105", "15750"]
    assert rows[0][0] == "Item"


def test_excel_refuses_arbitrary_paragraph(tmp_path):
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 100), "This is not a table")
        data = doc.tobytes()
    target = tmp_path / "not_table.xlsx"
    with pytest.raises(ValueError):
        export_pdf(data, str(target), [1], "xlsx")
    assert not target.exists()


def test_arabic_grid_table_exports_logical_text_and_rtl_sheet(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=300)
        for x in (40, 180, 320):
            page.draw_line((x, 40), (x, 120))
        for y in (40, 80, 120):
            page.draw_line((40, y), (320, y))
        for r, values in enumerate((("الشركة", "القيمة"), ("شركة المستقبل", "15750"))):
            for c, text in enumerate(values):
                OCREngine._insert_word_layer(page, [{"text": text, "left": 50+c*140,
                                                   "top": 50+r*40, "width": 110, "height": 20}], 1, 1)
        data = doc.tobytes()
    path = tmp_path / "arabic.xlsx"
    export_pdf(data, str(path), [1], "xlsx")
    book = load_workbook(path)
    try:
        assert book.active.sheet_view.rightToLeft
        assert book.active.cell(1,1).value == "الشركة"
        assert book.active.cell(2,1).value == "شركة المستقبل"
        assert book.active.cell(2,2).value == 15750
    finally:
        book.close()
