/*
PS-CONNECT-002 relationship isolation verification.

Run only against a disposable, explicitly selected database after the governed
migration gate has authorized it. This script reports structural evidence; it
does not apply, release, enable, or claim that any production database carries
the migration.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Verified bit = 1;
DECLARE @Failures table
(
    check_name nvarchar(160) NOT NULL,
    detail nvarchar(4000) NOT NULL
);

IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-PLAT-004')
BEGIN
    INSERT @Failures VALUES (N'prerequisite PS-PLAT-004', N'PS-PLAT-004 is not present in the target ledger.');
    SET @Verified = 0;
END;
IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-AUTH-001')
BEGIN
    INSERT @Failures VALUES (N'prerequisite PS-AUTH-001', N'PS-AUTH-001 is not present in the target ledger.');
    SET @Verified = 0;
END;
IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-CONNECT-002')
BEGIN
    INSERT @Failures VALUES (N'PS-CONNECT-002 ledger', N'PS-CONNECT-002 is not present in the target ledger.');
    SET @Verified = 0;
END;

DECLARE @ExpectedTables table (object_name sysname NOT NULL PRIMARY KEY);
INSERT @ExpectedTables VALUES
    (N'connection_relationship_states'),
    (N'connection_relationship_events'),
    (N'connection_relationship_commands');
IF EXISTS
(
    SELECT 1
    FROM @ExpectedTables AS expected
    WHERE OBJECT_ID(N'dbo.' + expected.object_name, N'U') IS NULL
)
BEGIN
    INSERT @Failures
    SELECT N'additive table', N'Missing dbo.' + expected.object_name
    FROM @ExpectedTables AS expected
    WHERE OBJECT_ID(N'dbo.' + expected.object_name, N'U') IS NULL;
    SET @Verified = 0;
END;

DECLARE @ExpectedProcedures table (object_name sysname NOT NULL PRIMARY KEY);
INSERT @ExpectedProcedures VALUES
    (N'usp_CommitConnectionRelationshipCommandForActor'),
    (N'usp_GetConnectionRelationshipSnapshotForActor'),
    (N'usp_GetConnectionRelationshipCommandForActor');
IF EXISTS
(
    SELECT 1
    FROM @ExpectedProcedures AS expected
    WHERE OBJECT_ID(N'dbo.' + expected.object_name, N'P') IS NULL
)
BEGIN
    INSERT @Failures
    SELECT N'foundation procedure', N'Missing dbo.' + expected.object_name
    FROM @ExpectedProcedures AS expected
    WHERE OBJECT_ID(N'dbo.' + expected.object_name, N'P') IS NULL;
    SET @Verified = 0;
END;

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.connection_relationship_commands')
      AND name = N'UQ_connection_relationship_commands_actor_idempotency'
      AND is_unique = 1
)
BEGIN
    INSERT @Failures VALUES
        (N'idempotency uniqueness', N'Missing unique actor/idempotency receipt fence.');
    SET @Verified = 0;
END;
IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.connection_relationship_events')
      AND name = N'UQ_connection_relationship_events_sequence'
      AND is_unique = 1
)
BEGIN
    INSERT @Failures VALUES
        (N'event ordering', N'Missing unique relationship/event sequence fence.');
    SET @Verified = 0;
END;

DECLARE @CommitDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitConnectionRelationshipCommandForActor'));
DECLARE @SnapshotDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetConnectionRelationshipSnapshotForActor'));
DECLARE @CommandDefinition nvarchar(max) = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_GetConnectionRelationshipCommandForActor'));
IF @CommitDefinition IS NULL OR @SnapshotDefinition IS NULL OR @CommandDefinition IS NULL
BEGIN
    INSERT @Failures VALUES (N'procedure definitions', N'Cannot inspect one or more PS-CONNECT-002 procedures.');
    SET @Verified = 0;
END
ELSE
BEGIN
    /* Exact binary keys avoid database-collation aliases; the pair applock and
       UPDLOCK, HOLDLOCK fence concurrent lifecycle command winners. */
    IF @CommitDefinition NOT LIKE N'%Latin1_General_100_BIN2%'
       OR @SnapshotDefinition NOT LIKE N'%Latin1_General_100_BIN2%'
       OR @CommandDefinition NOT LIKE N'%Latin1_General_100_BIN2%'
    BEGIN
        INSERT @Failures VALUES (N'binary identity fence', N'Missing Latin1_General_100_BIN2 key comparison.');
        SET @Verified = 0;
    END;
    IF @CommitDefinition NOT LIKE N'%sp_getapplock%'
       OR @CommitDefinition NOT LIKE N'%UPDLOCK, HOLDLOCK%'
       OR @CommitDefinition NOT LIKE N'%@ExistingCommandId IS NOT NULL%'
    BEGIN
        INSERT @Failures VALUES (N'concurrency and replay fence', N'Missing applock, lock hint, or stored-winner replay branch.');
        SET @Verified = 0;
    END;
    IF @SnapshotDefinition NOT LIKE N'%@ActorUserId = @SubjectUserId%'
       OR @SnapshotDefinition NOT LIKE N'%blocked_either_direction%'
       OR @CommandDefinition NOT LIKE N'%actor_user.user_key COLLATE Latin1_General_100_BIN2%'
    BEGIN
        INSERT @Failures VALUES (N'neutral pair retrieval fence', N'Missing actor/subject neutral absence or actor-scoped command lookup.');
        SET @Verified = 0;
    END;
