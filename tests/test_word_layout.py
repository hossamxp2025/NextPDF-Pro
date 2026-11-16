# -*- coding: utf-8 -*-
"""Editable Word export must rebuild structure, not just dump lines.

Before 1.5.0 every PDF line became one standalone paragraph: a statement table
arrived as a few hundred disconnected paragraphs, labels detached from their
values, and every run carried the generator's internal font name, which Word
cannot resolve.  These tests pin the structure that replaced it.
"""
import io

import pymupdf as fitz
import pytest
from docx import Document
from docx.oxml.ns import qn

from src.config import FONTS_DIR
from src.engine.conversion import export_pdf, _embedded_family
from tests.pdf_fixtures import (ARABIC_TABLE_COLUMNS, ARABIC_TABLE_ROWS,
                               build_arabic_borderless_table_pdf,
                               build_borderless_table_pdf,
                               build_broken_encoding_pdf, visual_order)

ARABIC_FONT = str(FONTS_DIR / "NotoSansArabic-Regular.ttf")


def _export(source, target, pages=(1,)):
    export_pdf(source.read_bytes(), str(target), list(pages), "docx_editable")
    return Document(target)


def _cell_fill(cell):
    properties = cell._tc.find(qn("w:tcPr"))
    if properties is None:
        return None
    shading = properties.find(qn("w:shd"))
    return shading.get(qn("w:fill")) if shading is not None else None


def _paragraph_texts(document):
    return [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]


def _body_kinds(document):
    """Flow of the document body: 'table', 'picture' or 'text', in order."""
    kinds = []
    for element in document.element.body.iterchildren():
        tag = element.tag.split("}")[-1]
        if tag == "tbl":
            kinds.append("table")
        elif tag == "p":
            if element.findall(".//" + qn("a:blip")):
                kinds.append("picture")
            elif "".join(element.itertext()).strip():
                kinds.append("text")
    return kinds


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def test_borderless_table_becomes_one_word_table(tmp_path):
    source = build_borderless_table_pdf(tmp_path / "table.pdf")
    document = _export(source, tmp_path / "out.docx")

    assert len(document.tables) == 1
    table = document.tables[0]
    assert (len(table.rows), len(table.columns)) == (5, 3)
    assert [cell.text for cell in table.rows[0].cells] == ["Date", "Description", "Amount"]
    assert [cell.text for cell in table.rows[1].cells] == [
        "2026-11-01", "Opening balance", "1,200.00"]


def test_table_values_are_not_also_loose_paragraphs(tmp_path):
    """A line the table already accounts for must not be emitted twice."""
    source = build_borderless_table_pdf(tmp_path / "table.pdf")
    document = _export(source, tmp_path / "out.docx")

    joined = "\n".join(_paragraph_texts(document))
    for value in ("Opening balance", "3,000.00", "Description"):
        assert value not in joined, joined


def test_row_shading_is_carried_from_the_page(tmp_path):
    source = build_borderless_table_pdf(tmp_path / "table.pdf")
    table = _export(source, tmp_path / "out.docx").tables[0]

    header = {_cell_fill(cell) for cell in table.rows[0].cells}
    assert header == {"EBEBEB"}, header
    assert {_cell_fill(cell) for cell in table.rows[1].cells} == {None}


def test_column_widths_follow_the_page_columns(tmp_path):
    """The narrow date column must not come out as wide as the description."""
    source = build_borderless_table_pdf(tmp_path / "table.pdf")
    table = _export(source, tmp_path / "out.docx").tables[0]

    widths = [cell.width.pt for cell in table.rows[1].cells]
    assert all(width > 0 for width in widths), widths
    assert widths[1] > widths[0], widths


