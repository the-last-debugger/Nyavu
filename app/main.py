"""Nyavu API - FastAPI application entry point."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
import secrets
import base64
import io
import hashlib
import os
import re
import time

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db
from . import threat
from .predictor import Predictor

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")

log = logging.getLogger("nyavu")

app = FastAPI(
    title="Nyavu API",
    version="1.0.0",
    description="Machine-learning phishing URL detection with explanations.",
)

state: dict = {}


def _init_storage() -> bool:
    """Prepare the database, but do not let it decide whether the service starts.

    The free-tier database suspends when idle, and a spin-up can reach this code while the
    database is still waking. Refusing to start in that window turns a slow afternoon into an
    outage, so storage is attempted with a short backoff and then reported as degraded: every
    verdict still works, and only history and statistics are unavailable until the next write.
    """
    for attempt in (1, 2, 3):
        try:
            db.init_db()
            db.migrate_auth()
            return True
        except Exception as exc:                      # noqa: BLE001 - storage is best effort
            log.warning("storage not ready (attempt %d/3): %s", attempt, exc)
            time.sleep(0.4 * attempt)
    log.error("starting without storage; verdicts will still be served")
    return False


@app.on_event("startup")
def _startup() -> None:
    state["storage_ready"] = _init_storage()
    state["predictor"] = Predictor()
    m = state["predictor"].info()["metrics"]
    try:
        db.record_model(state["predictor"].info()["model"], "1.0.0",
                        m["accuracy"], m["f1"])
    except Exception as exc:                          # noqa: BLE001
        log.warning("model record not written: %s", exc)



# --------------------------------------------------------------------------- #
# Abuse protection. Deliberately in-process: one instance, small audience, and no
# extra dependency. If the service is ever scaled out this must move to Redis.
# --------------------------------------------------------------------------- #
_RATE: dict[tuple[str, str], list[float]] = {}
WINDOW = 60


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _limit_for(path: str) -> tuple[str, int] | None:
    if path == "/api/predict":
        # A person comparing several links, or a demonstrator working through a list, reaches
        # thirty calls in a minute without trying. Sixty still stops a script and does not
        # interrupt a person.
        return "predict", 60
    if path == "/api/scan/bulk":
        return "bulk", 5
    if path.startswith("/api/auth"):
        return "auth", 10
    return None


@app.middleware("http")
async def protect(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    # A link checker is a natural target for injected scripts, so the policy is strict:
    # no third-party origins at all, and only our own bundle may execute.
    response.headers.setdefault("Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'")
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")

    # Nothing was setting a caching policy, so browsers fell back to guessing. Images and
    # fonts are content addressed by their own content and never change under the same
    # name, so they can be held; the shell and the worker must revalidate, or a deploy
    # takes an unpredictable time to arrive.
    path = request.url.path
    if path == "/sw.js" or path == "/" or path.endswith(".html") or path.startswith("/learn"):
        response.headers.setdefault("Cache-Control", "no-cache")
    elif path.endswith((".webp", ".png", ".ico", ".woff2")):
        response.headers.setdefault("Cache-Control", "public, max-age=604800")
    elif path.endswith((".css", ".js")):
        if request.query_params.get("v"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers.setdefault("Cache-Control", "public, max-age=300, must-revalidate")
    return response


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    rule = _limit_for(request.url.path)
    if rule:
        name, cap = rule
        key = (_client_ip(request), name)
        now = time.time()
        hits = [t for t in _RATE.get(key, []) if now - t < WINDOW]
        if len(hits) >= cap:
            return JSONResponse(
                {"detail": "Too many requests. Please wait a minute and try again."},
                status_code=429,
            )
        hits.append(now)
        _RATE[key] = hits
        if len(_RATE) > 20000:
            _RATE.clear()
    return await call_next(request)

# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class UrlIn(BaseModel):
    url: str = Field(..., min_length=3, max_length=2048)


class Credentials(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field("", max_length=120)



def cookie_secure() -> bool:
    """Cookies are marked Secure when the deployment says it is served over HTTPS."""
    return os.environ.get("NYAVU_COOKIE_SECURE", "0") == "1"

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def current_user(request: Request):
    return db.user_for_token(request.cookies.get("pg_session", ""))


def _store_scan(user_id, url: str, result: dict) -> bool:
    """Record a scan, but never at the cost of the verdict.

    The free-tier database suspends when idle, so the first request after a quiet period can
    lose its connection mid-write. A person who asked for a verdict should still get one: the
    write is retried once and then abandoned with a log line, because losing the record is a
    smaller failure than losing the answer.
    """
    for attempt in (1, 2):
        try:
            db.add_scan(user_id, url, result["host"], result["verdict"], result["risk"],
                        result["probability"], result["inference_ms"])
            return True
        except Exception as exc:                     # noqa: BLE001 - storage is best effort
            if attempt == 2:
                log.warning("scan not stored after retry: %s", exc)
            else:
                time.sleep(0.2)
    return False


def _scan_and_store(url: str, user_id):
    try:
        result = state["predictor"].predict(url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    result = _apply_credential_policy(result)
    result = _apply_hosting_policy(result)
    result = _apply_feed(result)
    result["stored"] = _store_scan(user_id, url, result)
    return result


_OFFICIAL = set()


def _official_domains() -> set:
    """The institution list, loaded once, as the domains a blocklist cannot condemn."""
    global _OFFICIAL
    if _OFFICIAL:
        return _OFFICIAL
    try:
        import json as _json
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "data", "institutions.json"), encoding="utf-8") as handle:
            data = _json.load(handle)
        _OFFICIAL = {row["domain"].lower().strip(".") for row in data.get("entries", [])}
    except Exception:                                      # noqa: BLE001
        _OFFICIAL = set()
    return _OFFICIAL


_LEGITIMACY = {}


def _legitimacy(name: str) -> dict:
    """Positive evidence for an official domain, gathered when the list was built."""
    global _LEGITIMACY
    if not _LEGITIMACY:
        try:
            import json as _json
            with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "data", "legitimacy.json"), encoding="utf-8") as handle:
                _LEGITIMACY = _json.load(handle)
        except Exception:                                  # noqa: BLE001
            _LEGITIMACY = {}
    for domain, record in _LEGITIMACY.items():
        if record.get("name") == name:
            return {"name": name, "domain": domain, "category": record.get("category"),
                    "evidence": record.get("evidence", [])}
    return {"name": name, "evidence": []}


_KNOWN = {}


def _known_sites() -> dict:
    """Worldwide sites we know, kept apart from the institution list.

    The tier matters: an institution domain is one we can name, a known site is one everybody visits.
    Both are cleared, but only the first is called official.
    """
    global _KNOWN
    if not _KNOWN:
        try:
            import json as _json
            with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "data", "known_sites.json"), encoding="utf-8") as handle:
                _KNOWN = _json.load(handle)
        except Exception:                                  # noqa: BLE001
            _KNOWN = {}
    return _KNOWN


# Platforms where any stranger can create a subdomain. Their reputation must never be lent down to
# one of those subdomains: "evil-verify.blogspot.com" was being cleared because blogspot.com is a
# well known site, which is exactly the shape a hosted phishing page takes.
_USER_CONTENT = {
    "blogspot.com", "blogspot.co.ke", "wordpress.com", "tumblr.com", "weebly.com", "wixsite.com",
    "github.io", "gitlab.io", "pages.dev", "workers.dev", "netlify.app", "vercel.app",
    "web.app", "firebaseapp.com", "herokuapp.com", "appspot.com", "amazonaws.com",
    "cloudfront.net", "azurewebsites.net", "sharepoint.com", "googleusercontent.com",
    "glitch.me", "replit.app", "000webhostapp.com", "webflow.io", "surge.sh",
}


def _registrable(host: str) -> str:
    labels = (host or "").lower().strip(".").split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else (host or "").lower()


def _known_site(host: str):
    host = (host or "").lower().strip(".")
    if not host:
        return None
    if _registrable(host) in _USER_CONTENT:
        return None
    known = _known_sites()
    labels = host.split(".")
    for index in range(0, max(0, len(labels) - 1)):
        candidate = ".".join(labels[index:])
        if candidate in known:
            record = known[candidate]
            return {"domain": candidate, "rank": record.get("rank"),
                    "evidence": record.get("evidence", [])}
    return None


def _official_name(host: str):
    """The institution whose published domain this is, or None."""
    host = (host or "").lower().strip(".")
    labels = host.split(".") if host else []
    for index in range(0, max(0, len(labels) - 1)):
        candidate = ".".join(labels[index:])
        for row in _official_rows():
            if row["domain"].lower().strip(".") == candidate:
                return row["name"]
    return None


_OFFICIAL_ROWS = []


def _official_rows() -> list:
    global _OFFICIAL_ROWS
    if _OFFICIAL_ROWS:
        return _OFFICIAL_ROWS
    try:
        import json as _json
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "data", "institutions.json"), encoding="utf-8") as handle:
            _OFFICIAL_ROWS = _json.load(handle).get("entries", [])
    except Exception:                                      # noqa: BLE001
        _OFFICIAL_ROWS = []
    return _OFFICIAL_ROWS


def _is_official_domain(host: str) -> bool:
    host = (host or "").lower().strip(".")
    if not host:
        return False
    official = _official_domains()
    if host in official:
        return True
    labels = host.split(".")
    for index in range(1, len(labels) - 1):
        if ".".join(labels[index:]) in official:
            return True
    return False


_CREDENTIAL_PATH = re.compile(
    r"(login|log-in|signin|sign-in|verify|verification|account|password|passwd|otp|unlock|"
    r"recover|secure|update|confirm)", re.I)


def _credential_imitator(result: dict) -> bool:
    """A brand in a label its owner does not control, on a path that asks for a secret.

    This is not a borderline case and should not be presented as one: the address is built to take a
    password or a one-time code from someone who thinks they are talking to the brand.
    """
    features = result.get("features") or {}
    if not features.get("brand_in_wrong_place"):
        return False
    return bool(_CREDENTIAL_PATH.search(result.get("url", "")))


def _apply_credential_policy(result: dict) -> dict:
    if result.get("verdict") == "phishing" or not _credential_imitator(result):
        return result
    result["verdict"] = "phishing"
    result["risk"] = "high"
    result["band"] = "Likely phishing"
    result["label"] = 1
    result["probability"] = max(float(result.get("probability") or 0), 0.85)
    result["reasons"] = [
        "A brand name sits in a label its owner does not control, on a path that asks for a password "
        "or a code. An address built that way is a phishing address, not a borderline one."
    ] + list(result.get("reasons") or [])[:3]
    return result


def _apply_hosting_policy(result: dict) -> dict:
    """A login page on a platform where anyone can publish is at least worth a look.

    It is not automatically phishing, because plenty of legitimate small sites live there, but it
    should never be cleared: the address cannot say whose page it is, and that is the whole problem.
    """
    host = (result.get("host") or "").lower()
    if _registrable(host) not in _USER_CONTENT:
        return result
    if result.get("verdict") != "legitimate":
        return result
    if not _CREDENTIAL_PATH.search(result.get("url", "")):
        return result
    result["verdict"] = "suspicious"
    result["risk"] = "medium"
    result["band"] = "Suspicious"
    result["label"] = 0
    result["probability"] = max(float(result.get("probability") or 0), 0.4)
    result["reasons"] = [
        "The address sits on a platform where anyone can publish, and its path asks for a password "
        "or a code. That does not prove who is behind it, which is why it is not cleared."
    ] + list(result.get("reasons") or [])[:3]
    return result


def _apply_feed(result: dict) -> dict:
    """Add evidence from the local snapshot of public phishing lists.

    The model judges the shape of a name, which is why a clean-looking address can still be a
    known campaign. A feed hit is the one piece of evidence that does not come from the name, so it
    is allowed to escalate the verdict; it is never allowed to clear one.
    """
    # An official domain is not to be condemned by either half of the system. The list carries brand
    # domains, so a stale entry must not escalate them; and the model judges shape, so it will happily
    # flag "kcb.co.ke" for being short. The institution's own published address is the one case where
    # we have direct knowledge, and it should win.
    official = _official_name(result.get("host", ""))
    if official:
        result["official"] = _legitimacy(official)
        if result.get("verdict") != "legitimate":
            result["verdict"] = "legitimate"
            result["risk"] = "low"
            result["band"] = "Likely legitimate"
            result["label"] = 0
            result["probability"] = min(float(result.get("probability") or 0), 0.2)
            result["reputation"] = result.get("reputation") or "established"
            result["reasons"] = [f"This is the address {official} publishes."] + list(result.get("reasons") or [])[:3]
        return result
    known = _known_site(result.get("host", ""))
    if known:
        result["established"] = known
        features = result.get("features") or {}
        # The same reasoning as an official domain, one step weaker: a site this widely used is not
        # cleared on the shape of its name. A brand in a label its owner does not control still wins.
        if result.get("verdict") != "legitimate" and not features.get("brand_in_wrong_place"):
            result["verdict"] = "legitimate"
            result["risk"] = "low"
            result["band"] = "Likely legitimate"
            result["label"] = 0
            result["probability"] = min(float(result.get("probability") or 0), 0.15)
            result["reputation"] = result.get("reputation") or "established"
            result["reasons"] = [
                f"Among the {known['rank']} most visited sites worldwide. Name-level evidence is not "
                "enough to flag it."
            ] + list(result.get("reasons") or [])[:2]

    feed = threat.lookup(result.get("url", ""))
    if not feed:
        return result
    result["feed"] = feed
    result["feed_listed"] = True
    if result.get("verdict") != "phishing":
        result["verdict"] = "phishing"
        result["risk"] = "high"
        result["band"] = "Listed in a phishing feed"
        result["label"] = 1
        reason = ("This address appears on a public phishing list"
                  + (f" (imitating {feed['target']})" if feed.get("target") else "")
                  + f", snapshot {feed['generated']}. A list can go stale, but a report is a reason to stop.")
        result["reasons"] = [reason] + list(result.get("reasons") or [])[:3]
    return result


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {"status": "ok" if state.get("storage_ready", True) else "degraded",
            "db": db.backend(), "model_loaded": "predictor" in state,
            "storage_ready": bool(state.get("storage_ready", True))}


@app.get("/api/model")
def model_info():
    return state["predictor"].info()



# Only web addresses are meaningful here. Anything with another scheme is rejected
# rather than scored: "javascript:alert(1)" has no host name, and prepending http://
# to it would invent one ("javascript") and return a confident verdict about it.
_NON_WEB_SCHEMES = {"javascript", "data", "file", "vbscript", "about", "blob",
                    "mailto", "tel", "ftp", "ftps", "ws", "wss", "chrome",
                    "view-source", "jar", "ms-msdt"}
_SCHEME_RE = re.compile(r"^\s*([a-zA-Z][a-zA-Z0-9+.\-]*):(//)?")


def _reject_non_web(url: str) -> None:
    m = _SCHEME_RE.match(url or "")
    if not m:
        return
    scheme = m.group(1).lower()
    if scheme in ("http", "https"):
        return
    if m.group(2) or scheme in _NON_WEB_SCHEMES:
        raise HTTPException(
            status_code=422,
            detail="Only http and https addresses can be checked.",
        )

@app.post("/api/predict")
def predict(payload: UrlIn, request: Request):
    _reject_non_web(payload.url)
    user = current_user(request)
    return _scan_and_store(payload.url.strip(), user["id"] if user else None)


@app.post("/api/scan/bulk")
async def scan_bulk(request: Request, file: UploadFile = File(...)):
    """Accept a CSV with a 'url' column (or one URL per line)."""
    user = current_user(request)
    # utf-8-sig: a CSV exported by Excel or written by PowerShell starts with a BOM, and with a BOM
    # on the first header cell the "url" column was not recognised. The file then fell through to
    # line parsing and the header row itself was scored as an address.
    raw = (await file.read()).decode("utf-8-sig", "ignore")
    urls = []
    try:
        reader = csv.DictReader(io.StringIO(raw))
        if reader.fieldnames and "url" in [f.lower() for f in reader.fieldnames]:
            key = next(f for f in reader.fieldnames if f.lower() == "url")
            urls = [row[key].strip() for row in reader if row.get(key)]
        else:
            raise ValueError
    except Exception:
        urls = [ln.strip() for ln in raw.splitlines()
                if ln.strip() and ln.strip().lower().lstrip("\ufeff") not in ("url", "urls")]

    urls = urls[:200]
    if not urls:
        raise HTTPException(status_code=422, detail="No URLs found in the uploaded file.")

    out = []
    for u in urls:
        try:
            r = state["predictor"].predict(u)
            # A batch must reach the same verdict as a single scan. It did not: this loop called the
            # model directly, so neither the credential policy nor the feed snapshot applied, and the
            # same address could be phishing on one page and suspicious in a CSV.
            r = _apply_credential_policy(r)
            r = _apply_hosting_policy(r)
            r = _apply_feed(r)
            db.add_scan(user["id"] if user else None, u, r["host"], r["verdict"],
                        r["risk"], r["probability"], r["inference_ms"])
            out.append({k: r.get(k) for k in ("url", "host", "verdict", "risk",
                                              "probability", "confidence")}
                       | {"official": (r.get("official") or {}).get("name"),
                          "reported": bool(r.get("feed_listed"))})
        except Exception:
            out.append({"url": u, "host": "", "verdict": "error", "risk": "unknown",
                        "probability": None, "confidence": None})
    flagged = sum(1 for r in out if r["verdict"] == "phishing")
    return {"count": len(out), "flagged": flagged, "results": out}


def _safe_history(limit: int, user_id):
    try:
        return db.recent_scans(limit, user_id)
    except Exception as exc:                          # noqa: BLE001
        log.warning("history unavailable: %s", exc)
        return None


@app.get("/api/history")
def history(request: Request, limit: int = 20):
    """Only the signed-in user's own scans.

    Scans are kept per account. An anonymous visitor has no account, so there is
    nothing that could correctly be returned - and nothing is.
    """
    user = current_user(request)
    if not user:
        return {"items": [], "note": "Sign in to keep a private scan history."}
    limit = max(1, min(limit, 100))
    items = _safe_history(limit, user["id"])
    if items is None:
        return {"items": [], "note": "History is unavailable for a moment. Try again shortly."}
    return {"items": items}


@app.get("/api/stats")
def get_stats():
    try:
        return db.stats()
    except Exception as exc:                          # noqa: BLE001
        log.warning("stats unavailable: %s", exc)
        return {"total_scans": 0, "phishing": 0, "legitimate": 0, "users": 0,
                "note": "Statistics are unavailable for a moment."}


@app.get("/api/stats/daily")
def get_daily_stats(days: int = 14):
    """Scan volume per day, for the sparkline. This service's own traffic only."""
    days = max(2, min(days, 60))
    try:
        return {"days": db.daily_scans(days)}
    except Exception as exc:                          # noqa: BLE001
        log.warning("daily stats unavailable: %s", exc)
        return {"days": [], "note": "Statistics are unavailable for a moment."}


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@app.get("/api/auth/me")
def me(request: Request):
    user = current_user(request)
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "email": user["email"], "full_name": user["full_name"]}


