# PS-MOMENT-001 — Capture Review and Canonical Moment Promotion

## Assignment

- Writer: ChatGPT Codex
- Manager/reviewer: ChatGPT Work
- Branch when accepted: `work/YYYY-MM-DD-moment-001`
- Entry gate: PS-NEXT-WAVE-MANAGER-001 is squash-merged, its Azure pipeline is green, and the branch starts from the resulting current `origin/main`.
- Depends on: PS-AUTH-001, PS-CAPTURE-001, and PS-CAPTURE-002 in production.

## Outcome

Implement the first canonicalization boundary over the shipped private text Capture:

**one owner-scoped Capture source version → editable private proposal → explicit member confirmation → source-linked canonical Moment**

The member reviews and edits the proposed structured record before confirmation. The Capture original and revision history remain the source; a later Capture correction never silently rewrites the proposal or confirmed Moment. Confirmation does not publish, place, share, add to Journal, alter a résumé, or create any public projection.

## Acceptance criteria

1. A signed-in owner can choose one active Capture source version, create or reopen one private Moment proposal for it, inspect the exact source version, edit the proposed Moment fields, discard an unconfirmed proposal, and explicitly confirm a valid proposal.
2. The source relationship pins the original Capture or one specific correction revision. A later Capture correction is detectable but does not silently update Moment content or source version.
3. Proposed and confirmed Moment content is owner-scoped, private by default, versioned for review provenance, and never returned across owners.
4. Confirmation requires an explicit action, current row-version token, valid required fields, accessible source, and a server-derived owner identity. It records who/when confirmed and the confirmed proposal version.
5. No procedure, route, or model call automatically publishes, places, shares, creates Journal UI, updates a résumé, or expands visibility.
6. The review page keeps the selected Capture text in a clearly labeled read-only source region and the proposed canonical fields in a separate editable region. Raw Capture text is not copied into unrelated tables or surfaces as a hidden second authority.
7. Capture deletion propagation is deterministic and body-free: an unconfirmed proposal whose only source is deleted cannot later be confirmed; a previously confirmed Moment may retain its member-approved canonical language while its source link becomes an explicit deleted-source tombstone. No deleted source body is retained in the relationship or audit record.
8. Migration apply/verify/guarded rollback/reapply is proven on real SQL Server in an isolated database before any production migration. Rollback refuses to discard Moment data or later dependencies.
9. Two-owner negative tests, stale-version tests, source-pinning tests, deletion-propagation tests, no-auto-publish/placement tests, focused regressions, governance/site guardrails, and the complete suite pass.

## Writable files

- `owner_routes.py` — Capture-to-Moment and protected Moment review routes only
- `templates/owner_capture.html` — minimal “Review as a Moment” entry control only
- `templates/owner_moment_review.html` — new protected review surface
- `static/css/owner-app.css` — Moment-specific selectors only
- `services/database_service.py` — stored-procedure allowlist only
- `services/moment_service.py` — optional new orchestration/validation module
- `SQL FIles/Migrations/proposed/PS-MOMENT-001_moments.sql`
- `SQL FIles/Migrations/proposed/PS-MOMENT-001_moments_rollback.sql`
- `SQL FIles/Verification/PS-MOMENT-001_owner_isolation_verify.sql`
- `scripts/apply_sql_migrations.py` — migration registration/verification only
- `tests/test_owner_moment.py`
- `tests/test_moment_migration.py`
- `tests/test_database_service.py` — allowlist tests only
- Capture lifecycle tests only when required to prove source-deletion propagation
- This initiative directory and its completion report

If implementation requires another shared file, stop and ask the manager to reserve it before editing.

## Read-only and forbidden domains

- Do not edit public résumé or Interview Studio templates, CSS, JavaScript, tests, routes, or datasets.
- Do not change global navigation, global theme tokens, authentication architecture, public routes, profile identity, or deployment configuration.
- Do not start PS-PLACEMENT-001, Journal UI, voice/media Capture, AI proposal generation, audience controls, public sharing, Story/Work/Project/Feed integration, or account-wide export/deletion.
- Do not insert raw Capture text into Journal, Story, Work, résumé, Interview Studio, Feed, placement, or another downstream surface.
- Do not require an LLM to prove the canonical review boundary. AI may populate proposals only in a later separately authorized package.

## Required reading

Follow `START_HERE.md`, then read the current baseline/state/initiatives, Document Control, Bible/Roadmap/Sync Standard, PS-CAPTURE-001, PS-CAPTURE-002, [architecture and state contract](01_ARCHITECTURE.md), [security/privacy contract](02_SECURITY_PRIVACY.md), [test plan](03_TEST_PLAN.md), and [implementation sequence](04_IMPLEMENTATION_PLAN.md).

Close with `docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md` and the exact branch plus full commit SHA.
