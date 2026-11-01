"""SQLite persistence layer (stdlib only, no ORM)."""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "nyavu.db")

SCHEMA = """
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


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with connect() as c:
        c.executescript(SCHEMA)


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
        cur = c.execute(
            "INSERT INTO users (email, full_name, password_hash, created_at) VALUES (?,?,?,?)",
            (email.lower().strip(), full_name.strip(), hash_password(password), now()),
        )
        return cur.lastrowid


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
        cur = c.execute(
            """INSERT INTO scans (user_id, url, host, verdict, risk, probability,
                                  inference_ms, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, url, host, verdict, risk, probability, inference_ms, now()),
        )
        return cur.lastrowid


def recent_scans(limit: int = 20, user_id=None):
    with connect() as c:
        if user_id is None:
            rows = c.execute(
                "SELECT id, url, host, verdict, risk, probability, created_at "
                "FROM scans ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = c.execute(
                "SELECT id, url, host, verdict, risk, probability, created_at "
                "FROM scans WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)).fetchall()
        return [dict(r) for r in rows]


def stats():
    with connect() as c:
        total = c.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        phish = c.execute("SELECT COUNT(*) FROM scans WHERE verdict='phishing'").fetchone()[0]
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        return {"total_scans": total, "phishing": phish,
                "legitimate": total - phish, "users": users}


def record_model(name: str, version: str, accuracy: float, f1: float) -> None:
    with connect() as c:
        c.execute("UPDATE models SET is_active = 0")
        c.execute(
            "INSERT INTO models (name, version, accuracy, f1, trained_at, is_active) "
            "VALUES (?,?,?,?,?,1)", (name, version, accuracy, f1, now()))
