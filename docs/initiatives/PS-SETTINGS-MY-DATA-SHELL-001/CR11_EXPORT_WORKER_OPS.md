# CR11 — Export worker retention maintenance (expiry becomes deletion)

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001`
**Delivery path:** Protected (it deletes member-facing artifacts) —
independent review required.
**Depends on:** C1's five lease-fenced worker procedures
(`PS-SETTINGS-EXPORT-001`), C2's private Blob adapter
(`services/account_export_storage_service.py`), and the C2/CR5 worker
entrypoint (`scripts/run_account_export_worker.py`). No schema change of
any kind — this package has no SQL surface.

## The gap this closes

Recorded in `C3_ACCOUNT_EXPORT_EXPERIENCE.md` ("Recorded but not fixed
here" → "Expiry is not deletion") and in the C3/C4 evidence: the
owner-approved seven-day ready window was enforced **in the ledger only**.
`usp_ExpireAccountExportJobs` existed but nothing called it;
`AccountExportStorageService.cleanup_final` existed but nothing ever
called it. An expired job would correctly refuse to download while the
member's complete account archive — the single most concentrated piece of
private data this product produces — sat in the private container
forever.

## What this package adds

One new mode on the existing worker entrypoint, nothing else:

```
python scripts/run_account_export_worker.py --expect-database <name> --maintenance
```

`run_maintenance(connection, storage)` runs two phases in a fixed order:

1. **Expire.** One bare `EXEC dbo.usp_ExpireAccountExportJobs;` — the
   procedure's own default `@BatchSize` (500) governs its internal
   bounded-batch loop, and its one `expired_count` result is read back
   and logged. Ready jobs past `ready_expires_at_utc` become `expired`;
   download refusal was already guaranteed by
   `usp_GetAccountExportDownloadMetadataForOwner`'s own ready-only
   predicate, so this transition only ever removes availability that had
   already lapsed.
2. **Physical cleanup, delete-then-mark.** One direct, parameterized
   ledger-metadata read (the same sanctioned interim shape the worker's
   existing `fetch_requested_at_utc` uses — job columns only, never
   member content) selects exactly the jobs with
   `cleanup_state = 'pending'` and `state IN ('expired', 'failed')`.
   For each: delete the physical objects through the storage adapter's
   idempotent calls — `cleanup_final(job_key)` for EVERY swept job, plus
   per-attempt staging leftovers up to the job's own `attempt_count` —
   and only after every delete succeeded, mark the job through
   `EXEC dbo.usp_CleanupAccountExportJob @JobKey = ?`. The final delete
   is unconditional because `CK_account_export_jobs_ready_artifact`
   constrains the failed job's LEDGER columns to NULL, not the
   container: `promote()` commits the final blob before hash
   verification and completion, so a failure after that point orphans a
   committed final object (each retry then dies on `storage_conflict`
   until the job terminates `failed` with no reference). The
   unconditional call deletes such an orphan, or proves absence for a
   job that never promoted; a failed job is never downloadable, so no
   downloadable artifact can be touched.

### The ordering rule (sacred, enforced in depth)

- **Never delete an object for a job still downloadable.** The sweep
  selects only `expired`/`failed` + `pending`; `ready` is structurally
  excluded from the SQL, and a runtime guard additionally refuses any
  row whose state is not one of those two — without a storage call —
  even if a defective read ever produced one. The database enforces the
  same rule independently: `usp_CleanupAccountExportJob` throws 57257
  for a still-ready job.
- **Never mark cleaned before the delete succeeded.** The
  `usp_CleanupAccountExportJob` call for a job is issued only after its
  storage deletes returned. A failing delete leaves that job `pending`
  (retried by the next run, safely — every delete is idempotent), is
  logged content-free, and the run continues to the remaining jobs, then
  finishes with outcome `failed` and a nonzero exit code. A failing mark
  after a successful delete is also counted and also fails the run: the
  ledger stays truthful (`pending`), and the next run's no-op delete plus
  retried mark converges.

Both directions are pinned in `tests/test_account_export_worker_ops.py`,
including the still-ready-row defense, the one-job-fails-run-continues
path, and the clean idempotent re-run.

## Logging

All maintenance logging flows through the existing `_log` /
`_LOG_FIELD_NAMES` allowlist, widened deliberately by exactly three
count fields: `expired_count`, `cleaned_count`, `cleanup_failed_count`.
Log lines carry counts, `job_key`, ledger `state`, and `error_type`
only — never a reason string, domain code, artifact reference, or any
member content. A test asserts every captured maintenance log line stays
inside the allowlist.

## What C1 supports that this package deliberately uses

- `usp_ExpireAccountExportJobs`: ledger-only expiry, bounded batches.
- `usp_CleanupAccountExportJob`: refuses `ready` (57257); idempotent
  no-op for `cleaned`/`not_required`; `pending → cleaned` plus audit
  event otherwise. Its recorded contract covers both the
  expired-final-artifact case and the failed-staging case, so the sweep
  handles both identically, driven only by `cleanup_state`.
- The `trg_account_export_jobs_cleanup_guard` trigger guarantees
  `cleaned` can never move backward, so a marked job is permanently
  settled.

## Honestly out of scope (remainder recorded)

- **This code still runs nowhere.** No scheduler, timer, host, container,
  worker identity, or deployment is created here — the runtime home of
  both the export worker and this maintenance mode is a separately gated
  owner decision. **Until that gate, the retention gap remains open in
  production behavior: enabling the export feature for real members
  without also scheduling `--maintenance` would reopen exactly the gap
  this package closes in code.** That warning belongs in the enablement
  checklist for the feature, not only here.
- **Failed jobs with invisible leftovers.** No C1 procedure ever sets
  `cleanup_state = 'pending'` on a `failed` row (`usp_FailAccountExportJob`
  leaves the default `'not_required'`), so a failed job whose in-run
  best-effort staging cleanup ALSO failed is invisible to this ledger-
  driven sweep. The sweep supports `failed` + `pending` rows exactly as
  far as `usp_CleanupAccountExportJob`'s contract does, but nothing can
  create them today. Closing that residue needs a procedure change
  (e.g. fail-time `cleanup_state` marking) that this package's no-SQL
  surface cannot author. Bounded residue: per-attempt staging
  parts (already best-effort deleted at failure time) and, after a
  post-promote failure, possibly an orphaned final object — never
  downloadable either way, since download metadata is served only for
  `ready` jobs. Once such rows can exist, the sweep already removes
  both kinds: `cleanup_final` runs unconditionally for every swept
  job.
- **No live proof.** Every test uses the house fake cursor/connection and
  a fake storage double; nothing here has run against a real database or
  container. First live runs belong to the separately gated operations
  path.
- The seven-day window itself (`@ReadyWindowDays` in the completion
  procedure) is untouched.
- **The C3 gap bullet is retired in this package's diff after all.** At
  this package's activation, `C3_ACCOUNT_EXPORT_EXPERIENCE.md` was held
  by the concurrently activating
  `PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001` (its activation PR
  predates this one), so the retirement was initially deferred. When
  that package closed and released the surface, this package claimed
  the file through the extend-surfaces control transition (PR 841) and
  retired the "Expiry is not deletion" bullet, pointing it here. The
  bullet's closing warning — schedule maintenance before enabling the
  feature — is preserved verbatim in the retired bullet's resolution
  text.
