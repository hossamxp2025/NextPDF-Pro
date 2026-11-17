#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The Review tab: drawing a comment in the viewer, selecting one, editing it,
removing it, listing them, and undoing every one of those.
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
from PySide6.QtWidgets import (QApplication, QInputDialog, QMessageBox,
                               QPushButton)

from src.ui.main_window import MainWindow
from src.ui.pdf_viewer import MODE_COMMENT, MODE_SELECT

SAMPLE = "comment sample line"


def app():
    return QApplication.instance() or QApplication([])


def make_pdf(path):
    doc = fitz.open()
    doc.new_page(width=400, height=300).insert_text((50, 100), SAMPLE)
    doc.save(path)
    doc.close()
    return path


class ReviewTabTests(unittest.TestCase):
    def setUp(self):
        app()
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_comments_ui_")
        self.path = make_pdf(os.path.join(self.tmp, "doc.pdf"))
        self.window = MainWindow()
        self.assertTrue(self.window._open_file_path(self.path))
        self.viewer = self.window.current_context.viewer
        self.document = self.window.current_document
        self.messages = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: self.messages.append(a[2] if len(a) > 2 else ""))
        QMessageBox.warning = staticmethod(
            lambda *a, **k: self.messages.append(a[2] if len(a) > 2 else ""))

    def tearDown(self):
        for context in list(getattr(self.window, "_contexts", [])):
            context.document.is_modified = False
        self.window.close()
        self.window.deleteLater()

    # ------------------------------------------------------------- helpers
    def answer(self, text):
        QInputDialog.getMultiLineText = staticmethod(
            lambda *a, **k: (text, True) if text is not None else ("", False))

    def text_rect(self):
        return self.document.doc[0].search_for(SAMPLE)[0]

    def drag(self, rect):
        """Drag across a PDF rectangle in the viewer."""
        polygon = self.viewer.canvas.pdf_to_widget(rect)
        start, end = polygon.at(0), polygon.at(2)

        def event(kind, point):
            return QMouseEvent(kind, QPointF(point), Qt.LeftButton,
                               Qt.LeftButton, Qt.NoModifier)

        self.viewer._on_canvas_press(event(QEvent.MouseButtonPress, start))
        self.viewer._on_canvas_move(event(QEvent.MouseMove, end))
        self.viewer._on_canvas_release(event(QEvent.MouseButtonRelease, end))

    def click(self, x, y):
        polygon = self.viewer.canvas.pdf_to_widget((x, y, x + 1, y + 1))
        point = polygon.at(0)
        self.viewer._on_canvas_press(
            QMouseEvent(QEvent.MouseButtonPress, QPointF(point), Qt.LeftButton,
                        Qt.LeftButton, Qt.NoModifier))

    # --------------------------------------------------------------- tests
    def test_the_review_tab_has_working_buttons(self):
        names = ("tool_Highlight", "tool_Sticky_note", "tool_Text_on_the_page",
                 "tool_Rectangle", "tool_Ellipse", "tool_Line",
                 "tool_Edit_the_comment", "tool_Delete_the_comment",
                 "tool_List_the_comments")
        for name in names:
            button = self.window.ribbon.findChild(QPushButton, name)
            self.assertIsNotNone(button, f"{name} is missing from the ribbon")
            self.assertTrue(button.isEnabled(), f"{name} is disabled")

    def test_the_button_arms_the_viewer_and_a_second_press_disarms_it(self):
        self.window._comment_mode("rectangle")
        self.assertEqual(self.viewer.current_mode(), MODE_COMMENT)
        self.assertEqual(self.viewer.comment_kind, "rectangle")
        self.window._comment_mode("rectangle")
        self.assertEqual(self.viewer.current_mode(), MODE_SELECT)

    def test_dragging_in_rectangle_mode_writes_a_rectangle(self):
        self.window._comment_mode("rectangle")
        self.drag(fitz.Rect(40, 40, 200, 120))
        comments = self.document.page_annotations(1)
        self.assertEqual([c["kind"] for c in comments], ["rectangle"])

    def test_highlighting_follows_the_text_under_the_drag(self):
        self.window._comment_mode("highlight")
        rect = self.text_rect()
        self.drag(rect)
        comments = self.document.page_annotations(1)
        self.assertEqual(len(comments), 1)
        self.assertTrue(fitz.Rect(comments[0]["rect"]).intersects(rect))

    def test_a_note_asks_for_its_text_and_keeps_it(self):
        self.answer("look at this")
        self.window._comment_mode("note")
        self.click(60, 60)
        comments = self.document.page_annotations(1)
        self.assertEqual(comments[0]["content"], "look at this")

    def test_a_note_keeps_arabic(self):
        self.answer("راجع هذا السطر")
        self.window._comment_mode("note")
        self.click(60, 60)
        self.assertEqual(self.document.page_annotations(1)[0]["content"],
                         "راجع هذا السطر")

    def test_cancelling_the_text_writes_nothing(self):
        self.answer(None)
        self.window._comment_mode("note")
        self.click(60, 60)
        self.assertEqual(self.document.page_annotations(1), [])

    def test_arabic_in_text_on_the_page_is_refused_with_a_reason(self):
        self.answer("نص عربي")
        self.window._comment_mode("free_text")
        self.drag(fitz.Rect(40, 150, 300, 200))
        self.assertEqual(self.document.page_annotations(1), [])
        self.assertTrue(self.messages, "the user must be told why")

    def test_drawing_a_comment_leaves_the_mode(self):
        self.window._comment_mode("ellipse")
        self.drag(fitz.Rect(40, 40, 200, 120))
        self.assertEqual(self.viewer.current_mode(), MODE_SELECT)

    def test_clicking_a_comment_selects_it(self):
        self.window._comment_mode("rectangle")
        self.drag(fitz.Rect(40, 40, 200, 120))
        self.click(100, 80)
        self.assertIsNotNone(self.viewer.selected_annotation)
        self.assertEqual(self.viewer.selected_annotation["kind"], "rectangle")

    def test_clicking_empty_space_selects_nothing(self):
        self.window._comment_mode("rectangle")
        self.drag(fitz.Rect(40, 40, 120, 90))
        self.click(350, 260)
        self.assertIsNone(self.viewer.selected_annotation)

    def test_deleting_without_a_selection_says_so(self):
        self.window._delete_selected_comment()
        self.assertTrue(self.messages)

    def test_a_selected_comment_can_be_deleted(self):
        self.window._comment_mode("rectangle")
        self.drag(fitz.Rect(40, 40, 200, 120))
        self.click(100, 80)
        self.window._delete_selected_comment()
        self.assertEqual(self.document.page_annotations(1), [])

    def test_a_selected_comment_can_be_edited(self):
        self.answer("first")
        self.window._comment_mode("note")
        self.click(60, 60)
        placed = self.document.page_annotations(1)[0]
        rect = fitz.Rect(placed["rect"])
        self.click((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
        self.assertIsNotNone(self.viewer.selected_annotation)
        self.answer("second")
        self.window._edit_selected_comment()
        self.assertEqual(self.document.page_annotations(1)[0]["content"],
                         "second")

    def test_the_list_shows_every_comment(self):
        self.answer("note text")
        self.window._comment_mode("note")
        self.click(60, 60)
        self.window._comment_mode("rectangle")
        self.drag(fitz.Rect(40, 150, 200, 220))
        self.messages.clear()
        self.window._list_comments()
        self.assertTrue(self.messages)
        self.assertIn("note text", self.messages[0])

    def test_the_list_of_an_empty_document_says_there_are_none(self):
        self.window._list_comments()
        self.assertTrue(self.messages)

    # ------------------------------------------------------------- undoing
    def test_adding_a_comment_can_be_undone_and_redone(self):
        self.window._comment_mode("rectangle")
        self.drag(fitz.Rect(40, 40, 200, 120))
        self.assertEqual(len(self.document.page_annotations(1)), 1)
        self.window._undo()
        self.assertEqual(self.document.page_annotations(1), [])
        self.window._redo()
        self.assertEqual(len(self.document.page_annotations(1)), 1)

    def test_deleting_a_comment_can_be_undone(self):
        self.window._comment_mode("rectangle")
        self.drag(fitz.Rect(40, 40, 200, 120))
        self.click(100, 80)
        self.window._delete_selected_comment()
        self.window._undo()
        self.assertEqual(len(self.document.page_annotations(1)), 1)

    def test_a_comment_marks_the_document_as_modified(self):
        self.document.is_modified = False
        self.window._comment_mode("rectangle")
        self.drag(fitz.Rect(40, 40, 200, 120))
        self.assertTrue(self.document.is_modified)

    def test_comments_are_written_into_the_saved_file(self):
        self.answer("saved note")
        self.window._comment_mode("note")
        self.click(60, 60)
        target = os.path.join(self.tmp, "saved.pdf")
        self.assertTrue(self.document.save(target))
        with fitz.open(target) as raw:
            contents = [a.info.get("content") for a in raw[0].annots()]
        self.assertIn("saved note", contents)

    def test_the_page_text_is_untouched_by_a_comment(self):
        self.window._comment_mode("highlight")
        self.drag(self.text_rect())
        self.assertIn(SAMPLE, self.document.doc[0].get_text())


if __name__ == "__main__":
    unittest.main()
