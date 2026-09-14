"""Chunk, embed and upsert the seed corpus into the RAG store.

    python -m scripts.ingest_rag          # ingest the seed corpus
    python -m scripts.ingest_rag --stats  # just report what is in the index

Targets Pinecone when PINECONE_API_KEY is set, otherwise the local JSON index.
Run this once after setting keys, and again whenever seed_data.py changes or you
switch embedding backends.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings  # noqa: E402
from backend.rag import embeddings, store  # noqa: E402
from backend.rag.experience import backfill_from_memory  # noqa: E402
from backend.rag.store import ALL_SEED_DOCUMENTS  # noqa: E402

MAX_CHARS = 1800


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split any oversized document on paragraph boundaries.

    The seed docs are written to sit under the limit already, so in practice this
    is a no-op guard that keeps the pipeline correct if someone adds a long doc.
    """
    chunks: list[dict] = []
    for doc in documents:
        text = doc["text"]
        if len(text) <= MAX_CHARS:
            chunks.append(doc)
            continue
        parts, current = [], ""
        for paragraph in text.split("\n\n"):
            if len(current) + len(paragraph) + 2 > MAX_CHARS and current:
                parts.append(current.strip())
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}" if current else paragraph
        if current.strip():
            parts.append(current.strip())
        for i, part in enumerate(parts):
            chunks.append(
                {
                    "id": f"{doc['id']}-c{i}",
                    "text": part,
                    "metadata": {**doc["metadata"], "parent_id": doc["id"]},
                }
            )
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest seed content into the RAG store.")
    parser.add_argument("--stats", action="store_true", help="report index stats and exit")
    parser.add_argument(
        "--wipe", action="store_true",
        help="delete every vector in every namespace before ingesting - clears stale "
             "live-sourced cache documents as well as any previous curated content",
    )
    parser.add_argument(
        "--experience", action="store_true",
        help="also index reviews and recommendation outcomes already in SQLite",
    )
    args = parser.parse_args()

    print(f"RAG backend    : {store.backend_name()}")
    print(f"Embedding model: {embeddings.embedding_backend()} ({embeddings.embedding_dims()} dims)")
    if not settings.pinecone_enabled:
        print("  ! PINECONE_API_KEY not set - using the local JSON index fallback.")
    if not settings.llm_enabled:
        print("  ! OPENAI_API_KEY not set - using the deterministic local hash embedder.")

    if args.stats:
        print(json.dumps(store.index_stats(), indent=2, default=str))
        return 0

    if args.wipe:
        print("Wiping all namespaces before reingest...")
        print(json.dumps(store.wipe(), indent=2, default=str))

    chunks = chunk_documents(ALL_SEED_DOCUMENTS)
    print(f"\nIngesting {len(chunks)} chunks from {len(ALL_SEED_DOCUMENTS)} seed documents...")
    result = store.ingest(chunks)
    print(json.dumps(result, indent=2))

    if args.experience:
        outcome = backfill_from_memory()
        print(f"Backfilled experience documents: {outcome}")

    # Smoke-test retrieval so a broken ingest fails loudly here, not mid-demo.
    probe = store.search("monsoon season rain", namespace="seasonal", destinations=["thailand"])
    print(f"\nSmoke test: 'monsoon season rain' scoped to thailand -> {len(probe)} hit(s)")
    for hit in probe[:2]:
        print(f"  {hit['score']:.3f}  {hit['id']}")
    return 0 if probe else 1


if __name__ == "__main__":
    raise SystemExit(main())
