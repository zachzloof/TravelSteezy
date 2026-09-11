"""Password hashing, JWT issuing/verification, and FastAPI auth dependencies.

Passwords are bcrypt-hashed via passlib and never stored in plaintext. The admin
identity is separate from user accounts entirely: it is not a row in ``users``, it
is a password checked against the ADMIN_PASSWORD environment variable.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import settings
from backend.db import get_conn

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# auto_error=False so we can return our own 401 body rather than FastAPI's default.
bearer_scheme = HTTPBearer(auto_error=False)

TokenKind = Literal["user", "admin"]


# --------------------------------------------------------------------------- #
# passwords
# --------------------------------------------------------------------------- #
def hash_password(plain: str) -> str:
    # bcrypt silently truncates past 72 bytes; reject instead of hashing a prefix.
    if len(plain.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password must be 72 bytes or fewer.")
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


# --------------------------------------------------------------------------- #
# tokens
# --------------------------------------------------------------------------- #
def create_token(subject: str, kind: TokenKind, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "kind": kind,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.jwt_ttl_hours)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token."
        ) from exc


# --------------------------------------------------------------------------- #
# user lookups
# --------------------------------------------------------------------------- #
def get_user_by_username(username: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def touch_last_seen(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_seen_at = datetime('now') WHERE id = ?", (user_id,)
        )


# --------------------------------------------------------------------------- #
# FastAPI dependencies
# --------------------------------------------------------------------------- #
def _credentials_or_401(
    creds: HTTPAuthorizationCredentials | None,
) -> HTTPAuthorizationCredentials:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated."
        )
    return creds


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Resolve the logged-in, approved user from the bearer token.

    Every per-account route depends on this, which is what makes cross-account
    access impossible: the user_id comes from the signed token, never from a
    path/query parameter the caller controls.
    """
    creds = _credentials_or_401(creds)
    payload = decode_token(creds.credentials)
    if payload.get("kind") != "user":
        raise HTTPException(status_code=403, detail="Not a user token.")

    user = get_user_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    if user["status"] != "approved":
        raise HTTPException(
            status_code=403,
            detail="Your account is awaiting admin approval.",
        )
    return user


def current_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Resolve the admin identity. Admin tokens are a separate ``kind``, so a
    regular user's token can never satisfy this dependency."""
    creds = _credentials_or_401(creds)
    payload = decode_token(creds.credentials)
    if payload.get("kind") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return {"admin": True, "sub": payload.get("sub")}
