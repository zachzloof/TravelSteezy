"""Catch-up: "here's where we left off - what's changed since?"

The problem this solves: every turn re-hydrates the stored profile, but nothing
ever prompted the traveller to actually UPDATE it after a gap. Someone who spoke
to the assistant on Tuesday and comes back on Friday might have left Chiang Mai,
crossed into Laos, changed their mind about a whole leg of the trip - and the
first the assistant hears of any of it is whatever happens to come up naturally
in conversation, if it comes up at all.

The design is deliberately NOT a repeat of the old onboarding mistake (a
conversational agent hijacking the first few turns of /chat, choosing what to
ask next). Catch-up is one fixed prompt, shown once per calendar-day gap, with
two ways to clear it:

  * type what has changed - which is processed through the SAME turn pipeline
    every ordinary chat message goes through (visits, departures, wishlist
    changes and reviews all get picked up for free, because it IS a normal
    turn), or
  * a one-tap "still here, nothing's changed" button that costs no model call
    at all.

"Due" is computed from ``trip_profile.last_active_date`` - a plain calendar
date, not a timestamp, touched once per REAL chat turn by ``run_turn`` (see
runner.py). It is deliberately not touched by onboarding or by reading the
catch-up status itself, so opening the chat page cannot silently clear it.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from backend.db import get_conn
from backend.memory import store, travel


def touch_last_active(user_id: int) -> None:
    """Record that a real chat turn happened today.

    Called once per genuine /chat turn (including a catch-up "update"
    message, which IS a genuine turn). Deliberately not audit-logged: like
    last_mentioned_at elsewhere in this codebase, this is bookkeeping, not
    something a traveller needs to see in "what was just remembered".
    """
    with get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET last_active_date = ? WHERE user_id = ?",
            (date.today().isoformat(), user_id),
        )


def get_last_active_date(user_id: int) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT last_active_date FROM trip_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row["last_active_date"] if row else None


def dismiss(user_id: int) -> None:
    """The quick "still here, nothing's changed" button. No model call."""
    touch_last_active(user_id)


def status(user_id: int) -> dict[str, Any]:
    """Is a catch-up prompt due, and what should it say.

    ``due`` is only ever true once per calendar-day gap - the DAY it becomes
    true, either answering it or dismissing it touches last_active_date to
    today, so it will not fire again until tomorrow at the earliest. A
    brand-new account (last_active_date is still null - onboarding never sets
    it) has nothing to catch up on, which is correct: there is no "last time we
    spoke" yet.
    """
    last = get_last_active_date(user_id)
    if not last:
        return {"due": False, "last_active_date": None, "days_since": None, "summary": ""}

    try:
        last_date = date.fromisoformat(last)
    except ValueError:
        return {"due": False, "last_active_date": last, "days_since": None, "summary": ""}

    days_since = (date.today() - last_date).days
    due = days_since >= 1
    return {
        "due": due,
        "last_active_date": last,
        "days_since": days_since,
        "summary": _summary(user_id, days_since) if due else "",
    }


def _summary(user_id: int, days_since: int) -> str:
    """A short, human sentence - not fed to any LLM, just shown on the card."""
    profile = store.get_profile(user_id)
    snapshot = travel.get_travel_snapshot(user_id)
    history = snapshot["travel_history"]
    wishlist = snapshot["wishlist"]

    when = "yesterday" if days_since == 1 else f"{days_since} days ago"
    parts = [f"Last time we spoke was {when}."]

    if profile.get("current_location"):
        parts.append(f"You were in {profile['current_location']}.")
    elif history:
        parts.append(f"You were last at {history[-1]['location']}.")

    if wishlist:
        parts.append(f"{wishlist[0]['location']} was next on your wishlist.")

    if profile.get("visa_deadline_date"):
        note = profile.get("visa_deadline_note") or "a deadline"
        parts.append(f"You had {note} on {profile['visa_deadline_date']}.")

    return " ".join(parts)
