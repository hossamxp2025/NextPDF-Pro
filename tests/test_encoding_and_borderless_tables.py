# -*- coding: utf-8 -*-
"""Regression tests for two field defects.

1. A PDF whose embedded font has no ToUnicode map used to export Latin
   Extended "garbage" instead of Arabic.  The export must now repair it from
   the font's cmap, or refuse when the font is not embedded.
2. A statement table drawn with shaded rows and no ruling lines used to be
   dropped by ``find_tables(strategy="lines")``.  It must be detected, keep its
   numeric values, and keep RTL column order.

All fixtures are synthetic; no customer data is used.
"""
import datetime

import pymupdf as fitz
import pytest
from docx import Document
from openpyxl import load_workbook

from src.engine import conversion
from src.engine.conversion import export_pdf
from tests.pdf_fixtures import (build_borderless_table_pdf,
                               build_broken_encoding_pdf)


# --------------------------------------------------------------------------
# Unit level: the guard and the visual -> logical flip
# --------------------------------------------------------------------------

def test_logical_text_refuses_glyph_id_dump():
    garbled = "\u010c\u0188\u01a2\u0197\u01b8\u01a5\u01bf"
    with pytest.raises(ValueError, match="damaged|Unicode"):
        conversion._logical_text(garbled)


def test_logical_text_keeps_plain_english():
    assert conversion._logical_text("Invoice INV-2026-105") == "Invoice INV-2026-105"


def test_logical_text_keeps_accented_latin():
    # Latin-1 accents are legitimate, not a glyph-id dump.
    assert conversion._logical_text("Café naïve") == "Café naïve"


def test_visual_to_logical_keeps_numbers_and_dates():
    # Numbers and dates are stored left-to-right even inside visual-order text,
    # so flipping the line must leave them intact.
    assert conversion._visual_to_logical("2,927.74") == "2,927.74"
    assert conversion._visual_to_logical("16-11-2026") == "16-11-2026"
    assert conversion._visual_to_logical("4,004") == "4,004"


def test_visual_to_logical_mirrors_brackets():
    assert conversion._visual_to_logical(")") == "("
    assert conversion._visual_to_logical("(") == ")"


def test_cell_value_reads_thousands_and_day_first_dates():
    assert conversion._cell_value("1,200.00") == 1200.0
    assert conversion._cell_value("6,266.56") == pytest.approx(6266.56)
    assert conversion._cell_value("16-11-2026") == datetime.date(2026, 11, 16)


# --------------------------------------------------------------------------
# Broken encoding: the real defect
# --------------------------------------------------------------------------

def test_fixture_reproduces_the_garbage_text(tmp_path):
    """The fixture really has no ToUnicode map before the repair runs."""
    source = build_broken_encoding_pdf(tmp_path / "broken.pdf", "كشف حساب بنكي")
    with fitz.open(source) as doc:
        extracted = doc[0].get_text()
    assert "كشف" not in extracted
    suspicious = [char for char in extracted
                  if 0x0100 <= ord(char) <= 0x024F or 0x0590 <= ord(char) <= 0x05FF]
    assert suspicious, "fixture should expose glyph ids as non-Arabic code points"


def test_embedded_font_is_repaired_to_arabic(tmp_path):
    source = build_broken_encoding_pdf(tmp_path / "broken.pdf", "كشف حساب بنكي")
    target = tmp_path / "out.docx"
    export_pdf(source.read_bytes(), str(target), [1], "docx_editable")
    assert target.exists()
    text = "".join(paragraph.text for paragraph in Document(target).paragraphs)
    assert "كشف حساب بنكي" in text
    assert not any(0x0100 <= ord(char) <= 0x024F for char in text), text


def test_missing_font_is_refused_not_corrupted(tmp_path):
    source = build_broken_encoding_pdf(tmp_path / "broken.pdf", "كشف حساب بنكي",
                                       embed_font=False)
    target = tmp_path / "out.docx"
    with pytest.raises(ValueError, match="damaged|Unicode"):
        export_pdf(source.read_bytes(), str(target), [1], "docx_editable")
    assert not target.exists()


# --------------------------------------------------------------------------
# Borderless table detection
# --------------------------------------------------------------------------

def test_borderless_shaded_table_is_detected_with_real_values(tmp_path):
    source = build_borderless_table_pdf(tmp_path / "table.pdf")
    target = tmp_path / "out.xlsx"
    export_pdf(source.read_bytes(), str(target), [1], "xlsx")

    sheet = load_workbook(target).worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    assert sheet.sheet_view.rightToLeft is False
    assert rows[0] == ("Date", "Description", "Amount")
    assert len(rows) == 5, rows

    dates = [row[0] for row in rows[1:]]
    assert dates == [datetime.datetime(2026, 11, day) for day in (1, 2, 3, 4)]
    amounts = [row[2] for row in rows[1:]]
    assert amounts == [1200, 85.5, 3000, 120.75]


def test_borderless_table_csv_keeps_rows_once(tmp_path):
    source = build_borderless_table_pdf(tmp_path / "table.pdf")
    target = tmp_path / "out.csv"
    export_pdf(source.read_bytes(), str(target), [1], "csv")
    lines = target.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0] == "Date,Description,Amount"
    assert len(lines) == 5, lines
    assert "Opening balance" in lines[1]
