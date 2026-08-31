/*
 PS-MYOPP-005 — My Opportunities C6 member-side saves and Slate-link
 persistence.

 Additive: owner-fenced saved opportunities following the closed doc 03 §7
 save/remove/undo machine with truthful state/timestamp pairing and terminal
 removed rows, and owner-fenced Slate links (doc 03 §8) with exactly one
 active link per member and opportunity. Reference-only: both tables carry
 canonical keys, never copied role facts, and NO overlay column exists --
 lifecycle overlays are derived at read time and cannot be persisted here.
 No route, UI, provider integration, C2/C3/C4/C5 change, fixture row, job,
 or production action.

 ordering_inputs_json-style scoring is intentionally absent: neither table
 carries any score/probability/rank/relevance column (verifier forbidden-
 column scan enforces it).
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-005')
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-001')
            THROW 55780, 'PS-MYOPP-005 requires PS-MYOPP-001.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-002')
            THROW 55781, 'PS-MYOPP-005 requires PS-MYOPP-002.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-003')
            THROW 55782, 'PS-MYOPP-005 requires PS-MYOPP-003.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-004')
            THROW 55783, 'PS-MYOPP-005 requires PS-MYOPP-004.', 1;

        CREATE TABLE dbo.myopp_saved_opportunities
        (
            myopp_saved_opportunity_id bigint IDENTITY(1,1) NOT NULL,
            save_key uniqueidentifier NOT NULL
                CONSTRAINT DF_myopp_saved_opportunities_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            data_class nvarchar(20) NOT NULL,
            myopp_canonical_opportunity_id bigint NOT NULL,
            last_reviewed_source_version_id bigint NOT NULL,
            state nvarchar(20) NOT NULL
                CONSTRAINT DF_myopp_saved_opportunities_state DEFAULT N'saved',
            saved_at_utc datetime2(7) NOT NULL,
            removal_requested_at_utc datetime2(7) NULL,
            removed_at_utc datetime2(7) NULL,
            created_at_utc datetime2(7) NOT NULL
                CONSTRAINT DF_myopp_saved_opportunities_created DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_saved_opportunities PRIMARY KEY (myopp_saved_opportunity_id),
            CONSTRAINT UQ_myopp_saved_opportunities_key UNIQUE (save_key),
            CONSTRAINT UQ_myopp_saved_opportunities_id_user UNIQUE (myopp_saved_opportunity_id, user_key),
            -- MINOR-13 precedent (PS-MYOPP-004): a second, class-inclusive
            -- uniqueness so a downstream child table can pair its FK on
            -- (id, user_key, data_class) rather than user_key alone.
            CONSTRAINT UQ_myopp_saved_opportunities_id_user_class
                UNIQUE (myopp_saved_opportunity_id, user_key, data_class),
            CONSTRAINT FK_myopp_saved_opportunities_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT FK_myopp_saved_opportunities_opportunity_class
                FOREIGN KEY (myopp_canonical_opportunity_id, data_class)
                REFERENCES dbo.myopp_canonical_opportunities (myopp_canonical_opportunity_id, data_class),
            CONSTRAINT FK_myopp_saved_opportunities_reviewed_version_class
                FOREIGN KEY (last_reviewed_source_version_id, data_class)
                REFERENCES dbo.myopp_source_versions (myopp_source_version_id, data_class),
            CONSTRAINT CK_myopp_saved_opportunities_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_saved_opportunities_state CHECK (state IN (N'saved', N'removing', N'removed')),
            CONSTRAINT CK_myopp_saved_opportunities_state_timestamps CHECK
            (
                (state = N'saved'    AND removal_requested_at_utc IS NULL     AND removed_at_utc IS NULL)
             OR (state = N'removing' AND removal_requested_at_utc IS NOT NULL AND removed_at_utc IS NULL)
             OR (state = N'removed'  AND removal_requested_at_utc IS NOT NULL AND removed_at_utc IS NOT NULL
                                      AND removed_at_utc >= removal_requested_at_utc)
            ),
            CONSTRAINT CK_myopp_saved_opportunities_removal_after_save CHECK
                (removal_requested_at_utc IS NULL OR removal_requested_at_utc >= saved_at_utc)
        );

        -- One active (non-removed) save per member and opportunity, as a
        -- filtered unique index (a CHECK cannot express it; the machine's
        -- "re-save creates a new row" needs removed rows exempt).
        CREATE UNIQUE INDEX UX_myopp_saved_opportunities_active
            ON dbo.myopp_saved_opportunities (user_key, myopp_canonical_opportunity_id)
            WHERE state <> N'removed';

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_saved_opportunities_guard
        ON dbo.myopp_saved_opportunities
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;

            IF EXISTS
            (
                SELECT 1 FROM deleted d
                LEFT JOIN inserted i ON i.myopp_saved_opportunity_id = d.myopp_saved_opportunity_id
                WHERE i.myopp_saved_opportunity_id IS NULL
            )
                -- IMPORTANT 3: MERGE-safe form (PS-MYOPP-004 idiom) -- a
                -- MERGE statement can populate both `inserted` and
                -- `deleted` in the same trigger firing even for rows it
                -- deletes; the LEFT JOIN isolates genuinely deleted rows
                -- (no matching row survives in `inserted`) rather than
                -- assuming a non-empty `inserted` table means no DELETE
                -- occurred at all.
                THROW 55784, ''Saved opportunities are member data; no erasure path exists in this schema (future erasure package).'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_saved_opportunity_id = i.myopp_saved_opportunity_id
                WHERE i.save_key <> d.save_key OR i.user_key <> d.user_key OR i.data_class <> d.data_class
                   OR i.myopp_canonical_opportunity_id <> d.myopp_canonical_opportunity_id
                   OR i.saved_at_utc <> d.saved_at_utc OR i.created_at_utc <> d.created_at_utc
            )
                THROW 55785, ''Saved opportunity identity is immutable.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_saved_opportunity_id = i.myopp_saved_opportunity_id
                WHERE d.state = N''removed''
            )
                -- IMPORTANT 8 idiom (PS-MYOPP-004): fires on ANY update of a
                -- row whose prior state was terminal, not only an update
                -- that changes state.
                THROW 55786, ''A terminal (removed) saved opportunity row cannot be updated.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_saved_opportunity_id = i.myopp_saved_opportunity_id
                WHERE i.state <> d.state
                  AND NOT EXISTS
                  (
                      SELECT 1 FROM (VALUES
                          (N''saved'', N''removing''), (N''removing'', N''saved''), (N''removing'', N''removed'')
                      ) legal(from_state, to_state)
                      WHERE legal.from_state = d.state AND legal.to_state = i.state
                  )
            )
                THROW 55787, ''Illegal saved opportunity state transition.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_saved_opportunity_id = i.myopp_saved_opportunity_id
                WHERE
                (
                    -- BLOCKER 1: a Boolean expression like
                    -- "(x IS NULL) <> (y IS NULL)" is not valid T-SQL
                    -- (sql_variant/Boolean comparison is refused); use the
                    -- repo''s value-level ISNULL-sentinel idiom instead
                    -- (PS-MYOPP-001 pattern) so a NULL<->non-NULL change is
                    -- caught by ordinary value inequality.
                    ISNULL(i.removal_requested_at_utc, N''00010101'') <> ISNULL(d.removal_requested_at_utc, N''00010101'')
                    AND NOT
                    (
                        (d.state = N''saved'' AND i.state = N''removing''
                         AND d.removal_requested_at_utc IS NULL AND i.removal_requested_at_utc IS NOT NULL)
                     OR (d.state = N''removing'' AND i.state = N''saved'' AND i.removal_requested_at_utc IS NULL)
                    )
                )
                OR
                (
                    ISNULL(i.removed_at_utc, N''00010101'') <> ISNULL(d.removed_at_utc, N''00010101'')
                    AND NOT
                    (
                        d.state = N''removing'' AND i.state = N''removed''
                        AND d.removed_at_utc IS NULL AND i.removed_at_utc IS NOT NULL
                    )
                )
            )
                THROW 55788, ''Saved opportunity removal_requested_at/removed_at may change only on their legal transition.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_saved_opportunity_id = i.myopp_saved_opportunity_id
                WHERE i.last_reviewed_source_version_id <> d.last_reviewed_source_version_id
                  AND i.state <> d.state
            )
                -- last_reviewed_source_version_id may change only when the
                -- row''s state is UNCHANGED by that same update (member
                -- review is not a state transition); 55786 above already
                -- refuses any update at all of a prior-removed row, so the
                -- surviving case here is always a non-removed state.
                THROW 55789, ''last_reviewed_source_version_id may change only via member review while the state is unchanged.'', 1;
        END');

        CREATE TABLE dbo.myopp_slate_links
        (
            myopp_slate_link_id bigint IDENTITY(1,1) NOT NULL,
            link_key uniqueidentifier NOT NULL
                CONSTRAINT DF_myopp_slate_links_key DEFAULT NEWID(),
            user_key nvarchar(300) NOT NULL,
            data_class nvarchar(20) NOT NULL,
            myopp_canonical_opportunity_id bigint NOT NULL,
            slate_workspace_ref nvarchar(200) NOT NULL,
            created_from nvarchar(20) NOT NULL,
            handoff_source_version_id bigint NOT NULL,
            state nvarchar(20) NOT NULL
                CONSTRAINT DF_myopp_slate_links_state DEFAULT N'linked',
            created_at_utc datetime2(7) NOT NULL,
            unlinked_at_utc datetime2(7) NULL,
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_slate_links PRIMARY KEY (myopp_slate_link_id),
            CONSTRAINT UQ_myopp_slate_links_key UNIQUE (link_key),
            CONSTRAINT UQ_myopp_slate_links_id_user UNIQUE (myopp_slate_link_id, user_key),
            CONSTRAINT UQ_myopp_slate_links_id_user_class
                UNIQUE (myopp_slate_link_id, user_key, data_class),
            CONSTRAINT FK_myopp_slate_links_user FOREIGN KEY (user_key)
                REFERENCES dbo.app_users (user_key),
            CONSTRAINT FK_myopp_slate_links_opportunity_class
                FOREIGN KEY (myopp_canonical_opportunity_id, data_class)
                REFERENCES dbo.myopp_canonical_opportunities (myopp_canonical_opportunity_id, data_class),
            CONSTRAINT FK_myopp_slate_links_handoff_version_class
                FOREIGN KEY (handoff_source_version_id, data_class)
                REFERENCES dbo.myopp_source_versions (myopp_source_version_id, data_class),
            CONSTRAINT CK_myopp_slate_links_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_slate_links_state CHECK (state IN (N'linked', N'unlinked')),
            CONSTRAINT CK_myopp_slate_links_created_from CHECK (created_from IN (N'result', N'saved')),
            CONSTRAINT CK_myopp_slate_links_state_timestamps CHECK
            (
                (state = N'linked'   AND unlinked_at_utc IS NULL)
             OR (state = N'unlinked' AND unlinked_at_utc IS NOT NULL AND unlinked_at_utc >= created_at_utc)
            ),
            CONSTRAINT CK_myopp_slate_links_workspace_ref CHECK (LEN(slate_workspace_ref) > 0)
        );

        -- Exactly one ACTIVE link per (member, opportunity) -- doc 03 §8.
        CREATE UNIQUE INDEX UX_myopp_slate_links_active
            ON dbo.myopp_slate_links (user_key, myopp_canonical_opportunity_id)
            WHERE state = N'linked';

        EXEC(N'
        CREATE TRIGGER dbo.trg_myopp_slate_links_guard
        ON dbo.myopp_slate_links
        AFTER UPDATE, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;

            IF EXISTS
            (
                SELECT 1 FROM deleted d
                LEFT JOIN inserted i ON i.myopp_slate_link_id = d.myopp_slate_link_id
                WHERE i.myopp_slate_link_id IS NULL
            )
                -- IMPORTANT 3: MERGE-safe form (PS-MYOPP-004 idiom); see the
                -- matching note on trg_myopp_saved_opportunities_guard.
                THROW 55790, ''Slate links are member history; no erasure path exists in this schema (future erasure package).'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_slate_link_id = i.myopp_slate_link_id
                WHERE i.link_key <> d.link_key OR i.user_key <> d.user_key OR i.data_class <> d.data_class
                   OR i.myopp_canonical_opportunity_id <> d.myopp_canonical_opportunity_id
                   OR i.slate_workspace_ref <> d.slate_workspace_ref OR i.created_from <> d.created_from
                   OR i.handoff_source_version_id <> d.handoff_source_version_id
                   OR i.created_at_utc <> d.created_at_utc
            )
                THROW 55791, ''Slate link identity is immutable.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_slate_link_id = i.myopp_slate_link_id
                WHERE d.state = N''unlinked''
            )
                THROW 55792, ''A terminal (unlinked) Slate link row cannot be updated.'', 1;

            IF EXISTS
            (
                SELECT 1 FROM inserted i JOIN deleted d ON d.myopp_slate_link_id = i.myopp_slate_link_id
                WHERE
                (
                    i.state <> d.state
                    AND NOT (d.state = N''linked'' AND i.state = N''unlinked'')
                )
                OR
                (
                    -- BLOCKER 1: ISNULL-sentinel idiom, as above.
                    i.state = d.state
                    AND ISNULL(i.unlinked_at_utc, N''00010101'') <> ISNULL(d.unlinked_at_utc, N''00010101'')
                )
                OR
                (
                    d.state = N''linked'' AND i.state = N''unlinked''
                    AND NOT (d.unlinked_at_utc IS NULL AND i.unlinked_at_utc IS NOT NULL)
                )
            )
                THROW 55793, ''Illegal Slate link transition, or unlinked_at may be set only exactly on linked->unlinked and never changed again.'', 1;
        END');

        CREATE INDEX IX_myopp_saved_opportunities_owner
            ON dbo.myopp_saved_opportunities (user_key, state, saved_at_utc DESC);
        CREATE INDEX IX_myopp_saved_opportunities_finalize
            ON dbo.myopp_saved_opportunities (state, removal_requested_at_utc);   -- content-blind sweep
        CREATE INDEX IX_myopp_slate_links_owner
            ON dbo.myopp_slate_links (user_key, myopp_canonical_opportunity_id, state);

        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES (N'PS-MYOPP-005',
                N'Additive My Opportunities C6 member-side saves and Slate-link persistence: owner-fenced saved opportunities with the closed save/remove/undo machine, undo window, terminal removed rows, one active save per member and opportunity, and last-reviewed source-version recording; owner-fenced Slate links with one active link and unlinked history. Reference-only bindings; no overlay, score, or copied-content column; no route, UI, provider, or production action.',
                N'PeerSlate My Opportunities C6 v0.1');
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
