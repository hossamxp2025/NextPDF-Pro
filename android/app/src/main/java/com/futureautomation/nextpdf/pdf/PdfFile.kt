/*
 * NextPDF Pro for Android — a thin, honest wrapper over the MuPDF engine.
 *
 * This file is the only place that touches MuPDF. Two facts shape it:
 *
 *  1. MuPDF objects belong to the thread that created them. Every call below is
 *     therefore funnelled through one single-threaded executor, and the document
 *     is opened on that same thread. Calling into the engine from two threads is
 *     not slow, it is a native crash.
 *  2. MuPDF reports failure by throwing RuntimeException from native code. The
 *     wrapper never swallows one silently; the caller is told what failed.
 *
 * The engine is the same MuPDF family (1.28) that the desktop build uses, under
 * the same AGPL v3 licence as this project.
 */
package com.futureautomation.nextpdf.pdf

import android.graphics.Bitmap
import com.artifex.mupdf.fitz.Document
import com.artifex.mupdf.fitz.PDFDocument
import com.artifex.mupdf.fitz.PDFPage
import com.artifex.mupdf.fitz.Quad
import com.artifex.mupdf.fitz.android.AndroidDrawDevice
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.withContext
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import com.artifex.mupdf.fitz.Context as FitzContext

/** A rectangle on a page, in fractions of the page box (0..1), origin top-left. */
data class PageRegion(
    val left: Float,
    val top: Float,
    val right: Float,
    val bottom: Float,
)

/** What the document says about itself. Absent values stay null rather than guessing. */
data class DocumentInfo(
    val format: String?,
    val encryption: String?,
    val title: String?,
    val isPdf: Boolean,
    val isEncrypted: Boolean,
    val mayPrint: Boolean,
    val mayCopy: Boolean,
    val mayEdit: Boolean,
    val mayAnnotate: Boolean,
)

/** One search match: which page, and where on it. */
data class SearchHit(val pageIndex: Int, val region: PageRegion)

