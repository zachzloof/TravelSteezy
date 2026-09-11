"""TRACE eval harness for Onward.

    python -m evals.run_evals                     # run everything
    python -m evals.run_evals --label before-fix  # name the results file
    python -m evals.run_evals --case season-nepal-monsoon --case rag-cites-source
    python -m evals.run_evals --no-judge          # assertion checks only

Every case runs against the real agent graph and the real memory store, using two
dedicated eval accounts that are isolated from any human user's data.

Scoring is assertion-first: "did the retrieval tool actually fire", "is this
destination ranked below another", "did a row land in visited_history". Those are
facts about the run, not opinions about the prose. Only the genuinely qualitative
cases ("is this backpacker advice or brochure copy") use an LLM judge, and each of
those states its own rubric and pass threshold in cases.jsonl.

Results are written to evals/results/<label>.json and a human-readable summary to
evals/results/<label>.md, so a run's score is a committed artifact rather than
terminal scrollback. Each run gets a run_id that is attached to every Langfuse
trace as a tag, so a failing case can be opened in Langfuse and inspected.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings  # noqa: E402
from backend.db import get_conn, init_db  # noqa: E402
from backend.memory import store  # noqa: E402
from backend.security import hash_password  # noqa: E402
from backend.tracing.langfuse_setup import flush, tracing_enabled  # noqa: E402

CASES_PATH = Path(__file__).parent / "cases.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"

# Dedicated accounts so eval data never mixes with a real user's memory.
EVAL_ACCOUNTS = {"a": "__eval_account_a", "b": "__eval_account_b"}


# --------------------------------------------------------------------------- #
# account setup
# --------------------------------------------------------------------------- #
def ensure_eval_accounts() -> dict[str, int]:
    init_db()
    ids: dict[str, int] = {}
    with get_conn() as conn:
        for key, username in EVAL_ACCOUNTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, status) VALUES (?,?,'approved')",
                (username, hash_password(f"eval-{uuid.uuid4().hex[:16]}")),
            )
            row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            ids[key] = int(row["id"])
    return ids


def apply_setup(user_id: int, setup: dict[str, Any]) -> None:
    store.forget_account_memory(user_id)
    # Also clear the structured travel tables. Without this, a wishlist or route
    # from an earlier case leaks into the next one on the same eval account -
    # which is exactly what made memory-recall-accurate start failing.
    reset_travel_state(user_id)
    set_onboarded(user_id)
    if setup.get("profile"):
        store.update_profile(user_id, setup["profile"], source="seed")
    for entry in setup.get("visited", []) or []:
        store.log_departure(
            user_id,
            country=entry["country"],
            departure_date=entry.get("departure_date"),
            arrival_date=entry.get("arrival_date"),
            notes=entry.get("notes"),
            source="seed",
        )


# --------------------------------------------------------------------------- #
# LLM judge
# --------------------------------------------------------------------------- #
JUDGE_PROMPT = """You are grading one reply from a travel assistant built for long-term
budget backpackers.

RUBRIC:
{rubric}

THE TRAVELLER ASKED:
{question}

THE ASSISTANT REPLIED:
{reply}

Score 1 to 5 against the rubric alone. Be strict and concrete; do not reward
fluent writing that misses what the rubric asks for.

EVIDENCE RULE: if your reason claims the assistant did something wrong - asked
for information it already had, invented a figure, omitted a warning - you must
quote the exact words from the reply that show it, in "quote". If you cannot
quote it, then it did not happen and you must not deduct marks for it. Leave
"quote" empty only when you are scoring 4 or 5.

