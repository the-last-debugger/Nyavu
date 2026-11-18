"""Persistence layer. Postgres when DATABASE_URL is set, SQLite otherwise.

One SQL dialect is written: statements use ``?`` placeholders and the adapter
translates them for Postgres. The schema is generated per backend because the two
disagree about auto-increment columns.

Why both: SQLite keeps local development and the test suite trivial (no server to
run), while Postgres gives the hosted deployment storage that survives a redeploy.
Nothing above this module knows which is in use.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("NYAVU_DB_PATH") or os.path.join(ROOT, "data", "nyavu.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))

_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    full_name     TEXT,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    created_at TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS scans (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER,
    url          TEXT    NOT NULL,
    host         TEXT    NOT NULL,
    verdict      TEXT    NOT NULL,
    risk         TEXT    NOT NULL,
    probability  REAL    NOT NULL,
    inference_ms REAL,
    created_at   TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS models (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    version    TEXT    NOT NULL,
    accuracy   REAL,
    f1         REAL,
    trained_at TEXT    NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_user    ON scans(user_id);
"""

_SCHEMA_PG = (_SCHEMA_SQLITE
              .replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
              .replace(" REAL", " DOUBLE PRECISION"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class _Connection:
    """The two drivers disagree about placeholders and cursors; this hides that."""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql: str, params=()):
        if USE_PG:
            sql = sql.replace("?", "%s")
        return self._raw.execute(sql, params) if params else self._raw.execute(sql)

    def executescript(self, script: str):
        statements = [s.strip() for s in script.split(";") if s.strip()]
        for stmt in statements:
            self._raw.execute(stmt)


_POOL = None


def _pool():
    """One process-wide pool.

    The service opens a connection per request, which SQLite tolerates and Postgres
    does not: a fresh TLS handshake each time costs ~50 ms and exhausts the server's
    connection allowance under any concurrency at all. The pool is created lazily so
    importing this module does not open a socket.
    """
    global _POOL
    if _POOL is None:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        _POOL = ConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=5,
            timeout=10,
            kwargs={"row_factory": dict_row, "connect_timeout": 10},
            open=True,
        )
    return _POOL


@contextmanager
def connect():
    if USE_PG:
        with _pool().connection() as conn:
            try:
                yield _Connection(conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return

    import sqlite3

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield _Connection(conn)
        conn.commit()
    finally:
        conn.close()


def _insert_id(c: _Connection, sql: str, params) -> int:
    """Return the id of the row just inserted, on either backend."""
    if USE_PG:
        row = c.execute(sql + " RETURNING id", params).fetchone()
        return int(row["id"])
    return int(c.execute(sql, params).lastrowid)


def init_db() -> None:
    if not USE_PG:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with connect() as c:
        c.executescript(_SCHEMA_PG if USE_PG else _SCHEMA_SQLITE)


def backend() -> str:
    return "postgres" if USE_PG else "sqlite"


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return secrets.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Users & sessions
# --------------------------------------------------------------------------- #
def create_user(email: str, full_name: str, password: str):
    with connect() as c:
        return _insert_id(
            c,
            "INSERT INTO users (email, full_name, password_hash, created_at) VALUES (?,?,?,?)",
            (email.lower().strip(), full_name.strip(), hash_password(password), now()),
        )


def get_user_by_email(email: str):
    with connect() as c:
        return c.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with connect() as c:
        c.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?,?,?)",
                  (token, user_id, now()))
    return token


def user_for_token(token: str):
    if not token:
        return None
    with connect() as c:
        return c.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()


def destroy_session(token: str) -> None:
    with connect() as c:
        c.execute("DELETE FROM sessions WHERE token = ?", (token,))


