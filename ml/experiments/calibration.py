"""
Two numbers the report does not yet state, and should.

1. The dataset has 17,730 rows but 16,185 domains, so rows repeat. A row-level recall can
   therefore understate how many *domains* are caught. Both are reported here.
2. ECE, the average gap between stated risk and observed rate. A "risk out of 100" that is not
   calibrated is a ranking wearing a percentage costume.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT_DIR, "ml"))
from features import FEATURE_ORDER, extract, hostname_of, registrable_domain  # noqa: E402

SEED = 42
DATA = os.path.join(ROOT_DIR, "data", "processed", "urls_v2.csv")


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for low, high in zip(edges[:-1], edges[1:]):
        mask = (p >= low) & (p < high if high < 1 else p <= high)
        if mask.sum():
            total += mask.mean() * abs(p[mask].mean() - y[mask].mean())
    return total


def main():
    df = pd.read_csv(DATA)
    feats = pd.DataFrame([extract(u)[0] for u in df["url"]])
    for column in FEATURE_ORDER:
        if column not in feats:
            feats[column] = 0
    data = pd.concat([df.reset_index(drop=True), feats[FEATURE_ORDER].fillna(0)], axis=1)
    data["domain"] = data["url"].map(lambda u: registrable_domain(hostname_of(u)))
    print(f"rows {len(data)} | unique domains {data['domain'].nunique()} | "
          f"rows per domain {len(data) / data['domain'].nunique():.3f}")

    split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr, te = next(split.split(data, data["label"], groups=data["domain"]))
    train, test = data.iloc[tr], data.iloc[te]
    y_tr = train["label"].astype(int)

    model = Pipeline([
        ("prep", ColumnTransformer([
            ("domain_ngrams", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2,
                                              max_features=60000, sublinear_tf=True), "domain"),
            ("numeric", StandardScaler(), FEATURE_ORDER),
        ], remainder="drop")),
        ("clf", LogisticRegression(max_iter=3000, C=4.0, solver="liblinear", random_state=SEED)),
    ]).fit(train, y_tr)

    test = test.copy()
    test["score"] = model.predict_proba(test)[:, 1]
    y = test["label"].astype(int).to_numpy()

    print(f"\nbrier {brier_score_loss(y, test['score']):.4f} | "
          f"ECE {ece(y, test['score'].to_numpy()):.4f}")

    print("\nrow level versus domain level, threshold 0.50")
    pred_rows = (test["score"] >= 0.5).astype(int)
    phish_rows = test[test["label"] == 1]
    legit_rows = test[test["label"] == 0]
    print(f"  rows:     caught {int(((test['label'] == 1) & (pred_rows == 1)).sum())}"
          f" / {int((test['label'] == 1).sum())} phishing rows")
    print(f"  rows:     false alarms {int(((test['label'] == 0) & (pred_rows == 1)).sum())}"
          f" / {int((test['label'] == 0).sum())} legitimate rows")

    # one verdict per domain: the best score any row on that domain received
    by_domain = test.groupby("domain").agg(label=("label", "max"), score=("score", "max"))
    caught = int(((by_domain["label"] == 1) & (by_domain["score"] >= 0.5)).sum())
    total_phish = int((by_domain["label"] == 1).sum())
    alarmed = int(((by_domain["label"] == 0) & (by_domain["score"] >= 0.5)).sum())
    total_legit = int((by_domain["label"] == 0).sum())
    print(f"  domains:  caught {caught} / {total_phish} = {caught / total_phish:.3f}")
    print(f"  domains:  false alarms {alarmed} / {total_legit} = {alarmed / total_legit:.3f}")

    print(f"\nunique domains among the {int(((test['label'] == 1) & (pred_rows == 0)).sum())} "
          f"missed phishing rows: "
          f"{phish_rows[phish_rows['score'] < 0.5]['domain'].nunique()}")


if __name__ == "__main__":
    main()

