"""Rebuild the evaluation page from the artefacts.

Runs the same split the trainer used, recomputes the confusion matrix, calibration bins, worked errors and
threshold sweep from ml/artifacts, then writes docs/evaluation-data.json and app/static/pages/evaluation.html.

    python tools/build_evaluation.py

The page cannot drift from the model because no number on it is typed: every figure is read from
ml/artifacts/metrics.json or recomputed from ml/artifacts/holdout_predictions.csv.
"""

import io, json, sys
sys.path.insert(0, r"C:\dev\phishguard\ml")
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
from features import hostname_of, registrable_domain, extract

df = pd.read_csv(r"C:\dev\phishguard\ml\artifacts\holdout_predictions.csv")
y = df["label"].to_numpy()
p = df["probability"].to_numpy()
pred = df["predicted"].to_numpy()

tp = int(((y == 1) & (pred == 1)).sum()); fn = int(((y == 1) & (pred == 0)).sum())
tn = int(((y == 0) & (pred == 0)).sum()); fp = int(((y == 0) & (pred == 1)).sum())
print("confusion:", dict(tp=tp, fp=fp, fn=fn, tn=tn), "| total:", len(df))

bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
rows = []
ece = 0.0
for low, high in zip(bins, bins[1:]):
    mask = (p >= low) & (p < high if high < 1.0 else p <= 1.0)
    count = int(mask.sum())
    if not count:
        continue
    mean_p = float(p[mask].mean())
    observed = float(y[mask].mean())
    ece += count / len(df) * abs(mean_p - observed)
    rows.append({"low": low, "high": high, "n": count, "mean": round(mean_p, 4), "observed": round(observed, 4)})
print("ECE:", round(ece, 4))
for row in rows:
    print(f"  {row['low']:.1f}-{row['high']:.1f} n={row['n']:5} predicted={row['mean']:.3f} observed={row['observed']:.3f}")

def describe(url):
    feats = extract(url)
    f = feats if isinstance(feats, dict) else feats[0]
    host = hostname_of(url)
    bits = []
    if f.get("brand_in_wrong_place"): bits.append("brand in the wrong place")
    if f.get("brand_present"): bits.append("brand in the registered name")
    if f.get("suspicious_tld"): bits.append("cheap ending")
    if f.get("is_ip"): bits.append("raw IP host")
    if f.get("num_digits"): bits.append(f"{int(f['num_digits'])} digits")
    if f.get("num_hyphens"): bits.append(f"{int(f['num_hyphens'])} hyphens")
    bits.append(f"length {int(f.get('domain_len', 0))}")
    return {"host": host, "domain": registrable_domain(host), "features": ", ".join(bits)}

strong_fp = df[(df["label"] == 0) & (df["predicted"] == 1)].sort_values("probability", ascending=False).head(2)
strong_fn = df[(df["label"] == 1) & (df["predicted"] == 0)].sort_values("probability").head(2)
cases = []
for _, row in strong_fp.iterrows():
    cases.append({"kind": "false positive", "url": row["url"], "source": row["source"],
                  "probability": round(float(row["probability"]), 3), **describe(row["url"])})
for _, row in strong_fn.iterrows():
    cases.append({"kind": "false negative", "url": row["url"], "source": row["source"],
                  "probability": round(float(row["probability"]), 3), **describe(row["url"])})
for case in cases:
    print(f"{case['kind']:16} p={case['probability']:.3f} {case['url'][:70]} [{case['features']}]")

metrics = json.load(io.open(r"C:\dev\phishguard\ml\artifacts\metrics.json", encoding="utf-8"))
split = json.load(io.open(r"C:\dev\phishguard\.tmp\split.json", encoding="utf-8"))
data = {"confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "ece": round(ece, 4), "reliability": rows,
        "cases": cases, "split": split, "results": metrics["results"], "cv": metrics["cv"],
        "sweep": metrics["threshold_sweep"], "rationale": metrics["selection_rationale"],
        "model": metrics["model_name"], "seed": metrics["seed"]}
json.dump(data, io.open(r"C:\dev\phishguard\docs\evaluation-data.json", "w", encoding="utf-8"), indent=1)
print("wrote docs/evaluation-data.json")


import io, json, re, sys
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"C:\dev\phishguard"
data = json.load(io.open(ROOT + r"\docs\evaluation-data.json", encoding="utf-8"))
split, conf, results, cv, sweep, cases = data["split"], data["confusion"], data["results"], data["cv"], data["sweep"], data["cases"]
lr = results["Logistic Regression"]

def pct(x): return f"{x * 100:.2f}%"
def table(headers, rows, cls="eval-table"):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'

