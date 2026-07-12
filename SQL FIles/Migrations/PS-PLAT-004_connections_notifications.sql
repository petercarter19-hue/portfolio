/* PeerSlate opt-in connections, safety controls, consent, and notifications. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-003')
        THROW 51400, 'PS-PLAT-003 must be applied first.', 1;

    IF OBJECT_ID(N'dbo.connection_preferences', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.connection_preferences
        (
            user_id int NOT NULL,
            discovery_opt_in bit NOT NULL CONSTRAINT DF_connection_preferences_discovery DEFAULT 0,
            goal_matching_opt_in bit NOT NULL CONSTRAINT DF_connection_preferences_goal DEFAULT 0,
            recruiter_discovery_opt_in bit NOT NULL CONSTRAINT DF_connection_preferences_recruiter DEFAULT 0,
            discoverable_audience nvarchar(30) NOT NULL CONSTRAINT DF_connection_preferences_audience DEFAULT N'private',
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_connection_preferences_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_connection_preferences PRIMARY KEY (user_id),
            CONSTRAINT FK_connection_preferences_user FOREIGN KEY (user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_connection_preferences_audience CHECK (discoverable_audience IN (N'private', N'connections', N'recruiter', N'public')),
            CONSTRAINT CK_connection_preferences_private CHECK (discoverable_audience <> N'private' OR (discovery_opt_in = 0 AND goal_matching_opt_in = 0 AND recruiter_discovery_opt_in = 0))
        );
    END;

    INSERT dbo.connection_preferences(user_id)
    SELECT u.id FROM dbo.app_users AS u
    WHERE NOT EXISTS (SELECT 1 FROM dbo.connection_preferences AS p WHERE p.user_id = u.id);

    IF OBJECT_ID(N'dbo.connection_requests', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.connection_requests
        (
            connection_request_id bigint IDENTITY(1,1) NOT NULL,
            request_key uniqueidentifier NOT NULL CONSTRAINT DF_connection_requests_key DEFAULT NEWSEQUENTIALID(),
            requester_user_id int NOT NULL,
            recipient_user_id int NOT NULL,
            request_message nvarchar(1000) NULL,
            request_status nvarchar(30) NOT NULL CONSTRAINT DF_connection_requests_status DEFAULT N'pending',
            requested_at_utc datetime2(7) NOT NULL CONSTRAINT DF_connection_requests_requested DEFAULT SYSUTCDATETIME(),
            responded_at_utc datetime2(7) NULL,
            CONSTRAINT PK_connection_requests PRIMARY KEY (connection_request_id),
            CONSTRAINT UQ_connection_requests_key UNIQUE (request_key),
            CONSTRAINT FK_connection_requests_requester FOREIGN KEY (requester_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_connection_requests_recipient FOREIGN KEY (recipient_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_connection_requests_distinct CHECK (requester_user_id <> recipient_user_id),
            CONSTRAINT CK_connection_requests_status CHECK (request_status IN (N'pending', N'accepted', N'declined', N'cancelled', N'expired'))
        );
        CREATE UNIQUE INDEX UX_connection_requests_pending
            ON dbo.connection_requests(requester_user_id, recipient_user_id)
            WHERE request_status = N'pending';
        CREATE INDEX IX_connection_requests_recipient
            ON dbo.connection_requests(recipient_user_id, request_status, requested_at_utc DESC);
    END;

    IF OBJECT_ID(N'dbo.member_connections', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.member_connections
        (
            connection_id bigint IDENTITY(1,1) NOT NULL,
            left_user_id int NOT NULL,
            right_user_id int NOT NULL,
            accepted_request_id bigint NULL,
            connection_status nvarchar(30) NOT NULL CONSTRAINT DF_member_connections_status DEFAULT N'active',
            connected_at_utc datetime2(7) NOT NULL CONSTRAINT DF_member_connections_connected DEFAULT SYSUTCDATETIME(),
            ended_at_utc datetime2(7) NULL,
            CONSTRAINT PK_member_connections PRIMARY KEY (connection_id),
            CONSTRAINT UQ_member_connections_pair UNIQUE (left_user_id, right_user_id),
            CONSTRAINT FK_member_connections_left FOREIGN KEY (left_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_member_connections_right FOREIGN KEY (right_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_member_connections_request FOREIGN KEY (accepted_request_id) REFERENCES dbo.connection_requests(connection_request_id),
            CONSTRAINT CK_member_connections_order CHECK (left_user_id < right_user_id),
            CONSTRAINT CK_member_connections_status CHECK (connection_status IN (N'active', N'ended'))
        );
        CREATE INDEX IX_member_connections_right ON dbo.member_connections(right_user_id, connection_status);
    END;

    IF OBJECT_ID(N'dbo.user_blocks', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.user_blocks
        (
            user_block_id bigint IDENTITY(1,1) NOT NULL,
            blocker_user_id int NOT NULL,
            blocked_user_id int NOT NULL,
            reason_code nvarchar(50) NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_user_blocks_created DEFAULT SYSUTCDATETIME(),
            revoked_at_utc datetime2(7) NULL,
            CONSTRAINT PK_user_blocks PRIMARY KEY (user_block_id),
            CONSTRAINT FK_user_blocks_blocker FOREIGN KEY (blocker_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_user_blocks_blocked FOREIGN KEY (blocked_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_user_blocks_distinct CHECK (blocker_user_id <> blocked_user_id)
        );
        CREATE UNIQUE INDEX UX_user_blocks_active ON dbo.user_blocks(blocker_user_id, blocked_user_id) WHERE revoked_at_utc IS NULL;
        CREATE INDEX IX_user_blocks_blocked ON dbo.user_blocks(blocked_user_id, revoked_at_utc);
    END;

    IF OBJECT_ID(N'dbo.user_reports', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.user_reports
        (
            user_report_id bigint IDENTITY(1,1) NOT NULL,
            report_key uniqueidentifier NOT NULL CONSTRAINT DF_user_reports_key DEFAULT NEWSEQUENTIALID(),
            reporter_user_id int NOT NULL,
            reported_user_id int NOT NULL,
            related_entity_id bigint NULL,
            reason_code nvarchar(50) NOT NULL,
            details nvarchar(2000) NULL,
            report_status nvarchar(30) NOT NULL CONSTRAINT DF_user_reports_status DEFAULT N'open',
            assigned_admin_user_id int NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_user_reports_created DEFAULT SYSUTCDATETIME(),
            resolved_at_utc datetime2(7) NULL,
            CONSTRAINT PK_user_reports PRIMARY KEY (user_report_id),
            CONSTRAINT UQ_user_reports_key UNIQUE (report_key),
            CONSTRAINT FK_user_reports_reporter FOREIGN KEY (reporter_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_user_reports_reported FOREIGN KEY (reported_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_user_reports_entity FOREIGN KEY (related_entity_id) REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT FK_user_reports_admin FOREIGN KEY (assigned_admin_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_user_reports_distinct CHECK (reporter_user_id <> reported_user_id),
            CONSTRAINT CK_user_reports_status CHECK (report_status IN (N'open', N'reviewing', N'resolved', N'dismissed'))
        );
        CREATE INDEX IX_user_reports_status ON dbo.user_reports(report_status, created_at_utc);
        CREATE INDEX IX_user_reports_reported ON dbo.user_reports(reported_user_id, report_status);
    END;

    IF OBJECT_ID(N'dbo.notifications', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.notifications
        (
            notification_id bigint IDENTITY(1,1) NOT NULL,
            notification_key uniqueidentifier NOT NULL CONSTRAINT DF_notifications_key DEFAULT NEWSEQUENTIALID(),
            user_id int NOT NULL,
            notification_type nvarchar(100) NOT NULL,
            title nvarchar(300) NOT NULL,
            body nvarchar(2000) NULL,
            related_entity_id bigint NULL,
            metadata_json nvarchar(max) NULL,
            delivery_status nvarchar(30) NOT NULL CONSTRAINT DF_notifications_delivery DEFAULT N'pending',
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_notifications_created DEFAULT SYSUTCDATETIME(),
            available_at_utc datetime2(7) NOT NULL CONSTRAINT DF_notifications_available DEFAULT SYSUTCDATETIME(),
            read_at_utc datetime2(7) NULL,
            dismissed_at_utc datetime2(7) NULL,
            CONSTRAINT PK_notifications PRIMARY KEY (notification_id),
            CONSTRAINT UQ_notifications_key UNIQUE (notification_key),
            CONSTRAINT FK_notifications_user FOREIGN KEY (user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_notifications_entity FOREIGN KEY (related_entity_id) REFERENCES dbo.slate_entities(entity_id),
            CONSTRAINT CK_notifications_delivery CHECK (delivery_status IN (N'pending', N'delivered', N'failed', N'suppressed')),
            CONSTRAINT CK_notifications_metadata CHECK (metadata_json IS NULL OR ISJSON(metadata_json) = 1)
        );
        CREATE INDEX IX_notifications_inbox ON dbo.notifications(user_id, dismissed_at_utc, read_at_utc, available_at_utc DESC);
        CREATE INDEX IX_notifications_delivery ON dbo.notifications(delivery_status, available_at_utc) WHERE delivery_status = N'pending';
    END;

    IF OBJECT_ID(N'dbo.notification_preferences', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.notification_preferences
        (
            user_id int NOT NULL,
            notification_type nvarchar(100) NOT NULL,
            in_app_enabled bit NOT NULL CONSTRAINT DF_notification_preferences_in_app DEFAULT 1,
            email_enabled bit NOT NULL CONSTRAINT DF_notification_preferences_email DEFAULT 0,
            quiet_hours_start time(0) NULL,
            quiet_hours_end time(0) NULL,
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_notification_preferences_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_notification_preferences PRIMARY KEY (user_id, notification_type),
            CONSTRAINT FK_notification_preferences_user FOREIGN KEY (user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_notification_preferences_quiet_pair CHECK ((quiet_hours_start IS NULL AND quiet_hours_end IS NULL) OR (quiet_hours_start IS NOT NULL AND quiet_hours_end IS NOT NULL))
        );
    END;

    IF OBJECT_ID(N'dbo.user_consents', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.user_consents
        (
            user_consent_id bigint IDENTITY(1,1) NOT NULL,
            user_id int NOT NULL,
            consent_code nvarchar(100) NOT NULL,
            policy_version nvarchar(100) NOT NULL,
            consent_status nvarchar(30) NOT NULL,
            recorded_at_utc datetime2(7) NOT NULL CONSTRAINT DF_user_consents_recorded DEFAULT SYSUTCDATETIME(),
            source_context nvarchar(100) NULL,
            evidence_json nvarchar(max) NULL,
            CONSTRAINT PK_user_consents PRIMARY KEY (user_consent_id),
            CONSTRAINT FK_user_consents_user FOREIGN KEY (user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_user_consents_status CHECK (consent_status IN (N'accepted', N'declined', N'withdrawn')),
            CONSTRAINT CK_user_consents_evidence CHECK (evidence_json IS NULL OR ISJSON(evidence_json) = 1)
        );
        CREATE INDEX IX_user_consents_history ON dbo.user_consents(user_id, consent_code, recorded_at_utc DESC);
    END;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-004')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES (N'PS-PLAT-004', N'Opt-in connections, safety controls, consent history, and notifications', N'PeerSlate SQL Foundation v0.1');
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.applied', @EntityType=N'database_migration', @Outcome=N'success', @MetadataJson=N'{"migration_id":"PS-PLAT-004"}';
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
