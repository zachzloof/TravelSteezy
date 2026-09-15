# Eval run `41-final-after-all-fixes`

- **Score:** 38/39 (97%)
- **Run id:** `eval-20260915T133903Z-1456bf` (Langfuse tag)
- **Timestamp:** 2026-09-15T13:49:21.550429+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
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
| `visa-vietnam-lead-time` | ignores a visa lead time that should rule out or flag a destination | PASS |
| `visa-nationality-aware` | ignores nationality-specific visa guidance | PASS |
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | PASS |
| `rag-cites-source` | generic tourist advice instead of backpacker-specific advice | PASS |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | FAIL |
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
| `discovery-honest-about-unknown-origin` | invents onward destinations, journey times or prices for an uncovered origin with no real search behind them | PASS |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS |
| `route-live-lookup-uncurated-pair` | invents a journey time or cost for an uncurated pair with no real search behind it | PASS |
| `scope-country-question-answered-with-countries` | answering a country-level question at town level | PASS |
| `scope-visa-expiry-forces-a-country-answer` | answering a country-level question at town level | PASS |
| `tracking-ignores-a-hypothetical-departure` | writing memory the user did not actually state | PASS |
| `tracking-does-not-relocate-you-on-a-placeless-turn` | writing memory the user did not actually state | PASS |

## Failing cases

### `rag-budget-numbers` - Quotes realistic daily budget numbers from the store
- Failed `retrieval_fired`: namespaces retrieved=['seasonal']
- Failed `reply_matches_regex`: match=None

> Given your shoestring budget and the fact that you're traveling slowly, both Laos and Cambodia aren't ideal under current conditions due to the wet season. While I don't have specific daily budget figures for this request, due to the wet and potentially problematic weather mentioned, it would be wise to consider another destination for now. September is the rainiest month for both, with road trave

