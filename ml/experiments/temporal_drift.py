"""
How the deployed model does on addresses it could not have seen: today's feed, today's web.

This is the experiment the report could not run, because it needs time to pass. It trains on
nothing new. It loads ml/artifacts/model.joblib exactly as the service does, and judges:

  phishing   the current OpenPhish feed, which is a live list of addresses being used right now
  legitimate Tranco ranks 100,001 to 1,000,000, which are real sites outside the reputation
             allowlist, so nobody gets the benefit of the established-domain ceiling

The dates are printed so the run can be repeated and compared.
"""
from __future__ import annotations

import csv
import io
import os
import sys
import urllib.request
import zipfile

import joblib
import numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT_DIR, "ml"))
from features import FEATURE_ORDER, extract, hostname_of, registrable_domain  # noqa: E402

ROOT = ROOT_DIR
RAW = os.path.join(ROOT, "data", "raw")
ART = os.path.join(ROOT, "ml", "artifacts")
TODAY = "2026-11-19"
UA = {"User-Agent": "NyavuResearch/1.0 (academic project)"}


def fetch(url: str, path: str) -> bytes:
    if os.path.exists(path):
        return open(path, "rb").read()
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    open(path, "wb").write(data)
    return data


def fresh_phishing(limit=500):
    path = os.path.join(RAW, f"openphish_{TODAY}.txt")
    text = fetch("https://openphish.com/feed.txt", path).decode("utf-8", "ignore")
    urls = [line.strip() for line in text.splitlines() if line.strip().startswith("http")]
    seen, picked = set(), []
    for url in urls:
        domain = registrable_domain(hostname_of(url))
        if domain and domain not in seen:
            seen.add(domain)
            picked.append(url)
        if len(picked) >= limit:
            break
    return picked


def fresh_legit(limit=500, low=100_000, high=1_000_000):
    path = os.path.join(RAW, f"tranco_{TODAY}.csv.zip")
    blob = fetch("https://tranco-list.eu/top-1m.csv.zip", path)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        name = archive.namelist()[0]
        rows = []
        with archive.open(name) as handle:
            for line in io.TextIOWrapper(handle, encoding="utf-8"):
                rank, domain = line.strip().split(",")
                if low < int(rank) <= high:
                    rows.append(domain)
    step = max(1, len(rows) // limit)
    return rows[::step][:limit]


def score(model, urls):
    rows = []
    for url in urls:
        features, _ = extract(url)
        if not features:
            continue
        row = dict(features)
        row["domain"] = registrable_domain(hostname_of(url))
        rows.append(row)
    frame = pd.DataFrame(rows)
    for column in FEATURE_ORDER:
        if column not in frame:
            frame[column] = 0
    return frame, model.predict_proba(frame)[:, 1]


def main():
    model = joblib.load(os.path.join(ART, "model.joblib"))
    allow = set()
    with open(os.path.join(ART, "allowlist.txt"), encoding="utf-8") as handle:
        allow = {line.strip().lower() for line in handle if line.strip()}

    phish = fresh_phishing()
    legit = fresh_legit()
    print(f"date {TODAY} | fresh phishing {len(phish)} | fresh legitimate {len(legit)} "
          f"| allowlist {len(allow)}")

    phish_frame, phish_score = score(model, phish)
    legit_frame, legit_score = score(model, legit)

    print("\nphishing from today's feed, judged by the deployed model")
    for threshold in (0.35, 0.50, 0.60, 0.65):
        rate = float((phish_score >= threshold).mean())
        print(f"  threshold {threshold:.2f}  detected {rate:.3f}  "
              f"(missed {1 - rate:.3f})")
    print(f"  median score {np.median(phish_score):.3f}  "
          f"p10 {np.percentile(phish_score, 10):.3f}  p90 {np.percentile(phish_score, 90):.3f}")

    print("\nlegitimate domains from Tranco 100k-1M, which the ceiling does not protect")
    for threshold in (0.35, 0.50, 0.60, 0.65):
        rate = float((legit_score >= threshold).mean())
        print(f"  threshold {threshold:.2f}  false alarm {rate:.3f}")
    print(f"  median score {np.median(legit_score):.3f}  "
          f"p90 {np.percentile(legit_score, 90):.3f}")

    inside = phish_frame["domain"].isin(allow)
    print(f"\nof today's phishing domains, {inside.mean():.3f} are inside the top-100k "
          f"allowlist, where a name verdict is capped at 15 by design")
    if inside.any():
        capped = phish_score[inside.values]
        print(f"  those {int(inside.sum())} would be reported at or below 15: "
              f"median raw score {np.median(capped):.3f}")

    combined = pd.DataFrame({"domain": list(phish_frame["domain"]) + list(legit_frame["domain"]),
                             "label": [1] * len(phish_frame) + [0] * len(legit_frame),
                             "score": list(phish_score) + list(legit_score)})
    out = os.path.join(ART, f"temporal_{TODAY}.csv")
    combined.to_csv(out, index=False)
    print("\nwrote", out)


if __name__ == "__main__":
    main()

