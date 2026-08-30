/* PS-SETTINGS-EXPORT-009 (account export evidence-rule reader --
   career_skill_links) production-safe owner-isolation verification.

   House pattern (PS-SETTINGS-EXPORT-007_media_transcript_reader_isolation_verify.sql,
   PS-SETTINGS-EXPORT-008_preferences_consent_reader_isolation_verify.sql):
   three synthetic owners (A, B, C) via a throwaway auth provider, C
   deactivated after its fixture is created, one outer always-rolled-back
   transaction, fresh THROW numbers in the 59300-59399 block (clear of
   this package's own migration/rollback 59200-59299 range and of every
   sibling verification file's range -- highest prior use anywhere under
   SQL FIles/ before this package is 59152).

   ONE PROCEDURE, NOT LOOPED. Every prior sibling package's own "0."
   section loops a table of reader names because it has several
   procedures to check identically; this package has exactly one, so
   its structural checks are written directly against that one
   procedure's OBJECT_DEFINITION rather than through loop machinery
   that would only ever run once.

   JOIN COUNT IS 2, NOT 1. Unlike PS-SETTINGS-EXPORT-008's three
   readers (each a top-level single-table read), this package's one
   reader joins dbo.career_skills for its skill_key linkage in addition
   to the identity header's own join to dbo.app_users -- two JOIN
   dbo. occurrences total, asserted explicitly in section 0b.

   TWO EXCLUDED REFERENCES, NEVER RESOLVED, NEVER JOINED.
   dbo.career_skill_links.source_entity_id (a dbo.slate_entities
   reference) and .evidence_item_id (a dbo.evidence_items reference)
   are both excluded outright -- never selected raw, never resolved to
   an opaque key, never joined. Section 0b asserts the procedure body
   never mentions dbo.slate_entities or dbo.evidence_items at all (a
   stronger check than a column-name grep: it proves no join to either
   table exists, not merely that one column is absent from the SELECT
   list). This is the identical boundary a prior sibling package drew
   for its own excluded polymorphic-entity reference column (see the
   migration file's own header for the full precedent), applied here to
   the second and third such reference this program has ever excluded
   this way.

   THE evidence_linked CANARY. The one thing this reader discloses
   about the excluded evidence_item_id reference is a derived bit,
   computed entirely from career_skill_links' own column (CASE WHEN
   evidence_item_id IS NOT NULL...) -- never a join, never any
   evidence_items content. Section 3's fixture deliberately varies this
   across owner A's three rows (two evidence-linked, one not) so the
   flag's true/false value is proven, not merely present in the
   procedure text without ever being exercised against a real 0/1
   contrast.

   EXCLUDED-COLUMN CANARIES, INTEGER-SHAPED. Unlike PS-SETTINGS-EXPORT-008's
   evidence_json/source_context (string columns with a distinctive
   payload to mark "must never be readable"), every column this
   procedure excludes -- skill_link_id, owner_profile_id, skill_id,
   source_entity_id, evidence_item_id, created_by_user_id -- is a plain
   internal bigint/int id with no string payload of its own to canary
   the same way. Their exclusion is proven differently: every one is
   captured into its own real, non-null Transact-SQL variable at fixture
   time (so the fixture provably wrote a genuine, known value, never an
   accidentally-absent one), and the capture table below declares the
   EXACT expected output shape, so an extra selected column (e.g.
   skill_id, evidence_item_id, owner_profile_id) would fail the
   INSERT ... EXEC itself with a column-count mismatch -- the identical
   "structurally impossible to smuggle through" proof
   PS-SETTINGS-EXPORT-008's own header describes for its own excluded
   columns. The one referenced evidence_items row per evidence-linked
   fixture row is ALSO given a distinctive "must never be readable"
   title, not because this reader could ever select it (it never joins
   dbo.evidence_items at all, so that risk does not exist structurally),
   but to prove the FK-satisfying evidence_items row was genuinely
   created with real content, not merely assumed to exist.

   OWNERSHIP -- TWO PREDICATED TABLES. dbo.career_skill_links carries
   its own owner_profile_id column directly (confirmed by reading
   PS-PLAT-006_living_resume_domain.sql's own DDL); the joined
   dbo.career_skills row is independently owner-predicated too, defense
   in depth beyond the composite FK_career_skill_links_skill_owner that
   already ties them to the same owner -- the identical "predicate every
   joined table" discipline PS-SETTINGS-EXPORT-003 already applies to
   its own chapter-joined extension readers.

   SOFT-DELETE BACK-DOOR PROOF. dbo.career_skill_links has no
   deleted_at_utc column of its own (confirmed by reading its own DDL);
   the joined dbo.career_skills row does, and this reader filters
   skill.deleted_at_utc IS NULL. Section 4 does not merely assert this
   textually: it soft-deletes the SKILL behind one of owner A's three
   links after the initial capture proof and re-invokes the reader,
   proving that specific link disappears from the output while owner
   A's other two links, and owner B's entirely separate fixture, are
   both untouched.

   Proof strategy:
     0. STRUCTURAL: exact "@UserKey nvarchar(300)" signature and no
        other parameter; the byte-identical identity-resolution header
        is present verbatim; an explicit ORDER BY is present; the
        read-window columns are present with exactly two SELECT
        keywords; no transaction-control keyword, write, or nested
        EXEC/dynamic SQL appears anywhere in the body; no
        link.deleted_at_utc reference (the table has no such column);
        skill.deleted_at_utc IS NULL is present (the joined skill's own
        soft-delete predicate, load-bearing, not redundant).
     0b. The content SELECT list -- located precisely as the text
        between the shared identity header's closing "IF @ProfileId IS
        NULL RETURN;" line and the procedure's own first subsequent
        "FROM dbo.career_skill_links AS link" -- never contains a
        forbidden column's fully-qualified reference and DOES contain
        the resolved skill_key linkage and the evidence_linked flag; the
        owner predicate is present on both the link and the joined
        skill; the join count is exactly 2; the procedure body never
        mentions dbo.slate_entities or dbo.evidence_items at all.
     1. Three synthetic owners (A, B, C) each get a constraint-complete
        fixture: their own dbo.slate_entities rows (one per skill, one
        per link source, one per evidence item -- each table's own
        UNIQUE(entity_id)-style constraint requires a distinct row, and
        source_entity_id has no such constraint of its own but is given
        its own row anyway for fixture clarity), a dbo.career_skills row,
        a dbo.evidence_items row for every evidence-linked fixture row,
        and one or more dbo.career_skill_links rows. Owner A gets three
        links (evidence-linked-and-ranked, no-evidence-no-rank, and a
        third whose SKILL is soft-deleted in section 4); owner B gets
        one contrasting link; owner C gets one minimal link and is then
        deactivated. Every NOT NULL no-DEFAULT column, CHECK constraint,
        and FOREIGN KEY on dbo.career_skill_links, dbo.career_skills,
        dbo.slate_entities, and dbo.evidence_items was re-read from their
        owning migrations before writing any INSERT below.
     2. Two synthetic-owner proofs (forged key, deactivated owner) via
        bare EXEC, checked by @@ROWCOUNT.
     3. DATA-LEVEL: calling as owner A must return exactly owner A's own
        three rows, carrying every distinguishing fixture value
        (resolved skill_key, relationship_type, approval_status,
        strength_rank including a genuine NULL, and the evidence_linked
        flag's true/false contrast), and must NEVER contain any value
        unique to owner B's fixture -- and symmetrically for B.
     4. Soft-delete back-door proof (see above).

   Every synthetic row is rolled back. This script performs no write of
   its own to any object outside this one transaction. */
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-SETTINGS-EXPORT-009')
        THROW 59300, 'PS-SETTINGS-EXPORT-009 is not registered.', 1;

    /* ------------------------------------------------------------
       0. Structural proof against the one reader procedure.
       ------------------------------------------------------------ */
    IF OBJECT_ID(N'dbo.usp_ReadAccountExportCareerSkillLinkForOwner', N'P') IS NULL
        THROW 59301, 'The account-export evidence-rule reader procedure is missing.', 1;

    DECLARE @CheckDefinition nvarchar(max);
    SET @CheckDefinition = OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ReadAccountExportCareerSkillLinkForOwner', N'P'));

    IF @CheckDefinition NOT LIKE N'%@UserKey nvarchar(300)%'
        THROW 59302, 'The evidence-rule reader procedure does not declare @UserKey nvarchar(300) as its parameter.', 1;
    IF @CheckDefinition LIKE N'%@UserKey nvarchar(300),%'
       OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) OUTPUT%'
       OR @CheckDefinition LIKE N'%@UserKey nvarchar(300) output%'
        THROW 59302, 'The evidence-rule reader procedure declares more than just @UserKey nvarchar(300).', 1;
    IF @CheckDefinition LIKE N'%@OwnerProfileId%'
       OR @CheckDefinition LIKE N'%@OwnerUserId%'
       OR @CheckDefinition LIKE N'%@TableName%'
       OR @CheckDefinition LIKE N'%@SkillId%'
       OR @CheckDefinition LIKE N'%@EvidenceItemId%'
       OR @CheckDefinition LIKE N'%@SourceEntityId%'
        THROW 59302, 'The evidence-rule reader procedure accepts a caller-supplied owner id or target.', 1;
    IF @CheckDefinition NOT LIKE N'%app_user.user_key = @UserKey%'
        THROW 59303, 'The evidence-rule reader procedure does not resolve @UserKey itself.', 1;
    IF @CheckDefinition NOT LIKE N'%app_user.active = 1%'
       OR @CheckDefinition NOT LIKE N'%profile.active = 1%'
        THROW 59303, 'The evidence-rule reader procedure does not require an active user AND an active profile.', 1;
    IF @CheckDefinition NOT LIKE N'%IF @ProfileId IS NULL RETURN%'
        THROW 59303, 'The evidence-rule reader procedure does not use the shared byte-identical identity header.', 1;
    IF @CheckDefinition NOT LIKE N'%ORDER BY%'
        THROW 59304, 'The evidence-rule reader procedure has no deterministic ORDER BY.', 1;
    IF @CheckDefinition LIKE N'%SELECT *%' OR @CheckDefinition LIKE N'%SELECT*%'
        THROW 59304, 'The evidence-rule reader procedure uses SELECT * instead of an explicit column list.', 1;
    IF @CheckDefinition NOT LIKE N'%read_started_at_utc%' OR @CheckDefinition NOT LIKE N'%read_ended_at_utc%'
        THROW 59305, 'The evidence-rule reader procedure does not return the read-window columns.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'SELECT', N''))) / LEN(N'SELECT') <> 2
        THROW 59305, 'The evidence-rule reader procedure does not contain exactly two SELECT keywords.', 1;
    IF @CheckDefinition LIKE N'%BEGIN TRAN%'
       OR @CheckDefinition LIKE N'%COMMIT%'
       OR @CheckDefinition LIKE N'%ROLLBACK%'
       OR @CheckDefinition LIKE N'%BEGIN TRY%'
       OR @CheckDefinition LIKE N'%BEGIN CATCH%'
       OR @CheckDefinition LIKE N'%INSERT %'
       OR @CheckDefinition LIKE N'%UPDATE %'
       OR @CheckDefinition LIKE N'%DELETE %'
       OR @CheckDefinition LIKE N'%EXEC%'
        THROW 59306, 'The evidence-rule reader procedure contains transaction control, a write, or dynamic SQL -- it is not a plain read-only SELECT.', 1;
    IF @CheckDefinition LIKE N'%link.deleted_at_utc%'
        THROW 59306, 'The evidence-rule reader procedure references a soft-delete column that does not exist on dbo.career_skill_links.', 1;
    IF @CheckDefinition NOT LIKE N'%skill.deleted_at_utc IS NULL%'
        THROW 59306, 'The evidence-rule reader procedure does not exclude a soft-deleted joined skill -- the back-door predicate is missing.', 1;

    /* ------------------------------------------------------------
       0b. Forbidden-column, resolved-linkage, owner-predicate,
           join-count, and excluded-table proof. The content SELECT
           list is located precisely between the shared identity
           header's closing line and the procedure's own first FROM
           clause.
       ------------------------------------------------------------ */
    DECLARE @HeaderEnd nvarchar(60) = N'IF @ProfileId IS NULL RETURN;';
    DECLARE @ListStart int = CHARINDEX(@HeaderEnd, @CheckDefinition) + LEN(@HeaderEnd);
    DECLARE @ListEnd int = CHARINDEX(N'FROM dbo.career_skill_links AS link', @CheckDefinition, @ListStart);
    IF @ListStart <= LEN(@HeaderEnd) OR @ListEnd = 0
        THROW 59310, 'Could not locate the evidence-rule reader''s content select list.', 1;
    DECLARE @SelectList nvarchar(max) = SUBSTRING(@CheckDefinition, @ListStart, @ListEnd - @ListStart);

    /* The derived evidence_linked bit is the ONE sanctioned mention of
       link.evidence_item_id inside the select list: the expression tests
       IS NOT NULL and outputs a bit; the column's VALUE never leaves the
       procedure. Assert the sanctioned expression is present exactly
       once, then neutralize exactly it before the forbidden scan, so the
       scan stays fully strict for any other appearance of the column.
       (Gate run 1 correctly refused to complete until this sanction was
       made explicit here -- the scan as first written contradicted the
       reader's own disclosed design.) */
    DECLARE @SanctionedEvidenceBit nvarchar(200) =
        N'CASE WHEN link.evidence_item_id IS NOT NULL THEN 1 ELSE 0';
    IF CHARINDEX(@SanctionedEvidenceBit, @SelectList) = 0
        THROW 59310, 'The evidence-rule reader''s sanctioned evidence_linked derivation is missing from its select list.', 1;
    IF CHARINDEX(@SanctionedEvidenceBit, @SelectList, CHARINDEX(@SanctionedEvidenceBit, @SelectList) + 1) > 0
        THROW 59310, 'The sanctioned evidence_linked derivation appears more than once in the select list.', 1;
    SET @SelectList = REPLACE(@SelectList, @SanctionedEvidenceBit, N'(sanctioned evidence_linked derivation)');

    IF @SelectList LIKE N'%link.skill_link_id%'
       OR @SelectList LIKE N'%link.owner_profile_id%'
       OR @SelectList LIKE N'%link.skill_id%'
       OR @SelectList LIKE N'%link.source_entity_id%'
       OR @SelectList LIKE N'%link.evidence_item_id%'
       OR @SelectList LIKE N'%link.created_by_user_id%'
       OR @SelectList LIKE N'%skill.skill_id%'
       OR @SelectList LIKE N'%skill.owner_profile_id%'
        THROW 59310, 'The evidence-rule reader selects a forbidden column.', 1;
    IF @SelectList NOT LIKE N'%skill.skill_key%'
        THROW 59310, 'The evidence-rule reader is missing its resolved skill_key linkage.', 1;
    IF @SelectList NOT LIKE N'%evidence_linked%'
        THROW 59310, 'The evidence-rule reader is missing its derived evidence_linked flag.', 1;
    IF @CheckDefinition LIKE N'%slate_entities%'
        THROW 59311, 'The evidence-rule reader references dbo.slate_entities; source_entity_id must never be resolved or joined.', 1;
    IF @CheckDefinition LIKE N'%evidence_items%'
        THROW 59311, 'The evidence-rule reader references dbo.evidence_items directly; it is out of this package''s scope.', 1;
    IF @CheckDefinition NOT LIKE N'%link.owner_profile_id = @ProfileId%'
        THROW 59312, 'The evidence-rule reader is missing its owner predicate on dbo.career_skill_links.', 1;
    IF @CheckDefinition NOT LIKE N'%skill.owner_profile_id = @ProfileId%'
        THROW 59312, 'The evidence-rule reader is missing its owner predicate on the joined dbo.career_skills row.', 1;
    IF (LEN(@CheckDefinition) - LEN(REPLACE(@CheckDefinition, N'JOIN dbo.', N''))) / LEN(N'JOIN dbo.') <> 2
        THROW 59313, 'The evidence-rule reader''s join count is not exactly 2 (the identity header''s own join plus the career_skills join).', 1;

    /* ------------------------------------------------------------
       1. Three synthetic owners (A, B, C) via a throwaway auth
          provider. C is deactivated after its fixture is created.
       ------------------------------------------------------------ */
    DECLARE @Suffix nvarchar(36) = CONVERT(nvarchar(36), NEWID());
    DECLARE @Issuer nvarchar(500) = N'urn:peerslate:settings-export-x9-verification';
    DECLARE @SubjectA nvarchar(500) = CONCAT(N'settings-export-x9-a-', @Suffix);
    DECLARE @SubjectB nvarchar(500) = CONCAT(N'settings-export-x9-b-', @Suffix);
    DECLARE @SubjectC nvarchar(500) = CONCAT(N'settings-export-x9-c-', @Suffix);

    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x9-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectA, @DisplayName = N'PSX9 Owner A', @Email = N'psx9-owner-a@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x9-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectB, @DisplayName = N'PSX9 Owner B', @Email = N'psx9-owner-b@example.invalid';
    EXEC dbo.usp_UpsertAppUserFromAuth
        @AuthProvider = N'settings-export-x9-verification', @AuthIssuer = @Issuer,
        @AuthSubject = @SubjectC, @DisplayName = N'PSX9 Owner C';

    DECLARE @UserKeyA nvarchar(300);
    DECLARE @UserKeyB nvarchar(300);
    DECLARE @UserKeyC nvarchar(300);
    DECLARE @ProfileIdA bigint;
    DECLARE @ProfileIdB bigint;
    DECLARE @ProfileIdC bigint;
    DECLARE @UserIdA int;
    DECLARE @UserIdB int;
    DECLARE @UserIdC int;

    SELECT @UserKeyA = app_user.user_key, @ProfileIdA = profile.profile_id, @UserIdA = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x9-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectA;

    SELECT @UserKeyB = app_user.user_key, @ProfileIdB = profile.profile_id, @UserIdB = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x9-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectB;

    SELECT @UserKeyC = app_user.user_key, @ProfileIdC = profile.profile_id, @UserIdC = app_user.id
    FROM dbo.app_users AS app_user
    JOIN dbo.user_identities AS identity_row ON identity_row.user_id = app_user.id
    JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
    WHERE identity_row.provider = N'settings-export-x9-verification'
      AND identity_row.issuer = @Issuer AND identity_row.subject = @SubjectC;

    IF @UserKeyA IS NULL OR @UserKeyB IS NULL OR @UserKeyC IS NULL
       OR @ProfileIdA IS NULL OR @ProfileIdB IS NULL OR @ProfileIdC IS NULL
       OR @ProfileIdA = @ProfileIdB OR @ProfileIdB = @ProfileIdC OR @ProfileIdA = @ProfileIdC
        THROW 59320, 'Synthetic evidence-rule verification owners were not provisioned.', 1;

    /* ------------------------------------------------------------
       Fixture. Every NOT NULL no-DEFAULT column, CHECK constraint, and
       FOREIGN KEY on dbo.career_skill_links, dbo.career_skills,
       dbo.slate_entities, and dbo.evidence_items was re-read from
       PS-PLAT-006_living_resume_domain.sql / PS-PLAT-002_profiles_entities_access.sql /
       PS-PLAT-003_evidence_ai.sql before writing any INSERT below.
       ------------------------------------------------------------ */
    DECLARE @EntitySkillA1 bigint, @EntitySkillA2 bigint, @EntitySkillA3 bigint, @EntitySkillB1 bigint, @EntitySkillC1 bigint;
    DECLARE @EntitySourceA1 bigint, @EntitySourceA2 bigint, @EntitySourceA3 bigint, @EntitySourceB1 bigint, @EntitySourceC1 bigint;
    DECLARE @EntityEvidenceA1 bigint, @EntityEvidenceA3 bigint, @EntityEvidenceB1 bigint;

    DECLARE @SkillIdA1 bigint, @SkillIdA2 bigint, @SkillIdA3 bigint, @SkillIdB1 bigint, @SkillIdC1 bigint;
    DECLARE @SkillKeyA1 uniqueidentifier, @SkillKeyA2 uniqueidentifier, @SkillKeyA3 uniqueidentifier;
    DECLARE @SkillKeyB1 uniqueidentifier;

    DECLARE @EvidenceItemIdA1 bigint, @EvidenceItemIdA3 bigint, @EvidenceItemIdB1 bigint;

    DECLARE @LinkIdA1 bigint, @LinkIdA2 bigint, @LinkIdA3 bigint, @LinkIdB1 bigint, @LinkIdC1 bigint;

    DECLARE @LinkCreatedAtUtcA1 datetime2(7) = DATEADD(MINUTE, -20, SYSUTCDATETIME());
    DECLARE @LinkCreatedAtUtcA2 datetime2(7) = DATEADD(MINUTE, -25, SYSUTCDATETIME());
    DECLARE @LinkCreatedAtUtcA3 datetime2(7) = DATEADD(MINUTE, -15, SYSUTCDATETIME());
    DECLARE @LinkCreatedAtUtcB1 datetime2(7) = DATEADD(MINUTE, -10, SYSUTCDATETIME());
    DECLARE @LinkCreatedAtUtcC1 datetime2(7) = SYSUTCDATETIME();

    ------------------------------------------------------------------
    -- Owner A fixture: three skills, three links (A1 evidence-linked
    -- and ranked; A2 no evidence and no rank; A3 evidence-linked --
    -- its SKILL is soft-deleted in section 4 to prove the back-door
    -- exclusion). Each skill and each link source gets its own
    -- dbo.slate_entities row (career_skills' own UQ_career_skills_entity
    -- requires a distinct entity_id per skill; source_entity_id has no
    -- analogous constraint but is given its own row anyway for fixture
    -- clarity).
    ------------------------------------------------------------------
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_skill');
    SET @EntitySkillA1 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_skill');
    SET @EntitySkillA2 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_skill');
    SET @EntitySkillA3 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_skill_link_source');
    SET @EntitySourceA1 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_skill_link_source');
    SET @EntitySourceA2 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'career_skill_link_source');
    SET @EntitySourceA3 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'evidence_item');
    SET @EntityEvidenceA1 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdA, N'evidence_item');
    SET @EntityEvidenceA3 = CONVERT(bigint, SCOPE_IDENTITY());

    INSERT dbo.career_skills (owner_profile_id, entity_id, skill_name)
    VALUES (@ProfileIdA, @EntitySkillA1, N'PSX9-A Skill One');
    SET @SkillIdA1 = SCOPE_IDENTITY();
    INSERT dbo.career_skills (owner_profile_id, entity_id, skill_name)
    VALUES (@ProfileIdA, @EntitySkillA2, N'PSX9-A Skill Two');
    SET @SkillIdA2 = SCOPE_IDENTITY();
    INSERT dbo.career_skills (owner_profile_id, entity_id, skill_name)
    VALUES (@ProfileIdA, @EntitySkillA3, N'PSX9-A Skill Three');
    SET @SkillIdA3 = SCOPE_IDENTITY();

    SELECT @SkillKeyA1 = skill_key FROM dbo.career_skills WHERE skill_id = @SkillIdA1;
    SELECT @SkillKeyA2 = skill_key FROM dbo.career_skills WHERE skill_id = @SkillIdA2;
    SELECT @SkillKeyA3 = skill_key FROM dbo.career_skills WHERE skill_id = @SkillIdA3;

    INSERT dbo.evidence_items (entity_id, owner_profile_id, title, evidence_type, source_kind, evidence_state)
    VALUES (@EntityEvidenceA1, @ProfileIdA, N'PSX9-A evidence must never be readable one', N'settings-export-x9-verification-type', N'member', N'self_reported');
    SET @EvidenceItemIdA1 = SCOPE_IDENTITY();
    INSERT dbo.evidence_items (entity_id, owner_profile_id, title, evidence_type, source_kind, evidence_state)
    VALUES (@EntityEvidenceA3, @ProfileIdA, N'PSX9-A evidence must never be readable three', N'settings-export-x9-verification-type', N'member', N'self_reported');
    SET @EvidenceItemIdA3 = SCOPE_IDENTITY();

    INSERT dbo.career_skill_links (owner_profile_id, skill_id, source_entity_id, evidence_item_id, relationship_type, approval_status, strength_rank, created_by_user_id, created_at_utc)
    VALUES (@ProfileIdA, @SkillIdA1, @EntitySourceA1, @EvidenceItemIdA1, N'demonstrated_in', N'approved', 85, @UserIdA, @LinkCreatedAtUtcA1);
    SET @LinkIdA1 = SCOPE_IDENTITY();
    INSERT dbo.career_skill_links (owner_profile_id, skill_id, source_entity_id, evidence_item_id, relationship_type, approval_status, strength_rank, created_by_user_id, created_at_utc)
    VALUES (@ProfileIdA, @SkillIdA2, @EntitySourceA2, NULL, N'learned_in', N'proposed', NULL, @UserIdA, @LinkCreatedAtUtcA2);
    SET @LinkIdA2 = SCOPE_IDENTITY();
    INSERT dbo.career_skill_links (owner_profile_id, skill_id, source_entity_id, evidence_item_id, relationship_type, approval_status, strength_rank, created_by_user_id, created_at_utc)
    VALUES (@ProfileIdA, @SkillIdA3, @EntitySourceA3, @EvidenceItemIdA3, N'supported_by', N'approved', 50, @UserIdA, @LinkCreatedAtUtcA3);
    SET @LinkIdA3 = SCOPE_IDENTITY();

    ------------------------------------------------------------------
    -- Owner B fixture: one skill, one evidence-linked link --
    -- contrasting values from owner A's, to prove isolation is
    -- genuinely owner_profile_id-scoped.
    ------------------------------------------------------------------
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'career_skill');
    SET @EntitySkillB1 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'career_skill_link_source');
    SET @EntitySourceB1 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdB, N'evidence_item');
    SET @EntityEvidenceB1 = CONVERT(bigint, SCOPE_IDENTITY());

    INSERT dbo.career_skills (owner_profile_id, entity_id, skill_name)
    VALUES (@ProfileIdB, @EntitySkillB1, N'PSX9-B Skill One');
    SET @SkillIdB1 = SCOPE_IDENTITY();
    SELECT @SkillKeyB1 = skill_key FROM dbo.career_skills WHERE skill_id = @SkillIdB1;

    INSERT dbo.evidence_items (entity_id, owner_profile_id, title, evidence_type, source_kind, evidence_state)
    VALUES (@EntityEvidenceB1, @ProfileIdB, N'PSX9-B evidence must never be readable', N'settings-export-x9-verification-type', N'member', N'self_reported');
    SET @EvidenceItemIdB1 = SCOPE_IDENTITY();

    INSERT dbo.career_skill_links (owner_profile_id, skill_id, source_entity_id, evidence_item_id, relationship_type, approval_status, strength_rank, created_by_user_id, created_at_utc)
    VALUES (@ProfileIdB, @SkillIdB1, @EntitySourceB1, @EvidenceItemIdB1, N'applied_in', N'rejected', 10, @UserIdB, @LinkCreatedAtUtcB1);
    SET @LinkIdB1 = SCOPE_IDENTITY();

    ------------------------------------------------------------------
    -- Owner C fixture: one minimal link, then C is deactivated -- must
    -- read as zero rows thereafter even though the row still
    -- physically exists.
    ------------------------------------------------------------------
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdC, N'career_skill');
    SET @EntitySkillC1 = CONVERT(bigint, SCOPE_IDENTITY());
    INSERT dbo.slate_entities (owner_profile_id, entity_type) VALUES (@ProfileIdC, N'career_skill_link_source');
    SET @EntitySourceC1 = CONVERT(bigint, SCOPE_IDENTITY());

    INSERT dbo.career_skills (owner_profile_id, entity_id, skill_name)
    VALUES (@ProfileIdC, @EntitySkillC1, N'PSX9-C Skill One');
    SET @SkillIdC1 = SCOPE_IDENTITY();

    INSERT dbo.career_skill_links (owner_profile_id, skill_id, source_entity_id, evidence_item_id, relationship_type, approval_status, strength_rank, created_by_user_id, created_at_utc)
    VALUES (@ProfileIdC, @SkillIdC1, @EntitySourceC1, NULL, N'demonstrated_in', N'proposed', NULL, @UserIdC, @LinkCreatedAtUtcC1);
    SET @LinkIdC1 = SCOPE_IDENTITY();

    UPDATE dbo.app_users SET active = 0 WHERE id = @UserIdC;
    IF @@ROWCOUNT <> 1
        THROW 59321, 'Could not deactivate synthetic owner C for the inactive-owner proof.', 1;

    DECLARE @ForgedUserKey nvarchar(300) = N'forged-user-key-does-not-exist';

    /* ------------------------------------------------------------
       2. Bare-EXEC forged-@UserKey and deactivated-owner proofs.
       ------------------------------------------------------------ */
    EXEC dbo.usp_ReadAccountExportCareerSkillLinkForOwner @UserKey = @ForgedUserKey;
    IF @@ROWCOUNT <> 0 THROW 59330, 'A forged UserKey returned a career-skill-link row.', 1;

    EXEC dbo.usp_ReadAccountExportCareerSkillLinkForOwner @UserKey = @UserKeyC;
    IF @@ROWCOUNT <> 0 THROW 59331, 'A deactivated owner''s career-skill-link row was still readable, despite the row still physically existing.', 1;

    /* ------------------------------------------------------------
       3. Real, two-owner, field-value isolation proof via
          INSERT ... EXEC. The capture table declares the exact
          expected output shape, so an extra selected column (e.g.
          skill_id, evidence_item_id, source_entity_id, owner_profile_id)
          would fail the INSERT ... EXEC itself.
       ------------------------------------------------------------ */
    DECLARE @LinkCapture TABLE
    (
        skill_key uniqueidentifier, relationship_type nvarchar(30), approval_status nvarchar(30),
        strength_rank tinyint, evidence_linked bit, created_at_utc datetime2(7),
        read_started_at_utc datetime2(7), read_ended_at_utc datetime2(7)
    );

    INSERT @LinkCapture EXEC dbo.usp_ReadAccountExportCareerSkillLinkForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @LinkCapture) <> 3
        THROW 59340, 'Owner A''s career-skill-link capture does not have exactly three rows.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @LinkCapture
        WHERE skill_key = @SkillKeyA1 AND relationship_type = N'demonstrated_in' AND approval_status = N'approved'
          AND strength_rank = 85 AND evidence_linked = 1 AND created_at_utc = @LinkCreatedAtUtcA1
    )
        THROW 59340, 'Owner A''s first (evidence-linked, ranked) career-skill-link row is missing or has the wrong values.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @LinkCapture
        WHERE skill_key = @SkillKeyA2 AND relationship_type = N'learned_in' AND approval_status = N'proposed'
          AND strength_rank IS NULL AND evidence_linked = 0 AND created_at_utc = @LinkCreatedAtUtcA2
    )
        THROW 59340, 'Owner A''s second (no-evidence, no-rank) career-skill-link row is missing or has the wrong values -- this is the central evidence_linked = 0 proof.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @LinkCapture
        WHERE skill_key = @SkillKeyA3 AND relationship_type = N'supported_by' AND approval_status = N'approved'
          AND strength_rank = 50 AND evidence_linked = 1 AND created_at_utc = @LinkCreatedAtUtcA3
    )
        THROW 59340, 'Owner A''s third (evidence-linked, pre-soft-delete) career-skill-link row is missing or has the wrong values.', 1;
    IF EXISTS (SELECT 1 FROM @LinkCapture WHERE skill_key = @SkillKeyB1 OR relationship_type = N'applied_in' OR strength_rank = 10)
        THROW 59341, 'Owner A''s career-skill-link capture contains owner B''s values.', 1;
    IF EXISTS (SELECT 1 FROM @LinkCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 59342, 'Owner A''s career-skill-link capture has a missing or non-monotonic read window.', 1;

    DELETE @LinkCapture;
    INSERT @LinkCapture EXEC dbo.usp_ReadAccountExportCareerSkillLinkForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @LinkCapture) <> 1
        THROW 59340, 'Owner B''s career-skill-link capture does not have exactly one row.', 1;
    IF NOT EXISTS
    (
        SELECT 1 FROM @LinkCapture
        WHERE skill_key = @SkillKeyB1 AND relationship_type = N'applied_in' AND approval_status = N'rejected'
          AND strength_rank = 10 AND evidence_linked = 1 AND created_at_utc = @LinkCreatedAtUtcB1
    )
        THROW 59340, 'Owner B''s career-skill-link row is missing or has the wrong values.', 1;
    IF EXISTS (SELECT 1 FROM @LinkCapture WHERE skill_key IN (@SkillKeyA1, @SkillKeyA2, @SkillKeyA3))
        THROW 59341, 'Owner B''s career-skill-link capture contains one of owner A''s rows.', 1;
    IF EXISTS (SELECT 1 FROM @LinkCapture WHERE read_started_at_utc IS NULL OR read_ended_at_utc IS NULL OR read_ended_at_utc < read_started_at_utc)
        THROW 59342, 'Owner B''s career-skill-link capture has a missing or non-monotonic read window.', 1;

    /* ------------------------------------------------------------
       4. Soft-delete back-door proof. Soft-deleting the SKILL behind
          owner A's third link must remove that link from the reader's
          output while leaving owner A's other two links, and owner
          B's entirely separate fixture, untouched.
       ------------------------------------------------------------ */
    UPDATE dbo.career_skills SET deleted_at_utc = SYSUTCDATETIME() WHERE skill_id = @SkillIdA3;
    IF @@ROWCOUNT <> 1
        THROW 59350, 'Could not soft-delete owner A''s third skill for the back-door proof.', 1;

    DELETE @LinkCapture;
    INSERT @LinkCapture EXEC dbo.usp_ReadAccountExportCareerSkillLinkForOwner @UserKey = @UserKeyA;
    IF (SELECT COUNT(*) FROM @LinkCapture) <> 2
        THROW 59350, 'Owner A''s career-skill-link capture did not drop to two rows after the joined skill''s soft-delete.', 1;
    IF EXISTS (SELECT 1 FROM @LinkCapture WHERE skill_key = @SkillKeyA3)
        THROW 59350, 'A career-skill-link row whose joined skill was soft-deleted is still returned -- the back door is open.', 1;
    IF NOT EXISTS (SELECT 1 FROM @LinkCapture WHERE skill_key IN (@SkillKeyA1, @SkillKeyA2))
        THROW 59351, 'Soft-deleting one skill incorrectly hid a sibling career-skill-link for the same owner.', 1;

    DELETE @LinkCapture;
    INSERT @LinkCapture EXEC dbo.usp_ReadAccountExportCareerSkillLinkForOwner @UserKey = @UserKeyB;
    IF (SELECT COUNT(*) FROM @LinkCapture) <> 1
        THROW 59351, 'Owner A''s soft-delete proof disturbed owner B''s unrelated career-skill-link fixture.', 1;

    ROLLBACK TRANSACTION;

    SELECT
        CAST(1 AS bit) AS verified,
        N'PS-SETTINGS-EXPORT-009: structural grep against the one evidence-rule reader procedure (exact @UserKey nvarchar(300) signature and no other parameter, byte-identical identity header, deterministic ORDER BY, read-window columns present with exactly two SELECT keywords, no transaction control/write/dynamic SQL, no link.deleted_at_utc reference, the joined skill''s own deleted_at_utc IS NULL predicate present); forbidden-column absence, resolved skill_key linkage, the derived evidence_linked flag, owner predicates on both the link and the joined skill, a join count of exactly 2, and no reference anywhere to dbo.slate_entities or dbo.evidence_items -- all verified against the procedure''s own isolated content select-list and full body text; a forged UserKey and a deactivated owner both yield zero rows (never an error); real two-owner fixture data (three career-skill-links for owner A spanning an evidence-linked-and-ranked row, a no-evidence-no-rank row, and a third later soft-delete-tested row, contrasted against one evidence-linked row for owner B) proves the reader returns exactly and only the calling owner''s own rows, complete with the resolved skill_key, a genuine evidence_linked true/false contrast, non-null monotonic read windows, and no leaked skill_id/source_entity_id/evidence_item_id/owner_profile_id; soft-deleting the skill behind one career-skill-link removes exactly that link while leaving sibling links and the other owner''s fixture untouched; full synthetic rollback verified.' AS detail;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
