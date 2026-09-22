package com.opensourceortho.lite

import android.content.Context
import android.opengl.GLSurfaceView
import android.view.MotionEvent
import android.view.ScaleGestureDetector

/** Depth-tested GPU surface. Uploads every triangle once, then redraws only on interaction. */
class ScanSurfaceView(context: Context, presentation: ScanPresentation, onError: (String) -> Unit) : GLSurfaceView(context) {
    private val surface = ScanRenderer(presentation) { message -> post { onError(message) } }
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
        contentDescription = "Recorded scan surfaces. Drag to rotate and pinch to zoom."
    }

    fun reveal(progress: Float) {
        queueEvent { surface.progress = progress.coerceIn(0f, 1f) }
        requestRender()
    }

    fun resetView() {
        queueEvent { surface.yaw = 0f; surface.pitch = -7f; surface.zoom = 1f }
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
        if (event.actionMasked == MotionEvent.ACTION_UP || event.actionMasked == MotionEvent.ACTION_CANCEL) {
            parent?.requestDisallowInterceptTouchEvent(false)
            if (event.actionMasked == MotionEvent.ACTION_UP) performClick()
        }
        return true
    }

    override fun performClick(): Boolean { super.performClick(); return true }
}