@app.post("/api/auth/register")
def register(payload: Credentials, response: Response):
    if "@" not in payload.email or "." not in payload.email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if db.get_user_by_email(payload.email):
        raise HTTPException(status_code=409, detail="That email is already registered.")
    uid = db.create_user(payload.email, payload.full_name or payload.email.split("@")[0],
                         payload.password)
    token = db.create_session(uid)
    response.set_cookie("pg_session", token, httponly=True, samesite="lax",
                        secure=cookie_secure(), max_age=604800)
    return {"authenticated": True, "email": payload.email.lower().strip(),
            "full_name": payload.full_name}


@app.post("/api/auth/login")
def login(payload: Credentials, response: Response):
    user = db.get_user_by_email(payload.email)
    if not user or not db.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    token = db.create_session(user["id"])
    response.set_cookie("pg_session", token, httponly=True, samesite="lax",
                        secure=cookie_secure(), max_age=604800)
    return {"authenticated": True, "email": user["email"], "full_name": user["full_name"]}


# --------------------------------------------------------------------------- #
# Sign in with Google, or with a phone number
#
# Both are optional and driven by the environment. The methods endpoint tells the
# browser which ones are actually configured, so the page never offers a button that
# cannot work. Phone codes go through Africa's Talking or Twilio when credentials are
# present; without them the code is written to the log and the response says so, which
# is what makes the flow testable locally.
# --------------------------------------------------------------------------- #
class PhoneIn(BaseModel):
    phone: str = Field(..., min_length=7, max_length=24)


