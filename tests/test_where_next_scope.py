"""Which SCOPE a "where next" turn is answered at, and what happens with no origin.

All of this is the fallout of bug report #3 (2026-09-14, test1234): asked three
times, three ways, which COUNTRY to go to next - once with a visa about to
expire - and answered every time with towns inside the country being left,
because scope was a side effect of how precisely the stored location happened
to be recorded rather than a reading of the question. See
notes/05-guards-and-prompting.md.

The turn is driven end to end through run_turn with the LLM calls stubbed, so
these assert the orchestrator's real routing, not a re-implementation of it.

    python -m pytest tests/test_where_next_scope.py -q
"""
from __future__ import annotations

import asyncio
import importlib
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def app_env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="onward-scope-test-")
    monkeypatch.setenv("DATA_DIR", tmp)
    monkeypatch.setenv("DB_PATH", str(Path(tmp) / "test.sqlite3"))
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-pw")
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "")
    monkeypatch.setenv("PINECONE_API_KEY", "")
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("SERVE_FRONTEND", "false")
    # run_turn short-circuits entirely without a key; the agents themselves are
    # stubbed below, so nothing is ever sent anywhere.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")

    import backend.config as config

    importlib.reload(config)
    import backend.db as db

    importlib.reload(db)
    import backend.memory.store as store

    importlib.reload(store)
    import backend.memory.travel as travel

    importlib.reload(travel)
    db.init_db()
    return {"config": config, "db": db, "store": store, "travel": travel}


def make_user(db, username: str) -> int:
    from backend.security import hash_password

    with db.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, status) VALUES (?,?, 'approved')",
            (username, hash_password("password123")),
        )
        user_id = int(cursor.lastrowid)
        conn.execute("INSERT OR IGNORE INTO trip_profile (user_id) VALUES (?)", (user_id,))
    return user_id


def run_stubbed_turn(monkeypatch, user_id: int, message: str, parse: dict) -> dict:
    """Run one real turn with turn_parser's output fixed and every answering
    agent replaced by a recorder. Returns which agent answered and the state it
    was handed."""
    import backend.agents.runner as runner
    from backend.rag import live_lookup

    monkeypatch.setattr(live_lookup, "classify_season", lambda country, month: None)

    seen: dict = {"sessions": []}
    parse.setdefault("profile_updates", {})
    parse.setdefault("candidate_destinations", [])

    async def fake_run_agent(agent, state, message_, uid, session_id):
        seen["sessions"].append((agent.name, session_id))
        if agent.name == "turn_parser":
            return "", {"turn_parse": parse}, []
        seen["agent"] = agent.name
        seen["state"] = dict(state)
        if agent.name == "decision_weigher":
            decision = '{"reply": "stub", "cards": [{"destination": "stub", "rank": 1}]}'
            return decision, {"decision": decision}, []
        return f"stub {agent.name}", {}, []

    monkeypatch.setattr(runner, "_run_agent", fake_run_agent)
    result = asyncio.run(runner.run_turn(user_id, message))
    seen["result"] = result
    return seen


def seed_traveller(env, username: str, current_location: str | None) -> int:
    store, travel, db = env["store"], env["travel"], env["db"]
    user_id = make_user(db, username)
    profile = {"nationality": "United Kingdom", "budget_band": "shoestring"}
    if current_location:
        profile["current_location"] = current_location
    store.update_profile(user_id, profile, source="user_edit")
    for place in ("Bangkok", "Chiang Mai", "Pai"):
        travel.add_travel_history(user_id, place, country="Thailand", source="onboarding")
    travel.add_wishlist(
        user_id, "Vietnam", location_type="country", country="Vietnam", priority=1
    )
    return user_id


# --------------------------------------------------------------------------- #
# the scope detector
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "message",
    [
        "which country should i go to next",
        "my visa is running out at the end of the month. what country should i go to next?",
        "i want to change country",
        "time for a visa run i think",
        "thinking about crossing the border next week",
        "what's the cheapest country from here",
    ],
)
def test_country_scope_is_detected(message):
    from backend.agents import coverage

    assert coverage.wants_country_scope(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "where should i go next",
        "Where should I go next from here?",
        "any good hostels here in Pai",
        "i love the countryside around here",
        "Pai was brilliant, easily a 5 out of 5",
        "What do you remember about me?",
    ],
)
def test_town_level_questions_are_not_forced_to_country_scope(message):
    from backend.agents import coverage

    assert coverage.wants_country_scope(message) is False


