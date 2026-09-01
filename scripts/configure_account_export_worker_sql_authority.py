#!/usr/bin/env python3
"""Plan, apply, or verify least-privilege account-export worker SQL access.

This is a separate protected authorization operation, not an application
migration. It must run as the configured Azure SQL Microsoft Entra admin after
PS-SETTINGS-EXPORT-001 and PS-SETTINGS-EXPORT-010 are applied and before the
export worker or its retention-maintenance mode is scheduled. The worker uses
a dedicated user-assigned managed identity with no database role, direct
EXECUTE grants on exactly the lifecycle and domain-reader procedures the
worker calls, and three column-scoped SELECT grants covering the worker's
sanctioned interim direct reads (a recorded C1->C2 obligation; see
scripts/run_account_export_worker.py: is_owner_active, fetch_owner_user_key,
fetch_requested_at_utc, and the maintenance sweep's
fetch_cleanup_pending_jobs). Structure mirrors
scripts/configure_community_maintenance_sql_authority.py; the column-grant
handling (sys.database_permissions class 1 rows with minor_id != 0, and
fn_my_permissions subentity rows) is the deliberate extension that precedent
does not need, because the community principal holds zero table grants.

The domain-reader procedure list is never hand-typed: it is enumerated at
runtime from services/account_export_domain_readers.py, the same module the
worker itself calls, so the grant list and the call list share one source.

Stale-principal remediation: if the worker user already exists with a
different SID (for example after the managed identity was recreated), the
guarded CREATE USER is a no-op and verify fails closed on the SID check.
Remediation is a deliberate manual ``DROP USER
[peerslate-account-export-worker];`` by the Entra admin, then rerunning
apply; this script never drops a principal on its own.

Column-grant scope note (recorded deviation from the C4 scout runbook):
the runbook's account_export_jobs grant listed only (job_key,
requested_at_utc). PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001 merged after
that scout and added the maintenance sweep's direct read, which also touches
state, attempt_count, cleanup_state (WHERE) and account_export_job_id
(ORDER BY). Column-level SELECT must cover predicate and ordering columns,
so the exact grant here is the six-column minimum the shipped worker needs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from uuid import UUID

from mssql_python import connect


ALLOWED_SERVER = "peerslate.database.windows.net"
ALLOWED_DATABASE = "peerslate-database"
ALLOWED_PRINCIPAL = "peerslate-account-export-worker"
QUERY_TIMEOUT_SECONDS = 30

# The five lifecycle procedures: the three the worker's run_once path EXECs
# (claim, complete-with-domains, fail) and the two the --maintenance path
# EXECs (expire, cleanup). C1's original usp_CompleteAccountExportJob is
# deliberately NOT granted: it has zero callers anywhere (the worker
# completes only through the WithDomains procedure), and least privilege
# wins over reserving it -- re-adding is one line if a caller ever ships
# (pre-execution review finding, 2026-09-01).
LIFECYCLE_PROCEDURES = (
    "usp_ClaimAccountExportJob",
    "usp_CompleteAccountExportWithDomains",
    "usp_FailAccountExportJob",
    "usp_ExpireAccountExportJobs",
    "usp_CleanupAccountExportJob",
)

# Grant-shape tripwires (pre-execution review finding, 2026-09-01): the
# granted set and the verify expectation both derive from the SAME runtime
# enumeration of the readers module, so silent module drift would shift a
# production grant and still verify. These pins fail the run instead. A
# future editor who deliberately changes the reader set or the sanctioned
# direct reads must update these pins in the same change, alongside
# services/account_export_domain_readers.py.
EXPECTED_DOMAIN_READER_COUNT = 31
# 1 CONNECT + 36 EXECUTE (5 lifecycle + 31 readers) + 12 column SELECTs.
EXPECTED_DIRECT_PERMISSION_ROWS = 49

# The worker's sanctioned interim direct reads, column-scoped so the identity
# can never read app_users or member_profiles broadly. Columns are sorted;
# every WHERE / JOIN / ORDER BY column is included because SQL Server
# column-level SELECT applies to predicate and ordering columns too.
COLUMN_SELECT_GRANTS = (
    ("app_users", ("active", "id", "user_key")),
    ("member_profiles", ("active", "profile_id", "user_id")),
    (
        "account_export_jobs",
        (
            "account_export_job_id",
            "attempt_count",
            "cleanup_state",
            "job_key",
            "requested_at_utc",
            "state",
        ),
    ),
)

ALLOWED_DATABASE_PERMISSIONS = frozenset(
    {
        "CONNECT",
        "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
        "VIEW ANY COLUMN MASTER KEY DEFINITION",
    }
)
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
SAFE_SQL_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,127}$")


def _domain_reader_procedures():
    """Enumerate every domain-reader procedure name from the worker's own
    reader module. Every module-level reader function carries its exact
    procedure name as a ``procedure_name`` attribute (set by that module's
    _make_reader factory), so this collection is complete by construction
    and immune to hand-transcription drift."""

    path = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "account_export_domain_readers.py"
    )
    spec = importlib.util.spec_from_file_location(
        "account_export_domain_readers_for_grants", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = sorted(
        {
            value.procedure_name
            for value in vars(module).values()
            if callable(value)
            and isinstance(getattr(value, "procedure_name", None), str)
        }
    )
    if not names:
        raise RuntimeError("Domain-reader enumeration returned nothing.")
    for name in names:
        if not (
            name.startswith("usp_ReadAccountExport")
            and name.endswith("ForOwner")
            and SAFE_SQL_IDENTIFIER.fullmatch(name)
        ):
            raise RuntimeError("Domain-reader enumeration failed shape validation.")
    return tuple(names)


def _all_procedures():
    readers = _domain_reader_procedures()
    if len(readers) != EXPECTED_DOMAIN_READER_COUNT:
        raise RuntimeError(
            "Domain-reader tripwire: enumeration returned a different reader "
            "count than the pinned EXPECTED_DOMAIN_READER_COUNT. If the reader "
            "set changed deliberately, update the pins in this script in the "
            "same change."
        )
    return LIFECYCLE_PROCEDURES + readers


def _validate_exact(server, database, principal):
    for value in (server, database, principal):
        if not SAFE_NAME.fullmatch(str(value or "")):
            raise ValueError("Invalid worker authority target.")
    if (
        server != ALLOWED_SERVER
        or database != ALLOWED_DATABASE
        or principal != ALLOWED_PRINCIPAL
    ):
        raise ValueError("Worker authority target is not approved.")


def _validate_identifiers(procedures):
    for procedure in procedures:
        if not SAFE_SQL_IDENTIFIER.fullmatch(procedure):
            raise ValueError("Unsafe procedure identifier.")
    for table, columns in COLUMN_SELECT_GRANTS:
        if not SAFE_SQL_IDENTIFIER.fullmatch(table):
            raise ValueError("Unsafe table identifier.")
        for column in columns:
            if not SAFE_SQL_IDENTIFIER.fullmatch(column):
                raise ValueError("Unsafe column identifier.")


def _client_sid(client_id):
    """Return SQL's explicit EXTERNAL_USER SID for one Entra application
    (client) ID: UUID.bytes_le, never a hand-transcribed byte string."""

    try:
        return UUID(str(client_id)).bytes_le
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError("Worker principal client ID is invalid.") from error


def _connection(server, database):
    connection = connect(
        f"Server={server};Database={database};Authentication=ActiveDirectoryDefault;"
        "Encrypt=yes;TrustServerCertificate=no",
        timeout=5,
    )
    connection.timeout = QUERY_TIMEOUT_SECONDS
    connection.setautocommit(False)
    return connection


def _first(cursor):
    while cursor.description is None:
        if not cursor.nextset():
            return {}
    columns = [column[0] for column in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else {}


def _drain(cursor):
    while cursor.nextset():
        pass


def _expected_direct_permissions(procedures):
    """The exact sys.database_permissions rows the principal must hold:
    CONNECT, one object EXECUTE per procedure, and one class-1 column row
    per granted column (sys.database_permissions records a column grant as
    its own row with minor_id = column_id and no object-level SELECT row)."""

    expected = {("DATABASE", "CONNECT", "GRANT", "", "", "")}
    for procedure in procedures:
        expected.add(("OBJECT_OR_COLUMN", "EXECUTE", "GRANT", "dbo", procedure, ""))
    for table, columns in COLUMN_SELECT_GRANTS:
        for column in columns:
            expected.add(("OBJECT_OR_COLUMN", "SELECT", "GRANT", "dbo", table, column))
    if len(expected) != EXPECTED_DIRECT_PERMISSION_ROWS:
        raise RuntimeError(
            "Grant-shape tripwire: the expected direct-permission set differs "
            "from the pinned EXPECTED_DIRECT_PERMISSION_ROWS. If the grant "
            "shape changed deliberately, update the pins in this script in "
            "the same change."
        )
    return expected


def _read_direct_permissions(cursor):
    cursor.execute(
        """
        SELECT permission_entry.class_desc,
               permission_entry.permission_name,
               permission_entry.state_desc,
               schema_entry.name AS schema_name,
               object_entry.name AS object_name,
               column_entry.name AS column_name
        FROM sys.database_permissions AS permission_entry
        JOIN sys.database_principals AS principal
          ON principal.principal_id = permission_entry.grantee_principal_id
        LEFT JOIN sys.objects AS object_entry
          ON permission_entry.class = 1
         AND object_entry.object_id = permission_entry.major_id
        LEFT JOIN sys.schemas AS schema_entry
          ON schema_entry.schema_id = object_entry.schema_id
        LEFT JOIN sys.columns AS column_entry
          ON permission_entry.class = 1
         AND permission_entry.minor_id <> 0
         AND column_entry.object_id = permission_entry.major_id
         AND column_entry.column_id = permission_entry.minor_id
        WHERE principal.name = N'peerslate-account-export-worker';
        """
    )
    return {
        (
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3] or ""),
            str(row[4] or ""),
            str(row[5] or ""),
        )
        for row in cursor.fetchall()
    }


def _expected_effective_objects(procedures):
    """The exact fn_my_permissions OBJECT-class rows: one subentity-free
    EXECUTE row per procedure and one subentity (column) SELECT row per
    granted column. Permission implication flows downward only, so a
    column grant never manufactures an object-level SELECT row."""

    expected = {("dbo", procedure, "", "EXECUTE") for procedure in procedures}
    for table, columns in COLUMN_SELECT_GRANTS:
        for column in columns:
            expected.add(("dbo", table, column, "SELECT"))
    return expected


def _verify_effective_permissions(cursor, procedures):
    """Enumerate the complete user-database authority of the dedicated user."""

    cursor.execute(
        """
        SELECT permission_name
        FROM sys.fn_my_permissions(NULL, N'DATABASE');
        """
    )
    database_permissions = {str(row[0]) for row in cursor.fetchall()}
    if not database_permissions.issubset(ALLOWED_DATABASE_PERMISSIONS):
        raise RuntimeError("Worker principal has unexpected database authority.")

    cursor.execute(
        """
        SELECT schema_name, permission_name
        FROM (
            SELECT schema_entry.name AS schema_name,
                   permission_entry.permission_name
            FROM sys.schemas AS schema_entry
            CROSS APPLY sys.fn_my_permissions(
                QUOTENAME(schema_entry.name), N'SCHEMA'
            ) AS permission_entry
            WHERE schema_entry.schema_id < 16384
        ) AS effective_schema_permissions;
        """
    )
    if cursor.fetchall():
        raise RuntimeError("Worker principal has unexpected schema authority.")

    cursor.execute(
        """
        SELECT schema_entry.name AS schema_name,
               object_entry.name AS object_name,
               permission_entry.subentity_name,
               permission_entry.permission_name
        FROM sys.objects AS object_entry
        JOIN sys.schemas AS schema_entry
          ON schema_entry.schema_id = object_entry.schema_id
        CROSS APPLY sys.fn_my_permissions(
            QUOTENAME(schema_entry.name) + N'.' + QUOTENAME(object_entry.name),
            N'OBJECT'
        ) AS permission_entry
        WHERE object_entry.is_ms_shipped = 0;
        """
    )
    effective_objects = {
        (str(row[0]), str(row[1]), str(row[2] or ""), str(row[3]))
        for row in cursor.fetchall()
    }
    if effective_objects != _expected_effective_objects(procedures):
        raise RuntimeError("Worker principal object authority is not exact.")


def verify(cursor, expected_database, expected_sid, procedures, *, allow_impersonation=False):
    cursor.execute(
        """
        SELECT DB_NAME() AS database_name,
               principal.type_desc AS principal_type,
               principal.sid AS principal_sid
        FROM (SELECT 1 AS boundary) AS boundary
        LEFT JOIN sys.database_principals AS principal
          ON principal.name = N'peerslate-account-export-worker';
        """
    )
    boundary = _first(cursor)
    if (
        boundary.get("database_name") != expected_database
        or boundary.get("principal_type") != "EXTERNAL_USER"
        or bytes(boundary.get("principal_sid") or b"") != expected_sid
    ):
        raise RuntimeError("Worker authority boundary verification failed.")

    missing = _missing_objects(cursor, procedures)
    if missing:
        raise RuntimeError("Worker authority target objects are incomplete.")

    cursor.execute(
        """
        SELECT role_principal.name AS role_name
        FROM sys.database_role_members AS membership
        JOIN sys.database_principals AS role_principal
          ON role_principal.principal_id = membership.role_principal_id
        JOIN sys.database_principals AS member_principal
          ON member_principal.principal_id = membership.member_principal_id
        WHERE member_principal.name = N'peerslate-account-export-worker';
        """
    )
    if cursor.fetchall():
        raise RuntimeError("Worker principal must have no database role.")

    direct_permissions = _read_direct_permissions(cursor)
    if direct_permissions != _expected_direct_permissions(procedures):
        raise RuntimeError("Worker principal direct authority is not exact.")

    cursor.execute("SELECT USER_NAME() AS current_principal;")
    current_principal = str(_first(cursor).get("current_principal") or "")
    impersonated = current_principal != ALLOWED_PRINCIPAL
    if impersonated:
        if not allow_impersonation:
            raise RuntimeError("Active worker SQL identity is not approved.")
        cursor.execute("EXECUTE AS USER = N'peerslate-account-export-worker';")
        _drain(cursor)
    try:
        _verify_effective_permissions(cursor, procedures)
    finally:
        if impersonated:
            cursor.execute("REVERT;")
            _drain(cursor)
    return True


def _missing_objects(cursor, procedures):
    """Count target objects (procedures and column-grant tables/columns)
    absent from the database. Content-free: callers receive counts only."""

    missing = 0
    for procedure in procedures:
        cursor.execute(
            "SELECT OBJECT_ID(N'dbo.' + QUOTENAME(?), N'P');", (procedure,)
        )
        row = cursor.fetchone()
        if row is None or row[0] is None:
            missing += 1
    for table, columns in COLUMN_SELECT_GRANTS:
        for column in columns:
            cursor.execute(
                "SELECT COL_LENGTH(N'dbo.' + QUOTENAME(?), ?);", (table, column)
            )
            row = cursor.fetchone()
            if row is None or row[0] is None:
                missing += 1
    return missing


def plan(cursor, expected_sid, procedures):
    """Read-only planning inventory: connect, compare present authority to
    the expected exact set, and report counts only. Running plan before and
    after apply proves idempotent planning (missing/extra collapse to 0)."""

    cursor.execute(
        """
        SELECT DB_NAME() AS database_name,
               principal.type_desc AS principal_type,
               principal.sid AS principal_sid
        FROM (SELECT 1 AS boundary) AS boundary
        LEFT JOIN sys.database_principals AS principal
          ON principal.name = N'peerslate-account-export-worker';
        """
    )
    boundary = _first(cursor)
    principal_exists = boundary.get("principal_type") is not None
    expected = _expected_direct_permissions(procedures)
    present = _read_direct_permissions(cursor) if principal_exists else set()
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM sys.database_role_members AS membership
        JOIN sys.database_principals AS member_principal
          ON member_principal.principal_id = membership.member_principal_id
        WHERE member_principal.name = N'peerslate-account-export-worker';
        """
    )
    role_memberships = int(cursor.fetchone()[0]) if principal_exists else 0
    return {
        "database_name_matches": boundary.get("database_name") == ALLOWED_DATABASE,
        "principal_exists": principal_exists,
        "principal_type_external_user": boundary.get("principal_type")
        == "EXTERNAL_USER"
        if principal_exists
        else None,
        "principal_sid_matches": bytes(boundary.get("principal_sid") or b"")
        == expected_sid
        if principal_exists
        else None,
        "role_memberships": role_memberships,
        "target_objects_missing": _missing_objects(cursor, procedures),
        "expected_grant_count": len(expected),
        "grants_present": len(expected & present),
        "grants_missing": len(expected - present),
        "grants_unexpected": len(present - expected),
    }


