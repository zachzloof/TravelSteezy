"""Tests for the memory store, the API surface and cross-account isolation.

These run against a throwaway SQLite file and need no API keys, so they stay fast
and can gate a deploy. The agent graph itself is covered by evals/, not here.

    python -m pytest tests -q
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def app_env(monkeypatch):
    """Fresh settings + database per test, isolated in a temp directory."""
    tmp = tempfile.mkdtemp(prefix="onward-test-")
    monkeypatch.setenv("DATA_DIR", tmp)
    monkeypatch.setenv("DB_PATH", str(Path(tmp) / "test.sqlite3"))
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-pw")
    monkeypatch.setenv("ADMIN_AUTO_APPROVE", "false")
    monkeypatch.setenv("SERVE_FRONTEND", "false")

    import backend.config as config

    importlib.reload(config)
    import backend.db as db

    importlib.reload(db)
    import backend.memory.store as store

    importlib.reload(store)
    db.init_db()
    return {"config": config, "db": db, "store": store, "tmp": tmp}


def make_user(db, username: str, status: str = "approved") -> int:
    from backend.security import hash_password

    with db.get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, status) VALUES (?,?,?)",
            (username, hash_password("password123"), status),
        )
        return int(cursor.lastrowid)


# --------------------------------------------------------------------------- #
# memory: what we keep / write / retrieve
# --------------------------------------------------------------------------- #
def test_profile_starts_empty_and_round_trips(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "alice")

    profile = store.get_profile(user_id)
    assert profile["nationality"] is None

    store.update_profile(user_id, {"nationality": "Ireland", "budget_band": "shoestring"})
    profile = store.get_profile(user_id)
    assert profile["nationality"] == "Ireland"
    assert profile["budget_band"] == "shoestring"


def test_update_profile_ignores_unknown_fields(app_env):
    """An LLM tool call must not be able to invent columns."""
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "bob")

    store.update_profile(user_id, {"nationality": "Canada", "evil_column": "boom", "id": 999})
    profile = store.get_profile(user_id)
    assert profile["nationality"] == "Canada"
    assert "evil_column" not in profile


def test_update_profile_normalises_enums(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "carol")

    store.update_profile(user_id, {"budget_band": "SHOESTRING", "travel_style": "Slow"})
    profile = store.get_profile(user_id)
    assert profile["budget_band"] == "shoestring"
    assert profile["travel_style"] == "slow"


def test_empty_update_is_a_no_op(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "dave")
    store.update_profile(user_id, {"nationality": "Spain"})
    store.update_profile(user_id, {"nationality": "   ", "budget_band": None})
    assert store.get_profile(user_id)["nationality"] == "Spain"


def test_every_write_is_audited(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "erin")

    store.update_profile(user_id, {"nationality": "Italy"}, source="agent")
    store.update_profile(user_id, {"budget_band": "mid"}, source="user_edit")

    log = store.get_write_log(user_id)
    assert [entry["source"] for entry in log] == ["user_edit", "agent"]


# --------------------------------------------------------------------------- #
# memory: when we forget
# --------------------------------------------------------------------------- #
def test_departure_archives_current_location(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "frank")
    store.update_profile(user_id, {"current_location": "Laos"})

    result = store.log_departure(user_id, "Laos", departure_date="2026-03-01")

    assert result["archived_from_active_context"] is True
    assert store.get_profile(user_id)["current_location"] is None
    history = store.get_visited_history(user_id)
    assert history[0]["country"] == "Laos"
    assert history[0]["departure_date"] == "2026-03-01"


def test_departure_from_elsewhere_leaves_location_alone(app_env):
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "grace")
    store.update_profile(user_id, {"current_location": "Thailand"})

    result = store.log_departure(user_id, "Cambodia")

    assert result["archived_from_active_context"] is False
    assert store.get_profile(user_id)["current_location"] == "Thailand"
    # still recorded in history - forgetting is archival, not deletion
    assert store.get_visited_history(user_id)[0]["country"] == "Cambodia"


def test_working_memory_is_pruned_but_profile_is_not(app_env):
    store, db = app_env["store"], app_env["db"]
    config = app_env["config"]
    config.settings.working_memory_turns = 4
    user_id = make_user(db, "heidi")
    store.update_profile(user_id, {"nationality": "Japan"})

    for i in range(10):
        store.append_turn(user_id, "user", f"message {i}")

    turns = store.get_recent_turns(user_id)
    assert len(turns) == 4
    assert turns[-1]["content"] == "message 9"
    # the durable profile is untouched by scrollback decay
    assert store.get_profile(user_id)["nationality"] == "Japan"


def test_forget_account_memory_scoped_to_one_account(app_env):
    store, db = app_env["store"], app_env["db"]
    keep = make_user(db, "ivan")
    wipe = make_user(db, "judy")
    for user_id in (keep, wipe):
        store.update_profile(user_id, {"nationality": "Peru"})
        store.log_departure(user_id, "Chile")

    store.forget_account_memory(wipe)

    assert store.get_profile(wipe)["nationality"] is None
    assert store.get_visited_history(wipe) == []
    assert store.get_profile(keep)["nationality"] == "Peru"
    assert len(store.get_visited_history(keep)) == 1


# --------------------------------------------------------------------------- #
# memory: persistence across a fresh session
# --------------------------------------------------------------------------- #
def test_profile_survives_reopening_the_database(app_env):
    """The literal 'memory persists across a fresh session' requirement."""
    store, db = app_env["store"], app_env["db"]
    user_id = make_user(db, "kate")
    store.update_profile(
        user_id, {"nationality": "Brazil", "budget_band": "mid", "current_location": "Vietnam"}
    )
    before = store.get_profile(user_id)

    # Reload the modules: every connection is dropped and reopened from the file.
    importlib.reload(db)
    importlib.reload(store)

    after = store.get_profile(user_id)
    for field in ("nationality", "budget_band", "current_location"):
        assert after[field] == before[field]


# --------------------------------------------------------------------------- #
# API: auth, admin approval, isolation
# --------------------------------------------------------------------------- #
@pytest.fixture()
def client(app_env):
    from fastapi.testclient import TestClient

    import backend.main as main

    importlib.reload(main)
    return TestClient(main.app)


def test_registration_is_pending_until_approved(client):
    response = client.post(
        "/auth/register", json={"username": "newbie", "password": "password123"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["access_token"] is None

    login = client.post("/auth/login", json={"username": "newbie", "password": "password123"})
    assert login.status_code == 403
    assert "approval" in login.json()["detail"].lower()


def test_duplicate_username_is_rejected(client):
    client.post("/auth/register", json={"username": "dupe", "password": "password123"})
    again = client.post("/auth/register", json={"username": "DUPE", "password": "password123"})
    assert again.status_code == 409


def test_admin_approval_unlocks_login(client):
    client.post("/auth/register", json={"username": "pending1", "password": "password123"})

    admin = client.post("/admin/login", json={"password": "test-admin-pw"})
    assert admin.status_code == 200
    headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}

    pending = client.get("/admin/pending", headers=headers).json()
    assert [u["username"] for u in pending] == ["pending1"]

    client.post(f"/admin/approve/{pending[0]['id']}", headers=headers)
    login = client.post("/auth/login", json={"username": "pending1", "password": "password123"})
    assert login.status_code == 200


def test_wrong_admin_password_rejected(client):
    assert client.post("/admin/login", json={"password": "nope"}).status_code == 401


def test_user_token_cannot_reach_admin_routes(client):
    client.post("/auth/register", json={"username": "plain", "password": "password123"})
    admin = client.post("/admin/login", json={"password": "test-admin-pw"}).json()
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}
    pending = client.get("/admin/pending", headers=admin_headers).json()
    client.post(f"/admin/approve/{pending[0]['id']}", headers=admin_headers)

    token = client.post(
        "/auth/login", json={"username": "plain", "password": "password123"}
    ).json()["access_token"]

    response = client.get("/admin/pending", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_profile_requires_auth(client):
    assert client.get("/profile/me").status_code == 401
    assert client.get(
        "/profile/me", headers={"Authorization": "Bearer not-a-real-token"}
    ).status_code == 401


def _approved_token(client, username: str) -> str:
    client.post("/auth/register", json={"username": username, "password": "password123"})
    admin = client.post("/admin/login", json={"password": "test-admin-pw"}).json()
    headers = {"Authorization": f"Bearer {admin['access_token']}"}
    for user in client.get("/admin/pending", headers=headers).json():
        if user["username"] == username:
            client.post(f"/admin/approve/{user['id']}", headers=headers)
    return client.post(
        "/auth/login", json={"username": username, "password": "password123"}
    ).json()["access_token"]


def test_profiles_are_isolated_between_accounts(client):
    token_a = _approved_token(client, "accounta")
    token_b = _approved_token(client, "accountb")
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    client.patch("/profile/me", headers=auth_a, json={"nationality": "Ireland", "current_location": "Nepal"})
    client.patch("/profile/me", headers=auth_b, json={"nationality": "Germany", "current_location": "Vietnam"})

    profile_a = client.get("/profile/me", headers=auth_a).json()
    profile_b = client.get("/profile/me", headers=auth_b).json()

    assert profile_a["username"] == "accounta"
    assert profile_a["profile"]["nationality"] == "Ireland"
    assert profile_b["profile"]["nationality"] == "Germany"
    assert profile_a["profile"]["current_location"] != profile_b["profile"]["current_location"]


def test_patch_only_touches_submitted_fields(client):
    token = _approved_token(client, "patcher")
    auth = {"Authorization": f"Bearer {token}"}

    client.patch("/profile/me", headers=auth, json={"nationality": "Chile", "budget_band": "mid"})
    client.patch("/profile/me", headers=auth, json={"budget_band": "shoestring"})

    profile = client.get("/profile/me", headers=auth).json()["profile"]
    assert profile["nationality"] == "Chile"
    assert profile["budget_band"] == "shoestring"


def test_patch_rejects_invalid_enum(client):
    token = _approved_token(client, "badenum")
    response = client.patch(
        "/profile/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"budget_band": "lavish"},
    )
    assert response.status_code == 422


def test_departure_endpoint_updates_history(client):
    token = _approved_token(client, "departer")
    auth = {"Authorization": f"Bearer {token}"}
    client.patch("/profile/me", headers=auth, json={"current_location": "Laos"})

    response = client.post(
        "/profile/me/departures", headers=auth, json={"country": "Laos", "departure_date": "2026-04-01"}
    ).json()

    assert response["visited_history"][0]["country"] == "Laos"
    assert response["profile"]["current_location"] is None


def test_health_reports_dependency_status(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "rag" in body and "llm" in body
    assert body["auth"]["admin_configured"] is True
