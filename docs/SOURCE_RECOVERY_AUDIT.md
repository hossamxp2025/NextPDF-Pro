# Source recovery audit

## Latest reconstructed-source checkpoint (2026-11-15)

- This is reconstructed source, not recovered original 1.1.0 source. Checkpoint: `backup/verified_source_20261115_091642`, including a source SHA256 manifest.
- Version/build identity is now `src/version.py`; `build/generate_metadata.py` generates VERSION.txt, Windows version resource and Inno version include. The release line remains 1.1.0 with development status; no final-release readiness is implied. Existing release directories were not changed.
- Implemented a real eleven-page Qt Ribbon with tab/stack synchronization, scrolling tool pages, document-aware buttons and explicit unavailable tools.
- Added logical Arabic OCR marked-content writer and post-save validation, isolated subprocess OCR and conversion dialogs, and supported-format exports with output inspection tests.
- Diagnosed and fixed native Qt lifetime crash using `tests/test_deferred_close.py`: closing a window while a removed viewer still had native parent ownership and pending deferred deletion could crash the next event loop. Detaching the viewer before deferred deletion fixed the reproducer and combined suite. The crash was not suppressed or bypassed by disabling tests.
- Latest full run: **109 passed in 15.85s**; log `docs/evidence/stabilization_20261115_tests.txt`. Native Windows Qt captures are in `docs/evidence/ribbon_reconstruction/`. DPI scaling at 125–200% was not verified.
- Mandatory remaining work includes portable Tesseract/license inventory, advanced editable Office modes, reverse conversion, final icon, complete themes/localization audit, large-document QA, independent-reader OCR copy verification, packaged runtime acceptance and installer. No EXE build was started.

## Snapshot and inventory

- Project: `<project-root>`.
- Before source edits, copied `src`, `tests`, `resources`, `docs`, `build`, `requirements.txt`, `README.txt`, and `VERSION.txt` into `backup/recovery_snapshot_20261114_163541`. Existing files and releases were not overwritten. This snapshot excludes the Python environments, distribution binaries and user settings stored outside the project.
- No `.git` entry exists at the project root; Git was not found on PATH or in the checked Program Files and per-user Git paths. Git status, log and reflog are therefore unavailable; no Git operation was attempted.
- `backup/src_baseline_20261114` is a pre-repair source snapshot. It has no `i18n.py`; its `ui/main_window.py` is 32,614 bytes, timestamp 2026-11-14 13:47:58, and does not contain `_contexts` or `DocumentContext`.
- Current `src/ui/main_window.py` is 32,663 bytes and likewise lacks those context symbols. Its small difference from the baseline includes later translator changes. The recovery snapshot contains the same current source.
- The current `src/i18n.py` has 55 Arabic keys at runtime. Neither the baseline nor any other source copy found under this project provides the previously reported larger translation table.
- Current `src/engine/text_editor.py`, `src/engine/image_editor.py`, `src/engine/page_manager.py`, `src/models/document.py` and `src/ui/pdf_viewer.py` differ in SHA-256 from the baseline and have later modification timestamps. Replacing them with baseline files would discard subsequent work.
- `backup/ocr_engine_before_rtl_20261114.py` is an OCR-only snapshot; the current OCR engine includes the newer fail-closed check. Both have been preserved. The regression test `test_rejects_reversed_arabic_layer_without_writing` remains in place.
- The build directory contains packaged Python archives and release artifacts, not verified original source files. They were not used to claim source recovery or overwrite source files.

## Cause and present status

The recorded prior execution copied `backup/src_baseline_20261114/ui/main_window.py` and `config.py` into `src`, and rewrote `i18n.py`. This explains why older source and a reduced translation table are now present. No complete, verified stable 1.1.0 source copy was located in the searched project paths. No source files have been restored from the old baseline in this recovery pass.

The ten teardown errors are caused by `tests/test_acceptance.py` accessing `win._contexts`, which the old `MainWindow` does not define. This is a missing implementation contract, not evidence that the teardown should be suppressed. Event-filter errors also occur when `PDFViewer.canvas` is absent during Qt events and require separate diagnosis.

Fresh full run: `$env:QT_QPA_PLATFORM='offscreen'; $env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe -m pytest tests -q --tb=no` produced **42 passed, 15 failed, 10 errors**. The failed Arabic searchable-PDF acceptance test is among the failures. This is not a recovered or release-ready source tree.

## Next work

Recover the per-document window and complete translation source from a trustworthy development copy if one is found; otherwise implement the missing contracts against the existing acceptance tests while preserving the newer engines and OCR safety check. Verify teardown, actual PDF editing and document isolation before adding conversion features. Arabic OCR, conversion, interface redesign and final packaging remain gated on recovery and testing.

## Subsequent incremental reconstruction

- Saved current source, tests, resources, build files and available user JSON settings in `backup/recovery_source_20261114_163724` before changes.
- Two older source backups under `<project-root>-Backup-v1.0.1-20261114-094850` and `<project-root>-Backup-20261114-112504` do not contain the missing document context implementation. They were not copied over the current source.
- Added an initial per-document context, tab switching, independent command stacks, guarded tab close, text commit routing and selected-text deletion. This is a reconstruction, not recovered original 1.1.0 source; remaining close, translation and toolbar behavior requires verification.
- Added a viewer event-filter lifecycle guard, with a test that failed before the patch and passed after it.
- Focused verification: `pytest tests/test_acceptance.py::test_09_delete_selected_text_removes_ink tests/test_document_context_lifecycle.py tests/test_viewer_lifecycle.py -q` yielded 3 passed. The context lifecycle test covers opening, switching and closing two documents, not the full range of editing or save behaviors.
- A preceding acceptance run reported 8 passed and 2 failed; one of those failures was the selected text deletion, subsequently addressed by the focused run. Language purity remains a known failure. Do not infer full-suite success from these focused runs.
- A full run before the latest window-close change reported 53 passed, 6 failed and no teardown errors. Failures: Arabic searchable OCR, language purity, version metadata, window title, ribbon compatibility and language switching. Following that run, window close was changed to process every context; the focused context and viewer lifecycle tests passed (3 passed). A fresh full run was started afterward; its result must be checked independently before claiming the same totals.
- Fresh full run after the window-close change: `pytest tests -q --tb=short`: **54 passed, 6 failed, no teardown errors**. Failures remain those listed above. The close test covers unmodified documents; save/cancel with multiple modified documents is not verified.
- Subsequent fresh full run before adding the modified-close test: **54 passed, 6 failed**, zero teardown errors, confirming the same failure groups. Added a real-PDF modified-tab test with dialog responses controlled via monkeypatch: cancel preserves the open modified document, then Save closes it and the saved text survives reopening. Focused `pytest tests/test_document_context_lifecycle.py -q`: **3 passed**. This test uses one modified document; multiple-modified-tab application-close and discard remain unverified. The full suite has not yet been rerun with this additional test.
