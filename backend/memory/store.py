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
#
# trip_start_date/trip_end_date/visa_deadline_date/visa_deadline_note were
# removed from this list deliberately: trip dates added little (a backpacker's
# "end date" is usually a soft flight-out guess, not a hard fact) and the turn
# parser kept inventing values for them from vague mentions of duration, and the
# "hard deadline" feature built on visa_deadline turned out to nag rather than
# help. The columns still exist in the database for any account that has old
# data in them, but nothing in the app reads, writes, or displays them any more.
PROFILE_FIELDS: tuple[str, ...] = (
    "nationality",
    "budget_band",
    "travel_style",
    "climate_preference",
    "current_location",
    "interests",
)

# --------------------------------------------------------------------------- #
# The three preference scales.
#
# Each is an ORDERED five-point scale, not a set: the order is the meaning, and
# the ranking code and the prompts both rely on "one step apart" being a smaller
# difference than "four steps apart". Three points was not enough to be useful -
# "hot" covered both a Thai beach in March and a Nepali hill town in October, and
# a traveller on GBP 15/day and one on GBP 45/day both had to answer "shoestring".
#
# Values are normalised in Python, never trusted from the model, because the
# extractor sees free text: "dirt cheap", "flashpacker", "as cold as possible".
BUDGET_BANDS: tuple[str, ...] = ("shoestring", "budget", "mid", "comfortable", "luxury")
TRAVEL_STYLES: tuple[str, ...] = ("very_slow", "slow", "balanced", "fast", "very_fast")
CLIMATE_PREFS: tuple[str, ...] = ("cold", "cool", "temperate", "warm", "hot")

# Human labels, used by the prompt renderer so the agents read something
# meaningful rather than a bare enum token.
BAND_LABELS: dict[str, str] = {
    "shoestring": "shoestring (dorms, street food, night buses)",
    "budget": "budget (cheap privates sometimes, still counting)",
    "mid": "mid-range (private rooms, occasional flights)",
    "comfortable": "comfortable (good privates, comfort over cost)",
    "luxury": "luxury (cost is not the constraint)",
    "very_slow": "very slow (weeks in one place)",
    "slow": "slow (several nights per stop)",
    "balanced": "balanced",
    "fast": "fast (a stop every night or two)",
    "very_fast": "very fast (covering ground, minimal stops)",
    "cold": "cold",
    "cool": "cool",
    "temperate": "temperate",
    "warm": "warm",
    "hot": "hot",
}

# Free-text synonyms mapped onto the canonical scales. This is the whole reason
# onboarding can accept plain English: the model is asked only to echo the phrase
# it heard into a field, and Python decides which band that phrase is.
_BAND_SYNONYMS: dict[str, dict[str, str]] = {
    "budget_band": {
        "shoestring": "shoestring", "dirt cheap": "shoestring", "cheap": "shoestring",
        "backpacker": "shoestring", "broke": "shoestring", "very low": "shoestring",
        "low": "budget", "budget": "budget", "tight": "budget", "frugal": "budget",
        "mid": "mid", "mid-range": "mid", "midrange": "mid", "medium": "mid",
        "moderate": "mid", "average": "mid", "flashpacker": "mid",
        "comfortable": "comfortable", "comfy": "comfortable", "high": "comfortable",
        "generous": "comfortable",
        "luxury": "luxury", "luxurious": "luxury", "splurge": "luxury",
        "no limit": "luxury", "unlimited": "luxury",
    },
    "travel_style": {
        "very slow": "very_slow", "very_slow": "very_slow", "glacial": "very_slow",
        "slomad": "very_slow", "base": "very_slow", "staying put": "very_slow",
        "slow": "slow", "relaxed": "slow", "chill": "slow", "leisurely": "slow",
        "balanced": "balanced", "moderate": "balanced", "medium": "balanced",
        "mixed": "balanced", "normal": "balanced",
        "fast": "fast", "quick": "fast", "busy": "fast", "packed": "fast",
        "very fast": "very_fast", "very_fast": "very_fast", "whirlwind": "very_fast",
        "rushed": "very_fast", "hectic": "very_fast", "whistle-stop": "very_fast",
    },
    "climate_preference": {
        "cold": "cold", "freezing": "cold", "snow": "cold", "snowy": "cold",
        "alpine": "cold", "very cold": "cold",
        "cool": "cool", "chilly": "cool", "crisp": "cool", "mild cold": "cool",
        "temperate": "temperate", "mild": "temperate", "moderate": "temperate",
        "spring": "temperate",
        "warm": "warm", "pleasant": "warm", "balmy": "warm",
        "hot": "hot", "tropical": "hot", "very hot": "hot", "sweltering": "hot",
        "humid": "hot", "beach": "hot", "heat": "hot", "sun": "hot",
    },
}

