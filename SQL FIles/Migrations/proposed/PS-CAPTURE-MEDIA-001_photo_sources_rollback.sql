/* ============================================================
   PS-CAPTURE-MEDIA-001 ROLLBACK - guarded Photo backend removal

   Rollback refuses destructive removal after any Photo row, later
   migration, external dependency, or protected-definition drift.
   It restores the exact PS-VOICE-001 shared delete/export behavior.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @PhotoAppliedAtUtc datetime2(7);
    SELECT @PhotoAppliedAtUtc = applied_at_utc
    FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
    WHERE migration_id = N'PS-CAPTURE-MEDIA-001';

    IF @PhotoAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1 FROM dbo.schema_migrations
           WHERE applied_at_utc > @PhotoAppliedAtUtc
       )
        THROW 52550, 'PS-CAPTURE-MEDIA-001 rollback refused: a later migration is present.', 1;

    IF OBJECT_ID(N'dbo.capture_media_sources', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.capture_media_sources)
        THROW 52551, 'PS-CAPTURE-MEDIA-001 rollback refused: capture_media_sources contains lifecycle or member data.', 1;
    IF OBJECT_ID(N'dbo.capture_media_links', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.capture_media_links)
        THROW 52552, 'PS-CAPTURE-MEDIA-001 rollback refused: capture_media_links contains Capture relationships.', 1;

    DECLARE @PhotoHashPropertyName sysname = N'PS_CAPTURE_MEDIA_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_CreatePhotoSource'), (N'usp_MarkPhotoUploaded'),
        (N'usp_FailPhotoSource'), (N'usp_GetPhotoSourceForOwner'),
        (N'usp_GetPhotoProcessingSourceForOwner'), (N'usp_RecordPhotoScanResult'),
        (N'usp_CompletePhotoProcessing'), (N'usp_ConfirmPhotoCapture'),
        (N'usp_GetPhotoMediaForOwner'), (N'usp_BeginPhotoDraftDeletion'),
        (N'usp_FinalizePhotoDraftDeletion'), (N'usp_FinalizePhotoCaptureDeletion'),
        (N'usp_DeleteCapture'), (N'usp_ExportCaptureForOwner');

    IF @PhotoAppliedAtUtc IS NOT NULL
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
            AND property.name = @PhotoHashPropertyName
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
        THROW 52553, 'PS-CAPTURE-MEDIA-001 rollback refused: protected procedure definition drift detected.', 1;

    DECLARE @PhotoTableIds TABLE (object_id int PRIMARY KEY);
    INSERT @PhotoTableIds (object_id)
    SELECT object_id FROM sys.tables
    WHERE object_id IN
    (
        OBJECT_ID(N'dbo.capture_media_sources'),
        OBJECT_ID(N'dbo.capture_media_links')
    );
    IF EXISTS
    (
        SELECT 1 FROM sys.foreign_keys
        WHERE referenced_object_id IN (SELECT object_id FROM @PhotoTableIds)
          AND parent_object_id NOT IN (SELECT object_id FROM @PhotoTableIds)
    )
        THROW 52554, 'PS-CAPTURE-MEDIA-001 rollback refused: a later table depends on Photo objects.', 1;
    IF EXISTS
    (
        SELECT 1 FROM sys.sql_expression_dependencies AS dependency
        WHERE dependency.referenced_id IN (SELECT object_id FROM @PhotoTableIds)
          AND dependency.referencing_id NOT IN
          (
              SELECT procedure_object.object_id
              FROM sys.procedures AS procedure_object
              JOIN @ProtectedProcedures AS protected_procedure
                ON protected_procedure.procedure_name = procedure_object.name
              WHERE procedure_object.schema_id = SCHEMA_ID(N'dbo')
          )
          AND dependency.referencing_id NOT IN (SELECT object_id FROM @PhotoTableIds)
          AND dependency.referencing_id NOT IN
          (
              SELECT schema_object.object_id FROM sys.objects AS schema_object
              WHERE schema_object.parent_object_id IN (SELECT object_id FROM @PhotoTableIds)
          )
    )
        THROW 52555, 'PS-CAPTURE-MEDIA-001 rollback refused: a later programmable object depends on Photo objects.', 1;

    /* Restore the PS-VOICE-001 shared deletion contract. */
    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DeleteCapture
            @UserKey nvarchar(300), @CaptureKey uniqueidentifier, @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            IF NULLIF(LTRIM(RTRIM(@UserKey)), N'''') IS NULL
               OR @CaptureKey IS NULL OR @ExpectedRowVersion IS NULL
                THROW 52114, ''Owner, capture, and expected version are required.'', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                DECLARE @ProfileId bigint;
                DECLARE @UserId int;
                DECLARE @CaptureId bigint;
                DECLARE @PreviousStatus nvarchar(30);
                DECLARE @SourceId bigint;
                SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
                FROM dbo.member_profiles AS profile JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = NULLIF(LTRIM(RTRIM(@UserKey)), N'''')
                  AND app_user.active = 1 AND profile.active = 1;
                SELECT @CaptureId = capture.capture_id, @PreviousStatus = capture.status,
                       @SourceId = voice_link.source_id
                FROM dbo.captures AS capture WITH (UPDLOCK, HOLDLOCK)
                LEFT JOIN dbo.voice_capture_links AS voice_link ON voice_link.capture_id = capture.capture_id
                WHERE capture.owner_profile_id = @ProfileId AND capture.capture_key = @CaptureKey
                  AND capture.deleted_at_utc IS NULL AND capture.row_version = @ExpectedRowVersion
                  AND ((capture.active = 1 AND capture.status = N''captured'')
                    OR (capture.active = 0 AND capture.status = N''archived''));
                IF @CaptureId IS NULL OR @UserId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''not_found_or_changed'' AS outcome,
                           CAST(NULL AS uniqueidentifier) AS source_key,
                           CAST(NULL AS nvarchar(160)) AS blob_name,
                           CAST(NULL AS binary(8)) AS deletion_token,
                           CAST(NULL AS int) AS deleted_revision_count,
                           CAST(NULL AS int) AS tombstoned_moment_source_count;
                    RETURN;
                END;
                IF @SourceId IS NOT NULL
                BEGIN
                    UPDATE dbo.voice_media_sources
                    SET state = N''deletion_pending'', safe_error_code = NULL,
                        deletion_capture_row_version = @ExpectedRowVersion,
                        deleted_by_user_id = @UserId, updated_at_utc = SYSUTCDATETIME()
                    WHERE source_id = @SourceId AND owner_profile_id = @ProfileId
                      AND state IN (N''confirmed'', N''deletion_pending'');
                    IF @@ROWCOUNT <> 1 THROW 52415, ''Voice deletion state is invalid.'', 1;
                    COMMIT TRANSACTION;
                    SELECT N''pending'' AS outcome, source_key, blob_name,
                           row_version AS deletion_token,
                           CAST(NULL AS int) AS deleted_revision_count,
                           CAST(NULL AS int) AS tombstoned_moment_source_count
                    FROM dbo.voice_media_sources
                    WHERE source_id = @SourceId AND owner_profile_id = @ProfileId;
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
                SELECT N''success'' AS outcome,
                       CAST(NULL AS uniqueidentifier) AS source_key,
                       CAST(NULL AS nvarchar(160)) AS blob_name,
                       CAST(NULL AS binary(8)) AS deletion_token,
                       @RevisionCount AS deleted_revision_count,
                       @MomentSourceCount AS tombstoned_moment_source_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    /* Restore the PS-VOICE-001 export contract. */
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
            SELECT @CaptureId = capture.capture_id
            FROM dbo.captures AS capture
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
            IF EXISTS
            (
                SELECT 1 FROM dbo.voice_capture_links
                WHERE capture_id = @CaptureId AND owner_profile_id = @ProfileId
            )
            BEGIN
                SELECT source.source_key, source.content_type, source.byte_length,
                       source.locale, source.client_duration_milliseconds,
                       source.verified_duration_milliseconds,
                       attempt.provider_transcript
                FROM dbo.voice_capture_links AS link
                JOIN dbo.voice_media_sources AS source ON source.source_id = link.source_id
                JOIN dbo.voice_transcription_attempts AS attempt
                  ON attempt.attempt_id = link.successful_attempt_id
                WHERE link.capture_id = @CaptureId AND link.owner_profile_id = @ProfileId
                  AND source.owner_profile_id = @ProfileId AND attempt.owner_profile_id = @ProfileId
                  AND source.state IN (N''confirmed'', N''deletion_pending'')
                  AND attempt.state = N''succeeded'';
            END;
        END;
    ');

    DECLARE @VoiceHashPropertyName sysname = N'PS_VOICE_001_DEFINITION_HASH';
    DECLARE @SharedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @SharedProcedures VALUES (N'usp_DeleteCapture'), (N'usp_ExportCaptureForOwner');
    DECLARE @SharedProcedureName sysname;
    DECLARE @SharedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @SharedProcedures)
    BEGIN
        SELECT TOP (1) @SharedProcedureName = procedure_name
        FROM @SharedProcedures ORDER BY procedure_name;
        IF EXISTS
        (
            SELECT 1 FROM sys.extended_properties
            WHERE class = 1 AND major_id = OBJECT_ID(N'dbo.' + @SharedProcedureName, N'P')
              AND minor_id = 0 AND name = @PhotoHashPropertyName
        )
            EXEC sys.sp_dropextendedproperty
                @name = @PhotoHashPropertyName,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @SharedProcedureName;
        SELECT @SharedProcedureHash = CONVERT
        (
            nvarchar(64),
            HASHBYTES('SHA2_256', OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @SharedProcedureName, N'P'))),
            2
        );
        IF EXISTS
        (
            SELECT 1 FROM sys.extended_properties
            WHERE class = 1 AND major_id = OBJECT_ID(N'dbo.' + @SharedProcedureName, N'P')
              AND minor_id = 0 AND name = @VoiceHashPropertyName
        )
            EXEC sys.sp_updateextendedproperty
                @name = @VoiceHashPropertyName, @value = @SharedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @SharedProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty
                @name = @VoiceHashPropertyName, @value = @SharedProcedureHash,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'PROCEDURE', @level1name = @SharedProcedureName;
        DELETE @SharedProcedures WHERE procedure_name = @SharedProcedureName;
    END;

    IF OBJECT_ID(N'dbo.usp_CreatePhotoSource', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_CreatePhotoSource;
    IF OBJECT_ID(N'dbo.usp_MarkPhotoUploaded', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_MarkPhotoUploaded;
    IF OBJECT_ID(N'dbo.usp_FailPhotoSource', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_FailPhotoSource;
    IF OBJECT_ID(N'dbo.usp_GetPhotoSourceForOwner', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_GetPhotoSourceForOwner;
    IF OBJECT_ID(N'dbo.usp_GetPhotoProcessingSourceForOwner', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_GetPhotoProcessingSourceForOwner;
    IF OBJECT_ID(N'dbo.usp_RecordPhotoScanResult', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_RecordPhotoScanResult;
    IF OBJECT_ID(N'dbo.usp_CompletePhotoProcessing', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_CompletePhotoProcessing;
    IF OBJECT_ID(N'dbo.usp_ConfirmPhotoCapture', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_ConfirmPhotoCapture;
    IF OBJECT_ID(N'dbo.usp_GetPhotoMediaForOwner', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_GetPhotoMediaForOwner;
    IF OBJECT_ID(N'dbo.usp_BeginPhotoDraftDeletion', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_BeginPhotoDraftDeletion;
    IF OBJECT_ID(N'dbo.usp_FinalizePhotoDraftDeletion', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_FinalizePhotoDraftDeletion;
    IF OBJECT_ID(N'dbo.usp_FinalizePhotoCaptureDeletion', N'P') IS NOT NULL DROP PROCEDURE dbo.usp_FinalizePhotoCaptureDeletion;

    IF OBJECT_ID(N'dbo.capture_media_links', N'U') IS NOT NULL DROP TABLE dbo.capture_media_links;
    IF OBJECT_ID(N'dbo.capture_media_sources', N'U') IS NOT NULL DROP TABLE dbo.capture_media_sources;
    IF EXISTS
    (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID(N'dbo.captures')
          AND name = N'UX_captures_id_owner_for_media'
    )
        DROP INDEX UX_captures_id_owner_for_media ON dbo.captures;

    IF @PhotoAppliedAtUtc IS NOT NULL
    BEGIN
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration', @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-CAPTURE-MEDIA-001"}';
        DELETE dbo.schema_migrations WHERE migration_id = N'PS-CAPTURE-MEDIA-001';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
