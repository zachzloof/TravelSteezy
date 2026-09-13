"""Tests for discover_next_destinations' live-lookup fallback.

No API keys and no network: backend.rag.live_lookup is monkeypatched directly.
Mirrors tests/test_agent_tools.py's coverage of check_route's identical pattern.

    python -m pytest tests/test_discovery_tools.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents import discovery_tools  # noqa: E402


@pytest.fixture(autouse=True)
def _no_recorder():
    yield


def test_covered_town_never_calls_live_lookup(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("live_lookup.get_or_fetch should not run for a town the route graph knows")

    monkeypatch.setattr(discovery_tools.live_lookup, "get_or_fetch", _fail)

    result = discovery_tools.discover_next_destinations("Chiang Mai")

    assert result["found"] is True
    assert result["live_sourced"] is False


def test_uncovered_town_falls_back_to_live_lookup_and_uses_it(monkeypatch):
    """Regression test for the same bug class as check_seasonal_conditions: a
    town outside the curated route corpus (route_hits empty, no ROUTE_GRAPH
    entry) used to be a dead end - "say you have no data" - even though a live
    search can answer an ordinary "where do backpackers go next" question."""
    calls = []

    def _fake_get_or_fetch(destination, kind, question, top_k=2):
        calls.append({"destination": destination, "kind": kind})
        return [
            {
                "id": "live-routes-reykjavik",
                "text": "Common onward destinations after Reykjavik include the Golden Circle...",
                "metadata": {"content_type": "routes", "destination": "reykjavik"},
            }
        ]

    monkeypatch.setattr(discovery_tools.rag_store, "search", lambda *a, **k: [])
    monkeypatch.setattr(discovery_tools.live_lookup, "get_or_fetch", _fake_get_or_fetch)

    result = discovery_tools.discover_next_destinations("Reykjavik", interests="hiking")

    assert len(calls) == 1
    assert calls[0]["destination"] == "reykjavik"
    assert calls[0]["kind"] == "routes"

    assert result["found"] is True
    assert result["live_sourced"] is True
    assert "live-routes-reykjavik" in result["route_source_ids"]
    assert "reykjavik" in result["route_knowledge"].lower()


def test_uncovered_town_stays_honest_when_live_lookup_finds_nothing(monkeypatch):
    monkeypatch.setattr(discovery_tools.rag_store, "search", lambda *a, **k: [])
    monkeypatch.setattr(discovery_tools.live_lookup, "get_or_fetch", lambda *a, **k: [])

    result = discovery_tools.discover_next_destinations("Reykjavik")

    assert result["found"] is False
    assert result["live_sourced"] is False
    assert "no curated route knowledge" in result["note"].lower()


def test_missing_location_skips_live_lookup_entirely(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("live_lookup.get_or_fetch should not run with no location given")

    monkeypatch.setattr(discovery_tools.live_lookup, "get_or_fetch", _fail)

    result = discovery_tools.discover_next_destinations("")

    assert result["found"] is False
