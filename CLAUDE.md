# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Travel Steezy is a multi-agent travel assistant for long-term backpackers: a FastAPI
backend running a Google ADK agent graph over SQLite memory and a Pinecone RAG corpus,
with a Vue 3 SPA served from the same origin.

## Read the existing docs first

This repo is unusually well documented, and the docs are the design record — most
non-obvious code here is the fix for a specific bug that is written up somewhere:

- [README.md](README.md) — core app: architecture, agent/tool table, memory model, RAG namespaces, stack, API, evals, local run, Railway deploy.
- [docs/EXTENSION.md](docs/EXTENSION.md) — onboarding, trip tracking, reviews, Google Places tools, the `routes`/`experience` namespaces, the extra `/travel/*` endpoints.
- [notes/](notes/00-index.md) — file-per-topic "why", with the bug, the fix, and the eval case or test that caught it. `notes/00-index.md` says which file to read before touching what. In particular: read `01` and `05` before changing the agent graph or a prompt, `04` before "fixing" ranking or clustering, `06` before trusting an eval score, and `09` before adding anything that calls an LLM.

## Commands

```bash
# setup (Python 3.13 — see runtime.txt; litellm 1.100.1 needs >=3.11)
python -m venv .venv && .venv/Scripts/activate   # source .venv/bin/activate on POSIX
pip install -r requirements.txt
cp .env.example .env                              # fill OPENAI_API_KEY, ADMIN_PASSWORD
python -m scripts.ingest_rag                      # build the RAG index (--stats to inspect)

# run
cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --reload --port 8000     # http://localhost:8000
cd frontend && npm run dev                        # hot-reload frontend on :5173, proxied to :8000

# tests (no API keys, no network)
python -m pytest tests -q
python -m pytest tests/test_travel_and_places.py -q                  # one file
python -m pytest tests/test_memory_and_auth.py -k isolation -q       # one test

# evals (these DO call OpenAI and hit the real database)
python -m evals.run_evals                         # full suite (every case in evals/cases.jsonl)
python -m evals.run_evals --case season-nepal-monsoon
python -m evals.run_evals --label after-fix       # names the output files
python -m evals.run_evals --no-judge              # assertions only, skip judge calls
python -m evals.run_evals --repeat 3              # per-case pass rate; agents are nondeterministic
```

Write files with the Write/Edit tools, not a shell heredoc. A heredoc edit here once ate
every `\b` in a regex into a literal `0x08` byte, and quoting failures are easy to miss in
long content — if you do use one, grep the result for stray control bytes (`notes/03`).

`pytest` is not in `requirements.txt` — install it separately. `scripts/bootstrap.py`
(run before uvicorn in production) creates the schema, ingests the corpus if the index
is empty, and seeds the demo account; it is idempotent.

## Architecture

**One turn = one function.** `run_turn()` in [backend/agents/runner.py](backend/agents/runner.py)
is the whole orchestrator, and it is a fixed pipeline rather than an agent deciding what to
do: read memory → parse → write memory → re-read + compute guards → route by intent → run
agents. `POST /chat` is a thin wrapper over it ([backend/routers/chat.py](backend/routers/chat.py)).

Agent definitions, prompts and the shared prompt blocks all live in
[backend/agents/graph.py](backend/agents/graph.py); the agent/tool/intent table is in
README section 3. Intents are `compare | discover | local | memory | review`.

Layout:

| Path | Holds |
|---|---|
| `backend/agents/` | The orchestrator (`runner.py`), agent + prompt definitions (`graph.py`), tools (`tools.py`, `place_tools.py`, `discovery_tools.py`), code-computed guards (`coverage.py`, `climate.py`, `routes.py`), tracking and onboarding |
| `backend/memory/` | `store.py` (profile, history, audit log) and `travel.py` (structured route, wishlist, interests, reviews) |
| `backend/rag/` | Pinecone/local store, embeddings, seed corpus, route corpus, the runtime `experience` store, and the live web-search fallback |
| `backend/places/` | Google Places client, Bayesian ranking, neighbourhood clustering, affiliate links |
| `backend/routers/` | `auth`, `admin`, `profile`, `travel`, `chat`, `bugs`, `memory_debug` |
| `frontend/src/` | Vue 3 + Vite SPA, plain CSS, no component library. Views map to the router paths in `main.js` |

### Invariants that look like they could be simplified, but cannot

Each of these is load-bearing and has a documented failure behind it. Do not undo one
without reading the note it points at.

- **Memory writes are plain Python calls, never a model side effect.** The parser emits
  JSON; `_apply_memory_writes` / `tracking.apply_tracking` do the writing. Free text is
  mapped onto the five-point budget/pace/climate scales by `store.normalise_band`, never
  by trusting a model to emit a valid token. (`notes/02`)
