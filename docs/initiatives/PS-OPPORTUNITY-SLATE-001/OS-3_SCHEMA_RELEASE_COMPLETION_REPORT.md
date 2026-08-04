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
  `work/2026-08-04-oppslate-os3-additive`, based on authoritative
  `origin/main` at `af1c6a2216bdb5cddd932fbc3d5c1d0e23ef95b3`. The exact
  implementation SHA and pushed handoff tip are recorded in the Clark handoff.
  Changed paths are the restored 001 forward, rollback, and verifier; the new
  002 forward, rollback, and verifier; the migration registry; the combined
  migration tests; this completion record; and the corrected governed-gate
  evidence.
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
- **Release state:** Local schema correction, ready for review and push;
  production unchanged. The existing production ledger still records the
  OS-1/OS-2 form of `PS-OPPSLATE-001`; `PS-OPPSLATE-002` has not been applied.
- **Known limits, deferred work, or owner decision needed:** The OS-3
  application branch remains separate and must not merge or deploy before the
  production 002 result is verified. The earlier reuse of the 001 ledger ID is
  superseded by this additive correction and must not be revived. The semantic
  false-positive limitation was accepted by Pete for the current small demo
  audience; that does not change the anonymous-route truth boundary.
- **Next action:** Review and merge this correction through an Azure DevOps
  pull request. After the automatic main run finishes, queue the governed
  manual pipeline with `schemaAction=apply`,
  `schemaMigrationId=PS-OPPSLATE-002`, and
  `forceProductionDeploy=false`; approve the protected plan only when the
  exact hash above is shown. Verify the production ledger and objects before
  advancing the OS-3 application branch.

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
