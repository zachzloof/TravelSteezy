"""Tests for the extension: structured travel memory, ranking, clustering, links.

No API keys and no network: the Places layer is exercised through its pure
functions and its no-key degradation path. The agent behaviour itself is covered
by evals/, not here.

    python -m pytest tests -q
"""
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def app_env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="onward-travel-test-")
    monkeypatch.setenv("DATA_DIR", tmp)
    monkeypatch.setenv("DB_PATH", str(Path(tmp) / "test.sqlite3"))
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-pw")
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "")
    monkeypatch.setenv("SERVE_FRONTEND", "false")

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


# --------------------------------------------------------------------------- #
# travel history
# --------------------------------------------------------------------------- #
def test_history_keeps_route_order(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "router")

    for place in ("Bangkok", "Koh Tao", "Chiang Mai"):
        travel.add_travel_history(user_id, place, country="Thailand", source="onboarding")

    route = [h["location"] for h in travel.get_travel_history(user_id)]
    assert route == ["Bangkok", "Koh Tao", "Chiang Mai"]


def test_re_adding_a_place_updates_rather_than_duplicates(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "dupe")

    first = travel.add_travel_history(user_id, "Pai", source="onboarding")
    second = travel.add_travel_history(user_id, "pai", departure_date="2026-05-02", source="tracked")

    assert first["created"] is True
    assert second["created"] is False
    history = travel.get_travel_history(user_id)
    assert len(history) == 1
    assert history[0]["departure_date"] == "2026-05-02"


def test_repeat_mention_is_not_recorded_as_a_write(app_env):
    """Re-mentioning somewhere already known must not pollute the audit trail."""
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "quiet")

    travel.add_travel_history(user_id, "Pai", country="Thailand", source="tracked")
    before = len(store.get_write_log(user_id, limit=100))

    result = travel.add_travel_history(user_id, "Pai", country="Thailand", source="tracked")
    after = len(store.get_write_log(user_id, limit=100))

    assert result["changed"] is False
    assert after == before


# --------------------------------------------------------------------------- #
# wishlist
# --------------------------------------------------------------------------- #
def test_somewhere_already_visited_can_be_wishlisted_as_a_revisit(app_env):
    """Wanting to go back is a real preference, not a data-entry mistake.

    An earlier version refused this outright, which silently dropped one of the
    most common things a long-term traveller says. It is accepted now and
    flagged, so the UI and the agents can tell a revisit from a first visit.
    """
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "been")

    travel.add_travel_history(user_id, "Chiang Mai", source="onboarding")
    result = travel.add_wishlist(user_id, "chiang mai", priority=1)

    assert result["ok"] is True
    assert result["revisit"] is True

    entries = travel.get_wishlist(user_id)
    assert [w["location"] for w in entries] == ["chiang mai"]
    assert entries[0]["revisit"] is True


def test_a_first_visit_is_not_flagged_as_a_revisit(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "notbeen")

    assert travel.add_wishlist(user_id, "Pai")["revisit"] is False
    assert travel.get_wishlist(user_id)[0]["revisit"] is False


def test_visit_promotes_off_the_wishlist(app_env):
    """The core trip-tracking behaviour."""
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "promoted")

    travel.add_wishlist(user_id, "Pai", country="Thailand", priority=1)
    assert [w["location"] for w in travel.get_wishlist(user_id)] == ["Pai"]

    travel.add_travel_history(user_id, "Pai", source="tracked")
    promoted = travel.resolve_wishlist(user_id, "Pai", status="visited")

    assert promoted is True
    assert travel.get_wishlist(user_id) == []
    everything = travel.get_wishlist(user_id, status="all")
    assert everything[0]["status"] == "visited"


def test_dropping_a_wishlist_entry_is_recorded(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "dropper")
    travel.add_wishlist(user_id, "Sihanoukville")

    assert travel.resolve_wishlist(user_id, "Sihanoukville", status="dropped") is True
    assert travel.resolve_wishlist(user_id, "Sihanoukville", status="dropped") is False


# --------------------------------------------------------------------------- #
# reviews
# --------------------------------------------------------------------------- #
def test_review_attaches_to_history(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "reviewer")
    travel.add_travel_history(user_id, "Pai", source="tracked")

    result = travel.save_review(user_id, "Pai", rating=5, review_notes="Stayed way too long")

    assert result["ok"] is True
    entry = travel.get_travel_history(user_id)[0]
    assert entry["rating"] == 5
    assert entry["review_notes"] == "Stayed way too long"


def test_review_rejects_out_of_range_rating(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "badrating")
    travel.add_travel_history(user_id, "Pai", source="tracked")

    assert travel.save_review(user_id, "Pai", rating=9)["ok"] is False
    assert travel.save_review(user_id, "Pai", rating=0)["ok"] is False
    assert travel.get_travel_history(user_id)[0]["rating"] is None


def test_review_for_unvisited_place_is_refused(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "never")
    assert travel.save_review(user_id, "Narnia", rating=4)["ok"] is False


def test_pending_review_triggers_on_departure(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "left")

    travel.add_travel_history(user_id, "Pai", departure_date="2020-01-01", source="tracked")
    pending = [p["location"] for p in travel.get_pending_reviews(user_id)]
    assert pending == ["Pai"]

    travel.save_review(user_id, "Pai", rating=4, review_notes="Good")
    assert travel.get_pending_reviews(user_id) == []


def test_pending_review_ignores_places_still_being_talked_about(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "current")
    # No departure date, mentioned just now: nothing to review yet.
    travel.add_travel_history(user_id, "Chiang Mai", source="tracked")
    assert travel.get_pending_reviews(user_id) == []


# --------------------------------------------------------------------------- #
# interests and onboarding progress
# --------------------------------------------------------------------------- #
def test_interests_deduplicate_and_mirror_to_profile(app_env):
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "interested")

    travel.set_interests(user_id, ["Nature", "food", "NATURE", " nightlife "])
    interests = travel.get_interests(user_id)

    assert sorted(interests) == ["food", "nature", "nightlife"]
    assert "nature" in (store.get_profile(user_id)["interests"] or "")