# A stored value that used to be valid must keep resolving to something sensible,
# otherwise deploying this would quietly blank an existing traveller's profile.
_LEGACY_VALUES: dict[str, dict[str, str]] = {
    "climate_preference": {"no_preference": ""},
}

# Words that flip the meaning of whatever band keyword sits beside them.
_NEGATORS: tuple[str, ...] = (
    " not ", " no ", " never ", " hate ", " hates ", " avoid ", " avoids ",
    " cant ", " can t ", " cannot ", " dont ", " don t ", " doesnt ", " isnt ",
    " melt ", " melts ", " wilt ", " wilts ", " struggle ", " struggles ",
    " suffer ", " suffers ", " rather ", " less ", " away from ", " too ",
    " sick of ", " fed up ", " enough of ",
)

# Where a negated keyword lands. One step in from the far end rather than the
# extreme: "not hot" is a request to be cooler, not a request to be freezing.
# Budget and pace are deliberately absent - "not cheap" genuinely could mean any
# of four bands, and storing a guess is worse than storing nothing.
_OPPOSITE: dict[str, dict[str, str]] = {
    "climate_preference": {
        "hot": "cool", "warm": "cool", "temperate": "", "cool": "warm", "cold": "warm",
    },
}

ENUM_FIELDS: dict[str, tuple[str, ...]] = {
    "budget_band": BUDGET_BANDS,
    "travel_style": TRAVEL_STYLES,
    "climate_preference": CLIMATE_PREFS,
}


def _flatten(text: str) -> str:
    """Lower-case, with hyphens and underscores flattened to spaces."""
    return str(text or "").strip().lower().replace("-", " ").replace("_", " ")


# The lookup table has to be flattened the same way the input is, or a key
# containing a hyphen can never match: "whistle-stop" arrives as "whistle stop"
# and missed its own entry entirely. Caught by a unit test, not in review.
_LOOKUP: dict[str, dict[str, str]] = {
    field: {_flatten(phrase): band for phrase, band in synonyms.items()}
    for field, synonyms in _BAND_SYNONYMS.items()
}


def normalise_band(field: str, value: Any) -> str | None:
    """Map free text onto one of the five canonical points of a scale.

    Returns None when the field is not one of the three scales (the caller should
    then keep the value as-is), and "" when the text was recognised as an explicit
    "no preference", which clears rather than sets the field.
    """
    if field not in ENUM_FIELDS:
        return None
    text = _flatten(value)
    if not text:
        return ""
    canonical = text.replace(" ", "_")
    if canonical in ENUM_FIELDS[field]:
        return canonical
    legacy = _LEGACY_VALUES.get(field, {})
    if canonical in legacy:
        return legacy[canonical]
    synonyms = _LOOKUP[field]
    if text in synonyms:
        return synonyms[text]

    # Longest phrase first, so "very slow" wins over "slow" inside the same string.
    for phrase in sorted(synonyms, key=len, reverse=True):
        if phrase not in text:
            continue
        # "I hate the heat" and "I love the heat" contain the same keyword and
        # mean opposite things. Substring matching alone gets this exactly
        # backwards, and it is the single most likely way onboarding would store
        # a preference that is the reverse of what the traveller said - so a
        # negated match is never taken at face value.
        remainder = text.replace(phrase, " ")
        if any(neg in f" {remainder} " for neg in _NEGATORS):
            return _OPPOSITE.get(field, {}).get(synonyms[phrase], "")
        return synonyms[phrase]

    if any(word in text for word in ("no preference", "any", "whatever", "dont mind", "don t mind")):
        return ""
    return ""


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


