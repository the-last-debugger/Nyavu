package ke.nyavu.shusha

import android.app.Activity
import android.content.Intent
import android.net.VpnService
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/**
 * Single screen: shows the state of the two permissions and starts/stops the DNS filter.
 * Deliberately built in code so the project needs no layout resources.
 */
class MainActivity : Activity() {

    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.START
            setPadding(56, 120, 56, 56)
        }

        val title = TextView(this).apply {
            text = "Shusha Nyavu"
            textSize = 26f
        }
        val blurb = TextView(this).apply {
            text = "Checks the links your phone receives and filters known phishing " +
                   "and advertising domains at the DNS level. Nothing leaves the device " +
                   "except a host name sent to your own Nyavu service."
            textSize = 14f
            setPadding(0, 24, 0, 32)
        }
        status = TextView(this).apply {
            textSize = 15f
            setPadding(0, 0, 0, 32)
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
        box.addView(status)
        box.addView(hint)
        box.addView(vpn)
        box.addView(stop)
        setContentView(box)
    }

    private fun requestVpn() {
        val consent = VpnService.prepare(this)
        if (consent != null) {
            startActivityForResult(consent, REQ_VPN)
        } else {
            startFilter()
        }
    }

    @Deprecated("startActivityForResult is retained for API 26 compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_VPN && resultCode == RESULT_OK) startFilter()
        refresh()
    }

    private fun startFilter() {
        startForegroundService(Intent(this, NyavuVpnService::class.java))
        refresh()
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        status.text = "DNS filter: " + (if (NyavuVpnService.running) "running" else "stopped")
    }

    companion object {
        private const val REQ_VPN = 41
    }
}
