#!/usr/bin/env python3
"""Plan, apply, or verify least-privilege Community maintenance SQL access.

This is a separate protected authorization operation, not an application
migration. It must run as the configured Azure SQL Microsoft Entra admin after
PS-COMMUNITY-REVIVAL-001 is applied and before maintenance is enabled. The
scheduled job uses a dedicated workload identity with no database role and
only the five direct procedure grants enumerated below.
"""

from __future__ import annotations

import argparse
import json
import re
from uuid import UUID

from mssql_python import connect


ALLOWED_SERVER = "peerslate.database.windows.net"
ALLOWED_DATABASE = "peerslate-database"
ALLOWED_PRINCIPAL = "peerslate-community-maintenance"
QUERY_TIMEOUT_SECONDS = 15
REQUIRED_PROCEDURES = (
    "usp_ClaimPublicCommunityMediaCleanup",
    "usp_CompletePublicCommunityMediaCleanup",
    "usp_PurgeCommunityContent",
    "usp_PurgeCommunityAuditEvents",
    "usp_PurgeCommunityOutbox",
)
ALLOWED_DATABASE_PERMISSIONS = frozenset(
    {
        "CONNECT",
        "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
        "VIEW ANY COLUMN MASTER KEY DEFINITION",
    }
)
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _validate_exact(server, database, principal):
    for value in (server, database, principal):
        if not SAFE_NAME.fullmatch(str(value or "")):
            raise ValueError("Invalid maintenance authority target.")
    if (
        server != ALLOWED_SERVER
        or database != ALLOWED_DATABASE
        or principal != ALLOWED_PRINCIPAL
    ):
        raise ValueError("Maintenance authority target is not approved.")


def _client_sid(client_id):
    """Return SQL's explicit EXTERNAL_USER SID for one Entra application ID."""

    try:
        return UUID(str(client_id)).bytes_le
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError("Maintenance principal client ID is invalid.") from error


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


