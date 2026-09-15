# Eval run `37-bug3-scope-and-grounding`

- **Score:** 6/6 (100%)
- **Run id:** `eval-20260915T130409Z-b09536` (Langfuse tag)
- **Timestamp:** 2026-09-15T13:07:07.822802+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | PASS |
| `discovery-honest-about-unknown-origin` | invents onward destinations, journey times or prices for an uncovered origin with no real search behind them | PASS |
| `scope-country-question-answered-with-countries` | answering a country-level question at town level | PASS |
| `scope-visa-expiry-forces-a-country-answer` | answering a country-level question at town level | PASS |
| `tracking-ignores-a-hypothetical-departure` | writing memory the user did not actually state | PASS |
| `tracking-does-not-relocate-you-on-a-placeless-turn` | writing memory the user did not actually state | PASS |
