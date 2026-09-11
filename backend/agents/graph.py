"""Agent definitions for the Onward graph.

Shape:

    turn_parser  (explicit memory extraction -> Python calls store.update_profile)
         |
    ParallelAgent  [ weather_agent | logistics_agent | recommendations_agent ]
         |                (only the specialists this turn actually needs)
    decision_weigher  (reads all three from session state, ranks candidates)

Note on structured output: ADK's ``output_schema`` serialises to
``response_format.response_schema``, which the OpenAI API rejects through
litellm. So the agents that must return JSON are prompted for it and parsed
tolerantly in Python (see ``parse_json_block``), with a pydantic validation pass.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from backend.agents.discovery_tools import (
    discover_next_destinations,
    get_traveller_feedback,
)
from backend.agents.place_tools import (
    find_food_near,
    find_hostels,
    get_booking_links,
    get_places_recommendations,
    suggest_areas_to_stay,
)
from backend.agents.tools import (
    check_route,
    check_seasonal_conditions,
    search_backpacker_tips,
    search_seasonal_notes,
    search_visa_rules,
)
from backend.config import settings

APP_NAME = "onward"


@lru_cache(maxsize=4)
def _cached_model(model_name: str) -> LiteLlm:
    return LiteLlm(model=f"openai/{model_name}", api_key=settings.openai_api_key)


def build_model() -> LiteLlm:
    """LiteLlm is ADK's bridge to non-Gemini providers; we point it at OpenAI.

    Shared rather than constructed per agent: litellm keeps process-global client
    state, and building a fresh instance for each of the concurrently-running
    specialists was implicated in intermittent "coroutine raised StopIteration"
    failures during the fan-out.
    """
    return _cached_model(settings.llm_model)


# --------------------------------------------------------------------------- #
# JSON helpers
# --------------------------------------------------------------------------- #
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_json_block(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of a JSON object from a model reply.

    Handles bare JSON, fenced JSON, and JSON with prose wrapped around it.
    Returns None rather than raising, so a malformed reply degrades to a
    text-only answer instead of a 500.
    """
    if not text:
        return None
    candidates: list[str] = []

    fenced = _FENCE_RE.search(text)
    if fenced:
        candidates.append(fenced.group(1))
    candidates.append(text)

    # last resort: the outermost {...} span
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


# --------------------------------------------------------------------------- #
# shared prompt fragments
# --------------------------------------------------------------------------- #
HOUSE_STYLE = """
You are part of Onward, an assistant for long-term budget backpackers already on
the road. Your user is not a package tourist: they sleep in dorms and guesthouses,
travel by night bus, slow boat and budget airline, and care about cost per day,
visa runs and whether a place is worth the journey.

Rules that apply to every agent in this system:
- Never ask the user for something already in the trip profile below. It is theirs,
  read it and use it.
- Be concrete. Numbers, months, hours, dollars. No "it depends" without the detail.
- If a tool returns "known": false or no passages, say plainly that you do not have
  verified data for that, rather than inventing a figure.
- Visa rules and prices change; tell the user to confirm visas with the official
  government source before booking.
"""

MEMORY_BLOCK = """
--- TRIP PROFILE (remembered for this account, do not ask for it again) ---
{memory_block?}
{travel_block?}
--- END TRIP PROFILE ---
"""

# Given to the specialists as well as the weigher. The specialists run first, and
# a confabulated specialist report gives the weigher plausible material to pass
# on even when the weigher itself is behaving.
COVERAGE_BLOCK = """
--- KNOWLEDGE COVERAGE (computed in code, not negotiable) ---
{coverage_note?}
--- END COVERAGE ---
"""


