# Eval run `40-bug3-weather-guard`

- **Score:** 2/3 (67%)
- **Run id:** `eval-20260915T133730Z-82b452` (Langfuse tag)
- **Timestamp:** 2026-09-15T13:38:46.450044+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | FAIL |

## Failing cases

### `rag-budget-numbers` - Quotes realistic daily budget numbers from the store
- Failed `retrieval_fired`: namespaces retrieved=['seasonal', 'visa']

> Given your shoestring budget and interest in food and temples, Cambodia might be the better choice right now. With a budget of roughly USD 20-35 per day for food, dorm accommodation, and local activities, it offers a slightly cheaper daily cost compared to Laos, where you'd budget about USD 25-40 per day. You're currently in Thailand, and an overland bus to Cambodia costs about USD 12-25, making i

