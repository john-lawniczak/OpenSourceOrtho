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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
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
    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenMultipleDocuments(),
    ) { uris ->
        uris.forEach { uri ->
            context.contentResolver.takePersistableReadPermission(uri)
            if (pendingModality == "browser-review") {
                model.importBrowserReview(context.storedPlanReview(uri))
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
        Button(onClick = {
            pendingModality = "stl"
            picker.launch(arrayOf("model/stl", "application/sla", "application/octet-stream", "*/*"))
        }) { Text("Add STL scan") }
        Button(onClick = {
            pendingModality = "cbct"
            picker.launch(arrayOf("application/zip", "application/dicom", "application/octet-stream", "*/*"))
        }) { Text("Add CBCT / DICOM") }
        Button(onClick = {
            pendingModality = "photo"
            picker.launch(arrayOf("image/*"))
        }) { Text("Add photos from device") }
        Button(onClick = {
            pendingModality = "photo"
            picker.launch(arrayOf("image/*", "application/octet-stream", "*/*"))
        }) { Text("Browse photos in Files or Drive") }
        Button(onClick = {
            pendingModality = "browser-review"
            picker.launch(arrayOf("application/json", "text/json", "text/plain", "*/*"))
        }) { Text("Import browser review") }
        Button(onClick = {
            model.addDevSample(context.devSampleByteCount())
        }) { Text("Use dev sample STL") }
        if (state.storedReviews.isNotEmpty()) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text("Stored browser reviews", style = MaterialTheme.typography.labelMedium)
                    state.storedReviews.forEach { review ->
                        Text(
                            "${review.fileName} - ${review.byteCount} bytes",
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
        }
    }
}

/** Step 2: staged teeth preview and timeline controls. */
@Composable
fun TeethAndTimeScreen(state: LiteUiState, model: LiteFlowViewModel) {
    var stage by remember { mutableFloatStateOf(0f) }
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
                            Text(
                                "${review.byteCount} bytes stored on this device for review/sharing. Open the browser workspace to edit the source plan.",
                                style = MaterialTheme.typography.bodySmall,
                            )
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
    val packageJson = remember { model.exportPackageJson() }
    val exportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/json"),
    ) { uri ->
        uri?.let { context.writeTextToUri(it, packageJson) }
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
        Button(onClick = {
            exportLauncher.launch("opensource-ortho-print-package.json")
        }) { Text("Export print package") }
        Button(onClick = {
            context.sharePackage(packageJson)
        }) { Text("Send to 3D printer") }
        Button(onClick = {
            context.printPackage(packageJson)
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
            }
        }
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Glossary", style = MaterialTheme.typography.labelMedium)
                fullGlossaryTerms.forEach { (term, definition) ->
                    GlossaryRow(term, definition)
                }
            }
        }
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Teeth map", style = MaterialTheme.typography.labelMedium)
                AndroidView(
                    factory = { TeethMapView(it) },
                    modifier = Modifier.fillMaxWidth().height(360.dp),
                )
                Text("Upper right: 18 17 16 15 14 13 12 11")
                Text("Upper left: 21 22 23 24 25 26 27 28")
                Text("Lower left: 31 32 33 34 35 36 37 38")
                Text("Lower right: 48 47 46 45 44 43 42 41")
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
    return StoredPlanReview.create(
        fileName = name,
        byteCount = text.toByteArray(Charsets.UTF_8).size,
        jsonText = text,
    )
}

