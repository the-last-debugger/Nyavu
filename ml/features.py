"""
Nyavu feature extraction.

Design decision
---------------
Every URL is reduced to its *registrable domain* (eTLD+1) before features are
computed. Public benign feeds list registrable domains while public phishing feeds
list full hosts, so a model trained on full host names learns the collection
artefact ("contains a subdomain, therefore phishing") instead of phishing
behaviour. Judging the domain name itself removes that artefact and keeps the two
classes on the same information basis.

All features come from URL text only: no crawling, no DNS, no WHOIS. Inference is
therefore offline-capable, deterministic and fast.

Each feature is paired with a human-readable reason so the interface can explain a
verdict instead of showing a bare probability.
"""
from __future__ import annotations

import math
import re
from urllib.parse import urlsplit

SUSPICIOUS_TLDS = {
    "tk", "ml", "ga", "cf", "gq", "xyz", "top", "club", "buzz", "click", "link",
    "work", "loan", "win", "download", "review", "country", "stream", "gdn",
    "icu", "cyou", "sbs", "monster", "quest", "rest", "bar", "cam", "surf",
    "vip", "live", "shop", "site", "online", "space", "website", "store",
}

# Brand -> the domain that brand actually uses. Used for impersonation reasons and
# for the wrong-place feature. Deliberately focused on brands commonly impersonated
# in Kenya, plus the global services seen in most phishing feeds.
BRAND_DOMAINS = {
    "safaricom": "safaricom.co.ke", "mpesa": "safaricom.co.ke",
    "kcb": "kcbgroup.com", "equity": "equitybank.co.ke",
    "coop": "co-opbank.co.ke", "co-operative": "co-opbank.co.ke",
    "ncba": "ncbagroup.com", "absa": "absabank.co.ke",
    "stanbic": "stanbicbank.co.ke", "dtb": "dtbafrica.com",
    "familybank": "familybank.co.ke", "airtel": "airtel.co.ke",
    "telkom": "telkom.co.ke", "jumia": "jumia.co.ke",
    "kilimall": "kilimall.co.ke", "ecitizen": "ecitizen.go.ke",
    "kra": "kra.go.ke", "helb": "helb.co.ke", "nhif": "nhif.or.ke",
    "gmail": "google.com", "google": "google.com",
    "facebook": "facebook.com", "whatsapp": "whatsapp.com",
    "instagram": "instagram.com", "paypal": "paypal.com",
    "amazon": "amazon.com", "netflix": "netflix.com",
    "microsoft": "microsoft.com", "apple": "apple.com",
    "binance": "binance.com", "coinbase": "coinbase.com",
    "dhl": "dhl.com", "fedex": "fedex.com",
}
BRANDS = list(BRAND_DOMAINS)

MULTI_SUFFIXES = {
    "co.ke", "or.ke", "ac.ke", "go.ke", "ne.ke", "sc.ke", "me.ke", "info.ke",
    "co.uk", "org.uk", "ac.uk", "gov.uk", "co.za", "org.za", "com.au", "net.au",
    "co.in", "com.br", "co.jp", "com.ng", "co.tz", "co.ug", "com.sg", "com.my",
    "com.pk", "com.gh",
}

HOMOGLYPHS = {"rn": "m", "0": "o", "1": "l", "vv": "w", "5": "s", "3": "e",
              "4": "a"}

IPV4_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

FEATURE_ORDER = [
    "domain_len", "num_labels", "num_hyphens", "num_digits", "digit_ratio",
    "hyphen_ratio", "tld_len", "suspicious_tld", "is_ip", "is_idn", "entropy",
    "max_label_len", "brand_present", "brand_in_wrong_place", "is_typosquat",
    "typo_distance", "digit_in_registrable",
]


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def dehomoglyph(s: str) -> str:
    for k, v in HOMOGLYPHS.items():
        s = s.replace(k, v)
    return s


def registrable_domain(host: str) -> str:
    """Approximate eTLD+1 without shipping the full Public Suffix List."""
    host = (host or "").lower().strip(".")
    if not host:
        return ""
    if IPV4_RE.match(host) or host.startswith("["):
        return host
    labels = host.split(".")
    if len(labels) < 2:
        return host
    for n in (3, 2):
        if len(labels) >= n:
            cand = ".".join(labels[-n:])
            if cand in MULTI_SUFFIXES:
                return ".".join(labels[-n - 1:]) if len(labels) > n else host
    return ".".join(labels[-2:])


