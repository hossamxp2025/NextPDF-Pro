# NextPDF Pro 1.4.2 — release record

Build: **1.4.2** / `20261116-1055`
Date: 2026-11-16
Scope: two field defects in PDF conversion, plus the legal-identity text in the
About and Terms windows.

This file records what was actually executed for 1.4.2. It replaces nothing:
the earlier 1.1.0 checklist in `docs/RELEASE_CHECKLIST.md` stays as history.

## 1. What changed

| Area | Defect | Fix |
|---|---|---|
| PDF → DOCX/PPTX | A PDF whose embedded Type0/Identity-H font has no `/ToUnicode` map exported as stretched Latin garbage (`ČƈƢƗ…`) | The embedded font's cmap is reversed through glyph IDs, then the visual order is converted to logical order. If the font is not embedded or coverage is too low, export stops with a clear message instead of writing a damaged file |
| PDF → XLSX/CSV | Borderless, shaded statement tables were not detected because detection relied on ruling lines | Detection now tries the drawn grid, then text columns, then text columns over horizontal lines, and rejects tables without a real gutter |
| Arabic tables | Text-detected tables came out in reverse column order | Only text-detected (borderless) tables are reversed; drawn grids keep the column order they are drawn in |
| Values | `1,200.00` and `16-11-2026` were written as text | Numbers and dates are written as real Excel numbers and dates |
| Terms (EN) | Dialog showed the literal key `Terms intro en` | The English body is shown |
| About | Founder line showed only the Arabic name in English mode | `Future of Automation (مستقبل الأتمتة)` in both languages |

## 2. Artifacts

Folder: `dist/release-1.4.2/` (not committed; rebuild with
`python build/build_exe.py --installer`)

| File | Size (bytes) | SHA-256 |
|---|---|---|
| `NextPDF-Pro.exe` | 92,879,093 | `36c2788df9affcb2efc75e923a0c0f3cce839b68c2d3833b6e7281b36850ad1a` |
| `NextPDF-Pro-Setup-1.4.2.exe` | 94,932,011 | `b63e3bd32cc395b378137207800fb6b8598e16ad82a2753e5b1fdd8b741d7467` |

`dist/release-1.4.0/` and `dist/release-1.4.1/` were left untouched; the build
script refuses to write into an existing release folder.

## 3. Verification performed

| Check | Result | Evidence |
|---|---|---|
| Full pytest suite | **201 passed, 0 failed** (99.5 s) | run twice, on 1.4.1 and again after the 1.4.2 text fix |
| New regression tests | 11 cases: broken-encoding repair, refusal without an embedded font, borderless table values/dates, RTL order | `tests/test_encoding_and_borderless_tables.py`, fixtures in `tests/pdf_fixtures.py` |
| Real statement, DOCX/PPTX | Arabic paragraphs correct in Word/PowerPoint output | `docs/evidence/stmt_result.docx`, `.pptx` (not committed: contains personal data) |
| Real statement, XLSX | Table 1 `A1:I19`, Table 2 `A1:I14`; headers `التاريخ…الرصيد`; dates as `datetime`; amounts numeric | `docs/evidence/stmt_result.xlsx` (not committed: contains personal data) |
| Packaged `--self-test` | PASS, 0 failures | `docs/evidence/selftest-1.4.2.txt` |
| Packaged `--verify-release` | **32/32 PASS** | `docs/evidence/verify-1.4.2/report.json` |
| Installer | Built with Inno Setup 6, installs and uninstalls cleanly | `docs/evidence/install-1.4.2-installed.log` |
| Installed EXE hash | Matches `SHA256SUMS.txt` | `36c2788d…` |
| Installed `--self-test` | PASS, 0 failures | `docs/evidence/selftest-1.4.2-installed.txt` |
| Installed `--verify-release` | **32/32 PASS** from `%LOCALAPPDATA%\Programs\NextPDF Pro\NextPDF-Pro.exe` | `docs/evidence/verify-1.4.2-installed/report.json` |
| UI screenshots | About and Terms in Arabic and English, captured from the real windows | `docs/screenshots/about-ar.png`, `about-en.png`, `terms-ar.png`, `terms-en.png` |
| Installer license page | Arabic (RTL wizard) and English captures | `docs/screenshots/setup-license-ar.png`, `setup-license-en.png` |

`clean_machine` is `false` in both verify reports: the checks ran on this
workstation, not on a fresh Windows image.

## 4. Still open

- **Clean-machine test not done.** Everything below ran on this machine.
- **Code signing not done.** SmartScreen will warn on first run.
- **License review is a legal decision**, not an engineering checkbox. MuPDF is
  AGPL-3.0; Qt/PySide6 are LGPL-3.0. See `LICENSES.txt` and
  `THIRD_PARTY_NOTICES.md`.
- The installer renders the English AGPL text right-aligned in the Arabic
  wizard because Inno Setup mirrors the license memo in RTL mode. The wording
  is unchanged; only the paragraph alignment mirrors.
