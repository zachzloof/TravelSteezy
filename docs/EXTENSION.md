# Extension: onboarding, trip tracking, reviews, and place recommendations

This document covers the second phase of work on Onward. The base app (ADK
orchestrator, memory store, RAG, auth, evals) is described in the main
[README](../README.md). For the specific bugs found while building each piece
below — the exact failure, the fix, and the test or eval case that caught it —
see [notes/](../notes/00-index.md), particularly notes 02-06.

Four connected features, in the order a traveller meets them:

1. **Onboarding** captures their route so far, where they want to go, and how
   they travel - conversationally, into structured fields.
2. **Trip tracking** notices when they actually reach somewhere and logs it,
   promoting it off the wishlist.
3. **Review prompts** ask what a place was like once they have left it.
4. **Recommendation tools** answer "where next" and "where do I stay here" using
   the Google Places API and a city-level route corpus, with reviews feeding back
   into the RAG store so suggestions improve.

---

## 1. Schema changes

Five new tables plus two columns, created by `backend/db.py` on boot. Everything
is keyed by `user_id` and cascades on account deletion.

| Table | Purpose |
|---|---|
| `travel_history` | The route. Town-level, explicitly ordered, with the post-visit review attached. |
| `wishlist` | Where they want to go, with priority and status (`open`/`visited`/`dropped`). |
| `user_interests` | Interests as rows, so agents can filter rather than parse a text blob. |
| `recommendation_feedback` | Whether a surfaced suggestion was accepted or rejected. |
| `places_cache` | Google Places responses, keyed by query hash, with a TTL. |
| `onboarding_state` | Status, step and turn count for the onboarding conversation. |

Added to `trip_profile`: `social_style` (solo/couple/group) and `onboarded`.

```sql
CREATE TABLE travel_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location        TEXT    NOT NULL,                  -- "Chiang Mai"
    location_type   TEXT    NOT NULL DEFAULT 'city',   -- country|city|town|region
    country         TEXT,
    order_index     INTEGER NOT NULL DEFAULT 0,        -- position in the route
    arrival_date    TEXT,
    departure_date  TEXT,
    source          TEXT    NOT NULL DEFAULT 'manual', -- onboarding|tracked|manual|migrated
    notes           TEXT,
    rating          INTEGER,                           -- post-visit review, 1-5
    review_notes    TEXT,
    reviewed_at     TEXT,
    review_prompted_at TEXT,                           -- so we ask only once
    last_mentioned_at  TEXT,                           -- drives the staleness trigger
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, location, arrival_date)
);
```

### Migration, not replacement

`travel_history` supersedes the original country-level `visited_history`, which
had no ordering, no town granularity and nowhere to put a review. The old table
is still written to and read from, so nothing that depended on it broke, and
`migrate_visited_history()` copies legacy rows across on boot. It is idempotent
and asserted by a test: an existing install must not appear to lose its history
on deploy.

`add_missing_columns()` handles the two new `trip_profile` columns, since SQLite
has no `ADD COLUMN IF NOT EXISTS`.

---

## 2. Onboarding

`backend/agents/graph.py` defines **two** agents, and that split is the whole
lesson of this feature.

The first attempt was one agent asked to both hold a warm conversation and append
a machine-readable block. It reliably produced the conversation and silently
dropped the block. Nothing was ever captured, so the step never advanced, so it
asked "where have you been?" on every single turn. The fix:

| Agent | Job |
|---|---|
| `onboarding_extractor` | Reads the message, returns JSON only. Never speaks to the user. |
| `onboarding_agent` | Holds the conversation. Never emits JSON. |

`_run_onboarding` in `backend/agents/runner.py` runs the extractor, writes what it
found with explicit calls, then asks the conversational agent for the next gap.

**Progress is computed from stored data, never from the model.**
`travel.onboarding_gaps(user_id)` asks the database three questions: is there any
route history, is there anything on the wishlist, do we have interests plus a
budget or pace. Whatever the model believes about which step it is on is
irrelevant. A hard cap of six turns means onboarding can never trap anyone, and
`POST /travel/me/onboarding/skip` lets them opt out.

Captured shape:

```json
{
  "travel_history": [{"location": "Bangkok", "location_type": "city",
                      "country": "Thailand", "order": 1}],
  "wishlist":       [{"location": "Pai", "priority": 1}],
  "interests":      ["nature", "trekking", "food"],
  "budget_band": "shoestring", "travel_style": "slow", "social_style": "solo"
}
```

---

## 3. Trip tracking

`backend/agents/tracking.py` turns a parsed turn into structured writes. The turn
parser extracts `visits`, `departures`, `wishlist_adds`, `wishlist_removes` and
`reviews`; `apply_tracking` decides what they mean for stored state.

On a detected visit:

- append to `travel_history` with `source="tracked"`
- `resolve_wishlist(...)` promotes it out of the wishlist
- `current_location` updates on the trip profile
- if it came off the wishlist, that is logged as an **accepted** recommendation
  and written to the RAG `experience` namespace

