"""One-shot boot tasks, run before uvicorn starts on every deploy.

Idempotent by design, because Railway runs it on every restart:
  1. create the SQLite schema on the mounted volume if it is not there yet
  2. ingest the RAG seed corpus if the index is empty
  3. optionally seed a pre-approved demo account

The demo account exists so the production-readiness check ("a stranger opens the
URL in incognito and it works") never depends on a human being awake to click
approve. It is only created when DEMO_USERNAME and DEMO_PASSWORD are both set.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings  # noqa: E402
from backend.db import get_conn, init_db  # noqa: E402
from backend.memory import store  # noqa: E402
from backend.rag import store as rag_store  # noqa: E402
from backend.security import hash_password  # noqa: E402


def ensure_schema() -> None:
    settings.ensure_dirs()
    init_db()
    print(f"[bootstrap] database ready at {settings.db_path}")


def ensure_rag() -> None:
    stats = rag_store.index_stats()
    populated = False
    if stats.get("backend") == "local-json":
        populated = bool(stats.get("documents"))
    else:
        total = (stats.get("stats") or {}).get("total_vector_count")
        populated = bool(total)

    if populated:
        print(f"[bootstrap] RAG index already populated ({rag_store.backend_name()})")
        return

    if not settings.llm_enabled and not settings.pinecone_enabled:
        print("[bootstrap] no OPENAI_API_KEY - ingesting with the local hash embedder")

    try:
        result = rag_store.ingest()
        print(f"[bootstrap] ingested {result['documents']} chunks into {result['backend']}")
    except Exception as exc:  # noqa: BLE001
        # A failed ingest must not stop the app booting; /health will show the
        # RAG as empty and the agents will say they have no passages.
        print(f"[bootstrap] WARNING: RAG ingest failed: {exc}")


def ensure_demo_account() -> None:
    username = os.getenv("DEMO_USERNAME")
    password = os.getenv("DEMO_PASSWORD")
    if not username or not password:
        print("[bootstrap] no DEMO_USERNAME/DEMO_PASSWORD set - skipping demo account")
        return

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, status FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
        if row is None:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, status, approved_at) "
                "VALUES (?,?, 'approved', datetime('now'))",
                (username, hash_password(password)),
            )
            user_id = int(cursor.lastrowid)
            created = True
        else:
            user_id = int(row["id"])
            created = False
            if row["status"] != "approved":
                conn.execute(
                    "UPDATE users SET status = 'approved', approved_at = datetime('now') "
                    "WHERE id = ?",
                    (user_id,),
                )

    store.ensure_profile(user_id)

    # Give the demo account a starting profile ONLY on first creation, so a live
    # demo has something to show immediately. Never overwrite it afterwards -
    # that would silently clobber whatever was demonstrated last time.
    if created:
        store.update_profile(
            user_id,
            {
                "budget_band": "shoestring",
                "travel_style": "slow",
                "climate_preference": "temperate",
                "current_location": "Thailand",
                "trip_start_date": "2026-09-01",
                "trip_end_date": "2026-12-15",
                "interests": "diving, hiking, street food, temples",
            },
            source="seed",
        )
        store.set_passports(user_id, ["United Kingdom"], source="seed")

        from backend.memory import travel

        # A route with ratings on it, because the ratings are what the profile is
        # FOR: a marker landing cold should be able to see a 2/5 in the history
        # panel and then watch it argue against a similar destination.
        for order, (location, country, rating, note) in enumerate(
            [
                ("Bangkok", "Thailand", 3, "fine, but I would not rush back"),
                ("Koh Tao", "Thailand", 5, "did my Open Water here, best two weeks of the trip"),
                ("Hanoi", "Vietnam", 2, "too loud and too busy for me"),
                ("Chiang Mai", "Thailand", None, None),
            ],
            start=1,
        ):
            travel.add_travel_history(
                user_id, location=location, country=country,
                source="seed", order_index=order,
            )
            if rating is not None:
                travel.save_review(
                    user_id, location=location, rating=rating,
                    review_notes=note, source="seed",
                )
        travel.add_wishlist(user_id, "Pai", country="Thailand", priority=1, source="seed")
        travel.set_interests(
            user_id, ["diving", "trekking", "food"], source="seed", replace=True
        )
        travel.set_social_style(user_id, "solo", source="seed")

        # Mark it onboarded, or the demo account lands on the welcome page and is
        # asked for a profile it already has. A marker seeing onboarding should
        # register a NEW account, which is what the README's demo script says.
        travel.set_onboarding(user_id, status="complete", step="done")
        print(f"[bootstrap] created pre-approved demo account {username!r} with a seeded profile")
    else:
        print(f"[bootstrap] demo account {username!r} already exists (approved, profile untouched)")


def main() -> int:
    print("[bootstrap] starting")
    ensure_schema()
    ensure_rag()
    ensure_demo_account()
    print("[bootstrap] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
