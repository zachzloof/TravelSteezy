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

import json
from typing import Any

from backend.db import get_conn
from backend.memory.store import _record_write, ensure_profile

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


def remove_travel_history(user_id: int, location: str, source: str = "user_edit") -> bool:
    """Delete one stop from the route. Returns True if a row was actually removed.

    The route is the user's own record of their trip, so they get to correct it -
    a tracked visit inferred from "I might head to Pai" that they never made
    would otherwise sit in their history forever and skew every recommendation.
    """
    location = _norm(location)
    if not location:
        return False
    with get_conn() as conn:
        removed = conn.execute(
            "DELETE FROM travel_history WHERE user_id = ? AND location = ? COLLATE NOCASE",
            (user_id, location),
        ).rowcount
        if removed:
            _record_write(
                conn, user_id, "remove_travel_history", {"location": location}, source
            )
    return bool(removed)


def set_rating(user_id: int, location: str, rating: int | None, source: str = "user_edit") -> bool:
    """Set or clear the star rating on a stop, without touching the review text."""
    location = _norm(location)
    if not location:
        return False
    if rating is not None:
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return False
        if not 1 <= rating <= 5:
            return False
    with get_conn() as conn:
        changed = conn.execute(
            "UPDATE travel_history SET rating = ?, reviewed_at = datetime('now') "
            "WHERE user_id = ? AND location = ? COLLATE NOCASE",
            (rating, user_id, location),
        ).rowcount
        if changed:
            _record_write(
                conn, user_id, "set_rating", {"location": location, "rating": rating}, source
            )
    return bool(changed)


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

    # Somewhere already visited CAN be wishlisted: wanting to go back to a place
    # you loved is one of the most common things a long-term traveller says, and
    # refusing it (as an earlier version did) silently dropped real intent. It is
    # flagged as a revisit so the UI and the agents can tell the two apart.
    revisit = any(_key(h["location"]) == _key(location) for h in get_travel_history(user_id))

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
            {"location": location, "priority": priority, **({"revisit": True} if revisit else {})},
            source,
        )
    return {"ok": True, "location": location, "priority": priority, "revisit": revisit}


def get_wishlist(user_id: int, status: str = "open") -> list[dict[str, Any]]:
    query = (
        "SELECT w.id, w.location, w.location_type, w.country, w.priority, w.status, "
        "       w.source, w.note, w.added_at, w.resolved_at, "
        "       EXISTS(SELECT 1 FROM travel_history t "
        "              WHERE t.user_id = w.user_id "
        "                AND t.location = w.location COLLATE NOCASE) AS revisit "
        "FROM wishlist w WHERE w.user_id = ?"
    )
    params: list[Any] = [user_id]
    if status != "all":
        query += " AND w.status = ?"
        params.append(status)
    query += " ORDER BY w.priority ASC, w.added_at ASC"
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    for row in rows:
        row["revisit"] = bool(row.get("revisit"))
    return rows


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
        ensure_profile(user_id)
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