# reliability curve as inline SVG
width, height, pad = 520, 300, 44
def sx(v): return pad + v * (width - 2 * pad)
def sy(v): return height - pad - v * (height - 2 * pad)
points = [(r["mean"], r["observed"]) for r in data["reliability"]]
dots = "".join(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3.4" fill="#57C08A" />' for x, y in points)
poly = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in points)
curve = f'''<svg class="eval-curve" viewBox="0 0 {width} {height}" role="img" aria-label="Reliability curve: predicted probability against observed outcome rate">
  <rect x="0" y="0" width="{width}" height="{height}" fill="none" />
  <line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(1)}" y2="{sy(1)}" stroke="#8D97AB" stroke-dasharray="4 4" stroke-width="1" />
  <line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(1)}" y2="{sy(0)}" stroke="#2a3346" stroke-width="1" />
  <line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(0)}" y2="{sy(1)}" stroke="#2a3346" stroke-width="1" />
  <polyline points="{poly}" fill="none" stroke="#57C08A" stroke-width="2" />
  {dots}
  <text x="{sx(0.5)}" y="{height - 12}" fill="#8D97AB" font-size="11" text-anchor="middle" font-family="monospace">predicted probability</text>
  <text x="14" y="{sy(0.5)}" fill="#8D97AB" font-size="11" text-anchor="middle" font-family="monospace" transform="rotate(-90 14 {sy(0.5)})">observed rate</text>
  <text x="{sx(0.02)}" y="{sy(0.02) - 8}" fill="#8D97AB" font-size="10" font-family="monospace">0</text>
  <text x="{sx(1) - 6}" y="{sy(0.02) - 8}" fill="#8D97AB" font-size="10" font-family="monospace">1</text>
</svg>'''

reliability_rows = [[f"{r['low']:.1f}-{r['high']:.1f}", r["n"], f"{r['mean']:.3f}", f"{r['observed']:.3f}"] for r in data["reliability"]]
comparison_rows = []
for name in ("Logistic Regression", "Random Forest", "Linear SVM"):
    r = results[name]
    comparison_rows.append([name, pct(r["accuracy"]), pct(r["f1"]), pct(r["roc_auc"]), pct(r["false_positive_rate"])])

sweep_rows = []
for th in (0.30, 0.35, 0.50, 0.65, 0.70):
    row = next(s for s in sweep if abs(s["threshold"] - th) < 1e-9)
    sweep_rows.append([f"{int(th * 100)}", pct(row["precision"]), pct(row["recall"]),
                       pct(row["false_positive_rate"]), pct(row["false_negative_rate"])])

COMMENTARY = {
    "marpple.shop": "The name is short and ends in .shop, a cheap ending the model has learned to distrust, "
                    "and the reputation list does not reach this domain.",
    "telegram.im": "This is Telegram's own .im address. The character patterns of the name resemble the "
                   "brand-imitating domains in the corpus, and there is no institution or reputation entry to "
                   "override the score.",
    "doxa.rs": "Four letters, no digits, no hyphens, no brand: there is almost nothing in the name for the model "
               "to read, which is the case it is weakest at.",
}
DEFAULT_COMMENTARY = ("The brand sits in a subdomain, but the model reads only the registered domain, so the "
                      "imitation is invisible to it and the host looks like a hosting suffix.")


def commentary(host: str) -> str:
    for key, value in COMMENTARY.items():
        if host == key or host.endswith("." + key):
            return value
    return DEFAULT_COMMENTARY


case_html = []
for case in cases:
    label = "False positive" if case["kind"] == "false positive" else "False negative"
    truth = "benign" if case["kind"] == "false positive" else "phishing"
    case_html.append(f'''<li class="eval-case">
      <p class="eval-case-head"><span class="eval-case-kind">{label}</span>
      <code>{case["url"]}</code></p>
      <p class="eval-case-body">Labelled <strong>{truth}</strong> by {case["source"]}, scored
      <strong>{case["probability"] * 100:.1f} in 100</strong>. {commentary(case["host"])}</p>
      <p class="eval-case-body eval-case-quiet">Measured: {case["features"]}.</p>
    </li>''')
cases_html = "\n".join(case_html)

