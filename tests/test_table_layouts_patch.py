import io

import pymupdf as fitz
import pytest
from openpyxl import load_workbook

from src.engine.conversion import export_pdf


@pytest.mark.parametrize('layout', ['complete', 'partial', 'borderless', 'multiple', 'pages'])
def test_table_layouts(tmp_path, layout):
    with fitz.open() as doc:
        for p in range(2 if layout == 'pages' else 1):
            page = doc.new_page(width=600, height=600)
            for offset in ([0, 220] if layout == 'multiple' else [0]):
                if layout != 'borderless':
                    for y in (40, 80, 120, 160):
                        page.draw_line((40, y + offset), (420, y + offset))
                    if layout == 'complete' or layout in {'multiple', 'pages'}:
                        for x in (40, 230, 420):
                            page.draw_line((x, 40 + offset), (x, 160 + offset))
                    else:
                        # Small interrupted vertical rules, joined within tolerance.
                        for x in (40, 230, 420):
                            page.draw_line((x, 40 + offset), (x, 99 + offset))
                            page.draw_line((x, 101 + offset), (x, 160 + offset))
                for r, values in enumerate([('Item', 'Amount'), ('Invoice', '125.50'), ('Date', '2026-11-15')]):
                    for c, text in enumerate(values):
                        page.insert_text((50 + 190 * c, 65 + 40 * r + offset), text)
            data = doc.tobytes()
    target = tmp_path / 'table.xlsx'
    export_pdf(data, str(target), list(range(1, 3 if layout == 'pages' else 2)), 'xlsx')
    book = load_workbook(target)
    try:
        assert len(book.worksheets) == (2 if layout in {'pages', 'multiple'} else 1)
        assert book.active['A1'].value == 'Item'
        assert book.active['B2'].value == 125.5
        assert book.active['B3'].value.year == 2026
    finally:
        book.close()


def test_scanned_table_refused(tmp_path):
    from PIL import Image
    image = io.BytesIO()
    Image.new('RGB', (400, 300), 'white').save(image, format='PNG')
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_image(page.rect, stream=image.getvalue())
        data = doc.tobytes()
    with pytest.raises(ValueError, match='No supported tables'):
        export_pdf(data, str(tmp_path / 'scan.xlsx'), [1], 'xlsx')
