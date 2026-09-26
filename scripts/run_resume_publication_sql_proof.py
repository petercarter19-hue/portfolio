"""Disposable Resume publication SQL proof.

Plan mode is the default and never starts Docker, opens a DSN, or mutates
schema. --execute is implemented for a dispatcher who has verified Pete's
separate exact approval for this source, resource plan, and one run. The
runner checks matching queue inputs but cannot authenticate that approval:
a caller who controls both inputs can make them match. Missing or mismatched
inputs refuse without contacting resources.

A client-supplied DSN is never the approved resource identity. Engine proof
remains prepared, not executed, until an authorized isolated Docker run
succeeds against the pinned images and invocation-owned databases.

Authorized execute prepares a hashed Linux CPython 3.12 wheelhouse, bakes it
with reviewed source and required OS libraries into a tagged client image,
installs only locked local wheels during the image build, and runs oracles in
the isolated client. --in-client-oracles is the inner entrypoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import sys
from uuid import UUID


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PROOF_ID = "ps-mvp1-ef-sql-proof-20260916-01"
SOURCE_FILES = (
    ROOT / "SQL FIles" / "Migrations" / "registry.json",
    ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-RESUME-CATALOG-001_curated_catalog.sql",
    ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-RESUME-CATALOG-001_curated_catalog_rollback.sql",
    ROOT / "SQL FIles" / "Verification" / "PS-RESUME-CATALOG-001_curated_catalog_verify.sql",
    ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-RESUME-PUBLICATION-001_publication.sql",
    ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-RESUME-PUBLICATION-001_publication_rollback.sql",
    ROOT / "SQL FIles" / "Verification" / "PS-RESUME-PUBLICATION-001_publication_verify.sql",
    ROOT / "scripts" / "run_resume_publication_sql_proof.py",
    ROOT / "scripts" / "configure_resume_publication_sql_authority.py",
    ROOT / "azure-pipelines-resume-publication-sql-proof.yml",
    ROOT / "requirements-resume-publication-sql-proof.txt",
    ROOT / "services" / "resume_publication_adapters.py",
)
PROOF_STEPS = (
    "preflight",
    "empty_forward",
    "codec_and_evidence",
    "two_connection_race",
    "injected_rollback",
    "application_principal_permissions",
    "empty_rollback",
    "cleanup",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan() -> dict:
    from services.resume_publication_adapters import (
        CLIENT_IMAGE,
        PROOF_CLIENT_CONTAINER,
        PROOF_CLIENT_CPUS,
        PROOF_CLIENT_MEMORY,
        PROOF_CLIENT_PACKAGING,
        PROOF_EMPTY_DATABASE,
        PROOF_JOB_TIMEOUT_SECONDS,
        PROOF_NETWORK,
        PROOF_POPULATED_DATABASE,
        PROOF_SQL_CONTAINER,
        PROOF_SQL_CPUS,
        PROOF_SQL_MEMORY,
        REQUIRED_PUBLICATION_CLOSURE_IDS,
        SQL_IMAGE,
        resolve_publication_migration_closure,
    )

    files = []
    for path in SOURCE_FILES:
        files.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    closure = resolve_publication_migration_closure(ROOT)
    return {
        "mode": "plan",
        "proof_id": PROOF_ID,
        "status": "proposal_not_executed",
        "prepared_not_executed": True,
        "execute_authorized": False,
        "client_dsn_accepted": False,
        "python": "3.12",
        "client_oracles": True,
        "migrations": list(REQUIRED_PUBLICATION_CLOSURE_IDS),
        "closure": closure,
        "files": files,
        "sql_image": SQL_IMAGE,
        "client_image": CLIENT_IMAGE,
        "client_packaging": {
            "method": PROOF_CLIENT_PACKAGING,
            "plan_image_name": "peerslate-mvp1-e-sql-proof:20260916-01",
            "reconciled": True,
            "reason": (
                "A temporary Dockerfile builds the pinned python:3.12-slim base with "
                "required OS libraries, the hash-verified wheelhouse, and reviewed "
                "source. pip installs only locked local wheels during docker build; "
                "the tagged image's content ID is inspected before isolated execution."
            ),
        },
        "limits": {
            "job_timeout_seconds": PROOF_JOB_TIMEOUT_SECONDS,
            "client_oracle_timeout_seconds": 30 * 60,
            "sql_memory": PROOF_SQL_MEMORY,
            "sql_cpus": PROOF_SQL_CPUS,
            "client_memory": PROOF_CLIENT_MEMORY,
            "client_cpus": PROOF_CLIENT_CPUS,
            "cleanup_window_seconds": 5 * 60,
        },
        "network": PROOF_NETWORK,
        "containers": {
            "sql": PROOF_SQL_CONTAINER,
            "client": PROOF_CLIENT_CONTAINER,
        },
        "databases": [PROOF_EMPTY_DATABASE, PROOF_POPULATED_DATABASE],
        "steps": list(PROOF_STEPS),
        "dependency_hashes_recorded_at_execute": False,
        "dependency_lock": {
            "file": "requirements-resume-publication-sql-proof.txt",
            "source": "pypi_published_metadata",
            "platform": "cp312-manylinux_x86_64_glibc",
            "downloaded_bytes_independently_verified": False,
            "install_requires_hashes": True,
            "install_offline": "--require-hashes --no-index --find-links",
        },
        "exclusions": [
            "production schema",
            "production permissions",
            "feature enablement",
            "historical one-use authorization reuse",
            "client-supplied DSN resource identity",
            "host job_local_connect as oracle runtime",
        ],
    }


def authorization_permits_execute(authorization_ref: str) -> bool:
    """Check queue input consistency; dispatcher verification is separate."""

    expected = os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_AUTHORIZATION", "").strip()
    proof_id = os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_ID", "").strip()
    execute_flag = os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_EXECUTE", "").strip().lower()
    if execute_flag != "authorized":
        return False
    if proof_id != PROOF_ID:
        return False
    if not expected or not authorization_ref or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,300}", authorization_ref):
        return False
    if authorization_ref != expected:
        return False
    if os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_PRODUCTION", "").lower() == "true":
        return False
    return True


def _refuse_execute(*, reason: str, authorization_ref_present: bool) -> int:
    print(
        json.dumps(
            {
                "status": "refused",
                "reason": reason,
                "proof_id": PROOF_ID,
                "authorization_ref_present": authorization_ref_present,
                "contacted_resources": False,
            },
            indent=2,
        ),
        file=sys.stderr,
    )
    return 2


def _write_evidence(evidence_path: Path, result: dict) -> None:
    def encode_driver_value(value):
        if isinstance(value, UUID):
            return str(value)
        raise TypeError(f"Unsupported proof evidence type: {type(value).__name__}")

    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=encode_driver_value) + "\n",
        encoding="utf-8",
    )


def _base_result(source_sha: str, ordered_ids: list[str], required_ids: list[str]) -> dict:
    return {
        "schema_version": 1,
        "status": "fail",
        "proof_id": PROOF_ID,
        "source_sha": source_sha,
        "classification": "disposable_x64_nonproduction_sql_runtime",
        "contains_member_data": False,
        "production_action": False,
        "prepared_not_executed": True,
        "client_dsn_accepted": False,
        "client_oracles": True,
        "python": "3.12",
        "steps": list(PROOF_STEPS),
        "closure_ids": ordered_ids,
        "required_closure_ids": required_ids,
        "dependency_lock": {
            "file": "requirements-resume-publication-sql-proof.txt",
            "source": "pypi_published_metadata",
            "downloaded_bytes_independently_verified": False,
            "install_offline": "--require-hashes --no-index --find-links",
        },
    }


def _secret_values(runtime) -> tuple[str, ...]:
    values = []
    if runtime is not None:
        secret = getattr(runtime, "_sql_password", "")
        if secret:
            values.append(str(secret))
    env_secret = os.environ.get("MSSQL_SA_PASSWORD", "")
    if env_secret:
        values.append(env_secret)
    return tuple(values)


def _migration_callables(closure, connect, resource_identity, apply_forward, apply_rollback, verify):
    from services.resume_publication_adapters import (
        EngineProofError, PROOF_EMPTY_DATABASE, apply_sql_file, run_capture_rollback_contracts,
    )

    forward_invocations = {}

    def run_files(connection, items, key, phase, after_file=None):
        # Each registered file is executed as one unchanged driver batch.
        for batch_number, item in enumerate(items, 1):
            try:
                apply_sql_file(connection, ROOT / item[key])
                if after_file:
                    after_file(item)
            except Exception as error:
                raise EngineProofError(
                    f"migration_phase_{phase}_migration_{item['id']}_batch_{batch_number}_failed: {error}"
                ) from error

    def default_forward(database_identity: str) -> dict:
        connection = connect(database_identity)
        try:
            invocation = forward_invocations.get(database_identity, 0) + 1
            forward_invocations[database_identity] = invocation
            evidence = {}

            def after_file(item):
                if (database_identity == f"{resource_identity}:{PROOF_EMPTY_DATABASE}"
                        and invocation == 1 and item["id"] == "PS-CAPTURE-001"):
                    evidence["capture_rollback"] = run_capture_rollback_contracts(connection)

            run_files(connection, closure, "forward", "forward" if invocation == 1 else "reapply", after_file)
            return evidence
        finally:
            connection.close()

    def default_rollback(database_identity: str) -> None:
        connection = connect(database_identity)
        try:
            run_files(connection, reversed(closure), "rollback", "rollback")
        finally:
            connection.close()

    def default_verify(database_identity: str) -> None:
        connection = connect(database_identity)
        try:
            run_files(connection, [item for item in closure if item.get("verify")], "verify", "verify")
        finally:
            connection.close()

    return (
        apply_forward or default_forward,
        apply_rollback or default_rollback,
        verify or default_verify,
    )


def execute_in_client_oracles(
    source_sha: str,
    evidence_path: Path,
    *,
    connect=None,
    apply_forward=None,
    apply_rollback=None,
    verify=None,
    codec_fields=None,
) -> int:
    """Inner isolated-client entrypoint. Secrets come from the process environment."""

    from services.resume_publication_adapters import (
        EngineProofError,
        PROOF_EMPTY_DATABASE,
        REQUIRED_PUBLICATION_CLOSURE_IDS,
        connect_from_client_environment,
        refuse_client_supplied_dsn,
        resolve_publication_migration_closure,
        run_publication_sql_oracles,
        sanitize_proof_error,
    )

    refuse_client_supplied_dsn(os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_DSN", "").strip())
    closure = resolve_publication_migration_closure(ROOT)
    ordered_ids = [item["id"] for item in closure]
    result = _base_result(source_sha, ordered_ids, list(REQUIRED_PUBLICATION_CLOSURE_IDS))
    result["engine"] = {"oracles": run_publication_sql_oracles.__name__}
    opener = connect or connect_from_client_environment
    host = os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_HOST", "").strip()
    resource_identity = f"docker:{host or PROOF_EMPTY_DATABASE}"
    try:
        if opener is connect_from_client_environment and not os.environ.get("MSSQL_SA_PASSWORD"):
            raise EngineProofError("sql_secret_missing")
        forward, rollback, check = _migration_callables(
            closure, opener, resource_identity, apply_forward, apply_rollback, verify
        )
        result["prepared_not_executed"] = False
        payload = run_publication_sql_oracles(
            resource_identity,
            opener,
            apply_forward=forward,
            apply_rollback=rollback,
            verify=check,
            ordered_ids=ordered_ids,
            codec_fields=codec_fields,
        )
        result["status"] = "pass"
        result["prepared_not_executed"] = False
        result["oracles"] = payload.get("oracles", payload)
        _write_evidence(evidence_path, result)
        return 0
    except Exception as error:
        result["status"] = "fail"
        result["error"] = sanitize_proof_error(error, _secret_values(None))
        _write_evidence(evidence_path, result)
        return 1


def execute_proof(
    source_sha: str,
    evidence_path: Path,
    *,
    authorization_ref: str | None = None,
    runtime=None,
    connect=None,
    apply_forward=None,
    apply_rollback=None,
    verify=None,
    codec_fields=None,
) -> int:
    """Authorized disposable proof. Imports engine adapters only after the gate.

    Injected connect adapters exercise oracles without Docker. Injected runtime
    adapters must still acquire, bake, verify, and run client oracles.
    A client DSN is never used as the resource identity. Host job_local_connect
    is not the oracle runtime.
    """

    from services.resume_publication_adapters import (
        EngineProofError,
        IsolatedDockerCliRuntime,
        CLIENT_IMAGE,
        REQUIRED_PUBLICATION_CLOSURE_IDS,
        SQL_IMAGE,
        acquire_isolated_sql_runtime,
        assert_reviewed_source,
        cleanup_owned_resources,
        refuse_client_supplied_dsn,
        resolve_publication_migration_closure,
        run_publication_sql_oracles,
        sanitize_proof_error,
        source_manifest,
        manifest_digest,
    )

    refuse_client_supplied_dsn(os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_DSN", "").strip())

    closure = resolve_publication_migration_closure(ROOT)
    ordered_ids = [item["id"] for item in closure]
    result = _base_result(source_sha, ordered_ids, list(REQUIRED_PUBLICATION_CLOSURE_IDS))
    result["migration_closure"] = closure
    result["approval"] = {
        "decision_ref": authorization_ref,
        "boundary": "dispatcher_verified_process_only",
        "independently_authenticated_by_runner": False,
    }
    result["run_context"] = {
        "azure_build_id": os.environ.get("BUILD_BUILDID") if os.environ.get("BUILD_BUILDID", "").isdigit() else None,
        "azure_definition_id": os.environ.get("BUILD_DEFINITIONID") if os.environ.get("BUILD_DEFINITIONID", "").isdigit() else None,
        "azure_job_id": os.environ.get("SYSTEM_JOBID") if re.fullmatch(r"[0-9a-fA-F-]{36}", os.environ.get("SYSTEM_JOBID", "")) else None,
        "host_os": platform.system(),
        "host_platform": platform.platform(),
        "host_python": platform.python_version(),
        "azure_agent_image_version": os.environ.get("IMAGEVERSION")
        if re.fullmatch(r"[A-Za-z0-9._-]{1,100}", os.environ.get("IMAGEVERSION", "")) else None,
    }
    result["image_pins"] = {"sql": SQL_IMAGE, "client_base": CLIENT_IMAGE}
    result["engine"] = {"oracles": run_publication_sql_oracles.__name__}
    result["proof_status"] = "fail"
    result["cleanup_status"] = "not_attempted"

    if runtime is None and connect is None:
        linux = platform.system().lower() == "linux"
        amd64 = platform.machine().lower() in {"x86_64", "amd64"}
        if not linux or not amd64:
            result["status"] = "prepared_not_executed"
            result["proof_status"] = "prepared_not_executed"
            result["reason"] = "execute_host_not_authorized"
            _write_evidence(evidence_path, result)
            return 3
        runtime = IsolatedDockerCliRuntime()

    owned: list = []
    proof_status = "fail"
    cleanup_status = "not_attempted"
    previous_handlers = {}
    cancelled = False

    def on_cancel(_signum, _frame):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise EngineProofError("proof_cancelled")

    try:
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[signum] = signal.signal(signum, on_cancel)
        if runtime is None:
            resource_identity = "injected://resume-publication-sql-proof"
            forward, rollback, check = _migration_callables(
                closure, connect, resource_identity, apply_forward, apply_rollback, verify
            )
            payload = run_publication_sql_oracles(
                resource_identity,
                connect,
                apply_forward=forward,
                apply_rollback=rollback,
                verify=check,
                ordered_ids=ordered_ids,
                codec_fields=codec_fields,
            )
            proof_status = payload.get("status") or "fail"
            result["prepared_not_executed"] = False
            result["oracles"] = payload.get("oracles", payload)
        else:
            bound_sha = assert_reviewed_source(source_sha, ROOT)
            result["source_sha"] = bound_sha
            manifest = source_manifest(ROOT)
            result["source_manifest_digest"] = manifest_digest(manifest)
            acquired = acquire_isolated_sql_runtime(runtime, owned=owned, expected_manifest=manifest)
            wheel = acquired.get("wheelhouse") or {}
            result["wheelhouse"] = wheel
            result["dependency_lock"]["downloaded_bytes_independently_verified"] = bool(
                wheel.get("downloaded_bytes_independently_verified")
            )
            result["dependency_lock"]["downloaded_bytes_source"] = wheel.get("source")
            result["resource_identity"] = acquired["resource_identity"]
            result["client_packaging"] = acquired.get("client_packaging")
            result["client_image_id"] = acquired.get("client_image_id")
            result["invocation_marker"] = acquired.get("invocation_marker")
            result["sql_identity"] = acquired.get("identity")
            result["client_runtime"] = acquired.get("client_runtime", {"status": "unavailable"})
            payload = runtime.run_client_oracles(
                source_sha=bound_sha,
                apply_forward=apply_forward,
                apply_rollback=apply_rollback,
                verify=verify,
                codec_fields=codec_fields,
            )
            result["prepared_not_executed"] = False
            result["oracles"] = payload.get("oracles", payload)
            proof_status = payload.get("status") or "fail"
            if proof_status != "pass" or payload.get("client_exit") not in (None, 0):
                proof_status = "fail"
    except Exception as error:
        result["error"] = sanitize_proof_error(error, _secret_values(runtime))
        proof_status = "fail"
    finally:
        result["acquired_resources"] = [
            {key: resource.get(key) for key in ("name", "kind", "id", "marker", "uncertain")}
            for resource in owned
        ]
        try:
            if runtime is not None:
                try:
                    cleanup = cleanup_owned_resources(runtime, owned)
                    cleanup_status = cleanup.get("status") or "fail"
                    result["cleanup"] = cleanup
                except Exception as error:
                    cleanup_status = "fail"
                    result["cleanup"] = {"status": "fail", "attempts": [],
                                         "error": sanitize_proof_error(error, _secret_values(runtime))}
        finally:
            for signum, previous in previous_handlers.items():
                signal.signal(signum, previous)
        result["proof_status"] = proof_status
        result["cleanup_status"] = cleanup_status
        if cleanup_status == "fail":
            result["status"] = "fail"
            _write_evidence(evidence_path, result)
            return 1
        if proof_status != "pass":
            result["status"] = "fail"
            _write_evidence(evidence_path, result)
            return 1
        result["status"] = "pass"
        _write_evidence(evidence_path, result)
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--in-client-oracles", action="store_true")
    parser.add_argument("--authorization-ref", default="")
    parser.add_argument("--source-sha", default="")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args(argv)
    if args.in_client_oracles:
        evidence = args.evidence or Path("/tmp/resume-publication-sql-proof.json")
        return execute_in_client_oracles(args.source_sha, evidence)
    if args.execute:
        if not authorization_permits_execute(args.authorization_ref):
            return _refuse_execute(
                reason=(
                    "SQL execution requires dispatcher-verified owner approval "
                    "and matching queue inputs; resources were not contacted."
                ),
                authorization_ref_present=bool(args.authorization_ref),
            )
        evidence = args.evidence or (ROOT / "tmp-resume-publication-sql-proof.json")
        return execute_proof(args.source_sha, evidence, authorization_ref=args.authorization_ref)
    print(json.dumps(plan(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
