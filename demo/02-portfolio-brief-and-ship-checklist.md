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

