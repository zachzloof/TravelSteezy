# Observability and tracing

## Current architecture: auto-instrumentation, not hand-rolled spans

As of 2026-09, tracing is **not** built by manually wrapping every agent call
in a Langfuse span. It is built on two OpenTelemetry auto-instrumentors,
turned on once at process startup (`init_tracing()` in
`backend/tracing/langfuse_setup.py`, called from `backend/main.py`'s lifespan
and from `evals/run_evals.py`):

```python
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from openinference.instrumentation.openai import OpenAIInstrumentor

GoogleADKInstrumentor().instrument()
OpenAIInstrumentor().instrument()
```

From that point on, **every** `google.adk.runners.Runner.run_async()` call
anywhere in the app - every specialist, `turn_parser`, `decision_weigher`,
`concierge`, `local_guide`, `discovery_agent`, the onboarding extractor - and
every raw OpenAI completion (the two calls in `backend/rag/live_lookup.py`,
and embedding calls in `backend/rag/embeddings.py`) is captured with **zero
tracing code at the call site**: the real model name, real token usage, the
actual request/response bodies, and the correct
`chain -> agent -> generation/tool/embedding` tree. This is Langfuse's own
documented, recommended way to trace a Google ADK application
(`langfuse.com/integrations/frameworks/google-adk`).

Verified against the real service, not assumed: ran a full real turn (parse →
fan-out of three specialists → decision weigher) with real `OPENAI_API_KEY`
and Langfuse keys, then read the trace back via
`GET /api/public/observations?traceId=`. It came back as **49 observations**
in a real tree - `SPAN(onward.turn) -> CHAIN(invocation) ->
AGENT(agent_run [weather_agent]) -> GENERATION(call_llm, model=
openai/gpt-4o-mini, real token counts) -> GENERATION(ChatCompletion, the
underlying HTTP call, also with real usage) -> TOOL(search_visa_rules) ->
EMBEDDING(CreateEmbeddings, from the RAG lookup the tool made)` - four levels
deep, all captured automatically. `evals/results/post-modernization.md` has
the full suite run confirming zero regressions from adopting it (34/35, the
one failure being the pre-existing flaky judge case documented in note 06).

**Manual tracing is now reserved for the few things that are neither an ADK
call nor an OpenAI call**: the root span for one whole turn (`Trace` in
`langfuse_setup.py`, so everything above lands under ONE trace instead of a
fresh one per agent), and two purely-Python orchestration steps - memory
read/write, and the `asyncio.gather` fan-out wrapper itself
(`backend/agents/runner.py`). Everything else that used to be a manual
`trace.generation()`/`tool_span()` call was deleted.

**Known, minor limitation**: `openinference-instrumentation-google-adk==0.1.27`
sometimes collapses several tool calls made within the same LLM turn into one
span literally named `(merged tools)`, losing which tool/args it was. This is
a limitation in that package's current release, not in this app's code -
worth re-checking on a future upgrade of that dependency.

## The session id the app sets is not the session id Langfuse keeps

**What broke:** conversation grouping, and only that. `run_turn` opens its
trace with `session_id=f"user-{user_id}"` through `propagate_attributes(...)`,
which is the documented way to set it and looks entirely correct in the code.
Langfuse nonetheless stored `local-2`, `discover-2`, `weigh-2-1`,
`concierge-2` - the ADK session id of whichever agent ran LAST in that turn,
because `_run_agent` used to build one per agent. One conversation therefore
scattered across four Langfuse "sessions" named after whichever agent happened
to answer, and no session in Langfuse showed the actual conversation.

**Found** while working bug report #3, the hard way: reconstructing that
traveller's conversation from Langfuse produced a session with four of the
turns missing, and the missing ones turned out to be filed under three other
session ids. The `--session` flag in `scripts/fetch_trace.py` and a `userId` +
time-window query are what actually recovered it.

**Why it is easy to miss, and why the UI looks fine:**

- Everything else is unaffected - span tree, models, token usage, cost,
  latency, tags, user id. Only conversation grouping is wrong.
