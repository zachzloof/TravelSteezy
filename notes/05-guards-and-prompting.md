# Code-computed guards and prompting

## The pattern

Every guard in this codebase follows the same shape, and it's worth stating the
shape explicitly because it's the single most repeated pattern in the whole
agent design:

1. A plain Python function computes a fact the model must not be allowed to get
   wrong (what's covered, what isn't, what's already known).
2. That fact is rendered as a block of text and injected into the relevant
   agent's prompt via ADK's state templating (`{block_name?}`), framed as
   **non-negotiable** — the prompt literally says "(computed in code, not
   negotiable)" so the model isn't invited to treat it as a suggestion.
3. The prompt's hard rules reference that block explicitly ("Any destination
   named in the COVERAGE WARNING above CANNOT be ranked first").

This exists because prompting alone — "don't make things up," "be honest about
what you don't know" — is not reliable under pressure from a well-formed
question. Every guard listed below was added *after* an eval case caught the
model violating the equivalent prompt-only instruction that existed before the
guard was code-computed.

## `coverage_note` / `coverage.classify`

**What it catches:** inventing visa rules, prices, and seasonal verdicts for
destinations outside the curated corpus.

**The eval case that caught it:** `honesty-unknown-destination` — asked to
compare Mongolia and Uzbekistan (genuinely outside the corpus), the assistant
invented specific dorm prices ($5-15/night for Mongolia, $8-15 for Uzbekistan)
and ranked Mongolia first, with a fluent, confident tone that gave no signal it
was guessing.

**How it works:** `classify(candidates)` splits a list of destination strings
into `supported`/`unsupported` by checking each against `SUPPORTED` (the union
of the climate table's countries and the RAG corpus's known destinations) via
`resolve_to_covered` (which itself uses `route_data.resolve_country` — see note
03 — so a town name inside a covered country isn't wrongly flagged
unsupported). If anything is unsupported, `coverage_note` returns a block
naming exactly what's missing and instructing:

> "You MUST NOT state ANY figure for them — no dorm prices, no daily budget
> ranges, no visa fees, no journey times, not even approximate or 'typically
> around' ones. Quoting a plausible-sounding price you cannot source is the
> exact failure this rule exists to stop."

That last sentence — explicitly naming the failure mode — was added after a
softer version of the same warning still let the model produce "dorm beds can
range from $5-$15 per night" for Mongolia, hedged as approximate but still
invented. Being polite about the instruction wasn't enough; it had to spell out
that even a hedged, plausible-sounding number counts as the violation.

**Injected into:** the weather/logistics/recommendations specialists (via
`COVERAGE_BLOCK`, added after specialists — not just the weigher — were found
to be the actual source of confabulated figures the weigher then passed
through) and the decision-weigher.

## `route_note`

**What it catches:** inventing onward destinations, journey times, and
attractions for a town/country the route corpus has no data for.

**The eval case:** `discovery-honest-about-unknown-origin` — asked "where next"
from Reykjavik (outside the SE Asia/Nepal/Sri Lanka corpus entirely), the
`discover_next_destinations` tool correctly returned `found: false`, and the
model **ignored that and invented Icelandic destinations anyway** — Terelj
National Park, scenic landscapes, fabricated specifics, with no acknowledgement
it was working outside its knowledge base. This is the clearest single proof in
the whole project that "the tool told the model it had no data" is not
sufficient on its own — the model can and will route around an honest tool
result if nothing else stops it.

**How it works:** `route_note(current_location)` is country-aware in a way that
matters:

- If the town itself is a route-document origin (`"chiang mai"` is a key in
  `ROUTE_GRAPH`), return the known onward hops directly.
