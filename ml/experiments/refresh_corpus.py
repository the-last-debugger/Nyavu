"""
Does refreshing the corpus recover what the model loses over time?

Design, so the answer is not flattering:
  - the fresh negatives are Tranco ranks 100,001-1,000,000, which the reputation ceiling does
    not protect, so nobody gets a free pass
  - fresh rows are split by registrable domain before training, so a domain cannot appear in
    both halves
  - the old 2025 hold-out is kept and re-evaluated after every retrain, to catch a model that
    improves on new data by forgetting the old

Three models, one test set:
  A  deployed recipe, trained on the 2025 corpus only            (the drift baseline)
  B  trained on the 2025 corpus plus 70 per cent of the fresh rows
  C  trained on the fresh rows only                               (does old data still matter?)

Nothing is written over the deployed artefact. This measures first.
"""
from __future__ import annotations

import os
import random
import sys
import zipfile

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "ml"))
from features import FEATURE_ORDER, extract, hostname_of, registrable_domain  # noqa: E402

SEED = 42
OLD = os.path.join(ROOT, "data", "processed", "urls_v2.csv")
DUMP = os.path.join(ROOT, "data", "raw", "phishing_database_active.txt")
TRANCO = os.path.join(ROOT, "data", "raw", "tranco_2026-11-19.csv.zip")
PHISH_DOMAINS = 3000
LEGIT_DOMAINS = 3000


def rows_for(domains, label):
    rows = []
    for domain in domains:
        features, _ = extract("http://" + domain)
        if not features:
            continue
        row = dict(features)
        row["domain"] = registrable_domain(hostname_of("http://" + domain))
        row["label"] = label
        rows.append(row)
    return pd.DataFrame(rows)


def fresh_phishing(limit):
    random.seed(SEED)
    seen, picked = set(), []
    with open(DUMP, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            url = line.split("\t")[0]
            domain = registrable_domain(hostname_of(url))
            if domain and "." in domain and domain not in seen:
                seen.add(domain)
                picked.append(domain)
    random.shuffle(picked)
    return picked[:limit]


def fresh_legit(limit, low=100_000, high=1_000_000):
    with zipfile.ZipFile(TRANCO) as archive:
        name = archive.namelist()[0]
        pool = []
        with archive.open(name) as handle:
            for line in handle:
                rank, domain = line.decode().strip().split(",")
                if low < int(rank) <= high:
                    pool.append(domain)
    random.seed(SEED)
    random.shuffle(pool)
    return pool[:limit]


def model():
    pre = ColumnTransformer([
        ("domain_ngrams", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2,
                                          max_features=60000, sublinear_tf=True), "domain"),
        ("numeric", StandardScaler(), FEATURE_ORDER),
    ], remainder="drop")
    return Pipeline([("prep", pre), ("clf", LogisticRegression(
        max_iter=3000, C=4.0, solver="liblinear", random_state=SEED))])


def scores(y, p):
    pred = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return dict(acc=(tp + tn) / len(y), f1=2 * tp / (2 * tp + fp + fn),
                fpr=fp / (fp + tn), tpr=tp / (tp + fn), auc=roc_auc_score(y, p),
                brier=brier_score_loss(y, p))


def show(name, result):
    print(f"  {name:44} acc {result['acc']:.4f}  f1 {result['f1']:.4f}  "
          f"recall {result['tpr']:.3f}  fpr {result['fpr']:.3f}  auc {result['auc']:.4f}")


def main():
    old = pd.read_csv(OLD)
    old_features = pd.DataFrame([extract(u)[0] for u in old["url"]])
    for column in FEATURE_ORDER:
        if column not in old_features:
            old_features[column] = 0
    old = pd.concat([old.reset_index(drop=True), old_features[FEATURE_ORDER].fillna(0)], axis=1)
    old["domain"] = old["url"].map(lambda u: registrable_domain(hostname_of(u)))

    split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr, te = next(split.split(old, old["label"], groups=old["domain"]))
    old_train, old_test = old.iloc[tr], old.iloc[te]

    fresh = pd.concat([
        rows_for(fresh_phishing(PHISH_DOMAINS), 1),
        rows_for(fresh_legit(LEGIT_DOMAINS), 0),
    ], ignore_index=True)
    fresh = fresh.drop_duplicates(subset=["domain", "label"])
    fresh_split = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=SEED)
    ftr, fte = next(fresh_split.split(fresh, fresh["label"], groups=fresh["domain"]))
    fresh_train, fresh_test = fresh.iloc[ftr], fresh.iloc[fte]
    print(f"old train {len(old_train)} | old test {len(old_test)} | "
          f"fresh train {len(fresh_train)} | fresh test {len(fresh_test)} "
          f"(phishing {int(fresh_test['label'].sum())})")

    print("\nA. trained on the 2025 corpus only")
    a = model().fit(old_train[["domain"] + FEATURE_ORDER], old_train["label"].astype(int))
    show("on the 2025 hold-out", scores(old_test["label"].astype(int),
                                        a.predict_proba(old_test[["domain"] + FEATURE_ORDER])[:, 1]))
    show("on fresh data (drift)", scores(fresh_test["label"].astype(int),
                                         a.predict_proba(fresh_test[["domain"] + FEATURE_ORDER])[:, 1]))

    print("\nB. trained on 2025 plus the fresh training slice")
    combined = pd.concat([old_train, fresh_train], ignore_index=True)
    b = model().fit(combined[["domain"] + FEATURE_ORDER], combined["label"].astype(int))
    show("on the 2025 hold-out", scores(old_test["label"].astype(int),
                                        b.predict_proba(old_test[["domain"] + FEATURE_ORDER])[:, 1]))
    show("on fresh data", scores(fresh_test["label"].astype(int),
                                 b.predict_proba(fresh_test[["domain"] + FEATURE_ORDER])[:, 1]))

    print("\nC. trained on the fresh training slice only")
    c = model().fit(fresh_train[["domain"] + FEATURE_ORDER], fresh_train["label"].astype(int))
    show("on the 2025 hold-out", scores(old_test["label"].astype(int),
                                        c.predict_proba(old_test[["domain"] + FEATURE_ORDER])[:, 1]))
    show("on fresh data", scores(fresh_test["label"].astype(int),
                                 c.predict_proba(fresh_test[["domain"] + FEATURE_ORDER])[:, 1]))


if __name__ == "__main__":
    main()