# --------------------------------------------------------------------------- #
# 1. turn parser  (the orchestrator's parsing step)
# --------------------------------------------------------------------------- #
TURN_PARSER_INSTRUCTION = (
    """
You are the parsing step of the Onward orchestrator. You do not talk to the user.
Read their latest message together with the stored trip profile, and return JSON
describing what changed and what work the specialists need to do.
"""
    + MEMORY_BLOCK
    + """
Today's date is {today?}.
Places awaiting a review: {pending_reviews?}
The user's message is the conversation input you have been given.

Return ONLY a raw JSON object, no code fences, with exactly these keys:

{{
  "intent": "compare",
  "profile_updates": {{}},
  "departures": [],
  "visits": [],
  "wishlist_adds": [],
  "wishlist_removes": [],
  "reviews": [],
  "candidate_destinations": [],
  "focus_location": null,
  "travel_month": null,
  "question_focus": "",
  "needs_weather": true,
  "needs_logistics": true,
  "needs_recommendations": true
}}

"intent" is the single most important field. One of:
- "compare"  : weighing two or more destinations against each other.
- "discover" : open "where should I go next" from where they are, no options named.
- "local"    : on-the-ground questions about ONE place - where to stay, what to
               eat, what to do, hostels, areas, nightlife.
- "memory"   : greetings, or asking what you remember about them.
- "review"   : they are giving an opinion or rating about a place they visited.

Field rules:
- "profile_updates": only fields stated or changed in THIS message. Allowed keys:
  nationality, budget_band (shoestring|mid|comfortable),
  travel_style (slow|balanced|fast), climate_preference (cool|temperate|hot|no_preference),
  current_location, trip_start_date (YYYY-MM-DD), trip_end_date (YYYY-MM-DD),
  visa_deadline_date (YYYY-MM-DD), visa_deadline_note, interests.
  Empty object if nothing new. Never repeat values already in the profile.
- "visits": places they are AT or have ARRIVED in, as
  [{{"location": "Chiang Mai", "location_type": "city", "country": "Thailand",
     "arrival_date": "YYYY-MM-DD or null"}}].
  Include a place when they say they are there, have just arrived, or ask an
  on-the-ground question that only makes sense if they are there ("any good
  hostels here in Pai"). Do NOT include somewhere they are merely considering.
- "departures": places they have LEFT, as
  [{{"location": "Laos", "location_type": "country", "departure_date": "YYYY-MM-DD or null"}}].
  Only on a clear signal that they have gone, or are leaving now.
- "wishlist_adds": places they say they want to go, as
  [{{"location": "Pai", "location_type": "city", "country": "Thailand", "priority": 1}}].
  Priority 1 high, 2 medium, 3 low. Wanting to go is enough; it need not be booked.
- "wishlist_removes": places they have decided AGAINST, as plain location strings.
- "reviews": opinions about somewhere they have been, as
  [{{"location": "Pai", "rating": 5, "notes": "what they said, in their words"}}].
  rating is 1-5 and may be null if they gave only prose. Convert plain language
  honestly: "loved it" is 5, "it was fine" is 3, "overrated" is 2.
- "candidate_destinations": lowercase places they are choosing between, for
  "compare". Include EVERY place they name, including ones you believe this
  assistant has no data for - a later step checks coverage and needs to see them.
  Anywhere they name two or more options, intent is "compare", even if the
  question is about what to do there rather than which to pick.
  Only leave this empty when they name no options at all, and then set intent to
  "discover".
- "focus_location": for "local" intent, the single place the question is about.
- "travel_month": the month the trip in question would happen, as a month name.
  Infer from the message, else trip_start_date, else today.
- "needs_*": false only when that specialist is clearly irrelevant.
"""
)


def make_turn_parser() -> LlmAgent:
    return LlmAgent(
        name="turn_parser",
        model=build_model(),
        description="Parses the user turn into memory updates and a dispatch plan.",
        instruction=TURN_PARSER_INSTRUCTION,
        output_key="turn_parse",
    )


