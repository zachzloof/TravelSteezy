# RAG and retrieval

## Namespace design

Five Pinecone namespaces, each searched by exactly one kind of agent call:

| Namespace | Content | Searched by |
|---|---|---|
| `visa` | Nationality-aware entry rules, costs, lead times | `search_visa_rules` (logistics agent) |
| `seasonal` | Monsoon windows, hazard seasons, prose detail | `search_seasonal_notes` (weather agent) |
| `tips` | Dorm prices, routes, safety/ethical notes | `search_backpacker_tips` (recommendations agent) |
| `routes` | City-level onward-hop knowledge ("from Chiang Mai...") | `discover_next_destinations` (discovery agent) |
| `experience` | Runtime-written reviews and recommendation outcomes | `get_traveller_feedback`, folded into recommendations |

The country-level corpus (`visa`/`seasonal`/`tips`) and the town-level corpus
(`routes`) are deliberately different granularities in different namespaces
rather than one mixed namespace, because the query shapes are different: "visa
rules for a UK passport into Cambodia" is a country query; "where do people go
next from Chiang Mai" is a town query. Mixing them would mean every query has
to hedge its metadata filter across both granularities, which either misses
results or (worse) returns town-level noise for a country-level question.

## The unscoped-retrieval-fallback removal

Early version of `rag_store.search`: if a destination-scoped query (e.g.
`destinations=["mongolia"]`) came back empty, it retried the same query
**unscoped** — searching the whole namespace with no destination filter — on
the theory that "some regional context is better than nothing."

