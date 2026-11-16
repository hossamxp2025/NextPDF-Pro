# Conversion implementation and current limits

## Verified scope

All enabled conversion Ribbon buttons run in a separate Qt-managed process. Inputs are snapshots of the active PDF; output is staged in a parent-created temporary directory and published after child success. Progress is per page, not fabricated duration. Cancel requests kill the owned process tree on Windows and do not publish staged output. Runtime does not download dependencies.

| Output | Implemented mode | Limits |
|---|---|---|
| PNG/JPEG/WEBP | Page raster, 150 DPI | One selected page; resolution/quality UI not yet exposed |
| TIFF | Raster frames, lossless deflate | Multi-page supported in engine; large-output memory stress not tested |
| TXT | Logical text layer | Scans require OCR first; shaped presentation-form Arabic is refused |
| HTML | UTF-8 logical text reflow with RTL and HTML escaping | No original images, fonts, tables or layout reconstruction |
| Markdown | Plain logical text valid as Markdown | No inferred headings, tables or original styling |
| SVG | MuPDF vector page representation | One page; not an editable document-layout conversion |
| JSON | Page dimensions, page number and logical text | Not a complete image/table/semantic document representation |
| DOCX | Embedded page images | NOT editable text/tables. Word page dimensions follow source; image is inset. No claim of pixel-perfect Word pagination |
| PPTX | Embedded page image per slide | NOT editable page elements. Mixed page sizes letterboxed into first-page slide dimensions |
| XLSX | Actual cells from a fully ruled rectangular grid | No merged cells, scanned tables, borderless tables or arbitrary layout inference. Simple numeric typing; date formats not inferred |
| CSV | One fully ruled rectangular grid | Multiple tables refused. UTF-8 BOM; formula-like strings escaped |

## Tests

- Every enabled format has a real output test. Image outputs are decoded; SVG parsed as XML; JSON decoded; text/HTML checked for expected content.
- Every enabled conversion button is clicked through the actual Ribbon/dialog with real subprocess export; save dialog path is supplied in the test. Output files are reopened and inspected.
- DOCX/PPTX fixture includes Arabic and English ink. Embedded page PNG bytes decode to the exact source raster; no claim of editable Arabic text is made.
- XLSX fixture verifies actual cell values, invoice-code punctuation and numeric values. A logical Arabic grid verifies Unicode values and `rightToLeft` worksheet direction.
- CSV fixture verifies actual row/column values. Non-table paragraphs are refused rather than labelled successful spreadsheets.
- Source bytes remain unchanged in the tested GUI export cases.

## Remaining mandatory work

Editable DOCX/PPTX modes, sophisticated layout preservation, reverse Office-to-PDF, image/HTML/TXT-to-PDF UI, automatic OCR fallback, output quality controls, large/multi-column stress tests, image-quality review in external Office applications, full UI localization/theme review and legal packaging inventory remain incomplete. Create-PDF and unsupported editing-mode controls are disabled. The current source is not a final release.

Development dependency additions: python-pptx 1.0.2 (PyPI metadata reports MIT), XlsxWriter 3.2.0. Installed binary wheels only without dependency scripts. No complete dependency advisory audit or redistribution legal review is claimed.
