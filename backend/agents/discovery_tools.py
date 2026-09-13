"""Destination-discovery tools backed by the RAG store and the user's own memory.

``discover_next_destinations`` is the "where should I go next from here" tool. It
is deliberately RAG-first rather than Places-first: Places can tell you what is
near a coordinate, but it cannot tell you that people leaving Chiang Mai go to
Pai, or that Nong Khiaw is what Vang Vieng used to be. That reasoning lives in the
curated ``routes`` corpus plus accumulated ``experience`` feedback.

All tools record into the per-turn ToolRecorder so the eval suite can assert a
real retrieval happened rather than pattern-matching prose.
"""
from __future__ import annotations

from typing import Any

from backend.agents.tools import _record, _record_retrieval
from backend.rag import experience as experience_store
from backend.rag import live_lookup
from backend.rag import store as rag_store
from backend.rag.route_data import CITY_TO_COUNTRY, ROUTE_GRAPH


def discover_next_destinations(
    from_location: str, interests: str = "", max_options: int = 4
) -> dict[str, Any]:
    """Find where backpackers actually go next from a given town, and why.

    Searches the curated route corpus for onward hops from this location, then
    layers on any real traveller feedback recorded for those places. Use this
    before recommending a next destination - do not answer from memory.

    Args:
        from_location: The town or city the traveller is in now, e.g. "Chiang Mai".
        interests: What they care about, e.g. "trekking, cheap food, quiet".
        max_options: How many onward options to return.
    """
    args = {"from_location": from_location, "interests": interests}
    origin = (from_location or "").strip()
    if not origin:
        result = {"found": False, "note": "No current location given - ask where they are now."}
        _record("discover_next_destinations", args, result)
        return result

    origin_key = origin.lower()
    query = f"where to go next from {origin}"
    if interests:
        query += f" for someone into {interests}"

    route_hits = rag_store.search(
        query, namespace="routes", destinations=[origin_key], top_k=2
    )
    _record_retrieval("routes", route_hits)

    # Known onward hops from the route graph, used to scope the experience lookup
    # and to give the agent a concrete candidate list even if retrieval is thin.
    hops = ROUTE_GRAPH.get(origin_key, [])[:max_options]

    experience_hits: list[dict[str, Any]] = []
    if hops:
        experience_hits = experience_store.search_experience(
            f"traveller feedback on {', '.join(hops)}", destinations=hops, top_k=3
        )
        _record_retrieval("experience", experience_hits)

    live_sourced = False
    if not route_hits and not hops:
        # Same fallback pattern as check_route/search_visa_rules: the curated
        # route corpus is town-level and cannot list every town on earth, so a
        # miss here used to be a dead end - "say plainly you hold no data" -
        # even when a live search would have answered a perfectly ordinary
        # question like "where do backpackers go after X".
        live_hits = live_lookup.get_or_fetch(
            origin_key,
            "routes",
            f"common onward destinations backpackers travel to next after {origin}"
            + (f", for someone into {interests}" if interests else ""),
            top_k=2,
        )
        _record_retrieval("routes", live_hits)
        if live_hits:
            live_sourced = True
            route_hits = live_hits

    result = {
        "found": bool(route_hits or hops),
        "from_location": origin,
        "country": CITY_TO_COUNTRY.get(origin_key),
        "candidate_next_hops": hops,
        "route_knowledge": rag_store.format_passages(route_hits),
        "route_source_ids": [h["id"] for h in route_hits if h.get("id") != "retrieval-error"],
        "traveller_feedback": rag_store.format_passages(experience_hits)
        if experience_hits
        else "(no traveller feedback recorded yet for these places)",
        "feedback_source_ids": [
            h["id"] for h in experience_hits if h.get("id") != "retrieval-error"
        ],
        "live_sourced": live_sourced,
    }
    if not result["found"]:
        result["note"] = (
            f"No curated route knowledge held for {origin}. Say so rather than "
            f"inventing onward legs and journey times."
        )
    _record(
        "discover_next_destinations",
        args,
        {"hops": hops, "route_hits": len(route_hits), "experience_hits": len(experience_hits)},
    )
    return result


def get_traveller_feedback(location: str) -> dict[str, Any]:
    """Retrieve what real travellers said about a place after visiting it.

    This is accumulated user feedback, not curated content. Present it as other
    backpackers' opinions, anonymously, never as established fact.

    Args:
        location: Town or city to look up feedback for.
    """
    args = {"location": location}
    location = (location or "").strip()
    if not location:
        return {"found": False, "note": "no location given"}

    hits = experience_store.search_experience(
        f"traveller feedback and reviews for {location}",
        destinations=[location.lower()],
        top_k=4,
    )
    _record_retrieval("experience", hits)
    result = {
        "found": bool(hits),
        "location": location,
        "feedback": rag_store.format_passages(hits)
        if hits
        else "(no traveller feedback recorded for this place yet)",
        "source_ids": [h["id"] for h in hits if h.get("id") != "retrieval-error"],
    }
    _record("get_traveller_feedback", args, {"hits": len(hits)})
    return result
