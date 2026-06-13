package com.opensourceortho.lite

import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color as AndroidColor
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.net.Uri
import android.os.Bundle
import android.os.CancellationSignal
import android.os.ParcelFileDescriptor
import android.print.PageRange
import android.print.PrintAttributes
import android.print.PrintDocumentAdapter
import android.print.PrintDocumentInfo
import android.print.PrintManager
import android.provider.OpenableColumns
import android.view.MotionEvent
import android.view.View
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

// Lite-flow screens. Mobile can synthesize a limited STL-only review if the
// engine is offline; CBCT/DICOM and mesh-backed edits remain browser/full-engine work.

/** Step 1: pick scan records, supporting photos, or browser-generated review packages. */
@Composable
fun UploadScreen(state: LiteUiState, model: LiteFlowViewModel) {
    val context = LocalContext.current
    var pendingModality by remember { mutableStateOf("stl") }
    var selectedImport by remember { mutableStateOf(importOptions.first()) }
    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenMultipleDocuments(),
    ) { uris ->
        uris.forEach { uri ->
            context.contentResolver.takePersistableReadPermission(uri)
            if (pendingModality == "browser-review") {
                runCatching { context.storedPlanReview(uri) }
                    .onSuccess(model::importBrowserReview)
                    .onFailure { model.reportImportError("Could not import browser review: ${it.message}") }
            } else {
                model.addScan(context.selectedScan(uri, pendingModality))
            }
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
    ) {
        Text("Upload patient files", style = MaterialTheme.typography.titleLarge)
        Text(
            "Mobile renders selected STL scans for review. CBCT/DICOM can be attached for engine/browser handoff; full volume review still needs the browser/full engine.",
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
        )
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text("Choose what to add", style = MaterialTheme.typography.titleSmall)
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    importOptions.take(2).forEach { option ->
                        ImportOptionCard(option, selectedImport == option, Modifier.weight(1f)) {
                            selectedImport = option
                        }
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    importOptions.drop(2).forEach { option ->
                        ImportOptionCard(option, selectedImport == option, Modifier.weight(1f)) {
                            selectedImport = option
                        }
                    }
                }
                Button(onClick = {
                    pendingModality = selectedImport.modality
                    picker.launch(selectedImport.mimeTypes)
                }, modifier = Modifier.fillMaxWidth()) { Text(selectedImport.actionTitle) }
            }
        }
        if (state.storedReviews.isNotEmpty()) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text("Stored browser reviews", style = MaterialTheme.typography.labelMedium)
                    state.storedReviews.forEach { review ->
                        Column {
                            Text(review.fileName, style = MaterialTheme.typography.bodySmall)
                            Text(
                                review.caseReview?.mobileSummary ?: "${review.byteCount} bytes",
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                }
            }
        }
    }
}

private data class ImportOption(
    val title: String,
    val subtitle: String,
    val actionTitle: String,
    val modality: String,
    val mimeTypes: Array<String>,
)

private val importOptions = listOf(
    ImportOption("STL scans", "3D surface files", "Choose STL scans", "stl", arrayOf("model/stl", "application/sla", "application/octet-stream", "*/*")),
    ImportOption("CBCT / DICOM", "Attach for handoff", "Choose CBCT / DICOM", "cbct", arrayOf("application/zip", "application/dicom", "application/octet-stream", "*/*")),
    ImportOption("Photos", "Images from device", "Choose photos", "photo", arrayOf("image/*", "application/octet-stream", "*/*")),
    ImportOption("Browser review", "Case JSON", "Import review JSON", "browser-review", arrayOf("application/json", "text/json", "text/plain", "*/*")),
)

@Composable
private fun ImportOptionCard(option: ImportOption, selected: Boolean, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Column(
        modifier = modifier
            .border(
                width = if (selected) 2.dp else 1.dp,
                color = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant,
                shape = RoundedCornerShape(10.dp),
            )
            .clickable(onClick = onClick)
            .padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(option.title, style = MaterialTheme.typography.bodyMedium)
        Text(option.subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** Step 2: staged teeth preview and timeline controls. */
@Composable
fun TeethAndTimeScreen(state: LiteUiState, model: LiteFlowViewModel) {
    val context = LocalContext.current
    var stage by remember { mutableFloatStateOf(0f) }
    var showDemoSample by remember { mutableStateOf(false) }
    val hasSelectedStl = state.scans.any { it.isStl }
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
    ) {
        Text("Teeth + time", style = MaterialTheme.typography.titleLarge)
        AndroidView(
            factory = { DentalPreview3dView(it) },
            update = {
                it.stage = stage
                it.scans = state.scans
            },
            modifier = Modifier.fillMaxWidth().height(340.dp),
        )
        if (!hasSelectedStl) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Button(onClick = { showDemoSample = !showDemoSample }) {
                    Text(if (showDemoSample) "Hide demo sample" else "Demo sample")
                }
                if (showDemoSample) {
                    Button(onClick = {
                        model.addDevSample(context.devSampleScans())
                        showDemoSample = false
                    }) { Text("Use full-arch dev sample") }
                    Text(
                        "Loads bundled upper and lower STL scans for a full mobile rendering preview.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center,
                    )
                }
            }
        }
        Slider(value = stage, onValueChange = { stage = it }, valueRange = 0f..12f, steps = 11)
        Text("Stage ${stage.toInt()} of 12", style = MaterialTheme.typography.bodyMedium)
        Text("${state.scans.size} file(s) selected", style = MaterialTheme.typography.titleMedium)
        Text(
            "STL scans render from the selected file when available. CBCT/DICOM is attached for engine/browser review; native volume rendering is not in lite yet.",
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
        )
        state.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, textAlign = TextAlign.Center)
        }
        Button(onClick = model::generate, enabled = !state.isGenerating) {
            if (state.isGenerating) CircularProgressIndicator(Modifier.height(20.dp))
            else Text("Generate for review")
        }
    }
}

