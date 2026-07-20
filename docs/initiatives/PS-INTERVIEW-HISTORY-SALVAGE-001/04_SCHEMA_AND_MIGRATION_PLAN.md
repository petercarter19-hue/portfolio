# 04 — Schema and migration work that would actually be required

Nothing described here has been written, applied, or reserved. This is what a
future writer would face, based on reading the real files on `origin/main` at
`531013dd8c1a05e2443becd881a226755f27ca14` rather than assuming the old
branch's premises still hold.

## Current schema reality — verified, not assumed

### Mandatory foundation

`scripts/apply_sql_migrations.py` treats these eight as required, in order:

`PS-PLAT-001`, `PS-PLAT-002`, `PS-PLAT-003`, `PS-PLAT-004`, `PS-PLAT-005`,
`PS-PLAT-006`, `PS-PLAT-007`, `PS-AUTH-001`.

`EXPECTED_MIGRATIONS` is derived from that tuple, and `verify_foundation()`
fails if any is missing. `EXPECTED_TABLES` lists 33 foundation tables;
`EXPECTED_PROGRAMMABLE_OBJECTS` lists six. None of them is interview-related.

### Package migrations — the current convention

Package migrations live in `SQL FIles/Migrations/proposed/` and are registered
in `APPROVED_OPTIONAL_MIGRATIONS`, each with a dedicated verifier under
`SQL FIles/Verification/`:

| Migration ID | Forward script | Verifier |
|---|---|---|
| `PS-CAPTURE-001` | `proposed/PS-CAPTURE-001_captures.sql` | `PS-CAPTURE-001_owner_isolation_verify.sql` |
| `PS-CAPTURE-002` | `proposed/PS-CAPTURE-002_capture_lifecycle.sql` | `PS-CAPTURE-002_lifecycle_verify.sql` |
| `PS-MOMENT-001` | `proposed/PS-MOMENT-001_moments.sql` | `PS-MOMENT-001_owner_isolation_verify.sql` |
| `PS-PLACEMENT-001` | `proposed/PS-PLACEMENT-001_moment_placements.sql` | `PS-PLACEMENT-001_owner_isolation_verify.sql` |
| `PS-VOICE-001` | `proposed/PS-VOICE-001_voice_capture.sql` | `PS-VOICE-001_owner_isolation_verify.sql` |
| `PS-CAPTURE-MEDIA-001` | `proposed/PS-CAPTURE-MEDIA-001_photo_sources.sql` | `PS-CAPTURE-MEDIA-001_owner_isolation_verify.sql` |
| `PS-HOME-001` | `proposed/PS-HOME-001_owner_home_reads.sql` | `PS-HOME-001_owner_isolation_verify.sql` |
| `PS-PLAT-008` | `proposed/PS-PLAT-008_people_interests_feed.sql` | — |

The old branch predates this split entirely. Its migration sits in the
top-level `Migrations/` directory and is registered as mandatory. That is
verdict **D-3** in `02_…` and must not be reproduced.

### Header convention every package migration follows

Read from `proposed/PS-MOMENT-001_moments.sql`:

- `SET NOCOUNT ON; SET XACT_ABORT ON;` then `BEGIN TRY / BEGIN TRANSACTION`.
- Throw if `dbo.schema_migrations` is missing.
- Throw a distinct numbered error per missing prerequisite migration
  (`PS-AUTH-001`, `PS-CAPTURE-001`, `PS-CAPTURE-002`, …).
- Throw if any required object is missing (`dbo.app_users`,
  `dbo.member_profiles`, `dbo.audit_events`, `dbo.usp_AppendAuditEvent`, …).
- Create objects only when `OBJECT_ID(...) IS NULL` — idempotent.
- Insert the ledger row and an audit event at the end.
- `BEGIN CATCH: IF XACT_STATE() <> 0 ROLLBACK TRANSACTION; THROW;`

The old branch's migration follows almost all of this correctly. Its only
prerequisite check is `PS-PLAT-007`; a current version would also require
`PS-AUTH-001` at minimum, and — depending on the C-1 decision — `PS-MOMENT-001`.

### Objects the old migration relies on that do exist today

Confirmed present in `SQL FIles/Migrations/PS-PLAT-002_profiles_entities_access.sql`
and the identity/governance migrations: `dbo.member_profiles`,
`dbo.slate_entities`, `dbo.app_users`, `dbo.audit_events`,
`dbo.content_approval_events`, `dbo.usp_AppendAuditEvent`,
`dbo.schema_migrations`.

So the old migration's dependencies are still satisfiable. Its problem is
placement, ID, and premises — not missing foundations.

## Two schema shapes, depending on the C-1 decision

### Shape A — standalone aggregate (closest to the old branch)

Six tables, essentially as inventoried in `01_…`. Changes required to make it
current:

1. Move to `SQL FIles/Migrations/proposed/`.
2. New migration ID (see below).
3. Add `PS-AUTH-001` to the prerequisite throws.
4. Add a per-package verifier at
   `SQL FIles/Verification/<ID>_owner_isolation_verify.sql` modelled on the
   Moment and Placement verifiers, proving two-owner isolation, permission
   filtering, version immutability, and synthetic rollback.
5. Register in `APPROVED_OPTIONAL_MIGRATIONS` and add a `*_VERIFY_PATH`
   constant — **not** in `MIGRATION_FILENAMES`, `EXPECTED_TABLES`, or
   `EXPECTED_PROGRAMMABLE_OBJECTS`.
