#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for user-facing redaction.

Redaction has to remove, not cover.  Every case therefore saves the file and
reads the text back out of it, which is what someone trying to recover the
content would do.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

from models.document import PDFDocument
from src.engine.redaction import find_text_rects, redact_page

SECRET = "ACCOUNT 123456789"
KEPT = "ordinary visible line"


def make_pdf(path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), SECRET)
    page.insert_text((72, 200), KEPT)
    doc.save(path)
    doc.close()
    return path


class RedactionTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_redact_")
        self.src = make_pdf(os.path.join(self.tmp, "src.pdf"))

    def saved_text(self, doc, name="out.pdf"):
        out = os.path.join(self.tmp, name)
        self.assertTrue(doc.save(out), doc.last_error)
        raw = fitz.open(out)
        text = "\n".join(page.get_text() for page in raw)
        raw.close()
        return text


class FindTests(RedactionTestCase):
    def test_a_phrase_is_located(self):
        raw = fitz.open(self.src)
        rects = find_text_rects(raw[0], SECRET)
        self.assertEqual(len(rects), 1)
        raw.close()

    def test_a_phrase_that_is_not_there_finds_nothing(self):
        raw = fitz.open(self.src)
        self.assertEqual(find_text_rects(raw[0], "not in this file"), [])
        self.assertEqual(find_text_rects(raw[0], ""), [])
        raw.close()


class RedactAreasTests(RedactionTestCase):
    def test_text_under_the_area_is_gone_from_the_saved_file(self):
        doc = PDFDocument()
        self.assertTrue(doc.load(self.src))
        rect = find_text_rects(doc.doc[0], SECRET)[0]
        self.assertEqual(doc.redact_areas({1: [rect]}), 1)
        text = self.saved_text(doc)
        self.assertNotIn("123456789", text)
        self.assertIn(KEPT, text)
        doc.close()

    def test_redaction_marks_the_document_modified(self):
        doc = PDFDocument()
        doc.load(self.src)
        rect = find_text_rects(doc.doc[0], SECRET)[0]
        doc.is_modified = False
        doc.redact_areas({1: [rect]})
        self.assertTrue(doc.is_modified)
        doc.close()

    def test_a_page_number_out_of_range_is_ignored(self):
        doc = PDFDocument()
        doc.load(self.src)
        self.assertEqual(doc.redact_areas({9: [(0, 0, 10, 10)]}), 0)
        self.assertFalse(doc.is_modified)
        doc.close()

    def test_an_empty_rectangle_is_not_applied(self):
        doc = PDFDocument()
        doc.load(self.src)
        self.assertEqual(doc.redact_areas({1: [(50, 50, 50, 50)]}), 0)
        doc.close()

    def test_redacting_without_a_document_reports_an_error(self):
        doc = PDFDocument()
        self.assertEqual(doc.redact_areas({1: [(0, 0, 10, 10)]}), 0)
        self.assertEqual(doc.last_error, "No document open")


class RedactTextTests(RedactionTestCase):
    def test_every_occurrence_is_removed(self):
        doc = fitz.open()
        for _ in range(2):
            page = doc.new_page()
            page.insert_text((72, 100), SECRET)
            page.insert_text((72, 200), KEPT)
        path = os.path.join(self.tmp, "two.pdf")
        doc.save(path)
        doc.close()

        model = PDFDocument()
        self.assertTrue(model.load(path))
        self.assertEqual(model.redact_text(SECRET), 2)
        text = self.saved_text(model, "two_out.pdf")
        self.assertNotIn("123456789", text)
        self.assertEqual(text.count(KEPT), 2)
        model.close()

    def test_only_the_named_pages_are_touched(self):
        doc = fitz.open()
        for _ in range(2):
            doc.new_page().insert_text((72, 100), SECRET)
        path = os.path.join(self.tmp, "pages.pdf")
        doc.save(path)
        doc.close()

        model = PDFDocument()
        model.load(path)
        self.assertEqual(model.redact_text(SECRET, pages=[2]), 1)
        text = self.saved_text(model, "pages_out.pdf")
        self.assertEqual(text.count("123456789"), 1)
        model.close()

    def test_an_empty_search_does_nothing(self):
        model = PDFDocument()
        model.load(self.src)
        self.assertEqual(model.redact_text(""), 0)
        self.assertFalse(model.is_modified)
        model.close()


class RedactPageHelperTests(RedactionTestCase):
    def test_the_helper_reports_how_many_areas_it_applied(self):
        raw = fitz.open(self.src)
        rects = find_text_rects(raw[0], SECRET)
        self.assertEqual(redact_page(raw[0], rects), 1)
        self.assertNotIn("123456789", raw[0].get_text())
        raw.close()

    def test_no_areas_means_no_change(self):
        raw = fitz.open(self.src)
        self.assertEqual(redact_page(raw[0], []), 0)
        self.assertIn("123456789", raw[0].get_text())
        raw.close()


if __name__ == "__main__":
    unittest.main()
