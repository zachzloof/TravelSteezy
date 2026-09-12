"""The RAG store.

Primary backend: Pinecone (managed, serverless). Documents are namespaced by
content type - ``visa``, ``seasonal``, ``tips`` - so the Logistics agent searches
only visa/seasonal content and the Recommendations agent searches only tips,
rather than every agent searching the whole index.

Fallback backend: a local JSON index on disk with brute-force cosine search. It
exists so the app, the tests and the eval harness run end-to-end with no managed
service and no keys. ``backend_name()`` reports which one is live and /health
exposes it, so "is the RAG real right now" is an observable fact.

Unlike the SQLite memory store, Pinecone data is NOT on the Railway volume - it
lives in the managed service and survives redeploys independently.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, Iterable

from backend.config import settings
from backend.rag import embeddings
from backend.rag.route_data import KNOWN_CITIES, ROUTE_DOCS
from backend.rag.seed_data import KNOWN_DESTINATIONS, SEED_DOCUMENTS

# visa/seasonal/tips are the curated country-level corpus.
# routes is city-level hop knowledge ("where next from Chiang Mai").
# experience is written at runtime from real user reviews and from whether a
# suggestion was accepted, so the store improves with use.
NAMESPACES = ("visa", "seasonal", "tips", "routes", "experience")

ALL_SEED_DOCUMENTS = SEED_DOCUMENTS + ROUTE_DOCS


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def backend_name() -> str:
    return "pinecone" if settings.pinecone_enabled else "local-json"


def detect_destinations(text: str) -> list[str]:
    """Pull known destination names out of free text.

    Used to scope retrieval to the candidate destinations in the query rather than
    searching the whole index. Handles a few common aliases.
    """
    lowered = (text or "").lower()
    aliases = {
        "bali": "indonesia",
        "ubud": "indonesia",
        "canggu": "indonesia",
        "java": "indonesia",
        "lombok": "indonesia",
        "gili": "indonesia",
        "siem reap": "cambodia",
        "angkor": "cambodia",
        "phnom penh": "cambodia",
        "hanoi": "vietnam",
        "saigon": "vietnam",
        "ho chi minh": "vietnam",
        "hoi an": "vietnam",
        "sapa": "vietnam",
        "ha giang": "vietnam",
        "bangkok": "thailand",
        "chiang mai": "thailand",
        "koh": "thailand",
        "phuket": "thailand",
        "krabi": "thailand",
        "pai": "thailand",
        "luang prabang": "laos",
        "vientiane": "laos",
        "vang vieng": "laos",
        "penang": "malaysia",
        "kuala lumpur": "malaysia",
        "borneo": "malaysia",
        "langkawi": "malaysia",
        "perhentian": "malaysia",
        "el nido": "philippines",
        "palawan": "philippines",
        "siargao": "philippines",
        "cebu": "philippines",
        "coron": "philippines",
        "kathmandu": "nepal",
        "pokhara": "nepal",
        "annapurna": "nepal",
        "everest": "nepal",
        "colombo": "sri lanka",
        "ella": "sri lanka",
        "arugam": "sri lanka",
        "kandy": "sri lanka",
        "mirissa": "sri lanka",
    }

    found: list[str] = []
    for dest in KNOWN_DESTINATIONS:
        if re.search(rf"\b{re.escape(dest)}\b", lowered):
            found.append(dest)
    for alias, dest in aliases.items():
        if alias in lowered and dest not in found:
            found.append(dest)
    return found


def detect_cities(text: str) -> list[dict[str, str]]:
    """Pull known city/town names out of free text, with their country.

    Country-level detection is not enough once routes and visits are tracked at
    town granularity: "I'm in Chiang Mai now" has to resolve to a city, not to
    Thailand. Longer names match first so "Gili Trawangan" is not reduced to a
    shorter overlapping entry.
    """
    lowered = (text or "").lower()
    found: list[dict[str, str]] = []
    claimed: list[str] = []
    for city in sorted(KNOWN_CITIES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(city)}\b", lowered):
            if any(city in longer for longer in claimed):
                continue
            claimed.append(city)
            found.append({"city": city, "country": KNOWN_CITIES[city]})
    return found


# --------------------------------------------------------------------------- #
# Pinecone backend
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _pinecone_index():
    from pinecone import Pinecone, ServerlessSpec

    pc = Pinecone(api_key=settings.pinecone_api_key)
    existing = {i["name"] for i in pc.list_indexes()}
    if settings.pinecone_index not in existing:
        pc.create_index(
            name=settings.pinecone_index,
            dimension=embeddings.embedding_dims(),
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )
    return pc.Index(settings.pinecone_index)


def _pinecone_upsert(documents: Iterable[dict[str, Any]]) -> dict[str, int]:
    docs = list(documents)
    index = _pinecone_index()
    counts: dict[str, int] = {}
    for namespace in NAMESPACES:
        batch = [d for d in docs if d["metadata"]["content_type"] == namespace]
        if not batch:
            continue
        vectors = embeddings.embed_texts([d["text"] for d in batch])
        index.upsert(
            vectors=[
                {
                    "id": doc["id"],
                    "values": vec,
                    # Pinecone metadata must be scalars or string lists; keep the
                    # source text there so retrieval returns usable passages.
                    "metadata": {**_flatten_metadata(doc["metadata"]), "text": doc["text"]},
                }
                for doc, vec in zip(batch, vectors)
            ],
            namespace=namespace,
        )
        counts[namespace] = len(batch)
    return counts


def _flatten_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Pinecone rejects nested objects; coerce lists of scalars to string lists."""
    flat: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            flat[key] = value
        elif isinstance(value, list):
            flat[key] = [str(v) for v in value]
        else:
            flat[key] = str(value)
    return flat


