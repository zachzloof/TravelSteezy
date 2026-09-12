"""Direct read/write access to the structured travel memory.

The conversational path can do all of this too, but a user should never be forced
to talk to an agent to correct their own data - and a marker should be able to
verify stored state without taking the chat's word for it. Same rule as
/profile/me: user_id comes from the signed token, never from a parameter.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.agents import catchup as catchup_flow
from backend.agents import onboarding as onboarding_flow
from backend.memory import store as profile_store
from backend.memory import travel as travel_store
from backend.rag import experience as experience_store
from backend.schemas import (
    CatchupStatus,
    CatchupUpdateRequest,
    ChatResponse,
    MemoryWriteEntry,
    OnboardingAnswerRequest,
    OnboardingAnswerResponse,
    OnboardingStartResponse,
    OnboardingState,
    RatingRequest,
    ReviewRequest,
    TravelEntry,
    TravelSnapshotResponse,
    TripProfile,
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


# --------------------------------------------------------------------------- #
# onboarding
#
# The welcome page asks a fixed set of questions (owned by
# backend/agents/onboarding.py) and the traveller answers each in plain text. The
# model's only job is turning one answer into structured fields; everything that
# decides what happens next is computed here from stored data.
# --------------------------------------------------------------------------- #
def _profile_model(user_id: int) -> TripProfile:
    profile = profile_store.get_profile(user_id)
    return TripProfile(**{k: v for k, v in profile.items() if k != "user_id"})


def _questions() -> list[dict[str, Any]]:
    return [dict(q) for q in onboarding_flow.QUESTIONS]


@router.get("/me/onboarding", response_model=OnboardingStartResponse)
def start_onboarding(user: dict = Depends(current_user)) -> OnboardingStartResponse:
    """The question set, plus wherever this account got to last time.

    Resumable on purpose: someone who closes the tab three questions in comes
    back to question four, with the first three already showing what was
    captured, rather than starting over.
    """
    user_id = user["id"]
    profile_store.sync_passports_from_nationality(user_id)
    state = travel_store.get_onboarding(user_id)
    if state["status"] == "not_started":
        state = travel_store.set_onboarding(user_id, status="in_progress")
    snapshot = _snapshot(user_id)
    return OnboardingStartResponse(
        questions=_questions(),
        state=snapshot.onboarding,
        next_step=onboarding_flow.next_step(state["answered"]),
        profile=_profile_model(user_id),
        travel_history=snapshot.travel_history,
        wishlist=snapshot.wishlist,
        interests=snapshot.interests,
    )


@router.post("/me/onboarding/answer", response_model=OnboardingAnswerResponse)
async def answer_onboarding(
    payload: OnboardingAnswerRequest, user: dict = Depends(current_user)
) -> OnboardingAnswerResponse:
    """Extract one plain-text answer into the profile, and say what was captured.

    The response echoes every write back so the page can show the traveller
    exactly what it understood. That echo is the point: extraction is not
    perfect, and the fix for that is showing your working immediately rather
    than hoping it was right.
    """
    user_id = user["id"]
    if onboarding_flow.get_question(payload.step) is None:
        raise HTTPException(status_code=404, detail=f"No onboarding step {payload.step!r}.")

    travel_store.set_onboarding(user_id, status="in_progress", bump_turn=True)

    note: str | None = None
    writes: list[dict[str, Any]] = []
    if not payload.skipped:
        outcome = await onboarding_flow.answer_step(user_id, payload.step, payload.text)
        writes = outcome["writes"]
        note = outcome.get("note")
        if not writes and payload.text.strip() and not note:
            note = "I could not pull anything usable out of that - add it by hand below."

    answered = travel_store.mark_step_answered(user_id, payload.step)
    following = onboarding_flow.next_step(answered)
    travel_store.set_onboarding(user_id, step=following or "done")

    snapshot = _snapshot(user_id)
    return OnboardingAnswerResponse(
        step=payload.step,
        next_step=following,
        captured=[MemoryWriteEntry(**w) for w in writes],
        note=note,
        state=snapshot.onboarding,
        profile=_profile_model(user_id),
        travel_history=snapshot.travel_history,
        wishlist=snapshot.wishlist,
        interests=snapshot.interests,
    )


@router.post("/me/onboarding/complete", response_model=TravelSnapshotResponse)
def complete_onboarding(user: dict = Depends(current_user)) -> TravelSnapshotResponse:
    """Finish onboarding from the review screen."""
    travel_store.set_onboarding(user["id"], status="complete", step="done")
    return _snapshot(user["id"])


@router.post("/me/onboarding/skip", response_model=TravelSnapshotResponse)
def skip_onboarding(user: dict = Depends(current_user)) -> TravelSnapshotResponse:
    """Let someone opt out of onboarding and go straight to the chat."""
    travel_store.set_onboarding(user["id"], status="skipped", step="done")
    return _snapshot(user["id"])


# --------------------------------------------------------------------------- #
# editing the route by hand
# --------------------------------------------------------------------------- #
@router.post("/me/history/rating", response_model=TravelSnapshotResponse)
def rate_stop(payload: RatingRequest, user: dict = Depends(current_user)) -> TravelSnapshotResponse:
    """Star-rate a place already on the route.

    Separate from POST /me/reviews because a rating with no write-up is the
    common case - it is one tap in the history panel - and forcing it through the
    review path would mean pushing an empty review into the shared RAG namespace.
    """
    if not travel_store.set_rating(user["id"], payload.location, payload.rating):
        raise HTTPException(
            status_code=404, detail=f"{payload.location} is not in your travel history."
        )
    return _snapshot(user["id"])


@router.delete("/me/history/{location}", response_model=TravelSnapshotResponse)
def remove_stop(location: str, user: dict = Depends(current_user)) -> TravelSnapshotResponse:
    """Remove a stop from the route - usually one that was auto-logged wrongly."""
    if not travel_store.remove_travel_history(user["id"], location):
        raise HTTPException(status_code=404, detail=f"{location} is not in your travel history.")
    return _snapshot(user["id"])


@router.get("/me/pending-reviews", response_model=list[dict[str, Any]])
def pending_reviews(user: dict = Depends(current_user)) -> list[dict[str, Any]]:
    """Places due a review prompt, for the frontend's review card."""
    return travel_store.get_pending_reviews(user["id"])


