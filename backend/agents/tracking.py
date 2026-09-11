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
from datetime import date
from typing import Any

from backend.memory import store, travel
from backend.rag import experience as experience_store
from backend.rag.route_data import KNOWN_CITIES
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


def apply_tracking(user_id: int, parse: dict[str, Any]) -> list[dict[str, Any]]:
    """Apply every structured travel write implied by one parsed turn.

    Returns a list of write records for the UI's "just remembered" panel.
    """
    writes: list[dict[str, Any]] = []

    # ---- visits: append to the route, promote off the wishlist ---------------
    for visit in _entries(parse, "visits"):
        location = str(visit["location"]).strip()
        country = _country_for(location, visit.get("country"))
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
        is_country = (
            str(departure.get("location_type") or "").lower() == "country"
            or location.strip().lower() in SUPPORTED_COUNTRIES
        )
        if is_country:
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
