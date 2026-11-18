/*
 * These run on the JVM, with no device and no MuPDF. They cover the arithmetic that
 * decides how large a bitmap the app asks the engine for — the one place where a
 * mistake turns into an OutOfMemoryError on a real phone.
 */
package com.futureautomation.nextpdf.viewer

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ZoomTest {

    @Test
    fun `zoom never goes below fit width`() {
        assertEquals(MIN_ZOOM, clampZoom(0.1f), 0f)
        assertEquals(MIN_ZOOM, clampZoom(-5f), 0f)
    }

    @Test
    fun `zoom never goes above the maximum`() {
        assertEquals(MAX_ZOOM, clampZoom(99f), 0f)
    }

    @Test
    fun `a not-a-number zoom falls back to fit width instead of propagating`() {
        assertEquals(MIN_ZOOM, clampZoom(Float.NaN), 0f)
    }

    @Test
    fun `at fit width the render is the viewport width`() {
        assertEquals(1080, renderWidth(1080, 1f))
    }

    @Test
    fun `zooming asks for a proportionally wider bitmap`() {
        assertEquals(2160, renderWidth(1080, 2f))
    }

    @Test
    fun `the render width is capped so a deep zoom cannot ask for an impossible bitmap`() {
        val width = renderWidth(1440, MAX_ZOOM)
        assertEquals(MAX_RENDER_WIDTH_PX, width)
        assertTrue(width <= MAX_RENDER_WIDTH_PX)
    }

    @Test
    fun `an unmeasured viewport asks for nothing rather than for one pixel`() {
        assertEquals(0, renderWidth(0, 2f))
        assertEquals(0, renderWidth(-100, 2f))
    }

    @Test
    fun `stepping out from fit width stays at fit width`() {
        assertEquals(MIN_ZOOM, steppedZoom(MIN_ZOOM, 0.8f), 0f)
    }

    @Test
    fun `stepping in repeatedly stops at the maximum`() {
        var zoom = MIN_ZOOM
        repeat(40) { zoom = steppedZoom(zoom, 1.25f) }
        assertEquals(MAX_ZOOM, zoom, 0f)
    }

    @Test
    fun `the percentage shown matches the zoom`() {
        assertEquals(100, zoomPercent(1f))
        assertEquals(250, zoomPercent(2.5f))
        assertEquals(800, zoomPercent(99f))
    }
}
