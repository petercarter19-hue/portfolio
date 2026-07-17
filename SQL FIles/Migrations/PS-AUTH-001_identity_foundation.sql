/* PS-AUTH-001 external identity mapping and private first-account provisioning. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-007')
        THROW 51800, 'PS-PLAT-007 must be applied first.', 1;

    IF OBJECT_ID(N'dbo.app_users', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_profiles', N'U') IS NULL
       OR OBJECT_ID(N'dbo.connection_preferences', N'U') IS NULL
        THROW 51801, 'The PeerSlate user and privacy foundation is missing.', 1;

    IF COL_LENGTH(N'dbo.app_users', N'account_key') IS NULL
    BEGIN
        EXEC(N'ALTER TABLE dbo.app_users ADD account_key uniqueidentifier NULL;');
        EXEC(N'UPDATE dbo.app_users SET account_key = NEWID() WHERE account_key IS NULL;');
        EXEC(N'ALTER TABLE dbo.app_users ALTER COLUMN account_key uniqueidentifier NOT NULL;');
        EXEC(N'ALTER TABLE dbo.app_users ADD CONSTRAINT DF_app_users_account_key DEFAULT NEWSEQUENTIALID() FOR account_key;');
        EXEC(N'ALTER TABLE dbo.app_users ADD CONSTRAINT UQ_app_users_account_key UNIQUE (account_key);');
    END;

    IF COL_LENGTH(N'dbo.app_users', N'auth_issuer') IS NULL
        EXEC(N'ALTER TABLE dbo.app_users ADD auth_issuer nvarchar(500) NULL;');

    EXEC(N'
        UPDATE dbo.app_users
        SET auth_issuer = N''urn:peerslate:legacy:app-users''
        WHERE auth_issuer IS NULL
          AND auth_provider IS NOT NULL
          AND auth_subject IS NOT NULL;
    ');

    IF COL_LENGTH(N'dbo.app_users', N'account_status') IS NULL
        EXEC(N'ALTER TABLE dbo.app_users ADD account_status nvarchar(30) NOT NULL CONSTRAINT DF_app_users_account_status DEFAULT N''active'' WITH VALUES;');

    IF COL_LENGTH(N'dbo.app_users', N'onboarding_status') IS NULL
        EXEC(N'ALTER TABLE dbo.app_users ADD onboarding_status nvarchar(30) NOT NULL CONSTRAINT DF_app_users_onboarding_status DEFAULT N''not_started'' WITH VALUES;');

    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_app_users_account_status')
        EXEC(N'ALTER TABLE dbo.app_users WITH CHECK ADD CONSTRAINT CK_app_users_account_status CHECK (account_status IN (N''active'', N''suspended'', N''closed''));');

    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_app_users_onboarding_status')
        EXEC(N'ALTER TABLE dbo.app_users WITH CHECK ADD CONSTRAINT CK_app_users_onboarding_status CHECK (onboarding_status IN (N''not_started'', N''in_progress'', N''complete''));');

    IF EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.app_users') AND name = N'UX_app_users_auth_provider_subject')
        DROP INDEX UX_app_users_auth_provider_subject ON dbo.app_users;

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.app_users') AND name = N'IX_app_users_auth_provider_subject')
        CREATE INDEX IX_app_users_auth_provider_subject
            ON dbo.app_users(auth_provider, auth_subject);

    IF OBJECT_ID(N'dbo.user_identities', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.user_identities
        (
            identity_id bigint IDENTITY(1,1) NOT NULL,
            identity_key uniqueidentifier NOT NULL
                CONSTRAINT DF_user_identities_key DEFAULT NEWSEQUENTIALID(),
            user_id int NOT NULL,
            provider nvarchar(100) NOT NULL,
            issuer nvarchar(500) NOT NULL,
            subject nvarchar(500) NOT NULL,
            identity_fingerprint binary(32) NOT NULL,
            email_snapshot nvarchar(254) NULL,
            display_name_snapshot nvarchar(150) NULL,
            identity_status nvarchar(30) NOT NULL
                CONSTRAINT DF_user_identities_status DEFAULT N'active',
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_user_identities_created DEFAULT SYSUTCDATETIME(),
            last_seen_at_utc datetime2(7) NULL,
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_user_identities_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_user_identities PRIMARY KEY (identity_id),
            CONSTRAINT UQ_user_identities_key UNIQUE (identity_key),
            CONSTRAINT UQ_user_identities_fingerprint UNIQUE (identity_fingerprint),
            CONSTRAINT FK_user_identities_user FOREIGN KEY (user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_user_identities_status
                CHECK (identity_status IN (N'active', N'revoked'))
        );
        CREATE INDEX IX_user_identities_user
            ON dbo.user_identities(user_id, identity_status);
    END;

    INSERT dbo.user_identities
    (
        user_id, provider, issuer, subject, identity_fingerprint,
        email_snapshot, display_name_snapshot, last_seen_at_utc
    )
    SELECT
        app_user.id,
        LOWER(LTRIM(RTRIM(app_user.auth_provider))),
        N'urn:peerslate:legacy:app-users',
        LTRIM(RTRIM(app_user.auth_subject)),
        HASHBYTES
        (
            'SHA2_256',
            CONCAT
            (
                LOWER(LTRIM(RTRIM(app_user.auth_provider))), NCHAR(31),
                N'urn:peerslate:legacy:app-users', NCHAR(31),
                LTRIM(RTRIM(app_user.auth_subject))
            )
        ),
        app_user.email,
        app_user.display_name,
        app_user.last_seen_at
    FROM dbo.app_users AS app_user
    WHERE app_user.auth_provider IS NOT NULL
      AND app_user.auth_subject IS NOT NULL
      AND NOT EXISTS
      (
          SELECT 1
          FROM dbo.user_identities AS identity_record
          WHERE identity_record.user_id = app_user.id
            AND identity_record.issuer = N'urn:peerslate:legacy:app-users'
            AND identity_record.subject = app_user.auth_subject
      );

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_UpsertAppUserFromAuth
            @AuthProvider nvarchar(100),
            @AuthIssuer nvarchar(500),
            @AuthSubject nvarchar(500),
            @Email nvarchar(254) = NULL,
            @DisplayName nvarchar(150) = NULL,
            @ProfileImageUrl nvarchar(500) = NULL,
            @TimezoneName nvarchar(100) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @AuthProvider = LOWER(LTRIM(RTRIM(@AuthProvider)));
            SET @AuthIssuer = LTRIM(RTRIM(@AuthIssuer));
            SET @AuthSubject = LTRIM(RTRIM(@AuthSubject));
            WHILE RIGHT(@AuthIssuer, 1) = N''/''
                SET @AuthIssuer = LEFT(@AuthIssuer, LEN(@AuthIssuer) - 1);

            IF NULLIF(@AuthProvider, N'''') IS NULL
                THROW 51810, ''Auth provider is required.'', 1;
            IF NULLIF(@AuthIssuer, N'''') IS NULL
                THROW 51811, ''Auth issuer is required.'', 1;
            IF NULLIF(@AuthSubject, N'''') IS NULL
                THROW 51812, ''Auth subject is required.'', 1;

            DECLARE @Fingerprint binary(32) = HASHBYTES
            (
                ''SHA2_256'',
                CONCAT(@AuthProvider, NCHAR(31), @AuthIssuer, NCHAR(31), @AuthSubject)
            );
            DECLARE @UserId int;
            DECLARE @AccountKey uniqueidentifier;
            DECLARE @UserKey nvarchar(150);
            DECLARE @CreatedAccount bit = 0;

            BEGIN TRY
                BEGIN TRANSACTION;

                IF EXISTS
                (
                    SELECT 1
                    FROM dbo.user_identities WITH (UPDLOCK, HOLDLOCK)
                    WHERE identity_fingerprint = @Fingerprint
                      AND (provider <> @AuthProvider OR issuer <> @AuthIssuer OR subject <> @AuthSubject)
                )
                    THROW 51813, ''Authentication identity collision.'', 1;

                SELECT @UserId = identity_record.user_id
                FROM dbo.user_identities AS identity_record WITH (UPDLOCK, HOLDLOCK)
                WHERE identity_record.identity_fingerprint = @Fingerprint
                  AND identity_record.provider = @AuthProvider
                  AND identity_record.issuer = @AuthIssuer
                  AND identity_record.subject = @AuthSubject
                  AND identity_record.identity_status = N''active'';

                IF @UserId IS NULL
                BEGIN
                    SET @AccountKey = NEWID();
                    SET @UserKey = CONVERT(nvarchar(36), @AccountKey);

                    INSERT dbo.app_users
                    (
                        account_key, user_key, display_name, email,
                        auth_provider, auth_issuer, auth_subject,
                        profile_image_url, timezone_name, user_role,
                        account_status, onboarding_status, active,
                        created_at, last_seen_at, updated_at
                    )
                    VALUES
                    (
                        @AccountKey, @UserKey,
                        COALESCE(NULLIF(@DisplayName, N''''), NULLIF(@Email, N''''), N''PeerSlate member''),
                        NULLIF(@Email, N''''), @AuthProvider, @AuthIssuer, @AuthSubject,
                        @ProfileImageUrl, @TimezoneName, N''user'',
                        N''active'', N''not_started'', 1,
                        SYSUTCDATETIME(), SYSUTCDATETIME(), SYSUTCDATETIME()
                    );

                    SET @UserId = CONVERT(int, SCOPE_IDENTITY());

                    INSERT dbo.user_identities
                    (
                        user_id, provider, issuer, subject, identity_fingerprint,
                        email_snapshot, display_name_snapshot, last_seen_at_utc
                    )
                    VALUES
                    (
                        @UserId, @AuthProvider, @AuthIssuer, @AuthSubject, @Fingerprint,
                        NULLIF(@Email, N''''), NULLIF(@DisplayName, N''''), SYSUTCDATETIME()
                    );

                    SET @CreatedAccount = 1;
                END
                ELSE IF NOT EXISTS
                (
                    SELECT 1 FROM dbo.app_users
                    WHERE id = @UserId AND active = 1 AND account_status = N''active''
                )
                    THROW 51814, ''PeerSlate account is not active.'', 1;

                UPDATE dbo.app_users
                SET display_name = COALESCE(NULLIF(@DisplayName, N''''), display_name),
                    email = COALESCE(NULLIF(@Email, N''''), email),
                    auth_provider = @AuthProvider,
                    auth_issuer = @AuthIssuer,
                    auth_subject = @AuthSubject,
                    profile_image_url = COALESCE(@ProfileImageUrl, profile_image_url),
                    timezone_name = COALESCE(@TimezoneName, timezone_name),
                    last_seen_at = SYSUTCDATETIME(),
                    updated_at = SYSUTCDATETIME()
                WHERE id = @UserId;

                UPDATE dbo.user_identities
                SET email_snapshot = COALESCE(NULLIF(@Email, N''''), email_snapshot),
                    display_name_snapshot = COALESCE(NULLIF(@DisplayName, N''''), display_name_snapshot),
                    last_seen_at_utc = SYSUTCDATETIME(),
                    updated_at_utc = SYSUTCDATETIME()
                WHERE identity_fingerprint = @Fingerprint;

                SELECT @AccountKey = account_key, @UserKey = user_key
                FROM dbo.app_users
                WHERE id = @UserId;

                IF NOT EXISTS (SELECT 1 FROM dbo.member_profiles WHERE user_id = @UserId)
                    INSERT dbo.member_profiles
                    (
                        user_id, profile_slug, display_name, visibility, active
                    )
                    VALUES
                    (
                        @UserId,
                        LOWER(N''member-'' + LEFT(REPLACE(CONVERT(nvarchar(36), @AccountKey), N''-'', N''''), 12)),
                        COALESCE(NULLIF(@DisplayName, N''''), NULLIF(@Email, N''''), N''PeerSlate member''),
                        N''private'', 1
                    );

                IF NOT EXISTS (SELECT 1 FROM dbo.connection_preferences WHERE user_id = @UserId)
                    INSERT dbo.connection_preferences(user_id) VALUES (@UserId);

                IF @CreatedAccount = 1
                BEGIN
                    DECLARE @AuditResult TABLE
                    (
                        audit_event_id bigint,
                        event_key uniqueidentifier,
                        occurred_at_utc datetime2(7),
                        actor_user_id int,
                        actor_user_key_snapshot nvarchar(300),
                        action_type nvarchar(200),
                        entity_type nvarchar(100),
                        entity_key uniqueidentifier,
                        outcome nvarchar(30),
                        request_id nvarchar(100),
                        metadata_json nvarchar(max)
                    );
                    INSERT @AuditResult
                    EXEC dbo.usp_AppendAuditEvent
                        @ActorUserId = @UserId,
                        @ActorUserKeySnapshot = @UserKey,
                        @ActionType = N''auth.account.created'',
                        @EntityType = N''app_user'',
                        @Outcome = N''success'',
                        @MetadataJson = N''{"private_profile_created":true,"discovery_opt_in":false}'';
                END;

                COMMIT TRANSACTION;

                SELECT
                    app_user.id AS user_id,
                    app_user.account_key,
                    app_user.user_key,
                    app_user.display_name,
                    app_user.email,
                    app_user.user_role,
                    app_user.account_status,
                    app_user.onboarding_status,
                    profile.profile_key,
                    profile.profile_slug,
                    profile.visibility AS profile_visibility
                FROM dbo.app_users AS app_user
                JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
                WHERE app_user.id = @UserId;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES
        (
            N'PS-AUTH-001',
            N'Issuer-aware external identities and private first-account provisioning',
            N'PeerSlate Company and Product Bible v1.4'
        );
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.applied',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-AUTH-001"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
