#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the protection user interface: the dialog's validation, the
password prompt shown for an encrypted file, and the ribbon handlers.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox

from src.models.document import PDFDocument, permissions_from_flags, FULL_PERMISSIONS
from src.ui.protect_dialog import ProtectDialog
from src.ui.main_window import MainWindow

SAMPLE_TEXT = "interface sample text"


def app():
    return QApplication.instance() or QApplication([])


def make_pdf(path):
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), SAMPLE_TEXT)
    doc.save(path)
    doc.close()
    return path


class ProtectDialogTests(unittest.TestCase):
    def setUp(self):
        app()
        self.dialog = ProtectDialog()

    def tearDown(self):
        self.dialog.deleteLater()

    def test_nothing_chosen_is_refused(self):
        self.assertIsNotNone(self.dialog.validation_error())

    def test_mismatched_open_passwords_are_refused(self):
        self.dialog.user_password.setText("one")
        self.dialog.user_password_confirm.setText("two")
        self.assertIsNotNone(self.dialog.validation_error())

    def test_an_open_password_alone_is_accepted(self):
        self.dialog.user_password.setText("open")
        self.dialog.user_password_confirm.setText("open")
        self.assertIsNone(self.dialog.validation_error())

    def test_restrictions_without_an_owner_password_are_refused(self):
        self.dialog.user_password.setText("open")
        self.dialog.user_password_confirm.setText("open")
        self.dialog.permission_boxes["print"].setChecked(False)
        self.assertIsNotNone(self.dialog.validation_error())

    def test_identical_open_and_owner_passwords_are_refused(self):
        self.dialog.user_password.setText("same")
        self.dialog.user_password_confirm.setText("same")
        self.dialog.owner_password.setText("same")
        self.assertIsNotNone(self.dialog.validation_error())

    def test_removing_the_information_alone_is_accepted(self):
        self.dialog.strip_metadata.setChecked(True)
        self.assertIsNone(self.dialog.validation_error())

    def test_the_arguments_match_the_choices(self):
        self.dialog.user_password.setText("open")
        self.dialog.user_password_confirm.setText("open")
        self.dialog.owner_password.setText("own")
        self.dialog.permission_boxes["copy"].setChecked(False)
        args = self.dialog.save_arguments()
        self.assertEqual(args["user_password"], "open")
        self.assertEqual(args["owner_password"], "own")
        self.assertFalse(args["permissions"] & fitz.PDF_PERM_COPY)
        self.assertFalse(args["strip_metadata"])

    def test_untouched_permissions_stay_full(self):
        self.dialog.user_password.setText("open")
        self.dialog.user_password_confirm.setText("open")
        self.assertEqual(self.dialog.save_arguments()["permissions"],
                         FULL_PERMISSIONS)


class PasswordPromptTests(unittest.TestCase):
    def setUp(self):
        app()
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_protect_ui_")
        plain = make_pdf(os.path.join(self.tmp, "plain.pdf"))
        doc = PDFDocument()
        doc.load(plain)
        self.encrypted = os.path.join(self.tmp, "enc.pdf")
        doc.save(self.encrypted, user_password="open-me")
        doc.close()
        self.window = MainWindow()
        self.asked = []

    def tearDown(self):
        for context in list(getattr(self.window, "_contexts", [])):
            context.document.is_modified = False
        self.window.close()
        self.window.deleteLater()

    def patch_prompt(self, answers):
        answers = list(answers)

        def fake(parent, title, label, echo=None, *args, **kwargs):
            self.asked.append(label)
            if not answers:
                return "", False
            value = answers.pop(0)
            if value is None:
                return "", False
            return value, True

        QInputDialog.getText = staticmethod(fake)

    def test_the_right_password_opens_the_file(self):
        self.patch_prompt(["open-me"])
        self.assertTrue(self.window._open_file_path(self.encrypted))
        self.assertEqual(len(self.asked), 1)
        self.assertIn(SAMPLE_TEXT, self.window.current_document.doc[0].get_text())

    def test_cancelling_leaves_the_file_closed_without_an_error(self):
        self.patch_prompt([None])
        self.assertFalse(self.window._open_file_path(self.encrypted))

    def test_a_wrong_password_is_asked_again_then_given_up(self):
        warned = []
        QMessageBox.warning = staticmethod(
            lambda *a, **k: warned.append(a[2] if len(a) > 2 else ""))
        self.patch_prompt(["no", "still-no", "wrong-again"])
        self.assertFalse(self.window._open_file_path(self.encrypted))
        self.assertEqual(len(self.asked), 3)
        self.assertNotEqual(self.asked[0], self.asked[1])
        self.assertTrue(warned)

    def test_a_plain_file_is_never_asked_for_a_password(self):
        self.patch_prompt([])
        plain = make_pdf(os.path.join(self.tmp, "other.pdf"))
        self.assertTrue(self.window._open_file_path(plain))
        self.assertEqual(self.asked, [])


