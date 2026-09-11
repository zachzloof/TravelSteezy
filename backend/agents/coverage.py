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

from typing import Any

from backend.agents.climate import CLIMATE_TABLE
from backend.rag.seed_data import KNOWN_DESTINATIONS

SUPPORTED: set[str] = set(CLIMATE_TABLE) | set(KNOWN_DESTINATIONS)


def classify(candidates: list[str]) -> dict[str, Any]:
    """Split candidates into those we hold data for and those we do not."""
    supported, unsupported = [], []
    for candidate in candidates:
        key = (candidate or "").strip().lower()
        if not key:
            continue
        (supported if key in SUPPORTED else unsupported).append(key)
    return {"supported": supported, "unsupported": unsupported}


def coverage_note(candidates: list[str]) -> str:
    """The block injected into the Decision-Weigher's prompt."""
    split = classify(candidates)
    if not split["unsupported"]:
        return "All candidate destinations are covered by the knowledge base."

    names = ", ".join(split["unsupported"])
    return (
        f"COVERAGE WARNING - NO VERIFIED DATA HELD FOR: {names}.\n"
        f"The knowledge base covers only: {', '.join(sorted(SUPPORTED))}.\n"
        f"For {names} you have no verified visa rules, no seasonal data, no route "
        f"costs and no budget figures. You MUST NOT state specifics for them, and "
        f"you MUST NOT rank any of them first. Give each a verdict of "
        f"'unknown', put the missing-data warning in its cons, and tell the "
        f"traveller plainly that this assistant does not cover that destination "
        f"and they should verify elsewhere."
    )


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
