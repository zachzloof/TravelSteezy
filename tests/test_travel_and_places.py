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
def test_cannot_wishlist_somewhere_already_visited(app_env):
    travel, db = app_env["travel"], app_env["db"]
    user_id = make_user(db, "been")

    travel.add_travel_history(user_id, "Chiang Mai", source="onboarding")
    result = travel.add_wishlist(user_id, "chiang mai")

    assert result["ok"] is False
    assert result["reason"] == "already visited"
    assert travel.get_wishlist(user_id) == []


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

    assert travel.onboarding_gaps(user_id)["missing"] == ["history", "wishlist", "preferences"]

    travel.add_travel_history(user_id, "Bangkok", source="onboarding")
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
