"""
Builds the popularity prior used by the deployed detector.

A domain-only classifier cannot reach a usable false-positive rate on its own (see
the evaluation in Chapter Four). Commercial filters solve this the same way: they
combine a model with a reputation list. Domains inside the top 100,000 of the Tranco
ranking are treated as established, so name-level evidence alone cannot mark them as
phishing. The trade-off is explicit: phishing hosted on a popular domain is not
detected by name, which is recorded as a limitation.

Output: ml/artifacts/allowlist.txt  (one domain per line)
"""
from __future__ import annotations

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP = os.path.join(ROOT, "data", "raw", "tranco_top1m.csv.zip")
OUT = os.path.join(ROOT, "ml", "artifacts", "allowlist.txt")
TOP_N = 100_000


def main() -> None:
    with zipfile.ZipFile(ZIP) as z:
        text = z.read(z.namelist()[0]).decode("utf-8", "ignore")
    domains = []
    for line in text.splitlines():
        parts = line.strip().split(",")
        if len(parts) >= 2 and parts[0].isdigit() and int(parts[0]) <= TOP_N:
            domains.append(parts[1].lower())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(domains))
    print(f"allowlist: {len(domains):,} domains -> {OUT} "
          f"({os.path.getsize(OUT) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
