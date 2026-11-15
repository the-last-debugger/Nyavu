"""Nyavu API - FastAPI application entry point."""
from __future__ import annotations

import csv
import io
import os
import time

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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
    return {"status": "ok", "model_loaded": "predictor" in state}


@app.get("/api/model")
def model_info():
    return state["predictor"].info()


@app.post("/api/predict")
def predict(payload: UrlIn, request: Request):
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
<div class="warn">SIMULATED PHISHING PAGE — a test artefact for the Nyavu demonstration.
This form does nothing and sends nothing.</div>
</body></html>"""


@app.get("/demo/phish", response_class=HTMLResponse)
def demo_phish():
    """Local stand-in for a phishing page; used to test Shusha Nyavu safely."""
    return DEMO_PHISH



@app.get("/download/nyavu.apk")
def download_apk():
    """Serves the built Android agent so a phone can install it over the tailnet."""
    path = os.path.normpath(os.path.join(BASE, "..", "dist", "Nyavu-Shusha-0.2.0-debug.apk"))
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="APK has not been built yet.")
    return FileResponse(path, media_type="application/vnd.android.package-archive",
                        filename="Nyavu-Shusha.apk")


# --------------------------------------------------------------------------- #
# Static front end
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
