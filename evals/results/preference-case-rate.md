# Eval run `preference-case-rate`

- **Score:** 1/1 (100%), passing all 8 runs
- **Run id:** `eval-20260912T112904Z-b9b755` (Langfuse tag)
- **Timestamp:** 2026-09-12T11:30:56.348444+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `memory-respects-explicit-preference` | failing to use the trip profile | PASS (8/8) |

Each case ran 8 times. A case counts as passing only if it passed every run; 100% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.
