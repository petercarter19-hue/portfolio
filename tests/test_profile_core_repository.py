from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Lock

from services.profile_core_repository import (
    SqlProfileCoreRepository,
    decode_draft,
    decode_revision,
    encode_draft,
    encode_revision,
)
from datetime import datetime, timezone

from services.profile_core_service import (
    ProfilePublicationCommand,
    ProfilePublicationRevision,
    ProfileConflictError,
    ProfileUnavailableError,
    PROFILE_PUBLICATION_ACTION_PUBLISH,
    PROFILE_PUBLICATION_ACTION_WITHDRAW,
    make_profile_draft,
    ProfileIdentityDraft,
)


class Executor:
    def __init__(self): self.calls = []; self.result = []
    def execute_procedure(self, name, parameters=None):
        self.calls.append((name, parameters)); return self.result


class AtomicProfileProcedureExecutor:
    """A lock-holding executable stored-procedure contract double."""

    def __init__(self, draft):
        self.lock = Lock()
        self.draft = draft
        self.command_row = None

    def execute_procedure(self, name, parameters=None):
        values = dict(parameters or ())
        with self.lock:
            if name == "usp_SaveProfileDraftForOwner":
                if values["@ExpectedDraftVersion"] != self.draft.version:
                    return [[{"saved": 0}]]
                self.draft = decode_draft(values["@ManifestJson"])
                return [[{"saved": 1}]]
            if name == "usp_CommitProfilePublicationForOwner":
                if self.command_row is None:
                    self.command_row = {
                        "committed": 1,
                        "command_key": values["@CommandKey"],
                        "owner_key": values["@OwnerKey"],
                        "idempotency_key": values["@IdempotencyKey"],
                        "request_digest": values["@RequestDigest"],
                        "manifest_json": values["@ManifestJson"],
                    }
                elif self.command_row["request_digest"] != values["@RequestDigest"]:
                    return [[{"committed": 0}]]
                return [[dict(self.command_row)]]
            if name == "usp_GetProfilePublicationCommandForOwner":
                if self.command_row is None:
                    return []
                return [[dict(self.command_row)]]
        raise AssertionError(name)