# --------------------------------------------------------------------------- #
# 2. specialists
# --------------------------------------------------------------------------- #
WEATHER_INSTRUCTION = (
    HOUSE_STYLE
    + MEMORY_BLOCK
    + COVERAGE_BLOCK
    + """
You are the Weather/Timing specialist.

Candidate destinations: {candidates?}
Travel month: {travel_month?}
Question: {user_question?}

You MUST call check_seasonal_conditions once for EVERY candidate destination,
using the travel month above. You MUST also call search_seasonal_notes for every
candidate to get the prose detail. Do not answer before calling both tools.

Your data is a curated seasonal table, not a live forecast: it is reliable for
"is this monsoon season" and cannot know about an anomalous year or a specific
storm. Say so if the user seems to want a forecast.

Then write 2-4 sentences per destination covering: the season it falls in, the
rating (good / mixed / avoid), and the practical consequence for a backpacker -
cancelled ferries, impassable roads, haze, crowds, price. Lead with any
destination rated "avoid" and state clearly that it is a bad time to go.
"""
)

LOGISTICS_INSTRUCTION = (
    HOUSE_STYLE
    + MEMORY_BLOCK
    + COVERAGE_BLOCK
    + """
You are the Logistics/Route specialist.

Candidate destinations: {candidates?}
Traveller is currently in: {current_location?}
Passport: {nationality?}
Travel month: {travel_month?}
Question: {user_question?}

You MUST call search_visa_rules once for EVERY candidate destination, passing the
traveller's passport nationality. You MUST call check_route once for every
candidate, from their current location. Do not state any visa rule, price or
journey time that did not come back from a tool.

If the passport nationality is unknown, say that visa guidance is generic until
they tell you their nationality, and still retrieve what you can.

Report per destination:
- Visa: what they get, cost, how long it lasts, and crucially any ADVANCE LEAD
  TIME (e.g. an e-visa that takes days to issue), because that can rule a
  destination out entirely on a short-notice plan.
- Route: overland option with hours and cost, flight option with hours and cost,
  and which is actually the better call given their budget band and pace.
- Border notes and scams worth knowing.

If the trip profile shows a HARD DEADLINE (a visa or permit expiry), check every
recommendation against it explicitly and say whether it fits.
"""
)

RECOMMENDATIONS_INSTRUCTION = (
    HOUSE_STYLE
    + MEMORY_BLOCK
    + COVERAGE_BLOCK
    + """
You are the Recommendations specialist for backpackers.

Candidate destinations: {candidates?}
Their interests: {interests?}
Budget band: {budget_band?}
Travel pace: {travel_style?}
Question: {user_question?}

You MUST call search_backpacker_tips once for EVERY candidate destination before
writing anything. Everything you recommend must come from retrieved passages or
from a tool result.

You also have live tools. Use them when the question calls for them:
- find_hostels: where to actually sleep, with real ratings and booking links.
- suggest_areas_to_stay: WHICH PART of a town to base yourself in. Prefer this
  over listing individual hostels when someone is choosing a place to stay.
- find_food_near: where to eat, including a specific dish.
- get_places_recommendations: anything else nearby - bars, markets, laundry, ATMs.
- get_traveller_feedback: what previous travellers said about a place after
  visiting. Present it as other backpackers' opinions, anonymously, never as fact.

Rules for the live tools:
- Results are ranked by a Bayesian weighted score, NOT raw star rating. When you
  quote a place, give its rating AND its review count, because "4.9 from 12
  reviews" and "4.6 from 2,400" mean very different things.
- If a tool returns configured:false, say plainly that live place data is not
  available on this deployment. Never invent hostel names, ratings or addresses.
- Booking links are affiliate links. Say so when you share them.

This is the important part: give BACKPACKER advice, not tourist-brochure advice.
Hostel scenes and dorm prices, realistic daily budgets in local terms, free and
cheap things, overland routes other backpackers actually take, ethical warnings,
and scam or safety notes. Do not produce a list of famous landmarks.

For every destination you MUST give all four of these, not a subset:
  1. a realistic daily budget with a number,
  2. two or three specific things worth doing, and why they suit this traveller,
  3. how backpackers actually get there and around - the night bus, sleeper
     train, slow boat or budget flight, with hours or price where you have them,
  4. one practical warning: a scam, a safety risk, or an ethical caution.

Omitting the transport line or the warning is the most common way this answer
turns into brochure copy. A list of nice things to see, with no cost, no route
and no warning, has failed the traveller.

Cite the retrieved passage you used for each destination by its source_id, in
square brackets, like [tips-vietnam]. If you could not retrieve a passage for a
destination, say so explicitly instead of filling the gap from memory.
"""
)


