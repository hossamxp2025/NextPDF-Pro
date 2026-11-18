#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The visible stamp in the Protect and Sign tab: arming the mode, dragging the
area, choosing an image or typing a name, undoing it, and the wording that
keeps a stamp from being mistaken for a digital signature.
"""

import os
import sys
import tempfile
import unittest

import pymupdf as fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (QApplication, QFileDialog, QInputDialog,
                               QMessageBox, QPushButton)

from src.i18n import get_translator
from src.ui.main_window import MainWindow
from src.ui.pdf_viewer import MODE_SELECT, MODE_STAMP

ARABIC_NAME = "حسام الفاخرة"


def app():
    return QApplication.instance() or QApplication([])


def plain_pdf(path):
    doc = fitz.open()
    doc.new_page(width=400, height=300).insert_text((40, 40), "Agreement")
    doc.save(path)
    doc.close()
    return path


def signature_png(path):
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 60), False)
    pixmap.set_rect(pixmap.irect, (255, 255, 255))
    pixmap.set_rect(fitz.IRect(10, 24, 110, 36), (10, 10, 10))
    pixmap.save(path)
    return path


class StampTabTests(unittest.TestCase):
    def setUp(self):
        app()
        get_translator().set_language("en")
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_stamp_ui_")
        self.path = plain_pdf(os.path.join(self.tmp, "doc.pdf"))
        self.image = signature_png(os.path.join(self.tmp, "sign.png"))
        self.window = MainWindow()
        self.assertTrue(self.window._open_file_path(self.path))
        self.viewer = self.window.current_context.viewer
        self.document = self.window.current_document
        self.messages = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: self.messages.append(a[2] if len(a) > 2 else ""))
        QMessageBox.warning = staticmethod(
            lambda *a, **k: self.messages.append(a[2] if len(a) > 2 else ""))
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)
        QFileDialog.getOpenFileName = staticmethod(
            lambda *a, **k: (self.image, ""))

    def tearDown(self):
        for context in list(getattr(self.window, "_contexts", [])):
            context.document.is_modified = False
        self.window.close()
        self.window.deleteLater()

    def drag(self, rect):
        polygon = self.viewer.canvas.pdf_to_widget(rect)
        start, end = polygon.at(0), polygon.at(2)

        def event(kind, point):
            return QMouseEvent(kind, QPointF(point), Qt.LeftButton,
                               Qt.LeftButton, Qt.NoModifier)

        self.viewer._on_canvas_press(event(QEvent.MouseButtonPress, start))
        self.viewer._on_canvas_move(event(QEvent.MouseMove, end))
        self.viewer._on_canvas_release(event(QEvent.MouseButtonRelease, end))

    def images_on_page(self):
        return len(self.document.get_page(1).get_images())

    # --------------------------------------------------------------- buttons
    def test_the_stamp_buttons_are_in_the_protect_tab_and_work(self):
        for name in ("tool_Stamp_an_image", "tool_Stamp_a_name",
                     "tool_What_a_stamp_is_not"):
            button = self.window.ribbon.findChild(QPushButton, name)
            self.assertIsNotNone(button, f"{name} is missing from the ribbon")
            self.assertTrue(button.isEnabled(), f"{name} is disabled")

    def test_the_explanation_says_it_is_not_a_digital_signature(self):
        self.window._explain_stamp()
        self.assertTrue(self.messages)
        self.assertIn("not a digital signature", self.messages[0])

    def test_the_explanation_is_translated_into_arabic(self):
        get_translator().set_language("ar")
        try:
            arabic = get_translator().tr(MainWindow.STAMP_NOT_A_SIGNATURE)
            self.assertNotEqual(arabic, MainWindow.STAMP_NOT_A_SIGNATURE)
            self.assertIn("ليس توقيعًا رقميًا", arabic)
        finally:
            get_translator().set_language("en")

    # ------------------------------------------------------------------ mode
    def test_the_image_button_arms_the_viewer_and_the_second_press_leaves(self):
        self.window._stamp_mode("image")
        self.assertEqual(self.viewer.current_mode(), MODE_STAMP)
        self.assertEqual(self.viewer.stamp_kind, "image")
        self.window._stamp_mode("image")
        self.assertEqual(self.viewer.current_mode(), MODE_SELECT)

    def test_switching_from_an_image_stamp_to_a_name_keeps_the_mode(self):
        self.window._stamp_mode("image")
        self.window._stamp_mode("text")
        self.assertEqual(self.viewer.current_mode(), MODE_STAMP)
        self.assertEqual(self.viewer.stamp_kind, "text")

    def test_the_status_line_tells_the_user_to_drag(self):
        self.window._stamp_mode("image")
        self.assertIn("drag", self.window.status_label.text().lower())

    def test_clearing_the_modes_clears_the_stamp_kind(self):
        self.window._stamp_mode("text")
        self.viewer.clear_modes()
        self.assertIsNone(self.viewer.stamp_kind)
        self.assertEqual(self.viewer.current_mode(), MODE_SELECT)

    # ---------------------------------------------------------- image stamps
    def test_dragging_an_area_places_the_chosen_image(self):
        self.window._stamp_mode("image")
        self.drag(fitz.Rect(60, 100, 260, 200))
        self.assertEqual(self.images_on_page(), 1)
        self.assertEqual(self.viewer.current_mode(), MODE_SELECT)

    def test_cancelling_the_file_dialog_places_nothing(self):
        QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
        self.window._stamp_mode("image")
        self.drag(fitz.Rect(60, 100, 260, 200))
        self.assertEqual(self.images_on_page(), 0)

    def test_an_image_stamp_undoes(self):
        self.window._stamp_mode("image")
        self.drag(fitz.Rect(60, 100, 260, 200))
        self.assertEqual(self.images_on_page(), 1)
        self.window._undo()
        self.assertEqual(self.images_on_page(), 0)

    def test_answering_yes_drops_the_white_background(self):
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
        page = self.document.get_page(1)
        page.draw_rect(page.rect, color=None, fill=(1, 0, 0))
        self.window._stamp_mode("image")
        self.drag(fitz.Rect(40, 40, 360, 200))
        target = os.path.join(self.tmp, "stamped.pdf")
        self.assertTrue(self.document.save(target, incremental=False))
        with fitz.open(target) as doc:
            pixmap = doc[0].get_pixmap(dpi=72)
            self.assertEqual(pixmap.pixel(200, 60), (255, 0, 0))

    def test_a_broken_image_is_reported_and_nothing_is_placed(self):
        broken = os.path.join(self.tmp, "broken.png")
        with open(broken, "wb") as handle:
            handle.write(b"not an image")
        QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (broken, ""))
        self.window._stamp_mode("image")
        self.drag(fitz.Rect(60, 100, 260, 200))
        self.assertEqual(self.images_on_page(), 0)
        self.assertTrue(self.messages)
        self.assertIn("image", self.messages[0].lower())

    # ----------------------------------------------------------- text stamps
    def test_dragging_an_area_and_typing_a_name_draws_real_text(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: (ARABIC_NAME, True))
        self.window._stamp_mode("text")
        self.drag(fitz.Rect(60, 120, 340, 180))
        self.assertIn(ARABIC_NAME, self.document.get_page(1).get_text())

    def test_cancelling_the_name_places_nothing(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
        self.window._stamp_mode("text")
        self.drag(fitz.Rect(60, 120, 340, 180))
        self.assertNotIn(ARABIC_NAME, self.document.get_page(1).get_text())

    def test_a_blank_name_places_nothing(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: ("   ", True))
        self.window._stamp_mode("text")
        self.drag(fitz.Rect(60, 120, 340, 180))
        self.assertEqual(self.document.get_page(1).get_text().strip(),
                         "Agreement")

    def test_a_name_stamp_undoes(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: (ARABIC_NAME, True))
        self.window._stamp_mode("text")
        self.drag(fitz.Rect(60, 120, 340, 180))
        self.window._undo()
        self.assertNotIn(ARABIC_NAME, self.document.get_page(1).get_text())

    def test_the_stamp_reaches_the_saved_file(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: (ARABIC_NAME, True))
        self.window._stamp_mode("text")
        self.drag(fitz.Rect(60, 120, 340, 180))
        target = os.path.join(self.tmp, "named.pdf")
        self.assertTrue(self.document.save(target, incremental=False))
        with fitz.open(target) as doc:
            self.assertIn(ARABIC_NAME, doc[0].get_text())

    def test_a_stray_click_stamps_nothing(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: (ARABIC_NAME, True))
        self.window._stamp_mode("text")
        self.drag(fitz.Rect(60, 120, 61, 121))
        self.assertNotIn(ARABIC_NAME, self.document.get_page(1).get_text())

    def test_the_window_title_shows_the_document_changed(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: (ARABIC_NAME, True))
        self.window._stamp_mode("text")
        self.drag(fitz.Rect(60, 120, 340, 180))
        self.assertTrue(self.document.is_modified)
        self.assertIn("*", self.window.windowTitle())


if __name__ == "__main__":
    unittest.main()
