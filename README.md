# Onward — a multi-agent travel assistant for long-term backpackers

Onward answers the one question every long-term backpacker asks over and over:
**where do I go next?** It weighs season, visas, routes and cost against the
traveller's own stored preferences, and returns a ranked comparison with pros,
cons and a verdict per destination.

---

> **Extension:** onboarding profile capture, live trip tracking, post-visit
> reviews and Google Places-backed recommendations are documented separately in
> [docs/EXTENSION.md](docs/EXTENSION.md). This README covers the core app.

## 1. The problem

Backpackers moving through a region face the "where next" decision constantly,
and it is genuinely hard because the inputs are unrelated to each other:

- **Season.** Is it monsoon there? The Perhentians shut November to February.
  Trekking Nepal in July is miserable and in places dangerous.
- **Visas.** Nationality-dependent, and some have lead times that rule a plan out
  entirely — a Vietnamese e-visa takes 3–5 working days, which is useless if your
  current visa expires on Thursday.
- **Logistics.** Overland or fly? Hanoi to Luang Prabang is 24 hours by bus or one
  hour by plane, and the bus is not always the cheaper choice once you price the
  lost day.
- **Money and taste.** Is it worth it on a shoestring, at their pace, for what
  they actually like doing?

Answering that means checking four unrelated things and then trading them off.
Onward does exactly that: four specialist agents, then a fifth that weighs their
findings against the traveller's stored profile.

The advice is deliberately **backpacker-shaped, not tourist-shaped** — dorm
prices, night buses, slow boats, free things to do, scams, and the ethical
warnings hostels actually pass around, rather than a list of landmarks.

---

## 2. Architecture

```
                       POST /chat  (authenticated)
                                │
                    ┌───────────▼────────────┐
                    │  read memory (SQLite)  │  get_memory_snapshot(user_id)
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
                    │      turn_parser       │  ADK LlmAgent
                    └───────────┬────────────┘
                                │  profile_updates, departures, candidates
                    ┌───────────▼────────────┐
                    │  EXPLICIT memory write │  store.update_profile(...)
                    │   (plain Python call)  │  store.log_departure(...)
                    └───────────┬────────────┘
                                │  re-read, so specialists see what we just learned
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │      run concurrently
┌───────▼───────┐   ┌───────────▼─────────┐   ┌─────────▼────────┐
│ weather_agent │   │  logistics_agent    │   │ recommendations  │
│               │   │                     │   │     _agent       │
│ tools:        │   │ tools:              │   │ tools:           │
│  seasonal     │   │  visa RAG search    │   │  tips RAG search │
│  conditions   │   │  route lookup       │   │                  │
└───────┬───────┘   └───────────┬─────────┘   └─────────┬────────┘
        └───────────────────────┼───────────────────────┘
                                │  three reports + code-computed guards
                    ┌───────────▼────────────┐
                    │   decision_weigher     │  ranks vs stored preferences
                    └───────────┬────────────┘
                                │
                     reply + comparison cards
```

Built on **Google ADK** (`LlmAgent`, `FunctionTool`, `Runner`, `InMemorySessionService`),
with **OpenAI** models reached through ADK's `LiteLlm` bridge.

The extension adds four more agents on the same pattern - an onboarding pair
(extractor plus conversationalist), a local guide for on-the-ground questions,
and a discovery agent for town-level "where next". A turn is routed to one of
them by intent. See [docs/EXTENSION.md](docs/EXTENSION.md).

### Two guards computed in code, not prompted for

Both were added because the eval suite caught the model getting them wrong.
They run in Python before the Decision-Weigher and are injected into its prompt
as non-negotiable blocks:

- **Coverage guard** (`backend/agents/coverage.py`). Candidate destinations are
  checked against the climate table and the RAG corpus. Anything outside both is
  named as unsupported, and the weigher may not rank it first or state specifics
  for it. This stopped the assistant inventing visa rules for Mongolia.
- **Deadline guard** (same module). If the profile holds a visa or permit expiry,
  the date is injected with an instruction to state it explicitly and check every
  option against it.

### Why not `ParallelAgent`