6. Revert the `peerslate_platform_foundation_verify.sql` edits entirely.
7. Resolve C-2 before keeping the `content_approval_events` write.
8. Keep `UQ_member_profiles_id_user`. Note that it alters a **foundation
   table**, so it is a shared-object change requiring explicit manager
   awareness and a rollback path that does not break other packages' FKs. The
   old rollback drops it unconditionally, which would be wrong if another
   package later depends on it.

*Cost estimate:* roughly the size of PS-MOMENT-001 — six tables, one trigger,
fourteen procedures, a verifier, migration tests, service tests, route tests,
isolation proofs. Not small.

### Shape B — STAR elaboration attached to a confirmed Moment version

If Pete decides an interview story is a *projection over canonical Moments*:

| Table | Purpose |
|---|---|
| `dbo.interview_story_elaborations` | Owner-scoped STAR decomposition (`situation`, `responsibility`, `personal_actions`, `reasoning`, `results`, `reflection`, `competencies_json`), referencing one exact `dbo.moment_versions` row |
| `dbo.interview_story_elaboration_versions` | Immutable confirmed snapshots of the elaboration, same trigger pattern |
| `dbo.interview_answer_attempts` / `dbo.interview_answer_sources` | Unchanged from Shape A, but pinning the elaboration version |
| `dbo.interview_mode_changes` | Unchanged |

The independent `allowed_for_ai_grounding` permission (K-1) lives on the
elaboration, not on the Moment, so a member can confirm a Moment as accurate
without permitting AI to speak from it.

*Advantages:* one canonical truth per experience; reuses the released
exact-version pinning contract; four tables instead of six; no second
confirmation state machine over the same facts.

*Costs:* an interview story cannot exist without first being captured as a
Moment, which is a heavier member journey and constrains the "capture a story
in the middle of practice" interaction the old branch's dialog was built for. A
`PS-CAPTURE-001`/`PS-MOMENT-001` dependency chain becomes mandatory.

*Unresolved in Shape B:* whether `interview_story_capture_responses` (the
append-only per-field raw capture log) belongs to the elaboration or is
replaced by the existing Capture revision model.

## Migration ID

`PS-INTERVIEW-001` is discarded (D-4). Two candidates, neither reserved by this
document:

- `PS-INTERVIEW-HISTORY-001` — reads as what it is, and does not collide with
  the released `PS-INTERVIEW-002` / `PS-INTERVIEW-PUBLIC-GATE-001` UI packages.
- `PS-STORY-001` — shorter, but risks confusion with `PS-STORY-COMPOSER-001`
  and the Owner Story composition standard, which are a different product area.

Recommendation: `PS-INTERVIEW-HISTORY-001`. **Reserving it is a later decision
by a designated manager, not an act of this document.**

## Files a future writer would touch

Listed so a manager can reserve them. **None of these has been changed.**

```
SQL FIles/Migrations/proposed/PS-INTERVIEW-HISTORY-001_*.sql          (new)
SQL FIles/Migrations/proposed/PS-INTERVIEW-HISTORY-001_*_rollback.sql (new)
SQL FIles/Verification/PS-INTERVIEW-HISTORY-001_owner_isolation_verify.sql (new)
scripts/apply_sql_migrations.py        (optional-migration registration only)
services/database_service.py           (procedure allowlist only)
services/interview_story_service.py    (new)
owner_routes.py  OR  a new authenticated blueprint   (per 03 route decision)
app.py                                 (model-answer source-mode branch only)
tests/test_interview_history_migration.py   (new)
tests/test_interview_story_service.py       (new)
tests/test_database_service.py         (allowlist assertions only)
tests/test_interview_studio.py         (source-mode route tests only)
docs/initiatives/PS-INTERVIEW-HISTORY-SALVAGE-001/  (this package)
```

Shared-file contention to check before assigning: `app.py`,
`services/database_service.py`, and `scripts/apply_sql_migrations.py` are all
touched by other active lanes. `PS-HOME-INTERVIEW-PARITY-001` (active, Claude
Code) and the Photo dark-launch task (open) both have plausible claims on
`app.py`.

## Migration execution gates

Following the pattern every recent package used, and the rules in
`docs/AI_WORKFLOW.md`:

1. Repository code, migration scripts, and migration tests can be completed and
   reviewed **without touching any database**. That is where a first slice
   should stop.
2. Apply/verify/guarded-rollback/reapply must be proven on a real SQL Server in
   an **isolated database** before any production run.
3. The production migration runs through the configured secure connection path
   only. Credentials are never read, requested, copied, or transmitted by any
   agent; if a credential-only step is required, Pete performs it.
4. The verifier must prove two-owner isolation without reading or printing any
   member content — the standard PS-MOMENT-001 / PS-PLACEMENT-001 verifiers
   already demonstrate this and are the model to copy.
5. Rollback must refuse when member rows exist. The old branch's rollback does
   this correctly and that behavior should be preserved.

## What must NOT change

- `MIGRATION_FILENAMES`, `EXPECTED_MIGRATIONS`, `EXPECTED_TABLES`, and
  `EXPECTED_PROGRAMMABLE_OBJECTS` in `scripts/apply_sql_migrations.py`.
- `SQL FIles/Verification/peerslate_platform_foundation_verify.sql`.
- Any released procedure, table, or contract from PS-CAPTURE-001/002,
  PS-MOMENT-001, PS-PLACEMENT-001, PS-VOICE-001, PS-CAPTURE-MEDIA-001, or
  PS-HOME-001.
- The public Interview Studio's rendered output, while the flag is off.
