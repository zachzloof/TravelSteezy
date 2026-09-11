"""The /chat endpoint.

Runs the ADK agent graph against the authenticated user's own memory. The user id
comes from the signed token, so a turn can only ever read and write the caller's
own profile - which is the mechanism behind the cross-account isolation eval.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.agents.runner import run_turn
from backend.schemas import (
    AgentTrace,
    ChatRequest,
    ChatResponse,
    DestinationVerdict,
    MemoryWriteEntry,
    TripProfile,
    VisitedEntry,
)
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

    profile = {k: v for k, v in (result.get("profile") or {}).items() if k != "user_id"}
    return ChatResponse(
        reply=result["reply"],
        comparison=[DestinationVerdict(**c) for c in result.get("comparison", [])],
        agents_fired=[AgentTrace(**a) for a in result.get("agents_fired", [])],
        memory_writes=[MemoryWriteEntry(**w) for w in result.get("memory_writes", [])],
        retrieved_sources=result.get("retrieved_sources", []),
        trace_id=result.get("trace_id"),
        profile=TripProfile(**profile) if profile else None,
        visited_history=[VisitedEntry(**v) for v in result.get("visited_history", [])],
    )
