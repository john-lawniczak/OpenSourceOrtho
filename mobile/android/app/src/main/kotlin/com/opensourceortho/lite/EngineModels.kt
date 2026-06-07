package com.opensourceortho.lite

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

/**
 * Serializable mirrors of the mobile-facing subset of the engine contract
 * (../../API_CONTRACT.md). Only the fields the lite UI renders are modeled; the
 * JSON parser is configured with ignoreUnknownKeys so the engine can evolve.
 */

/** Request body for `POST /api/generate-plan`. Lite defaults keep everything on
 *  the engine host: provider = "local", shareAcknowledged = false. */
@Serializable
data class GeneratePlanRequest(
    val plan: JsonElement,
    @SerialName("acknowledge_educational") val acknowledgeEducational: Boolean = true,
    val provider: String = "local",
    @SerialName("share_acknowledged") val shareAcknowledged: Boolean = false,
    val notes: String? = null,
)

@Serializable
data class PipelineStep(
    val name: String,
    val status: String = "ok",
    val detail: String = "",
)

@Serializable
data class Correctness(val verdict: String)

@Serializable
data class Timeline(
    @SerialName("stage_count") val stageCount: Int,
    @SerialName("wear_interval_days") val wearIntervalDays: Int,
    @SerialName("projected_duration_days") val projectedDurationDays: Int,
    @SerialName("projected_duration_weeks") val projectedDurationWeeks: Double,
    val caveat: String,
)

/** Subset of the `POST /api/generate-plan` success body the lite UI renders. */
@Serializable
data class GeneratePlanResponse(
    val ok: Boolean = false,
    val errors: List<String>? = null,
    val source: String? = null,
    val warnings: List<String>? = null,
    val steps: List<PipelineStep>? = null,
    val correctness: Correctness? = null,
    @SerialName("stage_count") val stageCount: Int? = null,
    val timeline: Timeline? = null,
    val caveat: String? = null,
    // The full generated plan stays opaque here; the progression screen reads
    // `plan.stages` lazily when the renderer is built.
    val plan: JsonElement? = null,
)
