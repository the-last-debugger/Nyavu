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

  /* A smooth closed curve through a ring of points: quadratics through the midpoints
     of each pair. Cheap, and it gives the rim the soft, lobed edge a net actually has
     instead of a polygon. */
  function smoothClosed(pts) {
    const n = pts.length;
    const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    const m0 = mid(pts[n - 1], pts[0]);
    let d = `M${m0[0].toFixed(1)} ${m0[1].toFixed(1)}`;
    for (let i = 0; i < n; i++) {
      const p = pts[i];
      const m = mid(p, pts[(i + 1) % n]);
      d += ` Q${p[0].toFixed(1)} ${p[1].toFixed(1)} ${m[0].toFixed(1)} ${m[1].toFixed(1)}`;
    }
    return d + "Z";
  }

  /* The net is real geometry, rebuilt every frame: a canopy with a near rim and a
     far rim, so it reads as a cone of cloth rather than a flat wheel, plus rings and
     spokes and a sway driven by two slow sines. A cast net covers ground - it opens
     wide as it flies and settles over the water. */
  /* Camera move on the viewBox: exact framing, and the artwork scales with it. */
  function cameraPush(root, to, ms) {
    const svg = root.querySelector(".fishing svg");
    if (!svg) return;
    const from = (svg.getAttribute("viewBox") || "-102 -28 813 315").split(/\s+/).map(Number);
    const t0 = performance.now();
    function frame(now) {
      const k = Math.min(1, (now - t0) / ms);
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      svg.setAttribute("viewBox", from.map((a, i) => (a + (to[i] - a) * e).toFixed(1)).join(" "));
      if (k < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function updateNet(root, t) {
    const body = root.querySelector(".netlive");
    if (!body) return;

    const { x, y, s } = netState(t);
    const T = performance.now() / 1000;

    const R = 6 + 126 * s;
    const FLAT = 0.42;
    const N = 20;
    const DIP = 20 * s;
    const t2 = Math.max(0, Math.min(1, (t - 0.90) / 0.10));   // the last tenth: it is drawn in

    const rim = [];
    const far = [];
    for (let i = 0; i < N; i++) {
      const a = (i / N) * Math.PI * 2;
      // in the water the net lies still and breathes; in the air it flutters
      const inWater = t > 0.34 && t < 0.78;
      const swell = inWater ? 0.018 : 0.05;
      const chop = inWater ? 0.008 : 0.03;
      const wob = IRREG[i]
        * (1 + swell * Math.sin(a * 3 + T * (inWater ? 0.8 : 2.1))
             + chop * Math.sin(a * 5 - T * (inWater ? 0.6 : 1.6)));
      const rr = R * wob * (1 - 0.55 * t2);
      const ex = Math.cos(a);
      const ey = Math.sin(a);
      const lift = -DIP * ey;
      rim.push([x + rr * ex, y + rr * FLAT * ey + lift + Math.sin(a + T * 1.25) * 3 * s]);
      far.push([x + rr * 0.60 * ex, y - rr * FLAT * 0.55 * ey - DIP * 0.8 + Math.sin(a - T * 1.1) * 2 * s]);
    }

    const fill = body.querySelector(".net-fill");
    if (fill) fill.setAttribute("d", smoothClosed(rim) + smoothClosed(far));

    // spokes, cross-links and rings: enough lines to read as holes, not a scaffold
    const hub = [x, y - DIP * 1.5 - R * 0.10];
    let d = "";
    for (let i = 0; i < N; i++) {
      const p = rim[i];
      const f = far[i];
      const n = rim[(i + 1) % N];
      d += `M${hub[0].toFixed(1)} ${hub[1].toFixed(1)}` +
           ` Q${((hub[0] + p[0]) / 2 + Math.sin(T * 1.6) * 2).toFixed(1)}` +
           ` ${((hub[1] + p[1]) / 2 + 2).toFixed(1)}` +
           ` ${p[0].toFixed(1)} ${p[1].toFixed(1)}`;
      d += `M${f[0].toFixed(1)} ${f[1].toFixed(1)} L${p[0].toFixed(1)} ${p[1].toFixed(1)}`;
      // a diagonal cross-link, so the interior is diamonds rather than wedges
      d += `M${f[0].toFixed(1)} ${f[1].toFixed(1)} L${n[0].toFixed(1)} ${n[1].toFixed(1)}`;
    }
    [0.20, 0.36, 0.52, 0.68, 0.84].forEach((k, idx) => {
      const ring = rim.map(([px, py]) => [
        hub[0] + (px - hub[0]) * k,
        hub[1] + (py - hub[1]) * k + Math.sin(T * 1.1 + idx * 1.7) * 2,
      ]);
      d += smoothClosed(ring);
    });
    const mesh = body.querySelector(".net-mesh");
    if (mesh) mesh.setAttribute("d", d);

    // from the last tenth the net is gone, but the catch is not: fade the cloth only
    const delivered = t2 >= 1;
    const scene = root.querySelector(".fishing");
    if (scene) {
      // it looks like a fish until it is in his hands, then it shows what it is
      scene.classList.toggle("revealed", t2 > 0.55);
      scene.classList.toggle("delivered", t2 > 0.55);
    }
    const clothFade = String(Math.max(0, 1 - t2 * 1.6));
    [fill, mesh].forEach((el) => { if (el) el.style.opacity = clothFade; });

    const caught = root.querySelector(".caught");
    if (caught && !catchEscaping) {
      if (delivered || t2 > 0.55) {
        // held up in front of him, still twitching but no longer thrashing
        const jx = Math.sin(T * 9) * 1.2;
        const jy = Math.cos(T * 11) * 1.2;
        // held up at the 20th size: from here on, the catch is the only subject
        caught.style.setProperty("transform",
          `translate(${(HAND_A[0] + 14 + jx).toFixed(1)}px, ${(HAND_A[1] + 2 + jy).toFixed(1)}px) ` +
          `rotate(${(Math.sin(T * 7) * 6).toFixed(1)}deg) scale(1.15)`, "important");
        caught.setAttribute("visibility", "visible");
        caught.style.opacity = "1";
      } else {
        const onWater = t > 0.40 && t < 0.78;
        const amp = onWater ? 7 : 2.5;
        const jx = Math.sin(T * 12) * amp + Math.sin(T * 19.3) * amp * 0.55;
        const jy = Math.cos(T * 14.7) * amp + Math.sin(T * 8.1) * amp * 0.45;
        const rot = onWater ? Math.sin(T * 11) * 34 : Math.sin(T * 16) * 12;
        // a real fish inside a real net: big enough to see, and only once it is caught
        const visible = t > 0.30;
        const size = (0.95 + 0.25 * Math.min(1, s)).toFixed(2);
        // variables, not a transform string: CSS composes it, so nothing can clobber it
        // inline !important: a running CSS animation would otherwise win over this
        caught.style.setProperty("transform",
          `translate(${(x + jx).toFixed(1)}px, ${(y + 8 * s + jy).toFixed(1)}px) ` +
          `rotate(${rot.toFixed(1)}deg) scale(${size})`, "important");
        caught.setAttribute("visibility", visible ? "visible" : "hidden");
        caught.style.opacity = "1";
      }
    }

    /* The rope joins the grip of his hands to the crown of the net. Measured between
       those two points, it appears as the net leaves him and shortens by itself as it
       is drawn back - no separate animation to keep in step. */
    const ropeGroup = root.querySelector(".ropeline");
    const rope = root.querySelector(".rope");
    const ropeHi = root.querySelector(".rope-hi");
    if (ropeGroup && rope) {
      const grip = [(HAND_A[0] + HAND_B[0]) / 2, (HAND_A[1] + HAND_B[1]) / 2];
      const span = Math.hypot(hub[0] - grip[0], hub[1] - grip[1]);
      ropeGroup.style.opacity = span > 8 && t < 0.97 ? "1" : "0";

      const sag = Math.min(16, span * 0.2);
      const cxp = (grip[0] + hub[0]) / 2;
      const cyp = (grip[1] + hub[1]) / 2 + sag;
      const d = `M${grip[0].toFixed(1)} ${grip[1].toFixed(1)}`
              + ` Q${cxp.toFixed(1)} ${cyp.toFixed(1)} ${hub[0].toFixed(1)} ${hub[1].toFixed(1)}`;
      rope.setAttribute("d", d);
      if (ropeHi) ropeHi.setAttribute("d", d);
    }

    const wet = root.querySelector(".wetnet");
    if (wet) {
      wet.setAttribute("d", smoothClosed(rim));
      wet.setAttribute("fill-opacity", t > 0.34 ? "0.8" : "0");
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

  /* The card keeps its own layout; the modal is a shell around it. Wrapping rather
     than restyling means the verdict looks exactly as designed, at any size. */
  const BEAT = {
    ready: 1200,      // he says his line; the net is still out of sight
    throw: 3200,
    impact: 4900,
    haul: 11000,
    fish: 12500,
    react: 13500,
    zoom: 17500,
    dial: 18500,
    drown: 21500,
    outro: 29000,
    reveal: 33000,
    end: 41000,
  };


  /* He talks while he works. The lines are chosen by what is in the net, and they
     are written in his voice: dry, plain, never a marketing sentence. */
  /* He speaks before he works. */
  const OPENERS = [
    "Here we go again.",
    "Right. Let's see what the sea brought us.",
    "Another one. Hold my hat.",
    "Same water, new trouble.",
    "Night shift. Nobody's watching.",
    "Let's see who's wearing a costume tonight.",
    "Off we go. Mind the wet.",
    "The sea keeps its secrets. Not for long.",
    "One more cast, then I'm done. I always say that.",
    "Wind's wrong for it. Doesn't matter.",
  ];

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
      "Honest scales. You don't see many.",
      "Swims true. I'd put my name on it.",
      "Nothing here a taxman would argue with.",
      "Clean as the day it was made.",
    ],
    odd: [
      "Hm. Half a fish.",
      "Something's off. Hold still, will you.",
      "You look like a fish. You don't feel like one.",
      "I've pulled boots out with more sense than you.",
      "Could be fine. Could be a boot. We wait.",
      "This one's wearing a disguise, I swear.",
      "Fins say yes. Face says no.",
      "I'll be honest with you: I don't know.",
      "Fifty-fifty. Like a coin in the harbour.",
      "I've seen this face before. Can't place it.",
    ],
    dark: [
      "Oi. That's not a fish.",
      "Bait. This one's bait.",
      "Teeth. Of course it has teeth.",
      "That's a phish, not a fish. One letter, whole different ocean.",
      "Careful now. It's dressed up like the real thing.",
      "See how it smiles? Fish don't smile.",
      "Beautiful scales. Shame about the teeth.",
      "It's got the bank's colours on. It's not the bank.",
      "Nice hat. Wrong fisherman.",
      "It swam up wearing somebody else's name.",
    ],
    lesson: [
      "Nobody gives away a free catch. Remember that.",
      "It's the hyphen that gives them away. Always the hyphen.",
      "If the net looks too good, check the net.",
      "A real bank never asks you to swim out to it.",
      "Funny thing about bait: it always looks like dinner.",
      "Check the harbour, not the flag on the boat.",
      "One letter moved is a whole new harbour.",
      "The address is the boat. Look at the boat, not the paint.",
      "Free things in the water are usually attached to something.",
      "If they hurry you, they're selling, not helping.",
      "A .tk doesn't cost enough to be a bank.",
      "Nobody legitimate asks for your net before you've seen the fish.",
    ],
  };
  /* He speaks twice while he works and twice while he examines - each line placed on a
     beat so the words and the action agree. The outcome-specific lines do not begin
     until the catch is in his hands, so the verdict is never given away early. */
  function shuffled(list, n) {
    const deck = [...list];
    for (let i = deck.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [deck[i], deck[j]] = [deck[j], deck[i]];
    }
    return deck.slice(0, n);
  }

  function say(root, text) {
    const bubble = root.querySelector(".bubble");
    if (!bubble || !text) return;
    const span = bubble.querySelector("span");
    if (span) span.textContent = text;
    bubble.classList.add("on", "swap");
    setTimeout(() => bubble.classList.remove("swap"), 180);
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
  function fishEscapes(root) {
    const caught = root.querySelector(".caught");
    if (!caught) return;
    catchEscaping = true;
    const from = [HAND_A[0] + 14, HAND_A[1] + 2];
    const t0 = performance.now();

    function frame(now) {
      const k = Math.min(1, (now - t0) / 2400);
      const x = from[0] + 120 * k;
      const y = from[1] - 70 * Math.sin(Math.PI * Math.min(1, k * 1.1)) + 150 * k * k;
      const spin = 220 * k;
      caught.style.setProperty("transform",
        `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) rotate(${spin.toFixed(1)}deg) scale(1.15)`,
        "important");
      caught.style.setProperty("opacity", String(Math.max(0, 1 - Math.max(0, k - 0.75) * 4)), "important");
      if (k < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function handOver(root) {
    const scene = root.querySelector(".fishing");
    const card = root.querySelector(".result");
    if (!card) return;

    const verdict = card._verdictHTML || "";
    const target = card._target || 0;

    if (scene) {
      scene.style.transition = "opacity .5s cubic-bezier(.4,0,.2,1)";
      scene.style.opacity = "0";
    }

    // hold the card's height through the swap, or the page jumps beneath the reader
    const held = Math.round(card.getBoundingClientRect().height);
    card.style.minHeight = `${held}px`;

    setTimeout(() => {
      // the card's own contents become the skeleton: identical box, identical flow
      card.innerHTML = `
        <div class="verdict-skeleton inplace" aria-hidden="true">
          <div class="sk-head">
            <span class="sk sk-gauge"></span>
            <div class="sk-body">
              <span class="sk sk-badge"></span>
              <span class="sk sk-title"></span>
              <span class="sk sk-url"></span>
              <span class="sk sk-suggest"></span>
              <span class="sk sk-meta"></span>
            </div>
          </div>
          <span class="sk sk-subtitle"></span>
          <span class="sk sk-row"></span>
          <span class="sk sk-row"></span>
          <span class="sk sk-row"></span>
        </div>`;

      setTimeout(() => {
        card.innerHTML = verdict;
        ensureClose(card);
        card.classList.add("verdict-shown");
        card.classList.remove("pending");
        card.classList.remove("zooming");
        const g = card.querySelector(".gauge");
        if (g) {
          g.style.setProperty("--p", target);
          const ro = card.querySelector(".readout span");
          if (ro) ro.textContent = target;
          const cap = card.querySelector(".readout small");
          if (cap) cap.textContent = "risk";
          g.style.setProperty("--tone", TONE_OF(target));
        }
        normaliseCard(card);
        const line = document.getElementById("thinking");
        if (line && line.parentElement) line.parentElement.remove();
        // the verdict is taller than the skeleton; release the pin once it is in
        requestAnimationFrame(() => { card.style.minHeight = ""; });
      }, 900);
    }, 380);
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

    /* two lines for the work, two for the examination, each on a beat */
    const kind = scene.dataset.catch || "odd";
    const intro = shuffled(OPENERS, 2);
    const exam = shuffled(LINES[kind] || LINES.odd, 2);

    const bubble = scene.querySelector(".bubble");
    if (bubble) {
      const span = bubble.querySelector("span");
      if (span) span.textContent = intro[0];
      bubble.classList.add("on");
    }

    function frame(now) {
      const elapsed = now - started;
      // the net works on its own ten seconds inside the longer scene
      const netT = Math.min(1, Math.max(0, (elapsed - BEAT.throw + 1200) / 10000));
      if (scene) scene.classList.toggle("castable", elapsed >= BEAT.ready);
      updateNet(root, elapsed >= BEAT.ready ? netT : 0);

      if (!done.impact && elapsed >= BEAT.impact) {
        done.impact = true;
        burst(root);
        say(root, intro[1]);            // the second line, as the net settles
      }
      if (!done.fish && elapsed >= BEAT.fish) {
        done.fish = true;
        scene.classList.add("examine");
        drip(root);
        say(root, exam[0]);              // the catch is in his hands; now he speaks to it
      }
      if (!done.react && elapsed >= BEAT.react) {
        done.react = true;
        scene.classList.add("reaction");
      }
      if (!done.zoom && elapsed >= BEAT.zoom) {
        done.zoom = true;
        // a phone sees a narrower slice of the same viewBox, so the push is gentler
        // there and wide enough to hold both the fisherman and the crescent
        const target = window.innerWidth < 700
          ? [52, 6, 630, 250]
          : [78, 20, 542, 210];
        cameraPush(root, target, 2400);
        if (card) card.classList.add("dialcoming");
        say(root, exam[1]);               // his second thought, as the camera moves in
      }
      if (!done.drown && elapsed >= BEAT.drown) {
        done.drown = true;
        if (scene.dataset.catch === "dark") {
          // only the phish frightens him; on a clean or unsure catch he keeps talking
          const b = root.querySelector(".bubble");
          if (b) b.classList.remove("on");
          scene.classList.add("drowning");
          setTimeout(() => fishEscapes(root), 700);
        }
      }
      if (!done.outro && elapsed >= BEAT.outro) {
        done.outro = true;
        if (typeof done.stopTalk === "function") done.stopTalk();
        handOver(root);
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
            : "No warning signs found"}</h2>
          <p class="verdict-url">${escapeHtml(r.url)}</p>
          <div class="stamp ${r.risk}" aria-hidden="true">${r.risk === "high" ? "phishing" : r.risk === "medium" ? "unsure" : "clear"}</div>

        <div class="fishing" data-catch="${r.risk === "high" ? "dark" : r.risk === "medium" ? "odd" : "plain"}" aria-hidden="true">
          <svg viewBox="-102 -28 813 315" preserveAspectRatio="xMidYMid slice">
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
                <rect x="-110" y="172" width="840" height="130"/>
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

            <rect x="-110" y="-40" width="840" height="212" fill="#070E15"/>
            <rect x="-110" y="-40" width="840" height="330" fill="url(#moonlight)"/>

            <mask id="crescent">
              <circle cx="602" cy="30" r="17" fill="#ffffff"/>
              <circle cx="595" cy="25" r="14.6" fill="#000000"/>
            </mask>
            <!-- dust: a few specks caught in the light -->
            <g fill="#EAF8FF" opacity="0.55">
              <circle cx="626" cy="18" r="1.1"/><circle cx="634" cy="30" r="0.8"/>
              <circle cx="618" cy="44" r="1"/><circle cx="640" cy="14" r="0.7"/>
              <circle cx="612" cy="8" r="0.9"/><circle cx="646" cy="38" r="0.6"/>
            </g>
            <circle cx="602" cy="30" r="17" fill="#F2FBFF" mask="url(#crescent)"/>

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

            <g class="boat">
              <!-- freeboard: gunwale at 140, keel at 182, waterline at 172 -->
              <path d="M28 140 q10 30 52 38 q60 10 128 0 q34 -6 46 -38 z"
                    fill="#080F16" stroke="#33505F" stroke-width="2.4"/>
              <path d="M22 138 h258" stroke="#41616F" stroke-width="4" stroke-linecap="round"/>
              <path d="M40 146 q10 18 44 24 q54 8 112 0 q26 -4 40 -24"
                    fill="none" stroke="#27414E" stroke-width="1.4"/>
              <!-- her registration, painted along the strake -->
              <defs>
                <path id="hullMarkLine" d="M96 150 q54 9 142 -1" fill="none"/>
              </defs>
              <text class="hull-mark" font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
                    font-size="9" letter-spacing="2.2" fill="#6E9FB2" opacity="0.85">
                <textPath href="#hullMarkLine" startOffset="0">NYAVU APD</textPath>
              </text>

              <!-- stern post and a thwart to sit on -->
              <path d="M264 138 l6 22" stroke="#41616F" stroke-width="3.5" stroke-linecap="round"/>
              <rect x="168" y="147" width="92" height="5" rx="2.5"
                    fill="#182833" stroke="#3A5666" stroke-width="1.4"/>
            </g>

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

            <!-- the sea is drawn after the boat, so only the keel sits under it -->
            <rect x="-110" y="172" width="840" height="130" fill="url(#seaG)"/>
            <rect x="-110" y="172" width="840" height="26" fill="url(#moonwater)"/>
            <path d="M-110 172 h840" stroke="#12303A" stroke-width="1.2"/>
            <g class="wavelayer wl1" style="--tile:780px">
              <path d="M0 173.5 L11 175.2 L22 176.4 L32 176.9 L43 176.4 L54 175.2 L65 173.5 L76 171.8 L87 170.6 L97 170.1 L108 170.6 L119 171.8 L130 173.5 L141 175.2 L152 176.4 L162 176.9 L173 176.4 L184 175.2 L195 173.5 L206 171.8 L217 170.6 L228 170.1 L238 170.6 L249 171.8 L260 173.5 L271 175.2 L282 176.4 L292 176.9 L303 176.4 L314 175.2 L325 173.5 L336 171.8 L347 170.6 L357 170.1 L368 170.6 L379 171.8 L390 173.5 L401 175.2 L412 176.4 L422 176.9 L433 176.4 L444 175.2 L455 173.5 L466 171.8 L477 170.6 L487 170.1 L498 170.6 L509 171.8 L520 173.5 L531 175.2 L542 176.4 L552 176.9 L563 176.4 L574 175.2 L585 173.5 L596 171.8 L607 170.6 L618 170.1 L628 170.6 L639 171.8 L650 173.5 L661 175.2 L672 176.4 L683 176.9 L693 176.4 L704 175.2 L715 173.5 L726 171.8 L737 170.6 L748 170.1 L758 170.6 L769 171.8 L780 173.5" fill="none" stroke="#2F7186" stroke-width="1.50" opacity="0.55"/>
              <path d="M0 173.5 L11 175.2 L22 176.4 L32 176.9 L43 176.4 L54 175.2 L65 173.5 L76 171.8 L87 170.6 L97 170.1 L108 170.6 L119 171.8 L130 173.5 L141 175.2 L152 176.4 L162 176.9 L173 176.4 L184 175.2 L195 173.5 L206 171.8 L217 170.6 L228 170.1 L238 170.6 L249 171.8 L260 173.5 L271 175.2 L282 176.4 L292 176.9 L303 176.4 L314 175.2 L325 173.5 L336 171.8 L347 170.6 L357 170.1 L368 170.6 L379 171.8 L390 173.5 L401 175.2 L412 176.4 L422 176.9 L433 176.4 L444 175.2 L455 173.5 L466 171.8 L477 170.6 L487 170.1 L498 170.6 L509 171.8 L520 173.5 L531 175.2 L542 176.4 L552 176.9 L563 176.4 L574 175.2 L585 173.5 L596 171.8 L607 170.6 L618 170.1 L628 170.6 L639 171.8 L650 173.5 L661 175.2 L672 176.4 L683 176.9 L693 176.4 L704 175.2 L715 173.5 L726 171.8 L737 170.6 L748 170.1 L758 170.6 L769 171.8 L780 173.5" transform="translate(780 0)" fill="none" stroke="#2F7186" stroke-width="1.50" opacity="0.55"/>
            </g>
            <g class="wavelayer wl2" style="--tile:1020px">
              <path d="M0 179.0 L14 178.2 L28 177.0 L42 175.7 L57 174.5 L71 173.9 L85 174.0 L99 174.8 L113 176.0 L128 177.3 L142 178.5 L156 179.1 L170 179.0 L184 178.2 L198 177.0 L212 175.7 L227 174.5 L241 173.9 L255 174.0 L269 174.8 L283 176.0 L298 177.3 L312 178.5 L326 179.1 L340 179.0 L354 178.2 L368 177.0 L383 175.7 L397 174.5 L411 173.9 L425 174.0 L439 174.8 L453 176.0 L468 177.3 L482 178.5 L496 179.1 L510 179.0 L524 178.2 L538 177.0 L553 175.7 L567 174.5 L581 173.9 L595 174.0 L609 174.8 L623 176.0 L638 177.3 L652 178.5 L666 179.1 L680 179.0 L694 178.2 L708 177.0 L722 175.7 L737 174.5 L751 173.9 L765 174.0 L779 174.8 L793 176.0 L807 177.3 L822 178.5 L836 179.1 L850 179.0 L864 178.2 L878 177.0 L892 175.7 L907 174.5 L921 173.9 L935 174.0 L949 174.8 L963 176.0 L977 177.3 L992 178.5 L1006 179.1 L1020 179.0" fill="none" stroke="#2F7186" stroke-width="1.20" opacity="0.4"/>
              <path d="M0 179.0 L14 178.2 L28 177.0 L42 175.7 L57 174.5 L71 173.9 L85 174.0 L99 174.8 L113 176.0 L128 177.3 L142 178.5 L156 179.1 L170 179.0 L184 178.2 L198 177.0 L212 175.7 L227 174.5 L241 173.9 L255 174.0 L269 174.8 L283 176.0 L298 177.3 L312 178.5 L326 179.1 L340 179.0 L354 178.2 L368 177.0 L383 175.7 L397 174.5 L411 173.9 L425 174.0 L439 174.8 L453 176.0 L468 177.3 L482 178.5 L496 179.1 L510 179.0 L524 178.2 L538 177.0 L553 175.7 L567 174.5 L581 173.9 L595 174.0 L609 174.8 L623 176.0 L638 177.3 L652 178.5 L666 179.1 L680 179.0 L694 178.2 L708 177.0 L722 175.7 L737 174.5 L751 173.9 L765 174.0 L779 174.8 L793 176.0 L807 177.3 L822 178.5 L836 179.1 L850 179.0 L864 178.2 L878 177.0 L892 175.7 L907 174.5 L921 173.9 L935 174.0 L949 174.8 L963 176.0 L977 177.3 L992 178.5 L1006 179.1 L1020 179.0" transform="translate(1020 0)" fill="none" stroke="#2F7186" stroke-width="1.20" opacity="0.4"/>
            </g>
            <g class="wavelayer wl3" style="--tile:1320px">
              <path d="M0 179.3 L18 178.7 L37 178.6 L55 179.0 L73 179.8 L92 180.8 L110 181.7 L128 182.3 L147 182.4 L165 182.0 L183 181.2 L202 180.2 L220 179.3 L238 178.7 L257 178.6 L275 179.0 L293 179.8 L312 180.8 L330 181.7 L348 182.3 L367 182.4 L385 182.0 L403 181.2 L422 180.2 L440 179.3 L458 178.7 L477 178.6 L495 179.0 L513 179.8 L532 180.8 L550 181.7 L568 182.3 L587 182.4 L605 182.0 L623 181.2 L642 180.2 L660 179.3 L678 178.7 L697 178.6 L715 179.0 L733 179.8 L752 180.8 L770 181.7 L788 182.3 L807 182.4 L825 182.0 L843 181.2 L862 180.2 L880 179.3 L898 178.7 L917 178.6 L935 179.0 L953 179.8 L972 180.8 L990 181.7 L1008 182.3 L1027 182.4 L1045 182.0 L1063 181.2 L1082 180.2 L1100 179.3 L1118 178.7 L1137 178.6 L1155 179.0 L1173 179.8 L1192 180.8 L1210 181.7 L1228 182.3 L1247 182.4 L1265 182.0 L1283 181.2 L1302 180.2 L1320 179.3" fill="none" stroke="#2F7186" stroke-width="0.90" opacity="0.28"/>
              <path d="M0 179.3 L18 178.7 L37 178.6 L55 179.0 L73 179.8 L92 180.8 L110 181.7 L128 182.3 L147 182.4 L165 182.0 L183 181.2 L202 180.2 L220 179.3 L238 178.7 L257 178.6 L275 179.0 L293 179.8 L312 180.8 L330 181.7 L348 182.3 L367 182.4 L385 182.0 L403 181.2 L422 180.2 L440 179.3 L458 178.7 L477 178.6 L495 179.0 L513 179.8 L532 180.8 L550 181.7 L568 182.3 L587 182.4 L605 182.0 L623 181.2 L642 180.2 L660 179.3 L678 178.7 L697 178.6 L715 179.0 L733 179.8 L752 180.8 L770 181.7 L788 182.3 L807 182.4 L825 182.0 L843 181.2 L862 180.2 L880 179.3 L898 178.7 L917 178.6 L935 179.0 L953 179.8 L972 180.8 L990 181.7 L1008 182.3 L1027 182.4 L1045 182.0 L1063 181.2 L1082 180.2 L1100 179.3 L1118 178.7 L1137 178.6 L1155 179.0 L1173 179.8 L1192 180.8 L1210 181.7 L1228 182.3 L1247 182.4 L1265 182.0 L1283 181.2 L1302 180.2 L1320 179.3" transform="translate(1320 0)" fill="none" stroke="#2F7186" stroke-width="0.90" opacity="0.28"/>
            </g>

            <circle class="ripple r1" cx="352" cy="196" r="10"/>
            <circle class="ripple r2" cx="352" cy="196" r="10"/>
            <circle class="ripple r3" cx="352" cy="196" r="10"/>

            <g class="ropeline">
              <path class="rope" fill="none" stroke="#16232B" stroke-width="3" stroke-linecap="round" d=""/>
              <path class="rope-hi" fill="none" stroke="#5C8A9C" stroke-width="1" stroke-linecap="round" opacity="0.55" d=""/>
            </g>

            <g class="netlive">
              <path class="net-fill" fill="url(#mesh)" fill-opacity="0.96" stroke="none" d=""/>
              <path class="net-mesh" fill="none" stroke="#4E7B8C" stroke-width="0.9" stroke-opacity="0.85" d=""/>
              <g class="drip-group" fill="#8FF3E2" stroke="none">
                <circle class="drip" cx="300" cy="150" r="1.6"/>
                <circle class="drip" cx="314" cy="156" r="1.3"/>
                <circle class="drip" cx="328" cy="150" r="1.5"/>
              </g>
            </g>

            <g class="caught">
              <circle class="catch-halo" r="17" fill="rgba(3, 9, 13, .55)"/>
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

            <g clip-path="url(#waterBand)" style="pointer-events:none">
              <path class="wetnet" fill="#12495C" fill-opacity="0.85" stroke="none"/>
            </g>

            <g class="splash">
              <path class="spike" d="M352 196 l-9 -20 M358 194 l-2 -24 M364 196 l9 -19" stroke="#B9F7EC" stroke-width="2.6" stroke-linecap="round" fill="none"/>
              <circle class="drop" cx="342" cy="172" r="2.9" fill="#B9F7EC"/>
              <circle class="drop" cx="356" cy="163" r="3.4" fill="#B9F7EC"/>
              <circle class="drop" cx="368" cy="174" r="2.6" fill="#B9F7EC"/>
            </g>
          </svg>
          <div class="bubble" aria-live="polite"><span></span></div>
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
    result._verdictHTML = result.innerHTML;
    result._target = pct;
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
          <td><span class="pill ${it.risk}">${escapeHtml(it.verdict)}</span></td>
          <td>${(it.probability * 100).toFixed(1)}%</td>
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
        <h3 class="block-title">Full comparison — domain-disjoint hold-out set</h3>
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
          <thead><tr><th>Host</th><th>Verdict</th><th>Score</th></tr></thead>
          <tbody>${r.results.map(x => `
            <tr><td title="${escapeHtml(x.url)}">${escapeHtml(x.host || x.url)}</td>
            <td><span class="pill ${x.risk}">${escapeHtml(x.verdict)}</span></td>
            <td>${x.probability === null ? "—" : (x.probability * 100).toFixed(1) + "%"}</td></tr>`).join("")}
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
    btn.addEventListener("click", () => dismissResult());
    card.appendChild(btn);
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
    if (e.key === "Escape" && document.body.classList.contains("has-result")) {
      dismissResult();
    }
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
