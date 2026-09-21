package com.opensourceortho.lite

import android.content.Context
import android.opengl.GLES20.*
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

/** Depth-tested GPU surface. Uploads every triangle once, then redraws only on interaction. */
class ScanSurfaceView(context: Context, mesh: StlMesh, rotation: List<Float>) : GLSurfaceView(context) {
    private val surface = ScanRenderer(mesh, rotation)
    private var lastX = 0f
    private var lastY = 0f
    private val scaleDetector = ScaleGestureDetector(context, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
        override fun onScale(detector: ScaleGestureDetector): Boolean {
            val factor = detector.scaleFactor
            queueEvent { surface.zoom = (surface.zoom * factor).coerceIn(0.5f, 4f) }
            requestRender()
            return true
        }
    })

    init {
        setEGLContextClientVersion(2)
        setEGLConfigChooser(8, 8, 8, 8, 16, 0)
        preserveEGLContextOnPause = true
        setRenderer(surface)
        renderMode = RENDERMODE_WHEN_DIRTY
        contentDescription = "Real STL scan. Drag to rotate and pinch to zoom."
    }

    fun resetView() {
        queueEvent { surface.yaw = 0f; surface.pitch = 0f; surface.zoom = 1f }
        requestRender()
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        parent?.requestDisallowInterceptTouchEvent(true)
        scaleDetector.onTouchEvent(event)
        if (event.actionMasked == MotionEvent.ACTION_MOVE && !scaleDetector.isInProgress && event.pointerCount == 1) {
            val dx = (event.x - lastX) * 0.4f
            val dy = (event.y - lastY) * 0.4f
            queueEvent { surface.yaw += dx; surface.pitch += dy }
            requestRender()
        }
        lastX = event.x
        lastY = event.y
        if (event.actionMasked == MotionEvent.ACTION_UP) performClick()
        return true
    }

    override fun performClick(): Boolean { super.performClick(); return true }
}

private class ScanRenderer(private val mesh: StlMesh, private val rotation: List<Float>) : GLSurfaceView.Renderer {
    var yaw = 0f
    var pitch = 0f
    var zoom = 1f
    private var aspect = 1f
    private var program = 0
    private var vbo = 0
    private val model = FloatArray(16)
    private val projection = FloatArray(16)
    private val transform = FloatArray(16)

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        glClearColor(0.07f, 0.10f, 0.15f, 1f)
        glEnable(GL_DEPTH_TEST)
        val vertex = shader(GL_VERTEX_SHADER, """
            uniform mat4 transform;
            uniform mat4 model;
            attribute vec3 position;
            attribute vec3 normal;
            varying vec3 surfaceNormal;
            void main() {
                gl_Position = transform * vec4(position, 1.0);
                surfaceNormal = mat3(model) * normal;
            }
        """.trimIndent())
        val fragment = shader(GL_FRAGMENT_SHADER, """
            precision mediump float;
            varying vec3 surfaceNormal;
            void main() {
                vec3 n = normalize(surfaceNormal);
                if (!gl_FrontFacing) n = -n;
                float light = 0.30 + 0.70 * max(dot(n, normalize(vec3(-0.4, 0.6, 1.0))), 0.0);
                gl_FragColor = vec4(vec3(0.88, 0.85, 0.78) * light, 1.0);
            }
        """.trimIndent())
        program = glCreateProgram()
        glAttachShader(program, vertex)
        glAttachShader(program, fragment)
        glLinkProgram(program)
        val linked = IntArray(1)
        glGetProgramiv(program, GL_LINK_STATUS, linked, 0)
        check(linked[0] != 0) { glGetProgramInfoLog(program) }
        glDeleteShader(vertex)
        glDeleteShader(fragment)
        val ids = IntArray(1)
        glGenBuffers(1, ids, 0)
        vbo = ids[0]
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        val buffer: FloatBuffer = ByteBuffer.allocateDirect(mesh.vertices.size * 4)
            .order(ByteOrder.nativeOrder()).asFloatBuffer().apply { put(mesh.vertices); position(0) }
        glBufferData(GL_ARRAY_BUFFER, mesh.vertices.size * 4, buffer, GL_STATIC_DRAW)
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        glViewport(0, 0, width, height)
        aspect = width.toFloat() / height.coerceAtLeast(1)
    }

    override fun onDrawFrame(gl: GL10?) {
        glClear(GL_COLOR_BUFFER_BIT or GL_DEPTH_BUFFER_BIT)
        glUseProgram(program)
        Matrix.setIdentityM(model, 0)
        Matrix.rotateM(model, 0, pitch, 1f, 0f, 0f)
        Matrix.rotateM(model, 0, yaw, 0f, 1f, 0f)
        val scale = 2f / mesh.span
        Matrix.scaleM(model, 0, scale * rotation[0], scale * rotation[1], scale * rotation[2])
        Matrix.translateM(model, 0, -mesh.center[0], -mesh.center[1], -mesh.center[2])
        val vertical = 1.25f / zoom / minOf(aspect, 1f)
        Matrix.orthoM(projection, 0, -vertical*aspect, vertical*aspect, -vertical, vertical, -10f, 10f)
        Matrix.multiplyMM(transform, 0, projection, 0, model, 0)
        glUniformMatrix4fv(glGetUniformLocation(program, "transform"), 1, false, transform, 0)
        glUniformMatrix4fv(glGetUniformLocation(program, "model"), 1, false, model, 0)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        for ((name, offset) in listOf("position" to 0, "normal" to 12)) {
            val attribute = glGetAttribLocation(program, name)
            glEnableVertexAttribArray(attribute)
            glVertexAttribPointer(attribute, 3, GL_FLOAT, false, 24, offset)
        }
        glDrawArrays(GL_TRIANGLES, 0, mesh.triangleCount * 3)
    }

    private fun shader(type: Int, source: String): Int {
        val shader = glCreateShader(type)
        glShaderSource(shader, source)
        glCompileShader(shader)
        val compiled = IntArray(1)
        glGetShaderiv(shader, GL_COMPILE_STATUS, compiled, 0)
        check(compiled[0] != 0) { glGetShaderInfoLog(shader) }
        return shader
    }
}