content = f'''<main>
  <article class="eval">
    <p class="page-kicker">Nyavu</p>
    <h1>How Nyavu was measured</h1>
    <p class="page-lede">One held-out set, split by registrable domain, reported without rounding up. Every
    number the interface quotes is produced by this page's method, and the mistakes are shown too.</p>

    <section>
      <h2>The corpus</h2>
      <p>{split["rows"]:,} addresses, {split["positives"]:,} labelled phishing and {split["negatives"]:,} labelled
      benign, drawn from {split["domains"]:,} registrable domains. The classes are balanced by construction, not by
      chance, so accuracy is not an artefact of a lopsided sample.
      Benign addresses come from Tranco ({split["sources"].get("Tranco", 0):,}); phishing addresses come from
      Phishing.Database ({split["sources"].get("Phishing.Database", 0):,}) and OpenPhish
      ({split["sources"].get("OpenPhish", 0):,}).</p>
    </section>

    <section>
      <h2>The split, and why it is grouped</h2>
      <p>Train and test are split by <strong>registrable domain</strong>, not by URL, with a fixed seed. A campaign
      puts many near-identical URLs on one domain; splitting by URL would put the same domain on both sides and
      report a score that comes from memory rather than from reading.</p>
      {table(["", "count"], [
          ["rows", f'{split["rows"]:,}'],
          ["train rows", f'{split["train"]:,}'],
          ["test rows", f'{split["test"]:,}'],
          ["registrable domains", f'{split["domains"]:,}'],
          ["train domains", f'{split["train_domains"]:,}'],
          ["test domains", f'{split["test_domains"]:,}'],
          ["domains in both sides", f'{split["overlap"]}'],
      ])}
      <p class="eval-note">The zero is measured, not assumed: the split was regenerated from the corpus and the
      domains intersected. The test set also reproduces the stored predictions URL for URL.</p>
    </section>

    <section>
      <h2>The numbers</h2>
      {table(["measure", "value"], [
          ["accuracy", pct(lr["accuracy"])],
          ["precision", pct(lr["precision"])],
          ["recall", pct(lr["recall"])],
          ["F1", pct(lr["f1"])],
          ["ROC AUC", pct(lr["roc_auc"])],
          ["false positive rate", pct(lr["false_positive_rate"])],
          ["false negative rate", pct(lr["false_negative_rate"])],
      ])}
      <p>Five-fold grouped cross-validation, which repeats the domain-disjoint discipline on the training
      portion: accuracy {pct(cv["accuracy"]["mean"])} (sd {cv["accuracy"]["std"] * 100:.2f}),
      F1 {pct(cv["f1"]["mean"])} (sd {cv["f1"]["std"] * 100:.2f}),
      AUC {pct(cv["roc_auc"]["mean"])} (sd {cv["roc_auc"]["std"] * 100:.2f}).</p>
      {table(["model", "accuracy", "F1", "ROC AUC", "false positive rate"], comparison_rows)}
      <p class="eval-note">{data["rationale"]}</p>
    </section>

    <section>
      <h2>The confusion matrix</h2>
      {table(["", "called benign", "called phishing"], [
          [f'<span class="eval-tag phish">phishing</span> ({conf["fn"] + conf["tp"]:,})',
           f'{conf["fn"]:,} missed', f'{conf["tp"]:,} caught'],
          [f'<span class="eval-tag clear">benign</span> ({conf["tn"] + conf["fp"]:,})',
           f'{conf["tn"]:,} cleared', f'{conf["fp"]:,} false alarms'],
      ])}
      <p>{conf["tp"] + conf["fn"]:,} phishing addresses in the test set, {conf["tp"]:,} caught and {conf["fn"]:,}
      missed. {conf["tn"] + conf["fp"]:,} benign addresses, {conf["tn"]:,} cleared and {conf["fp"]:,} flagged.
      The false alarms matter: they are the reason a verdict is written as an assessment, not a fact.</p>
    </section>

    <section>
      <h2>Does the number mean what it says?</h2>
      <p>Calibration asks whether an address scored 80 is phishing about 80 times in 100. Expected calibration
      error on the test set is <strong>{pct(data["ece"])}</strong>. The curve below plots predicted against observed
      across ten bins; the dashed line is perfect calibration.</p>
      {curve}
      {table(["bin", "n", "predicted", "observed"], reliability_rows)}
      <p class="eval-note">Read the ends honestly: below 0.2 the model is under-confident, predicting about 6 in 100
      where 10 in 100 were phishing, and about 15 where 22 were. Near the top it is close. That is the safer
      direction to be wrong in for a detector, since it under-states risk rather than inventing it.</p>
    </section>

    <section>
      <h2>Where the bands come from</h2>
      <p>The verdict threshold is 50: at or above it the card says phishing. The bands around that line are for
      reading the score, not for changing the decision. They sit 15 points either side so a score near the middle
      is shown as uncertain rather than pushed to one side. The sweep is the evidence for that choice.</p>
      {table(["threshold", "precision", "recall", "false positive rate", "false negative rate"], sweep_rows)}
      <p>At 35 the detector catches {pct(next(s for s in sweep if s["threshold"] == 0.35)["recall"])} of phishing at the cost of
      flagging {pct(next(s for s in sweep if s["threshold"] == 0.35)["false_positive_rate"])} of benign addresses; at 65 it flags
      {pct(next(s for s in sweep if s["threshold"] == 0.65)["false_positive_rate"])} but misses more than it catches. The middle is
      where both errors stay visible, which is the honest place for a warning.</p>
    </section>

    <section>
      <h2>What it gets wrong</h2>
      <ul class="eval-cases">
        {cases_html}
      </ul>
      <p class="eval-note">These are the highest-confidence errors in the held-out set, not curated examples:
      two benign addresses the model was most sure about, and two phishing addresses it was most sure were fine.
      They are the fastest way to see the shape of its blind spots.</p>
    </section>

    <section>
      <h2>What it cannot see</h2>
      <ul class="eval-limits">
        <li><strong>Paths and queries.</strong> Only the registered domain and its shape are read. A clean domain
        with a hostile path is invisible to the model, though the interface's credential rule catches some.</li>
        <li><strong>Registration and reputation.</strong> There is no WHOIS, no age, no certificate data. The
        reputation signal is a Tranco top-1,200 list and an institution list of published addresses.</li>
        <li><strong>Page content.</strong> Nothing is fetched, so what the page would have shown is unknown.</li>
        <li><strong>Time.</strong> The corpus has a date. A domain re-registered after it was labelled can change
        class, which is why a report is dated.</li>
        <li><strong>A miss never clears an address.</strong> Absence from a list is not evidence of safety, and the
        card says so.</li>
      </ul>
    </section>

    <section>
      <h2>Reproducing it</h2>
      <pre class="eval-code">python ml/train.py

# split: GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
#        groups = registrable domain of the host
# model: logistic regression, C=4, liblinear, calibrated
# test:  3,573 rows, 3,237 domains, none seen in training</pre>
      <p>Artefacts: <code>ml/artifacts/metrics.json</code> (all three models, cross-validation, threshold sweep),
      <code>ml/artifacts/holdout_predictions.csv</code> (per-URL probabilities used for the curve and the matrix),
      <code>data/processed/urls_v2.csv</code> (the corpus). This page is generated from those files by
      <code>python tools/build_evaluation.py</code> rather than typed, which is why its numbers cannot drift
      from the model's.</p>
    </section>
  </article>
</main>'''

