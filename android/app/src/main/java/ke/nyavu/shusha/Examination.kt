package ke.nyavu.shusha

import android.app.Activity
import android.os.Handler
import android.os.Looper
import android.widget.TextView

/**
 * The examination: the address written left to right, then read from the right.
 *
 * This is the thing the website does that the app was missing. A caret types each piece, then
 * the notes arrive from the ending backwards, which is the lesson: the word before the ending
 * is the one somebody bought. It runs on the main thread with a handler because it is a short
 * sequence of state changes, not work that needs a scheduler.
 */
class Examination(
    private val activity: Activity,
    private val parts: List<UrlParts.Part>,
    private val pieces: List<Pair<TextView, TextView>>,   // text, note
    private val onDone: () -> Unit,
) {

    private val handler = Handler(Looper.getMainLooper())
    private val perCharacter = 52L
    private val afterWrite = 300L
    private val noteGap = 320L

    fun start() {
        pieces.forEach { (text, note) ->
            text.text = ""
            note.alpha = 0f
        }
        write(0, 0)
    }

    fun cancel() = handler.removeCallbacksAndMessages(null)

    /** Phase one: each piece is typed, one character at a time, at the product's pace. */
    private fun write(piece: Int, character: Int) {
        if (piece >= pieces.size) {
            handler.postDelayed({ read(pieces.size - 1) }, afterWrite)
            return
        }
        val (text, _) = pieces[piece]
        val full = parts[piece].text
        if (character <= full.length) {
            text.text = full.substring(0, character) + "|"
            handler.postDelayed({ write(piece, character + 1) }, perCharacter)
        } else {
            text.text = full
            handler.postDelayed({ write(piece + 1, 0) }, 90)
        }
    }

    /** Phase two: the notes arrive from the ending backwards. */
    private fun read(piece: Int) {
        if (piece < 0) {
            onDone()
            return
        }
        val (_, note) = pieces[piece]
        note.animate().alpha(1f).setDuration(220).start()
        handler.postDelayed({ read(piece - 1) }, noteGap)
    }
}
