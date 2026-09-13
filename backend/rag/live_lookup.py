"""The RAG-miss fallback: real web search, grounded LLM synthesis, then ingest.

Gated entirely behind ``TAVILY_API_KEY`` (see ``settings.live_lookup_enabled``).
Absent that key this module is fully dormant and every public function returns
an empty result - the honesty guarantee described in
notes/03-rag-and-retrieval.md (a scoped search that matches nothing stays
empty) is completely unchanged for anyone who hasn't opted in.

Why this is NOT "ask the model and trust it": the failure mode this project
spent real effort guarding against (see the coverage guard, note 03, and the
``honesty-unknown-destination`` eval) is the model answering a gap in the
curated corpus from its own parametric memory - fluent, specific, and
unverifiable. Asking the same model to "double check" its own recollection
does not fix that; it is the same blind spots checking themselves.

What actually changes the risk profile here is that the *first* LLM call is
never allowed to answer from memory - it is handed real, freshly-fetched
search results and told to answer only from them, saying NOT_FOUND if they
don't contain an answer. The *second* call re-checks the first call's draft
sentence-by-sentence against those same snippets and strips anything not
directly supported. That is real, if imperfect, grounding against external
text - not the model checking its own homework from nothing.

Trust is tracked with a metadata flag, not a separate namespace. A document
this module writes lands in the SAME Pinecone namespace as curated content of
that kind (``visa``/``seasonal``/``tips``/``routes``), tagged
``metadata.origin = "live"`` - curated seed docs carry no such field (see
backend/rag/seed_data.py). Curated and live-sourced content used to be kept in
physically separate namespaces (a dedicated ``unverified`` namespace, keyed
only by destination). That looked safer but was not: a namespace keyed only by
destination cannot tell a visa question from a tips question, so once ANY
question about a country got a live answer, every OTHER kind of question about
that same country silently received that same cached, unrelated document
instead of ever searching for its own answer - reproduced live: a visa lookup
for Japan came back with backpacker-budget tips, because tips had been
live-searched for Japan first in the same turn. Sharing the real per-kind
namespace with curated content fixes that at the root: a visa search only ever
searches the visa namespace, live-sourced or not. The trust distinction that
matters - "was this hand-curated or fetched and synthesised this session" -
still needs disclosing to the traveller, which is exactly what
``metadata.origin`` is for; see search_visa_rules/search_backpacker_tips/
search_seasonal_notes and check_route in backend/agents/tools.py, and
_run_comparison in backend/agents/runner.py, which now key off ``origin``
instead of off namespace.

The ``coverage`` guard (backend/agents/coverage.py) is deliberately NOT
touched by this module: SUPPORTED stays curated-only, so a destination this
module has filled in via live search still cannot be ranked first or treated
as verified without disclosure. Closing a knowledge gap and lowering the
honesty bar are two different things, and this only does the first.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import httpx

from backend.config import settings
from backend.rag import store as rag_store

logger = logging.getLogger(__name__)

TAVILY_URL = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 15.0

_SYNTHESIS_PROMPT = """You are answering one narrow, factual backpacker travel question
using ONLY the search results below. Do not use anything you recall from training -
if the search results do not actually answer the question, say so.

QUESTION: {question}

SEARCH RESULTS:
{snippets}

Write a short, factual answer (3-6 sentences) a backpacker could act on: concrete
numbers (fees, durations, dates) where the results give them. Every sentence must be
traceable to one of the search results above. If results conflict, say so rather than
silently picking one. If the results genuinely do not answer the question, reply with
exactly: NOT_FOUND"""

_VERIFY_PROMPT = """You are fact-checking a drafted answer against the search results it
was supposedly built from. Check EVERY factual claim in the draft (a number, a date, a
rule, a name) against the search results text below.

DRAFTED ANSWER:
{answer}

SEARCH RESULTS:
{snippets}

Rewrite the answer keeping ONLY claims directly supported by the search results text.
Delete or soften anything you cannot find explicit support for. If nothing in the draft
is supported, reply with exactly: NOT_FOUND
Return only the corrected answer text, no preamble, no markdown."""

_SEASON_CLASSIFY_PROMPT = """You are rating how suitable one month is for backpacker travel in a
destination, based ONLY on the seasonal description below - not on anything you recall from
training.

