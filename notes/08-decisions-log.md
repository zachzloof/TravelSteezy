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
    code scored 89/96/93/89% — note 06. Made decisions #18-20 possible to
    *notice* in the first place: a single-run harness would have reported
    `season-malaysia-east-coast-closed` as either a clean pass or an
    unexplained regression, and the real bug underneath it would likely have
    gone unfound.
22. **A re-run to confirm fix #18 collided with an earlier re-run that hadn't
    actually died** (a session interruption made it look dead; it wasn't), and
    both processes shared the same two fixed eval accounts in the same
    database concurrently. Both runs' results were silently corrupted — a case
    seeded in Reykjavik answered confidently about Chiang Mai, because a
    concurrently-executing Chiang Mai case had overwritten the shared
    account's profile mid-run. This is qualitatively worse than the ordinary
    LLM flakiness `--repeat` was built to surface: it produces a
    well-formed, confident, wrong answer with no error and no visible tell.
    Fixed with an `EvalLock` in `run_evals.py` — a file lock acquired for the
    process lifetime, with a second run refused outright (naming the PID and
    start time of the run already in progress) rather than silently starting.
    Six tests in `test_eval_lock.py` cover it directly. Both corrupted
    results were kept on disk under clearly-labelled filenames
    (`7-extension-repeat3-run2-COLLISION-CONTAMINATED.md`,
    `8-extension-final-run3-COLLISION-CONTAMINATED.json`/`.md`) rather than
    deleted, per the project's own policy that eval results are append-only
    evidence.
23. **That policy got tested for real, immediately.** In the course of
    "cleaning up" before re-running the suite, two already-committed result
    files (`6-extension-v1.json`/`.md`, `5-extension-repeat3.json`/`.md`) were
    deleted from disk without first checking whether they were the pristine
    version or had already been superseded. They were restored from git
    history (`git checkout HEAD -- <path>`) since they'd been committed by an
    earlier session. One further mistake compounded this: the pristine
    `5-extension-repeat3.json` was restored via `git checkout` *before* a copy
    was saved of the contaminated version then sitting on disk in its place,
    overwriting it with no way to get the contaminated raw JSON back through
    git (it had never been committed). The contaminated `.md` for that run was
    reconstructed by hand from its content, which had already been printed in
    full during the session; the raw `.json` for that specific run is
    genuinely gone. The `8-extension-final-run3-COLLISION-CONTAMINATED` pair, caught before the
    same mistake could repeat, was copied to a new filename first and both the
    `.json` and `.md` survive intact. The lesson, stated plainly for next
    time: **copy before you restore, every time, no exceptions** — checking
    out a clean version and overwriting an unsaved one is functionally
    identical to deleting it, even though no `rm` was involved.

## The final number

`9-extension-final.json`/`.md`, run after both the `resolve_country` fix (#18)
and the `EvalLock` fix (#22), lock-protected and confirmed uncontaminated
(the two cases that had shown contamination signatures — the Reykjavik/Chiang
Mai mix-up and the departure case with no departure logic — both pass cleanly
in this run):

**27/27 (100%), every case passing all 3 repeated runs, 81/81 individual
attempts passing.**

The full extension eval evidence trail, kept in full rather than trimmed to
just this final number:

| File | Score | Status |
|---|---|---|
| `6-extension-v1.md` | 23/27 | single run, before repeat-mode existed |
| `5-extension-repeat3.md` | 26/27 | clean; its one flaky case led to fix #18 |
| `7-extension-repeat3-run2-COLLISION-CONTAMINATED.md` | 20/27 | invalid — decision #22 |
| `8-extension-final-run3-COLLISION-CONTAMINATED.json`/`.md` | 19/27 | invalid — decision #22 |
| `9-extension-final.json`/`.md` | **27/27** | **clean, lock-protected — cite this one** |

---

# Phase 3 — the onboarding and trip-profile rework

Prompted by using the app rather than by a failing test: the first thing a new
account saw was a chat window interviewing it, and the trip profile was a single
form that could not edit the two lists it was supposedly about.

## 23. Onboarding became a page of fixed questions, not a conversation

The conversational agent was deleted; the extractor kept and specialised per
question. Full reasoning in
[01-agent-architecture.md](01-agent-architecture.md) (the epilogue to the
two-agent split) and [docs/EXTENSION.md](../docs/EXTENSION.md) section 2. The
short version: splitting the agent in two was the right fix for the bug it was
aimed at, but nobody had re-examined whether the conversational half needed a
model at all. It did not, and removing it made the feature faster, more
predictable, and for the first time properly testable.

## 24. The three preference scales went from three points to five

`hot` was covering both a Thai beach in March and a Nepali hill town in October.
The new scales are supersets of the old ones — every value seeded anywhere in the
suite still normalises to itself — and free text maps onto them in Python rather
than being rounded by the model. See [02-memory-and-schema.md](02-memory-and-schema.md).

## 25. Negated preferences are inverted or dropped, never matched on their keyword

"I hate the heat" and "I love the heat" share a keyword. Storing the first as
`hot` is the worst single thing this code could do to a profile, so a negated
match inverts for climate and drops for budget and pace, where inverting would
itself be a guess.

## 26. Passports became a table; `nationality` mirrors the primary

A dual national was previously quoted the harder of their two options. The mirror
is what made this cheap: nothing written against `nationality` had to change.

## 27. Ratings were promoted from a stored field to a prompt-level signal

They were already being collected and were barely being used. They are now split
into liked/lukewarm/disliked in the prompt block with an explicit instruction to
generalise from them — which is what makes "you did not enjoy Hanoi, so here is
why Ho Chi Minh City will or will not land differently" possible at all.

## 28. Two bugs the new evals and tests caught immediately

**`set_social_style` silently did nothing for a brand-new account.** It wrote
with a bare `UPDATE trip_profile`, which matches no rows and reports no error
when the profile row does not exist yet — which is every account arriving at
onboarding. The eval case captured budget, pace and interests correctly and lost
only "solo". `set_interests`' mirror into the text column had the same shape.
Both now call `ensure_profile` first.

That failure mode is worth naming: **a bare `UPDATE` is a silent no-op, not an
error.** It is the third time in this codebase a write has failed by matching
zero rows and saying nothing about it (see also the no-op audit-write bug and the
`update_profile` clearing no-op in note 02).

**A revisit was being dropped.** "I'd go back to Koh Tao in a heartbeat" was
filed as history — where Koh Tao already was — and never reached the wishlist,
losing the only intent in the sentence. Fixed with per-question extractor rules,
which is the concrete payoff of building the extractor per question rather than
once.

## 29. Somewhere already visited can be wishlisted

`add_wishlist` used to refuse it outright with `reason: "already visited"`.
Wanting to go back somewhere is one of the most common things a long-term
traveller says, and refusing it silently dropped real intent. It is accepted now
and flagged as `revisit`, so the UI shows a "going back" badge and the agents can
still tell the two apart. The test that asserted the refusal was inverted rather
than deleted, so the new rule is pinned as deliberately as the old one was.

---

# Phase 4 — bug reports from actually using the app, plus two new features

Six numbered issues reported directly from use: markdown rendering literally,
a hallucinated passport, trip dates nobody wanted, an unreachable nav on
Preferences, and a wrong place inserted mid-route. Each was reproduced against
the real model or over real HTTP before being called fixed - repro scripts are
referenced inline below rather than kept in the repo.

## 30. A phantom "Thailand" entry landing mid-route was an order_index collision, not a fluke

Reported: answering the route question with "Melbourne, Sydney, Cairns, Bali,
Chiang Mai" produced a stored route of "Melbourne, Thailand, Sydney, Cairns,
Bali, Chiang Mai" - a country-level entry appearing at position 2, matching
nothing the traveller actually typed.

**Reproduction, not guessing.** The route question alone, repeated 12 times
(two phrasings x 6), never reproduced it. The real trigger was the "timing"
question ("when did this trip start/end, is anything expiring?"): a natural
answer to it restates the current location ("nothing expiring, I'm in Chiang
Mai") and, 6/6 in testing, the extractor captured THAT as a fresh
`travel_history` entry too - a question with no business writing to that field
at all.

**Why it landed in the MIDDLE, not just as a duplicate.** `apply_capture`
computed `order_index` per extractor call, either from the model's own
`"order"` field or from the entry's position within that one call's array -
never from what was already stored. The route question's own call had already
written Melbourne at `order_index=1`. The timing question's call, being a
single-entry array, also produced `order_index=1`. Sorting is
`ORDER BY order_index ASC, id ASC`: Melbourne (lower id) sorts first, the
phantom entry (higher id, tied order) sorts second - directly producing
"Melbourne, Thailand, Sydney...".

**The fix is two-layered, on purpose:**

1. **A hard code-level scope gate.** `apply_capture` now takes a `step_id` and
   discards `travel_history` entirely unless `step_id == "route"` (and
   similarly gates `wishlist` to `{route, wishlist}` and `passports` to
   `passports` only - see #31). This is enforced in Python regardless of what
   the model returns, which is the stronger of the two fixes: a prompt
   instruction reduces a bad extraction, a code gate makes the class of bug
   impossible.
2. **`order_index` is rebased on the current stored max**, not restarted at 1
   per call. Even a future extractor bug that DID leak an entry through would
   now append it at the END of the route, not splice it into the middle - a
   far smaller, more visible mistake.

The schema's own JSON example was also de-leaked: it used real values
(`"Koh Tao"`, `"Thailand"`, `order: 2`) which a small model can partially copy
verbatim rather than treating as shape-only. It now uses "Example City" /
"Example Country". Whether that specific mechanism ever fired could not be
confirmed either way, but there was no reason to leave a plausible-looking real
answer sitting in the prompt once the risk was named.

See `test_only_the_route_question_may_write_travel_history` and
`test_new_history_entries_always_continue_the_stored_route` in
`tests/test_travel_and_places.py`.

## 31. A passport hallucinated from "I started my trip in Australia"

Reproduced directly: answering the PASSPORTS question with "I started my trip
in Australia, then went to Bali, and now I'm in Chiang Mai" produced
`passports: ["Australia"]` 2/6 times - the model treating a stated starting
point as a citizenship claim. Two layers again:

- The extractor prompt now says explicitly not to infer a passport from
  anywhere the traveller started, is visiting, or is currently in.
- `apply_capture`'s code-level gate (above) restricts passport writes to the
  `passports` step only, so even a full prompt regression could not resurrect
  this on the route, timing, wishlist or style questions.

6/6 clean after the fix (`test_only_the_passports_question_may_write_passports`).

## 32. `trip_start_date` / `trip_end_date` removed from the app entirely

Requested directly: they added little (an end date is usually a soft
flight-out guess, not a hard fact) and the base-app turn parser kept inventing
them mid-conversation. Removed from `PROFILE_FIELDS`, the onboarding schema,
both agent prompts, both frontend forms, and the seeded demo profile. The
columns stay in SQLite (dropping a column is a bigger migration than this
warrants) but nothing reads or writes them; `get_profile()` no longer surfaces
them at all. The `travel_month` fallback that used to read `trip_start_date`
now falls back straight to `date.today()`, which is arguably a better default
regardless.

## 33. "Forget everything" only wiped the base-app tables

Found while building the memory debug page, not reported directly:
`forget_account_memory` deleted `conversation_turns`, `visited_history`,
`trip_profile` and `passports`, but never touched `travel_history`, `wishlist`,
`user_interests`, `recommendation_feedback` or `onboarding_state` - the entire
extension. A user who read "erase everything Travel Steezy remembers about
your trip" and clicked it would have kept their whole route, wishlist,
ratings and interests, and would not even have been sent back through
onboarding. Fixed by adding those tables (plus `memory_writes` itself - the
audit log is account data too, so a genuine forget clears it, leaving only the
one entry recording that the forget happened).

## 34. The chat bubble rendered markdown literally

The assistant's replies are prompted for and genuinely contain markdown -
bold, bullet lists - which showed as literal asterisks and dashes. Fixed with
a small `Markdown.vue` component (`marked` + DOMPurify, since this is
ultimately LLM-sourced `v-html`), applied to the chat bubble and to every
LLM-authored field on the destination cards (rationale, pros/cons, backpacker
notes, cost note). The user's own typed messages are deliberately NOT run
through it - they stay literal plain text.

## 35. The top nav scrolled away on any page taller than one screen

Preferences (now three panels, one of them a raw table on the memory page) is
often taller than the viewport, and the header was a normal in-flow element -
on a window-level scroll it went with the rest of the page, leaving no way
back to Chat without scrolling up first. Fixed with `position: sticky; top: 0`
on the header. Also added a `Memory` link, since a third real page existed
with no way to reach it.

## 36. Two new pages: Memory (debug) and the catch-up card

**Memory** (`/memory`, `GET /memory/me`) shows exactly what gets fed into the
next agent prompt - `memory_block` and `travel_block`, rendered live by the
same two functions a real turn calls, not a paraphrase - plus every raw row
(including deprecated columns, interest weights, the onboarding answered-list)
and per-row/per-field deletion. It also fetches, by deterministic id, which of
an account's reviews have actually reached the shared RAG experience store,
rather than trusting what was submitted.

**Catch-up** ("here's where we left off - what's changed?") fires once per
calendar-day gap since the account's last real chat turn, tracked by a plain
date column (`trip_profile.last_active_date`) touched inside `run_turn`. It is
deliberately NOT a repeat of the first onboarding design's mistake: one fixed
card, cleared either by free text (which runs through the ordinary `run_turn`
pipeline - it IS a normal turn, so visits/wishlist/reviews are picked up for
free) or a one-tap "still here" button with no model call at all.

**A bug found by the smoke test, not by inspection**: `touch_last_active` was
originally placed AFTER `run_turn`'s `if not settings.llm_enabled: return
_llm_disabled_response(...)` early exit, so answering the catch-up card while
the LLM was unavailable never actually cleared the prompt - a real gap between
"the user came back and told us something" and "the app noticed." Moved before
the check; a turn counts as activity regardless of whether the LLM path
succeeds.

## Open items at the time of writing

- Railway deployment, the demo-safety account decision (seeded demo account
  vs. `ADMIN_AUTO_APPROVE`), and the backup screen recording remain outstanding
  from the original build — unrelated to the extension, carried over from
  before it started.