def _verify_effective_permissions(cursor):
    """Enumerate the complete user-database authority of the dedicated user."""

    cursor.execute(
        """
        SELECT permission_name
        FROM sys.fn_my_permissions(NULL, N'DATABASE');
        """
    )
    database_permissions = {str(row[0]) for row in cursor.fetchall()}
    if not database_permissions.issubset(ALLOWED_DATABASE_PERMISSIONS):
        raise RuntimeError("Maintenance principal has unexpected database authority.")

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
        raise RuntimeError("Maintenance principal has unexpected schema authority.")

    cursor.execute(
        """
        SELECT schema_entry.name AS schema_name,
               object_entry.name AS object_name,
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
        (str(row[0]), str(row[1]), str(row[2])) for row in cursor.fetchall()
    }
    expected_objects = {
        ("dbo", procedure, "EXECUTE") for procedure in REQUIRED_PROCEDURES
    }
    if effective_objects != expected_objects:
        raise RuntimeError("Maintenance principal object authority is not exact.")


def verify(cursor, expected_database, expected_sid, *, allow_impersonation=False):
    cursor.execute(
        """
        SELECT DB_NAME() AS database_name,
               principal.type_desc AS principal_type,
               principal.sid AS principal_sid,
               CASE WHEN OBJECT_ID(N'dbo.usp_ClaimPublicCommunityMediaCleanup', N'P') IS NOT NULL
                     AND OBJECT_ID(N'dbo.usp_CompletePublicCommunityMediaCleanup', N'P') IS NOT NULL
                     AND OBJECT_ID(N'dbo.usp_PurgeCommunityContent', N'P') IS NOT NULL
                     AND OBJECT_ID(N'dbo.usp_PurgeCommunityAuditEvents', N'P') IS NOT NULL
                     AND OBJECT_ID(N'dbo.usp_PurgeCommunityOutbox', N'P') IS NOT NULL
                    THEN 1 ELSE 0 END AS procedures_present
        FROM (SELECT 1 AS boundary) AS boundary
        LEFT JOIN sys.database_principals AS principal
          ON principal.name = N'peerslate-community-maintenance';
        """
    )
    boundary = _first(cursor)
    if (
        boundary.get("database_name") != expected_database
        or boundary.get("principal_type") != "EXTERNAL_USER"
        or bytes(boundary.get("principal_sid") or b"") != expected_sid
        or int(boundary.get("procedures_present") or 0) != 1
    ):
        raise RuntimeError("Maintenance authority boundary verification failed.")

    cursor.execute(
        """
        SELECT role_principal.name AS role_name
        FROM sys.database_role_members AS membership
        JOIN sys.database_principals AS role_principal
          ON role_principal.principal_id = membership.role_principal_id
        JOIN sys.database_principals AS member_principal
          ON member_principal.principal_id = membership.member_principal_id
        WHERE member_principal.name = N'peerslate-community-maintenance';
        """
    )
    if cursor.fetchall():
        raise RuntimeError("Maintenance principal must have no database role.")

    cursor.execute(
        """
        SELECT permission_entry.class_desc,
               permission_entry.permission_name,
               permission_entry.state_desc,
               schema_entry.name AS schema_name,
               object_entry.name AS object_name
        FROM sys.database_permissions AS permission_entry
        JOIN sys.database_principals AS principal
          ON principal.principal_id = permission_entry.grantee_principal_id
        LEFT JOIN sys.objects AS object_entry
          ON permission_entry.class = 1
         AND object_entry.object_id = permission_entry.major_id
        LEFT JOIN sys.schemas AS schema_entry
          ON schema_entry.schema_id = object_entry.schema_id
        WHERE principal.name = N'peerslate-community-maintenance';
        """
    )
    direct_permissions = {
        (
            str(row[0]),
            str(row[1]),
            str(row[2]),
            str(row[3] or ""),
            str(row[4] or ""),
        )
        for row in cursor.fetchall()
    }
    expected_direct = {
        ("OBJECT_OR_COLUMN", "EXECUTE", "GRANT", "dbo", procedure)
        for procedure in REQUIRED_PROCEDURES
    }
    expected_direct.add(("DATABASE", "CONNECT", "GRANT", "", ""))
    if direct_permissions != expected_direct:
        raise RuntimeError("Maintenance principal direct authority is not exact.")

    cursor.execute("SELECT USER_NAME() AS current_principal;")
    current_principal = str(_first(cursor).get("current_principal") or "")
    impersonated = current_principal != ALLOWED_PRINCIPAL
    if impersonated:
        if not allow_impersonation:
            raise RuntimeError("Active maintenance SQL identity is not approved.")
        cursor.execute("EXECUTE AS USER = N'peerslate-community-maintenance';")
        _drain(cursor)
    try:
        _verify_effective_permissions(cursor)
    finally:
        if impersonated:
            cursor.execute("REVERT;")
            _drain(cursor)
    return True


def apply(cursor, principal_sid):
    sid_literal = "0x" + principal_sid.hex()
    cursor.execute(
        f"""
        IF DATABASE_PRINCIPAL_ID(N'peerslate-community-maintenance') IS NULL
            CREATE USER [peerslate-community-maintenance]
            WITH SID = {sid_literal}, TYPE = E;
        """
    )
    _drain(cursor)
    for procedure in REQUIRED_PROCEDURES:
        cursor.execute(
            f"GRANT EXECUTE ON OBJECT::dbo.{procedure} "
            "TO [peerslate-community-maintenance];"
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
        if args.mode == "plan":
            print(
                json.dumps(
                    {
                        "status": "planned",
                        "database": args.database,
                        "principal": args.principal,
                        "procedure_count": len(REQUIRED_PROCEDURES),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if args.mode == "apply" and not args.confirm_apply:
            raise ValueError("Apply requires --confirm-apply.")
        with _connection(args.server, args.database) as connection:
            cursor = connection.cursor()
            if args.mode == "apply":
                try:
                    apply(cursor, principal_sid)
                    verify(
                        cursor,
                        args.database,
                        principal_sid,
                        allow_impersonation=True,
                    )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
            else:
                verify(cursor, args.database, principal_sid)
        print(
            json.dumps(
                {
                    "status": "verified",
                    "database": args.database,
                    "principal": args.principal,
                    "procedure_count": len(REQUIRED_PROCEDURES),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
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
