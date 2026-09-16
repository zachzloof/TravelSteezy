# Corpus coverage tracker

Purpose: a single place to see how much of the world the curated corpus
actually covers, at what depth, and — as importantly — what was deliberately
left out. Update this file whenever a country is added, split, deepened, or
fact-checked, so "do we cover X" and "how good is our X data" both have a
one-look answer instead of requiring a grep through `seed_data.py`.

This is a living document, not a one-time snapshot: the counts and star
ratings below reflect the corpus as of the 2026-09-14 fact-check and
expansion (see "History" at the bottom) and will drift out of date the
moment someone adds or edits a document without updating this file.

## How to read the depth rating

Each country gets a 1-5 star rating based on four things, in order of how
much they matter to an actual traveller relying on this app:

1. **Full visa/seasonal/tips triad present** (the baseline - a country with
   only one or two of the three is a stub, not real coverage).
2. **Seasonal nuance matches real climatic complexity.** A country with one
   genuinely uniform climate is honestly served by one seasonal doc; a
   country that spans multiple climate zones (coastal desert + highlands +
   Amazon, or a whole-country wet/dry split) needs two, and gets one anyway
   if it doesn't, that's a real depth gap, not a stylistic choice - see
   `seasonal-india`/`seasonal-india-south` and `seasonal-peru-highlands`/
   `seasonal-peru-coast-amazon` for what "did it right" looks like.
3. **Route-doc density relative to the country's actual size and
   complexity.** Three route docs is deep coverage for a small, linear
   backpacker circuit (Cambodia) and shallow coverage for a continent-sized
   country with several genuinely separate regions (Brazil, Australia). This
   is judged relative to the country, not as a flat number.
4. **Benefit from region-wide supplementary docs.** Southeast Asia and South
   Asia both have a stack of cross-country `tips` documents (visa-run
   comparison, diving, solo female travel, street food safety, and others)
   that meaningfully deepen every country in those regions beyond what their
   own three-doc triad shows. A country in a region with no such
   supplementary layer yet (South America, East Asia, Oceania, as of this
   writing) is rated on its own documents alone.

Ratings are a judgment call made by whoever last touched this file, not a
formula - the point is a consistent, explainable ordering, not false
precision. If a rating looks wrong, that's a signal to add depth, not to
argue with the star count.

## Coverage table

