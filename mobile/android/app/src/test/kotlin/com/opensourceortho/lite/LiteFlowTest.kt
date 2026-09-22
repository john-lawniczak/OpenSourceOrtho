package com.opensourceortho.lite

import kotlinx.serialization.json.Json
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class LiteFlowTest {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    @Test
    fun minimalPlanCarriesScanMetadata() {
        val plan = LitePlanBuilder.minimalPlan(listOf(SelectedScan("upper.stl", "upper")))
        val text = json.encodeToString(kotlinx.serialization.json.JsonObject.serializer(), plan)
        assertTrue(text.contains("\"id\""))
        assertTrue(text.contains("\"asset\""))
        assertTrue(text.contains("upper.stl"))
        assertTrue(text.contains("maxillary"))
        assertTrue(text.contains("vertex_count"))
        assertFalse(text.contains("file_name"))
    }

    @Test
    fun minimalPlanKeepsDuplicateFilenamesDistinct() {
        val plan = LitePlanBuilder.minimalPlan(
            listOf(
                SelectedScan("scan.stl", "upper"),
                SelectedScan("scan.stl", "lower"),
            ),
        )
        val text = json.encodeToString(kotlinx.serialization.json.JsonObject.serializer(), plan)

        assertTrue(text.contains("lite-0-scan-stl"))
        assertTrue(text.contains("lite-1-scan-stl"))
    }

    @Test
    fun minimalPlanCarriesNonStlModalities() {
        val plan = LitePlanBuilder.minimalPlan(
            listOf(
                SelectedScan(fileName = "cbct.zip", modality = "cbct"),
                SelectedScan(fileName = "smile.jpg", modality = "photo"),
            ),
        )
        val text = json.encodeToString(kotlinx.serialization.json.JsonObject.serializer(), plan)

        assertTrue(text.contains("\"format\":\"dicom\""))
        assertTrue(text.contains("\"source\":\"cbct\""))
        assertTrue(text.contains("\"format\":\"image\""))
        assertTrue(text.contains("\"source\":\"photo\""))
    }

    @Test
    fun requestDefaultsKeepDataLocal() {
        val request = LitePlanBuilder.request(emptyList())
        assertEquals("local", request.provider)
        assertFalse("lite must not opt into egress by default", request.shareAcknowledged)
        assertTrue(request.acknowledgeEducational)
    }

    @Test
    fun onDeviceSynthesisIsStlOnlyAndCaveated() {
        val stlScans = listOf(SelectedScan("upper.stl", "upper", 100))
        assertTrue(OnDevicePlanSynthesizer.canSynthesize(stlScans))

        val cbctScans = listOf(SelectedScan(fileName = "cbct.zip", byteCount = 100, modality = "cbct"))
        assertFalse(OnDevicePlanSynthesizer.canSynthesize(cbctScans))

        val response = OnDevicePlanSynthesizer.response(stlScans)
        assertEquals("mobile-stl-best-effort", response.source)
        assertEquals("CONSISTENT", response.correctness?.verdict)
        assertTrue(response.caveat!!.contains("STL metadata only"))
        assertTrue(response.warnings!!.joinToString(" ").contains("browser/full engine"))
    }

    @Test
    fun storedBrowserReviewCarriesOpaqueJson() {
        val review = StoredPlanReview.create("case-review.json", 11, "{\"ok\":true}")
        assertEquals("case-review.json", review.fileName)
        assertEquals("{\"ok\":true}", review.jsonText)
        assertEquals(null, review.caseReview)
        assertTrue(review.id.isNotEmpty())
    }

    @Test
    fun storedCaseReviewFixtureDecodesForMobileImport() {
        val text = fixture("case-review-v1.json").readText()
        val stored = StoredPlanReview.importCaseReview("case-review-v1.json", text.toByteArray().size, text)
        val review = stored.caseReview
        assertNotNull(review)

        assertEquals("orthoplan-case-review-v1", review!!.schema)
        assertEquals("stored-review", review.kind)
        assertEquals("stl-only", review.reviewTier.tier)
        assertFalse(review.reviewTier.rootBoneAware)
        assertEquals(5, review.unresolvedDataGaps.size)
        assertFalse(review.editable.inMobile)
        assertTrue(review.editable.requiresBrowserEngine)
        assertEquals("https://ortho.example/app/?case=golden-case-001", review.handoff.openUrl)
        assertEquals("orthoplan://case/golden-case-001", review.handoff.deepLink)
        assertEquals(review.handoff.openUrl, review.handoff.qrPayload)
    }

    @Test
    fun storedCaseReviewImportRejectsNonStoredReviewJson() {
        try {
            StoredPlanReview.importCaseReview("bad.json", 11, "{\"ok\":true}")
            throw AssertionError("Expected invalid stored-review JSON to be rejected")
        } catch (_: Exception) {
            // Expected: either schema decode fails or the stored-review gate rejects it.
        }
    }

    @Test
    fun decodeGeneratePlanResponseSubset() {
        val body = """
            {
              "ok": true,
              "source": "template",
              "correctness": { "verdict": "CONSISTENT", "extra": 1 },
              "stage_count": 12,
              "timeline": {
                "stage_count": 12, "wear_interval_days": 14,
                "projected_duration_days": 168, "projected_duration_weeks": 24.0,
                "caveat": "Projection excludes refinements."
              },
              "caveat": "Plan generation is deterministic ...",
              "plan": { "stages": [] }
            }
        """.trimIndent()
        val response = json.decodeFromString(GeneratePlanResponse.serializer(), body)
        assertTrue(response.ok)
        assertEquals("CONSISTENT", response.correctness?.verdict)
        assertEquals(24.0, response.timeline?.projectedDurationWeeks!!, 0.0)
    }

    @Test
    fun verdictLabelNeverImpliesApproval() {
        for (verdict in listOf("CONSISTENT", "ISSUES")) {
            val label = SafetyText.verdictLabel(verdict).lowercase()
            for (banned in listOf("safe", "approved", "cleared", "ready")) {
                assertFalse("verdict label leaked '$banned'", label.contains(banned))
            }
        }
        assertEquals("Internally consistent", SafetyText.verdictLabel("CONSISTENT"))
        assertEquals("Issues found", SafetyText.verdictLabel("ISSUES"))
    }

    private fun fixture(name: String): File {
        val candidates = listOf(
            File("../fixtures/$name"),
            File("../../fixtures/$name"),
            File("mobile/fixtures/$name"),
        )
        return candidates.firstOrNull { it.isFile }
            ?: error("Missing fixture $name from ${File(".").absolutePath}")
    }
}