def test_onboarding_gaps_derive_from_stored_data(app_env):
    """Progress must come from the database, not from the model's own claim."""
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "onboardee")

    assert travel.onboarding_gaps(user_id)["missing"] == [
        "history", "passports", "wishlist", "preferences",
    ]

    travel.add_travel_history(user_id, "Bangkok", source="onboarding")
    assert travel.onboarding_gaps(user_id)["missing"] == [
        "passports", "wishlist", "preferences",
    ]

    store.set_passports(user_id, ["United Kingdom"])
    assert travel.onboarding_gaps(user_id)["missing"] == ["wishlist", "preferences"]

    travel.add_wishlist(user_id, "Pai")
    assert travel.onboarding_gaps(user_id)["missing"] == ["preferences"]

    travel.set_interests(user_id, ["nature"])
    store.update_profile(user_id, {"budget_band": "shoestring"})
    gaps = travel.onboarding_gaps(user_id)
    assert gaps["missing"] == []
    assert gaps["complete"] is True


def test_travel_memory_is_isolated_per_account(app_env):
    travel, db = app_env["travel"], app_env["db"]
    a = make_user(db, "acct_a")
    b = make_user(db, "acct_b")

    travel.add_travel_history(a, "Nepal", source="onboarding")
    travel.add_wishlist(a, "Pokhara")
    travel.add_travel_history(b, "Vietnam", source="onboarding")

    assert [h["location"] for h in travel.get_travel_history(a)] == ["Nepal"]
    assert [h["location"] for h in travel.get_travel_history(b)] == ["Vietnam"]
    assert travel.get_wishlist(b) == []


def test_legacy_visited_history_is_migrated(app_env):
    """An existing install must not appear to lose its history on deploy."""
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "legacy")

    store.log_departure(user_id, "Laos", departure_date="2026-02-01")
    assert travel.get_travel_history(user_id) == []

    db.migrate_visited_history()

    history = travel.get_travel_history(user_id)
    assert [h["location"] for h in history] == ["Laos"]
    assert history[0]["source"] == "migrated"

    # Idempotent: running it again must not duplicate.
    db.migrate_visited_history()
    assert len(travel.get_travel_history(user_id)) == 1


# --------------------------------------------------------------------------- #
# Bayesian ranking
# --------------------------------------------------------------------------- #
def test_thin_five_star_loses_to_well_reviewed_places():
    """The whole point of weighting: one 5.0 review must not top the list."""
    from backend.places.ranking import rank_places

    ranked = rank_places(
        [
            {"name": "One review", "rating": 5.0, "user_rating_count": 1},
            {"name": "Well reviewed", "rating": 4.8, "user_rating_count": 180},
            {"name": "Very popular", "rating": 4.6, "user_rating_count": 2400},
            {"name": "Mediocre but busy", "rating": 3.9, "user_rating_count": 5000},
        ],
        min_reviews=25,
    )
    names = [p["name"] for p in ranked]
    assert names[0] == "Well reviewed"
    # A raw-rating sort would have put it first; it should now be near the bottom.
    assert names.index("One review") >= 2


def test_prior_is_weighted_by_review_count_not_a_plain_average():
    """Guards the fix: a plain mean let one thin outlier inflate the prior."""
    from backend.places.ranking import mean_rating

    places = [
        {"rating": 5.0, "user_rating_count": 1},
        {"rating": 4.0, "user_rating_count": 999},
    ]
    prior = mean_rating(places)
    assert abs(prior - 4.0) < 0.01  # a plain average would give 4.5


def test_two_candidate_near_tie_is_acknowledged():
    """Honest edge case: with only two candidates and the population mean sitting
    at the well-reviewed place's own rating, shrinkage cannot separate them much.
    We assert the gap is tiny rather than pretending the thin place is beaten."""
    from backend.places.ranking import rank_places

    ranked = rank_places(
        [
            {"name": "One review", "rating": 5.0, "user_rating_count": 1},
            {"name": "Well reviewed", "rating": 4.8, "user_rating_count": 180},
        ],
        min_reviews=25,
    )
    scores = {p["name"]: p["weighted_score"] for p in ranked}
    assert abs(scores["One review"] - scores["Well reviewed"]) < 0.02


def test_weighted_score_converges_on_raw_rating_with_many_reviews():
    from backend.places.ranking import weighted_score

    score = weighted_score(4.6, 100000, prior_mean=3.0, min_reviews=25)
    assert abs(score - 4.6) < 0.01


def test_missing_rating_scores_zero_not_crash():
    from backend.places.ranking import rank_places

    ranked = rank_places([{"name": "No data", "rating": None, "user_rating_count": None}])
    assert ranked[0]["weighted_score"] == 0.0


def test_budget_filter_excludes_expensive_but_never_returns_nothing():
    from backend.places.ranking import rank_places

    places = [
        {"name": "Dorm", "rating": 4.5, "user_rating_count": 900,
         "price_level": "PRICE_LEVEL_INEXPENSIVE"},
        {"name": "Resort", "rating": 4.9, "user_rating_count": 900,
         "price_level": "PRICE_LEVEL_VERY_EXPENSIVE"},
    ]
    assert [p["name"] for p in rank_places(places, budget_band="shoestring")] == ["Dorm"]

    only_expensive = [places[1]]
    assert len(rank_places(only_expensive, budget_band="shoestring")) == 1


# --------------------------------------------------------------------------- #
# clustering
# --------------------------------------------------------------------------- #
def test_clustering_does_not_chain_a_whole_city_into_one_area():
    """Single-linkage merged all of Chiang Mai into one 2.6km 'area'."""
    from backend.places.clustering import cluster_places

    # Three pairs, each pair tight, the pairs ~2km apart.
    points = [
        {"name": "A1", "latitude": 18.7880, "longitude": 98.9860, "weighted_score": 4.5},
        {"name": "A2", "latitude": 18.7885, "longitude": 98.9866, "weighted_score": 4.4},
        {"name": "B1", "latitude": 18.8060, "longitude": 98.9860, "weighted_score": 4.6},
        {"name": "B2", "latitude": 18.8065, "longitude": 98.9866, "weighted_score": 4.3},
    ]
    clusters = cluster_places(points, radius_meters=700)

    assert len(clusters) == 2
    assert all(c["spread_meters"] < 1400 for c in clusters)


