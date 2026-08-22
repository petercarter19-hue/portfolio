#!/usr/bin/env python3
"""Plan, apply, or verify least-privilege Interview telemetry SQL access.

This is a separate protected authorization operation, not an application
migration. It must run as the server's Microsoft Entra administrator over an
``Authentication=ActiveDirectoryDefault`` connection (exactly as the Community
authority script does) after PS-INTERVIEW-AI-EXTRACT-001 is applied and
before Interview retention is enabled. A SQL-authenticated administrator
connection is NOT sufficient: SQL Server refuses ``EXECUTE AS`` on an
EXTERNAL_USER from it ("only active directory users can impersonate other
active directory users"), which the disposable proof demonstrated on
2026-08-22 and which ``verify`` depends on. It exists because the governed apply
identity (``peerslate-ado-schema``) holds ``db_ddladmin`` only: it can create
tables and procedures and can neither create database roles nor grant
execute permission - run 1419 (2026-08-22) refused the migration that tried
to do both, transactionally, and wrote nothing. Community maintenance
already follows this split (``configure_community_maintenance_sql_authority``).

Authority model (unchanged from the reviewed design):

* ``interview_telemetry_append`` - EXECUTE on ``usp_AppendInterviewAIServerCall``
  only; member: the application's EXTERNAL_USER (the App Service identity).
* ``interview_telemetry_maintenance`` - EXECUTE on
  ``usp_PurgeInterviewAIServerCalls`` only; member: the dedicated Interview
  maintenance EXTERNAL_USER (SID = its Entra application ID), never the
  Community maintenance identity.

Neither role receives any direct table permission.

The application identity already holds broad standing grants in production
(``db_datareader``, ``db_datawriter`` and a database-wide EXECUTE). Those
predate this package and are not changed here; but they would let the
application execute the purge procedure and write the telemetry table
directly, which the reviewed boundary forbids. ``apply`` therefore also
places two explicit DENYs on the application identity - EXECUTE on the
purge procedure and SELECT/INSERT/UPDATE/DELETE on the telemetry table. A
DENY overrides every broader GRANT, and the append procedure keeps working
because it and the table share an owner (ownership chaining). ``verify``
proves the effective result for the real identities, not proof stand-ins.

Modes (the command line is locked to the production server, database and
principal names; only the disposable-database proof passes stand-in names
to the functions directly, over its own Entra-authenticated connection):

* ``plan``   - verify read-only and print what ``apply`` would do; touches nothing.
* ``apply``  - ensure roles, grants, the maintenance user, both memberships and
  the application DENYs inside ONE transaction, verify the complete boundary,
  commit; any failure rolls everything back. Requires ``--confirm-apply``.
* ``verify`` - read-only boundary verification only.

What a rollback leaves behind: the migration's rollback drops the procedures
and the empty table, and the grants and DENYs vanish with those objects; the
two roles, the maintenance user and the memberships persist holding no
object permission. Removing them is a separate administrator operation
(``ALTER ROLE ... DROP MEMBER``, ``DROP ROLE``, ``DROP USER``), deliberately
not automated here.

Output is one content-free JSON report: named boolean checks and role
names. No connection detail, no SID bytes, no raw error text - every mode
reports only an exception class on failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_SERVER = "peerslate.database.windows.net"
ALLOWED_DATABASE = "peerslate-database"
APPEND_ROLE = "interview_telemetry_append"
MAINTENANCE_ROLE = "interview_telemetry_maintenance"
APPEND_PROCEDURE = "usp_AppendInterviewAIServerCall"
PURGE_PROCEDURE = "usp_PurgeInterviewAIServerCalls"
TELEMETRY_TABLE = "interview_ai_server_calls"
# The application identity: the App Service system-assigned identity that
# already exists in the database as an EXTERNAL_USER.
APPLICATION_PRINCIPAL = "peerslate-pete"
# The dedicated Interview maintenance identity - never the Community one.
MAINTENANCE_PRINCIPAL = "peerslate-interview-telemetry-maintenance"
COMMUNITY_PRINCIPAL = "peerslate-community-maintenance"

ROLE_GRANTS = (
    (APPEND_ROLE, APPEND_PROCEDURE),
    (MAINTENANCE_ROLE, PURGE_PROCEDURE),
)
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _client_sid(client_id):
    """Return SQL's explicit EXTERNAL_USER SID for one Entra application ID."""

    try:
        return UUID(str(client_id)).bytes_le
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError("Maintenance principal client ID is invalid.") from error


def _safe(name):
    if not SAFE_NAME.fullmatch(str(name or "")):
        raise ValueError("Principal name is invalid.")
    return name


