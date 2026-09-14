# Eval run `vietnam-postfix-repeat8`

- **Score:** 0/1 (0%), passing all 8 runs
- **Run id:** `eval-20260914T091822Z-ebb967` (Langfuse tag)
- **Timestamp:** 2026-09-14T09:21:29.794974+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | FLAKY (6/8) |

Each case ran 8 times. A case counts as passing only if it passed every run; 75% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.

## Failing cases

### `visa-vietnam-lead-time` - Respects the Vietnam e-visa lead time against a hard deadline

> Given your hard deadline of March 4, 2026, Thailand is the safer and more practical choice for your next destination. Since obtaining a Vietnam e-visa takes 3-5 working days, you won't meet this timeline. Entering Thailand is visa-free for 60 days, which fits perfectly with your fast pace and shoestring budget. The overland route from Cambodia to Thailand via Siem Reap and Bangkok takes 8-9 hours 

