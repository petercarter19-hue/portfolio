# CR2 account export Capture/Moment readers

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-CAPTURE-MOMENT-READERS-001`
**Slice:** Protected, replacement package 2 of the 2026-08-29 reader
topology, after `PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001` (replacement
package 1) was independently reviewed and merged at main `cc5174da`.
**Depends on:** the lane claim's own enumerated contract
(`docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-CAPTURE-MOMENT-READERS-001.json`);
reads `C0_ACCOUNT_EXPORT_ARCHITECTURE.md`'s V1 domain matrix ("Capture/
revisions" and "Moments/versions/sources/placements" rows) as the allowlist
bible; reads `CR1_ACCOUNT_EXPORT_CORE_READERS.md` and
`PS-SETTINGS-EXPORT-003_core_readers.sql` as the structural template this
package follows closely.
**Status:** Candidate migration/rollback/verification/adapter/test files,
self-reviewed by the writer. **Nothing in this package runs in production.
No schema apply has been performed anywhere except by the manager's own
future gate. No account export exists, is available, or is usable by any
member today.**

## Decision

Six tables, text truth only, one reader per table: `dbo.captures`,
`dbo.capture_revisions`, `dbo.moments`, `dbo.moment_versions`,
`dbo.moment_sources`, and `dbo.moment_placements`. All six are applied in
production per `docs/governance/PRODUCTION_SCHEMA_STATE.md` (rows 10-13,
applied 2026-07-17 through 2026-07-19) despite living under
`SQL FIles/Migrations/proposed/` and carrying `gate: null` in the registry
-- gated-ness and applied-ness are different facts (see "A factual
correction" below). Six procedures total, each with a paired Python adapter
function in `services/account_export_domain_readers.py`, grouped into two
`DOMAINS` entries matching the C0 matrix's own two-row grouping: `capture`
(2 readers) and `moment` (4 readers).

This package creates no table, no trigger, no index, no container, no
worker, no route, and no UI. It does not populate
`dbo.account_export_job_domains` or wire any reader into a worker.

## A factual correction this package makes in passing

`services/account_export_domain_readers.py`'s prior `capture`/`moment`/
`voice_photo` entries all claimed their source schema was "not gated/
applied." That conflated two different facts: `gate: null` in
`SQL FIles/Migrations/registry.json` means no disposable-database rehearsal
proof has been recorded for that migration under this repository's gate
discipline (introduced 2026-08-04); it says nothing about whether a real
database carries the migration, which `PRODUCTION_SCHEMA_STATE.md` alone
records. All four of `PS-CAPTURE-001`, `PS-CAPTURE-002`, `PS-MOMENT-001`,
and `PS-PLACEMENT-001` (and, for that matter, `PS-VOICE-001`/
`PS-CAPTURE-MEDIA-001`) are applied, `gate: null` notwithstanding -- they
predate the gate discipline. This package corrects `capture` and `moment`
by construction (flipping them to `included`) and corrects `voice_photo`'s
disposition from `unavailable` to `excluded` with a truthful reason, since
leaving a known-false "schema not applied" claim beside two just-corrected
entries in the same file would be internally inconsistent. See
`CR2_OWNER_TECHNICAL_COMPLETION_REPORT.md`'s "Deviations" section for the
scope reasoning behind touching `voice_photo` at all.

## Shared contract every one of the six procedures follows

- Accepts **only** `@UserKey nvarchar(300)`. No owner id, table name, or
  dynamic SQL built from any argument. Pinned by
  `tests/test_settings_export_capture_moment_readers.py`'s exact-signature
  assertion.
- Resolves identity with the **byte-identical** header
  `PS-SETTINGS-EXPORT-003` itself uses (pinned by test, same literal
  constant): `@UserKey` -> an **active** `dbo.app_users` row -> its
  **active** `dbo.member_profiles` row. An unresolved identity `RETURN`s
  before any `SELECT` -- no result set at all, which the calling adapter
  treats as zero rows, never an error.
- Filters every row by the resolved owner profile, with two different
  shapes depending on what the source table actually carries:
  - `dbo.moment_sources` and `dbo.moment_placements` each carry their own
    `owner_profile_id` column, so the join to `dbo.moments` **also**
    independently asserts the parent's `owner_profile_id` against
    `@ProfileId` -- the "owner predicate on both sides" defense in depth
    `PS-SETTINGS-EXPORT-003`'s own independent review added (its
    correction round, finding 3), applied here **from the start**.
  - `dbo.capture_revisions` and `dbo.moment_versions` carry **no**
    `owner_profile_id` column of their own -- only a bare `capture_id` /
    `moment_id` foreign key to their parent. Ownership is asserted exactly
    once, through the joined parent (`capture.owner_profile_id =
    @ProfileId` / `moment.owner_profile_id = @ProfileId`). This is not an
    incomplete application of the "both sides" pattern; it is the only
    predicate the schema has a column for. `PS-SETTINGS-EXPORT-003` never
    faced this shape -- every one of its Living Resume child tables
    carries its own `owner_profile_id` -- so this package's contribution
    is recognizing where the pattern legitimately cannot apply, not
    weakening it.
- Every internal integer id is replaced in the output by the row's own
  opaque `*_key uniqueidentifier`, plus the parent's opaque key
  (`capture_key` / `moment_key`) for intra-export linkage wherever the
  table carries a parent id, resolved through the same owner-predicated
  join. `dbo.moment_sources` additionally carries its own
  `source_capture_key` and nullable `source_revision_key`: opaque,
  strictly-intra-export linkage to the exact `dbo.captures` /
  `dbo.capture_revisions` row a Moment was sourced from.
- **`dbo.moment_placements.target_entity_id` is deliberately excluded** --
  unlike every other parent-id column here, it is a foreign key to
  `dbo.slate_entities` (the Opportunity Slate destination), which is not
  one of this package's six claimed tables. Opportunity Slate is its own,
  separate C0 V1-matrix row with its own future, separately claimed
  reader. This migration adds no dependency on `PS-PLAT-002`/`PS-PLAT-005`
  (which together create `dbo.slate_entities`) precisely because it never
  reads that table. The placement row still exports its own lifecycle
  facts (status, `moment_version_number`, every timestamp) through its
  `dbo.moments` parent link; only the cross-domain destination identity is
  deferred. See "Interpretation notes" below.
- Returns **only** an explicit, hand-picked column list -- never
  `SELECT *` -- with a deterministic `ORDER BY` (see the per-table
  "Ordering" note below; the exact column depends on whether the table has
  a per-parent sequence number or its own creation timeline).
- Contains **no transaction control of any kind**, no write, and no nested
  `EXEC`/dynamic SQL -- identical structural guarantee to
  `PS-SETTINGS-EXPORT-003`, proven the same three ways (a structural grep
  loop in the paired verification script, a static text assertion in the
  test file, and by construction: exactly two `SELECT` keywords per body).
- Returns the read window as two trailing columns on the single content
  result set -- identical mechanism to `PS-SETTINGS-EXPORT-003`; see that
  package's own `CR1_ACCOUNT_EXPORT_CORE_READERS.md` "Read window
  mechanism" section for the full Microsoft-documentation-backed rationale
  (OUTPUT parameters would violate the `@UserKey`-only signature; a second
  result set would break `INSERT ... EXEC`). Not re-litigated here since
  nothing about it changed.
- Never selects `row_version`, any `created_by`/`approved_by`/
  `confirmed_by`/`reactivated_by`/`removed_by`/`saved_by`/`corrected_by`
  user id, or any column carrying its **own** row's soft-delete state
  (used only as a `WHERE` predicate where the table has one, never
  selected).

## Domain-by-domain contract

### `capture` -- included (2 readers)

#### `dbo.captures` -> `usp_ReadAccountExportCaptureForOwner`

**Source:** `dbo.captures`, created by `PS-CAPTURE-001`
(`SQL FIles/Migrations/proposed/PS-CAPTURE-001_captures.sql`).

**Allowlist (7 content fields):** `capture_key`, `capture_type`, `body`,
`visibility`, `status`, `created_at_utc`, `updated_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `capture_id` | Internal integer surrogate; never disclosed. |
| `owner_profile_id` | Internal id, used only as the `WHERE` predicate. |
| `active` | Redundant encoding of `status` (the schema ties `active=1 <-> status='captured'`, `active=0 <-> status='archived'` via app-level invariant, though the `CHECK` constraint itself does not enforce every direction). This reader does not gate row presence on it -- only `deleted_at_utc IS NULL` does -- so an archived capture (`status='archived'`, `active=0`) still appears, matching the same "implied precondition, not independently informative" reasoning `PS-SETTINGS-EXPORT-003` applied to `app_user.active`/`profile.active`. |
| `deleted_at_utc` | Soft-delete column; used as the `WHERE capture.deleted_at_utc IS NULL` predicate, never selected. |
| `row_version` | Not member-authored content; changes on every update, so it is not a stable cross-file linkage identifier either. |