| Country | Visa | Seasonal | Tips | Routes | Depth | Notes |
|---|---|---|---|---|---|---|
| Thailand | Yes | 1 doc | 1 doc | 3 | ★★★★★ | Flagship country - deepest prose, most-iterated, benefits from all 12 SE Asia region-wide tips docs |
| Vietnam | Yes | 1 doc | 1 doc | 6 | ★★★★★ | Widest route network in SE Asia (Hanoi/Hoi An/HCMC/Da Lat/Hue/Sapa as origins) |
| Cambodia | Yes | 1 doc | 1 doc | 5 | ★★★★★ | Dense route coverage (Siem Reap/Phnom Penh/Sihanoukville/Kampot/Battambang) for a small country |
| India | Yes | 2 docs | 1 doc | 10 | ★★★★★ | Deepest route network in the whole corpus (10 origin cities); north/south seasonal split is genuinely warranted |
| Laos | Yes | 1 doc | 1 doc | 4 | ★★★★ | |
| Indonesia | Yes | 1 doc | 1 doc | 3 | ★★★★ | Bali-centric; wider archipelago (Sumatra, Sulawesi, further Java) thinner |
| Malaysia | Yes | 1 doc | 1 doc | 3 | ★★★★ | |
| Philippines | Yes | 1 doc | 1 doc | 3 | ★★★★ | |
| Nepal | Yes | 1 doc | 1 doc | 2 | ★★★★ | Thin route count offset by deep South Asia region docs (Himalaya trekking comparison, overland logistics) |
| Myanmar | Yes | 1 doc | 1 doc | 5 | ★★★★ | Real depth undercut by an explicit, correct safety caveat capping practical usefulness - see the visa doc |
| Peru | Yes | 2 docs | 1 doc | 3 | ★★★★ | Highlands/coast-Amazon seasonal split genuinely warranted (three separate climate systems) |
| Argentina | Yes | 1 doc | 1 doc | 4 | ★★★★ | Widest route network of the 2026-09 South America batch (BA/Mendoza/Bariloche/El Calafate) |
| Japan | Yes | 2 docs | 1 doc | 4 | ★★★★ | Okinawa split from the mainland doc is a real climate distinction, not padding |
| Australia | Yes | 2 docs | 1 doc | 4 | ★★★★ | North/south split is a genuine opposite-climate system; still thin for a continent (Perth/west coast effectively uncovered) |
| New Zealand | Yes | 1 doc | 1 doc | 4 | ★★★★ | |
| Sri Lanka | Yes | 1 doc | 1 doc | 2 | ★★★ | |
| Mongolia | Yes | 1 doc | 1 doc | 1 | ★★★ | Single travel-season country; thin route count matches how little of the country has independent tourist infrastructure |
| Colombia | Yes | 1 doc | 1 doc | 3 | ★★★ | |
| Ecuador | Yes | 1 doc | 1 doc | 3 | ★★★ | Galapagos treated as part of the mainland seasonal doc rather than its own document - candidate for a future split |
| Bolivia | Yes | 1 doc | 1 doc | 3 | ★★★ | |
| Chile | Yes | 1 doc | 1 doc | 3 | ★★★ | North (Atacama) vs. south (Patagonia) is as real a split as Peru's or Australia's but currently held in one doc - candidate for a future two-doc split |
| Brazil | Split by nationality | 1 doc | 1 doc | 3 | ★★★ | Continent-sized country genuinely undercovered at 3 route docs - Amazon (Manaus), the northeast beaches beyond Salvador, and Sao Paulo are all unrepresented as origins |
| South Korea | Yes | 1 doc | 1 doc | 3 | ★★★ | The country that triggered this whole review - now has a real, sourced month-by-month table instead of one live-search guess |
| China | Split by nationality | 2 docs | 1 doc | 4 | ★★★ | Full triad present and the corridor/Yunnan seasonal split is genuinely warranted, but 4 route docs (Beijing/Xian/Chengdu/Guilin) is thin for a country this size - Yunnan beyond Kunming, the northeast, and the whole west (Xinjiang, Tibet's own independent-travel ban aside) are unrepresented as origins, the same honest gap Brazil has |
| Bhutan | No (operator-arranged) | No (folded into tips) | 1 doc | 0 | ★ | Deliberately minimal by design - independent budget travel isn't possible there, see `tips-bhutan-overview`; not a gap to close, a fact to keep surfacing honestly |

**25 countries covered**, 92 curated `visa`/`seasonal`/`tips` documents, 88
`routes` documents, ~320 known place names resolvable to a country (see
`route_data.KNOWN_CITIES`).

## What's deliberately NOT covered (candidates for a future round)

Left out of the 2026-09 expansion to keep that batch high-quality rather than
wide, not because they're low-priority:

- **Mexico and Central America** (Mexico, Guatemala, Costa Rica, Belize,
  Nicaragua, Panama) - probably the single biggest real gap for an
  English-speaking backpacker audience; arguably higher priority than several
  countries already covered.
- **Southern/Western Europe backpacker staples** (Portugal, Spain, Italy,
  Greece, the Balkans) - a completely different traveller profile (rail
  passes, hostels, no visa friction for most Western passports) that this
  corpus has never modelled at all.
- **Africa** - zero coverage. Morocco and South Africa/east Africa safari
  circuits (Kenya, Tanzania) are the most commonly requested gap-year
  destinations here.
- **Rest of South America**: Uruguay, Paraguay, Venezuela and Guyana/Suriname
  were excluded from the 2026-09 batch as lower-traffic on the backpacker
  circuit than the seven added - worth revisiting if user demand says
  otherwise.

**China was on this list until 2026-09-16 and no longer is** - see the History
entry below. The "visa complexity" reasoning that kept it off the 2026-09
batch turned out to be stale even at the time it was written: China's
unilateral visa-free policy (Ireland/Australia/New Zealand since 2024, Canada
and the UK added 17 February 2026) means five of the six "Western" passports
this corpus tracks get 30 days visa-free, not the blanket in-advance
requirement the old note claimed. Worth remembering as a general lesson, not
just a China-specific correction: a reason for deferring a country is a
claim about the world at a point in time, and claims like that can go stale
just as easily as a number can - the fix, same as everywhere else in this
file, is to verify before repeating it, not to trust a previous entry's
confidence.

## Countries the app can now NAME but does not cover

Read this before concluding the corpus is inconsistent with what the assistant
offers. The curated corpus is still the 25 countries in the table above — that
number has not changed — but since decision 53 `coverage.COUNTRY_NEIGHBOURS`
holds the five *genuinely* nearest countries to each origin rather than the
nearest ones the corpus happened to cover. So a "where next" turn can put a
destination in front of the specialists that has no row here:

`singapore, brunei, timor-leste, taiwan, bangladesh, pakistan, maldives,
russia, kazakhstan, papua new guinea, solomon islands, fiji, tonga, vanuatu,
new caledonia, paraguay, uruguay, panama, venezuela`

Several were already on the "deliberately not covered" list above -
Uruguay/Paraguay/Venezuela as lower-traffic, Panama as part of the Central
America gap. That reasoning stands for *curation*. It was never a reason to
pretend they are not next door.

These are handled, not curated:

- `coverage_note` gags them by default — no figures, cannot rank first.
- `live_lookup`'s two-pass search-and-verify fills the gap at runtime, once per
  destination ever, and `coverage_note` treats a verified live hit as fully
  covered (note 03).
- With no `TAVILY_API_KEY` they stay gagged and lose to covered candidates,
  which is the honest outcome rather than a wrong one.

**If you curate any of them, they move into the table above and out of this
list** — and this is exactly the trigger the "How to extend this file" section
below describes, and exactly what happened to China. The remaining nineteen
were not curated in decision 53 because doing so would have meant writing
unverified dorm prices, visa fees and monthly climate ratings for places like
Vanuatu and Kazakhstan, which is what the rule at the top of this file exists
to prevent.

## How to extend this file

When adding a country:
1. Add its row to the table above with real document counts, not estimates -
   pull them from `seed_data.py`/`route_data.py` rather than guessing.
2. Justify the star rating in the Notes column using the four criteria
   above, in one sentence.
3. If it's a genuinely multi-climate country, decide the one-doc-vs-two-doc
   seasonal question explicitly and say why, the same way the India and Peru
   entries do - don't split by default, and don't skip a split a country
   clearly needs.
4. Update the "N countries covered" summary line below the table and the
   "What's deliberately NOT covered" list (remove what you just added).
5. Re-run `python -m scripts.ingest_rag --wipe` (full reingest, not additive
   - see the docstring on `backend/rag/store.wipe()` for why a wipe is
   needed rather than an additive upsert) and confirm the smoke test at the
   bottom of that script still passes.

## History

- **2026-09-14: Fact-check + South America/Korea/Japan/Australia/NZ
  expansion.** Triggered by a user catching a wrong live-sourced seasonal
  verdict for South Korea (September wrongly rated "avoid"). Root cause
  traced to `backend/rag/live_lookup.py::classify_season` reading one
  generic annual passage too bluntly for month-specific judgment - fixed at
  the code level (tighter prompt, month-specific search query), not just for
  Korea. Separately fact-checked the original 13-country curated corpus
  against live sources (see `08-decisions-log.md` for the Thailand
  60-to-30-day visa exemption change caught in the process - effective 15
  September 2026, the day after this fact-check ran) and added 11 new
  countries: Peru, Colombia, Ecuador, Bolivia, Chile, Argentina, Brazil,
  South Korea, Japan, Australia, New Zealand. Corpus grew from 13 to 24
  countries, 53 to 88 curated documents, 60 to 84 route documents.
- **2026-09-16: China added, and the reason it had been deferred turned out
  to be stale.** Traced back from a live symptom: China was being dropped
  from Logistics/Recommendations specialist reports even after the batching
  fix in decision 56, and a Langfuse trace pointed at the real cause -
  `climate.CLIMATE_TABLE` had no entry for China at all, so it fell into the
  worst season tier by default and the coverage guard suppressed any figures
  for it. The "deliberately not covered" reasoning above (visa complexity)
  was checked rather than taken on trust, given the user's own suspicion it
  might be out of date - and it was: China's unilateral visa-free policy
  (Ireland/Australia/New Zealand since 2024, Canada and the UK added 17
  February 2026) now covers five of the six Western passports this corpus
  tracks, with the US the sole exception (240-hour transit or a standard
  L-visa). Added the full triad - one visa document with the real
  per-nationality split, two seasonal documents (the main
  Beijing-Xian-Shanghai-Guilin corridor, and Yunnan/the southwest, which runs
  on a genuinely different clock and carries the Tibet independent-travel
  restriction and Xinjiang's climate extremes as their own callouts rather
  than folding them into a false seasonal verdict) - plus a tips document,
  four town-level route documents (Beijing, Xian, Chengdu, Guilin), and seven
  country-pair route legs (Vietnam, Laos, Mongolia, Nepal, Myanmar, Japan,
  South Korea) in `routes.py`, all covering the neighbours already in
  `coverage.COUNTRY_NEIGHBOURS`'s new `"china"` entry. Rated ★★★ rather than
  higher specifically because route-doc density is thin for a country this
  size - the same honest gap Brazil has. Corpus grew from 24 to 25 countries,
  88 to 92 curated documents, 84 to 88 route documents. See decision 58 in
  `08-decisions-log.md`.
