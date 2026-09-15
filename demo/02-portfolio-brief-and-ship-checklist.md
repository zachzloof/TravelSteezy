# Travel Steezy — Portfolio Brief & Ship Checklist

*Written for: a recruiter, hiring manager, or interviewer who has never seen
this project — readable in under two minutes, or explainable out loud in
ninety seconds.*

---

## Case-study README

### Problem

Long-term backpackers moving through a region keep asking themselves the
same question: **where do I go next?** It's a harder question than it
sounds, because the things that decide it don't share a unit — is it monsoon
season there, does a visa need days of lead time you don't have, is the
24-hour bus actually cheaper than the 1-hour flight once you price the lost
day, and is it worth it for what this specific traveller likes doing on this
specific budget? Travel Steezy is a multi-agent assistant that checks all
four of those things in parallel and hands back a ranked comparison — pros,
cons, and a verdict per destination — grounded in what it actually knows
about the traveller, not a generic tourist brochure.

### Architecture

A single request moves through a fixed pipeline, not a freeform agent loop:

1. **Read memory** — the traveller's stored profile (budget, pace, current
   location, passports, travel history with ratings) loads from SQLite.
2. **Parse the turn** — one small LLM call extracts intent and any new facts
   from the message, as structured JSON. It never talks to the user.
3. **Write memory** — plain Python functions apply what was parsed. The
   model never touches the database directly.
4. **Route by intent** — `compare | discover | local | memory | review`,
   each handled by a different agent (or set of agents) with only the tools
   that intent actually needs.
5. **Run the specialists** — for a comparison, three agents (weather,
   visa/logistics, backpacker recommendations) run concurrently, each
   pulling from its own scoped slice of a Pinecone vector store.
6. **Weigh and reply** — a final agent ranks the candidates against the
   traveller's stored preferences and returns comparison cards with cited
   sources.

### Stack

Google ADK 2.9 for agent orchestration (`LlmAgent`, `FunctionTool`,
`Runner`), OpenAI models reached through ADK's `LiteLlm` bridge, Pinecone
(serverless) for RAG with OpenAI embeddings, SQLite on a Railway volume for
memory, Langfuse 4 for tracing (OpenTelemetry auto-instrumentation, not
hand-rolled spans), FastAPI + uvicorn for the API, Vue 3 + Vite for the
frontend, and a small custom eval harness (`evals/run_evals.py`) with
assertion-first scoring and repeat-mode.

### Evals

35 cases, scored **assertion-first**: whether a retrieval tool actually
fired, whether a row landed in the database, whether a destination was
ranked where the rule says it must be — read from real system state, not
graded on how plausible the prose sounds. A small taxonomy of failure modes
is covered on purpose: wrong-season recommendations, ignored visa lead
times, generic-tourist-instead-of-backpacker advice, forgetting the stored
profile, cross-account leakage, and memory not surviving a fresh session.

**One concrete before/after number:** the case `visa-vietnam-lead-time`
(does the assistant respect a visa lead time against a hard deadline)
regressed when all three specialist agents were briefly upgraded to a
stronger model. Under ordinary load that tripped this org's OpenAI rate
limit, and an 8-run repeat measured the damage directly: **38% of attempts
passing (3/8)** before the fix. Rolling the specialists back to the cheaper
model and adding rate-limit-aware backoff to the retry loop brought the same
case, same harness, to **75% (6/8)**. The base eval suite overall went from
**14/19 to 19/19** across four separate fixes earlier in the project, and the
harness later caught something more interesting than a bug in the app: an
LLM judge that hallucinated a specific false failure reason and confidently
docked a score for it — fixed by requiring the judge to quote the exact
offending text, and rejecting any deduction whose quote doesn't actually
appear in the reply.

### Memory

- **What we keep:** an active trip profile (budget, pace, climate
  preference, location, passports, key interests) plus an append-only travel
  history with star ratings.
- **When we write:** explicit Python function calls after parsing a turn —
  never a side effect buried in a prompt.
- **Where it lives:** SQLite on a Railway volume, verified to survive a real
  process kill and restart.
- **How we retrieve:** one function loads the full profile at the top of
  every turn and backs the profile API directly, so chat and the UI can't
  disagree about what's remembered.
- **When we forget:** countries move from active context to history on
  departure; scrollback is capped; the profile itself never expires —
  forgetting is entirely user-driven.

### Live URL and backup recording

**Status: pending.** The app runs correctly end to end against live OpenAI,
Pinecone, and Langfuse services in local verification, but the Railway
deployment step and the accompanying 30–60 second screen recording have not
been completed yet. Both are the immediate next step before this is
share-ready — see the ship checklist below.

---

## Interview talking points — three decisions

### Decision 1: a fixed question sequence, not a conversational agent, for onboarding

**Decision:** Onboarding used to be a second conversational LLM agent that
decided what question to ask next. It was deleted and replaced with a fixed,
data-driven list of questions plus a single extractor agent that only turns
one answer into structured JSON.

**Why:** The conversational agent was doing real work — holding a warm
back-and-forth — but almost none of that work needed a model. "Where have
you been so far?" isn't a question that benefits from being improvised, and
letting the model choose the next question made the flow non-deterministic:
run to run, "question 2" wasn't a stable thing an eval case could even point
at. A fixed sequence is a workflow decision, not a smaller model or a better
prompt — the tradeoff was control and testability against a marginally
"smarter-feeling" chat.

