# -*- coding: utf-8 -*-
"""Arabic text layer contract: text inserted or edited by NextPDF Pro must be
stored as logical Unicode (searchable, extractable, exportable), not as a
visual string of presentation forms, and edits must leave no stale glyphs.

These tests reopen the saved file with plain PyMuPDF so they measure what
other readers see, not what the in-memory model believes.
"""
import os
import unicodedata

import pymupdf as fitz
import pytest

from src.engine.text_editor import TextEditor
from src.engine.text_engine import TextEngine, TextStyle, parse_tounicode, build_tounicode
from src.engine.fonts import get_font_registry, DEFAULT_ARABIC_FAMILY, FALLBACK_FAMILY
from src.engine import conversion
from src.models.document import PDFDocument

AR_LINE = "إجمالي المبلغ المستحق 15,750.00 ريال سعودي"
AR_EDIT = "إجمالي المبلغ المستحق 18,500.00 ريال سعودي"
PRESENTATION = tuple((lo, hi) for lo, hi in (("ﭐ", "﷿"), ("ﹰ", "﻿")))


def _norm(s):
    return " ".join(unicodedata.normalize("NFKC", s).split())


def _has_presentation_forms(text):
    return any(lo <= ch <= hi for ch in text for lo, hi in PRESENTATION)


def _source(path):
    with fitz.open() as d:
        p = d.new_page()
        p.insert_text((60, 80), "Invoice INV-2026/0042", fontsize=12)
        d.save(str(path))
    return str(path)


def _reopen(path):
    return fitz.open(str(path))


# --------------------------------------------------------------------- insert
def test_inserted_arabic_is_searchable_after_reopen(tmp_path):
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    res = TextEditor(doc).add_text(1, 400, 200, AR_LINE, font_size=14)
    assert res.success, res.message
    out = tmp_path / "added.pdf"
    assert doc.save(str(out))

    page = _reopen(out)[0]
    text = page.get_text()
    assert not _has_presentation_forms(text)
    assert _norm(AR_LINE) in _norm(text)
    for needle in ("المبلغ", "المستحق", "15,750.00", "ريال", "سعودي", "INV-2026"):
        assert page.search_for(needle), f"{needle!r} not found"
    assert any(DEFAULT_ARABIC_FAMILY in f[3] for f in page.get_fonts())


