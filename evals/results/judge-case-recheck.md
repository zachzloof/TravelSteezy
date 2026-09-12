# Eval run `judge-case-recheck`

- **Score:** 0/1 (0%), passing all 4 runs
- **Run id:** `eval-20260912T094620Z-f950dc` (Langfuse tag)
- **Timestamp:** 2026-09-12T09:47:20.659258+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | FLAKY (2/4) |

Each case ran 4 times. A case counts as passing only if it passed every run; 50% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.

## Failing cases

### `rag-backpacker-not-tourist` - Gives backpacker advice, not brochure tourism

> Given your shoestring budget and slow travel pace, I recommend Laos as the better option for you. Laos offers a realistic daily budget of around $18-25, which fits well with your budget band, and it has opportunities for caving and enjoying cheap food. You can experience the Mekong Slow Boat, a two-day journey from Huay Xai to Luang Prabang costing approximately $35. Currently, you're in Cambodia,

