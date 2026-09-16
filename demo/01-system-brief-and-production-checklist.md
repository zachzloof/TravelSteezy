# Travel Steezy — System Brief & Production-Readiness Checklist

*Internal brief. Written so a stranger — a marker, a teammate picking this up cold — can understand what this is and whether it's ready to show.*

---

## 1. The problem / product

Long-term backpackers moving through a region face the same question over and
over: **where do I go next?** It's genuinely hard because the inputs don't
share a unit — season (is it monsoon there?), visas (nationality-dependent,
sometimes with a lead time that rules a plan out entirely), logistics
(overland vs. flight — is the cheaper option actually worth the lost day?),
and money/taste (is it worth it on a shoestring, at their pace, for what they
actually like doing?). Answering well means checking four unrelated things
and trading them off against a specific person's stored preferences.

Travel Steezy answers that question with **four specialist agents plus a
fifth that weighs their findings against the traveller's own memory**, and
returns a ranked comparison with pros, cons, and a verdict per destination.
The advice is deliberately backpacker-shaped, not tourist-shaped — dorm
prices, night buses, visa-run scams, free things to do — because that's the
question this traveller is actually asking.

## 2. Architecture

```
POST /chat (authenticated)
  → read memory (SQLite)                         get_memory_snapshot(user_id)
  → turn_parser (ADK LlmAgent, no tools)          → intent, profile updates, candidates
  → explicit memory write (plain Python calls)    store.update_profile(), log_departure()
  → re-read memory + compute code-side guards     coverage_note(), route_note()
  → route by intent: compare | discover | local | memory | review
       compare  → weather_agent ‖ logistics_agent ‖ recommendations_agent   (asyncio.gather, one Runner each)
                → decision_weigher (ranks vs. stored preferences)
       discover → discovery_agent  (route-graph RAG, not Places)
       local    → local_guide      (place-level tools, deliberately no visa/route tools)
       memory/review → concierge   (answers straight from the profile)
  → reply + ranked comparison cards
```

One function, `run_turn()` (`backend/agents/runner.py`), owns this pipeline —
it is not "one agent," it's parse → write → re-read → route → run. Built on
**Google ADK** (`LlmAgent`, `FunctionTool`, `Runner`) with OpenAI models
reached through ADK's `LiteLlm` bridge — proven live with every Google
credential stripped from the process.

**Two guards run in Python, not in a prompt**, before the final synthesis
step: a coverage guard (blocks the model from stating specifics for a
destination outside the RAG corpus and climate table) and a live-source
disclosure check (forces upfront disclosure whenever a card's data came from
a live web lookup rather than the curated corpus). Both exist because the
eval suite caught the model getting them wrong when they were only prompted
instructions.

**Why not ADK's `ParallelAgent`?** The first version nested one inside a
`SequentialAgent` for the specialist fan-out. It intermittently raised
`aclose(): asynchronous generator is already running` during teardown, which
silently aborted the whole turn and returned zero comparison cards — caught
twice by the eval case `rag-cites-source`. Replaced with `asyncio.gather` over
one `Runner` per specialist: still genuine concurrency (verified in Langfuse
traces — 9.87s wall clock for 26.3s of combined specialist work), plus a
property `ParallelAgent` didn't give for free: one specialist erroring no
longer takes the other two, or the final answer, down with it.

## 3. Stack and tools

| Layer | Choice |
|---|---|
| Frontend | Vue 3 + Vite, plain CSS |
| Backend | FastAPI, served by uvicorn |
| Agents | Google ADK 2.9 (`LlmAgent`, `FunctionTool`, `Runner`) |
| LLM | OpenAI via ADK's `LiteLlm` bridge — `gpt-4o-mini` for 7+ agents, `gpt-4o` for the Decision-Weigher and the eval judge only |
| Memory | SQLite on a Railway volume (`backend/memory/store.py`) |
| RAG | Pinecone 10 (serverless) + OpenAI `text-embedding-3-small`, with a local JSON/brute-force-cosine fallback when no key is set |
| Live-lookup fallback | Tavily web search + two-pass LLM synthesis/verify, gated behind `TAVILY_API_KEY`, only fires when a scoped curated search returns nothing |
| Tracing/evals harness | Langfuse 4 (OTEL), auto-instrumented via OpenInference — zero hand-rolled spans |
| Places | Google Places API (New), Bayesian-ranked, SQLite-cached |
| Auth | Direct `bcrypt` hashing + JWT (`python-jose`) |
| Host | Railway, one service serving API and frontend |

## 4. Evals (TRACE)

