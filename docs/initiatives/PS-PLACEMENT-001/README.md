# PS-PLACEMENT-001 — Confirmed Moment Placement References

## Assignment

- Writer: ChatGPT Codex
- Manager/reviewer: ChatGPT Work
- Branch when accepted: `work/YYYY-MM-DD-placement-001`
- Entry gate: PS-BACKEND-NEXT-GATE-MANAGER-001 is squash-merged, its Azure pipeline is green, and the branch starts from the resulting current `origin/main`.
- Depends on: PS-AUTH-001, PS-PLAT-002/PS-PLAT-005, PS-CAPTURE-001/002, and PS-MOMENT-001 in production.

## Outcome

Implement the first “create once, place many” backend reference contract:

**one exact owner-confirmed Moment version → one explicit private placement reference → one existing owner-owned private/unpublished Slate destination**

The reference connects records by stable IDs. It never copies Capture text, Moment title/narrative, destination content, or presentation wording. Creating or removing the reference does not create or edit the destination, change its audience, publish anything, create an access grant, or update a downstream page.

This package is backend foundation work. It does not add a public experience or claim that Story, Work, Project, résumé, Studio, Journal, Feed, or sharing already consumes placements.

## Acceptance criteria

1. An explicit authenticated-owner call can create or reactivate one placement from a confirmed private Moment to an existing active, approved, private, unpublished `dbo.slate_entities` destination owned by the same member.
2. The placement pins the exact confirmed `dbo.moment_versions` row. A proposal, a non-confirmed version, an absent Moment, an unavailable destination, or a stale Moment/placement row-version token fails closed.
3. Placement persistence contains identifiers, ownership, lifecycle state, actors, timestamps, and concurrency tokens only. It contains no Capture body, Moment title/narrative/why-it-matters, destination body, presentation snapshot, audience payload, prompt, or AI output.
4. Duplicate concurrent create requests deterministically produce one active reference. Idempotent re-entry returns the existing reference without creating a second row or audit success event.
5. Removing a placement is explicit, owner-scoped, row-version protected, reversible by a later explicit reactivation, and does not delete or alter the Moment, its source, its destination, or another placement.
6. Cross-owner Moment, version, placement, or destination references return no protected data and perform no write. Owner identity is always server-derived.
7. Create, list, and remove operations never change `dbo.slate_entities` visibility/approval/publication/active state, never write `dbo.entity_access_grants` or `dbo.entity_publication_versions`, and never create Story/Work/Project/résumé/Studio/Journal/Feed records.
8. Source-deleted confirmed Moments remain eligible because the confirmed canonical language survives with a body-free source tombstone. Unconfirmed proposals remain ineligible.
9. Migration apply/verify/guarded rollback/reapply is proven on real SQL Server in an isolated database before any production migration. Rollback refuses when placement rows, later migrations, or protected-procedure drift make data loss or contract reversal unsafe.
10. Two-owner negative tests, exact-version tests, target-state tests, concurrency/idempotency tests, remove/reactivate tests, no-text-copy and no-publication tests, focused regressions, governance/site guardrails, and the complete suite pass.

## Writable files

- `services/database_service.py` — placement stored-procedure allowlist only
- `services/placement_service.py` — optional new validation/orchestration module
- `SQL FIles/Migrations/proposed/PS-PLACEMENT-001_moment_placements.sql`
- `SQL FIles/Migrations/proposed/PS-PLACEMENT-001_moment_placements_rollback.sql`
- `SQL FIles/Verification/PS-PLACEMENT-001_owner_isolation_verify.sql`
- `scripts/apply_sql_migrations.py` — placement migration registration/verification only
- `tests/test_placement_migration.py`
- `tests/test_placement_service.py` — if the service module is created
- `tests/test_database_service.py` — placement allowlist tests only
- this initiative directory and its completion report

No owner route or template is authorized in this foundation package. If implementation requires another shared file, stop and ask ChatGPT Work to reserve it before editing.

## Read-only and forbidden domains

- Do not edit public résumé or Interview Studio templates, CSS, JavaScript, tests, routes, or datasets.
- Do not change Capture or Moment UI/routes except when a manager-approved contract defect makes the reference boundary impossible; stop first rather than expanding scope.
- Do not change global navigation, theme tokens, authentication architecture, deployment configuration, or existing destination content.
- Do not create Journal UI, Story/Work/Project/résumé/Studio/Feed integration, sharing, publication, audience controls, access grants, public projection, voice/media Capture, AI proposals, or purpose-specific placement wording.
- Do not insert raw Capture text or canonical Moment text into `dbo.moment_placements`, `dbo.slate_entities`, `dbo.slate_entity_relations`, publication snapshots, audit metadata, request fields, or another surface.
- Do not automatically place on Moment confirmation. Placement always requires a separate explicit owner action.

## Required reading

Follow `START_HERE.md`, then read the current baseline/state/initiatives, Document Control, Bible/Roadmap/Sync Standard, PS-CAPTURE-001/002, PS-MOMENT-001, [architecture contract](01_ARCHITECTURE.md), [security/privacy contract](02_SECURITY_PRIVACY.md), [test plan](03_TEST_PLAN.md), and [implementation sequence](04_IMPLEMENTATION_PLAN.md).

Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` and the exact branch plus full commit SHA. Do not open a PR, apply production SQL, merge, deploy, or start the next package; hand the reviewed branch back to ChatGPT Work.
