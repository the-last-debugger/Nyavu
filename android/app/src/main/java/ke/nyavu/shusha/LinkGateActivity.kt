package ke.nyavu.shusha

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * The zero-permission interception surface.
 *
 * Android hands us a link only when the user explicitly shares one to Nyavu, or opens
 * it with Nyavu. Nothing is read in the background, no notification is inspected, and
 * the app has no access to messages. This replaces the notification listener, which
 * required read access to every notification on the device.
 */
class LinkGateActivity : Activity() {

    private lateinit var headline: TextView
    private lateinit var detail: TextView
    private lateinit var reasons: TextView
    private lateinit var actions: LinearLayout
    private var target: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        target = extractUrl(intent)

        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.START
            setPadding(56, 120, 56, 56)
        }
        val brand = TextView(this).apply {
            text = "Nyavu"
            textSize = 26f
        }
        val sub = TextView(this).apply {
            text = "Shusha Nyavu: checking this link on your device"
            textSize = 13f
            setPadding(0, 10, 0, 34)
        }
        headline = TextView(this).apply { textSize = 20f; text = "Checking…" }
        detail = TextView(this).apply { textSize = 14f; setPadding(0, 12, 0, 18) }
        reasons = TextView(this).apply { textSize = 14f; setPadding(0, 0, 0, 28) }

        actions = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.START
        }

        box.addView(brand)
        box.addView(sub)
        box.addView(headline)
        box.addView(detail)
        box.addView(reasons)
        box.addView(actions)
        setContentView(box)

        val url = target
        if (url == null) {
            headline.text = "No link found"
            detail.text = "Share a link to Nyavu, or paste one in the app."
            showClose()
        } else {
            check(url)
        }
    }

    /** Pull a URL out of a shared text blob, or fall back to the intent data. */
    private fun extractUrl(intent: Intent?): String? {
        if (intent == null) return null
        if (intent.action == Intent.ACTION_SEND &&
            intent.type?.startsWith("text/") == true
        ) {
            val shared = intent.getStringExtra(Intent.EXTRA_TEXT)?.trim() ?: return null
            val found = Regex("""https?://[^\s"'<>]+""", RegexOption.IGNORE_CASE)
                .find(shared)?.value
            if (found != null) return found
            return if (shared.contains(".")) "http://$shared" else null
        }
        return intent.dataString
    }

    private fun check(url: String) {
        headline.text = "Checking…"
        detail.text = url
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
        conn.outputStream.use {
            it.write(JSONObject().put("url", url).toString().toByteArray())
        }
        if (conn.responseCode != 200) error("HTTP ${conn.responseCode}")
        return JSONObject(conn.inputStream.bufferedReader().readText())
    }

    private fun render(url: String, json: JSONObject) {
        val phishing = json.optString("verdict") == "phishing"
        val pct = Math.round(json.optDouble("probability", 0.0) * 100)
        val established = json.optString("reputation") == "established"

        headline.text = when {
            established -> "Established domain · $pct%"
            phishing -> "This link looks like phishing · $pct%"
            else -> "No phishing pattern detected · $pct%"
        }
        detail.text = json.optString("host", url) +
            if (json.has("suggested")) {
                "\nDid you mean ${json.getJSONObject("suggested").optString("domain")}?"
            } else ""

        val list = json.optJSONArray("reasons")
        val text = buildString {
            if (list != null) {
                for (i in 0 until minOf(list.length(), 4)) appendLine("• ${list.getString(i)}")
            }
        }
        reasons.text = text.ifEmpty { "No strong phishing indicators were found." }

        actions.removeAllViews()
        if (!phishing && !established) {
            actions.addView(primaryButton("Open link") { openExternally(url) })
        } else if (!established) {
            actions.addView(primaryButton("Go back") { finish() })
            actions.addView(secondaryButton("Open anyway") { openExternally(url) })
        } else {
            actions.addView(primaryButton("Open link") { openExternally(url) })
        }
        actions.addView(secondaryButton("Close") { finish() })
    }

    private fun failed(url: String) {
        headline.text = "Could not reach Nyavu"
        detail.text = "The service is not responding. Check that the API is running."
        reasons.text = ""
        actions.removeAllViews()
        actions.addView(primaryButton("Open anyway") { openExternally(url) })
        actions.addView(secondaryButton("Close") { finish() })
    }

    private fun showClose() {
        actions.removeAllViews()
        actions.addView(secondaryButton("Close") { finish() })
    }

    private fun openExternally(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (e: ActivityNotFoundException) {
            // no browser installed; nothing sensible to do
        }
        finish()
    }

    private fun primaryButton(label: String, action: () -> Unit) =
        Button(this).apply {
            text = label
            setOnClickListener { action() }
        }

    private fun secondaryButton(label: String, action: () -> Unit) =
        Button(this).apply {
            text = label
            setOnClickListener { action() }
        }
}
