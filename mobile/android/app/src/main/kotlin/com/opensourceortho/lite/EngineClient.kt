package com.opensourceortho.lite

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/** Failures surfaced to the UI. The lite app never falls back to an on-device
 *  plan; any failure becomes an explicit "engine offline / rejected" state. */
sealed class EngineException(message: String) : Exception(message) {
    class Offline(message: String) : EngineException(message)
    class Rejected(val errors: List<String>) : EngineException(errors.joinToString("\n"))
    class Decode(message: String) : EngineException(message)
}

/**
 * Thin coroutine HTTP client over the OpenSource Ortho engine. Implements only
 * the lite-flow endpoints from ../../API_CONTRACT.md using java.net (no OkHttp),
 * keeping the dependency surface small.
 */
class EngineClient(
    private val config: EngineConfig = EngineConfig.DEFAULT,
    private val json: Json = Json { ignoreUnknownKeys = true; encodeDefaults = true },
) {
    /** `POST /api/generate-plan` - the core lite call. */
    suspend fun generatePlan(request: GeneratePlanRequest): GeneratePlanResponse {
        val body = json.encodeToString(GeneratePlanRequest.serializer(), request)
        val raw = postJson("/api/generate-plan", body)
        val response = try {
            json.decodeFromString(GeneratePlanResponse.serializer(), raw)
        } catch (e: Exception) {
            throw EngineException.Decode("Could not read engine response: ${e.message}")
        }
        if (!response.ok) {
            throw EngineException.Rejected(response.errors ?: listOf("request rejected"))
        }
        return response
    }

    /** `GET /api/mesh/<id>` - raw mesh bytes for the 3D preview, or null if the
     *  engine has no registered asset (caller falls back to schematic teeth). */
    suspend fun meshBytes(assetId: String): ByteArray? = withContext(Dispatchers.IO) {
        val url = URL("${config.baseUrl}/api/mesh/${encode(assetId)}")
        val conn = url.openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "GET"
            if (conn.responseCode != 200) return@withContext null
            conn.inputStream.use { it.readBytes() }
        } catch (e: IOException) {
            throw EngineException.Offline("Engine unreachable: ${e.message}")
        } finally {
            conn.disconnect()
        }
    }

    private suspend fun postJson(path: String, body: String): String = withContext(Dispatchers.IO) {
        val conn = (URL("${config.baseUrl}$path").openConnection() as HttpURLConnection)
        try {
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            val stream = if (conn.responseCode in 200..299) conn.inputStream else conn.errorStream
            stream?.use { it.readBytes().toString(Charsets.UTF_8) }
                ?: throw EngineException.Offline("Empty response from engine")
        } catch (e: IOException) {
            throw EngineException.Offline("Engine unreachable: ${e.message}")
        } finally {
            conn.disconnect()
        }
    }

    private fun encode(value: String): String =
        java.net.URLEncoder.encode(value, "UTF-8").replace("+", "%20")
}
