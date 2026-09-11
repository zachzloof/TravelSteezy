"""Turn orchestration: the code path a single /chat request takes.

    read memory  ->  parse turn  ->  EXPLICIT memory writes  ->  re-read memory
                 ->  fan out to specialists  ->  decision weigher  ->  response

The memory writes are plain Python calls to backend.memory.store made here by the
orchestrator, immediately after parsing the turn. They are not a side effect
hidden inside a prompt, which is what the syllabus asks for and what makes the
write path pointable-at in a demo.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.agents import coverage, graph
from backend.agents.tools import ToolRecorder, reset_recorder, set_recorder
from backend.config import settings
from backend.memory import store
from backend.rag import store as rag_store
from backend.tracing.langfuse_setup import Trace

logger = logging.getLogger(__name__)


class _DropAppNameMismatch(logging.Filter):
    """ADK infers an "app name" from the root agent's module path and warns when it
    differs from the Runner's. We build agents dynamically from this package, so the
    warning fires on every turn and means nothing. Drop just that one message."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "App name mismatch detected" not in record.getMessage()


for _name in ("google_adk.google.adk.runners", "google.adk.runners", "google_adk"):
    logging.getLogger(_name).addFilter(_DropAppNameMismatch())


# Every state key referenced by an agent instruction must exist before the run,
# otherwise ADK's template resolution fails on the missing key.
STATE_KEYS = (
    "memory_block", "user_question", "candidates", "travel_month", "today",
    "nationality", "current_location", "budget_band", "travel_style", "interests",
    "weather_assessment", "logistics_assessment", "recommendations",
    "turn_parse", "decision", "concierge_reply", "coverage_note", "deadline_note",
)


async def _run_agent(
    agent: LlmAgent,
    state: dict[str, Any],
    message: str,
    user_id: str,
    session_id: str,
) -> tuple[str, dict[str, Any], list[str]]:
    """Run one agent (or pipeline) and return its text, final state and tool calls."""
    session_service = InMemorySessionService()
    seeded = {key: "" for key in STATE_KEYS}
    seeded.update({k: ("" if v is None else str(v)) for k, v in state.items()})

    await session_service.create_session(
        app_name=graph.APP_NAME, user_id=user_id, session_id=session_id, state=seeded
    )
    # Pass an explicit App so ADK does not infer an app name from the module
    # path of whichever agent class happens to be the root (which logs a warning).
    runner = Runner(
        app=App(name=graph.APP_NAME, root_agent=agent), session_service=session_service
    )

    final_text = ""
    tool_calls: list[str] = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=message)]),
    ):
        for call in event.get_function_calls() or []:
            tool_calls.append(call.name)
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            if text.strip():
                final_text = text

    session = await session_service.get_session(
        app_name=graph.APP_NAME, user_id=user_id, session_id=session_id
    )
    return final_text, dict(session.state if session else {}), tool_calls


# --------------------------------------------------------------------------- #
# parsing + the explicit write step
# --------------------------------------------------------------------------- #
def _apply_memory_writes(user_id: int, parse: dict[str, Any]) -> list[dict[str, Any]]:
    """THE WRITE PATH. Explicit calls, one per thing the user told us."""
    writes: list[dict[str, Any]] = []

    updates = parse.get("profile_updates") or {}
    if isinstance(updates, dict) and updates:
        store.update_profile(user_id, updates, source="agent")
        writes.append({"operation": "update_profile", "payload": updates, "source": "agent"})

    for departure in parse.get("departures") or []:
        if not isinstance(departure, dict):
            continue
        country = departure.get("country")
        if not country:
            continue
        store.log_departure(
            user_id,
            country=country,
            departure_date=departure.get("departure_date"),
            source="agent",
        )
        writes.append(
            {
                "operation": "log_departure",
                "payload": {"country": country, "departure_date": departure.get("departure_date")},
                "source": "agent",
            }
        )
    return writes