class PhoneVerifyIn(BaseModel):
    phone: str = Field(..., min_length=7, max_length=24)
    code: str = Field(..., min_length=4, max_length=8)


def _id_token_claims(id_token: str) -> dict:
    """Read the claims out of an id_token.

    The token arrived over TLS from Google's token endpoint in the same response as the
    access token, which is the one case where reading a JWT without re-verifying its
    signature is sound: the channel already established that Google produced it, and the
    alternative was a second network call that kept failing.
    """
    try:
        payload = id_token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:  # noqa: BLE001
        return {}


def _oauth_redirect(request: Request) -> str:
    base = os.getenv("OAUTH_REDIRECT_BASE") or str(request.base_url).rstrip("/")
    return f"{base}/api/auth/google/callback"


def _sms_configured() -> bool:
    return bool(os.getenv("AT_API_KEY") and os.getenv("AT_USERNAME")) or \
           bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"))


def normalise_phone(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
    if not digits.startswith("+"):
        digits = "+" + digits.lstrip("+")
    if digits.startswith("+0"):
        digits = "+254" + digits[2:]
    elif len(digits) == 10 and digits.startswith("+7"):
        digits = "+254" + digits[2:]
    return digits


def send_otp(phone: str, code: str) -> str:
    """Return 'sms' when sent, 'log' when there is no provider."""
    body = f"Nyavu verification code: {code}. It expires in five minutes."
    if os.getenv("AT_API_KEY") and os.getenv("AT_USERNAME"):
        data = urllib.parse.urlencode({
            "username": os.getenv("AT_USERNAME"),
            "to": phone,
            "message": body,
            "from": os.getenv("AT_SENDER_ID", ""),
        }).encode()
        req = urllib.request.Request("https://api.africastalking.com/version1/messaging", data=data,
                                     headers={"apiKey": os.getenv("AT_API_KEY"),
                                              "Content-Type": "application/x-www-form-urlencoded"})
        try:
            urllib.request.urlopen(req, timeout=15).read()
            return "sms"
        except Exception as exc:
            print("SMS send failed:", exc)
            return "log"
    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        data = urllib.parse.urlencode({"To": phone, "From": os.getenv("TWILIO_FROM", ""),
                                       "Body": body}).encode()
        token = base64.b64encode(f"{sid}:{os.getenv('TWILIO_AUTH_TOKEN')}".encode()).decode()
        req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                                     data=data, headers={"Authorization": f"Basic {token}"})
        try:
            urllib.request.urlopen(req, timeout=15).read()
            return "sms"
        except Exception as exc:
            print("SMS send failed:", exc)
            return "log"
    print(f"[dev] OTP for {phone}: {code}")
    return "log"


