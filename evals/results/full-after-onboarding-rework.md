# Eval run `full-after-onboarding-rework`

- **Score:** 34/35 (97%)
- **Run id:** `eval-20260912T094139Z-cc01a7` (Langfuse tag)
- **Timestamp:** 2026-09-12T09:45:56.905488+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `onboarding-captures-route-with-ratings` | onboarding fails to capture structured profile | PASS |
| `onboarding-maps-plain-english-to-bands` | onboarding fails to capture structured profile | PASS |
| `onboarding-does-not-invert-a-negated-preference` | onboarding stores a preference as its opposite | PASS |
| `onboarding-captures-both-passports` | onboarding fails to capture structured profile | PASS |
| `onboarding-wishlist-allows-a-revisit` | onboarding fails to capture structured profile | PASS |
| `onboarding-scopes-answers-to-the-question-asked` | onboarding stores wanted places as already visited | PASS |
| `onboarding-invents-nothing` | onboarding invents profile data that was never stated | PASS |
| `onboarding-survives-a-non-answer` | onboarding traps the user or writes junk | PASS |
| `onboarding-full-flow-completes` | onboarding fails to capture structured profile | PASS |
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | PASS |
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-nationality-aware` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-deadline-surfaced` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | FAIL |
| `rag-cites-source` | generic tourist advice instead of backpacker-specific advice | PASS |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | PASS |
| `memory-no-repeat-budget` | failing to use the trip profile | PASS |
| `memory-respects-explicit-preference` | failing to use the trip profile | PASS |
| `memory-recall-accurate` | failing to use the trip profile | PASS |
| `memory-writes-departure` | failing to use the trip profile | PASS |
| `memory-persists-fresh-session` | memory persisting across a fresh session | PASS |
| `isolation-cross-account` | cross-account isolation | PASS |
| `isolation-endpoint-scoping` | cross-account isolation | PASS |
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | PASS |
| `route-overland-vs-flight` | failing to use the trip profile | PASS |
| `tracking-promotes-wishlist-to-history` | live trip tracking does not fire | PASS |
| `tracking-ignores-mere-curiosity` | live trip tracking does not fire | PASS |
| `review-captured-and-stored` | post-visit review not captured | PASS |
| `review-prompt-fires-after-departure` | post-visit review not captured | PASS |
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | PASS |
| `discovery-honest-about-unknown-origin` | generic tourist advice instead of backpacker-specific advice | PASS |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS |

## Failing cases

### `rag-backpacker-not-tourist` - Gives backpacker advice, not brochure tourism
- Failed `judge`: judge score 3/5 - While the assistant provides some relevant budget information and travel tips, it lacks a clear focus on budget backpacker logistics and does not sufficiently emphasize overland transport options or specific hostel prices.

> Given your budget of shoestring travel and current location in Cambodia, I recommend focusing on Laos for your three weeks. September is rated as a poor season for both countries, but Laos offers a simpler visa process and stunning landscapes. You'll need USD 30-42 for a visa on arrival, valid for 30 days, and the daily budget is around USD 18-25. You can explore beautiful spots like the slow boat