The fan-out originally used ADK's `ParallelAgent` inside a `SequentialAgent`.
That intermittently raised `aclose(): asynchronous generator is already running`
during teardown, which **aborted the whole turn** and returned zero comparison
cards — the eval case `rag-cites-source` caught it twice. The orchestrator now
runs each specialist in its own `Runner` under `asyncio.gather`. That is still a
genuine parallel fan-out, and it additionally isolates failures: one specialist
erroring no longer takes the other two, or the final answer, down with it. Each
specialist also gets one retry.

---

## 3. Memory

A standalone, inspectable module (`backend/memory/store.py`) — not conversation
history replayed into a prompt. The five syllabus questions each map to named
functions.

### What we keep

Two deliberately separate tables, so "active context" and "historical log" are
distinct things:

| Table | Role |
|---|---|
| `trip_profile` | **Active context**, one row per account: nationality, budget band, travel style, climate preference, current location, trip dates, visa deadline, interests. |
| `visited_history` | **Append-only log**: country, arrival/departure dates, notes. |
| `conversation_turns` | Chat scrollback, capped at `WORKING_MEMORY_TURNS` (default 20). |
| `memory_writes` | Audit trail of every write, with its source (`agent`, `user_edit`, `seed`). |

The extension adds `travel_history`, `wishlist`, `user_interests`,
`recommendation_feedback` and `onboarding_state`, which hold the route at town
granularity with post-visit reviews attached. `visited_history` is still
maintained and its rows are migrated across on boot.

### When we write

Writes are **explicit Python calls the orchestrator makes** after parsing the
turn — `backend/agents/runner.py`, function `_apply_memory_writes`. They are not
a side effect buried in a prompt. The same functions back the My Preferences
screen via `PATCH /profile/me`, with `source` distinguishing an agent-inferred
write from a user's own edit. Every call lands in `memory_writes`, which the UI
displays, so the write path is demoable rather than asserted.

### Where it lives

A SQLite file on the Railway volume. Set `DATA_DIR=/data` with a volume mounted
at `/data`; the database is `/data/onward.sqlite3`. Locally it defaults to
`./data/onward.sqlite3` (git-ignored).

**This was verified, not assumed.** Profile written, server process killed,
new process started on a different port against the same volume, profile re-read
identical including its `updated_at` timestamp, and a fresh login still returned
it. The same property is asserted in `tests/` and by the eval case
`memory-persists-fresh-session`.

Note the contrast with the RAG store: Pinecone is a managed service and lives
outside the container entirely, so it is unaffected by redeploys either way.

### How we retrieve

`get_memory_snapshot(user_id)` runs at the top of every turn and hydrates the
orchestrator and all specialists, so the traveller is never asked to repeat
themselves. The same call backs `GET /profile/me`, so what the chat claims to
remember and what the endpoint reports cannot drift apart — a marker can verify
memory independently of anything the model says.

### When we forget

- **Countries.** On a confirmed departure, `log_departure` appends to
  `visited_history` and `archive_country` clears `current_location`. The country
  leaves active context but stays readable in history, so a later re-entry or
  re-entry-visa question can still reach it.
- **Scrollback.** Capped at 20 turns, pruned on write.
- **Profiles.** The session-level rule is explicit: **profiles persist
  indefinitely for the life of the account.** They are the user's own data and
  there is no inactivity expiry. Forgetting is user-driven — "Forget everything"
  in My Preferences calls `DELETE /profile/me`.

### Per-account, not per-browser-session

Everything is keyed by an authenticated `user_id` taken from the signed JWT,
never from a path or query parameter the caller controls. Account A cannot
address account B's row. Two eval cases and four unit tests assert this.

---

## 4. RAG

Seed corpus: 29 curated documents covering the Southeast Asia backpacker circuit
plus Nepal and Sri Lanka, in three namespaces:

| Namespace | Contents | Read by |
|---|---|---|
| `visa` | Nationality-aware entry rules, costs, durations, lead times, border scams | Logistics agent |
| `seasonal` | Monsoon windows, hazard seasons, coast-by-coast splits | Weather agent |
| `tips` | Dorm prices, daily budgets, routes, free things to do, safety warnings | Recommendations agent |

Each agent searches only its own namespace, scoped by destination metadata, so
nobody searches the whole index. Embeddings are OpenAI `text-embedding-3-small`.

Ingest with `python -m scripts.ingest_rag` (or `--stats` to inspect the index).

> **A scoped search that matches nothing returns nothing.** An earlier version
> retried unscoped, which handed the agent passages about entirely different
> countries and led directly to confabulation. That fallback was removed.

---

