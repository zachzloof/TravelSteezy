"""ADK FunctionTools available to the specialist agents.

Every tool call is recorded in a per-turn ``ToolRecorder`` held in a ContextVar.
That recorder is what makes the eval assertions real: "did a RAG passage actually
get retrieved for this turn" is answered by inspecting recorded calls, not by
pattern-matching the model's prose (which would pass on plausible-sounding
parametric knowledge - exactly the failure mode we are testing for).
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import Any

from backend.agents import climate, routes
from backend.rag import live_lookup
from backend.rag import store as rag_store


# --------------------------------------------------------------------------- #
# per-turn recording
# --------------------------------------------------------------------------- #
@dataclass
class ToolRecorder:
    """Collects everything the tools did during one user turn."""

    calls: list[dict[str, Any]] = field(default_factory=list)
    retrieved: list[dict[str, Any]] = field(default_factory=list)

    def record(self, tool: str, args: dict[str, Any], result: Any) -> None:
        self.calls.append({"tool": tool, "args": args, "result": result})

    def record_retrieval(self, namespace: str, hits: list[dict[str, Any]]) -> None:
        for hit in hits:
            if hit.get("id") == "retrieval-error":
                continue
            self.retrieved.append(
                {
                    "id": hit["id"],
                    "namespace": namespace,
                    "score": round(float(hit.get("score", 0.0)), 4),
                    "destination": hit.get("metadata", {}).get("destination"),
                    "excerpt": (hit.get("text") or "")[:240],
                }
            )

    @property
    def tool_names(self) -> list[str]:
        return [c["tool"] for c in self.calls]

    @property
    def retrieved_ids(self) -> list[str]:
        return [r["id"] for r in self.retrieved]


_recorder: contextvars.ContextVar[ToolRecorder | None] = contextvars.ContextVar(
    "onward_tool_recorder", default=None
)


def set_recorder(recorder: ToolRecorder | None) -> contextvars.Token:
    return _recorder.set(recorder)


def reset_recorder(token: contextvars.Token) -> None:
    _recorder.reset(token)


def current_recorder() -> ToolRecorder | None:
    return _recorder.get()


def _record(tool: str, args: dict[str, Any], result: Any) -> None:
    rec = current_recorder()
    if rec is not None:
        rec.record(tool, args, result)


def _record_retrieval(namespace: str, hits: list[dict[str, Any]]) -> None:
    rec = current_recorder()
    if rec is not None:
        rec.record_retrieval(namespace, hits)


# --------------------------------------------------------------------------- #
# Weather / timing tool
# --------------------------------------------------------------------------- #
def check_seasonal_conditions(destination: str, month: str) -> dict[str, Any]:
    """Check whether a month is a good time to visit a destination.

    Returns a seasonal rating of 'good', 'mixed' or 'avoid' plus an explanatory
    note covering monsoon, heat, haze, typhoon and crowd considerations.

    Args:
        destination: Country name, e.g. "thailand", "nepal", "philippines".
        month: Month name or number, e.g. "July", "jul", "7".
    """
    result = climate.assess(destination, month)
    _record("check_seasonal_conditions", {"destination": destination, "month": month}, result)
    return result


def _search_with_live_fallback(
    query: str, namespace: str, destination: str, live_question: str, top_k: int
) -> list[dict[str, Any]]:
    """Curated search first. Only on a genuine empty result, try the live-lookup
    fallback - dormant unless TAVILY_API_KEY is configured, in which case it
    returns [] immediately (see backend/rag/live_lookup.py) and this behaves
    exactly as it always has: an empty scoped search stays empty.
    """
    hits = rag_store.search(query, namespace=namespace, destinations=[destination], top_k=top_k)
    _record_retrieval(namespace, hits)
    if hits:
        return hits
    live_hits = live_lookup.get_or_fetch(destination, namespace, live_question, top_k=top_k)
    _record_retrieval("unverified", live_hits)
    return live_hits


# --------------------------------------------------------------------------- #
# Logistics tools
# --------------------------------------------------------------------------- #
def check_route(origin: str, destination: str) -> dict[str, Any]:
    """Look up overland and flight options between two countries.

    Returns indicative journey time and cost for both, plus border-crossing notes.
    If neither is curated for this pair, falls back to a live web search - the
    same pattern as search_visa_rules - checked once against its sources and
    cached, so it is a fresh search only the first time this pair is asked
    about.

    Args:
        origin: Country the traveller is currently in.
        destination: Candidate country they are considering next.
    """
    result = routes.lookup(origin, destination)
    live_sourced = False
    if origin and destination and not result.get("known"):
        live_hits = live_lookup.get_or_fetch(
            destination,
            "routes",
            f"fastest and cheapest way to travel from {origin} to {destination}: "
            f"flight time and cost, and any overland option with its duration and cost",
            top_k=2,
        )
        _record_retrieval("unverified", live_hits)
        if live_hits:
            live_sourced = True
            result = {
                **result,
                "known": True,
                "passages": rag_store.format_passages(live_hits),
                "source_ids": [h["id"] for h in live_hits if h.get("id") != "retrieval-error"],
            }
    result["live_sourced"] = live_sourced
    _record("check_route", {"origin": origin, "destination": destination}, result)
    return result


def search_visa_rules(destination: str, nationality: str) -> dict[str, Any]:
    """Retrieve visa requirements for a passport holder entering a destination.

    Searches the visa namespace of the RAG store. ALWAYS call this before making
    any claim about visas; do not answer from memory.

    Args:
        destination: Country the traveller wants to enter.
        nationality: The traveller's passport nationality, e.g. "United Kingdom".
    """
    query = f"visa requirements for {nationality} passport holders entering {destination}"
    hits = _search_with_live_fallback(
        query, "visa", destination,
        f"{nationality} passport visa requirements to enter {destination}: cost, duration, "
        f"how to apply, processing/lead time",
        top_k=2,
    )
    result = {
        "destination": destination,
        "nationality": nationality,
        "passages": rag_store.format_passages(hits),
        "source_ids": [h["id"] for h in hits if h.get("id") != "retrieval-error"],
        "live_sourced": bool(hits) and hits[0].get("namespace") == "unverified",
    }
    _record("search_visa_rules", {"destination": destination, "nationality": nationality}, result)
    return result


# --------------------------------------------------------------------------- #
# Recommendations tool
# --------------------------------------------------------------------------- #
def search_backpacker_tips(destination: str, topic: str) -> dict[str, Any]:
    """Retrieve backpacker-specific things to do, budgets, routes and safety notes.

    Searches the tips namespace of the RAG store, which holds hostel, budget,
    overland-route and scam/safety content rather than package-tourist material.
    ALWAYS call this before recommending activities; do not answer from memory.

    Args:
        destination: Country to retrieve tips for.
        topic: What the traveller cares about, e.g. "diving and cheap islands".
    """
    query = f"backpacker things to do, daily budget and safety in {destination}: {topic}"
    hits = _search_with_live_fallback(
        query, "tips", destination,
        f"backpacker daily budget, things to do, and safety notes for {destination}: {topic}",
        top_k=3,
    )
    result = {
        "destination": destination,
        "passages": rag_store.format_passages(hits),
        "source_ids": [h["id"] for h in hits if h.get("id") != "retrieval-error"],
        "live_sourced": bool(hits) and hits[0].get("namespace") == "unverified",
    }
    _record("search_backpacker_tips", {"destination": destination, "topic": topic}, result)
    return result


def search_seasonal_notes(destination: str) -> dict[str, Any]:
    """Retrieve prose seasonal and safety notes for a destination from the RAG store.

    Complements check_seasonal_conditions, which returns the structured rating.

    Args:
        destination: Country to retrieve seasonal notes for.
    """
    hits = _search_with_live_fallback(
        f"seasonal weather monsoon safety in {destination}",
        "seasonal", destination,
        f"seasonal weather, monsoon or hazard season timing for {destination} for travellers",
        top_k=2,
    )
    result = {
        "destination": destination,
        "passages": rag_store.format_passages(hits),
        "source_ids": [h["id"] for h in hits if h.get("id") != "retrieval-error"],
        "live_sourced": bool(hits) and hits[0].get("namespace") == "unverified",
    }
    _record("search_seasonal_notes", {"destination": destination}, result)
    return result
