"""
Nyavu model training and evaluation.

Pipeline
    URL text -> [ handcrafted host features | char n-gram TF-IDF of the host ]
             -> ColumnTransformer -> classifier

Three classifiers are trained and compared so the report can justify the deployed
choice quantitatively.  Splits are grouped by registrable domain: the same domain
never appears in both train and test, which prevents the inflated accuracy that
comes from leaking near-duplicate URLs across the split.

Model selection rule
    The classifier with the highest F1 is preferred, except that a model which
    cannot emit a calibrated probability is only selected if it beats the best
    probabilistic model by more than MARGIN.  The interface reports a risk
    percentage, so calibrated output is a functional requirement, not a detail.
"""
from __future__ import annotations

import json
import os
import time

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score,
                             roc_curve)
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from features import FEATURE_ORDER, extract, hostname_of, registrable_domain

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "processed", "urls_v2.csv")
ART = os.path.join(ROOT, "ml", "artifacts")
FIG = os.path.join(ROOT, "docs", "figures")
os.makedirs(ART, exist_ok=True)
os.makedirs(FIG, exist_ok=True)
SEED = 42
MARGIN = 0.01          # F1 margin a non-probabilistic model must clear


def build_frame(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    rows = [extract(u)[0] for u in df["url"]]
    feats = pd.DataFrame(rows)
    for c in FEATURE_ORDER:
        if c not in feats:
            feats[c] = 0
    feats = feats[FEATURE_ORDER]
    df = pd.concat([df.reset_index(drop=True), feats], axis=1)
    df["domain"] = df["url"].map(lambda u: registrable_domain(hostname_of(u)))
    return df


def make_pipeline(clf) -> Pipeline:
    pre = ColumnTransformer(
        transformers=[
            ("domain_ngrams", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5),
                                              min_df=2, max_features=60000,
                                              sublinear_tf=True), "domain"),
            ("numeric", StandardScaler(), FEATURE_ORDER),
        ],
        remainder="drop",
    )
    return Pipeline([("prep", pre), ("clf", clf)])


