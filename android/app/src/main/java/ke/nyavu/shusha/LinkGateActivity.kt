package ke.nyavu.shusha

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * The share target: a link arrives from another app and is checked immediately.
 *
 * Nothing is read in the background, no notification is inspected, and the app has no access
 * to messages. Android hands over a link only when a person chooses Nyavu, which is the whole
 * of the permission model here.
 */
class LinkGateActivity : Activity() {

    private fun dp(v: Int) = NyavuTheme.dp(this, v)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = NyavuTheme.BG
        window.navigationBarColor = NyavuTheme.BG

        val url = extractUrl(intent)
        if (url == null) {
            finish()
            return
        }

        val scroll = ScrollView(this).apply { setBackgroundColor(NyavuTheme.BG) }
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(30), dp(24), dp(24))
        }
        scroll.addView(page)

        page.addView(TextView(this).apply {
            text = "Nyavu"
            textSize = 22f
            setTextColor(NyavuTheme.ink)
            typeface = NyavuTheme.serif(bold = true)
        })
        page.addView(TextView(this).apply {
            text = "Reading the address"
            textSize = 15f
            setTextColor(NyavuTheme.faint)
            setPadding(0, dp(12), 0, 0)
        })
        page.addView(TextView(this).apply {
            text = url
            textSize = 12.5f
            setTextColor(NyavuTheme.muted)
            typeface = NyavuTheme.mono()
            setLineSpacing(dp(3).toFloat(), 1.1f)
            setPadding(0, dp(8), 0, 0)
        })
        setContentView(scroll)

        Thread {
            val res = runCatching { Api.predict(this, url) }.getOrNull()
            runOnUiThread {
                if (res == null || !res.ok) {
                    page.addView(TextView(this).apply {
                        text = "Nyavu could not be reached. Check your connection."
                        textSize = 13f
                        setTextColor(NyavuTheme.WARN)
                        setPadding(0, dp(16), 0, 0)
                    })
                    return@runOnUiThread
                }
                val json = runCatching { res.json() }.getOrNull()
                if (json == null) {
                    finish()
                    return@runOnUiThread
                }
                VerdictDialog(this, json) { link ->
                    runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(link))) }
                }.show()
                finish()
            }
        }.start()
    }

    /** Pull a URL out of a shared text blob, or fall back to the intent data. */
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
}
