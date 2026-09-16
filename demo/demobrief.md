## 6. Demo Day walkthrough plan (5–10 min slot, ~5 min live)

| Time | Segment |
|---|---|
| 0:00–0:30 | **Problem.** One line: backpackers ask "where next" constantly, and season/visa/logistics/taste don't share a unit. |
| 0:30–1:15 | **Architecture.** Point at the pipeline diagram: parse → write → parallel specialists → weigher. Name the one deliberate guard (coverage) so the audience knows honesty is engineered, not hoped for. |
| 1:15–1:45 | **Stack.** One breath: ADK + OpenAI via LiteLlm, Pinecone RAG, SQLite memory, Langfuse tracing, Railway host. |
| 1:45–6:45 | **Live demo (~5 min)**, following the README's demo script: <br>1. Incognito, log in as the seeded demo account — memory sidebar already populated, nothing typed yet. <br>2. Ask *"I'm in Thailand with six weeks left — Laos or Vietnam?"* — ranked cards with pros/cons/season/visa flags and sourced backpacker notes appear. <br>3. Expand "Show what ran" — real specialist timings and retrieved passages with similarity scores, straight from the trace. <br>4. Change a preference (climate → cool) in My Preferences, ask again — ranking moves, reply names the preference that drove it. <br>5. Say *"I left Laos yesterday, I'm in Thailand now"* — sidebar's "Just remembered" panel shows the write live. |
| 6:45–7:30 | **Prove persistence.** Log out, reopen in a fresh incognito window, log back in — profile is exactly as it was (or hit `/profile/me` directly). |
| 7:30–8:00 | **Evals close.** State the number, not a vibe: "33/35 on the full suite, and here's a real regression this exact harness caught and the fix that closed it" (Vietnam lead-time, 38%→75%). |

If live time runs short, cut step 4 (preference change) first — persistence
and the initial comparison are the two things that must land.


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
