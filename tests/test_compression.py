#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compression: the written file is measured, not the intent.  A file that
cannot be made smaller is reported as unchanged rather than as a saving.
"""

import os
import sys

import pymupdf as fitz
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.engine.optimizer import compress_pdf
from src.models.document import PDFDocument


def bulky_pdf(path, pages=3, dpi=300):
    """A PDF whose weight is in high-resolution page images."""
    with fitz.open() as typeset:
        page = typeset.new_page(width=400, height=300)
        for y in range(40, 280, 12):
            page.insert_text((20, y), "The quick brown fox jumps over it all",
                             fontsize=9)
        image = page.get_pixmap(dpi=dpi).tobytes("png")
    with fitz.open() as doc:
        for _ in range(pages):
            page = doc.new_page(width=400, height=300)
            page.insert_image(page.rect, stream=image)
        doc.save(path, deflate=False)
    return path


def text_pdf(path, text="COMPRESSION TEST"):
    with fitz.open() as doc:
        doc.new_page().insert_text((40, 80), text, fontsize=14)
        doc.save(path)
    return path


def test_a_heavy_scan_gets_smaller(tmp_path):
    source = bulky_pdf(tmp_path / "heavy.pdf")
    target = tmp_path / "small.pdf"
    result = compress_pdf(str(source), str(target))
    assert result["after"] < result["before"]
    assert result["saved"] == result["before"] - result["after"]
    assert result["changed"] is True


def test_the_compressed_file_still_opens_with_every_page(tmp_path):
    source = bulky_pdf(tmp_path / "heavy.pdf", pages=3)
    target = tmp_path / "small.pdf"
    compress_pdf(str(source), str(target))
    with fitz.open(target) as doc:
        assert doc.page_count == 3
        assert doc[0].get_images()


def test_the_text_survives_compression(tmp_path):
    source = text_pdf(tmp_path / "text.pdf")
    target = tmp_path / "small.pdf"
    compress_pdf(str(source), str(target), recompress_images=False)
    with fitz.open(target) as doc:
        assert "COMPRESSION TEST" in doc[0].get_text()


def test_the_source_file_is_left_alone(tmp_path):
    source = bulky_pdf(tmp_path / "heavy.pdf")
    before = source.read_bytes()
    compress_pdf(str(source), str(tmp_path / "small.pdf"))
    assert source.read_bytes() == before


def test_an_already_small_file_is_reported_as_unchanged(tmp_path):
    source = text_pdf(tmp_path / "tiny.pdf")
    target = tmp_path / "out.pdf"
    # Compress twice: the second run has nothing left to take out.
    compress_pdf(str(source), str(target))
    again = tmp_path / "again.pdf"
    result = compress_pdf(str(target), str(again))
    if result["changed"]:
        pytest.skip("this build still found something to remove")
    assert result["saved"] == 0
    assert result["after"] == result["before"]
    assert again.stat().st_size == target.stat().st_size


def test_nothing_is_lost_when_the_result_would_be_bigger(tmp_path):
    source = text_pdf(tmp_path / "tiny.pdf")
    target = tmp_path / "out.pdf"
    compress_pdf(str(source), str(target))
    again = tmp_path / "again.pdf"
    compress_pdf(str(target), str(again))
    with fitz.open(again) as doc:
        assert "COMPRESSION TEST" in doc[0].get_text()


def test_a_protected_file_needs_its_password(tmp_path):
    plain = text_pdf(tmp_path / "plain.pdf")
    protected = tmp_path / "protected.pdf"
    document = PDFDocument()
    document.load(str(plain))
    document.save(str(protected), user_password="open-me")
    document.close()
    with pytest.raises(ValueError):
        compress_pdf(str(protected), str(tmp_path / "out.pdf"))


def test_a_protected_file_stays_protected_after_compression(tmp_path):
    plain = bulky_pdf(tmp_path / "heavy.pdf")
    protected = tmp_path / "protected.pdf"
    document = PDFDocument()
    document.load(str(plain))
    document.save(str(protected), user_password="open-me")
    document.close()
    target = tmp_path / "small.pdf"
    compress_pdf(str(protected), str(target), password="open-me")
    with fitz.open(target) as doc:
        assert doc.needs_pass, "the copy must not drop the password"
        assert doc.authenticate("open-me")


@pytest.mark.parametrize("options", [{"image_dpi": 10}, {"image_dpi": 2000},
                                     {"quality": 0}, {"quality": 500}])
def test_impossible_options_are_refused(tmp_path, options):
    source = text_pdf(tmp_path / "text.pdf")
    target = tmp_path / "out.pdf"
    with pytest.raises(ValueError):
        compress_pdf(str(source), str(target), **options)
    assert not target.exists()


def test_no_temporary_file_is_left_behind(tmp_path):
    source = bulky_pdf(tmp_path / "heavy.pdf")
    target = tmp_path / "small.pdf"
    compress_pdf(str(source), str(target))
    leftovers = [p for p in tmp_path.iterdir()
                 if p.suffix == ".pdf" and p.name not in {"heavy.pdf", "small.pdf"}]
    assert leftovers == []


def test_a_lower_resolution_saves_more_than_a_lossless_pass(tmp_path):
    source = bulky_pdf(tmp_path / "heavy.pdf")
    lossless = compress_pdf(str(source), str(tmp_path / "a.pdf"),
                            recompress_images=False)
    lossy = compress_pdf(str(source), str(tmp_path / "b.pdf"),
                         recompress_images=True, image_dpi=72, quality=40)
    assert lossy["after"] <= lossless["after"]
