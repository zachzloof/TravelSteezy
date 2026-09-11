"""SQLite connection handling + schema migration.

The database file lives on the Railway volume (see DATA_DIR / DB_PATH in config.py)
so it survives redeploys and restarts. Everything is keyed by ``user_id`` -- there is
no anonymous/browser-session storage anywhere in this app.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from backend.config import settings

SCHEMA = """
-- ---------------------------------------------------------------- accounts
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash   TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending',   -- pending | approved | rejected
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    approved_at     TEXT,
    last_seen_at    TEXT
);

-- ------------------------------------------------- ACTIVE CONTEXT (1 per user)
-- "What you keep": the live trip profile that hydrates every agent on every turn.
CREATE TABLE IF NOT EXISTS trip_profile (
    user_id             INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    nationality         TEXT,
    budget_band         TEXT,      -- shoestring | mid | comfortable
    travel_style        TEXT,      -- slow | balanced | fast
    climate_preference  TEXT,      -- cool | temperate | hot | no_preference
    current_location    TEXT,
    trip_start_date     TEXT,      -- ISO yyyy-mm-dd
    trip_end_date       TEXT,
    visa_deadline_date  TEXT,      -- next hard visa/permit expiry
    visa_deadline_note  TEXT,
    interests           TEXT,      -- free text, comma separated
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- -------------------------------------------- HISTORICAL LOG (append-only)
-- "When you forget": a country leaves active context and lands here on departure.
CREATE TABLE IF NOT EXISTS visited_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    country         TEXT    NOT NULL,
    arrival_date    TEXT,
    departure_date  TEXT,
    notes           TEXT,
    logged_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_visited_user ON visited_history(user_id);

-- ------------------------------------------------- conversational working memory
-- Capped at settings.working_memory_turns; older turns are pruned on write.
CREATE TABLE IF NOT EXISTS conversation_turns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        TEXT    NOT NULL,         -- user | assistant
    content     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_turns_user ON conversation_turns(user_id);

-- ------------------------------------------------- audit trail of memory writes
-- Makes "when you write" demoable: every explicit write is recorded here.
CREATE TABLE IF NOT EXISTS memory_writes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation   TEXT    NOT NULL,         -- update_profile | log_departure | ...
    payload     TEXT    NOT NULL,         -- JSON of what changed
    source      TEXT    NOT NULL,         -- agent | user_edit | seed
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_writes_user ON memory_writes(user_id);
"""


def connect() -> sqlite3.Connection:
    """Open a connection to the SQLite file with sane defaults."""
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL keeps reads non-blocking while a write is in flight.
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Context-managed connection that commits on success and rolls back on error."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist. Safe to call on every boot."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
