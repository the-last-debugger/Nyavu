"""
Where the mistakes are, and which parts of the feature set carry the model.

Runs offline against data/processed/urls_v2.csv with the same split seed as training, so the
numbers are comparable to ml/artifacts/metrics.json rather than a fresh experiment.

Print only: this is analysis, not a new artefact.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT_DIR, "ml"))
from features import (BRANDS, FEATURE_ORDER, extract, hostname_of,  # noqa: E402
                      registrable_domain)

ROOT = ROOT_DIR
DATA = os.path.join(ROOT, "data", "processed", "urls_v2.csv")
ALLOWLIST = os.path.join(ROOT, "ml", "artifacts", "allowlist.txt")
SEED = 42
BRAND_FEATS = ["brand_present", "brand_in_wrong_place", "is_typosquat", "typo_distance"]
TLD_FEATS = ["tld_len", "suspicious_tld"]


def load():
    df = pd.read_csv(DATA)
    feats = pd.DataFrame([extract(u)[0] for u in df["url"]])
    for c in FEATURE_ORDER:
        if c not in feats:
            feats[c] = 0
    feats = feats[FEATURE_ORDER].fillna(0)
    df = pd.concat([df.reset_index(drop=True), feats], axis=1)
    df["domain"] = df["url"].map(lambda u: registrable_domain(hostname_of(u)))
    return df


def pipeline(numeric, ngrams=True):
    transformers = []
    if ngrams:
        transformers.append(("domain_ngrams", TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), min_df=2, max_features=60000,
            sublinear_tf=True), "domain"))
    if numeric:
        transformers.append(("numeric", StandardScaler(), numeric))
    return Pipeline([
        ("prep", ColumnTransformer(transformers, remainder="drop")),
        ("clf", LogisticRegression(max_iter=3000, C=4.0, solver="liblinear",
                                   random_state=SEED)),
    ])


def evaluate(y_true, y_score, threshold=0.5):
    pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    acc = (tp + tn) / len(y_true)
    f1 = 2 * tp / (2 * tp + fp + fn) if (tp + fp + fn) else 0.0
    return dict(acc=acc, f1=f1, fpr=fp / (fp + tn) if (fp + tn) else 0.0,
                tpr=tp / (tp + fn) if (tp + fn) else 0.0,
                tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp),
                auc=float(roc_auc_score(y_true, y_score)))


def main():
    df = load()
    print(f"rows {len(df)} | domains {df['domain'].nunique()} | "
          f"phishing {int(df['label'].sum())} | legit {int((df['label'] == 0).sum())}")

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr, te = next(splitter.split(df, df["label"], groups=df["domain"]))
    train, test = df.iloc[tr], df.iloc[te]
    y_tr, y_te = train["label"].astype(int), test["label"].astype(int)

    model = pipeline(FEATURE_ORDER).fit(train, y_tr)
    score = model.predict_proba(test)[:, 1]
    base = evaluate(y_te, score)
    print("\nbaseline:", {k: round(v, 4) if isinstance(v, float) else v for k, v in base.items()})

    # ---------------- where the errors are ----------------
    test = test.copy()
    test["score"] = score
    test["pred"] = (score >= 0.5).astype(int)
    fps = test[(test["label"] == 0) & (test["pred"] == 1)]
    fns = test[(test["label"] == 1) & (test["pred"] == 0)]

    allow = set()
    if os.path.exists(ALLOWLIST):
        with open(ALLOWLIST, encoding="utf-8") as fh:
            allow = {line.strip().lower() for line in fh if line.strip()}
    print(f"allowlist size {len(allow)}")

    print(f"\nfalse positives: {len(fps)} of {int((test['label'] == 0).sum())} legitimate")
    for feature in ("brand_in_wrong_place", "suspicious_tld", "is_ip", "is_idn",
                    "is_typosquat"):
        share = float(fps[feature].mean()) if len(fps) else 0.0
        print(f"  share with {feature:22} {share:.3f}")

    print(f"\nfalse negatives: {len(fns)} of {int(test['label'].sum())} phishing")
    for feature in ("brand_present", "suspicious_tld", "is_ip", "is_typosquat"):
        share = float(fns[feature].mean()) if len(fns) else 0.0
        print(f"  share with {feature:22} {share:.3f}")
    if allow:
        on_allow = fns["domain"].isin(allow).mean() if len(fns) else 0.0
        print(f"  on an allowlisted domain  {on_allow:.3f}")

    print("  score distribution of missed phish:",
          np.round(np.percentile(fns["score"], [10, 50, 90]), 3).tolist() if len(fns) else "n/a")
    print("  score distribution of flagged legit:",
          np.round(np.percentile(fps["score"], [10, 50, 90]), 3).tolist() if len(fps) else "n/a")

    # how many phishing rows sit on domains whose name carries no brand at all
    missed_no_brand = fns[(fns["brand_present"] == 0) & (fns["suspicious_tld"] == 0)
                          & (fns["is_ip"] == 0)]
    print(f"  missed with no brand, no bad TLD, no IP: {len(missed_no_brand)}")

    # ---------------- which feature block carries it ----------------
    print("\nablation (same split, logistic regression):")
    variants = {
        "ngrams + numeric": (FEATURE_ORDER, True),
        "ngrams only": ([], True),
        "numeric only": (FEATURE_ORDER, False),
        "no brand features": ([f for f in FEATURE_ORDER if f not in BRAND_FEATS], True),
        "no tld features": ([f for f in FEATURE_ORDER if f not in TLD_FEATS], True),
    }
    for label, (numeric, ngrams) in variants.items():
        m = pipeline(numeric, ngrams).fit(train, y_tr)
        s = m.predict_proba(test)[:, 1]
        r = evaluate(y_te, s)
        print(f"  {label:20} acc {r['acc']:.4f}  f1 {r['f1']:.4f}  "
              f"fpr {r['fpr']:.4f}  auc {r['auc']:.4f}")

    # ---------------- cost of the operating point ----------------
    print("\nthreshold policy (cost of a miss = 10x cost of a false alarm):")
    for th in (0.35, 0.40, 0.50, 0.60, 0.65, 0.70):
        r = evaluate(y_te, score, th)
        cost = 10 * r["fn"] + r["fp"]
        print(f"  threshold {th:.2f}: fp {r['fp']:4d}  fn {r['fn']:4d}  "
              f"weighted cost {cost:5d}")


if __name__ == "__main__":
    main()

