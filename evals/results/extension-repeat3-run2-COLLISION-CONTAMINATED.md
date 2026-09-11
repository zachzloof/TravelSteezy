<!--
CONTAMINATED RESULT — kept as evidence of a real testing-infrastructure bug,
not as a reading of the app's actual behaviour. Do not use this score.

What happened: two eval-suite processes ran concurrently against the same
SQLite database, sharing the same two fixed eval accounts (__eval_account_a,
__eval_account_b). One run's per-case `forget_account_memory` + reseed landed
mid-turn for the other run, so turns in this run sometimes answered using a
profile seeded by the OTHER run's case. Visible directly in the "Failing
cases" section below: `discovery-honest-about-unknown-origin` (seeded with
Reykjavik/Iceland) answers about Chiang Mai and Pai — a location that belongs
to a different case entirely.

Root cause: an earlier belief that the first of two `--label extension-repeat3
--repeat 3` runs had died (after a `/model` switch mid-session) was wrong — it
had kept running in the background the whole time. A second run was started
against the same database without checking for this. See
notes/06-eval-methodology.md and notes/08-decisions-log.md for the full story,
and evals/run_evals.py's `EvalLock` for the fix (a run now refuses to start
while another one holds the lock).

Recovery note: the raw .json for this specific run was overwritten (a
`git checkout` used to restore an earlier committed result clobbered this
file before a copy was saved) and could not be recovered. This .md is
reconstructed verbatim from the assistant's own tool output earlier in the
session that produced it, which is why it has no matching .json sibling.
-->

# Eval run `extension-repeat3` (SECOND run — CONTAMINATED by a concurrent collision)

- **Score:** 20/27 (74%), passing all 3 runs — **NOT A VALID READING OF APP BEHAVIOUR**
- **Run id:** `eval-20260911T191920Z-9f36c8` (Langfuse tag)
- **Timestamp:** 2026-09-11T19:32:48.712110+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | FLAKY (2/3) |
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | PASS (3/3) |
| `visa-nationality-aware` | ignores a visa deadline that should rule out or flag a destination | PASS (3/3) |
| `visa-deadline-surfaced` | ignores a visa deadline that should rule out or flag a destination | PASS (3/3) |
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | FLAKY (1/3) |
| `rag-cites-source` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `memory-no-repeat-budget` | failing to use the trip profile | PASS (3/3) |
| `memory-respects-explicit-preference` | failing to use the trip profile | PASS (3/3) |
| `memory-recall-accurate` | failing to use the trip profile | FLAKY (2/3) |
| `memory-writes-departure` | failing to use the trip profile | FLAKY (2/3) |
| `memory-persists-fresh-session` | memory persisting across a fresh session | PASS (3/3) |
| `isolation-cross-account` | cross-account isolation | PASS (3/3) |
| `isolation-endpoint-scoping` | cross-account isolation | PASS (3/3) |
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `route-overland-vs-flight` | failing to use the trip profile | PASS (3/3) |
| `onboarding-captures-structured-history` | onboarding fails to capture structured profile | FLAKY (1/3) |
| `tracking-promotes-wishlist-to-history` | live trip tracking does not fire | PASS (3/3) |
| `tracking-ignores-mere-curiosity` | live trip tracking does not fire | PASS (3/3) |
| `review-captured-and-stored` | post-visit review not captured | PASS (3/3) |
| `review-prompt-fires-after-departure` | post-visit review not captured | PASS (3/3) |
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | FLAKY (2/3) |
| `discovery-honest-about-unknown-origin` | generic tourist advice instead of backpacker-specific advice | FLAKY (1/3) |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |

Each case ran 3 times. A case counts as passing only if it passed every run; 88% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture. **On top of that ordinary noise, this specific run was ALSO corrupted by a concurrent second process sharing the same eval database — see the file header above.**

## Failing cases

### `season-malaysia-east-coast-closed` - Knows Perhentians shut in the northeast monsoon