This was actively harmful. The eval case `honesty-unknown-destination` (asking
about Mongolia and Uzbekistan, which the corpus doesn't cover) failed because
the unscoped fallback handed the Recommendations agent passages about
*completely different countries* the corpus does cover, and the model — not
unreasonably, given it was handed real-looking retrieved text — used them to
confabulate specific visa rules, prices, and a seasonal verdict for Mongolia,
then ranked it first.

Fix: removed the fallback entirely. A scoped search that matches nothing now
returns nothing, full stop. An empty result is honest; a wrong-country result
dressed up as relevant is a worse failure than no result. This is paired with
the coverage guard (see note 05) which tells the model in-prompt, computed in
code, exactly which destinations it has zero data for, so it doesn't need
retrieval noise to realise that — it's told directly.

## `resolve_country`: town names breaking country-keyed lookups

This bug appeared **twice**, independently, in two different country-keyed
tables, which is why it got pulled out into one shared resolver rather than
patched in each call site.

**First appearance:** `backend/agents/climate.py`'s `CLIMATE_TABLE` is keyed by
country name (`"malaysia"`, `"thailand"`, etc.). Once the extension's turn
parser started returning candidates at town granularity — "Perhentian Islands,
Malaysia" rather than just "Malaysia" — an exact-match lookup against
`CLIMATE_TABLE` returned nothing, `assess()` fell into its "unknown" branch, and
a correct northeast-monsoon closure warning for the Perhentians (which *is* in
the table, under "malaysia") silently disappeared. Caught by the eval harness's
`--repeat 3` mode: `season-malaysia-east-coast-closed` was passing 1 run in 3,
which any single run would have reported as either a clean pass or a clean
regression — the flakiness itself was the symptom, and it only became visible
because the harness ran the case more than once (see note 06).

**Second appearance:** `backend/agents/routes.py`'s `ROUTES` table is keyed by
a sorted pair of country names. Same exact-match problem, same fix needed.

**The fix**, `backend/rag/route_data.py::resolve_country`:

```python
def resolve_country(location: str | None) -> str | None:
    key = (location or "").strip().lower()
    if key in COUNTRIES: return key
    if key in KNOWN_CITIES: return KNOWN_CITIES[key]
    for part in key.replace("/", ",").split(","):        # "Bali, Indonesia"
        part = part.strip()
        if part in COUNTRIES: return part
        if part in KNOWN_CITIES: return KNOWN_CITIES[part]
    for country in COUNTRIES:                              # "...near Bali..."
        if country in key: return country
    for city, country in KNOWN_CITIES.items():
        if city in key: return country
    return None
```

Both `climate.assess` and `routes.lookup` now try an exact match first, then
fall back to `resolve_country` before giving up and returning "unknown" /
"known: false". A genuinely uncovered place (Reykjavik) still correctly
resolves to `None` and stays honestly unknown — the fix widens what counts as
"we have data for this," it doesn't weaken the honesty guarantee for what we
don't.

The coverage guard (`coverage.classify` / `coverage.resolve_to_covered`) got
the same treatment for the same reason: treating "Perhentian Islands, Malaysia"
as *uncovered* (because it's not a literal string in `SUPPORTED`) made the
coverage warning suppress a correct, in-corpus monsoon warning — the guard
designed to stop confabulation was itself causing a different kind of data
loss.

**General lesson:** any table keyed by a controlled vocabulary (country names,
in this case) needs one canonical resolver the moment inputs can arrive at a
different granularity than the table's keys, and that resolver needs to be
shared across every call site that keys off the same vocabulary — patching
each site independently is how the same bug shipped twice.

## City detection and a heredoc bug worth remembering

`rag_store.detect_cities` does regex word-boundary matching against
`route_data.KNOWN_CITIES` (86 entries), sorted longest-first so "Gili
Trawangan" isn't reduced to a shorter overlapping match. During development,
one heredoc-based file edit silently converted every `\b` regex boundary marker
into a literal backspace byte (`0x08`) — bash/here-string escaping ate the
backslash and the shell interpreted `\b` as an actual backspace control
character rather than passing the two-character sequence `\` `b` through to
Python. The function ran without raising (backspace bytes are legal inside a
Python string literal), but silently matched nothing, because
`re.search(r"\x08chiang mai\x08", text)` — with real backspace characters — never
matches ordinary text.

This is recorded here because it's a class of bug that's easy to reintroduce:
**any time a file is edited via a shell heredoc rather than a dedicated
file-write tool, grep the result for stray control bytes before trusting it.**
A repo-wide scan (`any(c<9 or 11<=c<=12 or 14<=c<=31 for c in file.read_bytes())`)
was added as a manual check step after this was found, and should be run again
if heredoc-based edits are used in future.

## The `experience` namespace: feedback loop, not just storage

Two write paths feed `experience`:

- **Reviews** (`experience.ingest_review`) — only when the free-text notes are
  ≥12 characters. A bare star rating with no prose is deliberately *not*
  indexed: it adds a document to the vector store with almost no retrievable
  signal (a number encoded as English text embeds close to nothing useful) and
  just dilutes real feedback.
- **Recommendation outcomes** (`experience.ingest_outcome`) — written whenever
  a wishlist item is promoted to `travel_history` (accepted) or explicitly
  dropped (rejected), via `tracking.apply_tracking`.

Documents carry `account_id` (an integer) but never a username or any other
PII, and the Recommendations/discovery agent prompts explicitly instruct
presenting this content as "other backpackers' opinions, anonymously, never as
established fact" — it's retrieved and quoted, not treated as ground truth the
way the curated `tips`/`visa`/`seasonal` corpus is. `share=False` on a review
keeps it entirely out of this namespace (private to the account), checked
before `ingest_review` is even called.

## `KNOWN_CITIES` vocabulary boundaries

`route_data.py` hand-curates ~86 town/city names across the Southeast
Asia + Nepal + Sri Lanka corpus, split into `CITY_TO_COUNTRY` (towns that are
route-document origins, 16 of them) and `EXTRA_CITIES` (towns mentioned only as
onward hops or in seed content, not themselves route origins, 70 of them). This
is a closed vocabulary — a real product would eventually want a proper
gazetteer or geocoding-based resolution rather than a hardcoded dict — but for
the scope of this app (one region, ~90 known places) a dict is simpler,
faster, has zero external dependency, and is exhaustively enumerable in a code
review. See note 07 for the explicit tradeoff statement.

(Since extended — see "Corpus expansion" below — to ~130 places across a wider
region; the tradeoff statement above still holds, just at a larger N.)

## Corpus expansion: India, Mongolia, Myanmar and Bhutan added, 45 → 99 documents

Requested directly: the corpus covered Southeast Asia plus Nepal and Sri Lanka
only, and India and Mongolia specifically were named as obvious, real gaps.
Added, alongside genuine depth elsewhere rather than just bolting on two
countries:

- **Four new countries.** India and Myanmar get full visa/seasonal/tips triads
  (India's seasonal split into two documents — north/central vs. south/coastal
  — because a single doc undersold how differently the two halves behave
  seasonally, the same reasoning Vietnam's single nuanced doc already applied
  at a smaller scale). Mongolia gets the same triad. Bhutan gets one combined
  `tips` document rather than a full triad, because its defining fact for a
  *backpacker* assistant is that independent budget travel isn't possible
  there (a mandatory operator-arranged package plus a USD 100/night
  Sustainable Development Fee) — three separate documents would imply a normal
  backpacker circuit exists when the honest answer is "this is a save-up-for-
  a-short-trip destination," and the tips document says that plainly.
- **31 new `routes` documents**: a full India sub-circuit (Delhi, Rishikesh,
  Varanasi, Goa, Jaisalmer, Hampi, Jaipur, Udaipur, Amritsar, Mumbai), a
  Myanmar circuit (Yangon, Bagan, Inle Lake, Mandalay, Kalaw), Mongolia's
  Ulaanbaatar gateway, and 15 fill-in documents for towns that existing routes
  already named as onward hops but that had no route document of their own
  (Vientiane, Nong Khiaw, Da Lat, Hue, Sihanoukville, Kampot, Sapa, Coron,
  Siargao, Canggu, Gili Trawangan, Pokhara, Kandy, Battambang, Langkawi) —
  giving each of them their own onward-hop content rather than only existing
  as someone else's destination.
- **12 region-wide `tips` documents** (connectivity/long-stay work, diving,
  solo female travel, visa-run comparison, street food safety, South Asia
  overland logistics, Himalaya trekking compared across Nepal and India, lost
  passport/emergency procedure, ethical wildlife tourism, party-town
  comparison, money/banking, budget-airline strategy) — depth that cuts across
  countries rather than duplicating what a country-specific document already
  says, checked against the existing docs before writing each one specifically
  to avoid restating the same fact twice under a different heading.
- **`CLIMATE_TABLE` (climate.py) got matching entries** for all four new
  countries. This is a direct application of the lesson under "town names
  breaking country-keyed lookups" above, generalised: coverage.py's
  `SUPPORTED` set is `CLIMATE_TABLE keys | KNOWN_DESTINATIONS`, so a country
  present in the RAG seed data but absent from `CLIMATE_TABLE` would be
  "supported" for visa/tips/seasonal-prose purposes while `check_seasonal_conditions`
  quietly returned `known: false` for the exact same country — the same class
  of two-sources-of-truth disagreement that caused the original
  `resolve_country` bug, just at the country-table level instead of the
  town-vs-country level. Added in lockstep specifically to not reintroduce it.

**The one required side effect: `honesty-unknown-destination` had to change.**
That eval case tested the coverage guard using Mongolia and Uzbekistan as
known-uncovered probes. Adding Mongolia to the corpus would have made the
eval meaningless (asserting honesty about a destination that is now, correctly,
answered with real data) rather than fixing anything. The case now uses Nauru
and Uzbekistan instead — both genuinely outside every corpus this app holds —
so the eval keeps testing the thing it was built to test rather than silently
starting to pass for the wrong reason.

## The `unverified` namespace: closing gaps without lowering the honesty bar

Feature request, considered carefully because it cuts close to a mistake this
project already made and fixed once (see "The unscoped-retrieval-fallback
removal" above): when a scoped search comes back empty, don't just say "no
data" — look it up live, check it, and remember it for next time.

The literal version of that request — ask the LLM to find out, ask the LLM to
double-check itself, trust the result — was rejected. Asking a model to verify
its own recollection against nothing is not verification; it's the same blind
spots marking their own homework, and it would have quietly undermined the
exact guarantee `coverage.py` and the `honesty-unknown-destination` eval exist
to protect: that this app never states a visa fee or a monsoon month it cannot
source.

What got built instead, in `backend/rag/live_lookup.py`, keeps the same shape
but changes what "verify" means:

1. **A real web search** (Tavily, gated behind `TAVILY_API_KEY`) for the
   specific factual question — not the model's memory.
2. **A synthesis LLM call that may only answer from the search results**,
   instructed to say `NOT_FOUND` if they don't actually answer the question.
3. **A second, separate LLM call that checks the first call's own draft
   against those same search results**, sentence by sentence, and strips
   anything not directly supported. Still the same model's blind spots in
   principle, but now checking against external fetched text rather than
   against nothing — a materially different and weaker-but-real form of
   grounding, not a rebrand of "ask twice."
4. **Ingested into a new `unverified` namespace** — never into
   `visa`/`seasonal`/`tips` — with the source URLs and fetch date kept in
   metadata, and the disclaimer baked directly into the document's own text
   (`[UNVERIFIED - live-sourced ...]`) so it survives being formatted by the
   same generic `format_passages()` every other namespace uses, with no
   namespace-specific formatting code required.
5. **Cached, not repeated.** `get_or_fetch` checks the `unverified` namespace
   before doing anything live; a destination/topic pair is searched, drafted
   and verified once, and every subsequent turn is an ordinary RAG hit. This
   is the literal "next time it is in the RAG" the feature was asked for.

**What deliberately did NOT change:** `coverage.py`'s `SUPPORTED` set is still
curated-only. A destination filled in via live search is not "covered" for the
purposes of the hard honesty guard — it still cannot be ranked first, and the
specialist prompts (`graph.py`) are instructed to flag any `live_sourced: true`
result as unconfirmed every time it's used, with the same confidence level as
`experience` namespace anecdotes, not curated fact. Closing a knowledge gap and
lowering the bar for what counts as verified are two different changes; this
project has already paid once (in eval regressions) for conflating "some data"
with "correct data," and the whole point of the three-tier design (curated /
unverified / experience, each presented at a different confidence level) is to
not pay for it twice.

Deliberately not built yet (per explicit instruction): a human-review step
before promoting anything out of `unverified`. The namespace is additive and
inert by default — nothing changes for anyone who hasn't set
`TAVILY_API_KEY` — so this can be added later without touching anything that
exists today.

### Follow-up: source URLs were captured but never surfaced

Caught by direct pushback, not by testing: "verified" here was being read as
"true," when what the two-pass pipeline actually checks is narrower — that
the drafted answer is *supported by the fetched search-result text*, not that
the search results themselves are current or correct. That's a real, useful
check (it catches the model drifting back onto its own memory), but it's not
a truth guarantee, and framing it as flatly "unverified" with no way to
actually check it made the whole tier read as worthless rather than as
"sourced, one step short of curated."

The concrete gap: `fetch_and_verify` was already storing `source_urls` in the
document's metadata, but `format_passages()` — the one function every
namespace's tool result is rendered through — only ever printed
`source_id` and `destination`. The link was captured and then never reached
an agent, a prompt, or a user. Fixed by having `format_passages` include
`sources=<url, url, ...>` in its header whenever a hit's metadata carries
`source_urls` (a no-op for every curated hit, which has no such field), and
by updating the `live_sourced: true` prompt rules in three places in
`graph.py` to require citing at least one of those URLs in the reply, not
just repeating the disclaimer. The underlying trust tier is unchanged — this
doesn't promote `unverified` content to curated status, it just makes the
"go check this yourself" instruction something the traveller can actually
act on in one click.

### Second follow-up: a successful live lookup was being fetched, verified, ingested — and then thrown away

Caught by direct pushback, again: "make sure the Tavily data is actually
usable, not just stored." Correct catch. `coverage.coverage_note()` is
injected into the Decision-Weigher's prompt with the exact wording "You MUST
NOT state ANY figure for them," computed from `classify()` — which is
curated-only and knows nothing about `unverified`. So even a destination that
live-lookup successfully searched, verified, and ingested THIS turn would
still get the absolute "no figures" instruction, because the guard had no way
to know a lookup had succeeded. The feature would work exactly as designed
right up until the final synthesis step, which would then override it. Fetch,
verify, ingest, get overruled — a whole pipeline for the reply to say "no
data" anyway.

**Why this couldn't be fixed by just deleting the restriction.** The guard
exists because the model does not reliably self-limit to "only state what a
tool returned" without a deterministic, destination-specific block — that is
the literal lesson of `honesty-unknown-destination`. Removing the block
entirely to let live-sourced data through would also remove the protection
for the case where NOTHING was found (live lookup unconfigured, Tavily
returns nothing, or both LLM passes say `NOT_FOUND`) — which is still the
common case for most destinations, most of the time.

**The fix is two-stage, matching when each fact is actually knowable:**

1. `coverage_note()` now takes an optional `live_sourced` set and produces up
   to two separate blocks instead of one: a `LIVE-SOURCED DATA FOUND FOR`
   block (full permission to state figures, ranked normally, disclosure
   required) for destinations in that set, and the original
   `COVERAGE WARNING - NO DATA HELD FOR` block (unchanged, absolute) for
   everything else.
2. **Specialist-level call** (`runner.py`, before any tool has run):
   `live_sourced` is necessarily empty — nobody knows yet whether this turn's
   lookup will succeed — so every unsupported candidate gets the strict block.
   That block now carries one added sentence: an explicit exception for the
   specialist's OWN tool call coming back `live_sourced: true`, so the
   specialist isn't holding two contradictory instructions when its own tool
   result and the pre-computed guard disagree.
3. **Decision-Weigher-level call** (`runner.py::_run_comparison`, after
   `asyncio.gather` on the specialists completes): recomputed from what
   actually happened. The per-turn `ToolRecorder` is one mutable object
   referenced (not copied) by every specialist task spawned under it — a
   property already relied on elsewhere in this codebase for the eval
   assertions — so reading `recorder.retrieved` after the fan-out reveals
   every `unverified`-namespace hit any specialist got this turn. Those
   destinations move to the permissive block; everything else stays under the
   strict one. `DECISION_INSTRUCTION`'s hard rule #4 was reworded to match:
   only a destination in the `NO DATA HELD` block is barred from ranking
   first.

Net effect: a destination with genuinely nothing behind it (the case the
guard was built for) is exactly as restricted as before — the eval keeps
testing what it tested. A destination that live-lookup actually found and
verified this turn is now used at full strength in the final reply, disclosed
but not discounted, which is what "closing the gap" was supposed to mean in
the first place.

### Third follow-up: the `unverified` namespace itself was the bug

Reproduced live, 2026-09-13: a traveller in Bali with Japan and Australia on
their wishlist asked "where next" and got told this app holds no data for
either — reasonable, since neither is curated — but the reply also failed to
use the live lookup that should have covered the gap, even though calling
`search_visa_rules("japan", ...)` directly returned a perfectly good,
correctly-sourced live answer.

The cause was the `unverified` namespace design itself. It was keyed only by
`destination`, with no `kind` (visa vs. tips vs. routes vs. seasonal). Once
ANY question about a country got a live answer, `get_or_fetch`'s cache check
found that same document for every OTHER kind of question about the same
country — a visa lookup for Japan came back with backpacker-budget tips,
because tips had been live-searched for Japan earlier in the same turn.
Quarantining live-sourced content in its own namespace, meant to keep the
honesty guarantee visible and separate, instead broke the one thing retrieval
scoping depends on: that a namespace search returns passages actually
relevant to the question asked.

**The fix removes the separate namespace rather than patching around it.** A
live-sourced document is now ingested into the SAME namespace curated content
of that kind already uses — a live visa answer for Japan goes into `visa`,
right where `search_visa_rules` already looks. The trust distinction that
namespace used to carry — "was this hand-curated or fetched this session" —
moved to a `metadata.origin = "live"` field instead; curated seed docs carry
no such field. Everywhere that used to check `namespace == "unverified"`
(`search_visa_rules`/`search_backpacker_tips`/`search_seasonal_notes` in
`tools.py`, and the Decision-Weigher's `live_sourced` set in
`runner.py::_run_comparison`) now checks `metadata.origin == "live"` instead.
Nothing about the disclosure behaviour changed — a live-sourced hit is still
flagged unconfirmed with its source link, same as before — only *where the
document lives* and *what a real per-kind search actually finds* changed.

One side effect worth naming: this also means a live-sourced document is now
a genuine, permanent improvement to that namespace's coverage for every
future turn — not just a same-turn patch. The next traveller who asks about
Japan's visa rules gets served that same verified-once answer directly out of
the curated-shaped `visa` namespace, correctly scoped, instead of triggering
a fresh search or (worse, under the old design) getting handed an unrelated
cached document. The old `unverified` namespace, now unused, was deleted from
the live Pinecone index along with the handful of stale dev/eval artifacts
that had accumulated in it (`nauru`, `uzbekistan`, `perhentian-islands`, a
literal `-test-ping` id) — none of it was curated content or real traveller
`experience` data, so nothing of value was lost.

A separate, code-level bug in the same turn compounded this: the "where
next from here" fallback (`runner.py`, the country-neighbour + wishlist
candidate picker used when only a country, not a town, is known) ranked
seasonal fit with `{"good": 0, "mixed": 1, "unknown": 2, "avoid": 3}` —
treating "we hold no seasonal data at all" as *better* than "we know this is
a bad month." That let wishlist countries with zero curated coverage (Japan,
Australia) outrank actually-covered neighbours (Thailand, Philippines) simply
because the covered ones were in their real, known-bad season that month.
Reordered to `{"good": 0, "mixed": 1, "avoid": 2, "unknown": 3}` so "unknown"
is treated as the least favourable tier, not a safer bet than a known-bad one.

### Fourth follow-up: a wishlist mostly outside the curated table still lost to a known-bad month

Follow-up to the "unknown vs. avoid" reorder above, caught the same day by
direct pushback with a real example: a traveller with ten wishlist countries
in Bali got served Vietnam and Thailand - both genuinely in typhoon/monsoon
season that month - because those were the only two candidates the curated
table could rate at all. The other eight (Japan, Australia, South Korea,
Peru, Mexico, Morocco, Iceland, New Zealand, Colombia) all came back
"unknown" and, correctly per the fix above, lost to a known "avoid" - but
several of those eight were, in reality, having a genuinely good month. The
reorder fixed "unknown beating avoid unfairly"; it did not fix "avoid always
beating unknown even when unknown means good," because `climate.assess()`
simply has no opinion outside its ~15-country table - silence was still being
read as "assume the worst," which is honest but not useful when the
alternative on offer is a known-bad month.

The fix: `live_lookup.classify_season(destination, month)` turns a seasonal
passage into an actual good/mixed/avoid rating for wishlist countries the
table can't rate, reusing the exact search-once-cache-forever mechanism
`get_or_fetch` already provides for the "seasonal" kind - the expensive part
(a Tavily search plus the two-pass synthesis/verify) still runs at most once
per destination ever; classifying a different month later is one cheap
completion against the already-fetched, already-verified passage. Wired into
the candidate ranking in `runner.py`: up to 6 wishlist countries the table
can't rate get checked concurrently, highest wishlist-priority first (so a
long wishlist cannot turn one turn into a dozen live searches), before the
season/distance/priority sort runs. Re-run against the reproduction above,
the result became South Korea, Australia and Peru - all genuinely good-season
- instead of Vietnam and Thailand.

### Fifth follow-up: the disclosure requirement itself was the wrong call

Direct instruction, not a bug report: stop presenting live-sourced content as
lesser. Every one of the last five follow-ups above treated "disclosed as
unconfirmed" as the safety property worth protecting - the `[UNVERIFIED -
live-sourced ...]` prefix baked into every live document's own text, the
"you MUST say plainly it is unconfirmed" clause in three separate specialist
prompts, the `coverage_note()` block requiring a source link and an
unconfirmed label, and `_enforce_live_source_disclosure()` in `runner.py` -
a code-level backstop that prepended "treat it as unconfirmed and check it
yourself" to the reply whenever any candidate was live-sourced. Working
exactly as designed, this is what a traveller actually saw: a card, correctly
and grounded via a real search plus a two-pass verify against that search's
own text, still labelled "unconfirmed" and prefaced with a doubt the app
itself had no real reason to hold.

The correction: the two-pass search-and-verify pipeline IS the verification.
A live-sourced document that passed it is real information, not a lesser
guess - treating it as inferior to curated content past that point was
manufacturing distrust in data the app had already checked. All of the
following were removed: the baked-in text disclaimer (`fetch_and_verify` now
stores the verified answer as-is), the "say plainly it's unconfirmed, include
a source link" instructions in `WEATHER_INSTRUCTION`/`LOGISTICS_INSTRUCTION`/
`RECOMMENDATIONS_INSTRUCTION` and `DECISION_INSTRUCTION`'s hard rule #4,
`coverage_note()`'s separate "LIVE-SOURCED DATA FOUND" block (a live-sourced
destination now simply isn't in the "NO DATA HELD" warning at all - same
treatment as a curated hit), and `_enforce_live_source_disclosure()` entirely.

What did NOT change: `metadata.origin = "live"` is still written and still
tracked through the `ToolRecorder` and into `coverage_note()`'s `live_sourced`
set - purely as an internal provenance marker for our own tracing and
debugging (which passage came from where, auditable later), never surfaced to
the traveller as a reason to doubt the answer. The one honesty guarantee that
remains structurally enforced, in code rather than prompted: a destination
where NEITHER curated data NOR a live search found anything at all this turn
still gets the strict "you MUST NOT state a figure" warning - fabricating
from pure parametric memory, the original `honesty-unknown-destination`
failure mode, is still caught. What changed is only the middle case: found
via a real, verified live search is no longer treated as a lesser tier than
curated. `evals/cases.jsonl`'s `honesty-unknown-destination` and
`route-live-lookup-uncurated-pair` rubrics were reworded to match - both used
to score a confident, live-sourced answer as a failure unless hedged, which
would have graded the new, correct behaviour as broken.

### Sixth follow-up: not every tool that needed the fallback had it

Caught live, immediately after the fifth follow-up shipped: a "where next"
reply picked South Korea (correctly - `classify_season` had rated it "mixed"
for September during candidate selection) and then, in the same reply,
reported it as "unknown, no verified seasonal data" - a direct contradiction
inside one turn's own output.

The cause: `check_seasonal_conditions` - the Weather specialist's tool for
producing the actual rating shown in the verdict - was a pure
`climate.assess()` lookup with NO live fallback at all, unlike every other
curated-data tool in this file (`search_visa_rules`, `search_backpacker_tips`,
`search_seasonal_notes`, `check_route`). `classify_season` was built for the
candidate-*picking* step in `runner.py` in the previous follow-up and never
wired into the tool the specialist actually calls for its rating - so
selection got smarter while the thing producing the user-facing verdict did
not, and the two disagreed within the same turn. Confirmed live: Tavily found
real South Korea seasonal data in about a second: this was not a data gap,
it was a tool that never tried.

Audited every tool for the same shape of gap rather than patching this one
instance - the instruction was "give anything that would obviously need it
the fallback, not tool-by-tool as bugs surface." Found one more:
`discover_next_destinations` (the town-level "where next from here" tool)
had the identical problem - a town outside the curated route corpus was a
dead end even though a plain "where do backpackers go after X" question is
exactly what a live search answers well. Both now fall back the same way
`check_route` already did: `check_seasonal_conditions` calls
`classify_season` when `climate.assess()` comes back "unknown" (reusing
whatever passage is already cached, so this is a cheap reclassification, not
a new search, after the first time); `discover_next_destinations` calls
`live_lookup.get_or_fetch` with `kind="routes"` when neither curated route
hits nor a `ROUTE_GRAPH` entry exist. `route_note()` (the discovery agent's
own pre-tool-call guard, the exact analogue of `coverage_note()`) had the
same absolute "you MUST NOT name onward destinations" wording with no
exception for its own tool's live search succeeding - reworded to match
`coverage_note()`'s pattern: call the tool regardless, use what it finds, and
only fall back to the honest admission if the live search also comes up
empty.

Two tools were deliberately NOT given this fallback, for the same reason as
each other: `get_traveller_feedback` is accumulated real-user review data,
not a factual question a web search can substitute for - "no traveller has
reviewed this yet" is an honest, expected state, not a coverage gap to fill.
And the Google Places-backed tools in `place_tools.py` (`find_hostels`,
`find_food_near`, `suggest_areas_to_stay`, `get_places_recommendations`) are
already live via a different provider - there is no curated layer beneath
them to fall back from, `configured: false` is the correct honest state when
`GOOGLE_PLACES_API_KEY` is unset, and a Tavily search is not a substitute for
a real-time places database anyway.

`evals/cases.jsonl`'s `discovery-honest-about-unknown-origin` (Reykjavik) was
reworded the same way as the fifth follow-up's two cases - it used to score a
live-sourced onward-route answer as a failure unless the reply admitted no
data, which would have graded the new, correct behaviour as broken.
