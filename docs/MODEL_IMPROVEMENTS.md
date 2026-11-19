# The model: what was measured, and what to change

Everything below was run against the repository on 19 November 2026. Numbers are reproducible
with the four scripts in `ml/experiments/`. Nothing here fetches a page, resolves a name or
asks a third party about a domain, so the privacy promise is untouched.

## What the model actually is

```
URL text -> registrable domain (eTLD+1)
         -> [ char_wb TF-IDF, 2-5 grams, 60k features | 17 handcrafted numeric features ]
         -> StandardScaler -> LogisticRegression(C=4, liblinear)
         -> probability, plus a reproduction of the reasons from the coefficients
```

Two consequences worth stating plainly, because they bound every improvement below:

1. **The path, query and subdomain never reach the model.** Curation reduced every row to its
   registrable domain, and the service does the same before scoring. A phish at
   `safaricom.co.ke.verify-account.top/login?ref=x` is judged on `verify-account.top`.
2. **The corpus has no paths at all.** Measured: 0.0 per cent of rows in both classes carry a
   non-empty path. So path features cannot be added today without leaking the collection
   method, which is exactly the trap the earlier 95.7 per cent configuration fell into.

## Baseline, reproduced

Same split seed as training, so these are comparable to `ml/artifacts/metrics.json`.

| metric | row level | domain level |
| --- | --- | --- |
| accuracy | 0.7540 | |
| F1 | 0.7402 | |
| false positive rate | 0.1976 | 0.197 |
| recall | 0.7050 | **0.690** (1,073 of 1,554 phishing domains) |
| ROC-AUC | 0.8293 | |
| Brier | 0.1674 | |
| **ECE** | **0.0280** | |

**The percentage is honest.** An expected calibration error of 2.8 points means that when the
interface says 80, roughly 80 of 100 such addresses are phishing. This is the strongest claim
the product can make and it deserves to be in the report.

Domain-level recall is 0.690 against 0.705 at row level, because 1,545 rows share a domain with
another row. Reporting the row figure alone flatters the model slightly.

## Where the mistakes are

**False alarms (355).** They are not brand lookalikes: only 1.1 per cent carry a
brand-in-wrong-place flag and 9.9 per cent a suspicious TLD. Inspecting the highest-scoring
ones shows what they are:

```
0.968  marpple.shop
0.951  securelogger.top
0.941  campusvirtualisaeuniversidad.net
0.929  c81358859121583b7adf2ace89cb39f44.com
0.922  srrunm1yhpr9.link
0.920  nadimtogelife.xyz
```

A 32-character hexadecimal domain labelled legitimate is label noise in the negative class, not
a model failure. Tranco ranks by traffic, not by virtue, so it contains parked, expired and
recently abused domains. Part of the measured false-positive rate is the corpus arguing with
itself.

**Misses (524 rows, 481 domains).** They are the opposite shape entirely:

- 99.6 per cent carry no brand at all
- 99.2 per cent carry no suspicious TLD
- 518 of 524 have no brand, no bad TLD and no IP address
- 0 per cent sit on an allowlisted domain

```
0.033  doxa.rs
0.041  aglob.fr
0.045  xzone.no
0.047  g8way.io
0.053  lowhost.ru
```

These are short, ordinary-looking names on ordinary endings. There is no lexical signal to
find, because the strength of a short domain is that it looks like every other short domain.

## What was tried, and what it did

In-domain, same split, threshold 0.50:

