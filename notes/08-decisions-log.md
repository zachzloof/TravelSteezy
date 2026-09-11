# Decisions log

Chronological record of every non-obvious choice, in the order it was actually
made. Where a decision was reversed or refined later, both the original and the
revision are recorded — the "why we changed our mind" is often the most useful
part.

## Phase 1: base app scaffold

1. **Python 3.10, not 3.11+.** Only version available in the dev environment.
   Forced `litellm==1.72.0` pin (see note 01) since 1.78+ needs
   `typing.NotRequired` from 3.11.
2. **`LiteLlm` bridge for OpenAI, not native Gemini.** Brief specified OpenAI
   models with ADK as the framework; proven with Google credentials fully
   stripped from the environment (note 01).
3. **SQLite on a Railway volume, not Postgres.** Course-scale traffic, no
   need for the operational overhead of a managed Postgres instance; SQLite's
   file-based nature also makes "does memory survive a redeploy" a directly
   testable question (kill the process, start a new one against the same file,
   check the row is still there) — which was done live, not just asserted.
4. **Pinecone with a local-JSON fallback**, so the app, the tests, and the
   eval suite all run with zero external keys. The fallback path uses a
   deterministic hashed bag-of-words embedding (not real semantic search) when
   `OPENAI_API_KEY` is also absent — clearly inferior to real embeddings, but
   keeps the whole stack runnable offline for development.
5. **Admin auth is structurally separate from user auth** (`kind: "admin"` vs
   `kind: "user"` in the JWT payload, checked by different FastAPI
   dependencies) rather than an `is_admin` flag on the user table — this makes
   "a user token can reach an admin route" a type error at the dependency
   level, not a logic bug that has to be remembered.

## Phase 2: base-app eval cycle (14/19 → 19/19)

6. **The synthesis step was discarding retrieved detail.** Specialists
   retrieved correctly (right tools, right passages) but the decision-weigher
   compressed everything into 3-6 generic sentences — "lower visa costs"
   instead of "$30 visa on arrival, 30 days." Fixed by requiring the weigher's
   reply to carry ≥2 concrete figures forward and adding a `backpacker_notes`
   field to each card with required coverage (cost + activity + transport +
   warning) and `source_ids` for citation.
7. **The unscoped-retrieval fallback was removed** after it caused
   confabulation for uncovered destinations (see note 03) — this was the fix
   for `honesty-unknown-destination` in the base-app cycle, and the same
   underlying principle (an empty scoped result must stay empty, never widen
   the search silently) held throughout the rest of the project.
8. **`ParallelAgent` replaced with `asyncio.gather`** after the generator
   teardown race aborted turns (note 01). This was found via the eval suite,
   not via manual testing — `rag-cites-source` returned zero cards twice
   before the cause was diagnosed.
9. **A real `StopIteration` bug in the climate table's month-name lookup**,
   found only because fix #8's error isolation let the underlying exception
   surface instead of silently killing the whole turn. `MONTH_NAMES[month - 1]`
   replaced a fragile reverse-search (`next(n for n, v in MONTHS.items() if v
   == month and len(n) > 3)`) that happened to find nothing for May, since
   May's full name is exactly three characters and the filter required
   `len(n) > 3`.

## Phase 3: live service wiring

10. **Pinecone ingested into a real, pre-existing index** (`ai-bootcamp`) with
    its own namespaces (`visa`/`seasonal`/`tips`) rather than requiring a fresh
    index — verified the existing 59 vectors in the default namespace were
    untouched.
11. **Langfuse spans needed nesting, not just existing.** The first working
    version produced 5 flat spans per turn (no parent/child relationship), which
    technically satisfied "instrument every agent call" but didn't show the
    orchestrator fan-out structure the brief specifically asked to see. Spans
    were made nestable (`Trace.span(..., parent=...)`) and tool calls emit as
    child spans of their calling agent, producing an 18-span tree verified by
    reading it back through the Langfuse API, not just by publishing it.

## Phase 4: the extension

12. **Schema: `travel_history` supersedes `visited_history`, migrated not
    replaced** (note 02).
13. **Onboarding: one agent → two agents** after discovering the model
    silently drops a structured-output instruction when it's paired with a
    conversational one in the same call (note 01) — the single most
    significant architectural finding of the whole extension.
14. **Onboarding progress computed from the database, never from the model's
    own claim.** A `next_step` field in the model's JSON output was
    considered and rejected as the source of truth, specifically because if
    extraction silently failed (as it did in decision #13's bug), the step
    would never advance and the conversation would loop forever with no
    external signal that anything was wrong. `travel.onboarding_gaps(user_id)`
    asks the database directly instead.
15. **Bayesian ranking: prior weighted by review count, not candidate count**
    (note 04) — caught by a two-candidate unit test that exposed the plain-mean
    prior letting a single thin outlier win.
16. **Clustering: centroid distance + spread cap, not single-linkage** (note
    04) — caught on real data (Chiang Mai hostels chained into one 2.6km
    "area").
17. **Hostel search: text search, not `includedTypes: ["lodging"]`** (note 04)
    — caught on real data (lodging search returned five-star resorts).
18. **`resolve_country` extracted as a shared resolver** after the same
    town-vs-country bug appeared independently in the climate table, the route
    table, and the coverage guard (note 03) — the third occurrence is what
    triggered pulling it into one function rather than patching a third call
    site.
19. **Town departures stopped writing into country-level history** (note 02)
    — "leaving Pai" was being recorded as "leaving Thailand."
20. **The eval judge required to quote evidence** after fabricating a
    deduction ("asks for budget information" against a reply that asked for
    nothing) — note 06.
21. **`--repeat 3` added to the eval harness** after four runs of identical
    code scored 89/96/93/89% — note 06. This is listed last in the log not
    because it's least important but because it's the methodological decision
    that made decisions #18-20 possible to *notice* in the first place: a
    single-run harness would have reported `season-malaysia-east-coast-closed`
    as either a clean pass or an unexplained regression, and the real bug
    underneath it would likely have gone unfound.

## Open items at the time of writing

- The extension's final repeat-3 eval run (post-fix #18) is in progress; its
  results file (`evals/results/extension-final.json`/`.md`) is the
  authoritative current number, superseding any number quoted earlier in this
  conversation before the fix landed.
- Railway deployment, the demo-safety account decision (seeded demo account
  vs. `ADMIN_AUTO_APPROVE`), and the backup screen recording remain outstanding
  from the original build — unrelated to the extension, carried over from
  before it started.
