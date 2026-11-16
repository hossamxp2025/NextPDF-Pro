"""Exercise the low-level PDF text stream independently of recognition quality."""
import pymupdf as fitz
import pytest
from src.engine.ocr_engine import OCREngine


@pytest.mark.parametrize("text", ["مرحبا بالعالم", "INV-2026-105", "15,750", "14/11/2026"])
def test_actualtext_word_layer_reopens_and_searches_at_word_box(tmp_path, text):
    path = tmp_path / "layer.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=400)
        words = [{"text": text, "left": 100, "top": 80, "width": 220, "height": 30}]
        OCREngine._insert_word_layer(page, words, 1, 1)
        doc.save(path)
    with fitz.open(path) as doc:
        page = doc[0]
        assert text in page.get_text()
        hits = page.search_for(text)
        assert hits
        rect = hits[0]
        assert abs(rect.x0 - 100) < 1
        assert abs(rect.x1 - 320) < 1
        assert abs(rect.y0 - 80) < 1
        assert abs(rect.y1 - 110) < 1
        assert not doc.is_repaired
        assert all(v == 255 for v in page.get_pixmap().samples)
