"""In-app bug reports.

A traveller taps "Report a bug", says what went wrong, and this stores a
ready-to-paste trace - the report plus their recent conversation turns plus a
Langfuse link if one is available - for the admin (the developer) to read in
the admin panel and hand straight to Claude Code. No screenshots, no outbound
email, no new external service to configure.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.db import get_conn
from backend.schemas import BugReportCreate, BugReportCreated
from backend.security import current_user
from backend.tracing.langfuse_setup import trace_url

router = APIRouter(prefix="/bugs", tags=["bugs"])

# Enough for the reporter's own last few turns of context, not the whole
# conversation - conversation_turns is already capped at working_memory_turns.
RECENT_TURNS = 12


def _format_trace_text(
    *,
    report_id: int,
    created_at: str,
    username: str,
    description: str,
    page: str | None,
    user_agent: str | None,
    trace_id: str | None,
    url: str | None,
    turns: list[dict],
) -> str:
    lines = [
        f"Bug report #{report_id} -- {created_at} UTC",
        f"User: {username}",
        f"Page: {page or 'unknown'}",
        f"Browser: {user_agent or 'unknown'}",
    ]
    if trace_id:
        lines.append(f"Langfuse trace: {url or trace_id}")
    lines += ["", "What went wrong (reported by the user):", description.strip()]
    if turns:
        lines += ["", f"Recent conversation (last {len(turns)} turns):"]
        lines += [f"[{t['role']}] {t['content']}" for t in turns]
    return "\n".join(lines)


@router.post("", response_model=BugReportCreated)
def report_bug(payload: BugReportCreate, user: dict = Depends(current_user)) -> BugReportCreated:
    url = trace_url(payload.trace_id)
    with get_conn() as conn:
        turn_rows = conn.execute(
            "SELECT role, content FROM conversation_turns WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (user["id"], RECENT_TURNS),
        ).fetchall()
        turns = [dict(r) for r in reversed(turn_rows)]

        created_at = conn.execute("SELECT datetime('now') AS now").fetchone()["now"]

        cur = conn.execute(
            "INSERT INTO bug_reports "
            "(user_id, username, description, page, user_agent, trace_id, trace_url, "
            " trace_text, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                user["id"],
                user["username"],
                payload.description.strip(),
                payload.page,
                payload.user_agent,
                payload.trace_id,
                url,
                "",
                created_at,
            ),
        )
        report_id = cur.lastrowid
        trace_text = _format_trace_text(
            report_id=report_id,
            created_at=created_at,
            username=user["username"],
            description=payload.description,
            page=payload.page,
            user_agent=payload.user_agent,
            trace_id=payload.trace_id,
            url=url,
            turns=turns,
        )
        conn.execute("UPDATE bug_reports SET trace_text = ? WHERE id = ?", (trace_text, report_id))

    return BugReportCreated(id=report_id, created_at=created_at)
