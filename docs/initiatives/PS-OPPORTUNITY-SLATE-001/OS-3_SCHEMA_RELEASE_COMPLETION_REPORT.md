# PS-OPPORTUNITY-SLATE-001 OS-3 additive schema release record

Status: **Conditional** until this branch passes pull-request validation, is
merged, and `PS-OPPSLATE-002` is applied and verified through the protected
production schema environment. This branch contains no OS-3 route, AI
orchestration, or member-facing UI.

## Core record

- **Task/package and delivery path:** PS-OPPORTUNITY-SLATE-001 slice OS-3,
  schema-first **Protected** release through PS-OPS-001.
- **Outcome and member/site effect:** Restores `PS-OPPSLATE-001` to its exact
  immutable OS-1/OS-2 bytes and moves the OS-3 analysis and response schema
  into the new additive migration `PS-OPPSLATE-002`. Production and the
  current member experience are unchanged until the protected apply and the
  separate OS-3 application release complete.
- **Branch, base SHA, final SHA, and changed paths:**
  `work/2026-08-04-oppslate-os3-additive`. Originally based on authoritative
  `origin/main` at `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3`; the Codex
  implementation commit is `8797c7fe7394f3f32893a73ab5166c2c0e3b037f` and its
  pushed documentation tip is `f602c3fac9b867b12704a89850642de683c0779d`.
  Changed paths are the restored 001 forward, rollback, and verifier; the new
  002 forward, rollback, and verifier; the migration registry; the combined
  migration tests; this completion record; and the corrected governed-gate
  evidence.
- **Reconciliation with current authority (Claude continuation):** `origin/main`
  moved to `d58434869d7873ee16be9df6ca41174ef37c2ca1` while this branch was
  paused, adding the PS-DELIVERY-RESET-001 control plane and changing
  `scripts/govern_sql_migrations.py`, `tests/test_schema_migration_path.py`, and
  `azure-pipelines.yml`. Current `main` was merged into this branch with no
  conflicts, Codex's tip is preserved as an ancestor, and the affected checks
  were re-run against the merged result rather than trusting the earlier run.
- **Verification performed and result:** Disposable Basic-tier database
  `ps-oppslate-additive-gate-20260804` on Azure SQL server `peerslate`.
  The governed gate first proved the restored 001 baseline, then proved the
  additive 002 delta over it. Each passed prerequisite application, forward
  apply, no-op reapply, owner-isolation verification, rollback rehearsal, and
  clean forward reapply. The 001 verifier returned `verified = 1` with exact
  executable SHA-256
  `2406ff6eedd44939ee5148982462a66935f13dfea45fe46076cf5895883c7273`.
  The 002 verifier returned `verified = 1` with exact executable SHA-256
  `2af25b7d4f04984d88a30b7d65bc1948bc4bba810ab048963b4cd85a8d471dd0`.
  Focused migration/path tests: **116 passed, 3 skipped**. Wider affected
  Opportunity Slate, database, and operational tests: **309 passed, 3
  skipped**. Registry validation and `git diff --check`: pass. The disposable
  database was permanently deleted and a follow-up Azure resource lookup
  returned `ResourceNotFound`.

  Re-verified independently on the merged result against current `main`:
  migration and schema-path suites **116 passed, 3 skipped, 292 subtests**;
  those plus the delivery/governance/operational suites **180 passed, 3
  skipped**; the pipeline's own command, `python -m unittest discover -s tests`,
  **2,362 tests run, 26 skipped**, with the only 2 failures being
  `test_auth_release_template` assertions that require PowerShell and fail
  identically on pristine `main` in this Linux container. `govern_sql_migrations
  check` reports **24 registered, 12 gated and matching**, and both OPPSLATE
  digests match the values above.

  The restoration was checked byte-for-byte rather than taken on trust. The
  registry history shows `PS-OPPSLATE-001` gated at
  `2406ff6eedd44939…` on `ps-migration-path-20260804` at merge commit
  `98d1565`, then mutated to `752812bd7d290a0d…` on
  `ps-oppslate-os3-gate-20260804` by PR 274 at `d3af479`. This branch's 001
  forward, rollback, and verifier are byte-identical to the `98d1565` versions,
  which is the form production applied.
- **Release state:** Schema correction pushed and open as an Azure pull
  request; production unchanged. The existing production ledger still records
  the OS-1/OS-2 form of `PS-OPPSLATE-001`; `PS-OPPSLATE-002` has not been
  applied. Merging this pull request changes no database: the schema stage runs
  only on a deliberate manual queue with a non-`none` `schemaAction`.
- **Known limits, deferred work, or owner decision needed:** The OS-3
  application branch remains separate and must not merge or deploy before the
  production 002 result is verified. The earlier reuse of the 001 ledger ID is
  superseded by this additive correction and must not be revived. The semantic
  false-positive limitation was accepted by Pete for the current small demo
  audience; that does not change the anonymous-route truth boundary.
  **Outstanding:** the package requires a fresh independent review of the exact
  candidate SHA for schema work. This continuation performed a complete-diff
  self-review and the re-verification recorded above, but no separate reviewer
  session has run. That remains Pete's call before the protected apply.
- **Next action:** After this pull request passes current-target validation and
  is squash-merged, run the governed **read-only** `schemaAction=report` first.
  It creates `docs/governance/PRODUCTION_SCHEMA_STATE.md`, which does not exist
  yet, and provides the hosted read-only ledger proof the
  `opportunity_slate_schema_revision` finding still requires. Commit that
  generated record, then queue the manual pipeline on the exact merged `main`
  SHA with `schemaAction=apply`, `schemaMigrationId=PS-OPPSLATE-002`, and
  `forceProductionDeploy=false`. Approve the `peerslate-database-schema`
  environment only when the plan shows migration 002 at
  `2af25b7d4f04984d88a30b7d65bc1948bc4bba810ab048963b4cd85a8d471dd0` and leaves
  the applied `PS-OPPSLATE-001` ledger row untouched. Verify the production
  ledger and object inventory, commit the regenerated schema-state record, and
  only then advance the OS-3 application branch. Applying 002 is a schema
  operation; it does not make OS-3 live.

## Protected additions

- **Data, identity, privacy, authorization, deletion, publication, or AI:**
  Every new procedure derives the owner from `@UserKey`, reasserts
  `owner_profile_id` in its predicates, and accepts no caller-supplied owner
  id. The verifier exercises two-owner negative paths and leaves no residue.
  The 002 migration refuses an incomplete or drifted 001 baseline, labels the
  eight procedures it owns with its definition hash, and writes only its new
  immutable ledger row.
- **Migration and rollback proof:** The 002 rollback refuses member rows,
  later migrations, or drifted procedure definitions. It drops the four new
  procedures, restores the four modified 001 procedures to their exact OS-2
  definitions, removes the four new tables, and deletes only the 002 ledger
  row. Both migrations were independently rehearsed through rollback and
  reapply in the disposable Azure SQL database.
- **Shared infrastructure or broad release:** The contained deployment
  principal remains `peerslate-ado-schema` through the existing Azure service
  connection. Its known permissions are `db_ddladmin`, database-definition
  visibility, object-scoped ledger DML, and object-scoped audit-procedure
  execution; it is not a member-data reader/writer or `db_owner` principal.
  No firewall or secret change is part of this correction.
- **Actual handoff:** Clark receives the pushed branch tip, this record, and
  the dedicated handoff document. Codex relinquishes this additive schema
  branch after the exact pushed SHA is reported. Production release authority
  and subsequent application release remain with Pete/the designated manager.
