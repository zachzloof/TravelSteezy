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

**Pin note:** `litellm==1.72.0` specifically, because 1.78+ requires Python 3.11
(`typing.NotRequired`), and this was developed against Python 3.10.1. If the
deploy environment moves to 3.11+, the pin can be relaxed.

## `output_schema` doesn't work with OpenAI through LiteLlm

ADK's `LlmAgent(output_schema=SomePydanticModel)` serialises to
`response_format.response_schema` in the request body. OpenAI's API rejects that
key — it's a Gemini-specific field name. Every agent that needs structured output
(the turn parser, the onboarding extractor, the decision-weigher) is instead
prompted to emit raw JSON and parsed tolerantly in Python
(`graph.parse_json_block`), which tries a fenced block, then bare JSON, then the
outermost `{...}` span. This was discovered empirically by hitting the error,
not from documentation — LiteLlm's OpenAI mapping doesn't surface this
incompatibility until you actually call it.

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
