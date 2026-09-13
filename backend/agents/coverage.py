"""Knowledge-coverage guard.

Shipped in response to eval case ``honesty-unknown-destination``, which the
baseline run failed: asked about Mongolia and Uzbekistan, the assistant invented
visa rules, budgets and a seasonal verdict, and ranked Mongolia first.

This is a deterministic Python check that runs BEFORE the Decision-Weigher, not
another line of prompt hoping the model behaves. Candidate destinations are
checked against the two knowledge sources the app actually has - the climate table
and the RAG corpus - and anything outside both is passed to the weigher as an
explicitly unsupported destination it is forbidden to rank first.
"""
from __future__ import annotations

from typing import Any, Iterable

from backend.agents.climate import CLIMATE_TABLE
from backend.rag.seed_data import KNOWN_DESTINATIONS

SUPPORTED: set[str] = set(CLIMATE_TABLE) | set(KNOWN_DESTINATIONS)


def resolve_to_covered(candidate: str) -> str | None:
    """Map a candidate to the covered country it belongs to, or None.

    Candidates arrive at town granularity ("Perhentian Islands, Malaysia") as well
    as country level. Treating a covered country's town as unsupported made the
    guard suppress a correct monsoon warning, so resolve through the city index
    and through any country named inside the string before giving up.
    """
    from backend.rag.route_data import KNOWN_CITIES

    key = (candidate or "").strip().lower()
    if not key:
        return None
    if key in SUPPORTED:
        return key
    if key in KNOWN_CITIES:
        return KNOWN_CITIES[key]

    # "perhentian islands, malaysia" or "bali, indonesia"
    for part in (p.strip() for p in key.replace("/", ",").split(",")):
        if part in SUPPORTED:
            return part
        if part in KNOWN_CITIES:
            return KNOWN_CITIES[part]
    for country in SUPPORTED:
        if country in key:
            return country
    for city, country in KNOWN_CITIES.items():
        if city in key:
            return country
    return None


def classify(candidates: list[str]) -> dict[str, Any]:
    """Split candidates into those we hold data for and those we do not."""
    supported, unsupported = [], []
    for candidate in candidates:
        key = (candidate or "").strip().lower()
        if not key:
            continue
        if resolve_to_covered(key):
            supported.append(key)
        else:
            unsupported.append(key)
    return {"supported": supported, "unsupported": unsupported}


def coverage_note(candidates: list[str], live_sourced: Iterable[str] | None = None) -> str:
    """The block injected into the specialist and Decision-Weigher prompts.

    ``live_sourced`` is the set of candidates for which a live web search +
    two-pass LLM verification actually succeeded THIS turn (see
    backend/rag/live_lookup.py). It is unknown - and always empty - when this
    is called for the specialists, since that call happens BEFORE any tool has
    run; it is known when called again for the Decision-Weigher, after the
    specialists' tool calls have completed (see runner.py::_run_comparison).

    A destination with no curated data but a genuine live-sourced hit this
    turn is treated as having real, sourced data - not curated, but not
    nothing - and gets an explicit permission to be used at full strength
    provided it is disclosed, rather than being swept into the same "you have
    literally nothing, do not invent a figure" bucket as a destination this
    turn found nothing for at all. See the live-sourced disclosure section of
    notes/03-rag-and-retrieval.md for why this split exists: without it, a
    successful live lookup is either indistinguishable from curated fact (the
    honesty bar silently drops) or gets fetched, verified, and then thrown
    away by this exact guard (the whole feature is pointless).
    """
    split = classify(candidates)
    if not split["unsupported"]:
        return "All candidate destinations are covered by the knowledge base."

    live_sourced_set = {str(d).strip().lower() for d in (live_sourced or [])}
    live_covered = [d for d in split["unsupported"] if d in live_sourced_set]
    genuinely_unknown = [d for d in split["unsupported"] if d not in live_sourced_set]

    blocks: list[str] = []
    if live_covered:
        names = ", ".join(live_covered)
        blocks.append(
            f"LIVE-SOURCED DATA FOUND FOR: {names}.\n"
            f"The curated knowledge base holds nothing for {names}, but a live web "
            f"search this turn found real information, and a second LLM pass "
            f"checked the drafted answer against those search results before it was "
            f"kept (see the specialist reports, marked 'live_sourced': true). Treat "
            f"this as genuinely usable, not as a lesser guess: state its figures, "
            f"rank {names} on its actual merits, and do NOT artificially hold it back "
            f"or default it to last place or 'unknown' just because it isn't curated. "
            f"The one requirement is disclosure - every specific for {names} must be "
            f"labeled live-sourced/unconfirmed (not part of the curated corpus) and "
            f"must include the source link the specialist reported."
        )
    if genuinely_unknown:
        names = ", ".join(genuinely_unknown)
        blocks.append(
            f"COVERAGE WARNING - NO DATA HELD FOR: {names}.\n"
            f"Neither the curated knowledge base nor a live search this turn found "
            f"anything for {names}. The knowledge base covers only: "
            f"{', '.join(sorted(SUPPORTED))}.\n"
            f"You MUST NOT rank any of them first, and you MUST give each a verdict of "
            f"'unknown' with the missing-data warning in its cons.\n"
            f"You MUST NOT state ANY figure for them - no dorm prices, no daily budget "
            f"ranges, no visa fees, no journey times, not even approximate or "
            f"'typically around' ones. Quoting a plausible-sounding price you cannot "
            f"source is the exact failure this rule exists to stop.\n"
            f"EXCEPTION: if your OWN tool call for one of {names} returns "
            f"'live_sourced': true, you may then report exactly what it returned, "
            f"clearly labeled unconfirmed/live-sourced with its source link - that is "
            f"the only case in which stating a figure for {names} is allowed.\n"
            f"Absent that, say plainly that this assistant does not cover {names} and "
            f"they should check a source that does."
        )
    return "\n\n".join(blocks)


