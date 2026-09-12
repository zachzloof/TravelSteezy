// The three preference scales, defined once.
//
// These mirror BUDGET_BANDS / TRAVEL_STYLES / CLIMATE_PREFS in
// backend/memory/store.py. They live in one file rather than being inlined into
// each form because the welcome page, the About You panel and the sidebar all
// render the same five points, and three copies of a five-point scale is three
// chances for them to disagree about what "mid" means.
//
// Each point carries a short label for the control and a longer `note` shown
// under the selection - the note is what makes a five-point scale answerable.
// "Mid-range" on its own means nothing; "private rooms, occasional flights"
// is a thing somebody can recognise themselves in.

export const BUDGET_BANDS = [
  { value: 'shoestring', label: 'Shoestring', note: 'Dorms, street food, night buses. Counting every note.' },
  { value: 'budget', label: 'Budget', note: 'Mostly dorms, the odd cheap private. Still watching it.' },
  { value: 'mid', label: 'Mid-range', note: 'Private rooms, occasional flights instead of the 14-hour bus.' },
  { value: 'comfortable', label: 'Comfortable', note: 'Good privates, comfort usually wins over cost.' },
  { value: 'luxury', label: 'Luxury', note: 'Cost is not the constraint.' }
]

export const TRAVEL_STYLES = [
  { value: 'very_slow', label: 'Very slow', note: 'Weeks in one place. Living somewhere, not passing through.' },
  { value: 'slow', label: 'Slow', note: 'Several nights per stop, no rush between them.' },
  { value: 'balanced', label: 'Balanced', note: 'A few days each, moving steadily.' },
  { value: 'fast', label: 'Fast', note: 'A stop every night or two, covering ground.' },
  { value: 'very_fast', label: 'Very fast', note: 'Seeing as much as possible in the time you have.' }
]

export const CLIMATE_PREFS = [
  { value: 'cold', label: 'Cold', note: 'Mountains and altitude. Bring the layers.' },
  { value: 'cool', label: 'Cool', note: 'Crisp mornings. Hill towns over coastlines.' },
  { value: 'temperate', label: 'Temperate', note: 'Mild and even. No extremes either way.' },
  { value: 'warm', label: 'Warm', note: 'Pleasant heat without the humidity.' },
  { value: 'hot', label: 'Hot', note: 'Tropical, humid, beaches. The hotter the better.' }
]

export const SOCIAL_STYLES = [
  { value: 'solo', label: 'Solo' },
  { value: 'couple', label: 'As a couple' },
  { value: 'group', label: 'With friends' }
]

export const PRIORITIES = [
  { value: 1, label: 'Set on it' },
  { value: 2, label: 'Keen' },
  { value: 3, label: 'Curious' }
]

const ALL = [...BUDGET_BANDS, ...TRAVEL_STYLES, ...CLIMATE_PREFS, ...SOCIAL_STYLES]

/** Human label for a stored value, falling back to the raw value itself. */
export function labelFor(value) {
  if (!value) return ''
  return ALL.find((option) => option.value === value)?.label || String(value)
}

export function priorityLabel(priority) {
  return PRIORITIES.find((p) => p.value === priority)?.label || 'Keen'
}
