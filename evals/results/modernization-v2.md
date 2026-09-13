# Eval run `modernization-v2`

- **Score:** 32/35 (91%)
- **Run id:** `eval-20260913T115400Z-4873dd` (Langfuse tag)
- **Timestamp:** 2026-09-13T11:58:18.819349+00:00
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
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | FAIL |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | PASS |
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-nationality-aware` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-deadline-surfaced` | ignores a visa deadline that should rule out or flag a destination | PASS |
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
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | FAIL |
| `route-overland-vs-flight` | failing to use the trip profile | PASS |
| `tracking-promotes-wishlist-to-history` | live trip tracking does not fire | PASS |
| `tracking-ignores-mere-curiosity` | live trip tracking does not fire | PASS |
| `review-captured-and-stored` | post-visit review not captured | PASS |
| `review-prompt-fires-after-departure` | post-visit review not captured | PASS |
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | PASS |
| `discovery-honest-about-unknown-origin` | generic tourist advice instead of backpacker-specific advice | PASS |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS |

## Failing cases

### `season-philippines-typhoon` - Flags Philippine typhoon season in September
- Failed `tool_called`: tool_calls=['search_backpacker_tips', 'search_backpacker_tips']
- Failed `not_ranked_first`: rank 1 = 'philippines'
- Failed `reply_mentions_any`: matched=[]

> I recommend the Philippines for your September island time primarily due to its stunning diving and island adventures. Expect a daily budget of around USD 25-35, slightly higher than Malaysia, but the unique island hopping experiences, especially in El Nido and Coron, are a must. Both countries are great, but the Philippines aligns better with your interests in diving and islands. Currently, you'r

### `rag-budget-numbers` - Quotes realistic daily budget numbers from the store
- Failed `retrieval_fired`: namespaces retrieved=['visa']

> I recommend Cambodia for your budget and interests, as it offers a lower daily budget range. You should budget about **USD 25-45** a day in Cambodia, while in Laos, the estimate rises to **USD 30-50**. Since you're currently in Thailand and have a shoestring budget, you'll appreciate that the overland travel from Thailand to Cambodia via bus costs **USD 12-25** and takes **8-9 hours**, making it t

### `honesty-unknown-destination` - Admits when it has no verified data for a destination
- Failed `judge`: judge score 1/5 - The assistant confidently stated invented specifics about visa rules and budget data for both Nauru and Uzbekistan without a clear upfront admission of lacking verified data.

> I recommend heading to Uzbekistan as your top choice. It offers a significantly lower daily budget compared to Nauru, around $20 to $30 USD, with dorm prices between $5-10. Your current position in Thailand and shoestring budget makes Uzbekistan a better fit for long-term travel since it allows you to explore rich culture and hiking opportunities without breaking the bank. Even though there's no v

