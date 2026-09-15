# Places recommendations and ranking

## The Bayesian ranking bug: plain mean vs. review-weighted prior

The ranking formula itself is the standard Bayesian/"true Bayesian estimate"
shrinkage (the same shape IMDb uses for its weighted rank):

```
weighted_score = (v / (v + m)) * R + (m / (v + m)) * C
```

`R` = the place's own rating, `v` = its review count, `m` = the prior strength
in "virtual reviews" (default 25, from `PLACES_MIN_REVIEWS`), `C` = the prior
(the "typical" rating across the candidate set).

**The bug was in how `C` was computed.** The first implementation used a plain
arithmetic mean of ratings across candidates:

```python
C = sum(ratings) / len(ratings)
```

With a realistic candidate set (four or five hostels with review counts from 1
to 5000) this is fine — the outliers wash out. But the first unit test used
just two candidates:

```python
[{"rating": 5.0, "user_rating_count": 1},
 {"rating": 4.8, "user_rating_count": 180}]
```

Plain mean: `C = (5.0 + 4.8) / 2 = 4.9`. Plugging that into the formula:

```
one-review:     (1/26)*5.0   + (25/26)*4.9  = 4.9038
well-reviewed:  (180/205)*4.8 + (25/205)*4.9 = 4.8122
```

**The one-review place won.** This is the exact failure the whole feature
exists to prevent — a thinly-reviewed outlier beating a well-established place
— and it happened because the *prior itself* was contaminated by the outlier
it was supposed to be correcting for. A plain mean gives a single review the
same voting weight as 180 reviews when computing "what's typical here," which
defeats the entire premise of Bayesian shrinkage.

**Fix:** weight the prior by review count, i.e. compute `C` as a
review-count-weighted mean rather than a candidate-count mean:

```python
C = sum(r * v for r, v in ratings_and_counts) / sum(v for _, v in ratings_and_counts)
```

Re-run with the same two candidates: `C = (5.0*1 + 4.8*180) / 181 = 4.8011`.
Now:

```
one-review:     4.8088
well-reviewed:  4.8001
```

Still extremely close (this two-candidate case is a genuine near-tie, and
`test_two_candidate_near_tie_is_acknowledged` asserts the gap is small rather
than pretending shrinkage can do more than the data supports with only two
points). But on a realistic four-candidate spread, the effect is decisive:

| Place | Rating | Reviews | Weighted score |
|---|---|---|---|
| Well reviewed | 4.8 | 180 | **4.72** (1st) |
| Very popular | 4.6 | 2,400 | 4.60 |
| One review | 5.0 | 1 | 4.18 |
| Mediocre but busy | 3.9 | 5,000 | 3.90 |

The one-review place drops from what would be 1st-by-raw-rating to 3rd — this
is the number quoted in the README/EXTENSION.md, and it's the number that
matters for the demo: it's the concrete, checkable proof the ranking isn't
just "sort by stars."

Two tests guard this specifically: `test_prior_is_weighted_by_review_count_not_a_plain_average`
(directly checks `mean_rating()` against the two known-different answers, plain
vs weighted) and `test_thin_five_star_loses_to_well_reviewed_places` (the
four-candidate end-to-end case above).

## The clustering bug: single-linkage chaining

`suggest_areas_to_stay` groups a town's hostels into walkable "areas" (Old City
vs Nimman in Chiang Mai) rather than listing 20 individual properties. The
first implementation used single-linkage agglomeration: a place joins a cluster
if it's within `radius_meters` of **any single member** of that cluster.

This is a well-known failure mode of single-linkage clustering called
"chaining," and it showed up immediately on real data: with Chiang Mai's ~20
returned hostels, each within ~700m of *some* neighbour, single-linkage merged
literally the entire result set into one cluster spanning 2,623 metres. A
"walkable area" 2.6km across is not a walkable area — it's most of a city
diameter — so the tool's entire reason for existing (helping someone pick a
neighbourhood on foot) was defeated by its own clustering algorithm.

**Fix:** switched to centroid-distance clustering with an explicit spread cap.
A place joins the nearest existing cluster only if (a) it's within
`radius_meters` of that cluster's *centroid* (not any member) and (b) joining
wouldn't stretch the cluster's max internal distance past `max_spread_meters`
(default `2 * radius_meters`). Clusters are built strongest-place-first (sorted
by weighted score descending) so clusters form around the best options rather
than whatever order the API happened to return:

```python
for place in ordered_by_score_desc:
    best = None
    for i, (clat, clon) in enumerate(centroids):
        d = haversine_m(place.lat, place.lon, clat, clon)
        if d <= radius_meters and _spread(clusters[i] + [place]) <= max_spread_meters:
            best = i  # nearest centroid that doesn't blow the spread cap
    ...
```

Result on the same Chiang Mai data: four areas, spreads of 526m–966m — genuinely
walkable — plus 2-3 standalone options for places that didn't cluster with
anything. Verified by `test_clustering_does_not_chain_a_whole_city_into_one_area`,
which constructs two clearly-separated pairs of points ~2km apart and asserts
the result is 2 clusters, not 1.

## Area labelling: stripping house numbers

Places API (New) has no "neighbourhood" field on a nearby/text search result —
the only spatial-context string available is the formatted address, e.g.
`"5/10 Soi 7, Chang Moi, Chiang Mai"`. The first label extraction just took the
first comma-separated component, which for many Thai/SE-Asian address formats
is a house number, not a street name — labels came out as `"Around 27"` or
`"Around 5/10 Soi 7"` (the house number leading the street name).

