package ke.nyavu.shusha

import android.content.Context
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Small shared helpers.
 *
 * FIRST CUT: this file has not yet been compiled or run on a device. It is included
 * so the team can build and finish it against the existing Android SDK, and the
 * README records exactly what is and is not done.
 */
object NyavuApi {
    const val DEFAULT_BASE = "https://nyavu.onrender.com"

    fun base(ctx: Context): String =
        ctx.getSharedPreferences("nyavu", Context.MODE_PRIVATE)
            .getString("apiBase", DEFAULT_BASE) ?: DEFAULT_BASE

    /** Returns the model probability that the address is phishing, or null on failure. */
    fun probabilityOf(ctx: Context, url: String): Double? = runCatching {
        val conn = URL(base(ctx) + "/api/predict").openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.connectTimeout = 4000
        conn.readTimeout = 6000
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json")
        conn.outputStream.use { it.write(JSONObject().put("url", url).toString().toByteArray()) }
        if (conn.responseCode != 200) return null
        val body = conn.inputStream.bufferedReader().readText()
        JSONObject(body).getDouble("probability")
    }.getOrNull()

    fun hostOf(url: String): String? = runCatching { URL(url).host }.getOrNull()?.lowercase()
}

object Counters {
    private fun prefs(ctx: Context) = ctx.getSharedPreferences("nyavu", Context.MODE_PRIVATE)

    fun read(ctx: Context): Triple<Int, Int, Int> = with(prefs(ctx)) {
        Triple(getInt("checked", 0), getInt("flagged", 0), getInt("blocked", 0))
    }

    fun bump(ctx: Context, checked: Boolean = false, flagged: Boolean = false, blocked: Boolean = false) {
        val (c, f, b) = read(ctx)
        prefs(ctx).edit()
            .putInt("checked", c + if (checked) 1 else 0)
            .putInt("flagged", f + if (flagged) 1 else 0)
            .putInt("blocked", b + if (blocked) 1 else 0)
            .apply()
    }
}

/**
 * Reads every notification posted on the device and looks for a link or for the
 * language that spam notifications use. A link is scored by Nyavu; a flagged
 * notification is dismissed.
 *
 * Requires the user to grant notification access in system settings — the app
 * cannot read notifications without that explicit grant.
 */
/**
 * DNS-level filter implemented as a local VPN.
 *
 * Only the DNS resolver address is routed into the tunnel (10.111.222.1/32), so the
 * rest of the device's traffic is untouched. Queries for blocked names are answered
 * locally with NXDOMAIN; every other query is forwarded to an upstream resolver and
 * the answer is relayed back.
 *
 * FIRST CUT: UDP on port 53 only. TCP DNS, DNS-over-TLS and IPv6 are not handled.
 */