# --------------------------------------------------------------------------- #
# routing
# --------------------------------------------------------------------------- #
def test_country_question_from_a_covered_town_is_answered_with_countries(app_env, monkeypatch):
    """THE bug: standing in Pai, "which country next" went to the town-level
    discovery agent, whose only route knowledge is Thai towns."""
    user_id = seed_traveller(app_env, "country_scope", "Pai")

    seen = run_stubbed_turn(
        monkeypatch, user_id, "which country should i go to next", {"intent": "discover"}
    )

    assert seen["agent"] == "decision_weigher"
    assert seen["result"]["intent"] == "compare"
    candidates = seen["state"]["candidates"]
    assert "chiang mai" not in candidates and "mae hong son" not in candidates
    # Thailand is where they are; the answer has to be somewhere else.
    assert "thailand" not in candidates
    assert candidates.strip() and candidates != "(none named)"


def test_visa_running_out_is_treated_as_a_leave_the_country_question(app_env, monkeypatch):
    """The harmful half of the report: a visa about to expire answered with
    towns in the country they have to leave."""
    user_id = seed_traveller(app_env, "visa_scope", "Pai")

    seen = run_stubbed_turn(
        monkeypatch,
        user_id,
        "my visa is running out at the end of the month. what country should i go to next?",
        {"intent": "discover"},
    )

    assert seen["agent"] == "decision_weigher"
    assert "thailand" not in seen["state"]["candidates"]


def test_plain_where_next_from_a_town_still_gets_town_level_hops(app_env, monkeypatch):
    """The fix must not swallow the ordinary case: no country wording, stored
    town, still the town-level discovery agent (eval discovery-uses-route-corpus)."""
    user_id = seed_traveller(app_env, "town_scope", "Chiang Mai")

    seen = run_stubbed_turn(
        monkeypatch, user_id, "Where should I go next from here?", {"intent": "discover"}
    )

    assert seen["agent"] == "discovery_agent"
    assert seen["result"]["intent"] == "discover"
    assert "Route data IS held for chiang mai" in seen["state"]["route_note"]


def test_where_next_with_no_stored_location_never_reaches_the_discovery_agent(
    app_env, monkeypatch
):
    """With no origin the discovery agent picked a town out of the route history
    and answered as though they were still in it, with real curated hops for a
    place they never named. It must not get the turn at all."""
    user_id = seed_traveller(app_env, "no_location", None)

    seen = run_stubbed_turn(
        monkeypatch, user_id, "where should i go next", {"intent": "discover"}
    )

    assert seen["agent"] == "concierge"
    assert seen["result"]["intent"] == "memory"


def test_route_note_for_an_unknown_location_forbids_guessing_one():
    from backend.agents import coverage

    note = coverage.route_note(None)
    assert "MUST NOT assume, infer or pick" in note


def test_route_note_for_a_country_does_not_hand_over_a_list_of_towns():
    """The country-level note used to end with "Towns held: <every town>",
    which is a menu, not a guard - the model picked Chiang Mai off it."""
    from backend.agents import coverage

    note = coverage.route_note("Thailand")
    assert "Towns held" not in note
    assert "chiang mai" not in note.lower()
    assert "MUST NOT choose a town" in note


# --------------------------------------------------------------------------- #
# the memory writes underneath it
# --------------------------------------------------------------------------- #
def test_leaving_a_country_clears_a_town_inside_it(app_env):
    """archive_country compared raw strings, so leaving Thailand left the app
    believing the traveller was still in Pai."""
    store = app_env["store"]
    user_id = make_user(app_env["db"], "left_country")
    store.update_profile(user_id, {"current_location": "Pai"}, source="user_edit")

    store.log_departure(user_id, country="Thailand", departure_date="2026-09-14")

    assert store.get_profile(user_id).get("current_location") in (None, "")


def test_leaving_a_town_does_not_clear_a_different_town(app_env):
    """The widened match must stay one-way: leaving Chiang Mai says nothing
    about a traveller whose stored location is Pai."""
    store = app_env["store"]
    user_id = make_user(app_env["db"], "left_town")
    store.update_profile(user_id, {"current_location": "Pai"}, source="user_edit")

    assert store.archive_country(user_id, "Chiang Mai") is False
    assert store.get_profile(user_id).get("current_location") == "Pai"


def test_naming_the_country_you_are_already_in_keeps_the_known_town(app_env):
    """"I'm in Thailand now" while known to be in Pai is a confirmation, not a
    move: it must not overwrite Pai or append a country to the town-level route."""
    from backend.agents import tracking

    store, travel = app_env["store"], app_env["travel"]
    user_id = seed_traveller(app_env, "confirming", "Pai")

    tracking.apply_tracking(
        user_id,
        {"visits": [{"location": "Thailand", "location_type": "country", "country": "Thailand"}]},
        "i'm in thailand now",
    )

    assert store.get_profile(user_id).get("current_location") == "Pai"
    route = [h["location"] for h in travel.get_travel_history(user_id)]
    assert "Thailand" not in route


