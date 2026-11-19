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


# Hosts where the path belongs to whoever put it there. A report about one path is not a report about
# the domain, so these match on the exact URL only.
SHARED_HOSTS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "buff.ly", "cutt.ly", "rb.gy",
    "shorturl.at", "rebrand.ly", "tiny.cc", "lnkd.in", "short.io", "s.id", "bit.do", "t.ly", "v.gd",
    "t.me", "wa.me", "linktr.ee", "forms.gle", "docs.google.com", "drive.google.com", "sites.google.com",
    "dropbox.com", "onedrive.live.com", "sharepoint.com", "notion.site", "github.io", "netlify.app",
    "vercel.app", "pages.dev", "blogspot.com", "wordpress.com", "wixsite.com", "weebly.com",
    "godaddysites.com", "myshopify.com", "azurewebsites.net", "herokuapp.com", "glitch.me",
    "web.app", "firebaseapp.com", "appspot.com", "cloudfront.net", "s3.amazonaws.com",
    "storage.googleapis.com", "files.wordpress.com", "medium.com", "substack.com", "carrd.co",
}
SHARED_HOST_SUFFIXES = ("github.io", "netlify.app", "vercel.app", "pages.dev", "blogspot.com",
                        "wordpress.com", "azurewebsites.net", "herokuapp.com", "web.app",
                        "firebaseapp.com", "appspot.com")


def is_shared(host: str) -> bool:
    """True for a host where anyone can put anything: a shortener, a blog platform, a file host."""
    host = (host or "").lower().strip(".")
    return host in SHARED_HOSTS or any(host == s or host.endswith("." + s) for s in SHARED_HOST_SUFFIXES)


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
    # On a host where anyone can put anything, the domain is not the reported thing: the path is.
    # A phish on bit.ly/x9f2k says nothing about bit.ly, and treating it as though it did called a
    # link shortener a phishing domain. Those hosts match only when the exact URL matches.
    shared = host in SHARED_HOSTS or any(host == suffix or host.endswith("." + suffix)
                                         for suffix in SHARED_HOST_SUFFIXES)
    exact = url in data["urls"]
    if not exact and (shared or host not in data["hosts"]):
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
