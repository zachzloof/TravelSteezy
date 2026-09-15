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
    """Morocco is not in COUNTRY_NEIGHBOURS at all, so we hold no geography for
    it. With an empty wishlist there is no country pool to answer with, and
    falling through to the town-level agent would answer a country question with
    towns all over again. The concierge holds no tools, and gets a code-written
    note saying so.

    This used to be asserted with Japan, which was one of six origins
    deliberately given no neighbours because it had no *overland* pairing inside
    the corpus. All six have five nearest countries now (South Korea is an
    overnight ferry from Japan, and pretending otherwise was the bug, not the
    feature), so the only route into this branch is an origin we genuinely know
    nothing about - which is what it should always have been testing."""
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "no_country_options")
    store.update_profile(
        user_id,
        {"nationality": "United Kingdom", "current_location": "Morocco"},
        source="user_edit",
    )

    seen = run_stubbed_turn(
        monkeypatch, user_id, "which country should i go to next", {"intent": "discover"}
    )

    assert seen["agent"] == "concierge"
    assert seen["result"]["intent"] == "memory"
    assert "NO ONWARD COUNTRIES HELD" in seen["state"]["route_note"]


# --------------------------------------------------------------------------- #
# how the candidate pool is built
# --------------------------------------------------------------------------- #
# Until this change a "where next" turn was cut to exactly three destinations by
# a code-side sort - season tier, then journey hours, then wishlist priority -
# before a single specialist ran. Everything else the traveller had asked for was
# dropped silently, with nothing in the trace to say what or why. The pool is now
# capped by budget rather than by that heuristic, every survivor is researched,
# and the decision_weigher does the ranking.
def test_every_origin_offers_five_nearest_countries():
    """The table used to hold at most three, and six origins held none at all."""
    from backend.agents import coverage

    for origin, neighbours in coverage.COUNTRY_NEIGHBOURS.items():
        assert len(neighbours) == 5, f"{origin} has {len(neighbours)}"
        assert len(set(neighbours)) == 5, f"{origin} repeats a neighbour"
        assert origin not in neighbours, f"{origin} lists itself"

    # The six that were deliberately empty before, on the reasoning that they had
    # no overland pairing inside the corpus.
    for origin in ("japan", "australia", "new zealand", "mongolia", "south korea", "myanmar"):
        assert len(coverage.nearby_country_options(origin)) == 5


def test_nearest_countries_are_not_limited_to_the_curated_corpus():
    """The widening is the point: the nearest country is often one the seed
    corpus never covered, and live_lookup is what fills that in at runtime."""
    from backend.agents import coverage

    assert "china" in coverage.nearby_country_options("laos")
    assert "taiwan" in coverage.nearby_country_options("philippines")
    assert "bangladesh" in coverage.nearby_country_options("myanmar")
    assert "uruguay" in coverage.nearby_country_options("brazil")

    uncovered = {
        c
        for neighbours in coverage.COUNTRY_NEIGHBOURS.values()
        for c in neighbours
        if c not in coverage.SUPPORTED
    }
    assert uncovered, "nothing outside the corpus - the table did not widen"
    # Independent travel to North Korea is not available to this app's users, so
    # it is the one true neighbour left out on purpose.
    assert "north korea" not in uncovered


@pytest.mark.parametrize(
    "budget,wishlist_count,expected",
    [
        (10, 8, (5, 5)),   # the stated default: half each
        (8, 8, (4, 4)),
        (6, 8, (3, 3)),
        (10, 2, (2, 5)),   # short wishlist cannot lend its half to nobody
        (10, 0, (0, 5)),   # empty wishlist still gets every neighbour
        (3, 8, (2, 1)),    # odd budget: the spare slot goes to the wishlist
    ],
)
def test_candidate_budget_is_split_evenly_between_wishlist_and_neighbours(
    budget, wishlist_count, expected
):
    from backend.agents import runner

    wishlist = [f"w{i}" for i in range(wishlist_count)]
    neighbours = ["n1", "n2", "n3", "n4", "n5"]

    chosen_w, chosen_n = runner._split_candidate_budget(wishlist, neighbours, budget)

    assert (len(chosen_w), len(chosen_n)) == expected
    assert len(chosen_w) + len(chosen_n) <= budget
    # Both sides arrive pre-ordered and are taken as prefixes.
    assert chosen_n == neighbours[: len(chosen_n)]
    assert chosen_w == wishlist[: len(chosen_w)]