def _pinecone_query(
    query: str, namespace: str, destinations: list[str] | None, top_k: int
) -> list[dict[str, Any]]:
    index = _pinecone_index()
    flt: dict[str, Any] | None = None
    if destinations:
        flt = {"destination": {"$in": [d.lower() for d in destinations]}}

    result = index.query(
        vector=embeddings.embed_text(query),
        top_k=top_k,
        namespace=namespace,
        include_metadata=True,
        filter=flt,
    )
    matches = result.get("matches", []) if isinstance(result, dict) else result.matches
    out = []
    for match in matches:
        metadata = dict(match["metadata"] if isinstance(match, dict) else match.metadata)
        text = metadata.pop("text", "")
        out.append(
            {
                "id": match["id"] if isinstance(match, dict) else match.id,
                "score": float(match["score"] if isinstance(match, dict) else match.score),
                "text": text,
                "metadata": metadata,
                "namespace": namespace,
            }
        )
    return out


# --------------------------------------------------------------------------- #
# local JSON backend
# --------------------------------------------------------------------------- #
def _load_local_index() -> dict[str, Any]:
    path = settings.local_rag_path
    if not path.exists():
        return {"backend": "local-json", "embedding": None, "documents": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"backend": "local-json", "embedding": None, "documents": []}


def _local_upsert(documents: Iterable[dict[str, Any]]) -> dict[str, int]:
    docs = list(documents)
    vectors = embeddings.embed_texts([d["text"] for d in docs])
    payload = {
        "backend": "local-json",
        "embedding": embeddings.embedding_backend(),
        "dims": embeddings.embedding_dims(),
        "documents": [
            {"id": d["id"], "text": d["text"], "metadata": d["metadata"], "vector": v}
            for d, v in zip(docs, vectors)
        ],
    }
    settings.ensure_dirs()
    settings.local_rag_path.write_text(json.dumps(payload), encoding="utf-8")
    counts: dict[str, int] = {}
    for doc in docs:
        ns = doc["metadata"]["content_type"]
        counts[ns] = counts.get(ns, 0) + 1
    return counts


