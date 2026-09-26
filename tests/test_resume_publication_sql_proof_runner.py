"""SQL proof runner: plan default, execute gated, fabricated auth never connects."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_resume_publication_sql_proof import (
    authorization_permits_execute,
    execute_proof,
    main,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_resume_publication_sql_proof.py"


def _record_proof_rollback(order, identity):
    order.append(("rollback", identity))
    if identity.endswith("PeerSlateMvp1EFPopulated_20260916_01"):
        raise RuntimeError("54120 Rollback refused: publication state is populated.")


def _record_proof_forward(order, identity):
    from tests.test_resume_publication_sql_engine import _simulated_capture_forward
    order.append(("forward", identity))
    return _simulated_capture_forward(identity)


class ResumePublicationSqlProofRunnerTests(unittest.TestCase):
    def test_capture_guard_hook_only_runs_at_first_exact_empty_capture_boundary(self):
        from scripts.run_resume_publication_sql_proof import _migration_callables
        from services.resume_publication_adapters import PROOF_EMPTY_DATABASE, PROOF_POPULATED_DATABASE
        order = []
        closure = [{"id": name, "forward": f"{name}.sql"}
                   for name in ("PS-AUTH-001", "PS-CAPTURE-001", "PS-CAPTURE-002")]

        class Connection:
            def close(self):
                pass

        def proof(connection):
            order.append("guard")
            return {"cases": "observed"}

        with patch("services.resume_publication_adapters.apply_sql_file",
                   side_effect=lambda connection, path: order.append(path.name)), \
             patch("services.resume_publication_adapters.run_capture_rollback_contracts", side_effect=proof):
            forward, _, _ = _migration_callables(closure, lambda identity: Connection(), "docker:proof", None, None, None)
            first = forward(f"docker:proof:{PROOF_EMPTY_DATABASE}")
            self.assertEqual(first, {"capture_rollback": {"cases": "observed"}})
            self.assertEqual(order, ["PS-AUTH-001.sql", "PS-CAPTURE-001.sql", "guard", "PS-CAPTURE-002.sql"])
            for identity in (f"docker:proof:{PROOF_EMPTY_DATABASE}", f"docker:proof:{PROOF_POPULATED_DATABASE}",
                             f"docker:other:{PROOF_EMPTY_DATABASE}"):
                order.clear()
                self.assertEqual(forward(identity), {})
                self.assertEqual(order, ["PS-AUTH-001.sql", "PS-CAPTURE-001.sql", "PS-CAPTURE-002.sql"])

    def test_plan_emits_hashes_and_does_not_execute(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--plan"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "proposal_not_executed")
        self.assertFalse(payload["execute_authorized"])
        self.assertFalse(payload["client_dsn_accepted"])
        self.assertTrue(payload["prepared_not_executed"])
        self.assertEqual(payload["proof_id"], "ps-mvp1-ef-sql-proof-20260916-01")
        self.assertIn("PS-PLAT-000", payload["migrations"])
        self.assertIn("PS-RESUME-MEDIA-001", payload["migrations"])
        self.assertGreaterEqual(len(payload["closure"]), 20)
        self.assertGreaterEqual(len(payload["files"]), 8)
        self.assertIn("codec_and_evidence", payload["steps"])
        self.assertEqual(payload["python"], "3.12")
        self.assertTrue(payload["client_oracles"])
        for item in payload["files"]:
            self.assertEqual(len(item["sha256"]), 64)
        self.assertFalse(payload["dependency_hashes_recorded_at_execute"])
        lock = payload["dependency_lock"]
        self.assertEqual(lock["source"], "pypi_published_metadata")
        self.assertTrue(lock["install_requires_hashes"])
        self.assertFalse(lock["downloaded_bytes_independently_verified"])
        requirements = (ROOT / "requirements-resume-publication-sql-proof.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("azure-identity==1.25.3", requirements)
        self.assertIn(
            "d9ed6e3a3b4bbfb8acb18946de0919ca7b83e8456fa8cf78f668ef89f476f093",
            requirements,
        )
        self.assertIn("--hash=sha256:", requirements)
        self.assertNotIn("recorded at execute", requirements.lower())

    def test_execute_without_authorization_refuses_without_contacting_resources(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--execute"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stderr)
        self.assertEqual(payload["status"], "refused")
        self.assertFalse(payload["contacted_resources"])

    def test_missing_or_mismatched_queue_inputs_refuse_before_resources(self):
        self.assertFalse(authorization_permits_execute("fabricated-owner-ref"))
        with patch.dict(
            "os.environ",
            {
                "PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_EXECUTE": "authorized",
                "PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_ID": "ps-mvp1-ef-sql-proof-20260916-01",
                "PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_AUTHORIZATION": "other-ref",
            },
            clear=False,
        ):
            self.assertFalse(authorization_permits_execute("fabricated-owner-ref"))
        with patch.object(sys, "argv", ["prog", "--execute", "--authorization-ref", "fabricated-owner-ref"]):
            with patch("scripts.run_resume_publication_sql_proof.execute_proof") as mocked:
                status = main(
                    ["--execute", "--authorization-ref", "fabricated-owner-ref"]
                )
        self.assertEqual(status, 2)
        mocked.assert_not_called()

    def test_matching_queue_inputs_are_not_independent_owner_approval(self):
        env = {
            "PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_EXECUTE": "authorized",
            "PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_ID": "ps-mvp1-ef-sql-proof-20260916-01",
            "PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_AUTHORIZATION": "fabricated-not-owner-approved",
        }
        with patch.dict("os.environ", env, clear=False):
            # The dispatcher must separately verify Pete's decision before
            # setting these values. Matching text alone passes this shape gate.
            self.assertTrue(authorization_permits_execute("fabricated-not-owner-approved"))
            with patch(
                "scripts.run_resume_publication_sql_proof.execute_proof",
                return_value=0,
            ) as mocked:
                status = main(
                    [
                        "--execute",
                        "--authorization-ref",
                        "fabricated-not-owner-approved",
                        "--source-sha",
                        "abc",
                        "--evidence",
                        str(ROOT / "tmp-not-written.json"),
                    ]
                )
        self.assertEqual(status, 0)
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.kwargs["authorization_ref"], "fabricated-not-owner-approved")
        self.assertIs(execute_proof, execute_proof)

    def test_execute_proof_body_runs_oracles_with_injected_adapters(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from tests.test_resume_publication_sql_engine import _EngineConnection

        _EngineConnection.reset()
        connections = []

        def connect(identity):
            connections.append(identity)
            self.assertFalse(identity.startswith("Driver="))
            return _EngineConnection(identity)

        order = []
        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            status = execute_proof(
                "injected-oracle",
                evidence,
                connect=connect,
                apply_forward=lambda identity: _record_proof_forward(order, identity),
                apply_rollback=lambda identity: _record_proof_rollback(order, identity),
                verify=lambda identity: order.append(("verify", identity)),
            )
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(status, 0, payload)
        self.assertEqual(payload["status"], "pass")
        self.assertFalse(payload["prepared_not_executed"])
        self.assertEqual(
            [step for step, _identity in order],
            [
                "forward",
                "verify",
                "rollback",
                "forward",
                "verify",
                "forward",
                "verify",
                "verify",
                "verify",
                "verify",
                "verify",
                "forward",
                "verify",
                "verify",
                "rollback",
                "verify",
            ],
        )
        self.assertTrue(all(identity.endswith("PeerSlateMvp1EFEmpty_20260916_01") for _step, identity in order[:-5]))
        self.assertTrue(all(identity.endswith("PeerSlateMvp1EFPopulated_20260916_01") for _step, identity in order[-5:]))
        self.assertTrue(payload["oracles"]["injected_rollback"]["injected_after_writes"])
        self.assertTrue(payload["oracles"]["two_connection_race"]["interleaved"])
        self.assertTrue(payload["oracles"]["codec_and_evidence"]["equal"])
        self.assertTrue(payload["oracles"]["permissions"]["internal_denied_present"])
        self.assertTrue(payload["oracles"]["correction_wording"]["changed"])
        self.assertEqual(payload["oracles"]["correction_wording"]["after"], "Led team 1.")
        self.assertIn("PS-PLAT-000", payload["closure_ids"])

    def test_driver_uuid_receipt_survives_nested_success_and_failure_evidence(self):
        from tempfile import TemporaryDirectory
        from uuid import UUID

        from scripts.run_resume_publication_sql_proof import (
            _write_evidence,
            execute_in_client_oracles,
        )
        from services.resume_publication_adapters import capture_publication_state

        request_id = UUID("00000000-0000-4000-8000-0000000000e1")

        class Cursor:
            def execute(self, statement, params=None):
                if "FROM dbo.resume_publication_receipts" in statement:
                    self.rows = [(1, request_id, "publish", "committed")]
                elif "SELECT COUNT(*)" in statement:
                    self.rows = [(1,)]
                else:
                    self.rows = []

            def fetchall(self):
                return self.rows

            def close(self):
                pass

        class Connection:
            def cursor(self):
                return Cursor()

        snapshot = capture_publication_state(Connection())
        self.assertIsInstance(snapshot["receipts"][0][1], UUID)
        oracles = {
            "two_connection_race": {"final_state": snapshot},
            "injected_rollback": {"before": snapshot, "after": snapshot},
        }

        def observed_oracles(*args, **kwargs):
            return {"oracles": oracles}

        with TemporaryDirectory() as directory:
            success_path = Path(directory) / "success.json"
            with patch(
                "services.resume_publication_adapters.run_publication_sql_oracles",
                new=observed_oracles,
            ):
                status = execute_in_client_oracles(
                    "synthetic-source", success_path, connect=lambda identity: Connection()
                )
            self.assertEqual(status, 0)
            success = json.loads(success_path.read_text(encoding="utf-8"))

            failure_path = Path(directory) / "failure.json"
            original_write_text = Path.write_text
            attempts = []

            def fail_first_write(path, *args, **kwargs):
                if path == failure_path and not attempts:
                    attempts.append("failed")
                    raise OSError("synthetic evidence write interruption")
                return original_write_text(path, *args, **kwargs)

            with patch(
                "services.resume_publication_adapters.run_publication_sql_oracles",
                new=observed_oracles,
            ), patch.object(Path, "write_text", new=fail_first_write):
                status = execute_in_client_oracles(
                    "synthetic-source", failure_path, connect=lambda identity: Connection()
                )
            self.assertEqual(status, 1)
            failure = json.loads(failure_path.read_text(encoding="utf-8"))
            self.assertEqual(failure["status"], "fail")
            self.assertIn("synthetic evidence write interruption", failure["error"])

            for payload in (success, failure):
                nested = payload["oracles"]
                self.assertEqual(
                    nested["two_connection_race"]["final_state"]["receipts"][0][1],
                    str(request_id),
                )
                self.assertEqual(
                    nested["injected_rollback"]["before"]["receipts"][0][1],
                    str(request_id),
                )
                self.assertEqual(
                    nested["injected_rollback"]["after"]["receipts"][0][1],
                    str(request_id),
                )
            with self.assertRaisesRegex(TypeError, "Unsupported proof evidence type"):
                _write_evidence(
                    Path(directory) / "unsupported.json", {"value": object()}
                )

    def test_hosted_yaml_has_authorized_execute_path(self):
        text = (ROOT / "azure-pipelines-resume-publication-sql-proof.yml").read_text(encoding="utf-8")
        self.assertIn("--plan", text)
        self.assertIn("--execute", text)
        self.assertIn("executeAuthorized", text)
        self.assertIn("authorizationRef", text)
        self.assertIn("UsePythonVersion@0", text)
        self.assertIn("3.12", text)
        self.assertIn("pip download", text)
        self.assertIn("--require-hashes", text)
        self.assertIn("--python-version 3.12", text)
        self.assertIn("manylinux_2_28_x86_64", text)
        self.assertIn("PEERSLATE_RESUME_PUBLICATION_WHEELHOUSE", text)
        self.assertIn("timeoutInMinutes: 45", text)
        self.assertIn("cancelTimeoutInMinutes: 5", text)
        self.assertIn("dependsOn: ResumePublicationSqlProofPlan", text)
        self.assertIn("condition: and(succeeded(), eq('${{ parameters.executeAuthorized }}', 'True')", text)
        self.assertIn("PublishPipelineArtifact@1", text)
        self.assertIn("condition: always()", text)
        self.assertIn("source_sha_mismatch", text)
        self.assertIn("git rev-parse HEAD", text)
        self.assertNotIn("timeoutInMinutes: 90", text)

    def test_execute_proof_sanitizes_secrets_in_failure_evidence(self):
        from tempfile import TemporaryDirectory

        secret = "invocation-local-sa-secret"
        created = []

        class BoomRuntime:
            _sql_password = secret

            def exists(self, name):
                return False

            def prepare_hashed_wheelhouse(self):
                return ROOT

            def verify_downloaded_wheelhouse(self, path):
                return {
                    "downloaded_bytes_independently_verified": True,
                    "artifact_count": 1,
                    "source": "downloaded_bytes",
                }

            def build_client_image(self, root, wheelhouse, manifest):
                return {"id": "sha256:" + "a" * 64, "marker": "ps-mvp1-ef-sql-proof-20260916-01"}

            def create_network(self, name, internal=True, marker=""):
                created.append(name)
                raise RuntimeError(
                    f"Login failed PWD={secret};MSSQL_SA_PASSWORD={secret} connection string"
                )

        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            with patch(
                "services.resume_publication_adapters.assert_reviewed_source",
                return_value="a" * 40,
            ):
                status = execute_proof("a" * 40, evidence, runtime=BoomRuntime())
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(status, 1)
        serialized = json.dumps(payload)
        self.assertNotIn(secret, serialized)
        self.assertIn("[redacted]", payload["error"])
        self.assertNotEqual(payload["error"], f"Login failed PWD={secret}")

    def test_in_client_oracles_entrypoint_runs_oracles_without_docker(self):
        from tempfile import TemporaryDirectory

        from scripts.run_resume_publication_sql_proof import execute_in_client_oracles
        from tests.test_resume_publication_sql_engine import _EngineConnection

        _EngineConnection.reset()
        identity = "docker:ps-mvp1-ef-sql-proof-20260916-01-sql"

        def connect(database_identity):
            return _EngineConnection(database_identity)

        order = []
        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            with patch.dict(
                "os.environ",
                {
                    "MSSQL_SA_PASSWORD": "client-secret",
                    "PEERSLATE_RESUME_PUBLICATION_SQL_HOST": "ps-mvp1-ef-sql-proof-20260916-01-sql",
                },
                clear=False,
            ):
                status = execute_in_client_oracles(
                    "in-client",
                    evidence,
                    connect=connect,
                    apply_forward=lambda identity: _record_proof_forward(order, identity),
                    apply_rollback=lambda identity: _record_proof_rollback(order, identity),
                    verify=lambda identity: order.append(("verify", identity)),
                )
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(status, 0, payload)
        self.assertEqual(payload["status"], "pass")
        self.assertTrue(payload["oracles"]["correction_wording"]["changed"])
        self.assertEqual(
            [step for step, _identity in order],
            [
                "forward",
                "verify",
                "rollback",
                "forward",
                "verify",
                "forward",
                "verify",
                "verify",
                "verify",
                "verify",
                "verify",
                "forward",
                "verify",
                "verify",
                "rollback",
                "verify",
            ],
        )
        self.assertTrue(all(identity.endswith("PeerSlateMvp1EFEmpty_20260916_01") for _step, identity in order[:-5]))
        self.assertTrue(all(identity.endswith("PeerSlateMvp1EFPopulated_20260916_01") for _step, identity in order[-5:]))
        self.assertNotIn("client-secret", json.dumps(payload))

    def test_migration_failures_identify_sequence_phase_and_batch_without_retry(self):
        from scripts.run_resume_publication_sql_proof import _migration_callables
        from services.resume_publication_adapters import EngineProofError

        closure = [{"id": name, "forward": f"{name}.sql", "rollback": f"{name}_rollback.sql", "verify": f"{name}_verify.sql"} for name in ("A", "B", "C")]
        for phase in ("forward", "verify", "rollback", "reapply"):
            with self.subTest(phase=phase):
                attempts = []
                closed = []
                fail = False

                class Connection:
                    def close(self):
                        closed.append(True)

                def apply_file(connection, path):
                    attempts.append(path.name)
                    if fail and path.name.startswith("B"):
                        raise EngineProofError(f"migration_file_{path.name}_failed: sql_batch_drain_failed: native 207")

                with patch("services.resume_publication_adapters.apply_sql_file", apply_file):
                    forward, rollback, verify = _migration_callables(closure, lambda identity: Connection(), "docker:proof", None, None, None)
                    if phase == "reapply":
                        forward("empty")
                        # A distinct populated database still starts at forward.
                        forward("populated")
                        attempts.clear()
                    fail = True
                    operation = {"forward": forward, "verify": verify, "rollback": rollback, "reapply": forward}[phase]
                    with self.assertRaises(EngineProofError) as caught:
                        operation("empty")
                self.assertIn(f"migration_phase_{phase}_migration_B_batch_2_failed", str(caught.exception))
                self.assertIn("sql_batch_drain_failed: native 207", str(caught.exception))
                expected = {"forward": ["A.sql", "B.sql"], "reapply": ["A.sql", "B.sql"], "verify": ["A_verify.sql", "B_verify.sql"], "rollback": ["C_rollback.sql", "B_rollback.sql"]}[phase]
                self.assertEqual(attempts, expected)
                self.assertEqual(len(closed), 3 if phase == "reapply" else 1)

    def test_failed_client_execution_is_not_reported_as_plan_only(self):
        from tempfile import TemporaryDirectory
        from scripts.run_resume_publication_sql_proof import execute_in_client_oracles

        def failing_oracle(*args, **kwargs):
            raise RuntimeError("migration failed")

        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            with patch("services.resume_publication_adapters.run_publication_sql_oracles", failing_oracle):
                status = execute_in_client_oracles("in-client-failure", evidence, connect=lambda identity: None)
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertFalse(payload["prepared_not_executed"])
        self.assertIn("migration failed", payload["error"])

    def test_authorized_supported_host_dispatches_isolated_docker_cli(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from services import resume_publication_adapters as adapters
        # Load the local driver before this test spoofs Linux for host routing;
        # its native loader uses platform.system() to choose an extension.
        from services import database_service as _database_service

        self.assertTrue(hasattr(adapters, "IsolatedDockerCliRuntime"))
        from tests.test_resume_publication_sql_engine import _EngineConnection

        _EngineConnection.reset()
        runtimes = []

        class RecordingRuntime:
            def __init__(self, *args, **kwargs):
                self.created = []
                self._sql_password = "runtime-secret-not-for-evidence"
                runtimes.append(self)

            def exists(self, name):
                return False

            def prepare_hashed_wheelhouse(self):
                self.created.append(("prepare",))
                return ROOT

            def verify_downloaded_wheelhouse(self, path):
                self.created.append(("verify_bytes", str(path)))
                return {
                    "downloaded_bytes_independently_verified": True,
                    "artifact_count": 1,
                    "source": "downloaded_bytes",
                }

            def build_client_image(self, root, wheelhouse, manifest):
                self.created.append(("build", len(manifest)))
                return {"id": "sha256:" + "a" * 64, "marker": "ps-mvp1-ef-sql-proof-20260916-01"}

            def create_network(self, name, internal=True, marker=""):
                self.created.append(("network", name, marker, internal))
                return {"id": "net-1", "marker": marker}

            def start_sql(self, name, **kwargs):
                self.created.append(("sql", name, kwargs.get("marker"), kwargs.get("publish_host_ports")))
                return {"id": "sql-1", "marker": kwargs.get("marker")}

            def start_client(self, name, **kwargs):
                self.created.append(("client", name, kwargs.get("image"), kwargs.get("publish_host_ports")))
                return {"id": "client-1", "marker": kwargs.get("marker")}

            def verify_copied_client_source(self, container, manifest):
                self.created.append(("source_digest", container))
                return manifest

            def verify_sql_identity(self, sql):
                return {
                    "production_connection": False,
                    "database": "PeerSlateMvp1EFEmpty_20260916_01",
                    "sql_build": "16.0.4265.3",
                }

            def inspect(self, name):
                marker = "ps-mvp1-ef-sql-proof-20260916-01"
                if name == "peerslate-mvp1-e-sql-proof:20260916-01":
                    return {"id": "sha256:" + "a" * 64, "marker": marker}
                if name.endswith("-client"):
                    return {"id": "client-1", "marker": marker}
                if name.endswith("-sql"):
                    return {"id": "sql-1", "marker": marker}
                return {"id": "net-1", "marker": marker}

            def remove(self, name):
                self.created.append(("remove", name))

            def resource_id_present(self, kind, resource_id):
                self.created.append(("verify_id_absent", kind, resource_id))
                return False

            def ensure_databases(self, names):
                self.created.append(("databases", tuple(names)))

            def run_client_oracles(
                self,
                *,
                source_sha="",
                apply_forward=None,
                apply_rollback=None,
                verify=None,
                codec_fields=None,
                extra_env=None,
            ):
                from services.resume_publication_adapters import (
                    run_publication_sql_oracles,
                    resolve_publication_migration_closure,
                )

                self.created.append(("client_oracles", source_sha))
                identity = "docker:ps-mvp1-ef-sql-proof-20260916-01-sql"

                def connect(database_identity):
                    return _EngineConnection(database_identity)

                ids = [item["id"] for item in resolve_publication_migration_closure()]
                return run_publication_sql_oracles(
                    identity,
                    connect,
                    apply_forward=apply_forward or (lambda identity: _record_proof_forward([], identity)),
                    apply_rollback=apply_rollback or (lambda _identity: None),
                    verify=verify or (lambda _identity: None),
                    ordered_ids=ids,
                    codec_fields=codec_fields,
                )

        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            order = []
            with patch(
                "scripts.run_resume_publication_sql_proof.platform.system",
                return_value="Linux",
            ), patch(
                "scripts.run_resume_publication_sql_proof.platform.machine",
                return_value="x86_64",
            ), patch.object(
                adapters, "IsolatedDockerCliRuntime", RecordingRuntime
            ), patch(
                "services.resume_publication_adapters.assert_reviewed_source",
                return_value="a" * 40,
            ):
                status = execute_proof(
                    "a" * 40,
                    evidence,
                    authorization_ref="test:dispatcher-verified-owner-decision",
                    apply_forward=lambda identity: _record_proof_forward(order, identity),
                    apply_rollback=lambda identity: _record_proof_rollback(order, identity),
                    verify=lambda identity: order.append(("verify", identity)),
                )
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertNotEqual(payload.get("reason"), "isolated_docker_runtime_not_dispatched")
        self.assertEqual(status, 0, payload)
        self.assertEqual(payload["status"], "pass")
        self.assertFalse(payload["prepared_not_executed"])
        self.assertEqual(
            [step for step, _identity in order],
            [
                "forward",
                "verify",
                "rollback",
                "forward",
                "verify",
                "forward",
                "verify",
                "verify",
                "verify",
                "verify",
                "verify",
                "forward",
                "verify",
                "verify",
                "rollback",
                "verify",
            ],
        )
        self.assertTrue(all(identity.endswith("PeerSlateMvp1EFEmpty_20260916_01") for _step, identity in order[:-5]))
        self.assertTrue(all(identity.endswith("PeerSlateMvp1EFPopulated_20260916_01") for _step, identity in order[-5:]))
        self.assertTrue(payload["oracles"]["correction_wording"]["changed"])
        self.assertTrue(payload["dependency_lock"]["downloaded_bytes_independently_verified"])
        self.assertTrue(runtimes)
        actions = [item[0] for item in runtimes[0].created]
        self.assertEqual(actions[:7], ["prepare", "verify_bytes", "build", "network", "sql", "client", "source_digest"])
        self.assertIn(("client", "ps-mvp1-ef-sql-proof-20260916-01-client", "sha256:" + "a" * 64, False), runtimes[0].created)
        self.assertIn("client_oracles", actions)
        self.assertIn("remove", actions)
        self.assertNotIn("job_local_connect", actions)
        self.assertIn("build", actions)
        self.assertNotIn("runtime-secret-not-for-evidence", json.dumps(payload))
        self.assertEqual(payload["cleanup_status"], "pass")
        self.assertEqual(payload["proof_status"], "pass")
        self.assertEqual(payload["approval"]["decision_ref"], "test:dispatcher-verified-owner-decision")
        self.assertFalse(payload["approval"]["independently_authenticated_by_runner"])
        self.assertEqual(len(payload["migration_closure"]), len(payload["closure_ids"]))
        self.assertTrue(all(len(item["forward_sha256"]) == 64 for item in payload["migration_closure"]))
        self.assertEqual(len(payload["acquired_resources"]), 4)
        self.assertTrue(all(item["id"] and item["marker"] for item in payload["acquired_resources"]))
        self.assertTrue(all(item["id_absent_verified"] and item["name_absent_verified"]
                            for item in payload["cleanup"]["attempts"]))
        self.assertEqual(payload["sql_identity"]["sql_build"], "16.0.4265.3")
        self.assertEqual(payload["client_image_id"], "sha256:" + "a" * 64)

    def test_client_exit_conflict_cannot_be_promoted_to_host_pass(self):
        from tempfile import TemporaryDirectory

        class Runtime:
            def run_client_oracles(self, **_kwargs):
                return {"status": "pass", "client_exit": 1, "oracles": {"claimed": True}}

        acquired = {
            "wheelhouse": {"downloaded_bytes_independently_verified": True},
            "resource_identity": "docker:synthetic-sql",
            "client_packaging": "test-only",
            "client_image_id": "sha256:" + "a" * 64,
            "invocation_marker": "test-only-marker",
            "identity": {"sql_build": "16.0.4265.3"},
        }
        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            with patch("services.resume_publication_adapters.assert_reviewed_source", return_value="a" * 40), \
                 patch("services.resume_publication_adapters.source_manifest", return_value={"proof": "a" * 64}), \
                 patch("services.resume_publication_adapters.acquire_isolated_sql_runtime", return_value=acquired), \
                 patch("services.resume_publication_adapters.cleanup_owned_resources",
                       return_value={"status": "pass", "attempts": [], "cleaned": []}) as cleanup:
                status = execute_proof("a" * 40, evidence, runtime=Runtime())
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["proof_status"], "fail")
        self.assertEqual(payload["cleanup_status"], "pass")
        cleanup.assert_called_once()

    def test_execute_proof_refuses_wrong_sha_before_acquisition(self):
        from tempfile import TemporaryDirectory

        created = []

        class Runtime:
            def exists(self, name):
                return False

            def create_network(self, name, internal=True, marker=""):
                created.append(name)
                return {"id": "net-1", "marker": marker}

        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            with patch(
                "services.resume_publication_adapters.checkout_sha",
                return_value="a" * 40,
            ):
                status = execute_proof("b" * 40, evidence, runtime=Runtime())
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(status, 1)
        self.assertEqual(created, [])
        self.assertIn("source_sha_mismatch", payload["error"])
        self.assertEqual(payload["proof_status"], "fail")
        self.assertIn("evidence.json", str(evidence))

    def test_cleanup_failure_cannot_yield_overall_success(self):
        from tempfile import TemporaryDirectory

        class Runtime:
            _sql_password = "x"
            fail_after = "network"

            def exists(self, name):
                return False

            def prepare_hashed_wheelhouse(self):
                return ROOT

            def verify_downloaded_wheelhouse(self, path):
                return {
                    "downloaded_bytes_independently_verified": True,
                    "artifact_count": 1,
                    "source": "downloaded_bytes",
                }

            def build_client_image(self, root, wheelhouse, manifest):
                return {"id": "sha256:" + "a" * 64, "marker": "ps-mvp1-ef-sql-proof-20260916-01"}

            def create_network(self, name, internal=True, marker=""):
                return {"id": "net-1", "marker": marker}

            def inspect(self, name):
                if name == "peerslate-mvp1-e-sql-proof:20260916-01":
                    return {"id": "sha256:" + "a" * 64, "marker": "ps-mvp1-ef-sql-proof-20260916-01"}
                return {"id": "net-1", "marker": "ps-mvp1-ef-sql-proof-20260916-01"}

            def remove(self, name):
                raise RuntimeError("cleanup boom")

        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            with patch(
                "services.resume_publication_adapters.assert_reviewed_source",
                return_value="a" * 40,
            ):
                status = execute_proof("a" * 40, evidence, runtime=Runtime())
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(status, 1)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["cleanup_status"], "fail")
        self.assertIn("cleanup", payload)

    def test_sigterm_during_create_attempts_bounded_owned_cleanup(self):
        import signal
        from tempfile import TemporaryDirectory

        marker = "ps-mvp1-ef-sql-proof-20260916-01.cancel"
        resources = {}

        class CancelRuntime:
            invocation_marker = marker

            def exists(self, name):
                return name in resources

            def prepare_hashed_wheelhouse(self):
                return ROOT

            def verify_downloaded_wheelhouse(self, _path):
                return {"downloaded_bytes_independently_verified": True, "artifact_count": 1, "source": "downloaded_bytes"}

            def build_client_image(self, _root, _wheelhouse, _manifest):
                name = "peerslate-mvp1-e-sql-proof:20260916-01"
                resources[name] = {"id": "sha256:" + "a" * 64, "marker": marker}
                return resources[name]

            def create_network(self, name, internal=True, marker=""):
                resources[name] = {"id": "net-1", "marker": marker}
                signal.raise_signal(signal.SIGTERM)
                raise AssertionError("signal handler did not cancel")

            def inspect(self, name):
                return resources[name]

            def remove(self, name):
                del resources[name]

        previous = signal.getsignal(signal.SIGTERM)
        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            with patch(
                "services.resume_publication_adapters.assert_reviewed_source",
                return_value="a" * 40,
            ):
                status = execute_proof(
                    "a" * 40, evidence, runtime=CancelRuntime(),
                )
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(status, 1)
        self.assertEqual(payload["proof_status"], "fail")
        self.assertEqual(payload["cleanup_status"], "pass")
        self.assertIn("proof_cancelled", payload["error"])
        self.assertEqual({item["name"] for item in payload["acquired_resources"]},
                         {"peerslate-mvp1-e-sql-proof:20260916-01", "ps-mvp1-ef-sql-proof-20260916-01-net"})
        self.assertTrue(all(item["id"] and item["marker"] for item in payload["acquired_resources"]))
        self.assertEqual({item["id"] for item in payload["cleanup"]["attempts"]},
                         {item["id"] for item in payload["acquired_resources"]})
        self.assertEqual(resources, {})
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)


if __name__ == "__main__":
    unittest.main()
