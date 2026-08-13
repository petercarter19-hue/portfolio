from __future__ import annotations

import inspect
import unittest
from dataclasses import replace

from identity import PeerSlateIdentity
from services.connection_foundation_service import (
    ConnectionAudienceSnapshot,
    ConnectionCommand,
    ConnectionCommandResult,
    ConnectionFoundationAuthorizationError,
    ConnectionFoundationConflictError,
    ConnectionFoundationNotFoundError,
    ConnectionFoundationProfileReader,
    ConnectionFoundationService,
    ConnectionFoundationUnavailableError,
    ConnectionFoundationValidationError,
)


ACTOR = PeerSlateIdentity(
    "actorAlpha_001", "test", "https://issuer.example", "actor-subject"
)
OTHER_ACTOR = PeerSlateIdentity(
    "otherActor_02", "test", "https://issuer.example", "other-subject"
)
SUBJECT = "subjectBravo_02"
DIGEST = "a" * 64


def snapshot(*, state="connected", actor=ACTOR.user_key, subject=SUBJECT, version=1, epoch=1):
    return ConnectionAudienceSnapshot(
        actor_key=actor,
        subject_owner_key=subject,
        state=state,
        relationship_version=f"rel_{version:020d}",
        block_epoch=f"blk_{epoch:020d}",
        blocked_either_direction=state == "blocked",
    )


def command(name="request", *, key="request-0001", digest=DIGEST, version=None):
    return ConnectionCommand(
        command=name,
        idempotency_key=key,
        request_digest=digest,
        expected_relationship_version=version,
    )


def result(*, actor=ACTOR.user_key, subject=SUBJECT, value=None, name="request", key="request-0001", digest=DIGEST):
    return ConnectionCommandResult(
        command_key="command_0001",
        actor_key=actor,
        subject_owner_key=subject,
        command=name,
        idempotency_key=key,
        request_digest=digest,
        snapshot=value or snapshot(actor=actor, subject=subject),
    )


class Store:
    def __init__(self):
        self.calls = []
        self.committed = result()
        self.current = snapshot()
        self.existing = result()
        self.error = None

    def commit(self, **kwargs):
        self.calls.append(("commit", kwargs))
        if self.error:
            raise self.error
        return self.committed

    def current_audience_snapshot(self, **kwargs):
        self.calls.append(("snapshot", kwargs))
        if self.error:
            raise self.error
        return self.current

    def command_for(self, **kwargs):
        self.calls.append(("command_for", kwargs))
        if self.error:
            raise self.error
        return self.existing


