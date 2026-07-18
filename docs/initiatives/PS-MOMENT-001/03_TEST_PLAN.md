# PS-MOMENT-001 — Test and Evidence Plan

## Repository tests

Add focused route/service tests proving:

- unauthenticated requests redirect before database calls;
- same-origin enforcement for every write;
- server-derived identity and no accepted browser user/profile ID;
- valid create/reopen, review, edit/version, explicit confirm, and proposal discard;
- required-field/length validation and safe database failure behavior;
- stale row versions and stale proposal versions cannot save or confirm;
- confirmed status is private and creates no placement/publication/Journal/résumé/etc.;
- protected page separates read-only source from editable proposal;
- no public Interview Studio or résumé files/behavior change.

Add migration contract and real verification coverage for:

- prerequisite ledger checks;
- owner/profile/source/aggregate/version/source-link constraints;
- one pinned original or correction revision;
- later Capture corrections do not mutate a Moment;
- two owners cannot get, edit, confirm, discard, or infer each other's source/Moment;
- idempotent proposal creation for the same owner/source version;
- source deletion propagation and body-free tombstone/audit data;
- unconfirmed source-deleted proposal cannot confirm;
- confirmed source-deleted Moment retains only approved canonical content plus body-free provenance;
- rollback blocks on data/later dependencies and restores exact PS-CAPTURE-002 behavior when safe.

Run at minimum:

- new Moment route/service/migration tests
- affected Capture lifecycle/database-service tests
- `tests/test_governance_pointers.py`
- `tests/test_site_rules.py`
- the repository's complete discovered test command
- syntax/import checks and `git diff --check`

## Real SQL gate

Before production migration, use a short-lived isolated Azure SQL database with no production/member data:

1. Apply the existing foundation, PS-CAPTURE-001, and PS-CAPTURE-002 prerequisites.
2. Apply PS-MOMENT-001.
3. Run a transactional two-owner verifier for proposal/version/confirm/source-pinning/deletion behavior and no automatic placement/publication.
4. Prove guarded rollback on an empty Moment state and verify the exact prior objects remain.
5. Reapply and rerun verification.
6. Delete the exact temporary database and confirm it is absent.

Any incompatibility, unknown dependency, rollback ambiguity, or production-schema difference is a stop condition for manager review. Do not apply the production migration merely because repository tests pass.

## Protected UI evidence

Review at desktop, 390×844 mobile, keyboard only, and 200% zoom. Prove private/proposal/confirmed labels, read-only source separation, validation errors, stale-state recovery, explicit confirmation, discard confirmation, visible focus, no horizontal overflow, and no accidental public/placement controls.

## Release evidence

The completion report must separate repository tests, isolated SQL evidence, production migration evidence, deployed auth-boundary checks, and real-member validation. No real-member workflow may be claimed without performing it safely after deployment.
