package com.opensourceortho.lite

import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** The four-step lite flow shared with iOS (../../README.md). */
enum class LiteStep(val title: String) {
    UPLOAD("Upload scan"),
    GENERATE("Generate plan"),
    REVIEW("Review"),
    PROGRESSION("Progression"),
}

/** A locally-selected scan file. Lite uploads metadata + registers bytes with the
 *  engine mesh workspace; plan JSON never carries mesh bytes. */
data class SelectedScan(
    val fileName: String,
    val arch: String? = null, // "upper" | "lower" | null (unspecified)
    val byteCount: Int = 0,
)

/** Builds the minimal plan-shaped payload the lite flow sends to
 *  `POST /api/generate-plan`. The engine fills in defaults and is the source of
 *  truth for the full TreatmentPlan shape; lite only seeds scan metadata. */
object LitePlanBuilder {
    fun minimalPlan(scans: List<SelectedScan>): JsonObject = buildJsonObject {
        put("scans", buildJsonArray {
            scans.forEach { scan ->
                add(buildJsonObject {
                    put("file_name", scan.fileName)
                    scan.arch?.let { put("arch", it) }
                })
            }
        })
    }

    fun request(scans: List<SelectedScan>): GeneratePlanRequest =
        GeneratePlanRequest(plan = minimalPlan(scans) as JsonElement)
}
