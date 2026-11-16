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
    [0.00, 246, 106, 0.26, -12],
    [0.12, 246, 106, 0.26, -12],
    [0.26, 310, 150, 0.62, 10],
    [0.34, 352, 194, 1.12, 0],
    [0.66, 355, 196, 1.16, -3],
    [0.78, 330, 168, 0.86, 5],
    [0.88, 276, 132, 0.62, -4],
    [0.94, 252, 116, 0.50, 0],
    [1.00, 252, 116, 0.50, 0],
  ];
  const HAND_A = [236, 105];
  const HAND_B = [246, 121];

  function netState(t) {
    for (let i = 0; i < NET_KEY.length - 1; i++) {
      const [t0, x0, y0, s0, r0] = NET_KEY[i];
      const [t1, x1, y1, s1, r1] = NET_KEY[i + 1];
      if (t >= t0 && t <= t1) {
        const k = (t - t0) / (t1 - t0);
        const e = k * k * (3 - 2 * k);
        return {
          x: x0 + (x1 - x0) * e,
          y: y0 + (y1 - y0) * e,
          s: s0 + (s1 - s0) * e,
          r: r0 + (r1 - r0) * e,
        };
      }
    }
    const last = NET_KEY[NET_KEY.length - 1];
    return { x: last[1], y: last[2], s: last[3], r: last[4] };
  }

  function updateNet(root, t) {
    const cloth = root.querySelector(".netcloth");
    const tether = root.querySelector(".tether");
    if (!cloth) return;
    const { x, y, s, r } = netState(t);
    cloth.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) scale(${s.toFixed(3)}) rotate(${r.toFixed(1)}deg)`;

    if (tether) {
      // the mouth of the net: the edge nearest his hands
      const half = 58 * s;
      const lift = 26 * s;
      const nl = [x - half, y - lift];
      const nr = [x + half, y - lift];
      tether.setAttribute("d",
        `M${HAND_A[0]} ${HAND_A[1]} L${nl[0].toFixed(1)} ${nl[1].toFixed(1)} ` +
        `L${nr[0].toFixed(1)} ${nr[1].toFixed(1)} L${HAND_B[0]} ${HAND_B[1]} Z`);
      // slack under water: the strip darkens as it sinks
      tether.setAttribute("fill-opacity", t > 0.3 && t < 0.7 ? "0.35" : "0.55");

      // the submerged share of the net takes the water's colour
      const wet = root.querySelector(".wetnet");
      const front = root.querySelector(".cloth.front");
      if (wet && front) {
        wet.setAttribute("d", front.getAttribute("d"));
        wet.setAttribute("transform",
          `translate(${x.toFixed(1)}, ${y.toFixed(1)}) scale(${s.toFixed(3)}) rotate(${r.toFixed(1)})`);
        wet.setAttribute("fill-opacity", t > 0.30 ? "0.82" : "0");
      }
    }
  }


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
  let activeModal = null;   // { shell, backdrop, home }

  /* The card keeps its own layout; the modal is a shell around it. Wrapping rather
     than restyling means the verdict looks exactly as designed, at any size. */
  function openVerdictModal(card) {
    closeVerdictModal(true);

    const backdrop = document.createElement("div");
    backdrop.className = "backdrop";

    const shell = document.createElement("div");
    shell.className = "modal-shell";
    shell.setAttribute("role", "dialog");
    shell.setAttribute("aria-modal", "true");
    shell.setAttribute("aria-label", "Verdict");

    const close = document.createElement("button");
    close.type = "button";
    close.className = "modal-close";
    close.textContent = "Close";
    shell.appendChild(close);

    document.body.appendChild(backdrop);
    document.body.appendChild(shell);

    const home = card.parentElement;
    shell.appendChild(card);

    requestAnimationFrame(() => {
      backdrop.classList.add("on");
      shell.classList.add("on");
      card.scrollIntoView({ block: "nearest" });
    });

    document.body.classList.add("verdict-open");
    card.classList.add("in-modal");
    activeModal = { shell, backdrop, home };

    const shut = () => closeVerdictModal();
    close.addEventListener("click", shut, { once: true });
    backdrop.addEventListener("click", shut, { once: true });
    shell.addEventListener("keydown", (e) => { if (e.key === "Escape") shut(); });
    document.addEventListener("keydown", function esc(e) {
      if (e.key !== "Escape") return;
      document.removeEventListener("keydown", esc);
      shut();
    });
  }

  function closeVerdictModal(silent) {
    if (!activeModal) return;
    const { shell, backdrop, home } = activeModal;
    activeModal = null;

    const card = shell.querySelector(".result");
    if (card) {
      card.classList.remove("in-modal");
      if (home) home.appendChild(card);
    }
    shell.classList.remove("on");
    backdrop.classList.remove("on");
    document.body.classList.remove("verdict-open");
    setTimeout(() => { shell.remove(); backdrop.remove(); }, 420);
    if (!silent) window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const BEAT = {
    throw: 2000,
    impact: 4900,
    haul: 11000,
    fish: 12500,
    react: 13500,
    zoom: 17500,
    dial: 18500,
    water: 29000,
    reveal: 35000,
    end: 41000,
  };


  /* He talks while he works. The lines are chosen by what is in the net, and they
     are written in his voice: dry, plain, never a marketing sentence. */
  /* His lines. The deck is reshuffled every scan, one lesson is slipped in, and the
     phish/fish pun belongs to the dark catch where it actually applies. */
  const LINES = {
    plain: [
      "Clean. Not a thing hiding in it.",
      "Good weight. Good shape. Off you go.",
      "Now that's a fish worth the rowing.",
      "Nothing in the belly but water. Nice.",
      "Straight as a new rope, this one.",
      "No teeth. No tricks. Just a fish.",
    ],
    odd: [
      "Hm. Half a fish.",
      "Something's off. Hold still, will you.",
      "You look like a fish. You don't feel like one.",
      "I've pulled boots out with more sense than you.",
      "Could be fine. Could be a boot. We wait.",
      "This one's wearing a disguise, I swear.",
    ],
    dark: [
      "Oi. That's not a fish.",
      "Bait. This one's bait.",
      "Teeth. Of course it has teeth.",
      "That's a phish, not a fish. One letter, whole different ocean.",
      "Careful now. It's dressed up like the real thing.",
      "See how it smiles? Fish don't smile.",
      "Beautiful scales. Shame about the teeth.",
    ],
    lesson: [
      "Nobody gives away a free catch. Remember that.",
      "It's the hyphen that gives them away. Always the hyphen.",
      "If the net looks too good, check the net.",
      "A real bank never asks you to swim out to it.",
      "Funny thing about bait: it always looks like dinner.",
      "Check the harbour, not the flag on the boat.",
    ],
  };

  function startMonologue(root) {
    const bubble = root.querySelector(".bubble");
    const scene = root.querySelector(".fishing");
    if (!bubble || !scene) return;
    const kind = scene.dataset.catch || "odd";

    /* Shuffle a deck per scan, then drop one lesson into the middle of it. The order is
       different every time, so a second scan never sounds like a re-run. */
    const deck = [...(LINES[kind] || LINES.odd)];
    for (let i = deck.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [deck[i], deck[j]] = [deck[j], deck[i]];
    }
    const lesson = LINES.lesson[Math.floor(Math.random() * LINES.lesson.length)];
    deck.splice(Math.min(2, deck.length), 0, lesson);

    const span = bubble.querySelector("span");
    let i = 0;

    const show = () => {
      if (span) span.textContent = deck[i % deck.length];
      bubble.classList.add("on");
      i += 1;
    };

    show();
    // the words change; the bubble never leaves, so there is no flicker between lines
    const cycle = setInterval(() => {
      bubble.classList.add("swap");
      setTimeout(() => { show(); bubble.classList.remove("swap"); }, 220);
    }, 3400);

    return () => { clearInterval(cycle); bubble.classList.remove("on", "swap"); };
  }

  function resetArtifacts(scene) {
    [scene.querySelector(".splash"), ...scene.querySelectorAll(".ripple")]
      .forEach((el) => {
        if (!el) return;
        el.style.animation = "none";
        el.style.opacity = "0";
      });
  }

  function burst(root) {
    const scene = root.querySelector(".fishing");
    const splash = scene && scene.querySelector(".splash");
    const rings = scene ? Array.from(scene.querySelectorAll(".ripple")) : [];
    if (!scene) return;

    const t0 = performance.now();
    const LIFE = 900;

    function frame(now) {
      const k = Math.min(1, (now - t0) / LIFE);
      if (splash) {
        splash.style.opacity = String(Math.max(0, 1 - k * k));
        splash.style.transform = `translateY(${(-10 * k).toFixed(1)}px) scale(${(1 + 0.4 * k).toFixed(2)})`;
        splash.style.transformBox = "fill-box";
        splash.style.transformOrigin = "center";
      }
      rings.forEach((r, i) => {
        const kk = Math.max(0, Math.min(1, (now - t0 - i * 120) / 800));
        r.style.opacity = kk > 0 ? String((1 - kk) * 0.7) : "0";
        r.style.transform = `scale(${(0.3 + kk * 2.4).toFixed(2)})`;
        r.style.transformBox = "fill-box";
        r.style.transformOrigin = "center";
      });
      if (k < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function drip(root) {
    const scene = root.querySelector(".fishing");
    const drops = scene ? Array.from(scene.querySelectorAll(".drip")) : [];
    if (!drops.length) return;
    const t0 = performance.now();
    function frame(now) {
      const k = Math.min(1, (now - t0) / 2600);
      drops.forEach((d, i) => {
        const kk = Math.max(0, Math.min(1, (now - t0 - i * 260) / 1400));
        d.style.opacity = kk > 0 && kk < 1 ? String(0.9 * (1 - kk)) : "0";
        d.style.transform = `translateY(${(kk * 26).toFixed(1)}px)`;
      });
      if (k < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  /* A vertical curtain of water rises over the finished scene, its ripples spreading
     outward. It holds while the card swaps behind it, then the ripples dissipate and
     the verdict is simply there. Nothing flashes; nothing crossfades. */
  function waterCurtain(root) {
    const card = root.querySelector(".result");
    if (!card) return;
    // cover the whole view, so the card and the reasons below it are both hidden
    const stage = card.closest(".view") || card;
    const water = document.createElement("div");
    water.className = "waterline";
    // real elements, not pseudo-elements: Chromium does not apply SVG filters to those
    const ca = document.createElement("div");
    ca.className = "caustic ca";
    const cb = document.createElement("div");
    cb.className = "caustic cb";
    water.appendChild(ca);
    water.appendChild(cb);
    const sheen = document.createElement("div");
    sheen.className = "sheen";
    water.appendChild(sheen);
    stage.appendChild(water);
    requestAnimationFrame(() => water.classList.add("rise"));

    setTimeout(() => {
      card.classList.remove("pending");
      card.classList.remove("zooming");
      const line = document.getElementById("thinking");
      if (line && line.parentElement) line.parentElement.remove();
      const skip = document.getElementById("skipBtn");
      if (skip) skip.remove();
      // the answer takes the stage as the water clears
      openVerdictModal(card);
    }, 8200);   // swap once the water has actually finished building

    setTimeout(() => water.classList.add("fall"), 9000);
    setTimeout(() => water.remove(), 13600);
  }

  function runScene(root) {
    const scene = root.querySelector(".fishing");
    if (!scene) return;
    resetArtifacts(scene);

    const card = root.querySelector(".result");
    const started = performance.now();
    // exposed so the verification tools can report the page's own clock rather than
    // their own, which drifts by a second per screenshot
    window.__sceneStart = started;
    window.__beatOf = (ms) => Math.round(ms);
    const done = {};

    function frame(now) {
      const elapsed = now - started;
      // the net works on its own ten seconds inside the longer scene
      const netT = Math.min(1, Math.max(0, (elapsed - BEAT.throw + 1200) / 10000));
      updateNet(root, netT);

      if (!done.impact && elapsed >= BEAT.impact) { done.impact = true; burst(root); }
      if (!done.fish && elapsed >= BEAT.fish) { done.fish = true; scene.classList.add("examine"); drip(root); }
      if (!done.react && elapsed >= BEAT.react) { done.react = true; scene.classList.add("reaction"); }
      if (!done.zoom && elapsed >= BEAT.zoom) {
        done.zoom = true;
        scene.classList.add("zoom");
        if (card) card.classList.add("dialcoming");
        done.stopTalk = startMonologue(root);
      }
      if (!done.water && elapsed >= BEAT.water) {
        done.water = true;
        if (typeof done.stopTalk === "function") done.stopTalk();
        waterCurtain(root);
        return;
      }

      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }


  const TONE_OF = (v) => (v < 35 ? "#35e0a0" : v < 65 ? "#ffb020" : "#ff4d6d");

  function sweepNeedle(root) {
    const g = root.querySelector(".gauge");
    if (!g) return;
    const target = Number(g.dataset.target || 0);
    const readout = g.querySelector(".readout span");
    const caption = g.querySelector(".readout small");

    const token = ++sweepToken;
    const pause = 18500;   // the dial wakes once the camera is on him   // the catch is in his hands here; the dial starts
    const duration = 9000;   // nine seconds of calibrating, settling as the water comes

    if (caption) caption.textContent = "examining";
    const scene = document.querySelector(".fishing");
    if (scene) scene.classList.add("go");
    updateNet(document, 0);
    runScene(document);

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
          // the card stays open: the scene has a hold and a transition still to play
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

    /* The card element survives between scans, so anything the previous run set on it
       has to be cleared here. Without this the dial arrives already visible on the
       next link, and a stale water curtain can linger under the new scene. */
    result.classList.remove("dialcoming", "zooming", "modal", "revealed");
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
            : "No warning signs found"}</h2>
          <p class="verdict-url">${escapeHtml(r.url)}</p>
          <div class="stamp ${r.risk}" aria-hidden="true">${r.risk === "high" ? "phishing" : r.risk === "medium" ? "unsure" : "clear"}</div>

        <div class="fishing" data-catch="${r.risk === "high" ? "dark" : r.risk === "medium" ? "odd" : "plain"}" aria-hidden="true">
          <svg viewBox="0 12 610 236" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="seaG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#0B3546"/>
                <stop offset="100%" stop-color="#04121A"/>
              </linearGradient>
              <radialGradient id="moonG" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#1B3A44"/>
                <stop offset="100%" stop-color="#0A1A22"/>
              </radialGradient>
              <pattern id="mesh" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="9" height="9" fill="#162B36"/>
                <path d="M0 0 V9 M0 0 H9" stroke="#4E7B8C" stroke-width="1.15" fill="none" opacity="1"/>
              </pattern>
              <clipPath id="waterBand" clipPathUnits="userSpaceOnUse">
                <rect x="0" y="172" width="610" height="88"/>
              </clipPath>
              <filter id="flutter" x="-30%" y="-30%" width="160%" height="160%">
                <feTurbulence type="fractalNoise" baseFrequency="0.014 0.022" numOctaves="2" seed="7" result="noise">
                  <animate attributeName="baseFrequency" dur="10s" repeatCount="indefinite"
                           values="0.012 0.022;0.022 0.012;0.012 0.022"/>
                </feTurbulence>
                <feDisplacementMap in="SourceGraphic" in2="noise" scale="7"
                                   xChannelSelector="R" yChannelSelector="G"/>
              </filter>
            </defs>

            <defs>
              <!-- moonlight: a cool wash from the crescent across the sky and water -->
              <radialGradient id="moonlight" cx="54%" cy="14%" r="62%">
                <stop offset="0%" stop-color="#BFE9F7" stop-opacity="0.30"/>
                <stop offset="30%" stop-color="#6FB4CE" stop-opacity="0.13"/>
                <stop offset="70%" stop-color="#1C3B4C" stop-opacity="0.04"/>
                <stop offset="100%" stop-color="#050B11" stop-opacity="0"/>
              </radialGradient>
              <!-- the water takes the moon too, from above -->
              <linearGradient id="moonwater" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#2E6D82" stop-opacity="0.55"/>
                <stop offset="100%" stop-color="#0A2430" stop-opacity="0"/>
              </linearGradient>
            </defs>
            <rect x="0" y="0" width="610" height="172" fill="#070E15"/>
            <rect x="0" y="0" width="610" height="236" fill="url(#moonlight)"/>
            <!-- a crescent: the disc with an offset disc subtracted from it.
                 Placed left of centre, because the dial owns the right of the frame. -->
            <mask id="crescent">
              <circle cx="318" cy="38" r="18" fill="#ffffff"/>
              <circle cx="310" cy="32" r="15.4" fill="#000000"/>
            </mask>
            <circle cx="318" cy="38" r="54" fill="#8FD3E8" opacity="0.05"/>
            <circle cx="318" cy="38" r="30" fill="#BFE9F7" opacity="0.06"/>
            <circle cx="318" cy="38" r="18" fill="url(#moonG)" mask="url(#crescent)"/>

            <!-- far shore: a church and a lighthouse, held back by tone, not by blur -->
            <g class="far-shore" fill="#070E14" stroke="#1B2C38" stroke-width="1.6" stroke-linejoin="round">
              <!-- church: nave, pitched roof, tower, spire -->
              <path d="M74 172 v-24 l26 -13 l26 13 v24 z"/>
              <path d="M128 172 v-34 h13 v34 z"/>
              <path d="M134.5 138 v-14 l6 -8 l6 8 v14 z"/>
              <path d="M140.5 108 v-8"/>
              <path d="M137 112 h7"/>
              <!-- a lit window, the only warmth on the shore -->
              <rect x="132" y="158" width="4" height="6" fill="#C9A45A" stroke="none" opacity="0.55"/>
            </g>

            <!-- The lighthouse sits far left, clear of the dial on the right. Attention
                 in the scene runs boat (left) -> net (centre) -> dial (right), so the
                 landmarks fill the emptier left half and never compete with the needle. -->
            <g class="far-shore" fill="#070E14" stroke="#1B2C38" stroke-width="1.6"
               stroke-linejoin="round" transform="translate(-430 0)">
              <!-- lighthouse: tapered tower, gallery, lantern, and its beam -->
              <path d="M458 172 l3 -46 h12 l3 46 z"/>
              <path d="M459 126 h19"/>
              <path d="M463 126 v-8 h11 v8 z"/>
              <path d="M464 118 h9"/>
              <path class="lamp" d="M468.5 122 m-1.6 0 a1.6 1.6 0 1 1 3.2 0 a1.6 1.6 0 1 1 -3.2 0"
                    fill="#B8F2E6" stroke="none"/>
              <path class="beam" d="M476 122 l30 -12 v24 z" fill="#8FF3E2" stroke="none" opacity="0.10"/>
            </g>

            <!-- the boat: gunwale at 150, keel at 180, waterline at 172 => a quarter under -->
            <g class="boat">
              <!-- freeboard: gunwale at 140, keel at 182, waterline at 172 -->
              <path d="M28 140 q10 30 52 38 q60 10 128 0 q34 -6 46 -38 z"
                    fill="#080F16" stroke="#33505F" stroke-width="2.4"/>
              <path d="M22 138 h258" stroke="#41616F" stroke-width="4" stroke-linecap="round"/>
              <path d="M40 146 q10 18 44 24 q54 8 112 0 q26 -4 40 -24"
                    fill="none" stroke="#27414E" stroke-width="1.4"/>
              <!-- stern post and a thwart to sit on -->
              <path d="M264 138 l6 22" stroke="#41616F" stroke-width="3.5" stroke-linecap="round"/>
              <rect x="168" y="147" width="92" height="5" rx="2.5"
                    fill="#182833" stroke="#3A5666" stroke-width="1.4"/>
            </g>

            <!-- the hull has its own small wake where it meets the surface -->
            <path class="wake" d="M26 173 q46 -5 92 0 q40 4 82 0 q18 -2 34 0"
                  fill="none" stroke="#1D4A57" stroke-width="1.6" stroke-linecap="round"/>

            <g class="fisher">
              <!-- trousers: thigh along the thwart, shin dropping to the boards -->
              <path class="trouser" d="M196 140 q22 -4 40 2 l2 12 q-22 6 -42 0 z"
                    fill="#0B141A" stroke="#3A5666" stroke-width="2"/>
              <path class="trouser" d="M232 152 q8 2 8 12 l-2 12 h-12 l2 -22 z"
                    fill="#0B141A" stroke="#3A5666" stroke-width="2"/>
              <path class="shirt" d="M198 112 q14 -16 26 0 l4 30 h-34 z"
                    fill="#0A1218" stroke="#3A5666" stroke-width="2.2"/>
              <circle class="head" cx="211" cy="100" r="10.5" fill="#0A1218" stroke="#3A5666" stroke-width="2.2"/>
              <circle class="eye" cx="213" cy="98" r="1.3" fill="#42596B"/>
              <path class="nose" d="M219 100 l5 2 l-5 1.4 z" fill="#42596B"/>
              <path class="mouth" d="M218 105 q4 1 6 -1" fill="none" stroke="#42596B" stroke-width="1.4" stroke-linecap="round"/>
              <path class="hat" d="M194 94 q17 -19 34 0 l9 5 h-52 z" fill="#0A1218" stroke="#3A5666" stroke-width="2.2"/>

              <!-- arms: upper, elbow, forearm; no filled hands -->
              <g class="arms">
                <!-- far arm: only the forearm clears the body, so the bicep is hidden -->
                <path d="M223 117 L240 110" stroke="#3A5666" stroke-width="5" fill="none" stroke-linecap="round"/>
                <path d="M212 126 L224 125" stroke="#3A5666" stroke-width="6" fill="none" stroke-linecap="round"/>
                <circle cx="224" cy="125" r="3.4" fill="#263947"/>
                <path d="M224 125 L238 120" stroke="#3A5666" stroke-width="5" fill="none" stroke-linecap="round"/>
              </g>
            </g>

            <!-- sea drawn after the boat so only the keel sits under it -->
            <rect x="0" y="172" width="610" height="88" fill="url(#seaG)"/>
            <rect x="0" y="172" width="610" height="26" fill="url(#moonwater)"/>
            <path d="M0 172 h610" stroke="#12303A" stroke-width="1.2"/>

            <circle class="ripple r1" cx="352" cy="196" r="10"/>
            <circle class="ripple r2" cx="352" cy="196" r="10"/>
            <circle class="ripple r3" cx="352" cy="196" r="10"/>

            <path class="tether" fill="url(#mesh)" fill-opacity="0.92" stroke="none" d=""/>

            <g class="netcloth" filter="url(#flutter)">
              <path class="cloth back" fill="url(#mesh)" stroke="none" fill-opacity="0.85"
                    d="M-58 -4 q8 -22 32 -25 q20 -2 27 -15 q9 13 28 15 q23 3 29 25 q-5 21 -30 23 q-22 2 -30 13 q-9 -11 -30 -13 q-27 -3 -26 -23 z"/>
              <path class="cloth front" fill="url(#mesh)" stroke="none"
                    d="M-52 2 q6 -19 28 -22 q18 -2 24 -13 q8 11 25 13 q20 3 26 22 q-4 19 -26 21 q-19 2 -26 11 q-8 -9 -26 -11 q-24 -2 -25 -21 z"/>
              <g class="drip-group" fill="#8FF3E2" stroke="none">
              <circle class="drip" cx="300" cy="150" r="1.6"/>
              <circle class="drip" cx="314" cy="156" r="1.3"/>
              <circle class="drip" cx="328" cy="150" r="1.5"/>
            </g>
            <g class="caught">
                <g class="catch-dark">
                  <path d="M-13 2 q9 -11 19 -1 q-4 8 -12 8 z" fill="#200910" stroke="#ff4d6d" stroke-width="2"/>
                  <path d="M-6 -5 l1 -7 M0 -6 l2 -7 M6 -4 l3 -6" stroke="#ff4d6d" stroke-width="2" stroke-linecap="round"/>
                </g>
                <g class="catch-odd">
                  <circle cx="0" cy="2" r="8.5" fill="#1C1608" stroke="#ffb020" stroke-width="2"/>
                  <path d="M-4 -3 q6 -6 6 5" stroke="#ffb020" stroke-width="2" fill="none" stroke-linecap="round"/>
                </g>
                <g class="catch-plain">
                  <path d="M-15 2 q10 -8 21 0 q-11 8 -21 0 z" fill="#0C2C24" stroke="#35e0a0" stroke-width="2"/>
                  <path d="M6 2 l8 -5 v10 z" fill="#0C2C24" stroke="#35e0a0" stroke-width="1.8"/>
                </g>
              </g>
            </g>

            <!-- drawn after the net, in world coordinates, so the water can show through it -->
            <g clip-path="url(#waterBand)" style="pointer-events:none">
              <path class="wetnet" fill="#12495C" fill-opacity="0.85" stroke="none"/>
            </g>
          </svg>
          <div class="bubble" aria-live="polite"><span></span></div>
          <svg class="svg-close" aria-hidden="true" style="display:none"></svg>

            <g class="wash" fill="none" stroke="#8FF3E2" stroke-width="1.4" opacity="0">
              <circle cx="352" cy="190" r="40"/>
              <circle cx="352" cy="190" r="40"/>
              <circle cx="352" cy="190" r="40"/>
            </g>
            <g class="splash">
              <path class="spike" d="M352 196 l-9 -20 M358 194 l-2 -24 M364 196 l9 -19" stroke="#B9F7EC" stroke-width="2.6" stroke-linecap="round" fill="none"/>
              <circle class="drop" cx="342" cy="172" r="2.9" fill="#B9F7EC"/>
              <circle class="drop" cx="356" cy="163" r="3.4" fill="#B9F7EC"/>
              <circle class="drop" cx="368" cy="174" r="2.6" fill="#B9F7EC"/>
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
      <h3 class="block-title">${r.risk === "low"
        ? "Why this looks fine"
        : r.risk === "medium" ? "What gave Nyavu pause" : "Why Nyavu raised a concern"}</h3>
      <ul class="reasons">${reasons}</ul>
      ${evidence}
      <details class="advanced">
        <summary>What the model measured</summary>
        <dl class="feat-grid">${featRows}</dl>
      </details>`;
    sweepNeedle(result);
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
