# CR8 account export evidence-rule reader

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-EVIDENCE-RULE-READER-001`
**Slice:** Protected. The CLOSING reader package of the 2026-08-29/
2026-08-30 account-export reader topology. Executes the owner's
accepted 2026-08-30 Papers 4-7 rulings: adopts the safe-references-only
evidence rule and applies it now to the one reader it unblocks
(`dbo.career_skill_links`), and records four further durable rulings
(`ai_proposals`, the two publication-adjacent domains, and
`community_authored_content`) as updated `DOMAINS` reason strings.
**Depends on:** the lane claim's own enumerated contract
(`docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-EVIDENCE-RULE-READER-001.json`);
reads `PS-PLAT-006_living_resume_domain.sql` (`dbo.career_skill_links`
and `dbo.career_skills` in full) and `PS-PLAT-002_profiles_entities_access.sql`
/ `PS-PLAT-003_evidence_ai.sql` / `PS-PLAT-005_tenant_integrity.sql` (for
what `source_entity_id`/`evidence_item_id` actually point at and the
composite unique constraints that make those references possible) as
the schema baseline; reads `CR7_ACCOUNT_EXPORT_PREFERENCES_CONSENT_READER.md`
+ `CR7_OWNER_TECHNICAL_COMPLETION_REPORT.md` and
`CR6_ACCOUNT_EXPORT_MEDIA_TRANSCRIPT_READER.md` for package shape,
gate-state conventions, and deviation style; reads
`PS-SETTINGS-EXPORT-003` through `-008`'s own migrations/verifications/
tests as the house pattern; the core-readers package's own
`career_skill_links` exclusion (`SQL FIles/Migrations/PS-SETTINGS-EXPORT-003_core_readers.sql`'s
own header and `services/account_export_domain_readers.py`'s prior
reason string) as the exact boundary this package closes.
**Status:** Candidate migration/rollback/verification/adapter/test
files, self-reviewed by the writer. **Nothing in this package runs in
production. No schema apply has been performed anywhere except by the
manager's own future gate. No account export exists, is available, or
is usable by any member today.**

## Decision

One table, one reader: `dbo.career_skill_links`. Created by
`PS-PLAT-006_living_resume_domain.sql` (applied in production per
`docs/governance/PRODUCTION_SCHEMA_STATE.md`), the SAME migration that
created the eight tables `PS-SETTINGS-EXPORT-003` already reads. That
package left `career_skill_links` excluded for exactly one stated
reason: "its rows reference evidence_item_id, whose disclosure rules
are undecided." This package IS the evidence-decision package that
reason deferred to. One procedure,
`usp_ReadAccountExportCareerSkillLinkForOwner`, with a paired Python
adapter function `read_career_skill_link` in `services/account_export_domain_readers.py`,
flipping the EXISTING `career_skill_links` `DOMAINS` key from
`excluded` to `included` (see "One existing key, flipped, not a new
one" below).

## Papers 4-7 -- the safe-references-only evidence rule

The owner's ruling, stated once and binding program-wide from this
package forward: **titles, types, statuses, and dates may export.
Storage locators, container names, object keys, URLs, hashes/digests,
and verifier identity may NEVER export** -- from `dbo.career_skill_links`
or any evidence-adjacent table anywhere in this reader program, until a
dedicated future package performs the field-by-field review the rule
requires. This package adopts the rule as durable text (this document,
`services/account_export_domain_readers.py`'s own module docstring, and
`file_evidence_metadata`'s own updated `DOMAINS` reason -- see "The
other four rulings" below) and applies it immediately to the one reader
it unblocks.

## The reader

**Allowlist (4 member-authored content fields, plus the resolved
linkage and the derived flag):** `skill_key`, `relationship_type`,
`approval_status`, `strength_rank`, `evidence_linked`, `created_at_utc`.

**Exclusions and reasons:**

| Column | Category | Reason |
| --- | --- | --- |
| `skill_link_id` | (standard) | Internal integer surrogate; never disclosed. Also the reader's own trailing `ORDER BY` tiebreak -- excluded from output, used only as a sort key, the identical treatment every prior *ForOwner reader in this program gives its own excluded internal id. |
| `owner_profile_id` | (standard) | Internal id, used only as the `WHERE` predicate. |
| `skill_id` | (standard, resolved not disclosed) | Never selected raw. Resolved instead to the joined `dbo.career_skills` row's own `skill_key` -- see "The skill side" below. |
| `source_entity_id` | (standard, program-wide convention) | A `dbo.slate_entities` reference. Never resolved -- see "The source side" below. |
| `evidence_item_id` | `SAFE_REFERENCES_RULE` (`evidence_reference`) | A `dbo.evidence_items` reference. `dbo.evidence_items` is not a claimed table of this package, so resolving it to anything -- even an opaque key -- is out of scope. Excluded whole; a derived `evidence_linked` bit is disclosed instead -- see "The evidence side" below. |
| `created_by_user_id` | (standard) | Internal id, never disclosed by any reader in this program. |

## The skill side -- resolved to career_skills' own skill_key, never double-exported

`career_skill_links.skill_id` is a foreign key into `dbo.career_skills`
(`FK_career_skill_links_skill_owner FOREIGN KEY (skill_id,
owner_profile_id) REFERENCES dbo.career_skills(skill_id,
owner_profile_id)`, confirmed by reading `PS-PLAT-006`'s own DDL).
`career_skills` is already an included domain
(`usp_ReadAccountExportCareerSkillForOwner`, part of `living_resume`,
built by `PS-SETTINGS-EXPORT-003`), so this package resolves `skill_id`
to that table's own `skill_key` via a join, owner-predicated on BOTH
sides (`link.owner_profile_id = @ProfileId AND skill.owner_profile_id =
@ProfileId` -- defense in depth beyond the composite FK, the identical
discipline `PS-SETTINGS-EXPORT-003`'s own chapter-joined extension
readers already apply). This is the exact `chapter_id -> chapter_key`
intra-export-linkage idiom `usp_ReadAccountExportCareerExperienceForOwner`
already established, applied here for the first time to a link table
rather than a chapter extension. `skill_name`, `skill_summary`,
`visibility`, `featured`, and `display_order` are never re-selected --
`career_skills`' own reader already exports them; re-selecting them
here would double-export skill content.

Because the join carries `dbo.career_skills`' own `deleted_at_utc`
column, this reader also filters `skill.deleted_at_utc IS NULL` -- the
identical "extension content must not surface if its parent was
soft-deleted" widening `PS-SETTINGS-EXPORT-003`'s own header documents
for its own chapter-joined readers, applied here because
`career_skill_links` itself carries **no** `deleted_at_utc` or
`row_version` column of its own (confirmed by reading its own DDL).
Without this predicate, a soft-deleted skill's link would still surface
through this back door even though the skill itself would no longer
appear in the member's own `career_skill` export. The paired
verification script does not merely argue this from the DDL: it
soft-deletes a real skill mid-script and re-invokes the reader, proving
the back door is actually closed against a real engine.

## The source side -- excluded outright, never resolved, the same as every prior entity_id reference

`career_skill_links.source_entity_id` is a foreign key into
`dbo.slate_entities` (`FK_career_skill_links_source_owner`), the
polymorphic identity table underneath every Living Resume row
(`career_chapters`/`achievements`/`skills`/`timeline_events` each key
an `entity_id` off it). This whole reader program has never once
resolved an `entity_id` or `*_entity_id` reference to anything, anywhere:
`PS-SETTINGS-EXPORT-003`'s own ten readers forbid "chapter_id, entity_id,
any *_id surrogate column" outright as a program-wide rule, and
`PS-SETTINGS-EXPORT-004` drew the identical boundary for its own
`dbo.moment_placements.target_entity_id` ("`dbo.slate_entities` is not
one of `PS-SETTINGS-EXPORT-004`'s six claimed tables"). This package's
own reader never joins `dbo.slate_entities` and never selects
`source_entity_id` in any form, opaque or otherwise -- extending that
same program-wide boundary, not creating a new one. Because
`source_entity_id`'s exclusion is this older, separate, structural
convention -- not the subject of the owner's 2026-08-30 evidence ruling
-- it is classified in this package's own test file as a plain
`FORBIDDEN_FIELDS` member (the identical treatment `PS-SETTINGS-EXPORT-004`
gave `target_entity_id`), never folded into the `SAFE_REFERENCES_RULE`
category the evidence ruling itself created.

## The evidence side -- excluded outright; a derived evidence_linked flag disclosed instead

`career_skill_links.evidence_item_id` is a nullable foreign key into
`dbo.evidence_items` (`FK_career_skill_links_evidence_owner`).
`dbo.evidence_items` is **not** one of this package's claimed tables --
this migration creates no reader that selects from it, and never joins
it -- so resolving `evidence_item_id` to any `evidence_items` field,
even an opaque key, is out of scope by construction, the identical
reasoning that already excludes `source_entity_id` above. The owner's
safe-references-only rule's forbidden list (locators/keys/URLs/hashes/
verifier identity) is absolute, so even the raw `evidence_item_id`
surrogate integer is never selected.

**What IS disclosed:** a single derived bit, `evidence_linked`,
computed entirely from this package's own claimed column -- no join, no
`evidence_items` read of any kind:

```sql
CAST
(
    CASE WHEN link.evidence_item_id IS NOT NULL THEN 1 ELSE 0
    END AS bit
) AS evidence_linked,
```

**Why this is safe, and why it is the reading of the brief this package
adopts.** The writer brief framed the choice explicitly: "(a) exclude
the evidence reference entirely (a link row exports as 'a link to
evidence exists, with these member-authored facts')... evidence_items
is NOT a claimed table, so a join to it is out of scope -- which forces
(a) unless you find a compelling in-scope alternative." Option (a)'s
own description already names the outcome this package implements: the
export states that a link to evidence exists (a boolean fact) alongside
the member-authored facts the link itself carries. `evidence_linked`
delivers exactly that description literally -- it is not a locator, key,
hash, URL, or any fact about `evidence_items`' content; it is a
member-authored fact about the member's OWN row (did they say, when
they created this skill claim, that it is backed by evidence). This is
categorically closer to a "status" (explicitly named safe under the
rule) than to any forbidden category. No in-scope alternative to (a)
was found or attempted: `dbo.evidence_items` is genuinely never touched
by this migration, its reader, or (beyond planting FK-satisfying
fixture rows) its verification script.

**The table is practically empty today.** `dbo.evidence_items` has no
writer anywhere in this codebase (a repository-wide search for any
`INSERT`/`UPDATE` targeting it returns zero results) -- most members
export zero rows from this reader today, and every row that does exist
necessarily has `evidence_linked = 0` in practice, since no member has
ever been able to create a real evidence item to link against. This is
disclosed here and in the adapter module's own docstring, not hidden;
the reader still exists so the export's own manifest can truthfully
report this domain as included-but-usually-empty rather than silently
absent, and the adapter's own offline tests model the
resolved-owner-with-an-empty-table cursor shape precisely (the CR7
review's own F1 lesson: a real column description, zero rows -- never
the description-less shape an unresolved identity produces).

## Ownership

`dbo.career_skill_links` carries its own `owner_profile_id` column
directly (`bigint NOT NULL`, confirmed by reading `PS-PLAT-006`'s own
DDL) -- no inheritance through a parent row is required, unlike
`career_experiences`/`career_education`/etc., whose own
`owner_profile_id` column exists but whose PARENT join (`career_chapters`)
is what makes the chain meaningful. The joined `dbo.career_skills` row
is independently owner-predicated too, defense in depth beyond the
composite FK that already ties them to the same owner -- the identical
"predicate every joined table" discipline `PS-SETTINGS-EXPORT-003`
already applies.

## Ordering

`dbo.career_skill_links` has no opaque `*_key` column of its own and no
`display_order` (unlike `career_chapters`/`achievements`/`skills`/
`timeline_events`, which all carry one). The reader orders by
`link.created_at_utc, link.skill_link_id` -- chronological, then the
trailing excluded internal surrogate as the deterministic tiebreak, the
same "order by an excluded internal id" idiom
`usp_ReadAccountExportAccountForOwner` and
`usp_ReadAccountExportConnectionPreferenceForOwner` already use for a
table with no better tiebreak available.

## Shared contract this procedure follows

Identical to every prior package in this program: accepts only
`@UserKey nvarchar(300)`; resolves identity with the byte-identical
header (including the otherwise-unused member-profile join); filters by
the owner predicate on every joined table; returns only an explicit
column list; orders deterministically; returns the read window as two
trailing columns; contains no transaction control, write, or nested
`EXEC`/dynamic SQL; accepts no caller-selected owner or target. The one
structural difference from every prior "flip a domain to included"
package (`PS-SETTINGS-EXPORT-006`, `-007`, `-008`) is that this reader's
`JOIN dbo.` count is 2, not 1 -- the identity header's own join plus this
reader's own join to `dbo.career_skills` -- the first content-level join
a flip package in this program has needed.

## One existing key, flipped, not a new one

The writer brief's own instruction: "flip the relevant excluded domains
to included with the new readers; preserve historical reasons in the
contract doc, not the dict." `services/account_export_domain_readers.py`
already carried the `career_skill_links` key, excluded with this exact
reason (preserved here verbatim, as this program's own established
practice for a flipped domain requires -- the identical treatment
`PS-SETTINGS-EXPORT-007` gave `voice_photo`'s own prior reason):

> **`career_skill_links`** (recorded by `PS-SETTINGS-EXPORT-003`):
> "Deferred to a future evidence-decision package: rows reference
> evidence_item_id, whose disclosure rules (which evidence_items
> fields, if any, are safe to export) are undecided. Not read by this
> package."

This package **is** the package that reason deferred to. The dict
entry now carries `disposition: "included"`, `reason: None`, and one
reader; the historical reason above is preserved here, in this
document, rather than left as dead prose inside the Python dict where a
future reader could mistake it for still governing today's decision.
The module docstring's own historical paragraph describing
`PS-SETTINGS-EXPORT-003`'s original scope decision (including its own
mention of `career_skill_links`) is left untouched, exactly as
`PS-SETTINGS-EXPORT-004`'s own historical `voice_photo` paragraph was
left untouched when `PS-SETTINGS-EXPORT-007` later flipped that domain
-- it narrates history, not today's disposition. One comment
cross-reference (the `workshop_knowledge_save_requests` entry's own
precedent citation, which named `career_skill_links` as a currently-excluded
analogy) DID need a small correction, since that comment made a
present-tense claim about `career_skill_links`'s disposition that this
flip makes false; it now reads in the past tense for that specific
citation while leaving the still-accurate `target_entity_id` citation
untouched.

## The other four rulings this package records

The writer brief's mission asked for four ruling categories to be
recorded durably; because "publication" spans two existing `DOMAINS`
keys with different current dispositions
(`profile_publication_foundation`, `unavailable`;
`own_publication_versions`, `excluded`), this package updates **five**
reason strings in total, applying the publication ruling consistently
to both:

- **`ai_proposals`** (disposition unchanged, `excluded`): the owner
  ruled 2026-08-30 that there is nothing additional to export today. A
  member's own durable decisions arising from an AI proposal are
  already exported through the domain that stores the finished result
  (an approved career chapter or skill, for example); the proposal
  record itself is provider-facing process, not canonical member
  content. Revisit only if a live, member-facing AI proposal feature
  ships.
- **`profile_publication_foundation`** (disposition unchanged,
  `unavailable`): nothing exists to export here -- `PS-PROFILE-002` is
  registered but unapplied, so no Profile-native publication source
  table exists at all.
- **`own_publication_versions`** (disposition unchanged, `excluded`):
  nothing exists to export here today either, verified rather than
  assumed -- a repository-wide check performed for this package found no
  writer anywhere for `dbo.entity_publication_versions` or
  `dbo.entity_access_grants` (both created by the already-applied
  `PS-PLAT-002`), so no member has ever published anything through this
  schema.
- **Both publication domains**: the future publishing package must ship
  its own export reader in the same body of work that ships publication
  itself -- publication and its own export are not to be delivered
  separately.
- **`community_authored_content`** (disposition unchanged, `excluded`):
  the owner ruled this domain is honestly omitted from v1. The
  redaction C0 requires (removing every other member's body, identity,
  media, reaction, and relationship context) is not yet built. A
  future, dedicated "own words only" package is queued: the member's
  own authored text alone, with no thread context and nothing
  belonging to any other member.
- **`file_evidence_metadata`** (disposition unchanged, `excluded`): its
  reason now names the safe-references-only rule itself as the binding
  standard for whichever package first builds a reader for this
  domain, and names this package as the rule's origin.

None of these five domains gets a reader in this package. Each reason
is now durable owner-ruling text, pinned by a dedicated test in this
package's own test file, so a future package that touches one of them
without a genuine new owner ruling fails a test rather than silently
drifting.

## Interpretation notes

Recorded because the contract left this to judgment, not because it is
a defect:

1. **`evidence_linked`'s exact name and shape were a judgment call.**
   The brief described the OUTCOME ("a link row exports as 'a link to
   evidence exists'") without prescribing a column name. `evidence_linked`
   was chosen to match this schema's own plain, unprefixed adjectival
   boolean-naming convention (`current_role`, `featured`,
   `in_app_enabled`, `download_available` -- never a `has_`/`is_`
   prefix), and the `CAST(CASE WHEN ... THEN 1 ELSE 0 END AS bit)`
   idiom is copied verbatim from `PS-SETTINGS-EXPORT-001`'s own
   `download_available` column, the one other derived-boolean precedent
   in this program.
2. **`source_entity_id`'s classification (a plain `FORBIDDEN_FIELDS`
   member, not a `SAFE_REFERENCES_RULE` category) is a considered
   choice, not an oversight.** Its exclusion predates and is independent
   of the owner's 2026-08-30 evidence ruling; folding it into the new
   rule's own named category would misattribute a years-old,
   program-wide convention to a rule that did not create it.
3. **The verification script's back-door proof soft-deletes a real
   skill mid-script** rather than merely asserting the predicate's
   presence in the procedure text, because this program's own
   established discipline (`PS-SETTINGS-EXPORT-003`'s own soft-delete
   precision proof) treats "argued from the DDL" and "proven against a
   real engine" as different strengths of evidence, and the stronger
   one is preferred whenever the fixture cost is reasonable.
4. **`requires` conservatively names `PS-PLAT-003` even though it is
   already a transitive ancestor of `PS-PLAT-006`** (`PS-PLAT-006 ->
   005 -> 004 -> 003`), because this package's own verification script
   inserts real rows into `dbo.evidence_items` (created by `PS-PLAT-003`)
   to satisfy `career_skill_links`' own FK -- the identical "a
   registry-level requirement can cover the verification script's own
   direct dependency, not merely the migration body's guard checks"
   reasoning this program already uses for `PS-AUTH-001`.

## Grant model

Identical to every prior package in this program: the governed apply
identity holds `db_ddladmin` only and cannot `GRANT EXECUTE`; no
`GRANT`, `CREATE ROLE`, `CREATE USER`, or `sp_addrolemember` statement
appears anywhere in this migration. The intended production grant --
`EXECUTE` on this procedure for the existing web-app principal role --
is a separate, later, administrator-run authority operation, not
created here and not authorized by a repository merge of this file.
Design only; nothing applied.
