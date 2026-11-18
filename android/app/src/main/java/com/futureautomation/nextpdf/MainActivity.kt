package com.futureautomation.nextpdf

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.futureautomation.nextpdf.pdf.DocumentInfo
import com.futureautomation.nextpdf.ui.NextPdfTheme
import com.futureautomation.nextpdf.viewer.Failure
import com.futureautomation.nextpdf.viewer.ViewerState
import com.futureautomation.nextpdf.viewer.ViewerViewModel
import com.futureautomation.nextpdf.viewer.renderWidth
import com.futureautomation.nextpdf.viewer.zoomPercent

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            NextPdfTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    ViewerScreen(startUri = intent?.takeIf { it.action == Intent.ACTION_VIEW }?.data)
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ViewerScreen(startUri: Uri?) {
    val model: ViewerViewModel = viewModel()
    val state by model.state.collectAsState()
    val zoom by model.zoom.collectAsState()
    val query by model.searchQuery.collectAsState()
    val hits by model.searchHits.collectAsState()
    val searching by model.searching.collectAsState()
    val scrollTo by model.scrollTo.collectAsState()

    var searchOpen by remember { mutableStateOf(false) }
    var aboutOpen by remember { mutableStateOf(false) }
    var infoOpen by remember { mutableStateOf(false) }

    val listState = rememberLazyListState()

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri -> if (uri != null) model.open(uri) }

    LaunchedEffect(startUri) {
        if (startUri != null) model.open(startUri)
    }

    LaunchedEffect(scrollTo) {
        val target = scrollTo
        if (target != null) {
            listState.animateScrollToItem(target)
            model.scrollHandled()
        }
    }

    val ready = state as? ViewerState.Ready

    Scaffold(
        topBar = {
            TopAppBar(
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary,
                ),
                title = {
                    Text(
                        text = ready?.name?.takeIf { it.isNotBlank() }
                            ?: stringResource(R.string.app_name),
                        maxLines = 1,
                        style = MaterialTheme.typography.titleMedium,
                    )
                },
                actions = {
                    TextButton(onClick = { picker.launch(arrayOf("application/pdf")) }) {
                        Label(stringResource(R.string.open_document))
                    }
                    if (ready != null) {
                        TextButton(onClick = {
                            searchOpen = !searchOpen
                            if (!searchOpen) model.clearSearch()
                        }) {
                            Label(stringResource(R.string.search))
                        }
                        TextButton(onClick = { infoOpen = true }) {
                            Label(stringResource(R.string.info_title))
                        }
                    }
                    TextButton(onClick = { aboutOpen = true }) {
                        Label(stringResource(R.string.about))
                    }
                },
            )
        },
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize()) {

            if (ready != null && searchOpen) {
                SearchBar(
                    query = query,
                    searching = searching,
                    matchCount = hits.size,
                    onQueryChange = model::setSearchQuery,
                    onSubmit = model::runSearch,
                    onJump = { index -> model.requestScrollTo(hits[index].pageIndex) },
                )
            }

            if (ready != null) {
                ZoomBar(
                    zoomLabel = zoomPercent(zoom),
                    onIn = { model.stepZoom(1.25f) },
                    onOut = { model.stepZoom(0.8f) },
                    onReset = { model.setZoom(1f) },
                )
            }

            Box(modifier = Modifier.fillMaxSize()) {
                when (val current = state) {
                    is ViewerState.Empty -> Welcome { picker.launch(arrayOf("application/pdf")) }

                    is ViewerState.Opening -> Centered { CircularProgressIndicator() }

                    is ViewerState.NeedsPassword -> {
                        Welcome { picker.launch(arrayOf("application/pdf")) }
                        PasswordDialog(
                            attemptsLeft = current.attemptsLeft,
                            lastWasWrong = current.lastWasWrong,
                            onSubmit = model::submitPassword,
                            onCancel = model::cancelPassword,
                        )
                    }

                    is ViewerState.Failed -> {
                        Welcome { picker.launch(arrayOf("application/pdf")) }
                        FailureDialog(current.reason) { model.dismissFailure() }
                    }

                    is ViewerState.Ready -> PageList(
                        model = model,
                        pageCount = current.pageCount,
                        zoom = zoom,
                        listState = listState,
                    )
                }
            }
        }
    }

    if (aboutOpen) AboutDialog { aboutOpen = false }
    if (infoOpen && ready != null) {
        InfoDialog(name = ready.name, pageCount = ready.pageCount, info = ready.info) {
            infoOpen = false
        }
    }
}

