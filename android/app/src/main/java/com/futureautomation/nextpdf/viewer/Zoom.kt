/*
 * Zoom arithmetic, kept free of Android and MuPDF so it can be tested on the JVM
 * without a device. Everything here is a pure function.
 */
package com.futureautomation.nextpdf.viewer

const val MIN_ZOOM = 1.0f
const val MAX_ZOOM = 8.0f

/** The largest bitmap width the app will ask for, whatever the zoom. */
const val MAX_RENDER_WIDTH_PX = 4096

fun clampZoom(value: Float): Float = when {
    value.isNaN() -> MIN_ZOOM
    else -> value.coerceIn(MIN_ZOOM, MAX_ZOOM)
}

/**
 * The pixel width a page should be drawn at. Capped, because a deep zoom on a wide
 * screen would otherwise ask for a bitmap no device can allocate — and an
 * OutOfMemoryError in the middle of a render is not a zoom feature.
 */
fun renderWidth(
    viewportWidthPx: Int,
    zoom: Float,
    maxWidthPx: Int = MAX_RENDER_WIDTH_PX,
): Int {
    if (viewportWidthPx <= 0) return 0
    val wanted = (viewportWidthPx.toFloat() * clampZoom(zoom)).toInt()
    return wanted.coerceIn(1, maxWidthPx)
}

/** Steps the zoom by a factor, clamped. Used by the + and − buttons. */
fun steppedZoom(current: Float, factor: Float): Float = clampZoom(clampZoom(current) * factor)

/** Human label for the zoom, e.g. 1.0 -> "100%". */
fun zoomPercent(zoom: Float): Int = Math.round(clampZoom(zoom) * 100f)
