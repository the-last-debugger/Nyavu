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


/* What each Kenyan ending actually means. This is the honest version of "belongs to": a restricted
   namespace is a fact about who is allowed to hold a name there, and it needs no lookup. */
const SUFFIX_MEANING = {
  "ac.ke": "reserved for universities and colleges accredited in Kenya, so a phisher cannot buy one",
  "go.ke": "reserved for Kenyan government bodies",
  "or.ke": "reserved for Kenyan non-profit organisations",
  "sc.ke": "reserved for Kenyan schools",
  "ne.ke": "reserved for Kenyan network operators",
  "co.ke": "open to any registered business, so it says nothing about who owns it",
  "ac.ug": "reserved for Ugandan universities",
  "go.ug": "reserved for Ugandan government bodies",
  "co.ug": "open to any registered Ugandan business",
};

/* How a borrowed name is written when we say it back. "Kra" is not a word; "KRA" is. */
const DISPLAY_NAME = {
  mpesa: "M-Pesa", safaricom: "Safaricom", kra: "KRA", ecitizen: "eCitizen", ntsa: "NTSA",
  helb: "HELB", huduma: "Huduma Centre", equity: "Equity", kcb: "KCB", coop: "Co-operative Bank",
  absa: "Absa", ncba: "NCBA", stanbic: "Stanbic", google: "Google", facebook: "Facebook",
  whatsapp: "WhatsApp", paypal: "PayPal", netflix: "Netflix", microsoft: "Microsoft",
  apple: "Apple", amazon: "Amazon", instagram: "Instagram",
};

/* Institutions whose address we can name, because they publish it. The claim is about our list,
   not about a verification performed just now: nothing is fetched when a link is checked. */
/* The generated list is the source of truth and grows without touching this file; the entries
   below stay as a fallback for the case where the data file has not loaded. */
