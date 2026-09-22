package com.opensourceortho.lite

/** Primitive storage prevents millions of boxed Floats during text/PLY parsing. */
internal class FloatValues : AbstractList<Float>() {
    private var data = FloatArray(4096)
    override var size: Int = 0
        private set
    override fun get(index: Int): Float {
        require(index in 0 until size)
        return data[index]
    }
    fun add(value: Float) {
        require(size < StlMesh.MAX_TRIANGLES * 9) { "Too much geometry for mobile preview." }
        if (size == data.size) data = data.copyOf(minOf(data.size * 2, StlMesh.MAX_TRIANGLES * 9))
        data[size++] = value
    }
    fun toFloatArray() = data.copyOf(size)
}
