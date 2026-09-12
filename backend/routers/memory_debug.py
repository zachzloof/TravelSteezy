"""The memory debug page: read everything, delete anything.

This is not a marketing feature - it exists because building the memory
system surfaced a real need, articulated directly: "a page that is solely for
the memory of the AI, here you can delete information, and read it... shows
what is being fed into each conversation."

Two things make this different from My Preferences, which already lets someone
edit their own profile:

1. It shows the EXACT text (``memory_block`` / ``travel_block``) that gets
   spliced into every agent prompt, computed live by the same two functions the
   real chat turn uses - not a paraphrase of it. If the assistant is behaving
   as though it does not know something, this is where to check whether that
   something was actually in the prompt at all.
2. It exposes rows nothing else shows: raw trip_profile columns including
   deprecated ones, interest weights, the onboarding answered-list, and (read
   with a fetch, not a claim) which reviews have actually reached the shared
   RAG experience store.

Every route here is scoped to the caller's own account via ``current_user``,
the same as every other route in this app - there is no cross-account access
and no admin-only gate, because this is the user's OWN memory.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.memory import store, travel
from backend.rag import experience as experience_store
from backend.schemas import MemoryDebugResponse
from backend.security import current_user

router = APIRouter(prefix="/memory", tags=["memory-debug"])


def _snapshot(user_id: int) -> MemoryDebugResponse:
    profile_snapshot = store.get_memory_snapshot(user_id)
    travel_snapshot = travel.get_travel_snapshot(user_id)
    return MemoryDebugResponse(
        memory_block=store.format_profile_for_prompt(profile_snapshot),
        travel_block=travel.format_travel_for_prompt(travel_snapshot),
        profile_row=store.get_raw_profile_row(user_id),
        passports=store.get_passports(user_id),
        travel_history=travel.get_travel_history(user_id),
        wishlist=travel.get_wishlist(user_id, status="all"),
        interests=travel.get_interests_with_weight(user_id),
        onboarding_state=travel.get_onboarding(user_id),
        recommendation_feedback=travel.get_recommendation_feedback(user_id),
        memory_writes=store.get_write_log(user_id, limit=200),
        conversation_turns=store.get_recent_turns(user_id),
        published_experience_documents=experience_store.list_own_documents(user_id),
    )


@router.get("/me", response_model=MemoryDebugResponse)
def read_my_memory(user: dict = Depends(current_user)) -> MemoryDebugResponse:
    return _snapshot(user["id"])


@router.delete("/me/interests/{interest}", response_model=MemoryDebugResponse)
def delete_interest(interest: str, user: dict = Depends(current_user)) -> MemoryDebugResponse:
    if not travel.remove_interest(user["id"], interest):
        raise HTTPException(status_code=404, detail=f"{interest!r} is not stored.")
    return _snapshot(user["id"])


@router.delete("/me/passports/{country}", response_model=MemoryDebugResponse)
def delete_passport(country: str, user: dict = Depends(current_user)) -> MemoryDebugResponse:
    before = store.get_passports(user["id"])
    after = store.remove_passport(user["id"], country)
    if after == before:
        raise HTTPException(status_code=404, detail=f"{country!r} is not on file.")
    return _snapshot(user["id"])


@router.delete("/me/profile-field/{field}", response_model=MemoryDebugResponse)
def clear_profile_field(field: str, user: dict = Depends(current_user)) -> MemoryDebugResponse:
    """Blank one field of the raw trip_profile row directly."""
    store.clear_profile_fields(user["id"], [field])
    return _snapshot(user["id"])


@router.post("/me/onboarding/reset", response_model=MemoryDebugResponse)
def reset_onboarding(user: dict = Depends(current_user)) -> MemoryDebugResponse:
    """Send this account back through the welcome page's questions.

    Leaves the route, wishlist, interests and passports untouched - this is
    "let me redo the interview", not "forget everything" (that is
    DELETE /profile/me, which this page also exposes).
    """
    travel.reset_onboarding(user["id"])
    return _snapshot(user["id"])
