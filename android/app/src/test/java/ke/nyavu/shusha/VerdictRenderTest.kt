package ke.nyavu.shusha

import android.graphics.Bitmap
import android.graphics.Canvas
import android.view.View
import org.json.JSONObject
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import org.robolectric.shadows.ShadowLooper
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * Render the verdict, from real responses.
 *
 * The fixtures are the service's own answers, captured from /api/predict for one phishing
 * address, one ordinary one and one in between. The dialog is the screen nobody had seen, and
 * drawing it is the only way to notice that a label collides, a bar is invisible or the
 * examination leaves the text half written.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [30], qualifiers = "w393dp-h852dp-xhdpi")
class VerdictRenderTest {

    private val out = File("build/screenshots").apply { mkdirs() }

    private fun fixture(name: String): JSONObject {
        val text = javaClass.classLoader!!.getResourceAsStream("verdict-$name.json")!!
            .bufferedReader().use { it.readText() }
        return JSONObject(text)
    }

    private fun captureDialog(name: String, json: JSONObject) {
        val activity = Robolectric.buildActivity(MainActivity::class.java).setup().get()
        val dialog = VerdictDialog(activity, json) { }.show()

        // let the examination finish: it types every character, then reveals the notes
        ShadowLooper.shadowMainLooper().idleFor(12, TimeUnit.SECONDS)

        val decor: View = dialog.window!!.decorView
        val width = 786
        val height = 1704
        decor.measure(
            View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY)
        )
        decor.layout(0, 0, width, height)
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        decor.draw(Canvas(bitmap))
        File(out, "$name.png").outputStream().use {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
        dialog.dismiss()
    }

    @Test
    fun phishingVerdict() = captureDialog("05-verdict-phishing", fixture("phishing"))

    @Test
    fun legitimateVerdict() = captureDialog("06-verdict-legitimate", fixture("legitimate"))

    @Test
    fun suspiciousVerdict() = captureDialog("07-verdict-suspicious", fixture("suspicious"))
}
