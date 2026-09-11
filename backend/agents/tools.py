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


# --------------------------------------------------------------------------- #
# Logistics tools
# --------------------------------------------------------------------------- #
def check_route(origin: str, destination: str) -> dict[str, Any]:
    """Look up overland and flight options between two countries.

    Returns indicative journey time and cost for both, plus border-crossing notes.

    Args:
        origin: Country the traveller is currently in.
        destination: Candidate country they are considering next.
    """
    result = routes.lookup(origin, destination)
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
    hits = rag_store.search(query, namespace="visa", destinations=[destination], top_k=2)
    _record_retrieval("visa", hits)
    result = {
        "destination": destination,
        "nationality": nationality,
        "passages": rag_store.format_passages(hits),
        "source_ids": [h["id"] for h in hits if h.get("id") != "retrieval-error"],
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
    hits = rag_store.search(query, namespace="tips", destinations=[destination], top_k=3)
    _record_retrieval("tips", hits)
    result = {
        "destination": destination,
        "passages": rag_store.format_passages(hits),
        "source_ids": [h["id"] for h in hits if h.get("id") != "retrieval-error"],
    }
    _record("search_backpacker_tips", {"destination": destination, "topic": topic}, result)
    return result


def search_seasonal_notes(destination: str) -> dict[str, Any]:
    """Retrieve prose seasonal and safety notes for a destination from the RAG store.

    Complements check_seasonal_conditions, which returns the structured rating.

    Args:
        destination: Country to retrieve seasonal notes for.
    """
    hits = rag_store.search(
        f"seasonal weather monsoon safety in {destination}",
        namespace="seasonal",
        destinations=[destination],
        top_k=2,
    )
    _record_retrieval("seasonal", hits)
    result = {
        "destination": destination,
        "passages": rag_store.format_passages(hits),
        "source_ids": [h["id"] for h in hits if h.get("id") != "retrieval-error"],
    }
    _record("search_seasonal_notes", {"destination": destination}, result)
    return result
