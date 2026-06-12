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
    val localUri: String? = null,
) {
    val isStl: Boolean
        get() = modality.lowercase() == "stl" || fileName.lowercase().endsWith(".stl")
}

/** Browser/full-engine review JSON retained on-device as an opaque artifact. */
@Serializable
data class StoredPlanReview(
    val id: String,
    val fileName: String,
    val byteCount: Int,
    val importedAtEpochMillis: Long,
    val jsonText: String,
    val caseReview: StoredCaseReview? = null,
) {
    companion object {
        private val reviewJson = kotlinx.serialization.json.Json { ignoreUnknownKeys = true }

        fun create(fileName: String, byteCount: Int, jsonText: String): StoredPlanReview {
            val importedAt = System.currentTimeMillis()
            return create(fileName, byteCount, jsonText, importedAt, null)
        }

        fun importCaseReview(fileName: String, byteCount: Int, jsonText: String): StoredPlanReview {
            val review = reviewJson.decodeFromString(StoredCaseReview.serializer(), jsonText)
            require(review.isImportableStoredReview) {
                "Not an orthoplan-case-review-v1 stored review"
            }
            return create(fileName, byteCount, jsonText, System.currentTimeMillis(), review)
        }

        private fun create(
            fileName: String,
            byteCount: Int,
            jsonText: String,
            importedAt: Long,
            caseReview: StoredCaseReview?,
        ): StoredPlanReview {
            val cleaned = fileName.lowercase()
                .map { if (it.isLetterOrDigit()) it else '-' }
                .joinToString("")
                .trim('-')
            return StoredPlanReview(
                id = "${cleaned.ifEmpty { "browser-review" }}-$importedAt",
                fileName = fileName,
                byteCount = byteCount,
                importedAtEpochMillis = importedAt,
                jsonText = jsonText,
                caseReview = caseReview,
            )
        }
    }
}

/** Conservative STL-only synthesis used when the engine is unreachable. */
object OnDevicePlanSynthesizer {
    fun canSynthesize(scans: List<SelectedScan>): Boolean =
        scans.isNotEmpty() && scans.all { it.isStl }

    fun response(scans: List<SelectedScan>): GeneratePlanResponse {
        val stageCount = maxOf(6, scans.size * 6)
        val projectedDays = stageCount * 14
        val plan = buildJsonObject {
            LitePlanBuilder.minimalPlan(scans).forEach { (key, value) -> put(key, value) }
            put("stages", buildJsonArray {})
            put("mobile_synthesis", buildJsonObject {
                put("mode", "stl-only-best-effort")
                put("requires_browser_for_edits", true)
            })
        }
        return GeneratePlanResponse(
            ok = true,
            source = "mobile-stl-best-effort",
            warnings = listOf(
                "Generated on-device from STL metadata only.",
                "Open the browser/full engine for segmentation, mesh-backed editing, CBCT/DICOM, or print-critical review.",
            ),
            steps = listOf(
                PipelineStep(
                    name = "mobile-stl-intake",
                    status = "warning",
                    detail = "STL files were accepted for a limited on-device review.",
                ),
                PipelineStep(
                    name = "browser-handoff",
                    status = "warning",
                    detail = "Use the browser workspace for CBCT/DICOM, segmentation, and plan changes.",
                ),
            ),
            correctness = Correctness("CONSISTENT"),
            stageCount = stageCount,
            timeline = Timeline(
                stageCount = stageCount,
                wearIntervalDays = 14,
                projectedDurationDays = projectedDays,
                projectedDurationWeeks = projectedDays / 7.0,
                caveat = "Mobile STL-only synthesis is a conservative review artifact. It excludes segmentation, CBCT/DICOM registration, root/bone checks, collision validation from real tooth meshes, and clinical approval.",
            ),
            caveat = "This review was synthesized on-device from STL metadata only. Use the browser/full engine for accurate mesh geometry, CBCT/DICOM, plan edits, print-critical exports, and clinician review.",
            plan = plan,
        )
    }
}

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
