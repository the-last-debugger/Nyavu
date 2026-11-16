package ke.nyavu.shusha

import android.app.Activity
import android.content.Intent
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView

/**
 * First screen: the name arrives one letter at a time.
 *
 * Deliberately short. It exists to say what the product is before the controls
 * appear, not to hold anyone up - there is no login, no permission prompt, and it
 * moves on by itself after the word is complete.
 */
class WelcomeActivity : Activity() {

    private val handler = Handler(Looper.getMainLooper())
    private val word = "Welcome"

    private lateinit var title: TextView
    private lateinit var caret: View
    private lateinit var tagline: TextView
    private var index = 0

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = 0xFF04060B.toInt()
        window.navigationBarColor = 0xFF04060B.toInt()

        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(0xFF04060B.toInt())
            setPadding(dp(28), 0, dp(28), 0)
        }

        val mark = TextView(this).apply {
            text = "\uD83D\uDEE1"
            textSize = 30f
            gravity = Gravity.CENTER
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(0xFF0C1A1A.toInt())
                setStroke(dp(2), 0xFF2E7D6B.toInt())
            }
        }
        page.addView(mark, LinearLayout.LayoutParams(dp(84), dp(84)).apply { bottomMargin = dp(30) })

        // The word is left-aligned and grows to the right as letters arrive.
        val line = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL or Gravity.START
        }

        title = TextView(this).apply {
            text = ""
            textSize = 44f
            setTextColor(0xFFEEF2FA.toInt())
            typeface = Typeface.DEFAULT_BOLD
            letterSpacing = -0.03f
            gravity = Gravity.START
        }
        line.addView(title)

        caret = View(this).apply { setBackgroundColor(0xFF43E8C8.toInt()) }
        line.addView(caret, LinearLayout.LayoutParams(dp(3), dp(38)).apply { leftMargin = dp(4) })

        page.addView(line)

        tagline = TextView(this).apply {
            text = "Your personal link inspector"
            textSize = 13f
            setTextColor(0xFF6E7A90.toInt())
            alpha = 0f
            setPadding(0, dp(14), 0, 0)
        }
        page.addView(tagline)

        setContentView(page)
        blink()
        type()
    }

    /** One letter every 300 ms, then the caret stops. */
    private fun type() {
        if (index <= word.length) {
            title.text = word.substring(0, index)
            index++
            handler.postDelayed({ type() }, 300)
        } else {
            handler.postDelayed({ caret.animate().alpha(0f).setDuration(250).start() }, 300)
            handler.postDelayed({
                tagline.animate().alpha(1f).setDuration(550).start()
            }, 400)
            handler.postDelayed({
                startActivity(Intent(this, MainActivity::class.java))
                overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
                finish()
            }, 1500)
        }
    }

    private fun blink() {
        val on = caret.alpha > 0.5f
        caret.animate().alpha(if (on) 0.15f else 1f).setDuration(380).withEndAction { blink() }.start()
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