**Joins:** none.

**Ordering:** `capture.created_at_utc, capture.capture_key` (no parent, no
per-parent sequence column; the row's own creation timeline plus its own
key as a deterministic tiebreak).

**Read window:** trailing `read_started_at_utc`/`read_ended_at_utc`
columns, per the shared contract.

**Note on `status`/`visibility`:** both are included as "types/statuses"
and "visibility/audience facts" per the lane claim's own allowlist
categories. `visibility` currently only ever holds `'private'` in
practice (nothing in `PS-CAPTURE-001`/`PS-CAPTURE-002` sets another value),
but the `CHECK` constraint allows `'shared'`/`'connections'`/`'recruiter'`/
`'public'`, and an owner's own export must report the real column value,
not assume it is always private. `status` similarly allows a currently-
unreachable `'placed'` value (no procedure in `PS-CAPTURE-001`/
`PS-CAPTURE-002` sets it); this reader does not special-case it -- any
`status` the schema allows is real, undeleted, member-owned content.

#### `dbo.capture_revisions` -> `usp_ReadAccountExportCaptureRevisionForOwner`

**Source:** `dbo.capture_revisions`, created by `PS-CAPTURE-002`
(`SQL FIles/Migrations/proposed/PS-CAPTURE-002_capture_lifecycle.sql`).

