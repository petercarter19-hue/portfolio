"""Fail-closed retirement for exactly two attended-proof QA members.

This module is an operator tool, not application runtime.  It accepts External
ID subjects only through non-echoing interactive input, resolves them without
selecting identity content, and emits structural counts and closed codes only.
No operation contacts Microsoft Entra.  Entra object retirement remains a
separate Pete-controlled step after ``verify-retired`` succeeds.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Sequence


ALLOWED_SERVER = "peerslate.database.windows.net"
ALLOWED_DATABASE = "peerslate-database"
PROVIDER = "aad"
MAX_CUTOFF_AGE = timedelta(days=7)
MAX_SUBJECT_LENGTH = 500
AUTHORIZATION_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{7,255}$")
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


class RetirementRefusal(RuntimeError):
    """A safe, closed reason for refusing an operation."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Target:
    """Transient internal keys and structural state; never serialized."""

    identity_id: int
    user_id: int
    profile_id: int
    identity_status: str
    user_active: bool
    account_status: str
    user_role: str
    profile_active: bool
    visibility: str
    identity_created_at: datetime
    user_created_at: datetime
    profile_created_at: datetime
    identity_last_seen_at: datetime | None
    user_last_seen_at: datetime | None
    auth_fields_match: bool


@dataclass(frozen=True)
class Reference:
    child_schema: str
    child_table: str
    child_column: str
    parent_schema: str
    parent_table: str
    parent_column: str
    disabled: bool
    untrusted: bool

    @property
    def key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.child_schema,
            self.child_table,
            self.child_column,
            self.parent_schema,
            self.parent_table,
            self.parent_column,
        )


