# Eval run `judge-evidence-fix-repeat`

- **Score:** 2/2 (100%), passing all 3 runs
- **Run id:** `eval-20260914T081210Z-fbfeab` (Langfuse tag)
- **Timestamp:** 2026-09-14T08:17:43.820630+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `route-live-lookup-uncurated-pair` | invents a journey time or cost for an uncurated pair with no real search behind it | PASS (3/3) |

Each case ran 3 times. A case counts as passing only if it passed every run; 100% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.