def get_interests_with_weight(user_id: int) -> list[dict[str, Any]]:
    """The raw rows, weight included - the memory debug page's own view."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT interest, weight, added_at FROM user_interests WHERE user_id = ? "
            "ORDER BY weight DESC, interest ASC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def remove_interest(user_id: int, interest: str, source: str = "user_edit") -> bool:
    """Delete one interest without touching the rest of the list."""
    interest = _key(interest)
    if not interest:
        return False
    with get_conn() as conn:
        removed = conn.execute(
            "DELETE FROM user_interests WHERE user_id = ? AND interest = ?",
            (user_id, interest),
        ).rowcount
        if removed:
            _record_write(conn, user_id, "remove_interest", {"interest": interest}, source)
    if removed:
        # Keep the mirrored free-text column (read by every agent prompt) in
        # sync, the same way set_interests does.
        remaining = get_interests(user_id)
        with get_conn() as conn:
            conn.execute(
                "UPDATE trip_profile SET interests = ?, updated_at = datetime('now') "
                "WHERE user_id = ?",
                (", ".join(remaining) if remaining else None, user_id),
            )
    return bool(removed)


def set_social_style(user_id: int, style: str, source: str = "agent") -> str | None:
    style = _key(style)
    if style not in SOCIAL_STYLES:
        return None
    # UPDATE against a missing row matches nothing and reports no error, so this
    # silently did nothing for a brand-new account whose profile row had not
    # been created yet - which is every account arriving at onboarding. Found by
    # the eval case onboarding-maps-plain-english-to-bands, which captured the
    # budget, the pace and the interests correctly and lost only "solo".
    ensure_profile(user_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET social_style = ?, updated_at = datetime('now') "
            "WHERE user_id = ?",
            (style, user_id),
        )
        _record_write(conn, user_id, "set_social_style", {"social_style": style}, source)
    return style


def clear_social_style(user_id: int, source: str = "user_edit") -> None:
    """Unset who they travel with. Its own function because social_style lives on
    trip_profile but is not one of store.PROFILE_FIELDS, so the generic clear
    path cannot reach it."""
    ensure_profile(user_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET social_style = NULL, updated_at = datetime('now') "
            "WHERE user_id = ?",
            (user_id,),
        )
        _record_write(conn, user_id, "clear_social_style", {}, source)


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
            "SELECT status, step, turns, started_at, completed_at, answered "
            "FROM onboarding_state WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    state = dict(row)
    # Stored as JSON text so the column stays a plain TEXT migration; decoded
    # here so no caller ever has to know that.
    try:
        answered = json.loads(state.pop("answered") or "[]")
    except (TypeError, ValueError):
        answered = []
    state["answered"] = [str(a) for a in answered if isinstance(a, (str, int))]
    return state


def mark_step_answered(user_id: int, step_id: str) -> list[str]:
    """Record that one onboarding question has been dealt with.

    Answering and skipping both land here: from the flow's point of view a
    skipped question is answered, it just yielded nothing. Keeping them the same
    is what stops a skipped optional question re-appearing on resume.
    """
    step_id = _norm(step_id)
    if not step_id:
        return get_onboarding(user_id)["answered"]
    answered = get_onboarding(user_id)["answered"]
    if step_id not in answered:
        answered.append(step_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE onboarding_state SET answered = ? WHERE user_id = ?",
            (json.dumps(answered), user_id),
        )
    return answered


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


def reset_onboarding(user_id: int, source: str = "user_edit") -> dict[str, Any]:
    """Send this account back through onboarding from question one.

    Deliberately does NOT touch travel_history/wishlist/interests/passports -
    this is "redo the questions", not "forget everything". A full wipe is
    store.forget_account_memory; this exists for the debug page and for
    "Redo the questions" in My Preferences, where the existing profile is
    exactly what onboarding is meant to let someone correct.
    """
    with get_conn() as conn:
        conn.execute(
            "UPDATE onboarding_state SET status = 'not_started', step = 'route', "
            "  turns = 0, answered = '[]', started_at = NULL, completed_at = NULL "
            "WHERE user_id = ?",
            (user_id,),
        )
        conn.execute("UPDATE trip_profile SET onboarded = 0 WHERE user_id = ?", (user_id,))
        _record_write(conn, user_id, "reset_onboarding", {}, source)
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
    else:
        lines.append("- Route so far: (nothing recorded yet)")

    # Ratings are the strongest preference signal in the whole profile, and a LOW
    # one is the most informative of all: somebody who rated Hanoi 2/5 is telling
    # you something about big, loud, traffic-heavy cities, not only about Hanoi.
    # An earlier version showed only the last four ratings with no framing, so a
    # 1/5 read to the model as a neutral fact about one town.
    def describe(entry: dict[str, Any]) -> str:
        note = f" - \"{entry['review_notes'][:110]}\"" if entry.get("review_notes") else ""
        return f"{entry['location']} {entry['rating']}/5{note}"

    loved = [h for h in history if (h.get("rating") or 0) >= 4]
    mixed = [h for h in history if (h.get("rating") or 0) == 3]
    disliked = [h for h in history if 1 <= (h.get("rating") or 0) <= 2]
    if loved:
        lines.append("- Rated highly: " + "; ".join(describe(e) for e in loved[-6:]))
    if mixed:
        lines.append("- Felt lukewarm about: " + "; ".join(describe(e) for e in mixed[-4:]))
    if disliked:
        lines.append("- Did NOT enjoy: " + "; ".join(describe(e) for e in disliked[-6:]))
    if loved or disliked:
        lines.append(
            "- Use those ratings: infer WHAT KIND of place they liked or disliked "
            "and apply it to the candidates. Somewhere similar to a place they "
            "rated 1-2/5 needs an explicit reason why it will land differently, "
            "or it should rank lower. Say which past rating drove the call."
        )

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
ONBOARDING_TOPICS = ("history", "passports", "wishlist", "preferences")


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
    if not (profile.get("passports") or profile.get("nationality")):
        missing.append("passports")
    if not wishlist:
        missing.append("wishlist")
    if not have_preferences:
        missing.append("preferences")

    captured = []
    if history:
        captured.append("been to " + ", ".join(h["location"] for h in history[:6]))
    rated = [h for h in history if h.get("rating")]
    if rated:
        captured.append(
            "rated " + ", ".join(f"{h['location']} {h['rating']}/5" for h in rated[:6])
        )
    if profile.get("passports"):
        captured.append("travels on " + ", ".join(profile["passports"]))
    if wishlist:
        captured.append("wants " + ", ".join(w["location"] for w in wishlist[:6]))
    if interests:
        captured.append("into " + ", ".join(interests[:6]))
    if profile.get("budget_band"):
        captured.append(f"{profile['budget_band']} budget")
    if profile.get("travel_style"):
        captured.append(f"{profile['travel_style']} pace")
    if profile.get("climate_preference"):
        captured.append(f"prefers it {profile['climate_preference']}")
    if profile.get("social_style"):
        captured.append(f"travelling {profile['social_style']}")

    labels = {
        "history": "where they have already been on this trip, and roughly in what order",
        "passports": "which passport or passports they travel on",
        "wishlist": "where they most want to go next",
        "preferences": "how they travel: interests, budget level, pace, solo or with people",
    }
    return {
        "missing": missing,
        "missing_text": "; ".join(labels[m] for m in missing) or "nothing",
        "captured_text": "; ".join(captured) or "nothing yet",
        "complete": not missing,
    }
