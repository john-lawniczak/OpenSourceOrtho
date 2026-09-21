package com.opensourceortho.lite

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** Observed visits, kept separate from generated plan stages and selected user files. */
@Serializable
data class SampleHistory(
    val schema: String,
    val specimenId: String,
    val title: String,
    val summary: String,
    val timing: String,
    val limitation: String,
    val context: String,
    val visits: List<SampleVisit>,
    val events: List<SampleEvent>,
) {
    companion object {
        fun decode(text: String): SampleHistory {
            val history = Json.decodeFromString<SampleHistory>(text)
            require(history.schema == "opensource-ortho-mobile-history-v1")
            require(history.visits.isNotEmpty())
            require(history.visits.map { it.id }.distinct().size == history.visits.size)
            require(history.visits.all { it.arches.isNotEmpty() })
            return history
        }
    }
}

@Serializable
data class SampleVisit(
    val id: String,
    val label: String,
    val date: String,
    val detail: String,
    val arches: List<SampleArch>,
)

@Serializable
data class SampleArch(
    val name: String,
    val previewImage: String,
    val filename: String,
    val sha256: String,
    val faceCount: Int,
    val zeroAreaFaces: Int,
    val units: String,
)

@Serializable
data class SampleEvent(val id: String, val date: String, val label: String)
