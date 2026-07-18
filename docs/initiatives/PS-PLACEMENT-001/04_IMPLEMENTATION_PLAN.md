# PS-PLACEMENT-001 — Implementation Sequence

## Entry

1. Follow `START_HERE.md` and synchronize from authoritative Azure `origin/main`.
2. Confirm PS-BACKEND-NEXT-GATE-MANAGER-001 is present on main and its pipeline is green.
3. Read the current controlled documents and all PS-PLACEMENT-001 files.
4. Create `work/YYYY-MM-DD-placement-001` from the exact current `origin/main`; record the full base SHA.
5. Confirm no other writer owns the branch and no file outside the package allowlist is required.

## Build order

1. Inventory current production-chain schemas/procedures for `moments`, `moment_versions`, `moment_sources`, `slate_entities`, audit, access, and publication. Record any incompatibility before writing.
2. Draft the versioned forward migration with dependency checks, minimum composite keys/indexes, body-free placement table, procedures, fingerprints, and migration-ledger record.
3. Draft the guarded rollback before implementing application code. Destructive statements must follow all data, later-migration, dependency, and fingerprint guards.
4. Add the isolated SQL verifier with two synthetic owners, confirmed/proposal Moments, eligible/ineligible targets, exact-version assertions, lifecycle checks, content sentinels, no-side-effect counts, and full rollback.
5. Register forward migration and verifier in `scripts/apply_sql_migrations.py`.
6. Add the minimum database allowlist and optional `placement_service.py`. Do not add routes, templates, public consumers, or UI.
7. Add focused static and behavioral tests, including concurrent duplicate creation and remove/reactivate sequencing on real SQL Server.
8. Run isolated apply/verify/concurrency/guarded rollback/reapply proof on a temporary database; delete only after validating the exact resource.
9. Run focused, governance/site, complete-suite, syntax, diff, staged allowlist, secret-pattern, and plan-only gates.
10. Complete `COMPLETION_REPORT.md`, commit, push, verify remote SHA and clean tree, relinquish writer ownership, and hand off to ChatGPT Work.

## Required design choices

- Prefer database-enforced tenant integrity and uniqueness over service-only checks.
- Store the exact confirmed Moment version, not merely the current Moment pointer.
- Keep placement lifecycle as metadata; never hard-delete a real placement through ordinary remove behavior.
- Make create/reactivate and remove explicit and concurrency-protected.
- Return reference metadata only. A future consumer may retrieve canonical content through its own authorized domain service.
- Treat target availability as a current state, not a reason to mutate the target.

## Stop conditions

Stop and report to ChatGPT Work before continuing if:

- current main does not contain the verified PS-MOMENT-001 boundary;
- the target entity foundation cannot enforce same-owner references;
- placement requires creating/editing a destination or copying text;
- a public/audience/publication/access change appears necessary;
- rollback cannot be made data-safe and dependency-aware;
- another active package owns a required file;
- isolated real SQL Server proof cannot be completed; or
- a requirement conflicts with Bible/Roadmap v2.3 or the current hold on Journal.

## Handoff contract

Use the required repository handoff format and include:

- branch and exact 40-character HEAD;
- exact base and current merge-base;
- clean working-tree and remote-SHA verification;
- changed-file allowlist;
- migration and rollback design summary;
- isolated SQL resource name and deletion confirmation;
- concurrency/idempotency evidence;
- tests and exact counts;
- explicit no-text-copy/no-publication/no-downstream-write proof;
- known gaps and next action;
- statement that no PR, production SQL, merge, deployment, downstream integration, or next package was started;
- active writer relinquished: yes.
