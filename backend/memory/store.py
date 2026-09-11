"""The memory module.

This is deliberately a standalone, inspectable module rather than "conversation
history stuffed back into a prompt". Each of the five memory questions from the
syllabus maps to a named function in here:

  WHAT WE KEEP    -> ``trip_profile`` (active context, one row per account)
                     ``visited_history`` (append-only historical log)
  WHEN WE WRITE   -> ``update_profile`` / ``log_departure`` / ``append_turn``
                     are explicit calls. The orchestrator invokes them as ADK tools;
                     the "My Preferences" screen invokes the same functions via
                     PATCH /profile/me. Every call lands in ``memory_writes``.
  WHERE IT LIVES  -> SQLite file on the Railway volume (see backend/db.py).
  HOW WE RETRIEVE -> ``get_memory_snapshot`` at the top of every turn, hydrating
                     every agent, and served by GET /profile/me.
  WHEN WE FORGET  -> ``archive_country`` moves a country out of active context;
                     ``prune_turns`` caps conversational working memory.
"""
from __future__ import annotations

import json
from typing import Any

from backend.config import settings
from backend.db import get_conn

# Columns a caller may write to trip_profile. Anything else is ignored, so an LLM
# tool call cannot invent columns or smuggle SQL in through a field name.
PROFILE_FIELDS: tuple[str, ...] = (
    "nationality",
    "budget_band",
    "travel_style",
    "climate_preference",
    "current_location",
    "trip_start_date",
    "trip_end_date",
    "visa_deadline_date",
    "visa_deadline_note",
    "interests",
)

BUDGET_BANDS = {"shoestring", "mid", "comfortable"}
TRAVEL_STYLES = {"slow", "balanced", "fast"}
CLIMATE_PREFS = {"cool", "temperate", "hot", "no_preference"}


# --------------------------------------------------------------------------- #
# audit trail
# --------------------------------------------------------------------------- #
def _record_write(conn, user_id: int, operation: str, payload: dict, source: str) -> None:
    conn.execute(
        "INSERT INTO memory_writes (user_id, operation, payload, source) VALUES (?,?,?,?)",
        (user_id, operation, json.dumps(payload, default=str), source),
    )


