/*
PS-RESUME-CATALOG-001 — durable curated catalog fence for generated Resume media.

PROPOSED ONLY. Gate is null. Fixtures cannot stand in for this table.
Catalog maintenance is a distinct closed command. The ordinary application
principal cannot execute internal helpers or mutate catalog rows directly.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-MEDIA-001')
        THROW 53100, 'PS-RESUME-MEDIA-001 must be applied first.', 1;

    IF OBJECT_ID(N'dbo.resume_catalog_assets', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_catalog_assets
        (
            catalog_asset_id bigint IDENTITY(1,1) NOT NULL,
            asset_id uniqueidentifier NOT NULL,
            asset_version int NOT NULL,
            content_sha256 char(64) NOT NULL,
            label nvarchar(200) NOT NULL,
            category nvarchar(80) NOT NULL,
            tags nvarchar(400) NOT NULL,
            width int NOT NULL,
            height int NOT NULL,
            origin nvarchar(40) NOT NULL,
            lifecycle nvarchar(30) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_catalog_assets_created DEFAULT SYSUTCDATETIME(),
            withdrawn_at_utc datetime2(7) NULL,
            CONSTRAINT PK_resume_catalog_assets PRIMARY KEY (catalog_asset_id),
            CONSTRAINT UQ_resume_catalog_assets_id_version UNIQUE (asset_id, asset_version),
            CONSTRAINT CK_resume_catalog_assets_version CHECK (asset_version >= 1),
            CONSTRAINT CK_resume_catalog_assets_origin CHECK (origin = N'generated_illustration'),
            CONSTRAINT CK_resume_catalog_assets_lifecycle CHECK (lifecycle IN (N'active', N'withdrawn')),
            CONSTRAINT CK_resume_catalog_assets_withdrawn CHECK
                ((lifecycle = N'withdrawn' AND withdrawn_at_utc IS NOT NULL)
                 OR (lifecycle = N'active' AND withdrawn_at_utc IS NULL))
        );
    END;

    IF OBJECT_ID(N'dbo.resume_catalog_command_receipts', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.resume_catalog_command_receipts
        (
            command_receipt_id bigint IDENTITY(1,1) NOT NULL,
            actor_profile_id bigint NOT NULL,
            request_id uniqueidentifier NOT NULL,
            request_digest char(64) NOT NULL,
            command_type nvarchar(40) NOT NULL,
            outcome nvarchar(40) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_catalog_receipts_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_catalog_command_receipts PRIMARY KEY (command_receipt_id),
            CONSTRAINT UQ_resume_catalog_receipts_actor_request UNIQUE (actor_profile_id, request_id),
            CONSTRAINT FK_resume_catalog_receipts_actor
                FOREIGN KEY (actor_profile_id) REFERENCES dbo.member_profiles(profile_id)
        );
    END;

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_ResumeCatalogApplyInternal
    @AssetId uniqueidentifier,
    @AssetVersion int,
    @Lifecycle nvarchar(30)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF @Lifecycle = N''withdrawn''
        UPDATE dbo.resume_catalog_assets
           SET lifecycle = N''withdrawn'',
               withdrawn_at_utc = SYSUTCDATETIME()
         WHERE asset_id = @AssetId
           AND asset_version = @AssetVersion
           AND lifecycle = N''active'';
    IF @@ROWCOUNT <> 1
        THROW 53110, ''Catalog asset is unavailable.'', 1;
END;';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_GetResumeCatalogAsset
    @AssetId uniqueidentifier,
    @AssetVersion int
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SELECT asset_id, asset_version AS version, content_sha256 AS digest, label, category,
           tags, width, height, origin, lifecycle
      FROM dbo.resume_catalog_assets
     WHERE asset_id = @AssetId
       AND asset_version = @AssetVersion;
END;';

    EXEC sys.sp_executesql N'
CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeCatalogCommandForOwner
    @UserKey uniqueidentifier,
    @RequestId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    IF @@TRANCOUNT <> 0
        THROW 53120, ''Ambient transactions are not permitted.'', 1;

    BEGIN TRANSACTION;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey
       AND app_user.active = 1
       AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 53121, ''Owner is unavailable.'', 1;

    DECLARE @Digest char(64) = CONVERT(char(64), HASHBYTES(''SHA2_256'', CONVERT(varbinary(max), @CommandJson)), 2);
    DECLARE @Existing char(64);
    SELECT @Existing = request_digest
      FROM dbo.resume_catalog_command_receipts WITH (UPDLOCK, HOLDLOCK)
     WHERE actor_profile_id = @ProfileId
       AND request_id = @RequestId;
    IF @Existing IS NOT NULL
    BEGIN
        IF @Existing <> @Digest
            THROW 53122, ''That request already used a different payload.'', 1;
        SELECT committed = 0, replayed = 1, outcome = N''replayed'', request_digest = @Existing;
        COMMIT;
        RETURN;
    END;

    DECLARE @Type nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
    IF @Type <> N''withdraw''
        THROW 53123, ''Unknown catalog command.'', 1;
    DECLARE @AssetId uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.asset_id''));
    DECLARE @AssetVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.version''));
    EXEC dbo.usp_ResumeCatalogApplyInternal @AssetId = @AssetId, @AssetVersion = @AssetVersion, @Lifecycle = N''withdrawn'';

    INSERT dbo.resume_catalog_command_receipts (actor_profile_id, request_id, request_digest, command_type, outcome)
    VALUES (@ProfileId, @RequestId, @Digest, @Type, N''withdrawn'');
    SELECT committed = 1, replayed = 0, outcome = N''withdrawn'', request_digest = @Digest;
    COMMIT;
END;';

    DENY INSERT, UPDATE, DELETE ON dbo.resume_catalog_assets TO PUBLIC;
    DENY EXECUTE ON dbo.usp_ResumeCatalogApplyInternal TO PUBLIC;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-RESUME-CATALOG-001')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES
            (N'PS-RESUME-CATALOG-001',
             N'Proposed durable curated catalog fence for generated Resume media',
             N'PeerSlate MVP1 Package E');
        EXEC dbo.usp_AppendAuditEvent
            @ActionType=N'schema.migration.applied', @EntityType=N'database_migration',
            @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-RESUME-CATALOG-001"}';
    END;

    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;