35 cases in `evals/cases.jsonl` (19 base app + 16 extension), run by
`python -m evals.run_evals`. Scoring is **assertion-first**: did the
retrieval tool actually fire, is this destination ranked below another, did a
row land in `visited_history` — facts about the run, read from `ToolRecorder`
and the database, not opinions about prose. Only four qualitative cases use
an LLM judge, and the judge's negative verdicts are themselves checked: a
score ≤3 requires a verbatim quote from the reply, and the harness rejects
the deduction in code if that quote doesn't actually appear in the text. This
caught a real judge fabrication mid-project (a false "you asked for budget
info again" deduction on a reply that never asked).

**What TRACE proved, headline run:** base-app suite went from **14/19 →
19/19** after four fixes (`evals/results/1-baseline-before-fix.md` →
`2-after-fix.md`), re-confirmed at 19/19 against live Pinecone + Langfuse
(`3-after-fix-pinecone-langfuse.md`). Current full-suite score, most recently
recorded: **33/35** (`evals/results/modernization-v3-final.md`, 2026-09-13) —
the two misses are a flaky judge case (`season-malaysia-east-coast-closed`)
and a strict retrieval-namespace assertion (`rag-budget-numbers`), both
tracked as known gaps rather than silently ignored. Unit tests: 103/103,
no API keys needed.

**One concrete fix shipped from a TRACE failure — with a before/after
number:** `visa-vietnam-lead-time` (respects an e-visa lead time against a
hard deadline) regressed after all three specialist agents were briefly
upgraded to `gpt-4o`. Under real load, four `gpt-4o` calls per comparison
turn reliably tripped this org's 30K-TPM rate limit — reproduced directly via
captured `RateLimitError` tracebacks. An 8-run repeat confirmed it:
**3/8 attempts passing (38%)** before the fix
(`evals/results/vietnam-regression-repeat8.md`). Fix: rolled the three
specialists back to `gpt-4o-mini` (keeping `gpt-4o` only on the one-shot
Decision-Weigher call) and added rate-limit-aware exponential backoff to the
retry loop. Re-run: **6/8 attempts passing (75%)**
(`evals/results/vietnam-postfix-repeat8.md`) — same eval case, same harness,
isolated change.

Other fixes traced the same way: the synthesis step discarding retrieved
figures (fixed by requiring ≥2 concrete figures and a `backpacker_notes`
field per card), confabulation for uncovered destinations like Mongolia
(fixed by removing an unscoped-retrieval fallback and adding the coverage
guard), and a real `StopIteration` bug in the climate table that killed every
May query (one-line fix, surfaced only because the `ParallelAgent` fix's
error isolation let the exception through instead of swallowing it).

## 5. Memory

| Question | Answer |
|---|---|
| **What we keep** | `trip_profile` (active context: budget, pace, climate preference, current location, key interests), `passports`, `visited_history`/`travel_history` (append-only route log with ratings), `conversation_turns` (capped scrollback), `memory_writes` (audit trail) |
| **When we write** | Explicit Python function calls the orchestrator makes after parsing the turn (`_apply_memory_writes`), never a model-authored side effect — the model's job ends at "here is what I heard, as JSON" |
| **Where it lives** | A SQLite file on a Railway volume (`/data/onward.sqlite3`); verified by killing the process, starting a new one on a different port against the same volume, and reading back an identical profile including its `updated_at` timestamp |
| **How we retrieve** | `get_memory_snapshot(user_id)` runs at the top of every turn and hydrates the orchestrator and every specialist — the same call backs `GET /profile/me`, so chat and the profile endpoint can't drift apart |
| **When we forget** | Countries: archived from active context on a confirmed departure but kept in history. Scrollback: capped at 20 turns. Profiles: persist indefinitely — forgetting is user-driven only (`DELETE /profile/me`) |

Everything is keyed by the authenticated `user_id` from the signed JWT, never
from a caller-controlled parameter — asserted by dedicated eval cases and
unit tests for cross-account isolation.



## 7. Backup demo — critical

**Record a short screen capture of the flow above before Demo Day.** Live
demos break (rate limits, a flaky Wi-Fi, a cold Railway container). Bring the
recording as insurance; if the live run stalls, narrate over the recording
rather than debugging in front of the room.

**Status: outstanding** — no recording exists yet in this repo. Record once
deployed (see checklist below).

## 8. Production-readiness checklist

| Item | Status | Evidence |
|---|---|---|
| URL loads for a stranger (incognito) without VPN tricks | ⚠️ **Outstanding** | Not yet deployed to Railway — no hostname is baked into the frontend build. `railway.json`/`Procfile`/`nixpacks.toml` are all in place and ready; the deploy step itself hasn't run. |
| Core task works end to end | ✅ Done | Verified locally against the live OpenAI API, including the full onboarding → discover → track → review loop (`PROGRESS.md`, README §9) |
| Memory persists across a fresh session | ✅ Done | Verified against a real process restart (kill + restart on a different port against the same SQLite file), plus `tests/test_memory_and_auth.py` and the eval case `memory-persists-fresh-session` |
| Eval suite still passes (or latest score + known gaps shown) | ✅ Done | Latest full-run score **33/35** (`evals/results/modernization-v3-final.md`), unit tests **103/103**. Known gaps: one flaky judge case (`season-malaysia-east-coast-closed`) and one strict retrieval assertion (`rag-budget-numbers`) — both named, not hidden |
| At least one fix from TRACE is shipped | ✅ Done | Multiple — headline: the Vietnam visa-lead-time rate-limit fix, 38%→75% attempt-pass rate (§4 above), plus four base-app fixes that took the suite from 14/19 to 19/19 |
| README or brief covers problem, architecture, stack, and demos | ✅ Done | `README.md` §1–11, plus `notes/00-index.md` for depth and this document |
| Backup recording exported and ready | ⚠️ **Outstanding** | Not yet recorded — do this immediately after deploying |
