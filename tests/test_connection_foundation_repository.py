from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from services.connection_foundation_repository import SqlConnectionFoundationRepository
from services.connection_foundation_service import (
    ConnectionCommand,
    ConnectionFoundationConflictError,
    ConnectionFoundationNotFoundError,
    ConnectionFoundationUnavailableError,
    ConnectionFoundationValidationError,
)


ACTOR = "actorAlpha_001"
SUBJECT = "subjectBravo_02"
DIGEST = "a" * 64


def command(*, key="request-0001", digest=DIGEST, name="request", version=None):
    return ConnectionCommand(name, key, digest, version)


def row(*, actor=ACTOR, subject=SUBJECT, key="request-0001", digest=DIGEST, name="request", state="outbound_pending", version=1, epoch=1):
    return {
        "committed": 1,
        "command_key": "command_0001",
        "actor_user_key": actor,
        "subject_user_key": subject,
        "command": name,
        "idempotency_key": key,
        "request_digest": digest,
        "state": state,
        "relationship_version": f"rel_{version:020d}",
        "block_epoch": f"blk_{epoch:020d}",
        "blocked_either_direction": state == "blocked",
    }


class Executor:
    def __init__(self, result=None):
        self.calls = []
        self.result = result if result is not None else [[row()]]

    def execute_procedure(self, name, parameters=None):
        self.calls.append((name, tuple(parameters or ())))
        return self.result


class AtomicExecutor:
    """Executable stored-procedure contract double with one idempotency winner."""

    def __init__(self):
        self.lock = Lock()
        self.calls = []
        self.receipt = None

    def execute_procedure(self, name, parameters=None):
        values = dict(parameters or ())
        with self.lock:
            self.calls.append((name, tuple(parameters or ())))
            if name == "usp_CommitConnectionRelationshipCommandForActor":
                if self.receipt is None:
                    self.receipt = row(
                        actor=values["@ActorUserKey"],
                        subject=values["@SubjectUserKey"],
                        key=values["@IdempotencyKey"],
                        digest=values["@RequestDigest"],
                        name=values["@Command"],
                    )
                elif any((
                    self.receipt["actor_user_key"] != values["@ActorUserKey"],
                    self.receipt["subject_user_key"] != values["@SubjectUserKey"],
                    self.receipt["idempotency_key"] != values["@IdempotencyKey"],
                    self.receipt["request_digest"] != values["@RequestDigest"],
                    self.receipt["command"] != values["@Command"],
                )):
                    return [[{"committed": 0}]]
                return [[dict(self.receipt)]]
            if name == "usp_GetConnectionRelationshipCommandForActor":
                if self.receipt is None or self.receipt["actor_user_key"] != values["@ActorUserKey"]:
                    return []
                return [[dict(self.receipt)]]
        raise AssertionError(name)


