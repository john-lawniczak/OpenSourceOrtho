package com.opensourceortho.lite

/** Offline scanner geometry import. Material paths and external textures are never opened. */
object ScanImport {
    private val whitespace = Regex("\\s+")
    val extensions = setOf("stl", "obj", "ply", "asc", "xyz", "pts")
    const val formats = "STL, OBJ, PLY, ASC, XYZ, PTS"
    fun supports(filename: String) = filename.substringAfterLast('.', "").lowercase() in extensions

    fun decode(bytes: ByteArray, filename: String, check: () -> Unit = {}): StlMesh {
        require(bytes.size <= StlMesh.MAX_BYTES) { "Scan exceeds mobile preview limit." }
        return when (filename.substringAfterLast('.', "").lowercase()) {
            "stl" -> StlMesh.decode(bytes, check)
            "obj" -> textMesh(bytes, true, false, check)
            "ply" -> PlyImport.decode(bytes, check)
            "asc", "xyz" -> textMesh(bytes, false, false, check)
            "pts" -> textMesh(bytes, false, true, check)
            else -> error("Unsupported scan. Export $formats from your scanner.")
        }
    }

    internal fun validateTextLines(bytes: ByteArray, offset: Int = 0, check: () -> Unit = {}) {
        var length = 0
        for (i in offset until bytes.size) {
            if (i % 262144 == 0) check()
            val b = bytes[i].toInt()
            length = if (b == 10 || b == 13) 0 else length + 1
            require(b != 0 && length <= 16384) { "Invalid or overlong scan text line." }
        }
    }

    private fun textMesh(bytes: ByteArray, obj: Boolean, counted: Boolean, check: () -> Unit): StlMesh {
        validateTextLines(bytes, 0, check)
        val points = FloatValues()
        val triangles = FloatValues()
        var expected: Int? = null
        bytes.inputStream().bufferedReader().useLines { lines ->
            lines.forEachIndexed { i, line ->
                if (i % 1024 == 0) check()
                val clean = line.substringBefore('#').trim()
                if (clean.isEmpty()) return@forEachIndexed
                val tokens = clean.split(whitespace)
                if (counted && expected == null) {
                    require(tokens.size == 1) { "PTS must begin with a point count." }
                    expected = tokens[0].toInt()
                    require(expected!! in 1..StlMesh.MAX_TRIANGLES) { "Invalid point count." }
                } else if (obj && tokens[0] == "f") {
                    val indices = tokens.drop(1).map {
                        val raw = it.substringBefore('/').toInt()
                        require(raw != 0) { "OBJ indices start at one." }
                        if (raw > 0) raw - 1 else points.size / 3 + raw
                    }
                    appendFace(indices, points, triangles)
                } else if (!obj || tokens[0] == "v") {
                    val coordinates = if (obj) tokens.drop(1) else tokens
                    require(coordinates.size >= 3 && (!obj || coordinates.size in listOf(3,4,6)) &&
                        (!obj || coordinates.size != 4 || coordinates[3].toFloatOrNull() == 1f)) { "Incomplete point." }
                    coordinates.take(3).forEach {
                        val v = it.toFloat()
                        require(v.isFinite() && kotlin.math.abs(v) <= 1_000_000f) { "Invalid coordinates." }
                        points.add(v)
                    }
                    require(points.size / 3 <= StlMesh.MAX_TRIANGLES) { "Too many points." }
                } else if (tokens[0] in listOf("l", "curv", "curv2", "surf")) {
                    error("Export a polygon mesh or point cloud from your scanner.")
                }
            }
        }
        require(expected == null || expected == points.size / 3) { "PTS point count does not match its data." }
        return StlMesh.build((if (triangles.isEmpty()) points else triangles).toFloatArray(), check, triangles.isEmpty())
    }

    internal fun appendFace(indices: List<Int>, points: List<Float>, triangles: FloatValues) {
        require(indices.size in 3..64 && indices.all { it >= 0 && it < points.size / 3 } && indices.distinct().size == indices.size) { "Invalid polygon indices." }
        require(triangles.size / 9 + indices.size - 2 <= StlMesh.MAX_TRIANGLES) { "Too many triangles." }
        if (indices.size > 3) validatePolygon(indices, points)
        for (i in 1 until indices.size - 1) {
            for (index in listOf(indices[0], indices[i], indices[i+1])) {
                for (axis in 0..2) triangles.add(points[index*3+axis])
            }
        }
    }

    private fun validatePolygon(indices: List<Int>, points: List<Float>) {
        val p = indices.map { index -> DoubleArray(3) { points[index*3+it].toDouble() } }
        fun cross(a: DoubleArray, b: DoubleArray) = doubleArrayOf(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
        val n = cross(DoubleArray(3) { p[1][it]-p[0][it] }, DoubleArray(3) { p[2][it]-p[1][it] })
        val length = kotlin.math.sqrt(n.sumOf { it*it })
        require(length > 0) { "Degenerate polygon. Export triangulated geometry." }
        for (i in p.indices) {
            val distance = (0..2).sumOf { (p[i][it]-p[0][it])*n[it] } / length
            require(kotlin.math.abs(distance) <= 0.0001) { "Non-planar face. Export triangulated geometry." }
            val edge = DoubleArray(3) { p[(i+1)%p.size][it]-p[i][it] }
            for (j in p.indices) {
                if (j == i || j == (i+1)%p.size) continue
                val side = cross(edge, DoubleArray(3) { p[j][it]-p[i][it] })
                require((0..2).sumOf { side[it]*n[it] } > 0) {
                    "Concave or self-intersecting face. Export triangulated geometry."
                }
            }
        }
    }
}
