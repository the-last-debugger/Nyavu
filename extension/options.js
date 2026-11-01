/* Shusha Nyavu — settings page. */
const DEFAULTS = { apiBase: "http://127.0.0.1:8000", mode: "warn", enabled: true, allow: [] };
const $ = (id) => document.getElementById(id);

function paintAllow(allow) {
  $("allowList").textContent = allow.length ? allow.join(", ") : "None yet.";
}

async function boot() {
  const { settings } = await chrome.storage.local.get(["settings"]);
  const cfg = { ...DEFAULTS, ...(settings || {}) };
  $("api").value = cfg.apiBase;
  $("mode").value = cfg.mode;
  $("enabled").checked = cfg.enabled;
  paintAllow(cfg.allow);

  $("test").onclick = async () => {
    const out = $("testOut");
    out.textContent = "testing…";
    try {
      const r = await fetch($("api").value.replace(/\/$/, "") + "/api/health");
      const j = await r.json();
      out.textContent = j.status === "ok" ? "connected" : "unexpected response";
      out.style.color = j.status === "ok" ? "#34d399" : "#f2545b";
    } catch (e) {
      out.textContent = "unreachable — is the service running?";
      out.style.color = "#f2545b";
    }
  };

  $("clearAllow").onclick = async () => {
    const { settings: s } = await chrome.storage.local.get(["settings"]);
    const next = { ...DEFAULTS, ...(s || {}), allow: [] };
    await chrome.storage.local.set({ settings: next });
    paintAllow([]);
  };

  $("save").onclick = async () => {
    const { settings: s } = await chrome.storage.local.get(["settings"]);
    await chrome.storage.local.set({
      settings: {
        ...DEFAULTS, ...(s || {}),
        apiBase: $("api").value.trim().replace(/\/$/, ""),
        mode: $("mode").value,
        enabled: $("enabled").checked
      }
    });
    $("save").textContent = "Saved";
    setTimeout(() => ($("save").textContent = "Save settings"), 1200);
  };
}

boot();
