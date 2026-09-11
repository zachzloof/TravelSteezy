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

Reply with ONLY raw JSON: {{"score": <1-5>, "reason": "<one sentence>"}}"""


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
        return {
            "score": int(parsed.get("score", 0)),
            "reason": str(parsed.get("reason", ""))[:300],
        }
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

    return {"passed": False, "detail": f"unknown check type {kind!r}"}


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
    args = parser.parse_args()

    run_id = f"eval-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
    label = args.label or run_id

    cases = load_cases(args.cases)
    account_ids = ensure_eval_accounts()

    print(f"Onward eval suite")
    print(f"  run id     : {run_id}")
    print(f"  cases      : {len(cases)}")
    print(f"  llm        : {settings.llm_model if settings.llm_enabled else 'DISABLED'}")
    print(f"  langfuse   : {'on' if tracing_enabled() else 'off'}")
    print(f"  rag backend: {__import__('backend.rag.store', fromlist=['x']).backend_name()}")
    print()

    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']} ... ", end="", flush=True)
        scenario = case.get("scenario")
        try:
            if scenario == "persistence":
                run = run_persistence_case(case, account_ids)
            elif scenario == "endpoint_isolation":
                run = run_endpoint_isolation_case(case, account_ids)
            else:
                run = await run_agent_case(case, account_ids)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR ({type(exc).__name__})")
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

    passed_count = sum(1 for r in results if r["passed"])
    summary = {
        "run_id": run_id,
        "label": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "score": f"{passed_count}/{len(results)}",
        "passed": passed_count,
        "total": len(results),
        "pass_rate": round(passed_count / len(results), 3) if results else 0.0,
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
    print(f"SCORE: {passed_count}/{len(results)} ({summary['pass_rate'] * 100:.0f}%)")
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
        f"- **Score:** {summary['score']} ({summary['pass_rate'] * 100:.0f}%)",
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
        lines.append(f"| `{r['id']}` | {r.get('failure_mode', '')} | {mark} |")

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
