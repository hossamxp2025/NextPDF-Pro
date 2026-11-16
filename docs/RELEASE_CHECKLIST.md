# NextPDF Pro — Release Checklist

Build: **1.1.0** / `20261114-1800`
Date: 2026-11-14
Decision: **READY FOR INTERNAL TESTING — NOT CLEARED FOR PUBLIC RELEASE**

The editing core passes its acceptance gate. The items in §5 block a public
release and are not cosmetic.

---

## 1. Artifact inventory

Folder: `dist/release-1.1.0/`

| File | Size | SHA-256 |
|---|---|---|
| `NextPDF-Pro.exe` | 104,319,641 B (99.5 MB) | `c11d7aab3e2b0ca5238d41a6c8aba0440f0d6f771c75f72e3786b25cceb3433f` |
| `README.txt` | — | `7ccafdb8970d4a27feb9b0cd359935b7d0c177f1d4cc44b6f4ec75a7de981aca` |
| `LICENSE.txt` | — | `58cd5dc029534518893c9f0b47293457dc1ffdee49fb526b9185160c0c59c6f0` |
| `LICENSES.txt` | — | `b53a00cd4e9a6e99f8cff4d3a14df386f6259b8e9e59b29efb0af4b449a90f15` |
| `OFL.txt` | — | `c5b58599ef73c8b021edbe8f3d6b7442cd5262d0c39aaa2f638ec340b9e2feda` |
| `VERSION.txt` | — | `142717db44f6c18614ccfa9d70e00b30ed9db2c43dc3c582349a95df3785357b` |
| `TEST_REPORT.txt` | — | `8ec93a4add6ab1fcba4f6a6da00f4c22a07bd953d529e2404f10432dd6c40a6c` |

`SHA256SUMS.txt` is generated from these files (it excludes itself).

The previous release in `dist/release/` was left untouched.

**Installer:** not built (`dist/release-1.1.0/NextPDF-Pro-Setup-1.1.0.exe` does
not exist). Inno Setup is not installed on this machine.

---

## 2. Build verification

- [x] `build/NextPDF-Pro.spec` points at `src/main.py`, bundles
      `resources/icons`, `resources/fonts` (incl. `OFL.txt`) and
      `resources/translations`.
- [x] Icon is a true multi-resolution ICO: 16/24/32/48/64/128/256.
- [x] Windows version resource (`build/version_info.txt`) embedded.
- [x] Optional OCR stack excluded intentionally; the app reports OCR as
      unavailable instead of bundling a non-working stack.
- [x] `upx=False` (fewer antivirus false positives, reproducible output).
- [x] Build script writes to a versioned folder and refuses to report success
      if the EXE is missing.
- [x] `--version`, `--self-test`, `--smoke-gui` diagnostics included.

Build command:

```powershell
python build\build_exe.py
```

## 3. Test verification

- [x] Full suite: **49 passed / 0 failed** (`docs/evidence/pytest_full.txt`).
- [x] Acceptance tests 01–10: **10 passed**
      (`docs/evidence/pytest_acceptance.txt`).
- [x] Add Text survives Save As + reopen (English and Arabic).
- [x] Edit Text removes the old glyphs and survives reopen (English and
      shaped Arabic).
- [x] Arabic shaping and embedded Noto font verified in the saved file.
- [x] Undo/redo restores real PDF bytes.
- [x] Two open documents stay isolated.
- [x] Arabic UI has no untranslated application labels; English UI has no
      Arabic labels.
- [x] Packaged `--self-test`: exit 0 (`docs/evidence/exe_selftest.txt`).
- [x] Packaged `--smoke-gui` offscreen: exit 0
      (`docs/evidence/exe_gui_smoke.txt`).

Re-run:

```powershell
$env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONIOENCODING="utf-8"
.venv\Scripts\python.exe -m pytest tests -v

$env:NEXTPDF_SELFTEST_REPORT="$env:TEMP\selftest.txt"
Start-Process .\dist\release-1.1.0\NextPDF-Pro.exe -ArgumentList --self-test -Wait -PassThru
```

---

## 4. Functional checklist (tested scope)

| Area | Status | Note |
|---|---|---|
| Open / Save / Save As | PASS | atomic full save, source file untouched on Save As |
| Add Text (ar/en) | PASS | shaped, positioned at click, font embedded |
| Edit Text (ar/en) | PASS | old glyphs removed, replacement in same band |
| Delete Text | PASS | redaction without touching images/line art |
| Undo / Redo | PASS | byte snapshots |
| Multiple documents | PASS | per-tab context, no cross-tab leakage |
| Page insert/delete/rotate/move | PASS | survives save/reopen |
| Extract / Merge | PASS (engine) | dialog-driven in UI |
| Print | Code path verified | needs a printer for an end-to-end run |
| Search | PASS | existing UI tests |
| Properties | Code path verified | dialog inspection |
| Settings + language persistence | PASS | `settings.json` reload |
| OCR | Honestly unavailable | button disabled, explicit message |
| Signature / encryption / redaction | Not implemented | not exposed as working buttons |

---

## 5. Blockers for public release

1. **Clean Windows VM test — NOT DONE.** Install and run on a fresh Windows 10
   and Windows 11 x64 VM, including a non-admin user profile and a path with
   spaces/Arabic characters.
2. **Installer — NOT BUILT.** Install Inno Setup 6, run
   `python build\build_exe.py --installer`, then test install/uninstall,
   desktop shortcut, and `.pdf` association on the VM.
3. **Licensing — NOT CLEARED.** PyMuPDF/MuPDF are AGPL-3.0. Public
   distribution requires AGPL compliance (source offer) or a commercial
   PyMuPDF license. Qt/PySide6 LGPL-3.0 obligations also need review. See
   `LICENSES.txt`. This is a legal decision, not an engineering checkbox.
4. **Code signing — NOT DONE.** The EXE is unsigned; SmartScreen will warn.
5. **Manual QA — PARTIAL.** Printer output, OCR on a machine with Tesseract,
   very large PDFs (100+ MB), and RTL layout at 125–200% display scaling were
   not exercised.
6. **Native Arabic wording review — RECOMMENDED.** Coverage is verified;
   literary quality is not.

---

## 6. Rollback

- Pre-repair source snapshot: `backup/src_baseline_20261114/`.
- Previous release: `dist/release/` (unchanged).
- Rebuild from the snapshot by restoring `src/` and the three build files
  (`NextPDF-Pro.spec`, `build_exe.py`, `installer.iss`).

---

## 7. Sign-off

| Gate | Result |
|---|---|
| Code compiles and tests pass | YES |
| Add/Edit Text survive save + reopen | YES |
| Arabic shaping in saved PDF | YES |
| Localization complete (ar/en) | YES |
| EXE builds and self-tests | YES |
| Clean-VM test | NO — required before release |
| Installer | NO — required before release |
| License review | NO — required before release |

**Release status: internal build only.**
