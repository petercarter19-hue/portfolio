"""Static SQL regression evidence only; no engine/transaction execution claims."""
import json
import re
from pathlib import Path
import unittest
from tests.test_living_resume_editor_migration import procedure_batches, assert_balanced_sql_delimiters
ROOT = Path(__file__).resolve().parents[1]
PROPOSED = ROOT / 'SQL FIles/Migrations/proposed'
OLD = (PROPOSED / 'PS-RESUME-EDIT-001_private_commands.sql').read_text(encoding='utf-8')
FORWARD = (PROPOSED / 'PS-RESUME-EDIT-002_education_commands.sql').read_text(encoding='utf-8')
ROLLBACK = (PROPOSED / 'PS-RESUME-EDIT-002_education_commands_rollback.sql').read_text(encoding='utf-8')
PROCS = {k: v.replace("''", "'") for k, v in procedure_batches(FORWARD).items()}
COMMAND = PROCS['usp_CommitLivingResumeCommandForOwner']
READER = PROCS['usp_GetOwnerLivingResumeEditor']

class ResumeEducationMigrationTests(unittest.TestCase):

    def test_proposed_registration_and_closed_rollback_preserve_existing_data(self):
        registry = json.loads((ROOT / 'SQL FIles/Migrations/registry.json').read_text(encoding='utf-8'))['migrations']
        entry = next((x for x in registry if x['id'] == 'PS-RESUME-EDIT-002'))
        assert entry['requires'] == ['PS-RESUME-EDIT-001']
        if entry['gate'] is not None:
            from scripts.migration_registry import load_registry, gate_status
            migration = load_registry(root=ROOT).get(entry['id'])
            self.assertTrue(gate_status(migration, ROOT)[0])
        assert 'WITH (UPDLOCK, HOLDLOCK)' in ROLLBACK
        assert "WHERE record_type=N'education'" in ROLLBACK
        assert ROLLBACK.index('Rollback refused') < ROLLBACK.index('ALTER TABLE')
        assert procedure_batches(ROLLBACK) == procedure_batches(OLD)
        assert not re.search('(?:DELETE|DROP TABLE|ALTER TABLE)\\s+(?:FROM\\s+)?dbo\\.career_education', FORWARD + ROLLBACK, re.I)
        assert 'DELETE dbo.schema_migrations WHERE migration_id' in ROLLBACK

    def test_only_receipt_vocabulary_constraints_are_extended_and_remain_trusted(self):
        names = re.findall('DROP CONSTRAINT (\\w+)', FORWARD)
        assert names == ['CK_living_resume_command_receipts_type', 'CK_living_resume_command_receipts_record_type']
        assert FORWARD.count('WITH CHECK ADD CONSTRAINT') == 2
        assert 'NOCHECK' not in FORWARD
        assert "N'create_education'" in FORWARD and "N'update_education'" in FORWARD and ("N'remove_education'" in FORWARD)

    def test_existing_five_reader_sets_are_byte_preserved_before_education(self):
        old_reader = procedure_batches(OLD)['usp_GetOwnerLivingResumeEditor'].replace("''", "'")
        assert READER.startswith(old_reader.rsplit('        END;', 1)[0])
        education = READER[len(old_reader.rsplit('        END;', 1)[0]):]
        for required in ["chapter.chapter_type = N'education'", 'education.owner_profile_id = chapter.owner_profile_id', 'entity.owner_profile_id = chapter.owner_profile_id', 'chapter.owner_profile_id = @ProfileId', "chapter.visibility = N'private'", 'entity_publication_versions', 'entity_access_grants', 'content_approval_events', 'education.education_status', 'education.grade_text', 'chapter.row_version', 'ORDER BY chapter.display_order']:
            assert required in education
        assert 'TOP ' not in education
        assert 'credential.' not in education

    def test_education_lookup_locks_owner_subtype_and_parent_version_before_shared_guard(self):
        lookup = COMMAND[COMMAND.index("IF @RecordType = N'education'\n                    SELECT"):]
        lookup = lookup[:lookup.index("IF @RecordType = N'accomplishment'")]
        for required in ['dbo.career_chapters AS chapter WITH (UPDLOCK, HOLDLOCK)', 'dbo.career_education AS education WITH (UPDLOCK, HOLDLOCK)', 'education.owner_profile_id = chapter.owner_profile_id', 'chapter.owner_profile_id = @ProfileId', 'chapter.chapter_key = @RecordKey', "chapter.chapter_type = N'education'", 'chapter.deleted_at_utc IS NULL']:
            assert required in lookup
        assert COMMAND.index('IF @CurrentVersion <> @ExpectedVersion') < COMMAND.index('DECLARE @AffectedEntities')
        assert "IF @RecordType IN (N'role', N'credential', N'education') AND EXISTS" in COMMAND
        assert "IF @Operation = N'remove' AND @RecordType IN (N'role', N'credential', N'education')" in COMMAND
        assert "IF @RecordType IN (N'role',N'credential',N'education')" in COMMAND

    def test_entire_shared_dependency_guard_remains_identical(self):
        old_command = procedure_batches(OLD)['usp_CommitLivingResumeCommandForOwner'].replace("''", "'")

        def guard(source):
            start = source.index('                IF EXISTS\n                (\n                    SELECT 1 FROM @AffectedEntities')
            end = source.index("                IF @RecordType IN (N'role'", start)
            return source[start:end]
        assert guard(COMMAND) == guard(old_command)
        for table in ['entity_publication_versions', 'entity_access_grants', 'content_approval_events', 'career_achievements', 'career_timeline_events', 'slate_entity_relations', 'career_skill_links', 'evidence_links', 'ai_proposals']:
            assert 'dbo.' + table in guard(COMMAND)

    def test_education_changes_are_transactional_owner_scoped_and_receipt_digest_bound(self):
        assert 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE' in COMMAND
        assert 'SET XACT_ABORT ON' in COMMAND
        assert COMMAND.index('BEGIN TRANSACTION') < COMMAND.index('INSERT dbo.career_education')
        assert COMMAND.index('INSERT dbo.living_resume_command_receipts') > COMMAND.index('UPDATE dbo.career_education')
        assert 'receipt.owner_profile_id = @ProfileId' in COMMAND and 'receipt.command_id = @CommandId' in COMMAND
        assert 'IF @ExistingDigest <> @Digest' in COMMAND
        assert COMMAND.index('IF @ExistingDigest IS NOT NULL') < COMMAND.index('INSERT dbo.career_education')
        assert "HASHBYTES('SHA2_256'" in COMMAND
        assert COMMAND.count('WHERE chapter_id=@ChapterId AND owner_profile_id=@ProfileId AND row_version=@ExpectedVersion') >= 3
        assert 'IF XACT_STATE() <> 0 ROLLBACK TRANSACTION' in COMMAND
        education_update = COMMAND[COMMAND.index('UPDATE dbo.career_education'):]
        assert education_update.index('WHERE chapter_id=@ChapterId AND owner_profile_id=@ProfileId') < education_update.index('IF @@ROWCOUNT <> 1')

    def test_education_validation_does_not_truncate_or_invent_role_date_rules(self):
        start = COMMAND.index("IF @RecordType = N'education' AND @Operation <> N'remove'")
        validation = COMMAND[start:COMMAND.index("            IF @Operation = N'create'\n            BEGIN\n                IF EXISTS", start)]
        for field in ['title', 'institution_name', 'degree_name', 'field_of_study', 'grade_text', 'summary']:
            assert field + ' nvarchar(max)' in validation
        assert 'DATALENGTH(@EducationSummary)>16000' in validation
        assert 'DATALENGTH(@Grade)>200' in validation
        assert 'type NOT IN (0, 1)' in validation
        assert "N'approximate'" in validation
        assert '@EducationStart IS NOT NULL AND @EducationEnd IS NOT NULL' in validation
        assert 'current_role' not in validation

    def test_education_update_preserves_hidden_original_wording_even_for_null_summary(self):
        start = COMMAND.index("                    IF @RecordType = N'education'\n                    BEGIN")
        update = COMMAND[start:COMMAND.index("                    IF @RecordType = N'credential'", start)]
        assignments = update[update.index('SET title='):update.index('WHERE chapter_id=')]
        assert 'summary=@EducationSummary' in assignments
        assert 'original_member_wording' not in assignments
        create_start = COMMAND.index("                IF @RecordType = N'education'\n                BEGIN")
        create = COMMAND[create_start:COMMAND.index("                IF @RecordType = N'credential'", create_start)]
        assert 'summary, original_member_wording' in create
        assert '@EducationLocation, @EducationSummary, @EducationSummary' in create

    def test_both_forward_and_restored_procedures_have_balanced_sql_delimiters(self):
        for source in [FORWARD, ROLLBACK]:
            batches = procedure_batches(source)
            assert len(batches) == 2
            for body in batches.values():
                assert_balanced_sql_delimiters(unittest.TestCase(), body)
