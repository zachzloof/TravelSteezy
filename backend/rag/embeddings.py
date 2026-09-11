"""Embeddings.

Primary path: OpenAI ``text-embedding-3-small`` (1536 dims), used both at
ingestion time and at query time.

Fallback path: when OPENAI_API_KEY is absent we use a deterministic hashed
bag-of-words vector instead. It is not as good as a real embedding, but it is a
genuine lexical-similarity signal rather than noise, which keeps the whole app and
the eval harness runnable on a laptop with no keys. Which path is active is
reported by ``embedding_backend()`` and surfaced in /health, so the README's claim
about what is real and what is a fallback can be checked, not just trusted.
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from typing import Iterable

from backend.config import settings

OPENAI_DIMS = 1536
FALLBACK_DIMS = 512

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be", "been",
    "to", "of", "in", "on", "at", "for", "with", "from", "by", "it", "its", "this",
    "that", "these", "those", "as", "if", "you", "your", "i", "we", "they", "there",
}


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key)


def embedding_backend() -> str:
    """Which embedding path is live: 'openai' or 'local-hash'."""
    return "openai" if settings.llm_enabled else "local-hash"


def embedding_dims() -> int:
    return OPENAI_DIMS if settings.llm_enabled else FALLBACK_DIMS


# --------------------------------------------------------------------------- #
# local deterministic fallback
# --------------------------------------------------------------------------- #
def _tokenise(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 2]


def _hash_embed(text: str) -> list[float]:
    """Hashed bag-of-words with sublinear term weighting, L2-normalised.

    Deterministic across processes (uses blake2b, not Python's salted hash()), so
    an index built in one run is still queryable in the next.
    """
    vec = [0.0] * FALLBACK_DIMS
    counts: dict[str, int] = {}
    for token in _tokenise(text):
        counts[token] = counts.get(token, 0) + 1

    for token, count in counts.items():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest[:4], "big") % FALLBACK_DIMS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign * (1.0 + math.log(count))

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """Embed a batch. Falls back to the local hash embedder without a key."""
    items = [t if t.strip() else " " for t in texts]
    if not items:
        return []

    if not settings.llm_enabled:
        return [_hash_embed(t) for t in items]

    response = _openai_client().embeddings.create(
        model=settings.embedding_model, input=items
    )
    return [d.embedding for d in response.data]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
