# NextPDF Pro — Engineering Audit (Phase 0)

Date: 2026-11-14
Auditor: automated source inspection + executed baseline tests
Project root: `<project-root>`
Python: 3.12.10 (venv: `.venv`, PySide6 6.12.0, PyMuPDF 2.1 / MuPDF 1.28.6)

This audit records what the existing code actually does. A method existing in a
module is **not** evidence that the corresponding feature works. Every status
below is based on source inspection and, where possible, an executed command.

---

## 1. Actual module architecture

```
src/
  main.py                 entry point; QApplication, theme, MainWindow
  config.py               metadata, settings JSON (LOCALAPPDATA), SimpleTranslator
  i18n.py                 (added in this repair) centralized ar/en strings
  models/document.py      PDFDocument + TextRun/ImageElement/Shape/Annotation dataclasses
  engine/text_editor.py   text selection and text mutation
  engine/page_manager.py  page insert/delete/rotate/move/merge/split
  engine/image_editor.py  image insert/delete/resize/move/extract
  engine/ocr_engine.py    Tesseract OCR (optional)
  commands/command.py     CommandStack + text commands
  ui/main_window.py       ribbon (QToolBar), menus, tabs, side panels, handlers
  ui/pdf_viewer.py        QScrollArea + QLabel renderer, zoom, click selection
  ui/components.py        buttons, cards, empty state, properties, thumbnails
  ui/theme_manager.py     light/dark QSS + RTL/LTR
resources/
  icons/*.svg, *.png, NextPDF-Pro.ico
  theme/modern_dark.qss, modern_light.qss
  fonts/                  (added in this repair) Noto fonts for Arabic shaping
tests/
  test_pdf_engine.py      engine unit tests (do not reopen saved files)
  test_regression_ui.py   imports/window creation
  test_modern_ui.py       smoke test for widget construction
build/                    PyInstaller spec + Inno Setup script
dist/release/             old binaries and old report (not evidence)
```

Entry point: `src/main.py` (`python -m src.main` / `python src/main.py`).

PDF library: **PyMuPDF 2.1** (`import pymupdf as fitz`). It is AGPL-3.0 or
commercial; distribution requires AGPL compliance or a commercial licence.
`pikepdf` (MPL-2.0), Pillow, OpenCV, pytesseract, reportlab, pyHanko are
declared in `requirements.txt`; most are unused by current code paths.

## 2. Baseline test execution (real result)

Command:

```
$env:QT_QPA_PLATFORM="offscreen"
.\.venv\Scripts\python.exe -m pytest tests -v
```

Result: **36 passed, 3 failed**.

Failures (real, reproducible):

| Test | Failure |
|---|---|
| `tests/test_modern_ui.py::test_components` | `RibbonGroup` inherits `QWidget` but calls `setFrameStyle()` → `AttributeError` |
| `tests/test_regression_ui.py::TestMainWindow::test_ribbon_exists` | test expects `ribbon.current_tab_id`; toolbar is a plain `QToolBar` with no such attribute |
| `tests/test_regression_ui.py::TestMainWindow::test_language_switch` | `_retranslate_ui()` reads `settings["language"]` instead of the translator language, so English switch leaves Arabic title |

Test-suite weaknesses (verified by reading the tests):

- `test_edit_text` only mutates an in-memory `TextRun`; it never saves and
  reopens the PDF, so it cannot prove that text editing reaches the file.
- No test calls `PDFDocument.save()` with the default arguments used by the
  Save button.
- No GUI test opens a real PDF, clicks the page, enters text, or checks tabs.
- No localization test inspects displayed Arabic/English widget text.
- No coordinate/zoom accuracy test.

## 3. Verified functions (work at code level)

| Area | Evidence |
|---|---|
| Open PDF / read pages | `PDFDocument.load()` uses `fitz.open`, extracts pages/text/images |
| Render page | `render_page()` returns a valid pixmap (unit test passes) |
| Page count / rotation | PyMuPDF page APIs; unit tests pass |
| Insert blank page / delete page | `PageManager` + unit tests pass |
| Insert image | `page.insert_image` called at fixed rect |
| Thumbnails | rendered from `get_page_thumb` |
| Theme switching (dark/light) | QSS applied, tests pass |
| Basic text extraction | spans extracted with font/size/color/bbox |

