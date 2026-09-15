# Eval run `44-baseline-tracking-flake`

- **Score:** 0/1 (0%), passing all 5 runs
- **Run id:** `eval-20260915T200341Z-7dbfda` (Langfuse tag)
- **Timestamp:** 2026-09-15T20:05:44.448271+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `tracking-does-not-relocate-you-on-a-placeless-turn` | writing memory the user did not actually state | FLAKY (3/5) |

Each case ran 5 times. A case counts as passing only if it passed every run; 60% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.

## Failing cases

### `tracking-does-not-relocate-you-on-a-placeless-turn` - A turn naming no place does not move the traveller

> Today, I recommend heading to Malaysia, as it's the most feasible option given your current location in Thailand and shoestring budget. With visa-free entry for 90 days and a daily budget around $25-30, Malaysia offers both affordability and ease of entry. You can travel overland from Bangkok to Penang, a journey that takes about 20 hours and costs roughly USD 30-50. This fits well with your shoes

