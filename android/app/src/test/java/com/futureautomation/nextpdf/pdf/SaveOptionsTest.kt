package com.futureautomation.nextpdf.pdf

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * These run on the JVM, with no device and no engine. They cover the one part of
 * saving that can be got wrong silently: the option string handed to MuPDF and
 * the permission bitfield inside it.
 */
class SaveOptionsTest {

    @Test
    fun `an empty password is refused`() {
        assertEquals(PasswordRule.EMPTY, checkPassword(""))
    }

    @Test
    fun `a password with a comma is refused because the option list is comma separated`() {
        assertEquals(PasswordRule.HAS_COMMA, checkPassword("one,two"))
    }

    @Test
    fun `a password longer than the limit is refused`() {
        assertEquals(PasswordRule.TOO_LONG, checkPassword("x".repeat(MAX_PASSWORD_LENGTH + 1)))
    }

    @Test
    fun `a password at the limit is accepted`() {
        assertEquals(PasswordRule.OK, checkPassword("x".repeat(MAX_PASSWORD_LENGTH)))
    }

    @Test
    fun `an Arabic password is accepted`() {
        assertEquals(PasswordRule.OK, checkPassword("كلمة-المرور"))
    }

    @Test
    fun `protecting asks for AES-256 and sets both passwords`() {
        val options = SaveOptions.protected("hunter2")
        assertTrue(options.contains("encrypt=aes-256"))
        assertTrue(options.contains("user-password=hunter2"))
        assertTrue(options.contains("owner-password=hunter2"))
    }

    @Test
    fun `removing protection asks for no encryption`() {
        assertTrue(SaveOptions.unprotected().contains("encrypt=none"))
    }

    @Test
    fun `a plain copy neither compresses images nor changes encryption`() {
        val options = SaveOptions.plainCopy()
        assertFalse(options.contains("encrypt"))
        assertFalse(options.contains("compress-images"))
    }

    @Test
    fun `compressing asks for the image and font passes`() {
        val options = SaveOptions.compressed()
        assertTrue(options.contains("compress-images"))
        assertTrue(options.contains("compress-fonts"))
        assertFalse(options.contains("encrypt"))
    }

    @Test
    fun `everything allowed leaves the reserved low bits set`() {
        assertEquals(-4, Permissions().toBitfield())
    }

    @Test
    fun `denying printing clears bit three and nothing else`() {
        val denied = Permissions(mayPrint = false).toBitfield()
        assertEquals(0, denied and (1 shl 2))
        assertEquals(1 shl 3, denied and (1 shl 3))
        assertEquals(1 shl 4, denied and (1 shl 4))
        assertEquals(1 shl 5, denied and (1 shl 5))
    }

    @Test
    fun `denying copying clears bit five`() {
        val denied = Permissions(mayCopy = false).toBitfield()
        assertEquals(0, denied and (1 shl 4))
        assertEquals(1 shl 2, denied and (1 shl 2))
    }

    @Test
    fun `the permissions value reaches the option string`() {
        val options = SaveOptions.protected("pw", Permissions(mayPrint = false))
        assertTrue(options.contains("permissions=${Permissions(mayPrint = false).toBitfield()}"))
    }
}
