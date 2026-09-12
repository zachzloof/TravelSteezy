# Extension: onboarding, trip tracking, reviews, and place recommendations

This document covers the second phase of work on Travel Steezy. The base app (ADK
orchestrator, memory store, RAG, auth, evals) is described in the main
[README](../README.md). For the specific bugs found while building each piece
below — the exact failure, the fix, and the test or eval case that caught it —
see [notes/](../notes/00-index.md), particularly notes 02-06.

Four connected features, in the order a traveller meets them:

1. **Onboarding** captures their route so far, where they want to go, and how
   they travel - a welcome page of fixed questions answered in plain text, with
   an LLM turning each answer into structured fields.
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
| `onboarding_state` | Status, step, turn count and which questions have been answered. |
| `passports` | Every passport the traveller holds. A dual national gets a different, usually better, visa answer. |

Added to `trip_profile`: `social_style` (solo/couple/group) and `onboarded`.
Added to `onboarding_state`: `answered`, a JSON list of question ids.

`trip_profile.nationality` is kept in sync with the primary passport, so every
prompt, tool and eval written against that single field keeps working unchanged
and a single-passport traveller sees no difference at all.

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

Onboarding is a **welcome page with a fixed set of questions**, not a
conversation. That is the second design for this feature, and the reason for the
change is worth recording.

### What the first version did, and why it was replaced

The first version was two agents hijacking the opening turns of `/chat`: one
held the conversation and decided what to ask next, the other pulled structured
facts out of the answer. Splitting them fixed the original bug (one agent asked
to both chat warmly and emit JSON reliably produced the chat and dropped the
JSON), but three problems survived:

- **The first thing a new account saw was a chat window asking it questions.**
  Someone who arrived wanting to ask something got interviewed instead.
- **Which question got asked varied run to run**, because a model chose it. That
  made the eval case weak by construction: it could only assert the end state
  after three turns, never that a specific question was extracted correctly.
- **Nothing showed the traveller what had been captured.** Extraction quietly
  succeeded or quietly failed, and they found out later.

### What it does now

The questions live in `backend/agents/onboarding.py` as `QUESTIONS` - ordered
data, served to the frontend by `GET /travel/me/onboarding`. The conversational
agent is gone. The model keeps the one job it is genuinely good at: turning one
plain-English answer into structured fields.

| Question | Captures |
|---|---|
| Where have you been so far? | route in order, ratings, current location |
| How long have you got? | trip dates, visa/permit deadline |
| Which passport do you travel on? | passports (plural) |
| Where do you want to get to? | wishlist, including revisits |
| How do you travel? | budget, pace, climate, company, interests |

Two are marked optional and say so on screen.

**Each question gets its own extractor**, built with the question embedded in
its instruction plus any question-specific rules. This is not decoration: which
of `travel_history` or `wishlist` a place belongs in is carried almost entirely
by which question prompted the answer. The eval case
`onboarding-wishlist-allows-a-revisit` failed for exactly this reason - "I'd go
back to Koh Tao in a heartbeat" was filed as history (where Koh Tao already was)
and dropped from the wishlist, losing the only intent in the sentence. The fix
was a per-question rule telling the wishlist extractor that every place named
there is a wishlist entry, revisits included.

### Everything after extraction is Python

The model is never trusted to emit a valid enum value. It is told the opposite -
to copy the traveller's own words - and `store.normalise_band` maps them:

```
"dirt cheap"        -> shoestring        "as slow as I can"  -> slow
"flashpacker"       -> mid               "whistle-stop"      -> very_fast
```

Place names resolve through the same gazetteer as the coverage guard, so "koh
tao" and "Koh Tao, Thailand" become one row. Ratings are clamped. Nationality
adjectives become country names ("British" -> "United Kingdom"), because the
visa corpus is keyed on countries.

**Negation is handled explicitly**, because it is the worst failure available
here. "I hate the heat" and "I love the heat" share a keyword and mean opposite
things; substring matching alone stores the reverse of what was said. A negated
match is inverted for climate (`hot` -> `cool`) and **dropped** for budget and
pace, where inverting would itself be a guess - "not cheap" honestly could mean
any of four bands, and storing a guess is worse than storing nothing.

