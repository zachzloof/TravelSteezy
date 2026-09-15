# Eval run `43-wider-candidate-pool`

- **Score:** 38/39 (97%), passing all 3 runs
- **Run id:** `eval-20260915T193826Z-bab97a` (Langfuse tag)
- **Timestamp:** 2026-09-15T20:02:11.106149+00:00
- **Model:** gpt-4o-mini / judge gpt-4o
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `onboarding-captures-route-with-ratings` | onboarding fails to capture structured profile | PASS (3/3) |
| `onboarding-maps-plain-english-to-bands` | onboarding fails to capture structured profile | PASS (3/3) |
| `onboarding-does-not-invert-a-negated-preference` | onboarding stores a preference as its opposite | PASS (3/3) |
| `onboarding-captures-both-passports` | onboarding fails to capture structured profile | PASS (3/3) |
| `onboarding-wishlist-allows-a-revisit` | onboarding fails to capture structured profile | PASS (3/3) |
| `onboarding-scopes-answers-to-the-question-asked` | onboarding stores wanted places as already visited | PASS (3/3) |
| `onboarding-invents-nothing` | onboarding invents profile data that was never stated | PASS (3/3) |
| `onboarding-survives-a-non-answer` | onboarding traps the user or writes junk | PASS (3/3) |
| `onboarding-full-flow-completes` | onboarding fails to capture structured profile | PASS (3/3) |
| `season-nepal-monsoon` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `season-philippines-typhoon` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `season-cambodia-april-heat` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `season-malaysia-east-coast-closed` | recommends a destination during its monsoon/unsafe season | PASS (3/3) |
| `visa-vietnam-lead-time` | ignores a visa lead time that should rule out or flag a destination | PASS (3/3) |
| `visa-nationality-aware` | ignores nationality-specific visa guidance | PASS (3/3) |
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
| `tracking-promotes-wishlist-to-history` | live trip tracking does not fire | PASS (3/3) |
| `tracking-ignores-mere-curiosity` | live trip tracking does not fire | PASS (3/3) |
| `review-captured-and-stored` | post-visit review not captured | PASS (3/3) |
| `review-prompt-fires-after-departure` | post-visit review not captured | PASS (3/3) |
| `discovery-uses-route-corpus` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `discovery-honest-about-unknown-origin` | invents onward destinations, journey times or prices for an uncovered origin with no real search behind them | PASS (3/3) |
| `local-guide-uses-places` | generic tourist advice instead of backpacker-specific advice | PASS (3/3) |
| `route-live-lookup-uncurated-pair` | invents a journey time or cost for an uncurated pair with no real search behind it | PASS (3/3) |
| `scope-country-question-answered-with-countries` | answering a country-level question at town level | PASS (3/3) |
| `scope-visa-expiry-forces-a-country-answer` | answering a country-level question at town level | PASS (3/3) |
| `tracking-ignores-a-hypothetical-departure` | writing memory the user did not actually state | PASS (3/3) |
| `tracking-does-not-relocate-you-on-a-placeless-turn` | writing memory the user did not actually state | FLAKY (2/3) |

Each case ran 3 times. A case counts as passing only if it passed every run; 99% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.

## Failing cases

### `tracking-does-not-relocate-you-on-a-placeless-turn` - A turn naming no place does not move the traveller
- Failed `profile_field_in`: current_location='chiang mai', wanted one of ['thailand', 'pai']

> Here are some options for what you can do next from Chiang Mai:
> 
> 1. **Pai**  
>    - **Journey**: 3 hours north by minibus, with around 762 curves. Cost: 150-200 THB.  
>    - **Who it suits**: Highly recommended! It's a small hippie town known for its relaxed vibe, beautiful scenery, and vibrant sunsets at the canyon. Many travelers end up staying longer than planned.  
>    - Feedback: A traveler rate

