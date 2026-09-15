# Eval run `live-route-fallback-verify`

- **Score:** 1/1 (100%)
- **Run id:** `eval-20260913T141049Z-f13d5f` (Langfuse tag)
- **Timestamp:** 2026-09-13T14:11:05.661072+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `route-live-lookup-uncurated-pair` | presents unverified route data as curated, or invents figures for an uncurated pair | PASS |
