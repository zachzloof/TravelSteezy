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

**Confirmed.** The eventual clean, lock-protected re-run (`9-extension-final.md`,
after both this fix and the concurrency fix below) scored **27/27, 81/81
individual attempts passing** — the previously-flaky case included, no longer
flaky at all. That is the strongest evidence available that the fix addressed
the actual cause rather than papering over a symptom: the case didn't just
pass more often, it stopped being nondeterministic.

## A second, more serious bug: two eval runs corrupting each other

While chasing the `resolve_country` fix above, a genuinely different and more
serious problem surfaced. Fixing the bug meant re-running the repeat-3 suite to
confirm it. A session interruption made it look like the re-run had died
partway through, so a second re-run was started. It hadn't died — both
processes kept running concurrently against the same SQLite file, sharing the
same two fixed eval accounts (`__eval_account_a`, `__eval_account_b`) that
every case's setup calls `forget_account_memory()` and reseeds on.

The result was silent cross-contamination. The clearest signature, found in
one of the two corrupted result files: a case that seeds the traveller in
Reykjavik, Iceland, and asks "where next" — the correct behaviour is an honest
"no route data for Iceland" — got a confident answer entirely about Chiang Mai
and Pai. That's only possible if this turn's account row had been overwritten,
mid-run, by a *different* case (one of the several Chiang Mai/Pai discovery
cases) executing in the other process at the same moment. A second signature
in the same files: a departure-tracking case whose reply contained no
departure logic at all, reading as if the model had answered a completely
different, more generic question — again consistent with the account's stored
profile changing under it between the setup step and the message step.

**This is a more fundamental problem than eval flakiness** — it doesn't
degrade gracefully, it produces confidently wrong answers to the wrong
question with no error and no obvious tell in the output itself. Both
corrupted runs' results were kept, not deleted (`7-extension-repeat3-run2-COLLISION-CONTAMINATED.md`
and `8-extension-final-run3-COLLISION-CONTAMINATED.json`/`.md`), clearly labelled
as invalid, because they're the actual evidence for this finding and because
eval results are treated as append-only artifacts in this project — see the
decisions log for the moment that policy got tested for real when files were
briefly deleted, then restored from git history and reconstructed where they
weren't recoverable.

**The fix**: `evals/run_evals.py` now has an `EvalLock` — a simple file lock
(`evals/.eval_lock`, containing the holder's PID and start time) acquired
before any case runs and released when the process exits. A second run started
while the lock is held gets an immediate, explicit refusal naming the PID and
start time of the process already running, rather than silently starting and
corrupting both runs' data. Covered by `tests/test_eval_lock.py` (acquire,
release, double-release safety, collision refusal, and that the error message
actually names the holding process — six tests, no API keys, sub-second).

This is not a perfect distributed lock (a hard crash can leave a stale lock
file behind, requiring a manual check-and-delete, which the refusal message
explains how to do), but it converts "corrupts silently" into "refuses loudly,"
which is the property that actually matters here — the corruption was
dangerous specifically *because* nothing about the failed runs' output signalled
that anything was wrong; both produced complete, well-formed markdown reports
with a plausible-looking score.

## What "the eval score" means for the demo

Given the above, the honest way to present a number in a demo is not a bare
percentage from one run — it's the repeat-mode summary: "N/27 cases pass every
one of 3 runs; X% of all individual attempts pass; here are the cases that are
flaky and why." That's a materially stronger claim than a single-run
percentage.

The number that actually landed, after both fixes documented above:
**27/27 cases (100%), passing every one of 3 runs — 81/81 individual attempts
passing, zero flaky cases.** Stored in `evals/results/9-extension-final.md` /
`.json`. See note 08's decision log for the full timeline of getting a
genuinely clean run recorded, including the two contaminated attempts kept on
disk alongside it as evidence rather than discarded.

## Attributing a regression before believing it: the `rag-backpacker-not-tourist` case

During the onboarding rework, the full 35-case suite came back **34/35**, with
`rag-backpacker-not-tourist` — a judge-scored case — failing. It had passed
**3/3 in both** prior repeat-3 runs (`5-extension-repeat3`, `9-extension-final`), so
"it used to pass and now it doesn't" looked like a clean regression signal.

It was not one, and the way that was established is the point of this note.

**Step 1 — get a rate, not a verdict.** One failure is not a measurement. Re-run
on the current code: 2/4, then 5/6. Combined with the full run: **7/11 (64%)**.
Lower than 6/6, but 6 historical samples against 11 is thin evidence for a real
change (Fisher's exact on 6/6 vs 7/11 gives p ≈ 0.13 — suggestive, not
conclusive).

**Step 2 — isolate the suspect.** Exactly one change in the rework touches what
this case's agents actually read: `format_profile_for_prompt` now expands a band
into a labelled form (`shoestring (dorms, street food, night buses)`) and renders
a `Travelling:` line. Everything else the rework changed — the questions, the
extractor, the passports table, the ratings block — is either on a different code
path or produces identical output for this case's seeded profile, which has no
route, no wishlist and no ratings.

So: temporarily revert *only* that rendering change and run the same 6 reps.

| Condition | Attempts passing |
|---|---|
| With the band labels (current code) | 7/11 (64%) |
| **Without** them (temporarily reverted) | **3/6 (50%)** |

The case is no better without the change. If anything the labels help slightly.
**The flakiness is pre-existing and not attributable to this work**, and the
historical 6/6 was a run of luck on a case that genuinely sits near its judge
threshold — which is precisely the phenomenon the top of this note was written
about, showing up again in the one place it was easiest to misread.

The change was restored.

### Why this is written down

Two failure modes were available here and both are bad:

- **Shrug it off** — "judge cases are flaky, notes/06 says so" — which is true
  in general and would have been an unfalsifiable excuse in this instance.
- **Tune the product until the judge is happy**, which this note already warns
  against at length, and which would have meant changing a prompt that the
  measurement shows was never the problem.

The isolation run costs about five minutes and replaces both with an answer. The
general rule: **before accepting or dismissing a regression on a nondeterministic
case, get a rate, then A/B the one change that could plausibly explain it.** A
before/after comparison where only one side was measured repeatedly is not a
comparison.
