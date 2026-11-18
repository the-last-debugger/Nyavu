package ke.nyavu.shusha

import android.app.Activity
import android.app.Dialog
import android.content.Context
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.Window
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject

/**
 * The verdict, rebuilt for the app from the same parts as the site.
 *
 * A dialog rather than a page, because on a phone the verdict should land on top of what you
 * were doing and be dismissed, exactly as it behaves on the web. The order is the site's:
 * headline, address, the pieces that raised it, the number, the reasons, and the working
 * folded away until asked for.
 */
class VerdictDialog(
    private val host: Activity,
    private val payload: JSONObject,
    private val onOpenLink: (String) -> Unit,
) {

    private fun dp(v: Int) = NyavuTheme.dp(host, v)

    fun show() {
        val verdict = payload.optString("verdict")
        val risk = payload.optString("risk")
        val pct = Math.round(payload.optDouble("probability", 0.0) * 100).toInt()
        val established = payload.optString("reputation") == "established"
        val url = payload.optString("url", "")
        val colour = if (established) NyavuTheme.SAFE else NyavuTheme.toneFor(risk)

        val dialog = Dialog(host)
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE)
        dialog.window?.setBackgroundDrawable(GradientDrawable().apply {
            setColor(NyavuTheme.BG)
            setStroke(dp(1), 0x1FFFFFFF)
            cornerRadius = dp(20).toFloat()
        })

        val scroll = ScrollView(host).apply { setBackgroundColor(NyavuTheme.BG) }
        val page = LinearLayout(host).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(24), dp(22), dp(26))
        }
        scroll.addView(page)

        val head = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.TOP
        }
        val title = TextView(host).apply {
            text = if (established) "An established domain" else NyavuTheme.headlineFor(risk)
            textSize = 24f
            setTextColor(NyavuTheme.ink)
            typeface = NyavuTheme.serif()
            setLineSpacing(dp(2).toFloat(), 1.1f)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }
        head.addView(title)
        head.addView(TextView(host).apply {
            text = "Close"
            textSize = 12f
            setTextColor(NyavuTheme.faint)
            setPadding(dp(10), dp(4), dp(4), dp(4))
            setOnClickListener { dialog.dismiss() }
        })
        page.addView(head)

        page.addView(TextView(host).apply {
            text = payload.optString("host", url)
            textSize = 12.5f
            setTextColor(NyavuTheme.muted)
            typeface = NyavuTheme.mono()
            setPadding(0, dp(8), 0, dp(14))
        })

        // the pieces of the address, with the note under each
        val parts = UrlParts.dissect(url)
        val examinationRows = mutableListOf<Pair<TextView, TextView>>()
        if (parts.isNotEmpty()) {
            val box = LinearLayout(host).apply {
                orientation = LinearLayout.VERTICAL
                background = NyavuTheme.panel(host, radius = 16)
                setPadding(dp(16), dp(12), dp(16), dp(10))
            }
            parts.forEach { part ->
                val row = LinearLayout(host).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(0, dp(5), 0, dp(5))
                }
                val words = TextView(host).apply {
                    text = part.text
                    textSize = 15f
                    typeface = NyavuTheme.mono()
                    setTextColor(
                        when {
                            established -> NyavuTheme.ink
                            part.wrong -> colour
                            else -> NyavuTheme.ink
                        }
                    )
                }
                val note = TextView(host).apply {
                    text = part.note
                    textSize = 11f
                    setTextColor(NyavuTheme.faint)
                    setPadding(0, dp(3), 0, 0)
                }
                row.addView(words)
                row.addView(note)
                box.addView(row)
                examinationRows += words to note
            }
            box.addView(TextView(host).apply {
                text = UrlParts.readingNote(parts)
                textSize = 11.5f
                setTextColor(NyavuTheme.muted)
                typeface = NyavuTheme.serif()
                setPadding(0, dp(10), 0, dp(2))
            })
            page.addView(box)
        }

        // the number and its bar
        val figureRow = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.BOTTOM
            setPadding(0, dp(16), 0, 0)
        }
        figureRow.addView(TextView(host).apply {
            text = pct.toString()
            textSize = 34f
            setTextColor(colour)
            typeface = NyavuTheme.mono(bold = true)
        })
        figureRow.addView(TextView(host).apply {
            text = " risk out of 100"
            textSize = 11.5f
            setTextColor(NyavuTheme.faint)
            setPadding(dp(8), 0, 0, dp(7))
        })
        page.addView(figureRow)

        val bar = LinearLayout(host)
        val fill = View(host).apply { setBackgroundColor(colour) }
        val track = View(host).apply { setBackgroundColor(0x14FFFFFF) }
        bar.addView(fill, LinearLayout.LayoutParams(0, dp(3), pct.coerceAtLeast(1).toFloat()))
        bar.addView(track, LinearLayout.LayoutParams(0, dp(3), (100 - pct).coerceAtLeast(1).toFloat()))
        page.addView(bar)

        // what the number is, and the working behind the plus
        val noteLead = if (established) {
            "Held at $pct so a known site is never flagged on the shape of its name."
        } else {
            "Scored $pct out of 100. That is the estimated chance this address is a phish, read from its name alone."
        }
        page.addView(TextView(host).apply {
            text = noteLead
            textSize = 12.5f
            setTextColor(NyavuTheme.muted)
            setLineSpacing(dp(3).toFloat(), 1.1f)
            setPadding(0, dp(10), 0, 0)
        })

        val reasoning = TextView(host).apply {
            text = "Anything above 65 is treated as a concern, and below 35 as clear. The number " +
                "comes from a logistic-regression model trained on 17,730 addresses, whose " +
                "hold-out accuracy is 75.4 per cent."
            textSize = 12f
            setTextColor(NyavuTheme.faint)
            setLineSpacing(dp(3).toFloat(), 1.1f)
            setPadding(0, dp(10), 0, 0)
            visibility = View.GONE
        }
        val fold = TextView(host).apply {
            text = "+  How that was worked out"
            textSize = 12f
            setTextColor(NyavuTheme.faint)
            setPadding(0, dp(14), 0, 0)
            setOnClickListener {
                val open = reasoning.visibility != View.VISIBLE
                reasoning.visibility = if (open) View.VISIBLE else View.GONE
                text = if (open) "−  How that was worked out" else "+  How that was worked out"
            }
        }
        page.addView(fold)
        page.addView(reasoning)

        // the reasons
        val reasons = payload.optJSONArray("reasons")
        val count = minOf(reasons?.length() ?: 0, 4)
        page.addView(NyavuTheme.label(host, NyavuTheme.reasonTitleFor(risk)))
        if (count == 0) {
            page.addView(reasonRow("1", "Nothing in the name raised a pattern Nyavu knows."))
        } else {
            for (i in 0 until count) page.addView(reasonRow((i + 1).toString(), reasons!!.getString(i)))
        }

        // actions
        val actions = LinearLayout(host).apply { orientation = LinearLayout.VERTICAL }
        actions.setPadding(0, dp(18), 0, 0)
        if (established || risk == "low") {
            actions.addView(button("Open link", primary = true) { dialog.dismiss(); onOpenLink(url) })
        } else if (risk == "medium") {
            actions.addView(button("Open anyway", primary = false) { dialog.dismiss(); onOpenLink(url) })
        }
        actions.addView(button("Close", primary = risk == "high") { dialog.dismiss() })
        page.addView(actions)

        dialog.setContentView(scroll)
        dialog.show()

        // the examination plays on open: written, then read from the ending backwards
        val examination = Examination(host, parts, examinationRows) { }
        examination.start()
        dialog.setOnDismissListener { examination.cancel() }
    }

    private fun reasonRow(number: String, text: String): LinearLayout {
        val row = LinearLayout(host).apply {
            orientation = LinearLayout.HORIZONTAL
            background = NyavuTheme.panel(host, radius = 14)
            setPadding(dp(12), dp(12), dp(14), dp(12))
        }
        val params = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        params.bottomMargin = dp(8)
        row.layoutParams = params
        row.addView(TextView(host).apply {
            this.text = number
            textSize = 10f
            setTextColor(NyavuTheme.faint)
            typeface = NyavuTheme.mono()
            setPadding(0, dp(2), dp(12), 0)
        })
        row.addView(TextView(host).apply {
            this.text = text
            textSize = 12.5f
            setTextColor(NyavuTheme.muted)
            setLineSpacing(dp(3).toFloat(), 1.1f)
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        })
        return row
    }

    private fun button(label: String, primary: Boolean, action: () -> Unit): Button =
        Button(host).apply {
            text = label
            isAllCaps = false
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(if (primary) NyavuTheme.ON_BONE else NyavuTheme.ink)
            background = if (primary) {
                GradientDrawable().apply {
                    setColor(NyavuTheme.BONE)
                    cornerRadius = dp(26).toFloat()
                }
            } else {
                NyavuTheme.panel(host, fill = 0x0DFFFFFF, radius = 26)
            }
            setOnClickListener { action() }
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(46))
            params.bottomMargin = dp(8)
            layoutParams = params
        }
}