def test_arriving_in_a_new_country_still_records_it(app_env):
    """The other half of the same rule, and eval case memory-writes-departure:
    a country they are NOT in is a real move and must land."""
    from backend.agents import tracking

    store, travel = app_env["store"], app_env["travel"]
    user_id = make_user(app_env["db"], "moved_country")
    store.update_profile(user_id, {"current_location": "Luang Prabang"}, source="user_edit")

    tracking.apply_tracking(
        user_id,
        {"visits": [{"location": "Thailand", "location_type": "country", "country": "Thailand"}]},
        "i left laos yesterday and i'm in thailand now",
    )

    assert store.get_profile(user_id).get("current_location") == "Thailand"
    assert "Thailand" in [h["location"] for h in travel.get_travel_history(user_id)]


# --------------------------------------------------------------------------- #
# grounding: a place the traveller never typed is not a memory write
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "location,message,expected",
    [
        ("Pai", "i just got to pai", True),
        ("Chiang Mai", "I'm currently in chiang mai", True),
        ("Thailand", "i'm in thailand now", True),
        ("Bali, Indonesia", "i just got to bali", True),          # compound, part match
        ("Tokyo", "I've landed in Tokyo!", True),                  # punctuation
        ("Chiang Mai", "where should i go next", False),           # THE bug
        ("Pai", "any parties?", False),
        ("Pai", "what things should i do? give me some ideas", False),
        ("Chiang Mai", "", True),                                  # no message: fail open
        ("Pai", "i have a pain in my leg", False),                 # not a substring match
        ("Malmö", "i am in Malmö now", True),                      # non-ASCII survives
    ],
)
def test_mentioned_in(location, message, expected):
    from backend.agents import tracking

    assert tracking.mentioned_in(location, message) is expected


def test_a_visit_the_traveller_never_named_is_not_written(app_env):
    """The exact parse from the reported trace: the message named nowhere, and
    the parser emitted a visit to a town out of the route history."""
    from backend.agents import tracking

    store, travel = app_env["store"], app_env["travel"]
    user_id = seed_traveller(app_env, "ungrounded_visit", "Thailand")

    writes = tracking.apply_tracking(
        user_id,
        {
            "visits": [
                {
                    "location": "Chiang Mai",
                    "location_type": "city",
                    "country": "Thailand",
                    "arrival_date": "2026-09-14",
                }
            ]
        },
        "where should i go next",
    )

    assert writes == []
    assert store.get_profile(user_id).get("current_location") == "Thailand"
    assert travel.get_travel_history(user_id)[-1]["location"] != "Chiang Mai"


def test_a_departure_the_traveller_never_named_is_not_written(app_env):
    from backend.agents import tracking

    store = app_env["store"]
    user_id = seed_traveller(app_env, "ungrounded_departure", "Pai")

    tracking.apply_tracking(
        user_id,
        {"departures": [{"location": "Thailand", "location_type": "country"}]},
        "where should i go next",
    )

    assert store.get_profile(user_id).get("current_location") == "Pai"


def test_a_departure_is_dropped_when_the_same_turn_says_they_are_there(app_env):
    """"i said i was in thailand? i want to change country" was parsed as both
    current_location=Thailand AND a departure from Thailand dated today; the
    departure won and wiped the location the same sentence had just set."""
    from backend.agents import tracking

    store = app_env["store"]
    user_id = seed_traveller(app_env, "contradiction", "Chiang Mai")

    tracking.apply_tracking(
        user_id,
        {
            "profile_updates": {"current_location": "Thailand"},
            "departures": [
                {"location": "Thailand", "location_type": "country", "departure_date": "2026-09-14"}
            ],
        },
        "i never said i was in chiang mai? i said i was in thailand? i want to change country",
    )

    visited = [v["country"].lower() for v in store.get_memory_snapshot(user_id)["visited_history"]]
    assert "thailand" not in visited
    assert store.get_profile(user_id).get("current_location") == "Chiang Mai"


def test_ungrounded_current_location_update_is_dropped(app_env):
    import backend.agents.runner as runner

    store = app_env["store"]
    user_id = seed_traveller(app_env, "ungrounded_profile", "Thailand")

    runner._apply_memory_writes(
        user_id,
        {"profile_updates": {"current_location": "Chiang Mai", "budget_band": "shoestring"}},
        "where should i go next",
    )

    profile = store.get_profile(user_id)
    assert profile.get("current_location") == "Thailand"
    # The rest of the same update still lands - only the place name is grounded.
    assert profile.get("budget_band") == "shoestring"


