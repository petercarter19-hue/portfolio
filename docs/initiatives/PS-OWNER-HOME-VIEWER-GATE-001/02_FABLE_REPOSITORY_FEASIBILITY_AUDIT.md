# PS-OWNER-HOME-VIEWER-GATE-001 — Current-Repository Feasibility Audit

Recorded 2026-07-19 by the Claude/Fable architecture writer against
`origin/main` `6d5ef46ce05bd7c3a3f6e4b4c356bdf9c9bc6fcd` (verified locally and
remotely; guardrail suites 25/25 and full suite 494 passed / 1 environmental
skip in this worktree). This updates the Codex `CURRENT_STATE_INVENTORY.md`
(audited at `31864e4…`, synchronized through `5cc5b69…`) to the current main.

## 1. Existing foundations (verified in code at this base)

### Owner identity and auth boundary

- `identity.py` — `get_current_identity()` / `get_optional_identity()` return
  a `PeerSlateIdentity` dataclass keyed by opaque `user_key`
  (`identity.py:51-52, 210, 247`); trusted Easy Auth principal parsing with a
  config-gated development identity (`PEERSLATE_ALLOW_DEV_IDENTITY`,
  `PEERSLATE_DEV_USER_KEY`).
- Enforcement is **per-route**, not decorator-based: protected routes call
  `get_current_identity()` and catch `AuthenticationRequired` → redirect to
  `auth.sign_in` with a validated local `return_to`
  (`auth_routes.py:113-128`), and `DatabaseServiceError` → 503 unavailable
  page. Owner Home must reuse exactly this pattern.
- `/app` HTML is `auth.owner_workspace` (`auth_routes.py:113`), rendering
  `owner_workspace.html` with `page_title="My PeerSlate"`. A shared
  `app_context_processor` exposes `current_member` / `owner_workspace_url`
  to every template (`auth_routes.py:131-148`).

### Route and blueprint structure

- Single Flask app (`app.py`, 2,683 lines) plus blueprints registered at
  `app.py:136-140`: `auth`, `owner`, `control_room`, `peerslate_api`,
  `people_interests_api`.
- The `owner` blueprint has **no url_prefix**; each route declares its full
  `/app/...` path (`owner_routes.py:38, 256, 274`). A new
  `GET /api/v1/owner/home` can therefore live on the `owner` blueprint.
- Feature flags are environment variables surfaced through `app.config` with
  the `PEERSLATE_*` prefix (e.g. `PEERSLATE_LIVING_RESUME_DB_ENABLED`,
  `app.py:96-97`), read at request time.

### Database access

- `services/database_service.py` — single `DatabaseService` executing only
  procedures in the `ALLOWED_PROCEDURES` frozenset, `usp_*` naming, strict
  parameter-name validation, positional binding (`database_service.py:8-115`).
- Owner-scoped read convention: `usp_<Verb><Noun>ForOwner(@UserKey, …)` —
  e.g. `usp_ListCapturesForOwner`, `usp_GetMomentForOwner`,
  `usp_GetVoiceDraftForOwner`. Every owner procedure resolves `@UserKey`
  internally; no client-supplied owner IDs.
- The legacy `usp_GetPeerSlateUserDashboard` remains in the allowlist and
  backs `/api/dashboard` — confirmed present and confirmed **not** a Home
  source per the gate contract.

### Capture (PS-CAPTURE-001/002) — released

- Owner-scoped create/list/correct/archive/restore/delete/export with
  row-version concurrency (`owner_routes.py:274-345, 773-964`);
  `dbo.captures` + `dbo.capture_revisions`
  (`SQL FIles/Migrations/proposed/PS-CAPTURE-001_captures.sql`,
  `PS-CAPTURE-002_capture_lifecycle.sql`).

### Voice Capture (PS-VOICE-001) — released

- Owner-only upload/transcribe/review/confirm/delete with private audio proxy
  setting `Cache-Control: private, no-store` (`owner_routes.py:346-511`);
  `services/voice_capture_service.py`, `services/media_storage_service.py`,
  `services/speech_transcription_service.py`.
- The accepted **Coming later** capability-preview pattern exists in
  production code: disabled + `aria-disabled` chips and marigold pills in
  `owner_capture.html:257-313` with `.owner-app__voice-soon`
  (`owner-app.css:701-710`). This is the authoritative precedent the Home
  previews restyle.

### Canonical Moment (PS-MOMENT-001) — released

- Proposal/save/confirm/discard against one pinned Capture revision;
  deleted-source tombstones; single-Moment review route
  (`owner_routes.py:512-772`); `dbo.moments`, `dbo.moment_versions`,
  `dbo.moment_sources` (`proposed/PS-MOMENT-001_moments.sql`).
- **No owner Moment list or "recent confirmed Moment" read procedure exists**
  — the Home read procedure supplies this.

### Placement (PS-PLACEMENT-001) — released

- Body-free exact-version references (`dbo.moment_placements`,
  `usp_CreateOrReactivateMomentPlacement`, `usp_ListMomentPlacementsForOwner`,
  `usp_RemoveMomentPlacement`); no route/UI consumer yet. Correct reference
  pattern for any future projection; not needed by the first Home slice.

### Platform schema foundations (PS-PLAT-001…008)

- `member_profiles`, `slate_entities`, `entity_access_grants`,
  `entity_publication_versions`, connection/block/consent/notification tables
  exist as foundations only — unchanged conclusion from the Codex inventory:
  presence is not viewer capability.

