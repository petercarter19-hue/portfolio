/* PS-RESUME-IDENTITY-001. PROPOSED ONLY; no execution authority.
Pin an approved same-owner Profile identity reference in each immutable Resume
revision. Corrections carry the reference forward; new publishes explicitly
replace or clear it. Profile remains the only editable identity authority.
G also atomically commits reviewed editorial deltas, explicit display/AI choices,
media and draft advancement under the same publication transaction.
Existing procedure permissions are preserved by CREATE OR ALTER.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-PROFILE-002')
        OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-PUBLICATION-001')
        OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-WORKSHOP-004')
        OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-VISITOR-AI-001')
        THROW 54300, 'Profile and Resume publication prerequisites are required.', 1;
    IF COL_LENGTH(N'dbo.resume_publication_revisions',N'profile_identity_json') IS NULL
        ALTER TABLE dbo.resume_publication_revisions ADD profile_identity_json nvarchar(max) NULL
            CONSTRAINT CK_resume_publication_identity_json CHECK(profile_identity_json IS NULL OR ISJSON(profile_identity_json)=1);

    IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-WORKSHOP-004')
        THROW 54300,'Versioned knowledge provenance prerequisite is required.',1;
    IF COL_LENGTH(N'dbo.resume_drafts',N'story_entry_key') IS NULL
        ALTER TABLE dbo.resume_drafts ADD story_entry_key uniqueidentifier NULL;
    ALTER TABLE dbo.resume_draft_items DROP CONSTRAINT CK_resume_draft_items_type;
    ALTER TABLE dbo.resume_draft_items ADD CONSTRAINT CK_resume_draft_items_type CHECK
      (record_type IN(N'role',N'education',N'credential',N'skill',N'accomplishment',N'knowledge'));
    ALTER TABLE dbo.resume_draft_command_receipts DROP CONSTRAINT CK_resume_draft_command_receipts_type;
    ALTER TABLE dbo.resume_draft_command_receipts ADD CONSTRAINT CK_resume_draft_command_receipts_type CHECK
      (command_type IN(N'save_item',N'discard_item',N'create_private_item',N'review_candidate',N'bind_story',N'clear_story'));
    ALTER TABLE dbo.resume_draft_command_receipts DROP CONSTRAINT CK_resume_draft_command_receipts_outcome;
    ALTER TABLE dbo.resume_draft_command_receipts ADD CONSTRAINT CK_resume_draft_command_receipts_outcome CHECK
      (outcome IN(N'saved',N'discarded',N'created',N'reviewed',N'story_selected',N'story_removed'));

    /* Provenance belongs to the immutable receipt, independently of mutable
       placements and without altering its replayed outcome JSON. Pre-G/photo-only
       receipts remain false. The command derives this bit, never its caller. */
    IF COL_LENGTH(N'dbo.resume_media_command_receipts',N'catalog_source_bound') IS NULL
        ALTER TABLE dbo.resume_media_command_receipts ADD catalog_source_bound bit NOT NULL
            CONSTRAINT DF_resume_media_receipts_catalog_bound DEFAULT(0) WITH VALUES;

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeMediaCommandForOwner
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

            /* Preserve the latest PUBLICATION wrapper guard inside G''s transaction. */
            EXEC dbo.usp_ResumePublicationGuardLegacyMutator
                @ProfileId=@ProfileId, @Mutator=N''media'', @CommandJson=@CommandJson;

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
                    ROLLBACK TRANSACTION;
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

            DECLARE @CatalogSourceBound bit=0;
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
                ROLLBACK TRANSACTION;
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
                    ROLLBACK TRANSACTION;
                    SELECT CONVERT(bit, 0) AS committed,
                           CONVERT(bit, 0) AS replayed,
                           N''source_changed'' AS outcome,
                           NULL AS outcome_json,
                           CONVERT(bit, 0) AS publishes;
                    RETURN;
                END;

                /* G binds generated placements to the authoritative catalog in
                   this same transaction. No application/fixture read can replace
                   the locked identity, version, digest and eligibility fence. */
                IF EXISTS (SELECT 1 FROM OPENJSON(@Placements)
                    WITH (source_kind nvarchar(40) ''$.source_kind'') AS candidate
                    WHERE candidate.source_kind=N''generated_illustration'')
                BEGIN
                    IF OBJECT_ID(N''dbo.resume_catalog_assets'', N''U'') IS NULL
                    BEGIN
                        ROLLBACK TRANSACTION;
                        SELECT CONVERT(bit,0) AS committed, CONVERT(bit,0) AS replayed,
                            N''source_unavailable'' AS outcome, NULL AS outcome_json,
                            CONVERT(bit,0) AS publishes;
                        RETURN;
                    END;
                    IF EXISTS (
                        SELECT 1 FROM OPENJSON(@Placements)
                        WITH (source_kind nvarchar(40) ''$.source_kind'',
                              asset_id nvarchar(max) ''$.asset_id'',
                              asset_version bigint ''$.asset_version'',
                              asset_digest nvarchar(max) ''$.asset_digest'') AS candidate
                        WHERE candidate.source_kind=N''generated_illustration''
                          AND NOT EXISTS (
                            SELECT 1 FROM dbo.resume_catalog_assets AS asset WITH (UPDLOCK,HOLDLOCK)
                            WHERE DATALENGTH(candidate.asset_id)=72
                              AND TRY_CONVERT(uniqueidentifier,candidate.asset_id) IS NOT NULL
                              AND asset.asset_id=TRY_CONVERT(uniqueidentifier,candidate.asset_id)
                              AND asset.asset_version=candidate.asset_version
                              AND DATALENGTH(candidate.asset_digest)=128
                              AND LOWER(candidate.asset_digest) COLLATE Latin1_General_100_BIN2
                                  = LOWER(asset.content_sha256) COLLATE Latin1_General_100_BIN2
                              AND asset.origin=N''generated_illustration''
                              AND asset.lifecycle=N''active''
                              AND asset.width>0 AND asset.height>0))
                    BEGIN
                        ROLLBACK TRANSACTION;
                        SELECT CONVERT(bit,0) AS committed, CONVERT(bit,0) AS replayed,
                            N''source_changed'' AS outcome, NULL AS outcome_json,
                            CONVERT(bit,0) AS publishes;
                        RETURN;
                    END;
                    SET @CatalogSourceBound=1;
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
                (owner_profile_id, command_type, request_uuid, semantic_digest, outcome_json, catalog_source_bound)
            VALUES
                (@ProfileId, @CommandType, @RequestId, @ReceiptDigest, @ReceiptOutcome, @CatalogSourceBound);

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
        END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetResumeDraftForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            /* db.py uses an autocommit connection. Own the transaction inside
               the procedure so the two result sets are one consistent read
               and every lock is released by this procedure. */
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
                THROW 52202, ''RESUME_DRAFT_NOT_FOUND'', 1;

            /* Fix the shared-resource lock order explicitly: owner draft,
               receipt range, then items. Keep the public reader at exactly two
               result sets by carrying receipts in the header JSON column. */
            DECLARE @ReadStoryKey uniqueidentifier;
            DECLARE @ReadDraftId bigint;
            DECLARE @ReadDraftVersion int;
            DECLARE @ReadBasePublicationVersion nvarchar(64);
            SELECT @ReadStoryKey = draft.story_entry_key, @ReadDraftId = draft.resume_draft_id,
                   @ReadDraftVersion = draft.draft_version,
                   @ReadBasePublicationVersion = draft.base_publication_version
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            WHERE draft.owner_profile_id = @ProfileId;

            DECLARE @CommandReceiptsJson nvarchar(max);
            SELECT @CommandReceiptsJson = (
                SELECT
                    CONVERT(nvarchar(36), receipt.request_id) AS request_id,
                    receipt.request_digest,
                    receipt.outcome
                FROM dbo.resume_draft_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
                WHERE receipt.owner_profile_id = @ProfileId
                ORDER BY receipt.committed_at_utc, receipt.request_id
                FOR JSON PATH
            );

            SELECT
                @ReadStoryKey AS story_entry_key, @ReadDraftVersion AS draft_version,
                @ReadBasePublicationVersion AS base_publication_version,
                JSON_QUERY(COALESCE(@CommandReceiptsJson, N''[]'')) AS command_receipts_json
            WHERE @ReadDraftId IS NOT NULL;

            SELECT
                item.record_key,
                item.record_type,
                item.base_content_token,
                item.base_access_revision,
                item.proposed_values_json,
                item.intended_permission_expansions_json,
                item.is_new
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.resume_draft_items AS item WITH (UPDLOCK, HOLDLOCK)
              ON item.resume_draft_id = draft.resume_draft_id
            WHERE draft.owner_profile_id = @ProfileId
            ORDER BY item.record_type, item.record_key;

            COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeDraftCommandForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            /* The driver is autocommit, so receipt arbitration, the shared
               draft-version fence, item mutation and receipt insertion must be
               owned by one internal transaction. A nested intake call already
               owns the outer transaction, so this callee participates in it
               and never commits or rolls the caller back. */
            DECLARE @OwnTransaction bit = 0;
            IF @@TRANCOUNT = 0
            BEGIN
                BEGIN TRANSACTION;
                SET @OwnTransaction = 1;
            END;

            BEGIN TRY

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52202, ''RESUME_DRAFT_NOT_FOUND'', 1;

            /* Preserve the latest PUBLICATION wrapper guard inside G''s transaction. */
            EXEC dbo.usp_ResumePublicationGuardLegacyMutator
                @ProfileId=@ProfileId, @Mutator=N''draft'', @CommandJson=@CommandJson;

            IF @CommandJson IS NULL OR ISJSON(@CommandJson) <> 1
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;

            /* The application computes the receipt digest from the normalized
               command semantics. Use that exact digest for both first commit
               and replay; hashing this transport envelope is not equivalent. */
            DECLARE @IncomingDigest nvarchar(128) = JSON_VALUE(@CommandJson, ''$.request_digest'');
            IF @IncomingDigest IS NULL
               OR LEN(@IncomingDigest) <> 64
               OR @IncomingDigest COLLATE Latin1_General_100_BIN2 LIKE ''%[^0-9a-f]%''
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;
            DECLARE @Digest char(64) = CONVERT(char(64), @IncomingDigest);
            DECLARE @ExistingDigest char(64);
            DECLARE @ExistingOutcome nvarchar(40);

            /* Every reader and both text/media writers acquire the shared
               owner draft before a receipt row. The version is intentionally
               not evaluated yet: an exact receipt replay still wins before
               the expected-version fence below. */
            DECLARE @DraftId bigint;
            DECLARE @DraftVersion int;
            SELECT @DraftId = draft.resume_draft_id,
                   @DraftVersion = draft.draft_version
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            WHERE draft.owner_profile_id = @ProfileId;

            SELECT @ExistingDigest = receipt.request_digest,
                   @ExistingOutcome = receipt.outcome
            FROM dbo.resume_draft_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId
              AND receipt.request_id = @RequestId;

            IF @ExistingDigest IS NOT NULL
            BEGIN
                IF @ExistingDigest <> @Digest
                BEGIN
                    /* RESUME_DRAFT_IDEMPOTENCY_CONFLICT is returned as a
                       stable outcome row so adapters do not parse engine
                       error text and can map the conflict deterministically. */
                    IF @OwnTransaction = 1 COMMIT TRANSACTION;
                    SELECT CONVERT(bit, 0) AS committed,
                           CONVERT(bit, 0) AS replayed,
                           N''idempotency_conflict'' AS outcome,
                           @ExistingDigest AS request_digest,
                           CONVERT(bit, 0) AS publishes;
                    RETURN;
                END;
                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 1) AS replayed,
                       @ExistingOutcome AS outcome,
                       @ExistingDigest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            DECLARE @CommandType nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
            DECLARE @ExpectedDraftVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_draft_version''));
            IF @CommandType NOT IN (N''save_item'', N''discard_item'', N''create_private_item'', N''review_candidate'', N''bind_story'', N''clear_story'')
               OR @ExpectedDraftVersion IS NULL
               OR @ExpectedDraftVersion < 0
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;

            /* Both text and media commands acquire this same owner draft row
               before their domain-specific writes. Exact replay was resolved
               above, so only a genuinely new command reaches the fence. */
            IF @DraftId IS NULL AND @ExpectedDraftVersion = 0
            BEGIN
                INSERT dbo.resume_drafts (owner_profile_id, draft_version)
                VALUES (@ProfileId, 0);
                SELECT @DraftId = SCOPE_IDENTITY(), @DraftVersion = 0;
            END;

            IF ISNULL(@DraftVersion, 0) <> @ExpectedDraftVersion
               OR @DraftId IS NULL
            BEGIN
                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 0) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''stale_draft'' AS outcome,
                       @DraftVersion AS current_draft_version,
                       @ExpectedDraftVersion AS expected_draft_version,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            IF @CommandType = N''review_candidate''
            BEGIN
                INSERT dbo.resume_draft_command_receipts
                    (owner_profile_id, request_id, request_digest, command_type, outcome)
                VALUES
                    (@ProfileId, @RequestId, @Digest, @CommandType, N''reviewed'');
                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''reviewed'' AS outcome,
                       @Digest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            DECLARE @RecordKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.record_key''));
            DECLARE @RecordType nvarchar(40) = JSON_VALUE(@CommandJson, ''$.record_type'');
            DECLARE @ExpectedToken nvarchar(64) = JSON_VALUE(@CommandJson, ''$.expected_content_token'');
            DECLARE @ExpectedAccess int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_access_revision''));
            DECLARE @Proposed nvarchar(max) = JSON_QUERY(@CommandJson, ''$.values'');
            DECLARE @Intended nvarchar(max) = JSON_QUERY(@CommandJson, ''$.intended_permission_expansions'');

            IF @CommandType IN (N''save_item'', N''discard_item'', N''create_private_item'')
               AND @RecordKey IS NULL
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;

            IF @CommandType = N''save_item''
               AND (
                    @ExpectedToken IS NULL
                    OR @ExpectedAccess IS NULL
                    OR ISJSON(ISNULL(@Proposed, N''{}'')) <> 1
               )
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;

            IF @Intended IS NOT NULL AND ISJSON(@Intended) <> 1
                THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;


            IF @CommandType IN(N''bind_story'',N''clear_story'')
            BEGIN
                IF @CommandType=N''bind_story''
                BEGIN
                    IF @RecordKey IS NULL OR @ExpectedToken IS NULL OR LEN(@ExpectedToken)<>16
                        OR @ExpectedToken COLLATE Latin1_General_100_BIN2 LIKE ''%[^0-9a-f]%''
                        OR @ExpectedAccess IS NULL OR @ExpectedAccess<0
                        THROW 52204,''RESUME_DRAFT_VALIDATION'',1;
                    IF NOT EXISTS(SELECT 1 FROM dbo.knowledge_items WITH(UPDLOCK,HOLDLOCK)
                        WHERE owner_profile_id=@ProfileId AND knowledge_item_key=@RecordKey
                          AND item_status=N''confirmed'' AND classification=N''personal''
                          AND confirmed_version_number=current_version_number
                          AND row_version=TRY_CONVERT(binary(8),@ExpectedToken,2))
                        THROW 52205,''RESUME_DRAFT_CHANGED'',1;
                    IF @ExpectedAccess=0
                    BEGIN
                        IF EXISTS(SELECT 1 FROM dbo.entry_policy_records WITH(UPDLOCK,HOLDLOCK)
                            WHERE owner_profile_id=@ProfileId AND entry_key=@RecordKey)
                            THROW 52205,''RESUME_DRAFT_CHANGED'',1;
                        INSERT dbo.entry_policy_records(owner_profile_id,entry_key,canonical_type,canonical_key,
                            category,content_version,access_revision,resume_display,visitor_ai,private_assistance_excluded,lifecycle)
                          VALUES(@ProfileId,@RecordKey,N''knowledge'',@RecordKey,N''personal'',1,1,0,0,0,N''active'');
                    END
                    ELSE IF NOT EXISTS(SELECT 1 FROM dbo.entry_policy_records WITH(UPDLOCK,HOLDLOCK)
                        WHERE owner_profile_id=@ProfileId AND entry_key=@RecordKey AND canonical_key=@RecordKey
                          AND canonical_type=N''knowledge'' AND lifecycle=N''active'' AND access_revision=@ExpectedAccess)
                        THROW 52205,''RESUME_DRAFT_CHANGED'',1;
                END;
                UPDATE dbo.resume_drafts SET story_entry_key=CASE WHEN @CommandType=N''bind_story'' THEN @RecordKey END,
                    draft_version=@DraftVersion+1,updated_at_utc=SYSUTCDATETIME() WHERE resume_draft_id=@DraftId;
                DECLARE @StoryOutcome nvarchar(40)=CASE WHEN @CommandType=N''bind_story'' THEN N''story_selected'' ELSE N''story_removed'' END;
                INSERT dbo.resume_draft_command_receipts(owner_profile_id,request_id,request_digest,command_type,outcome)
                    VALUES(@ProfileId,@RequestId,@Digest,@CommandType,@StoryOutcome);
                IF @OwnTransaction=1 COMMIT TRANSACTION;
                SELECT CONVERT(bit,1) AS committed,CONVERT(bit,0) AS replayed,@StoryOutcome AS outcome,
                    @Digest AS request_digest,CONVERT(bit,0) AS publishes;
                RETURN;
            END;
            IF @CommandType = N''save_item''
            BEGIN
                DECLARE @PolicyContent int, @CanonicalKey uniqueidentifier;
                DECLARE @PolicyAccess int;
                SELECT @CanonicalKey=record.canonical_key, @PolicyContent = record.content_version,
                       @PolicyAccess = record.access_revision
                FROM dbo.entry_policy_records AS record WITH (UPDLOCK, HOLDLOCK)
                WHERE record.owner_profile_id = @ProfileId
                  AND record.entry_key = @RecordKey
                  AND record.lifecycle = N''active''
                  AND record.canonical_type = CASE @RecordType WHEN N''accomplishment'' THEN N''achievement'' ELSE @RecordType END;

                IF @PolicyAccess IS NULL OR @PolicyAccess <> @ExpectedAccess
                    THROW 52205, ''RESUME_DRAFT_CHANGED'', 1;
                DECLARE @CanonicalRowVersion binary(8);
                IF @RecordType IN(N''role'',N''education'',N''credential'')
                    SELECT @CanonicalRowVersion=row_version FROM dbo.career_chapters WITH(UPDLOCK,HOLDLOCK)
                        WHERE owner_profile_id=@ProfileId AND chapter_key=@CanonicalKey AND deleted_at_utc IS NULL;
                ELSE IF @RecordType=N''skill''
                    SELECT @CanonicalRowVersion=row_version FROM dbo.career_skills WITH(UPDLOCK,HOLDLOCK)
                        WHERE owner_profile_id=@ProfileId AND skill_key=@CanonicalKey AND deleted_at_utc IS NULL;
                ELSE IF @RecordType=N''accomplishment''
                    SELECT @CanonicalRowVersion=row_version FROM dbo.career_achievements WITH(UPDLOCK,HOLDLOCK)
                        WHERE owner_profile_id=@ProfileId AND achievement_key=@CanonicalKey AND deleted_at_utc IS NULL;
                ELSE IF @RecordType=N''knowledge''
                    SELECT @CanonicalRowVersion=row_version FROM dbo.knowledge_items WITH(UPDLOCK,HOLDLOCK)
                        WHERE owner_profile_id=@ProfileId AND knowledge_item_key=@CanonicalKey
                          AND item_status=N''confirmed'' AND classification=N''personal''
                          AND current_version_number=confirmed_version_number;
                IF @ExpectedToken IS NULL OR LEN(@ExpectedToken)<>16
                    OR @ExpectedToken COLLATE Latin1_General_100_BIN2 LIKE ''%[^0-9a-fA-F]%''
                    OR @CanonicalRowVersion IS NULL OR TRY_CONVERT(binary(8),@ExpectedToken,2) IS NULL
                    OR TRY_CONVERT(binary(8),@ExpectedToken,2)<>@CanonicalRowVersion
                    THROW 52205, ''RESUME_DRAFT_CHANGED'', 1;
                SET @ExpectedToken=LOWER(@ExpectedToken);
            END;

            IF @CommandType = N''save_item''
            BEGIN
                MERGE dbo.resume_draft_items WITH (UPDLOCK, HOLDLOCK) AS target
                USING (SELECT @DraftId AS resume_draft_id, @RecordKey AS record_key) AS source
                   ON target.resume_draft_id = source.resume_draft_id
                  AND target.record_key = source.record_key
                WHEN MATCHED THEN
                    UPDATE SET
                        record_type = @RecordType,
                        base_content_token = @ExpectedToken,
                        base_access_revision = @ExpectedAccess,
                        proposed_values_json = ISNULL(@Proposed, N''{}''),
                        intended_permission_expansions_json = @Intended,
                        is_new = 0,
                        updated_at_utc = SYSUTCDATETIME()
                WHEN NOT MATCHED THEN
                    INSERT
                        (resume_draft_id, record_key, record_type, base_content_token,
                         base_access_revision, proposed_values_json,
                         intended_permission_expansions_json, is_new)
                    VALUES
                        (@DraftId, @RecordKey, @RecordType, @ExpectedToken,
                         @ExpectedAccess, ISNULL(@Proposed, N''{}''), @Intended, 0);

                UPDATE dbo.resume_drafts
                SET draft_version = @DraftVersion + 1,
                    updated_at_utc = SYSUTCDATETIME()
                WHERE resume_draft_id = @DraftId;

                INSERT dbo.resume_draft_command_receipts
                    (owner_profile_id, request_id, request_digest, command_type, outcome)
                VALUES
                    (@ProfileId, @RequestId, @Digest, @CommandType, N''saved'');

                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''saved'' AS outcome,
                       @Digest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            IF @CommandType = N''discard_item''
            BEGIN
                DELETE dbo.resume_draft_items
                WHERE resume_draft_id = @DraftId
                  AND record_key = @RecordKey;
                IF @@ROWCOUNT > 0
                    UPDATE dbo.resume_drafts
                    SET draft_version = @DraftVersion + 1,
                        updated_at_utc = SYSUTCDATETIME()
                    WHERE resume_draft_id = @DraftId;

                INSERT dbo.resume_draft_command_receipts
                    (owner_profile_id, request_id, request_digest, command_type, outcome)
                VALUES
                    (@ProfileId, @RequestId, @Digest, @CommandType, N''discarded'');

                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''discarded'' AS outcome,
                       @Digest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            IF @CommandType = N''create_private_item''
            BEGIN

                IF @RecordType=N''knowledge''
                BEGIN
                    IF @Proposed IS NULL OR LEFT(LTRIM(@Proposed),1)<>N''{''
                        OR (SELECT COUNT(*) FROM OPENJSON(@Proposed))<>3
                        OR (SELECT COUNT(DISTINCT [key] COLLATE Latin1_General_100_BIN2) FROM OPENJSON(@Proposed))<>3
                        OR EXISTS(SELECT 1 FROM OPENJSON(@Proposed) WHERE type<>1 OR [key] COLLATE Latin1_General_100_BIN2 NOT IN(N''title'',N''wording'',N''classification''))
                        OR ISNULL(JSON_VALUE(@Proposed,''$.classification''),N'''') COLLATE Latin1_General_100_BIN2<>N''personal''
                        THROW 52204,''RESUME_DRAFT_VALIDATION'',1;
                    DECLARE @StoryTitle nvarchar(max),@StoryWording nvarchar(max),@StoryActor int,@StoryItemId bigint;
                    SELECT @StoryTitle=value FROM OPENJSON(@Proposed) WHERE [key] COLLATE Latin1_General_100_BIN2=N''title'';
                    SELECT @StoryWording=value FROM OPENJSON(@Proposed) WHERE [key] COLLATE Latin1_General_100_BIN2=N''wording'';
                    IF @StoryTitle IS NULL OR DATALENGTH(@StoryTitle)/2 NOT BETWEEN 1 AND 160 OR LEN(LTRIM(RTRIM(@StoryTitle)))=0
                        OR @StoryWording IS NULL OR DATALENGTH(@StoryWording)/2 NOT BETWEEN 1 AND 8000 OR LEN(LTRIM(RTRIM(@StoryWording)))=0
                        THROW 52204,''RESUME_DRAFT_VALIDATION'',1;
                    SELECT @StoryActor=user_id FROM dbo.member_profiles WHERE profile_id=@ProfileId AND active=1;
                    IF EXISTS(SELECT 1 FROM dbo.knowledge_items WITH(UPDLOCK,HOLDLOCK) WHERE knowledge_item_key=@RecordKey)
                        OR EXISTS(SELECT 1 FROM dbo.entry_policy_records WITH(UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId AND entry_key=@RecordKey)
                        THROW 52205,''RESUME_DRAFT_CHANGED'',1;
                    INSERT dbo.knowledge_items(knowledge_item_key,owner_profile_id,item_status,classification,
                        current_version_number,confirmed_version_number,confirmed_by_user_id,confirmed_at_utc)
                      VALUES(@RecordKey,@ProfileId,N''confirmed'',N''personal'',1,1,@StoryActor,SYSUTCDATETIME());
                    SET @StoryItemId=CONVERT(bigint,SCOPE_IDENTITY());
                    INSERT dbo.knowledge_item_versions(knowledge_item_id,owner_profile_id,version_number,title,
                        approved_wording,original_member_wording,body_format,authored_via,saved_by_user_id)
                      VALUES(@StoryItemId,@ProfileId,1,@StoryTitle,@StoryWording,@StoryWording,N''plain'',N''typed'',@StoryActor);
                    INSERT dbo.entry_policy_records(owner_profile_id,entry_key,canonical_type,canonical_key,
                        category,content_version,access_revision,resume_display,visitor_ai,private_assistance_excluded,lifecycle)
                      VALUES(@ProfileId,@RecordKey,N''knowledge'',@RecordKey,N''personal'',1,1,0,0,0,N''active'');
                    -- No implicit Story selection, permission grant, or publication.
                END;
                INSERT dbo.resume_draft_command_receipts
                    (owner_profile_id, request_id, request_digest, command_type, outcome)
                VALUES
                    (@ProfileId, @RequestId, @Digest, @CommandType, N''created'');
                IF @OwnTransaction = 1 COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 0) AS replayed,
                       N''created'' AS outcome,
                       @Digest AS request_digest,
                       CONVERT(bit, 0) AS publishes;
                RETURN;
            END;

            THROW 52204, ''RESUME_DRAFT_VALIDATION'', 1;
            END TRY
            BEGIN CATCH
                IF @OwnTransaction = 1 AND XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationBuildManifestsInternal
    @ProfileId bigint,
    @Revision int,
    @CommandJson nvarchar(max),
    @Display nvarchar(max) OUTPUT,
    @VisitorAi nvarchar(max) OUTPUT,
    @Evidence nvarchar(max) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET @Display = N''{}'';
    SET @VisitorAi = N''{}'';
    SET @Evidence = N''{}'';

    DECLARE @StoryEntryKey uniqueidentifier;
    IF EXISTS(SELECT 1 FROM OPENJSON(@CommandJson) WHERE [key] COLLATE Latin1_General_100_BIN2=N''story_entry_key'')
        SET @StoryEntryKey=TRY_CONVERT(uniqueidentifier,JSON_VALUE(@CommandJson,''$.story_entry_key''));
    ELSE
        SELECT @StoryEntryKey=TRY_CONVERT(uniqueidentifier,item.[key])
          FROM dbo.resume_sharing_state AS sharing
          JOIN dbo.resume_publication_revisions AS revision ON revision.owner_profile_id=sharing.owner_profile_id
            AND revision.publication_revision=sharing.current_revision
          CROSS APPLY OPENJSON(revision.display_json) AS item
          WHERE sharing.owner_profile_id=@ProfileId AND JSON_VALUE(item.value,''$.presentation_section'')=N''story'';
    DECLARE @EntryKey uniqueidentifier;
    DECLARE @CanonicalType nvarchar(40),@PersonalRevision varchar(16),@PersonalRowversion binary(8);
    DECLARE @ContentVersion int;
    DECLARE @AccessRevision int;
    DECLARE @ResumeDisplay bit;
    DECLARE @VisitorAiFlag bit;
    DECLARE @CanonicalKey uniqueidentifier;
    DECLARE @Fields nvarchar(max);
    DECLARE @Bytes varbinary(max);
    DECLARE @Digest char(64);
    DECLARE @Wording nvarchar(max);

    DECLARE entry_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT policy.entry_key, policy.canonical_type, policy.content_version, policy.access_revision,
               policy.resume_display, policy.visitor_ai, policy.canonical_key
          FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
         WHERE policy.owner_profile_id = @ProfileId
           AND policy.lifecycle = N''active''
           AND (policy.resume_display = 1 OR policy.visitor_ai = 1)
         ORDER BY policy.entry_key;
    OPEN entry_cursor;
    FETCH NEXT FROM entry_cursor INTO @EntryKey, @CanonicalType, @ContentVersion, @AccessRevision,
        @ResumeDisplay, @VisitorAiFlag, @CanonicalKey;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        DECLARE @EntryKeyText nvarchar(36)=LOWER(CONVERT(nvarchar(36),@EntryKey));
        DECLARE @ExpectedContent int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, CONCAT(N''$.expected_by_entry."'', @EntryKeyText, N''".content_version'')));
        DECLARE @ExpectedAccess int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, CONCAT(N''$.expected_by_entry."'', @EntryKeyText, N''".access_revision'')));
        IF @ExpectedContent IS NOT NULL AND @ExpectedContent <> @ContentVersion
            THROW 54023, ''The publication changed.'', 1;
        IF @ExpectedAccess IS NOT NULL AND @ExpectedAccess <> @AccessRevision
            THROW 54023, ''The publication changed.'', 1;

        SELECT @Fields = (
            SELECT
                @CanonicalType AS canonical_type,
                exp.role_title,
                exp.employer_name,
                chapter.location_text,
                COALESCE(knowledge_version.approved_wording, chapter.approved_wording, chapter.summary) AS summary,
                CONVERT(nvarchar(40), chapter.start_date, 23) AS start_date,
                CONVERT(nvarchar(40), chapter.end_date, 23) AS end_date,
                chapter.date_precision,
                exp.employment_type,
                exp.current_role,
                COALESCE(knowledge_version.title,chapter.title) AS title,
                edu.institution_name,
                edu.degree_name,
                edu.field_of_study,
                edu.education_status,
                edu.grade_text,
                cred.credential_name,
                cred.issuer_name,
                cred.credential_identifier,
                CONVERT(nvarchar(40), cred.issue_date, 23) AS issue_date,
                CONVERT(nvarchar(40), cred.expiration_date, 23) AS expiration_date,
                skill.skill_name AS name,
                COALESCE(chapter.summary, skill.skill_summary) AS skill_summary,
                COALESCE(knowledge_version.approved_wording,chapter.approved_wording,ach.approved_wording,ach.original_member_wording) AS wording,
                ach.metric_value,
                ach.metric_label,
                CONVERT(bit, NULL) AS accomplishment_to_achievement,
                parent.canonical_type AS parent_canonical_type
            FROM dbo.entry_policy_records AS policy
            LEFT JOIN dbo.knowledge_items AS knowledge
              ON knowledge.owner_profile_id=policy.owner_profile_id AND knowledge.knowledge_item_key=policy.canonical_key
             AND policy.canonical_type=N''knowledge'' AND knowledge.item_status=N''confirmed''
             AND knowledge.classification=N''personal'' AND knowledge.current_version_number=knowledge.confirmed_version_number
            LEFT JOIN dbo.knowledge_item_versions AS knowledge_version
              ON knowledge_version.owner_profile_id=knowledge.owner_profile_id
             AND knowledge_version.knowledge_item_id=knowledge.knowledge_item_id
             AND knowledge_version.version_number=knowledge.current_version_number
            LEFT JOIN dbo.career_chapters AS chapter
              ON chapter.owner_profile_id = policy.owner_profile_id
             AND chapter.chapter_key = policy.canonical_key
            LEFT JOIN dbo.career_experiences AS exp
              ON exp.chapter_id = chapter.chapter_id AND exp.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_education AS edu
              ON edu.chapter_id = chapter.chapter_id AND edu.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_credentials AS cred
              ON cred.chapter_id = chapter.chapter_id AND cred.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_skills AS skill
              ON skill.owner_profile_id = policy.owner_profile_id
             AND skill.skill_key = policy.canonical_key
            LEFT JOIN dbo.career_achievements AS ach
              ON ach.owner_profile_id = policy.owner_profile_id
             AND ach.achievement_key = policy.canonical_key
            LEFT JOIN dbo.career_projects AS proj
              ON proj.chapter_id = chapter.chapter_id AND proj.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.entry_policy_records AS parent
              ON parent.owner_profile_id = policy.owner_profile_id
             AND parent.entry_key = policy.parent_entry_key
            WHERE policy.owner_profile_id = @ProfileId
              AND policy.entry_key = @EntryKey
            FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
        );

        IF @Fields IS NULL OR ISJSON(@Fields) <> 1
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType=N''knowledge'' AND JSON_VALUE(@Fields,''$.summary'') IS NULL THROW 54015,''Canonical personal entry is unavailable.'',1;
        IF @CanonicalType = N''education'' AND JSON_VALUE(@Fields, ''$.institution_name'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''credential'' AND JSON_VALUE(@Fields, ''$.credential_name'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''skill'' AND JSON_VALUE(@Fields, ''$.name'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''achievement'' AND JSON_VALUE(@Fields, ''$.wording'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;

        SELECT @PersonalRevision=NULL,@PersonalRowversion=NULL;
        IF @CanonicalType=N''knowledge''
        BEGIN
            SELECT @PersonalRowversion=row_version FROM dbo.knowledge_items
              WHERE owner_profile_id=@ProfileId AND knowledge_item_key=@CanonicalKey
                AND item_status=N''confirmed'' AND classification=N''personal'' AND current_version_number=confirmed_version_number;
            IF @PersonalRowversion IS NULL THROW 54015,''Canonical personal entry is unavailable.'',1;
            SET @PersonalRevision=CONVERT(varchar(16),@PersonalRowversion,2);
        END;
        EXEC dbo.usp_ResumePublicationEncodeSourceInternal
            @FieldsJson = @Fields, @Bytes = @Bytes OUTPUT, @Digest = @Digest OUTPUT;

        DECLARE @EvidenceKey nvarchar(120) = CONCAT(N''evidence:'', @EntryKeyText, N'':'', CONVERT(nvarchar(20), @Revision));
        INSERT dbo.resume_publication_evidence
            (owner_profile_id, entry_key, evidence_version_key, codec, canonical_token,
             policy_content_version, access_revision, content_bytes, content_sha256,
             display_eligible, visitor_ai_eligible)
        VALUES
            (@ProfileId, @EntryKey, @EvidenceKey, N''resume-canonical-source.v1'',
             CONVERT(nvarchar(100), @ContentVersion), @ContentVersion, @AccessRevision,
             @Bytes, @Digest, @ResumeDisplay, @VisitorAiFlag);
        IF CONVERT(nvarchar(20), SESSION_CONTEXT(N''resume_publication_proof_fail_after_evidence'')) = N''1''
            THROW 54999, ''PROOF_INJECTED_FAILURE'', 1;

        SET @Wording = COALESCE(JSON_QUERY(@Fields, N''$''), N''{}'');
        IF @ResumeDisplay = 1
            SET @Display = JSON_MODIFY(@Display, CONCAT(N''$."'', @EntryKeyText, N''"''),
                JSON_QUERY(CONCAT(N''{"canonical_type":"'', @CanonicalType, N''","canonical_revision":"'', ISNULL(@PersonalRevision,''''), N''","presentation_section":"'', CASE WHEN @EntryKey=@StoryEntryKey AND @CanonicalType=N''knowledge'' THEN N''story'' ELSE N''entry'' END, N''","wording":'', @Wording, N'',"evidence_sha256":"'', @Digest, N''","canonical_token":"'', CONVERT(nvarchar(100), @ContentVersion), N''"}'')));
        IF @VisitorAiFlag = 1
            SET @VisitorAi = JSON_MODIFY(@VisitorAi, CONCAT(N''$."'', @EntryKeyText, N''"''),
                JSON_QUERY(CONCAT(N''{"canonical_type":"'', @CanonicalType, N''","canonical_revision":"'', ISNULL(@PersonalRevision,''''), N''","presentation_section":"'', CASE WHEN @EntryKey=@StoryEntryKey AND @CanonicalType=N''knowledge'' THEN N''story'' ELSE N''entry'' END, N''","wording":'', @Wording, N'',"evidence_sha256":"'', @Digest, N''","canonical_token":"'', CONVERT(nvarchar(100), @ContentVersion), N''"}'')));
        SET @Evidence = JSON_MODIFY(@Evidence, CONCAT(N''$."'', @EntryKeyText, N''"''),
            JSON_QUERY(CONCAT(N''{"content_sha256":"'', @Digest, N''","codec":"resume-canonical-source.v1"}'')));

        FETCH NEXT FROM entry_cursor INTO @EntryKey, @CanonicalType, @ContentVersion, @AccessRevision,
            @ResumeDisplay, @VisitorAiFlag, @CanonicalKey;
    END;
    CLOSE entry_cursor;
    DEALLOCATE entry_cursor;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_ListResumePublicationPolicyForOwner
    @UserKey nvarchar(300)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 54021, ''Owner is unavailable.'', 1;

    SELECT policy.entry_key, policy.canonical_type, policy.canonical_key, policy.category,
           policy.parent_entry_key, policy.content_version, policy.access_revision,
           policy.resume_display, policy.visitor_ai, policy.private_assistance_excluded,
           policy.lifecycle, policy.recover_until_utc,
           CASE WHEN policy.canonical_type=N''knowledge'' THEN (SELECT knowledge_version.title,knowledge_version.approved_wording AS wording,knowledge.classification FOR JSON PATH,WITHOUT_ARRAY_WRAPPER) ELSE (
               SELECT exp.role_title, exp.employer_name, chapter.location_text,
                      COALESCE(knowledge_version.approved_wording, chapter.approved_wording, chapter.summary) AS summary,
                      CONVERT(nvarchar(40), chapter.start_date, 23) AS start_date,
                      CONVERT(nvarchar(40), chapter.end_date, 23) AS end_date,
                      chapter.date_precision, exp.employment_type, exp.current_role,
                      COALESCE(knowledge_version.title,chapter.title) AS title, edu.institution_name, edu.degree_name,
                      edu.field_of_study, edu.education_status, edu.grade_text,
                      cred.credential_name, cred.issuer_name, cred.credential_identifier,
                      CONVERT(nvarchar(40), cred.issue_date, 23) AS issue_date,
                      CONVERT(nvarchar(40), cred.expiration_date, 23) AS expiration_date,
                      skill.skill_name AS name, skill.skill_summary,
                      COALESCE(knowledge_version.approved_wording,chapter.approved_wording,ach.approved_wording,ach.original_member_wording) AS wording,
                      ach.metric_value, ach.metric_label
                 FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
           ) END AS values_json
      FROM dbo.entry_policy_records AS policy
      LEFT JOIN dbo.knowledge_items AS knowledge
              ON knowledge.owner_profile_id=policy.owner_profile_id AND knowledge.knowledge_item_key=policy.canonical_key
             AND policy.canonical_type=N''knowledge'' AND knowledge.item_status=N''confirmed''
             AND knowledge.classification=N''personal'' AND knowledge.current_version_number=knowledge.confirmed_version_number
            LEFT JOIN dbo.knowledge_item_versions AS knowledge_version
              ON knowledge_version.owner_profile_id=knowledge.owner_profile_id
             AND knowledge_version.knowledge_item_id=knowledge.knowledge_item_id
             AND knowledge_version.version_number=knowledge.current_version_number
            LEFT JOIN dbo.career_chapters AS chapter
        ON chapter.owner_profile_id = policy.owner_profile_id
       AND chapter.chapter_key = policy.canonical_key
      LEFT JOIN dbo.career_experiences AS exp
        ON exp.owner_profile_id = chapter.owner_profile_id AND exp.chapter_id = chapter.chapter_id
      LEFT JOIN dbo.career_education AS edu
        ON edu.owner_profile_id = chapter.owner_profile_id AND edu.chapter_id = chapter.chapter_id
      LEFT JOIN dbo.career_credentials AS cred
        ON cred.owner_profile_id = chapter.owner_profile_id AND cred.chapter_id = chapter.chapter_id
      LEFT JOIN dbo.career_skills AS skill
        ON skill.owner_profile_id = policy.owner_profile_id AND skill.skill_key = policy.canonical_key
      LEFT JOIN dbo.career_achievements AS ach
        ON ach.owner_profile_id = policy.owner_profile_id AND ach.achievement_key = policy.canonical_key
     WHERE policy.owner_profile_id = @ProfileId
       AND policy.lifecycle <> N''permanently_deleted''
     ORDER BY policy.category, policy.entry_key;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyCanonicalInternal
    @ProfileId bigint,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @Type nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
    DECLARE @EntryKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.entry_key''));
    DECLARE @Now datetime2(7) = SYSUTCDATETIME();

    IF @Type IN (N''edit'', N''correct'')
    BEGIN
        IF @EntryKey IS NULL
            THROW 54026, ''Entry is unavailable.'', 1;
        DECLARE @ExpectedContent int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_content_version''));
        DECLARE @ExpectedAccess int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_access_revision''));
        IF @ExpectedContent IS NULL OR @ExpectedAccess IS NULL
            THROW 54027, ''Expected content and access versions are required.'', 1;

        DECLARE @Lifecycle nvarchar(30);
        DECLARE @ContentVersion int;
        DECLARE @AccessRevision int;
        DECLARE @CanonicalType nvarchar(40);
        DECLARE @CanonicalKey uniqueidentifier;
        SELECT @Lifecycle = policy.lifecycle,
               @ContentVersion = policy.content_version,
               @AccessRevision = policy.access_revision,
               @CanonicalType = policy.canonical_type,
               @CanonicalKey = policy.canonical_key
          FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
         WHERE policy.owner_profile_id = @ProfileId
           AND policy.entry_key = @EntryKey;
        IF @CanonicalKey IS NULL
            THROW 54026, ''Entry is unavailable.'', 1;
        IF @Lifecycle <> N''active''
            THROW 54028, ''Entry is not active.'', 1;
        IF @ContentVersion <> @ExpectedContent OR @AccessRevision <> @ExpectedAccess
            THROW 54023, ''The publication changed.'', 1;

        IF @CanonicalType IN (N''role'', N''education'', N''credential'', N''project'')
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM dbo.career_chapters AS chapter WITH (UPDLOCK, HOLDLOCK)
                 WHERE chapter.owner_profile_id = @ProfileId
                   AND chapter.chapter_key = @CanonicalKey)
                THROW 54026, ''Canonical source is unavailable.'', 1;
        END
        ELSE IF @CanonicalType = N''skill''
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM dbo.career_skills AS skill WITH (UPDLOCK, HOLDLOCK)
                 WHERE skill.owner_profile_id = @ProfileId
                   AND skill.skill_key = @CanonicalKey)
                THROW 54026, ''Canonical source is unavailable.'', 1;
        END
        ELSE IF @CanonicalType = N''achievement''
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM dbo.career_achievements AS achievement WITH (UPDLOCK, HOLDLOCK)
                 WHERE achievement.owner_profile_id = @ProfileId
                   AND achievement.achievement_key = @CanonicalKey)
                THROW 54026, ''Canonical source is unavailable.'', 1;
        END
        ELSE IF @CanonicalType=N''knowledge''
        BEGIN
            IF NOT EXISTS(SELECT 1 FROM dbo.knowledge_items WITH(UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId AND knowledge_item_key=@CanonicalKey AND item_status=N''confirmed'' AND classification=N''personal'' AND current_version_number=confirmed_version_number) THROW 54026,''Canonical personal entry is unavailable.'',1;
        END
        ELSE
            THROW 54026, ''Canonical source is unavailable.'', 1;

        -- My Data shows summary and wording as aliases for the same approved
        -- chapter text. A form can change either field while submitting both.
        -- Compare exact UTF-16 bytes with the displayed value so a case-only
        -- edit counts and an unchanged alias cannot undo the edited one.
        -- Summary wins only when both aliases changed.
        UPDATE chapter
           SET summary = COALESCE(next_wording.wording, chapter.summary),
               approved_wording = COALESCE(next_wording.wording, chapter.approved_wording),
               title = COALESCE(
                    JSON_VALUE(@CommandJson, ''$.values.role_title''),
                    JSON_VALUE(@CommandJson, ''$.values.title''),
                    chapter.title),
               updated_at_utc = @Now
          FROM dbo.career_chapters AS chapter WITH (UPDLOCK, HOLDLOCK)
          JOIN dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
            ON policy.owner_profile_id = chapter.owner_profile_id
           AND policy.canonical_key = chapter.chapter_key
          CROSS APPLY (SELECT
              COALESCE(JSON_VALUE(@CommandJson, ''$.values.summary''),
                       JSON_VALUE(@CommandJson, ''$.fields.summary'')) AS submitted_summary,
              COALESCE(JSON_VALUE(@CommandJson, ''$.values.wording''),
                       JSON_VALUE(@CommandJson, ''$.fields.wording'')) AS submitted_wording,
              COALESCE(chapter.approved_wording, chapter.summary) AS displayed_wording
          ) AS submitted
          CROSS APPLY (SELECT CASE
              WHEN submitted.submitted_summary IS NOT NULL
                   AND (DATALENGTH(submitted.submitted_summary) <> DATALENGTH(submitted.displayed_wording)
                        OR CONVERT(varbinary(max), submitted.submitted_summary)
                           <> CONVERT(varbinary(max), submitted.displayed_wording))
                  THEN submitted.submitted_summary
              WHEN submitted.submitted_wording IS NOT NULL
                   AND (DATALENGTH(submitted.submitted_wording) <> DATALENGTH(submitted.displayed_wording)
                        OR CONVERT(varbinary(max), submitted.submitted_wording)
                           <> CONVERT(varbinary(max), submitted.displayed_wording))
                  THEN submitted.submitted_wording
              ELSE COALESCE(submitted.submitted_summary, submitted.submitted_wording)
          END AS wording) AS next_wording
         WHERE policy.owner_profile_id = @ProfileId
           AND policy.entry_key = @EntryKey;
        IF @CanonicalType IN (N''role'', N''education'', N''credential'', N''project'')
           AND @@ROWCOUNT <> 1
            THROW 54029, ''Canonical source did not change.'', 1;

        UPDATE dbo.career_experiences WITH (UPDLOCK, HOLDLOCK)
           SET role_title = COALESCE(JSON_VALUE(@CommandJson, ''$.values.role_title''), role_title),
               employer_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.employer_name''), employer_name),
               employment_type = COALESCE(JSON_VALUE(@CommandJson, ''$.values.employment_type''), employment_type),
               current_role = COALESCE(TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.values.current_role'')), current_role)
         WHERE owner_profile_id = @ProfileId
           AND chapter_id IN (
                SELECT chapter.chapter_id
                  FROM dbo.career_chapters AS chapter
                  JOIN dbo.entry_policy_records AS policy
                    ON policy.canonical_key = chapter.chapter_key
                   AND policy.owner_profile_id = chapter.owner_profile_id
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);

        UPDATE dbo.career_education WITH (UPDLOCK, HOLDLOCK)
           SET institution_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.institution_name''), institution_name),
               degree_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.degree_name''), degree_name),
               field_of_study = COALESCE(JSON_VALUE(@CommandJson, ''$.values.field_of_study''), field_of_study),
               education_status = COALESCE(JSON_VALUE(@CommandJson, ''$.values.education_status''), education_status),
               grade_text = COALESCE(JSON_VALUE(@CommandJson, ''$.values.grade_text''), grade_text)
         WHERE owner_profile_id = @ProfileId
           AND chapter_id IN (
                SELECT chapter.chapter_id
                  FROM dbo.career_chapters AS chapter
                  JOIN dbo.entry_policy_records AS policy
                    ON policy.canonical_key = chapter.chapter_key
                   AND policy.owner_profile_id = chapter.owner_profile_id
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);

        UPDATE dbo.career_credentials WITH (UPDLOCK, HOLDLOCK)
           SET credential_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.credential_name''), credential_name),
               issuer_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.issuer_name''), issuer_name),
               credential_identifier = COALESCE(JSON_VALUE(@CommandJson, ''$.values.credential_identifier''), credential_identifier),
               issue_date = COALESCE(TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.issue_date'')), issue_date),
               expiration_date = COALESCE(TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.expiration_date'')), expiration_date)
         WHERE owner_profile_id = @ProfileId
           AND chapter_id IN (
                SELECT chapter.chapter_id
                  FROM dbo.career_chapters AS chapter
                  JOIN dbo.entry_policy_records AS policy
                    ON policy.canonical_key = chapter.chapter_key
                   AND policy.owner_profile_id = chapter.owner_profile_id
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);

        UPDATE dbo.career_projects WITH (UPDLOCK, HOLDLOCK)
           SET project_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.title''), JSON_VALUE(@CommandJson, ''$.values.project_name''), project_name),
               project_role = COALESCE(JSON_VALUE(@CommandJson, ''$.values.project_role''), project_role)
         WHERE owner_profile_id = @ProfileId
           AND chapter_id IN (
                SELECT chapter.chapter_id
                  FROM dbo.career_chapters AS chapter
                  JOIN dbo.entry_policy_records AS policy
                    ON policy.canonical_key = chapter.chapter_key
                   AND policy.owner_profile_id = chapter.owner_profile_id
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);

        UPDATE dbo.career_skills WITH (UPDLOCK, HOLDLOCK)
           SET skill_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.name''), skill_name),
               skill_summary = COALESCE(
                    JSON_VALUE(@CommandJson, ''$.values.skill_summary''),
                    JSON_VALUE(@CommandJson, ''$.values.summary''),
                    skill_summary),
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND skill_key IN (
                SELECT policy.canonical_key
                  FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);
        IF @CanonicalType = N''skill'' AND @@ROWCOUNT <> 1
            THROW 54029, ''Canonical source did not change.'', 1;

        UPDATE dbo.career_achievements WITH (UPDLOCK, HOLDLOCK)
           SET approved_wording = COALESCE(
                    JSON_VALUE(@CommandJson, ''$.values.wording''),
                    JSON_VALUE(@CommandJson, ''$.fields.wording''),
                    approved_wording),
               metric_value = COALESCE(JSON_VALUE(@CommandJson, ''$.values.metric_value''), metric_value),
               metric_label = COALESCE(JSON_VALUE(@CommandJson, ''$.values.metric_label''), metric_label),
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND achievement_key IN (
                SELECT policy.canonical_key
                  FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);
        IF @CanonicalType = N''achievement'' AND @@ROWCOUNT <> 1
            THROW 54029, ''Canonical source did not change.'', 1;


        IF @CanonicalType=N''knowledge''
        BEGIN
            DECLARE @PersonalFields nvarchar(max)=COALESCE(JSON_QUERY(@CommandJson,''$.values''),JSON_QUERY(@CommandJson,''$.fields''));
            IF @PersonalFields IS NULL OR LEFT(LTRIM(@PersonalFields),1)<>N''{''
              OR EXISTS(SELECT 1 FROM OPENJSON(@PersonalFields) WHERE type<>1 OR [key] COLLATE Latin1_General_100_BIN2 NOT IN(N''title'',N''wording'',N''classification''))
              OR EXISTS(SELECT 1 FROM OPENJSON(@PersonalFields) GROUP BY [key] COLLATE Latin1_General_100_BIN2 HAVING COUNT(*)<>1)
                THROW 54027,''Invalid personal entry fields.'',1;
            DECLARE @PersonalId bigint,@PersonalVersion int,@PersonalActor int,@PersonalToken binary(8),
                @PersonalTitle nvarchar(max),@PersonalWording nvarchar(max),@PersonalOriginal nvarchar(max);
            SELECT @PersonalId=item.knowledge_item_id,@PersonalVersion=item.current_version_number,@PersonalToken=item.row_version,
                @PersonalTitle=version_record.title,@PersonalWording=version_record.approved_wording,@PersonalOriginal=version_record.original_member_wording
              FROM dbo.knowledge_items AS item WITH(UPDLOCK,HOLDLOCK)
              JOIN dbo.knowledge_item_versions AS version_record WITH(UPDLOCK,HOLDLOCK)
                ON version_record.knowledge_item_id=item.knowledge_item_id AND version_record.owner_profile_id=item.owner_profile_id
                AND version_record.version_number=item.current_version_number
              WHERE item.owner_profile_id=@ProfileId AND item.knowledge_item_key=@CanonicalKey;
            IF @PersonalOriginal IS NULL THROW 54026,''Personal entry source is unavailable.'',1;
            SELECT @PersonalTitle=value FROM OPENJSON(@PersonalFields) WHERE [key] COLLATE Latin1_General_100_BIN2=N''title'';
            SELECT @PersonalWording=value FROM OPENJSON(@PersonalFields) WHERE [key] COLLATE Latin1_General_100_BIN2=N''wording'';
            IF @PersonalTitle IS NULL OR DATALENGTH(@PersonalTitle)/2 NOT BETWEEN 1 AND 160 OR LEN(LTRIM(RTRIM(@PersonalTitle)))=0
              OR @PersonalWording IS NULL OR DATALENGTH(@PersonalWording)/2 NOT BETWEEN 1 AND 8000 OR LEN(LTRIM(RTRIM(@PersonalWording)))=0
              OR EXISTS(SELECT 1 FROM OPENJSON(@PersonalFields) WHERE [key] COLLATE Latin1_General_100_BIN2=N''classification'' AND value COLLATE Latin1_General_100_BIN2<>N''personal'')
                THROW 54027,''Invalid personal entry wording.'',1;
            SELECT @PersonalActor=user_id FROM dbo.member_profiles WHERE profile_id=@ProfileId AND active=1;
            INSERT dbo.knowledge_item_versions(knowledge_item_id,owner_profile_id,version_number,title,
                approved_wording,original_member_wording,body_format,authored_via,saved_by_user_id)
              VALUES(@PersonalId,@ProfileId,@PersonalVersion+1,@PersonalTitle,@PersonalWording,@PersonalOriginal,N''plain'',N''typed'',@PersonalActor);
            UPDATE dbo.knowledge_items SET current_version_number=@PersonalVersion+1,confirmed_version_number=@PersonalVersion+1,
                confirmed_by_user_id=@PersonalActor,confirmed_at_utc=@Now,updated_at_utc=@Now
              WHERE owner_profile_id=@ProfileId AND knowledge_item_id=@PersonalId AND row_version=@PersonalToken;
            IF @@ROWCOUNT<>1 THROW 54023,''Personal entry changed.'',1;
        END;
        UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
           SET content_version = content_version + 1,
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND entry_key = @EntryKey
           AND lifecycle = N''active''
           AND content_version = @ExpectedContent
           AND access_revision = @ExpectedAccess;
        IF @@ROWCOUNT <> 1
            THROW 54023, ''The publication changed.'', 1;
    END;

    IF @Type = N''change_permissions''
    BEGIN
        DECLARE @PermissionTargets TABLE (
            entry_key uniqueidentifier NULL,
            expected_access_revision int NULL,
            permissions nvarchar(max) NULL
        );
        DECLARE @TargetsJson nvarchar(max) = JSON_QUERY(@CommandJson, ''$.targets'');
        IF EXISTS (SELECT 1 FROM OPENJSON(@CommandJson) WHERE [key] = N''targets'')
        BEGIN
            IF @TargetsJson IS NULL OR LEFT(LTRIM(@TargetsJson), 1) <> N''[''
                THROW 54061, ''Invalid permission targets.'', 1;
            INSERT @PermissionTargets (entry_key, expected_access_revision, permissions)
            SELECT TRY_CONVERT(uniqueidentifier, JSON_VALUE(value, ''$.entry_key'')),
                   TRY_CONVERT(int, JSON_VALUE(value, ''$.expected_access_revision'')),
                   JSON_QUERY(value, ''$.permissions'')
              FROM OPENJSON(@TargetsJson);
        END
        ELSE
            INSERT @PermissionTargets (entry_key, expected_access_revision, permissions)
            VALUES (@EntryKey,
                    TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_access_revision'')),
                    JSON_QUERY(@CommandJson, ''$.permissions''));

        DECLARE @TargetCount int = (SELECT COUNT(*) FROM @PermissionTargets);
        IF @TargetCount = 0 OR EXISTS (
            SELECT 1 FROM @PermissionTargets
             WHERE entry_key IS NULL OR expected_access_revision IS NULL
                OR permissions IS NULL OR LEFT(LTRIM(permissions), 1) <> N''{''
            ) OR EXISTS (
            SELECT entry_key FROM @PermissionTargets GROUP BY entry_key HAVING COUNT(*) > 1
            ) OR EXISTS (
            SELECT 1 FROM @PermissionTargets AS target
             WHERE NOT EXISTS (SELECT 1 FROM OPENJSON(target.permissions))
                OR EXISTS (SELECT 1 FROM OPENJSON(target.permissions) AS field
                            WHERE field.[key] NOT IN (N''resume_display'', N''visitor_ai'', N''private_assistance_excluded'')
                               OR field.[type] <> 3)
            ) OR (@TargetsJson IS NOT NULL AND @EntryKey IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM @PermissionTargets WHERE entry_key = @EntryKey))
            THROW 54061, ''Invalid permission targets.'', 1;

        -- The owner transaction holds the publication lock. Check every target
        -- before changing any policy row; one conflict rolls back the batch.
        IF EXISTS (
            SELECT 1 FROM @PermissionTargets AS target
            LEFT JOIN dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
              ON policy.owner_profile_id = @ProfileId AND policy.entry_key = target.entry_key
            WHERE policy.entry_key IS NULL OR policy.lifecycle <> N''active''
               OR policy.access_revision <> target.expected_access_revision)
            THROW 54014, ''ENTRY_POLICY_CHANGED'', 1;

        UPDATE policy
           SET resume_display = COALESCE(TRY_CONVERT(bit, JSON_VALUE(target.permissions, ''$.resume_display'')), policy.resume_display),
               visitor_ai = COALESCE(TRY_CONVERT(bit, JSON_VALUE(target.permissions, ''$.visitor_ai'')), policy.visitor_ai),
               private_assistance_excluded = COALESCE(TRY_CONVERT(bit, JSON_VALUE(target.permissions, ''$.private_assistance_excluded'')), policy.private_assistance_excluded),
               access_revision = policy.access_revision + 1,
               updated_at_utc = @Now
          FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
          JOIN @PermissionTargets AS target ON target.entry_key = policy.entry_key
         WHERE policy.owner_profile_id = @ProfileId
           AND policy.lifecycle = N''active''
           AND policy.access_revision = target.expected_access_revision;
        IF @@ROWCOUNT <> @TargetCount
            THROW 54014, ''ENTRY_POLICY_CHANGED'', 1;
    END;

    IF @Type = N''delete''
    BEGIN
        UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
           SET lifecycle = N''deleted'',
               resume_display = 0,
               visitor_ai = 0,
               deleted_at_utc = @Now,
               recover_until_utc = DATEADD(day, 30, @Now),
               access_revision = access_revision + 1,
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND (entry_key = @EntryKey OR parent_entry_key = @EntryKey)
           AND lifecycle = N''active'';
    END;

    IF @Type = N''restore''
    BEGIN
        UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
           SET lifecycle = N''active'',
               resume_display = 0,
               visitor_ai = 0,
               deleted_at_utc = NULL,
               recover_until_utc = NULL,
               access_revision = access_revision + 1,
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND entry_key = @EntryKey
           AND lifecycle = N''deleted'';
    END;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_MemberVisitorAiSnapshotInternal
    @UserKey nvarchar(300) = NULL, @ProfileSlug nvarchar(100) = NULL,
    @OwnerPreview bit
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    -- This reader must own its transaction; no caller can retain locks through AI work.
    IF @@TRANCOUNT <> 0 THROW 54201, ''AI source authority is unavailable.'', 1;
    IF @OwnerPreview IS NULL OR (@OwnerPreview = 1 AND (@UserKey IS NULL OR @ProfileSlug IS NOT NULL))
       OR (@OwnerPreview = 0 AND (@ProfileSlug IS NULL OR @UserKey IS NOT NULL))
        THROW 54201, ''AI source authority is unavailable.'', 1;
    BEGIN TRY
    BEGIN TRANSACTION;
    DECLARE @ProfileId bigint, @Subject nvarchar(300), @ProfileVersion varchar(16), @ProfileRowversion binary(8);
    -- Resolve first, then re-prove identity under locks after the sharing lock.
    IF @OwnerPreview = 1
        SELECT @ProfileId=p.profile_id FROM dbo.member_profiles p JOIN dbo.app_users u ON u.id=p.user_id
        WHERE u.user_key=@UserKey AND u.active=1 AND p.active=1;
    ELSE
        SELECT @ProfileId=owner_profile_id FROM dbo.resume_sharing_state WHERE public_slug=@ProfileSlug;
    IF @ProfileId IS NULL THROW 54201, ''AI source authority is unavailable.'', 1;
    DECLARE @Sharing bit=0, @Epoch int=0, @Revision int=0, @Current int=NULL, @Slug nvarchar(100);
    -- Shared E lock order: sharing, sorted policy, draft, publication, media/catalog.
    SELECT @Sharing=sharing_enabled,@Epoch=sharing_epoch,@Revision=publication_revision,
           @Current=current_revision,@Slug=public_slug
      FROM dbo.resume_sharing_state WITH (UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId;
    IF @OwnerPreview=0 AND (@Sharing<>1 OR @Current IS NULL OR @Slug<>@ProfileSlug)
        THROW 54201, ''AI source authority is unavailable.'', 1;
    SELECT @Subject=CONVERT(nvarchar(300),u.user_key),@ProfileRowversion=p.row_version
      FROM dbo.member_profiles p WITH (HOLDLOCK) JOIN dbo.app_users u WITH (HOLDLOCK) ON u.id=p.user_id
      WHERE p.profile_id=@ProfileId AND u.active=1 AND p.active=1;
    IF @Subject IS NULL OR @ProfileRowversion IS NULL OR (@OwnerPreview=1 AND @Subject<>@UserKey)
        THROW 54201, ''AI source authority is unavailable.'', 1;
    SET @ProfileVersion=CONVERT(varchar(16),@ProfileRowversion,2);
    DECLARE @LockEntry uniqueidentifier;
    DECLARE policy_locks CURSOR LOCAL FAST_FORWARD FOR
        SELECT entry_key FROM dbo.entry_policy_records WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId ORDER BY entry_key;
    OPEN policy_locks; FETCH NEXT FROM policy_locks INTO @LockEntry;
    WHILE @@FETCH_STATUS=0 FETCH NEXT FROM policy_locks INTO @LockEntry;
    CLOSE policy_locks; DEALLOCATE policy_locks;
    DECLARE @DraftId bigint, @Draft int=0, @DraftJson nvarchar(max);
    SELECT @DraftId=resume_draft_id,@Draft=draft_version FROM dbo.resume_drafts WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId;
    SELECT @DraftJson=(SELECT record_key,record_type,base_content_token,base_access_revision,
        proposed_values_json,intended_permission_expansions_json,is_new
        FROM dbo.resume_draft_items WITH (HOLDLOCK) WHERE resume_draft_id=@DraftId
        ORDER BY record_key FOR JSON PATH,INCLUDE_NULL_VALUES);
    DECLARE @Visitor nvarchar(max), @Media nvarchar(max), @Reviewed char(64);
    SELECT @Visitor=visitor_ai_json,@Media=media_json,@Reviewed=reviewed_digest
        FROM dbo.resume_publication_revisions WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId AND publication_revision=@Current;
    IF @OwnerPreview=0 AND (@Visitor IS NULL OR ISJSON(@Visitor)<>1 OR ISJSON(@Media)<>1)
        THROW 54201, ''AI source authority is unavailable.'', 1;
    SET @Media=COALESCE(@Media,N''{}'');
    -- Missing/duplicate/foreign/stale manifest members deny the complete guest snapshot.
    IF @OwnerPreview=0 AND (EXISTS(SELECT [key] FROM OPENJSON(@Visitor) GROUP BY [key] HAVING COUNT(*)<>1)
        OR EXISTS(SELECT 1 FROM OPENJSON(@Visitor) j LEFT JOIN dbo.entry_policy_records p
            ON p.owner_profile_id=@ProfileId AND p.entry_key=TRY_CONVERT(uniqueidentifier,j.[key])
            WHERE LEN(j.[key])<>36 OR p.entry_key IS NULL OR p.lifecycle<>N''active'' OR p.visitor_ai<>1))
        THROW 54201, ''AI source authority is unavailable.'', 1;
    DECLARE @Entries table(entry_key uniqueidentifier PRIMARY KEY,payload nvarchar(max));
    DECLARE @EntryKey uniqueidentifier,@CanonicalType nvarchar(40),@ContentVersion int,@Access int,
        @Display bit,@Ai bit,@CanonicalKey uniqueidentifier,@Parent uniqueidentifier;
    DECLARE entry_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT p.entry_key,p.canonical_type,p.content_version,p.access_revision,p.resume_display,p.visitor_ai,p.canonical_key,p.parent_entry_key
        FROM dbo.entry_policy_records p WHERE p.owner_profile_id=@ProfileId AND p.lifecycle=N''active''
        AND (@OwnerPreview=1 OR (p.visitor_ai=1 AND EXISTS(SELECT 1 FROM OPENJSON(@Visitor) j WHERE TRY_CONVERT(uniqueidentifier,j.[key])=p.entry_key)))
        ORDER BY p.entry_key;
    OPEN entry_cursor;
    FETCH NEXT FROM entry_cursor INTO @EntryKey,@CanonicalType,@ContentVersion,@Access,@Display,@Ai,@CanonicalKey,@Parent;
    WHILE @@FETCH_STATUS=0
    BEGIN
        IF @CanonicalType NOT IN (N''role'',N''education'',N''credential'',N''skill'',N''achievement'',N''project'',N''knowledge'')
            THROW 54201, ''AI source authority is unavailable.'', 1;
        DECLARE @ParentVersion nvarchar(300)=N''none'';
        IF @Parent IS NOT NULL
        BEGIN
            SET @ParentVersion=NULL;
            SELECT @ParentVersion=CONCAT(LOWER(CONVERT(nvarchar(36),entry_key)),N'':'',content_version,N'':'',access_revision,N'':'',lifecycle)
            FROM dbo.entry_policy_records WHERE owner_profile_id=@ProfileId AND entry_key=@Parent AND lifecycle=N''active'';
            IF @ParentVersion IS NULL THROW 54201, ''AI source authority is unavailable.'', 1;
        END;
        -- Materialize the eight bytes before style-2 text encoding.
        DECLARE @CanonicalRowversion binary(8)=NULL;
        SELECT @CanonicalRowversion=CASE
            WHEN @CanonicalType=N''skill'' THEN s.row_version
            WHEN @CanonicalType=N''achievement'' THEN a.row_version
            WHEN @CanonicalType=N''role'' AND EXISTS(SELECT 1 FROM dbo.career_experiences x WITH (HOLDLOCK) WHERE x.chapter_id=c.chapter_id AND x.owner_profile_id=@ProfileId) THEN c.row_version
            WHEN @CanonicalType=N''education'' AND EXISTS(SELECT 1 FROM dbo.career_education x WITH (HOLDLOCK) WHERE x.chapter_id=c.chapter_id AND x.owner_profile_id=@ProfileId) THEN c.row_version
            WHEN @CanonicalType=N''credential'' AND EXISTS(SELECT 1 FROM dbo.career_credentials x WITH (HOLDLOCK) WHERE x.chapter_id=c.chapter_id AND x.owner_profile_id=@ProfileId) THEN c.row_version
            WHEN @CanonicalType=N''project'' AND EXISTS(SELECT 1 FROM dbo.career_projects x WITH (HOLDLOCK) WHERE x.chapter_id=c.chapter_id AND x.owner_profile_id=@ProfileId) THEN c.row_version
            WHEN @CanonicalType=N''knowledge'' THEN k.row_version END
        FROM dbo.entry_policy_records p
        LEFT JOIN dbo.knowledge_items k WITH(HOLDLOCK) ON k.owner_profile_id=p.owner_profile_id
          AND k.knowledge_item_key=p.canonical_key AND k.item_status=N''confirmed'' AND k.classification=N''personal''
          AND k.current_version_number=k.confirmed_version_number
        LEFT JOIN dbo.career_chapters c WITH (HOLDLOCK) ON c.owner_profile_id=p.owner_profile_id AND c.chapter_key=p.canonical_key AND c.deleted_at_utc IS NULL
        LEFT JOIN dbo.career_achievements a WITH (HOLDLOCK) ON a.owner_profile_id=p.owner_profile_id AND a.achievement_key=p.canonical_key AND a.deleted_at_utc IS NULL
        LEFT JOIN dbo.career_skills s WITH (HOLDLOCK) ON s.owner_profile_id=p.owner_profile_id AND s.skill_key=p.canonical_key AND s.deleted_at_utc IS NULL
        WHERE p.owner_profile_id=@ProfileId AND p.entry_key=@EntryKey;
        IF @CanonicalRowversion IS NULL THROW 54201, ''AI source authority is unavailable.'', 1;
        DECLARE @CanonicalRevision varchar(16)=CONVERT(varchar(16),@CanonicalRowversion,2);
        DECLARE @Fields nvarchar(max),@Bytes varbinary(max),@Digest char(64);
        SELECT @Fields = (
            SELECT
                @CanonicalType AS canonical_type,
                exp.role_title,
                exp.employer_name,
                chapter.location_text,
                COALESCE(knowledge_version.approved_wording, chapter.approved_wording, chapter.summary) AS summary,
                CONVERT(nvarchar(40), chapter.start_date, 23) AS start_date,
                CONVERT(nvarchar(40), chapter.end_date, 23) AS end_date,
                chapter.date_precision,
                exp.employment_type,
                exp.current_role,
                COALESCE(knowledge_version.title,chapter.title) AS title,
                edu.institution_name,
                edu.degree_name,
                edu.field_of_study,
                edu.education_status,
                edu.grade_text,
                cred.credential_name,
                cred.issuer_name,
                cred.credential_identifier,
                CONVERT(nvarchar(40), cred.issue_date, 23) AS issue_date,
                CONVERT(nvarchar(40), cred.expiration_date, 23) AS expiration_date,
                skill.skill_name AS name,
                COALESCE(chapter.summary, skill.skill_summary) AS skill_summary,
                COALESCE(knowledge_version.approved_wording,chapter.approved_wording,ach.approved_wording,ach.original_member_wording) AS wording,
                ach.metric_value,
                ach.metric_label,
                CONVERT(bit, NULL) AS accomplishment_to_achievement,
                parent.canonical_type AS parent_canonical_type
            FROM dbo.entry_policy_records AS policy
            LEFT JOIN dbo.knowledge_items AS knowledge
              ON knowledge.owner_profile_id=policy.owner_profile_id AND knowledge.knowledge_item_key=policy.canonical_key
             AND policy.canonical_type=N''knowledge'' AND knowledge.item_status=N''confirmed''
             AND knowledge.classification=N''personal'' AND knowledge.current_version_number=knowledge.confirmed_version_number
            LEFT JOIN dbo.knowledge_item_versions AS knowledge_version
              ON knowledge_version.owner_profile_id=knowledge.owner_profile_id
             AND knowledge_version.knowledge_item_id=knowledge.knowledge_item_id
             AND knowledge_version.version_number=knowledge.current_version_number
            LEFT JOIN dbo.career_chapters AS chapter WITH (HOLDLOCK)
              ON chapter.owner_profile_id = policy.owner_profile_id
             AND chapter.chapter_key = policy.canonical_key
            LEFT JOIN dbo.career_experiences AS exp WITH (HOLDLOCK)
              ON exp.chapter_id = chapter.chapter_id AND exp.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_education AS edu WITH (HOLDLOCK)
              ON edu.chapter_id = chapter.chapter_id AND edu.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_credentials AS cred WITH (HOLDLOCK)
              ON cred.chapter_id = chapter.chapter_id AND cred.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_skills AS skill WITH (HOLDLOCK)
              ON skill.owner_profile_id = policy.owner_profile_id
             AND skill.skill_key = policy.canonical_key
            LEFT JOIN dbo.career_achievements AS ach WITH (HOLDLOCK)
              ON ach.owner_profile_id = policy.owner_profile_id
             AND ach.achievement_key = policy.canonical_key
            LEFT JOIN dbo.career_projects AS proj WITH (HOLDLOCK)
              ON proj.chapter_id = chapter.chapter_id AND proj.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.entry_policy_records AS parent
              ON parent.owner_profile_id = policy.owner_profile_id
             AND parent.entry_key = policy.parent_entry_key
            WHERE policy.owner_profile_id = @ProfileId
              AND policy.entry_key = @EntryKey
            FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
        );
        EXEC dbo.usp_ResumePublicationEncodeSourceInternal @FieldsJson=@Fields,@Bytes=@Bytes OUTPUT,@Digest=@Digest OUTPUT;
        DECLARE @EvidenceBytes varbinary(max)=@Bytes,@EvidenceDigest char(64)=@Digest,
            @EvidenceKey nvarchar(200)=CONCAT(N''candidate:'',LOWER(CONVERT(nvarchar(36),@EntryKey)),N'':'',@ContentVersion,N'':'',@Access,N'':'',@Digest),
            @EvidenceVersion int=@ContentVersion,@EvidenceDisplay bit=@Display,@EvidenceAi bit=@Ai,
            @EvidenceContent int=@ContentVersion,@EvidenceAccess int=@Access,@Codec nvarchar(80)=N''resume-canonical-source.v1'',
            @Token nvarchar(100)=CONVERT(nvarchar(100),@ContentVersion);
        IF @OwnerPreview=0
        BEGIN
            DECLARE @Member nvarchar(max);
            SELECT @Member=[value] FROM OPENJSON(@Visitor) WHERE TRY_CONVERT(uniqueidentifier,[key])=@EntryKey;
            IF JSON_VALUE(@Member,''$.evidence_sha256'')<>@Digest OR JSON_VALUE(@Member,''$.canonical_token'')<>@Token
               OR JSON_VALUE(@Member,''$.evidence_sha256'') IS NULL OR JSON_VALUE(@Member,''$.canonical_token'') IS NULL
                THROW 54201, ''AI source authority is unavailable.'', 1;
            SET @EvidenceKey=NULL;
            SELECT TOP (1) @EvidenceKey=evidence_version_key,@EvidenceBytes=content_bytes,@EvidenceDigest=content_sha256,
                @EvidenceDisplay=display_eligible,@EvidenceAi=visitor_ai_eligible,
                @EvidenceContent=policy_content_version,@EvidenceAccess=access_revision,@Codec=codec,@Token=canonical_token
                FROM dbo.resume_publication_evidence WITH (HOLDLOCK)
                WHERE owner_profile_id=@ProfileId AND entry_key=@EntryKey AND content_sha256=@Digest
                  AND policy_content_version=@ContentVersion AND access_revision=@Access AND visitor_ai_eligible=1
                ORDER BY evidence_id DESC;
            IF @EvidenceKey IS NULL OR @EvidenceBytes<>@Bytes OR @EvidenceDigest<>@Digest
                THROW 54201, ''AI source authority is unavailable.'', 1;
            SET @EvidenceVersion=TRY_CONVERT(int,RIGHT(@EvidenceKey,CHARINDEX(N'':'',REVERSE(@EvidenceKey))-1));
            IF @EvidenceVersion IS NULL OR @EvidenceVersion<1 THROW 54201, ''AI source authority is unavailable.'', 1;
        END;
        INSERT @Entries VALUES(@EntryKey,(SELECT @Subject owner_key,LOWER(CONVERT(nvarchar(36),@EntryKey)) entry_key,
            @CanonicalType canonical_type,@ContentVersion content_version,@Access access_revision,
            @Display resume_display,@Ai visitor_ai,N''active'' lifecycle,@CanonicalRevision canonical_revision,
            JSON_QUERY(CONCAT(N''["'',STRING_ESCAPE(@ParentVersion,''json''),N''"]'')) dependency_versions,
            CONVERT(varchar(max),@EvidenceBytes,2) content_hex,@EvidenceDigest content_sha256,@Digest current_content_sha256,
            @EvidenceKey evidence_version_key,@EvidenceVersion evidence_version,@Codec codec,@Token canonical_token,
            @EvidenceContent evidence_content_version,@EvidenceAccess evidence_access_revision,
            @EvidenceDisplay evidence_display,@EvidenceAi evidence_ai FOR JSON PATH,WITHOUT_ARRAY_WRAPPER,INCLUDE_NULL_VALUES));
        FETCH NEXT FROM entry_cursor INTO @EntryKey,@CanonicalType,@ContentVersion,@Access,@Display,@Ai,@CanonicalKey,@Parent;
    END;
    CLOSE entry_cursor; DEALLOCATE entry_cursor;
    DECLARE @PlacementJson nvarchar(max);
    SELECT @PlacementJson=(SELECT slot,source_kind,asset_id,asset_version,asset_digest,presentation_version,
        crop_x,crop_y,crop_width,crop_height,alt_text,decorative,caption
        FROM dbo.resume_media_placements WITH (UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId
        ORDER BY slot FOR JSON PATH,INCLUDE_NULL_VALUES);
    DECLARE @Refs table(slot nvarchar(40) PRIMARY KEY,kind nvarchar(40),asset nvarchar(120),version bigint,digest char(64),placement int);
    IF @OwnerPreview=1
        INSERT @Refs SELECT slot,source_kind,asset_id,asset_version,asset_digest,presentation_version
        FROM dbo.resume_media_placements WHERE owner_profile_id=@ProfileId;
    ELSE
    BEGIN
        IF EXISTS(SELECT [key] FROM OPENJSON(@Media) GROUP BY [key] HAVING COUNT(*)<>1)
            THROW 54201, ''AI source authority is unavailable.'', 1;
        IF EXISTS(SELECT 1 FROM OPENJSON(@Media) WHERE JSON_VALUE([value],''$.active'') IS NULL OR JSON_VALUE([value],''$.active'') NOT IN (''true'',''false'',''0'',''1''))
            THROW 54201, ''AI source authority is unavailable.'', 1;
        INSERT @Refs SELECT [key],JSON_VALUE([value],''$.source_kind''),JSON_VALUE([value],''$.source_key''),
            TRY_CONVERT(bigint,JSON_VALUE([value],''$.asset_version'')),JSON_VALUE([value],''$.content_sha256''),
            @Current FROM OPENJSON(@Media)
            WHERE JSON_VALUE([value],''$.active'') IN (''true'',''1'');
    END;
    IF EXISTS(SELECT 1 FROM @Refs WHERE slot NOT IN (''story_banner'',''experience_support'')
        OR kind IS NULL OR kind NOT IN (''owner_photo'',''generated_illustration'') OR asset IS NULL OR version IS NULL OR digest IS NULL OR placement IS NULL)
        THROW 54201, ''AI source authority is unavailable.'', 1;
    DECLARE @MediaRows table(slot nvarchar(40) PRIMARY KEY,payload nvarchar(max));
    DECLARE @Slot nvarchar(40),@Kind nvarchar(40),@Asset nvarchar(120),@Version bigint,@AssetDigest char(64),@Placement int;
    DECLARE media_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT slot,kind,asset,version,digest,placement FROM @Refs ORDER BY slot;
    OPEN media_cursor; FETCH NEXT FROM media_cursor INTO @Slot,@Kind,@Asset,@Version,@AssetDigest,@Placement;
    WHILE @@FETCH_STATUS=0
    BEGIN
        DECLARE @SourceRevision nvarchar(100)=NULL,@CatalogRevision nvarchar(100)=NULL,@ReadyJson nvarchar(max)=NULL;
        IF @Kind=N''generated_illustration''
        BEGIN
            SELECT @SourceRevision=CONVERT(nvarchar(100),asset_version),@CatalogRevision=CONVERT(nvarchar(100),asset_version),
                @ReadyJson=(SELECT asset_version,content_sha256,lifecycle,origin,width,height FOR JSON PATH,WITHOUT_ARRAY_WRAPPER)
                FROM dbo.resume_catalog_assets WITH (UPDLOCK,HOLDLOCK)
                WHERE asset_id=TRY_CONVERT(uniqueidentifier,@Asset) AND asset_version=@Version AND content_sha256=@AssetDigest AND lifecycle=N''active'';
        END
        ELSE
        BEGIN
            SELECT @SourceRevision=CONVERT(varchar(16),row_version,2),
                @ReadyJson=(SELECT CONVERT(varchar(16),row_version,2) version,state,scan_result,
                    CONVERT(varchar(64),derivative_sha256_digest,2) digest,pixel_width,pixel_height FOR JSON PATH,WITHOUT_ARRAY_WRAPPER)
                FROM dbo.capture_media_sources WITH (HOLDLOCK)
                WHERE owner_profile_id=@ProfileId AND source_key=TRY_CONVERT(uniqueidentifier,@Asset)
                  AND CONVERT(bigint,row_version)=@Version AND state IN (N''needs_review'',N''confirmed'') AND scan_result=N''clean''
                  AND LOWER(CONVERT(varchar(64),derivative_sha256_digest,2))=@AssetDigest AND deleted_at_utc IS NULL;
        END;
        IF @SourceRevision IS NULL OR @ReadyJson IS NULL THROW 54201, ''AI source authority is unavailable.'', 1;
        INSERT @MediaRows VALUES(@Slot,(SELECT @Slot slot,@Placement placement_version,@Kind source_kind,@Asset source_key,
            @SourceRevision source_revision,@Version asset_version,@CatalogRevision catalog_revision,@AssetDigest content_sha256,
            LOWER(CONVERT(char(64),HASHBYTES(''SHA2_256'',dbo.fn_ResumePublicationUtf8(@ReadyJson)),2)) readiness_sha256,
            CONVERT(bit,1) ready,CONVERT(bit,1) active FOR JSON PATH,WITHOUT_ARRAY_WRAPPER,INCLUDE_NULL_VALUES));
        FETCH NEXT FROM media_cursor INTO @Slot,@Kind,@Asset,@Version,@AssetDigest,@Placement;
    END;
    CLOSE media_cursor; DEALLOCATE media_cursor;
    DECLARE @EntriesJson nvarchar(max),@MediaJson nvarchar(max),@Snapshot nvarchar(max);
    SELECT @EntriesJson=N''[''+COALESCE(STRING_AGG(CONVERT(nvarchar(max),payload),N'','') WITHIN GROUP(ORDER BY entry_key),N'''')+N'']'' FROM @Entries;
    SELECT @MediaJson=N''[''+COALESCE(STRING_AGG(CONVERT(nvarchar(max),payload),N'','') WITHIN GROUP(ORDER BY slot),N'''')+N'']'' FROM @MediaRows;
    SELECT @Snapshot=(SELECT 1 schema_version,@Subject subject_key,CONCAT(N''resume:'',@Subject) resume_key,
        CASE WHEN @OwnerPreview=1 THEN N''owner_preview'' ELSE N''guest'' END mode,
        @ProfileVersion profile_revision,@Sharing sharing_enabled,@Epoch sharing_epoch,@Revision publication_revision,
        @Current current_revision,@Reviewed reviewed_digest,@Draft draft_revision,
        LOWER(CONVERT(char(64),HASHBYTES(''SHA2_256'',dbo.fn_ResumePublicationUtf8(@DraftJson)),2)) draft_digest,
        LOWER(CONVERT(char(64),HASHBYTES(''SHA2_256'',dbo.fn_ResumePublicationUtf8(@PlacementJson)),2)) placement_digest,
        JSON_QUERY(@EntriesJson) entries,JSON_QUERY(@MediaJson) media,JSON_QUERY(@Media) publication_media
        FOR JSON PATH,WITHOUT_ARRAY_WRAPPER,INCLUDE_NULL_VALUES);
    COMMIT TRANSACTION;
    SELECT @Snapshot snapshot_json;
    END TRY
    BEGIN CATCH
        IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetOwnerLivingResumeEditor
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52002, ''RESUME_EDITOR_NOT_FOUND'', 1;

            SELECT profile.profile_key, profile.profile_slug, profile.display_name
            FROM dbo.member_profiles AS profile
            WHERE profile.profile_id = @ProfileId;

            SELECT
                chapter.chapter_key AS record_key,
                experience.role_title,
                experience.employer_name,
                chapter.location_text,
                chapter.summary,
                chapter.start_date,
                chapter.end_date,
                chapter.date_precision,
                experience.employment_type,
                experience.current_role,
                chapter.row_version,
                CONVERT(bit, CASE WHEN
                    chapter.visibility = N''private''
                    AND chapter.approval_status = N''draft''
                    AND chapter.publication_status = N''unpublished''
                    AND entity.visibility = N''private''
                    AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    chapter.visibility <> N''private'' OR chapter.approval_status <> N''draft'' OR chapter.publication_status <> N''unpublished''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_chapters AS chapter
            JOIN dbo.career_experiences AS experience
              ON experience.chapter_id = chapter.chapter_id
             AND experience.owner_profile_id = chapter.owner_profile_id
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = chapter.entity_id
             AND entity.owner_profile_id = chapter.owner_profile_id
            WHERE chapter.owner_profile_id = @ProfileId
              AND chapter.chapter_type = N''experience''
              AND chapter.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.start_date, chapter.chapter_id;

            SELECT
                achievement.achievement_key AS record_key,
                chapter.chapter_key AS parent_key,
                COALESCE(achievement.approved_wording,achievement.original_member_wording) AS wording,
                achievement.metric_value,
                achievement.metric_label,
                achievement.row_version,
                CONVERT(bit, CASE WHEN
                    achievement.visibility = N''private'' AND achievement.approval_status = N''draft''
                    AND entity.visibility = N''private'' AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    achievement.visibility <> N''private'' OR achievement.approval_status <> N''draft''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_achievements AS achievement
            JOIN dbo.career_chapters AS chapter
              ON chapter.chapter_id = achievement.chapter_id
             AND chapter.owner_profile_id = achievement.owner_profile_id
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = achievement.entity_id
             AND entity.owner_profile_id = achievement.owner_profile_id
            WHERE achievement.owner_profile_id = @ProfileId
              AND achievement.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, achievement.display_order, achievement.achievement_id;

            SELECT
                skill.skill_key AS record_key,
                skill.skill_name AS name,
                skill.skill_summary AS summary,
                skill.row_version,
                CONVERT(bit, CASE WHEN
                    skill.visibility = N''private'' AND skill.approval_status = N''draft''
                    AND entity.visibility = N''private'' AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    skill.visibility <> N''private'' OR skill.approval_status <> N''draft''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_skills AS skill
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = skill.entity_id
             AND entity.owner_profile_id = skill.owner_profile_id
            WHERE skill.owner_profile_id = @ProfileId
              AND skill.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY skill.featured DESC, skill.display_order, skill.skill_name;

            SELECT
                chapter.chapter_key AS record_key,
                credential.credential_name AS name,
                credential.issuer_name AS issuer,
                credential.credential_identifier AS identifier,
                credential.issue_date,
                credential.expiration_date,
                credential.verification_url,
                credential.credential_completion_status AS completion_status,
                chapter.row_version,
                CONVERT(bit, CASE WHEN
                    chapter.visibility = N''private'' AND chapter.approval_status = N''draft''
                    AND chapter.publication_status = N''unpublished''
                    AND entity.visibility = N''private'' AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    chapter.visibility <> N''private'' OR chapter.approval_status <> N''draft'' OR chapter.publication_status <> N''unpublished''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_chapters AS chapter
            JOIN dbo.career_credentials AS credential
              ON credential.chapter_id = chapter.chapter_id
             AND credential.owner_profile_id = chapter.owner_profile_id
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = chapter.entity_id
             AND entity.owner_profile_id = chapter.owner_profile_id
            WHERE chapter.owner_profile_id = @ProfileId
              AND chapter.chapter_type = N''credential''
              AND chapter.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, credential.issue_date, chapter.chapter_id;
            SELECT
                chapter.chapter_key AS record_key,
                chapter.title,
                education.institution_name,
                education.degree_name,
                education.field_of_study,
                education.education_status,
                education.grade_text,
                chapter.location_text,
                chapter.summary,
                chapter.start_date,
                chapter.end_date,
                chapter.date_precision,
                chapter.row_version,
                CONVERT(bit, CASE WHEN
                    chapter.visibility = N''private''
                    AND chapter.approval_status = N''draft''
                    AND chapter.publication_status = N''unpublished''
                    AND entity.visibility = N''private''
                    AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    chapter.visibility <> N''private'' OR chapter.approval_status <> N''draft'' OR chapter.publication_status <> N''unpublished''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_chapters AS chapter
            JOIN dbo.career_education AS education
              ON education.chapter_id = chapter.chapter_id
             AND education.owner_profile_id = chapter.owner_profile_id
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = chapter.entity_id
             AND entity.owner_profile_id = chapter.owner_profile_id
            WHERE chapter.owner_profile_id = @ProfileId
              AND chapter.chapter_type = N''education''
              AND chapter.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.start_date, chapter.chapter_id;

        END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationRefreshProjectionInternal
    @ProfileId bigint,
    @Revision int,
    @Digest char(64),
    @Display nvarchar(max),
    @VisitorAi nvarchar(max),
    @Evidence nvarchar(max),
    @Media nvarchar(max),
    @ProfileIdentityJson nvarchar(max) = NULL,
    @ReplaceProfileIdentity bit = 0
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET @Display = ISNULL(@Display, N''{}'');
    SET @VisitorAi = ISNULL(@VisitorAi, N''{}'');
    SET @Evidence = ISNULL(@Evidence, N''{}'');
    SET @Media = ISNULL(@Media, N''{}'');
    IF @ReplaceProfileIdentity = 0
        SELECT @ProfileIdentityJson = prior.profile_identity_json
          FROM dbo.resume_sharing_state AS sharing WITH (UPDLOCK, HOLDLOCK)
          JOIN dbo.resume_publication_revisions AS prior WITH (UPDLOCK, HOLDLOCK)
            ON prior.owner_profile_id = sharing.owner_profile_id
           AND prior.publication_revision = sharing.current_revision
         WHERE sharing.owner_profile_id = @ProfileId;
    INSERT dbo.resume_publication_revisions
        (owner_profile_id, publication_revision, reviewed_digest, display_json, visitor_ai_json, evidence_json, media_json, profile_identity_json)
    VALUES (@ProfileId, @Revision, @Digest, @Display, @VisitorAi, @Evidence, @Media, @ProfileIdentityJson);
    UPDATE dbo.resume_sharing_state
       SET publication_revision = @Revision,
           current_revision = @Revision,
           updated_at_utc = SYSUTCDATETIME()
     WHERE owner_profile_id = @ProfileId;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_CommitResumePublicationCommandForOwner
    @UserKey nvarchar(300),
    @RequestId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    IF @@TRANCOUNT <> 0
        THROW 54020, ''Ambient transactions are not permitted.'', 1;
    BEGIN TRANSACTION;

    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey
       AND app_user.active = 1
       AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 54021, ''Owner is unavailable.'', 1;

    EXEC dbo.usp_ResumePublicationLockOwnerInternal @ProfileId = @ProfileId;

    DECLARE @Type nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
    IF @Type NOT IN (
            N''publish'', N''correct'', N''change_permissions'', N''delete'', N''restore'',
            N''sharing_off'', N''catalog_withdraw'', N''media_restrict'',
            N''create'', N''edit'', N''recategorize'', N''permanently_delete'', N''resolve_match'')
        THROW 54025, ''Unknown publication command.'', 1;

    DECLARE @Digest char(64) = LOWER(CONVERT(char(64), HASHBYTES(''SHA2_256'', dbo.fn_ResumePublicationUtf8(@CommandJson)), 2));
    DECLARE @Existing char(64), @ExistingOutcome nvarchar(40);
    SELECT @Existing = request_digest, @ExistingOutcome = outcome
      FROM dbo.resume_publication_receipts WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId AND request_id = @RequestId;
    IF @Existing IS NOT NULL
    BEGIN
        IF @Existing <> @Digest
            THROW 54022, ''That request already used a different payload.'', 1;
        SELECT committed = CONVERT(bit, 1), replayed = CONVERT(bit, 1), outcome = @ExistingOutcome,
               request_digest = @Existing, read_state = N''current'';
        COMMIT;
        RETURN;
    END;

    DECLARE @PublicationRevision int, @CurrentRevision int, @Sharing bit;
    SELECT @PublicationRevision = publication_revision,
           @CurrentRevision = current_revision, @Sharing = sharing_enabled
      FROM dbo.resume_sharing_state WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId;

    DECLARE @Expected int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_publication_revision''));
    IF @Expected IS NOT NULL AND @Expected <> @PublicationRevision
        THROW 54023, ''The publication changed.'', 1;

    DECLARE @NewRevision int = @PublicationRevision;
    DECLARE @Outcome nvarchar(40) = N''applied'';
    DECLARE @Display nvarchar(max), @Visitor nvarchar(max), @Evidence nvarchar(max), @Media nvarchar(max);

    IF @Type IN (N''create'', N''edit'', N''recategorize'', N''permanently_delete'', N''resolve_match'',
                 N''change_permissions'', N''delete'', N''restore'', N''correct'')
    BEGIN
        IF @Type IN (N''edit'', N''correct'', N''change_permissions'')
            EXEC dbo.usp_ResumePublicationApplyCanonicalInternal @ProfileId = @ProfileId, @CommandJson = @CommandJson;
        ELSE IF OBJECT_ID(N''dbo.usp_CommitEntryPolicyCommandForOwnerCore'', N''P'') IS NOT NULL
            EXEC dbo.usp_CommitEntryPolicyCommandForOwnerCore
                @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
        ELSE
            EXEC dbo.usp_ResumePublicationApplyCanonicalInternal @ProfileId = @ProfileId, @CommandJson = @CommandJson;
        IF @Type = N''restore''
        BEGIN
            SET @Outcome = N''restored_private'';
        END
        ELSE IF @CurrentRevision IS NOT NULL AND @Type <> N''create''
        BEGIN
            SET @NewRevision = @PublicationRevision + 1;
            EXEC dbo.usp_ResumePublicationBuildManifestsInternal
                @ProfileId = @ProfileId, @Revision = @NewRevision, @CommandJson = @CommandJson,
                @Display = @Display OUTPUT, @VisitorAi = @Visitor OUTPUT, @Evidence = @Evidence OUTPUT;
            SELECT @Media = media_json
              FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
             WHERE owner_profile_id = @ProfileId AND publication_revision = @CurrentRevision;
            EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
                @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Digest,
                @Display = @Display, @VisitorAi = @Visitor,
                @Evidence = @Evidence, @Media = @Media;
            SET @Outcome = CASE @Type WHEN N''correct'' THEN N''corrected'' WHEN N''edit'' THEN N''corrected''
                                      WHEN N''delete'' THEN N''deleted'' ELSE N''restricted'' END;
        END
        ELSE
            SET @Outcome = CASE @Type WHEN N''create'' THEN N''created'' ELSE N''applied'' END;
    END
    ELSE IF @Type = N''publish''
    BEGIN
        -- The reference is part of CommandJson and its idempotency digest.
        -- Hold the same owner''s current Profile publication through commit.
        IF (SELECT COUNT(*) FROM OPENJSON(@CommandJson) WHERE [key] COLLATE Latin1_General_100_BIN2 = N''profile_identity'') > 1
            OR EXISTS (SELECT 1 FROM OPENJSON(@CommandJson) WHERE [key] COLLATE Latin1_General_100_BIN2 = N''profile_identity'' AND [type] NOT IN (0,5))
            THROW 54301, ''Invalid Profile identity selection.'', 1;
        DECLARE @ProfileIdentityJson nvarchar(max) = JSON_QUERY(@CommandJson, ''$.profile_identity'');
        IF @ProfileIdentityJson IS NOT NULL
        BEGIN
            IF (SELECT COUNT(*) FROM OPENJSON(@ProfileIdentityJson)) <> 6
                OR (SELECT COUNT(DISTINCT [key] COLLATE Latin1_General_100_BIN2) FROM OPENJSON(@ProfileIdentityJson)) <> 6
                OR EXISTS (SELECT 1 FROM OPENJSON(@ProfileIdentityJson) WHERE
                    ([key] COLLATE Latin1_General_100_BIN2 IN (N''owner_key'',N''profile_slug'',N''revision_key'',N''publication_digest'') AND [type] <> 1)
                    OR ([key] COLLATE Latin1_General_100_BIN2 IN (N''schema_version'',N''revision_number'') AND [type] <> 2)
                    OR [key] COLLATE Latin1_General_100_BIN2 NOT IN (N''owner_key'',N''profile_slug'',N''revision_key'',N''publication_digest'',N''schema_version'',N''revision_number''))
                OR ISNULL(JSON_VALUE(@ProfileIdentityJson,''$.schema_version''), N'''') COLLATE Latin1_General_100_BIN2 <> N''1''
                OR ISNULL(JSON_VALUE(@ProfileIdentityJson,''$.owner_key''),N'''') COLLATE Latin1_General_100_BIN2 <> @UserKey COLLATE Latin1_General_100_BIN2
                THROW 54301, ''Invalid Profile identity selection.'', 1;
            IF NOT EXISTS (
                SELECT 1
                  FROM dbo.profile_publications AS publication WITH (UPDLOCK, HOLDLOCK)
                  JOIN dbo.profile_publication_revisions AS identity_revision WITH (UPDLOCK, HOLDLOCK)
                    ON identity_revision.profile_publication_revision_id = publication.current_revision_id
                   AND identity_revision.owner_profile_id = publication.owner_profile_id
                   AND identity_revision.audience COLLATE Latin1_General_100_BIN2 = N''public''
                  JOIN dbo.profile_slug_history AS slug WITH (UPDLOCK, HOLDLOCK)
                    ON slug.owner_profile_id = publication.owner_profile_id
                   AND slug.normalized_slug COLLATE Latin1_General_100_BIN2 = identity_revision.profile_slug COLLATE Latin1_General_100_BIN2
                   AND slug.active = 1
                 WHERE publication.owner_profile_id = @ProfileId
                   AND publication.audience COLLATE Latin1_General_100_BIN2 = N''public''
                   AND publication.publication_state = N''published''
                   AND identity_revision.revision_key COLLATE Latin1_General_100_BIN2 = JSON_VALUE(@ProfileIdentityJson,''$.revision_key'') COLLATE Latin1_General_100_BIN2
                   AND CONVERT(nvarchar(20),identity_revision.revision_number) COLLATE Latin1_General_100_BIN2 = JSON_VALUE(@ProfileIdentityJson,''$.revision_number'') COLLATE Latin1_General_100_BIN2
                   AND identity_revision.profile_slug COLLATE Latin1_General_100_BIN2 = JSON_VALUE(@ProfileIdentityJson,''$.profile_slug'') COLLATE Latin1_General_100_BIN2
                   AND JSON_VALUE(identity_revision.manifest_json,''$.digest'') COLLATE Latin1_General_100_BIN2 = JSON_VALUE(@ProfileIdentityJson,''$.publication_digest'') COLLATE Latin1_General_100_BIN2
                   AND JSON_VALUE(identity_revision.manifest_json,''$.owner_key'') COLLATE Latin1_General_100_BIN2 = @UserKey COLLATE Latin1_General_100_BIN2
                   AND JSON_VALUE(identity_revision.manifest_json,''$.action'') COLLATE Latin1_General_100_BIN2 = N''publish''
                   AND JSON_QUERY(identity_revision.manifest_json,''$.identity'') IS NOT NULL
            ) THROW 54302, ''Profile identity changed. Review it again.'', 1;
        END;

        -- Integrated G publish: the complete reviewed candidate is immutable input.
        -- Every dependency is fenced inside this existing owner transaction.
        DECLARE @GCandidate nvarchar(max) = JSON_QUERY(@CommandJson, ''$.candidate'');
        IF @GCandidate IS NULL OR LEFT(LTRIM(@GCandidate),1)<>N''{''
            OR (SELECT COUNT(*) FROM OPENJSON(@GCandidate))<>10
            OR (SELECT COUNT(DISTINCT [key] COLLATE Latin1_General_100_BIN2) FROM OPENJSON(@GCandidate))<>10
            OR EXISTS(SELECT 1 FROM OPENJSON(@GCandidate) WHERE
                ([key] COLLATE Latin1_General_100_BIN2 IN(N''schema_version'',N''draft_revision'',N''publication_revision'',N''sharing_epoch'') AND type<>2)
                OR ([key] COLLATE Latin1_General_100_BIN2 IN(N''reviewed_digest'',N''resume_key'') AND type<>1)
                OR ([key] COLLATE Latin1_General_100_BIN2 IN(N''entries'',N''placements'') AND type<>4)
                OR ([key] COLLATE Latin1_General_100_BIN2=N''profile_identity'' AND type NOT IN(0,5))
                OR ([key] COLLATE Latin1_General_100_BIN2=N''story_entry_key'' AND type NOT IN(0,1))
                OR [key] COLLATE Latin1_General_100_BIN2 NOT IN(N''schema_version'',N''draft_revision'',N''publication_revision'',N''sharing_epoch'',N''reviewed_digest'',N''resume_key'',N''entries'',N''placements'',N''profile_identity'',N''story_entry_key''))
            THROW 54303,''Invalid reviewed candidate shape.'',1;
        IF ISNULL(JSON_QUERY(@GCandidate,''$.profile_identity''),N''null'') COLLATE Latin1_General_100_BIN2
            <> ISNULL(@ProfileIdentityJson,N''null'') COLLATE Latin1_General_100_BIN2
            THROW 54303,''Profile identity must match the reviewed candidate.'',1;
        IF @GCandidate IS NULL OR ISNULL(JSON_VALUE(@GCandidate, ''$.schema_version''), N'''') <> N''1''
            OR ISNULL(JSON_VALUE(@GCandidate, ''$.reviewed_digest''), N'''') COLLATE Latin1_General_100_BIN2
                <> ISNULL(JSON_VALUE(@CommandJson, ''$.reviewed_digest''), N'''') COLLATE Latin1_General_100_BIN2
            OR ISNULL(JSON_VALUE(@GCandidate, ''$.publication_revision''), N'''') <> CONVERT(nvarchar(20), @PublicationRevision)
            THROW 54303, ''A complete current reviewed candidate is required.'', 1;
        DECLARE @GSharingEpoch int, @GDraftId bigint, @GDraftVersion int, @GStoryKey uniqueidentifier;
        SELECT @GSharingEpoch = sharing_epoch FROM dbo.resume_sharing_state WITH(UPDLOCK,HOLDLOCK)
          WHERE owner_profile_id=@ProfileId;
        SELECT @GDraftId=resume_draft_id, @GDraftVersion=draft_version, @GStoryKey=story_entry_key
          FROM dbo.resume_drafts WITH(UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId;
        DECLARE @GStoryInput nvarchar(max), @GStoryInputType int;
        SELECT @GStoryInput=[value], @GStoryInputType=[type]
          FROM OPENJSON(@GCandidate) WHERE [key] COLLATE Latin1_General_100_BIN2=N''story_entry_key'';
        IF (SELECT COUNT(*) FROM OPENJSON(@GCandidate) WHERE [key] COLLATE Latin1_General_100_BIN2=N''story_entry_key'' AND type IN(0,1))<>1
            OR @GStoryInputType IS NULL
            OR (@GStoryKey IS NULL AND @GStoryInputType<>0)
            OR (@GStoryKey IS NOT NULL AND (@GStoryInputType<>1 OR @GStoryInput IS NULL
                OR DATALENGTH(@GStoryInput)<>72
                OR TRY_CONVERT(uniqueidentifier,@GStoryInput) IS NULL
                OR TRY_CONVERT(uniqueidentifier,@GStoryInput)<>@GStoryKey))
            THROW 54304,''The selected personal entry changed.'',1;
        IF ISNULL(JSON_VALUE(@GCandidate, ''$.sharing_epoch''), N'''') <> CONVERT(nvarchar(20), @GSharingEpoch)
            OR ISNULL(JSON_VALUE(@GCandidate, ''$.draft_revision''), N'''') <> CONVERT(nvarchar(20), ISNULL(@GDraftVersion,0))
            THROW 54304, ''The Resume draft or sharing state changed.'', 1;
        IF JSON_QUERY(@GCandidate,''$.entries'') IS NULL OR LEFT(LTRIM(JSON_QUERY(@GCandidate,''$.entries'')),1) <> N''[''
            THROW 54303, ''Complete entry selections are required.'', 1;
        DECLARE @GEntries TABLE(entry_key uniqueidentifier PRIMARY KEY, content_version int NOT NULL,
            access_revision int NOT NULL, canonical_token nvarchar(128), resume_display bit NOT NULL,
            visitor_ai bit NOT NULL, deltas nvarchar(max) NOT NULL);
        IF EXISTS(SELECT 1 FROM OPENJSON(@GCandidate,''$.entries'') AS selected
            WHERE selected.type<>5 OR
            (SELECT COUNT(*) FROM OPENJSON(selected.value))<>7 OR
            (SELECT COUNT(DISTINCT [key] COLLATE Latin1_General_100_BIN2) FROM OPENJSON(selected.value))<>7 OR
            EXISTS(SELECT 1 FROM OPENJSON(selected.value) WHERE
                ([key] COLLATE Latin1_General_100_BIN2 IN(N''entry_key'',N''content_revision'',N''canonical_token'') AND type<>1)
                OR ([key] COLLATE Latin1_General_100_BIN2=N''access_revision'' AND (type<>2 OR TRY_CONVERT(int,value) IS NULL OR TRY_CONVERT(int,value)<1))
                OR ([key] COLLATE Latin1_General_100_BIN2 IN(N''resume_display'',N''visitor_ai'') AND type<>3)
                OR ([key] COLLATE Latin1_General_100_BIN2=N''deltas'' AND type<>4)
                OR [key] COLLATE Latin1_General_100_BIN2 NOT IN(N''entry_key'',N''content_revision'',N''access_revision'',N''canonical_token'',N''resume_display'',N''visitor_ai'',N''deltas'')))
            THROW 54303, ''Explicit permission choices are required.'', 1;
        INSERT @GEntries
          SELECT TRY_CONVERT(uniqueidentifier,entry_key),TRY_CONVERT(int,content_revision),access_revision,
            canonical_token,CASE resume_display WHEN N''true'' THEN 1 WHEN N''false'' THEN 0 END,
            CASE visitor_ai WHEN N''true'' THEN 1 WHEN N''false'' THEN 0 END,deltas
          FROM OPENJSON(@GCandidate,''$.entries'') WITH(entry_key nvarchar(100),content_revision nvarchar(100),
            access_revision int,canonical_token nvarchar(128),resume_display nvarchar(10),visitor_ai nvarchar(10),deltas nvarchar(max) AS JSON);
        IF EXISTS(SELECT 1 FROM @GEntries AS candidate LEFT JOIN dbo.entry_policy_records AS policy WITH(UPDLOCK,HOLDLOCK)
            ON policy.owner_profile_id=@ProfileId AND policy.entry_key=candidate.entry_key
            WHERE policy.entry_key IS NULL OR policy.lifecycle<>N''active''
                OR policy.content_version<>candidate.content_version OR policy.access_revision<>candidate.access_revision)
            OR EXISTS(SELECT 1 FROM dbo.entry_policy_records AS policy WITH(UPDLOCK,HOLDLOCK)
                WHERE policy.owner_profile_id=@ProfileId AND policy.lifecycle=N''active''
                AND NOT EXISTS(SELECT 1 FROM @GEntries WHERE entry_key=policy.entry_key))
            THROW 54304, ''Saved information or permissions changed.'', 1;
        DECLARE @GKey uniqueidentifier,@GCanonicalKey uniqueidentifier,@GType nvarchar(40),@GToken nvarchar(128),
            @GDeltas nvarchar(max),@GProposed nvarchar(max),@GStoredToken nvarchar(64),@GActualToken binary(8),
            @GField nvarchar(100),@GAfter nvarchar(max),@GAfterType int,@GDelta nvarchar(max);
        DECLARE g_entry_cursor CURSOR LOCAL FAST_FORWARD FOR
          SELECT candidate.entry_key,policy.canonical_key,policy.canonical_type,candidate.canonical_token,candidate.deltas
          FROM @GEntries AS candidate JOIN dbo.entry_policy_records AS policy WITH(UPDLOCK,HOLDLOCK)
            ON policy.owner_profile_id=@ProfileId AND policy.entry_key=candidate.entry_key ORDER BY candidate.entry_key;
        OPEN g_entry_cursor;
        FETCH NEXT FROM g_entry_cursor INTO @GKey,@GCanonicalKey,@GType,@GToken,@GDeltas;
        WHILE @@FETCH_STATUS=0
        BEGIN
            SELECT @GActualToken=NULL,@GProposed=NULL,@GStoredToken=NULL;
            IF @GType IN(N''role'',N''education'',N''credential'',N''project'')
                SELECT @GActualToken=row_version FROM dbo.career_chapters WITH(UPDLOCK,HOLDLOCK)
                    WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey AND deleted_at_utc IS NULL;
            ELSE IF @GType=N''skill''
                SELECT @GActualToken=row_version FROM dbo.career_skills WITH(UPDLOCK,HOLDLOCK)
                    WHERE owner_profile_id=@ProfileId AND skill_key=@GCanonicalKey AND deleted_at_utc IS NULL;
            ELSE IF @GType=N''achievement''
                SELECT @GActualToken=row_version FROM dbo.career_achievements WITH(UPDLOCK,HOLDLOCK)
                    WHERE owner_profile_id=@ProfileId AND achievement_key=@GCanonicalKey AND deleted_at_utc IS NULL;
            ELSE IF @GType=N''knowledge''
                SELECT @GActualToken=row_version FROM dbo.knowledge_items WITH(UPDLOCK,HOLDLOCK)
                    WHERE owner_profile_id=@ProfileId AND knowledge_item_key=@GCanonicalKey
                      AND item_status=N''confirmed'' AND classification=N''personal'' AND current_version_number=confirmed_version_number;
            IF @GToken IS NULL OR LEN(@GToken)<>16 OR @GToken COLLATE Latin1_General_100_BIN2 LIKE ''%[^0-9a-f]%''
                OR (@GActualToken IS NULL OR TRY_CONVERT(binary(8),@GToken,2) IS NULL
                OR TRY_CONVERT(binary(8),@GToken,2)<>@GActualToken)
                THROW 54304, ''Canonical information changed.'', 1;
            SELECT @GProposed=proposed_values_json,@GStoredToken=base_content_token
                FROM dbo.resume_draft_items WITH(UPDLOCK,HOLDLOCK)
                WHERE resume_draft_id=@GDraftId AND record_key=@GKey;
            IF EXISTS(SELECT 1 FROM OPENJSON(@GDeltas)) AND
                (@GProposed IS NULL OR @GToken IS NULL OR @GStoredToken COLLATE Latin1_General_100_BIN2<>@GToken COLLATE Latin1_General_100_BIN2)
                THROW 54304, ''Saved editorial changes are unavailable.'', 1;
            IF EXISTS(SELECT 1 FROM OPENJSON(@GDeltas) GROUP BY JSON_VALUE(value,''$.field'') HAVING COUNT(*)>1)
                THROW 54303, ''Duplicate editorial change.'', 1;
            IF EXISTS(SELECT 1 FROM OPENJSON(@GDeltas) AS delta WHERE delta.type<>5
                OR (SELECT COUNT(*) FROM OPENJSON(delta.value))<>3
                OR (SELECT COUNT(DISTINCT [key] COLLATE Latin1_General_100_BIN2) FROM OPENJSON(delta.value))<>3
                OR EXISTS(SELECT 1 FROM OPENJSON(delta.value) WHERE
                    ([key] COLLATE Latin1_General_100_BIN2=N''field'' AND type<>1)
                    OR ([key] COLLATE Latin1_General_100_BIN2 IN(N''before'',N''after'') AND type NOT IN(0,1,3))
                    OR [key] COLLATE Latin1_General_100_BIN2 NOT IN(N''field'',N''before'',N''after'')))
                THROW 54303,''Invalid editorial change shape.'',1;
            DECLARE g_delta_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT value FROM OPENJSON(@GDeltas);
            OPEN g_delta_cursor;
            FETCH NEXT FROM g_delta_cursor INTO @GDelta;
            WHILE @@FETCH_STATUS=0
            BEGIN
                SELECT @GField=JSON_VALUE(@GDelta,''$.field''),@GAfter=NULL,@GAfterType=NULL;
                SELECT @GAfter=value,@GAfterType=type FROM OPENJSON(@GDelta) WHERE [key] COLLATE Latin1_General_100_BIN2=N''after'';
                IF @GAfterType IS NULL OR @GAfterType NOT IN(0,1,3)
                    OR NOT EXISTS(SELECT 1 FROM OPENJSON(@GProposed) WHERE [key] COLLATE Latin1_General_100_BIN2=@GField COLLATE Latin1_General_100_BIN2
                        AND type=@GAfterType AND (type=0 OR CONVERT(varbinary(max),value)=CONVERT(varbinary(max),@GAfter)))
                    THROW 54303, ''Editorial changes must match the saved draft.'', 1;
                IF @GType=N''knowledge'' AND (@GAfterType<>1 OR @GField COLLATE Latin1_General_100_BIN2 NOT IN(N''title'',N''wording'',N''classification'')
                    OR (@GField=N''title'' AND (DATALENGTH(@GAfter)/2 NOT BETWEEN 1 AND 160 OR LEN(LTRIM(RTRIM(@GAfter)))=0))
                    OR (@GField=N''wording'' AND (DATALENGTH(@GAfter)/2 NOT BETWEEN 1 AND 8000 OR LEN(LTRIM(RTRIM(@GAfter)))=0))
                    OR (@GField=N''classification'' AND @GAfter COLLATE Latin1_General_100_BIN2<>N''personal''))
                    THROW 54303,''Invalid personal entry wording.'',1;
                -- Fixed type/field/column mapping follows; no dynamic SQL or client table names.
                IF NOT ((@GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2 IN(N''current_role'',N''date_precision'',N''employer_name'',N''employment_type'',N''end_date'',N''location_text'',N''role_title'',N''start_date'',N''summary'')) OR (@GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2 IN(N''date_precision'',N''degree_name'',N''education_status'',N''end_date'',N''field_of_study'',N''grade_text'',N''institution_name'',N''location_text'',N''start_date'',N''summary'',N''title'')) OR (@GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2 IN(N''completion_status'',N''expiration_date'',N''identifier'',N''issue_date'',N''issuer'',N''name'',N''verification_url'')) OR (@GType=N''skill'' AND @GField COLLATE Latin1_General_100_BIN2 IN(N''name'',N''summary'')) OR (@GType=N''achievement'' AND @GField COLLATE Latin1_General_100_BIN2 IN(N''metric_label'',N''metric_value'',N''wording'')) OR (@GType=N''knowledge'' AND @GField COLLATE Latin1_General_100_BIN2 IN(N''title'',N''wording'',N''classification''))) THROW 54303, ''Unsupported editorial field.'', 1;
                IF (@GField=N''current_role'' AND @GAfterType<>3) OR (@GField<>N''current_role'' AND @GAfterType=3) THROW 54303, ''Invalid editorial value type.'', 1;

                IF @GAfterType=1 AND DATALENGTH(@GAfter)/2 > CASE
                    WHEN @GField IN(N''summary'',N''wording'') THEN 8000
                    WHEN @GField=N''verification_url'' THEN 1000
                    WHEN @GField IN(N''grade_text'',N''metric_value'') THEN 100
                    WHEN @GField=N''name'' AND @GType=N''skill'' THEN 200
                    WHEN @GField=N''title'' AND @GType=N''knowledge'' THEN 160
                    ELSE 300 END THROW 54303,''Editorial value is too long.'',1;
                IF (@GType=N''role'' AND @GField IN(N''role_title'',N''employer_name'',N''date_precision''))
                    OR (@GType=N''education'' AND @GField IN(N''title'',N''institution_name'',N''education_status'',N''date_precision''))
                    OR (@GType=N''credential'' AND @GField IN(N''name'',N''issuer'',N''completion_status''))
                    OR (@GType=N''skill'' AND @GField=N''name'') OR (@GType=N''achievement'' AND @GField=N''wording'')
                BEGIN
                    IF @GAfter IS NULL OR LEN(LTRIM(RTRIM(@GAfter)))=0 THROW 54303,''Required editorial wording is absent.'',1;
                END;
                IF @GField IN(N''start_date'',N''end_date'',N''issue_date'',N''expiration_date'') AND @GAfterType<>0
                  AND (LEN(@GAfter)<>10 OR TRY_CONVERT(date,@GAfter,23) IS NULL
                    OR CONVERT(nvarchar(10),TRY_CONVERT(date,@GAfter,23),23) COLLATE Latin1_General_100_BIN2<>@GAfter COLLATE Latin1_General_100_BIN2)
                    THROW 54303,''Invalid editorial date.'',1;
                IF @GField=N''date_precision'' AND @GAfter COLLATE Latin1_General_100_BIN2 NOT IN(N''day'',N''month'',N''year'',N''unknown'')
                    AND NOT(@GType=N''education'' AND @GAfter COLLATE Latin1_General_100_BIN2=N''approximate'')
                    THROW 54303,''Invalid date precision.'',1;
                IF @GField=N''employment_type'' AND @GAfterType<>0 AND @GAfter COLLATE Latin1_General_100_BIN2 NOT IN
                    (N''full_time'',N''part_time'',N''contract'',N''freelance'',N''internship'',N''volunteer'',N''military'',N''other'')
                    THROW 54303,''Invalid employment type.'',1;
                IF @GField=N''education_status'' AND @GAfter COLLATE Latin1_General_100_BIN2 NOT IN
                    (N''planned'',N''admitted'',N''in_progress'',N''completed'',N''paused'',N''withdrawn'')
                    THROW 54303,''Invalid education status.'',1;
                IF @GField=N''completion_status'' AND @GAfter COLLATE Latin1_General_100_BIN2 NOT IN(N''planned'',N''in_progress'',N''completed'')
                    THROW 54303,''Invalid credential status.'',1;
                IF @GField=N''verification_url'' AND @GAfterType<>0 AND @GAfter NOT LIKE N''http://_%'' AND @GAfter NOT LIKE N''https://_%''
                    THROW 54303,''Invalid verification link.'',1;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''role_title'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET title=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''employer_name'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET organization_name=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''location_text'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET location_text=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''summary'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET summary=@GAfter, approved_wording=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''start_date'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET start_date=TRY_CONVERT(date,@GAfter,23) WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''end_date'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET end_date=TRY_CONVERT(date,@GAfter,23) WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''date_precision'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET date_precision=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''role_title'' BEGIN UPDATE dbo.career_experiences WITH(UPDLOCK,HOLDLOCK) SET role_title=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''employer_name'' BEGIN UPDATE dbo.career_experiences WITH(UPDLOCK,HOLDLOCK) SET employer_name=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''employment_type'' BEGIN UPDATE dbo.career_experiences WITH(UPDLOCK,HOLDLOCK) SET employment_type=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''role'' AND @GField COLLATE Latin1_General_100_BIN2=N''current_role'' BEGIN UPDATE dbo.career_experiences WITH(UPDLOCK,HOLDLOCK) SET current_role=CASE @GAfter WHEN N''true'' THEN CONVERT(bit,1) ELSE CONVERT(bit,0) END WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''title'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET title=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''institution_name'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET organization_name=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''location_text'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET location_text=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''summary'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET summary=@GAfter, approved_wording=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''start_date'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET start_date=TRY_CONVERT(date,@GAfter,23) WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''end_date'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET end_date=TRY_CONVERT(date,@GAfter,23) WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''date_precision'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET date_precision=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''institution_name'' BEGIN UPDATE dbo.career_education WITH(UPDLOCK,HOLDLOCK) SET institution_name=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''degree_name'' BEGIN UPDATE dbo.career_education WITH(UPDLOCK,HOLDLOCK) SET degree_name=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''field_of_study'' BEGIN UPDATE dbo.career_education WITH(UPDLOCK,HOLDLOCK) SET field_of_study=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''education_status'' BEGIN UPDATE dbo.career_education WITH(UPDLOCK,HOLDLOCK) SET education_status=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''education'' AND @GField COLLATE Latin1_General_100_BIN2=N''grade_text'' BEGIN UPDATE dbo.career_education WITH(UPDLOCK,HOLDLOCK) SET grade_text=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''name'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET title=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''issuer'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET organization_name=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''issue_date'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET start_date=TRY_CONVERT(date,@GAfter,23) WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''expiration_date'' BEGIN UPDATE dbo.career_chapters WITH(UPDLOCK,HOLDLOCK) SET end_date=TRY_CONVERT(date,@GAfter,23) WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''name'' BEGIN UPDATE dbo.career_credentials WITH(UPDLOCK,HOLDLOCK) SET credential_name=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''issuer'' BEGIN UPDATE dbo.career_credentials WITH(UPDLOCK,HOLDLOCK) SET issuer_name=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''identifier'' BEGIN UPDATE dbo.career_credentials WITH(UPDLOCK,HOLDLOCK) SET credential_identifier=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''issue_date'' BEGIN UPDATE dbo.career_credentials WITH(UPDLOCK,HOLDLOCK) SET issue_date=TRY_CONVERT(date,@GAfter,23) WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''expiration_date'' BEGIN UPDATE dbo.career_credentials WITH(UPDLOCK,HOLDLOCK) SET expiration_date=TRY_CONVERT(date,@GAfter,23) WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''verification_url'' BEGIN UPDATE dbo.career_credentials WITH(UPDLOCK,HOLDLOCK) SET verification_url=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''credential'' AND @GField COLLATE Latin1_General_100_BIN2=N''completion_status'' BEGIN UPDATE dbo.career_credentials WITH(UPDLOCK,HOLDLOCK) SET credential_completion_status=@GAfter WHERE owner_profile_id=@ProfileId AND chapter_id IN(SELECT chapter_id FROM dbo.career_chapters WHERE owner_profile_id=@ProfileId AND chapter_key=@GCanonicalKey); IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''skill'' AND @GField COLLATE Latin1_General_100_BIN2=N''name'' BEGIN UPDATE dbo.career_skills WITH(UPDLOCK,HOLDLOCK) SET skill_name=@GAfter WHERE owner_profile_id=@ProfileId AND skill_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''skill'' AND @GField COLLATE Latin1_General_100_BIN2=N''summary'' BEGIN UPDATE dbo.career_skills WITH(UPDLOCK,HOLDLOCK) SET skill_summary=@GAfter WHERE owner_profile_id=@ProfileId AND skill_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''achievement'' AND @GField COLLATE Latin1_General_100_BIN2=N''wording'' BEGIN UPDATE dbo.career_achievements WITH(UPDLOCK,HOLDLOCK) SET approved_wording=@GAfter WHERE owner_profile_id=@ProfileId AND achievement_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''achievement'' AND @GField COLLATE Latin1_General_100_BIN2=N''metric_value'' BEGIN UPDATE dbo.career_achievements WITH(UPDLOCK,HOLDLOCK) SET metric_value=@GAfter WHERE owner_profile_id=@ProfileId AND achievement_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;
                IF @GType=N''achievement'' AND @GField COLLATE Latin1_General_100_BIN2=N''metric_label'' BEGIN UPDATE dbo.career_achievements WITH(UPDLOCK,HOLDLOCK) SET metric_label=@GAfter WHERE owner_profile_id=@ProfileId AND achievement_key=@GCanonicalKey; IF @@ROWCOUNT<>1 THROW 54304, ''Canonical entry changed.'', 1; END;

                FETCH NEXT FROM g_delta_cursor INTO @GDelta;
            END;
            CLOSE g_delta_cursor;
            DEALLOCATE g_delta_cursor;
            IF @GType IN(N''role'',N''education'') AND EXISTS(SELECT 1 FROM dbo.career_chapters AS chapter
                LEFT JOIN dbo.career_experiences AS experience ON experience.owner_profile_id=chapter.owner_profile_id AND experience.chapter_id=chapter.chapter_id
                WHERE chapter.owner_profile_id=@ProfileId AND chapter.chapter_key=@GCanonicalKey
                  AND ((chapter.start_date IS NOT NULL AND chapter.end_date<chapter.start_date)
                    OR (@GType=N''role'' AND chapter.end_date IS NOT NULL AND (chapter.start_date IS NULL OR experience.current_role=1))))
                THROW 54303,''Editorial dates conflict.'',1;
            IF @GType=N''credential'' AND EXISTS(SELECT 1 FROM dbo.career_credentials AS credential
                JOIN dbo.career_chapters AS chapter ON chapter.owner_profile_id=credential.owner_profile_id AND chapter.chapter_id=credential.chapter_id
                WHERE chapter.owner_profile_id=@ProfileId AND chapter.chapter_key=@GCanonicalKey
                  AND ((credential.credential_completion_status=N''completed'' AND credential.issue_date IS NULL)
                    OR (credential.credential_completion_status IN(N''planned'',N''in_progress'') AND (credential.issue_date IS NOT NULL OR credential.expiration_date IS NOT NULL))
                    OR credential.expiration_date<credential.issue_date))
                THROW 54303,''Credential dates conflict.'',1;
            IF @GType=N''knowledge'' AND EXISTS(SELECT 1 FROM OPENJSON(@GDeltas))
            BEGIN
                DECLARE @GKnowledgeId bigint,@GKnowledgeVersion int,@GKnowledgeActor int,
                    @GKnowledgeTitle nvarchar(max),@GKnowledgeWording nvarchar(max),@GKnowledgeOriginal nvarchar(max);
                SELECT @GKnowledgeId=item.knowledge_item_id,@GKnowledgeVersion=item.current_version_number,
                    @GKnowledgeOriginal=version_record.original_member_wording,
                    @GKnowledgeTitle=version_record.title,@GKnowledgeWording=version_record.approved_wording
                  FROM dbo.knowledge_items AS item WITH(UPDLOCK,HOLDLOCK)
                  JOIN dbo.knowledge_item_versions AS version_record WITH(UPDLOCK,HOLDLOCK)
                    ON version_record.knowledge_item_id=item.knowledge_item_id AND version_record.owner_profile_id=item.owner_profile_id
                    AND version_record.version_number=item.current_version_number
                  WHERE item.owner_profile_id=@ProfileId AND item.knowledge_item_key=@GCanonicalKey;
                IF @GKnowledgeOriginal IS NULL THROW 54304,''Personal entry source changed.'',1;
                SELECT @GKnowledgeActor=user_id FROM dbo.member_profiles WHERE profile_id=@ProfileId AND active=1;
                SELECT @GKnowledgeTitle=changed.value FROM OPENJSON(@GDeltas) AS delta CROSS APPLY OPENJSON(delta.value) AS changed
                    WHERE JSON_VALUE(delta.value,''$.field'')=N''title'' AND changed.[key]=N''after'';
                SELECT @GKnowledgeWording=changed.value FROM OPENJSON(@GDeltas) AS delta CROSS APPLY OPENJSON(delta.value) AS changed
                    WHERE JSON_VALUE(delta.value,''$.field'')=N''wording'' AND changed.[key]=N''after'';
                INSERT dbo.knowledge_item_versions(knowledge_item_id,owner_profile_id,version_number,title,
                    approved_wording,original_member_wording,body_format,authored_via,saved_by_user_id)
                  VALUES(@GKnowledgeId,@ProfileId,@GKnowledgeVersion+1,@GKnowledgeTitle,@GKnowledgeWording,
                    @GKnowledgeOriginal,N''plain'',N''typed'',@GKnowledgeActor);
                UPDATE dbo.knowledge_items SET current_version_number=@GKnowledgeVersion+1,
                    confirmed_version_number=@GKnowledgeVersion+1,confirmed_by_user_id=@GKnowledgeActor,
                    confirmed_at_utc=SYSUTCDATETIME(),updated_at_utc=SYSUTCDATETIME()
                  WHERE owner_profile_id=@ProfileId AND knowledge_item_id=@GKnowledgeId AND row_version=@GActualToken;
                IF @@ROWCOUNT<>1 THROW 54304,''Personal entry changed.'',1;
            END;
            UPDATE policy SET content_version=policy.content_version+CASE WHEN EXISTS(SELECT 1 FROM OPENJSON(@GDeltas)) THEN 1 ELSE 0 END,
                access_revision=policy.access_revision+CASE WHEN policy.resume_display<>candidate.resume_display OR policy.visitor_ai<>candidate.visitor_ai THEN 1 ELSE 0 END,
                resume_display=candidate.resume_display,visitor_ai=candidate.visitor_ai
              FROM dbo.entry_policy_records AS policy JOIN @GEntries AS candidate ON candidate.entry_key=policy.entry_key
              WHERE policy.owner_profile_id=@ProfileId AND policy.entry_key=@GKey;
            FETCH NEXT FROM g_entry_cursor INTO @GKey,@GCanonicalKey,@GType,@GToken,@GDeltas;
        END;
        CLOSE g_entry_cursor;
        DEALLOCATE g_entry_cursor;
        DELETE item FROM dbo.resume_draft_items AS item JOIN @GEntries AS candidate ON candidate.entry_key=item.record_key
          WHERE item.resume_draft_id=@GDraftId;
        IF @GDraftId IS NULL
            INSERT dbo.resume_drafts(owner_profile_id,draft_version,base_publication_version) VALUES(@ProfileId,1,@PublicationRevision+1);
        ELSE
            UPDATE dbo.resume_drafts SET draft_version=draft_version+1,base_publication_version=@PublicationRevision+1
              WHERE resume_draft_id=@GDraftId;

        DECLARE @GMedia TABLE(slot nvarchar(40) PRIMARY KEY,source_kind nvarchar(40),asset_id nvarchar(120),
            asset_version bigint,asset_digest nvarchar(128),crop_x decimal(9,6),crop_y decimal(9,6),
            crop_width decimal(9,6),crop_height decimal(9,6),presentation_version int,
            alt_text nvarchar(300),decorative bit,provenance_label nvarchar(120),caption nvarchar(500));
        IF JSON_QUERY(@GCandidate,''$.placements'') IS NULL OR LEFT(LTRIM(JSON_QUERY(@GCandidate,''$.placements'')),1)<>N''[''
            THROW 54303,''Complete media selection is required.'',1;
        IF EXISTS(SELECT 1 FROM OPENJSON(@GCandidate,''$.placements'') AS placement WHERE placement.type<>5
            OR (SELECT COUNT(*) FROM OPENJSON(placement.value))<>11
            OR (SELECT COUNT(DISTINCT [key] COLLATE Latin1_General_100_BIN2) FROM OPENJSON(placement.value))<>11
            OR EXISTS(SELECT 1 FROM OPENJSON(placement.value) WHERE
                ([key] COLLATE Latin1_General_100_BIN2 IN(N''slot'',N''source_kind'',N''asset_id'',N''asset_version'',N''asset_digest'',N''alt_text'',N''provenance_label'') AND type<>1)
                OR ([key] COLLATE Latin1_General_100_BIN2=N''presentation_version'' AND type<>2)
                OR ([key] COLLATE Latin1_General_100_BIN2=N''crop'' AND type<>5)
                OR ([key] COLLATE Latin1_General_100_BIN2=N''decorative'' AND type<>3)
                OR ([key] COLLATE Latin1_General_100_BIN2=N''caption'' AND type NOT IN(0,1))
                OR [key] COLLATE Latin1_General_100_BIN2 NOT IN(N''slot'',N''source_kind'',N''asset_id'',N''asset_version'',N''asset_digest'',N''alt_text'',N''provenance_label'',N''presentation_version'',N''crop'',N''decorative'',N''caption'')
                OR (type=1 AND DATALENGTH(value)/2>CASE [key] WHEN N''caption'' THEN 500 WHEN N''alt_text'' THEN 300
                    WHEN N''asset_id'' THEN 120 WHEN N''provenance_label'' THEN 120 WHEN N''asset_digest'' THEN 64 WHEN N''asset_version'' THEN 19 ELSE 40 END))
            OR (SELECT COUNT(*) FROM OPENJSON(placement.value,''$.crop''))<>4
            OR (SELECT COUNT(DISTINCT [key] COLLATE Latin1_General_100_BIN2) FROM OPENJSON(placement.value,''$.crop''))<>4
            OR EXISTS(SELECT 1 FROM OPENJSON(placement.value,''$.crop'') WHERE type<>2 OR [key] COLLATE Latin1_General_100_BIN2 NOT IN(N''x'',N''y'',N''width'',N''height'')
                OR TRY_CONVERT(decimal(9,6),value) IS NULL OR TRY_CONVERT(decimal(38,14),value)<>TRY_CONVERT(decimal(9,6),value)))
            THROW 54303,''Invalid media selection shape.'',1;
        INSERT @GMedia SELECT slot,source_kind,asset_id,asset_version,asset_digest,crop_x,crop_y,crop_width,crop_height,
            presentation_version,alt_text,CASE decorative WHEN N''true'' THEN 1 WHEN N''false'' THEN 0 END,provenance_label,caption
          FROM OPENJSON(@GCandidate,''$.placements'') WITH(slot nvarchar(40),source_kind nvarchar(40),asset_id nvarchar(120),
            asset_version bigint,asset_digest nvarchar(128),crop_x decimal(9,6) ''$.crop.x'',crop_y decimal(9,6) ''$.crop.y'',
            crop_width decimal(9,6) ''$.crop.width'',crop_height decimal(9,6) ''$.crop.height'',presentation_version int,
            alt_text nvarchar(300),decorative nvarchar(10),provenance_label nvarchar(120),caption nvarchar(500));
        IF EXISTS(SELECT * FROM @GMedia EXCEPT
            SELECT slot,source_kind,asset_id,asset_version,asset_digest,crop_x,crop_y,crop_width,crop_height,
                presentation_version,ISNULL(alt_text,N''''),decorative,provenance_label,caption
            FROM dbo.resume_media_placements WITH(UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId)
            OR EXISTS(SELECT slot,source_kind,asset_id,asset_version,asset_digest,crop_x,crop_y,crop_width,crop_height,
                presentation_version,ISNULL(alt_text,N''''),decorative,provenance_label,caption
            FROM dbo.resume_media_placements WITH(UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId EXCEPT SELECT * FROM @GMedia)
            THROW 54304,''The selected media changed.'',1;
        IF EXISTS(SELECT 1 FROM @GMedia AS candidate WHERE candidate.source_kind=N''owner_photo'' AND NOT EXISTS(
            SELECT 1 FROM dbo.capture_media_sources AS source WITH(UPDLOCK,HOLDLOCK)
            WHERE source.owner_profile_id=@ProfileId AND source.source_type=N''photo''
                AND source.source_key=TRY_CONVERT(uniqueidentifier,candidate.asset_id)
                AND CONVERT(bigint,source.row_version)=candidate.asset_version
                AND source.state IN(N''needs_review'',N''confirmed'') AND source.scan_result=N''clean''
                AND LOWER(CONVERT(varchar(64),source.derivative_sha256_digest,2)) COLLATE Latin1_General_100_BIN2
                    =candidate.asset_digest COLLATE Latin1_General_100_BIN2))
            OR EXISTS(SELECT 1 FROM @GMedia AS candidate WHERE candidate.source_kind=N''generated_illustration'' AND NOT EXISTS(
                SELECT 1 FROM dbo.resume_catalog_assets AS asset WITH(UPDLOCK,HOLDLOCK)
                WHERE asset.asset_id=TRY_CONVERT(uniqueidentifier,candidate.asset_id)
                    AND asset.asset_version=candidate.asset_version AND asset.lifecycle=N''active''
                    AND asset.content_sha256 COLLATE Latin1_General_100_BIN2=candidate.asset_digest COLLATE Latin1_General_100_BIN2))
            THROW 54304,''Selected media is no longer available.'',1;
        SET @Media=N''{}'';
        DECLARE @GSlot nvarchar(40),@GMediaJson nvarchar(max);
        DECLARE g_media_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT slot FROM @GMedia ORDER BY slot;
        OPEN g_media_cursor;
        FETCH NEXT FROM g_media_cursor INTO @GSlot;
        WHILE @@FETCH_STATUS=0
        BEGIN
            SET @GMediaJson=(SELECT slot,source_kind,asset_id AS source_key,asset_version,asset_digest AS content_sha256,
                CONVERT(bit,1) AS active,presentation_version,alt_text,decorative,provenance_label,caption,
                JSON_QUERY((SELECT crop_x AS x,crop_y AS y,crop_width AS width,crop_height AS height FOR JSON PATH,WITHOUT_ARRAY_WRAPPER)) AS crop
                FROM @GMedia WHERE slot=@GSlot FOR JSON PATH,WITHOUT_ARRAY_WRAPPER,INCLUDE_NULL_VALUES);
            SET @Media=JSON_MODIFY(@Media,CONCAT(N''$."'',@GSlot,N''"''),JSON_QUERY(@GMediaJson));
            FETCH NEXT FROM g_media_cursor INTO @GSlot;
        END;
        CLOSE g_media_cursor;
        DEALLOCATE g_media_cursor;
        DECLARE @GManifestCommand nvarchar(max)=(SELECT @GStoryKey AS story_entry_key FOR JSON PATH,INCLUDE_NULL_VALUES,WITHOUT_ARRAY_WRAPPER);
        DECLARE @Reviewed char(64) = JSON_VALUE(@CommandJson, ''$.reviewed_digest'');
        IF @Reviewed IS NULL OR LEN(@Reviewed) <> 64
            THROW 54024, ''Reviewed digest is required.'', 1;
        SET @NewRevision = @PublicationRevision + 1;
        SET @Outcome = N''published'';
        UPDATE dbo.resume_sharing_state
           SET sharing_enabled = 1, sharing_epoch = sharing_epoch + 1,
               public_slug = JSON_VALUE(@CommandJson, ''$.slug''),
               updated_at_utc = SYSUTCDATETIME()
         WHERE owner_profile_id = @ProfileId;
        EXEC dbo.usp_ResumePublicationBuildManifestsInternal
            @ProfileId = @ProfileId, @Revision = @NewRevision, @CommandJson = @GManifestCommand,
            @Display = @Display OUTPUT, @VisitorAi = @Visitor OUTPUT, @Evidence = @Evidence OUTPUT;
        EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
            @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Reviewed,
            @Display = @Display, @VisitorAi = @Visitor,
            @Evidence = @Evidence, @Media = @Media,
            @ProfileIdentityJson = @ProfileIdentityJson, @ReplaceProfileIdentity = 1;
    END
    ELSE IF @Type = N''sharing_off''
    BEGIN
        SET @Outcome = N''restricted'';
        UPDATE dbo.resume_sharing_state
           SET sharing_enabled = 0, sharing_epoch = sharing_epoch + 1, updated_at_utc = SYSUTCDATETIME()
         WHERE owner_profile_id = @ProfileId;
    END
    ELSE IF @Type = N''catalog_withdraw''
    BEGIN
        SET @Outcome = N''withdrawn'';
        DECLARE @WithdrawAssetId uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.asset_id''));
        DECLARE @WithdrawAssetVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.version''));
        EXEC dbo.usp_ResumeCatalogApplyInternal
            @AssetId = @WithdrawAssetId,
            @AssetVersion = @WithdrawAssetVersion,
            @Lifecycle = N''withdrawn'';
        SET @NewRevision = @PublicationRevision + 1;
        SELECT @Display = display_json, @Visitor = visitor_ai_json, @Evidence = evidence_json, @Media = media_json
          FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
         WHERE owner_profile_id = @ProfileId AND publication_revision = @CurrentRevision;
        EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
            @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Digest,
            @Display = @Display, @VisitorAi = @Visitor,
            @Evidence = @Evidence, @Media = @Media;
    END
    ELSE IF @Type = N''media_restrict''
    BEGIN
        SET @Outcome = N''restricted'';
        SET @NewRevision = @PublicationRevision + 1;
        SELECT @Display = display_json, @Visitor = visitor_ai_json, @Evidence = evidence_json, @Media = media_json
          FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
         WHERE owner_profile_id = @ProfileId AND publication_revision = @CurrentRevision;
        DECLARE @Slot nvarchar(40) = JSON_VALUE(@CommandJson, ''$.slot'');
        IF @Media IS NOT NULL AND @Slot IS NOT NULL
            SET @Media = JSON_MODIFY(@Media, CONCAT(N''$."'', @Slot, N''".active''), CONVERT(bit, 0));
        EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
            @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Digest,
            @Display = @Display, @VisitorAi = @Visitor,
            @Evidence = @Evidence, @Media = @Media;
    END;

    INSERT dbo.resume_publication_receipts (owner_profile_id, request_id, request_digest, command_type, outcome)
    VALUES (@ProfileId, @RequestId, @Digest, @Type, @Outcome);
    INSERT dbo.resume_publication_outbox (owner_profile_id, publication_revision, event_type, payload_json)
    VALUES (@ProfileId, @NewRevision, @Type, @CommandJson);

    SELECT committed = CONVERT(bit, 1), replayed = CONVERT(bit, 0), outcome = @Outcome,
           request_digest = @Digest, read_state = N''current'', publication_revision = @NewRevision;
    COMMIT;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetResumePublicationForOwner
    @UserKey nvarchar(300)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    SELECT s.sharing_enabled, s.sharing_epoch, s.publication_revision, s.current_revision, s.public_slug,
           r.media_json, r.reviewed_digest, r.profile_identity_json
      FROM dbo.resume_sharing_state AS s
      LEFT JOIN dbo.resume_publication_revisions AS r
        ON r.owner_profile_id = s.owner_profile_id
       AND r.publication_revision = s.current_revision
     WHERE s.owner_profile_id = @ProfileId;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetPublicResumePublicationBySlug
    @ProfileSlug nvarchar(100)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint, @Revision int, @Sharing bit;
    SELECT @ProfileId = owner_profile_id, @Revision = current_revision, @Sharing = sharing_enabled
      FROM dbo.resume_sharing_state
     WHERE public_slug = @ProfileSlug;
    IF @ProfileId IS NULL OR @Sharing = 0 OR @Revision IS NULL
        THROW 54030, ''Publication is unavailable.'', 1;
    IF EXISTS(SELECT 1 FROM dbo.resume_publication_revisions AS revision
        CROSS APPLY OPENJSON(revision.display_json) AS displayed
        LEFT JOIN dbo.knowledge_items AS personal ON personal.owner_profile_id=revision.owner_profile_id
          AND personal.knowledge_item_key=TRY_CONVERT(uniqueidentifier,displayed.[key])
          AND personal.item_status=N''confirmed'' AND personal.classification=N''personal''
          AND personal.current_version_number=personal.confirmed_version_number
        WHERE revision.owner_profile_id=@ProfileId AND revision.publication_revision=@Revision
          AND JSON_VALUE(displayed.value,''$.canonical_type'')=N''knowledge''
          AND (personal.knowledge_item_id IS NULL
            OR JSON_VALUE(displayed.value,''$.canonical_revision'') IS NULL
            OR DATALENGTH(JSON_VALUE(displayed.value,''$.canonical_revision''))<>32
            OR JSON_VALUE(displayed.value,''$.canonical_revision'') COLLATE Latin1_General_100_BIN2 LIKE N''%[^0-9A-Fa-f]%''
            OR TRY_CONVERT(binary(8),JSON_VALUE(displayed.value,''$.canonical_revision''),2) IS NULL
            OR TRY_CONVERT(binary(8),JSON_VALUE(displayed.value,''$.canonical_revision''),2)<>personal.row_version))
        THROW 54030,''Publication is unavailable.'',1;
    SELECT r.publication_revision, r.reviewed_digest, r.display_json, r.media_json, r.profile_identity_json, app_user.user_key AS owner_user_key
      FROM dbo.resume_publication_revisions AS r
      JOIN dbo.member_profiles AS profile ON profile.profile_id = r.owner_profile_id AND profile.active = 1
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id AND app_user.active = 1
     WHERE r.owner_profile_id = @ProfileId AND r.publication_revision = @Revision;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetCurrentProfilePublicationForOwner
    @OwnerKey nvarchar(300), @Audience nvarchar(20)
  AS
  BEGIN
    SET NOCOUNT ON;
    SELECT revision.manifest_json
    FROM dbo.app_users AS app_user
    JOIN dbo.member_profiles AS profile ON profile.user_id=app_user.id AND profile.active=1
    JOIN dbo.profile_publications AS publication ON publication.owner_profile_id=profile.profile_id AND publication.audience=@Audience AND publication.publication_state IN(N''published'',N''withdrawn'')
    JOIN dbo.profile_publication_revisions AS revision ON revision.profile_publication_revision_id=publication.current_revision_id AND revision.owner_profile_id=profile.profile_id AND revision.audience=@Audience
    WHERE app_user.user_key=@OwnerKey AND app_user.active=1;
  END';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetResumePublicationMediaAuthorization
    @ProfileSlug nvarchar(100),
    @Slot nvarchar(40),
    @PublicationRevision int = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint, @Revision int, @Sharing bit, @Media nvarchar(max), @OwnerUserKey nvarchar(300);
    SELECT @ProfileId = sharing.owner_profile_id, @Revision = sharing.current_revision,
           @Sharing = sharing.sharing_enabled, @OwnerUserKey = account.user_key
      FROM dbo.resume_sharing_state AS sharing
      JOIN dbo.member_profiles AS profile ON profile.profile_id=sharing.owner_profile_id AND profile.active=1
      JOIN dbo.app_users AS account ON account.id=profile.user_id AND account.active=1
     WHERE sharing.public_slug=@ProfileSlug;
    IF @ProfileId IS NULL OR @Sharing = 0 OR @Revision IS NULL
        THROW 54031, ''Media is unavailable.'', 1;
    IF @PublicationRevision IS NOT NULL AND @PublicationRevision <> @Revision
        THROW 54032, ''Media is unavailable.'', 1;
    SELECT @Media = media_json
      FROM dbo.resume_publication_revisions
     WHERE owner_profile_id = @ProfileId AND publication_revision = @Revision;
    DECLARE @Active bit = TRY_CONVERT(bit, JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".active'')));
    DECLARE @Kind nvarchar(40) = JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".source_kind''));
    DECLARE @SourceKey nvarchar(80) = JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".source_key''));
    DECLARE @AssetVersion bigint = TRY_CONVERT(bigint, JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".asset_version'')));
    DECLARE @Digest char(64) = JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".content_sha256''));
    IF @Media IS NULL OR @Active IS NULL OR @Active <> 1
        THROW 54033, ''Media is unavailable.'', 1;
    IF @Kind = N''generated_illustration''
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM dbo.resume_catalog_assets
             WHERE CONVERT(nvarchar(36), asset_id) = @SourceKey
               AND asset_version = @AssetVersion
               AND lifecycle = N''active''
               AND content_sha256 = @Digest)
            THROW 54034, ''Media is unavailable.'', 1;
    END;
    IF @Kind=N''owner_photo''
    BEGIN
        IF NOT EXISTS(SELECT 1 FROM dbo.capture_media_sources AS source
            JOIN dbo.member_profiles AS profile ON profile.profile_id=source.owner_profile_id AND profile.active=1
            JOIN dbo.app_users AS account ON account.id=profile.user_id AND account.active=1
            WHERE source.owner_profile_id=@ProfileId AND source.source_type=N''photo''
                AND source.source_key=TRY_CONVERT(uniqueidentifier,@SourceKey)
                AND CONVERT(bigint,source.row_version)=@AssetVersion
                AND source.state IN(N''needs_review'',N''confirmed'') AND source.scan_result=N''clean''
                AND LOWER(CONVERT(varchar(64),source.derivative_sha256_digest,2)) COLLATE Latin1_General_100_BIN2=@Digest COLLATE Latin1_General_100_BIN2)
            THROW 54034,''Media is unavailable.'',1;
    END
    ELSE IF @Kind<>N''generated_illustration'' OR @Kind IS NULL
        THROW 54034,''Media is unavailable.'',1;
    SELECT authorized = CONVERT(bit, 1), slot = @Slot, rechecked = CONVERT(bit, 1),
           content_sha256 = @Digest, source_kind = @Kind, source_key = @SourceKey,
           asset_version = @AssetVersion, publication_revision = @Revision, owner_user_key = @OwnerUserKey;
END;';

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-IDENTITY-001')
    BEGIN
        INSERT dbo.schema_migrations(migration_id,description,application_version)
        VALUES(N'PS-RESUME-IDENTITY-001',N'Integrated reviewed Resume publication and pinned Profile identity',N'PeerSlate MVP1 Package G');
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.applied', @EntityType=N'database_migration',
            @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-RESUME-IDENTITY-001"}';
    END;
    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;
