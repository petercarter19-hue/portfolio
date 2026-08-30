# CR7 account export preferences and consent reader

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-PREFERENCES-CONSENT-READER-001`
**Slice:** Protected. Executes the owner's accepted 2026-08-30 "Paper 2"
and "Paper 3" rulings: read-only, owner-scoped account-export readers for
the member's own preference and consent records.
**Depends on:** the lane claim's own enumerated contract
(`docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-PREFERENCES-CONSENT-READER-001.json`);
reads `PS-PLAT-004_connections_notifications.sql` (all three claimed
tables, plus their five sibling tables which this package does not
read) and `PS-AUTH-001_identity_foundation.sql` (the per-signup seeding
of `dbo.connection_preferences` inside `usp_UpsertAppUserFromAuth`) in
full as the schema baseline; reads
`CR6_ACCOUNT_EXPORT_MEDIA_TRANSCRIPT_READER.md` +
`CR6_OWNER_TECHNICAL_COMPLETION_REPORT.md` and `CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md`
+ its own completion report for package shape, gate-state conventions,
and deviation style; reads `PS-SETTINGS-EXPORT-003` through `-007`'s own
migrations/verifications/tests as the house pattern;
`docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/B0_PREFERENCES_CONSENTS_TAXONOMY_SCHEMA_FIT.md`
as background evidence on the current schema-fit and write-path state of
all three tables (a Settings-B1-write-feature decision record, not this
package's own governing authority, but independently corroborating every
"no writer exists" and "auto-seeded" finding below).
**Status:** Candidate migration/rollback/verification/adapter/test
files, self-reviewed by the writer. **Nothing in this package runs in
production. No schema apply has been performed anywhere except by the
manager's own future gate. No account export exists, is available, or
is usable by any member today.**

## Decision

Three tables, one reader per table, both directive framings from the
same owner ruling: `dbo.connection_preferences`, `dbo.
notification_preferences`, `dbo.user_consents`. All three are created by
a single migration, `PS-PLAT-004_connections_notifications.sql`
(applied in production per `docs/governance/PRODUCTION_SCHEMA_STATE.md`),
alongside five sibling tables this package does not read
(`connection_requests`, `member_connections`, `user_blocks`,
`user_reports`, `notifications`) -- each already carries its own
`DOMAINS` entry with its own excluded/unavailable disposition
(`connection_records`, `notifications_inbox`), untouched by this
package. Three procedures total, each with a paired Python adapter
function in `services/account_export_domain_readers.py`, flipping three
EXISTING `DOMAINS` keys from `excluded` to `included` (see "Three
existing keys, flipped, not new ones" below).

## Identity -- the one structural nuance of this package

Every reader this program has built before this package filters by
`owner_profile_id = @ProfileId`, with exactly one exception:
`usp_ReadAccountExportAccountForOwner`, whose claimed table IS
`dbo.app_users` itself, filters `id = @UserId` against its own primary
key. All three tables this package reads key on `user_id int NOT NULL`
with a foreign key straight to `dbo.app_users(id)` -- confirmed by
reading `PS-PLAT-004`'s own DDL, not assumed -- and have **no**
`owner_profile_id` column at all. Filtering by `@UserId` is therefore
**not a new pattern**, only the second time this program has used it:
`usp_ReadAccountExportAccountForOwner` (`PS-SETTINGS-EXPORT-003`)
already filters `WHERE app_user.id = @UserId` for the identical
structural reason (`dbo.app_users` itself keys on `id`, not
`profile_id`). This package's three readers are the second, third, and
fourth readers in the program to filter on `@UserId` instead of
`@ProfileId`.

Every reader below still resolves the full, **byte-identical** identity
header every prior package uses -- `@UserKey` -> an **active**
`dbo.app_users` row -> its **active** `dbo.member_profiles` row,
capturing **both** `@ProfileId` and `@UserId` even though only
`@UserId` is used downstream -- rather than a shortened header that
skips the `member_profiles` join entirely. This is a deliberate choice,
not an oversight left over from copying the template:

1. **One identity contract, program-wide.** A member without an
   **active** `dbo.member_profiles` row gets nothing from **any**
   reader in this program, including these three. If this package's
   readers resolved identity through `dbo.app_users` alone (skipping
   the profile join), a member whose account is active but whose
   profile has been deactivated -- a real, distinct state this schema
   allows -- would see their preferences/consent history in an export
   that already excludes every other domain for that same member. That
   would be a second, weaker, silently-inconsistent identity contract
   living inside one otherwise-uniform reader program.
2. **The identity-header byte-consistency test requires exactly ONE
   distinct header variant across the whole program**
   (`test_identity_header_is_byte_identical_across_every_account_export_reader_in_the_program`,
   extended in this package's own test file to scan
   `PS-SETTINGS-EXPORT-003` through this package's own file). A
   shortened header would introduce a second variant and fail that test
   by design -- the test exists specifically to catch this class of
   drift.

The verification in this contract's own paired test file confirms both
properties hold: exactly one identity-header variant exists across the
program after this package's additions, and it is byte-identical to
every prior package's own.

## Paper 2 -- both preference tables included, labeled dormant

C0's own V1 domain matrix already recorded this disposition for both
rows: "Connection preferences: Included, labeled dormant";
"Notification preferences: Included after owner-scoped/dormant field
allowlist... label dormant behavior truthfully; do not promise
unsupported email or quiet-hours behavior." This package performs the
underlying verification C0 called for, against the real schema and a
repository-wide grep, not merely restating C0's own framing:

- **`dbo.notification_preferences` has NO writer anywhere in this
  codebase.** A repository-wide search for any `INSERT`/`UPDATE`
  statement targeting this table, across every `.sql` file this
  worktree materializes, returns zero results. `B0_PREFERENCES_CONSENTS_TAXONOMY_SCHEMA_FIT.md`
  independently confirms the identical finding ("No governed
  notification-type catalog, notification-preference runtime, email
  sender, or quiet-hours evaluator was found"). A real export for any
  member legitimately returns **zero rows** here today -- this is not a
  defect in the reader, and the reader must still exist so the export's
  own manifest can truthfully report the domain as included-but-empty
  rather than silently absent.
- **`dbo.connection_preferences` is auto-seeded, all-defaults, for
  every member.** Two writers exist, and only two: `PS-PLAT-004`'s own
  backfill (`INSERT dbo.connection_preferences(user_id) SELECT u.id
  FROM dbo.app_users AS u WHERE NOT EXISTS (...)`, run once at migration
  time for every user that existed then) and `PS-AUTH-001`'s
  `usp_UpsertAppUserFromAuth` (`IF NOT EXISTS (SELECT 1 FROM dbo.
  connection_preferences WHERE user_id = @UserId) INSERT dbo.
  connection_preferences(user_id) VALUES (@UserId);`, run for every
  signup since). Neither writer ever sets a non-default value for any
  of the three opt-in flags or `discoverable_audience` -- every member's
  row, without exception, starts at `discovery_opt_in = 0,
  goal_matching_opt_in = 0, recruiter_discovery_opt_in = 0,
  discoverable_audience = 'private'`, and no procedure anywhere changes
  it. A real export for any member returns exactly **one** row here
  today, always at these defaults.

Exporting either table's stored values without saying so would let an
all-defaults row **masquerade as live product behavior** the member
actually configured and the product actually honors -- precisely the
risk the owner's ruling names. Both readers therefore emit an explicit
constant disclosure column on every row:

```sql
N'dormant_not_yet_enforced' AS feature_status
```

**Wording rationale, recorded because the brief left this to
judgment.** The chosen value states two facts precisely and nothing
more: (1) `dormant` -- the underlying feature has no live enforcement
path, distinguishing it from a value like `disabled` or `off`, which
would wrongly imply the member's stored value is being respected by
some inactive switch; (2) `not_yet_enforced` -- the state is temporal
and reversible (a future feature package could activate real
enforcement), not `never_enforced` or `deprecated`, which would wrongly
imply a permanent product decision. The identical value is used for
**both** preference tables rather than two distinct wordings, because
the underlying truth is identical for both (no runtime path reads or
acts on either table's values today) and a single, program-wide
constant is easier for a future package to grep for and retire in one
place when real enforcement ships. The column name `feature_status`
matches this schema's own established `_status` suffix idiom
(`consent_status`, `report_status`, `request_status`,
`delivery_status`), rather than inventing a new naming shape.

**This is a projection-truth disclosure about the FEATURE, not stored
member data.** The distinction matters for how a future reader of this
export should treat the column: it is not something the member set, not
something that varies per member, and not itself subject to the
"canonical truth vs. AI proposal vs. derived projection" separation this
program's own trust invariants require for *content* -- it is closer to
a schema/manifest-level annotation the reader emits about *itself*, the
same category as the `read_started_at_utc`/`read_ended_at_utc` trailing
columns every reader in this program already emits, except human-legible
rather than a timestamp. `services/account_export_domain_readers.py`'s
own module docstring and this document both state this explicitly so a
future package does not mistake the constant for a member fact that
needs its own privacy review.

**The consent reader carries NO such label.** See "Paper 3" below for
why.

## Paper 3 -- the member's own consent history included; evidence_json excluded whole; no third-party consent read

`dbo.user_consents` is an append-only history ledger:
`consent_code`, `policy_version`, `consent_status`, and a
server-defaulted `recorded_at_utc` per event. C0's own V1 domain matrix
already recorded this disposition: "Consent history: Included,
evidence-minimized... exclude raw claims, secrets, excessive evidence,
and third-party content."

**Allowlist (4 content fields):** `consent_code`, `policy_version`,
`consent_status`, `recorded_at_utc`.

**Exclusions and reasons:**

| Column | Category | Reason |
| --- | --- | --- |
| `user_consent_id` | (standard) | Internal integer surrogate; never disclosed. Also the reader's own trailing `ORDER BY` tiebreak -- excluded from output, used only as a sort key, the identical treatment `usp_ReadAccountExportAccountForOwner`/`usp_ReadAccountExportProfileForOwner` already give their own excluded internal id. |
| `user_id` | (standard) | Internal id, used only as the `WHERE` predicate. |
| `evidence_json` | `UNCONSTRAINED_EVIDENCE` | A schema-free `nvarchar(max)` column (`CK_user_consents_evidence` only requires valid JSON, never a bounded shape) that could hold anything a future writer chooses to put there -- up to and including network addresses or device details. Excluded whole until a future package performs the field-by-field review the owner's ruling requires. |
| `source_context` | (disclosed, not a directive category -- see below) | A plain `nvarchar(100)` scalar column, distinct from `evidence_json`, excluded for a different, narrower reason. |

**`consent_status` includes `withdrawn`, and every status is
returned.** `CK_user_consents_status` allows exactly `accepted`,
`declined`, `withdrawn` -- this is genuine history semantics, never a
single current-state flag. `B0_PREFERENCES_CONSENTS_TAXONOMY_SCHEMA_FIT.md`'s
own future-writer contract is explicit that a withdrawal "is a new
ledger event, never an update or deletion of the earlier event." This
reader includes **every** row for the member, at every status, so a
member's export shows their full consent history including any
withdrawal -- never only the latest event or only the accepted ones.
This is the central Paper 3 proof, pinned by a dedicated test
(`test_verify_proves_the_withdrawn_after_accepted_consent_history`) and
canary-proven in the verification script (an accepted event followed by
a withdrawn event for the same `consent_code`, deliberately sharing one
identical `recorded_at_utc` -- see "A deliberate same-timestamp tie"
below -- both proven present in the captured output).

**No dormant-feature label on this reader.** Unlike the two preference
tables, a `dbo.user_consents` row -- if one exists -- is never an
all-defaults placeholder nobody configured; the table has no `DEFAULT`
constraint on any of `consent_code`/`policy_version`/`consent_status`
at all (every value must be supplied by whatever writer creates the
row), so any row this reader ever returns is, by construction, a real
event some caller actually recorded. Labeling it dormant would be
false, not merely unnecessary.

### Why `source_context` is excluded, and why it is NOT the same reasoning as `evidence_json`

`source_context nvarchar(100) NULL` is a plain, length-bounded scalar
column -- structurally nothing like `evidence_json`'s unbounded
schema-free shape. The writer brief's own instruction was to judge this
column against the DDL/procedures and include it **only if** it can be
shown to carry "a plain, bounded, non-PII context label," excluding
with a reason if in doubt. The judgment performed here, following this
program's own "trace actual writes" discipline (the precedent
`PS-SETTINGS-EXPORT-007` set for classifying
`deletion_capture_row_version`/`scan_result` by reading the procedures
that actually write them, never by column name or type alone):

**A repository-wide search confirms NO procedure anywhere writes
`dbo.user_consents` at all, today.** Not one `INSERT`, `UPDATE`, or
`DELETE` statement targeting this table exists anywhere in this
worktree's `SQL FIles/` tree. `PS-ASK-PETE-DIRECT-001` -- this
program's one existing feature-scoped consent precedent -- has its own,
entirely separate storage contract (`ask-pete-direct-consent.v1`,
stored on its own feature table) and never touches `dbo.user_consents`.
There is therefore **no procedure body to trace**: the "judge it against
the DDL/procedures" instruction cannot be satisfied in the affirmative
direction, because the second half of that phrase (procedures) supplies
zero evidence either way. The column's *name* suggests something
bounded and label-like (and `B0_PREFERENCES_CONSENTS_TAXONOMY_SCHEMA_FIT.md`'s
own future-writer contract describes an intended future use, "feature
surface or source context"), but a name and a future intention are not
the same thing this program's own discipline requires: a real procedure
body showing what is actually written. Per the brief's own "if in
doubt, EXCLUDE with a reason" instruction, `source_context` is excluded
-- not folded into `UNCONSTRAINED_EVIDENCE` (it is not schema-free or
unbounded; that categorization would overstate the risk), but as its
own disclosed, non-directive-category exclusion, matching this
program's existing precedent for a column excluded on program discipline
rather than an owner-named category (`PS-SETTINGS-EXPORT-006`'s
`idempotency_key`). **This classification is provisional by its own
nature**: the moment a future package adds the first real writer to
`dbo.user_consents`, this column should be re-judged against that
writer's actual procedure body, exactly as this program's own precedent
requires -- not left excluded merely because this document once excluded
it.

### No third-party consent is read

Stated explicitly, per the owner's ruling, not merely true by omission:
`dbo.recruiter_questions` is untouched and unread by this migration, by
the reader it would have to extend to reach it, and by the paired
verification script. This package's three claimed tables
(`connection_preferences`, `notification_preferences`, `user_consents`)
are the entire scope; no fourth table is read, joined, or referenced
anywhere in this candidate.

## A deliberate same-timestamp tie

`IX_user_consents_history (user_id, consent_code, recorded_at_utc DESC)`
is **not** a unique index -- confirmed by reading `PS-PLAT-004`'s own
DDL (`CREATE INDEX`, no `UNIQUE` keyword). `consent_code +
recorded_at_utc` is therefore not provably collision-free: two events
for the same code could, in principle, share one `recorded_at_utc` tick
(`datetime2(7)` is high-precision, but not infinitely so, and nothing in
the schema prevents two writes in the same instant). This package's own
`ORDER BY` accounts for that directly: `consent.consent_code,
consent.recorded_at_utc, consent.user_consent_id` -- the trailing,
excluded-from-output surrogate id makes the ordering fully deterministic
even under a genuine tie.

The paired verification script does not merely argue this from the DDL:
owner A's two events for one `consent_code` (accepted, then withdrawn)
are inserted against the **same captured `recorded_at_utc` variable**
on purpose, so the fixture actually exercises the tie against a real
engine rather than only a hypothetical one. Both rows are proven present
and individually correct in the captured output, confirming the
tiebreak works rather than merely compiling.

## Three existing keys, flipped, not new ones

The writer brief's own instruction: "flip the relevant excluded domains
to included with the new readers; preserve historical reasons in the
contract doc, not the dict." `services/account_export_domain_readers.py`
already carried all three keys, each excluded with this exact reason
(preserved here verbatim, as this program's own established practice for
a flipped domain requires -- the identical treatment
`PS-SETTINGS-EXPORT-007` gave `voice_photo`'s own prior reason):

> **`connection_preferences`** (recorded by `PS-SETTINGS-EXPORT-003`):
> "C0 marks this includable with truthful dormant-behavior labeling;
> this package builds no reader for it."

> **`notification_preferences`** (recorded by `PS-SETTINGS-EXPORT-003`):
> "C0 marks this includable after an owner-scoped/dormant field
> allowlist and truthful behavior labeling; this package builds no
> reader for it. Distinct from the excluded notifications inbox."

> **`consent_history`** (recorded by `PS-SETTINGS-EXPORT-003`):
> "C0 marks this includable in evidence-minimized form (excluding raw
> claims/excessive evidence); this package builds no reader for it."

This package **is** the package each of those three reasons deferred
to. All three dict entries now carry `disposition: "included"`,
`reason: None`, and one reader each; the historical reasons above are
preserved here, in this document, rather than left as dead prose inside
the Python dict where a future reader could mistake them for still
governing today's decision.

## Shared contract every one of the three procedures follows

- Accepts **only** `@UserKey nvarchar(300)`. No owner id, table name, or
  dynamic SQL built from any argument.
- Resolves identity with the **byte-identical** header every prior
  package in this program uses (see "Identity" above for why the full
  header, including the otherwise-unused `@ProfileId`, is preserved).
- Filters its one claimed table by `user_id = @UserId` -- never
  `owner_profile_id`, which none of the three tables has.
- Returns **only** an explicit, hand-picked column list -- never
  `SELECT *`.
- Orders its result set deterministically (see each table's own
  "Ordering" note below).
- Returns the read window as two trailing columns on the single content
  result set -- identical mechanism to every prior package.
- Contains **no transaction control of any kind**, no write, and no
  nested `EXEC`/dynamic SQL.
- Never selects `row_version` -- **none of the three tables has one**.
- No content-level join: every reader's total `JOIN dbo.` count is
  exactly 1, the identity header's own join to `dbo.app_users`.

### `dbo.connection_preferences` -> `usp_ReadAccountExportConnectionPreferenceForOwner`

**Allowlist (5 content fields, plus the dormant-feature label):**
`discovery_opt_in`, `goal_matching_opt_in`, `recruiter_discovery_opt_in`,
`discoverable_audience`, `updated_at_utc`.

**Exclusions:** `user_id` (standard).

**Joins:** none beyond the identity header's own.

**Ordering:** `preference.user_id` -- `PK_connection_preferences
(user_id)` alone guarantees at most one row per owner, so this mirrors
`usp_ReadAccountExportAccountForOwner`'s own "order by an excluded
internal id" idiom exactly, on an already-trivially-deterministic
single-row result.

**No value-based predicate on `discoverable_audience`.** Unlike
`opportunity_slates.visibility` or `capture_media_sources.source_type`
elsewhere in this program, this reader does not filter rows by any
value of `discoverable_audience` -- it returns whatever value the
member's single row carries, whatever that is. `CK_connection_preferences_audience`
bounds the column to four known values (`private`, `connections`,
`recruiter`, `public`); none is treated as more or less exportable than
another.

### `dbo.notification_preferences` -> `usp_ReadAccountExportNotificationPreferenceForOwner`

**Allowlist (6 content fields, plus the dormant-feature label):**
`notification_type`, `in_app_enabled`, `email_enabled`,
`quiet_hours_start`, `quiet_hours_end`, `updated_at_utc`.

**Exclusions:** `user_id` (standard).

**Joins:** none beyond the identity header's own.

**Ordering:** `preference.notification_type` --
`PK_notification_preferences (user_id, notification_type)` makes
`notification_type` alone unique once `user_id` is fixed by the
`WHERE` predicate.

**A legitimately empty domain.** As established above, no writer
anywhere populates this table; a real export for any member returns
zero rows today. This is disclosed here and pinned by a dedicated
adapter test
(`test_notification_preference_legitimately_empty_result_is_not_an_error`)
proving the adapter reports a clean, non-error empty read (using its own
documented fallback read-window) for this specific, expected case --
not merely for the generic "unresolved identity" empty case every
reader in this program already covers. (Corrected in the
independent-review round: the test as first written modeled the
description-less unresolved-identity cursor shape, so it did not yet
exercise the distinct resolved-owner-with-empty-table shape this
paragraph describes; it now drives the adapter with a real
nine-column result description and zero rows, making this claim true
by execution rather than by intent.)

### `dbo.user_consents` -> `usp_ReadAccountExportUserConsentForOwner`

See "Paper 3" above for the full allowlist, exclusions, ordering, and
no-dormant-label rationale.

## Interpretation notes

Recorded because the contract left this to judgment, not because it is
a defect:

1. **The dormant-feature label's exact wording
   (`dormant_not_yet_enforced`) is a judgment call the writer brief left
   open** ("pick precise, truthful wording"), not an instruction
   followed to the letter. See "Wording rationale" under Paper 2 above
   for the full reasoning a reviewer would need to independently
   re-verify or overturn it.
2. **`source_context`'s exclusion required concluding an ABSENCE of
   evidence (no writer exists), not tracing a positive procedure body**
   -- the inverse of the situation `PS-SETTINGS-EXPORT-007`'s own
   `deletion_capture_row_version` finding was in. This is the single
   decision in this package most likely to draw independent-review
   attention, because a reviewer could reasonably argue the column's
   name and bounded length are themselves enough evidence to include it
   is a "plain... label." The reasoning above defends the more
   conservative reading and names the exact re-judgment trigger (a
   future package's first real writer to this table) for whoever
   revisits it.
3. **The connection-preferences fixture updates an existing,
   auto-seeded row rather than inserting one**, in the paired
   verification script -- a direct consequence of `PK_connection_preferences
   (user_id)` and the `usp_UpsertAppUserFromAuth` seed already having
   run for every synthetic owner by the time the fixture section
   executes. An `INSERT` there would fail the primary key, not merely
   be redundant; this is disclosed as a structural fact about the
   fixture, not a workaround.
4. **The same-timestamp tie in the consent fixture is deliberate
   stress-testing, not an authoring accident** -- see "A deliberate
   same-timestamp tie" above.

## Grant model

Identical to every prior package in this program: the governed apply
identity holds `db_ddladmin` only and cannot `GRANT EXECUTE`; no
`GRANT`, `CREATE ROLE`, `CREATE USER`, or `sp_addrolemember` statement
appears anywhere in this migration. The intended production grant --
`EXECUTE` on these three procedures for the existing web-app principal
role -- is a separate, later, administrator-run authority operation,
not created here and not authorized by a repository merge of this file.
Design only; nothing applied.
