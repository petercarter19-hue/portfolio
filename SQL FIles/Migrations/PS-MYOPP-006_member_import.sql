/*
 PS-MYOPP-006 -- My Opportunities C10 owner-scoped private member_import
 storage.

 Additive: deterministic paste and document-upload intake (magic-byte sniffed,
 streaming-cutoff bounded document parsing lives in the service; this schema
 stores only the terminal pipeline truth), the doc 06 section 2 closed
 outcome-state vocabulary recorded per import, an append-only stage-outcome
 trail, in-record fetch provenance (schema-complete now so the future C13
 url_fetch child needs no migration), dual-retention body-removal tombstones
 (member delete and rights-obligation takedown), and content-free idempotency
 receipts. No route, UI, provider integration, AI involvement, C2-C6 file
 change, fixture row, job, or production action.

 Deliberate structural absences (invariant-8 proof by construction): no
 column here references receipt_key, listing_key, source_version, or any
 shared-side key; no shared table gains a member_import reference. The
 verifier scans for these absences.

 THROW range for this migration: 55840-55850 (prerequisite guards
 55840-55844; trigger guards 55845-55850), inside the reserved
 55840-55899 band confirmed unused repo-wide against origin/main at
 authoring (next occupied THROW number above the band is 56101).
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-006')
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-001')
            THROW 55840, 'PS-MYOPP-006 requires PS-MYOPP-001.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-002')
            THROW 55841, 'PS-MYOPP-006 requires PS-MYOPP-002.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-003')
            THROW 55842, 'PS-MYOPP-006 requires PS-MYOPP-003.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-004')
            THROW 55843, 'PS-MYOPP-006 requires PS-MYOPP-004.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-005')
            THROW 55844, 'PS-MYOPP-006 requires PS-MYOPP-005.', 1;

        CREATE TABLE dbo.myopp_member_imports
        (
            myopp_member_import_id bigint IDENTITY(1,1) NOT NULL,
            import_key uniqueidentifier NOT NULL
                CONSTRAINT DF_myopp_member_imports_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            data_class nvarchar(20) NOT NULL,
            intake_method nvarchar(20) NOT NULL,
            record_state nvarchar(20) NOT NULL
                CONSTRAINT DF_myopp_member_imports_state DEFAULT N'active',
            declared_content_type nvarchar(255) NULL,
            byte_count bigint NULL,
            -- fetch provenance: schema-complete now for the C13-era url_fetch
            -- path; always NULL for C10's paste/upload intake methods.
            submitted_url nvarchar(2048) NULL,
            final_url nvarchar(2048) NULL,
            resolved_address nvarchar(64) NULL,
            fetched_at_utc datetime2(7) NULL,
            content_hash char(64) NULL,
            sanitizer_version nvarchar(40) NOT NULL,
            sanitized_text nvarchar(max) NULL,
            extracted_units int NULL,
            truncated bit NOT NULL
                CONSTRAINT DF_myopp_member_imports_truncated DEFAULT 0,
            current_outcome nvarchar(20) NOT NULL,
            current_reason nvarchar(40) NULL,
            rights_obligation_class nvarchar(20) NOT NULL
                CONSTRAINT DF_myopp_member_imports_rights DEFAULT N'none',
            body_removed_at_utc datetime2(7) NULL,
            body_removal_reason nvarchar(30) NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_member_imports_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_member_imports_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_member_imports PRIMARY KEY (myopp_member_import_id),
            CONSTRAINT UQ_myopp_member_imports_key UNIQUE (import_key),
            -- owner-fence composite targets (MINOR-13 precedent): let a
            -- downstream child table pair its FK on either the surrogate id
            -- or the opaque public key, always together with the owner.
            CONSTRAINT UQ_myopp_member_imports_id_user UNIQUE (myopp_member_import_id, user_key),
            CONSTRAINT UQ_myopp_member_imports_key_user UNIQUE (import_key, user_key),
            CONSTRAINT FK_myopp_member_imports_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT CK_myopp_member_imports_data_class
                CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_member_imports_intake_method
                CHECK (intake_method IN (N'paste', N'upload', N'url_fetch')),
            CONSTRAINT CK_myopp_member_imports_record_state
                CHECK (record_state IN (N'active', N'deleted')),
            CONSTRAINT CK_myopp_member_imports_byte_count
                CHECK (byte_count IS NULL OR byte_count >= 0),
            CONSTRAINT CK_myopp_member_imports_extracted_units
                CHECK (extracted_units IS NULL OR extracted_units >= 0),
            CONSTRAINT CK_myopp_member_imports_content_hash_hex
                CHECK (content_hash IS NULL OR (LEN(content_hash) = 64 AND content_hash NOT LIKE '%[^0-9a-f]%')),
            -- fetch-provenance pairing: the four fetch-only columns are
            -- populated only for intake_method = url_fetch (the C13 path);
            -- always NULL together for paste/upload.
            CONSTRAINT CK_myopp_member_imports_fetch_provenance CHECK
            (
                (intake_method = N'url_fetch')
                OR (submitted_url IS NULL AND final_url IS NULL AND resolved_address IS NULL AND fetched_at_utc IS NULL)
            ),
            -- doc 06 section 2 closed outcome-state vocabulary, byte-equal to
            -- the service module's OUTCOME_STATES; fetched/blocked are
            -- reserved for the C13 fetch stage but are schema-complete now.
            CONSTRAINT CK_myopp_member_imports_outcome CHECK
            (
                current_outcome IN (N'fetched', N'decoded', N'parsed', N'extracted', N'empty',
                                     N'partial', N'blocked', N'timeout', N'refused')
            ),
            -- outcome/reason pairing, byte-equal to the service module's
            -- closed pairing map; the blocked/fetch_deadline/fetch_too_large
            -- reason codes are C13-reserved but carried now so C13 needs no
            -- migration of its own.
            CONSTRAINT CK_myopp_member_imports_outcome_reason CHECK
            (
                (current_outcome IN (N'fetched', N'decoded', N'parsed', N'extracted', N'empty') AND current_reason IS NULL)
                OR (current_outcome = N'refused' AND current_reason IN
                    (N'could_not_decode', N'parser_failure', N'parser_resource_bounds',
                     N'archive_bomb_suspected', N'hostile_characters', N'fetch_too_large'))
                OR (current_outcome = N'partial' AND current_reason = N'output_truncated')
                OR (current_outcome = N'timeout' AND current_reason IN (N'extraction_deadline', N'fetch_deadline'))
                OR (current_outcome = N'blocked' AND current_reason IN
                    (N'denied_address', N'scheme_refused', N'redirect_refused', N'content_mismatch'))
            ),
            -- success/text pairing: stored text exists only for a successful
            -- (extracted/partial) outcome whose body has not been removed;
            -- truncated is set exactly, and only, for the partial outcome.
            CONSTRAINT CK_myopp_member_imports_outcome_text CHECK
            (
                (sanitized_text IS NULL AND current_outcome NOT IN (N'extracted', N'partial'))
                OR (sanitized_text IS NULL AND current_outcome IN (N'extracted', N'partial') AND body_removed_at_utc IS NOT NULL)
                OR (sanitized_text IS NOT NULL AND current_outcome IN (N'extracted', N'partial') AND body_removed_at_utc IS NULL)
            ),
            CONSTRAINT CK_myopp_member_imports_truncated CHECK
            (
                (truncated = 1 AND current_outcome = N'partial')
                OR (truncated = 0 AND current_outcome <> N'partial')
            ),
            CONSTRAINT CK_myopp_member_imports_rights_class
                CHECK (rights_obligation_class IN (N'none', N'takedown_required')),
            CONSTRAINT CK_myopp_member_imports_removal_reason
                CHECK (body_removal_reason IS NULL OR body_removal_reason IN (N'member_delete', N'rights_takedown')),
            -- tombstone pairing CKs. NOTE: T-SQL has no boolean-equality
            -- operator over two IS NULL predicates (the same BLOCKER-1 limit
            -- documented in PS-MYOPP-005's trigger comments applies equally
            -- inside a CHECK constraint); each pairing below is written as
            -- the equivalent OR-of-AND-branches instead.
            CONSTRAINT CK_myopp_member_imports_removal_pairing CHECK
            (
                (body_removed_at_utc IS NULL AND body_removal_reason IS NULL)
                OR (body_removed_at_utc IS NOT NULL AND body_removal_reason IS NOT NULL)
            ),
            CONSTRAINT CK_myopp_member_imports_removal_text
                CHECK (body_removed_at_utc IS NULL OR sanitized_text IS NULL),
            -- deleted <=> removed-with-member_delete; a rights takedown keeps
            -- the row active.
            CONSTRAINT CK_myopp_member_imports_state_removal CHECK
            (
                (record_state = N'active' AND (body_removal_reason IS NULL OR body_removal_reason = N'rights_takedown'))
                OR (record_state = N'deleted' AND body_removal_reason = N'member_delete')
            ),
            CONSTRAINT CK_myopp_member_imports_timestamp_order
                CHECK (updated_at_utc >= created_at_utc)
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_member_imports_transition_guard
        ON dbo.myopp_member_imports
        AFTER UPDATE
        AS
        BEGIN
            SET NOCOUNT ON;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_member_import_id = i.myopp_member_import_id
                WHERE i.import_key <> d.import_key OR i.user_key <> d.user_key OR i.data_class <> d.data_class
                   OR i.intake_method <> d.intake_method
                   OR ISNULL(i.declared_content_type, N''00010101'') <> ISNULL(d.declared_content_type, N''00010101'')
                   OR ISNULL(i.byte_count, -1) <> ISNULL(d.byte_count, -1)
                   OR ISNULL(i.submitted_url, N''00010101'') <> ISNULL(d.submitted_url, N''00010101'')
                   OR ISNULL(i.final_url, N''00010101'') <> ISNULL(d.final_url, N''00010101'')
                   OR ISNULL(i.resolved_address, N''00010101'') <> ISNULL(d.resolved_address, N''00010101'')
                   OR ISNULL(i.fetched_at_utc, N''00010101'') <> ISNULL(d.fetched_at_utc, N''00010101'')
                   OR ISNULL(i.content_hash, N''00010101'') <> ISNULL(d.content_hash, N''00010101'')
                   OR i.sanitizer_version <> d.sanitizer_version
                   OR ISNULL(i.extracted_units, -1) <> ISNULL(d.extracted_units, -1)
                   OR i.truncated <> d.truncated
                   OR i.current_outcome <> d.current_outcome
                   OR ISNULL(i.current_reason, N''00010101'') <> ISNULL(d.current_reason, N''00010101'')
                   OR i.created_at_utc <> d.created_at_utc
            )
                THROW 55845, ''Member import identity, intake facts, and pipeline outcome truth are immutable.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_member_import_id = i.myopp_member_import_id
                WHERE
                (
                    i.record_state <> d.record_state
                    OR ISNULL(i.sanitized_text, N''00010101'') <> ISNULL(d.sanitized_text, N''00010101'')
                    OR i.rights_obligation_class <> d.rights_obligation_class
                    OR ISNULL(i.body_removed_at_utc, N''00010101'') <> ISNULL(d.body_removed_at_utc, N''00010101'')
                    OR ISNULL(i.body_removal_reason, N''00010101'') <> ISNULL(d.body_removal_reason, N''00010101'')
                )
                AND NOT
                (
                    -- (a) rights-obligation body removal: active stays active
                    (
                        d.record_state = N''active'' AND i.record_state = N''active''
                        AND d.rights_obligation_class = N''none'' AND i.rights_obligation_class = N''takedown_required''
                        AND d.body_removed_at_utc IS NULL AND i.body_removed_at_utc IS NOT NULL
                        AND d.body_removal_reason IS NULL AND i.body_removal_reason = N''rights_takedown''
                        AND i.sanitized_text IS NULL
                    )
                    OR
                    -- (b) member delete: active -> deleted, tombstoned
                    (
                        d.record_state = N''active'' AND i.record_state = N''deleted''
                        AND d.body_removed_at_utc IS NULL AND i.body_removed_at_utc IS NOT NULL
                        AND d.body_removal_reason IS NULL AND i.body_removal_reason = N''member_delete''
                        AND i.sanitized_text IS NULL
                        AND i.rights_obligation_class = d.rights_obligation_class
                    )
                )
            )
                THROW 55846, ''Illegal member import transition: only a rights-obligation body removal (active to active) or a member delete (active to deleted) is permitted, and each only once from an unremoved body.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_member_import_id = i.myopp_member_import_id
                WHERE i.updated_at_utc < d.updated_at_utc
            )
                THROW 55847, ''updated_at_utc must not move backward.'', 1;
        END');

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_member_imports_delete_block
        ON dbo.myopp_member_imports
        AFTER DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            -- MERGE-SAFE BY CONSTRUCTION: this trigger fires only AFTER
            -- DELETE (never AFTER UPDATE), so every firing -- whether from a
            -- bare DELETE statement or a MERGE''s WHEN MATCHED ... THEN
            -- DELETE action -- is a genuine row removal. The inserted/deleted
            -- correlation PS-MYOPP-004/005 need (LEFT JOIN to rule out a
            -- MERGE UPDATE action populating both sides) only matters for a
            -- trigger that also fires on UPDATE; this one never does.
            IF EXISTS (SELECT 1 FROM deleted)
                THROW 55848, ''Member import rows are member history; no erasure path exists in this schema (future erasure package).'', 1;
        END');

        CREATE TABLE dbo.myopp_member_import_stage_outcomes
        (
            myopp_member_import_stage_outcome_id bigint IDENTITY(1,1) NOT NULL,
            myopp_member_import_id bigint NOT NULL,
            user_key nvarchar(300) NOT NULL,
            outcome nvarchar(20) NOT NULL,
            reason_code nvarchar(40) NULL,
            sequence_number int NOT NULL,
            occurred_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_member_import_stage_outcomes_occurred DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_member_import_stage_outcomes PRIMARY KEY (myopp_member_import_stage_outcome_id),
            CONSTRAINT UQ_myopp_member_import_stage_outcomes_sequence
                UNIQUE (myopp_member_import_id, sequence_number),
            CONSTRAINT FK_myopp_member_import_stage_outcomes_import_owner
                FOREIGN KEY (myopp_member_import_id, user_key)
                REFERENCES dbo.myopp_member_imports (myopp_member_import_id, user_key),
            CONSTRAINT CK_myopp_member_import_stage_outcomes_outcome CHECK
            (
                outcome IN (N'fetched', N'decoded', N'parsed', N'extracted', N'empty',
                            N'partial', N'blocked', N'timeout', N'refused')
            ),
            CONSTRAINT CK_myopp_member_import_stage_outcomes_sequence
                CHECK (sequence_number > 0)
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_member_import_stage_outcomes_immutable
        ON dbo.myopp_member_import_stage_outcomes
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            -- Any firing of an AFTER UPDATE, DELETE trigger means an update
            -- or delete was attempted; both are forbidden unconditionally
            -- for this append-only pipeline trail (PS-MYOPP-003 idiom).
            THROW 55849, ''Member import stage outcomes are an append-only pipeline trail.'', 1;
        END');

        CREATE TABLE dbo.myopp_member_import_idempotency
        (
            myopp_member_import_idempotency_id bigint IDENTITY(1,1) NOT NULL,
            user_key nvarchar(300) NOT NULL,
            idempotency_key nvarchar(200) NOT NULL,
            command nvarchar(40) NOT NULL,
            canonical_input_hash char(64) NOT NULL,
            result_json nvarchar(max) NOT NULL,
            expires_at_utc datetime2(7) NOT NULL,
            CONSTRAINT PK_myopp_member_import_idempotency PRIMARY KEY (myopp_member_import_idempotency_id),
            CONSTRAINT UQ_myopp_member_import_idempotency_owner_key UNIQUE (user_key, idempotency_key),
            CONSTRAINT FK_myopp_member_import_idempotency_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT CK_myopp_member_import_idempotency_key
                CHECK (LEN(idempotency_key) > 0),
            -- closed command vocabulary, byte-equal to the service module's
            -- ImportReceipt.command values.
            CONSTRAINT CK_myopp_member_import_idempotency_command
                CHECK (command IN (N'submit_paste', N'submit_upload', N'import_from_url', N'delete_import')),
            CONSTRAINT CK_myopp_member_import_idempotency_input_hash
                CHECK (LEN(canonical_input_hash) = 64 AND canonical_input_hash NOT LIKE '%[^0-9a-f]%'),
            -- content-free receipt only: opaque key + outcome + reason +
            -- truncated (doc 09 section 2); never the imported content.
            CONSTRAINT CK_myopp_member_import_idempotency_result_json
                CHECK (ISJSON(result_json) = 1 AND LEFT(LTRIM(result_json), 1) = N'{')
        );

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_member_import_idempotency_immutable
        ON dbo.myopp_member_import_idempotency
        AFTER UPDATE
        AS
        BEGIN
            SET NOCOUNT ON;
            -- DELETE remains allowed (unguarded): the content-blind TTL
            -- purge needs it. Only UPDATE is forbidden.
            THROW 55850, ''Member import idempotency receipts are immutable (the content-blind TTL purge deletes; it never updates).'', 1;
        END');

        CREATE INDEX IX_myopp_member_imports_owner
            ON dbo.myopp_member_imports (user_key, record_state, created_at_utc DESC);
        CREATE INDEX IX_myopp_member_import_stage_outcomes_owner
            ON dbo.myopp_member_import_stage_outcomes (myopp_member_import_id, user_key);
        CREATE INDEX IX_myopp_member_import_idempotency_expiry
            ON dbo.myopp_member_import_idempotency (expires_at_utc);   -- content-blind sweep

        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES (N'PS-MYOPP-006',
                N'Additive My Opportunities C10 owner-scoped private member_import storage: deterministic paste/upload intake (paste, upload, and a schema-complete but C10-unused url_fetch method), sanitized extracted content, the append-only pipeline stage-outcome trail, in-record fetch provenance, dual-retention body-removal tombstones (member delete and rights takedown), and content-free idempotency receipts. No route, provider, AI, C2-C6 file change, fixture row, or production action.',
                N'PeerSlate My Opportunities C10 v0.1');
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
