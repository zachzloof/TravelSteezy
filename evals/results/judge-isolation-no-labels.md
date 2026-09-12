# Eval run `judge-isolation-no-labels`

- **Score:** 0/1 (0%), passing all 6 runs
- **Run id:** `eval-20260912T095031Z-74fe35` (Langfuse tag)
- **Timestamp:** 2026-09-12T09:52:00.945481+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | FLAKY (3/6) |

Each case ran 6 times. A case counts as passing only if it passed every run; 50% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.

## Failing cases

### `rag-backpacker-not-tourist` - Gives backpacker advice, not brochure tourism
- Failed `judge`: judge score 3/5 - While the assistant provides some budget details and mentions dorm prices, it lacks specific overland transport options and detailed safety warnings relevant to budget backpackers.

> I recommend going to Vietnam for your three weeks, as the weather in March is rated 'good' for travel, making it a great time to explore. Your daily budget would be around USD 20-25, and you'll need an e-Visa costing approximately USD 25, valid for up to 90 days with a processing lead time of 3-5 working days. Given your budget band and slow travel pace, Vietnam is a perfect fit for your current s

