package ke.nyavu.shusha

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject

/**
 * The product, on a phone: detector, bulk, history and model, the same four screens the site
 * has, in the same order and the same voice.
 *
 * Built with plain Android views deliberately. The app is small, the screens are layouts of
 * text and rules rather than long dynamic lists, and a framework would add a dependency
 * without adding behaviour.
 */
class MainActivity : Activity() {

    private companion object {
        const val REQ_CSV = 41
    }

    private lateinit var body: FrameLayout
    private lateinit var navBar: LinearLayout
    private lateinit var accountLabel: TextView
    private val tabs = listOf("Detector", "Bulk", "History", "Model")

    private val samples = listOf(
        "safaricom.co.ke",
        "safaricom-secure-login.tk",
        "mpesa.co.ke.verify-account.top",
    )

    private fun dp(v: Int) = NyavuTheme.dp(this, v)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = NyavuTheme.BG
        window.navigationBarColor = NyavuTheme.BG

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(NyavuTheme.BG)
        }

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(20), dp(18), dp(20), dp(10))
        }
        header.addView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(TextView(this@MainActivity).apply {
                text = "Nyavu"
                textSize = 24f
                setTextColor(NyavuTheme.ink)
                typeface = NyavuTheme.serif(bold = true)
            })
            addView(TextView(this@MainActivity).apply {
                text = "Your personal link inspector"
                textSize = 12f
                setTextColor(NyavuTheme.faint)
            })
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))

        accountLabel = TextView(this).apply {
            textSize = 11.5f
            setTextColor(NyavuTheme.muted)
            setPadding(dp(12), dp(8), dp(12), dp(8))
            background = NyavuTheme.pill(this@MainActivity, 0x0DFFFFFF, 0x1FFFFFFF)
        }
        header.addView(accountLabel)
        root.addView(header)

        body = FrameLayout(this)
        root.addView(body, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))

        navBar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dp(10), dp(6), dp(10), dp(12))
        }
        tabs.forEachIndexed { index, label ->
            navBar.addView(TextView(this).apply {
                text = label
                textSize = 12f
                gravity = Gravity.CENTER
                setPadding(0, dp(10), 0, dp(10))
                setOnClickListener { select(index) }
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            })
        }
        root.addView(navBar)

        setContentView(root)
        select(0)
        refreshAccount()
    }

    private fun select(index: Int) {
        (0 until navBar.childCount).forEach { i ->
            val view = navBar.getChildAt(i) as TextView
            view.setTextColor(if (i == index) NyavuTheme.BONE else NyavuTheme.faint)
            view.typeface = if (i == index)
                android.graphics.Typeface.DEFAULT_BOLD else android.graphics.Typeface.DEFAULT
        }
        body.removeAllViews()
        val incoming = when (index) {
            0 -> detectorScreen()
            1 -> bulkScreen()
            2 -> historyScreen()
            else -> modelScreen()
        }
        incoming.alpha = 0f
        incoming.translationY = dp(10).toFloat()
        body.addView(incoming)
        incoming.animate().alpha(1f).translationY(0f)
            .setDuration(230)
            .setInterpolator(android.view.animation.DecelerateInterpolator())
            .start()
    }

    private fun page(): Pair<ScrollView, LinearLayout> {
        val scroll = ScrollView(this)
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(8), dp(20), dp(24))
        }
        scroll.addView(column)
        return scroll to column
    }

    // ---------------------------------------------------------------- detector

    private fun detectorScreen(): View {
        val (scroll, column) = page()
        val field = EditText(this).apply {
            hint = "Paste a link"
            setHintTextColor(NyavuTheme.faint)
            setTextColor(NyavuTheme.ink)
            textSize = 15f
            setSingleLine()
            inputType = InputType.TYPE_TEXT_VARIATION_URI
            background = FieldStyle.field(this@MainActivity)
            setPadding(dp(16), dp(13), dp(16), dp(13))
        }
        column.addView(field, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT))

        val analyse = Button(this).apply {
            text = "Analyse"
            isAllCaps = false
            textSize = 15f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setTextColor(NyavuTheme.ON_BONE)
            background = NyavuTheme.pill(this@MainActivity, NyavuTheme.BONE, NyavuTheme.BONE, 26)
        }
        column.addView(analyse, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(50)).apply { topMargin = dp(10) })

        val status = TextView(this).apply {
            textSize = 12f
            setTextColor(NyavuTheme.faint)
            setPadding(0, dp(10), 0, dp(4))
        }
        column.addView(status)

        column.addView(NyavuTheme.label(this, "Or try one"))
        val chips = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        samples.forEach { sample ->
            chips.addView(TextView(this).apply {
                text = sample
                textSize = 13f
                setTextColor(NyavuTheme.muted)
                typeface = NyavuTheme.mono()
                setPadding(0, dp(9), 0, dp(9))
                setOnClickListener {
                    field.setText(sample)
                    analyse.performClick()
                }
            })
        }
        column.addView(chips)

        column.addView(NyavuTheme.label(this, "What it does"))
        column.addView(TextView(this).apply {
            text = "Nyavu reads the address, not the page. Nothing is fetched and nothing is " +
                "stored about you, so there is nothing for a bad link to exploit."
            textSize = 12.5f
            setTextColor(NyavuTheme.faint)
            setLineSpacing(dp(3).toFloat(), 1.1f)
        })

        pressable(analyse)
        analyse.setOnClickListener {
            val link = field.text.toString().trim()
            if (link.isEmpty()) {
                field.error = "Paste a link first"
                return@setOnClickListener
            }
            analyse.isEnabled = false
            val frames = listOf("Reading the address", "Reading the address.", "Reading the address..",
                "Reading the address...")
            var frame = 0
            val ticker = object : Runnable {
                override fun run() {
                    status.text = frames[frame % frames.size]
                    frame++
                    status.postDelayed(this, 320)
                }
            }
            status.post(ticker)
            status.tag = ticker
            Thread {
                val res = runCatching { Api.predict(this, link) }.getOrNull()
                runOnUiThread {
                    (status.tag as? Runnable)?.let { status.removeCallbacks(it) }
                    status.tag = null
                    analyse.isEnabled = true
                    when {
                        res == null -> status.text = "Nyavu could not be reached. Check your connection."
                        !res.ok -> status.text = errorMessage(res.body)
                        else -> {
                            status.text = ""
                            VerdictDialog(this, res.json()) { openLink(it) }.show()
                            refreshAccount()
                        }
                    }
                }
            }.start()
        }
        return scroll
    }

    // -------------------------------------------------------------------- bulk

    private fun bulkScreen(): View {
        val (scroll, column) = page()
        column.addView(TextView(this).apply {
            text = "Paste one address per line. Up to two hundred at a time."
            textSize = 12.5f
            setTextColor(NyavuTheme.faint)
            setLineSpacing(dp(3).toFloat(), 1.1f)
        })

        val field = EditText(this).apply {
            hint = "example.co.ke\nlogin.example.top"
            setHintTextColor(NyavuTheme.faint)
            setTextColor(NyavuTheme.ink)
            textSize = 13f
            typeface = NyavuTheme.mono()
            minLines = 5
            gravity = Gravity.TOP
            background = FieldStyle.field(this@MainActivity)
            setPadding(dp(14), dp(12), dp(14), dp(12))
        }
        column.addView(field, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(170)).apply { topMargin = dp(12) })

        val pick = TextView(this).apply {
            text = "or choose a CSV from this device"
            textSize = 12f
            setTextColor(NyavuTheme.muted)
            setPadding(0, dp(10), 0, dp(2))
            setOnClickListener { pickCsv(field) }
        }
        column.addView(pick)

        val run = Button(this).apply {
            text = "Screen the list"
            isAllCaps = false
            textSize = 14f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setTextColor(NyavuTheme.ON_BONE)
            background = NyavuTheme.pill(this@MainActivity, NyavuTheme.BONE, NyavuTheme.BONE, 26)
        }
        column.addView(run, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(48)).apply { topMargin = dp(10) })

        val results = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        column.addView(results)

        pressable(run)
        run.setOnClickListener {
            val urls = field.text.toString().split("\n").map { it.trim() }.filter { it.isNotEmpty() }
            if (urls.isEmpty()) {
                field.error = "Paste at least one address"
                return@setOnClickListener
            }
            run.isEnabled = false
            results.removeAllViews()
            results.addView(TextView(this).apply {
                text = "Screening ${urls.size} addresses"
                textSize = 12f
                setTextColor(NyavuTheme.faint)
            })
            Thread {
                val res = runCatching { Api.bulk(this, urls) }.getOrNull()
                runOnUiThread {
                    run.isEnabled = true
                    results.removeAllViews()
                    if (res == null || !res.ok) {
                        results.addView(TextView(this).apply {
                            text = if (res == null) "Nyavu could not be reached."
                            else errorMessage(res.body)
                            textSize = 12f
                            setTextColor(NyavuTheme.WARN)
                            setPadding(0, dp(10), 0, 0)
                        })
                        return@runOnUiThread
                    }
                    val data = res.json()
                    results.addView(TextView(this).apply {
                        text = "${data.optInt("count")} screened, ${data.optInt("flagged")} flagged"
                        textSize = 12f
                        setTextColor(NyavuTheme.muted)
                        setPadding(0, dp(12), 0, dp(8))
                    })
                    val items = data.optJSONArray("results") ?: return@runOnUiThread
                    for (i in 0 until items.length()) {
                        val item = items.getJSONObject(i)
                        val row = LinearLayout(this).apply {
                            orientation = LinearLayout.HORIZONTAL
                            setPadding(0, dp(9), 0, dp(9))
                        }
                        row.addView(TextView(this).apply {
                            text = item.optString("host")
                            textSize = 13f
                            typeface = NyavuTheme.mono()
                            setTextColor(NyavuTheme.ink)
                            layoutParams = LinearLayout.LayoutParams(
                                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                        })
                        row.addView(TextView(this).apply {
                            text = item.optString("verdict", "error")
                            textSize = 13f
                            typeface = NyavuTheme.serif()
                            setTextColor(NyavuTheme.toneFor(item.optString("risk")))
                            setPadding(dp(8), 0, dp(8), 0)
                        })
                        row.addView(TextView(this).apply {
                            text = if (item.has("probability") && !item.isNull("probability"))
                                Math.round(item.optDouble("probability") * 100).toString()
                            else "not scored"
                            textSize = 12f
                            typeface = NyavuTheme.mono()
                            setTextColor(NyavuTheme.faint)
                        })
                        results.addView(row)
                        results.addView(View(this).apply { setBackgroundColor(0x0DFFFFFF) },
                            LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 1))
                    }
                }
            }.start()
        }
        return scroll
    }

    // ----------------------------------------------------------------- history

    /** Choose a CSV and put its lines into the field, so the same button screens it. */
    private fun pickCsv(field: EditText) {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("text/*", "text/csv", "application/csv",
                "application/vnd.ms-excel", "text/comma-separated-values"))
        }
        fileResult = field
        startActivityForResult(intent, REQ_CSV)
    }

    private var fileResult: EditText? = null

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_CSV || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        val target = fileResult ?: return
        Thread {
            val text = runCatching {
                contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() }
            }.getOrNull()
            runOnUiThread {
                if (text == null) {
                    target.error = "Could not read that file."
                    return@runOnUiThread
                }
                val lines = text.split("\n").map { it.trim() }.filter { it.isNotEmpty() }
                // a header row is not an address
                val cleaned = lines.filterIndexed { i, line ->
                    !(i == 0 && line.lowercase().trim('"') == "url")
                }
                target.setText(cleaned.joinToString("\n"))
            }
        }.start()
    }

    private fun historyScreen(): View {
        val (scroll, column) = page()
        column.addView(TextView(this).apply {
            text = "Your most recent checks. Signing in keeps them; a visitor without an " +
                "account keeps them on this device's session only."
            textSize = 12.5f
            setTextColor(NyavuTheme.faint)
            setLineSpacing(dp(3).toFloat(), 1.1f)
        })
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        column.addView(list)

        list.addView(TextView(this).apply {
            text = "Loading"
            textSize = 12f
            setTextColor(NyavuTheme.faint)
            setPadding(0, dp(12), 0, 0)
        })
        Thread {
            val res = runCatching { Api.history(this) }.getOrNull()
            runOnUiThread {
                list.removeAllViews()
                if (res == null || !res.ok) {
                    list.addView(TextView(this).apply {
                        text = "Could not load history."
                        textSize = 12f
                        setTextColor(NyavuTheme.WARN)
                        setPadding(0, dp(12), 0, 0)
                    })
                    return@runOnUiThread
                }
                val payload = runCatching { res.json() }.getOrNull()
                val items = payload?.optJSONArray("items")
                if (items == null || items.length() == 0) {
                    val note = payload?.optString("note").orEmpty()
                    list.addView(TextView(this).apply {
                        text = note.ifEmpty {
                            "Nothing caught yet. Check a link and it will appear here."
                        }
                        textSize = 12.5f
                        setTextColor(NyavuTheme.faint)
                        setLineSpacing(dp(3).toFloat(), 1.1f)
                        setPadding(0, dp(16), 0, 0)
                    })
                    return@runOnUiThread
                }
                for (i in 0 until items.length()) {
                    val item = items.getJSONObject(i)
                    val row = LinearLayout(this).apply {
                        orientation = LinearLayout.HORIZONTAL
                        setPadding(0, dp(10), 0, dp(10))
                    }
                    row.addView(TextView(this).apply {
                        text = item.optString("host")
                        textSize = 13f
                        typeface = NyavuTheme.mono()
                        setTextColor(NyavuTheme.ink)
                        layoutParams = LinearLayout.LayoutParams(
                            0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                    })
                    row.addView(TextView(this).apply {
                        text = item.optString("verdict")
                        textSize = 13f
                        typeface = NyavuTheme.serif()
                        setTextColor(NyavuTheme.toneFor(item.optString("risk")))
                        setPadding(dp(8), 0, dp(8), 0)
                    })
                    list.addView(row)
                    list.addView(View(this).apply { setBackgroundColor(0x0DFFFFFF) },
                        LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 1))
                }
            }
        }.start()
        return scroll
    }

    // ------------------------------------------------------------------- model

    private fun modelScreen(): View {
        val (scroll, column) = page()
        column.addView(NyavuTheme.label(this, "Classifiers compared"))
        val table = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        column.addView(table)
        table.addView(TextView(this).apply {
            text = "Loading"
            textSize = 12f
            setTextColor(NyavuTheme.faint)
        })

        Thread {
            val res = runCatching { Api.model(this) }.getOrNull()
            runOnUiThread {
                table.removeAllViews()
                if (res == null || !res.ok) {
                    table.addView(TextView(this).apply {
                        text = "Could not load the model report."
                        textSize = 12f
                        setTextColor(NyavuTheme.WARN)
                    })
                    return@runOnUiThread
                }
                val data = runCatching { res.json() }.getOrNull() ?: return@runOnUiThread
                val comparison = data.optJSONObject("comparison")
                val deployed = data.optString("model", "")
                if (comparison != null) {
                    val names = comparison.keys()
                    while (names.hasNext()) {
                        val name = names.next()
                        val row = comparison.getJSONObject(name)
                        val line = LinearLayout(this).apply {
                            orientation = LinearLayout.HORIZONTAL
                            setPadding(0, dp(9), 0, dp(9))
                        }
                        line.addView(TextView(this).apply {
                            text = name + if (name == deployed) "  deployed" else ""
                            textSize = 12.5f
                            setTextColor(if (name == deployed) NyavuTheme.ACCENT else NyavuTheme.muted)
                            layoutParams = LinearLayout.LayoutParams(
                                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
                        })
                        line.addView(TextView(this).apply {
                            text = String.format("%.1f%%", row.optDouble("accuracy") * 100)
                            textSize = 12.5f
                            typeface = NyavuTheme.mono()
                            setTextColor(NyavuTheme.ink)
                        })
                        table.addView(line)
                        table.addView(View(this).apply { setBackgroundColor(0x0DFFFFFF) },
                            LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 1))
                    }
                }

                column.addView(NyavuTheme.label(this, "What the measurements say"))
                column.addView(TextView(this).apply {
                    text = "On 3,573 held-out addresses the deployed model is right about 75 times " +
                        "in a hundred, with a false positive rate of 19.8 per cent. A verdict is " +
                        "an assessment, not a guarantee of safety."
                    textSize = 12.5f
                    setTextColor(NyavuTheme.faint)
                    setLineSpacing(dp(3).toFloat(), 1.1f)
                })
            }
        }.start()
        return scroll
    }

    // ------------------------------------------------------------------ shared

    /** A small dip under the finger, so a button feels pressed rather than merely tapped. */
    private fun pressable(view: View) {
        view.setOnTouchListener { v, event ->
            when (event.action) {
                android.view.MotionEvent.ACTION_DOWN ->
                    v.animate().scaleX(0.97f).scaleY(0.97f).setDuration(90).start()
                android.view.MotionEvent.ACTION_UP,
                android.view.MotionEvent.ACTION_CANCEL ->
                    v.animate().scaleX(1f).scaleY(1f).setDuration(120).start()
            }
            false
        }
    }

    private fun refreshAccount() {
        Thread {
            val res = runCatching { Api.me(this) }.getOrNull()
            runOnUiThread {
                val me = res?.takeIf { it.ok }?.let { runCatching { it.json() }.getOrNull() }
                val signedIn = me?.optBoolean("authenticated") == true
                accountLabel.text = if (signedIn) {
                    me?.optString("full_name")?.ifEmpty { me?.optString("email") } ?: "Account"
                } else "Sign in"
                accountLabel.setOnClickListener {
                    if (signedIn) {
                        Thread {
                            Api.logout(this)
                            runOnUiThread { refreshAccount() }
                        }.start()
                    } else {
                        openLink(NyavuApi.base(this).trimEnd('/') + "/#history")
                    }
                }
            }
        }.start()
    }

    private fun errorMessage(body: String): String =
        runCatching { JSONObject(body).optString("detail") }.getOrNull()
            ?.takeIf { it.isNotEmpty() } ?: "That did not work. Try again."

    private fun openLink(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (e: ActivityNotFoundException) {
            // no browser installed
        }
    }
}

/** The field style, kept in one place so it cannot drift between screens. */
object FieldStyle {
    fun field(context: android.content.Context): android.graphics.drawable.GradientDrawable =
        android.graphics.drawable.GradientDrawable().apply {
            setColor(NyavuTheme.FIELD)
            cornerRadius = NyavuTheme.dp(context, 14).toFloat()
            setStroke(NyavuTheme.dp(context, 1), 0x1FFFFFFF)
        }
}
