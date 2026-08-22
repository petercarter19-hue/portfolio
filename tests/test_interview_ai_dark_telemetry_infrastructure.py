"""PS-INTERVIEW-AI-EXTRACT-001 dark telemetry infrastructure.

This branch lands the telemetry table, procedures, roles, purge script,
and independently gated pipeline stage **without changing the Interview
runtime**. Nothing here dispatches to a provider, connects to a database,
or enables anything.

The tests below hold the separation contract:

- the application identity may append and may NOT purge;
- the maintenance identity is separate from both the application and
  Community identities;
- retention is default-off and schedule-isolated from Community;
- the migration and rollback match the CURRENT recorded disposable-gate
  receipt, refreshed on a new throwaway database whenever the SQL bytes
  change;
- the migration carries schema only: the two execute-only roles, their
  grants and the identity memberships are created by the administrator-run
  authority script, because the governed apply identity holds
  db_ddladmin only (run 1419, 2026-08-22, refused the in-migration
  version transactionally and wrote nothing);
- no runtime, provider, or B3 runtime-lock material entered this branch;
- evidence carries no secret, connection string, member content, model
  content, URL, or raw exception text.
"""

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.database_service import ALLOWED_PROCEDURES  # noqa: E402

PIPELINE = (ROOT / "azure-pipelines.yml").read_text(encoding="utf-8")
MIGRATION_DIR = ROOT / "SQL FIles" / "Migrations"
FORWARD_SQL = (
    MIGRATION_DIR / "proposed" / "PS-INTERVIEW-AI-EXTRACT-001_telemetry.sql"
)
ROLLBACK_SQL = (
    MIGRATION_DIR / "proposed"
    / "PS-INTERVIEW-AI-EXTRACT-001_telemetry_rollback.sql"
)
SQL_REGISTRY = json.loads(
    (MIGRATION_DIR / "registry.json").read_text(encoding="utf-8")
)
EVIDENCE_DIR = ROOT / "docs" / "initiatives" / "PS-INTERVIEW-AI-EXTRACT-001"
DISPOSABLE_PROOF = json.loads(
    (EVIDENCE_DIR / "05_SQL_DISPOSABLE_PROOF.json").read_text(encoding="utf-8")
)

APPEND_PROCEDURE = "usp_AppendInterviewAIServerCall"
PURGE_PROCEDURE = "usp_PurgeInterviewAIServerCalls"
ENABLE_VARIABLE = "interviewTelemetryMaintenanceEnabled"
INTERVIEW_SCHEDULE = "Interview telemetry retention nightly"
COMMUNITY_SCHEDULE = "Community maintenance hourly"


def _migration_record():
    for migration in SQL_REGISTRY["migrations"]:
        if migration["id"] == "PS-INTERVIEW-AI-EXTRACT-001":
            return migration
    raise AssertionError("the telemetry migration is not registered")


class ApplicationBoundaryTests(unittest.TestCase):
    """The application may append; only the maintenance identity purges."""

    def test_append_procedure_is_allowlisted(self):
        self.assertIn(APPEND_PROCEDURE, ALLOWED_PROCEDURES)

    def test_purge_procedure_is_never_allowlisted(self):
        # execute_procedure raises before the database boundary for any
        # name outside the allowlist, so this absence is the enforcement.
        self.assertNotIn(PURGE_PROCEDURE, ALLOWED_PROCEDURES)

    def test_no_interview_procedure_other_than_append_is_allowlisted(self):
        interview_names = {
            name for name in ALLOWED_PROCEDURES if "InterviewAI" in name
        }
        self.assertEqual(interview_names, {APPEND_PROCEDURE})

    def test_purge_reaches_the_database_only_through_its_own_script(self):
        purge_script = (
            ROOT / "scripts" / "interview_ai"
            / "run_interview_telemetry_purge.py"
        ).read_text(encoding="utf-8")
        self.assertIn(PURGE_PROCEDURE, purge_script)
        # The out-of-process purge uses its own dedicated connection
        # variable, never the application's database service.
        self.assertIn("INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING", purge_script)
        self.assertNotIn("database_service", purge_script)


