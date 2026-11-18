"""Model loading, inference and explanation."""
from __future__ import annotations

import json
from urllib.parse import urlsplit
import os
import time

import re

import joblib
import numpy as np
import pandas as pd

import sys as _sys

_ML = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml")
if _ML not in _sys.path:
    _sys.path.insert(0, _ML)

from features import (BRANDS, BRAND_DOMAINS, FEATURE_ORDER, IPV4_RE,  # noqa: E402
                      extract, hostname_of, levenshtein, registrable_domain)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "ml", "artifacts")

# Registry-restricted Kenyan second-level domains. A name under one of these cannot
# be bought by the public - the registry allocates them to accredited institutions -
# so a name-based model should not be flagging them on string evidence. This is the
# same reasoning as the reputation prior, applied to a namespace instead of a rank.
TRUSTED_SUFFIXES = (".co.ke", ".ac.ke", ".go.ke", ".or.ke", ".sc.ke", ".ne.ke",
                    ".me.ke", ".info.ke", ".mobi.ke", ".co.ug", ".ac.ug", ".go.ug", ".or.ug")


def _address_problem(url: str) -> str:
    """Reject what is not a web address, with a reason a person can act on.

    A name with no ending cannot be resolved by anybody, so scoring it produces a
    confident verdict about nothing. The same is true of a bare integer, of a private
    address, and of a string long enough to be an attack rather than a link.
    """
    raw = (url or "").strip()
    if not raw:
        return "Type or paste a link first."
    if len(raw) > 2048:
        return "That address is too long to be a real link."
    if " " in raw or "\n" in raw:
        return "A link cannot contain spaces."

    probe = raw if re.match(r"^[a-zA-Z][\w+.-]*://", raw) else "http://" + raw.lstrip("/")
    try:
        parts = urlsplit(probe)
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        return "That does not look like a web address."

    if not host:
        return "That does not look like a web address."

    if IPV4_RE.match(host):
        first, second = (int(x) for x in host.split(".")[:2])
        private = (first in (10, 127) or (first == 192 and second == 168)
                   or (first == 172 and 16 <= second <= 31))
        if private:
            return "That is a private address on a local network, not a public one."
        if first == 0 or first >= 224:
            return "That is not a routable address."
        return ""

    if "." not in host:
        return ("That is a name without an ending. A web address needs one, such as "
                "example.com or example.co.ke.")

    labels = [x for x in host.split(".") if x]
    if len(labels[-1]) < 2:
        return "That address ends in a single character, which no registry issues."
    if not re.fullmatch(r"[a-z0-9-]+", labels[-1]):
        return "That address has an ending that is not valid."
    return ""


class Predictor:
    def __init__(self) -> None:
        self.pipeline = joblib.load(os.path.join(ART, "model.joblib"))
        with open(os.path.join(ART, "metrics.json"), encoding="utf-8") as fh:
            self.metrics = json.load(fh)
        self.feature_names = list(self.pipeline.named_steps["prep"].get_feature_names_out())
        # Only the n-gram columns are ever surfaced as evidence; marking them once
        # avoids testing 50,000 names on every request.
        self._ngram_mask = np.array([n.startswith("domain_ngrams__")
                                     for n in self.feature_names], dtype=bool)
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
    def _contributions(self, Xt, top: int = 200):
        """Per-feature contribution to the logit, from an already-transformed matrix.

        The transformed row is sparse and almost entirely zero: a URL activates a few
        hundred character n-grams out of tens of thousands. Multiplying only the stored
        entries, and selecting the strongest with a partial sort, avoids densifying and
        fully sorting a 50,000-wide row on every request.
        """
        if not self.is_linear:
            return None
        coef = np.ravel(self.weights)
        if hasattr(Xt, "tocoo"):
            m = Xt.tocoo()
            idx, vals = m.col, m.data
        else:
            vals = np.ravel(Xt)
            idx = np.arange(vals.size)
        if vals.size == 0:
            return []
        contrib = vals * coef[idx]

        # Restrict to n-gram columns: those are the only features the explanation
        # reports, and doing so here keeps the result exactly what a full sort of all
        # columns would have produced, without sorting tens of thousands of zeros.
        keep = self._ngram_mask[idx]
        if not keep.any():
            return []
        idx, contrib = idx[keep], contrib[keep]

        # Order by weight, then by token. Ties are common (many character n-grams carry
        # an identical coefficient) and numpy's sort does not define their order, so
        # without this the same URL could report different evidence between processes.
        pairs = sorted(((self.feature_names[idx[i]].split("__", 1)[1], float(contrib[i]))
                        for i in range(contrib.size)),
                       key=lambda t: (-t[1], t[0]))
        return [(f"domain_ngrams__{tok}", w) for tok, w in pairs]

    def predict(self, url: str) -> dict:
        t0 = time.perf_counter()
        # protocol-relative links are common in paste buffers and are web addresses
        if (url or "").strip().startswith("//"):
            url = "https:" + url.strip()
        problem = _address_problem(url)
        if problem:
            raise ValueError(problem)
        feats, reasons = extract(url)
        if not feats:
            raise ValueError(reasons[0] if reasons else "Unparseable URL")

        host = hostname_of(url)
        domain = registrable_domain(host) if host else ""
        # One frame, one transform. Building the frame column-by-column and calling
        # transform twice (score, then explanation) accounted for most of the request's
        # server time on a small CPU.
        data = {c: feats.get(c, 0) for c in FEATURE_ORDER}
        data["domain"] = domain
        row = pd.DataFrame([data], columns=list(FEATURE_ORDER) + ["domain"])

        prep = self.pipeline.named_steps["prep"]
        clf = self.pipeline.named_steps["clf"]
        Xt = prep.transform(row)

        if hasattr(clf, "predict_proba"):
            prob = float(clf.predict_proba(Xt)[0, 1])
        else:
            d = float(clf.decision_function(Xt)[0])
            prob = 1 / (1 + np.exp(-d))

        model_prob = prob          # the classifier's own estimate, before any prior
        label = int(prob >= 0.5)
        if prob >= 0.65:
            risk, band = "high", "Likely phishing"
        elif prob >= 0.35:
            risk, band = "medium", "Suspicious"
        else:
            risk, band = "low", "Likely legitimate"

        # "Did you mean ...?", a near miss on a watched brand, or a brand embedded in a
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
        trusted = bool(domain) and (
            domain in self.allowlist or domain.endswith(TRUSTED_SUFFIXES)
        )
        if trusted and not feats.get("brand_in_wrong_place"):
            reputation = "established"
            if prob > 0.15:
                prob = 0.15
            label, risk, band = 0, "low", "Likely legitimate"
            reasons = [
                "This is an established domain, among the 100,000 most visited on the "
                "internet. Name-level evidence is not enough to flag it."
            ]

        if "@" in (url or "").split("//")[-1].split("/")[0]:
            reputation = reputation or "credentials"
            reasons.insert(0, "This link carries a username before the host, which can be "
                              "used to make a different domain appear in front of the real one.")
            if risk == "low":
                risk, band = "medium", "Suspicious"
                prob = max(prob, 0.5)

        evidence = []
        contribs = self._contributions(Xt)
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
            "model_probability": round(model_prob, 4),
            "capped_by_reputation": bool(reputation == "established" and model_prob > prob),
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
