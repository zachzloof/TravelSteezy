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
import random
import re
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
from backend.rag import live_lookup
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

# Used only to break exact ties in wishlist ordering - see _order_wishlist. Its
# own Random instance, not the `random` module functions, so tests can seed this
# one object without touching global random state and nothing else in the process
# can reseed it out from under a turn.
_candidate_rng = random.Random()


def _journey_hours(origin: str, dest: str) -> float:
    """Shortest curated travel time between two countries, ``inf`` if unknown.

    The same curated overland/flight figures the Logistics specialist reports, so
    "closest" here means the same thing to the ranking code as it will to the
    traveller reading the answer.
    """
    from backend.agents import routes

    route = routes.lookup(origin, dest)
    hours = [
        h for h in (route.get("overland_hours"), route.get("flight_hours"))
        if h is not None
    ]
    return min(hours) if hours else float("inf")


def _order_wishlist(
    wishlist_priority: dict[str, int],
    here_country: str,
    rng: random.Random,
) -> list[str]:
    """Order wishlist countries by how they should compete for a candidate slot.

    Stated priority first, then distance from where the traveller actually is.

    Priority leading is the whole point: it is the one number the traveller set
    themselves, and a destination they marked 1 should not have to win a coin
    toss against one they marked 5. Distance only ever separates entries that
    already tie on priority - which is the common case, since a traveller who
    marks ten places "must do" has told us they all matter equally and has not
    told us which to raise first. Proximity is the honest answer there: of two
    equally-wanted countries, the nearer one is the cheaper, more plausible next
    hop, and it is the same curated figure the Logistics specialist will quote.

    The random tiebreak underneath is a last resort, not a strategy. It only
    reaches entries identical on BOTH priority and journey time, which in
    practice means a group of same-priority countries we hold no route data for
    at all - several of the twenty uncovered countries COUNTRY_NEIGHBOURS can now
    name sit at ``inf`` together. Ordering those alphabetically would be
    deterministic but would also mean the same few won every single turn forever;
    shuffling them lets a long flat wishlist rotate. Anything we actually hold
    data for is fully determined by priority and distance.
    """
    return sorted(
        wishlist_priority,
        key=lambda c: (
            wishlist_priority.get(c, 3),
            _journey_hours(here_country, c),
            rng.random(),
        ),
    )


def _split_candidate_budget(
    wishlist: list[str],
    neighbours: list[str],
    budget: int,
) -> tuple[list[str], list[str]]:
    """Divide ``budget`` candidate slots between the two sources.

    Half each, so a budget of 10 is 5 wishlist + 5 nearest countries and a budget
    of 8 is 4 + 4. Whichever side cannot fill its half lends the remainder to the
    other, so an empty wishlist still yields all five neighbours and an origin we
    hold no geography for still yields a full pool of wishlist entries.

    Both lists are taken as prefixes, so both arrive already in the order they
    should compete in: the wishlist from _order_wishlist, the neighbours
    nearest-first as COUNTRY_NEIGHBOURS stores them.

    Returns ``(wishlist_choice, neighbour_choice)`` rather than one merged list so
    the caller can say in the trace where each candidate came from.
    """
    budget = max(0, budget)
    half = budget // 2

    # Claim half each, then hand out what neither side could use. Wishlist is
    # offered the leftover first: those are destinations the traveller asked for
    # by name, which is a stronger signal than proximity.
    take_wishlist = min(len(wishlist), half)
    take_neighbours = min(len(neighbours), half)
    spare = budget - take_wishlist - take_neighbours
    if spare > 0:
        extra = min(spare, len(wishlist) - take_wishlist)
        take_wishlist += extra
        spare -= extra
    if spare > 0:
        take_neighbours += min(spare, len(neighbours) - take_neighbours)

    return wishlist[:take_wishlist], neighbours[:take_neighbours]


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
    "turn_parse", "decision", "concierge_reply", "coverage_note",
    "travel_block", "pending_reviews", "focus_location", "route_note",
    "local_guide_reply", "discovery_reply", "passports", "max_cards",
)