## 4. Broken or non-functional (verified)

### 4.1 Add Text / Edit Text (critical)
`set_add_text_mode()` / `set_editing_mode()` only set a boolean and cursor.
`_on_mouse_press()` never branches on those booleans. There is no inline editor,
no commit path, and no signal to the main window. **Feature is a UI stub.**

Additionally the `README`/`FUNCTIONAL_AUDIT` claim for text editing is
unsupported.

### 4.2 Save button can fail
`PDFDocument.save()` defaults to `incremental=True` and passes
`garbage=4, deflate=True`. PyMuPDF rejects garbage collection during an
incremental save. `_save_file()` uses those defaults, so saving over the
original file can fail while `Save As` (incremental=False) works.
Also `save(incremental=True)` after page insertion/deletion is not allowed.

### 4.3 Active viewer resolution
`_get_current_viewer()` only accepts `tab_widget.currentWidget()` if it is a
`PDFViewer`. The empty-state tab is an `EmptyState`; if the current tab is the
empty state (or a viewer was replaced) every command reports
"No active PDF viewer". Opening a second file closes `self.current_document`
(the previously active document) while leaving its tab alive with a closed
`fitz.Document`. There is no per-tab context: editors, command stack, page and
zoom are global, so commands can target the wrong document.

### 4.4 Coordinate conversion
`_check_text_selection()` adds scrollbar values to a `QLabel` mouse position.
Qt already gives widget-relative coordinates; scroll offsets are already
applied by the scroll area. The code then divides by zoom and DPI, but the
label also has stylesheet padding/border while its fixed size equals the
pixmap size, so the pixmap is shifted/clipped. Rotation is ignored entirely.
Selection therefore lands at wrong PDF coordinates.

### 4.5 Selection rendering
`update_selection()` is `pass`. No visual feedback for selected text.

### 4.6 Text edit persistence
`TextEditor.edit_text_run()` only mutates a Python dataclass. `commit_changes_to_pdf()`
is never called by the UI, and `PDFDocument.save()` only inserts runs whose id
starts with `new_`; it never applies edits to existing text. Saving after an
edit loses the change. `TextEditor._replace_existing_text()` uses
`run.height` and `y` in a way that can redact the wrong band, and does not
preserve background.

### 4.7 Arabic text
`_insert_text_run` uses `page.insert_text()` with the glyphs in logical order.
MuPDF does no Arabic shaping or bidi in that API. A real probe rendered
`مرحبا بالعالم` as disconnected, reversed letters. **Arabic is not supported
by the current insertion path.** A real shaped insertion is possible with
`Page.insert_htmlbox` + an embedded font; this repair uses that path and
verifies it visually and in the saved file.

### 4.8 Localization
Hard-coded bilingual strings exist throughout:
`"خطأ / Error"`, `"تنبيه / Warning"`, `"Fit Page"`, `"Fit Width"`,
`"Edit Text"`, `"Add Text"`, `"Insert Image"`, menu labels `"ملف / File"`,
`"صفحة 1 / 1 / Page 1 / 1"`, properties panel, empty state, OCR dialog.
`SimpleTranslator` has an incomplete dictionary (no "Add Text", "Edit Text",
"Insert Image", "Page", "Get Started", "Print", "Cancel", "Apply", ...).
`_retranslate_ui()` only changes the window title; it does not rebuild the
ribbon, menus, panels or viewer, and it ignores the translator's current
language. Language preference is saved but not applied to live widgets.

### 4.9 RibbonGroup crash
`RibbonGroup(QWidget)` calls `setFrameStyle()`; `QWidget` has no such method.
Any construction of this widget crashes. It is currently unused, but the UI
test exercises it.

### 4.10 Icons
`resources/icons/NextPDF-Pro.ico` is 855 bytes. The PNG set is inconsistent
(512×512 PNG is 5.8 KB while 256×256 is 136 KB), indicating upscaled/downscaled
raster sources. The ICO almost certainly lacks true 16/24/32/48/256 frames.
`NextPDF-Pro.svg` exists but is not used to generate the ICO.

