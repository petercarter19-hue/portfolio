/*
PS-RESUME-EDIT-001 — proposed private Living Resume editor commands.

PROPOSED ONLY. This file has not been applied to any database. Its registry
gate is null. Disposable SQL Server execution, concurrency, rollback, and
driver serialization proof remain required before any separately authorized
schema application.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-007')
        THROW 52000, 'PS-PLAT-007 must be applied first.', 1;

    IF COL_LENGTH(N'dbo.career_credentials', N'credential_completion_status') IS NULL
    BEGIN
        ALTER TABLE dbo.career_credentials
            ADD credential_completion_status nvarchar(30) NULL;
        ALTER TABLE dbo.career_credentials
            ADD CONSTRAINT CK_career_credentials_completion_status CHECK
                (credential_completion_status IS NULL OR credential_completion_status IN
                    (N'planned', N'in_progress', N'completed'));
    END;

    IF OBJECT_ID(N'dbo.living_resume_command_receipts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.living_resume_command_receipts
        (
            command_receipt_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            command_id uniqueidentifier NOT NULL,
            request_digest char(64) NOT NULL,
            command_type nvarchar(40) NOT NULL,
            record_type nvarchar(30) NOT NULL,
            record_key uniqueidentifier NOT NULL,
            outcome nvarchar(20) NOT NULL,
            result_version binary(8) NULL,
            committed_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_living_resume_command_receipts_committed DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_living_resume_command_receipts PRIMARY KEY (command_receipt_id),
            CONSTRAINT UQ_living_resume_command_receipts_owner_command
                UNIQUE (owner_profile_id, command_id),
            CONSTRAINT FK_living_resume_command_receipts_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_living_resume_command_receipts_digest
                CHECK (request_digest NOT LIKE '%[^0-9a-f]%' AND LEN(request_digest) = 64),
            CONSTRAINT CK_living_resume_command_receipts_type CHECK
                (command_type IN
                    (N'create_role', N'update_role', N'remove_role',
                     N'create_accomplishment', N'update_accomplishment', N'remove_accomplishment',
                     N'create_skill', N'update_skill', N'remove_skill',
                     N'create_credential', N'update_credential', N'remove_credential')),
            CONSTRAINT CK_living_resume_command_receipts_record_type CHECK
                (record_type IN (N'role', N'accomplishment', N'skill', N'credential')),
            CONSTRAINT CK_living_resume_command_receipts_outcome CHECK
                (outcome IN (N'created', N'updated', N'removed')),
            CONSTRAINT CK_living_resume_command_receipts_result CHECK
                ((outcome = N'removed' AND result_version IS NULL)
                 OR (outcome IN (N'created', N'updated') AND result_version IS NOT NULL))
        );
    END;

    EXEC(N'
        CREATE OR ALTER TRIGGER dbo.trg_living_resume_command_receipts_immutable
        ON dbo.living_resume_command_receipts
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            THROW 52001, ''Living Resume command receipts are immutable.'', 1;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetOwnerLivingResumeEditor
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
                achievement.original_member_wording AS wording,
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
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CommitLivingResumeCommandForOwner
            @UserKey nvarchar(300),
            @CommandId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            DECLARE @ProfileId bigint, @ActorUserId int;
            DECLARE @Type nvarchar(40), @Operation nvarchar(20), @RecordType nvarchar(30);
            DECLARE @RecordKey uniqueidentifier, @ParentKey uniqueidentifier;
            DECLARE @ExpectedVersionText varchar(16), @ExpectedVersion binary(8);
            DECLARE @Digest char(64), @Outcome nvarchar(20), @ResultVersion binary(8);
            DECLARE @EntityId bigint, @ChapterId bigint, @RecordId bigint;
            DECLARE @ExistingDigest char(64), @ExistingType nvarchar(40), @ExistingRecordKey uniqueidentifier;
            DECLARE @ExistingOutcome nvarchar(20), @ExistingVersion binary(8);

            IF ISJSON(@CommandJson) <> 1
                THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
            IF EXISTS
            (
                SELECT 1 FROM OPENJSON(@CommandJson)
                WHERE [key] NOT IN
                    (N''command_id'', N''type'', N''record_key'', N''parent_key'', N''expected_version'', N''values'')
            )
                THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;

            SET @Type = JSON_VALUE(@CommandJson, ''$.type'');
            SET @RecordKey = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.record_key''));
            SET @ParentKey = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.parent_key''));
            SET @ExpectedVersionText = JSON_VALUE(@CommandJson, ''$.expected_version'');
            SET @Digest = LOWER(CONVERT(varchar(64), HASHBYTES(''SHA2_256'', CONVERT(varbinary(max), @CommandJson)), 2));

            IF TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.command_id'')) IS NULL
               OR TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.command_id'')) <> @CommandId
               OR @RecordKey IS NULL
               OR @Type NOT IN
                    (N''create_role'', N''update_role'', N''remove_role'',
                     N''create_accomplishment'', N''update_accomplishment'', N''remove_accomplishment'',
                     N''create_skill'', N''update_skill'', N''remove_skill'',
                     N''create_credential'', N''update_credential'', N''remove_credential'')
                THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;

            SET @Operation = LEFT(@Type, CHARINDEX(N''_'', @Type) - 1);
            SET @RecordType = SUBSTRING(@Type, CHARINDEX(N''_'', @Type) + 1, 30);
            IF @Operation = N''create'' AND @ExpectedVersionText IS NOT NULL
                THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
            IF @Operation <> N''create''
            BEGIN
                IF @ExpectedVersionText IS NULL OR LEN(@ExpectedVersionText) <> 16
                   OR @ExpectedVersionText LIKE ''%[^0-9A-Fa-f]%''
                    THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                SET @ExpectedVersion = CONVERT(binary(8), @ExpectedVersionText, 2);
            END;
            IF (@Type = N''create_accomplishment'' AND @ParentKey IS NULL)
               OR (@Type <> N''create_accomplishment'' AND @ParentKey IS NOT NULL)
                THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
            IF @Operation = N''remove'' AND
               (JSON_QUERY(@CommandJson, ''$.values'') IS NULL OR JSON_QUERY(@CommandJson, ''$.values'') <> N''{}'')
                THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;

            SELECT @ProfileId = profile.profile_id, @ActorUserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;
            IF @ProfileId IS NULL
                THROW 52002, ''RESUME_EDITOR_NOT_FOUND'', 1;

            BEGIN TRY
            BEGIN TRANSACTION;

            SELECT
                @ExistingDigest = receipt.request_digest,
                @ExistingType = receipt.command_type,
                @ExistingRecordKey = receipt.record_key,
                @ExistingOutcome = receipt.outcome,
                @ExistingVersion = receipt.result_version
            FROM dbo.living_resume_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId
              AND receipt.command_id = @CommandId;

            IF @ExistingDigest IS NOT NULL
            BEGIN
                IF @ExistingDigest <> @Digest
                    THROW 52004, ''RESUME_EDITOR_IDEMPOTENCY_CONFLICT'', 1;
                COMMIT TRANSACTION;
                SELECT CONVERT(bit, 1) AS committed, CAST(NULL AS nvarchar(40)) AS error_code,
                       @CommandId AS command_id, @ExistingDigest AS request_digest,
                       @ExistingType AS command_type, @ExistingRecordKey AS record_key,
                       @ExistingOutcome AS outcome, @ExistingVersion AS record_version,
                       CONVERT(bit, 1) AS replayed;
                RETURN;
            END;

            IF @Operation <> N''remove''
            BEGIN
                DECLARE @AllowedValues TABLE (field_name nvarchar(100) PRIMARY KEY);
                IF @RecordType = N''role'' INSERT @AllowedValues VALUES
                    (N''role_title''),(N''employer_name''),(N''location_text''),(N''summary''),(N''start_date''),(N''end_date''),(N''date_precision''),(N''employment_type''),(N''current_role'');
                IF @RecordType = N''accomplishment'' INSERT @AllowedValues VALUES
                    (N''wording''),(N''metric_value''),(N''metric_label'');
                IF @RecordType = N''skill'' INSERT @AllowedValues VALUES
                    (N''name''),(N''summary'');
                IF @RecordType = N''credential'' INSERT @AllowedValues VALUES
                    (N''name''),(N''issuer''),(N''identifier''),(N''issue_date''),(N''expiration_date''),(N''verification_url''),(N''completion_status'');
                IF JSON_QUERY(@CommandJson, ''$.values'') IS NULL
                   OR EXISTS
                      (SELECT 1 FROM OPENJSON(@CommandJson, ''$.values'') AS supplied
                       WHERE NOT EXISTS (SELECT 1 FROM @AllowedValues AS allowed WHERE allowed.field_name = supplied.[key]))
                    THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
            END;

            IF @Operation = N''create''
            BEGIN
                IF EXISTS (SELECT 1 FROM dbo.slate_entities WHERE entity_key = @RecordKey)
                    THROW 52004, ''RESUME_EDITOR_IDEMPOTENCY_CONFLICT'', 1;

                INSERT dbo.slate_entities
                    (entity_key, owner_profile_id, entity_type, source_schema, source_table,
                     source_record_id, visibility, approval_status, publication_status, active)
                VALUES
                    (@RecordKey, @ProfileId, N''career_'' + @RecordType, NULL, NULL,
                     NULL, N''private'', N''draft'', N''unpublished'', 1);
                SET @EntityId = SCOPE_IDENTITY();

                IF @RecordType = N''role''
                BEGIN
                    DECLARE @RoleSummary nvarchar(max);
                    SELECT @RoleSummary = NULLIF(LTRIM(RTRIM(parsed.summary)), N'''')
                    FROM OPENJSON(@CommandJson, N''$.values'')
                    WITH (summary nvarchar(max) N''$.summary'') AS parsed;
                    DECLARE @RoleTitle nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.role_title''))), N''''),
                            @Employer nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.employer_name''))), N''''),
                            @RoleLocation nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.location_text''))), N''''),
                            @RoleStart date = TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.start_date''), 23),
                            @RoleEnd date = TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.end_date''), 23),
                            @DatePrecision nvarchar(20) = JSON_VALUE(@CommandJson, ''$.values.date_precision''),
                            @EmploymentType nvarchar(30) = JSON_VALUE(@CommandJson, ''$.values.employment_type''),
                            @CurrentRole bit = CASE JSON_VALUE(@CommandJson, ''$.values.current_role'') WHEN N''true'' THEN 1 WHEN N''false'' THEN 0 END;
                    IF @RoleTitle IS NULL OR @Employer IS NULL OR @CurrentRole IS NULL
                       OR LEN(@RoleSummary) > 8000
                       OR @DatePrecision NOT IN (N''day'',N''month'',N''year'',N''unknown'')
                       OR (@EmploymentType IS NOT NULL AND @EmploymentType NOT IN (N''full_time'',N''part_time'',N''contract'',N''freelance'',N''internship'',N''volunteer'',N''military'',N''other''))
                       OR (@RoleEnd IS NOT NULL AND @RoleStart IS NULL)
                       OR (@RoleEnd IS NOT NULL AND @RoleEnd < @RoleStart)
                       OR (@CurrentRole = 1 AND @RoleEnd IS NOT NULL)
                        THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                    INSERT dbo.career_chapters
                        (chapter_key, owner_profile_id, entity_id, chapter_type, title,
                         organization_name, location_text, summary, original_member_wording,
                         start_date, end_date, date_precision, visibility, approval_status,
                         publication_status, created_by_user_id)
                    VALUES
                        (@RecordKey, @ProfileId, @EntityId, N''experience'', @RoleTitle,
                         @Employer, @RoleLocation, @RoleSummary, @RoleSummary,
                         @RoleStart, @RoleEnd, @DatePrecision, N''private'', N''draft'',
                         N''unpublished'', @ActorUserId);
                    SET @ChapterId = SCOPE_IDENTITY();
                    INSERT dbo.career_experiences
                        (chapter_id, owner_profile_id, role_title, employer_name, employment_type, current_role)
                    VALUES (@ChapterId, @ProfileId, @RoleTitle, @Employer, @EmploymentType, @CurrentRole);
                    SELECT @ResultVersion = row_version FROM dbo.career_chapters WHERE chapter_id = @ChapterId;
                END;

                IF @RecordType = N''credential''
                BEGIN
                    DECLARE @CredentialName nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.name''))), N''''),
                            @Issuer nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.issuer''))), N''''),
                            @Identifier nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.identifier''))), N''''),
                            @IssueDate date = TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.issue_date''), 23),
                            @ExpirationDate date = TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.expiration_date''), 23),
                            @VerificationUrl nvarchar(1000) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.verification_url''))), N''''),
                            @CompletionStatus nvarchar(30) = JSON_VALUE(@CommandJson, ''$.values.completion_status'');
                    IF @CredentialName IS NULL OR @Issuer IS NULL
                       OR @CompletionStatus NOT IN (N''planned'',N''in_progress'',N''completed'')
                       OR (@CompletionStatus IN (N''planned'',N''in_progress'') AND (@IssueDate IS NOT NULL OR @ExpirationDate IS NOT NULL))
                       OR (@CompletionStatus = N''completed'' AND @IssueDate IS NULL)
                       OR (@ExpirationDate IS NOT NULL AND @ExpirationDate < @IssueDate)
                       OR (@VerificationUrl IS NOT NULL AND @VerificationUrl NOT LIKE N''http://%'' AND @VerificationUrl NOT LIKE N''https://%'')
                        THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                    INSERT dbo.career_chapters
                        (chapter_key, owner_profile_id, entity_id, chapter_type, title,
                         organization_name, start_date, end_date, date_precision,
                         visibility, approval_status, publication_status, created_by_user_id)
                    VALUES
                        (@RecordKey, @ProfileId, @EntityId, N''credential'', @CredentialName,
                         @Issuer, @IssueDate, @ExpirationDate, N''day'',
                         N''private'', N''draft'', N''unpublished'', @ActorUserId);
                    SET @ChapterId = SCOPE_IDENTITY();
                    INSERT dbo.career_credentials
                        (chapter_id, owner_profile_id, credential_name, issuer_name,
                         credential_identifier, issue_date, expiration_date, verification_url,
                         credential_completion_status)
                    VALUES
                        (@ChapterId, @ProfileId, @CredentialName, @Issuer,
                         @Identifier, @IssueDate, @ExpirationDate, @VerificationUrl,
                         @CompletionStatus);
                    SELECT @ResultVersion = row_version FROM dbo.career_chapters WHERE chapter_id = @ChapterId;
                END;

                IF @RecordType = N''accomplishment''
                BEGIN
                    DECLARE @Wording nvarchar(max);
                    SELECT @Wording = NULLIF(LTRIM(RTRIM(parsed.wording)), N'''')
                    FROM OPENJSON(@CommandJson, N''$.values'')
                    WITH (wording nvarchar(max) N''$.wording'') AS parsed;
                    DECLARE @MetricValue nvarchar(100) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.metric_value''))), N''''),
                            @MetricLabel nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.metric_label''))), N'''');
                    SELECT @ChapterId = chapter.chapter_id
                    FROM dbo.career_chapters AS chapter WITH (UPDLOCK, HOLDLOCK)
                    JOIN dbo.career_experiences AS experience WITH (UPDLOCK, HOLDLOCK)
                      ON experience.chapter_id = chapter.chapter_id
                     AND experience.owner_profile_id = chapter.owner_profile_id
                    JOIN dbo.slate_entities AS entity WITH (UPDLOCK, HOLDLOCK)
                      ON entity.entity_id = chapter.entity_id
                     AND entity.owner_profile_id = chapter.owner_profile_id
                    WHERE chapter.owner_profile_id = @ProfileId AND chapter.chapter_key = @ParentKey
                      AND chapter.chapter_type = N''experience'' AND chapter.deleted_at_utc IS NULL
                      AND chapter.visibility = N''private'' AND chapter.approval_status = N''draft''
                      AND chapter.publication_status = N''unpublished''
                      AND entity.visibility = N''private'' AND entity.approval_status = N''draft''
                      AND entity.publication_status = N''unpublished'' AND entity.active = 1
                      AND entity.deleted_at_utc IS NULL
                      AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                      AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                      AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id);
                    IF @ChapterId IS NULL
                        THROW 52002, ''RESUME_EDITOR_NOT_FOUND'', 1;
                    IF @Wording IS NULL OR LEN(@Wording) > 8000
                        THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                    INSERT dbo.career_achievements
                        (achievement_key, owner_profile_id, entity_id, chapter_id,
                         original_member_wording, metric_value, metric_label,
                         visibility, approval_status, created_by_user_id)
                    VALUES
                        (@RecordKey, @ProfileId, @EntityId, @ChapterId,
                         @Wording, @MetricValue, @MetricLabel,
                         N''private'', N''draft'', @ActorUserId);
                    SET @RecordId = SCOPE_IDENTITY();
                    SELECT @ResultVersion = row_version FROM dbo.career_achievements WHERE achievement_id = @RecordId;
                END;

                IF @RecordType = N''skill''
                BEGIN
                    DECLARE @SkillSummary nvarchar(max);
                    SELECT @SkillSummary = NULLIF(LTRIM(RTRIM(parsed.summary)), N'''')
                    FROM OPENJSON(@CommandJson, N''$.values'')
                    WITH (summary nvarchar(max) N''$.summary'') AS parsed;
                    DECLARE @SkillName nvarchar(200) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.name''))), N'''');
                    IF @SkillName IS NULL OR LEN(@SkillSummary) > 8000 OR EXISTS
                        (SELECT 1 FROM dbo.career_skills WITH (UPDLOCK, HOLDLOCK)
                         WHERE owner_profile_id = @ProfileId AND skill_name = @SkillName AND deleted_at_utc IS NULL)
                        THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                    INSERT dbo.career_skills
                        (skill_key, owner_profile_id, entity_id, skill_name, skill_summary,
                         visibility, approval_status)
                    VALUES
                        (@RecordKey, @ProfileId, @EntityId, @SkillName, @SkillSummary,
                         N''private'', N''draft'');
                    SET @RecordId = SCOPE_IDENTITY();
                    SELECT @ResultVersion = row_version FROM dbo.career_skills WHERE skill_id = @RecordId;
                END;
                SET @Outcome = N''created'';
            END;

            IF @Operation IN (N''update'', N''remove'')
            BEGIN
                DECLARE @CurrentVersion binary(8);
                IF @RecordType = N''role''
                    SELECT @ChapterId = chapter.chapter_id, @EntityId = chapter.entity_id, @CurrentVersion = chapter.row_version
                    FROM dbo.career_chapters AS chapter WITH (UPDLOCK, HOLDLOCK)
                    JOIN dbo.career_experiences AS experience WITH (UPDLOCK, HOLDLOCK)
                      ON experience.chapter_id = chapter.chapter_id
                     AND experience.owner_profile_id = chapter.owner_profile_id
                    WHERE chapter.owner_profile_id = @ProfileId AND chapter.chapter_key = @RecordKey
                      AND chapter.chapter_type = N''experience''
                      AND chapter.deleted_at_utc IS NULL;
                IF @RecordType = N''credential''
                    SELECT @ChapterId = chapter.chapter_id, @EntityId = chapter.entity_id, @CurrentVersion = chapter.row_version
                    FROM dbo.career_chapters AS chapter WITH (UPDLOCK, HOLDLOCK)
                    JOIN dbo.career_credentials AS credential WITH (UPDLOCK, HOLDLOCK)
                      ON credential.chapter_id = chapter.chapter_id
                     AND credential.owner_profile_id = chapter.owner_profile_id
                    WHERE chapter.owner_profile_id = @ProfileId AND chapter.chapter_key = @RecordKey
                      AND chapter.chapter_type = N''credential''
                      AND chapter.deleted_at_utc IS NULL;
                IF @RecordType = N''accomplishment''
                BEGIN
                    DECLARE @CandidateChapterId bigint,
                            @ParentEntityId bigint,
                            @ParentChapterValid bit,
                            @ExperienceParentValid bit;
                    SELECT @CandidateChapterId = achievement.chapter_id
                    FROM dbo.career_achievements AS achievement WITH (READUNCOMMITTED)
                    WHERE achievement.owner_profile_id = @ProfileId AND achievement.achievement_key = @RecordKey
                      AND achievement.deleted_at_utc IS NULL;

                    SELECT @ParentEntityId = parent_chapter.entity_id,
                           @ParentChapterValid = CASE
                               WHEN parent_chapter.chapter_type = N''experience''
                                AND parent_chapter.deleted_at_utc IS NULL
                                AND parent_chapter.visibility = N''private''
                                AND parent_chapter.approval_status = N''draft''
                                AND parent_chapter.publication_status = N''unpublished''
                               THEN 1 ELSE 0 END
                    FROM dbo.career_chapters AS parent_chapter WITH (UPDLOCK, HOLDLOCK)
                    WHERE parent_chapter.chapter_id = @CandidateChapterId
                      AND parent_chapter.owner_profile_id = @ProfileId;

                    SELECT @ExperienceParentValid = 1
                    FROM dbo.career_experiences AS parent_experience WITH (UPDLOCK, HOLDLOCK)
                    JOIN dbo.slate_entities AS parent_entity WITH (UPDLOCK, HOLDLOCK)
                      ON parent_entity.entity_id = @ParentEntityId
                     AND parent_entity.owner_profile_id = parent_experience.owner_profile_id
                    WHERE parent_experience.chapter_id = @CandidateChapterId
                      AND parent_experience.owner_profile_id = @ProfileId
                      AND @ParentChapterValid = 1
                      AND parent_entity.active = 1 AND parent_entity.deleted_at_utc IS NULL
                      AND parent_entity.visibility = N''private''
                      AND parent_entity.approval_status = N''draft''
                      AND parent_entity.publication_status = N''unpublished''
                      AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = parent_entity.entity_id)
                      AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = parent_entity.entity_id)
                      AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = parent_entity.entity_id);

                    SELECT @RecordId = achievement.achievement_id, @EntityId = achievement.entity_id,
                           @ChapterId = achievement.chapter_id, @CurrentVersion = achievement.row_version
                    FROM dbo.career_achievements AS achievement WITH (UPDLOCK, HOLDLOCK)
                    WHERE achievement.owner_profile_id = @ProfileId AND achievement.achievement_key = @RecordKey
                      AND achievement.chapter_id = @CandidateChapterId
                      AND achievement.deleted_at_utc IS NULL;
                    IF @EntityId IS NOT NULL AND @ExperienceParentValid IS NULL
                        THROW 52005, ''RESUME_EDITOR_PROTECTED'', 1;
                END;
                IF @RecordType = N''skill''
                    SELECT @RecordId = skill.skill_id, @EntityId = skill.entity_id, @CurrentVersion = skill.row_version
                    FROM dbo.career_skills AS skill WITH (UPDLOCK, HOLDLOCK)
                    WHERE skill.owner_profile_id = @ProfileId AND skill.skill_key = @RecordKey
                      AND skill.deleted_at_utc IS NULL;
                IF @EntityId IS NULL
                    THROW 52002, ''RESUME_EDITOR_NOT_FOUND'', 1;
                IF @CurrentVersion <> @ExpectedVersion
                BEGIN
                    ROLLBACK TRANSACTION;
                    SELECT CONVERT(bit, 0) AS committed, N''changed'' AS error_code,
                           CAST(NULL AS uniqueidentifier) AS command_id,
                           CAST(NULL AS char(64)) AS request_digest,
                           CAST(NULL AS nvarchar(40)) AS command_type,
                           CAST(NULL AS uniqueidentifier) AS record_key,
                           CAST(NULL AS nvarchar(20)) AS outcome,
                           CAST(NULL AS binary(8)) AS record_version,
                           CONVERT(bit, 0) AS replayed;
                    RETURN;
                END;

                DECLARE @AffectedEntities TABLE (entity_id bigint PRIMARY KEY);
                INSERT @AffectedEntities VALUES (@EntityId);
                IF @Operation = N''remove'' AND @RecordType IN (N''role'', N''credential'')
                BEGIN
                    INSERT @AffectedEntities(entity_id)
                    SELECT achievement.entity_id FROM dbo.career_achievements AS achievement
                    WHERE achievement.owner_profile_id = @ProfileId AND achievement.chapter_id = @ChapterId
                      AND achievement.deleted_at_utc IS NULL AND NOT EXISTS
                          (SELECT 1 FROM @AffectedEntities AS present WHERE present.entity_id = achievement.entity_id);
                    INSERT @AffectedEntities(entity_id)
                    SELECT timeline.entity_id FROM dbo.career_timeline_events AS timeline
                    WHERE timeline.owner_profile_id = @ProfileId AND timeline.chapter_id = @ChapterId
                      AND NOT EXISTS (SELECT 1 FROM @AffectedEntities AS present WHERE present.entity_id = timeline.entity_id);
                END;

                IF EXISTS
                (
                    SELECT 1 FROM @AffectedEntities AS affected
                    JOIN dbo.slate_entities AS entity WITH (UPDLOCK, HOLDLOCK) ON entity.entity_id = affected.entity_id
                    WHERE entity.owner_profile_id <> @ProfileId
                       OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft''
                       OR entity.publication_status <> N''unpublished'' OR entity.active <> 1 OR entity.deleted_at_utc IS NOT NULL
                ) OR EXISTS
                (
                    SELECT 1 FROM @AffectedEntities AS affected
                    WHERE EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = affected.entity_id)
                       OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = affected.entity_id)
                       OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = affected.entity_id)
                ) OR EXISTS
                (
                    SELECT 1 FROM dbo.career_achievements AS achievement
                    WHERE achievement.entity_id IN (SELECT entity_id FROM @AffectedEntities)
                      AND (achievement.owner_profile_id <> @ProfileId
                           OR achievement.visibility <> N''private''
                           OR achievement.approval_status <> N''draft''
                           OR achievement.deleted_at_utc IS NOT NULL)
                ) OR EXISTS
                (
                    SELECT 1 FROM dbo.career_timeline_events AS timeline
                    WHERE timeline.entity_id IN (SELECT entity_id FROM @AffectedEntities)
                      AND (timeline.owner_profile_id <> @ProfileId
                           OR timeline.visibility <> N''private''
                           OR timeline.approval_status <> N''draft'')
                ) OR EXISTS
                (
                    SELECT 1 FROM dbo.slate_entity_relations AS relation
                    WHERE (relation.from_entity_id IN (SELECT entity_id FROM @AffectedEntities)
                           OR relation.to_entity_id IN (SELECT entity_id FROM @AffectedEntities))
                      AND
                      (
                          relation.owner_profile_id <> @ProfileId OR relation.visibility <> N''private''
                          OR relation.approval_status <> N''proposed''
                          OR EXISTS
                            (SELECT 1 FROM dbo.slate_entities AS counterpart
                             WHERE counterpart.entity_id = CASE WHEN relation.from_entity_id IN (SELECT entity_id FROM @AffectedEntities)
                                                               THEN relation.to_entity_id ELSE relation.from_entity_id END
                               AND (counterpart.owner_profile_id <> @ProfileId OR counterpart.visibility <> N''private''
                                    OR counterpart.approval_status <> N''draft''
                                    OR counterpart.publication_status <> N''unpublished'' OR counterpart.active <> 1
                                    OR counterpart.deleted_at_utc IS NOT NULL
                                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = counterpart.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = counterpart.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = counterpart.entity_id)))
                      )
                ) OR EXISTS
                (
                    SELECT 1 FROM dbo.career_skill_links AS link
                    WHERE (link.source_entity_id IN (SELECT entity_id FROM @AffectedEntities)
                           OR link.skill_id = CASE WHEN @RecordType = N''skill'' THEN @RecordId ELSE -1 END)
                      AND
                      (
                          link.owner_profile_id <> @ProfileId OR link.approval_status <> N''proposed''
                          OR EXISTS
                            (SELECT 1 FROM dbo.slate_entities AS source_entity
                             WHERE source_entity.entity_id = link.source_entity_id
                               AND (source_entity.owner_profile_id <> @ProfileId
                                    OR source_entity.visibility <> N''private''
                                    OR source_entity.approval_status <> N''draft''
                                    OR source_entity.publication_status <> N''unpublished''
                                    OR source_entity.active <> 1 OR source_entity.deleted_at_utc IS NOT NULL
                                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = source_entity.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = source_entity.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = source_entity.entity_id)))
                          OR EXISTS
                            (SELECT 1 FROM dbo.career_skills AS linked_skill
                             JOIN dbo.slate_entities AS skill_entity ON skill_entity.entity_id = linked_skill.entity_id
                             WHERE linked_skill.skill_id = link.skill_id
                               AND (linked_skill.owner_profile_id <> @ProfileId
                                    OR linked_skill.visibility <> N''private'' OR linked_skill.approval_status <> N''draft''
                                    OR skill_entity.visibility <> N''private'' OR skill_entity.approval_status <> N''draft''
                                    OR skill_entity.publication_status <> N''unpublished''
                                    OR skill_entity.active <> 1 OR skill_entity.deleted_at_utc IS NOT NULL
                                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = skill_entity.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = skill_entity.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = skill_entity.entity_id)))
                          OR EXISTS
                            (SELECT 1 FROM dbo.evidence_items AS evidence
                             JOIN dbo.slate_entities AS evidence_entity ON evidence_entity.entity_id = evidence.entity_id
                             WHERE evidence.evidence_item_id = link.evidence_item_id
                               AND (evidence.owner_profile_id <> @ProfileId OR evidence.visibility <> N''private''
                                    OR evidence_entity.visibility <> N''private'' OR evidence_entity.approval_status <> N''draft''
                                    OR evidence_entity.publication_status <> N''unpublished''
                                    OR evidence_entity.active <> 1 OR evidence_entity.deleted_at_utc IS NOT NULL
                                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = evidence_entity.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = evidence_entity.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = evidence_entity.entity_id)))
                      )
                ) OR EXISTS
                (
                    SELECT 1 FROM dbo.evidence_links AS evidence_link
                    WHERE evidence_link.source_entity_id IN (SELECT entity_id FROM @AffectedEntities)
                      AND
                      (
                          evidence_link.approval_status <> N''proposed''
                          OR EXISTS
                            (SELECT 1 FROM dbo.evidence_items AS evidence
                             JOIN dbo.slate_entities AS evidence_entity ON evidence_entity.entity_id = evidence.entity_id
                             WHERE evidence.evidence_item_id = evidence_link.evidence_item_id
                               AND (evidence.owner_profile_id <> @ProfileId OR evidence.visibility <> N''private''
                                    OR evidence_entity.visibility <> N''private'' OR evidence_entity.approval_status <> N''draft''
                                    OR evidence_entity.publication_status <> N''unpublished''
                                    OR evidence_entity.active <> 1 OR evidence_entity.deleted_at_utc IS NOT NULL
                                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = evidence_entity.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = evidence_entity.entity_id)
                                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = evidence_entity.entity_id)))
                      )
                ) OR EXISTS
                (
                    SELECT 1 FROM dbo.ai_proposals AS proposal
                    WHERE proposal.owner_profile_id = @ProfileId
                      AND proposal.target_entity_id IN (SELECT entity_id FROM @AffectedEntities)
                )
                    THROW 52005, ''RESUME_EDITOR_PROTECTED'', 1;

                IF @RecordType IN (N''role'', N''credential'') AND EXISTS
                    (SELECT 1 FROM dbo.career_chapters WHERE chapter_id = @ChapterId
                     AND (visibility <> N''private'' OR approval_status <> N''draft'' OR publication_status <> N''unpublished''))
                    THROW 52005, ''RESUME_EDITOR_PROTECTED'', 1;
                IF @RecordType = N''accomplishment'' AND EXISTS
                    (SELECT 1 FROM dbo.career_achievements WHERE achievement_id = @RecordId
                     AND (visibility <> N''private'' OR approval_status <> N''draft''))
                    THROW 52005, ''RESUME_EDITOR_PROTECTED'', 1;
                IF @RecordType = N''skill'' AND EXISTS
                    (SELECT 1 FROM dbo.career_skills WHERE skill_id = @RecordId
                     AND (visibility <> N''private'' OR approval_status <> N''draft''))
                    THROW 52005, ''RESUME_EDITOR_PROTECTED'', 1;

                IF @Operation = N''update''
                BEGIN
                    UPDATE dbo.slate_entities
                    SET visibility=N''private'', approval_status=N''draft'', publication_status=N''unpublished'', updated_at_utc=SYSUTCDATETIME()
                    WHERE entity_id=@EntityId AND owner_profile_id=@ProfileId;

                    IF @RecordType = N''role''
                    BEGIN
                        DECLARE @UpdateRoleSummary nvarchar(max);
                        SELECT @UpdateRoleSummary = NULLIF(LTRIM(RTRIM(parsed.summary)), N'''')
                        FROM OPENJSON(@CommandJson, N''$.values'')
                        WITH (summary nvarchar(max) N''$.summary'') AS parsed;
                        DECLARE @UpdateRoleTitle nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.role_title''))), N''''),
                                @UpdateEmployer nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.employer_name''))), N''''),
                                @UpdateRoleLocation nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.location_text''))), N''''),
                                @UpdateRoleStart date = TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.start_date''), 23),
                                @UpdateRoleEnd date = TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.end_date''), 23),
                                @UpdateDatePrecision nvarchar(20) = JSON_VALUE(@CommandJson, ''$.values.date_precision''),
                                @UpdateEmploymentType nvarchar(30) = JSON_VALUE(@CommandJson, ''$.values.employment_type''),
                                @UpdateCurrentRole bit = CASE JSON_VALUE(@CommandJson, ''$.values.current_role'') WHEN N''true'' THEN 1 WHEN N''false'' THEN 0 END;
                        IF @UpdateRoleTitle IS NULL OR @UpdateEmployer IS NULL OR @UpdateCurrentRole IS NULL
                           OR LEN(@UpdateRoleSummary) > 8000
                           OR @UpdateDatePrecision NOT IN (N''day'',N''month'',N''year'',N''unknown'')
                           OR (@UpdateEmploymentType IS NOT NULL AND @UpdateEmploymentType NOT IN (N''full_time'',N''part_time'',N''contract'',N''freelance'',N''internship'',N''volunteer'',N''military'',N''other''))
                           OR (@UpdateRoleEnd IS NOT NULL AND @UpdateRoleStart IS NULL)
                           OR (@UpdateRoleEnd IS NOT NULL AND @UpdateRoleEnd < @UpdateRoleStart)
                           OR (@UpdateCurrentRole = 1 AND @UpdateRoleEnd IS NOT NULL)
                            THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        UPDATE dbo.career_chapters
                        SET title=@UpdateRoleTitle, organization_name=@UpdateEmployer,
                            location_text=@UpdateRoleLocation, summary=@UpdateRoleSummary,
                            original_member_wording=@UpdateRoleSummary,
                            start_date=@UpdateRoleStart, end_date=@UpdateRoleEnd,
                            date_precision=@UpdateDatePrecision, visibility=N''private'',
                            approval_status=N''draft'', publication_status=N''unpublished'',
                            approved_by_user_id=NULL, approved_at_utc=NULL, updated_at_utc=SYSUTCDATETIME()
                        WHERE chapter_id=@ChapterId AND owner_profile_id=@ProfileId AND row_version=@ExpectedVersion;
                        IF @@ROWCOUNT <> 1 THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        UPDATE dbo.career_experiences
                        SET role_title=@UpdateRoleTitle, employer_name=@UpdateEmployer,
                            employment_type=@UpdateEmploymentType, current_role=@UpdateCurrentRole
                        WHERE chapter_id=@ChapterId AND owner_profile_id=@ProfileId;
                        IF @@ROWCOUNT <> 1 THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        SELECT @ResultVersion=row_version FROM dbo.career_chapters WHERE chapter_id=@ChapterId;
                    END;

                    IF @RecordType = N''credential''
                    BEGIN
                        DECLARE @UpdateCredentialName nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.name''))), N''''),
                                @UpdateIssuer nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.issuer''))), N''''),
                                @UpdateIdentifier nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.identifier''))), N''''),
                                @UpdateIssueDate date = TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.issue_date''), 23),
                                @UpdateExpirationDate date = TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.expiration_date''), 23),
                                @UpdateVerificationUrl nvarchar(1000) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.verification_url''))), N''''),
                                @UpdateCompletionStatus nvarchar(30) = JSON_VALUE(@CommandJson, ''$.values.completion_status'');
                        IF @UpdateCredentialName IS NULL OR @UpdateIssuer IS NULL
                           OR @UpdateCompletionStatus NOT IN (N''planned'',N''in_progress'',N''completed'')
                           OR (@UpdateCompletionStatus IN (N''planned'',N''in_progress'') AND (@UpdateIssueDate IS NOT NULL OR @UpdateExpirationDate IS NOT NULL))
                           OR (@UpdateCompletionStatus = N''completed'' AND @UpdateIssueDate IS NULL)
                           OR (@UpdateExpirationDate IS NOT NULL AND @UpdateExpirationDate < @UpdateIssueDate)
                           OR (@UpdateVerificationUrl IS NOT NULL AND @UpdateVerificationUrl NOT LIKE N''http://%'' AND @UpdateVerificationUrl NOT LIKE N''https://%'')
                            THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        UPDATE dbo.career_chapters
                        SET title=@UpdateCredentialName, organization_name=@UpdateIssuer,
                            start_date=@UpdateIssueDate, end_date=@UpdateExpirationDate,
                            date_precision=N''day'', visibility=N''private'', approval_status=N''draft'',
                            publication_status=N''unpublished'', approved_by_user_id=NULL,
                            approved_at_utc=NULL, updated_at_utc=SYSUTCDATETIME()
                        WHERE chapter_id=@ChapterId AND owner_profile_id=@ProfileId AND row_version=@ExpectedVersion;
                        IF @@ROWCOUNT <> 1 THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        UPDATE dbo.career_credentials
                        SET credential_name=@UpdateCredentialName, issuer_name=@UpdateIssuer,
                            credential_identifier=@UpdateIdentifier, issue_date=@UpdateIssueDate,
                            expiration_date=@UpdateExpirationDate, verification_url=@UpdateVerificationUrl,
                            credential_completion_status=@UpdateCompletionStatus
                        WHERE chapter_id=@ChapterId AND owner_profile_id=@ProfileId;
                        IF @@ROWCOUNT <> 1 THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        SELECT @ResultVersion=row_version FROM dbo.career_chapters WHERE chapter_id=@ChapterId;
                    END;

                    IF @RecordType = N''accomplishment''
                    BEGIN
                        DECLARE @UpdateWording nvarchar(max);
                        SELECT @UpdateWording = NULLIF(LTRIM(RTRIM(parsed.wording)), N'''')
                        FROM OPENJSON(@CommandJson, N''$.values'')
                        WITH (wording nvarchar(max) N''$.wording'') AS parsed;
                        DECLARE @UpdateMetricValue nvarchar(100) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.metric_value''))), N''''),
                                @UpdateMetricLabel nvarchar(300) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.metric_label''))), N'''');
                        IF @UpdateWording IS NULL OR LEN(@UpdateWording) > 8000 THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        UPDATE dbo.career_achievements
                        SET original_member_wording=@UpdateWording, metric_value=@UpdateMetricValue,
                            metric_label=@UpdateMetricLabel, visibility=N''private'', approval_status=N''draft'',
                            approved_by_user_id=NULL, approved_at_utc=NULL, updated_at_utc=SYSUTCDATETIME()
                        WHERE achievement_id=@RecordId AND owner_profile_id=@ProfileId AND row_version=@ExpectedVersion;
                        IF @@ROWCOUNT <> 1 THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        SELECT @ResultVersion=row_version FROM dbo.career_achievements WHERE achievement_id=@RecordId;
                    END;

                    IF @RecordType = N''skill''
                    BEGIN
                        DECLARE @UpdateSkillSummary nvarchar(max);
                        SELECT @UpdateSkillSummary = NULLIF(LTRIM(RTRIM(parsed.summary)), N'''')
                        FROM OPENJSON(@CommandJson, N''$.values'')
                        WITH (summary nvarchar(max) N''$.summary'') AS parsed;
                        DECLARE @UpdateSkillName nvarchar(200) = NULLIF(LTRIM(RTRIM(JSON_VALUE(@CommandJson, ''$.values.name''))), N'''');
                        IF @UpdateSkillName IS NULL OR LEN(@UpdateSkillSummary) > 8000 OR EXISTS
                            (SELECT 1 FROM dbo.career_skills WITH (UPDLOCK, HOLDLOCK)
                             WHERE owner_profile_id=@ProfileId AND skill_name=@UpdateSkillName
                               AND skill_id<>@RecordId AND deleted_at_utc IS NULL)
                            THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        UPDATE dbo.career_skills
                        SET skill_name=@UpdateSkillName, skill_summary=@UpdateSkillSummary,
                            visibility=N''private'', approval_status=N''draft'', updated_at_utc=SYSUTCDATETIME()
                        WHERE skill_id=@RecordId AND owner_profile_id=@ProfileId AND row_version=@ExpectedVersion;
                        IF @@ROWCOUNT <> 1 THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                        SELECT @ResultVersion=row_version FROM dbo.career_skills WHERE skill_id=@RecordId;
                    END;
                    IF @ResultVersion IS NULL THROW 52003, ''RESUME_EDITOR_VALIDATION'', 1;
                    SET @Outcome=N''updated'';
                END;

                IF @Operation = N''remove''
                BEGIN
                    DELETE evidence_link FROM dbo.evidence_links AS evidence_link
                    WHERE evidence_link.owner_profile_id=@ProfileId
                      AND evidence_link.source_entity_id IN (SELECT entity_id FROM @AffectedEntities)
                      AND evidence_link.approval_status=N''proposed'';
                    DELETE link FROM dbo.career_skill_links AS link
                    WHERE link.owner_profile_id=@ProfileId
                      AND (link.source_entity_id IN (SELECT entity_id FROM @AffectedEntities)
                           OR link.skill_id=CASE WHEN @RecordType=N''skill'' THEN @RecordId ELSE -1 END)
                      AND link.approval_status=N''proposed'';
                    DELETE relation FROM dbo.slate_entity_relations AS relation
                    WHERE relation.owner_profile_id=@ProfileId AND relation.visibility=N''private''
                      AND relation.approval_status=N''proposed''
                      AND (relation.from_entity_id IN (SELECT entity_id FROM @AffectedEntities)
                           OR relation.to_entity_id IN (SELECT entity_id FROM @AffectedEntities));
                    IF @RecordType IN (N''role'',N''credential'')
                    BEGIN
                        DELETE FROM dbo.career_timeline_events
                        WHERE owner_profile_id=@ProfileId AND chapter_id=@ChapterId;
                        UPDATE dbo.career_achievements
                        SET deleted_at_utc=SYSUTCDATETIME(), updated_at_utc=SYSUTCDATETIME()
                        WHERE owner_profile_id=@ProfileId AND chapter_id=@ChapterId AND deleted_at_utc IS NULL;
                        UPDATE dbo.career_chapters
                        SET deleted_at_utc=SYSUTCDATETIME(), updated_at_utc=SYSUTCDATETIME()
                        WHERE owner_profile_id=@ProfileId AND chapter_id=@ChapterId AND row_version=@ExpectedVersion;
                    END;
                    IF @RecordType=N''accomplishment''
                        UPDATE dbo.career_achievements SET deleted_at_utc=SYSUTCDATETIME(), updated_at_utc=SYSUTCDATETIME()
                        WHERE owner_profile_id=@ProfileId AND achievement_id=@RecordId AND row_version=@ExpectedVersion;
                    IF @RecordType=N''skill''
                        UPDATE dbo.career_skills SET deleted_at_utc=SYSUTCDATETIME(), updated_at_utc=SYSUTCDATETIME()
                        WHERE owner_profile_id=@ProfileId AND skill_id=@RecordId AND row_version=@ExpectedVersion;
                    UPDATE entity
                    SET active=0, deleted_at_utc=SYSUTCDATETIME(), updated_at_utc=SYSUTCDATETIME()
                    FROM dbo.slate_entities AS entity
                    JOIN @AffectedEntities AS affected ON affected.entity_id=entity.entity_id
                    WHERE entity.owner_profile_id=@ProfileId;
                    SET @Outcome=N''removed'';
                    SET @ResultVersion=NULL;
                END;
            END;

            INSERT dbo.living_resume_command_receipts
                (owner_profile_id, command_id, request_digest, command_type,
                 record_type, record_key, outcome, result_version)
            VALUES
                (@ProfileId, @CommandId, @Digest, @Type,
                 @RecordType, @RecordKey, @Outcome, @ResultVersion);

            COMMIT TRANSACTION;
            SELECT CONVERT(bit, 1) AS committed, CAST(NULL AS nvarchar(40)) AS error_code,
                   @CommandId AS command_id, @Digest AS request_digest,
                   @Type AS command_type, @RecordKey AS record_key,
                   @Outcome AS outcome, @ResultVersion AS record_version,
                   CONVERT(bit, 0) AS replayed;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-EDIT-001')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES
            (N'PS-RESUME-EDIT-001',
             N'Proposed owner-scoped private Living Resume editor commands and idempotency receipts',
             N'PeerSlate MVP1 Package 1');
        EXEC dbo.usp_AppendAuditEvent
            @ActionType=N'schema.migration.applied', @EntityType=N'database_migration',
            @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-RESUME-EDIT-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
