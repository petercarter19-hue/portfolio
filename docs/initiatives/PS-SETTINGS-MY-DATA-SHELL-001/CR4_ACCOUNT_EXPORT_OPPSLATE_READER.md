# CR4 account export Opportunity Slate reader

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-OPPSLATE-READER-001`
**Slice:** Protected, replacement package 4 -- the FINAL content reader of
the accepted 2026-08-29 reader topology -- after
`PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001` (package 1, main `cc5174da`),
`PS-SETTINGS-ACCOUNT-EXPORT-CAPTURE-MOMENT-READERS-001` (package 2, main
`1f701263`), and `PS-SETTINGS-ACCOUNT-EXPORT-WORKSHOP-READER-001` (package
3, main `7d6b0ea1`) were all independently reviewed and merged.
**Depends on:** the lane claim's own enumerated contract
(`docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-OPPSLATE-READER-001.json`);
reads `C0_ACCOUNT_EXPORT_ARCHITECTURE.md`'s V1 domain matrix ("Opportunity
Slate" row) as the allowlist starting point, TRIMMED by the owner's later
2026-08-29 directive (see "C0-versus-directive supersession" below); reads
all four `PS-OPPSLATE-001..004` migration files under
`SQL FIles/Migrations/proposed/` in full as the schema baseline; reads
`CR3_ACCOUNT_EXPORT_WORKSHOP_READER.md` and
`PS-SETTINGS-EXPORT-005_workshop_reader.sql` as the structural template
this package follows closely.
**Status:** Candidate migration/rollback/verification/adapter/test files,
self-reviewed by the writer. **Nothing in this package runs in production.
No schema apply has been performed anywhere except by the manager's own
future gate. No account export exists, is available, or is usable by any
member today.**

## Decision

Four tables, directive-trimmed, one reader per table:
`dbo.opportunity_slates`, `dbo.opportunity_saved_results`,
`dbo.opportunity_saved_qualifications`, `dbo.opportunity_saved_evidence`.
All four are created by `PS-OPPSLATE-003_opportunity_slate_os4.sql`
(applied in production per `docs/governance/PRODUCTION_SCHEMA_STATE.md`),
living under `SQL FIles/Migrations/proposed/` despite that. Four
procedures total, each with a paired Python adapter function in
`services/account_export_domain_readers.py`, grouped into one `DOMAINS`
entry matching the C0 matrix's own single row: `opportunity_slate` (4
readers). This package creates no table, no trigger, no index, no
container, no worker, no route, and no UI. It does not populate
`dbo.account_export_job_domains` or wire any reader into a worker.

## Table-by-table durability judgment (the writer brief's own instruction, performed against the schema)

The writer brief named an expectation ("saved-slate/results/
qualifications/evidence-class tables from 001-003 and the 004
replacement's durable member tables: `opportunity_source_identities`,
`opportunity_requirement_review_events`, `opportunity_member_takes`") and
explicitly instructed judging each table against the real schema --
durable member record vs. ephemeral working-session state vs.
third-party/source content -- rather than trusting that expectation. All
four `PS-OPPSLATE-001..004` files were read in full, table DDL and
procedure bodies both, before any allowlist decision below was made. The
result **contradicts the "expect" framing on one material point**,
recorded here in full because it changes this package's entire table
list.

### PS-OPPSLATE-001 (OS-1/OS-2) -- 8 tables, ALL ephemeral

`opportunity_working_sessions`, `opportunity_sources`,
`opportunity_source_versions`, `opportunity_source_reviews`,
`opportunity_source_concerns`, `opportunity_requirement_sets`,
`opportunity_requirement_set_versions`, `opportunity_requirement_statements`.
The migration's own header states the judgment directly: "a working
session is infrastructure. It is never listed, exported, projected, or
shared." Physically destroyed by `usp_PurgeExpiredOpportunityWorkingData`;
cascade-deleted by `usp_DeleteOpportunityWorkingSessionForOwner`. **Verdict:
ephemeral working-session state. Excluded whole.**

### PS-OPPSLATE-002 (OS-3) -- 4 tables, ALL ephemeral

`opportunity_analyses`, `opportunity_analysis_statements`,
`opportunity_analysis_citations`, `opportunity_responses`. Not inferred --
confirmed by reading the actual `DELETE ... FROM ... JOIN ... JOIN
@ExpiredSessions` statements `usp_PurgeExpiredOpportunityWorkingData`
issues against all four, on every purge call for every owner.
`PS-OPPSLATE-002`'s own header states outright: "the durable, versioned
record is OS-4's saved slate" -- i.e. OS-3 names its own successor as the
durable one, not itself. **Verdict: ephemeral working-session state.
Excluded whole.**

### PS-OPPSLATE-003 (OS-4) -- 4 tables, ALL durable -- the ONLY durable group in the schema

`opportunity_slates`, `opportunity_saved_results`,
`opportunity_saved_qualifications`, `opportunity_saved_evidence`. The
migration's own header leaves no ambiguity: "EVERYTHING ABOVE THIS LINE IS
EPHEMERAL... This is the first table group in this file that survives
expiry, survives the member deleting their working session, and survives
the source being replaced." None of the four carries a foreign key into
any OS-1/OS-2/OS-3 table; a saved result **copies** what it shows (source
text, qualification text, citation excerpts) rather than referencing the
ephemeral rows it was computed from, specifically so the working tables
can be purged with zero conditional retention logic. **Verdict: durable
member record. Read by this package -- the only tables it reads.**

### PS-OPPSLATE-004 ("the replacement") -- 3 new tables, ALL ephemeral, DESPITE the name

`opportunity_source_identities`, `opportunity_requirement_review_events`,
`opportunity_member_takes`. `PS-OPPSLATE-004` is a separate, parallel R1
shell architecture (owner decision 2026-08-11: replace, not evolve) that
ships **beside** `PS-OPPSLATE-001..003`, which stay production truth for
the legacy room forever; it alters nothing in them. This is the finding
that overturned the writer brief's own framing:

- `opportunity_requirement_review_events` and `opportunity_member_takes`
  are **shape only** -- `PS-OPPSLATE-004`'s own header: "Their PROCEDURES
  are deliberately NOT created by this migration... No R1 route or service
  touches either table." As of this writing, **no row can exist in either
  table under any real database**: nothing has ever written to them.
- All three are cascade-deleted by `PS-OPPSLATE-004`'s own takeover of
  `usp_PurgeExpiredOpportunityWorkingData`, read directly from the
  migration's own comments and executable SQL:
  > "`opportunity_member_takes` and `opportunity_requirement_review_events`
  > both hang off `opportunity_requirement_statements`, so both have to go
  > before it does" -- followed by an actual
  > `DELETE take_record FROM dbo.opportunity_member_takes AS take_record
  > JOIN dbo.opportunity_requirement_statements ... JOIN @ExpiredSessions
  > ...` statement, and the identical shape for
  > `opportunity_requirement_review_events`.
  > "`opportunity_source_identities` hangs off
  > `opportunity_source_versions`, so it has to go before the version
  > delete below" -- followed by the matching
  > `DELETE identity_record FROM dbo.opportunity_source_identities ...
  > JOIN @ExpiredSessions ...` statement.
- A table cascade-deleted by the same procedure that purges expired
  working-session infrastructure **is** working-session infrastructure,
  regardless of which migration file created it or what that file is
  named. The replacement architecture has not yet shipped its own durable
  save mechanism at all -- R1's own delegation brief: "Build NOTHING
  beyond R1: ... no requirement review, no alignment, no save/history."

**Verdict: ephemeral working-session state, exactly like every OS-1/OS-2
table, despite living in a migration titled "replacement." Excluded whole,
with this exact reasoning recorded (not silently folded into
`opportunity_slate` or omitted).** Today there is exactly one durable
Opportunity Slate save path in this schema -- OS-4 -- and only it is read
here.

`PS-OPPSLATE-USE-001` (`SQL FIles/Migrations/`, not `proposed/` -- outside
this package's declared `PS-OPPSLATE-001..004` reading baseline and
therefore not a dependency) was also re-read for safety: it adds one index
and one new procedure (`usp_GetOpportunitySlateUseForOwner`) over
`dbo.opportunity_saved_evidence` and holds no `ALTER TABLE` of any kind. It
changes no column this package reads and requires no guard here.

## C0-versus-directive supersession (explicit record)

C0's V1 domain matrix marked this row **"Included with provenance"**:
"Durable member records plus provenance and proposed/noncanonical status
where applicable." **The owner's later 2026-08-29 directive TRIMS that**:
AI/model provenance is now excluded pending a separate review. Where C0
said "with provenance," **the directive controls** and this package ships
**without** provenance. C0's disposition for this row is superseded on
that one point; every other aspect of C0's framing (durable member records,
not the legacy room's ephemeral working data) stands and is exactly what
the table-by-table judgment above independently re-derived from the
schema.

Four categories are HARD-EXCLUDED per the directive, each with a directive
category tag used consistently below and in the paired verification
script's canary proof:

| Category | Definition | Columns found carrying it |
| --- | --- | --- |
| `THIRD_PARTY_POSTING_TEXT` | Any column carrying source-document content authored by someone other than the member. | `opportunity_saved_results.source_text`, `opportunity_saved_qualifications.employer_text`, `opportunity_saved_evidence.covered_text` |
| `EVIDENCE_LINKS` | `evidence_item_id` and any evidence linkage, excluded even where the referenced evidence is the member's own Workshop record. | `opportunity_saved_evidence.evidence_kind`/`.evidence_key`/`.evidence_version`/`.evidence_title`/`.excerpt`, `opportunity_saved_qualifications.connected_evidence_title`/`.connected_evidence_version` |
| `RESPONSES` | The member's own response context to a qualification prompt, hard-excluded as its own category regardless of authorship, pending the same separate review. | `opportunity_saved_qualifications.response_kind`/`.response_text`/`.authored_via`/`.connected_evidence_title`/`.connected_evidence_version` (the last two doubly tagged, also `EVIDENCE_LINKS`) |
| `AI_MODEL_PROVENANCE` | Model names/ids, prompts, scores, confidence values, generation metadata. | `opportunity_saved_results.model_name`/`.prompt_contract_version`/`.saved_analysis_key` (the last added in the independent-review correction round -- see the note under the saved-result reader below) |

Two counts were deliberately **not** swept into `AI_MODEL_PROVENANCE`
despite sitting next to it, and are recorded here as the judgment calls
most likely to draw review attention:

- `opportunity_saved_results.evidence_considered_count` -- a plain count,
  not a name/id/prompt/score/confidence value. The schema's own comment on
  this exact column states it directly: "A count of the member's own
  inputs, not a measure of them." (In context the antecedent is the
  member's inputs; `PS-OPPSLATE-002` separately states `derived_status`
  "is not the model's opinion. It is COMPUTED by the application.")
  Included.
- `opportunity_saved_qualifications.citation_count` and `.derived_status`
  -- `PS-OPPSLATE-002`'s own header is explicit that `derived_status` "is
  COMPUTED by the application from the citations... and the
  member-confirmed AND/OR structure... There is deliberately no column
  anywhere in this file that a sentence about the member could be written
  into" (i.e. by the schema author's own design intent, application
  accounting, never a model opinion). `citation_count` is included
  alongside it because `CK_opportunity_saved_qualifications_citation_pair`
  ties the two together (`citation_count = 0` iff `derived_status =
  'not_enough_information'`); excluding one half of a CHECK-enforced pair
  while keeping the other would be an arbitrary split. Included.

## Shared contract every one of the four procedures follows

- Accepts **only** `@UserKey nvarchar(300)`. No owner id, table name, or
  dynamic SQL built from any argument.
- Resolves identity with the **byte-identical** header every prior package
  in this program uses: `@UserKey` -> an **active** `dbo.app_users` row ->
  its **active** `dbo.member_profiles` row. An unresolved identity
  `RETURN`s before any `SELECT` -- no result set at all.
- Filters every row by the resolved owner profile **on every joined
  table, never only the leaf**: all four tables independently carry their
  own `owner_profile_id` column (confirmed by reading `PS-OPPSLATE-003`'s
  own DDL, not assumed), so every reader asserts
  `owner_profile_id = @ProfileId` on every table it touches -- the "owner
  predicate on every side" defense in depth `PS-SETTINGS-EXPORT-004`
  introduced for `dbo.moment_sources`/`dbo.moment_placements` and
  `PS-SETTINGS-EXPORT-005` applied to `dbo.knowledge_item_versions`,
  extended here across a **four-level chain**
  (`opportunity_slates` -> `opportunity_saved_results` ->
  `opportunity_saved_qualifications` -> `opportunity_saved_evidence`).
- Also asserts `slate.visibility = N'private'` explicitly on **every**
  reader, including the three descendant readers (each joins all the way
  up to `opportunity_slates` for exactly this predicate) -- the identical
  "never trust the default" discipline `PS-SETTINGS-EXPORT-005` applied to
  `dbo.knowledge_items`, even though `CK_opportunity_slates_visibility`
  hard-locks the column today.
- Replaces every internal integer id with the row's own opaque
  `*_key uniqueidentifier` where the table has one
  (`opportunity_slates.slate_key`, `opportunity_saved_results.
  saved_result_key`), plus the nearest ancestor's opaque key for
  intra-export linkage where the table has none of its own.
  `opportunity_saved_qualifications` and `opportunity_saved_evidence` have
  **no opaque key column of their own** -- their identifying tuples are
  `(saved_result_key, ordinal)` and `(saved_result_key,
  saved_qualification_ordinal, ordinal)`, already unique per
  `UQ_opportunity_saved_qualifications_ordinal` and
  `UQ_opportunity_saved_evidence_ordinal`. No surrogate key is
  manufactured for a column the schema does not have.
- Returns **only** an explicit, hand-picked, directive-trimmed column
  list -- never `SELECT *`.
- Orders its result set deterministically, parent-then-sequence at every
  level (see each table's own "Ordering" note below).
- Returns the read window as two trailing columns on the single content
  result set -- identical mechanism to every prior package.
- Contains **no transaction control of any kind**, no write, and no
  nested `EXEC`/dynamic SQL.
- Never selects `row_version`, any actor/owner user id, or a soft-delete
  column -- **none of the four tables has one** (see "Note on deletion"
  below).

## Domain-by-domain contract

### `opportunity_slate` -- included (4 readers)

#### `dbo.opportunity_slates` -> `usp_ReadAccountExportOpportunitySlateForOwner`

**Source:** `dbo.opportunity_slates`, created by `PS-OPPSLATE-003`.

**Allowlist (5 content fields):** `slate_key`, `visibility`,
`current_save_version_number`, `created_at_utc`, `updated_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `opportunity_slate_id` | Internal integer surrogate; never disclosed. |
| `owner_profile_id` | Internal id, used only as the `WHERE` predicate. |
| `row_version` | Not member-authored content; changes on every update. |

