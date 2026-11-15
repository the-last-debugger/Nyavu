package ke.nyavu.shusha

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONObject
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.InetAddress
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
class NyavuVpnService : VpnService() {

    private var tunnel: ParcelFileDescriptor? = null
    private var worker: Thread? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (tunnel == null) start()
        return START_STICKY
    }

    private fun start() {
        try {
            startForeground(NOTIF_ID, foregroundNotification())
        } catch (e: Exception) {
            // Android 12+ refuses a foreground service it considers undeclared.
            toast("Could not start the filter: " + (e.message ?: "foreground service refused"))
            stopSelf()
            return
        }
        Blocklist.load(this)

        val fd = try {
            Builder()
                .setSession("Nyavu DNS filter")
                .addAddress("10.111.222.1", 32)
                .addDnsServer("10.111.222.1")
                .addRoute("10.111.222.1", 32)
                .setBlocking(true)
                .establish()
        } catch (e: Exception) {
            null
        }

        if (fd == null) {
            // Almost always another VPN holding the single slot Android allows.
            toast("Another VPN is active. Turn it off, then start the filter again.")
            stopSelf()
            return
        }

        tunnel = fd
        running = true
        worker = Thread { loop() }.also { it.start() }
    }

    private fun toast(message: String) {
        android.os.Handler(mainLooper).post {
            android.widget.Toast.makeText(applicationContext, message,
                android.widget.Toast.LENGTH_LONG).show()
        }
    }

    private fun foregroundNotification(): android.app.Notification {
        val mgr = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            mgr.createNotificationChannel(
                NotificationChannel(CHANNEL, "DNS filter", NotificationManager.IMPORTANCE_LOW)
            )
        }
        return Notification.Builder(this, CHANNEL)
            .setContentTitle("Shusha Nyavu")
            .setContentText("Filtering known phishing and advertising domains")
            .setSmallIcon(android.R.drawable.ic_lock_lock)
            .build()
    }

    private fun loop() {
        val input = FileInputStream(tunnel!!.fileDescriptor)
        val output = FileOutputStream(tunnel!!.fileDescriptor)
        val buffer = ByteArray(32767)

        while (running) {
            val length = try {
                input.read(buffer)
            } catch (e: Exception) {
                break
            }
            if (length <= 0) continue
            try {
                handle(buffer, length, output)
            } catch (e: Exception) {
                // A malformed packet must not stop the tunnel.
            }
        }
    }

    private fun handle(packet: ByteArray, length: Int, out: FileOutputStream) {
        if (length < 28) return
        val version = (packet[0].toInt() shr 4) and 0x0f
        if (version != 4) return
        if (packet[9].toInt() != 17) return                      // UDP only

        val ihl = (packet[0].toInt() and 0x0f) * 4
        val dstPort = u16(packet, ihl + 2)
        if (dstPort != 53) return

        val dnsStart = ihl + 8
        val dnsLength = length - dnsStart
        if (dnsLength < 12) return

        val name = queryName(packet, dnsStart) ?: return

        if (Blocklist.isBlocked(name)) {
            val answer = nxdomain(packet, dnsStart, dnsLength)
            val reply = buildReply(packet, ihl, answer)
            out.write(reply)
            Counters.bump(this, checked = true, flagged = true, blocked = true)
            return
        }

        val upstream = forwarded(packet, dnsStart, dnsLength) ?: return
        val reply = buildReply(packet, ihl, upstream)
        out.write(reply)
        Counters.bump(this, checked = true)
    }

    /** Sends the query out on a protected socket and returns the resolver's payload. */
    private fun forwarded(packet: ByteArray, dnsStart: Int, dnsLength: Int): ByteArray? = runCatching {
        val query = packet.copyOfRange(dnsStart, dnsStart + dnsLength)
        DatagramSocket().use { socket ->
            protect(socket)
            socket.soTimeout = 4000
            val upstream = InetAddress.getByName(UPSTREAM)
            socket.send(DatagramPacket(query, query.size, upstream, 53))
            val buf = ByteArray(4096)
            val response = DatagramPacket(buf, buf.size)
            socket.receive(response)
            buf.copyOfRange(0, response.length)
        }
    }.getOrNull()

    private fun nxdomain(packet: ByteArray, dnsStart: Int, dnsLength: Int): ByteArray {
        val out = packet.copyOfRange(dnsStart, dnsStart + dnsLength)
        out[2] = 0x81.toByte()
        out[3] = 0x83.toByte()                                    // QR=1, RD=1, RA=1, RCODE=3
        for (i in 6 until 12) out[i] = 0                            // no answers/authority/additional
        return out
    }

    /** Wraps a DNS payload in an IPv4/UDP packet with the endpoints swapped. */
    private fun buildReply(original: ByteArray, ihl: Int, payload: ByteArray): ByteArray {
        val total = ihl + 8 + payload.size
        val reply = ByteArray(total)

        System.arraycopy(original, 0, reply, 0, ihl)
        reply[0] = 0x45                                             // IPv4, 20-byte header
        reply[2] = ((total shr 8) and 0xff).toByte()
        reply[3] = (total and 0xff).toByte()
        reply[8] = 64                                               // TTL
        reply[9] = 17                                               // UDP
        reply[10] = 0; reply[11] = 0                                // checksum cleared

        System.arraycopy(original, 16, reply, 12, 4)                // new src = old dst
        System.arraycopy(original, 12, reply, 16, 4)                // new dst = old src

        System.arraycopy(original, ihl, reply, ihl, 2)              // src port
        System.arraycopy(original, ihl + 2, reply, ihl + 2, 2)      // dst port
        val lenBytes = ((8 + payload.size) shr 8 and 0xff).toByte()
        reply[ihl + 4] = lenBytes
        reply[ihl + 5] = (8 + payload.size and 0xff).toByte()

        // swap the ports in the reply (source was the client, now the server)
        System.arraycopy(reply, ihl + 2, reply, ihl, 2)
        System.arraycopy(original, ihl, reply, ihl + 2, 2)

        reply[ihl + 6] = 0; reply[ihl + 7] = 0                      // UDP checksum optional in IPv4
        System.arraycopy(payload, 0, reply, ihl + 8, payload.size)

        val csum = ipChecksum(reply, ihl)
        reply[10] = ((csum shr 8) and 0xff).toByte()
        reply[11] = (csum and 0xff).toByte()
        return reply
    }

    private fun ipChecksum(data: ByteArray, ihl: Int): Int {
        var sum = 0L
        var i = 0
        while (i < ihl) {
            sum += ((data[i].toInt() and 0xff) shl 8) or (data[i + 1].toInt() and 0xff)
            i += 2
        }
        while (sum shr 16 != 0L) sum = (sum and 0xffff) + (sum shr 16)
        return (sum.inv() and 0xffff).toInt()
    }

    private fun queryName(packet: ByteArray, start: Int): String? {
        var offset = start + 12
        val labels = mutableListOf<String>()
        while (offset < packet.size && packet[offset].toInt() != 0) {
            val len = packet[offset].toInt() and 0xff
            if (len == 0 || offset + 1 + len > packet.size) return null
            labels += String(packet, offset + 1, len)
            offset += 1 + len
        }
        return if (labels.isEmpty()) null else labels.joinToString(".").lowercase()
    }

    private fun u16(data: ByteArray, offset: Int): Int =
        ((data[offset].toInt() and 0xff) shl 8) or (data[offset + 1].toInt() and 0xff)

    override fun onDestroy() {
        running = false
        worker?.interrupt()
        tunnel?.close()
        tunnel = null
        super.onDestroy()
    }

    companion object {
        @Volatile var running: Boolean = false
        private const val CHANNEL = "shusha"
        private const val NOTIF_ID = 1
        private const val UPSTREAM = "1.1.1.1"
    }
}

/**
 * Domain blocklist. The shipped list is a small starter set; the generator script in
 * tools/make_blocklist.py expands it from public ad/tracker/phishing lists into
 * app/src/main/assets/blocklist.txt.
 */
object Blocklist {
    private var domains: Set<String> = emptySet()
    private var loaded = false

    fun load(ctx: Context) {
        if (loaded) return
        domains = runCatching {
            ctx.assets.open("blocklist.txt").bufferedReader().readLines()
                .map { it.trim().lowercase() }
                .filter { it.isNotEmpty() && !it.startsWith("#") }
                .toSet()
        }.getOrElse { emptySet() }
        loaded = true
    }

    fun isBlocked(host: String): Boolean {
        if (domains.isEmpty()) return false
        if (domains.contains(host)) return true
        return domains.any { host.endsWith(".$it") }
    }
}