def _drain(cursor):
    while cursor.nextset():
        pass


# --------------------------------------------------------------------------
# apply
# --------------------------------------------------------------------------


def ensure_roles_and_grants(cursor):
    """Create both execute-only roles and their single grants. Idempotent.

    Shared with the disposable-database proof so the gate proves the same
    statements an administrator runs in production.
    """

    for role, procedure in ROLE_GRANTS:
        cursor.execute(
            f"IF DATABASE_PRINCIPAL_ID(N'{role}') IS NULL CREATE ROLE [{role}];"
        )
        _drain(cursor)
        cursor.execute(
            f"GRANT EXECUTE ON OBJECT::dbo.{procedure} TO [{role}];"
        )
        _drain(cursor)


def ensure_maintenance_user(cursor, maintenance_sid, principal=MAINTENANCE_PRINCIPAL):
    """Create the maintenance EXTERNAL_USER from its Entra application ID.
    Idempotent: an existing principal is left untouched (verify then checks
    that its SID is the expected one)."""

    _safe(principal)
    sid_literal = "0x" + bytes(maintenance_sid).hex()
    cursor.execute(
        f"IF DATABASE_PRINCIPAL_ID(N'{principal}') IS NULL "
        f"CREATE USER [{principal}] WITH SID = {sid_literal}, TYPE = E;"
    )
    _drain(cursor)


def ensure_memberships(
    cursor,
    application_principal=APPLICATION_PRINCIPAL,
    maintenance_principal=MAINTENANCE_PRINCIPAL,
):
    for role, member in (
        (APPEND_ROLE, _safe(application_principal)),
        (MAINTENANCE_ROLE, _safe(maintenance_principal)),
    ):
        cursor.execute(
            f"IF IS_ROLEMEMBER(N'{role}', N'{member}') = 0 "
            f"ALTER ROLE [{role}] ADD MEMBER [{member}];"
        )
        _drain(cursor)


def ensure_application_denies(cursor, principal=APPLICATION_PRINCIPAL):
    """Close the application identity's broad standing grants at the
    telemetry boundary. DENY overrides GRANT; ownership chaining keeps the
    append procedure working. Idempotent. The disposable proof passes a
    stand-in principal carrying the same broad grants."""

    _safe(principal)
    cursor.execute(
        f"DENY EXECUTE ON OBJECT::dbo.{PURGE_PROCEDURE} TO [{principal}];"
    )
    _drain(cursor)
    cursor.execute(
        f"DENY SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.{TELEMETRY_TABLE} "
        f"TO [{principal}];"
    )
    _drain(cursor)


def apply(
    cursor,
    maintenance_sid,
    *,
    application_principal=APPLICATION_PRINCIPAL,
    maintenance_principal=MAINTENANCE_PRINCIPAL,
):
    ensure_roles_and_grants(cursor)
    ensure_maintenance_user(cursor, maintenance_sid, maintenance_principal)
    ensure_memberships(cursor, application_principal, maintenance_principal)
    ensure_application_denies(cursor, application_principal)


# --------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------


def _principal(cursor, name):
    cursor.execute(
        "SELECT type_desc, sid FROM sys.database_principals WHERE name = ?;",
        (name,),
    )
    row = cursor.fetchone()
    return None if row is None else (str(row[0]), bytes(row[1] or b""))


def _memberships(cursor, member):
    cursor.execute(
        "SELECT role_principal.name "
        "FROM sys.database_role_members AS membership "
        "JOIN sys.database_principals AS role_principal "
        "  ON role_principal.principal_id = membership.role_principal_id "
        "JOIN sys.database_principals AS member_principal "
        "  ON member_principal.principal_id = membership.member_principal_id "
        "WHERE member_principal.name = ?;",
        (member,),
    )
    return sorted(str(row[0]) for row in cursor.fetchall())


def _direct_permissions(cursor, principal):
    cursor.execute(
        "SELECT permission_entry.class_desc, permission_entry.permission_name, "
        "       permission_entry.state_desc, "
        "       COALESCE(OBJECT_NAME(CASE WHEN permission_entry.class = 1 "
        "                            THEN permission_entry.major_id END), '') "
        "FROM sys.database_permissions AS permission_entry "
        "JOIN sys.database_principals AS principal "
        "  ON principal.principal_id = permission_entry.grantee_principal_id "
        "WHERE principal.name = ?;",
        (principal,),
    )
    return {
        (str(row[0]), str(row[1]), str(row[2]), str(row[3] or ""))
        for row in cursor.fetchall()
    }


