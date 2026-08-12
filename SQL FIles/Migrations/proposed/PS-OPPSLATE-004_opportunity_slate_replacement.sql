/* ============================================================
   PS-OPPSLATE-004 - Opportunity Slate replacement R1 additive schema

   Package: docs/initiatives/PS-OPPORTUNITY-SLATE-002. Controlling contract:
   artifacts/2026-08-11-opportunity-slate-architecture/
   OPPORTUNITY_SLATE_ARCHITECTURE.md, sections 5.1-5.3 (data architecture),
   6.1 (source capture), 6.10 (authorization boundaries), 9 (route/service
   contract), 14 "R1" (implementation sequence).

   This is the first schema delta for the Opportunity Slate REPLACEMENT
   experience (owner decision 2026-08-11: replace, not evolve). It ships
   beside PS-OPPSLATE-001/002/003, which stay production truth for the
   legacy room, byte-for-byte, forever. Nothing below drops, alters the
   shape of, or mutates a row in any 001-003 table.

   R1 SCOPE (shell + stage-1 intake + stage-2 captured-source review) adds
   exactly one new table this slice's application code writes to:

     dbo.opportunity_source_identities   member-entered employer/role-title
                                          metadata, one row per source
                                          version (image 05 section A).

   and two more new tables whose SHAPE this migration proves once, per the
   architecture's explicit instruction that "tables 2-3 are consumed by R2
   but gate-proofed once here" (section 14, R1). Their PROCEDURES are
   deliberately NOT created by this migration -- see the note below the
   table DDL. No R1 route or service touches either table:

     dbo.opportunity_requirement_review_events   R2 (requirement review,
                                                   image 06)
     dbo.opportunity_member_takes                 R2 (qualification "Your
                                                   take" + response, images
                                                   01-03/07-11)

   and three nullable, additive columns R2's currency model will need
   (section 6.5/6.5a): two on dbo.opportunity_analyses
   (evidence_snapshot_sha256, confirmed_requirements_ordinal) and one on
   dbo.opportunity_requirement_sets (member_confirmed_ordinal). All three
   are NULL on every existing row and change nothing about how a 001-003
   procedure reads or writes those tables. Their CHECK constraints are
   intentionally added WITH NOCHECK: the production migration identity has
   ALTER but no SELECT on protected member tables, and WITH CHECK would scan
   historical rows and fail that least-privilege boundary. Because the three
   columns are created nullable in this same transaction, every historical
   value is already NULL. SQL Server still enforces each enabled constraint
   on later INSERT/UPDATE operations; the catalog records them as untrusted
   only because old rows were deliberately not scanned.

   DEFERRED PROCEDURES, DELIBERATELY. Section 5.2 of the architecture also
   sketches usp_SaveOpportunityRequirementReviewForOwner,
   usp_ConfirmOpportunityRequirementsForOwnerR,
   usp_ReviseOpportunityRequirementsForOwner,
   usp_SaveOpportunityMemberTakeForOwner,
   usp_ReviewOpportunityMemberResponseForOwner,
   usp_ContinueOpportunityQualificationForOwner,
   usp_SaveOpportunityAnalysisForOwnerR, and
   usp_GetOpportunityRoomForOwnerR. The R1 delegation brief is explicit --
   "Build NOTHING beyond R1: ... no requirement review, no alignment, no
   save/history" -- and every one of those eight procedures IS requirement
   review, alignment, or save/history at the data layer, with zero R1
   caller to prove its contract against. Writing eight untested, unexercised
   owner-scoped mutating procedures now, against contracts that only
   solidify once R2's route/service code exists, is exactly the speculative
   surface PeerSlate's lean-delivery policy (docs/AI_WORKFLOW.md) warns
   against. The tables and columns those procedures will eventually write
   to are created NOW, so R2 needs no further ALTER; R2 adds only its own
   procedures, via its own small additive migration -- the same pattern
   PS-OPPSLATE-002 (OS-3) used to add OS-3's procedures on top of the
   OS-1/OS-2 tables PS-OPPSLATE-001 had already shipped.

   PROCEDURE TAKEOVER, HASH-STAMPED. usp_PurgeExpiredOpportunityWorkingData
   and usp_DeleteOpportunityWorkingSessionForOwner both cascade-delete an
   owner's ephemeral working data, and both now have to learn about
   opportunity_source_identities, opportunity_requirement_review_events, and
   opportunity_member_takes, or a purge/delete would leave orphaned v2 rows
   referencing an about-to-be-deleted parent and the FK would refuse the
   parent delete. This migration CREATE OR ALTERs both procedures --
   inserting exactly one new DELETE block per new table, at the correct
   position in each procedure's existing dependency order -- and re-stamps
   both with a PS_OPPSLATE_004_DEFINITION_HASH extended property, exactly
   as PS-OPPSLATE-002 did when OS-3 first took these same two procedures
   over from OS-1. The PS_OPPSLATE_002_DEFINITION_HASH stamp already on
   both procedures is left in place (now describing a superseded body, not
   the live one) so a chain rollback can still find and verify it; this
   migration's own rollback restores the OS-3 body and hash exactly, so the
   chain stays reversible in sequence. No other procedure in this file
   revises an existing definition; every other object below is new.

   STILL NO SCORE. Not one column below holds an aggregate, a percentage, a
   ranking, a recommendation, or an employer prediction, and none may ever
   be added.

   R1 has no AI call anywhere. Nothing in this migration is read by an AI
   prompt or a validator; opportunity_requirement_review_events and
   opportunity_member_takes are both pure member-authored truth (Section
   5.3), never written by an AI path.

   A missing or partial PS-OPPSLATE-001/002/003 baseline fails before the
   first mutation. It never updates or reuses a PS-OPPSLATE-001/002/003
   ledger row and inserts only its own.

   Rollback: PS-OPPSLATE-004_opportunity_slate_replacement_rollback.sql
   Verification: ../../Verification/PS-OPPSLATE-004_owner_isolation_verify.sql
   ============================================================ */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
        THROW 53800, 'PS-OPPSLATE-004 requires the migration ledger.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                   WHERE migration_id = N'PS-OPPSLATE-001')
        THROW 53801, 'PS-OPPSLATE-001 must be applied before PS-OPPSLATE-004.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                   WHERE migration_id = N'PS-OPPSLATE-002')
        THROW 53802, 'PS-OPPSLATE-002 must be applied before PS-OPPSLATE-004.', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
                   WHERE migration_id = N'PS-OPPSLATE-003')
        THROW 53803, 'PS-OPPSLATE-003 must be applied before PS-OPPSLATE-004.', 1;

    DECLARE @RequiredBaselineObjects TABLE
        (object_name nvarchar(300) NOT NULL, object_type char(1) NOT NULL);
    INSERT @RequiredBaselineObjects (object_name, object_type)
    VALUES
        (N'dbo.opportunity_working_sessions', N'U'),
        (N'dbo.opportunity_sources', N'U'),
        (N'dbo.opportunity_source_versions', N'U'),
        (N'dbo.opportunity_source_reviews', N'U'),
        (N'dbo.opportunity_source_concerns', N'U'),
        (N'dbo.opportunity_requirement_sets', N'U'),
        (N'dbo.opportunity_requirement_set_versions', N'U'),
        (N'dbo.opportunity_requirement_statements', N'U'),
        (N'dbo.opportunity_analyses', N'U'),
        (N'dbo.opportunity_analysis_statements', N'U'),
        (N'dbo.opportunity_analysis_citations', N'U'),
        (N'dbo.opportunity_responses', N'U'),
        (N'dbo.opportunity_slates', N'U'),
        (N'dbo.opportunity_saved_results', N'U'),
        (N'dbo.opportunity_saved_qualifications', N'U'),
        (N'dbo.opportunity_saved_evidence', N'U'),
        (N'dbo.usp_PurgeExpiredOpportunityWorkingData', N'P'),
        (N'dbo.usp_GetOpportunityWorkingSessionForOwner', N'P'),
        (N'dbo.usp_SaveOpportunitySourceForOwner', N'P'),
        (N'dbo.usp_CorrectOpportunitySourceForOwner', N'P'),
        (N'dbo.usp_ConfirmOpportunitySourceForOwner', N'P'),
        (N'dbo.usp_DeleteOpportunityWorkingSessionForOwner', N'P'),
        (N'dbo.usp_ConfirmOpportunityRequirementsForOwner', N'P'),
        (N'dbo.usp_SaveOpportunityAnalysisForOwner', N'P');
    IF EXISTS (SELECT 1 FROM @RequiredBaselineObjects
               WHERE OBJECT_ID(object_name, object_type) IS NULL)
        THROW 53804, 'PS-OPPSLATE-001/002/003 does not match the required baseline.', 1;

    IF COL_LENGTH(N'dbo.opportunity_analyses', N'opportunity_analysis_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_requirement_sets', N'opportunity_requirement_set_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_requirement_statements', N'opportunity_requirement_statement_id') IS NULL
       OR COL_LENGTH(N'dbo.opportunity_source_versions', N'opportunity_source_version_id') IS NULL
        THROW 53807, 'PS-OPPSLATE-001/002/003 does not match the required baseline.', 1;

    DECLARE @MigrationAlreadyApplied bit = CASE WHEN EXISTS
        (SELECT 1 FROM dbo.schema_migrations WITH (UPDLOCK, HOLDLOCK)
         WHERE migration_id = N'PS-OPPSLATE-004') THEN 1 ELSE 0 END;
    DECLARE @OwnershipPropertyName sysname = N'PS_OPPSLATE_004_OWNED';
    DECLARE @Os5Objects TABLE
        (object_name nvarchar(300) NOT NULL, object_type char(1) NOT NULL);
    INSERT @Os5Objects (object_name, object_type)
    VALUES
        (N'dbo.opportunity_source_identities', N'U'),
        (N'dbo.opportunity_requirement_review_events', N'U'),
        (N'dbo.opportunity_member_takes', N'U'),
        (N'dbo.usp_SaveOpportunitySourceIdentityForOwner', N'P'),
        (N'dbo.usp_GetOpportunitySourceIdentityForOwner', N'P');
    DECLARE @ExistingOs5ObjectCount int =
        (SELECT COUNT(*) FROM @Os5Objects WHERE OBJECT_ID(object_name, object_type) IS NOT NULL);
    DECLARE @OwnedColumnCount int =
        (CASE WHEN COL_LENGTH(N'dbo.opportunity_analyses', N'evidence_snapshot_sha256') IS NULL THEN 0 ELSE 1 END)
      + (CASE WHEN COL_LENGTH(N'dbo.opportunity_analyses', N'confirmed_requirements_ordinal') IS NULL THEN 0 ELSE 1 END)
      + (CASE WHEN COL_LENGTH(N'dbo.opportunity_requirement_sets', N'member_confirmed_ordinal') IS NULL THEN 0 ELSE 1 END);
    DECLARE @OwnedConstraintCount int =
        (SELECT COUNT(*) FROM sys.check_constraints
         WHERE name IN
         (
             N'CK_opportunity_analyses_evidence_snapshot_hash',
             N'CK_opportunity_analyses_confirmed_ordinal',
             N'CK_opportunity_requirement_sets_member_confirmed_ordinal'
         ));

    /* Never adopt a name-compatible object or additive column that this
       migration did not create. An unapplied ledger plus any owned surface
       is a dirty partial state and fails before the first mutation. */
    IF @MigrationAlreadyApplied = 0
       AND (@ExistingOs5ObjectCount > 0 OR @OwnedColumnCount > 0 OR @OwnedConstraintCount > 0)
        THROW 53805, 'A partial PS-OPPSLATE-004 schema exists without an applied migration; no existing object or column will be adopted.', 1;

    /* Reapply is allowed only for the exact recorded surface and only when
       every independently droppable table/column carries this migration's
       ownership stamp. */
    IF @MigrationAlreadyApplied = 1
    BEGIN
        IF @ExistingOs5ObjectCount <> 5 OR @OwnedColumnCount <> 3
            THROW 53808, 'Recorded PS-OPPSLATE-004 schema is incomplete or drifted.', 1;
        IF EXISTS
        (
            SELECT 1
            FROM (VALUES
                (N'opportunity_source_identities'),
                (N'opportunity_requirement_review_events'),
                (N'opportunity_member_takes')
            ) AS owned(table_name)
            LEFT JOIN sys.tables AS table_record
              ON table_record.schema_id = SCHEMA_ID(N'dbo')
             AND table_record.name = owned.table_name
            LEFT JOIN sys.extended_properties AS property_record
              ON property_record.class = 1
             AND property_record.major_id = table_record.object_id
             AND property_record.minor_id = 0
             AND property_record.name = @OwnershipPropertyName
            WHERE property_record.major_id IS NULL
        )
            THROW 53809, 'Recorded PS-OPPSLATE-004 table ownership stamp is missing.', 1;
        IF EXISTS
        (
            SELECT 1
            FROM (VALUES
                (N'opportunity_analyses', N'evidence_snapshot_sha256'),
                (N'opportunity_analyses', N'confirmed_requirements_ordinal'),
                (N'opportunity_requirement_sets', N'member_confirmed_ordinal')
            ) AS owned(table_name, column_name)
            JOIN sys.tables AS table_record
              ON table_record.schema_id = SCHEMA_ID(N'dbo')
             AND table_record.name = owned.table_name
            JOIN sys.columns AS column_record
              ON column_record.object_id = table_record.object_id
             AND column_record.name = owned.column_name
            LEFT JOIN sys.extended_properties AS property_record
              ON property_record.class = 1
             AND property_record.major_id = table_record.object_id
             AND property_record.minor_id = column_record.column_id
             AND property_record.name = @OwnershipPropertyName
            WHERE property_record.major_id IS NULL
        )
            THROW 53810, 'Recorded PS-OPPSLATE-004 column ownership stamp is missing.', 1;
    END;

    /* ------------------------------------------------------------
       1. dbo.opportunity_source_identities (image 05 section A).

       One row per source version; member-entered; kept entirely apart from
       the write-once employer wording on opportunity_source_versions and
       from the AI proposal columns nothing in this room ever populates for
       identity (there is no AI step over identity in R1 -- see the
       architecture's decision D-6). Correcting it does not create a source
       version and does not clear the source's confirmation triple: it is
       member metadata, not employer wording (section 6.1).
       ------------------------------------------------------------ */

    IF OBJECT_ID(N'dbo.opportunity_source_identities', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_source_identities
        (
            opportunity_source_identity_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_source_version_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            employer_name nvarchar(200) NULL,
            role_title nvarchar(200) NULL,
            /* The whole vocabulary today is "job posting" (image 05's
               "Source type -- Job posting" meta row). Hard-CHECK-pinned
               rather than defaulted only, exactly like
               opportunity_working_sessions.visibility, so a future source
               kind cannot silently appear without a schema decision. */
            source_type nvarchar(30) NOT NULL
                CONSTRAINT DF_opportunity_source_identities_type DEFAULT N'job_posting',
            entered_by_user_id int NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_source_identities_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_source_identities_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_source_identities PRIMARY KEY (opportunity_source_identity_id),
            /* One identity row per source version -- a replaced source
               (new version) gets a fresh, empty identity, never a copy
               forward, so a member is never shown a stale employer/role
               title pair against wording they have not yet reviewed. */
            CONSTRAINT UQ_opportunity_source_identities_version
                UNIQUE (opportunity_source_version_id),
            CONSTRAINT UQ_opportunity_source_identities_id_owner
                UNIQUE (opportunity_source_identity_id, owner_profile_id),
            CONSTRAINT FK_opportunity_source_identities_version FOREIGN KEY
                (opportunity_source_version_id, owner_profile_id)
                REFERENCES dbo.opportunity_source_versions
                           (opportunity_source_version_id, owner_profile_id),
            CONSTRAINT FK_opportunity_source_identities_enterer FOREIGN KEY (entered_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_source_identities_type CHECK
                (source_type IN (N'job_posting')),
            CONSTRAINT CK_opportunity_source_identities_employer_length CHECK
                (employer_name IS NULL OR DATALENGTH(employer_name) / 2 BETWEEN 1 AND 200),
            CONSTRAINT CK_opportunity_source_identities_role_length CHECK
                (role_title IS NULL OR DATALENGTH(role_title) / 2 BETWEEN 1 AND 200)
        );
    END;

    /* ------------------------------------------------------------
       2. dbo.opportunity_requirement_review_events (image 06 section C +
          correction inspector). SHAPE ONLY in this slice -- see the file
          header. Append-only: the latest event per statement is the
          current review decision, and the full correction history falls
          out of the event stream for free (architecture section 6.2).
       ------------------------------------------------------------ */

    IF OBJECT_ID(N'dbo.opportunity_requirement_review_events', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_requirement_review_events
        (
            opportunity_requirement_review_event_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_requirement_statement_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            event_ordinal int NOT NULL,
            review_decision nvarchar(30) NOT NULL,
            /* A correction payload travels only with a needs_correction
               decision -- CK_..._payload below. */
            corrected_organized_text nvarchar(1200) NULL,
            corrected_class nvarchar(40) NULL,
            decided_by_user_id int NOT NULL,
            decided_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_requirement_review_events_decided DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_opportunity_requirement_review_events PRIMARY KEY (opportunity_requirement_review_event_id),
            CONSTRAINT UQ_opportunity_requirement_review_events_ordinal
                UNIQUE (opportunity_requirement_statement_id, event_ordinal),
            CONSTRAINT UQ_opportunity_requirement_review_events_id_owner
                UNIQUE (opportunity_requirement_review_event_id, owner_profile_id),
            CONSTRAINT FK_opportunity_requirement_review_events_statement FOREIGN KEY
                (opportunity_requirement_statement_id, owner_profile_id)
                REFERENCES dbo.opportunity_requirement_statements
                           (opportunity_requirement_statement_id, owner_profile_id),
            CONSTRAINT FK_opportunity_requirement_review_events_decider FOREIGN KEY (decided_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_requirement_review_events_ordinal CHECK (event_ordinal > 0),
            CONSTRAINT CK_opportunity_requirement_review_events_decision CHECK
                (review_decision IN (N'accurate', N'needs_correction', N'not_a_requirement')),
            CONSTRAINT CK_opportunity_requirement_review_events_class CHECK
                (corrected_class IS NULL OR corrected_class IN
                    (N'required_qualification', N'preferred_qualification',
                     N'responsibility', N'informational_statement')),
            CONSTRAINT CK_opportunity_requirement_review_events_text_length CHECK
                (corrected_organized_text IS NULL
                 OR DATALENGTH(corrected_organized_text) / 2 BETWEEN 1 AND 1200),
            CONSTRAINT CK_opportunity_requirement_review_events_payload CHECK
            (
                (review_decision = N'needs_correction')
                OR (corrected_organized_text IS NULL AND corrected_class IS NULL)
            )
        );
    END;

    /* ------------------------------------------------------------
       3. dbo.opportunity_member_takes (images 01/02/03 sections B and C).
          SHAPE ONLY in this slice -- see the file header. One current row
          per qualification; the NEW experience's take + own-words
          response. The old five-kind opportunity_responses table is
          untouched and stays exactly as PS-OPPSLATE-001/002 left it
          (architecture section 5.2 table 3 / section 11).
       ------------------------------------------------------------ */

    IF OBJECT_ID(N'dbo.opportunity_member_takes', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.opportunity_member_takes
        (
            opportunity_member_take_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_requirement_statement_id bigint NOT NULL,
            owner_profile_id bigint NOT NULL,
            take nvarchar(30) NULL,
            response_text nvarchar(max) NULL,
            authored_via nvarchar(30) NOT NULL
                CONSTRAINT DF_opportunity_member_takes_authored DEFAULT N'typed',
            /* Explicit member commit of the free-text response (section
               6.4's "Response reviewed" control); NULL until the member
               reviews it, and cleared again by any edit after that. */
            response_reviewed_at_utc datetime2(7) NULL,
            /* Set by "Continue to next qualification"; never unset by
               "Back" or by free navigation (section 6.7). */
            alignment_continued_at_utc datetime2(7) NULL,
            created_by_user_id int NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_member_takes_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_opportunity_member_takes_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_opportunity_member_takes PRIMARY KEY (opportunity_member_take_id),
            CONSTRAINT UQ_opportunity_member_takes_statement
                UNIQUE (opportunity_requirement_statement_id),
            CONSTRAINT UQ_opportunity_member_takes_id_owner
                UNIQUE (opportunity_member_take_id, owner_profile_id),
            CONSTRAINT FK_opportunity_member_takes_statement FOREIGN KEY
                (opportunity_requirement_statement_id, owner_profile_id)
                REFERENCES dbo.opportunity_requirement_statements
                           (opportunity_requirement_statement_id, owner_profile_id),
            CONSTRAINT FK_opportunity_member_takes_author FOREIGN KEY (created_by_user_id)
                REFERENCES dbo.app_users(id),
            CONSTRAINT CK_opportunity_member_takes_take CHECK
                (take IS NULL OR take IN (N'done_this', N'done_related', N'not_yet')),
            /* DATALENGTH/2 BETWEEN 1 AND 4000 already refuses an empty
               non-NULL string, so a member cannot "commit" a blank
               response and have it read as reviewed. */
            CONSTRAINT CK_opportunity_member_takes_response_length CHECK
                (response_text IS NULL OR DATALENGTH(response_text) / 2 BETWEEN 1 AND 4000),
            CONSTRAINT CK_opportunity_member_takes_authored CHECK
                (authored_via IN (N'typed', N'dictated')),
            CONSTRAINT CK_opportunity_member_takes_reviewed_pair CHECK
                (response_reviewed_at_utc IS NULL OR response_text IS NOT NULL)
        );
    END;

    /* ------------------------------------------------------------
       4. Analysis currency columns (architecture sections 6.5, 6.5a).
          Nullable and additive; every existing opportunity_analyses row
          stays NULL and is simply treated by R2 as "not current" until a
          new analysis run populates them. No existing procedure changes.
       ------------------------------------------------------------ */

    IF COL_LENGTH(N'dbo.opportunity_analyses', N'evidence_snapshot_sha256') IS NULL
        EXEC(N'ALTER TABLE dbo.opportunity_analyses ADD evidence_snapshot_sha256 char(64) NULL;');
    IF COL_LENGTH(N'dbo.opportunity_analyses', N'confirmed_requirements_ordinal') IS NULL
        EXEC(N'ALTER TABLE dbo.opportunity_analyses ADD confirmed_requirements_ordinal int NULL;');

    /* Do not change these three existing-table constraints to WITH CHECK.
       peerslate-ado-schema intentionally cannot SELECT protected member rows,
       so validating historical rows would reproduce governed production run
       836's permission failure. The nullable columns above are new in this
       transaction and therefore NULL on every old row. WITH NOCHECK skips only
       that historical scan; each enabled constraint still rejects invalid
       future INSERT/UPDATE values. The verifier pins enabled + untrusted. */
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints
                   WHERE name = N'CK_opportunity_analyses_evidence_snapshot_hash')
        EXEC(N'ALTER TABLE dbo.opportunity_analyses WITH NOCHECK ADD
                  CONSTRAINT CK_opportunity_analyses_evidence_snapshot_hash CHECK
                  (evidence_snapshot_sha256 IS NULL OR evidence_snapshot_sha256 NOT LIKE N''%[^0-9a-f]%'');');
    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints
                   WHERE name = N'CK_opportunity_analyses_confirmed_ordinal')
        EXEC(N'ALTER TABLE dbo.opportunity_analyses WITH NOCHECK ADD
                  CONSTRAINT CK_opportunity_analyses_confirmed_ordinal CHECK
                  (confirmed_requirements_ordinal IS NULL OR confirmed_requirements_ordinal > 0);');

    /* ------------------------------------------------------------
       5. Requirement-set confirmation ordinal (architecture section 6.5a).
          Bumped by a future "Confirm requirements"; lets a post-confirm
          revision supersede an analysis without a new set version. Old
          rows stay NULL, which R2 treats as ordinal 1 on first confirm.
       ------------------------------------------------------------ */

    IF COL_LENGTH(N'dbo.opportunity_requirement_sets', N'member_confirmed_ordinal') IS NULL
        EXEC(N'ALTER TABLE dbo.opportunity_requirement_sets ADD member_confirmed_ordinal int NULL;');

    IF NOT EXISTS (SELECT 1 FROM sys.check_constraints
                   WHERE name = N'CK_opportunity_requirement_sets_member_confirmed_ordinal')
        EXEC(N'ALTER TABLE dbo.opportunity_requirement_sets WITH NOCHECK ADD
                  CONSTRAINT CK_opportunity_requirement_sets_member_confirmed_ordinal CHECK
                  (member_confirmed_ordinal IS NULL OR member_confirmed_ordinal > 0);');

    /* ------------------------------------------------------------
       6. usp_SaveOpportunitySourceIdentityForOwner (image 05 section A).

       Fenced on the SAME opportunity_sources.row_version token the room
       already hands the client for corrections/confirm (WorkingSourceView.
       source_version_token) -- no new concurrency token is invented.
       Resolves the source''s CURRENT version and upserts exactly one
       identity row for it. Never creates a source version, never touches
       original_text, and never clears the source''s confirmation triple.
       An accepted upsert advances updated_at_utc so the shared rowversion
       fences the next identity/correction/confirm write. Identity remains
       member metadata, not employer wording (section 6.1).
       ------------------------------------------------------------ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_SaveOpportunitySourceIdentityForOwner
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier,
            @ExpectedRowVersion binary(8),
            @EmployerName nvarchar(200) = NULL,
            @RoleTitle nvarchar(200) = NULL
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            SET @EmployerName = NULLIF(LTRIM(RTRIM(@EmployerName)), N'''');
            SET @RoleTitle = NULLIF(LTRIM(RTRIM(@RoleTitle)), N'''');

            IF @UserKey IS NULL OR @SourceKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version;
                RETURN;
            END;

            IF (@EmployerName IS NOT NULL AND DATALENGTH(@EmployerName) / 2 > 200)
               OR (@RoleTitle IS NOT NULL AND DATALENGTH(@RoleTitle) / 2 > 200)
            BEGIN
                SELECT N''invalid'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            DECLARE @UserId int;
            SELECT @ProfileId = profile.profile_id, @UserId = app_user.id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version;
                RETURN;
            END;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @SourceId bigint;
            DECLARE @VersionId bigint;
            DECLARE @NewSourceRowVersion binary(8);

            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT @SourceId = source_record.opportunity_source_id
                FROM dbo.opportunity_sources AS source_record WITH (UPDLOCK, HOLDLOCK)
                JOIN dbo.opportunity_working_sessions AS working_session
                  ON working_session.working_session_id = source_record.working_session_id
                 AND working_session.owner_profile_id = source_record.owner_profile_id
                WHERE source_record.source_key = @SourceKey
                  AND source_record.owner_profile_id = @ProfileId
                  AND source_record.row_version = @ExpectedRowVersion
                  AND working_session.expires_at_utc > @Now;

                /* A missing, foreign, expired, or stale-version source all
                   resolve to the same neutral ''changed'' outcome, so the
                   response can never confirm whether another member''s key
                   exists (the usp_CorrectOpportunitySourceForOwner rule). */
                IF @SourceId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS binary(8)) AS source_row_version;
                    RETURN;
                END;

                SELECT @VersionId = version_record.opportunity_source_version_id
                FROM dbo.opportunity_source_versions AS version_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = version_record.opportunity_source_id
                 AND source_record.owner_profile_id = version_record.owner_profile_id
                WHERE version_record.opportunity_source_id = @SourceId
                  AND version_record.owner_profile_id = @ProfileId
                  AND version_record.version_number = source_record.current_version_number;

                UPDATE dbo.opportunity_source_identities
                SET employer_name = @EmployerName,
                    role_title = @RoleTitle,
                    updated_at_utc = @Now
                WHERE opportunity_source_version_id = @VersionId
                  AND owner_profile_id = @ProfileId;

                IF @@ROWCOUNT = 0
                    INSERT dbo.opportunity_source_identities
                        (opportunity_source_version_id, owner_profile_id, employer_name,
                         role_title, source_type, entered_by_user_id, created_at_utc, updated_at_utc)
                    VALUES
                        (@VersionId, @ProfileId, @EmployerName, @RoleTitle, N''job_posting'',
                         @UserId, @Now, @Now);

                /* Identity writes share the source token with wording and
                   confirmation, so advance that token after every accepted
                   upsert. Without this update, two clients carrying the same
                   source token could both succeed and the later identity
                   write would silently win. Identity remains metadata: this
                   touches no employer wording and no confirmation field. */
                UPDATE dbo.opportunity_sources
                SET updated_at_utc = @Now
                WHERE opportunity_source_id = @SourceId
                  AND owner_profile_id = @ProfileId;

                SELECT @NewSourceRowVersion = CONVERT(binary(8), row_version)
                FROM dbo.opportunity_sources
                WHERE opportunity_source_id = @SourceId AND owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, @NewSourceRowVersion AS source_row_version;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    /* ------------------------------------------------------------
       7. usp_GetOpportunitySourceIdentityForOwner. A minimal read
          counterpart to Save, exactly as OS-2''s
          usp_GetOpportunitySourceReviewForOwner pairs with
          usp_SaveOpportunitySourceReviewForOwner. Not named in the
          architecture''s section 5.2 sketch; added because stage 2 cannot
          render prefilled Employer/Role title fields without it. No row
          means "nothing entered yet" -- the room shows the honest
          placeholder the architecture describes (section 4.2), never an
          error.
       ------------------------------------------------------------ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_GetOpportunitySourceIdentityForOwner
            @UserKey nvarchar(300),
            @SourceKey uniqueidentifier
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @SourceKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            SELECT
                identity_record.employer_name,
                identity_record.role_title,
                identity_record.source_type
            FROM dbo.opportunity_source_identities AS identity_record
            JOIN dbo.opportunity_source_versions AS version_record
              ON version_record.opportunity_source_version_id = identity_record.opportunity_source_version_id
             AND version_record.owner_profile_id = identity_record.owner_profile_id
            JOIN dbo.opportunity_sources AS source_record
              ON source_record.opportunity_source_id = version_record.opportunity_source_id
             AND source_record.owner_profile_id = version_record.owner_profile_id
            WHERE source_record.source_key = @SourceKey
              AND source_record.owner_profile_id = @ProfileId
              AND version_record.version_number = source_record.current_version_number;
        END;
    ');

    /* ------------------------------------------------------------
       8. TAKEOVER: usp_PurgeExpiredOpportunityWorkingData learns the three
          new v2 child tables. Every existing delete in this procedure is
          reproduced byte-for-byte from its PS-OPPSLATE-002 body; the three
          new blocks are marked below and sit at the position each new
          table''s foreign key requires (child before parent).
       ------------------------------------------------------------ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_PurgeExpiredOpportunityWorkingData
            @UserKey nvarchar(300),
            @IncludeCounts bit = 1
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @IncludeCounts IS NULL SET @IncludeCounts = 1;
            IF @UserKey IS NULL RETURN;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL RETURN;

            DECLARE @Now datetime2(7) = SYSUTCDATETIME();
            DECLARE @ExpiredSessions TABLE (working_session_id bigint NOT NULL PRIMARY KEY);
            DECLARE @PurgedVersionCount int = 0;
            DECLARE @PurgedSessionCount int = 0;
            DECLARE @OuterTranCount int = @@TRANCOUNT;

            BEGIN TRY
                IF @OuterTranCount = 0 BEGIN TRANSACTION;

                INSERT @ExpiredSessions (working_session_id)
                SELECT working_session.working_session_id
                FROM dbo.opportunity_working_sessions AS working_session WITH (UPDLOCK, HOLDLOCK)
                WHERE working_session.owner_profile_id = @ProfileId
                  AND working_session.expires_at_utc <= @Now;

                DELETE concern_record
                FROM dbo.opportunity_source_concerns AS concern_record
                JOIN dbo.opportunity_source_reviews AS review_record
                  ON review_record.opportunity_source_review_id = concern_record.opportunity_source_review_id
                 AND review_record.owner_profile_id = concern_record.owner_profile_id
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = review_record.opportunity_source_id
                 AND source_record.owner_profile_id = review_record.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = source_record.working_session_id
                WHERE concern_record.owner_profile_id = @ProfileId;

                DELETE review_record
                FROM dbo.opportunity_source_reviews AS review_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = review_record.opportunity_source_id
                 AND source_record.owner_profile_id = review_record.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = source_record.working_session_id
                WHERE review_record.owner_profile_id = @ProfileId;

                DELETE citation_record
                FROM dbo.opportunity_analysis_citations AS citation_record
                JOIN dbo.opportunity_analysis_statements AS analysis_statement
                  ON analysis_statement.opportunity_analysis_statement_id = citation_record.opportunity_analysis_statement_id
                 AND analysis_statement.owner_profile_id = citation_record.owner_profile_id
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE citation_record.owner_profile_id = @ProfileId;

                DELETE analysis_statement
                FROM dbo.opportunity_analysis_statements AS analysis_statement
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE analysis_statement.owner_profile_id = @ProfileId;

                DELETE analysis_record
                FROM dbo.opportunity_analyses AS analysis_record
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE analysis_record.owner_profile_id = @ProfileId;

                DELETE response_record
                FROM dbo.opportunity_responses AS response_record
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.opportunity_requirement_statement_id = response_record.opportunity_requirement_statement_id
                 AND statement_record.owner_profile_id = response_record.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE response_record.owner_profile_id = @ProfileId;

                /* PS-OPPSLATE-004 ADDITION (1 of 2). opportunity_member_takes
                   and opportunity_requirement_review_events both hang off
                   opportunity_requirement_statements, so both have to go
                   before it does, exactly like opportunity_responses above. */
                DELETE take_record
                FROM dbo.opportunity_member_takes AS take_record
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.opportunity_requirement_statement_id = take_record.opportunity_requirement_statement_id
                 AND statement_record.owner_profile_id = take_record.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE take_record.owner_profile_id = @ProfileId;

                DELETE review_event
                FROM dbo.opportunity_requirement_review_events AS review_event
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.opportunity_requirement_statement_id = review_event.opportunity_requirement_statement_id
                 AND statement_record.owner_profile_id = review_event.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE review_event.owner_profile_id = @ProfileId;

                DELETE statement_record
                FROM dbo.opportunity_requirement_statements AS statement_record
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE statement_record.owner_profile_id = @ProfileId;

                DELETE set_version
                FROM dbo.opportunity_requirement_set_versions AS set_version
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE set_version.owner_profile_id = @ProfileId;

                DELETE requirement_set
                FROM dbo.opportunity_requirement_sets AS requirement_set
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = requirement_set.working_session_id
                WHERE requirement_set.owner_profile_id = @ProfileId;

                /* PS-OPPSLATE-004 ADDITION (2 of 2). opportunity_source_identities
                   hangs off opportunity_source_versions, so it has to go
                   before the version delete below. */
                DELETE identity_record
                FROM dbo.opportunity_source_identities AS identity_record
                JOIN dbo.opportunity_source_versions AS version_record
                  ON version_record.opportunity_source_version_id = identity_record.opportunity_source_version_id
                 AND version_record.owner_profile_id = identity_record.owner_profile_id
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = version_record.opportunity_source_id
                 AND source_record.owner_profile_id = version_record.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = source_record.working_session_id
                WHERE identity_record.owner_profile_id = @ProfileId;

                DELETE version_record
                FROM dbo.opportunity_source_versions AS version_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = version_record.opportunity_source_id
                 AND source_record.owner_profile_id = version_record.owner_profile_id
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = source_record.working_session_id
                WHERE version_record.owner_profile_id = @ProfileId;
                SET @PurgedVersionCount = @@ROWCOUNT;

                DELETE source_record
                FROM dbo.opportunity_sources AS source_record
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = source_record.working_session_id
                WHERE source_record.owner_profile_id = @ProfileId;

                DELETE working_session
                FROM dbo.opportunity_working_sessions AS working_session
                JOIN @ExpiredSessions AS expired
                  ON expired.working_session_id = working_session.working_session_id
                WHERE working_session.owner_profile_id = @ProfileId;
                SET @PurgedSessionCount = @@ROWCOUNT;

                IF @OuterTranCount = 0 COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF @OuterTranCount = 0 AND XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;

            IF @IncludeCounts = 1
                SELECT
                    @PurgedSessionCount AS purged_session_count,
                    @PurgedVersionCount AS purged_version_count;
        END;
    ');

    /* ------------------------------------------------------------
       9. TAKEOVER: usp_DeleteOpportunityWorkingSessionForOwner learns the
          same three new tables, at the same relative positions, for the
          member''s explicit "delete this working opportunity" action.
       ------------------------------------------------------------ */

    EXEC(N'
        CREATE OR ALTER PROCEDURE dbo.usp_DeleteOpportunityWorkingSessionForOwner
            @UserKey nvarchar(300),
            @WorkingSessionKey uniqueidentifier,
            @ExpectedRowVersion binary(8)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
            IF @UserKey IS NULL OR @WorkingSessionKey IS NULL OR @ExpectedRowVersion IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_version_count;
                RETURN;
            END;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
            BEGIN
                SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_version_count;
                RETURN;
            END;

            DECLARE @SessionId bigint;
            DECLARE @DeletedVersionCount int = 0;

            BEGIN TRY
                BEGIN TRANSACTION;

                SELECT @SessionId = working_session.working_session_id
                FROM dbo.opportunity_working_sessions AS working_session WITH (UPDLOCK, HOLDLOCK)
                WHERE working_session.working_session_key = @WorkingSessionKey
                  AND working_session.owner_profile_id = @ProfileId
                  AND working_session.row_version = @ExpectedRowVersion;

                IF @SessionId IS NULL
                BEGIN
                    COMMIT TRANSACTION;
                    SELECT N''changed'' AS outcome, CAST(NULL AS int) AS deleted_version_count;
                    RETURN;
                END;

                DELETE concern_record
                FROM dbo.opportunity_source_concerns AS concern_record
                JOIN dbo.opportunity_source_reviews AS review_record
                  ON review_record.opportunity_source_review_id = concern_record.opportunity_source_review_id
                 AND review_record.owner_profile_id = concern_record.owner_profile_id
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = review_record.opportunity_source_id
                 AND source_record.owner_profile_id = review_record.owner_profile_id
                WHERE source_record.working_session_id = @SessionId
                  AND concern_record.owner_profile_id = @ProfileId;

                DELETE review_record
                FROM dbo.opportunity_source_reviews AS review_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = review_record.opportunity_source_id
                 AND source_record.owner_profile_id = review_record.owner_profile_id
                WHERE source_record.working_session_id = @SessionId
                  AND review_record.owner_profile_id = @ProfileId;

                DELETE citation_record
                FROM dbo.opportunity_analysis_citations AS citation_record
                JOIN dbo.opportunity_analysis_statements AS analysis_statement
                  ON analysis_statement.opportunity_analysis_statement_id = citation_record.opportunity_analysis_statement_id
                 AND analysis_statement.owner_profile_id = citation_record.owner_profile_id
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND citation_record.owner_profile_id = @ProfileId;

                DELETE analysis_statement
                FROM dbo.opportunity_analysis_statements AS analysis_statement
                JOIN dbo.opportunity_analyses AS analysis_record
                  ON analysis_record.opportunity_analysis_id = analysis_statement.opportunity_analysis_id
                 AND analysis_record.owner_profile_id = analysis_statement.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND analysis_statement.owner_profile_id = @ProfileId;

                DELETE analysis_record
                FROM dbo.opportunity_analyses AS analysis_record
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = analysis_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = analysis_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND analysis_record.owner_profile_id = @ProfileId;

                DELETE response_record
                FROM dbo.opportunity_responses AS response_record
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.opportunity_requirement_statement_id = response_record.opportunity_requirement_statement_id
                 AND statement_record.owner_profile_id = response_record.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND response_record.owner_profile_id = @ProfileId;

                /* PS-OPPSLATE-004 ADDITION (1 of 2). Same reasoning as the
                   purge: "atomic and complete" now reaches the member''s
                   take/response rows and requirement-review history too. */
                DELETE take_record
                FROM dbo.opportunity_member_takes AS take_record
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.opportunity_requirement_statement_id = take_record.opportunity_requirement_statement_id
                 AND statement_record.owner_profile_id = take_record.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND take_record.owner_profile_id = @ProfileId;

                DELETE review_event
                FROM dbo.opportunity_requirement_review_events AS review_event
                JOIN dbo.opportunity_requirement_statements AS statement_record
                  ON statement_record.opportunity_requirement_statement_id = review_event.opportunity_requirement_statement_id
                 AND statement_record.owner_profile_id = review_event.owner_profile_id
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND review_event.owner_profile_id = @ProfileId;

                DELETE statement_record
                FROM dbo.opportunity_requirement_statements AS statement_record
                JOIN dbo.opportunity_requirement_set_versions AS set_version
                  ON set_version.opportunity_requirement_set_version_id = statement_record.opportunity_requirement_set_version_id
                 AND set_version.owner_profile_id = statement_record.owner_profile_id
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND statement_record.owner_profile_id = @ProfileId;

                DELETE set_version
                FROM dbo.opportunity_requirement_set_versions AS set_version
                JOIN dbo.opportunity_requirement_sets AS requirement_set
                  ON requirement_set.opportunity_requirement_set_id = set_version.opportunity_requirement_set_id
                 AND requirement_set.owner_profile_id = set_version.owner_profile_id
                WHERE requirement_set.working_session_id = @SessionId
                  AND set_version.owner_profile_id = @ProfileId;

                DELETE dbo.opportunity_requirement_sets
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                /* PS-OPPSLATE-004 ADDITION (2 of 2). */
                DELETE identity_record
                FROM dbo.opportunity_source_identities AS identity_record
                JOIN dbo.opportunity_source_versions AS version_record
                  ON version_record.opportunity_source_version_id = identity_record.opportunity_source_version_id
                 AND version_record.owner_profile_id = identity_record.owner_profile_id
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = version_record.opportunity_source_id
                 AND source_record.owner_profile_id = version_record.owner_profile_id
                WHERE source_record.working_session_id = @SessionId
                  AND identity_record.owner_profile_id = @ProfileId;

                DELETE version_record
                FROM dbo.opportunity_source_versions AS version_record
                JOIN dbo.opportunity_sources AS source_record
                  ON source_record.opportunity_source_id = version_record.opportunity_source_id
                 AND source_record.owner_profile_id = version_record.owner_profile_id
                WHERE source_record.working_session_id = @SessionId
                  AND version_record.owner_profile_id = @ProfileId;
                SET @DeletedVersionCount = @@ROWCOUNT;

                DELETE dbo.opportunity_sources
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                DELETE dbo.opportunity_working_sessions
                WHERE working_session_id = @SessionId AND owner_profile_id = @ProfileId;

                COMMIT TRANSACTION;

                SELECT N''success'' AS outcome, @DeletedVersionCount AS deleted_version_count;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;
    ');

    /* ------------------------------------------------------------
       10. Fingerprint the two taken-over procedures and the two new ones,
           exactly as PS-OPPSLATE-002 stamped its own takeovers. A future
           migration that ever needs to take usp_PurgeExpiredOpportunity-
           WorkingData or usp_DeleteOpportunityWorkingSessionForOwner over
           again re-stamps in the same way; the forward-idempotency gate
           fails if any of the four bodies below drifts without a stamp.
       ------------------------------------------------------------ */

    DECLARE @ProcedureHashPropertyName sysname = N'PS_OPPSLATE_004_DEFINITION_HASH';
    DECLARE @ProtectedProcedures TABLE (procedure_name sysname NOT NULL PRIMARY KEY);
    INSERT @ProtectedProcedures (procedure_name)
    VALUES
        (N'usp_PurgeExpiredOpportunityWorkingData'),
        (N'usp_DeleteOpportunityWorkingSessionForOwner'),
        (N'usp_SaveOpportunitySourceIdentityForOwner'),
        (N'usp_GetOpportunitySourceIdentityForOwner');
    DECLARE @ProtectedProcedureName sysname, @ProtectedProcedureHash nvarchar(64);
    WHILE EXISTS (SELECT 1 FROM @ProtectedProcedures)
    BEGIN
        SELECT TOP (1) @ProtectedProcedureName = procedure_name
        FROM @ProtectedProcedures ORDER BY procedure_name;
        IF OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P') IS NULL
            THROW 53806, 'A required PS-OPPSLATE-004 procedure was not created.', 1;
        SELECT @ProtectedProcedureHash = CONVERT(nvarchar(64),
            HASHBYTES('SHA2_256', OBJECT_DEFINITION(OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P'))), 2);
        IF EXISTS (SELECT 1 FROM sys.extended_properties
                   WHERE class = 1 AND major_id = OBJECT_ID(N'dbo.' + @ProtectedProcedureName, N'P')
                     AND minor_id = 0 AND name = @ProcedureHashPropertyName)
            EXEC sys.sp_updateextendedproperty @name=@ProcedureHashPropertyName,
                @value=@ProtectedProcedureHash, @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'PROCEDURE', @level1name=@ProtectedProcedureName;
        ELSE
            EXEC sys.sp_addextendedproperty @name=@ProcedureHashPropertyName,
                @value=@ProtectedProcedureHash, @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'PROCEDURE', @level1name=@ProtectedProcedureName;
        DELETE @ProtectedProcedures WHERE procedure_name = @ProtectedProcedureName;
    END;

    /* Stamp every table/column rollback can drop. The fresh-admission guard
       above proves these surfaces were absent before this migration; the
       stamp lets rollback refuse an object whose ownership cannot be
       established instead of dropping by name alone. */
    DECLARE @OwnedTables TABLE (table_name sysname NOT NULL PRIMARY KEY);
    INSERT @OwnedTables (table_name)
    VALUES
        (N'opportunity_source_identities'),
        (N'opportunity_requirement_review_events'),
        (N'opportunity_member_takes');
    DECLARE @OwnedTableName sysname;
    WHILE EXISTS (SELECT 1 FROM @OwnedTables)
    BEGIN
        SELECT TOP (1) @OwnedTableName = table_name FROM @OwnedTables ORDER BY table_name;
        IF EXISTS
        (
            SELECT 1 FROM sys.extended_properties
            WHERE class = 1
              AND major_id = OBJECT_ID(N'dbo.' + @OwnedTableName, N'U')
              AND minor_id = 0
              AND name = @OwnershipPropertyName
        )
            EXEC sys.sp_updateextendedproperty @name=@OwnershipPropertyName, @value=N'1',
                @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'TABLE', @level1name=@OwnedTableName;
        ELSE
            EXEC sys.sp_addextendedproperty @name=@OwnershipPropertyName, @value=N'1',
                @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'TABLE', @level1name=@OwnedTableName;
        DELETE @OwnedTables WHERE table_name = @OwnedTableName;
    END;

    DECLARE @OwnedColumns TABLE
        (table_name sysname NOT NULL, column_name sysname NOT NULL,
         PRIMARY KEY (table_name, column_name));
    INSERT @OwnedColumns (table_name, column_name)
    VALUES
        (N'opportunity_analyses', N'evidence_snapshot_sha256'),
        (N'opportunity_analyses', N'confirmed_requirements_ordinal'),
        (N'opportunity_requirement_sets', N'member_confirmed_ordinal');
    DECLARE @OwnedColumnTableName sysname;
    DECLARE @OwnedColumnName sysname;
    WHILE EXISTS (SELECT 1 FROM @OwnedColumns)
    BEGIN
        SELECT TOP (1)
            @OwnedColumnTableName = table_name,
            @OwnedColumnName = column_name
        FROM @OwnedColumns ORDER BY table_name, column_name;
        IF EXISTS
        (
            SELECT 1
            FROM sys.extended_properties AS property_record
            JOIN sys.columns AS column_record
              ON column_record.object_id = property_record.major_id
             AND column_record.column_id = property_record.minor_id
            WHERE property_record.class = 1
              AND property_record.major_id = OBJECT_ID(N'dbo.' + @OwnedColumnTableName, N'U')
              AND column_record.name = @OwnedColumnName
              AND property_record.name = @OwnershipPropertyName
        )
            EXEC sys.sp_updateextendedproperty @name=@OwnershipPropertyName, @value=N'1',
                @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'TABLE', @level1name=@OwnedColumnTableName,
                @level2type=N'COLUMN', @level2name=@OwnedColumnName;
        ELSE
            EXEC sys.sp_addextendedproperty @name=@OwnershipPropertyName, @value=N'1',
                @level0type=N'SCHEMA', @level0name=N'dbo',
                @level1type=N'TABLE', @level1name=@OwnedColumnTableName,
                @level2type=N'COLUMN', @level2name=@OwnedColumnName;
        DELETE @OwnedColumns
        WHERE table_name = @OwnedColumnTableName AND column_name = @OwnedColumnName;
    END;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-OPPSLATE-004')
    BEGIN
        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES (N'PS-OPPSLATE-004', N'Opportunity Slate replacement R1 additive delta: source identity (member-entered employer/role title), the shape of two R2 tables (requirement review events, member takes) and three R2 currency columns, and a hash-stamped takeover of the purge/delete procedures to learn all three new child tables. Requires PS-OPPSLATE-001/002/003. No aggregate score, percentage, ranking, recommendation, or verdict. No AI call.', N'PeerSlate Bible and Roadmap v3.0');
        EXEC dbo.usp_AppendAuditEvent @ActionType=N'schema.migration.applied',
            @EntityType=N'database_migration', @Outcome=N'success',
            @MetadataJson=N'{"migration_id":"PS-OPPSLATE-004"}';
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
