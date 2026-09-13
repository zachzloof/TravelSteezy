"""Tests for backend.rag.live_lookup.get_or_fetch's post-ingest behaviour.

No API keys and no network: rag_store and fetch_and_verify are monkeypatched
directly. The real search + LLM synthesis pipeline is covered by the evals
suite.

    python -m pytest tests/test_live_lookup.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.rag import live_lookup  # noqa: E402


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    monkeypatch.setattr(live_lookup, "is_configured", lambda: True)


def test_cache_hit_short_circuits_before_any_fetch(monkeypatch):
    monkeypatch.setattr(
        live_lookup.rag_store, "search", lambda *a, **k: [{"id": "live-routes-laos"}]
    )

    def _fail(*args, **kwargs):
        raise AssertionError("fetch_and_verify should not run on a cache hit")

    monkeypatch.setattr(live_lookup, "fetch_and_verify", _fail)

    result = live_lookup.get_or_fetch("laos", "routes", "how far is laos")

    assert result == [{"id": "live-routes-laos"}]


def test_cache_check_is_scoped_to_the_kind_namespace(monkeypatch):
    """Regression test: the cache check used to run against a single shared
    "unverified" namespace keyed only by destination, so a visa question and a
    tips question about the same country collided - the first live answer for
    a country got reused for every other kind of question about it. The check
    must now be scoped to the SAME namespace curated docs of this kind use."""
    seen_namespaces = []

    def _search(query, namespace, destinations=None, top_k=2, **kwargs):
        seen_namespaces.append(namespace)
        return []

    monkeypatch.setattr(live_lookup.rag_store, "search", _search)
    monkeypatch.setattr(live_lookup, "fetch_and_verify", lambda *a, **k: None)

    live_lookup.get_or_fetch("laos", "visa", "visa requirements for laos")

    assert seen_namespaces == ["visa"]


def test_fresh_fetch_returns_the_document_without_re_querying_the_store(monkeypatch):
    """Regression test: get_or_fetch used to re-run rag_store.search immediately
    after rag_store.ingest to fetch back what it had just written. Pinecone's
    index is only eventually consistent, so that re-query could legitimately
    return nothing for a vector that had just been upserted, silently turning a
    successful live lookup into an empty result. It must now hand back the
    document it just verified and ingested directly, with no second search."""
    search_calls = []

    def _search(query, namespace, destinations=None, top_k=2, **kwargs):
        search_calls.append((namespace, tuple(destinations or ())))
        return []  # cache miss every time, including any post-ingest re-query

    ingested = []

    doc = {
        "id": "live-routes-mongolia",
        "text": "[UNVERIFIED - live-sourced] Flights from Nepal to Mongolia run via Delhi, "
        "roughly 8-10 hours total.",
        "metadata": {
            "content_type": "routes",
            "kind": "routes",
            "origin": "live",
            "destination": "mongolia",
        },
    }

    monkeypatch.setattr(live_lookup.rag_store, "search", _search)
    monkeypatch.setattr(live_lookup.rag_store, "ingest", lambda docs: ingested.extend(docs))
    monkeypatch.setattr(live_lookup, "fetch_and_verify", lambda *a, **k: doc)

    result = live_lookup.get_or_fetch("mongolia", "routes", "how to get from nepal to mongolia")

    assert ingested == [doc]
    # Exactly one search call: the initial cache check. No post-ingest re-query.
    assert len(search_calls) == 1

    assert len(result) == 1
    assert result[0]["id"] == doc["id"]
    assert result[0]["text"] == doc["text"]
    assert result[0]["metadata"] == doc["metadata"]
    assert result[0]["namespace"] == "routes"


def test_failed_ingest_returns_empty_rather_than_raising(monkeypatch):
    monkeypatch.setattr(live_lookup.rag_store, "search", lambda *a, **k: [])
    monkeypatch.setattr(
        live_lookup.rag_store,
        "ingest",
        lambda docs: (_ for _ in ()).throw(RuntimeError("pinecone is down")),
    )
    monkeypatch.setattr(
        live_lookup,
        "fetch_and_verify",
        lambda *a, **k: {"id": "x", "text": "y", "metadata": {}},
    )

    result = live_lookup.get_or_fetch("mongolia", "routes", "how to get from nepal to mongolia")

    assert result == []


def test_not_configured_returns_empty_without_touching_the_store(monkeypatch):
    monkeypatch.setattr(live_lookup, "is_configured", lambda: False)

    def _fail(*args, **kwargs):
        raise AssertionError("rag_store.search should not run when live lookup is disabled")

    monkeypatch.setattr(live_lookup.rag_store, "search", _fail)

    result = live_lookup.get_or_fetch("mongolia", "routes", "how to get from nepal to mongolia")

    assert result == []


# --------------------------------------------------------------------------- #
# classify_season
# --------------------------------------------------------------------------- #
def test_classify_season_reads_the_cached_seasonal_passage(monkeypatch):
    """The expensive part (search + synthesis/verify) must not re-run just to
    classify a different month - classify_season should reuse whatever
    get_or_fetch already has cached for the "seasonal" kind."""
    calls = []

    def _get_or_fetch(destination, kind, question, top_k=2):
        calls.append((destination, kind))
        return [{"id": "live-seasonal-narnia", "text": "Narnia is always winter."}]

    monkeypatch.setattr(live_lookup, "get_or_fetch", _get_or_fetch)
    monkeypatch.setattr(live_lookup, "_llm_complete", lambda prompt: "avoid")

    rating = live_lookup.classify_season("narnia", "December")

    assert rating == "avoid"
    assert calls == [("narnia", "seasonal")]


def test_classify_season_returns_none_when_no_passage_exists(monkeypatch):
    monkeypatch.setattr(live_lookup, "get_or_fetch", lambda *a, **k: [])

    def _fail(*args, **kwargs):
        raise AssertionError("no passage to classify - should not call the LLM at all")

    monkeypatch.setattr(live_lookup, "_llm_complete", _fail)

    assert live_lookup.classify_season("atlantis", "June") is None


def test_classify_season_returns_none_when_not_configured(monkeypatch):
    monkeypatch.setattr(live_lookup, "is_configured", lambda: False)

    def _fail(*args, **kwargs):
        raise AssertionError("get_or_fetch should not run when live lookup is disabled")

    monkeypatch.setattr(live_lookup, "get_or_fetch", _fail)

    assert live_lookup.classify_season("narnia", "December") is None


def test_classify_season_treats_an_unclear_verdict_as_no_rating(monkeypatch):
    """"unknown" (the passage didn't clearly cover this month) and any other
    junk the completion might return both mean "nothing to rank with" - the
    caller (runner.py) must fall back to plain "unknown", not a fabricated
    tier, so this returns None rather than the literal string "unknown"."""
    monkeypatch.setattr(
        live_lookup, "get_or_fetch",
        lambda *a, **k: [{"id": "x", "text": "some passage"}],
    )
    monkeypatch.setattr(live_lookup, "_llm_complete", lambda prompt: "unknown")

    assert live_lookup.classify_season("narnia", "December") is None