def make_weather_agent() -> LlmAgent:
    return LlmAgent(
        name="weather_agent",
        model=build_model(),
        description="Assesses seasonal fit for candidate destinations.",
        instruction=WEATHER_INSTRUCTION,
        tools=[check_seasonal_conditions, search_seasonal_notes],
        output_key="weather_assessment",
    )


def make_logistics_agent() -> LlmAgent:
    return LlmAgent(
        name="logistics_agent",
        model=build_model(),
        description="Visa requirements, routes, journey time and cost.",
        instruction=LOGISTICS_INSTRUCTION,
        tools=[search_visa_rules, check_route],
        output_key="logistics_assessment",
    )


def make_recommendations_agent() -> LlmAgent:
    return LlmAgent(
        name="recommendations_agent",
        model=build_model(),
        description="Backpacker-specific things to do and budget notes from the RAG store.",
        instruction=RECOMMENDATIONS_INSTRUCTION,
        tools=[
            search_backpacker_tips,
            find_hostels,
            suggest_areas_to_stay,
            find_food_near,
            get_places_recommendations,
            get_traveller_feedback,
        ],
        output_key="recommendations",
    )


# --------------------------------------------------------------------------- #
# 3. decision weigher
# --------------------------------------------------------------------------- #
DECISION_INSTRUCTION = (
    HOUSE_STYLE
    + MEMORY_BLOCK
    + """
You are the Decision-Weigher. The specialists have reported:

--- WEATHER / TIMING ---
{weather_assessment?}

--- LOGISTICS / VISAS / ROUTES ---
{logistics_assessment?}

--- BACKPACKER RECOMMENDATIONS ---
{recommendations?}

The user asked: {user_question?}
Candidates: {candidates?}
Travel month: {travel_month?}

--- KNOWLEDGE COVERAGE (computed in code, not negotiable) ---
{coverage_note?}
--- END COVERAGE ---

--- HARD DEADLINE (computed in code, not negotiable) ---
{deadline_note?}
--- END DEADLINE ---

Weigh these against the traveller's OWN stated priorities in the trip profile
above - their budget band, their pace, their climate preference and any hard
deadline. A destination that is wrong for their stated preferences should rank
lower even if it is objectively pleasant. Say which preference drove the call.

Season is one input, not the whole answer. If everywhere is in a poor season, say
so briefly and then still give the traveller something to act on: which option is
least affected, what to do there anyway, and how to work around the weather. A
reply that is mostly weather warnings with no budget, route or activity detail has
failed, even when the weather warnings are correct.

Hard rules:
1. A destination the weather specialist rated "avoid" CANNOT be ranked first
   unless the user has explicitly said they accept that season. Put the seasonal
   problem in its cons and in season_flag.
2. A destination that cannot be reached in time because of a visa lead time or a
   hard deadline in the profile CANNOT be ranked first. Put it in visa_flag.
3. Never invent a fact the specialists did not report.
4. Any destination named in the COVERAGE WARNING above CANNOT be ranked first and
   CANNOT be given specifics. Set its verdict to "unknown" and say in the reply
   that you hold no verified data for it.
5. If the HARD DEADLINE block names a date, you MUST state that date explicitly in
   your reply and say whether your top recommendation fits inside it. Do not
   silently plan past a deadline the traveller is under.

CARRY THE DETAIL THROUGH. The specialists did the research; your job is to weigh
it, NOT to compress it into generalities. A reply that says "lower visa costs" or
"cheaper daily costs" instead of the actual figures has thrown away the work.
Your "reply" MUST contain at least two concrete specifics taken from the
specialist reports above - for example a daily budget in dollars, a visa type with
its cost and duration, an e-visa lead time in days, or a journey time in hours
with its price. Use the real numbers the specialists reported. Never replace a
number with an adjective.

Return ONLY a raw JSON object, no code fences:

{{
  "reply": "4-8 sentences to the traveller, conversational. Lead with your recommendation and the single most important reason. Include at least two concrete figures carried over from the specialists (daily budget, visa cost/duration/lead time, or journey hours and price). Explicitly name the stored profile values you used - say their budget band, their pace, where they are now and their dates back to them in passing, so it is obvious you did not need to ask. Never end by asking them for something already in the profile.",
  "cards": [
    {{
      "destination": "Country Name",
      "rank": 1,
      "verdict": "go | maybe | avoid | unknown",
      "rationale": "one line on why it sits at this rank",
      "pros": ["specific, concrete"],
      "cons": ["specific, concrete"],
      "season_flag": "null, or the seasonal warning",
      "visa_flag": "null, or the visa/deadline warning",
      "est_cost_note": "indicative daily budget and cost to get there",
      "backpacker_notes": ["3-4 concrete specifics lifted from the Recommendations and Logistics specialists for THIS destination. Cover all of: (a) a cost with its number - dorm price, daily budget or an entry fee; (b) a named thing to do that a backpacker actually does, with the place name; (c) how you get there or get around - the bus, train, slow boat or flight with its hours or price; (d) a scam, safety or ethical warning. Keep the specialists' actual figures and place names. Empty list only if that destination has no retrieved content."],
      "source_ids": ["the source ids the Recommendations specialist cited for this destination, e.g. tips-vietnam"]
    }}
  ]
}}

Include one card per candidate, ranked 1..n with no ties.

The "backpacker_notes" are the part the traveller actually acts on. Fill them from
the Recommendations specialist's report verbatim enough to keep its numbers and
place names - a dorm price, the name of a route or trek, a specific warning. Do
not paraphrase them into generic advice, and do not write them from your own
knowledge: if the specialist did not report something for a destination, leave
that destination's notes empty and say so in the reply.
"""
)


