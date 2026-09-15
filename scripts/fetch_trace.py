"""Print a Langfuse trace by id, for working a bug report from the outside.

Every bug report submitted in-app carries the Langfuse trace URL for the turn
that went wrong (see backend/routers/bugs.py), but reading it means opening the
Langfuse UI and clicking through the span tree. This prints the same trace as
text: the turn's input and output, then every observation in order with its
name, model, latency, input and output. That is enough to answer the questions
a bug report actually turns on - which intent the turn was routed to, what the
turn parser extracted, what the tools returned, which origin an agent passed to
a tool - without leaving the terminal.

Reads LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST from the
environment or .env, the same three settings the app itself uses for tracing.
The keys are used to sign the request and are never printed.

    python -m scripts.fetch_trace 03466b5fc74eb8b8b55191d0e99406ed
    python -m scripts.fetch_trace <url-or-id> --full      # no truncation
    python -m scripts.fetch_trace <url-or-id> --json      # raw API response
    python -m scripts.fetch_trace <url-or-id> --session   # every turn in its session

``--session`` exists because a bug report names the turn where the traveller
noticed, which is rarely the turn where the app went wrong - bug report #3's
reported turn was four turns downstream of the write that caused it. It lists
the whole conversation newest-first with each turn's id, so the earlier ones
can be opened directly.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from backend.config import settings  # noqa: E402

TRUNCATE = 1200


def trace_id_from(value: str) -> str:
    """Accept a bare id or a full Langfuse URL - bug reports carry the URL."""
    value = (value or "").strip().rstrip("/")
    if "/traces/" in value:
        value = value.split("/traces/", 1)[1]
    return value.split("?", 1)[0]


def shorten(value: Any, limit: int) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = text.strip()
    if limit and len(text) > limit:
        return text[:limit] + f"... [{len(text) - limit} more chars]"
    return text


def fetch(trace_id: str) -> dict[str, Any]:
    if not settings.langfuse_enabled:
        raise SystemExit(
            "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are not set - add them to .env "
            "(same values as the deployment) and try again."
        )
    url = f"{settings.langfuse_host.rstrip('/')}/api/public/traces/{trace_id}"
    response = httpx.get(
        url,
        auth=(settings.langfuse_public_key or "", settings.langfuse_secret_key or ""),
        timeout=30.0,
    )
    if response.status_code == 401:
        raise SystemExit("Langfuse rejected the credentials (401). Check the key pair and host.")
    if response.status_code == 404:
        raise SystemExit(f"No trace {trace_id} on {settings.langfuse_host} for this project.")
    response.raise_for_status()
    return response.json()


def fetch_session(session_id: str, limit: int = 30) -> list[dict[str, Any]]:
    """Every trace in one chat session, newest first."""
    url = f"{settings.langfuse_host.rstrip('/')}/api/public/traces"
    response = httpx.get(
        url,
        params={"sessionId": session_id, "limit": limit},
        auth=(settings.langfuse_public_key or "", settings.langfuse_secret_key or ""),
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json().get("data") or []


def render_session(traces: list[dict[str, Any]], session_id: str) -> None:
    print("=" * 78)
    print(f"session {session_id}: {len(traces)} turn(s), newest first")
    print("=" * 78)
    for trace in traces:
        message = trace.get("input")
        if isinstance(message, dict):
            message = message.get("message")
        print(f"{trace.get('timestamp')}  {trace.get('id')}")
        print(f"    user : {shorten(message, 140)}")
        reply = trace.get("output")
        if isinstance(reply, dict):
            reply = reply.get("reply")
        print(f"    reply: {shorten(reply, 140)}")


def render(trace: dict[str, Any], limit: int) -> None:
    print("=" * 78)
    print(f"trace      : {trace.get('name')}  ({trace.get('id')})")
    print(f"timestamp  : {trace.get('timestamp')}")
    print(f"user/session: {trace.get('userId')} / {trace.get('sessionId')}")
    if trace.get("tags"):
        print(f"tags       : {', '.join(trace['tags'])}")
    print(f"latency    : {trace.get('latency')}")
    print("-" * 78)
    print("INPUT :", shorten(trace.get("input"), limit))
    print("OUTPUT:", shorten(trace.get("output"), limit))

    observations = trace.get("observations") or []
    print("-" * 78)
    print(f"{len(observations)} observation(s)")
    for index, obs in enumerate(observations, start=1):
        print("=" * 78)
        head = f"[{index}] {obs.get('name')}  ({obs.get('type')})"
        if obs.get("model"):
            head += f"  model={obs['model']}"
        if obs.get("latency") is not None:
            head += f"  {obs['latency']}s"
        if obs.get("level") and obs["level"] != "DEFAULT":
            head += f"  level={obs['level']}"
        print(head)
        if obs.get("statusMessage"):
            print("  status:", obs["statusMessage"])
        if obs.get("input") is not None:
            print("  in :", shorten(obs.get("input"), limit))
        if obs.get("output") is not None:
            print("  out:", shorten(obs.get("output"), limit))


def main() -> None:
    # Traveller messages contain whatever the traveller typed - place names with
    # macrons, emoji, curly quotes. The Windows console defaults to cp1252 and
    # dies on all three, which is a silly way to lose a bug investigation.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover - non-reconfigurable stream
        pass

    parser = argparse.ArgumentParser(description="Print one Langfuse trace as text.")
    parser.add_argument("trace", help="Trace id, or the full trace URL from a bug report.")
    parser.add_argument("--full", action="store_true", help="Do not truncate long values.")
    parser.add_argument("--json", action="store_true", help="Print the raw API response instead.")
    parser.add_argument(
        "--session",
        action="store_true",
        help="List every turn in this trace's session instead of the trace itself.",
    )
    args = parser.parse_args()

    trace = fetch(trace_id_from(args.trace))
    if args.session:
        session_id = trace.get("sessionId")
        if not session_id:
            raise SystemExit("That trace carries no sessionId.")
        render_session(fetch_session(session_id), session_id)
        return
    if args.json:
        print(json.dumps(trace, indent=2, ensure_ascii=False, default=str))
        return
    render(trace, 0 if args.full else TRUNCATE)


if __name__ == "__main__":
    main()