### Showing its working

Every answer's writes are echoed straight back to the page as "here is what I
took from that". This is the feature that makes imperfect extraction acceptable:
a misread is visible in the same second it happens, next to a panel where it can
be corrected. The flow ends on a review screen, and nothing in it is a one-way
door.

### It cannot trap anyone

Progress is a list of answered question ids on `onboarding_state.answered`, not
a single step cursor - a cursor could not express "skipped question 2, answered
question 3", so a resumed session re-asked something already dealt with. Every
question can be skipped, the whole thing can be skipped, and a skipped question
counts as answered so it does not reappear. Extraction failing is not fatal:
the step still advances and the field is editable by hand on the next screen.

### Captured shape

```json
{
  "travel_history": [{"location": "Koh Tao", "country": "Thailand", "order": 2,
                      "rating": 5, "review_notes": "did my Open Water here"}],
  "wishlist":       [{"location": "Pai", "priority": 1}],
  "passports":      ["United Kingdom", "Ireland"],
  "interests":      ["nature", "trekking", "food"],
  "budget_band": "shoestring", "travel_style": "slow",
  "climate_preference": "cool", "social_style": "solo"
}
```

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
| `GET /travel/me/onboarding` | The question set plus wherever this account got to |
| `POST /travel/me/onboarding/answer` | Extract one plain-text answer, echo back what was captured |
| `POST /travel/me/onboarding/complete` | Finish from the review screen |
| `POST /travel/me/onboarding/skip` | Opt out of onboarding |
| `POST /travel/me/history/rating` | Star-rate a stop already on the route |
| `DELETE /travel/me/history/{location}` | Remove a stop logged wrongly |
| `GET /travel/me/pending-reviews` | Places due a review prompt |
| `GET /travel/me/catchup` | Whether a "here's where we left off" prompt is due, and its summary |
| `POST /travel/me/catchup/dismiss` | The quick "still here, nothing's changed" button - no model call |
| `POST /travel/me/catchup/update` | Answer the catch-up card in free text - a genuine chat turn |
| `GET /memory/me` | Every raw row this account has, plus the exact prompt text fed to agents |
| `DELETE /memory/me/interests/{interest}` | Delete one interest |
| `DELETE /memory/me/passports/{country}` | Delete one passport |
| `DELETE /memory/me/profile-field/{field}` | Clear one raw trip_profile field |
| `POST /memory/me/onboarding/reset` | Redo the welcome-page questions without touching the route/wishlist |

---

## 9. Frontend

- **Welcome page** (`/welcome`) is where a new account lands. Five questions, one
  at a time, each answered in a plain textarea, with a panel beside it filling in
  with what has been captured so far. A router gate sends any account that has
  not finished or skipped onboarding here before it can reach the chat.
- **The trip profile** (`/preferences`) is three panels rather than one form:

  | Panel | Holds |
  |---|---|
  | About you | Passports (a list), currently in, the three five-point scales, deadline and interests |
  | Where you have been | The route, each stop star-rated inline, removable |
  | Where you want to go | The wishlist, with priority, and a "going back" badge on a revisit |

  History and wishlist actions persist immediately, because each is a discrete
  action. Only About You has a Save button, because that is the only panel where
  the user is mid-thought. Previously neither list was editable here at all -
  they could be seen in the chat sidebar and changed only by talking to an agent,
  which is backwards for the user's own data.
- **Five-point scales are five buttons, not a dropdown.** The order is the
  meaning, and a `<select>` hid it. Each point carries a one-line description
  ("private rooms, occasional flights") because "mid-range" alone is not
  something anybody can recognise themselves in.
- **Trip panel** in the chat sidebar shows the route with its star ratings, the
  wishlist with priorities, and interests. Auto-logged stops are marked as such.
- **Review card** appears above the composer when a review is due: a star rating,
  free text, and a share toggle.
