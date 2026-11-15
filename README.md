# Nyavu

**A machine-learning phishing URL detector that explains its verdicts.**

Nyavu (Swahili for *fishing net*) assesses a web address from its text alone — no page is
fetched, no third-party lookup is made — and returns a risk band, a score, and the specific
characteristics that produced it.

A COMP324 team project at Kabarak University, built to be reproducible, honest about its
accuracy, and cheap enough to run for nothing.

---

## Why it exists

Blocklists are the standard defence against phishing, and they are structurally reactive: an
address appears on a list only after someone has reported and verified it. In that window the
page is live and unrecognised. Nyavu asks a different question — *is this address, which nobody
has reported yet, safe to open?* — and answers it from the address itself in tens of milliseconds.

## How it works

```
URL ──► registrable domain ──► 17 numeric features ──► logistic regression ──► score
                                    │                                             │
                          character n-grams                          risk band + reasons
```

1. **Reduce** the address to its registrable domain (`mpesa.co.ke.verify-account.top` → `verify-account.top`).
2. **Extract** 17 interpretable features (length, digit and hyphen counts, entropy, TLD, brand proximity, typosquat distance) plus character n-grams of the domain.
3. **Classify** with a calibrated linear model, so the reported percentage means what it says.
4. **Explain** using the model's own coefficients — the reasons shown are the features that actually moved the score.
5. **Record** the scan for the signed-in user's private history.

## Model card

| | |
|---|---|
| Corpus | 17,730 addresses, balanced 8,865 / 8,865 |
| Removed as undetectable | 4,236 phishing URLs (32%) hosted on domains in the Tranco top 200,000 — compromised legitimate sites that no name-based model can detect |
| Split | Grouped by registrable domain; no domain appears in both train and test |
| Accuracy | **75.4%** |
| F1 / ROC-AUC | 0.740 / 0.829 |
| False-positive rate | **19.8%** on the bare model |
| Cross-validation | 5 grouped folds, F1 0.727 ± 0.013 |
| Inference | ~20–130 ms per URL, CPU only |

**Why 75% and not the 97% common in the literature.** Published figures are usually inflated by a
collection artefact: benign feeds list bare domains while phishing feeds list full hosts, so the
model learns "has a subdomain ⇒ phishing" instead of learning phishing. An earlier configuration
of this project reached 95.7% that way, and collapsed to 63% once the artefact was removed. The
number above is what remains after the data was curated honestly.

**Because 19.8% is unusable in front of a person**, the deployed system adds a reputation prior:
a domain inside the Tranco top 100,000 is never flagged on name evidence alone. The trade-off is
stated rather than hidden — phishing hosted on a popular domain is missed.

## Privacy

- **No page fetching.** The destination server never learns the address was checked.
- **No notification access.** An Android build that read every notification was rejected: the
  permission is disproportionate to the benefit.
- **Private history.** Scans belong to an account. Anonymous visitors are never shown anybody
  else's history; the endpoint returns an empty list by design.
- **Passwords** are stored as salted PBKDF2-SHA256 (200,000 iterations), never in plain text.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/predict` | Classify a URL; returns verdict, band, score, reasons, evidence |
| POST | `/api/scan/bulk` | Screen a CSV or newline-separated list (max 200) |
| POST | `/api/auth/register` · `/api/auth/login` · `/api/auth/logout` | Optional accounts |
| GET | `/api/history` | The signed-in user's own scans |
| GET | `/api/stats` | Scan counts for this service |
| GET | `/api/model` | Model name and the full comparison table |
| GET | `/api/health` | Liveness and whether the model is loaded |

Rate limited in-process: 30 predictions/min per IP, 10 auth attempts/min, 5 bulk uploads/min.

## Run it

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open <http://127.0.0.1:8000>. The interactive API docs are at `/docs`.

## Tests

```bash
python tests/run_tests.py        # 11 end-to-end checks against a running service
```

Covers classification, the reputation prior, malformed input, bulk screening, and the
history-privacy rule.

## Clients

| Client | State | Notes |
|---|---|---|
| Web app (PWA) | Working | Installable; works offline for the shell |
| Browser extension | Working | Warns before a phishing page loads; per-host notifications |
| Android agent | Built, unverified | Share-sheet and DNS filter present; not yet exercised on a device |

## Limitations

- Judges **names, not pages**. A phishing page on a compromised legitimate domain defeats it.
- Decays as tactics change; retraining on a schedule is required, not optional.
- The brand reference table is a curated list, **not** a verified registry of official domains.
- A verdict is an assessment, never a guarantee of safety.

## Licence

MIT — see [LICENSE](LICENSE).