Fixed with a regex that recognises house-number patterns
(`^\d+\s*[/-]?\s*\d*[A-Za-z]?$` — matches `"27"`, `"5/10"`, `"47/5"`, `"12-14"`)
and skips past them to the next comma-separated component:

```
"5/10 Soi 7, Chang Moi, Chiang Mai"  -> "Around Soi 7"
"27, Prapokklao Road, Old City"      -> "Around Prapokklao Road"
"50200 Chiang Mai"                    -> "Around Chiang Mai"  (postcode also skipped)
```

This is explicitly documented in the tool's own output as "labels, not official
boundaries" — the label is a best-effort human-readable handle for the cluster,
not a claim about administrative neighbourhood boundaries, because Places
simply doesn't give us that data.

## Why hostel search doesn't use `includedTypes: ["lodging"]`

Places API (New)'s type taxonomy has no `hostel` type. The obvious first
attempt — searching nearby with `includedTypes=["lodging"]` — returns
overwhelmingly hotels and resorts (Shangri-La, Anantara, Marriott showed up in
early test output for a Chiang Mai "lodging" search), which is close to the
opposite of what a backpacker-focused app should surface.

Fixed by using **text search** instead of type-filtered nearby search:
`"hostels and backpacker guesthouses in {location}"`, then a secondary filter
on the results keeping only ones whose name contains a backpacker-signal word
(`hostel`, `backpacker`, `guesthouse`, `guest house`, `dorm`) or whose `types`
array still includes `lodging` as a fallback if the name filter would return
nothing. This is a real trade-off worth being explicit about: text search is a
looser match than a type filter, so it can occasionally surface a non-hostel
result if a hotel's marketing copy happens to use one of those words — but
empirically (see the live test output in `notes/08-decisions-log.md`) it
reliably returns actual hostels like "The Yard Hostel," "Stamps Backpackers,"
"Bed and Bag Station" rather than five-star resorts.

## Caching, retries, and graceful degradation

- **Cache**: `places_cache` table, key = blake2b hash of `{kind, ...query
  params}`, TTL 24h (`PLACES_CACHE_TTL_SECONDS`). Verified live: an identical
  `search_nearby` call went from 0.2s (real API round-trip) to 0.003s (cache
  hit) on repeat. This matters for demo cost/rate-limit safety — a marker
  clicking through the same conversation twice doesn't double-bill or risk a
  429.
- **Retries**: up to 3 attempts with exponential backoff + jitter
  (`(2**(attempt-1)) * 0.6 + random(0, 0.3)` seconds), only on
  `{408, 429, 500, 502, 503, 504}` or a network-level `httpx.RequestError`.
  Other 4xx errors (bad request, auth failure) are **not** retried — retrying a
  malformed request three times just triples the latency of an error that
  won't fix itself.
- **Degradation**: every tool function checks `settings.places_enabled` first
  and returns `{"configured": False, "results": [], "note": "..."}` rather than
  raising, if there's no `GOOGLE_PLACES_API_KEY`. Booking/Hostelworld links
  (`affiliate.py`) need no API key at all, so `find_hostels` still returns
  working booking links even when Places itself is unconfigured — verified by
  `test_hostel_search_still_returns_booking_links_without_a_key`. The
  system-prompt instruction for every agent using these tools says explicitly:
  "If a tool returns configured:false, say plainly that live place data is not
  available on this deployment. Never invent hostel names, ratings or
  addresses." — this is a prompt-level instruction rather than a code-level
  guard because there's no deterministic way to intercept "the model decided to
  make up a hostel name," but it's paired with the honesty-focused eval cases
  (`honesty-unknown-destination`, `discovery-honest-about-unknown-origin`) that
  specifically test for confabulation under missing data.

## Geocoding a town needs the country we already know it is in

**What it catches:** searching the wrong continent, confidently.

**The bug:** `client.geocode()` resolves a place name through Places text
search, which takes a bare string and returns whatever scores highest
*globally*. `geocode("Pai")` returns **"Public Administration International
(PAI)", 56 Russell Sq, London** — a real organisation with a strong listing —
so `get_places_recommendations("Pai", "bar")` centred its radius search on
Bloomsbury and recommended a backpacker in northern Thailand Dishoom Covent
Garden, Ronnie Scott's and the BFI IMAX. `find_hostels` partly escaped because
it searches by text ("hostels and backpacker guesthouses in Pai") rather than
by radius, but it still labelled its results with the London organisation's
name.

**How it surfaced, which is the interesting part:** it didn't, for as long as
the `GOOGLE_PLACES_API_KEY` was dead. Every call was returning `401 API keys
are not supported by this API`, the tools degraded honestly to
`configured: false`, and the agents correctly said they had no live place data.
Replacing the key on 2026-09-15 fixed the 401 and revealed this underneath.
Worth remembering when reading `/health`: "configured" means a key is present,
not that the key works or that what comes back is right.

**The fix:** `place_tools._geocode()` appends the country the corpus already
knows, via `route_data.resolve_country` — `"Pai"` → `"Pai, Thailand"`, which
resolves correctly. A location that already names a country is passed through
untouched, and so is one the corpus doesn't recognise: inventing a country for
an unknown town would be a worse failure than the ambiguity. This is the same
`resolve_country` theme as note 05's "city-awareness" section, now appearing in
a fifth place. Pinned by `test_geocode_disambiguates_a_town_with_its_country`
and `test_geocode_leaves_an_already_qualified_or_unknown_location_alone`, and
verified live: Pai bars are now The Lost Texan, Spirit Bar and Rose's
Roadhouse, all in Amphoe Pai, Mae Hong Son.