def get_raw_profile_row(user_id: int) -> dict[str, Any]:
    """Every column in trip_profile, unfiltered - including deprecated ones.

    get_profile() only returns PROFILE_FIELDS, which is deliberately curated for
    what agents and the ordinary UI should see. The memory debug page's whole
    purpose is different: showing precisely what is in the database, including
    columns nothing else reads any more (trip_start_date/trip_end_date) so a
    developer can confirm an old value really is inert rather than assuming it.
    """
    ensure_profile(user_id)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM trip_profile WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else {}


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
    profile["social_style"] = row["social_style"] if row is not None else None
    # Passports live in their own table but travel with the profile everywhere,
    # so no caller has to remember to fetch them separately.
    profile["passports"] = get_passports(user_id)
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
        if key in ENUM_FIELDS:
            # An unrecognised band is dropped rather than stored raw. Storing
            # "pretty cheap I guess" in climate_preference would render straight
            # into every agent prompt as though it were a real preference.
            banded = normalise_band(key, text)
            if not banded:
                continue
            text = banded
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


# --------------------------------------------------------------------------- #
# passports
# --------------------------------------------------------------------------- #
def get_passports(user_id: int) -> list[str]:
    """Every passport this traveller holds, primary first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT country FROM passports WHERE user_id = ? "
            "ORDER BY is_primary DESC, id ASC",
            (user_id,),
        ).fetchall()
    return [r["country"] for r in rows]


def set_passports(
    user_id: int, passports: list[str], source: str = "user_edit"
) -> list[str]:
    """Replace the passport list. The first entry becomes the primary.

    ``trip_profile.nationality`` is kept in sync with the primary passport so
    that every prompt, tool and eval written against ``nationality`` keeps
    working unchanged - a single-passport traveller sees no difference at all.
    """
    cleaned: list[str] = []
    for entry in passports or []:
        text = str(entry or "").strip()
        if text and text.lower() not in {c.lower() for c in cleaned}:
            cleaned.append(text)

    ensure_profile(user_id)
    with get_conn() as conn:
        conn.execute("DELETE FROM passports WHERE user_id = ?", (user_id,))
        for index, country in enumerate(cleaned):
            conn.execute(
                "INSERT INTO passports (user_id, country, is_primary) VALUES (?,?,?)",
                (user_id, country, 1 if index == 0 else 0),
            )
        conn.execute(
            "UPDATE trip_profile SET nationality = ?, updated_at = datetime('now') "
            "WHERE user_id = ?",
            (cleaned[0] if cleaned else None, user_id),
        )
        _record_write(conn, user_id, "set_passports", {"passports": cleaned}, source)
    return cleaned


def add_passport(user_id: int, country: str, source: str = "user_edit") -> list[str]:
    """Add one passport, keeping the existing primary. Idempotent."""
    country = (country or "").strip()
    if not country:
        return get_passports(user_id)
    existing = get_passports(user_id)
    if country.lower() in {c.lower() for c in existing}:
        return existing
    return set_passports(user_id, existing + [country], source=source)


def remove_passport(user_id: int, country: str, source: str = "user_edit") -> list[str]:
    """Drop one passport. If the primary is removed, the next one takes over."""
    country = (country or "").strip().lower()
    existing = get_passports(user_id)
    remaining = [c for c in existing if c.lower() != country]
    if remaining == existing:
        return existing
    return set_passports(user_id, remaining, source=source)


def sync_passports_from_nationality(user_id: int) -> list[str]:
    """Backfill the passport table for an account that predates it.

    Called on read paths that need passports, so an existing traveller whose
    profile only has ``nationality`` shows one passport rather than none.
    """
    existing = get_passports(user_id)
    if existing:
        return existing
    with get_conn() as conn:
        row = conn.execute(
            "SELECT nationality FROM trip_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
    nationality = (row["nationality"] if row else None) or ""
    if not nationality.strip():
        return []
    return set_passports(user_id, [nationality.strip()], source="migrated")


def clear_profile_fields(
    user_id: int, fields: list[str], source: str = "user_edit"
) -> dict[str, Any]:
    """Blank named profile fields.

    ``update_profile`` deliberately drops empty values - a PATCH from a partial
    form must not wipe what it did not show - which left no way at all to unset
    something. That was fine while the UI was dropdowns with a "not set" option,
    but the five-point scales clear by tapping the selected point again, and a
    control that says it clears a field has to actually clear it. So clearing is
    its own explicit operation rather than a special case inside the writer.
    """
    clean = [f for f in (fields or []) if f in PROFILE_FIELDS]
    if not clean:
        return get_profile(user_id)
    ensure_profile(user_id)
    assignments = ", ".join(f"{f} = NULL" for f in clean)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE trip_profile SET {assignments}, updated_at = datetime('now') "
            "WHERE user_id = ?",
            (user_id,),
        )
        _record_write(conn, user_id, "clear_profile_fields", {"fields": clean}, source)
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
    """If the archived place is the profile's ``current_location``, clear it.

    The country stops being live context but stays readable in ``visited_history``,
    so a later re-entry or re-entry-visa question can still reach it.
    Returns True when active context actually changed.

    A COUNTRY also clears a town inside it: the comparison used to be a raw
    string match, so leaving Thailand while the stored location was "Pai" left
    the app believing the traveller was still in Pai, days after they had gone
    (bug report #3, 2026-09-14). A TOWN still only clears itself - resolving
    both sides to a country would make leaving Chiang Mai wrongly clear a
    stored location of Pai. This is the ``resolve_country`` rule from
    notes/05-guards-and-prompting.md applied to the one place that still
    compared destination strings directly.
    """
    from backend.rag.route_data import COUNTRIES, resolve_country

    profile = get_profile(user_id)
    current = (profile.get("current_location") or "").strip().lower()
    archived = country.strip().lower()
    if not current:
        return False
    if current != archived:
        archived_is_country = archived in COUNTRIES
        if not archived_is_country or resolve_country(current) != archived:
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


# Every table that holds this-account-only memory. Kept as one list so
# forget_account_memory cannot silently miss one when a new table is added -
# this is precisely the bug being fixed here: the function wiped the base-app
# tables only, so "Forget everything" in My Preferences left the entire route,
# wishlist, ratings, interests and onboarding status fully intact. A user who
# read "erase everything Travel Steezy remembers about your trip" and clicked
# it would have found almost all of it still there.
_EXTENSION_TABLES: tuple[str, ...] = (
    "travel_history", "wishlist", "user_interests",
    "recommendation_feedback", "onboarding_state",
    # The audit trail is itself account data (locations, ratings, nationality
    # mentions), so a genuine "forget everything" clears it too. It is wiped
    # BEFORE _record_write below adds the one entry that should survive: the
    # record that a forget happened at all.
    "memory_writes",
)


def forget_account_memory(user_id: int) -> None:
    """Hard reset, used by the eval harness and by an explicit user request.

    Wipes profile, history and scrollback for ONE account without touching the
    account itself or any other account's data.
    """
    with get_conn() as conn:
        conn.execute("DELETE FROM conversation_turns WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM visited_history WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM trip_profile WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM passports WHERE user_id = ?", (user_id,))
        for table in _EXTENSION_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
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
        if value and key in ENUM_FIELDS:
            value = BAND_LABELS.get(str(value), value)
        return f"- {label}: {value}" if value else f"- {label}: (unknown)"

    passports = profile.get("passports") or []
    if len(passports) > 1:
        # Spelled out rather than left implicit: a dual national gets a different
        # and usually better answer, and the agent has to be told it may choose.
        passport_line = (
            f"- Passports held: {', '.join(passports)} "
            f"(primary {passports[0]}). They may enter on WHICHEVER of these gives "
            f"the easier entry - check the destination against each passport and say "
            f"which one you assumed."
        )
    elif passports:
        passport_line = f"- Passport / nationality: {passports[0]}"
    else:
        passport_line = line("nationality", "Passport / nationality")

    lines = [
        passport_line,
        line("current_location", "Currently in"),
        line("budget_band", "Budget band"),
        line("travel_style", "Travel pace"),
        line("climate_preference", "Climate preference"),
        line("social_style", "Travelling"),
        # Interests are NOT rendered here even though trip_profile.interests
        # mirrors them: travel_block (travel.format_travel_for_prompt, appended
        # right after this block via MEMORY_BLOCK) renders the same data from
        # the structured, tiered source - key interests first, explicitly
        # marked. Rendering both used to show every interest twice, and only
        # travel_block's version carries the KEY framing.
    ]
    if visited:
        been = ", ".join(
            v["country"] + (f" (left {v['departure_date']})" if v.get("departure_date") else "")
            for v in visited[:10]
        )
        lines.append(f"- Already visited this trip: {been}")
    return "\n".join(lines)
