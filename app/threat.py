"""A local snapshot of public phishing lists.

Nothing is fetched when a link is checked: the lists are downloaded when the project is built and
shipped with it. A hit is evidence from outside the name, which is the whole reason it is here: the
model can only judge the shape of an address, and a feed can say "this exact host has been reported".

The claim is deliberately dated. A domain can be re-registered after it is listed, so a hit is a
reason to stop, not a proof about the page that answers today.
"""

from __future__ import annotations

import gzip
import json
import os
import threading
from urllib.parse import urlsplit

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "threat_snapshot.json.gz")
_LOCK = threading.Lock()
_STATE = None


def _load():
    global _STATE
    if _STATE is not None:
        return _STATE
    with _LOCK:
        if _STATE is not None:
            return _STATE
        try:
            with gzip.open(_PATH, "rb") as handle:
                raw = json.load(handle)
            _STATE = {
                "generated": raw.get("generated"),
                "sources": raw.get("sources", []),
                "hosts": set(raw.get("hosts", [])),
                "urls": set(raw.get("urls", [])),
                "targets": raw.get("targets", {}),
            }
        except Exception:                                  # noqa: BLE001
            # a missing or damaged snapshot must not break a scan
            _STATE = {"generated": None, "sources": [], "hosts": set(), "urls": set(), "targets": {}}
    return _STATE


def info() -> dict:
    data = _load()
    return {"generated": data["generated"], "sources": data["sources"],
            "hosts": len(data["hosts"]), "urls": len(data["urls"])}


def lookup(url: str):
    """Return feed evidence for a URL, or None.

    An exact URL match is the strongest form. A host match still counts: the domain itself is what
    was reported, and a campaign usually moves paths on the same host.
    """
    data = _load()
    if not data["generated"] or not url:
        return None
    try:
        parts = urlsplit(url if "://" in url else "http://" + url)
        host = (parts.hostname or "").lower().strip(".")
    except Exception:                                      # noqa: BLE001
        return None
    if not host:
        return None

    # Only the exact host or the exact URL counts. Walking up to a parent domain looked helpful and
    # was not: the public blocklists contain brand domains too, so www.google.com matched a listed
    # "google.com" and a clean address was escalated. A listed parent is a compromise of that domain,
    # not evidence about the subdomain being checked.
    exact = url in data["urls"]
    if not exact and host not in data["hosts"]:
        return None
    matched_host = host
    return {
        "listed": True,
        "host": matched_host,
        "exact_url": bool(exact),
        "target": data["targets"].get(matched_host),
        "generated": data["generated"],
        "sources": [s.get("name") for s in data["sources"]],
    }
