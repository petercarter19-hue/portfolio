"""Bounded worker entry for one Settings account-export job (C2/CR5).

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
later slice may formalize it as a procedure) -> resolve the owner's own
@UserKey (fetch_owner_user_key -- a second sanctioned interim read, not
a second identity-resolution path: see its own docstring) -> read every
DOMAINS-included reader for that owner through
services/account_export_domain_readers.py, plus one honest,
reason-carrying excluded/unavailable entry for every other DOMAINS row
(build_domain_files_from_readers) -> assemble the real archive -> stage
and promote it through the private Blob adapter -> complete the job
atomically (ledger rows + ready) through usp_CompleteAccountExportWithDomains,
or fail it through C1's lease-fenced usp_FailAccountExportJob. Every log line is
content-free: job_key, state, and bounded counts only.

PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001 (this package)
retired the C2 fixture-only worker: build_fixture_domain_files and the
ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED tripwire it required are
both gone, in this same change, replaced by
build_domain_files_from_readers and the tests that pin the real-reader
path (tests/test_account_export_integration.py -- every DOMAINS
included reader invoked exactly once per job; no fixture source left in
this module). This worker now reads and exports REAL member content
for every domain services/account_export_domain_readers.py's DOMAINS
registry marks "included" (12 domains, 31 readers today); every other
domain still appears in the manifest as an honest, reasoned
"excluded"/"unavailable" entry, never silently dropped. Still not wired
to any scheduler, route, or UI -- run by hand from an operator shell
only -- and production authority remains withheld: nothing in this
package deploys, schedules, or exposes this worker, and no migration or
gate is part of this claim.

Determinism. services/account_export_assembly_service.py's own
assemble() call remains a pure function: identical input (including
identical read-window timestamps) always produces byte-identical
output -- unit-tested directly and unchanged by this package. What
changes is what now FEEDS that function during a live run:
build_domain_files_from_readers embeds each reader's own real,
wall-clock read-window timestamps into every included file. Because a
fresh reader call captures a fresh timestamp, two SEPARATE ATTEMPTS at
the SAME job will generally produce DIFFERENT archive bytes and a
different sha256 even when every underlying row is unchanged --
byte-identical reproducibility ACROSS ATTEMPTS was never literally true
once real read windows entered the picture, and this package states
that explicitly rather than letting the older, narrower pure-function
claim be misread as a live-run guarantee. What remains invariant across
attempts: every emitted byte is fully accounted for in the manifest,
every count/hash is independently recomputed from real content, and
the domain set/dispositions/reasons are stable for a given owner
(DOMAINS is a static registry) -- exactly what C0 itself requires
("this is a bounded assembly window, not an atomic request-time
snapshot").

Manifest/ledger agreement -- now enforced end to end. Since
PS-SETTINGS-EXPORT-010, C1's child ledger
(dbo.account_export_job_domains) HAS its writer:
dbo.usp_CompleteAccountExportWithDomains, which this worker calls as
its one completion path, inserting the thirty per-domain rows and
transitioning the job to ready in a single transaction.
summarize_domain_ledger and domain_ledger_row_matches_check_shape below
compute and validate the exact rows that call sends -- shaped against
C1's own CK_account_export_job_domains_shape CHECK text -- and the
integration suite proves they agree, file by file and domain by domain,
with the manifest and with the bytes actually serialized into the ZIP.
run_once additionally refuses, BEFORE any storage write, a summary that
is not exactly the canonical domain set (assert_domain_ledger_complete),
and bounds every over-long reason explicitly so the ledger can never
hold an engine-truncated record that disagrees with the manifest. The
aggregate artifact facts still come from
AccountExportStorageService.promote()'s own independent readback, never
from a pre-upload estimate.md, "Manifest/ledger agreement").

Retention maintenance (PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001).
The same entrypoint also owns the retention half C3 recorded as
"expiry is not deletion": --maintenance runs run_maintenance instead
of run_once -- EXEC dbo.usp_ExpireAccountExportJobs first (ledger
expiry), then, for exactly the past-ready jobs whose cleanup_state
is 'pending', idempotent physical deletion through
AccountExportStorageService followed -- only after a successful
delete -- by dbo.usp_CleanupAccountExportJob. Never a deletion for a
still-downloadable job; never a cleaned mark before the delete; a
failed delete leaves the job pending for the next run and fails this
run loudly. Like run_once, this mode is not wired to any scheduler,
route, or UI -- run by hand from an operator shell only until the
separately gated worker-host decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal


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
from services.account_export_domain_readers import DOMAINS  # noqa: E402


LOGGER = logging.getLogger("account_export_worker")

CONNECTION_ENV = "ACCOUNT_EXPORT_WORKER_SQL_CONNECTIONSTRING"

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
        # Maintenance-mode fields (PS-SETTINGS-ACCOUNT-EXPORT-WORKER-
        # OPS-001): bounded counts only, deliberately widened here --
        # never a reason, domain, or artifact reference.
        "expired_count",
        "cleaned_count",
        "cleanup_failed_count",
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


def fetch_owner_user_key(cursor, owner_user_id, owner_profile_id):
    """The one sanctioned identity-translation read this package adds.

    The claimed job row (usp_ClaimAccountExportJob) resolves and
    returns owner_user_id/owner_profile_id -- internal identity -- but
    every domain-reader procedure in services/account_export_domain_
    readers.py takes only the member's own external @UserKey (the same
    shape usp_RequestAccountExportForOwner itself accepts). This is NOT
    a second identity-resolution path: it is a single, direct,
    parameterized lookup of the SAME already-resolved row's own
    user_key column, scoped by the exact ids the claim procedure itself
    just returned -- never a caller-supplied value, never a fresh
    credential/session check. It is the same "sanctioned interim read"
    shape is_owner_active and fetch_requested_at_utc already use. The
    active = 1 predicate is repeated here even though is_owner_active
    already confirmed it immediately before this call in run_once, so
    this function's own SQL text remains independently correct even if
    a future caller ever invoked it without that ordering guarantee.

    Returns the member's own user_key string, or None if no row matches
    both ids together (unreachable today given run_once's own ordering,
    guarded defensively there exactly like fetch_requested_at_utc's own
    NULL handling).
    """

    cursor.execute(
        "SELECT TOP (1) app_user.user_key "
        "FROM dbo.app_users AS app_user "
        "JOIN dbo.member_profiles AS profile ON profile.user_id = app_user.id "
        "WHERE app_user.id = ? AND profile.profile_id = ? "
        "AND app_user.active = 1 AND profile.active = 1;",
        (owner_user_id, owner_profile_id),
    )
    row = cursor.fetchone()
    return row[0] if row else None


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

LEDGER_REASON_MAX_CHARS = 200  # dbo.account_export_job_domains' column bound


def _bound_ledger_reason(reason):
    """Bound a reason for the 200-character ledger column, explicitly.

    Seven real DOMAINS reasons exceed 200 characters. The manifest keeps
    the full text; the ledger row stores this bounded excerpt, marked with
    an ellipsis so a reader knows it is one. Explicit here, and refused
    loudly by the procedure (57281) if anything longer ever arrives, so
    the engine can never truncate silently into a record that disagrees
    mid-sentence with the archive.
    """

    if reason is None or len(reason) <= LEDGER_REASON_MAX_CHARS:
        return reason
    return reason[: LEDGER_REASON_MAX_CHARS - 1] + "\u2026"


def build_domain_ledger_payload(domain_ledger_summary, manifest):
    """One JSON payload row per canonical domain, for the atomic completion.

    Values come from summarize_domain_ledger (already validated against the
    CHECK shape) plus a per-domain provenance roll-up: the sorted, distinct
    reader procedures the manifest recorded for that domain's included
    files. Sorted so the payload is deterministic byte-for-byte for a given
    manifest, matching the assembly service's own determinism discipline.
    """

    provenance_by_domain = {}
    for entry in manifest["files"]:
        if entry["disposition"] != "included":
            continue
        procedures = provenance_by_domain.setdefault(entry["domain_code"], set())
        provenance = entry.get("provenance") or {}
        reader_procedure = provenance.get("reader_procedure")
        if reader_procedure:
            procedures.add(reader_procedure)

    payload = []
    for domain_code in sorted(domain_ledger_summary):
        row = domain_ledger_summary[domain_code]
        procedures = sorted(provenance_by_domain.get(domain_code, ()))
        payload.append(
            {
                "domain_code": domain_code,
                "disposition": row["disposition"],
                "record_count": row["record_count"],
                "byte_count": row["byte_count"],
                "content_sha256": row["content_sha256"],
                "read_started_at_utc": row["read_started_at_utc"],
                "read_ended_at_utc": row["read_ended_at_utc"],
                "omission_reason": _bound_ledger_reason(row["omission_reason"]),
                "failure_reason": _bound_ledger_reason(row["failure_reason"]),
                "provenance_json": (
                    json.dumps({"reader_procedures": procedures}, sort_keys=True)
                    if procedures
                    else None
                ),
            }
        )
    return payload


def assert_domain_ledger_complete(domain_ledger_summary):
    """Refuse, BEFORE any storage write, a summary that is not exactly the
    canonical domain set.

    Ordering is the point, not redundancy: the final object's name is
    job-scoped and promote refuses overwrite, so a payload defect
    discovered after promote would strand the job permanently -- every
    retry re-assembles, hits storage_conflict, and burns an attempt until
    the reaper fails the job. Validating completeness here means the only
    failures possible after the archive physically exists are
    infrastructure failures, which retries CAN cure. The procedure
    re-validates everything server-side regardless; this is the belt, the
    procedure is the braces.
    """

    expected = set(DOMAINS)
    actual = set(domain_ledger_summary)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise RuntimeError(
            "Domain ledger summary is not the canonical set"
            + (" missing=" + ",".join(missing) if missing else "")
            + (" extra=" + ",".join(extra) if extra else "")
        )


def complete_job_with_domains(
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
    domain_ledger_payload,
):
    """The atomic completion: ledger rows + ready in one procedure call.

    The worker's connection is autocommit, so both-or-neither cannot live
    here -- it lives inside dbo.usp_CompleteAccountExportWithDomains,
    which validates the payload again, derives job/owner identity from the
    locked row, re-checks owner-active under the lock, inserts exactly the
    canonical per-domain rows, and transitions the job to ready in one
    transaction. C1's usp_CompleteAccountExportJob remains untouched and
    is no longer called by this worker.
    """

    cursor.execute(
        "EXEC dbo.usp_CompleteAccountExportWithDomains "
        "@JobKey = ?, @LeaseToken = ?, @AssemblyStartedAtUtc = ?, "
        "@AssemblyCutoffAtUtc = ?, @ConsistencyMarkerStart = ?, "
        "@ConsistencyMarkerCutoff = ?, @FinalArtifactReference = ?, "
        "@FinalArtifactSha256 = ?, @CompressedSizeBytes = ?, "
        "@UncompressedSizeBytes = ?, @DomainLedgerJson = ?;",
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
            json.dumps(domain_ledger_payload, sort_keys=True),
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


def expire_ready_jobs(cursor):
    """One bare ``EXEC dbo.usp_ExpireAccountExportJobs;`` -- the ledger
    half of retention: every ready job past its ready_expires_at_utc
    becomes 'expired' (blocking download; physical deletion is the
    separate, later step below). The procedure's own default @BatchSize
    (500) governs its internal bounded-batch loop, so no parameter is
    passed here; its single result set is one expired_count row, read
    back for content-free logging. SET NOCOUNT ON inside the procedure
    means that SELECT is the only result set, so an absent result is a
    defect worth failing loudly on -- never silently reported as zero.
    """

    cursor.execute("EXEC dbo.usp_ExpireAccountExportJobs;")
    if cursor.description is None:
        raise RuntimeError("usp_ExpireAccountExportJobs returned no result set.")
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("usp_ExpireAccountExportJobs returned no expired_count row.")
    return int(row[0])


def fetch_cleanup_pending_jobs(cursor):
    """The maintenance sweep's own ledger read: exactly the jobs whose
    physical artifacts may be deleted under C1's contract --
    cleanup_state 'pending' AND state 'expired' or 'failed', the two
    states usp_CleanupAccountExportJob itself accepts (it throws 57257
    for 'ready'; 'queued'/'running' can never be 'pending' per
    CK_account_export_jobs_cleanup_pair). 'ready' is deliberately
    absent: a still-downloadable job's artifact is untouchable, which is
    the sacred half of the retention rule.

    This is the same sanctioned interim direct-read shape as
    fetch_requested_at_utc above: job ledger metadata only (job_key,
    state, attempt_count), no @UserKey, no member content, no dynamic
    SQL. attempt_count is read so a failed job's per-attempt staging
    leftovers can be swept; the states are fixed literals from the
    ledger's own closed CHECK vocabulary, never caller input.
    """

    cursor.execute(
        "SELECT job_key, state, attempt_count "
        "FROM dbo.account_export_jobs "
        "WHERE cleanup_state = N'pending' "
        "AND state IN (N'expired', N'failed') "
        "ORDER BY account_export_job_id;"
    )
    # Values are returned RAW: run_maintenance normalizes and converts
    # per job inside its own per-row isolation, so one malformed ledger
    # row cannot abort the whole sweep here before any cleanup ran.
    return [
        {"job_key": row[0], "state": row[1], "attempt_count": row[2]}
        for row in cursor.fetchall()
    ]


def mark_job_cleaned(cursor, job_key):
    """Record one job's completed physical cleanup:
    ``EXEC dbo.usp_CleanupAccountExportJob @JobKey = ?``. Called ONLY
    after every storage delete for that job succeeded -- the mark must
    never precede the delete, or the ledger would claim a deletion that
    did not happen. The procedure is idempotent (a concurrently cleaned
    job returns 'cleaned' without re-transitioning), refuses a
    still-ready job with 57257 as an independent, database-side
    enforcement of the same ordering rule, and appends the
    account_export.cleaned audit event itself. Returns the procedure's
    own reported cleanup_state.
    """

    cursor.execute("EXEC dbo.usp_CleanupAccountExportJob @JobKey = ?;", (job_key,))
    if cursor.description is None:
        raise RuntimeError("usp_CleanupAccountExportJob returned no result set.")
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("usp_CleanupAccountExportJob returned no row.")
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row)).get("cleanup_state")


def _now_utc():
    """A naive UTC datetime, matching every other SYSUTCDATETIME()-
    facing value in this codebase (e.g.
    services/community_media_storage.py's _parse_scan_time)."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso_z(value):
    # timespec="microseconds" forces a FIXED six-digit fractional-second
    # field even when it is exactly zero. Without it,
    # datetime.isoformat() silently varies the string's WIDTH (the
    # fractional part is omitted entirely when microsecond == 0), which
    # would make plain lexical comparison of two _iso_z() outputs
    # disagree with true chronological order -- exactly the property
    # summarize_domain_ledger's min()/max() over read-window strings
    # depends on below.
    return (
        value.replace(tzinfo=timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _iso_z_or_none(value):
    return _iso_z(value) if value is not None else None


def _json_safe(value):
    """Coerce one driver-returned column value into a JSON-encodable
    Python primitive, losslessly: date/datetime -> ISO-8601 string
    (matching _iso_z's own formatting convention elsewhere in this
    file); Decimal -> str (never float, which would silently lose or
    distort precision); bytes/bytearray -> hex string; uuid.UUID ->
    str. Every other type (str, int, float, bool, None) passes through
    unchanged -- json.dumps already handles those natively.
    """

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _serialize_ndjson_rows(rows):
    """Encode a reader's content rows (each an ordered dict of plain
    column-name -> value, exactly as services/account_export_domain_
    readers.py returns them -- the two read-window columns already
    stripped) as UTF-8 NDJSON bytes: one compact JSON object per line,
    in the rows' own order, with each row's own key order preserved
    (the procedure's own SELECT list order -- never sorted or
    alphabetized). Zero rows encodes to ``b""`` -- a legitimate,
    empty-but-included file; see
    services/account_export_assembly_service.py's own relaxed
    "included may be empty" rule this depends on.
    """

    lines = [
        json.dumps(
            {key: _json_safe(value) for key, value in row.items()},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for row in rows
    ]
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_domain_files_from_readers(connection, user_key):
    """The real content source, replacing the retired fixture builder:
    one manifest file per reader for every services/account_export_
    domain_readers.py DOMAINS entry whose disposition is "included" (22
    readers across 7 domains today; see iter_included_readers()), plus
    exactly one file for every other DOMAINS entry, carrying that
    domain's own disposition and reason string VERBATIM -- never
    dropped, never reworded (C0's manifest contract: "Every domain has
    an explicit included, excluded, or unavailable manifest disposition
    with a stable safe reason").

    Every reader is called with the SAME user_key, exactly once, over
    the SAME caller-supplied connection. This function opens no
    connection of its own and manages no transaction; every domain-
    reader function it calls already guarantees that on its own (see
    that module's own docstring and tests). It iterates DOMAINS.items()
    in that dict's own fixed order; the assembly service re-sorts
    entries by path before writing, so this function's own emission
    order is not itself load-bearing.

    A reader that raises propagates unchanged: this function makes no
    attempt to catch or partially tolerate a single failing reader. A
    partial export assembled from some-but-not-all domains would be a
    truth violation (a manifest that looks complete but is not); the
    correct, and already-existing, response to any reader failure is
    the caller's own generic exception handling in run_once: fail the
    whole attempt, requeue while attempts remain.
    """

    domain_files = []
    for domain_code, domain in DOMAINS.items():
        disposition = domain["disposition"]
        if disposition == "included":
            for reader_entry in domain["readers"]:
                result = reader_entry["function"](connection, user_key)
                rows = result["rows"]
                schema_tail = reader_entry["schema_id"].split(".")[-2]
                domain_files.append(
                    {
                        "path": "domains/%s/%s.ndjson" % (domain_code, schema_tail),
                        "domain_code": domain_code,
                        "schema_id": reader_entry["schema_id"],
                        "schema_version": 1,
                        "disposition": "included",
                        "content": _serialize_ndjson_rows(rows),
                        "record_count": len(rows),
                        "provenance": {"reader_procedure": reader_entry["procedure"]},
                        "read_window": {
                            "started_at_utc": _iso_z_or_none(result["read_started_at_utc"]),
                            "ended_at_utc": _iso_z_or_none(result["read_ended_at_utc"]),
                        },
                    }
                )
        else:
            domain_files.append(
                {
                    "path": "domains/%s.omitted.json" % domain_code,
                    "domain_code": domain_code,
                    "schema_id": "peerslate.account_export.%s.v1" % domain_code,
                    "schema_version": 1,
                    "disposition": disposition,
                    "omission_reason": domain["reason"] if disposition == "excluded" else None,
                    "failure_reason": domain["reason"] if disposition == "unavailable" else None,
                }
            )
    return domain_files


def summarize_domain_ledger(manifest):
    """Group ``manifest["files"]`` entries by domain_code into one
    ledger-shaped row per domain -- the exact row a future
    domain-ledger write sends to dbo.usp_CompleteAccountExportWithDomains
    (PS-SETTINGS-EXPORT-010), which INSERTs it into C1's
    ``dbo.account_export_job_domains``. This function computes exactly
    what that call persists, from the manifest's own per-file facts, so
    the manifest and the ledger can never silently disagree; reason
    strings longer than the ledger's 200-character bound are bounded
    explicitly by build_domain_ledger_payload, with the full text
    remaining in the manifest.

    An INCLUDED domain combines every one of its manifest files: summed
    record_count/byte_count (matching CK_account_export_job_domains_
    counts' non-negativity, which a sum of non-negative parts always
    satisfies), the domain's overall
    [min(read_started_at_utc), max(read_ended_at_utc)] read window
    across every one of its readers, and one content_sha256 computed
    over the sorted, concatenated per-file hashes -- never a single
    file's own hash standing in for the whole domain, since C1's own
    ``UQ_account_export_job_domains_job_domain`` allows only one row per
    (job, domain_code). EXCLUDED/UNAVAILABLE domains carry the domain's
    own reason and nothing else, matching
    ``CK_account_export_job_domains_shape``'s other two shapes exactly.

    Two real foreign-key columns a genuine INSERT would also need
    (``account_export_job_id``, ``owner_profile_id``) are DB-internal
    identity values with no Python-side equivalent visible to this
    function (it only ever sees a manifest); they are not fabricated
    here.
    """

    files_by_domain = {}
    domain_order = []
    for file_entry in manifest["files"]:
        domain_code = file_entry["domain_code"]
        if domain_code not in files_by_domain:
            files_by_domain[domain_code] = []
            domain_order.append(domain_code)
        files_by_domain[domain_code].append(file_entry)

    summary = {}
    for domain_code in domain_order:
        files = files_by_domain[domain_code]
        dispositions = {file_entry["disposition"] for file_entry in files}
        if len(dispositions) != 1:
            raise ValueError(
                "Mixed disposition within one domain_code: " + domain_code
            )
        disposition = dispositions.pop()

        if disposition == "included":
            started_values = [file_entry["read_window"]["started_at_utc"] for file_entry in files]
            ended_values = [file_entry["read_window"]["ended_at_utc"] for file_entry in files]
            combined_hash_input = "".join(
                sorted(file_entry["sha256"] for file_entry in files)
            ).encode("ascii")
            summary[domain_code] = {
                "domain_code": domain_code,
                "disposition": disposition,
                "file_count": len(files),
                "record_count": sum(file_entry["record_count"] for file_entry in files),
                "byte_count": sum(file_entry["byte_length"] for file_entry in files),
                "content_sha256": hashlib.sha256(combined_hash_input).hexdigest(),
                "read_started_at_utc": min(started_values),
                "read_ended_at_utc": max(ended_values),
                "omission_reason": None,
                "failure_reason": None,
            }
        else:
            if len(files) != 1:
                raise ValueError(
                    "A non-included domain must have exactly one manifest "
                    "file: " + domain_code
                )
            only = files[0]
            summary[domain_code] = {
                "domain_code": domain_code,
                "disposition": disposition,
                "file_count": 1,
                "record_count": None,
                "byte_count": None,
                "content_sha256": None,
                "read_started_at_utc": None,
                "read_ended_at_utc": None,
                "omission_reason": only["omission_reason"],
                "failure_reason": only["failure_reason"],
            }
    return summary


def domain_ledger_row_matches_check_shape(row):
    """A pure re-implementation, for offline testing only, of
    ``CK_account_export_job_domains_shape``'s exact boolean logic (see
    SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation.sql).
    Never touches a database. Returns True when the given
    summarize_domain_ledger() row is shaped exactly as that real CHECK
    constraint would require of a genuine INSERT.
    """

    if row["disposition"] == "included":
        return (
            row["read_started_at_utc"] is not None
            and row["read_ended_at_utc"] is not None
            and row["record_count"] is not None
            and row["byte_count"] is not None
            and row["content_sha256"] is not None
            and row["omission_reason"] is None
            and row["failure_reason"] is None
        )
    if row["disposition"] == "excluded":
        return (
            row["read_started_at_utc"] is None
            and row["read_ended_at_utc"] is None
            and row["record_count"] is None
            and row["byte_count"] is None
            and row["content_sha256"] is None
            and row["omission_reason"] is not None
            and row["failure_reason"] is None
        )
    if row["disposition"] == "unavailable":
        has_omission = row["omission_reason"] is not None
        has_failure = row["failure_reason"] is not None
        return (
            row["read_started_at_utc"] is None
            and row["read_ended_at_utc"] is None
            and row["record_count"] is None
            and row["byte_count"] is None
            and row["content_sha256"] is None
            and (has_omission or has_failure)
            and not (has_omission and has_failure)
        )
    return False


def run_once(connection, *, domain_files_builder):
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
        owner_user_key = fetch_owner_user_key(cursor, owner_user_id, owner_profile_id)
        if owner_user_key is None:
            # Unreachable today -- is_owner_active just confirmed this
            # exact (owner_user_id, owner_profile_id) pair is active --
            # but fetch_owner_user_key's own SQL is independently
            # correct on its own terms, so a defensive, loud failure
            # here (never a silently-invented identity) matches the
            # same "no false promise" posture requested_at_utc's own
            # NULL handling below already uses.
            raise RuntimeError("Owner user_key could not be resolved for the claimed job.")

        # The assembly window brackets the REAL domain reads below, per
        # C0's "assembly start and cutoff" / "@@DBTS at both" contract
        # -- unlike the old fixture worker, real work now actually
        # happens between these two marker reads.
        assembly_started_at_utc = _now_utc()
        consistency_marker_start = read_consistency_marker(cursor)
        domain_files = domain_files_builder(connection, owner_user_key)
        assembly_cutoff_at_utc = _now_utc()
        consistency_marker_cutoff = read_consistency_marker(cursor)

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

        # Refuse to complete a job whose own manifest could not satisfy
        # C1's real CK_account_export_job_domains_shape CHECK -- these are
        # the exact rows usp_CompleteAccountExportWithDomains persists.
        domain_ledger_summary = summarize_domain_ledger(assembled["manifest"])
        for summarized_domain_code, ledger_row in domain_ledger_summary.items():
            if not domain_ledger_row_matches_check_shape(ledger_row):
                raise RuntimeError(
                    "Domain ledger summary shape mismatch for " + summarized_domain_code
                )
        assert_domain_ledger_complete(domain_ledger_summary)
        domain_ledger_payload = build_domain_ledger_payload(
            domain_ledger_summary, assembled["manifest"]
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

        complete_job_with_domains(
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
            domain_ledger_payload=domain_ledger_payload,
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


def run_maintenance(connection, storage):
    """Retention maintenance (PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001):
    make expiry mean deletion.

    Two phases, fixed order. First the ledger transition
    (expire_ready_jobs); then physical cleanup for exactly the jobs the
    ledger shows past-ready with cleanup pending -- delete the objects
    through the storage adapter's idempotent calls, and only after the
    deletes succeed, mark the job cleaned. The ordering rule both
    directions: never delete an object for a job still downloadable
    (only 'expired'/'failed' + 'pending' rows are swept, and a runtime
    guard refuses anything else even if a defective read produced it),
    and never mark cleaned before the delete succeeded (a failing
    delete leaves the job 'pending' for the next run's retry -- every
    delete is an idempotent no-op on re-run -- while this run continues
    to the remaining jobs and then fails loudly at the end).

    Every swept job gets cleanup_final plus its per-attempt staging
    sweep, unconditionally. CK_account_export_jobs_ready_artifact
    forces a failed job's LEDGER columns to NULL, but the physical
    final object can still exist: promote() commits the final blob
    BEFORE verify_promoted_hash and the completion call, so a failure
    after that point orphans a committed final object while every
    retry dies on storage_conflict (create-only final names) and the
    job terminates 'failed' with no reference. cleanup_final deletes
    that orphan, or proves absence for a job that never promoted --
    both idempotent -- and a failed job is never downloadable
    (usp_GetAccountExportDownloadMetadataForOwner serves only ready
    jobs), so the unconditional delete cannot touch a downloadable
    artifact.
    Every log line is content-free: counts, job_key, ledger state, and
    error_type -- never a reason, domain, or artifact reference.

    Returns a content-free outcome dict; 'failed' means at least one
    job's cleanup did not complete and the entrypoint exits nonzero.
    """

    cursor = connection.cursor()

    expired_count = expire_ready_jobs(cursor)
    _log("maintenance_expired", expired_count=expired_count)

    cleaned_count = 0
    cleanup_failed_count = 0
    for job in fetch_cleanup_pending_jobs(cursor):
        state = job["state"]
        try:
            # Normalized per job, inside the sweep, so one malformed
            # ledger row is counted and skipped (fail-safe: nothing was
            # deleted for it) instead of aborting the entire run before
            # the remaining jobs' overdue deletions.
            job_key = normalize_job_key(job["job_key"])
            attempt_count = int(job["attempt_count"])
        except Exception as error:  # noqa: BLE001 -- same one-job isolation as below
            cleanup_failed_count += 1
            _log(
                "maintenance_cleanup_failed",
                state=state,
                error_type=type(error).__name__,
            )
            continue
        if state not in ("expired", "failed"):
            # Defense in depth for the sacred rule beyond the WHERE
            # clause: a job in any other state is still (or may again
            # be) downloadable and must never lose its artifact here.
            cleanup_failed_count += 1
            _log("maintenance_cleanup_refused", job_key=job_key, state=state)
            continue
        try:
            # Unconditionally, for BOTH swept states: a 'failed' job's
            # ledger reference is NULL, but a post-promote failure can
            # orphan a committed physical final object (see docstring).
            # Idempotent: absence is success.
            storage.cleanup_final(job_key)
            # Staging objects can exist only for attempts that actually
            # ran (stage() is called with the claimed attempt ordinal),
            # so the sweep is bounded by the job's own attempt_count --
            # CK_account_export_jobs_attempts caps it at MAX_ATTEMPTS.
            for attempt in range(1, attempt_count + 1):
                storage.cleanup_staging(job_key, attempt)
            marked_state = mark_job_cleaned(cursor, job_key)
        except Exception as error:  # noqa: BLE001 -- one job's failure must not end the sweep
            cleanup_failed_count += 1
            _log(
                "maintenance_cleanup_failed",
                job_key=job_key,
                state=state,
                error_type=type(error).__name__,
            )
            continue
        if marked_state != "cleaned":
            # Defensive: the procedure reported something other than a
            # settled cleanup. Leave the job for the next run and fail
            # this one loudly rather than claim a cleanup the ledger
            # does not show.
            cleanup_failed_count += 1
            _log("maintenance_cleanup_unconfirmed", job_key=job_key, state=state)
            continue
        cleaned_count += 1
        _log("maintenance_cleaned", job_key=job_key, state=state)

    _log(
        "maintenance_finished",
        expired_count=expired_count,
        cleaned_count=cleaned_count,
        cleanup_failed_count=cleanup_failed_count,
    )
    return {
        "outcome": "completed" if cleanup_failed_count == 0 else "failed",
        "expired_count": expired_count,
        "cleaned_count": cleaned_count,
        "cleanup_failed_count": cleanup_failed_count,
    }


def _connect(connection_string):
    from mssql_python import connect

    connection = connect(connection_string, timeout=30)
    connection.setautocommit(True)
    return connection


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-database", required=True)
    parser.add_argument(
        "--maintenance",
        action="store_true",
        help=(
            "Run retention maintenance (ledger expiry, then physical "
            "cleanup of past-ready pending artifacts) instead of "
            "claiming one export job."
        ),
    )
    arguments = parser.parse_args(argv)

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

        if arguments.maintenance:
            result = run_maintenance(connection, account_export_storage_service)
        else:
            result = run_once(connection, domain_files_builder=build_domain_files_from_readers)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["outcome"] in ("idle", "completed") else 1
    finally:
        try:
            connection.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