| variant | accuracy | F1 | FPR | verdict |
| --- | --- | --- | --- | --- |
| deployed recipe | 0.7540 | 0.7402 | 0.1976 | |
| n-grams only | 0.7375 | 0.7226 | 0.2137 | numeric features earn their place |
| numeric only | 0.6781 | 0.6408 | 0.2226 | the name's spelling carries most of it |
| without brand features | 0.7487 | 0.7349 | 0.2042 | small but real contribution |
| without TLD features | 0.7545 | 0.7412 | 0.1987 | TLD features are noise |
| 70 more brands | 0.7540 | 0.7386 | 0.1920 | no gain, slightly worse F1 |
| character shape features | 0.7576 | 0.7435 | 0.1920 | **+0.36 points, does not transfer** |
| fold-safe TLD prior | 0.7562 | 0.7419 | 0.1931 | +0.22 points, untested on drift |
| gradient boosting, numeric only | 0.7137 | 0.7029 | 0.2543 | loses badly without n-grams |

The shape-feature gain looked like the one free win available. It is not:

| model | in-domain accuracy | today's phishing detected | today's false alarm rate |
| --- | --- | --- | --- |
| deployed recipe | 0.7540 | 0.558 | 0.302 |
| plus shape features | 0.7554 | 0.558 | 0.294 |

The gain does not survive contact with data it has not seen. A benign-likeness feature, fitted
only on legitimate names, made things worse (0.523 detected), and is recorded here so nobody
repeats it.

## The finding that matters: the model is decaying

The deployed artefact was judged on addresses it could not have seen, from a live feed on the
day of the run, with legitimate negatives drawn from Tranco ranks 100,001 to 1,000,000 so the
reputation ceiling gives nobody a free pass.

| threshold | today's phishing detected | false alarm on long-tail legitimate |
| --- | --- | --- |
| 0.35 | 0.686 | 0.470 |
| **0.50** | **0.570** | **0.302** |
| 0.60 | 0.453 | 0.192 |
| 0.65 | 0.407 | 0.162 |

Against the 2025 hold-out, recall at 0.50 was 0.705 and the false-positive rate 0.198. On
today's traffic they are **0.570 and 0.302**. Some of that is the harder negative sample, not
pure decay, but the direction is unambiguous and it is the single most important number in this
document: a deployed model that is retrained never will lose roughly a fifth of its recall
within a year.

**The reputation ceiling has a blind spot of 17.4 per cent.** Of the 86 phishing domains in
today's feed, 15 are inside the top-100,000 allowlist, where the design holds the reported risk
at 15 or below. Their raw scores were low (median 0.236), so the model would have missed most
of them anyway, but the cap guarantees the miss. Nearly one in five phish now arrives on a
domain the ceiling protects.

## Cost of a mistake, and what that implies for the threshold

Expected cost over the hold-out, for several ratios of "a missed phish costs N times a false
alarm":

| threshold | false alarms | misses | 1:1 | 5:1 | 10:1 | 30:1 |
| --- | --- | --- | --- | --- | --- | --- |
| 0.30 | 770 | 257 | 1,027 | 2,055 | **3,340** | **8,480** |
| 0.40 | 532 | 371 | 903 | 2,387 | 4,242 | 11,662 |
| 0.50 | 355 | 524 | **879** | 2,975 | 5,595 | 16,075 |
| 0.60 | 220 | 701 | 921 | 3,725 | 7,230 | 21,250 |
| 0.70 | 132 | 839 | 971 | 4,327 | 8,522 | 25,302 |

There is no single right threshold; there is a right policy. If a miss costs ten times a false
alarm, the current 0.50 is too strict and 0.30 is better, at the price of alarming 43 per cent
of legitimate addresses. That trade is only defensible if the interface presents a **band**
rather than a verdict, which it already does. The recommendation is therefore to fix the band
edges by policy and state the cost assumption, rather than to nudge one threshold.

## The improvement agenda, in order of expected value

### 1. Retrain on a schedule, and prove it happened

Measured decay gives the argument. Weekly or fortnightly retraining, the same grouped split, and
a frozen baseline kept for comparison. The dashboard should show the current model's age and its
score distribution against the baseline, because a shift in the distribution of scores is the
earliest visible failure.

Cost: an afternoon. Value: recovers most of the 13 points of recall lost in a year.

### 2. Fix the negative class before touching the features

