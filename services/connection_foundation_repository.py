"""Injected stored-procedure repository for PS-CONNECT-002.

The shared ``database_service`` procedure allowlist is intentionally not
changed in this non-production package.  A future integration must explicitly
add the three procedure names and construct this repository after its own
authorization.  Until then this module is a tested, inert provider seam.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from services.connection_foundation_service import (
    CONNECTION_COMMANDS,
    ConnectionAudienceSnapshot,
    ConnectionCommand,
    ConnectionCommandResult,
    ConnectionFoundationConflictError,
    ConnectionFoundationNotFoundError,
    ConnectionFoundationUnavailableError,
    validate_connection_actor_key,
    validate_connection_command,
    validate_connection_command_result,
    validate_connection_idempotency_key,
    validate_connection_parties,
    validate_connection_snapshot,
)


CONNECTION_FOUNDATION_PROCEDURES = frozenset(
    {
        "usp_CommitConnectionRelationshipCommandForActor",
        "usp_GetConnectionRelationshipSnapshotForActor",
        "usp_GetConnectionRelationshipCommandForActor",
    }
)


class ConnectionFoundationProcedureExecutor(Protocol):
    def execute_procedure(
        self,
        procedure_name: str,
        parameters: Sequence[tuple[str, object]] | None = None,
    ) -> list[list[Mapping[str, object]]]: ...


def _first_row(
    result_sets: object, *, allow_empty_result_set: bool
) -> Mapping[str, object] | None:
    """Accept only one exact stored-procedure result shape.

    A procedure that returns an extra row or result set is not an acceptable
    winner or absence signal: accepting its first row could silently discard
    relationship data that belongs to another query branch. Read procedures
    may return one empty list for neutral absence; a commit must always return
    exactly one mapping row.
    """

    if not isinstance(result_sets, list) or len(result_sets) != 1:
        raise ConnectionFoundationUnavailableError()
    result_set = result_sets[0]
    if not isinstance(result_set, list):
        raise ConnectionFoundationUnavailableError()
    if not result_set:
        if allow_empty_result_set:
            return None
        raise ConnectionFoundationUnavailableError()
    if len(result_set) != 1:
        raise ConnectionFoundationUnavailableError()
    row = result_set[0]
    if not isinstance(row, Mapping):
        raise ConnectionFoundationUnavailableError()
    return row


def _bit(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    return None


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _snapshot_from_row(
    row: Mapping[str, object], *, actor_user_key: str, subject_user_key: str
) -> ConnectionAudienceSnapshot:
    expected = {
        "actor_user_key",
        "subject_user_key",
        "state",
        "relationship_version",
        "block_epoch",
        "blocked_either_direction",
    }
    if set(row) != expected:
        raise ConnectionFoundationUnavailableError()
    blocked = _bit(row.get("blocked_either_direction"))
    if blocked is None:
        raise ConnectionFoundationUnavailableError()
    snapshot = ConnectionAudienceSnapshot(
        actor_key=_text(row.get("actor_user_key")) or "",
        subject_owner_key=_text(row.get("subject_user_key")) or "",
        state=_text(row.get("state")) or "",
        relationship_version=_text(row.get("relationship_version")) or "",
        block_epoch=_text(row.get("block_epoch")) or "",
        blocked_either_direction=blocked,
    )
    return validate_connection_snapshot(
        snapshot, actor_key=actor_user_key, subject_owner_key=subject_user_key
    )


def _command_result_from_row(
    row: Mapping[str, object], *, actor_user_key: str, subject_user_key: str | None = None
) -> ConnectionCommandResult:
    expected = {
        "committed",
        "command_key",
        "actor_user_key",
        "subject_user_key",
        "command",
        "idempotency_key",
        "request_digest",
        "state",
        "relationship_version",
        "block_epoch",
        "blocked_either_direction",
    }
    if set(row) != expected or _bit(row.get("committed")) is not True:
        raise ConnectionFoundationUnavailableError()
    returned_subject = _text(row.get("subject_user_key"))
    if returned_subject is None:
        raise ConnectionFoundationUnavailableError()
    if subject_user_key is not None and returned_subject != subject_user_key:
        raise ConnectionFoundationNotFoundError()
    snapshot = _snapshot_from_row(
        {
            "actor_user_key": row["actor_user_key"],
            "subject_user_key": row["subject_user_key"],
            "state": row["state"],
            "relationship_version": row["relationship_version"],
            "block_epoch": row["block_epoch"],
            "blocked_either_direction": row["blocked_either_direction"],
        },
        actor_user_key=actor_user_key,
        subject_user_key=returned_subject,
    )
    result = ConnectionCommandResult(
        command_key=_text(row.get("command_key")) or "",
        actor_key=_text(row.get("actor_user_key")) or "",
        subject_owner_key=returned_subject,
        command=_text(row.get("command")) or "",
        idempotency_key=_text(row.get("idempotency_key")) or "",
        request_digest=_text(row.get("request_digest")) or "",
        snapshot=snapshot,
    )
    return validate_connection_command_result(
        result, actor_key=actor_user_key,
        **{"subject_owner_key": returned_subject},
    )


class SqlConnectionFoundationRepository:
    """Exact operation adapter.  It is deliberately unregistered at startup."""

    def __init__(self, executor: ConnectionFoundationProcedureExecutor) -> None:
        self._executor = executor

    def _execute(
        self, procedure_name: str, parameters: Sequence[tuple[str, object]]
    ) -> list[list[Mapping[str, object]]]:
        if procedure_name not in CONNECTION_FOUNDATION_PROCEDURES:
            raise ConnectionFoundationUnavailableError()
        try:
            return self._executor.execute_procedure(procedure_name, parameters)
        except ConnectionFoundationUnavailableError:
            raise
        except Exception as error:
            raise ConnectionFoundationUnavailableError() from error

    def commit(
        self,
        *,
        actor_user_key: str,
        subject_user_key: str,
        command: ConnectionCommand,
    ) -> ConnectionCommandResult:
        actor_user_key, subject_user_key = validate_connection_parties(
            actor_user_key, subject_user_key
        )
        command = validate_connection_command(command)
        row = _first_row(
            self._execute(
                "usp_CommitConnectionRelationshipCommandForActor",
                (
                    ("@ActorUserKey", actor_user_key),
                    ("@SubjectUserKey", subject_user_key),
                    ("@Command", command.command),
                    ("@ExpectedRelationshipVersion", command.expected_relationship_version),
                    ("@IdempotencyKey", command.idempotency_key),
                    ("@RequestDigest", command.request_digest),
                ),
            ),
            allow_empty_result_set=False,
        )
        if row is None:
            raise ConnectionFoundationUnavailableError()
        committed = _bit(row.get("committed"))
        if committed is None:
            raise ConnectionFoundationUnavailableError()
        if committed is False:
            # A non-winner deliberately carries no relationship details.
            if set(row) != {"committed"}:
                raise ConnectionFoundationUnavailableError()
            raise ConnectionFoundationConflictError()
        result = _command_result_from_row(
            row, actor_user_key=actor_user_key, subject_user_key=subject_user_key
        )
        if not (
            result.command == command.command
            and result.idempotency_key == command.idempotency_key
            and result.request_digest == command.request_digest
        ):
            raise ConnectionFoundationConflictError()
        return result

    def current_audience_snapshot(
        self, *, actor_user_key: str, subject_user_key: str
    ) -> ConnectionAudienceSnapshot | None:
        actor_user_key, subject_user_key = validate_connection_parties(
            actor_user_key, subject_user_key
        )
        row = _first_row(
            self._execute(
                "usp_GetConnectionRelationshipSnapshotForActor",
                (
                    ("@ActorUserKey", actor_user_key),
                    ("@SubjectUserKey", subject_user_key),
                ),
            ),
            allow_empty_result_set=True,
        )
        if row is None:
            return None
        return _snapshot_from_row(
            row, actor_user_key=actor_user_key, subject_user_key=subject_user_key
        )

    def command_for(
        self, *, actor_user_key: str, idempotency_key: str
    ) -> ConnectionCommandResult | None:
        actor_user_key = validate_connection_actor_key(actor_user_key)
        idempotency_key = validate_connection_idempotency_key(idempotency_key)
        row = _first_row(
            self._execute(
                "usp_GetConnectionRelationshipCommandForActor",
                (("@ActorUserKey", actor_user_key), ("@IdempotencyKey", idempotency_key)),
            ),
            allow_empty_result_set=True,
        )
        if row is None:
            return None
        return _command_result_from_row(row, actor_user_key=actor_user_key)
