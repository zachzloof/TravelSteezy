# Eval run `42-all-specialists-on-compare`

- **Score:** 4/4 (100%)
- **Run id:** `eval-20260915T150545Z-08803b` (Langfuse tag)
- **Timestamp:** 2026-09-15T15:07:31.993941+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `visa-vietnam-lead-time` | ignores a visa lead time that should rule out or flag a destination | PASS |
| `rag-cites-source` | generic tourist advice instead of backpacker-specific advice | PASS |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | PASS |