def deadline_note(profile: dict[str, Any]) -> str:
    """The hard-deadline block injected into the Decision-Weigher's prompt.

    Shipped after eval case ``visa-deadline-surfaced`` failed: the deadline was
    present in the trip profile, but the weigher summarised it away and never told
    the traveller the date. Surfacing it as its own non-negotiable prompt block,
    computed in code, makes it much harder to drop.
    """
    date = (profile or {}).get("visa_deadline_date")
    if not date:
        return "No hard deadline recorded for this traveller."
    note = (profile or {}).get("visa_deadline_note") or "visa/permit expiry"
    return (
        f"HARD DEADLINE: {date} ({note}). "
        f"State this date explicitly in your reply, and say whether your top "
        f"recommendation fits inside it. Anything that cannot be done before "
        f"{date} must be flagged in visa_flag and cannot be ranked first."
    )


def route_note(current_location: str | None) -> str:
    """Guard for the discovery agent: do we hold onward-route data for here?

    Shipped after the eval case ``discovery-honest-about-unknown-origin`` failed:
    the tool correctly reported found:false for Reykjavik, and the agent invented
    Icelandic destinations anyway. Telling it in a non-negotiable prompt block,
    computed in code, is stronger than hoping it reads the tool result.
    """
    from backend.rag.route_data import ROUTE_GRAPH

    origin = (current_location or "").strip().lower()
    if not origin:
        return "Current location unknown - ask where they are before suggesting onward hops."
    if origin in ROUTE_GRAPH:
        hops = ", ".join(ROUTE_GRAPH[origin])
        return f"Route data IS held for {origin}. Known onward hops: {hops}."

    # The route corpus is keyed by TOWN. A traveller whose stored location is a
    # whole country is not outside coverage - we just cannot give hop-by-hop
    # detail until we know which town they are in.
    if origin in SUPPORTED:
        towns = sorted(t for t in ROUTE_GRAPH if t)
        return (
            f"{origin.title()} is covered at country level, but the onward-route "
            f"corpus is town-level and no town is recorded. Ask which town they "
            f"are in before giving hop-by-hop detail. Towns held: {', '.join(towns)}."
        )
    return (
        f"NO ROUTE DATA HELD FOR {origin.upper()}. The route corpus covers only "
        f"these origins: {', '.join(sorted(ROUTE_GRAPH))}. You MUST tell the "
        f"traveller plainly that this assistant does not cover where they are, and "
        f"you MUST NOT name onward destinations, journey times, prices or "
        f"attractions for {origin}. Suggest they ask again once they reach a "
        f"region it covers."
    )


# Overland neighbours within the covered corpus, used when we know the country
# but not the town, so "where next" still gets a real answer.
COUNTRY_NEIGHBOURS: dict[str, list[str]] = {
    "thailand": ["laos", "cambodia", "malaysia"],
    "laos": ["thailand", "vietnam", "cambodia"],
    "vietnam": ["cambodia", "laos", "thailand"],
    "cambodia": ["thailand", "vietnam", "laos"],
    "malaysia": ["thailand", "indonesia", "philippines"],
    "indonesia": ["malaysia", "philippines", "thailand"],
    "philippines": ["malaysia", "vietnam", "indonesia"],
    "nepal": ["india", "sri lanka", "thailand"],
    "sri lanka": ["india", "nepal", "thailand"],
    "india": ["nepal", "sri lanka", "bhutan"],
    "bhutan": ["india", "nepal"],
    # Mongolia and Myanmar are deliberately left without neighbours here: neither
    # has a realistic overland "nearby country" pairing within this corpus (and
    # Myanmar's land borders carry their own safety caveats - see the visa doc).
}


def nearby_country_options(origin: str, limit: int = 3) -> list[str]:
    """Plausible next countries from a covered country. Empty if uncovered."""
    return COUNTRY_NEIGHBOURS.get((origin or "").strip().lower(), [])[:limit]
