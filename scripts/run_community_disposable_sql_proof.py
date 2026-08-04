"""Run the protected Community migration proof on disposable x64 Linux only.

Plan mode is the default and performs no Docker, database, or network action.
Remote execution is intentionally not wired into the deployment pipeline.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import socket
import stat
import string
import subprocess
import sys
import tempfile
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_RUNNER_PATH = ROOT / "scripts" / "apply_sql_migrations.py"
COMMUNITY_FORWARD_PATH = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql"
)
COMMUNITY_VERIFY_PATH = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-COMMUNITY-PUBLIC-PILOT-001_owner_public_verify.sql"
)
COMMUNITY_ROLLBACK_PATH = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-COMMUNITY-PUBLIC-PILOT-001_community_rollback.sql"
)
RESTORE_ROLLBACK_PATH = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-COMMUNITY-RESTORE-001_restore_rollback.sql"
)
RETENTION_ROLLBACK_PATH = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-COMMUNITY-RETENTION-001_retention_rollback.sql"
)
# Applied together and rolled back in reverse: retention depends on the
# Community tables, so its rollback must run first.
COMMUNITY_MIGRATION_IDS = [
    "PS-COMMUNITY-PUBLIC-PILOT-001",
    "PS-COMMUNITY-RETENTION-001",
    "PS-COMMUNITY-RESTORE-001",
]

SQL_IMAGE_TAG = "mcr.microsoft.com/mssql/server:2022-CU26-ubuntu-22.04"
SQL_IMAGE_DIGEST = (
    "sha256:ba4c8329f48fb8f02e1416be6a930ebfd71268caee78aa985f3af4315e457c89"
)
SQL_IMAGE = f"{SQL_IMAGE_TAG}@{SQL_IMAGE_DIGEST}"
SQL_BUILD = "16.0.4265.3"

CLIENT_IMAGE_TAG = "python:3.12-slim"
CLIENT_IMAGE_DIGEST = (
    "sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464"
)
CLIENT_IMAGE = f"{CLIENT_IMAGE_TAG}@{CLIENT_IMAGE_DIGEST}"

TRUE_VALUES = {"1", "true", "yes", "on"}
PROOF_STEPS = (
    "preflight",
    "empty_forward",
    "forward_idempotency",
    "two_owner_verifier",
    "empty_rollback",
    "populated_rollback_refusal",
    "cleanup",
)
OUTER_COMMAND_BOUNDARIES = frozenset(
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
        "sql_readiness",
        "client_proof",
    }
)
CHECKED_OUTER_COMMAND_BOUNDARIES = OUTER_COMMAND_BOUNDARIES - {
    "sql_readiness",
    "client_proof",
}
CHILD_PROOF_STAGES = (
    "preflight",
    "database_setup",
    "empty_forward",
    "forward_idempotency",
    "two_owner_verifier",
    "empty_rollback",
    "populated_rollback_refusal",
)
CHILD_FAILURE_CODES = frozenset(
    {
        "mode_requires_container",
        "mode_requires_ci",
        "community_flag_must_remain_false",
        "preexisting_sql_connection_forbidden",
        "sql_host_not_job_local",
        "proof_id_invalid",
        "sql_machine_binding_invalid",
        "sql_network_binding_invalid",
        "source_sha_invalid",
        "proof_environment_invalid",
        "migration_runner_import_failed",
        "sql_job_local_name_resolution_failed",
        "sql_job_local_address_mismatch",
        "sql_source_files_unreadable",
        "sql_tcp_unreachable",
        "sql_connect_failed",
        "sql_connect_failed_tls_only",
        "sql_identity_query_failed",
        "sql_machine_identity_mismatch",
        "sql_build_or_edition_unexpected",
        "preflight_unexpected",
        "database_setup_unexpected",
        "empty_forward_unexpected",
        "empty_forward_ps_plat_000",
        "empty_forward_ps_plat_001",
        "empty_forward_ps_plat_002",
        "empty_forward_ps_plat_003",
        "empty_forward_ps_plat_004",
        "empty_forward_ps_plat_005",
        "empty_forward_ps_plat_006",
        "empty_forward_ps_plat_007",
        "empty_forward_ps_auth_001",
        "empty_forward_ps_community_public_pilot_001",
        "empty_forward_ps_community_retention_001",
        "empty_forward_ps_community_restore_001",
        "forward_idempotency_unexpected",
        "two_owner_verifier_unexpected",
        "empty_rollback_unexpected",
        "populated_rollback_refusal_unexpected",
        "purge_precondition_missing",
        "purge_left_content_unpurged",
        "purge_ignored_a_legal_hold",
        "purge_count_query_failed",
        "purge_execution_failed",
        "purge_verify_query_failed",
        "purge_hold_query_failed",
        "purge_setup_responses_failed",
        "purge_setup_saves_failed",
        "purge_setup_remove_failed",
        "populated_rollback_refusal_not_recognized",
        "populated_rollback_was_not_refused",
        "database_cleanup_unconfirmed",
    }
)
CLIENT_FAILURE_RECORD_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "failure_code",
        "contains_member_data",
        "production_action",
    }
)
CLIENT_PASS_RECORD_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "classification",
        "source_sha",
        "sql",
        "steps",
        "database_cleanup_confirmed",
        "file_sha256",
        "duration_seconds",
        "contains_member_data",
        "production_action",
    }
)
CLIENT_FAILURE_RECORD_MAX_BYTES = 4096
CLIENT_PASS_RECORD_MAX_BYTES = 65536
PINNED_IMAGE_PATTERN = re.compile(
    r"^[a-z0-9./_-]+(?::[A-Za-z0-9._-]+)?@sha256:[0-9a-f]{64}$"
)
SAFE_ID_PATTERN = re.compile(r"^[a-z0-9_-]{8,80}$")
IMAGE_ID_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMUNITY_TABLES = (
    "community_posts",
    "community_post_revisions",
    "community_contributions",
    "community_contribution_revisions",
    "community_responses",
    "community_saves",
    "community_contribution_saves",
    "community_media",
    "community_audit_events",
    "community_outbox",
)
COMMUNITY_PROCEDURES = (
    "usp_ListPublicCommunityFeed",
    "usp_ListPublicCommunityShelf",
    "usp_GetPublicCommunityPost",
    "usp_GetPublicCommunityContribution",
    "usp_SearchPublicCommunity",
    "usp_PublishPublicCommunityPost",
    "usp_EditPublicCommunityPost",
    "usp_DeletePublicCommunityPost",
    "usp_AddPublicCommunityContribution",
    "usp_EditPublicCommunityContribution",
    "usp_DeletePublicCommunityContribution",
    "usp_SetPublicCommunityResponse",
    "usp_RemovePublicCommunityResponse",
    "usp_SetPublicCommunitySave",
    "usp_SetPublicCommunityContributionSave",
    "usp_ReservePublicCommunityMedia",
    "usp_MarkPublicCommunityMediaUploaded",
    "usp_GetPublicCommunityMediaForOwner",
    "usp_CompletePublicCommunityMedia",
    "usp_CompensatePublicCommunityMediaCompletion",
    "usp_RejectPublicCommunityMedia",
    "usp_ClaimPublicCommunityMediaCleanup",
    "usp_CompletePublicCommunityMediaCleanup",
    "usp_GetPublicCommunityMedia",
    "usp_DeletePublicCommunityMedia",
)


class ProofError(RuntimeError):
    """Fail-closed proof error with a content-free message."""


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_source_sha(value: str) -> str:
    normalized = value.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", normalized):
        raise ProofError("source_sha_invalid")
    return normalized


def _validate_source_sha_at_head(value: str) -> str:
    expected = _safe_source_sha(value)
    actual = _run(
        ["git", "rev-parse", "HEAD"], boundary="source_head", timeout=30
    ).stdout.strip().lower()
    if actual != expected:
        raise ProofError("source_sha_does_not_match_head")
    status = _run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        boundary="source_status",
        timeout=30,
    ).stdout
    if status.strip():
        raise ProofError("source_worktree_must_be_clean")
    return expected


def _validate_image(value: str, expected: str, label: str) -> str:
    if not PINNED_IMAGE_PATTERN.fullmatch(value) or value != expected:
        raise ProofError(f"{label}_image_not_exactly_pinned")
    return value


def validate_execute_host(
    *,
    system: str | None = None,
    machine: str | None = None,
    release: dict[str, str] | None = None,
    environ: dict[str, str] | None = None,
) -> None:
    env = dict(os.environ if environ is None else environ)
    actual_system = system or platform.system()
    actual_machine = (machine or platform.machine()).lower()
    if actual_system != "Linux" or actual_machine != "x86_64":
        raise ProofError("supported_x64_linux_required")
    os_release = release
    if os_release is None:
        os_release = platform.freedesktop_os_release()
    if os_release.get("ID") != "ubuntu" or os_release.get("VERSION_ID") != "22.04":
        raise ProofError("ubuntu_22_04_required")
    if (
        not _truthy(env.get("TF_BUILD"))
        or env.get("AGENT_OS") != "Linux"
        or env.get("AGENT_OSARCHITECTURE") not in {"X64", "x64"}
    ):
        raise ProofError("microsoft_hosted_x64_agent_required")
    if _truthy(env.get("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED")):
        raise ProofError("community_flag_must_remain_false")
    if env.get("AZURE_SQL_CONNECTIONSTRING"):
        raise ProofError("preexisting_sql_connection_forbidden")
    for key in (
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
        "ARM_CLIENT_ID",
        "ARM_CLIENT_SECRET",
    ):
        if env.get(key):
            raise ProofError("external_provider_credential_forbidden")


def validate_docker_server(info: dict[str, object]) -> None:
    os_type = str(info.get("OSType") or "").lower()
    architecture = str(info.get("Architecture") or "").lower()
    if os_type != "linux" or architecture != "x86_64":
        raise ProofError("docker_server_must_be_x64_linux")


def validate_inside_environment(
    *,
    environ: dict[str, str] | None = None,
    docker_marker: Path = Path("/.dockerenv"),
) -> None:
    env = dict(os.environ if environ is None else environ)
    if not docker_marker.exists():
        raise ProofError("mode_requires_container")
    if not _truthy(env.get("CI")):
        raise ProofError("mode_requires_ci")
    if _truthy(env.get("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED")):
        raise ProofError("community_flag_must_remain_false")
    if env.get("AZURE_SQL_CONNECTIONSTRING"):
        raise ProofError("preexisting_sql_connection_forbidden")
    if env.get("PROOF_SQL_HOST") != "community-sql":
        raise ProofError("sql_host_not_job_local")
    proof_id = env.get("PROOF_ID", "")
    if not SAFE_ID_PATTERN.fullmatch(proof_id):
        raise ProofError("proof_id_invalid")
    if env.get("PROOF_SQL_EXPECTED_MACHINE") != f"ps-community-sql-{proof_id}":
        raise ProofError("sql_machine_binding_invalid")
    try:
        expected_ip = ipaddress.ip_address(env.get("PROOF_SQL_EXPECTED_IP", ""))
    except ValueError as error:
        raise ProofError("sql_network_binding_invalid") from error
    private_networks = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    )
    if expected_ip.version != 4 or not any(
        expected_ip in network for network in private_networks
    ):
        raise ProofError("sql_network_binding_invalid")


def _run(
    command: list[str],
    *,
    boundary: str | None = None,
    timeout: int = 300,
    env: dict[str, str] | None = None,
    check: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess:
    if any(
        "Password=" in item or "PWD=" in item or "MSSQL_SA_PASSWORD=" in item
        for item in command
    ):
        raise ProofError("secret_in_command_argv")
    if boundary is not None and boundary not in OUTER_COMMAND_BOUNDARIES:
        raise ProofError("command_boundary_invalid")
    if check and boundary not in CHECKED_OUTER_COMMAND_BOUNDARIES:
        raise ProofError("command_boundary_required")
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=text,
            timeout=timeout,
            env=env,
        )
    except OSError:
        code = f"{boundary}_unavailable" if boundary else "required_command_unavailable"
        raise ProofError(code) from None
    except subprocess.TimeoutExpired:
        code = f"{boundary}_timeout" if boundary else "bounded_command_timeout"
        raise ProofError(code) from None
    if check and result.returncode != 0:
        raise ProofError(f"{boundary}_nonzero")
    return result


def _write_private_env(path: Path, values: dict[str, str]) -> None:
    if any("\n" in value or "\r" in value for value in values.values()):
        raise ProofError("environment_value_invalid")
    path.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items()),
        encoding="utf-8",
    )
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "Ps!9" + "".join(secrets.choice(alphabet) for _ in range(28))


def _resource_names(proof_id: str) -> dict[str, str]:
    if not SAFE_ID_PATTERN.fullmatch(proof_id):
        raise ProofError("proof_id_invalid")
    return {
        "network": f"ps-community-sql-{proof_id}",
        "sql_container": f"ps-community-sql-{proof_id}",
        "client_container": f"ps-community-client-{proof_id}",
        "client_image": f"peerslate-community-sql-proof-client:{proof_id}",
        "client_image_cleanup": f"peerslate-community-sql-proof-client:{proof_id}",
    }


def _docker_cleanup_commands(names: dict[str, str]) -> list[list[str]]:
    return [
        ["docker", "rm", "--force", names["client_container"]],
        ["docker", "rm", "--force", names["sql_container"]],
        ["docker", "network", "rm", names["network"]],
        ["docker", "image", "rm", "--force", names["client_image_cleanup"]],
    ]


def _client_run_command(
    names: dict[str, str], env_file: Path, client_artifact_id: str
) -> list[str]:
    if not IMAGE_ID_PATTERN.fullmatch(client_artifact_id):
        raise ProofError("client_artifact_identity_invalid")
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        names["client_container"],
        "--network",
        names["network"],
        "--env-file",
        str(env_file),
        client_artifact_id,
        "--inside",
    ]


def _cleanup_exact(names: dict[str, str]) -> bool:
    success = True
    for command in _docker_cleanup_commands(names):
        try:
            result = _run(command, timeout=90, check=False)
        except ProofError:
            success = False
            continue
        missing = any(
            marker in (result.stderr or "").lower()
            for marker in ("no such", "not found")
        )
        if result.returncode != 0 and not missing:
            success = False
    return success


def _build_context(context: Path) -> None:
    shutil.copy2(ROOT / "requirements-sql.txt", context / "requirements-sql.txt")
    scripts_dir = context / "scripts"
    scripts_dir.mkdir()
    shutil.copy2(MIGRATION_RUNNER_PATH, scripts_dir / MIGRATION_RUNNER_PATH.name)
    shutil.copy2(Path(__file__).resolve(), scripts_dir / Path(__file__).name)
    shutil.copytree(ROOT / "SQL FIles", context / "SQL FIles")
    dockerfile = f"""ARG CLIENT_IMAGE
