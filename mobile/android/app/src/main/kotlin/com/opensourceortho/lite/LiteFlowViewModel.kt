package com.opensourceortho.lite

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** Immutable UI state for the lite flow. */
data class LiteUiState(
    val step: LiteStep = LiteStep.UPLOAD,
    val scans: List<SelectedScan> = emptyList(),
    val isGenerating: Boolean = false,
    val result: GeneratePlanResponse? = null,
    val errorMessage: String? = null,
)

/**
 * Drives the lite flow for the Compose screens. All real work delegates to
 * [EngineClient]; this only holds view state.
 */
class LiteFlowViewModel(
    private val client: EngineClient,
) : ViewModel() {
    // Real no-arg constructor so Compose's default `viewModel()` factory can
    // instantiate it (a Kotlin default-value param does not create one).
    constructor() : this(EngineClient())

    private val _state = MutableStateFlow(LiteUiState())
    val state: StateFlow<LiteUiState> = _state.asStateFlow()

    fun addScan(scan: SelectedScan) {
        _state.update { it.copy(scans = it.scans + scan, step = LiteStep.GENERATE) }
    }

    /** One-tap "Generate Plan": posts to the engine and advances to Review. */
    fun generate() {
        val scans = _state.value.scans
        if (scans.isEmpty()) return
        _state.update { it.copy(isGenerating = true, errorMessage = null) }
        viewModelScope.launch {
            try {
                val response = client.generatePlan(LitePlanBuilder.request(scans))
                _state.update {
                    it.copy(isGenerating = false, result = response, step = LiteStep.REVIEW)
                }
            } catch (e: EngineException) {
                _state.update { it.copy(isGenerating = false, errorMessage = e.message) }
            }
        }
    }

    fun showProgression() = _state.update { it.copy(step = LiteStep.PROGRESSION) }

    fun reset() = _state.update { LiteUiState() }
}
