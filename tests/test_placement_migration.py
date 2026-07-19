from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
import re
import threading
import time
import unittest
import uuid
from pathlib import Path

from mssql_python import connect


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
RUNNER = ROOT / "scripts" / "apply_sql_migrations.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("placement_migrations", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dynamic_procedure_batches(sql):
    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    return {
        match.group(1): batch
        for batch in batches
        if (match := re.search(r"PROCEDURE dbo\.(usp_[A-Za-z0-9_]+)", batch))
    }


def fetch_nonempty_result_sets(cursor):
    result_sets = []
    while True:
        if cursor.description is not None:
            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            if rows:
                result_sets.append(rows)
        if not cursor.nextset():
            return result_sets


class PlacementMigrationTests(unittest.TestCase):
    def setUp(self):
        self.forward = MIGRATIONS / "PS-PLACEMENT-001_moment_placements.sql"
        self.rollback = (
            MIGRATIONS / "PS-PLACEMENT-001_moment_placements_rollback.sql"
        )
        self.verification = (
            VERIFICATION / "PS-PLACEMENT-001_owner_isolation_verify.sql"
        )

    def test_forward_rollback_and_real_verification_exist(self):
        self.assertTrue(self.forward.exists())
        self.assertTrue(self.rollback.exists())
        self.assertTrue(self.verification.exists())

    def test_forward_requires_moment_destination_and_tenant_foundations(self):
        sql = self.forward.read_text(encoding="utf-8")

        self.assertIn("PS-PLAT-002", sql)
        self.assertIn("PS-PLAT-005", sql)
        self.assertIn("PS-MOMENT-001", sql)
        self.assertIn("dbo.moment_versions", sql)
        self.assertIn("dbo.moment_sources", sql)
        self.assertIn("dbo.slate_entities", sql)
        self.assertIn("dbo.audit_events", sql)
        self.assertIn("SET XACT_ABORT ON", sql)
        self.assertIn("BEGIN TRANSACTION", sql)
        self.assertIn("COMMIT TRANSACTION", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)
        self.assertIn("migration_id = N'PS-PLACEMENT-001'", sql)

    def test_body_free_reference_model_uses_exact_tenant_safe_keys(self):
        sql = self.forward.read_text(encoding="utf-8")
        table = sql.split("CREATE TABLE dbo.moment_placements", 1)[1].split(
            "CREATE INDEX IX_moment_placements_owner_status", 1
        )[0]

        self.assertIn("UQ_moment_placements_logical", table)
        self.assertIn("owner_profile_id", table)
        self.assertIn("moment_id", table)
        self.assertIn("moment_version_number", table)
        self.assertIn("target_entity_id", table)
        self.assertIn("placement_status IN (N'active', N'removed')", table)
        self.assertIn("row_version rowversion NOT NULL", table)
        self.assertIn("FK_moment_placements_moment_owner", table)
        self.assertIn("REFERENCES dbo.moments(moment_id, owner_profile_id)", table)
        self.assertIn("FK_moment_placements_exact_version", table)
        self.assertIn(
            "REFERENCES dbo.moment_versions(moment_id, version_number)", table
        )
        self.assertIn("FK_moment_placements_target_owner", table)
        self.assertIn(
            "REFERENCES dbo.slate_entities(entity_id, owner_profile_id)", table
        )

        forbidden_fields = (
            " body ",
            " title ",
            " narrative ",
            " why_it_matters ",
            " content ",
            " label ",
            " audience ",
            " prompt ",
            " completion ",
            " snapshot_json ",
            " metadata_json ",
            " nvarchar(max)",
        )
        normalized = f" {table.lower()} "
        for field in forbidden_fields:
            self.assertNotIn(field, normalized)

    def test_create_list_remove_procedures_are_owner_resolving_and_narrow(self):
        sql = self.forward.read_text(encoding="utf-8")
        batches = dynamic_procedure_batches(sql)

        self.assertEqual(
            set(batches),
            {
                "usp_CreateOrReactivateMomentPlacement",
                "usp_ListMomentPlacementsForOwner",
                "usp_RemoveMomentPlacement",
            },
        )
        for procedure in batches.values():
            self.assertIn("@UserKey nvarchar(300)", procedure)
            self.assertNotIn("@OwnerProfileId", procedure)

        create = batches["usp_CreateOrReactivateMomentPlacement"]
        self.assertIn("moment.owner_profile_id = @ProfileId", create)
        self.assertIn("target.owner_profile_id = @ProfileId", create)
        self.assertIn("@MomentStatus <> N''confirmed''", create)
        self.assertIn("moment.visibility", create)
        self.assertIn("@ExpectedMomentRowVersion binary(8)", create)
        self.assertIn("@ExpectedPlacementRowVersion binary(8) = NULL", create)
        self.assertIn("moment.row_version", create)
        self.assertIn("target.visibility", create)
        self.assertIn("target.approval_status", create)
        self.assertIn("target.publication_status", create)
        self.assertIn("target.active", create)
        self.assertIn("target.deleted_at_utc", create)
        self.assertIn("N''target_unavailable'' AS outcome", create)
        self.assertIn("N''created'' AS outcome", create)
        self.assertIn("N''reactivated'' AS outcome", create)
        self.assertIn("N''existing'' AS outcome", create)
        self.assertIn("N''stale'' AS outcome", create)

        listing = batches["usp_ListMomentPlacementsForOwner"]
        self.assertIn("placement.owner_profile_id = @ProfileId", listing)
        self.assertIn("target_available", listing)
        self.assertNotIn("version_record.title", listing)
        self.assertNotIn("version_record.narrative", listing)
        self.assertNotIn("capture.body", listing)
        self.assertNotIn("snapshot_json", listing)

        remove = batches["usp_RemoveMomentPlacement"]
        self.assertIn("placement.owner_profile_id = @ProfileId", remove)
        self.assertIn("placement.row_version", remove)
        self.assertIn("N''already_removed'' AS outcome", remove)
        self.assertIn("N''removed'' AS outcome", remove)

    def test_concurrency_contract_serializes_duplicates_and_preserves_one_row(self):
        sql = self.forward.read_text(encoding="utf-8")
        create = dynamic_procedure_batches(sql)[
            "usp_CreateOrReactivateMomentPlacement"
        ]

        self.assertIn("UQ_moment_placements_logical", sql)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", create)
        self.assertIn(
            "WITH (UPDLOCK, HOLDLOCK, INDEX(UQ_moment_placements_logical))",
            create,
        )
        self.assertLess(
            create.index("FROM dbo.moments AS moment WITH (UPDLOCK, HOLDLOCK)"),
            create.index("FROM dbo.slate_entities AS target WITH (UPDLOCK, HOLDLOCK)"),
        )
        self.assertLess(
            create.index("FROM dbo.slate_entities AS target WITH (UPDLOCK, HOLDLOCK)"),
            create.index("FROM dbo.moment_placements AS placement"),
        )
        self.assertEqual(create.count("moment.placement.created"), 1)
        self.assertEqual(create.count("moment.placement.reactivated"), 1)

    def test_placement_procedures_do_not_write_downstream_or_copy_content(self):
        sql = self.forward.read_text(encoding="utf-8")
        batches = dynamic_procedure_batches(sql)
        procedures = "\n".join(batches.values())

        forbidden_writes = (
            "INSERT dbo.slate_entities",
            "UPDATE dbo.slate_entities",
            "INSERT dbo.slate_entity_relations",
            "UPDATE dbo.slate_entity_relations",
            "INSERT dbo.entity_access_grants",
            "UPDATE dbo.entity_access_grants",
            "INSERT dbo.entity_publication_versions",
            "UPDATE dbo.entity_publication_versions",
            "INSERT dbo.moments",
            "UPDATE dbo.moments",
            "INSERT dbo.moment_versions",
            "UPDATE dbo.moment_versions",
            "INSERT dbo.moment_sources",
            "UPDATE dbo.moment_sources",
            "INSERT dbo.captures",
            "UPDATE dbo.captures",
            "INSERT dbo.capture_revisions",
            "UPDATE dbo.capture_revisions",
            "INSERT dbo.journal",
            "INSERT dbo.story",
            "INSERT dbo.work",
            "INSERT dbo.project",
            "INSERT dbo.career_",
            "INSERT dbo.studio",
            "INSERT dbo.feed",
        )
        for statement in forbidden_writes:
            self.assertNotIn(statement, procedures)

        forbidden_parameters = (
            "@Body",
            "@Title",
            "@Narrative",
            "@Content",
            "@Audience",
            "@Json",
            "@Snapshot",
            "@Prompt",
        )
        for parameter in forbidden_parameters:
            self.assertNotIn(parameter, procedures)

    def test_rollback_guards_data_later_changes_and_dependencies_before_drop(self):
        forward = self.forward.read_text(encoding="utf-8")
        rollback = self.rollback.read_text(encoding="utf-8")

        self.assertIn("moment_placements contains lifecycle records", rollback)
        self.assertIn("a migration later than PS-PLACEMENT-001 is present", rollback)
        self.assertIn("sys.foreign_keys", rollback)
        self.assertIn("sys.sql_expression_dependencies", rollback)
        self.assertIn("a later table depends on PS-PLACEMENT-001", rollback)
        self.assertIn("a later programmable object depends on PS-PLACEMENT-001", rollback)
        self.assertIn("a later table uses the Placement Moment-owner key", rollback)
        self.assertIn("PS_PLACEMENT_001_DEFINITION_HASH", forward)
        self.assertIn("PS_PLACEMENT_001_DEFINITION_HASH", rollback)
        self.assertIn("HASHBYTES", forward)
        self.assertIn("HASHBYTES", rollback)
        self.assertIn("OBJECT_DEFINITION(procedure_object.object_id)", rollback)
        self.assertIn("DROP TABLE dbo.moment_placements", rollback)
        self.assertIn("DROP CONSTRAINT UQ_moments_id_owner", rollback)
        self.assertIn("migration_id = N'PS-PLACEMENT-001'", rollback)

        first_drop = rollback.index("DROP PROCEDURE")
        for guard in (
            "@PlacementAppliedAtUtc",
            "@ProtectedProcedures",
            "moment_placements contains lifecycle records",
            "sys.foreign_keys",
            "sys.sql_expression_dependencies",
            "@MomentOwnerUniqueIndexId",
        ):
            self.assertLess(rollback.index(guard), first_drop)

    def test_verification_proves_exact_version_state_isolation_and_zero_copy(self):
        sql = self.verification.read_text(encoding="utf-8")

        required_evidence = (
            "@SubjectA",
            "@SubjectB",
            "confirmed_version_number = 2",
            "source_state = N'deleted'",
            "source-deleted proposal was placed",
            "cross-owner Moment or destination",
            "stale Moment token",
            "stale placement token",
            "unavailable destination",
            "Explicit placement removal",
            "Explicit placement reactivation",
            "Idempotent placement creation",
            "audit/request metadata contains a content sentinel",
            "entity_access_grants",
            "entity_publication_versions",
            "target_available = 0",
            "ROLLBACK TRANSACTION",
            "CAST(1 AS bit) AS verified",
        )
        for evidence in required_evidence:
            self.assertIn(evidence, sql)

    def test_runner_selects_and_verifies_placement_only(self):
        runner = load_runner()

        paths = runner.selected_optional_migrations(["PS-PLACEMENT-001"])

        self.assertEqual(paths, [self.forward])
        self.assertEqual(runner.PLACEMENT_VERIFY_PATH, self.verification)
        self.assertNotIn(self.forward.name, runner.MIGRATION_FILENAMES)