class RetentionGatingTests(unittest.TestCase):
    """Retention is default-off and isolated from Community."""

    def _stage_body(self, stage_name):
        pattern = re.compile(
            r"(?ms)^  - stage: %s\b.*?(?=^  - stage: |\Z)" % stage_name
        )
        match = pattern.search(PIPELINE)
        self.assertIsNotNone(match, "stage %s is missing" % stage_name)
        return match.group(0)

    def test_retention_stage_exists_and_is_schedule_gated(self):
        body = self._stage_body("InterviewTelemetryMaintenance")
        self.assertIn("eq(variables['Build.Reason'], 'Schedule')", body)
        self.assertIn(
            "eq(variables['Build.CronSchedule.DisplayName'], '%s')"
            % INTERVIEW_SCHEDULE,
            body,
        )
        self.assertIn(
            "eq(variables['Build.SourceBranch'], 'refs/heads/main')", body
        )

    def test_community_stage_is_pinned_to_its_own_schedule(self):
        body = self._stage_body("CommunityMaintenance")
        self.assertIn(
            "eq(variables['Build.CronSchedule.DisplayName'], '%s')"
            % COMMUNITY_SCHEDULE,
            body,
        )
        # Community must not respond to the Interview schedule.
        self.assertNotIn(INTERVIEW_SCHEDULE, body)

    def test_the_two_schedules_are_distinct_and_both_declared(self):
        self.assertIn("displayName: %s" % INTERVIEW_SCHEDULE, PIPELINE)
        self.assertIn("displayName: %s" % COMMUNITY_SCHEDULE, PIPELINE)
        self.assertNotEqual(INTERVIEW_SCHEDULE, COMMUNITY_SCHEDULE)

    def test_every_operative_retention_step_requires_explicit_enablement(self):
        body = self._stage_body("InterviewTelemetryMaintenance")
        # The disabled report runs when the variable is not exactly 'true';
        # every operative step requires succeeded() AND exactly 'true'
        # (correction C1: an enable check alone would run after an earlier
        # step in the job had failed).
        self.assertIn(
            "ne(variables['%s'], 'true')" % ENABLE_VARIABLE, body
        )
        self.assertIn(
            "eq(variables['%s'], 'true')" % ENABLE_VARIABLE, body
        )
        # The purge invocation itself is one of the gated steps.
        purge_line = [
            line for line in body.splitlines()
            if "run_interview_telemetry_purge.py" in line
        ]
        self.assertTrue(purge_line, "the purge invocation is missing")

    def test_retention_is_default_off_because_the_variable_is_undeclared(self):
        # A default-on variable would appear in the pipeline's variables
        # block. It must not: the operator creates it, later, deliberately.
        variables_block = re.search(
            r"(?ms)^variables:.*?(?=^stages:)", PIPELINE
        ).group(0)
        self.assertNotIn(ENABLE_VARIABLE, variables_block)

    def test_maintenance_identity_is_separate(self):
        body = self._stage_body("InterviewTelemetryMaintenance")
        community = self._stage_body("CommunityMaintenance")
        self.assertIn(
            "interviewTelemetryMaintenanceSqlConnectionString", body
        )
        # The Interview connection variable is used by Interview only, and
        # Interview borrows no Community connection variable.
        self.assertNotIn(
            "interviewTelemetryMaintenanceSqlConnectionString", community
        )
        community_connections = set(
            re.findall(r"\$\((community[A-Za-z]*[Cc]onnection[A-Za-z]*)\)",
                       community)
        )
        for name in community_connections:
            self.assertNotIn(name, body)

    def test_purge_runs_inside_the_interview_service_connection(self):
        """Defect correction: the purge must execute inside an AzureCLI
        task bound to the dedicated Interview maintenance service
        connection, as Community maintenance does. A plain script step has
        no identity on a hosted agent and could never authenticate the
        nonsecret ActiveDirectoryDefault connection. The task is inserted
        at COMPILE time only once the connection variable exists, because
        Azure resolves azureSubscription when the YAML compiles and an
        undefined connection would invalidate the whole pipeline."""
        body = self._stage_body("InterviewTelemetryMaintenance")
        purge_index = body.index("run_interview_telemetry_purge.py")
        preceding = body[:purge_index]
        task_index = preceding.rfind("- task: AzureCLI@2")
        script_index = preceding.rfind("- script:")
        self.assertGreater(task_index, -1, "purge is not inside an AzureCLI task")
        self.assertGreater(task_index, script_index,
                           "a plain script step precedes the purge invocation")
        self.assertIn(
            "azureSubscription: $(interviewTelemetryMaintenanceServiceConnectionId)",
            body[task_index:purge_index],
        )
        guard = preceding.rfind(
            "- ${{ if ne(variables['interviewTelemetryMaintenanceServiceConnectionId'], '') }}:"
        )
        self.assertGreater(guard, -1, "the AzureCLI task is not compile-time guarded")
        self.assertLess(guard, task_index)
        # The continuation lines are real (multi-line inline script).
        self.assertIn("run_interview_telemetry_purge.py \\\n", body)
        community = self._stage_body("CommunityMaintenance")
        self.assertNotIn("interviewTelemetryMaintenanceServiceConnectionId", community)
        self.assertNotIn("communityMaintenanceServiceConnectionId", body)

    def test_retention_evidence_artifact_is_published_on_every_run(self):
        body = self._stage_body("InterviewTelemetryMaintenance")
        self.assertIn("artifact: InterviewTelemetryMaintenanceEvidence", body)
        self.assertIn("condition: always()", body)


