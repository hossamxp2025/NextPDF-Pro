package com.futureautomation.nextpdf.viewer

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import android.provider.OpenableColumns
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.futureautomation.nextpdf.pdf.DocumentInfo
import com.futureautomation.nextpdf.pdf.PdfFile
import com.futureautomation.nextpdf.pdf.SearchHit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** How many wrong passwords are allowed before the document is given up on. */
const val PASSWORD_ATTEMPTS = 3

/** Files larger than this are refused with a reason rather than risking an OOM kill. */
const val MAX_FILE_BYTES = 64L * 1024L * 1024L

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

    private var file: PdfFile? = null
    private var attemptsLeft = PASSWORD_ATTEMPTS
    private var pendingName: String = ""
    private var searchJob: Job? = null

    fun setZoom(value: Float) {
        _zoom.value = clampZoom(value)
    }

    fun stepZoom(factor: Float) {
        _zoom.value = steppedZoom(_zoom.value, factor)
    }

    fun open(uri: Uri) {
        viewModelScope.launch {
            closeCurrent()
            _state.value = ViewerState.Opening
            _zoom.value = MIN_ZOOM
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

    suspend fun renderPage(index: Int, widthPx: Int): Bitmap? {
        val opened = file ?: return null
        if (widthPx <= 0) return null
        return try {
            opened.renderPage(index, widthPx)
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

    fun dismissFailure() {
        _state.value = ViewerState.Empty
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