def test_cluster_labels_skip_house_numbers():
    from backend.places.clustering import _label_from

    assert _label_from([{"address": "5/10 Soi 7, Chang Moi, Chiang Mai"}]) == "Around Soi 7"
    assert _label_from([{"address": "27, Prapokklao Road, Old City"}]) == "Around Prapokklao Road"


def test_places_without_coordinates_are_skipped():
    from backend.places.clustering import cluster_places

    assert cluster_places([{"name": "Nowhere"}]) == []


# --------------------------------------------------------------------------- #
# affiliate links
# --------------------------------------------------------------------------- #
def test_booking_links_contain_location_and_dates():
    from backend.places import affiliate

    links = affiliate.booking_links("Chiang Mai", "2026-10-02", "2026-10-06")
    assert "Chiang+Mai" in links["booking_com"]
    assert "checkin=2026-10-02" in links["booking_com"]
    assert "date_from=2026-10-02" in links["hostelworld"]
    assert "affiliate" in links["disclosure"].lower()


def test_malformed_dates_fall_back_to_a_valid_window():
    from backend.places import affiliate

    url = affiliate.booking_link("Pai", "not-a-date", "also-not-a-date")
    assert "checkin=" in url and "not-a-date" not in url


# --------------------------------------------------------------------------- #
# Places degradation without a key
# --------------------------------------------------------------------------- #
def test_place_tools_degrade_without_a_key(app_env):
    import backend.agents.place_tools as place_tools

    importlib.reload(place_tools)
    result = place_tools.get_places_recommendations("Chiang Mai", "food")

    assert result["configured"] is False
    assert result["results"] == []
    assert "GOOGLE_PLACES_API_KEY" in result["note"]


def test_hostel_search_still_returns_booking_links_without_a_key(app_env):
    """Booking links need no API key, so a missing key must not remove them."""
    import backend.agents.place_tools as place_tools

    importlib.reload(place_tools)
    result = place_tools.find_hostels("Pai")

    assert result["configured"] is False
    assert "booking_com" in result["booking_links"]


# --------------------------------------------------------------------------- #
# geocoding a town needs the country we already know it is in
# --------------------------------------------------------------------------- #
def test_geocode_disambiguates_a_town_with_its_country(app_env, monkeypatch):
    """geocode("Pai") resolved to an organisation on Russell Square in LONDON,
    so a traveller in northern Thailand was recommended Dishoom Covent Garden.
    The corpus already knows Pai is in Thailand - say so."""
    import backend.agents.place_tools as place_tools

    importlib.reload(place_tools)
    seen: list[str] = []
    monkeypatch.setattr(
        place_tools.client, "geocode", lambda q: seen.append(q) or {"latitude": 1, "longitude": 2}
    )

    place_tools._geocode("Pai")
    place_tools._geocode("Chiang Mai")

    assert seen == ["Pai, Thailand", "Chiang Mai, Thailand"]


def test_geocode_leaves_an_already_qualified_or_unknown_location_alone(app_env, monkeypatch):
    """A string that already names its country is passed through untouched, and
    so is a town the corpus does not recognise - that is a coverage gap, not a
    disambiguation one, and inventing a country for it would be worse."""
    import backend.agents.place_tools as place_tools

    importlib.reload(place_tools)
    seen: list[str] = []
    monkeypatch.setattr(
        place_tools.client, "geocode", lambda q: seen.append(q) or {"latitude": 1, "longitude": 2}
    )

    place_tools._geocode("Pai, Thailand")
    place_tools._geocode("Nowhereville")
    place_tools._geocode("Thailand")

    assert seen == ["Pai, Thailand", "Nowhereville", "Thailand"]


# --------------------------------------------------------------------------- #
# city detection
# --------------------------------------------------------------------------- #
def test_city_detection_prefers_the_longest_match():
    from backend.rag.store import detect_cities

    cities = [c["city"] for c in detect_cities("just landed in Gili Trawangan")]
    assert "gili trawangan" in cities


def test_city_detection_finds_multiple_towns():
    from backend.rag.store import detect_cities

    found = {c["city"]: c["country"] for c in detect_cities("Left Luang Prabang for Vang Vieng")}
    assert found == {"luang prabang": "laos", "vang vieng": "laos"}


# --------------------------------------------------------------------------- #
# departures at town vs country granularity
# --------------------------------------------------------------------------- #
def test_leaving_a_town_does_not_pollute_country_history(app_env, monkeypatch):
    """Leaving Pai is not leaving Thailand.

    An earlier version passed the town name straight into the country-level log,
    writing "Pai" into visited_history as though it were a country.
    """
    import importlib

    import backend.agents.tracking as tracking

    importlib.reload(tracking)
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "towndeparture")
    store.update_profile(user_id, {"current_location": "Pai"})

    tracking.apply_tracking(
        user_id,
        {"departures": [{"location": "Pai", "location_type": "city",
                         "departure_date": "2026-09-20"}]},
    )

    assert store.get_visited_history(user_id) == []
    # It still stops being active context, and lands in the route with its date.
    assert store.get_profile(user_id)["current_location"] is None
    entry = travel.get_travel_history(user_id)[0]
    assert entry["location"] == "Pai"
    assert entry["departure_date"] == "2026-09-20"


def test_leaving_a_country_still_logs_at_country_level(app_env):
    import importlib

    import backend.agents.tracking as tracking

    importlib.reload(tracking)
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "countrydeparture")
    store.update_profile(user_id, {"current_location": "Thailand"})

    tracking.apply_tracking(
        user_id,
        {"departures": [{"location": "Thailand", "location_type": "country",
                         "departure_date": "2026-09-25"}]},
    )

    assert [v["country"] for v in store.get_visited_history(user_id)] == ["Thailand"]


