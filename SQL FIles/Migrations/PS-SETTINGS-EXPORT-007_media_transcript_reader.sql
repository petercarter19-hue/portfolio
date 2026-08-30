/* ============================================================
   PS-SETTINGS-EXPORT-007 - account export Voice/Photo media and
   transcript reader

   Read-only, owner-scoped SQL reader procedures for EXACTLY the C0
   V1-matrix "voice_photo" row (docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/
   C0_ACCOUNT_EXPORT_ARCHITECTURE.md), executing the owner's accepted
   "Paper 1" ruling: the member's own Voice/Photo capture FACTS and the
   member's OWN TRANSCRIPTS over exactly five tables --
   dbo.voice_media_sources, dbo.voice_transcription_attempts,
   dbo.voice_capture_links, dbo.capture_media_sources,
   dbo.capture_media_links -- one procedure per table, five total. This
   migration creates ONLY procedures. It creates no table, no trigger, no
   index, and writes nothing anywhere except its own ledger row.

   RAW MEDIA BYTES NEVER LIVE IN SQL -- A STRUCTURAL FACT, NOT A FIELD
   DECISION. PS-VOICE-001''s own header: "the application stores original
   audio in private Blob Storage." PS-CAPTURE-MEDIA-001''s own header:
   "Original bytes stay private and unavailable until Defender reports
   clean." Every one of the five tables below stores only a metadata
   row: a blob LOCATOR (excluded, see below), never the bytes
   themselves. There is therefore no "raw bytes" column anywhere in this
   migration''s scope to include or exclude -- the boundary is structural,
   not a judgment call.

   HARD EXCLUSIONS, CANARIED BY THE PAIRED VERIFICATION SCRIPT. Four
   categories, each with a directive category tag, found on the columns
   listed:
     STORAGE_LOCATOR (every blob_name/original_blob_name/
       derivative_blob_name column, and any container/path column) --
       voice_media_sources.blob_name; capture_media_sources.
       original_blob_name/derivative_blob_name.
     CONTENT_DIGEST (every sha256/digest column) --
       voice_media_sources.sha256_digest; capture_media_sources.
       original_sha256_digest/derivative_sha256_digest.
     STORAGE_ETAG (every etag column) -- capture_media_sources.
       original_blob_etag/derivative_blob_etag. voice_media_sources has
       no etag column of any kind.
     PROVIDER_REFERENCE (provider_request_id and any vendor id) --
       voice_transcription_attempts.provider_request_id, the ASR
       vendor''s own request identifier.
   Plus the standard program set every reader in this program already
   applies: every internal integer id/surrogate, owner_profile_id (used
   only as a WHERE predicate, never selected), every actor/confirmed-by
   user id (created_by_user_id, deleted_by_user_id, confirmed_by_user_id),
   row_version, and MACHINERY columns -- disclosed individually, not a
   directive category:
     safe_error_code (voice_media_sources, voice_transcription_attempts,
       capture_media_sources) -- error-code plumbing for a failed
       operation, never member-authored content. A failed attempt/source
       still appears in its reader (see "Transcript nuance" below); only
       the error CODE itself is withheld.
     scan_result and scan_completed_at_utc (capture_media_sources) --
       Microsoft Defender''s own malware-scan verdict and its timestamp,
       operational security machinery, not a member fact. The two travel
       together: scan_completed_at_utc is intrinsically bound to
       scan_result (both populated or both null in lockstep on every row
       this program has observed), so it follows the same exclusion
       rather than the general timestamp-inclusion rule below.
     deletion_capture_row_version (voice_media_sources,
       capture_media_sources) -- a cleanup CLAIM TOKEN: PS-CAPTURE-MEDIA-
       001''s own usp_DeleteCapture writes the parent capture''s
       row_version here so usp_FinalizePhotoCaptureDeletion can later
       confirm the capture has not changed since deletion began
       ("capture.row_version = source.deletion_capture_row_version").
       Never member-authored content; extends this program''s existing
       idempotency-ledger/machinery precedent
       (PS-SETTINGS-EXPORT-006''s idempotency_key) to a second column.
     deleted_at_utc (voice_media_sources, capture_media_sources) --
       excluded not as a directive category but because it carries zero
       information for any row this migration''s WHERE clause ever
       returns: CK_voice_media_sources_live_payload and
       CK_capture_media_sources_original_payload both tie
       deleted_at_utc IS NULL to every non-deleted state and
       deleted_at_utc IS NOT NULL to state = ''deleted'' exclusively, and
       every reader below filters state <> ''deleted'' (see next
       section), so a returned row''s deleted_at_utc is always NULL by
       construction. Selecting an always-null column would be dead
       weight, not a disclosure risk.

   DELETED-STATE ROWS ARE PAYLOAD-NULLED, NEVER EXPORTED. Both source
   tables tie their entire live payload to state <> ''deleted'' via a
   CHECK constraint that nulls EVERY content column when state =
   ''deleted'' (CK_voice_media_sources_live_payload,
   CK_capture_media_sources_original_payload) -- an empty shell row
   (every field NULL except the opaque key, state, and timestamps) would
   tell the member nothing they do not already know from having deleted
   it, so both source readers filter state <> N''deleted'' explicitly,
   proved absent by a planted fixture row in the paired verification
   script. dbo.voice_capture_links and dbo.capture_media_links have no
   state column of their own, but each joins to its own source table and
   inherits the identical state <> N''deleted'' predicate on that join as
   defense in depth: PS-VOICE-001''s usp_FinalizeVoiceDraftDeletion and
   PS-CAPTURE-MEDIA-001''s usp_FinalizePhotoDraftDeletion both structurally
   REQUIRE "NOT EXISTS (SELECT 1 FROM dbo.voice_capture_links/
   capture_media_links WHERE source_id = source.source_id)" before a
   source may reach state = ''deleted'', so no live application code path
   can ever produce a link row whose source is deleted -- this
   migration''s own join predicate does not rely on that invariant
   holding forever, matching the "never trust the default" discipline
   PS-SETTINGS-EXPORT-005/006 already applied to columns that are
   CHECK-locked today. dbo.voice_transcription_attempts has no state
   value named "deleted" either; it inherits the identical predicate
   through its own join to dbo.voice_media_sources for the same reason.

   TRANSCRIPT NUANCE: WHICH ATTEMPTS THE MEMBER GETS, AND WHY. Every
   voice source can accumulate more than one dbo.voice_transcription_
   attempts row (UQ_voice_transcription_attempts_source_number keys on
   (source_id, attempt_number), not a single row per source), each
   passing through a state machine (queued -> processing -> succeeded OR
   failed) that CK_voice_transcription_attempts_result enforces exactly:
   provider_transcript IS NOT NULL only when state = ''succeeded'';
   completed_at_utc IS NOT NULL only once a state machine reaches
   ''succeeded'' or ''failed''; both are NULL while state IN (''queued'',
   ''processing''). This migration reads every attempt whose state IS
   ''succeeded'' OR ''failed'' -- every attempt that has CONCLUDED,
   equivalently every row where completed_at_utc IS NOT NULL -- and
   EXCLUDES every attempt still ''queued''/''processing''. Two
   independent reasons, not one:
     (1) A queued/processing attempt carries NO content column at all
         (provider_transcript, provider_request_id, and completed_at_utc
         are all structurally NULL for these two states per the CHECK
         above) -- there is nothing to export from that row today,
         mirroring this migration''s own deleted-row-filtering logic:
         both are "this row is not yet/no longer a settled fact,"
         applied at the state-machine level here instead of the
         deletion level.
     (2) An in-flight attempt is a live operational status, not a
         durable member fact -- it can flip to ''succeeded''/''failed'' or
         be superseded by usp_QueueVoiceTranscription''s own recovery-
         retry logic (which marks a stuck queued/processing attempt
         ''failed'' with safe_error_code = ''recovery_retry'' before
         creating the next attempt) at any moment after this reader
         returns. Exporting a snapshot of "processing" would be
         immediately stale in a way exporting a concluded attempt never
         is.
   A FAILED attempt IS included as a row (state, attempt_number, and
   every timestamp still export normally) -- only its safe_error_code is
   withheld (see the machinery exclusion above); "do not export
   failed-attempt error plumbing" governs the ERROR CODE column, not the
   fact that an attempt failed. EVERY concluded attempt is exported, not
   merely the one attempt actually linked to a confirmed capture via
   dbo.voice_capture_links.successful_attempt_id: a member may retry
   after a failure, or record more than one successful transcription
   attempt before confirming, and each one is the member''s own spoken
   words at that moment, independent of which single attempt eventually
   became a Capture. This is also non-overlapping with
   PS-SETTINGS-EXPORT-004''s existing dbo.captures reader
   (usp_ReadAccountExportCaptureForOwner), which already exports
   capture.body for every capture including voice/photo ones: that body
   is the member''s CONFIRMED, possibly-edited final text
   (usp_ConfirmVoiceCapture''s own @ApprovedBody parameter) -- a
   different fact from the raw provider_transcript this migration
   reads, even when the member accepted the transcript verbatim and the
   characters coincide.

   OUT-OF-SCOPE LINKAGE: capture_id IS EXCLUDED FROM BOTH LINK READERS,
   NOT RESOLVED. dbo.voice_capture_links.capture_id and dbo.
   capture_media_links.capture_id both reference dbo.captures, which is
   NOT one of this migration''s five claimed tables (it belongs to
   PS-SETTINGS-EXPORT-004''s own already-shipped "capture" domain).
   Unlike every ancestor-linkage column elsewhere in this migration
   (resolved to its parent''s own opaque key via an in-scope join), this
   FK is excluded outright rather than resolved by joining a sixth
   table -- the identical boundary PS-SETTINGS-EXPORT-004''s own header
   already drew for dbo.moment_placements.target_entity_id ("it does not
   point at one of this package''s claimed tables... this migration adds
   no dependency on [the owning migration] precisely because it never
   reads that table"). The cross-domain source-to-Capture identity is
   DEFERRED, exactly as that precedent deferred its own: no field the
   export emits today lets a member correlate a voice/photo source row
   to the specific Capture it became, and correcting that (if the owner
   ever wants it) is a future package''s decision, not a join this
   migration may quietly add.

   NOT EVERY BORDERLINE COLUMN WAS EXCLUDED -- JUDGMENT CALLS RECORDED.
     - capture_media_sources.source_type is INCLUDED and additionally
       used as an explicit WHERE predicate (source_type = N''photo'').
       CK_capture_media_sources_type hard-locks every row to ''photo''
       today, so the predicate is provably a no-op kept as
       never-trust-the-default discipline -- the identical treatment
       PS-SETTINGS-EXPORT-006 gave opportunity_slates.visibility even
       though its own CHECK constraint hard-locks the column too. If a
       future migration widens this table to another media type, this
       reader must not silently start returning it unreviewed.
     - voice_media_sources.verified_duration_milliseconds is INCLUDED
       even though it is NULL until a transcription attempt actually
       succeeds (usp_CompleteVoiceTranscription is the only writer): a
       null-until-verified column is still a plain member fact (the
       verified spoken-audio duration), not machinery, and the schema
       itself treats it exactly like client_duration_milliseconds
       (paired in the same CK range check).
     - Byte sizes (byte_length, original_byte_length,
       derivative_byte_length) and pixel dimensions (pixel_width,
       pixel_height) are INCLUDED per the writer brief''s own framing:
       plain facts about the member''s own media, not locators. None of
       them can be combined to reconstruct a blob name, digest, or etag.
     - voice_transcription_attempts.queued_at_utc/started_at_utc are
       INCLUDED alongside completed_at_utc: all three are lifecycle
       timestamps recording when the member''s own transcription attempt
       moved through the state machine, the identical "created/updated/
       confirmed timestamp" class this program already exports
       everywhere else, not machinery.

   Every procedure, identical in shape and discipline to every prior
   package in this program (most recently
   PS-SETTINGS-EXPORT-006_oppslate_reader.sql):
     - accepts ONLY @UserKey nvarchar(300) -- no owner id, no table name,
       no dynamic SQL built from any argument;
     - resolves identity internally, BYTE-IDENTICALLY across all five,
       exactly like every prior package''s readers: @UserKey -> an ACTIVE
       dbo.app_users row -> its ACTIVE dbo.member_profiles row. An
       unresolved identity RETURNs before any SELECT (no result set at
       all) -- the caller-side adapter treats that as zero rows, never
       an error;
     - filters every row by the resolved owner profile on EVERY joined
       table, never only the leaf: all five tables independently carry
       their own owner_profile_id column (confirmed by reading
       PS-VOICE-001''s and PS-CAPTURE-MEDIA-001''s own DDL, not assumed),
       so every reader below asserts owner_profile_id = @ProfileId on
       every table it touches -- the "owner predicate on every side"
       defense in depth PS-SETTINGS-EXPORT-004 introduced and
       PS-SETTINGS-EXPORT-006 extended to a four-level chain, applied
       here up to a three-table join (voice_capture_links);
     - replaces every internal integer id with the row''s own opaque
       *_key uniqueidentifier where the table has one (voice_media_
       sources.source_key, voice_transcription_attempts.attempt_key,
       capture_media_sources.source_key), plus the nearest in-scope
       ancestor''s opaque key for intra-export linkage. dbo.voice_capture_
       links and dbo.capture_media_links have NO opaque key column of
       their own (unlike every table above) -- their exported
       identifying tuple is the joined source''s own source_key alone,
       already unique per UQ_voice_capture_links_source/
       UQ_capture_media_links_source, the identical "no surrogate key
       manufactured for a column the schema does not have" treatment
       PS-SETTINGS-EXPORT-006 gave opportunity_saved_qualifications/
       opportunity_saved_evidence;
     - returns ONLY an explicit, hand-picked column list (never
       SELECT *), matching this package''s directive-trimmed allowlist
       exactly;
     - orders its result set deterministically: both top-level readers
       (voice_media_source, capture_media_source) order by their own
       created_at_utc then their own opaque key -- the "own timestamp,
       own key" idiom every top-level reader in this program uses. The
       transcription-attempt reader orders by its parent source''s
       created_at_utc then source_key first, then its own attempt_number
       (unique only WITHIN one source per
       UQ_voice_transcription_attempts_source_number), the identical
       parent-then-sequence reasoning PS-SETTINGS-EXPORT-004/006 already
       applied to their own version-history tables. Both link readers
       order by their joined source''s created_at_utc then source_key,
       since at most one link row can exist per source
       (UQ_voice_capture_links_source/UQ_capture_media_links_source);
     - returns a read window (SYSUTCDATETIME() captured at the top of
       the procedure as @ReadStartedAtUtc, and again inline in the
       content SELECT as read_ended_at_utc) as two TRAILING COLUMNS on
       the single content result set -- identical mechanism and
       rationale to every prior package;
     - contains NO transaction control of any kind -- no BEGIN
       TRANSACTION, COMMIT, ROLLBACK, or TRY/CATCH, and no nested EXEC or
       dynamic SQL of its own. Every procedure here is a single
       read-only SELECT, safe to call with a bare EXEC.

   Requires PS-VOICE-001 and PS-CAPTURE-MEDIA-001 -- the two migrations
   that create all five tables this package reads (voice_media_sources,
   voice_transcription_attempts, and voice_capture_links from
   PS-VOICE-001; capture_media_sources and capture_media_links from
   PS-CAPTURE-MEDIA-001). PS-AUTH-001 is named in the registry''s own
   requires list too, for the paired verification script''s
   usp_UpsertAppUserFromAuth dependency -- named here from the start,
   matching every package since PS-SETTINGS-EXPORT-003''s own gate round
   had to correct the identical omission after the fact. This migration''s
   own guards do not check for PS-AUTH-001 directly: every column they
   touch on dbo.app_users/dbo.member_profiles already exists as of
   PS-PLAT-000/PS-PLAT-002, predating PS-AUTH-001, identically to every
   prior package''s recorded reasoning for the same omission. This
   migration does not require PS-CAPTURE-001, PS-CAPTURE-002,
   PS-MOMENT-001, or PS-PLACEMENT-001 (PS-VOICE-001''s own prerequisites):
   it reads no column any of those migrations created, and PS-VOICE-001''s
   own ledger row already attests those were satisfied when PS-VOICE-001
   itself was gated. It does not require whatever migration creates
   dbo.captures either (PS-CAPTURE-001): this migration never reads that
   table, per the capture_id exclusion above.

   Grant model: identical to every prior package in this program. The
   governed apply identity holds db_ddladmin only and cannot GRANT
   EXECUTE; no GRANT, CREATE ROLE, CREATE USER, or sp_addrolemember
   statement appears anywhere in this file. The intended production
   grant -- EXECUTE on these five procedures for the existing web-app
   principal role -- is a separate, later, administrator-run authority
   operation, not created here and not authorized by a repository merge
   of this file.

   THROW range: 58800-58899 (this migration; the rollback file continues
   within the same block at 58812). Verified clear of every sibling
   migration/rollback/verification file''s range: the highest prior THROW
   number anywhere under SQL FIles/ is 58753
   (PS-SETTINGS-EXPORT-006_oppslate_reader_isolation_verify.sql).

   No production apply is authorized by this file. No container, worker,
   schedule, or UI is created or implied.

   Rollback: PS-SETTINGS-EXPORT-007_media_transcript_reader_rollback.sql
   Verification: ../Verification/PS-SETTINGS-EXPORT-007_media_transcript_reader_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 58800, 'PS-SETTINGS-EXPORT-007 requires the migration ledger.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-VOICE-001')
        THROW 58801, 'PS-VOICE-001 must be applied before PS-SETTINGS-EXPORT-007.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK) WHERE migration_id = N'PS-CAPTURE-MEDIA-001')
        THROW 58802, 'PS-CAPTURE-MEDIA-001 must be applied before PS-SETTINGS-EXPORT-007.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
        THROW 58803, 'The PeerSlate identity and profile foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'active') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'profile_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'user_id') IS NULL
       OR COL_LENGTH(N'dbo.member_profiles', N'active') IS NULL
        THROW 58804, 'The PeerSlate identity or profile columns are incompatible.', 1;

    IF OBJECT_ID(N'dbo.voice_media_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.voice_transcription_attempts', N'U') IS NULL
       OR OBJECT_ID(N'dbo.voice_capture_links', N'U') IS NULL
        THROW 58805, 'The Voice Capture schema is missing.', 1;

    IF COL_LENGTH(N'dbo.voice_media_sources', N'source_key') IS NULL
       OR COL_LENGTH(N'dbo.voice_media_sources', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.voice_media_sources', N'content_type') IS NULL
       OR COL_LENGTH(N'dbo.voice_media_sources', N'byte_length') IS NULL
       OR COL_LENGTH(N'dbo.voice_media_sources', N'locale') IS NULL
       OR COL_LENGTH(N'dbo.voice_media_sources', N'client_duration_milliseconds') IS NULL
       OR COL_LENGTH(N'dbo.voice_media_sources', N'verified_duration_milliseconds') IS NULL
       OR COL_LENGTH(N'dbo.voice_media_sources', N'state') IS NULL
       OR COL_LENGTH(N'dbo.voice_media_sources', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.voice_media_sources', N'updated_at_utc') IS NULL
        THROW 58806, 'The voice_media_sources columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.voice_transcription_attempts', N'attempt_key') IS NULL
       OR COL_LENGTH(N'dbo.voice_transcription_attempts', N'source_id') IS NULL
       OR COL_LENGTH(N'dbo.voice_transcription_attempts', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.voice_transcription_attempts', N'attempt_number') IS NULL
       OR COL_LENGTH(N'dbo.voice_transcription_attempts', N'state') IS NULL
       OR COL_LENGTH(N'dbo.voice_transcription_attempts', N'provider_transcript') IS NULL
       OR COL_LENGTH(N'dbo.voice_transcription_attempts', N'queued_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.voice_transcription_attempts', N'started_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.voice_transcription_attempts', N'completed_at_utc') IS NULL
        THROW 58807, 'The voice_transcription_attempts columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.voice_capture_links', N'source_id') IS NULL
       OR COL_LENGTH(N'dbo.voice_capture_links', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.voice_capture_links', N'successful_attempt_id') IS NULL
       OR COL_LENGTH(N'dbo.voice_capture_links', N'confirmed_at_utc') IS NULL
        THROW 58808, 'The voice_capture_links columns are incompatible.', 1;

    IF OBJECT_ID(N'dbo.capture_media_sources', N'U') IS NULL
       OR OBJECT_ID(N'dbo.capture_media_links', N'U') IS NULL
        THROW 58809, 'The Capture Media (Photo) schema is missing.', 1;

    IF COL_LENGTH(N'dbo.capture_media_sources', N'source_key') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'source_type') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'original_content_type') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'original_byte_length') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'derivative_content_type') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'derivative_byte_length') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'pixel_width') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'pixel_height') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'state') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'created_at_utc') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_sources', N'updated_at_utc') IS NULL
        THROW 58810, 'The capture_media_sources columns are incompatible.', 1;

    IF COL_LENGTH(N'dbo.capture_media_links', N'source_id') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_links', N'owner_profile_id') IS NULL
       OR COL_LENGTH(N'dbo.capture_media_links', N'confirmed_at_utc') IS NULL
        THROW 58811, 'The capture_media_links columns are incompatible.', 1;

    /* ============================================================
       READER 1: dbo.voice_media_sources (9 content columns; no parent)
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportVoiceMediaSourceForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                source.source_key,
                source.content_type,
                source.byte_length,
                source.locale,
                source.client_duration_milliseconds,
                source.verified_duration_milliseconds,
                source.state,
                source.created_at_utc,
                source.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.voice_media_sources AS source
            WHERE source.owner_profile_id = @ProfileId
              AND source.state <> N''deleted''
            ORDER BY source.created_at_utc, source.source_key;
        END;
    ');

    /* ============================================================
       READER 2: dbo.voice_transcription_attempts (8 content columns,
       plus the joined parent''s source_key for linkage). Owner predicate
       on both tables; PROVIDER_REFERENCE (provider_request_id) and
       MACHINERY (safe_error_code) excluded; only concluded attempts
       (state IN (''succeeded'', ''failed'')) are read -- see this file''s
       own header, "Transcript nuance".
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportVoiceTranscriptionAttemptForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                source.source_key,
                attempt.attempt_key,
                attempt.attempt_number,
                attempt.state,
                attempt.provider_transcript,
                attempt.queued_at_utc,
                attempt.started_at_utc,
                attempt.completed_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.voice_transcription_attempts AS attempt
            JOIN dbo.voice_media_sources AS source
              ON source.source_id = attempt.source_id
            WHERE attempt.owner_profile_id = @ProfileId
              AND source.owner_profile_id = @ProfileId
              AND source.state <> N''deleted''
              AND attempt.state IN (N''succeeded'', N''failed'')
            ORDER BY source.created_at_utc, source.source_key, attempt.attempt_number;
        END;
    ');

    /* ============================================================
       READER 3: dbo.voice_capture_links -- no content column of its
       own beyond confirmed_at_utc; parent linkage via the joined
       source''s source_key and the joined attempt''s attempt_key; owner
       predicate on all three tables; capture_id EXCLUDED (points at
       dbo.captures, outside this migration''s five-table scope -- see
       this file''s own header).
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportVoiceCaptureLinkForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                source.source_key,
                attempt.attempt_key,
                link.confirmed_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.voice_capture_links AS link
            JOIN dbo.voice_media_sources AS source
              ON source.source_id = link.source_id
            JOIN dbo.voice_transcription_attempts AS attempt
              ON attempt.attempt_id = link.successful_attempt_id
            WHERE link.owner_profile_id = @ProfileId
              AND source.owner_profile_id = @ProfileId
              AND attempt.owner_profile_id = @ProfileId
              AND source.state <> N''deleted''
            ORDER BY source.created_at_utc, source.source_key;
        END;
    ');

    /* ============================================================
       READER 4: dbo.capture_media_sources (11 content columns; no
       parent). source_type = N''photo'' asserted explicitly
       (never-trust-the-default, matching PS-SETTINGS-EXPORT-006''s
       opportunity_slates.visibility treatment) even though
       CK_capture_media_sources_type hard-locks it today.
       STORAGE_LOCATOR/CONTENT_DIGEST/STORAGE_ETAG and MACHINERY
       (scan_result, scan_completed_at_utc, safe_error_code,
       deletion_capture_row_version) excluded.
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCaptureMediaSourceForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                source.source_key,
                source.source_type,
                source.original_content_type,
                source.original_byte_length,
                source.derivative_content_type,
                source.derivative_byte_length,
                source.pixel_width,
                source.pixel_height,
                source.state,
                source.created_at_utc,
                source.updated_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.capture_media_sources AS source
            WHERE source.owner_profile_id = @ProfileId
              AND source.source_type = N''photo''
              AND source.state <> N''deleted''
            ORDER BY source.created_at_utc, source.source_key;
        END;
    ');

    /* ============================================================
       READER 5: dbo.capture_media_links -- no content column of its
       own beyond confirmed_at_utc; parent linkage via the joined
       source''s source_key; owner predicate on both tables; capture_id
       EXCLUDED (points at dbo.captures, outside this migration''s
       five-table scope -- see this file''s own header).
       ============================================================ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ReadAccountExportCaptureMediaLinkForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;

            DECLARE @ReadStartedAtUtc datetime2(7) = SYSUTCDATETIME();

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            IF @UserKey IS NOT NULL
                SELECT
                    @ProfileId = profile.profile_id,
                    @UserId = app_user.id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                source.source_key,
                link.confirmed_at_utc,
                @ReadStartedAtUtc AS read_started_at_utc,
                SYSUTCDATETIME() AS read_ended_at_utc
            FROM dbo.capture_media_links AS link
            JOIN dbo.capture_media_sources AS source
              ON source.source_id = link.source_id
            WHERE link.owner_profile_id = @ProfileId
              AND source.owner_profile_id = @ProfileId
              AND source.source_type = N''photo''
              AND source.state <> N''deleted''
            ORDER BY source.created_at_utc, source.source_key;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-007'
    )
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-SETTINGS-EXPORT-007',
            N'Read-only owner-scoped account-export Voice/Photo media and transcript readers: five @UserKey-only procedures over voice_media_sources, voice_transcription_attempts, voice_capture_links, capture_media_sources, and capture_media_links. Excludes every blob locator, content digest, storage etag, provider reference, and payload-nulled deleted row; includes the member''s own concluded transcription attempts (provider_transcript).',
            N'PeerSlate Bible and Roadmap v3.0'
        );

        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-SETTINGS-EXPORT-007"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