- **Catch-up card** appears above the composer once per calendar-day gap since
  the account's last real chat turn: a short "here's where we left off" summary,
  a free-text box (processed as an ordinary chat turn), and a one-tap "still
  here" dismiss that makes no model call at all.
- **Memory page** (`/memory`) is a debug view, not a marketing feature: the
  exact `memory_block`/`travel_block` text fed into every agent prompt,
  every raw row (interest weights, deprecated columns, the onboarding
  answered-list included), per-row and per-field deletion, and which of an
  account's reviews have actually reached the shared RAG experience store -
  fetched by id, not trusted from what was submitted.
- **Assistant replies render as markdown**, not literal asterisks and dashes -
  a small `Markdown.vue` component (`marked` + DOMPurify) used for the chat
  bubble and every LLM-authored field on a destination card. The traveller's
  own typed messages are deliberately left as plain text.

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

**82 unit tests** across `tests/`, no keys and no network: route ordering, the
visit-promotes-wishlist path, rating validation, both review triggers, onboarding
gaps derived from data, per-account isolation, the legacy migration, the ranking
maths including the weighted-prior fix, clustering not chaining a city, label
cleaning, affiliate URLs, and Places degradation without a key.

The onboarding rework added coverage for the passport list and its `nationality`
mirror, free text landing on the five-point scales, **negated preferences never
being stored as their opposite**, an unrecognised band being dropped rather than
stored raw, ratings being settable and clearable, a stop being removable, and
`apply_capture` being idempotent and junk-tolerant.

**16 eval cases** exercise agent behaviour against the real database - eight
`travel` cases (tracking, reviews, discovery, the local guide) and eight
`onboarding` cases.

Both kinds check **stored rows rather than reply text**, which is a stronger
assertion than anything that inspects prose. The onboarding cases in particular
assert things a prose check simply cannot reach:

| Case | What it pins |
|---|---|
| `onboarding-captures-route-with-ratings` | A messy paragraph becomes an ordered route with the right ratings, and no rating is invented for the stop they gave no verdict on |
| `onboarding-maps-plain-english-to-bands` | "pretty tight budget", "staying put for a couple of weeks", "on my own" land on the scales |
| `onboarding-does-not-invert-a-negated-preference` | "I can't handle the heat" is never stored as `hot` |
| `onboarding-captures-both-passports` | The second passport is not dropped |
| `onboarding-wishlist-allows-a-revisit` | "I'd go back to Koh Tao" reaches the wishlist |
| `onboarding-scopes-answers-to-the-question-asked` | Places named on the wishlist question do not become visited history |
| `onboarding-invents-nothing` | Only what was said is stored |
| `onboarding-survives-a-non-answer` | Five non-answers write nothing and still complete the flow |
| `onboarding-full-flow-completes` | All five questions end to end produce a usable profile |

The `onboarding` case kind drives the same sequence as
`POST /travel/me/onboarding/answer`, including finishing on the review screen, so
it exercises the shipped path rather than a convenient approximation of it.

### What these cases caught immediately

First run: **7/9**. Both failures were real.

1. **`set_social_style` silently did nothing for a brand-new account.** It wrote
   with a bare `UPDATE trip_profile`, which matches no rows and reports no error
   when the profile row does not exist yet - which is every account arriving at
   onboarding. The case captured the budget, the pace and the interests correctly
   and lost only "solo", which is exactly the kind of single-field gap that never
   gets noticed by hand. `set_interests`' mirror into the text column had the
   same shape. Both now call `ensure_profile` first, pinned by
   `test_style_and_interests_save_for_an_account_with_no_profile_row_yet`.
2. **A revisit was being dropped**, which produced the per-question extractor
   rules described in section 2.

After both fixes: **9/9, passing all 3 repeat runs, 27/27 individual attempts**
(`evals/results/11-onboarding-v2.md`).

A third bug was caught by a unit test rather than an eval, and is worth noting
because it was invisible by inspection: the band synonym table flattens hyphens
in the *input* but not in its own *keys*, so `"whistle-stop"` arrived as
`"whistle stop"` and could never match its own entry. `"mid-range"` got away with
it only because `"mid"` matched as a substring.

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
