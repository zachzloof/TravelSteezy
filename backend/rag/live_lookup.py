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

Three-tier trust model, kept deliberately visible rather than laundered into
one pile of "the RAG store":
  - curated (``visa``/``seasonal``/``tips``/``routes``) - hand-written seed
    content, the thing the app's honesty guarantees are actually built on.
  - ``unverified`` - written here, from a live search, checked once against
    its own sources. Presented to the traveller as unconfirmed, always.
  - ``experience`` - real traveller reviews/outcomes, presented as anecdote.

The ``coverage`` guard (backend/agents/coverage.py) is deliberately NOT
touched by this module: SUPPORTED stays curated-only, so a destination this
module has filled in via live search still cannot be ranked first or treated
as verified. Closing a knowledge gap and lowering the honesty bar are two
different things, and this only does the first.
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
NAMESPACE = "unverified"

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
        "id": f"unverified-{kind}-{slug}",
        "text": text,
        "metadata": {
            "content_type": NAMESPACE,
            "kind": kind,
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

    Checks the ``unverified`` namespace first, so a destination is only ever
    searched live, synthesised and verified ONCE - "next time it is in the
    RAG" is this cache hit, not a fresh web search and two more LLM calls on
    every subsequent turn.
    """
    if not is_configured():
        return []

    cached = rag_store.search(
        question, namespace=NAMESPACE, destinations=[destination], top_k=top_k
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
            "namespace": NAMESPACE,
        }
    ]
