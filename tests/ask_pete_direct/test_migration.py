"""Source-level guardrails for the PS-ASK-PETE-DIRECT-001 migration set.

These read the T-SQL as text. They do not need (and must not require) a
database: the executable proof is the disposable-database gate
(``scripts/govern_sql_migrations.py gate``) plus
``PS-ASK-PETE-DIRECT-001_owner_isolation_verify.sql``. What is checked here
is everything that can drift silently in an editor - the guards, the bounds,
the ownership predicates, and above all the absence of any delete path.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
VERIFICATION = ROOT / "SQL FIles" / "Verification"
REGISTRY = ROOT / "SQL FIles" / "Migrations" / "registry.json"

FORWARD = MIGRATIONS / "PS-ASK-PETE-DIRECT-001_recruiter_questions.sql"
ROLLBACK = MIGRATIONS / "PS-ASK-PETE-DIRECT-001_recruiter_questions_rollback.sql"
VERIFY = VERIFICATION / "PS-ASK-PETE-DIRECT-001_owner_isolation_verify.sql"

PROCEDURE_NAMES = (
    "usp_SubmitRecruiterQuestion",
    "usp_ListRecruiterQuestionsForOwner",
    "usp_SetRecruiterQuestionStatusForOwner",
)

TABLES = ("recruiter_questions", "recruiter_question_save_requests")


def procedure_batches(sql: str) -> dict[str, str]:
    """Map each CREATE OR ALTER PROCEDURE dynamic-SQL batch to its name.

    Copied from tests/test_workshop_migration.py. It doubles as a quoting
    check: an unbalanced apostrophe inside a batch makes the batch
    unparseable here, which is exactly what it would be on the server.
    """
    batches = re.findall(r"EXEC\(N'((?:''|[^'])*)'\);", sql, re.DOTALL)
    mapped = {}
    for batch in batches:
        match = re.search(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)", batch)
        if match:
            mapped[match.group(1)] = batch
    return mapped


class RecruiterQuestionMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verification = VERIFY.read_text(encoding="utf-8")
        cls.procedures = procedure_batches(cls.forward)

    def test_forward_rollback_and_verification_exist(self):
        for path in (FORWARD, ROLLBACK, VERIFY):
            self.assertTrue(path.is_file(), path)

    def test_no_file_carries_a_byte_order_mark(self):
        for path in (FORWARD, ROLLBACK, VERIFY):
            with self.subTest(path=path.name):
                self.assertNotEqual(path.read_bytes()[:3], b"\xef\xbb\xbf")

    def test_all_three_procedures_are_present_exactly_once(self):
        self.assertEqual(set(self.procedures), set(PROCEDURE_NAMES))
        self.assertEqual(
            self.forward.count("CREATE OR ALTER PROCEDURE"), len(PROCEDURE_NAMES)
        )

    def test_migration_is_one_guarded_transactional_batch(self):
        for token in (
            "SET NOCOUNT ON",
            "SET XACT_ABORT ON",
            "BEGIN TRY",
            "BEGIN TRANSACTION",
            "COMMIT TRANSACTION",
            "IF XACT_STATE() <> 0 ROLLBACK TRANSACTION",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.forward)

    def test_prerequisites_are_guarded_before_anything_is_created(self):
        for migration_id in ("PS-PLAT-001", "PS-PLAT-002", "PS-AUTH-001"):
            with self.subTest(migration_id=migration_id):
                guard = (
                    "IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations "
                    f"WHERE migration_id = N'{migration_id}')"
                )
                self.assertIn(guard, self.forward)
                self.assertLess(
                    self.forward.index(guard),
                    self.forward.index("CREATE TABLE dbo.recruiter_questions"),
                )

    def test_every_create_is_idempotent(self):
        for table in TABLES:
            with self.subTest(table=table):
                self.assertIn(
                    f"IF OBJECT_ID(N'dbo.{table}', N'U') IS NULL", self.forward
                )
        # CREATE OR ALTER makes each procedure re-appliable in place.
        self.assertNotIn("CREATE PROCEDURE", self.forward)

    def test_the_ledger_row_and_audit_event_are_written_once(self):
        self.assertIn("N'PS-ASK-PETE-DIRECT-001'", self.forward)
        self.assertIn("schema.migration.applied", self.forward)
        self.assertEqual(self.forward.count("INSERT dbo.schema_migrations"), 1)


class ArchiveOnlyTests(unittest.TestCase):
    """v1 has no delete path anywhere. This is the check that keeps it so."""

    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.procedures = procedure_batches(cls.forward)

    def test_no_procedure_body_contains_a_delete_statement(self):
        for name, body in self.procedures.items():
            with self.subTest(procedure=name):
                self.assertNotIn("DELETE", body.upper())

    def test_the_migration_never_deletes_from_either_new_table(self):
        pattern = re.compile(
            r"\b(DELETE|TRUNCATE)\s+(TABLE\s+)?(dbo\.)?recruiter_question", re.I
        )
        self.assertIsNone(pattern.search(self.forward))

    def test_the_forward_migration_declares_no_delete_or_purge_procedure(self):
        for forbidden in ("usp_DeleteRecruiterQuestion", "usp_PurgeRecruiterQuestion"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.forward)

    def test_the_rollback_refuses_rather_than_discarding_stored_questions(self):
        self.assertIn("EXISTS (SELECT 1 FROM dbo.recruiter_questions)", self.rollback)
        self.assertIn("Rollback refused: recruiter questions are stored.", self.rollback)
        # The only rows this script may remove are its own ledger row.
        deletes = re.findall(r"^\s*DELETE\s+(\S+)", self.rollback, re.M)
        self.assertEqual(deletes, ["dbo.schema_migrations"])

    def test_the_rollback_guards_drift_and_later_migrations(self):
        for token in (
            "a migration later than PS-ASK-PETE-DIRECT-001 is present",
            "PS_ASK_PETE_DIRECT_001_DEFINITION_HASH",
            "a protected PS-ASK-PETE-DIRECT-001 procedure changed after it applied",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.rollback)

    def test_the_rollback_drops_the_child_ledger_before_its_parent(self):
        self.assertLess(
            self.rollback.index("DROP TABLE dbo.recruiter_question_save_requests"),
            self.rollback.index("DROP TABLE dbo.recruiter_questions"),
        )


class OwnerScopingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.procedures = procedure_batches(cls.forward)

    def test_no_procedure_accepts_an_owner_id_from_its_caller(self):
        for name, body in self.procedures.items():
            with self.subTest(procedure=name):
                self.assertNotIn("@OwnerProfileId", body)

    def test_every_procedure_resolves_its_own_owner_key(self):
        for name, body in self.procedures.items():
            with self.subTest(procedure=name):
                self.assertIn("JOIN dbo.app_users AS app_user", body)
                self.assertIn("app_user.active = 1", body)
                self.assertIn("profile.active = 1", body)
                self.assertIn("owner_profile_id = @ProfileId", body)

    def test_the_owner_scoped_procedures_take_a_bounded_user_key(self):
        for name in (
            "usp_ListRecruiterQuestionsForOwner",
            "usp_SetRecruiterQuestionStatusForOwner",
        ):
            with self.subTest(procedure=name):
                self.assertIn("@UserKey nvarchar(300)", self.procedures[name])

    def test_the_public_submit_takes_a_bounded_recipient_key_and_no_sender(self):
        body = self.procedures["usp_SubmitRecruiterQuestion"]
        self.assertIn("@OwnerUserKey nvarchar(300)", body)
        # There is no sender parameter of any kind: no identity, no address,
        # no fingerprint. The only personal data is what the sender typed.
        for forbidden in ("@SenderUserKey", "@SenderEmail", "@SenderIp", "@ClientIp"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, body)

    def test_the_list_read_is_bounded_and_excludes_archived_by_default(self):
        body = self.procedures["usp_ListRecruiterQuestionsForOwner"]
        self.assertIn("TOP (200)", body)
        self.assertIn("@IncludeArchived bit = 0", body)
        self.assertIn(
            "(@IncludeArchived = 1 OR question.question_status <> N''archived'')", body
        )

    def test_the_status_change_is_version_fenced(self):
        body = self.procedures["usp_SetRecruiterQuestionStatusForOwner"]
        self.assertIn("@ExpectedRowVersion binary(8)", body)
        self.assertIn("question.row_version = @ExpectedRowVersion", body)
        self.assertIn("SELECT N''changed'' AS outcome", body)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", body)


class ConsentAndBoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.procedures = procedure_batches(cls.forward)

    def test_consent_is_required_by_the_procedure_before_it_stores(self):
        body = self.procedures["usp_SubmitRecruiterQuestion"]
        self.assertIn("IF @ConsentGiven IS NULL OR @ConsentGiven <> 1", body)
        self.assertLess(
            body.index("@ConsentGiven <> 1"),
            body.index("INSERT dbo.recruiter_questions"),
        )

    def test_the_stored_consent_version_is_a_column_not_an_assumption(self):
        self.assertIn("consent_version nvarchar(60) NOT NULL", self.forward)

    def test_text_bounds_are_enforced_by_check_constraints_in_utf16_units(self):
        for constraint in (
            "DATALENGTH(question_text) / 2 BETWEEN 1 AND 2000",
            "DATALENGTH(contact_text) / 2 BETWEEN 1 AND 300",
            "DATALENGTH(consent_version) / 2 BETWEEN 1 AND 60",
        ):
            with self.subTest(constraint=constraint):
                self.assertIn(constraint, self.forward)

    def test_the_procedure_rejects_over_length_text_before_the_constraint_does(self):
        body = self.procedures["usp_SubmitRecruiterQuestion"]
        for guard in (
            "IF DATALENGTH(@IdempotencyKey) / 2 > 200",
            "IF DATALENGTH(@QuestionText) / 2 > 2000",
            "IF @ContactText IS NOT NULL AND DATALENGTH(@ContactText) / 2 > 300",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, body)

    def test_the_status_column_is_constrained_to_three_values(self):
        self.assertIn(
            "question_status IN (N'new', N'read', N'archived')", self.forward
        )

    def test_the_submit_never_returns_the_question_key_to_its_caller(self):
        body = self.procedures["usp_SubmitRecruiterQuestion"]
        for outcome in ("not_found", "existing", "success"):
            with self.subTest(outcome=outcome):
                self.assertIn(f"SELECT N''{outcome}'' AS outcome;", body)
        self.assertNotIn("AS outcome,", body)

    def test_audit_metadata_carries_no_question_or_contact_text(self):
        body = self.procedures["usp_SubmitRecruiterQuestion"]
        metadata = body[body.index("@AuditMetadataJson nvarchar(max) = CONCAT") :]
        metadata = metadata[: metadata.index(";")]
        self.assertIn("has_contact", metadata)
        self.assertIn("consent_version", metadata)
        self.assertNotIn("@QuestionText", metadata)
        self.assertNotIn("@ContactText,", metadata)

    def test_an_anonymous_submission_never_manufactures_an_actor(self):
        body = self.procedures["usp_SubmitRecruiterQuestion"]
        audit = body[body.index("EXEC dbo.usp_AppendAuditEvent") :]
        self.assertNotIn("@ActorUserId", audit)
        self.assertNotIn("@ActorUserKeySnapshot", audit)


class VerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verification = VERIFY.read_text(encoding="utf-8")

    def test_the_verifier_always_rolls_its_synthetic_state_back(self):
        self.assertIn("ROLLBACK TRANSACTION;", self.verification)
        self.assertIn("CAST(1 AS bit) AS verified", self.verification)
        self.assertNotIn("COMMIT TRANSACTION", self.verification)

    def test_the_verifier_uses_two_distinct_synthetic_recipients(self):
        self.assertIn("usp_UpsertAppUserFromAuth", self.verification)
        self.assertIn("@UserKeyA = @UserKeyB OR @ProfileIdA = @ProfileIdB", self.verification)

    def test_the_verifier_proves_the_properties_that_matter(self):
        for claim in (
            "A recruiter question procedure contains a DELETE statement.",
            "usp_SubmitRecruiterQuestion does not require consent.",
            "usp_SubmitRecruiterQuestion returns more than an outcome",
            "A repeated idempotency key did not report an existing question.",
            "A replayed submit created a second question.",
            "The same idempotency-key literal collided across two recipients.",
            "A cross-recipient question leaked into the recipient A list read.",
            "A stale expected version did not produce a changed outcome.",
            "Archiving removed the question instead of keeping it retrievable.",
            "A forged recipient key produced a truthful-looking submit outcome.",
            "Audit metadata contains recruiter question or contact text.",
            "An anonymous submission was audited against a manufactured actor identity.",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, self.verification)

    def test_captured_calls_opt_out_of_the_second_result_set(self):
        """Every INSERT ... EXEC of the list read must suppress result set 2.

        T-SQL requires every result set a target procedure returns to match
        the INSERT target's column list, so a capture that forgot
        @IncludeTotalCount = 0 would fail at run time only - during the gate,
        against a real server, long after this file was written.
        """
        captures = re.findall(
            r"INSERT @\w+\s+EXEC dbo\.usp_ListRecruiterQuestionsForOwner[^;]+;",
            self.verification,
        )
        self.assertTrue(captures)
        for capture in captures:
            with self.subTest(capture=capture.split("\n")[0]):
                self.assertIn("@IncludeTotalCount = 0", capture)

    def test_success_path_calls_are_never_captured_with_insert_exec(self):
        """INSERT ... EXEC cannot nest, and every success path audits.

        A captured call may only be one that returns before
        usp_AppendAuditEvent - i.e. one whose expected outcome is
        'existing', 'not_found', or 'changed'.
        """
        captures = re.findall(
            r"INSERT @\w+\s+EXEC dbo\.usp_(?:SubmitRecruiterQuestion|"
            r"SetRecruiterQuestionStatusForOwner)[^;]+;",
            self.verification,
        )
        self.assertTrue(captures)
        for capture in captures:
            following = self.verification[
                self.verification.index(capture) + len(capture) :
            ][:600]
            with self.subTest(capture=capture.split("\n")[0]):
                self.assertTrue(
                    any(
                        outcome in following
                        for outcome in ("N'existing'", "N'not_found'", "N'changed'")
                    ),
                    "a captured call must stay on an early-return branch",
                )


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.entry = next(
            entry
            for entry in cls.document["migrations"]
            if entry["id"] == "PS-ASK-PETE-DIRECT-001"
        )

    def test_the_entry_carries_exactly_the_registry_keys(self):
        self.assertEqual(
            {"id", "forward", "rollback", "requires", "summary", "gate"},
            set(self.entry),
        )

    def test_the_entry_is_registered_ungated(self):
        """gate: null is the truthful state. This migration has never been

        proven against a throwaway database, so the governed applier must
        refuse it. The gate proof is a later, owner-attended leg."""
        self.assertIsNone(self.entry["gate"])

    def test_the_entry_points_at_files_that_exist(self):
        for key in ("forward", "rollback"):
            with self.subTest(key=key):
                self.assertTrue((ROOT / self.entry[key]).is_file())
                self.assertNotIn("\\", self.entry[key])

    def test_every_prerequisite_is_registered_earlier(self):
        order = [entry["id"] for entry in self.document["migrations"]]
        position = order.index("PS-ASK-PETE-DIRECT-001")
        for requirement in self.entry["requires"]:
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, order[:position])


if __name__ == "__main__":
    unittest.main()
