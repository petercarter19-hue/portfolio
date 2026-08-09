import importlib.util
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_sql_authority():
    path = ROOT / "scripts" / "configure_community_maintenance_sql_authority.py"
    spec = importlib.util.spec_from_file_location("community_sql_authority", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CommunityScheduledMaintenanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = (ROOT / "azure-pipelines.yml").read_text(encoding="utf-8")

    def test_hourly_schedule_is_main_only_and_non_overlapping(self):
        self.assertIn("cron: '17 * * * *'", self.pipeline)
        self.assertIn("displayName: Community maintenance hourly", self.pipeline)
        schedule = self.pipeline.split("schedules:", 1)[1].split("parameters:", 1)[0]
        self.assertIn("- main", schedule)
        self.assertIn("always: true", schedule)
        self.assertIn("batch: true", schedule)

    def test_scheduled_runs_skip_the_deploy_build_path(self):
        build = self.pipeline.split("- stage: Build", 1)[1].split(
            "- stage: ProductionWebDeploy", 1
        )[0]
        # The split must actually bound the Build stage. `str.split` on a
        # missing separator returns the whole remainder, so a stage rename
        # would silently widen this to the entire file and the assertion
        # below would keep passing while testing nothing.
        self.assertNotIn("- stage: ", build)
        self.assertIn("ne(variables['Build.Reason'], 'Schedule')", build)
        maintenance = self.pipeline.split("- stage: CommunityMaintenance", 1)[1]
        self.assertIn("dependsOn: []", maintenance)
        self.assertIn("eq(variables['Build.Reason'], 'Schedule')", maintenance)
        self.assertIn("eq(variables['Build.SourceBranch'], 'refs/heads/main')", maintenance)

    def test_visibility_and_maintenance_flags_are_independent(self):
        maintenance = self.pipeline.split("- stage: CommunityMaintenance", 1)[1]
        self.assertIn("PEERSLATE_COMMUNITY_MAINTENANCE_ENABLED", maintenance)
        self.assertNotIn("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED", maintenance)

    def test_scheduler_uses_a_dedicated_workload_identity(self):
        maintenance = self.pipeline.split("- stage: CommunityMaintenance", 1)[1]
        self.assertNotIn("azureSubscription: $(azureServiceConnectionId)", maintenance)
        self.assertNotIn("AZURE_SQL_CONNECTIONSTRING: $(schemaConnectionString)", maintenance)
        self.assertIn(
            "azureSubscription: $(communityMaintenanceServiceConnectionId)",
            maintenance,
        )
        self.assertIn(
            "AZURE_SQL_CONNECTIONSTRING: $(communityMaintenanceSqlConnectionString)",
            maintenance,
        )
        self.assertIn("scripts/run_community_maintenance.py", maintenance)
        self.assertIn("configure_community_maintenance_sql_authority.py verify", maintenance)
        self.assertIn("communityMaintenancePrincipalClientId", maintenance)
        self.assertNotIn("provision_community_maintenance_blob_access.ps1", maintenance)
        self.assertIn("CommunityMaintenanceEvidence", maintenance)
        self.assertIn('--expect-database "$(schemaDatabaseName)"', maintenance)
        self.assertIn("Record independently disabled maintenance", maintenance)
        disabled = maintenance.split(
            "displayName: Record independently disabled maintenance", 1
        )[1].split("- task: AzureCLI@2", 1)[0]
        self.assertIn(
            "ne(variables['communityMaintenanceEnabled'], 'true')", disabled
        )
        self.assertNotIn("azureSubscription:", disabled)

    def test_web_deploy_waits_for_the_exact_additive_schema(self):
        self.assertIn("- job: VerifyCommunitySchemaBeforeDeploy", self.pipeline)
        deploy = self.pipeline.split("- deployment: DeployWebApp", 1)[1]
        self.assertIn("VerifyCommunitySchemaBeforeDeploy", deploy)
        gate = self.pipeline.split("- job: VerifyCommunitySchemaBeforeDeploy", 1)[1]
        gate = gate.split("- deployment: DeployWebApp", 1)[0]
        self.assertIn("scripts/verify_community_release_schema.py", gate)
        self.assertIn("AZURE_SQL_CONNECTIONSTRING: $(schemaConnectionString)", gate)

    def test_maintenance_authority_is_narrow_and_separately_verified(self):
        sql_authority = (
            ROOT / "scripts" / "configure_community_maintenance_sql_authority.py"
        ).read_text(encoding="utf-8")
        blob_authority = (
            ROOT / "scripts" / "provision_community_maintenance_blob_access.ps1"
        ).read_text(encoding="utf-8")
        for procedure in (
            "usp_ClaimPublicCommunityMediaCleanup",
            "usp_CompletePublicCommunityMediaCleanup",
            "usp_PurgeCommunityContent",
            "usp_PurgeCommunityAuditEvents",
            "usp_PurgeCommunityOutbox",
        ):
            self.assertIn(procedure, sql_authority)
        self.assertNotIn("usp_ClaimPublicCommunityMediaCleanupForOwner\"", sql_authority)
        self.assertIn("Storage Blob Data Contributor", blob_authority)
        self.assertNotIn("Storage Blob Data Owner", blob_authority)
        self.assertIn("blobServices/default/containers", blob_authority)
        self.assertIn("peerslate-community-maintenance", sql_authority)
        self.assertNotIn("peerslate-ado-schema", sql_authority)
        self.assertIn("if cursor.fetchall():", sql_authority)
        self.assertIn("direct_permissions != expected_direct", sql_authority)
        self.assertIn("effective_objects != expected_objects", sql_authority)
        self.assertIn("--include-inherited", blob_authority)
        self.assertIn("transitiveMemberOf/microsoft.graph.group", blob_authority)
        self.assertNotIn("get-member-groups", blob_authority)
        self.assertIn('"role", "assignment", "delete"', blob_authority)

    def test_blob_authority_uses_an_executable_graph_contract(self):
        if not shutil.which("pwsh"):
            self.skipTest("PowerShell is unavailable")
        script = ROOT / "scripts" / "provision_community_maintenance_blob_access.ps1"
        subscription = "00000000-0000-0000-0000-000000000001"
        scope = (
            f"/subscriptions/{subscription}/resourceGroups/peerslate/providers/"
            "Microsoft.Storage/storageAccounts/peerslatecapturemedia/blobServices/"
            "default/containers/peerslate-private-capture-media"
        )
        assignment_id = (
            f"{scope}/providers/Microsoft.Authorization/roleAssignments/"
            "0a1c352c-8847-4a3a-8d68-b1c10196ec76"
        )
        command = rf"""
        $global:Calls = @()
        function global:az {{
            $Line = $args -join ' '
            $global:Calls += $Line
            $global:LASTEXITCODE = 0
            if ($Line -like 'account show*') {{ '{subscription}' }}
            elseif ($Line -like 'rest *') {{ '[]' }}
            elseif ($Line -like 'role assignment list*') {{
                '[{{"id":"{assignment_id}","role":"Storage Blob Data Contributor","scope":"{scope}"}}]'
            }}
            else {{ throw "Unexpected Azure CLI call" }}
        }}
        & '{script}' -Mode verify `
            -PrincipalObjectId '11111111-2222-3333-4444-555555555555' `
            -StorageAccountName 'peerslatecapturemedia' `
            -ContainerName 'peerslate-private-capture-media'
        $global:Calls | ConvertTo-Json -Compress
        """
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("rest --method GET", result.stdout)
        self.assertNotIn("get-member-groups", result.stdout)

    def test_blob_apply_compensates_an_exact_new_role_on_postcheck_failure(self):
        if not shutil.which("pwsh"):
            self.skipTest("PowerShell is unavailable")
        script = ROOT / "scripts" / "provision_community_maintenance_blob_access.ps1"
        subscription = "00000000-0000-0000-0000-000000000001"
        scope = (
            f"/subscriptions/{subscription}/resourceGroups/peerslate/providers/"
            "Microsoft.Storage/storageAccounts/peerslatecapturemedia/blobServices/"
            "default/containers/peerslate-private-capture-media"
        )
        assignment_id = (
            f"{scope}/providers/Microsoft.Authorization/roleAssignments/"
            "0a1c352c-8847-4a3a-8d68-b1c10196ec76"
        )
        command = rf"""
        $global:Calls = @()
        $global:Lists = 0
        function global:az {{
            $Line = $args -join ' '
            $global:Calls += $Line
            $global:LASTEXITCODE = 0
            if ($Line -like 'account show*') {{ '{subscription}' }}
            elseif ($Line -like 'rest *') {{ '[]' }}
            elseif ($Line -like 'role assignment list*') {{
                $global:Lists += 1
                if ($global:Lists -eq 1) {{ '[]' }}
                else {{
                    '[{{"id":"{assignment_id}","role":"Contributor","scope":"{scope}"}}]'
                }}
            }}
            elseif ($Line -like 'role assignment create*') {{ '' }}
            elseif ($Line -like 'role assignment delete*') {{ '' }}
            else {{ throw "Unexpected Azure CLI call" }}
        }}
        try {{
            & '{script}' -Mode apply -ConfirmApply `
                -PrincipalObjectId '11111111-2222-3333-4444-555555555555' `
                -StorageAccountName 'peerslatecapturemedia' `
                -ContainerName 'peerslate-private-capture-media'
            exit 2
        }}
        catch {{
            $global:Calls | ConvertTo-Json -Compress
            exit 7
        }}
        """
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertIn("role assignment create", result.stdout)
        self.assertIn("role assignment delete --ids", result.stdout)
        self.assertIn(assignment_id, result.stdout)

    def test_scheduler_uses_pipeline_metadata_without_reading_app_settings(self):
        maintenance = self.pipeline.split("- stage: CommunityMaintenance", 1)[1]
        self.assertNotIn("az webapp config appsettings list", maintenance)
        self.assertIn(
            "PEERSLATE_COMMUNITY_MAINTENANCE_ENABLED: $(communityMaintenanceEnabled)",
            maintenance,
        )
        self.assertIn(
            "CAPTURE_MEDIA_BLOB_ACCOUNT_URL: $(communityMediaBlobAccountUrl)",
            maintenance,
        )
        self.assertIn(
            "CAPTURE_MEDIA_BLOB_CONTAINER: $(communityMediaBlobContainer)",
            maintenance,
        )


class CommunitySqlAuthorizationTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = load_sql_authority()

    class Connection:
        def __init__(self, events):
            self.events = events
            self.cursor_value = object()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return self.cursor_value

        def commit(self):
            self.events.append("commit")

        def rollback(self):
            self.events.append("rollback")

    def _arguments(self):
        return [
            "apply",
            "--principal-client-id",
            "11111111-2222-3333-4444-555555555555",
            "--confirm-apply",
        ]

    def test_apply_verifies_before_commit(self):
        events = []
        connection = self.Connection(events)

        def applied(*_):
            events.append("apply")

        def verified(*_, **keywords):
            self.assertTrue(keywords["allow_impersonation"])
            events.append("verify")

        with mock.patch.object(
            self.authority, "_connection", return_value=connection
        ), mock.patch.object(
            self.authority, "apply", side_effect=applied
        ), mock.patch.object(
            self.authority, "verify", side_effect=verified
        ):
            self.assertEqual(self.authority.main(self._arguments()), 0)

        self.assertEqual(events, ["apply", "verify", "commit"])

    def test_failed_verification_rolls_back_and_never_commits(self):
        events = []
        connection = self.Connection(events)
        with mock.patch.object(
            self.authority, "_connection", return_value=connection
        ), mock.patch.object(
            self.authority, "apply", side_effect=lambda *_: events.append("apply")
        ), mock.patch.object(
            self.authority,
            "verify",
            side_effect=RuntimeError("must not commit"),
        ):
            self.assertEqual(self.authority.main(self._arguments()), 1)

        self.assertEqual(events, ["apply", "rollback"])

    def test_scheduled_verify_rejects_a_broad_active_identity(self):
        authority = self.authority
        principal_sid = authority._client_sid(
            "11111111-2222-3333-4444-555555555555"
        )

        class Cursor:
            description = None

            def execute(self, statement):
                self.statement = statement
                if "SELECT DB_NAME()" in statement:
                    self.description = [
                        ("database_name",),
                        ("principal_type",),
                        ("principal_sid",),
                        ("procedures_present",),
                    ]
                elif "SELECT USER_NAME()" in statement:
                    self.description = [("current_principal",)]
                else:
                    self.description = [("value",)]

            def fetchone(self):
                if "SELECT DB_NAME()" in self.statement:
                    return (
                        "peerslate-database",
                        "EXTERNAL_USER",
                        principal_sid,
                        1,
                    )
                if "SELECT USER_NAME()" in self.statement:
                    return ("peerslate-ado-schema",)
                raise AssertionError("Unexpected scalar query")

            def fetchall(self):
                if "database_role_members" in self.statement:
                    return []
                if "database_permissions" in self.statement:
                    return [
                        ("DATABASE", "CONNECT", "GRANT", None, None),
                        *[
                            (
                                "OBJECT_OR_COLUMN",
                                "EXECUTE",
                                "GRANT",
                                "dbo",
                                procedure,
                            )
                            for procedure in authority.REQUIRED_PROCEDURES
                        ],
                    ]
                raise AssertionError("Unexpected rowset query")

            def nextset(self):
                return False

        with mock.patch.object(authority, "_verify_effective_permissions"):
            with self.assertRaisesRegex(RuntimeError, "Active maintenance SQL"):
                authority.verify(Cursor(), "peerslate-database", principal_sid)


class CommunityAdditiveMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migration_dir = ROOT / "SQL FIles" / "Migrations"
        cls.forward = (
            migration_dir / "PS-COMMUNITY-REVIVAL-001_maintenance.sql"
        ).read_text(encoding="utf-8")
        cls.rollback = (
            migration_dir / "PS-COMMUNITY-REVIVAL-001_maintenance_rollback.sql"
        ).read_text(encoding="utf-8")
        cls.verifier = (
            ROOT
            / "SQL FIles"
            / "Verification"
            / "PS-COMMUNITY-REVIVAL-001_verify.sql"
        ).read_text(encoding="utf-8")

    def test_new_id_never_replays_the_applied_community_ids(self):
        self.assertIn("migration_id = N'PS-COMMUNITY-REVIVAL-001'", self.forward)
        self.assertNotIn("INSERT dbo.schema_migrations (migration_id", self.forward)
        self.assertIn("CREATE OR ALTER PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanupForOwner", self.forward)

    def test_owner_identity_is_resolved_and_applied_in_sql(self):
        self.assertIn("WHERE user_key = @UserKey", self.forward)
        self.assertIn("media.uploader_user_id = @UploaderUserId", self.forward)
        self.assertIn("sys.parameters", self.verifier)
        self.assertIn("name = N'@UploaderUserId'", self.verifier)

    def test_rollback_drops_only_the_new_procedure(self):
        self.assertIn("DROP PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanupForOwner", self.rollback)
        self.assertNotIn("DROP TABLE", self.rollback)
        self.assertNotIn("DELETE dbo.community_media", self.rollback)

    def test_verifier_proves_cross_owner_refusal_and_rolls_back(self):
        self.assertIn("@UserKey = @UserKeyA", self.verifier)
        self.assertIn("@MediaKey = @MediaKeyB", self.verifier)
        self.assertIn("ROLLBACK TRANSACTION", self.verifier)
        self.assertIn("verified", self.verifier)


if __name__ == "__main__":
    unittest.main()
