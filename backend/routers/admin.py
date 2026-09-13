"""Admin-only routes: approve/reject pending accounts.

Admin auth is deliberately separate from user auth. There is no admin row in the
``users`` table; the admin logs in with ADMIN_PASSWORD (env var only, never in
source) and receives a token of kind ``admin``. A regular user's token cannot
satisfy the ``current_admin`` dependency, so /admin/* is invisible to them.
"""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, HTTPException

from backend.config import settings
from backend.db import get_conn
from backend.schemas import (
    AdminActionResponse,
    AdminLoginRequest,
    BugReportAdmin,
    PendingUser,
    TokenResponse,
)
from backend.security import create_token, current_admin, get_user_by_id

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=TokenResponse)
def admin_login(payload: AdminLoginRequest) -> TokenResponse:
    if not settings.admin_password:
        raise HTTPException(
            status_code=503,
            detail="Admin access is not configured on this deployment (ADMIN_PASSWORD unset).",
        )
    # compare_digest to avoid leaking the password length/prefix via timing.
    if not hmac.compare_digest(payload.password, settings.admin_password):
        raise HTTPException(status_code=401, detail="Incorrect admin password.")

    return TokenResponse(
        access_token=create_token("admin", "admin"), username="admin", status="admin"
    )


@router.get("/pending", response_model=list[PendingUser])
def list_pending(_: dict = Depends(current_admin)) -> list[PendingUser]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, status, created_at, last_seen_at FROM users "
            "WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
    return [PendingUser(**dict(r)) for r in rows]


@router.get("/users", response_model=list[PendingUser])
def list_all_users(_: dict = Depends(current_admin)) -> list[PendingUser]:
    """Full roster, so the admin panel can show approved/rejected accounts too."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, status, created_at, last_seen_at FROM users "
            "ORDER BY id ASC"
        ).fetchall()
    return [PendingUser(**dict(r)) for r in rows]


def _set_status(user_id: int, new_status: str) -> AdminActionResponse:
    if get_user_by_id(user_id) is None:
        raise HTTPException(status_code=404, detail="No such user.")
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET status = ?, approved_at = CASE WHEN ? = 'approved' "
            "THEN datetime('now') ELSE approved_at END WHERE id = ?",
            (new_status, new_status, user_id),
        )
    user = get_user_by_id(user_id)
    assert user is not None
    return AdminActionResponse(id=user["id"], username=user["username"], status=user["status"])


@router.post("/approve/{user_id}", response_model=AdminActionResponse)
def approve(user_id: int, _: dict = Depends(current_admin)) -> AdminActionResponse:
    return _set_status(user_id, "approved")


@router.post("/reject/{user_id}", response_model=AdminActionResponse)
def reject(user_id: int, _: dict = Depends(current_admin)) -> AdminActionResponse:
    return _set_status(user_id, "rejected")


# --------------------------------------------------------------------------- #
# bug reports (see backend/routers/bugs.py for how a report is created)
# --------------------------------------------------------------------------- #
@router.get("/bugs", response_model=list[BugReportAdmin])
def list_bugs(_: dict = Depends(current_admin)) -> list[BugReportAdmin]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, description, page, status, created_at, trace_url, trace_text "
            "FROM bug_reports ORDER BY id DESC"
        ).fetchall()
    return [BugReportAdmin(**dict(r)) for r in rows]


@router.post("/bugs/{report_id}/resolve", response_model=BugReportAdmin)
def toggle_bug_resolved(report_id: int, _: dict = Depends(current_admin)) -> BugReportAdmin:
    with get_conn() as conn:
        row = conn.execute("SELECT status FROM bug_reports WHERE id = ?", (report_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="No such bug report.")
        new_status = "resolved" if row["status"] == "open" else "open"
        conn.execute("UPDATE bug_reports SET status = ? WHERE id = ?", (new_status, report_id))
        row = conn.execute(
            "SELECT id, username, description, page, status, created_at, trace_url, trace_text "
            "FROM bug_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
    return BugReportAdmin(**dict(row))