### Templates / CSS / JS conventions (full detail in `05_…`)

- One `base.html`; owner pages extend it; route-scoped CSS via `extra_head`
  and deferred IIFE JS via `extra_scripts`; `owner-app.css` is the
  Voice-owned owner stylesheet with `--pv-*` Deep Navy Gold tokens.

### Tests

- 494 tests pass at this base (1 environmental skip: the isolated
  PS-PLACEMENT-001 SQL-gate database is not configured on this machine).
- Relevant suites: `test_auth.py`, `test_identity.py`, `test_owner_capture.py`,
  `test_owner_moment.py`, `test_owner_settings.py`, `test_owner_voice_*.py`,
  `test_database_service.py`, `test_navigation.py`, plus guardrails
  `test_site_rules.py` and `test_governance_pointers.py`. **No
  `test_owner_home.py` exists** — the name is free for the backend package.

## 2. What can be reused for the first slice

| Need | Reused foundation |
|---|---|
| Owner resolution & redirect behavior | `get_current_identity()` + the `auth.owner_workspace` pattern |
| Capture action destination | Released `/app/capture` (Speak/Type) |
| Review-item sources (candidates for manager decision U6) | (a) pending unconfirmed private Moment proposals; (b) Voice drafts awaiting transcript review/save; (c) Voice drafts with failed transcription needing retry/delete — all real owner workflows in production today |
| Recent confirmed Moment | `dbo.moments`/`dbo.moment_versions` via a new bounded read procedure |
| Next-step derivation | Deterministic rules over the same three sources plus Capture availability |
| Coming-later preview semantics | Voice pattern (`owner_capture.html`), restyled to the accepted authority |
| Procedure allowlist mechanism | `ALLOWED_PROCEDURES` + one new `usp_` entry |
| Flag mechanism | `PEERSLATE_*` env → `app.config` convention |
| Migration/verification pattern | `SQL FIles/Migrations/proposed/PS-XXX_*.sql` + `_rollback.sql`; `SQL FIles/Verification/PS-XXX_owner_isolation_verify.sql` |
| `no-store` precedent | Voice audio proxy (`owner_routes.py:507`) |

## 3. What does not exist yet (first slice must create)

- The finite Home aggregation: `services/owner_home_service.py`, the
  `owner-home.v1` serializer, and one bounded owner read procedure
  (proposed `usp_GetOwnerHomeForOwner(@UserKey)`).
- `GET /api/v1/owner/home` and the flagged `/app` render integration.
- `templates/owner_home.html` + partials, `static/css/owner-home.css`,
  `static/js/owner-home.js`, Home imagery.
- `tests/test_owner_home.py`, `tests/test_owner_home_migration.py`,
  `tests/test_owner_home_accessibility.py`.
- A server-owned capability-availability registry for the dormant categories.

Still absent and still out of scope (unchanged from the Codex inventory):
viewer authorization/projection service, publication/grant/connection
lifecycles, governed insights, resurfacing policy, My Slate preview, route
map, audience-vocabulary migration.

## 4. Drift from the Codex planning assumptions

| ID | Codex assumption | Current-repository reality | Consequence |
|---|---|---|---|
| DR1 | `owner_routes.py` reserved for the `/app` data integration | `/app` HTML is `auth.owner_workspace` in `auth_routes.py:113` | Backend package needs `auth_routes.py` in its reservation for the flagged render integration (or moves the route with manager approval); recorded in the intersection register I2 |
| DR2 | Procedure name `sp_owner_home_get_v1(@user_key)` | Repository convention is `usp_*` + `ForOwner(@UserKey)`; allowlist regex requires the `usp_` prefix (`database_service.py:8`) | Rename to `usp_GetOwnerHomeForOwner(@UserKey)` (final name owned by the backend package) |
| DR3 | Migration path `SQL FIles/Migrations/PS-HOME-001_owner_home_reads.sql` | Feature migrations live in `SQL FIles/Migrations/proposed/` (Capture/Moment/Placement/Voice all do) | Use `SQL FIles/Migrations/proposed/PS-HOME-001_owner_home_reads.sql` + `_rollback.sql`; verification as `SQL FIles/Verification/PS-HOME-001_owner_isolation_verify.sql` |
| DR4 | Flag `PS_OWNER_HOME_ENABLED` | Config convention is `PEERSLATE_*` env → `app.config` | Recommend `PEERSLATE_OWNER_HOME_ENABLED`, default off |
| DR5 | Planning base `31864e4…`/`5cc5b69…` | Main advanced to `6d5ef46…`, adding the control-room slice (`control_room_routes.py`, `services/azure_devops_read.py`), the homepage Interview demo scene, the people-interests feed slice (`people_interests_api`, PS-PLAT-008), and Gate-2.4 evidence | None conflicts with the Home reservations; re-verified rather than assumed |
| DR6 | — | `owner_workspace.html:10` and `owner_settings.html:10` nest a second `<main id="main-content">` inside `base.html`'s main (duplicate ID) | Owner Home must not repeat the defect; noted as a frontend regression check |
| DR7 | Codex docs list Pete + "Danielle" founding-alpha validation | Unchanged expectation; two distinct real accounts remain required | Carried into the review charter |

## 5. Feasibility conclusion

The first owner-only finite Home slice is implementable on the current main
with **one additive read migration and no schema changes** to existing tables.
All gaps found are naming/placement alignments (DR1–DR4) or known template
defects (DR6), none architectural. The complete result is scored in
`08_FABLE_FEASIBILITY_MATRIX.md`.
