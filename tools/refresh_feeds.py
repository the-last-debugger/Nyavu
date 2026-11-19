"""Refresh the local snapshot of public phishing lists.

Run when the project is built, not when a link is checked. The snapshot is what lets a scan say
"this address appears on a public list" without fetching anything at scan time.

    python tools/refresh_feeds.py

Sources: PhishTank (verified online entries, with the brand each one imitates), Phishing Army,
the Blocklist Project, and OpenPhish. Anything that fails is skipped with a line in the log rather
than silently dropped.
"""

from __future__ import annotations

import collections
import csv
import gzip
import io
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "threat_snapshot.json.gz")


def fetch(url: str, timeout: int = 90) -> str:
    # A plain project user-agent is sometimes answered with a throttled page: Phishing Army returned
    # five lines once, which would have quietly cut the snapshot from 338k hosts to 207k. A browser
    # style agent gets the list.
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Nyavu/1.0; +https://nyavu.onrender.com)"})
    raw = urllib.request.urlopen(request, timeout=timeout).read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "ignore")


def host_of(url: str) -> str:
    return url.split("://", 1)[-1].split("/")[0].split("?")[0].split("#")[0].lower().strip(".")


def main() -> None:
    hosts = collections.Counter()
    urls: set[str] = set()
    targets = collections.defaultdict(collections.Counter)
    sources = []

    try:
        rows = list(csv.DictReader(io.StringIO(fetch("https://data.phishtank.com/data/online-valid.csv"))))
        added = 0
        for row in rows:
            url = (row.get("url") or "").strip()
            host = host_of(url) if url else ""
            if not host:
                continue
            hosts[host] += 1
            urls.add(url)
            target = (row.get("target") or "").strip()
            if target and target.lower() != "other":
                targets[host][target] += 1
            added += 1
        sources.append({"name": "PhishTank", "listed": added, "fetched": time.strftime("%Y-%m-%d")})
        print(f"phishtank: {added}")
    except Exception as error:                             # noqa: BLE001
        print("phishtank failed:", str(error)[:80])

    try:
        added = 0
        for line in fetch("https://phishing.army/download/phishing_army_blocklist_extended.txt").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            host = line.split()[0].lower().strip(".")
            if "." in host:
                hosts[host] += 1
                added += 1
        sources.append({"name": "Phishing Army", "listed": added, "fetched": time.strftime("%Y-%m-%d")})
        print(f"phishing.army: {added}")
    except Exception as error:                             # noqa: BLE001
        print("phishing.army failed:", str(error)[:80])

    try:
        added = 0
        for line in fetch("https://raw.githubusercontent.com/blocklistproject/Lists/master/phishing.txt").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            host = line.split()[-1].lower().strip(".")
            if "." in host and host != "0.0.0.0":
                hosts[host] += 1
                added += 1
        sources.append({"name": "Blocklist Project", "listed": added, "fetched": time.strftime("%Y-%m-%d")})
        print(f"blocklistproject: {added}")
    except Exception as error:                             # noqa: BLE001
        print("blocklistproject failed:", str(error)[:80])

    try:
        added = 0
        for line in fetch("https://openphish.com/feed.txt").splitlines():
            url = line.strip()
            if not url.startswith("http"):
                continue
            host = host_of(url)
            if host:
                hosts[host] += 1
                urls.add(url)
                added += 1
        sources.append({"name": "OpenPhish", "listed": added, "fetched": time.strftime("%Y-%m-%d")})
        print(f"openphish: {added}")
    except Exception as error:                             # noqa: BLE001
        print("openphish failed:", str(error)[:80])

    if not hosts:
        print("no sources reachable; leaving the snapshot untouched")
        sys.exit(1)

    named = {host: counter.most_common(1)[0][0] for host, counter in targets.items() if counter}

    # Union with the previous snapshot. A source can be down, throttled, or simply thinner on the
    # day, and coverage must never shrink because of it: a host once reported stays reported.
    previous_hosts: set[str] = set()
    previous_urls: set[str] = set()
    previous_targets: dict[str, str] = {}
    previous_date = None
    try:
        with gzip.open(OUT, "rb") as handle:
            previous = json.load(handle)
        previous_hosts = set(previous.get("hosts", []))
        previous_urls = set(previous.get("urls", []))
        previous_targets = previous.get("targets", {})
        previous_date = previous.get("generated")
    except Exception:                                      # noqa: BLE001
        pass

    merged_hosts = sorted(set(hosts) | previous_hosts)
    merged_urls = sorted(set(urls) | previous_urls)[:80000]
    merged_targets = dict(previous_targets)
    merged_targets.update(named)
    print(f"previous snapshot: {len(previous_hosts):,} hosts ({previous_date}); "
          f"merged: {len(merged_hosts):,}")

    snapshot = {
        "generated": time.strftime("%Y-%m-%d"),
        "previous": previous_date,
        "sources": sources,
        "hosts": merged_hosts,
        "urls": merged_urls,
        "targets": merged_targets,
    }
    with gzip.open(OUT, "wb", compresslevel=9) as handle:
        handle.write(json.dumps(snapshot).encode())
    size = os.path.getsize(OUT) / 1e6
    print(f"hosts {len(snapshot['hosts']):,} | urls {len(snapshot['urls']):,} | "
          f"targets {len(named):,} | {size:.2f} MB")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
