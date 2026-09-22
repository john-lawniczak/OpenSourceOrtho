package com.opensourceortho.lite

import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Bounded ASCII/binary PLY import, preserving all faces and accepting both endian orders. */
internal object PlyImport {
    private data class Property(val name: String, val type: String, val countType: String? = null)
    private data class Element(val name: String, val count: Int, val properties: MutableList<Property> = mutableListOf())
    private data class Scalar(val size: Int, val signed: Boolean, val floating: Boolean = false)
    private val types = mapOf(
        "char" to Scalar(1,true), "int8" to Scalar(1,true), "uchar" to Scalar(1,false), "uint8" to Scalar(1,false),
        "short" to Scalar(2,true), "int16" to Scalar(2,true), "ushort" to Scalar(2,false), "uint16" to Scalar(2,false),
        "int" to Scalar(4,true), "int32" to Scalar(4,true), "uint" to Scalar(4,false), "uint32" to Scalar(4,false),
        "float" to Scalar(4,true,true), "float32" to Scalar(4,true,true), "double" to Scalar(8,true,true), "float64" to Scalar(8,true,true),
    )

    fun decode(bytes: ByteArray, check: () -> Unit): StlMesh {
        val prefix = bytes.copyOfRange(0, minOf(bytes.size, 65536)).toString(Charsets.ISO_8859_1)
        val marker = Regex("(?m)^end_header\\r?\\n").find(prefix) ?: error("Missing PLY header terminator.")
        val offset = marker.range.last + 1
        val (format, elements) = header(prefix.substring(0, offset))
        if (format == "ascii") ScanImport.validateTextLines(bytes, offset, check)
        val cursor = Cursor(bytes, offset, format)
        val points = FloatValues()
        val triangles = FloatValues()
        for (element in elements) {
            repeat(element.count) { row ->
                if (row % 1024 == 0) check()
                val xyz = FloatArray(3) { Float.NaN }
                var face: List<Int>? = null
                for (property in element.properties) {
                    if (property.countType != null) {
                        val count = cursor.integer(property.countType)
                        require(count in 3..64) { "Unsupported PLY polygon size." }
                        face = List(count) { cursor.integer(property.type) }
                    } else {
                        val value = cursor.value(property.type)
                        val axis = listOf("x", "y", "z").indexOf(property.name)
                        if (axis >= 0) xyz[axis] = value.toFloat()
                    }
                }
                if (element.name == "vertex") {
                    require(xyz.all { it.isFinite() && kotlin.math.abs(it) <= 1_000_000f }) { "Invalid PLY coordinates." }
                    xyz.forEach { points.add(it) }
                } else {
                    ScanImport.appendFace(requireNotNull(face) { "Missing PLY face indices." }, points, triangles)
                }
            }
        }
        require(cursor.atEnd()) { "PLY contains extra data beyond declared counts." }
        return StlMesh.build((if (triangles.isEmpty()) points else triangles).toFloatArray(), check, triangles.isEmpty())
    }

    private fun header(text: String): Pair<String, List<Element>> {
        val lines = text.lineSequence().toList()
        require(lines.first() == "ply") { "Not a PLY file." }
        var format = ""
        val elements = mutableListOf<Element>()
        for (line in lines.drop(1)) {
            val p = line.trim().split(Regex("\\s+"))
            when (p.first()) {
                "format" -> {
                    require(p.size == 3 && p[2] == "1.0" && format.isEmpty() && p[1] in listOf("ascii", "binary_little_endian", "binary_big_endian")) { "Unsupported PLY encoding." }
                    format = p[1]
                }
                "element" -> {
                    require(p.size == 3 && p[1] in listOf("vertex", "face") && elements.none { it.name == p[1] }) { "Unsupported PLY element." }
                    val count = p[2].toInt()
                    require(count in 0..StlMesh.MAX_TRIANGLES) { "Too many PLY elements." }
                    elements.add(Element(p[1], count))
                }
                "property" -> {
                    val element = elements.lastOrNull() ?: error("Property before element.")
                    val property = if (p.size == 5 && p[1] == "list" && types[p[2]]?.floating == false && types[p[3]]?.floating == false && element.name == "face" && p[4] in listOf("vertex_indices", "vertex_index")) {
                        Property(p[4], p[3], p[2])
                    } else {
                        require(p.size == 3 && types.containsKey(p[1])) { "Unsupported PLY property." }
                        Property(p[2], p[1])
                    }
                    require(element.properties.size < 32 && element.properties.none { it.name == property.name } &&
                        !(property.countType != null && element.properties.any { it.countType != null })) { "Duplicate PLY property." }
                    element.properties.add(property)
                }
                "comment", "obj_info", "end_header", "" -> Unit
                else -> error("Unsupported PLY header.")
            }
        }
        require(format.isNotEmpty() && elements.firstOrNull()?.name == "vertex" && elements[0].count > 0 &&
            elements[0].properties.map { it.name }.containsAll(listOf("x","y","z"))) { "Missing PLY vertices." }
        return format to elements
    }

    private class Cursor(bytes: ByteArray, offset: Int, private val format: String) {
        private val buffer = ByteBuffer.wrap(bytes).order(if (format == "binary_big_endian") ByteOrder.BIG_ENDIAN else ByteOrder.LITTLE_ENDIAN).apply { position(offset) }
        private val tokens = if (format == "ascii") bytes.inputStream(offset, bytes.size-offset).bufferedReader(Charsets.US_ASCII)
            .lineSequence().flatMap { it.trim().split(Regex("\\s+")).asSequence() }.filter { it.isNotEmpty() }.iterator() else emptyList<String>().iterator()
        fun value(name: String): Double {
            val type = types[name] ?: error("Invalid PLY scalar type.")
            val value = if (format == "ascii") {
                require(tokens.hasNext()) { "Truncated PLY data." }; tokens.next().toDouble()
            } else {
                require(buffer.remaining() >= type.size) { "Truncated PLY data." }
                if (type.floating) { if (type.size == 4) buffer.float.toDouble() else buffer.double }
                else when (type.size) {
                    1 -> { val v = buffer.get().toInt(); (if (type.signed) v else v and 255).toDouble() }
                    2 -> { val v = buffer.short.toInt(); (if (type.signed) v else v and 65535).toDouble() }
                    else -> { val v = buffer.int.toLong(); (if (type.signed) v else v and 0xffffffffL).toDouble() }
                }
            }
            require(value.isFinite()) { "Non-finite PLY scalar." }
            if (!type.floating) {
                val upper = Math.pow(2.0, (type.size*8 - if (type.signed) 1 else 0).toDouble()) - 1
                val lower = if (type.signed) -upper-1 else 0.0
                require(value >= lower && value <= upper && value == kotlin.math.floor(value)) { "Invalid PLY integer." }
            }
            return value
        }
        fun integer(type: String): Int {
            val value = value(type)
            require(value in Int.MIN_VALUE.toDouble()..Int.MAX_VALUE.toDouble()) { "PLY index overflow." }
            return value.toInt()
        }
        fun atEnd() = if (format == "ascii") !tokens.hasNext() else !buffer.hasRemaining()
    }
}
