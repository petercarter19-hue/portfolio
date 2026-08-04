/*
PS-PLAT-000 base identity table for fresh installs.

dbo.app_users was created by hand in production before the migration system
existed, so no tracked migration created it and a greenfield forward pass
failed at PS-PLAT-001's audit FK (found by the disposable Community SQL proof,
run 393, code inside_empty_forward_ps_plat_001). This file makes a fresh
database buildable. On production it creates nothing: the table exists, so
only the ledger row is added.

The column set is derived from every tracked consumer: the FK targets in
PS-PLAT-001/002/003/004/006, the insert/update column lists in PS-AUTH-001's
usp_UpsertAppUserFromAuth, and the index PS-AUTH-001 rebuilds. Columns that
PS-AUTH-001 adds itself when missing (account_key, auth_issuer,
account_status, onboarding_status) are intentionally omitted here so the
upgrade path stays exactly the one production already took. Exact type parity
with the hand-created production table is recorded as an open verification
item in PS-COMMUNITY-PUBLIC-PILOT-001; this file is additive-only and never
alters an existing table.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.schema_migrations
        (
            migration_id nvarchar(100) NOT NULL,
            description nvarchar(500) NOT NULL,
            applied_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_schema_migrations_applied_at DEFAULT SYSUTCDATETIME(),
            applied_by nvarchar(256) NOT NULL
                CONSTRAINT DF_schema_migrations_applied_by DEFAULT ORIGINAL_LOGIN(),
            application_version nvarchar(100) NULL,
            notes nvarchar(1000) NULL,
            CONSTRAINT PK_schema_migrations PRIMARY KEY (migration_id)
        );
    END;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.app_users
        (
            id int IDENTITY(1,1) NOT NULL,
            user_key nvarchar(300) NOT NULL,
            display_name nvarchar(300) NOT NULL,
            email nvarchar(320) NULL,
            auth_provider nvarchar(100) NULL,
            auth_subject nvarchar(300) NULL,
            profile_image_url nvarchar(2000) NULL,
            timezone_name nvarchar(100) NULL,
            user_role nvarchar(50) NOT NULL
                CONSTRAINT DF_app_users_user_role DEFAULT N'user',
            active bit NOT NULL
                CONSTRAINT DF_app_users_active DEFAULT 1,
            created_at datetime2(7) NOT NULL
                CONSTRAINT DF_app_users_created_at DEFAULT SYSUTCDATETIME(),
            last_seen_at datetime2(7) NULL,
            updated_at datetime2(7) NOT NULL
                CONSTRAINT DF_app_users_updated_at DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_app_users PRIMARY KEY (id),
            CONSTRAINT UQ_app_users_user_key UNIQUE (user_key)
        );
    END;

    IF COL_LENGTH(N'dbo.app_users', N'id') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'user_key') IS NULL
       OR COL_LENGTH(N'dbo.app_users', N'display_name') IS NULL
        THROW 51000, 'Existing app_users table is incompatible.', 1;

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-PLAT-000'
    )
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES
        (
            N'PS-PLAT-000',
            N'Base identity table for fresh installs (pre-migration app_users)',
            N'PeerSlate SQL Foundation v0.1'
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
