package com.opensourceortho.lite

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
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Observed surfaces only: synchronized cameras and a continuous reveal, never a fabricated morph. */
@Composable
fun TeethAndTimeScreen(state: LiteUiState, model: LiteFlowViewModel) {
    val context = LocalContext.current
    val history = remember {
        runCatching { context.assets.open("history.json").bufferedReader().use { SampleHistory.decode(it.readText()) } }
    }
    val sample = history.getOrNull()
    var arch by rememberSaveable { mutableStateOf("Both") }
    var importedIndex by rememberSaveable { mutableIntStateOf(-1) }
    var showSample by rememberSaveable { mutableStateOf(false) }
    var progress by rememberSaveable { mutableFloatStateOf(0f) }
    val imported = state.scans.filter { it.modality in listOf("scan", "stl") }
    val usingSample = showSample || imported.isEmpty()
    val chosen = if (importedIndex < 0) imported.take(2) else imported.drop(importedIndex).take(1)
    val loadID = if (usingSample) "sample" else chosen.joinToString { "${it.localUri}:${it.fileName}" }
    var presentation by remember(loadID) { mutableStateOf<ScanPresentation?>(null) }
    var error by remember(loadID) { mutableStateOf<String?>(null) }
    var surface by remember { mutableStateOf<ScanSurfaceView?>(null) }
    LaunchedEffect(loadID) {
        try {
            presentation = withContext(Dispatchers.IO) {
                val job = currentCoroutineContext()
                if (usingSample) ScanPresentationLoader.sample(context, sample ?: error("Sample history could not be loaded.")) { job.ensureActive() }
                else ScanPresentationLoader.imported(context, chosen) { job.ensureActive() }
            }
        } catch (e: kotlinx.coroutines.CancellationException) { throw e }
        catch (e: Exception) { error = e.message ?: "Scan could not be loaded." }
    }
    val visible = remember(presentation, arch, usingSample) {
        if (usingSample) presentation?.selecting(arch) else presentation
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
        Text(if (usingSample) "${sample?.pseudonym ?: "Sample"} · scan comparison" else "Your 3D scans",
            style = MaterialTheme.typography.headlineSmall)
        if (imported.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                FilterChip(!showSample, { showSample = false }, label = { Text("Your files") })
                FilterChip(showSample, { showSample = true }, label = { Text(sample?.pseudonym ?: "Sample") })
            }
        }
        if (usingSample) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                listOf("Both", "Upper", "Lower").forEach { value ->
                    FilterChip(arch == value, { arch = value }, label = { Text(value) })
                }
            }
            Text(if (arch == "Both") "Upper above · lower below" else "$arch arch", style = MaterialTheme.typography.bodySmall)
        } else {
            if (imported.size > 1) FilterChip(importedIndex == -1, { importedIndex = -1 }, label = { Text("First two files") })
            imported.forEachIndexed { i, scan ->
                FilterChip(importedIndex == i, { importedIndex = i }, label = { Text(scan.fileName) })
            }
        }
        Box(Modifier.fillMaxWidth().height(if (arch == "Both" || !usingSample) 400.dp else 320.dp)
            .clip(RoundedCornerShape(18.dp)).background(Color(0xFF111724)), contentAlignment = Alignment.Center) {
            if (error != null) Text(error!!, color = Color.White, modifier = Modifier.padding(16.dp))
            else if (visible != null) {
                key(loadID, if (usingSample) arch else "imports") {
                    AndroidView(factory = {
                        ScanSurfaceView(it, visible) { message -> error = message }.also { view -> surface = view }
                    }, update = { it.reveal(if (usingSample) progress else 0f) }, modifier = Modifier.fillMaxSize(),
                        onRelease = { it.onPause(); if (surface === it) surface = null })
                }
            } else CircularProgressIndicator()
        }
        if (usingSample) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text("Baseline"); Text("Week 7") }
            Slider(value = progress, onValueChange = { progress = when { it < 0.01f -> 0f; it > 0.99f -> 1f; else -> it } }, valueRange = 0f..1f,
                modifier = Modifier.semantics { contentDescription = "Compare recorded scans" })
            Text(when (progress) {
                0f -> "Baseline · ${sample?.visits?.firstOrNull()?.date ?: ""}"
                1f -> "Week 7 · ${sample?.visits?.lastOrNull()?.date ?: ""}"
                else -> "Before / after reveal · ${(progress*100).toInt()}% week 7"
            }, style = MaterialTheme.typography.bodySmall)
        }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween) {
            Text("Drag model to rotate · pinch to zoom", style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { surface?.resetView() }) { Text("Reset view") }
        }
        visible?.let { loaded ->
            val layers = if (usingSample && progress == 1f) loaded.after else loaded.before
            layers.forEach { layer ->
                Text("${if (usingSample && progress > 0f && progress < 1f) "Baseline · " else ""}${layer.label}: " +
                    if (layer.mesh.isPointCloud) "Point cloud · ${layer.mesh.vertexCount} points" else "Complete surface · ${layer.mesh.triangleCount} triangles",
                    style = MaterialTheme.typography.bodySmall)
            }
        }
        if (usingSample) {
            Text("Drag the slider to reveal the two recorded scans. Each arch is positioned separately for viewing, not as a registered bite. No intermediate movement is simulated; scale and registration between visits are unverified.",
                style = MaterialTheme.typography.bodySmall)
        } else {
            Text("Geometry-only preview; textures are not loaded. Point clouds are shown as points. Units are unverified.", style = MaterialTheme.typography.bodySmall)
            if (state.scans.isNotEmpty() && state.scans.all { it.isStl }) {
                Button(onClick = model::generate, enabled = !state.isGenerating && visible != null && error == null) { Text("Generate for review") }
            } else Text("Use the browser/full engine for review of other scan formats.", style = MaterialTheme.typography.bodySmall)
        }
        state.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
    }
}
