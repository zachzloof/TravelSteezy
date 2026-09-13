"""Tests for check_route's live-lookup fallback.

No API keys and no network: backend.rag.live_lookup is monkeypatched directly,
so these exercise the plumbing (when the fallback fires, what it returns, that
it never overwrites a curated hit) without depending on Tavily/OpenAI being
configured. The real live search + verification pipeline is covered by the
evals suite (see evals/cases.jsonl, "route-live-lookup-uncurated-pair").

    python -m pytest tests/test_agent_tools.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents import tools  # noqa: E402


@pytest.fixture(autouse=True)
def _no_recorder():
    """check_route calls _record/_record_retrieval; both are no-ops without a
    recorder set, which is exactly the state these tests want."""
    yield


def test_curated_pair_never_calls_live_lookup(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("live_lookup.get_or_fetch should not be called for a curated pair")

    monkeypatch.setattr(tools.live_lookup, "get_or_fetch", _fail)

    result = tools.check_route("thailand", "cambodia")

    assert result["known"] is True
    assert result["live_sourced"] is False
    assert "overland_hours" in result


def test_uncurated_pair_falls_back_to_live_lookup_and_discloses_it(monkeypatch):
    calls = []

    def _fake_get_or_fetch(destination, kind, question, top_k=2):
        calls.append({"destination": destination, "kind": kind, "question": question})
        return [
            {
                "id": "unverified-routes-philippines",
                "text": "[UNVERIFIED - live-sourced 2026-09-13] Flights from India to the "
                "Philippines run via Singapore or Bangkok, roughly 6-8 hours total.",
                "metadata": {
                    "content_type": "unverified",
                    "kind": "routes",
                    "destination": "philippines",
                    "source_urls": ["https://example.com/india-philippines-flights"],
                },
            }
        ]

    monkeypatch.setattr(tools.live_lookup, "get_or_fetch", _fake_get_or_fetch)

    # india<->philippines has no curated entry in backend.agents.routes.ROUTES.
    result = tools.check_route("india", "philippines")

    assert len(calls) == 1
    assert calls[0]["destination"] == "philippines"
    assert calls[0]["kind"] == "routes"

    assert result["known"] is True
    assert result["live_sourced"] is True
    assert "unverified-routes-philippines" in result["source_ids"]
    assert "philippines" in result["passages"].lower()


def test_uncurated_pair_stays_honest_when_live_lookup_finds_nothing(monkeypatch):
    monkeypatch.setattr(tools.live_lookup, "get_or_fetch", lambda *a, **k: [])

    result = tools.check_route("india", "philippines")

    assert result["known"] is False
    assert result["live_sourced"] is False
    assert "no curated route data" in result["note"].lower()


def test_missing_origin_skips_live_lookup_entirely(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("live_lookup.get_or_fetch should not run without a known origin")

    monkeypatch.setattr(tools.live_lookup, "get_or_fetch", _fail)

    result = tools.check_route("", "philippines")

    assert result["known"] is False
    assert result["live_sourced"] is False
