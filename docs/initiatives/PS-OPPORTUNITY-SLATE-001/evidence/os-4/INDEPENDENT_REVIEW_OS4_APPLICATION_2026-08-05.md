# Independent review — OS-4 application release candidate

- Reviewer: Claude Opus 5, fresh delegated session at maximum effort.
- First candidate `a87e713`: **REFUSED** — the three new mutating routes
  (`save_slate`, `delete_slate`, `reanalyze`) carried no rate limit with the
  limiter's default empty, proven behaviorally (12 rapid POSTs, zero 429s,
  versus six on the OS-3 control); the guard test named
  `test_every_state_changing_route_is_rate_limited` was a hardcoded five-name
  OS-1 list unable to detect any new route. Three further non-blocking truth
  and coverage findings.
- Corrected candidate `5b164c5b713988610b3eec811cd5e7cead257a15`: **APPROVE**.

## Fixes verified behaviorally

1. Rate limits: `reanalyze` on the 6/min AI budget (first 429 at request 7,
   identical to `run_analysis`); `save_slate`/`delete_slate` on 30/min (first
   429 at request 31, matching the `save_response` control). All 16 POST
   routes on the blueprint limiter-wrapped.
2. Replacement guard enumerates `app.url_map` and checks flask_limiter's own
   wrapper marker — verified set at exactly one place in the library, in the
   branch that registers a real limit, not set by `exempt`; mutation-proven
   against a removed entry AND a simulated brand-new unlimited POST route.
3. Footer truth correct in all four saved states; the reanalyzed state now
   says "Nothing new was saved. Your saved slate is unchanged."
4. Orphaned-saved-slate link renders only for the identified owner; absent on
   read failure; with the service deliberately poisoned, an anonymous request
   never calls the saved lookup at all.
5. Exact-set ALLOWED_PROCEDURES test rejects an injected rogue name (129
   names, grouped, cross-checked).

Regression: five files only, `services/` untouched, `SQL FIles` tree hash
unchanged (`e7fb5402…`); 385/809 targeted, 2,525 full with only the two
accepted PowerShell failures; the new entry-path call to the unapplied
procedure still fails safe to a 200 bare intake.

## Standing constraints

- **Deploy sequencing: merge only after PS-OPPSLATE-003 is applied.** Until
  then a signed-in member would see a live Save control that returns a
  truthful 503.
- Non-blocking: `saved_details` (GET) remains unrated, consistent with the
  room's existing GET posture; recorded as a deliberate choice.
