# Eval run `onboarding-v2`

- **Score:** 9/9 (100%), passing all 3 runs
- **Run id:** `eval-20260912T093952Z-f1386d` (Langfuse tag)
- **Timestamp:** 2026-09-12T09:41:16.658841+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
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

Each case ran 3 times. A case counts as passing only if it passed every run; 100% of individual attempts passed. The agents are nondeterministic, so a single run's score is noisy - this is the honest picture.
