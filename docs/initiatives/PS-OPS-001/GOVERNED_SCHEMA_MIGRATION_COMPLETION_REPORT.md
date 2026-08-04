# Governed production schema-migration path completion record

Status: **Conditional** until Azure DevOps PR 273 passes its blocking build,
merges, and the merged pipeline result is verified. This record describes the
path itself; it is not evidence that any Opportunity Slate migration has been
applied.

## Core record

- **Task/package and delivery path:** PS-OPS-001 shared infrastructure,
  **Protected**. Establish one registry-backed, approval-gated path for
  reporting, applying, and rolling back production SQL migrations.
- **Outcome and member/site effect:** No member-facing behavior changes. The
  pipeline gains a separate manual-main schema stage; application deployment
  does not open the database, and a schema run does not deploy the web app.
- **Branch, base SHA, final SHA, and changed paths:**
  `work/2026-08-04-governed-migration-path`; base
  `ed257c7b5dbc21b99208d117f509f9b6d457e95a`; implementation/reconciliation
  head before this closeout record
  `90d3d575626a3d80508bf0868b406b7e46e710c1`. Changed paths are
  `azure-pipelines.yml`, the SQL registry, the existing migration applier,
  `scripts/govern_sql_migrations.py`, `scripts/migration_registry.py`, the
  PS-OPS-001 runbook/README, and focused operational tests.
- **Verification performed and result:**
  `pytest tests/test_schema_migration_path.py tests/test_operational_readiness.py -q`
  → **71 passed, 1 skipped; 25 subtests passed**. The skip is the separately
  credentialed live-engine path. `python scripts/govern_sql_migrations.py check`
  → **23 registered, 11 gated and hash-matched; pass**. Complete-diff review
  and `git diff --check` passed.
- **Release state:** Active Azure DevOps PR 273. The original blocking build
  485 failed at plan validation because the protected environment did not yet
  exist. On 2026-08-04 Pete authorized creation of environment
  `peerslate-database-schema`, its Pete-only approval check, and the secret
  `schemaConnectionString` pipeline variable. Build 486 is the re-queued proof
  that the former environment-validation failure is cleared; PR 273's policy
  record identifies the final exact-source validation for the branch head.
- **Known limits, deferred work, or owner decision needed:** The path can
  report, apply, or roll back only registry entries with matching durable gate
  proof. Opportunity Slate OS-3/OS-4 remain separate schema operations and are
  not applied by this PR.
- **Next action:** Verify PR 273's exact-source blocking build, squash-merge the
  PR, verify the exact merge pipeline, then use a separately approved
  manual-main `report`/`apply` run for the named Opportunity Slate migration.

## Protected additions

- **Data/authorization/migration proof:** The connection string is a secret
  pipeline variable and is injected only into the guarded schema job. Offline
  registry and SHA-256 checks run before a connection is opened. Apply requires
  the registered verifier; rollback requires the registered rollback artifact,
  an exact migration id, and a second typed confirmation. No secret was printed
  or written to the repository during environment setup.
- **Shared infrastructure/release:** Environment
  `peerslate-database-schema` has a 30-day approval check whose sole approver is
  `peerslate19@gmail.com`; the check instructs Pete to confirm the exact
  registered migration, hash, verifier plan, and rollback plan. The path is
  intentionally serialized (`lockBehavior: sequential`).
- **Actual handoff:** Pete is operational owner. Exact pushed implementation
  SHA is `90d3d575626a3d80508bf0868b406b7e46e710c1`; PR 273 remains open until the
  conditional release evidence above is complete.

## First production-use correction — 2026-08-04

- PR 273 subsequently passed build 488 and squash-merged as
  `98d1565641b6476a85c7a58ff06ec54951c075a9`. The protected environment and
  Pete-only approval check are active.
- Opportunity Slate schema run 497 validated the registry, received both the
  environment permission and explicit approval, then failed before opening a
  database connection. `argparse` rejected global option `--print-state`
  because the pipeline placed it after the `apply` subcommand. No migration
  SQL executed and no production schema state changed in that run.
- Follow-up branch `work/2026-08-04-schema-cli-order-fix`, based on current
  `main` `2b0246c8d968d7e49b0762a0129aab4e6d99392b`, moves the global option ahead
  of all three connected subcommands (`report`, `apply`, and `rollback`) and
  adds an ordering regression test. Focused result: **45 passed, 1 skipped;
  3 subtests passed**. Registry check: **23 registered, 11 gated and
  hash-matched; pass**. `git diff --check`: pass.
- The correction is not production-effective until its PR passes, merges, and
  a new exact-main run proves the OS-3 apply. Run 497 is failure evidence, not
  a partial schema release.