### 4.11 Dead/disabled features presented as available
OCR is unavailable because Tesseract is not installed; the button remains
enabled and only shows a warning. Convert/Sign/Protect/Review buttons are not
present in the current ribbon but are listed as "NOT IMPLEMENTED" in the old
audit. No print, search, extract, merge, reorder, or properties UI exists even
though the engines partially support them.

## 5. Missing tests

- Save → reopen integrity (native and Save As)
- Add English text → save → reopen → verify ink/text
- Add Arabic text → save → reopen → verify shaped glyphs visually and embedded font
- Edit existing text → save → reopen → verify old text removed
- Active document isolation with two tabs
- Coordinate mapping at 50/100/200 % and rotated pages
- Arabic-only and English-only UI text + RTL/LTR
- Page insert/delete/rotate persisted and verified after reopen
- Corrupted / encrypted / read-only / non-PDF error handling
- EXE smoke test of the packaged binary

## 6. Packaging issues

- `build/build_exe.py` calls `pyinstaller` from PATH; PyInstaller is not in
  `.venv` (checked: `No module named PyInstaller`). Global Python 3.13 has
  PyInstaller 6.13 and PySide6 6.8.3 / PyMuPDF 2.1.
- `build/NextPDF-Pro.spec` does not include `resources/theme` or
  `resources/fonts` in `datas`, so a packaged build cannot load its QSS or
  Arabic fonts.
- Spec duplicates PySide6 plugin DLLs manually; PyInstaller hooks already do
  this and the manual copy risks path/plugin conflicts and bloat.
- Old `dist/release/TEST_REPORT.txt`, `SHA256SUMS.txt` and binaries are from
  earlier builds and are **not** evidence for this repair.
- Inno Setup script has a mojibake Arabic task description and includes the
  stale TEST_REPORT.

## 7. Licensing concerns

- PyMuPDF is AGPL-3.0 or commercial. Any public distribution of the EXE must
  comply with AGPL (source offer) or be covered by a commercial licence.
- Noto fonts (added under `resources/fonts`) are SIL OFL 1.1; the OFL text is
  included. Amiri (if used as an alternative) is also OFL.
- `LICENSE.txt` currently describes an MIT-style licence for the application;
  it does not address PyMuPDF AGPL obligations. Redistribution readiness is
  therefore **not established**.
- No JOPDF assets are copied; the UI is an independent implementation.

## 8. Repair plan (executed in this work)

1. Add per-tab document context, active-tab synchronization, safe close prompts,
   and structured viewer-resolution logging.
2. Rebuild the viewer around a dedicated page canvas with exact coordinate
   mapping (zoom, DPI, device pixel ratio, page rotation), visible selection,
   inline text overlay, and mode routing.
3. Implement real text insertion with shaped Arabic via `insert_htmlbox` and
   bundled Noto fonts; implement safe replacement via redaction only for
   supported horizontal runs, with explicit refusal otherwise.
4. Implement snapshot-based undo/redo that restores actual PDF bytes.
5. Fix save semantics (incremental vs full save) and reopen verification.
6. Centralize ar/en strings, rebuild UI on language switch, add Settings dialog,
   enforce RTL/LTR.
7. Add real handlers for print, search, properties, extract, merge, reorder,
   delete selected text; disable unavailable OCR with a clear reason.
8. Generate a new vector SVG icon and a true multi-resolution ICO.
9. Add file-level acceptance tests, run them, then package.

---

## 8. Post-repair status (2026-11-14, build 1.1.0)

This audit is the historical baseline. The repair described above was
implemented and verified afterwards:

- 49 automated tests pass (10 of them file-level acceptance tests).
- Add/Edit Text, Arabic shaping, undo/redo, document isolation, localization
  and page operations were re-verified after saving and reopening files.
- The packaged EXE passes a built-in `--self-test` (real PDF edit + reopen)
  and `--smoke-gui` (Qt window + document tab).
- Two additional defects found during GUI verification were fixed: RTL
  `text-align` was mirrored by MuPDF, and shaped Arabic runs were classified
  as LTR. Details in `docs/FUNCTIONAL_TEST_REPORT.md`.
- Localization coverage is documented in `docs/LOCALIZATION_AUDIT.md`.
- Release gates and remaining blockers are in `docs/RELEASE_CHECKLIST.md`.

Baseline failures listed in sections 2–4 must be read as "state before the
repair"; the current state is recorded in the documents above.
