package com.futureautomation.nextpdf.viewer

import android.app.Application
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import android.provider.OpenableColumns
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.futureautomation.nextpdf.pdf.DocumentInfo
import com.futureautomation.nextpdf.pdf.PasswordRule
import com.futureautomation.nextpdf.pdf.PdfFile
import com.futureautomation.nextpdf.pdf.Permissions
import com.futureautomation.nextpdf.pdf.SaveOptions
import com.futureautomation.nextpdf.pdf.SearchHit
import com.futureautomation.nextpdf.pdf.checkPassword
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

/** How many wrong passwords are allowed before the document is given up on. */
const val PASSWORD_ATTEMPTS = 3

/** Files larger than this are refused with a reason rather than risking an OOM kill. */
const val MAX_FILE_BYTES = 64L * 1024L * 1024L

/** The width a page is drawn at when it is exported as an image. */
const val EXPORT_IMAGE_WIDTH_PX = 2000

sealed interface ViewerState {
    data object Empty : ViewerState
    data object Opening : ViewerState
    data class NeedsPassword(val attemptsLeft: Int, val lastWasWrong: Boolean) : ViewerState
    data class Ready(val name: String, val pageCount: Int, val info: DocumentInfo) : ViewerState
    data class Failed(val reason: Failure) : ViewerState
}

/** Why opening failed. Each value maps to one message; none of them is "unknown error". */
enum class Failure {
    UNREADABLE,
    TOO_LARGE,
    WRONG_PASSWORD_TOO_OFTEN,
    NO_PAGES,
    CANNOT_READ_FILE,
}

/** What a save is meant to produce. The file on disk is never changed in place. */
enum class SaveKind {
    COPY,
    COMPRESSED,
    PROTECTED,
    UNPROTECTED,
    PAGE_IMAGE,
}

/** Why a task did not finish. Like [Failure], every value names a real cause. */
enum class TaskFailure {
    NOT_A_PDF,
    SAVE_FAILED,
    EXPORT_FAILED,
    LAST_PAGE,
    NO_TEXT,
    NOT_ENCRYPTED,
    PASSWORD_EMPTY,
    PASSWORD_HAS_COMMA,
    PASSWORD_TOO_LONG,
}

/** The one-off message shown after a task, as data rather than a pre-built string. */
sealed interface Notice {
    data class Saved(val name: String, val bytes: Long, val wasBytes: Long?) : Notice
    data class ImageSaved(val name: String) : Notice
    data class TextCopied(val characters: Int) : Notice
    data class PageDeleted(val pageNumber: Int) : Notice
    data class Rotated(val degrees: Int) : Notice
    data class Problem(val reason: TaskFailure) : Notice
}

class ViewerViewModel(application: Application) : AndroidViewModel(application) {

    private val _state = MutableStateFlow<ViewerState>(ViewerState.Empty)
    val state: StateFlow<ViewerState> = _state.asStateFlow()

    private val _zoom = MutableStateFlow(MIN_ZOOM)
    val zoom: StateFlow<Float> = _zoom.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _searchHits = MutableStateFlow<List<SearchHit>>(emptyList())
    val searchHits: StateFlow<List<SearchHit>> = _searchHits.asStateFlow()

    private val _searching = MutableStateFlow(false)
    val searching: StateFlow<Boolean> = _searching.asStateFlow()

    /** Set when the viewer should scroll to a page; cleared once the UI has done it. */
    private val _scrollTo = MutableStateFlow<Int?>(null)
    val scrollTo: StateFlow<Int?> = _scrollTo.asStateFlow()

    /** The page the user is looking at, 0-based, reported by the list as it scrolls. */
    private val _currentPage = MutableStateFlow(0)
    val currentPage: StateFlow<Int> = _currentPage.asStateFlow()

    /**
     * Bumped after every edit. Page bitmaps are keyed on it, so a rotated or
     * deleted page is redrawn instead of being served from the last composition.
     */
    private val _revision = MutableStateFlow(0)
    val revision: StateFlow<Int> = _revision.asStateFlow()

    /** True while a task is running; the interface shows a bar and blocks a second one. */
    private val _busy = MutableStateFlow(false)
    val busy: StateFlow<Boolean> = _busy.asStateFlow()

