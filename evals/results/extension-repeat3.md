# Eval run `extension-repeat3`

- **Score:** 26/27 (96%), passing all 3 runs
- **Run id:** `eval-20260911T190441Z-c3dc0c` (Langfuse tag)
- **Timestamp:** 2026-09-11T19:17:36.104927+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | FLAKY (1/3) |
| `visa-vietnam-lead-time` | ignores a visa deadline that should rule out or flag a destination | PASS (3/3) |
| `visa-nationality-aware` | ignores a visa deadline that should rule out or flag a destination | PASS (3/3) |
| `visa-deadline-surfaced` | ignores a visa deadline that should rule out or flag a destination | PASS (3/3) |
| `rag-backpacker-not-tourist` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `rag-cites-source` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `rag-budget-numbers` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `memory-no-repeat-budget` | failing to use the trip profile | PASS (3/3) |
| `memory-respects-explicit-preference` | failing to use the trip profile | PASS (3/3) |
| `memory-recall-accurate` | failing to use the trip profile | PASS (3/3) |
| `memory-writes-departure` | failing to use the trip profile | PASS (3/3) |
| `memory-persists-fresh-session` | memory persisting across a fresh session | PASS (3/3) |
| `isolation-cross-account` | cross-account isolation | PASS (3/3) |
| `isolation-endpoint-scoping` | cross-account isolation | PASS (3/3) |
| `honesty-unknown-destination` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `route-overland-vs-flight` | failing to use the trip profile | PASS (3/3) |
| `onboarding-captures-structured-history` | onboarding fails to capture structured profile | PASS (3/3) |
| `tracking-promotes-wishlist-to-history` | live trip tracking does not fire | PASS (3/3) |
| `tracking-ignores-mere-curiosity` | live trip tracking does not fire | PASS (3/3) |
| `review-captured-and-stored` | post-visit review not captured | PASS (3/3) |
| `review-prompt-fires-after-departure` | post-visit review not captured | PASS (3/3) |
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `discovery-honest-about-unknown-origin` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |

Each case ran 3 times. A case counts as passing only if it passed every run; 98% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.

## Failing cases

### `season-malaysia-east-coast-closed` - Knows Perhentians shut in the northeast monsoon
- Failed `reply_mentions_any`: matched=[]

> I recommend heading to the Perhentian Islands in Malaysia for December because it's a more budget-friendly and accessible option given your shoestring budget and slow travel pace. You can stay in Malaysia visa-free for up to 90 days, which is convenient. The overland journey from Bangkok to Butterworth will take about 20 hours and cost approximately USD 30-50. While Indonesia's wet season might af

