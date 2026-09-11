"""Registration and login for regular user accounts.

New accounts land in ``pending`` and cannot reach the chat app until an admin
approves them - unless ADMIN_AUTO_APPROVE is set, which exists so a cold marker
in incognito is never blocked waiting on a human to click approve.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.db import get_conn
from backend.memory import store
from backend.schemas import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from backend.security import (
    create_token,
    get_user_by_username,
    hash_password,
    touch_last_seen,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest) -> RegisterResponse:
    initial_status = "approved" if settings.admin_auto_approve else "pending"

    try:
        with get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, status, approved_at) "
                "VALUES (?, ?, ?, CASE WHEN ? = 'approved' THEN datetime('now') END)",
                (
                    payload.username,
                    hash_password(payload.password),
                    initial_status,
                    initial_status,
                ),
            )
            user_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="That username is already taken.") from exc

    # Give every account an (empty) profile row up front, so GET /profile/me works
    # from the very first login rather than 404-ing until the first chat turn.
    store.ensure_profile(user_id)

    if initial_status == "approved":
        return RegisterResponse(
            username=payload.username,
            status="approved",
            message="Account created and approved. You are logged in.",
            access_token=create_token(str(user_id), "user", {"username": payload.username}),
        )

    return RegisterResponse(
        username=payload.username,
        status="pending",
        message=(
            "Account created. It is awaiting admin approval - you will be able to "
            "log in once an admin approves it."
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = get_user_by_username(payload.username)

    # Verify the password even when the user is missing/unapproved would be ideal
    # for timing symmetry; we keep it simple but never reveal which half failed.
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    if user["status"] == "pending":
        raise HTTPException(
            status_code=403,
            detail="Your account is awaiting admin approval. Check back once approved.",
        )
    if user["status"] != "approved":
        raise HTTPException(
            status_code=403, detail="This account has been rejected by an admin."
        )

    touch_last_seen(user["id"])
    store.ensure_profile(user["id"])
    return TokenResponse(
        access_token=create_token(str(user["id"]), "user", {"username": user["username"]}),
        username=user["username"],
        status=user["status"],
    )
