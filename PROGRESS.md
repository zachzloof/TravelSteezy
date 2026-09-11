# Extension work in progress

Working notes so this can be resumed cleanly across sessions. Delete once the
extension is merged and the README absorbs the detail.

**Session context:** extending Travel Steezy with onboarding capture, live
trip tracking, post-visit reviews, and Google Places-backed recommendation tools.

---

## Already existed before this extension (do not rebuild)

- ADK orchestrator: `turn_parser` -> parallel specialists -> `decision_weigher`
- Memory module `backend/memory/store.py` with explicit write path, audit log,
  archival-on-departure forgetting, per-account isolation
- Pinecone RAG, namespaces `visa` / `seasonal` / `tips`, 29 seed docs, live
- Langfuse tracing, nested 18-span tree per turn, live
- Auth + admin approval, 21 unit tests, 19/19 eval suite
- `visited_history` table (country-level only, no reviews, no ordering)
- `trip_profile.interests` as a free-text column

## What this extension adds

| # | Feature | Status |
|---|---|---|
| 1 | Structured schema: travel_history, wishlist, preferences, reviews, caches | DONE |
| 2 | Memory store functions for the above | DONE |
| 3 | Google Places tools + Bayesian ranking + cache + affiliate links | DONE |
| 4 | RAG `routes` namespace + experience feedback loop | DONE |
| 5 | Onboarding agent (conversational, agent-driven) | DONE |
| 6 | Trip tracking auto-detection + wishlist promotion | DONE |
| 7 | Post-visit review trigger + storage | DONE |
| 8 | API endpoints | DONE |
| 9 | Frontend (onboarding view, wishlist/history UI, review prompt) | DONE |
| 10 | Evals + tests for the new behaviour | DONE |
| 11 | README update | DONE (docs/EXTENSION.md) |

---

## Key decisions taken

- **`visited_history` is superseded by `travel_history`**, which adds city/town
  granularity, explicit ordering, a source column, and review fields. A migration
  copies old rows across. The old table is kept and still written to, so nothing
  that reads it breaks; `travel_history` is the one agents query.
- **Places API key**: `GOOGLE_PLACES_API_KEY` is set and verified live against
  Places API (New). Tools still degrade to `configured: false` without it.
  The separate `GOOGLE_API_KEY` in .env is unrelated and unused by this app.
- **Bayesian ranking** lives in `backend/places/ranking.py` so it is unit-testable
  independently of any API call. Verified: a 5.0-from-1-review place drops from
  1st to 3rd behind a 4.8-from-180.
- **Clustering uses centroid distance + a spread cap**, not single-linkage, which
  chained all 20 Chiang Mai hostels into one 2.6km "area".
- **Hostels go through text search, not the `lodging` type**, which returns hotels.
- **Feedback loop**: accepted/rejected recommendations and post-visit reviews are
  written to a new Pinecone namespace `experience`, retrievable alongside the
  curated corpus. Verified end to end against live Pinecone.
- **`routes` namespace** holds 16 city-level hop documents ("onward from Chiang
  Mai"), because the original corpus is country-level and cannot answer
  "where next from here". `backend/rag/route_data.py` also provides the city
  vocabulary used for visit detection.
- **Watch out for heredoc backslash loss**: writing regex via `cat <<PYEOF` ate
  `` into literal 0x08 bytes once. Use the Write/Edit tools for regex, and
  `python -c` scans for control bytes after bulk edits.

- **Onboarding is TWO agents**, an extractor (JSON only) and a conversationalist.
  One agent asked to do both reliably produced the chat and silently dropped the
  structured block, so nothing was captured and it looped asking the same
  question. Progress is judged from stored data (`travel.onboarding_gaps`), never
  from the model claiming which step it is on.
- **No-op writes are not audited**: re-mentioning a place you are already known to
  be in must not appear in the "just remembered" panel.

- **Town vs country granularity bit twice**: the climate/route tables are keyed by
  country, and once candidates arrived at town level an exact lookup returned
  "unknown" and dropped a correct monsoon warning. `route_data.resolve_country`
  is now the single resolver used by climate, routes and the coverage guard.
  Separately, town departures were being written into the country-level log.
- **Eval repeat mode earns its keep**: four runs of identical code scored 89/96/
  93/89%. Use `--repeat 3` for any number worth quoting.

## Resume checklist

All extension items are done, committed, and verified live end to end.

Still open from the original build: Railway deploy with a /data volume, the
demo-safety decision (seeded demo account vs ADMIN_AUTO_APPROVE), and the
backup screen recording.

Final eval figure: see `evals/results/extension-repeat3.md` (each case run 3x).
