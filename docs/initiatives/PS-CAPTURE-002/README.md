# PS-CAPTURE-002 — Private Capture Lifecycle

## Assignment

- Writer: ChatGPT Codex
- Manager/reviewer: ChatGPT Work
- Branch when accepted: `work/YYYY-MM-DD-capture-002`
- Entry gate: PS-BASELINE-001 is squash-merged, its Azure pipeline is green, and this branch is created from the resulting current `origin/main`.
- Depends on: PS-AUTH-001 and PS-CAPTURE-001.

## Outcome

Add correction, archive/restore, explicit delete, and versioned per-capture export to the shipped private text Capture. All operations remain owner-scoped and private. The original source text and revision provenance are preserved until the owner explicitly deletes the capture.

## Acceptance criteria

1. A signed-in owner can view one of their captures, correct it through a new revision, archive it, restore it, explicitly delete it, and export it as versioned JSON.
2. The original `dbo.captures.body` is never overwritten by correction. Current display text comes from the newest revision, or the original when no revision exists.
3. Every read/write derives the owner from the authenticated server identity; no client profile ID is trusted.
4. Cross-user keys, forged requests, stale row versions, and cross-site writes fail without revealing whether another owner’s capture exists.
5. Correction/archive/restore/delete do not publish, place, create a Moment, change visibility, or copy text into another surface.
6. Delete removes the original body and all revisions transactionally. Only body-free audit metadata may remain.
7. Migration up/down is proven in the repository test path. Rollback refuses to discard revision or archived state silently.
8. Focused backend tests, governance/site guardrails, and existing Capture regressions pass.

## Writable files

- `owner_routes.py` — Capture lifecycle routes only
- `templates/owner_capture.html` — minimal protected Capture controls only
- `static/css/owner-app.css` — Capture-specific selectors only
- `services/database_service.py` — stored-procedure allowlist only
- `SQL FIles/Migrations/proposed/PS-CAPTURE-002_capture_lifecycle.sql`
- `SQL FIles/Migrations/proposed/PS-CAPTURE-002_capture_lifecycle_rollback.sql`
- Capture-specific verification SQL if the repository pattern requires it
- `scripts/apply_sql_migrations.py` — migration registration only
- `tests/test_owner_capture.py`
- `tests/test_capture_migration.py`
- `tests/test_database_service.py`
- This initiative directory and its completion report

If implementation requires another shared file, stop and ask the manager to reserve it before editing.

## Read-only and forbidden domains

- Do not edit public résumé or Interview Studio templates, CSS, JavaScript, tests, or data.
- Do not change global navigation, the Deep Navy Gold theme, authentication architecture, public routes, or member-profile identity.
- Do not start Journal UI, canonical Moment, placement, AI structuring, audience controls, public sharing, or account-wide export/deletion.
- Do not copy raw Capture text into any other table or surface.

## Required reading

Follow `START_HERE.md`, then read the current baseline/state/initiatives, Document Control, Bible/Roadmap/Sync Standard, PS-CAPTURE-001, [architecture contract](01_ARCHITECTURE.md), [security contract](02_SECURITY_PRIVACY.md), [test plan](03_TEST_PLAN.md), and [implementation sequence](04_IMPLEMENTATION_PLAN.md).

Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` and the exact branch plus full commit SHA.
