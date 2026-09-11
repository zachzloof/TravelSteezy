"""Bayesian ranking for place recommendations.

Sorting by raw Google rating is actively misleading for a backpacker: a cafe with
one 5.0 review outranks a hostel with 4.6 from 2,400 people. The fix is the
standard Bayesian / "true Bayesian estimate" shrinkage used by IMDb's weighted
rank, which pulls thinly-reviewed places toward the typical rating of the candidate
set:

    weighted_score = (v / (v + m)) * R + (m / (v + m)) * C

    R = this place's rating
    v = this place's review count
    m = minimum review threshold (the prior's strength, in "virtual reviews")
    C = the prior: the review-count-weighted mean rating across the candidates

As v grows past m the place's own rating dominates; when v is small the score is
dragged toward C, so one-review outliers cannot win.

Pure functions, no network, no API key - so the maths is unit-testable on its own.
"""
from __future__ import annotations

from typing import Any, Iterable

DEFAULT_MIN_REVIEWS = 25

# Google Places API (New) returns price level as an enum string.
PRICE_LEVEL_ORDER = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}

# What a budget band will tolerate. Places with no price data are never excluded -
# most hostels do not publish one, and dropping them would gut the results.
BUDGET_MAX_PRICE_LEVEL = {"shoestring": 1, "mid": 2, "comfortable": 4}


def mean_rating(places: Iterable[dict[str, Any]]) -> float:
    """C: the prior - the typical rating across the candidate set.

    Weighted by review count rather than a plain average. A plain average lets a
    single thinly-reviewed outlier drag the prior toward itself, which then fails
    to shrink it: with just two candidates, a 5.0-from-1-review pulled the prior
    up to 4.9 and ended up OUTRANKING a 4.8-from-180. Weighting by evidence means
    a place with one review contributes roughly one review's worth to the prior.
    """
    total_weight = 0.0
    total = 0.0
    for place in places:
        rating = place.get("rating")
        count = place.get("user_rating_count")
        if rating is None or count is None:
            continue
        try:
            r = float(rating)
            v = float(count)
        except (TypeError, ValueError):
            continue
        if r <= 0 or v <= 0:
            continue
        total += r * v
        total_weight += v
    if total_weight == 0:
        return 0.0
    return total / total_weight


def weighted_score(
    rating: float | None, review_count: int | None, prior_mean: float, min_reviews: int
) -> float:
    """One place's Bayesian score. Returns 0.0 when there is nothing to go on."""
    if rating is None or review_count is None:
        return 0.0
    try:
        r = float(rating)
        v = int(review_count)
    except (TypeError, ValueError):
        return 0.0
    if r <= 0 or v < 0:
        return 0.0

    m = max(int(min_reviews), 0)
    denominator = v + m
    if denominator == 0:
        return r
    return (v / denominator) * r + (m / denominator) * prior_mean


def rank_places(
    places: list[dict[str, Any]],
    min_reviews: int = DEFAULT_MIN_REVIEWS,
    budget_band: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Score and sort candidates, annotating each with how it was scored.

    ``budget_band`` filters out places priced above what that band tolerates.
    Places with no price level are kept, since most budget accommodation omits it.
    """
    if not places:
        return []

    candidates = list(places)
    if budget_band:
        ceiling = BUDGET_MAX_PRICE_LEVEL.get(budget_band.strip().lower())
        if ceiling is not None:
            candidates = [
                p
                for p in candidates
                if PRICE_LEVEL_ORDER.get(p.get("price_level") or "", -1) <= ceiling
            ]
            # Never return an empty list purely because of a price filter.
            if not candidates:
                candidates = list(places)

    prior = mean_rating(candidates)
    scored: list[dict[str, Any]] = []
    for place in candidates:
        score = weighted_score(place.get("rating"), place.get("user_rating_count"), prior, min_reviews)
        scored.append(
            {
                **place,
                "weighted_score": round(score, 4),
                "ranking": {
                    "R_rating": place.get("rating"),
                    "v_review_count": place.get("user_rating_count"),
                    "m_min_reviews": min_reviews,
                    "C_candidate_mean": round(prior, 4),
                },
            }
        )

    scored.sort(
        key=lambda p: (p["weighted_score"], p.get("user_rating_count") or 0), reverse=True
    )
    return scored[:limit] if limit else scored


def explain_ranking(place: dict[str, Any]) -> str:
    """One human-readable line explaining why a place scored what it did."""
    info = place.get("ranking") or {}
    rating = info.get("R_rating")
    count = info.get("v_review_count")
    if rating is None or count is None:
        return f"{place.get('name', 'unknown')}: no rating data"
    return (
        f"{place.get('name', 'unknown')}: {rating} from {count} reviews "
        f"-> weighted {place.get('weighted_score')} "
        f"(shrunk toward candidate mean {info.get('C_candidate_mean')} "
        f"with m={info.get('m_min_reviews')})"
    )
