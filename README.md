# Travel Steezy — a multi-agent travel assistant for long-term backpackers

Travel Steezy answers the one question every long-term backpacker asks over and over:
**where do I go next?** It weighs season, visas, routes and cost against the
traveller's own stored preferences, and returns a ranked comparison with pros,
cons and a verdict per destination.

---

> **Extension:** onboarding profile capture, live trip tracking, post-visit
> reviews and Google Places-backed recommendations are documented separately in
> [docs/EXTENSION.md](docs/EXTENSION.md). This README covers the core app.
>
> **Design notes:** [notes/](notes/00-index.md) has a deeper, file-per-topic
> record of specific bugs found, the fix, and the eval case or test that caught
> each one — agent architecture, memory/schema, RAG, Places ranking, prompt
> guards, eval methodology, known limitations, and a chronological decision
> log. Read this if you want the "why," not just the "what."

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
Travel Steezy does exactly that: four specialist agents, then a fifth that weighs their
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

The extension adds three more agents on the same pattern - a local guide for
on-the-ground questions, a discovery agent for town-level "where next", and an
onboarding extractor. A turn is routed to one of them by intent. See
[docs/EXTENSION.md](docs/EXTENSION.md).

**Onboarding is not on this path at all.** It used to hijack the first few turns
of `/chat` with a pair of agents, one of which chose what to ask next. It is now
a welcome page with a fixed set of questions and its own endpoint, and the only
model left in it turns one plain-text answer into structured fields. The
questions being data rather than a model output is what makes onboarding
testable; see [docs/EXTENSION.md](docs/EXTENSION.md) section 2.

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
| `trip_profile` | **Active context**, one row per account: budget band, travel pace, climate preference, current location, trip dates, visa deadline, interests. |
| `passports` | Every passport held, primary first. `trip_profile.nationality` mirrors the primary, so everything written against that single field still works. |
| `visited_history` | **Append-only log**: country, arrival/departure dates, notes. |
| `conversation_turns` | Chat scrollback, capped at `WORKING_MEMORY_TURNS` (default 20). |
| `memory_writes` | Audit trail of every write, with its source (`agent`, `user_edit`, `seed`). |

The extension adds `travel_history`, `wishlist`, `user_interests`,
`recommendation_feedback`, `passports` and `onboarding_state`, which hold the
route at town granularity with post-visit reviews attached. `visited_history` is
still maintained and its rows are migrated across on boot.

**Budget, pace and climate are five-point ordered scales**, not three-point sets.
Three was not enough to be useful: "hot" covered both a Thai beach in March and a
Nepali hill town in October, and a traveller on GBP 15 a day and one on GBP 45 a
day both had to answer "shoestring". Free text is mapped onto the scale in Python
by `store.normalise_band`, never by trusting a model to emit a valid token - and
a negated phrase ("I hate the heat") is inverted or dropped rather than matched
on its keyword, which is the difference between storing a preference and storing
its opposite.

**A star rating on somewhere they have been is the strongest preference signal in
the profile**, and a low one is the most informative of all. Somebody who rated
Hanoi 2/5 is telling you something about big, loud, traffic-heavy cities, not
only about Hanoi. Ratings are rendered into every prompt split into liked and
disliked, with a standing instruction to generalise from them and to say which
past rating drove a call.

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

Seed corpus: 52 curated country-level documents covering the Southeast Asia
backpacker circuit, South Asia (Nepal, Sri Lanka, India, Bhutan) and Mongolia
and Myanmar, in three namespaces:

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

The extension adds three more namespaces on top of these — `routes` (47
town-level "where next from here" documents), `experience` (written at
runtime from reviews and accepted/rejected suggestions, so recommendations
improve with use), and `unverified` (written at runtime from a live web
search + two-pass LLM synthesis/verification, only when a scoped curated
search comes back empty and `TAVILY_API_KEY` is set - see note 03) — bringing
the live index to 99 curated documents plus runtime content. See
[docs/EXTENSION.md](docs/EXTENSION.md) section 6 and
[notes/03-rag-and-retrieval.md](notes/03-rag-and-retrieval.md) for the design
and the bugs found building it.

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

The extension adds `/travel/*` — structured route, wishlist, interest, rating and
review endpoints, plus the onboarding question set and answer endpoint. Full list
in [docs/EXTENSION.md](docs/EXTENSION.md) section 8.

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

19 base-app cases in `evals/cases.jsonl`, run by `python -m evals.run_evals`.
The extension adds 16 more (8 `travel`, 8 `onboarding`) for 35 in total.

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
| Baseline | **14/19** | local index, no tracing | `evals/results/1-baseline-before-fix.json` / `.md` |
| After fixes | **19/19** | local index, no tracing | `evals/results/2-after-fix.json` / `.md` |
| After fixes, live services | **19/19** | **Pinecone + Langfuse** | `evals/results/3-after-fix-pinecone-langfuse.json` / `.md` |

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

Unit tests (no API keys needed, ~20s):