class ProfileCoreRepositoryTests(unittest.TestCase):
    def test_draft_round_trip_preserves_owner_scoped_manifest(self):
        draft = make_profile_draft(
            owner_key="ownerAlpha_123", slug="avery",
            identity=ProfileIdentityDraft("Avery", "Engineer", None, "Builds useful systems."),
        )
        self.assertEqual(decode_draft(encode_draft(draft)), draft)

    def test_revision_round_trip_preserves_explicit_publication_action(self):
        revision = ProfilePublicationRevision(
            revision_key="v1:withdraw", owner_key="ownerAlpha_123", slug="avery",
            audience="public", action=PROFILE_PUBLICATION_ACTION_WITHDRAW,
            revision_number=1, created_at=datetime.now(timezone.utc), digest="a" * 64,
            identity=None, current_chapter=None, about=None, items=(),
        )
        self.assertEqual(
            decode_revision(encode_revision(revision)).action,
            PROFILE_PUBLICATION_ACTION_WITHDRAW,
        )

    def test_repository_uses_exact_named_operation(self):
        executor = Executor()
        executor.result = [[{"owner_key": "ownerAlpha_123"}]]
        repository = SqlProfileCoreRepository(executor)
        self.assertEqual(repository.profile_for_slug("avery"), "ownerAlpha_123")
        self.assertEqual(executor.calls[0][0], "usp_GetProfileOwnerBySlug")

    def test_malformed_manifest_fails_closed(self):
        executor = Executor()
        executor.result = [[{"manifest_json": '{"owner_key":"other"}'}]]
        with self.assertRaises(ProfileUnavailableError):
            SqlProfileCoreRepository(executor).draft_for_owner("ownerAlpha_123")

    def test_publication_commit_carries_expected_revision_to_atomic_boundary(self):
        executor = Executor()
        revision = ProfilePublicationRevision(
            revision_key="v2:revision", owner_key="ownerAlpha_123", slug="avery",
            audience="public", action=PROFILE_PUBLICATION_ACTION_WITHDRAW,
            revision_number=2, created_at=datetime.now(timezone.utc),
            digest="a" * 64, identity=None, current_chapter=None, about=None, items=(),
        )
        command = ProfilePublicationCommand(
            command_key="commandKey_123", owner_key="ownerAlpha_123",
            idempotency_key="publish-request-0009", request_digest="b" * 64,
            revision=revision,
        )
        executor.result = [[{
            "committed": 1,
            "command_key": command.command_key,
            "owner_key": command.owner_key,
            "idempotency_key": command.idempotency_key,
            "request_digest": command.request_digest,
            "manifest_json": encode_revision(revision),
        }]]
        expected_draft = make_profile_draft(
            owner_key="ownerAlpha_123", slug="avery",
            identity=ProfileIdentityDraft("Avery", "Engineer", None, "Summary"),
        )
        committed = SqlProfileCoreRepository(executor).append_publication(
            revision,
            command,
            action=PROFILE_PUBLICATION_ACTION_WITHDRAW,
            expected_public_revision="v1:prior",
            expected_draft=expected_draft,
        )
        params = dict(executor.calls[0][1])
        self.assertEqual(committed, command)
        self.assertEqual(params["@ExpectedPublicRevision"], "v1:prior")
        self.assertEqual(params["@PublicationAction"], PROFILE_PUBLICATION_ACTION_WITHDRAW)
        self.assertEqual(params["@ExpectedDraftKey"], expected_draft.draft_key)
        self.assertEqual(params["@ExpectedDraftVersion"], expected_draft.version)
        self.assertIn("@ExpectedDraftManifestJson", params)

    def test_repository_rejects_action_confusion_from_the_procedure_boundary(self):
        executor = Executor()
        expected_draft = make_profile_draft(
            owner_key="ownerAlpha_123", slug="avery",
            identity=ProfileIdentityDraft("Avery", "Engineer", None, "Summary"),
        )
        publish = ProfilePublicationRevision(
            revision_key="v1:publish", owner_key="ownerAlpha_123", slug="avery",
            audience="public", action=PROFILE_PUBLICATION_ACTION_PUBLISH,
            revision_number=1, created_at=datetime.now(timezone.utc), digest="a" * 64,
            identity=expected_draft.identity, current_chapter=None, about=None, items=(),
        )
        command = ProfilePublicationCommand(
            command_key="commandKey_456", owner_key="ownerAlpha_123",
            idempotency_key="publish-request-0010", request_digest="b" * 64,
            revision=publish,
        )
        confused = replace(
            publish,
            action=PROFILE_PUBLICATION_ACTION_WITHDRAW,
            identity=None,
        )
        executor.result = [[{
            "committed": 1,
            "command_key": command.command_key,
            "owner_key": command.owner_key,
            "idempotency_key": command.idempotency_key,
            "request_digest": command.request_digest,
            "manifest_json": encode_revision(confused),
        }]]
        with self.assertRaises(ProfileUnavailableError):
            SqlProfileCoreRepository(executor).append_publication(
                publish,
                command,
                action=PROFILE_PUBLICATION_ACTION_PUBLISH,
                expected_public_revision=None,
                expected_draft=expected_draft,
            )
        self.assertEqual(
            dict(executor.calls[0][1])["@PublicationAction"],
            PROFILE_PUBLICATION_ACTION_PUBLISH,
        )

    def test_two_sql_repository_writers_have_one_draft_winner(self):
        original = make_profile_draft(
            owner_key="ownerAlpha_123", slug="avery",
            identity=ProfileIdentityDraft("Avery", "Engineer", None, "Summary"),
        )
        executor = AtomicProfileProcedureExecutor(original)
        repositories = (SqlProfileCoreRepository(executor), SqlProfileCoreRepository(executor))
        drafts = (
            replace(original, version="v2:first-writer"),
            replace(original, version="v2:second-writer"),
        )

        def save(index):
            try:
                repositories[index].put_draft(drafts[index], expected_version=original.version)
                return "saved"
            except Exception as error:
                return type(error).__name__

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(save, (0, 1)))
        self.assertEqual(outcomes.count("saved"), 1)
        self.assertEqual(outcomes.count("ProfileConflictError"), 1)
        self.assertIn(executor.draft, drafts)

    def test_repository_rejects_case_only_stale_draft_version_without_overwrite(self):
        original = make_profile_draft(
            owner_key="ownerAlpha_123", slug="avery",
            identity=ProfileIdentityDraft("Avery", "Engineer", None, "Summary"),
        )
        executor = AtomicProfileProcedureExecutor(original)
        repository = SqlProfileCoreRepository(executor)
        replacement = replace(
            original,
            version="v2:replacement",
            identity=replace(original.identity, headline="This must not overwrite."),
        )
        case_only_stale_version = "V" + original.version[1:]
        self.assertNotEqual(case_only_stale_version, original.version)
        self.assertEqual(case_only_stale_version.casefold(), original.version.casefold())

        with self.assertRaises(ProfileConflictError):
            repository.put_draft(replacement, expected_version=case_only_stale_version)

        self.assertEqual(executor.draft, original)

    def test_simultaneous_identical_publish_reloads_exact_sql_winner(self):
        draft = make_profile_draft(
            owner_key="ownerAlpha_123", slug="avery",
            identity=ProfileIdentityDraft("Avery", "Engineer", None, "Summary"),
        )
        executor = AtomicProfileProcedureExecutor(draft)
        repositories = (SqlProfileCoreRepository(executor), SqlProfileCoreRepository(executor))
        revisions = tuple(
            ProfilePublicationRevision(
                revision_key=f"v1:writer-{index}", owner_key="ownerAlpha_123", slug="avery",
                audience="public", action=PROFILE_PUBLICATION_ACTION_PUBLISH,
                revision_number=1, created_at=datetime.now(timezone.utc),
                digest="a" * 64, identity=draft.identity, current_chapter=None, about=None, items=(),
            ) for index in (1, 2)
        )
        commands = tuple(
            ProfilePublicationCommand(
                command_key=f"commandKey_{index}23", owner_key="ownerAlpha_123",
                idempotency_key="publish-request-2010", request_digest="b" * 64,
                revision=revisions[index - 1],
            ) for index in (1, 2)
        )

        def publish(index):
            return repositories[index].append_publication(
                revisions[index], commands[index],
                action=PROFILE_PUBLICATION_ACTION_PUBLISH,
                expected_public_revision=None, expected_draft=draft,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(publish, (0, 1)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(
            repositories[0].command_for("ownerAlpha_123", "publish-request-2010"),
            results[0],
        )


if __name__ == "__main__": unittest.main()
