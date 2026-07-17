# Handoff

**Current state:** released and verified in Azure production through PR 56,
merge `af3547796966628da1672256a332e3b874750c7f`, and pipeline run 75.

## Canonical object

`dbo.captures` is the canonical private intake/source record. No Journal or
destination copy is created.

## Owner and audience

Each record belongs to one `member_profiles` owner resolved from trusted
server-side identity. Only the owner route and owner-scoped procedures read it.
All records in this slice are private; there is no publication step.

## Implemented in production

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
Desktop/mobile browser checks, long-content wrapping, one main landmark, and the
production sign-in boundary are verified.

## Release evidence and boundary

Azure SQL apply, synthetic two-owner isolation with full rollback, all 252
tests, 8/8 guardrails, PR squash merge, exact Build/Deploy stages, App Service
deployment record, and canonical auth redirect are confirmed in
`09-verification.md`.

No real member capture was added during release testing because archive/delete
controls are deferred. This is an intentional test-data boundary, not a claim
that a signed-in production POST was performed.
