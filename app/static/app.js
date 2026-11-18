      /* The verdict opens: the reasons expand from nothing in a keyframe animation, so the
         card grows by their height over about two thirds of a second instead of snapping.
         A transition could not do it, because these blocks had no previous computed value
         to interpolate from while they were hidden. */
/* Nyavu front-end. Vanilla JS, no build step, no external dependencies. */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  /* FastAPI returns a string for the errors we raise and an array for the ones
     pydantic raises. Neither should reach the reader as a JSON blob. */
  function readError(data, status) {
    const detail = data && data.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] || {};
      const type = first.type || "";
      if (type === "string_too_long") return "That address is too long to be a real link.";
      if (type === "string_too_short") return "Type or paste a link first.";
      return first.msg ? String(first.msg) : "That input was not accepted.";
    }
    return `Request failed (${status})`;
  }

  const api = async (path, opts = {}) => {
    const res = await fetch(path, { credentials: "same-origin", ...opts });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(readError(data, res.status));
    return data;
  };

  /* ---------------------------------------------------------------- routing */
  const views = $$(".view");

  /* The browser can own the switch: View Transitions crossfades the old view out and
     the new one in as a single composited operation, so there is never a frame where
     both are half-true. Where it is unavailable, the CSS entrance animation runs
     instead - the same curve, one element at a time. */
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const canViewTransition = typeof document.startViewTransition === "function" && !prefersReduced;
  if (canViewTransition) document.documentElement.classList.add("vt");

  function applyRoute(target) {
    views.forEach(v => v.classList.toggle("active", v.id === target));
    $$("#nav a").forEach(a => a.classList.toggle("active", a.getAttribute("href") === "#" + target));
  }

  function afterRoute(target) {
    if (target === "history") loadHistory();
    if (target === "model") loadModel();
    if (target === "detector") { loadStats(); loadSparkline(); }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function route() {
    const id = (location.hash || "#detector").slice(1);
    const target = $("#" + id) ? id : "detector";
    const current = views.find(v => v.classList.contains("active"));
    if (current && current.id === target) { afterRoute(target); return; }

    if (canViewTransition) {
      const t = document.startViewTransition(() => applyRoute(target));
      t.finished.then(() => afterRoute(target)).catch(() => afterRoute(target));
    } else {
      applyRoute(target);
      afterRoute(target);
    }
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
  ensureClose(result);
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

    const bring = () => {
      const rect = el.getBoundingClientRect();
      const header = document.querySelector(".topbar");
      const offset = (header ? header.offsetHeight : 0) + 18;
      if (rect.top >= offset && rect.top < window.innerHeight * 0.7) return;
      window.scrollTo({
        top: Math.max(0, window.scrollY + rect.top - offset),
        behavior: reduce ? "auto" : "smooth",
      });
    };

    // The hero collapses over 620ms when a scan starts, which moves the card up the
    // page. Measuring before that settles sends the scroll past its target, which is
    // what happened on a phone. Measure now, then again once the layout is still.
    requestAnimationFrame(bring);
    setTimeout(bring, 700);
  }




  /* The needle is the product's moment of measurement, so it is staged:
     a beat of stillness while the card settles, a climb, then a long approach
     that dithers between bands before locking on. 7.8 seconds in total: long
     enough to watch, short enough not to be an insult. Reduced-motion users get
     a short version rather than none - the number still has to arrive. */
  let sweepToken = 0;


  /* Skip: jump the theatre to its end. The result is already known; the animation is
     a presentation of it, never a delay in computing it. */
  /* Skip: land on the finished state immediately, without the theatre. */
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
    const scene = card.querySelector(".fishing");
    if (scene) scene.style.display = "none";
    card.classList.remove("pending");
    card.classList.remove("zooming");
    ensureClose(card);
    // the skip path must show the same verdict as the theatrical one
    card.classList.add("verdict-shown");
    normaliseCard(card);
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

  /* The net is driven from JavaScript rather than CSS, because the strip of netting
     between his hands and the net has to follow it. In reality the part still held
     stays narrow while the thrown part opens out; on the haul it reverses. */
  const NET_KEY = [
    [0.00, 268, 158, 0.10, -8],
    [0.12, 268, 158, 0.14, -8],
    [0.26, 310, 150, 0.62, 10],
    [0.34, 352, 194, 1.12, 0],
    [0.66, 355, 196, 1.16, -3],
    [0.78, 330, 168, 0.86, 5],
    [0.88, 286, 148, 0.62, -4],
    [0.94, 254, 124, 0.42, 0],
    [1.00, 250, 116, 0.34, 0],
  ];
  // one fixed radius per spoke: the rim is never a circle, it is a torn hide
  /* set while the catch is making its escape, so the scene loop stops holding it */
  let catchEscaping = false;

  const IRREG = [1.12, 0.94, 1.03, 0.86, 1.08, 0.97, 1.15, 0.9, 1.0, 0.88,
                 1.06, 0.93, 1.11, 0.96, 1.02, 0.87, 1.09, 0.95, 1.13, 0.99];

  const HAND_A = [236, 105];
  const HAND_B = [246, 121];



  /* A smooth closed curve through a ring of points: quadratics through the midpoints
     of each pair. Cheap, and it gives the rim the soft, lobed edge a net actually has
     instead of a polygon. */


  /* The net is real geometry, rebuilt every frame: a canopy with a near rim and a
     far rim, so it reads as a cone of cloth rather than a flat wheel, plus rings and
     spokes and a sway driven by two slow sines. A cast net covers ground - it opens
     wide as it flies and settles over the water. */
  /* Camera move on the viewBox: exact framing, and the artwork scales with it. */







  /* The scene runs on its own ten-second clock from the moment the card appears.
     The dial waits for the landing, then runs its own shorter sweep; the two are
     separate clocks so retiming one never drags the other. */
  /* One master clock for the whole performance. Every beat is a timestamp here, so
     retiming one act never drags another out of step.

     The choreography follows the standard shape: anticipation (winding up), action
     (the throw), follow-through (the net drifting), a hold while the dial works, then
     a transition that carries the eye into the card. Each beat is given time to land
     rather than being packed tight. */

  /* ---------------------------------------------------------------------------
     The whole performance, on one clock. Every beat is a timestamp, and each
     visual is animated here rather than in CSS, because two systems claiming the
     same property is how the splash ended up both everywhere and nowhere.

       0.0s  net leaves his hands
       4.7s  it meets the water: a short burst, then gone
       9.4s  net aboard, fish in his hands - the dial starts
      13.4s  the dial settles and he reacts to what he caught
      15.2s  camera pushes in on the catch
      18.8s  the scene sinks into water and the verdict rises out of it
     --------------------------------------------------------------------------- */
  /* Deliberately long. Every beat gets room to read before the next begins; these
     numbers come down only once each one is confirmed to render and to land.

       0-2s    the card settles, the scene fades up
       2-5s    he winds the net back
       5-8s    the throw
       8-9s    it meets the water
       9-20s   the net lies there and drifts
      20-24s   the haul
      24-26s   the catch comes aboard
      26-32s   he turns it over - the reaction, six seconds of it
      32-36s   the camera pushes in
      34-44s   the dial wakes and calibrates while he examines
      46-58s   water builds, takes over, and clears
      58s      the verdict
  */
  /* Every beat below has now been verified to render, to move and to settle, so the
     waits are trimmed to what the eye needs rather than what exploration needed.

       0.0- 2.0  wind up
       2.0- 4.0  the throw
       4.9       it meets the water
       4.9-11.0  the net lies there
      11.0-12.5  haul
      12.5-13.5  the catch comes aboard
      13.5-17.5  he turns it over
      17.5-20.0  the camera pushes in
      18.5-27.5  the dial calibrates and settles
      29.0-35.0  water builds and takes over
      35.0       card swaps behind it
      39.0       verdict
  */

  /* The verdict is the product's answer, so it gets the stage rather than sitting in
     the page flow. A blurred backdrop, the card lifted above it, and a way out that
     returns everything to normal. */

  /* The card keeps its own layout; the modal is a shell around it. Wrapping rather
     than restyling means the verdict looks exactly as designed, at any size. */



  /* He talks while he works. The lines are chosen by what is in the net, and they
     are written in his voice: dry, plain, never a marketing sentence. */
  /* He speaks before he works. */


  /* His lines. The deck is reshuffled every scan, one lesson is slipped in, and the
     phish/fish pun belongs to the dark catch where it actually applies. */

  /* He speaks twice while he works and twice while he examines - each line placed on a
     beat so the words and the action agree. The outcome-specific lines do not begin
     until the catch is in his hands, so the verdict is never given away early. */


  function say(root, text) {
    const bubble = root.querySelector(".bubble");
    if (!bubble || !text) return;
    const span = bubble.querySelector("span");
    if (span) span.textContent = text;
    bubble.classList.add("on", "swap");
    setTimeout(() => bubble.classList.remove("swap"), 180);
  }







  /* The scene fades; a skeleton holds the card's exact space; the verdict fills it.
     One container, no shell, no curtain, no movement of the page underneath. */

  /* Some layout quirks have resisted every selector I have tried; setting the two
     properties directly on the nodes is guaranteed to win. */
  function normaliseCard(card) {
    if (!card) return;
    card.querySelectorAll(".block-title").forEach((el) => {
      el.style.width = "100%";
      el.style.maxWidth = "none";
      el.style.marginLeft = "0";
      el.style.float = "none";
    });
    card.querySelectorAll(".reasons, .evidence").forEach((el) => {
      el.style.width = "100%";
      el.style.marginLeft = "0";
    });
  }

  /* He goes under, and the catch leaves the way it came - out of the water, up, and
     gone. The jump is computed, so it arcs rather than slides. */




  /* ---------------------------------------------------------------------------
     The examination, in six seconds rather than forty.

     The address is taken apart, each piece gets its note, the pieces that raised the
     score are marked, the dial settles, and the verdict is delivered. Type and rules
     only, so there is nothing here that can be got "almost" right.
     --------------------------------------------------------------------------- */
  /* ---------------------------------------------------------------------------
     The examination: seven seconds, five movements.

     0.35 the address is on the table      3.4  the dial begins its rise
     from 0.9 each piece is annotated      5.6  the needle settles
     2.6  the flagged pieces are called    6.4  the verdict lands
     --------------------------------------------------------------------------- */
  function runScene(root) {
    // may be handed the document or the card itself
    const card = root && root.matches && root.matches(".result") ? root : root.querySelector(".result");
    if (!card) return;

    const autopsy = card.querySelector(".autopsy");
    const segs = autopsy ? Array.from(autopsy.querySelectorAll(".seg")) : [];
    window.__sceneStart = performance.now();

    const phase = card.querySelector(".thinking .phase");
    const say = (text) => { if (phase) phase.textContent = text; };
    const delay = (ms, fn) => setTimeout(fn, ms);

    delay(350, () => {
      if (autopsy) autopsy.classList.add("live");
      say("Reading the address");
    });

    /* The address is written out by a cursor, left to right, one piece at a time. Then the
       notes resolve from the ending backwards, which is the lesson. Writing it is the
       clearest way to show something being worked on, and it needs no illustration. */
    const cursor = autopsy ? autopsy.querySelector(".scan-cursor") : null;
    const tag = autopsy ? autopsy.querySelector(".scan-tag") : null;
    const caret = autopsy ? autopsy.querySelector(".autopsy-caret") : null;
    const mode = autopsy ? autopsy.querySelector(".autopsy-mode") : null;

    const pieces = segs
      .map((el) => ({
        el,
        ink: el.querySelector(".seg-ink"),
        text: el.querySelector(".seg-text"),
        role: el.dataset.role || "",
      }))
      .sort((a, b) => a.el.offsetLeft - b.el.offsetLeft);

    const WRITE_START = 380;
    const PER_MS = 62;           // per piece, slow enough to watch being written

    const line = autopsy ? autopsy.querySelector(".autopsy-line") : null;
    const lineLeft = line ? line.getBoundingClientRect().left : 0;

    if (cursor) {
      cursor.classList.add("on");
      cursor.style.left = pieces.length ? pieces[0].el.offsetLeft + "px" : "0px";
    }

    let clock = WRITE_START;

    pieces.forEach((piece) => {
      piece.text.style.width = "0px";                 // hidden until written
      const width = piece.ink ? piece.ink.offsetWidth : 0;
      const dur = Math.max(90, width * PER_MS / 10);

      delay(clock, () => {
        if (tag) tag.textContent = piece.role;
        piece.el.classList.add("on");
        piece.el.classList.add("writing");
        piece.text.style.transition = `width ${dur}ms steps(12, end)`;
        piece.text.style.width = width + "px";
      });

      // the cursor rides the writing edge
      const steps = 14;
      for (let k = 1; k <= steps; k++) {
        delay(clock + (dur * k) / steps, () => {
          if (!cursor) return;
          cursor.style.left = (piece.el.offsetLeft + (width * k) / steps) + "px";
        });
      }

      clock += dur + 40;
    });

    if (cursor) {
      delay(clock + 60, () => {
        cursor.classList.remove("on");
        if (tag) tag.textContent = "";
      });
    }

    /* the resolve: notes arrive from the ending backwards */
    const resolveStart = clock + 200;
    delay(resolveStart, () => {
      if (mode) { mode.textContent = "reading from the right"; mode.dataset.state = "reading"; }
    });

    [...segs].reverse().forEach((seg, i) => {
      delay(resolveStart + i * 220, () => {
        if (caret) {
          caret.style.left = seg.offsetLeft + "px";
          caret.style.width = Math.max(12, seg.offsetWidth) + "px";
          caret.classList.add("on");
        }
        seg.classList.add("noted");
      });
    });

    delay(resolveStart + segs.length * 220 + 160, () => {
      if (caret) caret.classList.remove("on");
      if (autopsy) autopsy.classList.add("swept");
      if (mode) mode.dataset.state = "done";
    });

    const flagged = segs.filter((el) => el.classList.contains("flag"));
    flagged.forEach((seg, i) => {
      delay(2600 + i * 280, () => {
        seg.classList.add("called");
        say("Comparing against known brands");
      });
    });

    delay(3400, () => {
      say("Weighing the evidence");
      card.classList.add("dialcoming");
      sweepNeedle(card, 2200);
    });

    delay(5600, () => say("Reaching a verdict"));

    delay(6800, () => {
      /* The card grows by the height of the reasons at this instant. Animating that
         height has been attempted four ways, including animating the container itself,
         and the browser applies the new height without interpolating it: legacy rules in
         the stylesheet own display, opacity and transition for the inner verdict blocks
         with !important and with delays, so the reveal is a discrete change. The honest
         fix is to consolidate those rules, which is recorded in the backlog. */
      card.classList.add("verdict-shown");
      card.classList.remove("pending");
      const row = card.querySelector(".thinking-row");
      if (row) row.remove();
      normaliseCard(card);
      ensureClose(card);
      openVerdict(card);
    });
  }

  const TONE_OF = (v) => (v < 35 ? "#7FA98F" : v < 65 ? "#ffb020" : "#ff4d6d");

  /* The needle makes one gesture: it rises, overshoots by a few points, and settles.
     No vibration, no dithering, and it stops dead when it arrives. */
  function sweepNeedle(root, duration = 2200) {
    const g = root.querySelector(".gauge");
    if (!g) return;
    const target = Number(g.dataset.target || 0);
    const readout = g.querySelector(".readout span");
    const caption = g.querySelector(".readout small");
    const token = ++sweepToken;

    if (caption) caption.textContent = "estimating";
    const started = performance.now();
    const easeOut = (x) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);

    function frame(now) {
      if (token !== sweepToken) return;
      const t = Math.min(1, (now - started) / duration);
      let value;
      if (t >= 1) {
        value = target;
      } else {
        const base = target * easeOut(t);
        const swing = t > 0.6 && t < 1 ? Math.sin(Math.PI * ((t - 0.6) / 0.4)) * 3.5 : 0;
        value = Math.max(0, Math.min(100, base + swing));
      }
      g.style.setProperty("--p", t >= 1 ? String(target) : value.toFixed(2));
      g.style.setProperty("--tone", TONE_OF(target));
      if (readout) readout.textContent = String(Math.round(value));
      if (t >= 1) {
        if (readout) readout.textContent = String(target);
        if (caption) caption.textContent = "% risk";
        return;
      }
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }




  const escapeHtml = s => String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function render(r) {
    const pct = Math.round(r.probability * 100);

    /* The number is the model's estimated chance that the address is a phish, not a
       tally of faults. People reasonably expect a known-good site to read zero, so the
       card says out loud what the figure is, and why a real site still scores. */
    /* An established domain is held at a ceiling of fifteen, which is not the model's
       estimate: it is a prior applied so a known site is never flagged on the shape of its
       name. Saying "15" without saying that invites the reading "fifteen problems". */
    const scoreNote = r.capped_by_reputation
      ? `Scored ${pct} out of 100, which is a ceiling rather than an estimate. The name-based model put this address at ${Math.round((r.model_probability || 0) * 100)}, and an established domain holds it at ${pct} so that a known site is never flagged on the shape of its name.`
      : r.risk === "high"
      ? `Scored ${pct} out of 100. That is the estimated chance this address is a phish, read from its name alone. Anything above 65 is treated as a concern.`
      : r.risk === "medium"
        ? `Scored ${pct} out of 100. That is the estimated chance this address is a phish, read from its name alone. Below half, but not low enough to call it safe.`
        : `Scored ${pct} out of 100. That is the estimated chance this address is a phish, not a count of things wrong with it. A real site rarely reads zero, because the figure is a probability.`;
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
          const fragTitle = r.risk === "low"
            ? "Parts of the address that counted in its favour"
            : "Parts of the address that raised the score";
          return `<h3 class="block-title">${fragTitle}</h3>
                  <div class="evidence">${bars}</div>`;
        })()
      : "";

    const featRows = Object.entries(r.features)
      .filter(([, v]) => v !== 0 && v !== 0.0)
      .slice(0, 18)
      .map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");

    document.body.classList.add("has-result");
    result.classList.remove("hidden");
  ensureClose(result);

    /* The card element survives between scans, so anything the previous run set on it
       has to be cleared here. Without this the dial arrives already visible on the
       next link, and a stale water curtain can linger under the new scene. */
    result.classList.remove("dialcoming", "zooming", "modal", "revealed", "verdict-shown");
    catchEscaping = false;
    result.querySelectorAll(".waterline").forEach((n) => n.remove());
    document.body.classList.remove("verdict-open");
    document.documentElement.classList.remove("modal-lock");

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
          <h2>${r.risk === "high" ? "Something doesn't look right"
            : r.risk === "medium" ? "This one is hard to call"
            : "Nothing suspicious in the name"}</h2>
          <p class="verdict-url">${escapeHtml(r.url)}</p>
          <p class="score-note">${scoreNote}</p>
          <div class="stamp ${r.risk}" aria-hidden="true">${r.risk === "high" ? "phishing" : r.risk === "medium" ? "unsure" : "clear"}</div>
        </div>
        ${autopsyMarkup(r)}
      </div>
      <div class="thinking-row">
        <p class="thinking" id="thinking"><span class="dot"></span><span class="phase">Reading the address</span></p>
        <button type="button" class="skip" id="skipBtn">Skip the theatre</button>
      </div>
      <h3 class="block-title">${r.risk === "low"
        ? "Why this looks fine"
        : r.risk === "medium" ? "What gave Nyavu pause" : "Why Nyavu raised a concern"}</h3>
      <ul class="reasons">${reasons}</ul>
      ${evidence}
      <details class="advanced">
        <summary>What the model measured</summary>
        <dl class="feat-grid">${featRows}</dl>
      </details>`;
    result._verdictHTML = result.innerHTML;
    result._target = pct;
    result.dataset.target = String(pct);
    const gauge = result.querySelector(".gauge");
    if (gauge) gauge.dataset.target = String(pct);
    runScene(result);          // the examination owns the clock; it starts the dial itself
    revealResult(result);
  }



  /* ---------------------------------------------------------------- liveliness */


  /* Sections rise as they come into view. */
  const revealer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (!entry.isIntersecting) return;
      entry.target.style.transitionDelay = `${Math.min(i * 60, 240)}ms`;
      entry.target.classList.add("in");
      revealer.unobserve(entry.target);
    });
  }, { rootMargin: "0px 0px -12% 0px", threshold: 0.08 });

  function watchSections() {
    document.querySelectorAll(".step, .panel, .stats-strip, .spark-card")
      .forEach((el) => {
        if (el.classList.contains("in")) return;
        el.classList.add("reveal");
        revealer.observe(el);
      });
  }

  // Hero parallax: the orbital mark leans away from the pointer. A few degrees is
  // enough to make the page feel like a surface rather than a picture.
  document.addEventListener("pointermove", (event) => {
    const hero = document.querySelector(".hero");
    const visual = document.querySelector(".hero-visual");
    if (!hero || !visual) return;
    const r = hero.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right ||
        event.clientY < r.top || event.clientY > r.bottom) return;
    const dx = (event.clientX - (r.left + r.width / 2)) / (r.width / 2);
    const dy = (event.clientY - (r.top + r.height / 2)) / (r.height / 2);
    visual.style.setProperty("--rx", `${(-dy * 7).toFixed(2)}deg`);
    visual.style.setProperty("--ry", `${(dx * 9).toFixed(2)}deg`);
  }, { passive: true });

  // Magnetic primary button: it leans toward the pointer, then springs back.
  document.addEventListener("pointermove", (event) => {
    const btn = event.target.closest && event.target.closest(".btn.primary");
    if (!btn) return;
    const r = btn.getBoundingClientRect();
    const dx = (event.clientX - (r.left + r.width / 2)) / (r.width / 2);
    const dy = (event.clientY - (r.top + r.height / 2)) / (r.height / 2);
    btn.style.setProperty("--bx", `${(dx * 3).toFixed(2)}px`);
    btn.style.setProperty("--by", `${(dy * 2).toFixed(2)}px`);
  }, { passive: true });

  document.addEventListener("pointerout", (event) => {
    const btn = event.target.closest && event.target.closest(".btn.primary");
    if (!btn) return;
    btn.style.setProperty("--bx", "0px");
    btn.style.setProperty("--by", "0px");
  }, { passive: true });

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
      // the public page carries two figures: how much has been checked here, and how much
      // the model learned on. Accusation counts and account counts are operational, and
      // they belong to the signed-in view rather than the front door.
      countUp($("#statTotal"), s.total_scans);
    } catch { /* non-critical */ }
  }

  async function loadCorpusSize() {
    try {
      const m = await api("/api/model");
      $("#statTrain").textContent = m.dataset_size.toLocaleString();
    } catch { /* non-critical */ }
  }

  /* --------------------------------------------------------------- history */

  /* The drop zone: a file input that can also be dropped onto, with the chosen name
     shown in place of the browser's default control. */
  (function wireBulkDrop() {
    const drop = document.getElementById("bulkDrop");
    const input = document.getElementById("bulkFile");
    const name = document.getElementById("bulkFileName");
    if (!drop || !input) return;

    const show = () => {
      const f = input.files && input.files[0];
      if (name) name.textContent = f ? f.name : "No file chosen";
      drop.classList.toggle("has-file", !!f);
    };

    input.addEventListener("change", show);

    ["dragenter", "dragover"].forEach((evt) =>
      drop.addEventListener(evt, (e) => { e.preventDefault(); drop.classList.add("over"); }));

    ["dragleave", "drop"].forEach((evt) =>
      drop.addEventListener(evt, (e) => { e.preventDefault(); drop.classList.remove("over"); }));

    drop.addEventListener("drop", (e) => {
      const files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) return;
      const dt = new DataTransfer();
      dt.items.add(files[0]);
      input.files = dt.files;
      show();
    });
  })();

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
          <td><span class="bulk-verdict ${it.risk}">${escapeHtml(it.verdict)}</span></td>
          <td>${it.probability === null || it.probability === undefined ? "not scored" : Math.round(it.probability * 100)}</td>
        </tr>`).join("");
    } catch (e) {
        empty.classList.remove("hidden");
        const t = empty.querySelector(".empty-title");
        if (t) t.textContent = "Could not load history";
      }
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
        <h3 class="block-title">Full comparison, domain-disjoint hold-out set</h3>
        <div class="table-scroll"><table class="table">
          <thead><tr><th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th>
            <th>F1</th><th>ROC-AUC</th><th>False positive rate</th><th>ms / URL</th></tr></thead>
          <tbody>${rows}</tbody>
        </table></div>
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
        <div class="table-scroll"><table class="table">
          <thead><tr><th>Host</th><th>Verdict</th><th>Risk out of 100</th></tr></thead>
          <tbody>${r.results.map(x => `
            <tr><td title="${escapeHtml(x.url)}">${escapeHtml(x.host || x.url)}</td>
            <td><span class="bulk-verdict ${x.risk}">${escapeHtml(x.verdict)}</span></td>
            <td>${x.probability === null || x.probability === undefined ? "not scored" : Math.round(x.probability * 100)}</td></tr>`).join("")}
          </tbody></table></div>`;
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
        btn.title = "Signed in. Click to sign out.";
        btn.setAttribute("aria-label", `Signed in as ${me.email}. Sign out.`);
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

  /* --------------------------------------------------------------- suggestions
     Typing a long address by hand is the slowest way into the product. The list is
     offered, never insisted on: arrows move, Enter takes one, Escape dismisses, and
     nothing is filled in unless it is chosen. */
  (function initSuggest() {
    const input = $("#urlInput");
    const row = input && input.closest(".input-row");
    if (!input || !row) return;

    const list = document.createElement("ul");
    list.className = "suggest-list hidden";
    list.setAttribute("role", "listbox");
    row.appendChild(list);

    let items = [];
    let active = -1;
    let timer = 0;
    let lastQuery = "";

    const close = () => {
      list.classList.add("hidden");
      list.innerHTML = "";
      items = [];
      active = -1;
    };

    const paint = () => {
      list.innerHTML = items
        .map((text, i) => `<li role="option" class="${i === active ? "active" : ""}" data-value="${text}">${text}</li>`)
        .join("");
    };

    const choose = (value) => {
      input.value = value.startsWith("http") ? value : "https://" + value;
      close();
      input.focus();
    };

    input.addEventListener("input", () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) { close(); return; }
      timer = setTimeout(async () => {
        try {
          const data = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`).then((r) => r.json());
          if (input.value.trim() !== q) return;           // the field moved on
          lastQuery = q;
          items = (data.suggestions || []).slice(0, 6);
          active = -1;
          if (!items.length) { close(); return; }
          paint();
          list.classList.remove("hidden");
        } catch { close(); }
      }, 140);
    });

    input.addEventListener("keydown", (event) => {
      if (list.classList.contains("hidden")) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        active = (active + 1) % items.length;
        paint();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        active = (active - 1 + items.length) % items.length;
        paint();
      } else if (event.key === "Enter" && active >= 0) {
        event.preventDefault();
        choose(items[active]);
      } else if (event.key === "Escape") {
        close();
      }
    });

    list.addEventListener("mousedown", (event) => {
      const li = event.target.closest("li[data-value]");
      if (!li) return;
      event.preventDefault();
      choose(li.dataset.value);
    });

    input.addEventListener("blur", () => setTimeout(close, 120));
    row.addEventListener("focusout", (event) => {
      if (!row.contains(event.relatedTarget)) setTimeout(close, 120);
    });
  })();

  /* ---------------------------------------------------- the way back from Google
     The callback returns to /?auth=ok or /?auth=failed and nothing read it, so a
     successful sign-in and a broken one looked identical: a page that simply loaded.
     This says which happened, in a line that disappears, and strips the parameter. */
  (function handleAuthReturn() {
    const params = new URLSearchParams(location.search);
    const result = params.get("auth");
    if (!result) return;

    const messages = {
      ok: ["Signed in.", "Your checks are now recorded against your account."],
      cancelled: ["Sign-in cancelled.", "Nothing changed."],
      failed: ["That sign-in did not complete.", "Google returned an error. Try again."],
      state: ["That sign-in could not be verified.", "The request may have timed out. Try again."],
      unconfigured: ["Google sign-in is not configured.", "Use email instead."],
      noemail: ["Google did not share an address.", "Sign-in needs an email address."],
    };
    const [title, detail] = messages[result] || ["Sign-in could not complete.", "Try again."];

    const bar = document.createElement("div");
    bar.className = "auth-notice" + (result === "ok" ? " good" : "");
    bar.innerHTML = `<strong>${title}</strong><span>${detail}</span>
      <button type="button" aria-label="Dismiss">\u00d7</button>`;
    bar.querySelector("button").addEventListener("click", () => bar.remove());
    const main = document.querySelector("main");
    if (main) main.parentNode.insertBefore(bar, main);
    setTimeout(() => bar.classList.add("fade"), 6000);

    // the URL should not keep saying what happened
    const clean = new URL(location.href);
    clean.searchParams.delete("auth");
    history.replaceState({}, "", clean.pathname + (clean.hash || ""));

    if (result === "ok") refreshAccount();
  })();

  /* ---------------------------------------------------------- alternative sign in */
  (async function initAltAuth() {
    const googleBtn = $("#googleBtn");
    const alt = $("#authAlt");
    const phoneStep = $("#phoneStep");
    const phoneBtn = $("#phoneBtn");
    const phoneBack = $("#phoneBack");
    const phoneSend = $("#phoneSend");
    const phoneVerify = $("#phoneVerify");
    const phoneError = $("#phoneError");
    const authOr = $("#authOr");
    const emailForm = $("#authForm");
    if (!googleBtn || !phoneStep) return;

    let methods = { google: false, phone: false, sms: false };
    try {
      methods = await fetch("/api/auth/methods").then((r) => r.json());
    } catch { /* offline: keep email only */ }

    // never offer a method that cannot work
    if (!methods.google) googleBtn.remove();
    if (!methods.phone) { phoneBtn.remove(); }
    if (!methods.google && !methods.phone) { alt.remove(); authOr.remove(); }

    const showPhone = (on) => {
      phoneStep.classList.toggle("hidden", !on);
      emailForm.classList.toggle("hidden", on);
      if (authOr) authOr.classList.toggle("hidden", on);
      if (alt) alt.classList.toggle("hidden", on);
      if (on) $("#phoneInput").focus();
    };

    phoneBtn.addEventListener("click", () => showPhone(true));
    phoneBack.addEventListener("click", () => showPhone(false));

    phoneSend.addEventListener("click", async () => {
      phoneError.textContent = "";
      const phone = $("#phoneInput").value.trim();
      if (phone.length < 7) { phoneError.textContent = "Enter a phone number."; return; }
      phoneSend.disabled = true;
      phoneSend.textContent = "Sending…";
      try {
        const res = await fetch("/api/auth/phone/start", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Could not send the code.");
        $("#phoneCodeStep").classList.remove("hidden");
        phoneSend.textContent = data.channel === "sms" ? "Code sent" : "Code sent (see server log)";
        $("#phoneCode").focus();
      } catch (err) {
        phoneError.textContent = err.message;
        phoneSend.disabled = false;
        phoneSend.textContent = "Send me a code";
      }
    });

    phoneVerify.addEventListener("click", async () => {
      phoneError.textContent = "";
      const phone = $("#phoneInput").value.trim();
      const code = $("#phoneCode").value.trim();
      if (code.length < 4) { phoneError.textContent = "Enter the code."; return; }
      try {
        const res = await fetch("/api/auth/phone/verify", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone, code }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "That code was not accepted.");
        $("#authModal").classList.add("hidden");
        refreshAccount(); loadHistory(); loadStats();
      } catch (err) {
        phoneError.textContent = err.message;
      }
    });
  })();

  /* ------------------------------------------------------------- dismissing it all
     A verdict is a moment, not a page. It can be closed, and the detector, the brand
     and the Escape key all return to a clean sheet. */
  /* A verdict nobody wants any more should be one click from gone. */
  function ensureClose(card) {
    if (!card || card.querySelector(".verdict-close")) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "verdict-close";
    btn.setAttribute("aria-label", "Dismiss this verdict");
    btn.innerHTML = "\u00d7";
    btn.addEventListener("click", () => {
      if (document.body.classList.contains("verdict-open")) closeVerdict();
      else dismissResult();
    });
    card.appendChild(btn);
  }

  /* The verdict is a moment rather than a page, so it is lifted above a blurred backdrop
     when it lands, and closing it returns the visitor to a clean sheet: state cleared,
     address emptied, document reloaded so nothing stale survives. */
  let backdrop = null;

  function openVerdict(card) {
    if (!card || card.classList.contains("overlay")) return;
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.className = "verdict-backdrop";
      backdrop.addEventListener("click", () => closeVerdict());
    }
    document.body.appendChild(backdrop);
    document.body.classList.add("verdict-open");
    card.classList.add("overlay");
    // a dialog that lets Tab walk into the page behind it is not a dialog
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "true");
    card.setAttribute("aria-label", "Verdict");
    trapFocus(card);
    document.documentElement.classList.add("modal-lock");
    // keep the overlay scrollable from the top
    card.scrollTop = 0;
  }

  let releaseFocus = null;

  function trapFocus(container) {
    if (releaseFocus) releaseFocus();
    const selector = 'a[href], button:not([disabled]), summary, input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const focusables = () => Array.from(container.querySelectorAll(selector))
      .filter((el) => el.offsetParent !== null || el === document.activeElement);

    const target = container.querySelector(".verdict-close") || container;
    if (target === container) container.setAttribute("tabindex", "-1");
    setTimeout(() => target.focus({ preventScroll: true }), 30);

    const onKey = (event) => {
      if (event.key !== "Tab") return;
      const items = focusables();
      // with a single control there is nothing to cycle; let Tab leave for the browser
      if (items.length < 2) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      } else if (!container.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey, true);
    releaseFocus = () => {
      document.removeEventListener("keydown", onKey, true);
      releaseFocus = null;
    };
  }

  function closeVerdict() {
    if (releaseFocus) releaseFocus();
    const card = $("#result");
    if (backdrop) { backdrop.remove(); backdrop = null; }
    document.body.classList.remove("verdict-open");
    document.documentElement.classList.remove("modal-lock");
    if (card) card.classList.remove("overlay");
    dismissResult();
    // a real refresh, which is what "closed" should mean
    window.location.assign("/");
  }

  function dismissResult() {
    const card = $("#result");
    if (!card) return;
    card.dataset.dismissed = "1";
    cancelAnimationFrame(card._raf || 0);
    card.innerHTML = "";
    card.classList.remove("pending", "verdict-shown", "dialcoming", "zooming", "drowning");
    card.classList.add("hidden");
    document.body.classList.remove("has-result");
    $("#urlInput").value = "";
    history.replaceState({}, "", location.pathname);
  }

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    // any open dialog answers to Escape, in the order they stack
    const qr = document.getElementById("qrModal");
    if (qr && !qr.classList.contains("hidden")) {
      const close = document.getElementById("qrClose");
      if (close) close.click();
      else qr.classList.add("hidden");
      return;
    }
    const auth = document.getElementById("authModal");
    if (auth && !auth.classList.contains("hidden")) {
      auth.classList.add("hidden");
      const btn = document.getElementById("authBtn");
      if (btn) btn.focus();
      return;
    }
    if (document.body.classList.contains("verdict-open")) closeVerdict();
    else if (document.body.classList.contains("has-result")) dismissResult();
  });

  document.querySelectorAll('.nav a[href="#detector"], .brand').forEach((el) => {
    el.addEventListener("click", () => {
      if (document.body.classList.contains("has-result")) dismissResult();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });

  /* ------------------------------------------------------------------- PWA */
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      // updateViaCache none: the worker itself must never be served from the HTTP cache,
      // or a deploy could take days to reach a returning visitor
      navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" }).catch(() => {});
    });
  }

  /* ------------------------------------------------------------------ boot */
  route();
  refreshAccount();
  loadStats();
  loadSparkline();
  loadCorpusSize();
  watchSections();

  // Deep link: /?u=<url> pre-fills and analyses immediately, which also makes the
  // result shareable and the screen reproducible for documentation.
  const preset = new URLSearchParams(location.search).get("u");
  if (preset) {
    input.value = preset;
    location.hash = "#detector";
    form.requestSubmit();
  }
})();