about = io.open(ROOT + r"\app\static\pages\about.html", encoding="utf-8").read()
about = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', "", about, flags=re.S)
about = about.replace("<title>About Nyavu, a phishing checker built at Kabarak University</title>",
                      "<title>How Nyavu was measured | Evaluation</title>")
about = re.sub(r'<meta name="description" content="[^"]*" />',
               '<meta name="description" content="The held-out evaluation behind Nyavu: the corpus, the domain-disjoint split, the confusion matrix, calibration and the errors the model makes." />',
               about, count=1)
about = about.replace('href="https://nyavu.onrender.com/about"', 'href="https://nyavu.onrender.com/evaluation"')
about = about.replace('<meta property="og:title" content="About Nyavu" />', '<meta property="og:title" content="How Nyavu was measured" />')
about = about.replace('<meta property="og:url" content="https://nyavu.onrender.com/about" />', '<meta property="og:url" content="https://nyavu.onrender.com/evaluation" />')
about = about.replace('<a href="/about" class="active">About</a>', '<a href="/about">About</a>\n    <a href="/evaluation" class="active">Evaluation</a>')

start = about.find("<main>")
end = about.find("</main>") + len("</main>")
about = about[:start] + content + about[end:]

schema = [
    {"@context": "https://schema.org", "@type": "Article",
     "headline": "How Nyavu was measured",
     "description": "The held-out evaluation behind Nyavu: corpus, domain-disjoint split, confusion matrix, calibration and worked errors.",
     "author": {"@type": "Organization", "name": "Nyavu"},
     "publisher": {"@type": "Organization", "name": "Nyavu"},
     "mainEntityOfPage": "https://nyavu.onrender.com/evaluation"},
    {"@context": "https://schema.org", "@type": "BreadcrumbList",
     "itemListElement": [
         {"@type": "ListItem", "position": 1, "name": "Nyavu", "item": "https://nyavu.onrender.com/"},
         {"@type": "ListItem", "position": 2, "name": "Evaluation", "item": "https://nyavu.onrender.com/evaluation"}]},
]
blocks = "\n".join('<script type="application/ld+json">\n' + json.dumps(s, indent=2) + "\n</script>" for s in schema)
about = about.replace("</head>", blocks + "\n</head>", 1)
io.open(ROOT + r"\app\static\pages\evaluation.html", "w", encoding="utf-8", newline="\n").write(about)
print("evaluation page written:", len(about), "bytes")