- The overwrite is applied **at ingestion, as the child spans arrive**. Read
  the trace back immediately and it still says `user-2`; read it again a few
  seconds later and it says `concierge-2`. An early read will tell you there is
  no bug. (This cost a full experiment cycle before it was noticed.)

**Verified by experiment, not by reading the code** - the code reads correct,
which is exactly why. Same turn, same account, one variable changed:

| ADK session ids passed to `Runner` | `sessionId` Langfuse stores |
|---|---|
| one per agent (`parse-1`, `concierge-1`) | `concierge-1` |
| one per turn (`user-1` for every agent) | `user-1` |

**The fix** is `runner.adk_session_id(user_id)`, used by all six
`_run_agent` call sites: one ADK session per turn rather than one per agent.
Nothing depended on those ids being distinct - `_run_agent` builds its own
`InMemorySessionService` per call, so two agents are isolated by holding
separate service instances, not by the id string - and which agent ran is
still in the span name (`agent_run [decision_weigher]`) and in this app's own
"what ran" panel.

**Verified live afterwards on the demanding case**, per the standard below: a
real `compare` turn (turn_parser, three specialists concurrently under
`asyncio.gather`, then the decision weigher - 49 observations, five
`agent_run` spans) read back after ingestion settled, `sessionId: user-1`.
Regression-pinned by `test_every_agent_in_a_turn_shares_one_adk_session_id`.

### Why this replaced a hand-rolled version, twice

