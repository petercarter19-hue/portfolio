/*
PS-CONNECT-002 -- additive relationship lifecycle hardening for Profile.

PS-PLAT-004 remains the source of truth for its existing connection request,
current-member-connection, and directional-block tables.  This migration never
alters or replaces those objects.  It adds a pair-scoped state/epoch extension,
append-only lifecycle events, and exact idempotent command receipts around the
existing rows so later Profile authorization can consume one fail-closed
relationship snapshot.

The procedures are intentionally not added to services/database_service.py in
this non-production provider package.  Registration and route wiring require a
later, separately authorized integration slice.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-004')
        THROW 53300, 'PS-PLAT-004 must be applied before PS-CONNECT-002.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
        THROW 53301, 'PS-AUTH-001 must be applied before PS-CONNECT-002.', 1;
    IF OBJECT_ID(N'dbo.connection_requests', N'U') IS NULL
       OR OBJECT_ID(N'dbo.member_connections', N'U') IS NULL
       OR OBJECT_ID(N'dbo.user_blocks', N'U') IS NULL
       OR OBJECT_ID(N'dbo.app_users', N'U') IS NULL
        THROW 53302, 'PS-PLAT-004 connection foundation is incomplete.', 1;

    /* Do not guess through pre-existing contradictory PS-PLAT-004 rows.
       Reconciliation is a member/data decision, not a migration side effect. */
    IF EXISTS
    (
        SELECT 1
        FROM dbo.connection_requests AS first_request
        JOIN dbo.connection_requests AS reciprocal_request
          ON reciprocal_request.request_status = N'pending'
         AND reciprocal_request.requester_user_id = first_request.recipient_user_id
         AND reciprocal_request.recipient_user_id = first_request.requester_user_id
         AND reciprocal_request.connection_request_id > first_request.connection_request_id
        WHERE first_request.request_status = N'pending'
    )
        THROW 53303, 'PS-PLAT-004 has reciprocal pending requests requiring explicit reconciliation.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM dbo.connection_requests AS request_record
        JOIN dbo.member_connections AS connection_record
          ON connection_record.connection_status = N'active'
         AND connection_record.left_user_id = CASE WHEN request_record.requester_user_id < request_record.recipient_user_id THEN request_record.requester_user_id ELSE request_record.recipient_user_id END
         AND connection_record.right_user_id = CASE WHEN request_record.requester_user_id < request_record.recipient_user_id THEN request_record.recipient_user_id ELSE request_record.requester_user_id END
        WHERE request_record.request_status = N'pending'
    )
        THROW 53304, 'PS-PLAT-004 has both pending and active relationship truth for one pair.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM dbo.user_blocks AS block_record
        JOIN dbo.connection_requests AS request_record
          ON request_record.request_status = N'pending'
         AND ((request_record.requester_user_id = block_record.blocker_user_id AND request_record.recipient_user_id = block_record.blocked_user_id)
           OR (request_record.requester_user_id = block_record.blocked_user_id AND request_record.recipient_user_id = block_record.blocker_user_id))
        WHERE block_record.revoked_at_utc IS NULL
    )
        THROW 53305, 'PS-PLAT-004 has a pending request behind an active block.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM dbo.user_blocks AS block_record
        JOIN dbo.member_connections AS connection_record
          ON connection_record.connection_status = N'active'
         AND ((connection_record.left_user_id = CASE WHEN block_record.blocker_user_id < block_record.blocked_user_id THEN block_record.blocker_user_id ELSE block_record.blocked_user_id END)
          AND (connection_record.right_user_id = CASE WHEN block_record.blocker_user_id < block_record.blocked_user_id THEN block_record.blocked_user_id ELSE block_record.blocker_user_id END))
        WHERE block_record.revoked_at_utc IS NULL
    )
        THROW 53306, 'PS-PLAT-004 has an active connection behind an active block.', 1;

    IF OBJECT_ID(N'dbo.connection_relationship_states', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.connection_relationship_states
        (
            relationship_id bigint IDENTITY(1,1) NOT NULL,
            left_user_id int NOT NULL,
            right_user_id int NOT NULL,
            relationship_state nvarchar(24) NOT NULL,
            pending_requester_user_id int NULL,
            relationship_version bigint NOT NULL CONSTRAINT DF_connection_relationship_states_version DEFAULT 1,
            block_epoch bigint NOT NULL CONSTRAINT DF_connection_relationship_states_block_epoch DEFAULT 1,
            event_sequence bigint NOT NULL CONSTRAINT DF_connection_relationship_states_event_sequence DEFAULT 1,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_connection_relationship_states_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_connection_relationship_states_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_connection_relationship_states PRIMARY KEY (relationship_id),
            CONSTRAINT UQ_connection_relationship_states_pair UNIQUE (left_user_id, right_user_id),
            CONSTRAINT FK_connection_relationship_states_left FOREIGN KEY (left_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_connection_relationship_states_right FOREIGN KEY (right_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_connection_relationship_states_pending_requester FOREIGN KEY (pending_requester_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_connection_relationship_states_order CHECK (left_user_id < right_user_id),
            CONSTRAINT CK_connection_relationship_states_state CHECK (relationship_state IN (N'none', N'pending', N'connected', N'declined', N'cancelled', N'expired', N'disconnected', N'blocked')),
            CONSTRAINT CK_connection_relationship_states_pending_requester CHECK
            (
                (relationship_state = N'pending' AND pending_requester_user_id IS NOT NULL AND pending_requester_user_id IN (left_user_id, right_user_id))
                OR (relationship_state <> N'pending' AND pending_requester_user_id IS NULL)
            ),
            CONSTRAINT CK_connection_relationship_states_version CHECK (relationship_version >= 1 AND block_epoch >= 1 AND event_sequence >= 1)
        );
        CREATE INDEX IX_connection_relationship_states_right
            ON dbo.connection_relationship_states(right_user_id, relationship_state, updated_at_utc DESC);
    END;

    IF OBJECT_ID(N'dbo.connection_relationship_events', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.connection_relationship_events
        (
            relationship_event_id bigint IDENTITY(1,1) NOT NULL,
            event_key uniqueidentifier NOT NULL CONSTRAINT DF_connection_relationship_events_key DEFAULT NEWSEQUENTIALID(),
            relationship_id bigint NOT NULL,
            event_sequence bigint NOT NULL,
            actor_user_id int NULL,
            subject_user_id int NULL,
            event_kind nvarchar(40) NOT NULL,
            relationship_version bigint NOT NULL,
            block_epoch bigint NOT NULL,
            occurred_at_utc datetime2(7) NOT NULL CONSTRAINT DF_connection_relationship_events_occurred DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_connection_relationship_events PRIMARY KEY (relationship_event_id),
            CONSTRAINT UQ_connection_relationship_events_key UNIQUE (event_key),
            CONSTRAINT UQ_connection_relationship_events_sequence UNIQUE (relationship_id, event_sequence),
            CONSTRAINT FK_connection_relationship_events_relationship FOREIGN KEY (relationship_id) REFERENCES dbo.connection_relationship_states(relationship_id),
            CONSTRAINT FK_connection_relationship_events_actor FOREIGN KEY (actor_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_connection_relationship_events_subject FOREIGN KEY (subject_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_connection_relationship_events_kind CHECK (event_kind IN (N'legacy_anchor', N'legacy_block_anchor', N'request', N'reciprocal_accept', N'accept', N'decline', N'cancel', N'expire', N'disconnect', N'block', N'unblock', N'reconnect')),
            CONSTRAINT CK_connection_relationship_events_actor_subject CHECK
            (
                (actor_user_id IS NULL AND subject_user_id IS NULL AND event_kind IN (N'legacy_anchor', N'legacy_block_anchor'))
                OR (actor_user_id IS NOT NULL AND subject_user_id IS NOT NULL AND actor_user_id <> subject_user_id)
            ),
            CONSTRAINT CK_connection_relationship_events_epochs CHECK (relationship_version >= 1 AND block_epoch >= 1 AND event_sequence >= 1)
        );
        CREATE INDEX IX_connection_relationship_events_relationship
            ON dbo.connection_relationship_events(relationship_id, event_sequence DESC);
    END;

    IF OBJECT_ID(N'dbo.connection_relationship_commands', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.connection_relationship_commands
        (
            relationship_command_id bigint IDENTITY(1,1) NOT NULL,
            command_key uniqueidentifier NOT NULL CONSTRAINT DF_connection_relationship_commands_key DEFAULT NEWSEQUENTIALID(),
            relationship_id bigint NOT NULL,
            actor_user_id int NOT NULL,
            subject_user_id int NOT NULL,
            command_name nvarchar(20) NOT NULL,
            expected_relationship_version bigint NULL,
            idempotency_key nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL,
            request_digest nvarchar(64) COLLATE Latin1_General_100_BIN2 NOT NULL,
            result_state nvarchar(24) NOT NULL,
            result_relationship_version bigint NOT NULL,
            result_block_epoch bigint NOT NULL,
            result_blocked_either_direction bit NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_connection_relationship_commands_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_connection_relationship_commands PRIMARY KEY (relationship_command_id),
            CONSTRAINT UQ_connection_relationship_commands_key UNIQUE (command_key),
            CONSTRAINT UQ_connection_relationship_commands_actor_idempotency UNIQUE (actor_user_id, idempotency_key),
            CONSTRAINT FK_connection_relationship_commands_relationship FOREIGN KEY (relationship_id) REFERENCES dbo.connection_relationship_states(relationship_id),
            CONSTRAINT FK_connection_relationship_commands_actor FOREIGN KEY (actor_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT FK_connection_relationship_commands_subject FOREIGN KEY (subject_user_id) REFERENCES dbo.app_users(id),
            CONSTRAINT CK_connection_relationship_commands_distinct CHECK (actor_user_id <> subject_user_id),
            CONSTRAINT CK_connection_relationship_commands_name CHECK (command_name IN (N'request', N'accept', N'decline', N'cancel', N'expire', N'disconnect', N'block', N'unblock', N'reconnect')),
            CONSTRAINT CK_connection_relationship_commands_idempotency CHECK (LEN(idempotency_key) BETWEEN 8 AND 128 AND idempotency_key COLLATE Latin1_General_100_BIN2 NOT LIKE N'%[^-A-Za-z0-9_]%'),
            CONSTRAINT CK_connection_relationship_commands_digest CHECK (LEN(request_digest) = 64 AND request_digest COLLATE Latin1_General_100_BIN2 NOT LIKE N'%[^0-9a-f]%'),
            CONSTRAINT CK_connection_relationship_commands_result CHECK (result_state IN (N'none', N'outbound_pending', N'inbound_pending', N'connected', N'declined', N'cancelled', N'expired', N'disconnected', N'blocked') AND result_relationship_version >= 1 AND result_block_epoch >= 1)
        );
        CREATE INDEX IX_connection_relationship_commands_relationship
            ON dbo.connection_relationship_commands(relationship_id, created_at_utc DESC);
    END;

    /* Anchor compatible legacy state without rewriting PS-PLAT-004 rows. */
    INSERT dbo.connection_relationship_states
    (
        left_user_id, right_user_id, relationship_state, pending_requester_user_id,
        relationship_version, block_epoch, event_sequence
    )
    SELECT connection_record.left_user_id, connection_record.right_user_id,
           N'connected', NULL, 1, 1, 1
    FROM dbo.member_connections AS connection_record
    WHERE connection_record.connection_status = N'active'
      AND NOT EXISTS
      (
          SELECT 1 FROM dbo.connection_relationship_states AS state_record
          WHERE state_record.left_user_id = connection_record.left_user_id
            AND state_record.right_user_id = connection_record.right_user_id
      );

    ;WITH active_blocks AS
    (
        SELECT DISTINCT
            CASE WHEN blocker_user_id < blocked_user_id THEN blocker_user_id ELSE blocked_user_id END AS left_user_id,
            CASE WHEN blocker_user_id < blocked_user_id THEN blocked_user_id ELSE blocker_user_id END AS right_user_id
        FROM dbo.user_blocks
        WHERE revoked_at_utc IS NULL
    )
    INSERT dbo.connection_relationship_states
    (
        left_user_id, right_user_id, relationship_state, pending_requester_user_id,
        relationship_version, block_epoch, event_sequence
    )
    SELECT active_blocks.left_user_id, active_blocks.right_user_id,
           N'blocked', NULL, 1, 1, 1
    FROM active_blocks
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.connection_relationship_states AS state_record
        WHERE state_record.left_user_id = active_blocks.left_user_id
          AND state_record.right_user_id = active_blocks.right_user_id
    );

    INSERT dbo.connection_relationship_states
    (
        left_user_id, right_user_id, relationship_state, pending_requester_user_id,
        relationship_version, block_epoch, event_sequence
    )
    SELECT
        CASE WHEN request_record.requester_user_id < request_record.recipient_user_id THEN request_record.requester_user_id ELSE request_record.recipient_user_id END,
        CASE WHEN request_record.requester_user_id < request_record.recipient_user_id THEN request_record.recipient_user_id ELSE request_record.requester_user_id END,
        N'pending', request_record.requester_user_id, 1, 1, 1
    FROM dbo.connection_requests AS request_record
    WHERE request_record.request_status = N'pending'
      AND NOT EXISTS
      (
          SELECT 1
          FROM dbo.connection_relationship_states AS state_record
          WHERE state_record.left_user_id = CASE WHEN request_record.requester_user_id < request_record.recipient_user_id THEN request_record.requester_user_id ELSE request_record.recipient_user_id END
            AND state_record.right_user_id = CASE WHEN request_record.requester_user_id < request_record.recipient_user_id THEN request_record.recipient_user_id ELSE request_record.requester_user_id END
      );

    INSERT dbo.connection_relationship_events
    (
        relationship_id, event_sequence, actor_user_id, subject_user_id, event_kind,
        relationship_version, block_epoch
    )
    SELECT state_record.relationship_id, state_record.event_sequence, NULL, NULL,
           CASE WHEN state_record.relationship_state = N'blocked' THEN N'legacy_block_anchor' ELSE N'legacy_anchor' END,
           state_record.relationship_version, state_record.block_epoch
    FROM dbo.connection_relationship_states AS state_record
    WHERE NOT EXISTS
    (
        SELECT 1 FROM dbo.connection_relationship_events AS event_record
        WHERE event_record.relationship_id = state_record.relationship_id
          AND event_record.event_sequence = state_record.event_sequence
    );

    EXEC(N'
CREATE OR ALTER PROCEDURE dbo.usp_CommitConnectionRelationshipCommandForActor
    @ActorUserKey nvarchar(300),
    @SubjectUserKey nvarchar(300),
    @Command nvarchar(20),
    @ExpectedRelationshipVersion nvarchar(24) = NULL,
    @IdempotencyKey nvarchar(128),
    @RequestDigest nvarchar(64)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @ActorUserKey IS NULL OR @SubjectUserKey IS NULL OR @Command IS NULL
       OR @IdempotencyKey IS NULL OR @RequestDigest IS NULL
       OR LEN(@ActorUserKey) NOT BETWEEN 8 AND 128
       OR LEN(@SubjectUserKey) NOT BETWEEN 8 AND 128
       OR @ActorUserKey COLLATE Latin1_General_100_BIN2 LIKE N''%[^-A-Za-z0-9_]%''
       OR @SubjectUserKey COLLATE Latin1_General_100_BIN2 LIKE N''%[^-A-Za-z0-9_]%''
       OR LEN(@IdempotencyKey) NOT BETWEEN 8 AND 128
       OR @IdempotencyKey COLLATE Latin1_General_100_BIN2 LIKE N''%[^-A-Za-z0-9_]%''
       OR LEN(@RequestDigest) <> 64
       OR @RequestDigest COLLATE Latin1_General_100_BIN2 LIKE N''%[^0-9a-f]%''
       OR @Command COLLATE Latin1_General_100_BIN2 NOT IN (N''request'', N''accept'', N''decline'', N''cancel'', N''expire'', N''disconnect'', N''block'', N''unblock'', N''reconnect'')
    BEGIN
        SELECT CAST(0 AS bit) AS committed;
        RETURN;
    END;

    DECLARE @ExpectedVersion bigint = NULL;
    IF @ExpectedRelationshipVersion IS NOT NULL
    BEGIN
        IF LEN(@ExpectedRelationshipVersion) <> 24
           OR LEFT(@ExpectedRelationshipVersion, 4) COLLATE Latin1_General_100_BIN2 <> N''rel_''
           OR RIGHT(@ExpectedRelationshipVersion, 20) COLLATE Latin1_General_100_BIN2 LIKE N''%[^0-9]%''
        BEGIN
            SELECT CAST(0 AS bit) AS committed;
            RETURN;
        END;
        SET @ExpectedVersion = TRY_CONVERT(bigint, RIGHT(@ExpectedRelationshipVersion, 20));
        IF @ExpectedVersion IS NULL
        BEGIN
            SELECT CAST(0 AS bit) AS committed;
            RETURN;
        END;
    END;

    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @ActorUserId int;
        SELECT @ActorUserId = app_user.id
        FROM dbo.app_users AS app_user WITH (UPDLOCK, HOLDLOCK)
        WHERE app_user.user_key COLLATE Latin1_General_100_BIN2 = @ActorUserKey COLLATE Latin1_General_100_BIN2
          AND app_user.active = 1 AND app_user.account_status = N''active'';
        IF @ActorUserId IS NULL
        BEGIN
            ROLLBACK TRANSACTION;
            SELECT CAST(0 AS bit) AS committed;
            RETURN;
        END;

        /* This serializable key-range lock makes the same actor/key a single
           stored winner even when its pair request races another request. */
        DECLARE @ExistingCommandId bigint;
        DECLARE @ExistingSubjectUserId int;
        DECLARE @ExistingCommand nvarchar(20);
        DECLARE @ExistingDigest nvarchar(64);
        DECLARE @ExistingExpectedVersion bigint;
        SELECT @ExistingCommandId = command_record.relationship_command_id,
               @ExistingSubjectUserId = command_record.subject_user_id,
               @ExistingCommand = command_record.command_name,
               @ExistingDigest = command_record.request_digest,
               @ExistingExpectedVersion = command_record.expected_relationship_version
        FROM dbo.connection_relationship_commands AS command_record WITH (UPDLOCK, HOLDLOCK)
        WHERE command_record.actor_user_id = @ActorUserId
          AND command_record.idempotency_key COLLATE Latin1_General_100_BIN2 = @IdempotencyKey COLLATE Latin1_General_100_BIN2;

        DECLARE @SubjectUserId int;
        SELECT @SubjectUserId = app_user.id
        FROM dbo.app_users AS app_user WITH (UPDLOCK, HOLDLOCK)
        WHERE app_user.user_key COLLATE Latin1_General_100_BIN2 = @SubjectUserKey COLLATE Latin1_General_100_BIN2
          AND app_user.active = 1 AND app_user.account_status = N''active'';
        IF @SubjectUserId IS NULL OR @SubjectUserId = @ActorUserId
        BEGIN
            ROLLBACK TRANSACTION;
            SELECT CAST(0 AS bit) AS committed;
            RETURN;
        END;

        IF @ExistingCommandId IS NOT NULL
        BEGIN
            IF @ExistingSubjectUserId <> @SubjectUserId
               OR @ExistingCommand COLLATE Latin1_General_100_BIN2 <> @Command COLLATE Latin1_General_100_BIN2
               OR @ExistingDigest COLLATE Latin1_General_100_BIN2 <> @RequestDigest COLLATE Latin1_General_100_BIN2
               OR ((@ExistingExpectedVersion IS NULL AND @ExpectedVersion IS NOT NULL) OR (@ExistingExpectedVersion IS NOT NULL AND @ExpectedVersion IS NULL) OR (@ExistingExpectedVersion <> @ExpectedVersion))
            BEGIN
                ROLLBACK TRANSACTION;
                SELECT CAST(0 AS bit) AS committed;
                RETURN;
            END;

            COMMIT TRANSACTION;
            SELECT CAST(1 AS bit) AS committed,
                   CONVERT(nvarchar(36), command_record.command_key) AS command_key,
                   actor_user.user_key AS actor_user_key,
                   subject_user.user_key AS subject_user_key,
                   command_record.command_name AS command,
                   command_record.idempotency_key,
                   command_record.request_digest,
                   command_record.result_state AS state,
                   CONCAT(N''rel_'', RIGHT(REPLICATE(N''0'', 20) + CONVERT(nvarchar(20), command_record.result_relationship_version), 20)) AS relationship_version,
                   CONCAT(N''blk_'', RIGHT(REPLICATE(N''0'', 20) + CONVERT(nvarchar(20), command_record.result_block_epoch), 20)) AS block_epoch,
                   command_record.result_blocked_either_direction AS blocked_either_direction
            FROM dbo.connection_relationship_commands AS command_record
            JOIN dbo.app_users AS actor_user ON actor_user.id = command_record.actor_user_id
            JOIN dbo.app_users AS subject_user ON subject_user.id = command_record.subject_user_id
            WHERE command_record.relationship_command_id = @ExistingCommandId;
            RETURN;
        END;

        DECLARE @LeftUserId int = CASE WHEN @ActorUserId < @SubjectUserId THEN @ActorUserId ELSE @SubjectUserId END;
        DECLARE @RightUserId int = CASE WHEN @ActorUserId < @SubjectUserId THEN @SubjectUserId ELSE @ActorUserId END;
        DECLARE @LockResult int;
        DECLARE @PairLockResource nvarchar(255) = CONCAT(N''PS-CONNECT-002:'', @LeftUserId, N'':'', @RightUserId);
        EXEC @LockResult = sys.sp_getapplock @Resource = @PairLockResource, @LockMode = N''Exclusive'', @LockOwner = N''Transaction'', @LockTimeout = 5000, @DbPrincipal = N''public'';
        IF @LockResult < 0
        BEGIN
            ROLLBACK TRANSACTION;
            SELECT CAST(0 AS bit) AS committed;
            RETURN;
        END;

        DECLARE @RelationshipId bigint;
        DECLARE @CurrentState nvarchar(24) = N''none'';
        DECLARE @CurrentPendingRequesterId int = NULL;
        DECLARE @CurrentVersion bigint = 0;
        DECLARE @CurrentBlockEpoch bigint = 0;
        DECLARE @CurrentEventSequence bigint = 0;
        SELECT @RelationshipId = state_record.relationship_id,
               @CurrentState = state_record.relationship_state,
               @CurrentPendingRequesterId = state_record.pending_requester_user_id,
               @CurrentVersion = state_record.relationship_version,
               @CurrentBlockEpoch = state_record.block_epoch,
               @CurrentEventSequence = state_record.event_sequence
        FROM dbo.connection_relationship_states AS state_record WITH (UPDLOCK, HOLDLOCK)
        WHERE state_record.left_user_id = @LeftUserId AND state_record.right_user_id = @RightUserId;

        DECLARE @ActorBlockId bigint;
        SELECT @ActorBlockId = block_record.user_block_id
        FROM dbo.user_blocks AS block_record WITH (UPDLOCK, HOLDLOCK)
        WHERE block_record.blocker_user_id = @ActorUserId
          AND block_record.blocked_user_id = @SubjectUserId
          AND block_record.revoked_at_utc IS NULL;
        DECLARE @AnyActiveBlock bit = CASE WHEN EXISTS
        (
            SELECT 1 FROM dbo.user_blocks AS block_record WITH (UPDLOCK, HOLDLOCK)
            WHERE block_record.revoked_at_utc IS NULL
              AND ((block_record.blocker_user_id = @ActorUserId AND block_record.blocked_user_id = @SubjectUserId)
                OR (block_record.blocker_user_id = @SubjectUserId AND block_record.blocked_user_id = @ActorUserId))
        ) THEN 1 ELSE 0 END;

        /* A pair starts only from a token-less request or block. Every later
           mutation is an exact compare-and-swap; rel_000...0 is never an
           accepted synthetic initial token. */
        IF (@CurrentVersion = 0 AND (@ExpectedVersion IS NOT NULL OR @Command NOT IN (N''request'', N''block'')))
           OR (@CurrentVersion <> 0 AND (@ExpectedVersion IS NULL OR @ExpectedVersion <> @CurrentVersion))
        BEGIN
            ROLLBACK TRANSACTION;
            SELECT CAST(0 AS bit) AS committed;
            RETURN;
        END;

        DECLARE @NewState nvarchar(24);
        DECLARE @NewPendingRequesterId int = NULL;
        DECLARE @EventKind nvarchar(40);
        DECLARE @AdvanceBlockEpoch bit = 0;
        DECLARE @PendingRequestId bigint = NULL;
        DECLARE @PendingRequesterId int = NULL;
        DECLARE @PendingRecipientId int = NULL;

        SELECT TOP (1) @PendingRequestId = request_record.connection_request_id,
                       @PendingRequesterId = request_record.requester_user_id,
                       @PendingRecipientId = request_record.recipient_user_id
        FROM dbo.connection_requests AS request_record WITH (UPDLOCK, HOLDLOCK)
        WHERE request_record.request_status = N''pending''
          AND ((request_record.requester_user_id = @ActorUserId AND request_record.recipient_user_id = @SubjectUserId)
            OR (request_record.requester_user_id = @SubjectUserId AND request_record.recipient_user_id = @ActorUserId))
        ORDER BY request_record.connection_request_id;

        /* A reciprocal request is an explicit accept only when both canonical
           state and legacy pending truth agree on the opposite orientation. */
        DECLARE @IsReciprocalPendingRequest bit = CASE WHEN
            @CurrentState = N''pending''
            AND @CurrentPendingRequesterId = @SubjectUserId
            AND @PendingRequestId IS NOT NULL
            AND @PendingRequesterId = @SubjectUserId
            AND @PendingRecipientId = @ActorUserId
        THEN 1 ELSE 0 END;

        IF @Command = N''block''
        BEGIN
            IF @ActorBlockId IS NOT NULL
            BEGIN
                ROLLBACK TRANSACTION;
                SELECT CAST(0 AS bit) AS committed;
                RETURN;
            END;
            INSERT dbo.user_blocks(blocker_user_id, blocked_user_id, reason_code)
            VALUES (@ActorUserId, @SubjectUserId, N''member_action'');
            IF @PendingRequestId IS NOT NULL
                UPDATE dbo.connection_requests SET request_status = N''cancelled'', responded_at_utc = SYSUTCDATETIME()
                WHERE connection_request_id = @PendingRequestId AND request_status = N''pending'';
            UPDATE dbo.member_connections
            SET connection_status = N''ended'', ended_at_utc = SYSUTCDATETIME()
            WHERE left_user_id = @LeftUserId AND right_user_id = @RightUserId AND connection_status = N''active'';
            SET @NewState = N''blocked'';
            SET @EventKind = N''block'';
            SET @AdvanceBlockEpoch = 1;
        END
        ELSE IF @Command = N''unblock''
        BEGIN
            IF @ActorBlockId IS NULL OR @CurrentState <> N''blocked''
            BEGIN
                ROLLBACK TRANSACTION;
                SELECT CAST(0 AS bit) AS committed;
                RETURN;
            END;
            UPDATE dbo.user_blocks
            SET revoked_at_utc = SYSUTCDATETIME()
            WHERE user_block_id = @ActorBlockId AND revoked_at_utc IS NULL;
            SET @AnyActiveBlock = CASE WHEN EXISTS
            (
                SELECT 1 FROM dbo.user_blocks AS block_record WITH (UPDLOCK, HOLDLOCK)
                WHERE block_record.revoked_at_utc IS NULL
                  AND ((block_record.blocker_user_id = @ActorUserId AND block_record.blocked_user_id = @SubjectUserId)
                    OR (block_record.blocker_user_id = @SubjectUserId AND block_record.blocked_user_id = @ActorUserId))
            ) THEN 1 ELSE 0 END;
            SET @NewState = CASE WHEN @AnyActiveBlock = 1 THEN N''blocked'' ELSE N''none'' END;
            SET @EventKind = N''unblock'';
            SET @AdvanceBlockEpoch = 1;
        END
        ELSE
        BEGIN
            IF @AnyActiveBlock = 1 OR @CurrentState = N''blocked''
            BEGIN
                ROLLBACK TRANSACTION;
                SELECT CAST(0 AS bit) AS committed;
                RETURN;
            END;

            IF @Command = N''request''
            BEGIN
                IF @CurrentState NOT IN (N''none'', N''declined'', N''cancelled'', N''expired'')
                   AND @IsReciprocalPendingRequest = 0
                BEGIN
                    ROLLBACK TRANSACTION;
                    SELECT CAST(0 AS bit) AS committed;
                    RETURN;
                END;
                IF @IsReciprocalPendingRequest = 1
                BEGIN
                    UPDATE dbo.connection_requests
                    SET request_status = N''accepted'', responded_at_utc = SYSUTCDATETIME()
                    WHERE connection_request_id = @PendingRequestId AND request_status = N''pending'';
                    IF EXISTS (SELECT 1 FROM dbo.member_connections WITH (UPDLOCK, HOLDLOCK) WHERE left_user_id = @LeftUserId AND right_user_id = @RightUserId)
                        UPDATE dbo.member_connections
                        SET accepted_request_id = @PendingRequestId, connection_status = N''active'', connected_at_utc = SYSUTCDATETIME(), ended_at_utc = NULL
                        WHERE left_user_id = @LeftUserId AND right_user_id = @RightUserId;
                    ELSE
                        INSERT dbo.member_connections(left_user_id, right_user_id, accepted_request_id, connection_status)
                        VALUES (@LeftUserId, @RightUserId, @PendingRequestId, N''active'');
                    SET @NewState = N''connected'';
                    SET @EventKind = N''reciprocal_accept'';
                END
                ELSE IF @PendingRequestId IS NULL
                BEGIN
                    INSERT dbo.connection_requests(requester_user_id, recipient_user_id, request_status)
                    VALUES (@ActorUserId, @SubjectUserId, N''pending'');
                    SET @NewState = N''pending'';
                    SET @NewPendingRequesterId = @ActorUserId;
                    SET @EventKind = N''request'';
                END
                ELSE
                BEGIN
                    ROLLBACK TRANSACTION;
                    SELECT CAST(0 AS bit) AS committed;
                    RETURN;
                END;
            END
            ELSE IF @Command = N''reconnect''
            BEGIN
                IF @CurrentState <> N''disconnected'' OR @PendingRequestId IS NOT NULL
                BEGIN
                    ROLLBACK TRANSACTION;
                    SELECT CAST(0 AS bit) AS committed;
                    RETURN;
                END;
                INSERT dbo.connection_requests(requester_user_id, recipient_user_id, request_status)
                VALUES (@ActorUserId, @SubjectUserId, N''pending'');
                SET @NewState = N''pending'';
                SET @NewPendingRequesterId = @ActorUserId;
                SET @EventKind = N''reconnect'';
            END
            ELSE IF @Command = N''accept''
            BEGIN
                IF @CurrentState <> N''pending'' OR @CurrentPendingRequesterId <> @SubjectUserId
                   OR @PendingRequestId IS NULL OR @PendingRequesterId <> @SubjectUserId OR @PendingRecipientId <> @ActorUserId
                BEGIN
                    ROLLBACK TRANSACTION;
                    SELECT CAST(0 AS bit) AS committed;
                    RETURN;
                END;
                UPDATE dbo.connection_requests
                SET request_status = N''accepted'', responded_at_utc = SYSUTCDATETIME()
                WHERE connection_request_id = @PendingRequestId AND request_status = N''pending'';
                IF EXISTS (SELECT 1 FROM dbo.member_connections WITH (UPDLOCK, HOLDLOCK) WHERE left_user_id = @LeftUserId AND right_user_id = @RightUserId)
                    UPDATE dbo.member_connections
                    SET accepted_request_id = @PendingRequestId, connection_status = N''active'', connected_at_utc = SYSUTCDATETIME(), ended_at_utc = NULL
                    WHERE left_user_id = @LeftUserId AND right_user_id = @RightUserId;
                ELSE
                    INSERT dbo.member_connections(left_user_id, right_user_id, accepted_request_id, connection_status)
                    VALUES (@LeftUserId, @RightUserId, @PendingRequestId, N''active'');
                SET @NewState = N''connected'';
                SET @EventKind = N''accept'';
            END
            ELSE IF @Command = N''decline''
            BEGIN
                IF @CurrentState <> N''pending'' OR @CurrentPendingRequesterId <> @SubjectUserId
                   OR @PendingRequestId IS NULL OR @PendingRequesterId <> @SubjectUserId OR @PendingRecipientId <> @ActorUserId
                BEGIN
                    ROLLBACK TRANSACTION;
                    SELECT CAST(0 AS bit) AS committed;
                    RETURN;
                END;
                UPDATE dbo.connection_requests SET request_status = N''declined'', responded_at_utc = SYSUTCDATETIME()
                WHERE connection_request_id = @PendingRequestId AND request_status = N''pending'';
                SET @NewState = N''declined'';
                SET @EventKind = N''decline'';
            END
            ELSE IF @Command = N''cancel''
            BEGIN
                IF @CurrentState <> N''pending'' OR @CurrentPendingRequesterId <> @ActorUserId
                   OR @PendingRequestId IS NULL OR @PendingRequesterId <> @ActorUserId OR @PendingRecipientId <> @SubjectUserId
                BEGIN
                    ROLLBACK TRANSACTION;
                    SELECT CAST(0 AS bit) AS committed;
                    RETURN;
                END;
                UPDATE dbo.connection_requests SET request_status = N''cancelled'', responded_at_utc = SYSUTCDATETIME()
                WHERE connection_request_id = @PendingRequestId AND request_status = N''pending'';
                SET @NewState = N''cancelled'';
                SET @EventKind = N''cancel'';
            END
            ELSE IF @Command = N''expire''
            BEGIN
                IF @CurrentState <> N''pending'' OR @PendingRequestId IS NULL
                   OR @ActorUserId NOT IN (@PendingRequesterId, @PendingRecipientId)
                BEGIN
                    ROLLBACK TRANSACTION;
                    SELECT CAST(0 AS bit) AS committed;
                    RETURN;
                END;
                UPDATE dbo.connection_requests SET request_status = N''expired'', responded_at_utc = SYSUTCDATETIME()
                WHERE connection_request_id = @PendingRequestId AND request_status = N''pending'';
                SET @NewState = N''expired'';
                SET @EventKind = N''expire'';
            END
            ELSE IF @Command = N''disconnect''
            BEGIN
                IF @CurrentState <> N''connected''
                   OR NOT EXISTS
                   (
                       SELECT 1 FROM dbo.member_connections WITH (UPDLOCK, HOLDLOCK)
                       WHERE left_user_id = @LeftUserId AND right_user_id = @RightUserId AND connection_status = N''active''
                   )
                BEGIN
                    ROLLBACK TRANSACTION;
                    SELECT CAST(0 AS bit) AS committed;
                    RETURN;
                END;
                UPDATE dbo.member_connections
                SET connection_status = N''ended'', ended_at_utc = SYSUTCDATETIME()
                WHERE left_user_id = @LeftUserId AND right_user_id = @RightUserId AND connection_status = N''active'';
                SET @NewState = N''disconnected'';
                SET @EventKind = N''disconnect'';
            END;
        END;

        DECLARE @NextVersion bigint = @CurrentVersion + 1;
        DECLARE @NextBlockEpoch bigint = CASE
            WHEN @CurrentBlockEpoch = 0 THEN 1
            ELSE @CurrentBlockEpoch + CASE WHEN @AdvanceBlockEpoch = 1 THEN 1 ELSE 0 END
        END;
        DECLARE @NextEventSequence bigint = @CurrentEventSequence + 1;
        IF @RelationshipId IS NULL
        BEGIN
            INSERT dbo.connection_relationship_states
            (
                left_user_id, right_user_id, relationship_state, pending_requester_user_id,
                relationship_version, block_epoch, event_sequence
            )
            VALUES
            (
                @LeftUserId, @RightUserId, @NewState, @NewPendingRequesterId,
                @NextVersion, @NextBlockEpoch, @NextEventSequence
            );
            SET @RelationshipId = CONVERT(bigint, SCOPE_IDENTITY());
        END
        ELSE
        BEGIN
            UPDATE dbo.connection_relationship_states
            SET relationship_state = @NewState,
                pending_requester_user_id = @NewPendingRequesterId,
                relationship_version = @NextVersion,
                block_epoch = @NextBlockEpoch,
                event_sequence = @NextEventSequence,
                updated_at_utc = SYSUTCDATETIME()
            WHERE relationship_id = @RelationshipId;
        END;

        SET @AnyActiveBlock = CASE WHEN EXISTS
        (
            SELECT 1 FROM dbo.user_blocks AS block_record WITH (UPDLOCK, HOLDLOCK)
            WHERE block_record.revoked_at_utc IS NULL
              AND ((block_record.blocker_user_id = @ActorUserId AND block_record.blocked_user_id = @SubjectUserId)
                OR (block_record.blocker_user_id = @SubjectUserId AND block_record.blocked_user_id = @ActorUserId))
        ) THEN 1 ELSE 0 END;
        DECLARE @ResultState nvarchar(24) = CASE
            WHEN @NewState = N''pending'' AND @NewPendingRequesterId = @ActorUserId THEN N''outbound_pending''
            WHEN @NewState = N''pending'' THEN N''inbound_pending''
            ELSE @NewState
        END;

        INSERT dbo.connection_relationship_events
        (
            relationship_id, event_sequence, actor_user_id, subject_user_id, event_kind,
            relationship_version, block_epoch
        )
        VALUES
        (
            @RelationshipId, @NextEventSequence, @ActorUserId, @SubjectUserId, @EventKind,
            @NextVersion, @NextBlockEpoch
        );

        INSERT dbo.connection_relationship_commands
        (
            relationship_id, actor_user_id, subject_user_id, command_name,
            expected_relationship_version, idempotency_key, request_digest,
            result_state, result_relationship_version, result_block_epoch,
            result_blocked_either_direction
        )
        VALUES
        (
            @RelationshipId, @ActorUserId, @SubjectUserId, @Command,
            @ExpectedVersion, @IdempotencyKey, @RequestDigest,
            @ResultState, @NextVersion, @NextBlockEpoch, @AnyActiveBlock
        );
        DECLARE @NewCommandId bigint = CONVERT(bigint, SCOPE_IDENTITY());

        COMMIT TRANSACTION;
        SELECT CAST(1 AS bit) AS committed,
               CONVERT(nvarchar(36), command_record.command_key) AS command_key,
               actor_user.user_key AS actor_user_key,
               subject_user.user_key AS subject_user_key,
               command_record.command_name AS command,
               command_record.idempotency_key,
               command_record.request_digest,
               command_record.result_state AS state,
               CONCAT(N''rel_'', RIGHT(REPLICATE(N''0'', 20) + CONVERT(nvarchar(20), command_record.result_relationship_version), 20)) AS relationship_version,
               CONCAT(N''blk_'', RIGHT(REPLICATE(N''0'', 20) + CONVERT(nvarchar(20), command_record.result_block_epoch), 20)) AS block_epoch,
               command_record.result_blocked_either_direction AS blocked_either_direction
        FROM dbo.connection_relationship_commands AS command_record
        JOIN dbo.app_users AS actor_user ON actor_user.id = command_record.actor_user_id
        JOIN dbo.app_users AS subject_user ON subject_user.id = command_record.subject_user_id
        WHERE command_record.relationship_command_id = @NewCommandId;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
');

    EXEC(N'
CREATE OR ALTER PROCEDURE dbo.usp_GetConnectionRelationshipSnapshotForActor
    @ActorUserKey nvarchar(300),
    @SubjectUserKey nvarchar(300)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @ActorUserKey IS NULL OR @SubjectUserKey IS NULL
       OR LEN(@ActorUserKey) NOT BETWEEN 8 AND 128
       OR LEN(@SubjectUserKey) NOT BETWEEN 8 AND 128
       OR @ActorUserKey COLLATE Latin1_General_100_BIN2 LIKE N''%[^-A-Za-z0-9_]%''
       OR @SubjectUserKey COLLATE Latin1_General_100_BIN2 LIKE N''%[^-A-Za-z0-9_]%''
        RETURN;

    BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @ActorUserId int;
    DECLARE @SubjectUserId int;
    SELECT @ActorUserId = app_user.id
    FROM dbo.app_users AS app_user WITH (UPDLOCK, HOLDLOCK)
    WHERE app_user.user_key COLLATE Latin1_General_100_BIN2 = @ActorUserKey COLLATE Latin1_General_100_BIN2
      AND app_user.active = 1 AND app_user.account_status = N''active'';
    SELECT @SubjectUserId = app_user.id
    FROM dbo.app_users AS app_user WITH (UPDLOCK, HOLDLOCK)
    WHERE app_user.user_key COLLATE Latin1_General_100_BIN2 = @SubjectUserKey COLLATE Latin1_General_100_BIN2
      AND app_user.active = 1 AND app_user.account_status = N''active'';
    IF @ActorUserId IS NULL OR @SubjectUserId IS NULL OR @ActorUserId = @SubjectUserId
    BEGIN
        ROLLBACK TRANSACTION;
        RETURN;
    END;

    DECLARE @LeftUserId int = CASE WHEN @ActorUserId < @SubjectUserId THEN @ActorUserId ELSE @SubjectUserId END;
    DECLARE @RightUserId int = CASE WHEN @ActorUserId < @SubjectUserId THEN @SubjectUserId ELSE @ActorUserId END;
    DECLARE @State nvarchar(24);
    DECLARE @PendingRequesterUserId int;
    DECLARE @RelationshipVersion bigint;
    DECLARE @BlockEpoch bigint;
    SELECT @State = state_record.relationship_state,
           @PendingRequesterUserId = state_record.pending_requester_user_id,
           @RelationshipVersion = state_record.relationship_version,
           @BlockEpoch = state_record.block_epoch
    FROM dbo.connection_relationship_states AS state_record WITH (UPDLOCK, HOLDLOCK)
    WHERE state_record.left_user_id = @LeftUserId AND state_record.right_user_id = @RightUserId;
    IF @RelationshipVersion IS NULL
    BEGIN
        ROLLBACK TRANSACTION;
        RETURN;
    END;

    DECLARE @Blocked bit = CASE WHEN EXISTS
    (
        SELECT 1
        FROM dbo.user_blocks AS block_record WITH (UPDLOCK, HOLDLOCK)
        WHERE block_record.revoked_at_utc IS NULL
          AND ((block_record.blocker_user_id = @ActorUserId AND block_record.blocked_user_id = @SubjectUserId)
            OR (block_record.blocker_user_id = @SubjectUserId AND block_record.blocked_user_id = @ActorUserId))
    ) THEN 1 ELSE 0 END;
    COMMIT TRANSACTION;
    SELECT @ActorUserKey AS actor_user_key,
           @SubjectUserKey AS subject_user_key,
           CASE
             WHEN @Blocked = 1 THEN N''blocked''
             WHEN @State = N''pending'' AND @PendingRequesterUserId = @ActorUserId THEN N''outbound_pending''
             WHEN @State = N''pending'' THEN N''inbound_pending''
             ELSE @State
           END AS state,
           CONCAT(N''rel_'', RIGHT(REPLICATE(N''0'', 20) + CONVERT(nvarchar(20), @RelationshipVersion), 20)) AS relationship_version,
           CONCAT(N''blk_'', RIGHT(REPLICATE(N''0'', 20) + CONVERT(nvarchar(20), @BlockEpoch), 20)) AS block_epoch,
           @Blocked AS blocked_either_direction;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
');

    EXEC(N'
CREATE OR ALTER PROCEDURE dbo.usp_GetConnectionRelationshipCommandForActor
    @ActorUserKey nvarchar(300),
    @IdempotencyKey nvarchar(128)
AS
BEGIN
    SET NOCOUNT ON;

    IF @ActorUserKey IS NULL OR @IdempotencyKey IS NULL
       OR LEN(@ActorUserKey) NOT BETWEEN 8 AND 128
       OR @ActorUserKey COLLATE Latin1_General_100_BIN2 LIKE N''%[^-A-Za-z0-9_]%''
       OR LEN(@IdempotencyKey) NOT BETWEEN 8 AND 128
       OR @IdempotencyKey COLLATE Latin1_General_100_BIN2 LIKE N''%[^-A-Za-z0-9_]%''
        RETURN;

    SELECT TOP (1)
           CAST(1 AS bit) AS committed,
           CONVERT(nvarchar(36), command_record.command_key) AS command_key,
           actor_user.user_key AS actor_user_key,
           subject_user.user_key AS subject_user_key,
           command_record.command_name AS command,
           command_record.idempotency_key,
           command_record.request_digest,
           command_record.result_state AS state,
           CONCAT(N''rel_'', RIGHT(REPLICATE(N''0'', 20) + CONVERT(nvarchar(20), command_record.result_relationship_version), 20)) AS relationship_version,
           CONCAT(N''blk_'', RIGHT(REPLICATE(N''0'', 20) + CONVERT(nvarchar(20), command_record.result_block_epoch), 20)) AS block_epoch,
           command_record.result_blocked_either_direction AS blocked_either_direction
    FROM dbo.connection_relationship_commands AS command_record
    JOIN dbo.app_users AS actor_user
      ON actor_user.id = command_record.actor_user_id
     AND actor_user.active = 1 AND actor_user.account_status = N''active''
    JOIN dbo.app_users AS subject_user
      ON subject_user.id = command_record.subject_user_id
     AND subject_user.active = 1 AND subject_user.account_status = N''active''
    WHERE actor_user.user_key COLLATE Latin1_General_100_BIN2 = @ActorUserKey COLLATE Latin1_General_100_BIN2
      AND command_record.idempotency_key COLLATE Latin1_General_100_BIN2 = @IdempotencyKey COLLATE Latin1_General_100_BIN2;
END;
');

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CONNECT-002')
    BEGIN
        INSERT dbo.schema_migrations(migration_id, description, application_version)
        VALUES (N'PS-CONNECT-002', N'Additive pair-scoped relationship lifecycle, epochs, and idempotent Profile audience snapshots', N'PeerSlate PS-CONNECT-002');
        EXEC dbo.usp_AppendAuditEvent @ActionType = N'schema.migration.applied', @EntityType = N'database_migration', @Outcome = N'success', @MetadataJson = N'{"migration_id":"PS-CONNECT-002"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
