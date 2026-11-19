/*
 * The whole interface. It is deliberately one file: the screen is one viewer with
 * a few sheets and dialogs hanging off it, and splitting that across files would
 * hide the shape rather than clarify it.
 *
 * Nothing here talks to MuPDF. Everything goes through ViewerViewModel, which
 * funnels the engine onto its own thread.
 */
package com.futureautomation.nextpdf

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.print.PrintManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.LockOpen
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.futureautomation.nextpdf.print.PdfPrintAdapter
import com.futureautomation.nextpdf.ui.NextPdfTheme
import com.futureautomation.nextpdf.viewer.Failure
import com.futureautomation.nextpdf.viewer.Notice
import com.futureautomation.nextpdf.viewer.SaveKind
import com.futureautomation.nextpdf.viewer.TaskFailure
import com.futureautomation.nextpdf.viewer.ViewerState
import com.futureautomation.nextpdf.viewer.ViewerViewModel
import com.futureautomation.nextpdf.viewer.renderWidth
import com.futureautomation.nextpdf.viewer.zoomPercent
import kotlinx.coroutines.launch
import java.util.Locale

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        hideNavigationBar()
        setContent {
            NextPdfTheme {
                val model: ViewerViewModel = viewModel()
                LaunchedEffect(Unit) { intent?.let { openFrom(it, model) } }
                ViewerScreen(model)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        // The system puts its bars back after a dialog, a share sheet or a
        // moment in the recents list; put them away again.
        if (hasFocus) hideNavigationBar()
    }

    /**
     * Hides the navigation buttons so they cannot sit under the app's own
     * controls, and lets a swipe from the edge bring them back for as long as
     * the user needs them. The status bar stays: the clock and the battery are
     * not in anyone's way, and hiding them only makes the phone feel broken.
     */
    private fun hideNavigationBar() {
        val controller = WindowCompat.getInsetsController(window, window.decorView)
        controller.systemBarsBehavior =
            WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        controller.hide(WindowInsetsCompat.Type.navigationBars())
    }

    private fun openFrom(intent: Intent, model: ViewerViewModel) {
        if (intent.action != Intent.ACTION_VIEW) return
        val uri: Uri = intent.data ?: return
        model.open(uri)
    }
}