def _local_query(
    query: str, namespace: str, destinations: list[str] | None, top_k: int
) -> list[dict[str, Any]]:
    index = _load_local_index()
    docs = index.get("documents", [])

    # If the index was built with a different embedder than the one now active,
    # it is unusable - say so loudly rather than returning silent nonsense.
    if docs and index.get("embedding") != embeddings.embedding_backend():
        raise RuntimeError(
            f"Local RAG index was built with the '{index.get('embedding')}' embedder but "
            f"'{embeddings.embedding_backend()}' is active. Re-run scripts/ingest_rag.py."
        )

    wanted = {d.lower() for d in destinations} if destinations else None
    query_vec = embeddings.embed_text(query)

    scored = []
    for doc in docs:
        metadata = doc["metadata"]
        if metadata.get("content_type") != namespace:
            continue
        if wanted and metadata.get("destination") not in wanted:
            continue
        scored.append(
            {
                "id": doc["id"],
                "score": embeddings.cosine_similarity(query_vec, doc["vector"]),
                "text": doc["text"],
                "metadata": metadata,
                "namespace": namespace,
            }
        )
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:top_k]


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def ingest(documents: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Embed and upsert documents into whichever backend is configured."""
    docs = list(documents if documents is not None else ALL_SEED_DOCUMENTS)
    if settings.pinecone_enabled:
        counts = _pinecone_upsert(docs)
    else:
        counts = _local_upsert(docs)
    return {
        "backend": backend_name(),
        "embedding": embeddings.embedding_backend(),
        "documents": len(docs),
        "by_namespace": counts,
    }


def search(
    query: str,
    namespace: str,
    destinations: list[str] | None = None,
    top_k: int = 4,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    """Similarity search within one content-type namespace.

    ``destinations`` scopes the search via metadata filter. A scoped search that
    matches nothing returns nothing: we deliberately do NOT fall back to an
    unscoped search, because passages about the wrong country are worse than no
    passages at all (see the note in the body).
    """
    if namespace not in NAMESPACES:
        raise ValueError(f"Unknown namespace {namespace!r}; expected one of {NAMESPACES}.")

    runner = _pinecone_query if settings.pinecone_enabled else _local_query
    try:
        hits = runner(query, namespace, destinations, top_k)
        # NOTE (eval fix, case honesty-unknown-destination): an earlier version
        # retried UNSCOPED when a destination-scoped search came back empty. That
        # handed the agent passages about entirely different countries, which it
        # then used to confabulate specifics for a destination we hold no data on.
        # An empty result is the correct, honest answer - the agents are instructed
        # to say they have no verified data rather than fill the gap.
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001 - retrieval must never kill a turn
        return [{"id": "retrieval-error", "score": 0.0, "text": "", "metadata": {},
                 "namespace": namespace, "error": str(exc)}]

    return [h for h in hits if h.get("score", 0.0) >= min_score]


def fetch_by_ids(ids: list[str], namespace: str = "experience") -> list[dict[str, Any]]:
    """Look up specific documents by their exact id, no similarity search.

    Used by the memory debug page to answer "what has THIS account actually
    published to the shared store" - ids for experience documents are
    deterministic (see backend/rag/experience.py), so the caller can compute
    exactly which ids an account's own reviews would have produced and check
    whether each one is really there, rather than guessing from what was
    submitted. A review that was too short to index, or marked private, will
    correctly not appear.
    """
    if not ids:
        return []
    try:
        if settings.pinecone_enabled:
            index = _pinecone_index()
            result = index.fetch(ids=ids, namespace=namespace)
            found = []
            for vid, vec in (result.vectors or {}).items():
                md = dict(vec.metadata or {})
                found.append({"id": vid, "metadata": md, "text": md.get("text", "")})
            return found
        data = _load_local_index()
        wanted = set(ids)
        return [
            {"id": d["id"], "metadata": d.get("metadata", {}), "text": d.get("text", "")}
            for d in data.get("documents", [])
            if d["id"] in wanted
        ]
    except Exception as exc:  # noqa: BLE001 - a debug view must never 500
        return [{"id": "fetch-error", "metadata": {}, "text": "", "error": str(exc)}]


def format_passages(hits: list[dict[str, Any]]) -> str:
    """Render hits as a numbered, citable block for an agent prompt."""
    if not hits:
        return "(no passages retrieved)"
    lines = []
    for i, hit in enumerate(hits, start=1):
        dest = hit.get("metadata", {}).get("destination", "general")
        lines.append(f"[{i}] (source_id={hit['id']}, destination={dest})\n{hit['text']}")
    return "\n\n".join(lines)


def index_stats() -> dict[str, Any]:
    """Lightweight health info without requiring a query."""
    if settings.pinecone_enabled:
        try:
            stats = _pinecone_index().describe_index_stats()
            return {"backend": "pinecone", "index": settings.pinecone_index, "stats": dict(stats)}
        except Exception as exc:  # noqa: BLE001
            return {"backend": "pinecone", "index": settings.pinecone_index, "error": str(exc)}
    index = _load_local_index()
    return {
        "backend": "local-json",
        "path": str(settings.local_rag_path),
        "documents": len(index.get("documents", [])),
        "embedding": index.get("embedding"),
    }