@Composable
private fun Label(text: String) {
    Text(text = text, color = MaterialTheme.colorScheme.onPrimary)
}

@Composable
private fun Centered(content: @Composable () -> Unit) {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { content() }
}

@Composable
private fun Welcome(onOpen: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = stringResource(R.string.welcome_title),
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            text = stringResource(R.string.welcome_body),
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(24.dp))
        TextButton(onClick = onOpen) {
            Text(stringResource(R.string.open_document))
        }
    }
}

@Composable
private fun ZoomBar(
    zoomLabel: Int,
    onIn: () -> Unit,
    onOut: () -> Unit,
    onReset: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(horizontal = 8.dp, vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TextButton(onClick = onOut) { Text("−") }
        Text(
            text = stringResource(R.string.zoom_level, zoomLabel),
            style = MaterialTheme.typography.labelLarge,
        )
        TextButton(onClick = onIn) { Text("+") }
        Spacer(Modifier.width(8.dp))
        TextButton(onClick = onReset) { Text(stringResource(R.string.zoom_reset)) }
    }
}

@Composable
private fun SearchBar(
    query: String,
    searching: Boolean,
    matchCount: Int,
    onQueryChange: (String) -> Unit,
    onSubmit: () -> Unit,
    onJump: (Int) -> Unit,
) {
    Column(modifier = Modifier.fillMaxWidth().padding(8.dp)) {
        OutlinedTextField(
            value = query,
            onValueChange = onQueryChange,
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text(stringResource(R.string.search_hint)) },
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { onSubmit() }),
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            TextButton(onClick = onSubmit) { Text(stringResource(R.string.search)) }
            Spacer(Modifier.width(8.dp))
            Text(
                text = when {
                    searching -> stringResource(R.string.search_running)
                    query.isBlank() -> ""
                    matchCount == 0 -> stringResource(R.string.search_none)
                    else -> stringResource(R.string.search_matches, matchCount)
                },
                style = MaterialTheme.typography.labelMedium,
            )
        }
        if (matchCount > 0) {
            Row(modifier = Modifier.horizontalScroll(rememberScrollState())) {
                for (index in 0 until minOf(matchCount, 40)) {
                    TextButton(onClick = { onJump(index) }) {
                        Text(stringResource(R.string.search_jump, index + 1))
                    }
                }
            }
        }
    }
}

@Composable
private fun PageList(
    model: ViewerViewModel,
    pageCount: Int,
    zoom: Float,
    listState: androidx.compose.foundation.lazy.LazyListState,
) {
    val pages = remember(pageCount) { (0 until pageCount).toList() }
    val density = LocalDensity.current
    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        // One measurement for the whole list: the width a page gets at 100%.
        val viewportWidthPx = with(density) { (maxWidth - 16.dp).coerceAtLeast(0.dp).toPx() }
            .toInt()
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(8.dp),
        ) {
            items(pages, key = { it }) { index ->
                PageCard(
                    model = model,
                    index = index,
                    pageCount = pageCount,
                    zoom = zoom,
                    viewportWidthPx = viewportWidthPx,
                )
                Spacer(Modifier.height(12.dp))
            }
        }
    }
}