// ---------------------------------------------------------------------------
// The screen
// ---------------------------------------------------------------------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ViewerScreen(model: ViewerViewModel) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val state by model.state.collectAsState()
    val zoom by model.zoom.collectAsState()
    val busy by model.busy.collectAsState()
    val edited by model.edited.collectAsState()
    val notice by model.notice.collectAsState()
    val currentPage by model.currentPage.collectAsState()
    val nightReading by model.nightReading.collectAsState()

    var searchOpen by remember { mutableStateOf(false) }
    var showTools by remember { mutableStateOf(false) }
    var showPages by remember { mutableStateOf(false) }
    var showInfo by remember { mutableStateOf(false) }
    var showAbout by remember { mutableStateOf(false) }
    var showGoToPage by remember { mutableStateOf(false) }
    var showProtect by remember { mutableStateOf(false) }
    var showUnprotect by remember { mutableStateOf(false) }
    var overflowOpen by remember { mutableStateOf(false) }

    val snackbar = remember { SnackbarHostState() }

    val openLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri -> uri?.let(model::open) }

    val savePdfLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/pdf"),
    ) { uri -> uri?.let(model::completeSave) }

    val savePngLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("image/png"),
    ) { uri -> uri?.let(model::completeSave) }

    fun startSave(kind: SaveKind, password: String = "") {
        val suggested = model.prepareSave(kind, password) ?: return
        if (kind == SaveKind.PAGE_IMAGE) savePngLauncher.launch(suggested)
        else savePdfLauncher.launch(suggested)
    }

    val noticeText = notice?.let { describe(it, context) }
    LaunchedEffect(notice) {
        if (noticeText != null) {
            snackbar.showSnackbar(noticeText)
            model.dismissNotice()
        }
    }

    val ready = state as? ViewerState.Ready

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            Column {
                TopAppBar(
                    title = {
                        Column {
                            Text(
                                text = ready?.name ?: stringResource(R.string.app_name),
                                maxLines = 1,
                                style = MaterialTheme.typography.titleMedium,
                            )
                            if (edited) {
                                Text(
                                    text = stringResource(R.string.unsaved_changes),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.error,
                                )
                            }
                        }
                    },
                    actions = {
                        IconButton(onClick = { openLauncher.launch(arrayOf("application/pdf")) }) {
                            Icon(Icons.Filled.Add, stringResource(R.string.open_document))
                        }
                        if (ready != null) {
                            IconButton(onClick = {
                                searchOpen = !searchOpen
                                if (!searchOpen) model.clearSearch()
                            }) {
                                Icon(Icons.Filled.Search, stringResource(R.string.search))
                            }
                            Box {
                                IconButton(onClick = { overflowOpen = true }) {
                                    Icon(Icons.Filled.MoreVert, stringResource(R.string.more_actions))
                                }
                                DropdownMenu(
                                    expanded = overflowOpen,
                                    onDismissRequest = { overflowOpen = false },
                                ) {
                                    DropdownMenuItem(
                                        text = { Text(stringResource(R.string.pages_title)) },
                                        onClick = { overflowOpen = false; showPages = true },
                                    )
                                    DropdownMenuItem(
                                        text = { Text(stringResource(R.string.night_reading)) },
                                        leadingIcon = { Icon(Icons.Filled.DarkMode, null) },
                                        trailingIcon = {
                                            Switch(checked = nightReading, onCheckedChange = null)
                                        },
                                        onClick = { model.toggleNightReading() },
                                    )
                                    DropdownMenuItem(
                                        text = { Text(stringResource(R.string.tool_share)) },
                                        leadingIcon = { Icon(Icons.Filled.Share, null) },
                                        onClick = {
                                            overflowOpen = false
                                            scope.launch { shareDocument(context, model) }
                                        },
                                    )
                                    DropdownMenuItem(
                                        text = { Text(stringResource(R.string.tool_print)) },
                                        onClick = {
                                            overflowOpen = false
                                            scope.launch { printDocument(context, model, ready.name) }
                                        },
                                    )
                                    HorizontalDivider()
                                    DropdownMenuItem(
                                        text = { Text(stringResource(R.string.info_title)) },
                                        leadingIcon = { Icon(Icons.Filled.Info, null) },
                                        onClick = { overflowOpen = false; showInfo = true },
                                    )
                                    DropdownMenuItem(
                                        text = { Text(stringResource(R.string.about)) },
                                        onClick = { overflowOpen = false; showAbout = true },
                                    )
                                }
                            }
                        } else {
                            IconButton(onClick = { showAbout = true }) {
                                Icon(Icons.Filled.Info, stringResource(R.string.about))
                            }
                        }
                    },
                )
                if (ready != null) {
                    // The controls live up here, not at the foot of the screen:
                    // down there they sit on top of the phone's own navigation
                    // buttons and cannot be pressed.
                    ControlBar(
                        pageNumber = currentPage + 1,
                        pageCount = ready.pageCount,
                        zoom = zoom,
                        onPrevious = { model.requestScrollTo((currentPage - 1).coerceAtLeast(0)) },
                        onNext = {
                            model.requestScrollTo((currentPage + 1).coerceAtMost(ready.pageCount - 1))
                        },
                        onPageTap = { showGoToPage = true },
                        onZoomIn = { model.stepZoom(1.25f) },
                        onZoomOut = { model.stepZoom(0.8f) },
                        onFitWidth = { model.setZoom(1f) },
                        onTools = { showTools = true },
                    )
                }
                if (searchOpen && ready != null) SearchBar(model)
                if (busy) LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }
        },
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(MaterialTheme.colorScheme.background),
        ) {
            when (val current = state) {
                is ViewerState.Ready -> PageList(model, current.pageCount, zoom, nightReading)
                ViewerState.Opening -> Centered { CircularProgressIndicator() }
                else -> Welcome { openLauncher.launch(arrayOf("application/pdf")) }
            }
        }
    }

    // --- sheets and dialogs -------------------------------------------------

    if (showTools && ready != null) {
        ModalBottomSheet(
            onDismissRequest = { showTools = false },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        ) {
            ToolsSheet(
                isEncrypted = ready.info.isEncrypted,
                onRotateLeft = { showTools = false; model.rotateCurrentPage(-90) },
                onRotateRight = { showTools = false; model.rotateCurrentPage(90) },
                onDeletePage = { showTools = false; model.deleteCurrentPage() },
                onPageImage = { showTools = false; startSave(SaveKind.PAGE_IMAGE) },
                onCopyText = { showTools = false; model.copyCurrentPageText() },
                onProtect = { showTools = false; showProtect = true },
                onUnprotect = { showTools = false; showUnprotect = true },
                onCompress = { showTools = false; startSave(SaveKind.COMPRESSED) },
                onSaveCopy = { showTools = false; startSave(SaveKind.COPY) },
            )
        }
    }

    if (showPages && ready != null) {
        ModalBottomSheet(
            onDismissRequest = { showPages = false },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        ) {
            PagesSheet(model, ready.pageCount) { index ->
                showPages = false
                model.requestScrollTo(index)
            }
        }
    }

    if (showGoToPage && ready != null) {
        GoToPageDialog(
            pageCount = ready.pageCount,
            onDismiss = { showGoToPage = false },
            onGo = { index -> showGoToPage = false; model.requestScrollTo(index) },
        )
    }

    if (showProtect) {
        ProtectDialog(
            onDismiss = { showProtect = false },
            onProtect = { password -> showProtect = false; startSave(SaveKind.PROTECTED, password) },
        )
    }

    if (showUnprotect) {
        AlertDialog(
            onDismissRequest = { showUnprotect = false },
            title = { Text(stringResource(R.string.unprotect_title)) },
            text = { Text(stringResource(R.string.unprotect_body)) },
            confirmButton = {
                TextButton(onClick = {
                    showUnprotect = false
                    startSave(SaveKind.UNPROTECTED)
                }) { Text(stringResource(R.string.save)) }
            },
            dismissButton = {
                TextButton(onClick = { showUnprotect = false }) {
                    Text(stringResource(R.string.cancel))
                }
            },
        )
    }

    if (showInfo && ready != null) {
        InfoDialog(ready) { showInfo = false }
    }

    if (showAbout) {
        AboutDialog { showAbout = false }
    }

    when (val current = state) {
        is ViewerState.NeedsPassword -> PasswordDialog(
            attemptsLeft = current.attemptsLeft,
            lastWasWrong = current.lastWasWrong,
            onSubmit = model::submitPassword,
            onCancel = model::cancelPassword,
        )

        is ViewerState.Failed -> FailureDialog(current.reason) { model.dismissFailure() }
        else -> Unit
    }
}

