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

from backend.agents import catchup, coverage, graph, tracking
from backend.agents.tools import ToolRecorder, current_recorder, reset_recorder, set_recorder
from backend.config import settings
from backend.memory import store, travel
from backend.rag import store as rag_store
from backend.schemas import (
    AgentTrace,
    ChatResponse,
    DestinationVerdict,
    MemoryWriteEntry,
    OnboardingState,
    TravelEntry,
    TripProfile,
    VisitedEntry,
    WishlistEntry,
)
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
    "travel_block", "pending_reviews", "focus_location", "route_note",
    "local_guide_reply", "discovery_reply", "passports",
)


async def _run_agent(
    agent: LlmAgent,
    state: dict[str, Any],
    message: str,
    user_id: str,
    session_id: str,
) -> tuple[str, dict[str, Any], list[str]]:
    """Run one agent (or pipeline) and return its text, final state, and the
    names of the tools it called.

    That tool-name list is for this app's OWN "what ran" panel only. The full
    detail Langfuse needs - model, real token usage, tool args/results, the
    correct agent/tool/generation typing - is captured automatically by the
    google-adk OTEL instrumentation turned on in
    backend/tracing/langfuse_setup.py, with no per-call code here; see that
    module's docstring for why this is the officially recommended way to
    trace a Google ADK app, and notes/09-observability-and-tracing.md for the
    hand-rolled version this replaced.
    """
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
        "travel_month": date.today().isoformat(),
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


_DISCLOSURE_MARKERS = ("unconfirmed", "unverified", "live-sourced", "live sourced")


def _enforce_live_source_disclosure(
    reply: str, cards: list[dict[str, Any]], live_sourced: set[str]
) -> tuple[str, list[dict[str, Any]]]:
    """Code-level backstop for the live-sourced disclosure rule.

    The weigher is instructed (DECISION_INSTRUCTION plus the coverage_note's
    "LIVE-SOURCED DATA FOUND" block) to flag every figure it states for an
    off-corpus destination as unconfirmed/live-sourced. It does not reliably
    do this - reproduced live, repeatedly: the exact guard text was present,
    the specialist's OWN report already carried the disclosure ("This
    information is unverified and came from a live source..."), and the
    weigher's synthesis still dropped it from the reply, presenting AUD 50
    visa fees and $20-30/day budgets for Nauru and Uzbekistan as plain fact.
    Strengthening the prompt alone did not fix it. This makes disclosure a
    fact about the output rather than a hope about the model, matching the
    coverage guard's own philosophy (backend/agents/coverage.py) of computing
    safety-critical checks in code rather than trusting the model to comply.
    """
    if not live_sourced:
        return reply, cards

    marked: list[dict[str, Any]] = []
    for card in cards:
        if card["destination"].strip().lower() not in live_sourced:
            marked.append(card)
            continue
        card_text = " ".join(
            str(card.get(k) or "")
            for k in ("rationale", "est_cost_note", "visa_flag", "season_flag")
        ) + " " + " ".join(card.get("backpacker_notes") or [])
        if any(marker in card_text.lower() for marker in _DISCLOSURE_MARKERS):
            marked.append(card)
            continue
        note = (
            "Figures for this destination are live-sourced and unconfirmed, not "
            "part of the curated knowledge base - confirm before relying on them."
        )
        card = dict(card)
        card["visa_flag"] = f"{card['visa_flag']} {note}".strip() if card.get("visa_flag") else note
        marked.append(card)

    # Prepended, unconditionally, whenever any candidate is live-sourced - not
    # only appended when disclosure is entirely absent. A disclosure that
    # shows up after several sentences of confidently-stated figures reads as
    # an afterthought, not an admission: reproduced live, the model stated
    # every figure as plain fact and only mentioned "live-sourced, unverified"
    # in a final sentence tacked on the end, which still read as confabulation
    # to a human (and to the eval judge, whose own rubric asks for an "upfront"
    # admission). Leading with it is what actually satisfies that bar.
    names = sorted(live_sourced)
    label = " and ".join(name.title() for name in names)
    pronoun_subject = "it is" if len(names) == 1 else "they are"
    pronoun_object = "it" if len(names) == 1 else "them"
    disclosure = (
        f"A heads-up before the specifics: this assistant holds no curated, "
        f"verified data for {label} - {pronoun_subject} outside the knowledge base "
        f"this covers. Everything below on {pronoun_object} came from a live web "
        f"search this turn instead, so treat it as unconfirmed and check it "
        f"yourself before relying on it."
    )
    reply = f"{disclosure} {reply}".strip()
    return reply, marked