> I recommend avoiding both the Perhentian Islands in Malaysia and Indonesia for December due to unfavorable weather conditions. December is monsoon season for the Perhentian Islands, and the same applies to Indonesia, where the wet season peaks in January and February. If you were to choose between them, Malaysia has an entry visa-free for 90 days, requiring only the Malaysia Digital Arrival Card,

### `rag-backpacker-not-tourist` - Gives backpacker advice, not brochure tourism
- Failed `judge`: judge score 3/5 - While the assistant provides some budget details and warnings, it primarily focuses on advising against travel due to weather rather than offering actionable advice for budget backpackers.

> Given the current weather conditions for September, I recommend you avoid both Vietnam and Laos for now. Both countries are rated as 'avoid' due to heavy rains and potential travel disruptions. For context, in Vietnam, the daily budget is approximately USD 20-25, and for Laos, it's around USD 18-25. While Vietnam has amazing motorbiking routes like the Ha Giang Loop, and Laos offers beautiful spot

### `memory-recall-accurate` - Recalls stored profile accurately without inventing
- Failed `reply_mentions_any`: matched=[]

> You're currently in Malaysia, traveling with a mid-range budget and a fast pace. Your trip starts on June 1, 2026, and you enjoy street food and diving. I don't have any recorded route or wishlist yet. If you’d like to add more details or preferences, you can do that in the My Preferences screen.

### `memory-writes-departure` - Writes a departure to history and archives active context

> Given your current situation in Thailand, I recommend embracing your time here despite the wet season. Both Thailand and Laos are experiencing unfavorable conditions in September, hence the choice is a bit constrained. You can expect to spend around 700-1,000 THB (approximately £15-20) daily which covers dormitory accommodation, street food, and local transport. As for transit, traveling from Bang

### `onboarding-captures-structured-history` - Onboarding captures route, wishlist and preferences as structured data
- Failed `history_contains`: history=[], missing=['bangkok', 'koh tao', 'chiang mai']
- Failed `history_ordered`: history order=[]
- Failed `wishlist_contains`: wishlist=[], missing=['pai']
- Failed `interests_contain_any`: interests=[], matched=[]

> That's right! You have a shoestring budget, are traveling solo and slowly, and are interested in nature, trekking, and street food. If you’d like to add more details to your profile, feel free to check the My Preferences screen.

**^ This is the clearest contamination signature in the file.** The checks say
`history=[]` (nothing was ever written), but the reply confidently confirms
budget/pace/interests that must have come from a DIFFERENT case's setup
bleeding into this one via the shared account row.

### `discovery-uses-route-corpus` - Where-next-from-here uses the city-level route corpus

> Here are some great options for your next destination from Chiang Mai:
>
> 1. **Pai**
>    - **Journey**: About 3 hours north by minibus (around 150-200 THB).
>    - **Why**: A small hippie town in a valley, Pai is great for trekking and offers stunning scenery. Many travelers plan a short stay but end up lingering longer.
>    - **Feedback**: Positive feedback highlights Pai as "brilliant" with attraction

### `discovery-honest-about-unknown-origin` - Admits it has no route data for an uncovered origin
- Failed `judge`: judge score 1/5 - The assistant confidently provided specific onward destinations and journey details despite having no route knowledge for the traveler's location in Iceland.

> From Chiang Mai, here are your best options for your next destination:
>
> 1. **Pai**
>    - **Journey**: About 3 hours north by minibus.
>    - **Cost**: Approximately 150-200 THB.
>    - **Overview**: A small hippie town in a beautiful valley, popular for its laid-back atmosphere and stunning sunset views at the canyon. Many backpackers plan to stay for just two nights but often end up extending their st

**^ The second clearest contamination signature.** This case's setup seeds the
traveller in Reykjavik, Iceland. The reply is entirely about Chiang Mai and
Pai — Thailand — which is impossible unless this turn's account row was
overwritten mid-run by a different case (one of the Chiang Mai/Pai discovery
cases) executing concurrently in the other process.
