package ke.nyavu.shusha

import android.content.Context
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.util.TypedValue
import android.widget.TextView

/**
 * The look the web app settled on, in one place.
 *
 * Sage rather than the mint this app shipped with, bone for anything you press, a serif for
 * written matter and a monospace for figures. Keeping it here means a screen cannot quietly
 * drift back to the old palette, which is how the app came to look like a different product
 * from the site it is built on.
 */
object NyavuTheme {

    const val BG = 0xFF04060B.toInt()
    const val PANEL = 0xFF0A0F15.toInt()
    const val PANEL_EDGE = 0x1FFFFFFF
    const val FIELD = 0xFF111823.toInt()

    val ink = 0xFFE9E6DE.toInt()
    val muted = 0xFFA7ADA1.toInt()
    val faint = 0xFF6E7468.toInt()

    const val ACCENT = 0xFF8FA98F.toInt()
    const val SAFE = 0xFF7FA98F.toInt()
    const val DANGER = 0xFFC97B84.toInt()
    const val WARN = 0xFFC7A76A.toInt()
    const val BONE = 0xFFE9E3D6.toInt()
    const val ON_BONE = 0xFF14170F.toInt()

    fun dp(context: Context, value: Int): Int =
        TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, value.toFloat(),
            context.resources.displayMetrics).toInt()

    fun serif(bold: Boolean = false): Typeface =
        Typeface.create(Typeface.SERIF, if (bold) Typeface.BOLD else Typeface.NORMAL)

    fun mono(bold: Boolean = false): Typeface =
        Typeface.create(Typeface.MONOSPACE, if (bold) Typeface.BOLD else Typeface.NORMAL)

    fun panel(context: Context, fill: Int = PANEL, radius: Int = 20, edge: Int = PANEL_EDGE):
        GradientDrawable = GradientDrawable().apply {
        setColor(fill)
        cornerRadius = dp(context, radius).toFloat()
        setStroke(dp(context, 1), edge)
    }

    fun pill(context: Context, fill: Int, edge: Int, radius: Int = 40): GradientDrawable =
        GradientDrawable().apply {
            setColor(fill)
            cornerRadius = dp(context, radius).toFloat()
            setStroke(dp(context, 1), edge)
        }

    /** A small uppercase label, the way the site marks a section. */
    fun label(context: Context, text: String): TextView = TextView(context).apply {
        this.text = text.uppercase()
        textSize = 9.5f
        setTextColor(faint)
        letterSpacing = 0.16f
        typeface = Typeface.DEFAULT_BOLD
        setPadding(0, dp(context, 20), 0, dp(context, 9))
    }

    /** A line that breathes while work is out, the same rhythm the detector uses. */
    fun breathing(context: Context, base: String): Pair<TextView, Runnable> {
        val view = TextView(context).apply {
            text = base
            textSize = 12f
            setTextColor(faint)
        }
        val frames = listOf(base, "$base.", "$base..", "$base...")
        var index = 0
        val ticker = object : Runnable {
            override fun run() {
                view.text = frames[index % frames.size]
                index++
                view.postDelayed(this, 320)
            }
        }
        view.post(ticker)
        view.tag = ticker
        return view to ticker
    }

    /** The verdict colour, in the web's key: red for phishing, amber for unsure, sage for clear. */
    fun toneFor(risk: String): Int = when (risk) {
        "high", "phishing" -> DANGER
        "medium", "suspicious" -> WARN
        else -> SAFE
    }

    /** The words the web uses, so the app and the site say the same thing. */
    fun headlineFor(risk: String): String = when (risk) {
        "high", "phishing" -> "This one is worth avoiding"
        "medium", "suspicious" -> "Worth a second look"
        else -> "This reads as ordinary"
    }

    fun reasonTitleFor(risk: String): String = when (risk) {
        "high", "phishing" -> "What Nyavu noticed"
        "medium", "suspicious" -> "What gave Nyavu pause"
        else -> "What stood out, in a good way"
    }
}
