package com.opensourceortho.lite

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
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
    fun requestDefaultsKeepDataLocal() {
        val request = LitePlanBuilder.request(emptyList())
        assertEquals("local", request.provider)
        assertFalse("lite must not opt into egress by default", request.shareAcknowledged)
        assertTrue(request.acknowledgeEducational)
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
}