// ---------------------------------------------------------------------------
// Pieces
// ---------------------------------------------------------------------------

@Composable
private fun Centered(content: @Composable () -> Unit) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { content() }
}

@Composable
private fun Welcome(onOpen: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(R.string.welcome_title),
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            text = stringResource(R.string.welcome_body),
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.secondary,
        )
        Spacer(Modifier.height(24.dp))
        TextButton(onClick = onOpen) { Text(stringResource(R.string.open_document)) }
    }
}

@Composable
private fun SearchBar(model: ViewerViewModel) {
    val query by model.searchQuery.collectAsState()
    val hits by model.searchHits.collectAsState()
    val searching by model.searching.collectAsState()

    Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)) {
        OutlinedTextField(
            value = query,
            onValueChange = model::setSearchQuery,
            label = { Text(stringResource(R.string.search_hint)) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            trailingIcon = {
                Row {
                    if (query.isNotEmpty()) {
                        IconButton(onClick = { model.setSearchQuery("") }) {
                            Icon(Icons.Filled.Close, stringResource(R.string.close))
                        }
                    }
                    IconButton(onClick = model::runSearch) {
                        Icon(Icons.Filled.Search, stringResource(R.string.search))
                    }
                }
            },
        )
        Spacer(Modifier.height(4.dp))
        when {
            searching -> Text(
                stringResource(R.string.search_running),
                style = MaterialTheme.typography.labelMedium,
            )

            hits.isNotEmpty() -> {
                Text(
                    stringResource(R.string.search_matches, hits.size),
                    style = MaterialTheme.typography.labelMedium,
                )
                // A row of jumps, scrolled rather than wrapped: a document can
                // have hundreds of matches and they must not push the page away.
                LazyRow(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 4.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    itemsIndexed(hits) { position, hit ->
                        AssistChip(
                            onClick = { model.requestScrollTo(hit.pageIndex) },
                            label = { Text(stringResource(R.string.search_jump, position + 1)) },
                        )
                    }
                }
            }

            query.isNotBlank() -> Text(
                stringResource(R.string.search_none),
                style = MaterialTheme.typography.labelMedium,
            )
        }
    }
}

