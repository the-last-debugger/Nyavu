/*
 * Prototype of the examination, as a piece of considered work rather than a form submission.
 *
 * The rule the whole thing obeys: content comes from the model, pacing comes from here. Every
 * number, every measurement and every sentence in the verdict is read out of the /api/predict
 * response. Nothing is invented to look busier.
 *
 * Why the pacing looks like this, from the research:
 *  - a wait feels shorter when there is something to watch (the elevator mirror effect)
 *  - steps should show what is happening now and what has finished, not a spinner
 *  - reasoning is collapsed by default; curious people expand it
 *  - typing cadence with jitter and occasional hesitation reads as work, while a perfectly even
 *    cadence reads as an animation
 */
(() => {
  "use strict";

  const params = new URLSearchParams(location.search);
  const target = params.get("url") || "http://mpesa.co.ke.verify-account.top/";

  const el = (id) => document.getElementById(id);
  const typedEl = el("typed");
  const caretEl = el("caret");
  const statusEl = el("status");
  const statusText = el("statusText");
  const measuresEl = el("measures");

  const weighEl = el("weigh");
  const scoreEl = el("score");
  const fillEl = el("fill");
  const verdictEl = el("verdict");
  const headlineEl = el("headline");
  const bandEl = el("band");
  const reasonsEl = el("reasons");

  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const jitter = (ms, spread) => ms + (Math.random() * spread * 2 - spread);

  // The measurements are shown in the order the extractor computes them, so the list is the
  // pipeline rather than a decorative sequence.
  const MEASUREMENTS = [
    ["length of the registered name", "domain_len"],
    ["labels in the name", "num_labels"],
    ["hyphens", "num_hyphens"],
    ["digits", "num_digits"],
    ["share of digits", "digit_ratio"],
    ["share of hyphens", "hyphen_ratio"],
    ["length of the ending", "tld_len"],
    ["ending is cheap or abused", "suspicious_tld"],
    ["host is a raw address", "is_ip"],
    ["punycode present", "is_idn"],
    ["character entropy", "entropy"],
    ["longest label", "max_label_len"],
    ["a known brand appears", "brand_present"],
    ["brand in the wrong place", "brand_in_wrong_place"],
    ["looks like a lookalike", "is_typosquat"],
    ["distance to nearest brand", "typo_distance"],
    ["digits in the name", "digit_in_registrable"],
  ];

  const HOT = new Set(["suspicious_tld", "brand_in_wrong_place", "is_typosquat", "is_ip"]);

  function reset() {
    typedEl.textContent = "";
    measuresEl.innerHTML = "";
    weighEl.classList.remove("on");
    verdictEl.classList.remove("on");
    scoreEl.textContent = "0";
    fillEl.style.width = "0%";
    caretEl.className = "caret blink";
    caretEl.style.display = "";
  }

  let phaseStart = performance.now();
  function setStatus(text) { statusText.textContent = text; phaseStart = performance.now(); }

  /** Type the address the way a careful reader would: uneven, pausing at the punctuation. */
  async function typeAddress(address) {
    caretEl.className = "caret steady";
    setStatus("reading the address");
    for (const character of address) {
      typedEl.textContent += character;
      let pause = jitter(38, 10);
      if (character === "." || character === "-" || character === "/") pause += jitter(90, 40);
      if (Math.random() < 0.04) pause += 140;          // a hesitation, about one per address
      await wait(Math.max(18, pause));
    }
  }

  /** Mark the part of the address that actually decides the verdict. */
  async function markRegistered(host, domain) {
    const address = typedEl.textContent;
    const at = address.indexOf(domain);
    if (at === -1) return;
    typedEl.innerHTML =
      `<span class="host-mark">${address.slice(0, at)}</span>` +
      `<span class="registered">${address.slice(at, at + domain.length)}</span>` +
      `<span class="host-mark">${address.slice(at + domain.length)}</span>`;
    caretEl.style.display = "none";
    setStatus("the registered name: " + domain);
    await wait(420);
  }

  async function measure(features) {
    setStatus("measuring 0 of 17");
    for (let i = 0; i < MEASUREMENTS.length; i += 1) {
      const [label, key] = MEASUREMENTS[i];
      const chip = document.createElement("span");
      chip.className = "measure" + (HOT.has(key) && features[key] ? " hot" : "");
      const raw = features[key];
      const shown = typeof raw === "number" ? (Number.isInteger(raw) ? raw : raw.toFixed(4)) : raw;
      chip.textContent = `${label}: ${shown}`;
      measuresEl.appendChild(chip);
      if (i % 4 === 0) setStatus(`measuring ${i + 1} of 17`);
      const pause = i % 6 === 0 ? jitter(150, 30) : jitter(52, 14);
      await wait(Math.max(30, pause));
    }
    await wait(200);
  }

  /** Weigh the evidence. The number only ever moves toward the model's own answer. */
  async function weigh(probability) {
    setStatus("weighing the evidence");
    weighEl.classList.add("on");
    const final = Math.round(probability * 100);
    const stops = [Math.round(final * 0.35), Math.round(final * 0.62), Math.round(final * 0.9), final];
    for (let i = 0; i < stops.length; i += 1) {
      scoreEl.textContent = String(stops[i]);
      fillEl.style.width = stops[i] + "%";
      await wait(i === stops.length - 1 ? 220 : jitter(230, 50));
    }
    setStatus("probability " + final + " out of 100");
  }

  async function writeVerdict(payload) {
    setStatus("writing the verdict");
    headlineEl.textContent = payload.headline || (payload.risk === "high"
      ? "This one is worth avoiding"
      : payload.risk === "medium" ? "Worth a second look" : "This reads as ordinary");
    bandEl.textContent = `${payload.verdict} · ${payload.risk} risk · ${payload.probability ===
      null ? "not scored" : Math.round(payload.probability * 100)} out of 100`;
    verdictEl.classList.add("on");
    const reasons = payload.reasons || [];
    for (let i = 0; i < reasons.length; i += 1) {
      const row = document.createElement("div");
      row.className = "reason";
      row.style.animationDelay = "0ms";
      row.innerHTML = `<b>${String(i + 1).padStart(2, "0")}</b><span></span>`;
      row.querySelector("span").textContent = reasons[i];
      reasonsEl.appendChild(row);
      await wait(jitter(300, 60));
    }
    setStatus("done");
    statusEl.querySelector(".dot").style.animation = "none";
  }

  async function run() {
    reset();
    const started = performance.now();

    // The request goes out while the address is being typed, so the waiting overlaps the
    // reading instead of following it. That is the whole trick: no extra time is added.
    const request = fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: target }),
    }).then((response) => response.json());

    await typeAddress(target);
    const payload = await request;

    if (payload && payload.host) {
      await markRegistered(payload.host, payload.domain || payload.host);
      await measure(payload.features || {});
      await weigh(payload.probability ?? 0);
      await writeVerdict(payload);
    }

    const elapsed = Math.round(performance.now() - started);
    const foot = el("foot");
    foot.textContent = `Done in ${(elapsed / 1000).toFixed(1)} seconds. Every value above came
      from the model's response: the address, ${Object.keys(payload && payload.features || {}).length}
      measurements, the probability and the reasons drawn from those measurements. The pacing is
      designed. The content is not.`;
  }

  el("again").addEventListener("click", run);
  run();
})();