def test_an_origin_with_no_geography_gives_the_whole_budget_to_the_wishlist():
    from backend.agents import runner

    wishlist = [f"w{i}" for i in range(12)]
    chosen_w, chosen_n = runner._split_candidate_budget(wishlist, [], 10)

    assert len(chosen_w) == 10
    assert chosen_n == []


# --- how the wishlist half is ordered -------------------------------------- #
def test_stated_priority_beats_distance():
    """The one number the traveller set themselves leads. A priority-1 country on
    the far side of the world outranks a priority-5 country next door."""
    import random

    from backend.agents import runner

    order = runner._order_wishlist(
        {"japan": 1, "laos": 5, "peru": 1, "cambodia": 4},
        "thailand",
        random.Random(0),
    )

    assert set(order[:2]) == {"japan", "peru"}
    assert order[2:] == ["cambodia", "laos"]


def test_same_priority_is_broken_by_distance_from_where_they_are():
    """"If they all matter equally, take the closest" - the nearer of two
    equally-wanted countries is the cheaper, more plausible next hop."""
    import random

    from backend.agents import runner

    # All priority 1. Laos and Cambodia have curated route legs from Thailand;
    # Peru does not, so it sorts last on unknown distance rather than being lost.
    order = runner._order_wishlist(
        {"peru": 1, "laos": 1, "cambodia": 1}, "thailand", random.Random(0)
    )

    assert order[-1] == "peru"
    assert set(order[:2]) == {"laos", "cambodia"}
    assert runner._journey_hours("thailand", "laos") < float("inf")
    assert runner._journey_hours("thailand", "peru") == float("inf")


def test_the_closest_wins_when_priorities_tie():
    import random

    from backend.agents import runner

    hours = {c: runner._journey_hours("thailand", c) for c in ("laos", "cambodia", "malaysia")}
    nearest = min(hours, key=hours.get)

    order = runner._order_wishlist(
        {c: 1 for c in hours}, "thailand", random.Random(0)
    )

    assert order[0] == nearest


def test_only_exact_ties_fall_through_to_the_random_tiebreak():
    """Entries identical on BOTH priority and journey time - in practice a group
    of same-priority countries we hold no route data for - rotate rather than
    letting the same few win every turn forever. Anything we hold data for is
    fully determined."""
    import random

    from backend.agents import runner

    # All priority 1, none with a curated leg from Thailand, so all tie at inf.
    flat = {c: 1 for c in ("peru", "brazil", "chile", "colombia", "ecuador")}
    draws = {
        tuple(runner._order_wishlist(flat, "thailand", random.Random(seed)))
        for seed in range(12)
    }
    assert len(draws) > 1, "exact ties are not rotating"

    # But a pool with real priorities and real distances is stable across seeds.
    determined = {"japan": 1, "laos": 2, "cambodia": 3}
    stable = {
        tuple(runner._order_wishlist(determined, "thailand", random.Random(seed)))
        for seed in range(12)
    }
    assert len(stable) == 1, f"a fully-determined ordering varied: {stable}"


def test_the_whole_pool_reaches_the_specialists_not_just_three(app_env, monkeypatch):
    """The `ranked[:3]` cut is gone. A traveller in Thailand with four wishlist
    countries should have all five nearest countries AND their wishlist weighed,
    not three survivors of a code-side heuristic."""
    store, travel, db = app_env["store"], app_env["travel"], app_env["db"]
    user_id = make_user(db, "full_pool")
    store.update_profile(
        user_id,
        {"nationality": "United Kingdom", "current_location": "Thailand"},
        source="user_edit",
    )
    for place, priority in (("Japan", 1), ("Nepal", 2), ("Peru", 3), ("India", 4)):
        travel.add_wishlist(
            user_id, place, location_type="country", country=place, priority=priority
        )

    seen = run_stubbed_turn(
        monkeypatch, user_id, "which country should i go to next", {"intent": "discover"}
    )

    assert seen["agent"] == "decision_weigher"
    candidates = [c.strip() for c in seen["state"]["candidates"].split(",")]
    # 4 wishlist (under its half of 5) + all 5 nearest countries.
    assert len(candidates) == 9
    assert {"laos", "cambodia", "myanmar", "malaysia", "vietnam"} <= set(candidates)
    assert {"japan", "nepal", "peru", "india"} <= set(candidates)


