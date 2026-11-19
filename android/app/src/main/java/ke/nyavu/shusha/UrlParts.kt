package ke.nyavu.shusha

/**
 * The address split into the pieces a person is being taught to read, with the same notes
 * the website puts under them.
 *
 * The web app dissects the address on the client, without a network call, and the app should
 * teach the same lesson the same way rather than printing one long string. This is a port of
 * that dissection: scheme, name, ending, path, each with the sentence that explains it.
 */
object UrlParts {

    private val CHEAP_ENDINGS = setOf(
        "tk", "top", "xyz", "buzz", "click", "link", "zip", "mov", "country", "gq", "ml", "cf",
    )
    private val TWO_LABEL_SUFFIXES = setOf("co.ke", "me.ke", "info.ke", "mobi.ke", "co.ug",
        "co.tz", "co.za", "com.au", "co.uk", "org.uk", "ac.ke")

    data class Part(val text: String, val note: String, val role: String, val wrong: Boolean)

    fun dissect(raw: String): List<Part> {
        val parts = mutableListOf<Part>()
        val cleaned = raw.trim()

        val schemeEnd = cleaned.indexOf("://")
        val scheme = if (schemeEnd > 0) cleaned.substring(0, schemeEnd).lowercase() else ""
        var rest = if (schemeEnd > 0) cleaned.substring(schemeEnd + 3) else cleaned

        val cut = rest.indexOfFirst { it == '/' || it == '?' || it == '#' }
        val host = if (cut >= 0) rest.substring(0, cut) else rest
        rest = if (cut >= 0) rest.substring(cut) else ""

        if (scheme.isNotEmpty()) {
            parts += Part(
                "$scheme://",
                if (scheme == "https") "encrypted, a tampered page cannot pass for this one"
                else "no HTTPS: nothing here is encrypted",
                "scheme",
                wrong = scheme != "https",
            )
        }

        val labels = host.split(".").filter { it.isNotEmpty() }
        if (labels.isEmpty()) {
            parts += Part(host.ifEmpty { raw }, "not a name at all", "name", wrong = true)
            return parts
        }

        // A name has three parts, not two: any subdomains, the registrable name, and the
        // ending. Showing "www.safaricom" as one piece and calling "www" the name was wrong
        // and taught the opposite of the lesson.
        val twoLabel = labels.size >= 3 &&
            TWO_LABEL_SUFFIXES.contains(labels.takeLast(2).joinToString(".").lowercase())
        val suffixLabels = if (twoLabel) 2 else 1
        val suffixStart = labels.size - suffixLabels
        val beforeSuffix = labels.take(suffixStart)

        val registrable = beforeSuffix.lastOrNull().orEmpty()
        val subdomains = beforeSuffix.dropLast(1)

        if (subdomains.isNotEmpty()) {
            parts += Part(
                subdomains.joinToString(".") + ".",
                "a subdomain: anyone can put a word in front of a name",
                "subdomain",
                wrong = false,
            )
        }
        if (registrable.isNotEmpty()) {
            parts += Part(
                registrable,
                "\"$registrable\" is the name this address is registered under",
                "name",
                wrong = false,
            )
        }
        if (suffixStart < labels.size) {
            val suffix = labels.drop(suffixStart).joinToString(".")
            val ending = suffix.substringAfterLast(".")
            val cheap = CHEAP_ENDINGS.contains(ending.lowercase())
            parts += Part(
                ".$suffix",
                if (cheap) ".$ending: cheap and abused"
                else ".$suffix: the ending, where the name is registered",
                "ending",
                wrong = cheap,
            )
        }
        if (rest.isNotEmpty() && rest != "/") {
            val path = rest.substringBefore('?')
            if (path.isNotEmpty() && path != "/") {
                parts += Part(path, "the path, cosmetic", "path", wrong = false)
            }
        }
        return parts
    }

    /** The lesson, in one line: the word before the ending is the one that was bought. */
    fun readingNote(parts: List<Part>): String =
        if (parts.size >= 3) "Read it from the right. The name before the ending is the one somebody bought."
        else "Read the address from the right."
}
