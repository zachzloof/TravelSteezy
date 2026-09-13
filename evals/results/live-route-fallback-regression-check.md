# Eval run `live-route-fallback-regression-check`

- **Score:** 4/4 (100%)
- **Run id:** `eval-20260913T141152Z-82aa4a` (Langfuse tag)
- **Timestamp:** 2026-09-13T14:12:34.800977+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | PASS |
| `route-overland-vs-flight` | failing to use the trip profile | PASS |
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | PASS |
| `discovery-honest-about-unknown-origin` | generic tourist advice instead of backpacker-specific advice | PASS |
