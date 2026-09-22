package com.opensourceortho.lite

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp

@Composable
fun SampleHistoryScreen() {
    val context = LocalContext.current
    val result = remember(context) {
        runCatching {
            context.assets.open("history.json").bufferedReader().use {
                SampleHistory.decode(it.readText())
            }
        }
    }
    val history = result.getOrNull()
    if (history == null) {
        Text("Sample history could not be loaded.", modifier = Modifier.padding(16.dp))
        return
    }
    var visitIndex by rememberSaveable { mutableIntStateOf(0) }
    val visit = history.visits[visitIndex.coerceIn(history.visits.indices)]
    Column(
        modifier = Modifier.verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(history.summary, style = MaterialTheme.typography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            history.visits.forEachIndexed { index, item ->
                FilterChip(selected = visitIndex == index, onClick = { visitIndex = index },
                    label = { Text(item.label) })
            }
        }
        Text("${visit.label} · ${visit.date}", style = MaterialTheme.typography.titleLarge)
        Text(visit.detail, style = MaterialTheme.typography.bodyMedium)
        Text(history.limitation, style = MaterialTheme.typography.bodySmall)
        visit.arches.forEach { arch -> SampleArchCard(arch, visit.label) }
        Text("Recorded timeline", style = MaterialTheme.typography.titleMedium)
        history.events.forEach { event ->
            Column {
                Text(event.label, style = MaterialTheme.typography.titleSmall)
                Text(event.date, style = MaterialTheme.typography.bodySmall)
            }
        }
        Text(history.timing, style = MaterialTheme.typography.bodySmall)
        Text(history.context, style = MaterialTheme.typography.bodySmall)
        Text("Research sample · final outcome not recorded", style = MaterialTheme.typography.titleSmall)
    }
}

@Composable
private fun SampleArchCard(arch: SampleArch, visitLabel: String) {
    val context = LocalContext.current
    val bitmap = remember(context, arch.previewImage) {
        runCatching {
            context.assets.open(arch.previewImage).use { BitmapFactory.decodeStream(it) }
                ?.asImageBitmap()
        }.getOrNull()
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("${arch.name} arch", style = MaterialTheme.typography.titleMedium)
        if (bitmap != null) {
            Image(bitmap, "$visitLabel, ${arch.name.lowercase()} scan surface, independent view",
                modifier = Modifier.fillMaxWidth().aspectRatio(bitmap.width.toFloat() / bitmap.height))
        } else {
            Text("Scan preview unavailable")
        }
        Text("${arch.faceCount} triangles · ${arch.zeroAreaFaces} zero-area faces",
            style = MaterialTheme.typography.bodySmall)
        Text(if (arch.units == "mm") "Recorded units: mm" else "Physical scale unverified",
            style = MaterialTheme.typography.bodySmall)
        Text("View rendered from the original STL. No intermediate scans are inferred.",
            style = MaterialTheme.typography.bodySmall)
    }
}
