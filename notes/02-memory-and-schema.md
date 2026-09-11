# Memory and schema

## The five questions, and where each is answered in code

The syllabus grades memory as five separate, named things. Each maps to one
function, on purpose, so the answer to "where is X implemented" is never "it's
spread across the prompt somewhere":

| Question | Function | File |
|---|---|---|
| What you keep | `get_memory_snapshot`, `get_travel_snapshot` | `store.py`, `travel.py` |
| When you write | `update_profile`, `log_departure`, `apply_tracking`, `_apply_onboarding_capture` | `store.py`, `tracking.py`, `runner.py` |
| Where it lives | SQLite file on the Railway volume | `db.py` / `config.py` (`DATA_DIR`) |
| How you retrieve | `get_memory_snapshot` at the top of every turn | `runner.py::run_turn` |
| When you forget | `archive_country`, `prune_turns`, `forget_account_memory` | `store.py` |

The extension added a second write surface (`travel.py` / `tracking.py`) rather
than growing `store.py` indefinitely. Reasoning: `store.py` answers the five
questions for the *active trip profile* — nationality, budget, current
location, one row per account. `travel.py` holds the *structured route data* —
an ordered list, a wishlist, reviews — which has different shape (many rows,
not one) and different write triggers (a tool call mid-conversation, not a
profile edit). Keeping them in separate modules with separate `_record_write`
calls into the same shared `memory_writes` audit table means the audit log is
unified even though the write logic isn't.

## Why every write is a Python function call, never a prompt instruction

This is stated as a design principle in the syllabus brief and it's worth
recording *why* it matters beyond "the checklist says so": an agent's prompt is
not a reliable place to put a side effect. If "update the user's location" were
just an instruction in a system prompt, there would be no way to:

- assert in a test that it happened (you'd have to re-parse the model's prose)
- distinguish an agent-inferred write from a user's own edit in the UI
- guarantee it happens exactly once per real change (see the no-op audit fix
  below)
- have a stable contract that survives a prompt rewrite

So the pattern throughout is: the model's job ends at "here is what I heard,
as JSON" (via `output_key` and `parse_json_block`), and a plain Python function
in the orchestrator decides what that JSON means for the database. The model
never touches SQLite directly, even indirectly through a "database tool" — the
closest it gets is the tools in `tools.py` / `place_tools.py`, which are all
*reads* (RAG search, Places lookups) or *computed lookups* (`check_route`,
`check_seasonal_conditions`), never writes.

## `travel_history` supersedes `visited_history` — migration, not replacement

The original schema had one country-level append-only table,
`visited_history(country, arrival_date, departure_date, notes)`. The extension
needed: town/city granularity (a route through Bangkok → Koh Tao → Chiang Mai
is not "Thailand" three times), explicit ordering (a route is a sequence, not a
set), a place for the post-visit review, and a `source` column to distinguish
onboarding-stated history from live-tracked visits from a manual edit.

Rather than replace the table (which would silently lose data for anyone who'd
already used the base app), `migrate_visited_history()` runs on every boot and
copies any `visited_history` row that has no matching `travel_history` row for
that `(user_id, location)` pair, tagging it `source='migrated'`. It's
idempotent — the `NOT EXISTS` guard means running it twice does nothing the
second time — and this is asserted by
`test_legacy_visited_history_is_migrated`, which writes to the old table,
migrates, checks the new table has it, migrates *again*, checks there's still
only one row.

`visited_history` itself is **not deprecated or removed** — country-level
departures still write to it (see the departure-granularity note below), so the
original "what countries has this account been to" view keeps working
unmodified for anyone who only ever interacts at country level.

## Late-column migration

Two columns were added to `trip_profile` after the base schema was designed:
`social_style` and `onboarded`. SQLite has no `ALTER TABLE ... ADD COLUMN IF NOT
EXISTS`, so `add_missing_columns()` reads `PRAGMA table_info(trip_profile)`,
checks which of a declared list `LATE_COLUMNS` are missing, and adds only those.
This runs before `migrate_visited_history()` in `init_db()`, so the migration
that reads/writes those columns never hits a "no such column" error on an
existing database file.

## The no-op audit-write bug

Early behaviour: mentioning a place you were already known to be in (e.g. the
model re-stating "you're in Chiang Mai" mid-conversation) triggered
`add_travel_history`, which — even when nothing about the row actually
changed — still called `_record_write`, and that write appeared in the
`memory_writes` audit log and in the frontend's "just remembered" panel.

This matters because that panel is a **demo-facing feature**: the whole point
is showing a marker "here's proof the app just wrote something new to memory."
If it lights up on every turn regardless of whether anything changed, it stops
being evidence of anything.

Fixed at the SQL level: the `UPDATE` for an existing `travel_history` row now
has a `WHERE` clause that only matches if at least one field is transitioning
from `NULL` to non-`NULL` (`country IS NULL` etc.), and `rowcount` from that
conditional update determines whether `_record_write` fires. `add_travel_history`
now also returns a `changed: bool` key distinct from `created: bool`, and
`tracking.py`'s visit-handling logic only appends to the `writes` list returned
to the UI if `created or changed or promoted` is true. Tested directly by
`test_repeat_mention_is_not_recorded_as_a_write`.

## Departure granularity bug: leaving Pai ≠ leaving Thailand

`tracking.apply_tracking`'s departure handler originally passed whatever
location string the parser produced straight to `store.log_departure(country=
location, ...)` — which writes to the country-level `visited_history` table
regardless of whether `location` was actually a country. A traveller saying
"leaving Pai today" therefore wrote `"Pai"` into `visited_history` as though Pai
were a country, and (worse) `archive_country`'s matching logic would then never
correctly clear `current_location` for a real country departure later, because
the country-level log now had junk in it.

Fixed by classifying the departure before deciding which table it belongs in:

```python
is_country = (
    departure.get("location_type", "").lower() == "country"
    or location.strip().lower() in SUPPORTED_COUNTRIES
)
if is_country:
    store.log_departure(user_id, country=location, ...)   # country-level log
else:
    store.archive_country(user_id, location, ...)          # clears current_location only
```

A town departure still needs *something* to happen — the place should stop
being "where you are now" — and `archive_country` already had exactly that
behaviour (it was written for the country case, but its actual logic is just
"if `current_location` matches this string, clear it," which generalises fine
to a town). Reusing it rather than writing new clearing logic kept this a
one-function-call fix. Two regression tests
(`test_leaving_a_town_does_not_pollute_country_history`,
`test_leaving_a_country_still_logs_at_country_level`) pin both branches.

## `update_profile` deliberately can't clear a field

`store.update_profile` drops any value that's `None` or empty after
`.strip()` — this is intentional (a PATCH from the UI should only touch fields
the user actually typed into, not blank out everything else), but it means you
*cannot* use `update_profile(user_id, {"current_location": ""})` to clear
`current_location`. This tripped up an early draft of the town-departure fix,
which tried exactly that and silently no-op'd. The eventual fix (reusing
`archive_country`, above) sidesteps the problem entirely, but it's worth noting
here because the failure mode was silent — no error, just nothing happening —
which is the worst kind of bug to hit blind.

## Working-memory pruning is separate from profile persistence

`conversation_turns` (raw chat scrollback) is capped at
`settings.working_memory_turns` (default 20) and pruned on every write via
`prune_turns`. The `trip_profile` row and `travel_history` table are **not**
subject to this — they persist for the life of the account, full stop, no
inactivity expiry. This is a deliberate policy choice recorded in the README's
"when you forget" section, not an oversight: the profile is durable state the
user owns, not context-window management.
