/* Nyavu front-end. Vanilla JS, no build step, no external dependencies. */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const api = async (path, opts = {}) => {
    const res = await fetch(path, { credentials: "same-origin", ...opts });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    return data;
  };

  /* ---------------------------------------------------------------- routing */
  const views = $$(".view");
  function route() {
    const id = (location.hash || "#detector").slice(1);
    const target = $("#" + id) ? id : "detector";
    views.forEach(v => v.classList.toggle("active", v.id === target));
    $$("#nav a").forEach(a => a.classList.toggle("active", a.getAttribute("href") === "#" + target));
    if (target === "history") loadHistory();
    if (target === "model") loadModel();
    if (target === "detector") loadStats();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  window.addEventListener("hashchange", route);

  /* ------------------------------------------------------------------ scan */
  const form = $("#scanForm");
  const input = $("#urlInput");
  const result = $("#result");

  $$(".chip[data-url]").forEach(c =>
    c.addEventListener("click", () => { input.value = c.dataset.url; form.requestSubmit(); })
  );

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const url = input.value.trim();
    if (!url) return;
    const btn = $("#scanBtn");
    btn.disabled = true; btn.textContent = "Analysing…";
    document.body.classList.add("scanning");
    try {
      const r = await api("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      render(r);
      loadStats();
      loadHistory();
    } catch (err) {
      result.classList.remove("hidden");
      result.innerHTML = `<div class="verdict-text"><span class="badge high">Error</span>
        <p class="verdict-url">${escapeHtml(err.message)}</p></div>`;
    } finally {
      btn.disabled = false; btn.textContent = "Analyse";
      document.body.classList.remove("scanning");
    }
  });

  const TONE = { high: "var(--danger)", medium: "var(--warn)", low: "var(--safe)" };


  /* Small things people notice: numbers that count to their value, and a scanning
     line in the header while a request is in flight. */
  function countUp(el, value) {
    if (!el) return;
    const target = Number(value) || 0;
    const startAt = performance.now();
    const duration = 900;
    function step(now) {
      const t = Math.min(1, (now - startAt) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(target * eased).toLocaleString();
      if (t < 1) requestAnimationFrame(step);
      else el.textContent = target.toLocaleString();
    }
    requestAnimationFrame(step);
  }


  /* The result used to render below the fold, so the needle swept where nobody could
     see it. Only scroll when it is actually out of sight, and never when the reader
     has deliberately scrolled elsewhere. */
  function revealResult(el) {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    requestAnimationFrame(() => {
      const rect = el.getBoundingClientRect();
      const header = document.querySelector(".topbar");
      const offset = (header ? header.offsetHeight : 0) + 18;
      if (rect.top >= offset && rect.top < window.innerHeight * 0.7) return;
      window.scrollTo({
        top: Math.max(0, window.scrollY + rect.top - offset),
        behavior: reduce ? "auto" : "smooth",
      });
    });
  }




  /* The needle is the product's moment of measurement, so it is staged:
     a beat of stillness while the card settles, a climb, then a long approach
     that dithers between bands before locking on. 7.8 seconds in total: long
     enough to watch, short enough not to be an insult. Reduced-motion users get
     a short version rather than none - the number still has to arrive. */
  function sweepNeedle(root) {
    const g = root.querySelector(".gauge");
    if (!g) return;
    const target = Number(g.dataset.target || 0);
    const readout = g.querySelector(".readout span");
    const caption = g.querySelector(".readout small");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const pause = reduce ? 0 : 600;
    const duration = reduce ? 420 : 7800;

    if (caption) caption.textContent = "examining";

    setTimeout(() => {
      const started = performance.now();

      function frame(now) {
        const t = Math.min(1, (now - started) / duration);

        // 0 -> 86% quickly, then the last 14% slowly: the needle looks unsure
        const climb = t < 0.62
          ? (t / 0.62) * 0.86
          : 0.86 + (1 - Math.pow(1 - (t - 0.62) / 0.38, 2)) * 0.14;

        // dithering: twenty direction changes over the sweep, decaying to nothing.
        // Enough to feel like the needle is weighing the evidence, not so much that
        // it reads as a broken gauge.
        const wobble = Math.sin(t * 70) * Math.pow(1 - t, 1.6) * 8;
        const value = Math.max(0, Math.min(100, target * climb + wobble));

        g.style.setProperty("--p", value.toFixed(2));
        if (readout) readout.textContent = Math.round(value);

        if (t < 1) {
          requestAnimationFrame(frame);
        } else {
          g.style.setProperty("--p", target);
          if (readout) readout.textContent = target;
          if (caption) caption.textContent = "risk";
        }
      }
      requestAnimationFrame(frame);
    }, pause);
  }

  const escapeHtml = s => String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function render(r) {
    const pct = Math.round(r.probability * 100);
    const reasons = r.reasons.length
      ? r.reasons.map(t => `<li>${escapeHtml(t)}</li>`).join("")
      : `<li class="safe">No strong phishing indicators were found in the URL text.</li>`;

    const evidence = r.evidence && r.evidence.length
      ? (() => {
          const max = Math.max(...r.evidence.map(e => e.weight || 0), 0.0001);
          const bars = r.evidence.map(e => {
            const share = Math.max(6, Math.round(((e.weight || 0) / max) * 100));
            return `<span class="pill"><i style="--w:${share}%"></i>${escapeHtml(e.token)}</span>`;
          }).join("");
          return `<h3 class="block-title">Parts of the address that raised the score</h3>
                  <div class="evidence">${bars}</div>`;
        })()
      : "";

    const featRows = Object.entries(r.features)
      .filter(([, v]) => v !== 0 && v !== 0.0)
      .slice(0, 18)
      .map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");

    document.body.classList.add("has-result");
    result.classList.remove("hidden");
    result.innerHTML = `
      <div class="verdict-head">
        <div class="gauge" style="--p:0; --tone:${TONE[r.risk]}" data-target="${pct}">
          <svg class="dial" viewBox="0 0 200 132" aria-hidden="true">
            <path class="track" d="M22 112 A78 78 0 0 1 178 112" />
            <path class="fill" d="M22 112 A78 78 0 0 1 178 112" />
          </svg>
          <div class="needle"></div>
          <div class="readout"><span>0</span><small>risk</small></div>
        </div>
        <div class="verdict-text">
          <span class="badge ${r.risk}">${r.band}</span>${r.reputation === "established"
            ? '<span class="badge rep">Established domain</span>' : ""}
          <h2>${r.verdict === "phishing" ? "Something doesn't look right" : "No warning signs found"}</h2>
          <p class="verdict-url">${escapeHtml(r.url)}</p>
          ${r.suggested ? `<p class="suggest">You may have meant
             <strong>${escapeHtml(r.suggested.domain)}</strong> — that address is in our
             reference list for ${escapeHtml(r.suggested.brand)}. We cannot verify official
             sites, so only open it if you trust the address.</p>` : ""}
          <div class="meta-row">
            <span><b>Host</b> ${escapeHtml(r.host)}</span>
            ${r.verdict === "phishing"
              ? `<span><b>Model score</b> ${(r.probability * 100).toFixed(1)}</span>` : ""}
            <span><b>Latency</b> ${r.inference_ms} ms</span>
          </div>
        </div>
      </div>
      <h3 class="block-title">Why Nyavu raised a concern</h3>
      <ul class="reasons">${reasons}</ul>
      ${evidence}
      <details class="advanced">
        <summary>What the model measured</summary>
        <dl class="feat-grid">${featRows}</dl>
      </details>`;
    sweepNeedle(result);
    revealResult(result);
  }


  /* A light that follows the pointer across cards. Cheap, and it makes a static
     panel feel like a surface rather than a picture. */
  document.addEventListener("pointermove", (event) => {
    const card = event.target.closest(".verdict-head, .step, .panel, .stats-strip");
    if (!card) return;
    const rect = card.getBoundingClientRect();
    card.style.setProperty("--mx", `${event.clientX - rect.left}px`);
    card.style.setProperty("--my", `${event.clientY - rect.top}px`);
  }, { passive: true });

  /* ----------------------------------------------------------------- stats */
  async function loadStats() {
    try {
      const s = await api("/api/stats");
      countUp($("#statTotal"), s.total_scans);
      countUp($("#statPhish"), s.phishing);
      countUp($("#statUsers"), s.users);
    } catch { /* non-critical */ }
  }

  async function loadCorpusSize() {
    try {
      const m = await api("/api/model");
      $("#statTrain").textContent = m.dataset_size.toLocaleString();
    } catch { /* non-critical */ }
  }

  /* --------------------------------------------------------------- history */
  async function loadHistory() {
    const tbody = $("#historyTable tbody");
    const empty = $("#historyEmpty");
    try {
      const { items } = await api("/api/history?limit=25");
      empty.classList.toggle("hidden", items.length > 0);
      $("#historyTable").classList.toggle("hidden", items.length === 0);
      tbody.innerHTML = items.map(it => `
        <tr>
          <td>${new Date(it.created_at).toLocaleString()}</td>
          <td title="${escapeHtml(it.url)}">${escapeHtml(it.host)}</td>
          <td><span class="pill ${it.risk}">${escapeHtml(it.verdict)}</span></td>
          <td>${(it.probability * 100).toFixed(1)}%</td>
        </tr>`).join("");
    } catch (e) { empty.textContent = "Could not load history."; }
  }

  /* ----------------------------------------------------------------- model */
  async function loadModel() {
    const body = $("#modelBody");
    try {
      const m = await api("/api/model");
      const order = Object.keys(m.comparison);
      const rows = order.map(name => {
        const r = m.comparison[name];
        const cls = name === m.model ? "best" : "";
        return `<tr>
          <td class="${cls}">${name}</td>
          <td>${(r.accuracy * 100).toFixed(2)}%</td>
          <td>${(r.precision * 100).toFixed(2)}%</td>
          <td>${(r.recall * 100).toFixed(2)}%</td>
          <td>${(r.f1 * 100).toFixed(2)}%</td>
          <td>${(r.roc_auc * 100).toFixed(2)}%</td>
          <td>${(r.false_positive_rate * 100).toFixed(2)}%</td>
          <td>${r.inference_ms_per_url.toFixed(2)}</td>
        </tr>`;
      }).join("");

      body.innerHTML = `
        <dl class="kv">
          <div><dt>Deployed model</dt><dd>${m.model}</dd></div>
          <div><dt>Training URLs</dt><dd>${m.trained_on.toLocaleString()}</dd></div>
          <div><dt>Hold-out URLs</dt><dd>${m.tested_on.toLocaleString()}</dd></div>
          <div><dt>Input features</dt><dd>${m.features} numeric + char n-grams</dd></div>
        </dl>
        <h3 class="block-title">F1 by model · hold-out set</h3>
        <div class="bars">
          ${order.map(name => {
            const v = m.comparison[name].f1 * 100;
            const cls = name === m.model ? " bar-best" : "";
            return `<div class="bar-row${cls}">
              <span class="bar-name">${name}</span>
              <span class="bar"><i style="--v:${v.toFixed(2)}%"></i></span>
              <b class="bar-val">${v.toFixed(2)}</b>
            </div>`;
          }).join("")}
        </div>
        <h3 class="block-title">Full comparison — domain-disjoint hold-out set</h3>
        <table class="table">
          <thead><tr><th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th>
            <th>F1</th><th>ROC-AUC</th><th>False positive rate</th><th>ms / URL</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <h3 class="block-title">How it works</h3>
        <p class="lede">Each URL is reduced to its registrable domain and converted into
        17 numeric domain features plus character n-gram features of the domain name.
        Nothing is fetched from the internet, so a verdict is produced in milliseconds
        and cannot be influenced by the attacker's server.</p>`;
    } catch (e) {
      body.textContent = "Could not load model information.";
    }
  }

  /* ------------------------------------------------------------------ bulk */
  $("#bulkForm").addEventListener("submit", async e => {
    e.preventDefault();
    const file = $("#bulkFile").files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    const out = $("#bulkResult");
    out.classList.remove("hidden");
    out.innerHTML = "<p class='lede'>Screening…</p>";
    try {
      const r = await api("/api/scan/bulk", { method: "POST", body: fd });
      out.innerHTML = `
        <p class="lede"><strong>${r.flagged}</strong> of <strong>${r.count}</strong>
        URLs were flagged as phishing.</p>
        <table class="table">
          <thead><tr><th>Host</th><th>Verdict</th><th>Score</th></tr></thead>
          <tbody>${r.results.map(x => `
            <tr><td title="${escapeHtml(x.url)}">${escapeHtml(x.host || x.url)}</td>
            <td><span class="pill ${x.risk}">${escapeHtml(x.verdict)}</span></td>
            <td>${x.probability === null ? "—" : (x.probability * 100).toFixed(1) + "%"}</td></tr>`).join("")}
          </tbody></table>`;
      loadStats();
    } catch (err) {
      out.innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
    }
  });

  /* ------------------------------------------------------------------- QR */
  let qrStream = null, qrTimer = null;
  $("#qrBtn").addEventListener("click", async () => {
    const modal = $("#qrModal"), hint = $("#qrHint"), video = $("#qrVideo");
    modal.classList.remove("hidden");
    if (!("BarcodeDetector" in window)) {
      hint.textContent = "This browser cannot decode QR codes. Open Nyavu on an Android Chrome device to use the camera scanner.";
      return;
    }
    try {
      qrStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      video.srcObject = qrStream;
      await video.play();
      const detector = new BarcodeDetector({ formats: ["qr_code"] });
      hint.textContent = "Point the camera at a QR code…";
      qrTimer = setInterval(async () => {
        try {
          const codes = await detector.detect(video);
          if (codes.length) {
            const text = codes[0].rawValue;
            closeQr();
            input.value = text;
            form.requestSubmit();
          }
        } catch { /* frame skipped */ }
      }, 400);
    } catch (e) {
      hint.textContent = "Camera access was blocked. Allow camera permission and try again.";
    }
  });
  function closeQr() {
    if (qrTimer) { clearInterval(qrTimer); qrTimer = null; }
    if (qrStream) { qrStream.getTracks().forEach(t => t.stop()); qrStream = null; }
    $("#qrModal").classList.add("hidden");
  }
  $("#qrClose").addEventListener("click", closeQr);

  /* ----------------------------------------------------------------- auth */
  let mode = "login";
  const authModal = $("#authModal");

  async function refreshAccount() {
    try {
      const me = await api("/api/auth/me");
      const btn = $("#authBtn");
      if (me.authenticated) {
        btn.textContent = me.full_name || me.email;
        btn.onclick = async () => {
          await api("/api/auth/logout", { method: "POST" });
          refreshAccount(); loadStats(); loadHistory();
        };
        $("#historyNote").textContent = "Scans recorded against your account.";
      } else {
        btn.textContent = "Sign in";
        btn.onclick = () => openAuth("login");
        $("#historyNote").textContent = "Your most recent URL checks (anonymous session).";
      }
    } catch { /* ignore */ }
  }

  function openAuth(m) {
    mode = m;
    authModal.classList.remove("hidden");
    $("#authTitle").textContent = m === "login" ? "Sign in" : "Create an account";
    $("#authSubmit").textContent = m === "login" ? "Sign in" : "Register";
    $("#authSwitch").textContent = m === "login" ? "Need an account? Register" : "Already registered? Sign in";
    $("#authName").style.display = m === "login" ? "none" : "block";
    $("#authError").textContent = "";
  }
  $("#authClose").addEventListener("click", () => authModal.classList.add("hidden"));
  $("#authSwitch").addEventListener("click", e => {
    e.preventDefault(); openAuth(mode === "login" ? "register" : "login");
  });
  $("#authForm").addEventListener("submit", async e => {
    e.preventDefault();
    const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
    try {
      await api(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: $("#authEmail").value,
          password: $("#authPassword").value,
          full_name: $("#authName").value,
        }),
      });
      authModal.classList.add("hidden");
      $("#authPassword").value = "";
      refreshAccount(); loadHistory(); loadStats();
    } catch (err) {
      $("#authError").textContent = err.message;
    }
  });

  /* ------------------------------------------------------------------- PWA */
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
  }

  /* ------------------------------------------------------------------ boot */
  route();
  refreshAccount();
  loadStats();
  loadCorpusSize();

  // Deep link: /?u=<url> pre-fills and analyses immediately, which also makes the
  // result shareable and the screen reproducible for documentation.
  const preset = new URLSearchParams(location.search).get("u");
  if (preset) {
    input.value = preset;
    location.hash = "#detector";
    form.requestSubmit();
  }
})();
