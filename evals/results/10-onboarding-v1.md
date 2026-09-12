# Eval run `onboarding-v1`

- **Score:** 7/9 (78%)
- **Run id:** `eval-20260912T093708Z-3fcbca` (Langfuse tag)
- **Timestamp:** 2026-09-12T09:37:41.642950+00:00
- **Model:** gpt-4o-mini / judge gpt-4o-mini
- **RAG:** pinecone with openai embeddings

| Case | Failure mode | Result |
|---|---|---|
| `onboarding-captures-route-with-ratings` | onboarding fails to capture structured profile | PASS |
| `onboarding-maps-plain-english-to-bands` | onboarding fails to capture structured profile | FAIL |
| `onboarding-does-not-invert-a-negated-preference` | onboarding stores a preference as its opposite | PASS |
| `onboarding-captures-both-passports` | onboarding fails to capture structured profile | PASS |
| `onboarding-wishlist-allows-a-revisit` | onboarding fails to capture structured profile | FAIL |
| `onboarding-scopes-answers-to-the-question-asked` | onboarding stores wanted places as already visited | PASS |
| `onboarding-invents-nothing` | onboarding invents profile data that was never stated | PASS |
| `onboarding-survives-a-non-answer` | onboarding traps the user or writes junk | PASS |
| `onboarding-full-flow-completes` | onboarding fails to capture structured profile | PASS |

## Failing cases

### `onboarding-maps-plain-english-to-bands` - Free-text style answer lands on the five-point scales
- Failed `profile_field_set`: social_style=''

> set_interests({'interests': ['hiking', 'diving']}); set_social_style({'social_style': 'solo'}); update_profile({'budget_band': 'budget', 'travel_style': 'slow'})

### `onboarding-wishlist-allows-a-revisit` - Wanting to return somewhere is captured rather than refused
- Failed `wishlist_contains`: wishlist=['pai', 'laos'], missing=['koh tao']

> add_travel_history({'location': 'Koh Tao', 'order': 1, 'rating': 5}); add_wishlist({'location': 'Pai', 'priority': 1}); add_wishlist({'location': 'Laos', 'priority': 1})

