/* Shusha Nyavu — popup controller. */
const $ = (id) => document.getElementById(id);

async function currentHost() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) return { tab: null, host: "" };
  try { return { tab, host: new URL(tab.url).hostname.toLowerCase() }; }
  catch { return { tab, host: "" }; }
}

function paintBand(v) {
  const band = $("band");
  band.textContent = v ? `${v.band} · ${Math.round(v.probability * 100)}%` : "not yet checked";
  band.className = "band " + (v ? (v.risk || "unknown") : "unknown");
}

function paintReasons(v) {
  const list = $("reasons");
  list.innerHTML = "";
  for (const r of (v?.reasons || []).slice(0, 4)) {
    const li = document.createElement("li");
    li.textContent = r;
    list.appendChild(li);
  }
}

async function boot() {
  const { tab, host } = await currentHost();
  $("host").textContent = host || "no page open";
  $("analyse").disabled = !host;

  const { settings, cache, stats } = await chrome.storage.local.get(["settings", "cache", "stats"]);
  paintBand(cache?.[host]);
  paintReasons(cache?.[host]);

  const s = stats || { checked: 0, flagged: 0, allowed: 0 };
  $("s-checked").textContent = s.checked;
  $("s-flagged").textContent = s.flagged;
  $("s-allowed").textContent = s.allowed;

  try {
    const r = await fetch((settings?.apiBase || "https://nyavu.onrender.com") + "/api/health");
    $("dot").style.background = r.ok ? "var(--ok)" : "var(--bad)";
    $("dot").title = r.ok ? "Nyavu API reachable" : "Nyavu API unreachable";
  } catch {
    $("dot").style.background = "var(--bad)";
    $("dot").title = "Nyavu API unreachable";
  }

  $("analyse").onclick = () => {
    const base = settings?.apiBase || "https://nyavu.onrender.com";
    chrome.tabs.create({ url: `${base}/?u=${encodeURIComponent("https://" + host)}` });
  };

  $("trust").onclick = async () => {
    if (!host) return;
    const allow = new Set(settings?.allow || []);
    allow.add(host);
    await chrome.storage.local.set({ settings: { ...(settings || {}), allow: [...allow] } });
    const next = { checked: s.checked, flagged: s.flagged, allowed: s.allowed + 1 };
    await chrome.storage.local.set({ stats: next });
    $("band").textContent = "trusted";
    $("band").className = "band low";
    $("reasons").innerHTML = "";
  };

  $("options").onclick = () => chrome.runtime.openOptionsPage();
}

boot();