def scores_for(y_true, y_pred, y_score) -> dict:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else 0.0,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def threshold_sweep(y_true, y_score):
    rows = []
    for th in (0.20, 0.30, 0.35, 0.40, 0.50, 0.60, 0.65, 0.70, 0.80):
        pred = (y_score >= th).astype(int)
        cm = confusion_matrix(y_true, pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        rows.append({
            "threshold": th,
            "precision": round(float(precision_score(y_true, pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, pred, zero_division=0)), 4),
            "false_positive_rate": round(float(fp / (fp + tn)), 4),
            "false_negative_rate": round(float(fn / (fn + tp)), 4),
        })
    return rows


def plot_roc(curves, path):
    fig, ax = plt.subplots(figsize=(6.0, 4.4), dpi=220)
    for name, (fpr, tpr, auc) in curves.items():
        ax.plot(fpr, tpr, lw=1.8, label=f"{name} (AUC = {auc:.4f})")
    ax.plot([0, 1], [0, 1], "k--", lw=0.9, alpha=.6, label="Chance")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curves on the domain-disjoint hold-out set")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_comparison(results, path):
    names = list(results)
    metrics = ["accuracy", "precision", "recall", "f1"]
    x = np.arange(len(metrics))
    w = 0.8 / len(names)
    fig, ax = plt.subplots(figsize=(6.6, 2.9), dpi=220)
    for i, n in enumerate(names):
        vals = [results[n][m] * 100 for m in metrics]
        ax.bar(x + i * w, vals, w, label=n)
    ax.set_xticks(x + w * (len(names) - 1) / 2)
    ax.set_xticklabels([m.capitalize() for m in metrics])
    ax.set_ylabel("Percent")
    ax.set_ylim(85, 100.5)
    ax.legend(fontsize=8, frameon=False, ncol=3)
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    df = build_frame(DATA)
    X = df[["domain"] + FEATURE_ORDER]
    y = df["label"].astype(int)
    groups = df["domain"]

    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr_idx, te_idx = next(gss.split(X, y, groups=groups))
    Xtr, Xte = X.iloc[tr_idx], X.iloc[te_idx]
    ytr, yte = y.iloc[tr_idx], y.iloc[te_idx]
    print(f"train {len(Xtr)} | test {len(Xte)} | domain overlap "
          f"{len(set(groups.iloc[tr_idx]) & set(groups.iloc[te_idx]))}")

    candidates = {
        "Logistic Regression": LogisticRegression(max_iter=3000, C=4.0,
                                                  solver="liblinear", random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=150, min_samples_leaf=5,
                                                n_jobs=-1, random_state=SEED),
        "Linear SVM": LinearSVC(C=0.5, max_iter=20000, random_state=SEED),
    }

    results, fitted, curves, probs = {}, {}, {}, {}
    for name, clf in candidates.items():
        pipe = make_pipeline(clf)
        t0 = time.perf_counter()
        pipe.fit(Xtr, ytr)
        train_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        y_pred = pipe.predict(Xte)
        infer_ms = (time.perf_counter() - t0) / len(Xte) * 1000

        if hasattr(pipe, "predict_proba"):
            y_score = pipe.predict_proba(Xte)[:, 1]
        else:
            d = pipe.decision_function(Xte)
            y_score = 1 / (1 + np.exp(-d))
        probs[name] = y_score

        r = scores_for(yte, y_pred, y_score)
        r["train_seconds"] = round(train_s, 2)
        r["inference_ms_per_url"] = round(infer_ms, 4)
        r["calibrated_probability"] = hasattr(pipe, "predict_proba")
        results[name] = r
        fitted[name] = pipe
        curves[name] = (*roc_curve(yte, y_score)[:2], r["roc_auc"])
        print(f"{name:20} acc={r['accuracy']:.4f} f1={r['f1']:.4f} "
              f"fpr={r['false_positive_rate']:.4f} auc={r['roc_auc']:.4f}")

    # ---- selection rule --------------------------------------------------
    probabilistic = {k: v for k, v in results.items() if v["calibrated_probability"]}
    best_prob = max(probabilistic, key=lambda k: probabilistic[k]["f1"])
    best_any = max(results, key=lambda k: results[k]["f1"])
    if (best_any != best_prob
            and results[best_any]["f1"] - results[best_prob]["f1"] > MARGIN):
        chosen = best_any
        rationale = (f"{best_any} returned the highest F1 and exceeded {best_prob} by more "
                     f"than {MARGIN}, so its lack of calibrated output was accepted.")
    else:
        chosen = best_prob
        rationale = (f"{best_prob} was selected because it produces calibrated probabilities, "
                     f"which the interface depends on, and its F1 was within {MARGIN} of the "
                     f"highest score ({best_any}).")
    print(f"\nSelected: {chosen}\n  {rationale}")
    best = fitted[chosen]

    # ---- grouped 5-fold CV on the deployed model -------------------------
    gkf = GroupKFold(n_splits=5)
    cv = cross_validate(best, X, y, groups=groups, cv=gkf,
                        scoring=["accuracy", "precision", "recall", "f1", "roc_auc"],
                        n_jobs=1)
    cv_summary = {k.replace("test_", ""): {"mean": float(np.mean(v)), "std": float(np.std(v))}
                  for k, v in cv.items() if k.startswith("test_")}
    print("CV:", {k: round(v["mean"], 4) for k, v in cv_summary.items()})

    sweep = threshold_sweep(yte, probs[chosen])

    # ---- figures ---------------------------------------------------------
    plot_roc(curves, os.path.join(FIG, "roc_curves.png"))
    plot_comparison(results, os.path.join(FIG, "model_comparison.png"))

    # ---- persist ---------------------------------------------------------
    joblib.dump(best, os.path.join(ART, "model.joblib"))
    payload = {
        "model_name": chosen,
        "selection_rationale": rationale,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "n_total": int(len(df)),
        "n_positive": int(y.sum()),
        "n_negative": int((y == 0).sum()),
        "n_domains": int(groups.nunique()),
        "feature_order": FEATURE_ORDER,
        "results": results,
        "cv": cv_summary,
        "threshold_sweep": sweep,
        "seed": SEED,
    }
    with open(os.path.join(ART, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    out = df.iloc[te_idx][["url", "label", "source"]].copy()
    out["predicted"] = best.predict(Xte)
    out["probability"] = np.round(probs[chosen], 6)
    out.to_csv(os.path.join(ART, "holdout_predictions.csv"), index=False)

    print("artifacts ->", ART)
    print("figures   ->", FIG)


if __name__ == "__main__":
    main()