def make_decision_weigher() -> LlmAgent:
    return LlmAgent(
        name="decision_weigher",
        model=build_model(),
        description="Ranks candidates against the traveller's stated priorities.",
        instruction=DECISION_INSTRUCTION,
        output_key="decision",
    )


# --------------------------------------------------------------------------- #
# 4. concierge (no destination comparison needed)
# --------------------------------------------------------------------------- #
CONCIERGE_INSTRUCTION = (
    HOUSE_STYLE
    + MEMORY_BLOCK
    + """
The user has asked something that does not need a destination comparison - a
greeting, a follow-up, or a question about what you remember about them.

Question: {user_question?}

Answer directly and briefly from the trip profile above. If they are asking what
you remember, list it back accurately: never claim to remember something that is
"(unknown)" in the profile, and never invent a value. If the profile is mostly
empty, say what you still need and point them at the My Preferences screen where
they can set it directly.
"""
)


def make_concierge() -> LlmAgent:
    return LlmAgent(
        name="concierge",
        model=build_model(),
        description="Answers memory and small-talk turns from the trip profile.",
        instruction=CONCIERGE_INSTRUCTION,
        output_key="concierge_reply",
    )


# --------------------------------------------------------------------------- #
# 5. assembling the fan-out
# --------------------------------------------------------------------------- #
def build_specialists(
    needs_weather: bool, needs_logistics: bool, needs_recommendations: bool
) -> list[tuple[LlmAgent, str]]:
    """Pick the specialists this turn needs, each with the state key it writes.

    The set is chosen per turn, which is the orchestrator deciding which agents are
    relevant rather than always paying for all three.

    WHY NOT ADK's ParallelAgent: it drives its concurrent sub-agents through a
    shared async generator, and on teardown that intermittently raised
    "aclose(): asynchronous generator is already running", which killed the whole
    turn - the eval case rag-cites-source caught it twice, returning zero
    comparison cards. The orchestrator now runs each specialist in its own Runner
    under asyncio.gather instead. That is still a genuine parallel fan-out, and it
    additionally isolates failures: one specialist erroring no longer takes the
    other two, or the final recommendation, down with it.
    """
    chosen: list[tuple[LlmAgent, str]] = []
    if needs_weather:
        chosen.append((make_weather_agent(), "weather_assessment"))
    if needs_logistics:
        chosen.append((make_logistics_agent(), "logistics_assessment"))
    if needs_recommendations:
        chosen.append((make_recommendations_agent(), "recommendations"))
    if not chosen:
        chosen.append((make_weather_agent(), "weather_assessment"))
    return chosen


