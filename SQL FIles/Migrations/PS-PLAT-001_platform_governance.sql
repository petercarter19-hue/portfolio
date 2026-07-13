/*
PeerSlate platform governance foundation.
Additive and idempotent for compatible existing objects.
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

    IF COL_LENGTH(N'dbo.schema_migrations', N'migration_id') IS NULL
        THROW 51001, 'Existing schema_migrations table is incompatible.', 1;

    IF OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.audit_events
        (
            audit_event_id bigint IDENTITY(1,1) NOT NULL,
            event_key uniqueidentifier NOT NULL
                CONSTRAINT DF_audit_events_event_key DEFAULT NEWSEQUENTIALID(),
            occurred_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_audit_events_occurred_at DEFAULT SYSUTCDATETIME(),
            actor_user_id int NULL,
            actor_user_key_snapshot nvarchar(300) NULL,
            action_type nvarchar(200) NOT NULL,
            entity_type nvarchar(100) NULL,
            entity_key uniqueidentifier NULL,
            outcome nvarchar(30) NOT NULL,
            request_id nvarchar(100) NULL,
            metadata_json nvarchar(max) NULL,
            CONSTRAINT PK_audit_events PRIMARY KEY (audit_event_id),
            CONSTRAINT UQ_audit_events_event_key UNIQUE (event_key),
            CONSTRAINT FK_audit_events_app_users FOREIGN KEY (actor_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_audit_events_outcome
                CHECK (outcome IN ('success', 'denied', 'failure')),
            CONSTRAINT CK_audit_events_metadata_json
                CHECK (metadata_json IS NULL OR ISJSON(metadata_json) = 1)
        );

        CREATE INDEX IX_audit_events_actor_time
            ON dbo.audit_events(actor_user_id, occurred_at_utc DESC);
        CREATE INDEX IX_audit_events_entity
            ON dbo.audit_events(entity_type, entity_key, occurred_at_utc DESC);
        CREATE INDEX IX_audit_events_request
            ON dbo.audit_events(request_id)
            WHERE request_id IS NOT NULL;
    END;

    IF COL_LENGTH(N'dbo.audit_events', N'audit_event_id') IS NULL
       OR COL_LENGTH(N'dbo.audit_events', N'action_type') IS NULL
       OR COL_LENGTH(N'dbo.audit_events', N'outcome') IS NULL
        THROW 51002, 'Existing audit_events table is incompatible.', 1;

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_AppendAuditEvent
            @ActorUserId int = NULL,
            @ActorUserKeySnapshot nvarchar(300) = NULL,
            @ActionType nvarchar(200),
            @EntityType nvarchar(100) = NULL,
            @EntityKey uniqueidentifier = NULL,
            @Outcome nvarchar(30),
            @RequestId nvarchar(100) = NULL,
            @MetadataJson nvarchar(max) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            IF @Outcome NOT IN (N''success'', N''denied'', N''failure'')
                THROW 51003, ''Unsupported audit outcome.'', 1;
            IF @MetadataJson IS NOT NULL AND ISJSON(@MetadataJson) <> 1
                THROW 51004, ''Audit metadata must be valid JSON.'', 1;

            INSERT dbo.audit_events
            (
                actor_user_id, actor_user_key_snapshot, action_type,
                entity_type, entity_key, outcome, request_id, metadata_json
            )
            VALUES
            (
                @ActorUserId, @ActorUserKeySnapshot, @ActionType,
                @EntityType, @EntityKey, @Outcome, @RequestId, @MetadataJson
            );

            SELECT *
            FROM dbo.audit_events
            WHERE audit_event_id = CONVERT(bigint, SCOPE_IDENTITY());
        END;
    ');

    EXEC(N'
        CREATE OR ALTER TRIGGER dbo.trg_audit_events_immutable
        ON dbo.audit_events
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            THROW 51005, ''Audit events are immutable.'', 1;
        END;
    ');

    IF NOT EXISTS
    (
        SELECT 1 FROM dbo.schema_migrations
        WHERE migration_id = N'PS-PLAT-001'
    )
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES
        (
            N'PS-PLAT-001',
            N'Platform migration ledger and immutable audit foundation',
            N'PeerSlate SQL Foundation v0.1'
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
