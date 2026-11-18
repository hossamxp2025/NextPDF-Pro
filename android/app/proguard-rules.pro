# MuPDF is reached over JNI: the native library looks these classes, their fields
# and their constructors up by name. R8 cannot see those references, so without
# this the release build would strip them and the first page render would crash.
-keep class com.artifex.mupdf.fitz.** { *; }
-keep class com.artifex.mupdf.fitz.android.** { *; }
-keepclasseswithmembernames class com.artifex.mupdf.fitz.** {
    native <methods>;
}

# Kotlin coroutines' service loader metadata.
-dontwarn kotlinx.coroutines.**
