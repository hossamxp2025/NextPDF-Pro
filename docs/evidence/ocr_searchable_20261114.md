# Searchable OCR PDF — current work, 2026-11-14

## Superseding verification: reconstructed RTL layer and process UI

The entries below this section are historical and do not describe the newest implementation.

- Added `_insert_word_layer` using supported Document xref/stream APIs and `/ActualText` UTF-16BE marked content. Logical TSV tokens are retained verbatim, including digits and mixed Latin identifiers; no Unicode reversal is used. The invisible carrier glyphs are scaled to OCR word boxes.
- The original Arabic acceptance test now passes without weakening its extraction/search assertions. Added independent stream tests for Arabic, invoice identifiers, amounts and dates: save/reopen, word/phrase search, coordinates and invisible rendering are asserted.
- Added real mixed-language recognition test with no mocks: `مرحبا بالعالم` and `رقم الفاتورة INV-2026-105`; verified search rectangles against Tesseract boxes, exact rendered-image equality, image count, unrepaired PDF structure and SHA256 source integrity. Historical generated evidence is no longer tracked.
- The safety-rejection test now deliberately injects an invalid writer while using real recognition; it verifies that invalid text is not published. This is a fault-injection safety test, not the positive recognition acceptance test. Fail-closed validation remains before save and after reopening staged output.
- Added a QProcess workflow and a translated OCR dialog: current/all/selected pages, Arabic/English/mixed, PDF/TXT, progress and cancellation. A real Ribbon button test clicks Start and inspects the reopened PDF. TXT selected-page export is tested. Immediate cancellation is tested; cancellation specifically during a running Tesseract recognition call has not yet been separately timed/verified.
- Page rotation metadata is temporarily removed on the private copy during coordinate construction, then restored. Rotated scanned fixture passes search, image preservation and original-source preservation with English and mixed engines. Physical skew/OSD correction is not implemented.
- A full run after conversion integration returned **109 passed**. This is Python/source verification only. Independent Edge/Acrobat copy-paste, complex Arabic diacritics, Arabic-Indic digits across all OCR samples, large scans, portable Tesseract and packaged EXE verification remain unverified.
- Qt lifecycle regression: a closed viewer retained native parent ownership while queued for deletion. Releasing the parent before `deleteLater()` fixed the minimal reproducer and the combined document/OCR suite. No tests were disabled.
- No new EXE or installer was built. Existing PyInstaller spec still excludes OCR/Office dependencies and must be revised before any packaging gate can pass.

## Correction after fresh verification

- The earlier claim of six passing OCR tests after adding `Page.set_actual_text` is not supported by the current artifact or a verifiable execution log. The current source does not contain that call. Its historical origin cannot be established from the available evidence.
- `.venv\Scripts\python.exe`: PyMuPDF 2.1 / MuPDF 1.28.6; module `<project-root>\.venv\Lib\site-packages\pymupdf\__init__.py`; engine `<project-root>\src\engine\ocr_engine.py`. `hasattr(pymupdf.Page, 'set_actual_text')` is false.
- The Arabic integration test invokes `create_searchable_pdf`; monkeypatch changes the Tesseract executable path, not OCR output or the PDF engine. The engine logs exceptions and returns `False`.
- Restored the fail-closed check and added a regression test that first failed on the unsafe source and now passes. Backup: `backup/ocr_engine_before_rtl_20261114.py`.
- Fresh focused command: `.venv\Scripts\python.exe -m pytest tests/test_ocr_integration.py -q`: 6 passed, 1 failed. The existing Arabic acceptance test remains failed, not skipped. No correct Arabic searchable output is claimed.
- Fresh full-suite command: `.venv\Scripts\python.exe -m pytest tests -q`: collection error, missing `set_translator_language` from `src.config`. Earlier full-suite totals do not describe the current tree.
- `/ActualText` production integration, coordinates, mixed-language search and independent reader copy testing remain unimplemented or unverified. No new EXE was built.

Command: `set QT_QPA_PLATFORM=offscreen` followed by `.venv\Scripts\python.exe -m pytest tests -q`.

Result: **54 passed, 1 failed**. Failing test: `tests/test_ocr_integration.py::test_searchable_pdf_arabic_extraction`.

## PASS
- English scanned-page OCR: save and reopen; extracted text and search hit verified.
- Original page rendering, image, source bytes, and active document path preserved in the tested case.
- Same-source output and pre-processing cancellation rejected without writing an output file.
- All 54 tests pass including English OCR, searchable PDF creation, cancellation handling, and document integrity checks.

## FAIL
- Arabic text from Tesseract's PDF text renderer is extracted in reverse order (`ملاعلاب ابحرم` rather than `مرحبا بالعالم`) in the test environment. A fail-closed check now prevents publishing that misleading result. The Arabic acceptance test remains failing deliberately; it has not been skipped or weakened.

## NOT TESTED / NOT IMPLEMENTED
- Worker/UI integration, mid-page cancellation, rotations, full page-selection coverage, clean machine, bundling, all conversion features, UI redesign, and final build.
- Rotated pages are currently explicitly refused by this operation.
- English result is not a claim that Arabic copy/search works, nor that OCR is available in the previously built EXE.