    /** True when something has been changed and not written to any file yet. */
    private val _edited = MutableStateFlow(false)
    val edited: StateFlow<Boolean> = _edited.asStateFlow()

    /** Draw pages inverted, for reading in the dark. Affects the screen only. */
    private val _nightReading = MutableStateFlow(false)
    val nightReading: StateFlow<Boolean> = _nightReading.asStateFlow()

    private val _notice = MutableStateFlow<Notice?>(null)
    val notice: StateFlow<Notice?> = _notice.asStateFlow()

    private var file: PdfFile? = null
    private var attemptsLeft = PASSWORD_ATTEMPTS
    private var pendingName: String = ""
    private var sourceBytes: Long = 0L
    private var searchJob: Job? = null

    /** The save the user asked for, held while the system asks them where to put it. */
    private var pendingKind: SaveKind? = null
    private var pendingPassword: String = ""
    private var pendingPermissions: Permissions = Permissions()
    private var pendingPageIndex: Int = 0

    // -----------------------------------------------------------------
    // Opening
    // -----------------------------------------------------------------

    fun open(uri: Uri) {
        viewModelScope.launch {
            closeCurrent()
            _state.value = ViewerState.Opening
            _zoom.value = MIN_ZOOM
            _currentPage.value = 0
            _edited.value = false
            _notice.value = null
            clearSearch()

            val name = displayName(uri)
            pendingName = name

            val bytes = try {
                withContext(Dispatchers.IO) { readBytes(uri) }
            } catch (_: OversizedFile) {
                _state.value = ViewerState.Failed(Failure.TOO_LARGE)
                return@launch
            } catch (_: Throwable) {
                _state.value = ViewerState.Failed(Failure.CANNOT_READ_FILE)
                return@launch
            }
            sourceBytes = bytes.size.toLong()

            val opened = try {
                PdfFile.open(bytes, name.ifBlank { "document.pdf" })
            } catch (_: Throwable) {
                _state.value = ViewerState.Failed(Failure.UNREADABLE)
                return@launch
            }

            file = opened
            attemptsLeft = PASSWORD_ATTEMPTS

            if (opened.needsPassword()) {
                _state.value = ViewerState.NeedsPassword(attemptsLeft, lastWasWrong = false)
            } else {
                becomeReady()
            }
        }
    }

    fun submitPassword(password: String) {
        val opened = file ?: return
        viewModelScope.launch {
            val accepted = try {
                opened.authenticate(password)
            } catch (_: Throwable) {
                false
            }
            if (accepted) {
                becomeReady()
                return@launch
            }
            attemptsLeft -= 1
            _state.value = if (attemptsLeft <= 0) {
                closeCurrent()
                ViewerState.Failed(Failure.WRONG_PASSWORD_TOO_OFTEN)
            } else {
                ViewerState.NeedsPassword(attemptsLeft, lastWasWrong = true)
            }
        }
    }

    fun cancelPassword() {
        viewModelScope.launch {
            closeCurrent()
            _state.value = ViewerState.Empty
        }
    }

    private suspend fun becomeReady() {
        val opened = file ?: return
        val count = try {
            opened.pageCount()
        } catch (_: Throwable) {
            closeCurrent()
            _state.value = ViewerState.Failed(Failure.UNREADABLE)
            return
        }
        if (count <= 0) {
            closeCurrent()
            _state.value = ViewerState.Failed(Failure.NO_PAGES)
            return
        }
        val info = try {
            opened.info()
        } catch (_: Throwable) {
            null
        }
        _state.value = ViewerState.Ready(
            name = pendingName,
            pageCount = count,
            info = info ?: DocumentInfo(
                format = null, encryption = null, title = null, isPdf = true,
                isEncrypted = false, mayPrint = true, mayCopy = true,
                mayEdit = true, mayAnnotate = true,
            ),
        )
    }

    // -----------------------------------------------------------------
    // Drawing
    // -----------------------------------------------------------------

    suspend fun renderPage(index: Int, widthPx: Int): Bitmap? {
        val opened = file ?: return null
        if (widthPx <= 0) return null
        return try {
            opened.renderPage(index, widthPx)
        } catch (_: Throwable) {
            null
        }
    }

