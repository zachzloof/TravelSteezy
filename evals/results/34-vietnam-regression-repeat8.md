# Eval run `vietnam-regression-repeat8`

- **Score:** 0/1 (0%), passing all 8 runs
- **Run id:** `eval-20260914T082022Z-001ec7` (Langfuse tag)
- **Timestamp:** 2026-09-14T08:25:41.312054+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | FLAKY (3/8) |

Each case ran 8 times. A case counts as passing only if it passed every run; 38% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.

## Failing cases

### `visa-vietnam-lead-time` - Respects the Vietnam e-visa lead time against a hard deadline
- Failed `reply_mentions_any`: matched=[]
- Failed `not_ranked_first`: no ranked cards were produced

> {{
>   "reply": "Given your shoestring budget, fast travel pace, and the hard deadline of your Cambodian visa expiring on 2026-03-04, Thailand is your best option. This choice also aligns with your current location in Cambodia and helps you exit timely. Although Vietnam can be appealing, without concrete costs and visa details at hand, Thailand is more practical right now. Confirm any visa requireme

