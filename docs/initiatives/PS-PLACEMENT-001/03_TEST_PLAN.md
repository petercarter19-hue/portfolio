# PS-PLACEMENT-001 — Test and Release Plan

## 1. Static migration contract

Focused tests must prove the migration and rollback contain:

- dependency checks for PS-MOMENT-001 and the owner/entity/audit foundations;
- a body-free `dbo.moment_placements` model;
- composite tenant-safe Moment and target references;
- exact confirmed-version pinning;
- active/removed lifecycle and row-version concurrency;
- one-active-logical-placement uniqueness;
- owner-resolving create/reactivate, list, and remove procedures;
- no text/JSON columns or text parameters/results;
- no writes to entity content, relations, access grants, publication versions, or downstream domain tables;
- rollback guards before any destructive statement;
- migration registration and focused verifier registration.

## 2. Service and procedure behavior

Use synthetic owners and opaque keys to cover:

- confirmed Moment + eligible same-owner target → created;
- exact retry → existing with one row and one create audit success;
- removed placement + still-eligible target → reactivated;
- explicit removal → removed without changing Moment/target;
- stale Moment or placement row-version → no write;
- proposal/non-confirmed Moment → no placement;
- target draft, non-private, published, inactive, deleted, or missing → no placement;
- source-deleted confirmed Moment → allowed without source-body retrieval;
- source-deleted proposal → not eligible;
- owner A Moment + owner B target → no write/no disclosure;
- owner A request for owner B placement/Moment/version → no protected result;
- malformed keys/tokens → deterministic validation failure;
- simulated storage failure → privacy-safe unavailable behavior and no false success.

## 3. Concurrency and idempotency

On real SQL Server with two independent connections:

- issue simultaneous create calls for the same logical placement;
- prove one active row, deterministic outcomes, and no deadlock;
- prove an overlapping remove/reactivate sequence serializes to a valid final lifecycle state;
- prove duplicate retries do not append duplicate success audit events;
- record lock/wait evidence without printing content.

## 4. Data-minimization and no-side-effect proof

Seed synthetic sentinel text only in canonical Capture/Moment/target fixture locations. After placement create/list/remove/reactivate:

- sentinel occurrences in placement table, procedure request fields, audit metadata, entity relation rows, access grants, and publication snapshots must be zero;
- counts and lifecycle fields for `dbo.slate_entities`, `dbo.slate_entity_relations`, `dbo.entity_access_grants`, and `dbo.entity_publication_versions` must remain unchanged;
- Story, Work, Project, résumé, Studio, Journal, Feed, and other downstream tables must remain unchanged;
- no public/private route behavior changes because this package has no UI or route.

All synthetic SQL rows must roll back.

## 5. Migration apply/down/reapply proof

Before production, use a short-lived empty SQL Server database containing the current production migration chain:

1. Apply PS-PLACEMENT-001.
2. Run schema and two-owner behavior verification.
3. Prove concurrency/idempotency with independent connections.
4. Prove rollback refuses with a synthetic placement row.
5. Prove rollback refuses with a synthetic later migration.
6. Prove rollback refuses after a protected-procedure alteration or missing protected procedure.
7. Remove/roll back test-only state.
8. Run normal guarded rollback and verify only Placement artifacts are removed.
9. Verify Capture, Moment, entity, relation, access, publication, and audit contracts remain intact.
10. Reapply PS-PLACEMENT-001 and rerun verification.
11. Validate the exact temporary resource before deletion and confirm it is gone.

No production SQL may be applied by Codex. ChatGPT Work owns the production migration gate after branch review.

## 6. Repository gates

At minimum run:

- placement-focused migration/service/database tests;
- existing Moment and Capture regressions affected by migration registration;
- `tests/test_governance_pointers.py` and `tests/test_site_rules.py`;
- the complete configured test suite;
- syntax/import checks for changed Python files;
- `git diff --check`;
- staged-file allowlist and secret-pattern checks;
- migration plan-only selection proving no database connection.

## 7. Manager release gate

Codex stops after commit, push, and exact-SHA handoff. ChatGPT Work will:

1. inspect the complete branch delta and re-run proportional tests;
2. open the Azure PR only after review passes;
3. apply/verify the backward-compatible production migration through the configured secure connection path;
4. squash-merge and delete the source branch;
5. verify the exact merge commit’s Azure Build and Deploy stages;
6. verify unchanged public/protected route health and the production placement schema/procedure boundary without reading member content;
7. report any real-member validation limit honestly.