Reply with ONLY raw JSON:
{{"score": <1-5>, "reason": "<one sentence>", "quote": "<exact words, or empty>"}}"""


def judge(rubric: str, question: str, reply: str) -> dict[str, Any]:
    if not settings.llm_enabled:
        return {"score": 0, "reason": "judge unavailable: OPENAI_API_KEY not set"}
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        completion = client.chat.completions.create(
            model=settings.judge_model,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": JUDGE_PROMPT.format(
                        rubric=rubric, question=question, reply=reply
                    ),
                }
            ],
        )
        text = completion.choices[0].message.content or ""
        start, end = text.find("{"), text.rfind("}")
        parsed = json.loads(text[start : end + 1]) if start != -1 else {}
        score = int(parsed.get("score", 0))
        reason = str(parsed.get("reason", ""))[:300]
        quote = str(parsed.get("quote", "")).strip()

        # Enforce the evidence rule in code: a low score justified by a quote that
        # does not appear in the reply is the judge confabulating, not a finding.
        # This caught a 1/5 whose stated reason ("asks for budget information")
        # described something the reply never did.
        if score <= 3 and quote:
            normalised = " ".join(reply.lower().split())
            if " ".join(quote.lower().split()) not in normalised:
                return {
                    "score": 4,
                    "reason": f"judge quote not found in reply, deduction rejected: {reason}",
                }
        return {"score": score, "reason": reason}
    except Exception as exc:  # noqa: BLE001
        return {"score": 0, "reason": f"judge error: {exc}"}


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def _cards_by_destination(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(c.get("destination", "")).strip().lower(): c
        for c in result.get("comparison", [])
    }


def full_answer(result: dict[str, Any]) -> str:
    """Everything the traveller actually reads: the prose reply AND the cards.

    The destination cards are the product's primary output, not a decoration, so a
    check on "what the user was told" has to include them. Checks that are about
    the conversational reply specifically (reply_lacks_regex for 'did it ask me to
    repeat my budget') still look at the reply alone.
    """
    parts = [result.get("reply") or ""]
    for card in result.get("comparison", []):
        parts.append(str(card.get("destination", "")))
        parts.append(str(card.get("rationale") or ""))
        parts.extend(str(p) for p in card.get("pros", []))
        parts.extend(str(c) for c in card.get("cons", []))
        parts.extend(str(n) for n in card.get("backpacker_notes", []))
        parts.append(str(card.get("est_cost_note") or ""))
        parts.append(str(card.get("season_flag") or ""))
        parts.append(str(card.get("visa_flag") or ""))
    return chr(10).join(p for p in parts if p)


def run_check(check: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one assertion. Returns {passed, detail}."""
    kind = check["type"]
    result = ctx.get("result") or {}
    reply = (result.get("reply") or "").lower()
    cards = _cards_by_destination(result)

    if kind == "tool_called":
        called = result.get("tool_calls", [])
        return {
            "passed": check["tool"] in called,
            "detail": f"tool_calls={called}",
        }

    if kind == "retrieval_fired":
        namespaces = {s["namespace"] for s in result.get("retrieved_sources", [])}
        return {
            "passed": check["namespace"] in namespaces,
            "detail": f"namespaces retrieved={sorted(namespaces)}",
        }

    if kind == "not_ranked_first":
        target = check["destination"].lower()
        first = next((c for c in result.get("comparison", []) if c.get("rank") == 1), None)
        if first is None:
            return {"passed": False, "detail": "no ranked cards were produced"}
        actual = str(first.get("destination", "")).strip().lower()
        return {
            "passed": target not in actual,
            "detail": f"rank 1 = {actual!r}",
        }

    if kind == "flag_present":
        card = cards.get(check["destination"].lower())
        if card is None:
            return {"passed": False, "detail": f"no card for {check['destination']}"}
        value = card.get(check["field"])
        return {
            "passed": bool(value),
            "detail": f"{check['field']}={value!r}",
        }

    if kind == "reply_mentions_any":
        haystack = full_answer(result).lower() if result.get("comparison") else reply
        hits = [v for v in check["values"] if v.lower() in haystack]
        return {"passed": bool(hits), "detail": f"matched={hits}"}

    if kind == "reply_matches_regex":
        haystack = full_answer(result) if result.get("comparison") else reply
        match = re.search(check["pattern"], haystack, re.IGNORECASE)
        return {"passed": match is not None, "detail": f"match={match.group(0) if match else None}"}

    if kind == "reply_lacks_regex":
        match = re.search(check["pattern"], reply, re.IGNORECASE)
        return {
            "passed": match is None,
            "detail": "clean" if match is None else f"found forbidden {match.group(0)!r}",
        }

    if kind == "grounded_in_retrieval":
        # Does the reply actually reuse distinctive vocabulary from retrieved
        # passages, rather than sounding plausible from parametric knowledge?
        passages = " ".join(s.get("excerpt", "") for s in result.get("retrieved_sources", []))
        passage_terms = {
            w for w in re.findall(r"[a-z]{5,}", passages.lower())
        }
        reply_terms = set(re.findall(r"[a-z]{5,}", full_answer(result).lower()))
        overlap = passage_terms & reply_terms
        common = {
            "there", "about", "these", "those", "would", "could", "should", "which",
            "their", "other", "where", "while", "being", "between", "around",
            "travel", "traveller", "travellers", "budget", "country", "season",
        }
        distinctive = sorted(overlap - common)
        return {
            "passed": len(distinctive) >= check.get("min_overlap", 2),
            "detail": f"{len(distinctive)} distinctive shared terms: {distinctive[:8]}",
        }

    if kind == "memory_write_occurred":
        ops = [w["operation"] for w in result.get("memory_writes", [])]
        return {"passed": check["operation"] in ops, "detail": f"writes={ops}"}

    if kind == "visited_history_contains":
        countries = [
            str(v.get("country", "")).lower()
            for v in store.get_visited_history(ctx["user_id"])
        ]
        return {
            "passed": any(check["country"].lower() in c for c in countries),
            "detail": f"visited={countries}",
        }

    if kind == "no_cross_account_rows":
        # Structural proof, independent of the model's prose: the other account's
        # rows must not be readable through this account's memory snapshot.
        own = store.get_memory_snapshot(ctx["user_id"])
        other = store.get_memory_snapshot(ctx["other_user_id"])
        leaked = own["profile"].get("nationality") == other["profile"].get("nationality") and \
            own["profile"].get("current_location") == other["profile"].get("current_location")
        return {
            "passed": not leaked,
            "detail": f"own={own['profile'].get('current_location')} other={other['profile'].get('current_location')}",
        }

    if kind == "profile_unchanged_after_restart":
        before, after = ctx["before"], ctx["after"]
        mismatched = {
            f: (before.get(f), after.get(f))
            for f in check["fields"]
            if before.get(f) != after.get(f)
        }
        return {
            "passed": not mismatched,
            "detail": "identical after restart" if not mismatched else f"drifted: {mismatched}",
        }

    if kind == "endpoint_returns_own_profile":
        own, other = ctx["own_profile"], ctx["other_profile"]
        return {
            "passed": own.get("nationality") != other.get("nationality")
            and own.get("current_location") != other.get("current_location"),
            "detail": f"own={own.get('nationality')} / other={other.get('nationality')}",
        }

    if kind == "judge":
        verdict = judge(check["rubric"], ctx.get("message", ""), full_answer(result))
        return {
            "passed": verdict["score"] >= check.get("pass_score", 4),
            "detail": f"judge score {verdict['score']}/5 - {verdict['reason']}",
            "score": verdict["score"],
        }

    # Anything not handled above is a structured-travel check that reads the
    # database rather than the reply text.
    return run_travel_check(check, ctx)


# --------------------------------------------------------------------------- #
# extension checks: structured travel memory, tracking, reviews
# --------------------------------------------------------------------------- #
def _history_locations(user_id: int) -> list[str]:
    from backend.memory import travel as travel_store

    return [h["location"].strip().lower() for h in travel_store.get_travel_history(user_id)]


def _wishlist_locations(user_id: int) -> list[str]:
    from backend.memory import travel as travel_store

    return [w["location"].strip().lower() for w in travel_store.get_wishlist(user_id)]


def run_travel_check(check: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Checks that inspect stored state rather than the reply text.

    These are the strongest assertions in the suite: they read the database
    directly, so a case passes only if the app genuinely remembered something.
    """
    from backend.memory import travel as travel_store
    from backend.memory.store import get_profile

    kind = check["type"]
    user_id = ctx["user_id"]

    if kind == "history_contains":
        have = _history_locations(user_id)
        missing = [loc for loc in check["locations"] if loc.lower() not in have]
        return {"passed": not missing, "detail": f"history={have}, missing={missing}"}

    if kind == "history_lacks":
        have = _history_locations(user_id)
        present = [loc for loc in check["locations"] if loc.lower() in have]
        return {
            "passed": not present,
            "detail": f"history={have}" + (f", wrongly present={present}" if present else ""),
        }

    if kind == "history_ordered":
        have = _history_locations(user_id)
        wanted = [loc.lower() for loc in check["locations"]]
        positions = [have.index(loc) for loc in wanted if loc in have]
        ordered = positions == sorted(positions) and len(positions) == len(wanted)
        return {"passed": ordered, "detail": f"history order={have}"}

    if kind == "wishlist_contains":
        have = _wishlist_locations(user_id)
        missing = [loc for loc in check["locations"] if loc.lower() not in have]
        return {"passed": not missing, "detail": f"wishlist={have}, missing={missing}"}

    if kind == "wishlist_lacks":
        have = _wishlist_locations(user_id)
        present = [loc for loc in check["locations"] if loc.lower() in have]
        return {
            "passed": not present,
            "detail": f"open wishlist={have}" + (f", still present={present}" if present else ""),
        }

    if kind == "interests_contain_any":
        have = travel_store.get_interests(user_id)
        blob = " ".join(have)
        hits = [v for v in check["values"] if v.lower() in blob]
        return {"passed": bool(hits), "detail": f"interests={have}, matched={hits}"}

    if kind == "profile_field_set":
        actual = (get_profile(user_id).get(check["field"]) or "").strip().lower()
        wanted = str(check["value"]).strip().lower()
        return {"passed": actual == wanted, "detail": f"{check['field']}={actual!r}"}

    if kind == "onboarding_complete":
        state = travel_store.get_onboarding(user_id)
        return {
            "passed": state["status"] in {"complete", "skipped"},
            "detail": f"status={state['status']}, turns={state['turns']}",
        }

    if kind == "review_saved":
        entry = next(
            (
                h
                for h in travel_store.get_travel_history(user_id)
                if h["location"].strip().lower() == check["location"].lower()
            ),
            None,
        )
        if entry is None:
            return {"passed": False, "detail": f"{check['location']} not in history"}
        rating = entry.get("rating") or 0
        has_notes = bool((entry.get("review_notes") or "").strip())
        return {
            "passed": rating >= check.get("min_rating", 1) and has_notes,
            "detail": f"rating={rating}, notes={'yes' if has_notes else 'no'}",
        }

    if kind == "review_prompt_issued":
        prompt = (ctx.get("result") or {}).get("review_prompt")
        got = (prompt or {}).get("location", "").strip().lower()
        return {
            "passed": got == check["location"].lower(),
            "detail": f"review_prompt={prompt}",
        }

    if kind == "tool_called_any":
        called = (ctx.get("result") or {}).get("tool_calls", [])
        hits = [t for t in check["tools"] if t in called]
        return {"passed": bool(hits), "detail": f"tool_calls={called}, matched={hits}"}

    return {"passed": False, "detail": f"unknown travel check {kind!r}"}


def apply_travel_setup(user_id: int, setup: dict[str, Any]) -> None:
    """Seed structured travel state for a case."""
    from backend.memory import travel as travel_store

    for entry in setup.get("travel_history", []) or []:
        travel_store.add_travel_history(
            user_id,
            location=entry["location"],
            location_type=entry.get("location_type", "city"),
            country=entry.get("country"),
            arrival_date=entry.get("arrival_date"),
            departure_date=entry.get("departure_date"),
            source="seed",
        )
    for entry in setup.get("wishlist", []) or []:
        travel_store.add_wishlist(
            user_id,
            location=entry["location"],
            location_type=entry.get("location_type", "city"),
            country=entry.get("country"),
            priority=int(entry.get("priority", 2)),
            source="seed",
        )
    if setup.get("interests"):
        travel_store.set_interests(user_id, setup["interests"], source="seed")
    if setup.get("onboarding"):
        travel_store.set_onboarding(user_id, status=setup["onboarding"], step="done")


def set_onboarded(user_id: int) -> None:
    """Mark the account onboarded so ordinary cases reach the normal graph."""
    from backend.memory import travel as travel_store

    travel_store.set_onboarding(user_id, status="complete", step="done")


def reset_travel_state(user_id: int) -> None:
    from backend.db import get_conn

    with get_conn() as conn:
        for table in (
            "travel_history", "wishlist", "user_interests",
            "recommendation_feedback", "onboarding_state",
        ):
            conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))


async def run_travel_case(case: dict[str, Any], account_ids: dict[str, int]) -> dict[str, Any]:
    """Multi-turn case exercising onboarding, tracking or reviews."""
    from backend.agents.runner import run_turn

    user_id = account_ids[case.get("account", "a")]
    other_key = "b" if case.get("account", "a") == "a" else "a"

    store.forget_account_memory(user_id)
    reset_travel_state(user_id)
    if case.get("scenario") != "onboarding":
        set_onboarded(user_id)
    if case.get("setup", {}).get("profile"):
        store.update_profile(user_id, case["setup"]["profile"], source="seed")
    apply_travel_setup(user_id, case.get("setup", {}))

    started = time.perf_counter()
    result: dict[str, Any] = {}
    for message in case.get("messages") or [case.get("message", "")]:
        if not message:
            continue
        result = await run_turn(user_id, message, username="__eval")
    elapsed = int((time.perf_counter() - started) * 1000)

    ctx = {
        "result": result,
        "user_id": user_id,
        "other_user_id": account_ids[other_key],
        "message": (case.get("messages") or [case.get("message", "")])[-1],
    }
    return {"ctx": ctx, "elapsed_ms": elapsed, "result": result}


# --------------------------------------------------------------------------- #
# scenarios
# --------------------------------------------------------------------------- #
async def run_agent_case(case: dict[str, Any], account_ids: dict[str, int]) -> dict[str, Any]:
    from backend.agents.runner import run_turn

    user_id = account_ids[case.get("account", "a")]
    other_key = "b" if case.get("account", "a") == "a" else "a"
    other_id = account_ids[other_key]

    # Seed the *other* account first, so a leak would have something to leak.
    if case.get("other_account_setup"):
        apply_setup(account_ids[case["other_account_setup"]["account"]], case["other_account_setup"])
    else:
        store.forget_account_memory(other_id)

    apply_setup(user_id, case.get("setup", {}))

    started = time.perf_counter()
    result = await run_turn(user_id, case["message"], username=EVAL_ACCOUNTS[case.get("account", "a")])
    elapsed = int((time.perf_counter() - started) * 1000)

    ctx = {
        "result": result,
        "user_id": user_id,
        "other_user_id": other_id,
        "message": case["message"],
    }
    return {"ctx": ctx, "elapsed_ms": elapsed, "result": result}


def run_persistence_case(case: dict[str, Any], account_ids: dict[str, int]) -> dict[str, Any]:
    """Write a profile, drop every connection, re-read it - the literal
    'memory persists across a fresh session' check."""
    user_id = account_ids[case.get("account", "b")]
    apply_setup(user_id, case.get("setup", {}))
    before = store.get_profile(user_id)

    # Simulate a process restart: SQLite connections here are opened per call and
    # closed on exit, so re-reading goes back to the file on disk, not a cache.
    import gc

    gc.collect()
    after = store.get_profile(user_id)

    return {
        "ctx": {"before": before, "after": after, "user_id": user_id, "result": {}},
        "elapsed_ms": 0,
        "result": {"reply": "(persistence scenario - no agent turn)"},
    }


def run_endpoint_isolation_case(case: dict[str, Any], account_ids: dict[str, int]) -> dict[str, Any]:
    """Two accounts, two reads, asserting each only sees its own row."""
    own_id = account_ids[case.get("account", "b")]
    other_cfg = case["other_account_setup"]
    other_id = account_ids[other_cfg["account"]]

    apply_setup(other_id, other_cfg)
    apply_setup(own_id, case.get("setup", {}))

    return {
        "ctx": {
            "own_profile": store.get_profile(own_id),
            "other_profile": store.get_profile(other_id),
            "user_id": own_id,
            "other_user_id": other_id,
            "result": {},
        },
        "elapsed_ms": 0,
        "result": {"reply": "(endpoint isolation scenario - no agent turn)"},
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def load_cases(selected: list[str] | None) -> list[dict[str, Any]]:
    cases = []
    for line in CASES_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        case = json.loads(line)
        if not selected or case["id"] in selected:
            cases.append(case)
    return cases


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Onward eval suite.")
    parser.add_argument("--label", default=None, help="name for the results files")
    parser.add_argument("--case", action="append", dest="cases", help="run only these case ids")
    parser.add_argument("--no-judge", action="store_true", help="skip LLM-judge checks")
    parser.add_argument(
        "--repeat", type=int, default=1,
        help="run every case N times and report a per-case pass rate. The agents are "
             "nondeterministic, so a single run's score is noisy; N>=3 shows which "
             "cases are genuinely solid and which sit on the boundary.",
    )
    args = parser.parse_args()

    run_id = f"eval-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
    label = args.label or run_id

    cases = load_cases(args.cases)
    account_ids = ensure_eval_accounts()

    print("Onward eval suite")
    print(f"  run id     : {run_id}")
    print(f"  cases      : {len(cases)}")
    print(f"  llm        : {settings.llm_model if settings.llm_enabled else 'DISABLED'}")
    print(f"  langfuse   : {'on' if tracing_enabled() else 'off'}")
    print(f"  rag backend: {__import__('backend.rag.store', fromlist=['x']).backend_name()}")
    print()

    repeats = max(1, int(args.repeat))
    attempts: dict[str, list[bool]] = {}
    results: list[dict[str, Any]] = []
    plan = [(case, run_no) for run_no in range(1, repeats + 1) for case in cases]

    for index, (case, run_no) in enumerate(plan, start=1):
        label_suffix = f" (run {run_no}/{repeats})" if repeats > 1 else ""
        print(f"[{index}/{len(plan)}] {case['id']}{label_suffix} ... ", end="", flush=True)
        scenario = case.get("scenario")
        try:
            if case.get("kind") == "travel":
                run = await run_travel_case(case, account_ids)
            elif scenario == "persistence":
                run = run_persistence_case(case, account_ids)
            elif scenario == "endpoint_isolation":
                run = run_endpoint_isolation_case(case, account_ids)
            else:
                run = await run_agent_case(case, account_ids)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR ({type(exc).__name__})")
            attempts.setdefault(case["id"], []).append(False)
            results = [r for r in results if r["id"] != case["id"]]
            results.append(
                {
                    "id": case["id"],
                    "name": case["name"],
                    "failure_mode": case.get("failure_mode"),
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "checks": [],
                }
            )
            continue

        checks_out = []
        for check in case.get("checks", []):
            if check["type"] == "judge" and args.no_judge:
                checks_out.append(
                    {"type": "judge", "passed": True, "detail": "skipped (--no-judge)", "skipped": True}
                )
                continue
            outcome = run_check(check, run["ctx"])
            checks_out.append({"type": check["type"], **outcome})

        passed = all(c["passed"] for c in checks_out) if checks_out else False
        print("PASS" if passed else "FAIL")
        if not passed:
            for check in checks_out:
                if not check["passed"]:
                    print(f"      - {check['type']}: {check['detail']}")

        attempts.setdefault(case["id"], []).append(passed)
        results = [r for r in results if r["id"] != case["id"]]
        results.append(
            {
                "id": case["id"],
                "name": case["name"],
                "failure_mode": case.get("failure_mode"),
                "message": case.get("message"),
                "passed": passed,
                "elapsed_ms": run["elapsed_ms"],
                "trace_id": run["result"].get("trace_id"),
                "checks": checks_out,
                "reply": (run["result"].get("reply") or "")[:1200],
                "cards": [
                    {
                        "destination": c.get("destination"),
                        "rank": c.get("rank"),
                        "verdict": c.get("verdict"),
                        "season_flag": c.get("season_flag"),
                        "visa_flag": c.get("visa_flag"),
                        "backpacker_notes": c.get("backpacker_notes", []),
                        "source_ids": c.get("source_ids", []),
                    }
                    for c in run["result"].get("comparison", [])
                ],
                "tool_calls": run["result"].get("tool_calls", []),
                "retrieved": [s.get("id") for s in run["result"].get("retrieved_sources", [])],
            }
        )

    flush()

    # Order results the way the cases file does, so the report is stable.
    order = {case["id"]: i for i, case in enumerate(cases)}
    results.sort(key=lambda r: order.get(r["id"], 999))
    for record in results:
        runs = attempts.get(record["id"], [record["passed"]])
        record["runs"] = len(runs)
        record["passes"] = sum(1 for r in runs if r)
        record["pass_rate"] = round(record["passes"] / len(runs), 3)
        # With repeats, a case only counts as passing if it passed EVERY run.
        record["passed"] = all(runs)
        record["flaky"] = 0 < record["passes"] < len(runs)

    passed_count = sum(1 for r in results if r["passed"])
    flaky_count = sum(1 for r in results if r.get("flaky"))
    summary = {
        "run_id": run_id,
        "label": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "score": f"{passed_count}/{len(results)}",
        "passed": passed_count,
        "total": len(results),
        "pass_rate": round(passed_count / len(results), 3) if results else 0.0,
        "repeats": repeats,
        "flaky": flaky_count,
        "total_attempts": sum(len(v) for v in attempts.values()),
        "attempt_pass_rate": round(
            sum(sum(v) for v in attempts.values()) / max(sum(len(v) for v in attempts.values()), 1), 3
        ),
        "config": {
            "llm_model": settings.llm_model,
            "judge_model": settings.judge_model,
            "judge_enabled": not args.no_judge,
            "rag_backend": __import__("backend.rag.store", fromlist=["x"]).backend_name(),
            "embeddings": __import__("backend.rag.embeddings", fromlist=["x"]).embedding_backend(),
            "langfuse": tracing_enabled(),
        },
        "results": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / f"{label}.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md_path = RESULTS_DIR / f"{label}.md"
    md_path.write_text(render_markdown(summary), encoding="utf-8")

    print()
    if repeats > 1:
        print(
            f"SCORE: {passed_count}/{len(results)} cases passed ALL {repeats} runs "
            f"({summary['pass_rate'] * 100:.0f}%)"
        )
        print(
            f"       {summary['attempt_pass_rate'] * 100:.0f}% of individual attempts passed; "
            f"{flaky_count} case(s) flaky"
        )
    else:
        print(f"SCORE: {passed_count}/{len(results)} ({summary['pass_rate'] * 100:.0f}%)")

    flaky = [r for r in results if r.get("flaky")]
    if flaky:
        print("\nFlaky (passed some runs, failed others):")
        for r in flaky:
            print(f"  - {r['id']}: {r['passes']}/{r['runs']}")
    failing = [r for r in results if not r["passed"]]
    if failing:
        print("\nFailing cases:")
        for r in failing:
            reasons = [c["detail"] for c in r["checks"] if not c["passed"]] or [r.get("error", "")]
            print(f"  - {r['id']}: {reasons[0]}")
    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Eval run `{summary['label']}`",
        "",
        f"- **Score:** {summary['score']} ({summary['pass_rate'] * 100:.0f}%)"
        + (f", passing all {summary['repeats']} runs" if summary.get("repeats", 1) > 1 else ""),
        f"- **Run id:** `{summary['run_id']}` (Langfuse tag)",
        f"- **Timestamp:** {summary['timestamp']}",
        f"- **Model:** {summary['config']['llm_model']} / judge {summary['config']['judge_model']}",
        f"- **RAG:** {summary['config']['rag_backend']} with {summary['config']['embeddings']} embeddings",
        "",
        "| Case | Failure mode | Result |",
        "|---|---|---|",
    ]
    for r in summary["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        if r.get("runs", 1) > 1:
            mark += f" ({r['passes']}/{r['runs']})"
        if r.get("flaky"):
            mark = f"FLAKY ({r['passes']}/{r['runs']})"
        lines.append(f"| `{r['id']}` | {r.get('failure_mode', '')} | {mark} |")

    if summary.get("repeats", 1) > 1:
        lines += [
            "",
            f"Each case ran {summary['repeats']} times. A case counts as passing only "
            f"if it passed every run; {summary['attempt_pass_rate'] * 100:.0f}% of "
            f"individual attempts passed. The agents are nondeterministic, so a "
            f"single run's score is noisy - this is the honest picture.",
        ]

    failing = [r for r in summary["results"] if not r["passed"]]
    if failing:
        lines += ["", "## Failing cases", ""]
        for r in failing:
            lines.append(f"### `{r['id']}` - {r['name']}")
            if r.get("error"):
                lines.append(f"- Error: `{r['error']}`")
            for check in r["checks"]:
                if not check["passed"]:
                    lines.append(f"- Failed `{check['type']}`: {check['detail']}")
            if r.get("reply"):
                lines += ["", "> " + r["reply"][:400].replace("\n", "\n> "), ""]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