/**
 * Page, zoom and tools, in a row directly under the title bar.
 *
 * It was at the foot of the screen in 0.2.0 and that was wrong: on a phone with
 * on-screen navigation buttons the two rows overlap and the app's buttons cannot
 * be reached at all.
 */
@Composable
private fun ControlBar(
    pageNumber: Int,
    pageCount: Int,
    zoom: Float,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    onPageTap: () -> Unit,
    onZoomIn: () -> Unit,
    onZoomOut: () -> Unit,
    onFitWidth: () -> Unit,
    onTools: () -> Unit,
) {
    Surface(tonalElevation = 3.dp, color = MaterialTheme.colorScheme.surface) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                // A narrow phone can run out of room for ten controls; scrolling
                // the row keeps every one of them reachable.
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 4.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onPrevious, enabled = pageNumber > 1) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.page_previous))
            }
            Text(
                // Isolated left-to-right: "1 / 7" in an Arabic layout otherwise
                // comes out as "7 / 1", because the slash is a neutral character
                // between two numbers and takes the paragraph's direction.
                text = "⁦" + stringResource(R.string.page_short, pageNumber, pageCount) + "⁩",
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier
                    .clickable(onClick = onPageTap)
                    .padding(horizontal = 6.dp, vertical = 8.dp),
            )
            IconButton(onClick = onNext, enabled = pageNumber < pageCount) {
                Icon(Icons.AutoMirrored.Filled.ArrowForward, stringResource(R.string.page_next))
            }

            Spacer(Modifier.width(8.dp))

            IconButton(onClick = onZoomOut) {
                Icon(Icons.Filled.Remove, stringResource(R.string.zoom_out))
            }
            Text(
                text = "⁦" + stringResource(R.string.zoom_level, zoomPercent(zoom)) + "⁩",
                style = MaterialTheme.typography.labelLarge,
                modifier = Modifier
                    .clickable(onClick = onFitWidth)
                    .padding(horizontal = 4.dp, vertical = 8.dp),
            )
            IconButton(onClick = onZoomIn) {
                Icon(Icons.Filled.Add, stringResource(R.string.zoom_in))
            }

            Spacer(Modifier.width(8.dp))

            IconButton(onClick = onTools) {
                Icon(Icons.Filled.Build, stringResource(R.string.tools_title))
            }
        }
    }
}

@Composable
private fun PageList(
    model: ViewerViewModel,
    pageCount: Int,
    zoom: Float,
    nightReading: Boolean,
) {
    val listState = rememberLazyListState()
    val scrollTo by model.scrollTo.collectAsState()
    val revision by model.revision.collectAsState()
    val density = LocalDensity.current

    LaunchedEffect(scrollTo) {
        val target = scrollTo ?: return@LaunchedEffect
        listState.animateScrollToItem(target.coerceIn(0, (pageCount - 1).coerceAtLeast(0)))
        model.scrollHandled()
    }

    LaunchedEffect(listState) {
        snapshotFlow { listState.firstVisibleItemIndex }
            .collect { model.setCurrentPage(it) }
    }

    val pages = remember(pageCount, revision) { (0 until pageCount).toList() }

    Box(modifier = Modifier.fillMaxSize()) {
        // One measurement for the whole list: the width a page gets at 100%.
        androidx.compose.foundation.layout.BoxWithConstraints(Modifier.fillMaxSize()) {
            val viewportWidthPx = with(density) {
                (maxWidth - 16.dp).coerceAtLeast(0.dp).toPx()
            }.toInt()
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(8.dp),
            ) {
                items(pages, key = { it }) { index ->
                    PageCard(model, index, pageCount, zoom, viewportWidthPx, revision, nightReading)
                    Spacer(Modifier.height(12.dp))
                }
            }
        }
    }
}

/** The colour filter that turns a page into light-on-dark for night reading. */
private val InvertFilter = ColorFilter.colorMatrix(
    ColorMatrix(
        floatArrayOf(
            -1f, 0f, 0f, 0f, 255f,
            0f, -1f, 0f, 0f, 255f,
            0f, 0f, -1f, 0f, 255f,
            0f, 0f, 0f, 1f, 0f,
        ),
    ),
)