# --------------------------------------------------------------------------- #
# town -> country resolution for the country-keyed tables
# --------------------------------------------------------------------------- #
def test_resolve_country_handles_towns_and_compounds():
    from backend.rag.route_data import resolve_country

    assert resolve_country("Malaysia") == "malaysia"
    assert resolve_country("Perhentian Islands, Malaysia") == "malaysia"
    assert resolve_country("koh tao") == "thailand"
    assert resolve_country("Bali") == "indonesia"
    assert resolve_country("Reykjavik") is None
    assert resolve_country("") is None


def test_seasonal_lookup_works_for_a_town_not_just_a_country():
    """A town-level candidate must not lose its monsoon warning.

    The climate table is keyed by country; an exact lookup returned "unknown" for
    "Perhentian Islands, Malaysia" and silently dropped a correct December
    closure warning.
    """
    from backend.agents.climate import assess

    country = assess("malaysia", "december")
    town = assess("Perhentian Islands, Malaysia", "december")

    assert country["rating"] == "avoid"
    assert town["rating"] == country["rating"]
    assert town["known"] is True


def test_seasonal_lookup_still_unknown_for_uncovered_places():
    from backend.agents.climate import assess

    assert assess("Reykjavik", "december")["rating"] == "unknown"


def test_route_lookup_resolves_towns_to_their_country():
    from backend.agents.routes import lookup

    by_town = lookup("Chiang Mai", "Luang Prabang")
    by_country = lookup("Thailand", "Laos")

    assert by_town["known"] is True
    assert by_town["overland"] == by_country["overland"]


# --------------------------------------------------------------------------- #
# passports
# --------------------------------------------------------------------------- #
def test_passports_are_a_list_with_nationality_mirroring_the_primary(app_env):
    """A dual national must not have to pick one passport and lose the other.

    ``nationality`` is kept in sync with the first passport, because every
    prompt, tool and eval in the base app was written against that single field.
    Adding passports must not quietly break any of them.
    """
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "dual")

    store.set_passports(user_id, ["United Kingdom", "Ireland"])

    assert store.get_passports(user_id) == ["United Kingdom", "Ireland"]
    profile = store.get_profile(user_id)
    assert profile["nationality"] == "United Kingdom"
    assert profile["passports"] == ["United Kingdom", "Ireland"]


def test_passports_deduplicate_and_reordering_moves_the_primary(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "reorder")

    store.set_passports(user_id, ["Ireland", "ireland", "United Kingdom"])
    assert store.get_passports(user_id) == ["Ireland", "United Kingdom"]

    store.set_passports(user_id, ["United Kingdom", "Ireland"])
    assert store.get_profile(user_id)["nationality"] == "United Kingdom"


def test_existing_accounts_backfill_a_passport_from_nationality(app_env):
    """An account created before passports existed must not show an empty panel."""
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "legacy")

    store.update_profile(user_id, {"nationality": "Australia"})
    assert store.get_passports(user_id) == []

    assert store.sync_passports_from_nationality(user_id) == ["Australia"]
    # Idempotent: running it again must not duplicate or reorder anything.
    assert store.sync_passports_from_nationality(user_id) == ["Australia"]


def test_forgetting_an_account_clears_its_passports(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "forgetful")

    store.set_passports(user_id, ["Canada"])
    store.forget_account_memory(user_id)

    assert store.get_passports(user_id) == []


# --------------------------------------------------------------------------- #
# the five-point scales
# --------------------------------------------------------------------------- #
def test_free_text_maps_onto_the_five_point_scales(app_env):
    """Onboarding can accept plain English because Python does the mapping."""
    store = app_env["store"]

    assert store.normalise_band("budget_band", "dirt cheap") == "shoestring"
    assert store.normalise_band("budget_band", "flashpacker") == "mid"
    assert store.normalise_band("budget_band", "splurge") == "luxury"
    assert store.normalise_band("travel_style", "as slow as I can") == "slow"
    assert store.normalise_band("travel_style", "whistle-stop") == "very_fast"
    assert store.normalise_band("climate_preference", "tropical") == "hot"
    assert store.normalise_band("climate_preference", "very cold") == "cold"


def test_a_negated_preference_is_never_stored_as_its_opposite(app_env):
    """The most damaging extraction failure available here.

    "I hate the heat" and "I love the heat" share a keyword and mean opposite
    things. Plain substring matching stores the reverse of what was said, so a
    negated match is inverted for climate, and dropped wherever inverting would
    itself be a guess.
    """
    store = app_env["store"]

    assert store.normalise_band("climate_preference", "I melt in the heat") == "cool"
    assert store.normalise_band("climate_preference", "hate the heat") == "cool"
    assert store.normalise_band("climate_preference", "not too hot") == "cool"
    assert store.normalise_band("climate_preference", "love the heat") == "hot"

    # "not cheap" could honestly mean any of four bands, so nothing is stored.
    assert store.normalise_band("budget_band", "not cheap") == ""


def test_an_unrecognised_band_is_dropped_rather_than_stored_raw(app_env):
    """Storing "pretty cheap I guess" would render into every agent prompt."""
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "vague")

    store.update_profile(user_id, {"budget_band": "banana", "nationality": "Ireland"})
    profile = store.get_profile(user_id)

    assert profile["budget_band"] is None
    assert profile["nationality"] == "Ireland"


def test_a_legacy_no_preference_climate_does_not_survive_as_a_value(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "nopref")

    store.update_profile(user_id, {"climate_preference": "no_preference"})
    assert store.get_profile(user_id)["climate_preference"] is None


def test_clearing_a_field_actually_clears_it(app_env):
    """update_profile deliberately cannot clear, so clearing is its own call."""
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "clearer")

    store.update_profile(user_id, {"budget_band": "mid", "nationality": "Spain"})
    store.clear_profile_fields(user_id, ["budget_band"])

    profile = store.get_profile(user_id)
    assert profile["budget_band"] is None
    assert profile["nationality"] == "Spain"