# --------------------------------------------------------------------------- #
# 6. onboarding  (runs on the first few turns of a brand-new account)
# --------------------------------------------------------------------------- #
ONBOARDING_INSTRUCTION = (
    HOUSE_STYLE
    + MEMORY_BLOCK
    + """
You are onboarding a traveller who has just created an account. This is a short
CONVERSATION, not a form. Two or three sentences, warm, one topic at a time.
Never present a numbered list of questions.

Still missing: {onboarding_gaps?}
Already captured: {onboarding_captured?}

Ask about the FIRST item in "Still missing" and nothing else. Briefly acknowledge
what they just told you before you ask - and if "Already captured" shows we now
know something, do NOT ask for it again.

If nothing is missing, do not ask another question: thank them, say they can
refine anything later in My Preferences, and stop.

If they ask to skip, accept immediately and stop asking.

Never invent travel history or preferences. Only reflect back what they said.
Reply with your conversational message only - no JSON, no lists of fields.
"""
)

# Extraction is a SEPARATE agent from the conversation. Asking one agent to both
# chat warmly and emit a machine-readable block did not work: gpt-4o-mini reliably
# produced the chat and silently dropped the block, so onboarding captured nothing
# and looped. Splitting them makes each job unambiguous.
ONBOARDING_EXTRACTOR_INSTRUCTION = (
    """
You extract structured travel facts from one message. You never talk to the user.
"""
    + MEMORY_BLOCK
    + """
Today's date is {today?}.
The user's message is the conversation input you have been given.

Return ONLY a raw JSON object, no code fences, no prose:

{{
  "travel_history": [{{"location": "Bangkok", "location_type": "city", "country": "Thailand", "order": 1}}],
  "wishlist": [{{"location": "Pai", "location_type": "city", "country": "Thailand", "priority": 1}}],
  "interests": [],
  "budget_band": null,
  "travel_style": null,
  "social_style": null,
  "current_location": null,
  "nationality": null,
  "trip_start_date": null,
  "trip_end_date": null,
  "skip_requested": false
}}

Rules:
- Only what THIS message states. Empty list or null for anything not mentioned.
- "travel_history": EVERY place they say they have already been, in the order
  they said them - if they name three towns, return three entries, not one. The
  place they are in NOW also belongs here, and also in "current_location".
  Include a place even when they mention it only in passing ("then Koh Tao for
  diving" is a visit).
- "wishlist": places they want to go but have not been. priority 1 high, 2 medium,
  3 low; use 1 if they sound keen, else 2.
- "location_type" is country, city, town or region. Prefer city/town granularity.
- "interests" are lowercase single words where possible: nature, food, nightlife,
  trekking, diving, history, beaches, surfing, culture, photography, wildlife.
- "budget_band" is shoestring, mid or comfortable. "travel_style" is slow,
  balanced or fast. "social_style" is solo, couple or group.
- "skip_requested" is true only if they clearly want to stop answering.
"""
)


