"""Look a name up, and nothing more.

The model reads the name. This module answers two questions the name cannot: does anything
answer at that name, and is the certificate in front of it brand new. It resolves the host
and completes a TLS handshake. It never requests a page, never follows a redirect, never
runs anything the host sends back.

The guards matter more than the feature:

- private, loopback, link-local, multicast and metadata addresses are refused before any
  connection is made, so the service cannot be pointed at its own network
- the connection goes to the address that was resolved and checked, not to a fresh lookup,
  which closes the usual DNS rebinding gap
- every step has a small budget, and the whole probe has a total one
- results are cached per host, because a scan run tends to repeat the same names
"""
from __future__ import annotations

import ipaddress
import socket
import ssl
import threading
import time
from datetime import datetime, timezone

RESOLVE_TIMEOUT = 2.0
TLS_TIMEOUT = 3.0
TOTAL_BUDGET = 5.0
CACHE_TTL = 3600
CACHE_MAX = 2048

_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()


def _cached(host: str):
    with _lock:
        hit = _cache.get(host)
    if not hit:
        return None
    stamped, value = hit
    if time.time() - stamped > CACHE_TTL:
        with _lock:
            _cache.pop(host, None)
        return None
    return value


def _store(host: str, value: dict) -> None:
    with _lock:
        if len(_cache) >= CACHE_MAX:
            oldest = min(_cache, key=lambda k: _cache[k][0])
            _cache.pop(oldest, None)
        _cache[host] = (time.time(), value)


def _resolve(host: str):
    """Return (addresses, error). Runs in a thread so a hostile resolver cannot hang us."""
    result: dict = {}

    def work():
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
            result["addresses"] = sorted({info[4][0] for info in infos})
        except Exception as exc:                       # noqa: BLE001 - any failure means "no"
            result["error"] = type(exc).__name__

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    thread.join(RESOLVE_TIMEOUT)
    if thread.is_alive():
        return [], "timeout"
    return result.get("addresses", []), result.get("error")


def classify(address: str) -> str:
    """Name the address class, because a link that resolves inward is not a public link."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return "unknown"
    if ip.is_loopback:
        return "loopback"
    if ip.is_link_local:
        return "link_local"
    if ip.is_private:
        return "private"
    if ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return "reserved"
    return "public"


def _certificate(host: str, address: str):
    """Complete a handshake and read the certificate. No HTTP is ever sent."""
    started = time.time()
    out = {"tls": False, "days_old": None, "issuer": None, "verified": None}

    def handshake(context, verify: bool):
        with socket.create_connection((address, 443), timeout=TLS_TIMEOUT) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls_sock:
                cert = tls_sock.getpeercert()
        return cert, verify

    try:
        cert, verified = handshake(ssl.create_default_context(), True)
    except ssl.SSLCertVerificationError:
        try:
            # the certificate is still worth reading, we simply do not trust it
            insecure = ssl._create_unverified_context()
            cert, verified = handshake(insecure, False)
        except Exception:                              # noqa: BLE001
            return out
    except Exception:                                  # noqa: BLE001
        return out

    if not cert:
        return out

    out["tls"] = True
    out["verified"] = verified
    issuer = cert.get("issuer") or ()
    for part in issuer:
        for key, value in part:
            if key == "organizationName":
                out["issuer"] = value
    not_before = cert.get("notBefore")
    if not_before:
        try:
            issued = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            out["days_old"] = max(0, (datetime.now(timezone.utc) - issued).days)
        except ValueError:
            pass
    out["ms"] = round((time.time() - started) * 1000)
    return out


def probe(host: str) -> dict:
    """Resolve and handshake. Cached, bounded, and safe to call on anything."""
    host = (host or "").strip().lower().rstrip(".")
    if not host or len(host) > 253:
        return {"ok": False, "reason": "no host"}

    hit = _cached(host)
    if hit is not None:
        return hit

    started = time.time()
    if _looks_like_ip(host):
        return {"ok": True, "addresses": [host], "class": classify(host),
                "resolves": True, "cert": {}, "ms": 0, "ip_literal": True}

    addresses, error = _resolve(host)
    if not addresses:
        value = {"ok": True, "resolves": False, "addresses": [], "class": "none",
                 "cert": {}, "error": error, "ms": round((time.time() - started) * 1000)}
        _store(host, value)
        return value

    # every address must be public and routable, or we do not connect at all
    classes = {classify(a) for a in addresses}
    if classes != {"public"}:
        value = {"ok": True, "resolves": True, "addresses": addresses,
                 "class": sorted(classes)[0], "cert": {},
                 "ms": round((time.time() - started) * 1000)}
        _store(host, value)
        return value

    if time.time() - started > TOTAL_BUDGET:
        return {"ok": False, "reason": "budget"}

    cert = _certificate(host, addresses[0])
    value = {"ok": True, "resolves": True, "addresses": addresses, "class": "public",
             "cert": cert, "ms": round((time.time() - started) * 1000)}
    _store(host, value)
    return value


def _looks_like_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