class ConnectionFoundationRepositoryTests(unittest.TestCase):
    def test_commit_uses_only_the_exact_injected_procedure_and_parameter_contract(self):
        executor = Executor()
        repository = SqlConnectionFoundationRepository(executor)

        committed = repository.commit(
            actor_user_key=ACTOR,
            subject_user_key=SUBJECT,
            command=command(),
        )

        self.assertEqual(committed.idempotency_key, "request-0001")
        self.assertEqual(executor.calls, [(
            "usp_CommitConnectionRelationshipCommandForActor",
            (
                ("@ActorUserKey", ACTOR),
                ("@SubjectUserKey", SUBJECT),
                ("@Command", "request"),
                ("@ExpectedRelationshipVersion", None),
                ("@IdempotencyKey", "request-0001"),
                ("@RequestDigest", DIGEST),
            ),
        )])

    def test_same_idempotency_request_has_one_atomic_winner_and_reloads_that_receipt(self):
        executor = AtomicExecutor()
        repositories = (SqlConnectionFoundationRepository(executor), SqlConnectionFoundationRepository(executor))

        with ThreadPoolExecutor(max_workers=2) as pool:
            winners = list(pool.map(
                lambda repository: repository.commit(
                    actor_user_key=ACTOR, subject_user_key=SUBJECT, command=command()
                ),
                repositories,
            ))

        self.assertEqual(winners[0], winners[1])
        self.assertEqual(winners[0].relationship_version if hasattr(winners[0], "relationship_version") else winners[0].snapshot.relationship_version, "rel_00000000000000000001")
        self.assertEqual(
            repositories[0].command_for(actor_user_key=ACTOR, idempotency_key="request-0001"),
            winners[0],
        )
        with self.assertRaises(ConnectionFoundationConflictError):
            repositories[0].commit(
                actor_user_key=ACTOR,
                subject_user_key=SUBJECT,
                command=command(digest="b" * 64),
            )

    def test_non_winner_contains_no_pair_details_and_is_reported_as_conflict(self):
        executor = Executor([[{"committed": 0}]])
        with self.assertRaises(ConnectionFoundationConflictError):
            SqlConnectionFoundationRepository(executor).commit(
                actor_user_key=ACTOR, subject_user_key=SUBJECT, command=command()
            )

        executor = Executor([[{"committed": 0, "state": "connected"}]])
        with self.assertRaises(ConnectionFoundationUnavailableError):
            SqlConnectionFoundationRepository(executor).commit(
                actor_user_key=ACTOR, subject_user_key=SUBJECT, command=command()
            )

    def test_malformed_or_cross_owner_rows_fail_closed(self):
        malformed = row()
        malformed["unexpected"] = "must not be accepted"
        with self.assertRaises(ConnectionFoundationUnavailableError):
            SqlConnectionFoundationRepository(Executor([[malformed]])).commit(
                actor_user_key=ACTOR, subject_user_key=SUBJECT, command=command()
            )

        with self.assertRaises(ConnectionFoundationNotFoundError):
            SqlConnectionFoundationRepository(Executor([[row(subject="otherSubject_03")]])).commit(
                actor_user_key=ACTOR, subject_user_key=SUBJECT, command=command()
            )

    def test_direct_repository_calls_validate_party_and_idempotency_inputs_before_executor(self):
        executor = Executor()
        repository = SqlConnectionFoundationRepository(executor)

        with self.assertRaises(ConnectionFoundationNotFoundError):
            repository.commit(actor_user_key="bad key", subject_user_key=SUBJECT, command=command())
        with self.assertRaises(ConnectionFoundationNotFoundError):
            repository.current_audience_snapshot(actor_user_key=ACTOR, subject_user_key=ACTOR)
        with self.assertRaises(ConnectionFoundationValidationError):
            repository.command_for(actor_user_key=ACTOR, idempotency_key="bad key")
        self.assertEqual(executor.calls, [])

    def test_snapshot_is_pair_scoped_and_command_lookup_is_actor_scoped(self):
        executor = Executor([[
            {
                "actor_user_key": ACTOR,
                "subject_user_key": SUBJECT,
                "state": "connected",
                "relationship_version": "rel_00000000000000000002",
                "block_epoch": "blk_00000000000000000001",
                "blocked_either_direction": 0,
            }
        ]])
        repository = SqlConnectionFoundationRepository(executor)

        snapshot = repository.current_audience_snapshot(
            actor_user_key=ACTOR, subject_user_key=SUBJECT
        )

        self.assertEqual(snapshot.state, "connected")
        self.assertEqual(executor.calls[0][0], "usp_GetConnectionRelationshipSnapshotForActor")
        self.assertEqual(
            dict(executor.calls[0][1]),
            {"@ActorUserKey": ACTOR, "@SubjectUserKey": SUBJECT},
        )

        executor.result = [[row(actor="otherActor_02")]]
        with self.assertRaises(ConnectionFoundationNotFoundError):
            repository.command_for(actor_user_key=ACTOR, idempotency_key="request-0001")

    def test_only_one_empty_result_set_is_neutral_absence_for_read_operations(self):
        self.assertIsNone(
            SqlConnectionFoundationRepository(Executor([[]])).current_audience_snapshot(
                actor_user_key=ACTOR, subject_user_key=SUBJECT
            )
        )
        self.assertIsNone(
            SqlConnectionFoundationRepository(Executor([[]])).command_for(
                actor_user_key=ACTOR, idempotency_key="request-0001"
            )
        )
        with self.assertRaises(ConnectionFoundationUnavailableError):
            SqlConnectionFoundationRepository(Executor([[]])).commit(
                actor_user_key=ACTOR, subject_user_key=SUBJECT, command=command()
            )

    def test_extra_or_non_list_result_shapes_are_unavailable_for_every_operation(self):
        shapes = (
            [],
            [[row(), row()]],
            [[row()], []],
            [[row()], ()],
            [[], []],
            [(row(),)],
            [row()],
        )
        operations = (
            lambda repository: repository.commit(
                actor_user_key=ACTOR, subject_user_key=SUBJECT, command=command()
            ),
            lambda repository: repository.current_audience_snapshot(
                actor_user_key=ACTOR, subject_user_key=SUBJECT
            ),
            lambda repository: repository.command_for(
                actor_user_key=ACTOR, idempotency_key="request-0001"
            ),
        )
        for shape in shapes:
            for operation in operations:
                with self.subTest(shape=repr(shape), operation=operations.index(operation)):
                    with self.assertRaises(ConnectionFoundationUnavailableError):
                        operation(SqlConnectionFoundationRepository(Executor(shape)))


if __name__ == "__main__":
    unittest.main()