# --------------------------------------------------------------------------- #
# ratings: the signal that drives recommendations
# --------------------------------------------------------------------------- #
def test_a_rating_can_be_set_and_cleared_without_touching_the_review_text(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "rater")

    travel.add_travel_history(user_id, "Hanoi", source="onboarding")
    travel.save_review(user_id, "Hanoi", rating=2, review_notes="too loud")

    assert travel.set_rating(user_id, "hanoi", 4) is True
    entry = travel.get_travel_history(user_id)[0]
    assert entry["rating"] == 4
    assert entry["review_notes"] == "too loud"

    assert travel.set_rating(user_id, "Hanoi", None) is True
    assert travel.get_travel_history(user_id)[0]["rating"] is None


def test_rating_somewhere_not_in_the_history_fails_rather_than_inventing_a_stop(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "phantom")

    assert travel.set_rating(user_id, "Atlantis", 5) is False
    assert travel.get_travel_history(user_id) == []


def test_the_prompt_block_separates_liked_from_disliked_and_says_to_generalise(app_env):
    """The whole point of collecting ratings.

    Somebody who rated Hanoi 2/5 is telling the assistant something about big,
    loud cities generally, not only about Hanoi. An earlier version listed the
    last four ratings with no framing at all, so a 1/5 read to the model as a
    neutral fact about one town.
    """
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "prompted")

    travel.add_travel_history(user_id, "Hanoi", source="onboarding")
    travel.add_travel_history(user_id, "Pai", source="onboarding")
    travel.save_review(user_id, "Hanoi", rating=2, review_notes="too loud, traffic everywhere")
    travel.save_review(user_id, "Pai", rating=5, review_notes="canyon at sunset")

    block = travel.format_travel_for_prompt(travel.get_travel_snapshot(user_id))

    assert "Did NOT enjoy: Hanoi 2/5" in block
    assert "too loud, traffic everywhere" in block
    assert "Rated highly: Pai 5/5" in block
    assert "rank lower" in block


def test_a_stop_can_be_removed_from_the_route(app_env):
    """A visit inferred wrongly would otherwise skew every future answer."""
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "corrector")

    travel.add_travel_history(user_id, "Pai", source="tracked")
    assert travel.remove_travel_history(user_id, "pai") is True
    assert travel.get_travel_history(user_id) == []
    assert travel.remove_travel_history(user_id, "Pai") is False


# --------------------------------------------------------------------------- #
# onboarding: from one extracted answer to stored rows
# --------------------------------------------------------------------------- #
def test_onboarding_capture_writes_route_ratings_passports_and_bands(app_env):
    """The whole onboarding contract, asserted on stored rows.

    This is what the welcome page's first question produces once extraction has
    run: an ordered route with ratings attached, passports normalised from
    adjectives to country names, and free-text bands mapped onto the scales.
    """
    import backend.agents.onboarding as onboarding

    importlib.reload(onboarding)
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "onboard_capture")

    writes = onboarding.apply_capture(
        user_id,
        {
            "travel_history": [
                {"location": "bangkok", "order": 1, "rating": 3,
                 "review_notes": "would not rush back"},
                {"location": "Koh Tao, Thailand", "order": 2, "rating": 5},
                {"location": "chiang mai", "order": 3},
            ],
            "wishlist": [{"location": "pai", "priority": 1}],
            "passports": ["British", "Irish"],
            "interests": ["Trekking", "diving"],
            "social_style": "just me",
            "budget_band": "dirt cheap",
            "travel_style": "as slow as I can",
            "climate_preference": "I melt in the heat",
            "current_location": "chiang mai",
        },
    )

    route = travel.get_travel_history(user_id)
    assert [h["location"] for h in route] == ["Bangkok", "Koh Tao", "Chiang Mai"]
    assert [h["rating"] for h in route] == [3, 5, None]
    # "Koh Tao, Thailand" must resolve to the town, with the country alongside.
    assert route[1]["country"] == "Thailand"

    assert [w["location"] for w in travel.get_wishlist(user_id)] == ["Pai"]

    profile = store.get_profile(user_id)
    assert profile["passports"] == ["United Kingdom", "Ireland"]
    assert profile["budget_band"] == "shoestring"
    assert profile["travel_style"] == "slow"
    assert profile["climate_preference"] == "cool"
    assert profile["social_style"] == "solo"
    assert profile["current_location"] == "Chiang Mai"
    assert sorted(travel.get_interests(user_id)) == ["diving", "trekking"]

    # Every write is echoed back, because the welcome page shows the traveller
    # exactly what was taken from their answer.
    assert {w["operation"] for w in writes} >= {
        "add_travel_history", "add_wishlist", "set_passports",
        "set_interests", "set_social_style", "update_profile",
    }


def test_onboarding_capture_is_idempotent_on_a_repeated_answer(app_env):
    """Redoing a question must correct the profile, not duplicate the route."""
    import backend.agents.onboarding as onboarding

    importlib.reload(onboarding)
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "onboard_repeat")

    captured = {"travel_history": [{"location": "Bangkok", "order": 1, "rating": 4}]}
    onboarding.apply_capture(user_id, captured)
    onboarding.apply_capture(user_id, captured)

    route = travel.get_travel_history(user_id)
    assert [h["location"] for h in route] == ["Bangkok"]
    assert route[0]["rating"] == 4


def test_onboarding_capture_ignores_junk_without_failing(app_env):
    """Extraction is best-effort, so bad output must never break the flow."""
    import backend.agents.onboarding as onboarding

    importlib.reload(onboarding)
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "onboard_junk")

    writes = onboarding.apply_capture(
        user_id,
        {
            "travel_history": [{"location": ""}, "not a dict", {"no_location": 1}],
            "wishlist": [{"location": None}],
            "passports": ["", "   "],
            "interests": [],
            "budget_band": "hmm not sure really",
            "nothing_to_extract": True,
        },
    )

    assert writes == []
    assert travel.get_travel_history(user_id) == []
    assert travel.get_wishlist(user_id) == []