class RibbonHandlerTests(unittest.TestCase):
    def setUp(self):
        app()
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_protect_ribbon_")
        self.plain = make_pdf(os.path.join(self.tmp, "plain.pdf"))
        self.window = MainWindow()
        self.window._open_file_path(self.plain)

    def tearDown(self):
        for context in list(getattr(self.window, "_contexts", [])):
            context.document.is_modified = False
        self.window.close()
        self.window.deleteLater()

    def test_removing_protection_from_an_open_file_says_so(self):
        shown = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: shown.append(a[2] if len(a) > 2 else ""))
        self.window._remove_protection()
        self.assertTrue(shown)

    def test_redacting_a_phrase_removes_it(self):
        QInputDialog.getText = staticmethod(lambda *a, **k: (SAMPLE_TEXT, True))
        self.window._redact_text()
        self.assertNotIn(SAMPLE_TEXT,
                         self.window.current_document.doc[0].get_text())

    def test_redacting_nothing_reports_no_match(self):
        shown = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: shown.append(a[2] if len(a) > 2 else ""))
        QInputDialog.getText = staticmethod(lambda *a, **k: ("absent phrase", True))
        self.window._redact_text()
        self.assertTrue(shown)

    def test_the_protect_tab_has_working_buttons(self):
        from PySide6.QtWidgets import QPushButton
        names = ("tool_Protect_with_a_password", "tool_Remove_protection",
                 "tool_Remove_document_information", "tool_Redact_text")
        for name in names:
            button = self.window.ribbon.findChild(QPushButton, name)
            self.assertIsNotNone(button, f"{name} is missing from the ribbon")
            self.assertTrue(button.isEnabled(),
                            f"{name} is disabled with a document open")


class AreaRedactionTests(unittest.TestCase):
    """Marking rectangles in the viewer and removing what is under them."""

    def setUp(self):
        app()
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_redact_area_")
        self.plain = make_pdf(os.path.join(self.tmp, "plain.pdf"))
        self.window = MainWindow()
        self.window._open_file_path(self.plain)
        self.viewer = self.window.current_context.viewer

    def tearDown(self):
        for context in list(getattr(self.window, "_contexts", [])):
            context.document.is_modified = False
        self.window.close()
        self.window.deleteLater()

    def text_rect(self):
        page = self.window.current_document.doc[0]
        hits = page.search_for(SAMPLE_TEXT)
        self.assertTrue(hits, "the sample text should be on the page")
        return hits[0]

    def test_marking_an_area_counts_it_without_changing_the_file(self):
        self.viewer.mark_redaction(1, self.text_rect())
        self.assertEqual(self.viewer.pending_redaction_count(), 1)
        self.assertIn(SAMPLE_TEXT,
                      self.window.current_document.doc[0].get_text())

    def test_clearing_the_marks_empties_them(self):
        self.viewer.mark_redaction(1, (10, 10, 60, 40))
        self.viewer.clear_pending_redactions()
        self.assertEqual(self.viewer.pending_redaction_count(), 0)

    def test_the_marks_of_the_current_page_are_drawn(self):
        self.viewer.mark_redaction(1, (10, 10, 60, 40))
        self.assertEqual(len(self.viewer.canvas._redact_rects), 1)

    def test_the_button_turns_the_mode_on_and_off(self):
        from src.ui.pdf_viewer import MODE_REDACT, MODE_SELECT
        self.window._mark_redaction_area()
        self.assertEqual(self.viewer.current_mode(), MODE_REDACT)
        self.window._mark_redaction_area()
        self.assertEqual(self.viewer.current_mode(), MODE_SELECT)

    def test_a_drag_in_hiding_mode_marks_an_area(self):
        from PySide6.QtCore import QEvent, QPointF
        from PySide6.QtGui import QMouseEvent

        self.window._mark_redaction_area()
        rect = self.text_rect()
        start = self.viewer.canvas.pdf_to_widget(rect).at(0)
        end = self.viewer.canvas.pdf_to_widget(rect).at(2)

        def press(kind, point):
            return QMouseEvent(kind, QPointF(point), Qt.LeftButton,
                               Qt.LeftButton, Qt.NoModifier)

        self.viewer._on_canvas_press(press(QEvent.MouseButtonPress, start))
        self.viewer._on_canvas_move(press(QEvent.MouseMove, end))
        self.viewer._on_canvas_release(press(QEvent.MouseButtonRelease, end))
        self.assertEqual(self.viewer.pending_redaction_count(), 1)

    def test_a_drag_in_hiding_mode_does_not_select_text(self):
        self.window._mark_redaction_area()
        self.assertEqual(self.viewer.get_selected_runs(), [])

    def test_applying_removes_the_text_under_the_area(self):
        self.viewer.mark_redaction(1, self.text_rect())
        self.window._apply_marked_redactions()
        self.assertNotIn(SAMPLE_TEXT,
                         self.window.current_document.doc[0].get_text())
        self.assertEqual(self.viewer.pending_redaction_count(), 0)

    def test_applying_with_nothing_marked_says_so(self):
        shown = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: shown.append(a[2] if len(a) > 2 else ""))
        self.window._apply_marked_redactions()
        self.assertTrue(shown)
        self.assertIn(SAMPLE_TEXT,
                      self.window.current_document.doc[0].get_text())

    def test_applying_marks_the_document_as_modified(self):
        self.window.current_document.is_modified = False
        self.viewer.mark_redaction(1, self.text_rect())
        self.window._apply_marked_redactions()
        self.assertTrue(self.window.current_document.is_modified)

    def test_the_hiding_buttons_are_on_the_protect_tab(self):
        from PySide6.QtWidgets import QPushButton
        for name in ("tool_Hide_an_area", "tool_Apply_the_hidden_areas"):
            button = self.window.ribbon.findChild(QPushButton, name)
            self.assertIsNotNone(button, f"{name} is missing from the ribbon")
            self.assertTrue(button.isEnabled(),
                            f"{name} is disabled with a document open")


if __name__ == "__main__":
    unittest.main()