- **A place the traveller did not type is never written.** `tracking.mentioned_in`
  grounds `visits`, `departures` and `profile_updates.current_location` in the raw
  message, and a stated presence beats a departure inferred in the same turn. The
  parser restates a location on nearly every turn, including turns naming nowhere, and
  one stale restatement overwrote a traveller's own words. The write path being Python
  does not make the extraction true. (`notes/02`, bug report #3)
- **Scope is read from the question, not from how precisely the location was stored.**
  `coverage.wants_country_scope` forces the country-level path for "which country
  next" / "change country" / "my visa is running out", whatever the classifier said,
  and a `discover` turn with no stored location goes to the tool-less concierge rather
  than to an agent that could invent an origin. (`notes/05`)
- **The Weather specialist always runs on a comparison.** `needs_weather` from the
  parser is ignored there: it came back false for "a big trek in July, Nepal or Sri
  Lanka?", no weather agent ran, and Nepal was ranked first in monsoon. (`notes/05`,
  decision 51)
- **Every agent in a turn shares one ADK session id** (`runner.adk_session_id`).
  Per-agent ids get carried onto the auto-instrumented spans and overwrite the trace's
  Langfuse session, scattering one conversation across several. Same rule in
  `onboarding.py`. (`notes/09`)
- **The `compare` fan-out is `asyncio.gather` over one `Runner` per specialist, not ADK's
  `ParallelAgent`.** `ParallelAgent` intermittently raised `aclose(): asynchronous generator
  is already running` and aborted the whole turn. Per-specialist Runners also isolate
  failures, and each gets a retry with rate-limit-aware backoff. (`notes/01`)
- **Any message naming two or more destinations is forced into `compare`**, overriding the
  classifier — `local_guide` deliberately holds no visa/route tools and once answered a
  two-country visa question from parametric memory. (`notes/05`)
- **A scoped RAG search that matches nothing returns nothing.** The unscoped retry was
  removed: it handed agents passages about unrelated countries and caused confabulation.
  The live web-search fallback (`TAVILY_API_KEY`) is the sanctioned replacement, and it
  writes its result into the namespace matching the question's kind, tagged `origin: live`. (`notes/03`)
- **Guards are computed in code and injected into the weigher's prompt as non-negotiable
  blocks**, not prompted for: `coverage_note` (a destination outside both the climate table
  and the corpus may not be ranked first or described with specifics) and `route_note`. (`notes/05`)
- **Model tiers per agent are deliberate** ([backend/config.py](backend/config.py) carries the
  full reasoning): `gpt-4o-mini` for extraction and narrow completions, `gpt-4o` for
  `decision_weigher` and the eval judge. The three specialists were moved to `gpt-4o` and
  rolled back — four `gpt-4o` calls per comparison turn tripped this org's 30K TPM limit at a
  62% failure rate. `SPECIALIST_MODEL` stays its own setting so opting back in is env-only.
- **The eval suite takes a lock** (`EvalLock`, refuses a concurrent run). Two suites against
  the same SQLite database and the same two fixed eval accounts silently corrupted each
  other's results. (`notes/06`)

### Degradation is a feature

Everything optional has an honest fallback, and `GET /health` reports which path each
dependency is on: no `PINECONE_API_KEY` → local JSON index; no `GOOGLE_PLACES_API_KEY` →
place tools report `configured: false`; no `LANGFUSE_*` → no tracing; no `TAVILY_API_KEY` →
an empty scoped search stays empty. Keep new integrations to this pattern, and keep
`/health` truthful.

### Tracing

Langfuse via OTEL auto-instrumentation (OpenInference for google-adk and openai) —
`init_tracing()` runs in the app lifespan before any agent call, so agent and tool spans
appear with no tracing code at the call site. Do not hand-roll spans; the one manual span
is `agents.fan_out`, because it wraps app-level orchestration rather than an agent call. (`notes/09`)

## Keeping the docs current

The docs are part of the deliverable here, so a substantial change is not finished until
they match the code.

**This applies to changes that alter behaviour, contracts or architecture** — adding or
changing an agent, tool, prompt, guard, intent, endpoint, schema column, setting, model
choice, or corpus content.

**It does not apply to** typo and comment fixes, formatting, renames, dependency bumps with
no behaviour change, or refactors that leave behaviour identical. Don't update four
documents for a one-line change; if a change sits on the line, ask rather than assume.

For a change in scope, update in the same commit:

- **README.md** — when the architecture, agent/tool table, API surface, stack, namespace
  counts or eval scores change.
- **docs/EXTENSION.md** — for anything in onboarding, tracking, reviews, Places or the
  `/travel/*` endpoints.
- **notes/** — add the *why*: the bug, the fix, and the eval case or test that caught it.
  New non-obvious decisions also get an entry in `notes/08-decisions-log.md`, and
  `notes/00-index.md` gets a row if you add a file. `notes/10-corpus-coverage.md` must be
  updated whenever a country is added, split, deepened or re-rated.
- **.env.example** — whenever a setting is added to `backend/config.py`.

Do not write aspirational claims into these files. Every number in them (test counts, eval
scores, corpus sizes, failure rates) was verified against a real run at the time of writing,
so either verify the new number or don't state one.

Eval results in `evals/results/` are committed as graded evidence and are numbered
chronologically; `--label` auto-prefixes the next sequence number, so don't number by hand,
and don't rewrite or delete existing result files.
