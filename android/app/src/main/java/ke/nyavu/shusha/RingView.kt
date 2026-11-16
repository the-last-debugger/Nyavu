package ke.nyavu.shusha

import android.animation.ValueAnimator
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.view.View
import android.view.animation.DecelerateInterpolator

/**
 * The home screen's score ring.
 *
 * Draws a 270° arc that fills to a fraction and writes a value in the middle. The
 * arc animates from its current position rather than jumping, because the number is
 * the first thing anyone reads and it should look measured, not assigned.
 */
class RingView(context: Context) : View(context) {

    private val density = resources.displayMetrics.density

    private val trackPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 10f * density
        strokeCap = Paint.Cap.ROUND
        color = Color.parseColor("#141C27")
    }

    private val arcPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 10f * density
        strokeCap = Paint.Cap.ROUND
        color = Color.parseColor("#43E8C8")
        setShadowLayer(18f * density, 0f, 0f, Color.parseColor("#8043E8C8"))
    }

    private val valuePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textAlign = Paint.Align.CENTER
        color = Color.parseColor("#EEF2FA")
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
    }

    private val captionPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textAlign = Paint.Align.CENTER
        color = Color.parseColor("#5B667D")
        letterSpacing = 0.14f
    }

    private val box = RectF()
    private var fraction = 0f
    private var shown = 0f
    private var target = 0f

    var valueText: String = "0"
        set(v) { field = v; invalidate() }

    var captionText: String = "of 3"
        set(v) { field = v; invalidate() }

    var accent: Int = Color.parseColor("#43E8C8")
        set(v) {
            field = v
            arcPaint.color = v
            arcPaint.setShadowLayer(18f * density, 0f, 0f, v)
            invalidate()
        }

    /** Animate to a new fraction (0..1) and a new headline value. */
    fun setProgress(newFraction: Float, newValue: String) {
        target = newFraction.coerceIn(0f, 1f)
        valueText = newValue
        ValueAnimator.ofFloat(shown, target).apply {
            duration = 900
            interpolator = DecelerateInterpolator()
            addUpdateListener {
                shown = it.animatedValue as Float
                invalidate()
            }
            start()
        }
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        val inset = 14f * density
        box.set(inset, inset, w - inset, h - inset)
        valuePaint.textSize = (w * 0.30f).coerceAtMost(64f * density)
        captionPaint.textSize = 10f * density
        fraction = w.toFloat()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val start = 135f
        val sweep = 270f

        canvas.drawArc(box, start, sweep, false, trackPaint)
        if (shown > 0.001f) {
            canvas.drawArc(box, start, sweep * shown, false, arcPaint)
        }

        val cx = width / 2f
        val cy = height / 2f
        canvas.drawText(valueText, cx, cy + valuePaint.textSize * 0.30f, valuePaint)
        canvas.drawText(captionText, cx, cy + valuePaint.textSize * 0.30f + 20f * density, captionPaint)
    }
}
