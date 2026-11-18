#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visible stamps: an image or typed text drawn onto the page as page content.

Every check reads the saved file.  What a stamp is *not* is tested too: it
leaves no annotation and no form field behind, because a visible stamp must
not be mistaken for a signature anywhere in the file.
"""

import os
import sys
import tempfile
import unittest

import pymupdf as fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.engine import stamps
from src.models.document import PDFDocument

ARABIC_NAME = "حسام الفاخرة"


def plain_pdf(path, width=400, height=300):
    doc = fitz.open()
    doc.new_page(width=width, height=height).insert_text((40, 40), "Agreement")
    doc.save(path)
    doc.close()
    return path


def signature_png(path, stroke=(10, 10, 10)):
    """A dark stroke on a white background, like a scanned signature."""
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 60), False)
    pixmap.set_rect(pixmap.irect, (255, 255, 255))
    pixmap.set_rect(fitz.IRect(10, 24, 110, 36), stroke)
    pixmap.save(path)
    return path


class ImageStampTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nextpdf_stamp_")
        self.source = plain_pdf(os.path.join(self.dir, "source.pdf"))
        self.image = signature_png(os.path.join(self.dir, "sign.png"))
        self.target = os.path.join(self.dir, "out.pdf")

    def test_image_is_drawn_as_page_content_and_survives_saving(self):
        document = PDFDocument()
        self.assertTrue(document.load(self.source))
        stamp = document.add_image_stamp(1, (60, 100, 260, 200), self.image)
        self.assertIsNotNone(stamp)
        self.assertEqual(stamp["kind"], "image")
        self.assertEqual(stamp["page"], 1)
        self.assertTrue(document.save(self.target, incremental=False))
        with fitz.open(self.target) as doc:
            page = doc[0]
            self.assertEqual(len(page.get_images()), 1)
            xref = page.get_images()[0][0]
            placed = page.get_image_rects(xref)[0]
            self.assertAlmostEqual(placed.x0, stamp["rect"][0], places=1)
            self.assertAlmostEqual(placed.y1, stamp["rect"][3], places=1)

    def test_a_stamp_is_not_an_annotation_and_not_a_field(self):
        document = PDFDocument()
        document.load(self.source)
        document.add_image_stamp(1, (60, 100, 260, 200), self.image)
        document.save(self.target, incremental=False)
        with fitz.open(self.target) as doc:
            self.assertEqual(list(doc[0].annots()), [])
            self.assertFalse(doc.is_form_pdf)

    def test_proportions_are_kept_and_the_drawn_area_is_reported(self):
        document = PDFDocument()
        document.load(self.source)
        # The area is square; the image is 2:1, so only half the height is used.
        stamp = document.add_image_stamp(1, (50, 50, 250, 250), self.image)
        drawn = fitz.Rect(stamp["rect"])
        self.assertAlmostEqual(drawn.width / drawn.height, 2.0, places=2)
        self.assertEqual(stamp["requested_rect"], (50.0, 50.0, 250.0, 250.0))
        self.assertTrue(fitz.Rect(stamp["requested_rect"]).contains(drawn))

    def test_stretching_is_possible_when_asked_for(self):
        document = PDFDocument()
        document.load(self.source)
        stamp = document.add_image_stamp(1, (50, 50, 250, 250), self.image,
                                         keep_ratio=False)
        self.assertEqual(stamp["rect"], (50.0, 50.0, 250.0, 250.0))

    def test_white_background_can_be_dropped_without_touching_the_stroke(self):
        document = PDFDocument()
        document.load(self.source)
        page = document.get_page(1)
        page.draw_rect(page.rect, color=None, fill=(1, 0, 0))
        stamp = document.add_image_stamp(1, (40, 40, 360, 200), self.image,
                                        drop_white_background=True)
        self.assertTrue(stamp["transparent"])
        document.save(self.target, incremental=False)
        with fitz.open(self.target) as doc:
            pixmap = doc[0].get_pixmap(dpi=72)
            drawn = fitz.Rect(stamp["rect"])
            middle_x = int((drawn.x0 + drawn.x1) / 2)
            # Above the stroke the red page must still show through.
            above = pixmap.pixel(middle_x, int(drawn.y0 + drawn.height * 0.1))
            on_stroke = pixmap.pixel(middle_x, int((drawn.y0 + drawn.y1) / 2))
            self.assertEqual(above, (255, 0, 0))
            self.assertLess(max(on_stroke), 80)

    def test_the_white_background_is_kept_when_not_asked_for(self):
        document = PDFDocument()
        document.load(self.source)
        page = document.get_page(1)
        page.draw_rect(page.rect, color=None, fill=(1, 0, 0))
        stamp = document.add_image_stamp(1, (40, 40, 360, 200), self.image)
        self.assertFalse(stamp["transparent"])
        document.save(self.target, incremental=False)
        with fitz.open(self.target) as doc:
            pixmap = doc[0].get_pixmap(dpi=72)
            drawn = fitz.Rect(stamp["rect"])
            above = pixmap.pixel(int((drawn.x0 + drawn.x1) / 2),
                                 int(drawn.y0 + drawn.height * 0.1))
            self.assertEqual(above, (255, 255, 255))

    def test_a_missing_image_is_refused_with_the_reason(self):
        document = PDFDocument()
        document.load(self.source)
        missing = os.path.join(self.dir, "nothing.png")
        self.assertIsNone(document.add_image_stamp(1, (50, 50, 200, 120), missing))
        self.assertEqual(document.last_error, "The image file was not found")

    def test_a_file_that_is_not_an_image_is_refused_with_the_reason(self):
        document = PDFDocument()
        document.load(self.source)
        broken = os.path.join(self.dir, "broken.png")
        with open(broken, "wb") as handle:
            handle.write(b"this is not an image")
        self.assertIsNone(document.add_image_stamp(1, (50, 50, 200, 120), broken))
        self.assertEqual(document.last_error, "The image could not be read")

    def test_a_stray_click_is_refused_rather_than_stamped(self):
        document = PDFDocument()
        document.load(self.source)
        self.assertIsNone(document.add_image_stamp(1, (50, 50, 53, 53), self.image))
        self.assertEqual(document.last_error, "The stamp area is too small")

    def test_image_bytes_are_accepted_as_well_as_a_path(self):
        document = PDFDocument()
        document.load(self.source)
        with open(self.image, "rb") as handle:
            data = handle.read()
        self.assertIsNotNone(document.add_image_stamp(1, (50, 50, 250, 150), data))

    def test_no_such_page_is_refused(self):
        document = PDFDocument()
        document.load(self.source)
        self.assertIsNone(document.add_image_stamp(9, (50, 50, 250, 150), self.image))
        self.assertEqual(document.last_error, "No such page")

    def test_a_stamp_marks_the_document_as_modified(self):
        document = PDFDocument()
        document.load(self.source)
        document.is_modified = False
        document.add_image_stamp(1, (50, 50, 250, 150), self.image)
        self.assertTrue(document.is_modified)

    def test_the_page_underneath_is_not_removed(self):
        document = PDFDocument()
        document.load(self.source)
        document.add_image_stamp(1, (60, 150, 260, 250), self.image)
        document.save(self.target, incremental=False)
        with fitz.open(self.target) as doc:
            self.assertIn("Agreement", doc[0].get_text())


class TextStampTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nextpdf_stamp_text_")
        self.source = plain_pdf(os.path.join(self.dir, "source.pdf"))
        self.target = os.path.join(self.dir, "out.pdf")

    def test_arabic_is_drawn_as_real_searchable_text(self):
        document = PDFDocument()
        document.load(self.source)
        stamp = document.add_text_stamp(1, (60, 120, 340, 170), ARABIC_NAME)
        self.assertIsNotNone(stamp)
        self.assertTrue(document.save(self.target, incremental=False))
        with fitz.open(self.target) as doc:
            page = doc[0]
            self.assertIn(ARABIC_NAME, page.get_text())
            self.assertTrue(page.search_for("الفاخرة"))

    def test_the_arabic_font_is_embedded_so_any_reader_shapes_it(self):
        document = PDFDocument()
        document.load(self.source)
        document.add_text_stamp(1, (60, 120, 340, 170), ARABIC_NAME)
        document.save(self.target, incremental=False)
        with fitz.open(self.target) as doc:
            names = [font[3] for font in doc[0].get_fonts()]
            self.assertTrue(any("Arabic" in name for name in names), names)

    def test_latin_text_works_too(self):
        document = PDFDocument()
        document.load(self.source)
        document.add_text_stamp(1, (60, 120, 340, 170), "Hossam Alfakhera")
        document.save(self.target, incremental=False)
        with fitz.open(self.target) as doc:
            self.assertIn("Hossam Alfakhera", doc[0].get_text())

    def test_the_text_leaves_no_annotation_and_no_field(self):
        document = PDFDocument()
        document.load(self.source)
        document.add_text_stamp(1, (60, 120, 340, 170), ARABIC_NAME)
        document.save(self.target, incremental=False)
        with fitz.open(self.target) as doc:
            self.assertEqual(list(doc[0].annots()), [])
            self.assertFalse(doc.is_form_pdf)

    def test_empty_text_is_refused_with_the_reason(self):
        document = PDFDocument()
        document.load(self.source)
        self.assertIsNone(document.add_text_stamp(1, (60, 120, 340, 170), "   "))
        self.assertEqual(document.last_error, "The stamp needs its text")

    def test_a_stray_click_is_refused(self):
        document = PDFDocument()
        document.load(self.source)
        self.assertIsNone(document.add_text_stamp(1, (60, 120, 62, 122), ARABIC_NAME))
        self.assertEqual(document.last_error, "The stamp area is too small")

    def test_the_reported_rectangle_is_inside_the_area_that_was_asked_for(self):
        document = PDFDocument()
        document.load(self.source)
        stamp = document.add_text_stamp(1, (60, 120, 340, 180), ARABIC_NAME)
        drawn = fitz.Rect(stamp["rect"])
        self.assertTrue(fitz.Rect(60, 120, 340, 180).contains(drawn), drawn)

    def test_the_size_can_be_chosen(self):
        document = PDFDocument()
        document.load(self.source)
        small = document.add_text_stamp(1, (60, 60, 340, 110), ARABIC_NAME, size=10)
        large = document.add_text_stamp(1, (60, 160, 340, 230), ARABIC_NAME, size=28)
        self.assertLess(fitz.Rect(small["rect"]).height,
                        fitz.Rect(large["rect"]).height)


class EngineBoundaryTests(unittest.TestCase):
    """The module's own promises, checked directly."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nextpdf_stamp_engine_")
        self.image = signature_png(os.path.join(self.dir, "sign.png"))

    def test_image_suffixes_are_recognised(self):
        self.assertTrue(stamps.is_image_file("c:/a/b/sign.PNG"))
        self.assertTrue(stamps.is_image_file("sign.jpeg"))
        self.assertFalse(stamps.is_image_file("sign.pdf"))
        self.assertFalse(stamps.is_image_file(""))
        self.assertFalse(stamps.is_image_file(None))

    def test_the_fitted_rectangle_is_centred_in_the_area(self):
        box = fitz.Rect(0, 0, 200, 200)
        fitted = stamps._fitted(box, 100, 50)
        self.assertEqual(tuple(fitted), (0.0, 50.0, 200.0, 150.0))

    def test_dropping_the_white_background_only_changes_alpha(self):
        pixmap = fitz.Pixmap(self.image)
        result = stamps._without_white_background(pixmap)
        self.assertTrue(result.alpha)
        self.assertEqual((result.width, result.height),
                         (pixmap.width, pixmap.height))
        # the stroke pixel keeps its colour
        self.assertEqual(result.pixel(60, 30)[:3], pixmap.pixel(60, 30)[:3])

    def test_the_module_states_that_a_stamp_is_not_a_signature(self):
        self.assertIn("not a digital signature", stamps.__doc__)

    def test_the_known_limitations_say_a_stamp_is_not_a_signature(self):
        path = os.path.join(os.path.dirname(__file__), "..",
                            "KNOWN_LIMITATIONS.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("ليس توقيعًا رقميًا", text)

    def test_a_rotated_or_reversed_area_is_normalised(self):
        doc = fitz.open()
        page = doc.new_page(width=300, height=300)
        stamp = stamps.add_image_stamp(page, (250, 200, 50, 60), self.image,
                                       keep_ratio=False)
        self.assertEqual(stamp["rect"], (50.0, 60.0, 250.0, 200.0))
        doc.close()


if __name__ == "__main__":
    unittest.main()