**First problem (found 2026-09-13, this app's original state):** Langfuse
keys were configured, `Langfuse()` initialised fine, and every turn produced
a trace - so from the outside this looked "done." It wasn't. The project was
pinned to `langfuse==2.60.10`, an SDK version whose entire observation
vocabulary is `SPAN` / `GENERATION` / `EVENT` (verified directly against the
installed package's `ObservationType` enum) - `AGENT`/`TOOL`/`CHAIN`/etc.
require SDK `>=3.3.1`, a fact confirmed against Langfuse's own docs, not
assumed. On top of that old SDK, the hand-rolled tracer in
`backend/agents/runner.py` never called `.generation()` at all (everything
was a generic `span`), tool spans were created with no args/result attached
even though the API supported them, most agent spans never got an `output`,
and two whole LLM call sites (`onboarding.answer_step`,
`live_lookup.fetch_and_verify`) had no tracing at all.

**Second problem (found minutes later, in the same session):** the first fix
upgraded to `langfuse==4.15.2` and hand-rewrote the tracer to call
`.generation()`/create real tool spans with the newly-available
`agent`/`tool`/`chain` types - a real improvement, verified against a live
trace. But hand-parsing ADK's event stream (pairing
`get_function_calls()`/`get_function_responses()` by id, summing
`usage_metadata`) to feed those calls was reinventing, less completely, what
turned out to already exist: `google-adk` had shipped its **own native OTEL
instrumentation** (`google/adk/telemetry/`, not present in the `1.20.0` this
app was pinned to) - and Langfuse itself documents `openinference-
instrumentation-google-adk` as the recommended way to capture it. The
hand-rolled version was deleted in favour of that, which is what's described
above. Both problems trace back to the same root cause: **dependencies were
pinned to whatever was current when first installed, then never revisited** -
`langfuse==2.60.10` and `google-adk==1.20.0` both had no comment explaining
the pin (unlike `litellm==1.72.0`, which does - see note 01 and the
dependency-modernization section below).

## Dependency modernization (2026-09)

Prompted by the same session finding two unrelated "ancient, unexplained
pins." A full audit of `requirements.txt` followed: every package was checked
against its latest release, and every non-trivial bump was verified, not
assumed:

| Package | Was | Now | How it was verified |
|---|---|---|---|
| `google-adk` | 1.20.0 | 2.9.0 | Read every real `BREAKING CHANGES` entry in the upstream changelog between the two versions (none touch `LlmAgent`/`Runner`/`LiteLlm`/tool-calling); ran a real tool-calling `LlmAgent` call through `LiteLlm` + this version. The full eval suite is where a *different*, real regression was actually caught - not from this bump itself, but from adopting `output_schema` afterward on `decision_weigher` (see the dependency-modernization code-update section below and notes/01) - fixed and reverified at 33/35, `evals/results/modernization-v3-final.md`. |
| `openai` | 2.54.0 | 3.13.0, later resettled at 2.54.0 | First bumped to 3.13.0 (`litellm==1.72.0` declares `openai>=1.68.2` with no upper bound), verified with a real end-to-end call through litellm+ADK. Landed back on 2.54.0 - its latest 2.x release, not a deliberate downgrade - once `litellm` itself moved to 1.100.1, which caps `openai<3.0.0`; see the Python move below. |
| `pinecone` | 5.4.2 | 10.0.0 | Read the real release notes for every major version 6 through 10; v10's own notes state plainly that `upsert`/`query`/`fetch`/`create_index` "does not change what your code means" for this exact usage. |
| `langfuse` | 2.60.10 | 4.15.2 | See above - the whole point of this note. |
| `fastapi` | 0.115.14 | 0.141.1 | Scanned every release's `Breaking Changes` section; none touch this app's usage (no `ORJSONResponse`/`UJSONResponse`, no `pydantic.v1`). |
| `uvicorn` | 0.34.3 | 0.52.4 | Pulled in transitively by the above with no conflict. |
| `bcrypt` | 4.0.1 | 5.0.0 | Only reachable by removing `passlib` - see below. |
| `passlib` | 1.7.4 | **removed** | Last released 2020-10-08 (dead upstream) - its `bcrypt<4.1` pin (reads `bcrypt.__about__`, removed in bcrypt 4.1) was therefore permanent, not fixable by waiting. Its entire usage in this app was `CryptContext(schemes=["bcrypt"])` with no other scheme ever configured - i.e. no real abstraction being used. Replaced with direct `bcrypt.hashpw`/`checkpw` in `backend/security.py`. Verified before touching any code: passlib's bcrypt handler emits a standard `$2b$...` hash with no passlib-specific wrapper, so a hash produced by the old code verified correctly with a bare `bcrypt.checkpw()` call - no data migration needed, checked against this project's own real stored hashes. |
| `litellm` | 1.72.0 | 1.100.1 | First re-verified (not just re-read) that the current release still hard-fails on Python 3.10 - `>=1.78` needs `typing.NotRequired`. Only Python 3.10 was installed on this machine at the time, so this was left alone in that pass as a deliberately separate, bigger decision than a `requirements.txt` edit. Revisited the same session: the runtime itself moved to Python 3.13 (below), which unblocked this. |

### The Python move itself (3.10 → 3.13)

Done as its own deliberate step once the user weighed the trade-off (a whole
additional round of the same verify-live-then-eval cycle, for a library -
`litellm` - whose current pin had no actual functional cost to this app) and
asked for it anyway: "the earlier we do it the better we can refine."

**Installing Python 3.13 was not straightforward on this machine.** Both the
winget-driven install and a direct download of the official
`python-3.13.15-amd64.exe` installer hung identically and indefinitely in
`/quiet` mode - no `msiexec` process ever spawned, no install log was ever
written, across three separate attempts (winget, direct EXE, direct EXE with
explicit `/log`). This looked like a UAC/elevation stall at first, but
`InstallAllUsers=0` (a genuinely elevation-free per-user install) hung the
same way, which ruled that out - something about this machine or session
blocks the installer's bootstrap stage outright, not just its elevation
prompt. Diagnosed by checking the full process list each time (`tasklist`
with no filter), not just grepping for "python", specifically to catch a
child process running under a different name - none ever appeared.

Worked around by using Python's **embeddable ZIP distribution** instead
(`python-3.13.15-embed-amd64.zip`), which needs no installer at all:
extracted, edited `python313._pth` to enable `import site` and
`Lib\site-packages`, bootstrapped `pip` via `get-pip.py`. The embeddable
distribution deliberately ships without the stdlib `venv` module (confirmed:
`ModuleNotFoundError: No module named 'venv'`), so the third-party
`virtualenv` package - which doesn't depend on stdlib `venv` - was used to
build the project's actual `.venv` instead of `python -m venv`.

Verified before adopting, in this order: `pip check` for a clean dependency
graph (`openai` correctly resolved down to 2.54.0 to satisfy litellm's own
`<3.0.0` cap - no conflict, no manual pinning fight); `litellm` and every
other core library importing cleanly (confirming the original `NotRequired`
failure was actually gone, not just theoretically fixed); the full unit test
suite (103/103); live calls through the schema-typed agents, the
prompted-JSON `decision_weigher` including its live-source disclosure
backstop, the onboarding extractor, Pinecone, and embeddings; and a full eval
run, `evals/results/python313-litellm-current.md`, scoring **33/35** -
matching the pre-move score, with `honesty-unknown-destination` (the guard
this session spent the most effort on) passing, and the two misses being
different cases than the previous run, consistent with the already-documented
specialist-dispatch variance rather than anything the Python move caused.
`nixpacks.toml` and `runtime.txt` updated to `python313`/`3.13.15` for the
Railway deploy target; `python313` confirmed as a real, current nixpkgs
attribute (not assumed) before relying on it.

`opentelemetry-api`/`-sdk`/`-exporter-otlp-proto-http` are pinned to exactly
`1.42.1`: `google-adk` caps them at `<=1.42.1` while `langfuse` alone would
happily pull something newer, which produces a real, reproducible pip
conflict on a fresh install (hit and fixed during this work) unless pinned
explicitly.

### Updating the code to the new versions' idioms, not just to not-crash

A version bump alone leaves code that still runs but no longer reflects how
the upgraded library is meant to be used. Two follow-up rewrites, both found
by reading the new major version's actual capabilities rather than only
checking for breakage:

- **Real `output_schema` instead of prompted JSON - for the two agents where
  it held up.** `turn_parser` and the onboarding extractor
  (`backend/agents/graph.py`, `backend/agents/onboarding.py`) now declare a
  Pydantic `output_schema` instead of being prompted to emit raw JSON and
  parsed tolerantly after the fact. This was possible the whole time this
  session's `google-adk` bump was live, but is easy to miss if you only check
  "does the old code still work" rather than "does the new version make the
  old code's workaround obsolete." `decision_weigher` was tried the same way
  and reverted after a live eval run caught it dropping the coverage guard's
  disclosure requirement under both calling conventions - fixed instead with
  a code-level backstop, not a prompt tweak. Full detail, the verification
  steps, and the eval trail that caught and then confirmed the fix are in
  [notes/01-agent-architecture.md](01-agent-architecture.md#output_schema--fixed-upstream-since-re-adopted-2026-09).
- **Pinecone: attribute access and real enums, not dict-style hedging.**
  `backend/rag/store.py` used to check `isinstance(result, dict)` before
  every field access on a query result, and built `ServerlessSpec` from raw
  strings (`cloud="aws"`, `metric="cosine"`). Pinecone's client was rewritten
  as hand-written, `mypy --strict`-typed models starting at v9 — verified
  live against the real index that `list_indexes()`/`query()`/`fetch()`/
  `describe_index_stats()` all return typed model objects with attribute
  access as the real interface (dict-style access still works, kept only for
  migration ease from pre-v9 code), and that `CloudProvider`/`Metric` enums
  exist and match the configured string values exactly. Rewritten to use
  attribute access and the enums throughout, dropping the dual-mode hedging.
  `region` stays a plain string deliberately: which enum applies depends on
  the chosen cloud provider (`AwsRegion` vs `GcpRegion` vs `AzureRegion`), and
  building that resolution for a single-cloud deployment wasn't worth it.

Both were verified against the real live services (a real Pinecone query
against the production index; a real OpenAI call through the real prompts
for each of the three schema-typed agents) before being considered done -
same standard as everything else in this note.

## Standard to hold future changes to

Read this before adding or changing anything that calls an LLM, in this app
or its next one:

1. **A new agent, tool, or endpoint that calls google-adk or openai needs
   nothing added to get traced** - the auto-instrumentation already covers
   any `Runner.run_async()` or `chat.completions.create()` call, anywhere,
   automatically. Do not add a manual `trace.generation()`/span around it;
   that would either duplicate what's already captured or, if done with an
   old-API assumption, silently produce a worse trace than doing nothing.
2. **Manual tracing is only for a genuinely non-ADK, non-OpenAI step**
   (a plain-Python orchestration step, a step in some future third-party API
   this app calls directly). Use `Trace.span()` for those, `Trace.local_step()`
   for a step whose real Langfuse detail is already auto-captured elsewhere
   and only needs a timing entry in this app's own "what ran" UI panel.
3. **A v4 Langfuse span is a real OpenTelemetry span - once its `with` block
   exits, it is genuinely closed.** Unlike the old v2 SDK, you cannot call
   `.update()` on a handle after its context manager has exited and expect it
   to take effect. If a span's final output isn't known until after some work
   finishes, keep that work inside the same `with` block (see
   `agents.fan_out` in `runner.py` for the pattern: the whole fan-out,
   including building the aggregate report, stays inside one `with
   trace.span(...)`, not split into "gather, then close, then try to update").
4. **Trace-level attributes (session id, user id) can be overwritten by the
   auto-instrumentation**, which carries its own idea of them from whatever
   framework object it wraps. Setting them correctly on the app's own root
   span is not sufficient and not proof - see the session-id section above.
   After any change that touches them, read a real trace back through the API
   and check the stored value, and do it a second time a minute later: the
   overwrite happens at ingestion, so an immediate read shows the value you
   set rather than the value that sticks.

4. **Don't assume a pin has gone stale without checking why it's there.**
   Both `langfuse` and `google-adk` were years behind with no reason on
   record; `litellm` looks identically stale next to them but has a real,
   twice-verified reason. Check for an actual technical constraint (try the
   upgrade in isolation, read the real changelog) before either "it's
   probably fine, bump it" or "there's probably a reason, leave it."
5. **Verify a live trace after any change here, don't trust that a client
   initializing or a call not raising means tracing is correct.** Every claim
   in this note was checked by reading a real trace back via
   `GET /api/public/observations?traceId=...` with the project's own
   Langfuse keys, not inferred from code review alone - that's what caught
   both the original span-vs-generation gap and the fact that a "healthy"
   auto-instrumented call still needs `init_tracing()` to have actually run
   first (a smoke-test script that skipped it produced a visibly messier,
   less-typed trace even though nothing raised an exception).
6. **A major version bump is a prompt to check what became newly possible,
   not just what might now be broken.** "Does the old code still run" and
   "is the old code still how you're meant to do this" are different
   questions - `google-adk` 1.20→2.9 answered both differently: nothing broke,
   but `output_schema` genuinely started working with OpenAI along the way,
   which made a whole hand-rolled JSON-parsing layer obsolete. Checking only
   for breakage would have missed it entirely.
7. **A live sanity call proves an agent CAN work, not that it reliably will.**
   `output_schema` on `decision_weigher` looked completely fine in a live
   smoke test (correct types, correct fields, sensible-looking text) and
   still dropped a safety-critical disclosure requirement in the full eval
   suite, reproducibly. For an agent carrying real conditional, safety-shaped
   prose instructions - not just "extract these fields" - a passing manual
   test is necessary but not sufficient; run the eval suite (or the specific
   cases that exercise that instruction) before trusting a behavior change,
   agent-architecture or otherwise. And when an eval does catch something,
   don't assume the first fix that makes the specific failing case pass is
   the real fix - the first attempt here (append a disclosure only if one
   looks absent) passed a quick manual check but still failed the eval judge,
   because it satisfied the letter of "discloses somewhere" without the
   substance of "discloses upfront" the rubric actually asked for.