# --------------------------------------------------------------------------- #
# Scans
# --------------------------------------------------------------------------- #
def add_scan(user_id, url: str, host: str, verdict: str, risk: str,
             probability: float, inference_ms: float) -> int:
    with connect() as c:
        return _insert_id(
            c,
            """INSERT INTO scans (user_id, url, host, verdict, risk, probability,
                                  inference_ms, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, url, host, verdict, risk, probability, inference_ms, now()),
        )


def recent_scans(limit: int = 20, user_id: int | None = None):
    """Scans belonging to one account.

    A missing user must never widen the query: anonymous scans are recorded with a
    NULL user_id and are deliberately not readable back, so no visitor can see the
    addresses another person submitted. Returning an empty list here is the safe
    default if a caller forgets the argument.
    """
    if not user_id:
        return []
    with connect() as c:
        rows = c.execute(
            "SELECT id, url, host, verdict, risk, probability, created_at "
            "FROM scans WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def daily_scans(days: int = 14):
    """Scan counts per calendar day, oldest first.

    substr() is used rather than a date-cast because the column is ISO text and the
    same expression works on both SQLite and Postgres.
    """
    with connect() as c:
        rows = c.execute(
            "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS n "
            "FROM scans GROUP BY day ORDER BY day DESC LIMIT ?", (days,)).fetchall()
    return [{"day": r["day"], "count": int(r["n"])} for r in reversed(rows)]


def stats():
    with connect() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM scans").fetchone()["n"]
        phish = c.execute("SELECT COUNT(*) AS n FROM scans WHERE verdict='phishing'").fetchone()["n"]
        users = c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        return {"total_scans": int(total), "phishing": int(phish),
                "legitimate": int(total) - int(phish), "users": int(users)}


def record_model(name: str, version: str, accuracy: float, f1: float) -> None:
    with connect() as c:
        c.execute("UPDATE models SET is_active = 0")
        c.execute(
            "INSERT INTO models (name, version, accuracy, f1, trained_at, is_active) "
            "VALUES (?,?,?,?,?,1)", (name, version, accuracy, f1, now()))

# --------------------------------------------------------------------------- #
# Alternative sign-in: OAuth identities and phone numbers
# --------------------------------------------------------------------------- #
def migrate_auth() -> None:
    """Add the columns that social and phone sign-in need.

    SQLite cannot add a NOT NULL column without a default, and neither backend can drop
    NOT NULL in place, so accounts created this way carry a random password hash that is
    never usable. The email stays the primary identity.
    """
    cols = [("phone", "TEXT"), ("google_sub", "TEXT")]
    with connect() as c:
        for name, kind in cols:
            try:
                if USE_PG:
                    c.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {name} {kind}")
                else:
                    c.execute(f"ALTER TABLE users ADD COLUMN {name} {kind}")
            except Exception:
                pass
        try:
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_phone_idx ON users (phone)")
        except Exception:
            pass
        try:
            c.execute("""CREATE TABLE IF NOT EXISTS phone_otps (
                           phone      TEXT PRIMARY KEY,
                           code_hash  TEXT NOT NULL,
                           expires_at TEXT NOT NULL,
                           attempts   INTEGER NOT NULL DEFAULT 0)""")
        except Exception:
            pass


def _random_hash() -> str:
    return hash_password(secrets.token_urlsafe(24))


def create_social_user(email: str, full_name: str, google_sub: str = ""):
    with connect() as c:
        return _insert_id(
            c,
            "INSERT INTO users (email, full_name, password_hash, created_at, google_sub) VALUES (?,?,?,?,?)",
            (email.lower().strip(), full_name.strip() or email.split("@")[0], _random_hash(), now(), google_sub or None),
        )


def link_google_sub(user_id: int, google_sub: str) -> None:
    with connect() as c:
        c.execute("UPDATE users SET google_sub = ? WHERE id = ?", (google_sub, user_id))


def create_phone_user(phone: str):
    """A phone account keyed on a synthetic address the user never sees."""
    email = f"{phone.lstrip('+').replace(' ', '')}@phone.nyavu.local"
    with connect() as c:
        return _insert_id(
            c,
            "INSERT INTO users (email, full_name, password_hash, created_at, phone) VALUES (?,?,?,?,?)",
            (email, phone, _random_hash(), now(), phone),
        )


def get_user_by_phone(phone: str):
    with connect() as c:
        return c.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()


def save_otp(phone: str, code: str, ttl_seconds: int = 300) -> None:
    expires = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat(timespec="seconds")
    with connect() as c:
        c.execute("DELETE FROM phone_otps WHERE phone = ?", (phone,))
        c.execute("INSERT INTO phone_otps (phone, code_hash, expires_at, attempts) VALUES (?,?,?,0)",
                  (phone, hash_password(code), expires))


def check_otp(phone: str, code: str):
    """Return True when the code matches and has not expired. Bounded attempts."""
    with connect() as c:
        row = c.execute("SELECT * FROM phone_otps WHERE phone = ?", (phone,)).fetchone()
        if not row:
            return False
        row = dict(row)
        if row["attempts"] >= 5:
            c.execute("DELETE FROM phone_otps WHERE phone = ?", (phone,))
            return False
        c.execute("UPDATE phone_otps SET attempts = attempts + 1 WHERE phone = ?", (phone,))
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            c.execute("DELETE FROM phone_otps WHERE phone = ?", (phone,))
            return False
        ok = verify_password(code, row["code_hash"])
        if ok:
            c.execute("DELETE FROM phone_otps WHERE phone = ?", (phone,))
        return ok
