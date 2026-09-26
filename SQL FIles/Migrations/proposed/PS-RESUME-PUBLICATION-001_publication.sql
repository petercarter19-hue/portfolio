/*
PS-RESUME-PUBLICATION-001 — complete Resume publication consistency boundary.

PROPOSED ONLY. Gate is null. One application write command owns publish,
canonical correction, restriction, restore-private, sharing, media and
catalog fences. Ambient transactions are refused. Internal helpers are
ownership-chained and DENY EXECUTE to the application principal.

Lock order (deterministic): owner sharing row → sorted entry IDs → draft →
publication/receipts → media/catalog.

Codec resume-canonical-source.v1 is length-prefixed UTF-8, matching Python.
Evidence rows are inserted in the same transaction. Display and visitor-AI
manifests are produced separately. Caller JSON is not stored as canonical
evidence.

Entry-policy command vocabulary and @UserKey nvarchar(300) are preserved.
Affected draft/media/intake/editor mutators enter this boundary or refuse.
Rollback restores the replaced procedures from their original Core names.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-CATALOG-001')
        THROW 54000, 'PS-RESUME-CATALOG-001 must be applied first.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-DRAFT-001')
        THROW 54001, 'PS-RESUME-DRAFT-001 must be applied first.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-ENTRY-POLICY-001')
        THROW 54002, 'PS-ENTRY-POLICY-001 must be applied first.', 1;

    -- Renaming a predecessor procedure preserves its object permissions. Keep
    -- the exact PUBLIC state before this migration protects the Core ports so
    -- an empty rollback can restore their effective application access.
    IF OBJECT_ID(N'dbo.resume_publication_core_execute_permissions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_publication_core_execute_permissions (
            procedure_name sysname NOT NULL PRIMARY KEY,
            permission_state char(1) NULL,
            CONSTRAINT CK_resume_publication_core_execute_state
                CHECK (permission_state IN ('G', 'D', 'W') OR permission_state IS NULL)
        );
        INSERT dbo.resume_publication_core_execute_permissions (procedure_name, permission_state)
        SELECT predecessor.procedure_name, permission_record.state
          FROM (VALUES
              (N'usp_CommitEntryPolicyCommandForOwner'),
              (N'usp_ListEntryPolicyEntriesForOwner'),
              (N'usp_GetEntryPolicyEntryForOwner'),
              (N'usp_CommitResumeDraftCommandForOwner'),
              (N'usp_CommitResumeMediaCommandForOwner'),
              (N'usp_CommitResumeIntakeCommandForOwner'),
              (N'usp_CommitLivingResumeCommandForOwner')
          ) AS predecessor(procedure_name)
          JOIN sys.objects AS object_record
            ON object_record.object_id = OBJECT_ID(N'dbo.' + predecessor.procedure_name, N'P')
          LEFT JOIN sys.database_permissions AS permission_record
            ON permission_record.class = 1 AND permission_record.major_id = object_record.object_id
           AND permission_record.minor_id = 0 AND permission_record.permission_name = N'EXECUTE'
           AND permission_record.grantee_principal_id = DATABASE_PRINCIPAL_ID(N'public');
    END;

    IF OBJECT_ID(N'dbo.resume_sharing_state', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_sharing_state
        (
            owner_profile_id bigint NOT NULL,
            sharing_enabled bit NOT NULL CONSTRAINT DF_resume_sharing_enabled DEFAULT 0,
            sharing_epoch int NOT NULL CONSTRAINT DF_resume_sharing_epoch DEFAULT 0,
            publication_revision int NOT NULL CONSTRAINT DF_resume_sharing_revision DEFAULT 0,
            current_revision int NULL,
            public_slug nvarchar(100) NULL,
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_sharing_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_sharing_state PRIMARY KEY (owner_profile_id),
            CONSTRAINT FK_resume_sharing_state_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id)
        );
    END;

    -- Unpublished owners have no slug. Enforce uniqueness only after a
    -- slug exists; SQL Server otherwise permits only one NULL owner row.
    IF EXISTS (SELECT 1 FROM sys.key_constraints
               WHERE parent_object_id = OBJECT_ID(N'dbo.resume_sharing_state')
                 AND name = N'UQ_resume_sharing_state_slug')
        ALTER TABLE dbo.resume_sharing_state DROP CONSTRAINT UQ_resume_sharing_state_slug;
    IF NOT EXISTS (SELECT 1 FROM sys.indexes
                   WHERE object_id = OBJECT_ID(N'dbo.resume_sharing_state')
                     AND name = N'UX_resume_sharing_state_public_slug')
        CREATE UNIQUE INDEX UX_resume_sharing_state_public_slug
            ON dbo.resume_sharing_state(public_slug) WHERE public_slug IS NOT NULL;

    IF OBJECT_ID(N'dbo.resume_publication_revisions', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_publication_revisions
        (
            publication_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            publication_revision int NOT NULL,
            reviewed_digest char(64) NOT NULL,
            display_json nvarchar(max) NOT NULL,
            visitor_ai_json nvarchar(max) NOT NULL,
            evidence_json nvarchar(max) NOT NULL,
            media_json nvarchar(max) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_publication_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_publication_revisions PRIMARY KEY (publication_id),
            CONSTRAINT UQ_resume_publication_owner_revision UNIQUE (owner_profile_id, publication_revision),
            CONSTRAINT FK_resume_publication_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id)
        );
    END;

    IF OBJECT_ID(N'dbo.resume_publication_evidence', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_publication_evidence
        (
            evidence_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            entry_key uniqueidentifier NOT NULL,
            evidence_version_key nvarchar(120) NOT NULL,
            codec nvarchar(40) NOT NULL,
            canonical_token nvarchar(100) NOT NULL,
            policy_content_version int NOT NULL,
            access_revision int NOT NULL,
            content_bytes varbinary(max) NOT NULL,
            content_sha256 char(64) NOT NULL,
            display_eligible bit NOT NULL,
            visitor_ai_eligible bit NOT NULL,
            CONSTRAINT PK_resume_publication_evidence PRIMARY KEY (evidence_id),
            CONSTRAINT UQ_resume_publication_evidence_version UNIQUE (evidence_version_key),
            CONSTRAINT FK_resume_publication_evidence_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_publication_evidence_codec CHECK (codec = N'resume-canonical-source.v1')
        );
    END;

    IF OBJECT_ID(N'dbo.resume_publication_receipts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_publication_receipts
        (
            command_receipt_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            request_id uniqueidentifier NOT NULL,
            request_digest char(64) NOT NULL,
            command_type nvarchar(40) NOT NULL,
            outcome nvarchar(40) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_publication_receipts_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_publication_receipts PRIMARY KEY (command_receipt_id),
            CONSTRAINT UQ_resume_publication_receipts_owner_request UNIQUE (owner_profile_id, request_id),
            CONSTRAINT FK_resume_publication_receipts_owner FOREIGN KEY (owner_profile_id)
                REFERENCES dbo.member_profiles(profile_id)
        );
        EXEC(N'
            CREATE TRIGGER dbo.trg_resume_publication_receipts_immutable
            ON dbo.resume_publication_receipts
            AFTER UPDATE, DELETE
            AS
            BEGIN
                THROW 54010, ''Publication receipts are immutable.'', 1;
            END;
        ');
    END;

    IF OBJECT_ID(N'dbo.resume_publication_outbox', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_publication_outbox
        (
            outbox_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            publication_revision int NOT NULL,
            event_type nvarchar(40) NOT NULL,
            payload_json nvarchar(max) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_publication_outbox_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_publication_outbox PRIMARY KEY (outbox_id)
        );
    END;

    EXEC sys.sp_executesql N'
CREATE OR ALTER FUNCTION dbo.fn_ResumePublicationUtf8(@Text nvarchar(max))
RETURNS varbinary(max)
WITH SCHEMABINDING
AS
BEGIN
    IF @Text IS NULL
        RETURN CAST(0x AS varbinary(max));
    RETURN CONVERT(varbinary(max), CAST(@Text COLLATE Latin1_General_100_BIN2_UTF8 AS varchar(max)));
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationEncodeSourceInternal
    @FieldsJson nvarchar(max),
    @Bytes varbinary(max) OUTPUT,
    @Digest char(64) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF @FieldsJson IS NULL OR ISJSON(@FieldsJson) <> 1
        THROW 54011, ''Canonical source fields are unavailable.'', 1;

    DECLARE @Names TABLE (sort_order int NOT NULL PRIMARY KEY, field_name nvarchar(40) NOT NULL, is_bool bit NOT NULL);
    INSERT @Names(sort_order, field_name, is_bool) VALUES
        (1, N''canonical_type'', 0),
        (2, N''role_title'', 0),
        (3, N''employer_name'', 0),
        (4, N''location_text'', 0),
        (5, N''summary'', 0),
        (6, N''start_date'', 0),
        (7, N''end_date'', 0),
        (8, N''date_precision'', 0),
        (9, N''employment_type'', 0),
        (10, N''current_role'', 1),
        (11, N''title'', 0),
        (12, N''institution_name'', 0),
        (13, N''degree_name'', 0),
        (14, N''field_of_study'', 0),
        (15, N''education_status'', 0),
        (16, N''grade_text'', 0),
        (17, N''credential_name'', 0),
        (18, N''issuer_name'', 0),
        (19, N''credential_identifier'', 0),
        (20, N''issue_date'', 0),
        (21, N''expiration_date'', 0),
        (22, N''name'', 0),
        (23, N''skill_summary'', 0),
        (24, N''wording'', 0),
        (25, N''metric_value'', 0),
        (26, N''metric_label'', 0),
        (27, N''accomplishment_to_achievement'', 1),
        (28, N''parent_canonical_type'', 0);

    -- OPENJSON retains nvarchar(max) values and JSON types. JSON_VALUE
    -- would silently turn a valid string over 4000 characters into NULL.
    DECLARE @Fields TABLE (field_name nvarchar(4000), field_value nvarchar(max), json_type int);
    INSERT @Fields SELECT [key], [value], [type] FROM OPENJSON(@FieldsJson);
    IF EXISTS (
        SELECT 1 FROM @Fields AS field
        WHERE NOT EXISTS (SELECT 1 FROM @Names AS name
            WHERE name.field_name COLLATE Latin1_General_100_BIN2 = field.field_name COLLATE Latin1_General_100_BIN2
              AND DATALENGTH(name.field_name) = DATALENGTH(field.field_name))
    ) OR EXISTS (SELECT field_name COLLATE Latin1_General_100_BIN2 FROM @Fields
                 GROUP BY field_name COLLATE Latin1_General_100_BIN2 HAVING COUNT(*) > 1)
        THROW 54012, ''unknown or duplicate codec field'', 1;

    SET @Bytes = dbo.fn_ResumePublicationUtf8(N''resume-canonical-source.v1'');
    DECLARE @Sort int = 1;
    WHILE @Sort <= 28
    BEGIN
        DECLARE @Name nvarchar(40), @IsBool bit;
        SELECT @Name = field_name, @IsBool = is_bool FROM @Names WHERE sort_order = @Sort;
        DECLARE @NameUtf8 varbinary(max) = dbo.fn_ResumePublicationUtf8(@Name);
        DECLARE @NameLen varchar(20) = CONVERT(varchar(20), DATALENGTH(@NameUtf8));
        SET @Bytes = @Bytes
            + CONVERT(varbinary(max), @NameLen COLLATE Latin1_General_BIN)
            + CONVERT(varbinary(1), 0x3A)
            + @NameUtf8;

        DECLARE @Raw nvarchar(max) = NULL, @JsonType int = NULL;
        SELECT @Raw = field_value, @JsonType = json_type FROM @Fields
         WHERE field_name COLLATE Latin1_General_100_BIN2 = @Name COLLATE Latin1_General_100_BIN2
           AND DATALENGTH(field_name) = DATALENGTH(@Name);

        IF @JsonType IS NULL OR @JsonType = 0
            SET @Bytes = @Bytes + CONVERT(varbinary(1), 0x4E);
        ELSE IF @IsBool = 1
        BEGIN
            IF @JsonType <> 3 OR @Raw NOT IN (N''true'', N''false'')
                THROW 54013, ''boolean codec field required'', 1;
            SET @Bytes = @Bytes + CONVERT(varbinary(1), 0x42)
                + CASE WHEN @Raw IN (N''true'', N''1'') THEN CONVERT(varbinary(1), 0x31) ELSE CONVERT(varbinary(1), 0x30) END;
        END
        ELSE
        BEGIN
            IF @JsonType <> 1
                THROW 54013, ''string codec field required'', 1;
            DECLARE @ValUtf8 varbinary(max) = dbo.fn_ResumePublicationUtf8(@Raw);
            DECLARE @ValLen varchar(20) = CONVERT(varchar(20), DATALENGTH(@ValUtf8));
            SET @Bytes = @Bytes
                + CONVERT(varbinary(1), 0x53)
                + CONVERT(varbinary(max), @ValLen COLLATE Latin1_General_BIN)
                + CONVERT(varbinary(1), 0x3A)
                + @ValUtf8;
        END;
        SET @Sort = @Sort + 1;
    END;

    SET @Digest = LOWER(CONVERT(char(64), HASHBYTES(''SHA2_256'', @Bytes), 2));
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationLockOwnerInternal
    @ProfileId bigint
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF NOT EXISTS (SELECT 1 FROM dbo.resume_sharing_state WITH (UPDLOCK, HOLDLOCK) WHERE owner_profile_id = @ProfileId)
        INSERT dbo.resume_sharing_state (owner_profile_id) VALUES (@ProfileId);
    SELECT sharing_enabled, sharing_epoch, publication_revision, current_revision, public_slug
      FROM dbo.resume_sharing_state WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId;
    SELECT entry_key
      FROM dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId
     ORDER BY entry_key;
    IF OBJECT_ID(N''dbo.resume_drafts'', N''U'') IS NOT NULL
        SELECT TOP (1) draft_version
          FROM dbo.resume_drafts WITH (UPDLOCK, HOLDLOCK)
         WHERE owner_profile_id = @ProfileId
         ORDER BY draft_version DESC;
    SELECT publication_revision
      FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId
     ORDER BY publication_revision;
    SELECT request_id
      FROM dbo.resume_publication_receipts WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId
     ORDER BY request_id;
    IF OBJECT_ID(N''dbo.resume_media_placements'', N''U'') IS NOT NULL
        SELECT slot
          FROM dbo.resume_media_placements WITH (UPDLOCK, HOLDLOCK)
         WHERE owner_profile_id = @ProfileId
         ORDER BY slot;
    IF OBJECT_ID(N''dbo.resume_catalog_assets'', N''U'') IS NOT NULL
        SELECT asset_id, asset_version
          FROM dbo.resume_catalog_assets WITH (UPDLOCK, HOLDLOCK)
         ORDER BY asset_id, asset_version;
    IF OBJECT_ID(N''dbo.resume_catalog_command_receipts'', N''U'') IS NOT NULL
        SELECT request_id
          FROM dbo.resume_catalog_command_receipts WITH (UPDLOCK, HOLDLOCK)
         ORDER BY request_id;
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyCanonicalInternal
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
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationRefreshProjectionInternal
    @ProfileId bigint,
    @Revision int,
    @Digest char(64),
    @Display nvarchar(max),
    @VisitorAi nvarchar(max),
    @Evidence nvarchar(max),
    @Media nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET @Display = ISNULL(@Display, N''{}'');
    SET @VisitorAi = ISNULL(@VisitorAi, N''{}'');
    SET @Evidence = ISNULL(@Evidence, N''{}'');
    SET @Media = ISNULL(@Media, N''{}'');
    INSERT dbo.resume_publication_revisions
        (owner_profile_id, publication_revision, reviewed_digest, display_json, visitor_ai_json, evidence_json, media_json)
    VALUES (@ProfileId, @Revision, @Digest, @Display, @VisitorAi, @Evidence, @Media);
    UPDATE dbo.resume_sharing_state
       SET publication_revision = @Revision,
           current_revision = @Revision,
           updated_at_utc = SYSUTCDATETIME()
     WHERE owner_profile_id = @ProfileId;
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationBuildManifestsInternal
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

    DECLARE @EntryKey uniqueidentifier;
    DECLARE @CanonicalType nvarchar(40);
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
        DECLARE @ExpectedContent int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, CONCAT(N''$.expected_by_entry."'', CONVERT(nvarchar(36), @EntryKey), N''".content_version'')));
        DECLARE @ExpectedAccess int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, CONCAT(N''$.expected_by_entry."'', CONVERT(nvarchar(36), @EntryKey), N''".access_revision'')));
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
                COALESCE(chapter.approved_wording, chapter.summary) AS summary,
                CONVERT(nvarchar(40), chapter.start_date, 23) AS start_date,
                CONVERT(nvarchar(40), chapter.end_date, 23) AS end_date,
                chapter.date_precision,
                exp.employment_type,
                exp.current_role,
                chapter.title,
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
                COALESCE(chapter.approved_wording, ach.approved_wording, ach.original_member_wording) AS wording,
                ach.metric_value,
                ach.metric_label,
                CONVERT(bit, NULL) AS accomplishment_to_achievement,
                parent.canonical_type AS parent_canonical_type
            FROM dbo.entry_policy_records AS policy
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
        IF @CanonicalType = N''education'' AND JSON_VALUE(@Fields, ''$.institution_name'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''credential'' AND JSON_VALUE(@Fields, ''$.credential_name'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''skill'' AND JSON_VALUE(@Fields, ''$.name'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''achievement'' AND JSON_VALUE(@Fields, ''$.wording'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;

        EXEC dbo.usp_ResumePublicationEncodeSourceInternal
            @FieldsJson = @Fields, @Bytes = @Bytes OUTPUT, @Digest = @Digest OUTPUT;

        DECLARE @EvidenceKey nvarchar(120) = CONCAT(N''evidence:'', CONVERT(nvarchar(36), @EntryKey), N'':'', CONVERT(nvarchar(20), @Revision));
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
            SET @Display = JSON_MODIFY(@Display, CONCAT(N''$."'', CONVERT(nvarchar(36), @EntryKey), N''"''),
                JSON_QUERY(CONCAT(N''{"wording":'', @Wording, N'',"evidence_sha256":"'', @Digest, N''","canonical_token":"'', CONVERT(nvarchar(100), @ContentVersion), N''"}'')));
        IF @VisitorAiFlag = 1
            SET @VisitorAi = JSON_MODIFY(@VisitorAi, CONCAT(N''$."'', CONVERT(nvarchar(36), @EntryKey), N''"''),
                JSON_QUERY(CONCAT(N''{"wording":'', @Wording, N'',"evidence_sha256":"'', @Digest, N''","canonical_token":"'', CONVERT(nvarchar(100), @ContentVersion), N''"}'')));
        SET @Evidence = JSON_MODIFY(@Evidence, CONCAT(N''$."'', CONVERT(nvarchar(36), @EntryKey), N''"''),
            JSON_QUERY(CONCAT(N''{"content_sha256":"'', @Digest, N''","codec":"resume-canonical-source.v1"}'')));

        FETCH NEXT FROM entry_cursor INTO @EntryKey, @CanonicalType, @ContentVersion, @AccessRevision,
            @ResumeDisplay, @VisitorAiFlag, @CanonicalKey;
    END;
    CLOSE entry_cursor;
    DEALLOCATE entry_cursor;
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationGuardLegacyMutator
    @ProfileId bigint,
    @Mutator nvarchar(40),
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @Sharing bit, @Revision int, @Media nvarchar(max);
    SELECT @Sharing = sharing_enabled, @Revision = current_revision
      FROM dbo.resume_sharing_state WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId;
    IF @Sharing IS NULL OR @Sharing = 0 OR @Revision IS NULL
        RETURN;

    IF @Mutator = N''draft''
       AND (
            TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.resume_display'')) = 1
         OR TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.visitor_ai'')) = 1
         OR JSON_VALUE(@CommandJson, ''$.type'') IN (N''publish'', N''correct'', N''change_permissions'')
       )
        THROW 54050, ''PUBLICATION_COMMAND_REQUIRED'', 1;

    IF @Mutator = N''media'' AND JSON_VALUE(@CommandJson, ''$.command'') = N''keep_words_only''
    BEGIN
        SELECT @Media = media_json
          FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
         WHERE owner_profile_id = @ProfileId AND publication_revision = @Revision;
        DECLARE @Slot nvarchar(40) = JSON_VALUE(@CommandJson, ''$.slot'');
        DECLARE @SlotActive bit = TRY_CONVERT(bit, JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".active'')));
        IF @Slot IS NOT NULL AND @SlotActive = 1
            THROW 54051, ''PUBLICATION_MEDIA_RESTRICT_REQUIRED'', 1;
    END;

    IF @Mutator = N''intake''
       AND (
            TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.resume_display'')) = 1
         OR TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.visitor_ai'')) = 1
         OR TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.permissions.resume_display'')) = 1
         OR TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.permissions.visitor_ai'')) = 1
       )
        THROW 54052, ''PUBLICATION_COMMAND_REQUIRED'', 1;

    IF @Mutator = N''living_resume''
    BEGIN
        DECLARE @Op nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
        DECLARE @RecordKey nvarchar(36) = JSON_VALUE(@CommandJson, ''$.record_key'');
        IF @Op LIKE N''update_%'' OR @Op LIKE N''remove_%''
        BEGIN
            DECLARE @Display nvarchar(max), @Visitor nvarchar(max);
            SELECT @Display = display_json, @Visitor = visitor_ai_json
              FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
             WHERE owner_profile_id = @ProfileId AND publication_revision = @Revision;
            IF JSON_QUERY(@Display, CONCAT(N''$."'', @RecordKey, N''"'')) IS NOT NULL
               OR JSON_QUERY(@Visitor, CONCAT(N''$."'', @RecordKey, N''"'')) IS NOT NULL
                THROW 54053, ''PUBLICATION_CORRECTION_REQUIRED'', 1;
        END;
    END;
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyAfterPolicyInternal
    @ProfileId bigint,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @Sharing bit, @Revision int, @Type nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
    SELECT @Sharing = sharing_enabled, @Revision = current_revision
      FROM dbo.resume_sharing_state WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId;
    IF @Sharing IS NULL OR @Revision IS NULL
        RETURN;
    IF @Type NOT IN (N''create'', N''edit'', N''recategorize'', N''change_permissions'',
                     N''delete'', N''restore'', N''permanently_delete'', N''resolve_match'')
        RETURN;

    DECLARE @Display nvarchar(max), @Visitor nvarchar(max), @Evidence nvarchar(max);
    DECLARE @NewRevision int = @Revision + CASE WHEN @Type = N''create'' THEN 0 ELSE 1 END;
    IF @Type = N''create''
        RETURN;
    DECLARE @Digest char(64) = LOWER(CONVERT(char(64), HASHBYTES(''SHA2_256'', dbo.fn_ResumePublicationUtf8(@CommandJson)), 2));
    EXEC dbo.usp_ResumePublicationBuildManifestsInternal
        @ProfileId = @ProfileId, @Revision = @NewRevision, @CommandJson = @CommandJson,
        @Display = @Display OUTPUT, @VisitorAi = @Visitor OUTPUT, @Evidence = @Evidence OUTPUT;
    DECLARE @Media nvarchar(max) = N''{}'';
    SELECT @Media = media_json
      FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId AND publication_revision = @Revision;
    EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
        @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Digest,
        @Display = @Display, @VisitorAi = @Visitor, @Evidence = @Evidence, @Media = @Media;
    IF @Type = N''restore''
        UPDATE dbo.resume_sharing_state
           SET updated_at_utc = SYSUTCDATETIME()
         WHERE owner_profile_id = @ProfileId;
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_CommitResumePublicationCommandForOwner
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
            @ProfileId = @ProfileId, @Revision = @NewRevision, @CommandJson = @CommandJson,
            @Display = @Display OUTPUT, @VisitorAi = @Visitor OUTPUT, @Evidence = @Evidence OUTPUT;
        SET @Media = ISNULL(JSON_QUERY(@CommandJson, ''$.media''), N''{}'');
        IF ISJSON(@Media) <> 1 SET @Media = N''{}'';
        EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
            @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Reviewed,
            @Display = @Display, @VisitorAi = @Visitor,
            @Evidence = @Evidence, @Media = @Media;
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
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_GetResumePublicationForOwner
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
           r.media_json, r.reviewed_digest
      FROM dbo.resume_sharing_state AS s
      LEFT JOIN dbo.resume_publication_revisions AS r
        ON r.owner_profile_id = s.owner_profile_id
       AND r.publication_revision = s.current_revision
     WHERE s.owner_profile_id = @ProfileId;
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_GetResumePublicationReceiptForOwner
    @UserKey nvarchar(300),
    @RequestId uniqueidentifier
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    SELECT receipt.request_id, receipt.request_digest, receipt.command_type, receipt.outcome,
           state.publication_revision
      FROM dbo.resume_publication_receipts AS receipt
      JOIN dbo.resume_sharing_state AS state ON state.owner_profile_id = receipt.owner_profile_id
     WHERE receipt.owner_profile_id = @ProfileId AND receipt.request_id = @RequestId;
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_GetPublicResumePublicationBySlug
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
    SELECT r.publication_revision, r.reviewed_digest, r.display_json, r.media_json
      FROM dbo.resume_publication_revisions AS r
     WHERE r.owner_profile_id = @ProfileId AND r.publication_revision = @Revision;
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_GetResumePublicationMediaAuthorization
    @ProfileSlug nvarchar(100),
    @Slot nvarchar(40),
    @PublicationRevision int = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint, @Revision int, @Sharing bit, @Media nvarchar(max);
    SELECT @ProfileId = owner_profile_id, @Revision = current_revision, @Sharing = sharing_enabled
      FROM dbo.resume_sharing_state
     WHERE public_slug = @ProfileSlug;
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
    DECLARE @AssetVersion int = TRY_CONVERT(int, JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".asset_version'')));
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
    SELECT authorized = CONVERT(bit, 1), slot = @Slot, rechecked = CONVERT(bit, 1),
           content_sha256 = @Digest, source_kind = @Kind, source_key = @SourceKey,
           asset_version = @AssetVersion, publication_revision = @Revision;
END;
';

    -- Preserve original entry-policy vocabulary: rename once, wrap with the
    -- same nvarchar(300) owner key, then apply publication follow-up in the
    -- same transaction. Core keeps create/edit/recategorize/permanently_delete/resolve_match.
    IF OBJECT_ID(N'dbo.usp_CommitEntryPolicyCommandForOwnerCore', N'P') IS NULL
       AND OBJECT_ID(N'dbo.usp_CommitEntryPolicyCommandForOwner', N'P') IS NOT NULL
        EXEC sys.sp_rename N'dbo.usp_CommitEntryPolicyCommandForOwner', N'usp_CommitEntryPolicyCommandForOwnerCore';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_CommitEntryPolicyCommandForOwner
    @UserKey nvarchar(300),
    @RequestId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    IF @@TRANCOUNT <> 0
        THROW 54040, ''Ambient transactions are not permitted.'', 1;
    DECLARE @Type nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
    IF @Type IN (N''edit'', N''change_permissions'')
    BEGIN
        EXEC dbo.usp_CommitResumePublicationCommandForOwner
            @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
        RETURN;
    END;
    BEGIN TRANSACTION;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 52102, ''ENTRY_POLICY_NOT_FOUND'', 1;
    EXEC dbo.usp_ResumePublicationLockOwnerInternal @ProfileId = @ProfileId;
    CREATE TABLE #CoreOutcome (
        committed bit NOT NULL,
        replayed bit NOT NULL,
        outcome nvarchar(40) NULL,
        request_digest char(64) NULL
    );
    INSERT #CoreOutcome (committed, replayed, outcome, request_digest)
    EXEC dbo.usp_CommitEntryPolicyCommandForOwnerCore
        @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
    DECLARE @CoreReplayed bit = 0;
    SELECT TOP (1) @CoreReplayed = replayed FROM #CoreOutcome;
    IF @CoreReplayed = 1
    BEGIN
        SELECT committed, replayed, outcome, request_digest FROM #CoreOutcome;
        COMMIT;
        RETURN;
    END
    EXEC dbo.usp_ResumePublicationApplyAfterPolicyInternal
        @ProfileId = @ProfileId, @CommandJson = @CommandJson;
    SELECT committed, replayed, outcome, request_digest FROM #CoreOutcome;
    COMMIT;
END;
';

    IF OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwnerCore', N'P') IS NULL
       AND OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwner', N'P') IS NOT NULL
        EXEC sys.sp_rename N'dbo.usp_CommitResumeDraftCommandForOwner', N'usp_CommitResumeDraftCommandForOwnerCore';

    IF OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwnerCore', N'P') IS NOT NULL
    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeDraftCommandForOwner
    @UserKey nvarchar(300),
    @RequestId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    DECLARE @OwnTransaction bit = 0;
    IF @@TRANCOUNT = 0
    BEGIN
        BEGIN TRANSACTION;
        SET @OwnTransaction = 1;
    END;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 52202, ''RESUME_DRAFT_NOT_FOUND'', 1;
    EXEC dbo.usp_ResumePublicationGuardLegacyMutator
        @ProfileId = @ProfileId, @Mutator = N''draft'', @CommandJson = @CommandJson;
    EXEC dbo.usp_CommitResumeDraftCommandForOwnerCore
        @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
    IF @OwnTransaction = 1 COMMIT TRANSACTION;
END;
';

    IF OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwnerCore', N'P') IS NULL
       AND OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwner', N'P') IS NOT NULL
        EXEC sys.sp_rename N'dbo.usp_CommitResumeMediaCommandForOwner', N'usp_CommitResumeMediaCommandForOwnerCore';

    IF OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwnerCore', N'P') IS NOT NULL
    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeMediaCommandForOwner
    @UserKey nvarchar(300),
    @RequestId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    DECLARE @OwnTransaction bit = 0;
    IF @@TRANCOUNT = 0
    BEGIN
        BEGIN TRANSACTION;
        SET @OwnTransaction = 1;
    END;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 52302, ''RESUME_MEDIA_NOT_FOUND'', 1;
    EXEC dbo.usp_ResumePublicationGuardLegacyMutator
        @ProfileId = @ProfileId, @Mutator = N''media'', @CommandJson = @CommandJson;
    EXEC dbo.usp_CommitResumeMediaCommandForOwnerCore
        @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
    IF @OwnTransaction = 1 COMMIT TRANSACTION;
END;
';

    IF OBJECT_ID(N'dbo.usp_CommitResumeIntakeCommandForOwnerCore', N'P') IS NULL
       AND OBJECT_ID(N'dbo.usp_CommitResumeIntakeCommandForOwner', N'P') IS NOT NULL
        EXEC sys.sp_rename N'dbo.usp_CommitResumeIntakeCommandForOwner', N'usp_CommitResumeIntakeCommandForOwnerCore';

    IF OBJECT_ID(N'dbo.usp_CommitResumeIntakeCommandForOwnerCore', N'P') IS NOT NULL
    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeIntakeCommandForOwner
    @UserKey nvarchar(300),
    @RequestId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    DECLARE @OwnTransaction bit = 0;
    IF @@TRANCOUNT = 0
    BEGIN
        BEGIN TRANSACTION;
        SET @OwnTransaction = 1;
    END;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 52310, ''RESUME_INTAKE_NOT_FOUND'', 1;
    EXEC dbo.usp_ResumePublicationGuardLegacyMutator
        @ProfileId = @ProfileId, @Mutator = N''intake'', @CommandJson = @CommandJson;
    EXEC dbo.usp_CommitResumeIntakeCommandForOwnerCore
        @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
    IF @OwnTransaction = 1 COMMIT TRANSACTION;
END;
';

    IF OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwnerCore', N'P') IS NULL
       AND OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwner', N'P') IS NOT NULL
        EXEC sys.sp_rename N'dbo.usp_CommitLivingResumeCommandForOwner', N'usp_CommitLivingResumeCommandForOwnerCore';

    IF OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwnerCore', N'P') IS NOT NULL
    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_CommitLivingResumeCommandForOwner
    @UserKey nvarchar(300),
    @CommandId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    DECLARE @OwnTransaction bit = 0;
    IF @@TRANCOUNT = 0
    BEGIN
        BEGIN TRANSACTION;
        SET @OwnTransaction = 1;
    END;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 52002, ''RESUME_EDITOR_NOT_FOUND'', 1;
    EXEC dbo.usp_ResumePublicationGuardLegacyMutator
        @ProfileId = @ProfileId, @Mutator = N''living_resume'', @CommandJson = @CommandJson;
    EXEC dbo.usp_CommitLivingResumeCommandForOwnerCore
        @UserKey = @UserKey, @CommandId = @CommandId, @CommandJson = @CommandJson;
    IF @OwnTransaction = 1 COMMIT TRANSACTION;
END;
';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ListResumePublicationPolicyForOwner
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
           (
               SELECT exp.role_title, exp.employer_name, chapter.location_text,
                      COALESCE(chapter.approved_wording, chapter.summary) AS summary,
                      CONVERT(nvarchar(40), chapter.start_date, 23) AS start_date,
                      CONVERT(nvarchar(40), chapter.end_date, 23) AS end_date,
                      chapter.date_precision, exp.employment_type, exp.current_role,
                      chapter.title, edu.institution_name, edu.degree_name,
                      edu.field_of_study, edu.education_status, edu.grade_text,
                      cred.credential_name, cred.issuer_name, cred.credential_identifier,
                      CONVERT(nvarchar(40), cred.issue_date, 23) AS issue_date,
                      CONVERT(nvarchar(40), cred.expiration_date, 23) AS expiration_date,
                      skill.skill_name AS name, skill.skill_summary,
                      COALESCE(chapter.approved_wording, ach.approved_wording, ach.original_member_wording) AS wording,
                      ach.metric_value, ach.metric_label
                 FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
           ) AS values_json
      FROM dbo.entry_policy_records AS policy
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
END;
';

    -- My Data's existing owner-scoped list/get ports must return the same
    -- current canonical values that the publication review port reads.
    IF OBJECT_ID(N'dbo.usp_ListEntryPolicyEntriesForOwnerCore', N'P') IS NULL
       AND OBJECT_ID(N'dbo.usp_ListEntryPolicyEntriesForOwner', N'P') IS NOT NULL
        EXEC sys.sp_rename N'dbo.usp_ListEntryPolicyEntriesForOwner', N'usp_ListEntryPolicyEntriesForOwnerCore';
    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ListEntryPolicyEntriesForOwner
    @UserKey nvarchar(300)
AS
BEGIN
    SET NOCOUNT ON;
    EXEC dbo.usp_ListResumePublicationPolicyForOwner @UserKey = @UserKey;
END;
';

    IF OBJECT_ID(N'dbo.usp_GetEntryPolicyEntryForOwnerCore', N'P') IS NULL
       AND OBJECT_ID(N'dbo.usp_GetEntryPolicyEntryForOwner', N'P') IS NOT NULL
        EXEC sys.sp_rename N'dbo.usp_GetEntryPolicyEntryForOwner', N'usp_GetEntryPolicyEntryForOwnerCore';
    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_GetEntryPolicyEntryForOwner
    @UserKey nvarchar(300),
    @EntryKey uniqueidentifier
AS
BEGIN
    SET NOCOUNT ON;
    CREATE TABLE #CurrentEntries (
        entry_key uniqueidentifier, canonical_type nvarchar(40), canonical_key uniqueidentifier,
        category nvarchar(40), parent_entry_key uniqueidentifier, content_version int,
        access_revision int, resume_display bit, visitor_ai bit,
        private_assistance_excluded bit, lifecycle nvarchar(30),
        recover_until_utc datetime2(7), values_json nvarchar(max)
    );
    INSERT #CurrentEntries
    EXEC dbo.usp_ListResumePublicationPolicyForOwner @UserKey = @UserKey;
    SELECT entry_key, canonical_type, canonical_key, category, parent_entry_key,
           content_version, access_revision, resume_display, visitor_ai,
           private_assistance_excluded, lifecycle, recover_until_utc, values_json
      FROM #CurrentEntries WHERE entry_key = @EntryKey;
END;
';

    DENY INSERT, UPDATE, DELETE ON dbo.resume_sharing_state TO PUBLIC;
    DENY INSERT, UPDATE, DELETE ON dbo.resume_publication_revisions TO PUBLIC;
    DENY INSERT, UPDATE, DELETE ON dbo.resume_publication_evidence TO PUBLIC;
    DENY INSERT, UPDATE, DELETE ON dbo.resume_publication_receipts TO PUBLIC;
    DENY INSERT, UPDATE, DELETE ON dbo.resume_publication_outbox TO PUBLIC;
    DENY INSERT, UPDATE, DELETE ON dbo.resume_publication_core_execute_permissions TO PUBLIC;
    DENY EXECUTE ON dbo.usp_ResumePublicationApplyCanonicalInternal TO PUBLIC;
    DENY EXECUTE ON dbo.usp_ResumePublicationRefreshProjectionInternal TO PUBLIC;
    DENY EXECUTE ON dbo.usp_ResumePublicationEncodeSourceInternal TO PUBLIC;
    DENY EXECUTE ON dbo.usp_ResumePublicationLockOwnerInternal TO PUBLIC;
    DENY EXECUTE ON dbo.usp_ResumePublicationBuildManifestsInternal TO PUBLIC;
    DENY EXECUTE ON dbo.usp_ResumePublicationGuardLegacyMutator TO PUBLIC;
    DENY EXECUTE ON dbo.usp_ResumePublicationApplyAfterPolicyInternal TO PUBLIC;
    IF OBJECT_ID(N'dbo.usp_CommitEntryPolicyCommandForOwnerCore', N'P') IS NOT NULL
        DENY EXECUTE ON dbo.usp_CommitEntryPolicyCommandForOwnerCore TO PUBLIC;
    IF OBJECT_ID(N'dbo.usp_ListEntryPolicyEntriesForOwnerCore', N'P') IS NOT NULL
        DENY EXECUTE ON dbo.usp_ListEntryPolicyEntriesForOwnerCore TO PUBLIC;
    IF OBJECT_ID(N'dbo.usp_GetEntryPolicyEntryForOwnerCore', N'P') IS NOT NULL
        DENY EXECUTE ON dbo.usp_GetEntryPolicyEntryForOwnerCore TO PUBLIC;
    IF OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwnerCore', N'P') IS NOT NULL
        DENY EXECUTE ON dbo.usp_CommitResumeDraftCommandForOwnerCore TO PUBLIC;
    IF OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwnerCore', N'P') IS NOT NULL
        DENY EXECUTE ON dbo.usp_CommitResumeMediaCommandForOwnerCore TO PUBLIC;
    IF OBJECT_ID(N'dbo.usp_CommitResumeIntakeCommandForOwnerCore', N'P') IS NOT NULL
        DENY EXECUTE ON dbo.usp_CommitResumeIntakeCommandForOwnerCore TO PUBLIC;
    IF OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwnerCore', N'P') IS NOT NULL
        DENY EXECUTE ON dbo.usp_CommitLivingResumeCommandForOwnerCore TO PUBLIC;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-PUBLICATION-001')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES
            (N'PS-RESUME-PUBLICATION-001',
             N'Proposed complete Resume publication consistency boundary',
             N'PeerSlate MVP1 Package E');
        EXEC dbo.usp_AppendAuditEvent
            @ActionType=N'schema.migration.applied', @EntityType=N'database_migration',
            @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-RESUME-PUBLICATION-001"}';
    END;

    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;
