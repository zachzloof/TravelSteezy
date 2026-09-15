"""Live trip tracking: turning a parsed turn into structured memory writes.

This is the "when you write" path for the extension, and it is deliberately
plain Python called by the orchestrator rather than anything the model does to
the database itself. The model's job is to say what it heard; this module decides
what that means for stored state.

Three things happen here:

  * **visit detection** - a place the traveller says they are at is appended to
    ``travel_history`` and, if it was on the wishlist, promoted out of it
  * **wishlist maintenance** - adds and explicit removals
  * **reviews** - a rating or opinion is attached to the history row and pushed
    into the RAG ``experience`` namespace so future suggestions improve

A safety rule runs through all of it: we only act on places we can recognise, and
a visit is never inferred from the traveller merely *asking about* somewhere.
That distinction is enforced in the parser prompt and re-checked here.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

from backend.memory import store, travel
from backend.rag import experience as experience_store
from backend.rag.route_data import KNOWN_CITIES, resolve_country
from backend.rag.seed_data import KNOWN_DESTINATIONS

SUPPORTED_COUNTRIES = set(KNOWN_DESTINATIONS)

logger = logging.getLogger(__name__)


def _entries(parse: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = parse.get(key) or []
    return [item for item in value if isinstance(item, dict) and item.get("location")]


def _country_for(location: str, given: str | None) -> str | None:
    if given:
        return given
    return KNOWN_CITIES.get((location or "").strip().lower())


def _normalise(text: str) -> str:
    """Lowercase and collapse punctuation/whitespace, for substring matching.

    Keeps unicode word characters rather than stripping to ASCII: a traveller
    typing "Malmö" or a Thai place name in Thai script should still match
    itself, and both sides of the comparison go through this same function, so
    the only thing that matters is that it is consistent.
    """
    return re.sub(r"\W+", " ", (text or "").lower(), flags=re.UNICODE).strip()


def mentioned_in(location: str, message: str) -> bool:
    """Did the traveller actually name this place in THIS message?

    THE GROUNDING RULE. Reconstructed from bug report #3's Langfuse traces
    (2026-09-14): the turn parser emits a `visits` entry on almost every turn,
    echoing whatever it believes the current location to be, even when the
    message names nowhere at all -

        "what things should i do? give me some ideas"   -> visits: [Pai]
        "any parties?"                                  -> visits: [Pai]
        "where should i go next"                        -> visits: [Chiang Mai]

    That was invisible while it echoed the right place. On the last one it
    echoed a STALE town out of the route history - thirteen seconds after the
    traveller had said "i'm in thailand now" - and `apply_tracking` wrote it
    over their own statement as though they had said it. The next message was
    "i never said i was in chiang mai?". They hadn't. The parser had, and the
    shape it emitted (city, Chiang Mai, arrival_date today) is the literal
    example from its own prompt.

    A location the traveller did not type cannot become a visit or a departure.
    This is the same principle as every other guard here - a cheap
    deterministic check beats trusting the extraction - applied to the one
    input that had none: which place the model claims was named.

    Compound strings ("Bali, Indonesia") match on any part, so a parser that
    helpfully expands a town into "town, country" still lands. Parts shorter
    than three characters are ignored, since they match almost anything.
    """
    if not message:
        # No message to check against (a caller that predates this rule, e.g.
        # onboarding). Fail open rather than silently dropping every write.
        return True
    haystack = f" {_normalise(message)} "
    candidates = [location] + [p for p in re.split(r"[,/]", location or "")]
    for candidate in candidates:
        needle = _normalise(candidate)
        if len(needle) >= 3 and f" {needle} " in haystack:
            return True
    return False


def _stated_presence(parse: dict[str, Any], message: str) -> set[str]:
    """Places this turn says the traveller IS in, as country keys where known.

    Used to drop a contradictory departure: at 16:54:38 in the same report the
    parser read "i said i was in thailand? i want to change country" as both
    `current_location: Thailand` AND a departure from Thailand dated that day,
    and the departure won - wiping the location a sentence that explicitly
    stated it had just set. A statement of presence beats an inferred
    departure, every time.
    """
    here: set[str] = set()
    for visit in _entries(parse, "visits"):
        location = str(visit["location"]).strip()
        if mentioned_in(location, message):
            here.add(location.lower())
            here.add(resolve_country(location) or location.lower())
    stated = str((parse.get("profile_updates") or {}).get("current_location") or "").strip()
    if stated and mentioned_in(stated, message):
        here.add(stated.lower())
        here.add(resolve_country(stated) or stated.lower())
    return {h for h in here if h}


def _is_country(location: str, location_type: str | None) -> bool:
    """Is this entry a whole country rather than a town?

    Trusts the parser's ``location_type`` when it says so, and re-checks the
    name against the covered-country list either way - the parser labels
    country-level mentions "city" often enough that the label alone is not a
    safe test.
    """
    return (
        str(location_type or "").strip().lower() == "country"
        or (location or "").strip().lower() in SUPPORTED_COUNTRIES
    )


def apply_tracking(
    user_id: int, parse: dict[str, Any], message: str = ""
) -> list[dict[str, Any]]:
    """Apply every structured travel write implied by one parsed turn.

    ``message`` is the traveller's raw text, used to ground place-level writes
    in what they actually said - see ``mentioned_in``. It defaults to empty for
    callers with no message to check against, which fails open.

    Returns a list of write records for the UI's "just remembered" panel.
    """
    writes: list[dict[str, Any]] = []
    present_in = _stated_presence(parse, message)

    # ---- visits: append to the route, promote off the wishlist ---------------
    for visit in _entries(parse, "visits"):
        location = str(visit["location"]).strip()
        if not mentioned_in(location, message):
            logger.info(
                "dropping ungrounded visit %r for user %s - not named in the message",
                location, user_id,
            )
            continue
        country = _country_for(location, visit.get("country"))

        # "I'm in Thailand now" when we already have them in Pai is a
        # CONFIRMATION, not a move. Treating it as a fresh visit appended
        # "Thailand" to a town-level route ("Bangkok -> Chiang Mai -> Pai ->
        # Thailand", as though the country were the next stop) and overwrote
        # the precise stored town with the vaguer country - which then took
        # "where next" off the town-level path entirely. Reported in bug report
        # #3, 2026-09-14. A country-level visit that names a DIFFERENT country
        # from the one they are in is a real move and still lands normally
        # (eval case memory-writes-departure: "I left Laos yesterday and I'm in
        # Thailand now").
        if _is_country(location, visit.get("location_type")):
            current = store.get_profile(user_id).get("current_location") or ""
            if current and resolve_country(current) == location.strip().lower():
                travel.touch_location_mention(user_id, current)
                continue

        result = travel.add_travel_history(
            user_id,
            location=location,
            location_type=str(visit.get("location_type") or "city"),
            country=country,
            arrival_date=visit.get("arrival_date") or date.today().isoformat(),
            source="tracked",
        )
        if not result.get("ok"):
            continue

        promoted = travel.resolve_wishlist(user_id, location, status="visited")
        # Mentioning a place you are already known to be in is not a memory write.
        # Only report something the traveller would recognise as newly remembered.
        if result.get("created") or result.get("changed") or promoted:
            writes.append(
                {
                    "operation": "track_visit",
                    "payload": {
                        "location": location,
                        "new_entry": result.get("created", False),
                        "promoted_from_wishlist": promoted,
                    },
                    "source": "agent",
                }
            )

        # Being somewhere makes it the current location.
        store.update_profile(user_id, {"current_location": location}, source="agent")

        # An accepted suggestion is a signal worth keeping.
        if promoted:
            travel.record_recommendation_feedback(
                user_id, location, "accepted", reason="visited after being on the wishlist"
            )
            experience_store.ingest_outcome(user_id, location, "accepted")

    # ---- wishlist adds ------------------------------------------------------
    for want in _entries(parse, "wishlist_adds"):
        location = str(want["location"]).strip()
        priority = want.get("priority")
        try:
            priority = int(priority) if priority is not None else 2
        except (TypeError, ValueError):
            priority = 2
        result = travel.add_wishlist(
            user_id,
            location=location,
            location_type=str(want.get("location_type") or "city"),
            country=_country_for(location, want.get("country")),
            priority=priority,
            source="agent",
        )
        if result.get("ok"):
            writes.append(
                {
                    "operation": "add_wishlist",
                    "payload": {"location": location, "priority": priority},
                    "source": "agent",
                }
            )

    # ---- wishlist removals --------------------------------------------------
    for removal in parse.get("wishlist_removes") or []:
        location = str(removal).strip() if not isinstance(removal, dict) else str(
            removal.get("location") or ""
        ).strip()
        if not location:
            continue
        if travel.resolve_wishlist(user_id, location, status="dropped"):
            travel.record_recommendation_feedback(user_id, location, "rejected")
            experience_store.ingest_outcome(user_id, location, "rejected")
            writes.append(
                {
                    "operation": "drop_wishlist",
                    "payload": {"location": location},
                    "source": "agent",
                }
            )

    # ---- departures ---------------------------------------------------------
    for departure in _entries(parse, "departures"):
        location = str(departure["location"]).strip()
        departure_date = departure.get("departure_date") or date.today().isoformat()

        if not mentioned_in(location, message):
            logger.info(
                "dropping ungrounded departure %r for user %s - not named in the message",
                location, user_id,
            )
            continue
        # A place they have just said they are IN cannot also be one they have
        # left this turn. "i said i was in thailand? i want to change country"
        # was parsed as both, and the departure won - clearing the location the
        # same sentence had set (bug report #3).
        if present_in & {location.lower(), resolve_country(location) or location.lower()}:
            logger.info(
                "dropping departure %r for user %s - the same turn states they are there",
                location, user_id,
            )
            continue

        # Make sure the place is in the route before we close it out - people
        # often only mention somewhere when they are leaving it.
        travel.add_travel_history(
            user_id,
            location=location,
            location_type=str(departure.get("location_type") or "city"),
            country=_country_for(location, departure.get("country")),
            departure_date=departure_date,
            source="tracked",
        )
        # Only a COUNTRY departure belongs in the country-level log. Passing a
        # town name here wrote "Pai" into visited_history as though it were a
        # country, and leaving Pai does not mean leaving Thailand.
        if _is_country(location, departure.get("location_type")):
            store.log_departure(
                user_id, country=location, departure_date=departure_date, source="agent"
            )
        else:
            # Town-level: archive_country clears current_location when it matches,
            # which is the same "stop treating this as active context" rule. Note
            # update_profile cannot do this - it drops empty values by design.
            store.archive_country(user_id, location, source="agent")
        writes.append(
            {
                "operation": "log_departure",
                "payload": {"location": location, "departure_date": departure_date},
                "source": "agent",
            }
        )

    # ---- reviews ------------------------------------------------------------
    for review in _entries(parse, "reviews"):
        location = str(review["location"]).strip()
        rating = review.get("rating")
        notes = review.get("notes")

        # A review implies they went, so make sure there is a row to attach to.
        travel.add_travel_history(
            user_id, location=location,
            country=_country_for(location, review.get("country")), source="tracked",
        )
        result = travel.save_review(
            user_id, location=location, rating=rating, review_notes=notes, source="agent"
        )
        if result.get("ok"):
            experience_store.ingest_review(user_id, location, rating, notes)
            writes.append(
                {
                    "operation": "save_review",
                    "payload": {"location": location, "rating": rating},
                    "source": "agent",
                }
            )

    # ---- keep the review timer honest ---------------------------------------
    for group in ("visits", "reviews"):
        for item in _entries(parse, group):
            travel.touch_location_mention(user_id, str(item["location"]))
    if parse.get("focus_location"):
        travel.touch_location_mention(user_id, str(parse["focus_location"]))

    return writes


def review_prompt_for(user_id: int, exclude: list[str] | None = None) -> dict[str, Any] | None:
    """The next place we should ask the traveller to review, if any.

    Returns None when nothing is due. The caller appends the question to its reply
    rather than hijacking the turn, so the traveller still gets what they asked for.
    """
    excluded = {(e or "").strip().lower() for e in (exclude or [])}
    for candidate in travel.get_pending_reviews(user_id):
        location = candidate["location"]
        if location.strip().lower() in excluded:
            continue
        # Do not nag: one prompt per place until they engage with it.
        if candidate.get("review_prompted_at"):
            continue
        travel.mark_review_prompted(user_id, location)
        return {
            "location": location,
            "country": candidate.get("country"),
            "departure_date": candidate.get("departure_date"),
        }
    return None


def render_review_prompt(prompt: dict[str, Any]) -> str:
    """The one-line nudge appended to a reply."""
    return (
        f"\n\nBy the way - how was {prompt['location']}? "
        f"Give it a score out of 5 and a line on what it was actually like, and I'll "
        f"remember it for next time (and it helps other travellers too)."
    )