def adk_session_id(user_id: int | str) -> str:
    """The ADK session id every agent in one turn runs under.

    It is deliberately the SAME string for all of them, and deliberately the
    same string ``run_turn`` gives its Langfuse trace.

    It used to be one per agent - "parse-2", "local-2", "discover-2",
    "weigh-2-1" - which read as helpful labelling and quietly broke session
    grouping in Langfuse. The OpenInference instrumentation carries the ADK
    session onto its spans, and at ingestion the LAST agent to run overwrites
    the trace's session id with it, so one conversation scattered across four
    "sessions" named after whichever agent happened to answer, and no session
    in Langfuse showed the actual conversation. Verified by experiment against
    the live project, both before and after - see notes/08, decision 47.

    Nothing depended on those ids being distinct: ``_run_agent`` builds its own
    ``InMemorySessionService`` per call, so two agents are isolated by holding
    separate service instances, not by the id string. Which agent ran is still
    visible in the span name (``agent_run [local_guide]``) and in this app's
    own per-agent timing panel.
    """
    return f"user-{user_id}"


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
def _apply_memory_writes(
    user_id: int, parse: dict[str, Any], message: str = ""
) -> list[dict[str, Any]]:
    """THE WRITE PATH. Explicit calls, one per thing the user told us."""
    writes: list[dict[str, Any]] = []

    raw_updates = parse.get("profile_updates")
    updates = dict(raw_updates) if isinstance(raw_updates, dict) else {}
    if updates:
        # current_location is grounded in the traveller's own words, same rule
        # and same reason as tracking's visits and departures: the parser
        # re-states a location on nearly every turn, and one stale re-statement
        # silently overwrote what the traveller had just told us (bug report
        # #3). Every other profile field is a preference they stated in prose
        # and cannot be checked this way; this one is a place name, so it can.
        stated_location = str(updates.get("current_location") or "").strip()
        if stated_location and not tracking.mentioned_in(stated_location, message):
            logger.info(
                "dropping ungrounded current_location %r for user %s - not named in the message",
                stated_location, user_id,
            )
            updates.pop("current_location", None)
        # "interests" is turn_parser's one free-text field that is NOT a
        # trip_profile column: it has to go through travel.set_interests (the
        # structured, weighted, KEY-aware store), never store.update_profile,
        # which would overwrite the trip_profile.interests mirror with a raw
        # string and silently blow away whichever interests are marked KEY.
        # Merge, not replace: a mid-chat mention adds to what is already known,
        # it does not restate the whole list.
        interests_text = str(updates.pop("interests", "") or "").strip()
        if interests_text:
            mentioned = [
                t.strip() for t in re.split(r"[,;]|\band\b", interests_text) if t.strip()
            ]
            if mentioned:
                travel.set_interests(user_id, mentioned, source="agent")
                writes.append(
                    {"operation": "set_interests", "payload": {"interests": mentioned}, "source": "agent"}
                )
        if updates:
            store.update_profile(user_id, updates, source="agent")
            writes.append({"operation": "update_profile", "payload": updates, "source": "agent"})

    # Departures are NOT written here. This function used to carry its own
    # departure loop keyed on departure["country"], but ParsedDeparture (see
    # graph.py) has no country field and ADK's strict output schema strips any
    # the model emits, so `country` was always None and the loop's guard always
    # skipped - unreachable code that read like the live write path. The real
    # one is tracking.apply_tracking below, which additionally gets the
    # town-vs-country distinction right (leaving Pai is not leaving Thailand).
    return writes


