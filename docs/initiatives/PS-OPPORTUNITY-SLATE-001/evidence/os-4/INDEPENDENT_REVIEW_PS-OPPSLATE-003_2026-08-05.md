# Independent review — PS-OPPSLATE-003 additive re-cut

- Reviewer: Claude Opus 5, fresh delegated session at maximum effort, per
  Pete's 2026-08-05 model routing.
- Candidate SHA: `ebde2bb382cc1148923c424057a228ad48f5fbd3`
  (base `cb8591de50e6a682674c2610c5dd4c98eaeb5c0f`).
- Verdict: **APPROVE** — zero blocking findings.

## Verified

- **Immutability**: every blob under `SQL FIles/` SHA-256-hashed at both
  commits; the change adds only the three 003 files and one registry entry;
  all PS-OPPSLATE-001/002 files byte-identical to production's applied bytes.
- **Fidelity**: the OS-4 checkpoint delta (`3ac0e9d5..de8735ce`) was
  reconstructed independently; the 336-line table block and 691-line procedure
  block are byte-identical to the checkpoint; 17→20 procedures with zero
  existing bodies changed.
- **"No existing procedure needs revision" proven mechanically**: the four new
  tables carry no FK into any working table and no cascade clause; existing
  purge/delete paths touch only working tables; the verifier proves a purge of
  every working row leaves the saved slate complete (error 53869).
- **Additive correctness**: UPDLOCK/HOLDLOCK preflight requiring 001+002, a
  29-object baseline, 0-or-7 partial-shape refusal; single XACT_ABORT
  transaction; insert-only ledger handling; 002-consistent hash labeling.
- **Owner isolation**: @UserKey-only procedures, server-side @ProfileId,
  composite owner-preserving FKs; forged-key and cross-owner write/delete
  negatives exercised. Save accepts no content payload — snapshots build only
  from the owner's own rows.
- **No aggregate**: all 195 columns of all 16 tables clean; the widened
  pattern-based check catches ten control probes including match_score,
  fit_index, and hire_probability; a planted match_score column turns the
  suite red.
- **Privacy**: visibility hard-locked to 'private' by a single-value CHECK; no
  audience, share, send, or notification surface.
- **Tests**: 146 passed / 1 skipped / 450 subtests; registry check exits 0
  with 25 registered and 003 as draft. The 28 new tests were mutation-tested:
  9 of 10 planted defects caught by pytest, the tenth (applied-file tamper) by
  `govern_sql_migrations check` exiting 1.

## Non-blocking findings (follow-up backlog)

1. `test_original_001_and_002_files_are_untouched_by_this_chain` pins no
   bytes; the authoritative digest guard lives in `govern_sql_migrations
   check`. Add a SHA assertion or fix the docstring.
2. The verifier's cross-owner READ negative is under-asserted (owner B is
   empty, result sets uncaptured, cross-owner saved_result_key never passed);
   the procedure is correct by inspection.
3. Forbidden-pattern asymmetry: procedure-body check uses narrower patterns
   than the column check.
4. The Python FORBIDDEN_VERDICT_IDENTIFIERS mirror is still a fixed-name
   list; the SQL layer is pattern-based and tested to stay so.
5. `fitness_index` would evade both lists (narrow residual).
6. The checkpoint's COL_LENGTH probes are intentionally absent — correct for
   a re-cut over an immutable ledgered baseline.
7. Deleting a working session no longer removes the saved slate (by design);
   truthful member disclosure is an app-lane obligation for the OS-4 UI.

## Limitation

Static review plus mutation analysis only — no SQL Server available here. The
gate-database apply/verify/rollback leg is unexecuted; 003 is correctly
`gate: null` and unwired from any apply path, so merging changes no deployed
behavior. The disposable-database gate run must precede any apply.
