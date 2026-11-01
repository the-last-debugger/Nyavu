"""
Zero-cost dataset acquisition for Nyavu.

Sources (all free, no API key):
  * OpenPhish public feed          -> phishing URLs (curated, live snapshot)
  * Phishing.Database active list  -> additional phishing URLs (aggregator)
  * Tranco top-1M list             -> legitimate domains (research-grade ranking)

Both classes are normalised to the URL ORIGIN (scheme + host + port).  This is a
deliberate methodological choice: phishing URLs in public feeds usually retain
deep paths while benign domain lists are bare hosts, so training on full strings
lets a classifier learn the collection bias ("has a path => phishing") instead of
phishing behaviour.  Comparing at origin level keeps both classes on the same
information basis.

Output: data/processed/urls.csv  with columns url,label,source
"""
from __future__ import annotations

import csv
import io
import json
import os
import random
import re
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROC = os.path.join(ROOT, "data", "processed")
os.makedirs(RAW, exist_ok=True)
os.makedirs(PROC, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Nyavu academic dataset builder)"}
SEED = 20261101
random.seed(SEED)

PHISH_CAP = 15000          # per source
LEGIT_TARGET = 15000

def fetch(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$")

def host_from_url(u: str):
    """Return (scheme, host, port) from a URL string, or None."""
    u = u.strip()
    if not u or u.startswith("#"):
        return None
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", u):
        u = "http://" + u
    try:
        scheme, rest = u.split("://", 1)
    except ValueError:
        return None
    scheme = scheme.lower()
    if scheme not in ("http", "https"):
        return None
    rest = rest.split("#", 1)[0].split("?", 1)[0]
    authority = rest.split("/", 1)[0]
    authority = authority.rsplit("@", 1)[-1]        # drop userinfo
    if not authority:
        return None
    host, port = authority, None
    if ":" in authority and not authority.startswith("["):
        host, _, p = authority.rpartition(":")
        if p.isdigit():
            port = int(p)
        else:
            host = authority
    host = host.lower().rstrip(".")
    if not host or len(host) > 253 or "." not in host:
        return None
    labels = host.split(".")
    if not all(HOST_RE.match(lab) or lab.startswith("xn--") for lab in labels):
        return None
    return scheme, host, port


def origin(scheme: str, host: str, port) -> str:
    return f"{scheme}://{host}" + (f":{port}" if port and port not in (80, 443) else "")


def go():
    phishing = []   # (url, source)
    legit = []

    # ---------------- phishing: OpenPhish ----------------
    try:
        raw = fetch("https://openphish.com/feed.txt")
        open(os.path.join(RAW, "openphish_feed.txt"), "wb").write(raw)
        lines = [l.strip() for l in raw.decode("utf-8", "ignore").splitlines() if l.strip()]
        lines = [l for l in lines if not l.startswith("#")]
        for l in lines[:PHISH_CAP]:
            phishing.append((l, "OpenPhish"))
        print(f"OpenPhish: {len(lines)} lines, kept {min(len(lines), PHISH_CAP)}")
    except Exception as e:
        print("OpenPhish FAILED:", e)

    # ---------------- phishing: Phishing.Database ----------------
    try:
        raw = fetch("https://raw.githubusercontent.com/Phishing-Database/Phishing.Database/master/phishing-links-ACTIVE.txt")
        open(os.path.join(RAW, "phishing_database_active.txt"), "wb").write(raw)
        lines = [l.strip() for l in raw.decode("utf-8", "ignore").splitlines() if l.strip()]
        lines = [l for l in lines if not l.startswith("#")]
        random.shuffle(lines)
        for l in lines[:PHISH_CAP]:
            phishing.append((l, "Phishing.Database"))
        print(f"Phishing.Database: {len(lines)} lines, kept {min(len(lines), PHISH_CAP)}")
    except Exception as e:
        print("Phishing.Database FAILED:", e)

    # ---------------- legitimate: Tranco ----------------
    tranco_rows = []
    for url in ("https://tranco-list.eu/top-1m.csv.zip",):
        try:
            raw = fetch(url, timeout=180)
            open(os.path.join(RAW, "tranco_top1m.csv.zip"), "wb").write(raw)
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                name = z.namelist()[0]
                text = z.read(name).decode("utf-8", "ignore")
            for line in text.splitlines():
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    tranco_rows.append((int(parts[0]), parts[1]))
            print(f"Tranco: {len(tranco_rows)} domains via {url}")
            break
        except Exception as e:
            print("Tranco zip FAILED:", e)

    if not tranco_rows:
        try:
            meta = json.loads(fetch("https://tranco-list.eu/api/lists/date/latest").decode())
            dl = meta.get("download") or meta.get("list", {}).get("download")
            if dl:
                raw = fetch(dl if dl.endswith(".zip") else dl + "/full", timeout=180)
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    text = z.read(z.namelist()[0]).decode("utf-8", "ignore")
                for line in text.splitlines():
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        tranco_rows.append((int(parts[0]), parts[1]))
                print(f"Tranco API: {len(tranco_rows)} domains")
        except Exception as e:
            print("Tranco API FAILED:", e)

    # sample from the most credible slice of the ranking
    top = [d for r, d in tranco_rows if r <= 200000]
    random.shuffle(top)
    for d in top[:LEGIT_TARGET]:
        legit.append((f"http://{d}", "Tranco"))

    # ---------------- normalise, dedupe, balance ----------------
    ph_hosts, ph_rows = set(), []
    random.shuffle(phishing)
    for u, src in phishing:
        hp = host_from_url(u)
        if not hp:
            continue
        scheme, host, port = hp
        if host in ph_hosts:
            continue
        ph_hosts.add(host)
        ph_rows.append((origin(scheme, host, port), 1, src))

    lg_hosts, lg_rows = set(), []
    for u, src in legit:
        hp = host_from_url(u)
        if not hp:
            continue
        scheme, host, port = hp
        if host in lg_hosts or host in ph_hosts:     # never let a host appear in both
            continue
        lg_hosts.add(host)
        lg_rows.append((origin(scheme, host, port), 0, src))

    n = min(len(ph_rows), len(lg_rows))
    ph_rows, lg_rows = ph_rows[:n], lg_rows[:n]
    rows = ph_rows + lg_rows
    random.shuffle(rows)

    out = os.path.join(PROC, "urls.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["url", "label", "source"])
        w.writerows(rows)

    from collections import Counter
    print(f"\nBalanced rows: {len(rows)}  (phishing {n}, legitimate {n})")
    print("sources:", dict(Counter(r[2] for r in rows)))
    print("written:", out)


if __name__ == "__main__":
    go()
