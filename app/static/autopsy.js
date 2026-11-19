/**
 * The address autopsy.
 *
 * Takes the URL apart the way the checker actually reads it, scheme, labels, the
 * registrable domain, the ending, the path, and hangs a plain-English note under each
 * piece, in the manner of explainshell.com.
 *
 * The notes argue whichever case the model made. A clean address is annotated with the
 * reasons it is clean; a dangerous one with the pieces that raised the score. A
 * dissection that only ever labels the bad links explains half the product.
 */

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

const RISKY_TLDS = ["tk", "top", "xyz", "gq", "ml", "cf", "ga", "work", "click", "link"];
const TRUSTED_SUFFIXES = ["co.ke", "go.ke", "or.ke", "ac.ke", "sc.ke", "ne.ke",
                          "ac.ug", "go.ug", "co.ug"];
const KNOWN_BRANDS = ["safaricom", "mpesa", "kra", "equity", "kcb", "coop", "absa",
                      "ncba", "stanbic", "google", "facebook", "whatsapp", "paypal",
                      "netflix", "microsoft", "apple", "amazon", "instagram"];

function splitUrl(raw) {
  const url = (raw || "").trim();
  const m = url.match(/^([a-zA-Z][\w+.-]*):\/\/([^/?#]*)(.*)$/);
  const scheme = m ? m[1].toLowerCase() : "";
  const host = m ? m[2] : url.split("/")[0];
  const path = m ? m[3] : "/" + url.split("/").slice(1).join("/");

  const hostOnly = host.split(":")[0];
  const labels = hostOnly.toLowerCase().split(".").filter(Boolean);

  // .co.ke and friends are two labels, not one: the registrable domain of
  // www.safaricom.co.ke is safaricom.co.ke, and getting that wrong flags the brand itself
  const two = labels.length >= 2 ? labels.slice(-2).join(".") : "";
  const three = labels.length >= 3 ? labels.slice(-3).join(".") : "";
  let suffix, name, subs;
  if (TRUSTED_SUFFIXES.includes(three) && labels.length >= 3) {
    suffix = three;
    name = labels[labels.length - 4] || "";
    subs = labels.slice(0, Math.max(0, labels.length - 4));
  } else if (TRUSTED_SUFFIXES.includes(two) && labels.length >= 2) {
    suffix = two;
    name = labels[labels.length - 3] || "";
    subs = labels.slice(0, Math.max(0, labels.length - 3));
  } else {
    suffix = labels.length >= 2 ? labels.slice(-1)[0] : hostOnly.toLowerCase();
    name = labels.length >= 2 ? labels[labels.length - 2] : (labels[0] || "");
    subs = labels.slice(0, Math.max(0, labels.length - 2));
  }

  const tld = suffix;
  return { scheme, host, hostOnly, labels, tld, name, subs, path: path || "", suffix };
}

function autopsySegments(r) {
  const { scheme, hostOnly, tld, name, subs, path, suffix } = splitUrl(r.url);
  const clean = r.risk !== "high";
  const isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(hostOnly);
  const brandInName = KNOWN_BRANDS.find((b) => name.includes(b));
  const nameHyphens = (name.match(/-/g) || []).length;
  const trustedSuffix = TRUSTED_SUFFIXES.includes(suffix);
  const segs = [];

  if (scheme) {
    const https = scheme === "https";
    segs.push({
      text: scheme + "://",
      role: "scheme",
      note: https
        ? (clean ? "encrypted, a tampered page cannot pass for this one" : "encrypted")
        : "no HTTPS: nothing here is encrypted",
      // HTTP is marked, not condemned: old and institutional sites still use it, and a
      // flagged red segment would say "phishing" where the evidence says "unencrypted"
      flag: false,
      soft: !https,
      tight: true,
    });
  }

  if (isIp) {
    segs.push({
      text: hostOnly,
      role: "address",
      note: "a bare address, not a name: nothing to check against",
      flag: true,
    });
  } else {
    subs.forEach((label) => {
      const brand = KNOWN_BRANDS.find((b) => label.includes(b));
      const hyphens = (label.match(/-/g) || []).length;
      segs.push({
        text: label + ".",
        role: "a label",
        note: brand
          ? `"${brand}" in a label the owner can invent`
          : (clean ? "a label the owner can invent, harmless on its own" : "free to invent"),
        flag: Boolean(brand) || hyphens >= 2,
        soft: true,
      });
    });

    let nameNote;
    let nameFlag = false;
    if (brandInName && !trustedSuffix) {
      nameNote = `"${brandInName}" where it does not belong`;
      nameFlag = true;
    } else if (brandInName && trustedSuffix) {
      nameNote = `"${brandInName}" on its own registry domain`;
    } else if (nameHyphens >= 2) {
      nameNote = `${nameHyphens} hyphens, a compound built to look official`;
      nameFlag = true;
    } else if (nameHyphens === 1) {
      nameNote = "one hyphen: often a sign, sometimes just a name";
    } else {
      nameNote = clean ? "no hyphens to hide behind" : "the name somebody bought";
    }
    segs.push({ text: name, role: "the name", note: nameNote, flag: nameFlag, strong: true });

    if (tld) {
      let tldNote;
      let tldFlag = false;
      if (RISKY_TLDS.includes(tld)) {
        tldNote = `".${tld}": cheap and abused`;
        tldFlag = true;
      } else if (trustedSuffix) {
        tldNote = `".${tld}", a Kenyan registry ending, not free to buy`;
      } else if (tld === "ke") {
        tldNote = `".ke", Kenya's country ending`;
      } else {
        tldNote = clean ? `".${tld}", an ordinary ending` : "the ending";
      }
      segs.push({ text: "." + tld, role: "the ending", note: tldNote, flag: tldFlag, tight: true });
    }
  }

  if (path && path !== "/") {
    segs.push({
      text: path,
      role: "the path",
      note: clean ? "the path: cosmetic, but read it anyway" : "the path, cosmetic",
      flag: false,
      soft: true,
    });
  }

  return { segs, clean, trustedSuffix, host: hostOnly };
}

function autopsyMarkup(r) {
  const { segs, clean, trustedSuffix, host } = autopsySegments(r);
  const flagged = segs.filter((s) => s.flag).length;

  /* The address stays one line and the note appears once, in a panel beneath it. The note used
     to sit under its own piece, which squeezed it into whatever width was left over: readable
     at six pieces on a wide screen, unreadable on a phone. One panel gives every note a full
     line, and the underline that used to sit beneath the note now sweeps along the address. */
  const items = segs.map((s, i) => {
    const cls = ["seg"];
    if (s.flag) cls.push("flag");
    else if (clean) cls.push("fine");
    if (s.soft) cls.push("soft");
    if (s.strong) cls.push("strong");
    if (s.tight) cls.push("tight");
    return `<span class="${cls.join(" ")}" style="--i:${i}" data-role="${escapeHtml(s.role)}"
        data-note="${escapeHtml(s.note)}">
        <span class="seg-text"><span class="seg-ink">${escapeHtml(s.text)}</span></span>
      </span>`;
  });

  let caption;
  if (flagged === 0) {
    caption = trustedSuffix
      ? `Nothing in ${escapeHtml(host)} is out of place, and the ending is registry-controlled. It still deserves the caution you would give any link.`
      : `Nothing in ${escapeHtml(host)} is out of place. That is evidence, not a guarantee.`;
  } else {
    caption = "Read it from the right. The name before the ending is the one somebody bought.";
  }

  return `<div class="autopsy ${flagged === 0 ? "clean" : "risky"}" data-flags="${flagged}">
      <div class="autopsy-head">
        <span class="autopsy-mode" data-state="idle">where the name sits</span>
      </div>
      <div class="autopsy-line">
        <span class="scan-cursor" aria-hidden="true"><span class="scan-tag"></span></span>
        <span class="autopsy-caret" aria-hidden="true"></span>
        ${items.join("")}
      </div>
      <ul class="autopsy-all">
        ${segs.map((s) => `<li><b>${escapeHtml(s.text)}</b> ${escapeHtml(s.note)}</li>`).join("")}
      </ul>
      <p class="autopsy-panel" aria-live="polite">
        <span class="panel-who"></span><span class="panel-say"></span>
      </p>
      <p class="autopsy-caption">${caption}</p>
    </div>`;
}
