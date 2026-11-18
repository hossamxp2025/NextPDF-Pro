# NextPDF Pro 1.6.1 — release record

Build: **1.6.1** / `20261118-0940`
Date: 2026-11-18
Scope: the first half of band 5 of `docs/ROADMAP_1.5.md` — the visible stamp.
The digital signature itself is **not** in this release.

## 1. What is in this release

Everything in 1.6.0, plus a "Visible stamp" group in the Protect and Sign tab:
an image stamp, a typed-name stamp, and a "What a stamp is not" button.

- The stamp is **page content, not an annotation**: every reader sees it, it
  prints, no reader can switch it off, and an ordinary save keeps it.
- The image keeps its proportions and is centred in the dragged area; the
  rectangle reported back is the area actually drawn into, not the area asked
  for. Stretching is available as an explicit choice.
- The white background of a signature scanned on white paper can be dropped.
  Only the alpha channel is touched, so no stroke is thinned, lightened or
  redrawn.
- The typed name is drawn through the project's text engine, which embeds a
  font that shapes Arabic, so an Arabic name renders correctly in any reader
  and stays searchable.
- A stray click, a missing image, a file that is not an image and an empty
  name are each refused with the reason, and nothing is drawn.
- Every stamp goes through the snapshot command, so each one undoes.

**A visible stamp is not a digital signature.** It proves nothing about who
placed it, detects no later change to the file, and the picture can be copied
into another file. The sentence lives in the header of `src/engine/stamps.py`,
in the "What a stamp is not" button in both languages, and in
`KNOWN_LIMITATIONS.md`; a test fails if it disappears from any of them.

## 2. Artifacts

Folder: `dist/release-1.6.1/` (not committed; rebuild with
`python build/build_exe.py` then `python build/build_exe.py --installer`)

| File | Size (bytes) | SHA-256 |
|---|---|---|
| `NextPDF-Pro.exe` | 92,978,158 | `883eb53a87c5943e1b7180473162175dc931311b1c17f4ac7fcdf4e51c2e79c1` |
| `NextPDF-Pro-Setup-1.6.1.exe` | 95,034,553 | `7fcf2bf491d7eaf64da4d7f40253e478b7af125d1bfd606284f9e1fd3efc73be` |

`dist/release-1.6.0/` was left untouched.

## 3. Verification performed

`--verify-release` grew from 71 checks to **81**: ten of them exercise the
stamp inside the packaged application, against a file written and then
reopened.

| Check | Result | Evidence |
|---|---|---|
| Full pytest suite | **512 passed, 0 failed** (162.8 s) | `tests/`, run on the source before the build |
| Packaged `--version` | `NextPDF Pro 1.6.1 (build 20261118-0940)`, exit 0 | `docs/evidence/version-1.6.1.txt` |
| Packaged `--self-test` | PASS, 0 failures | `docs/evidence/selftest-1.6.1.txt` |
| Packaged `--smoke-gui` | PASS | `docs/evidence/smoke-gui-1.6.1.txt` |
| Packaged `--verify-release` | **81/81 PASS**, `"frozen": true`, executable = the released EXE | `docs/evidence/verify-1.6.1/report.json` |
| Source `--verify-release` | 81/81 PASS, `"frozen": false`, run before the build | — |
| Installer | Compiled with Inno Setup 6 | build log |
| Installation | `/VERYSILENT /CURRENTUSER`, exit 0; upgraded the installed 1.6.0 in place at `%LOCALAPPDATA%\Programs\NextPDF Pro`; `VERSION.txt` reads 1.6.1 / `20261118-0940` and the uninstall entry reads `1.6.1` | `docs/evidence/install-1.6.1.log` (local; `.log` is git-ignored) |
| Installed binary integrity | SHA-256 of the installed `NextPDF-Pro.exe` equals the released hash `883eb53a…1c2e79c1` | — |
| Installed `--version` | `NextPDF Pro 1.6.1 (build 20261118-0940)`, exit 0 | `docs/evidence/version-1.6.1-installed.txt` |
| Installed `--self-test` | PASS, 0 failures | `docs/evidence/selftest-1.6.1-installed.txt` |
| Installed `--smoke-gui` | PASS | `docs/evidence/smoke-gui-1.6.1-installed.txt` |
| Installed `--verify-release` | **81/81 PASS**, `"frozen": true`, executable = `%LOCALAPPDATA%\Programs\NextPDF Pro\NextPDF-Pro.exe` | `docs/evidence/verify-1.6.1-installed/report.json` |

As with 1.5.0 and 1.6.0, the silent install reused the remembered task choices:
no Start Menu group, and the desktop shortcut refreshed to the 1.6.1 binary.

What the ten new packaged checks prove: the image is placed and its
proportions are kept (measured 2:1 in a square area); the typed Arabic name is
real searchable text in the saved file; the saved page carries **no annotation
and no form field**, so a stamp cannot be mistaken for a signature anywhere in
the file; the dropped white background shows the red page through it while the
stroke stays black (read back pixel by pixel); and a stray click and a missing
image are refused.

## 4. Not done, and not claimed

- **The digital signature is not implemented.** No PKCS#12, no verification,
  nothing in the interface that claims to sign. It needs a real test
  certificate first.
- Moving, resizing or rotating a stamp after it is placed, and repeating it
  across every page in one step, are not implemented.
- Uninstallation has still never been exercised; the application is left
  installed at 1.6.1.
- The binaries are not code-signed.
- No clean-machine test.
- No GUI walk-through by hand; the stamp is verified headlessly through the
  packaged binary and through the UI tests, which drive the real window.
