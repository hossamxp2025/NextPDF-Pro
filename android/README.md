# NextPDF Pro for Android

**Version 0.2.1 — it now changes documents, and it is still not the Windows build.**

This is a separate application, not a port. The Windows build is Python with PyQt6
and PyMuPDF; neither runs on Android. What the two share is the **engine** —
MuPDF 1.28, the same family — and the project's rules about saying only what has
been tested. Why it had to be a new application, and what is expected to carry
over, is in [`../docs/ANDROID_PLAN.md`](../docs/ANDROID_PLAN.md).

The version number is 0.2.1 and not 1.6.1 on purpose. It is still well short of
the Windows build's feature set, and a matching number would imply otherwise.

## What it does

Reading:

- Opens a PDF from the system document picker or from another app (`ACTION_VIEW`).
- Draws pages with MuPDF, one bitmap per page at the width the zoom asks for, so
  zooming re-renders instead of stretching a bitmap. Fit-width to 800%, capped at
  a 4096 px bitmap.
- Searches the whole document; matches become chips that jump to the page.
- Page thumbnails, previous/next, and go-to-page by number.
- Night reading: the page is drawn inverted on screen. The file is not touched.
- Opens a password-protected document: three attempts, and a wrong password is
  told apart from an unreadable file.
- Reports format, page count, encryption and reader permissions.
- Arabic and English, with the layout and the navigation arrows mirroring from the
  system.

The page, zoom and tool controls sit in a row **under the title bar**, not at the
foot of the screen. On a phone with on-screen navigation buttons the foot of the
screen belongs to the system, and controls placed there cannot be pressed. The
navigation bar itself is hidden while the app is open and comes back for as long
as it is needed when swiped up from the bottom edge.

Changing (new in 0.2.0):

- Turn a page left or right; remove a page.
- Save a copy, or compress and save — the result reports its size against the
  original rather than claiming "compressed".
- Protect with an **AES-256** password, or remove the password from a file that
  has one.
- Save the page on screen as a PNG.
- Copy the page's text to the clipboard — real text, not a picture.
- Share the document with another app, or print it through Android's own printer.

**Edits are made to the copy in memory.** The file the user picked is never
written to. Saving always writes a **new** file to a place the user chooses, so a
mistake costs nothing.

## What it does NOT do

No text editing inside a page, no comments or highlights, no form filling, no
stamping, no redaction, no Office conversion, no OCR, no digital signing. The
Windows build does those; this one does not, and the "About" screen says so in
both languages rather than leaving it to be discovered.

## What 0.2.1 fixed

0.2.0 was run on a real phone. Three things were wrong and are fixed here:

- **The icon was not the program's icon.** It is now, and the artwork itself was
  repaired: the "PDF" and "Pro" lettering in `NextPDF-Pro.svg` was drawn as
  solid shapes whose paths were malformed, so both words rendered as unreadable
  blobs on Windows as well. They are drawn as strokes now, and every desktop
  size and the `.ico` were regenerated from the corrected drawing.
- **The controls could not be pressed**, because the bar holding them sat on top
  of the phone's navigation buttons. They moved under the title bar.
- **The page counter read backwards in Arabic** — "1 / 7" came out as "7 / 1",
  because a slash between two numbers is a neutral character and takes the
  paragraph's direction. The counter is wrapped in a left-to-right isolate.

## Verified, and not verified

Built on 2026-11-19 with JDK 17.0.21, Android SDK platform 35, Gradle 8.11.1:

| Check | Result |
|---|---|
| `:app:assembleDebug` | **passed** — `app-debug.apk`, 43.67 MB |
| `:app:assembleRelease` (R8 + resource shrinking + lintVital) | **passed** — 29.75 MB unsigned at 0.2.0 |
| `:app:testDebugUnitTest` | **23 tests, 0 failures** (zoom arithmetic, save options, permission bits) |
| Manifest in the built APK | `com.futureautomation.nextpdf`, versionName `0.2.1`, versionCode 3, minSdk 24, targetSdk 35 |
| Launcher icon in the built APK | legacy, round and adaptive-foreground PNGs at all five densities |

0.2.0 was installed and opened on a phone and drew its pages correctly, which is
the first time any of this was seen running. That is the whole of what has been
seen.

**Not verified: that the rest of it runs.** There is still no Android device or
emulator attached to the machine this is built on, so nothing below has been
executed even once:

- the new tools — rotate, delete, compress, protect, unprotect, export, share,
  print — have **never been run against a real document**;
- MuPDF's writer options (`encrypt=aes-256`, `compress-images`, `garbage=compact`)
  are taken from the engine's documented option set and have **not** been proved
  against this build of the engine. If one is rejected the save fails with the
  "could not be written" message rather than producing a broken file, but that
  path is also untested;
- the instrumented tests that would prove the engine works are written and have
  **not been run**.

Nothing here should be read as "the app works".

## Architecture

| Layer | File |
|---|---|
| The only code that touches MuPDF | `app/src/main/java/.../pdf/PdfFile.kt` |
| Writer options and permission bits, pure and JVM-testable | `.../pdf/SaveOptions.kt` |
| Zoom arithmetic, pure and JVM-testable | `.../viewer/Zoom.kt` |
| State, tasks, saving | `.../viewer/ViewerViewModel.kt` |
| Compose interface | `.../MainActivity.kt` |
| Handing a file to the printer | `.../print/PdfPrintAdapter.kt` |

**MuPDF objects belong to the thread that made them.** `PdfFile` therefore owns a
single-threaded executor and opens the document on it, and every later call is
funnelled through the same thread. This is not a performance choice; calling the
engine from two threads is a native crash.

MuPDF's writer takes a path, not a stream, so a save is written into the app's
cache and then copied into the location the user picked. Its options are a
comma-separated list, which is why a password containing a comma is **refused**
with a reason instead of being cut in half.

The whole file is read into memory, and a file over 64 MB is refused with a
reason. A streaming reader (`SeekableInputStream`) is the right fix and is not
done yet.

## Permissions

The app declares none. The merged APK carries AndroidX's
`DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`, which AndroidX defines for an app's
own broadcast receivers. There is no `INTERNET` permission and no storage
permission: files arrive through the system picker, and the only thing another
app can read is a copy the user asked to share, through a `FileProvider` scoped
to one cache folder.

## The icon

The launcher icon is the desktop icon. `resources/icons/NextPDF-Pro-512.png` is
resized for the legacy icons, and the same artwork with its red backdrop lifted
out becomes the adaptive foreground over a red background drawable, so the shape
survives whatever mask the phone applies.

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

- `app/src/test/` — runs on the JVM. Covers the zoom and render-width arithmetic,
  the writer option strings and the PDF permission bitfield.
- `app/src/androidTest/` — **needs a real device or an emulator**, because MuPDF
  is a native library. It builds the PDFs it reads from bytes, so it depends on no
  file on the machine, and covers opening, page count, rendering at a requested
  width, reading text back, search positions, and refusing bytes that are not a
  document.

## Licence

GNU AGPL v3.0, the same as the rest of the project. The MuPDF JNI bindings
(`com.artifex.mupdf:fitz`) are Artifex's and are also AGPL v3, which is why they
can be used here.
