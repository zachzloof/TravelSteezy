"""The user-facing read/write path into the memory store.

GET /profile/me exists so that "the assistant remembers me" is independently
verifiable - a user (or a marker) can check the stored state directly rather than
taking the chat reply's word for it.

Every route here derives user_id from the signed token, never from a parameter,
so account A physically cannot address account B's row.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.memory import store
from backend.schemas import (
    DepartureRequest,
    MemoryWriteEntry,
    ProfilePatch,
    ProfileResponse,
    TripProfile,
    VisitedEntry,
)
from backend.security import current_user

router = APIRouter(prefix="/profile", tags=["profile"])


def _build_response(user: dict[str, Any]) -> ProfileResponse:
    snapshot = store.get_memory_snapshot(user["id"])
    return ProfileResponse(
        username=user["username"],
        profile=TripProfile(**{k: v for k, v in snapshot["profile"].items() if k != "user_id"}),
        visited_history=[VisitedEntry(**v) for v in snapshot["visited_history"]],
        recent_writes=[MemoryWriteEntry(**w) for w in store.get_write_log(user["id"], limit=15)],
    )


@router.get("/me", response_model=ProfileResponse)
def read_my_profile(user: dict = Depends(current_user)) -> ProfileResponse:
    return _build_response(user)


@router.patch("/me", response_model=ProfileResponse)
def patch_my_profile(
    patch: ProfilePatch, user: dict = Depends(current_user)
) -> ProfileResponse:
    # exclude_unset: a PATCH must only touch fields the user actually submitted,
    # otherwise the My Preferences form would blank out everything it did not show.
    updates = patch.model_dump(exclude_unset=True, exclude_none=True)
    store.update_profile(user["id"], updates, source="user_edit")
    return _build_response(user)


@router.post("/me/departures", response_model=ProfileResponse)
def log_my_departure(
    payload: DepartureRequest, user: dict = Depends(current_user)
) -> ProfileResponse:
    """Explicit 'I have left this country' - the user-driven twin of the agent tool."""
    store.log_departure(
        user["id"],
        country=payload.country,
        departure_date=payload.departure_date,
        arrival_date=payload.arrival_date,
        notes=payload.notes,
        source="user_edit",
    )
    return _build_response(user)


@router.delete("/me", response_model=ProfileResponse)
def forget_me(user: dict = Depends(current_user)) -> ProfileResponse:
    """User-triggered forgetting: wipe this account's memory, keep the account."""
    store.forget_account_memory(user["id"])
    return _build_response(user)
