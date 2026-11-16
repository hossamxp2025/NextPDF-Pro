# NextPDF Pro — Functional Test Report

Date: 2026-11-14
Build: 1.1.0 / `20261114-1800`
Scope: real PDF editing through the application's own code, then save and reopen.
Verdict: **PASS for the tested scope.** Add Text and Edit Text survive Save As
and reopen, Arabic is genuinely shaped, undo/redo restores real PDF bytes, and
two open documents stay isolated.

---

## 1. Environment

| Component | Test environment | Build environment |
|---|---|---|
| Python | 3.12.10 (.venv) | 3.12.10 |
| PySide6 | 6.12.0 | 6.8.3 |
| PyMuPDF | 2.1 (MuPDF 1.28.6) | 2.1 (MuPDF 1.28.6) |
| PyInstaller | not installed | 6.13.0 |
| OS | Windows x64 | Windows x64 |
| Qt platform | `offscreen` for GUI tests | n/a |

Commands were executed from `C:\Users\DELL\NextPDF-Pro` with
`QT_QPA_PLATFORM=offscreen` and `PYTHONIOENCODING=utf-8`.

---

## 2. Defects fixed in this phase

These were found by executing the app, not by reading it:

1. **RTL text was pinned to the wrong edge of its box.** MuPDF resolves
   `text-align` against paragraph direction; with `direction: rtl`, `right`
   behaved as the left edge. Text clicked at x=400 was drawn at x≈349.
   Fix: mirror the keyword for RTL in `TextEditor._css`. Verified: click at
   x=400 now ends the glyph run at x≈399.
2. **Shaped Arabic runs were classified as LTR.** Extraction returns Arabic
   presentation forms (U+FB50–FDFF, U+FE70–FEFF), outside the old U+0600–06FF
   test. Editing text inserted by the app itself would have defaulted to LTR.
   Fix: shared `contains_rtl_text()` in `models/document.py`.
3. **Failed engine operations were pushed onto the undo stack.** A refused
   edit created a useless snapshot entry. Fix: `PDFSnapshotCommand.execute`
   now treats `result.success == False` as failure.
4. **Arabic-mode group label "Insert" was untranslated.** Found by a runtime
   recorder of translator calls; added to `src/i18n.py`.
5. **The shipped ICO contained only a 16×16 frame.** Rebuilt from a new SVG as
   16/24/32/48/64/128/256 px and packaged.
6. **Silent settings/directory failures.** Replaced `except: pass` with logged
   warnings in `config.py`.

Engine-level Arabic and replacement behavior had already been proven in the
preceding probe; this phase moved the same operations through the GUI.

---

## 3. Executed test evidence

### 3.1 Full suite

```
.venv\Scripts\python.exe -m pytest tests -v
49 passed in 2.42s
```

Raw output: `docs/evidence/pytest_full.txt`.

### 3.2 Acceptance tests (01–10)

```
.venv\Scripts\python.exe -m pytest tests\test_acceptance.py -v
10 passed in 1.89s
```

Raw output: `docs/evidence/pytest_acceptance.txt`.

| ID | Test | Method | Result |
|---|---|---|---|
| 01 | Add English text survives save + reopen | GUI click → overlay → commit → Save As → reopen | PASS |
| 02 | Add Arabic shapes and embeds a font | same, plus font table, shaped spans, right edge, ink pixels | PASS |
| 03 | Edit English removes old text | GUI edit overlay → Save As → reopened text | PASS |
| 04 | Edit shaped Arabic removes old ink | shaped fixture, RTL direction check, replace, reopen | PASS |
| 05 | Undo/redo restores real bytes | command stack undo → text gone; redo → text back | PASS |
| 06 | Two documents stay isolated | add to A, add to B, save both, compare contents | PASS |
| 07 | Localization has no leaks | collect every ribbon/menu label in ar/en | PASS |
| 08 | Save As does not touch source | SHA-256 untouched; output valid PDF | PASS |
| 09 | Delete selected text removes ink | select run → delete → save → reopen | PASS |
| 10 | Page operations survive save | insert page, rotate page, save, reopen | PASS |

Key assertions, for the record:

- **Arabic is checked as ink, not as a string.** PyMuPDF extracts shaped text
  as presentation forms (and some ligatures carry no clean Unicode mapping).
  Test 02 therefore asserts: `Noto Naskh Arabic Regular` is in the font table,
  at least one span is RTL, its right edge is within 3 pt of the click, and
  the rendered clip contains non-white pixels.
- **Replacement really removes the old text.** Tests 03/04 assert the old
  string is absent after reopening, not merely that the new string exists.
- **Undo is byte-level.** `PDFSnapshotCommand` stores `to_bytes()` before and
  after; test 05 verifies the page text changes back and forth.

### 3.3 Packaged executable

Built with `python build\build_exe.py` (global Python + PyInstaller):

```
dist\release-1.1.0\NextPDF-Pro.exe
size: 104,319,641 bytes (99.5 MB)
sha256: c11d7aab3e2b0ca5238d41a6c8aba0440f0d6f771c75f72e3786b25cceb3433f
```

Because a windowed EXE has no console, the build contains two diagnostic
modes that write a report file and return an exit code:

| Command | Result | Evidence |
|---|---|---|
| `NextPDF-Pro.exe --self-test` | exit 0; bundled fonts found; PDF created, Arabic+Latin inserted, saved, reopened; Noto Naskh embedded; shaped spans present | `docs/evidence/exe_selftest.txt` |
| `NextPDF-Pro.exe --smoke-gui` (offscreen) | exit 0; window created (Arabic title), ribbon built, PDF opened in a viewer tab | `docs/evidence/exe_gui_smoke.txt` |

A successful launch alone was not counted as proof; the self-test exercises
the same engine functions used by the UI and inspects the saved file.

---

## 4. Button-by-button functional status

Every ribbon button either performs a real operation or is disabled with an
explicit reason. None is a placeholder.

| Button | Behavior | Evidence |
|---|---|---|
| New / Open / Save / Save As | real document create/load/save (atomic temp+replace) | tests 01/08; smoke |
| Print | renders every page into a real QPrinter | code path inspected; needs a printer to execute |
| Undo / Redo | restores PDF bytes from snapshots | test 05 |
| Edit Text | redacts old glyphs, inserts shaped replacement | tests 03/04 |
| Add Text | HTML layout with bundled Noto fonts | tests 01/02 |
| Delete Selected Text | redacts the selected run | test 09 |
| Insert Image | file dialog + `ImageEditor.insert_image` | engine path; not covered by an automated GUI test |
| Insert/Delete/Rotate/Move Page | real page mutations via PyMuPDF | test 10 |
| Extract Pages / Merge PDFs | real page-manager operations with dialogs | engine functions exercised in earlier probes |
| Zoom In/Out, Fit Page/Width | real viewer zoom state | existing UI tests |
| Search | real text search + highlight | existing UI tests |
| Properties | real run/element inspection dialog | code path inspected |
| OCR | **disabled** when Tesseract is absent, with a clear message | verified disabled at startup |
| Settings / Language | persisted settings and full retranslation | test 07 + persistence check |
| Insert Page | adds a blank page | test 10 |

---

## 5. Not tested / limitations (no overclaiming)

- **Clean Windows 10/11 VM: NOT TESTED.** All runs were on the development
  machine. Installer execution on a fresh VM remains a release gate.
- **Installer: NOT BUILT.** Inno Setup (`ISCC.exe`) is not installed here.
- **OCR: unavailable.** Tesseract is intentionally not bundled; the button is
  disabled rather than faking a result.
- **Text editing is horizontal-only.** Rotated/vertical runs are refused with
  a message; this is a deliberate limit, not silent corruption.
- **Arabic extraction is lossy.** Text copied out of a saved PDF may differ
  from the logical Arabic string; rendering and printing are correct.
- **No Acrobat/JOPDF parity claimed.** Signatures, encryption, and secure
  redaction are not implemented.
- **Licensing:** PyMuPDF is AGPL-3.0. Public redistribution needs AGPL
  compliance or a commercial license; this build has neither legal review nor
  a commercial PyMuPDF license.

---

## 6. Release artifacts

`dist/release-1.1.0/`:

| File | SHA-256 |
|---|---|
| `NextPDF-Pro.exe` | `c11d7aab3e2b0ca5238d41a6c8aba0440f0d6f771c75f72e3786b25cceb3433f` |
| `README.txt` | `7ccafdb8970d4a27feb9b0cd359935b7d0c177f1d4cc44b6f4ec75a7de981aca` |
| `LICENSE.txt` | `58cd5dc029534518893c9f0b47293457dc1ffdee49fb526b9185160c0c59c6f0` |
| `LICENSES.txt` | `b53a00cd4e9a6e99f8cff4d3a14df386f6259b8e9e59b29efb0af4b449a90f15` |
| `OFL.txt` | `c5b58599ef73c8b021edbe8f3d6b7442cd5262d0c39aaa2f638ec340b9e2feda` |
| `VERSION.txt` | `142717db44f6c18614ccfa9d70e00b30ed9db2c43dc3c582349a95df3785357b` |
| `TEST_REPORT.txt` | `8ec93a4add6ab1fcba4f6a6da00f4c22a07bd953d529e2404f10432dd6c40a6c` |

`SHA256SUMS.txt` in the same folder lists the same hashes.

---

## 7. Quality-gate evaluation

| Gate | Status |
|---|---|
| Add Text survives Save As + reopen | **PASS** (test 01/02) |
| Edit Text survives Save As + reopen and removes old text | **PASS** (tests 03/04) |
| Arabic shape appears in the saved file | **PASS** (font + ink assertions) |
| Active-document isolation | **PASS** (test 06) |
| Arabic UI has no English labels (product names excepted) | **PASS** (test 07 + runtime key recorder) |
| Enabled buttons do real work or are honestly disabled | **PASS for the inspected set**; OCR disabled by design |
| EXE launches and edits a PDF | **PASS** (self-test + GUI smoke) |
| Clean-VM install test | **NOT TESTED** |
| Installer | **NOT BUILT** |

Conclusion: the editing core meets the acceptance gate. The build is suitable
for internal testing; it is not cleared for public distribution until the VM
test, installer, and AGPL/LGPL licensing review are complete.