**Allowlist (6 content fields):** `revision_key`, `capture_key` (parent
linkage), `revision_number`, `body`, `correction_note`, `corrected_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `revision_id` | Internal integer surrogate. |
| `capture_id` | Internal FK id; replaced in the output by the joined `capture.capture_key`. |
| `corrected_by_user_id` | A "created-by"-class user id (who made this correction); excluded by the same hard-exclusion class as every other `*_by_user_id` column in this package. |
| `row_version` | Same reasoning as `dbo.captures.row_version`. |

**Joins:** `JOIN dbo.captures AS capture ON capture.capture_id =
revision.capture_id` -- single-sided owner predicate
(`capture.owner_profile_id = @ProfileId`) because `dbo.capture_revisions`
carries no `owner_profile_id` column of its own to double against; the
parent join is the only column that exists to check. The same join also
carries the parent's own soft-delete predicate
(`capture.deleted_at_utc IS NULL`): a capture's revisions must not survive
their parent's soft-delete, even though `dbo.capture_revisions` itself has
no `deleted_at_utc` column of its own to filter on.

**Ordering:** `capture.created_at_utc, capture.capture_key,
revision.revision_number` -- `revision_number` is only unique **within**
one capture (`UQ_capture_revisions_capture_number UNIQUE (capture_id,
revision_number)`), so a flat reader over every capture's revisions must
group by the parent first (by the parent's own creation timeline and key)
before ordering by the child's per-parent sequence number, or revisions
from different captures sharing the same `revision_number` would interleave
without a stable order.

**Read window:** trailing columns, per the shared contract.

### `voice_photo` -- excluded (not built by this package)

Corrected from `unavailable` to `excluded`; see "A factual correction"
above. `dbo.captures`/`dbo.capture_revisions` themselves have no media,
transcript, hash, or checksum column of any kind, so this package's own
readers never had a media column to exclude from a row -- the boundary is
recorded because it governs the *domain's* future scope (a dedicated
Voice/Photo reader package), not because a `capture`/`capture_revision` row
here was incomplete for lack of one.

### `moment` -- included (4 readers)

#### `dbo.moments` -> `usp_ReadAccountExportMomentForOwner`

**Source:** `dbo.moments`, created by `PS-MOMENT-001`
(`SQL FIles/Migrations/proposed/PS-MOMENT-001_moments.sql`).

**Allowlist (8 content fields):** `moment_key`, `visibility`, `status`,
`current_version_number`, `confirmed_version_number`, `confirmed_at_utc`,
`created_at_utc`, `updated_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `moment_id` | Internal integer surrogate. |
| `owner_profile_id` | Internal id, used only as the `WHERE` predicate. |
| `confirmed_by_user_id` | An "approved-by"-class user id (who confirmed this Moment); excluded by the hard-exclusion class covering `created_by`/`approved_by`-shaped columns. |
| `row_version` | Same reasoning as above. |

