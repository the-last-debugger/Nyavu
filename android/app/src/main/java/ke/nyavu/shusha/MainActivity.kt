package ke.nyavu.shusha

import android.app.Activity
import android.content.Intent
import android.net.VpnService
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

/**
 * Single screen: the API address, the two controls for the DNS filter, and a note on
 * how links are checked. The address is stored in shared preferences so the app can
 * follow a tunnel URL that changes without needing a new build.
 */
class MainActivity : Activity() {

    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.START
            setPadding(56, 110, 56, 56)
        }

        val title = TextView(this).apply {
            text = "Nyavu"
            textSize = 26f
        }
        val blurb = TextView(this).apply {
            text = "Checks links you share to it, and can block known phishing and " +
                   "advertising domains at the DNS level."
            textSize = 14f
            setPadding(0, 14, 0, 26)
        }

        val apiLabel = TextView(this).apply {
            text = "Nyavu service address"
            textSize = 12f
            setPadding(0, 0, 0, 6)
        }
        val apiField = EditText(this).apply {
            setText(NyavuApi.base(this@MainActivity))
            hint = "https://example.trycloudflare.com"
            textSize = 13f
            setSingleLine()
        }
        val saveApi = Button(this).apply {
            text = "Save address"
            setOnClickListener {
                val value = apiField.text.toString().trim().trimEnd('/')
                getSharedPreferences("nyavu", MODE_PRIVATE).edit()
                    .putString("apiBase", value).apply()
                status.text = "Saved. Links will be checked against $value"
            }
        }

        status = TextView(this).apply {
            textSize = 14f
            setPadding(0, 26, 0, 22)
        }

        val hint = TextView(this).apply {
            text = "To check a link: open it in any app, tap Share, and choose Nyavu. " +
                   "No notification access is requested."
            textSize = 13f
            setPadding(0, 0, 0, 24)
        }

        val vpn = Button(this).apply {
            text = "Start DNS filtering"
            setOnClickListener { requestVpn() }
        }
        val stop = Button(this).apply {
            text = "Stop filtering"
            setOnClickListener {
                stopService(Intent(this@MainActivity, NyavuVpnService::class.java))
                refresh()
            }
        }

        box.addView(title)
        box.addView(blurb)
        box.addView(apiLabel)
        box.addView(apiField)
        box.addView(saveApi)
        box.addView(status)
        val urlField = EditText(this).apply {
            setHint("Paste a link to check")
            setSingleLine()
            textSize = 13f
        }
        val check = Button(this).apply {
            text = "Check link"
            setOnClickListener {
                val link = urlField.text.toString().trim()
                if (link.isNotEmpty()) {
                    val i = Intent(this@MainActivity, LinkGateActivity::class.java).apply {
                        action = Intent.ACTION_SEND
                        type = "text/plain"
                        putExtra(Intent.EXTRA_TEXT, link)
                    }
                    startActivity(i)
                }
            }
        }

        box.addView(hint)
        box.addView(urlField)
        box.addView(check)
        box.addView(vpn)
        box.addView(stop)
        setContentView(box)
    }

    private fun requestVpn() {
        val consent = VpnService.prepare(this)
        if (consent != null) startActivityForResult(consent, REQ_VPN) else startFilter()
    }

    @Deprecated("startActivityForResult is retained for API 26 compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_VPN && resultCode == RESULT_OK) startFilter()
        refresh()
    }

    private fun startFilter() {
        try {
            startForegroundService(Intent(this, NyavuVpnService::class.java))
        } catch (e: Exception) {
            status.text = "Could not start the filter: ${e.message}"
        }
        refresh()
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        status.text = if (NyavuVpnService.running) {
            "DNS filter: running"
        } else {
            "DNS filter: stopped. If another VPN (such as Tailscale) is active, " +
                "Android allows only one — turn the other off first."
        }
    }

    companion object {
        private const val REQ_VPN = 41
    }
}