def apply(cursor, principal_sid, procedures):
    sid_literal = "0x" + principal_sid.hex()
    cursor.execute(
        f"""
        IF DATABASE_PRINCIPAL_ID(N'peerslate-account-export-worker') IS NULL
            CREATE USER [peerslate-account-export-worker]
            WITH SID = {sid_literal}, TYPE = E;
        """
    )
    _drain(cursor)
    for procedure in procedures:
        cursor.execute(
            f"GRANT EXECUTE ON OBJECT::dbo.{procedure} "
            "TO [peerslate-account-export-worker];"
        )
        _drain(cursor)
    for table, columns in COLUMN_SELECT_GRANTS:
        column_list = ", ".join(columns)
        cursor.execute(
            f"GRANT SELECT ON OBJECT::dbo.{table} ({column_list}) "
            "TO [peerslate-account-export-worker];"
        )
        _drain(cursor)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "apply", "verify"))
    parser.add_argument("--server", default=ALLOWED_SERVER)
    parser.add_argument("--database", default=ALLOWED_DATABASE)
    parser.add_argument("--principal", default=ALLOWED_PRINCIPAL)
    parser.add_argument("--principal-client-id", required=True)
    parser.add_argument("--confirm-apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        _validate_exact(args.server, args.database, args.principal)
        principal_sid = _client_sid(args.principal_client_id)
        procedures = _all_procedures()
        _validate_identifiers(procedures)
        if args.mode == "apply" and not args.confirm_apply:
            raise ValueError("Apply requires --confirm-apply.")
        summary = {
            "database": args.database,
            "principal": args.principal,
            "lifecycle_procedure_count": len(LIFECYCLE_PROCEDURES),
            "domain_reader_count": len(procedures) - len(LIFECYCLE_PROCEDURES),
            "column_grant_count": sum(
                len(columns) for _, columns in COLUMN_SELECT_GRANTS
            ),
        }
        with _connection(args.server, args.database) as connection:
            cursor = connection.cursor()
            if args.mode == "plan":
                summary.update(plan(cursor, principal_sid, procedures))
                summary["status"] = "planned"
                connection.rollback()
            elif args.mode == "apply":
                try:
                    apply(cursor, principal_sid, procedures)
                    verify(
                        cursor,
                        args.database,
                        principal_sid,
                        procedures,
                        allow_impersonation=True,
                    )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                summary["status"] = "verified"
            else:
                verify(cursor, args.database, principal_sid, procedures)
                connection.rollback()
                summary["status"] = "verified"
        print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as error:
        print(
            json.dumps(
                {"status": "failed", "error_type": type(error).__name__},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