private fun Context.devSampleByteCount(): Int =
    resources.openRawResourceFd(R.raw.dev_sample_incisor)?.use { descriptor ->
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

private fun Context.writeTextToUri(uri: Uri, text: String) {
    contentResolver.openOutputStream(uri)?.use { stream ->
        stream.write(text.toByteArray(Charsets.UTF_8))
    }
}

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
            meshPoints = loadFirstStlMesh(value)
            invalidate()
        }

    private var rotation = 0f
    private var lastX = 0f
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private var meshPoints: List<FloatArray> = emptyList()

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

        if (meshPoints.isNotEmpty()) {
            drawMesh(canvas, meshPoints)
            paint.textSize = 24f
            paint.color = AndroidColor.rgb(71, 85, 105)
            canvas.drawText("Rendering selected STL geometry", width / 2f, height - 22f, paint)
        } else {
            drawArch(canvas, isUpper = true)
            drawArch(canvas, isUpper = false)
            paint.textSize = 24f
            paint.color = AndroidColor.rgb(71, 85, 105)
            val caption = if (scans.any { it.modality == "cbct" }) {
                "CBCT attached; open browser/full engine for volume rendering"
            } else {
                "Add an STL scan to render patient geometry"
            }
            canvas.drawText(caption, width / 2f, height - 22f, paint)
        }
    }

    private fun loadFirstStlMesh(scans: List<SelectedScan>): List<FloatArray> {
        val scan = scans.firstOrNull { it.isStl && it.localUri != null } ?: return emptyList()
        val bytes = context.contentResolver.openInputStream(Uri.parse(scan.localUri))?.use { it.readBytes() }
            ?: return emptyList()
        return parseStlPoints(bytes).take(18000)
    }

    private fun drawMesh(canvas: Canvas, points: List<FloatArray>) {
        val bounds = meshBounds(points)
        val span = max(bounds[3] - bounds[0], max(bounds[4] - bounds[1], bounds[5] - bounds[2])).coerceAtLeast(1f)
        val scale = min(width, height) * 0.62f / span
        val cx = (bounds[0] + bounds[3]) / 2f
        val cy = (bounds[1] + bounds[4]) / 2f
        val cz = (bounds[2] + bounds[5]) / 2f
        val centerX = width / 2f
        val centerY = height / 2f

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.2f
        paint.color = AndroidColor.rgb(196, 176, 129)
        var index = 0
        while (index + 2 < points.size) {
            val a = project(points[index], cx, cy, cz, scale, centerX, centerY)
            val b = project(points[index + 1], cx, cy, cz, scale, centerX, centerY)
            val c = project(points[index + 2], cx, cy, cz, scale, centerX, centerY)
            canvas.drawLine(a[0], a[1], b[0], b[1], paint)
            canvas.drawLine(b[0], b[1], c[0], c[1], paint)
            canvas.drawLine(c[0], c[1], a[0], a[1], paint)
            index += 3
        }
    }

    private fun project(point: FloatArray, cx: Float, cy: Float, cz: Float, scale: Float, centerX: Float, centerY: Float): FloatArray {
        val x = point[0] - cx
        val y = point[1] - cy
        val z = point[2] - cz
        val rotatedX = x * cos(rotation) - z * sin(rotation)
        val rotatedZ = x * sin(rotation) + z * cos(rotation)
        return floatArrayOf(centerX + rotatedX * scale, centerY - (y * 0.72f + rotatedZ * 0.18f) * scale)
    }

    private fun meshBounds(points: List<FloatArray>): FloatArray {
        var minX = Float.POSITIVE_INFINITY
        var minY = Float.POSITIVE_INFINITY
        var minZ = Float.POSITIVE_INFINITY
        var maxX = Float.NEGATIVE_INFINITY
        var maxY = Float.NEGATIVE_INFINITY
        var maxZ = Float.NEGATIVE_INFINITY
        points.forEach {
            minX = min(minX, it[0]); minY = min(minY, it[1]); minZ = min(minZ, it[2])
            maxX = max(maxX, it[0]); maxY = max(maxY, it[1]); maxZ = max(maxZ, it[2])
        }
        return floatArrayOf(minX, minY, minZ, maxX, maxY, maxZ)
    }

    private fun drawArch(canvas: Canvas, isUpper: Boolean) {
        val centerX = width / 2f
        val centerY = height / 2f + if (isUpper) -54f else 54f
        val progress = stage / 12f
        paint.color = if (isUpper) AndroidColor.rgb(20, 184, 166) else AndroidColor.rgb(45, 212, 191)

        for (index in 0 until 8) {
            val normalized = index / 7f
            val centered = index - 3.5f
            val curve = sin(normalized * Math.PI).toFloat() * 54f
            val rotated = centered * cos(rotation) * 46f
            val stageOffset = if (centered >= 0f) progress * 14f else -progress * 14f
            val x = centerX + rotated + stageOffset
            val y = centerY + curve * if (isUpper) 1f else -1f
            canvas.drawOval(RectF(x - 18f, y - 26f, x + 18f, y + 26f), paint)
        }
    }

    private fun parseStlPoints(bytes: ByteArray): List<FloatArray> {
        val text = bytes.decodeToString(endIndex = min(bytes.size, 1024 * 1024))
        if (text.contains("vertex")) {
            return text.lineSequence()
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
        }
        if (bytes.size < 84) return emptyList()
        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        val triangleCount = buffer.getInt(80).coerceAtLeast(0)
        val points = ArrayList<FloatArray>(min(triangleCount * 3, 18000))
        var offset = 84
        repeat(min(triangleCount, 6000)) {
            if (offset + 50 > bytes.size) return@repeat
            offset += 12
            repeat(3) {
                val x = buffer.getFloat(offset)
                val y = buffer.getFloat(offset + 4)
                val z = buffer.getFloat(offset + 8)
                points.add(floatArrayOf(x, y, z))
                offset += 12
            }
            offset += 2
        }
        return points
    }
}

