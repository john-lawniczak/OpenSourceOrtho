package com.opensourceortho.lite

import android.opengl.GLES20.*
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

/** Uploads complete surfaces once per GL context. Slider updates only the scissor rectangle. */
internal class ScanRenderer(private val presentation: ScanPresentation, private val onError: (String) -> Unit) : GLSurfaceView.Renderer {
    var yaw = 0f
    var pitch = -7f
    var zoom = 1f
    var progress = 0f
    private var width = 1
    private var height = 1
    private var program = 0
    private var failed = false
    private var position = 0
    private var normal = 0
    private var transformLocation = 0
    private var modelLocation = 0
    private var pointsLocation = 0
    private var buffers = IntArray(0)
    private val layers = presentation.before + presentation.after
    private val model = FloatArray(16)
    private val projection = FloatArray(16)
    private val transform = FloatArray(16)

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        failed = false
        try {
            glClearColor(0.065f, 0.09f, 0.14f, 1f)
            glEnable(GL_DEPTH_TEST)
            val vertex = shader(GL_VERTEX_SHADER, """
                uniform mat4 transform;
                uniform mat4 model;
                attribute vec3 position;
                attribute vec3 normal;
                varying vec3 surfaceNormal;
                void main() {
                    gl_Position = transform * vec4(position, 1.0);
                    gl_PointSize = 3.0;
                    surfaceNormal = mat3(model) * normal;
                }
            """.trimIndent())
            val fragment = shader(GL_FRAGMENT_SHADER, """
                precision mediump float;
                uniform float points;
                varying vec3 surfaceNormal;
                void main() {
                    vec3 n = normalize(surfaceNormal);
                    if (!gl_FrontFacing) n = -n;
                    float key = max(dot(n, normalize(vec3(-0.4, 0.6, 1.0))), 0.0);
                    float fill = max(dot(n, normalize(vec3(0.8, -0.2, 0.6))), 0.0);
                    float light = mix(0.23 + 0.57 * key + 0.20 * fill, 0.9, points);
                    gl_FragColor = vec4(vec3(0.83, 0.85, 0.88) * light, 1.0);
                }
            """.trimIndent())
            program = glCreateProgram()
            glAttachShader(program, vertex); glAttachShader(program, fragment); glLinkProgram(program)
            val linked = IntArray(1)
            glGetProgramiv(program, GL_LINK_STATUS, linked, 0)
            check(linked[0] != 0) { "Could not link scan shaders." }
            glDeleteShader(vertex); glDeleteShader(fragment)
            position = glGetAttribLocation(program, "position"); normal = glGetAttribLocation(program, "normal")
            transformLocation = glGetUniformLocation(program, "transform")
            modelLocation = glGetUniformLocation(program, "model"); pointsLocation = glGetUniformLocation(program, "points")
            buffers = IntArray(layers.size)
            glGenBuffers(buffers.size, buffers, 0)
            layers.forEachIndexed { i, layer ->
                glBindBuffer(GL_ARRAY_BUFFER, buffers[i])
                val data = ByteBuffer.allocateDirect(layer.mesh.vertices.size * 4).order(ByteOrder.nativeOrder())
                    .asFloatBuffer().apply { put(layer.mesh.vertices); position(0) }
                glBufferData(GL_ARRAY_BUFFER, layer.mesh.vertices.size * 4, data, GL_STATIC_DRAW)
                check(glGetError() == GL_NO_ERROR) { "Device could not allocate the scan surfaces. View one file at a time." }
            }
        } catch (e: Exception) {
            failed = true; onError(e.message ?: "Device could not render this scan.")
        }
    }
    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        this.width = width.coerceAtLeast(1); this.height = height.coerceAtLeast(1)
        glViewport(0, 0, width, height)
    }
    override fun onDrawFrame(gl: GL10?) {
        glDisable(GL_SCISSOR_TEST)
        glClear(GL_COLOR_BUFFER_BIT or GL_DEPTH_BUFFER_BIT)
        if (failed) return
        glUseProgram(program)
        val aspect = width.toFloat() / height
        val vertical = maxOf(if (presentation.before.size > 1) 2f else 1.25f, 1.1f / aspect) / zoom
        Matrix.orthoM(projection, 0, -vertical*aspect, vertical*aspect, -vertical, vertical, -10f, 10f)
        val split = if (presentation.after.isEmpty()) width else (width*(1f-progress)).toInt()
        glEnable(GL_SCISSOR_TEST)
        glScissor(0, 0, split, height)
        drawLayers(presentation.before, 0)
        if (presentation.after.isNotEmpty()) {
            glScissor(split, 0, width-split, height)
            drawLayers(presentation.after, presentation.before.size)
            if (split in 1 until width) {
                glScissor(split-1, 0, 2, height)
                glClearColor(0.2f, 0.8f, 1f, 1f); glClear(GL_COLOR_BUFFER_BIT)
                glClearColor(0.065f, 0.09f, 0.14f, 1f)
            }
        }
        glDisable(GL_SCISSOR_TEST)
    }
    private fun drawLayers(pass: List<ScanLayer>, offset: Int) {
        pass.forEachIndexed { i, layer ->
            val mesh = layer.mesh
            Matrix.setIdentityM(model, 0)
            Matrix.translateM(model, 0, 0f, if (pass.size > 1) { if (i == 0) 0.95f else -0.95f } else 0f, 0f)
            Matrix.rotateM(model, 0, pitch, 1f, 0f, 0f); Matrix.rotateM(model, 0, yaw, 0f, 1f, 0f)
            val scale = (if (pass.size > 1) 1.65f else 2f) / mesh.span
            Matrix.scaleM(model, 0, scale*layer.rotation[0], scale*layer.rotation[1], scale*layer.rotation[2])
            Matrix.translateM(model, 0, -mesh.center[0], -mesh.center[1], -mesh.center[2])
            Matrix.multiplyMM(transform, 0, projection, 0, model, 0)
            glUniformMatrix4fv(transformLocation, 1, false, transform, 0)
            glUniformMatrix4fv(modelLocation, 1, false, model, 0)
            glUniform1f(pointsLocation, if (mesh.isPointCloud) 1f else 0f)
            glBindBuffer(GL_ARRAY_BUFFER, buffers[offset+i])
            glEnableVertexAttribArray(position); glEnableVertexAttribArray(normal)
            glVertexAttribPointer(position, 3, GL_FLOAT, false, 24, 0)
            glVertexAttribPointer(normal, 3, GL_FLOAT, false, 24, 12)
            glDrawArrays(if (mesh.isPointCloud) GL_POINTS else GL_TRIANGLES, 0, mesh.vertexCount)
        }
    }
    private fun shader(type: Int, source: String): Int {
        val shader = glCreateShader(type)
        glShaderSource(shader, source); glCompileShader(shader)
        val compiled = IntArray(1)
        glGetShaderiv(shader, GL_COMPILE_STATUS, compiled, 0)
        check(compiled[0] != 0) { "Could not compile scan shaders." }
        return shader
    }
}
