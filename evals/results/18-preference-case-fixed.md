# Eval run `preference-case-fixed`

- **Score:** 1/1 (100%), passing all 6 runs
- **Run id:** `eval-20260912T112245Z-d0945b` (Langfuse tag)
- **Timestamp:** 2026-09-12T11:24:08.454745+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `memory-respects-explicit-preference` | failing to use the trip profile | PASS (6/6) |

Each case ran 6 times. A case counts as passing only if it passed every run; 100% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.
