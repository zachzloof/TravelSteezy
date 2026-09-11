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
