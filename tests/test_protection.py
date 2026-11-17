#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for document protection: passwords, permissions and metadata removal.

Every case writes a real encrypted PDF and reads it back, so the assertions
are about what a reader would see in the file, not about the arguments the
code passed to PyMuPDF.
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

from models.document import (
    PDFDocument,
    FULL_PERMISSIONS,
    PERMISSION_MASK,
    permissions_are_restricted,
    permissions_from_flags,
)

SAMPLE_TEXT = "protected sample text"


def make_plain_pdf(path, title="Sample Title", author="Sample Author"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), SAMPLE_TEXT)
    doc.set_metadata({"title": title, "author": author})
    doc.save(path)
    doc.close()
    return path


class ProtectionTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nextpdf_protect_")
        self.plain = make_plain_pdf(os.path.join(self.tmp, "plain.pdf"))

    def out(self, name):
        return os.path.join(self.tmp, name)

    def encrypt(self, name="enc.pdf", **kwargs):
        doc = PDFDocument()
        self.assertTrue(doc.load(self.plain), doc.last_error)
        target = self.out(name)
        self.assertTrue(doc.save(target, **kwargs), doc.last_error)
        doc.close()
        return target


class PermissionFlagsTests(unittest.TestCase):
    def test_no_flags_allows_everything(self):
        self.assertEqual(permissions_from_flags({}) & PERMISSION_MASK,
                         permissions_from_flags({}) & PERMISSION_MASK)
        self.assertFalse(permissions_are_restricted(permissions_from_flags({})))

    def test_each_flag_clears_only_its_own_bit(self):
        value = permissions_from_flags({"print": False})
        self.assertFalse(value & fitz.PDF_PERM_PRINT)
        self.assertTrue(value & fitz.PDF_PERM_COPY)
        self.assertTrue(value & fitz.PDF_PERM_MODIFY)
        self.assertTrue(permissions_are_restricted(value))

    def test_accessibility_is_never_removed(self):
        value = permissions_from_flags(
            {"print": False, "modify": False, "copy": False,
             "annotate": False, "form": False, "assemble": False})
        self.assertTrue(value & fitz.PDF_PERM_ACCESSIBILITY)


class OpeningProtectedFilesTests(ProtectionTestCase):
    def test_plain_file_reports_no_protection(self):
        doc = PDFDocument()
        self.assertTrue(doc.load(self.plain))
        self.assertFalse(doc.is_encrypted)
        self.assertFalse(doc.needs_password)
        self.assertFalse(permissions_are_restricted(doc.permissions))
        doc.close()

    def test_without_a_password_the_file_is_refused_and_flagged(self):
        target = self.encrypt(user_password="open-me")
        doc = PDFDocument()
        self.assertFalse(doc.load(target))
        self.assertTrue(doc.needs_password)
        self.assertFalse(doc.wrong_password)
        self.assertEqual(doc.last_error, "Document is encrypted")

    def test_a_wrong_password_is_reported_as_wrong(self):
        target = self.encrypt(user_password="open-me")
        doc = PDFDocument()
        self.assertFalse(doc.load(target, "not-the-password"))
        self.assertTrue(doc.needs_password)
        self.assertTrue(doc.wrong_password)
        self.assertEqual(doc.last_error, "Password is incorrect")

    def test_the_user_password_opens_the_file_and_its_text(self):
        target = self.encrypt(user_password="open-me")
        doc = PDFDocument()
        self.assertTrue(doc.load(target, "open-me"), doc.last_error)
        self.assertTrue(doc.is_encrypted)
        self.assertIn(SAMPLE_TEXT, doc.doc[0].get_text())
        doc.close()

    def test_the_owner_password_also_opens_the_file(self):
        target = self.encrypt(user_password="open-me", owner_password="own-me")
        doc = PDFDocument()
        self.assertTrue(doc.load(target, "own-me"), doc.last_error)
        self.assertIn(SAMPLE_TEXT, doc.doc[0].get_text())
        doc.close()


