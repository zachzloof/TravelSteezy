# Eval run `bugfix-round-truly-final`

- **Score:** 33/35 (94%)
- **Run id:** `eval-20260912T113814Z-ea8a37` (Langfuse tag)
- **Timestamp:** 2026-09-12T11:42:26.934350+00:00
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
| `memory-no-repeat-budget` | failing to use the trip profile | FAIL |
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
- Failed `judge`: judge score 3/5 - The advice includes some budget details and travel logistics but lacks specific recommendations for budget backpackers and does not sufficiently address overland transport options or safety warnings relevant to their travel style.

> I recommend Laos for your three-week trip because the visa on arrival is convenient and there are beautiful natural landscapes to explore. You can expect to budget around USD 18-25 per day here. In Laos, embark on a Mekong Slow Boat journey from Huay Xai to Luang Prabang, which takes about two days at a cost of around USD 35. Currently, you are in Cambodia and might face challenges in Vietnam duri

### `memory-no-repeat-budget` - Does not ask for a budget it already stores
- Failed `judge`: judge score 1/5 - The assistant asks for budget information by stating 'Expect daily costs around 700-1,000 THB' without using the stored context of the traveller's budget.

> I recommend heading to Thailand as your next destination. The main reason is that you can enter visa-free for up to 60 days, which fits well with your current situation in Laos. In terms of budget, expect to spend around 700-1,000 THB (approximately £17-£25) per day covering dorm beds and street food. You're currently in Laos, and with your pace in mind, overland travel to Thailand will be cheaper