# --------------------------------------------------------------------------- #
# named destinations win outright: the pool is only built when they name none
# --------------------------------------------------------------------------- #
# "Thailand or Vietnam?" must compare exactly Thailand and Vietnam. The wishlist
# and the five nearest countries exist to answer an OPEN "where next" - they are
# what we fall back to when the traveller has not said, and adding them to a
# question that named two countries would be answering a different question (and
# paying for eight extra destinations of specialist research to do it).
def test_two_named_destinations_are_the_only_candidates(app_env, monkeypatch):
    """Even with a location and a full wishlist - everything needed to build a
    ten-candidate pool - naming two countries wins."""
    store, travel, db = app_env["store"], app_env["travel"], app_env["db"]
    user_id = make_user(db, "named_two")
    store.update_profile(
        user_id,
        {"nationality": "United Kingdom", "current_location": "Thailand"},
        source="user_edit",
    )
    for p in ("Japan", "Nepal", "Peru", "India", "Taiwan", "Mexico"):
        travel.add_wishlist(user_id, p, location_type="country", country=p, priority=1)

    seen = run_stubbed_turn(
        monkeypatch,
        user_id,
        "where should i go next, thailand or vietnam?",
        {"intent": "compare", "candidate_destinations": ["Thailand", "Vietnam"]},
    )

    assert seen["agent"] == "decision_weigher"
    candidates = [c.strip() for c in seen["state"]["candidates"].split(",")]
    assert candidates == ["thailand", "vietnam"]
    # None of the pool-building sources leaked in.
    assert not ({"japan", "nepal", "peru", "india", "taiwan", "mexico"} & set(candidates))
    assert not ({"laos", "cambodia", "myanmar", "malaysia"} & set(candidates))


def test_named_destinations_win_even_when_the_question_is_country_scoped(
    app_env, monkeypatch
):
    """The country-scope override and the named-candidate override could fight:
    "my visa is running out" forces the country-level path, which is what builds
    the pool. Naming two countries has to win, or a specific question gets
    answered with eight countries they did not ask about."""
    store, travel, db = app_env["store"], app_env["travel"], app_env["db"]
    from backend.agents import coverage

    user_id = make_user(db, "named_two_country_scope")
    store.update_profile(
        user_id,
        {"nationality": "United Kingdom", "current_location": "Thailand"},
        source="user_edit",
    )
    travel.add_wishlist(
        user_id, "Japan", location_type="country", country="Japan", priority=1
    )

    message = "my visa is running out - should i go to laos or cambodia next?"
    assert coverage.wants_country_scope(message) is True

    seen = run_stubbed_turn(
        monkeypatch,
        user_id,
        message,
        {"intent": "compare", "candidate_destinations": ["Laos", "Cambodia"]},
    )

    candidates = [c.strip() for c in seen["state"]["candidates"].split(",")]
    assert candidates == ["laos", "cambodia"]
    assert "japan" not in candidates


def test_naming_nowhere_is_what_builds_the_pool(app_env, monkeypatch):
    """The contrast case, asserted alongside the two above so the boundary is
    visible in one place: same account, same location, no destination named."""
    store, travel, db = app_env["store"], app_env["travel"], app_env["db"]
    user_id = make_user(db, "named_none")
    store.update_profile(
        user_id,
        {"nationality": "United Kingdom", "current_location": "Thailand"},
        source="user_edit",
    )
    travel.add_wishlist(
        user_id, "Japan", location_type="country", country="Japan", priority=1
    )

    seen = run_stubbed_turn(
        monkeypatch, user_id, "which country should i go to next", {"intent": "discover"}
    )

    candidates = [c.strip() for c in seen["state"]["candidates"].split(",")]
    assert len(candidates) > 2
    assert "japan" in candidates
    assert {"laos", "cambodia", "myanmar", "malaysia", "vietnam"} <= set(candidates)


