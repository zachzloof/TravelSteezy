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
from backend.memory import travel as travel_store
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
    # Backfills the passport table from `nationality` for an account created
    # before passports were a separate thing, so an existing traveller sees the
    # passport they already told us about rather than an empty panel.
    store.sync_passports_from_nationality(user["id"])
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

    # Passports and social_style are not trip_profile columns the generic writer
    # handles: passports are their own table, and social_style has its own
    # validated setter. Both are pulled out before update_profile sees them.
    passports = updates.pop("passports", None)
    social_style = updates.pop("social_style", None)
    clear = updates.pop("clear", None)

    if clear:
        store.clear_profile_fields(user["id"], clear, source="user_edit")
    if updates:
        store.update_profile(user["id"], updates, source="user_edit")
    if passports is not None:
        store.set_passports(user["id"], passports, source="user_edit")
    if social_style:
        travel_store.set_social_style(user["id"], social_style, source="user_edit")
    elif clear and "social_style" in clear:
        travel_store.clear_social_style(user["id"], source="user_edit")
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
