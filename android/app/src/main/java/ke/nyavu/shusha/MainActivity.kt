package ke.nyavu.shusha

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.VpnService
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * Home screen.
 *
 * One page, three things in order of importance: what Nyavu is doing for you right
 * now, the action you came for, and the controls that change its behaviour. The
 * service address sits at the bottom because it is configuration, not a feature.
 */
class MainActivity : Activity() {

    private lateinit var status: TextView
    private lateinit var orb: TextView
    private lateinit var orbLabel: TextView
    private lateinit var filterButton: Button

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun panel(fill: Int = 0xFF0A1018.toInt()): GradientDrawable =
        GradientDrawable().apply {
            setColor(fill)
            cornerRadius = dp(20).toFloat()
            setStroke(dp(1), 0xFF1B2430.toInt())
        }

    private fun pill(fill: Int): GradientDrawable = GradientDrawable().apply {
        setColor(fill)
        cornerRadius = dp(28).toFloat()
    }

    private fun outline(): GradientDrawable = GradientDrawable().apply {
        setColor(Color.TRANSPARENT)
        cornerRadius = dp(28).toFloat()
        setStroke(dp(1), 0xFF2A3546.toInt())
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.statusBarColor = 0xFF04060B.toInt()
        window.navigationBarColor = 0xFF04060B.toInt()

        val scroll = ScrollView(this).apply { setBackgroundColor(0xFF04060B.toInt()) }
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(34), dp(22), dp(40))
        }
        scroll.addView(page)

        /* ---------------------------------------------------------- identity */
        val brand = TextView(this).apply {
            text = "Nyavu"
            textSize = 30f
            setTextColor(0xFFEEF2FA.toInt())
            typeface = Typeface.DEFAULT_BOLD
        }
        val tagline = TextView(this).apply {
            text = "Your personal link inspector"
            textSize = 13.5f
            setTextColor(0xFF6E7A90.toInt())
            setPadding(0, dp(4), 0, dp(24))
        }
        page.addView(brand)
        page.addView(tagline)

        /* ------------------------------------------------------------- state */
        val heroCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            background = panel()
            setPadding(0, dp(26), 0, dp(26))
        }

        orb = TextView(this).apply {
            text = "\uD83D\uDEE1"
            textSize = 34f
            gravity = Gravity.CENTER
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(0xFF0C1A1A.toInt())
                setStroke(dp(2), 0xFF2E7D6B.toInt())
            }
        }
        heroCard.addView(orb, LinearLayout.LayoutParams(dp(108), dp(108)))

        orbLabel = TextView(this).apply {
            text = "Ready"
            textSize = 19f
            setTextColor(0xFFEEF2FA.toInt())
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            setPadding(0, dp(16), 0, dp(2))
        }
        heroCard.addView(orbLabel)

        val orbHint = TextView(this).apply {
            text = "Nothing to report. Inspect a link to begin."
            textSize = 12.5f
            setTextColor(0xFF6E7A90.toInt())
            gravity = Gravity.CENTER
            setPadding(dp(20), 0, dp(20), 0)
        }
        heroCard.addView(orbHint)

        page.addView(heroCard, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = dp(18) })

        /* ------------------------------------------------------------- action */
        val actionCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = panel()
            setPadding(dp(18), dp(20), dp(18), dp(20))
        }

        val actionLabel = TextView(this).apply {
            text = "INSPECT A LINK"
            textSize = 10.5f
            setTextColor(0xFF5B667D.toInt())
            letterSpacing = 0.18f
            typeface = Typeface.DEFAULT_BOLD
        }
        actionCard.addView(actionLabel)

        val urlField = EditText(this).apply {
            hint = "Paste a link"
            setHintTextColor(0xFF4E5A70.toInt())
            setTextColor(0xFFEEF2FA.toInt())
            textSize = 14.5f
            setSingleLine()
            inputType = InputType.TYPE_TEXT_VARIATION_URI
            background = GradientDrawable().apply {
                setColor(0xFF111823.toInt())
                cornerRadius = dp(14).toFloat()
                setStroke(dp(1), 0xFF1E2836.toInt())
            }
            setPadding(dp(14), dp(12), dp(14), dp(12))
        }
        actionCard.addView(urlField, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = dp(10) })

        val inspect = Button(this).apply {
            text = "Inspect link"
            textSize = 15f
            isAllCaps = false
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(0xFF032620.toInt())
            background = pill(0xFF43E8C8.toInt())
            setOnClickListener {
                val link = urlField.text.toString().trim()
                if (link.isNotEmpty()) {
                    startActivity(Intent(this@MainActivity, LinkGateActivity::class.java).apply {
                        action = Intent.ACTION_SEND
                        type = "text/plain"
                        putExtra(Intent.EXTRA_TEXT, link)
                    })
                } else {
                    urlField.error = "Paste a link first"
                }
            }
        }
        actionCard.addView(inspect, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(52)
        ).apply { topMargin = dp(14) })

        page.addView(actionCard, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = dp(14) })

        /* --------------------------------------------------------- protection */
        val protectCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = panel()
            setPadding(dp(18), dp(18), dp(18), dp(18))
        }

        status = TextView(this).apply {
            text = ""
            textSize = 13.5f
            setTextColor(0xFF939FB5.toInt())
            setLineSpacing(dp(2).toFloat(), 1f)
        }
        protectCard.addView(status)

        filterButton = Button(this).apply {
            text = "Start DNS filtering"
            textSize = 14f
            isAllCaps = false
            setTextColor(0xFFB9C6DD.toInt())
            background = outline()
            setOnClickListener { requestVpn() }
        }
        protectCard.addView(filterButton, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(46)
        ).apply { topMargin = dp(14) })

        val stop = Button(this).apply {
            text = "Stop filtering"
            textSize = 13f
            isAllCaps = false
            setTextColor(0xFF6E7A90.toInt())
            background = null
            setOnClickListener {
                stopService(Intent(this@MainActivity, NyavuVpnService::class.java))
                refresh()
            }
        }
        protectCard.addView(stop, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(40)
        ).apply { topMargin = dp(2) })

        page.addView(protectCard, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { bottomMargin = dp(14) })

        /* ------------------------------------------------------------ service */
        val configCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = panel(0xFF080D14.toInt())
            setPadding(dp(18), dp(16), dp(18), dp(16))
        }
        val configLabel = TextView(this).apply {
            text = "SERVICE ADDRESS"
            textSize = 10f
            setTextColor(0xFF4E5A70.toInt())
            letterSpacing = 0.18f
            typeface = Typeface.DEFAULT_BOLD
        }
        configCard.addView(configLabel)

        val apiField = EditText(this).apply {
            setText(NyavuApi.base(this@MainActivity))
            textSize = 12.5f
            setTextColor(0xFF939FB5.toInt())
            setSingleLine()
            inputType = InputType.TYPE_TEXT_VARIATION_URI
        }
        configCard.addView(apiField, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = dp(6) })

        val saveApi = Button(this).apply {
            text = "Save address"
            textSize = 12.5f
            isAllCaps = false
            setTextColor(0xFF43E8C8.toInt())
            background = null
            setOnClickListener {
                val value = apiField.text.toString().trim().trimEnd('/')
                getSharedPreferences("nyavu", MODE_PRIVATE).edit()
                    .putString("apiBase", value).apply()
                status.text = "Saved. Links will be checked against $value"
            }
        }
        configCard.addView(saveApi)

        page.addView(configCard)

        val footNote = TextView(this).apply {
            text = "Nyavu reads the address, never the page. Nothing you inspect is sent " +
                   "to the site itself, and no notification access is requested."
            textSize = 11.5f
            setTextColor(0xFF4E5A70.toInt())
            setLineSpacing(dp(2).toFloat(), 1f)
            setPadding(0, dp(18), 0, 0)
        }
        page.addView(footNote)

        setContentView(scroll)
        refresh()
    }

    /** Reflects the filter state without pretending it is more than it is. */
    private fun refresh() {
        val on = NyavuVpnService.running
        status.text = if (on) {
            "DNS filter is on. Known phishing and advertising domains are blocked for " +
            "every app on this device. It does not inspect pages, and it cannot catch a " +
            "site that is not already on the list."
        } else {
            "DNS filter is off. Only links you send to Nyavu are inspected. If another " +
            "VPN is active, Android allows just one \u2014 turn the other off first."
        }
        orbLabel.text = if (on) "Protection on" else "Ready"
        orb.background = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(if (on) 0xFF0B1F1A.toInt() else 0xFF0C1A1A.toInt())
            setStroke(dp(2), if (on) 0xFF35E0A0.toInt() else 0xFF2E7D6B.toInt())
        }
        filterButton.text = if (on) "Restart filtering" else "Start DNS filtering"
    }

    private fun requestVpn() {
        val intent = VpnService.prepare(this)
        if (intent != null) {
            startActivityForResult(intent, REQ_VPN)
        } else {
            startService(Intent(this, NyavuVpnService::class.java))
            status.postDelayed({ refresh() }, 600)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_VPN && resultCode == RESULT_OK) {
            startService(Intent(this, NyavuVpnService::class.java))
            status.postDelayed({ refresh() }, 600)
        }
    }

    override fun onResume() {
        super.onResume()
        if (::status.isInitialized) refresh()
    }

    companion object {
        private const val REQ_VPN = 41
    }
}
