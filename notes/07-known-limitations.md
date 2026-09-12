# Known limitations, stated plainly

Everything here is a deliberate scope boundary or a genuine gap, not an
oversight nobody noticed. Recording it so it doesn't get re-discovered
mid-demo, and so a future contributor knows what's already been weighed and
decided rather than re-litigating it.

## Simplifications made on purpose (and why the alternative was worse)

- **Weather is a curated seasonal table, not a live forecast API.** The
  question this app answers ("should I go to Laos in July") is asked weeks or
  months ahead; a forecast API covers ~14 days and simply cannot answer it.
  The table is *more* useful for this use case than a real forecast would be,
  at the cost of being unable to flag an anomalous year or a specific storm —
  the agent prompt says so.
- **Routes are curated indicative figures, not a live flight/bus search.**
  Real-time aggregator APIs (Skyscanner, Kiwi) require commercial partnership
  access this project doesn't have, and a live price quoted weeks ahead of
  travel is not meaningfully more useful than an indicative range for the kind
  of planning this app supports.
- **`KNOWN_CITIES` is a hand-curated dict of ~90 places, not a geocoding
  service.** Fine for one region (SE Asia + Nepal + Sri Lanka); would need to
  become a real gazetteer or Google Geocoding-backed lookup before covering
  more regions. The `resolve_country` fallback chain (substring match as a
  last resort) is a pragmatic hedge, not a robust NLP solution — it will
  mis-resolve a place name that happens to contain another place name as a
  substring (this hasn't been observed in practice with the current
  vocabulary, but it's a real edge case with a larger gazetteer).
- **Area labels come from address-string parsing, not real neighbourhood
  boundaries.** Places API (New) doesn't return neighbourhood data on a
  nearby/text search. The label is honestly described as such in the tool's
  own output ("Area labels are derived from the street of the strongest
  listing, not official neighbourhood boundaries.").

## Things that are implemented but only lightly load-tested

- **`asyncio.gather` fan-out under real concurrent load.** Verified correct
  under the eval harness's sequential-but-repeated load (81 turns across a
  15-20 minute run), and manually under a handful of concurrent curl requests,
  but never load-tested with many simultaneous real users. The per-turn
  `ToolRecorder` uses a `contextvars.ContextVar`, which is correctly
  task-local under `asyncio` — this is architecturally sound for concurrent
  requests — but hasn't been stress-tested.
- **The Places cache under high write contention.** `places_cache` uses SQLite
  with WAL mode (`PRAGMA journal_mode = WAL`), which allows concurrent reads
  during a write, but SQLite fundamentally serialises writers. Under heavy
  concurrent cache-miss traffic (many users asking about many different towns
  simultaneously, all missing cache), writes could serialise and add latency.
  Not observed at demo scale; worth knowing if this were to see real traffic.
- **The onboarding hard-cap (6 turns) has not been tested against an
  adversarial or confused user** who gives ambiguous answers for all 6 turns —
  behaviour in that case is "onboarding force-completes with whatever partial
  data was captured," which is reasonable but hasn't been exercised in an eval
  case.

## Known gaps in eval coverage

- **No eval case directly tests the Places-tool retry/backoff logic** against
  a simulated 429 or 5xx. The retry logic (`client.py::_post`) is exercised by
  unit-adjacent reasoning (the code path is straightforward) but not by an
  actual eval turn that forces a Places failure and checks graceful recovery.
- **No eval case tests the `places_cache` TTL boundary** (a cache entry that's
  23h59m old vs 24h01m old). The TTL query itself
  (`strftime('%s','now') - strftime('%s', created_at) < ttl`) is simple SQL
  and was manually verified once, not covered by an automated test.
- **Cross-account isolation is tested for `/profile/me` and the chat turn's
  memory, but not explicitly for `/travel/me` and its sub-routes** with a
  dedicated eval case — it *is* tested at the unit-test level
  (`test_travel_memory_is_isolated_per_account`) and the endpoints follow the
  identical `current_user` dependency pattern as the already-isolated routes,
  so the risk is low, but there's no eval-level assertion specifically for
  "account A's wishlist never appears in account B's chat context."

## Things that would need to change before this scales past a demo

- **The `SUPPORTED_COUNTRIES` / `KNOWN_CITIES` vocabulary is a fixed, closed
  list** — Southeast Asia, South Asia (Nepal, Sri Lanka, India, Bhutan),
  Mongolia and Myanmar, as of the corpus expansion in note 03. Every guard,
  every table, every eval case assumes this exact scope. Extending to another
  region means extending all three data files (`seed_data.py`,
  `route_data.py`, `climate.py`'s `CLIMATE_TABLE`) in lockstep, or the
  coverage guard will (correctly, but confusingly for a user) start refusing
  destinations that feel like they should obviously be covered. The
  `unverified` live-lookup tier (note 03) narrows this limitation for
  factual gaps when `TAVILY_API_KEY` is set, but does not remove it: a
  destination still needs `CLIMATE_TABLE`/`route_data.py` entries before the
  structured tools (seasonal verdicts, onward-hop graphs) can say anything
  about it at all, live search or not.
- **The onboarding extractor and turn parser both make one full LLM round-trip
  per turn on top of the specialist calls.** For a chat-latency-sensitive
  product this is a real cost (visible in the Langfuse spans: `turn_parser`
  alone is typically 1.5-2.5s). Not a correctness problem, but a
  cost/latency one worth knowing about if response time becomes a demo concern.
- **No rate limiting on `/chat` or the Places-backed endpoints beyond the
  Places response cache itself.** A malicious or just very chatty user could
  drive real OpenAI/Pinecone/Places API cost. Fine for a course demo behind
  admin-gated registration; would need real rate limiting before any public
  deployment.

## What "verified" means in this project's claims

Every number and behavioural claim in the README, EXTENSION.md, and these
notes was checked against either: a passing automated test, a passing eval
case with its results file committed, or a manually-run command whose actual
output is quoted (not paraphrased) in the relevant note. Where something is a
design intention rather than a verified fact, it's flagged as such (e.g. "not
observed at demo scale" above, rather than a bare unqualified claim). If a
future change makes any of these notes stale, the note itself will be wrong —
these were accurate as of the commit they were written for, not guaranteed to
stay accurate as the code evolves around them.
