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
    let res;
    try {
      res = await fetch(path, { credentials: "same-origin", ...opts });
    } catch {
      // the browser says "Failed to fetch"; a person reads that as nothing at all
      throw new Error("Nyavu could not be reached. Check your connection and try again.");
    }
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
    if (target === "history") transit.track(loadHistory());
    if (target === "model") transit.track(loadModel());
    if (target === "detector") { transit.track(loadStats()); transit.track(loadSparkline()); }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  /* ------------------------------------------------------------------ transit
     A thin bar at the top of the page while something is actually being fetched or a view is
     changing. Research on response times is blunt: below a second a person needs no indicator,
     above a second they need to know the system is working. This page is a single-page app, so
     without it a change of view looks static even though data is arriving behind it. */
  const transit = (() => {
    const bar = document.createElement("div");
    bar.id = "transit";
    bar.setAttribute("aria-hidden", "true");
    const attach = () => { if (!bar.isConnected && document.body) document.body.appendChild(bar); };
    if (document.body) attach();
    else document.addEventListener("DOMContentLoaded", attach, { once: true });
    // the script can be parsed before <body> exists, and DOMContentLoaded may already have
    // fired by the time this runs; attaching on first use covers both cases
    window.addEventListener("load", attach, { once: true });
    let pending = 0;
    return {
      start() {
        attach();
        pending += 1;
        bar.classList.add("on");
        bar.classList.remove("done");
      },
      track(promise) {
        this.start();
        return Promise.resolve(promise).finally(() => this.done());
      },
      done() {
        pending = Math.max(0, pending - 1);
        if (pending) return;
        bar.classList.add("done");
        setTimeout(() => { bar.classList.remove("on", "done"); }, 320);
      },
    };
  })();

  /* The first visit does real work: fonts, the shell, the counters. A brief fade covers that
     work honestly and gives the page the sense of having arrived, which is what people expect of
     an application. It runs once per session, not on every navigation. */
  (function arrival() {
    let seen = false;
    try { seen = sessionStorage.getItem("nyavu.arrived") === "1"; } catch (e) { seen = false; }
    if (seen) return;
    document.documentElement.classList.add("booting");
    const settle = () => {
      document.documentElement.classList.remove("booting");
      try { sessionStorage.setItem("nyavu.arrived", "1"); } catch (e) { /* storage may be off */ }
    };
    window.addEventListener("load", () => setTimeout(settle, 420), { once: true });
    setTimeout(settle, 1600);
  })();

  function route() {
    const id = (location.hash || "#detector").slice(1);
    const target = $("#" + id) ? id : "detector";
    const current = views.find(v => v.classList.contains("active"));
    if (current && current.id === target) { afterRoute(target); return; }

    // the bar covers the transition, the view swap and the new view's data
    transit.start();
    if (canViewTransition) {
      const t = document.startViewTransition(() => applyRoute(target));
      t.finished.then(() => { afterRoute(target); transit.done(); })
        .catch(() => { afterRoute(target); transit.done(); });
    } else {
      applyRoute(target);
      afterRoute(target);
      transit.done();
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
      rememberLocally(r);
      transit.track(loadStats());
      transit.track(loadSparkline());
      transit.track(loadHistory());
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

  // the dial speaks in the signal palette; the muted tokens stay for furniture
const TONE = { high: "var(--signal-danger)", medium: "var(--signal-warn)", low: "var(--signal-safe)" };


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
     the page flow: a native modal dialog in the top layer, a scrim behind it, and a way
     out that returns everything to normal. */

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
    /* One clock for the whole examination, so its length can be changed in one place rather
       than in nine scattered literals. 10.9 seconds end to end: long enough to be watched
       without being an insult, which is what the first version got wrong at seven. */
    const SCENE = {
      start: 420,            // the address arrives on the table
      chipsFrom: 900,        // the measurements begin arriving
      chipGap: 148,          // seventeen of them, about two and a half seconds
      chipSettle: 4300,      // the strip dissolves as the dial takes over
      writeStart: 420,       // the cursor begins writing the pieces
      perPiece: 78,          // slower than before, so the writing reads as writing
      flaggedFrom: 4100,     // flagged pieces are called out
      dialFrom: 6000,        // the earliest the needle may start; it waits for the evidence
      needle: 2900,          // how long the hunt lasts, once the evidence is in
    };

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

    delay(SCENE.start, () => {
      if (autopsy) autopsy.classList.add("live");
      say("Reading the address");
    });

    /* The measurements arrive in the extractor's own order while the address is being read.
       They are the evidence the dial will summarise, so the wait shows the work instead of
       hiding it. The strip dissolves when the dial begins, because the finished card shows
       the same figures in its own place and two copies would be noise. */
    const strip = card.querySelector(".measures-strip");
    const chips = strip ? Array.from(strip.children) : [];

    /* On a phone the dissection fills the card, so a strip below it arrives out of sight.
       Moving it above the dissection on narrow screens keeps the evidence where the eye is
       while the address is being written. The desktop order is unchanged. */
    if (strip && autopsy && window.matchMedia("(max-width: 640px)").matches) {
      autopsy.parentElement.insertBefore(strip, autopsy);
    }
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const settle = () => { if (strip) strip.classList.add("settled"); };
    if (chips.length) {
      if (reduced) {
        // no choreography for anyone who asked for less movement, but the evidence still has
        // to be readable: it appears at once and stays for a beat before the verdict arrives
        chips.forEach((chip) => chip.classList.add("on"));
        if (strip) strip.classList.add("live");
      } else {
        strip.classList.add("live");
        chips.forEach((chip, index) => {
          delay(SCENE.chipsFrom + index * SCENE.chipGap, () => {
            chip.classList.add("on");
            if (index % 5 === 0 && index > 0) say(`Measuring ${index + 1} of ${chips.length}`);
          });
        });
        delay(SCENE.chipsFrom + chips.length * SCENE.chipGap + 300, () => say("Weighing the evidence"));
      }
    }

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

    const WRITE_START = SCENE.writeStart;
    const PER_MS = SCENE.perPiece;   // per piece, slow enough to watch being written

    /* Position inside the element the cursors are actually placed in. A single row needs
       only left, but a phone stacks the pieces into rows, and a cursor that tracks left
       alone then points at the wrong line while the words appear elsewhere. */
    const cursorHost = cursor ? cursor.offsetParent || autopsy : null;
    const place = (el, originX, originY) => {
      const box = el.getBoundingClientRect();
      const y = originY === undefined ? box.bottom : box.top;
      return {
        left: box.left - originX,
        top: y - originY,
        width: box.width,
      };
    };

    const line = autopsy ? autopsy.querySelector(".autopsy-line") : null;
    const lineLeft = line ? line.getBoundingClientRect().left : 0;

    /* Measured at the moment of use, never once up front: the card is still growing and the
       page scrolls to it as the examination starts, so a rect taken earlier is stale by
       hundreds of pixels and the cursor appears far above the address. */
    const hostNow = () => (cursor && cursor.offsetParent ? cursor.offsetParent : autopsy)
      .getBoundingClientRect();

    const textBottom = (el) => {
      const words = el.querySelector(".seg-text") || el;
      return words.getBoundingClientRect();
    };

    /* Character by character, measured rather than assumed.

       A typewriter does not ease: each keypress puts one glyph down and the carriage jumps.
       Approximating that with a fixed number of width steps and a transition on the cursor
       reads as sliding, because the eye follows the smooth motion and not the glyphs. So
       every character's right edge is measured once by handing a Range to the browser,
       which is the only way to know where a proportional font put it, and then the reveal
       and the cursor both jump to those exact positions on a fixed tick. */
    const charOffsets = (el) => {
      const node = el.firstChild;
      if (!node || node.nodeType !== Node.TEXT_NODE) return [];
      const base = el.getBoundingClientRect().left;
      const range = document.createRange();
      const offsets = [];
      for (let i = 1; i <= node.textContent.length; i++) {
        range.setStart(node, 0);
        range.setEnd(node, i);
        const box = range.getBoundingClientRect();
        offsets.push(Math.max(0, box.right - base));
      }
      range.detach && range.detach();
      return offsets;
    };

    if (cursor) {
      cursor.classList.add("on");
      if (pieces.length) {
        const box = textBottom(pieces[0].el);
        const host = hostNow();
        cursor.style.left = (box.left - host.left) + "px";
        // the writing cursor spans the words, so it is placed at their top with their height
        cursor.style.top = (box.top - host.top) + "px";
        cursor.style.height = Math.round(box.height) + "px";
      } else {
        cursor.style.left = "0px";
        cursor.style.top = "0px";
      }
    }

    let clock = WRITE_START;

    pieces.forEach((piece) => {
      const offsets = charOffsets(piece.ink);
      const chars = Math.max(offsets.length, 1);
      // 42 to 70 milliseconds per character: the range research puts typing in, and the
      // shorter the piece the brisker it can be without losing the sense of writing
      const per = Math.max(38, Math.min(62, 1400 / chars));
      const dur = chars * per;
      piece.text.style.width = "0px";

      delay(clock, () => {
        if (tag) tag.textContent = piece.role;
        piece.el.classList.add("on");
        piece.el.classList.add("writing");
      });

      for (let k = 1; k <= chars; k++) {
        delay(clock + per * k, () => {
          const offset = offsets[k - 1] || piece.ink.offsetWidth;
          piece.text.style.width = Math.round(offset) + "px";
          if (!cursor) return;
          const box = textBottom(piece.el);
          const host = hostNow();
          cursor.style.left = (box.left - host.left + offset) + "px";
          cursor.style.top = (box.top - host.top) + "px";
          cursor.style.height = Math.round(box.height) + "px";
        });
      }

      clock += dur + 90;
    });

    if (cursor) {
      delay(clock + 60, () => {
        cursor.classList.remove("on");
        if (tag) tag.textContent = "";
      });
    }

    /* The typing set each piece's width to the last glyph it reached. That width is a
       clipping box, so a long host stayed truncated once the writing finished, and printed
       or copied text was cut mid-word. The width goes back to the layout once the writing is
       over; the reveal already happened, so nothing is lost on screen. */
    pieces.forEach((piece) => {
      delay(clock, () => { piece.text.style.width = ""; });
    });
    // once written, the pieces may wrap: a sixty-character host cannot fit one phone line,
    // and clipping it would hide the very part the verdict is about
    if (autopsy) delay(clock, () => autopsy.classList.add("written"));

    /* the resolve: notes arrive from the ending backwards */
    const resolveStart = clock + 200;
    delay(resolveStart, () => {
      if (mode) { mode.textContent = "reading from the ending"; mode.dataset.state = "reading"; }
    });

    /* The cursor goes first, then the note arrives under it, the way a typist's words
       follow the caret rather than appearing beside it. Two beats per piece: move, then
       write. The gap is the caret's own travel time, so the note never overtakes it. */
    const STEP = 640;
    const WRITE_GAP = 330;

    [...segs].reverse().forEach((seg, i) => {
      const at = resolveStart + i * STEP;

      /* The caret used to travel to the next piece before the note arrived, which left two
         markers on one line: the caret ahead and the lit piece behind. With the note in its own
         panel, the lit piece is the marker, so the caret stays out of the reading. */
      delay(at + WRITE_GAP, () => {
        /* Notes accumulate. They used to replace one another, which meant that by the end of the
           examination only the last piece read had a note left: the opposite of a report. Now
           every note stays, in reading order, and the piece being read is the one lit. */
        const panel = autopsy ? autopsy.querySelector(".autopsy-panel") : null;
        segs.forEach((other) => other.classList.remove("speaking"));
        seg.classList.add("speaking");
        seg.classList.add("read");
        if (panel) {
          const item = document.createElement("li");
          item.className = "note-item";
          const word = document.createElement("span");
          word.className = "note-word";
          word.textContent = (seg.querySelector(".seg-text") || seg).textContent.trim();
          const said = document.createElement("span");
          said.className = "note-say";
          said.textContent = seg.dataset.note || "";
          item.appendChild(word);
          item.appendChild(said);
          panel.appendChild(item);
          panel.classList.add("on");
          item.scrollIntoView({ block: "nearest" });
        }
        if (mode && mode.dataset.state !== "reading") {
          mode.textContent = "reading from the ending";
          mode.dataset.state = "reading";
        }
      });
    });

    delay(resolveStart + segs.length * STEP + WRITE_GAP + 220, () => {
      if (caret) caret.classList.remove("on");
      if (autopsy) autopsy.classList.add("swept");
      /* The sweep is over: every note is on the panel, and the registered name keeps the
         highlight because it is the piece the verdict rests on. */
      segs.forEach((other) => other.classList.remove("speaking"));
      const registered = segs.find((el) => el.dataset.role === "the name");
      if (registered) {
        registered.classList.add("speaking");
        registered.classList.add("key-piece");
      }
      if (mode) {
        mode.textContent = "the name is what was registered";
        mode.dataset.state = "done";
      }
    });

    const flagged = segs.filter((el) => el.classList.contains("flag"));
    const PER_FLAG = 300;
    flagged.forEach((seg, i) => {
      delay(SCENE.flaggedFrom + i * PER_FLAG, () => {
        seg.classList.add("called");
        say("Comparing against known brands");
      });
    });

    /* The dial is the last thing to move. Its start is not a fixed number: it waits until the
       writing, the notes and the flagged pieces have all finished, so the examination ends on
       the needle settling instead of the needle talking over the evidence. */
    const writingEnd = clock;
    const notesEnd = resolveStart + segs.length * STEP + WRITE_GAP + 220;
    const flaggedEnd = flagged.length ? SCENE.flaggedFrom + (flagged.length - 1) * PER_FLAG : 0;
    const evidenceEnd = Math.max(writingEnd, notesEnd, flaggedEnd);
    const dialAt = Math.max(SCENE.dialFrom, evidenceEnd + 320);
    const dialEnds = dialAt + SCENE.needle;

    // the dial fades up shortly before it moves, so it arrives rather than waits
    delay(Math.max(0, dialAt - 900), () => {
      const fade = card.querySelector(".gauge-fade");
      if (fade) fade.classList.add("in");
    });

    delay(dialAt, () => {
      say("Weighing the evidence");
      card.classList.add("dialcoming");
      if (strip) strip.classList.add("settled");
      sweepNeedle(card, SCENE.needle);
    });

    delay(Math.max(dialAt + 400, dialEnds - 520), () => say("Reaching a verdict"));

    delay(dialEnds + 280, () => {
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
      window.__sceneEnd = performance.now();
      openVerdict(card);
    });
  }

  const TONE_OF = (v) => (v < 35 ? "#57C08A" : v < 65 ? "#E6B450" : "#EF4444");

  /* The needle makes one gesture: it rises, overshoots by a few points, and settles.
     No vibration, no dithering, and it stops dead when it arrives. */
  function sweepNeedle(root, duration = 2200) {
    const g = root.querySelector(".gauge");
    if (!g) return;
    const target = Number(g.dataset.target || 0);
    const readout = g.querySelector(".readout span");
    const caption = g.querySelector(".readout small");
    const token = ++sweepToken;

    /* Nothing on the dial reads as an answer until the needle moves. Before this, the readout
       said "clear" while the verdict was still unknown, which read as a verdict. */
    g.classList.add("armed");
    const fade = g.closest(".gauge-fade");
    if (fade) fade.classList.add("armed");
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
      // the colour follows the value the needle is passing, not the value it will reach
      g.style.setProperty("--tone", TONE_OF(t >= 1 ? target : value));
      if (readout) readout.textContent = BAND_WORD(value);
      if (t >= 1) {
        if (readout) readout.textContent = BAND_WORD(target);
        if (caption) caption.textContent = "verdict";
        g.classList.add("settled");
        return;
      }
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }




  const escapeHtml = s => String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* The score note says what the number is and how it was reached. The first two sentences
     stay on the card; the rest folds behind the plus. */
  function noteParts(note) {
    const parts = String(note).split(". ").map((x) => x.trim()).filter(Boolean);
    const withStop = (x) => (/[.!?]$/.test(x) ? x : x + ".");
    return {
      lead: parts.slice(0, 2).map(withStop).join(" "),
      tail: parts.slice(2).map(withStop).join(" "),
    };
  }

  function noteLead(note) { return noteParts(note).lead; }

  function noteTail(note) {
    const { tail, lead } = noteParts(note);
    return tail || lead;
  }

  /* The seventeen measurements, in the order the extractor computes them. The examination
     shows them arriving one at a time, so the list is the pipeline rather than decoration. */
  const FEATURE_LABELS = [
    ["domain_len", "length of the name"],
    ["num_labels", "labels in the name"],
    ["num_hyphens", "hyphens"],
    ["num_digits", "digits"],
    ["digit_ratio", "share of digits"],
    ["hyphen_ratio", "share of hyphens"],
    ["tld_len", "length of the ending"],
    ["suspicious_tld", "ending is cheap or abused"],
    ["is_ip", "host is a raw address"],
    ["is_idn", "punycode present"],
    ["entropy", "character entropy"],
    ["max_label_len", "longest label"],
    ["brand_present", "a known brand appears"],
    ["brand_in_wrong_place", "brand in the wrong place"],
    ["is_typosquat", "looks like a lookalike"],
    ["typo_distance", "distance to nearest brand"],
    ["digit_in_registrable", "digits in the name"],
  ];
  const FEATURE_HOT = new Set(["suspicious_tld", "brand_in_wrong_place", "is_typosquat", "is_ip"]);
  /* On a phone only the measurements that can move the band are worth the vertical space:
     the four that decide a verdict in practice. The rest are one tap away in the card. */
  const FEATURE_PHONE = new Set(["suspicious_tld", "brand_in_wrong_place", "is_typosquat", "is_ip"]);

  function measureStrip(features) {
    const narrow = window.matchMedia("(max-width: 640px)").matches;
    const chips = FEATURE_LABELS.map(([key, label]) => {
      const value = features && features[key] !== undefined ? features[key] : 0;
      const shown = Number.isInteger(value) ? value : Number(value).toFixed(4);
      const hot = FEATURE_HOT.has(key) && value;
      const keyish = narrow && FEATURE_PHONE.has(key);
      return `<span class="measure${hot ? " hot" : ""}${keyish ? " key" : ""}">` +
             `<b>${escapeHtml(label)}</b>${shown}</span>`;
    }).join("");
    return `<div class="measures-strip" aria-hidden="true">${chips}</div>`;
  }

  /* A band word, not a percentage. Research on confidence display is consistent: people read
     the same number differently depending on mood and situation, so the primary readout names
     the band and the number lives in the details as a frequency. */
  const BAND_WORD = (value) => (value >= 65 ? "concern" : value >= 35 ? "caution" : "clear");

  function render(r) {
    const pct = Math.round(r.probability * 100);

    /* The number is the model's estimated chance that the address is a phish, not a
       tally of faults. People reasonably expect a known-good site to read zero, so the
       card says out loud what the figure is, and why a real site still scores. */
    /* An established domain is held at a ceiling of fifteen, which is not the model's
       estimate: it is a prior applied so a known site is never flagged on the shape of its
       name. Saying "15" without saying that invites the reading "fifteen problems". */
    /* The verdict leads in words. The measurement follows, as a frequency rather than a
       percentage, because "about 1 in 5" is read more accurately than "22 out of 100". */
    const modelPct = Math.round((r.model_probability !== undefined ? r.model_probability : r.probability) * 100);
    const frequency = (value) => {
      if (value <= 1) return "less than 1 in 100";
      if (value >= 99) return "about 99 in 100";
      if (value >= 50) return `about ${Math.round(value)} in 100`;
      const oneIn = Math.max(2, Math.round(100 / value));
      return `about 1 in ${oneIn}`;
    };
    const verdictLine = r.capped_by_reputation
      ? "An established domain, so it is not flagged on the shape of its name."
      : r.risk === "high"
        ? "The name carries the marks of a phishing address."
        : r.risk === "medium"
          ? "Something about this name is worth a second look."
          : "Nothing in this name reads as phishing.";
    const scoreNote = r.capped_by_reputation
      ? `Model estimate ${frequency(modelPct === 0 ? 1 : modelPct)} (${modelPct} out of 100), held at ${pct} because the domain is established. Held at ${pct} is a reputation ceiling, not the model's estimate.`
      : `Model estimate ${frequency(pct)} (${pct} out of 100). That is the estimated chance this address is a phish, read from its name alone.`;
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

    /* All seventeen, zeros included. A reader who is told that no known brand appears is being
       told something; hiding the zero makes the list look like a fault count rather than a set of
       measurements. */
    const featRows = FEATURE_LABELS
      .map(([key, label]) => {
        const raw = r.features ? r.features[key] : undefined;
        const value = raw === undefined ? 0 : raw;
        const shown = Number.isInteger(value) ? value : Number(value).toFixed(4);
        const hot = FEATURE_HOT.has(key) && value;
        return `<div${hot ? ' class="hot"' : ""}><dt>${escapeHtml(label)}</dt><dd>${shown}</dd></div>`;
      }).join("");

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
        <div class="gauge-fade">
        <div class="gauge" style="--p:0; --tone:${TONE[r.risk]}" data-target="${pct}">
          <svg class="dial" viewBox="0 0 200 132" aria-hidden="true">
            <path class="track" d="M22 112 A78 78 0 0 1 178 112" />
            <!-- The three zones, on a thin ring outside the arc. Drawn on the arc itself they were
                 half hidden by the readout pill and the track; outside it, nothing covers them.
                 pathLength=100 lets the dash pattern be written in percent: 0 to 35 clear,
                 35 to 65 a look, above 65 a concern. -->
            <path class="band band-clear" pathLength="100" stroke-dasharray="35 65"
                  stroke-dashoffset="0" d="M14 112 A86 86 0 0 1 186 112" />
            <path class="band band-caution" pathLength="100" stroke-dasharray="30 70"
                  stroke-dashoffset="-35" d="M14 112 A86 86 0 0 1 186 112" />
            <path class="band band-concern" pathLength="100" stroke-dasharray="35 65"
                  stroke-dashoffset="-65" d="M14 112 A86 86 0 0 1 186 112" />
            <path class="fill" d="M22 112 A78 78 0 0 1 178 112" />
          </svg>
          <div class="needle"></div>
          <div class="readout"><span class="bandword">clear</span><small>band</small></div>
        </div>
        </div>
        <div class="verdict-text">
          <span class="badge ${r.risk}">${r.band}</span>${r.reputation === "established"
            ? '<span class="badge rep">Established domain</span>' : ""}
          <h2>${r.risk === "high" ? "This one is worth avoiding"
            : r.risk === "medium" ? "Worth a second look"
            : "This reads as ordinary"}</h2>
          <p class="verdict-url">${escapeHtml(r.url)}</p>
          <p class="verdict-line">${verdictLine}</p>
          <details class="score-more">
            <summary>How that was worked out</summary>
            <p class="score-note">${scoreNote}</p>
            <p class="band-legend">Bands: under 35 clear, 35 to 65 worth a look, above 65 a concern.</p>
            <h4 class="fold-title">The name, piece by piece</h4>
            ${autopsyBreakdown(r)}
            <h4 class="fold-title">What was measured</h4>
            <dl class="feat-grid all">${featRows}</dl>
          </details>
          <div class="stamp ${r.risk}" aria-hidden="true">${r.risk === "high" ? "phishing" : r.risk === "medium" ? "unsure" : "clear"}</div>
        </div>
        ${autopsyMarkup(r)}
      </div>
      <div class="thinking-row">
        <p class="thinking" id="thinking"><span class="dot"></span><span class="phase">Reading the address</span></p>
      </div>
      ${measureStrip(r.features)}
      <h3 class="block-title">${r.risk === "low"
        ? "What stood out, in a good way"
        : r.risk === "medium" ? "What gave Nyavu pause" : "What Nyavu noticed"}</h3>
      <ul class="reasons">${reasons}</ul>
      ${evidence}`;
    result._verdictHTML = result.innerHTML;
    result._target = pct;
    result.dataset.target = String(pct);
    const gauge = result.querySelector(".gauge");
    if (gauge) {
      gauge.dataset.target = String(pct);
      /* The stylesheet carries a decade of pending-state rules that fight over the dial's
         opacity. Setting the idle state inline makes the intended behaviour unambiguous: hidden
         until it arrives, then eased up by the scene. */
      /* The fade lives on a wrapper: the stylesheet carries older rules for .gauge that force its
         opacity, so anything set on the dial itself is overruled. A new parent element has no
         such history. */
      gauge.style.opacity = "";
    }
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
    finally {
      const holder = document.getElementById("spark");
      if (holder) holder.classList.remove("is-loading");
    }
  }

  async function loadStats() {
    try {
      const s = await api("/api/stats");
      // the public page carries two figures: how much has been checked here, and how much
      // the model learned on. Accusation counts and account counts are operational, and
      // they belong to the signed-in view rather than the front door.
      countUp($("#statTotal"), s.total_scans);
    } catch { /* non-critical */ }
    finally {
      const strip = document.getElementById("statsStrip");
      if (strip) strip.classList.remove("is-loading");
    }
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


  /* ------------------------------------------------- device-only history */
  /* Most people will never create an account, and a History tab that is always empty is a
     dead tab. These entries live in this browser's storage only: nothing is posted, nothing
     is keyed to a person, and Forget removes them. The server's behaviour is unchanged. */
  const LOCAL_KEY = "nyavu.recent.v1";
  const LOCAL_LIMIT = 25;

  function readLocal() {
    try {
      const raw = localStorage.getItem(LOCAL_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function rememberLocally(result) {
    try {
      const entry = {
        at: new Date().toISOString(),
        host: result.host || result.url,
        url: result.url,
        verdict: result.verdict,
        risk: result.risk,
        probability: result.probability,
      };
      const next = [entry, ...readLocal()].slice(0, LOCAL_LIMIT);
      localStorage.setItem(LOCAL_KEY, JSON.stringify(next));
    } catch (e) {
      // storage can be full or blocked; a failed convenience must not break a scan
    }
  }

  function forgetLocal() {
    try {
      localStorage.removeItem(LOCAL_KEY);
    } catch (e) {
      // nothing to do
    }
  }

  async function loadHistory() {
    const tbody = $("#historyTable tbody");
    const empty = $("#historyEmpty");
    try {
      let { items } = await api("/api/history?limit=25");
      let onDevice = false;
      if (!items.length) {
        // no account, or an account with nothing yet: show what this browser remembers
        items = readLocal().map(entry => ({
          created_at: entry.at,
          url: entry.url,
          host: entry.host,
          verdict: entry.verdict,
          risk: entry.risk,
          probability: entry.probability,
        }));
        onDevice = items.length > 0;
      }
      const note = $("#historyNote");
      if (note) {
        note.textContent = onDevice
          ? "Kept in this browser only. Nothing was sent to Nyavu, and Forget removes them."
          : "Your most recent URL checks.";
      }
      const forget = $("#historyForget");
      if (forget) forget.classList.toggle("hidden", !onDevice);

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

  document.addEventListener("click", (event) => {
    if (event.target && event.target.id === "historyForget") {
      forgetLocal();
      transit.track(loadHistory());
    }
  });

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
        // The name is a label, not a button. Clicking it used to sign the person out,
        // which is the one action nobody expects from their own name.
        const name = $("#accountName");
        const out = $("#signOutBtn");
        btn.hidden = true;
        name.hidden = false;
        name.textContent = me.full_name || me.email;
        name.title = me.email;
        out.hidden = false;
        out.onclick = async () => {
          out.disabled = true;
          try {
            await api("/api/auth/logout", { method: "POST" });
          } finally {
            out.disabled = false;
            refreshAccount(); transit.track(loadStats()); transit.track(loadHistory());
          }
        };
        $("#historyNote").textContent = "Scans recorded against your account.";
      } else {
        btn.hidden = false;
        btn.textContent = "Sign in";
        btn.onclick = () => openAuth("login");
        const name = $("#accountName");
        const out = $("#signOutBtn");
        if (name) name.hidden = true;
        if (out) out.hidden = true;
        $("#historyNote").textContent = "Your most recent URL checks (anonymous session).";
      }
    } catch { /* ignore */ }
  }

  function openAuth() {
    mode = "login";
    authModal.classList.remove("hidden");
    const error = $("#authError");
    if (error) error.textContent = "";
    const close = $("#authClose");
    if (close) close.focus({ preventScroll: true });
  }
  $("#authClose").addEventListener("click", () => authModal.classList.add("hidden"));
  /* The panel has one method. Google's redirect is an ordinary link, so there is nothing
     to wire; the round trip comes back to "/" with ?auth= and the notice explains it. */

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
    // when Google says why, say why: "an error" is not a diagnosis
    const why = params.get("why") || "";
    const stage = params.get("stage") || "";
    const [title, detail] = result === "failed" && why
      ? ["That sign-in did not complete.",
         `Google said: ${why}${stage ? " (at " + stage + ")" : ""}.`]
      : messages[result] || ["Sign-in could not complete.", "Try again."];
    const goTo = result === "ok"
      ? '<a class="auth-notice-link" href="#history">See your checks</a>'
      : "";

    const bar = document.createElement("div");
    bar.className = "auth-notice" + (result === "ok" ? " good" : "");
    bar.innerHTML = `<strong>${title}</strong><span>${detail}</span>${goTo}
      <button type="button" aria-label="Dismiss">\u00d7</button>`;
    bar.querySelector("button").addEventListener("click", () => bar.remove());
    const main = document.querySelector("main");
    if (main) main.parentNode.insertBefore(bar, main);
    setTimeout(() => bar.classList.add("fade"), 6000);

    // the URL should not keep saying what happened
    const clean = new URL(location.href);
    clean.searchParams.delete("auth");
    clean.searchParams.delete("why");
    clean.searchParams.delete("stage");
    history.replaceState({}, "", clean.pathname + (clean.hash || ""));

    if (result === "ok") refreshAccount();
  })();

  /* ------------------------------------------------------- is Google reachable? */
  (async function initAuth() {
    const googleBtn = $("#googleBtn");
    const note = $("#authNote");
    if (!googleBtn) return;

    try {
      const methods = await fetch("/api/auth/methods").then((r) => r.json());
      if (!methods.google) {
        googleBtn.replaceWith(Object.assign(document.createElement("p"), {
          className: "auth-note",
          textContent: "Google sign-in is not configured on this deployment.",
        }));
        if (note) note.textContent = "Checking a link works without an account.";
      }
    } catch {
      /* offline: the link still works when the network returns */
    }
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
  /* The verdict is a native modal dialog, not a fixed div.

     A fixed div is only above the page as long as its z-index wins inside whatever stacking
     context it happens to sit in. A transform on any ancestor, and a view transition has
     one, is enough to trap it under the backdrop, which is the dark screen with no card.
     showModal() places the element in the browser's top layer, above everything, and gives
     focus containment and Escape for free. The blur is gone with it: a full-viewport
     backdrop-filter is known to smear on some Windows compositors, and a solid scrim reads
     better anyway. */
  let verdictHome = null;
  let verdictNext = null;

  function verdictDialog() {
    return document.getElementById("verdictDialog");
  }

  function openVerdict(card) {
    const dialog = verdictDialog();
    if (!dialog || typeof dialog.showModal !== "function" || dialog.open) return;

    verdictHome = card.parentNode;
    verdictNext = card.nextSibling;
    dialog.appendChild(card);
    card.classList.add("in-dialog");
    card.classList.remove("overlay");
    document.body.classList.add("verdict-open");

    try {
      dialog.showModal();
    } catch {
      // no top layer available: leave the verdict where it was, readable
      if (verdictHome) verdictHome.insertBefore(card, verdictNext);
      card.classList.remove("in-dialog");
      document.body.classList.remove("verdict-open");
    }
  }

  function closeVerdict() {
    const dialog = verdictDialog();
    const card = document.getElementById("result");
    if (dialog && dialog.open) dialog.close();
    if (card && verdictHome) {
      card.classList.remove("in-dialog");
      verdictHome.insertBefore(card, verdictNext);
    }
    document.body.classList.remove("verdict-open");
    dismissResult();
    window.location.assign("/");
  }

  /* Escape is the dialog's own behaviour; this only cleans up after it. Attached now rather
     than on DOMContentLoaded, which may already have fired by the time this file runs. */
  (function watchDialogEscape() {
    const attach = () => {
      const dialog = verdictDialog();
      if (!dialog || dialog.dataset.escapeWatched) return;
      dialog.dataset.escapeWatched = "1";
      dialog.addEventListener("cancel", (event) => {
        event.preventDefault();
        closeVerdict();
      });
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", attach);
    else attach();
  })();

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

  /* ------------------------------------------------------- is this page current?
     A service worker can serve yesterday's shell when a cold start outlasts its network
     timeout, and yesterday's shell asks for yesterday's stylesheet. That mixture is how a
     verdict card ended up invisible behind its own backdrop. The page now knows which build
     it is, compares against the server, and gets out of the way instead of pretending. */
  (function checkBuild() {
    const meta = document.querySelector('meta[name="nyavu-build"]');
    const mine = meta && meta.content;
    if (!mine) return;

    fetch("/api/version", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data || !data.build || data.build === mine) return;
        const key = "nyavu-reloaded-for-" + data.build;
        if (sessionStorage.getItem(key)) {
          // already tried once for this build: say so rather than reload forever
          showStaleNotice();
          return;
        }
        sessionStorage.setItem(key, "1");
        location.reload();
      })
      .catch(() => { /* offline: the cached page is the right page */ });
  })();

  function showStaleNotice() {
    if (document.querySelector(".stale-notice")) return;
    const bar = document.createElement("div");
    bar.className = "auth-notice stale-notice";
    bar.innerHTML = '<strong>A newer version is available.</strong>' +
      '<span>This page was kept offline by the browser.</span>' +
      '<button type="button">Reload</button>';
    bar.querySelector("button").addEventListener("click", () => {
      sessionStorage.clear();
      location.reload();
    });
    const main = document.querySelector("main");
    if (main) main.parentNode.insertBefore(bar, main);
  }

  /* ------------------------------------------------------------ the app build
     The download link served an old release for three versions because nothing on the page
     knew what had been built. The number is printed beside the link now. */
  (async function showAppVersion() {
    try {
      const { version } = await api("/api/app/version");
      if (!version) return;
      document.querySelectorAll("#footAppVersion, #appVersion").forEach((el) => {
        el.textContent = " " + version;
      });
    } catch { /* the link still works without the label */ }
  })();

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
  transit.track(loadStats());
  transit.track(loadSparkline());
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