def _apply_structured_writes(
    user_id: int, parse: dict[str, Any], message: str = "", trace: Trace | None = None
) -> list[dict[str, Any]]:
    """The extension's write path: visits, wishlist, reviews, departures.

    Never kills a turn - a tracking failure must not cost the traveller their
    answer. It IS reported though: this is the only path that writes visits,
    departures and reviews, so swallowing an exception here silently loses
    everything the traveller just told us, and a log line nobody is tailing was
    the only trace of it.
    """
    try:
        return tracking.apply_tracking(user_id, parse, message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("tracking writes failed for user %s", user_id)
        if trace is not None:
            trace.note(
                "memory.tracking_failed", f"{type(exc).__name__}: {exc}", status="error"
            )
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

    # Enforce the card cap in code, not only in the prompt. The weigher is asked
    # for its best settings.weigher_top_n, and now that it can be handed ten
    # candidates instead of three, "return one card per candidate" is the
    # instruction it is most likely to fall back on when the prompt gets long -
    # which would push a ten-card wall into a UI built to show three and reveal
    # three more. Same reasoning as every other guard here: if the contract
    # matters, compute it rather than ask for it.
    #
    # Trimmed after the rank sort, so this keeps the weigher's OWN top picks
    # rather than whichever cards happened to come first in its JSON.
    if len(cards) > settings.weigher_top_n:
        logger.info(
            "decision_weigher returned %d cards, trimming to %d",
            len(cards), settings.weigher_top_n,
        )
        cards = cards[: settings.weigher_top_n]

    # Re-number after the trim so ranks are always a contiguous 1..n. The weigher
    # occasionally emits duplicate or gapped ranks, and the frontend orders and
    # labels cards by this field.
    for position, card in enumerate(cards, start=1):
        card["rank"] = position
    return cards


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
            # The weigher is handed the whole candidate pool and returns only its
            # best N; the UI shows three and hides the rest behind a toggle.
            "max_cards": str(settings.weigher_top_n),
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
                    str(user_id), adk_session_id(user_id),
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
            writes = _apply_memory_writes(user_id, parse, message)
            writes += _apply_structured_writes(user_id, parse, message, trace)
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
            # Read straight from the structured, tiered store rather than the
            # trip_profile.interests mirror, so this can never lag behind a
            # just-applied write in step 3 above within the same turn.
            "interests": travel.format_interests_display(
                travel.get_key_interests(user_id), travel.get_other_interests(user_id)
            ) or "(unknown)",
            # Deterministic guard computed in code, not left to the model.
            "coverage_note": coverage.coverage_note(candidates),
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

        # WHICH SCOPE a "where next" is answered at is decided here, in code.
        #
        # Two separate things force the country-level path:
        #   * the question itself is about leaving the country - "which country
        #     next", "I want to change country", "my visa is running out"
        #     (coverage.wants_country_scope). Reported 2026-09-14 (test1234):
        #     asked three times, in three phrasings, which COUNTRY to go to
        #     next - once with a visa about to expire - and answered every time
        #     with towns inside the country they were trying to leave, because
        #     the word "country" reached no decision anywhere in this pipeline.
        #     Scope used to be a pure side effect of how precisely the stored
        #     location happened to be recorded.
        #   * the stored location is a country rather than a town, so town-level
        #     hops do not exist for it anyway - the original reason this branch
        #     exists. Falling back to a country comparison beats stalling the
        #     turn to ask which town they are in; that dead end lost the
        #     traveller their answer.
        country_scope = coverage.wants_country_scope(message)
        # "i want to change country" was classified `local` in the reported
        # conversation, not `discover`, so gating this on `discover` alone would
        # have missed the exact turn the traveller complained about. A
        # country-scoped question with nowhere named is a where-next question
        # whatever the classifier called it. `review` and `memory` are left
        # alone: "Thailand was the best country I've been to" is a review, and
        # rewriting it into a comparison would be its own bug.
        if country_scope and intent == "local" and not candidates:
            intent = "discover"
            trace.note("routing.country_scope", "local -> discover (country question)")
        if intent == "discover":
            from backend.agents import climate
            from backend.rag.route_data import ROUTE_GRAPH, resolve_country

            here = (profile.get("current_location") or "").strip().lower()
            if not here:
                # No town, no country, nothing to route from. The town-level
                # discovery agent used to take this turn anyway, and with a
                # route history in its prompt it simply picked a town out of it
                # and answered as though the traveller were still there - real
                # curated hops for a place they never named (bug report #3).
                # The concierge holds no retrieval tools at all, so the worst it
                # can do is ask where they are, which is the only honest answer
                # available with no origin.
                intent = "memory"
                trace.note("routing.location_unknown", "asked where they are")
            elif country_scope or here not in ROUTE_GRAPH:
                here_country = resolve_country(here) or here
                neighbours = coverage.nearby_country_options(here_country)

                # An open "where next" should weigh places the traveller has
                # already said they want to go, not just overland geography -
                # a wishlist pick is still a real answer even when it isn't
                # next door. Wishlist is already open-only. Keep each
                # country's best (lowest-number) stored priority in case more
                # than one wishlist entry resolves to it (e.g. two cities in
                # the same country).
                wishlist_priority: dict[str, int] = {}
                for entry in travel_snapshot["wishlist"]:
                    loc = (entry.get("country") or entry.get("location") or "").strip().lower()
                    if not loc or loc == here_country:
                        continue
                    priority = entry.get("priority") or 3
                    if loc not in wishlist_priority or priority < wishlist_priority[loc]:
                        wishlist_priority[loc] = priority

                # A country on the wishlist that is ALSO one of the five nearest
                # is dropped here rather than researched twice - it stays in the
                # pool once, via the neighbour half, and keeps its stored
                # priority for the ordering sort below through
                # wishlist_priority.get(). Deduping on the neighbour side also
                # frees a wishlist slot for somewhere further afield, which is
                # the side with more to say that geography alone would not.
                wishlist_pool = [
                    c
                    for c in _order_wishlist(wishlist_priority, here_country, _candidate_rng)
                    if c not in neighbours
                ]
                chosen_wishlist, chosen_neighbours = _split_candidate_budget(
                    wishlist_pool,
                    neighbours,
                    settings.max_comparison_candidates,
                )
                pool = chosen_wishlist + chosen_neighbours
                if pool:
                    # Worth seeing in a trace: which half each candidate came
                    # from, and how many wishlist entries did not make the cut.
                    trace.note(
                        "candidates.pool",
                        f"{len(chosen_wishlist)} of {len(wishlist_pool)} wishlist "
                        f"(by priority, then distance) + {len(chosen_neighbours)} "
                        f"of {len(neighbours)} nearest, budget "
                        f"{settings.max_comparison_candidates}",
                    )
                    # climate.assess() only knows the curated table (~15
                    # countries) - everything else comes back "unknown", which
                    # the season_rank tiering below (correctly) treats as the
                    # worst tier. That is honest but not useful for a wishlist
                    # that is mostly countries outside that table: a genuinely
                    # good month for an uncurated country would always lose to
                    # a curated country's known-bad month, because "unknown"
                    # has nothing real to compete on. Reproduced live: a
                    # traveller whose wishlist was mostly Japan/Peru/Morocco/
                    # Iceland-style countries got served two typhoon/monsoon
                    # "avoid" picks, because none of their real wishlist had a
                    # curated rating to rank with.
                    #
                    # So for any candidate the table comes back "unknown" for,
                    # actually check - live_lookup's existing
                    # search-once-cache-forever pipeline underneath
                    # classify_season means this only ever pays the real
                    # search+LLM cost once per destination; every later month
                    # asked about the same country reuses the same fetched,
                    # verified passage. Capped, and in pool order (wishlist
                    # first), so a long candidate list cannot turn one turn into
                    # a dozen live searches.
                    #
                    # "any candidate", not "any wishlist candidate": this used to
                    # skip neighbours on the reasoning that they were "always
                    # curated by construction". That stopped being true when
                    # COUNTRY_NEIGHBOURS widened to the five genuinely nearest
                    # countries rather than the nearest ones the corpus happened
                    # to cover (see the long note there). Twenty of the countries
                    # it can now name - China, Taiwan, Singapore, Bangladesh,
                    # Uruguay, Panama and the rest - have no curated climate row
                    # at all, and leaving them on the old assumption would have
                    # handed every one of them to the weigher permanently
                    # "unknown": gagged by the coverage guard, unable to rank
                    # first, and beaten by any curated neighbour having a
                    # genuinely terrible month. This live check is precisely what
                    # makes widening that table safe rather than cosmetic.
                    MAX_LIVE_SEASON_CHECKS = 6
                    uncovered = [
                        c for c in pool
                        if climate.assess(c, travel_month)["rating"] == "unknown"
                    ][:MAX_LIVE_SEASON_CHECKS]

                    live_season_ratings: dict[str, str] = {}
                    if uncovered:
                        with trace.local_step("candidates.live_season_check"):
                            results = await asyncio.gather(
                                *(
                                    asyncio.to_thread(live_lookup.classify_season, c, travel_month)
                                    for c in uncovered
                                )
                            )
                            live_season_ratings = {
                                c: r for c, r in zip(uncovered, results) if r
                            }
                        trace.set_span_summary(
                            "candidates.live_season_check",
                            f"{len(live_season_ratings)}/{len(uncovered)} resolved",
                        )
                    # This sort ORDERS the pool; it no longer decides who is in
                    # it. That is the whole point of the change: the three-pass
                    # tiering below used to be followed by a hard `[:3]`, so a
                    # cheap code-side heuristic - season tier, then curated
                    # journey hours, then stored wishlist priority - was the
                    # thing choosing the traveller's three destinations, and the
                    # specialists and the weigher only ever saw what had already
                    # survived it. Everything it discarded was discarded before a
                    # single agent had looked at the traveller's budget band,
                    # pace, interests or visa position, and nothing recorded what
                    # had been dropped. The whole (budget-capped) pool now goes
                    # to the specialists and the decision_weigher ranks it, which
                    # is the one step in this graph that actually holds all three
                    # specialist reports and the trip profile at once.
                    #
                    # Keeping the sort anyway is deliberate. It costs nothing, it
                    # gives the weigher a sane default ordering to push against
                    # rather than a list in dictionary order, and it keeps the
                    # trace readable. The three passes: (1) season fit right now
                    # - a country in its rainy season sorts below one actually in
                    # its travel window, from the same curated table the Weather
                    # specialist uses; (2) distance - the same curated
                    # flight/overland hours the Logistics specialist uses,
                    # closest first, unknown routes sinking within their season
                    # tier; (3) how badly they want to go - the wishlist priority
                    # they set themselves, neighbours defaulting to the lowest
                    # since they were never explicitly asked for.
                    #
                    # "unknown" sits WORSE than "avoid", not between "mixed" and
                    # "avoid": a country this app holds zero seasonal data for is
                    # not a safer bet than a covered neighbour having a bad month,
                    # it is an untested one. Ranking unknown ahead of avoid let
                    # bucket-list countries with no curated coverage at all (e.g.
                    # Japan, Australia) push out actually-covered neighbours just
                    # because the neighbours' real season happened to be bad that
                    # month - reproduced live from a Bali account with
                    # Japan/Australia on the wishlist in September, when Thailand
                    # and Philippines are both genuinely "avoid" season: the old
                    # tiering chose Japan and Australia over Malaysia, Thailand
                    # and Philippines, none of which this app can back up.
                    # It matters less now that this only orders, but it is still
                    # the honest tiering and the live check above is what stops
                    # most candidates landing in "unknown" in the first place.
                    season_rank = {"good": 0, "mixed": 1, "avoid": 2, "unknown": 3}

                    def _season_rating(dest: str) -> str:
                        return live_season_ratings.get(dest) or climate.assess(dest, travel_month)["rating"]

                    ranked = sorted(
                        pool,
                        key=lambda c: (
                            season_rank.get(_season_rating(c), 3),
                            _journey_hours(here_country, c),
                            wishlist_priority.get(c, 3),
                        ),
                    )
                    # No truncation. The weigher decides what makes the reply.
                    candidates = ranked
                    state["candidates"] = ", ".join(candidates)
                    state["coverage_note"] = coverage.coverage_note(candidates)
                    trace.note("candidates.ranked", ", ".join(candidates))
                    intent = "compare"
                    # The needs_* flags on `parse` were set by turn_parser for the
                    # ORIGINAL "discover" intent, where the discovery agent (not
                    # these three specialists) does the work and there was nothing
                    # to compare yet - so needs_logistics/needs_weather often came
                    # back false. Reusing those stale flags here silently skipped
                    # whole specialists on exactly the turns this fallback exists
                    # for. Now that there is a real candidate set to weigh, all
                    # three specialists are back in scope regardless of what the
                    # parser guessed before it knew that.
                    parse["needs_weather"] = True
                    parse["needs_logistics"] = True
                    parse["needs_recommendations"] = True
                elif country_scope:
                    # They asked about countries and there is no country pool to
                    # answer with: an empty wishlist, and an origin this app
                    # holds no geography for at all - somewhere outside
                    # COUNTRY_NEIGHBOURS entirely, e.g. a traveller who has
                    # stored "Morocco" as their location.
                    #
                    # This branch used to fire for Japan, Australia, Mongolia,
                    # New Zealand, South Korea and Myanmar too, because those six
                    # were deliberately given no neighbours. They have five each
                    # now, so the only way to reach this is a genuinely unknown
                    # origin. Handing that to the
                    # town-level agent would answer a country question with
                    # towns again, which is the whole bug. Say what we hold and
                    # ask, rather than quietly changing the subject.
                    intent = "memory"
                    state["route_note"] = (
                        f"COUNTRY-LEVEL QUESTION, NO ONWARD COUNTRIES HELD. They are "
                        f"asking about leaving {here_country.title()}, and this app "
                        f"holds no onward-country options from there and has nothing "
                        f"on their wishlist to weigh instead. Say that plainly, say "
                        f"what you would need from them (somewhere they are "
                        f"considering, or a wishlist entry), and do NOT name "
                        f"countries, routes, flights or prices from your own knowledge."
                    )
                    trace.note(
                        "routing.no_country_options",
                        f"no onward countries held for {here_country}",
                    )

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
            graph.make_local_guide(), state, message, str(user_id), adk_session_id(user_id)
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
            graph.make_discovery_agent(), state, message, str(user_id), adk_session_id(user_id)
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
            graph.make_concierge(), state, message, str(user_id), adk_session_id(user_id)
        )
    return text.strip() or "I'm not sure how to help with that yet.", [], ["concierge"]