const KNOWN_INSTITUTIONS = Object.assign({
  "kabarak.ac.ke": "Kabarak University",
  "safaricom.co.ke": "Safaricom",
  "kra.go.ke": "the Kenya Revenue Authority",
  "equitybank.co.ke": "Equity Bank",
  "kcb.co.ke": "KCB Bank",
  "coopbank.co.ke": "the Co-operative Bank",
  "strathmore.edu": "Strathmore University",
  "uonbi.ac.ke": "the University of Nairobi",
}, (typeof window !== "undefined" && window.NYAVU_INSTITUTIONS) || {});

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
      /* An institution's own name, borrowed as a label inside somebody else's domain, is the
         clearest form of impersonation there is, and "free to invent" undersells it. */
      const institution = Object.entries(KNOWN_INSTITUTIONS)
        .find(([domain]) => domain.split(".")[0] === label);
      const hyphens = (label.match(/-/g) || []).length;
      segs.push({
        text: label + ".",
        role: "a label",
        note: institution
          ? `${institution[1]}'s own name, borrowed as a label in a domain they do not own`
          : brand
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
    /* When we can name the institution that publishes this address, say so. The claim is about
       our list, not about a lookup performed just now: nothing is fetched when a link is checked. */
    const registered = KNOWN_INSTITUTIONS[`${name}.${suffix}`];
    if (registered) {
      nameNote = clean
        ? `${registered}'s own address; it is on our list because they publish it`
        : `here it sits inside somebody else's domain, not at ${registered}`;
    }
    segs.push({ text: name, role: "the name", note: nameNote, flag: nameFlag, strong: true });

    if (tld) {
      let tldNote;
      let tldFlag = false;
      if (RISKY_TLDS.includes(tld)) {
        tldNote = `".${tld}": cheap and abused`;
        tldFlag = true;
      } else if (SUFFIX_MEANING[suffix]) {
        tldNote = `".${suffix}" is ${SUFFIX_MEANING[suffix]}`;
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


/* The complete breakdown, for the fold and for paper: every piece with its role and its note.
   The examination shows one note at a time, so this is where the whole reading survives. */
function autopsyBreakdown(r) {
  const { segs } = autopsySegments(r);
  const items = segs.map((s) => `<li>
      <span class="bd-word">${escapeHtml(s.text)}</span>
      <span class="bd-role">${escapeHtml(s.role)}</span>
      <span class="bd-note">${escapeHtml(s.note)}</span>
    </li>`).join("");
  return `<ul class="breakdown">${items}</ul>`;
}


/* What a link is probably after.
   A name cannot prove intent, but it often names it: a path that says "verify" is asking for a
   password, and a domain that borrows "mpesa" is asking for a PIN. Every goal below is inferred
   from the address and its path alone, which is why the copy says "looks" rather than "is". The
   vocabulary follows the plain-language rule: name the thing taken, not the technique. */
const INTENT_CUES = [
  { goal: "get a password or a one-time code",
    words: ["login", "log-in", "signin", "sign-in", "verify", "verification", "account",
            "update", "confirm", "auth", "password", "passwd", "otp", "unlock", "recover"] },
  { goal: "take an M-Pesa PIN or a payment",
    words: ["mpesa", "m-pesa", "paybill", "till", "wallet", "payment", "pay", "billing",
            "invoice", "refund", "deposit", "transaction"] },
  { goal: "collect identity or tax details",
    words: ["kra", "ecitizen", "ntsa", "helb", "huduma", "tax", "passport", "id-number"] },
  { goal: "take a deposit on an investment",
    words: ["invest", "crypto", "bitcoin", "forex", "profit", "trading", "earn", "bonus"] },
  { goal: "charge a fee for a parcel that is not coming",
    words: ["parcel", "delivery", "tracking", "courier", "dhl", "posta", "shipping"] },
  { goal: "collect application details for a job or a loan",
    words: ["job", "career", "vacancy", "loan", "grant", "apply", "shortlist"] },
];

function intentOf(r) {
  if (!r || !r.url) return null;
  const { name, subs, suffix, path } = splitUrl(r.url);
  const host = `${name}.${suffix}`;
  const haystack = [name, subs.join(" "), path].join(" ").toLowerCase();

  // whose name is being borrowed, if any
  let borrowed = null;
  Object.entries(KNOWN_INSTITUTIONS).forEach(([domain, label]) => {
    const key = domain.split(".")[0];
    const appears = subs.some((s) => s === key) || name === key;
    if (appears && host !== domain.replace(/^www\./, "")) borrowed = label;
  });
  const brand = KNOWN_BRANDS.find((b) => haystack.includes(b));

  const goals = INTENT_CUES
    .map((cue) => {
      const hits = cue.words.filter((word) => haystack.includes(word));
      return { goal: cue.goal, cue: hits[0] || "", score: hits.length };
    })
    .filter((entry) => entry.cue)
    .sort((a, b) => b.score - a.score);

  if (!goals.length && !borrowed && !brand) return null;
  return { goals, borrowed, brand, host };
}

/* One sentence, and it must stay a guess: the address says what it wants, the page would say what
   it does, and we never read the page. */
function intentLine(r) {
  const found = intentOf(r);
  if (!found) return "";
  const { goals, borrowed, brand } = found;
  const who = borrowed || (brand ? (DISPLAY_NAME[brand] || brand[0].toUpperCase() + brand.slice(1)) : "");
  /* A known credential case already says in the sentence what the address is built to take. Repeating
     the goal here made the card state it twice; the block names the target instead, which the sentence
     does not. */
  if (r.certain && r.decided_by === "credential imitation" && who) {
    return `<p class="intent-line intent-target"><span class="intent-tag">impersonating</span> ${escapeHtml(who)}</p>`;
  }
  let lead;
  if (who && goals.length) {
    lead = `Looks built to imitate ${escapeHtml(who)} and ${escapeHtml(goals[0].goal)}.`;
  } else if (who) {
    lead = `Borrows the name ${escapeHtml(who)} without owning it.`;
  } else {
    lead = `The address is shaped to ${escapeHtml(goals[0].goal)}.`;
  }
  return `<p class="intent-line"><span class="intent-tag">likely goal</span> ${lead}</p>`;
}


function intentList(r) {
  const found = intentOf(r);
  if (!found) {
    return `<p class="intent-none">No goal is legible from the name alone. That is not the same as
      harmless: a plain address can still lead somewhere bad.</p>`;
  }
  const rows = found.goals.map((entry) => `<li>
      <span class="goal">${escapeHtml(entry.goal)}</span>
      <span class="cue">named by "${escapeHtml(entry.cue)}"</span>
    </li>`).join("");
  const who = found.borrowed ? `<li>
      <span class="goal">borrow ${escapeHtml(found.borrowed)}'s name</span>
      <span class="cue">the name appears in the address, not the domain</span>
    </li>` : "";
  return `<ul class="intent-list">${who}${rows}</ul>`;
}

function autopsyMarkup(r, reported) {
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

  const known = KNOWN_INSTITUTIONS[host.replace(/^www\./, "")];
  let caption;
  if (reported) {
    caption = "Nothing in the name is out of place, which is exactly how an address like this gets past a reader. The report above is what settles it.";
  } else if (flagged === 0) {
    if (known) {
      // the heading already says whose address this is; the caption should add, not repeat
      caption = `Nothing in ${escapeHtml(host)} is out of place.`;
    } else {
      caption = trustedSuffix
      ? `Nothing in ${escapeHtml(host)} is out of place, and the ending is registry-controlled. It still deserves the caution you would give any link.`
      : `Nothing in ${escapeHtml(host)} is out of place. That is evidence, not a guarantee.`;
    }
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
      <ol class="autopsy-panel" aria-live="polite"></ol>
      <p class="autopsy-caption">${caption}</p>
    </div>`;
}
