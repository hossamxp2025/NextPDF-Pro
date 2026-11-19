/*
 * The option strings MuPDF's PDF writer takes.
 *
 * MuPDF parses these as a comma-separated list of key=value pairs, which has one
 * consequence worth stating plainly: a password containing a comma would be cut
 * in half and the file would be written with a password nobody could type. Rather
 * than silently mangling it, [PasswordRule] refuses such a password and the
 * interface says why.
 *
 * This file is deliberately free of Android and of MuPDF types, so the strings it
 * builds can be tested on the JVM without a device.
 */
package com.futureautomation.nextpdf.pdf

/** Why a password cannot be used, or that it can. */
enum class PasswordRule {
    OK,
    EMPTY,
    HAS_COMMA,
    TOO_LONG,
}

/** PDF's own limit for the classic password; AES-256 allows more, this is the safe floor. */
const val MAX_PASSWORD_LENGTH = 32

fun checkPassword(password: String): PasswordRule = when {
    password.isEmpty() -> PasswordRule.EMPTY
    password.contains(',') -> PasswordRule.HAS_COMMA
    password.length > MAX_PASSWORD_LENGTH -> PasswordRule.TOO_LONG
    else -> PasswordRule.OK
}

/** What the reader of the saved file is allowed to do. */
data class Permissions(
    val mayPrint: Boolean = true,
    val mayCopy: Boolean = true,
    val mayEdit: Boolean = true,
    val mayAnnotate: Boolean = true,
) {
    /**
     * The PDF permission bitfield. Bits 1-2 are reserved and must be set, so the
     * base is 0xFFFFFFFC with the bits that are denied cleared. The bit numbers
     * are PDF's own, counted from 1: print 3, edit 4, copy 5, annotate 6.
     */
    fun toBitfield(): Int {
        var bits = -4 // 0xFFFFFFFC: everything allowed, reserved low bits set
        if (!mayPrint) bits = bits and (1 shl 2).inv()
        if (!mayEdit) bits = bits and (1 shl 3).inv()
        if (!mayCopy) bits = bits and (1 shl 4).inv()
        if (!mayAnnotate) bits = bits and (1 shl 5).inv()
        return bits
    }
}

object SaveOptions {

    /** A straight copy: no re-encoding, no change of encryption. */
    fun plainCopy(): String = "garbage=compact"

    /** Rewrites the file smaller. Nothing is removed from the page content. */
    fun compressed(): String = "compress,compress-images,compress-fonts,garbage=compact"

    /**
     * Writes the file encrypted with AES-256. Both passwords are set to the same
     * value, because a file whose owner password differs is one the user can open
     * but cannot change, and this app offers no way to tell them apart later.
     */
    fun protected(password: String, permissions: Permissions = Permissions()): String {
        require(checkPassword(password) == PasswordRule.OK) { "password rejected by checkPassword" }
        return listOf(
            "compress",
            "garbage=compact",
            "encrypt=aes-256",
            "user-password=$password",
            "owner-password=$password",
            "permissions=${permissions.toBitfield()}",
        ).joinToString(",")
    }

    /** Writes the file with no encryption at all. The document must already be unlocked. */
    fun unprotected(): String = "compress,garbage=compact,encrypt=none"
}