END;

/* Exercise the reciprocal-request transition against real disposable state.
   The enclosing rollback keeps this verifier compatible with the gate's later
   rollback rehearsal while still proving the procedure branch is reachable. */
BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @VerifierActorKey nvarchar(64) = CONCAT(N'gateactor_', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''));
    DECLARE @VerifierSubjectKey nvarchar(64) = CONCAT(N'gatesubject-', REPLACE(CONVERT(nvarchar(36), NEWID()), N'-', N''));
    DECLARE @VerifierActorUserId int;
    DECLARE @VerifierSubjectUserId int;
    DECLARE @FirstVersion nvarchar(24);
    DECLARE @VerifierFirstDigest nvarchar(64) = REPLICATE(N'a', 64);
    DECLARE @VerifierSecondDigest nvarchar(64) = REPLICATE(N'b', 64);

    INSERT dbo.app_users(user_key, display_name)
    VALUES (@VerifierActorKey, N'PS-CONNECT gate actor');
    SET @VerifierActorUserId = CONVERT(int, SCOPE_IDENTITY());

    INSERT dbo.app_users(user_key, display_name)
    VALUES (@VerifierSubjectKey, N'PS-CONNECT gate subject');
    SET @VerifierSubjectUserId = CONVERT(int, SCOPE_IDENTITY());

    EXEC dbo.usp_CommitConnectionRelationshipCommandForActor
        @ActorUserKey = @VerifierActorKey,
        @SubjectUserKey = @VerifierSubjectKey,
        @Command = N'request',
        @ExpectedRelationshipVersion = NULL,
        @IdempotencyKey = N'gate_request_001',
        @RequestDigest = @VerifierFirstDigest;

    SELECT @FirstVersion = CONCAT(N'rel_', RIGHT(REPLICATE(N'0', 20) + CONVERT(nvarchar(20), state_record.relationship_version), 20))
    FROM dbo.connection_relationship_states AS state_record
    WHERE state_record.left_user_id = CASE WHEN @VerifierActorUserId < @VerifierSubjectUserId THEN @VerifierActorUserId ELSE @VerifierSubjectUserId END
      AND state_record.right_user_id = CASE WHEN @VerifierActorUserId < @VerifierSubjectUserId THEN @VerifierSubjectUserId ELSE @VerifierActorUserId END
      AND state_record.relationship_state = N'pending'
      AND state_record.pending_requester_user_id = @VerifierActorUserId;

    IF @FirstVersion IS NULL
    BEGIN
        INSERT @Failures VALUES (N'reciprocal request setup', N'Initial canonical pending request was not committed.');
        SET @Verified = 0;
    END
    ELSE
    BEGIN
        EXEC dbo.usp_CommitConnectionRelationshipCommandForActor
            @ActorUserKey = @VerifierSubjectKey,
            @SubjectUserKey = @VerifierActorKey,
            @Command = N'request',
            @ExpectedRelationshipVersion = @FirstVersion,
            @IdempotencyKey = N'gate-reciprocal-002',
            @RequestDigest = @VerifierSecondDigest;

        IF NOT EXISTS
        (
            SELECT 1
            FROM dbo.connection_relationship_states AS state_record
            JOIN dbo.connection_requests AS request_record
              ON request_record.requester_user_id = @VerifierActorUserId
             AND request_record.recipient_user_id = @VerifierSubjectUserId
             AND request_record.request_status = N'accepted'
            JOIN dbo.member_connections AS connection_record
              ON connection_record.left_user_id = state_record.left_user_id
             AND connection_record.right_user_id = state_record.right_user_id
             AND connection_record.connection_status = N'active'
             AND connection_record.accepted_request_id = request_record.connection_request_id
            WHERE state_record.left_user_id = CASE WHEN @VerifierActorUserId < @VerifierSubjectUserId THEN @VerifierActorUserId ELSE @VerifierSubjectUserId END
              AND state_record.right_user_id = CASE WHEN @VerifierActorUserId < @VerifierSubjectUserId THEN @VerifierSubjectUserId ELSE @VerifierActorUserId END
              AND state_record.relationship_state = N'connected'
              AND state_record.pending_requester_user_id IS NULL
              AND state_record.relationship_version = 2
        )
        BEGIN
            INSERT @Failures VALUES (N'reciprocal request transition', N'Opposite-direction request did not atomically accept the canonical pending request.');
            SET @Verified = 0;
        END;

        /* The SQL predicate must reject a dot while accepting the underscore
           and hyphen used by the successful commands above. If this malformed
           idempotency key were accepted, the otherwise-valid disconnect would
           mutate this disposable pair, which this check detects. */
        DECLARE @SecondVersion nvarchar(24);
        SELECT @SecondVersion = CONCAT(N'rel_', RIGHT(REPLICATE(N'0', 20) + CONVERT(nvarchar(20), state_record.relationship_version), 20))
        FROM dbo.connection_relationship_states AS state_record
        WHERE state_record.left_user_id = CASE WHEN @VerifierActorUserId < @VerifierSubjectUserId THEN @VerifierActorUserId ELSE @VerifierSubjectUserId END
          AND state_record.right_user_id = CASE WHEN @VerifierActorUserId < @VerifierSubjectUserId THEN @VerifierSubjectUserId ELSE @VerifierActorUserId END
          AND state_record.relationship_state = N'connected';

        IF @SecondVersion IS NULL
        BEGIN
            INSERT @Failures VALUES (N'opaque key predicate setup', N'Reciprocal acceptance did not leave an active pair for malformed-key refusal testing.');
            SET @Verified = 0;
        END
        ELSE
        BEGIN
            EXEC dbo.usp_CommitConnectionRelationshipCommandForActor
                @ActorUserKey = @VerifierActorKey,
                @SubjectUserKey = @VerifierSubjectKey,
                @Command = N'disconnect',
                @ExpectedRelationshipVersion = @SecondVersion,
                @IdempotencyKey = N'gate.invalid.004',
                @RequestDigest = @VerifierFirstDigest;

            IF NOT EXISTS
            (
                SELECT 1
                FROM dbo.connection_relationship_states AS state_record
                JOIN dbo.member_connections AS connection_record
                  ON connection_record.left_user_id = state_record.left_user_id
                 AND connection_record.right_user_id = state_record.right_user_id
                 AND connection_record.connection_status = N'active'
                WHERE state_record.left_user_id = CASE WHEN @VerifierActorUserId < @VerifierSubjectUserId THEN @VerifierActorUserId ELSE @VerifierSubjectUserId END
                  AND state_record.right_user_id = CASE WHEN @VerifierActorUserId < @VerifierSubjectUserId THEN @VerifierSubjectUserId ELSE @VerifierActorUserId END
                  AND state_record.relationship_state = N'connected'
                  AND NOT EXISTS
                  (
                      SELECT 1 FROM dbo.connection_relationship_commands AS command_record
                      WHERE command_record.idempotency_key = N'gate.invalid.004'
                  )
            )
            BEGIN
                INSERT @Failures VALUES (N'opaque key predicate refusal', N'Malformed idempotency key was not rejected before a valid disconnect could mutate the pair.');
                SET @Verified = 0;
            END;
        END;
    END;

    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
    DECLARE @ReciprocalLifecycleError nvarchar(4000) = ERROR_MESSAGE();
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    INSERT @Failures VALUES (N'reciprocal request execution', @ReciprocalLifecycleError);
    SET @Verified = 0;
END CATCH;

SELECT @Verified AS verified,
       CASE WHEN @Verified = 1 THEN N'PS-CONNECT-002 relationship isolation and reciprocal lifecycle checks passed; not a production gate.'
            ELSE N'PS-CONNECT-002 relationship isolation checks failed.' END AS summary;
SELECT check_name, detail FROM @Failures ORDER BY check_name;