@Composable
private fun PageCard(
    model: ViewerViewModel,
    index: Int,
    pageCount: Int,
    zoom: Float,
    viewportWidthPx: Int,
) {
    val density = LocalDensity.current
    var aspect by remember(index) { mutableStateOf(1f / 1.414f) }
    var bitmap by remember(index) { mutableStateOf<android.graphics.Bitmap?>(null) }

    LaunchedEffect(index) {
        aspect = model.pageAspectRatio(index)
    }

    val wanted = renderWidth(viewportWidthPx, zoom)

    LaunchedEffect(index, wanted) {
        if (wanted > 0) {
            bitmap = model.renderPage(index, wanted)
        }
    }

    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = stringResource(R.string.page_of, index + 1, pageCount),
            style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(start = 4.dp, bottom = 4.dp),
        )
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
        ) {
            Card(shape = RoundedCornerShape(4.dp)) {
                Box(
                    modifier = Modifier
                        .width(with(density) { wanted.coerceAtLeast(1).toDp() })
                        .aspectRatio(if (aspect > 0f) aspect else 1f / 1.414f)
                        .background(Color.White),
                ) {
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
            }
        }
    }
}

@Composable
private fun PasswordDialog(
    attemptsLeft: Int,
    lastWasWrong: Boolean,
    onSubmit: (String) -> Unit,
    onCancel: () -> Unit,
) {
    var value by remember { mutableStateOf("") }
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
                    )
                }
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = value,
                    onValueChange = { value = it },
                    singleLine = true,
                    label = { Text(stringResource(R.string.password_hint)) },
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    keyboardActions = KeyboardActions(onDone = { onSubmit(value) }),
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { onSubmit(value) }) { Text(stringResource(R.string.unlock)) }
        },
        dismissButton = {
            TextButton(onClick = onCancel) { Text(stringResource(R.string.cancel)) }
        },
    )
}

@Composable
private fun FailureDialog(reason: Failure, onClose: () -> Unit) {
    val message = when (reason) {
        Failure.UNREADABLE -> R.string.failed_unreadable
        Failure.TOO_LARGE -> R.string.failed_too_large
        Failure.WRONG_PASSWORD_TOO_OFTEN -> R.string.failed_wrong_password
        Failure.NO_PAGES -> R.string.failed_no_pages
        Failure.CANNOT_READ_FILE -> R.string.failed_cannot_read
    }
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text(stringResource(R.string.app_name)) },
        text = { Text(stringResource(message)) },
        confirmButton = { TextButton(onClick = onClose) { Text(stringResource(R.string.close)) } },
    )
}

@Composable
private fun InfoDialog(name: String, pageCount: Int, info: DocumentInfo, onClose: () -> Unit) {
    val permissions = buildList {
        if (info.mayPrint) add(stringResource(R.string.info_permission_print))
        if (info.mayCopy) add(stringResource(R.string.info_permission_copy))
        if (info.mayEdit) add(stringResource(R.string.info_permission_edit))
        if (info.mayAnnotate) add(stringResource(R.string.info_permission_annotate))
    }
    val none = stringResource(R.string.info_none)
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text(stringResource(R.string.info_title)) },
        text = {
            Column {
                Text(name, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(8.dp))
                InfoRow(stringResource(R.string.info_format), info.format ?: none)
                InfoRow(stringResource(R.string.info_pages), pageCount.toString())
                InfoRow(
                    stringResource(R.string.info_encryption),
                    info.encryption?.takeIf { info.isEncrypted } ?: none,
                )
                InfoRow(
                    stringResource(R.string.info_permissions),
                    permissions.joinToString(", ").ifEmpty { none },
                )
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text(stringResource(R.string.close)) } },
    )
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
        Text(text = "$label: ", style = MaterialTheme.typography.labelMedium)
        Text(text = value, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun AboutDialog(onClose: () -> Unit) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text(stringResource(R.string.app_name)) },
        text = {
            Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                Text(stringResource(R.string.about_version, BuildConfig.VERSION_NAME))
                Spacer(Modifier.height(8.dp))
                Text(stringResource(R.string.about_body))
                Spacer(Modifier.height(16.dp))
                Text(
                    text = stringResource(R.string.about_not_yet_title),
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(4.dp))
                Text(stringResource(R.string.about_not_yet))
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text(stringResource(R.string.close)) } },
    )
}