# --------------------------------------------------------------------------- #
# catch-up: "here's where we left off - what's changed?"
#
# Fires once per calendar-day gap since the account's last real chat turn.
# Deliberately not a conversational hijack of /chat the way the first version
# of onboarding was: it is one fixed card, shown by the frontend, cleared
# either by a free-text answer (which runs through the ordinary chat pipeline -
# it IS a normal turn, so visits/departures/wishlist/reviews are picked up for
# free) or by a one-tap "still here" button that makes no model call at all.
# --------------------------------------------------------------------------- #
@router.get("/me/catchup", response_model=CatchupStatus)
def get_catchup(user: dict = Depends(current_user)) -> CatchupStatus:
    return CatchupStatus(**catchup_flow.status(user["id"]))


@router.post("/me/catchup/dismiss", response_model=CatchupStatus)
def dismiss_catchup(user: dict = Depends(current_user)) -> CatchupStatus:
    """The quick "still here, nothing's changed" button. No model call."""
    catchup_flow.dismiss(user["id"])
    return CatchupStatus(**catchup_flow.status(user["id"]))


@router.post("/me/catchup/update", response_model=ChatResponse)
async def update_catchup(
    payload: CatchupUpdateRequest, user: dict = Depends(current_user)
) -> ChatResponse:
    """Answering the catch-up card is just a chat turn with a specific prompt.

    Reuses run_turn - and therefore the whole tracking pipeline - rather than a
    second, parallel extraction path for "what changed". run_turn itself
    touches last_active_date, which is what stops catch-up firing again today.
    """
    from backend.agents.runner import run_turn, to_chat_response

    result = await run_turn(user_id=user["id"], message=payload.message, username=user["username"])
    return to_chat_response(result)
