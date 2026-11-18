"""Nyavu API - FastAPI application entry point."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import urllib.request
import urllib.parse
import secrets
import base64
import io
import os
import re
import time

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db
from .predictor import Predictor

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")

app = FastAPI(
    title="Nyavu API",
    version="1.0.0",
    description="Machine-learning phishing URL detection with explanations.",
)

state: dict = {}


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    db.migrate_auth()
    state["predictor"] = Predictor()
    m = state["predictor"].info()["metrics"]
    db.record_model(state["predictor"].info()["model"], "1.0.0",
                    m["accuracy"], m["f1"])



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
        return "predict", 30
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


def _scan_and_store(url: str, user_id):
    try:
        result = state["predictor"].predict(url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    db.add_scan(user_id, url, result["host"], result["verdict"], result["risk"],
                result["probability"], result["inference_ms"])
    return result


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {"status": "ok", "db": db.backend(), "model_loaded": "predictor" in state}


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
    raw = (await file.read()).decode("utf-8", "ignore")
    urls = []
    try:
        reader = csv.DictReader(io.StringIO(raw))
        if reader.fieldnames and "url" in [f.lower() for f in reader.fieldnames]:
            key = next(f for f in reader.fieldnames if f.lower() == "url")
            urls = [row[key].strip() for row in reader if row.get(key)]
        else:
            raise ValueError
    except Exception:
        urls = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    urls = urls[:200]
    if not urls:
        raise HTTPException(status_code=422, detail="No URLs found in the uploaded file.")

    out = []
    for u in urls:
        try:
            r = state["predictor"].predict(u)
            db.add_scan(user["id"] if user else None, u, r["host"], r["verdict"],
                        r["risk"], r["probability"], r["inference_ms"])
            out.append({k: r[k] for k in ("url", "host", "verdict", "risk",
                                          "probability", "confidence")})
        except Exception:
            out.append({"url": u, "host": "", "verdict": "error", "risk": "unknown",
                        "probability": None, "confidence": None})
    flagged = sum(1 for r in out if r["verdict"] == "phishing")
    return {"count": len(out), "flagged": flagged, "results": out}


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
    return {"items": db.recent_scans(limit, user["id"])}


@app.get("/api/stats")
def get_stats():
    return db.stats()


@app.get("/api/stats/daily")
def get_daily_stats(days: int = 14):
    """Scan volume per day, for the sparkline. This service's own traffic only."""
    days = max(2, min(days, 60))
    return {"days": db.daily_scans(days)}


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
    return {
        "password": True,
        "google": bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")),
        "phone": True,
        "sms": _sms_configured(),
    }


@app.get("/api/auth/google/start")
def google_start(request: Request):
    cid = os.getenv("GOOGLE_CLIENT_ID")
    if not (cid and os.getenv("GOOGLE_CLIENT_SECRET")):
        raise HTTPException(status_code=400, detail="Google sign-in is not configured.")
    state = secrets.token_urlsafe(24)
    params = urllib.parse.urlencode({
        "client_id": cid,
        "redirect_uri": _oauth_redirect(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")
    response.set_cookie("pg_oauth_state", state, httponly=True, samesite="lax",
                        secure=cookie_secure(), max_age=600)
    return response


@app.get("/api/auth/google/callback")
def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return RedirectResponse("/?auth=cancelled")
    if not state or state != request.cookies.get("pg_oauth_state"):
        return RedirectResponse("/?auth=state")
    cid, secret = os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")
    if not (cid and secret):
        return RedirectResponse("/?auth=unconfigured")
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": cid,
        "client_secret": secret,
        "redirect_uri": _oauth_redirect(request),
        "grant_type": "authorization_code",
    }).encode()
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=20) as r:
            tokens = json.loads(r.read())
        with urllib.request.urlopen("https://openidconnect.googleapis.com/v1/userinfo",
                                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                                    timeout=20) as r:
            info = json.loads(r.read())
    except Exception as exc:
        print("Google sign-in failed:", exc)
        return RedirectResponse("/?auth=failed")

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



@app.get("/download/nyavu.apk")
def download_apk():
    """Send the phone to the published release rather than a file inside the repo.

    The binary used to sit in dist/ and be served from disk, which meant every build
    changed the repository and the download could drift from the released version.
    """
    return RedirectResponse(
        "https://github.com/the-last-debugger/Nyavu/releases/latest/download/Nyavu.apk",
        status_code=307,
    )


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


_INDEX_CACHE: dict[str, str] = {}


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
        _INDEX_CACHE[origin] = html
    return HTMLResponse(_INDEX_CACHE[origin])


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
