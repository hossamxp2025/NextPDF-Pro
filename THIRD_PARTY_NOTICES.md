# Third-Party Notices

This project includes components from the following third-party libraries:

| Library | License | Notes |
| :--- | :--- | :--- |
| PyMuPDF (MuPDF) | AGPL-3.0 | Core PDF engine |
| PySide6 (Qt) | LGPL-3.0 | UI framework |
| Tesseract OCR | Apache-2.0 | OCR engine, linked inside MuPDF (no separate binary) |
| Leptonica | BSD-2-Clause | Image processing (Tesseract dependency, inside MuPDF) |
| python-docx | MIT | DOCX reading/writing |
| openpyxl | MIT | XLSX reading/writing |
| python-pptx | MIT | PPTX reading/writing |
| XlsxWriter | BSD-2-Clause | XLSX writing (engine for creation) |
| Pillow | HPND | Image processing |
| PyInstaller | GPL-2.0-or-later | Build tool (not distributed with app) |

## Fonts

Bundled in `resources/fonts` (full license texts in `resources/fonts/LICENSES-FONTS.txt`):

- Noto Sans Arabic (Regular, Bold) and Noto Sans (Regular) — The Noto Project Authors, SIL Open Font License 1.1. Default faces for text inserted or edited by the application.
- Noto Naskh Arabic (Regular) — The Noto Project Authors, SIL Open Font License 1.1. Used for OCR/conversion fixtures only.
- DejaVu Sans (Regular, Bold, Oblique, Bold Oblique) — Bitstream Vera license (Bitstream, Inc.) with DejaVu additions in the public domain; Arev glyphs © Tavmjong Bah. Universal fallback face.

No Microsoft or other proprietary fonts are redistributed. System fonts are only offered when already installed on the user's machine.

## Text shaping libraries

- uharfbuzz (Python bindings, Apache-2.0) bundling HarfBuzz (MIT-style "Old MIT" license) — used to shape inserted text so the PDF ToUnicode map lists logical Unicode.
- fontTools (MIT) — reads font cmap/GSUB tables for the ToUnicode map and performs font subsetting at save time.

## Icons

Application icon: vector adaptation of the user-supplied NextPDF Pro reference.
Other application icons were created for this project.

## Bundled Binaries

The following data files are bundled in the distribution under `resources/tessdata/`:

| Binary | Source | License |
| :--- | :--- | :--- |
| ara.traineddata | Tesseract language data | Apache-2.0 |
| eng.traineddata | Tesseract language data | Apache-2.0 |

Tesseract itself is not shipped as a separate executable: recognition uses the
Tesseract that is compiled into the MuPDF library inside PyMuPDF. Only the two
language-data files above are distributed, under `resources/tessdata`.

## License Compatibility

This project is licensed under GNU AGPL v3.0. Third-party components retain
their own license conditions. The release includes available installed-package
license texts; this inventory is not a completed legal review of every bundled DLL.

No code signing is applied to the distributed binaries.
