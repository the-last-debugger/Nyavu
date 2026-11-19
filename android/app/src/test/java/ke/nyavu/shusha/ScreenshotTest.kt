package ke.nyavu.shusha

import android.graphics.Bitmap
import android.graphics.Canvas
import android.view.View
import androidx.test.core.app.ApplicationProvider
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * Draw the screens in the JVM and write them to disk.
 *
 * The emulator will not run in this environment: WHPX needs named pipes and software
 * emulation receives no CPU, so nothing here has ever been seen. Robolectric draws Android
 * views into a bitmap with no device, no virtualisation and no QEMU, which is enough to
 * answer the only question that matters about a layout: what does it look like.
 *
 * Run with: gradlew testDebugUnitTest --tests "*ScreenshotTest*"
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [30], qualifiers = "w393dp-h852dp-xhdpi")
class ScreenshotTest {

    private val out = File("build/screenshots").apply { mkdirs() }

    // xhdpi means two device pixels per dp, and rendering a 393dp phone at 393 pixels laid
    // the whole interface out in half the width it expects. The size here is pixels.
    private fun capture(name: String, view: View, width: Int = 786, height: Int = 1704) {
        view.measure(
            View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(height, View.MeasureSpec.EXACTLY)
        )
        view.layout(0, 0, width, height)
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        view.draw(canvas)
        File(out, "$name.png").outputStream().use {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
    }

    @Test
    fun mainActivityRenders() {
        val controller = Robolectric.buildActivity(MainActivity::class.java).setup()
        val activity = controller.get()
        capture("01-detector", activity.window.decorView)

        // the other three screens, by asking the activity to switch, which is what a tap does
        val select = MainActivity::class.java.getDeclaredMethod("select", Int::class.javaPrimitiveType)
        select.isAccessible = true
        listOf(1 to "02-bulk", 2 to "03-history", 3 to "04-model").forEach { (index, name) ->
            select.invoke(activity, index)
            org.robolectric.shadows.ShadowLooper.idleMainLooper()
            capture(name, activity.window.decorView)
        }
        File(out, "ok.txt").writeText("rendered")
    }

    @Test
    fun themeValuesAreTheProduct() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val ink = NyavuTheme.ink
        check(ink == 0xFFE9E6DE.toInt()) { "ink should be the product's warm bone, was $ink" }
        check(NyavuTheme.headlineFor("high") == "This one is worth avoiding")
        check(NyavuTheme.headlineFor("low") == "This reads as ordinary")
    }
}
