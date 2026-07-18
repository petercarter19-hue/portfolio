# PS-CAPTURE-002 — Verification Plan

## Migration tests

- forward migration requires PS-AUTH-001 and PS-CAPTURE-001 and is idempotent;
- creates the revision constraints/indexes and owner-scoped procedures;
- records PS-CAPTURE-002 in `dbo.schema_migrations`;
- rollback succeeds on an empty/reversible test state and restores PS-CAPTURE-001 behavior;
- rollback stops with a clear error when revisions or archived state would be lost;
- apply → rollback → reapply succeeds in an isolated test database path.

## Service and route tests

- procedure allowlist contains only the required new procedures;
- unauthenticated requests redirect to sign-in without database calls;
- valid correct/archive/restore/delete/export requests pass server-derived `@UserKey` and opaque key;
- required fields, UUID, UTF-16 length, row-version, and same-origin checks fail safely;
- stale and not-found/foreign outcomes are generic;
- exported JSON, headers, filename, order, and schema version are deterministic;
- delete requires explicit confirmation and uses POST.

## Data and authorization tests

Use at least two owners and prove every operation is isolated. Confirm original-body immutability, ordered revisions, current-body selection, archive visibility/filter behavior, reversible restore, transactional delete, body-free audit, and no automatic visibility/placement/Moment changes.

## Regression and release

Run at minimum:

- `tests/test_owner_capture.py`
- `tests/test_capture_migration.py`
- `tests/test_database_service.py`
- `tests/test_governance_pointers.py`
- `tests/test_site_rules.py`
- the repository’s complete discovered test command in a configured environment

Capture exact commands/results in the completion report. After Azure merge/deploy, verify the unauthenticated protection boundary and perform an authenticated real-owner lifecycle check only through approved test data. Do not use or expose secrets in evidence.
