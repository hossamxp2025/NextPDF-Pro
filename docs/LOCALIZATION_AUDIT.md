# NextPDF Pro — Localization Audit

Date: 2026-11-14
Build: 1.1.0 / `20261114-1800`
Verdict: **PASS.** Arabic mode shows Arabic labels for all application UI
text; English mode shows English. Latin text that remains is limited to
product/technical names (`NextPDF Pro`, `PDF`, version numbers) and file
extensions.

---

## 1. Architecture

- `src/i18n.py` is the single source of strings: a 199-entry `ar` dictionary
  plus an English passthrough. `Translator.tr(key, **kwargs)` looks up the
  active language, falls back to the key, and formats placeholders.
- `src/config.py` keeps `get_translator()` / `set_translator_language()` for
  backward compatibility and persists the choice in
  `%LOCALAPPDATA%\NextPDF-Pro\settings.json`.
- `MainWindow._retranslate_ui()` rebuilds the ribbon and menus, retranslates
  panels, open viewers, overlays, and sets the application layout direction:
  `Qt.RightToLeft` for `ar`, `Qt.LeftToRight` for `en`.
- Language can be switched from **Settings** or the ribbon's language button;
  both call the same translation path.

---

## 2. Methods used

1. **Static extraction.** Parsed `src/i18n.py` with `ast` and scanned every
   `tr("…")` literal in `src/`. Result: 124 direct keys, 0 missing.
2. **Runtime recorder.** Monkey-patched `Translator.tr` to log any key that
   returned untranslated while the language was Arabic. Exercised: main window
   creation, ribbon + menus, document open, Add Text overlay creation,
   retranslation. Result: **0 untranslated keys** after adding `Insert`.
3. **Label dump.** Collected every `QPushButton` text, every ribbon group
   label, every menu action, tab title and the window title in both languages,
   then regex-checked for the opposite script.
4. **Persistence test.** Saved `language`, constructed a fresh `Settings`
   instance, and confirmed the value reloaded from disk.
5. **Layout direction check.** Compared `QApplication.layoutDirection()` and
   `MainWindow.layoutDirection()` after each switch.
6. **PDF-level Arabic check.** Separately verified that Arabic inserted into a
   PDF is shaped and stored with an embedded Noto font (see
   `docs/FUNCTIONAL_TEST_REPORT.md`, tests 02/04).

---

## 3. Results

### 3.1 Script leakage

| Check | Result |
|---|---|
| Arabic characters in any English-mode label | none |
| Latin characters in Arabic-mode labels | only `PDF` / `NextPDF` / `Pro` / version |
| Untranslated keys at runtime (Arabic) | 0 |
| Missing static `tr()` keys | 0 |

Examples of the only Latin strings left in Arabic mode:

- `دمج ملفات PDF` — "PDF" is a file-format name.
- Window title `NextPDF Pro 1.1.0 - محرر PDF احترافي` — product name + format.
- `NextPDF Pro` in the About dialog and `OFL`/license names in credits.

These are explicitly allowed as product/technical names.

### 3.2 Direction and persistence

```
ar app RTL | window RTL | title NextPDF Pro 1.1.0 - محرر PDF احترافي
en app LTR | window LTR | title NextPDF Pro 1.1.0 - Professional PDF Editor
```

```
saved language: en
reloaded language: en
after restart (new Settings): ar
```

The switch is applied immediately and survives a restart through
`settings.json`.

### 3.3 Localized surfaces covered

- Ribbon groups and every button (File, Edit, Insert, Pages, View, Tools).
- Full menu bar and all submenus.
- Window title, status bar, page/zoom labels.
- Empty state, thumbnails panel, properties panel.
- Inline text overlay: title, font/size/color labels, direction choices
  (Auto / Left to right / Right to left), Cancel/Apply, placeholders.
- Dialogs and warnings: open/save/print errors, unsupported text, OCR
  unavailable, page-range errors, unsaved-changes prompt.
- Settings dialog, including the interface-language selector.

---

## 4. Arabic text inside PDFs (not just the UI)

The UI language and PDF text shaping are separate concerns, and both were
checked:

- Insertion uses `Page.insert_htmlbox` with bundled Noto Naskh Arabic and
  Noto Sans, so glyphs are shaped and bidi-ordered.
- The saved file embeds `Noto Naskh Arabic Regular` (verified via
  `page.get_fonts()`).
- A rendered PNG of the reopened page shows connected, right-to-left Arabic
  (`مرحبا`, `مرحبا من الملف أ`).
- Extraction returns presentation forms such as `ﺣﺮﻣ`; that is a MuPDF
  extraction characteristic, not a rendering defect. Tests therefore assert
  fonts, span direction, geometry and ink instead of the logical string.

---

## 5. Deliberate English retained

| Item | Why |
|---|---|
| `NextPDF Pro`, `PDF`, `OCR`, `PNG`, `JPG` | product and format names |
| Font names (`Noto Naskh Arabic`, `Noto Sans`) | proper names of typefaces |
| Log messages and diagnostic reports | developer-facing, not UI |
| `Tesseract OCR` in the OCR-unavailable message | name of the external engine |

---

## 6. Limitations

- Only Arabic and English are shipped. The translator falls back to the key,
  so adding a third language requires a new dictionary, not code changes.
- Arabic UI fonts depend on Windows-provided fallbacks (Segoe UI); the PDF
  editor itself uses the bundled Noto fonts.
- No automated visual RTL screenshot comparison was performed; layout
  direction, label text and overlay behavior were asserted programmatically.
- A native-speaker review of wording is recommended before public release;
  this audit verifies coverage and script purity, not literary quality.