@Composable
private fun PageCard(
    model: ViewerViewModel,
    index: Int,
    pageCount: Int,
    zoom: Float,
    viewportWidthPx: Int,
    revision: Int,
    nightReading: Boolean,
) {
    val wanted = renderWidth(viewportWidthPx, zoom)
    var bitmap by remember(index, revision) {
        mutableStateOf<android.graphics.Bitmap?>(null)
    }
    var aspect by remember(index, revision) { mutableStateOf(1f / 1.414f) }

    LaunchedEffect(index, wanted, revision) {
        if (wanted <= 0) return@LaunchedEffect
        aspect = model.pageAspectRatio(index)
        bitmap = model.renderPage(index, wanted)
    }

    Card(shape = RoundedCornerShape(4.dp)) {
        Column {
            val drawn = bitmap
            if (drawn != null) {
                Image(
                    bitmap = drawn.asImageBitmap(),
                    contentDescription = stringResource(R.string.page_of, index + 1, pageCount),
                    modifier = Modifier.fillMaxWidth(),
                    contentScale = ContentScale.FillWidth,
                    colorFilter = if (nightReading) InvertFilter else null,
                )
            } else {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(aspect.coerceAtLeast(0.1f)),
                    contentAlignment = Alignment.Center,
                ) { CircularProgressIndicator() }
            }
            Text(
                text = stringResource(R.string.page_of, index + 1, pageCount),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.secondary,
                modifier = Modifier.padding(8.dp),
            )
        }
    }
}

@Composable
private fun ToolsSheet(
    isEncrypted: Boolean,
    onRotateLeft: () -> Unit,
    onRotateRight: () -> Unit,
    onDeletePage: () -> Unit,
    onPageImage: () -> Unit,
    onCopyText: () -> Unit,
    onProtect: () -> Unit,
    onUnprotect: () -> Unit,
    onCompress: () -> Unit,
    onSaveCopy: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 24.dp),
    ) {
        Text(
            text = stringResource(R.string.tools_title),
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(start = 24.dp, end = 24.dp, bottom = 8.dp),
        )
        Tool(stringResource(R.string.tool_rotate_right), Icons.Filled.Refresh, onRotateRight)
        Tool(stringResource(R.string.tool_rotate_left), Icons.Filled.Refresh, onRotateLeft)
        Tool(stringResource(R.string.tool_delete_page), Icons.Filled.Delete, onDeletePage)
        HorizontalDivider()
        Tool(stringResource(R.string.tool_copy_text), Icons.Filled.Share, onCopyText)
        Tool(stringResource(R.string.tool_page_image), Icons.Filled.Share, onPageImage)
        HorizontalDivider()
        Tool(stringResource(R.string.tool_protect), Icons.Filled.Lock, onProtect)
        if (isEncrypted) {
            Tool(stringResource(R.string.tool_unprotect), Icons.Filled.LockOpen, onUnprotect)
        }
        Tool(stringResource(R.string.tool_compress), Icons.Filled.Build, onCompress)
        Tool(stringResource(R.string.tool_save_copy), Icons.Filled.Add, onSaveCopy)
        Text(
            text = stringResource(R.string.tools_edit_note),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.secondary,
            modifier = Modifier.padding(24.dp),
        )
    }
}

@Composable
private fun Tool(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit,
) {
    ListItem(
        headlineContent = { Text(label) },
        leadingContent = { Icon(icon, null) },
        modifier = Modifier.clickable(onClick = onClick),
    )
}

@Composable
private fun PagesSheet(model: ViewerViewModel, pageCount: Int, onPick: (Int) -> Unit) {
    val revision by model.revision.collectAsState()
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = stringResource(R.string.pages_title),
            style = MaterialTheme.typography.titleMedium,
            modifier = Modifier.padding(24.dp),
        )
        LazyVerticalGrid(
            columns = GridCells.Adaptive(minSize = 110.dp),
            contentPadding = PaddingValues(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.height(380.dp),
        ) {
            items((0 until pageCount).toList(), key = { it }) { index ->
                Thumbnail(model, index, revision) { onPick(index) }
            }
        }
    }
}