class PdfFile private constructor(
    private val executor: ExecutorService,
    private val dispatcher: CoroutineDispatcher,
    private val document: Document,
) {
    private var closed = false

    /** True while the document has not been unlocked yet. */
    suspend fun needsPassword(): Boolean = withContext(dispatcher) { document.needsPassword() }

    /** Returns true when the password was accepted. A wrong password is not an error. */
    suspend fun authenticate(password: String): Boolean =
        withContext(dispatcher) { document.authenticatePassword(password) }

    /**
     * The number of pages. Only call this after the document is unlocked: MuPDF
     * cannot count the pages of a document it cannot decrypt.
     */
    suspend fun pageCount(): Int = withContext(dispatcher) { document.countPages() }

    /** Page width divided by page height, for laying a page out before it is drawn. */
    suspend fun pageAspectRatio(index: Int): Float = withContext(dispatcher) {
        val page = document.loadPage(index)
        try {
            val bounds = page.bounds
            val width = bounds.x1 - bounds.x0
            val height = bounds.y1 - bounds.y0
            if (width > 0f && height > 0f) width / height else 1f
        } finally {
            page.destroy()
        }
    }

    /**
     * Draws one page into a bitmap [widthPx] pixels wide. The caller decides the
     * width, so zoom is a render at a larger width rather than a stretched bitmap.
     */
    suspend fun renderPage(index: Int, widthPx: Int): Bitmap = withContext(dispatcher) {
        require(widthPx > 0) { "A page cannot be drawn into a bitmap of width $widthPx" }
        val page = document.loadPage(index)
        try {
            AndroidDrawDevice.drawPageFitWidth(page, widthPx)
        } finally {
            page.destroy()
        }
    }

    /** The page's text, in logical order. Arabic comes back as Unicode, not glyph codes. */
    suspend fun pageText(index: Int): String = withContext(dispatcher) {
        val page = document.loadPage(index)
        try {
            val text = page.toStructuredText()
            try {
                text.asText() ?: ""
            } finally {
                text.destroy()
            }
        } finally {
            page.destroy()
        }
    }

    /** Every match of [needle] on one page, at most [limit] of them. */
    suspend fun searchPage(index: Int, needle: String, limit: Int = 64): List<PageRegion> =
        withContext(dispatcher) {
            if (needle.isBlank()) return@withContext emptyList()
            val page = document.loadPage(index)
            try {
                val bounds = page.bounds
                val width = bounds.x1 - bounds.x0
                val height = bounds.y1 - bounds.y0
                if (width <= 0f || height <= 0f) return@withContext emptyList()
                val hits = page.search(needle) ?: return@withContext emptyList()
                hits.asSequence()
                    .filterNotNull()
                    .filter { it.isNotEmpty() }
                    .map { quads -> quads.boundingRegion(bounds.x0, bounds.y0, width, height) }
                    .take(limit)
                    .toList()
            } finally {
                page.destroy()
            }
        }

    suspend fun info(): DocumentInfo = withContext(dispatcher) {
        val encryption = document.getMetaData(Document.META_ENCRYPTION)
        DocumentInfo(
            format = document.getMetaData(Document.META_FORMAT),
            encryption = encryption,
            title = document.getMetaData(Document.META_INFO_TITLE)?.takeIf { it.isNotBlank() },
            isPdf = document.isPDF,
            // isUnencryptedPDF() answers for PDFs; anything else is reported as not encrypted.
            isEncrypted = document.isPDF && !document.isUnencryptedPDF,
            mayPrint = document.hasPermission(Document.PERMISSION_PRINT),
            mayCopy = document.hasPermission(Document.PERMISSION_COPY),
            mayEdit = document.hasPermission(Document.PERMISSION_EDIT),
            mayAnnotate = document.hasPermission(Document.PERMISSION_ANNOTATE),
        )
    }

    // ---------------------------------------------------------------------
    // Changing the document. Everything below needs a PDF; a document in any
    // other format throws [NotAPdf] rather than quietly doing nothing.
    // ---------------------------------------------------------------------

    /** Thrown when an edit is asked of a document that is not a PDF. */
    class NotAPdf : RuntimeException("this document is not a PDF, so it cannot be edited")

    private fun pdf(): PDFDocument = document.asPDF() ?: throw NotAPdf()

    /**
     * The page's stored /Rotate value, normalised to 0, 90, 180 or 270.
     *
     * A page that inherits its rotation from the page tree rather than carrying
     * its own reports 0 here. That is rare, and the cost is only that the first
     * turn of such a page starts counting from zero.
     */
    suspend fun pageRotation(index: Int): Int = withContext(dispatcher) {
        val page = pdf().loadPage(index) as PDFPage
        try {
            val stored = page.`object`.get("Rotate")
            val degrees = if (stored != null && stored.isInteger) stored.asInteger() else 0
            ((degrees % 360) + 360) % 360
        } finally {
            page.destroy()
        }
    }

    /** Turns one page by [byDegrees] (a multiple of 90) and leaves it unsaved. */
    suspend fun rotatePage(index: Int, byDegrees: Int) = withContext(dispatcher) {
        val page = pdf().loadPage(index) as PDFPage
        try {
            val stored = page.`object`.get("Rotate")
            val current = if (stored != null && stored.isInteger) stored.asInteger() else 0
            val turned = (((current + byDegrees) % 360) + 360) % 360
            page.`object`.put("Rotate", turned)
        } finally {
            page.destroy()
        }
    }

    /** Removes one page. The caller is responsible for not removing the last one. */
    suspend fun deletePage(index: Int) = withContext(dispatcher) {
        pdf().deletePage(index)
    }

    /**
     * Rebuilds the document from [order], a list of the pages to keep in the order
     * to keep them. Pages left out are dropped, and a page may appear twice.
     */
    suspend fun rearrangePages(order: IntArray) = withContext(dispatcher) {
        require(order.isNotEmpty()) { "a document cannot be left with no pages" }
        pdf().rearrangePages(order)
    }

    /** True when an edit has been made that is not yet in any saved file. */
    suspend fun hasUnsavedChanges(): Boolean = withContext(dispatcher) {
        try {
            pdf().hasUnsavedChanges()
        } catch (_: NotAPdf) {
            false
        }
    }

    /**
     * Writes the whole document to [path] with MuPDF's own writer options, which
     * [SaveOptions] builds. This writes a new file; the document in memory and the
     * file it came from are untouched.
     */
    suspend fun saveTo(path: String, options: String) = withContext(dispatcher) {
        pdf().save(path, options)
    }

    /** Draws a page to fit inside a box, for thumbnails. */
    suspend fun renderPageFit(index: Int, widthPx: Int, heightPx: Int): Bitmap =
        withContext(dispatcher) {
            require(widthPx > 0 && heightPx > 0) { "thumbnail box must have a size" }
            val page = document.loadPage(index)
            try {
                AndroidDrawDevice.drawPageFit(page, widthPx, heightPx)
            } finally {
                page.destroy()
            }
        }

    /** Releases the native document and the thread that owned it. Safe to call twice. */
    suspend fun close() {
        if (closed) return
        closed = true
        try {
            withContext(dispatcher) { document.destroy() }
        } finally {
            executor.shutdown()
        }
    }

    companion object {
        /**
         * Opens a document held in memory. [magic] is the file name or MIME type that
         * tells MuPDF which format to expect.
         *
         * A document that needs a password still opens; [needsPassword] then reports
         * it. A document MuPDF cannot read at all throws.
         */
        suspend fun open(bytes: ByteArray, magic: String): PdfFile {
            val executor = Executors.newSingleThreadExecutor { runnable ->
                Thread(runnable, "nextpdf-mupdf").apply { isDaemon = true }
            }
            val dispatcher = executor.asCoroutineDispatcher()
            return try {
                val document = withContext(dispatcher) {
                    FitzContext.init()
                    Document.openDocument(bytes, magic)
                }
                PdfFile(executor, dispatcher, document)
            } catch (error: Throwable) {
                executor.shutdown()
                throw error
            }
        }
    }
}

/** The smallest page-fraction rectangle covering every quad of one match. */
private fun Array<Quad>.boundingRegion(
    originX: Float,
    originY: Float,
    width: Float,
    height: Float,
): PageRegion {
    var minX = Float.MAX_VALUE
    var minY = Float.MAX_VALUE
    var maxX = -Float.MAX_VALUE
    var maxY = -Float.MAX_VALUE
    for (quad in this) {
        val xs = floatArrayOf(quad.ul_x, quad.ur_x, quad.ll_x, quad.lr_x)
        val ys = floatArrayOf(quad.ul_y, quad.ur_y, quad.ll_y, quad.lr_y)
        for (x in xs) {
            if (x < minX) minX = x
            if (x > maxX) maxX = x
        }
        for (y in ys) {
            if (y < minY) minY = y
            if (y > maxY) maxY = y
        }
    }
    return PageRegion(
        left = ((minX - originX) / width).coerceIn(0f, 1f),
        top = ((minY - originY) / height).coerceIn(0f, 1f),
        right = ((maxX - originX) / width).coerceIn(0f, 1f),
        bottom = ((maxY - originY) / height).coerceIn(0f, 1f),
    )
}
