# Eval run `python313-litellm-current`

- **Score:** 33/35 (94%)
- **Run id:** `eval-20260913T131049Z-b2aa1a` (Langfuse tag)
- **Timestamp:** 2026-09-13T13:15:04.879307+00:00
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
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | FAIL |
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | PASS |
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-nationality-aware` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-deadline-surfaced` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | PASS |
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

### `season-nepal-monsoon` - Does not recommend Nepal trekking in monsoon
- Failed `tool_called`: tool_calls=['search_backpacker_tips', 'search_backpacker_tips', 'search_visa_rules', 'search_visa_rules', 'check_route', 'check_route']
- Failed `not_ranked_first`: rank 1 = 'nepal'
- Failed `flag_present`: season_flag=None

> I recommend Nepal for your big trek in July because it offers extensive trekking options suited to your interest in mountains. Expect to spend about $20-25 per day in Kathmandu and Pokhara, increasing to $30-40 on trekking routes due to food costs. You can get a visa on arrival for USD 30 (15 days) or USD 50 (30 days), and the flight from Bangkok to Kathmandu takes around 3 hours and costs between

### `memory-no-repeat-budget` - Does not ask for a budget it already stores
- Failed `judge`: judge score 1/5 - The assistant asks for budget information by providing an 'indicative daily budget of around $20', which is unnecessary given the traveller's profile.

> Given the current weather conditions, I recommend postponing both Thailand and Vietnam until a better time, as both are rated 'avoid' in September, aligning with your budget band as a shoestring traveller seeking adventures in Laos. Thailand’s Andaman coast is particularly affected by heavy rain, with cancellations of ferries making travel tough, while Vietnam's central coast faces the risk of typ

