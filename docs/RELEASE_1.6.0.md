# NextPDF Pro 1.6.0 — release record

Build: **1.6.0** / `20261118-1100`
Date: 2026-11-18
Scope: bands 2, 3, 4 and 6 of `docs/ROADMAP_1.5.md` — conversion completed,
protection and redaction, comments, interactive forms.

This file records what was actually executed for 1.6.0. It adds to, and
replaces nothing of, the earlier release records.

## 1. What is in this release

| Band | Feature | Details |
|---|---|---|
| 3 | Protection and redaction | AES-256 with an open password and an owner password, reader permissions, opening protected files, removing protection on an explicit request, clearing document data, redaction by text and by dragging an area |
| 2 | Conversion completed | Export resolution 72–600 DPI, real Markdown (headings, pipe tables, emphasis), numbered image files per page, automatic recognition of a scanned page with the output marked as recognised, PDF compression, Print and Document properties |
| 4 | Comments | Highlight, sticky note, text on the page, rectangle, ellipse, line — written as real PDF annotations; selection, editing, deletion, a list of all of them, each step undoable |
| 6 | Interactive forms | Read, fill and save AcroForm fields; create a text field, a tick box or a list of choices; delete a field; flatten the form |

Band 1 shipped in 1.5.0. Bands 5 (signing) and the remaining parts of 7 are
not in this release.

## 2. Artifacts

Folder: `dist/release-1.6.0/` (not committed; rebuild with
`python build/build_exe.py` then `python build/build_exe.py --installer`)

| File | Size (bytes) | SHA-256 |
|---|---|---|
| `NextPDF-Pro.exe` | 92,966,497 | `f70c84b67f2594d516e2eb14836638e66acc80c5c5116e671c164c64450f55eb` |
| `NextPDF-Pro-Setup-1.6.0.exe` | 95,020,335 | `71dd367d884606a683d96930a78546f3ff658b614bdbd2f32790d76872d5a036` |

Earlier release folders were left untouched; the build script refuses to write
into an existing release folder.

## 3. Verification performed

`--verify-release` was extended for this release: it now also exercises
protection, redaction, compression, comments, forms and the new conversion
outputs **inside the packaged application**, each against a file it writes and
then reopens, so what is checked is the saved PDF and not the state left in
memory. It grew from 32 checks to 71.

| Check | Result | Evidence |
|---|---|---|
| Full pytest suite | **466 passed, 0 failed** (169.8 s) | `tests/`, run on the source before the build |
| Packaged `--version` | `NextPDF Pro 1.6.0 (build 20261118-1100)`, exit 0 | `docs/evidence/version-1.6.0.txt` |
| Packaged `--self-test` | PASS, 0 failures | `docs/evidence/selftest-1.6.0.txt` |
| Packaged `--smoke-gui` | PASS (window titled `NextPDF Pro 1.6.0`, ribbon, open document, viewer tab/page) | `docs/evidence/smoke-gui-1.6.0.txt` |
| Packaged `--verify-release` | **71/71 PASS**, `"frozen": true`, executable = the released EXE | `docs/evidence/verify-1.6.0/report.json` |
| Source `--verify-release` | 71/71 PASS, `"frozen": false` — same checks, run before the build to separate a packaging fault from a code fault | run on the source tree |
| Installer | Compiled with Inno Setup 6 (10.9 s) | build log |
| Installation | `/VERYSILENT /CURRENTUSER`, exit 0; upgraded the installed 1.5.0 in place at `%LOCALAPPDATA%\Programs\NextPDF Pro`; `VERSION.txt` reads 1.6.0 / `20261118-1100` and the uninstall entry reads `1.6.0` | `docs/evidence/install-1.6.0.log` |
| Installed binary integrity | SHA-256 of the installed `NextPDF-Pro.exe` equals the released hash `f70c84b6…450f55eb` | — |
| Installed `--version` | `NextPDF Pro 1.6.0 (build 20261118-1100)`, exit 0 | `docs/evidence/version-1.6.0-installed.txt` |
| Installed `--self-test` | PASS, 0 failures | `docs/evidence/selftest-1.6.0-installed.txt` |
| Installed `--smoke-gui` | PASS; the window came up in Arabic (`NextPDF Pro 1.6.0 - محرر PDF احترافي`) from the saved language setting | `docs/evidence/smoke-gui-1.6.0-installed.txt` |
| Installed `--verify-release` | **71/71 PASS**, `"frozen": true`, executable = `%LOCALAPPDATA%\Programs\NextPDF Pro\NextPDF-Pro.exe` | `docs/evidence/verify-1.6.0-installed/report.json` |

One observation from the install, not a defect in this release and the same as
1.5.0: the silent install reused the task choices remembered from the previous
install, which had no Start Menu folder and a desktop icon. So no Start Menu
group was created and the desktop shortcut was refreshed to point at the 1.6.0
binary. A fresh machine with default choices gets the Start Menu group.

What the 39 new packaged checks prove, concretely:

| Area | Checked inside the EXE |
|---|---|
| Protection | A file saved with AES-256 and permissions is **refused without the password** and opens with it; its content is readable after unlocking; an ordinary save of it **still needs the password** afterwards |
| Redaction | The marked text is gone from the reopened page (`123456789` absent), the rest of the page survived |
| Compression | The reported before/after sizes equal the real file sizes on disk; the output is never larger; the result still opens |
| Comments | Highlight, note and rectangle are all read back from the saved file as their real PDF subtypes; the Arabic note text comes back exactly as typed; Arabic free text is refused with a reason; one comment can be deleted |
| Forms | A text field is created; a duplicate name and a choice-less list are refused; the Arabic value is stored and the broken appearance is **declared, not hidden** (`appearance_ok` false); after reopening the value is character-exact; flattening redraws it as real shaped page text and leaves nothing fillable |
| Conversion | Markdown carries the page text; a two-page range produces two numbered PNG files |

## 4. Not done, and not claimed

- Uninstallation has still never been exercised; the application is left
  installed at 1.6.0.
- The binaries are not code-signed.
- No clean-machine test.
- No GUI walk-through of the new tabs by hand: the new features are verified
  headlessly through the packaged binary, not by clicking the ribbon.
- Band 5 (signing) is not started; it needs a real PKCS#12 test certificate
  before any of it can be verified.
