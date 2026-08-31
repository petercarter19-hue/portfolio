/*
 PS-MYOPP-003 — My Opportunities C5 owner-scoped qualification foundation.

 Additive member-side persistence for evidence grants, four-state assessments
 with append-only revisions, reference-only evidence links, and practical-fit
 observations. AI proposes and deterministic code decides; no route, search
 execution, retrieval, provider, fixture row, job, Workshop change, or
 production action; no score/probability/ranking field anywhere.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-003')
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-001')
            THROW 55660, 'PS-MYOPP-003 requires PS-MYOPP-001.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-002')
            THROW 55661, 'PS-MYOPP-003 requires PS-MYOPP-002.', 1;

        CREATE TABLE dbo.myopp_evidence_grants
        (
            myopp_evidence_grant_id bigint IDENTITY(1,1) NOT NULL,
            grant_key uniqueidentifier NOT NULL
                CONSTRAINT DF_myopp_evidence_grants_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            purpose nvarchar(40) NOT NULL
                CONSTRAINT DF_myopp_evidence_grants_purpose DEFAULT N'qualification_verification',
            scope_classes_json nvarchar(max) NOT NULL,
            scope_record_keys_json nvarchar(max) NULL,
            granted_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_evidence_grants_granted DEFAULT SYSUTCDATETIME(),
            expires_at_utc datetime2(7) NOT NULL,
            revoked_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_evidence_grants PRIMARY KEY (myopp_evidence_grant_id),
            CONSTRAINT UQ_myopp_evidence_grants_key UNIQUE (grant_key),
            CONSTRAINT UQ_myopp_evidence_grants_id_user UNIQUE (myopp_evidence_grant_id, user_key),
            CONSTRAINT UQ_myopp_evidence_grants_key_user UNIQUE (grant_key, user_key),
            CONSTRAINT FK_myopp_evidence_grants_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT CK_myopp_evidence_grants_purpose CHECK (purpose = N'qualification_verification'),
            CONSTRAINT CK_myopp_evidence_grants_scope_classes_json
                CHECK (ISJSON(scope_classes_json) = 1 AND LEFT(LTRIM(scope_classes_json), 1) = N'['
                       AND scope_classes_json <> N'[]'),
            CONSTRAINT CK_myopp_evidence_grants_scope_records_json
                CHECK (scope_record_keys_json IS NULL
                       OR (ISJSON(scope_record_keys_json) = 1
                           AND LEFT(LTRIM(scope_record_keys_json), 1) = N'['
                           AND scope_record_keys_json <> N'[]')),
            CONSTRAINT CK_myopp_evidence_grants_expiry CHECK (expires_at_utc > granted_at_utc),
            CONSTRAINT CK_myopp_evidence_grants_revocation
                CHECK (revoked_at_utc IS NULL OR revoked_at_utc >= granted_at_utc)
        );

        CREATE TABLE dbo.myopp_assessments
        (
            myopp_assessment_id bigint IDENTITY(1,1) NOT NULL,
            assessment_key uniqueidentifier NOT NULL
                CONSTRAINT DF_myopp_assessments_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            data_class nvarchar(20) NOT NULL,
            myopp_requirement_item_id bigint NOT NULL,
            myopp_requirement_version_id bigint NOT NULL,
            assessment_type nvarchar(20) NOT NULL,
            state nvarchar(30) NOT NULL,
            reason_code nvarchar(40) NOT NULL,
            current_revision_number int NOT NULL
                CONSTRAINT DF_myopp_assessments_revision DEFAULT 1,
            assessed_at_utc datetime2(7) NOT NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_assessments_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_assessments_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_assessments PRIMARY KEY (myopp_assessment_id),
            CONSTRAINT UQ_myopp_assessments_key UNIQUE (assessment_key),
            CONSTRAINT UQ_myopp_assessments_id_user UNIQUE (myopp_assessment_id, user_key),
            CONSTRAINT UQ_myopp_assessments_key_user UNIQUE (assessment_key, user_key),
            CONSTRAINT UQ_myopp_assessments_identity
                UNIQUE (user_key, myopp_requirement_item_id, myopp_requirement_version_id),
            CONSTRAINT FK_myopp_assessments_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT FK_myopp_assessments_requirement_item_class
                FOREIGN KEY (myopp_requirement_item_id, data_class)
                REFERENCES dbo.myopp_requirement_items (myopp_requirement_item_id, data_class),
            CONSTRAINT FK_myopp_assessments_requirement_version_class
                FOREIGN KEY (myopp_requirement_version_id, data_class)
                REFERENCES dbo.myopp_requirement_versions (myopp_requirement_version_id, data_class),
            CONSTRAINT CK_myopp_assessments_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_assessments_type CHECK (assessment_type IN (N'required', N'preferred')),
            CONSTRAINT CK_myopp_assessments_state
                CHECK (state IN (N'verified', N'not_established', N'appears_unmet', N'review_unavailable')),
            CONSTRAINT CK_myopp_assessments_state_reason CHECK
            (
                (state = N'verified' AND reason_code IN (N'direct_evidence', N'corroborated', N'alternative_path_met'))
                OR
                (state = N'not_established' AND reason_code IN (N'no_evidence_in_scope', N'ambiguous_evidence',
                    N'partial_evidence', N'temporal_mismatch', N'evidence_revoked',
                    N'classification_ambiguous', N'candidate_evidence_only'))
                OR
                (state = N'appears_unmet' AND reason_code = N'affirmative_contradiction')
                OR
                (state = N'review_unavailable' AND reason_code IN (N'ai_unavailable',
                    N'evidence_source_unavailable', N'timeout', N'assessment_error'))
            ),
            CONSTRAINT CK_myopp_assessments_revision CHECK (current_revision_number > 0),
            CONSTRAINT CK_myopp_assessments_timestamp_order CHECK (updated_at_utc >= created_at_utc)
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_assessments_requirement_consistency
        ON dbo.myopp_assessments
        AFTER INSERT
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS
            (
                SELECT 1 FROM inserted i
                JOIN dbo.myopp_requirement_items item
                  ON item.myopp_requirement_item_id = i.myopp_requirement_item_id
                WHERE item.myopp_requirement_version_id <> i.myopp_requirement_version_id
            )
                THROW 55662, ''An assessment must reference an item of its own requirement version.'', 1;
        END');

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_assessments_head_guard
        ON dbo.myopp_assessments
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS (SELECT 1 FROM deleted d LEFT JOIN inserted i
                       ON i.myopp_assessment_id = d.myopp_assessment_id
                       WHERE i.myopp_assessment_id IS NULL)
                THROW 55663, ''Assessment rows are member history and cannot be deleted here.'', 1;
            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_assessment_id = i.myopp_assessment_id
                WHERE i.assessment_key <> d.assessment_key OR i.user_key <> d.user_key
                   OR i.data_class <> d.data_class
                   OR i.myopp_requirement_item_id <> d.myopp_requirement_item_id
                   OR i.myopp_requirement_version_id <> d.myopp_requirement_version_id
                   OR i.assessment_type <> d.assessment_type
                   OR i.created_at_utc <> d.created_at_utc
            )
                THROW 55664, ''Assessment identity is immutable.'', 1;
            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_assessment_id = i.myopp_assessment_id
                WHERE i.current_revision_number <> d.current_revision_number + 1
            )
                THROW 55665, ''An assessment head advances exactly one revision at a time.'', 1;
        END');

        CREATE TABLE dbo.myopp_assessment_revisions
        (
            myopp_assessment_revision_id bigint IDENTITY(1,1) NOT NULL,
            myopp_assessment_id bigint NOT NULL,
            user_key nvarchar(300) NOT NULL,
            revision_number int NOT NULL,
            state nvarchar(30) NOT NULL,
            reason_code nvarchar(40) NOT NULL,
            recompute_cause nvarchar(30) NOT NULL,
            actor nvarchar(60) NOT NULL,
            assessed_at_utc datetime2(7) NOT NULL,
            recorded_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_assessment_revisions_recorded DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_assessment_revisions PRIMARY KEY (myopp_assessment_revision_id),
            CONSTRAINT UQ_myopp_assessment_revisions_id_user
                UNIQUE (myopp_assessment_revision_id, user_key),
            CONSTRAINT UQ_myopp_assessment_revisions_number
                UNIQUE (myopp_assessment_id, revision_number),
            CONSTRAINT FK_myopp_assessment_revisions_assessment_owner
                FOREIGN KEY (myopp_assessment_id, user_key)
                REFERENCES dbo.myopp_assessments (myopp_assessment_id, user_key),
            CONSTRAINT CK_myopp_assessment_revisions_number CHECK (revision_number > 0),
            CONSTRAINT CK_myopp_assessment_revisions_state
                CHECK (state IN (N'verified', N'not_established', N'appears_unmet', N'review_unavailable')),
            CONSTRAINT CK_myopp_assessment_revisions_state_reason CHECK
            (
                (state = N'verified' AND reason_code IN (N'direct_evidence', N'corroborated', N'alternative_path_met'))
                OR
                (state = N'not_established' AND reason_code IN (N'no_evidence_in_scope', N'ambiguous_evidence',
                    N'partial_evidence', N'temporal_mismatch', N'evidence_revoked',
                    N'classification_ambiguous', N'candidate_evidence_only'))
                OR
                (state = N'appears_unmet' AND reason_code = N'affirmative_contradiction')
                OR
                (state = N'review_unavailable' AND reason_code IN (N'ai_unavailable',
                    N'evidence_source_unavailable', N'timeout', N'assessment_error'))
            ),
            CONSTRAINT CK_myopp_assessment_revisions_cause
                CHECK (recompute_cause IN (N'initial', N'retry', N'member_correction',
                                           N'reading_flagged', N'grant_revoked', N'grant_expired')),
            CONSTRAINT CK_myopp_assessment_revisions_actor
                CHECK (actor IN (N'system:search_worker/assessment', N'system:recompute',
                                 N'member', N'correction'))
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_assessment_revisions_immutable
        ON dbo.myopp_assessment_revisions
        AFTER UPDATE, DELETE
        AS
        BEGIN
            THROW 55666, ''Assessment revisions are append-only history.'', 1;
        END');

        CREATE TABLE dbo.myopp_assessment_evidence_links
        (
            myopp_assessment_evidence_link_id bigint IDENTITY(1,1) NOT NULL,
            myopp_assessment_revision_id bigint NOT NULL,
            user_key nvarchar(300) NOT NULL,
            evidence_class nvarchar(40) NOT NULL,
            evidence_key uniqueidentifier NOT NULL,
            evidence_version int NOT NULL,
            myopp_evidence_grant_id bigint NOT NULL,
            relation nvarchar(20) NOT NULL,
            time_span_start date NULL,
            time_span_end date NULL,
            credential_name nvarchar(200) NULL,
            recorded_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_assessment_evidence_links_recorded DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_assessment_evidence_links PRIMARY KEY (myopp_assessment_evidence_link_id),
            CONSTRAINT UQ_myopp_assessment_evidence_links_claim
                UNIQUE (myopp_assessment_revision_id, evidence_class, evidence_key, evidence_version, relation),
            CONSTRAINT FK_myopp_assessment_evidence_links_revision_owner
                FOREIGN KEY (myopp_assessment_revision_id, user_key)
                REFERENCES dbo.myopp_assessment_revisions (myopp_assessment_revision_id, user_key),
            CONSTRAINT FK_myopp_assessment_evidence_links_grant_owner
                FOREIGN KEY (myopp_evidence_grant_id, user_key)
                REFERENCES dbo.myopp_evidence_grants (myopp_evidence_grant_id, user_key),
            CONSTRAINT CK_myopp_assessment_evidence_links_class
                CHECK (evidence_class IN (N'workshop_knowledge')),
            CONSTRAINT CK_myopp_assessment_evidence_links_version CHECK (evidence_version > 0),
            CONSTRAINT CK_myopp_assessment_evidence_links_relation
                CHECK (relation IN (N'supports', N'partial', N'contradicts')),
            CONSTRAINT CK_myopp_assessment_evidence_links_span
                CHECK ((time_span_start IS NULL AND time_span_end IS NULL)
                       OR (time_span_start IS NOT NULL AND time_span_end IS NOT NULL
                           AND time_span_end >= time_span_start)),
            CONSTRAINT CK_myopp_assessment_evidence_links_credential
                CHECK (credential_name IS NULL OR LEN(credential_name) > 0)
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_assessment_evidence_links_immutable
        ON dbo.myopp_assessment_evidence_links
        AFTER UPDATE, DELETE
        AS
        BEGIN
            THROW 55667, ''Assessment evidence links are immutable references.'', 1;
        END');

        CREATE TABLE dbo.myopp_practical_fit_observations
        (
            myopp_practical_fit_observation_id bigint IDENTITY(1,1) NOT NULL,
            observation_key uniqueidentifier NOT NULL
                CONSTRAINT DF_myopp_practical_fit_observations_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            data_class nvarchar(20) NOT NULL,
            myopp_canonical_opportunity_id bigint NOT NULL,
            note_text nvarchar(2000) NOT NULL,
            recorded_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_practical_fit_observations_recorded DEFAULT SYSUTCDATETIME(),
            archived_at_utc datetime2(7) NULL,
            CONSTRAINT PK_myopp_practical_fit_observations PRIMARY KEY (myopp_practical_fit_observation_id),
            CONSTRAINT UQ_myopp_practical_fit_observations_key UNIQUE (observation_key),
            CONSTRAINT UQ_myopp_practical_fit_observations_id_user
                UNIQUE (myopp_practical_fit_observation_id, user_key),
            CONSTRAINT FK_myopp_practical_fit_observations_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT FK_myopp_practical_fit_observations_opportunity_class
                FOREIGN KEY (myopp_canonical_opportunity_id, data_class)
                REFERENCES dbo.myopp_canonical_opportunities (myopp_canonical_opportunity_id, data_class),
            CONSTRAINT CK_myopp_practical_fit_observations_data_class
                CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_practical_fit_observations_note CHECK (LEN(note_text) > 0),
            CONSTRAINT CK_myopp_practical_fit_observations_archive
                CHECK (archived_at_utc IS NULL OR archived_at_utc >= recorded_at_utc)
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_practical_fit_observations_guard
        ON dbo.myopp_practical_fit_observations
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS (SELECT 1 FROM deleted d LEFT JOIN inserted i
                       ON i.myopp_practical_fit_observation_id = d.myopp_practical_fit_observation_id
                       WHERE i.myopp_practical_fit_observation_id IS NULL)
                THROW 55668, ''Practical-fit observations are member history and cannot be deleted here.'', 1;
            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d
                  ON d.myopp_practical_fit_observation_id = i.myopp_practical_fit_observation_id
                WHERE i.observation_key <> d.observation_key OR i.user_key <> d.user_key
                   OR i.data_class <> d.data_class
                   OR i.myopp_canonical_opportunity_id <> d.myopp_canonical_opportunity_id
                   OR i.note_text <> d.note_text
                   OR i.recorded_at_utc <> d.recorded_at_utc
                   OR NOT (d.archived_at_utc IS NULL AND i.archived_at_utc IS NOT NULL)
            )
                THROW 55669, ''Only an archive transition on an unarchived observation is allowed.'', 1;
        END');

        CREATE TABLE dbo.myopp_qualification_commands
        (
            myopp_qualification_command_id bigint IDENTITY(1,1) NOT NULL,
            user_key nvarchar(300) NOT NULL,
            idempotency_key_sha256 char(64) NOT NULL,
            command_name nvarchar(40) NOT NULL,
            canonical_input_sha256 char(64) NOT NULL,
            result_kind nvarchar(20) NOT NULL,
            result_grant_id bigint NULL,
            result_observation_id bigint NULL,
            receipt_at_utc datetime2(7) NOT NULL,
            expires_at_utc datetime2(7) NOT NULL,
            CONSTRAINT PK_myopp_qualification_commands PRIMARY KEY (myopp_qualification_command_id),
            CONSTRAINT UQ_myopp_qualification_commands_owner_key UNIQUE (user_key, idempotency_key_sha256),
            CONSTRAINT FK_myopp_qualification_commands_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT FK_myopp_qualification_commands_grant_owner
                FOREIGN KEY (result_grant_id, user_key)
                REFERENCES dbo.myopp_evidence_grants (myopp_evidence_grant_id, user_key),
            CONSTRAINT FK_myopp_qualification_commands_observation_owner
                FOREIGN KEY (result_observation_id, user_key)
                REFERENCES dbo.myopp_practical_fit_observations (myopp_practical_fit_observation_id, user_key),
            CONSTRAINT CK_myopp_qualification_commands_idempotency_hash
                CHECK (LEN(idempotency_key_sha256) = 64 AND idempotency_key_sha256 NOT LIKE '%[^0-9a-f]%'),
            CONSTRAINT CK_myopp_qualification_commands_input_hash
                CHECK (LEN(canonical_input_sha256) = 64 AND canonical_input_sha256 NOT LIKE '%[^0-9a-f]%'),
            CONSTRAINT CK_myopp_qualification_commands_name
                CHECK (command_name IN (N'create_grant', N'revoke_grant', N'record_practical_fit', N'archive_practical_fit')),
            CONSTRAINT CK_myopp_qualification_commands_result CHECK
            (
                (result_kind = N'grant' AND result_grant_id IS NOT NULL AND result_observation_id IS NULL)
                OR
                (result_kind = N'observation' AND result_observation_id IS NOT NULL AND result_grant_id IS NULL)
            ),
            CONSTRAINT CK_myopp_qualification_commands_expiry CHECK (expires_at_utc > receipt_at_utc)
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_qualification_commands_immutable
        ON dbo.myopp_qualification_commands
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS (SELECT 1 FROM inserted)
                THROW 55670, ''Qualification command receipts are immutable.'', 1;
            IF EXISTS (SELECT 1 FROM deleted WHERE expires_at_utc > SYSUTCDATETIME())
                THROW 55671, ''Unexpired qualification command receipts cannot be removed.'', 1;
        END');

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_evidence_grants_transition_guard
        ON dbo.myopp_evidence_grants
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            IF EXISTS (SELECT 1 FROM deleted d LEFT JOIN inserted i
                       ON i.myopp_evidence_grant_id = d.myopp_evidence_grant_id
                       WHERE i.myopp_evidence_grant_id IS NULL)
                THROW 55672, ''Evidence grants are member authorization history and cannot be deleted here.'', 1;
            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_evidence_grant_id = i.myopp_evidence_grant_id
                WHERE i.grant_key <> d.grant_key OR i.user_key <> d.user_key OR i.purpose <> d.purpose
                   OR i.scope_classes_json <> d.scope_classes_json
                   OR (i.scope_record_keys_json IS NULL AND d.scope_record_keys_json IS NOT NULL)
                   OR (i.scope_record_keys_json IS NOT NULL AND d.scope_record_keys_json IS NULL)
                   OR (i.scope_record_keys_json IS NOT NULL AND d.scope_record_keys_json IS NOT NULL
                       AND i.scope_record_keys_json <> d.scope_record_keys_json)
                   OR i.granted_at_utc <> d.granted_at_utc OR i.expires_at_utc <> d.expires_at_utc
            )
                THROW 55673, ''Grant identity, purpose, scope, and expiry are immutable.'', 1;
            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_evidence_grant_id = i.myopp_evidence_grant_id
                WHERE NOT (d.revoked_at_utc IS NULL AND i.revoked_at_utc IS NOT NULL)
            )
                THROW 55674, ''A grant revocation cannot be undone or restated.'', 1;
        END');

        CREATE INDEX IX_myopp_evidence_grants_owner_live
            ON dbo.myopp_evidence_grants (user_key, revoked_at_utc, expires_at_utc);
        CREATE INDEX IX_myopp_evidence_grants_expiry
            ON dbo.myopp_evidence_grants (expires_at_utc);
        CREATE INDEX IX_myopp_assessments_owner_version
            ON dbo.myopp_assessments (user_key, myopp_requirement_version_id, state);
        CREATE INDEX IX_myopp_assessment_evidence_links_grant
            ON dbo.myopp_assessment_evidence_links (myopp_evidence_grant_id, user_key);
        CREATE INDEX IX_myopp_practical_fit_observations_owner
            ON dbo.myopp_practical_fit_observations (user_key, recorded_at_utc DESC);
        CREATE INDEX IX_myopp_qualification_commands_expiry
            ON dbo.myopp_qualification_commands (expires_at_utc);

        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES (N'PS-MYOPP-003',
                N'My Opportunities C5 owner-scoped evidence grants, four-state assessments with append-only revisions and reference-only evidence links, practical-fit observations, and content-free command receipts',
                N'PeerSlate My Opportunities C5 v0.1');
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
