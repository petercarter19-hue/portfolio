# Handoff

**Current state:** implementation and Azure SQL migration verified; PR 56 is
active and application deployment is not yet live.

## Canonical object

`dbo.captures` is the canonical private intake/source record. No Journal or
destination copy is created.

## Owner and audience

Each record belongs to one `member_profiles` owner resolved from trusted
server-side identity. Only the owner route and owner-scoped procedures read it.
All records in this slice are private; there is no publication step.

## Implemented on the task branch

- Protected text composer and recent-capture list.
- Required/max-length validation and controlled unavailable state.
- Owner-scoped forward migration, guarded rollback, and metadata-only audit.
- Transactional two-owner isolation verification.
- Explicit procedure allowlist and optional-migration runner support.
- Focused application and migration-contract tests.

## Fixture-only or mocked

Automated Flask tests mock identity/database results to verify application
contracts. The SQL verifier uses real procedures and temporary synthetic rows,
then rolls them back. No fixture capture is shown as member data.

## Deferred

- Non-text capture, placement, Journal, AI, audience choice, and publication.
- Archive/delete/correction/export member controls.
- Retry-specific UI beyond reloading after a temporary 503.

## Accessibility and status truth

The form has a label, hint, character limit, visible focus, accessible status
and alert regions, responsive document flow, and no fake action controls.
Final browser evidence is pending.

## Release gate

Do not call this package complete until the migration verification, full tests,
Azure PR/squash merge, exact pipeline, production auth boundary, signed-in
owner isolation, and backup mirror are confirmed in `09-verification.md`.