class GateReceiptTests(unittest.TestCase):
    """The SQL matches the current recorded gate receipt."""

    def test_migration_matches_the_recorded_gate_receipt(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        from migration_registry import executable_sha256
        record = _migration_record()
        self.assertEqual(
            executable_sha256(FORWARD_SQL),
            record["gate"]["executable_sha256"],
            "the migration bytes no longer match the gate receipt; a new "
            "disposable gate would be required, which is withheld",
        )

    def test_registry_points_at_both_sql_files(self):
        record = _migration_record()
        self.assertEqual(
            record["forward"],
            "SQL FIles/Migrations/proposed/"
            "PS-INTERVIEW-AI-EXTRACT-001_telemetry.sql",
        )
        self.assertEqual(
            record["rollback"],
            "SQL FIles/Migrations/proposed/"
            "PS-INTERVIEW-AI-EXTRACT-001_telemetry_rollback.sql",
        )
        self.assertTrue(FORWARD_SQL.is_file())
        self.assertTrue(ROLLBACK_SQL.is_file())

    def test_gate_database_was_disposable_and_recorded_as_deleted(self):
        record = _migration_record()
        gate_database = record["gate"]["gate_database"]
        self.assertNotIn("peerslate-database", gate_database)
        lifecycle = DISPOSABLE_PROOF["disposable_database_lifecycle"]
        self.assertIn(gate_database, lifecycle["created"])
        self.assertIn("delete", lifecycle["deleted"].lower())

    def test_rollback_refuses_to_drop_a_populated_table(self):
        rollback = ROLLBACK_SQL.read_text(encoding="utf-8")
        self.assertIn("50090", rollback)
        proof = DISPOSABLE_PROOF["checks"]
        self.assertEqual(proof["rollback_refuses_nonempty_table"], "pass")
        self.assertEqual(
            proof["rollback_completes_against_empty_table"], "pass"
        )


class MigrationAuthorityBoundaryTests(unittest.TestCase):
    """Schema and security-principal work are separate operations.

    The governed apply identity (peerslate-ado-schema) holds db_ddladmin
    only. It can create tables and procedures; it can neither create
    database roles nor grant execute permission. Run 1419 (2026-08-22)
    refused the migration that embedded both - transactionally, nothing
    written - so the roles, grants and memberships now come from the
    administrator-run authority script, exactly as Community maintenance
    already does. The disposable gate proves the same function.
    """

    AUTHORITY = ROOT / "scripts" / "configure_interview_telemetry_sql_authority.py"
    PROOF = ROOT / "scripts" / "interview_ai" / "run_interview_telemetry_sql_proof.py"
    # T-SQL is case-insensitive, so the probe is too; comments are
    # stripped first so prose can neither hide a statement nor trip it.
    SECURITY_STATEMENTS = re.compile(
        r"\b(CREATE\s+ROLE|ALTER\s+ROLE|DROP\s+ROLE|GRANT|DENY|REVOKE"
        r"|CREATE\s+USER|ALTER\s+USER|DROP\s+USER|ALTER\s+AUTHORIZATION"
        r"|CREATE\s+SCHEMA|EXECUTE\s+AS|sp_addrolemember|sp_droprolemember"
        r"|sp_addsrvrolemember)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _statements_only(sql):
        without_blocks = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
        return re.sub(r"--[^\r\n]*", " ", without_blocks)

    def test_comment_stripping_and_case_folding_are_real(self):
        # Negative controls: the probe must fire on lowercase statements
        # and must NOT fire on statements that live only inside comments.
        self.assertEqual(
            [m.upper() for m in self.SECURITY_STATEMENTS.findall(
                self._statements_only("create role x; /* GRANT y */ -- DENY z"))],
            ["CREATE ROLE"],
        )

    def test_forward_migration_carries_schema_only(self):
        self.assertEqual(
            self.SECURITY_STATEMENTS.findall(
                self._statements_only(FORWARD_SQL.read_text(encoding="utf-8"))
            ),
            [],
            "the forward migration must not create roles, users or grants: the "
            "governed apply identity cannot execute them",
        )

    def test_rollback_carries_no_role_teardown(self):
        self.assertEqual(
            self.SECURITY_STATEMENTS.findall(
                self._statements_only(ROLLBACK_SQL.read_text(encoding="utf-8"))
            ),
            [],
        )

    def test_rollback_is_recorded_as_administrator_run(self):
        # The empty-table guard reads the table, which db_ddladmin cannot;
        # the rollback file and the release plan must both say so.
        rollback = ROLLBACK_SQL.read_text(encoding="utf-8")
        self.assertIn("runs as the administrator", rollback)
        plan = (EVIDENCE_DIR / "10_RELEASE_PLAN.md").read_text(encoding="utf-8")
        self.assertIn("Administrator-run rollback", plan)

    def test_authority_script_owns_roles_grants_and_memberships(self):
        self.assertTrue(self.AUTHORITY.is_file())
        source = self.AUTHORITY.read_text(encoding="utf-8")
        for expected in (
            "interview_telemetry_append",
            "interview_telemetry_maintenance",
            APPEND_PROCEDURE,
            PURGE_PROCEDURE,
            "CREATE ROLE",
            "GRANT EXECUTE ON OBJECT::dbo.",
            "TYPE = E",
            "ALTER ROLE",
            "--confirm-apply",
            'ALLOWED_DATABASE = "peerslate-database"',
            "def ensure_roles_and_grants",
            "def ensure_application_denies",
            "DENY EXECUTE ON OBJECT::dbo.",
            "DENY SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.",
        ):
            self.assertIn(expected, source, expected)
        # Exactly one grant per role, each to its own procedure, never a table.
        self.assertIn(
            "(APPEND_ROLE, APPEND_PROCEDURE),", source
        )
        self.assertIn(
            "(MAINTENANCE_ROLE, PURGE_PROCEDURE),", source
        )
        # The only GRANT verb in the script is EXECUTE; the table is
        # touched only by DENY.
        self.assertEqual(
            set(re.findall(r"\bGRANT\s+([A-Z]+)", source)), {"EXECUTE"}
        )
        self.assertIn("DENY SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.{TELEMETRY_TABLE}", source)
        # The script connects as the Entra administrator and never reads a
        # credential: SQL-auth cannot impersonate an EXTERNAL_USER.
        self.assertIn("Authentication=ActiveDirectoryDefault", source)
        self.assertNotIn("get_connection", source)
        self.assertNotIn("AZURE_SQL_CONNECTIONSTRING", source)
        self.assertNotIn("--env-file", source)
        # Every failure path reports an exception class, never raw text.
        self.assertNotIn("import traceback", source)
        self.assertGreaterEqual(source.count('"error_class": type(error).__name__'), 3)
        # The Community maintenance identity is named only to assert its absence.
        self.assertNotIn(
            "ADD MEMBER [peerslate-community-maintenance]", source
        )

    def test_authority_script_never_dispatches_to_a_provider(self):
        source = self.AUTHORITY.read_text(encoding="utf-8").lower()
        self.assertNotIn("anthropic", source)
        self.assertNotIn("messages.create", source)

    def test_proof_tool_binds_roles_through_the_authority_module(self):
        source = self.PROOF.read_text(encoding="utf-8")
        self.assertIn(
            "from configure_interview_telemetry_sql_authority import", source
        )
        self.assertIn("ensure_roles_and_grants(cursor)", source)
        self.assertNotIn("CREATE ROLE", source)
        # Round 2: apply() and verify() run end to end on stand-ins, and
        # the recorded proof carries the end-to-end result.
        self.assertIn("authority_apply(", source)
        self.assertIn("authority_verify(", source)
        self.assertEqual(
            DISPOSABLE_PROOF["checks"].get("authority_apply_and_verify_end_to_end"),
            "pass",
        )
        self.assertEqual(
            DISPOSABLE_PROOF["checks"].get(
                "authority_verify_maintenance_principal_external_with_expected_sid"),
            "pass",
        )

    def test_authority_script_refuses_apply_without_confirmation(self):
        completed = subprocess.run(
            [sys.executable, str(self.AUTHORITY), "apply",
             "--maintenance-client-id", "00000000-0000-0000-0000-000000000000"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(completed.returncode, 2, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "refused")
        self.assertIn("--confirm-apply", report["reason"])

    def test_authority_script_refuses_a_malformed_client_id(self):
        completed = subprocess.run(
            [sys.executable, str(self.AUTHORITY), "verify",
             "--maintenance-client-id", "not-a-guid"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["result"], "refused")


class SeparationTests(unittest.TestCase):
    """No runtime, provider, or B3 material entered this branch."""

    def test_no_interview_runtime_package_is_present(self):
        self.assertFalse((ROOT / "services" / "interview_ai").exists())
        self.assertFalse((ROOT / "prompts" / "interview").exists())
        self.assertFalse((ROOT / "tests" / "interview_ai").exists())

    def test_no_parity_oracle_is_copied_here(self):
        # The runtime parity oracle stays on the runtime branch.
        self.assertFalse(
            (ROOT / "tests" / "interview_ai" / "fixtures" / "parity").exists()
        )

    def test_pipeline_carries_no_runtime_lock_material(self):
        for marker in (
            "interview-runtime-lock.txt",
            "interview-runtime-constraints.txt",
            "interview-runtime-vendor-args.txt",
            "verify_staged_runtime",
            "--require-hashes",
            ".python_packages",
        ):
            self.assertNotIn(marker, PIPELINE, marker)

    def test_this_branch_dispatches_to_no_provider(self):
        for script in sorted(
            (ROOT / "scripts" / "interview_ai").glob("*.py")
        ):
            source = script.read_text(encoding="utf-8")
            self.assertNotIn("anthropic", source.lower(), script.name)
            self.assertNotIn("messages.create", source, script.name)

    def test_only_the_two_telemetry_scripts_are_present(self):
        names = sorted(
            path.name
            for path in (ROOT / "scripts" / "interview_ai").glob("*.py")
        )
        self.assertEqual(
            names,
            [
                "run_interview_telemetry_purge.py",
                "run_interview_telemetry_sql_proof.py",
            ],
        )


class BoundedOperationTests(unittest.TestCase):
    """The purge and proof tools refuse unsafe invocations, offline."""

    def _run(self, script, *arguments, env=None):
        environment = dict(os.environ)
        environment.pop("INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING", None)
        environment.pop(
            "INTERVIEW_TELEMETRY_SQL_PROOF_CONNECTIONSTRING", None
        )
        if env:
            environment.update(env)
        return subprocess.run(
            [sys.executable,
             str(ROOT / "scripts" / "interview_ai" / script), *arguments],
            capture_output=True, text=True, cwd=str(ROOT), env=environment,
            timeout=120,
        )

    def test_purge_refuses_a_malformed_database_name(self):
        # Correction C4: this asserts MALFORMED-name rejection (a space is
        # not a legal identifier character), not production-name rejection.
        result = self._run(
            "run_interview_telemetry_purge.py",
            "--expect-database", "peerslate database",
        )
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "refused")
        self.assertEqual(payload["reason"], "invalid_expected_database")

    def test_purge_refuses_out_of_bounds_batches(self):
        for flag, value in (("--batch-size", "0"), ("--batch-size", "5001"),
                            ("--max-batches", "0"), ("--max-batches", "1001")):
            result = self._run(
                "run_interview_telemetry_purge.py",
                "--expect-database", "ps-disposable-proof",
                flag, value,
            )
            self.assertNotEqual(result.returncode, 0, (flag, value))
            payload = json.loads(result.stdout)
            self.assertEqual(payload["result"], "refused")
            self.assertIn(
                payload["reason"],
                ("batch_size_out_of_bounds", "batch_count_out_of_bounds"),
                (flag, value),
            )

    def test_purge_refuses_without_its_dedicated_connection(self):
        result = self._run(
            "run_interview_telemetry_purge.py",
            "--expect-database", "ps-disposable-proof",
        )
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "refused")
        self.assertEqual(payload["reason"], "connection_not_configured")

    def test_sql_proof_tool_refuses_a_production_named_database(self):
        result = self._run(
            "run_interview_telemetry_sql_proof.py",
            "--expect-database", "peerslate-database",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refused", result.stdout)


FAKE_DRIVER = '''
import json, os

MODE = set(os.environ.get("FAKE_MODE", "ok").split(","))
TRACE = os.environ.get("FAKE_TRACE")
DB = os.environ.get("FAKE_DB_NAME", "ps-disposable-proof")
MARKER = os.environ["FAKE_MARKER"]


def _record(event):
    if TRACE:
        with open(TRACE, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\\n")


class _Cursor:
    def __init__(self):
        self._rows = [(None,)]
        self._last = ""

    def execute(self, statement, *args):
        _record({"execute": statement})
        self._last = statement
        if "DB_NAME" in statement:
            if "dbname_raise" in MODE:
                raise RuntimeError(MARKER)
            self._rows = [(DB,)]
        elif "usp_PurgeInterviewAIServerCalls" in statement:
            if "purge_raise" in MODE:
                raise RuntimeError(MARKER)
            self._rows = [(5, 1, 1000, False)]

    def fetchone(self):
        if "result_unreadable" in MODE and "Purge" in self._last:
            raise RuntimeError(MARKER)
        return self._rows[0]


class _Connection:
    def cursor(self):
        _record({"cursor": True})
        if "cursor_raise" in MODE:
            raise RuntimeError(MARKER)
        return _Cursor()

    def commit(self):
        _record({"commit": True})
        if "commit_raise" in MODE:
            raise RuntimeError(MARKER)

    def close(self):
        _record({"close": True})
        if "close_raise" in MODE:
            raise RuntimeError(MARKER)


def connect(connection_string, timeout=None):
    _record({"connect": True})
    if "connect_raise" in MODE:
        raise RuntimeError(MARKER)
    return _Connection()
'''

BROKEN_DRIVER = 'raise ImportError(__import__("os").environ["FAKE_MARKER"])\n'


class PurgeFailureContractTests(unittest.TestCase):
    """Correction C1: every stage fails bounded, content-free, nonzero."""

    MARKER = "RAWMARKER-Server=tcp:hidden.example.net;Password=hunter2"

    def _run_with_fake(self, mode, driver=FAKE_DRIVER, db_name=None,
                       expect_database="ps-disposable-proof"):
        import tempfile
        with tempfile.TemporaryDirectory() as fake_root:
            (Path(fake_root) / "mssql_python.py").write_text(
                driver, encoding="utf-8"
            )
            trace = Path(fake_root) / "trace.jsonl"
            environment = dict(os.environ)
            environment.update({
                "PYTHONPATH": fake_root,
                "FAKE_MODE": mode,
                "FAKE_TRACE": str(trace),
                "FAKE_MARKER": self.MARKER,
                "INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING":
                    "Server=tcp:hidden.example.net;Password=hunter2",
            })
            if db_name:
                environment["FAKE_DB_NAME"] = db_name
            result = subprocess.run(
                [sys.executable,
                 str(ROOT / "scripts" / "interview_ai"
                     / "run_interview_telemetry_purge.py"),
                 "--expect-database", expect_database],
                capture_output=True, text=True, cwd=str(ROOT),
                env=environment, timeout=120,
            )
            events = []
            if trace.is_file():
                events = [
                    json.loads(line)
                    for line in trace.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            return result, events

    def _assert_bounded(self, result, expected_reason, expected_result):
        # Valid JSON on stdout, exactly one object.
        self.assertEqual(len(result.stdout.strip().splitlines()), 1,
                         "expected exactly one JSON line")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], expected_result)
        self.assertEqual(payload["reason"], expected_reason)
        # Closed field set and closed enums.
        from importlib.machinery import SourceFileLoader
        module = SourceFileLoader(
            "purge_contract",
            str(ROOT / "scripts" / "interview_ai"
                / "run_interview_telemetry_purge.py"),
        ).load_module()
        self.assertLessEqual(set(payload), set(module.REPORT_FIELDS))
        self.assertIn(payload["reason"], module.REASONS)
        self.assertIn(payload["result"], module.RESULTS)
        # Nonzero exit, empty stderr, no traceback, no injected raw marker.
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), "")
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        self.assertNotIn(self.MARKER, result.stdout + result.stderr)
        self.assertNotIn("hunter2", result.stdout + result.stderr)
        return payload

    def test_dependency_import_failure_is_bounded(self):
        result, _ = self._run_with_fake(
            "ok", driver=BROKEN_DRIVER,
        )
        self._assert_bounded(result, "dependency_unavailable", "failed")

    def test_connection_failure_is_bounded(self):
        result, _ = self._run_with_fake("connect_raise")
        self._assert_bounded(result, "connection_failed", "failed")

    def test_cursor_failure_is_bounded(self):
        result, _ = self._run_with_fake("cursor_raise")
        self._assert_bounded(result, "cursor_failed", "failed")

    def test_database_verification_failure_is_bounded(self):
        result, _ = self._run_with_fake("dbname_raise")
        self._assert_bounded(result, "database_verification_failed", "failed")

    def test_purge_execution_failure_is_bounded(self):
        result, _ = self._run_with_fake("purge_raise")
        self._assert_bounded(result, "purge_failed", "failed")

    def test_result_parsing_failure_is_bounded(self):
        result, _ = self._run_with_fake("result_unreadable")
        self._assert_bounded(result, "result_unreadable", "failed")

    def test_commit_failure_is_bounded(self):
        result, _ = self._run_with_fake("commit_raise")
        self._assert_bounded(result, "commit_failed", "failed")

    def test_close_failure_is_bounded(self):
        result, _ = self._run_with_fake("close_raise")
        payload = self._assert_bounded(result, "close_failed", "failed")
        # The purge did commit, so its true counts are still reported.
        self.assertEqual(payload["deleted_rows"], 5)

    def test_purge_and_close_failing_together_yield_one_report(self):
        """Fix 2: an operational failure plus a close failure still emit
        exactly one bounded report, and the operational reason wins."""
        result, _ = self._run_with_fake("purge_raise,close_raise")
        payload = self._assert_bounded(result, "purge_failed", "failed")
        self.assertNotIn("close_failed", result.stdout)

    def test_commit_and_close_failing_together_yield_one_report(self):
        result, _ = self._run_with_fake("commit_raise,close_raise")
        self._assert_bounded(result, "commit_failed", "failed")
        self.assertNotIn("close_failed", result.stdout)

    def test_wrong_target_and_close_failure_still_refuse_once(self):
        result, events = self._run_with_fake(
            "close_raise", db_name="some-other-database",
        )
        payload = self._assert_bounded(result, "unexpected_database",
                                       "refused")
        self.assertEqual(payload["result"], "refused")
        executed = [event.get("execute", "") for event in events]
        self.assertFalse(
            any("usp_PurgeInterviewAIServerCalls" in item
                for item in executed)
        )
        self.assertFalse(any("commit" in event for event in events))

    def test_wrong_target_database_refuses_without_purging(self):
        """Correction C4: a fake connection pointed at the wrong database
        must refuse before the purge procedure is ever invoked."""
        result, events = self._run_with_fake(
            "ok", db_name="some-other-database",
            expect_database="ps-disposable-proof",
        )
        payload = self._assert_bounded(result, "unexpected_database",
                                       "refused")
        self.assertEqual(payload["result"], "refused")
        executed = [event.get("execute", "") for event in events]
        self.assertTrue(any("DB_NAME" in item for item in executed))
        # The purge procedure is never invoked, and nothing is committed.
        self.assertFalse(
            any("usp_PurgeInterviewAIServerCalls" in item
                for item in executed),
            "the purge procedure was invoked against the wrong database",
        )
        self.assertFalse(any("commit" in event for event in events),
                         "a commit occurred against the wrong database")
        # No connection detail is emitted.
        self.assertNotIn("hidden.example.net",
                         result.stdout + result.stderr)

    def test_successful_run_reports_counts_and_exits_zero(self):
        result, events = self._run_with_fake("ok")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "pass")
        self.assertEqual(payload["deleted_rows"], 5)
        self.assertEqual(result.stderr.strip(), "")
        self.assertTrue(any("commit" in event for event in events))