def _fallback_parse(message: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Used when the parser agent fails or returns unusable JSON.

    Keeps the turn alive with a best-effort plan rather than 500-ing.
    """
    destinations = rag_store.detect_destinations(message)
    profile = snapshot.get("profile", {})
    return {
        "profile_updates": {},
        "departures": [],
        "candidate_destinations": destinations,
        "travel_month": profile.get("trip_start_date") or date.today().isoformat(),
        "question_focus": message[:80],
        "needs_weather": bool(destinations),
        "needs_logistics": bool(destinations),
        "needs_recommendations": bool(destinations),
        "is_small_talk": not destinations,
        "_fallback": True,
    }


def _coerce_cards(raw: Any) -> list[dict[str, Any]]:
    """Normalise the weigher's card list, dropping anything unusable."""
    if not isinstance(raw, list):
        return []
    cards: list[dict[str, Any]] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict) or not item.get("destination"):
            continue

        def clean(key: str) -> str | None:
            value = item.get(key)
            if value is None:
                return None
            text = str(value).strip()
            # Models sometimes echo the field name back ("visa_flag": "visa_flag")
            # or emit a JSON null as a string. Neither is content.
            if text.lower() in {"", "null", "none", "n/a", key.lower()}:
                return None
            return text

        def clean_list(key: str) -> list[str]:
            value = item.get(key)
            if isinstance(value, list):
                return [str(v).strip() for v in value if str(v).strip()]
            if isinstance(value, str) and value.strip():
                return [value.strip()]
            return []

        cards.append(
            {
                "destination": str(item["destination"]).strip(),
                "rank": int(item["rank"]) if str(item.get("rank", "")).isdigit() else index,
                "verdict": (clean("verdict") or "maybe").lower(),
                "rationale": clean("rationale"),
                "pros": clean_list("pros"),
                "cons": clean_list("cons"),
                "season_flag": clean("season_flag"),
                "visa_flag": clean("visa_flag"),
                "est_cost_note": clean("est_cost_note"),
                "backpacker_notes": clean_list("backpacker_notes"),
                "source_ids": clean_list("source_ids"),
            }
        )
    cards.sort(key=lambda c: c["rank"])
    return cards


