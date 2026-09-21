package com.opensourceortho.lite

import java.io.File
import org.junit.Assert.*
import org.junit.Test
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject

class SampleHistoryTest {
    private val fixture = File("../../sample-history/history.json")

    @Test
    fun observedVisitsKeepSeparateGeometryAndDates() {
        val history = SampleHistory.decode(fixture.readText())
        assertEquals(listOf("2026-06-05", "2026-09-17"), history.visits.map { it.date })
        assertEquals(listOf("Baseline", "Week 7"), history.visits.map { it.label })
        assertEquals(4, history.visits.flatMap { it.arches }.map { it.sha256 }.distinct().size)
        assertTrue(history.visits[1].arches.all { it.units == "unverified" })
        assertTrue(history.timing.contains("Five-day"))
        history.visits.flatMap { it.arches }.forEach {
            assertTrue(File(fixture.parentFile, it.previewImage).isFile)
        }
    }

    @Test(expected = IllegalArgumentException::class)
    fun emptyVisitsAreRejectedWithoutSyntheticFallback() {
        val json = Json.parseToJsonElement(fixture.readText()).jsonObject.toMutableMap()
        json["visits"] = JsonArray(emptyList())
        SampleHistory.decode(JsonObject(json).toString())
    }
}
