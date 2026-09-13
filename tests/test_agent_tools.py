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
                "id": "live-routes-philippines",
                "text": "[UNVERIFIED - live-sourced 2026-09-13] Flights from India to the "
                "Philippines run via Singapore or Bangkok, roughly 6-8 hours total.",
                "metadata": {
                    "content_type": "routes",
                    "kind": "routes",
                    "origin": "live",
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
    assert "live-routes-philippines" in result["source_ids"]
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


def test_search_visa_rules_flags_live_sourced_via_origin_metadata(monkeypatch):
    """Regression test: live_sourced used to be computed from
    hits[0]["namespace"] == "unverified". Now that a live-sourced document is
    ingested into the SAME namespace as curated content of its kind (see
    backend/rag/live_lookup.py), namespace alone can no longer tell the two
    apart - metadata.origin is what a live-sourced document carries and a
    curated one does not, so that is what live_sourced must check."""
    monkeypatch.setattr(tools.rag_store, "search", lambda *a, **k: [])
    monkeypatch.setattr(
        tools.live_lookup,
        "get_or_fetch",
        lambda *a, **k: [
            {
                "id": "live-visa-japan",
                "score": 1.0,
                "text": "[UNVERIFIED - live-sourced] ...",
                "metadata": {"content_type": "visa", "origin": "live", "destination": "japan"},
                "namespace": "visa",
            }
        ],
    )

    result = tools.search_visa_rules("japan", "United Kingdom")

    assert result["live_sourced"] is True
    assert "live-visa-japan" in result["source_ids"]


def test_search_visa_rules_does_not_flag_curated_hits_as_live_sourced(monkeypatch):
    monkeypatch.setattr(
        tools.rag_store,
        "search",
        lambda *a, **k: [
            {
                "id": "visa-thailand-western",
                "score": 0.9,
                "text": "Thailand visa exemption...",
                "metadata": {"content_type": "visa", "destination": "thailand"},
                "namespace": "visa",
            }
        ],
    )

    def _fail(*args, **kwargs):
        raise AssertionError("a curated hit should short-circuit before any live lookup")

    monkeypatch.setattr(tools.live_lookup, "get_or_fetch", _fail)

    result = tools.search_visa_rules("thailand", "United Kingdom")

    assert result["live_sourced"] is False


# --------------------------------------------------------------------------- #
# check_seasonal_conditions's live-lookup fallback
# --------------------------------------------------------------------------- #
def test_curated_seasonal_rating_never_calls_classify_season(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("classify_season should not run for a curated destination")

    monkeypatch.setattr(tools.live_lookup, "classify_season", _fail)

    result = tools.check_seasonal_conditions("thailand", "September")

    assert result["known"] is True
    assert result["rating"] == "avoid"  # curated: wettest month on the Andaman coast
    assert result["live_sourced"] is False


def test_uncurated_destination_falls_back_to_classify_season(monkeypatch):
    """Regression test for the exact bug reported live: check_seasonal_conditions
    used to have NO live fallback at all, so a wishlist country outside the
    curated table (e.g. South Korea) was reported as "unknown, no verified
    seasonal data" even on a turn where search_seasonal_notes - a different
    tool, already live-aware - found real seasonal data for the same country."""
    calls = []

    def _fake_classify_season(destination, month):
        calls.append((destination, month))
        return "mixed"

    monkeypatch.setattr(tools.live_lookup, "classify_season", _fake_classify_season)

    result = tools.check_seasonal_conditions("south korea", "September")

    assert calls == [("south korea", "September")]
    assert result["known"] is True
    assert result["rating"] == "mixed"
    assert result["is_bad_season"] is False
    assert result["live_sourced"] is True


def test_uncurated_destination_stays_honest_when_classify_season_finds_nothing(monkeypatch):
    monkeypatch.setattr(tools.live_lookup, "classify_season", lambda *a, **k: None)

    result = tools.check_seasonal_conditions("atlantis", "September")

    assert result["known"] is False
    assert result["rating"] == "unknown"
    assert result["live_sourced"] is False
