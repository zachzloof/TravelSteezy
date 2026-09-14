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
    trip_start_date     TEXT,      -- DEPRECATED: kept only so an old row does not
    trip_end_date       TEXT,      -- error; nothing reads or writes these any more
    visa_deadline_date  TEXT,      -- DEPRECATED: same as above, the "hard deadline"
    visa_deadline_note  TEXT,      -- feature was removed; nothing reads or writes these
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

-- ==================================================================== #
-- EXTENSION: structured travel profile, tracking and reviews
-- ==================================================================== #

-- Onboarding state. Onboarding is conversational and multi-turn, so we need to
-- know where a user is up to and whether to keep steering the conversation.
CREATE TABLE IF NOT EXISTS onboarding_state (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    status      TEXT    NOT NULL DEFAULT 'not_started',  -- not_started|in_progress|complete|skipped
    step        TEXT    NOT NULL DEFAULT 'history',      -- history|wishlist|preferences|done
    turns       INTEGER NOT NULL DEFAULT 0,
    started_at  TEXT,
    completed_at TEXT
);

-- Structured travel history. Supersedes visited_history: adds city/town
-- granularity, explicit route ordering, how we learned about the visit, and the
-- post-visit review. visited_history is still maintained for the country-level
-- "which countries have you been to" view and for backwards compatibility.
CREATE TABLE IF NOT EXISTS travel_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location        TEXT    NOT NULL,                 -- "Chiang Mai"
    location_type   TEXT    NOT NULL DEFAULT 'city',  -- country|city|town|region
    country         TEXT,                             -- "Thailand"
    order_index     INTEGER NOT NULL DEFAULT 0,       -- position in the route
    arrival_date    TEXT,
    departure_date  TEXT,
    source          TEXT    NOT NULL DEFAULT 'manual',-- onboarding|tracked|manual|agent
    notes           TEXT,
    -- post-visit review, filled in when the review prompt is answered
    rating          INTEGER,                          -- 1-5
    review_notes    TEXT,
    reviewed_at     TEXT,
    review_prompted_at TEXT,                          -- when we last asked
    last_mentioned_at  TEXT,                          -- drives the time-based trigger
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, location, arrival_date)
);
CREATE INDEX IF NOT EXISTS idx_history_user ON travel_history(user_id, order_index);

-- Places the user wants to go. A tracked visit promotes the matching row out of
-- here and into travel_history.
CREATE TABLE IF NOT EXISTS wishlist (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location      TEXT    NOT NULL,
    location_type TEXT    NOT NULL DEFAULT 'city',
    country       TEXT,
    priority      INTEGER NOT NULL DEFAULT 2,          -- 1 high, 2 medium, 3 low
    status        TEXT    NOT NULL DEFAULT 'open',     -- open|visited|dropped
    source        TEXT    NOT NULL DEFAULT 'manual',
    note          TEXT,
    added_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    resolved_at   TEXT,
    UNIQUE(user_id, location)
);
CREATE INDEX IF NOT EXISTS idx_wishlist_user ON wishlist(user_id, status);

-- Structured interests, replacing the free-text trip_profile.interests column as
-- the thing agents query. The text column is kept and mirrored for prompts.
CREATE TABLE IF NOT EXISTS user_interests (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    interest  TEXT    NOT NULL,                        -- nightlife|nature|food|...
    weight    INTEGER NOT NULL DEFAULT 1,
    added_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, interest)
);
CREATE INDEX IF NOT EXISTS idx_interests_user ON user_interests(user_id);

-- Whether a surfaced recommendation was taken. Feeds the RAG experience loop.
CREATE TABLE IF NOT EXISTS recommendation_feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location     TEXT    NOT NULL,
    from_location TEXT,
    verdict      TEXT    NOT NULL,                     -- accepted|rejected
    reason       TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_recfeedback_user ON recommendation_feedback(user_id);