The important negative rule: **asking about a place is not visiting it.** "What
is Luang Prabang like? I might go one day" must not log a visit. That distinction
is stated in the parser prompt and has its own eval case.

Re-mentioning somewhere already known is not a memory write either. An earlier
version logged `track_visit` on every turn that named the current town, which
filled the "just remembered" panel with noise. `add_travel_history` now reports
whether anything actually changed, and only real changes reach the audit log.

---

## 4. Review prompts

Two triggers, both in `travel.get_pending_reviews`:

- **explicit** - the place has a `departure_date` in the past
- **time-based** - it has not been mentioned for N days (default 3)

`tracking.review_prompt_for` picks the next place due, marks it prompted so the
traveller is asked once rather than nagged, and the reply gets one line appended.
The prompt never hijacks the turn: the traveller still gets the answer they asked
for, with the nudge after it.

A review can arrive conversationally ("Pai was a solid 5/5, the canyon at sunset
is unreal") or through the review card in the UI. Both land on the same
`travel_history` row, and both push a document into the RAG `experience`
namespace unless the traveller unticks sharing.

---

## 5. Place recommendation tools

### Bayesian ranking

`backend/places/ranking.py`. Sorting by raw Google rating is actively misleading:
a cafe with one 5.0 review outranks a hostel with 4.6 from 2,400 people.

```
weighted_score = (v / (v + m)) * R + (m / (v + m)) * C
```

`R` the rating, `v` the review count, `m` the prior strength in virtual reviews
(default 25), `C` the prior.

**`C` is weighted by review count, not a plain average.** A plain mean let a
single thin outlier drag the prior toward itself and then fail to shrink it - with
two candidates, a 5.0-from-1 pulled the prior to 4.9 and *outranked* a
4.8-from-180. A unit test guards this.

On a realistic spread the thin five-star drops from first to last:

| Place | Rating | Reviews | Weighted |
|---|---|---|---|
| Well reviewed | 4.8 | 180 | 4.72 |
| Very popular | 4.6 | 2,400 | 4.60 |
| One review | 5.0 | 1 | 4.18 |
| Mediocre but busy | 3.9 | 5,000 | 3.90 |

### Neighbourhood clustering

`backend/places/clustering.py` groups hostels into walkable areas, because
backpackers choose an area before a bed.

It uses **centroid distance with a spread cap**, not single-linkage. Single
linkage chained twenty Chiang Mai hostels 700m apart into one "area" spanning
2.6km, which is useless advice. The current version returns four areas with
spreads of 526-966m. Area labels come from the street of the strongest listing,
with house numbers stripped; they are labels, not official boundaries, and the
tool says so.

### The tools

| Tool | What it does |
|---|---|
| `get_places_recommendations(location, place_type, radius_meters)` | Ranked places of a type near a location. |
| `find_hostels(location, budget_band)` | Hostels plus booking links. |
| `find_food_near(location, craving)` | Where to eat, including a named dish. |
| `suggest_areas_to_stay(location)` | Clustered areas rather than a list of properties. |
| `get_booking_links(location, checkin, checkout)` | Booking.com and Hostelworld URLs. |
| `discover_next_destinations(from_location, interests)` | Onward hops from the route corpus plus traveller feedback. |
| `get_traveller_feedback(location)` | What previous travellers said after visiting. |

**Hostel search uses text search, not the `lodging` type.** Places API (New) has
no hostel type, and `lodging` returns hotels - the wrong answer for this app.

**Caching and retries.** `places_cache` keys on a hash of the query with a 24h
TTL, so a demo re-asking the same question does not re-bill. A repeat lookup goes
from 0.2s to 0.003s. Retries are bounded at three attempts with exponential
backoff and jitter on 408/429/5xx and network errors; other 4xx are not retried.

**Without a key**, every tool returns `configured: false` with an explanatory note
and an empty list, and the agent says live place data is unavailable rather than
inventing a hostel. Booking links still work, since they need no API.

**Affiliate links** are URL construction only - no API, no key. `BOOKING_AFFILIATE_ID`
and `HOSTELWORLD_AFFILIATE_ID` are optional; without them the links still work.
Every response carries a disclosure string and the UI labels them as affiliate
links.

---

## 6. The RAG feedback loop

Two new Pinecone namespaces:

- **`routes`** - 16 curated city-level documents ("onward from Chiang Mai": Pai 3h
  by minibus, Chiang Rai for the Laos border, the Mae Hong Son loop). The original
  corpus is country-level and cannot answer "where next from here".
- **`experience`** - written at runtime from post-visit reviews and from whether a
  suggestion was accepted or rejected.

`backend/rag/experience.py` builds the documents. Reviews shorter than a dozen
characters are skipped: a bare rating adds noise without information. Documents
carry the account id but never a username, and are presented to other travellers
as anonymous feedback. `share=False` keeps a review out of the shared namespace
entirely.

`python -m scripts.ingest_rag --experience` backfills everything already in SQLite.

---

## 7. Guards computed in code

The pattern from the base app extended to three more places. Each is Python that
runs before an agent and is injected as a non-negotiable prompt block, and each
exists because an eval case caught the model getting it wrong.

| Guard | Catches |
|---|---|
| `coverage_note` | Inventing visa rules and prices for destinations outside the corpus. |
| `deadline_note` | Silently planning past a visa expiry. |
| `route_note` | Inventing onward hops from a town with no route data. |
| intent override | A two-destination question routed to an agent with no visa tool. |

Two of these were added during this extension:

**`route_note`** - asked "where next" from Reykjavik, the discovery tool correctly
returned `found: false` and the agent invented Icelandic destinations anyway.
Telling it in code is stronger than hoping it reads the tool result. It is
country-aware: a traveller whose stored location is "Thailand" is not outside
coverage, we just need to know which town before giving hop-by-hop detail.

**The intent override** - the classifier sent "what do I need to get into Indonesia
and Cambodia?" to the local guide, which has no visa tool, and it answered from
parametric knowledge with a wrong visa rule. Now any turn naming two or more
destinations is forced to the comparison path, and if the parser returns fewer
than two candidates the runner falls back to deterministic detection over the raw
message.

The coverage guard also had to become **city-aware**: treating "Perhentian
Islands, Malaysia" as unsupported made it suppress a correct monsoon warning for a
country that is fully covered.

---

## 8. New API endpoints

All scoped to the authenticated account; `user_id` comes from the signed token.

| Endpoint | Purpose |
|---|---|
| `GET /travel/me` | Route, wishlist, interests, pending reviews, onboarding state |
| `POST /travel/me/visits` | Record a visit |
| `POST /travel/me/wishlist` | Add somewhere to the wishlist |
| `DELETE /travel/me/wishlist/{location}` | Drop it, recorded as a rejected suggestion |
| `POST /travel/me/reviews` | Save a review, optionally private |
| `POST /travel/me/interests` | Replace the interest list |
| `POST /travel/me/onboarding/skip` | Opt out of onboarding |
| `GET /travel/me/pending-reviews` | Places due a review prompt |

---

## 9. Frontend

- **Onboarding** takes over the chat for the first few turns, with its own
  suggested openers and a skip link.
- **Trip panel** in the sidebar shows the route as a timeline with ratings, the
  wishlist with priorities, and interests. Auto-logged stops are marked as such.
- **Review card** appears above the composer when a review is due: a star rating,
  free text, and a share toggle.
- Wishlist entries can be dropped inline.

---

## 10. Configuration

```bash
GOOGLE_PLACES_API_KEY=        # Places API (New), restricted to that API
PLACES_CACHE_TTL_SECONDS=86400
PLACES_MIN_REVIEWS=25         # m, the Bayesian prior strength
BOOKING_AFFILIATE_ID=         # optional
HOSTELWORLD_AFFILIATE_ID=     # optional
```

`GET /health` reports `places.configured` alongside the other dependencies.

---

## 11. What is tested

30 unit tests in `tests/test_travel_and_places.py`, no keys and no network:
route ordering, the visit-promotes-wishlist path, rating validation, both review
triggers, onboarding gaps derived from data, per-account isolation, the legacy
migration, the ranking maths including the weighted-prior fix, clustering not
chaining a city, label cleaning, affiliate URLs, and Places degradation without a
key.

Eight new eval cases in `evals/cases.jsonl` exercise the agent behaviour against
the real database: onboarding capturing structured history in order, a visit
promoting off the wishlist, curiosity *not* logging a visit, a review being
stored, the review prompt firing after departure, discovery using the route
corpus, discovery admitting an uncovered origin, and the local guide hitting
Places.

These use a `travel` case kind whose checks read the database rather than the
reply text, which is a stronger assertion than anything that inspects prose.

### Repeat mode, and why it exists

Four consecutive runs of the *same code* scored 89%, 96%, 93% and 89%, failing a
different subset each time. The agents are nondeterministic, so a single run's
score is close to meaningless - it would have been easy to report the 96% and
call it done.

`--repeat N` runs every case N times. A case counts as passing only if it passed
**every** run, and the report shows per-case pass rates plus which cases are
flaky. That turns "somewhere between 89 and 96" into an honest picture of which
behaviour is solid and which sits on the boundary.

```bash
python -m evals.run_evals --repeat 3
```

It immediately earned its keep: `season-malaysia-east-coast-closed` was passing
1 run in 3, which a single run would have reported as either a clean pass or a
regression. The cause was a real bug - the country-keyed climate table returning
"unknown" for a town-level candidate, silently dropping a monsoon warning.

### The judge has to show its evidence

An LLM judge scored a reply 1/5 with the reason "the assistant asks for budget
information, which is unnecessary given the stored context". The reply asked for
nothing; it used every stored field correctly. The judge had invented the fault.

The judge prompt now requires a verbatim `quote` from the reply for any
deduction, and `run_evals.py` checks in code that the quote actually appears. A
low score justified by a quote that is not in the reply is rejected and treated
as a pass. Fixing the instrument rather than tuning the product to satisfy a
faulty one.