# --------------------------------------------------------------------------- #
# main entry point
# --------------------------------------------------------------------------- #
async def run_turn(user_id: int, message: str, username: str = "") -> dict[str, Any]:
    """Run one full conversational turn for one account."""
    trace = Trace(
        name="onward.turn",
        user_id=str(user_id),
        session_id=f"user-{user_id}",
        input={"message": message},
        tags=["chat"],
        metadata={"username": username},
    )
    recorder = ToolRecorder()
    token = set_recorder(recorder)

    try:
        if not settings.llm_enabled:
            return _llm_disabled_response(user_id, message, trace)

        # ---- 1. HOW WE RETRIEVE: read memory at the top of every turn --------
        with trace.span("memory.read"):
            snapshot = store.get_memory_snapshot(user_id)
            memory_block = store.format_profile_for_prompt(snapshot)
        trace.set_span_summary("memory.read", f"{len(snapshot['visited_history'])} visited entries")

        base_state = {
            "memory_block": memory_block,
            "user_question": message,
            "today": date.today().isoformat(),
        }

        # ---- 2. parse the turn ----------------------------------------------
        parse: dict[str, Any] = {}
        with trace.span("agent.turn_parser", input={"message": message}):
            try:
                text, _, _ = await _run_agent(
                    graph.make_turn_parser(), base_state, message,
                    str(user_id), f"parse-{user_id}",
                )
                parse = graph.parse_json_block(text) or {}
            except Exception as exc:  # noqa: BLE001
                logger.warning("turn_parser failed: %s", exc)
                parse = {}
        if not parse:
            parse = _fallback_parse(message, snapshot)
            trace.set_span_summary("agent.turn_parser", "fell back to heuristic parse")

        # ---- 3. WHEN WE WRITE: explicit memory writes ------------------------
        with trace.span("memory.write", input=parse.get("profile_updates")):
            writes = _apply_memory_writes(user_id, parse)
        trace.set_span_summary("memory.write", f"{len(writes)} write(s)")

        # ---- 4. re-read so specialists see what we just learned --------------
        snapshot = store.get_memory_snapshot(user_id)
        profile = snapshot["profile"]
        base_state["memory_block"] = store.format_profile_for_prompt(snapshot)

        candidates = [
            str(c).strip().lower()
            for c in (parse.get("candidate_destinations") or [])
            if str(c).strip()
        ]
        travel_month = parse.get("travel_month") or profile.get("trip_start_date") or ""

        state = {
            **base_state,
            "candidates": ", ".join(candidates) if candidates else "(none named)",
            "travel_month": travel_month,
            "nationality": profile.get("nationality") or "(unknown)",
            "current_location": profile.get("current_location") or "(unknown)",
            "budget_band": profile.get("budget_band") or "(unknown)",
            "travel_style": profile.get("travel_style") or "(unknown)",
            "interests": profile.get("interests") or "(unknown)",
            # Deterministic guard computed in code, not left to the model.
            "coverage_note": coverage.coverage_note(candidates),
            "deadline_note": coverage.deadline_note(profile),
        }

        # ---- 5. dispatch ------------------------------------------------------
        small_talk = bool(parse.get("is_small_talk")) or not candidates
        if small_talk:
            reply, cards, fired = await _run_concierge(state, message, user_id, trace)
        else:
            reply, cards, fired = await _run_comparison(state, message, user_id, parse, trace)

        # ---- 6. persist the turn ---------------------------------------------
        store.append_turn(user_id, "user", message)
        store.append_turn(user_id, "assistant", reply)

        trace.end(output={"reply": reply, "cards": len(cards)})
        return {
            "reply": reply,
            "comparison": cards,
            "agents_fired": trace.spans,
            "memory_writes": writes,
            "retrieved_sources": recorder.retrieved,
            "trace_id": trace.id,
            "trace_url": trace.url,
            "tool_calls": recorder.tool_names,
            "profile": profile,
            "visited_history": snapshot["visited_history"],
            "specialists": fired,
        }
    finally:
        reset_recorder(token)


async def _run_concierge(
    state: dict[str, Any], message: str, user_id: int, trace: Trace
) -> tuple[str, list[dict[str, Any]], list[str]]:
    with trace.span("agent.concierge"):
        text, _, _ = await _run_agent(
            graph.make_concierge(), state, message, str(user_id), f"concierge-{user_id}"
        )
    return text.strip() or "I'm not sure how to help with that yet.", [], ["concierge"]


async def _run_one_specialist(
    agent: LlmAgent,
    key: str,
    state: dict[str, Any],
    message: str,
    user_id: int,
    trace: Trace,
    parent_span: Any = None,
) -> tuple[str, str, list[str], str | None]:
    """Run one specialist. Never raises: a failure is reported, not propagated.

    Opens its own Langfuse span nested under the fan-out, and emits a child span
    per tool call, so the trace tree shows which specialist called what.
    """
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            with trace.span(
                agent.name,
                parent=parent_span,
                input={"candidates": state.get("candidates"), "attempt": attempt},
            ) as span_handle:
                text, final_state, tool_calls = await _run_agent(
                    agent, state, message, str(user_id), f"{agent.name}-{user_id}-{attempt}"
                )
                output = str(final_state.get(key) or text or "")
                for tool_name in tool_calls:
                    trace.tool_span(span_handle, tool_name)
                try:
                    span_handle.end(output=output[:2000])
                except Exception:  # noqa: BLE001
                    pass

            trace.set_span_summary(agent.name, output[:180] or "(no output)")
            if output.strip():
                return key, output, tool_calls, None
            last_error = RuntimeError("specialist produced no output")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "specialist %s attempt %d failed: %s", agent.name, attempt, exc
            )
    return key, "", [], f"{type(last_error).__name__}: {last_error}"