    suspend fun renderThumbnail(index: Int, widthPx: Int, heightPx: Int): Bitmap? {
        val opened = file ?: return null
        if (widthPx <= 0 || heightPx <= 0) return null
        return try {
            opened.renderPageFit(index, widthPx, heightPx)
        } catch (_: Throwable) {
            null
        }
    }

    suspend fun pageAspectRatio(index: Int): Float {
        val opened = file ?: return 1f / 1.414f
        return try {
            opened.pageAspectRatio(index)
        } catch (_: Throwable) {
            1f / 1.414f
        }
    }

    fun setZoom(value: Float) {
        _zoom.value = clampZoom(value)
    }

    fun stepZoom(factor: Float) {
        _zoom.value = steppedZoom(_zoom.value, factor)
    }

    fun toggleNightReading() {
        _nightReading.value = !_nightReading.value
    }

    fun setCurrentPage(index: Int) {
        _currentPage.value = index
    }

    // -----------------------------------------------------------------
    // Searching
    // -----------------------------------------------------------------

    fun setSearchQuery(value: String) {
        _searchQuery.value = value
    }

    fun clearSearch() {
        searchJob?.cancel()
        searchJob = null
        _searchQuery.value = ""
        _searchHits.value = emptyList()
        _searching.value = false
    }

    /** Searches every page, newest request cancelling the one before it. */
    fun runSearch() {
        val opened = file ?: return
        val ready = _state.value as? ViewerState.Ready ?: return
        val needle = _searchQuery.value
        searchJob?.cancel()
        if (needle.isBlank()) {
            _searchHits.value = emptyList()
            return
        }
        searchJob = viewModelScope.launch {
            _searching.value = true
            _searchHits.value = emptyList()
            val found = mutableListOf<SearchHit>()
            try {
                for (page in 0 until ready.pageCount) {
                    val regions = try {
                        opened.searchPage(page, needle)
                    } catch (_: Throwable) {
                        emptyList()
                    }
                    regions.forEach { found += SearchHit(page, it) }
                    if (found.size >= 500) break
                    if (found.isNotEmpty() && page % 8 == 0) {
                        _searchHits.value = found.toList()
                    }
                }
                _searchHits.value = found.toList()
                found.firstOrNull()?.let { _scrollTo.value = it.pageIndex }
            } finally {
                _searching.value = false
            }
        }
    }

    fun requestScrollTo(pageIndex: Int) {
        _scrollTo.value = pageIndex
    }

    fun scrollHandled() {
        _scrollTo.value = null
    }

    // -----------------------------------------------------------------
    // Editing the document in memory
    // -----------------------------------------------------------------

    /** Turns the page on screen. The file on disk is untouched until it is saved. */
    fun rotateCurrentPage(byDegrees: Int) = runTask {
        val opened = file ?: return@runTask
        val index = _currentPage.value
        try {
            opened.rotatePage(index, byDegrees)
        } catch (_: PdfFile.NotAPdf) {
            _notice.value = Notice.Problem(TaskFailure.NOT_A_PDF)
            return@runTask
        }
        _edited.value = true
        _revision.value += 1
        _notice.value = Notice.Rotated(byDegrees)
    }

    /** Removes the page on screen, unless it is the only one left. */
    fun deleteCurrentPage() = runTask {
        val opened = file ?: return@runTask
        val ready = _state.value as? ViewerState.Ready ?: return@runTask
        if (ready.pageCount <= 1) {
            _notice.value = Notice.Problem(TaskFailure.LAST_PAGE)
            return@runTask
        }
        val index = _currentPage.value.coerceIn(0, ready.pageCount - 1)
        try {
            opened.deletePage(index)
        } catch (_: PdfFile.NotAPdf) {
            _notice.value = Notice.Problem(TaskFailure.NOT_A_PDF)
            return@runTask
        }
        val remaining = try {
            opened.pageCount()
        } catch (_: Throwable) {
            ready.pageCount - 1
        }
        _state.value = ready.copy(pageCount = remaining)
        _currentPage.value = index.coerceAtMost(remaining - 1)
        _edited.value = true
        _revision.value += 1
        clearSearch()
        _notice.value = Notice.PageDeleted(index + 1)
    }