DESTINATION: {destination}
MONTH: {month}

SEASONAL DESCRIPTION:
{passage}

Reply with EXACTLY one word and nothing else - good, mixed, avoid, or unknown. "avoid" means a
genuinely bad time (monsoon, typhoon peak, extreme heat, a major seasonal closure). "mixed" means
a real but manageable downside. "good" means no significant seasonal problem for backpacking. If
the description does not actually mention {month} or its season clearly enough to judge, reply
with exactly: unknown"""


def is_configured() -> bool:
    return settings.live_lookup_enabled


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


# --------------------------------------------------------------------------- #
# web search
# --------------------------------------------------------------------------- #
def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Real web search via Tavily. Empty, never raises, when unconfigured or failing."""
    if not settings.tavily_api_key:
        return []
    try:
        response = httpx.post(
            TAVILY_URL,
            headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
            json={
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": False,
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("live web search failed for %r: %s", query, exc)
        return []

    results: list[dict[str, str]] = []
    for item in data.get("results", []) or []:
        content = (item.get("content") or "").strip()
        if not content:
            continue
        results.append(
            {
                "title": (item.get("title") or "").strip(),
                "url": (item.get("url") or "").strip(),
                "content": content[:1500],
            }
        )
    return results


def _format_snippets(results: list[dict[str, str]]) -> str:
    return "\n\n".join(
        f"[{i}] {r['title']}\n{r['content']}\nSource: {r['url']}"
        for i, r in enumerate(results, start=1)
    )


def _llm_complete(prompt: str) -> str:
    """One raw OpenAI completion, outside ADK entirely.

    No manual tracing here: the openai auto-instrumentation turned on in
    backend/tracing/langfuse_setup.py captures every ``chat.completions.create``
    call - including this one, several calls removed from run_turn inside a
    tool function called back by ADK's own tool-execution loop - as its own
    Langfuse generation with the real model, prompt, completion and token
    usage, via OpenTelemetry's automatic context propagation. Nothing here
    needs to know tracing exists.
    """
    completion = _openai_client().chat.completions.create(
        model=settings.llm_model,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return (completion.choices[0].message.content or "").strip()


def _is_not_found(text: str) -> bool:
    return not text or text.strip().strip(".").upper() == "NOT_FOUND"


# --------------------------------------------------------------------------- #
# search -> synthesise -> verify -> document
# --------------------------------------------------------------------------- #
def fetch_and_verify(destination: str, kind: str, question: str) -> dict[str, Any] | None:
    """Search live, draft an answer grounded in it, verify the draft, and return
    an ingestable document - or None if any step comes up empty.

    Two LLM passes, not one, and neither is "ask the model what it knows": the
    synthesis pass may only answer from the supplied search snippets, and the
    verify pass then checks that pass's own output against those same snippets
    and strips anything unsupported. See the module docstring for why this is
    not the same as the model checking its own memory.
    """
    if not is_configured():
        return None

    results = search_web(question)
    if not results:
        return None

    snippets = _format_snippets(results)
    try:
        draft = _llm_complete(_SYNTHESIS_PROMPT.format(question=question, snippets=snippets))
        if _is_not_found(draft):
            return None

        verified = _llm_complete(_VERIFY_PROMPT.format(answer=draft, snippets=snippets))
    except Exception as exc:  # noqa: BLE001 - a synthesis failure must not kill the turn
        logger.warning("live-lookup synthesis failed for %r: %s", question, exc)
        return None

    if _is_not_found(verified):
        return None

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    source_urls = [r["url"] for r in results if r.get("url")]
    text = (
        f"[UNVERIFIED - live-sourced {fetched_at}, not part of the curated knowledge base, "
        f"confirm before relying on it] {verified}"
    )
    slug = destination.lower().strip().replace(" ", "-").replace(",", "")
    return {
        "id": f"live-{kind}-{slug}",
        "text": text,
        "metadata": {
            # Same content_type/namespace a curated doc of this kind would use
            # (see backend/rag/seed_data.py) - `origin` is what marks this one
            # as live-sourced rather than a separate namespace doing that job.
            "content_type": kind,
            "kind": kind,
            "origin": "live",
            "destination": destination.lower().strip(),
            "region": "live-sourced",
            "source_urls": source_urls,
            "fetched_at": fetched_at,
        },
    }


def get_or_fetch(
    destination: str, kind: str, question: str, top_k: int = 2
) -> list[dict[str, Any]]:
    """The RAG-miss fallback. Call ONLY after a curated-namespace search already
    came back empty (see backend/agents/tools.py) - this never runs instead of,
    or ahead of, real curated data.

    Checks the ``kind`` namespace first - the same one curated docs of this
    kind live in, since a live-sourced doc is ingested there too (see
    fetch_and_verify) - so a destination is only ever searched live,
    synthesised and verified ONCE per kind. "Next time it is in the RAG" is
    this cache hit (or, after the first hit, the caller's own curated-namespace
    search in backend/agents/tools.py finding it directly), not a fresh web
    search and two more LLM calls on every subsequent turn. Scoping the cache
    check to ``kind`` rather than a shared namespace is the fix for a real bug:
    a shared "unverified" namespace keyed only by destination could not tell a
    visa question from a tips question, so the first live answer for a country
    got reused for every other kind of question about it too.
    """
    if not is_configured():
        return []

    cached = rag_store.search(
        question, namespace=kind, destinations=[destination], top_k=top_k
    )
    if cached:
        return cached

    doc = fetch_and_verify(destination, kind, question)
    if not doc:
        return []

    try:
        rag_store.ingest([doc])
    except Exception as exc:  # noqa: BLE001 - a failed write must not break the turn
        logger.warning("failed to ingest live-sourced document %s: %s", doc["id"], exc)
        return []

    # Return the just-verified document directly rather than re-querying the
    # vector store immediately after the upsert. Pinecone's index is only
    # eventually consistent, so a search microseconds after ingest can miss
    # the vector it was just given - the live lookup quietly succeeds but the
    # caller sees an empty result and reports "no data", on exactly the turn
    # where a fresh answer was found and paid for. This document is what the
    # index will hold as soon as it catches up, so there is nothing to gain by
    # asking the store to confirm it back to us.
    return [
        {
            "id": doc["id"],
            "score": 1.0,
            "text": doc["text"],
            "metadata": doc["metadata"],
            "namespace": kind,
        }
    ]


def classify_season(destination: str, month: str) -> str | None:
    """A good/mixed/avoid/None rating for one month, for a destination
    backend.agents.climate's static CLIMATE_TABLE has no entry for.

    Built for the "where next" candidate ranking in backend/agents/runner.py,
    which could previously only ever call climate.assess() - fine for the
    ~15-country curated table, but permanently "unknown" for anything else, no
    matter how good or bad the real season actually is. Reproduced live: a
    traveller with mostly non-curated countries on their wishlist (Japan,
    Peru, Morocco, ...) had every one of them rank below Vietnam and Thailand
    even though both were genuinely in typhoon/monsoon season, because
    "unknown" had nothing to compete on - the ranking had no way to tell
    "unmeasured" apart from "actually fine".

    The EXPENSIVE part - a Tavily search plus the two-pass synthesis/verify -
    runs at most ONCE per destination, ever: this reads the same "seasonal"
    namespace document search_seasonal_notes uses (curated, or previously
    live-sourced), via get_or_fetch's existing cache. Once fetched for any
    month, that passage is part of the corpus, and classifying a DIFFERENT
    month later for the same destination is a single cheap completion against
    already-fetched, already-verified text - no new search, no repeat cost.

    Returns None (not "unknown" as a value) when there is nothing to classify
    at all - not configured, no search/curated hit, or a failed completion -
    so a caller can tell "genuinely nothing to go on" apart from "checked, and
    the passage itself did not clearly answer for this month".
    """
    if not is_configured():
        return None

    hits = get_or_fetch(
        destination,
        "seasonal",
        f"seasonal weather, monsoon or hazard season timing for {destination} for travellers",
        top_k=1,
    )
    if not hits:
        return None
    passage = (hits[0].get("text") or "").strip()
    if not passage:
        return None

    try:
        rating = _llm_complete(
            _SEASON_CLASSIFY_PROMPT.format(destination=destination, month=month, passage=passage)
        ).strip().lower()
    except Exception as exc:  # noqa: BLE001 - a classification failure must not kill the turn
        logger.warning("season classification failed for %r/%r: %s", destination, month, exc)
        return None

    return rating if rating in {"good", "mixed", "avoid"} else None
