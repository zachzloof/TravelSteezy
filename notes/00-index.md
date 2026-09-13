# Design notes — index

These notes exist so a decision can be looked up later without re-deriving it,
and so a marker or a future contributor can see *why* something is shaped the
way it is, not just what it does. Each file covers one area and is written to
stand alone.

They complement, not duplicate, two other documents:

- [README.md](../README.md) — the pitch, architecture, stack, and demo script.
- [docs/EXTENSION.md](../docs/EXTENSION.md) — the feature-level writeup of the
  onboarding/tracking/reviews/Places extension, for the grading checklist.

The notes here go one level deeper: the specific bug, the specific fix, the
specific number, and the reasoning that connects them. Every claim in here was
verified against the running code or a real eval/test result at the time it was
written — none of it is aspirational.

| File | Covers |
|---|---|
| [01-agent-architecture.md](01-agent-architecture.md) | Why ADK, why LiteLlm not Gemini, why `asyncio.gather` not `ParallelAgent`, the two-agent onboarding split |
| [02-memory-and-schema.md](02-memory-and-schema.md) | The five memory questions, the `travel_history` migration, why writes are explicit Python calls |
| [03-rag-and-retrieval.md](03-rag-and-retrieval.md) | Namespace design, the unscoped-fallback removal, the `resolve_country` bug and fix, the experience feedback loop |
| [04-places-and-ranking.md](04-places-and-ranking.md) | The Bayesian ranking bug, the clustering bug, hostel search, caching, degradation |
| [05-guards-and-prompting.md](05-guards-and-prompting.md) | Every code-computed guard, why each exists, the exact eval case that caught it |
| [06-eval-methodology.md](06-eval-methodology.md) | Why single-run scores are meaningless here, the repeat-mode design, the judge evidence rule |
| [07-known-limitations.md](07-known-limitations.md) | What is simplified, what is untested, what would break first in production |
| [08-decisions-log.md](08-decisions-log.md) | Chronological log of every non-obvious choice, in the order they were made |
| [09-observability-and-tracing.md](09-observability-and-tracing.md) | Tracing rebuilt on OTEL auto-instrumentation (not hand-rolled spans) - why, how it was verified against a live trace - plus the full 2026-09 dependency modernization (google-adk, openai, pinecone, langfuse, fastapi, bcrypt/passlib removal) and what stayed pinned and why |

## How to use these if you're picking this project back up

1. Read `08-decisions-log.md` first — it's the fastest way to reconstruct how the
   codebase got to its current shape.
2. If you're about to touch the agent graph, read `01` and `05` — most of the
   subtlety in this codebase is in how prompts and code-computed guards interact.
3. If something about ranking or clustering looks wrong, read `04` before
   "fixing" it — both algorithms had a wrong-seeming first version that was
   actually the bug, and the fix is documented with the numbers that proved it.
4. If you're about to trust an eval score, read `06` first.
5. If you're adding a new agent, endpoint, or anything that calls an LLM, read
   `09` first — it's a short checklist, and skipping it is exactly how the
   gaps documented there happened in the first place.