@Composable
private fun Thumbnail(model: ViewerViewModel, index: Int, revision: Int, onClick: () -> Unit) {
    var bitmap by remember(index, revision) {
        mutableStateOf<android.graphics.Bitmap?>(null)
    }
    LaunchedEffect(index, revision) {
        bitmap = model.renderThumbnail(index, 220, 300)
    }
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.clickable(onClick = onClick),
    ) {
        Card(shape = RoundedCornerShape(3.dp), modifier = Modifier.size(110.dp, 150.dp)) {
            val drawn = bitmap
            if (drawn != null) {
                Image(
                    bitmap = drawn.asImageBitmap(),
                    contentDescription = null,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit,
                )
            }
        }
        Text("${index + 1}", style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun GoToPageDialog(pageCount: Int, onDismiss: () -> Unit, onGo: (Int) -> Unit) {
    var typed by remember { mutableStateOf("") }
    val number = typed.toIntOrNull()
    val valid = number != null && number in 1..pageCount
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.go_to_page)) },
        text = {
            OutlinedTextField(
                value = typed,
                onValueChange = { typed = it.filter(Char::isDigit).take(6) },
                label = { Text(stringResource(R.string.go_to_page_hint)) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            )
        },
        confirmButton = {
            TextButton(enabled = valid, onClick = { onGo(number!! - 1) }) {
                Text(stringResource(R.string.done))
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        },
    )
}

@Composable
private fun ProtectDialog(onDismiss: () -> Unit, onProtect: (String) -> Unit) {
    var password by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.protect_title)) },
        text = {
            Column {
                Text(stringResource(R.string.protect_body))
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text(stringResource(R.string.password_hint)) },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                )
                Spacer(Modifier.height(12.dp))
                Text(
                    text = stringResource(R.string.protect_warning),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        },
        confirmButton = {
            TextButton(enabled = password.isNotEmpty(), onClick = { onProtect(password) }) {
                Text(stringResource(R.string.save))
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) }
        },
    )
}

@Composable
private fun PasswordDialog(
    attemptsLeft: Int,
    lastWasWrong: Boolean,
    onSubmit: (String) -> Unit,
    onCancel: () -> Unit,
) {
    var password by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text(stringResource(R.string.password_title)) },
        text = {
            Column {
                Text(stringResource(R.string.password_body, attemptsLeft))
                if (lastWasWrong) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = stringResource(R.string.password_wrong),
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text(stringResource(R.string.password_hint)) },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { onSubmit(password) }) {
                Text(stringResource(R.string.unlock))
            }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text(stringResource(R.string.cancel)) }
        },
    )
}

@Composable
private fun FailureDialog(reason: Failure, onDismiss: () -> Unit) {
    val message = when (reason) {
        Failure.UNREADABLE -> R.string.failed_unreadable
        Failure.TOO_LARGE -> R.string.failed_too_large
        Failure.WRONG_PASSWORD_TOO_OFTEN -> R.string.failed_wrong_password
        Failure.NO_PAGES -> R.string.failed_no_pages
        Failure.CANNOT_READ_FILE -> R.string.failed_cannot_read
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.app_name)) },
        text = { Text(stringResource(message)) },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.close)) }
        },
    )
}

@Composable
private fun InfoDialog(ready: ViewerState.Ready, onDismiss: () -> Unit) {
    val info = ready.info
    val allowed = buildList {
        if (info.mayPrint) add(stringResource(R.string.info_permission_print))
        if (info.mayCopy) add(stringResource(R.string.info_permission_copy))
        if (info.mayEdit) add(stringResource(R.string.info_permission_edit))
        if (info.mayAnnotate) add(stringResource(R.string.info_permission_annotate))
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.info_title)) },
        text = {
            Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                InfoRow(stringResource(R.string.info_format), info.format ?: "—")
                InfoRow(stringResource(R.string.info_pages), ready.pageCount.toString())
                InfoRow(
                    stringResource(R.string.info_encryption),
                    info.encryption?.takeIf { info.isEncrypted } ?: stringResource(R.string.info_none),
                )
                InfoRow(
                    stringResource(R.string.info_permissions),
                    if (allowed.isEmpty()) stringResource(R.string.info_none) else allowed.joinToString("، "),
                )
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.close)) }
        },
    )
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(modifier = Modifier.padding(vertical = 4.dp)) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier.width(110.dp),
        )
        Text(text = value, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun AboutDialog(onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.app_name)) },
        text = {
            Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                Text(stringResource(R.string.about_version, BuildConfig.VERSION_NAME))
                Spacer(Modifier.height(8.dp))
                Text(stringResource(R.string.about_body))
                Spacer(Modifier.height(16.dp))
                Text(
                    text = stringResource(R.string.about_does_title),
                    style = MaterialTheme.typography.titleSmall,
                )
                Spacer(Modifier.height(4.dp))
                Text(stringResource(R.string.about_does))
                Spacer(Modifier.height(16.dp))
                Text(
                    text = stringResource(R.string.about_not_yet_title),
                    style = MaterialTheme.typography.titleSmall,
                )
                Spacer(Modifier.height(4.dp))
                Text(stringResource(R.string.about_not_yet))
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.close)) }
        },
    )
}

