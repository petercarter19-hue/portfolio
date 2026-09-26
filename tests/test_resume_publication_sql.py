"""Static contract checks for proposed publication and catalog SQL.

These tests do not claim SQL Server execution, race, rollback, permission,
or driver serialization proof. Registry gates stay null.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from services.database_service import ALLOWED_PROCEDURES
from services.resume_publication_repository import (
    PUBLICATION_BROWSER_PROCEDURES,
    PUBLICATION_INTERNAL_PROCEDURES,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
REGISTRY = ROOT / "SQL FIles" / "Migrations" / "registry.json"
PUBLICATION = MIGRATIONS / "PS-RESUME-PUBLICATION-001_publication.sql"
PUBLICATION_ROLLBACK = MIGRATIONS / "PS-RESUME-PUBLICATION-001_publication_rollback.sql"
PUBLICATION_VERIFY = ROOT / "SQL FIles" / "Verification" / "PS-RESUME-PUBLICATION-001_publication_verify.sql"
CATALOG = MIGRATIONS / "PS-RESUME-CATALOG-001_curated_catalog.sql"
CATALOG_ROLLBACK = MIGRATIONS / "PS-RESUME-CATALOG-001_curated_catalog_rollback.sql"
CATALOG_VERIFY = ROOT / "SQL FIles" / "Verification" / "PS-RESUME-CATALOG-001_curated_catalog_verify.sql"


class ResumePublicationSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.publication = PUBLICATION.read_text(encoding="utf-8")
        cls.publication_rollback = PUBLICATION_ROLLBACK.read_text(encoding="utf-8")
        cls.publication_verify = PUBLICATION_VERIFY.read_text(encoding="utf-8")
        cls.catalog = CATALOG.read_text(encoding="utf-8")
        cls.catalog_rollback = CATALOG_ROLLBACK.read_text(encoding="utf-8")
        cls.catalog_verify = CATALOG_VERIFY.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_both_draft_readers_preserve_the_shared_text_publication_token(self):
        for name in ("PS-RESUME-DRAFT-001_resume_drafts.sql", "PS-RESUME-MEDIA-001_resume_media.sql"):
            with self.subTest(migration=name):
                source = (MIGRATIONS / name).read_text(encoding="utf-8")
                self.assertRegex(source, r"DECLARE\s+@ReadBasePublicationVersion\s+nvarchar\(64\)\s*;")

    def test_registry_entries_are_proposed_with_null_gates(self):
        catalog = next(item for item in self.registry["migrations"] if item["id"] == "PS-RESUME-CATALOG-001")
        publication = next(item for item in self.registry["migrations"] if item["id"] == "PS-RESUME-PUBLICATION-001")
        self.assertIsNone(catalog["gate"])
        self.assertIsNone(publication["gate"])
        self.assertEqual(catalog["requires"], ["PS-RESUME-MEDIA-001"])
        self.assertEqual(
            publication["requires"],
            ["PS-RESUME-CATALOG-001", "PS-RESUME-DRAFT-001", "PS-ENTRY-POLICY-001"],
        )

    def test_procedure_calls_use_sql_server_supported_parameter_arguments(self):
        from services.resume_publication_adapters import resolve_publication_migration_closure
        for migration in resolve_publication_migration_closure():
            for kind in ("forward", "rollback"):
                source = (ROOT / migration[kind]).read_text(encoding="utf-8")
                for call in re.finditer(r"\bEXEC(?:UTE)?\s+dbo\.\w+\s+[^;]*;", source, re.I):
                    with self.subTest(migration=migration["id"], kind=kind, call=call.group(0)[:100]):
                        self.assertIsNone(re.search(r"@\w+\s*=\s*\w+\s*\(", call.group(0)))

    def test_complete_command_is_serializable_owner_keyed_and_closed(self):
        source = self.publication
        self.assertIn("PROPOSED ONLY", source)
        self.assertIn("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", source)
        self.assertIn("SET XACT_ABORT ON", source)
        self.assertIn("Ambient transactions are not permitted", source)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", source)
        self.assertIn("@UserKey nvarchar(300)", source)
        self.assertNotIn("@UserKey uniqueidentifier", source)
        self.assertNotIn("@OwnerProfileId", source)
        self.assertIn("usp_CommitResumePublicationCommandForOwner", source)
        self.assertIn("usp_GetPublicResumePublicationBySlug", source)
        self.assertIn("usp_GetResumePublicationReceiptForOwner", source)
        self.assertIn("usp_GetResumePublicationMediaAuthorization", source)
        self.assertIn("resume-canonical-source.v1", source)
        self.assertIn("Latin1_General_100_BIN2_UTF8", source)
        self.assertIn("INSERT dbo.resume_publication_evidence", source)
        self.assertIn("HASHBYTES", source)
        self.assertIn("display_json", source)
        self.assertIn("visitor_ai_json", source)
        self.assertIn("entry_policy_records", source)
        self.assertIn("resume_drafts", source)
        self.assertIn("N''sharing_off''", source)
        self.assertIn("N''restore''", source)
        self.assertIn("N''create''", source)
        self.assertIn("N''edit''", source)
        self.assertIn("N''recategorize''", source)
        self.assertIn("N''permanently_delete''", source)
        self.assertIn("N''resolve_match''", source)
        self.assertIn("COALESCE(TRY_CONVERT(bit, JSON_VALUE(target.permissions, ''$.visitor_ai''))", source)
        self.assertIn("approved_wording", source)
        self.assertIn("CONVERT(varbinary(max), submitted.submitted_summary)", source)
        self.assertIn("CONVERT(varbinary(max), submitted.submitted_wording)", source)
        self.assertIn("CONVERT(varbinary(max), submitted.displayed_wording)", source)
        self.assertIn("DATALENGTH(submitted.submitted_summary) <> DATALENGTH(submitted.displayed_wording)", source)
        self.assertIn("DATALENGTH(submitted.submitted_wording) <> DATALENGTH(submitted.displayed_wording)", source)
        self.assertIn("usp_CommitEntryPolicyCommandForOwnerCore", source)
        self.assertIn("usp_ResumePublicationGuardLegacyMutator", source)
        self.assertIn("DENY EXECUTE", source)
        self.assertIn("resume_media_placements", source)
        self.assertIn("resume_catalog_assets", source)
        self.assertIn("EXEC dbo.usp_ResumePublicationEncodeSourceInternal", source)
        self.assertNotIn("CHARINDEX(@Slot", source)
        self.assertNotIn("CHARINDEX(@RecordKey", source)
        self.assertNotIn("fields_by_entry", source)
        self.assertIsNone(re.search(r"(?mi)^[ \t]*GO[ \t]*$", source))
        self.assertIn("media_json", source[source.index("CREATE OR ALTER PROCEDURE dbo.usp_GetResumePublicationForOwner"):])

    def test_entry_policy_wrapper_skips_projection_when_core_reports_replay(self):
        source = self.publication
        start = source.rindex("CREATE OR ALTER PROCEDURE dbo.usp_CommitEntryPolicyCommandForOwner")
        end = source.index("usp_CommitResumeDraftCommandForOwnerCore", start)
        wrapper = source[start:end]
        self.assertIn("usp_CommitEntryPolicyCommandForOwnerCore", wrapper)
        self.assertIn("@CoreReplayed", wrapper)
        replay_gate = wrapper.index("IF @CoreReplayed = 1")
        apply_call = wrapper.index("usp_ResumePublicationApplyAfterPolicyInternal")
        self.assertLess(replay_gate, apply_call)
        skip = wrapper[replay_gate:apply_call]
        self.assertIn("RETURN", skip)

    def test_owner_get_returns_current_revision_media_json(self):
        source = self.publication
        start = source.index("CREATE OR ALTER PROCEDURE dbo.usp_GetResumePublicationForOwner")
        end = source.index("CREATE OR ALTER PROCEDURE dbo.usp_GetPublicResumePublicationBySlug")
        getter = source[start:end]
        self.assertIn("media_json", getter)
        self.assertIn("resume_publication_revisions", getter)

    def test_after_policy_wrapper_rebuilds_from_committed_rows_with_real_digest(self):
        source = self.publication
        start = source.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyAfterPolicyInternal")
        end = source.index("CREATE OR ALTER PROCEDURE dbo.usp_CommitResumePublicationCommandForOwner")
        wrapper = source[start:end]
        self.assertNotIn("usp_ResumePublicationApplyCanonicalInternal", wrapper)
        self.assertNotIn("0" * 64, wrapper)
        self.assertIn("HASHBYTES", wrapper)
        self.assertIn("usp_ResumePublicationBuildManifestsInternal", wrapper)

    def test_injected_failure_is_after_evidence_insert(self):
        source = self.publication
        start = source.index("INSERT dbo.resume_publication_evidence")
        region = source[start : start + 800]
        self.assertIn("PROOF_INJECTED_FAILURE", region)
        self.assertLess(
            region.index("INSERT dbo.resume_publication_evidence"),
            region.index("PROOF_INJECTED_FAILURE"),
        )

    def test_publication_correct_and_my_data_edit_use_apply_canonical_not_core(self):
        source = self.publication
        start = source.index("CREATE OR ALTER PROCEDURE dbo.usp_CommitResumePublicationCommandForOwner")
        command = source[start:]
        marker = command.index("IF @Type IN (N''edit'', N''correct'', N''change_permissions'')")
        region = command[marker : marker + 500]
        self.assertIn("usp_ResumePublicationApplyCanonicalInternal", region)
        before_else = region.split("ELSE IF", 1)[0]
        self.assertNotIn("usp_CommitEntryPolicyCommandForOwnerCore", before_else)
        apply = source[
            source.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyCanonicalInternal") : source.index(
                "CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationRefreshProjectionInternal"
            )
        ]
        self.assertIn("N''correct''", apply)
        self.assertIn("UPDLOCK, HOLDLOCK", apply)
        self.assertLess(apply.index("UPDLOCK, HOLDLOCK"), apply.index("UPDATE chapter"))
        self.assertIn("54026", apply)
        self.assertIn("54027", apply)
        self.assertIn("54028", apply)
        self.assertIn("54029", apply)
        self.assertIn("expected_content_version", apply)
        self.assertIn("expected_access_revision", apply)
        self.assertIn("@@ROWCOUNT", apply)

    def test_my_data_sql_wrapper_routes_normalized_permission_batch_without_rewriting_it(self):
        source = self.publication
        wrapper = source[source.index("CREATE OR ALTER PROCEDURE dbo.usp_CommitEntryPolicyCommandForOwner\n"):]
        self.assertLess(wrapper.index("IF @Type IN (N''edit'', N''change_permissions'')"),
                        wrapper.index("BEGIN TRANSACTION;"))
        self.assertNotIn("$.targets[0]", wrapper)
        self.assertNotIn("Unsupported multi-entry permission command", wrapper)
        self.assertIn("EXEC dbo.usp_CommitResumePublicationCommandForOwner", wrapper)
        apply = source[source.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyCanonicalInternal"):
                       source.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationRefreshProjectionInternal")]
        permission_batch = apply[apply.index("IF @Type = N''change_permissions''"):apply.index("IF @Type = N''delete''")]
        self.assertIn("FROM OPENJSON(@TargetsJson)", permission_batch)
        self.assertIn("GROUP BY entry_key HAVING COUNT(*) > 1", permission_batch)
        self.assertLess(permission_batch.index("IF EXISTS (\n            SELECT 1 FROM @PermissionTargets AS target"),
                        permission_batch.index("UPDATE policy"))
        self.assertIn("IF @@ROWCOUNT <> @TargetCount", permission_batch)
        self.assertIn("usp_ListEntryPolicyEntriesForOwnerCore", wrapper)
        self.assertIn("usp_GetEntryPolicyEntryForOwnerCore", wrapper)
        self.assertIn("EXEC dbo.usp_ListResumePublicationPolicyForOwner @UserKey = @UserKey", wrapper)
        self.assertIn("values_json", wrapper)

    def test_decoded_permission_target_predicate_has_balanced_parentheses(self):
        apply = self.publication[
            self.publication.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyCanonicalInternal"):
            self.publication.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationRefreshProjectionInternal")
        ].replace("''", "'")
        predicate = apply[
            apply.index("IF @TargetCount = 0 OR EXISTS ("):
            apply.index("THROW 54061", apply.index("IF @TargetCount = 0 OR EXISTS ("))
        ]
        without_literals = re.sub(r"N?'(?:''|[^'])*'", "''", predicate)
        depth = 0
        for character in without_literals:
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                self.assertGreaterEqual(depth, 0)
        self.assertEqual(depth, 0)

    def test_canonical_writes_cover_education_credential_skill_and_achievement(self):
        source = self.publication
        start = source.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyCanonicalInternal")
        end = source.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationRefreshProjectionInternal")
        apply = source[start:end]
        self.assertIn("dbo.career_education", apply)
        self.assertIn("dbo.career_credentials", apply)
        self.assertIn("dbo.career_skills", apply)
        self.assertIn("dbo.career_achievements", apply)
        self.assertIn("dbo.career_projects", apply)

    def test_build_manifests_fails_closed_without_command_json_fallback(self):
        source = self.publication
        start = source.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationBuildManifestsInternal")
        end = source.index("CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationGuardLegacyMutator")
        builder = source[start:end]
        self.assertNotIn("fields_by_entry", builder)
        self.assertIn("Canonical source is unavailable.", builder)
        self.assertIn("dbo.career_education", builder)
        self.assertIn("dbo.career_skills", builder)

    def test_rollback_restores_entry_policy_and_legacy_cores(self):
        rollback = self.publication_rollback
        self.assertIn("usp_CommitEntryPolicyCommandForOwnerCore", rollback)
        self.assertIn("usp_ListEntryPolicyEntriesForOwnerCore", rollback)
        self.assertIn("usp_GetEntryPolicyEntryForOwnerCore", rollback)
        self.assertIn("usp_CommitResumeDraftCommandForOwnerCore", rollback)
        self.assertIn("usp_CommitResumeMediaCommandForOwnerCore", rollback)
        self.assertIn("usp_CommitResumeIntakeCommandForOwnerCore", rollback)
        self.assertIn("sp_rename", rollback)
        self.assertIn("resume_publication_core_execute_permissions", self.publication)
        self.assertIn("resume_publication_core_execute_permissions", self.publication_verify)
        self.assertIn("permission_record.grantee_principal_id = DATABASE_PRINCIPAL_ID(N'public')", self.publication)
        self.assertIn("REVOKE EXECUTE ON OBJECT::dbo.", rollback)
        self.assertIn("GRANT EXECUTE ON OBJECT::dbo.", rollback)
        self.assertIn("DENY EXECUTE ON OBJECT::dbo.", rollback)
        self.assertLess(rollback.index("Rollback refused: publication state is populated."),
                        rollback.index("DROP PROCEDURE dbo.usp_CommitResumePublicationCommandForOwner"))

    def test_catalog_fence_is_closed_and_internal_helper_is_denied(self):
        self.assertIn("PROPOSED ONLY", self.catalog)
        self.assertIn("usp_CommitResumeCatalogCommandForOwner", self.catalog)
        self.assertIn("usp_GetResumeCatalogAsset", self.catalog)
        self.assertIn("usp_ResumeCatalogApplyInternal", self.catalog)
        self.assertIn("DENY EXECUTE ON dbo.usp_ResumeCatalogApplyInternal", self.catalog)
        self.assertIn("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", self.catalog)
        self.assertIn("Ambient transactions are not permitted", self.catalog)

    def test_rollback_and_verify_are_structural_only(self):
        self.assertIn("PS-RESUME-PUBLICATION-001", self.publication_rollback)
        self.assertIn("PS-RESUME-CATALOG-001", self.catalog_rollback)
        self.assertIn("verified", self.publication_verify)
        self.assertIn("runtime proof remains outstanding", self.publication_verify)
        self.assertIn("verified", self.catalog_verify)
        self.assertIn("runtime proof remains outstanding", self.catalog_verify)

    def test_browser_procedures_are_allowlisted_and_internals_are_not(self):
        for name in PUBLICATION_BROWSER_PROCEDURES:
            self.assertIn(name, ALLOWED_PROCEDURES)
        for name in PUBLICATION_INTERNAL_PROCEDURES:
            self.assertNotIn(name, ALLOWED_PROCEDURES)
            self.assertIn(name, self.publication)


if __name__ == "__main__":
    unittest.main()
