# NextPDF Pro 1.5.0 — release record

Build: **1.5.0** / `20261116-1540`
Date: 2026-11-16
Scope: band 1 of `docs/ROADMAP_1.5.md` — formatting fidelity of the editable
Word export (PDF → DOCX, "editable").

This file records what was actually executed for 1.5.0. It adds to, and
replaces nothing of, the earlier release records.

## 1. What changed

| Area | Defect | Fix |
|---|---|---|
| PDF → editable DOCX | Statement tables came out as loose paragraphs; the Word file had 0 tables | The existing table detector now also returns per-cell rectangles, styles and content bounds, and the Word path rebuilds a real Word table from them |
| Column widths | Columns were not carried, so Word wrapped narrow columns | Each column gets the wider of its detected boundary and its content width + 12% font-substitution allowance + 6 pt padding, then the row is fitted to the usable page width by taking space only from columns that have slack. `w:tblCellMar` reduced to 28 twips |
| Shading | Header bands and alternating row fills were lost | Fills under cells and under free lines are carried as `w:shd`; fills covering more than 60% of the page are treated as page background and ignored |
| White text | The white title on the navy band became white on white, i.e. missing text | The band under a line is carried as paragraph shading |
| Fonts | Runs were named after the generator-internal basefont (`FontReg`) | The family is read from the embedded font program's own `name` table (nameID 16, then 1), so `FontReg` resolves to `Tajawal` |
| Reading order | Side-by-side blocks on an Arabic page were emitted left-to-right | Items are banded by row and ordered right-to-left when the page is predominantly Arabic |
| RTL tables | Borderless detection yields page-left-to-right columns, which Word drew in the wrong order | Arabic tables get `w:bidiVisual` and their columns are written in logical order |
| Alignment | Every Arabic paragraph rendered against the left margin | Word mirrors `w:jc` inside a `w:bidi` paragraph; the requested edge is now swapped. `w:shd` and `w:bidi` are written before python-docx inserts `w:spacing`/`w:jc` so the `w:pPr` child order stays schema-valid |
| Images | Images were appended at the end of the page | Images are placed at their own position in the reading order |
| Page setup | Page size and orientation were not carried | Section size and orientation follow the source page |

Measured on a real bank statement (2 pages, outside the repository):

| Measure | Before | After |
|---|---|---|
| Paragraphs | 144 | 33 |
| Tables | 0 | 2 (19×9 and 14×9) |
| Font name | `FontReg` | `Tajawal` |
| Title "كشف حساب" | invisible (white on white) | visible on its navy band |
| Arabic alignment | left | right |
| Date column | wrapped to two lines | one line |

Not reproduced, by design: absolute positions. Word reflows text and the export
uses no text frames, so the three side-by-side summary cards in the statement
header stack vertically.

## 2. Artifacts

Folder: `dist/release-1.5.0/` (not committed; rebuild with
`python build/build_exe.py` then `python build/build_exe.py --installer`)

| File | Size (bytes) | SHA-256 |
|---|---|---|
| `NextPDF-Pro.exe` | 92,888,787 | `b5c459604be3ca350a8ad6d6cad623db0da70144da57c4421a5168e97d7b330e` |
| `NextPDF-Pro-Setup-1.5.0.exe` | 94,945,328 | `dc7bb6a902ee2b4ea35bab208a3dee03212d5b1844b1dc657c1bc84e90e12228` |

Earlier release folders were left untouched; the build script refuses to write
into an existing release folder.

## 3. Verification performed

| Check | Result | Evidence |
|---|---|---|
| Full pytest suite | **223 passed, 0 failed** (50.4 s) | `tests/`, run on the source immediately before the build |
| New regression tests | 22 cases: table rebuild, shading, column widths, RTL order, embedded font names, image placement, mirrored alignment, damaged page refusal | `tests/test_word_layout.py` |
| Packaged `--version` | `NextPDF Pro 1.5.0 (build 20261116-1540)`, exit 0 | — |
| Packaged `--self-test` | PASS, 0 failures | `docs/evidence/selftest-1.5.0.txt` |
| Packaged `--smoke-gui` | PASS (window, ribbon, open document, viewer tab/page) | `docs/evidence/smoke-gui-1.5.0.txt` |
| Packaged `--verify-release` | **32/32 PASS**, `"frozen": true` | `docs/evidence/verify-1.5.0/report.json` |
| Packaged conversion job, real statement → editable DOCX | `{"ok": true}`; 33 paragraphs, 2 tables (19×9, 14×9), both `bidiVisual`, fills `0B1647 / EAF0FF / F4F7FF / FFF6DA`, font `Tajawal`, section 842×595 landscape — identical to the source-tree result | run through `NextPDF-Pro.exe --conversion-job` |
| Visual check of that DOCX | Opened in **Microsoft Word 16** and exported from Word to PDF: 3 pages, navy header band with the white title visible, table right-to-left with the date column on one line | render kept local (real statement); reproduce with `docs/evidence/word-layout/README.md` |
| Installer | Compiled with Inno Setup 6 | build log above |
| Installation | `/VERYSILENT /CURRENTUSER`, exit 0, upgraded the installed 1.4.2 in place at `%LOCALAPPDATA%\Programs\NextPDF Pro`; `VERSION.txt` and the uninstall entry both read 1.5.0 | `docs/evidence/install-1.5.0.log` |
| Installed binary integrity | SHA-256 of the installed `NextPDF-Pro.exe` equals the released hash | `b5c45960…7d7b330e` |
| Installed `--self-test` | PASS, 0 failures | `docs/evidence/selftest-1.5.0-installed.txt` |
| Installed `--smoke-gui` | PASS | `docs/evidence/smoke-gui-1.5.0-installed.txt` |
| Installed `--verify-release` | **32/32 PASS** from `%LOCALAPPDATA%\Programs\NextPDF Pro\NextPDF-Pro.exe` | `docs/evidence/verify-1.5.0-installed/report.json` |
| Installed conversion, same statement | `{"ok": true}`; `word/document.xml` is **byte-identical** to the portable build's output (SHA-256 `77a9eeef…4d7b0826`) | run through the installed `--conversion-job` |

Two observations from the install, neither a defect in this release:

- The silent install reused the task choices remembered from the previous
  install, which had no Start Menu folder and a desktop icon. So the Start Menu
  group was not created and the desktop shortcut was refreshed to point at the
  1.5.0 binary. A fresh machine with default choices gets the Start Menu group.
- `SHA256SUMS.txt` as shipped **inside** the installer lists only
  `NextPDF-Pro.exe`, because the file is staged before the installer exists.
  The copy in `dist/release-1.5.0/` lists both. Pre-existing behaviour.

## 4. Not done

- Uninstallation was not exercised; the application is left installed at 1.5.0.
- The binaries are not code-signed.
- No clean-machine test.
- Bands 2–7 of `docs/ROADMAP_1.5.md` have not been started.