# --------------------------------------------------------------------------- #
# main entry point
# --------------------------------------------------------------------------- #
def to_chat_response(result: dict[str, Any]) -> ChatResponse:
    """Shape a run_turn() result dict into the API's ChatResponse model.

    Shared rather than duplicated: /chat calls run_turn directly, and the
    catch-up "what's changed" answer IS a run_turn call too - it is a genuine
    chat turn, just triggered from a different card - so both routes build the
    same response the same way.
    """
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
        intent=result.get("intent"),
        travel_history=[TravelEntry(**h) for h in result.get("travel_history", [])],
        wishlist=[WishlistEntry(**w) for w in result.get("wishlist", [])],
        review_prompt=result.get("review_prompt"),
        onboarding=(
            OnboardingState(**result["onboarding"]) if result.get("onboarding") else None
        ),
    )


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

    # A real turn happened today - regardless of what happens next, including
    # the LLM being unavailable. This is the ONLY place that gets touched for
    # it, so opening the chat page or checking catch-up status cannot silently
    # clear tomorrow's catch-up prompt on its own. It has to sit before the
    # llm_enabled check below, not after: an earlier version placed it after,
    # so answering the catch-up card while the LLM was unavailable never
    # cleared the prompt at all - caught by a smoke test, not by inspection.
    catchup.touch_last_active(user_id)

    try:
        if not settings.llm_enabled:
            return _llm_disabled_response(user_id, message, trace)

        # ---- 1. HOW WE RETRIEVE: read memory at the top of every turn --------
        with trace.span("memory.read", input={"user_id": user_id}) as mem_read:
            snapshot = store.get_memory_snapshot(user_id)
            travel_snapshot = travel.get_travel_snapshot(user_id)
            memory_block = store.format_profile_for_prompt(snapshot)
            travel_block = travel.format_travel_for_prompt(travel_snapshot)
            mem_read.update(
                output={
                    "profile": {k: v for k, v in snapshot["profile"].items() if k != "user_id"},
                    "visited_count": len(snapshot["visited_history"]),
                    "travel_history_count": len(travel_snapshot["travel_history"]),
                    "wishlist_count": len(travel_snapshot["wishlist"]),
                }
            )
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

        # Onboarding is NOT handled here any more. It used to hijack the first
        # few turns of /chat, which meant a brand-new account's first question
        # was answered with a question back. It is now its own page and its own
        # endpoint (backend/agents/onboarding.py, POST /travel/me/onboarding/
        # answer), so a turn that reaches this function is always a real turn.

        # ---- 2. parse the turn ----------------------------------------------
        # Real Langfuse detail (model, tokens, prompt/completion) for this call
        # is captured automatically by the google-adk instrumentation - see
        # backend/tracing/langfuse_setup.py. local_step is this app's own
        # "what ran" timing only, not a second Langfuse observation.
        parse: dict[str, Any] = {}
        with trace.local_step("agent.turn_parser") as parser_step:
            try:
                text, final_state, _ = await _run_agent(
                    graph.make_turn_parser(), base_state, message,
                    str(user_id), f"parse-{user_id}",
                )
                # turn_parser has a real output_schema (see graph.py), so ADK
                # already validated the model's JSON and put a clean dict in
                # state - parse_json_block is only a fallback for the rare
                # case that didn't happen (an ADK/litellm hiccup, not
                # something observed in practice).
                structured = final_state.get("turn_parse")
                parse = structured if isinstance(structured, dict) else (graph.parse_json_block(text) or {})
            except Exception as exc:  # noqa: BLE001
                logger.warning("turn_parser failed: %s", exc)
                parse = {}
                parser_step["status"] = "error"
                parser_step["summary"] = f"{type(exc).__name__}: {exc}"
        if not parse:
            parse = _fallback_parse(message, snapshot)
            trace.set_span_summary("agent.turn_parser", "fell back to heuristic parse")

        # ---- 3. WHEN WE WRITE: explicit memory writes ------------------------
        with trace.span("memory.write", input=parse.get("profile_updates")) as mem_write:
            writes = _apply_memory_writes(user_id, parse)
            writes += _apply_structured_writes(user_id, parse)
            mem_write.update(output={"writes": writes})
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
        # trip_start_date was removed from the profile - it added little (a
        # backpacker's "end date" is usually a soft guess, not a hard fact) and
        # kept getting invented. today() is a better default anyway: it reflects
        # when the question is actually being asked.
        travel_month = parse.get("travel_month") or date.today().isoformat()

        state = {
            **base_state,
            "candidates": ", ".join(candidates) if candidates else "(none named)",
            "travel_month": travel_month,
            # A dual national's second passport is only useful if the specialist
            # can see it, so {nationality?} carries the full list when there is
            # one. It still reads as a single passport for everyone else.
            "nationality": ", ".join(profile.get("passports") or [])
            or profile.get("nationality")
            or "(unknown)",
            "passports": ", ".join(profile.get("passports") or []) or "(unknown)",
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
            reply, cards, fired = await _run_comparison(
                state, message, user_id, parse, trace, candidates
            )

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
        # Safety net for the (already-guarded-against) uncaught-exception path:
        # Trace.end() is idempotent, so this only matters when nothing above
        # got a chance to call it with the real output - it still needs to
        # close the OTEL span so it exports instead of hanging open forever.
        trace.end()


async def _run_local_guide(
    state: dict[str, Any], message: str, user_id: int, trace: Trace
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """On-the-ground questions about one town: where to stay, eat, go."""
    with trace.local_step("agent.local_guide"):
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
    with trace.local_step("agent.discovery"):
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
    with trace.local_step("agent.concierge"):
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
) -> tuple[str, str, list[str], str | None]:
    """Run one specialist. Never raises: a failure is reported, not propagated.

    No explicit parent handle is threaded through any more: this runs inside
    ``asyncio.gather`` under the ``agents.fan_out`` span (see
    ``_run_comparison``), and OpenTelemetry's context propagation - which
    survives a Task being spawned mid-context, copying it at creation time -
    is what nests this call's auto-instrumented ADK activity under that span
    correctly, with no manual wiring.
    """
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            with trace.local_step(agent.name):
                text, final_state, tool_calls = await _run_agent(
                    agent, state, message, str(user_id), f"{agent.name}-{user_id}-{attempt}"
                )
                output = str(final_state.get(key) or text or "")

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
    candidates: list[str] | None = None,
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
    # The whole stage - the gather AND building the reports/failures summary -
    # stays inside this one span, so its aggregate output can be attached
    # before the span closes. A v4 Langfuse span is a real OTEL span: once its
    # `with` block exits the span has genuinely ended, and updating it after
    # that (the old v2 approach - close early, attach output later) is no
    # longer possible.
    #
    # Each gathered specialist's own auto-instrumented ADK activity (see
    # backend/tracing/langfuse_setup.py) nests under this span automatically:
    # OpenTelemetry propagates the "current span" through contextvars, and
    # asyncio.gather's Tasks each copy that context at creation time, which
    # happens synchronously here, still inside this `with` block.
    reports: dict[str, str] = {
        "weather_assessment": "",
        "logistics_assessment": "",
        "recommendations": "",
    }
    all_tool_calls: list[str] = []
    failures: list[str] = []
    with trace.span("agents.fan_out", metadata={"specialists": names}) as fan_span:
        outcomes = await asyncio.gather(
            *(
                _run_one_specialist(agent, key, state, message, user_id, trace)
                for agent, key in specialists
            )
        )

        for (agent, _), (key, output, tool_calls, error) in zip(specialists, outcomes):
            reports[key] = output
            all_tool_calls.extend(tool_calls)
            if error:
                failures.append(f"{agent.name}: {error}")
                # The local timing entry was already recorded by
                # _run_one_specialist; just mark the failure for the UI panel.
                trace.set_span_status(agent.name, "error", error)

        fan_span.update(
            output={"reports": {k: v[:300] for k, v in reports.items() if v}, "failures": failures}
        )

    summary = f"{', '.join(names)}; {len(all_tool_calls)} tool call(s)"
    if failures:
        summary += f"; {len(failures)} failed"
    trace.set_span_summary("agents.fan_out", summary)

    # ---- stage 2: decision weigher ----------------------------------------
    # Recompute the coverage note now that the specialists' tool calls have
    # actually run: the pre-fan-out note (still in `state["coverage_note"]`)
    # was necessarily written before anyone knew whether a live lookup would
    # succeed. The ToolRecorder is a single mutable object shared across the
    # gathered specialist tasks (contextvars carry the same reference, not a
    # copy), so by this point it holds every retrieval any specialist made,
    # including any "unverified" namespace hit from live_lookup - checking it
    # here is how the weigher finds out a gap got filled this turn instead of
    # relying on the stale, necessarily-more-cautious pre-run note.
    recorder = current_recorder()
    live_sourced = {
        (r.get("destination") or "").strip().lower()
        for r in (recorder.retrieved if recorder else [])
        if r.get("namespace") == "unverified" and r.get("destination")
    }
    weigher_state = {
        **state,
        **reports,
        "coverage_note": coverage.coverage_note(candidates or [], live_sourced),
    }
    cards: list[dict[str, Any]] = []
    reply = ""
    text = ""
    with trace.local_step("agent.decision_weigher"):
        # Up to three attempts: the weigher occasionally answers in prose instead
        # of JSON, and returning no comparison at all is the worst outcome for the
        # user, so it is worth another cheap call before giving up. No
        # output_schema on this agent - see graph.py's make_decision_weigher for
        # why - so parse_json_block is the primary path here, not a fallback.
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
    reply, cards = _enforce_live_source_disclosure(reply, cards, live_sourced)
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
