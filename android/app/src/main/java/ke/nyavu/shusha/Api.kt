package ke.nyavu.shusha

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Every call to the service, in one place.
 *
 * The web app keeps a session in a cookie; the app has to do the same or history would be
 * empty and sign-in state would vanish between screens. Cookies are stored in preferences
 * because HttpURLConnection does not keep a jar of its own.
 */
object Api {

    private const val PREFS = "nyavu"
    private const val COOKIE_KEY = "cookies"

    data class Response(val code: Int, val body: String) {
        fun json(): JSONObject = JSONObject(body)
        fun array(): JSONArray = JSONArray(body)
        val ok get() = code in 200..299
    }

    private fun base(context: Context): String =
        NyavuApi.base(context).trimEnd('/')

    private fun cookies(context: Context): Map<String, String> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(COOKIE_KEY, "") ?: ""
        return raw.split("; ").mapNotNull { pair ->
            val i = pair.indexOf('=')
            if (i <= 0) null else pair.substring(0, i) to pair.substring(i + 1)
        }.toMap()
    }

    private fun storeCookies(context: Context, headers: List<String>) {
        if (headers.isEmpty()) return
        val jar = cookies(context).toMutableMap()
        headers.forEach { line ->
            val pair = line.substringBefore(';')
            val i = pair.indexOf('=')
            if (i > 0) jar[pair.substring(0, i).trim()] = pair.substring(i + 1).trim()
        }
        val joined = jar.entries.joinToString("; ") { "${it.key}=${it.value}" }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(COOKIE_KEY, joined).apply()
    }

    fun call(context: Context, path: String, method: String = "GET",
             payload: JSONObject? = null, timeoutMs: Int = 15000): Response {
        val conn = URL(base(context) + path).openConnection() as HttpURLConnection
        conn.requestMethod = method
        conn.connectTimeout = 8000
        conn.readTimeout = timeoutMs
        conn.setRequestProperty("Accept", "application/json")
        val jar = cookies(context)
        if (jar.isNotEmpty()) {
            conn.setRequestProperty("Cookie", jar.entries.joinToString("; ") { "${it.key}=${it.value}" })
        }
        if (payload != null) {
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            conn.outputStream.use { it.write(payload.toString().toByteArray()) }
        }
        val code = conn.responseCode
        storeCookies(context, conn.headerFields["Set-Cookie"] ?: emptyList())
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val body = stream?.bufferedReader()?.use { it.readText() } ?: ""
        return Response(code, body)
    }

    fun predict(context: Context, url: String): Response =
        call(context, "/api/predict", "POST", JSONObject().put("url", url))

    /** Bulk screening takes a file, not JSON: the endpoint accepts a CSV upload. */
    fun bulk(context: Context, urls: List<String>, timeoutMs: Int = 60000): Response {
        val boundary = "----nyavu" + System.nanoTime()
        val payload = urls.joinToString("\n")
        val head = (
            "--$boundary\r\n" +
            "Content-Disposition: form-data; name=\"file\"; filename=\"list.csv\"\r\n" +
            "Content-Type: text/csv\r\n\r\n"
        ).toByteArray()
        val tail = "\r\n--$boundary--\r\n".toByteArray()

        val conn = URL(base(context) + "/api/scan/bulk").openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.connectTimeout = 8000
        conn.readTimeout = timeoutMs
        conn.doOutput = true
        conn.setRequestProperty("Accept", "application/json")
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
        val jar = cookies(context)
        if (jar.isNotEmpty()) {
            conn.setRequestProperty("Cookie", jar.entries.joinToString("; ") { "${it.key}=${it.value}" })
        }
        conn.outputStream.use { out ->
            out.write(head)
            out.write(payload.toByteArray())
            out.write(tail)
        }
        val code = conn.responseCode
        storeCookies(context, conn.headerFields["Set-Cookie"] ?: emptyList())
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val body = stream?.bufferedReader()?.use { it.readText() } ?: ""
        return Response(code, body)
    }

    fun history(context: Context): Response = call(context, "/api/history?limit=25")

    fun model(context: Context): Response = call(context, "/api/model")

    fun me(context: Context): Response = call(context, "/api/auth/me")

    fun logout(context: Context): Response {
        val res = call(context, "/api/auth/logout", "POST", JSONObject())
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .remove(COOKIE_KEY).apply()
        return res
    }
}
