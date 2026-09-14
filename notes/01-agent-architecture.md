# Agent architecture

## Why Google ADK with an OpenAI model, not Gemini

The brief specified ADK as the framework and OpenAI as the model provider. ADK is
a framework, not a model — it defaults to Gemini but ships `LiteLlm`
specifically to bridge other providers. We point it at OpenAI:

```python
LiteLlm(model="openai/gpt-4o-mini", api_key=settings.openai_api_key)
```

This was proven, not assumed: a probe script imported everything, then stripped
`GOOGLE_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, `GEMINI_API_KEY` and the
Vertex env vars from the process, and ran a real `LlmAgent` through a real
`Runner`. It worked — ADK invoked the tool itself, correct answer, zero Google
credentials present. `agent.model` is `google.adk.models.lite_llm.LiteLlm`
pointed at `openai/gpt-4o-mini`. The user's `.env` has an unrelated
`GOOGLE_API_KEY` (looks like an OAuth token, not an API key) that nothing in
this app reads.

**Pin note (resolved 2026-09):** this was pinned at `litellm==1.72.0` because
1.78+ requires Python 3.11 (`typing.NotRequired`), and the project was
developed against Python 3.10.1. Relaxed by moving the runtime itself to
Python 3.13 rather than leaving the pin in place - see the dependency
modernization in [notes/09](09-observability-and-tracing.md) for how the
move was carried out (Python installed per-user via the embeddable
distribution + `virtualenv`, since the standard installer hung
non-interactively on this machine) and verified (full test suite, live
calls through every agent, a full eval run at 33/35 matching the pre-move
score - `evals/results/python313-litellm-current.md`) before being adopted.
`litellm==1.100.1` and `openai==2.54.0` now, the latter capped by litellm's
own `openai<3.0.0` requirement rather than a deliberate downgrade.

## `output_schema` — fixed upstream, since re-adopted (2026-09)

This used to say `output_schema` didn't work with OpenAI through LiteLlm:
older ADK serialised `LlmAgent(output_schema=SomePydanticModel)` to
`response_format.response_schema`, a Gemini-specific key OpenAI's API
rejects, discovered empirically by hitting the error. Every agent needing
structured output (turn parser, onboarding extractor, decision-weigher) was
instead prompted to emit raw JSON and parsed tolerantly in Python
(`graph.parse_json_block`: fenced block, then bare JSON, then the outermost
`{...}` span).

**That is no longer true.** Verified directly against the ADK version this
app now runs (2.9, up from 1.20 — see the 2026-09 dependency modernization in
[notes/09](09-observability-and-tracing.md)): `google.adk.models.lite_llm`
now branches on the model — Gemini gets the old `response_schema` shape,
anything else gets OpenAI's real `{"type": "json_schema", "json_schema":
{..., "strict": true}}` structured-outputs format, with the generated schema
automatically rewritten to satisfy OpenAI's strict-mode rules
(`additionalProperties: false`, every property forced into `required`). This
was read from the ADK source (`_to_litellm_response_format`,
`_enforce_strict_openai_schema`) and confirmed live: a schema-typed call
returns an already-validated `dict` in `session.state[output_key]`, no text
to parse.

`turn_parser` and the onboarding extractor now declare a real Pydantic
`output_schema` (see `backend/agents/graph.py`, `backend/agents/onboarding.py`)
instead of relying on a prompted JSON convention. `parse_json_block` is kept
only as a defensive fallback for the case a schema-typed call doesn't
populate state as expected — not observed in practice for these two, but
cheap insurance. One genuine side benefit: the onboarding extractor used to
show the model a literal example JSON block to convey its shape, and the
model would occasionally copy that literal example into unrelated answers
(see `backend/agents/onboarding.py` for the specific bug this caused). Real
`output_schema` conveys the shape via the API's own mechanism instead of
prompt text, so there is no example left to copy — the failure mode
disappeared as a side effect of the fix, not something that needed a
separate workaround.

**`decision_weigher` deliberately did NOT keep `output_schema`.** It was
tried, and reverted after being caught live: with the exact same
coverage-guard text present, and the specialist's own report already
correctly labeling its findings "unverified... came from a live source,"
the schema-typed weigher still dropped that disclosure when synthesising its
reply and cards — reproduced 3/3 runs, stating AUD 50 visa fees and
$20-30/day budgets for Nauru and Uzbekistan (destinations this app holds zero
curated data for) as plain, undisclosed fact. Reverting to prompted JSON
alone did not fix it either — the same failure reproduced again without
`output_schema` in the picture at all, which means it was never really about
strict mode specifically; it is a standing weakness in how reliably this
agent follows its most safety-critical, most deeply conditional instruction
(five "hard rules" plus two guard blocks - by far the most prose-instruction
load of any agent here) under either calling convention. The fix that
actually held is a code-level backstop,
`_enforce_live_source_disclosure` in `backend/agents/runner.py`: after the
weigher answers, code checks whether its own output actually discloses
live-sourced figures and, if not, prepends an explicit disclosure to the
reply and appends one to the affected cards' `visa_flag` - unconditionally,
every time a candidate came from live lookup, not only when disclosure looks
absent. This mirrors the existing coverage guard's own philosophy
(`backend/agents/coverage.py`): compute the safety-critical fact in code,
don't hope the model states it. The first version of this backstop only
*appended* the disclosure when it looked entirely missing, which technically
satisfied "mentions unverified somewhere" but still read - correctly - as an
afterthought to a human and to the eval judge, whose rubric explicitly wants
an "upfront" admission; leading with it unconditionally is what actually
holds under repeat runs. See `evals/results/modernization-final.md` (30/35,
the regression caught), `modernization-v2.md` (32/35, append-only fix,
`honesty-unknown-destination` still failing on "not upfront"), and
`modernization-v3-final.md` (33/35, fixed) for the documented trail.

## Why not ADK's `ParallelAgent`

The first version of the specialist fan-out nested a `ParallelAgent` inside a
`SequentialAgent`:

```python
SequentialAgent(sub_agents=[ParallelAgent(sub_agents=[weather, logistics, recs]), weigher])
```

This intermittently raised `aclose(): asynchronous generator is already
running` during teardown of the concurrent sub-generators. The failure mode
wasn't cosmetic — it **aborted the whole turn**, and the eval case
`rag-cites-source` caught it returning zero comparison cards to the user twice
in a row.

The fix: run each specialist in its own `Runner` under `asyncio.gather`,
outside of any ADK-managed concurrency construct.

```python
outcomes = await asyncio.gather(*(
    _run_one_specialist(agent, key, state, message, user_id, trace, fan_span)
    for agent, key in specialists
))
```

This is still genuine parallelism — Langfuse traces show the fan-out completing
in wall-clock time close to the *slowest* individual specialist (9.87s wall
clock for 26.3s of combined specialist work), not the sum. It also has a
property `ParallelAgent` didn't give us for free: **failure isolation**. Each
specialist runs in `_run_one_specialist`, which catches its own exceptions and
reports `(key, "", [], error)` rather than propagating — one specialist erroring
no longer takes the other two, or the weigher, down with it. Each specialist
also gets one retry before being marked failed.

## The two-agent split for onboarding

This is probably the single most instructive bug in the whole project, so it's
worth explaining in full.

**First attempt:** one `LlmAgent` with an instruction that asked it to (a) hold
a warm, brief conversation and (b) append a hidden machine-readable block in a
fixed format after its reply, for the orchestrator to parse and strip before the
user sees it.

**What happened:** `gpt-4o-mini` reliably produced (a) and reliably dropped (b).
Not sometimes — every single test run. The conversational framing apparently
dominates enough that the structured-output instruction gets deprioritized to
the point of non-existence. This was diagnosed by writing a standalone debug
script that called the agent directly and printed the raw completion:

```
RAW OUTPUT >>>
Sounds like you're having quite the adventure in Thailand! Now, where do you
most want to go next?
<<< END RAW
PARSED captured: {}
```

No JSON block at all — not malformed, not truncated, just absent. Because
nothing was ever captured, `onboarding_gaps()` (see note 02) never advanced,
so the conversational agent kept re-asking the same first question forever.

**Fix:** split into two agents with disjoint jobs:

- `onboarding_extractor` — reads one message, returns JSON only, never speaks to
  the user. Its whole prompt is "you extract structured travel facts... you
  never talk to the user."
- `onboarding_agent` — holds the conversation, is told explicitly "Reply with
  your conversational message only — no JSON, no lists of fields," and is fed
  `onboarding_gaps` / `onboarding_captured` (both computed in Python from the
  database, not from the model) so it knows what to ask next.

This is a general lesson worth remembering for any future agent design in this
codebase: **an LLM asked to do two jobs in one call at very different
"registers" (warm prose vs. exact-format machine output) will silently favour
one and drop the other**, and it won't necessarily be predictable which one. If
a step in the pipeline genuinely needs both, split it into two calls rather than
trying to prompt-engineer around it — the split cost one extra LLM call per
onboarding turn and was worth every millisecond of it.

### Epilogue: the conversational half was later deleted entirely

The two-agent split fixed the bug it was aimed at. Extraction started working and
stayed working. But `onboarding_agent` — the half that held the conversation —
was removed in a later pass, and the reasoning is a useful counterweight to the
lesson above.

Splitting the agent was the right fix *given the requirement that onboarding be a
conversation*. Nobody had re-examined that requirement. Once it was, the
conversational agent turned out to be carrying almost no weight and costing quite
a lot:

- **It decided what to ask next**, which meant the question varied run to run.
  That made the eval case weak by construction — it could assert the end state
  after three turns but never that a specific question's extraction was correct,
  because there was no stable "question 2" to point at.
- **It was a whole LLM round-trip per turn** to produce a sentence that a
  designer could have written once, better, and put on a page.
- **It was slower and vaguer than a form** at the thing it was for. "Where have
  you been so far?" is not a question that benefits from being improvised.

So the questions became data (`QUESTIONS` in `backend/agents/onboarding.py`) and
the extractor stayed. It is now built per question, with the question text in its
instruction, which made extraction measurably better at the one distinction it
kept getting wrong: whether a place belongs in history or on the wishlist is
carried almost entirely by which question prompted the answer.

The general lesson above still holds — do not ask one call to do two registers.
The additional lesson is narrower and easier to miss: **check whether the second
register needs a model at all.** Here it did not, and removing it made the
feature faster, more predictable, and for the first time properly testable.

## Intent routing

A turn is classified into one of `compare | discover | local | memory | review`
by the turn parser, and the runner dispatches to a different agent/pipeline per
intent (`_run_comparison`, `_run_discovery`, `_run_local_guide`,
`_run_concierge`). This grew out of the extension: the original app only ever
did `compare` (or fell back to `concierge` for small talk). Adding
"where next from here" (discover) and "what's good near me" (local) needed
different tool sets — `discover_next_destinations` for the former,
`suggest_areas_to_stay` / `find_hostels` / `find_food_near` for the latter — and
routing all of it through the comparison pipeline would have forced every one of
those tools onto every agent, which is both slower (more tools = more
temptation for the model to call ones it doesn't need) and muddier in the
prompt.

**The routing itself needed a deterministic override.** The classifier
initially sent "what do I need to get into Indonesia and Cambodia?" to `local`
(it read as an on-the-ground question), which routed to `local_guide` — an
agent with no visa tool — and the model answered a visa question from
parametric memory, getting a rule wrong. Fixed with a hard rule in
`runner.py`: any turn naming two or more destinations is forced into `compare`
regardless of what the classifier said, because a real comparison-shaped
question (even if worded as "what do I need for X and Y") should never reach an
agent with no visa/route tools. If the parser under-detects destinations (fewer
than 2 recognised), the runner falls back to `rag_store.detect_destinations`
over the raw message text as a second pass. Classification is a hint; two named
places is a fact.

## Model sharing across concurrent specialists

`build_model()` originally constructed a new `LiteLlm` instance per agent. This
was implicated (not conclusively proven, but the fix eliminated the symptom) in
intermittent `coroutine raised StopIteration` failures when three specialists
ran concurrently under `asyncio.gather` — `litellm` appears to keep some
process-global client state that doesn't like being initialised freshly by
several coroutines at once. Fixed by `@lru_cache`-ing the `LiteLlm` instance per
model name, so all agents share one client object. Combined with the retry
logic in `_run_one_specialist`, this brought that failure mode's observed rate
to zero across the repeat-3 eval runs (81 turns × several tool calls each).

## Model selection: not every agent needs the same model (2026-09)

Every agent used `settings.llm_model` (`gpt-4o-mini`) uniformly until this
point. That stopped being a neutral default once the reliability bugs traced
through most of `notes/03-rag-and-retrieval.md`'s later follow-ups turned out
to concentrate in one place: `decision_weigher`. It is the single most complex
reasoning step in the graph - synthesise three specialist reports, hold five
hard rules simultaneously (season, visa/deadline, no-invented-facts, coverage,
verdict-consistency), stay internally consistent across candidates, and emit
valid JSON - and it was where the actual bugs showed up: a verdict spread
manufactured across ranked candidates with no data behind it, needing up to
three attempts because it sometimes answered in prose instead of JSON, and
residual "avoid" verdicts for destinations the specialists had reported
cleanly and positively.

The fix is not a bigger prompt, it's a bigger model for that one call.
`decision_weigher` now runs on `settings.weigher_model` (default `gpt-4o`)
instead of the shared `settings.llm_model` (`gpt-4o-mini`) - see
`build_model()`'s optional `model_name` argument in `backend/agents/graph.py`.
This is called exactly ONCE per turn, so the cost/latency delta against a
pricier model is negligible per turn even though the per-token price is
higher; upgrading a tool the specialists call three times each would be a
real cost decision, upgrading the one-shot final synthesis is not.

**Initially left on the shared cheap model** - the three specialists
(`weather_agent`/`logistics_agent`/`recommendations_agent`) each hold several
MUST-call-this-tool rules plus the coverage/disclosure guard simultaneously,
the same multi-constraint prompt shape that caused trouble for the weigher,
and one live reproduction had the Weather specialist skip its required tool
calls entirely for a turn. Upgrading three agents that each run once per turn
is a real cost multiplier though (triples the added spend versus the weigher
alone), so this was deliberately deferred pending actual measurement of how
often the skip happens, rather than upgraded on a guess.

**Upgraded anyway, on explicit instruction** rather than after that
measurement: `settings.specialist_model` (default `gpt-4o`) backed all three
specialists too, briefly. The cost tradeoff named above is real and was
un-measured - this was a judgment call to accept it now rather than wait, not
a finding that the skip rate turned out to be high. Noted at the time: if it
later turns out unnecessary, the fix is a one-line env var change, not a code
change - which is exactly what happened next.

**Rolled back the next day, for a reason nobody had measured yet:** this
org's actual OpenAI rate limit for `gpt-4o` is 30,000 tokens/minute - the
standard low starting tier, much lower than `gpt-4o-mini`'s. Putting four
agents on `gpt-4o` per comparison turn (three specialists firing concurrently
via `asyncio.gather`, plus the weigher) reliably tripped that limit under
completely ordinary load, not just heavy testing - reproduced directly via
captured `litellm.RateLimitError` tracebacks ("Limit 30000, Used 29425,
Requested 2122") and an 8x repeat run of one eval case: 62% of attempts
degraded (5/8), either losing a candidate's card silently or returning no
comparison at all. This is what caused a real regression in the previously-
reliable `visa-vietnam-lead-time` eval case: the rate limit hit a specialist
mid-turn, that specialist's report came back empty, and the weigher had
nothing to build Vietnam's card from - not a reasoning or prompt failure, a
straightforward capacity mismatch between what was asked for and what the
account could sustain.

`specialist_model`'s default reverted to `gpt-4o-mini` (`SPECIALIST_MODEL` in
`.env`/`.env.example` likewise) - back to exactly one `gpt-4o` call per turn
(the weigher), not four. The setting itself was kept, not deleted, precisely
for this: raising it again is a one-line change once this org's `gpt-4o` TPM
limit is confirmed higher, with no code change needed either way. Paired with
this: `runner.py`'s specialist and Decision-Weigher retry loops previously
retried ANY failure instantly with no backoff at all. `_rate_limit_backoff_seconds()`
now detects a rate-limit error specifically (by exception name or message
text, since ADK's error wrapping means the type reaching this code cannot be
relied on to always be the exact `litellm.exceptions.RateLimitError` class)
and sleeps for the API's own "try again in Xs" hint (or a small capped
default if that hint is absent) before the next attempt - so a transient 429
gets a real chance to clear instead of every retry burning itself on the same
still-active limit. This is a general robustness fix, independent of which
model tier is in use, and stays useful even at `gpt-4o-mini`'s much higher
ceiling.

**`judge_model` (`evals/run_evals.py`) was also decoupled from `llm_model` and
upgraded to `gpt-4o`**, independent of the weigher change above and for a
different reason: it used to default to the same model (`gpt-4o-mini`) the
system under test runs on, which means the judge shares that model's blind
spots - it is structurally less likely to catch the exact class of mistake it
would make itself. A judge from a different model line does not have this
problem.

`LLM_MODEL` was NOT retired or made redundant by any of this - it is still
the model seven-plus agents actually run on (`turn_parser`, all three
specialists, `concierge`, `local_guide`, `discovery_agent`, the onboarding
extractor) plus every `live_lookup.py` synthesis/verify/`classify_season`
call. `WEIGHER_MODEL` and `JUDGE_MODEL` are narrow overrides for the two
places that specifically warranted a different model, not a replacement for
the shared default everything else still relies on.
