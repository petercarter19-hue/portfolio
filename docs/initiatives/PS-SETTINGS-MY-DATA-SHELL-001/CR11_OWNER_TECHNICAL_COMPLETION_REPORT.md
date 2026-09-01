# CR11 owner technical completion report

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001`
**Delivery path:** Protected (deletion of member-facing artifacts);
independent review required.
**Outcome:** The recorded "expiry is not deletion" retention gap is closed
in code: the export worker gains a `--maintenance` mode that expires
past-window jobs in the ledger and then actually deletes their archives
from the private container, delete-first, mark-after, ledger-driven, and
idempotent.

## Changed paths

- `scripts/run_account_export_worker.py` — `run_maintenance`,
  `expire_ready_jobs`, `fetch_cleanup_pending_jobs`, `mark_job_cleaned`,
  the `--maintenance` flag on the existing entrypoint, and three new
  count fields in the content-free log allowlist. `run_once` and the
  export path are untouched.
- `tests/test_account_export_worker_ops.py` — new file; offline tests
  pinning expire execution, sweep scope, the delete-then-mark ordering,
  the never-touch-a-ready-job rule, failure loudness, idempotent re-run,
  and log discipline.
- `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR11_EXPORT_WORKER_OPS.md`
  — the package contract document.
- `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C3_ACCOUNT_EXPORT_EXPERIENCE.md`
  — the "Expiry is not deletion" bullet retired with a pointer to the
  CR11 contract document (surface claimed via the extend-surfaces
  control transition after `PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001`
  closed and released it).
- This report, plus the package's governance claim records.

## Verification performed

Full offline suite (`unittest discover -s tests`) green locally before
push, including the new worker-ops file. No database, storage, network,
or provider call in any test: DB interactions use the house shared-plan
fake cursor/connection; storage uses a fake double modeled on the
integration suite's own.

## Review and merge state

Frozen candidate pushed for independent review (Protected path). Not
merged at the time this report was written; no receipt issued by the
writer. Merge follows the accepted independent review through the
ordinary preflight-gated path.

## Deployment, schema, enablement state

Nothing deployed, scheduled, enabled, or applied. No SQL file changed;
no migration; no production operation; production authority withheld.
A merge of this package changes repository truth only.

## Known limits and owner decision needed

- **This code runs nowhere until the owner's worker-host gate.** The
  export worker and this maintenance mode share the same missing runtime
  home. Until a host schedules `--maintenance`, the seven-day retention
  promise remains enforced only in the ledger for any archive that ever
  reaches `ready` in a real environment.
- **Enablement warning:** turning the export feature on for real members
  without scheduling maintenance would reopen the exact gap this package
  closes. The enablement decision must pair the two.
- Failed jobs' leftovers (staging parts, or an orphaned final object
  from a post-promote failure — never downloadable either way) remain
  invisible to the ledger-driven sweep while no procedure sets
  `pending` on a failed row; closing that residue needs a future SQL
  slice. When such rows exist, the sweep already deletes both kinds:
  `cleanup_final` runs unconditionally for every swept job.
- No live database or Blob proof; first live maintenance run belongs to
  the separately gated operations path.
- The C3 "Expiry is not deletion" bullet IS retired in this diff. At
  activation the C3 doc was held by the concurrently activating
  `PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001`; after its close
  released the surface, this package claimed it through the
  extend-surfaces control transition (PR 841) and the bullet now points
  at `CR11_EXPORT_WORKER_OPS.md`.

## Next action

Independent review of the frozen candidate, then merge and close. The
worker-host/scheduling decision remains with the owner and is not
advanced by this package.
