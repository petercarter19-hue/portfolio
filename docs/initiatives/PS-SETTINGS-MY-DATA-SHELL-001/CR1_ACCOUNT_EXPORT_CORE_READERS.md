# CR1 account export core readers

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001`
**Slice:** Protected, replacement package 1 of the 2026-08-29 reader topology,
after `PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-READERS-001` (all 13 C0 domains at
once) failed independent pre-activation review.
**Depends on:** the lane claim's own enumerated contract
(`docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001.json`);
reads `C0_ACCOUNT_EXPORT_ARCHITECTURE.md`'s V1 domain matrix as the allowlist
bible for the one row this package builds and for the truthful reasons every
other row is recorded with.
**Status:** Candidate migration/rollback/verification/adapter/test files,
self-reviewed by the writer. **Nothing in this package runs in production. No
schema apply has been performed anywhere except by the manager's own future
gate. No account export exists, is available, or is usable by any member
today.**

## Decision

Exactly three domains, this package's entire enumerated scope: the member's
own `dbo.app_users` row, the member's own active `dbo.member_profiles` row,
and the eight PS-PLAT-006 Living Resume tables (one reader per table, never
folded together). Ten procedures total, each with a paired Python adapter
function in `services/account_export_domain_readers.py`. Every other C0 V1
domain-matrix row — including `dbo.career_skill_links`, a Living Resume table
this package deliberately does not read — gets an explicit, truthful
`disposition` and `reason` in the same `DOMAINS` registry, so a future reader
of that dict never has to guess whether an absence is deliberate or a bug.

This package creates no table, no trigger, no index, no container, no worker,
no route, and no UI. It does not populate `dbo.account_export_job_domains`
(C1's still-empty child ledger) or wire any reader into a worker.

## What this package corrects from the paused DOMAIN-READERS-001 branch

Read as non-authoritative research only (`git show ecfa4754:<path>`, branch
`work/2026-08-29-settings-account-export-domain-readers-001`, tip `ecfa4754`,
never merged, never a build dependency of this package). Its C1-style
procedure mechanics were sound and are reused: identity resolution, dynamic-SQL
`CREATE OR ALTER PROCEDURE` wrapping, and one-procedure-per-table splitting
(T-SQL's `INSERT ... EXEC` requires every result set a target procedure
returns to be compatible with the capturing table's columns, not merely the
first one — the exact trap that package's own header comment records having
hit, and `PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql`'s "Correction
round" independently hit the sibling failure mode).

Its scope and some inclusions were not sound, against **this package's own**
enumerated contract:

- Its account reader selected `app_user.active`. This package's contract
  forbids `active` by name — the reader precondition already requires an
  active account to resolve identity at all, so echoing it back adds nothing
  and widens the output beyond the enumerated allowlist.
- Its profile reader selected `profile.profile_key` and `profile.active`.
  This package's contract forbids both: `profile_key` is an opaque internal
  identifier never disclosed as an export field (the export links Living
  Resume rows to their parent chapter via `chapter_key`, never via a
  member-identity key), and `active` is again an implied precondition.
- Its Living Resume coverage collapsed `career_experiences`,
  `career_education`, `career_credentials`, and `career_projects` into inline
  joined columns on a single "chapter" reader, and never built a standalone
  reader for any of the four. This package's contract requires one reader per
  PS-PLAT-006 table — eight readers, not four with four tables silently
  folded in.

This package builds fresh and narrower: exactly the columns and readers the
lane claim's own contract enumerates, verified against the actual applied
PS-PLAT-000/002/006 schema before a single `INSERT` or `SELECT` was written.

## Shared contract every one of the ten procedures follows

- Accepts **only** `@UserKey nvarchar(300)`. No owner id, table name, or
  dynamic SQL built from any argument. Pinned by
  `tests/test_settings_export_core_readers.py`'s exact-signature assertion.
- Resolves identity with a byte-identical header across all ten (pinned by
  test): `@UserKey` -> an **active** `dbo.app_users` row -> its **active**
  `dbo.member_profiles` row, exactly like `PS-SETTINGS-EXPORT-001`'s owner
  procedures. An unresolved identity `RETURN`s before any `SELECT` — no
  result set at all, which the calling adapter treats as zero rows, never an
  error.
- Filters every row by the resolved owner: `id = @UserId` for the account
  reader (the only reader keyed directly off `app_users`, never a profile);
  `profile_id = @ProfileId` for the profile reader; `owner_profile_id =
  @ProfileId` for every Living Resume reader. A reader that joins
  `dbo.career_chapters` for parent linkage repeats the owner predicate on
  **both** the child and the parent table — defense in depth beyond the
  composite foreign key that already ties them to the same
  `owner_profile_id`.
- Returns **only** an explicit, hand-picked column list — never `SELECT *` —
  with a deterministic `ORDER BY` (`display_order` then `created_at_utc` then
  the table's own, or a chapter-less subtype table's borrowed, opaque key).
- Contains **no transaction control of any kind** (no `BEGIN TRANSACTION`,
  `COMMIT`, `ROLLBACK`, `TRY`/`CATCH`), no write, and no nested `EXEC`/dynamic
  SQL. A structural, not merely behavioural, guarantee: a procedure that can
  never reach `ROLLBACK` can never trip T-SQL's "Cannot use the ROLLBACK
  statement within an INSERT-EXEC statement" refusal, which is exactly why
  every one is genuinely "INSERT-EXEC-safe by construction." Proven three
  ways: a structural grep loop in
  `PS-SETTINGS-EXPORT-003_core_reader_isolation_verify.sql`'s section 0
  (checked against the live `OBJECT_DEFINITION()` of every procedure), a
  static text assertion in `tests/test_settings_export_core_readers.py`, and
  by construction (every body is one identity-resolution `SELECT` plus one
  content `SELECT`, confirmed by an exact `SELECT`-keyword count).
- Every internal integer identity column is replaced in the output by the
  row's own opaque `*_key uniqueidentifier` where the source table has one; a
  chapter-subtype table with no key of its own (`career_experiences`,
  `career_education`, `career_credentials`, `career_projects`, all keyed
  1:1 by `chapter_id`) exposes only the joined parent `chapter_key`, which is
  sufficient for intra-export linkage since the row is already 1:1 with that
  chapter.
- Excludes soft-deleted rows: `deleted_at_utc IS NULL` on its own column
  where the table has one (`career_chapters`, `career_achievements`,
  `career_skills`), **and**, for every reader that joins `career_chapters`
  for parent linkage, `chapter.deleted_at_utc IS NULL` as well — a
  deliberate widening beyond the literal "every table that has the column"
  instruction, recorded here as this package's one contract interpretation
  (see "Interpretation notes" below).
- Never selects `row_version` anywhere. It is not named in any per-table
  forbidden list, but it is also not member-authored content and not a
  stable cross-file linkage identifier (it changes on every row update) —
  excluded by the same closed-allowlist logic that already excludes every
  column not explicitly enumerated in the lane claim's contract.

## Read-window mechanism

The lane claim's outcome requires "a read window (`SYSUTCDATETIME()` captured
at start and end, returned as columns or a second result set — follow the
C1-foundation style you judge cleanest, document the choice)." This package
chose **columns on the single content result set** —
`@ReadStartedAtUtc AS read_started_at_utc` (captured once, at the top of the
procedure, before identity resolution) and `SYSUTCDATETIME() AS
read_ended_at_utc` (evaluated inline in the same content `SELECT`) — over
both alternatives the claim names, for concrete, testable reasons:

- **Why not OUTPUT parameters** (a third option the claim does not name but
  this package considered): they would add a second and third declared
  parameter to every procedure, which directly violates the pinned
  "`@UserKey`-only signatures" test requirement.
- **Why not a genuinely separate second result set**: Microsoft's own INSERT
  (Transact-SQL) reference is explicit — "If `execute_statement` is used with
  INSERT, each result set must be compatible with the columns in the table."
  Not merely the first one. A window result set of a different shape
  (two `datetime2(7)` columns vs. the content columns) would make every one
  of these procedures **unsafe** to call with `INSERT ... EXEC` for any
  caller wanting the content — directly contradicting the lane claim's own
  "INSERT-EXEC-safe by construction" requirement. This is exactly the trap
  the paused DOMAIN-READERS-001 package's own header comment records having
  hit for the same reason (motivating its one-procedure-per-table split in
  the first place).
- **The accepted cost**: columns-on-the-content-row means the read window is
  present only when at least one content row comes back; a legitimate
  zero-row result (a member with no `career_skills`, or an unresolved
  identity) carries no SQL-sourced window. `services/account_export_domain_readers.py`'s
  `_call_reader` independently brackets every call with a
  `SELECT SYSUTCDATETIME()` on the same connection (the same idiom
  `scripts/run_account_export_worker.py`'s `read_consistency_marker` already
  uses for `@@DBTS`) as the documented fallback for exactly that case, and
  prefers the SQL-embedded window (tighter — it brackets only the actual
  table read, not the round trip to get there) whenever a row exists.

`services/account_export_domain_readers.py`'s `_call_reader` returns
`{"rows": [...], "read_started_at_utc": ..., "read_ended_at_utc": ...}` for
every call; the two window fields are popped off each decoded row (they would
otherwise repeat identically on every row of a multi-row reader) and surfaced
once at the top level.

## Domain-by-domain contract

### `account` — included

| Reader | Source table (applied migration) | Fields (allowlisted, 9) |
| --- | --- | --- |
| `usp_ReadAccountExportAccountForOwner` | `dbo.app_users` (`PS-PLAT-000`) | `display_name`, `email`, `auth_provider`, `profile_image_url`, `timezone_name`, `user_role`, `created_at_utc`, `last_seen_at_utc`, `updated_at_utc` |

**Ordering:** `app_user.id` (exactly one row possible; still explicit per the
lane claim's "deterministic ORDER BY per table").

**Redaction (forbidden by name, per the lane claim's canary):** `id` (internal
identity), `user_key` (the same value the caller already authenticated with —
never echoed back as content), `auth_subject` (credential-adjacent — the raw
external-provider subject identifier), `active` (implied by the reader's own
precondition). Also excluded, not named by the claim but outside its exact
INCLUDE list: `account_key`, `auth_issuer`, `account_status`,
`onboarding_status` (all added by `PS-AUTH-001`) — the allowlist is closed;
nothing outside the nine named fields is selected.

### `profile` — included

| Reader | Source table (applied migration) | Fields (allowlisted, 8) |
| --- | --- | --- |
| `usp_ReadAccountExportProfileForOwner` | `dbo.member_profiles` (`PS-PLAT-002`) | `profile_slug`, `display_name`, `headline`, `bio`, `location_text`, `visibility`, `created_at_utc`, `updated_at_utc` |

**Ordering:** `profile.profile_id` (exactly one row possible; explicit for
the same reason as above).

**Redaction (forbidden by name):** `profile_id`, `profile_key`, `user_id`,
`active`, `row_version`.

### `living_resume` — included (one reader per PS-PLAT-006 table, 8 readers)

| Reader | Source table(s) (applied migration) | Fields (allowlisted, content only — 2 read-window columns on every reader are additional and not part of this count) |
| --- | --- | --- |
| `usp_ReadAccountExportCareerChapterForOwner` | `dbo.career_chapters` (`PS-PLAT-006`) | 19: `chapter_key`, `chapter_type`, `title`, `organization_name`, `location_text`, `summary`, `original_member_wording`, `approved_wording`, `start_date`, `end_date`, `date_precision`, `visibility`, `approval_status`, `publication_status`, `featured`, `display_order`, `approved_at_utc`, `created_at_utc`, `updated_at_utc` |
| `usp_ReadAccountExportCareerExperienceForOwner` | `dbo.career_experiences` joined to `dbo.career_chapters` on `chapter_id` (`PS-PLAT-006`) | 5: `chapter_key` (parent linkage), `role_title`, `employer_name`, `employment_type`, `current_role` |
| `usp_ReadAccountExportCareerEducationForOwner` | `dbo.career_education` joined to `dbo.career_chapters` (`PS-PLAT-006`) | 6: `chapter_key`, `institution_name`, `degree_name`, `field_of_study`, `education_status`, `grade_text` |
| `usp_ReadAccountExportCareerCredentialForOwner` | `dbo.career_credentials` joined to `dbo.career_chapters` (`PS-PLAT-006`) | 7: `chapter_key`, `credential_name`, `issuer_name`, `credential_identifier`, `issue_date`, `expiration_date`, `verification_url` |
| `usp_ReadAccountExportCareerProjectForOwner` | `dbo.career_projects` joined to `dbo.career_chapters` (`PS-PLAT-006`) | 5: `chapter_key`, `project_name`, `project_role`, `project_status`, `project_url` |
| `usp_ReadAccountExportCareerAchievementForOwner` | `dbo.career_achievements` joined to `dbo.career_chapters` on `chapter_id` (`PS-PLAT-006`) | 13: `achievement_key`, `chapter_key`, `original_member_wording`, `approved_wording`, `metric_value`, `metric_label`, `visibility`, `approval_status`, `featured`, `display_order`, `approved_at_utc`, `created_at_utc`, `updated_at_utc` |
| `usp_ReadAccountExportCareerSkillForOwner` | `dbo.career_skills` (`PS-PLAT-006`, no `chapter_id` column — no parent join) | 9: `skill_key`, `skill_name`, `skill_summary`, `visibility`, `approval_status`, `featured`, `display_order`, `created_at_utc`, `updated_at_utc` |
| `usp_ReadAccountExportCareerTimelineEventForOwner` | `dbo.career_timeline_events` joined to `dbo.career_chapters` on `chapter_id` (`PS-PLAT-006`) | 13: `timeline_event_key`, `chapter_key`, `event_label`, `event_type`, `start_date`, `end_date`, `date_precision`, `visibility`, `approval_status`, `constellation_featured`, `display_order`, `created_at_utc`, `updated_at_utc` |

**Ordering:** every reader orders by `display_order` then `created_at_utc`
then the row's own (or, for the four chapter-subtype tables with no ordering
column of their own, the joined chapter's) `display_order`/`created_at_utc`,
then the opaque key, as a final deterministic tiebreaker.

**Redaction (forbidden by name, applied uniformly across all eight):** every
internal integer id — `chapter_id`, `entity_id`, `achievement_id`, `skill_id`,
`timeline_event_id`, and every `*_id` surrogate column including
`owner_profile_id` itself (never selected as output on any reader; used only
as a `WHERE`/`JOIN` predicate) — `created_by_user_id`, `approved_by_user_id`,
and `deleted_at_utc` (used only as a predicate, per "soft-delete predicate
presence" below, never selected).

`chapter_type` (on the chapter reader) and `event_type` (on the timeline
event reader) are included as content, not merely a joined predicate: without
it, `title`/`organization_name` (chapter) or `event_label` (timeline event)
would be ambiguous — the member chose this categorical value when authoring
the record, so it is member-authored content by the same logic that includes
`visibility`/`approval_status`. This is this package's second contract
interpretation (see below).

**`career_skill_links` — deliberately not read.** Its rows reference
`evidence_item_id`, whose disclosure rules (which `evidence_items` fields, if
any, are safe to export) are undecided. Recorded in
`services/account_export_domain_readers.py`'s `DOMAINS` registry as its own
`"excluded"` entry — not silently folded into `living_resume` and not
omitted — deferred to a future, separately claimed evidence-decision package.

## Every other C0 domain

Recorded in `DOMAINS` with a truthful `disposition` (`"excluded"` for a
future, separately claimed reader this package does not build; `"unavailable"`
for a domain whose source schema is not yet applied or that is structurally
unavailable to a server-side export — never guessed) and a `reason` drawn
from `C0_ACCOUNT_EXPORT_ARCHITECTURE.md`'s own "V1 domain matrix" and
"Required truth boundary" text: `profile_publication_foundation`,
`own_publication_versions`, `capture`, `voice_photo`, `moment`, `journal`,
`workshop_my_knowledge`, `opportunity_slate`, `my_opportunities`,
`community_authored_content`, `connection_preferences`, `connection_records`,
`notifications_inbox`, `notification_preferences`, `consent_history`,
`audit_events`, `browser_local_interview_history`, `interview_telemetry`,
`ai_proposals`, `ask_pete_public`, `ask_pete_direct`, `projects`, `home`,
`file_evidence_metadata`, `indexes_caches_provider_backups`. `projects` notes
that career-project records are already covered by `living_resume`'s
`career_project` reader (`chapter_type = 'project'`); every other entry
builds no reader here.

## Interpretation notes

Recorded because the contract left these to judgment, not because either is a
defect:

1. **Joined-chapter soft-delete widening.** The lane claim's soft-delete rule
   reads "`WHERE deleted_at_utc IS NULL` predicate on every table that has
   the column" — literally, a per-table rule keyed on column presence. Five
   of the eight Living Resume tables (`career_experiences`, `career_education`,
   `career_credentials`, `career_projects`, `career_timeline_events`) have no
   `deleted_at_utc` column of their own; their only lifecycle signal is their
   parent chapter's. Filtering only by column presence would let a row whose
   parent chapter was soft-deleted leak through its child/joined reader. This
   package instead applies `chapter.deleted_at_utc IS NULL` on **every**
   reader that joins `career_chapters` for parent linkage, regardless of
   whether the joined-from table has its own `deleted_at_utc` column
   (`career_achievements` gets both: its own **and** the joined chapter's).
   Proven at the data level in
   `PS-SETTINGS-EXPORT-003_core_reader_isolation_verify.sql` section 4: a
   soft-deleted chapter removes both itself and its joined `career_projects`
   row.
2. **`chapter_type`/`event_type` included as content**, not treated as a pure
   structural/predicate field, for the reason given in the `living_resume`
   section above.

## Grant model

Identical to `PS-SETTINGS-EXPORT-001` and the paused DOMAIN-READERS-001
package: the governed apply identity holds `db_ddladmin` only and cannot
`GRANT EXECUTE`; no `GRANT`, `CREATE ROLE`, `CREATE USER`, or
`sp_addrolemember` statement appears anywhere in this migration. The intended
production grant — `EXECUTE` on these ten procedures for the existing
web-app principal role — is a separate, later, administrator-run authority
operation, not created here and not authorized by a repository merge of this
file.
