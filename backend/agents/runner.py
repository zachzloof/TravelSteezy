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

from backend.agents import coverage, graph, tracking
from backend.agents.tools import ToolRecorder, reset_recorder, set_recorder
from backend.config import settings
from backend.memory import store, travel
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
    "travel_block", "pending_reviews", "focus_location", "route_note", "onboarding_step",
    "onboarding_turns", "onboarding_reply", "local_guide_reply", "discovery_reply",
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


def _apply_structured_writes(user_id: int, parse: dict[str, Any]) -> list[dict[str, Any]]:
    """The extension's write path: visits, wishlist, reviews. Never kills a turn."""
    try:
        return tracking.apply_tracking(user_id, parse)
    except Exception as exc:  # noqa: BLE001
        logger.warning("tracking writes failed for user %s: %s", user_id, exc)
        return []


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
            travel_snapshot = travel.get_travel_snapshot(user_id)
            memory_block = store.format_profile_for_prompt(snapshot)
            travel_block = travel.format_travel_for_prompt(travel_snapshot)
        trace.set_span_summary(
            "memory.read",
            f"{len(travel_snapshot['travel_history'])} places, "
            f"{len(travel_snapshot['wishlist'])} on wishlist",
        )

        pending = [p["location"] for p in travel_snapshot["pending_reviews"]]
        base_state = {
            "memory_block": memory_block,
            "travel_block": travel_block,
            "user_question": message,
            "today": date.today().isoformat(),
            "pending_reviews": ", ".join(pending) if pending else "(none)",
        }

        # ---- onboarding takes over the first few turns of a new account ----
        onboarding = travel_snapshot["onboarding"]
        if onboarding["status"] in {"not_started", "in_progress"}:
            return await _run_onboarding(
                user_id, message, base_state, onboarding, trace, recorder
            )

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
            writes += _apply_structured_writes(user_id, parse)
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
        # The parser sometimes classifies a two-destination question as "local"
        # and leaves candidates empty, which sent visa questions to an agent with
        # no visa tool. Fall back to deterministic detection over the raw message.
        if len(candidates) < 2:
            detected = rag_store.detect_destinations(message)
            if len(detected) >= 2:
                candidates = detected
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
            "route_note": coverage.route_note(profile.get("current_location")),
            "travel_block": travel.format_travel_for_prompt(travel.get_travel_snapshot(user_id)),
            "focus_location": parse.get("focus_location") or profile.get("current_location") or "",
        }

        # ---- 5. dispatch ------------------------------------------------------
        intent = str(parse.get("intent") or "").strip().lower()
        if intent not in {"compare", "discover", "local", "memory", "review"}:
            intent = "compare" if candidates else "memory"
        # Two or more named destinations IS a comparison, whatever the parser
        # called it. Without this the classifier routed "what do I need to get
        # into Indonesia and Cambodia?" to the local guide, which has no visa
        # tool and answered from parametric knowledge - it got the rule wrong.
        if len(candidates) >= 2:
            intent = "compare"
        # A comparison with nothing to compare is really a discovery question.
        elif intent == "compare" and not candidates:
            intent = "discover" if profile.get("current_location") else "memory"

        # Town-level discovery needs a town. If we only know the country, fall back
        # to the country-level comparison path rather than stalling the turn to ask
        # which town they are in - that dead end lost the traveller their answer
        # AND suppressed the hard-deadline warning they needed.
        if intent == "discover":
            from backend.rag.route_data import ROUTE_GRAPH

            here = (profile.get("current_location") or "").strip().lower()
            if here and here not in ROUTE_GRAPH:
                neighbours = coverage.nearby_country_options(here)
                if neighbours:
                    candidates = neighbours
                    state["candidates"] = ", ".join(neighbours)
                    state["coverage_note"] = coverage.coverage_note(neighbours)
                    intent = "compare"

        if intent == "local":
            reply, cards, fired = await _run_local_guide(state, message, user_id, trace)
        elif intent == "discover":
            reply, cards, fired = await _run_discovery(state, message, user_id, trace)
        elif intent in {"memory", "review"}:
            reply, cards, fired = await _run_concierge(state, message, user_id, trace)
        else:
            reply, cards, fired = await _run_comparison(state, message, user_id, parse, trace)

        # ---- post-visit review nudge, appended rather than hijacking the turn --
        just_reviewed = [str(r.get("location", "")) for r in (parse.get("reviews") or []) if isinstance(r, dict)]
        prompt = tracking.review_prompt_for(user_id, exclude=just_reviewed)
        if prompt and intent != "review":
            reply += tracking.render_review_prompt(prompt)
            trace.note("review_prompt", f"asked about {prompt['location']}")

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
            "intent": intent,
            "travel_history": travel.get_travel_history(user_id),
            "wishlist": travel.get_wishlist(user_id),
            "review_prompt": prompt,
            "onboarding": travel.get_onboarding(user_id),
        }
    finally:
        reset_recorder(token)