def test_the_reported_sequence_no_longer_relocates_the_traveller(app_env, monkeypatch):
    """End-to-end replay of bug report #3's two decisive turns, with the exact
    parses the Langfuse traces recorded."""
    store = app_env["store"]
    user_id = seed_traveller(app_env, "reported_sequence", "Chiang Mai")

    run_stubbed_turn(
        monkeypatch,
        user_id,
        "i'm in thailand now",
        {
            "intent": "local",
            "profile_updates": {"current_location": "Thailand"},
            "visits": [
                {"location": "Thailand", "location_type": "country", "country": "Thailand"}
            ],
            "focus_location": "Thailand",
        },
    )
    assert store.get_profile(user_id).get("current_location") == "Thailand"

    seen = run_stubbed_turn(
        monkeypatch,
        user_id,
        "where should i go next",
        {
            "intent": "discover",
            "visits": [
                {
                    "location": "Chiang Mai",
                    "location_type": "city",
                    "country": "Thailand",
                    "arrival_date": "2026-09-14",
                }
            ],
        },
    )

    # The hallucinated visit is refused, so they are still where they said.
    assert store.get_profile(user_id).get("current_location") == "Thailand"
    # And the answer is a country comparison, not onward hops from a town they
    # never named.
    assert seen["agent"] == "decision_weigher"
    assert "chiang mai" not in seen["state"]["candidates"]


def test_a_country_question_classified_local_is_still_answered_with_countries(
    app_env, monkeypatch
):
    """The reported turn was classified `local`, not `discover` - gating the
    country override on `discover` alone would have missed it."""
    user_id = seed_traveller(app_env, "local_country_q", "Pai")

    seen = run_stubbed_turn(
        monkeypatch,
        user_id,
        "i never said i was in chiang mai? i said i was in thailand? i want to change country",
        {"intent": "local", "focus_location": "Thailand"},
    )

    assert seen["agent"] == "decision_weigher"
    assert "thailand" not in seen["state"]["candidates"]


def test_parsed_departures_carry_no_country_field(app_env):
    """Pins the schema fact behind removing the dead departure loop from
    _apply_memory_writes: ADK's strict output schema strips anything not on
    ParsedDeparture, so a country key can never arrive there."""
    from backend.agents.graph import TurnParse

    parsed = TurnParse(
        intent="discover",
        departures=[{"location": "Thailand", "location_type": "country", "country": "Thailand"}],
    )
    assert "country" not in parsed.model_dump()["departures"][0]


# --------------------------------------------------------------------------- #
# one ADK session id per turn (Langfuse session grouping)
# --------------------------------------------------------------------------- #
def test_every_agent_in_a_turn_shares_one_adk_session_id(app_env, monkeypatch):
    """Per-agent ADK session ids ("parse-2", "local-2", "weigh-2-1") were
    carried onto the auto-instrumented spans, and at ingestion the last agent
    to run overwrote the trace's Langfuse session id with its own - so one
    conversation scattered across four "sessions" named after whichever agent
    answered. Verified live before and after; see notes/08 decision 47."""
    import backend.agents.runner as runner

    user_id = seed_traveller(app_env, "one_session", "Pai")

    seen = run_stubbed_turn(
        monkeypatch,
        user_id,
        "Laos or Cambodia next?",
        {"intent": "compare", "candidate_destinations": ["laos", "cambodia"]},
    )

    expected = runner.adk_session_id(user_id)
    assert expected == f"user-{user_id}"
    # A compare turn is the demanding case: parser, three concurrent
    # specialists, then the weigher.
    agents = [name for name, _ in seen["sessions"]]
    assert "turn_parser" in agents and "decision_weigher" in agents
    assert len(seen["sessions"]) >= 5
    assert {session for _, session in seen["sessions"]} == {expected}


def test_a_single_agent_turn_uses_the_same_session_id_too(app_env, monkeypatch):
    user_id = seed_traveller(app_env, "one_session_local", "Pai")

    seen = run_stubbed_turn(
        monkeypatch, user_id, "any good hostels here?", {"intent": "local", "focus_location": "Pai"}
    )

    assert {session for _, session in seen["sessions"]} == {f"user-{user_id}"}


def test_country_question_with_no_onward_options_asks_instead_of_answering(app_env, monkeypatch):
    """Japan has no overland neighbour in COUNTRY_NEIGHBOURS. With an empty
    wishlist there is no country pool to answer with, and falling through to the
    town-level agent would answer a country question with towns all over again.
    The concierge holds no tools, and gets a code-written note saying so."""
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "no_country_options")
    store.update_profile(
        user_id,
        {"nationality": "United Kingdom", "current_location": "Japan"},
        source="user_edit",
    )

    seen = run_stubbed_turn(
        monkeypatch, user_id, "which country should i go to next", {"intent": "discover"}
    )

    assert seen["agent"] == "concierge"
    assert seen["result"]["intent"] == "memory"
    assert "NO ONWARD COUNTRIES HELD" in seen["state"]["route_note"]