def test_ruled_grid_table_is_rebuilt_too(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page(width=420, height=260)
        xs, ys = (30, 160, 290, 400), (30, 70, 110, 150)
        for x in xs:
            page.draw_line((x, ys[0]), (x, ys[-1]))
        for y in ys:
            page.draw_line((xs[0], y), (xs[-1], y))
        rows = (("Item", "Date", "Amount"), ("INV-1", "2026-11-14", "15750"),
                ("INV-2", "2026-11-15", "2026"))
        for r, values in enumerate(rows):
            for c, text in enumerate(values):
                page.insert_text((xs[c] + 8, ys[r] + 26), text, fontsize=11)
        doc.save(tmp_path / "grid.pdf")
    document = _export(tmp_path / "grid.pdf", tmp_path / "out.docx")

    assert len(document.tables) == 1
    assert [cell.text for cell in document.tables[0].rows[0].cells] == [
        "Item", "Date", "Amount"]


# ---------------------------------------------------------------------------
# Right-to-left structure
# ---------------------------------------------------------------------------

def test_arabic_table_is_bidi_and_starts_at_the_rightmost_column(tmp_path):
    source = build_arabic_borderless_table_pdf(tmp_path / "arabic.pdf")
    document = _export(source, tmp_path / "out.docx")

    assert len(document.tables) == 1
    table = document.tables[0]
    assert table._tbl.tblPr.find(qn("w:bidiVisual")) is not None
    # Drawn left to right, the last page column reads first.
    assert [cell.text for cell in table.rows[0].cells] == list(
        reversed(ARABIC_TABLE_COLUMNS))
    assert [cell.text for cell in table.rows[1].cells] == list(
        reversed(ARABIC_TABLE_ROWS[0]))


def test_latin_table_is_not_marked_bidi(tmp_path):
    source = build_borderless_table_pdf(tmp_path / "table.pdf")
    table = _export(source, tmp_path / "out.docx").tables[0]
    assert table._tbl.tblPr.find(qn("w:bidiVisual")) is None


def _side_by_side(path, left_text, right_text, font=None):
    with fitz.open() as doc:
        page = doc.new_page(width=595, height=300)
        writer = fitz.TextWriter(page.rect)
        face = fitz.Font(fontfile=font) if font else fitz.Font("helv")
        writer.append((40, 100), visual_order(left_text), font=face, fontsize=14)
        writer.append((400, 100), visual_order(right_text), font=face, fontsize=14)
        writer.write_text(page)
        doc.save(path)
    return path


def test_arabic_side_by_side_boxes_read_right_to_left(tmp_path):
    source = _side_by_side(tmp_path / "cards.pdf", "يسار", "يمين", ARABIC_FONT)
    texts = _paragraph_texts(_export(source, tmp_path / "out.docx"))
    assert texts.index("يمين") < texts.index("يسار"), texts


def test_latin_side_by_side_boxes_keep_left_to_right(tmp_path):
    source = _side_by_side(tmp_path / "cards.pdf", "LEFT BOX", "RIGHT BOX")
    texts = _paragraph_texts(_export(source, tmp_path / "out.docx"))
    assert texts.index("LEFT BOX") < texts.index("RIGHT BOX"), texts


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

def test_embedded_family_replaces_the_generator_internal_font_name(tmp_path):
    """``/BaseFont /BrokenFace`` is meaningless to Word; the real family is not."""
    source = build_broken_encoding_pdf(tmp_path / "broken.pdf", "كشف حساب بنكي")
    document = _export(source, tmp_path / "out.docx")

    names = {run.font.name for paragraph in document.paragraphs
             for run in paragraph.runs if run.text.strip()}
    assert names == {"Noto Sans Arabic"}, names
    assert "BrokenFace" not in names


def test_embedded_family_reads_the_font_name_table():
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((40, 60), "Hi", fontname="F0", fontfile=ARABIC_FONT)
        data = doc.tobytes()
    with fitz.open(stream=data, filetype="pdf") as doc:
        xref = doc[0].get_fonts(full=True)[0][0]
        assert _embedded_family(doc, xref) == "Noto Sans Arabic"


def test_missing_embedded_font_falls_back_without_raising():
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((40, 60), "Hi", fontname="helv")
        data = doc.tobytes()
    with fitz.open(stream=data, filetype="pdf") as doc:
        xref = doc[0].get_fonts(full=True)[0][0]
        assert _embedded_family(doc, xref) is None


# ---------------------------------------------------------------------------
# Images and page geometry
# ---------------------------------------------------------------------------

def test_image_is_placed_in_page_order_not_appended_at_the_end(tmp_path):
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 60, 40))
    pixmap.set_rect(pixmap.irect, (200, 40, 40))
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=400)
        page.insert_text((40, 60), "ABOVE THE IMAGE", fontsize=12)
        page.insert_image(fitz.Rect(40, 120, 200, 220), pixmap=pixmap)
        page.insert_text((40, 300), "BELOW THE IMAGE", fontsize=12)
        doc.save(tmp_path / "mixed.pdf")
    document = _export(tmp_path / "mixed.pdf", tmp_path / "out.docx")

    assert _body_kinds(document) == ["text", "picture", "text"]
    assert len(document.inline_shapes) == 1