```bash
python -m pytest tests -q      # 82 tests: memory contract, auth, isolation,
                               # structured travel memory, ranking, onboarding
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

**Extension flow** (a brand-new account, so onboarding fires):

9. **Onboard.** Register a fresh account. It lands on the welcome page, not the
   chat. Answer the first question in plain English, messily and with opinions:
   *"Started in Bangkok, fine but I wouldn't rush back, 3/5. Then Koh Tao where I
   did my Open Water, loved it, easily a 5. Hanoi after that, way too loud for me,
   2 out of 5. I'm in Chiang Mai now."* The panel beside it fills in immediately
   with the ordered route and the three ratings — that echo is the point, because
   a misread is visible in the same second it happens. Then: *"British, and I've
   got an Irish passport too"*, *"Dead set on Pai, and I'd go back to Koh Tao in a
   heartbeat"*, and *"Tight budget, I like staying put for a couple of weeks, I
   melt in the heat, travelling on my own, mostly hiking and diving."*
9a. **Show what that became.** Go to My Preferences. Both passports are listed.
    Budget sits on `shoestring`, pace on `slow`, and climate on **`cool`** — not
    `hot`, even though the only weather word they typed was "heat". Koh Tao is in
    the history at 5/5 *and* on the wishlist as "going back".
9b. **Show it is not a one-way door.** Change a star rating in the history panel;
    it saves on the tap.
10. **Discover, then track.** Ask *"Where next from here?"* — it prioritises
    Pai because it's on the wishlist, citing the route corpus. Say *"I'm in Pai
    now"* — the trip panel updates live: Pai moves from wishlist to route.
11. **Live Places.** Ask *"Any good hostels here, and which area should I stay
    in?"* — real Google Places results, ranked by weighted score (not raw
    star rating), grouped into walkable areas.
12. **Review loop.** Say *"Leaving Pai today, heading back to Chiang Mai"* — a
    review prompt appears. Answer it; the review is saved and feeds back into
    the RAG store for future travellers' suggestions.

Full extension design (and every bug found building it) is in
[docs/EXTENSION.md](docs/EXTENSION.md) and [notes/](notes/00-index.md).

---

## 11. Checklist status

| Requirement | Status |
|---|---|
| Problem / product | Section 1 |
| Architecture: agents, memory, tools, APIs | Section 2, extended by [docs/EXTENSION.md](docs/EXTENSION.md) |
| Stack | Section 5 — all of it live, including Pinecone, Langfuse and Places |
| Evals: what TRACE proved + a shipped fix | Base app: Section 7, 14/19 → 19/19, four fixes. Extension: 16 more cases — six fixes, including a bug in the eval harness itself (two runs corrupting each other's data). The onboarding rework added 8 more cases which caught two real bugs on their first run, `evals/results/11-onboarding-v2.md`. All in [notes/06-eval-methodology.md](notes/06-eval-methodology.md) and [notes/08-decisions-log.md](notes/08-decisions-log.md) |
| Memory: keep / write / lives / retrieve / forget | Section 3 — five separately implemented answers, extended with structured route/wishlist/review tables, a passport list, and five-point preference scales |
| URL loads for a stranger in incognito | Needs the Railway deploy; no hostname is baked into the frontend build |
| Core task works end to end | Verified locally against the live OpenAI API, including the full onboarding → discover → track → review loop |
| Memory persists across a fresh session | **Verified** against a real process restart, plus tests and an eval case |
| Eval suite passes / latest score shown | **34/35** on the full suite after the onboarding rework (`evals/results/12-full-after-onboarding-rework.md`). The onboarding cases specifically: **9/9 passing all 3 runs, 27/27 attempts** (`evals/results/11-onboarding-v2.md`). The one failure is the judge case `rag-backpacker-not-tourist`, which an A/B isolation run showed is flaky independently of this work (3/6 without the change, 7/11 with it) — the investigation is written up in [notes/06-eval-methodology.md](notes/06-eval-methodology.md) |
| At least one fix from TRACE shipped | Twelve across three phases — four base-app (Section 7), six extension, and two from the onboarding rework's first eval run: a `set_social_style` write that silently no-opped for every brand-new account, and a dropped revisit ([notes/08-decisions-log.md](notes/08-decisions-log.md)) |
| README covers problem/architecture/stack/demo | This file, plus [docs/EXTENSION.md](docs/EXTENSION.md) and [notes/](notes/00-index.md) for depth |
| Backup recording exported | **Outstanding** — record once deployed |

### Outstanding before demo day

1. Deploy to Railway with a `/data` volume and verify in incognito.
2. Decide the demo-safety mechanism (Section 9).
3. Run `python -m scripts.ingest_rag` against the production Pinecone index to
   pick up the expanded corpus (99 curated documents total once it has - see
   [notes/03-rag-and-retrieval.md](notes/03-rag-and-retrieval.md)).
4. Screen-record the Section 10 flow, extension steps included.

Pinecone and Langfuse are done — keys supplied, corpus ingested, traces verified,
and the full suite re-run green against both.
