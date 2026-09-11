# Eval methodology

## Why the checks are assertion-first, not judge-first

Of the 27 extension eval cases (plus 19 base-app cases, 46 total), only a
handful use an LLM judge. The rest are deterministic assertions against real
system state:

- `tool_called` / `tool_called_any` — did a specific tool actually get invoked
  (read from `ToolRecorder`, not inferred from the reply text)
- `retrieval_fired` — did a RAG search actually hit a given namespace
- `history_contains` / `wishlist_contains` / `review_saved` / etc. — read
  straight from the SQLite tables after the turn, not from what the model
  *said* it did
- `not_ranked_first` / `flag_present` — inspect the structured card output,
  not prose
- `grounded_in_retrieval` — checks for genuine lexical overlap between
  retrieved passage text and the reply, as a cheap proxy for "did this actually
  use the retrieved content" without needing a judge call

This matters specifically because one of the base-app failure modes being
tested for is "generic tourist advice instead of backpacker-specific advice,
asserted on retrieval actually firing, not on plausible-sounding text." A judge
call asking "does this sound like backpacker advice?" can be fooled by fluent
prose that never touched the RAG store. Checking `retrieved_sources` against
the actual `ToolRecorder` state cannot be fooled by fluency — either the search
happened or it didn't.

The judge is reserved for genuinely qualitative questions with no
structural proxy: "is this backpacker-specific rather than brochure-generic,"
"did the reply honestly admit missing data rather than confidently inventing
it," "did the reply use stored profile context rather than asking to repeat
it." Even these are backed by a `pass_score` threshold (usually 4/5) rather
than a bare pass/fail, so partial credit is visible in the raw results file.

## The judge fabrication incident, and the evidence-quote fix

During the extension's fix cycle, the judge scored a reply **1/5** for
`memory-no-repeat-budget` with the stated reason: "the assistant asks for
budget information, which is unnecessary given the stored context." The full
reply, read directly from the run's results file:

> "I recommend heading to Thailand next, primarily because it has a much
> simpler visa process... As for your budget, shoestring travelers can expect
> to spend around 700-1,000 THB (about 20-30 USD) per day here. Currently,
> you're in Laos and planning to travel between November 5 and December 20,
> 2026..."

The reply asks for nothing. It restates the stored budget band, dates, and
current location correctly. The judge's stated reason for the 1/5 score was
simply false — not a defensible-but-harsh reading, a description of something
that did not happen in the text it was grading.

This is a serious finding on its own: an LLM judge can hallucinate a specific,
plausible-sounding failure and confidently deduct marks for it, and a
naive "trust the judge" eval harness would have silently recorded a false
negative and possibly triggered an unnecessary "fix" to already-correct
behaviour.

**Fix, in two parts:**

1. The judge prompt now requires, for any score ≤3, a verbatim `quote` field —
   the exact words from the reply that demonstrate the claimed fault. "Leave
   'quote' empty only when you are scoring 4 or 5."
2. `run_evals.py` enforces this in code, not just by asking nicely: if
   `score <= 3` and a `quote` is provided, the runner checks whether a
   whitespace-normalised version of that quote actually appears in the reply
   text. If it doesn't, **the deduction is rejected and the score is
   overridden to 4**, with the rejected reason logged:
   `"judge quote not found in reply, deduction rejected: {original_reason}"`.

This is the same design principle as the code-computed prompt guards (note
05): don't trust a natural-language claim when a cheap string-containment
check can verify it. The judge is still useful for qualitative signal, but its
negative verdicts are now falsifiable rather than taken on faith.

## Why single-run scores are close to meaningless here

Four consecutive runs of **identical code** — no changes between them —
produced these scores on the 27-case extension suite:

| Run | Score |
|---|---|
| 1 | 24/27 (89%) |
| 2 | 26/27 (96%) |
| 3 | 25/27 (93%) |
| 4 | 24/27 (89%) |

Each run failed a *different* subset of cases. This isn't a sign the suite is
badly designed — it's the honest consequence of the system under test being a
chain of temperature>0 LLM calls (turn parser → specialists → weigher, or
extractor → conversationalist for onboarding), where a small wording
difference in one call can cascade into a different tool-call sequence, a
different retrieved passage, or a different phrasing that a regex check
happens to miss.

A single run's score is therefore not "the score" — it's one sample from a
distribution. Reporting the best of several runs would be dishonest (survivor
bias); reporting a random single run risks either flattering the system
(showing 96% when the true rate is closer to 91%) or unfairly failing it
(showing 89% on a genuinely solid case that just had one unlucky
generation).

## The `--repeat N` design

`run_evals.py --repeat 3` runs every case 3 times and reports:

- **Per-case pass rate** (`passes/runs`, e.g. `2/3`), with a case counting as
  "passed" overall only if it passed **every** run — this is the strict
  reading, appropriate for a demo claim ("this works") rather than a
  loose "usually works" claim.
- **A `flaky` flag** on any case that passed some runs and failed others,
  surfaced separately in both the console output and the markdown report,
  because a flaky case is a qualitatively different finding from a
  consistently-failing one — it usually points at either genuine model
  variance in wording, or (as it turned out once) a real bug that only
  manifests for certain inputs.
- **`attempt_pass_rate`** — the pass rate across all individual attempts
  (not per-case), which is a better estimate of "how reliable is this system
  on any given real user turn" than the strict per-case number.

**It immediately justified its own existence.** `season-malaysia-east-coast-closed`
showed as `FLAKY (1/3)` in the first repeat-3 run. A single-run harness would
have reported this case as either "pass" (if it happened to be the 1 lucky run)
or "fail" (if not), with no indication that the *same code* would produce a
different verdict next time. Investigating the flakiness — rather than
shrugging it off as "LLM variance" — surfaced the `resolve_country` bug
documented in note 03: it wasn't randomness in the model's wording, it was a
real code bug (a country-keyed table returning "unknown" for a town-level
input) that only triggered when the model happened to phrase its
`candidate_destinations` output as a town name (`"Perhentian Islands, Malaysia"`)
rather than the bare country name (`"Malaysia"`) — both of which are
individually reasonable extractions from the same user message, so which one
came out was itself somewhat arbitrary from run to run. Fixing the resolver
should make the case deterministic (pass on every run) rather than merely
"less flaky," which is exactly the kind of finding repeat-mode is meant to
surface — a code fix that converts a flaky case into a reliably-passing one,
versus a case that just needs a softer regex.

## What "the eval score" means for the demo

Given the above, the honest way to present a number in a demo is not a bare
percentage from one run — it's the repeat-mode summary: "N/27 cases pass every
one of 3 runs; X% of all individual attempts pass; here are the cases that are
flaky and why." That's a materially stronger claim than a single-run
percentage, and it's the number stored in
`evals/results/extension-final.md` (see note 08's decision log for the
timeline of getting a clean run recorded).
