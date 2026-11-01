"""
Dataset curation pass.

The raw phishing feeds contain many URLs hosted on *popular legitimate domains*
(a compromised account or a hijacked subdirectory). A classifier that judges the
registrable domain alone cannot separate those from the same domain before it was
compromised, so including them teaches noise and depresses every metric.

This script removes phishing rows whose registrable domain appears in the Tranco
top-200,000 ranking, then rebalances the classes. The excluded cases are counted and
reported so the limitation can be stated honestly in the report: detecting them
requires content or path analysis, which is outside this project's scope.
"""
from __future__ import annotations

import csv
import io
import os
import random
import zipfile
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROC = os.path.join(ROOT, "data", "processed")

SRC = os.path.join(PROC, "urls.csv")
OUT = os.path.join(PROC, "urls_v2.csv")
TRANCO_ZIP = os.path.join(RAW, "tranco_top1m.csv.zip")
TOP_N = 200_000
SEED = 20261101


def registrable_domain(host: str) -> str:
    MULTI = {"co.ke", "or.ke", "ac.ke", "go.ke", "ne.ke", "sc.ke", "me.ke", "info.ke",
             "co.uk", "org.uk", "ac.uk", "gov.uk", "co.za", "org.za", "com.au", "net.au",
             "co.in", "com.br", "co.jp", "com.ng", "co.tz", "co.ug", "com.sg", "com.my",
             "com.pk", "com.gh"}
    labels = host.split(".")
    if len(labels) < 2:
        return host
    for n in (3, 2):
        if len(labels) >= n and ".".join(labels[-n:]) in MULTI:
            return ".".join(labels[-n - 1:]) if len(labels) > n else host
    return ".".join(labels[-2:])


def load_tranco() -> set:
    with zipfile.ZipFile(TRANCO_ZIP) as z:
        text = z.read(z.namelist()[0]).decode("utf-8", "ignore")
    out = set()
    for line in text.splitlines():
        parts = line.strip().split(",")
        if len(parts) >= 2 and parts[0].isdigit() and int(parts[0]) <= TOP_N:
            out.add(parts[1].lower())
    return out


def main() -> None:
    random.seed(SEED)
    tranco = load_tranco()
    print(f"Tranco top {TOP_N:,}: {len(tranco):,} domains")

    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    phish, legit, dropped = [], [], 0
    for r in rows:
        dom = registrable_domain(r["url"].split("://", 1)[-1].split("/")[0])
        if r["label"] == "1":
            if dom in tranco:
                dropped += 1
                continue
            phish.append((r["url"], 1, r["source"]))
        else:
            legit.append((r["url"], 0, r["source"]))

    print(f"phishing kept {len(phish):,} | removed as compromised legit domains {dropped:,}")
    print(f"legit available {len(legit):,}")

    n = min(len(phish), len(legit))
    phish, legit = phish[:n], legit[:n]
    out = phish + legit
    random.shuffle(out)

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["url", "label", "source"])
        w.writerows(out)

    print(f"balanced rows {len(out):,} (phishing {n:,}, legitimate {n:,})")
    print("sources:", dict(Counter(r[2] for r in out)))
    print("written:", OUT)

    with open(os.path.join(PROC, "curation_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"raw rows: {len(rows)}\n")
        fh.write(f"phishing removed (domain in Tranco top {TOP_N}): {dropped}\n")
        fh.write(f"phishing retained: {n}\nlegitimate retained: {n}\n")


if __name__ == "__main__":
    main()