def test_inserted_line_is_one_run_in_logical_order(tmp_path):
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    assert TextEditor(doc).add_text(1, 400, 200, AR_LINE, font_size=14).success
    runs = [r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL"]
    assert len(runs) == 1, [r.text for r in runs]
    assert _norm(runs[0].text) == _norm(AR_LINE)


@pytest.mark.parametrize("text", [
    "شكراً لتعاملكم",                       # tanween mark
    "Thank you — شكراً لتعاملكم",           # LTR paragraph with an Arabic run
    "القاهرة، مصر — 2026/11/16",            # punctuation, digits, dash
    "لا إله إلا الله",                      # lam-alef ligatures
    "Mixed English and عربي together 42",   # bidi runs both ways
    "ﻣﺮﺣﺒﺎ",                                # presentation forms typed by the user
])
def test_text_layer_round_trips(tmp_path, text):
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    assert TextEditor(doc).add_text(1, 300, 300, text, font_size=14).success
    out = tmp_path / "out.pdf"
    assert doc.save(str(out))
    page = _reopen(out)[0]
    extracted = page.get_text()
    assert _norm(text) in _norm(extracted), extracted


def test_fallback_family_keeps_full_tashkeel(tmp_path):
    """DejaVu Sans keeps stacked marks (shadda + vowel) in the text layer."""
    text = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    assert TextEditor(doc).add_text(1, 400, 300, text, font_family=FALLBACK_FAMILY, font_size=14).success
    out = tmp_path / "out.pdf"
    assert doc.save(str(out))
    assert _norm(text) in _norm(_reopen(out)[0].get_text())


# ----------------------------------------------------------------------- edit
def test_editing_arabic_line_leaves_no_stale_glyphs(tmp_path):
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    editor = TextEditor(doc)
    assert editor.add_text(1, 400, 200, AR_LINE, font_size=14).success
    added = tmp_path / "added.pdf"
    assert doc.save(str(added))

    doc = PDFDocument()
    assert doc.load(str(added))
    editor = TextEditor(doc)
    run = next(r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL")
    old_bbox = fitz.Rect(*run.bbox)
    res = editor.replace_text_run(run.run_id, AR_EDIT)
    assert res.success, res.message
    edited = tmp_path / "edited.pdf"
    assert doc.save(str(edited))

    page = _reopen(edited)[0]
    text = page.get_text()
    assert _norm(AR_EDIT) in _norm(text)
    assert "15,750.00" not in text
    assert page.search_for("18,500.00") and not page.search_for("15,750.00")
    assert "Invoice INV-2026/0042" in text          # untouched line survives
    # Exactly one RTL line remains, in the band of the old one.
    rtl = [r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL"]
    assert len(rtl) == 1
    new_bbox = fitz.Rect(*rtl[0].bbox)
    assert abs(new_bbox.y0 - old_bbox.y0) < 1.0, (new_bbox, old_bbox)
    assert abs(new_bbox.x1 - old_bbox.x1) < 1.0, (new_bbox, old_bbox)


@pytest.mark.parametrize("replacement", [
    AR_EDIT,                                                     # same length
    "إجمالي المبلغ المستحق 18,500.00 ريال سعودي فقط لا غير",     # longer
    "قصير",                                                      # much shorter
])
def test_replacement_keeps_the_line_anchor(tmp_path, replacement):
    """Whatever its length, the new RTL line keeps the old right edge and
    baseline band; it grows towards the free (left) side."""
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    assert TextEditor(doc).add_text(1, 400, 250, AR_LINE, font_size=14).success
    added = tmp_path / "added.pdf"
    assert doc.save(str(added))

    doc = PDFDocument()
    assert doc.load(str(added))
    run = next(r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL")
    old = fitz.Rect(*run.bbox)
    assert TextEditor(doc).replace_text_run(run.run_id, replacement).success
    out = tmp_path / "edited.pdf"
    assert doc.save(str(out))

    new = fitz.Rect(*next(r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL").bbox)
    assert abs(new.x1 - old.x1) < 1.0, (new, old)
    assert abs(new.y0 - old.y0) < 1.0, (new, old)
    page = _reopen(out)[0]
    assert _norm(replacement) in _norm(page.get_text()), page.get_text()


def test_insertion_is_anchored_at_the_requested_point(tmp_path):
    """The requested point is the text's top-right corner for RTL and its
    top-left corner for LTR (no drift from the layout box's padding)."""
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    editor = TextEditor(doc)
    assert editor.add_text(1, 400, 250, AR_LINE, font_size=14).success
    assert editor.add_text(1, 120, 400, "Added by NextPDF 2026", font_size=14).success
    out = tmp_path / "anchored.pdf"
    assert doc.save(str(out))

    page = _reopen(out)[0]
    spans = [s for b in page.get_text("dict")["blocks"]
             for line in b.get("lines", []) for s in line["spans"] if s["text"].strip()]
    arabic = [s for s in spans if any("؀" <= c <= "ۿ" for c in s["text"])]
    latin = [s for s in spans if "Added by NextPDF" in s["text"]]
    assert arabic and latin
    assert abs(max(s["bbox"][2] for s in arabic) - 400) < 1.0
    assert abs(min(s["bbox"][1] for s in arabic) - 250) < 1.0
    assert abs(latin[0]["bbox"][0] - 120) < 1.0
    assert abs(latin[0]["bbox"][1] - 400) < 1.0


def test_delete_arabic_line_removes_ink_and_text(tmp_path):
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    editor = TextEditor(doc)
    res = editor.add_text(1, 400, 200, AR_LINE, font_size=14)
    assert res.success
    run = next(r for r in doc.get_text_runs_for_page(1) if r.direction == "RTL")
    band = fitz.Rect(*run.bbox)
    assert editor.delete_text_run(run.run_id)
    out = tmp_path / "deleted.pdf"
    assert doc.save(str(out))
    page = _reopen(out)[0]
    assert not page.search_for("المبلغ")
    pix = page.get_pixmap(dpi=72, clip=band)
    assert all(b > 240 for b in pix.samples), "ink left behind after delete"


# --------------------------------------------------------------------- export
def test_text_exports_contain_inserted_arabic(tmp_path):
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    assert TextEditor(doc).add_text(1, 400, 200, AR_LINE, font_size=14).success
    out = tmp_path / "added.pdf"
    assert doc.save(str(out))
    data = out.read_bytes()

    txt = tmp_path / "out.txt"
    conversion.export_pdf(data, str(txt), [1], "txt")
    assert "المبلغ المستحق 15,750.00" in txt.read_text(encoding="utf-8")

    docx = tmp_path / "out.docx"
    conversion.export_pdf(data, str(docx), [1], "docx_editable")
    from docx import Document
    joined = _norm(" ".join(p.text for p in Document(str(docx)).paragraphs))
    assert "المبلغ المستحق 15,750.00" in joined


# --------------------------------------------------------------- font bloat
def test_repeated_inserts_do_not_bloat_saved_file(tmp_path):
    doc = PDFDocument()
    assert doc.load(_source(tmp_path / "src.pdf"))
    editor = TextEditor(doc)
    for i in range(6):
        assert editor.add_text(1, 400, 120 + i * 60, f"سطر رقم {i} — line {i}", font_size=12).success
    out = tmp_path / "many.pdf"
    assert doc.save(str(out))
    size = os.path.getsize(out)
    registry = get_font_registry()
    full = os.path.getsize(registry.get_family(DEFAULT_ARABIC_FAMILY).face().path)
    assert size < full * 2, f"saved file is {size} bytes; fonts were not subset"
    page = _reopen(out)[0]
    for i in range(6):
        assert page.search_for(f"رقم {i}"), i


# ------------------------------------------------------------ unit helpers
def test_tounicode_round_trip():
    mapping = {5: "ا", 6: "لا", 7: "", 300: "A"}
    parsed = parse_tounicode(build_tounicode(mapping).decode("latin-1"))
    assert parsed[5] == "ا" and parsed[6] == "لا" and parsed[300] == "A"
    assert parsed[7] in ("", "\x00")


def test_bfrange_parsing():
    cmap = "1 beginbfrange\n<0041> <0043> <0061>\nendbfrange\n1 beginbfrange\n<0010> <0011> [<0627> <0628>]\nendbfrange"
    parsed = parse_tounicode(cmap)
    assert parsed[0x41] == "a" and parsed[0x43] == "c"
    assert parsed[0x10] == "ا" and parsed[0x11] == "ب"


def test_engine_refuses_empty_and_tiny_boxes():
    engine = TextEngine()
    with fitz.open() as d:
        page = d.new_page()
        assert not engine.insert_text(page, fitz.Rect(10, 10, 100, 40), "   ", TextStyle()).success
        assert not engine.insert_text(page, fitz.Rect(10, 10, 11, 40), "x", TextStyle()).success
