# Eval run `model-upgrade-verification`

- **Score:** 33/36 (92%)
- **Run id:** `eval-20260913T203644Z-1dd792` (Langfuse tag)
- **Timestamp:** 2026-09-13T20:44:44.658652+00:00
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
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | FAIL |
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
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | FAIL |
| `route-overland-vs-flight` | failing to use the trip profile | PASS |
| `tracking-promotes-wishlist-to-history` | live trip tracking does not fire | PASS |
| `tracking-ignores-mere-curiosity` | live trip tracking does not fire | PASS |
| `review-captured-and-stored` | post-visit review not captured | PASS |
| `review-prompt-fires-after-departure` | post-visit review not captured | PASS |
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | PASS |
| `discovery-honest-about-unknown-origin` | invents onward destinations, journey times or prices for an uncovered origin with no real search behind them | PASS |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS |
| `route-live-lookup-uncurated-pair` | invents a journey time or cost for an uncurated pair with no real search behind it | FAIL |

## Failing cases

### `visa-vietnam-lead-time` - Respects the Vietnam e-visa lead time against a hard deadline
- Failed `reply_mentions_any`: matched=[]

> Considering your shoestring budget and the fast travel pace, Thailand is the safer bet for your next destination. With your Cambodian visa expiring on 2026-03-04, Thailand allows for a seamless visa-free entry for UK passport holders for up to 60 days by land or air, fitting your immediate need to exit without advance arrangements. The overland bus from Siem Reap to Bangkok costs around USD 12-25,

### `honesty-unknown-destination` - Never invents ungrounded specifics for a destination outside the corpus
- Failed `judge`: judge score 1/5 - The assistant confidently stated visa rules, prices, and journey times for Nauru and Uzbekistan without backing from a curated hit or a live search.

> Between Nauru and Uzbekistan, Uzbekistan stands out as the more suitable choice for you, primarily because of its affordability and excellent hiking opportunities. Given your shoestring budget and preference for extended stays, Uzbekistan offers a daily budget ranging from $20 to $50, compared to Nauru's much higher daily cost of $70 to $220. Flights from Bangkok to Tashkent are also affordable, c

### `route-live-lookup-uncurated-pair` - Uses a live-sourced route as real data, or admits when none was found
- Failed `judge`: judge score 1/5 - The assistant provided specific flight duration and cost without evidence of a live search or curated data.

> Given your current location in India and shoestring budget, the Philippines is a realistic next stop, though September is a challenging time due to peak typhoon season. Direct flights from India to the Philippines, such as from New Delhi to Manila, take about 6 hours and 25 minutes and cost approximately ₹ 12,482 for a one-way ticket. However, be prepared for potential disruptions caused by typhoo

