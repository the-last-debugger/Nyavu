/**
 * Shusha Nyavu, background service worker.
 *
 * Two interception points, because one is not enough:
 *
 *   onBeforeNavigate  fires before the request leaves the browser. If the host is
 *                     already known to be phishing the user is redirected (block
 *                     mode) or handed a system notification (warn mode), without
 *                     ever contacting the site. This path works even when the host
 *                     does not resolve.
 *   onCommitted       fires once a page starts loading. It warms the cache for hosts
 *                     that were not known yet and injects the in-page banner.
 *
 * The extension never sends page content, cookies or history, only the host part of
 * the address the user is already navigating to.
 */
const DEFAULTS = {
  apiBase: "https://nyavu.onrender.com",
  mode: "warn",              // "warn" | "block"
  enabled: true,
  allow: []                  // hosts the user has chosen to trust
};

const CACHE_TTL_MS = 6 * 60 * 60 * 1000;


async function settings() {
  const s = await chrome.storage.local.get(["settings", "cache", "stats"]);
  return {
    settings: { ...DEFAULTS, ...(s.settings || {}) },
    cache: s.cache || {},
    stats: s.stats || { checked: 0, flagged: 0, allowed: 0 }
  };
}

async function save(patch) {
  const cur = await chrome.storage.local.get(["settings", "cache", "stats"]);
  await chrome.storage.local.set({ ...cur, ...patch });
}

function hostOf(url) {
  try { return new URL(url).hostname.toLowerCase(); } catch { return ""; }
}

/** The Nyavu app itself must never be netted: it is the tool, not a suspect. */
function ownHost(cfg) {
  try { return new URL(cfg.apiBase).hostname.toLowerCase(); } catch { return "127.0.0.1"; }
}