def _effective(cursor, user, securable, permission):
    """Tri-state effective permission for ``user`` on ``dbo.securable``:
    True, False, or None when SQL cannot evaluate it (HAS_PERMS_BY_NAME
    returns NULL for an unknown securable). Callers treat None as a
    failure in BOTH directions - "cannot" is never inferred from NULL."""

    cursor.execute(f"EXECUTE AS USER = N'{_safe(user)}';")
    _drain(cursor)
    try:
        cursor.execute(
            "SELECT HAS_PERMS_BY_NAME(?, 'OBJECT', ?);",
            (f"dbo.{securable}", permission),
        )
        value = cursor.fetchone()[0]
        if value is None:
            return None
        return int(value) == 1
    finally:
        cursor.execute("REVERT;")
        _drain(cursor)


def _table_access_closed(cursor, user):
    """True only when every direct table permission evaluates to 0."""

    for permission in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        if _effective(cursor, user, TELEMETRY_TABLE, permission) is not False:
            return False
    return True


def verify(
    cursor,
    maintenance_sid,
    *,
    expected_database=ALLOWED_DATABASE,
    application_principal=APPLICATION_PRINCIPAL,
    maintenance_principal=MAINTENANCE_PRINCIPAL,
):
    """Verify the complete boundary. Returns a content-free report."""

    _safe(application_principal)
    _safe(maintenance_principal)
    expected_sid = bytes(maintenance_sid)
    report = {}
    cursor.execute("SELECT DB_NAME();")
    report["database_ok"] = str(cursor.fetchone()[0]) == expected_database

    cursor.execute(
        "SELECT OBJECT_ID(?, 'U'), OBJECT_ID(?, 'P'), OBJECT_ID(?, 'P');",
        (f"dbo.{TELEMETRY_TABLE}", f"dbo.{APPEND_PROCEDURE}", f"dbo.{PURGE_PROCEDURE}"),
    )
    report["objects_present"] = all(value is not None for value in cursor.fetchone())

    roles_ok = True
    grants_ok = True
    for role, procedure in ROLE_GRANTS:
        principal = _principal(cursor, role)
        roles_ok = roles_ok and principal is not None and principal[0] == "DATABASE_ROLE"
        grants_ok = grants_ok and _direct_permissions(cursor, role) == {
            ("OBJECT_OR_COLUMN", "EXECUTE", "GRANT", procedure)
        }
    report["roles_present"] = roles_ok
    report["role_grants_exact"] = grants_ok

    application = _principal(cursor, application_principal)
    maintenance = _principal(cursor, maintenance_principal)
    report["application_principal_present"] = application is not None
    report["maintenance_principal_external_with_expected_sid"] = bool(
        maintenance
        and maintenance[0] == "EXTERNAL_USER"
        and maintenance[1] == expected_sid
    )

    application_roles = _memberships(cursor, application_principal)
    maintenance_roles = _memberships(cursor, maintenance_principal) if maintenance else []
    report["application_roles"] = application_roles
    report["maintenance_roles"] = maintenance_roles
    report["append_role_bound_to_application"] = APPEND_ROLE in application_roles
    report["maintenance_role_bound_to_maintenance_only"] = (
        maintenance_roles == [MAINTENANCE_ROLE]
    )
    report["cross_binding_absent"] = (
        MAINTENANCE_ROLE not in application_roles
        and APPEND_ROLE not in maintenance_roles
    )
    report["community_identity_not_bound"] = not any(
        role in (APPEND_ROLE, MAINTENANCE_ROLE)
        for role in _memberships(cursor, COMMUNITY_PRINCIPAL)
    )
    report["maintenance_direct_permissions_connect_only"] = bool(maintenance) and (
        _direct_permissions(cursor, maintenance_principal)
        <= {("DATABASE", "CONNECT", "GRANT", "")}
    )
    report["application_denies_recorded"] = bool(application) and {
        ("OBJECT_OR_COLUMN", "EXECUTE", "DENY", PURGE_PROCEDURE),
        ("OBJECT_OR_COLUMN", "SELECT", "DENY", TELEMETRY_TABLE),
        ("OBJECT_OR_COLUMN", "INSERT", "DENY", TELEMETRY_TABLE),
        ("OBJECT_OR_COLUMN", "UPDATE", "DENY", TELEMETRY_TABLE),
        ("OBJECT_OR_COLUMN", "DELETE", "DENY", TELEMETRY_TABLE),
    } <= _direct_permissions(cursor, application_principal)

    bound = (
        report["objects_present"]
        and report["append_role_bound_to_application"]
        and report["maintenance_role_bound_to_maintenance_only"]
    )
    if bound:
        report["application_can_append"] = (
            _effective(cursor, application_principal, APPEND_PROCEDURE, "EXECUTE") is True
        )
        report["application_cannot_purge"] = (
            _effective(cursor, application_principal, PURGE_PROCEDURE, "EXECUTE") is False
        )
        report["maintenance_can_purge"] = (
            _effective(cursor, maintenance_principal, PURGE_PROCEDURE, "EXECUTE") is True
        )
        report["maintenance_cannot_append"] = (
            _effective(cursor, maintenance_principal, APPEND_PROCEDURE, "EXECUTE") is False
        )
        report["maintenance_no_direct_table_access"] = _table_access_closed(
            cursor, maintenance_principal
        )
        report["application_no_direct_table_access"] = _table_access_closed(
            cursor, application_principal
        )
    else:
        report["effective_permissions_checked"] = False

    checks = {key: value for key, value in report.items() if isinstance(value, bool)}
    report["result"] = "pass" if checks and all(checks.values()) else "FAIL"
    return report


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def _open():
    """Connect as the server's Entra administrator. No credential is read
    or written anywhere: the token comes from the signed-in Azure identity
    (DefaultAzureCredential), mirroring the Community authority script."""

    from mssql_python import connect

    connection = connect(
        f"Server={ALLOWED_SERVER};Database={ALLOWED_DATABASE};"
        "Authentication=ActiveDirectoryDefault;"
        "Encrypt=yes;TrustServerCertificate=no",
        timeout=60,
    )
    connection.setautocommit(False)
    return connection