def test_onboarding_steps_are_tracked_so_a_resumed_session_does_not_repeat_one(app_env):
    """Progress is stored per question, not as a single cursor.

    A single "current step" pointer could not express "skipped question 2,
    answered question 3", so a resumed session re-asked something already dealt
    with.
    """
    import backend.agents.onboarding as onboarding

    importlib.reload(onboarding)
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "onboard_resume")

    assert travel.get_onboarding(user_id)["answered"] == []
    assert onboarding.next_step([]) == onboarding.QUESTION_IDS[0]

    travel.mark_step_answered(user_id, "route")
    travel.mark_step_answered(user_id, "route")  # idempotent
    answered = travel.mark_step_answered(user_id, "timing")

    assert answered == ["route", "timing"]
    assert travel.get_onboarding(user_id)["answered"] == ["route", "timing"]
    assert onboarding.next_step(answered) == "passports"
    assert onboarding.next_step(list(onboarding.QUESTION_IDS)) is None


def test_style_and_interests_save_for_an_account_with_no_profile_row_yet(app_env):
    """Regression: an UPDATE against a missing row reports no error.

    set_social_style and the interests mirror both wrote with a bare UPDATE, so
    for a brand-new account - which is every account arriving at onboarding -
    they silently did nothing. Caught by an eval case that captured the budget,
    the pace and the interests correctly and lost only "solo".
    """
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "rowless")
    store.forget_account_memory(user_id)

    assert travel.set_social_style(user_id, "solo") == "solo"
    travel.set_interests(user_id, ["diving"])

    profile = store.get_profile(user_id)
    assert profile["social_style"] == "solo"
    assert "diving" in (profile["interests"] or "")


# --------------------------------------------------------------------------- #
# regressions from real usage: markdown/nav bugs are frontend-only, but these
# four are backend and each was reproduced against the real model before being
# fixed - see notes/08-decisions-log.md for the write-up.
# --------------------------------------------------------------------------- #
def test_trip_start_and_end_dates_are_gone_from_the_profile(app_env):
    """Removed on request: they added little and the parser kept inventing them.

    The columns still exist in SQLite (dropping a column is a bigger migration
    than this warrants) but nothing in the app may read or write them any more.
    """
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "nodates")

    assert "trip_start_date" not in store.PROFILE_FIELDS
    assert "trip_end_date" not in store.PROFILE_FIELDS

    store.update_profile(user_id, {
        "trip_start_date": "2026-01-01", "trip_end_date": "2026-02-01",
        "nationality": "Spain",
    })
    profile = store.get_profile(user_id)
    assert "trip_start_date" not in profile
    assert "trip_end_date" not in profile
    assert profile["nationality"] == "Spain"


def test_forget_everything_actually_wipes_the_extension_tables(app_env):
    """Regression: forget_account_memory only wiped the base-app tables.

    A user who read "erase everything Travel Steezy remembers about your trip"
    and clicked it would have found their entire route, wishlist, ratings,
    interests and onboarding status completely untouched.
    """
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "forgetter")

    travel.add_travel_history(user_id, "Hanoi", source="onboarding")
    travel.save_review(user_id, "Hanoi", rating=2, review_notes="too loud")
    travel.add_wishlist(user_id, "Pai", priority=1)
    travel.set_interests(user_id, ["diving"])
    travel.set_onboarding(user_id, status="complete", step="done")
    store.set_passports(user_id, ["United Kingdom"])

    store.forget_account_memory(user_id)

    assert travel.get_travel_history(user_id) == []
    assert travel.get_wishlist(user_id) == []
    assert travel.get_interests(user_id) == []
    assert store.get_passports(user_id) == []
    # A full wipe sends them back through onboarding - that is the point of a
    # full wipe, and it is exactly what the router's onboarding gate checks for.
    assert travel.get_onboarding(user_id)["status"] == "not_started"
    # The audit log is itself account data and is wiped too - except the one
    # entry that records the wipe happened at all.
    writes = store.get_write_log(user_id, limit=50)
    assert len(writes) == 1
    assert writes[0]["operation"] == "forget_account_memory"


# --------------------------------------------------------------------------- #
# onboarding step-scoping: the code-level gate behind the route-order bug fix
# --------------------------------------------------------------------------- #
def test_only_the_route_question_may_write_travel_history(app_env):
    """A hard code-level gate, not just a prompt instruction.

    Reproduced against the real model: the "timing" question ("is anything
    about to expire?") produced a phantom travel_history entry 6/6 times
    whenever the answer restated the traveller's current location in passing -
    which real answers to that question naturally do. Because
    add_travel_history's order_index was assigned per extractor call, that
    phantom entry collided with the route question's own numbering and was
    inserted in the MIDDLE of the route, not the end: "Melbourne, Thailand,
    Sydney, Cairns..." instead of the traveller's actual order.
    """
    import backend.agents.onboarding as onboarding
    importlib.reload(onboarding)
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "scoped_history")

    captured = {"travel_history": [{"location": "Phantom City", "order": 1}]}
    onboarding.apply_capture(user_id, captured, step_id="timing")
    onboarding.apply_capture(user_id, captured, step_id="style")
    onboarding.apply_capture(user_id, captured, step_id="passports")
    onboarding.apply_capture(user_id, captured, step_id="wishlist")
    assert travel.get_travel_history(user_id) == []

    onboarding.apply_capture(user_id, captured, step_id="route")
    assert [h["location"] for h in travel.get_travel_history(user_id)] == ["Phantom City"]


def test_only_route_or_wishlist_questions_may_write_the_wishlist(app_env):
    import backend.agents.onboarding as onboarding
    importlib.reload(onboarding)
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "scoped_wishlist")

    captured = {"wishlist": [{"location": "Pai", "priority": 1}]}
    onboarding.apply_capture(user_id, captured, step_id="timing")
    onboarding.apply_capture(user_id, captured, step_id="style")
    assert travel.get_wishlist(user_id) == []

    onboarding.apply_capture(user_id, captured, step_id="route")
    onboarding.apply_capture(user_id, {"wishlist": [{"location": "Laos", "priority": 2}]},
                              step_id="wishlist")
    assert sorted(w["location"] for w in travel.get_wishlist(user_id)) == ["Laos", "Pai"]