class PipelineReportGuaranteeTests(unittest.TestCase):
    """C1: a valid content-free report exists before the enabled path."""

    def _stage_body(self):
        pattern = re.compile(
            r"(?ms)^  - stage: InterviewTelemetryMaintenance\b.*?"
            r"(?=^  - stage: |\Z)"
        )
        match = pattern.search(PIPELINE)
        self.assertIsNotNone(match)
        return match.group(0)

    def test_a_fallback_report_is_written_before_install_or_purge(self):
        body = self._stage_body()
        guarantee = body.index("Guarantee a content-free retention report")
        install = body.index("Install and verify purge dependencies")
        purge = body.index("Run the default-off bounded retention purge")
        self.assertLess(guarantee, install)
        self.assertLess(guarantee, purge)
        self.assertIn("purge_did_not_run", body)

    def test_the_fallback_reason_is_in_the_closed_enum(self):
        from importlib.machinery import SourceFileLoader
        module = SourceFileLoader(
            "purge_contract_enum",
            str(ROOT / "scripts" / "interview_ai"
                / "run_interview_telemetry_purge.py"),
        ).load_module()
        self.assertIn("purge_did_not_run", module.REASONS)

    def test_operative_steps_preserve_prior_step_success(self):
        body = self._stage_body()
        # Every enable-gated step must also require succeeded(); an
        # enable check alone would run after an earlier failure.
        for condition in re.findall(
            r"condition: >-\s*\n\s*and\(([^)]*(?:\)[^)]*)*?)\n\s*\)", body
        ):
            if "interviewTelemetryMaintenanceEnabled" in condition:
                self.assertIn("succeeded()", condition)
        self.assertEqual(
            body.count("eq(variables['interviewTelemetryMaintenanceEnabled'],"
                       " 'true')"),
            2,
            "expected exactly the install and purge steps to be enable-gated",
        )


