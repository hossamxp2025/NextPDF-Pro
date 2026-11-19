#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The signing part of the Protect and Sign tab: the dialog's choices, where a
visible signature lands on the page, the wording of a verification result, and
the two refusals that keep a signature honest - signing an unsaved document,
and signing something that is not a file yet.

These tests drive the real window with the real test certificate, so a signed
file is actually produced and read back, not simulated.
"""

import os
import sys
import tempfile
import unittest

import pymupdf as fitz

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from src.engine.signing import SignatureReport, verify_document
from src.i18n import get_translator
from src.ui.main_window import MainWindow
from src.ui.sign_dialog import (DEFAULT_HEIGHT, DEFAULT_WIDTH, MARGIN,
                                SignDialog, placement_rect, report_text)

CERT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "certificates")
P12 = os.path.join(CERT_DIR, "test-signer.p12")
ROOT = os.path.join(CERT_DIR, "test-signer.crt")
PASSWORD = "nextpdf-test"
ARABIC_NAME = "حسام الفاخرة"


def app():
    return QApplication.instance() or QApplication([])


def plain_pdf(path, pages=1):
    doc = fitz.open()
    for number in range(pages):
        doc.new_page(width=400, height=600).insert_text((40, 40), f"Page {number}")
    doc.save(path)
    doc.close()
    return path


class PlacementTests(unittest.TestCase):
    """A corner put in the wrong place is invisible until someone looks."""

    def test_bottom_right_keeps_the_margin_from_both_edges(self):
        left, top, right, bottom = placement_rect("bottom-right", 400, 600)
        self.assertAlmostEqual(right, 400 - MARGIN)
        self.assertAlmostEqual(bottom, 600 - MARGIN)
        self.assertAlmostEqual(right - left, DEFAULT_WIDTH)
        self.assertAlmostEqual(bottom - top, DEFAULT_HEIGHT)

    def test_top_left_starts_at_the_margin(self):
        left, top, _, _ = placement_rect("top-left", 400, 600)
        self.assertAlmostEqual(left, MARGIN)
        self.assertAlmostEqual(top, MARGIN)

    def test_the_two_bottom_corners_are_not_the_same_place(self):
        self.assertNotAlmostEqual(placement_rect("bottom-left", 400, 600)[0],
                                  placement_rect("bottom-right", 400, 600)[0])

    def test_a_page_narrower_than_the_signature_still_gives_a_box_on_it(self):
        left, top, right, bottom = placement_rect("bottom-right", 120, 120)
        self.assertGreaterEqual(left, 0)
        self.assertGreaterEqual(top, 0)
        self.assertLessEqual(right, 120)
        self.assertLessEqual(bottom, 120)


class ReportWordingTests(unittest.TestCase):
    """What the reader acts on is the sentence, not the flag behind it."""

    def setUp(self):
        get_translator().set_language("en")
        self.tr = get_translator().tr

    def report(self, **changes):
        fields = dict(field_name="F", signer="Test Signer", intact=True,
                      valid=True, trusted=False, covers_whole_file=True)
        fields.update(changes)
        return SignatureReport(**fields)

    def test_no_signature_is_said_plainly(self):
        self.assertIn("no digital signature", report_text([], self.tr))

    def test_an_intact_but_untrusted_signature_says_both_things(self):
        text = report_text([self.report()], self.tr)
        self.assertIn("has not changed", text)
        self.assertIn("not confirmed", text)

    def test_a_broken_signature_says_the_file_changed(self):
        text = report_text([self.report(intact=False)], self.tr)
        self.assertIn("HAS changed", text)
        self.assertNotIn("has not changed since", text)

    def test_an_addition_after_signing_is_called_out(self):
        text = report_text([self.report(covers_whole_file=False)], self.tr)
        self.assertIn("added to the file after signing", text)

    def test_trust_is_only_claimed_when_it_was_established(self):
        text = report_text([self.report(trusted=True)], self.tr)
        self.assertIn("trusted on this computer", text)
        self.assertNotIn("not confirmed", text)


class SignDialogTests(unittest.TestCase):
    def setUp(self):
        app()
        get_translator().set_language("en")

    def test_signing_without_a_certificate_is_refused_with_a_reason(self):
        dialog = SignDialog(page_count=3, current_page=2)
        self.assertIsNotNone(dialog.validation_error())
        dialog.deleteLater()

    def test_a_certificate_path_that_does_not_exist_is_refused(self):
        dialog = SignDialog()
        dialog.certificate_path.setText(os.path.join(tempfile.gettempdir(),
                                                     "no-such-file.p12"))
        self.assertIn("does not exist", dialog.validation_error())
        dialog.deleteLater()

    def test_the_dialog_opens_on_the_page_being_viewed(self):
        dialog = SignDialog(page_count=5, current_page=4)
        self.assertEqual(dialog.page.value(), 4)
        self.assertEqual(dialog.page.maximum(), 5)
        dialog.deleteLater()

    def test_turning_the_drawing_off_disables_the_placement_choices(self):
        dialog = SignDialog(page_count=2)
        dialog.visible.setChecked(False)
        self.assertFalse(dialog.page.isEnabled())
        self.assertFalse(dialog.position.isEnabled())
        dialog.deleteLater()

    @unittest.skipUnless(os.path.isfile(P12), "no test certificate")
    def test_checking_a_self_signed_certificate_says_nobody_vouches_for_it(self):
        dialog = SignDialog()
        dialog.certificate_path.setText(P12)
        dialog.password.setText(PASSWORD)
        dialog._check_certificate()
        details = dialog.certificate_details.text()
        self.assertIn("signed itself", details)
        self.assertIn("Test", details)
        dialog.deleteLater()

    @unittest.skipUnless(os.path.isfile(P12), "no test certificate")
    def test_a_wrong_password_is_reported_in_the_dialog_not_raised(self):
        dialog = SignDialog()
        dialog.certificate_path.setText(P12)
        dialog.password.setText("wrong")
        dialog._check_certificate()
        self.assertIn("password", dialog.certificate_details.text().lower())
        dialog.deleteLater()


@unittest.skipUnless(os.path.isfile(P12),
                     "run scripts/make_test_certificate.py first")
class SigningFromTheWindowTests(unittest.TestCase):
    def setUp(self):
        app()
        get_translator().set_language("en")
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_sign_ui_")
        self.path = plain_pdf(os.path.join(self.tmp, "doc.pdf"), pages=2)
        self.output = os.path.join(self.tmp, "signed.pdf")
        self.window = MainWindow()
        self.assertTrue(self.window._open_file_path(self.path))
        self.messages = []
        QMessageBox.information = staticmethod(
            lambda *a, **k: self.messages.append(a[2] if len(a) > 2 else ""))
        QMessageBox.critical = staticmethod(
            lambda *a, **k: self.messages.append(a[2] if len(a) > 2 else ""))
        QMessageBox.warning = staticmethod(
            lambda *a, **k: self.messages.append(a[2] if len(a) > 2 else ""))
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)
        QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: (self.output, ""))

    def tearDown(self):
        for context in list(getattr(self.window, "_contexts", [])):
            context.document.is_modified = False
        self.window.close()
        self.window.deleteLater()

    def arm_dialog(self, **choices):
        """Accept the dialog with a fixed set of answers, without showing it."""
        answers = {
            "certificate_path": P12,
            "password": PASSWORD,
            "reason": "Approved",
            "location": "Cairo",
            "signer_label": ARABIC_NAME,
            "visible": True,
            "page": 1,
            "position": "bottom-right",
        }
        answers.update(choices)
        import src.ui.sign_dialog as sign_dialog

        class Armed(sign_dialog.SignDialog):
            def exec(inner):
                return QDialog.DialogCode.Accepted

            def signing_arguments(inner):
                return dict(answers)

        self.addCleanup(setattr, sign_dialog, "SignDialog",
                        sign_dialog.SignDialog)
        sign_dialog.SignDialog = Armed

    def test_the_ribbon_offers_the_three_signing_buttons(self):
        from src.ui.ribbon import RibbonButton

        names = {button.objectName()
                 for button in self.window.ribbon.findChildren(RibbonButton)}
        self.assertIn("tool_Sign_with_a_certificate", names)
        self.assertIn("tool_Check_the_signatures", names)
        self.assertIn("tool_What_a_signature_proves", names)

    def test_signing_an_unsaved_document_is_refused_and_says_why(self):
        self.window.current_document.is_modified = True
        self.window._sign_document()
        self.assertFalse(os.path.exists(self.output))
        self.assertTrue(any("unsaved" in m for m in self.messages), self.messages)

    def test_a_signed_copy_is_written_and_the_original_is_untouched(self):
        before = open(self.path, "rb").read()
        self.arm_dialog()
        self.window._sign_document()

        self.assertTrue(os.path.isfile(self.output))
        self.assertEqual(open(self.path, "rb").read(), before)
        report = verify_document(self.output, trust_roots=[ROOT])[0]
        self.assertTrue(report.unchanged_since_signing)
        self.assertTrue(report.covers_whole_file)

    def test_a_visible_signature_lands_on_the_page_that_was_chosen(self):
        self.arm_dialog(page=2)
        self.window._sign_document()

        with fitz.open(self.output) as signed:
            first = list(signed.load_page(0).widgets())
            second = list(signed.load_page(1).widgets())
        self.assertFalse(first)
        self.assertTrue(second)

    def test_an_invisible_signature_draws_nothing_but_still_signs(self):
        self.arm_dialog(visible=False)
        self.window._sign_document()

        # An invisible signature is still a signature field - that is how PDF
        # records one - but its rectangle is empty, so nothing is painted.
        with fitz.open(self.output) as signed:
            areas = [w.rect.get_area() for page in signed for w in page.widgets()]
        self.assertTrue(all(area == 0 for area in areas), areas)
        self.assertTrue(verify_document(self.output)[0].intact)

    def test_the_success_message_says_there_is_no_timestamp(self):
        self.arm_dialog()
        self.window._sign_document()
        self.assertTrue(any("timestamp" in m for m in self.messages),
                        self.messages)

    def test_a_wrong_certificate_password_fails_without_writing_a_file(self):
        self.arm_dialog(password="wrong")
        self.window._sign_document()
        self.assertFalse(os.path.exists(self.output))
        self.assertTrue(any("password" in m.lower() for m in self.messages),
                        self.messages)

    def test_checking_an_unsigned_document_says_it_has_no_signature(self):
        shown = {}
        import src.ui.sign_dialog as sign_dialog
        original = sign_dialog.SignatureReportDialog

        class Captured(original):
            def __init__(inner, reports, parent=None):
                shown["reports"] = reports

            def exec(inner):
                return 0

        sign_dialog.SignatureReportDialog = Captured
        self.addCleanup(setattr, sign_dialog, "SignatureReportDialog", original)

        self.window._check_signatures()
        self.assertEqual(shown["reports"], [])

    def test_the_explanation_names_what_the_program_does_not_do(self):
        self.window._explain_signature()
        text = " ".join(self.messages)
        self.assertIn("timestamp", text)
        self.assertIn("revocation", text)

    def test_the_stamp_explanation_no_longer_says_signing_is_unavailable(self):
        self.window._explain_stamp()
        text = " ".join(self.messages)
        self.assertNotIn("not available yet", text)
        self.assertIn("certificate", text)


if __name__ == "__main__":
    unittest.main()
