"""Static PS-CONNECT-002 migration and isolation contract tests.

The package is intentionally a non-production provider: these tests prove the
additive SQL contracts, rollback refusal, and registry boundary without
asserting that any database has applied the migration. A disposable database
gate remains a separately authorized release action.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.migration_registry import executable_sha256


ROOT = Path(__file__).resolve().parents[1]
FORWARD = ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-CONNECT-002_profile_relationships.sql"
ROLLBACK = ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-CONNECT-002_profile_relationships_rollback.sql"
VERIFY = ROOT / "SQL FIles" / "Verification" / "PS-CONNECT-002_relationship_isolation_verify.sql"
REGISTRY = ROOT / "SQL FIles" / "Migrations" / "registry.json"


def procedure_body(text: str, name: str) -> str:
    start = text.index(f"CREATE OR ALTER PROCEDURE dbo.{name}")
    return text[start : text.index("\n');", start)]


class Connect002MigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verify = VERIFY.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entry = next(
            entry for entry in cls.registry["migrations"] if entry["id"] == "PS-CONNECT-002"
        )

    def test_registered_additively_after_its_applied_prerequisites_with_a_passed_gate(self):
        ids = [entry["id"] for entry in self.registry["migrations"]]
        self.assertLess(ids.index("PS-PLAT-004"), ids.index("PS-CONNECT-002"))
        self.assertLess(ids.index("PS-AUTH-001"), ids.index("PS-CONNECT-002"))
        self.assertEqual(self.entry["requires"], ["PS-PLAT-004", "PS-AUTH-001"])
        self.assertEqual(
            self.entry["forward"],
            "SQL FIles/Migrations/proposed/PS-CONNECT-002_profile_relationships.sql",
        )
        self.assertEqual(
            self.entry["rollback"],
            "SQL FIles/Migrations/proposed/PS-CONNECT-002_profile_relationships_rollback.sql",
        )
        gate = self.entry["gate"]
        self.assertIsInstance(gate, dict)
        self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD))
        self.assertEqual(gate["gate_database"], "ps-connect-002-gate-202608131840")
        self.assertEqual(gate["gate_server"], "peerslate")
        self.assertEqual(
            gate["prerequisites"],
            [
                "PS-PLAT-000", "PS-PLAT-001", "PS-PLAT-002", "PS-PLAT-003",
                "PS-PLAT-004", "PS-PLAT-005", "PS-PLAT-006", "PS-PLAT-007",
                "PS-AUTH-001",
            ],
        )
        self.assertEqual(
            gate["verification"],
            "PS-CONNECT-002_relationship_isolation_verify.sql returned verified = 1",
        )
        self.assertEqual(gate["operator"], "Codex (Pete-delegated)")
        self.assertEqual(
            gate["notes"], "Disposable Azure AD gate; no production database contacted."
        )

    def test_extension_preserves_ps_plat_004_as_source_instead_of_forking_or_altering_it(self):
        for source in ("dbo.connection_requests", "dbo.member_connections", "dbo.user_blocks"):
            self.assertIn(source, self.forward)
            self.assertNotIn(source, self.rollback)
        self.assertNotIn("ALTER TABLE dbo.connection_requests", self.forward)
        self.assertNotIn("ALTER TABLE dbo.member_connections", self.forward)
        self.assertNotIn("ALTER TABLE dbo.user_blocks", self.forward)
        self.assertNotIn("DROP TABLE", self.forward.upper())
        self.assertIn("reciprocal pending requests requiring explicit reconciliation", self.forward)
        self.assertIn("both pending and active relationship truth", self.forward)
        self.assertIn("pending request behind an active block", self.forward)

    def test_forward_creates_only_the_additive_state_event_command_extension_and_exact_procedures(self):
        for table in (
            "dbo.connection_relationship_states",
            "dbo.connection_relationship_events",
            "dbo.connection_relationship_commands",
        ):
            self.assertIn(f"CREATE TABLE {table}", self.forward)
        for procedure in (
            "usp_CommitConnectionRelationshipCommandForActor",
            "usp_GetConnectionRelationshipSnapshotForActor",
            "usp_GetConnectionRelationshipCommandForActor",
        ):
            self.assertIn(f"CREATE OR ALTER PROCEDURE dbo.{procedure}", self.forward)
        self.assertNotIn("profile_publications", self.forward)
        self.assertNotIn("CREATE PROCEDURE dbo.usp_GetProfile", self.forward)
        self.assertIn("UQ_connection_relationship_commands_actor_idempotency", self.forward)
        self.assertIn("UQ_connection_relationship_events_sequence", self.forward)
        self.assertIn("pending_requester_user_id IS NOT NULL", self.forward)
        self.assertIn(
            "idempotency_key nvarchar(128) COLLATE Latin1_General_100_BIN2 NOT NULL",
            self.forward,
        )

    def test_all_lifecycle_actions_are_explicit_and_only_the_initial_request_or_block_lack_cas(self):
        procedure = procedure_body(
            self.forward, "usp_CommitConnectionRelationshipCommandForActor"
        )
        for action in (
            "request", "accept", "decline", "cancel", "expire", "disconnect",
            "block", "unblock", "reconnect",
        ):
            self.assertIn(f"N''{action}''", procedure)
        self.assertIn("@ExpectedVersion", procedure)
        self.assertIn("@Command NOT IN (N''request'', N''block'')", procedure)
        self.assertIn("@CurrentVersion = 0 AND (@ExpectedVersion IS NOT NULL", procedure)
        self.assertIn("@CurrentVersion <> 0 AND (@ExpectedVersion IS NULL", procedure)
        self.assertIn("sp_getapplock", procedure)
        self.assertIn("UPDLOCK, HOLDLOCK", procedure)
        self.assertLess(
            procedure.index("@ExpectedVersion IS NULL"),
            procedure.index("UPDATE dbo.connection_relationship_states"),
        )
        cas_index = procedure.index("@CurrentVersion = 0 AND (@ExpectedVersion IS NOT NULL")
        for mutation in (
            "INSERT dbo.user_blocks",
            "UPDATE dbo.connection_requests",
            "UPDATE dbo.member_connections",
            "INSERT dbo.connection_relationship_states",
            "UPDATE dbo.connection_relationship_states",
        ):
            self.assertLess(cas_index, procedure.index(mutation), mutation)
        self.assertIn("@NextVersion bigint = @CurrentVersion + 1", procedure)
        self.assertIn("WHEN @CurrentBlockEpoch = 0 THEN 1", procedure)
        self.assertIn("@CurrentBlockEpoch + CASE WHEN @AdvanceBlockEpoch = 1", procedure)
        self.assertIn("@NextEventSequence bigint = @CurrentEventSequence + 1", procedure)

    def test_command_replay_is_binary_exact_and_does_not_mutate_before_returning_stored_winner(self):
        procedure = procedure_body(
            self.forward, "usp_CommitConnectionRelationshipCommandForActor"
        )
        for contract in (
            "idempotency_key COLLATE Latin1_General_100_BIN2",
            "@ExistingDigest COLLATE Latin1_General_100_BIN2",
            "@ExistingCommand COLLATE Latin1_General_100_BIN2",
            "@ExistingCommandId IS NOT NULL",
            "SELECT CAST(0 AS bit) AS committed",
            "SELECT CAST(1 AS bit) AS committed",
        ):
            self.assertIn(contract, procedure)
        self.assertLess(
            procedure.index("@ExistingCommandId IS NOT NULL"),
            procedure.index("INSERT dbo.connection_relationship_events"),
        )
        self.assertLess(
            procedure.index("@ExistingCommandId IS NOT NULL"),
            procedure.index("INSERT dbo.connection_relationship_commands"),
        )

    def test_lifecycle_branches_preserve_orientation_and_block_precedence(self):
        procedure = procedure_body(
            self.forward, "usp_CommitConnectionRelationshipCommandForActor"
        )
        for contract in (
            "@CurrentState NOT IN (N''none'', N''declined'', N''cancelled'', N''expired'')",
            "@CurrentPendingRequesterId = @SubjectUserId",
            "AND @PendingRequesterId = @SubjectUserId",
            "AND @PendingRecipientId = @ActorUserId",
            "@CurrentPendingRequesterId <> @SubjectUserId",
            "@CurrentPendingRequesterId <> @ActorUserId",
            "@ActorUserId NOT IN (@PendingRequesterId, @PendingRecipientId)",
            "@CurrentState <> N''disconnected''",
            "@AnyActiveBlock = 1 OR @CurrentState = N''blocked''",
            "SET request_status = N''cancelled''",
            "SET connection_status = N''ended''",
            "SET @NewState = CASE WHEN @AnyActiveBlock = 1 THEN N''blocked'' ELSE N''none'' END",
            "SET @EventKind = N''reciprocal_accept''",
        ):
            self.assertIn(contract, procedure)
        self.assertLess(
            procedure.index("@AnyActiveBlock = 1 OR @CurrentState = N''blocked''"),
            procedure.index("IF @Command = N''request''"),
        )

    def test_reciprocal_request_is_reachable_only_from_canonical_opposite_pending_truth(self):
        procedure = procedure_body(
            self.forward, "usp_CommitConnectionRelationshipCommandForActor"
        )
        reciprocal_truth = (
            "DECLARE @IsReciprocalPendingRequest bit = CASE WHEN\n"
            "            @CurrentState = N''pending''\n"
            "            AND @CurrentPendingRequesterId = @SubjectUserId\n"
            "            AND @PendingRequestId IS NOT NULL\n"
            "            AND @PendingRequesterId = @SubjectUserId\n"
            "            AND @PendingRecipientId = @ActorUserId\n"
            "        THEN 1 ELSE 0 END;"
        )
        request_guard = (
            "IF @CurrentState NOT IN (N''none'', N''declined'', N''cancelled'', N''expired'')\n"
            "                   AND @IsReciprocalPendingRequest = 0"
        )
        self.assertIn(reciprocal_truth, procedure)
        self.assertIn(request_guard, procedure)
        self.assertIn("IF @IsReciprocalPendingRequest = 1", procedure)
        self.assertLess(
            procedure.index(request_guard),
            procedure.index("IF @IsReciprocalPendingRequest = 1"),
        )

    def test_snapshot_and_command_readers_bind_server_derived_actor_before_returning_pair_data(self):
        snapshot_proc = procedure_body(
            self.forward, "usp_GetConnectionRelationshipSnapshotForActor"
        )
        command_proc = procedure_body(
            self.forward, "usp_GetConnectionRelationshipCommandForActor"
        )
        for contract in (
            "@ActorUserKey", "@SubjectUserKey", "app_user.active = 1",
            "app_user.account_status = N''active''", "@ActorUserId = @SubjectUserId",
            "@Blocked = 1 THEN N''blocked''", "blocked_either_direction",
        ):
            self.assertIn(contract, snapshot_proc)
        self.assertIn("actor_user.user_key COLLATE Latin1_General_100_BIN2 = @ActorUserKey", command_proc)
        self.assertIn("command_record.idempotency_key COLLATE Latin1_General_100_BIN2", command_proc)
        self.assertIn("subject_user.active = 1 AND subject_user.account_status = N''active''", command_proc)
        self.assertNotIn("SELECT *", snapshot_proc)
        self.assertNotIn("SELECT *", command_proc)

    def test_sql_opaque_key_validation_matches_the_python_underscore_and_hyphen_contract(self):
        self.assertNotIn("A-Za-z0-9[_]-", self.forward)
        self.assertEqual(self.forward.count("A-Za-z0-9_"), 8)
        self.assertEqual(self.forward.count("N''%[^-A-Za-z0-9_]%''"), 7)
        self.assertIn("N'%[^-A-Za-z0-9_]%'", self.forward)
        self.assertIn(
            "CK_connection_relationship_commands_idempotency CHECK (LEN(idempotency_key) BETWEEN 8 AND 128",
            self.forward,
        )

    def test_rollback_refuses_data_or_later_history_and_drops_only_connect_extension_objects(self):
        for contract in (
            "PS-CONNECT-002 rollback refused because a later or unrelated migration is present",
            "PS-CONNECT-002 rollback refused because relationship data exists",
            "dbo.connection_relationship_commands",
            "dbo.connection_relationship_events",
            "dbo.connection_relationship_states",
        ):
            self.assertIn(contract, self.rollback)
        for ps_plat_table in ("connection_requests", "member_connections", "user_blocks"):
            self.assertNotIn(ps_plat_table, self.rollback)

    def test_verifier_requires_additive_shape_binary_identity_and_concurrency_fences(self):
        for contract in (
            "PS-CONNECT-002 relationship isolation verification",
            "connection_relationship_states",
            "connection_relationship_events",
            "connection_relationship_commands",
            "Latin1_General_100_BIN2",
            "sp_getapplock",
            "UPDLOCK, HOLDLOCK",
            "UQ_connection_relationship_commands_actor_idempotency",
            "reciprocal request transition",
            "gate-reciprocal-002",
            "@ExpectedRelationshipVersion = @FirstVersion",
            "DECLARE @VerifierFirstDigest nvarchar(64) = REPLICATE(N'a', 64);",
            "DECLARE @VerifierSecondDigest nvarchar(64) = REPLICATE(N'b', 64);",
            "@RequestDigest = @VerifierFirstDigest",
            "@RequestDigest = @VerifierSecondDigest",
            "@IdempotencyKey = N'gate.invalid.004'",
            "opaque key predicate refusal",
            "IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;",
            "verified",
            "not a production gate",
        ):
            self.assertIn(contract, self.verify)


if __name__ == "__main__":
    unittest.main()
