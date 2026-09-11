# Eval run `baseline-before-fix`

- **Score:** 14/19 (74%)
- **Run id:** `eval-20260911T160147Z-6fe60f` (Langfuse tag)
- **Timestamp:** 2026-09-11T16:05:01.244382+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** local-json with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | PASS |
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-nationality-aware` | ignores a visa deadline that should rule out or flag a destination | FAIL |
| `visa-deadline-surfaced` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | FAIL |
| `rag-cites-source` | generic tourist advice instead of backpacker-specific advice | FAIL |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | PASS |
| `memory-no-repeat-budget` | failing to use the trip profile | PASS |
| `memory-respects-explicit-preference` | failing to use the trip profile | PASS |
| `memory-recall-accurate` | failing to use the trip profile | PASS |
| `memory-writes-departure` | failing to use the trip profile | PASS |
| `memory-persists-fresh-session` | memory persisting across a fresh session | PASS |
| `isolation-cross-account` | cross-account isolation | PASS |
| `isolation-endpoint-scoping` | cross-account isolation | PASS |
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | FAIL |
| `route-overland-vs-flight` | failing to use the trip profile | FAIL |

## Failing cases

### `visa-nationality-aware` - Uses the stored nationality for visa guidance
- Failed `reply_mentions_any`: matched=[]

> I recommend Cambodia as your first choice for travel from Malaysia due to its faster flight times and lower visa costs. Using your stored preferences, (budget-friendly, balanced pace), a flight to Phnom Penh is both economical and efficient at around USD 95. In contrast, Indonesia requires a longer flight and includes a more complex visa extension process if needed.

### `rag-backpacker-not-tourist` - Gives backpacker advice, not brochure tourism
- Failed `judge`: judge score 2/5 - The response lacks specific budget details, transport options, and practical advice for backpackers, focusing instead on general travel conditions.

> Given your interests and budget, I recommend avoiding both Vietnam and Laos in September due to heavy rain and potential travel disruptions in both countries. However, if you had to choose based on your interests, Laos could be slightly better for its relaxed visa process and cheaper daily costs. Ultimately, both destinations are rated as 'avoid' this time of year, but Laos allows for more flexibi

### `rag-cites-source` - Cites the retrieved passage it used
- Error: `RuntimeError: aclose(): asynchronous generator is already running`
### `honesty-unknown-destination` - Admits when it has no verified data for a destination
- Failed `judge`: judge score 1/5 - The assistant confidently stated invented specifics about Mongolia and Uzbekistan's visa requirements and budget without acknowledging the lack of verified data.

> I recommend considering Mongolia first for your travel plans in June. The main reason is that it offers pleasant weather that is ideal for hiking and outdoor activities, which aligns well with your interests. Both Mongolia and Uzbekistan have similar budgets and visa requirements, but Mongolia's scenic landscapes in places like Terelj National Park provide great value experiences for a shoestring 

### `route-overland-vs-flight` - Compares overland against flying with real numbers
- Failed `reply_matches_regex`: match=None

> I recommend opting for Malaysia over Laos for your September travel. The main reason is that Laos experiences heavy rain during this month, making overland travel potentially unsafe and challenging. Based on your budget and preference for slow travel, Malaysia still offers interesting experiences and reliable transport options, allowing you to explore while staying within your shoestring budget.

