# Code-computed guards and prompting

## The pattern

Every guard in this codebase follows the same shape, and it's worth stating the
shape explicitly because it's the single most repeated pattern in the whole
agent design:

1. A plain Python function computes a fact the model must not be allowed to get
   wrong (what's covered, what isn't, what the deadline is, what's already
   known).
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

## `deadline_note`

**What it catches:** silently planning past a hard visa/permit expiry stored
in the trip profile.

**The eval case:** `visa-deadline-surfaced` — profile has `visa_deadline_date`
set two days out; the weigher's reply talked about destinations and budgets
without ever mentioning the deadline explicitly by date, even though it should
have been the single most important constraint on the answer.

**How it works:** if `trip_profile.visa_deadline_date` is set,
`deadline_note(profile)` returns a block stating the exact date and instructing
the model to state it explicitly in its reply and check every recommendation
against it. Injected into the weigher and the discovery agent (the latter
added after `discovery-honest-about-unknown-origin`-adjacent testing showed
"where next" answers could also quietly ignore a deadline).

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
  detail, and list which towns we do have — because someone whose stored
  location is just "Thailand" is not an uncovered traveller, they're a
  traveller we need one more detail from.
- Otherwise, a hard block: "NO ROUTE DATA HELD FOR {origin}... you MUST NOT
  name onward destinations, journey times, prices or attractions."

This three-way split (town-known / country-known-town-unknown / genuinely
unknown) exists because the two-way version (known vs unknown) caused a
regression: a traveller whose profile said `current_location: "Thailand"`
(country-level, common for someone who just finished onboarding) got routed
into the "no data" branch and the discovery agent asked a clarifying question
instead of answering — which lost the traveller their answer *and* suppressed
an otherwise-correct hard-deadline warning that should have fired in the same
turn. The runner now has an explicit fallback for this case (see below).

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

## What a guard does *not* do

Worth being explicit: none of these guards can stop a model from getting
something wrong within its permitted scope — a guard only fires when the model
is about to step *outside* what it has verified data for, or ignore a
structural fact (a deadline, a route boundary) that's supposed to be
non-negotiable. They don't replace the underlying eval suite; they're the
concrete artifact that eval failures produced. Every guard in this file exists
because a specific eval case failed first, was diagnosed, and the guard was the
fix — none were added speculatively.
