"""The /chat endpoint.

Runs the ADK agent graph against the authenticated user's own memory. The user id
comes from the signed token, so a turn can only ever read and write the caller's
own profile - which is the mechanism behind the cross-account isolation eval.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.agents.runner import run_turn, to_chat_response
from backend.schemas import ChatRequest, ChatResponse
from backend.security import current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user: dict = Depends(current_user)) -> ChatResponse:
    try:
        result = await run_turn(
            user_id=user["id"], message=payload.message, username=user["username"]
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("chat turn failed for user %s", user["id"])
        raise HTTPException(
            status_code=502, detail=f"The agent graph failed on this turn: {exc}"
        ) from exc

    return to_chat_response(result)
