package com.opensourceortho.lite

import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import java.security.MessageDigest
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Recorded sample visits are view-only and never added to the uploaded case. */
@Composable
fun TeethAndTimeScreen(state: LiteUiState, model: LiteFlowViewModel) {
    val context = LocalContext.current
    val history = remember {
        runCatching { context.assets.open("history.json").bufferedReader().use { SampleHistory.decode(it.readText()) } }
    }
    val sample = history.getOrNull()
    var visitIndex by rememberSaveable { mutableIntStateOf(0) }
    var archIndex by rememberSaveable { mutableIntStateOf(0) }
    var importedIndex by rememberSaveable { mutableIntStateOf(0) }
    var showSample by rememberSaveable { mutableStateOf(false) }
    val imported = state.scans.filter { it.isStl && it.localUri != null }
    val usingSample = showSample || imported.isEmpty()
    val visit = sample?.visits?.getOrNull(visitIndex)
    val arch = visit?.arches?.getOrNull(archIndex)
    val selected = imported.getOrNull(importedIndex)
    val loadID = if (usingSample) arch?.sha256 else selected?.localUri
    var mesh by remember(loadID) { mutableStateOf<StlMesh?>(null) }
    var error by remember(loadID) { mutableStateOf<String?>(null) }
    var surface by remember { mutableStateOf<ScanSurfaceView?>(null) }

    LaunchedEffect(loadID) {
        if (loadID == null) { error = "Scan could not be loaded."; return@LaunchedEffect }
        val result = withContext(Dispatchers.IO) {
            val jobContext = currentCoroutineContext()
            runCatching {
                val stream = if (usingSample) context.assets.open("sample-scans/${arch!!.filename}")
                    else context.contentResolver.openInputStream(Uri.parse(selected!!.localUri))!!
                val bytes = stream.use { it.readBytesLimited() }
                if (usingSample) {
                    val hash = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
                    require(hash == arch!!.sha256) { "Sample scan failed its integrity check." }
                }
                StlMesh.decode(bytes) { jobContext.ensureActive() }
            }
        }
        mesh = result.getOrNull()
        error = result.exceptionOrNull()?.message
    }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(surface, lifecycle) {
        val view = surface
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_PAUSE) view?.onPause()
            if (event == Lifecycle.Event.ON_RESUME) view?.onResume()
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer); view?.onPause() }
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(if (usingSample) "${sample?.pseudonym ?: "Sample"} · scan history" else "Your scan",
            style = MaterialTheme.typography.headlineSmall)
        if (imported.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                FilterChip(!showSample, { showSample = false }, label = { Text("Your files") })
                FilterChip(showSample, { showSample = true }, label = { Text(sample?.pseudonym ?: "Sample") })
            }
        }
        if (usingSample && sample != null && visit != null) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                sample.visits.forEachIndexed { i, item ->
                    FilterChip(visitIndex == i, { visitIndex = i }, label = { Text(item.label) })
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                visit.arches.forEachIndexed { i, item ->
                    FilterChip(archIndex == i, { archIndex = i }, label = { Text(item.name) })
                }
            }
            Text("${visit.label} · ${visit.date}", style = MaterialTheme.typography.bodyMedium)
        } else if (imported.isNotEmpty()) {
            imported.forEachIndexed { i, scan ->
                FilterChip(importedIndex == i, { importedIndex = i }, label = { Text(scan.fileName) })
            }
        }
        Box(Modifier.fillMaxWidth().height(320.dp).clip(RoundedCornerShape(18.dp))
            .background(Color(0xFF121A26)), contentAlignment = Alignment.Center) {
            val loaded = mesh
            if (loaded != null) {
                key(loadID) {
                    AndroidView(factory = {
                        ScanSurfaceView(it, loaded, if (usingSample) arch!!.displayRotation else listOf(1f,1f,1f))
                            .also { view -> surface = view }
                    }, modifier = Modifier.fillMaxSize(), onRelease = { it.onPause() })
                }
            } else if (error != null) Text(error!!, color = Color.White, modifier = Modifier.padding(16.dp))
            else CircularProgressIndicator()
        }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Drag to rotate · pinch to zoom", style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { surface?.resetView() }) { Text("Reset view") }
        }
        mesh?.let { Text("Complete STL surface · ${it.triangleCount} triangles", style = MaterialTheme.typography.bodySmall) }
        if (usingSample && visit != null) {
            Text(visit.detail, style = MaterialTheme.typography.bodyMedium)
            Text("Two recorded visits. Each arch is fitted independently to the view. Scale and registration between visits are unverified; no tooth movement is inferred.",
                style = MaterialTheme.typography.bodySmall)
        } else if (imported.isNotEmpty()) {
            Text("Original uploaded geometry. No simulated movement is applied.", style = MaterialTheme.typography.bodySmall)
            Button(onClick = model::generate, enabled = !state.isGenerating) { Text("Generate for review") }
        }
        state.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
    }
}

private fun java.io.InputStream.readBytesLimited(): ByteArray {
    val output = java.io.ByteArrayOutputStream()
    val buffer = ByteArray(8192)
    while (true) {
        val count = read(buffer)
        if (count < 0) break
        require(output.size() + count <= StlMesh.MAX_BYTES) { "Scan exceeds the mobile preview limit. Open it in the browser." }
        output.write(buffer, 0, count)
    }
    return output.toByteArray()
}