async def _run_onboarding(
    user_id: int,
    message: str,
    base_state: dict[str, Any],
    onboarding: dict[str, Any],
    trace: Trace,
    recorder: ToolRecorder,
) -> dict[str, Any]:
    """Conversational onboarding for a brand-new account.

    Two agents, on purpose. An extractor turns the message into structured facts,
    then THIS function writes them, then a separate conversational agent asks for
    whatever is still missing. One agent asked to do both reliably produced the
    chat and silently dropped the structured block, so nothing was ever captured
    and onboarding asked the same question on every turn.

    Progress is judged from what is actually stored, never from the model's own
    claim about which step it is on.
    """
    travel.set_onboarding(user_id, status="in_progress", bump_turn=True)

    # ---- 1. extract structured facts from this message --------------------
    captured: dict[str, Any] = {}
    with trace.span("agent.onboarding_extractor"):
        try:
            text, _, _ = await _run_agent(
                graph.make_onboarding_extractor(), base_state, message,
                str(user_id), f"onboard-extract-{user_id}",
            )
            captured = graph.parse_json_block(text) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("onboarding extraction failed: %s", exc)
    trace.set_span_summary(
        "agent.onboarding_extractor",
        ", ".join(k for k, v in captured.items() if v) or "nothing captured",
    )

    # ---- 2. write what we learned ------------------------------------------
    with trace.span("memory.write"):
        writes = _apply_onboarding_capture(user_id, captured)
    trace.set_span_summary("memory.write", f"{len(writes)} write(s)")

    # ---- 3. decide whether we are done, from stored data --------------------
    gaps = travel.onboarding_gaps(user_id)
    skip_requested = bool(captured.get("skip_requested"))
    state_now = travel.get_onboarding(user_id)
    # Hard cap so onboarding can never trap someone in a loop.
    exhausted = state_now["turns"] >= 6

    finishing = gaps["complete"] or skip_requested or exhausted
    conversation_state = {
        **base_state,
        "onboarding_gaps": "nothing" if finishing else gaps["missing_text"],
        "onboarding_captured": gaps["captured_text"],
    }

    # ---- 4. converse --------------------------------------------------------
    with trace.span("agent.onboarding"):
        try:
            reply, _, _ = await _run_agent(
                graph.make_onboarding_agent(), conversation_state, message,
                str(user_id), f"onboard-{user_id}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("onboarding conversation failed: %s", exc)
            reply = ""
    reply = (reply or "").strip()

    if finishing:
        travel.set_onboarding(user_id, status="complete", step="done")
        if not reply:
            reply = "Thanks - that's everything I need to get started."
        reply += (
            "\n\nYou can change any of this any time in My Preferences. "
            "Ask me where to go next whenever you are ready."
        )
    else:
        travel.set_onboarding(user_id, step=gaps["missing"][0])
        if not reply:
            reply = "Tell me a bit about where you have been so far on this trip."

    store.append_turn(user_id, "user", message)
    store.append_turn(user_id, "assistant", reply)
    trace.end(output={"reply": reply, "onboarding": True})

    return {
        "reply": reply,
        "comparison": [],
        "agents_fired": trace.spans,
        "memory_writes": writes,
        "retrieved_sources": recorder.retrieved,
        "trace_id": trace.id,
        "trace_url": trace.url,
        "tool_calls": recorder.tool_names,
        "profile": store.get_profile(user_id),
        "visited_history": store.get_visited_history(user_id),
        "specialists": ["onboarding_extractor", "onboarding_agent"],
        "intent": "onboarding",
        "travel_history": travel.get_travel_history(user_id),
        "wishlist": travel.get_wishlist(user_id),
        "review_prompt": None,
        "onboarding": travel.get_onboarding(user_id),
    }


def _apply_onboarding_capture(user_id: int, captured: dict[str, Any]) -> list[dict[str, Any]]:
    """Write what onboarding learned. Explicit calls, one per field."""
    writes: list[dict[str, Any]] = []
    if not isinstance(captured, dict) or not captured:
        return writes

    for index, entry in enumerate(captured.get("travel_history") or [], start=1):
        if not isinstance(entry, dict) or not entry.get("location"):
            continue
        order = entry.get("order")
        try:
            order = int(order) if order is not None else None
        except (TypeError, ValueError):
            order = None
        result = travel.add_travel_history(
            user_id,
            location=str(entry["location"]),
            location_type=str(entry.get("location_type") or "city"),
            country=entry.get("country"),
            arrival_date=entry.get("arrival_date"),
            departure_date=entry.get("departure_date"),
            source="onboarding",
            order_index=order if order is not None else index,
        )
        if result.get("ok"):
            writes.append(
                {
                    "operation": "add_travel_history",
                    "payload": {"location": entry["location"], "order": order or index},
                    "source": "onboarding",
                }
            )

    for entry in captured.get("wishlist") or []:
        if not isinstance(entry, dict) or not entry.get("location"):
            continue
        try:
            priority = int(entry.get("priority") or 2)
        except (TypeError, ValueError):
            priority = 2
        result = travel.add_wishlist(
            user_id,
            location=str(entry["location"]),
            location_type=str(entry.get("location_type") or "city"),
            country=entry.get("country"),
            priority=priority,
            source="onboarding",
        )
        if result.get("ok"):
            writes.append(
                {
                    "operation": "add_wishlist",
                    "payload": {"location": entry["location"], "priority": priority},
                    "source": "onboarding",
                }
            )

    interests = [str(i) for i in (captured.get("interests") or []) if str(i).strip()]
    if interests:
        travel.set_interests(user_id, interests, source="onboarding")
        writes.append(
            {
                "operation": "set_interests",
                "payload": {"interests": interests},
                "source": "onboarding",
            }
        )

    if captured.get("social_style"):
        if travel.set_social_style(user_id, str(captured["social_style"]), source="onboarding"):
            writes.append(
                {
                    "operation": "set_social_style",
                    "payload": {"social_style": captured["social_style"]},
                    "source": "onboarding",
                }
            )

    profile_updates = {
        key: captured[key]
        for key in (
            "budget_band", "travel_style", "climate_preference",
            "current_location", "nationality", "trip_start_date", "trip_end_date",
        )
        if captured.get(key)
    }
    if profile_updates:
        store.update_profile(user_id, profile_updates, source="onboarding")
        writes.append(
            {
                "operation": "update_profile",
                "payload": profile_updates,
                "source": "onboarding",
            }
        )
    return writes


async def _run_local_guide(
    state: dict[str, Any], message: str, user_id: int, trace: Trace
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """On-the-ground questions about one town: where to stay, eat, go."""
    with trace.span("agent.local_guide", input={"focus": state.get("focus_location")}):
        text, _, tool_calls = await _run_agent(
            graph.make_local_guide(), state, message, str(user_id), f"local-{user_id}"
        )
    trace.set_span_summary("agent.local_guide", f"{len(tool_calls)} tool call(s)")
    return (
        text.strip() or "I could not find anything solid for that place.",
        [],
        ["local_guide"],
    )


async def _run_discovery(
    state: dict[str, Any], message: str, user_id: int, trace: Trace
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Open "where next from here", answered at town level from the route corpus."""
    with trace.span("agent.discovery", input={"from": state.get("current_location")}):
        text, _, tool_calls = await _run_agent(
            graph.make_discovery_agent(), state, message, str(user_id), f"discover-{user_id}"
        )
    trace.set_span_summary("agent.discovery", f"{len(tool_calls)} tool call(s)")
    return (
        text.strip() or "I don't have route data for where you are right now.",
        [],
        ["discovery_agent"],
    )


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
        # Up to three attempts: the weigher occasionally answers in prose instead
        # of JSON, and returning no comparison at all is the worst outcome for the
        # user, so it is worth another cheap call before giving up.
        for attempt in (1, 2, 3):
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