_RATE_LIMIT_WAIT_RE = re.compile(r"try again in ([\d.]+)\s*s", re.IGNORECASE)


def _rate_limit_backoff_seconds(exc: Exception, attempt: int) -> float | None:
    """How long to wait before retrying ``exc``, or None if it is not a
    rate-limit error at all - a non-rate-limit failure retrying immediately,
    as these loops already did, is fine; it is usually a transient blip, not
    quota that needs time to actually recover.

    Reproduced live: the specialists and the Decision-Weigher share this
    org's real gpt-4o rate limit (30,000 tokens/minute, the OpenAI default
    starting tier - see notes/01-agent-architecture.md's "Model selection"
    section), and a comparison turn's concurrent specialist calls plus the
    weigher can trip a 429 in one burst. Retrying instantly into a limit that
    has not cleared yet just burns every retry attempt on the same failure -
    which is exactly how a candidate's card went missing with no error ever
    surfaced to the traveller. Respecting the API's own "try again in Xs"
    hint instead gives the limit a real chance to clear before the next try.
    """
    name = type(exc).__name__
    if "RateLimit" not in name and "rate_limit" not in str(exc).lower():
        return None
    match = _RATE_LIMIT_WAIT_RE.search(str(exc))
    if match:
        return float(match.group(1)) + 0.5
    return min(2.0 * attempt, 10.0)


