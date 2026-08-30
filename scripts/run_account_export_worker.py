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
and promote it through the private Blob adapter -> complete or fail the
job through the C1 lease-fenced procedures. Every log line is
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
registry marks "included" (7 domains, 22 readers today); every other
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

Manifest/ledger agreement -- this package's central proof. C1's child
ledger (dbo.account_export_job_domains) has no writer procedure at all
(C1_ACCOUNT_EXPORT_FOUNDATION.md: "No procedure in this migration
writes to this table... population is deferred to a future, separately
claimed domain-reader slice"), and this package's frozen surfaces
include no SQL file, so nothing here can INSERT a real ledger row.
summarize_domain_ledger and domain_ledger_row_matches_check_shape below
instead compute, offline, the EXACT row a future writer would need --
shaped and validated against C1's own
CK_account_export_job_domains_shape CHECK text -- and prove (in
tests/test_account_export_integration.py) that it agrees, file by file
and domain by domain, with the manifest and with the bytes actually
serialized into the ZIP. run_once also runs this same shape check live,
as a defensive backstop that refuses to complete a job whose own
manifest could not satisfy that CHECK. The AGGREGATE facts that DO
reach a real, live ledger row today (compressed_size_bytes,
uncompressed_size_bytes, final_artifact_sha256, via
usp_CompleteAccountExportJob) are unchanged by this package and still
come from AccountExportStorageService.promote()'s own independent
readback, never from a pre-upload estimate. Actually persisting a
per-domain row remains a disclosed, out-of-scope gap: it needs a new
procedure and migration this claim cannot author (see
CR5_ACCOUNT_EXPORT_READER_INTEGRATION.md, "Manifest/ledger agreement").
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
    domain-ledger-writing slice would need to INSERT into C1's
    ``dbo.account_export_job_domains`` (currently unpopulated -- see
    this module's own docstring). This package writes no such row
    anywhere: that table has no writer procedure at all in the current
    schema, and this claim's frozen surfaces include no SQL file, so
    nothing here can create one. This function only PROVES, offline,
    that the manifest's own per-file facts already sum to exactly what
    such a future writer would need, so the manifest and any eventual
    ledger population can never silently disagree.

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

        # Defensive backstop, not merely a test-time exercise: refuse to
        # complete a job whose own manifest could not satisfy C1's real
        # CK_account_export_job_domains_shape CHECK, even though
        # nothing in this claim's frozen surfaces can write that row
        # today (see summarize_domain_ledger's own docstring above).
        domain_ledger_summary = summarize_domain_ledger(assembled["manifest"])
        for summarized_domain_code, ledger_row in domain_ledger_summary.items():
            if not domain_ledger_row_matches_check_shape(ledger_row):
                raise RuntimeError(
                    "Domain ledger summary shape mismatch for " + summarized_domain_code
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
