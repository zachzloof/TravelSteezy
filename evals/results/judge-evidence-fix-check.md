# Eval run `judge-evidence-fix-check`

- **Score:** 2/2 (100%)
- **Run id:** `eval-20260914T080920Z-6705e8` (Langfuse tag)
- **Timestamp:** 2026-09-14T08:12:01.764210+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | PASS |
| `route-live-lookup-uncurated-pair` | invents a journey time or cost for an uncurated pair with no real search behind it | PASS |