/** Step 3: engine verdict + steps. Verdict is CONSISTENT/ISSUES only. */
@Composable
fun ReviewScreen(state: LiteUiState, model: LiteFlowViewModel) {
    val context = LocalContext.current
    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Engine verdict", style = MaterialTheme.typography.labelMedium)
                Text(
                    state.result?.correctness?.verdict?.let(SafetyText::verdictLabel)
                        ?: "Generate a review to see engine findings.",
                    style = MaterialTheme.typography.titleMedium,
                )
            }
        }
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Pipeline", style = MaterialTheme.typography.labelMedium)
                val steps = state.result?.steps.orEmpty()
                if (steps.isEmpty()) {
                    Text("No engine steps yet.", style = MaterialTheme.typography.bodySmall)
                } else {
                    steps.forEach { step ->
                        Column {
                            Text(step.name, style = MaterialTheme.typography.bodyMedium)
                            Text("${step.status}: ${step.detail}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
        state.result?.caveat?.let {
            Card(modifier = Modifier.fillMaxWidth()) {
                Text(
                    it,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(16.dp),
                )
            }
        }
        state.result?.warnings?.takeIf { it.isNotEmpty() }?.let { warnings ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text("Mobile limits", style = MaterialTheme.typography.labelMedium)
                    warnings.forEach { warning ->
                        Text(warning, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
        if (state.storedReviews.isNotEmpty()) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text("Stored browser reviews", style = MaterialTheme.typography.labelMedium)
                    state.storedReviews.forEach { review ->
                        Column {
                            Text(review.fileName, style = MaterialTheme.typography.bodyMedium)
                            val caseReview = review.caseReview
                            if (caseReview == null) {
                                Text(
                                    "${review.byteCount} bytes stored on this device for review/sharing. Open the browser workspace to edit the source plan.",
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            } else {
                                Text(caseReview.reviewTier.label, style = MaterialTheme.typography.bodySmall)
                                Text(
                                    "${caseReview.unresolvedDataGaps.size} unresolved data gaps. Mobile edit lock: browser engine required.",
                                    style = MaterialTheme.typography.bodySmall,
                                )
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    caseReview.handoff.openUrl?.let { url ->
                                        Button(onClick = { context.openHandoff(url) }) {
                                            Text("Open browser case")
                                        }
                                    }
                                    Button(onClick = { context.openHandoff(caseReview.handoff.deepLink) }) {
                                        Text("Open app link")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Tray estimate", style = MaterialTheme.typography.labelMedium)
                val trayCount = state.result?.timeline?.stageCount
                    ?: state.result?.stageCount
                    ?: maxOf(1, state.scans.size * 6)
                Text("Initial trays: $trayCount", style = MaterialTheme.typography.bodyMedium)
                state.result?.timeline?.let { timeline ->
                    Text("Wear interval: ${timeline.wearIntervalDays} days")
                    Text(
                        "Projected duration: ${
                            String.format(Locale.US, "%.1f", timeline.projectedDurationWeeks)
                        } weeks",
                    )
                } ?: Text(
                    "Generate a review to estimate trays from the engine timeline.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Refinement options", style = MaterialTheme.typography.labelMedium)
                RefinementRow("No refinement", "Proceed with the initial generated sequence for review.")
                RefinementRow("Mid-course scan", "Add a new STL/CBCT record if tracking drifts from plan.")
                RefinementRow("Attachment/IPR review", "Flag the plan for clinician review of auxiliaries and spacing.")
                RefinementRow("Additional trays", "Plan a second pass after reviewing the final-stage fit.")
            }
        }
        Button(onClick = model::showPrintAndSend) { Text("Print and send") }
    }
}

@Composable
private fun RefinementRow(title: String, detail: String) {
    Column {
        Text(title, style = MaterialTheme.typography.bodyMedium)
        Text(detail, style = MaterialTheme.typography.bodySmall)
    }
}

/** Step 4: export package for print / 3D-printer handoff. */
@Composable
fun PrintAndSendScreen(model: LiteFlowViewModel) {
    val context = LocalContext.current
    var packageJson by remember { mutableStateOf(model.exportPackageJson()) }
    var packageStatus by remember { mutableStateOf(printPackageStatus(packageJson)) }

    fun refreshPackage() {
        packageJson = model.exportPackageJson()
        packageStatus = printPackageStatus(packageJson)
    }

    val exportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/json"),
    ) { uri ->
        packageStatus = when {
            uri == null -> "Export cancelled."
            context.writeTextToUri(uri, packageJson) -> "Package exported."
            else -> "Could not export package."
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Print and send", style = MaterialTheme.typography.titleLarge)
        Text(
            "Export the generated package for clinician review, lab handoff, or 3D-printer preparation.",
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
        )
        Text(
            packageStatus,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
        Button(onClick = ::refreshPackage) { Text("Refresh package") }
        Button(onClick = {
            exportLauncher.launch("opensource-ortho-print-package.json")
        }) { Text("Export print package") }
        Button(onClick = {
            packageStatus = runCatching {
                context.sharePackage(packageJson)
                "Choose an app to send the package."
            }.getOrElse { "Could not open share sheet." }
        }) { Text("Send to 3D printer") }
        Button(onClick = {
            packageStatus = runCatching {
                context.printPackage(packageJson)
                "Print dialog opened."
            }.getOrElse { "Could not open print dialog." }
        }) { Text("Open print dialog") }
        Text(
            "Android has no universal 3D-printer API; this opens document export, share targets, and print services.",
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
fun SettingsScreen() {
    var glossaryQuery by remember { mutableStateOf("") }
    var showAboutDetails by remember { mutableStateOf(false) }
    var numberingSystem by remember { mutableStateOf(ToothNumberingSystem.FDI) }
    val filteredGlossary = remember(glossaryQuery) {
        val needle = glossaryQuery.trim().lowercase()
        if (needle.isEmpty()) {
            fullGlossaryTerms
        } else {
            fullGlossaryTerms.filter { (term, definition) ->
                term.lowercase().contains(needle) || definition.lowercase().contains(needle)
            }
        }
    }
    val groupedGlossary = remember(filteredGlossary) {
        filteredGlossary
            .groupBy { (term, _) -> term.firstOrNull()?.uppercaseChar()?.toString() ?: "#" }
            .toSortedMap()
    }
    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Settings", style = MaterialTheme.typography.titleLarge)
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("About", style = MaterialTheme.typography.labelMedium)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("OpenSource Ortho Lite", style = MaterialTheme.typography.bodyMedium)
                    Spacer(modifier = Modifier.width(16.dp).weight(1f))
                    Text(
                        "Version ${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.End,
                    )
                }
                Column(
                    modifier = Modifier.fillMaxWidth().clickable { showAboutDetails = !showAboutDetails },
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text("Mobile app and browser accuracy", style = MaterialTheme.typography.bodyMedium)
                    Text(
                        if (showAboutDetails) "Hide details" else "Tap for details",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    if (showAboutDetails) {
                        Text(
                            "OpenSource Ortho Lite is a mobile review and handoff companion for scan intake, quick case review, glossary lookup, and sharing packages.",
                            style = MaterialTheme.typography.bodySmall,
                        )
                        Text(
                            "For large STL/CBCT files, detailed segmentation, full 3D rendering, restaging, and final print-package QA, use the full browser version. Mobile previews may simplify geometry when files are too large or unsupported.",
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
        }
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Glossary", style = MaterialTheme.typography.labelMedium)
                OutlinedTextField(
                    value = glossaryQuery,
                    onValueChange = { glossaryQuery = it },
                    label = { Text("Search glossary") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                groupedGlossary.forEach { (letter, terms) ->
                    Text(
                        letter,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    terms.sortedBy { it.first }.forEach { (term, definition) ->
                        GlossaryRow(term, definition)
                    }
                }
                if (filteredGlossary.isEmpty()) {
                    Text("No matching terms.", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Teeth map", style = MaterialTheme.typography.labelMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { numberingSystem = ToothNumberingSystem.FDI }) {
                        Text("FDI")
                    }
                    Button(onClick = { numberingSystem = ToothNumberingSystem.UNIVERSAL }) {
                        Text("Universal")
                    }
                }
                Text(numberingSystem.detail, style = MaterialTheme.typography.bodySmall)
                AndroidView(
                    factory = { TeethMapView(it) },
                    update = { it.numberingSystem = numberingSystem },
                    modifier = Modifier.fillMaxWidth().height(390.dp),
                )
                Text("Upper right: ${numberingSystem.upperRight.joinToString(" ")}")
                Text("Upper left: ${numberingSystem.upperLeft.joinToString(" ")}")
                Text("Lower left: ${numberingSystem.lowerLeft.joinToString(" ")}")
                Text("Lower right: ${numberingSystem.lowerRight.joinToString(" ")}")
            }
        }
    }
}

@Composable
private fun GlossaryRow(term: String, definition: String) {
    Column {
        Text(term, style = MaterialTheme.typography.bodyMedium)
        Text(definition, style = MaterialTheme.typography.bodySmall)
    }
}

private fun android.content.ContentResolver.takePersistableReadPermission(uri: Uri) {
    try {
        takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
    } catch (_: SecurityException) {
        // Some providers grant transient read access only; the selected metadata
        // is still captured immediately for the lite request.
    }
}

private fun Context.selectedScan(uri: Uri, modality: String): SelectedScan {
    val name = contentResolver.displayName(uri) ?: uri.lastPathSegment ?: "selected-file"
    val byteCount = contentResolver.byteCount(uri)
    return SelectedScan(
        fileName = name,
        arch = inferredArch(name),
        byteCount = byteCount,
        modality = modality,
        localUri = uri.toString(),
    )
}

private fun Context.storedPlanReview(uri: Uri): StoredPlanReview {
    val name = contentResolver.displayName(uri) ?: uri.lastPathSegment ?: "browser-review.json"
    val text = contentResolver.openInputStream(uri)?.use { stream ->
        stream.readBytes().toString(Charsets.UTF_8)
    } ?: ""
    return StoredPlanReview.importCaseReview(
        fileName = name,
        byteCount = text.toByteArray(Charsets.UTF_8).size,
        jsonText = text,
    )
}

private fun Context.openHandoff(target: String) {
    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(target)))
}

private fun Context.devSampleScans(): List<SelectedScan> =
    listOf(
        devSampleScan(
            fileName = "dev-sample-upper.stl",
            arch = "upper",
            resourceId = R.raw.dev_sample_upper,
        ),
        devSampleScan(
            fileName = "dev-sample-lower.stl",
            arch = "lower",
            resourceId = R.raw.dev_sample_lower,
        ),
    )

private fun Context.devSampleScan(fileName: String, arch: String, resourceId: Int): SelectedScan =
    SelectedScan(
        fileName = fileName,
        arch = arch,
        byteCount = rawResourceByteCount(resourceId),
        modality = "stl",
        localUri = "android.resource://$packageName/$resourceId",
    )

private fun Context.rawResourceByteCount(resourceId: Int): Int =
    resources.openRawResourceFd(resourceId)?.use { descriptor ->
        descriptor.length.coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
    } ?: 0

private fun android.content.ContentResolver.displayName(uri: Uri): String? =
    query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
        if (cursor.moveToFirst()) cursor.getString(0) else null
    }

private fun android.content.ContentResolver.byteCount(uri: Uri): Int =
    query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { cursor ->
        if (cursor.moveToFirst() && !cursor.isNull(0)) cursor.getLong(0).coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
        else 0
    } ?: 0

private fun inferredArch(fileName: String): String? {
    val lower = fileName.lowercase()
    return when {
        lower.contains("upper") || lower.contains("maxillary") -> "upper"
        lower.contains("lower") || lower.contains("mandibular") -> "lower"
        else -> null
    }
}

private fun printPackageStatus(packageJson: String): String =
    "Package ready: ${packageSizeLabel(packageJson)}"

private fun packageSizeLabel(packageJson: String): String {
    val bytes = packageJson.toByteArray(Charsets.UTF_8).size
    return when {
        bytes < 1024 -> "$bytes bytes"
        bytes < 1024 * 1024 -> "${bytes / 1024} KB"
        else -> "${bytes / (1024 * 1024)} MB"
    }
}

private fun Context.writeTextToUri(uri: Uri, text: String): Boolean =
    runCatching {
        contentResolver.openOutputStream(uri)?.use { stream ->
            stream.write(text.toByteArray(Charsets.UTF_8))
            true
        } ?: false
    }.getOrDefault(false)

private fun Context.sharePackage(packageJson: String) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "application/json"
        putExtra(Intent.EXTRA_SUBJECT, "OpenSource Ortho print package")
        putExtra(Intent.EXTRA_TEXT, packageJson)
    }
    startActivity(Intent.createChooser(intent, "Send print package"))
}

private fun Context.printPackage(packageJson: String) {
    val printManager = getSystemService(Context.PRINT_SERVICE) as PrintManager
    printManager.print(
        "OpenSource Ortho package",
        JsonPrintDocumentAdapter(packageJson),
        PrintAttributes.Builder().build(),
    )
}

private class JsonPrintDocumentAdapter(private val packageJson: String) : PrintDocumentAdapter() {
    override fun onLayout(
        oldAttributes: PrintAttributes?,
        newAttributes: PrintAttributes?,
        cancellationSignal: CancellationSignal?,
        callback: LayoutResultCallback,
        extras: Bundle?,
    ) {
        if (cancellationSignal?.isCanceled == true) {
            callback.onLayoutCancelled()
            return
        }
        callback.onLayoutFinished(
            PrintDocumentInfo.Builder("opensource-ortho-print-package.json")
                .setContentType(PrintDocumentInfo.CONTENT_TYPE_DOCUMENT)
                .build(),
            true,
        )
    }

    override fun onWrite(
        pages: Array<out PageRange>?,
        destination: ParcelFileDescriptor,
        cancellationSignal: CancellationSignal?,
        callback: WriteResultCallback,
    ) {
        if (cancellationSignal?.isCanceled == true) {
            callback.onWriteCancelled()
            return
        }
        FileOutputStream(destination.fileDescriptor).use { output ->
            output.write(packageJson.toByteArray(Charsets.UTF_8))
        }
        callback.onWriteFinished(arrayOf(PageRange.ALL_PAGES))
    }
}

private class DentalPreview3dView(context: Context) : View(context) {
    var stage: Float = 0f
        set(value) {
            field = value
            invalidate()
        }
    var scans: List<SelectedScan> = emptyList()
        set(value) {
            if (field == value) return
            field = value
            meshTriangles = loadFirstStlMesh(value)
            invalidate()
        }

    private var rotation = 0f
    private var lastX = 0f
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private var meshTriangles: List<StlTriangle> = emptyList()

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> lastX = event.x
            MotionEvent.ACTION_MOVE -> {
                rotation += (event.x - lastX) * 0.01f
                lastX = event.x
                invalidate()
            }
        }
        return true
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(AndroidColor.rgb(248, 250, 252))
        paint.textAlign = Paint.Align.CENTER
        paint.textSize = 34f
        paint.color = AndroidColor.rgb(30, 41, 59)
        canvas.drawText("Drag to rotate. Scrub stages below.", width / 2f, 46f, paint)

        if (meshTriangles.isNotEmpty()) {
            drawMesh(canvas, meshTriangles)
            paint.textSize = 24f
            paint.color = AndroidColor.rgb(71, 85, 105)
            canvas.drawText("Rendering selected STL surface", width / 2f, height - 22f, paint)
        } else {
            drawSampleDentalCast(canvas)
            paint.textSize = 24f
            paint.color = AndroidColor.rgb(71, 85, 105)
            val caption = if (scans.any { it.modality == "cbct" }) {
                "CBCT attached; open browser/full engine for volume rendering"
            } else if (scans.any { it.isStl }) {
                "Showing sample teeth preview"
            } else {
                "Add an STL scan to render patient geometry"
            }
            canvas.drawText(caption, width / 2f, height - 22f, paint)
        }
    }

    private fun loadFirstStlMesh(scans: List<SelectedScan>): List<StlTriangle> {
        val triangles = ArrayList<StlTriangle>()
        scans.filter { it.isStl && it.localUri != null }.forEach { scan ->
            val bytes = context.contentResolver.openInputStream(Uri.parse(scan.localUri))?.use { it.readBytes() }
                ?: return@forEach
            triangles += parseStlTriangles(bytes).take(14000)
        }
        return triangles.take(28000)
    }

    private fun drawMesh(canvas: Canvas, triangles: List<StlTriangle>) {
        val bounds = meshBounds(triangles)
        val span = max(bounds[3] - bounds[0], max(bounds[4] - bounds[1], bounds[5] - bounds[2])).coerceAtLeast(1f)
        val scale = min(width, height) * 0.62f / span
        val cx = (bounds[0] + bounds[3]) / 2f
        val cy = (bounds[1] + bounds[4]) / 2f
        val cz = (bounds[2] + bounds[5]) / 2f
        val centerX = width / 2f
        val centerY = height / 2f

        val projected = triangles.mapNotNull { triangle ->
            val a = project(triangle.a, cx, cy, cz, scale, centerX, centerY)
            val b = project(triangle.b, cx, cy, cz, scale, centerX, centerY)
            val c = project(triangle.c, cx, cy, cz, scale, centerX, centerY)
            val light = (kotlin.math.abs(screenNormalZ(a, b, c)) / 1800f).coerceIn(0.18f, 1f)
            ProjectedTriangle(a, b, c, (a[2] + b[2] + c[2]) / 3f, light)
        }.sortedBy { it.depth }

        paint.style = Paint.Style.FILL
        projected.forEach { triangle ->
            val shade = (196 + (triangle.light * 48f).toInt()).coerceIn(170, 244)
            paint.color = AndroidColor.rgb(shade, shade - 4, shade - 18)
            val path = Path().apply {
                moveTo(triangle.a[0], triangle.a[1])
                lineTo(triangle.b[0], triangle.b[1])
                lineTo(triangle.c[0], triangle.c[1])
                close()
            }
            canvas.drawPath(path, paint)
        }

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 0.45f
        paint.color = AndroidColor.argb(56, 99, 90, 70)
        projected.take(6000).forEach { triangle ->
            val path = Path().apply {
                moveTo(triangle.a[0], triangle.a[1])
                lineTo(triangle.b[0], triangle.b[1])
                lineTo(triangle.c[0], triangle.c[1])
                close()
            }
            canvas.drawPath(path, paint)
        }
    }

    private fun project(point: FloatArray, cx: Float, cy: Float, cz: Float, scale: Float, centerX: Float, centerY: Float): FloatArray {
        val x = point[0] - cx
        val y = point[1] - cy
        val z = point[2] - cz
        val rotatedX = x * cos(rotation) - z * sin(rotation)
        val rotatedZ = x * sin(rotation) + z * cos(rotation)
        val tiltedY = y * 0.72f + rotatedZ * 0.18f
        return floatArrayOf(centerX + rotatedX * scale, centerY - tiltedY * scale, rotatedZ)
    }

    private fun screenNormalZ(a: FloatArray, b: FloatArray, c: FloatArray): Float {
        val abX = b[0] - a[0]
        val abY = b[1] - a[1]
        val acX = c[0] - a[0]
        val acY = c[1] - a[1]
        return abX * acY - abY * acX
    }

    private fun meshBounds(triangles: List<StlTriangle>): FloatArray {
        var minX = Float.POSITIVE_INFINITY
        var minY = Float.POSITIVE_INFINITY
        var minZ = Float.POSITIVE_INFINITY
        var maxX = Float.NEGATIVE_INFINITY
        var maxY = Float.NEGATIVE_INFINITY
        var maxZ = Float.NEGATIVE_INFINITY
        triangles.forEach { triangle ->
            listOf(triangle.a, triangle.b, triangle.c).forEach {
                minX = min(minX, it[0]); minY = min(minY, it[1]); minZ = min(minZ, it[2])
                maxX = max(maxX, it[0]); maxY = max(maxY, it[1]); maxZ = max(maxZ, it[2])
            }
        }
        return floatArrayOf(minX, minY, minZ, maxX, maxY, maxZ)
    }

    private fun drawSampleDentalCast(canvas: Canvas) {
        val centerX = width / 2f
        val centerY = height / 2f - 8f
        drawCastBase(canvas, centerX, centerY - 66f, upper = true)
        drawCastBase(canvas, centerX, centerY + 66f, upper = false)
        drawBiteArch(canvas, centerX, centerY - 16f, upper = true)
        drawBiteArch(canvas, centerX, centerY + 16f, upper = false)
    }

    private fun drawCastBase(canvas: Canvas, centerX: Float, baseY: Float, upper: Boolean) {
        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.rgb(205, 200, 181)
        val band = RectF(centerX - 244f, baseY - 44f, centerX + 244f, baseY + 44f)
        canvas.drawRoundRect(band, 26f, 26f, paint)

        paint.color = AndroidColor.rgb(228, 224, 208)
        for (index in 0..10) {
            val centered = index - 5f
            val ridgeWidth = 76f - kotlin.math.abs(centered) * 4f
            val ridgeHeight = 34f - kotlin.math.abs(centered) * 1.4f
            val x = centerX + centered * 44f
            val y = baseY + if (upper) 18f else -18f
            canvas.drawOval(RectF(x - ridgeWidth / 2f, y - ridgeHeight / 2f, x + ridgeWidth / 2f, y + ridgeHeight / 2f), paint)
        }

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.2f
        paint.color = AndroidColor.argb(120, 148, 139, 112)
        canvas.drawRoundRect(band, 26f, 26f, paint)
    }

    private fun drawBiteArch(canvas: Canvas, centerX: Float, centerY: Float, upper: Boolean) {
        val progress = stage / 12f
        for (index in 0 until 16) {
            val centered = index - 7.5f
            val normalized = kotlin.math.abs(centered) / 7.5f
            val curve = (1f - normalized * normalized) * 42f
            val rotated = centered * cos(rotation) * 30f
            val stageOffset = if (centered >= 0f) progress * 12f else -progress * 12f
            val x = centerX + rotated + stageOffset
            val y = centerY + curve * if (upper) 1f else -1f
            val halfWidth = 15f + normalized * 9f
            val halfHeight = 32f - normalized * 9f
            drawSampleTooth(canvas, x, y, halfWidth, halfHeight, upper, normalized)
        }
    }

    private fun drawSampleTooth(canvas: Canvas, x: Float, y: Float, halfWidth: Float, halfHeight: Float, upper: Boolean, normalized: Float) {
        val rect = RectF(x - halfWidth, y - halfHeight, x + halfWidth, y + halfHeight)
        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.rgb(232, 228, 210)
        canvas.drawRoundRect(rect, 10f + normalized * 6f, 10f + normalized * 6f, paint)

        paint.color = AndroidColor.argb(110, 255, 255, 255)
        val shineX = x - halfWidth * 0.35f
        canvas.drawRoundRect(
            RectF(shineX - 3f, y - halfHeight * 0.55f, shineX + 3f, y + halfHeight * 0.08f),
            3f,
            3f,
            paint,
        )

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.4f
        paint.color = AndroidColor.argb(150, 133, 124, 95)
        canvas.drawRoundRect(rect, 10f + normalized * 6f, 10f + normalized * 6f, paint)

        if (normalized < 0.34f) {
            paint.style = Paint.Style.FILL
            paint.color = AndroidColor.rgb(202, 194, 168)
            val rootY = if (upper) rect.top - 18f else rect.bottom + 18f
            val tipY = if (upper) rect.top else rect.bottom
            val path = Path().apply {
                moveTo(x - halfWidth * 0.34f, tipY)
                lineTo(x, rootY)
                lineTo(x + halfWidth * 0.34f, tipY)
                close()
            }
            canvas.drawPath(path, paint)
        }
    }

    private fun parseStlTriangles(bytes: ByteArray): List<StlTriangle> {
        val text = bytes.decodeToString(endIndex = min(bytes.size, 4 * 1024 * 1024))
        if (text.contains("vertex")) {
            val vertices = text.lineSequence()
                .mapNotNull { line ->
                    val parts = line.trim().split(Regex("\\s+"))
                    if (parts.size >= 4 && parts[0] == "vertex") {
                        val x = parts[1].toFloatOrNull()
                        val y = parts[2].toFloatOrNull()
                        val z = parts[3].toFloatOrNull()
                        if (x != null && y != null && z != null) floatArrayOf(x, y, z) else null
                    } else {
                        null
                    }
                }
                .toList()
            return vertices
                .chunked(3)
                .filter { it.size == 3 }
                .map { StlTriangle(it[0], it[1], it[2]) }
        }
        if (bytes.size < 84) return emptyList()
        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        val triangleCount = buffer.getInt(80).coerceAtLeast(0)
        val triangles = ArrayList<StlTriangle>(min(triangleCount, 20000))
        var offset = 84
        repeat(min(triangleCount, 20000)) {
            if (offset + 50 > bytes.size) return@repeat
            offset += 12
            val points = ArrayList<FloatArray>(3)
            repeat(3) {
                val x = buffer.getFloat(offset)
                val y = buffer.getFloat(offset + 4)
                val z = buffer.getFloat(offset + 8)
                points.add(floatArrayOf(x, y, z))
                offset += 12
            }
            triangles.add(StlTriangle(points[0], points[1], points[2]))
            offset += 2
        }
        return triangles
    }

    private data class StlTriangle(
        val a: FloatArray,
        val b: FloatArray,
        val c: FloatArray,
    )

    private data class ProjectedTriangle(
        val a: FloatArray,
        val b: FloatArray,
        val c: FloatArray,
        val depth: Float,
        val light: Float,
    )
}

// BEGIN GENERATED GLOSSARY TERMS
private val fullGlossaryTerms = listOf(
    "Arch" to "One jaw's row of teeth: maxillary (upper) or mandibular (lower).",
    "Attachment" to "A small composite bump bonded to a tooth so an aligner can grip it. Planning intent only, not a force model.",
    "Canine" to "The pointed corner tooth, position 3 in FDI notation.",
    "CBCT" to "Cone-beam CT. The higher-fidelity record for roots and bone when ordered and interpreted by a professional.",
    "Class I bite" to "A common reference bite where the upper and lower first molars fit in the expected front/back relationship. It can still have crowding, spacing, or other issues; the app does not diagnose bite class.",
    "Class II bite" to "A front/back bite pattern where the lower teeth or jaw sit farther back relative to the upper teeth than in Class I. The app can record geometry, but it does not diagnose or correct this relationship.",
    "Class III bite" to "A front/back bite pattern where the lower teeth or jaw sit farther forward relative to the upper teeth than in Class I. The app can visualize scans, but it does not diagnose jaw relationships.",
    "Coordinate frame" to "The axis system movements use. scan-local has z as vertical and x/y in the occlusal plane.",
    "Crowding" to "Too little space, so teeth overlap or twist. The app does not diagnose crowding.",
    "Cumulative pose" to "A tooth's total position after summing every stage up to a selected point.",
    "Data gap" to "A missing record such as roots, CBCT, occlusion, or periodontal status that limits review.",
    "Extrusion" to "Moving a tooth out of the bone, opposite intrusion.",
    "FDI notation" to "Two-digit tooth numbering: first digit is quadrant, second digit counts from the midline.",
    "Finding" to "A structured observation from a deterministic rule or linted advisory review. Never an approval.",
    "Fixed tooth" to "A tooth intended to stay still for part or all of a plan.",
    "Incisor" to "A front cutting tooth, positions 1 and 2.",
    "Intrusion" to "Pushing a tooth into the bone.",
    "IPR" to "Interproximal reduction: planned enamel reduction between adjacent teeth to create space.",
    "Malocclusion" to "A bad bite or misalignment. Class I, II, and III are broad bite-relationship categories, not treatment instructions. The app does not diagnose malocclusion.",
    "Mesh / STL" to "A 3D surface model. STL stands for stereolithography; STL files describe triangle surfaces and carry no units, so units start unverified until confirmed.",
    "Molar" to "A large back chewing tooth, positions 6 through 8.",
    "Movement cap" to "A per-stage review threshold for linear, vertical, angular, and rotation movement.",
    "Occlusion" to "How upper and lower teeth meet when biting.",
    "Premolar" to "A tooth between canine and molars, positions 4 and 5.",
    "Provenance" to "Where data came from: patient-derived, imported, manual, model-generated, or synthetic.",
    "Quadrant" to "One of the four mouth sections; the first digit in FDI notation.",
    "Rotation" to "Turning a tooth around its own long axis.",
    "Segmentation" to "Splitting a whole-arch scan into individual per-tooth meshes.",
    "Spacing" to "Unwanted gaps between teeth.",
    "Stage" to "One aligner-style step containing per-tooth movement values.",
    "Tip" to "Mesiodistal angulation: tilting a tooth forward or backward along the arch.",
    "Torque" to "Buccolingual inclination: tilting the crown inward or outward.",
    "Translation" to "Sliding a tooth in millimeters along x, y, or z.",
    "Units" to "The real-world scale of a scan. Must be confirmed before millimeter checks run.",
    "Wear interval" to "How many days each aligner stage is worn; used for projected duration.",
)
// END GENERATED GLOSSARY TERMS

private enum class ToothNumberingSystem(
    val detail: String,
    val upperRight: List<String>,
    val upperLeft: List<String>,
    val lowerLeft: List<String>,
    val lowerRight: List<String>,
) {
    FDI(
        detail = "Federation Dentaire Internationale (FDI) uses two digits: quadrant first, then tooth position from the midline.",
        upperRight = listOf("18", "17", "16", "15", "14", "13", "12", "11"),
        upperLeft = listOf("21", "22", "23", "24", "25", "26", "27", "28"),
        lowerLeft = listOf("31", "32", "33", "34", "35", "36", "37", "38"),
        lowerRight = listOf("48", "47", "46", "45", "44", "43", "42", "41"),
    ),
    UNIVERSAL(
        detail = "Universal numbering labels permanent teeth 1 through 32, starting at the upper right third molar.",
        upperRight = listOf("1", "2", "3", "4", "5", "6", "7", "8"),
        upperLeft = listOf("9", "10", "11", "12", "13", "14", "15", "16"),
        lowerLeft = listOf("24", "23", "22", "21", "20", "19", "18", "17"),
        lowerRight = listOf("32", "31", "30", "29", "28", "27", "26", "25"),
    );
}

private data class ToothNumber(val fdi: String, val universal: String)

private class TeethMapView(context: Context) : View(context) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    var numberingSystem: ToothNumberingSystem = ToothNumberingSystem.FDI
        set(value) {
            if (field == value) return
            field = value
            invalidate()
        }
    private val upperRight = listOf(
        ToothNumber("18", "1"), ToothNumber("17", "2"), ToothNumber("16", "3"), ToothNumber("15", "4"),
        ToothNumber("14", "5"), ToothNumber("13", "6"), ToothNumber("12", "7"), ToothNumber("11", "8"),
    )
    private val upperLeft = listOf(
        ToothNumber("21", "9"), ToothNumber("22", "10"), ToothNumber("23", "11"), ToothNumber("24", "12"),
        ToothNumber("25", "13"), ToothNumber("26", "14"), ToothNumber("27", "15"), ToothNumber("28", "16"),
    )
    private val lowerLeft = listOf(
        ToothNumber("31", "24"), ToothNumber("32", "23"), ToothNumber("33", "22"), ToothNumber("34", "21"),
        ToothNumber("35", "20"), ToothNumber("36", "19"), ToothNumber("37", "18"), ToothNumber("38", "17"),
    )
    private val lowerRight = listOf(
        ToothNumber("48", "32"), ToothNumber("47", "31"), ToothNumber("46", "30"), ToothNumber("45", "29"),
        ToothNumber("44", "28"), ToothNumber("43", "27"), ToothNumber("42", "26"), ToothNumber("41", "25"),
    )

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val centerX = width / 2f
        val centerY = height / 2f
        val radiusX = minOf(width * 0.37f, 132f)
        val upperY = centerY - 104f
        val lowerY = centerY + 104f

        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.rgb(248, 250, 252)
        canvas.drawRoundRect(0f, 0f, width.toFloat(), height.toFloat(), 36f, 36f, paint)

        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.argb(45, 244, 114, 182)
        canvas.drawOval(RectF(centerX - 74f, upperY + 14f, centerX + 74f, upperY + 88f), paint)
        paint.color = AndroidColor.argb(32, 239, 68, 68)
        canvas.drawOval(RectF(centerX - 80f, lowerY - 88f, centerX + 80f, lowerY - 6f), paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 28f
        paint.color = AndroidColor.argb(86, 244, 114, 182)
        canvas.drawPath(gumPath(centerX, upperY, radiusX, upper = true), paint)
        canvas.drawPath(gumPath(centerX, lowerY, radiusX, upper = false), paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.5f
        paint.color = AndroidColor.rgb(203, 213, 225)
        canvas.drawLine(centerX, 42f, centerX, height - 42f, paint)

        val occlusalGap = Path().apply {
            moveTo(centerX - radiusX + 12f, centerY)
            cubicTo(centerX - 72f, centerY + 18f, centerX + 72f, centerY + 18f, centerX + radiusX - 12f, centerY)
        }
        paint.strokeWidth = 2f
        paint.color = AndroidColor.argb(70, 100, 116, 139)
        canvas.drawPath(occlusalGap, paint)

        paint.style = Paint.Style.FILL
        paint.textAlign = Paint.Align.CENTER
        paint.textSize = 28f
        paint.color = AndroidColor.rgb(71, 85, 105)
        paint.isFakeBoldText = true
        canvas.drawText("Upper", centerX, 40f, paint)
        canvas.drawText("Lower", centerX, height - 28f, paint)

        paint.textSize = 22f
        paint.isFakeBoldText = false
        canvas.drawText("Patient right", 82f, centerY, paint)
        canvas.drawText("Patient left", width - 82f, centerY, paint)

        (upperRight + upperLeft + lowerLeft + lowerRight).forEach { tooth ->
            val point = toothPoint(tooth.fdi, centerX, upperY, lowerY, radiusX)
            val labelPoint = labelPoint(tooth.fdi, centerX, upperY, lowerY, radiusX)
            drawTooth(canvas, point[0], point[1], toothKind(tooth.fdi), tooth.fdi.first() == '1' || tooth.fdi.first() == '2')
            drawToothLabel(canvas, tooth, labelPoint[0], labelPoint[1])
        }
    }

    private fun toothPoint(label: String, centerX: Float, upperY: Float, lowerY: Float, radiusX: Float): FloatArray {
        val quadrant = label.firstOrNull()?.digitToIntOrNull() ?: 1
        val digit = label.lastOrNull()?.digitToIntOrNull()?.toFloat() ?: 1f
        val side = if (quadrant == 1 || quadrant == 4) -1f else 1f
        val isUpper = quadrant == 1 || quadrant == 2
        val t = (digit - 1f) / 7f
        val distance = 17f + t * (radiusX - 22f)
        val posteriorCurve = t * t * 96f
        val y = if (isUpper) upperY + posteriorCurve else lowerY - posteriorCurve
        return floatArrayOf(centerX + side * distance, y)
    }

    private fun labelPoint(label: String, centerX: Float, upperY: Float, lowerY: Float, radiusX: Float): FloatArray {
        val point = toothPoint(label, centerX, upperY, lowerY, radiusX)
        val quadrant = label.firstOrNull()?.digitToIntOrNull() ?: 1
        val digit = label.lastOrNull()?.digitToIntOrNull()?.toFloat() ?: 1f
        val side = if (quadrant == 1 || quadrant == 4) -1f else 1f
        val isUpper = quadrant == 1 || quadrant == 2
        val t = (digit - 1f) / 7f
        val xOffset = side * (10f + t * 16f)
        val yOffset = (if (isUpper) -1f else 1f) * (22f - t * 7f)
        return floatArrayOf(point[0] + xOffset, point[1] + yOffset)
    }

    private fun gumPath(centerX: Float, baseY: Float, radiusX: Float, upper: Boolean): Path {
        val direction = if (upper) 1f else -1f
        return Path().apply {
            moveTo(centerX - radiusX, baseY + direction * 96f)
            cubicTo(
                centerX - radiusX * 0.78f,
                baseY + direction * 38f,
                centerX - radiusX * 0.32f,
                baseY + direction * 10f,
                centerX - 18f,
                baseY,
            )
            cubicTo(
                centerX - 8f,
                baseY - direction * 4f,
                centerX + 8f,
                baseY - direction * 4f,
                centerX + 18f,
                baseY,
            )
            cubicTo(
                centerX + radiusX * 0.32f,
                baseY + direction * 10f,
                centerX + radiusX * 0.78f,
                baseY + direction * 38f,
                centerX + radiusX,
                baseY + direction * 96f,
            )
        }
    }

    private fun drawTooth(canvas: Canvas, x: Float, y: Float, kind: ToothKind, upper: Boolean) {
        val toothRect = toothRect(kind, x, y)
        val toothPath = toothPath(kind, toothRect, upper)

        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.WHITE
        canvas.drawPath(toothPath, paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.5f
        paint.color = AndroidColor.rgb(203, 213, 225)
        canvas.drawPath(toothPath, paint)

    }

    private fun drawToothLabel(canvas: Canvas, tooth: ToothNumber, x: Float, y: Float) {
        val label = if (numberingSystem == ToothNumberingSystem.FDI) tooth.fdi else tooth.universal
        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.argb(232, 255, 255, 255)
        val labelWidth = paint.measureText(label).coerceAtLeast(18f) + 12f
        canvas.drawRoundRect(RectF(x - labelWidth / 2f, y - 13f, x + labelWidth / 2f, y + 11f), 12f, 12f, paint)

        paint.textAlign = Paint.Align.CENTER
        paint.textSize = 20f
        paint.isFakeBoldText = true
        paint.color = AndroidColor.rgb(15, 23, 42)
        canvas.drawText(label, x, y + 7f, paint)
        paint.isFakeBoldText = false
    }

    private fun toothKind(label: String): ToothKind =
        when (label.lastOrNull()?.digitToIntOrNull() ?: 1) {
            1, 2 -> ToothKind.INCISOR
            3 -> ToothKind.CANINE
            4, 5 -> ToothKind.PREMOLAR
            else -> ToothKind.MOLAR
        }

    private fun toothRect(kind: ToothKind, x: Float, y: Float): RectF {
        val width = when (kind) {
            ToothKind.INCISOR -> 24f
            ToothKind.CANINE -> 26f
            ToothKind.PREMOLAR -> 29f
            ToothKind.MOLAR -> 32f
        }
        val height = when (kind) {
            ToothKind.INCISOR -> 32f
            ToothKind.CANINE -> 35f
            ToothKind.PREMOLAR -> 30f
            ToothKind.MOLAR -> 30f
        }
        return RectF(x - width / 2f, y - height / 2f, x + width / 2f, y + height / 2f)
    }

    private fun toothPath(kind: ToothKind, rect: RectF, upper: Boolean): Path {
        if (kind != ToothKind.CANINE) {
            val radius = if (kind == ToothKind.MOLAR) 14f else 11f
            return Path().apply { addRoundRect(rect, radius, radius, Path.Direction.CW) }
        }

        val path = Path()
        if (upper) {
            path.moveTo(rect.centerX(), rect.bottom)
            path.cubicTo(rect.centerX() - 10f, rect.bottom - 4f, rect.left + 4f, rect.centerY() + 10f, rect.left + 4f, rect.centerY())
            path.cubicTo(rect.left + 4f, rect.top + 8f, rect.centerX() - 10f, rect.top, rect.centerX(), rect.top)
            path.cubicTo(rect.centerX() + 10f, rect.top, rect.right - 4f, rect.top + 8f, rect.right - 4f, rect.centerY())
            path.cubicTo(rect.right - 4f, rect.centerY() + 10f, rect.centerX() + 10f, rect.bottom - 4f, rect.centerX(), rect.bottom)
        } else {
            path.moveTo(rect.centerX(), rect.top)
            path.cubicTo(rect.centerX() - 10f, rect.top + 4f, rect.left + 4f, rect.centerY() - 10f, rect.left + 4f, rect.centerY())
            path.cubicTo(rect.left + 4f, rect.bottom - 8f, rect.centerX() - 10f, rect.bottom, rect.centerX(), rect.bottom)
            path.cubicTo(rect.centerX() + 10f, rect.bottom, rect.right - 4f, rect.bottom - 8f, rect.right - 4f, rect.centerY())
            path.cubicTo(rect.right - 4f, rect.centerY() - 10f, rect.centerX() + 10f, rect.top + 4f, rect.centerX(), rect.top)
        }
        path.close()
        return path
    }

    private enum class ToothKind {
        INCISOR,
        CANINE,
        PREMOLAR,
        MOLAR,
    }
}
