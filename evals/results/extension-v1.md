# Eval run `extension-v1`

- **Score:** 23/27 (85%)
- **Run id:** `eval-20260911T182727Z-49fe9f` (Langfuse tag)
- **Timestamp:** 2026-09-11T18:31:19.865834+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | PASS |
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-nationality-aware` | ignores a visa deadline that should rule out or flag a destination | FAIL |
| `visa-deadline-surfaced` | ignores a visa deadline that should rule out or flag a destination | FAIL |
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | FAIL |
| `rag-cites-source` | generic tourist advice instead of backpacker-specific advice | PASS |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | PASS |
| `memory-no-repeat-budget` | failing to use the trip profile | PASS |
| `memory-respects-explicit-preference` | failing to use the trip profile | PASS |
| `memory-recall-accurate` | failing to use the trip profile | FAIL |
| `memory-writes-departure` | failing to use the trip profile | PASS |
| `memory-persists-fresh-session` | memory persisting across a fresh session | PASS |
| `isolation-cross-account` | cross-account isolation | PASS |
| `isolation-endpoint-scoping` | cross-account isolation | PASS |
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | PASS |
| `route-overland-vs-flight` | failing to use the trip profile | PASS |
| `onboarding-captures-structured-history` | onboarding fails to capture structured profile | PASS |
| `tracking-promotes-wishlist-to-history` | live trip tracking does not fire | PASS |
| `tracking-ignores-mere-curiosity` | live trip tracking does not fire | PASS |
| `review-captured-and-stored` | post-visit review not captured | PASS |
| `review-prompt-fires-after-departure` | post-visit review not captured | PASS |
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | PASS |
| `discovery-honest-about-unknown-origin` | generic tourist advice instead of backpacker-specific advice | PASS |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS |

## Failing cases

### `visa-nationality-aware` - Uses the stored nationality for visa guidance
- Failed `tool_called`: tool_calls=['search_backpacker_tips', 'search_backpacker_tips']
- Failed `retrieval_fired`: namespaces retrieved=['tips']

> Here's what you need for entering Indonesia and Cambodia:
> 
> ### Indonesia
> - **Visa**: As a New Zealand passport holder, you can enter Indonesia for tourism purposes without a visa for up to 30 days. This can be extended once for another 30 days while in the country.
> - **Requirements**: You might need to show proof of onward travel and sufficient funds for your stay.
> - **Travel Tips**: Daily budget 

### `visa-deadline-surfaced` - Surfaces the stored hard deadline unprompted
- Failed `reply_mentions_any`: matched=[]

> Here are some great options for your next destination from Chiang Mai, especially since you love hiking:
> 
> 1. **Pai**
>    - **Journey**: About 3 hours north by minibus (150-200 THB).
>    - **Who it suits**: This small hippie town in a stunning valley often sees visitors planning just a couple of nights but ending up staying much longer. The nearby canyon at sunset is a must-see, and the vibe is very 

### `rag-backpacker-not-tourist` - Gives backpacker advice, not brochure tourism
- Failed `retrieval_fired`: namespaces retrieved=[]
- Failed `tool_called`: tool_calls=['discover_next_destinations']
- Failed `judge`: judge score 2/5 - While the response includes some budget-related information, it lacks specific hostel or dorm prices, realistic daily budgets, and detailed overland transport options that are crucial for budget backpackers.

> I don't have specific curated route data for your current location in Cambodia, so I can't suggest direct onward destinations for Vietnam or Laos. However, I'll summarize what you can generally expect in those countries based on your interests.
> 
> ### Vietnam
> 1. **Hanoi**: The capital offers cheap street food and is a great base for exploring nearby caves like the fascinating Trang An or Ninh Binh. 

### `memory-recall-accurate` - Recalls stored profile accurately without inventing
- Failed `reply_lacks_regex`: found forbidden 'nepal'

> You're from Ireland and currently in Malaysia. Your travel budget is mid-range, and you have a fast travel pace. Your trip started on June 1, 2026, and while you don't have an end date set yet, you have high-priority destinations including Nepal, Sri Lanka, and the Philippines. You're interested in street food and diving, and your route so far includes Chiang Mai.

