/* ============================================================
   PS-JOURNAL-001 (Slice J1 + J1.1) ROLLBACK - guarded removal of the
   derived Journal read, one-step Save Moment, and owner-authorized
   search

   Refuses to discard any member Moment-save replay record or any
   archived-lifecycle Moment. Removes only the objects PS-JOURNAL-001
   added: usp_ListJournalMomentsForOwner, usp_SaveMomentForOwner,
   usp_SearchJournalMomentsForOwner, dbo.moment_save_requests, and the
   two additive lifecycle columns on dbo.moments. It never touches
   dbo.moments, dbo.moment_versions, dbo.moment_sources, or
   dbo.captures rows themselves - those remain owned by
   PS-MOMENT-001/PS-CAPTURE-001.
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @JournalAppliedAtUtc datetime2(7);
    SELECT @JournalAppliedAtUtc = migration.applied_at_utc
    FROM dbo.schema_migrations AS migration WITH (UPDLOCK, HOLDLOCK)
    WHERE migration.migration_id = N'PS-JOURNAL-001';

    IF @JournalAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM dbo.schema_migrations AS migration
           WHERE migration.applied_at_utc > @JournalAppliedAtUtc
       )
        THROW 52730, 'Rollback blocked: a migration later than PS-JOURNAL-001 is present.', 1;

    DECLARE @ProcedureHashPropertyName sysname =
        N'PS_JOURNAL_001_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE
    (
        procedure_name sysname NOT NULL PRIMARY KEY
    );
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_ListJournalMomentsForOwner'),
        (N'usp_SaveMomentForOwner'),
        (N'usp_SearchJournalMomentsForOwner');

    IF @JournalAppliedAtUtc IS NOT NULL
       AND EXISTS
       (
           SELECT 1
           FROM @ProtectedProcedures AS protected_procedure
           LEFT JOIN sys.procedures AS procedure_object
             ON procedure_object.schema_id = SCHEMA_ID(N'dbo')
            AND procedure_object.name = protected_procedure.procedure_name
           LEFT JOIN sys.extended_properties AS property
             ON property.class = 1
            AND property.major_id = procedure_object.object_id
            AND property.minor_id = 0
            AND property.name = @ProcedureHashPropertyName
           WHERE procedure_object.object_id IS NULL
              OR property.major_id IS NULL
              OR CONVERT(nvarchar(64), property.value) <>
                 CONVERT
                 (
                     nvarchar(64),
                     HASHBYTES
                     (
                         'SHA2_256',
                         OBJECT_DEFINITION(procedure_object.object_id)
                     ),
                     2
                 )
       )
        THROW 52731, 'Rollback blocked: a protected procedure changed after PS-JOURNAL-001.', 1;

    IF OBJECT_ID(N'dbo.moment_save_requests', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.moment_save_requests)
        THROW 52732, 'Rollback blocked: moment_save_requests contains member replay records.', 1;

    IF COL_LENGTH(N'dbo.moments', N'archived_at_utc') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.moments WHERE archived_at_utc IS NOT NULL)
        THROW 52733, 'Rollback blocked: an owner has an archived Moment in this column.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.foreign_keys AS foreign_key
        WHERE foreign_key.referenced_object_id = OBJECT_ID(N'dbo.moment_save_requests')
          AND foreign_key.parent_object_id <> OBJECT_ID(N'dbo.moment_save_requests')
    )
        THROW 52734, 'Rollback blocked: a later table depends on moment_save_requests.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.sql_expression_dependencies AS dependency
        WHERE
        (
            dependency.referenced_id = OBJECT_ID(N'dbo.moment_save_requests')
            OR dependency.referenced_id = OBJECT_ID(N'dbo.usp_ListJournalMomentsForOwner')
            OR dependency.referenced_id = OBJECT_ID(N'dbo.usp_SaveMomentForOwner')
            OR dependency.referenced_id = OBJECT_ID(N'dbo.usp_SearchJournalMomentsForOwner')
        )
          AND dependency.referencing_id NOT IN
          (
              OBJECT_ID(N'dbo.usp_ListJournalMomentsForOwner'),
              OBJECT_ID(N'dbo.usp_SaveMomentForOwner'),
              OBJECT_ID(N'dbo.usp_SearchJournalMomentsForOwner')
          )
          AND dependency.referencing_id <> OBJECT_ID(N'dbo.moment_save_requests')
    )
        THROW 52735, 'Rollback blocked: a later programmable object depends on PS-JOURNAL-001.', 1;

    IF OBJECT_ID(N'dbo.usp_ListJournalMomentsForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ListJournalMomentsForOwner;
    IF OBJECT_ID(N'dbo.usp_SaveMomentForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SaveMomentForOwner;
    IF OBJECT_ID(N'dbo.usp_SearchJournalMomentsForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_SearchJournalMomentsForOwner;

    IF OBJECT_ID(N'dbo.moment_save_requests', N'U') IS NOT NULL
        DROP TABLE dbo.moment_save_requests;

    IF EXISTS
    (
        SELECT 1 FROM sys.check_constraints
        WHERE name = N'CK_moments_archive_pair'
          AND parent_object_id = OBJECT_ID(N'dbo.moments')
    )
        ALTER TABLE dbo.moments DROP CONSTRAINT CK_moments_archive_pair;

    IF EXISTS
    (
        SELECT 1 FROM sys.foreign_keys
        WHERE name = N'FK_moments_archived_by'
          AND parent_object_id = OBJECT_ID(N'dbo.moments')
    )
        ALTER TABLE dbo.moments DROP CONSTRAINT FK_moments_archived_by;

    IF COL_LENGTH(N'dbo.moments', N'archived_by_user_id') IS NOT NULL
        ALTER TABLE dbo.moments DROP COLUMN archived_by_user_id;

    IF COL_LENGTH(N'dbo.moments', N'archived_at_utc') IS NOT NULL
        ALTER TABLE dbo.moments DROP COLUMN archived_at_utc;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NOT NULL
       AND EXISTS
       (
           SELECT 1 FROM dbo.schema_migrations
           WHERE migration_id = N'PS-JOURNAL-001'
       )
    BEGIN
        EXEC dbo.usp_AppendAuditEvent
            @ActionType = N'schema.migration.rolled_back',
            @EntityType = N'database_migration',
            @Outcome = N'success',
            @MetadataJson = N'{"migration_id":"PS-JOURNAL-001"}';

        DELETE dbo.schema_migrations
        WHERE migration_id = N'PS-JOURNAL-001';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