@app.get("/api/auth/methods")
def auth_methods():
    """What the sign-in panel may offer.

    Google is the only method in service. Email and password, and the phone code, still
    exist in the code and still work if called directly, but nothing advertises them until
    the Google round trip has been proven on a real device. AUTH_GOOGLE_ONLY=0 brings them
    back without a code change.
    """
    google_only = os.getenv("AUTH_GOOGLE_ONLY", "1") != "0"
    return {
        "password": not google_only,
        "google": bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")),
        # The phone button is only offered when a code can actually reach the person.
        # Offering it with no SMS provider is a dead end: the code would go to the server
        # log, which the visitor cannot read. ALLOW_LOG_OTP keeps the flow testable.
        "phone": (not google_only) and (_sms_configured() or os.getenv("ALLOW_LOG_OTP") == "1"),
        "sms": _sms_configured(),
    }


@app.get("/api/auth/google/start")
def google_start(request: Request):
    cid = os.getenv("GOOGLE_CLIENT_ID")
    if not (cid and os.getenv("GOOGLE_CLIENT_SECRET")):
        raise HTTPException(status_code=400, detail="Google sign-in is not configured.")
    state = secrets.token_urlsafe(24)

    # PKCE. A web client does not need it, an installed client requires it, and Google's
    # answer to a missing verifier is exactly the invalid_grant this flow kept receiving.
    # Sending it is correct for every client type, so it is unconditional.
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")

    params = urllib.parse.urlencode({
        "client_id": cid,
        "redirect_uri": _oauth_redirect(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")
    response.set_cookie("pg_oauth_state", state, httponly=True, samesite="lax",
                        secure=cookie_secure(), max_age=600)
    response.set_cookie("pg_oauth_verifier", verifier, httponly=True, samesite="lax",
                        secure=cookie_secure(), max_age=600)
    return response


@app.get("/api/auth/google/diagnose")
def google_diagnose(request: Request, token: str = ""):
    """Say, without exposing a secret, why the Google round trip is failing.

    Guarded by the DIAG_TOKEN environment variable. It reports the shape of the configured
    credentials rather than the credentials, and asks Google to reject a fake code, which
    separates "our client is wrong" (invalid_client) from "our client is fine and the code
    was the problem" (invalid_grant).
    """
    expected = os.getenv("DIAG_TOKEN")
    if not expected or token != expected:
        raise HTTPException(status_code=404, detail="Not found.")

    cid = os.getenv("GOOGLE_CLIENT_ID") or ""
    secret = os.getenv("GOOGLE_CLIENT_SECRET") or ""
    redirect = _oauth_redirect(request)

    payload = urllib.parse.urlencode({
        "code": "diagnostic-not-a-real-code",
        "client_id": cid,
        "client_secret": secret,
        "redirect_uri": redirect,
        "grant_type": "authorization_code",
    }).encode()

    google = {"status": None, "error": None, "description": None}
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=payload, timeout=20) as r:
            google["status"] = r.status
    except urllib.error.HTTPError as exc:
        google["status"] = exc.code
        try:
            body = json.loads(exc.read())
            google["error"] = body.get("error")
            google["description"] = body.get("error_description")
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        google["error"] = type(exc).__name__
        google["description"] = str(exc)[:200]

    return {
        "redirect_uri": redirect,
        "client_id": {
            "length": len(cid),
            "prefix": cid[:14],
            "suffix": cid[-20:],
            "has_whitespace": cid != cid.strip(),
            "looks_like_google": cid.endswith(".apps.googleusercontent.com"),
        },
        "client_secret": {
            "length": len(secret),
            "has_whitespace": secret != secret.strip(),
            "prefix": secret[:6],
            "ends_like_google": secret.endswith(".apps.googleusercontent.com") or secret.startswith("GOCSPX-"),
        },
        "google_answer": google,
    }


@app.get("/api/auth/google/callback")
def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return RedirectResponse("/?auth=cancelled")
    if not state or state != request.cookies.get("pg_oauth_state"):
        return RedirectResponse("/?auth=state")
    cid, secret = os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")
    if not (cid and secret):
        return RedirectResponse("/?auth=unconfigured")
    fields = {
        "code": code,
        "client_id": cid,
        "client_secret": secret,
        "redirect_uri": _oauth_redirect(request),
        "grant_type": "authorization_code",
    }
    verifier = request.cookies.get("pg_oauth_verifier")
    if verifier:
        fields["code_verifier"] = verifier
    data = urllib.parse.urlencode(fields).encode()
    # One request, not two.

    # The token endpoint already returns an id_token containing the address, so the separate
    # userinfo call was an extra failure point for data we had in hand. It was also the call
    # that kept raising TypeError on the deployed instance, for reasons that never reached a
    # log we could read. Decoding the id_token removes the request and the class of failure.
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/token",
                                    data=data, timeout=20) as r:
            tokens = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        why = ""
        try:
            payload = json.loads(exc.read())
            why = str(payload.get("error_description") or payload.get("error") or "")
        except Exception:
            pass
        print(f"Google sign-in failed at token: {exc.code} {why}")
        query = urllib.parse.urlencode({"auth": "failed", "stage": "token", "why": why[:120]})
        return RedirectResponse(f"/?{query}")
    except Exception as exc:  # noqa: BLE001
        print(f"Google sign-in failed at token: {type(exc).__name__} {exc}")
        query = urllib.parse.urlencode({"auth": "failed", "stage": "token",
                                        "why": type(exc).__name__})
        return RedirectResponse(f"/?{query}")

    info = _id_token_claims(tokens.get("id_token", ""))
    if not info.get("email") and tokens.get("access_token"):
        # older clients may not return an id_token; ask once, and fail gently if refused
        try:
            with urllib.request.urlopen("https://openidconnect.googleapis.com/v1/userinfo",
                                        headers={"Authorization": f"Bearer {tokens['access_token']}"},
                                        timeout=20) as r:
                info = json.loads(r.read())
        except Exception as exc:  # noqa: BLE001
            print(f"Google sign-in failed at userinfo: {type(exc).__name__} {exc}")
            query = urllib.parse.urlencode({"auth": "failed", "stage": "userinfo",
                                            "why": type(exc).__name__})
            return RedirectResponse(f"/?{query}")

    email = (info.get("email") or "").lower()
    if not email:
        return RedirectResponse("/?auth=noemail")
    user = db.get_user_by_email(email)
    if not user:
        uid = db.create_social_user(email, info.get("name", ""), info.get("sub", ""))
        user = db.get_user_by_email(email)
    elif info.get("sub") and not user.get("google_sub"):
        db.link_google_sub(user["id"], info["sub"])

    token = db.create_session(user["id"])
    response = RedirectResponse("/?auth=ok")
    response.set_cookie("pg_session", token, httponly=True, samesite="lax",
                        secure=cookie_secure(), max_age=604800)
    return response


@app.post("/api/auth/phone/start")
def phone_start(payload: PhoneIn):
    phone = normalise_phone(payload.phone)
    if len(phone) < 9:
        raise HTTPException(status_code=422, detail="That does not look like a phone number.")
    code = f"{secrets.randbelow(1000000):06d}"
    db.save_otp(phone, code)
    channel = send_otp(phone, code)
    return {"sent": True, "channel": channel}


@app.post("/api/auth/phone/verify")
def phone_verify(payload: PhoneVerifyIn, response: Response):
    phone = normalise_phone(payload.phone)
    if not db.check_otp(phone, payload.code.strip()):
        raise HTTPException(status_code=401, detail="That code is wrong or has expired.")
    user = db.get_user_by_phone(phone)
    if not user:
        db.create_phone_user(phone)
        user = db.get_user_by_phone(phone)
    token = db.create_session(user["id"])
    response.set_cookie("pg_session", token, httponly=True, samesite="lax",
                        secure=cookie_secure(), max_age=604800)
    return {"authenticated": True, "phone": phone, "full_name": user["full_name"]}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    db.destroy_session(request.cookies.get("pg_session", ""))
    response.delete_cookie("pg_session")
    return {"authenticated": False}



# --------------------------------------------------------------------------- #
# Simulated phishing page, served locally so the extension can be demonstrated
# without visiting a real malicious site. Clearly labelled as a test artefact.
# --------------------------------------------------------------------------- #
DEMO_PHISH = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mobile Money Login</title>
<style>
 body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0f1a2b;
      font:16px/1.5 -apple-system,"Segoe UI",Roboto,sans-serif;color:#e8eefb}
 .card{width:min(360px,92vw);background:#16233d;border:1px solid #22304d;border-radius:16px;padding:28px}
 h1{font-size:20px;margin:0 0 6px;letter-spacing:-.02em}
 p{color:#93a6c4;font-size:14px;margin:0 0 18px}
 input{width:100%;padding:12px;margin-bottom:12px;border-radius:10px;border:1px solid #2c3d5e;
       background:#0e1628;color:#e8eefb;font:15px inherit}
 button{width:100%;padding:12px;border:0;border-radius:10px;font-weight:700;cursor:pointer;
        background:linear-gradient(180deg,#4cc2f7,#2a9fdc);color:#04121f}
 .warn{position:fixed;bottom:0;left:0;right:0;background:#3b0d12;color:#ffb4b8;
       padding:10px 16px;font-size:12px;text-align:center;border-top:1px solid #f2545b}
</style></head><body>
<div class="card">
  <h1>Mobile Money Login</h1>
  <p>Enter your phone number to continue to your account.</p>
  <input placeholder="07XX XXX XXX">
  <input placeholder="PIN" type="password">
  <button>Continue</button>
</div>
<div class="warn">SIMULATED PHISHING PAGE, a test artefact for the Nyavu demonstration.
This form does nothing and sends nothing.</div>
</body></html>"""


@app.get("/demo/phish", response_class=HTMLResponse)
def demo_phish():
    """Local stand-in for a phishing page; used to test Shusha Nyavu safely."""
    return DEMO_PHISH



def _latest_apk() -> str | None:
    """The newest app build in dist, or None.

    The download used to redirect to a published release, and the release could drift: the
    link was serving 0.8.0 while the repository held 0.9.1. Serving the newest build from the
    repository means the link cannot disagree with the artefact beside it.
    """
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")
    if not os.path.isdir(folder):
        return None

    # Pick by version number, not by modification time: a checkout rewrites mtimes, and a
    # loose prefix match once served a year-old "Nyavu-Shusha" build from the same folder.
    pattern = re.compile(r"^Nyavu-(\d+)\.(\d+)\.(\d+)-debug\.apk$")
    builds = []
    for name in os.listdir(folder):
        match = pattern.match(name)
        if match:
            builds.append((tuple(int(x) for x in match.groups()), os.path.join(folder, name)))
    if not builds:
        return None
    return max(builds, key=lambda pair: pair[0])[1]


@app.get("/download/nyavu.apk")
def download_apk():
    path = _latest_apk()
    if not path:
        raise HTTPException(status_code=404, detail="No build available.")
    version = os.path.basename(path).replace("Nyavu-", "").replace("-debug.apk", "")
    return FileResponse(
        path,
        media_type="application/vnd.android.package-archive",
        filename=f"Nyavu-{version}.apk",
        headers={"X-Nyavu-Version": version},
    )


@app.get("/api/app/version")
def app_version() -> dict:
    path = _latest_apk()
    if not path:
        return {"version": None, "bytes": 0}
    name = os.path.basename(path)
    return {
        "version": name.replace("Nyavu-", "").replace("-debug.apk", ""),
        "bytes": os.path.getsize(path),
        "file": name,
    }


# --------------------------------------------------------------------------- #
# Static front end
# --------------------------------------------------------------------------- #

@app.get("/about")
def about():
    return FileResponse(os.path.join(STATIC, "pages", "about.html"))


@app.get("/learn/{slug}")
def learn(slug: str):
    if not slug.replace("-", "").isalnum():
        raise HTTPException(status_code=404)
    path = os.path.join(STATIC, "pages", "learn", f"{slug}.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    return FileResponse(path)


# --------------------------------------------------------------------------- #
# Search engines
#
# robots.txt and sitemap.xml are generated rather than stored, so they always agree with
# the routes that exist and always name the host the visitor actually used. The hash
# routes (#model, #history) are deliberately absent: a fragment cannot be indexed as a
# page, and listing it would only produce duplicates of the home page.
# --------------------------------------------------------------------------- #
PUBLIC_PAGES = ["/", "/learn/is-this-link-safe", "/learn/how-phishing-works", "/about"]


def _origin(request: Request) -> str:
    base = os.getenv("PUBLIC_ORIGIN")
    if base:
        return base.rstrip("/")
    return str(request.base_url).rstrip("/")


# --------------------------------------------------------------------------- #
# Suggestions while typing
#
# Two sources: hosts this deployment has actually seen, and a small seed of domains
# people here type often. A host that was ever scored as phishing is never suggested:
# offering one as a convenience would be a delivery mechanism, not a feature.
# --------------------------------------------------------------------------- #
SEED_DOMAINS = [
    "safaricom.co.ke", "www.safaricom.co.ke", "mpesa.co.ke", "kra.go.ke",
    "www.kra.go.ke", "kabarak.ac.ke", "students.kabarak.ac.ke", "equitybank.co.ke",
    "kcbgroup.com", "ecitizen.go.ke", "helb.co.ke", "nhif.or.ke", "google.com",
    "accounts.google.com", "facebook.com", "whatsapp.com", "netflix.com", "paypal.com",
]


@app.get("/api/suggest")
def suggest(request: Request, q: str = "", limit: int = 6):
    term = (q or "").strip().lower()
    term = term.replace("https://", "").replace("http://", "").split("/")[0]
    if len(term) < 2:
        return {"query": q, "suggestions": []}

    seen: list[str] = []
    try:
        for row in db.recent_scans(60):
            record = dict(row)
            if (record.get("verdict") or "").lower() == "phishing":
                continue
            host = (record.get("host") or "").strip().lower()
            if host and host not in seen:
                seen.append(host)
    except Exception:
        pass

    pool = seen + [d for d in SEED_DOMAINS if d not in seen]
    matches = [d for d in pool if term in d or d.startswith(term)][:limit]
    return {"query": q, "suggestions": matches}


@app.exception_handler(StarletteHTTPException)
async def not_found(request: Request, exc: StarletteHTTPException):
    """A wrong address gets a page, not a JSON body, when a browser asked for one."""
    wants_html = "text/html" in request.headers.get("accept", "")
    if exc.status_code == 404 and wants_html:
        page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Nothing at this address | Nyavu</title>
        <link rel="stylesheet" href="/styles.css"></head>
        <body><main style="max-width:640px;margin:18vh auto 0;padding:0 24px">
        <p style="font-family:Georgia,serif;font-style:italic;color:#8D97AB;margin:0 0 14px">404</p>
        <h1 style="font-family:Georgia,serif;font-weight:400;font-size:2.2rem;line-height:1.1;margin:0 0 16px;color:#E4E8EE">
        There is nothing at this address</h1>
        <p style="color:#9BA5B2;line-height:1.6;margin:0 0 24px">
        The page you asked for does not exist. If you followed a link from somewhere,
        that link is wrong, which is worth knowing in itself.</p>
        <p><a href="/" style="color:#8FA98F">Check a link instead</a></p>
        </main></body></html>"""
        return HTMLResponse(page, status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/robots.txt", include_in_schema=False)
def robots(request: Request):
    origin = _origin(request)
    body = f"""User-agent: *
Allow: /
Disallow: /api/

Sitemap: {origin}/sitemap.xml
"""
    return Response(content=body, media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request):
    origin = _origin(request)
    today = datetime.now(timezone.utc).date().isoformat()
    urls = "".join(
        f"  <url><loc>{origin}{path}</loc><lastmod>{today}</lastmod>"
        f"<changefreq>{'weekly' if path == '/' else 'monthly'}</changefreq>"
        f"<priority>{'1.0' if path == '/' else '0.7'}</priority></url>\n"
        for path in PUBLIC_PAGES
    )
    body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}</urlset>\n")
    return Response(content=body, media_type="application/xml")


@app.get("/{key_name}.txt", include_in_schema=False)
def indexnow_key(key_name: str):
    """Bing verifies an IndexNow key by fetching it from the root of the site."""
    expected = os.getenv("INDEXNOW_KEY", "")
    if expected and key_name == expected:
        return Response(content=expected, media_type="text/plain")
    raise HTTPException(status_code=404, detail="Not found")


_ASSET_FILES = ("styles.css", "guards.css", "app.js", "autopsy.js", "institutions.js", "sw.js")


def _asset_version() -> str:
    """A stamp that changes only when one of the shell files changes.

    Assets were referenced by fixed URLs, so a slow or failed fetch could leave the CSS from
    one deploy next to the JavaScript from another. That mixture is what produced a blurred
    page with no verdict card: the new script opened an overlay whose styles the old
    stylesheet did not contain. A version in the URL makes the two impossible to mix.
    """
    digest = hashlib.sha256()
    for name in _ASSET_FILES:
        try:
            with open(os.path.join(STATIC, name), "rb") as fh:
                digest.update(fh.read())
        except OSError:
            digest.update(name.encode())
    # The server's own code belongs in the stamp too. It did not, so a Python-only fix shipped and
    # the version endpoint kept reporting the previous build: the marker lied about the deploy.
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("main.py", "predictor.py", "threat.py", "db.py"):
        try:
            with open(os.path.join(here, name), "rb") as fh:
                digest.update(fh.read())
        except OSError:
            digest.update(name.encode())
    # Data counts as part of the build. A refreshed feed snapshot ships without touching a line of
    # code, so a code-only stamp reported the previous build and made a completed deploy look stuck.
    digest.update(_data_digest().encode())
    return digest.hexdigest()[:10]


_DATA_DIGEST = ""


def _data_digest() -> str:
    """A short hash over the shipped data files, computed once per process."""
    global _DATA_DIGEST
    if _DATA_DIGEST:
        return _DATA_DIGEST
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inner = hashlib.sha256()
    for name in ("threat_snapshot.json.gz", "institutions.json", "known_sites.json", "legitimacy.json"):
        try:
            with open(os.path.join(root, "data", name), "rb") as fh:
                while True:
                    chunk = fh.read(1 << 20)
                    if not chunk:
                        break
                    inner.update(chunk)
        except OSError:
            inner.update(name.encode())
    _DATA_DIGEST = inner.hexdigest()[:10]
    return _DATA_DIGEST


_INDEX_CACHE: dict[str, str] = {}


@app.get("/api/version")
def version() -> dict:
    """The build the server is serving, so a stale page can notice it is stale."""
    return {"build": _asset_version()}


@app.get("/")
def index(request: Request):
    """Serve the shell with the search-console tokens spliced in.

    The tokens come from the environment so they are never committed, and the page is
    cached per origin rather than read from disk on every request.
    """
    origin = _origin(request)
    if origin not in _INDEX_CACHE:
        with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as fh:
            html = fh.read()
        tags = []
        google = os.getenv("GOOGLE_SITE_VERIFICATION")
        bing = os.getenv("BING_SITE_VERIFICATION")
        if google:
            tags.append(f'<meta name="google-site-verification" content="{google}" />')
        if bing:
            tags.append(f'<meta name="msvalidate.01" content="{bing}" />')
        html = html.replace("<!--verification-->", "\n".join(tags).strip())
        html = html.replace("https://nyavu.onrender.com/", origin + "/")
        version = _asset_version()
        for name in ("styles.css", "guards.css", "app.js", "autopsy.js", "institutions.js"):
            html = html.replace(f'"/{name}"', f'"/{name}?v={version}"')
        html = html.replace("<!--build-->", f'<meta name="nyavu-build" content="{version}" />')
        _INDEX_CACHE[origin] = html
    return HTMLResponse(_INDEX_CACHE[origin])


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