def make_onboarding_agent() -> LlmAgent:
    return LlmAgent(
        name="onboarding_agent",
        model=build_model(),
        description="Conversationally captures a new traveller's history, wishlist and preferences.",
        instruction=ONBOARDING_INSTRUCTION,
        output_key="onboarding_reply",
    )


def make_onboarding_extractor() -> LlmAgent:
    return LlmAgent(
        name="onboarding_extractor",
        model=build_model(),
        description="Extracts structured travel facts from an onboarding message.",
        instruction=ONBOARDING_EXTRACTOR_INSTRUCTION,
        output_key="onboarding_capture",
    )


# --------------------------------------------------------------------------- #
# 7. local guide  (they are somewhere and want things nearby, not a comparison)
# --------------------------------------------------------------------------- #
LOCAL_GUIDE_INSTRUCTION = (
    HOUSE_STYLE
    + MEMORY_BLOCK
    + """
You are the on-the-ground guide. The traveller is asking about a place they are
in or about to be in - where to stay, what to eat, what to do nearby - rather
than asking you to compare destinations.

Place in question: {focus_location?}
Question: {user_question?}
Budget band: {budget_band?}
Interests: {interests?}

Use your tools before answering, and never invent a venue:
- suggest_areas_to_stay when they are deciding WHERE in a town to base themselves.
- find_hostels when they want actual beds. Mention the booking links are affiliate.
- find_food_near for eating, including a named dish.
- get_places_recommendations for anything else nearby.
- search_backpacker_tips for the curated budget and safety context.
- get_traveller_feedback for what previous travellers said about the place.

When you quote a place, always give its rating AND review count together.
Results are ranked by a weighted score that discounts thinly-reviewed places, so
do not re-sort them by raw rating. If a tool reports configured:false, say that
live place data is unavailable here rather than making somewhere up.

Answer in short paragraphs or a tight list. Lead with the single thing you would
actually tell a mate arriving tonight.
"""
)


def make_local_guide() -> LlmAgent:
    return LlmAgent(
        name="local_guide",
        model=build_model(),
        description="Answers on-the-ground questions about a specific town.",
        instruction=LOCAL_GUIDE_INSTRUCTION,
        tools=[
            suggest_areas_to_stay,
            find_hostels,
            find_food_near,
            get_places_recommendations,
            search_backpacker_tips,
            get_traveller_feedback,
            get_booking_links,
        ],
        output_key="local_guide_reply",
    )


# --------------------------------------------------------------------------- #
# 8. next-hop discovery  (where next from HERE, at town level)
# --------------------------------------------------------------------------- #
def make_discovery_agent() -> LlmAgent:
    return LlmAgent(
        name="discovery_agent",
        model=build_model(),
        description="Suggests onward towns from the traveller's current location.",
        instruction=(
            HOUSE_STYLE
            + MEMORY_BLOCK
            + """
You suggest where to go NEXT, at town level, from where the traveller is now.

Currently in: {current_location?}
Interests: {interests?}
Question: {user_question?}

--- ROUTE COVERAGE (computed in code, not negotiable) ---
{route_note?}
--- END COVERAGE ---

--- HARD DEADLINE (computed in code, not negotiable) ---
{deadline_note?}
--- END DEADLINE ---

You MUST call discover_next_destinations with their current location before
answering. It returns the curated route knowledge plus any real traveller
feedback. If it reports found:false, say plainly that you hold no route data for
where they are, and do not invent journey times or onward legs.

If the HARD DEADLINE block names a date, state that date explicitly in your reply
and say whether each option fits inside it. Never quietly plan past a deadline
the traveller is under.

Prefer somewhere already on their wishlist when it is a sensible next hop, and
say that is why you picked it. Give 2-4 options, each with the journey from here
(time and rough cost, only if the route knowledge gave it) and one line on who it
suits. Cite the route source id you used, like [route-chiang-mai].
"""
        ),
        tools=[discover_next_destinations, get_traveller_feedback],
        output_key="discovery_reply",
    )
