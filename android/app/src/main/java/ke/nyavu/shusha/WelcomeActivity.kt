package ke.nyavu.shusha

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView

/**
 * First screen: the name, written.
 *
 * The icon is the app's own launcher mark rather than an emoji, the wordmark is the serif the
 * product uses everywhere else, and the caret is bone instead of the mint this screen shipped
 * with. It still types the name and moves on by itself, because that is the product's idea:
 * an address is something you watch being read.
 */
class WelcomeActivity : Activity() {

    private val handler = Handler(Looper.getMainLooper())
    private val word = "Nyavu"

    private lateinit var title: TextView
    private lateinit var caret: TextView
    private lateinit var tagline: TextView
    private var index = 0

    private fun dp(v: Int) = NyavuTheme.dp(this, v)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = NyavuTheme.BG
        window.navigationBarColor = NyavuTheme.BG

        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(NyavuTheme.BG)
            setPadding(dp(30), 0, dp(30), 0)
        }

        val mark = ImageView(this).apply {
            setImageResource(R.mipmap.ic_launcher)
            scaleType = ImageView.ScaleType.FIT_CENTER
        }
        page.addView(mark, LinearLayout.LayoutParams(dp(96), dp(96)).apply { bottomMargin = dp(26) })

        val line = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        title = TextView(this).apply {
            text = ""
            textSize = 44f
            setTextColor(NyavuTheme.ink)
            typeface = NyavuTheme.serif(bold = true)
            letterSpacing = -0.02f
        }
        line.addView(title)

        caret = TextView(this).apply {
            text = "|"
            textSize = 34f
            setTextColor(NyavuTheme.BONE)
            typeface = NyavuTheme.mono()
        }
        line.addView(caret, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { leftMargin = dp(4) })

        page.addView(line)

        tagline = TextView(this).apply {
            text = "Read the address before you trust it."
            textSize = 14f
            setTextColor(NyavuTheme.muted)
            typeface = NyavuTheme.serif()
            alpha = 0f
            setPadding(0, dp(16), 0, 0)
        }
        page.addView(tagline)

        setContentView(page)
        type()
        blink()
    }

    /** One letter every 130 ms: quick enough not to be a wait, slow enough to read as writing. */
    private fun type() {
        if (index <= word.length) {
            title.text = word.substring(0, index)
            index++
            handler.postDelayed({ type() }, 130)
        } else {
            handler.postDelayed({ caret.animate().alpha(0f).setDuration(200).start() }, 260)
            handler.postDelayed({ tagline.animate().alpha(1f).setDuration(420).start() }, 320)
            handler.postDelayed({
                startActivity(Intent(this, MainActivity::class.java))
                overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
                finish()
            }, 1100)
        }
    }

    private fun blink() {
        caret.animate().alpha(0.25f).setDuration(320)
            .withEndAction { caret.animate().alpha(1f).setDuration(320).withEndAction { blink() }.start() }
            .start()
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