def get_write_log(user_id: int, limit: int = 25) -> list[dict[str, Any]]:
    """Recent memory writes for this account - shows *when* we wrote, in the UI."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT operation, payload, source, created_at FROM memory_writes "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [
        {
            "operation": r["operation"],
            "payload": json.loads(r["payload"]),
            "source": r["source"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# HOW WE RETRIEVE - called at the start of every turn
# --------------------------------------------------------------------------- #
def ensure_profile(user_id: int) -> None:
    """Create an empty profile row for a new account (idempotent)."""
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO trip_profile (user_id) VALUES (?)", (user_id,))


def get_profile(user_id: int) -> dict[str, Any]:
    """Return the account's active trip profile. Never raises for a missing row."""
    ensure_profile(user_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM trip_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
    profile: dict[str, Any] = {f: (row[f] if row else None) for f in PROFILE_FIELDS}
    profile["user_id"] = user_id
    profile["updated_at"] = row["updated_at"] if row else None
    return profile


def get_visited_history(user_id: int) -> list[dict[str, Any]]:
    """The append-only historical log, newest first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT country, arrival_date, departure_date, notes, logged_at "
            "FROM visited_history WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_memory_snapshot(user_id: int) -> dict[str, Any]:
    """Everything the assistant remembers for this account, in one read.

    This hydrates the agents AND backs GET /profile/me, so what the chat claims to
    remember and what the endpoint reports cannot drift apart.
    """
    return {
        "profile": get_profile(user_id),
        "visited_history": get_visited_history(user_id),
        "recent_turns": get_recent_turns(user_id),
    }


# --------------------------------------------------------------------------- #
# WHEN WE WRITE - explicit calls, never an implicit prompt side effect
# --------------------------------------------------------------------------- #
def update_profile(
    user_id: int, updates: dict[str, Any], source: str = "agent"
) -> dict[str, Any]:
    """Write one or more profile fields. Unknown keys and empty values are dropped.

    ``source`` separates an agent-inferred write from the user's explicit edit in
    the My Preferences screen. Both paths funnel through here on purpose.
    """
    clean: dict[str, Any] = {}
    for key, value in (updates or {}).items():
        if key not in PROFILE_FIELDS or value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        lowered = text.lower()
        if key == "budget_band" and lowered in BUDGET_BANDS:
            text = lowered
        elif key == "travel_style" and lowered in TRAVEL_STYLES:
            text = lowered
        elif key == "climate_preference" and lowered in CLIMATE_PREFS:
            text = lowered
        clean[key] = text

    if not clean:
        return get_profile(user_id)

    ensure_profile(user_id)
    assignments = ", ".join(f"{k} = ?" for k in clean)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE trip_profile SET {assignments}, updated_at = datetime('now') "
            "WHERE user_id = ?",
            (*clean.values(), user_id),
        )
        _record_write(conn, user_id, "update_profile", clean, source)
    return get_profile(user_id)


def log_departure(
    user_id: int,
    country: str,
    departure_date: str | None = None,
    arrival_date: str | None = None,
    notes: str | None = None,
    source: str = "agent",
) -> dict[str, Any]:
    """The user has left a country: append to history, archive out of active context.

    This is the concrete "when you forget" code path.
    """
    country = (country or "").strip()
    if not country:
        return {"ok": False, "reason": "no country given"}

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO visited_history (user_id, country, arrival_date, departure_date, notes) "
            "VALUES (?,?,?,?,?)",
            (user_id, country, arrival_date, departure_date, notes),
        )
        _record_write(
            conn,
            user_id,
            "log_departure",
            {"country": country, "departure_date": departure_date},
            source,
        )
    archived = archive_country(user_id, country, source=source)
    return {"ok": True, "country": country, "archived_from_active_context": archived}


def append_turn(user_id: int, role: str, content: str) -> None:
    """Append one conversational turn, then prune to the retention window."""
    if not content:
        return
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversation_turns (user_id, role, content) VALUES (?,?,?)",
            (user_id, role, content),
        )
    prune_turns(user_id)


# --------------------------------------------------------------------------- #
# WHEN WE FORGET
# --------------------------------------------------------------------------- #
def archive_country(user_id: int, country: str, source: str = "agent") -> bool:
    """If the archived country is the profile's ``current_location``, clear it.

    The country stops being live context but stays readable in ``visited_history``,
    so a later re-entry or re-entry-visa question can still reach it.
    Returns True when active context actually changed.
    """
    profile = get_profile(user_id)
    current = (profile.get("current_location") or "").strip().lower()
    if not current or current != country.strip().lower():
        return False
    with get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET current_location = NULL, updated_at = datetime('now') "
            "WHERE user_id = ?",
            (user_id,),
        )
        _record_write(conn, user_id, "archive_country", {"country": country}, source)
    return True


def prune_turns(user_id: int) -> int:
    """Cap conversational working memory at settings.working_memory_turns.

    The durable trip profile is deliberately NOT subject to this - it persists for
    the life of the account. Only chat scrollback decays.
    """
    keep = settings.working_memory_turns
    with get_conn() as conn:
        deleted = conn.execute(
            "DELETE FROM conversation_turns WHERE user_id = ? AND id NOT IN ("
            "  SELECT id FROM conversation_turns WHERE user_id = ? ORDER BY id DESC LIMIT ?"
            ")",
            (user_id, user_id, keep),
        ).rowcount
    return max(deleted, 0)


def get_recent_turns(user_id: int, limit: int | None = None) -> list[dict[str, Any]]:
    limit = limit or settings.working_memory_turns
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM conversation_turns "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def forget_account_memory(user_id: int) -> None:
    """Hard reset, used by the eval harness and by an explicit user request.

    Wipes profile, history and scrollback for ONE account without touching the
    account itself or any other account's data.
    """
    with get_conn() as conn:
        conn.execute("DELETE FROM conversation_turns WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM visited_history WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM trip_profile WHERE user_id = ?", (user_id,))
        _record_write(conn, user_id, "forget_account_memory", {}, "user_edit")


# --------------------------------------------------------------------------- #
# rendering for prompts
# --------------------------------------------------------------------------- #
def format_profile_for_prompt(snapshot: dict[str, Any]) -> str:
    """Render the memory snapshot as the block injected into every agent prompt."""
    profile = snapshot.get("profile", {}) or {}
    visited = snapshot.get("visited_history", []) or []

    def line(key: str, label: str) -> str:
        value = profile.get(key)
        return f"- {label}: {value}" if value else f"- {label}: (unknown)"

    lines = [
        line("nationality", "Passport / nationality"),
        line("current_location", "Currently in"),
        line("budget_band", "Budget band"),
        line("travel_style", "Travel pace"),
        line("climate_preference", "Climate preference"),
        line("trip_start_date", "Trip start"),
        line("trip_end_date", "Trip end"),
        line("interests", "Interests"),
    ]
    if profile.get("visa_deadline_date"):
        note = profile.get("visa_deadline_note") or "visa/permit expiry"
        lines.append(f"- HARD DEADLINE: {profile['visa_deadline_date']} ({note})")
    if visited:
        been = ", ".join(
            v["country"] + (f" (left {v['departure_date']})" if v.get("departure_date") else "")
            for v in visited[:10]
        )
        lines.append(f"- Already visited this trip: {been}")
    return "\n".join(lines)
