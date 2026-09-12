# Eval run `after-fix-pinecone-langfuse`

- **Score:** 19/19 (100%)
- **Run id:** `eval-20260911T165850Z-2493bc` (Langfuse tag)
- **Timestamp:** 2026-09-11T17:02:22.394800+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | PASS |
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-nationality-aware` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `visa-deadline-surfaced` | ignores a visa deadline that should rule out or flag a destination | PASS |
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | PASS |
| `rag-cites-source` | generic tourist advice instead of backpacker-specific advice | PASS |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | PASS |
| `memory-no-repeat-budget` | failing to use the trip profile | PASS |
| `memory-respects-explicit-preference` | failing to use the trip profile | PASS |
| `memory-recall-accurate` | failing to use the trip profile | PASS |
| `memory-writes-departure` | failing to use the trip profile | PASS |
| `memory-persists-fresh-session` | memory persisting across a fresh session | PASS |
| `isolation-cross-account` | cross-account isolation | PASS |
| `isolation-endpoint-scoping` | cross-account isolation | PASS |
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | PASS |
| `route-overland-vs-flight` | failing to use the trip profile | PASS |