// ---------------------------------------------------------------------------
// Things that leave the app
// ---------------------------------------------------------------------------

private suspend fun shareDocument(context: Context, model: ViewerViewModel) {
    val file = model.exportToCache()
    if (file == null) {
        model.raiseProblem(TaskFailure.SAVE_FAILED)
        return
    }
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "application/pdf"
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    runCatching { context.startActivity(Intent.createChooser(intent, file.name)) }
        .onFailure { model.raiseProblem(TaskFailure.SAVE_FAILED) }
}

private suspend fun printDocument(context: Context, model: ViewerViewModel, jobName: String) {
    val file = model.exportToCache()
    if (file == null) {
        model.raiseProblem(TaskFailure.SAVE_FAILED)
        return
    }
    val manager = context.getSystemService(Context.PRINT_SERVICE) as? PrintManager
    if (manager == null) {
        model.raiseProblem(TaskFailure.SAVE_FAILED)
        return
    }
    runCatching { manager.print(jobName, PdfPrintAdapter(file, jobName), null) }
        .onFailure { model.raiseProblem(TaskFailure.SAVE_FAILED) }
}

// ---------------------------------------------------------------------------
// Turning a notice into the sentence the user reads
// ---------------------------------------------------------------------------

private fun describe(notice: Notice, context: Context): String = when (notice) {
    is Notice.Saved -> when {
        notice.wasBytes == null ->
            context.getString(R.string.notice_saved, notice.name, humanSize(notice.bytes))

        notice.bytes < notice.wasBytes -> context.getString(
            R.string.notice_saved_smaller,
            notice.name,
            humanSize(notice.bytes),
            humanSize(notice.wasBytes),
        )

        else -> context.getString(
            R.string.notice_saved_bigger,
            notice.name,
            humanSize(notice.bytes),
            humanSize(notice.wasBytes),
        )
    }

    is Notice.ImageSaved -> context.getString(R.string.notice_image_saved, notice.name)
    is Notice.TextCopied -> context.getString(R.string.notice_text_copied, notice.characters)
    is Notice.PageDeleted -> context.getString(R.string.notice_page_deleted, notice.pageNumber)
    is Notice.Rotated -> context.getString(R.string.notice_rotated)
    is Notice.Problem -> context.getString(
        when (notice.reason) {
            TaskFailure.NOT_A_PDF -> R.string.problem_not_a_pdf
            TaskFailure.SAVE_FAILED -> R.string.problem_save_failed
            TaskFailure.EXPORT_FAILED -> R.string.problem_export_failed
            TaskFailure.LAST_PAGE -> R.string.problem_last_page
            TaskFailure.NO_TEXT -> R.string.problem_no_text
            TaskFailure.NOT_ENCRYPTED -> R.string.problem_not_encrypted
            TaskFailure.PASSWORD_EMPTY -> R.string.problem_password_empty
            TaskFailure.PASSWORD_HAS_COMMA -> R.string.problem_password_comma
            TaskFailure.PASSWORD_TOO_LONG -> R.string.problem_password_long
        },
    )
}

/** A file size the way a person reads it. */
internal fun humanSize(bytes: Long): String = when {
    bytes >= 1024L * 1024L -> String.format(Locale.US, "%.1f MB", bytes / 1024.0 / 1024.0)
    bytes >= 1024L -> String.format(Locale.US, "%.0f KB", bytes / 1024.0)
    else -> "$bytes B"
}