    /** Puts the page's text on the clipboard, as text rather than as a picture. */
    fun copyCurrentPageText() = runTask {
        val opened = file ?: return@runTask
        val text = try {
            opened.pageText(_currentPage.value)
        } catch (_: Throwable) {
            ""
        }
        if (text.isBlank()) {
            _notice.value = Notice.Problem(TaskFailure.NO_TEXT)
            return@runTask
        }
        val clipboard = getApplication<Application>()
            .getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(pendingName, text))
        _notice.value = Notice.TextCopied(text.length)
    }

    // -----------------------------------------------------------------
    // Saving. The system picks the destination, so this is in two halves.
    // -----------------------------------------------------------------

    /**
     * Records what the user asked for and returns the file name to suggest, or
     * null when the request cannot be met and a notice has been raised instead.
     */
    fun prepareSave(kind: SaveKind, password: String = ""): String? {
        val ready = _state.value as? ViewerState.Ready ?: return null
        if (kind == SaveKind.PROTECTED) {
            when (checkPassword(password)) {
                PasswordRule.EMPTY -> {
                    _notice.value = Notice.Problem(TaskFailure.PASSWORD_EMPTY); return null
                }
                PasswordRule.HAS_COMMA -> {
                    _notice.value = Notice.Problem(TaskFailure.PASSWORD_HAS_COMMA); return null
                }
                PasswordRule.TOO_LONG -> {
                    _notice.value = Notice.Problem(TaskFailure.PASSWORD_TOO_LONG); return null
                }
                PasswordRule.OK -> Unit
            }
        }
        if (kind == SaveKind.UNPROTECTED && !ready.info.isEncrypted) {
            _notice.value = Notice.Problem(TaskFailure.NOT_ENCRYPTED)
            return null
        }
        pendingKind = kind
        pendingPassword = password
        pendingPageIndex = _currentPage.value
        return suggestedName(ready.name, kind)
    }

    /** Carries out the save the user prepared, into the destination they picked. */
    fun completeSave(destination: Uri) = runTask {
        val kind = pendingKind ?: return@runTask
        pendingKind = null
        val opened = file ?: return@runTask

        if (kind == SaveKind.PAGE_IMAGE) {
            val bitmap = renderPage(pendingPageIndex, EXPORT_IMAGE_WIDTH_PX)
            if (bitmap == null) {
                _notice.value = Notice.Problem(TaskFailure.EXPORT_FAILED)
                return@runTask
            }
            val written = withContext(Dispatchers.IO) {
                runCatching {
                    getApplication<Application>().contentResolver
                        .openOutputStream(destination)?.use { out ->
                            bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
                        } ?: false
                }.getOrDefault(false)
            }
            bitmap.recycle()
            _notice.value = if (written) {
                Notice.ImageSaved(displayName(destination))
            } else {
                Notice.Problem(TaskFailure.EXPORT_FAILED)
            }
            return@runTask
        }

        val options = when (kind) {
            SaveKind.COPY -> SaveOptions.plainCopy()
            SaveKind.COMPRESSED -> SaveOptions.compressed()
            SaveKind.PROTECTED -> SaveOptions.protected(pendingPassword, pendingPermissions)
            SaveKind.UNPROTECTED -> SaveOptions.unprotected()
            SaveKind.PAGE_IMAGE -> return@runTask
        }
        pendingPassword = ""

        // MuPDF writes to a path, so the file is built in the cache and then
        // handed to the location the user chose.
        val scratch = File(getApplication<Application>().cacheDir, "save-${System.nanoTime()}.pdf")
        val size = try {
            opened.saveTo(scratch.absolutePath, options)
            val bytes = scratch.length()
            val copied = withContext(Dispatchers.IO) {
                runCatching {
                    getApplication<Application>().contentResolver
                        .openOutputStream(destination)?.use { out ->
                            scratch.inputStream().use { it.copyTo(out) }
                            true
                        } ?: false
                }.getOrDefault(false)
            }
            if (!copied) null else bytes
        } catch (_: PdfFile.NotAPdf) {
            _notice.value = Notice.Problem(TaskFailure.NOT_A_PDF)
            return@runTask
        } catch (_: Throwable) {
            null
        } finally {
            scratch.delete()
        }

        if (size == null) {
            _notice.value = Notice.Problem(TaskFailure.SAVE_FAILED)
            return@runTask
        }
        _edited.value = false
        _notice.value = Notice.Saved(
            name = displayName(destination),
            bytes = size,
            wasBytes = if (kind == SaveKind.COMPRESSED) sourceBytes else null,
        )
    }

    /**
     * Writes the document, as it now stands, into the cache and returns the file,
     * for handing to another app or to the printer. Returns null if it cannot.
     */
    suspend fun exportToCache(): File? {
        val opened = file ?: return null
        val folder = File(getApplication<Application>().cacheDir, "shared")
        withContext(Dispatchers.IO) { folder.mkdirs() }
        val safeName = pendingName.ifBlank { "document.pdf" }
            .replace(Regex("[^\\p{L}\\p{N}._-]"), "_")
            .let { if (it.endsWith(".pdf", ignoreCase = true)) it else "$it.pdf" }
        val target = File(folder, safeName)
        return try {
            withContext(Dispatchers.IO) { target.delete() }
            opened.saveTo(target.absolutePath, SaveOptions.plainCopy())
            target
        } catch (_: Throwable) {
            null
        }
    }

    fun dismissNotice() {
        _notice.value = null
    }

    fun dismissFailure() {
        _state.value = ViewerState.Empty
    }

    fun raiseProblem(reason: TaskFailure) {
        _notice.value = Notice.Problem(reason)
    }

    // -----------------------------------------------------------------

    private fun runTask(block: suspend () -> Unit) {
        if (_busy.value) return
        viewModelScope.launch {
            _busy.value = true
            try {
                block()
            } finally {
                _busy.value = false
            }
        }
    }

    private fun suggestedName(original: String, kind: SaveKind): String {
        val stem = original.substringBeforeLast('.', original).ifBlank { "document" }
        return when (kind) {
            SaveKind.COPY -> "$stem-copy.pdf"
            SaveKind.COMPRESSED -> "$stem-compressed.pdf"
            SaveKind.PROTECTED -> "$stem-protected.pdf"
            SaveKind.UNPROTECTED -> "$stem-unlocked.pdf"
            SaveKind.PAGE_IMAGE -> "$stem-page${_currentPage.value + 1}.png"
        }
    }

    private suspend fun closeCurrent() {
        file?.close()
        file = null
    }

    override fun onCleared() {
        super.onCleared()
        val closing = file
        file = null
        if (closing != null) {
            // The view model is going away; still release the native document.
            viewModelScope.launch { closing.close() }
        }
    }

    private class OversizedFile : RuntimeException()

    private fun readBytes(uri: Uri): ByteArray {
        val resolver = getApplication<Application>().contentResolver
        resolver.openAssetFileDescriptor(uri, "r")?.use { descriptor ->
            val length = descriptor.length
            if (length != -1L && length > MAX_FILE_BYTES) throw OversizedFile()
        }
        val stream = resolver.openInputStream(uri) ?: throw IllegalStateException("no stream")
        return stream.use { input ->
            val buffer = java.io.ByteArrayOutputStream()
            val chunk = ByteArray(64 * 1024)
            var total = 0L
            while (true) {
                val read = input.read(chunk)
                if (read <= 0) break
                total += read
                if (total > MAX_FILE_BYTES) throw OversizedFile()
                buffer.write(chunk, 0, read)
            }
            buffer.toByteArray()
        }
    }

    private fun displayName(uri: Uri): String {
        val resolver = getApplication<Application>().contentResolver
        try {
            resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
                ?.use { cursor ->
                    if (cursor.moveToFirst() && !cursor.isNull(0)) {
                        val name = cursor.getString(0)
                        if (!name.isNullOrBlank()) return name
                    }
                }
        } catch (_: Throwable) {
            // A provider that refuses the query is not a failure to open the file.
        }
        return uri.lastPathSegment?.substringAfterLast('/') ?: "document.pdf"
    }
}
