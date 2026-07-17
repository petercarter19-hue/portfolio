SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.user_identities', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1 FROM dbo.user_identities
           WHERE issuer <> N'urn:peerslate:legacy:app-users'
       )
        THROW 51890, 'PS-AUTH-001 contains real external identity mappings; export and review retention before rollback.', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_UpsertAppUserFromAuth
            @AuthProvider nvarchar(100),
            @AuthSubject nvarchar(250),
            @Email nvarchar(250) = NULL,
            @DisplayName nvarchar(150) = NULL,
            @ProfileImageUrl nvarchar(500) = NULL,
            @TimezoneName nvarchar(100) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            DECLARE @UserId int;
            DECLARE @UserKey nvarchar(150);

            IF NULLIF(LTRIM(RTRIM(@AuthProvider)), N'''') IS NULL
                THROW 51891, ''Auth provider is required.'', 1;
            IF NULLIF(LTRIM(RTRIM(@AuthSubject)), N'''') IS NULL
                THROW 51892, ''Auth subject is required.'', 1;

            SELECT @UserId = id
            FROM dbo.app_users
            WHERE auth_provider = @AuthProvider AND auth_subject = @AuthSubject;

            IF @UserId IS NULL
            BEGIN
                SET @UserKey = CONCAT(@AuthProvider, N'':'', @AuthSubject);
                INSERT dbo.app_users
                (
                    user_key, display_name, email, auth_provider, auth_subject,
                    profile_image_url, timezone_name, user_role, active,
                    created_at, last_seen_at, updated_at
                )
                VALUES
                (
                    @UserKey, COALESCE(@DisplayName, @Email, @UserKey), @Email,
                    @AuthProvider, @AuthSubject, @ProfileImageUrl, @TimezoneName,
                    N''user'', 1, SYSUTCDATETIME(), SYSUTCDATETIME(), SYSUTCDATETIME()
                );
                SET @UserId = CONVERT(int, SCOPE_IDENTITY());
            END
            ELSE
                UPDATE dbo.app_users
                SET display_name = COALESCE(@DisplayName, display_name),
                    email = COALESCE(@Email, email),
                    profile_image_url = COALESCE(@ProfileImageUrl, profile_image_url),
                    timezone_name = COALESCE(@TimezoneName, timezone_name),
                    last_seen_at = SYSUTCDATETIME(),
                    updated_at = SYSUTCDATETIME()
                WHERE id = @UserId;

            SELECT id AS user_id, user_key, display_name, email,
                   auth_provider, auth_subject, profile_image_url,
                   timezone_name, user_role, active, created_at,
                   last_seen_at, updated_at
            FROM dbo.app_users WHERE id = @UserId;
        END;
    ');

    IF OBJECT_ID(N'dbo.user_identities', N'U') IS NOT NULL
        DROP TABLE dbo.user_identities;

    IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.app_users') AND name = N'IX_app_users_auth_provider_subject')
        DROP INDEX IX_app_users_auth_provider_subject ON dbo.app_users;

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.app_users') AND name = N'UX_app_users_auth_provider_subject')
        CREATE UNIQUE INDEX UX_app_users_auth_provider_subject
            ON dbo.app_users(auth_provider, auth_subject);

    IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_app_users_onboarding_status')
        ALTER TABLE dbo.app_users DROP CONSTRAINT CK_app_users_onboarding_status;
    IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_app_users_account_status')
        ALTER TABLE dbo.app_users DROP CONSTRAINT CK_app_users_account_status;
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = N'UQ_app_users_account_key')
        ALTER TABLE dbo.app_users DROP CONSTRAINT UQ_app_users_account_key;
    IF EXISTS (SELECT 1 FROM sys.default_constraints WHERE name = N'DF_app_users_account_key')
        ALTER TABLE dbo.app_users DROP CONSTRAINT DF_app_users_account_key;
    IF EXISTS (SELECT 1 FROM sys.default_constraints WHERE name = N'DF_app_users_onboarding_status')
        ALTER TABLE dbo.app_users DROP CONSTRAINT DF_app_users_onboarding_status;
    IF EXISTS (SELECT 1 FROM sys.default_constraints WHERE name = N'DF_app_users_account_status')
        ALTER TABLE dbo.app_users DROP CONSTRAINT DF_app_users_account_status;

    IF COL_LENGTH(N'dbo.app_users', N'onboarding_status') IS NOT NULL
        ALTER TABLE dbo.app_users DROP COLUMN onboarding_status;
    IF COL_LENGTH(N'dbo.app_users', N'account_status') IS NOT NULL
        ALTER TABLE dbo.app_users DROP COLUMN account_status;
    IF COL_LENGTH(N'dbo.app_users', N'auth_issuer') IS NOT NULL
        ALTER TABLE dbo.app_users DROP COLUMN auth_issuer;
    IF COL_LENGTH(N'dbo.app_users', N'account_key') IS NOT NULL
        ALTER TABLE dbo.app_users DROP COLUMN account_key;

    DELETE dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001';
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