private val fullGlossaryTerms = listOf(
    "Arch" to "One jaw's row of teeth: maxillary (upper) or mandibular (lower).",
    "Attachment" to "A small composite bump bonded to a tooth so an aligner can grip it. Planning intent only, not a force model.",
    "Canine" to "The pointed corner tooth, position 3 in FDI notation.",
    "CBCT" to "Cone-beam CT. The higher-fidelity record for roots and bone when ordered and interpreted by a professional.",
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
    "Malocclusion" to "A bad bite or misalignment. The app does not diagnose malocclusion.",
    "Mesh / STL" to "A 3D surface model. STL files carry no units, so units start unverified until confirmed.",
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

private class TeethMapView(context: Context) : View(context) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val upperRight = listOf("18", "17", "16", "15", "14", "13", "12", "11")
    private val upperLeft = listOf("21", "22", "23", "24", "25", "26", "27", "28")
    private val lowerLeft = listOf("31", "32", "33", "34", "35", "36", "37", "38")
    private val lowerRight = listOf("48", "47", "46", "45", "44", "43", "42", "41")

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val centerX = width / 2f
        val centerY = height / 2f
        val radiusX = minOf(width * 0.43f, 172f)
        val upperY = centerY - 68f
        val lowerY = centerY + 68f

        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.rgb(248, 250, 252)
        canvas.drawRoundRect(0f, 0f, width.toFloat(), height.toFloat(), 36f, 36f, paint)

        paint.color = AndroidColor.argb(40, 244, 114, 182)
        canvas.drawOval(RectF(16f, 24f, width - 16f, height - 24f), paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 3f
        paint.color = AndroidColor.argb(96, 244, 114, 182)
        canvas.drawOval(RectF(16f, 24f, width - 16f, height - 24f), paint)

        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.argb(45, 244, 114, 182)
        canvas.drawOval(RectF(centerX - 70f, centerY - 82f, centerX + 70f, centerY + 22f), paint)
        paint.color = AndroidColor.argb(32, 239, 68, 68)
        canvas.drawOval(RectF(centerX - 78f, centerY + 20f, centerX + 78f, centerY + 138f), paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 34f
        paint.color = AndroidColor.argb(122, 244, 114, 182)
        canvas.drawArc(
            RectF(centerX - radiusX, upperY + 86f - radiusX, centerX + radiusX, upperY + 86f + radiusX),
            202f,
            136f,
            false,
            paint,
        )
        canvas.drawArc(
            RectF(centerX - radiusX, lowerY - 86f - radiusX, centerX + radiusX, lowerY - 86f + radiusX),
            22f,
            136f,
            false,
            paint,
        )

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

        drawQuadrant(canvas, upperRight, -1f, upperY, radiusX, upper = true)
        drawQuadrant(canvas, upperLeft, 1f, upperY, radiusX, upper = true)
        drawQuadrant(canvas, lowerLeft, 1f, lowerY, radiusX, upper = false)
        drawQuadrant(canvas, lowerRight, -1f, lowerY, radiusX, upper = false)
    }

    private fun drawQuadrant(
        canvas: Canvas,
        labels: List<String>,
        side: Float,
        archY: Float,
        radiusX: Float,
        upper: Boolean,
    ) {
        labels.forEachIndexed { index, label ->
            val t = index / 7f
            val distance = 16f + t * (radiusX - 34f)
            val curve = sin(t * Math.PI).toFloat() * 66f
            val x = width / 2f + side * distance
            val y = if (upper) archY + curve else archY - curve
            drawTooth(canvas, label, x, y, toothKind(index), upper)
        }
    }

    private fun drawTooth(canvas: Canvas, label: String, x: Float, y: Float, kind: ToothKind, upper: Boolean) {
        val toothRect = toothRect(kind, x, y)
        val toothPath = toothPath(kind, toothRect, upper)

        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.WHITE
        canvas.drawPath(toothPath, paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.5f
        paint.color = AndroidColor.rgb(203, 213, 225)
        canvas.drawPath(toothPath, paint)

        paint.style = Paint.Style.FILL
        paint.textAlign = Paint.Align.CENTER
        paint.textSize = 24f
        paint.isFakeBoldText = true
        paint.color = AndroidColor.rgb(15, 23, 42)
        val baseline = y + 8f + if (kind == ToothKind.CANINE && !upper) 3f else if (kind == ToothKind.CANINE) -3f else 0f
        canvas.drawText(label, x, baseline, paint)
        paint.isFakeBoldText = false
    }

    private fun toothKind(index: Int): ToothKind =
        when (index) {
            0, 1 -> ToothKind.MOLAR
            2, 3 -> ToothKind.PREMOLAR
            4 -> ToothKind.CANINE
            else -> ToothKind.INCISOR
        }

    private fun toothRect(kind: ToothKind, x: Float, y: Float): RectF {
        val width = when (kind) {
            ToothKind.INCISOR -> 34f
            ToothKind.CANINE -> 36f
            ToothKind.PREMOLAR -> 42f
            ToothKind.MOLAR -> 48f
        }
        val height = when (kind) {
            ToothKind.INCISOR -> 42f
            ToothKind.CANINE -> 46f
            ToothKind.PREMOLAR -> 40f
            ToothKind.MOLAR -> 42f
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
