package com.opensourceortho.lite

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.junit.Assert.*
import org.junit.Test

class StlMeshTest {
    @Test fun allOriginalFacesSurviveLoading() {
        val history = SampleHistory.decode(File("../../sample-history/history.json").readText())
        for (arch in history.visits.flatMap { it.arches }) {
            val mesh = StlMesh.decode(File("../../../datasets/${history.specimenId}/${arch.filename}").readBytes())
            assertEquals(arch.filename, arch.faceCount, mesh.triangleCount)
            assertEquals(arch.faceCount * 18, mesh.vertices.size)
            assertTrue(mesh.vertices.all { it.isFinite() })
            assertTrue(mesh.span in 50f..70f)
        }
    }

    @Test fun asciiAndMalformedInput() {
        val ascii = "solid scan\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid scan"
        val mesh = StlMesh.decode(ascii.toByteArray())
        assertEquals(1, mesh.triangleCount)
        assertArrayEquals(floatArrayOf(0.5f, 0.5f, 0f), mesh.center, 0f)
        assertArrayEquals(floatArrayOf(0f, 0f, 1f), mesh.vertices.copyOfRange(3, 6), 0f)
        listOf("", "solid scan", ascii.replace("vertex 0 1 0\n", ""),
            ascii.replace("vertex 0 1 0", "vertex NaN 1 0")).forEach {
            assertTrue(runCatching { StlMesh.decode(it.toByteArray()) }.isFailure)
        }
        val truncated = ByteArray(134).also { it[80] = 2 }
        assertTrue(runCatching { StlMesh.decode(truncated) }.isFailure)
    }

    @Test fun binarySolidHeaderIsNotAscii() {
        val bytes = ByteArray(134)
        "solid".toByteArray().copyInto(bytes)
        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        buffer.putInt(80, 1)
        buffer.putFloat(108, 1f)
        buffer.putFloat(124, 1f)
        assertEquals(1, StlMesh.decode(bytes).triangleCount)
    }
}
