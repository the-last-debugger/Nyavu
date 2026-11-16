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
    if (target === "detector") { loadStats(); loadSparkline(); }
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
    document.getElementById("scanForm").classList.add("scanning");
    try {
      const r = await api("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      render(r);
      loadStats();
      loadSparkline();
      loadHistory();
    } catch (err) {
      result.classList.remove("hidden");
      result.innerHTML = `<div class="verdict-text"><span class="badge high">Error</span>
        <p class="verdict-url">${escapeHtml(err.message)}</p></div>`;
    } finally {
      btn.disabled = false; btn.textContent = "Analyse";
      document.body.classList.remove("scanning");
      const f = document.getElementById("scanForm");
      if (f) f.classList.remove("scanning");
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
  let sweepToken = 0;


  /* Skip: jump the theatre to its end. The result is already known; the animation is
     a presentation of it, never a delay in computing it. */
  function finishNow() {
    sweepToken++;
    const card = document.querySelector(".result.pending");
    if (!card) return;
    const g = card.querySelector(".gauge");
    const target = Number(g && g.dataset.target ? g.dataset.target : 0);
    if (g) {
      g.style.setProperty("--p", target);
      g.style.setProperty("--tone", TONE_OF(target));
    }
    const ro = card.querySelector(".readout span");
    if (ro) ro.textContent = target;
    const cap = card.querySelector(".readout small");
    if (cap) cap.textContent = "risk";
    card.classList.remove("pending");
    const line = document.getElementById("thinking");
    if (line && line.parentElement) line.parentElement.remove();
    const skip = document.getElementById("skipBtn");
    if (skip) skip.remove();
  }

  document.addEventListener("click", (event) => {
    if (event.target && event.target.id === "skipBtn") finishNow();
  });

  /* The dial starts almost still, accelerates, becomes frantic, then commits.
     Seven seconds of it. Colour follows the band the needle is passing through,
     so the dial reads as undecided while it hunts.

     Note: this runs at full length even when the system asks for reduced motion.
     The dial is the product's only feedback that a scan happened; shortening it
     was hiding the feature on machines with Windows animation effects disabled.
     The decorative animations elsewhere still honour the preference. */
  const TONE_OF = (v) => (v < 35 ? "#35e0a0" : v < 65 ? "#ffb020" : "#ff4d6d");

  function sweepNeedle(root) {
    const g = root.querySelector(".gauge");
    if (!g) return;
    const target = Number(g.dataset.target || 0);
    const readout = g.querySelector(".readout span");
    const caption = g.querySelector(".readout small");

    const token = ++sweepToken;
    const pause = 250;
    const duration = 7000;

    if (caption) caption.textContent = "examining";

    const ease = (x) => {
      const k = Math.min(1, Math.max(0, x));
      return k * k * (3 - 2 * k);
    };

    function valueAt(t) {
      // the score is only approached in the final tenth
      const rise = target * ease(t / 0.7) * 0.55;
      const centre = rise + (target - rise) * ease((t - 0.9) / 0.1);
      // amplitude grows slowly, then collapses into the answer
      const amp = 52 * ease(t / 0.9) * (1 - ease((t - 0.92) / 0.08));
      // frequency climbs, so the swings crowd together before they stop
      const phase = 2 * Math.PI * (0.3 * t + 13 * t * t * t);
      return Math.max(0, Math.min(100, centre + amp * Math.sin(phase)));
    }

    setTimeout(() => {
      const started = performance.now();

      const PHASES = [
        [0.00, "Reading the address"],
        [0.18, "Finding the registered domain"],
        [0.34, "Comparing against known brands"],
        [0.52, "Measuring the character patterns"],
        [0.70, "Weighing the evidence"],
        [0.86, "Reaching a verdict"],
      ];
      let phaseIndex = -1;
      const phaseTimer = setInterval(() => {
        if (token !== sweepToken) { clearInterval(phaseTimer); return; }
        const elapsed = (performance.now() - started) / duration;
        let next = 0;
        PHASES.forEach((p, i) => { if (elapsed >= p[0]) next = i; });
        if (next !== phaseIndex) {
          phaseIndex = next;
          const node = document.querySelector("#thinking .phase");
          if (node) node.textContent = PHASES[next][1];
        }
        if (elapsed >= 1) clearInterval(phaseTimer);
      }, 120);

      function frame(now) {
        const t = Math.min(1, (now - started) / duration);
        const value = t === 1 ? target : valueAt(t);

        if (token !== sweepToken) return;   // a newer scan took over
        g.style.setProperty("--p", value.toFixed(2));
        g.style.setProperty("--tone", TONE_OF(value));
        if (readout) readout.textContent = Math.round(value);

        if (t < 1) {
          requestAnimationFrame(frame);
        } else {
          g.style.setProperty("--p", target);
          g.style.setProperty("--tone", TONE_OF(target));
          if (readout) readout.textContent = target;
          if (caption) caption.textContent = "risk";
          const card = g.closest(".result");
          if (card) card.classList.remove("pending");
          const line = document.getElementById("thinking");
          if (line && line.parentElement) line.parentElement.remove();
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
    result.classList.add("pending");
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

        <div class="fishing" data-catch="${r.risk === "high" ? "dark" : r.risk === "medium" ? "odd" : "plain"}" aria-hidden="true">
          <svg viewBox="0 0 600 210" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="seaG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#0B2530"/>
                <stop offset="100%" stop-color="#050D13"/>
              </linearGradient>
              <linearGradient id="skyG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#071019"/>
                <stop offset="100%" stop-color="#04070B"/>
              </linearGradient>
            </defs>

            <rect x="0" y="0" width="600" height="132" fill="url(#skyG)"/>
            <circle cx="470" cy="44" r="16" fill="#0F2A33"/>
            <rect x="0" y="130" width="600" height="80" fill="url(#seaG)"/>

            <circle class="ripple r1" cx="300" cy="166" r="9"/>
            <circle class="ripple r2" cx="300" cy="166" r="9"/>
            <circle class="ripple r3" cx="300" cy="166" r="9"/>

            <g class="boat">
              <path d="M196 132 q46 26 108 26 q62 0 96 -26 z" fill="#060C12" stroke="#1B2A36" stroke-width="2"/>
              <path d="M206 130 h188" stroke="#243543" stroke-width="3" stroke-linecap="round"/>
              <path d="M284 132 v-26" stroke="#1B2A36" stroke-width="3"/>
            </g>

            <g class="fisher">
              <path class="torso" d="M272 108 q10 -22 26 -4 l-4 24 h-18 z" fill="#060C12" stroke="#22323F" stroke-width="2"/>
              <path class="hat" d="M270 84 q16 -16 32 0 l6 4 h-44 z" fill="#060C12" stroke="#22323F" stroke-width="2"/>
              <circle class="head" cx="288" cy="88" r="7" fill="#060C12" stroke="#22323F" stroke-width="2"/>
              <g class="arm">
                <path d="M296 100 l34 -16" stroke="#22323F" stroke-width="5" stroke-linecap="round"/>
                <path d="M330 84 L392 44" stroke="#2C4150" stroke-width="2.4" stroke-linecap="round"/>
                <g class="netg">
                  <path class="net" d="M392 44 q14 10 6 26 q-16 -2 -20 -14 z"
                        fill="rgba(67,232,200,.08)" stroke="#43e8c8" stroke-width="1.6"/>
                  <path class="netmesh" d="M394 50 l8 10 M392 58 l8 10 M398 48 l-4 20"
                        stroke="rgba(67,232,200,.4)" stroke-width="1"/>
                </g>
              </g>
              <path class="line" d="M396 70 Q340 120 300 158" stroke="rgba(190,215,230,.28)"
                    stroke-width="1.1" fill="none"/>
            </g>

            <g class="catch">
              <g class="catch-dark">
                <path d="M282 158 q16 -20 34 -2 q-6 14 -20 14 z" fill="#200910" stroke="#ff4d6d" stroke-width="1.8"/>
                <path d="M292 148 l2 -10 M300 147 l3 -10 M308 150 l5 -9" stroke="#ff4d6d" stroke-width="1.8" stroke-linecap="round"/>
              </g>
              <g class="catch-odd">
                <circle cx="300" cy="156" r="12" fill="#1C1608" stroke="#ffb020" stroke-width="1.8"/>
                <path d="M295 149 q8 -8 8 6" stroke="#ffb020" stroke-width="1.8" fill="none" stroke-linecap="round"/>
                <circle cx="300" cy="162" r="2" fill="#ffb020"/>
              </g>
              <g class="catch-plain">
                <path d="M280 158 q18 -14 34 0 q-16 14 -34 0 z" fill="#0C2C24" stroke="#35e0a0" stroke-width="1.8"/>
                <path d="M314 158 l10 -7 v14 z" fill="#0C2C24" stroke="#35e0a0" stroke-width="1.6"/>
                <circle cx="290" cy="155" r="1.6" fill="#35e0a0"/>
              </g>
            </g>
          </svg>
        </div>
          <div class="skeleton" aria-hidden="true"><i></i><i></i><i></i></div>
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
      <div class="thinking-row">
        <p class="thinking" id="thinking"><span class="dot"></span><span class="phase">Reading the address</span></p>
        <button type="button" class="skip" id="skipBtn">Skip the theatre</button>
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

  /* A 14-day volume line. Drawn from /api/stats/daily, so it shows this service's
     own traffic and never implies knowledge of the wider internet. */
  function drawSparkline(days) {
    const holder = document.getElementById("spark");
    if (!holder || !days || !days.length) return;

    // The API returns only days that have rows. A day with no scans is a real zero,
    // so the series is filled out before it is drawn rather than left gappy.
    const span = 14;
    const byDay = new Map(days.map(d => [d.day, d.count]));
    const last = new Date(days[days.length - 1].day + "T00:00:00");
    const series = [];
    for (let i = span - 1; i >= 0; i--) {
      const d = new Date(last);
      d.setDate(last.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      series.push({ day: key, count: byDay.get(key) || 0 });
    }

    const busy = series.filter(d => d.count > 0);
    const w = 260, h = 52, pad = 7;
    const max = Math.max(...series.map(d => d.count), 1);
    const step = (w - pad * 2) / (series.length - 1);
    const points = series.map((d, i) => [
      pad + i * step,
      h - pad - (d.count / max) * (h - pad * 2),
    ]);

    const line = points.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
    const area = `${line} L${points[points.length - 1][0].toFixed(1)},${h - pad} L${pad},${h - pad} Z`;
    const dots = series.map((d, i) => d.count > 0
      ? `<circle class="spark-dot" cx="${points[i][0].toFixed(1)}" cy="${points[i][1].toFixed(1)}" r="2.2" />`
      : "").join("");

    const total = series.reduce((sum, d) => sum + d.count, 0);
    const caption = busy.length
      ? `last ${span} days · ${total} inspections on ${busy.length} day${busy.length === 1 ? "" : "s"}`
      : `last ${span} days · no inspections recorded yet`;

    holder.innerHTML = `
      <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">
        <line class="spark-base" x1="${pad}" y1="${h - pad}" x2="${w - pad}" y2="${h - pad}" />
        <path class="spark-area" d="${area}" />
        <path class="spark-line" d="${line}" />
        ${dots}
      </svg>
      <span class="spark-cap">${caption}</span>`;
    holder.classList.add("ready");
  }


  async function loadSparkline() {
    try {
      const data = await api("/api/stats/daily?days=14");
      drawSparkline(data.days);
    } catch { /* the strip is decoration until data exists */ }
  }

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
  loadSparkline();
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
