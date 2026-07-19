/* ============================================================
   PS-VOICE-001 ROLLBACK - guarded private Voice removal

   Rollback refuses destructive schema removal after any Voice row,
   later migration, external dependency, or protected-definition drift.
   It restores the pre-Voice Capture/Moment procedure contracts.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @VoiceAppliedAtUtc datetime2(7);
    SELECT @VoiceAppliedAtUtc = applied_at_utc
    FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
    WHERE migration_id = N'PS-VOICE-001';

    IF @VoiceAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1 FROM dbo.schema_migrations
           WHERE applied_at_utc > @VoiceAppliedAtUtc
       )
        THROW 52450, 'PS-VOICE-001 rollback refused: a later migration is present.', 1;

    IF OBJECT_ID(N'dbo.voice_media_sources', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.voice_media_sources)
        THROW 52451, 'PS-VOICE-001 rollback refused: voice_media_sources contains lifecycle or member data.', 1;
    IF OBJECT_ID(N'dbo.voice_transcription_attempts', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.voice_transcription_attempts)
        THROW 52452, 'PS-VOICE-001 rollback refused: voice_transcription_attempts contains provenance.', 1;
    IF OBJECT_ID(N'dbo.voice_capture_links', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.voice_capture_links)
        THROW 52453, 'PS-VOICE-001 rollback refused: voice_capture_links contains Capture relationships.', 1;

    DECLARE @ProcedureHashPropertyName sysname = N'PS_VOICE_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_CreateVoiceDraft'), (N'usp_FailVoiceUpload'),
        (N'usp_QueueVoiceTranscription'), (N'usp_MarkVoiceTranscriptionProcessing'),
        (N'usp_CompleteVoiceTranscription'), (N'usp_FailVoiceTranscription'),
        (N'usp_GetVoiceDraftForOwner'), (N'usp_GetVoiceMediaForOwner'),
        (N'usp_ConfirmVoiceCapture'), (N'usp_BeginVoiceDraftDeletion'),
        (N'usp_FinalizeVoiceDraftDeletion'), (N'usp_FinalizeVoiceCaptureDeletion'),
        (N'usp_ListCapturesForOwner'), (N'usp_GetCaptureForOwner'),
        (N'usp_DeleteCapture'), (N'usp_ExportCaptureForOwner');

    IF @VoiceAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM @ProtectedProcedures AS protected_procedure
           LEFT JOIN sys.procedures AS procedure_object
             ON procedure_object.schema_id = SCHEMA_ID(N'dbo')
            AND procedure_object.name = protected_procedure.procedure_name
           LEFT JOIN sys.extended_properties AS property
             ON property.class = 1
            AND property.major_id = procedure_object.object_id
            AND property.minor_id = 0
            AND property.name = @ProcedureHashPropertyName
           WHERE procedure_object.object_id IS NULL
              OR property.major_id IS NULL
              OR CONVERT(nvarchar(64), property.value) <>
                 CONVERT
                 (
                     nvarchar(64),
                     HASHBYTES('SHA2_256', OBJECT_DEFINITION(procedure_object.object_id)),
                     2
                 )
       )
        THROW 52454, 'PS-VOICE-001 rollback refused: protected procedure definition drift detected.', 1;

    DECLARE @VoiceTableIds TABLE (object_id int PRIMARY KEY);
    INSERT @VoiceTableIds (object_id)
    SELECT object_id FROM sys.tables
    WHERE object_id IN
    (
        OBJECT_ID(N'dbo.voice_media_sources'),
        OBJECT_ID(N'dbo.voice_transcription_attempts'),
        OBJECT_ID(N'dbo.voice_capture_links')
    );
    IF EXISTS
    (
        SELECT 1 FROM sys.foreign_keys
        WHERE referenced_object_id IN (SELECT object_id FROM @VoiceTableIds)
          AND parent_object_id NOT IN (SELECT object_id FROM @VoiceTableIds)
    )
        THROW 52455, 'PS-VOICE-001 rollback refused: a later table depends on Voice objects.', 1;
    IF EXISTS
    (
        SELECT 1 FROM sys.sql_expression_dependencies AS dependency
        WHERE dependency.referenced_id IN (SELECT object_id FROM @VoiceTableIds)
          AND dependency.referencing_id NOT IN
          (
              SELECT procedure_object.object_id
              FROM sys.procedures AS procedure_object
              JOIN @ProtectedProcedures AS protected_procedure
                ON protected_procedure.procedure_name = procedure_object.name
              WHERE procedure_object.schema_id = SCHEMA_ID(N'dbo')
          )
          AND dependency.referencing_id NOT IN (SELECT object_id FROM @VoiceTableIds)
          AND dependency.referencing_id NOT IN
          (
              SELECT schema_object.object_id
              FROM sys.objects AS schema_object
              WHERE schema_object.parent_object_id IN (SELECT object_id FROM @VoiceTableIds)
          )
          AND dependency.referencing_id <> OBJECT_ID(N'dbo.trg_voice_transcription_attempts_immutable_result')
    )
        THROW 52456, 'PS-VOICE-001 rollback refused: a later programmable object depends on Voice objects.', 1;

    IF OBJECT_ID(N'dbo.usp_CreateVoiceDraft', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_CreateVoiceDraft;
    IF OBJECT_ID(N'dbo.usp_FailVoiceUpload', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_FailVoiceUpload;
    IF OBJECT_ID(N'dbo.usp_QueueVoiceTranscription', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_QueueVoiceTranscription;
    IF OBJECT_ID(N'dbo.usp_MarkVoiceTranscriptionProcessing', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_MarkVoiceTranscriptionProcessing;
    IF OBJECT_ID(N'dbo.usp_CompleteVoiceTranscription', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_CompleteVoiceTranscription;
    IF OBJECT_ID(N'dbo.usp_FailVoiceTranscription', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_FailVoiceTranscription;
    IF OBJECT_ID(N'dbo.usp_GetVoiceDraftForOwner', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_GetVoiceDraftForOwner;
    IF OBJECT_ID(N'dbo.usp_GetVoiceMediaForOwner', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_GetVoiceMediaForOwner;
    IF OBJECT_ID(N'dbo.usp_ConfirmVoiceCapture', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_ConfirmVoiceCapture;
    IF OBJECT_ID(N'dbo.usp_BeginVoiceDraftDeletion', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_BeginVoiceDraftDeletion;
    IF OBJECT_ID(N'dbo.usp_FinalizeVoiceDraftDeletion', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_FinalizeVoiceDraftDeletion;
    IF OBJECT_ID(N'dbo.usp_FinalizeVoiceCaptureDeletion', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_FinalizeVoiceCaptureDeletion;

    /* Restore the PS-CAPTURE-002 list contract. */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListCapturesForOwner
            @UserKey nvarchar(300), @Take int = 50, @Archived bit = 0
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL THROW 52106, ''Authenticated user key is required.'', 1;
            IF @Take IS NULL SET @Take = 50;
            IF @Take < 1 SET @Take = 1;
            IF @Take > 100 SET @Take = 100;
            IF @Archived IS NULL SET @Archived = 0;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
            IF @ProfileId IS NULL THROW 52107, ''Authenticated owner profile not found.'', 1;
            SELECT TOP (@Take) capture.capture_key, capture.capture_type,
                COALESCE(latest_revision.body, capture.body) AS body,
                capture.body AS original_body, capture.visibility, capture.status,
                capture.active, COALESCE(latest_revision.revision_number, 0) AS revision_number,
                revision_count.revision_count, capture.created_at_utc, capture.updated_at_utc,
                capture.row_version
            FROM dbo.captures AS capture
            OUTER APPLY
            (
                SELECT TOP (1) revision.body, revision.revision_number
                FROM dbo.capture_revisions AS revision WHERE revision.capture_id = capture.capture_id
                ORDER BY revision.revision_number DESC
            ) AS latest_revision
            OUTER APPLY
            (
                SELECT COUNT(*) AS revision_count FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = capture.capture_id
            ) AS revision_count
            WHERE capture.owner_profile_id = @ProfileId AND capture.deleted_at_utc IS NULL
              AND ((@Archived = 0 AND capture.active = 1 AND capture.status = N''captured'')
                OR (@Archived = 1 AND capture.active = 0 AND capture.status = N''archived''))
            ORDER BY capture.updated_at_utc DESC, capture.capture_id DESC;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetCaptureForOwner
            @UserKey nvarchar(300), @CaptureKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            SELECT capture.capture_key, capture.capture_type,
                COALESCE(latest_revision.body, capture.body) AS body,
                capture.body AS original_body, capture.visibility, capture.status,
                capture.active, COALESCE(latest_revision.revision_number, 0) AS revision_number,
                revision_count.revision_count, capture.created_at_utc, capture.updated_at_utc,
                capture.row_version
            FROM dbo.captures AS capture
            OUTER APPLY
            (
                SELECT TOP (1) revision.body, revision.revision_number
                FROM dbo.capture_revisions AS revision WHERE revision.capture_id = capture.capture_id
                ORDER BY revision.revision_number DESC
            ) AS latest_revision
            OUTER APPLY
            (
                SELECT COUNT(*) AS revision_count FROM dbo.capture_revisions AS revision
                WHERE revision.capture_id = capture.capture_id
            ) AS revision_count
            WHERE capture.owner_profile_id = @ProfileId AND capture.capture_key = @CaptureKey
              AND capture.deleted_at_utc IS NULL
              AND ((capture.active = 1 AND capture.status = N''captured'')
                OR (capture.active = 0 AND capture.status = N''archived''));
        END;
    ');

    /* Restore the PS-MOMENT-001 deletion behavior, including source tombstones. */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DeleteCapture
            @UserKey nvarchar(300), @CaptureKey uniqueidentifier, @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @CaptureKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52114, ''Owner, capture, and expected version are required.'', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @CaptureId bigint;
                DECLARE @PreviousStatus nvarchar(30);
                SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
                FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
                SELECT @CaptureId = capture.capture_id, @PreviousStatus = capture.status
                FROM dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK)
                WHERE capture.owner_profile_id = @ProfileId AND capture.capture_key = @CaptureKey
                  AND capture.deleted_at_utc IS NULL AND capture.row_version = @ExpectedRowVersion
                  AND ((capture.active = 1 AND capture.status = N''captured'')
                    OR (capture.active = 0 AND capture.status = N''archived''));
                IF @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS int) AS deleted_revision_count,
                           CAST(NULL AS int) AS tombstoned_moment_source_count;
                    RETURN;
                END;
                DECLARE @RevisionCount int =
                    (SELECT COUNT(*) FROM dbo.capture_revisions WHERE capture_id = @CaptureId);
                DECLARE @MomentSourceCount int =
                    (SELECT COUNT(*) FROM dbo.moment_sources
                     WHERE owner_profile_id = @ProfileId AND capture_id = @CaptureId
                       AND source_state = N''available'');
                UPDATE dbo.moment_sources
                SET source_state = N''deleted'', source_deleted_at_utc = SYSUTCDATETIME(),
                    capture_revision_id = NULL, capture_id = NULL
                WHERE owner_profile_id = @ProfileId AND capture_id = @CaptureId
                  AND source_state = N''available'';
                IF @@ROWCOUNT <> @MomentSourceCount
                    THROW 52216, ''Capture source tombstones were not updated atomically.'', 1;
                DECLARE @AuditMetadata nvarchar(max) = CONCAT
                    (N''{"previous_status":"'', @PreviousStatus, N''","revision_count":'',
                     @RevisionCount, N'',"moment_source_tombstone_count":'', @MomentSourceCount, N''}'');
                DECLARE @AuditResult TABLE
                (
                    audit_event_id bigint, event_key uniqueidentifier,
                    occurred_at_utc datetime2(7), actor_user_id int,
                    actor_user_key_snapshot nvarchar(300), action_type nvarchar(200),
                    entity_type nvarchar(100), entity_key uniqueidentifier,
                    outcome nvarchar(30), request_id nvarchar(100), metadata_json nvarchar(max)
                );
                INSERT @AuditResult
                EXEC dbo.usp_AppendAuditEvent
                    @ActorUserId = @UserId, @ActorUserKeySnapshot = @UserKey,
                    @ActionType = N''capture.deleted'', @EntityType = N''capture'',
                    @EntityKey = @CaptureKey, @Outcome = N''success'', @MetadataJson = @AuditMetadata;
                DELETE dbo.capture_revisions WHERE capture_id = @CaptureId;
                DELETE dbo.captures WHERE capture_id = @CaptureId AND owner_profile_id = @ProfileId;
                IF @@ROWCOUNT <> 1 THROW 52115, ''Capture delete did not complete atomically.'', 1;
                COMMIT TRANSACTION;
                SELECT N''success'' AS outcome, @RevisionCount AS deleted_revision_count,
                       @MomentSourceCount AS tombstoned_moment_source_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ExportCaptureForOwner
            @UserKey nvarchar(300), @CaptureKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            DECLARE @ProfileId bigint;
            DECLARE @CaptureId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
              AND app_user.active = 1 AND profile.active = 1;
            SELECT @CaptureId = capture.capture_id FROM dbo.captures AS capture
            WHERE capture.owner_profile_id = @ProfileId AND capture.capture_key = @CaptureKey
              AND capture.deleted_at_utc IS NULL
              AND ((capture.active = 1 AND capture.status = N''captured'')
                OR (capture.active = 0 AND capture.status = N''archived''));
            SELECT capture.capture_key, capture.capture_type,
                COALESCE(latest_revision.body, capture.body) AS body,
                capture.body AS original_body, capture.visibility, capture.status,
                capture.active, COALESCE(latest_revision.revision_number, 0) AS revision_number,
                capture.created_at_utc, capture.updated_at_utc, revisions.revisions_json
            FROM dbo.captures AS capture
            OUTER APPLY
            (
                SELECT TOP (1) revision.body, revision.revision_number
                FROM dbo.capture_revisions AS revision WHERE revision.capture_id = capture.capture_id
                ORDER BY revision.revision_number DESC
            ) AS latest_revision
            OUTER APPLY
            (
                SELECT
                (
                    SELECT revision.revision_number, revision.body, revision.correction_note,
                           revision.corrected_at_utc
                    FROM dbo.capture_revisions AS revision WHERE revision.capture_id = capture.capture_id
                    ORDER BY revision.revision_number FOR JSON PATH
                ) AS revisions_json
            ) AS revisions
            WHERE capture.capture_id = @CaptureId AND capture.owner_profile_id = @ProfileId;
        END;
    ');

    /* Remove only the Voice fingerprint; retain and refresh Moment ownership of delete. */
    DECLARE @SharedProcedure sysname;
    DECLARE @SharedProcedures TABLE (procedure_name sysname PRIMARY KEY);
    INSERT @SharedProcedures VALUES
        (N'usp_ListCapturesForOwner'), (N'usp_GetCaptureForOwner'),
        (N'usp_DeleteCapture'), (N'usp_ExportCaptureForOwner');
    WHILE EXISTS (SELECT 1 FROM @SharedProcedures)
    BEGIN
        SELECT TOP (1) @SharedProcedure = procedure_name FROM @SharedProcedures ORDER BY procedure_name;
        IF EXISTS
        (
            SELECT 1 FROM sys.extended_properties
            WHERE class = 1 AND major_id = OBJECT_ID(N'dbo.' + @SharedProcedure, N'P')
              AND minor_id = 0 AND name = @ProcedureHashPropertyName
        )
            EXEC sys.sp_dropextendedproperty
                @name = @ProcedureHashPropertyName,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @SharedProcedure;
        DELETE @SharedProcedures WHERE procedure_name = @SharedProcedure;
    END;

    DECLARE @MomentHash nvarchar(64) = CONVERT
    (
        nvarchar(64),
        HASHBYTES('SHA2_256', OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_DeleteCapture', N'P'))),
        2
    );
    IF EXISTS
    (
        SELECT 1 FROM sys.extended_properties
        WHERE class = 1 AND major_id = OBJECT_ID(N'dbo.usp_DeleteCapture', N'P')
          AND minor_id = 0 AND name = N'PS_MOMENT_001_DEFINITION_HASH'
    )
        EXEC sys.sp_updateextendedproperty
            @name = N'PS_MOMENT_001_DEFINITION_HASH', @value = @MomentHash,
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'PROCEDURE', @level1name = N'usp_DeleteCapture';

    IF OBJECT_ID(N'dbo.trg_voice_transcription_attempts_immutable_result', N'TR') IS NOT NULL
        DROP TRIGGER dbo.trg_voice_transcription_attempts_immutable_result;
    IF OBJECT_ID(N'dbo.voice_capture_links', N'U') IS NOT NULL DROP TABLE dbo.voice_capture_links;
    IF OBJECT_ID(N'dbo.voice_transcription_attempts', N'U') IS NOT NULL DROP TABLE dbo.voice_transcription_attempts;
    IF OBJECT_ID(N'dbo.voice_media_sources', N'U') IS NOT NULL DROP TABLE dbo.voice_media_sources;

    IF @VoiceAppliedAtUtc IS NOT NULL
    BEGIN
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-VOICE-001"}';
        DELETE dbo.schema_migrations WHERE migration_id = N'PS-VOICE-001';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
