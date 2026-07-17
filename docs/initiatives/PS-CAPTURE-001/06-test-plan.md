# Test plan

## Automated route and service tests

- Anonymous redirect and exact `return_to`.
- Authenticated composer, returned rows, private label, and honest empty state.
- Exact signed-in `@UserKey`, trimmed body, and `text` create call.
- Blank and 8,001-character rejection with no create call.
- Cross-site form POST rejection before identity or create calls.
- Accessible success/validation messages.
- List/create database failures and no-return create response produce 503.
- Capture procedures remain explicitly allowlisted.

## Migration contract tests

- Forward, rollback, and verification artifacts exist.
- Forward migration is transactional, private-by-default, owner-resolving, and
  contains no caller-supplied profile ID.
- Audit metadata excludes private body content.
- Rollback blocks member data and later dependencies.
- Verification uses two identities, asserts no cross-owner rows, and rolls back.
- Runner selects only the explicitly requested optional migration.
- Foundation verification tolerates later migration ledger records while still
  requiring every foundation record.

## Release checks

1. Focused capture and SQL tests.
2. `tests/test_site_rules.py` guardrails.
3. Full unit-test discovery.
4. Python compilation and diff whitespace checks.
5. Migration plan-only output.
6. Approved Azure SQL apply plus foundation and transactional two-owner checks.
7. Desktop, mobile, keyboard/focus, long-content, 200% zoom, and reduced-motion
   review.
8. Azure pipeline Build and Deploy for the exact merge commit.
9. Production anonymous auth boundary and signed-in save/list verification.
