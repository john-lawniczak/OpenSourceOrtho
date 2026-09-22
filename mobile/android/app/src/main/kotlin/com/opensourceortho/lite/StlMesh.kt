package com.opensourceortho.lite

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.sqrt

/** Complete STL surface with derived face normals; no sampling or truncation. */
data class StlMesh(val vertices: FloatArray, val triangleCount: Int, val center: FloatArray, val span: Float, val isPointCloud: Boolean = false) {
    val vertexCount: Int get() = vertices.size / 6
    companion object {
        const val MAX_TRIANGLES = 1_000_000
        const val MAX_BYTES = 80 * 1024 * 1024

        fun decode(bytes: ByteArray, checkCancellation: () -> Unit = {}): StlMesh {
            require(bytes.size <= MAX_BYTES) { "Scan exceeds the mobile preview limit. Open it in the browser." }
            val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            val count = if (bytes.size >= 84) buffer.getInt(80).toLong() and 0xffffffffL else 0L
            val positions = if (count > 0 && 84L + count * 50L == bytes.size.toLong()) {
                require(count <= MAX_TRIANGLES) { "Too many triangles for mobile preview." }
                FloatArray(count.toInt() * 9) { index ->
                    if (index % 4096 == 0) checkCancellation()
                    buffer.getFloat(84 + (index / 9) * 50 + 12 + (index % 9) * 4)
                }
            } else {
                parseAscii(bytes, checkCancellation)
            }
            return build(positions, checkCancellation)
        }

        private fun parseAscii(bytes: ByteArray, checkCancellation: () -> Unit): FloatArray {
            ScanImport.validateTextLines(bytes, 0, checkCancellation)
            val text = bytes.toString(Charsets.UTF_8)
            require(text.trimStart().startsWith("solid") && text.contains("endsolid")) { "Incomplete or invalid STL." }
            val values = FloatValues()
            text.lineSequence().forEach { line ->
                if (values.size % 4096 == 0) checkCancellation()
                val parts = line.trim().split(Regex("\\s+"))
                if (parts.firstOrNull() == "vertex") {
                    require(parts.size == 4) { "Invalid STL vertex." }
                    parts.drop(1).forEach { values.add(it.toFloat()) }
                    require(values.size <= MAX_TRIANGLES * 9) { "Too many triangles for mobile preview." }
                }
            }
            return values.toFloatArray()
        }

        fun build(positions: FloatArray, checkCancellation: () -> Unit = {}, pointCloud: Boolean = false): StlMesh {
            require(positions.size <= MAX_TRIANGLES * (if (pointCloud) 3 else 9)) { "Too much geometry for mobile preview." }
            require(positions.isNotEmpty() && positions.size % (if (pointCloud) 3 else 9) == 0) { "Empty or incomplete STL." }
            require(positions.all { it.isFinite() && abs(it) <= 1_000_000f }) { "Invalid STL coordinates." }
            val low = FloatArray(3) { Float.POSITIVE_INFINITY }
            val high = FloatArray(3) { Float.NEGATIVE_INFINITY }
            val vertices = FloatArray(positions.size * 2)
            for (start in positions.indices step (if (pointCloud) 3 else 9)) {
                if (start % 4096 == 0) checkCancellation()
                if (pointCloud) {
                    for (axis in 0..2) {
                        val value = positions[start + axis]
                        low[axis] = minOf(low[axis], value); high[axis] = maxOf(high[axis], value)
                        vertices[start * 2 + axis] = value
                    }
                    vertices[start * 2 + 5] = 1f
                    continue
                }
                val a = FloatArray(3) { positions[start + 3 + it] - positions[start + it] }
                val b = FloatArray(3) { positions[start + 6 + it] - positions[start + it] }
                val n = floatArrayOf(a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
                val length = sqrt(n.sumOf { (it * it).toDouble() }).toFloat()
                val normal = if (length > 0) FloatArray(3) { n[it]/length } else floatArrayOf(0f, 0f, 1f)
                for (vertex in 0..2) {
                    for (axis in 0..2) {
                        val value = positions[start + vertex * 3 + axis]
                        low[axis] = minOf(low[axis], value)
                        high[axis] = maxOf(high[axis], value)
                        vertices[start * 2 + vertex * 6 + axis] = value
                        vertices[start * 2 + vertex * 6 + 3 + axis] = normal[axis]
                    }
                }
            }
            val span = (0..2).maxOf { high[it] - low[it] }
            require(span > 0 || pointCloud) { "STL has no spatial extent." }
            return StlMesh(vertices, if (pointCloud) 0 else positions.size / 9, FloatArray(3) { (low[it]+high[it])/2 }, maxOf(span, 0.0001f), pointCloud)
        }
    }
}
