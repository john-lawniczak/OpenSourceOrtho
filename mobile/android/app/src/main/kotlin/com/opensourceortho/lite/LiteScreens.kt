package com.opensourceortho.lite

import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color as AndroidColor
import android.graphics.Paint
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
import kotlin.math.cos
import kotlin.math.sin

// Lite-flow screens. Scaffolding: they wire the flow and render engine output.
// Mesh registration and destination-specific printer/lab integrations are TODO.

/** Step 1: pick CBCT, STL, or photo records from the device. */
@Composable
fun UploadScreen(model: LiteFlowViewModel) {
    val context = LocalContext.current
    var pendingModality by remember { mutableStateOf("stl") }
    val picker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenMultipleDocuments(),
    ) { uris ->
        uris.forEach { uri ->
            context.contentResolver.takePersistableReadPermission(uri)
            model.addScan(context.selectedScan(uri, pendingModality))
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
    ) {
        Text("Upload patient files", style = MaterialTheme.typography.titleLarge)
        Text(
            "CBCT is preferred when available. STL scans work well. General photos can support review notes.",
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
        )
        Button(onClick = {
            pendingModality = "cbct"
            picker.launch(arrayOf("application/zip", "application/dicom", "application/octet-stream", "*/*"))
        }) { Text("Add CBCT / DICOM") }
        Button(onClick = {
            pendingModality = "stl"
            picker.launch(arrayOf("model/stl", "application/sla", "application/octet-stream", "*/*"))
        }) { Text("Add STL scan") }
        Button(onClick = {
            pendingModality = "photo"
            picker.launch(arrayOf("image/*"))
        }) { Text("Add photos") }
        Button(onClick = {
            model.addDevSample(context.devSampleByteCount())
        }) { Text("Use dev sample STL") }
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
            update = { it.stage = stage },
            modifier = Modifier.fillMaxWidth().height(280.dp),
        )
        Slider(value = stage, onValueChange = { stage = it }, valueRange = 0f..12f, steps = 11)
        Text("Stage ${stage.toInt()} of 12", style = MaterialTheme.typography.bodyMedium)
        Text("${state.scans.size} file(s) selected", style = MaterialTheme.typography.titleMedium)
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
        state.result?.correctness?.verdict?.let {
            Text("Engine verdict", style = MaterialTheme.typography.labelMedium)
            Text(SafetyText.verdictLabel(it), style = MaterialTheme.typography.titleMedium)
        }
        state.result?.steps?.forEach { step ->
            Text(step.name, style = MaterialTheme.typography.bodyMedium)
            Text("${step.status}: ${step.detail}", style = MaterialTheme.typography.bodySmall)
        }
        state.result?.caveat?.let {
            Text(it, style = MaterialTheme.typography.bodySmall)
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
                    Text("Projected duration: ${timeline.projectedDurationWeeks} weeks")
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
        Button(onClick = model::reset) { Text("Start over") }
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
                GlossaryRow("CBCT", "Cone-beam CT. Best source when roots, bone, or impacted teeth matter.")
                GlossaryRow("STL", "Surface mesh from an intraoral scan or model scan.")
                GlossaryRow("Stage", "One planned tooth-position step in the timeline.")
                GlossaryRow("IPR", "Interproximal reduction, measured space created between teeth.")
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

    private var rotation = 0f
    private var lastX = 0f
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)

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

        drawArch(canvas, isUpper = true)
        drawArch(canvas, isUpper = false)
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
}

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
        val radiusX = minOf(width * 0.42f, 170f)
        val upperY = centerY - 54f
        val lowerY = centerY + 54f

        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.rgb(248, 250, 252)
        canvas.drawRoundRect(0f, 0f, width.toFloat(), height.toFloat(), 28f, 28f, paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.5f
        paint.color = AndroidColor.rgb(203, 213, 225)
        canvas.drawLine(centerX, 36f, centerX, height - 36f, paint)

        paint.strokeWidth = 28f
        paint.color = AndroidColor.argb(90, 244, 114, 182)
        canvas.drawArc(
            RectF(centerX - radiusX, upperY + 72f - radiusX, centerX + radiusX, upperY + 72f + radiusX),
            205f,
            130f,
            false,
            paint,
        )
        canvas.drawArc(
            RectF(centerX - radiusX, lowerY - 72f - radiusX, centerX + radiusX, lowerY - 72f + radiusX),
            25f,
            130f,
            false,
            paint,
        )

        paint.style = Paint.Style.FILL
        paint.textAlign = Paint.Align.CENTER
        paint.textSize = 28f
        paint.color = AndroidColor.rgb(71, 85, 105)
        paint.isFakeBoldText = true
        canvas.drawText("Upper", centerX, 30f, paint)
        canvas.drawText("Lower", centerX, height - 18f, paint)

        paint.textSize = 22f
        paint.isFakeBoldText = false
        canvas.drawText("Patient right", 74f, centerY, paint)
        canvas.drawText("Patient left", width - 74f, centerY, paint)

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
            val distance = 18f + t * (radiusX - 28f)
            val curve = sin(t * Math.PI).toFloat() * 56f
            val x = width / 2f + side * distance
            val y = if (upper) archY + curve else archY - curve
            drawTooth(canvas, label, x, y)
        }
    }

    private fun drawTooth(canvas: Canvas, label: String, x: Float, y: Float) {
        paint.style = Paint.Style.FILL
        paint.color = AndroidColor.WHITE
        canvas.drawRoundRect(x - 28f, y - 22f, x + 28f, y + 22f, 24f, 24f, paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.5f
        paint.color = AndroidColor.rgb(203, 213, 225)
        canvas.drawRoundRect(x - 28f, y - 22f, x + 28f, y + 22f, 24f, 24f, paint)

        paint.style = Paint.Style.FILL
        paint.textAlign = Paint.Align.CENTER
        paint.textSize = 24f
        paint.isFakeBoldText = true
        paint.color = AndroidColor.rgb(15, 23, 42)
        canvas.drawText(label, x, y + 8f, paint)
        paint.isFakeBoldText = false
    }
}
