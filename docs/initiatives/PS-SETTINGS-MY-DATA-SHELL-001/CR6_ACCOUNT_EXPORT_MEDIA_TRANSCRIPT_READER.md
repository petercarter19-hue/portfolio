# CR6 account export Voice/Photo media and transcript reader

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-MEDIA-TRANSCRIPT-READER-001`
**Slice:** Protected. Executes the owner's accepted "Paper 1" ruling: a
read-only, owner-scoped account-export reader for the member's own
Voice/Photo capture FACTS and the member's OWN TRANSCRIPTS.
**Depends on:** the lane claim's own enumerated contract
(`docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-MEDIA-TRANSCRIPT-READER-001.json`);
reads `PS-VOICE-001_voice_capture.sql` and
`PS-CAPTURE-MEDIA-001_photo_sources.sql` (both under
`SQL FIles/Migrations/proposed/`) in full as the schema baseline; reads
`CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md` and
`PS-SETTINGS-EXPORT-006_oppslate_reader.sql` as the closest structural
template (same package shape, gate-state conventions, deviation style);
reads `PS-SETTINGS-EXPORT-003..006`'s migrations/verifications/tests as
the house pattern; reads `tests/test_settings_export_capture_moment_readers.py`
and `PS-SETTINGS-EXPORT-004_capture_moment_readers.sql` as the
capture/moment overlap-check sibling.
**Status:** Candidate migration/rollback/verification/adapter/test files,
self-reviewed by the writer. **Nothing in this package runs in production.
No schema apply has been performed anywhere except by the manager's own
future gate. No account export exists, is available, or is usable by any
member today.**

## Decision

Five tables, one reader per table, no directive trim (this domain's own
directive is inclusion, not exclusion -- see "Mission framing" below):
`dbo.voice_media_sources`, `dbo.voice_transcription_attempts`,
`dbo.voice_capture_links`, `dbo.capture_media_sources`,
`dbo.capture_media_links`. All five are created by `PS-VOICE-001` (the
first three) and `PS-CAPTURE-MEDIA-001` (the last two), both living under
`SQL FIles/Migrations/proposed/` despite being applied in production per
`docs/governance/PRODUCTION_SCHEMA_STATE.md` (the same "gated: null in the
registry is not a claim about what a real database carries" fact CR4's own
`PS-OPPSLATE-*` migrations already established for this program). Five
procedures total, each with a paired Python adapter function in
`services/account_export_domain_readers.py`, grouped into the ALREADY
EXISTING `voice_photo` C0 matrix key -- flipped from `excluded` to
`included`, not a new key (see "voice_photo domain identity" below).

## Mission framing: this domain's own directive is inclusion

Every prior package in this program (`PS-SETTINGS-EXPORT-004`,
`PS-SETTINGS-EXPORT-006`) worked from an owner directive that TRIMMED an
otherwise-includable domain (excluding third-party text, evidence links,
responses, AI provenance). This package's own directive runs the other
way: the owner's accepted "Paper 1" ruling explicitly names
`provider_transcript` as member content that MUST be included ("it is
the member's own spoken words, the whole point of this package"). There
is no third-party content anywhere in these five tables to trim -- every
table is the member's own upload/scan/transcription pipeline, not a
record about someone else. The judgment calls in this package are
therefore about a different axis entirely: which METADATA columns are
locators/digests/machinery versus plain member facts, and which ROW
STATES (deleted, in-flight) are settled facts versus not-yet/no-longer
member content.

## Raw media bytes never live in SQL -- a structural fact

`PS-VOICE-001`'s own header: "the application stores original audio in
private Blob Storage." `PS-CAPTURE-MEDIA-001`'s own header: "Original
bytes stay private and unavailable until Defender reports clean." Every
one of the five tables stores only a metadata row: a blob LOCATOR
(excluded), never the bytes themselves. There is no "raw bytes" column
anywhere in this migration's scope to include or exclude -- this
boundary is structural, not a judgment call, and is stated here per the
mission's own explicit instruction to record it as such.

## Column-level judgment, table by table

### `dbo.voice_media_sources` -> `usp_ReadAccountExportVoiceMediaSourceForOwner`

**Source:** `dbo.voice_media_sources`, created by `PS-VOICE-001`.

**Allowlist (9 content fields):** `source_key`, `content_type`,
`byte_length`, `locale`, `client_duration_milliseconds`,
`verified_duration_milliseconds`, `state`, `created_at_utc`,
`updated_at_utc`.

**Exclusions and reasons:**

| Column | Category | Reason |
| --- | --- | --- |
| `source_id` | (standard) | Internal integer surrogate; never disclosed. |
| `owner_profile_id` | (standard) | Internal id, used only as the `WHERE` predicate. |
| `blob_name` | `STORAGE_LOCATOR` | The private Blob Storage path to the member's own audio. |
| `sha256_digest` | `CONTENT_DIGEST` | A content hash of the audio bytes. |
| `safe_error_code` | MACHINERY | Error-code plumbing for a failed upload/scan; see "Failed sources still appear" below. |
| `deletion_capture_row_version` | MACHINERY | A cleanup CLAIM TOKEN -- see "The cleanup-claim-token finding" below. |
| `created_by_user_id` | (standard) | Actor user id. |
| `deleted_by_user_id` | (standard) | Actor user id. |
| `deleted_at_utc` | (disclosed, not directive) | Always `NULL` for every row this reader returns -- see "Why `deleted_at_utc` itself is excluded" below. |
| `row_version` | (standard) | Not member-authored content; changes on every update. |

**Joins:** none (top-level table).

**Filter:** `state <> N'deleted'` -- see "Deleted rows are payload-nulled"
below.

**Ordering:** `source.created_at_utc, source.source_key` -- the "own
timestamp, own key" idiom every top-level reader in this program uses.

### `dbo.voice_transcription_attempts` -> `usp_ReadAccountExportVoiceTranscriptionAttemptForOwner`

**Source:** `dbo.voice_transcription_attempts`, created by `PS-VOICE-001`.

**Allowlist (8 content fields):** `source_key` (parent linkage),
`attempt_key`, `attempt_number`, `state`, `provider_transcript`,
`queued_at_utc`, `started_at_utc`, `completed_at_utc`.

**Exclusions and reasons:**

| Column | Category | Reason |
| --- | --- | --- |
| `attempt_id` | (standard) | Internal integer surrogate. |
| `source_id` (this table's own FK) | (standard) | Internal FK id; replaced in the output by the joined `source.source_key`. |
| `owner_profile_id` (this table's own) | (standard) | Internal id; used as one of the "every side" `WHERE` predicates, never selected. |
| `provider_request_id` | `PROVIDER_REFERENCE` | The ASR vendor's own request identifier. |
| `safe_error_code` | MACHINERY | "Do not export failed-attempt error plumbing" -- the brief's own words; see "Failed attempts still appear" below. |
| `row_version` | (standard) | Not member-authored content. |

**Joins:** `JOIN dbo.voice_media_sources AS source ON source.source_id =
attempt.source_id` -- owner predicate on **both** tables, plus
`source.state <> N'deleted'`.

**Row filter (the central judgment call of this package):** `attempt.state
IN (N'succeeded', N'failed')` -- see "Transcript nuance" below.

**Ordering:** `source.created_at_utc, source.source_key,
attempt.attempt_number` -- `attempt_number` is unique only **within** one
source (`UQ_voice_transcription_attempts_source_number`), so a flat
reader over every owner's attempts must group by the parent first.

#### Transcript nuance: which attempts the member gets, and why

`voice_transcription_attempts` holds a state machine (`queued` ->
`processing` -> `succeeded` OR `failed`) enforced exactly by
`CK_voice_transcription_attempts_result`: `provider_transcript` is
`NOT NULL` only when `state = 'succeeded'`; `completed_at_utc` is
`NOT NULL` only once a state machine reaches `succeeded` or `failed`;
both `provider_transcript` and `safe_error_code` are `NULL` while `state
IN ('queued', 'processing')`. There is also an immutability trigger
(`trg_voice_transcription_attempts_immutable_result`) locking
`provider_transcript`/`provider_request_id` once a `succeeded` result is
recorded.

This reader includes every attempt whose state IS `succeeded` OR
`failed` -- every attempt that has **concluded**, equivalently every row
where `completed_at_utc IS NOT NULL` -- and **excludes** every attempt
still `queued`/`processing`. Two independent reasons, not one:

1. A queued/processing attempt carries **no content column at all**
   (`provider_transcript`, `provider_request_id`, and `completed_at_utc`
   are all structurally `NULL` for these two states per the `CHECK`
   above) -- there is nothing to export from that row today. This
   mirrors this package's own deleted-row-filtering logic: both are
   "this row is not yet/no longer a settled fact," applied at the
   state-machine level here instead of the deletion level.
2. An in-flight attempt is a **live operational status**, not a durable
   member fact -- it can flip to `succeeded`/`failed`, or be superseded
   by `usp_QueueVoiceTranscription`'s own recovery-retry logic (which
   marks a stuck `queued`/`processing` attempt `failed` with
   `safe_error_code = 'recovery_retry'` before creating the next
   attempt), at any moment after this reader returns. Exporting a
   snapshot of "processing" would be immediately stale in a way
   exporting a concluded attempt never is.

**Failed attempts still appear as rows** -- only `safe_error_code` is
withheld. The instruction "do not export failed-attempt error plumbing"
is read here as governing the ERROR CODE column specifically, not as an
instruction to drop failed rows outright: a failed attempt's `state`,
`attempt_number`, and timestamps are still the truthful lifecycle record
of what happened, the same "state/lifecycle columns tell the member the
truth" principle this package applies to `voice_media_sources.state`
lower down. This reading is also the only one under which the specific
instruction is not vacuous: if failed rows were excluded entirely,
naming their error-code column specifically would have nothing to
govern.

**Every concluded attempt is exported, not merely the one linked to a
confirmed capture.** `dbo.voice_capture_links.successful_attempt_id`
identifies exactly one attempt per source (the one a member confirmed
into a Capture), but this reader does not filter down to only that one.
A member may retry after a failure, or record more than one successful
transcription before confirming; each is the member's own spoken words
at that moment, independent of which attempt eventually became a
Capture. This is also **deliberately non-overlapping** with
`PS-SETTINGS-EXPORT-004`'s existing `dbo.captures` reader
(`usp_ReadAccountExportCaptureForOwner`), which already exports
`capture.body` for every capture including voice/photo ones: that body
is the member's CONFIRMED, possibly-edited final text
(`usp_ConfirmVoiceCapture`'s own `@ApprovedBody` parameter) -- a
different fact from the raw `provider_transcript` this package reads,
even when the member accepted the transcript verbatim and the
characters coincide. A member's export can therefore legitimately show
a raw transcript here alongside the polished (or identical) Capture
body EXPORT-004 already exports -- that is the intended, disclosed
shape, not a duplication.

### `dbo.voice_capture_links` -> `usp_ReadAccountExportVoiceCaptureLinkForOwner`

**Source:** `dbo.voice_capture_links`, created by `PS-VOICE-001`.

**Allowlist (3 content fields -- see "A near-empty table, disclosed"
below):** `source_key` (identifying tuple and parent linkage),
`attempt_key` (cross-reference linkage), `confirmed_at_utc`.

**Exclusions and reasons:**

| Column | Category | Reason |
| --- | --- | --- |
| `voice_capture_link_id` | (standard) | Internal integer surrogate; never disclosed. |
| `source_id` | (standard) | Internal FK id; replaced by the joined `source.source_key`. |
| `owner_profile_id` (this table's own) | (standard) | Internal id. |
| `capture_id` | out-of-scope linkage | Points at `dbo.captures`, outside this package's five-table scope -- see "Out-of-scope linkage" below. |
| `successful_attempt_id` | (standard) | Internal FK id; replaced by the joined `attempt.attempt_key`. |
| `confirmed_by_user_id` | (standard) | Actor user id. |

**Joins:** `JOIN dbo.voice_media_sources AS source ON source.source_id =
link.source_id`, `JOIN dbo.voice_transcription_attempts AS attempt ON
attempt.attempt_id = link.successful_attempt_id` -- owner predicate on
**all three** tables, plus `source.state <> N'deleted'` (defense in
depth; see "Deleted rows" below).

**Ordering:** `source.created_at_utc, source.source_key` -- at most one
link row can exist per source (`UQ_voice_capture_links_source`), so
ordering by the joined source's own timestamp and key is already fully
deterministic.

**A near-empty table, disclosed rather than quietly folded away.**
`dbo.voice_capture_links` carries no content of its own beyond
`confirmed_at_utc` -- its entire purpose is linkage. This package still
builds its reader, per this program's own precedent for a genuinely
sparse table (`CR4`'s `opportunity_saved_evidence`, reduced to two
structural columns by its own directive), because the linkage itself
("this transcript became a Capture, and at this attempt/time") is a real
member fact distinct from anything the source or attempt readers already
carry.

**No opaque key of its own.** Unlike every table above, `dbo.
voice_capture_links` has no `*_key uniqueidentifier` column
(`voice_capture_link_id` is a bare `bigint IDENTITY`). Its exported
identifying tuple is the joined source's own `source_key` alone, already
unique per `UQ_voice_capture_links_source` (one link row per source, by
constraint). No surrogate key is manufactured for a column the schema
does not have -- the identical treatment `PS-SETTINGS-EXPORT-006` gave
`dbo.opportunity_saved_qualifications`/`dbo.opportunity_saved_evidence`.

### `dbo.capture_media_sources` -> `usp_ReadAccountExportCaptureMediaSourceForOwner`

**Source:** `dbo.capture_media_sources`, created by
`PS-CAPTURE-MEDIA-001`.

**Allowlist (11 content fields):** `source_key`, `source_type`,
`original_content_type`, `original_byte_length`,
`derivative_content_type`, `derivative_byte_length`, `pixel_width`,
`pixel_height`, `state`, `created_at_utc`, `updated_at_utc`.

**Exclusions and reasons:**

| Column | Category | Reason |
| --- | --- | --- |
| `source_id` | (standard) | Internal integer surrogate. |
| `owner_profile_id` | (standard) | Internal id, predicate only. |
| `original_blob_name` | `STORAGE_LOCATOR` | The private Blob Storage path to the member's own original photo. |
| `derivative_blob_name` | `STORAGE_LOCATOR` | The private Blob Storage path to the member's own safe derivative. |
| `original_sha256_digest` | `CONTENT_DIGEST` | A content hash of the original photo bytes. |
| `original_blob_etag` | `STORAGE_ETAG` | Blob Storage's own concurrency token for the original. |
| `derivative_sha256_digest` | `CONTENT_DIGEST` | A content hash of the derivative photo bytes. |
| `derivative_blob_etag` | `STORAGE_ETAG` | Blob Storage's own concurrency token for the derivative. |
| `scan_result` | MACHINERY | Microsoft Defender's own malware-scan verdict -- security operational machinery, not a member fact. |
| `scan_completed_at_utc` | MACHINERY | Bound to `scan_result`; see "The scan-result pairing" below. |
| `safe_error_code` | MACHINERY | Error-code plumbing for a failed upload/scan/processing step. |
| `deletion_capture_row_version` | MACHINERY | A cleanup CLAIM TOKEN -- see "The cleanup-claim-token finding" below. |
| `created_by_user_id` | (standard) | Actor user id. |
| `deleted_by_user_id` | (standard) | Actor user id. |
| `deleted_at_utc` | (disclosed, not directive) | Always `NULL` for every row this reader returns -- see below. |
| `row_version` | (standard) | Not member-authored content. |

**Joins:** none (top-level table).

**Filter:** `source_type = N'photo'` **and** `state <> N'deleted'`.

**Ordering:** `source.created_at_utc, source.source_key`.

**Judgment call: `source_type = 'photo'` is included AND asserted as an
explicit predicate.** `CK_capture_media_sources_type` hard-locks every
row to `'photo'` today, so the predicate is provably a no-op kept as
never-trust-the-default discipline -- the identical treatment
`PS-SETTINGS-EXPORT-006` gave `opportunity_slates.visibility` even
though its own `CHECK` constraint hard-locks the column too. If a future
migration widens this table to another media type, this reader must not
silently start returning it unreviewed. `source_type` itself is included
in the output as a plain member fact (today, always `"photo"`), matching
the parallel treatment `visibility` received in `CR4`.

**Judgment call: byte sizes and pixel dimensions are included.**
`original_byte_length`, `derivative_byte_length`, `pixel_width`, and
`pixel_height` are plain facts about the member's own media -- not
locators, digests, or etags, and none of them can be combined to
reconstruct one. Per the writer brief's own framing.

### `dbo.capture_media_links` -> `usp_ReadAccountExportCaptureMediaLinkForOwner`

**Source:** `dbo.capture_media_links`, created by
`PS-CAPTURE-MEDIA-001`.

**Allowlist (2 content fields):** `source_key` (identifying tuple and
parent linkage), `confirmed_at_utc`.

**Exclusions and reasons:**

| Column | Category | Reason |
| --- | --- | --- |
| `capture_media_link_id` | (standard) | Internal integer surrogate. |
| `source_id` | (standard) | Internal FK id; replaced by the joined `source.source_key`. |
| `owner_profile_id` (this table's own) | (standard) | Internal id. |
| `capture_id` | out-of-scope linkage | Points at `dbo.captures`, outside this package's five-table scope. |
| `confirmed_by_user_id` | (standard) | Actor user id. |

**Joins:** `JOIN dbo.capture_media_sources AS source ON source.source_id
= link.source_id` -- owner predicate on both tables, plus
`source.source_type = N'photo'` and `source.state <> N'deleted'`.

**Ordering:** `source.created_at_utc, source.source_key` -- at most one
link row can exist per source (`UQ_capture_media_links_source`).

**No opaque key of its own**, matching `dbo.voice_capture_links`'
precedent immediately above: the identifying tuple is the joined
source's own `source_key` alone, already unique per
`UQ_capture_media_links_source`.

## Cross-cutting findings

### The cleanup-claim-token finding

`deletion_capture_row_version` (on both source tables) is not obviously
machinery from its name alone, so it was traced through the actual
procedure bodies rather than assumed. `PS-CAPTURE-MEDIA-001`'s own
`usp_DeleteCapture` writes the parent CAPTURE's `row_version` into this
column when deletion begins
(`deletion_capture_row_version = @ExpectedRowVersion`);
`usp_FinalizePhotoCaptureDeletion` later reads it back only to confirm
the capture has not changed since
(`capture.row_version = source.deletion_capture_row_version`). This is
exactly a cleanup CLAIM TOKEN -- the writer brief's own named example --
never member-authored content, and it names the *capture's* concurrency
state, not the source's own. Excluded as MACHINERY, extending this
program's existing idempotency-ledger precedent
(`PS-SETTINGS-EXPORT-006`'s `idempotency_key`) to a second and third
package.

### The scan-result pairing

`scan_result` and `scan_completed_at_utc` were confirmed, by reading
every procedure that writes them (`usp_CreatePhotoSource`,
`usp_RecordPhotoScanResult`), to always travel together: both populated
or both left at their "not yet scanned" state in lockstep on every write
path this schema has. `scan_completed_at_utc` is therefore excluded
alongside `scan_result` rather than swept into the general
timestamp-inclusion rule (`created_at_utc`/`updated_at_utc` etc.) --
it is a timestamp of an internal antivirus operation, not a member
action.

### Why `deleted_at_utc` itself is excluded from output

Both source tables' own `CHECK` constraints
(`CK_voice_media_sources_live_payload`,
`CK_capture_media_sources_original_payload`) tie `deleted_at_utc IS
NULL` to every non-deleted state and `deleted_at_utc IS NOT NULL`
exclusively to `state = 'deleted'`. Since every reader filters `state <>
'deleted'` (see below), a returned row's `deleted_at_utc` is always
`NULL` by construction -- selecting an always-null column would be dead
weight, not a disclosure risk, so it is a disclosed (not directive)
exclusion distinct from the four hard categories.

### Deleted rows are payload-nulled, never exported

Both source tables tie their entire live payload to `state <> 'deleted'`
via a `CHECK` constraint that nulls EVERY content column when `state =
'deleted'` (`CK_voice_media_sources_live_payload`,
`CK_capture_media_sources_original_payload`) -- an empty shell row
(every field `NULL` except the opaque key, state, and timestamps) would
tell the member nothing they do not already know from having deleted it.
Both source readers filter `state <> N'deleted'` explicitly, proved
absent by a planted fixture row in the paired verification script.
`dbo.voice_capture_links` and `dbo.capture_media_links` have no state
column of their own, but each joins to its own source table and inherits
the identical `state <> N'deleted'` predicate on that join as **defense
in depth**: `PS-VOICE-001`'s `usp_FinalizeVoiceDraftDeletion` and
`PS-CAPTURE-MEDIA-001`'s `usp_FinalizePhotoDraftDeletion` both
structurally REQUIRE `NOT EXISTS (SELECT 1 FROM
dbo.voice_capture_links/capture_media_links WHERE source_id =
source.source_id)` before a source may reach `state = 'deleted'`, so no
live application code path can ever produce a link row whose source is
deleted -- this package's own join predicate does not rely on that
invariant holding forever, matching the "never trust the default"
discipline `PS-SETTINGS-EXPORT-005`/`006` already applied to columns
that are `CHECK`-locked today. `dbo.voice_transcription_attempts` has no
state value named "deleted" either; it inherits the identical predicate
through its own join to `dbo.voice_media_sources` for the same reason.

**Honest limitation:** the "link/attempt pointing at a deleted source"
scenario is defended structurally (the predicate is present and correct)
but is not separately fixture-proven in the verification script -- the
schema's own deletion-guard invariant makes it unreachable through any
real application code path, and constructing a synthetic row that
violates that invariant (bypassing every guard directly via `INSERT`)
was judged not to add proportional value over the two source-table
canary proofs the script already performs. If a future package ever
relaxes either finalize procedure's guard, this predicate -- and this
gap in fixture coverage -- should be revisited together.

### Out-of-scope linkage: `capture_id` is excluded, never resolved

Both `dbo.voice_capture_links.capture_id` and
`dbo.capture_media_links.capture_id` reference `dbo.captures`, which is
**not** one of this package's five claimed tables (it belongs to
`PS-SETTINGS-EXPORT-004`'s own already-shipped "capture" domain). Unlike
every ancestor-linkage column elsewhere in this package (resolved to its
parent's own opaque key via an in-scope join), this FK is excluded
outright rather than resolved by joining a sixth table -- the identical
boundary `PS-SETTINGS-EXPORT-004`'s own header already drew for `dbo.
moment_placements.target_entity_id` ("it does not point at one of this
package's claimed tables... this migration adds no dependency on [the
owning migration] precisely because it never reads that table"). The
cross-domain source-to-Capture identity is DEFERRED, exactly as that
precedent deferred its own (corrected in the independent-review round:
the original text here claimed the correlation was "already possible"
through EXPORT-004's capture reader, which is false -- the two domains'
outputs share no field, so no export field today lets a member match a
source row to the specific Capture it became; adding one, if the owner
ever wants it, is a future package's decision). This also keeps
`requires` clean: no dependency on whatever migration creates
`dbo.captures` is needed, because no column of it is ever read.

### `voice_photo` domain identity: an existing key, flipped, not a new one

The writer brief's own instruction: "your work replaces that exclusion
with an included domain; preserve the historical reason in your contract
doc, not in the dict." `services/account_export_domain_readers.py`
already carried a `"voice_photo"` entry, corrected once before by
`PS-SETTINGS-EXPORT-004` from `"unavailable"` to `"excluded"` with this
exact reason:

> "PS-VOICE-001/PS-CAPTURE-MEDIA-001 are applied in production
> (docs/governance/PRODUCTION_SCHEMA_STATE.md), but every
> media/transcript/hash/blob column is PS-SETTINGS-EXPORT-004's defining
> boundary and is excluded from every domain that package built (capture,
> moment). Voice/photo metadata and transcripts are deferred to a
> future, separately claimed media/evidence-decision reader package; this
> package builds no reader for them."

This package **is** that future package. The dict entry now carries
`disposition: "included"`, `reason: None`, and the five readers below;
the historical reason above is preserved here, in this document, rather
than left as dead prose inside the Python dict where a future reader
could mistake it for still governing today's decision.

### Overlap check against `PS-SETTINGS-EXPORT-004`

`PS-SETTINGS-EXPORT-004`'s own `usp_ReadAccountExportCaptureForOwner`
already reads `dbo.captures` unconditionally (no filter by
`capture_type`), so it already exports `capture.body` -- the CONFIRMED,
possibly-edited final text -- for voice and photo captures exactly as it
does for text ones. `PS-SETTINGS-EXPORT-004`'s own migration header
states its own boundary directly: "every content hash, checksum,
media/photo/voice/blob/file reference, transcript linkage, storage
locator, and URL to stored media is excluded from every allowlist
below... that boundary is recorded because it governs this package's
field decisions generally (and **binds the future voice/photo/media
reader packages**)." This package honors that boundary: it never reads
`dbo.captures`, `dbo.capture_revisions`, `dbo.moments`, or any of
`PS-SETTINGS-EXPORT-004`'s six tables, and its own output (raw
`provider_transcript`, media metadata, lifecycle facts) carries no
column `PS-SETTINGS-EXPORT-004` already exports. No double-export of the
same fact exists between the two packages.

## Shared contract every one of the five procedures follows

- Accepts **only** `@UserKey nvarchar(300)`. No owner id, table name, or
  dynamic SQL built from any argument.
- Resolves identity with the **byte-identical** header every prior
  package in this program uses (confirmed identical, not merely
  similar, across `PS-SETTINGS-EXPORT-003` through this package, by a
  dedicated cross-file test): `@UserKey` -> an **active** `dbo.app_users`
  row -> its **active** `dbo.member_profiles` row. An unresolved identity
  `RETURN`s before any `SELECT` -- no result set at all.
- Filters every row by the resolved owner profile **on every joined
  table, never only the leaf**: all five tables independently carry
  their own `owner_profile_id` column (confirmed by reading
  `PS-VOICE-001`'s and `PS-CAPTURE-MEDIA-001`'s own DDL, not assumed),
  extending the "owner predicate on every side" defense in depth
  `PS-SETTINGS-EXPORT-004`/`006` already established, up to a
  three-table join (`voice_capture_links`).
- Replaces every internal integer id with the row's own opaque `*_key
  uniqueidentifier` where the table has one, plus the nearest in-scope
  ancestor's opaque key for intra-export linkage. `voice_capture_links`
  and `capture_media_links` have **no opaque key column of their own**
  (see each table's own section above).
- Returns **only** an explicit, hand-picked column list -- never
  `SELECT *`.
- Orders its result set deterministically, parent-then-sequence where a
  parent exists (see each table's own "Ordering" note above).
- Returns the read window as two trailing columns on the single content
  result set -- identical mechanism to every prior package.
- Contains **no transaction control of any kind**, no write, and no
  nested `EXEC`/dynamic SQL.
- Never selects `row_version`, any actor/confirmed-by user id, or
  `deleted_at_utc`.

## Interpretation notes

Recorded because the contract left this to judgment, not because it is a
defect:

1. **The transcript-nuance decision (concluded attempts only) is the
   single decision in this package most likely to draw independent-review
   attention**, because the brief's own phrasing ("every attempt's
   transcript or only completed/confirmed ones") is genuinely ambiguous
   between several readings. The reading adopted here -- every CONCLUDED
   attempt (`succeeded` or `failed`), never an in-flight one, and never
   narrowed to only the one attempt a member happened to confirm -- is
   defended in full above with the exact `CHECK` constraint evidence a
   reviewer would need to re-verify it independently.
2. **`deletion_capture_row_version`'s classification as MACHINERY
   required tracing actual procedure bodies**, not just the column's
   schema type or name: it names the *parent capture's* concurrency
   token, not the source row's own, and is written/read only by the
   deletion-coordination pair of procedures. Recorded in full under "The
   cleanup-claim-token finding" above.
3. **`capture_id` is excluded on both link tables, not resolved**, even
   though every analogous ancestor-linkage column elsewhere in this
   package IS resolved to an opaque key. This is a deliberate scope
   boundary (dbo.captures is outside the five claimed tables), not an
   oversight or a missed opportunity to enrich the export -- see
   "Out-of-scope linkage" above, with the `PS-SETTINGS-EXPORT-004`
   `target_entity_id` precedent cited directly.
4. **`voice_capture_links` and `capture_media_links` carry almost no
   content of their own** (`confirmed_at_utc` plus linkage only). Built
   anyway, per this program's own precedent for a genuinely sparse table
   (`CR4`'s `opportunity_saved_evidence`), because the linkage fact
   itself has independent value.
5. **The deleted-source-linked-to-a-link-row scenario is defended but not
   fixture-proven** -- an honest, disclosed limitation, not a silent gap;
   see "Deleted rows are payload-nulled" above.

## Grant model

Identical to every prior package in this program: the governed apply
identity holds `db_ddladmin` only and cannot `GRANT EXECUTE`; no `GRANT`,
`CREATE ROLE`, `CREATE USER`, or `sp_addrolemember` statement appears
anywhere in this migration. The intended production grant -- `EXECUTE` on
these five procedures for the existing web-app principal role -- is a
separate, later, administrator-run authority operation, not created here
and not authorized by a repository merge of this file. Design only;
nothing applied.