def _emit(report):
    report.setdefault("authentication", "ActiveDirectoryDefault")
    print(json.dumps(report, indent=1, sort_keys=True))


def _planned():
    return [
        f"create role {APPEND_ROLE} if absent; grant execute on "
        f"{APPEND_PROCEDURE} to it",
        f"create role {MAINTENANCE_ROLE} if absent; grant execute on "
        f"{PURGE_PROCEDURE} to it",
        f"create external user {MAINTENANCE_PRINCIPAL} if absent "
        "(SID = the Entra application ID)",
        f"add {APPLICATION_PRINCIPAL} to {APPEND_ROLE}",
        f"add {MAINTENANCE_PRINCIPAL} to {MAINTENANCE_ROLE}",
        f"deny {APPLICATION_PRINCIPAL} execute on {PURGE_PROCEDURE} and "
        f"select/insert/update/delete on {TELEMETRY_TABLE} (its standing "
        "db_datawriter and database-wide execute grants would otherwise "
        "reach past the role boundary)",
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "apply", "verify"))
    parser.add_argument("--maintenance-client-id", required=True,
                        help="Entra application ID of the Interview maintenance identity")
    parser.add_argument("--confirm-apply", action="store_true")
    args = parser.parse_args(argv)

    try:
        maintenance_sid = _client_sid(args.maintenance_client_id)
    except ValueError as error:
        _emit({"result": "refused", "reason": str(error)})
        return 2
    if args.mode == "apply" and not args.confirm_apply:
        _emit({"result": "refused", "reason": "apply requires --confirm-apply"})
        return 2

    try:
        connection = _open()
    except Exception as error:  # content-free: class only
        _emit({"result": "refused", "reason": "connection_failed",
               "error_class": type(error).__name__})
        return 2

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT DB_NAME();")
        if str(cursor.fetchone()[0]) != ALLOWED_DATABASE:
            connection.rollback()
            _emit({"result": "refused", "reason": "unexpected database"})
            return 2

        if args.mode in ("plan", "verify"):
            try:
                report = verify(cursor, maintenance_sid)
            except Exception as error:  # content-free: class only
                connection.rollback()
                _emit({"result": "FAIL", "stage": args.mode,
                       "error_class": type(error).__name__})
                return 1
            connection.rollback()
            if args.mode == "plan":
                report["planned"] = _planned()
                _emit(report)
                return 0
            _emit(report)
            return 0 if report["result"] == "pass" else 1

        # apply: one transaction, verified before commit
        try:
            apply(cursor, maintenance_sid)
            report = verify(cursor, maintenance_sid)
        except Exception as error:  # content-free: class only
            connection.rollback()
            _emit({"result": "FAIL", "committed": False, "stage": "apply",
                   "error_class": type(error).__name__})
            return 1
        if report["result"] != "pass":
            connection.rollback()
            report["committed"] = False
            _emit(report)
            return 1
        connection.commit()
        report["committed"] = True
        _emit(report)
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