class EncryptingTests(ProtectionTestCase):
    def test_saving_with_a_user_password_encrypts_the_file(self):
        target = self.encrypt(user_password="open-me")
        raw = fitz.open(target)
        self.assertTrue(raw.needs_pass)
        raw.close()

    def test_an_owner_password_alone_leaves_the_file_openable(self):
        target = self.encrypt(
            owner_password="own-me",
            permissions=permissions_from_flags({"print": False}))
        raw = fitz.open(target)
        self.assertFalse(raw.needs_pass)
        self.assertFalse(int(raw.permissions) & fitz.PDF_PERM_PRINT)
        self.assertIn(SAMPLE_TEXT, raw[0].get_text())
        raw.close()

    def test_restrictions_survive_the_round_trip(self):
        target = self.encrypt(
            user_password="open-me", owner_password="own-me",
            permissions=permissions_from_flags({"print": False, "copy": False}))
        doc = PDFDocument()
        self.assertTrue(doc.load(target, "open-me"), doc.last_error)
        self.assertFalse(doc.permissions & fitz.PDF_PERM_PRINT)
        self.assertFalse(doc.permissions & fitz.PDF_PERM_COPY)
        self.assertTrue(doc.permissions & fitz.PDF_PERM_MODIFY)
        doc.close()

    def test_restrictions_need_a_separate_owner_password(self):
        """Without its own owner password the file has only one password, and
        whoever opens it is the owner, so no restriction binds.  The dialog
        must therefore ask for an owner password before offering
        permissions."""
        target = self.encrypt(
            name="single.pdf", user_password="open-me",
            permissions=permissions_from_flags({"print": False}))
        doc = PDFDocument()
        self.assertTrue(doc.load(target, "open-me"), doc.last_error)
        self.assertTrue(doc.permissions & fitz.PDF_PERM_PRINT)
        doc.close()

    def test_the_open_document_stays_readable_after_an_encrypting_save(self):
        """Regression: reading ``needs_pass`` on an authenticated document
        drops its decryption state, which left the saved file open but with
        empty pages."""
        doc = PDFDocument()
        self.assertTrue(doc.load(self.plain))
        self.assertTrue(doc.save(self.out("after.pdf"), user_password="open-me"),
                        doc.last_error)
        self.assertIsNotNone(doc.doc)
        self.assertIn(SAMPLE_TEXT, doc.doc[0].get_text())
        self.assertTrue(doc.is_encrypted)
        doc.close()

    def test_an_ordinary_save_keeps_the_protection(self):
        target = self.encrypt(user_password="open-me")
        doc = PDFDocument()
        self.assertTrue(doc.load(target, "open-me"), doc.last_error)
        again = self.out("again.pdf")
        self.assertTrue(doc.save(again), doc.last_error)
        doc.close()
        raw = fitz.open(again)
        self.assertTrue(raw.needs_pass)
        raw.close()

    def test_removing_the_protection_leaves_a_readable_file(self):
        target = self.encrypt(user_password="open-me")
        doc = PDFDocument()
        self.assertTrue(doc.load(target, "open-me"), doc.last_error)
        cleared = self.out("cleared.pdf")
        self.assertTrue(doc.save(cleared, remove_encryption=True), doc.last_error)
        self.assertFalse(doc.is_encrypted)
        doc.close()
        raw = fitz.open(cleared)
        self.assertFalse(raw.needs_pass)
        self.assertFalse(permissions_are_restricted(int(raw.permissions) & PERMISSION_MASK))
        self.assertIn(SAMPLE_TEXT, raw[0].get_text())
        raw.close()


class MetadataRemovalTests(ProtectionTestCase):
    def test_a_normal_save_keeps_the_document_information(self):
        doc = PDFDocument()
        self.assertTrue(doc.load(self.plain))
        target = self.out("kept.pdf")
        self.assertTrue(doc.save(target), doc.last_error)
        doc.close()
        raw = fitz.open(target)
        self.assertEqual(raw.metadata.get("title"), "Sample Title")
        raw.close()

    def test_stripping_removes_every_information_field_but_keeps_the_pages(self):
        doc = PDFDocument()
        self.assertTrue(doc.load(self.plain))
        target = self.out("stripped.pdf")
        self.assertTrue(doc.save(target, strip_metadata=True), doc.last_error)
        doc.close()
        raw = fitz.open(target)
        for key in ("title", "author", "subject", "keywords", "creator", "producer"):
            self.assertFalse(raw.metadata.get(key),
                             f"{key} survived the metadata removal")
        self.assertIn(SAMPLE_TEXT, raw[0].get_text())
        raw.close()

    def test_stripping_and_encrypting_can_be_done_in_one_save(self):
        doc = PDFDocument()
        self.assertTrue(doc.load(self.plain))
        target = self.out("both.pdf")
        self.assertTrue(
            doc.save(target, strip_metadata=True, user_password="open-me"),
            doc.last_error)
        doc.close()
        raw = fitz.open(target)
        self.assertTrue(raw.needs_pass)
        raw.authenticate("open-me")
        self.assertFalse(raw.metadata.get("author"))
        self.assertIn(SAMPLE_TEXT, raw[0].get_text())
        raw.close()


if __name__ == "__main__":
    unittest.main()