**Forward-looking note (independent-review finding, recorded for a future
applier):** `PS-JOURNAL-001` — registered but NOT applied in production —
would add `archived_at_utc`/`archived_by_user_id` to `dbo.moments`. This
explicit allowlist would silently omit that archived-state text-truth fact
(nothing would leak — the reader never uses `SELECT *`), so whichever
package ever applies `PS-JOURNAL-001` must revisit this allowlist in the
same motion.

**Joins:** none.

**Ordering:** `moment.created_at_utc, moment.moment_key` (no parent, no
`display_order` column on this table).

**Read window:** trailing columns, per the shared contract.

**Note on soft-delete:** `dbo.moments` has **no** `deleted_at_utc` column.
Discarding a Moment proposal (`usp_DiscardMomentProposal`) is a real
`DELETE` of the row (and its `moment_versions`/`moment_sources` children),
not a soft-delete flag, so there is no predicate to add here. A confirmed
Moment is never deleted by any procedure in `PS-MOMENT-001`/
`PS-PLACEMENT-001`.

#### `dbo.moment_versions` -> `usp_ReadAccountExportMomentVersionForOwner`

**Source:** `dbo.moment_versions`, created by `PS-MOMENT-001`.

**Allowlist (10 content fields):** `moment_version_key`, `moment_key`
(parent linkage), `version_number`, `moment_kind`, `title`, `occurred_on`,
`occurred_precision`, `narrative`, `why_it_matters`, `saved_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `moment_version_id` | Internal integer surrogate. |
| `moment_id` | Internal FK id; replaced by the joined `moment.moment_key`. |
| `saved_by_user_id` | A "created-by"-class user id; excluded. |
| `row_version` | Same reasoning as above. |

**Joins:** `JOIN dbo.moments AS moment ON moment.moment_id =
moment_version.moment_id` -- single-sided owner predicate, for the same
structural reason as `dbo.capture_revisions` (`dbo.moment_versions` has no
`owner_profile_id` column of its own).

**Ordering:** `moment.created_at_utc, moment.moment_key,
moment_version.version_number` -- `version_number` is only unique within
one Moment (`UQ_moment_versions_number UNIQUE (moment_id,
version_number)`), so the same parent-then-sequence grouping applies as for
`dbo.capture_revisions`.

**Read window:** trailing columns, per the shared contract. A blank
proposal version (title/narrative/why_it_matters/occurred_on all `NULL`,
`occurred_precision = 'unknown'`) is a legitimate, fully-supported reader
output, not an error case -- proven by the verification script's fixture.

#### `dbo.moment_sources` -> `usp_ReadAccountExportMomentSourceForOwner`

**Source:** `dbo.moment_sources`, created by `PS-MOMENT-001`.

**Allowlist (8 content fields):** `moment_source_key`, `moment_key`
(parent linkage), `source_capture_key`, `source_revision_key`,
`source_revision_number`, `source_state`, `source_deleted_at_utc`,
`created_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `moment_source_id` | Internal integer surrogate. |
| `moment_id` | Internal FK id; replaced by the joined `moment.moment_key`. |
| `owner_profile_id` | Internal id; used as one half of the "both sides" `WHERE` predicate, never selected. |
| `capture_id` | Internal FK id; superseded by the opaque `source_capture_key`, which is already present on this table (no join to `dbo.captures` needed to obtain it). |
| `capture_revision_id` | Internal FK id; superseded by the opaque `source_revision_key`, already present on this table. |
| `row_version` | Same reasoning as above. |

