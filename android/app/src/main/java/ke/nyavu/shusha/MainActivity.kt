package ke.nyavu.shusha

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * Home screen: what is protecting you, the action you came for, and the controls.
 *
 * The ring is the honest count of active protections - never a score of how safe the
 * device is, which Nyavu cannot know.
 */
class MainActivity : Activity() {

    private lateinit var ring: RingView
    private lateinit var ringLabel: TextView
    private lateinit var ringSub: TextView
    private lateinit var urlField: EditText
    private lateinit var status: TextView

    // the palette lives in NyavuTheme, so a screen cannot drift back to the old mint
    private val ink get() = NyavuTheme.ink
    private val muted get() = NyavuTheme.muted
    private val faint get() = NyavuTheme.faint
    private val accent = NyavuTheme.ACCENT
    private val safe = NyavuTheme.SAFE

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun panel(fill: Int = 0xFF0A1018.toInt(), radius: Int = 20): GradientDrawable =
        GradientDrawable().apply {
            setColor(fill)
            cornerRadius = dp(radius).toFloat()
            setStroke(dp(1), 0xFF1B2430.toInt())
        }

    private fun label(text: String): TextView = TextView(this).apply {
        this.text = text
        textSize = 9.5f
        setTextColor(faint)
        letterSpacing = 0.2f
        typeface = Typeface.DEFAULT_BOLD
        setPadding(0, dp(22), 0, dp(10))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = NyavuTheme.BG
        window.navigationBarColor = NyavuTheme.BG

        val scroll = ScrollView(this).apply { setBackgroundColor(NyavuTheme.BG) }
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(30), dp(22), dp(36))
        }
        scroll.addView(page)

        /* ------------------------------------------------------------ identity */
        page.addView(TextView(this).apply {
            text = "Nyavu"
            textSize = 28f
            setTextColor(ink)
            typeface = Typeface.DEFAULT_BOLD
        })
        page.addView(TextView(this).apply {
            text = "Your personal link inspector"
            textSize = 13f
            setTextColor(faint)
            setPadding(0, dp(3), 0, dp(20))
        })

        /* --------------------------------------------------------------- ring */
        val hero = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            background = panel()
            setPadding(0, dp(22), 0, dp(22))
        }
        ring = RingView(this)
        hero.addView(ring, LinearLayout.LayoutParams(dp(184), dp(184)))

        ringLabel = TextView(this).apply {
            textSize = 17f
            setTextColor(ink)
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            setPadding(dp(20), dp(14), dp(20), 0)
        }
        hero.addView(ringLabel)

        ringSub = TextView(this).apply {
            textSize = 12f
            setTextColor(faint)
            gravity = Gravity.CENTER
            setPadding(dp(24), dp(3), dp(24), 0)
        }
        hero.addView(ringSub)

        page.addView(hero, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = dp(14) })

        /* ------------------------------------------------------------- action */
        val actionCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = panel()
            setPadding(dp(16), dp(16), dp(16), dp(16))
        }
        actionCard.addView(TextView(this).apply {
            text = "INSPECT A LINK"
            textSize = 9.5f
            setTextColor(faint)
            letterSpacing = 0.2f
            typeface = Typeface.DEFAULT_BOLD
        })

        urlField = EditText(this).apply {
            hint = "Paste a link"
            setHintTextColor(0xFF4E5A70.toInt())
            setTextColor(ink)
            textSize = 14.5f
            setSingleLine()
            inputType = InputType.TYPE_TEXT_VARIATION_URI
            background = GradientDrawable().apply {
                setColor(0xFF111823.toInt())
                cornerRadius = dp(14).toFloat()
                setStroke(dp(1), 0xFF1E2836.toInt())
            }
            setPadding(dp(14), dp(11), dp(14), dp(11))
        }
        actionCard.addView(urlField, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = dp(9) })

        actionCard.addView(Button(this).apply {
            text = "Inspect link"
            textSize = 15f
            isAllCaps = false
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(0xFF032620.toInt())
            background = GradientDrawable().apply {
                setColor(accent)
                cornerRadius = dp(26).toFloat()
            }
            setOnClickListener { inspect() }
        }, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(50)
        ).apply { topMargin = dp(12) })

        status = TextView(this).apply {
            textSize = 11.5f
            setTextColor(faint)
            setPadding(0, dp(10), 0, 0)
        }
        actionCard.addView(status)

        page.addView(actionCard, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = dp(6) })

        /* ------------------------------------------------------- quick action */
        page.addView(label("QUICK ACTIONS"))

        val tiles = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        tiles.addView(tile("\uD83D\uDD0D", "Inspect\nlink") {
            urlField.requestFocus()
        }, LinearLayout.LayoutParams(0, dp(88), 1f).apply { rightMargin = dp(8) })
        tiles.addView(tile("\u2139", "About\nNyavu") { showAbout() },
            LinearLayout.LayoutParams(0, dp(88), 1f))
        page.addView(tiles)

        /* --------------------------------------------------------- protection */
        page.addView(label("PROTECTION"))

        page.addView(card("Link inspection", "Always on", true,
            "Every link you send to Nyavu is scored by the model and explained."),
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = dp(10) })

        page.addView(card("Share to Nyavu", "Available", true,
            "Open the share sheet on any link and choose Nyavu. No notification access " +
            "is requested."))

        /* ------------------------------------------------------------ service */
        page.addView(label("SERVICE ADDRESS"))
        val config = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = panel(0xFF080D14.toInt(), 16)
            setPadding(dp(16), dp(14), dp(16), dp(12))
        }
        val apiField = EditText(this).apply {
            setText(NyavuApi.base(this@MainActivity))
            textSize = 12f
            setTextColor(muted)
            setSingleLine()
            inputType = InputType.TYPE_TEXT_VARIATION_URI
        }
        config.addView(apiField)
        config.addView(TextView(this).apply {
            text = "Save address"
            textSize = 12f
            setTextColor(accent)
            setPadding(0, dp(6), 0, 0)
            setOnClickListener {
                val value = apiField.text.toString().trim().trimEnd('/')
                getSharedPreferences("nyavu", MODE_PRIVATE).edit()
                    .putString("apiBase", value).apply()
                status.text = "Saved. Links will be checked against $value"
            }
        })
        page.addView(config)

        page.addView(TextView(this).apply {
            text = "Nyavu reads the address, never the page. Nothing you inspect is sent to " +
                   "the site itself."
            textSize = 11f
            setTextColor(0xFF4E5A70.toInt())
            setLineSpacing(dp(2).toFloat(), 1f)
            setPadding(0, dp(16), 0, 0)
        })

        setContentView(scroll)
        refresh()
    }

    private fun tile(glyph: String, text: String, onClick: () -> Unit): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            background = panel(0xFF0A1018.toInt(), 16)
            setOnClickListener { onClick() }
            addView(TextView(this@MainActivity).apply {
                this.text = glyph
                textSize = 19f
                alpha = 0.9f
            })
            addView(TextView(this@MainActivity).apply {
                this.text = text
                textSize = 10.5f
                gravity = Gravity.CENTER
                setTextColor(0xFFC3CDDD.toInt())
                setPadding(0, dp(7), 0, 0)
            })
        }

    private fun card(title: String, state: String, on: Boolean, body: String): LinearLayout {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = panel()
            setPadding(dp(16), dp(15), dp(16), dp(14))
        }
        val head = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        head.addView(TextView(this).apply {
            text = title
            textSize = 13.5f
            setTextColor(ink)
            typeface = Typeface.DEFAULT_BOLD
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        })
        head.addView(TextView(this).apply {
            text = state.uppercase()
            textSize = 9.5f
            letterSpacing = 0.12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(if (on) safe else muted)
            setPadding(dp(9), dp(4), dp(9), dp(4))
            background = GradientDrawable().apply {
                cornerRadius = dp(20).toFloat()
                setColor(if (on) 0x1A35E0A0 else 0x0DFFFFFF)
                setStroke(dp(1), if (on) 0x7335E0A0.toInt() else 0xFF232E3D.toInt())
            }
        })
        box.addView(head)

        box.addView(View(this).apply {
            setBackgroundColor(if (on) safe else 0xFF141C27.toInt())
        }, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(3)
        ).apply { topMargin = dp(9) })

        box.addView(TextView(this).apply {
            text = body
            textSize = 11.5f
            setTextColor(faint)
            setLineSpacing(dp(2).toFloat(), 1f)
            setPadding(0, dp(9), 0, 0)
        })
        return box
    }

    private fun inspect() {
        val link = urlField.text.toString().trim()
        if (link.isEmpty()) {
            urlField.error = "Paste a link first"
            return
        }
        startActivity(Intent(this, LinkGateActivity::class.java).apply {
            action = Intent.ACTION_SEND
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, link)
        })
    }

    private fun showAbout() {
        AlertDialog.Builder(this)
            .setTitle("Nyavu")
            .setMessage(
                "A link inspector built on a logistic-regression model trained on 17,730 " +
                "addresses.\n\nIt judges the address only - it never opens the page, so the " +
                "site you check never learns you looked.\n\nOn our held-out data the model is " +
                "right about 75% of the time. Treat a verdict as one signal, not a guarantee.\n\n" +
                "Kabarak University - COMP324 team project."
            )
            .setPositiveButton("Close", null)
            .show()
    }

    /** The ring counts what is actually on, not how safe the device is. */
    private fun refresh() {
        val active = 2                              // link inspection and the share target

        ring.accent = accent
        ring.captionText = "of 2"
        ring.setProgress(active / 2f, active.toString())

        ringLabel.text = "Link inspection is on"
        ringSub.text = "Send a link here, or share one to Nyavu from any app"
    }

    override fun onResume() {
        super.onResume()
        if (::ring.isInitialized) refresh()
    }

}
