"""Bounded worker entry for one Settings account-export job (C2).

Claims exactly one job via dbo.usp_ClaimAccountExportJob under a
DEDICATED worker SQL identity -- never the application's own
AZURE_SQL_CONNECTIONSTRING (ACCOUNT_EXPORT_WORKER_SQL_CONNECTIONSTRING
below, following the exact
scripts/interview_ai/run_interview_telemetry_purge.py house pattern of
a maintenance-class script owning its own connection-string variable).
services/database_service.py is deliberately NOT used here: its
ALLOWED_PROCEDURES allowlist is outside this claim's frozen surfaces
and does not list any of the eight account-export procedures, and
reusing the shared application connection would also contradict C1's
recorded intent that the five worker procedures are reserved for "a
future dedicated worker identity...distinct from the application and
maintenance identities" (C1_ACCOUNT_EXPORT_FOUNDATION.md, "Grant
model"). This script calls those procedures directly over its own
connection instead.

Sequence: claim -> enforce owner-active (a direct, parameterized SELECT
-- usp_ClaimAccountExportJob itself has no owner-active predicate, a
recorded C1->C2 obligation, and no new procedure is possible under this
claim's frozen surfaces, so this is the sanctioned interim mechanism; a
later slice may formalize it as a procedure) -> assemble a FIXTURE-ONLY
archive (no domain reader exists yet; every domain file this worker
ever sees is synthetic, never real member content) -> stage and
promote it through the private Blob adapter -> complete or fail the
job through the C1 lease-fenced procedures. Every log line is
content-free: job_key, state, and bounded counts only.

FIXTURE WARNING: this worker completes every job it claims with
SYNTHETIC placeholder content, because no real domain-reader slice
exists yet (see docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/
C2_ACCOUNT_EXPORT_ASSEMBLY.md, "What is fixture-proven vs unproven").
Running it against a database that might hold a REAL member's queued
export request would complete that request with fake content -- a
genuine trust violation. main() refuses to run at all unless
ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED is explicitly set, on top
of the existing --expect-database guard.

Not wired to any scheduler, route, or UI. Run by hand from an operator
shell only.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.account_export_assembly_service import (  # noqa: E402
    account_export_assembly_service,
)
from services.account_export_storage_service import (  # noqa: E402
    AccountExportStorageError,
    account_export_storage_service,
)


LOGGER = logging.getLogger("account_export_worker")

CONNECTION_ENV = "ACCOUNT_EXPORT_WORKER_SQL_CONNECTIONSTRING"
FIXTURE_MODE_ENV = "ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})

# The exact closed vocabulary usp_FailAccountExportJob accepts (SQL
# FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation.sql,
# CK_account_export_jobs_failure_code minus 'attempts_exhausted', which
# only usp_ClaimAccountExportJob's own stale-lease reap may set -- the
# fail procedure itself throws 57241 for any code outside this list).
# Kept as a Python-side mirror so an invalid code is refused here,
# offline, before it ever reaches the database.
FAILURE_CODES = frozenset(
    {
        "domain_unavailable",
        "assembly_timeout",
        "hash_mismatch",
        "oversize_compressed",
        "oversize_uncompressed",
        "internal_error",
        "worker_unavailable",
    }
)

# C0's trust boundary treats an owner whose authorization is no longer
# valid as making every domain's read contract unsatisfiable at once
# ("A domain that cannot satisfy its contract is unavailable or
# excluded before readiness" -- C0_ACCOUNT_EXPORT_ARCHITECTURE.md,
# "Trust and identity boundary"). No enum value names authorization
# directly; among the seven usp_FailAccountExportJob accepts,
# 'domain_unavailable' is the closest true statement: the owner's
# deactivation makes the complete requested domain set unavailable, not
# an internal bug ('internal_error') or an infrastructure shortage
# ('worker_unavailable').
OWNER_INACTIVE_FAILURE_CODE = "domain_unavailable"

# usp_FailAccountExportJob's own hardcoded @MaxAttempts (not a parameter,
# per the migration: "DECLARE @MaxAttempts int = 3;"). It requeues to
# 'queued' (retaining the failure code) while attempt_count < this, and
# only terminates to 'failed' once attempts are exhausted. A worker log
# claiming state='failed' unconditionally would misreport every
# requeued attempt as terminal.
MAX_ATTEMPTS = 3

# Content-free log allowlist. A field not in this set is silently
# dropped rather than raising, so a future call site cannot leak a new
# field into a log line by forgetting to widen this set first.
_LOG_FIELD_NAMES = frozenset(
    {
        "stage",
        "job_key",
        "state",
        "attempt",
        "compressed_size_bytes",
        "uncompressed_size_bytes",
        "file_count",
        "failure_code",
        "error_type",
    }
)


def content_free_log_fields(**fields):
    """Keep only the allowlisted, content-free fields for one log line.

    Public (no leading underscore) because it is the unit-testable
    core of this script's logging contract -- see
    tests/test_account_export_storage.py.
    """

    return {
        name: value
        for name, value in fields.items()
        if name in _LOG_FIELD_NAMES and value is not None
    }


def _log(stage, **fields):
    LOGGER.info(json.dumps(content_free_log_fields(stage=stage, **fields), sort_keys=True))


def normalize_job_key(value):
    """Return the canonical lowercase-with-dashes string form of a
    uniqueidentifier value, whether the driver handed back a str or a
    uuid.UUID."""

    if isinstance(value, uuid.UUID):
        return str(value)
    return str(uuid.UUID(str(value)))


def choose_failure_code_for_error(error):
    """Map an internal exception to one of the seven codes
    usp_FailAccountExportJob accepts.

    A cap breach or a hash mismatch keeps its exact, more truthful
    code; only a genuinely unrecognized condition collapses to
    'internal_error'.
    """

    code = getattr(error, "code", None)
    if code in ("oversize_compressed", "oversize_uncompressed", "hash_mismatch"):
        return code
    if code in ("storage_unavailable", "storage_access_denied"):
        return "worker_unavailable"
    if isinstance(error, TimeoutError):
        return "assembly_timeout"
    return "internal_error"


def post_fail_state(attempt):
    """The truthful ledger state after calling usp_FailAccountExportJob
    for a job claimed at this ``attempt`` count: 'queued' (requeued,
    attempts remain) or 'failed' (terminal, attempts exhausted) --
    never a hardcoded 'failed' regardless of which actually happened.
    """

    return "failed" if attempt >= MAX_ATTEMPTS else "queued"


def verify_promoted_hash(assembled, promoted):
    """Defense in depth: the SHA-256 promote() independently recomputed
    from what is actually persisted must match what assembly computed
    before upload. Raises AccountExportStorageError("hash_mismatch")
    -- mapped by choose_failure_code_for_error to the same closed-enum
    code -- on any disagreement, so a corrupted-in-transit archive is
    never completed as 'ready'.
    """

    if promoted["sha256"] != assembled["sha256"]:
        raise AccountExportStorageError("hash_mismatch")


def is_owner_active(cursor, owner_user_id, owner_profile_id):
    """The sanctioned interim owner-active check (a recorded C1->C2
    obligation: usp_ClaimAccountExportJob has no owner-active
    predicate). Mirrors the exact predicate
    usp_RequestAccountExportForOwner already trusts
    (app_users.active AND member_profiles.active), applied here to the
    claimed job's already-resolved owner ids rather than to a
    @UserKey. No new procedure is created or called -- this is a
    direct, parameterized SELECT, never dynamic SQL.
    """

    cursor.execute(
        "SELECT TOP (1) 1 "
        "FROM dbo.app_users AS app_user "
        "JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id "
        "WHERE app_user.id = ? AND profile.profile_id = ? "
        "AND app_user.active = 1 AND profile.active = 1;",
        (owner_user_id, owner_profile_id),
    )
    return cursor.fetchone() is not None


def fetch_requested_at_utc(cursor, job_key):
    """usp_ClaimAccountExportJob's own SELECT list does not include
    requested_at_utc (see its result columns in the migration: job_key,
    owner_user_id, owner_profile_id, attempt_count, lease_token,
    lease_expires_at_utc only), so it is fetched here with a second,
    direct, job_key-scoped read. This names no @UserKey and returns no
    member content -- job ledger metadata only, exactly the same
    'sanctioned interim direct read' shape as is_owner_active above.
    """

    cursor.execute(
        "SELECT requested_at_utc FROM dbo.account_export_jobs WHERE job_key = ?;",
        (job_key,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def read_consistency_marker(cursor):
    """A plain @@DBTS read -- a database-internal counter, never
    member content -- matching C0's "SQL consistency markers"
    requirement. Not a domain reader: it names no member table."""

    cursor.execute("SELECT @@DBTS AS marker;")
    row = cursor.fetchone()
    value = row[0] if row else None
    return bytes(value) if value is not None else None


def claim_job(cursor):
    """Claim exactly one job. Returns a dict of claimed fields, or
    ``None`` when nothing is claimable.

    usp_ClaimAccountExportJob produces NO result set at all in the
    nothing-to-claim case (COMMIT then a bare RETURN, no SELECT) --
    the same shape C1_ACCOUNT_EXPORT_FOUNDATION.md records for
    usp_GetAccountExportStatusForOwner's unresolved-identity path.
    ``cursor.description`` is ``None`` in that case; this function
    checks it explicitly rather than calling fetchone() blind.
    """

    cursor.execute("EXEC dbo.usp_ClaimAccountExportJob;")
    if cursor.description is None:
        return None
    columns = [column[0] for column in cursor.description]
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row))


def complete_job(
    cursor,
    *,
    job_key,
    lease_token,
    assembly_started_at_utc,
    assembly_cutoff_at_utc,
    consistency_marker_start,
    consistency_marker_cutoff,
    final_artifact_reference,
    final_artifact_sha256,
    compressed_size_bytes,
    uncompressed_size_bytes,
):
    cursor.execute(
        "EXEC dbo.usp_CompleteAccountExportJob "
        "@JobKey = ?, @LeaseToken = ?, @AssemblyStartedAtUtc = ?, "
        "@AssemblyCutoffAtUtc = ?, @ConsistencyMarkerStart = ?, "
        "@ConsistencyMarkerCutoff = ?, @FinalArtifactReference = ?, "
        "@FinalArtifactSha256 = ?, @CompressedSizeBytes = ?, "
        "@UncompressedSizeBytes = ?;",
        (
            job_key,
            lease_token,
            assembly_started_at_utc,
            assembly_cutoff_at_utc,
            consistency_marker_start,
            consistency_marker_cutoff,
            final_artifact_reference,
            final_artifact_sha256,
            compressed_size_bytes,
            uncompressed_size_bytes,
        ),
    )


def fail_job(cursor, *, job_key, lease_token, failure_code):
    if failure_code not in FAILURE_CODES:
        raise ValueError("Invalid account export failure code.")
    cursor.execute(
        "EXEC dbo.usp_FailAccountExportJob "
        "@JobKey = ?, @LeaseToken = ?, @FailureCode = ?;",
        (job_key, lease_token, failure_code),
    )


def _now_utc():
    """A naive UTC datetime, matching every other SYSUTCDATETIME()-
    facing value in this codebase (e.g.
    services/community_media_storage.py's _parse_scan_time)."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso_z(value):
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def build_fixture_domain_files(read_window_started_at_utc, read_window_ended_at_utc):
    """The worker's OWN hardcoded fixture set -- an injected iterable
    of already-shaped domain files, per this claim's frozen scope. No
    domain reader may be written under this claim, and no domain
    file's content here may resemble real member data: every string is
    an obvious, labeled placeholder.

    One entry per disposition, so a real assembly run always exercises
    all three shapes end to end, not only the happy path.
    """

    return [
        {
            "path": "domains/account_profile.ndjson",
            "domain_code": "account_profile",
            "schema_id": "peerslate.account_profile.v1",
            "schema_version": 1,
            "disposition": "included",
            "content": (
                b'{"note":"SYNTHETIC ACCOUNT EXPORT FIXTURE - NOT REAL MEMBER '
                b'DATA","profile_display_name":"Synthetic Fixture Member"}\n'
            ),
            "record_count": 1,
            "provenance": {
                "source": "fixture",
                "domain_reader": "not_yet_implemented",
            },
            "read_window": {
                "started_at_utc": read_window_started_at_utc,
                "ended_at_utc": read_window_ended_at_utc,
            },
        },
        {
            "path": "domains/community_authored_content.ndjson",
            "domain_code": "community_authored_content",
            "schema_id": "peerslate.community_authored_content.v1",
            "schema_version": 1,
            "disposition": "excluded",
            "omission_reason": (
                "C0 V1 domain matrix: no domain-reader slice is claimed yet "
                "for Community authored content."
            ),
        },
        {
            "path": "domains/journal.ndjson",
            "domain_code": "journal",
            "schema_id": "peerslate.journal.v1",
            "schema_version": 1,
            "disposition": "unavailable",
            "failure_reason": (
                "PS-JOURNAL-001 is unapplied; no legal source table exists yet "
                "(C0 V1 domain matrix)."
            ),
        },
    ]


def run_once(connection, *, fixture_domain_files):
    """Claim and process exactly one job on the given connection.

    Returns a content-free outcome dict. Only an unexpected, defensive
    condition (not an ordinary business outcome such as no claimable
    job or an inactive owner) ever propagates as an exception.
    """

    cursor = connection.cursor()
    claimed = claim_job(cursor)
    if claimed is None:
        _log("claim", state="idle")
        return {"outcome": "idle"}

    job_key = normalize_job_key(claimed["job_key"])
    lease_token = claimed["lease_token"]
    owner_user_id = claimed["owner_user_id"]
    owner_profile_id = claimed["owner_profile_id"]
    attempt = int(claimed["attempt_count"])
    _log("claimed", job_key=job_key, state="running", attempt=attempt)

    if not is_owner_active(cursor, owner_user_id, owner_profile_id):
        try:
            fail_job(
                cursor,
                job_key=job_key,
                lease_token=lease_token,
                failure_code=OWNER_INACTIVE_FAILURE_CODE,
            )
            _log(
                "failed",
                job_key=job_key,
                state=post_fail_state(attempt),
                failure_code=OWNER_INACTIVE_FAILURE_CODE,
            )
        except Exception:
            # Same reasoning as the general error path below: the
            # lease is very likely already gone, and there is nothing
            # more this attempt can safely do about it.
            _log("fail_job_refused", job_key=job_key, state="running")
        return {
            "outcome": "failed",
            "job_key": job_key,
            "failure_code": OWNER_INACTIVE_FAILURE_CODE,
        }

    try:
        assembly_started_at_utc = _now_utc()
        consistency_marker_start = read_consistency_marker(cursor)
        assembly_cutoff_at_utc = _now_utc()
        consistency_marker_cutoff = read_consistency_marker(cursor)

        domain_files = fixture_domain_files(
            _iso_z(assembly_started_at_utc), _iso_z(assembly_cutoff_at_utc)
        )
        requested_at_utc = fetch_requested_at_utc(cursor, job_key)
        if requested_at_utc is None:
            # Unreachable today -- requested_at_utc is NOT NULL in
            # dbo.account_export_jobs -- but C0's no-false-promise rule
            # means this worker must fail loudly rather than fabricate
            # a request time it could not actually read (substituting
            # the worker's own start time would misreport when the
            # member actually asked).
            raise RuntimeError("requested_at_utc could not be read for the claimed job.")

        assembled = account_export_assembly_service.assemble(
            domain_files,
            job_key=job_key,
            requested_at_utc=_iso_z(requested_at_utc),
            assembly_started_at_utc=_iso_z(assembly_started_at_utc),
            assembly_cutoff_at_utc=_iso_z(assembly_cutoff_at_utc),
            consistency_marker_start=(
                consistency_marker_start.hex() if consistency_marker_start else None
            ),
            consistency_marker_cutoff=(
                consistency_marker_cutoff.hex() if consistency_marker_cutoff else None
            ),
        )
        _log(
            "assembled",
            job_key=job_key,
            state="running",
            attempt=attempt,
            compressed_size_bytes=assembled["compressed_size_bytes"],
            uncompressed_size_bytes=assembled["uncompressed_size_bytes"],
            file_count=len(assembled["manifest"]["files"]),
        )

        account_export_storage_service.stage(job_key, attempt, assembled["archive_bytes"])
        promoted = account_export_storage_service.promote(job_key, attempt)
        verify_promoted_hash(assembled, promoted)
        _log(
            "stored",
            job_key=job_key,
            state="running",
            compressed_size_bytes=promoted["compressed_size_bytes"],
            uncompressed_size_bytes=promoted["uncompressed_size_bytes"],
        )

        complete_job(
            cursor,
            job_key=job_key,
            lease_token=lease_token,
            assembly_started_at_utc=assembly_started_at_utc,
            assembly_cutoff_at_utc=assembly_cutoff_at_utc,
            consistency_marker_start=consistency_marker_start,
            consistency_marker_cutoff=consistency_marker_cutoff,
            final_artifact_reference=promoted["reference"],
            final_artifact_sha256=promoted["sha256"],
            compressed_size_bytes=promoted["compressed_size_bytes"],
            uncompressed_size_bytes=promoted["uncompressed_size_bytes"],
        )
        _log(
            "completed",
            job_key=job_key,
            state="ready",
            compressed_size_bytes=promoted["compressed_size_bytes"],
            uncompressed_size_bytes=promoted["uncompressed_size_bytes"],
        )
        return {"outcome": "completed", "job_key": job_key}
    except Exception as error:  # noqa: BLE001 -- every failure funnels to one bounded fail-job call
        failure_code = choose_failure_code_for_error(error)
        _log(
            "error",
            job_key=job_key,
            state="running",
            error_type=type(error).__name__,
            failure_code=failure_code,
        )
        # Best-effort: a staging object may or may not have been
        # written by the point of failure. cleanup_staging is
        # idempotent (absence is success), so it is always safe to
        # call here regardless of which stage failed, and it prevents
        # an abandoned attempt's bytes from lingering in the private
        # container indefinitely. Its own failure is swallowed: it
        # must never mask the real error or block the fail-job call
        # below, and there is no ledger column this claim can use to
        # record a leftover staging object's cleanup state anyway (no
        # procedure sets cleanup_state for a 'failed' row).
        try:
            account_export_storage_service.cleanup_staging(job_key, attempt)
        except Exception:
            _log("cleanup_staging_failed", job_key=job_key, state="running")
        try:
            fail_job(cursor, job_key=job_key, lease_token=lease_token, failure_code=failure_code)
            _log("failed", job_key=job_key, state=post_fail_state(attempt), failure_code=failure_code)
        except Exception:
            # Most likely the lease is already gone -- reaped by a
            # later claim after this attempt's lease expired, or
            # already completed/failed by a previous, since-timed-out
            # invocation of this same script. There is nothing more
            # this attempt can safely do to a job it no longer holds.
            _log("fail_job_refused", job_key=job_key, state="running")
        return {"outcome": "failed", "job_key": job_key, "failure_code": failure_code}


def _connect(connection_string):
    from mssql_python import connect

    connection = connect(connection_string, timeout=30)
    connection.setautocommit(True)
    return connection


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-database", required=True)
    arguments = parser.parse_args(argv)

    if str(os.environ.get(FIXTURE_MODE_ENV, "")).strip().lower() not in _TRUE_VALUES:
        LOGGER.error(
            "Refusing to run: %s is not confirmed. This worker has no real "
            "domain reader yet and completes every job with SYNTHETIC "
            "fixture content only.",
            FIXTURE_MODE_ENV,
        )
        return 1

    connection_string = os.environ.get(CONNECTION_ENV)
    if not connection_string:
        LOGGER.error("%s is not configured.", CONNECTION_ENV)
        return 1

    try:
        connection = _connect(connection_string)
    except Exception as error:
        LOGGER.error(
            "Account export worker could not connect: error_type=%s.",
            type(error).__name__,
        )
        return 1

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DB_NAME();")
        actual_database = cursor.fetchone()[0]
        if actual_database != arguments.expect_database:
            LOGGER.error("Account export worker refused an unexpected database target.")
            return 1

        result = run_once(connection, fixture_domain_files=build_fixture_domain_files)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["outcome"] in ("idle", "completed") else 1
    finally:
        try:
            connection.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
