#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Markdown export: headings from the page's own sizes, real pipe tables, and
emphasis.  Every check reads the written file.
"""

import os
import sys

import pymupdf as fitz
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.engine.conversion import (
    export_pdf, _heading_level, _markdown_escape, _markdown_inline,
    _markdown_table,
)


def write(tmp_path, build, pages=(1,)):
    with fitz.open() as doc:
        build(doc)
        data = doc.tobytes()
    target = tmp_path / "out.md"
    export_pdf(data, str(target), list(pages), "md")
    return target.read_text(encoding="utf-8")


def headed_page(doc):
    page = doc.new_page(width=400, height=400)
    page.insert_text((40, 60), "Quarterly report", fontsize=24)
    page.insert_text((40, 110), "Revenue", fontsize=16)
    page.insert_text((40, 150), "The quarter closed above the plan.", fontsize=11)
    page.insert_text((40, 180), "Every region contributed to the result.", fontsize=11)


# ------------------------------------------------------------------ helpers
@pytest.mark.parametrize("size,level", [(24, 1), (16, 2), (13, 3), (11, 0)])
def test_a_line_becomes_a_heading_only_when_it_stands_above_the_body(size, level):
    assert _heading_level(size, 11, False) == level


def test_a_page_with_one_size_has_no_headings():
    assert _heading_level(11, 11, False) == 0


def test_a_pipe_character_cannot_break_the_table():
    assert _markdown_escape("a|b") == "a\\|b"


def test_bold_and_italic_keep_their_emphasis():
    assert _markdown_inline([{"text": "Total", "bold": True, "italic": False,
                              "size": 11}]) == "**Total**"
    assert _markdown_inline([{"text": "note", "bold": False, "italic": True,
                              "size": 11}]) == "*note*"


def test_a_table_gets_a_header_separator():
    lines = _markdown_table([["Item", "Amount"], ["Pen", "5"]], rtl=False)
    assert lines[1] == "| --- | --- |"
    assert lines[0] == "| Item | Amount |"


def test_a_ragged_table_is_padded_not_truncated():
    lines = _markdown_table([["a", "b", "c"], ["x"]], rtl=False)
    assert lines[-1] == "| x |  |  |"


# ------------------------------------------------------------- written file
def test_the_biggest_line_on_the_page_becomes_the_top_heading(tmp_path):
    text = write(tmp_path, headed_page)
    assert "# Quarterly report" in text
    assert "## Revenue" in text


def test_body_text_is_written_without_a_heading_marker(tmp_path):
    text = write(tmp_path, headed_page)
    for line in text.splitlines():
        if "closed above the plan" in line:
            assert not line.startswith("#")
            break
    else:
        raise AssertionError("the body line is missing from the export")


def test_a_page_of_one_size_produces_no_headings(tmp_path):
    def build(doc):
        page = doc.new_page(width=300, height=200)
        page.insert_text((40, 60), "first line", fontsize=11)
        page.insert_text((40, 90), "second line", fontsize=11)

    text = write(tmp_path, build)
    assert "first line" in text and "second line" in text
    assert "#" not in text


def test_a_ruled_table_becomes_a_pipe_table(tmp_path):
    def build(doc):
        page = doc.new_page(width=400, height=300)
        for x in (40, 180, 320):
            page.draw_line((x, 40), (x, 120))
        for y in (40, 80, 120):
            page.draw_line((40, y), (320, y))
        for r, values in enumerate((("Item", "Amount"), ("INV-2026-105", "15750"))):
            for c, value in enumerate(values):
                page.insert_text((50 + c * 140, 65 + r * 40), value, fontsize=12)

    text = write(tmp_path, build)
    assert "| Item | Amount |" in text
    assert "| --- | --- |" in text
    assert "| INV-2026-105 | 15750 |" in text


def test_table_text_is_not_repeated_as_a_paragraph(tmp_path):
    def build(doc):
        page = doc.new_page(width=400, height=300)
        for x in (40, 180, 320):
            page.draw_line((x, 40), (x, 120))
        for y in (40, 80, 120):
            page.draw_line((40, y), (320, y))
        for r, values in enumerate((("Item", "Amount"), ("Pen", "5"))):
            for c, value in enumerate(values):
                page.insert_text((50 + c * 140, 65 + r * 40), value, fontsize=12)

    text = write(tmp_path, build)
    assert text.count("INV") == 0
    assert text.count("Pen") == 1


def test_several_pages_are_separated(tmp_path):
    def build(doc):
        for number in (1, 2):
            doc.new_page(width=300, height=200).insert_text(
                (40, 60), f"page {number} body", fontsize=11)

    text = write(tmp_path, build, pages=(1, 2))
    assert "page 1 body" in text and "page 2 body" in text
    assert "---" in text


def test_arabic_is_written_in_logical_order(tmp_path):
    from src.engine.ocr_engine import OCREngine

    def build(doc):
        page = doc.new_page(width=400, height=200)
        OCREngine._insert_word_layer(
            page, [{"text": "تقرير الربع", "left": 40, "top": 40,
                    "width": 200, "height": 24}], 1, 1)

    text = write(tmp_path, build)
    assert "تقرير الربع" in text


def test_a_page_without_text_is_refused_rather_than_written_empty(tmp_path):
    with fitz.open() as doc:
        doc.new_page()
        data = doc.tobytes()
    target = tmp_path / "empty.md"
    with pytest.raises(ValueError):
        export_pdf(data, str(target), [1], "md")
    assert not target.exists()
