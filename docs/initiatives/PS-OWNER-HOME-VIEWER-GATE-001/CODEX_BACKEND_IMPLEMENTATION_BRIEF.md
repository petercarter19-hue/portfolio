# CODEX_BACKEND_IMPLEMENTATION_BRIEF — PS-HOME-BACKEND-001

Prepared 2026-07-19 by the Claude/Fable architecture writer for the future
Codex backend implementation lane. **Activated 2026-07-19** by the designated
ChatGPT Work/Codex manager session. Read the binding corrections and resolved
U1–U6 decisions in `11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md` before starting.
The assignment is queued: do not create the branch until the currently
allocated `PS-CAPTURE-PHOTO-BACKEND-001` lane has merged or explicitly
relinquished its overlapping shared-file reservations.

## 0. Non-negotiables

- Fresh `work/YYYY-MM-DD-home-backend-001` branch from then-current
  `origin/main`. Follow `START_HERE.md` and `docs/AI_WORKFLOW.md`; recheck the
  reservations in `07_FABLE_FILE_RESERVATIONS_INTERSECTIONS.md` against that
  main before editing.
- **Backend merges before any frontend work.** Flag defaults off; no visual
  release; this package does not edit `auth_routes.py` or change `/app` at all.
- Product law: `FINITE_HOME_CONTRACT.md` and
  `04_FABLE_BACKEND_CONTRACT_MAPPING.md`. Nine objects max, three reviews max,
  deduplication, deterministic selection, owner isolation,
  authorization-before-retrieval, failure independence, `private, no-store`,
  ≤64 KiB, no `/api/dashboard` reuse, no fabricated data, no telemetry
  containing member content.

## 1. Deliverables

1. `services/owner_home_service.py` — `get_home(owner_identity)` returning the
   bounded `OwnerHomeViewModel`; explicit `owner-home.v1` serializer with
   field allowlist that fails closed; server-owned versioned
   capability-availability registry emitting `coming_later` for
   `resurfaced_moment`, `noticed_item`, `connection_item` (no member-data
   query behind those states).
2. `usp_GetOwnerHomeForOwner(@UserKey)` via
   `SQL FIles/Migrations/proposed/PS-HOME-001_owner_home_reads.sql` (+ exact
   `_rollback.sql`), verification in
   `SQL FIles/Verification/PS-HOME-001_owner_isolation_verify.sql`.
   One transactionally consistent call returning the bounded result sets
   (review items TOP 3 by urgency → oldest-waiting → stable opaque key; recent
   confirmed Moment TOP 1 excluding review-selected records; next-step inputs).
   Resolve `@UserKey` to the owner profile internally, exactly like
   `usp_ListCapturesForOwner`. Confirm final migration name availability at
   assignment time.
3. Allowlist: add exactly one entry to `ALLOWED_PROCEDURES`
   (`services/database_service.py:11`).
4. Route: `GET /api/v1/owner/home` on the `owner` blueprint
   (`owner_routes.py`). Check the feature flag before identity or data
   retrieval: flag off → neutral `404 {"error":"not_found"}`; flag on →
   `get_current_identity()`, anonymous →
   `401 {"error":"authentication_required"}`, success → `owner-home.v1` with
   `Cache-Control: private, no-store`. Do not add a placeholder page, edit
   `auth_routes.py`, select `owner_home.html`, or otherwise change `/app`.
5. Flag: `PEERSLATE_OWNER_HOME_ENABLED` env → `app.config`, default false,
   following `app.py:96-97`.
6. Tests: new `tests/test_owner_home.py` and
   `tests/test_owner_home_migration.py` covering the full list in
   `10_FABLE_REVIEW_CHARTER_EVIDENCE_MATRIX.md` §2 (schema shape, limits,
   dedup, determinism, two-owner + payload canaries, foreign selectors,
   failure independence, headers, flag-off neutral 404/no retrieval, no-N+1, migration
   apply/verify/rollback/reapply on an isolated database).
7. `docs/initiatives/PS-HOME-BACKEND-001/**` — package README, evidence,
   standard completion report (exact base SHA, branch, full HEAD SHA,
   commands and results, self-certification).

## 2. Files you own (exact)

- `app.py` — only the default-off `PEERSLATE_OWNER_HOME_ENABLED` config entry.
- `services/owner_home_service.py` — new bounded service/serializer.
- `owner_routes.py` — only the flag-gated JSON route.
- `services/database_service.py` — exactly one procedure allowlist entry.
- `SQL FIles/Migrations/proposed/PS-HOME-001_owner_home_reads.sql`.
- `SQL FIles/Migrations/proposed/PS-HOME-001_owner_home_reads_rollback.sql`.
- `SQL FIles/Verification/PS-HOME-001_owner_isolation_verify.sql`.
- `tests/test_owner_home.py` and `tests/test_owner_home_migration.py`.
- `docs/initiatives/PS-HOME-BACKEND-001/**`.

**Do not touch:** `auth_routes.py`, any template/CSS/JavaScript, Voice files,
Capture/Moment/Placement service internals or migrations, `identity.py`,
homepage/Interview/Story files, shared governance records, `.env`, or
`.claude/launch.json`.

## 3. Selection rules to implement (not reinterpret)

- Category priority and one-slot budget per `FINITE_HOME_CONTRACT.md` §"Hard
  content budget" and §"Prioritization and de-duplication".
- Review kinds and priority are fixed by U6: `voice_draft_failed`
  (`voice_media_sources.state='failed'`) → `moment_proposal_pending`
  (`moments.status='proposal'`) → `voice_draft_ready`
  (`voice_media_sources.state='needs_review'`). Within a kind, oldest
  actionable `updated_at_utc` first, then stable opaque key. Exclude confirmed,
  deleted, and deletion-pending records.
- Next step: first eligible of — blocking review/stale conflict → existing
  draft/review flow → recent Capture/Moment management route → (future
  Settings action, skip) → start a new text Capture. Name the action and
  destination truthfully.
- `state_version`: opaque, changes when any selected owner-state input
  changes; used by the frontend for stale handling (`409 state_changed`).

## 4. Evidence before requesting acceptance

Focused tests green; guardrails
(`tests/test_site_rules.py`, `tests/test_governance_pointers.py`) green; full
`python -m unittest discover -s tests` green (record counts and any
environmental skips exactly); SQL gate transcript (apply/verify/rollback/
reapply, no credentials); performance numbers against the founding-alpha
profile (`TEST_RELEASE_PLAN.md`); complete-diff review confirming only
reserved files changed; self-certification `Pass`/`Conditional`/`Fail`.

After Pete/designated-manager acceptance: Azure squash PR, pipeline,
production verification that `/app` and all public routes are unchanged and
the default-off JSON route is neutral, then closeout per `docs/AI_WORKFLOW.md`.
Never claim the Home experience is live — this package ships an inert,
default-off backend only.
