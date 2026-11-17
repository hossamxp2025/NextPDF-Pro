#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comments written as real PDF annotations: added, read back from the saved
file, found under a point, edited and removed.
"""

import os
import sys
import tempfile
import unittest

import pymupdf as fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.engine import annotations as engine
from src.models.document import PDFDocument

SAMPLE = "annotation sample text"


def make_pdf(path):
    doc = fitz.open()
    doc.new_page(width=400, height=300).insert_text((50, 100), SAMPLE)
    doc.save(path)
    doc.close()
    return path


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.doc = fitz.open()
        self.page = self.doc.new_page(width=400, height=300)
        self.page.insert_text((50, 100), SAMPLE)

    def tearDown(self):
        self.doc.close()

    def test_a_highlight_is_written_as_a_highlight(self):
        item = engine.add_highlight(self.page, [(48, 88, 200, 104)])
        self.assertEqual(item["kind"], "highlight")
        self.assertEqual(item["subtype"], "Highlight")
        self.assertEqual(len(engine.list_annotations(self.page)), 1)

    def test_a_highlight_sits_over_the_text_it_was_given(self):
        rect = self.page.search_for(SAMPLE)[0]
        item = engine.add_highlight(self.page, [rect])
        self.assertTrue(fitz.Rect(item["rect"]).intersects(rect))

    def test_a_highlight_needs_an_area(self):
        with self.assertRaises(ValueError):
            engine.add_highlight(self.page, [])

    def test_a_note_keeps_its_text_and_author(self):
        item = engine.add_note(self.page, (60, 60), "check this", author="Hossam")
        self.assertEqual(item["content"], "check this")
        self.assertEqual(item["author"], "Hossam")
        self.assertEqual(item["kind"], "note")

    def test_a_note_keeps_arabic_exactly_as_written(self):
        text = "راجع هذا السطر"
        engine.add_note(self.page, (60, 60), text)
        self.assertEqual(engine.list_annotations(self.page)[0]["content"], text)

    def test_an_empty_note_is_refused(self):
        with self.assertRaises(ValueError):
            engine.add_note(self.page, (60, 60), "   ")

    def test_free_text_is_written_on_the_page(self):
        item = engine.add_free_text(self.page, (40, 150, 300, 190), "Approved")
        self.assertEqual(item["kind"], "free_text")
        self.assertEqual(item["content"], "Approved")

    def test_arabic_free_text_is_refused_with_a_reason(self):
        # The standard PDF fonts cannot shape Arabic; writing it anyway
        # produces broken letters, so the kind is refused instead.
        with self.assertRaises(ValueError) as caught:
            engine.add_free_text(self.page, (40, 150, 300, 190), "مرحبا")
        self.assertIn("Arabic", str(caught.exception))
        self.assertEqual(engine.list_annotations(self.page), [])

    def test_every_shape_kind_is_written(self):
        for kind in engine.SHAPE_KINDS:
            item = engine.add_shape(self.page, (20, 20, 120, 80), kind=kind)
            self.assertEqual(item["kind"], kind)
        self.assertEqual(len(engine.list_annotations(self.page)), 3)

    def test_an_unknown_shape_is_refused(self):
        with self.assertRaises(ValueError):
            engine.add_shape(self.page, (20, 20, 120, 80), kind="triangle")

    def test_a_shape_with_no_area_is_refused(self):
        with self.assertRaises(ValueError):
            engine.add_shape(self.page, (20, 20, 20, 20), kind="rectangle")

    def test_a_point_finds_the_annotation_under_it(self):
        engine.add_shape(self.page, (20, 20, 120, 80))
        found = engine.find_at(self.page, 60, 50)
        self.assertIsNotNone(found)
        self.assertEqual(found["kind"], "rectangle")

    def test_a_point_on_nothing_finds_nothing(self):
        engine.add_shape(self.page, (20, 20, 120, 80))
        self.assertIsNone(engine.find_at(self.page, 300, 260))

    def test_the_topmost_annotation_is_the_one_found(self):
        engine.add_shape(self.page, (20, 20, 200, 200), kind="rectangle")
        engine.add_shape(self.page, (30, 30, 180, 180), kind="ellipse")
        self.assertEqual(engine.find_at(self.page, 100, 100)["kind"], "ellipse")

    def test_an_annotation_can_be_removed(self):
        item = engine.add_shape(self.page, (20, 20, 120, 80))
        self.assertTrue(engine.delete_annotation(self.page, item["xref"]))
        self.assertEqual(engine.list_annotations(self.page), [])

    def test_removing_an_unknown_annotation_reports_false(self):
        self.assertFalse(engine.delete_annotation(self.page, 99999))

    def test_the_text_of_a_note_can_be_changed(self):
        item = engine.add_note(self.page, (60, 60), "first")
        self.assertTrue(engine.set_content(self.page, item["xref"], "second"))
        self.assertEqual(engine.list_annotations(self.page)[0]["content"], "second")

    def test_arabic_cannot_be_put_into_a_free_text_by_editing_it(self):
        item = engine.add_free_text(self.page, (40, 150, 300, 190), "ok")
        with self.assertRaises(ValueError):
            engine.set_content(self.page, item["xref"], "نص عربي")

    def test_the_colour_is_recorded(self):
        item = engine.add_shape(self.page, (20, 20, 120, 80),
                                color=(1.0, 0.0, 0.0))
        self.assertEqual(item["color"][:3], (1.0, 0.0, 0.0))


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_annots_")
        self.path = make_pdf(os.path.join(self.tmp, "doc.pdf"))
        self.document = PDFDocument()
        self.assertTrue(self.document.load(self.path))

    def tearDown(self):
        self.document.close()

    def test_a_new_document_has_no_comments(self):
        self.assertEqual(self.document.page_annotations(1), [])

    def test_adding_a_comment_marks_the_document_as_modified(self):
        self.document.is_modified = False
        self.document.add_comment(1, "note", point=(60, 60), content="hi")
        self.assertTrue(self.document.is_modified)

    def test_a_refused_comment_leaves_a_reason_and_changes_nothing(self):
        self.document.is_modified = False
        self.assertIsNone(self.document.add_comment(
            1, "free_text", rect=(20, 20, 200, 60), text="مرحبا"))
        self.assertIn("Arabic", self.document.last_error)
        self.assertFalse(self.document.is_modified)
        self.assertEqual(self.document.page_annotations(1), [])

    def test_an_unknown_kind_is_refused(self):
        self.assertIsNone(self.document.add_comment(1, "scribble"))
        self.assertIn("Unknown", self.document.last_error)

    def test_a_comment_on_a_page_that_does_not_exist_is_refused(self):
        self.assertIsNone(self.document.add_comment(99, "note",
                                                    point=(10, 10), content="x"))

    def test_the_comments_survive_a_save_and_reopen(self):
        self.document.add_comment(1, "note", point=(60, 60), content="review me")
        self.document.add_comment(1, "highlight", rects=[(48, 88, 200, 104)])
        target = os.path.join(self.tmp, "with-comments.pdf")
        self.assertTrue(self.document.save(target))
        reopened = PDFDocument()
        try:
            self.assertTrue(reopened.load(target))
            kinds = sorted(item["kind"] for item in reopened.page_annotations(1))
            self.assertEqual(kinds, ["highlight", "note"])
            notes = [i for i in reopened.page_annotations(1) if i["kind"] == "note"]
            self.assertEqual(notes[0]["content"], "review me")
        finally:
            reopened.close()

    def test_another_reader_sees_them_as_ordinary_annotations(self):
        self.document.add_comment(1, "rectangle", rect=(20, 20, 120, 80))
        target = os.path.join(self.tmp, "shape.pdf")
        self.document.save(target)
        with fitz.open(target) as raw:
            subtypes = [annot.type[1] for annot in raw[0].annots()]
        self.assertEqual(subtypes, ["Square"])

    def test_all_annotations_covers_every_page(self):
        doc = fitz.open()
        doc.new_page()
        doc.new_page()
        two = os.path.join(self.tmp, "two.pdf")
        doc.save(two)
        doc.close()
        document = PDFDocument()
        document.load(two)
        try:
            document.add_comment(1, "note", point=(20, 20), content="one")
            document.add_comment(2, "note", point=(20, 20), content="two")
            self.assertEqual(len(document.all_annotations()), 2)
            self.assertEqual({i["page"] for i in document.all_annotations()},
                             {1, 2})
        finally:
            document.close()

    def test_a_comment_can_be_removed_from_the_document(self):
        item = self.document.add_comment(1, "note", point=(60, 60), content="x")
        self.assertTrue(self.document.delete_comment(1, item["xref"]))
        self.assertEqual(self.document.page_annotations(1), [])

    def test_removing_a_comment_that_is_gone_reports_the_reason(self):
        self.assertFalse(self.document.delete_comment(1, 123456))
        self.assertTrue(self.document.last_error)

    def test_the_text_of_a_comment_can_be_changed_and_saved(self):
        item = self.document.add_comment(1, "note", point=(60, 60), content="old")
        self.assertTrue(self.document.set_comment_text(1, item["xref"], "new"))
        target = os.path.join(self.tmp, "edited.pdf")
        self.document.save(target)
        reopened = PDFDocument()
        try:
            reopened.load(target)
            self.assertEqual(reopened.page_annotations(1)[0]["content"], "new")
        finally:
            reopened.close()

    def test_the_page_text_is_not_touched_by_a_comment(self):
        self.document.add_comment(1, "highlight", rects=[(48, 88, 200, 104)])
        target = os.path.join(self.tmp, "kept.pdf")
        self.document.save(target)
        with fitz.open(target) as raw:
            self.assertIn(SAMPLE, raw[0].get_text())


if __name__ == "__main__":
    unittest.main()
