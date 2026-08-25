/*
 PS-MYOPP-001 — My Opportunities C2 canonical shared-side foundation.

 Additive-only, shared-side schema for provider-neutral source policy,
 immutable receipts/versions, source lifecycle heads, canonical opportunities,
 requirement versions, content-free canonical events, and rights tombstones.
 Every object is deliberately named dbo.myopp_* and has no member/owner table,
 key, foreign key, or cross-class relationship. This migration creates no
 scheduler, connector credential, external provider call, route, or fixture
 rows. Application persistence remains behind C2's injected repository seam.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-001')
    BEGIN
        CREATE TABLE dbo.myopp_source_policies
        (
            myopp_source_policy_id bigint IDENTITY(1,1) NOT NULL,
            policy_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_source_policies_key DEFAULT NEWID(),
            policy_version int NOT NULL,
            source_id nvarchar(160) NOT NULL,
            source_class nvarchar(80) NOT NULL,
            data_class nvarchar(20) NOT NULL,
            source_priority int NOT NULL,
            effective_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_source_policies_effective DEFAULT SYSUTCDATETIME(),
            expires_at_utc datetime2(7) NULL,
            evidence_ref nvarchar(500) NOT NULL,
            decision_ref nvarchar(500) NOT NULL,
            display_allowed bit NOT NULL,
            excerpt_allowed bit NOT NULL,
            full_description_allowed bit NOT NULL,
            storage_allowed bit NOT NULL,
            ai_ml_allowed bit NOT NULL,
            caching_allowed bit NOT NULL,
            retention_allowed bit NOT NULL,
            attribution_allowed bit NOT NULL,
            removal_allowed bit NOT NULL,
            termination_allowed bit NOT NULL,
            exit_allowed bit NOT NULL,
            survivable_minimal_facts_allowed bit NOT NULL,
            allowed_actions_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_source_policies_allowed_actions DEFAULT N'[]',
            retained_source_fields_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_source_policies_retained_fields DEFAULT N'[]',
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_source_policies PRIMARY KEY (myopp_source_policy_id),
            CONSTRAINT UQ_myopp_source_policies_key_class_version UNIQUE (policy_key, data_class, policy_version),
            CONSTRAINT UQ_myopp_source_policies_source_class_version UNIQUE (data_class, source_id, policy_version),
            CONSTRAINT UQ_myopp_source_policies_id_class UNIQUE (myopp_source_policy_id, data_class),
            CONSTRAINT UQ_myopp_source_policies_id_class_source UNIQUE (myopp_source_policy_id, data_class, source_id),
            CONSTRAINT CK_myopp_source_policies_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_source_policies_version CHECK (policy_version > 0),
            CONSTRAINT CK_myopp_source_policies_priority CHECK (source_priority >= 0),
            CONSTRAINT CK_myopp_source_policies_expiry CHECK (expires_at_utc IS NULL OR expires_at_utc > effective_at_utc),
            CONSTRAINT CK_myopp_source_policies_allowed_actions_json CHECK (ISJSON(allowed_actions_json) = 1 AND LEFT(LTRIM(allowed_actions_json), 1) = N'['),
            CONSTRAINT CK_myopp_source_policies_retained_fields_json CHECK (ISJSON(retained_source_fields_json) = 1 AND LEFT(LTRIM(retained_source_fields_json), 1) = N'['),
            CONSTRAINT CK_myopp_source_policies_strict_false_retention CHECK (survivable_minimal_facts_allowed = 1 OR retained_source_fields_json = N'[]')
        );

        CREATE TABLE dbo.myopp_canonical_opportunities
        (
            myopp_canonical_opportunity_id bigint IDENTITY(1,1) NOT NULL,
            opportunity_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_canonical_opportunities_key DEFAULT NEWID(),
            data_class nvarchar(20) NOT NULL,
            governing_listing_id bigint NULL,
            governing_source_version_id bigint NULL,
            current_requirement_version_id bigint NULL,
            tombstone_target_opportunity_id bigint NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_canonical_opportunities_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_canonical_opportunities_updated DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_canonical_opportunities PRIMARY KEY (myopp_canonical_opportunity_id),
            CONSTRAINT UQ_myopp_canonical_opportunities_key UNIQUE (opportunity_key),
            CONSTRAINT UQ_myopp_canonical_opportunities_id_class UNIQUE (myopp_canonical_opportunity_id, data_class),
            CONSTRAINT CK_myopp_canonical_opportunities_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_canonical_opportunities_no_self_tombstone CHECK (tombstone_target_opportunity_id IS NULL OR tombstone_target_opportunity_id <> myopp_canonical_opportunity_id)
        );

        CREATE TABLE dbo.myopp_source_receipts
        (
            myopp_source_receipt_id bigint IDENTITY(1,1) NOT NULL,
            receipt_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_source_receipts_key DEFAULT NEWID(),
            myopp_source_policy_id bigint NOT NULL,
            data_class nvarchar(20) NOT NULL,
            source_id nvarchar(160) NULL,
            external_reference nvarchar(300) NULL,
            received_at_utc datetime2(7) NULL,
            content_type nvarchar(255) NULL,
            byte_count bigint NULL,
            payload_sha256 char(64) NULL,
            payload_body varbinary(max) NULL,
            content_tombstoned_at_utc datetime2(7) NULL,
            myopp_terminal_policy_id bigint NULL,
            terminal_policy_version int NULL,
            terminal_disposition nvarchar(20) NULL,
            tombstone_reason nvarchar(80) NULL,
            terminal_actor nvarchar(160) NULL,
            retained_source_fields_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_source_receipts_retained_fields DEFAULT N'[]',
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_source_receipts_created DEFAULT SYSUTCDATETIME(),
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_source_receipts PRIMARY KEY (myopp_source_receipt_id),
            CONSTRAINT UQ_myopp_source_receipts_key UNIQUE (receipt_key),
            CONSTRAINT UQ_myopp_source_receipts_id_class UNIQUE (myopp_source_receipt_id, data_class),
            CONSTRAINT FK_myopp_source_receipts_policy_class FOREIGN KEY (myopp_source_policy_id, data_class) REFERENCES dbo.myopp_source_policies (myopp_source_policy_id, data_class),
            CONSTRAINT FK_myopp_source_receipts_terminal_policy_class FOREIGN KEY (myopp_terminal_policy_id, data_class) REFERENCES dbo.myopp_source_policies (myopp_source_policy_id, data_class),
            CONSTRAINT CK_myopp_source_receipts_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_source_receipts_byte_count CHECK (byte_count IS NULL OR byte_count > 0),
            CONSTRAINT CK_myopp_source_receipts_sha CHECK (payload_sha256 IS NULL OR payload_sha256 NOT LIKE '%[^0-9a-f]%'),
            CONSTRAINT CK_myopp_source_receipts_retained_fields_json CHECK (ISJSON(retained_source_fields_json) = 1 AND LEFT(LTRIM(retained_source_fields_json), 1) = N'['),
            CONSTRAINT CK_myopp_source_receipts_tombstone CHECK
            (
                (content_tombstoned_at_utc IS NULL
                 AND myopp_terminal_policy_id IS NULL AND terminal_policy_version IS NULL
                 AND terminal_disposition IS NULL AND tombstone_reason IS NULL AND terminal_actor IS NULL
                 AND source_id IS NOT NULL AND external_reference IS NOT NULL
                 AND received_at_utc IS NOT NULL AND content_type IS NOT NULL AND byte_count IS NOT NULL
                 AND payload_body IS NOT NULL AND payload_sha256 IS NOT NULL
                 AND retained_source_fields_json = N'[]')
                OR
                (content_tombstoned_at_utc IS NOT NULL
                 AND myopp_terminal_policy_id IS NOT NULL AND terminal_policy_version > 0
                 AND terminal_disposition IN (N'removal', N'termination')
                 AND tombstone_reason IS NOT NULL AND terminal_actor IS NOT NULL)
            )
        );

        CREATE TABLE dbo.myopp_source_listings
        (
            myopp_source_listing_id bigint IDENTITY(1,1) NOT NULL,
            listing_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_source_listings_key DEFAULT NEWID(),
            myopp_source_policy_id bigint NOT NULL,
            myopp_canonical_opportunity_id bigint NOT NULL,
            data_class nvarchar(20) NOT NULL,
            source_id nvarchar(160) NULL,
            external_reference nvarchar(300) NULL,
            application_url nvarchar(2048) NULL,
            expected_application_hosts_json nvarchar(max) NULL,
            listing_state nvarchar(30) NOT NULL,
            application_link_state nvarchar(20) NOT NULL CONSTRAINT DF_myopp_source_listings_link_state DEFAULT N'unknown',
            application_link_invalid_reason nvarchar(30) NULL,
            link_last_attempted_at_utc datetime2(7) NULL,
            link_last_validated_at_utc datetime2(7) NULL,
            last_attempted_at_utc datetime2(7) NULL,
            last_successfully_verified_at_utc datetime2(7) NULL,
            link_review_pending bit NOT NULL CONSTRAINT DF_myopp_source_listings_link_review DEFAULT 0,
            current_source_version_id bigint NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_source_listings_created DEFAULT SYSUTCDATETIME(),
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_source_listings_updated DEFAULT SYSUTCDATETIME(),
            content_tombstoned_at_utc datetime2(7) NULL,
            myopp_terminal_policy_id bigint NULL,
            terminal_policy_version int NULL,
            terminal_disposition nvarchar(20) NULL,
            tombstone_reason nvarchar(80) NULL,
            terminal_actor nvarchar(160) NULL,
            retained_source_fields_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_source_listings_retained_fields DEFAULT N'[]',
            row_version rowversion NOT NULL,
            CONSTRAINT PK_myopp_source_listings PRIMARY KEY (myopp_source_listing_id),
            CONSTRAINT UQ_myopp_source_listings_key UNIQUE (listing_key),
            CONSTRAINT UQ_myopp_source_listings_id_class UNIQUE (myopp_source_listing_id, data_class),
            CONSTRAINT FK_myopp_source_listings_policy_source_class FOREIGN KEY (myopp_source_policy_id, data_class, source_id) REFERENCES dbo.myopp_source_policies (myopp_source_policy_id, data_class, source_id),
            CONSTRAINT FK_myopp_source_listings_opportunity_class FOREIGN KEY (myopp_canonical_opportunity_id, data_class) REFERENCES dbo.myopp_canonical_opportunities (myopp_canonical_opportunity_id, data_class),
            CONSTRAINT FK_myopp_source_listings_terminal_policy_class FOREIGN KEY (myopp_terminal_policy_id, data_class) REFERENCES dbo.myopp_source_policies (myopp_source_policy_id, data_class),
            CONSTRAINT CK_myopp_source_listings_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_source_listings_state CHECK (listing_state IN (N'intake', N'current', N'changed', N'closed', N'unreachable', N'stale', N'quarantined', N'invalid')),
            CONSTRAINT CK_myopp_source_listings_link_state CHECK (application_link_state IN (N'valid', N'invalid', N'unknown')),
            CONSTRAINT CK_myopp_source_listings_link_reason CHECK ((application_link_state = N'invalid' AND application_link_invalid_reason IN (N'unresolvable', N'soft_closed', N'host_mismatch', N'blocked')) OR (application_link_state <> N'invalid' AND application_link_invalid_reason IS NULL)),
            CONSTRAINT CK_myopp_source_listings_success_after_attempt CHECK (last_successfully_verified_at_utc IS NULL OR last_attempted_at_utc IS NULL OR last_successfully_verified_at_utc <= last_attempted_at_utc),
            CONSTRAINT CK_myopp_source_listings_link_success_after_attempt CHECK (link_last_validated_at_utc IS NULL OR link_last_attempted_at_utc IS NULL OR link_last_validated_at_utc <= link_last_attempted_at_utc),
            CONSTRAINT CK_myopp_source_listings_expected_hosts_json CHECK (expected_application_hosts_json IS NULL OR (ISJSON(expected_application_hosts_json) = 1 AND LEFT(LTRIM(expected_application_hosts_json), 1) = N'[')),
            CONSTRAINT CK_myopp_source_listings_retained_fields_json CHECK (ISJSON(retained_source_fields_json) = 1 AND LEFT(LTRIM(retained_source_fields_json), 1) = N'['),
            CONSTRAINT CK_myopp_source_listings_tombstone CHECK
            (
                (content_tombstoned_at_utc IS NULL
                 AND myopp_terminal_policy_id IS NULL AND terminal_policy_version IS NULL
                 AND terminal_disposition IS NULL AND tombstone_reason IS NULL AND terminal_actor IS NULL
                 AND source_id IS NOT NULL AND external_reference IS NOT NULL AND application_url IS NOT NULL
                 AND expected_application_hosts_json IS NOT NULL AND retained_source_fields_json = N'[]')
                OR
                (content_tombstoned_at_utc IS NOT NULL
                 AND myopp_terminal_policy_id IS NOT NULL AND terminal_policy_version > 0
                 AND terminal_disposition IN (N'removal', N'termination')
                 AND tombstone_reason IS NOT NULL AND terminal_actor IS NOT NULL)
            )
        );

        CREATE UNIQUE INDEX UX_myopp_source_listings_active_source_reference
            ON dbo.myopp_source_listings (data_class, source_id, external_reference)
            WHERE source_id IS NOT NULL AND external_reference IS NOT NULL;

        CREATE TABLE dbo.myopp_source_versions
        (
            myopp_source_version_id bigint IDENTITY(1,1) NOT NULL,
            source_version_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_source_versions_key DEFAULT NEWID(),
            myopp_source_listing_id bigint NOT NULL,
            myopp_source_receipt_id bigint NOT NULL,
            data_class nvarchar(20) NOT NULL,
            content_sha256 char(64) NULL,
            observed_at_utc datetime2(7) NULL,
            employer_name nvarchar(300) NULL,
            role_title nvarchar(300) NULL,
            locations_json nvarchar(max) NULL,
            arrangement nvarchar(80) NULL,
            application_url nvarchar(2048) NULL,
            source_body nvarchar(max) NULL,
            normalized_fields_json nvarchar(max) NULL,
            normalized_requirements_json nvarchar(max) NULL,
            content_tombstoned_at_utc datetime2(7) NULL,
            myopp_terminal_policy_id bigint NULL,
            terminal_policy_version int NULL,
            terminal_disposition nvarchar(20) NULL,
            tombstone_reason nvarchar(80) NULL,
            terminal_actor nvarchar(160) NULL,
            retained_source_fields_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_source_versions_retained_fields DEFAULT N'[]',
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_source_versions_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_source_versions PRIMARY KEY (myopp_source_version_id),
            CONSTRAINT UQ_myopp_source_versions_key UNIQUE (source_version_key),
            CONSTRAINT UQ_myopp_source_versions_id_class UNIQUE (myopp_source_version_id, data_class),
            CONSTRAINT FK_myopp_source_versions_listing_class FOREIGN KEY (myopp_source_listing_id, data_class) REFERENCES dbo.myopp_source_listings (myopp_source_listing_id, data_class),
            CONSTRAINT FK_myopp_source_versions_receipt_class FOREIGN KEY (myopp_source_receipt_id, data_class) REFERENCES dbo.myopp_source_receipts (myopp_source_receipt_id, data_class),
            CONSTRAINT FK_myopp_source_versions_terminal_policy_class FOREIGN KEY (myopp_terminal_policy_id, data_class) REFERENCES dbo.myopp_source_policies (myopp_source_policy_id, data_class),
            CONSTRAINT CK_myopp_source_versions_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_source_versions_hash CHECK (content_sha256 IS NULL OR content_sha256 NOT LIKE '%[^0-9a-f]%'),
            CONSTRAINT CK_myopp_source_versions_retained_fields_json CHECK (ISJSON(retained_source_fields_json) = 1 AND LEFT(LTRIM(retained_source_fields_json), 1) = N'['),
            CONSTRAINT CK_myopp_source_versions_tombstone CHECK
            (
                (content_tombstoned_at_utc IS NULL
                 AND myopp_terminal_policy_id IS NULL AND terminal_policy_version IS NULL
                 AND terminal_disposition IS NULL AND tombstone_reason IS NULL AND terminal_actor IS NULL
                 AND content_sha256 IS NOT NULL AND observed_at_utc IS NOT NULL
                 AND employer_name IS NOT NULL AND role_title IS NOT NULL AND locations_json IS NOT NULL
                 AND arrangement IS NOT NULL AND application_url IS NOT NULL AND source_body IS NOT NULL
                 AND normalized_fields_json IS NOT NULL AND normalized_requirements_json IS NOT NULL
                 AND ISJSON(locations_json) = 1 AND ISJSON(normalized_fields_json) = 1 AND ISJSON(normalized_requirements_json) = 1
                 AND retained_source_fields_json = N'[]')
                OR
                (content_tombstoned_at_utc IS NOT NULL
                 AND myopp_terminal_policy_id IS NOT NULL AND terminal_policy_version > 0
                 AND terminal_disposition IN (N'removal', N'termination')
                 AND tombstone_reason IS NOT NULL AND terminal_actor IS NOT NULL)
            )
        );

        CREATE UNIQUE INDEX UX_myopp_source_versions_active_listing_hash
            ON dbo.myopp_source_versions (myopp_source_listing_id, data_class, content_sha256)
            WHERE content_sha256 IS NOT NULL;

        CREATE TABLE dbo.myopp_source_version_receipt_links
        (
            myopp_source_version_receipt_link_id bigint IDENTITY(1,1) NOT NULL,
            myopp_source_version_id bigint NOT NULL,
            myopp_source_receipt_id bigint NOT NULL,
            data_class nvarchar(20) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_source_version_receipt_links_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_source_version_receipt_links PRIMARY KEY (myopp_source_version_receipt_link_id),
            CONSTRAINT UQ_myopp_source_version_receipt_links_pair_class UNIQUE (myopp_source_version_id, myopp_source_receipt_id, data_class),
            CONSTRAINT UQ_myopp_source_version_receipt_links_receipt_class UNIQUE (myopp_source_receipt_id, data_class),
            CONSTRAINT UQ_myopp_source_version_receipt_links_id_class UNIQUE (myopp_source_version_receipt_link_id, data_class),
            CONSTRAINT FK_myopp_source_version_receipt_links_version_class FOREIGN KEY (myopp_source_version_id, data_class) REFERENCES dbo.myopp_source_versions (myopp_source_version_id, data_class),
            CONSTRAINT FK_myopp_source_version_receipt_links_receipt_class FOREIGN KEY (myopp_source_receipt_id, data_class) REFERENCES dbo.myopp_source_receipts (myopp_source_receipt_id, data_class),
            CONSTRAINT CK_myopp_source_version_receipt_links_data_class CHECK (data_class IN (N'fixture', N'production'))
        );

        ALTER TABLE dbo.myopp_source_listings ADD CONSTRAINT FK_myopp_source_listings_current_version_class FOREIGN KEY (current_source_version_id, data_class) REFERENCES dbo.myopp_source_versions (myopp_source_version_id, data_class);

        CREATE TABLE dbo.myopp_requirement_versions
        (
            myopp_requirement_version_id bigint IDENTITY(1,1) NOT NULL,
            requirement_version_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_requirement_versions_key DEFAULT NEWID(),
            myopp_canonical_opportunity_id bigint NOT NULL,
            myopp_source_version_id bigint NOT NULL,
            data_class nvarchar(20) NOT NULL,
            clause_fingerprint char(64) NULL,
            derived_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_requirement_versions_derived DEFAULT SYSUTCDATETIME(),
            content_tombstoned_at_utc datetime2(7) NULL,
            myopp_terminal_policy_id bigint NULL,
            terminal_policy_version int NULL,
            terminal_disposition nvarchar(20) NULL,
            tombstone_reason nvarchar(80) NULL,
            terminal_actor nvarchar(160) NULL,
            retained_source_fields_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_requirement_versions_retained_fields DEFAULT N'[]',
            CONSTRAINT PK_myopp_requirement_versions PRIMARY KEY (myopp_requirement_version_id),
            CONSTRAINT UQ_myopp_requirement_versions_key UNIQUE (requirement_version_key),
            CONSTRAINT UQ_myopp_requirement_versions_id_class UNIQUE (myopp_requirement_version_id, data_class),
            CONSTRAINT FK_myopp_requirement_versions_opportunity_class FOREIGN KEY (myopp_canonical_opportunity_id, data_class) REFERENCES dbo.myopp_canonical_opportunities (myopp_canonical_opportunity_id, data_class),
            CONSTRAINT FK_myopp_requirement_versions_source_version_class FOREIGN KEY (myopp_source_version_id, data_class) REFERENCES dbo.myopp_source_versions (myopp_source_version_id, data_class),
            CONSTRAINT FK_myopp_requirement_versions_terminal_policy_class FOREIGN KEY (myopp_terminal_policy_id, data_class) REFERENCES dbo.myopp_source_policies (myopp_source_policy_id, data_class),
            CONSTRAINT CK_myopp_requirement_versions_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_requirement_versions_fingerprint CHECK (clause_fingerprint IS NULL OR clause_fingerprint NOT LIKE '%[^0-9a-f]%'),
            CONSTRAINT CK_myopp_requirement_versions_retained_fields_json CHECK (ISJSON(retained_source_fields_json) = 1 AND LEFT(LTRIM(retained_source_fields_json), 1) = N'['),
            CONSTRAINT CK_myopp_requirement_versions_tombstone CHECK
            (
                (content_tombstoned_at_utc IS NULL
                 AND myopp_terminal_policy_id IS NULL AND terminal_policy_version IS NULL
                 AND terminal_disposition IS NULL AND tombstone_reason IS NULL AND terminal_actor IS NULL
                 AND clause_fingerprint IS NOT NULL AND retained_source_fields_json = N'[]')
                OR
                (content_tombstoned_at_utc IS NOT NULL
                 AND myopp_terminal_policy_id IS NOT NULL AND terminal_policy_version > 0
                 AND terminal_disposition IN (N'removal', N'termination')
                 AND tombstone_reason IS NOT NULL AND terminal_actor IS NOT NULL)
            )
        );

        CREATE UNIQUE INDEX UX_myopp_requirement_versions_active_opportunity_fingerprint
            ON dbo.myopp_requirement_versions (myopp_canonical_opportunity_id, data_class, clause_fingerprint)
            WHERE clause_fingerprint IS NOT NULL;

        CREATE TABLE dbo.myopp_requirement_items
        (
            myopp_requirement_item_id bigint IDENTITY(1,1) NOT NULL,
            requirement_item_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_requirement_items_key DEFAULT NEWID(),
            myopp_requirement_version_id bigint NOT NULL,
            data_class nvarchar(20) NOT NULL,
            ordinal int NULL,
            normalized_clause nvarchar(max) NULL,
            requirement_class nvarchar(20) NULL,
            source_span_start int NULL,
            source_span_length int NULL,
            classification_basis nvarchar(80) NULL,
            content_tombstoned_at_utc datetime2(7) NULL,
            myopp_terminal_policy_id bigint NULL,
            terminal_policy_version int NULL,
            terminal_disposition nvarchar(20) NULL,
            tombstone_reason nvarchar(80) NULL,
            terminal_actor nvarchar(160) NULL,
            retained_source_fields_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_requirement_items_retained_fields DEFAULT N'[]',
            CONSTRAINT PK_myopp_requirement_items PRIMARY KEY (myopp_requirement_item_id),
            CONSTRAINT UQ_myopp_requirement_items_key UNIQUE (requirement_item_key),
            CONSTRAINT UQ_myopp_requirement_items_id_class UNIQUE (myopp_requirement_item_id, data_class),
            CONSTRAINT FK_myopp_requirement_items_version_class FOREIGN KEY (myopp_requirement_version_id, data_class) REFERENCES dbo.myopp_requirement_versions (myopp_requirement_version_id, data_class),
            CONSTRAINT FK_myopp_requirement_items_terminal_policy_class FOREIGN KEY (myopp_terminal_policy_id, data_class) REFERENCES dbo.myopp_source_policies (myopp_source_policy_id, data_class),
            CONSTRAINT CK_myopp_requirement_items_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_requirement_items_ordinal CHECK (ordinal IS NULL OR ordinal > 0),
            CONSTRAINT CK_myopp_requirement_items_class CHECK (requirement_class IS NULL OR requirement_class IN (N'required', N'preferred')),
            CONSTRAINT CK_myopp_requirement_items_span CHECK ((source_span_start = -1 AND source_span_length = -1) OR (source_span_start >= 0 AND source_span_length > 0) OR (source_span_start IS NULL AND source_span_length IS NULL)),
            CONSTRAINT CK_myopp_requirement_items_retained_fields_json CHECK (ISJSON(retained_source_fields_json) = 1 AND LEFT(LTRIM(retained_source_fields_json), 1) = N'['),
            CONSTRAINT CK_myopp_requirement_items_tombstone CHECK
            (
                (content_tombstoned_at_utc IS NULL
                 AND myopp_terminal_policy_id IS NULL AND terminal_policy_version IS NULL
                 AND terminal_disposition IS NULL AND tombstone_reason IS NULL AND terminal_actor IS NULL
                 AND ordinal IS NOT NULL AND normalized_clause IS NOT NULL AND requirement_class IS NOT NULL
                 AND source_span_start IS NOT NULL AND source_span_length IS NOT NULL
                 AND classification_basis IS NOT NULL AND retained_source_fields_json = N'[]')
                OR
                (content_tombstoned_at_utc IS NOT NULL
                 AND myopp_terminal_policy_id IS NOT NULL AND terminal_policy_version > 0
                 AND terminal_disposition IN (N'removal', N'termination')
                 AND tombstone_reason IS NOT NULL AND terminal_actor IS NOT NULL)
            )
        );

        CREATE UNIQUE INDEX UX_myopp_requirement_items_active_version_ordinal
            ON dbo.myopp_requirement_items (myopp_requirement_version_id, data_class, ordinal)
            WHERE ordinal IS NOT NULL;

        ALTER TABLE dbo.myopp_canonical_opportunities ADD CONSTRAINT FK_myopp_canonical_opportunities_tombstone_class FOREIGN KEY (tombstone_target_opportunity_id, data_class) REFERENCES dbo.myopp_canonical_opportunities (myopp_canonical_opportunity_id, data_class);
        ALTER TABLE dbo.myopp_canonical_opportunities ADD CONSTRAINT FK_myopp_canonical_opportunities_governing_listing_class FOREIGN KEY (governing_listing_id, data_class) REFERENCES dbo.myopp_source_listings (myopp_source_listing_id, data_class);
        ALTER TABLE dbo.myopp_canonical_opportunities ADD CONSTRAINT FK_myopp_canonical_opportunities_governing_version_class FOREIGN KEY (governing_source_version_id, data_class) REFERENCES dbo.myopp_source_versions (myopp_source_version_id, data_class);
        ALTER TABLE dbo.myopp_canonical_opportunities ADD CONSTRAINT FK_myopp_canonical_opportunities_requirement_version_class FOREIGN KEY (current_requirement_version_id, data_class) REFERENCES dbo.myopp_requirement_versions (myopp_requirement_version_id, data_class);

        CREATE TABLE dbo.myopp_canonical_field_attributions
        (
            myopp_canonical_field_attribution_id bigint IDENTITY(1,1) NOT NULL,
            myopp_canonical_opportunity_id bigint NOT NULL,
            field_name nvarchar(100) NULL,
            myopp_source_listing_id bigint NOT NULL,
            myopp_source_version_id bigint NOT NULL,
            data_class nvarchar(20) NOT NULL,
            recorded_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_canonical_field_attributions_recorded DEFAULT SYSUTCDATETIME(),
            content_tombstoned_at_utc datetime2(7) NULL,
            myopp_terminal_policy_id bigint NULL,
            terminal_policy_version int NULL,
            terminal_disposition nvarchar(20) NULL,
            tombstone_reason nvarchar(80) NULL,
            terminal_actor nvarchar(160) NULL,
            retained_source_fields_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_canonical_field_attributions_retained_fields DEFAULT N'[]',
            CONSTRAINT PK_myopp_canonical_field_attributions PRIMARY KEY (myopp_canonical_field_attribution_id),
            CONSTRAINT UQ_myopp_canonical_field_attributions_id_class UNIQUE (myopp_canonical_field_attribution_id, data_class),
            CONSTRAINT FK_myopp_canonical_field_attributions_opportunity_class FOREIGN KEY (myopp_canonical_opportunity_id, data_class) REFERENCES dbo.myopp_canonical_opportunities (myopp_canonical_opportunity_id, data_class),
            CONSTRAINT FK_myopp_canonical_field_attributions_listing_class FOREIGN KEY (myopp_source_listing_id, data_class) REFERENCES dbo.myopp_source_listings (myopp_source_listing_id, data_class),
            CONSTRAINT FK_myopp_canonical_field_attributions_version_class FOREIGN KEY (myopp_source_version_id, data_class) REFERENCES dbo.myopp_source_versions (myopp_source_version_id, data_class),
            CONSTRAINT FK_myopp_canonical_field_attributions_terminal_policy_class FOREIGN KEY (myopp_terminal_policy_id, data_class) REFERENCES dbo.myopp_source_policies (myopp_source_policy_id, data_class),
            CONSTRAINT CK_myopp_canonical_field_attributions_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_canonical_field_attributions_field CHECK (field_name IS NULL OR LEN(field_name) > 0),
            CONSTRAINT CK_myopp_canonical_field_attributions_retained_fields_json CHECK (ISJSON(retained_source_fields_json) = 1 AND LEFT(LTRIM(retained_source_fields_json), 1) = N'['),
            CONSTRAINT CK_myopp_canonical_field_attributions_tombstone CHECK
            (
                (content_tombstoned_at_utc IS NULL
                 AND myopp_terminal_policy_id IS NULL AND terminal_policy_version IS NULL
                 AND terminal_disposition IS NULL AND tombstone_reason IS NULL AND terminal_actor IS NULL
                 AND field_name IS NOT NULL AND retained_source_fields_json = N'[]')
                OR
                (content_tombstoned_at_utc IS NOT NULL
                 AND myopp_terminal_policy_id IS NOT NULL AND terminal_policy_version > 0
                 AND terminal_disposition IN (N'removal', N'termination')
                 AND tombstone_reason IS NOT NULL AND terminal_actor IS NOT NULL)
            )
        );

        CREATE UNIQUE INDEX UX_myopp_canonical_field_attributions_active_opportunity_field
            ON dbo.myopp_canonical_field_attributions (myopp_canonical_opportunity_id, data_class, field_name)
            WHERE field_name IS NOT NULL;

        CREATE TABLE dbo.myopp_canonical_events
        (
            myopp_canonical_event_id bigint IDENTITY(1,1) NOT NULL,
            event_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_canonical_events_key DEFAULT NEWID(),
            myopp_canonical_opportunity_id bigint NOT NULL,
            data_class nvarchar(20) NOT NULL,
            event_kind nvarchar(80) NOT NULL,
            occurred_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_canonical_events_occurred DEFAULT SYSUTCDATETIME(),
            detail_json nvarchar(max) NOT NULL,
            CONSTRAINT PK_myopp_canonical_events PRIMARY KEY (myopp_canonical_event_id),
            CONSTRAINT UQ_myopp_canonical_events_key UNIQUE (event_key),
            CONSTRAINT UQ_myopp_canonical_events_id_class UNIQUE (myopp_canonical_event_id, data_class),
            CONSTRAINT FK_myopp_canonical_events_opportunity_class FOREIGN KEY (myopp_canonical_opportunity_id, data_class) REFERENCES dbo.myopp_canonical_opportunities (myopp_canonical_opportunity_id, data_class),
            CONSTRAINT CK_myopp_canonical_events_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_canonical_events_detail_json CHECK (ISJSON(detail_json) = 1)
        );

        CREATE TABLE dbo.myopp_content_tombstones
        (
            myopp_content_tombstone_id bigint IDENTITY(1,1) NOT NULL,
            tombstone_key uniqueidentifier NOT NULL CONSTRAINT DF_myopp_content_tombstones_key DEFAULT NEWID(),
            myopp_source_receipt_id bigint NOT NULL,
            myopp_source_version_id bigint NOT NULL,
            data_class nvarchar(20) NOT NULL,
            myopp_source_policy_id bigint NOT NULL,
            policy_version int NOT NULL,
            disposition nvarchar(20) NOT NULL,
            removal_reason nvarchar(80) NOT NULL,
            actor_ref nvarchar(160) NOT NULL,
            retained_source_fields_json nvarchar(max) NOT NULL CONSTRAINT DF_myopp_content_tombstones_retained_fields DEFAULT N'[]',
            actioned_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_content_tombstones_actioned DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_myopp_content_tombstones PRIMARY KEY (myopp_content_tombstone_id),
            CONSTRAINT UQ_myopp_content_tombstones_key UNIQUE (tombstone_key),
            CONSTRAINT UQ_myopp_content_tombstones_pair_class UNIQUE (myopp_source_receipt_id, myopp_source_version_id, data_class),
            CONSTRAINT UQ_myopp_content_tombstones_id_class UNIQUE (myopp_content_tombstone_id, data_class),
            CONSTRAINT FK_myopp_content_tombstones_receipt_class FOREIGN KEY (myopp_source_receipt_id, data_class) REFERENCES dbo.myopp_source_receipts (myopp_source_receipt_id, data_class),
            CONSTRAINT FK_myopp_content_tombstones_version_class FOREIGN KEY (myopp_source_version_id, data_class) REFERENCES dbo.myopp_source_versions (myopp_source_version_id, data_class),
            CONSTRAINT FK_myopp_content_tombstones_pair_link_class FOREIGN KEY (myopp_source_version_id, myopp_source_receipt_id, data_class) REFERENCES dbo.myopp_source_version_receipt_links (myopp_source_version_id, myopp_source_receipt_id, data_class),
            CONSTRAINT FK_myopp_content_tombstones_policy_class FOREIGN KEY (myopp_source_policy_id, data_class) REFERENCES dbo.myopp_source_policies (myopp_source_policy_id, data_class),
            CONSTRAINT CK_myopp_content_tombstones_data_class CHECK (data_class IN (N'fixture', N'production')),
            CONSTRAINT CK_myopp_content_tombstones_target CHECK (myopp_source_receipt_id IS NOT NULL AND myopp_source_version_id IS NOT NULL),
            CONSTRAINT CK_myopp_content_tombstones_policy_version CHECK (policy_version > 0),
            CONSTRAINT CK_myopp_content_tombstones_disposition CHECK (disposition IN (N'removal', N'termination')),
            CONSTRAINT CK_myopp_content_tombstones_actor CHECK (LEN(actor_ref) > 0),
            CONSTRAINT CK_myopp_content_tombstones_retained_fields_json CHECK (ISJSON(retained_source_fields_json) = 1 AND LEFT(LTRIM(retained_source_fields_json), 1) = N'[')
        );

        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_source_policies_revision_guard
            ON dbo.myopp_source_policies
            AFTER INSERT, UPDATE, DELETE
            AS
            BEGIN
                SET NOCOUNT ON;

                /* Source-policy rows are append-only. A restrictive revision is
                   a new row, never an UPDATE of its prior decision. */
                IF EXISTS (SELECT 1 FROM deleted)
                    THROW 55500, ''Source policy rows are append-only.'', 1;

                /* Persist both the exact closed action array and retained-field
                   decision. The dimensions and action vocabulary are the full
                   SQL-side policy rights surface this trigger can narrow. */
                IF EXISTS
                (
                    SELECT 1
                    FROM inserted i
                    WHERE LEN(LTRIM(RTRIM(i.evidence_ref))) = 0
                       OR LEN(LTRIM(RTRIM(i.decision_ref))) = 0
                       OR ISJSON(i.allowed_actions_json) <> 1
                       OR LEFT(LTRIM(i.allowed_actions_json), 1) <> N''[''
                       OR i.allowed_actions_json LIKE N''% %''
                       OR i.allowed_actions_json LIKE N''%'' + NCHAR(9) + N''%''
                       OR i.allowed_actions_json LIKE N''%'' + NCHAR(10) + N''%''
                       OR i.allowed_actions_json LIKE N''%'' + NCHAR(13) + N''%''
                       OR i.allowed_actions_json LIKE N''%'' + NCHAR(92) + N''%''
                       OR ISJSON(i.retained_source_fields_json) <> 1
                       OR LEFT(LTRIM(i.retained_source_fields_json), 1) <> N''[''
                       OR i.retained_source_fields_json LIKE N''% %''
                       OR i.retained_source_fields_json LIKE N''%'' + NCHAR(9) + N''%''
                       OR i.retained_source_fields_json LIKE N''%'' + NCHAR(10) + N''%''
                       OR i.retained_source_fields_json LIKE N''%'' + NCHAR(13) + N''%''
                       OR i.retained_source_fields_json LIKE N''%'' + NCHAR(92) + N''%''
                       OR (i.survivable_minimal_facts_allowed = 0 AND i.retained_source_fields_json <> N''[]'')
                       OR EXISTS
                          (
                              SELECT 1
                              FROM OPENJSON(i.allowed_actions_json) allowed_action
                              WHERE allowed_action.[type] <> 1
                                 OR allowed_action.[value] COLLATE Latin1_General_100_BIN2 NOT IN
                                 (
                                     N''acquire'', N''ai'', N''cache'', N''display'', N''export'',
                                     N''persist'', N''register'', N''remove'', N''retain'', N''terminate''
                                 )
                          )
                       OR EXISTS
                          (
                               SELECT 1
                               FROM OPENJSON(i.allowed_actions_json) allowed_action
                               GROUP BY allowed_action.[value] COLLATE Latin1_General_100_BIN2
                              HAVING COUNT(*) > 1
                          )
                       OR EXISTS
                          (
                              SELECT 1
                              FROM OPENJSON(i.allowed_actions_json) earlier_action
                              JOIN OPENJSON(i.allowed_actions_json) later_action
                                ON TRY_CONVERT(int, earlier_action.[key]) < TRY_CONVERT(int, later_action.[key])
                              WHERE CASE earlier_action.[value] COLLATE Latin1_General_100_BIN2
                                      WHEN N''acquire'' THEN 1 WHEN N''ai'' THEN 2 WHEN N''cache'' THEN 3
                                      WHEN N''display'' THEN 4 WHEN N''export'' THEN 5 WHEN N''persist'' THEN 6
                                      WHEN N''register'' THEN 7 WHEN N''remove'' THEN 8 WHEN N''retain'' THEN 9
                                      WHEN N''terminate'' THEN 10 END
                                    > CASE later_action.[value] COLLATE Latin1_General_100_BIN2
                                      WHEN N''acquire'' THEN 1 WHEN N''ai'' THEN 2 WHEN N''cache'' THEN 3
                                      WHEN N''display'' THEN 4 WHEN N''export'' THEN 5 WHEN N''persist'' THEN 6
                                      WHEN N''register'' THEN 7 WHEN N''remove'' THEN 8 WHEN N''retain'' THEN 9
                                      WHEN N''terminate'' THEN 10 END
                          )
                       OR EXISTS
                          (
                              SELECT 1
                              FROM OPENJSON(i.retained_source_fields_json) retained
                               WHERE retained.[type] <> 1
                                  OR retained.[value] COLLATE Latin1_General_100_BIN2 NOT IN
                                 (
                                     N''receipt.source_id'', N''receipt.external_reference'', N''receipt.received_at'',
                                     N''receipt.content_type'', N''receipt.byte_count'', N''receipt.payload'',
                                     N''listing.source_id'', N''listing.external_reference'', N''listing.expected_application_hosts'',
                                     N''source_version.content_sha256'', N''source_version.observed_at'',
                                     N''source_version.employer'', N''source_version.title'', N''source_version.locations'',
                                     N''source_version.arrangement'', N''source_version.application_url'',
                                     N''source_version.description'', N''source_version.requirement_clauses'',
                                     N''source_version.fields'', N''requirement_version.clause_fingerprint'',
                                     N''requirement_item.ordinal'', N''requirement_item.normalized_clause'',
                                     N''field_attribution.field_name''
                                 )
                          )
                       OR EXISTS
                          (
                               SELECT 1
                               FROM OPENJSON(i.retained_source_fields_json) retained
                               GROUP BY retained.[value] COLLATE Latin1_General_100_BIN2
                               HAVING COUNT(*) > 1
                           )
                       OR EXISTS
                           (
                               SELECT 1
                               FROM OPENJSON(i.retained_source_fields_json) earlier_field
                               JOIN OPENJSON(i.retained_source_fields_json) later_field
                                 ON TRY_CONVERT(int, earlier_field.[key]) < TRY_CONVERT(int, later_field.[key])
                               WHERE earlier_field.[value] COLLATE Latin1_General_100_BIN2
                                     > later_field.[value] COLLATE Latin1_General_100_BIN2
                           )
                )
                    THROW 55501, ''Source policy evidence, decision, or retained-field allowlist is invalid.'', 1;

                /* Registration and revision are one command at a time. Refuse
                   any multirow batch instead of accepting an ambiguous in-batch
                   predecessor chain. */
                IF (SELECT COUNT(*) FROM inserted) <> 1
                    THROW 55502, ''Ambiguous source policy revision batch refused.'', 1;

                /* The first row in a class-safe lineage may carry a provider''s
                   already-positive version number, but it must be a complete
                   affirmative registration decision. */
                IF EXISTS
                (
                    SELECT 1
                    FROM inserted i
                    WHERE NOT EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_source_policies lineage
                        WHERE lineage.data_class = i.data_class
                          AND (lineage.policy_key = i.policy_key OR lineage.source_id = i.source_id)
                          AND lineage.myopp_source_policy_id NOT IN
                              (SELECT batch.myopp_source_policy_id FROM inserted batch)
                    )
                    AND
                    (
                        i.display_allowed <> 1 OR i.excerpt_allowed <> 1
                        OR i.full_description_allowed <> 1 OR i.storage_allowed <> 1
                        OR i.ai_ml_allowed <> 1 OR i.caching_allowed <> 1
                        OR i.retention_allowed <> 1 OR i.attribution_allowed <> 1
                        OR i.removal_allowed <> 1 OR i.termination_allowed <> 1
                        OR i.exit_allowed <> 1 OR i.survivable_minimal_facts_allowed <> 1
                        OR EXISTS
                           (
                               SELECT required_action.[value]
                               FROM
                               (
                                   VALUES
                                   (N''acquire''), (N''ai''), (N''cache''), (N''display''), (N''export''),
                                   (N''persist''), (N''register''), (N''remove''), (N''retain''), (N''terminate'')
                               ) required_action([value])
                               WHERE NOT EXISTS
                               (
                                   SELECT 1
                                   FROM OPENJSON(i.allowed_actions_json) initial_action
                                   WHERE initial_action.[type] = 1
                                     AND initial_action.[value] COLLATE Latin1_General_100_BIN2 = required_action.[value] COLLATE Latin1_General_100_BIN2
                               )
                           )
                    )
                )
                    THROW 55503, ''Initial source policy must satisfy the fail-closed registration contract.'', 1;

                /* A source id and policy key identify exactly one class-specific
                   lineage. A later row must preserve that identity and use the
                   immediately preceding persisted version, never a batch peer. */
                IF EXISTS
                (
                    SELECT 1
                    FROM inserted i
                    JOIN dbo.myopp_source_policies lineage
                      ON lineage.data_class = i.data_class
                     AND lineage.myopp_source_policy_id NOT IN
                         (SELECT batch.myopp_source_policy_id FROM inserted batch)
                    WHERE (lineage.policy_key = i.policy_key AND
                           (lineage.source_id <> i.source_id
                            OR lineage.source_class <> i.source_class
                            OR lineage.source_priority <> i.source_priority))
                       OR (lineage.source_id = i.source_id AND lineage.policy_key <> i.policy_key)
                )
                    THROW 55504, ''Source policy revision changed class-safe identity.'', 1;

                IF EXISTS
                (
                    SELECT 1
                    FROM inserted i
                    LEFT JOIN dbo.myopp_source_policies prior
                      ON prior.policy_key = i.policy_key
                     AND prior.data_class = i.data_class
                     AND prior.policy_version = i.policy_version - 1
                     AND prior.myopp_source_policy_id NOT IN
                         (SELECT batch.myopp_source_policy_id FROM inserted batch)
                    WHERE EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_source_policies lineage
                        WHERE lineage.policy_key = i.policy_key
                          AND lineage.data_class = i.data_class
                          AND lineage.myopp_source_policy_id NOT IN
                              (SELECT batch.myopp_source_policy_id FROM inserted batch)
                    )
                      AND
                      (
                          prior.myopp_source_policy_id IS NULL
                          OR i.source_id <> prior.source_id
                          OR i.source_class <> prior.source_class
                          OR i.source_priority <> prior.source_priority
                          OR (i.display_allowed = 1 AND prior.display_allowed = 0)
                          OR (i.excerpt_allowed = 1 AND prior.excerpt_allowed = 0)
                          OR (i.full_description_allowed = 1 AND prior.full_description_allowed = 0)
                          OR (i.storage_allowed = 1 AND prior.storage_allowed = 0)
                          OR (i.ai_ml_allowed = 1 AND prior.ai_ml_allowed = 0)
                          OR (i.caching_allowed = 1 AND prior.caching_allowed = 0)
                          OR (i.retention_allowed = 1 AND prior.retention_allowed = 0)
                          OR (i.attribution_allowed = 1 AND prior.attribution_allowed = 0)
                          OR (i.removal_allowed = 1 AND prior.removal_allowed = 0)
                          OR (i.termination_allowed = 1 AND prior.termination_allowed = 0)
                          OR (i.exit_allowed = 1 AND prior.exit_allowed = 0)
                          OR (i.survivable_minimal_facts_allowed = 1 AND prior.survivable_minimal_facts_allowed = 0)
                          OR EXISTS
                             (
                                 SELECT 1
                                 FROM OPENJSON(i.allowed_actions_json) current_actions
                                 WHERE NOT EXISTS
                                 (
                                     SELECT 1
                                     FROM OPENJSON(prior.allowed_actions_json) prior_actions
                                     WHERE prior_actions.[type] = 1
                                       AND prior_actions.[value] COLLATE Latin1_General_100_BIN2 = current_actions.[value] COLLATE Latin1_General_100_BIN2
                                 )
                             )
                          OR EXISTS
                             (
                                 SELECT 1
                                 FROM OPENJSON(i.retained_source_fields_json) current_fields
                                 WHERE NOT EXISTS
                                 (
                                     SELECT 1
                                     FROM OPENJSON(prior.retained_source_fields_json) prior_fields
                                     WHERE prior_fields.[type] = 1
                                       AND prior_fields.[value] = current_fields.[value]
                                 )
                             )
                      )
                )
                    THROW 55505, ''Source policy revision must be the immediate restrictive successor.'', 1;
            END');
        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_source_receipts_terminal_guard
            ON dbo.myopp_source_receipts AFTER UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                IF ISNULL(TRY_CONVERT(nvarchar(32), SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')), N'''') <> N''active''
                    THROW 55530, ''Source receipt mutation is reserved for the controlled terminal takedown.'', 1;
                IF EXISTS
                (
                    SELECT 1
                    FROM deleted d
                    LEFT JOIN inserted i ON i.myopp_source_receipt_id = d.myopp_source_receipt_id
                    JOIN dbo.myopp_source_policies original_policy
                      ON original_policy.myopp_source_policy_id = d.myopp_source_policy_id
                     AND original_policy.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_policies terminal_policy
                      ON terminal_policy.myopp_source_policy_id = i.myopp_terminal_policy_id
                     AND terminal_policy.data_class = i.data_class
                    WHERE i.myopp_source_receipt_id IS NULL
                       OR d.content_tombstoned_at_utc IS NOT NULL
                       OR i.content_tombstoned_at_utc IS NULL
                       OR i.receipt_key <> d.receipt_key
                       OR i.myopp_source_policy_id <> d.myopp_source_policy_id
                       OR i.data_class <> d.data_class
                       OR i.created_at_utc <> d.created_at_utc
                       OR i.myopp_terminal_policy_id IS NULL OR i.terminal_policy_version IS NULL
                       OR i.terminal_disposition NOT IN (N''removal'', N''termination'')
                       OR LEN(LTRIM(RTRIM(i.tombstone_reason))) = 0 OR LEN(LTRIM(RTRIM(i.terminal_actor))) = 0
                       OR terminal_policy.myopp_source_policy_id IS NULL
                       OR terminal_policy.policy_version <> i.terminal_policy_version
                       OR terminal_policy.policy_key <> original_policy.policy_key
                       OR terminal_policy.source_id <> original_policy.source_id
                       OR terminal_policy.source_class <> original_policy.source_class
                       OR terminal_policy.retained_source_fields_json <> i.retained_source_fields_json
                       OR (i.terminal_disposition = N''removal'' AND
                           (terminal_policy.removal_allowed <> 1 OR NOT EXISTS
                            (SELECT 1 FROM OPENJSON(terminal_policy.allowed_actions_json) action_record
                             WHERE action_record.[type] = 1 AND action_record.[value] = N''remove'')))
                       OR (i.terminal_disposition = N''termination'' AND
                           (terminal_policy.termination_allowed <> 1 OR NOT EXISTS
                            (SELECT 1 FROM OPENJSON(terminal_policy.allowed_actions_json) action_record
                             WHERE action_record.[type] = 1 AND action_record.[value] = N''terminate'')))
                       OR (i.source_id IS NOT NULL AND
                           (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''receipt.source_id'') OR i.source_id <> d.source_id))
                       OR (i.external_reference IS NOT NULL AND
                           (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''receipt.external_reference'') OR i.external_reference <> d.external_reference))
                       OR (i.received_at_utc IS NOT NULL AND
                           (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''receipt.received_at'') OR i.received_at_utc <> d.received_at_utc))
                       OR (i.content_type IS NOT NULL AND
                           (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''receipt.content_type'') OR i.content_type <> d.content_type))
                       OR (i.byte_count IS NOT NULL AND
                           (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''receipt.byte_count'') OR i.byte_count <> d.byte_count))
                       OR ((i.payload_sha256 IS NOT NULL OR i.payload_body IS NOT NULL) AND
                           (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''receipt.payload'')
                            OR i.payload_sha256 <> d.payload_sha256 OR i.payload_body <> d.payload_body))
                )
                    THROW 55531, ''Source receipts permit only one exact terminal purge or allowlisted retention transition.'', 1;
            END');
        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_source_versions_terminal_guard
            ON dbo.myopp_source_versions AFTER UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                IF ISNULL(TRY_CONVERT(nvarchar(32), SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')), N'''') <> N''active''
                    THROW 55532, ''Source version mutation is reserved for the controlled terminal takedown.'', 1;
                IF EXISTS
                (
                    SELECT 1
                    FROM deleted d
                    LEFT JOIN inserted i ON i.myopp_source_version_id = d.myopp_source_version_id
                    JOIN dbo.myopp_source_receipts receipt_record
                      ON receipt_record.myopp_source_receipt_id = d.myopp_source_receipt_id
                     AND receipt_record.data_class = d.data_class
                    JOIN dbo.myopp_source_policies original_policy
                      ON original_policy.myopp_source_policy_id = receipt_record.myopp_source_policy_id
                     AND original_policy.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_policies terminal_policy
                      ON terminal_policy.myopp_source_policy_id = i.myopp_terminal_policy_id
                     AND terminal_policy.data_class = i.data_class
                    WHERE i.myopp_source_version_id IS NULL
                       OR d.content_tombstoned_at_utc IS NOT NULL
                       OR i.content_tombstoned_at_utc IS NULL
                       OR i.source_version_key <> d.source_version_key
                       OR i.myopp_source_listing_id <> d.myopp_source_listing_id
                       OR i.myopp_source_receipt_id <> d.myopp_source_receipt_id
                       OR i.data_class <> d.data_class
                       OR i.created_at_utc <> d.created_at_utc
                       OR i.myopp_terminal_policy_id IS NULL OR i.terminal_policy_version IS NULL
                       OR i.terminal_disposition NOT IN (N''removal'', N''termination'')
                       OR LEN(LTRIM(RTRIM(i.tombstone_reason))) = 0 OR LEN(LTRIM(RTRIM(i.terminal_actor))) = 0
                       OR terminal_policy.myopp_source_policy_id IS NULL
                       OR terminal_policy.policy_version <> i.terminal_policy_version
                       OR terminal_policy.policy_key <> original_policy.policy_key
                       OR terminal_policy.source_id <> original_policy.source_id
                       OR terminal_policy.source_class <> original_policy.source_class
                       OR terminal_policy.retained_source_fields_json <> i.retained_source_fields_json
                       OR (i.terminal_disposition = N''removal'' AND terminal_policy.removal_allowed <> 1)
                       OR (i.terminal_disposition = N''termination'' AND terminal_policy.termination_allowed <> 1)
                       OR (i.content_sha256 IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.content_sha256'') OR i.content_sha256 <> d.content_sha256))
                       OR (i.observed_at_utc IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.observed_at'') OR i.observed_at_utc <> d.observed_at_utc))
                       OR (i.employer_name IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.employer'') OR i.employer_name <> d.employer_name))
                       OR (i.role_title IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.title'') OR i.role_title <> d.role_title))
                       OR (i.locations_json IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.locations'') OR i.locations_json <> d.locations_json))
                       OR (i.arrangement IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.arrangement'') OR i.arrangement <> d.arrangement))
                       OR (i.application_url IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.application_url'') OR i.application_url <> d.application_url))
                       OR (i.source_body IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.description'') OR i.source_body <> d.source_body))
                       OR (i.normalized_fields_json IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.fields'') OR i.normalized_fields_json <> d.normalized_fields_json))
                       OR (i.normalized_requirements_json IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''source_version.requirement_clauses'') OR i.normalized_requirements_json <> d.normalized_requirements_json))
                )
                    THROW 55533, ''Source versions permit only one exact terminal purge or allowlisted retention transition.'', 1;
            END');
        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_source_listings_terminal_guard
            ON dbo.myopp_source_listings AFTER UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                IF ISNULL(TRY_CONVERT(nvarchar(32), SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')), N'''') <> N''active''
                    THROW 55534, ''Source listing mutation is reserved for the controlled terminal takedown.'', 1;
                IF EXISTS
                (
                    SELECT 1
                    FROM deleted d
                    LEFT JOIN inserted i ON i.myopp_source_listing_id = d.myopp_source_listing_id
                    JOIN dbo.myopp_source_policies original_policy
                      ON original_policy.myopp_source_policy_id = d.myopp_source_policy_id
                     AND original_policy.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_policies terminal_policy
                      ON terminal_policy.myopp_source_policy_id = i.myopp_terminal_policy_id
                     AND terminal_policy.data_class = i.data_class
                    WHERE i.myopp_source_listing_id IS NULL
                       OR d.content_tombstoned_at_utc IS NOT NULL
                       OR i.content_tombstoned_at_utc IS NULL
                       OR i.listing_key <> d.listing_key
                       OR i.myopp_source_policy_id <> d.myopp_source_policy_id
                       OR i.myopp_canonical_opportunity_id <> d.myopp_canonical_opportunity_id
                       OR i.data_class <> d.data_class
                       OR i.current_source_version_id <> d.current_source_version_id
                       OR i.created_at_utc <> d.created_at_utc OR i.updated_at_utc <> d.updated_at_utc
                       OR i.myopp_terminal_policy_id IS NULL OR i.terminal_policy_version IS NULL
                       OR i.terminal_disposition NOT IN (N''removal'', N''termination'')
                       OR LEN(LTRIM(RTRIM(i.tombstone_reason))) = 0 OR LEN(LTRIM(RTRIM(i.terminal_actor))) = 0
                       OR terminal_policy.myopp_source_policy_id IS NULL
                       OR terminal_policy.policy_version <> i.terminal_policy_version
                       OR terminal_policy.policy_key <> original_policy.policy_key
                       OR terminal_policy.source_id <> original_policy.source_id
                       OR terminal_policy.source_class <> original_policy.source_class
                       OR terminal_policy.retained_source_fields_json <> i.retained_source_fields_json
                       OR (i.terminal_disposition = N''removal'' AND (terminal_policy.removal_allowed <> 1 OR i.listing_state <> N''closed''))
                       OR (i.terminal_disposition = N''termination'' AND (terminal_policy.termination_allowed <> 1 OR i.listing_state <> N''invalid''))
                        OR i.application_url IS NOT NULL
                        OR i.application_link_state <> N''unknown'' OR i.application_link_invalid_reason IS NOT NULL OR i.link_review_pending <> 0
                        OR i.link_last_attempted_at_utc IS NOT NULL OR i.link_last_validated_at_utc IS NOT NULL
                        OR i.last_attempted_at_utc IS NOT NULL OR i.last_successfully_verified_at_utc IS NOT NULL
                       OR (i.source_id IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''listing.source_id'') OR i.source_id <> d.source_id))
                       OR (i.external_reference IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''listing.external_reference'') OR i.external_reference <> d.external_reference))
                       OR (i.expected_application_hosts_json IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''listing.expected_application_hosts'') OR i.expected_application_hosts_json <> d.expected_application_hosts_json))
                )
                    THROW 55535, ''Source listings permit only one exact terminal purge or allowlisted retention transition.'', 1;
            END');
        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_requirement_versions_terminal_guard
            ON dbo.myopp_requirement_versions AFTER UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                IF ISNULL(TRY_CONVERT(nvarchar(32), SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')), N'''') <> N''active''
                    THROW 55536, ''Requirement version mutation is reserved for the controlled terminal takedown.'', 1;
                IF EXISTS
                (
                    SELECT 1
                    FROM deleted d
                    LEFT JOIN inserted i ON i.myopp_requirement_version_id = d.myopp_requirement_version_id
                    LEFT JOIN dbo.myopp_source_versions source_version
                      ON source_version.myopp_source_version_id = d.myopp_source_version_id
                     AND source_version.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_receipts receipt_record
                      ON receipt_record.myopp_source_receipt_id = source_version.myopp_source_receipt_id
                     AND receipt_record.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_policies original_policy
                      ON original_policy.myopp_source_policy_id = receipt_record.myopp_source_policy_id
                     AND original_policy.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_policies terminal_policy
                      ON terminal_policy.myopp_source_policy_id = i.myopp_terminal_policy_id
                     AND terminal_policy.data_class = i.data_class
                    WHERE i.myopp_requirement_version_id IS NULL
                       OR d.content_tombstoned_at_utc IS NOT NULL OR i.content_tombstoned_at_utc IS NULL
                       OR i.requirement_version_key <> d.requirement_version_key
                       OR i.myopp_canonical_opportunity_id <> d.myopp_canonical_opportunity_id
                       OR i.myopp_source_version_id <> d.myopp_source_version_id OR i.data_class <> d.data_class
                       OR i.derived_at_utc <> d.derived_at_utc
                       OR i.myopp_terminal_policy_id IS NULL OR i.terminal_policy_version IS NULL
                       OR i.terminal_disposition NOT IN (N''removal'', N''termination'')
                       OR LEN(LTRIM(RTRIM(i.tombstone_reason))) = 0 OR LEN(LTRIM(RTRIM(i.terminal_actor))) = 0
                       OR terminal_policy.myopp_source_policy_id IS NULL
                       OR terminal_policy.policy_version <> i.terminal_policy_version
                       OR terminal_policy.policy_key <> original_policy.policy_key
                       OR terminal_policy.source_id <> original_policy.source_id
                       OR terminal_policy.source_class <> original_policy.source_class
                       OR terminal_policy.retained_source_fields_json <> i.retained_source_fields_json
                       OR (i.terminal_disposition = N''removal'' AND terminal_policy.removal_allowed <> 1)
                       OR (i.terminal_disposition = N''termination'' AND terminal_policy.termination_allowed <> 1)
                       OR (i.clause_fingerprint IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''requirement_version.clause_fingerprint'') OR i.clause_fingerprint <> d.clause_fingerprint))
                )
                    THROW 55537, ''Requirement versions permit only one exact terminal purge or allowlisted retention transition.'', 1;
            END');
        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_requirement_items_terminal_guard
            ON dbo.myopp_requirement_items AFTER UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                IF ISNULL(TRY_CONVERT(nvarchar(32), SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')), N'''') <> N''active''
                    THROW 55538, ''Requirement item mutation is reserved for the controlled terminal takedown.'', 1;
                IF EXISTS
                (
                    SELECT 1
                    FROM deleted d
                    LEFT JOIN inserted i ON i.myopp_requirement_item_id = d.myopp_requirement_item_id
                    LEFT JOIN dbo.myopp_requirement_versions requirement_version
                      ON requirement_version.myopp_requirement_version_id = d.myopp_requirement_version_id
                     AND requirement_version.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_versions source_version
                      ON source_version.myopp_source_version_id = requirement_version.myopp_source_version_id
                     AND source_version.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_receipts receipt_record
                      ON receipt_record.myopp_source_receipt_id = source_version.myopp_source_receipt_id
                     AND receipt_record.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_policies original_policy
                      ON original_policy.myopp_source_policy_id = receipt_record.myopp_source_policy_id
                     AND original_policy.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_policies terminal_policy
                      ON terminal_policy.myopp_source_policy_id = i.myopp_terminal_policy_id
                     AND terminal_policy.data_class = i.data_class
                    WHERE i.myopp_requirement_item_id IS NULL
                       OR d.content_tombstoned_at_utc IS NOT NULL OR i.content_tombstoned_at_utc IS NULL
                       OR i.requirement_item_key <> d.requirement_item_key
                       OR i.myopp_requirement_version_id <> d.myopp_requirement_version_id OR i.data_class <> d.data_class
                       OR i.myopp_terminal_policy_id IS NULL OR i.terminal_policy_version IS NULL
                       OR i.terminal_disposition NOT IN (N''removal'', N''termination'')
                       OR LEN(LTRIM(RTRIM(i.tombstone_reason))) = 0 OR LEN(LTRIM(RTRIM(i.terminal_actor))) = 0
                       OR terminal_policy.myopp_source_policy_id IS NULL
                       OR terminal_policy.policy_version <> i.terminal_policy_version
                       OR terminal_policy.policy_key <> original_policy.policy_key
                       OR terminal_policy.source_id <> original_policy.source_id
                       OR terminal_policy.source_class <> original_policy.source_class
                       OR terminal_policy.retained_source_fields_json <> i.retained_source_fields_json
                       OR (i.terminal_disposition = N''removal'' AND terminal_policy.removal_allowed <> 1)
                       OR (i.terminal_disposition = N''termination'' AND terminal_policy.termination_allowed <> 1)
                       OR i.requirement_class IS NOT NULL OR i.source_span_start IS NOT NULL OR i.source_span_length IS NOT NULL OR i.classification_basis IS NOT NULL
                       OR (i.ordinal IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''requirement_item.ordinal'') OR i.ordinal <> d.ordinal))
                       OR (i.normalized_clause IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''requirement_item.normalized_clause'') OR i.normalized_clause <> d.normalized_clause))
                )
                    THROW 55539, ''Requirement items permit only one exact terminal purge or allowlisted retention transition.'', 1;
            END');

        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_canonical_field_attributions_terminal_guard
            ON dbo.myopp_canonical_field_attributions AFTER UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                IF ISNULL(TRY_CONVERT(nvarchar(32), SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')), N'''') <> N''active''
                    THROW 55540, ''Field attribution mutation is reserved for the controlled terminal takedown.'', 1;
                IF EXISTS
                (
                    SELECT 1
                    FROM deleted d
                    LEFT JOIN inserted i ON i.myopp_canonical_field_attribution_id = d.myopp_canonical_field_attribution_id
                    LEFT JOIN dbo.myopp_source_versions source_version
                      ON source_version.myopp_source_version_id = d.myopp_source_version_id
                     AND source_version.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_receipts receipt_record
                      ON receipt_record.myopp_source_receipt_id = source_version.myopp_source_receipt_id
                     AND receipt_record.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_policies original_policy
                      ON original_policy.myopp_source_policy_id = receipt_record.myopp_source_policy_id
                     AND original_policy.data_class = d.data_class
                    LEFT JOIN dbo.myopp_source_policies terminal_policy
                      ON terminal_policy.myopp_source_policy_id = i.myopp_terminal_policy_id
                     AND terminal_policy.data_class = i.data_class
                    WHERE i.myopp_canonical_field_attribution_id IS NULL
                       OR d.content_tombstoned_at_utc IS NOT NULL OR i.content_tombstoned_at_utc IS NULL
                       OR i.myopp_canonical_opportunity_id <> d.myopp_canonical_opportunity_id
                       OR i.myopp_source_listing_id <> d.myopp_source_listing_id
                       OR i.myopp_source_version_id <> d.myopp_source_version_id OR i.data_class <> d.data_class
                       OR i.recorded_at_utc <> d.recorded_at_utc
                       OR i.myopp_terminal_policy_id IS NULL OR i.terminal_policy_version IS NULL
                       OR i.terminal_disposition NOT IN (N''removal'', N''termination'')
                       OR LEN(LTRIM(RTRIM(i.tombstone_reason))) = 0 OR LEN(LTRIM(RTRIM(i.terminal_actor))) = 0
                       OR terminal_policy.myopp_source_policy_id IS NULL
                       OR terminal_policy.policy_version <> i.terminal_policy_version
                       OR terminal_policy.policy_key <> original_policy.policy_key
                       OR terminal_policy.source_id <> original_policy.source_id
                       OR terminal_policy.source_class <> original_policy.source_class
                       OR terminal_policy.retained_source_fields_json <> i.retained_source_fields_json
                       OR (i.terminal_disposition = N''removal'' AND terminal_policy.removal_allowed <> 1)
                       OR (i.terminal_disposition = N''termination'' AND terminal_policy.termination_allowed <> 1)
                       OR (i.field_name IS NOT NULL AND (NOT EXISTS (SELECT 1 FROM OPENJSON(i.retained_source_fields_json) retained WHERE retained.[value] = N''field_attribution.field_name'') OR i.field_name <> d.field_name))
                )
                    THROW 55541, ''Field attributions permit only one exact terminal purge or allowlisted retention transition.'', 1;
            END');
        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_source_version_receipt_links_immutable
            ON dbo.myopp_source_version_receipt_links AFTER UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                THROW 55542, ''Source-version receipt provenance links are immutable.'', 1;
            END');
        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_content_tombstones_immutable
            ON dbo.myopp_content_tombstones AFTER INSERT, UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                IF EXISTS (SELECT 1 FROM deleted)
                    THROW 55543, ''Content tombstones are append-only.'', 1;
                IF ISNULL(TRY_CONVERT(nvarchar(32), SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')), N'''') <> N''active''
                    THROW 55544, ''Content tombstones are created only by the controlled terminal takedown.'', 1;
                IF EXISTS
                (
                    SELECT 1
                    FROM inserted i
                    LEFT JOIN dbo.myopp_source_version_receipt_links link_record
                      ON link_record.myopp_source_version_id = i.myopp_source_version_id
                     AND link_record.myopp_source_receipt_id = i.myopp_source_receipt_id
                     AND link_record.data_class = i.data_class
                    LEFT JOIN dbo.myopp_source_receipts receipt_record
                      ON receipt_record.myopp_source_receipt_id = i.myopp_source_receipt_id
                     AND receipt_record.data_class = i.data_class
                    LEFT JOIN dbo.myopp_source_versions source_version
                      ON source_version.myopp_source_version_id = i.myopp_source_version_id
                     AND source_version.data_class = i.data_class
                    LEFT JOIN dbo.myopp_source_policies terminal_policy
                      ON terminal_policy.myopp_source_policy_id = i.myopp_source_policy_id
                     AND terminal_policy.data_class = i.data_class
                    WHERE link_record.myopp_source_version_receipt_link_id IS NULL
                       OR receipt_record.content_tombstoned_at_utc <> i.actioned_at_utc
                       OR source_version.content_tombstoned_at_utc <> i.actioned_at_utc
                       OR receipt_record.myopp_terminal_policy_id <> i.myopp_source_policy_id
                       OR source_version.myopp_terminal_policy_id <> i.myopp_source_policy_id
                       OR receipt_record.terminal_policy_version <> i.policy_version
                       OR source_version.terminal_policy_version <> i.policy_version
                       OR receipt_record.terminal_disposition <> i.disposition
                       OR source_version.terminal_disposition <> i.disposition
                       OR receipt_record.tombstone_reason <> i.removal_reason
                       OR source_version.tombstone_reason <> i.removal_reason
                       OR receipt_record.terminal_actor <> i.actor_ref
                       OR source_version.terminal_actor <> i.actor_ref
                       OR receipt_record.retained_source_fields_json <> i.retained_source_fields_json
                       OR source_version.retained_source_fields_json <> i.retained_source_fields_json
                       OR terminal_policy.myopp_source_policy_id IS NULL
                       OR terminal_policy.policy_version <> i.policy_version
                       OR terminal_policy.retained_source_fields_json <> i.retained_source_fields_json
                       OR (i.disposition = N''removal'' AND terminal_policy.removal_allowed <> 1)
                       OR (i.disposition = N''termination'' AND terminal_policy.termination_allowed <> 1)
                )
                    THROW 55545, ''Content tombstones must bind one final paired receipt/version transition and exact policy metadata.'', 1;
            END');
        EXEC(N'
            CREATE TRIGGER dbo.trg_myopp_canonical_events_guard
            ON dbo.myopp_canonical_events AFTER INSERT, UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                IF EXISTS (SELECT 1 FROM deleted)
                    THROW 55546, ''Canonical events are append-only.'', 1;
                IF EXISTS
                (
                    SELECT 1
                    FROM inserted i
                    WHERE i.event_kind = N''content_tombstoned''
                      AND
                      (
                          ISNULL(TRY_CONVERT(nvarchar(32), SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')), N'''') <> N''active''
                          OR ISJSON(i.detail_json) <> 1
                          OR (SELECT COUNT(*) FROM OPENJSON(i.detail_json)) <> 2
                          OR NOT EXISTS (SELECT 1 FROM OPENJSON(i.detail_json) detail WHERE detail.[key] = N''disposition'' AND detail.[type] = 1 AND detail.[value] IN (N''removal'', N''termination''))
                          OR NOT EXISTS (SELECT 1 FROM OPENJSON(i.detail_json) detail WHERE detail.[key] = N''reason'' AND detail.[type] = 1 AND LEN(LTRIM(RTRIM(detail.[value]))) > 0)
                          OR EXISTS (SELECT 1 FROM OPENJSON(i.detail_json) detail WHERE detail.[key] NOT IN (N''disposition'', N''reason''))
                      )
                )
                    THROW 55547, ''Content tombstone events must be content-free disposition and reason records.'', 1;
            END');

        EXEC(N'
            CREATE PROCEDURE dbo.usp_myopp_tombstone_listing_content
                @myopp_source_listing_id bigint,
                @data_class nvarchar(20),
                @disposition nvarchar(20),
                @removal_reason nvarchar(80),
                @actor_ref nvarchar(160)
            WITH EXECUTE AS OWNER
            AS
            BEGIN
                SET NOCOUNT ON;
                SET XACT_ABORT ON;

                DECLARE @actioned_at_utc datetime2(7) = SYSUTCDATETIME();
                DECLARE @canonical_opportunity_id bigint;
                DECLARE @original_policy_key uniqueidentifier;
                DECLARE @source_id nvarchar(160);
                DECLARE @source_class nvarchar(80);
                DECLARE @external_reference nvarchar(300);
                DECLARE @terminal_policy_id bigint;
                DECLARE @terminal_policy_version int;
                DECLARE @retained_source_fields_json nvarchar(max);
                DECLARE @event_detail_json nvarchar(max);

                IF ISNULL(TRY_CONVERT(nvarchar(32), SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')), N'''') <> N''''
                    THROW 55548, ''Nested or caller-supplied terminal takedown context is refused.'', 1;
                IF @data_class NOT IN (N''fixture'', N''production'')
                   OR @disposition NOT IN (N''removal'', N''termination'')
                   OR LEN(LTRIM(RTRIM(@removal_reason))) = 0
                   OR LEN(LTRIM(RTRIM(@actor_ref))) = 0
                    THROW 55549, ''Terminal takedown arguments are invalid.'', 1;

                BEGIN TRY
                    BEGIN TRANSACTION;

                    SELECT
                        @canonical_opportunity_id = listing_record.myopp_canonical_opportunity_id,
                        @original_policy_key = original_policy.policy_key,
                        @source_id = listing_record.source_id,
                        @source_class = original_policy.source_class,
                        @external_reference = listing_record.external_reference
                    FROM dbo.myopp_source_listings listing_record WITH (UPDLOCK, HOLDLOCK)
                    JOIN dbo.myopp_source_policies original_policy WITH (UPDLOCK, HOLDLOCK)
                      ON original_policy.myopp_source_policy_id = listing_record.myopp_source_policy_id
                     AND original_policy.data_class = listing_record.data_class
                    WHERE listing_record.myopp_source_listing_id = @myopp_source_listing_id
                      AND listing_record.data_class = @data_class
                      AND listing_record.content_tombstoned_at_utc IS NULL
                      AND listing_record.source_id IS NOT NULL
                      AND listing_record.external_reference IS NOT NULL;

                    IF @canonical_opportunity_id IS NULL
                        THROW 55550, ''Terminal takedown target is absent, class-mismatched, or already terminal.'', 1;

                    SELECT TOP (1)
                        @terminal_policy_id = policy_record.myopp_source_policy_id,
                        @terminal_policy_version = policy_record.policy_version,
                        @retained_source_fields_json = policy_record.retained_source_fields_json
                    FROM dbo.myopp_source_policies policy_record WITH (UPDLOCK, HOLDLOCK)
                    WHERE policy_record.policy_key = @original_policy_key
                      AND policy_record.data_class = @data_class
                      AND policy_record.source_id = @source_id
                      AND policy_record.source_class = @source_class
                      AND policy_record.effective_at_utc <= @actioned_at_utc
                      AND (policy_record.expires_at_utc IS NULL OR policy_record.expires_at_utc > @actioned_at_utc)
                      AND ((@disposition = N''removal'' AND policy_record.removal_allowed = 1)
                           OR (@disposition = N''termination'' AND policy_record.termination_allowed = 1))
                      AND EXISTS
                          (
                              SELECT 1
                              FROM OPENJSON(policy_record.allowed_actions_json) action_record
                              WHERE action_record.[type] = 1
                                AND action_record.[value] = CASE WHEN @disposition = N''removal'' THEN N''remove'' ELSE N''terminate'' END
                          )
                      AND NOT EXISTS
                          (
                              SELECT 1
                              FROM dbo.myopp_source_policies later_policy
                              WHERE later_policy.policy_key = policy_record.policy_key
                                AND later_policy.data_class = policy_record.data_class
                                AND later_policy.policy_version > policy_record.policy_version
                          )
                    ORDER BY policy_record.policy_version DESC;

                    IF @terminal_policy_id IS NULL
                        THROW 55551, ''No current restrictive policy grants this terminal disposition.'', 1;
                    IF ISJSON(@retained_source_fields_json) <> 1
                       OR LEFT(LTRIM(@retained_source_fields_json), 1) <> N''[''
                       OR EXISTS
                          (
                               SELECT 1
                               FROM OPENJSON(@retained_source_fields_json) retained
                               WHERE retained.[type] <> 1
                                  OR retained.[value] COLLATE Latin1_General_100_BIN2 NOT IN
                                 (
                                     N''receipt.source_id'', N''receipt.external_reference'', N''receipt.received_at'',
                                     N''receipt.content_type'', N''receipt.byte_count'', N''receipt.payload'',
                                     N''listing.source_id'', N''listing.external_reference'', N''listing.expected_application_hosts'',
                                     N''source_version.content_sha256'', N''source_version.observed_at'',
                                     N''source_version.employer'', N''source_version.title'', N''source_version.locations'',
                                     N''source_version.arrangement'', N''source_version.application_url'',
                                     N''source_version.description'', N''source_version.requirement_clauses'',
                                     N''source_version.fields'', N''requirement_version.clause_fingerprint'',
                                     N''requirement_item.ordinal'', N''requirement_item.normalized_clause'',
                                     N''field_attribution.field_name''
                                 )
                          )
                        THROW 55552, ''Terminal policy retained-field decision is not a closed canonical allowlist.'', 1;

                    IF NOT EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_source_versions source_version WITH (UPDLOCK, HOLDLOCK)
                        WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                          AND source_version.data_class = @data_class
                    )
                        THROW 55553, ''Terminal takedown requires at least one source version.'', 1;
                    IF EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_source_versions source_version WITH (UPDLOCK, HOLDLOCK)
                        WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                          AND source_version.data_class = @data_class
                          AND (source_version.content_tombstoned_at_utc IS NOT NULL
                               OR NOT EXISTS
                                  (
                                      SELECT 1
                                      FROM dbo.myopp_source_version_receipt_links link_record WITH (UPDLOCK, HOLDLOCK)
                                      WHERE link_record.myopp_source_version_id = source_version.myopp_source_version_id
                                        AND link_record.data_class = @data_class
                                  )
                               OR NOT EXISTS
                                  (
                                      SELECT 1
                                      FROM dbo.myopp_source_version_receipt_links link_record WITH (UPDLOCK, HOLDLOCK)
                                      WHERE link_record.myopp_source_version_id = source_version.myopp_source_version_id
                                        AND link_record.myopp_source_receipt_id = source_version.myopp_source_receipt_id
                                        AND link_record.data_class = @data_class
                                  ))
                    )
                        THROW 55554, ''Terminal takedown refuses terminal or unpaired source versions.'', 1;
                    IF EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_source_receipts receipt_record WITH (UPDLOCK, HOLDLOCK)
                        WHERE receipt_record.data_class = @data_class
                          AND receipt_record.source_id = @source_id
                          AND receipt_record.external_reference = @external_reference
                          AND
                          (
                              receipt_record.content_tombstoned_at_utc IS NOT NULL
                              OR NOT EXISTS
                                 (
                                     SELECT 1
                                     FROM dbo.myopp_source_version_receipt_links link_record
                                     JOIN dbo.myopp_source_versions source_version
                                       ON source_version.myopp_source_version_id = link_record.myopp_source_version_id
                                      AND source_version.data_class = link_record.data_class
                                     WHERE link_record.myopp_source_receipt_id = receipt_record.myopp_source_receipt_id
                                       AND link_record.data_class = @data_class
                                       AND source_version.myopp_source_listing_id = @myopp_source_listing_id
                                 )
                          )
                    )
                        THROW 55555, ''Terminal takedown refuses an orphaned same-reference receipt.'', 1;
                    IF EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_source_version_receipt_links link_record
                        JOIN dbo.myopp_source_versions source_version
                          ON source_version.myopp_source_version_id = link_record.myopp_source_version_id
                         AND source_version.data_class = link_record.data_class
                        JOIN dbo.myopp_source_receipts receipt_record
                          ON receipt_record.myopp_source_receipt_id = link_record.myopp_source_receipt_id
                         AND receipt_record.data_class = link_record.data_class
                        WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                          AND link_record.data_class = @data_class
                          AND (receipt_record.source_id <> @source_id OR receipt_record.external_reference <> @external_reference)
                    )
                        THROW 55556, ''Terminal takedown refuses a cross-reference receipt association.'', 1;
                    IF EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_content_tombstones content_tombstone
                        JOIN dbo.myopp_source_version_receipt_links link_record
                          ON link_record.myopp_source_version_id = content_tombstone.myopp_source_version_id
                         AND link_record.myopp_source_receipt_id = content_tombstone.myopp_source_receipt_id
                         AND link_record.data_class = content_tombstone.data_class
                        JOIN dbo.myopp_source_versions source_version
                          ON source_version.myopp_source_version_id = link_record.myopp_source_version_id
                         AND source_version.data_class = link_record.data_class
                        WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                          AND content_tombstone.data_class = @data_class
                    )
                        THROW 55557, ''Terminal takedown refuses an already-tombstoned receipt/version pair.'', 1;
                    IF EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_requirement_versions requirement_version WITH (UPDLOCK, HOLDLOCK)
                        JOIN dbo.myopp_source_versions source_version
                          ON source_version.myopp_source_version_id = requirement_version.myopp_source_version_id
                         AND source_version.data_class = requirement_version.data_class
                        WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                          AND requirement_version.data_class = @data_class
                          AND requirement_version.content_tombstoned_at_utc IS NOT NULL
                    )
                    OR EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_requirement_items requirement_item WITH (UPDLOCK, HOLDLOCK)
                        JOIN dbo.myopp_requirement_versions requirement_version
                          ON requirement_version.myopp_requirement_version_id = requirement_item.myopp_requirement_version_id
                         AND requirement_version.data_class = requirement_item.data_class
                        JOIN dbo.myopp_source_versions source_version
                          ON source_version.myopp_source_version_id = requirement_version.myopp_source_version_id
                         AND source_version.data_class = requirement_version.data_class
                        WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                          AND requirement_item.data_class = @data_class
                          AND requirement_item.content_tombstoned_at_utc IS NOT NULL
                    )
                    OR EXISTS
                    (
                        SELECT 1
                        FROM dbo.myopp_canonical_field_attributions attribution_record WITH (UPDLOCK, HOLDLOCK)
                        WHERE attribution_record.data_class = @data_class
                          AND (attribution_record.myopp_source_listing_id = @myopp_source_listing_id
                               OR EXISTS
                                  (
                                      SELECT 1
                                      FROM dbo.myopp_source_versions source_version
                                      WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                                        AND source_version.myopp_source_version_id = attribution_record.myopp_source_version_id
                                        AND source_version.data_class = @data_class
                                  ))
                          AND attribution_record.content_tombstoned_at_utc IS NOT NULL
                    )
                        THROW 55558, ''Terminal takedown refuses a partially terminal derived aggregate.'', 1;

                    EXEC sys.sp_set_session_context @key = N''myopp.c2_terminal_takedown'', @value = N''active'';

                    UPDATE requirement_item
                    SET ordinal = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''requirement_item.ordinal'') THEN requirement_item.ordinal ELSE NULL END,
                        normalized_clause = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''requirement_item.normalized_clause'') THEN requirement_item.normalized_clause ELSE NULL END,
                        requirement_class = NULL, source_span_start = NULL, source_span_length = NULL, classification_basis = NULL,
                        content_tombstoned_at_utc = @actioned_at_utc, myopp_terminal_policy_id = @terminal_policy_id,
                        terminal_policy_version = @terminal_policy_version, terminal_disposition = @disposition,
                        tombstone_reason = @removal_reason, terminal_actor = @actor_ref,
                        retained_source_fields_json = @retained_source_fields_json
                    FROM dbo.myopp_requirement_items requirement_item
                    JOIN dbo.myopp_requirement_versions requirement_version
                      ON requirement_version.myopp_requirement_version_id = requirement_item.myopp_requirement_version_id
                     AND requirement_version.data_class = requirement_item.data_class
                    JOIN dbo.myopp_source_versions source_version
                      ON source_version.myopp_source_version_id = requirement_version.myopp_source_version_id
                     AND source_version.data_class = requirement_version.data_class
                    WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                      AND requirement_item.data_class = @data_class;

                    UPDATE requirement_version
                    SET clause_fingerprint = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''requirement_version.clause_fingerprint'') THEN requirement_version.clause_fingerprint ELSE NULL END,
                        content_tombstoned_at_utc = @actioned_at_utc, myopp_terminal_policy_id = @terminal_policy_id,
                        terminal_policy_version = @terminal_policy_version, terminal_disposition = @disposition,
                        tombstone_reason = @removal_reason, terminal_actor = @actor_ref,
                        retained_source_fields_json = @retained_source_fields_json
                    FROM dbo.myopp_requirement_versions requirement_version
                    JOIN dbo.myopp_source_versions source_version
                      ON source_version.myopp_source_version_id = requirement_version.myopp_source_version_id
                     AND source_version.data_class = requirement_version.data_class
                    WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                      AND requirement_version.data_class = @data_class;

                    UPDATE attribution_record
                    SET field_name = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''field_attribution.field_name'') THEN attribution_record.field_name ELSE NULL END,
                        content_tombstoned_at_utc = @actioned_at_utc, myopp_terminal_policy_id = @terminal_policy_id,
                        terminal_policy_version = @terminal_policy_version, terminal_disposition = @disposition,
                        tombstone_reason = @removal_reason, terminal_actor = @actor_ref,
                        retained_source_fields_json = @retained_source_fields_json
                    FROM dbo.myopp_canonical_field_attributions attribution_record
                    WHERE attribution_record.data_class = @data_class
                      AND (attribution_record.myopp_source_listing_id = @myopp_source_listing_id
                           OR EXISTS
                              (
                                  SELECT 1
                                  FROM dbo.myopp_source_versions source_version
                                  WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                                    AND source_version.myopp_source_version_id = attribution_record.myopp_source_version_id
                                    AND source_version.data_class = @data_class
                              ));

                    UPDATE source_version
                    SET content_sha256 = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.content_sha256'') THEN source_version.content_sha256 ELSE NULL END,
                        observed_at_utc = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.observed_at'') THEN source_version.observed_at_utc ELSE NULL END,
                        employer_name = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.employer'') THEN source_version.employer_name ELSE NULL END,
                        role_title = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.title'') THEN source_version.role_title ELSE NULL END,
                        locations_json = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.locations'') THEN source_version.locations_json ELSE NULL END,
                        arrangement = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.arrangement'') THEN source_version.arrangement ELSE NULL END,
                        application_url = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.application_url'') THEN source_version.application_url ELSE NULL END,
                        source_body = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.description'') THEN source_version.source_body ELSE NULL END,
                        normalized_requirements_json = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.requirement_clauses'') THEN source_version.normalized_requirements_json ELSE NULL END,
                        normalized_fields_json = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''source_version.fields'') THEN source_version.normalized_fields_json ELSE NULL END,
                        content_tombstoned_at_utc = @actioned_at_utc, myopp_terminal_policy_id = @terminal_policy_id,
                        terminal_policy_version = @terminal_policy_version, terminal_disposition = @disposition,
                        tombstone_reason = @removal_reason, terminal_actor = @actor_ref,
                        retained_source_fields_json = @retained_source_fields_json
                    FROM dbo.myopp_source_versions source_version
                    WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                      AND source_version.data_class = @data_class;

                    UPDATE receipt_record
                    SET source_id = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''receipt.source_id'') THEN receipt_record.source_id ELSE NULL END,
                        external_reference = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''receipt.external_reference'') THEN receipt_record.external_reference ELSE NULL END,
                        received_at_utc = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''receipt.received_at'') THEN receipt_record.received_at_utc ELSE NULL END,
                        content_type = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''receipt.content_type'') THEN receipt_record.content_type ELSE NULL END,
                        byte_count = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''receipt.byte_count'') THEN receipt_record.byte_count ELSE NULL END,
                        payload_sha256 = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''receipt.payload'') THEN receipt_record.payload_sha256 ELSE NULL END,
                        payload_body = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''receipt.payload'') THEN receipt_record.payload_body ELSE NULL END,
                        content_tombstoned_at_utc = @actioned_at_utc, myopp_terminal_policy_id = @terminal_policy_id,
                        terminal_policy_version = @terminal_policy_version, terminal_disposition = @disposition,
                        tombstone_reason = @removal_reason, terminal_actor = @actor_ref,
                        retained_source_fields_json = @retained_source_fields_json
                    FROM dbo.myopp_source_receipts receipt_record
                    JOIN dbo.myopp_source_version_receipt_links link_record
                      ON link_record.myopp_source_receipt_id = receipt_record.myopp_source_receipt_id
                     AND link_record.data_class = receipt_record.data_class
                    JOIN dbo.myopp_source_versions source_version
                      ON source_version.myopp_source_version_id = link_record.myopp_source_version_id
                     AND source_version.data_class = link_record.data_class
                    WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                      AND receipt_record.data_class = @data_class;

                    UPDATE listing_record
                    SET source_id = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''listing.source_id'') THEN listing_record.source_id ELSE NULL END,
                        external_reference = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''listing.external_reference'') THEN listing_record.external_reference ELSE NULL END,
                        application_url = NULL,
                        expected_application_hosts_json = CASE WHEN EXISTS (SELECT 1 FROM OPENJSON(@retained_source_fields_json) retained WHERE retained.[value] = N''listing.expected_application_hosts'') THEN listing_record.expected_application_hosts_json ELSE NULL END,
                        listing_state = CASE WHEN @disposition = N''removal'' THEN N''closed'' ELSE N''invalid'' END,
                        application_link_state = N''unknown'', application_link_invalid_reason = NULL,
                        link_last_attempted_at_utc = NULL, link_last_validated_at_utc = NULL,
                        last_attempted_at_utc = NULL, last_successfully_verified_at_utc = NULL,
                        link_review_pending = 0,
                        content_tombstoned_at_utc = @actioned_at_utc, myopp_terminal_policy_id = @terminal_policy_id,
                        terminal_policy_version = @terminal_policy_version, terminal_disposition = @disposition,
                        tombstone_reason = @removal_reason, terminal_actor = @actor_ref,
                        retained_source_fields_json = @retained_source_fields_json
                    FROM dbo.myopp_source_listings listing_record
                    WHERE listing_record.myopp_source_listing_id = @myopp_source_listing_id
                      AND listing_record.data_class = @data_class;

                    INSERT dbo.myopp_content_tombstones
                    (
                        myopp_source_receipt_id, myopp_source_version_id, data_class,
                        myopp_source_policy_id, policy_version, disposition, removal_reason,
                        actor_ref, retained_source_fields_json, actioned_at_utc
                    )
                    SELECT link_record.myopp_source_receipt_id, link_record.myopp_source_version_id, @data_class,
                           @terminal_policy_id, @terminal_policy_version, @disposition, @removal_reason,
                           @actor_ref, @retained_source_fields_json, @actioned_at_utc
                    FROM dbo.myopp_source_version_receipt_links link_record
                    JOIN dbo.myopp_source_versions source_version
                      ON source_version.myopp_source_version_id = link_record.myopp_source_version_id
                     AND source_version.data_class = link_record.data_class
                    WHERE source_version.myopp_source_listing_id = @myopp_source_listing_id
                      AND link_record.data_class = @data_class;

                    UPDATE canonical_opportunity
                    SET governing_listing_id = fallback_listing.myopp_source_listing_id,
                        governing_source_version_id = fallback_listing.current_source_version_id,
                        current_requirement_version_id = fallback_requirement.myopp_requirement_version_id
                    FROM dbo.myopp_canonical_opportunities canonical_opportunity
                    OUTER APPLY
                    (
                        SELECT TOP (1) candidate_listing.myopp_source_listing_id, candidate_listing.current_source_version_id
                        FROM dbo.myopp_source_listings candidate_listing
                        JOIN dbo.myopp_source_policies candidate_policy
                          ON candidate_policy.myopp_source_policy_id = candidate_listing.myopp_source_policy_id
                         AND candidate_policy.data_class = candidate_listing.data_class
                        WHERE candidate_listing.myopp_canonical_opportunity_id = canonical_opportunity.myopp_canonical_opportunity_id
                          AND candidate_listing.data_class = @data_class
                          AND candidate_listing.myopp_source_listing_id <> @myopp_source_listing_id
                          AND candidate_listing.content_tombstoned_at_utc IS NULL
                          AND candidate_listing.listing_state = N''current''
                        ORDER BY candidate_policy.source_priority, candidate_listing.myopp_source_listing_id
                    ) fallback_listing
                    OUTER APPLY
                    (
                        SELECT TOP (1) requirement_version.myopp_requirement_version_id
                        FROM dbo.myopp_requirement_versions requirement_version
                        WHERE requirement_version.myopp_source_version_id = fallback_listing.current_source_version_id
                          AND requirement_version.data_class = @data_class
                          AND requirement_version.content_tombstoned_at_utc IS NULL
                        ORDER BY requirement_version.myopp_requirement_version_id
                    ) fallback_requirement
                    WHERE canonical_opportunity.myopp_canonical_opportunity_id = @canonical_opportunity_id
                      AND canonical_opportunity.data_class = @data_class;

                    SELECT @event_detail_json =
                    (
                        SELECT @disposition AS disposition, @removal_reason AS reason
                        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
                    );
                    INSERT dbo.myopp_canonical_events
                    (
                        myopp_canonical_opportunity_id, data_class, event_kind, occurred_at_utc, detail_json
                    )
                    VALUES
                    (
                        @canonical_opportunity_id, @data_class, N''content_tombstoned'', @actioned_at_utc, @event_detail_json
                    );

                    EXEC sys.sp_set_session_context @key = N''myopp.c2_terminal_takedown'', @value = NULL;
                    COMMIT TRANSACTION;
                END TRY
                BEGIN CATCH
                    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                    EXEC sys.sp_set_session_context @key = N''myopp.c2_terminal_takedown'', @value = NULL;
                    THROW;
                END CATCH
            END');

        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-MYOPP-001',
            N'Additive My Opportunities C2 canonical shared-side source-policy, receipt, version, lifecycle, dedupe, attribution, requirement, event, and rights-tombstone foundation.',
            N'PeerSlate My Opportunities C2 v0.1'
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
