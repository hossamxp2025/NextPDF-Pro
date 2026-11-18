# NextPDF Pro for Android

**Version 0.1.0 — a reader, not the Windows build.**

This is a separate application, not a port. The Windows build is Python with PyQt6
and PyMuPDF; neither runs on Android. What the two share is the **engine** —
MuPDF 1.28, the same family — and the project's rules about saying only what has
been tested. Why it had to be a new application, and what is expected to carry
over, is in [`../docs/ANDROID_PLAN.md`](../docs/ANDROID_PLAN.md).

The version number starts at 0.1.0 deliberately. It is **not** 1.6.1, because it
is nowhere near the Windows build's feature set, and a matching number would
imply that it is.

## What it does

- Opens a PDF chosen through the system document picker, or handed to it by
  another app (`ACTION_VIEW` on `application/pdf`).
- Draws pages with MuPDF, one bitmap per page at the width the zoom asks for, so
  zooming re-renders instead of stretching a bitmap.
- Zoom from fit-width to 800%, capped at a 4096 px bitmap.
- Searches the whole document and jumps to a match.
- Opens a password-protected document: three attempts, and a wrong password is
  told apart from an unreadable file.
- Reports the document's format, page count, encryption and reader permissions.
- Arabic and English interface, with the layout mirroring from the system.

## What it does NOT do

No text editing, no comments, no form filling, no stamping, no encrypting, no
redaction, no Office conversion, no OCR, no printing, no digital signing. The
Windows build does those; this one does not, and the "About" screen says so in
both languages rather than leaving it to be discovered.

## Verified, and not verified

Built on 2026-11-18 with JDK 17.0.21, Android SDK platform 35, Gradle 8.11.1:

| Check | Result |
|---|---|
| `:app:assembleDebug` | **passed** — `app-debug.apk`, 36.81 MB |
| `:app:assembleRelease` (R8 + resource shrinking + lintVital) | **passed** — 29.45 MB unsigned |
| `:app:testDebugUnitTest` | **10 tests, 0 failures** |
| MuPDF native library inside the APK | present for `arm64-v8a` (10.3 MB), `armeabi-v7a` (7.2 MB), `x86_64` (10.7 MB) |
| Manifest in the built APK | `com.futureautomation.nextpdf`, versionName `0.1.0`, minSdk 24, targetSdk 35 |

**Not verified: that it runs.** No Android device or emulator was attached, so the
APK has never been installed, never launched, and no page has ever actually been
drawn on a screen. The instrumented tests that would prove the engine works are
written and have **not been run**. Nothing here should be read as "the app works".

The only permission in the built APK is `DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`,
which AndroidX defines for the app's own broadcast receivers. There is no
`INTERNET` permission and no storage permission.

## Architecture

| Layer | File |
|---|---|
| The only code that touches MuPDF | `app/src/main/java/.../pdf/PdfFile.kt` |
| Zoom arithmetic, pure and JVM-testable | `.../viewer/Zoom.kt` |
| State: opening, locked, ready, failed | `.../viewer/ViewerViewModel.kt` |
| Compose interface | `.../MainActivity.kt` |

**MuPDF objects belong to the thread that made them.** `PdfFile` therefore owns a
single-threaded executor and opens the document on it, and every later call is
funnelled through the same thread. This is not a performance choice; calling the
engine from two threads is a native crash.

The whole file is read into memory, and a file over 64 MB is refused with a
reason. A streaming reader (`SeekableInputStream`) is the right fix and is not
done yet.

## Building

Needs **JDK 17** and an **Android SDK** with platform 35 and build-tools 35.0.0.
`local.properties` holds this machine's SDK path and is not committed; create it
with one line:

```
sdk.dir=C\:\\path\\to\\Android\\Sdk
```

```bash
cd android
./gradlew :app:assembleDebug          # debug APK
./gradlew :app:testDebugUnitTest      # JVM tests, no device needed
./gradlew :app:connectedDebugAndroidTest   # needs a device or emulator
```

The debug APK lands in `app/build/outputs/apk/debug/`.

## Testing

- `app/src/test/` — runs on the JVM. Covers the zoom and render-width arithmetic.
- `app/src/androidTest/` — **needs a real device or an emulator**, because MuPDF
  is a native library. It builds the PDFs it reads from bytes, so it depends on no
  file on the machine, and covers opening, page count, rendering at a requested
  width, reading text back, search positions, and refusing bytes that are not a
  document.

## Licence

GNU AGPL v3.0, the same as the rest of the project. The MuPDF JNI bindings
(`com.artifex.mupdf:fitz`) are Artifex's and are also AGPL v3, which is why they
can be used here.
