package com.opensourceortho.lite

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    LiteApp()
                }
            }
        }
    }
}

/** Top-level lite UI: a standing safety banner plus the current flow step.
 *  Screens render engine output; they never compute a plan on-device. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LiteApp(model: LiteFlowViewModel = viewModel()) {
    val state by model.state.collectAsState()
    Scaffold(
        topBar = { TopAppBar(title = { Text("OpenSource Ortho") }) },
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            SafetyBanner()
            HorizontalDivider()
            when (state.step) {
                LiteStep.UPLOAD -> UploadScreen(model)
                LiteStep.GENERATE -> GenerateScreen(state, model)
                LiteStep.REVIEW -> ReviewScreen(state, model)
                LiteStep.PROGRESSION -> ProgressionScreen(state, model)
            }
        }
    }
}

/** Non-dismissible disclaimer (wording from strings.xml, kept in sync with the
 *  engine caveat). Required by the project safety boundary. */
@Composable
fun SafetyBanner() {
    Text(
        text = stringResource(R.string.safety_disclaimer),
        style = MaterialTheme.typography.bodySmall,
        modifier = Modifier.padding(12.dp),
    )
}
