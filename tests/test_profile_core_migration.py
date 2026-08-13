from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProfileMigrationTests(unittest.TestCase):
    def test_candidate_is_registered_dark_and_additive(self):
        registry = json.loads((ROOT / "SQL FIles/Migrations/registry.json").read_text(encoding="utf-8"))
        matches = [item for item in registry["migrations"] if item["id"] == "PS-PROFILE-002"]
        self.assertEqual(len(matches), 1)
        self.assertIsNone(matches[0]["gate"])
        self.assertEqual(matches[0]["requires"], ["PS-PLAT-002", "PS-PLAT-005", "PS-AUTH-001"])

    def test_forward_has_normalized_owner_and_audience_fences(self):
        sql = (ROOT / "SQL FIles/Migrations/proposed/PS-PROFILE-002_profile_publication.sql").read_text(encoding="utf-8")
        for table in ("profile_content_items", "profile_content_versions", "profile_projection_versions", "profile_publications", "profile_publication_revisions", "profile_publication_revision_items", "profile_draft_placements", "profile_slug_history"):
            self.assertIn(f"CREATE TABLE dbo.{table}", sql)
        self.assertIn("UQ_profile_publications_owner_audience", sql)
        self.assertIn("FK_profile_publication_revision_items_revision_owner", sql)
        self.assertNotIn("DROP TABLE", sql.upper())

    def test_draft_procedure_is_an_atomic_compare_and_swap(self):
        sql = (ROOT / "SQL FIles/Migrations/proposed/PS-PROFILE-002_profile_publication.sql").read_text(encoding="utf-8")
        start = sql.index("CREATE OR ALTER PROCEDURE dbo.usp_SaveProfileDraftForOwner")
        end = sql.index("CREATE OR ALTER PROCEDURE dbo.usp_CommitProfilePublicationForOwner")
        procedure = sql[start:end]
        for contract in (
            "@ExpectedDraftVersion",
            "sp_getapplock",
            "profile_drafts WITH(UPDLOCK,HOLDLOCK)",
            "@OwnerKey IS NULL",
            "@ProfileSlug IS NULL",
            "@DraftVersion IS NULL",
            "JSON_VALUE(@ManifestJson,''$.draft_key'') IS NULL",
            "JSON_VALUE(@ManifestJson,''$.owner_key'') COLLATE Latin1_General_100_BIN2<>@OwnerKey COLLATE Latin1_General_100_BIN2",
            "JSON_VALUE(@ManifestJson,''$.slug'') COLLATE Latin1_General_100_BIN2<>@ProfileSlug COLLATE Latin1_General_100_BIN2",
            "JSON_VALUE(@ManifestJson,''$.version'') COLLATE Latin1_General_100_BIN2<>@DraftVersion COLLATE Latin1_General_100_BIN2",
            "@ExpectedDraftVersion COLLATE Latin1_General_100_BIN2<>@CurrentDraftVersion COLLATE Latin1_General_100_BIN2",
            "@CurrentDraftKey COLLATE Latin1_General_100_BIN2<>JSON_VALUE(@ManifestJson,''$.draft_key'') COLLATE Latin1_General_100_BIN2",
            "SELECT CAST(0 AS bit) saved",
        ):
            self.assertIn(contract, procedure)
        self.assertNotIn("@ExpectedDraftVersion<>@CurrentDraftVersion", procedure)
        self.assertLess(procedure.index("WITH(UPDLOCK,HOLDLOCK)"), procedure.index("UPDATE dbo.profile_drafts"))
        self.assertLess(
            procedure.index("@ExpectedDraftVersion COLLATE Latin1_General_100_BIN2"),
            procedure.index("UPDATE dbo.profile_drafts"),
        )

    def test_publish_procedure_fences_reviewed_manifest_and_returns_sql_winner(self):
        sql = (ROOT / "SQL FIles/Migrations/proposed/PS-PROFILE-002_profile_publication.sql").read_text(encoding="utf-8")
        start = sql.index("CREATE OR ALTER PROCEDURE dbo.usp_CommitProfilePublicationForOwner")
        end = sql.index("CREATE OR ALTER PROCEDURE dbo.usp_GetProfileEligibleCommunityPostForOwner")
        procedure = sql[start:end]
        for contract in (
            "@ExpectedDraftKey", "@ExpectedDraftVersion", "@ExpectedDraftManifestJson",
            "dbo.profile_drafts WITH(UPDLOCK,HOLDLOCK)",
            "@CurrentDraftManifest COLLATE Latin1_General_100_BIN2<>@ExpectedDraftManifestJson COLLATE Latin1_General_100_BIN2",
            "@ManifestItemCount<>@DraftPlacementCount", "FULL JOIN OPENJSON",
            "@PublicationAction", "candidate_native", "content_kind", "source_metadata",
            "projection.source_version", "projection.revoked_at_utc",
            "body_json", "command.command_key", "revision.manifest_json",
        ):
            self.assertIn(contract, procedure)
        self.assertLess(procedure.index("@ExistingDigest IS NOT NULL"), procedure.index("@CurrentDraftManifest"))

    def test_publish_and_withdraw_action_fences_reject_before_any_publication_state_write(self):
        sql = (ROOT / "SQL FIles/Migrations/proposed/PS-PROFILE-002_profile_publication.sql").read_text(encoding="utf-8")
        start = sql.index("CREATE OR ALTER PROCEDURE dbo.usp_CommitProfilePublicationForOwner")
        end = sql.index("CREATE OR ALTER PROCEDURE dbo.usp_GetProfileEligibleCommunityPostForOwner")
        procedure = sql[start:end]
        self.assertNotIn("DECLARE @IsWithdrawal", procedure)
        self.assertIn("@PublicationAction=N''publish''", procedure)
        self.assertIn("@PublicationAction=N''withdraw''", procedure)
        self.assertIn("Latin1_General_100_BIN2", procedure)
        self.assertNotIn("ISNULL(item.content_kind", procedure)
        self.assertNotIn("ISNULL(item.source_metadata", procedure)
        self.assertLess(procedure.index("candidate_native"), procedure.index("INSERT dbo.profile_publications"))
        self.assertLess(procedure.index("source_metadata"), procedure.index("INSERT dbo.profile_publication_revisions"))

    def test_publish_manifest_comparisons_are_binary_and_null_exact_before_state_mutation(self):
        sql = (ROOT / "SQL FIles/Migrations/proposed/PS-PROFILE-002_profile_publication.sql").read_text(encoding="utf-8")
        start = sql.index("CREATE OR ALTER PROCEDURE dbo.usp_CommitProfilePublicationForOwner")
        end = sql.index("CREATE OR ALTER PROCEDURE dbo.usp_GetProfileEligibleCommunityPostForOwner")
        procedure = sql[start:end]
        for contract in (
            "@RevisionNumber IS NULL",
            "JSON_VALUE(@ManifestJson,''$.revision_number'') IS NULL",
            "candidate_native.value COLLATE Latin1_General_100_BIN2<>draft_native.value COLLATE Latin1_General_100_BIN2",
            "draft_item.placement_key COLLATE Latin1_General_100_BIN2=item.placement_key COLLATE Latin1_General_100_BIN2",
            "item.content_kind COLLATE Latin1_General_100_BIN2<>draft_item.content_kind COLLATE Latin1_General_100_BIN2",
            "item.destination COLLATE Latin1_General_100_BIN2<>draft_item.destination COLLATE Latin1_General_100_BIN2",
            "item.region COLLATE Latin1_General_100_BIN2<>draft_item.region COLLATE Latin1_General_100_BIN2",
            "item.source_key COLLATE Latin1_General_100_BIN2<>draft_item.source_key COLLATE Latin1_General_100_BIN2",
            "item.source_version COLLATE Latin1_General_100_BIN2<>draft_item.source_version COLLATE Latin1_General_100_BIN2",
            "item.source_metadata COLLATE Latin1_General_100_BIN2<>draft_item.source_metadata COLLATE Latin1_General_100_BIN2",
            "projection.approved_metadata_json COLLATE Latin1_General_100_BIN2<>item.source_metadata COLLATE Latin1_General_100_BIN2",
        ):
            self.assertIn(contract, procedure)
        self.assertIn("(candidate_native.value IS NULL AND draft_native.value IS NOT NULL)", procedure)
        self.assertIn("(item.content_kind IS NULL AND draft_item.content_kind IS NOT NULL)", procedure)
        self.assertNotIn("ISNULL(candidate_native.value", procedure)
        self.assertNotIn("ISNULL(item.content_kind", procedure)
        self.assertNotIn("ISNULL(item.source_metadata", procedure)
        self.assertLess(
            procedure.index("candidate_native.value COLLATE Latin1_General_100_BIN2"),
            procedure.index("INSERT dbo.profile_publications"),
        )
        self.assertLess(
            procedure.index("item.source_metadata COLLATE Latin1_General_100_BIN2"),
            procedure.index("INSERT dbo.profile_publication_revisions"),
        )

    def test_rollback_and_verifier_are_scoped(self):
        rollback = (ROOT / "SQL FIles/Migrations/proposed/PS-PROFILE-002_profile_publication_rollback.sql").read_text(encoding="utf-8")
        verify = (ROOT / "SQL FIles/Verification/PS-PROFILE-002_owner_isolation_verify.sql").read_text(encoding="utf-8")
        self.assertNotIn("member_profiles", rollback)
        self.assertIn("verified", verify)
        self.assertIn("owner fence", verify.lower())
        self.assertIn("Latin1_General_100_BIN2", verify)
        self.assertIn("Missing binary exact Profile manifest comparison fence.", verify)
        self.assertIn("Missing binary exact Profile draft manifest/CAS fence.", verify)


if __name__ == "__main__": unittest.main()
