package com.opensourceortho.lite

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

// Lite-flow screens. Scaffolding: they wire the flow and render engine output.
// The STL file picker and the real 3D renderer are TODO - see ../README.md.

/** Step 1: pick an STL scan from the device. */
@Composable
fun UploadScreen(model: LiteFlowViewModel) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
    ) {
        Text("Upload an STL scan", style = MaterialTheme.typography.titleLarge)
        Text(
            "Choose an upper and/or lower arch scan from your device.",
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
        )
        // TODO: launch the system document picker (ACTION_OPEN_DOCUMENT, */*) for
        // .stl and register bytes with the engine mesh workspace. Stubbed for now.
        Button(onClick = {
            model.addScan(SelectedScan(fileName = "upper.stl", arch = "upper"))
        }) { Text("Choose STL file") }
    }
}

/** Step 2: one-tap generate. */
@Composable
fun GenerateScreen(state: LiteUiState, model: LiteFlowViewModel) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
    ) {
        Text("${state.scans.size} scan(s) selected", style = MaterialTheme.typography.titleMedium)
        state.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, textAlign = TextAlign.Center)
        }
        Button(onClick = model::generate, enabled = !state.isGenerating) {
            if (state.isGenerating) CircularProgressIndicator(Modifier.height(20.dp))
            else Text("Generate plan")
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
        Button(onClick = model::showProgression) { Text("See progression over time") }
    }
}

/** Step 4: staged progression + 3D over time. */
@Composable
fun ProgressionScreen(state: LiteUiState, model: LiteFlowViewModel) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        state.result?.timeline?.let { timeline ->
            Text("${timeline.stageCount} stages", style = MaterialTheme.typography.titleLarge)
            Text(
                "~ ${timeline.projectedDurationWeeks} weeks " +
                    "(${timeline.wearIntervalDays}-day interval)",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(timeline.caveat, style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.Center)
        }
        // TODO: OpenGL/Filament 3D preview that animates `plan.stages` over time,
        // mirroring ui/viewer3d.js. Mesh bytes from GET /api/mesh/<id>; fall back
        // to schematic proxy teeth when absent.
        Surface(
            color = Color.LightGray.copy(alpha = 0.2f),
            modifier = Modifier.fillMaxWidth().height(280.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text("3D progression preview\n(TODO: renderer)", textAlign = TextAlign.Center)
            }
        }
        Button(onClick = model::reset) { Text("Start over") }
    }
}
