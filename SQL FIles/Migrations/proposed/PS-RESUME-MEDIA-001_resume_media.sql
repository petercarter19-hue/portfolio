/*
PS-RESUME-MEDIA-001 — proposed owner-scoped private Resume media placements.

PROPOSED ONLY. This file has not been applied to any database. Its registry
gate is null. Disposable SQL Server execution, two-connection concurrency,
rollback, permission, and driver serialization proof remain required before any
separately authorized schema application. Allowlisting procedure names does not
apply this file.

Scope: the two named decorative placement slots (story_banner,
experience_support), their per-slot crop and presentation semantics, and the
closed media command receipts for add_media and keep_words_only. Media
placements advance the SAME dbo.resume_drafts.draft_version the accepted
PS-RESUME-DRAFT-001 text commands fence, so a media Add and a text save cannot
silently overwrite each other: each command re-reads the shared version under a
serializable transaction and refuses a stale expectation.

Out of scope: publication, public readers, sharing, generated-image catalog
rows, storage, malware scanning, provider calls, Photo Capture lifecycle
mutation, and any production enablement. The command reads and locks the
authoritative Photo Capture row only to fence the exact source version,
lifecycle and derivative digest reviewed for the placement; it does not
duplicate that lifecycle or make an unready source servable.

Portrait is identity presentation, never a placement slot, so the slot
constraint below cannot represent it.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-DRAFT-001')
        THROW 52300, 'PS-RESUME-DRAFT-001 must be applied first.', 1;

    /* The media command's authoritative source fence reads the Photo Capture
       source row, so that table has to exist first. A missing table makes the
       fence impossible, and the procedure must refuse rather than persist an
       unverified source. */
    IF OBJECT_ID(N'dbo.capture_media_sources', N'U') IS NULL
        THROW 52307, 'PS-CAPTURE-MEDIA-001 (authoritative photo source table) must be applied first.', 1;

    IF OBJECT_ID(N'dbo.resume_media_placements', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_media_placements
        (
            resume_media_placement_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            slot nvarchar(40) NOT NULL,
            source_kind nvarchar(40) NOT NULL,
            asset_id nvarchar(120) NOT NULL,
            asset_version bigint NOT NULL,
            asset_digest nvarchar(128) NOT NULL,
            crop_x decimal(9,6) NOT NULL,
            crop_y decimal(9,6) NOT NULL,
            crop_width decimal(9,6) NOT NULL,
            crop_height decimal(9,6) NOT NULL,
            presentation_version int NOT NULL CONSTRAINT DF_resume_media_placements_presentation DEFAULT 1,
            alt_text nvarchar(300) NULL,
            decorative bit NOT NULL CONSTRAINT DF_resume_media_placements_decorative DEFAULT 0,
            provenance_label nvarchar(120) NOT NULL,
            caption nvarchar(500) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_media_placements_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_media_placements_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_media_placements PRIMARY KEY (resume_media_placement_id),
            CONSTRAINT UQ_resume_media_placements_owner_slot UNIQUE (owner_profile_id, slot),
            CONSTRAINT FK_resume_media_placements_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_media_placements_slot CHECK
                (slot IN (N'story_banner', N'experience_support')),
            CONSTRAINT CK_resume_media_placements_source_kind CHECK
                (source_kind IN (N'owner_photo', N'generated_illustration')),
            CONSTRAINT CK_resume_media_placements_asset CHECK
                (LEN(asset_id) > 0 AND asset_version >= 0 AND LEN(asset_digest) > 0),
            CONSTRAINT CK_resume_media_placements_crop_origin CHECK
                (crop_x >= 0 AND crop_y >= 0),
            CONSTRAINT CK_resume_media_placements_crop_extent CHECK
                (crop_width > 0 AND crop_height > 0
                 AND crop_x + crop_width <= 1 AND crop_y + crop_height <= 1),
            CONSTRAINT CK_resume_media_placements_presentation CHECK (presentation_version >= 1),
            CONSTRAINT CK_resume_media_placements_alt CHECK
                (decorative = 1 OR (alt_text IS NOT NULL AND LEN(LTRIM(RTRIM(alt_text))) > 0)),
            CONSTRAINT CK_resume_media_placements_caption CHECK
                (caption IS NULL OR (LEN(caption) > 0 AND LEN(caption) <= 500))
        );
    END;

    IF OBJECT_ID(N'dbo.resume_media_command_receipts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_media_command_receipts
        (
            resume_media_command_receipt_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            command_type nvarchar(40) NOT NULL,
            request_uuid uniqueidentifier NOT NULL,
            semantic_digest char(64) NOT NULL,
            outcome_json nvarchar(max) NOT NULL,
            recorded_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_media_command_receipts_recorded DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_media_command_receipts PRIMARY KEY (resume_media_command_receipt_id),
            CONSTRAINT UQ_resume_media_command_receipts_owner_key UNIQUE
                (owner_profile_id, command_type, request_uuid),
            CONSTRAINT FK_resume_media_command_receipts_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_media_command_receipts_type CHECK
                (command_type IN (N'add_media', N'keep_words_only')),
            CONSTRAINT CK_resume_media_command_receipts_digest CHECK (LEN(semantic_digest) = 64),
            CONSTRAINT CK_resume_media_command_receipts_outcome CHECK (ISJSON(outcome_json) = 1)
        );
    END;

    EXEC(N'
        CREATE OR ALTER TRIGGER dbo.trg_resume_media_command_receipts_immutable
        ON dbo.resume_media_command_receipts
        INSTEAD OF UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            THROW 52301, ''RESUME_MEDIA_RECEIPT_IMMUTABLE'', 1;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetResumeMediaDraftForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            /* The connection is autocommit, so this procedure opens its own
               transaction: the header, placements and receipts it returns are
               one consistent snapshot, and a failure rolls back rather than
               returning a partial read. */
            BEGIN TRY
            BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52302, ''RESUME_MEDIA_NOT_FOUND'', 1;

            /* Fix the same shared-resource lock order used by both command
               procedures: owner draft, receipt range, then placements. */
            DECLARE @ReadDraftVersion int;
            DECLARE @ReadBasePublicationVersion int;
            SELECT @ReadDraftVersion = draft.draft_version,
                   @ReadBasePublicationVersion = draft.base_publication_version
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            WHERE draft.owner_profile_id = @ProfileId;

            DECLARE @MediaGeneration int;
            SELECT @MediaGeneration = COUNT(*)
            FROM dbo.resume_media_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId;

            SELECT
                ISNULL(@ReadDraftVersion, 0) AS draft_version,
                @ReadBasePublicationVersion AS base_publication_version,
                ISNULL(@MediaGeneration, 0) AS media_generation;

            SELECT
                placement.slot,
                placement.source_kind,
                placement.asset_id,
                placement.asset_version,
                placement.asset_digest,
                placement.crop_x,
                placement.crop_y,
                placement.crop_width,
                placement.crop_height,
                placement.presentation_version,
                placement.alt_text,
                placement.decorative,
                placement.provenance_label,
                placement.caption
            FROM dbo.resume_media_placements AS placement WITH (UPDLOCK, HOLDLOCK)
            WHERE placement.owner_profile_id = @ProfileId
            ORDER BY CASE placement.slot
                        WHEN N''story_banner'' THEN 0
                        ELSE 1
                     END;

            SELECT
                receipt.command_type,
                receipt.request_uuid,
                receipt.semantic_digest,
                receipt.outcome_json
            FROM dbo.resume_media_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId
            ORDER BY receipt.recorded_at_utc, receipt.resume_media_command_receipt_id;

            COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeMediaCommandForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            /* The connection is autocommit. This procedure therefore opens its
               own transaction and rolls it back on any failure, so the shared
               draft version, the placements and the command receipt move
               together or not at all. A media command and a text command lock
               the same dbo.resume_drafts row, so only one of them can win a
               given version. */
            BEGIN TRY
            BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52302, ''RESUME_MEDIA_NOT_FOUND'', 1;

            IF @CommandJson IS NULL OR ISJSON(@CommandJson) <> 1
                THROW 52303, ''RESUME_MEDIA_VALIDATION'', 1;

            /* One digest vocabulary: the applied semantic digest the command
               payload carries is what this procedure stores and what a replay
               compares. A JSON hash would never equal it, so an exact retry
               would be refused as a conflict. */
            DECLARE @IncomingType nvarchar(40) = JSON_VALUE(@CommandJson, ''$.command'');
            DECLARE @IncomingDigest nvarchar(128) = JSON_VALUE(@CommandJson, ''$.receipt.semantic_digest'');
            IF @IncomingType NOT IN (N''add_media'', N''keep_words_only'')
               OR @IncomingDigest IS NULL
               OR LEN(@IncomingDigest) <> 64
               OR @IncomingDigest COLLATE Latin1_General_100_BIN2 LIKE ''%[^0-9a-f]%''
                THROW 52303, ''RESUME_MEDIA_VALIDATION'', 1;
            DECLARE @ExistingDigest char(64);
            DECLARE @ExistingType nvarchar(40);
            DECLARE @ExistingOutcome nvarchar(max);

            /* Match the read and text-command lock order: acquire the shared
               owner draft before any receipt row. Do not evaluate its version
               until after receipt replay, so an exact accepted retry remains
               authoritative even when a later command moved the draft. */
            DECLARE @DraftId bigint;
            DECLARE @DraftVersion int;
            SELECT @DraftId = draft.resume_draft_id,
                   @DraftVersion = draft.draft_version
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            WHERE draft.owner_profile_id = @ProfileId;

            SELECT @ExistingDigest = receipt.semantic_digest,
                   @ExistingType = receipt.command_type,
                   @ExistingOutcome = receipt.outcome_json
            FROM dbo.resume_media_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId
              AND receipt.request_uuid = @RequestId;

            IF @ExistingDigest IS NOT NULL
            BEGIN
                IF @ExistingType <> @IncomingType
                   OR @ExistingDigest <> @IncomingDigest
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT CONVERT(bit, 0) AS committed,
                           CONVERT(bit, 0) AS replayed,
                           N''idempotency_conflict'' AS outcome,
                           NULL AS outcome_json,
                           CONVERT(bit, 0) AS publishes;
                    RETURN;
                END;
                COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 1) AS replayed,
                       N''replayed'' AS outcome,
                       @ExistingOutcome AS outcome_json,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            DECLARE @CommandType nvarchar(40) = @IncomingType;
            DECLARE @ExpectedVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_draft_version''));
            DECLARE @NextVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.draft_version''));
            DECLARE @ReceiptType nvarchar(40) = JSON_VALUE(@CommandJson, ''$.receipt.command_type'');
            DECLARE @ReceiptUuid uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.receipt.request_uuid''));
            DECLARE @ReceiptDigest nvarchar(64) = JSON_VALUE(@CommandJson, ''$.receipt.semantic_digest'');
            DECLARE @ReceiptOutcome nvarchar(max) = JSON_QUERY(@CommandJson, ''$.receipt.outcome'');
            DECLARE @Placements nvarchar(max) = JSON_QUERY(@CommandJson, ''$.placements'');

            IF @ExpectedVersion IS NULL
               OR @NextVersion IS NULL
               OR @NextVersion <> @ExpectedVersion + 1
               OR @ReceiptType <> @CommandType
               OR @ReceiptUuid IS NULL
               OR @ReceiptUuid <> @RequestId
               OR @ReceiptDigest IS NULL
               OR LEN(@ReceiptDigest) <> 64
               OR @ReceiptOutcome IS NULL
               OR ISJSON(@ReceiptOutcome) <> 1
               OR @Placements IS NULL
               OR ISJSON(@Placements) <> 1
                THROW 52303, ''RESUME_MEDIA_VALIDATION'', 1;

            IF @DraftId IS NULL
            BEGIN
                INSERT dbo.resume_drafts (owner_profile_id, draft_version)
                VALUES (@ProfileId, 0);
                SET @DraftId = SCOPE_IDENTITY();
                SET @DraftVersion = 0;
            END;

            IF @DraftVersion <> @ExpectedVersion
            BEGIN
                COMMIT TRANSACTION;
                SELECT CONVERT(bit, 0) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''stale_draft'' AS outcome,
                       NULL AS outcome_json,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            IF @CommandType = N''add_media''
            BEGIN
                /* One placement per named slot: a payload that names the same
                   slot twice is refused before anything is written. */
                IF EXISTS (
                    SELECT 1
                    FROM OPENJSON(@Placements)
                    WITH (slot nvarchar(40) ''$.slot'') AS duplicate
                    GROUP BY duplicate.slot
                    HAVING COUNT(*) > 1
                )
                    THROW 52303, ''RESUME_MEDIA_VALIDATION'', 1;

                IF EXISTS (
                    SELECT 1
                    FROM OPENJSON(@Placements)
                    WITH (
                        slot nvarchar(40) ''$.slot'',
                        source_kind nvarchar(40) ''$.source_kind'',
                        asset_id nvarchar(120) ''$.asset_id'',
                        asset_version bigint ''$.asset_version'',
                        asset_digest nvarchar(128) ''$.asset_digest'',
                        crop_x decimal(9,6) ''$.crop.x'',
                        crop_y decimal(9,6) ''$.crop.y'',
                        crop_width decimal(9,6) ''$.crop.width'',
                        crop_height decimal(9,6) ''$.crop.height'',
                        presentation_version int ''$.presentation_version'',
                        alt_text nvarchar(300) ''$.alt_text'',
                        decorative bit ''$.decorative'',
                        provenance_label nvarchar(120) ''$.provenance_label'',
                        caption nvarchar(500) ''$.caption''
                    ) AS candidate
                    WHERE candidate.slot NOT IN (N''story_banner'', N''experience_support'')
                       OR candidate.source_kind NOT IN (N''owner_photo'', N''generated_illustration'')
                       OR candidate.asset_id IS NULL
                       OR LEN(candidate.asset_id) = 0
                       OR candidate.asset_version IS NULL
                       OR candidate.asset_version < 0
                       OR candidate.asset_digest IS NULL
                       OR LEN(candidate.asset_digest) = 0
                       OR candidate.crop_width <= 0
                       OR candidate.crop_height <= 0
                       OR candidate.crop_x < 0
                       OR candidate.crop_y < 0
                       OR candidate.crop_x + candidate.crop_width > 1
                       OR candidate.crop_y + candidate.crop_height > 1
                       OR candidate.presentation_version < 1
                       OR (candidate.decorative = 0
                           AND (candidate.alt_text IS NULL
                                OR LEN(LTRIM(RTRIM(candidate.alt_text))) = 0))
                       OR LEN(ISNULL(candidate.alt_text, N'''')) > 300
                       OR LEN(ISNULL(candidate.caption, N'''')) > 500
                       OR candidate.provenance_label IS NULL
                       OR LEN(LTRIM(RTRIM(candidate.provenance_label))) = 0
                       OR LEN(candidate.provenance_label) > 120
                )
                    THROW 52303, ''RESUME_MEDIA_VALIDATION'', 1;

                /* Authoritative source fence, inside this transaction. A
                   placement whose owner-photo source is no longer the exact
                   eligible, owner-scoped Photo Capture source version is
                   refused before any write, so a restriction, withdrawal,
                   deletion or replacement cannot land between an application
                   read and this commit. Locked with the same (UPDLOCK,
                   HOLDLOCK) discipline as the draft row. */
                IF EXISTS (
                    SELECT 1
                    FROM OPENJSON(@Placements)
                    WITH (
                        source_kind nvarchar(40) ''$.source_kind'',
                        asset_id nvarchar(120) ''$.asset_id'',
                        asset_version bigint ''$.asset_version'',
                        asset_digest nvarchar(128) ''$.asset_digest''
                    ) AS candidate
                    WHERE candidate.source_kind = N''owner_photo''
                      AND NOT EXISTS (
                            SELECT 1
                            FROM dbo.capture_media_sources AS source WITH (UPDLOCK, HOLDLOCK)
                            WHERE source.owner_profile_id = @ProfileId
                              AND source.source_type = N''photo''
                              AND source.source_key = TRY_CONVERT(uniqueidentifier, candidate.asset_id)
                              AND CONVERT(bigint, source.row_version) = candidate.asset_version
                              AND source.state IN (N''needs_review'', N''confirmed'')
                              AND source.scan_result = N''clean''
                              AND source.derivative_sha256_digest IS NOT NULL
                              AND LOWER(CONVERT(varchar(64), source.derivative_sha256_digest, 2))
                                  = LOWER(candidate.asset_digest)
                      )
                )
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT CONVERT(bit, 0) AS committed,
                           CONVERT(bit, 0) AS replayed,
                           N''source_changed'' AS outcome,
                           NULL AS outcome_json,
                           CONVERT(bit, 0) AS publishes;
                    RETURN;
                END;

                /* Curated catalog placements need the same authoritative
                   fence, and no catalog table exists in this proposal, so the
                   durable path refuses them instead of persisting a source it
                   cannot verify. The catalog fence belongs to the catalog
                   package; until then this adapter fails closed. */
                IF EXISTS (
                    SELECT 1
                    FROM OPENJSON(@Placements)
                    WITH (source_kind nvarchar(40) ''$.source_kind'') AS candidate
                    WHERE candidate.source_kind = N''generated_illustration''
                )
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT CONVERT(bit, 0) AS committed,
                           CONVERT(bit, 0) AS replayed,
                           N''source_unavailable'' AS outcome,
                           NULL AS outcome_json,
                           CONVERT(bit, 0) AS publishes;
                    RETURN;
                END;

                DELETE placement
                FROM dbo.resume_media_placements AS placement WITH (UPDLOCK, HOLDLOCK)
                WHERE placement.owner_profile_id = @ProfileId
                  AND placement.slot NOT IN (
                        SELECT removed.slot
                        FROM OPENJSON(@Placements)
                        WITH (slot nvarchar(40) ''$.slot'') AS removed
                  );

                MERGE dbo.resume_media_placements WITH (UPDLOCK, HOLDLOCK) AS target
                USING (
                    SELECT
                        candidate.slot,
                        candidate.source_kind,
                        candidate.asset_id,
                        candidate.asset_version,
                        candidate.asset_digest,
                        candidate.crop_x,
                        candidate.crop_y,
                        candidate.crop_width,
                        candidate.crop_height,
                        candidate.presentation_version,
                        candidate.alt_text,
                        candidate.decorative,
                        candidate.provenance_label,
                        candidate.caption
                    FROM OPENJSON(@Placements)
                    WITH (
                        slot nvarchar(40) ''$.slot'',
                        source_kind nvarchar(40) ''$.source_kind'',
                        asset_id nvarchar(120) ''$.asset_id'',
                        asset_version bigint ''$.asset_version'',
                        asset_digest nvarchar(128) ''$.asset_digest'',
                        crop_x decimal(9,6) ''$.crop.x'',
                        crop_y decimal(9,6) ''$.crop.y'',
                        crop_width decimal(9,6) ''$.crop.width'',
                        crop_height decimal(9,6) ''$.crop.height'',
                        presentation_version int ''$.presentation_version'',
                        alt_text nvarchar(300) ''$.alt_text'',
                        decorative bit ''$.decorative'',
                        provenance_label nvarchar(120) ''$.provenance_label'',
                        caption nvarchar(500) ''$.caption''
                    ) AS candidate
                ) AS source
                   ON target.owner_profile_id = @ProfileId
                  AND target.slot = source.slot
                WHEN MATCHED THEN
                    UPDATE SET
                        source_kind = source.source_kind,
                        asset_id = source.asset_id,
                        asset_version = source.asset_version,
                        asset_digest = source.asset_digest,
                        crop_x = source.crop_x,
                        crop_y = source.crop_y,
                        crop_width = source.crop_width,
                        crop_height = source.crop_height,
                        presentation_version = source.presentation_version,
                        alt_text = source.alt_text,
                        decorative = source.decorative,
                        provenance_label = source.provenance_label,
                        caption = source.caption,
                        updated_at_utc = SYSUTCDATETIME()
                WHEN NOT MATCHED THEN
                    INSERT
                        (owner_profile_id, slot, source_kind, asset_id, asset_version,
                         asset_digest, crop_x, crop_y, crop_width, crop_height,
                         presentation_version, alt_text, decorative, provenance_label, caption)
                    VALUES
                        (@ProfileId, source.slot, source.source_kind, source.asset_id,
                         source.asset_version, source.asset_digest, source.crop_x,
                         source.crop_y, source.crop_width, source.crop_height,
                         source.presentation_version, source.alt_text, source.decorative,
                         source.provenance_label, source.caption);
            END;

            UPDATE dbo.resume_drafts
            SET draft_version = @NextVersion,
                updated_at_utc = SYSUTCDATETIME()
            WHERE resume_draft_id = @DraftId;

            INSERT dbo.resume_media_command_receipts
                (owner_profile_id, command_type, request_uuid, semantic_digest, outcome_json)
            VALUES
                (@ProfileId, @CommandType, @RequestId, @ReceiptDigest, @ReceiptOutcome);

            COMMIT TRANSACTION;
            SELECT CONVERT(bit, 1) AS committed,
                   CONVERT(bit, 0) AS replayed,
                   N''committed'' AS outcome,
                   @ReceiptOutcome AS outcome_json,
                   CONVERT(bit, 0) AS publishes;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    INSERT dbo.schema_migrations (migration_id)
    VALUES (N'PS-RESUME-MEDIA-001');

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