**Evidence:** Once onboarding became data plus one extractor, its eval
coverage went from essentially unwriteable to **9/9 cases passing every one
of 3 runs, 27/27 individual attempts** (`evals/results/11-onboarding-v2.md`).
The rework's first eval run also caught two real, previously invisible bugs
in the first attempt — a preference write that silently no-op'd for every
brand-new account, and a dropped revisit — precisely because the flow was
now stable enough for an eval case to catch a wrong answer instead of a
different-but-plausible one.

### Decision 2: safety-critical behavior is enforced in code, not trusted to the prompt

**Decision:** Two hard rules — "never state specifics for a destination this
app holds no data on" and "always disclose upfront when a figure came from a
live web lookup, not the curated corpus" — are computed in Python and
injected as non-negotiable blocks into the final agent's prompt, rather than
left as prompt instructions the model is expected to follow on its own.

**Why:** Cost/control tradeoff. It's slower to build (a real guard function,
not a sentence in a system prompt) but it converts "the model usually
remembers to say this" into "this literally cannot be omitted."

**Evidence:** Directly caught by the eval suite, twice, at different layers.
First, the un-guarded version invented visa rules and a seasonal verdict for
Mongolia and ranked it first — fixed by adding the coverage guard, which
made `honesty-unknown-destination` pass reliably. Second, months later,
giving the final agent a real structured-output schema (instead of prompted
JSON) caused it to silently drop the live-source disclosure requirement —
reproduced 3/3 runs, stating fabricated AUD 50 visa fees for a destination
with zero curated data as plain fact, even with the exact same guard text
present. The fix that actually held wasn't a better prompt; it was a
code-level check, run after the model answers, that verifies the disclosure
is actually there and inserts it if not. Score trail:
`evals/results/modernization-final.md` (30/35, regression caught) →
`modernization-v2.md` (32/35, partial fix) → `modernization-v3-final.md`
(33/35, fixed) — a documented before/after/after showing the fix, not just
the claim of one.

### Decision 3: memory writes are a Python function call, never a model-authored side effect

**Decision:** The model's job always ends at "here is what I heard, as
structured JSON." A plain Python function in the orchestrator, not the
model, decides what that JSON means for the database — there is no "database
tool" the model can call to write directly.

**Why:** This is a deliberate security and reliability tradeoff, not the
faster path. It costs an extra parse-then-apply step on every turn, but in
exchange every write is: assertable in a test without re-parsing prose,
distinguishable in the UI as agent-inferred vs. user-edited, guaranteed to
fire exactly once for a real change (not on every re-mention), and stable
across a prompt rewrite that would otherwise silently change what gets
persisted.

**Evidence:** The audit table this enables (`memory_writes`) is a demo-facing
feature — the UI's "just remembered" panel — and it directly surfaced a real
bug: early on, simply re-stating a location the traveller was already known
to be in triggered a database write and lit up that panel every turn,
which would have made it worthless as proof of anything. Fixed at the SQL
level (the write only fires when a field actually transitions from null to
set) and pinned by a regression test
(`test_repeat_mention_is_not_recorded_as_a_write`). The same explicit-write
discipline is what makes cross-account isolation a testable property rather
than a hope: every write and read is keyed by the `user_id` pulled from a
signed JWT, never from a caller-controlled parameter, asserted by dedicated
eval cases and unit tests.

---

## Ship checklist

| Item | Status |
|---|---|
| README covers problem, architecture, stack, evals, and memory in a stranger-readable page | ✅ This document (and `README.md` in the repo) |
| At least one before/after metric from a fix is written down, not just remembered | ✅ Vietnam visa-lead-time case: 38% → 75% attempt-pass rate, both runs on disk (`evals/results/vietnam-regression-repeat8.md`, `vietnam-postfix-repeat8.md`) |
| Live URL works in incognito, plus a recorded backup demo | ⚠️ **Outstanding** — Railway deploy and screen recording are the two remaining steps (see `demo/01-system-brief-and-production-checklist.md` §8) |
| Can state, out loud, why each of the three biggest architecture decisions was the right one | ✅ The three decisions above, each in Decision/Why/Evidence form |
| LinkedIn post or portfolio-site entry published, crediting the programme | ⚠️ **Outstanding** — publish once the live URL and recording exist, so the post can link to something real |

### Good to have

- A short blog post walking through the `output_schema`-drops-disclosure
  regression above — it's a genuinely interesting failure mode (a major
  version bump making an old workaround obsolete, and the new "better" path
  quietly failing in a way a quick manual test wouldn't catch) and the eval
  trail to prove it is already written and dated.
- Screenshots of `evals/results/modernization-final.md` (30/35) next to
  `modernization-v3-final.md` (33/35) as visual before/after evidence.
- Repo cleanup pass: `README.md` is current, but confirm no stray debug
  files sit at the repo root before pinning it publicly, and consider
  trimming `PROGRESS.md` (marked in its own header as scratch notes to
  delete once absorbed) since its content now lives in `docs/EXTENSION.md`
  and `notes/`.
