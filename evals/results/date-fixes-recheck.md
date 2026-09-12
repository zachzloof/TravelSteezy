# Eval run `date-fixes-recheck`

- **Score:** 1/2 (50%), passing all 4 runs
- **Run id:** `eval-20260912T113612Z-f326ab` (Langfuse tag)
- **Timestamp:** 2026-09-12T11:38:02.843246+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `memory-no-repeat-budget` | failing to use the trip profile | FLAKY (3/4) |
| `memory-respects-explicit-preference` | failing to use the trip profile | PASS (4/4) |

Each case ran 4 times. A case counts as passing only if it passed every run; 88% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.

## Failing cases

### `memory-no-repeat-budget` - Does not ask for a budget it already stores

> I recommend you head to Thailand next due to the challenging weather conditions in both countries this September. Thailand's overland route from Laos allows for visa-free entry for **60 days**, making it easy for you as a UK passport holder. On a shoestring budget, expect to spend around **700-1,000 THB** (approximately $20-30) per day, covering dorms, street food, and transport. Given that you're

