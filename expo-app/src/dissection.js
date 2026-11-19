/**
 * The address split into the pieces a person is being taught to read.
 *
 * Same lesson as the site, and a name has three parts rather than two: subdomains, the
 * registrable name, and the ending. The Kotlin version got this wrong at first and told
 * readers that "www" was the name; keeping the logic here, once, is the other reason to
 * write the client in JavaScript.
 */

const CHEAP_ENDINGS = new Set([
  "tk", "top", "xyz", "buzz", "click", "link", "zip", "mov", "country", "gq", "ml", "cf",
]);

const TWO_LABEL_SUFFIXES = new Set([
  "co.ke", "me.ke", "info.ke", "mobi.ke", "co.ug", "co.tz", "co.za",
  "com.au", "co.uk", "org.uk", "ac.ke",
]);

export function dissect(raw) {
  const parts = [];
  const text = String(raw || "").trim();
  const schemeEnd = text.indexOf("://");
  const scheme = schemeEnd > 0 ? text.slice(0, schemeEnd).toLowerCase() : "";
  let rest = schemeEnd > 0 ? text.slice(schemeEnd + 3) : text;

  const cut = rest.search(/[/?#]/);
  const host = (cut >= 0 ? rest.slice(0, cut) : rest).toLowerCase();
  rest = cut >= 0 ? rest.slice(cut) : "";

  if (scheme) {
    parts.push({
      text: `${scheme}://`,
      role: "scheme",
      wrong: scheme !== "https",
      note: scheme === "https"
        ? "encrypted, a tampered page cannot pass for this one"
        : "no HTTPS: nothing here is encrypted",
    });
  }

  const labels = host.split(".").filter(Boolean);
  if (!labels.length) return parts;

  const twoLabel = labels.length >= 3 &&
    TWO_LABEL_SUFFIXES.has(labels.slice(-2).join(".").toLowerCase());
  const suffixCount = twoLabel ? 2 : 1;
  const suffixStart = labels.length - suffixCount;
  const beforeSuffix = labels.slice(0, suffixStart);

  const registrable = beforeSuffix[beforeSuffix.length - 1] || "";
  const subdomains = beforeSuffix.slice(0, -1);

  if (subdomains.length) {
    parts.push({
      text: `${subdomains.join(".")}.`,
      role: "subdomain",
      wrong: false,
      note: "a subdomain: anyone can put a word in front of a name",
    });
  }
  if (registrable) {
    parts.push({
      text: registrable,
      role: "name",
      wrong: false,
      note: `"${registrable}" is the name this address is registered under`,
    });
  }
  if (suffixStart < labels.length) {
    const suffix = labels.slice(suffixStart).join(".");
    const ending = suffix.split(".").pop();
    const cheap = CHEAP_ENDINGS.has(ending);
    parts.push({
      text: `.${suffix}`,
      role: "ending",
      wrong: cheap,
      note: cheap
        ? `.${ending}: cheap and abused`
        : `.${suffix}: the ending, where the name is registered`,
    });
  }
  if (rest && rest !== "/") {
    const path = rest.split("?")[0];
    if (path && path !== "/") {
      parts.push({ text: path, role: "path", wrong: false, note: "the path, cosmetic" });
    }
  }
  return parts;
}

export const readingNote = (parts) =>
  parts.length >= 3
    ? "Read it from the right. The name before the ending is the one somebody bought."
    : "Read the address from the right.";
