"""Direct read/write access to the structured travel memory.

The conversational path can do all of this too, but a user should never be forced
to talk to an agent to correct their own data - and a marker should be able to
verify stored state without taking the chat's word for it. Same rule as
/profile/me: user_id comes from the signed token, never from a parameter.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.memory import travel as travel_store
from backend.rag import experience as experience_store
from backend.schemas import (
    OnboardingState,
    ReviewRequest,
    TravelEntry,
    TravelSnapshotResponse,
    VisitRequest,
    WishlistEntry,
    WishlistRequest,
)
from backend.security import current_user

router = APIRouter(prefix="/travel", tags=["travel"])


def _snapshot(user_id: int) -> TravelSnapshotResponse:
    snapshot = travel_store.get_travel_snapshot(user_id)
    gaps = travel_store.onboarding_gaps(user_id)
    return TravelSnapshotResponse(
        travel_history=[TravelEntry(**h) for h in snapshot["travel_history"]],
        wishlist=[WishlistEntry(**w) for w in snapshot["wishlist"]],
        interests=snapshot["interests"],
        pending_reviews=[p["location"] for p in snapshot["pending_reviews"]],
        onboarding=OnboardingState(**snapshot["onboarding"], missing=gaps["missing"]),
    )


@router.get("/me", response_model=TravelSnapshotResponse)
def read_my_travel(user: dict = Depends(current_user)) -> TravelSnapshotResponse:
    return _snapshot(user["id"])


@router.post("/me/visits", response_model=TravelSnapshotResponse)
def add_visit(payload: VisitRequest, user: dict = Depends(current_user)) -> TravelSnapshotResponse:
    """Record a place visited. Promotes it off the wishlist if it was there."""
    result = travel_store.add_travel_history(
        user["id"],
        location=payload.location,
        location_type=payload.location_type,
        country=payload.country,
        arrival_date=payload.arrival_date,
        departure_date=payload.departure_date,
        notes=payload.notes,
        source="user_edit",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Could not add that."))
    travel_store.resolve_wishlist(user["id"], payload.location, status="visited", source="user_edit")
    return _snapshot(user["id"])


@router.post("/me/wishlist", response_model=TravelSnapshotResponse)
def add_wishlist(
    payload: WishlistRequest, user: dict = Depends(current_user)
) -> TravelSnapshotResponse:
    result = travel_store.add_wishlist(
        user["id"],
        location=payload.location,
        location_type=payload.location_type,
        country=payload.country,
        priority=payload.priority,
        note=payload.note,
        source="user_edit",
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=400, detail=result.get("reason", "Could not add that to the wishlist.")
        )
    return _snapshot(user["id"])


@router.delete("/me/wishlist/{location}", response_model=TravelSnapshotResponse)
def drop_wishlist(location: str, user: dict = Depends(current_user)) -> TravelSnapshotResponse:
    """Drop somewhere off the wishlist. Recorded as a rejected suggestion."""
    if not travel_store.resolve_wishlist(user["id"], location, status="dropped", source="user_edit"):
        raise HTTPException(status_code=404, detail=f"{location} is not on your wishlist.")
    travel_store.record_recommendation_feedback(user["id"], location, "rejected")
    experience_store.ingest_outcome(user["id"], location, "rejected")
    return _snapshot(user["id"])


@router.post("/me/reviews", response_model=TravelSnapshotResponse)
def save_review(payload: ReviewRequest, user: dict = Depends(current_user)) -> TravelSnapshotResponse:
    """Attach a post-visit review, and feed it back into the RAG store."""
    result = travel_store.save_review(
        user["id"],
        location=payload.location,
        rating=payload.rating,
        review_notes=payload.notes,
        source="user_edit",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Could not save that."))

    # share=False keeps a review private to this account.
    experience_store.ingest_review(
        user["id"], payload.location, payload.rating, payload.notes, share=payload.share
    )
    return _snapshot(user["id"])


@router.post("/me/interests", response_model=TravelSnapshotResponse)
def set_interests(
    interests: list[str], user: dict = Depends(current_user)
) -> TravelSnapshotResponse:
    travel_store.set_interests(user["id"], interests, source="user_edit", replace=True)
    return _snapshot(user["id"])


@router.post("/me/onboarding/skip", response_model=TravelSnapshotResponse)
def skip_onboarding(user: dict = Depends(current_user)) -> TravelSnapshotResponse:
    """Let someone opt out of onboarding and go straight to the chat."""
    travel_store.set_onboarding(user["id"], status="skipped", step="done")
    return _snapshot(user["id"])


@router.get("/me/pending-reviews", response_model=list[dict[str, Any]])
def pending_reviews(user: dict = Depends(current_user)) -> list[dict[str, Any]]:
    """Places due a review prompt, for the frontend's review card."""
    return travel_store.get_pending_reviews(user["id"])
