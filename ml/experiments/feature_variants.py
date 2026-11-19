"""
Which offline improvements actually move the numbers.

Everything here uses URL text only: no DNS, no WHOIS, no page fetch. The split and the seed
match ml/train.py so each variant is comparable to the deployed 0.754 / 0.740 / 19.76%.

Variants
    V0  deployed recipe: 17 features + char n-grams
    V1  V0 with a much larger brand list
    V2  V1 plus character-shape features (consonant runs, hex-like, repetition)
    V3  V2 plus a fold-safe TLD prior learned from the training half only
    V4  V3 plus n-grams (full recipe)
    V5  gradient boosting on V3 numerics, to see whether interactions beat a linear model
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT_DIR, "ml"))
import features as F  # noqa: E402

SEED = 42
DATA = os.path.join(ROOT_DIR, "data", "processed", "urls_v2.csv")

EXTRA_BRANDS = {
    # Kenyan banks, telcos, government and commerce
    "stanchart": "sc.com", "standardchartered": "sc.com", "barclays": "barclays.co.ke",
    "gtbank": "gtbank.com", "ecobank": "ecobank.com", "imbank": "imbank.co.ke",
    "sidian": "sidianbank.co.ke", "kingdom": "kingdombank.co.ke", "nic": "nicbank.co.ke",
    "cfc": "cfcstanbic.co.ke", "mwalimu": "mwalimubank.co.ke", "stima": "stima.co.ke",
    "sacco": "sacco.co.ke", "faiba": "faiba.co.ke", "jamii": "jamiitelecom.co.ke",
    "nssf": "nssf.or.ke", "sha": "sha.go.ke", "kplc": "kplc.co.ke", "kengen": "kengen.co.ke",
    "kbc": "kbc.co.ke", "citizen": "citizen.digital", "ntv": "ntvkenya.co.ke",
    "jiji": "jiji.co.ke", "bolt": "bolt.eu", "uber": "uber.com", "glovo": "glovoapp.com",
    "little": "little.africa", "showmax": "showmax.com", "dstv": "dstv.com",
    # global services common in feeds
    "outlook": "outlook.com", "office365": "office.com", "onedrive": "onedrive.live.com",
    "dropbox": "dropbox.com", "wetransfer": "wetransfer.com", "adobe": "adobe.com",
    "docusign": "docusign.com", "telegram": "telegram.org", "tiktok": "tiktok.com",
    "twitter": "twitter.com", "linkedin": "linkedin.com", "spotify": "spotify.com",
    "steam": "steampowered.com", "roblox": "roblox.com", "epicgames": "epicgames.com",
    "playstation": "playstation.com", "xbox": "xbox.com", "zoom": "zoom.us",
    "coinbase": "coinbase.com", "binance": "binance.com", "metamask": "metamask.io",
    "blockchain": "blockchain.com", "kraken": "kraken.com", "wise": "wise.com",
    "revolut": "revolut.com", "skrill": "skrill.com", "neteller": "neteller.com",
    "visa": "visa.com", "mastercard": "mastercard.com", "amex": "americanexpress.com",
    "chase": "chase.com", "wellsfargo": "wellsfargo.com", "citibank": "citi.com",
    "hsbc": "hsbc.com", "aliexpress": "aliexpress.com", "alibaba": "alibaba.com",
    "shein": "shein.com", "etsy": "etsy.com", "ebay": "ebay.com", "walmart": "walmart.com",
    "booking": "booking.com", "airbnb": "airbnb.com", "ups": "ups.com",
}


def shape_features(url: str) -> dict:
    """Character shape of the registrable label. Offline, no lookups."""
    host = F.hostname_of(url)
    reg = F.registrable_domain(host)
    label = reg.split(".")[0] if reg else ""
    letters = [c for c in label if c.isalpha()]
    vowels = sum(1 for c in letters if c in "aeiou")
    longest_run = run = 0
    for c in label:
        if c.isalpha() and c not in "aeiou":
            run += 1
            longest_run = max(longest_run, run)
        else:
            run = 0
    repeated = 0
    for i in range(1, len(label)):
        if label[i] == label[i - 1]:
            repeated += 1
    hex_like = int(bool(np and __import__("re").fullmatch(r"[0-9a-f]{12,}", label)))
    return {
        "vowel_ratio": vowels / max(len(letters), 1),
        "consonant_run": longest_run,
        "repeated_chars": repeated,
        "hex_like": hex_like,
        "letter_digit_switches": sum(
            1 for i in range(1, len(label))
            if label[i].isdigit() != label[i - 1].isdigit()
        ),
    }


def build(use_extra_brands: bool):
    if use_extra_brands:
        F.BRANDS = list(set(F.BRANDS) | set(EXTRA_BRANDS))
        F.BRAND_DOMAINS.update(EXTRA_BRANDS)

    df = pd.read_csv(DATA)
    rows = []
    for url in df["url"]:
        feats, _ = F.extract(url)
        feats.update(shape_features(url))
        rows.append(feats)
    feats = pd.DataFrame(rows).fillna(0)
    df = pd.concat([df.reset_index(drop=True), feats], axis=1)
    df["domain"] = df["url"].map(lambda u: F.registrable_domain(F.hostname_of(u)))
    df["tld"] = df["domain"].str.rsplit(".", n=1).str[-1]
    return df


def metrics(y, p, th=0.5):
    pred = (p >= th).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return dict(acc=(tp + tn) / len(y), f1=2 * tp / (2 * tp + fp + fn),
                fpr=fp / (fp + tn), auc=roc_auc_score(y, p),
                brier=brier_score_loss(y, p), fp=int(fp), fn=int(fn))


def lr(numeric, ngrams):
    transformers = [("numeric", StandardScaler(), numeric)]
    if ngrams:
        transformers.insert(0, ("domain_ngrams", TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), min_df=2, max_features=60000,
            sublinear_tf=True), "domain"))
    return Pipeline([("prep", ColumnTransformer(transformers, remainder="drop")),
                     ("clf", LogisticRegression(max_iter=3000, C=4.0,
                                                solver="liblinear", random_state=SEED))])


def report(label, result):
    print(f"{label:46} acc {result['acc']:.4f}  f1 {result['f1']:.4f}  "
          f"fpr {result['fpr']:.4f}  auc {result['auc']:.4f}  brier {result['brier']:.4f}")


def main():
    base_cols = list(F.FEATURE_ORDER)
    shape_cols = ["vowel_ratio", "consonant_run", "repeated_chars", "hex_like",
                  "letter_digit_switches"]

    for label, extra in (("V0 deployed recipe", False), ("V1 bigger brand list", True)):
        df = build(extra)
        split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
        tr, te = next(split.split(df, df["label"], groups=df["domain"]))
        train, test = df.iloc[tr], df.iloc[te]
        y_tr, y_te = train["label"].astype(int), test["label"].astype(int)

        model = lr(base_cols, True).fit(train, y_tr)
        report(label, metrics(y_te, model.predict_proba(test)[:, 1]))

        if not extra:
            baseline_df = (train, test, y_tr, y_te)
            continue

        for name, cols in (("V2 + shape features", base_cols + shape_cols),):
            m = lr(cols, True).fit(train, y_tr)
            report(name, metrics(y_te, m.predict_proba(test)[:, 1]))

        # fold-safe TLD prior: learned on the training half, smoothed towards the base rate
        prior = y_tr.mean()
        stats = pd.DataFrame({"tld": train["tld"], "y": y_tr}).groupby("tld")["y"].agg(["mean", "count"])
        smooth = 20.0
        encoding = ((stats["mean"] * stats["count"] + prior * smooth) /
                    (stats["count"] + smooth)).to_dict()
        for frame in (train, test):
            frame["tld_prior"] = frame["tld"].map(encoding).fillna(prior)

        cols = base_cols + shape_cols + ["tld_prior"]
        m3 = lr(cols, True).fit(train, y_tr)
        report("V3 + TLD prior (fold-safe)", metrics(y_te, m3.predict_proba(test)[:, 1]))

        hgb = Pipeline([
            ("prep", ColumnTransformer([("numeric", StandardScaler(), cols)],
                                       remainder="drop")),
            ("clf", HistGradientBoostingClassifier(
                max_iter=400, learning_rate=0.06, random_state=SEED)),
        ])
        m5 = hgb.fit(train, y_tr)
        report("V5 gradient boosting, numeric only", metrics(y_te, m5.predict_proba(test)[:, 1]))


if __name__ == "__main__":
    main()

