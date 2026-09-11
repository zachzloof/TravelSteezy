<!--
CONTAMINATED RESULT — kept as evidence of a real testing-infrastructure bug,
not as a reading of the app's actual behaviour. Do not use this score.

This run (label "extension-final", run_id eval-20260911T192438Z-c79ca9)
overlapped for most of its lifetime with the run preserved as
extension-repeat3-run2-COLLISION-CONTAMINATED.md — both processes shared the
same two fixed eval accounts (__eval_account_a/b) in the same SQLite database
at the same time. Same signature as that file: `memory-writes-departure`
returns a generic "stay in Thailand" reply with no departure logic at all, and
`onboarding-captures-structured-history` reads mid-onboarding-completion state
that belongs to a different case's turn.

See notes/06-eval-methodology.md and notes/08-decisions-log.md for the full
story, and evals/run_evals.py's EvalLock for the fix — a run now refuses to
start while another one holds the lock. The matching raw
extension-final-run3-COLLISION-CONTAMINATED.json is the real, unmodified
output file for this run, copied before extension-final.json/.md were
overwritten by the clean, lock-protected re-run.
-->

# Eval run `extension-final` (THIRD run — CONTAMINATED by a concurrent collision)

- **Score:** 19/27 (70%), passing all 3 runs — **NOT A VALID READING OF APP BEHAVIOUR**
- **Run id:** `eval-20260911T192438Z-c79ca9` (Langfuse tag)
- **Timestamp:** 2026-09-11T19:37:24.407485+00:00
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
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | FLAKY (2/3) |
| `rag-cites-source` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `memory-no-repeat-budget` | failing to use the trip profile | FLAKY (2/3) |
| `memory-respects-explicit-preference` | failing to use the trip profile | FLAKY (2/3) |
| `memory-recall-accurate` | failing to use the trip profile | PASS (3/3) |
| `memory-writes-departure` | failing to use the trip profile | FLAKY (1/3) |
| `memory-persists-fresh-session` | memory persisting across a fresh session | PASS (3/3) |
| `isolation-cross-account` | cross-account isolation | PASS (3/3) |
| `isolation-endpoint-scoping` | cross-account isolation | PASS (3/3) |
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `route-overland-vs-flight` | failing to use the trip profile | PASS (3/3) |
| `onboarding-captures-structured-history` | onboarding fails to capture structured profile | FLAKY (1/3) |
| `tracking-promotes-wishlist-to-history` | live trip tracking does not fire | FLAKY (1/3) |
| `tracking-ignores-mere-curiosity` | live trip tracking does not fire | PASS (3/3) |
| `review-captured-and-stored` | post-visit review not captured | FLAKY (2/3) |
| `review-prompt-fires-after-departure` | post-visit review not captured | PASS (3/3) |
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `discovery-honest-about-unknown-origin` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |

Each case ran 3 times. A case counts as passing only if it passed every run; 86% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.

## Failing cases

### `season-malaysia-east-coast-closed` - Knows Perhentians shut in the northeast monsoon

> I recommend heading to **Indonesia** this December, primarily due to accessibility and your budgetary considerations. While both destinations face weather challenges, Indonesia offers a vibrant backpacker scene with a realistic daily budget of **USD 22-30**. To get there from Thailand, you can find flights from Bangkok to Bali that take about **4 hours** and cost roughly **USD 120-220**, although 

### `rag-backpacker-not-tourist` - Gives backpacker advice, not brochure tourism

> Both Vietnam and Laos are currently rated as 'avoid' for September due to heavy rain and unfavorable travel conditions, which affects your travel pace as a slow backpacker focusing on budget experiences. However, given your budget band of shoestring and current location in Cambodia, Laos presents an intriguing option with a daily budget of $18-25 alongside unique cultural experiences. You can enjo

### `memory-no-repeat-budget` - Does not ask for a budget it already stores

> I recommend heading to **Thailand** as your next destination. It's a better fit for your shoestring budget and travel pace, particularly since you are currently in Laos and can easily cross into Thailand visa-free for **60 days**. Expect to spend around **700-1,000 THB** (approximately £15-20) per day, which includes dorm accommodation and local food. Your trip dates from **November 5 to December 

### `memory-respects-explicit-preference` - Respects an explicitly set preference over a generic pick

> I recommend heading to Nepal as your next destination due to the excellent trekking conditions in November, which perfectly align with your interests in hiking and cool weather. The cost of the visa on arrival is USD 30 for 15 days, or USD 50 for 30 days, and the flight from Bangkok to Kathmandu takes about 3 hours and costs between USD 180-300. Considering your budget band and slow travel pace, y

### `memory-writes-departure` - Writes a departure to history and archives active context

> I recommend you stay in Thailand since you're currently there, and it's a great time for outdoor activities. With a daily budget of around 700-1,000 THB ($20-$30), you'll find plenty of affordable options for dorm accommodation and local street food. You can explore Chiang Mai's temples or enjoy beautiful hiking trails at Doi Suthep. Considering your shoestring budget and slow travel pace, you can

### `onboarding-captures-structured-history` - Onboarding captures route, wishlist and preferences as structured data

> Great to hear you're into nature, trekking, and street food! Since you've shared your budget and travel style, could you let me know where your trip started?
> 
> You can change any of this any time in My Preferences. Ask me where to go next whenever you are ready.

### `tracking-promotes-wishlist-to-history` - Saying you are somewhere logs the visit and clears it from the wishlist

> Welcome to Pai! For your stay here, I recommend basing yourself in **Around Tambon Wiang Tai** or **Around Tambon Mae Hi**, both areas have solid accommodation options and a good vibe.
> 
> ### Where to Stay:
> 1. **Topp Stay Hostel** - Rating: 4.8 (123 reviews) [Location](https://maps.google.com/?cid=3225700185599337424&g_mp=Cidnb29nbGUubWFwcy5wbGFjZXMudjEuUGxhY2VzLlNlYXJjaFRleHQQAhgEIAA)
> 2. **Cody Bac

### `review-captured-and-stored` - A post-visit review is stored against the history entry

> Yes, you rated Pai a 5 out of 5! You mentioned that the canyon at sunset is free and unreal. If there's anything specific you'd like to discuss or explore next, let me know!