async def _run_one_specialist(
    agent: LlmAgent,
    key: str,
    state: dict[str, Any],
    message: str,
    user_id: int,
    trace: Trace,
    step_name: str | None = None,
) -> tuple[str, str, list[str], str | None]:
    """Run one specialist. Never raises: a failure is reported, not propagated.

    No explicit parent handle is threaded through any more: this runs inside
    ``asyncio.gather`` under the ``agents.fan_out`` span (see
    ``_run_comparison``), and OpenTelemetry's context propagation - which
    survives a Task being spawned mid-context, copying it at creation time -
    is what nests this call's auto-instrumented ADK activity under that span
    correctly, with no manual wiring.

    ``step_name`` overrides the local trace step's label - used by
    ``_run_specialist_batched`` so two concurrent chunks of the same agent
    show up as distinct rows in this app's own "what ran" panel rather than
    both being labelled e.g. "logistics_agent". It never affects the real,
    auto-instrumented ADK/OpenAI span Langfuse records for the call.
    """
    name = step_name or agent.name
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            with trace.local_step(name):
                text, final_state, tool_calls = await _run_agent(
                    agent, state, message, str(user_id), adk_session_id(user_id)
                )
                output = str(final_state.get(key) or text or "")

            trace.set_span_summary(name, output[:180] or "(no output)")
            if output.strip():
                return key, output, tool_calls, None
            last_error = RuntimeError("specialist produced no output")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "specialist %s attempt %d failed: %s", name, attempt, exc
            )
            wait = _rate_limit_backoff_seconds(exc, attempt)
            if wait:
                await asyncio.sleep(wait)
    return key, "", [], f"{type(last_error).__name__}: {last_error}"


