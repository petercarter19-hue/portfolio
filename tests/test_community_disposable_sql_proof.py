import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_community_disposable_sql_proof.py"
PIPELINE = ROOT / "azure-pipelines-community-sql-proof.yml"
SPEC = importlib.util.spec_from_file_location("community_sql_proof", SCRIPT)
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)


class CommunityDisposableSqlProofTests(unittest.TestCase):
    @staticmethod
    def _pipeline_sealer_source():
        source = PIPELINE.read_text(encoding="utf-8")
        marker = "set +e\n          python3 - <<'PY'\n"
        start = source.index(marker) + len(marker)
        end = source.index("\n          PY", start)
        return textwrap.dedent(source[start:end])

    @staticmethod
    def _pipeline_pass_record(source_sha):
        sql_files = {
            "forward": proof.COMMUNITY_FORWARD_PATH,
            "verifier": proof.COMMUNITY_VERIFY_PATH,
            "rollback": proof.COMMUNITY_ROLLBACK_PATH,
        }
        return {
            "schema_version": 1,
            "status": "pass",
            "classification": "disposable_x64_nonproduction_sql_runtime",
            "source_sha": source_sha,
            "sql": {
                "version": proof.SQL_BUILD,
                "edition": "Developer",
                "machine_bound": True,
            },
            "steps": [
                {"name": name, "status": "pass", "duration_seconds": 0.1}
                for name in proof.PROOF_STEPS
            ],
            "database_cleanup_confirmed": True,
            "file_sha256": {
                label: hashlib.sha256(path.read_bytes()).hexdigest()
                for label, path in sql_files.items()
            },
            "duration_seconds": 1.0,
            "contains_member_data": False,
            "production_action": False,
            "agent": {
                "os": "ubuntu-22.04",
                "architecture": "x86_64",
                "docker_version": "28.0.4",
            },
            "images": {
                "sql": proof.SQL_IMAGE,
                "client_base": proof.CLIENT_IMAGE,
                "client_artifact_id": "sha256:" + "1" * 64,
            },
            "cleanup_confirmed": True,
        }

    @staticmethod
    def _pipeline_envelope_env(temporary, artifacts, source_sha):
        return {
            "EXPECTED_SOURCE_SHA": source_sha,
            "AGENT_TEMP_DIRECTORY": str(temporary),
            "BUILD_SOURCES_DIRECTORY": str(ROOT),
            "ARTIFACT_STAGING_DIRECTORY": str(artifacts),
            "BUILD_SOURCE_BRANCH_VALUE": "refs/heads/codex/2026-08-01-community-primary-feed-sol-ultra",
            "BUILD_ID_VALUE": "12345",
            "BUILD_NUMBER_VALUE": "20260802.1",
            "DEFINITION_ID_VALUE": "987",
            "DEFINITION_NAME_VALUE": "PeerSlate Community SQL Proof",
            "ImageOS": "ubuntu22",
            "ImageVersion": "20260727.1.0",
        }

    def test_manual_pipeline_wrapper_is_source_bound_and_non_deploying(self):
        source = PIPELINE.read_text(encoding="utf-8")
        self.assertIn("trigger: none", source)
        self.assertIn("pr: none", source)
        self.assertIn("schedules: []", source)
        self.assertIn("name: expectedSourceSha", source)
        self.assertIn("vmImage: ubuntu-22.04", source)
        self.assertIn("clean: true", source)
        self.assertIn("persistCredentials: false", source)
        self.assertIn("$(Build.Reason)", source)
        self.assertIn("$(Build.SourceVersion)", source)
        self.assertIn("$(Build.SourceBranch)", source)
        self.assertIn("$(Build.BuildId)", source)
        self.assertIn("$(Build.BuildNumber)", source)
        self.assertIn("$(System.DefinitionId)", source)
        self.assertIn("$(Build.DefinitionName)", source)
        self.assertIn("$(Agent.TempDirectory)", source)
        self.assertIn("$(Build.ArtifactStagingDirectory)", source)
        self.assertNotIn("$(ImageOS)", source)
        self.assertNotIn("$(ImageVersion)", source)
        self.assertIn('${ImageOS:-}', source)
        self.assertIn('${ImageVersion:-}', source)
        self.assertIn('os.environ.get("ImageOS", "")', source)
        self.assertIn('os.environ.get("ImageVersion", "")', source)
        # The branch restriction is a shape, not a literal. It was pinned to
        # one feature branch until 2026-08-04, when that branch was
        # squash-merged and deleted and the proof became unrunnable for every
        # later change to the same SQL. Both copies of the pin are now
        # patterns; the exact-SHA binding asserted below is the real guarantee.
        self.assertNotIn("codex/2026-08-01-community-primary-feed-sol-ultra", source)
        self.assertIn("refs/heads/main|refs/heads/work/*|refs/heads/codex/*", source)
        self.assertIn("expected_branch_pattern", source)
        self.assertIn(
            r"^refs/heads/(main|work/[A-Za-z0-9._/-]+|codex/[A-Za-z0-9._/-]+)$",
            source,
        )
        self.assertIn(f'expected_sql_image = "{proof.SQL_IMAGE}"', source)
        self.assertIn(f'expected_client_base = "{proof.CLIENT_IMAGE}"', source)
        self.assertIn('record["file_sha256"] != checked_out_hashes', source)
        self.assertIn('type(record["schema_version"]) is not int', source)
        self.assertIn('sql.get("machine_bound") is not True', source)
        for path in (
            proof.COMMUNITY_FORWARD_PATH,
            proof.COMMUNITY_VERIFY_PATH,
            proof.COMMUNITY_ROLLBACK_PATH,
        ):
            self.assertIn(path.name, source)
        self.assertIn('envelope_path = output_dir / "run-envelope.json"', source)
        self.assertIn('"proof_sha256": proof_sha256', source)
        self.assertIn('"agent_image": {"os": image_os, "version": image_version}', source)
        self.assertIn(
            "sha256sum community-sql-proof-evidence.json run-envelope.json > SHA256SUMS",
            source,
        )
        self.assertIn("artifact: CommunitySqlProofEvidence", source)
        self.assertGreaterEqual(source.count("condition: always()"), 3)
        self.assertEqual(
            source.count("scripts/run_community_disposable_sql_proof.py"), 1
        )
        self.assertEqual(source.count("--execute"), 1)
        lowered = source.lower()
        for forbidden in (
            "azuresubscription",
            "connectedservicename",
            "serviceconnection",
            "azurecli@",
            "azurewebapp@",
            "kubernetes@",
            "docker@",
            "deployment:",
            "environment:",
            "persistcredentials: true",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lowered)

    def test_pipeline_sealer_binds_pass_to_checkout_and_run_envelope(self):
        source_sha = "a" * 40
        record = self._pipeline_pass_record(source_sha)
        with tempfile.TemporaryDirectory() as temporary_name, tempfile.TemporaryDirectory() as artifact_name:
            temporary = Path(temporary_name)
            artifacts = Path(artifact_name)
            (temporary / "community-sql-proof.raw.json").write_text(
                json.dumps(record), encoding="utf-8"
            )
            with mock.patch.dict(
                os.environ,
                self._pipeline_envelope_env(temporary, artifacts, source_sha),
                clear=True,
            ):
                exec(compile(self._pipeline_sealer_source(), "pipeline-sealer", "exec"), {})
            evidence = artifacts / "CommunitySqlProofEvidence"
            proof_path = evidence / "community-sql-proof-evidence.json"
            envelope = json.loads((evidence / "run-envelope.json").read_text())
            self.assertEqual(envelope["status"], "pass")
            self.assertEqual(envelope["source"]["sha"], source_sha)
            self.assertEqual(envelope["agent_image"]["os"], "ubuntu22")
            self.assertEqual(envelope["agent_image"]["version"], "20260727.1.0")
            self.assertEqual(
                envelope["proof_sha256"],
                hashlib.sha256(proof_path.read_bytes()).hexdigest(),
            )

    def test_pipeline_sealer_rejects_wrong_hash_or_unsafe_image_metadata(self):
        source_sha = "a" * 40
        for mutation, expected_code in (
            ("file_sha256", "raw_evidence_rejected"),
            ("image_version", "run_envelope_metadata_rejected"),
            ("schema_version_float", "raw_evidence_rejected"),
            ("machine_bound_int", "raw_evidence_rejected"),
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary_name, tempfile.TemporaryDirectory() as artifact_name:
                temporary = Path(temporary_name)
                artifacts = Path(artifact_name)
                record = self._pipeline_pass_record(source_sha)
                environment = self._pipeline_envelope_env(
                    temporary, artifacts, source_sha
                )
                if mutation == "file_sha256":
                    record["file_sha256"]["forward"] = "0" * 64
                elif mutation == "image_version":
                    environment["ImageVersion"] = "unsafe-secret"
                elif mutation == "schema_version_float":
                    record["schema_version"] = 1.0
                else:
                    record["sql"]["machine_bound"] = 1
                (temporary / "community-sql-proof.raw.json").write_text(
                    json.dumps(record), encoding="utf-8"
                )
                with mock.patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(SystemExit, expected_code):
                        exec(
                            compile(
                                self._pipeline_sealer_source(),
                                "pipeline-sealer",
                                "exec",
                            ),
                            {},
                        )
                evidence = artifacts / "CommunitySqlProofEvidence"
                sealed = json.loads(
                    (evidence / "community-sql-proof-evidence.json").read_text()
                )
                envelope_text = (evidence / "run-envelope.json").read_text()
                envelope = json.loads(envelope_text)
                self.assertEqual(sealed["status"], "fail")
                self.assertEqual(envelope["status"], "fail")
                self.assertEqual(envelope["failure_code"], expected_code)
                self.assertNotIn("unsafe-secret", envelope_text)

    def test_default_mode_is_inert_plan(self):
        output = io.StringIO()
        with mock.patch.object(proof.subprocess, "run") as run, mock.patch(
            "sys.stdout", output
        ):
            self.assertEqual(proof.main([]), 0)
        run.assert_not_called()
        record = json.loads(output.getvalue())
        self.assertEqual(record["status"], "plan_only")
        self.assertFalse(record["remote_execution_authorized"])
        self.assertEqual(record["steps"], list(proof.PROOF_STEPS))

    def test_exact_images_are_immutable(self):
        self.assertEqual(
            proof._validate_image(proof.SQL_IMAGE, proof.SQL_IMAGE, "sql"),
            proof.SQL_IMAGE,
        )
        self.assertEqual(
            proof._validate_image(proof.CLIENT_IMAGE, proof.CLIENT_IMAGE, "client"),
            proof.CLIENT_IMAGE,
        )
        for unsafe in (
            proof.SQL_IMAGE_TAG,
            "mcr.microsoft.com/mssql/server:2022-latest",
            "mcr.microsoft.com/mssql/server@sha256:abc",
        ):
            with self.assertRaises(proof.ProofError):
                proof._validate_image(unsafe, proof.SQL_IMAGE, "sql")

    def test_execute_host_requires_supported_ephemeral_agent(self):
        safe_env = {
            "TF_BUILD": "true",
            "AGENT_OS": "Linux",
            "AGENT_OSARCHITECTURE": "X64",
            "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED": "false",
        }
        proof.validate_execute_host(
            system="Linux",
            machine="x86_64",
            release={"ID": "ubuntu", "VERSION_ID": "22.04"},
            environ=safe_env,
        )
        cases = (
            ("Darwin", "arm64", {"ID": "macos", "VERSION_ID": "27.0"}, safe_env),
            ("Linux", "aarch64", {"ID": "ubuntu", "VERSION_ID": "22.04"}, safe_env),
            ("Linux", "x86_64", {"ID": "ubuntu", "VERSION_ID": "24.04"}, safe_env),
            ("Linux", "x86_64", {"ID": "ubuntu", "VERSION_ID": "22.04"}, {}),
            (
                "Linux",
                "x86_64",
                {"ID": "ubuntu", "VERSION_ID": "22.04"},
                {
                    **safe_env,
                    "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED": "true",
                },
            ),
            (
                "Linux",
                "x86_64",
                {"ID": "ubuntu", "VERSION_ID": "22.04"},
                {**safe_env, "AZURE_SQL_CONNECTIONSTRING": "forbidden"},
            ),
        )
        for system, machine, release, environ in cases:
            with self.subTest(system=system, machine=machine, release=release, environ=environ):
                with self.assertRaises(proof.ProofError):
                    proof.validate_execute_host(
                        system=system,
                        machine=machine,
                        release=release,
                        environ=environ,
                    )

    def test_docker_server_must_also_be_x64_linux(self):
        proof.validate_docker_server({"OSType": "linux", "Architecture": "x86_64"})
        for info in (
            {"OSType": "linux", "Architecture": "aarch64"},
            {"OSType": "windows", "Architecture": "x86_64"},
            {},
        ):
            with self.assertRaises(proof.ProofError):
                proof.validate_docker_server(info)

    def test_inside_mode_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / ".dockerenv"
            marker.touch()
            safe = {
                "CI": "true",
                "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED": "false",
                "PROOF_ID": "abcdef123456",
                "PROOF_SQL_HOST": "community-sql",
                "PROOF_SQL_EXPECTED_IP": "172.20.0.2",
                "PROOF_SQL_EXPECTED_MACHINE": "ps-community-sql-abcdef123456",
            }
            proof.validate_inside_environment(environ=safe, docker_marker=marker)
            for unsafe in (
                {},
                {**safe, "CI": "false"},
                {**safe, "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED": "true"},
                {**safe, "AZURE_SQL_CONNECTIONSTRING": "forbidden"},
                {**safe, "PROOF_SQL_HOST": "shared-sql"},
            ):
                with self.subTest(unsafe=unsafe):
                    with self.assertRaises(proof.ProofError):
                        proof.validate_inside_environment(
                            environ=unsafe, docker_marker=marker
                        )
            with self.assertRaises(proof.ProofError):
                proof.validate_inside_environment(
                    environ=safe, docker_marker=Path(directory) / "missing"
                )

    def test_inside_network_binding_rejects_public_or_mismatched_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / ".dockerenv"
            marker.touch()
            base = {
                "CI": "true",
                "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED": "false",
                "PROOF_ID": "abcdef123456",
                "PROOF_SQL_HOST": "community-sql",
                "PROOF_SQL_EXPECTED_MACHINE": "ps-community-sql-abcdef123456",
            }
            for address in ("127.0.0.1", "8.8.8.8", "2001:db8::1", "invalid"):
                with self.subTest(address=address):
                    with self.assertRaises(proof.ProofError):
                        proof.validate_inside_environment(
                            environ={**base, "PROOF_SQL_EXPECTED_IP": address},
                            docker_marker=marker,
                        )

    def test_sql_container_inspection_requires_one_private_network(self):
        names = proof._resource_names("abcdef123456")
        container_id = subprocess.CompletedProcess([], 0, "a" * 64 + "\n", "")
        network = subprocess.CompletedProcess(
            [],
            0,
            json.dumps(
                {
                    names["network"]: {
                        "IPAddress": "172.20.0.2",
                    }
                }
            ),
            "",
        )
        with mock.patch.object(proof, "_run", side_effect=(container_id, network)):
            identity = proof._inspect_sql_container(names)
        self.assertEqual(identity["ip_address"], "172.20.0.2")
        self.assertEqual(identity["machine_name"], names["sql_container"])

    def test_inside_target_binds_dns_and_reported_machine(self):
        class Cursor:
            def execute(self, _sql):
                return self

            def fetchone(self):
                return (
                    "ps-community-sql-abcdef123456",
                    proof.SQL_BUILD,
                    "Developer Edition",
                )

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def cursor(self):
                return Cursor()

        resolved = [(None, None, None, None, ("172.20.0.2", 1433))]
        with mock.patch.object(proof.socket, "getaddrinfo", return_value=resolved), mock.patch.object(
            proof.socket, "create_connection", return_value=mock.MagicMock()
        ), mock.patch.object(proof, "_connect", return_value=Connection()):
            identity = proof._validate_job_local_sql_target(
                "community-sql",
                "not-logged",
                "172.20.0.2",
                "ps-community-sql-abcdef123456",
            )
        self.assertTrue(identity["machine_bound"])
        mismatch = [(None, None, None, None, ("172.20.0.3", 1433))]
        with mock.patch.object(proof.socket, "getaddrinfo", return_value=mismatch):
            with self.assertRaises(proof.ProofError):
                proof._validate_job_local_sql_target(
                    "community-sql",
                    "not-logged",
                    "172.20.0.2",
                    "ps-community-sql-abcdef123456",
                )

    def test_forward_migration_failures_name_the_exact_file(self):
        # Each forward migration file maps to its own finite code so a failed
        # forward pass names the file rather than one opaque stage bucket.
        for filename, expected in (
            ("PS-PLAT-001_platform_governance.sql", "empty_forward_ps_plat_001"),
            ("PS-AUTH-001_identity_foundation.sql", "empty_forward_ps_auth_001"),
            (
                "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql",
                "empty_forward_ps_community_public_pilot_001",
            ),
        ):
            with self.subTest(filename=filename):
                code = proof._per_file_forward_code(Path(filename))
                self.assertEqual(code, expected)
                self.assertIn(code, proof.CHILD_FAILURE_CODES)
        # An unknown file cannot mint a new code.
        self.assertEqual(
            proof._per_file_forward_code(Path("PS-ROGUE-999_something.sql")),
            "empty_forward_unexpected",
        )
        self.assertNotIn("empty_forward_ps_rogue_999", proof.CHILD_FAILURE_CODES)
        # Every declared per-file code is inside the child allowlist.
        self.assertTrue(
            proof.FORWARD_MIGRATION_FILE_CODES <= proof.CHILD_FAILURE_CODES
        )

    def test_forward_error_numbers_map_only_within_the_allowlist(self):
        # A known engine or repository THROW number refines the per-file code.
        err = RuntimeError("[42000] ... invalid column name 'x' (207) (SQLExecDirectW)")
        self.assertEqual(proof._sql_error_number(err), 207)
        # The repository's own guard THROW ids are allowlisted.
        err = RuntimeError("... (52441) ...")
        self.assertEqual(proof._sql_error_number(err), 52441)
        # Unknown numbers are never recorded.
        err = RuntimeError("... (99999) ... (1234567) ...")
        self.assertIsNone(proof._sql_error_number(err))
        # The combined code is inside the child allowlist and content-free.
        combined = "empty_forward_ps_community_public_pilot_001_e207"
        self.assertIn(combined, proof.CHILD_FAILURE_CODES)
        self.assertTrue(proof.FORWARD_MIGRATION_ERROR_CODES <= proof.CHILD_FAILURE_CODES)
        for code in ("empty_forward_ps_plat_000_e102", combined):
            with self.subTest(code=code):
                self.assertRegex(code, r"^[a-z0-9_]{1,80}$")

    def test_connection_string_uses_odbc_keywords_the_driver_keeps(self):
        # mssql-python normalizes a fixed keyword set and silently discards
        # anything else. ADO.NET spellings (Initial Catalog, User ID,
        # Password, Connection Timeout) all normalize to None, which stripped
        # the credentials and database and made every proof run fail at login.
        built = proof._connection_string("community-sql", "PeerSlateProof_x1", "pw")
        for ado_only in ("Initial Catalog=", "User ID=", "Connection Timeout="):
            with self.subTest(keyword=ado_only):
                self.assertNotIn(ado_only, built)
        self.assertIn("Database=PeerSlateProof_x1", built)
        self.assertIn("UID=sa", built)
        self.assertIn("PWD=pw", built)
        self.assertIn("Encrypt=yes", built)
        self.assertIn("TrustServerCertificate=yes", built)
        # The master swap used by the identity and lifecycle helpers must
        # still resolve against the ODBC keyword.
        self.assertIn(
            "Database=master",
            built.replace("Database=PeerSlateProof_x1", "Database=master"),
        )

    def test_preflight_failures_are_separable_and_content_free(self):
        resolved = [(None, None, None, None, ("172.20.0.2", 1433))]
        args = ("community-sql", "not-logged", "172.20.0.2", "ps-community-sql-abcdef123456")

        # An unreachable job-local SQL port is its own code, so a network
        # problem is never mistaken for a driver or TLS problem.
        with mock.patch.object(proof.socket, "getaddrinfo", return_value=resolved), mock.patch.object(
            proof.socket, "create_connection", side_effect=OSError("route detail must not escape")
        ):
            with self.assertRaises(proof.ProofError) as caught:
                proof._validate_job_local_sql_target(*args)
        self.assertEqual(str(caught.exception), "sql_tcp_unreachable")

        # With TCP proven, a driver load, TLS, or authentication failure is a
        # separate code rather than the generic preflight bucket.
        with mock.patch.object(proof.socket, "getaddrinfo", return_value=resolved), mock.patch.object(
            proof.socket, "create_connection", return_value=mock.MagicMock()
        ), mock.patch.object(
            proof, "_connect", side_effect=RuntimeError("driver detail must not escape")
        ):
            with self.assertRaises(proof.ProofError) as caught:
                proof._validate_job_local_sql_target(*args)
        self.assertEqual(str(caught.exception), "sql_connect_failed")
        self.assertIn("sql_connect_failed", proof.CHILD_FAILURE_CODES)
        self.assertNotIn("driver detail", str(caught.exception))

        # A failure reading the server identity is a different condition.
        class BadCursor:
            def execute(self, _sql):
                raise RuntimeError("query detail must not escape")

        class BadConnection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def cursor(self):
                return BadCursor()

        with mock.patch.object(proof.socket, "getaddrinfo", return_value=resolved), mock.patch.object(
            proof.socket, "create_connection", return_value=mock.MagicMock()
        ), mock.patch.object(proof, "_connect", return_value=BadConnection()):
            with self.assertRaises(proof.ProofError) as caught:
                proof._validate_job_local_sql_target(*args)
        self.assertEqual(str(caught.exception), "sql_identity_query_failed")

        # Unreadable reviewed SQL files are distinguishable from both.
        with mock.patch.object(proof, "_sha256", side_effect=OSError):
            with self.assertRaises(proof.ProofError) as caught:
                proof._source_file_hashes()
        self.assertEqual(str(caught.exception), "sql_source_files_unreadable")

    def test_owned_object_lists_match_migration_authority(self):
        forward = proof.COMMUNITY_FORWARD_PATH.read_text(encoding="utf-8")
        rollback = proof.COMMUNITY_ROLLBACK_PATH.read_text(encoding="utf-8")
        self.assertEqual(len(proof.COMMUNITY_TABLES), 10)
        self.assertEqual(len(proof.COMMUNITY_PROCEDURES), 25)
        for name in proof.COMMUNITY_TABLES + proof.COMMUNITY_PROCEDURES:
            with self.subTest(name=name):
                self.assertIn(f"N'{name}'", forward)
                self.assertIn(f"N'{name}'", rollback)

    def test_source_sha_must_match_checked_out_head(self):
        source_sha = "a" * 40
        head = subprocess.CompletedProcess([], 0, source_sha + "\n", "")
        clean = subprocess.CompletedProcess([], 0, "", "")
        with mock.patch.object(proof, "_run", side_effect=(head, clean)):
            self.assertEqual(proof._validate_source_sha_at_head(source_sha), source_sha)
        mismatch = subprocess.CompletedProcess([], 0, "b" * 40 + "\n", "")
        with mock.patch.object(proof, "_run", return_value=mismatch):
            with self.assertRaises(proof.ProofError):
                proof._validate_source_sha_at_head(source_sha)
        dirty = subprocess.CompletedProcess([], 0, " M migration.sql\n", "")
        with mock.patch.object(proof, "_run", side_effect=(head, dirty)):
            with self.assertRaises(proof.ProofError):
                proof._validate_source_sha_at_head(source_sha)

    def test_every_checked_outer_boundary_has_finite_command_mappings(self):
        self.assertEqual(
            proof.CHECKED_OUTER_COMMAND_BOUNDARIES,
            {
                "source_head",
                "source_status",
                "docker_info",
                "sql_image_pull",
                "sql_digest_inspect",
                "client_image_build",
                "client_image_inspect",
                "network_create",
                "sql_container_start",
                "sql_container_identity",
                "sql_container_network",
            },
        )
        for boundary in proof.CHECKED_OUTER_COMMAND_BOUNDARIES:
            cases = (
                (FileNotFoundError("private-command"), "unavailable"),
                (
                    subprocess.TimeoutExpired(
                        ["private-command"], 1, output="private-output"
                    ),
                    "timeout",
                ),
                (
                    subprocess.CompletedProcess(
                        ["private-command"],
                        7,
                        "private-stdout",
                        "private-stderr",
                    ),
                    "nonzero",
                ),
            )
            for outcome, suffix in cases:
                with self.subTest(boundary=boundary, suffix=suffix), mock.patch.object(
                    proof.subprocess,
                    "run",
                    side_effect=outcome if isinstance(outcome, Exception) else None,
                    return_value=outcome if not isinstance(outcome, Exception) else None,
                ) as run:
                    with self.assertRaises(proof.ProofError) as caught:
                        proof._run(["private-command"], boundary=boundary)
                    self.assertEqual(str(caught.exception), f"{boundary}_{suffix}")
                    self.assertNotIn("private", str(caught.exception))
                    if suffix == "nonzero":
                        self.assertFalse(run.call_args.kwargs["check"])

    def test_readiness_and_client_unavailable_or_timeout_are_finite(self):
        for boundary in ("sql_readiness", "client_proof"):
            for error, suffix in (
                (FileNotFoundError("private-command"), "unavailable"),
                (
                    subprocess.TimeoutExpired(
                        ["private-command"], 1, output=b"private-output"
                    ),
                    "timeout",
                ),
            ):
                with self.subTest(boundary=boundary, suffix=suffix), mock.patch.object(
                    proof.subprocess, "run", side_effect=error
                ):
                    with self.assertRaises(proof.ProofError) as caught:
                        proof._run(
                            ["private-command"],
                            boundary=boundary,
                            check=False,
                            text=False,
                        )
                    self.assertEqual(str(caught.exception), f"{boundary}_{suffix}")
                    self.assertNotIn("private", str(caught.exception))

        not_ready = subprocess.CompletedProcess([], 1, "private-output", "private-error")
        with mock.patch.object(proof, "_run", return_value=not_ready) as run, mock.patch.object(
            proof.time, "sleep"
        ):
            with self.assertRaisesRegex(proof.ProofError, "^sql_readiness_timeout$"):
                proof._wait_for_sql("private-container")
        self.assertEqual(run.call_count, 45)
        self.assertTrue(
            all(call.kwargs["boundary"] == "sql_readiness" for call in run.call_args_list)
        )

    def test_client_nonzero_preserves_only_allowlisted_child_codes(self):
        for code in proof.CHILD_FAILURE_CODES:
            record = {
                "schema_version": 1,
                "status": "fail",
                "failure_code": code,
                "contains_member_data": False,
                "production_action": False,
            }
            result = subprocess.CompletedProcess(
                [], 1, json.dumps(record).encode("utf-8"), b"private-stderr"
            )
            with self.subTest(code=code), self.assertRaises(proof.ProofError) as caught:
                proof._client_result_record(result)
            self.assertEqual(str(caught.exception), f"inside_{code}")
            self.assertNotIn("private", str(caught.exception))

    def test_client_failure_record_rejects_malformed_extra_or_oversized_output(self):
        valid = {
            "schema_version": 1,
            "status": "fail",
            "failure_code": "empty_forward_unexpected",
            "contains_member_data": False,
            "production_action": False,
        }
        cases = (
            b"not-json private-secret",
            b"\xff",
            json.dumps([valid]).encode("utf-8"),
            json.dumps({**valid, "private": "private-secret"}).encode("utf-8"),
            json.dumps({key: value for key, value in valid.items() if key != "status"}).encode("utf-8"),
            json.dumps({**valid, "failure_code": "not_allowlisted"}).encode("utf-8"),
            json.dumps({**valid, "contains_member_data": True}).encode("utf-8"),
            b"x" * (proof.CLIENT_FAILURE_RECORD_MAX_BYTES + 1),
            "not-bytes private-secret",
        )
        for raw in cases:
            result = subprocess.CompletedProcess([], 1, raw, b"private-stderr")
            with self.subTest(raw_type=type(raw).__name__), self.assertRaises(
                proof.ProofError
            ) as caught:
                proof._client_result_record(result)
            self.assertEqual(
                str(caught.exception), "client_proof_invalid_failure_record"
            )
            self.assertNotIn("private-secret", str(caught.exception))

    def test_zero_exit_client_requires_the_exact_complete_pass_contract(self):
        source_sha = "a" * 40
        record = self._pipeline_pass_record(source_sha)
        for key in ("agent", "images", "cleanup_confirmed"):
            record.pop(key)
        record["steps"] = record["steps"][:-1]
        result = subprocess.CompletedProcess(
            [], 0, json.dumps(record).encode("utf-8"), b"private-stderr"
        )
        self.assertEqual(
            proof._client_result_record(result, source_sha),
            record,
        )
        record["private"] = "private-secret"
        result = subprocess.CompletedProcess(
            [], 0, json.dumps(record).encode("utf-8"), b"private-stderr"
        )
        with self.assertRaises(proof.ProofError) as caught:
            proof._client_result_record(result, source_sha)
        self.assertEqual(
            str(caught.exception), "client_proof_invalid_failure_record"
        )
        self.assertNotIn("private-secret", str(caught.exception))
        for mutation in ("schema_version_float", "machine_bound_int"):
            invalid = json.loads(json.dumps(record))
            invalid.pop("private")
            if mutation == "schema_version_float":
                invalid["schema_version"] = 1.0
            else:
                invalid["sql"]["machine_bound"] = 1
            result = subprocess.CompletedProcess(
                [], 0, json.dumps(invalid).encode("utf-8"), b"private-stderr"
            )
            with self.subTest(mutation=mutation), self.assertRaises(
                proof.ProofError
            ) as typed:
                proof._client_result_record(result, source_sha)
            self.assertEqual(
                str(typed.exception), "client_proof_invalid_failure_record"
            )

    def test_unexpected_child_exceptions_bind_to_each_finite_stage(self):
        for stage in proof.CHILD_PROOF_STAGES:
            with self.subTest(stage=stage), self.assertRaises(proof.ProofError) as caught:
                proof._run_child_stage(
                    stage, lambda: (_ for _ in ()).throw(RuntimeError("private-secret"))
                )
            self.assertEqual(str(caught.exception), f"{stage}_unexpected")
            self.assertNotIn("private-secret", str(caught.exception))

    def test_nonallowlisted_stage_proof_errors_normalize_at_current_stage(self):
        cases = (
            ("two_owner_verifier", "verifier_left_community_rows"),
            ("empty_rollback", "empty_rollback_postcondition_failed"),
            ("populated_rollback_refusal", "synthetic_identity_creation_failed"),
        )
        for stage, prior_code in cases:
            with self.subTest(stage=stage, prior_code=prior_code), self.assertRaises(
                proof.ProofError
            ) as caught:
                proof._run_child_stage(
                    stage,
                    lambda code=prior_code: (_ for _ in ()).throw(
                        proof.ProofError(code)
                    ),
                )
            self.assertEqual(str(caught.exception), f"{stage}_unexpected")
            self.assertNotIn(prior_code, str(caught.exception))

        with self.assertRaises(proof.ProofError) as allowed:
            proof._run_child_stage(
                "preflight",
                lambda: (_ for _ in ()).throw(
                    proof.ProofError("sql_job_local_address_mismatch")
                ),
            )
        self.assertEqual(str(allowed.exception), "sql_job_local_address_mismatch")

    def test_source_head_and_status_failures_write_evidence_and_run_cleanup(self):
        source_sha = "a" * 40
        cases = (
            (
                "source_head_nonzero",
                [
                    subprocess.CompletedProcess(
                        ["private-command"], 9, "private-stdout", "private-stderr"
                    )
                ],
            ),
            (
                "source_status_nonzero",
                [
                    subprocess.CompletedProcess([], 0, source_sha + "\n", ""),
                    subprocess.CompletedProcess(
                        ["private-command"], 9, "private-stdout", "private-stderr"
                    ),
                ],
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            for expected_code, command_results in cases:
                evidence = Path(directory) / f"{expected_code}.json"
                with self.subTest(expected_code=expected_code), mock.patch.object(
                    proof, "validate_execute_host"
                ), mock.patch.object(
                    proof.subprocess, "run", side_effect=command_results
                ), mock.patch.object(
                    proof, "_cleanup_exact", return_value=True
                ) as cleanup:
                    self.assertEqual(proof.execute_proof(source_sha, evidence), 1)
                record = json.loads(evidence.read_text(encoding="utf-8"))
                self.assertEqual(record["failure_code"], expected_code)
                self.assertTrue(record["cleanup_confirmed"])
                self.assertEqual(record["steps"][-1]["name"], "cleanup")
                self.assertEqual(record["steps"][-1]["status"], "pass")
                self.assertNotIn("private", evidence.read_text(encoding="utf-8"))
                cleanup.assert_called_once()
                with tempfile.TemporaryDirectory() as raw_name, tempfile.TemporaryDirectory() as artifact_name:
                    raw_directory = Path(raw_name)
                    artifacts = Path(artifact_name)
                    (raw_directory / "community-sql-proof.raw.json").write_text(
                        evidence.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                    with mock.patch.dict(
                        os.environ,
                        self._pipeline_envelope_env(
                            raw_directory, artifacts, source_sha
                        ),
                        clear=True,
                    ):
                        with self.assertRaisesRegex(
                            SystemExit, "^proof_reported_failure$"
                        ):
                            exec(
                                compile(
                                    self._pipeline_sealer_source(),
                                    "pipeline-sealer",
                                    "exec",
                                ),
                                {},
                            )
                    sealed = json.loads(
                        (
                            artifacts
                            / "CommunitySqlProofEvidence"
                            / "community-sql-proof-evidence.json"
                        ).read_text(encoding="utf-8")
                    )
                    self.assertEqual(sealed["failure_code"], expected_code)

    def test_database_cleanup_is_unconditional_and_authoritative(self):
        class Runner:
            @staticmethod
            def forward_migrations():
                raise RuntimeError("private-stage-error")

        environment = {
            "PROOF_SQL_HOST": "community-sql",
            "PROOF_SQL_PASSWORD": "private-password",
            "PROOF_ID": "abcdef123456",
            "PROOF_SOURCE_SHA": "a" * 40,
            "PROOF_SQL_EXPECTED_IP": "172.20.0.2",
            "PROOF_SQL_EXPECTED_MACHINE": "ps-community-sql-abcdef123456",
        }
        for cleanup_fails, expected_code in (
            (False, "empty_forward_unexpected"),
            (True, "database_cleanup_unconfirmed"),
        ):
            drop_effect = RuntimeError("private-cleanup-error") if cleanup_fails else None
            with self.subTest(cleanup_fails=cleanup_fails), mock.patch.dict(
                os.environ, environment, clear=True
            ), mock.patch.object(proof, "validate_inside_environment"), mock.patch.object(
                proof, "_load_migration_runner", return_value=Runner
            ), mock.patch.object(
                proof,
                "_validate_job_local_sql_target",
                return_value={"version": proof.SQL_BUILD, "edition": "Developer"},
            ), mock.patch.object(
                proof, "_create_database"
            ), mock.patch.object(
                proof, "_drop_database", side_effect=drop_effect
            ) as drop:
                with self.assertRaises(proof.ProofError) as caught:
                    proof.run_inside()
            self.assertEqual(str(caught.exception), expected_code)
            self.assertEqual(drop.call_count, 2)
            self.assertNotIn("private", str(caught.exception))

    def test_container_cleanup_failure_overrides_outer_diagnostic(self):
        source_sha = "a" * 40
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "proof.json"
            for cleanup_ok, expected_code in (
                (True, "docker_info_nonzero"),
                (False, "container_cleanup_unconfirmed"),
            ):
                with self.subTest(cleanup_ok=cleanup_ok), mock.patch.object(
                    proof, "validate_execute_host"
                ), mock.patch.object(
                    proof, "_validate_source_sha_at_head", return_value=source_sha
                ), mock.patch.object(
                    proof.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess(
                        ["private-command"],
                        7,
                        "private-stdout",
                        "private-stderr",
                    ),
                ), mock.patch.object(
                    proof, "_cleanup_exact", return_value=cleanup_ok
                ) as cleanup:
                    self.assertEqual(proof.execute_proof(source_sha, evidence), 1)
                record = json.loads(evidence.read_text(encoding="utf-8"))
                self.assertEqual(record["failure_code"], expected_code)
                self.assertNotIn("private", evidence.read_text(encoding="utf-8"))
                cleanup.assert_called_once()

    def test_private_environment_file_has_owner_only_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proof.env"
            proof._write_private_env(path, {"SAFE": "value"})
            self.assertEqual(path.read_text(encoding="utf-8"), "SAFE=value\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(proof.ProofError):
                proof._write_private_env(path, {"SAFE": "bad\nvalue"})

    def test_commands_never_embed_password_or_use_broad_cleanup(self):
        names = proof._resource_names("abcdef123456")
        cleanup = proof._docker_cleanup_commands(names)
        flattened = "\n".join(" ".join(command) for command in cleanup)
        self.assertNotIn("prune", flattened)
        self.assertNotIn("system", flattened)
        self.assertIn(names["sql_container"], flattened)
        self.assertIn(names["network"], flattened)
        with self.assertRaises(proof.ProofError):
            proof._run(["tool", "Password=do-not-log"])

    def test_client_executes_immutable_built_artifact_id(self):
        names = proof._resource_names("abcdef123456")
        artifact_id = "sha256:" + "a" * 64
        command = proof._client_run_command(names, Path("proof.env"), artifact_id)
        self.assertIn(artifact_id, command)
        self.assertNotIn(names["client_image"], command)
        with self.assertRaises(proof.ProofError):
            proof._client_run_command(names, Path("proof.env"), "mutable:tag")

    def test_cleanup_targets_exact_resources_and_tolerates_absent_objects(self):
        names = proof._resource_names("abcdef123456")
        completed = subprocess.CompletedProcess([], 1, "", "No such object")
        with mock.patch.object(proof, "_run", return_value=completed) as run:
            self.assertTrue(proof._cleanup_exact(names))
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            proof._docker_cleanup_commands(names),
        )
        self.assertTrue(all(call.kwargs["check"] is False for call in run.call_args_list))

    def test_cleanup_does_not_hide_a_real_failure(self):
        names = proof._resource_names("abcdef123456")
        completed = subprocess.CompletedProcess([], 1, "", "resource is still in use")
        with mock.patch.object(proof, "_run", return_value=completed):
            self.assertFalse(proof._cleanup_exact(names))

    def test_build_context_uses_pinned_client_arg_and_no_mount_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            context = Path(directory)
            proof._build_context(context)
            dockerfile = (context / "Dockerfile").read_text(encoding="utf-8")
            self.assertIn("ARG CLIENT_IMAGE", dockerfile)
            self.assertIn("FROM ${CLIENT_IMAGE}", dockerfile)
            self.assertNotIn("VOLUME", dockerfile.upper())
            self.assertTrue((context / "scripts" / SCRIPT.name).exists())
            self.assertTrue((context / "SQL FIles" / "Migrations").is_dir())

    def test_build_context_installs_documented_driver_runtime_libraries(self):
        with tempfile.TemporaryDirectory() as directory:
            context = Path(directory)
            proof._build_context(context)
            dockerfile = (context / "Dockerfile").read_text(encoding="utf-8")
            install_lines = [
                line for line in dockerfile.splitlines() if "apt-get install" in line
            ]
            self.assertEqual(len(install_lines), 1)
            for package in ("libgssapi-krb5-2", "libkrb5-3", "libltdl7"):
                with self.subTest(package=package):
                    self.assertIn(package, install_lines[0])
            self.assertIn("--no-install-recommends", install_lines[0])
            self.assertIn("rm -rf /var/lib/apt/lists/*", dockerfile)
            install_index = dockerfile.index("apt-get install")
            pip_index = dockerfile.index("pip install")
            self.assertLess(install_index, pip_index)

    def test_source_has_no_host_publish_mount_or_prune_command(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            '"--publish"',
            '"-p"',
            '"--volume"',
            '"-v"',
            '"prune"',
            'docker system',
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('"--internal"', source)
        self.assertIn('"--env-file"', source)
        for boundary in proof.OUTER_COMMAND_BOUNDARIES:
            with self.subTest(boundary=boundary):
                self.assertIn(f'boundary="{boundary}"', source)
        self.assertIn('boundary="client_proof"', source)
        self.assertIn("check=False,\n                text=False", source)

    def test_failure_records_are_content_free(self):
        with mock.patch.object(
            proof,
            "run_inside",
            side_effect=proof.ProofError("empty_forward_unexpected"),
        ):
            output = io.StringIO()
            with mock.patch("sys.stdout", output):
                self.assertEqual(proof.main(["--inside"]), 1)
        record = json.loads(output.getvalue())
        self.assertEqual(set(record), proof.CLIENT_FAILURE_RECORD_KEYS)
        self.assertEqual(record["failure_code"], "empty_forward_unexpected")
        self.assertFalse(record["contains_member_data"])
        self.assertFalse(record["production_action"])

    def test_inside_orchestration_order_and_step_durations(self):
        events = []

        class Runner:
            @staticmethod
            def forward_migrations():
                return ["foundation"]

            @staticmethod
            def selected_optional_migrations(_migration_ids):
                return ["community"]

            @staticmethod
            def apply_migrations(paths):
                events.append(("apply", tuple(paths)))

            @staticmethod
            def verify_foundation():
                events.append(("verify", "foundation"))

            @staticmethod
            def verify_community():
                events.append(("verify", "community"))

        def connection_action(_connection, action):
            return action()

        environment = {
            "PROOF_SQL_HOST": "community-sql",
            "PROOF_SQL_PASSWORD": "not-logged",
            "PROOF_ID": "abcdef123456",
            "PROOF_SOURCE_SHA": "a" * 40,
            "PROOF_SQL_EXPECTED_IP": "172.20.0.2",
            "PROOF_SQL_EXPECTED_MACHINE": "ps-community-sql-abcdef123456",
        }
        with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(
            proof, "validate_inside_environment"
        ), mock.patch.object(proof, "_load_migration_runner", return_value=Runner), mock.patch.object(
            proof,
            "_create_database",
            side_effect=lambda _host, _password, database: events.append(
                ("create", database)
            ),
        ), mock.patch.object(
            proof, "_with_connection_env", side_effect=connection_action
        ), mock.patch.object(
            proof,
            "_validate_job_local_sql_target",
            side_effect=lambda _host, _password, _ip, _machine: events.append(
                ("sql", "identity")
            )
            or {"version": proof.SQL_BUILD, "edition": "Developer"},
        ), mock.patch.object(
            proof,
            "_assert_empty_after_verifier",
            side_effect=lambda _connection: events.append(("assert", "verifier_empty")),
        ), mock.patch.object(
            proof,
            "_assert_empty_rollback",
            side_effect=lambda _connection: events.append(("assert", "empty_rollback")),
        ), mock.patch.object(
            proof,
            "_publish_synthetic_post",
            side_effect=lambda _connection, suffix="a": events.append(
                ("publish", "synthetic")
            ),
        ), mock.patch.object(
            proof,
            "_remove_synthetic_post",
            side_effect=lambda _connection: events.append(("remove", "synthetic")),
        ), mock.patch.object(
            proof,
            "_assert_purge_actually_runs",
            side_effect=lambda _connection: events.append(("assert", "purge_ran")),
        ), mock.patch.object(
            proof,
            "_assert_populated_refusal",
            side_effect=lambda _connection, _runner: events.append(
                ("assert", "populated_refusal")
            ),
        ), mock.patch.object(
            proof,
            "_drop_database",
            side_effect=lambda _host, _password, database: events.append(
                ("drop", database)
            ),
        ):
            record = proof.run_inside()

        self.assertEqual(record["status"], "pass")
        self.assertTrue(record["database_cleanup_confirmed"])
        self.assertEqual(
            [step["name"] for step in record["steps"]],
            list(proof.PROOF_STEPS[:-1]),
        )
        self.assertTrue(
            all("duration_seconds" in step for step in record["steps"])
        )
        self.assertLess(events.index(("apply", ("foundation",))), events.index(("apply", ("community",))))
        self.assertLess(events.index(("verify", "community")), events.index(("assert", "verifier_empty")))
        self.assertLess(events.index(("publish", "synthetic")), events.index(("assert", "populated_refusal")))
        # The purge must actually execute against removed content: applying
        # migrations alone hid a purge that could never commit (review F2).
        self.assertLess(events.index(("remove", "synthetic")), events.index(("assert", "purge_ran")))
        # And it must run AFTER the rollback assertions: a purge leaves
        # body-free tombstones, and the retention rollback correctly refuses
        # while any exist, so purging first would block a guard doing its job.
        self.assertLess(
            events.index(("assert", "populated_refusal")),
            events.index(("remove", "synthetic")),
        )
        self.assertEqual(events[-2][0], "drop")
        self.assertEqual(events[-1][0], "drop")


if __name__ == "__main__":
    unittest.main()