async def _run_comparison(
    state: dict[str, Any],
    message: str,
    user_id: int,
    parse: dict[str, Any],
    trace: Trace,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Stage 1: run the relevant specialists concurrently.
    Stage 2: hand their reports to the Decision-Weigher.
    """
    specialists = graph.build_specialists(
        needs_weather=parse.get("needs_weather", True) is not False,
        needs_logistics=parse.get("needs_logistics", True) is not False,
        needs_recommendations=parse.get("needs_recommendations", True) is not False,
    )
    names = [agent.name for agent, _ in specialists]

    # ---- stage 1: parallel fan-out ----------------------------------------
    with trace.span("agents.fan_out", metadata={"specialists": names}) as fan_span:
        outcomes = await asyncio.gather(
            *(
                _run_one_specialist(
                    agent, key, state, message, user_id, trace, fan_span
                )
                for agent, key in specialists
            )
        )

    reports: dict[str, str] = {
        "weather_assessment": "",
        "logistics_assessment": "",
        "recommendations": "",
    }
    all_tool_calls: list[str] = []
    failures: list[str] = []
    for (agent, _), (key, output, tool_calls, error) in zip(specialists, outcomes):
        reports[key] = output
        all_tool_calls.extend(tool_calls)
        if error:
            failures.append(f"{agent.name}: {error}")
            # The span itself was already recorded by _run_one_specialist; just
            # mark the failure so the UI panel shows it.
            trace.set_span_status(agent.name, "error", error)

    summary = f"{', '.join(names)}; {len(all_tool_calls)} tool call(s)"
    if failures:
        summary += f"; {len(failures)} failed"
    trace.set_span_summary("agents.fan_out", summary)

    # ---- stage 2: decision weigher ----------------------------------------
    weigher_state = {**state, **reports}
    cards: list[dict[str, Any]] = []
    reply = ""
    text = ""
    with trace.span(
        "agent.decision_weigher",
        input={k: v[:400] for k, v in reports.items() if v},
    ):
        # One retry: the weigher occasionally answers in prose instead of JSON,
        # which would otherwise cost the user their whole comparison.
        for attempt in (1, 2):
            try:
                text, final_state, _ = await _run_agent(
                    graph.make_decision_weigher(), weigher_state, message,
                    str(user_id), f"weigh-{user_id}-{attempt}",
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("decision_weigher attempt %d failed: %s", attempt, exc)
                continue
            decision = graph.parse_json_block(str(final_state.get("decision") or "")) or                 graph.parse_json_block(text) or {}
            cards = _coerce_cards(decision.get("cards"))
            reply = str(decision.get("reply") or "").strip()
            if cards:
                break
    if not reply:
        reply = text.strip() or "I could not put together a comparison for that."
    trace.set_span_summary("agent.decision_weigher", f"{len(cards)} card(s)")
    return reply, cards, names


def _llm_disabled_response(user_id: int, message: str, trace: Trace) -> dict[str, Any]:
    """Graceful degradation with no OPENAI_API_KEY.

    Memory still reads and writes normally, so the memory half of the app remains
    fully demoable; only the agent reasoning is unavailable.
    """
    snapshot = store.get_memory_snapshot(user_id)
    store.append_turn(user_id, "user", message)
    reply = (
        "The language model is not configured on this deployment (OPENAI_API_KEY is "
        "unset), so I can't run the agent graph for this turn. Your trip profile is "
        "still stored and readable - here is what I have:\n\n"
        + store.format_profile_for_prompt(snapshot)
    )
    store.append_turn(user_id, "assistant", reply)
    trace.note("llm.disabled", "OPENAI_API_KEY not configured", status="error")
    trace.end(output={"reply": reply})
    return {
        "reply": reply,
        "comparison": [],
        "agents_fired": trace.spans,
        "memory_writes": [],
        "retrieved_sources": [],
        "trace_id": trace.id,
        "trace_url": trace.url,
        "tool_calls": [],
        "profile": snapshot["profile"],
        "visited_history": snapshot["visited_history"],
        "specialists": [],
    }