class ConnectionFoundationServiceTests(unittest.TestCase):
    def test_execute_derives_the_actor_from_peer_slate_identity_only(self):
        store = Store()
        service = ConnectionFoundationService(store)

        committed = service.execute(identity=ACTOR, subject_user_key=SUBJECT, command=command())

        self.assertEqual(committed, store.committed)
        self.assertEqual(
            store.calls,
            [("commit", {
                "actor_user_key": ACTOR.user_key,
                "subject_user_key": SUBJECT,
                "command": command(),
            })],
        )
        self.assertNotIn("actor_user_key", inspect.signature(service.execute).parameters)

    def test_structural_or_invalid_identity_is_refused_before_any_retrieval_or_write(self):
        store = Store()
        service = ConnectionFoundationService(store)
        lookalike = type("Identity", (), {
            "user_key": ACTOR.user_key,
            "auth_provider": "test",
            "auth_issuer": "issuer",
            "auth_subject": "subject",
        })()

        for identity in (lookalike, None, PeerSlateIdentity("bad key", "test", "issuer", "sub")):
            with self.assertRaises(ConnectionFoundationAuthorizationError):
                service.execute(identity=identity, subject_user_key=SUBJECT, command=command())

        self.assertEqual(store.calls, [])

    def test_initial_request_or_block_can_start_a_pair_but_every_other_action_needs_a_version(self):
        store = Store()
        service = ConnectionFoundationService(store)

        service.execute(identity=ACTOR, subject_user_key=SUBJECT, command=command("request"))
        store.committed = result(name="block", key="block-0001", value=snapshot(state="blocked"))
        service.execute(identity=ACTOR, subject_user_key=SUBJECT, command=command("block", key="block-0001"))
        for name in ("accept", "decline", "cancel", "expire", "disconnect", "unblock", "reconnect"):
            with self.assertRaises(ConnectionFoundationValidationError):
                service.execute(
                    identity=ACTOR,
                    subject_user_key=SUBJECT,
                    command=command(name, key=f"{name}-0001"),
                )

        self.assertEqual([name for name, _ in store.calls], ["commit", "commit"])

    def test_block_epoch_cannot_be_substituted_for_the_relationship_cas_token(self):
        store = Store()
        service = ConnectionFoundationService(store)

        with self.assertRaises(ConnectionFoundationValidationError):
            service.execute(
                identity=ACTOR,
                subject_user_key=SUBJECT,
                command=command(
                    "disconnect",
                    key="disconnect-01",
                    version="blk_00000000000000000001",
                ),
            )
        store.current = replace(
            snapshot(),
            relationship_version="blk_00000000000000000001",
        )
        with self.assertRaises(ConnectionFoundationNotFoundError):
            service.profile_audience_snapshot(identity=ACTOR, subject_user_key=SUBJECT)
        self.assertEqual([name for name, _ in store.calls], ["snapshot"])

    def test_invalid_or_self_subject_has_one_neutral_not_found_result_before_store_access(self):
        store = Store()
        service = ConnectionFoundationService(store)

        for subject in ("short", ACTOR.user_key, None, "bad key"):
            with self.assertRaises(ConnectionFoundationNotFoundError) as raised:
                service.execute(identity=ACTOR, subject_user_key=subject, command=command())
            self.assertEqual(raised.exception.code, "not_found")

        self.assertEqual(store.calls, [])

    def test_snapshot_is_authorized_before_return_and_cross_owner_data_is_neutral(self):
        store = Store()
        store.current = snapshot(actor=OTHER_ACTOR.user_key)
        service = ConnectionFoundationService(store)

        with self.assertRaises(ConnectionFoundationNotFoundError) as raised:
            service.profile_audience_snapshot(identity=ACTOR, subject_user_key=SUBJECT)

        self.assertEqual(raised.exception.code, "not_found")
        self.assertEqual(store.calls[0][0], "snapshot")

    def test_absent_snapshot_and_cross_owner_command_are_neutral_not_found(self):
        store = Store()
        store.current = None
        store.existing = result(actor=OTHER_ACTOR.user_key)
        service = ConnectionFoundationService(store)

        with self.assertRaises(ConnectionFoundationNotFoundError):
            service.profile_audience_snapshot(identity=ACTOR, subject_user_key=SUBJECT)
        with self.assertRaises(ConnectionFoundationNotFoundError):
            service.command_result(identity=ACTOR, idempotency_key="request-0001")

    def test_mismatched_idempotency_receipt_is_a_conflict_not_a_new_winner(self):
        store = Store()
        store.committed = result(digest="b" * 64)
        service = ConnectionFoundationService(store)

        with self.assertRaises(ConnectionFoundationConflictError):
            service.execute(identity=ACTOR, subject_user_key=SUBJECT, command=command())

    def test_bad_snapshot_shape_or_block_invariant_fails_closed(self):
        store = Store()
        store.current = replace(snapshot(state="connected"), blocked_either_direction=True)
        service = ConnectionFoundationService(store)

        with self.assertRaises(ConnectionFoundationNotFoundError):
            service.profile_audience_snapshot(identity=ACTOR, subject_user_key=SUBJECT)

    def test_unexpected_provider_failure_is_unavailable_without_leaking_target_state(self):
        store = Store()
        store.error = RuntimeError("database details must not escape")
        service = ConnectionFoundationService(store)

        with self.assertRaises(ConnectionFoundationUnavailableError) as raised:
            service.profile_audience_snapshot(identity=ACTOR, subject_user_key=SUBJECT)
        self.assertEqual(raised.exception.code, "unavailable")

    def test_command_lookup_validates_the_key_before_repository_access(self):
        store = Store()
        service = ConnectionFoundationService(store)

        with self.assertRaises(ConnectionFoundationValidationError):
            service.command_result(identity=ACTOR, idempotency_key="bad key")
        self.assertEqual(store.calls, [])

    def test_command_result_none_is_neutral_absence_but_malformed_provider_values_are_unavailable(self):
        class MissingSubject:
            pass

        class ThrowingSubject:
            @property
            def subject_owner_key(self):
                raise RuntimeError("provider attribute failure")

        store = Store()
        service = ConnectionFoundationService(store)
        store.existing = None
        with self.assertRaises(ConnectionFoundationNotFoundError):
            service.command_result(identity=ACTOR, idempotency_key="request-0001")

        for hostile in (
            {},
            MissingSubject(),
            ThrowingSubject(),
            replace(result(), subject_owner_key=7),
        ):
            with self.subTest(hostile=type(hostile).__name__):
                store.existing = hostile
                with self.assertRaises(ConnectionFoundationUnavailableError) as raised:
                    service.command_result(identity=ACTOR, idempotency_key="request-0001")
                self.assertEqual(raised.exception.code, "unavailable")

    def test_profile_reader_returns_the_exact_profile_snapshot_shape_without_wiring_profile(self):
        store = Store()

        value = ConnectionFoundationProfileReader(store).current_snapshot(**{
            "actor_key": ACTOR.user_key,
            "subject_owner_key": SUBJECT,
        })

        from services.profile_relationship_service import ProfileRelationshipSnapshot

        self.assertIsInstance(value, ProfileRelationshipSnapshot)
        self.assertEqual(value, ProfileRelationshipSnapshot(
            actor_key=ACTOR.user_key,
            subject_owner_key=SUBJECT,
            state="connected",
            relationship_version="rel_00000000000000000001",
            block_epoch="blk_00000000000000000001",
            blocked_either_direction=False,
        ))

    def test_profile_reader_neutralizes_invalid_absent_and_cross_owner_snapshots_but_not_outages(self):
        store = Store()
        reader = ConnectionFoundationProfileReader(store)

        self.assertIsNone(reader.current_snapshot(actor_key=ACTOR.user_key, subject_owner_key=ACTOR.user_key))
        self.assertEqual(store.calls, [])
        store.current = None
        self.assertIsNone(reader.current_snapshot(actor_key=ACTOR.user_key, subject_owner_key=SUBJECT))
        store.current = snapshot(actor=OTHER_ACTOR.user_key)
        self.assertIsNone(reader.current_snapshot(actor_key=ACTOR.user_key, subject_owner_key=SUBJECT))
        store.error = RuntimeError("unavailable")
        with self.assertRaises(ConnectionFoundationUnavailableError):
            reader.current_snapshot(actor_key=ACTOR.user_key, subject_owner_key=SUBJECT)


if __name__ == "__main__":
    unittest.main()
