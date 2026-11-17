#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Making a PDF smaller.

Two things shrink a PDF: dropping what the file no longer needs (dead
objects, duplicated streams, uncompressed streams) and storing its images
at a lower resolution or quality.  The first is lossless and always safe;
the second is not, so it is a choice the caller makes and the result says
what it cost.

Nothing here reports a saving it did not achieve: if the rewritten file is
not smaller, the original bytes are kept and the result says so.
"""

import logging
import os
import shutil
import tempfile
from typing import Optional

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz

logger = logging.getLogger("NextPDF")

#: Images stored at more than this many dots per inch are candidates for
#: being stored again at ``image_dpi``.
DEFAULT_DPI_THRESHOLD = 200
DEFAULT_IMAGE_DPI = 150
DEFAULT_QUALITY = 70


class CompressionResult(dict):
    """What a compression run achieved, as plain data.

    Keys: ``before`` and ``after`` (bytes), ``saved`` (bytes, never
    negative), ``ratio`` (0.0-1.0 of the original that was saved),
    ``changed`` (whether the written file differs from the original) and
    ``images_rewritten``.
    """

    @property
    def saved(self) -> int:
        return self["saved"]

    @property
    def changed(self) -> bool:
        return self["changed"]


def compress_pdf(source_path: str, target_path: str,
                 recompress_images: bool = True,
                 image_dpi: int = DEFAULT_IMAGE_DPI,
                 quality: int = DEFAULT_QUALITY,
                 password: Optional[str] = None) -> CompressionResult:
    """Write a smaller copy of *source_path* to *target_path*.

    The copy keeps the original's encryption; a protected file is never
    silently written out unprotected.  When nothing can be saved the
    original is copied unchanged and ``changed`` is False.
    """
    if not 72 <= int(image_dpi) <= 600 or not 1 <= int(quality) <= 100:
        raise ValueError("Invalid compression options")
    before = os.path.getsize(source_path)
    images_rewritten = False
    directory = os.path.dirname(os.path.abspath(target_path)) or "."
    handle, staged = tempfile.mkstemp(suffix=".pdf", dir=directory)
    os.close(handle)
    try:
        doc = fitz.open(source_path)
        try:
            # needs_pass is read once, before authenticating: reading it
            # afterwards drops the decryption state in PyMuPDF.
            if getattr(doc, "needs_pass", False):
                if not password or not doc.authenticate(password):
                    raise ValueError("The file is protected by a password")
                encryption = fitz.PDF_ENCRYPT_KEEP
            else:
                encryption = fitz.PDF_ENCRYPT_KEEP
            if recompress_images:
                try:
                    doc.rewrite_images(dpi_threshold=DEFAULT_DPI_THRESHOLD,
                                       dpi_target=int(image_dpi),
                                       quality=int(quality))
                    images_rewritten = True
                except Exception:
                    # An image the rewriter cannot handle must not lose the
                    # user the lossless saving below.
                    logger.exception("Image rewriting failed; "
                                     "continuing without it")
            doc.save(staged, garbage=4, deflate=True, deflate_images=True,
                     deflate_fonts=True, clean=True, encryption=encryption)
        finally:
            doc.close()
        after = os.path.getsize(staged)
        if after < before:
            os.replace(staged, target_path)
            staged = None
            changed = True
        else:
            # Writing a bigger file and calling it compression would be a
            # lie; the user gets their original size instead.
            if os.path.abspath(source_path) != os.path.abspath(target_path):
                shutil.copyfile(source_path, target_path)
            after = before
            changed = False
            images_rewritten = False
    finally:
        if staged and os.path.exists(staged):
            os.unlink(staged)
    saved = max(0, before - after)
    return CompressionResult(before=before, after=after, saved=saved,
                             ratio=(saved / before) if before else 0.0,
                             changed=changed,
                             images_rewritten=images_rewritten)
