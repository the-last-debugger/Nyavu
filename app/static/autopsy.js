function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/**
 * The address autopsy.
 *
 * Replaces the fishing theatre. Takes the URL apart the way the checker actually reads
 * it — scheme, labels, the registrable domain, the path — and hangs a plain-English note
 * under each piece, in the manner of explainshell.com. Segments that raised the score
 * are marked, so the animation is the explanation rather than a prelude to it.
 *
 * Everything here is type and rules, so it can be perfected: there is no drawing to get
 * almost right.
 */

const RISKY_TLDS = ["tk", "top", "xyz", "gq", "ml", "cf", "ga", "work", "click", "link"];
const KNOWN_BRANDS = ["safaricom", "mpesa", "kra", "equity", "kcb", "coop", "absa",
                      "ncba", "stanbic", "google", "facebook", "whatsapp", "paypal",
                      "netflix", "microsoft", "apple", "amazon", "instagram"];

function splitUrl(raw) {
  const url = (raw || "").trim();
  const m = url.match(/^([a-zA-Z][\w+.-]*):\/\/([^/?#]*)(.*)$/);
  const scheme = m ? m[1].toLowerCase() : "";
  const host = m ? m[2] : url.split("/")[0];
  const path = m ? m[3] : "/" + url.split("/").slice(1).join("/");

  // best effort when someone types a bare host
  const hostOnly = host.split(":")[0];
  const labels = hostOnly.toLowerCase().split(".").filter(Boolean);
  const tld = labels.length > 1 ? labels[labels.length - 1] : "";
  const name = labels.length > 1 ? labels[labels.length - 2] : (labels[0] || "");
  const subs = labels.slice(0, Math.max(0, labels.length - 2));
  return { scheme, host, hostOnly, labels, tld, name, subs, path: path || "" };
}

function autopsySegments(r) {
  const { scheme, hostOnly, labels, tld, name, subs, path } = splitUrl(r.url);
  const isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(hostOnly);
  const segs = [];

  if (scheme) {
    segs.push({
      text: scheme + "://",
      note: scheme === "https" ? "encrypted" : "no HTTPS — sent in the clear",
      flag: scheme !== "https",
      tight: true,
    });
  }

  if (isIp) {
    segs.push({
      text: hostOnly,
      note: "a bare address, not a name — nothing to check against",
      flag: true,
    });
  } else {
    subs.forEach((label) => {
      const brand = KNOWN_BRANDS.find((b) => label.includes(b));
      const hyphens = (label.match(/-/g) || []).length;
      segs.push({
        text: label + ".",
        note: brand ? `"${brand}" in a label the owner can invent` : "free to invent",
        flag: Boolean(brand) || hyphens >= 2,
        soft: true,
      });
    });

    const nameBrand = KNOWN_BRANDS.find((b) => name.includes(b));
    const nameHyphens = (name.match(/-/g) || []).length;
    segs.push({
      text: name,
      note: nameBrand ? `"${nameBrand}" where it does not belong` : "the name somebody bought",
      flag: Boolean(nameBrand) || nameHyphens >= 2,
      strong: true,
    });

    if (tld) {
      segs.push({
        text: "." + tld,
        note: RISKY_TLDS.includes(tld) ? `".${tld}" — cheap and abused` : "the ending",
        flag: RISKY_TLDS.includes(tld),
        tight: true,
      });
    }
  }

  if (path && path !== "/") {
    segs.push({
      text: path,
      note: "the path — cosmetic",
      flag: false,
      soft: true,
    });
  }

  return segs;
}

function autopsyMarkup(r) {
  const segs = autopsySegments(r);
  const items = segs.map((s, i) => {
    const cls = ["seg"];
    if (s.flag) cls.push("flag");
    if (s.soft) cls.push("soft");
    if (s.strong) cls.push("strong");
    if (s.tight) cls.push("tight");
    return `<span class="${cls.join(" ")}" style="--i:${i}">
        <span class="seg-text">${escapeHtml(s.text)}</span>
        <span class="seg-note">${escapeHtml(s.note)}</span>
      </span>`;
  });
  return `<div class="autopsy" data-flags="${segs.filter((s) => s.flag).length}">
      <div class="autopsy-line">${items.join("")}</div>
      <p class="autopsy-caption">Read it from the right. The name before the ending is the one somebody bought.</p>
    </div>`;
}