async function score(apiBase, url) {
  const res = await fetch(`${apiBase}/api/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url })
  });
  if (!res.ok) throw new Error(`Nyavu API returned ${res.status}`);
  return res.json();
}

/**
 * Every notification names the host it is about and carries its own id, so a notice
 * can never be mistaken for the page currently in front of the user. Notices for
 * other hosts are cleared as soon as the user moves on.
 */
function notify(host, verdict) {
  const pct = Math.round(verdict.probability * 100);
  const first = verdict.reasons?.[0] || "The model recognised a phishing pattern.";
  clearHits(host);
  chrome.notifications.create(`nyavu-hit-${host}`, {
    type: "basic",
    iconUrl: "icon-192.png",
    title: `${host} looks like phishing (${pct}%)`,
    message: `${first}  ·  Reported by Nyavu`.slice(0, 240),
    priority: 2
  });
}

function clearHits(keepHost) {
  chrome.notifications.getAll((all) => {
    for (const id of Object.keys(all || {})) {
      if (id.startsWith("nyavu-hit-") && id !== `nyavu-hit-${keepHost}`) {
        chrome.notifications.clear(id);
      }
    }
  });
}

function interstitial(tabId, host, verdict) {
  const q = new URLSearchParams({
    host,
    score: Math.round(verdict.probability * 100),
    reasons: JSON.stringify((verdict.reasons || []).slice(0, 4))
  });
  chrome.tabs.update(tabId, { url: chrome.runtime.getURL(`warning.html?${q}`) });
}

/** Runs before the request: no page has loaded, so a dead host is still catchable. */
async function onBeforeNavigate(details) {
  if (details.frameId !== 0 || !/^https?:/i.test(details.url)) return;
  const host = hostOf(details.url);
  if (!host) return;

  const { settings: cfg, cache } = await settings();
  if (!cfg.enabled || cfg.allow.includes(host)) return;
  if (host === ownHost(cfg)) return;   // never net the Nyavu app

  const cached = cache[host];
  const fresh = cached && Date.now() - cached.at < CACHE_TTL_MS;
  if (!fresh || cached.verdict !== "phishing") {
    clearHits(null);          // the page in front of the user is not a known hit
    return;
  }

  if (cfg.mode === "block" && details.tabId >= 0) {
    interstitial(details.tabId, host, cached);
  } else {
    notify(host, cached);
  }
}

/** Runs once a page commits: warms the cache and paints the banner. */
async function onCommitted(details) {
  if (details.frameId !== 0 || !/^https?:/i.test(details.url)) return;
  const host = hostOf(details.url);
  if (!host) return;

  const { settings: cfg, cache, stats } = await settings();
  if (!cfg.enabled || cfg.allow.includes(host)) return;
  if (host === ownHost(cfg)) return;   // never net the Nyavu app

  let verdict = cache[host];
  const fresh = verdict && Date.now() - verdict.at < CACHE_TTL_MS;

  if (!fresh) {
    try {
      const r = await score(cfg.apiBase, details.url);
      verdict = {
        at: Date.now(),
        risk: r.risk,
        band: r.band,
        verdict: r.verdict,
        probability: r.probability,
        reasons: r.reasons || []
      };
      cache[host] = verdict;
      const keys = Object.keys(cache);
      if (keys.length > 500) {
        keys.sort((a, b) => cache[a].at - cache[b].at)
            .slice(0, keys.length - 400)
            .forEach(k => delete cache[k]);
      }
      await save({ cache, stats: { ...stats, checked: stats.checked + 1 } });
    } catch (err) {
      console.warn("[Nyavu] API unreachable:", err.message);
      return;
    }
  }

  if (verdict.verdict !== "phishing") return;

  await save({ stats: { ...stats, flagged: stats.flagged + 1 } });

  if (cfg.mode === "block" && details.tabId >= 0) {
    interstitial(details.tabId, host, verdict);
    return;
  }

  try {
    await chrome.scripting.executeScript({
      target: { tabId: details.tabId },
      func: banner,
      args: [{
        host,
        score: Math.round(verdict.probability * 100),
        reasons: (verdict.reasons || []).slice(0, 3)
      }]
    });
  } catch (err) {
    // Error pages and restricted origins cannot be scripted; the notification
    // raised below is the fallback so the user is still warned.
    console.warn("[Nyavu] banner not injectable:", err.message);
    notify(host, verdict);
  }
}

/**
 * Injected into the page. Kept self-contained because it is serialised into the
 * tab's context and cannot reference anything above.
 */
function banner({ host, score, reasons }) {
  const ID = "shusha-nyavu-banner";
  if (document.getElementById(ID)) return;
  const bar = document.createElement("div");
  bar.id = ID;
  Object.assign(bar.style, {
    position: "fixed", zIndex: 2147483647, top: "0", left: "0", right: "0",
    background: "#3b0d12", color: "#ffe8e9", borderBottom: "2px solid #f2545b",
    font: "14px/1.5 -apple-system, Segoe UI, Roboto, sans-serif",
    padding: "12px 18px", display: "flex", gap: "14px", alignItems: "center",
    boxShadow: "0 6px 24px rgba(0,0,0,.45)"
  });
  const text = document.createElement("div");
  text.style.flex = "1";
  const safe = (s) => String(s).replace(/[<>&]/g,
    c => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));
  text.innerHTML =
    `<strong>Nyavu: this link looks like phishing (${score}% risk)</strong>` +
    (reasons.length
      ? `<div style="opacity:.85;margin-top:4px">${reasons.map(safe).join(" · ")}</div>`
      : "");
  const close = document.createElement("button");
  close.textContent = "Dismiss";
  Object.assign(close.style, {
    background: "#f2545b", color: "#1b0507", border: "0", borderRadius: "8px",
    padding: "7px 14px", fontWeight: "700", cursor: "pointer"
  });
  close.onclick = () => bar.remove();
  bar.append(text, close);
  document.documentElement.appendChild(bar);
}

chrome.webNavigation.onBeforeNavigate.addListener(onBeforeNavigate);
chrome.webNavigation.onCommitted.addListener(onCommitted);
chrome.notifications.onClicked.addListener((id) => chrome.notifications.clear(id));
chrome.runtime.onInstalled.addListener(() => save({ settings: DEFAULTS }));
