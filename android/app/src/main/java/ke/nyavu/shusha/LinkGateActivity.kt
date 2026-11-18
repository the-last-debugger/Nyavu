package ke.nyavu.shusha

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * The verdict, in the app.
 *
 * Same shape as the site: the address, the number, the headline in the product's voice, the
 * pieces that raised it, and the explanation folded away behind a plus until asked for. The
 * app is a native screen rather than the site in a webview, so this is rebuilt with Android
 * widgets; the words, the colours and the order are the ones a visitor to the site would
 * recognise.
 */
class LinkGateActivity : Activity() {

    private val tone get() = NyavuTheme

    private lateinit var headline: TextView
    private lateinit var address: TextView
    private lateinit var figure: TextView
    private lateinit var barFill: View
    private lateinit var barTrack: View
    private lateinit var reasonsTitle: TextView
    private lateinit var reasonsBox: LinearLayout
    private lateinit var foldRow: LinearLayout
    private lateinit var foldBody: TextView
    private lateinit var actions: LinearLayout
    private var target: String? = null

    private fun dp(v: Int) = NyavuTheme.dp(this, v)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        target = extractUrl(intent)
        window.statusBarColor = NyavuTheme.BG
        window.navigationBarColor = NyavuTheme.BG

        val scroll = ScrollView(this).apply { setBackgroundColor(NyavuTheme.BG) }
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(34), dp(22), dp(40))
        }
        scroll.addView(page)

        page.addView(TextView(this).apply {
            text = "Nyavu"
            textSize = 24f
            setTextColor(NyavuTheme.ink)
            typeface = tone.serif(bold = true)
        })

        headline = TextView(this).apply {
            text = "Reading the address"
            textSize = 25f
            setTextColor(NyavuTheme.ink)
            typeface = tone.serif()
            setLineSpacing(dp(2).toFloat(), 1.05f)
            setPadding(0, dp(18), 0, dp(6))
        }
        page.addView(headline)

        address = TextView(this).apply {
            text = target ?: ""
            textSize = 12.5f
            setTextColor(NyavuTheme.muted)
            typeface = tone.mono()
            setLineSpacing(dp(3).toFloat(), 1.1f)
        }
        page.addView(address)

        // the number, and a quiet bar instead of the old dial
        val figureRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.BOTTOM
            setPadding(0, dp(16), 0, 0)
        }
        figure = TextView(this).apply {
            text = "·"
            textSize = 34f
            setTextColor(NyavuTheme.ink)
            typeface = tone.mono(bold = true)
        }
        figureRow.addView(figure)
        figureRow.addView(TextView(this).apply {
            text = " risk out of 100"
            textSize = 11.5f
            setTextColor(NyavuTheme.faint)
            setPadding(dp(8), 0, 0, dp(7))
        })
        page.addView(figureRow)

        barTrack = View(this).apply { setBackgroundColor(0x14FFFFFF) }
        val barRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, dp(10), 0, 0)
        }
        barFill = View(this).apply { setBackgroundColor(NyavuTheme.ACCENT) }
        barRow.addView(barFill, LinearLayout.LayoutParams(0, dp(3), 0.0001f))
        barRow.addView(barTrack, LinearLayout.LayoutParams(0, dp(3), 1f))
        page.addView(barRow)

        foldRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(16), 0, 0)
            visibility = View.GONE
        }
        foldRow.addView(TextView(this).apply {
            text = "+"
            textSize = 15f
            setTextColor(NyavuTheme.faint)
            typeface = tone.mono()
            setPadding(0, 0, dp(8), 0)
        })
        foldRow.addView(TextView(this).apply {
            text = "How that was worked out"
            textSize = 12f
            setTextColor(NyavuTheme.faint)
        })
        foldBody = TextView(this).apply {
            textSize = 12.5f
            setTextColor(NyavuTheme.muted)
            setLineSpacing(dp(3).toFloat(), 1.1f)
            setPadding(0, dp(10), 0, 0)
            visibility = View.GONE
        }
        foldRow.setOnClickListener {
            val open = foldBody.visibility != View.VISIBLE
            foldBody.visibility = if (open) View.VISIBLE else View.GONE
            (foldRow.getChildAt(0) as TextView).text = if (open) "−" else "+"
        }
        page.addView(foldRow)
        page.addView(foldBody)

        reasonsTitle = tone.label(this, "What Nyavu noticed")
        reasonsTitle.visibility = View.GONE
        page.addView(reasonsTitle)

        reasonsBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        page.addView(reasonsBox)

        actions = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(22), 0, 0)
        }
        page.addView(actions)

        page.addView(TextView(this).apply {
            text = "A verdict is an assessment, not a guarantee of safety."
            textSize = 11f
            setTextColor(NyavuTheme.faint)
            setPadding(0, dp(20), 0, 0)
        })

        setContentView(scroll)

        val url = target
        if (url == null) {
            headline.text = "No link to read"
            address.text = "Share a link to Nyavu, or paste one in the app."
            addButton("Close", primary = false) { finish() }
        } else {
            check(url)
        }
    }

    private fun extractUrl(intent: Intent?): String? {
        if (intent == null) return null
        if (intent.action == Intent.ACTION_SEND && intent.type?.startsWith("text/") == true) {
            val shared = intent.getStringExtra(Intent.EXTRA_TEXT)?.trim() ?: return null
            val found = Regex("""https?://[^\s"'<>]+""", RegexOption.IGNORE_CASE).find(shared)?.value
            if (found != null) return found
            return if (shared.contains(".")) "http://$shared" else null
        }
        return intent.dataString
    }

    private fun check(url: String) {
        headline.text = "Reading the address"
        Thread {
            val parsed = runCatching { request(url) }.getOrNull()
            runOnUiThread { if (parsed != null) render(url, parsed) else failed(url) }
        }.start()
    }

    private fun request(url: String): JSONObject {
        val conn = URL(NyavuApi.base(this) + "/api/predict").openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.connectTimeout = 6000
        conn.readTimeout = 9000
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json")
        conn.outputStream.use { it.write(JSONObject().put("url", url).toString().toByteArray()) }
        if (conn.responseCode != 200) error("HTTP ${conn.responseCode}")
        return JSONObject(conn.inputStream.bufferedReader().readText())
    }

    private fun render(url: String, json: JSONObject) {
        val verdict = json.optString("verdict")
        val risk = json.optString("risk")
        val pct = Math.round(json.optDouble("probability", 0.0) * 100).toInt()
        val established = json.optString("reputation") == "established"
        val colour = if (established) NyavuTheme.SAFE else tone.toneFor(risk)

        headline.text = if (established) "An established domain" else tone.headlineFor(risk)
        address.text = json.optString("host", url)
        figure.text = pct.toString()
        figure.setTextColor(colour)
        barFill.setBackgroundColor(colour)
        (barFill.layoutParams as LinearLayout.LayoutParams).weight = (pct.coerceAtLeast(1)).toFloat()
        (barTrack.layoutParams as LinearLayout.LayoutParams).weight =
            (100 - pct).coerceAtLeast(1).toFloat()
        barFill.requestLayout()
        barTrack.requestLayout()

        // the fold: one sentence that says what the number is, the rest behind the plus
        val note = when {
            established ->
                "Held at $pct so that a known site is never flagged on the shape of its name."
            risk == "high" ->
                "Scored $pct out of 100. That is the estimated chance this address is a phish, read from its name alone."
            risk == "medium" ->
                "Scored $pct out of 100. Below half, but not low enough to call it safe."
            else ->
                "Scored $pct out of 100. Nothing in the name matches the patterns measured on known phish."
        }
        foldBody.text = note + " Anything above 65 is treated as a concern, and below 35 as clear."
        foldRow.visibility = View.VISIBLE

        reasonsTitle.text = tone.reasonTitleFor(risk).uppercase()
        reasonsTitle.visibility = View.VISIBLE
        reasonsBox.removeAllViews()

        val list = json.optJSONArray("reasons")
        val count = minOf(list?.length() ?: 0, 4)
        if (count == 0) {
            reasonsBox.addView(reasonRow("1", "Nothing in the name raised a pattern Nyavu knows."))
        } else {
            for (i in 0 until count) {
                reasonsBox.addView(reasonRow((i + 1).toString(), list!!.getString(i)))
            }
        }

        actions.removeAllViews()
        when {
            established || risk == "low" ->
                addButton("Open link", primary = true) { openExternally(url) }
            risk == "medium" -> {
                addButton("Open anyway", primary = true) { openExternally(url) }
            }
            else -> {
                addButton("Close this", primary = true) { finish() }
            }
        }
        addButton("Close", primary = false) { finish() }
    }

    private fun reasonRow(number: String, text: String): LinearLayout {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            background = tone.panel(this@LinkGateActivity, radius = 14)
            setPadding(dp(12), dp(12), dp(14), dp(12))
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
            )
            params.bottomMargin = dp(8)
            layoutParams = params
        }
        row.addView(TextView(this).apply {
            this.text = number
            textSize = 10f
            setTextColor(NyavuTheme.faint)
            typeface = tone.mono()
            gravity = Gravity.CENTER
            setPadding(0, dp(2), dp(12), 0)
        })
        row.addView(TextView(this).apply {
            this.text = text
            textSize = 12.5f
            setTextColor(NyavuTheme.muted)
            setLineSpacing(dp(3).toFloat(), 1.1f)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        })
        return row
    }

    private fun failed(url: String) {
        headline.text = "Nyavu could not be reached"
        address.text = "Check your connection and try again."
        figure.text = "·"
        actions.removeAllViews()
        addButton("Open anyway", primary = false) { openExternally(url) }
        addButton("Close", primary = false) { finish() }
    }

    private fun addButton(label: String, primary: Boolean, action: () -> Unit) {
        val button = Button(this).apply {
            text = label
            isAllCaps = false
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(if (primary) NyavuTheme.ON_BONE else NyavuTheme.ink)
            background = if (primary) {
                GradientDrawableFactory.fill(this@LinkGateActivity, NyavuTheme.BONE, 26)
            } else {
                tone.panel(this@LinkGateActivity, fill = 0x0DFFFFFF, radius = 26)
            }
            setOnClickListener { action() }
        }
        val params = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(48)
        )
        params.bottomMargin = dp(8)
        actions.addView(button, params)
    }

    private fun openExternally(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (e: ActivityNotFoundException) {
            // no browser installed; nothing sensible to do
        }
        finish()
    }
}

/** Small helper so the theme file does not depend on a Context for a plain fill. */
object GradientDrawableFactory {
    fun fill(context: android.content.Context, colour: Int, radius: Int): android.graphics.drawable.GradientDrawable =
        android.graphics.drawable.GradientDrawable().apply {
            setColor(colour)
            cornerRadius = NyavuTheme.dp(context, radius).toFloat()
        }
}
