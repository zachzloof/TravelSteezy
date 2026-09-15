# Eval run `38-after-bug3-fixes`

- **Score:** 37/39 (95%)
- **Run id:** `eval-20260915T132221Z-b4a7b6` (Langfuse tag)
- **Timestamp:** 2026-09-15T13:34:10.626129+00:00
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
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | FAIL |
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

### `season-nepal-monsoon` - Does not recommend Nepal trekking in monsoon
- Failed `tool_called`: tool_calls=['search_backpacker_tips', 'search_backpacker_tips']
- Failed `not_ranked_first`: rank 1 = 'nepal'
- Failed `flag_present`: season_flag=None

> I recommend Nepal for your big trek in July, particularly since your key interest is mountains and trekking. Despite being in Thailand, making a move to Nepal fits well with your shoestring budget of USD 20-25 per day in major spots like Kathmandu and Pokhara, and offers more serious trekking options like the Annapurna Base Camp Trek (7-12 days) that align with your interests. High-altitude treks 

### `rag-budget-numbers` - Quotes realistic daily budget numbers from the store
- Failed `retrieval_fired`: namespaces retrieved=['visa']

> For your shoestring budget and slow travel pace, I'd recommend heading to Cambodia. You can budget around USD 25-35 per day in Cambodia, which is slightly lower than Laos, where you should plan for about USD 30-40 per day. Considering your interests in food and temples, Cambodia has much to offer in terms of notable temple sites like Angkor Wat. Since you're currently in Thailand and planning trav

