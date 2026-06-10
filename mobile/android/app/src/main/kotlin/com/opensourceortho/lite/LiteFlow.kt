package com.opensourceortho.lite

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** The four-step lite flow shared with iOS (../../README.md). */
enum class LiteStep(val title: String) {
    UPLOAD("Upload files"),
    TEETH_AND_TIME("Teeth + time"),
    REVIEW("Review"),
    PRINT_AND_SEND("Print + send"),
}

/** A locally-selected scan file. Lite uploads metadata + registers bytes with the
 *  engine mesh workspace; plan JSON never carries mesh bytes. */
@Serializable
data class SelectedScan(
    val fileName: String,
    val arch: String? = null, // "upper" | "lower" | null (unspecified)
    val byteCount: Int = 0,
    val modality: String = "stl", // "cbct" | "stl" | "photo"
)

/** Builds the minimal plan-shaped payload the lite flow sends to
 *  `POST /api/generate-plan`. The engine fills in defaults and is the source of
 *  truth for the full TreatmentPlan shape; lite only seeds scan metadata. */
object LitePlanBuilder {
    fun minimalPlan(scans: List<SelectedScan>): JsonObject = buildJsonObject {
        put("id", "lite-plan")
        put("title", "Lite plan")
        put("numbering_system", "FDI")
        put("coordinate_frame", buildJsonObject {
            put("name", "scan-local")
        })
        put("scans", buildJsonArray {
            scans.forEachIndexed { index, scan ->
                add(buildJsonObject {
                    put("asset", buildJsonObject {
                        put("id", assetId(scan.fileName, index))
                        put("format", engineFormat(scan.modality))
                        put("provenance", "patient-derived")
                        put("units", "unverified")
                        put("vertex_count", 0)
                        put("face_count", 0)
                        put("reference", scan.fileName)
                    })
                    put("source", engineSource(scan.modality))
                    engineArch(scan.arch)?.let { put("arch", it) }
                })
            }
        })
    }

    fun request(scans: List<SelectedScan>): GeneratePlanRequest =
        GeneratePlanRequest(plan = minimalPlan(scans) as JsonElement)

    private fun engineArch(value: String?): String? = when (value?.lowercase()) {
        "upper", "maxillary" -> "maxillary"
        "lower", "mandibular" -> "mandibular"
        else -> null
    }

    private fun engineFormat(value: String): String = when (value.lowercase()) {
        "cbct" -> "dicom"
        "photo" -> "image"
        else -> "stl"
    }

    private fun engineSource(value: String): String = when (value.lowercase()) {
        "cbct" -> "cbct"
        "photo" -> "photo"
        else -> "intraoral-scan"
    }

    private fun assetId(fileName: String, index: Int): String {
        val cleaned = fileName.lowercase()
            .map { if (it.isLetterOrDigit()) it else '-' }
            .joinToString("")
            .trim('-')
        return "lite-$index-${cleaned.ifEmpty { "scan" }}"
    }
}
