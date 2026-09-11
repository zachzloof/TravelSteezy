"""Structured travel memory: history, wishlist, interests, reviews, onboarding.

This sits alongside ``backend.memory.store`` and follows the same contract: every
function is an explicit call scoped to one ``user_id``, and every write lands in
the ``memory_writes`` audit log. Nothing here is an implicit prompt side effect.

Why a second module rather than growing store.py: store.py answers the five
syllabus memory questions for the *active trip profile*. This module holds the
structured route/wishlist/review data the recommendation agents query. Keeping
them apart keeps each readable.
"""
from __future__ import annotations

from typing import Any

from backend.db import get_conn
from backend.memory.store import _record_write

LOCATION_TYPES = {"country", "city", "town", "region"}
VALID_INTERESTS = {
    "nightlife", "nature", "food", "history", "beaches", "diving", "trekking",
    "surfing", "culture", "festivals", "photography", "wildlife", "art",
    "architecture", "markets", "music", "yoga", "climbing", "cycling", "wellness",
}
SOCIAL_STYLES = {"solo", "couple", "group"}


def _norm(value: str | None) -> str:
    return (value or "").strip()


def _key(value: str | None) -> str:
    return _norm(value).lower()


# --------------------------------------------------------------------------- #
# travel history
# --------------------------------------------------------------------------- #
def add_travel_history(
    user_id: int,
    location: str,
    location_type: str = "city",
    country: str | None = None,
    arrival_date: str | None = None,
    departure_date: str | None = None,
    notes: str | None = None,
    source: str = "manual",
    order_index: int | None = None,
) -> dict[str, Any]:
    """Append a visited place to the route.

    ``order_index`` defaults to the end of the route. Re-adding a place that is
    already recorded updates the existing row instead of duplicating it, because
    the tracker and onboarding can both surface the same visit.
    """
    location = _norm(location)
    if not location:
        return {"ok": False, "reason": "no location given"}
    if location_type not in LOCATION_TYPES:
        location_type = "city"

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id, order_index FROM travel_history "
            "WHERE user_id = ? AND location = ? COLLATE NOCASE",
            (user_id, location),
        ).fetchone()

        if existing is not None:
            # Only count it as a write if a field actually gains a value. Touching
            # last_mentioned_at is bookkeeping, not something to show the user or
            # log in the audit trail.
            changed = conn.execute(
                "UPDATE travel_history SET "
                "  country = COALESCE(?, country),"
                "  arrival_date = COALESCE(?, arrival_date),"
                "  departure_date = COALESCE(?, departure_date),"
                "  notes = COALESCE(?, notes),"
                "  last_mentioned_at = datetime('now') "
                "WHERE id = ? AND ("
                "  (? IS NOT NULL AND country IS NULL)"
                "  OR (? IS NOT NULL AND arrival_date IS NULL)"
                "  OR (? IS NOT NULL AND departure_date IS NULL)"
                "  OR (? IS NOT NULL AND notes IS NULL))",
                (country, arrival_date, departure_date, notes, existing["id"],
                 country, arrival_date, departure_date, notes),
            ).rowcount
            if not changed:
                conn.execute(
                    "UPDATE travel_history SET last_mentioned_at = datetime('now') WHERE id = ?",
                    (existing["id"],),
                )
            else:
                _record_write(
                    conn, user_id, "update_travel_history",
                    {"location": location, "source": source}, source,
                )
            return {
                "ok": True, "location": location, "created": False,
                "changed": bool(changed), "id": existing["id"],
            }

        if order_index is None:
            order_index = conn.execute(
                "SELECT COALESCE(MAX(order_index), 0) + 1 FROM travel_history WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

        cursor = conn.execute(
            "INSERT INTO travel_history "
            "(user_id, location, location_type, country, order_index, arrival_date, "
            " departure_date, source, notes, last_mentioned_at) "
            "VALUES (?,?,?,?,?,?,?,?,?, datetime('now'))",
            (user_id, location, location_type, country, order_index,
             arrival_date, departure_date, source, notes),
        )
        _record_write(
            conn, user_id, "add_travel_history",
            {"location": location, "location_type": location_type, "order": order_index},
            source,
        )
        return {"ok": True, "location": location, "created": True, "id": int(cursor.lastrowid)}


def get_travel_history(user_id: int) -> list[dict[str, Any]]:
    """The route in order, oldest first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, location, location_type, country, order_index, arrival_date, "
            "       departure_date, source, notes, rating, review_notes, reviewed_at, "
            "       review_prompted_at, last_mentioned_at "
            "FROM travel_history WHERE user_id = ? ORDER BY order_index ASC, id ASC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def touch_location_mention(user_id: int, location: str) -> None:
    """Record that the user just talked about a place.

    Drives the time-based review trigger: a place that has not been mentioned for
    N days, and has a departure date or is no longer current, becomes reviewable.
    """
    location = _norm(location)
    if not location:
        return
    with get_conn() as conn:
        conn.execute(
            "UPDATE travel_history SET last_mentioned_at = datetime('now') "
            "WHERE user_id = ? AND location = ? COLLATE NOCASE",
            (user_id, location),
        )


# --------------------------------------------------------------------------- #
# wishlist
# --------------------------------------------------------------------------- #
def add_wishlist(
    user_id: int,
    location: str,
    location_type: str = "city",
    country: str | None = None,
    priority: int = 2,
    note: str | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    location = _norm(location)
    if not location:
        return {"ok": False, "reason": "no location given"}
    if location_type not in LOCATION_TYPES:
        location_type = "city"
    priority = priority if priority in (1, 2, 3) else 2

    # Never wishlist somewhere already visited.
    if any(_key(h["location"]) == _key(location) for h in get_travel_history(user_id)):
        return {"ok": False, "reason": "already visited", "location": location}

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO wishlist (user_id, location, location_type, country, priority, note, source) "
            "VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(user_id, location) DO UPDATE SET "
            "  priority = excluded.priority,"
            "  country = COALESCE(excluded.country, wishlist.country),"
            "  note = COALESCE(excluded.note, wishlist.note),"
            "  status = 'open', resolved_at = NULL",
            (user_id, location, location_type, country, priority, note, source),
        )
        _record_write(
            conn, user_id, "add_wishlist",
            {"location": location, "priority": priority}, source,
        )
    return {"ok": True, "location": location, "priority": priority}


def get_wishlist(user_id: int, status: str = "open") -> list[dict[str, Any]]:
    query = (
        "SELECT id, location, location_type, country, priority, status, source, note, "
        "       added_at, resolved_at FROM wishlist WHERE user_id = ?"
    )
    params: list[Any] = [user_id]
    if status != "all":
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY priority ASC, added_at ASC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def resolve_wishlist(
    user_id: int, location: str, status: str = "visited", source: str = "agent"
) -> bool:
    """Close out a wishlist entry. Returns True if a row actually changed."""
    location = _norm(location)
    if not location:
        return False
    with get_conn() as conn:
        changed = conn.execute(
            "UPDATE wishlist SET status = ?, resolved_at = datetime('now') "
            "WHERE user_id = ? AND location = ? COLLATE NOCASE AND status = 'open'",
            (status, user_id, location),
        ).rowcount
        if changed:
            _record_write(
                conn, user_id, "resolve_wishlist",
                {"location": location, "status": status}, source,
            )
    return bool(changed)


# --------------------------------------------------------------------------- #
# interests / preferences
# --------------------------------------------------------------------------- #
def set_interests(
    user_id: int, interests: list[str], source: str = "agent", replace: bool = False
) -> list[str]:
    """Store interests as rows so agents can filter on them.

    Unrecognised interests are still stored - the vocabulary in VALID_INTERESTS is
    a hint for the onboarding agent, not a whitelist that silently drops what a
    real traveller told us.
    """
    cleaned = []
    for item in interests or []:
        text = _key(item)
        if text and text not in cleaned:
            cleaned.append(text)

    with get_conn() as conn:
        if replace:
            conn.execute("DELETE FROM user_interests WHERE user_id = ?", (user_id,))
        for interest in cleaned:
            conn.execute(
                "INSERT INTO user_interests (user_id, interest) VALUES (?,?) "
                "ON CONFLICT(user_id, interest) DO UPDATE SET weight = user_interests.weight + 1",
                (user_id, interest),
            )
        if cleaned:
            _record_write(conn, user_id, "set_interests", {"interests": cleaned}, source)

    # Mirror into the free-text column so existing prompt rendering keeps working.
    all_interests = get_interests(user_id)
    if all_interests:
        with get_conn() as conn:
            conn.execute(
                "UPDATE trip_profile SET interests = ?, updated_at = datetime('now') "
                "WHERE user_id = ?",
                (", ".join(all_interests), user_id),
            )
    return all_interests


def get_interests(user_id: int) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT interest FROM user_interests WHERE user_id = ? "
            "ORDER BY weight DESC, interest ASC",
            (user_id,),
        ).fetchall()
    return [r["interest"] for r in rows]


def set_social_style(user_id: int, style: str, source: str = "agent") -> str | None:
    style = _key(style)
    if style not in SOCIAL_STYLES:
        return None
    with get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET social_style = ?, updated_at = datetime('now') "
            "WHERE user_id = ?",
            (style, user_id),
        )
        _record_write(conn, user_id, "set_social_style", {"social_style": style}, source)
    return style


# --------------------------------------------------------------------------- #
# reviews
# --------------------------------------------------------------------------- #
def save_review(
    user_id: int,
    location: str,
    rating: int | None = None,
    review_notes: str | None = None,
    source: str = "user_edit",
) -> dict[str, Any]:
    """Attach a post-visit review to the travel_history row for that place."""
    location = _norm(location)
    if not location:
        return {"ok": False, "reason": "no location given"}
    if rating is not None:
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return {"ok": False, "reason": "rating must be a number 1-5"}
        if not 1 <= rating <= 5:
            return {"ok": False, "reason": "rating must be between 1 and 5"}

    with get_conn() as conn:
        changed = conn.execute(
            "UPDATE travel_history SET rating = COALESCE(?, rating), "
            "  review_notes = COALESCE(?, review_notes), reviewed_at = datetime('now') "
            "WHERE user_id = ? AND location = ? COLLATE NOCASE",
            (rating, review_notes, user_id, location),
        ).rowcount
        if changed:
            _record_write(
                conn, user_id, "save_review",
                {"location": location, "rating": rating}, source,
            )
    if not changed:
        return {"ok": False, "reason": f"{location} is not in your travel history"}
    return {"ok": True, "location": location, "rating": rating}


def get_pending_reviews(user_id: int, stale_days: int = 3) -> list[dict[str, Any]]:
    """Places that are due a review prompt.

    A place qualifies when it has no review yet AND either it has a departure date
    in the past, or it has not been mentioned for ``stale_days`` - the two
    triggers the brief asks for, explicit signal and time-based staleness.
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, location, country, arrival_date, departure_date, "
            "       last_mentioned_at, review_prompted_at "
            "FROM travel_history "
            "WHERE user_id = ? AND rating IS NULL AND review_notes IS NULL "
            "  AND ("
            "    (departure_date IS NOT NULL AND departure_date <= date('now'))"
            "    OR (last_mentioned_at IS NOT NULL "
            "        AND julianday('now') - julianday(last_mentioned_at) >= ?)"
            "  ) "
            "ORDER BY order_index DESC",
            (user_id, stale_days),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_review_prompted(user_id: int, location: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE travel_history SET review_prompted_at = datetime('now') "
            "WHERE user_id = ? AND location = ? COLLATE NOCASE",
            (user_id, location),
        )


# --------------------------------------------------------------------------- #
# recommendation feedback
# --------------------------------------------------------------------------- #
def record_recommendation_feedback(
    user_id: int,
    location: str,
    verdict: str,
    from_location: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Log whether a surfaced suggestion was taken. Feeds the RAG experience loop."""
    location = _norm(location)
    verdict = _key(verdict)
    if not location or verdict not in {"accepted", "rejected"}:
        return {"ok": False, "reason": "need a location and verdict of accepted|rejected"}
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO recommendation_feedback (user_id, location, from_location, verdict, reason) "
            "VALUES (?,?,?,?,?)",
            (user_id, location, from_location, verdict, reason),
        )
        _record_write(
            conn, user_id, "recommendation_feedback",
            {"location": location, "verdict": verdict}, "agent",
        )
    return {"ok": True, "location": location, "verdict": verdict}


def get_recommendation_feedback(user_id: int | None = None) -> list[dict[str, Any]]:
    query = (
        "SELECT user_id, location, from_location, verdict, reason, created_at "
        "FROM recommendation_feedback"
    )
    params: tuple[Any, ...] = ()
    if user_id is not None:
        query += " WHERE user_id = ?"
        params = (user_id,)
    query += " ORDER BY id DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


# --------------------------------------------------------------------------- #
# onboarding state
# --------------------------------------------------------------------------- #
def get_onboarding(user_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO onboarding_state (user_id) VALUES (?)", (user_id,)
        )
        row = conn.execute(
            "SELECT status, step, turns, started_at, completed_at "
            "FROM onboarding_state WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return dict(row)


def set_onboarding(
    user_id: int, status: str | None = None, step: str | None = None, bump_turn: bool = False
) -> dict[str, Any]:
    get_onboarding(user_id)
    with get_conn() as conn:
        if status:
            conn.execute(
                "UPDATE onboarding_state SET status = ?, "
                "  started_at = COALESCE(started_at, datetime('now')), "
                "  completed_at = CASE WHEN ? = 'complete' THEN datetime('now') ELSE completed_at END "
                "WHERE user_id = ?",
                (status, status, user_id),
            )
            if status in {"complete", "skipped"}:
                conn.execute(
                    "UPDATE trip_profile SET onboarded = 1 WHERE user_id = ?", (user_id,)
                )
        if step:
            conn.execute(
                "UPDATE onboarding_state SET step = ? WHERE user_id = ?", (step, user_id)
            )
        if bump_turn:
            conn.execute(
                "UPDATE onboarding_state SET turns = turns + 1 WHERE user_id = ?", (user_id,)
            )
    return get_onboarding(user_id)


# --------------------------------------------------------------------------- #
# combined view
# --------------------------------------------------------------------------- #
def get_travel_snapshot(user_id: int) -> dict[str, Any]:
    """Everything structured we hold about this traveller's route and tastes."""
    return {
        "travel_history": get_travel_history(user_id),
        "wishlist": get_wishlist(user_id),
        "interests": get_interests(user_id),
        "pending_reviews": get_pending_reviews(user_id),
        "onboarding": get_onboarding(user_id),
    }


def format_travel_for_prompt(snapshot: dict[str, Any]) -> str:
    """Render the structured travel memory for injection into agent prompts."""
    history = snapshot.get("travel_history") or []
    wishlist = snapshot.get("wishlist") or []
    interests = snapshot.get("interests") or []

    lines: list[str] = []
    if history:
        route = " -> ".join(h["location"] for h in history)
        lines.append(f"- Route so far: {route}")
        rated = [h for h in history if h.get("rating")]
        for entry in rated[-4:]:
            note = f" ({entry['review_notes'][:90]})" if entry.get("review_notes") else ""
            lines.append(f"- Rated {entry['location']} {entry['rating']}/5{note}")
    else:
        lines.append("- Route so far: (nothing recorded yet)")

    if wishlist:
        labels = {1: "high", 2: "medium", 3: "low"}
        want = ", ".join(
            f"{w['location']} ({labels.get(w['priority'], 'medium')} priority)"
            for w in wishlist[:8]
        )
        lines.append(f"- Wants to go: {want}")
    else:
        lines.append("- Wants to go: (nothing on the wishlist)")

    if interests:
        lines.append(f"- Interests: {', '.join(interests)}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# onboarding progress, computed from what is actually stored
# --------------------------------------------------------------------------- #
ONBOARDING_TOPICS = ("history", "wishlist", "preferences")


def onboarding_gaps(user_id: int) -> dict[str, Any]:
    """Which onboarding topics are still unanswered, judged by stored data.

    Deliberately derived from the database rather than from the model telling us
    which step it thinks it is on. An earlier version trusted a "next_step" field
    in the model's reply; when extraction silently failed, the step never advanced
    and onboarding asked the same question forever.
    """
    from backend.memory.store import get_profile

    history = get_travel_history(user_id)
    wishlist = get_wishlist(user_id)
    interests = get_interests(user_id)
    profile = get_profile(user_id)

    have_preferences = bool(
        interests and (profile.get("budget_band") or profile.get("travel_style"))
    )
    missing = []
    if not history:
        missing.append("history")
    if not wishlist:
        missing.append("wishlist")
    if not have_preferences:
        missing.append("preferences")

    captured = []
    if history:
        captured.append("been to " + ", ".join(h["location"] for h in history[:6]))
    if wishlist:
        captured.append("wants " + ", ".join(w["location"] for w in wishlist[:6]))
    if interests:
        captured.append("into " + ", ".join(interests[:6]))
    if profile.get("budget_band"):
        captured.append(f"{profile['budget_band']} budget")
    if profile.get("travel_style"):
        captured.append(f"{profile['travel_style']} pace")
    if profile.get("social_style"):
        captured.append(f"travelling {profile['social_style']}")

    labels = {
        "history": "where they have already been on this trip, and roughly in what order",
        "wishlist": "where they most want to go next",
        "preferences": "how they travel: interests, budget level, pace, solo or with people",
    }
    return {
        "missing": missing,
        "missing_text": "; ".join(labels[m] for m in missing) or "nothing",
        "captured_text": "; ".join(captured) or "nothing yet",
        "complete": not missing,
    }