def hostname_of(url: str) -> str:
    raw = (url or "").strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", raw):
        raw = "http://" + raw
    try:
        return (urlsplit(raw).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def extract(url: str):
    """Return (features: dict[str, float], reasons: list[str])."""
    raw = (url or "").strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", raw):
        raw = "http://" + raw
    try:
        parts = urlsplit(raw)
    except ValueError:
        return {}, ["The URL could not be parsed."]

    host = (parts.hostname or "").lower().rstrip(".")
    scheme = (parts.scheme or "http").lower()
    if not host:
        return {}, ["The URL contains no host name."]
    if not host.startswith("[") and not re.fullmatch(r"[a-z0-9.\-]+", host):
        return {}, ["The address contains characters that are not valid in a host name."]

    is_ip = bool(IPV4_RE.match(host))
    reg = registrable_domain(host) if not is_ip else host
    labels = [x for x in reg.split(".") if x]
    label = labels[0] if labels else ""
    suffix = labels[-1] if len(labels) > 1 else ""
    dehom = dehomoglyph(label)

    # --- brand / impersonation analysis ----------------------------------
    brand_hit = ""
    for b in BRANDS:
        if b in label:
            brand_hit = b
            break
    if not brand_hit:
        for b in BRANDS:
            if len(b) >= 4 and b in dehom and b not in label:
                brand_hit = b
                break

    brand_in_wrong_place = 0
    if brand_hit:
        official = BRAND_DOMAINS[brand_hit]
        if reg not in (official, "www." + official):
            brand_in_wrong_place = 1

    # A brand placed in a subdomain of somebody else's domain is the classic
    # impersonation pattern: "mpesa.co.ke.verify-account.top" is not mpesa.co.ke.
    brand_in_subdomain = ""
    if not is_ip and host != reg and host.endswith("." + reg):
        extra = host[: -len(reg)].rstrip(".")
        compact = extra.replace("-", "").replace(".", "")
        for b in BRANDS:
            if b in compact:
                brand_in_subdomain = b
                brand_in_wrong_place = 1
                break

    cands = [levenshtein(label, b) for b in BRANDS if b not in label]
    typo_distance = min(cands) if cands else 99
    is_typosquat = 1 if 0 < typo_distance <= 2 and len(label) >= 4 else 0

    digits = sum(c.isdigit() for c in reg)
    hyphens = reg.count("-")

    features = {
        "domain_len": len(reg),
        "num_labels": len(labels),
        "num_hyphens": hyphens,
        "num_digits": digits,
        "digit_ratio": digits / max(len(reg), 1),
        "hyphen_ratio": hyphens / max(len(reg), 1),
        "tld_len": len(suffix),
        "suspicious_tld": int(suffix in SUSPICIOUS_TLDS),
        "is_ip": int(is_ip),
        "is_idn": int(host.startswith("xn--") or "xn--" in host),
        "entropy": round(shannon_entropy(reg), 4),
        "max_label_len": max((len(x) for x in labels), default=0),
        "brand_present": int(bool(brand_hit)),
        "brand_in_wrong_place": brand_in_wrong_place,
        "is_typosquat": is_typosquat,
        "typo_distance": min(typo_distance, 20),
        "digit_in_registrable": digits,
    }

    # --- human-readable reasons -----------------------------------------
    reasons = []
    if is_ip:
        reasons.append("The host is a raw IP address rather than a domain name, "
                       "which attackers use to avoid registering a domain.")
    if brand_in_wrong_place:
        if brand_in_subdomain:
            reasons.append(f"The brand '{brand_in_subdomain}' appears in a subdomain, but the "
                           f"address is actually registered to '{reg}'. A brand inside somebody "
                           "else's domain is a common impersonation pattern.")
        else:
            reasons.append(f"The brand '{brand_hit}' appears in this domain, but "
                           f"'{brand_hit}' actually uses {BRAND_DOMAINS[brand_hit]}; "
                           "the extra or altered wording is a common impersonation trick.")
    if is_typosquat:
        nearest = min(BRANDS, key=lambda b: levenshtein(label, b))
        reasons.append(f"The domain '{label}' is within {typo_distance} character(s) of "
                       f"the well-known brand '{nearest}', suggesting a lookalike "
                       "(typosquatting) domain.")
    if features["suspicious_tld"]:
        reasons.append(f"Uses the '.{suffix}' top-level domain, which is frequently "
                       "associated with free or cheap bulk registration and abuse.")
    if features["is_idn"]:
        reasons.append("The host uses Punycode/IDN encoding, which can disguise "
                       "characters that look identical to a legitimate brand.")
    if hyphens >= 2:
        reasons.append(f"The domain contains {hyphens} hyphens, a pattern often used "
                       "to mimic a brand inside a compound domain.")
    if digits >= 4:
        reasons.append(f"The domain contains {digits} digits, which is unusual for "
                       "legitimate brand domains.")
    if features["entropy"] > 3.6 and len(reg) > 18:
        reasons.append("The domain has high character entropy, consistent with "
                       "machine-generated names.")
    if scheme != "https":
        reasons.append("The URL does not use HTTPS.")
    return features, reasons