**Joins:** `JOIN dbo.moments AS moment ON moment.moment_id =
moment_source.moment_id` -- **both-sided** owner predicate
(`moment_source.owner_profile_id = @ProfileId AND moment.owner_profile_id
= @ProfileId`), because `dbo.moment_sources` carries its own
`owner_profile_id` column.

**Ordering:** `moment_source.created_at_utc,
moment_source.moment_source_key` -- this table is 1:1 with its Moment
(`UQ_moment_sources_moment UNIQUE (moment_id)`), so there is no
per-parent-sequence grouping concern; its own creation timeline and key
are used directly, the same "own timestamp, own key" idiom
`PS-SETTINGS-EXPORT-003` used for `career_achievements`/`career_skills`
(tables with their own ordering columns and no need to group by a parent).

**Read window:** trailing columns, per the shared contract.

**`source_deleted_at_utc` and `source_state` are content, not a presence
predicate.** This is the one judgment call in this package most likely to
look, at first glance, like a missed soft-delete exclusion. It is not: the
column name contains "deleted," but it describes a fact about the **linked
capture** (whether `usp_DeleteCapture` later tombstoned the source this
Moment was built from), never a flag on the `moment_sources` row's own
existence. The row is 1:1 with its Moment via a real, non-conditional
unique constraint and is never itself soft-deleted -- it is either present
(1:1 with an existing Moment) or hard-deleted along with that Moment
(`usp_DiscardMomentProposal`). A member reading their own export needs to
know their Moment's source capture was later deleted; filtering that fact
out would make the export **less** truthful, not more private (the
Moment's own text, from `dbo.moment_versions`, is unaffected either way).
Proven at the data level in the verification script: a `moment_source` row
directly transitioned to `source_state = 'deleted'` (simulating
`usp_DeleteCapture`'s own tombstone update) is still returned by this
reader, alongside an unrelated `'available'` row for the same owner.

#### `dbo.moment_placements` -> `usp_ReadAccountExportMomentPlacementForOwner`

**Source:** `dbo.moment_placements`, created by `PS-PLACEMENT-001`
(`SQL FIles/Migrations/proposed/PS-PLACEMENT-001_moment_placements.sql`).

**Allowlist (8 content fields):** `placement_key`, `moment_key` (parent
linkage), `moment_version_number`, `placement_status`, `created_at_utc`,
`reactivated_at_utc`, `removed_at_utc`, `updated_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `placement_id` | Internal integer surrogate. |
| `owner_profile_id` | Internal id; used as one half of the "both sides" `WHERE` predicate, never selected. |
| `moment_id` | Internal FK id; replaced by the joined `moment.moment_key`. |
| `target_entity_id` | **This package's defining scope boundary for this table.** A foreign key to `dbo.slate_entities` (Opportunity Slate), which is not one of this package's six claimed tables. See "Interpretation notes" below -- this is the one deviation in this package worth independent-review attention beyond the shared contract's own restatement of it. |
| `created_by_user_id` | A "created-by"-class user id; excluded. |
| `reactivated_by_user_id` | Same class; excluded. |
| `removed_by_user_id` | Same class; excluded. |
| `row_version` | Same reasoning as above. |

**Joins:** `JOIN dbo.moments AS moment ON moment.moment_id =
placement.moment_id` -- **both-sided** owner predicate
(`placement.owner_profile_id = @ProfileId AND moment.owner_profile_id =
@ProfileId`), because `dbo.moment_placements` carries its own
`owner_profile_id` column.

**Ordering:** `placement.created_at_utc, placement.placement_key` -- a
Moment may have several placements over time (different target entities,
or a removed-then-reactivated history at the same target), so this table's
own creation timeline is the natural order, not a forced grouping by
parent Moment.

**Read window:** trailing columns, per the shared contract. A `'removed'`
placement is real historical content (the member placed something, then
removed it) and is not filtered out -- the same "archived/removed content
is still real content" reasoning applied to `dbo.captures`' `'archived'`
status.

## Every other C0 domain

Every domain this package does not touch is unchanged from
`PS-SETTINGS-EXPORT-003`'s own recorded `DOMAINS` entries, with one
exception: `voice_photo`'s disposition and reason were corrected (see "A
factual correction" above). Full listing:
`profile_publication_foundation`, `own_publication_versions`,
`voice_photo` (corrected), `journal`, `workshop_my_knowledge`,
`opportunity_slate`, `my_opportunities`, `community_authored_content`,
`connection_preferences`, `connection_records`, `notifications_inbox`,
`notification_preferences`, `consent_history`, `audit_events`,
`browser_local_interview_history`, `interview_telemetry`, `ai_proposals`,
`ask_pete_public`, `ask_pete_direct`, `projects`, `home`,
`file_evidence_metadata`, `indexes_caches_provider_backups`, and
`career_skill_links` (a `living_resume` sibling, also untouched).
`opportunity_slate` in particular remains `excluded` with its existing
reason ("C0 marks Opportunity Slate includable with provenance for durable
member records; this package builds no reader for it") -- unchanged by
this package's own `target_entity_id` exclusion, since that exclusion is
about **this package's placement reader**, not a claim about Opportunity
Slate's own future export contract.

## Interpretation notes

Recorded because the contract left this to judgment, not because it is a
defect:

1. **`target_entity_id`/`dbo.slate_entities` exclusion on
   `dbo.moment_placements`.** The lane claim's "opaque `*_key` columns...
   via owner-predicated joins where a table carries the parent id"
   language, read most literally, could be extended to any parent-shaped
   foreign key, including this one. This package reads it more narrowly:
   the claim's own two worked examples are `moment_key` and `capture_key`
   -- both **within** this package's six-table scope -- and the claim's
   scope line is explicit ("SIX TABLES, TEXT TRUTH ONLY"). `slate_entities`
   is not one of them, and Opportunity Slate already has its own,
   separate, `excluded`-with-a-reason C0 matrix row and `DOMAINS` entry
   pointing at a distinct future package. Exposing `target_entity_key`
   here would be safe in isolation (an opaque GUID, not sensitive) but
   would (a) add an undeclared dependency on `PS-PLAT-002`/`PS-PLAT-005`
   this migration's own guards do not check for, (b) require a `JOIN
   dbo.slate_entities` this package's six-table contract does not
   anticipate, and (c) preempt a decision that belongs to the Opportunity
   Slate reader package. The placement row still reports every fact about
   the placement **itself** -- status, exact version, every lifecycle
   timestamp -- so the export is not silently incomplete, only silent
   about *where* the Moment was placed. A member export today would still
   truthfully say "this Moment was actively placed somewhere on
   `<date>`," just not "...specifically onto Slate item `<key>`."
2. **`dbo.moment_sources`' `source_state`/`source_deleted_at_utc` are
   content, not a soft-delete presence predicate.** Covered in full in the
   `moment_sources` section above; recorded here because "deleted" in a
   column name is exactly the pattern the hard-exclusion instruction names
   generically, and this is the one place in this package's six tables
   where that pattern-match would be wrong if applied mechanically.
3. **`dbo.captures.active` excluded without becoming a `WHERE` predicate.**
   Unlike `PS-SETTINGS-EXPORT-003`'s `app_user.active`/`profile.active`
   (excluded **and** used as an implied identity-resolution precondition),
   `dbo.captures.active` is excluded from the output but never used to
   gate row presence -- only `deleted_at_utc IS NULL` does. An archived
   capture must still appear in an owner's own export; the `active` column
   never determines whether the row is deleted, only whether it is
   currently `'captured'` vs. `'archived'`, which `status` already states
   more legibly.

## Grant model

Identical to `PS-SETTINGS-EXPORT-001` and `PS-SETTINGS-EXPORT-003`: the
governed apply identity holds `db_ddladmin` only and cannot `GRANT
EXECUTE`; no `GRANT`, `CREATE ROLE`, `CREATE USER`, or `sp_addrolemember`
statement appears anywhere in this migration. The intended production
grant -- `EXECUTE` on these six procedures for the existing web-app
principal role -- is a separate, later, administrator-run authority
operation, not created here and not authorized by a repository merge of
this file. Design only; nothing applied.