@unittest.skipUnless(
    os.getenv("PS_PLACEMENT_SQL_GATE") == "1",
    "requires the isolated PS-PLACEMENT-001 SQL gate database",
)
class PlacementSqlConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection_string = os.environ["AZURE_SQL_CONNECTIONSTRING"]

    def connect(self):
        connection = connect(self.connection_string, timeout=60)
        connection.setautocommit(True)
        return connection

    def execute_procedure(self, statement, parameters):
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(statement, tuple(parameters))
            result_sets = fetch_nonempty_result_sets(cursor)
        self.assertTrue(result_sets)
        return result_sets[-1][0]

    def test_duplicate_create_and_overlapping_lifecycle_are_serialized(self):
        suffix = str(uuid.uuid4())
        source_sentinel = f"PLACEMENT_CONCURRENCY_SOURCE_{suffix}"
        title_sentinel = f"PLACEMENT_CONCURRENCY_TITLE_{suffix[:24]}"
        narrative_sentinel = f"PLACEMENT_CONCURRENCY_NARRATIVE_{suffix}"
        target_sentinel = f"PLACEMENT_CONCURRENCY_TARGET_{suffix}"
        setup_sql = """
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            BEGIN TRANSACTION;

            DECLARE @Issuer nvarchar(500) = N'urn:peerslate:placement-concurrency';
            DECLARE @Subject nvarchar(500) = ?;
            DECLARE @SourceSentinel nvarchar(300) = ?;
            DECLARE @TitleSentinel nvarchar(160) = ?;
            DECLARE @NarrativeSentinel nvarchar(500) = ?;
            DECLARE @TargetSentinel nvarchar(100) = ?;

            EXEC dbo.usp_UpsertAppUserFromAuth
                @AuthProvider = N'placement-concurrency',
                @AuthIssuer = @Issuer,
                @AuthSubject = @Subject,
                @DisplayName = N'Placement concurrency owner';

            DECLARE @UserKey nvarchar(300);
            DECLARE @ProfileId bigint;
            SELECT @UserKey = app_user.user_key, @ProfileId = profile.profile_id
            FROM dbo.app_users AS app_user
            JOIN dbo.user_identities AS identity_record
              ON identity_record.user_id = app_user.id
            JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id
            WHERE identity_record.provider = N'placement-concurrency'
              AND identity_record.issuer = @Issuer
              AND identity_record.subject = @Subject;

            EXEC dbo.usp_CreateCapture
                @UserKey = @UserKey,
                @CaptureType = N'text',
                @Body = @SourceSentinel;

            DECLARE @CaptureKey uniqueidentifier;
            SELECT @CaptureKey = capture_key
            FROM dbo.captures
            WHERE owner_profile_id = @ProfileId AND body = @SourceSentinel;

            EXEC dbo.usp_CreateOrReopenMomentProposal
                @UserKey = @UserKey,
                @CaptureKey = @CaptureKey,
                @SourceRevisionNumber = 0;

            DECLARE @MomentId bigint;
            DECLARE @MomentKey uniqueidentifier;
            DECLARE @MomentRowVersion binary(8);
            SELECT
                @MomentId = moment.moment_id,
                @MomentKey = moment.moment_key,
                @MomentRowVersion = moment.row_version
            FROM dbo.moments AS moment
            JOIN dbo.moment_sources AS source_link
              ON source_link.moment_id = moment.moment_id
            WHERE moment.owner_profile_id = @ProfileId
              AND source_link.source_capture_key = @CaptureKey;

            EXEC dbo.usp_SaveMomentProposal
                @UserKey = @UserKey,
                @MomentKey = @MomentKey,
                @ExpectedRowVersion = @MomentRowVersion,
                @MomentKind = N'achievement',
                @Title = @TitleSentinel,
                @OccurredOn = '2026-07-18',
                @OccurredPrecision = N'exact',
                @Narrative = @NarrativeSentinel,
                @WhyItMatters = NULL;

            SET @MomentRowVersion =
                (SELECT row_version FROM dbo.moments WHERE moment_id = @MomentId);
            EXEC dbo.usp_ConfirmMoment
                @UserKey = @UserKey,
                @MomentKey = @MomentKey,
                @ExpectedRowVersion = @MomentRowVersion,
                @ExpectedProposalVersion = 2;
            SET @MomentRowVersion =
                (SELECT row_version FROM dbo.moments WHERE moment_id = @MomentId);

            DECLARE @TargetEntityKey uniqueidentifier = NEWID();
            INSERT dbo.slate_entities
            (
                entity_key, owner_profile_id, entity_type, source_schema,
                source_table, source_record_id, visibility, approval_status,
                publication_status, active, deleted_at_utc
            )
            VALUES
            (
                @TargetEntityKey, @ProfileId, N'placement_test', N'dbo',
                N'placement_concurrency_fixture', @TargetSentinel,
                N'private', N'approved', N'unpublished', 1, NULL
            );

            COMMIT TRANSACTION;
            SELECT
                @UserKey AS user_key,
                @ProfileId AS profile_id,
                @MomentId AS moment_id,
                @MomentKey AS moment_key,
                @MomentRowVersion AS moment_row_version,
                @TargetEntityKey AS target_entity_key,
                (SELECT entity_id FROM dbo.slate_entities
                 WHERE entity_key = @TargetEntityKey) AS target_entity_id;
        """
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                setup_sql,
                (
                    f"placement-concurrency-{suffix}",
                    source_sentinel,
                    title_sentinel,
                    narrative_sentinel,
                    target_sentinel,
                ),
            )
            setup = fetch_nonempty_result_sets(cursor)[-1][0]

        create_sql = """
            EXEC dbo.usp_CreateOrReactivateMomentPlacement
                @UserKey = ?, @MomentKey = ?, @TargetEntityKey = ?,
                @ExpectedMomentRowVersion = ?,
                @ExpectedPlacementRowVersion = NULL;
        """
        create_parameters = (
            setup["user_key"],
            setup["moment_key"],
            setup["target_entity_key"],
            setup["moment_row_version"],
        )
        worker_barrier = threading.Barrier(3)
        worker_sessions = []
        session_lock = threading.Lock()

        def create_worker():
            with self.connect() as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT @@SPID")
                session_id = cursor.fetchone()[0]
                with session_lock:
                    worker_sessions.append(session_id)
                worker_barrier.wait(timeout=10)
                cursor.execute(create_sql, create_parameters)
                return fetch_nonempty_result_sets(cursor)[-1][0]

        blocker = self.connect()
        blocker_cursor = blocker.cursor()
        create_results = []
        blocked_before_release = []
        wait_rows = []
        try:
            blocker_cursor.execute(
                "BEGIN TRANSACTION; SELECT row_version FROM dbo.moments "
                "WITH (UPDLOCK, HOLDLOCK) WHERE moment_id = ?",
                (setup["moment_id"],),
            )
            blocker_cursor.fetchone()
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(create_worker) for _ in range(2)]
                worker_barrier.wait(timeout=10)
                time.sleep(0.5)
                blocked_before_release = [not future.done() for future in futures]
                with self.connect() as evidence_connection:
                    evidence_cursor = evidence_connection.cursor()
                    evidence_cursor.execute(
                        "SELECT session_id, wait_type, wait_time "
                        "FROM sys.dm_exec_requests WHERE session_id IN (?, ?)",
                        tuple(worker_sessions),
                    )
                    wait_rows = evidence_cursor.fetchall()
                blocker_cursor.execute("COMMIT TRANSACTION")
                create_results = [future.result(timeout=30) for future in futures]
        finally:
            try:
                blocker_cursor.execute(
                    "IF XACT_STATE() <> 0 ROLLBACK TRANSACTION"
                )
            finally:
                blocker.close()

        self.assertEqual(blocked_before_release, [True, True])
        self.assertEqual(len(wait_rows), 2)
        self.assertTrue(
            all(str(row[1]).startswith("LCK_M_") and row[2] > 0 for row in wait_rows)
        )

        self.assertEqual(
            sorted(result["outcome"] for result in create_results),
            ["created", "existing"],
        )
        self.assertEqual(
            len({str(result["placement_key"]) for result in create_results}), 1
        )
        placement_key = create_results[0]["placement_key"]
        active_token = create_results[0]["row_version"]
        self.assertEqual(
            {bytes(result["row_version"]) for result in create_results},
            {bytes(active_token)},
        )

        remove_sql = """
            EXEC dbo.usp_RemoveMomentPlacement
                @UserKey = ?, @PlacementKey = ?, @ExpectedRowVersion = ?;
        """
        remove_parameters = (setup["user_key"], placement_key, active_token)
        with ThreadPoolExecutor(max_workers=2) as pool:
            remove_results = list(
                pool.map(
                    lambda _: self.execute_procedure(remove_sql, remove_parameters),
                    range(2),
                )
            )
        self.assertEqual(
            sorted(result["outcome"] for result in remove_results),
            ["removed", "stale"],
        )

        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT placement_status, row_version FROM dbo.moment_placements "
                "WHERE placement_key = ?",
                (placement_key,),
            )
            removed_status, removed_token = cursor.fetchone()
        self.assertEqual(removed_status, "removed")

        reactivate_sql = """
            EXEC dbo.usp_CreateOrReactivateMomentPlacement
                @UserKey = ?, @MomentKey = ?, @TargetEntityKey = ?,
                @ExpectedMomentRowVersion = ?,
                @ExpectedPlacementRowVersion = ?;
        """
        reactivate_parameters = create_parameters + (removed_token,)
        overlap_remove_parameters = (setup["user_key"], placement_key, removed_token)
        with ThreadPoolExecutor(max_workers=2) as pool:
            reactivate_future = pool.submit(
                self.execute_procedure, reactivate_sql, reactivate_parameters
            )
            remove_future = pool.submit(
                self.execute_procedure, remove_sql, overlap_remove_parameters
            )
            overlap_results = [reactivate_future.result(), remove_future.result()]

        self.assertIn("reactivated", {result["outcome"] for result in overlap_results})
        self.assertTrue(
            {result["outcome"] for result in overlap_results}
            <= {"reactivated", "already_removed", "stale"}
        )

        evidence_sql = """
            SELECT
                (SELECT COUNT(*) FROM dbo.moment_placements
                 WHERE placement_key = ? AND placement_status = N'active') AS active_count,
                (SELECT COUNT(*) FROM dbo.audit_events
                 WHERE entity_type = N'moment_placement' AND entity_key = ?
                   AND action_type = N'moment.placement.created') AS create_audit_count,
                (SELECT COUNT(*) FROM dbo.audit_events
                 WHERE entity_type = N'moment_placement' AND entity_key = ?
                   AND (COALESCE(metadata_json, N'') LIKE ?
                        OR COALESCE(request_id, N'') LIKE ?)) AS sentinel_audit_count,
                (SELECT COUNT(*) FROM dbo.slate_entity_relations
                 WHERE from_entity_id = ? OR to_entity_id = ?) AS relation_count,
                (SELECT COUNT(*) FROM dbo.entity_access_grants
                 WHERE entity_id = ?) AS grant_count,
                (SELECT COUNT(*) FROM dbo.entity_publication_versions
                 WHERE entity_id = ?) AS publication_count,
                (SELECT COUNT(*) FROM dbo.moments
                 WHERE moment_id = ? AND status = N'confirmed'
                   AND visibility = N'private' AND confirmed_version_number = 2) AS unchanged_moment_count,
                (SELECT COUNT(*) FROM dbo.slate_entities
                 WHERE entity_id = ? AND visibility = N'private'
                   AND approval_status = N'approved'
                   AND publication_status = N'unpublished'
                   AND active = 1 AND deleted_at_utc IS NULL) AS unchanged_target_count;
        """
        sentinel_pattern = f"%{suffix}%"
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                evidence_sql,
                (
                    placement_key,
                    placement_key,
                    placement_key,
                    sentinel_pattern,
                    sentinel_pattern,
                    setup["target_entity_id"],
                    setup["target_entity_id"],
                    setup["target_entity_id"],
                    setup["target_entity_id"],
                    setup["moment_id"],
                    setup["target_entity_id"],
                ),
            )
            columns = [column[0] for column in cursor.description]
            evidence = dict(zip(columns, cursor.fetchone()))

        self.assertEqual(evidence["active_count"], 1)
        self.assertEqual(evidence["create_audit_count"], 1)
        self.assertEqual(evidence["sentinel_audit_count"], 0)
        self.assertEqual(evidence["relation_count"], 0)
        self.assertEqual(evidence["grant_count"], 0)
        self.assertEqual(evidence["publication_count"], 0)
        self.assertEqual(evidence["unchanged_moment_count"], 1)
        self.assertEqual(evidence["unchanged_target_count"], 1)

        print(
            "Placement SQL concurrency proof: created+existing share one active "
            "reference; duplicate remove serialized; remove/reactivate overlap "
            "completed without deadlock; two creator sessions were observed in "
            f"{sorted(str(row[1]) for row in wait_rows)} waits; "
            "sentinel/downstream counts are zero."
        )


if __name__ == "__main__":
    unittest.main()