## 5. Stack

| Layer | Choice |
|---|---|
| Frontend | Vue 3 + Vite, plain CSS, no component library |
| Backend | FastAPI, served by uvicorn |
| Agents | Google ADK 1.20 (`LlmAgent`, `FunctionTool`, `Runner`) |
| LLM | OpenAI `gpt-4o-mini` via ADK's `LiteLlm` |
| Memory | SQLite on a Railway volume |
| RAG | Pinecone (serverless) + `text-embedding-3-small` |
| Tracing | Langfuse |
| Places | Google Places API (New), Bayesian-ranked, SQLite-cached |
| Auth | `passlib` bcrypt hashing, JWT via `python-jose` |
| Hosting | Railway, one service serving API and frontend |

### API

| Endpoint | Purpose |
|---|---|
| `POST /auth/register` | Create a `pending` account (bcrypt-hashed password) |
| `POST /auth/login` | Log in an `approved` account, returns a JWT |
| `POST /admin/login` | Admin auth against `ADMIN_PASSWORD` |
| `GET /admin/pending`, `GET /admin/users` | Account roster (admin only) |
| `POST /admin/approve/{id}`, `POST /admin/reject/{id}` | Approve/reject |
| `POST /chat` | Run the agent graph against the caller's own memory |
| `GET /profile/me` | The caller's trip profile, history and recent writes |
| `PATCH /profile/me` | Direct preference editing |
| `POST /profile/me/departures` | Log a departure |
| `DELETE /profile/me` | Forget this account's memory |
| `GET /health` | Honest per-dependency status |

---

## 6. What is real and what is a fallback

Stated plainly, because the difference matters when marking this.

**Simplifications I chose deliberately:**

- **Weather is a curated seasonal table, not a live weather API**
  (`backend/agents/climate.py`). The question is "should I go to Laos in July",
  asked weeks or months ahead. A forecast API covers ~14 days and cannot answer
  it. Season boundaries are stable year to year, so a table gives a better and
  far more testable answer. **The cost:** it cannot know about an anomalous year
  or a specific storm, and the agent prompt says so.
- **Routes are curated indicative figures, not a live flight/bus search**
  (`backend/agents/routes.py`). Live aggregator APIs are not openly available,
  and a live price is the wrong answer to a question asked weeks ahead. Figures
  are presented as ranges.

**Every managed service is live and verified.** `GET /health` always reports
which path each dependency is on, so this is checkable rather than a claim:

- **Pinecone — live.** 29 documents ingested into the `ai-bootcamp` index
  (1536-dim, cosine) across the `visa`, `seasonal` and `tips` namespaces.
  Namespace isolation means pre-existing vectors in the default namespace are
  untouched. Metadata-filtered retrieval verified against the live index, and a
  scoped query for an off-corpus destination correctly returns nothing.
- **Langfuse — live.** Verified with `auth_check()` and by reading a trace back
  through the API: one trace per turn carrying user id, session id, tags, input
  and output, and an 18-span tree of agent and tool spans (see below).
- **A local fallback still exists for both**, so the app, the tests and the eval
  suite run with no managed services and no keys: a local JSON index with
  brute-force cosine search, and no-op tracing. `backend_name()` and
  `tracing_enabled()` report which path is live.
- **OpenAI.** If unset, memory still reads and writes normally and the app says
  the model is unavailable rather than erroring.

### The trace tree

```
TRACE onward.turn  user=19  spans=18
memory.read                         11ms
agent.turn_parser                 1857ms
memory.write                        15ms
agents.fan_out                    9872ms
   weather_agent                     7133ms
      tool.check_seasonal_conditions
      tool.check_seasonal_conditions        (one call per candidate)
      tool.search_seasonal_notes
      tool.search_seasonal_notes
   logistics_agent                   9869ms
      tool.search_visa_rules
      tool.search_visa_rules
      tool.check_route
      tool.check_route
   recommendations_agent             9319ms
      tool.search_backpacker_tips
      tool.search_backpacker_tips
agent.decision_weigher            5029ms
```

The fan-out is visible as parallelism, not just as structure: 26.3 seconds of
specialist work completed in 9.87 seconds of wall clock.

---

## 7. Evals (TRACE)

19 cases in `evals/cases.jsonl`, run by `python -m evals.run_evals`.

