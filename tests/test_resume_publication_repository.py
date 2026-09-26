"""Repository adapters for Resume publication. No SQL engine proof."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from services.resume_publication_repository import (
    PUBLICATION_BROWSER_PROCEDURES,
    PUBLICATION_INTERNAL_PROCEDURES,
    InMemoryResumePublicationRepository,
    PublicationConflictError,
    PublicationDenied,
    PublicationStoreUnavailable,
    SqlResumePublicationRepository,
    empty_publication_snapshot,
)
from services.database_service import ALLOWED_PROCEDURES, DatabaseServiceError


class ResumePublicationRepositoryTests(unittest.TestCase):
    def test_in_memory_owners_are_isolated(self):
        store = InMemoryResumePublicationRepository()
        snapshot = empty_publication_snapshot()
        snapshot["slug"] = "alice"
        store.save_owner("member-a", snapshot)
        other = store.load_owner("member-b")
        self.assertIsNone(other["slug"])
        self.assertEqual(store.load_owner("member-a")["slug"], "alice")

    def test_sql_adapter_names_the_complete_command_only(self):
        database = MagicMock()
        database.last_row.return_value = {
            "committed": 1,
            "replayed": 0,
            "outcome": "published",
            "request_digest": "a" * 64,
            "read_state": "current",
            "publication_revision": 1,
        }
        result = SqlResumePublicationRepository(database).commit_command(
            "member-a",
            "00000000-0000-4000-8000-000000000001",
            {"type": "publish"},
        )
        self.assertTrue(result["committed"])
        self.assertEqual(
            database.last_row.call_args.args[0],
            "usp_CommitResumePublicationCommandForOwner",
        )

    def test_sql_unavailable_and_denied_media(self):
        database = MagicMock()
        database.first_row.side_effect = ValueError("missing")
        with self.assertRaises(PublicationStoreUnavailable):
            SqlResumePublicationRepository(database).get_public_by_slug("alice")
        database.first_row.side_effect = None
        database.first_row.return_value = {"authorized": 0}
        with self.assertRaises(PublicationDenied):
            SqlResumePublicationRepository(database).authorize_media("alice", "story_banner", 1)

    def test_sql_load_owner_maps_media_json_onto_current_publication(self):
        database = MagicMock()
        database.first_row.return_value = {
            "sharing_enabled": 1,
            "sharing_epoch": 1,
            "publication_revision": 2,
            "current_revision": 2,
            "public_slug": "alice",
            "media_json": '{"portrait": {"active": true}}',
        }
        snapshot = SqlResumePublicationRepository(database).load_owner("member-a")
        self.assertEqual(
            snapshot["publications"][2]["media"]["portrait"]["active"],
            True,
        )
        database.first_row.assert_called_once()
        self.assertEqual(
            database.first_row.call_args.args[0],
            "usp_GetResumePublicationForOwner",
        )

    def test_browser_procedures_are_allowlisted_and_internals_are_not(self):
        for name in PUBLICATION_BROWSER_PROCEDURES:
            self.assertIn(name, ALLOWED_PROCEDURES)
        for name in PUBLICATION_INTERNAL_PROCEDURES:
            self.assertNotIn(name, ALLOWED_PROCEDURES)

    def test_sql_commit_maps_wrapped_54022_to_request_conflict(self):
        database = MagicMock()
        cause = RuntimeError(
            "[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]"
            "That request already used a different payload. (54022)"
        )
        try:
            raise DatabaseServiceError(
                "Database procedure usp_CommitResumePublicationCommandForOwner failed."
            ) from cause
        except DatabaseServiceError as error:
            wrapped = error
        self.assertNotIn("54022", str(wrapped))
        database.last_row.side_effect = wrapped
        with self.assertRaises(PublicationConflictError) as raised:
            SqlResumePublicationRepository(database).commit_command(
                "member-a",
                "00000000-0000-4000-8000-000000000001",
                {"type": "publish"},
            )
        self.assertEqual(raised.exception.code, "request_conflict")
        self.assertIs(raised.exception.__cause__, wrapped)

    def test_sql_commit_unrelated_wrapped_failure_stays_unavailable(self):
        database = MagicMock()
        cause = RuntimeError("login failed for user 'sa'")
        try:
            raise DatabaseServiceError(
                "Database procedure usp_CommitResumePublicationCommandForOwner failed."
            ) from cause
        except DatabaseServiceError as error:
            wrapped = error
        database.last_row.side_effect = wrapped
        with self.assertRaises(PublicationStoreUnavailable):
            SqlResumePublicationRepository(database).commit_command(
                "member-a",
                "00000000-0000-4000-8000-000000000001",
                {"type": "publish"},
            )

    def test_sql_commit_maps_invalid_correction_target_and_stale_versions(self):
        database = MagicMock()
        database.last_row.side_effect = ValueError("54026 Entry is unavailable.")
        with self.assertRaises(PublicationDenied):
            SqlResumePublicationRepository(database).commit_command(
                "member-a",
                "00000000-0000-4000-8000-000000000001",
                {"type": "correct"},
            )
        database.last_row.side_effect = ValueError("54023 The publication changed.")
        with self.assertRaises(PublicationConflictError) as raised:
            SqlResumePublicationRepository(database).commit_command(
                "member-a",
                "00000000-0000-4000-8000-000000000002",
                {"type": "correct"},
            )
        self.assertEqual(raised.exception.code, "stale_publish")

    def test_sql_commit_classifies_wrapped_correction_errors(self):
        database = MagicMock()
        for code, expected_type, expected_code in (
            ("54023", PublicationConflictError, "stale_publish"),
            ("54026", PublicationDenied, "denied"),
            ("54027", PublicationDenied, "denied"),
            ("54028", PublicationDenied, "denied"),
            ("54029", PublicationDenied, "denied"),
        ):
            try:
                raise DatabaseServiceError("Database procedure failed.") from RuntimeError(
                    f"SQL Server rejected correction ({code})"
                )
            except DatabaseServiceError as error:
                database.last_row.side_effect = error
            with self.subTest(code=code), self.assertRaises(expected_type) as raised:
                SqlResumePublicationRepository(database).commit_command(
                    "member-a", "00000000-0000-4000-8000-000000000003", {"type": "correct"}
                )
            self.assertEqual(raised.exception.code, expected_code)

    def test_sql_commit_classifies_exact_server_messages_without_numbers(self):
        database = MagicMock()
        repository = SqlResumePublicationRepository(database)
        for message in (
            "Entry is unavailable.",
            "Expected content and access versions are required.",
            "Entry is not active.",
            "Canonical source did not change.",
        ):
            try:
                raise DatabaseServiceError("Database procedure failed.") from RuntimeError(
                    f"Driver Error: [Microsoft][SQL Server]{message}"
                )
            except DatabaseServiceError as error:
                database.last_row.side_effect = error
            with self.subTest(message=message), self.assertRaises(PublicationDenied):
                repository.commit_command(
                    "member-a", "00000000-0000-4000-8000-000000000003", {"type": "correct"}
                )
        database.last_row.side_effect = ValueError("Entry is unavailable.")
        with self.assertRaises(PublicationStoreUnavailable):
            repository.commit_command(
                "member-a", "00000000-0000-4000-8000-000000000004", {"type": "correct"}
            )
        for suffix in ("", " (54015)"):
            try:
                raise DatabaseServiceError("Database procedure failed.") from RuntimeError(
                    "Driver Error: [Microsoft][SQL Server]Canonical source is unavailable."
                    + suffix
                )
            except DatabaseServiceError as error:
                database.last_row.side_effect = error
            with self.subTest(suffix=suffix), self.assertRaises(PublicationStoreUnavailable):
                repository.commit_command(
                    "member-a", "00000000-0000-4000-8000-000000000005", {"type": "publish"}
                )
        try:
            raise DatabaseServiceError("Database procedure failed.") from RuntimeError(
                "Driver Error: [Microsoft][SQL Server]Entry is unavailable. (54015)"
            )
        except DatabaseServiceError as error:
            database.last_row.side_effect = error
        with self.assertRaises(PublicationStoreUnavailable):
            repository.commit_command(
                "member-a", "00000000-0000-4000-8000-000000000006", {"type": "publish"}
            )

    def test_wrapped_guest_and_media_denials_stay_denials(self):
        database = MagicMock()
        repository = SqlResumePublicationRepository(database)
        for code, action in (
            ("54030", lambda: repository.get_public_by_slug("alice")),
            ("54034", lambda: repository.authorize_media("alice", "illustration", None)),
        ):
            try:
                raise DatabaseServiceError("Database procedure failed.") from RuntimeError(
                    f"SQL Server refused public content ({code})"
                )
            except DatabaseServiceError as error:
                database.first_row.side_effect = error
            with self.subTest(code=code), self.assertRaises(PublicationDenied):
                action()


if __name__ == "__main__":
    unittest.main()