- If the town isn't a route origin but its **country** is covered
  (`resolve_country("Thailand")` succeeds), return a message saying route data
  exists at country level but we need to know which *town* for hop-by-hop
  detail — because someone whose stored location is just "Thailand" is not an
  uncovered traveller, they're a traveller we need one more detail from. This
  branch used to end by listing every town held, which read as a menu to pick
  from; it now forbids choosing one instead (see "No location at all is not a
  licence to pick one" below).
- Otherwise, a hard block: "NO ROUTE DATA HELD FOR {origin}... you MUST NOT
  name onward destinations, journey times, prices or attractions."

This three-way split (town-known / country-known-town-unknown / genuinely
unknown) exists because the two-way version (known vs unknown) caused a
regression: a traveller whose profile said `current_location: "Thailand"`
(country-level, common for someone who just finished onboarding) got routed
into the "no data" branch and the discovery agent asked a clarifying question
instead of answering — which lost the traveller their answer for no reason.
The runner now has an explicit fallback for this case (see below).

## Question SCOPE: `coverage.wants_country_scope`

**What it catches:** answering "which **country** should I go to next" with a
list of towns inside the country the traveller is trying to leave.

**The bug report:** #3, 2026-09-14 (`test1234`). Standing in Pai, the traveller
asked three times, in three phrasings — "my visa is running out at the end of
the month, what country should i go to next?", "which country should i go to
next", "i want to change country" — and got Chiang Mai, Mae Hong Son and Chiang
Rai every time. The visa phrasing makes it worse than unhelpful: the answer to
"my permission to be in this country expires" was three suggestions for staying
in it.

**Why it happened, and why it is a design bug rather than a model failure:**
the scope of a "where next" answer was decided entirely by the *granularity of
the stored location*. A town in `ROUTE_GRAPH` → the town-level `discovery_agent`;
a country → the country-level comparison fallback below. The word "country" in
the question reached no decision anywhere in the pipeline: `TurnParse` has no
scope field, `intent: discover` covers both, and the `discovery_agent` holds
only `discover_next_destinations` and `get_traveller_feedback`, so once the turn
arrived there a country-level answer was not available at any price. Reproduced
deterministically with the agents stubbed — the routing alone is enough.

**How it works:** `coverage.wants_country_scope(message)` is a regex over the
message, in code, checked in `runner.py` alongside the existing
two-destinations-means-`compare` override. It matches the question asked at
country granularity ("which/what/another/next country", "change country",
"crossing the border", "visa run") and the constraint that forces that
granularity anyway ("my visa is running out", "overstaying"). When it fires on
a `discover` turn, the turn takes the country-level path regardless of how
precisely the location is recorded — the traveller's town is still passed to
the specialists, so `routes.lookup` and the visa tools resolve legs from where
they actually are.

It applies to `discover` turns and to `local` turns that name no destination —
the reported "i want to change country" was classified `local`, so gating it on
`discover` alone would have missed the exact turn the traveller complained
about. `review` and `memory` are deliberately left alone: "Thailand was the
best country I've been to" is a review, and rewriting it into a comparison
would be its own bug.

Deliberately **not** matched: a bare country name (travellers name countries
constantly in questions that are still about towns), and "countryside".

## No location at all is not a licence to pick one

Same bug report, the other half.

**Where the Chiang Mai answer actually came from** — written down because the
first diagnosis was wrong, and the wrong version is the more intuitive one.
From the reply alone ("here are some great options from Chiang Mai", carrying
the genuine `route-chiang-mai` journey times and prices, for a town the
traveller never mentioned) it looks exactly like an agent inventing an origin
and getting lucky with the retrieval. It was not. The Langfuse trace for that
turn (`3650cac7e23a…`, 2026-09-14 16:53:59) shows the `discovery_agent`
behaving correctly end to end: it was handed `current_location: Chiang Mai` and
answered from it, honestly. The lie was upstream, in the *parse* of that same
turn — the turn parser emitted a visit to Chiang Mai for a message that named
nowhere, and the write path stored it. See "the grounding rule" in
notes/02-memory-and-schema.md. **An agent's honesty guard cannot save a turn
whose memory is already wrong**, and no amount of prompt-level hardening here
would have caught this one.

The reachable-with-no-location state was real all the same, and nothing in code
stopped the town-level agent taking a turn it had no origin for. Both changes
below therefore stand on their own — as defence in depth for a state the
write-path fix makes much rarer, not as the fix for this report:

- **Control flow, in `runner.py`:** a `discover` turn with no recorded location
  goes to the `concierge`, which holds no tools at all, so the worst it can do
  is ask where they are. The town-level agent never gets the turn.
- **`route_note`, for the two location-unknown branches:** the "unknown" branch
  is now a hard block naming the specific move that was made ("not from their
  route history, not from their wishlist, not from anywhere in this prompt"),
  and the country-level branch **no longer lists the towns held**. That list was
  meant as "here is what we could answer with if you tell us the town", but a
  list of towns inside a prompt that also says "we don't know which town" reads
  as a menu. A guard that hands over the candidates it is trying to rule out is
  not a guard, whether or not it was the cause on this particular turn.

Covered by `tests/test_where_next_scope.py` (38 tests, 35 of which fail against
the pre-fix code) and eval cases `scope-country-question-answered-with-countries`
and `scope-visa-expiry-forces-a-country-answer`.

## The country-level-origin routing fallback

Related to `route_note` above but implemented in `runner.py` rather than the
prompt layer, because it's a control-flow decision, not a fact-injection one.
When `intent == "discover"` and the stored `current_location` is a country
(not in `ROUTE_GRAPH`), the runner doesn't hand the turn to the town-level
discovery agent at all — it looks up `coverage.nearby_country_options(country)`
(a small hardcoded adjacency list of "which covered countries border/connect to
which") and re-routes the turn through the ordinary `compare` pipeline against
those neighbour countries instead. This means "where next" from a
country-granularity profile still produces a real, useful comparison rather
than a dead-end clarifying question.

Since bug report #3 this same branch is entered whenever
`wants_country_scope` fires, not only when the stored location happens to be a
country. Its one remaining dead end is now handled explicitly: if the pool of
onward countries is empty (nothing on the wishlist, and an origin country with
no overland neighbour in `COUNTRY_NEIGHBOURS` — Japan, Australia, Mongolia),
the turn goes to the `concierge` with a code-written `route_note` saying
exactly that, rather than falling through to the town-level agent and answering
a country question with towns again.

## City-awareness as a recurring theme

Three separate guards — `coverage.resolve_to_covered`, `climate.assess`,
`routes.lookup` — all needed the same fix (falling back through
`route_data.resolve_country` when an exact string match fails) for the same
underlying reason: the turn parser started returning destinations at town
granularity once the extension shipped, and every piece of country-keyed logic
written *before* that point assumed country-granularity input. This is
recorded as its own theme (rather than just three bullet points under
different headings) because it's a useful lesson for extending this codebase
further: **any new table or guard keyed by "destination" should go through
`resolve_country` from day one**, not have the bug rediscovered a fourth time.

## The intent-override guard

Not a prompt-injected text block like the others, but the same underlying
principle — don't trust the model's own classification when a cheap
deterministic check can verify it. Covered in detail in note 01
(agent-architecture.md) since it's a routing decision rather than a
fact-injection guard, but listed here for completeness: any turn naming ≥2
destinations is forced into the `compare` intent regardless of what the parser
classified it as, because routing a genuine comparison question to an agent
without visa/route tools (as happened with `visa-nationality-aware`) produces
wrong answers with no code-level way to catch it after the fact — the fix has
to be upstream, at dispatch time.

## The specialists are not skippable

The fourth guard of the same family as the intent override and the
country-scope override: a decision the model was making, taken off it in code.
`turn_parser` says which specialists a turn needs; on the compare path those
`needs_*` flags are no longer read, and all three specialists always run.

It returned `needs_weather: false` for "I want to do a big trek in July. Nepal
or Sri Lanka?" — a question *about the season*. No `weather_agent` span appears
in that trace at all, the Decision-Weigher got an empty seasonal report, and
Nepal, in monsoon, was ranked first. Making only Weather mandatory then exposed
the same thing one layer down: `needs_recommendations: false` for "How much a
day should I budget for Laos versus Cambodia?", so the agent holding the `tips`
corpus — where the budget numbers are — never ran either.

Both failures are silent. Nothing errors, no empty report is flagged; the
weigher simply ranks on whatever it was given. That is what makes this worth a
guard rather than a better prompt: the symptom is a confident answer missing
one of the three inputs it claims to have weighed. Eval cases
`season-nepal-monsoon` and `rag-budget-numbers`; full history in note 08,
decisions 51 and 52.

## What a guard does *not* do

Worth being explicit: none of these guards can stop a model from getting
something wrong within its permitted scope — a guard only fires when the model
is about to step *outside* what it has verified data for, or ignore a
structural fact (a coverage gap, a route boundary) that's supposed to be
non-negotiable. They don't replace the underlying eval suite; they're the
concrete artifact that eval failures produced. Every guard in this file exists
because a specific eval case failed first, was diagnosed, and the guard was the
fix — none were added speculatively.