FROM ${{CLIENT_IMAGE}}
WORKDIR /proof
RUN apt-get update \\
    && apt-get install -y --no-install-recommends libgssapi-krb5-2 libkrb5-3 libltdl7 \\
    && rm -rf /var/lib/apt/lists/*
# The bundled msodbcsql18 negotiates TLS against the disposable SQL container's
# self-signed certificate. Debian's OpenSSL 3 defaults to security level 2,
# which refuses that handshake regardless of TrustServerCertificate, because
# the level governs key and cipher strength rather than certificate trust.
# Lower it inside this throwaway client only; nothing here touches production,
# which connects to Azure SQL over a normal public certificate chain.
RUN sed -i 's/@SECLEVEL=2/@SECLEVEL=0/' /etc/ssl/openssl.cnf
COPY requirements-sql.txt ./requirements-sql.txt
RUN python -m pip install --no-cache-dir -r requirements-sql.txt
COPY scripts ./scripts
COPY [\"SQL FIles\", \"SQL FIles\"]
ENTRYPOINT [\"python\", \"/proof/scripts/run_community_disposable_sql_proof.py\"]
"""
    (context / "Dockerfile").write_text(dockerfile, encoding="utf-8")


def _wait_for_sql(container: str) -> None:
    command = [
        "docker",
        "exec",
        container,
        "bash",
        "-lc",
        (
            "tool=/opt/mssql-tools18/bin/sqlcmd; "
            "test -x \"$tool\" || tool=/opt/mssql-tools/bin/sqlcmd; "
            "SQLCMDPASSWORD=\"$MSSQL_SA_PASSWORD\" \"$tool\" "
            "-S localhost -U sa -C -b -Q 'SET NOCOUNT ON; SELECT 1'"
        ),
    ]
    for _ in range(45):
        result = _run(
            command,
            boundary="sql_readiness",
            timeout=15,
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise ProofError("sql_readiness_timeout")


def _inspect_sql_container(names: dict[str, str]) -> dict[str, str]:
    container_id = _run(
        ["docker", "inspect", "--format", "{{.Id}}", names["sql_container"]],
        boundary="sql_container_identity",
        timeout=60,
    ).stdout.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", container_id):
        raise ProofError("sql_container_identity_invalid")
    networks = json.loads(
        _run(
            [
                "docker",
                "inspect",
                "--format",
                "{{json .NetworkSettings.Networks}}",
                names["sql_container"],
            ],
            boundary="sql_container_network",
            timeout=60,
        ).stdout
    )
    if set(networks) != {names["network"]}:
        raise ProofError("sql_container_network_not_isolated")
    address = str(networks[names["network"]].get("IPAddress") or "")
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError as error:
        raise ProofError("sql_container_network_address_invalid") from error
    private_networks = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    )
    if parsed.version != 4 or not any(parsed in network for network in private_networks):
        raise ProofError("sql_container_network_address_invalid")
    return {
        "container_id": container_id,
        "ip_address": address,
        "machine_name": names["sql_container"],
    }


def _load_migration_runner():
    try:
        spec = importlib.util.spec_from_file_location(
            "peerslate_sql_migration_runner", MIGRATION_RUNNER_PATH
        )
        if spec is None or spec.loader is None:
            raise RuntimeError
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        raise ProofError("migration_runner_import_failed")
    return module


def _run_child_stage(stage: str, action):
    if stage not in CHILD_PROOF_STAGES:
        raise ProofError("preflight_unexpected")
    try:
        return action()
    except ProofError as error:
        if _is_acceptable_child_code(str(error)):
            raise
        raise ProofError(f"{stage}_unexpected") from None
    except Exception:
        raise ProofError(f"{stage}_unexpected") from None


def _bounded_client_json(raw: object, maximum_bytes: int) -> dict[str, object]:
    if not isinstance(raw, bytes) or not raw or len(raw) > maximum_bytes:
        raise ProofError("client_proof_invalid_failure_record")
    try:
        decoded = raw.decode("utf-8", errors="strict")

        def exact_object(pairs):
            record = {}
            for key, value in pairs:
                if key in record:
                    raise ValueError
                record[key] = value
            return record

        record = json.loads(decoded, object_pairs_hook=exact_object)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise ProofError("client_proof_invalid_failure_record") from None
    if not isinstance(record, dict):
        raise ProofError("client_proof_invalid_failure_record")
    return record


def _parse_client_failure_record(raw: object) -> str:
    record = _bounded_client_json(raw, CLIENT_FAILURE_RECORD_MAX_BYTES)
    if set(record) != CLIENT_FAILURE_RECORD_KEYS:
        raise ProofError("client_proof_invalid_failure_record")
    code = record.get("failure_code")
    if (
        type(record.get("schema_version")) is not int
        or record.get("schema_version") != 1
        or record.get("status") != "fail"
        or record.get("contains_member_data") is not False
        or record.get("production_action") is not False
        or not _is_acceptable_child_code(code)
    ):
        raise ProofError("client_proof_invalid_failure_record")
    return code


def _bounded_duration(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= 3600
    )


def _parse_client_pass_record(
    raw: object, expected_source_sha: str
) -> dict[str, object]:
    record = _bounded_client_json(raw, CLIENT_PASS_RECORD_MAX_BYTES)
    if (
        set(record) != CLIENT_PASS_RECORD_KEYS
        or type(record.get("schema_version")) is not int
        or record.get("schema_version") != 1
        or record.get("status") != "pass"
        or record.get("classification")
        != "disposable_x64_nonproduction_sql_runtime"
        or record.get("source_sha") != expected_source_sha
        or record.get("contains_member_data") is not False
        or record.get("production_action") is not False
        or record.get("database_cleanup_confirmed") is not True
        or not _bounded_duration(record.get("duration_seconds"))
    ):
        raise ProofError("client_proof_invalid_failure_record")
    sql = record.get("sql")
    if (
        not isinstance(sql, dict)
        or set(sql) != {"version", "edition", "machine_bound"}
        or sql.get("version") != SQL_BUILD
        or sql.get("edition") != "Developer"
        or sql.get("machine_bound") is not True
    ):
        raise ProofError("client_proof_invalid_failure_record")
    hashes = record.get("file_sha256")
    if (
        not isinstance(hashes, dict)
        or set(hashes) != {"forward", "verifier", "rollback"}
        or not all(
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
            for value in hashes.values()
        )
    ):
        raise ProofError("client_proof_invalid_failure_record")
    steps = record.get("steps")
    if not isinstance(steps, list) or len(steps) != len(PROOF_STEPS) - 1:
        raise ProofError("client_proof_invalid_failure_record")
    for step, expected_name in zip(steps, PROOF_STEPS[:-1]):
        if (
            not isinstance(step, dict)
            or set(step) != {"name", "status", "duration_seconds"}
            or step.get("name") != expected_name
            or step.get("status") != "pass"
            or not _bounded_duration(step.get("duration_seconds"))
        ):
            raise ProofError("client_proof_invalid_failure_record")
    return record


def _client_result_record(
    result: subprocess.CompletedProcess, expected_source_sha: str = ""
) -> dict[str, object]:
    if result.returncode != 0:
        child_code = _parse_client_failure_record(result.stdout)
        raise ProofError(f"inside_{child_code}")
    return _parse_client_pass_record(result.stdout, expected_source_sha)


def _connection_string(host: str, database: str, password: str) -> str:
    if not re.fullmatch(r"[a-z0-9_-]{8,80}", host):
        raise ProofError("sql_host_not_job_local")
    if not re.fullmatch(r"[A-Za-z0-9_]{8,80}", database):
        raise ProofError("database_name_invalid")
    # ODBC keywords, not ADO.NET ones. mssql-python normalizes a fixed
    # keyword set and silently discards anything outside it: `Initial
    # Catalog`, `User ID`, `Password`, and `Connection Timeout` all normalize
    # to None, so the earlier string reached the driver carrying only Server,
    # Encrypt, and TrustServerCertificate. The login was therefore attempted
    # with no credentials and no database, which is why every run failed
    # identically whether encrypted or not. The login timeout is supplied as
    # the `timeout` argument to connect() instead.
    return (
        f"Server=tcp:{host},1433;Database={database};UID=sa;"
        f"PWD={password};Encrypt=yes;TrustServerCertificate=yes;"
    )


def _connect(connection_string: str):
    from mssql_python import connect

    connection = connect(connection_string, timeout=30)
    connection.setautocommit(True)
    return connection


def _create_database(host: str, password: str, database: str) -> None:
    master = _connection_string(host, "masterdb", password).replace(
        "Database=masterdb", "Database=master"
    )
    with _connect(master) as connection:
        connection.cursor().execute(f"CREATE DATABASE [{database}]")


def _drop_database(host: str, password: str, database: str) -> None:
    master = _connection_string(host, "masterdb", password).replace(
        "Database=masterdb", "Database=master"
    )
    with _connect(master) as connection:
        connection.cursor().execute(
            f"ALTER DATABASE [{database}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
            f"DROP DATABASE [{database}];"
        )


def _with_connection_env(connection_string: str, action):
    prior = os.environ.get("AZURE_SQL_CONNECTIONSTRING")
    os.environ["AZURE_SQL_CONNECTIONSTRING"] = connection_string
    try:
        with redirect_stdout(io.StringIO()):
            return action()
    finally:
        if prior is None:
            os.environ.pop("AZURE_SQL_CONNECTIONSTRING", None)
        else:
            os.environ["AZURE_SQL_CONNECTIONSTRING"] = prior


def _assert_empty_after_verifier(connection_string: str) -> None:
    tables = (
        "community_posts",
        "community_post_revisions",
        "community_contributions",
        "community_contribution_revisions",
        "community_responses",
        "community_saves",
        "community_contribution_saves",
        "community_media",
        "community_audit_events",
        "community_outbox",
    )
    with _connect(connection_string) as connection:
        cursor = connection.cursor()
        for table in tables:
            cursor.execute(f"SELECT COUNT_BIG(*) FROM dbo.[{table}]")
            if int(cursor.fetchone()[0]) != 0:
                raise ProofError("verifier_left_community_rows")


def _assert_empty_rollback(connection_string: str) -> None:
    table_names = ",".join(f"N'{name}'" for name in COMMUNITY_TABLES)
    procedure_names = ",".join(f"N'{name}'" for name in COMMUNITY_PROCEDURES)
    with _connect(connection_string) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT "
            f"(SELECT COUNT(*) FROM sys.tables WHERE schema_id=SCHEMA_ID(N'dbo') "
            f"AND name IN ({table_names})), "
            f"(SELECT COUNT(*) FROM sys.procedures WHERE schema_id=SCHEMA_ID(N'dbo') "
            f"AND name IN ({procedure_names})), "
            "CASE WHEN EXISTS(SELECT 1 FROM dbo.schema_migrations "
            "WHERE migration_id=N'PS-COMMUNITY-PUBLIC-PILOT-001') THEN 1 ELSE 0 END, "
            "CASE WHEN EXISTS(SELECT 1 FROM dbo.schema_migrations "
            "WHERE migration_id=N'PS-AUTH-001') THEN 1 ELSE 0 END"
        )
        table_count, procedure_count, ledger_present, auth_present = map(
            int, cursor.fetchone()
        )
        if (table_count, procedure_count, ledger_present, auth_present) != (0, 0, 0, 1):
            raise ProofError("empty_rollback_postcondition_failed")


def _remove_synthetic_post(connection_string: str) -> None:
    """Delete the synthetic post through its own procedure, as an author would.

    Backdates deleted_at_utc so the row is immediately purge-eligible; the
    production retention window is untouched.
    """
    with _connect(connection_string) as connection:
        cursor = connection.cursor()
        _coded(
            "purge_setup_responses_failed",
            lambda: cursor.execute("DELETE dbo.community_responses"),
        )
        _coded(
            "purge_setup_saves_failed",
            lambda: cursor.execute("DELETE dbo.community_saves"),
        )
        _coded(
            "purge_setup_remove_failed",
            lambda: cursor.execute(
                "UPDATE dbo.community_posts "
                "SET publication_state=N'deleted', "
                "deleted_at_utc=DATEADD(day,-2,SYSUTCDATETIME()) "
                "WHERE publication_state=N'published'"
            ),
        )


def _publish_synthetic_post(connection_string: str, suffix: str = "a") -> None:
    with _connect(connection_string) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "EXEC dbo.usp_UpsertAppUserFromAuth "
            "@AuthProvider=?,@AuthIssuer=?,@AuthSubject=?,@Email=?,@DisplayName=?",
            (
                "proof",
                "urn:peerslate:disposable-community-proof",
                "synthetic-owner",
                "synthetic-owner@example.invalid",
                "Synthetic owner",
            ),
        )
        rows = []
        while True:
            if cursor.description is not None:
                columns = [column[0] for column in cursor.description]
                rows.extend(dict(zip(columns, row)) for row in cursor.fetchall())
            if not cursor.nextset():
                break
        user_key = next((row.get("user_key") for row in rows if row.get("user_key")), None)
        if not user_key:
            raise ProofError("synthetic_identity_creation_failed")
        cursor.execute(
            "EXEC dbo.usp_PublishPublicCommunityPost "
            "@UserKey=?,@IdempotencyKey=?,@Body=?,@Intent=?,"
            "@ResponsePosture=?,@Audience=?,@AttachmentKeysJson=?",
            (
                user_key,
                "disposable-proof-command-000" + suffix,
                "Synthetic rollback refusal proof.",
                "post",
                "sharing_only",
                "public",
                "[]",
            ),
        )
        while True:
            if cursor.description is not None:
                cursor.fetchall()
            if not cursor.nextset():
                break


def _assert_populated_refusal(connection_string: str, runner) -> None:
    # Roll retention back first. While it is applied, the Community rollback
    # correctly refuses with "a later migration is present" â€” a different
    # guard from the one under test. An operator unwinds in this order anyway,
    # and it leaves the content interlock as the only thing standing between
    # the command and real member content.
    _with_connection_env(
        connection_string,
        lambda: runner.apply_migrations(
            [RESTORE_ROLLBACK_PATH, RETENTION_ROLLBACK_PATH]
        ),
    )
    try:
        _with_connection_env(
            connection_string,
            lambda: runner.apply_migrations([COMMUNITY_ROLLBACK_PATH]),
        )
    except Exception as error:
        # The driver surfaces the server's message text without the numeric
        # code, so matching on "52490" never succeeded and a correct refusal
        # was reported as an unexpected failure. Recognise the refusal by the
        # guard message the rollback file itself declares for the
        # content-present number, falling back to the number if a future
        # driver does surface it.
        if not _is_declared_content_refusal(error):
            raise ProofError("populated_rollback_refusal_not_recognized") from None
    else:
        raise ProofError("populated_rollback_was_not_refused")

    _with_connection_env(
        connection_string,
        lambda: runner.apply_migrations(
            runner.selected_optional_migrations(COMMUNITY_MIGRATION_IDS)
        ),
    )

    table_names = ",".join(f"N'{name}'" for name in COMMUNITY_TABLES)
    procedure_names = ",".join(f"N'{name}'" for name in COMMUNITY_PROCEDURES)
    with _connect(connection_string) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT "
            f"(SELECT COUNT(*) FROM sys.tables WHERE schema_id=SCHEMA_ID(N'dbo') "
            f"AND name IN ({table_names})), "
            f"(SELECT COUNT(*) FROM sys.procedures WHERE schema_id=SCHEMA_ID(N'dbo') "
            f"AND name IN ({procedure_names})), "
            "CASE WHEN EXISTS(SELECT 1 FROM dbo.schema_migrations "
            "WHERE migration_id=N'PS-COMMUNITY-PUBLIC-PILOT-001') THEN 1 ELSE 0 END, "
            "(SELECT COUNT_BIG(*) FROM dbo.community_posts)"
        )
        table_count, procedure_count, ledger_present, post_count = map(
            int, cursor.fetchone()
        )
        if (
            table_count,
            procedure_count,
            ledger_present,
            post_count,
        ) != (len(COMMUNITY_TABLES), len(COMMUNITY_PROCEDURES), 1, 1):
            raise ProofError("populated_rollback_did_not_preserve_state")


FORWARD_MIGRATION_FILE_CODES = frozenset(
    {
        "empty_forward_ps_plat_000",
        "empty_forward_ps_plat_001",
        "empty_forward_ps_plat_002",
        "empty_forward_ps_plat_003",
        "empty_forward_ps_plat_004",
        "empty_forward_ps_plat_005",
        "empty_forward_ps_plat_006",
        "empty_forward_ps_plat_007",
        "empty_forward_ps_auth_001",
        "empty_forward_ps_community_public_pilot_001",
        "empty_forward_ps_community_retention_001",
        "empty_forward_ps_community_restore_001",
    }
)
# SQL error numbers that may be appended to a per-file forward code. Engine
# numbers are finite server-defined identifiers and the 52xxx values are this
# repository's own guard THROWs, so naming one discloses no content. Numbers
# outside this set are never recorded.
ALLOWED_SQL_ERROR_NUMBERS = frozenset(
    {102, 156, 206, 207, 208, 213, 245, 257, 515, 547, 1750, 1767, 1776,
     1778, 1785, 1913, 2705, 2714, 2760, 4902, 8111, 8114, 8152,
     51000, 51001, 51002, 51800, 51801}
    | {52400, 52401, 52402, 52403, 52404, 52405, 52406, 52410, 52411, 52412,
       52413, 52420, 52421, 52422, 52423, 52424, 52425, 52426, 52427, 52430,
       52431, 52432, 52434, 52435, 52436, 52437, 52440, 52441, 52442, 52443,
       52444, 52445, 52446, 52450, 52451, 52452, 52453, 52454}
)
FORWARD_MIGRATION_ERROR_CODES = frozenset(
    f"{code}_e{number}"
    for code in FORWARD_MIGRATION_FILE_CODES
    for number in ALLOWED_SQL_ERROR_NUMBERS
)
# Last-resort refinement: the exception's class name, a finite content-free
# taxonomy that at least separates a Python-level fault from a driver fault.
ALLOWED_EXCEPTION_CLASS_NAMES = frozenset(
    {"programmingerror", "operationalerror", "integrityerror", "databaseerror",
     "interfaceerror", "dataerror", "internalerror", "notsupportederror",
     "runtimeerror", "attributeerror", "typeerror", "valueerror", "oserror",
     "keyerror", "exception"}
)
FORWARD_MIGRATION_CLASS_CODES = frozenset(
    f"{code}_x{name}"
    for code in FORWARD_MIGRATION_FILE_CODES
    for name in ALLOWED_EXCEPTION_CLASS_NAMES
)
# Rollback-refusal guard numbers declared by the Community rollback file, plus
# the engine numbers a synthetic publish can legitimately raise. This stage
# handles synthetic content, so only these finite numbers may be recorded Ã¢â‚¬â€
# never message text, unlike the empty-forward stage.
POPULATED_STAGE_ERROR_NUMBERS = frozenset(
    {52486, 52487, 52488, 52489, 52490, 52491, 52492, 52512, 52513,
     102, 201, 206, 207, 208, 245, 257, 515, 547, 2601, 2627, 8152, 50000}
)
POPULATED_STAGE_ERROR_CODES = frozenset(
    f"populated_rollback_refusal_{label}e{number}"
    for label in ("", "publish_")
    for number in POPULATED_STAGE_ERROR_NUMBERS
)
CHILD_FAILURE_CODES = (
    CHILD_FAILURE_CODES
    | FORWARD_MIGRATION_ERROR_CODES
    | FORWARD_MIGRATION_CLASS_CODES
    | POPULATED_STAGE_ERROR_CODES
)


def _populated_stage_number(error: Exception) -> int | None:
    """Return an allowlisted number for the populated stage, or None.

    Numbers only. This stage contains synthetic content, so message text is
    never recorded here even though the empty-forward stage may record it.
    """
    text = str(error)
    for match in re.finditer(r"\b(\d{3,6})\b", text):
        number = int(match.group(1))
        if number in POPULATED_STAGE_ERROR_NUMBERS:
            return number
    lowered = text.lower()
    for phrase, number in ENGINE_ERROR_PHRASES:
        if phrase in lowered and number in POPULATED_STAGE_ERROR_NUMBERS:
            return number
    return None


FORWARD_COMPACT_PREFIX = "efm_"
# The idempotency stage re-applies the same files to the same empty database,
# so it carries the same disclosure reasoning and gets its own short tag.
IDEMPOTENCY_COMPACT_PREFIX = "ifm_"


def _normalized_message_token(error: Exception) -> str:
    """Reduce a driver message to a bounded lowercase token.

    Permitted only for the two stages that run against the still-empty
    database, empty_forward and forward_idempotency: nothing is inserted there,
    so a server message can only derive from public repository DDL Ã¢â‚¬â€ never
    member content, synthetic content, credentials, or environment values.
    """
    text = str(error)
    if "]" in text:
        text = text.rsplit("]", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _is_acceptable_child_code(code: object) -> bool:
    if not isinstance(code, str):
        return False
    if code in CHILD_FAILURE_CODES:
        return True
    if not re.fullmatch(r"[a-z0-9_]{1,80}", code):
        return False
    if any(
        code.startswith(f"{base}_m_") and len(code) > len(base) + 3
        for base in FORWARD_MIGRATION_FILE_CODES
    ):
        return True
    # Compact empty-forward message form. The long per-file prefix consumed so
    # much of the 80-character budget that the message was truncated past the
    # point of use, so the stage is identified by a short fixed tag instead.
    return any(
        code.startswith(prefix) and len(code) > len(prefix)
        for prefix in (FORWARD_COMPACT_PREFIX, IDEMPOTENCY_COMPACT_PREFIX)
    )


# Stable engine message fragments mapped to their fixed error numbers. The
# driver surfaces the server's message text without the numeric code, so the
# number is recovered by matching these known phrases. Only the allowlisted
# number is ever recorded.
ENGINE_ERROR_PHRASES = (
    ("invalid column name", 207),
    ("invalid object name", 208),
    ("incorrect syntax", 102),
    ("is not a recognized", 156),
    ("already an object named", 2714),
    ("cannot insert the value null", 515),
    ("reference constraint", 547),
    ("string or binary data", 8152),
    ("conversion failed", 245),
    ("arithmetic overflow", 8114),
    ("column name or number of supplied values", 213),
    ("cannot find the object", 4902),
    ("multiple cascade paths", 1785),
    ("not the same data type as referencing column", 1778),
    ("no primary or candidate keys", 1776),
    ("already exists on table", 1913),
    ("operand type clash", 206),
    ("could not create constraint", 1750),
    ("column names in each table must be unique", 2705),
    ("cannot define primary key", 8111),
)


def _sql_error_number(error: Exception, path: Path | None = None) -> int | None:
    """Recover a known SQL error number from a driver exception, if possible.

    Resolution order: an allowlisted number literally present in the message;
    a THROW message declared by the failing migration file itself (parsed from
    the file, mapped back to its declared number); a stable engine phrase.
    Only numbers inside ALLOWED_SQL_ERROR_NUMBERS may be returned, and the
    exception text itself is never recorded anywhere.
    """
    text = str(error)
    lowered = text.lower()
    for match in re.finditer(r"\b(\d{3,6})\b", text):
        number = int(match.group(1))
        if number in ALLOWED_SQL_ERROR_NUMBERS:
            return number
    if path is not None:
        try:
            source = Path(path).read_text(encoding="utf-8")
        except OSError:
            source = ""
        for declared in re.finditer(
            r"THROW\s+(\d{4,6})\s*,\s*''?([^';]{12,200}?)''?\s*,", source
        ):
            number = int(declared.group(1))
            message = declared.group(2).strip().lower()
            if number in ALLOWED_SQL_ERROR_NUMBERS and message and message in lowered:
                return number
    for phrase, number in ENGINE_ERROR_PHRASES:
        if phrase in lowered and number in ALLOWED_SQL_ERROR_NUMBERS:
            return number
    return None


def _per_file_forward_code(path: Path) -> str:
    """Map a migration file to its finite content-free failure code.

    The migration ID is the public filename prefix already recorded in the
    repository, so naming it discloses nothing. An unrecognized file falls
    back to the generic stage code.
    """
    name = getattr(path, "name", str(path))
    label = name.split("_")[0].lower().replace("-", "_")
    code = f"empty_forward_{label}"
    if code in FORWARD_MIGRATION_FILE_CODES:
        return code
    return "empty_forward_unexpected"


def _source_file_hashes() -> dict[str, str]:
    """Hash the three reviewed Community SQL files inside the client image.

    A missing or unreadable file is a distinct, content-free condition; without
    its own code it collapses into the generic preflight bucket and cannot be
    told apart from a SQL connection failure.
    """
    try:
        return {
            "forward": _sha256(COMMUNITY_FORWARD_PATH),
            "verifier": _sha256(COMMUNITY_VERIFY_PATH),
            "rollback": _sha256(COMMUNITY_ROLLBACK_PATH),
        }
    except OSError:
        raise ProofError("sql_source_files_unreadable") from None


CONTENT_REFUSAL_NUMBERS = (52490, 52491, 52492)


def _is_declared_content_refusal(error: Exception) -> bool:
    """True when the rollback refused because Community content exists.

    Matches the guard messages the rollback file declares for the
    content-present THROW numbers. Those messages are public repository text,
    not member or synthetic content, and nothing from the exception is
    recorded Ã¢â‚¬â€ only this boolean.
    """
    text = str(error).lower()
    if any(str(number) in text for number in CONTENT_REFUSAL_NUMBERS):
        return True
    try:
        source = COMMUNITY_ROLLBACK_PATH.read_text(encoding="utf-8")
    except OSError:
        return False
    for declared in re.finditer(r"THROW\s+(\d{5})\s*,\s*'([^']{10,300})'", source):
        number = int(declared.group(1))
        message = declared.group(2).strip().lower()
        if number in CONTENT_REFUSAL_NUMBERS and message and message in text:
            return True
    return False


def _coded(code: str, action):
    """Run one raw proof statement under its own finite failure code.

    The populated stage records numbers only, never message text, because it
    holds synthetic content. When no allowlisted number matches, a distinct
    code per statement is the only thing that localises the failure.
    """
    try:
        return action()
    except ProofError:
        raise
    except Exception:
        raise ProofError(code) from None


def _assert_purge_actually_runs(connection_string: str) -> None:
    """Execute the purge against real synthetic content and prove it worked.

    The proof previously only applied and rolled back migrations, so a purge
    that could never commit passed every check (independent review 2026-08-04,
    F2: emptying the body violated the body-length constraint). Executing it
    is the only thing that would have caught that.
    """
    with _connect(connection_string) as connection:
        cursor = connection.cursor()
        _coded(
            "purge_count_query_failed",
            lambda: cursor.execute(
                "SELECT COUNT_BIG(*) FROM dbo.community_posts "
                "WHERE publication_state=N'deleted' AND purged_at_utc IS NULL"
            ),
        )
        if int(cursor.fetchone()[0]) < 1:
            raise ProofError("purge_precondition_missing")

        def run_purge():
            cursor.execute(
                "EXEC dbo.usp_PurgeCommunityContent @RetentionDays=?,@BatchSize=?",
                (1, 100),
            )
            while True:
                if cursor.description is not None:
                    cursor.fetchall()
                if not cursor.nextset():
                    break

        _coded("purge_execution_failed", run_purge)

        # A tombstone must exist with an emptied body: proof the purge both
        # ran and committed.
        _coded(
            "purge_verify_query_failed",
            lambda: cursor.execute(
                "SELECT COUNT_BIG(*) FROM dbo.community_posts "
                "WHERE purged_at_utc IS NOT NULL AND LEN(body)=0"
            ),
        )
        if int(cursor.fetchone()[0]) < 1:
            raise ProofError("purge_left_content_unpurged")

        # A held record must never be purged.
        _coded(
            "purge_hold_query_failed",
            lambda: cursor.execute(
                "SELECT COUNT_BIG(*) FROM dbo.community_posts "
                "WHERE legal_hold_reason IS NOT NULL AND purged_at_utc IS NOT NULL"
            ),
        )
        if int(cursor.fetchone()[0]) != 0:
            raise ProofError("purge_ignored_a_legal_hold")


def _populated_rollback_refusal_step(populated_connection: str, runner) -> None:
    """Prove rollback refuses while Community content exists.

    Each sub-operation reports a distinct allowlisted code so a failure names
    which one broke. Only numbers are recorded here: this stage creates
    synthetic content, so message text must never enter the evidence.
    """

    def guarded(label: str, action):
        try:
            return action()
        except ProofError:
            raise
        except Exception as error:
            number = _populated_stage_number(error)
            if number is not None:
                candidate = f"populated_rollback_refusal_{label}e{number}"
                if candidate in CHILD_FAILURE_CODES:
                    raise ProofError(candidate) from None
            raise ProofError("populated_rollback_refusal_unexpected") from None

    guarded(
        "",
        lambda: _with_connection_env(
            populated_connection,
            lambda: runner.apply_migrations(runner.forward_migrations()),
        ),
    )
    guarded(
        "",
        lambda: _with_connection_env(
            populated_connection,
            lambda: runner.apply_migrations(
                runner.selected_optional_migrations(COMMUNITY_MIGRATION_IDS)
            ),
        ),
    )
    guarded("publish_", lambda: _publish_synthetic_post(populated_connection))
    guarded("", lambda: _assert_populated_refusal(populated_connection, runner))
    # The purge runs LAST, and deliberately so. It leaves body-free tombstones,
    # and the retention rollback correctly refuses while any tombstone exists —
    # restoring the original body constraint would otherwise leave the table
    # violating its own constraint. Purging before the rollback assertions
    # above would block them on a guard that is doing its job.
    guarded("publish_", lambda: _remove_synthetic_post(populated_connection))
    guarded("publish_", lambda: _assert_purge_actually_runs(populated_connection))


def _validate_job_local_sql_target(
    host: str, password: str, expected_ip: str, expected_machine: str
) -> dict[str, str]:
    try:
        resolved = {
            result[4][0]
            for result in socket.getaddrinfo(host, 1433, socket.AF_INET, socket.SOCK_STREAM)
        }
    except OSError as error:
        raise ProofError("sql_job_local_name_resolution_failed") from error
    if resolved != {expected_ip}:
        raise ProofError("sql_job_local_address_mismatch")
    master = _connection_string(host, "masterdb", password).replace(
        "Database=masterdb", "Database=master"
    )
    # Prove plain TCP reachability before the driver runs. This splits a job
    # network problem from a driver load, TLS, or authentication problem,
    # which are otherwise indistinguishable in a content-free record. The
    # probe opens and closes a socket and reads nothing.
    try:
        probe = socket.create_connection((host, 1433), timeout=15)
    except OSError:
        raise ProofError("sql_tcp_unreachable") from None
    else:
        probe.close()
    # With TCP proven, a failure here is driver load, TLS negotiation, or
    # authentication rather than reachability. Distinguish TLS from the other
    # two by retrying once without encryption: if the unencrypted attempt
    # succeeds, the driver and credentials are fine and the encrypted
    # handshake is the sole problem. The probe connection is closed
    # immediately and never used for a proof step, so the proof itself still
    # only ever runs encrypted.
    try:
        connection = _connect(master)
    except Exception:
        try:
            probe_connection = _connect(master.replace("Encrypt=yes", "Encrypt=no"))
        except Exception:
            raise ProofError("sql_connect_failed") from None
        else:
            try:
                probe_connection.close()
            except Exception:
                pass
            raise ProofError("sql_connect_failed_tls_only") from None
    try:
        with connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT CAST(SERVERPROPERTY('MachineName') AS nvarchar(128)), "
                "CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(128)), "
                "CAST(SERVERPROPERTY('Edition') AS nvarchar(128))"
            )
            machine, version, edition = map(str, cursor.fetchone())
    except Exception:
        raise ProofError("sql_identity_query_failed") from None
    if machine != expected_machine:
        raise ProofError("sql_machine_identity_mismatch")
    if version != SQL_BUILD or "Developer" not in edition:
        raise ProofError("sql_build_or_edition_unexpected")
    return {"version": version, "edition": "Developer", "machine_bound": True}


def run_inside() -> dict[str, object]:
    steps: list[dict[str, object]] = []
    started = time.monotonic()
    sql_identity: dict[str, str] | None = None
    created: list[str] = []
    host = ""
    password = ""
    source_sha = ""

    def run_step(name: str, action):
        step_started = time.monotonic()
        result = _run_child_stage(name, action)
        steps.append(
            {
                "name": name,
                "status": "pass",
                "duration_seconds": round(time.monotonic() - step_started, 3),
            }
        )
        return result

    try:
        def prepare():
            validate_inside_environment()
            prepared_host = os.environ.get("PROOF_SQL_HOST", "")
            prepared_password = os.environ.get("PROOF_SQL_PASSWORD", "")
            proof_id = os.environ.get("PROOF_ID", "")
            expected_ip = os.environ.get("PROOF_SQL_EXPECTED_IP", "")
            expected_machine = os.environ.get("PROOF_SQL_EXPECTED_MACHINE", "")
            prepared_source_sha = _safe_source_sha(
                os.environ.get("PROOF_SOURCE_SHA", "")
            )
            if not SAFE_ID_PATTERN.fullmatch(proof_id) or not prepared_password:
                raise ProofError("proof_environment_invalid")
            return {
                "host": prepared_host,
                "password": prepared_password,
                "proof_id": proof_id,
                "expected_ip": expected_ip,
                "expected_machine": expected_machine,
                "source_sha": prepared_source_sha,
                "runner": _load_migration_runner(),
                "file_sha256": _source_file_hashes(),
            }

        prepared = _run_child_stage("preflight", prepare)
        host = prepared["host"]
        password = prepared["password"]
        proof_id = prepared["proof_id"]
        expected_ip = prepared["expected_ip"]
        expected_machine = prepared["expected_machine"]
        source_sha = prepared["source_sha"]
        runner = prepared["runner"]
        file_sha256 = prepared["file_sha256"]
        empty_database = f"PeerSlateCommunityEmpty_{proof_id.replace('-', '_')}"
        populated_database = (
            f"PeerSlateCommunityPopulated_{proof_id.replace('-', '_')}"
        )

        sql_identity = run_step(
            "preflight",
            lambda: _validate_job_local_sql_target(
                host, password, expected_ip, expected_machine
            ),
        )

        def create_databases():
            for database in (empty_database, populated_database):
                _create_database(host, password, database)
                created.append(database)
            return (
                _connection_string(host, empty_database, password),
                _connection_string(host, populated_database, password),
            )

        empty_connection, populated_connection = _run_child_stage(
            "database_setup", create_databases
        )

        def apply_forward_per_file():
            paths = list(runner.forward_migrations()) + list(
                runner.selected_optional_migrations(COMMUNITY_MIGRATION_IDS)
            )
            for path in paths:
                code = _per_file_forward_code(path)
                try:
                    _with_connection_env(
                        empty_connection,
                        lambda p=path: runner.apply_migrations([p]),
                    )
                except ProofError:
                    raise
                except Exception as error:
                    # Prefer the bounded message: it names the offending
                    # construct, where the error number alone only says a
                    # syntax error exists somewhere in 1,786 lines.
                    token = _normalized_message_token(error)
                    # The outer harness prefixes "inside_" before sealing and
                    # the pipeline sealer caps failure_code at 80 characters.
                    # The per-file prefix alone leaves too little room to read
                    # the message, so use the compact stage tag and spend the
                    # budget on the message itself.
                    budget = 80 - len("inside_") - len(FORWARD_COMPACT_PREFIX)
                    token = token[:budget].rstrip("_")
                    if token:
                        raise ProofError(
                            f"{FORWARD_COMPACT_PREFIX}{token}"
                        ) from None
                    number = _sql_error_number(error, path)
                    if number is not None:
                        candidate = f"{code}_e{number}"
                        if candidate in CHILD_FAILURE_CODES:
                            raise ProofError(candidate) from None
                    class_name = type(error).__name__.lower()
                    if class_name in ALLOWED_EXCEPTION_CLASS_NAMES:
                        raise ProofError(f"{code}_x{class_name}") from None
                    raise ProofError(code) from None

        def reapply_forward_per_file():
            """Re-apply every migration on its own, foundation included.

            Two reasons this covers the foundation migrations and not only the
            Community ones.

            First, diagnosis: applying all three Community files at once
            reported a single forward_idempotency_unexpected, which says only
            that re-application broke somewhere across three files. Per-file
            application with the same bounded-message treatment as the first
            application names the offending construct instead of the stage.

            Second, and the reason the foundation files were added on
            2026-08-04: this proof only ever re-applied the Community
            migrations, so nothing established that a foundation migration is
            safe to run twice. That mattered the moment production's ledger
            turned out to be missing PS-PLAT-000 -- the only supported way to
            add it is to re-run the whole foundation set, and there was no
            evidence that doing so was safe. Now there is, or this stage fails.
            """
            paths = list(runner.forward_migrations()) + list(
                runner.selected_optional_migrations(COMMUNITY_MIGRATION_IDS)
            )
            for path in paths:
                try:
                    _with_connection_env(
                        empty_connection,
                        lambda p=path: runner.apply_migrations([p]),
                    )
                except ProofError:
                    raise
                except Exception as error:
                    token = _normalized_message_token(error)
                    budget = 80 - len("inside_") - len(IDEMPOTENCY_COMPACT_PREFIX)
                    token = token[:budget].rstrip("_")
                    if token:
                        raise ProofError(
                            f"{IDEMPOTENCY_COMPACT_PREFIX}{token}"
                        ) from None
                    raise ProofError("forward_idempotency_unexpected") from None

        run_step("empty_forward", apply_forward_per_file)
        run_step("forward_idempotency", reapply_forward_per_file)
        run_step(
            "two_owner_verifier",
            lambda: (
                _with_connection_env(
                    empty_connection,
                    lambda: (runner.verify_foundation(), runner.verify_community()),
                ),
                _assert_empty_after_verifier(empty_connection),
            ),
        )
        run_step(
            "empty_rollback",
            lambda: (
                # Reverse order: retention's objects sit on the Community
                # tables, so its rollback must run before theirs.
                _with_connection_env(
                    empty_connection,
                    lambda: runner.apply_migrations(
                        [RESTORE_ROLLBACK_PATH, RETENTION_ROLLBACK_PATH, COMMUNITY_ROLLBACK_PATH]
                    ),
                ),
                _assert_empty_rollback(empty_connection),
            ),
        )

        run_step(
            "populated_rollback_refusal",
            lambda: _populated_rollback_refusal_step(
                populated_connection, runner
            ),
        )
    finally:
        cleanup_ok = True
        for database in reversed(created):
            try:
                _drop_database(host, password, database)
            except Exception:
                cleanup_ok = False
        password = ""
        if not cleanup_ok:
            raise ProofError("database_cleanup_unconfirmed")

    return {
        "schema_version": 1,
        "status": "pass",
        "classification": "disposable_x64_nonproduction_sql_runtime",
        "source_sha": source_sha,
        "sql": sql_identity,
        "steps": steps,
        "database_cleanup_confirmed": True,
        "file_sha256": file_sha256,
        "duration_seconds": round(time.monotonic() - started, 3),
        "contains_member_data": False,
        "production_action": False,
    }


def plan_record() -> dict[str, object]:
    return {
        "status": "plan_only",
        "remote_execution_authorized": False,
        "sql_image": SQL_IMAGE,
        "client_base_image": CLIENT_IMAGE,
        "client_artifact_identity": "inspect_build_and_execute_by_content_id",
        "required_host": "ubuntu-22.04-x86_64",
        "steps": list(PROOF_STEPS),
        "prohibitions": [
            "production_or_azure_database",
            "repository_or_member_secret",
            "retention_implementation",
            "community_flag_activation",
            "candidate_release_or_deployment",
            "host_port_or_volume",
            "broad_docker_prune",
        ],
    }


def execute_proof(source_sha: str, evidence_path: Path) -> int:
    validate_execute_host()
    _validate_image(SQL_IMAGE, SQL_IMAGE, "sql")
    _validate_image(CLIENT_IMAGE, CLIENT_IMAGE, "client")
    source_sha = _safe_source_sha(source_sha)
    proof_id = uuid.uuid4().hex[:12]
    names = _resource_names(proof_id)
    evidence_path = evidence_path.resolve()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result: dict[str, object] = {
        "schema_version": 1,
        "status": "fail",
        "classification": "disposable_x64_nonproduction_sql_runtime",
        "source_sha": source_sha,
        "steps": [],
        "contains_member_data": False,
        "production_action": False,
    }
    cleanup_ok = False
    client_artifact_id = ""
    with tempfile.TemporaryDirectory(prefix="peerslate-community-sql-proof-") as directory:
        temporary = Path(directory)
        sql_env = temporary / "sql.env"
        client_env = temporary / "client.env"
        context = temporary / "client-context"
        context.mkdir()
        password = _password()
        try:
            source_sha = _validate_source_sha_at_head(source_sha)
            docker_info = json.loads(
                _run(
                    ["docker", "info", "--format", "{{json .}}"],
                    boundary="docker_info",
                    timeout=60,
                ).stdout
            )
            validate_docker_server(docker_info)
            _run(
                ["docker", "pull", SQL_IMAGE_TAG],
                boundary="sql_image_pull",
                timeout=900,
            )
            repo_digests = json.loads(
                _run(
                    [
                        "docker",
                        "image",
                        "inspect",
                        "--format",
                        "{{json .RepoDigests}}",
                        SQL_IMAGE_TAG,
                    ],
                    boundary="sql_digest_inspect",
                    timeout=60,
                ).stdout
            )
            expected_repo_digest = f"mcr.microsoft.com/mssql/server@{SQL_IMAGE_DIGEST}"
            if expected_repo_digest not in repo_digests:
                raise ProofError("sql_image_digest_verification_failed")
            _build_context(context)
            _run(
                [
                    "docker",
                    "build",
                    "--pull",
                    "--build-arg",
                    f"CLIENT_IMAGE={CLIENT_IMAGE}",
                    "--tag",
                    names["client_image"],
                    str(context),
                ],
                boundary="client_image_build",
                timeout=900,
            )
            client_artifact_id = _run(
                [
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    "{{.Id}}",
                    names["client_image"],
                ],
                boundary="client_image_inspect",
                timeout=60,
            ).stdout.strip().lower()
            if not IMAGE_ID_PATTERN.fullmatch(client_artifact_id):
                raise ProofError("client_artifact_identity_invalid")
            names["client_image_cleanup"] = client_artifact_id
            _run(
                ["docker", "network", "create", "--internal", names["network"]],
                boundary="network_create",
            )
            _write_private_env(
                sql_env,
                {
                    "ACCEPT_EULA": "Y",
                    "MSSQL_PID": "Developer",
                    "MSSQL_SA_PASSWORD": password,
                },
            )
            _run(
                [
                    "docker",
                    "run",
                    "--detach",
                    "--name",
                    names["sql_container"],
                    "--hostname",
                    names["sql_container"],
                    "--network",
                    names["network"],
                    "--network-alias",
                    "community-sql",
                    "--env-file",
                    str(sql_env),
                    SQL_IMAGE,
                ],
                boundary="sql_container_start",
                timeout=120,
            )
            _wait_for_sql(names["sql_container"])
            sql_container = _inspect_sql_container(names)
            _write_private_env(
                client_env,
                {
                    "CI": "true",
                    "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED": "false",
                    "PROOF_ID": proof_id,
                    "PROOF_SOURCE_SHA": source_sha,
                    "PROOF_SQL_HOST": "community-sql",
                    "PROOF_SQL_PASSWORD": password,
                    "PROOF_SQL_EXPECTED_IP": sql_container["ip_address"],
                    "PROOF_SQL_EXPECTED_MACHINE": sql_container["machine_name"],
                },
            )
            client_result = _run(
                _client_run_command(names, client_env, client_artifact_id),
                boundary="client_proof",
                timeout=1800,
                check=False,
                text=False,
            )
            result = _client_result_record(client_result, source_sha)
            result["agent"] = {
                "os": "ubuntu-22.04",
                "architecture": "x86_64",
                "docker_version": str(docker_info.get("ServerVersion") or "unknown"),
            }
            result["images"] = {
                "sql": SQL_IMAGE,
                "client_base": CLIENT_IMAGE,
                "client_artifact_id": client_artifact_id,
            }
        except ProofError as error:
            result["failure_code"] = str(error)
        except Exception:
            result["failure_code"] = "unexpected_proof_failure"
        finally:
            password = ""
            cleanup_started = time.monotonic()
            cleanup_ok = _cleanup_exact(names)
            result["cleanup_confirmed"] = cleanup_ok
            cleanup_steps = [
                step
                for step in result.get("steps", [])
                if isinstance(step, dict) and step.get("name") != "cleanup"
            ]
            cleanup_steps.append(
                {
                    "name": "cleanup",
                    "status": "pass" if cleanup_ok else "fail",
                    "duration_seconds": round(time.monotonic() - cleanup_started, 3),
                }
            )
            result["steps"] = cleanup_steps
            result["duration_seconds"] = round(time.monotonic() - started, 3)
            if not cleanup_ok:
                result["status"] = "fail"
                result["failure_code"] = "container_cleanup_unconfirmed"
            evidence_path.write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
    return 0 if result.get("status") == "pass" and cleanup_ok else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Print the inert proof plan.")
    mode.add_argument("--execute", action="store_true", help="Run on authorized x64 CI.")
    mode.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--source-sha", default="")
    parser.add_argument("--evidence", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.inside:
        try:
            record = run_inside()
        except ProofError as error:
            record = {
                "schema_version": 1,
                "status": "fail",
                "failure_code": str(error),
                "contains_member_data": False,
                "production_action": False,
            }
        except Exception:
            record = {
                "schema_version": 1,
                "status": "fail",
                "failure_code": "preflight_unexpected",
                "contains_member_data": False,
                "production_action": False,
            }
        print(json.dumps(record, sort_keys=True))
        return 0 if record.get("status") == "pass" else 1
    if not args.execute:
        print(json.dumps(plan_record(), indent=2, sort_keys=True))
        return 0
    if not args.source_sha or args.evidence is None:
        raise SystemExit("--execute requires --source-sha and --evidence")
    return execute_proof(args.source_sha, args.evidence)


if __name__ == "__main__":
    sys.exit(main())
