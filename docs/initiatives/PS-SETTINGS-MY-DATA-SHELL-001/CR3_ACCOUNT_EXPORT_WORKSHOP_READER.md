# CR3 account export Workshop / My Knowledge reader

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-WORKSHOP-READER-001`
**Slice:** Protected, replacement package 3 of the 2026-08-29 reader
topology, after `PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001` (replacement
package 1, main `cc5174da`) and
`PS-SETTINGS-ACCOUNT-EXPORT-CAPTURE-MOMENT-READERS-001` (replacement
package 2, main `1f701263`) were both independently reviewed and merged.
**Depends on:** the lane claim's own enumerated contract
(`docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-WORKSHOP-READER-001.json`);
reads `C0_ACCOUNT_EXPORT_ARCHITECTURE.md`'s V1 domain matrix ("Workshop / My
Knowledge" row) as the allowlist bible; reads
`CR2_ACCOUNT_EXPORT_CAPTURE_MOMENT_READERS.md` and
`PS-SETTINGS-EXPORT-004_capture_moment_readers.sql` as the structural
template this package follows closely.
**Status:** Candidate migration/rollback/verification/adapter/test files,
self-reviewed by the writer. **Nothing in this package runs in production.
No schema apply has been performed anywhere except by the manager's own
future gate. No account export exists, is available, or is usable by any
member today.**

## Decision

Two tables, text truth only, one reader per table: `dbo.knowledge_items`
and `dbo.knowledge_item_versions`. Both are applied in production per
`docs/governance/PRODUCTION_SCHEMA_STATE.md` (`PS-WORKSHOP-001` applied
2026-08-02, `PS-WORKSHOP-002` applied 2026-08-06), living under
`SQL FIles/Migrations/proposed/` despite that. Two procedures total, each
with a paired Python adapter function in
`services/account_export_domain_readers.py`, grouped into one `DOMAINS`
entry matching the C0 matrix's own single row: `workshop_my_knowledge` (2
readers).

This package creates no table, no trigger, no index, no container, no
worker, no route, and no UI. It does not populate
`dbo.account_export_job_domains` or wire any reader into a worker.

## Schema revalidation (C0's own caveat for this row)

C0's V1 domain matrix marks this row **"Included after schema
revalidation"** with the required truth boundary: "current schema, owner
reads, and use-disclosure dependencies must be rechecked." This section
records that recheck, performed at write time, before any allowlist
decision below was made.

1. **Current schema.** `PS-WORKSHOP-001_knowledge_items.sql` and
   `PS-WORKSHOP-002_knowledge_confirmation.sql`
   (`SQL FIles/Migrations/proposed/`) were read in full. `PS-WORKSHOP-001`
   creates three tables: `dbo.knowledge_items`, `dbo.knowledge_item_versions`,
   and `dbo.knowledge_item_save_requests` (an idempotency ledger). `PS-
   WORKSHOP-002` creates **no table** -- only a new procedure
   (`usp_ConfirmAuthoredKnowledgeBacklogForOwner`) and a revised admission
   predicate on `usp_ArchiveKnowledgeItemForOwner`. `PS-WORKSHOP-003_
   knowledge_version_history_read.sql` and `PS-WORKSHOP-004_knowledge_edit_
   provenance.sql` (both applied 2026-08-28, per
   `PRODUCTION_SCHEMA_STATE.md`, more recently than `PS-WORKSHOP-001`/`002`
   and delivered by the now-closed `PS-WORKSHOP-PROVENANCE-VISIBILITY-001`/
   `PS-WORKSHOP-EDIT-PROVENANCE-001` lanes) were also read in full and
   confirmed to add **only procedures** -- `usp_ListKnowledgeItemVersionsForOwner`,
   and a replacement `usp_UpdateKnowledgeItemForOwner` body -- never a column,
   table, or constraint change on either table this package reads. The
   column/constraint enumeration in this document and in the migration's
   own guards is therefore the accurate current schema as of this writing,
   not merely `PS-WORKSHOP-001`'s original shape.
2. **Owner reads.** Every column this package exports was checked against
   `PS-WORKSHOP-001`'s own owner-scoped procedures
   (`usp_ListKnowledgeItemsForOwner`, `usp_GetKnowledgeItemForOwner`) to
   confirm the identity-resolution shape (`@UserKey` -> active
   `app_users` row -> active `member_profiles` row) and the
   `item.visibility = N'private'` "never trust the default" discipline
   those procedures already apply to this exact table, even though
   `CK_knowledge_items_visibility` hard-locks the column today. Both
   readers below apply the identical discipline.
3. **Use-disclosure dependencies.** `PS-OPPSLATE-USE-001_opportunity_
   slate_use.sql` (applied 2026-08-28, the migration that actually shipped
   under the "use-disclosure" heading) was read in full: it tags
   Opportunity Slate evidence rows with a bare string
   `evidence_kind = N'knowledge_item'` and is, by its own header comment,
   "deliberately NOT joined to `dbo.knowledge_items`." It adds no foreign
   key, column, or trigger on either table this package reads.
   `PS-OPPSLATE-001/002/003` similarly `JOIN`/`LEFT JOIN dbo.knowledge_items`
   only as a **reader** (Opportunity Slate citing a knowledge item as
   evidence), never altering its schema. There is no use-disclosure
   dependency this package's reader must account for.
4. **Active Workshop lane coordination.** Every `docs/governance/
   lane_claims/PS-WORKSHOP-*.json` file was read directly: all nine
   (`DELIVERY-CONTINUITY-001`, `EDIT-PROVENANCE-001`,
   `FG-PRODUCTION-TRUTH-001`, `PROVENANCE-001`, `PROVENANCE-EDGE-001`,
   `PROVENANCE-VISIBILITY-001`, `SURFACE-TRUTH-001`, `USE-DISCLOSURE-001`,
   `USE-DISCLOSURE-PRODUCTION-TRUTH-001`) carry `"state": "closed"`. A
   full scan of every lane claim in the repository found exactly two
   `"state": "active"` entries: this package's own claim, and
   `PS-SYNTHETIC-SEALED-CREDENTIAL-BROKER-RUNTIME-BINDING-001` (unrelated
   synthetic-member QA infrastructure, no Workshop or account-export
   surface overlap). **Coordination note:** at the time C0 was written
   (checkpoint `4873cd15`), C0 itself recorded that an active
   `PS-WORKSHOP-USE-DISCLOSURE-001` owned `services/database_service.py`
   and `SQL FIles/Migrations/registry.json` -- that lane has since closed
   (`closed_at: 2026-08-27T23:21:25Z`, merged `9e40993d`) after an owner
   reassignment recorded in its own claim file. No live Workshop lane's
   claimed surfaces collide with this package's allowlist reasoning or
   files today; nothing was adapted to accommodate one because none
   exists.

## Shared contract every one of the two procedures follows

- Accepts **only** `@UserKey nvarchar(300)`. No owner id, table name, or
  dynamic SQL built from any argument. Pinned by
  `tests/test_settings_export_workshop_reader.py`'s exact-signature
  assertion.
- Resolves identity with the **byte-identical** header every prior package
  in this program uses (pinned by test, same literal constant): `@UserKey`
  -> an **active** `dbo.app_users` row -> its **active**
  `dbo.member_profiles` row. An unresolved identity `RETURN`s before any
  `SELECT` -- no result set at all, which the calling adapter treats as
  zero rows, never an error.
- Filters every row by the resolved owner profile, with the shape each
  table's own schema requires -- derived from the schema, not assumed:
  - `dbo.knowledge_items` carries its own `owner_profile_id`, so its
    reader asserts `item.owner_profile_id = @ProfileId` directly (the same
    single-table shape `PS-SETTINGS-EXPORT-004`'s `captures`/`moments`
    readers use). It also asserts `item.visibility = N'private'`
    explicitly, matching `usp_ListKnowledgeItemsForOwner`'s/
    `usp_GetKnowledgeItemForOwner`'s own established discipline for this
    table.
  - `dbo.knowledge_item_versions` is **different from every version-
    history table `PS-SETTINGS-EXPORT-004` read**
    (`dbo.capture_revisions`, `dbo.moment_versions`): unlike those two, it
    independently carries its **own** `owner_profile_id` column, required
    by `FK_knowledge_item_versions_item`'s composite foreign key
    `(knowledge_item_id, owner_profile_id) -> dbo.knowledge_items
    (knowledge_item_id, owner_profile_id)`. Its reader therefore uses the
    **both-sided** owner predicate
    (`version_record.owner_profile_id = @ProfileId AND
    item.owner_profile_id = @ProfileId`) -- the same defense in depth
    `PS-SETTINGS-EXPORT-004` applied to `dbo.moment_sources`/
    `dbo.moment_placements` -- never the single-sided, parent-only shape
    that package needed for `capture_revisions`/`moment_versions`. This
    package has no "parent-only" reader at all.
- Every internal integer id is replaced in the output by the row's own
  opaque `*_key uniqueidentifier` where the table has one, plus the
  parent's opaque `knowledge_item_key` for intra-export linkage.
  `dbo.knowledge_item_versions` has **no opaque key column of its own**
  (unlike `dbo.capture_revisions.revision_key` or
  `dbo.moment_versions.moment_version_key`) -- its identifying tuple is
  `(knowledge_item_id, version_number)`, already unique per
  `UQ_knowledge_item_versions_number`, so its reader exports the joined
  parent's `knowledge_item_key` plus its own `version_number` as that
  tuple's exported form. No surrogate key is manufactured for a column
  the schema does not have.
- Returns **only** an explicit, hand-picked column list -- never
  `SELECT *` -- with a deterministic `ORDER BY` (see the per-table
  "Ordering" note below).
- Contains **no transaction control of any kind**, no write, and no nested
  `EXEC`/dynamic SQL -- identical structural guarantee to every prior
  package, proven the same three ways (a structural grep loop in the
  paired verification script, a static text assertion in the test file,
  and by construction: exactly two `SELECT` keywords per body).
- Returns the read window as two trailing columns on the single content
  result set -- identical mechanism to every prior package; see
  `CR1_ACCOUNT_EXPORT_CORE_READERS.md`'s "Read window mechanism" section
  for the full Microsoft-documentation-backed rationale. Not
  re-litigated here since nothing about it changed.
- Never selects `row_version`, any `created_by`/`approved_by`/
  `confirmed_by`/`archived_by`/`saved_by` user id, or a soft-delete
  column -- **neither table has one**. See "Note on deletion" below.

## Domain-by-domain contract

### `workshop_my_knowledge` -- included (2 readers)

#### `dbo.knowledge_items` -> `usp_ReadAccountExportKnowledgeItemForOwner`

**Source:** `dbo.knowledge_items`, created by `PS-WORKSHOP-001`
(`SQL FIles/Migrations/proposed/PS-WORKSHOP-001_knowledge_items.sql`).

**Allowlist (10 content fields):** `knowledge_item_key`, `item_status`,
`classification`, `visibility`, `current_version_number`,
`confirmed_version_number`, `confirmed_at_utc`, `archived_at_utc`,
`created_at_utc`, `updated_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `knowledge_item_id` | Internal integer surrogate; never disclosed. |
| `owner_profile_id` | Internal id, used only as the `WHERE` predicate. |
| `confirmed_by_user_id` | An "approved-by"-class user id (who confirmed this item); excluded by the same hard-exclusion class `PS-SETTINGS-EXPORT-004` applied to `dbo.moments.confirmed_by_user_id`. |
| `archived_by_user_id` | Same class as `confirmed_by_user_id` (who archived this item); excluded. |
| `row_version` | Not member-authored content; changes on every update, so it is not a stable cross-file linkage identifier either. |

