"""The feedback loop: real traveller experience written back into the RAG store.

Two signals go into the ``experience`` namespace:

  * **post-visit reviews** - a rating and free-text notes attached to a place the
    traveller actually went to
  * **recommendation outcomes** - whether a suggestion we surfaced was taken or
    turned down, and why

The Recommendations agent retrieves from this namespace alongside the curated
``tips`` corpus, so suggestions improve as the app is used rather than staying
frozen at whatever was seeded.

Privacy: documents are written with the *account id* only, never a username, and
the agent is told to present them as anonymous traveller feedback. A user's own
free-text review can still be surfaced to another user, so the ingestion function
takes ``share=False`` for anything a user marks private.
"""
from __future__ import annotations

import logging
from typing import Any

from backend.rag import store as rag_store
from backend.rag.route_data import KNOWN_CITIES

logger = logging.getLogger(__name__)

MIN_REVIEW_CHARS = 12


def _country_for(location: str) -> str | None:
    return KNOWN_CITIES.get((location or "").strip().lower())


def review_document(
    user_id: int,
    location: str,
    rating: int | None,
    review_notes: str | None,
    country: str | None = None,
) -> dict[str, Any] | None:
    """Turn one post-visit review into a retrievable document.

    Returns None when there is nothing worth indexing - a bare rating with no
    prose adds noise to retrieval without adding information.
    """
    location = (location or "").strip()
    notes = (review_notes or "").strip()
    if not location or len(notes) < MIN_REVIEW_CHARS:
        return None

    stars = f"{rating}/5" if rating else "unrated"
    text = (
        f"Traveller feedback on {location} ({stars}): {notes}"
    )
    return {
        "id": f"experience-review-u{user_id}-{location.lower().replace(' ', '-')}",
        "text": text,
        "metadata": {
            "content_type": "experience",
            "destination": location.lower(),
            "country": (country or _country_for(location) or "").lower(),
            "region": "user-generated",
            "signal": "review",
            "rating": int(rating) if rating else 0,
            "account_id": int(user_id),
        },
    }


def outcome_document(
    user_id: int,
    location: str,
    verdict: str,
    from_location: str | None = None,
    reason: str | None = None,
) -> dict[str, Any] | None:
    """Turn an accepted/rejected recommendation into a retrievable document."""
    location = (location or "").strip()
    if not location or verdict not in {"accepted", "rejected"}:
        return None

    leg = f" after {from_location}" if from_location else ""
    because = f" Reason given: {reason.strip()}" if (reason or "").strip() else ""
    verb = "went to" if verdict == "accepted" else "turned down"
    text = (
        f"A backpacker {verb} the suggestion of {location}{leg}.{because}"
    )
    return {
        "id": f"experience-outcome-u{user_id}-{location.lower().replace(' ', '-')}-{verdict}",
        "text": text,
        "metadata": {
            "content_type": "experience",
            "destination": location.lower(),
            "country": (_country_for(location) or "").lower(),
            "region": "user-generated",
            "signal": f"outcome_{verdict}",
            "account_id": int(user_id),
        },
    }


def ingest_documents(documents: list[dict[str, Any]]) -> dict[str, Any]:
    """Upsert experience documents. Never raises into a chat turn."""
    documents = [d for d in documents if d]
    if not documents:
        return {"ingested": 0, "skipped": True}
    try:
        result = rag_store.ingest(documents)
        return {"ingested": len(documents), "backend": result.get("backend")}
    except Exception as exc:  # noqa: BLE001
        logger.warning("experience ingest failed: %s", exc)
        return {"ingested": 0, "error": str(exc)}


def ingest_review(
    user_id: int,
    location: str,
    rating: int | None,
    review_notes: str | None,
    share: bool = True,
) -> dict[str, Any]:
    if not share:
        return {"ingested": 0, "skipped": "user marked this review private"}
    return ingest_documents([review_document(user_id, location, rating, review_notes)])


def ingest_outcome(
    user_id: int,
    location: str,
    verdict: str,
    from_location: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return ingest_documents(
        [outcome_document(user_id, location, verdict, from_location, reason)]
    )


def list_own_documents(user_id: int) -> list[dict[str, Any]]:
    """What THIS account has actually published to the shared experience store.

    Document ids are deterministic (see review_document/outcome_document above),
    so rather than trusting "I asked for it to be shared" as a proxy for "it is
    out there", this recomputes the ids a full set of reviews/outcomes for this
    account WOULD have produced and checks which of them genuinely exist in the
    index. A review that was too short to index, or explicitly kept private
    (share=False), correctly does not appear - this reports what is real, not
    what was requested.
    """
    from backend.db import get_conn

    with get_conn() as conn:
        reviews = conn.execute(
            "SELECT location FROM travel_history "
            "WHERE user_id = ? AND review_notes IS NOT NULL AND TRIM(review_notes) != ''",
            (user_id,),
        ).fetchall()
        outcomes = conn.execute(
            "SELECT location, verdict FROM recommendation_feedback WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    candidate_ids = [
        f"experience-review-u{user_id}-{row['location'].lower().replace(' ', '-')}"
        for row in reviews
    ]
    candidate_ids += [
        f"experience-outcome-u{user_id}-{row['location'].lower().replace(' ', '-')}-{row['verdict']}"
        for row in outcomes
    ]
    if not candidate_ids:
        return []
    return [d for d in rag_store.fetch_by_ids(candidate_ids) if d.get("id") != "fetch-error"]


def search_experience(
    query: str, destinations: list[str] | None = None, top_k: int = 3
) -> list[dict[str, Any]]:
    """Retrieve traveller feedback for a destination."""
    return rag_store.search(
        query, namespace="experience", destinations=destinations, top_k=top_k
    )


def backfill_from_memory() -> dict[str, Any]:
    """Index every review and outcome already sitting in SQLite.

    Used once after deploying the feedback loop, so existing reviews are not
    stranded outside the RAG store, and by the ingest script's --experience flag.
    """
    from backend.db import get_conn

    documents: list[dict[str, Any]] = []
    with get_conn() as conn:
        reviews = conn.execute(
            "SELECT user_id, location, country, rating, review_notes FROM travel_history "
            "WHERE review_notes IS NOT NULL AND TRIM(review_notes) != ''"
        ).fetchall()
        outcomes = conn.execute(
            "SELECT user_id, location, from_location, verdict, reason FROM recommendation_feedback"
        ).fetchall()

    for row in reviews:
        documents.append(
            review_document(
                row["user_id"], row["location"], row["rating"],
                row["review_notes"], row["country"],
            )
        )
    for row in outcomes:
        documents.append(
            outcome_document(
                row["user_id"], row["location"], row["verdict"],
                row["from_location"], row["reason"],
            )
        )
    return ingest_documents(documents)