Scoring is **assertion-first**: did the retrieval tool actually fire, is this
destination ranked below another, did a row land in `visited_history`. Those are
facts about the run, not opinions about prose. Only four genuinely qualitative
cases use an LLM judge, each with its own rubric and pass threshold.

Covered failure modes: recommending a destination in monsoon or hazard season;
ignoring a visa deadline or lead time; giving generic tourist advice instead of
backpacker advice (asserted on retrieval actually firing, not on plausible-
sounding text); failing to use the stored profile; cross-account leakage; and
memory surviving a fresh session.

### Result: 14/19 → 19/19

| Run | Score | RAG / tracing | Artifact |
|---|---|---|---|
| Baseline | **14/19** | local index, no tracing | `evals/results/baseline-before-fix.json` / `.md` |
| After fixes | **19/19** | local index, no tracing | `evals/results/after-fix.json` / `.md` |
| After fixes, live services | **19/19** | **Pinecone + Langfuse** | `evals/results/after-fix-pinecone-langfuse.json` / `.md` |

The third run re-ran the same suite against the real managed services after the
keys were supplied, confirming the fixes hold on Pinecone retrieval rather than
only on the local fallback.

### The four fixes shipped from those failures

**1. The synthesis step was throwing away the specialists' work.**
The three specialists retrieved correctly every time — right passages, right
tools — but the Decision-Weigher compressed everything into 3–6 generic
sentences. It said "lower visa costs" where the retrieved passage said "USD 30
on arrival, 30 days". Three cases failed on this. Fixed by rewriting the
weigher's contract: the reply must carry at least two concrete figures forward,
and each card now has a `backpacker_notes` field required to cover a cost, a
named activity, a transport option and a warning, plus `source_ids` citing the
passages used. Those notes are rendered on the cards in the UI.
*Fixed `visa-nationality-aware`, `route-overland-vs-flight`, and half of
`rag-backpacker-not-tourist`.*

**2. Confabulation for destinations outside the knowledge base.**
Asked about Mongolia and Uzbekistan, the assistant invented visa requirements and
budgets and ranked Mongolia first. Two causes: the retrieval layer was falling
back to an unscoped search and returning passages about other countries, and
nothing stopped the weigher ranking an unsupported destination. Fixed by removing
the unscoped fallback and adding the code-computed coverage guard.
*Fixed `honesty-unknown-destination`.*

**3. A crash that silently cost the user their whole comparison.**
`rag-cites-source` errored with `aclose(): asynchronous generator is already
running` from ADK's `ParallelAgent`, returning zero cards. Fixed by replacing it
with `asyncio.gather` over per-specialist Runners, adding per-specialist error
isolation and a retry.
*Fixed `rag-cites-source`.*

**4. A real bug in the climate table: `StopIteration` on May.**
`assess()` recovered the month name by searching for a key longer than three
characters — which finds nothing for May, whose full name *is* three letters.
Every May query killed the Weather specialist with
`coroutine raised StopIteration`. Found only because error isolation from fix 3
surfaced it instead of swallowing it. One-line fix, indexing a canonical list.

**Honest caveat on the before/after comparison.** Between the two runs, two
checks (`grounded_in_retrieval` and the judge prompts) changed scope from reading
only the prose reply to reading the full user-visible answer including the
comparison cards — because the cards are the product's primary output and a
grounding check that ignores them measures the wrong thing. That scope change
affects `rag-cites-source` and `rag-backpacker-not-tourist`. The other three
recovered cases are pure assertion checks whose definitions did not change, and
fixes 2, 3 and 4 are code-level fixes verifiable independently of the eval
wording.

**Langfuse traceability.** Every run gets a `run_id` recorded in the results file
and attached to traces as a tag, so a failing case can be opened in Langfuse. The
live run's id is `eval-20260911T165850Z-2493bc`.

### Running them

```bash
python -m evals.run_evals                      # full suite
python -m evals.run_evals --label before-fix   # name the output files
python -m evals.run_evals --case season-nepal-monsoon
python -m evals.run_evals --no-judge           # assertions only, no judge calls
```

Unit tests (no API keys needed, ~12s):

```bash
python -m pytest tests -q      # 21 tests: memory contract, auth, isolation
```

---

## 8. Running it locally

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows;  source .venv/bin/activate on POSIX
pip install -r requirements.txt

cp .env.example .env              # then fill in OPENAI_API_KEY and ADMIN_PASSWORD
python -m scripts.ingest_rag      # build the RAG index

cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000. For frontend hot-reload use `npm run dev` in
`frontend/` (port 5173, proxied to the backend).

> **Python version.** Pinned to `litellm==1.72.0` because 1.78+ requires Python
> 3.11 (`typing.NotRequired`). Developed and tested on Python 3.10.

---

## 9. Deploying to Railway

1. Create a service from this repo. `nixpacks.toml` installs Python and Node,
   builds the frontend, and starts uvicorn.
2. **Mount a volume at `/data`.** Without it the database is wiped on redeploy.
3. Set the service variables:

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | your key |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN_PASSWORD` | your choice — set it here, never in source |
| `DATA_DIR` | `/data` |
| `PINECONE_API_KEY`, `PINECONE_INDEX` | optional; local fallback without them |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | optional |
| `DEMO_USERNAME`, `DEMO_PASSWORD` | optional pre-approved demo account |
| `ADMIN_AUTO_APPROVE` | `true` to skip approval gating for demo day |

`scripts/bootstrap.py` runs before uvicorn on every boot: it creates the schema,
ingests the RAG corpus if the index is empty, and seeds the demo account if those
two variables are set. It is idempotent and never overwrites an existing profile.

### Demo-safety decision — needs your call

The brief asks for a pre-approved account so a marker landing cold is not blocked
waiting for you to click approve. Both mechanisms are built; **pick one before
demo day**:

- **`DEMO_USERNAME` + `DEMO_PASSWORD`** *(recommended)* — one pre-approved
  account with a seeded profile, so a marker sees a populated memory sidebar
  immediately and the approval gate still works as designed for everyone else.
- **`ADMIN_AUTO_APPROVE=true`** — anyone who registers is approved instantly.
  Simpler, but it disables the approval feature you are being marked on.

You can run both: auto-approve off, demo account on.

---

## 10. Demo script

1. **Incognito, cold.** Open the URL. Log in as the demo account.
2. **Memory is already there.** The sidebar shows nationality, budget, pace,
   dates and current location. Nothing was typed this session.
3. **Ask the question.** *"I'm in Thailand with six weeks left — Laos or
   Vietnam?"* Ranked cards appear with pros, cons, season and visa flags, and
   backpacker notes with source ids.
4. **Show what ran.** Expand "Show what ran": the specialists that fired, their
   timings, and every retrieved passage with its similarity score.
5. **Change a preference.** In My Preferences set climate preference to `cool`
   and save. Ask again — the ranking moves and the reply names the preference
   that drove it.
6. **Show the write path.** Say *"I left Laos yesterday, I'm in Thailand now."*
   The sidebar's "Just remembered" panel shows the `log_departure` write, Laos
   moves into visited history, and current location updates.
7. **Prove persistence.** Log out, close the window, reopen in a new incognito
   window, log back in. Everything is exactly as it was. Or hit `/profile/me`
   directly to see the stored JSON.
8. **Admin.** Register a second account, show it blocked pending approval, then
   approve it at `/admin`.

---

## 11. Checklist status

| Requirement | Status |
|---|---|
| Problem / product | Section 1 |
| Architecture: agents, memory, tools, APIs | Section 2 |
| Stack | Section 5 — all of it live, including Pinecone and Langfuse |
| Evals: what TRACE proved + a shipped fix | Section 7 — 14/19 → 19/19, both result files committed, four fixes |
| Memory: keep / write / lives / retrieve / forget | Section 3 — five separately implemented answers |
| URL loads for a stranger in incognito | Needs the Railway deploy; no hostname is baked into the frontend build |
| Core task works end to end | Verified locally against the live OpenAI API |
| Memory persists across a fresh session | **Verified** against a real process restart, plus tests and an eval case |
| Eval suite passes / latest score shown | 19/19 on the local fallback and 19/19 against live Pinecone + Langfuse |
| At least one fix from TRACE shipped | Four, Section 7 |
| README covers problem/architecture/stack/demo | This file |
| Backup recording exported | **Outstanding** — record once deployed |

### Outstanding before demo day

1. Deploy to Railway with a `/data` volume and verify in incognito.
2. Decide the demo-safety mechanism (Section 9).
3. Screen-record the Section 10 flow.

Pinecone and Langfuse are done — keys supplied, corpus ingested, traces verified,
and the full suite re-run green against both.
