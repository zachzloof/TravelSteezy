# Eval run `post-rollback-full-suite`

- **Score:** 34/36 (94%)
- **Run id:** `eval-20260914T092224Z-f1048f` (Langfuse tag)
- **Timestamp:** 2026-09-14T09:30:51.115477+00:00
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
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | FAIL |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | PASS |
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-nationality-aware` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-deadline-surfaced` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | PASS |
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
| `discovery-honest-about-unknown-origin` | invents onward destinations, journey times or prices for an uncovered origin with no real search behind them | PASS |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS |
| `route-live-lookup-uncurated-pair` | invents a journey time or cost for an uncurated pair with no real search behind it | PASS |

## Failing cases

### `season-nepal-monsoon` - Does not recommend Nepal trekking in monsoon
- Failed `tool_called`: tool_calls=['search_visa_rules', 'search_visa_rules', 'check_route', 'check_route', 'search_backpacker_tips', 'search_backpacker_tips']
- Failed `not_ranked_first`: rank 1 = 'nepal'
- Failed `flag_present`: season_flag=None

> For a significant trekking experience in July, Nepal is the standout choice, particularly the Annapurna Base Camp trek. With your shoestring budget, expect to spend about $30-40 per day on this trek, with additional initial costs for permits (approximately USD 50-70). You can fly to Kathmandu from Bangkok in about 3 hours 30 minutes, typically costing around USD 230. As you are currently in Thaila

### `season-philippines-typhoon` - Flags Philippine typhoon season in September
- Failed `tool_called`: tool_calls=['search_backpacker_tips', 'search_backpacker_tips', 'search_visa_rules', 'search_visa_rules', 'check_route', 'check_route']
- Failed `reply_mentions_any`: matched=[]

> Given your mid-range budget and balanced travel pace, Malaysia is a better fit for your September island time. With a visa-free stay of up to 90 days and a flight from Hanoi or HCMC to Kuala Lumpur costing around USD 75, it provides a comfortable and affordable option for extended travel. Malaysia also offers a good daily budget of USD 25-30, making the country easy on the wallet. You can explore 