def test_only_the_passports_question_may_write_passports(app_env):
    """The direct fix for hallucinating a passport from a place merely visited.

    Reproduced against the real model: answering "I started my trip in
    Australia, then went to Bali, and now I'm in Chiang Mai" on the PASSPORTS
    question produced passports=["Australia"] 2/6 times, purely from the
    starting point of the route - not a citizenship statement. Gating passport
    writes to the one question that actually asks about citizenship removes the
    class of bug regardless of what the extractor returns.
    """
    import backend.agents.onboarding as onboarding
    importlib.reload(onboarding)
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "scoped_passports")

    captured = {"passports": ["Australia"]}
    onboarding.apply_capture(user_id, captured, step_id="route")
    onboarding.apply_capture(user_id, captured, step_id="timing")
    onboarding.apply_capture(user_id, captured, step_id="style")
    onboarding.apply_capture(user_id, captured, step_id="wishlist")
    assert store.get_passports(user_id) == []

    onboarding.apply_capture(user_id, captured, step_id="passports")
    assert store.get_passports(user_id) == ["Australia"]


def test_gating_is_skipped_when_no_step_id_is_given(app_env):
    """Direct callers (tests, a future admin tool) can still write everything at
    once - the gate only applies when a step_id is actually supplied, which is
    what the real onboarding flow always does."""
    import backend.agents.onboarding as onboarding
    importlib.reload(onboarding)
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "ungated")

    onboarding.apply_capture(user_id, {
        "travel_history": [{"location": "Pai", "order": 1}],
        "wishlist": [{"location": "Laos", "priority": 1}],
        "passports": ["Ireland"],
    })
    assert [h["location"] for h in travel.get_travel_history(user_id)] == ["Pai"]
    assert [w["location"] for w in travel.get_wishlist(user_id)] == ["Laos"]
    assert store.get_passports(user_id) == ["Ireland"]


def test_new_history_entries_always_continue_the_stored_route(app_env):
    """order_index is rebased on the CURRENT stored max, not restarted at 1.

    Trusting a purely local index (or the model's own "order" field) per
    extractor call is what let an unrelated call's entry collide with the route
    question's own numbering. Two separate apply_capture calls for the route
    question - which is the only realistic way this table grows during
    onboarding - must never produce two rows with the same order_index.
    """
    import backend.agents.onboarding as onboarding
    importlib.reload(onboarding)
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "continues_route")

    onboarding.apply_capture(
        user_id,
        {"travel_history": [{"location": "Melbourne", "order": 1}, {"location": "Sydney", "order": 2}]},
        step_id="route",
    )
    # A second, later call (e.g. the traveller went back and added to their
    # answer) must append after Sydney, not restart at order 1 and collide.
    onboarding.apply_capture(
        user_id,
        {"travel_history": [{"location": "Cairns", "order": 1}]},
        step_id="route",
    )
    history = travel.get_travel_history(user_id)
    assert [h["location"] for h in history] == ["Melbourne", "Sydney", "Cairns"]
    assert [h["order_index"] for h in history] == sorted(h["order_index"] for h in history)
    assert len({h["order_index"] for h in history}) == 3


# --------------------------------------------------------------------------- #
# the memory debug page's backend primitives
# --------------------------------------------------------------------------- #
def test_remove_interest_deletes_one_and_leaves_the_rest(app_env):
    travel, store, db = app_env["travel"], app_env["store"], app_env["db"]
    user_id = make_user(db, "trims_interests")

    travel.set_interests(user_id, ["diving", "hiking", "food"])
    assert travel.remove_interest(user_id, "hiking") is True

    remaining = travel.get_interests(user_id)
    assert sorted(remaining) == ["diving", "food"]
    # The free-text mirror agents read from the trip profile must stay in sync.
    assert "hiking" not in (store.get_profile(user_id)["interests"] or "")
    assert travel.remove_interest(user_id, "hiking") is False


def test_get_interests_with_weight_exposes_the_raw_rows(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "weighted_interests")

    travel.set_interests(user_id, ["diving"])
    travel.set_interests(user_id, ["diving"])  # mentioned twice, weight increments

    rows = travel.get_interests_with_weight(user_id)
    assert rows[0]["interest"] == "diving"
    assert rows[0]["weight"] >= 2


def test_remove_passport_promotes_the_next_one_to_primary(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "trims_passports")

    store.set_passports(user_id, ["United Kingdom", "Ireland"])
    remaining = store.remove_passport(user_id, "united kingdom")

    assert remaining == ["Ireland"]
    assert store.get_profile(user_id)["nationality"] == "Ireland"
    # Removing something not on file is a harmless no-op, not an error.
    assert store.remove_passport(user_id, "France") == ["Ireland"]


def test_reset_onboarding_clears_progress_but_not_the_profile(app_env):
    """"Redo the questions" must actually let someone redo them.

    Before this existed, clicking it just reopened the welcome page, which
    computed next_step from the SAME answered list and landed straight back on
    the review screen - nothing was actually reset.
    """
    import backend.agents.onboarding as onboarding
    importlib.reload(onboarding)
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "redo_onboarding")

    travel.add_travel_history(user_id, "Pai", source="onboarding")
    travel.mark_step_answered(user_id, "route")
    travel.mark_step_answered(user_id, "timing")
    travel.set_onboarding(user_id, status="complete", step="done")

    travel.reset_onboarding(user_id)

    state = travel.get_onboarding(user_id)
    assert state["status"] == "not_started"
    assert state["answered"] == []
    assert onboarding.next_step(state["answered"]) == "route"
    # The existing route is untouched - this is "redo the interview", not
    # "forget everything" (that is store.forget_account_memory).
    assert [h["location"] for h in travel.get_travel_history(user_id)] == ["Pai"]


def test_raw_profile_row_exposes_deprecated_columns_for_debugging(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "raw_row")

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET trip_start_date = ? WHERE user_id = ?",
            ("2020-01-01", user_id),
        )

    row = store.get_raw_profile_row(user_id)
    # get_profile() must NOT surface it - nothing in the app reads it any more.
    assert "trip_start_date" not in store.get_profile(user_id)
    # but the raw debug view sees the actual column, so a developer can confirm
    # an old value is really inert rather than assuming it.
    assert row["trip_start_date"] == "2020-01-01"