def test_a_country_on_both_the_wishlist_and_the_neighbours_is_researched_once(
    app_env, monkeypatch
):
    """Vietnam is one of Thailand's five nearest AND on this traveller's
    wishlist. Sending it to the specialists twice would be paid-for duplicate
    work and would put two cards for the same country in front of the weigher."""
    store, travel, db = app_env["store"], app_env["travel"], app_env["db"]
    user_id = make_user(db, "dedup_pool")
    store.update_profile(
        user_id,
        {"nationality": "United Kingdom", "current_location": "Thailand"},
        source="user_edit",
    )
    travel.add_wishlist(
        user_id, "Vietnam", location_type="country", country="Vietnam", priority=1
    )
    travel.add_wishlist(
        user_id, "Japan", location_type="country", country="Japan", priority=1
    )

    seen = run_stubbed_turn(
        monkeypatch, user_id, "which country should i go to next", {"intent": "discover"}
    )

    candidates = [c.strip() for c in seen["state"]["candidates"].split(",")]
    assert candidates.count("vietnam") == 1
    assert len(candidates) == len(set(candidates))
    # It is still there - deduping must not drop it, only stop it doubling.
    assert "vietnam" in candidates
    assert "japan" in candidates


def test_a_long_wishlist_is_capped_at_the_configured_budget(app_env, monkeypatch):
    store, travel, db = app_env["store"], app_env["travel"], app_env["db"]
    from backend.config import settings

    user_id = make_user(db, "capped_pool")
    store.update_profile(
        user_id,
        {"nationality": "United Kingdom", "current_location": "Thailand"},
        source="user_edit",
    )
    for i in range(15):
        travel.add_wishlist(
            user_id, f"Country{i}", location_type="country",
            country=f"Country{i}", priority=1,
        )

    seen = run_stubbed_turn(
        monkeypatch, user_id, "which country should i go to next", {"intent": "discover"}
    )

    candidates = [c.strip() for c in seen["state"]["candidates"].split(",")]
    assert len(candidates) == settings.max_comparison_candidates
    # Half the budget is held for the nearest countries no matter how long the
    # wishlist gets - the whole point of the split.
    assert len({"laos", "cambodia", "myanmar", "malaysia", "vietnam"} & set(candidates)) == 5


def test_the_weigher_card_list_is_trimmed_to_the_configured_top_n():
    """The prompt asks for WEIGHER_TOP_N; the cap is enforced in code as well,
    because "one card per candidate" is the instruction the weigher falls back
    to, and ten cards would flood a UI built to reveal six."""
    from backend.agents import runner
    from backend.config import settings

    raw = [
        {"destination": f"Country{i}", "rank": i, "verdict": "maybe"}
        for i in range(1, 11)
    ]

    cards = runner._coerce_cards(raw)

    assert len(cards) == settings.weigher_top_n
    assert [c["rank"] for c in cards] == list(range(1, settings.weigher_top_n + 1))
    assert [c["destination"] for c in cards] == [
        f"Country{i}" for i in range(1, settings.weigher_top_n + 1)
    ]


def test_card_ranks_are_renumbered_contiguously():
    """The weigher occasionally emits gapped or duplicate ranks, and the
    frontend orders and labels cards by this field."""
    from backend.agents import runner

    cards = runner._coerce_cards(
        [
            {"destination": "Laos", "rank": 7},
            {"destination": "Vietnam", "rank": 2},
            {"destination": "Malaysia", "rank": 2},
        ]
    )

    assert [c["rank"] for c in cards] == [1, 2, 3]
    assert cards[0]["destination"] in {"Vietnam", "Malaysia"}
    assert cards[-1]["destination"] == "Laos"