Part of the 30 per cent false-alarm rate on the long tail is the corpus, not the model. A
benign sample should be checked for parked and expired domains, and the label should say what it
means: "a domain in a traffic ranking", not "a proven honest site".

Cost: a day of curation. Value: the measured false-positive rate becomes a number about the
model rather than about Tranco.

### 3. Get a benign corpus that has paths

This is the one that unlocks real capability, and it is blocked on data, not ideas. The earlier
structural study already showed that nested and encoded URLs are rare and dangerous to add
without benign redirects at scale. Adding 50,000 legitimate deep URLs (a crawl of the top
domains, or a Common Crawl sample) would let path, query and redirect features be evaluated
honestly for the first time.

Cost: a day to gather, a week to evaluate. Value: the only route past the lexical ceiling.

### 4. Make the reputation policy a graded one

Instead of capping every allowlisted domain at 15, cap by rank and by model score: a top-1,000
domain at 10, a rank-90,000 domain with a 0.9 score at, say, 45. This keeps the guarantee for
household names while narrowing the 17.4 per cent blind spot. It must be disclosed in the
verdict text, as the current cap is.

Cost: half a day. Value: removes a guarantee that fails 15 times in 86.

### 5. Try one model with interactions, properly

Gradient boosting on numeric features alone loses badly (0.714 against 0.754), but that compares
a boosted model without n-grams against a linear model with them. The fair comparison is boosting
over hashed n-grams or a small character CNN. Expect one to three AUC points at most; do not
expect a different product.

Cost: two days. Value: modest, but it is the standard question a marker will ask.

### 6. Keep the explanation and the score from drifting apart

The reasons come from the logistic coefficients, which is why they are exact rather than
approximated. If the classifier changes, the reasons must be re-derived with SHAP or dropped.
Any model swap is also an explanation swap.

### 7. Recalibrate at every retrain

ECE is 0.028 today, which is good. Calibration is not a property that survives retraining by
default, so the reliability curve should be recomputed and isotonic scaling refitted whenever
the model is replaced, even though it changed nothing on this corpus.

## What not to do, with the evidence

- **Do not add path features to the current corpus.** Every row is pathless; the feature would
  learn the collection method.
- **Do not expand the brand list and expect recall.** 70 more brands produced no gain and a
  slightly worse F1; 99.6 per cent of misses carry no brand at all.
- **Do not rely on shape features.** They gain in-domain and vanish out of domain.
- **Do not raise the threshold to look safe.** At 10:1 cost, 0.50 already loses to 0.30.
- **Do not ship a model without a date on it.** The decay above is the argument.

## Backlog items that bear on this

- **Measurement (open).** Continuous improvement needs recent labelled outcomes, and the service
  deliberately stores no outcomes. The privacy decision is therefore also the retraining
  decision: either a user opts in to contributing "this was a phishing page", or retraining
  stays manual from public feeds. This is the highest-leverage unresolved item in the project.
- **Real device pass (open).** Not a model issue, but the phone is where the band wording is
  read, and a threshold policy cannot be judged without it.
- **The structural rule (measured, parked).** Nested-address detection moved 2 of 1,500 phish
  because the model had already decided the rest. It stays as a reason, not a score, until a
  legitimate-redirect corpus exists.
- **Drift monitoring (new).** The statistics endpoint already records latency and counts; it
  should also bucket scores by day so the drift above becomes visible before users feel it.

## Reproducing

```
python ml/experiments/error_analysis.py      # errors, ablation, cost curve
python ml/experiments/feature_variants.py    # variant table, including the ones that failed
python ml/experiments/temporal_drift.py      # live feed and Tranco long tail, dated
python ml/experiments/calibration.py         # Brier, ECE, per-domain recall
```

The temporal script writes `ml/artifacts/temporal_<date>.csv`, so runs on different dates can be
compared. That file is the beginning of a drift record, and the record is worth more than any
single model.