def test_list_own_documents_computes_ids_and_checks_rather_than_trusts(app_env, monkeypatch):
    """Reports what was actually fetched from the store, not what was submitted.

    fetch_by_ids is monkeypatched rather than hitting a real index - this file's
    own contract is "no API keys and no network" - but the point under test is
    real: list_own_documents must derive the exact ids a review/outcome would
    have produced and ask the store for THOSE, not assume publication happened
    just because a review was saved locally.
    """
    from backend.rag import experience

    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "published_docs")

    travel.add_travel_history(user_id, "Pai", source="onboarding")
    travel.save_review(user_id, "Pai", rating=5, review_notes="canyon at sunset, unreal")

    seen_ids = []

    def fake_fetch(ids, namespace="experience"):
        seen_ids.extend(ids)
        # Simulate the store genuinely holding only ONE of the candidate ids -
        # proving the function reports what came BACK, not what was asked for.
        return [{"id": ids[0], "metadata": {"text": "stub"}, "text": "stub"}] if ids else []

    monkeypatch.setattr(experience.rag_store, "fetch_by_ids", fake_fetch)

    docs = experience.list_own_documents(user_id)
    assert seen_ids == [f"experience-review-u{user_id}-pai"]
    assert [d["id"] for d in docs] == seen_ids


def test_list_own_documents_is_empty_with_nothing_to_report(app_env, monkeypatch):
    from backend.rag import experience

    db = app_env["db"]
    user_id = make_user(db, "nothing_published")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("fetch_by_ids should not be called with no candidates")

    monkeypatch.setattr(experience.rag_store, "fetch_by_ids", fail_if_called)
    assert experience.list_own_documents(user_id) == []


# --------------------------------------------------------------------------- #
# catch-up: "here's where we left off - what's changed?"
# --------------------------------------------------------------------------- #
def test_a_brand_new_account_has_no_catchup_due(app_env):
    """Nothing to catch up on until there has been a real turn to catch up from."""
    from backend.agents import catchup
    db = app_env["db"]
    user_id = make_user(db, "catchup_fresh")

    result = catchup.status(user_id)
    assert result["due"] is False
    assert result["last_active_date"] is None
    assert result["summary"] == ""


def test_catchup_is_due_after_a_calendar_day_gap(app_env):
    from datetime import date, timedelta
    from backend.agents import catchup
    db = app_env["db"]
    user_id = make_user(db, "catchup_gap")

    yesterday = (date.today() - timedelta(days=3)).isoformat()
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET last_active_date = ? WHERE user_id = ?",
            (yesterday, user_id),
        )

    result = catchup.status(user_id)
    assert result["due"] is True
    assert result["days_since"] == 3
    assert "3 days ago" in result["summary"]


def test_catchup_is_not_due_the_same_day(app_env):
    from backend.agents import catchup
    db = app_env["db"]
    user_id = make_user(db, "catchup_sameday")

    catchup.touch_last_active(user_id)
    assert catchup.status(user_id)["due"] is False


def test_dismiss_clears_catchup_without_any_model_call(app_env):
    """The quick "still here" button - pure Python, no LLM involved."""
    from datetime import date, timedelta
    from backend.agents import catchup
    db = app_env["db"]
    user_id = make_user(db, "catchup_dismiss")

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET last_active_date = ? WHERE user_id = ?",
            ((date.today() - timedelta(days=2)).isoformat(), user_id),
        )
    assert catchup.status(user_id)["due"] is True

    catchup.dismiss(user_id)
    assert catchup.status(user_id)["due"] is False
    assert catchup.get_last_active_date(user_id) == date.today().isoformat()


def test_catchup_summary_mentions_location_and_wishlist(app_env):
    from datetime import date, timedelta
    from backend.agents import catchup
    store, travel, db = app_env["store"], app_env["travel"], app_env["db"]
    user_id = make_user(db, "catchup_summary")

    store.update_profile(user_id, {"current_location": "Chiang Mai"})
    travel.add_wishlist(user_id, "Pai", priority=1)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET last_active_date = ? WHERE user_id = ?",
            ((date.today() - timedelta(days=1)).isoformat(), user_id),
        )

    summary = catchup.status(user_id)["summary"]
    assert "yesterday" in summary
    assert "Chiang Mai" in summary
    assert "Pai" in summary


def test_real_chat_turns_update_last_active_but_onboarding_does_not(app_env, monkeypatch):
    """run_turn touches last_active_date; the onboarding endpoints never call it -
    a brand-new account finishing onboarding without ever sending a real message
    correctly has nothing to catch up on yet."""
    from backend.agents import catchup
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "catchup_onboarding_only")
    travel.set_onboarding(user_id, status="complete", step="done")

    assert catchup.get_last_active_date(user_id) is None
    assert catchup.status(user_id)["due"] is False


def test_touching_last_active_survives_the_llm_disabled_path(app_env, monkeypatch):
    """Regression: an earlier version touched last_active_date AFTER the
    llm_enabled check, so answering the catch-up card while the LLM was
    unavailable never actually cleared tomorrow's prompt. Caught by an HTTP
    smoke test, not by inspection - this pins it as a real unit test too."""
    import asyncio
    from datetime import date, timedelta
    import backend.agents.runner as runner_mod
    from backend.agents import catchup

    db = app_env["db"]
    user_id = make_user(db, "llm_disabled_touch")
    # llm_enabled is a read-only property computed from the key; unset the key
    # on the actual Settings instance runner.py holds (it binds `settings` by
    # value at import time, so patching a freshly-reloaded config module's
    # instance would silently miss it).
    monkeypatch.setattr(runner_mod.settings, "openai_api_key", None)
    run_turn = runner_mod.run_turn

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE trip_profile SET last_active_date = ? WHERE user_id = ?",
            ((date.today() - timedelta(days=2)).isoformat(), user_id),
        )
    assert catchup.status(user_id)["due"] is True

    asyncio.run(run_turn(user_id, "Left Chiang Mai, now in Pai."))

    assert catchup.get_last_active_date(user_id) == date.today().isoformat()
    assert catchup.status(user_id)["due"] is False