def _chunk(items: list[str], size: int) -> list[list[str]]:
    if size <= 0 or len(items) <= size:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


async def _run_specialist_batched(
    agent: LlmAgent,
    key: str,
    state: dict[str, Any],
    message: str,
    user_id: int,
    trace: Trace,
    candidates: list[str],
    batch_size: int,
) -> tuple[str, str, list[str], str | None]:
    """Like ``_run_one_specialist``, but splits ``candidates`` into chunks of
    at most ``batch_size`` and merges the reports.

    Logistics and Recommendations ask for far more detail per destination than
    Weather does (visa + two route options + border notes, or a mandatory
    budget/activities/transport/warning/citation block, versus Weather's score
    line + 2-4 sentences). Reproduced live at ``max_comparison_candidates=10``
    on ``specialist_model`` (``gpt-4o-mini``): both agents called their
    required tool once for every candidate every time, but silently stopped
    WRITING about some of them before finishing - Logistics dropped one
    candidate a turn, Recommendations as few as half of ten in one run, a
    different subset each time. It is candidate-count-times-output-load
    exceeding the cheap model's capacity, not a broken tool call, so no batch
    is ever asked to fully write up more than ``batch_size`` destinations.
    See ``settings.specialist_batch_size`` and notes/05.

    A chunk that fails outright does not discard the others - same
    isolate-don't-propagate rule ``_run_one_specialist`` already follows one
    level up, just applied within one specialist instead of across the three.
    """
    chunks = _chunk(candidates, batch_size)
    if len(chunks) <= 1:
        return await _run_one_specialist(agent, key, state, message, user_id, trace)

    async def _run_chunk(index: int, chunk: list[str]) -> tuple[str, list[str], str | None]:
        chunk_state = dict(state)
        chunk_state["candidates"] = ", ".join(chunk)
        _, output, tool_calls, error = await _run_one_specialist(
            agent,
            key,
            chunk_state,
            message,
            user_id,
            trace,
            step_name=f"{agent.name}[{index + 1}/{len(chunks)}]",
        )
        return output, tool_calls, error

    results = await asyncio.gather(
        *(_run_chunk(i, chunk) for i, chunk in enumerate(chunks))
    )

    outputs = [output for output, _, _ in results if output.strip()]
    tool_calls = [call for _, calls, _ in results for call in calls]
    errors = [error for _, _, error in results if error]

    merged_output = "\n\n".join(outputs)
    # Only surface an error if EVERY chunk failed - a partial report (some
    # candidates covered, one batch lost to a transient failure) is still
    # useful to the weigher and is not the same failure as an empty report.
    combined_error = "; ".join(errors) if errors and not merged_output else None
    return key, merged_output, tool_calls, combined_error


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
    # ALL THREE specialists run on a comparison. turn_parser's needs_* flags are
    # kept in the parse (they are useful for seeing what it thought) but are no
    # longer read here, because the parser was observed skipping, in turn, each
    # of the three inputs a comparison is made of:
    #
    #   season-nepal-monsoon   "a big trek in July. Nepal or Sri Lanka?"
    #                          -> needs_weather: false. No weather agent ran at
    #                             all, and Nepal - in monsoon, the destination
    #                             the case exists to rule out - ranked first.
    #   rag-budget-numbers     "How much a day should I budget for Laos versus
    #                          Cambodia?" -> needs_recommendations: false, so
    #                             the agent that owns the budget corpus never
    #                             ran, and the tips namespace was never searched
    #                             for a question that is entirely about budget.
    #
    # Both failures are silent: no error, no empty-report warning, just a
    # weigher ranking on whatever it did receive. And both are the same mistake
    # the rest of this codebase refuses to leave to a model (the intent
    # override, the country-scope override): a cheap deterministic rule beats a
    # classifier guessing at what a turn needs. The saving was never large -
    # this only ever skipped an agent on a turn the parser misread - and a
    # comparison missing one of its three inputs is not a cheaper answer, it is
    # a wrong one.
    specialists = graph.build_specialists(
        needs_weather=True,
        needs_logistics=True,
        needs_recommendations=True,
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
    # Weather's per-destination ask is light enough that it covers a full
    # candidate list reliably on specialist_model - only the two heavier
    # specialists get split into batches. See _run_specialist_batched.
    BATCHED_KEYS = {"logistics_assessment", "recommendations"}
    with trace.span("agents.fan_out", metadata={"specialists": names}) as fan_span:
        outcomes = await asyncio.gather(
            *(
                _run_specialist_batched(
                    agent, key, state, message, user_id, trace,
                    candidates or [], settings.specialist_batch_size,
                )
                if key in BATCHED_KEYS
                else _run_one_specialist(agent, key, state, message, user_id, trace)
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
    # including any live-sourced hit from live_lookup - checking it here is how
    # the weigher finds out a gap got filled this turn instead of relying on
    # the stale, necessarily-more-cautious pre-run note.
    #
    # "origin", not "namespace": live-sourced documents now live in the same
    # per-kind namespace as curated content (see backend/rag/live_lookup.py),
    # so namespace alone no longer distinguishes them.
    recorder = current_recorder()
    live_sourced = {
        (r.get("destination") or "").strip().lower()
        for r in (recorder.retrieved if recorder else [])
        if r.get("origin") == "live" and r.get("destination")
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
                    str(user_id), adk_session_id(user_id),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("decision_weigher attempt %d failed: %s", attempt, exc)
                wait = _rate_limit_backoff_seconds(exc, attempt)
                if wait:
                    await asyncio.sleep(wait)
                continue
            decision = graph.parse_json_block(str(final_state.get("decision") or "")) or                 graph.parse_json_block(text) or {}
            cards = _coerce_cards(decision.get("cards"))
            reply = str(decision.get("reply") or "").strip()
            if cards:
                break
    if not reply:
        # text.strip() is the LAST attempt's raw model output, kept as a fallback
        # for the genuine-prose case the loop above expects (weigher answered in
        # plain text instead of JSON). But if parse_json_block couldn't parse it
        # *because* it's a malformed/unparseable JSON blob rather than prose,
        # showing it raw leaks the payload straight into the chat UI - reported
        # 2026-09-14 (rachel.B) when a template brace bug in DECISION_INSTRUCTION
        # made the model echo back doubled braces that parse_json_block couldn't
        # parse. Never surface something that merely looks like JSON as if it
        # were the traveller-facing reply.
        fallback = text.strip()
        if fallback.startswith(("{", "[", "```")):
            fallback = ""
        reply = fallback or "I could not put together a comparison for that."
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