class ContentFreeEvidenceTests(unittest.TestCase):
    """Evidence carries no secret, connection, member, or model content."""

    # Value-bearing shapes only. A bare word like "secret" appears in
    # prose that ASSERTS absence ("no secret ... appears in this
    # record"); banning the word would fail on its own denial. What must
    # never appear is a credential or connection VALUE, so the patterns
    # below require an assignment or a known credential prefix.
    FORBIDDEN_PATTERNS = (
        r"(?:password|pwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*\S",
        r"connection\s*string\s*[:=]\s*\S",
        r"server\s*=\s*tcp:",
        r"\bbearer\s+[A-Za-z0-9._-]{8,}",
        r"\bsk-ant-[A-Za-z0-9_-]+",
        r"(?m)^\s*(?:traceback \(most recent call last\)|\s*File \".*\", line \d+)",
    )

    def _evidence_files(self):
        for name in (
            "05_SQL_DISPOSABLE_PROOF.json",
            "11_DARK_TELEMETRY_INFRASTRUCTURE_EVIDENCE.md",
        ):
            path = EVIDENCE_DIR / name
            if path.is_file():
                yield path

    def test_evidence_files_are_content_free(self):
        for path in self._evidence_files():
            lowered = path.read_text(encoding="utf-8").lower()
            for pattern in self.FORBIDDEN_PATTERNS:
                match = re.search(pattern, lowered)
                self.assertIsNone(
                    match,
                    "%s leaks %r via %s"
                    % (path.name, match.group(0) if match else "", pattern),
                )

    def test_the_content_free_scanner_actually_catches_a_leak(self):
        # Negative control: the patterns above must fire on real
        # credential shapes, so a passing scan means something.
        for leak in (
            "password=hunter2",
            "Server=tcp:peerslate.database.windows.net,1433",
            "Authorization: Bearer abcdefghijklmnop",
            "sk-ant-api03-EXAMPLEONLY",
            'api_key: "abc123"',
        ):
            lowered = leak.lower()
            self.assertTrue(
                any(re.search(p, lowered) for p in self.FORBIDDEN_PATTERNS),
                "scanner missed %r" % leak,
            )

    def test_disposable_proof_records_only_named_check_outcomes(self):
        for name, value in DISPOSABLE_PROOF["checks"].items():
            self.assertIsInstance(value, str)
            self.assertTrue(
                value == "pass" or value.startswith("FAIL"),
                "%s carries something other than an outcome" % name,
            )
        self.assertEqual(DISPOSABLE_PROOF["result"], "pass")

    def test_purge_report_shape_is_counts_only(self):
        source = (
            ROOT / "scripts" / "interview_ai"
            / "run_interview_telemetry_purge.py"
        ).read_text(encoding="utf-8")
        # The report is assembled from integer counts; no row content, no
        # exception text, and no connection detail may be printed. The
        # traceback machinery is never imported, and no bare exception
        # object is ever formatted into output.
        self.assertIn("batches_run", source)
        # Statement-anchored: the docstring legitimately SAYS the words
        # "import traceback" while forbidding the act.
        self.assertIsNone(
            re.search(r"(?m)^\s*import traceback\b", source)
        )
        self.assertNotIn("print_exc", source)
        self.assertNotIn("format_exc", source)
        self.assertNotIn("print(connection_string", source)
        self.assertNotIn("str(error", source)
        self.assertNotIn("%s\" % error", source)


if __name__ == "__main__":
    unittest.main()
