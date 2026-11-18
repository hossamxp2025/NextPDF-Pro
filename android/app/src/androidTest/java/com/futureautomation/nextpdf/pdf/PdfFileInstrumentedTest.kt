/*
 * These need a real device or emulator: MuPDF is a native library, so none of this
 * can run in a JVM unit test. They build the PDFs they read from bytes, so they do
 * not depend on any file on the machine.
 *
 * Run with:  gradlew :app:connectedDebugAndroidTest
 */
package com.futureautomation.nextpdf.pdf

import androidx.test.ext.junit.runners.AndroidJUnit4
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PdfFileInstrumentedTest {

    @Test
    fun opens_a_plain_pdf_and_counts_its_pages() = runBlocking {
        val file = PdfFile.open(onePagePdf(), "test.pdf")
        try {
            assertFalse(file.needsPassword())
            assertEquals(1, file.pageCount())
        } finally {
            file.close()
        }
    }

    @Test
    fun renders_a_page_at_the_width_it_was_asked_for() = runBlocking {
        val file = PdfFile.open(onePagePdf(), "test.pdf")
        try {
            val bitmap = file.renderPage(0, 600)
            assertEquals(600, bitmap.width)
            assertTrue("the page should have some height", bitmap.height > 0)
        } finally {
            file.close()
        }
    }

    @Test
    fun reads_the_text_of_a_page_back() = runBlocking {
        val file = PdfFile.open(onePagePdf(), "test.pdf")
        try {
            assertTrue(file.pageText(0).contains("NextPDF"))
        } finally {
            file.close()
        }
    }

    @Test
    fun finds_text_and_reports_where_it_sits_on_the_page() = runBlocking {
        val file = PdfFile.open(onePagePdf(), "test.pdf")
        try {
            val regions = file.searchPage(0, "NextPDF")
            assertTrue("the word should be found", regions.isNotEmpty())
            val region = regions.first()
            assertTrue(region.left in 0f..1f && region.right in 0f..1f)
            assertTrue(region.right > region.left)
            assertTrue(region.bottom > region.top)
        } finally {
            file.close()
        }
    }

    @Test
    fun a_blank_search_finds_nothing_rather_than_everything() = runBlocking {
        val file = PdfFile.open(onePagePdf(), "test.pdf")
        try {
            assertTrue(file.searchPage(0, "   ").isEmpty())
        } finally {
            file.close()
        }
    }

    @Test
    fun reports_the_document_as_a_pdf_that_is_not_encrypted() = runBlocking {
        val file = PdfFile.open(onePagePdf(), "test.pdf")
        try {
            val info = file.info()
            assertTrue(info.isPdf)
            assertFalse(info.isEncrypted)
        } finally {
            file.close()
        }
    }

    @Test(expected = RuntimeException::class)
    fun refuses_bytes_that_are_not_a_document() {
        runBlocking {
            PdfFile.open("this is not a PDF at all".toByteArray(), "test.pdf")
        }
    }

    @Test
    fun closing_twice_is_not_an_error() = runBlocking {
        val file = PdfFile.open(onePagePdf(), "test.pdf")
        file.close()
        file.close()
    }

    /**
     * The smallest hand-written PDF that carries real text, so the test needs no
     * asset file and no fixture on disk.
     */
    private fun onePagePdf(): ByteArray {
        val objects = mutableListOf<String>()
        objects += "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        objects += "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        objects += "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] " +
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n"
        val content = "BT /F1 24 Tf 72 700 Td (NextPDF Pro) Tj ET\n"
        objects += "4 0 obj\n<< /Length ${content.length} >>\nstream\n$content" +
            "endstream\nendobj\n"
        objects += "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

        val header = "%PDF-1.4\n"
        val builder = StringBuilder(header)
        val offsets = mutableListOf<Int>()
        for (entry in objects) {
            offsets += builder.length
            builder.append(entry)
        }
        val xrefPosition = builder.length
        builder.append("xref\n0 ${objects.size + 1}\n")
        builder.append("0000000000 65535 f \n")
        for (offset in offsets) {
            builder.append(offset.toString().padStart(10, '0')).append(" 00000 n \n")
        }
        builder.append(
            "trailer\n<< /Size ${objects.size + 1} /Root 1 0 R >>\n" +
                "startxref\n$xrefPosition\n%%EOF\n",
        )
        return builder.toString().toByteArray(Charsets.ISO_8859_1)
    }
}