ALLOWED_BASELINE_REFERENCES = {
    ("dbo", "user_identities", "user_id", "dbo", "app_users", "id"),
    ("dbo", "member_profiles", "user_id", "dbo", "app_users", "id"),
    ("dbo", "connection_preferences", "user_id", "dbo", "app_users", "id"),
    ("dbo", "audit_events", "actor_user_id", "dbo", "app_users", "id"),
}
REQUIRED_REFERENCES = ALLOWED_BASELINE_REFERENCES | {
    (
        "dbo",
        "knowledge_items",
        "owner_profile_id",
        "dbo",
        "member_profiles",
        "profile_id",
    )
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_cutoff(value: str, now: datetime) -> datetime:
    try:
        cutoff = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise RetirementRefusal("invalid_creation_cutoff") from error
    if cutoff.tzinfo is None:
        raise RetirementRefusal("creation_cutoff_must_include_timezone")
    cutoff = _utc(cutoff)
    current = _utc(now)
    if cutoff > current or current - cutoff > MAX_CUTOFF_AGE:
        raise RetirementRefusal("creation_cutoff_outside_recent_window")
    return cutoff


def validate_authorization_ref(value: str) -> str:
    if not AUTHORIZATION_REF.fullmatch(value or ""):
        raise RetirementRefusal("invalid_authorization_reference")
    return value


def _normalize_subject(value: str) -> str:
    subject = str(value or "").strip()
    if not subject or len(subject) > MAX_SUBJECT_LENGTH or any(
        ord(character) < 32 for character in subject
    ):
        raise RetirementRefusal("invalid_external_subject")
    return subject


def read_subjects(
    secret_reader: Callable[[str], str] = getpass.getpass,
    *,
    stdin_isatty: Callable[[], bool] = sys.stdin.isatty,
) -> tuple[str, str]:
    """Read and confirm the two subjects without echo or retained labels."""

    if not stdin_isatty():
        raise RetirementRefusal("interactive_terminal_required")
    values: list[str] = []
    for alias in ("member_a", "member_b"):
        first = _normalize_subject(secret_reader(f"{alias} External ID subject: "))
        second = _normalize_subject(secret_reader(f"Confirm {alias} subject: "))
        if first != second:
            raise RetirementRefusal("external_subject_confirmation_mismatch")
        values.append(first)
    if values[0] == values[1]:
        raise RetirementRefusal("external_subjects_not_distinct")
    return values[0], values[1]


def _quote(identifier: str) -> str:
    if not SAFE_IDENTIFIER.fullmatch(identifier or ""):
        raise RetirementRefusal("unsafe_database_metadata")
    return f"[{identifier}]"


def _scalar(cursor, statement: str, parameters: Sequence[object] = ()) -> int:
    cursor.execute(statement, tuple(parameters))
    row = cursor.fetchone()
    if row is None:
        raise RetirementRefusal("database_shape_mismatch")
    return int(row[0])


class SqlRetirementStore:
    """SQL Server implementation over an already-open DB-API connection."""

    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()

    def begin(self, *, serializable: bool) -> None:
        statement = "SET XACT_ABORT ON;"
        if serializable:
            statement += " SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;"
        self.cursor.execute(statement)

    def validate_database(self) -> None:
        self.cursor.execute("SELECT DB_NAME();")
        row = self.cursor.fetchone()
        if row is None or str(row[0]) != ALLOWED_DATABASE:
            raise RetirementRefusal("unexpected_database")

    def load_targets(
        self,
        subjects: Sequence[str],
        issuer: str,
        *,
        lock: bool,
    ) -> list[Target]:
        hint = " WITH (UPDLOCK, HOLDLOCK)" if lock else ""
        statement = f"""
            SELECT
                identity_record.identity_id,
                identity_record.user_id,
                profile.profile_id,
                identity_record.identity_status,
                app_user.active,
                app_user.account_status,
                app_user.user_role,
                profile.active,
                profile.visibility,
                identity_record.created_at_utc,
                app_user.created_at,
                profile.created_at_utc,
                identity_record.last_seen_at_utc,
                app_user.last_seen_at,
                CASE WHEN app_user.auth_provider = identity_record.provider
                           AND app_user.auth_issuer = identity_record.issuer
                           AND app_user.auth_subject = identity_record.subject
                     THEN 1 ELSE 0 END
            FROM dbo.user_identities AS identity_record{hint}
            JOIN dbo.app_users AS app_user{hint}
              ON app_user.id = identity_record.user_id
            JOIN dbo.member_profiles AS profile{hint}
              ON profile.user_id = app_user.id
            WHERE identity_record.provider = N'{PROVIDER}'
              AND identity_record.issuer = ?
              AND identity_record.subject = ?;
        """
        targets: list[Target] = []
        for subject in subjects:
            self.cursor.execute(statement, (issuer, subject))
            rows = list(self.cursor.fetchall())
            if len(rows) != 1:
                raise RetirementRefusal("external_subject_mapping_not_exactly_one")
            row = rows[0]
            targets.append(
                Target(
                    identity_id=int(row[0]),
                    user_id=int(row[1]),
                    profile_id=int(row[2]),
                    identity_status=str(row[3]),
                    user_active=bool(row[4]),
                    account_status=str(row[5]),
                    user_role=str(row[6]),
                    profile_active=bool(row[7]),
                    visibility=str(row[8]),
                    identity_created_at=_utc(row[9]),
                    user_created_at=_utc(row[10]),
                    profile_created_at=_utc(row[11]),
                    identity_last_seen_at=_utc(row[12]) if row[12] else None,
                    user_last_seen_at=_utc(row[13]) if row[13] else None,
                    auth_fields_match=bool(row[14]),
                )
            )
        return targets

    def references(self) -> list[Reference]:
        self.cursor.execute(
            """
            SELECT
                child_schema.name,
                child_table.name,
                child_column.name,
                parent_schema.name,
                parent_table.name,
                parent_column.name,
                foreign_key.is_disabled,
                foreign_key.is_not_trusted
            FROM sys.foreign_key_columns AS foreign_key_column
            JOIN sys.foreign_keys AS foreign_key
              ON foreign_key.object_id = foreign_key_column.constraint_object_id
            JOIN sys.tables AS child_table
              ON child_table.object_id = foreign_key_column.parent_object_id
            JOIN sys.schemas AS child_schema
              ON child_schema.schema_id = child_table.schema_id
            JOIN sys.columns AS child_column
              ON child_column.object_id = child_table.object_id
             AND child_column.column_id = foreign_key_column.parent_column_id
            JOIN sys.tables AS parent_table
              ON parent_table.object_id = foreign_key_column.referenced_object_id
            JOIN sys.schemas AS parent_schema
              ON parent_schema.schema_id = parent_table.schema_id
            JOIN sys.columns AS parent_column
              ON parent_column.object_id = parent_table.object_id
             AND parent_column.column_id = foreign_key_column.referenced_column_id
            WHERE (parent_schema.name = N'dbo' AND parent_table.name = N'app_users'
                   AND parent_column.name = N'id')
               OR (parent_schema.name = N'dbo' AND parent_table.name = N'member_profiles'
                   AND parent_column.name = N'profile_id');
            """
        )
        return [
            Reference(
                child_schema=str(row[0]),
                child_table=str(row[1]),
                child_column=str(row[2]),
                parent_schema=str(row[3]),
                parent_table=str(row[4]),
                parent_column=str(row[5]),
                disabled=bool(row[6]),
                untrusted=bool(row[7]),
            )
            for row in self.cursor.fetchall()
        ]

    def reference_count(self, reference: Reference, targets: Sequence[Target]) -> int:
        values = (
            [target.user_id for target in targets]
            if reference.parent_table == "app_users"
            else [target.profile_id for target in targets]
        )
        statement = (
            f"SELECT COUNT_BIG(*) FROM {_quote(reference.child_schema)}."
            f"{_quote(reference.child_table)} WHERE {_quote(reference.child_column)}"
            " IN (?, ?);"
        )
        return _scalar(self.cursor, statement, values)

    def identity_count(self, targets: Sequence[Target]) -> int:
        return _scalar(
            self.cursor,
            "SELECT COUNT_BIG(*) FROM dbo.user_identities WHERE user_id IN (?, ?);",
            [target.user_id for target in targets],
        )

    def profile_count(self, targets: Sequence[Target]) -> int:
        return _scalar(
            self.cursor,
            "SELECT COUNT_BIG(*) FROM dbo.member_profiles WHERE user_id IN (?, ?);",
            [target.user_id for target in targets],
        )

    def private_preference_count(self, targets: Sequence[Target]) -> int:
        return _scalar(
            self.cursor,
            """
            SELECT COUNT_BIG(*) FROM dbo.connection_preferences
            WHERE user_id IN (?, ?)
              AND discovery_opt_in = 0
              AND goal_matching_opt_in = 0
              AND recruiter_discovery_opt_in = 0
              AND discoverable_audience = N'private';
            """,
            [target.user_id for target in targets],
        )

    def workshop_item_count(self, targets: Sequence[Target]) -> int:
        return _scalar(
            self.cursor,
            "SELECT COUNT_BIG(*) FROM dbo.knowledge_items WHERE owner_profile_id IN (?, ?);",
            [target.profile_id for target in targets],
        )

    def mutate(self, action: str, targets: Sequence[Target]) -> None:
        identity_ids = [target.identity_id for target in targets]
        user_ids = [target.user_id for target in targets]
        profile_ids = [target.profile_id for target in targets]
        if action == "retire":
            statements = (
                (
                    "UPDATE dbo.user_identities SET identity_status=N'revoked', "
                    "updated_at_utc=SYSUTCDATETIME() WHERE identity_id IN (?, ?) "
                    "AND identity_status=N'active';",
                    identity_ids,
                ),
                (
                    "UPDATE dbo.app_users SET active=0, account_status=N'closed', "
                    "updated_at=SYSUTCDATETIME() WHERE id IN (?, ?) AND active=1 "
                    "AND account_status=N'active';",
                    user_ids,
                ),
                (
                    "UPDATE dbo.member_profiles SET active=0, "
                    "updated_at_utc=SYSUTCDATETIME() WHERE profile_id IN (?, ?) "
                    "AND active=1;",
                    profile_ids,
                ),
            )
        elif action == "recover":
            statements = (
                (
                    "UPDATE dbo.member_profiles SET active=1, "
                    "updated_at_utc=SYSUTCDATETIME() WHERE profile_id IN (?, ?) "
                    "AND active=0;",
                    profile_ids,
                ),
                (
                    "UPDATE dbo.app_users SET active=1, account_status=N'active', "
                    "updated_at=SYSUTCDATETIME() WHERE id IN (?, ?) AND active=0 "
                    "AND account_status=N'closed';",
                    user_ids,
                ),
                (
                    "UPDATE dbo.user_identities SET identity_status=N'active', "
                    "updated_at_utc=SYSUTCDATETIME() WHERE identity_id IN (?, ?) "
                    "AND identity_status=N'revoked';",
                    identity_ids,
                ),
            )
        else:
            raise RetirementRefusal("unsupported_operation")
        for statement, parameters in statements:
            self.cursor.execute(statement, tuple(parameters))
            if self.cursor.rowcount != 2:
                raise RetirementRefusal("atomic_update_count_mismatch")


def _validate_targets(
    targets: Sequence[Target], cutoff: datetime, expected_state: str
) -> None:
    if len(targets) != 2:
        raise RetirementRefusal("target_count_not_two")
    if len({target.identity_id for target in targets}) != 2 or len(
        {target.user_id for target in targets}
    ) != 2 or len({target.profile_id for target in targets}) != 2:
        raise RetirementRefusal("member_mappings_not_distinct")
    for target in targets:
        if target.user_role != "user":
            raise RetirementRefusal("ordinary_member_role_required")
        if target.visibility != "private":
            raise RetirementRefusal("private_profile_required")
        if not target.auth_fields_match:
            raise RetirementRefusal("identity_mapping_mismatch")
        if (
            target.identity_created_at < cutoff
            or target.user_created_at < cutoff
            or target.profile_created_at < cutoff
        ):
            raise RetirementRefusal("member_mapping_predates_cutoff")
        if target.identity_last_seen_at is None or target.user_last_seen_at is None:
            raise RetirementRefusal("member_mapping_not_observed_signed_in")
        active = (
            target.identity_status == "active"
            and target.user_active
            and target.account_status == "active"
            and target.profile_active
        )
        retired = (
            target.identity_status == "revoked"
            and not target.user_active
            and target.account_status == "closed"
            and not target.profile_active
        )
        if expected_state == "active" and not active:
            raise RetirementRefusal("active_state_required")
        if expected_state == "retired" and not retired:
            raise RetirementRefusal("retired_state_required")


def assess(
    store: SqlRetirementStore,
    subjects: Sequence[str],
    issuer: str,
    cutoff: datetime,
    *,
    expected_state: str,
    lock: bool,
) -> tuple[list[Target], dict[str, int]]:
    targets = store.load_targets(subjects, issuer, lock=lock)
    _validate_targets(targets, cutoff, expected_state)
    references = store.references()
    keys = {reference.key for reference in references}
    if not REQUIRED_REFERENCES.issubset(keys):
        raise RetirementRefusal("required_foreign_key_metadata_missing")
    if any(reference.disabled or reference.untrusted for reference in references):
        raise RetirementRefusal("foreign_key_boundary_not_enforced")
    if store.identity_count(targets) != 2:
        raise RetirementRefusal("additional_identity_mapping_present")
    if store.profile_count(targets) != 2:
        raise RetirementRefusal("profile_mapping_count_mismatch")
    if store.private_preference_count(targets) != 2:
        raise RetirementRefusal("private_connection_defaults_required")
    workshop_items = store.workshop_item_count(targets)
    disallowed = 0
    for reference in references:
        if reference.key not in ALLOWED_BASELINE_REFERENCES:
            disallowed += store.reference_count(reference, targets)
    if workshop_items or disallowed:
        raise RetirementRefusal("synthetic_member_residue_present")
    return targets, {
        "eligible_members": 2,
        "identity_mappings": 2,
        "member_profiles": 2,
        "workshop_items": 0,
        "disallowed_references": 0,
    }


def execute(
    store: SqlRetirementStore,
    *,
    mode: str,
    subjects: Sequence[str],
    issuer: str,
    cutoff: datetime,
) -> dict[str, object]:
    expected = "retired" if mode in ("verify-retired", "recover") else "active"
    mutating = mode in ("retire", "recover")
    # Every assessment spans multiple statements.  A serializable locked read
    # prevents plan/verification from combining a stale identity snapshot with
    # later counts after a concurrent retire or recovery commits.  The caller
    # holds these locks through commit/rollback.
    store.begin(serializable=True)
    store.validate_database()
    targets, counts = assess(
        store,
        subjects,
        issuer,
        cutoff,
        expected_state=expected,
        lock=True,
    )
    if mutating:
        store.mutate(mode, targets)
        final_state = "retired" if mode == "retire" else "active"
        _, counts = assess(
            store,
            subjects,
            issuer,
            cutoff,
            expected_state=final_state,
            lock=True,
        )
    result_state = {
        "plan": "eligible",
        "retire": "retired",
        "verify-retired": "retired_verified",
        "recover": "active_recovered",
    }[mode]
    return {"result": "pass", "state": result_state, "counts": counts}


def open_production_connection():
    """Open the one pinned database using the signed-in operator identity."""

    import logging

    from mssql_python import connect, driver_logger, logger

    # mssql-python's DEBUG diagnostics include bound parameter values.  This
    # dedicated privacy operation must refuse instead of risking subject
    # material in a trace file or console stream.
    if logger.isEnabledFor(logging.DEBUG) or driver_logger.isEnabledFor(logging.DEBUG):
        raise RetirementRefusal("database_diagnostic_logging_must_be_disabled")

    connection = connect(
        f"Server={ALLOWED_SERVER};Database={ALLOWED_DATABASE};"
        "Authentication=ActiveDirectoryDefault;Encrypt=yes;"
        "TrustServerCertificate=no",
        timeout=60,
    )
    connection.setautocommit(False)
    return connection


def emit(report: dict[str, object]) -> None:
    print(json.dumps(report, indent=1, sort_keys=True))


def _cleanup_connection(connection, *, rollback_required: bool) -> str | None:
    """Resolve and close without allowing a raw driver failure to escape."""

    failure_class = None
    if rollback_required:
        try:
            connection.rollback()
        except Exception as error:  # class only; never render driver detail
            failure_class = type(error).__name__
    try:
        connection.close()
    except Exception as error:  # class only; never render driver detail
        failure_class = failure_class or type(error).__name__
    return failure_class


def _confirmed(args: argparse.Namespace) -> None:
    if args.mode == "retire" and not (
        args.confirm_exact_two_synthetic_members
        and args.confirm_workshop_cleanup_complete
        and args.confirm_retire
    ):
        raise RetirementRefusal("retirement_confirmations_required")
    if args.mode == "recover" and not (
        args.confirm_exact_two_synthetic_members
        and args.confirm_external_identities_not_permanently_deleted
        and args.confirm_recover
    ):
        raise RetirementRefusal("recovery_confirmations_required")


def main(
    argv: Sequence[str] | None = None,
    *,
    connection_factory: Callable[[], object] = open_production_connection,
    secret_reader: Callable[[str], str] = getpass.getpass,
    stdin_isatty: Callable[[], bool] = sys.stdin.isatty,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "retire", "verify-retired", "recover"))
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--created-after-utc", required=True)
    parser.add_argument("--confirm-exact-two-synthetic-members", action="store_true")
    parser.add_argument("--confirm-workshop-cleanup-complete", action="store_true")
    parser.add_argument(
        "--confirm-external-identities-not-permanently-deleted", action="store_true"
    )
    parser.add_argument("--confirm-retire", action="store_true")
    parser.add_argument("--confirm-recover", action="store_true")
    args = parser.parse_args(argv)

    connection = None
    report: dict[str, object]
    return_code = 2
    transaction_resolved = False
    commit_attempted = False
    commit_completed = False
    try:
        validate_authorization_ref(args.authorization_ref)
        cutoff = parse_cutoff(args.created_after_utc, clock())
        _confirmed(args)
        issuer = str(os.environ.get("PEERSLATE_AUTH_ISSUER") or "").strip().rstrip("/")
        if not issuer or len(issuer) > 500:
            raise RetirementRefusal("approved_auth_issuer_required")
        subjects = read_subjects(secret_reader, stdin_isatty=stdin_isatty)
        connection = connection_factory()
        report = execute(
            SqlRetirementStore(connection),
            mode=args.mode,
            subjects=subjects,
            issuer=issuer,
            cutoff=cutoff,
        )
        if args.mode in ("retire", "recover"):
            commit_attempted = True
            connection.commit()
            commit_completed = True
        else:
            connection.rollback()
        transaction_resolved = True
        return_code = 0
    except RetirementRefusal as error:
        report = {"result": "refused", "reason_code": error.code}
    except Exception as error:  # Never emit raw database or identity material.
        report = {
            "result": "indeterminate" if commit_attempted else "refused",
            "reason_code": "commit_state_unknown" if commit_attempted else "operation_failed",
            "error_class": type(error).__name__,
        }
        return_code = 3 if commit_attempted else 2
    finally:
        if connection is not None:
            cleanup_error = _cleanup_connection(
                connection,
                rollback_required=not transaction_resolved,
            )
            if cleanup_error:
                commit_state_at_risk = commit_attempted
                report = {
                    "result": "indeterminate" if commit_state_at_risk else "refused",
                    "reason_code": (
                        "connection_cleanup_failed_after_commit"
                        if commit_completed
                        else (
                            "connection_cleanup_failed_after_commit_attempt"
                            if commit_attempted
                            else "connection_cleanup_failed"
                        )
                    ),
                    "error_class": cleanup_error,
                }
                return_code = 3 if commit_state_at_risk else 2
    emit(report)
    return return_code


__all__ = [
    "ALLOWED_DATABASE",
    "ALLOWED_SERVER",
    "Reference",
    "RetirementRefusal",
    "SqlRetirementStore",
    "Target",
    "assess",
    "execute",
    "main",
    "parse_cutoff",
    "read_subjects",
]
