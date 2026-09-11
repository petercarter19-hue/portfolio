/*
PS-ENTRY-POLICY-001 — proposed entry metadata, independent permissions,
lifecycle, project commands, and standalone achievements.

PROPOSED ONLY. This file has not been applied to any database. Its registry
gate is null. Disposable SQL Server execution, concurrency, rollback, and
driver serialization proof remain required before any separately authorized
schema application.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-EDIT-002')
        THROW 52100, 'PS-RESUME-EDIT-002 must be applied first.', 1;

    IF COL_LENGTH(N'dbo.career_achievements', N'chapter_id') IS NOT NULL
       AND EXISTS (
            SELECT 1
            FROM sys.columns
            WHERE object_id = OBJECT_ID(N'dbo.career_achievements')
              AND name = N'chapter_id'
              AND is_nullable = 0
       )
    BEGIN
        ALTER TABLE dbo.career_achievements
            ALTER COLUMN chapter_id bigint NULL;
    END;

    IF OBJECT_ID(N'dbo.entry_policy_records', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.entry_policy_records
        (
            entry_policy_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            entry_key uniqueidentifier NOT NULL,
            canonical_type nvarchar(40) NOT NULL,
            canonical_key uniqueidentifier NOT NULL,
            category nvarchar(40) NOT NULL,
            parent_entry_key uniqueidentifier NULL,
            content_version int NOT NULL CONSTRAINT DF_entry_policy_records_content DEFAULT 1,
            access_revision int NOT NULL CONSTRAINT DF_entry_policy_records_access DEFAULT 1,
            resume_display bit NOT NULL CONSTRAINT DF_entry_policy_records_display DEFAULT 0,
            visitor_ai bit NOT NULL CONSTRAINT DF_entry_policy_records_visitor DEFAULT 0,
            private_assistance_excluded bit NOT NULL CONSTRAINT DF_entry_policy_records_exclusion DEFAULT 0,
            lifecycle nvarchar(30) NOT NULL CONSTRAINT DF_entry_policy_records_lifecycle DEFAULT N'active',
            deleted_at_utc datetime2(7) NULL,
            recover_until_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_entry_policy_records_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_entry_policy_records_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_entry_policy_records PRIMARY KEY (entry_policy_id),
            CONSTRAINT UQ_entry_policy_records_owner_key UNIQUE (owner_profile_id, entry_key),
            CONSTRAINT FK_entry_policy_records_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_entry_policy_records_type CHECK
                (canonical_type IN (N'role', N'education', N'credential', N'skill', N'achievement', N'project', N'knowledge')),
            CONSTRAINT CK_entry_policy_records_category CHECK
                (category IN (N'experience', N'education', N'credential', N'skill', N'achievement', N'project', N'personal')),
            CONSTRAINT CK_entry_policy_records_lifecycle CHECK
                (lifecycle IN (N'active', N'deleted', N'permanently_deleted')),
            CONSTRAINT CK_entry_policy_records_versions CHECK
                (content_version >= 1 AND access_revision >= 1),
            CONSTRAINT CK_entry_policy_records_recovery CHECK
                ((lifecycle = N'deleted' AND deleted_at_utc IS NOT NULL AND recover_until_utc IS NOT NULL)
                 OR (lifecycle <> N'deleted' AND deleted_at_utc IS NULL AND recover_until_utc IS NULL))
        );
        CREATE INDEX IX_entry_policy_records_owner_lifecycle
            ON dbo.entry_policy_records(owner_profile_id, lifecycle, category);
    END;

    IF OBJECT_ID(N'dbo.entry_policy_command_receipts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.entry_policy_command_receipts
        (
            command_receipt_id bigint IDENTITY(1,1) NOT NULL,
            owner_profile_id bigint NOT NULL,
            request_id uniqueidentifier NOT NULL,
            request_digest char(64) NOT NULL,
            command_type nvarchar(40) NOT NULL,
            outcome nvarchar(40) NOT NULL,
            committed_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_entry_policy_command_receipts_committed DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_entry_policy_command_receipts PRIMARY KEY (command_receipt_id),
            CONSTRAINT UQ_entry_policy_command_receipts_owner_request
                UNIQUE (owner_profile_id, request_id),
            CONSTRAINT FK_entry_policy_command_receipts_owner
                FOREIGN KEY (owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_entry_policy_command_receipts_digest
                CHECK (request_digest NOT LIKE '%[^0-9a-f]%' AND LEN(request_digest) = 64),
            CONSTRAINT CK_entry_policy_command_receipts_type CHECK
                (command_type IN
                    (N'create', N'edit', N'recategorize', N'change_permissions',
                     N'delete', N'restore', N'permanently_delete', N'resolve_match')),
            CONSTRAINT CK_entry_policy_command_receipts_outcome CHECK
                (outcome IN
                    (N'created', N'updated', N'recategorized', N'permissions_changed',
                     N'deleted', N'restored', N'permanently_deleted', N'match_resolved'))
        );
    END;

    EXEC(N'
        CREATE OR ALTER TRIGGER dbo.trg_entry_policy_command_receipts_immutable
        ON dbo.entry_policy_command_receipts
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            THROW 52101, ''Entry policy command receipts are immutable.'', 1;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetEntryPolicyEntryForOwner
            @UserKey nvarchar(300),
            @EntryKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52102, ''ENTRY_POLICY_NOT_FOUND'', 1;

            SELECT
                record.entry_key,
                record.canonical_type,
                record.canonical_key,
                record.category,
                record.parent_entry_key,
                record.content_version,
                record.access_revision,
                record.resume_display,
                record.visitor_ai,
                record.private_assistance_excluded,
                record.lifecycle,
                record.recover_until_utc
            FROM dbo.entry_policy_records AS record WITH (UPDLOCK, HOLDLOCK)
            WHERE record.owner_profile_id = @ProfileId
              AND record.entry_key = @EntryKey
              AND record.lifecycle <> N''permanently_deleted'';
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_ListEntryPolicyEntriesForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52102, ''ENTRY_POLICY_NOT_FOUND'', 1;

            SELECT
                record.entry_key,
                record.canonical_type,
                record.canonical_key,
                record.category,
                record.parent_entry_key,
                record.content_version,
                record.access_revision,
                record.resume_display,
                record.visitor_ai,
                record.private_assistance_excluded,
                record.lifecycle,
                record.recover_until_utc
            FROM dbo.entry_policy_records AS record WITH (UPDLOCK, HOLDLOCK)
            WHERE record.owner_profile_id = @ProfileId
              AND record.lifecycle <> N''permanently_deleted''
            ORDER BY record.category, record.entry_key;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_CommitEntryPolicyCommandForOwner
            @UserKey nvarchar(300),
            @RequestId uniqueidentifier,
            @CommandJson nvarchar(max)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52102, ''ENTRY_POLICY_NOT_FOUND'', 1;

            DECLARE @Digest char(64) = CONVERT(char(64), HASHBYTES(''SHA2_256'', CONVERT(varbinary(max), @CommandJson)), 2);
            DECLARE @ExistingDigest char(64);
            DECLARE @ExistingOutcome nvarchar(40);

            SELECT @ExistingDigest = receipt.request_digest,
                   @ExistingOutcome = receipt.outcome
            FROM dbo.entry_policy_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
            WHERE receipt.owner_profile_id = @ProfileId
              AND receipt.request_id = @RequestId;

            IF @ExistingDigest IS NOT NULL
            BEGIN
                IF @ExistingDigest <> LOWER(@Digest)
                    THROW 52103, ''ENTRY_POLICY_IDEMPOTENCY_CONFLICT'', 1;
                SELECT CONVERT(bit, 1) AS committed,
                       CONVERT(bit, 1) AS replayed,
                       @ExistingOutcome AS outcome,
                       LOWER(@ExistingDigest) AS request_digest;
                RETURN;
            END;

            DECLARE @CommandType nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
            IF @CommandType NOT IN
                (N''create'', N''edit'', N''recategorize'', N''change_permissions'',
                 N''delete'', N''restore'', N''permanently_delete'', N''resolve_match'')
                THROW 52104, ''ENTRY_POLICY_UNKNOWN_COMMAND'', 1;

            DECLARE @EntryKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.entry_key''));
            DECLARE @ParentKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.parent_key''));
            DECLARE @CanonicalType nvarchar(40) = JSON_VALUE(@CommandJson, ''$.canonical_type'');
            DECLARE @Category nvarchar(40) = JSON_VALUE(@CommandJson, ''$.category'');
            DECLARE @ExpectedContent int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_content_version''));
            DECLARE @ExpectedAccess int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_access_revision''));
            DECLARE @Outcome nvarchar(40);
            DECLARE @Now datetime2(7) = SYSUTCDATETIME();

            IF @CommandType = N''create''
            BEGIN
                IF @CanonicalType NOT IN (N''role'', N''education'', N''credential'', N''skill'', N''achievement'', N''project'', N''knowledge'')
                    THROW 52104, ''ENTRY_POLICY_UNKNOWN_COMMAND'', 1;
                IF EXISTS (
                    SELECT 1 FROM dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
                    WHERE owner_profile_id = @ProfileId AND entry_key = @EntryKey
                )
                    THROW 52105, ''ENTRY_POLICY_CHANGED'', 1;
                IF @ParentKey IS NOT NULL
                   AND NOT EXISTS (
                        SELECT 1 FROM dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
                        WHERE owner_profile_id = @ProfileId
                          AND entry_key = @ParentKey
                          AND lifecycle = N''active''
                          AND canonical_type IN (N''role'', N''education'', N''credential'', N''project'')
                   )
                    THROW 52102, ''ENTRY_POLICY_NOT_FOUND'', 1;

                INSERT dbo.entry_policy_records
                    (owner_profile_id, entry_key, canonical_type, canonical_key, category, parent_entry_key,
                     content_version, access_revision, resume_display, visitor_ai, private_assistance_excluded, lifecycle)
                VALUES
                    (@ProfileId, @EntryKey, @CanonicalType, @EntryKey,
                     COALESCE(@Category, CASE @CanonicalType
                        WHEN N''role'' THEN N''experience''
                        WHEN N''knowledge'' THEN N''personal''
                        ELSE @CanonicalType END),
                     @ParentKey, 1, 1, 0, 0, 0, N''active'');
                SET @Outcome = N''created'';
            END
            ELSE IF @CommandType = N''change_permissions''
            BEGIN
                UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
                SET resume_display = COALESCE(TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.permissions.resume_display'')), resume_display),
                    visitor_ai = COALESCE(TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.permissions.visitor_ai'')), visitor_ai),
                    private_assistance_excluded = COALESCE(TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.permissions.private_assistance_excluded'')), private_assistance_excluded),
                    access_revision = access_revision + 1,
                    updated_at_utc = @Now
                WHERE owner_profile_id = @ProfileId
                  AND entry_key = @EntryKey
                  AND lifecycle = N''active''
                  AND access_revision = @ExpectedAccess;
                IF @@ROWCOUNT <> 1
                    THROW 52105, ''ENTRY_POLICY_CHANGED'', 1;
                SET @Outcome = N''permissions_changed'';
            END
            ELSE IF @CommandType = N''delete''
            BEGIN
                DECLARE @ActualChildCount int = (
                    SELECT COUNT(*)
                    FROM dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
                    WHERE owner_profile_id = @ProfileId
                      AND parent_entry_key = @EntryKey
                      AND lifecycle <> N''permanently_deleted''
                );
                DECLARE @ExpectedChildCount int = (
                    SELECT COUNT(*)
                    FROM OPENJSON(ISNULL(JSON_QUERY(@CommandJson, ''$.dependent_keys''), N''[]''))
                );
                IF @ExpectedChildCount <> @ActualChildCount
                    THROW 52106, ''ENTRY_POLICY_SCOPE_CHANGED'', 1;

                UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
                SET lifecycle = N''deleted'',
                    deleted_at_utc = @Now,
                    recover_until_utc = DATEADD(day, 30, @Now),
                    resume_display = 0,
                    visitor_ai = 0,
                    access_revision = access_revision + 1,
                    updated_at_utc = @Now
                WHERE owner_profile_id = @ProfileId
                  AND (entry_key = @EntryKey OR parent_entry_key = @EntryKey)
                  AND lifecycle = N''active''
                  AND (@ExpectedContent IS NULL OR content_version = @ExpectedContent)
                  AND (@ExpectedAccess IS NULL OR access_revision = @ExpectedAccess OR entry_key <> @EntryKey);
                IF @@ROWCOUNT < 1
                    THROW 52105, ''ENTRY_POLICY_CHANGED'', 1;
                SET @Outcome = N''deleted'';
            END
            ELSE IF @CommandType = N''restore''
            BEGIN
                DECLARE @GroupUntil datetime2(7);
                SELECT @GroupUntil = record.recover_until_utc
                FROM dbo.entry_policy_records AS record WITH (UPDLOCK, HOLDLOCK)
                WHERE record.owner_profile_id = @ProfileId
                  AND record.entry_key = @EntryKey
                  AND record.lifecycle = N''deleted''
                  AND record.recover_until_utc > @Now
                  AND record.access_revision = @ExpectedAccess;
                IF @GroupUntil IS NULL
                    THROW 52105, ''ENTRY_POLICY_CHANGED'', 1;

                UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
                SET lifecycle = N''active'',
                    deleted_at_utc = NULL,
                    recover_until_utc = NULL,
                    resume_display = 0,
                    visitor_ai = 0,
                    access_revision = access_revision + 1,
                    updated_at_utc = @Now
                WHERE owner_profile_id = @ProfileId
                  AND lifecycle = N''deleted''
                  AND recover_until_utc = @GroupUntil;
                IF @@ROWCOUNT < 1
                    THROW 52105, ''ENTRY_POLICY_CHANGED'', 1;
                SET @Outcome = N''restored'';
            END
            ELSE IF @CommandType = N''recategorize''
            BEGIN
                IF @Category NOT IN (N''experience'', N''education'', N''credential'', N''skill'', N''achievement'', N''project'', N''personal'')
                    THROW 52104, ''ENTRY_POLICY_UNKNOWN_COMMAND'', 1;
                UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
                SET category = @Category,
                    content_version = content_version + 1,
                    updated_at_utc = @Now
                WHERE owner_profile_id = @ProfileId
                  AND entry_key = @EntryKey
                  AND lifecycle = N''active''
                  AND content_version = @ExpectedContent;
                IF @@ROWCOUNT <> 1
                    THROW 52105, ''ENTRY_POLICY_CHANGED'', 1;
                SET @Outcome = N''recategorized'';
            END
            ELSE IF @CommandType = N''permanently_delete''
            BEGIN
                UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
                SET lifecycle = N''permanently_deleted'',
                    resume_display = 0,
                    visitor_ai = 0,
                    deleted_at_utc = NULL,
                    recover_until_utc = NULL,
                    access_revision = access_revision + 1,
                    updated_at_utc = @Now
                WHERE owner_profile_id = @ProfileId
                  AND lifecycle = N''deleted''
                  AND (entry_key = @EntryKey OR parent_entry_key = @EntryKey)
                  AND (entry_key <> @EntryKey OR access_revision = @ExpectedAccess);
                IF @@ROWCOUNT < 1
                    THROW 52105, ''ENTRY_POLICY_CHANGED'', 1;
                SET @Outcome = N''permanently_deleted'';
            END
            ELSE
            BEGIN
                UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
                SET content_version = content_version + 1,
                    updated_at_utc = @Now
                WHERE owner_profile_id = @ProfileId
                  AND entry_key = @EntryKey
                  AND lifecycle = N''active''
                  AND content_version = @ExpectedContent;
                IF @@ROWCOUNT <> 1
                    THROW 52105, ''ENTRY_POLICY_CHANGED'', 1;
                SET @Outcome = CASE @CommandType
                    WHEN N''resolve_match'' THEN N''match_resolved''
                    ELSE N''updated'' END;
            END;

            INSERT dbo.entry_policy_command_receipts
                (owner_profile_id, request_id, request_digest, command_type, outcome)
            VALUES
                (@ProfileId, @RequestId, LOWER(@Digest), @CommandType, @Outcome);

            SELECT CONVERT(bit, 1) AS committed,
                   CONVERT(bit, 0) AS replayed,
                   @Outcome AS outcome,
                   LOWER(@Digest) AS request_digest;
        END;
    ');

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SweepExpiredEntryPolicyForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52102, ''ENTRY_POLICY_NOT_FOUND'', 1;

            UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
            SET lifecycle = N''permanently_deleted'',
                resume_display = 0,
                visitor_ai = 0,
                deleted_at_utc = NULL,
                recover_until_utc = NULL,
                access_revision = access_revision + 1,
                updated_at_utc = SYSUTCDATETIME()
            WHERE owner_profile_id = @ProfileId
              AND lifecycle = N''deleted''
              AND recover_until_utc <= SYSUTCDATETIME();

            SELECT @@ROWCOUNT AS expired_count;
        END;
    ');

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-ENTRY-POLICY-001')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES
            (N'PS-ENTRY-POLICY-001',
             N'Proposed owner-scoped entry policy metadata, recovery, and closed commands',
             N'PeerSlate MVP1 Package A');
        EXEC dbo.usp_AppendAuditEvent
            @ActionType=N'schema.migration.applied', @EntityType=N'database_migration',
            @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-ENTRY-POLICY-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