**Joins:** none.

**Ordering:** `item.created_at_utc, item.knowledge_item_key` -- the row's
own creation timeline plus its own key as a deterministic tiebreak, the
same "own timestamp, own key" idiom `PS-SETTINGS-EXPORT-004` used for
`dbo.captures`/`dbo.moments`. Deliberately **not**
`usp_ListKnowledgeItemsForOwner`'s own `updated_at_utc DESC` list order:
that is the live UI's "recently edited first" order; this export uses the
same stable creation-chronological order every other top-level reader in
this program uses. See "Interpretation notes" below.

**Read window:** trailing `read_started_at_utc`/`read_ended_at_utc`
columns, per the shared contract.

**Note on deletion.** `dbo.knowledge_items` has **no** `deleted_at_utc`
column. `usp_DeleteKnowledgeItemForOwner` is a plain hard `DELETE` of the
item and its versions (`PS-WORKSHOP-001`'s own header: "W1 has no
downstream use table yet... Delete is therefore a plain hard delete"), so
there is no soft-delete predicate to add. `archived_at_utc`/
`archived_by_user_id` describe a **real, undeleted** item state -- exactly
the "archived is not deleted" treatment `PS-SETTINGS-EXPORT-004` already
gave `dbo.captures.status = 'archived'` -- so an archived item still
appears in the export; only the archiving actor's id is excluded.

**Note on `item_status`.** `CK_knowledge_items_status` allows
`'suggested'` (an AI-proposed, unaccepted draft) alongside `'unfinished'`/
`'confirmed'`/`'archived'`, but `PS-WORKSHOP-002`'s own header confirms
(via a full grep of `services/`) that no production code path writes
`'suggested'` today. This reader does not special-case it -- whatever
status is actually stored is returned truthfully, matching this program's
"text truth only" principle. A future package that ships a real
AI-suggestion write path should revisit whether an unaccepted
`'suggested'` row belongs in a member's own account export at all, since a
suggestion is explicitly not-yet-member-authored content -- the same
class of forward-looking note `PS-SETTINGS-EXPORT-004` recorded for
`PS-JOURNAL-001`'s future `dbo.moments.archived_at_utc`.

**Note on `visibility` (independent-review finding).** Both readers assert
`item.visibility = N'private'`. Today `CK_knowledge_items_visibility`
hard-locks every row to `'private'`, so the predicate is provably a no-op
kept as never-trust-the-default discipline. If that CHECK is ever relaxed,
a member's non-private knowledge items would silently vanish from their
OWN export — an export-completeness risk, not a privacy one. Whichever
package relaxes the constraint must revisit both readers' predicates in
the same motion.

**Note on `confirmed_at_utc`.** A row can become confirmed either through
a live member action or through `PS-WORKSHOP-002`'s
`usp_ConfirmAuthoredKnowledgeBacklogForOwner` standing-rule reconciliation
sweep (owner ruling, 2026-08-06: "anything in your knowledge database is
confirmed. You put it there"). Both are equally true current-state facts;
this export reports the state, not the audit-trail distinction between
the two mechanisms (`action_type` values `knowledge_item.updated` vs.
`knowledge_item.backlog_confirmed`), which lives only in `dbo.audit_events`
-- a domain C0 marks **excluded** entirely, unaffected by this package.

#### `dbo.knowledge_item_versions` -> `usp_ReadAccountExportKnowledgeItemVersionForOwner`

**Source:** `dbo.knowledge_item_versions`, created by `PS-WORKSHOP-001`.

**Allowlist (8 content fields):** `knowledge_item_key` (parent linkage,
this table's exported identifying key -- see below), `version_number`,
`title`, `approved_wording`, `original_member_wording`, `body_format`,
`authored_via`, `saved_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `knowledge_item_version_id` | Internal integer surrogate. |
| `knowledge_item_id` | Internal FK id; replaced in the output by the joined `item.knowledge_item_key`. |
| `owner_profile_id` (this table's own) | Internal id; used as one half of the "both sides" `WHERE` predicate, never selected. |
| `saved_by_user_id` | A "created-by"-class user id; excluded by the same class as `dbo.moment_versions.saved_by_user_id`. |
| `row_version` | Same reasoning as above. |

**Joins:** `JOIN dbo.knowledge_items AS item ON item.knowledge_item_id =
version_record.knowledge_item_id` -- **both-sided** owner predicate
(`version_record.owner_profile_id = @ProfileId AND
item.owner_profile_id = @ProfileId`), because `dbo.knowledge_item_versions`
carries its own `owner_profile_id` column (required by its own composite
foreign key to `dbo.knowledge_items`, confirmed by reading the schema, not
assumed -- see "Interpretation notes"). Also asserts the joined item's
`item.visibility = N'private'`.

**Ordering:** `item.created_at_utc, item.knowledge_item_key,
version_record.version_number` -- `version_number` is only unique
**within** one item (`UQ_knowledge_item_versions_number UNIQUE
(knowledge_item_id, version_number)`), so a flat reader over every item's
versions must group by the parent first (by the parent's own creation
timeline and key) before ordering by the child's per-parent sequence
number, the same `capture_revisions`/`moment_versions` idiom.

**Read window:** trailing columns, per the shared contract.

**Note on `authored_via`/`body_format`.** Both are types/statuses-class
facts about the member's own content -- how they created this version
(`typed`/`spoken`/`ai_assisted_approved`) and its formatting
(`plain`/`rich`) -- not confirmation-machinery about who reviewed or
approved it. `PS-WORKSHOP-002` added no column at all, so there is no
"confirmation-machinery field `PS-WORKSHOP-002` added" to exclude here;
both fields are `PS-WORKSHOP-001`'s own, in the same "types/statuses" the
lane claim's allowlist categories name. `ai_assisted_approved` is included
as a value like any other -- it describes the member's own approved
content, never a raw AI proposal (`PS-WORKSHOP-001`'s own header: "No AI
proposal is ever written here").

**Note on `original_member_wording`.** Retained verbatim, never rewritten,
per `PS-WORKSHOP-001`'s and `PS-WORKSHOP-004`'s own design (the latter
specifically exists to retain this exact fact across owner edits). Older
`ai_assisted_approved` rows may carry refined wording in this column
because the true original was not retained when those rows were created
(`PS-WORKSHOP-003`'s own header note) -- this reader exposes the stored
fact as-is and manufactures no greater certainty than the schema records.

## `dbo.knowledge_item_save_requests` -- excluded (not built by this package)

`PS-WORKSHOP-001`'s idempotency ledger for one-step Save: an owner-scoped
replay key and the resulting `knowledge_item_id` only -- no title,
wording, status, or other member-authored fact. Recorded in
`services/account_export_domain_readers.py` as its own named, excluded
`DOMAINS` entry (`workshop_knowledge_save_requests`), the identical
treatment `PS-SETTINGS-EXPORT-003` gave `career_skill_links` and
`PS-SETTINGS-EXPORT-004` gave `target_entity_id`/`dbo.slate_entities`:
never silently folded into `workshop_my_knowledge`, so a future reader of
that dict never has to guess whether the omission was deliberate.

## Every other C0 domain

Every domain this package does not touch is unchanged from
`PS-SETTINGS-EXPORT-004`'s own recorded `DOMAINS` entries. Full listing:
`account`, `profile`, `living_resume`, `career_skill_links`,
`profile_publication_foundation`, `own_publication_versions`, `capture`,
`voice_photo`, `moment`, `journal`, `opportunity_slate`, `my_opportunities`,
`community_authored_content`, `connection_preferences`,
`connection_records`, `notifications_inbox`, `notification_preferences`,
`consent_history`, `audit_events`, `browser_local_interview_history`,
`interview_telemetry`, `ai_proposals`, `ask_pete_public`, `ask_pete_direct`,
`projects`, `home`, `file_evidence_metadata`,
`indexes_caches_provider_backups`. `opportunity_slate` in particular
remains `excluded` with its existing reason ("C0 marks Opportunity Slate
includable with provenance for durable member records; this package
builds no reader for it") -- unaffected by this package's own scope,
since `PS-OPPSLATE-USE-001`'s bare `evidence_kind` string tag creates no
schema coupling this reader needs to account for (see "Schema
revalidation" above).

## Interpretation notes

Recorded because the contract left this to judgment, not because it is a
defect:

1. **`dbo.knowledge_item_versions`' owner-predicate shape was derived from
   the schema, not assumed.** The writer brief flagged this table as one
   whose shape needed checking ("via an owner-predicated-both-sides join
   if the versions table lacks its own owner column -- derive from
   schema"). Reading `PS-WORKSHOP-001_knowledge_items.sql` directly shows
   `dbo.knowledge_item_versions` **does** carry its own `owner_profile_id`
   column (required by its composite foreign key to `dbo.knowledge_items`),
   so this reader uses the **both-sided** predicate -- the opposite shape
   from `dbo.capture_revisions`/`dbo.moment_versions`, which carry no such
   column and use a single, parent-only predicate. This is the one
   judgment call in this package most likely to draw independent-review
   attention, precisely because it is easy to assume "a version-history
   table" always means "parent-only" from the sibling package's precedent
   without re-checking this table's own DDL.
2. **`dbo.knowledge_item_versions` has no opaque key column of its own.**
   Unlike every other child table read across this program
   (`capture_revisions.revision_key`, `moment_versions.moment_version_key`),
   this table's own primary key is a plain `IDENTITY(1,1) bigint`, never
   exposed. Its exported identifying tuple is `(knowledge_item_key,
   version_number)`, already unique per `UQ_knowledge_item_versions_number`.
   No surrogate key is manufactured for a column the schema does not have.
3. **Ordering by `created_at_utc` (ascending, creation order), not
   `usp_ListKnowledgeItemsForOwner`'s own `updated_at_utc DESC` list
   order.** The live Workshop UI's own reader orders "most recently
   edited first," a UX choice, not a truth requirement. This export uses
   the same stable creation-chronological order every other top-level
   reader in this program already uses (`dbo.captures`, `dbo.moments`), so
   an owner's knowledge items read in one order across every reader in
   their export, not a Workshop-specific "recency" order that other
   readers do not share.
4. **`item_status = 'suggested'` is not special-cased.** Covered in full
   in the `knowledge_items` section above; recorded here because it is the
   one place in this package where "text truth only" and "no AI proposal
   content" could be read as being in tension, and they are not: the
   column reports a status fact, never a proposal's actual wording (no
   `'suggested'` row is reachable through any production write path
   today, confirmed by `PS-WORKSHOP-002`'s own header).

## Grant model

Identical to `PS-SETTINGS-EXPORT-001`/`003`/`004`: the governed apply
identity holds `db_ddladmin` only and cannot `GRANT EXECUTE`; no `GRANT`,
`CREATE ROLE`, `CREATE USER`, or `sp_addrolemember` statement appears
anywhere in this migration. The intended production grant -- `EXECUTE` on
these two procedures for the existing web-app principal role -- is a
separate, later, administrator-run authority operation, not created here
and not authorized by a repository merge of this file. Design only;
nothing applied.