**Joins:** none (one slate row per owner, enforced by
`UQ_opportunity_slates_owner`).

**Ordering:** `slate.created_at_utc, slate.slate_key` -- the "own
timestamp, own key" idiom every top-level reader in this program uses,
even though at most one row can exist per owner today.

**Note on `visibility` (forward-looking, matching CR3's own
independent-review finding for `dbo.knowledge_items`).**
`CK_opportunity_slates_visibility` hard-locks every row to `'private'`
today, so the reader's explicit predicate is provably a no-op kept as
never-trust-the-default discipline. If that CHECK is ever relaxed, a
member's non-private slate would silently vanish from their own export --
an export-completeness risk, not a privacy one. Whichever package relaxes
the constraint must revisit this predicate in the same motion.

#### `dbo.opportunity_saved_results` -> `usp_ReadAccountExportOpportunitySavedResultForOwner`

**Source:** `dbo.opportunity_saved_results`, created by `PS-OPPSLATE-003`.

**Allowlist (9 content fields):** `slate_key` (parent linkage),
`saved_result_key`, `save_version_number`, `source_version_number`,
`requirement_version_number`,
`evidence_considered_count`, `qualification_count`, `input_fingerprint`,
`saved_at_utc`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `opportunity_saved_result_id` | Internal integer surrogate. |
| `opportunity_slate_id` | Internal FK id; replaced in the output by the joined `slate.slate_key`. |
| `owner_profile_id` (this table's own) | Internal id; used as one of the "every side" `WHERE` predicates, never selected. |
| `source_text` | **`THIRD_PARTY_POSTING_TEXT`** -- "the confirmed employer wording as the member accepted it, copied verbatim" (`PS-OPPSLATE-003`'s own header). |
| `model_name` | **`AI_MODEL_PROVENANCE`**. |
| `prompt_contract_version` | **`AI_MODEL_PROVENANCE`**. |
| `saved_analysis_key` | **`AI_MODEL_PROVENANCE`** -- excluded in the independent-review correction round, reversing this package's original keep. It IS an id: a `uniqueidentifier` naming which AI analysis run produced the save, squarely inside the category's own "Model names/ids" definition. The original keep rested on the inaccurate premise that it was not an id; the review also noted its member-readable export value is nil, because the run it names is ephemeral and already purged. |
| `idempotency_key` | Not a directive category -- extends this program's own machinery-not-content precedent to a column: the migration's own header calls it "the idempotency ledger," a client-supplied replay/dedupe token, never read back by any member-facing surface. Same class of decision this program already made whole-table for `knowledge_item_save_requests`/`recruiter_question_save_requests`/`moment_save_requests`. |
| `saved_by_user_id` | Actor user id. |
| `row_version` | Not member-authored content. |

**Joins:** `JOIN dbo.opportunity_slates AS slate ON slate.
opportunity_slate_id = saved_result.opportunity_slate_id` -- owner
predicate on **both** tables, plus `slate.visibility = N'private'`.

**Ordering:** `slate.created_at_utc, slate.slate_key,
saved_result.save_version_number` -- `save_version_number` is append-only
and unique only **within** one slate
(`UQ_opportunity_saved_results_version UNIQUE (opportunity_slate_id,
save_version_number)`), so a flat reader over every owner's saves must
group by the parent first.

**Note on `input_fingerprint` (judgment call) and `saved_analysis_key`
(reversed).** `input_fingerprint` is INCLUDED: a one-way SHA-256 digest
the member's own currency check depends on (equal means "Current,"
different means "Reanalysis required" -- the locked "currency is a
separate truth from savedness" rule); it is not a name, id, prompt,
score, or evidence reference, and it cannot be reversed to reveal
excluded content. `saved_analysis_key` was originally kept alongside it
on the premise that "neither is a name, id, prompt, score, or evidence
reference" -- the independent review found that premise inaccurate
(`saved_analysis_key` IS an id, a generation-run `uniqueidentifier`
inside `AI_MODEL_PROVENANCE`'s own "Model names/ids" definition), and
the correction round EXCLUDED it; see its row in the exclusions table
above. This paragraph originally argued for keeping both and is
preserved in corrected form rather than silently rewritten, because the
reversal is itself part of this package's record.

#### `dbo.opportunity_saved_qualifications` -> `usp_ReadAccountExportOpportunitySavedQualificationForOwner`

**Source:** `dbo.opportunity_saved_qualifications`, created by
`PS-OPPSLATE-003`.

**Allowlist (4 content fields):** `saved_result_key` (parent linkage,
this table's exported identifying key -- see below), `ordinal`,
`statement_class`, `derived_status`, `citation_count`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `opportunity_saved_qualification_id` | Internal integer surrogate. |
| `opportunity_saved_result_id` | Internal FK id; replaced in the output by the joined `saved_result.saved_result_key`. |
| `owner_profile_id` (this table's own) | Internal id. |
| `employer_text` | **`THIRD_PARTY_POSTING_TEXT`** -- "the employer's own wording for this statement." |
| `response_kind` | **`RESPONSES`**. |
| `response_text` | **`RESPONSES`** -- the member's own free-text answer, hard-excluded as a category regardless of authorship, pending the owner's separate review. |
| `authored_via` | **`RESPONSES`** -- provenance of the response payload. |
| `connected_evidence_title` | **`RESPONSES`** and **`EVIDENCE_LINKS`** (doubly tagged). |
| `connected_evidence_version` | **`RESPONSES`** and **`EVIDENCE_LINKS`** (doubly tagged). |
| `row_version` | Not member-authored content. |

**Joins:** `JOIN dbo.opportunity_saved_results AS saved_result ...` and
`JOIN dbo.opportunity_slates AS slate ...` -- owner predicate on **all
three** tables, plus `slate.visibility = N'private'`.

**Ordering:** `slate.created_at_utc, slate.slate_key,
saved_result.save_version_number, qualification.ordinal` -- `ordinal` is
unique only **within** one saved result
(`UQ_opportunity_saved_qualifications_ordinal`), so every ancestor's own
sequence key must lead.

**Note on `statement_class`.** The CHECK constraint on this exact column
is the widest of the four saved-qualification classes precisely because
"this column is a copy of the member's own decision, not a rule the room
enforces" (`PS-OPPSLATE-003`'s own header, explaining why a member's
post-hoc reclassification is faithfully recorded rather than narrowed).
Included as the member's own fact.

**Note on `derived_status`/`citation_count`.** See
"C0-versus-directive supersession" above -- both are application-computed
accounting, never a model opinion, per the schema author's own explicit
design-intent comment.

#### `dbo.opportunity_saved_evidence` -> `usp_ReadAccountExportOpportunitySavedEvidenceForOwner`

**Source:** `dbo.opportunity_saved_evidence`, created by `PS-OPPSLATE-003`.

**Allowlist (2 content fields -- see "A near-empty allowlist, disclosed"
below):** `saved_result_key` and `saved_qualification_ordinal` (parent
linkage, this table's exported identifying key), `ordinal`,
`clause_ordinal`.

**Exclusions and reasons:**

| Column | Reason |
| --- | --- |
| `opportunity_saved_evidence_id` | Internal integer surrogate. |
| `opportunity_saved_qualification_id` | Internal FK id; replaced in the output by the joined linkage. |
| `owner_profile_id` (this table's own) | Internal id. |
| `covered_text` | **`THIRD_PARTY_POSTING_TEXT`** -- "a verbatim span of the EMPLOYER's clause" (`PS-OPPSLATE-002`'s identical wording for the live-table sibling column). |
| `evidence_kind` | **`EVIDENCE_LINKS`**. |
| `evidence_key` | **`EVIDENCE_LINKS`** -- excluded even though it identifies the member's own Workshop record ("`evidence_key` and `evidence_version` identify the member's own Workshop record," `PS-OPPSLATE-003`'s own header); the directive names the whole category with no member-owned-evidence carve-out. |
| `evidence_version` | **`EVIDENCE_LINKS`**. |
| `evidence_title` | **`EVIDENCE_LINKS`**. |
| `excerpt` | **`EVIDENCE_LINKS`** -- bound intrinsically to the evidence reference it excerpts. |
| `row_version` | Not member-authored content. |

**Joins:** `JOIN dbo.opportunity_saved_qualifications AS qualification
...`, `JOIN dbo.opportunity_saved_results AS saved_result ...`, `JOIN
dbo.opportunity_slates AS slate ...` -- owner predicate on **all four**
tables, plus `slate.visibility = N'private'`.

**Ordering:** `slate.created_at_utc, slate.slate_key,
saved_result.save_version_number, qualification.ordinal,
evidence.ordinal` -- the full four-level chain, since `ordinal` is unique
only **within** one qualification (`UQ_opportunity_saved_evidence_ordinal`).

**A near-empty allowlist, disclosed rather than quietly reclassified.**
Every column carrying meaning to `THIRD_PARTY_POSTING_TEXT` or
`EVIDENCE_LINKS` is excluded from this table, leaving only two structural
position facts (`ordinal`, `clause_ordinal`) plus linkage. A member
reading this reader's output today learns "there were N evidence entries
for qualification Q, at clause positions [...]" with **no** information
about what evidence that was. This package still builds the reader, per
the writer brief's explicit instruction ("When a table is half
member-fact half third-party..., include ONLY the member-fact columns and
record each excluded column with its directive category") rather than
unilaterally reclassifying the whole domain as excluded because most of
one table's payload happens to be barred today. Recorded as an honest
limitation in the completion report, not hidden.

## Excluded tables (not built by this package)

Every table `PS-OPPSLATE-001`, `PS-OPPSLATE-002`, and `PS-OPPSLATE-004`
create is ephemeral working-session state (see the durability judgment
above for the full proof). None is silently folded into
`opportunity_slate` or omitted; the reasoning above is the recorded
disposition for all fifteen of them, grouped rather than repeated
per-table since the judgment and the proof are identical for every one:

- **PS-OPPSLATE-001 (8):** `opportunity_working_sessions`,
  `opportunity_sources`, `opportunity_source_versions`,
  `opportunity_source_reviews`, `opportunity_source_concerns`,
  `opportunity_requirement_sets`, `opportunity_requirement_set_versions`,
  `opportunity_requirement_statements`.
- **PS-OPPSLATE-002 (4):** `opportunity_analyses`,
  `opportunity_analysis_statements`, `opportunity_analysis_citations`,
  `opportunity_responses`.
- **PS-OPPSLATE-004 (3):** `opportunity_source_identities`,
  `opportunity_requirement_review_events`, `opportunity_member_takes`.

## `my_opportunities` -- re-verified, not merely left alone

C0 marks this row **"Unavailable/excluded"** with the required truth
boundary "do not conflate it with Opportunity Slate." This package's own
scope trigger ("`opportunity_slate` flips to included ... `my_opportunities`
stays excluded, verify its reason is still factual") required an actual
recheck, not an assumption that an unrelated flip left it untouched.
`PS-MYOPP-001` (`SQL FIles/Migrations/PS-MYOPP-001_canonical_foundation.sql`
-- outside `proposed/`, and the **only** applied My Opportunities
migration per the registry) was read: its own registry summary states
"Additive My Opportunities C2 shared-side canonical source-policy,
receipt, version, lifecycle, dedupe, attribution, requirement, event, and
rights-tombstone foundation. **No member-side objects.**" There is no
owner-scoped My Opportunities table any account-export reader could target
-- the existing reason remains factual, and the `DOMAINS` entry's text is
lightly extended (not changed in substance) to record this recheck.

## Every other C0 domain

Every domain neither this package nor `CR3` touches is unchanged from
`PS-SETTINGS-EXPORT-005`'s own recorded `DOMAINS` entries: `account`,
`profile`, `living_resume`, `career_skill_links`,
`profile_publication_foundation`, `own_publication_versions`, `capture`,
`voice_photo`, `moment`, `journal`, `workshop_my_knowledge`,
`workshop_knowledge_save_requests`, `community_authored_content`,
`connection_preferences`, `connection_records`, `notifications_inbox`,
`notification_preferences`, `consent_history`, `audit_events`,
`browser_local_interview_history`, `interview_telemetry`, `ai_proposals`,
`ask_pete_public`, `ask_pete_direct`, `projects`, `home`,
`file_evidence_metadata`, `indexes_caches_provider_backups`.

## Interpretation notes

Recorded because the contract left this to judgment, not because it is a
defect:

1. **The writer brief's own "expect" framing for `PS-OPPSLATE-004`'s
   three new tables was overturned by reading the schema, not assumed
   correct.** See the durability judgment section above in full; this is
   the single decision in this package most likely to draw
   independent-review attention, because it directly contradicts a
   sentence in the writer's own brief. The proof is textual and exact (the
   migration's own DELETE statements), not an inference from the word
   "replacement."
2. **`requires` names the full `PS-OPPSLATE-001/002/003` chain, not
   merely `PS-OPPSLATE-003`.** None of the four tables this package reads
   carries a foreign key into any OS-1/OS-2 table, so checking only
   `PS-OPPSLATE-003`'s ledger row would have been technically sufficient.
   The full chain is named anyway, following the in-family precedent
   `PS-OPPSLATE-003` and `PS-OPPSLATE-004` themselves already set (each
   checks/requires its own full ancestor chain by ledger row, never
   relying on transitivity alone) -- a disclosed, conservative,
   family-consistent choice, the same class of choice
   `PS-SETTINGS-EXPORT-005`'s own header recorded for including
   `PS-WORKSHOP-002` in its own `requires`.
3. **`opportunity_saved_qualifications` and `opportunity_saved_evidence`
   have no opaque key column of their own**, matching
   `dbo.knowledge_item_versions`' precedent from package 3: their
   identifying tuples are derived from their own UNIQUE constraints
   (`(saved_result_key, ordinal)` and `(saved_result_key,
   saved_qualification_ordinal, ordinal)`), and no surrogate key is
   manufactured for a column the schema does not have.
4. **`idempotency_key`'s exclusion is a precedent extension, not a
   directive category.** Recorded explicitly as its own reasoning class
   in the `opportunity_saved_results` exclusion table above, distinct from
   the four hard-exclusion categories, so a reviewer can evaluate it on
   its own terms rather than assuming it was directive-mandated.
5. **`opportunity_saved_evidence`'s near-empty allowlist** is a direct,
   disclosed consequence of the directive's two broadest categories
   (`THIRD_PARTY_POSTING_TEXT`, `EVIDENCE_LINKS`) both landing on the same
   table. Not a defect in this package's allowlist logic; a fact about
   what that one table's payload actually is.

## Grant model

Identical to every prior package in this program: the governed apply
identity holds `db_ddladmin` only and cannot `GRANT EXECUTE`; no `GRANT`,
`CREATE ROLE`, `CREATE USER`, or `sp_addrolemember` statement appears
anywhere in this migration. The intended production grant -- `EXECUTE` on
these four procedures for the existing web-app principal role -- is a
separate, later, administrator-run authority operation, not created here
and not authorized by a repository merge of this file. Design only;
nothing applied.
