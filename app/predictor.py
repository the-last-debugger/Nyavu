"""Model loading, inference and explanation."""
from __future__ import annotations

import json
import os
import time

import joblib
import numpy as np
import pandas as pd

import sys as _sys

_ML = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
if _ML not in _sys.path:
    _sys.path.insert(0, _ML)

from features import (BRANDS, BRAND_DOMAINS, FEATURE_ORDER, extract,  # noqa: E402
                      hostname_of, levenshtein, registrable_domain)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "ml", "artifacts")


class Predictor:
    def __init__(self) -> None:
        self.pipeline = joblib.load(os.path.join(ART, "model.joblib"))
        with open(os.path.join(ART, "metrics.json"), encoding="utf-8") as fh:
            self.metrics = json.load(fh)
        self.feature_names = list(self.pipeline.named_steps["prep"].get_feature_names_out())
        clf = self.pipeline.named_steps["clf"]
        self.weights = getattr(clf, "coef_", None)
        self.is_linear = self.weights is not None
        self.allowlist = self._load_allowlist()

    @staticmethod
    def _load_allowlist() -> set:
        path = os.path.join(ART, "allowlist.txt")
        try:
            with open(path, encoding="utf-8") as fh:
                return {ln.strip() for ln in fh if ln.strip()}
        except FileNotFoundError:
            return set()

    # ------------------------------------------------------------------ #
    def _contributions(self, row: pd.DataFrame):
        """Per-feature contribution to the logit, in the transformed space."""
        if not self.is_linear:
            return None
        prep = self.pipeline.named_steps["prep"]
        Xt = prep.transform(row)
        coef = np.ravel(self.weights)
        vals = np.asarray(Xt.todense()).ravel() if hasattr(Xt, "todense") else np.ravel(Xt)
        contrib = vals * coef
        order = np.argsort(contrib)[::-1]
        return [(self.feature_names[i], float(contrib[i])) for i in order]

    def predict(self, url: str) -> dict:
        t0 = time.perf_counter()
        feats, reasons = extract(url)
        if not feats:
            raise ValueError(reasons[0] if reasons else "Unparseable URL")

        host = hostname_of(url)
        domain = registrable_domain(host) if host else ""
        row = pd.DataFrame([{**feats, "domain": domain}])
        for c in FEATURE_ORDER:
            row[c] = row.get(c, 0)

        if hasattr(self.pipeline, "predict_proba"):
            prob = float(self.pipeline.predict_proba(row)[0, 1])
        else:
            d = float(self.pipeline.decision_function(row)[0])
            prob = 1 / (1 + np.exp(-d))

        label = int(prob >= 0.5)
        if prob >= 0.65:
            risk, band = "high", "Likely phishing"
        elif prob >= 0.35:
            risk, band = "medium", "Suspicious"
        else:
            risk, band = "low", "Likely legitimate"

        # "Did you mean ...?" — a near miss on a watched brand, or a brand embedded in a
        # longer label ("equitybankk"), which is the common typosquat shape.
        suggestion = None
        if domain:
            lbl = domain.split(".")[0].replace("-", "")
            best = None
            if feats.get("is_typosquat"):
                best = min(BRANDS, key=lambda b: levenshtein(lbl, b))
            else:
                best = next((b for b in BRANDS if b in lbl), None)
            if best:
                official_label = BRAND_DOMAINS[best].split(".")[0].replace("-", "")
                if lbl != official_label:
                    suggestion = {"brand": best, "domain": BRAND_DOMAINS[best]}

        reputation = None

        # Reputation prior: a domain-only model has a false-positive rate that is too
        # high to deploy unchecked, so an established domain (Tranco top 100,000) is not
        # marked on name evidence alone. Surfaced as its own state, not a footnote.
        if domain and domain in self.allowlist and not feats.get("brand_in_wrong_place"):
            reputation = "established"
            if prob > 0.15:
                prob = 0.15
            label, risk, band = 0, "low", "Likely legitimate"
            reasons = [
                "This is an established domain, among the 100,000 most visited on the "
                "internet. Name-level evidence is not enough to flag it."
            ]

        evidence = []
        contribs = self._contributions(row)
        if contribs:
            seen = set()
            for name, weight in contribs:
                if weight <= 0 or len(evidence) >= 5:
                    break
                if not name.startswith("domain_ngrams__"):
                    continue
                token = name.split("__", 1)[1].strip()
                if len(token) < 4 or token in seen:
                    continue
                seen.add(token)
                evidence.append({"token": token, "weight": round(weight, 4)})

        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "url": url,
            "host": host,
            "label": label,
            "verdict": "phishing" if label else "legitimate",
            "risk": risk,
            "band": band,
            "probability": round(prob, 4),
            "confidence": round(max(prob, 1 - prob) * 100, 1),
            "reputation": reputation,
            "suggested": suggestion,
            "reasons": reasons,
            "evidence": evidence,
            "features": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in feats.items()},
            "inference_ms": round(elapsed, 2),
        }

    # ------------------------------------------------------------------ #
    def info(self) -> dict:
        m = self.metrics
        best = m["model_name"]
        return {
            "model": best,
            "version": "1.0.0",
            "trained_on": m["n_train"],
            "tested_on": m["n_test"],
            "dataset_size": m["n_total"],
            "features": len(m["feature_order"]),
            "metrics": m["results"][best],
            "comparison": m["results"],
        }