def test_landscape_page_keeps_its_orientation_and_size(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page(width=842, height=595)
        page.insert_text((40, 60), "WIDE PAGE", fontsize=12)
        doc.save(tmp_path / "wide.pdf")
    section = _export(tmp_path / "wide.pdf", tmp_path / "out.docx").sections[0]

    assert round(section.page_width.pt) == 842
    assert round(section.page_height.pt) == 595
    assert section.page_width > section.page_height


def test_paragraphs_do_not_add_word_default_spacing(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page(width=400, height=200)
        page.insert_text((40, 60), "LINE ONE", fontsize=12)
        page.insert_text((40, 90), "LINE TWO", fontsize=12)
        doc.save(tmp_path / "lines.pdf")
    document = _export(tmp_path / "lines.pdf", tmp_path / "out.docx")

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            assert paragraph.paragraph_format.space_before.pt == 0
            assert paragraph.paragraph_format.space_after.pt <= 2


def _jc(paragraph):
    properties = paragraph._p.find(qn("w:pPr"))
    if properties is None:
        return None
    node = properties.find(qn("w:jc"))
    return node.get(qn("w:val")) if node is not None else None


def _paragraph_fill(paragraph):
    properties = paragraph._p.find(qn("w:pPr"))
    if properties is None:
        return None
    node = properties.find(qn("w:shd"))
    return node.get(qn("w:fill")) if node is not None else None


def test_arabic_paragraph_alignment_is_mirrored_for_word_bidi(tmp_path):
    """Word mirrors w:jc under w:bidi: 'left' is what pins text to the right."""
    with fitz.open() as doc:
        page = doc.new_page(width=595, height=200)
        writer = fitz.TextWriter(page.rect)
        writer.append((420, 60), visual_order("عنوان"),
                      font=fitz.Font(fontfile=ARABIC_FONT), fontsize=16)
        writer.write_text(page)
        doc.save(tmp_path / "title.pdf")
    document = _export(tmp_path / "title.pdf", tmp_path / "out.docx")

    paragraph = next(p for p in document.paragraphs if p.text.strip())
    assert paragraph._p.find(qn("w:pPr")).find(qn("w:bidi")) is not None
    assert _jc(paragraph) == "left"


def test_line_keeps_the_page_edge_it_was_anchored_to(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page(width=595, height=200)
        page.insert_text((40, 60), "FAR LEFT", fontsize=12)
        page.insert_text((470, 60), "FAR RIGHT", fontsize=12)
        doc.save(tmp_path / "edges.pdf")
    document = _export(tmp_path / "edges.pdf", tmp_path / "out.docx")

    by_text = {p.text.strip(): p for p in document.paragraphs if p.text.strip()}
    assert _jc(by_text["FAR LEFT"]) in (None, "left")
    assert _jc(by_text["FAR RIGHT"]) == "right"


def test_white_text_on_a_dark_band_keeps_its_band(tmp_path):
    """Without the band the title would be white on white, and read as missing."""
    with fitz.open() as doc:
        page = doc.new_page(width=595, height=200)
        page.draw_rect(fitz.Rect(0, 0, 595, 60), color=None,
                       fill=(0.04, 0.09, 0.28), width=0)
        page.insert_text((40, 38), "WHITE TITLE", fontsize=18, color=(1, 1, 1))
        doc.save(tmp_path / "banner.pdf")
    document = _export(tmp_path / "banner.pdf", tmp_path / "out.docx")

    paragraph = next(p for p in document.paragraphs if "WHITE TITLE" in p.text)
    assert _paragraph_fill(paragraph) == "0A1747"


def test_full_page_background_is_not_mistaken_for_a_band(tmp_path):
    with fitz.open() as doc:
        page = doc.new_page(width=595, height=200)
        page.draw_rect(page.rect, color=None, fill=(0.9, 0.9, 0.9), width=0)
        page.insert_text((40, 100), "ON A TINTED PAGE", fontsize=12)
        doc.save(tmp_path / "tinted.pdf")
    document = _export(tmp_path / "tinted.pdf", tmp_path / "out.docx")

    paragraph = next(p for p in document.paragraphs if p.text.strip())
    assert _paragraph_fill(paragraph) is None


def test_narrow_column_is_widened_to_fit_its_own_text(tmp_path):
    """A boundary narrower than its text would wrap every date onto two lines."""
    from src.engine.conversion import _column_widths

    rects = [[fitz.Rect(0, 0, 39, 12)], [fitz.Rect(0, 12, 39, 24)]]
    bounds = [[(0.0, 39.0)], [(0.0, 39.0)]]
    assert _column_widths(rects, 1, bounds)[0] > 39.0


def test_columns_are_fitted_to_the_usable_page_width(tmp_path):
    from src.engine.conversion import _column_widths

    rects = [[fitz.Rect(0, 0, 300, 12), fitz.Rect(300, 0, 600, 12)]]
    bounds = [[(0.0, 20.0), (300.0, 320.0)]]
    widths = _column_widths(rects, 2, bounds, usable_width=400.0)
    assert round(sum(widths)) == 400


def test_damaged_page_without_a_font_is_still_refused(tmp_path):
    """Table rebuilding must not turn a refusal into a corrupted document."""
    source = build_broken_encoding_pdf(tmp_path / "broken.pdf", "كشف حساب بنكي",
                                       embed_font=False)
    target = tmp_path / "out.docx"
    with pytest.raises(ValueError, match="damaged|Unicode"):
        export_pdf(source.read_bytes(), str(target), [1], "docx_editable")
    assert not target.exists()