-- Passports the traveller holds. A real long-term traveller often has two, and
-- which one they present changes the visa answer entirely - an Irish passport
-- and a UK passport are not the same at a Schengen or an ASEAN border. Stored as
-- rows rather than a comma-joined column so the logistics agent can reason over
-- them one at a time. trip_profile.nationality mirrors the primary passport, so
-- every existing prompt, tool and eval that reads `nationality` keeps working.
CREATE TABLE IF NOT EXISTS passports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    country     TEXT    NOT NULL,
    is_primary  INTEGER NOT NULL DEFAULT 0,
    added_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, country)
);
CREATE INDEX IF NOT EXISTS idx_passports_user ON passports(user_id);

-- Google Places response cache. Places bills per call and rate limits, so
-- identical lookups inside the TTL are served from here.
CREATE TABLE IF NOT EXISTS places_cache (
    cache_key   TEXT PRIMARY KEY,
    payload     TEXT NOT NULL,                         -- JSON
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- In-app bug reports. trace_text is a fully-formatted snapshot (description +
-- recent conversation + trace link) frozen at report time, so it stays exactly
-- what the reporter meant even if their conversation history moves on -
-- readable straight off the admin panel and pastable into Claude Code as-is.
CREATE TABLE IF NOT EXISTS bug_reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username    TEXT    NOT NULL,
    description TEXT    NOT NULL,
    page        TEXT,
    user_agent  TEXT,
    trace_id    TEXT,
    trace_url   TEXT,
    trace_text  TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'open',        -- open | resolved
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_bugreports_status ON bug_reports(status, created_at);
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
    """Create tables if they do not exist, then run migrations. Safe on every boot."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    add_missing_columns()
    migrate_visited_history()


# Columns added after the first release. SQLite has no ADD COLUMN IF NOT EXISTS,
# so we check PRAGMA table_info first. Each entry is (table, column, definition).
LATE_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("trip_profile", "social_style", "TEXT"),          # solo | couple | group
    ("trip_profile", "onboarded", "INTEGER NOT NULL DEFAULT 0"),
    # Which onboarding questions have actually been answered, as a JSON list.
    # Progress used to be a single "step" cursor, which could not express "they
    # skipped question 2 and answered 3", and so could not resume correctly.
    ("onboarding_state", "answered", "TEXT"),
    # The calendar date (YYYY-MM-DD, not a timestamp) of this account's most
    # recent REAL chat turn - never touched by onboarding or by the catch-up
    # prompt's own gate check. Comparing it to today's date is how the "you're
    # back after a gap" catch-up session decides whether one is due.
    ("trip_profile", "last_active_date", "TEXT"),
    # Marks up to travel.MAX_KEY_INTERESTS interests as the traveller's declared
    # top priorities, distinct from `weight` (a mention counter). Set explicitly
    # via My Preferences / POST /travel/me/interests/key, never inferred.
    ("user_interests", "is_key", "INTEGER NOT NULL DEFAULT 0"),
)


def add_missing_columns() -> list[str]:
    added: list[str] = []
    with get_conn() as conn:
        for table, column, definition in LATE_COLUMNS:
            existing = {
                r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                added.append(f"{table}.{column}")
    return added


def migrate_visited_history() -> int:
    """Copy legacy country-level rows into the structured travel_history table.

    Idempotent: a row is only copied if travel_history holds nothing for that
    (user, location) pair. Existing installs therefore keep their history when
    the extension is deployed, rather than appearing to have lost it.
    """
    copied = 0
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT v.user_id, v.country, v.arrival_date, v.departure_date, v.notes "
            "FROM visited_history v WHERE NOT EXISTS ("
            "  SELECT 1 FROM travel_history t "
            "  WHERE t.user_id = v.user_id AND t.location = v.country COLLATE NOCASE"
            ") ORDER BY v.id ASC"
        ).fetchall()
        for row in rows:
            next_order = conn.execute(
                "SELECT COALESCE(MAX(order_index), 0) + 1 FROM travel_history WHERE user_id = ?",
                (row["user_id"],),
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO travel_history "
                "(user_id, location, location_type, country, order_index, arrival_date, "
                " departure_date, source, notes) "
                "VALUES (?,?,'country',?,?,?,?,'migrated',?)",
                (
                    row["user_id"], row["country"], row["country"], next_order,
                    row["arrival_date"], row["departure_date"], row["notes"],
                ),
            )
            copied += 1
    return copied
