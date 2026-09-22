package com.opensourceortho.lite

import java.io.File
import java.io.InputStream
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import org.junit.Assert.*
import org.junit.Test

class ScanImportTest {
    @Serializable private data class Fixture(val filename: String, val triangles: Int?, val points: Int?)
    @Test fun sharedScannerExportsAndMalformedFiles() {
        val folder = File("../../test-fixtures/scans")
        val cases = Json.decodeFromString<List<Fixture>>(File(folder, "cases.json").readText())
        for (item in cases) {
            val bytes = File(folder, item.filename).readBytes()
            if (item.triangles == null && item.points == null) {
                assertTrue(item.filename, runCatching { ScanImport.decode(bytes, item.filename) }.isFailure)
            } else {
                val mesh = ScanImport.decode(bytes, item.filename)
                assertEquals(item.filename, item.triangles ?: 0, mesh.triangleCount)
                assertEquals(item.filename, item.points != null, mesh.isPointCloud)
                assertEquals(item.filename, item.points ?: (item.triangles!! * 3), mesh.vertexCount)
                assertTrue(item.filename, mesh.vertices.all { it.isFinite() })
            }
        }
    }
    @Test fun nonStlFormatsCannotEnterStlFallback() {
        for (ext in ScanImport.extensions) {
            val scan = SelectedScan(fileName = "upper.${ext.uppercase()}", byteCount = 20, modality = "scan")
            assertTrue(scan.isSurfaceScan)
            assertTrue(LitePlanBuilder.minimalPlan(listOf(scan)).toString().contains("\"format\":\"$ext\""))
            assertEquals(ext == "stl", scan.isStl)
            assertEquals(ext == "stl", OnDevicePlanSynthesizer.canSynthesize(listOf(scan)))
        }
        assertFalse(SelectedScan("upper.obj", byteCount = 20, modality = "stl").isStl)
        assertFalse(SelectedScan("upper.stl", byteCount = 20, modality = "photo").isStl)
    }
    @Test fun boundedReadAndLongLines() {
        assertArrayEquals("0 0 0\n".toByteArray(), "0 0 0\n".byteInputStream().readScanBytes())
        val oversized = object : InputStream() {
            var remaining = StlMesh.MAX_BYTES + 1
            override fun read(): Int = if (remaining-- > 0) 0 else -1
            override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
                if (remaining == 0) return -1
                val count = minOf(length, remaining)
                remaining -= count
                return count
            }
        }
        assertTrue(runCatching { oversized.readScanBytes() }.isFailure)
        assertTrue(runCatching { ScanImport.decode("1 ".repeat(10000).toByteArray(), "scan.xyz") }.isFailure)
    }
    @Test fun cancellationStopsReadAndDecode() {
        val stop = { throw java.util.concurrent.CancellationException() }
        assertThrows(java.util.concurrent.CancellationException::class.java) { "0 0 0".byteInputStream().readScanBytes(stop) }
        assertThrows(java.util.concurrent.CancellationException::class.java) { ScanImport.decode("0 0 0".toByteArray(), "cloud.xyz", stop) }
    }
}
