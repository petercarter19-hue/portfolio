"""Focused contracts for the real owner-authored Community public pilot."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from datetime import datetime
import os
import re
import unittest
from unittest.mock import patch
from uuid import uuid4
from types import SimpleNamespace
import hashlib

os.environ.setdefault("ANTHROPIC_API_KEY", "community-test-key")

from werkzeug.datastructures import FileStorage

from app import app
from services.community_command_service import CommunityCommandService
from services.community_contracts import (
    CommunityUnavailableError,
    CommunityValidationError,
    FEED_WINDOW_MAX,
    MAX_ATTACHMENT_BYTES,
    XLSX_CONTENT_TYPE,
    revision_number,
    safe_display_name,
    utf16_length,
)
from services.community_cursor import (
    decode_contribution_token,
    decode_shelf_token,
    decode_window_token,
    new_window_token,
    next_contribution_token,
    next_shelf_token,
    next_window_token,
)
from services.community_feed_service import (
    CommunityFeedService,
    _conversation_label,
    _utc_json,
)
from services.community_media_service import (
    CommunityMediaMaintenance,
    CommunityMediaService,
    stored_sha256,
    validate_upload,
)
from services.community_media_storage import CommunityMediaStorage, CommunityMediaStorageError
from services.database_service import DatabaseServiceError


ROOT = Path(__file__).resolve().parents[1]
OWNER_KEY = str(uuid4())
OTHER_KEY = str(uuid4())
POST_KEY = str(uuid4())


class FakeDatabase:
    def __init__(self, row=None):
        self.row = row or {"outcome": "created", "post_key": POST_KEY}
        self.calls = []

    def last_row(self, procedure, parameters):
        self.calls.append((procedure, parameters))
        return self.row


class CommunityCommandContractTests(unittest.TestCase):
    def test_revision_preconditions_reject_json_booleans(self):
        for value in (True, False):
            with self.subTest(value=value), self.assertRaises(
                CommunityValidationError
            ):
                revision_number(value)

    def test_publish_requires_explicit_public_and_never_accepts_capability_fields(self):
        service = CommunityCommandService(FakeDatabase())
        valid = {
            "body": "A real public update",
            "intent": "post",
            "response_posture": "open_feedback",
            "audience": "public",
            "attachment_keys": [],
        }
        for payload in ({**valid, "audience": None}, {**valid, "owner": True}):
            with self.subTest(payload=payload), self.assertRaises(CommunityValidationError):
                service.publish_post(OWNER_KEY, payload, "community-command-0001")

    def test_publish_binds_only_server_identity_and_idempotency(self):
        database = FakeDatabase()
        result = CommunityCommandService(database).publish_post(
            OWNER_KEY,
            {
                "body": "A real public update",
                "intent": "small_win",
                "response_posture": "sharing_only",
                "audience": "public",
                "attachment_keys": [],
            },
            "community-command-0001",
        )
        self.assertEqual(result["outcome"], "created")
        procedure, parameters = database.calls[0]
        self.assertEqual(procedure, "usp_PublishPublicCommunityPost")
        self.assertIn(("@UserKey", OWNER_KEY), parameters)
        self.assertNotIn("email", repr(parameters).lower())

    def test_contribution_kind_is_server_derived_and_client_claims_are_rejected(self):
        database = FakeDatabase()
        service = CommunityCommandService(database)
        payload = {
            "body": "A follow-up",
            "parent_key": None,
            "attachment_keys": [],
        }

        result = service.add_contribution(
            OWNER_KEY, POST_KEY, payload, "community-command-0002"
        )

        self.assertEqual(result["outcome"], "created")
        procedure, parameters = database.calls[0]
        self.assertEqual(procedure, "usp_AddPublicCommunityContribution")
        self.assertIn(("@ParentContributionKey", None), parameters)
        self.assertNotIn("@ContributionKind", dict(parameters))

        for kind in ("comment", "reply", "author_update"):
            with self.subTest(kind=kind), self.assertRaisesRegex(
                CommunityValidationError, "unsupported fields"
            ):
                service.add_contribution(
                    OWNER_KEY,
                    POST_KEY,
                    {**payload, "kind": kind},
                    "community-command-0002",
                )

    def test_contribution_parent_is_forwarded_without_a_client_kind(self):
        database = FakeDatabase()
        parent_key = str(uuid4())

        CommunityCommandService(database).add_contribution(
            OWNER_KEY,
            POST_KEY,
            {
                "body": "A nested reply",
                "parent_key": parent_key,
                "attachment_keys": [],
            },
            "community-command-0002",
        )

        parameters = dict(database.calls[0][1])
        self.assertEqual(parameters["@ParentContributionKey"], parent_key)
        self.assertNotIn("@ContributionKind", parameters)

    def test_maximum_reply_depth_is_a_truthful_non_retryable_domain_failure(self):
        service = CommunityCommandService(
            FakeDatabase({"outcome": "depth_limit"})
        )
        payload = {
            "body": "A reply beyond the supported depth",
            "parent_key": str(uuid4()),
            "attachment_keys": [],
        }
        with self.assertRaisesRegex(
            CommunityValidationError,
            "Maximum reply depth reached.*top-level update",
        ):
            service.add_contribution(
                OWNER_KEY, POST_KEY, payload, "community-command-0002"
            )


class CommunityCursorTests(unittest.TestCase):
    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        app.config["PEERSLATE_COMMUNITY_SIGNING_KEY"] = "cursor-test-key"

    def tearDown(self):
        self.context.pop()

    def test_cursor_is_signed_content_free_and_finite(self):
        first = new_window_token()
        window = decode_window_token(first)
        self.assertEqual(window["remaining"], FEED_WINDOW_MAX)
        second = next_window_token(
            window,
            {"post_key": POST_KEY, "published_at_utc": datetime(2026, 7, 31, 12, 0)},
            12,
        )
        decoded = decode_window_token(second)
        self.assertEqual(decoded["remaining"], FEED_WINDOW_MAX - 12)
        self.assertEqual(decoded["after_time"], datetime(2026, 7, 31, 12, 0))
        self.assertNotIn(POST_KEY, second)
        with self.assertRaises(CommunityValidationError):
            decode_window_token(second + "changed")

    def test_feed_cursor_rejects_an_unpaired_keyset_boundary(self):
        window = decode_window_token(new_window_token())
        malformed = next_window_token(
            window,
            {"published_at_utc": datetime(2026, 7, 31, 12, 0)},
            1,
        )
        with self.assertRaises(CommunityValidationError):
            decode_window_token(malformed)

    def test_new_windows_preserve_same_second_subsecond_watermarks(self):
        precise_now = datetime(2026, 8, 1, 12, 0, 0, 654321)
        same_second_row = datetime(2026, 8, 1, 12, 0, 0, 654320)

        with patch(
            "services.community_cursor._utc_now",
            return_value=precise_now,
        ):
            feed_window = decode_window_token(new_window_token())
            conversation_window = decode_contribution_token(None, POST_KEY)
            shelf_window = decode_shelf_token(None, POST_KEY)

        for window in (feed_window, conversation_window, shelf_window):
            with self.subTest(window=window):
                self.assertEqual(window["as_of"], precise_now)
                self.assertEqual(window["as_of"].microsecond, 654321)
                self.assertLessEqual(same_second_row, window["as_of"])

    def test_same_second_keyset_boundaries_preserve_microseconds(self):
        boundary_time = datetime(2026, 8, 1, 12, 0, 0, 345678)
        contribution_key = str(uuid4())

        feed_window = decode_window_token(new_window_token())
        feed_token = next_window_token(
            feed_window,
            {"post_key": POST_KEY, "published_at_utc": boundary_time},
            1,
        )
        conversation_window = decode_contribution_token(None, POST_KEY)
        conversation_token = next_contribution_token(
            conversation_window,
            {
                "contribution_key": contribution_key,
                "created_at_utc": boundary_time,
            },
        )
        shelf_window = decode_shelf_token(None, POST_KEY)
        shelf_token = next_shelf_token(
            shelf_window,
            {
                "contribution_key": contribution_key,
                "created_at_utc": boundary_time,
            },
        )

        self.assertEqual(
            decode_window_token(feed_token)["after_time"], boundary_time
        )
        self.assertEqual(
            decode_contribution_token(conversation_token, POST_KEY)["before_time"],
            boundary_time,
        )
        self.assertEqual(
            decode_shelf_token(shelf_token, POST_KEY)["before_time"],
            boundary_time,
        )

    def test_conversation_cursor_is_post_bound_and_has_no_total_row_cap(self):
        first_window = decode_contribution_token(None, POST_KEY)
        contribution_key = str(uuid4())
        token = next_contribution_token(
            first_window,
            {
                "contribution_key": contribution_key,
                "created_at_utc": datetime(2026, 7, 31, 11, 0),
            },
        )
        decoded = decode_contribution_token(token, POST_KEY)
        self.assertEqual(decoded["before_key"], contribution_key)
        self.assertNotIn("remaining", decoded)
        with self.assertRaises(CommunityValidationError):
            decode_contribution_token(token, str(uuid4()))

    def test_shelf_cursor_is_post_and_projection_scope_bound(self):
        window = decode_shelf_token(
            None, POST_KEY, as_of=datetime(2026, 7, 31, 12, 0)
        )
        contribution_key = str(uuid4())
        token = next_shelf_token(
            window,
            {
                "contribution_key": contribution_key,
                "created_at_utc": datetime(2026, 7, 31, 11, 0),
            },
        )
        decoded = decode_shelf_token(token, POST_KEY)
        self.assertEqual(decoded["before_key"], contribution_key)
        self.assertEqual(decoded["as_of"], datetime(2026, 7, 31, 12, 0))
        with self.assertRaises(CommunityValidationError):
            decode_shelf_token(token, str(uuid4()))
        with self.assertRaises(CommunityValidationError):
            decode_contribution_token(token, POST_KEY)


class CommunityProjectionServiceTests(unittest.TestCase):
    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        app.config["PEERSLATE_COMMUNITY_SIGNING_KEY"] = "projection-test-key"

    def tearDown(self):
        self.context.pop()

    def test_conversation_label_is_plain_clamped_and_not_a_second_truth_store(self):
        label = _conversation_label(
            "  A   deliberately long Community conversation label "
            "with whitespace and more text than the projection permits.  "
        )
        self.assertLessEqual(len(label), 72)
        self.assertTrue(label.endswith("…"))
        self.assertNotIn("  ", label)
        self.assertEqual(_conversation_label(" \n\t "), "Community conversation")

    @staticmethod
    def post_row():
        return {
            "post_key": POST_KEY,
            "author_name": "Owner",
            "body": "Public post",
            "intent": "post",
            "response_posture": "open_feedback",
            "published_at_utc": datetime(2026, 7, 31, 12, 0),
            "revision_number": 1,
            "contribution_count": 5,
        }

    @staticmethod
    def contribution_row(key=None, *, state="active"):
        return {
            "contribution_key": key or str(uuid4()),
            "post_key": POST_KEY,
            "parent_contribution_key": None,
            "contribution_kind": "comment" if state == "active" else None,
            "author_name": "Owner" if state == "active" else None,
            "body": "Reply" if state == "active" else None,
            "created_at_utc": datetime(2026, 7, 31, 11, 0),
            "revision_number": 1,
            "depth": 0,
            "projection_state": state,
            "viewer_saved": 1,
            "child_reply_count": 0,
        }

    def test_feed_uses_selected_boundary_and_returns_lazy_shelf_cursor(self):
        preview_rows = [self.contribution_row() for _ in range(4)]
        feed_boundary_key = str(uuid4())
        shelf_boundary = {
            "post_key": POST_KEY,
            "selected_candidate_count": 5,
            "has_more": 1,
            "boundary_created_at_utc": preview_rows[-1]["created_at_utc"],
            "boundary_contribution_key": preview_rows[-1]["contribution_key"],
        }
        feed_boundary = {
            "selected_candidate_count": 12,
            "has_more": 1,
            "boundary_published_at_utc": datetime(2026, 7, 30, 12, 0),
            "boundary_post_key": feed_boundary_key,
        }

        class Database:
            def execute_procedure(self, procedure, parameters):
                self.call = (procedure, parameters)
                return [
                    [CommunityProjectionServiceTests.post_row()],
                    [],
                    preview_rows,
                    [],
                    [shelf_boundary],
                    [feed_boundary],
                ]

        database = Database()
        page = CommunityFeedService(database).feed_page(
            viewer_user_key=OWNER_KEY
        )
        self.assertEqual(len(page["items"][0]["preview_contributions"]), 4)
        self.assertIsNotNone(page["items"][0]["next_shelf_cursor"])
        self.assertIsNotNone(page["next_cursor"])
        self.assertFalse(page["caught_up"])
        feed_window = decode_window_token(page["next_cursor"])
        self.assertEqual(feed_window["after_key"], feed_boundary_key)
        self.assertEqual(feed_window["remaining"], FEED_WINDOW_MAX - 12)
        decoded = decode_shelf_token(
            page["items"][0]["next_shelf_cursor"], POST_KEY
        )
        self.assertEqual(
            decoded["before_key"], preview_rows[-1]["contribution_key"]
        )
        self.assertEqual(database.call[0], "usp_ListPublicCommunityFeed")

    def test_feed_advances_when_every_selected_candidate_is_revoked(self):
        boundary_key = str(uuid4())

        class Database:
            def execute_procedure(self, procedure, parameters):
                return [
                    [],
                    [],
                    [],
                    [],
                    [],
                    [{
                        "selected_candidate_count": 12,
                        "has_more": 1,
                        "boundary_published_at_utc": datetime(2026, 7, 30, 12, 0),
                        "boundary_post_key": boundary_key,
                    }],
                ]

        page = CommunityFeedService(Database()).feed_page()
        self.assertEqual(page["items"], [])
        self.assertIsNotNone(page["next_cursor"])
        self.assertFalse(page["caught_up"])

    def test_feed_exact_full_page_without_plus_one_is_caught_up(self):
        posts = [
            {**self.post_row(), "post_key": str(uuid4())}
            for _ in range(12)
        ]
        boundary = {
            "selected_candidate_count": 12,
            "has_more": 0,
            "boundary_published_at_utc": posts[-1]["published_at_utc"],
            "boundary_post_key": posts[-1]["post_key"],
        }

        class Database:
            def execute_procedure(self, procedure, parameters):
                return [posts, [], [], [], [], [boundary]]

        page = CommunityFeedService(Database()).feed_page()
        self.assertEqual(len(page["items"]), 12)
        self.assertIsNone(page["next_cursor"])
        self.assertTrue(page["caught_up"])

    def test_shelf_page_is_bounded_and_uses_content_free_boundary(self):
        item = self.contribution_row()
        boundary = {
            "selected_candidate_count": 21,
            "has_more": 1,
            "boundary_created_at_utc": item["created_at_utc"],
            "boundary_contribution_key": item["contribution_key"],
        }

        class Database:
            def execute_procedure(self, procedure, parameters):
                self.call = (procedure, parameters)
                return [[{"post_key": POST_KEY}], [item], [], [boundary]]

        database = Database()
        page = CommunityFeedService(database).shelf_page(
            POST_KEY, viewer_user_key=OWNER_KEY
        )
        self.assertEqual(database.call[0], "usp_ListPublicCommunityShelf")
        self.assertIn(("@PageSize", 20), database.call[1])
        self.assertEqual(page["items"][0]["viewer_saved"], True)
        self.assertIsNotNone(page["next_cursor"])
        self.assertEqual(
            decode_shelf_token(page["next_cursor"], POST_KEY)["before_key"],
            item["contribution_key"],
        )

    def test_conversation_boundary_pages_without_a_total_cap(self):
        boundary_key = str(uuid4())
        boundary = {
            "selected_candidate_count": 21,
            "has_more": 1,
            "boundary_created_at_utc": datetime(2026, 7, 31, 10, 0),
            "boundary_contribution_key": boundary_key,
        }

        class Database:
            def execute_procedure(self, procedure, parameters):
                self.call = (procedure, parameters)
                return [
                    [CommunityProjectionServiceTests.post_row()],
                    [],
                    [],
                    [],
                    [{"saved": 0, "response_intention": None}],
                    [boundary],
                ]

        database = Database()
        detail = CommunityFeedService(database).post_detail(POST_KEY)
        self.assertIn(("@PageSize", 20), database.call[1])
        self.assertTrue(
            any(name == "@AsOfUtc" for name, _ in database.call[1])
        )
        cursor = detail["next_contribution_cursor"]
        self.assertIsNotNone(cursor)
        self.assertEqual(
            decode_contribution_token(cursor, POST_KEY)["before_key"],
            boundary_key,
        )

    def test_selected_contribution_keeps_hidden_ancestor_body_free(self):
        selected = self.contribution_row()
        hidden = self.contribution_row(state="unavailable")

        class Database:
            def execute_procedure(self, procedure, parameters):
                self.call = (procedure, parameters)
                return [[selected], [], [hidden], []]

        database = Database()
        detail = CommunityFeedService(database).selected_contribution(
            POST_KEY, selected["contribution_key"], OWNER_KEY
        )
        self.assertEqual(
            database.call[0], "usp_GetPublicCommunityContribution"
        )
        self.assertEqual(detail["contribution"]["body"], "Reply")
        self.assertEqual(detail["ancestors"][0]["state"], "unavailable")
        self.assertEqual(detail["ancestors"][0]["body"], "")
        self.assertIsNone(detail["ancestors"][0]["author"]["display_name"])


class CommunityUploadValidationTests(unittest.TestCase):
    def test_safe_display_name_counts_utf16_units_and_preserves_real_extension(self):
        display_name = safe_display_name(
            ("🧭" * 100) + ".spoofed", content_type="image/png"
        )
        self.assertLessEqual(utf16_length(display_name), 180)
        self.assertTrue(display_name.endswith(".png"))
        self.assertNotIn("spoofed", display_name)
        with self.assertRaises(CommunityValidationError):
            safe_display_name("🧭" * 91)

    def test_database_sha256_decoder_accepts_binary_and_serialized_hex_only(self):
        digest = hashlib.sha256(b"pilot").digest()
        self.assertEqual(stored_sha256(digest), digest)
        self.assertEqual(stored_sha256(memoryview(digest)), digest)
        self.assertEqual(stored_sha256(digest.hex()), digest)
        with self.assertRaises(CommunityUnavailableError):
            stored_sha256("not-a-digest")

    def test_defender_scan_time_accepts_current_and_utc_suffixed_tags(self):
        class Blob:
            def __init__(self, tags):
                self.tags = tags

            def get_blob_tags(self):
                return self.tags

        class Container:
            def __init__(self, tags):
                self.tags = tags

            def get_blob_client(self, blob_name):
                return Blob(self.tags)

        for time_key in ("Malware scanning scan time", "Malware Scanning scan time UTC"):
            with self.subTest(time_key=time_key):
                service = CommunityMediaStorage()
                service._container_client = Container({
                    "Malware scanning scan result": "No threats found",
                    time_key: "2026-07-31T12:00:00Z",
                })
                result = service.scan_result(
                    "community/v1/aa/" + "e" * 32 + ".pdf"
                )
                self.assertEqual(result["result"], "clean")
                self.assertEqual(result["scan_time_utc"], datetime(2026, 7, 31, 12, 0))
    def test_pdf_signature_filename_and_limit_contract(self):
        upload = FileStorage(
            stream=BytesIO(b"%PDF-1.7\nminimal\n%%EOF\n"),
            filename="../safe-report.pdf",
            content_type="application/pdf",
        )
        item = validate_upload(upload)
        self.assertEqual(item.display_name, "safe-report.pdf")
        self.assertEqual(item.content_type, "application/pdf")

    def test_filename_drops_paths_spoofing_controls_and_mismatched_extension(self):
        upload = FileStorage(
            stream=BytesIO(b"%PDF-1.7\nminimal\n%%EOF\n"),
            filename="C:\\private\\quarterly\u202eexe.png",
            content_type="application/pdf",
        )
        item = validate_upload(upload)
        self.assertEqual(item.display_name, "quarterlyexe.pdf")

    def test_mismatched_declared_type_is_rejected(self):
        upload = FileStorage(
            stream=BytesIO(b"not a png"), filename="image.png", content_type="image/png"
        )
        with self.assertRaises(CommunityValidationError):
            validate_upload(upload)

    def test_failed_blob_upload_marks_reservation_failed_and_attempts_cleanup(self):
        media_key = str(uuid4())

        class UploadDatabase:
            def __init__(self):
                self.calls = []

            def first_result(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                return []

            def last_row(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                if procedure == "usp_ReservePublicCommunityMedia":
                    return {"outcome": "reserved", "media_key": media_key}
                if procedure == "usp_RejectPublicCommunityMedia":
                    return {"outcome": "failed", "media_state": "failed"}
                return {"outcome": "uploaded"}

        class FailedStorage:
            def __init__(self):
                self.deleted = []

            def upload(self, blob_name, data, content_type):
                raise CommunityMediaStorageError("storage_upload_failed")

            def delete(self, blob_name):
                self.deleted.append(blob_name)

        database = UploadDatabase()
        storage = FailedStorage()
        upload = FileStorage(
            stream=BytesIO(b"%PDF-1.7\nminimal\n%%EOF\n"),
            filename="pilot.pdf",
            content_type="application/pdf",
        )
        with self.assertRaises(CommunityUnavailableError):
            CommunityMediaService(database, storage).reserve_and_upload(OWNER_KEY, upload)
        self.assertEqual(len(storage.deleted), 1)
        self.assertTrue(
            any(call[0] == "usp_RejectPublicCommunityMedia" for call in database.calls)
        )

    def test_malware_scan_is_terminal_and_never_downloaded(self):
        media_key = str(uuid4())

        class ScanDatabase:
            def first_result(self, procedure, parameters):
                return []

            def first_row(self, procedure, parameters):
                return {
                    "media_key": media_key,
                    "media_state": "processing",
                    "original_blob_name": "community/v1/aa/" + "a" * 32 + ".pdf",
                    "safe_blob_name": "community/v1/aa/" + "a" * 32 + ".pdf",
                    "content_type": "application/pdf",
                    "display_name": "pilot.pdf",
                }

            def last_row(self, procedure, parameters):
                self.rejected = procedure
                return {"outcome": "rejected", "media_state": "rejected"}

        class MaliciousStorage:
            def scan_result(self, blob_name):
                return {"result": "malicious", "scan_time_utc": None}

            def download(self, blob_name):
                raise AssertionError("Malicious content must never be downloaded")

        database = ScanDatabase()
        result = CommunityMediaService(database, MaliciousStorage()).reconcile(OWNER_KEY, media_key)
        self.assertEqual(result["state"], "rejected")
        self.assertEqual(database.rejected, "usp_RejectPublicCommunityMedia")

    def test_upload_fails_closed_when_database_does_not_mark_blob_uploaded(self):
        media_key = str(uuid4())

        class MarkDatabase:
            def first_result(self, procedure, parameters):
                return []

            def last_row(self, procedure, parameters):
                if procedure == "usp_ReservePublicCommunityMedia":
                    return {"outcome": "reserved", "media_key": media_key}
                if procedure == "usp_MarkPublicCommunityMediaUploaded":
                    return {"outcome": "not_found"}
                return {"outcome": "failed", "media_state": "failed"}

        class MarkStorage:
            def __init__(self):
                self.deleted = []

            def upload(self, blob_name, data, content_type):
                return {"etag": "test"}

            def delete(self, blob_name):
                self.deleted.append(blob_name)

        storage = MarkStorage()
        upload = FileStorage(
            stream=BytesIO(b"%PDF-1.7\nminimal\n%%EOF\n"),
            filename="pilot.pdf",
            content_type="application/pdf",
        )
        with self.assertRaises(CommunityUnavailableError):
            CommunityMediaService(MarkDatabase(), storage).reserve_and_upload(
                OWNER_KEY, upload
            )
        self.assertEqual(len(storage.deleted), 1)

    @patch("services.community_media_service.normalize_photo")
    def test_existing_matching_derivative_allows_database_completion_retry(self, normalize):
        media_key = str(uuid4())
        original = b"validated-original-image"
        derivative = b"normalized-safe-image"
        normalize.return_value = SimpleNamespace(
            data=derivative,
            content_type="image/jpeg",
            byte_length=len(derivative),
            sha256_digest=hashlib.sha256(derivative).digest(),
            width=640,
            height=480,
        )

        class RetryDatabase:
            def first_row(self, procedure, parameters):
                return {
                    "media_key": media_key,
                    "media_state": "uploaded",
                    "original_blob_name": "community/v1/aa/" + "c" * 32 + ".jpg",
                    "safe_blob_name": "community/v1/aa/" + "c" * 32 + "-safe.jpg",
                    "content_type": "image/jpeg",
                    "display_name": "pilot.jpg",
                    "byte_length": len(original),
                    "sha256": hashlib.sha256(original).hexdigest(),
                }

            def last_row(self, procedure, parameters):
                self.completion = (procedure, parameters)
                return {
                    "outcome": "ready",
                    "media_key": media_key,
                    "media_state": "ready",
                    "display_name": "pilot.jpg",
                    "content_type": "image/jpeg",
                }

        class RetryStorage:
            def scan_result(self, blob_name):
                return {"result": "clean", "scan_time_utc": datetime(2026, 7, 31, 12, 0)}

            def download(self, blob_name):
                data = derivative if "-safe" in blob_name else original
                return {
                    "data": data,
                    "byte_length": len(data),
                    "content_type": "image/jpeg",
                }

            def upload(self, blob_name, data, content_type):
                raise CommunityMediaStorageError("storage_conflict")

        database = RetryDatabase()
        result = CommunityMediaService(database, RetryStorage()).reconcile(
            OWNER_KEY, media_key
        )
        self.assertEqual(result["state"], "ready")
        self.assertEqual(database.completion[0], "usp_CompletePublicCommunityMedia")
        self.assertIn(
            ("@SafeSha256", hashlib.sha256(derivative).digest()),
            database.completion[1],
        )

    @patch("services.community_media_service.normalize_photo")
    def test_identical_concurrent_reconcile_completion_is_accepted(self, normalize):
        media_key = str(uuid4())
        original = b"validated-original-image"
        derivative = b"normalized-safe-image"
        derivative_digest = hashlib.sha256(derivative).digest()
        normalize.return_value = SimpleNamespace(
            data=derivative,
            content_type="image/jpeg",
            byte_length=len(derivative),
            sha256_digest=derivative_digest,
            width=640,
            height=480,
        )

        class ConcurrentDatabase:
            def __init__(self):
                self.calls = []

            def first_row(self, procedure, parameters):
                return {
                    "media_key": media_key,
                    "media_state": "uploaded",
                    "original_blob_name": "community/v1/aa/" + "e" * 32 + ".jpg",
                    "safe_blob_name": "community/v1/aa/" + "e" * 32 + "-safe.jpg",
                    "content_type": "image/jpeg",
                    "display_name": "pilot.jpg",
                    "byte_length": len(original),
                    "sha256": hashlib.sha256(original).digest(),
                }

            def last_row(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                if procedure == "usp_CompletePublicCommunityMedia":
                    return {"outcome": "not_found"}
                if procedure == "usp_CompensatePublicCommunityMediaCompletion":
                    return {
                        "outcome": "ready",
                        "media_key": media_key,
                        "media_state": "ready",
                        "display_name": "pilot.jpg",
                        "content_type": "image/jpeg",
                    }
                raise AssertionError(f"Unexpected procedure: {procedure}")

            def first_result(self, procedure, parameters):
                raise AssertionError("An identical ready derivative must not be cleaned")

        class ConcurrentStorage:
            def scan_result(self, blob_name):
                return {"result": "clean", "scan_time_utc": datetime(2026, 7, 31, 12, 0)}

            def download(self, blob_name):
                return {
                    "data": original,
                    "byte_length": len(original),
                    "content_type": "image/jpeg",
                }

            def upload(self, blob_name, data, content_type):
                return {"etag": "concurrent"}

        database = ConcurrentDatabase()
        result = CommunityMediaService(database, ConcurrentStorage()).reconcile(
            OWNER_KEY, media_key
        )
        self.assertEqual(result["state"], "ready")
        self.assertEqual(
            [call[0] for call in database.calls],
            [
                "usp_CompletePublicCommunityMedia",
                "usp_CompensatePublicCommunityMediaCompletion",
            ],
        )

    @patch("services.community_media_service.normalize_photo")
    def test_remove_cleanup_race_reopens_and_deletes_late_derivative(self, normalize):
        media_key = str(uuid4())
        claim_token = str(uuid4())
        original_name = "community/v1/aa/" + "f" * 32 + ".jpg"
        safe_name = "community/v1/aa/" + "f" * 32 + "-safe.jpg"
        original = b"validated-original-image"
        derivative = b"normalized-safe-image"
        normalize.return_value = SimpleNamespace(
            data=derivative,
            content_type="image/jpeg",
            byte_length=len(derivative),
            sha256_digest=hashlib.sha256(derivative).digest(),
            width=640,
            height=480,
        )

        class RaceDatabase:
            def __init__(self):
                self.calls = []

            def first_row(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                return {
                    "media_key": media_key,
                    "media_state": "uploaded",
                    "original_blob_name": original_name,
                    "safe_blob_name": safe_name,
                    "content_type": "image/jpeg",
                    "display_name": "pilot.jpg",
                    "byte_length": len(original),
                    "sha256": hashlib.sha256(original).digest(),
                }

            def first_result(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                return [{
                    "media_key": media_key,
                    "cleanup_claim_token": claim_token,
                    "original_blob_name": original_name,
                    "safe_blob_name": safe_name,
                }]

            def last_row(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                if procedure == "usp_CompletePublicCommunityMedia":
                    return {"outcome": "not_found"}
                if procedure == "usp_CompensatePublicCommunityMediaCompletion":
                    return {"outcome": "cleanup_reopened", "media_state": "removed"}
                if procedure == "usp_CompletePublicCommunityMediaCleanup":
                    return {"outcome": "completed"}
                raise AssertionError(f"Unexpected procedure: {procedure}")

        class RaceStorage:
            def __init__(self):
                self.blobs = {original_name: original}

            def scan_result(self, blob_name):
                return {"result": "clean", "scan_time_utc": datetime(2026, 7, 31, 12, 0)}

            def download(self, blob_name):
                data = self.blobs[blob_name]
                return {
                    "data": data,
                    "byte_length": len(data),
                    "content_type": "image/jpeg",
                }

            def upload(self, blob_name, data, content_type):
                # Model cleanup completing after the original download but
                # before this in-flight reconcile writes its derivative.
                self.blobs.pop(original_name, None)
                self.blobs[blob_name] = data

            def delete(self, blob_name):
                self.blobs.pop(blob_name, None)

        database = RaceDatabase()
        storage = RaceStorage()
        with patch("services.community_media_service.LOGGER"):
            with self.assertRaises(CommunityUnavailableError):
                CommunityMediaService(database, storage).reconcile(OWNER_KEY, media_key)
        self.assertEqual(storage.blobs, {})
        procedures = [call[0] for call in database.calls]
        self.assertLess(
            procedures.index("usp_CompensatePublicCommunityMediaCompletion"),
            procedures.index("usp_ClaimPublicCommunityMediaCleanup"),
        )
        self.assertIn("usp_CompletePublicCommunityMediaCleanup", procedures)

    @patch("services.community_media_service.normalize_photo")
    def test_oversize_normalized_derivative_is_terminal_before_upload(self, normalize):
        media_key = str(uuid4())
        original = b"validated-original-image"
        derivative = b"x" * (MAX_ATTACHMENT_BYTES + 1)
        normalize.return_value = SimpleNamespace(
            data=derivative,
            content_type="image/png",
            byte_length=len(derivative),
            sha256_digest=hashlib.sha256(derivative).digest(),
            width=2400,
            height=2400,
        )

        class OversizeDatabase:
            def __init__(self):
                self.calls = []

            def first_row(self, procedure, parameters):
                return {
                    "media_key": media_key,
                    "media_state": "uploaded",
                    "original_blob_name": "community/v1/aa/" + "1" * 32 + ".png",
                    "safe_blob_name": "community/v1/aa/" + "1" * 32 + "-safe.png",
                    "content_type": "image/png",
                    "display_name": "pilot.png",
                    "byte_length": len(original),
                    "sha256": hashlib.sha256(original).digest(),
                }

            def last_row(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                if procedure == "usp_RejectPublicCommunityMedia":
                    return {"outcome": "failed", "media_state": "failed"}
                raise AssertionError(f"Unexpected procedure: {procedure}")

            def first_result(self, procedure, parameters):
                self.calls.append((procedure, parameters))
                return []

        class OversizeStorage:
            def scan_result(self, blob_name):
                return {"result": "clean", "scan_time_utc": datetime(2026, 7, 31, 12, 0)}

            def download(self, blob_name):
                return {
                    "data": original,
                    "byte_length": len(original),
                    "content_type": "image/png",
                }

            def upload(self, blob_name, data, content_type):
                raise AssertionError("An oversize derivative must not be uploaded")

        database = OversizeDatabase()
        with patch("services.community_media_service.LOGGER"):
            with self.assertRaises(CommunityValidationError):
                CommunityMediaService(database, OversizeStorage()).reconcile(
                    OWNER_KEY, media_key
                )
        procedures = [call[0] for call in database.calls]
        self.assertIn("usp_RejectPublicCommunityMedia", procedures)
        self.assertNotIn("usp_CompletePublicCommunityMedia", procedures)

    def test_public_delivery_rejects_blob_digest_drift(self):
        expected = b"expected-public-file"

        class PublicDatabase:
            def first_row(self, procedure, parameters):
                return {
                    "content_type": "application/pdf",
                    "display_name": "pilot.pdf",
                    "safe_blob_name": "community/v1/aa/" + "d" * 32 + ".pdf",
                    "original_blob_name": "community/v1/aa/" + "d" * 32 + ".pdf",
                    "safe_byte_length": len(expected),
                    "safe_sha256": hashlib.sha256(expected).hexdigest(),
                }

        class DriftedStorage:
            def download(self, blob_name):
                drifted = b"x" * len(expected)
                return {
                    "data": drifted,
                    "byte_length": len(drifted),
                    "content_type": "application/pdf",
                }

        with self.assertRaises(CommunityUnavailableError):
            CommunityMediaService(PublicDatabase(), DriftedStorage()).public_file(
                POST_KEY, preview=False
            )

    def test_cleanup_claim_deletes_each_blob_and_completes_only_after_success(self):
        media_key = str(uuid4())
        claim_token = str(uuid4())

        class CleanupDatabase:
            def __init__(self):
                self.completed = []

            def first_result(self, procedure, parameters):
                self.claim_call = (procedure, parameters)
                return [{
                    "media_key": media_key,
                    "cleanup_claim_token": claim_token,
                    "original_blob_name": "community/v1/aa/" + "a" * 32 + ".jpg",
                    "safe_blob_name": "community/v1/aa/" + "a" * 32 + "-safe.jpg",
                }]

            def last_row(self, procedure, parameters):
                self.completed.append((procedure, parameters))
                return {"outcome": "completed"}

        class CleanupStorage:
            def __init__(self):
                self.deleted = []

            def delete(self, blob_name):
                self.deleted.append(blob_name)

        database = CleanupDatabase()
        storage = CleanupStorage()
        with patch("services.community_media_service.LOGGER") as logger:
            self.assertEqual(
                CommunityMediaService(database, storage).sweep_best_effort(limit=4),
                1,
            )
        logger.info.assert_called_once()
        self.assertEqual(database.claim_call[0], "usp_ClaimPublicCommunityMediaCleanup")
        self.assertEqual(len(storage.deleted), 2)
        self.assertEqual(database.completed[0][0], "usp_CompletePublicCommunityMediaCleanup")

    def test_cleanup_storage_failure_leaves_sql_claim_uncompleted_for_retry(self):
        class CleanupDatabase:
            def __init__(self):
                self.completed = False

            def first_result(self, procedure, parameters):
                return [{
                    "media_key": str(uuid4()),
                    "cleanup_claim_token": str(uuid4()),
                    "original_blob_name": "community/v1/aa/" + "b" * 32 + ".pdf",
                    "safe_blob_name": "community/v1/aa/" + "b" * 32 + ".pdf",
                }]

            def last_row(self, procedure, parameters):
                self.completed = True
                return {"outcome": "completed"}

        class FailedCleanupStorage:
            def delete(self, blob_name):
                raise CommunityMediaStorageError("storage_delete_failed")

        database = CleanupDatabase()
        with patch("services.community_media_service.LOGGER") as logger:
            completed = CommunityMediaService(
                database, FailedCleanupStorage()
            ).sweep_best_effort(limit=4)
        self.assertEqual(completed, 0)
        self.assertFalse(database.completed)
        logger.warning.assert_called_once()

    def test_cleanup_can_target_a_recently_revoked_post_without_queue_starvation(self):
        class CleanupDatabase:
            def __init__(self):
                self.parameters = None

            def first_result(self, procedure, parameters):
                self.parameters = parameters
                return []

        database = CleanupDatabase()
        completed = CommunityMediaService(database, object()).sweep(
            limit=20, post_key=POST_KEY
        )
        self.assertEqual(completed, 0)
        self.assertIn(("@PostKey", POST_KEY), database.parameters)
        self.assertNotIn(("@MediaKey", POST_KEY), database.parameters)

    def test_cleanup_dependency_failure_is_logged_without_identifiers(self):
        class FailedCleanupDatabase:
            def first_result(self, procedure, parameters):
                raise DatabaseServiceError("dependency unavailable")

        media_key = str(uuid4())
        with patch("services.community_media_service.LOGGER") as logger:
            completed = CommunityMediaService(
                FailedCleanupDatabase(), object()
            ).sweep_best_effort(limit=1, media_key=media_key)
        self.assertEqual(completed, 0)
        logger.error.assert_called_once()
        self.assertNotIn(media_key, repr(logger.error.call_args))

    @patch("services.community_media_service.time.monotonic")
    def test_always_on_maintenance_runs_one_bounded_hourly_batch(self, monotonic):
        class CleanupService:
            def __init__(self):
                self.calls = []

            def sweep_best_effort(self, limit):
                self.calls.append(limit)
                return 2

        service = CleanupService()
        maintenance = CommunityMediaMaintenance(service, interval_seconds=3600)
        monotonic.side_effect = [100.0, 100.0, 200.0, 3701.0, 3701.0]
        self.assertEqual(maintenance.maybe_run(), 2)
        self.assertEqual(maintenance.maybe_run(), 0)
        self.assertEqual(maintenance.maybe_run(), 2)
        self.assertEqual(service.calls, [20, 20])


class CommunityRouteAndApiTests(unittest.TestCase):
    def setUp(self):
        self.previous = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_OWNER_USER_KEYS=OWNER_KEY,
            PEERSLATE_OWNER_EMAILS="",
            PEERSLATE_COMMUNITY_SIGNING_KEY="community-test-signing-key",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous)

    def test_signed_out_page_is_public_read_only_and_noindex(self):
        response = self.client.get("/the-slate")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow")
        self.assertIn("Anyone can read public posts", body)
        self.assertNotIn("data-publish", body)
        self.assertIn("data-conversation", body)
        self.assertNotIn("data-reply-form", body)
        self.assertNotIn("Sample data", body)

    def test_real_feed_flag_retires_legacy_fixture_json_endpoint(self):
        response = self.client.get("/api/slate-feed")
        self.assertEqual(response.status_code, 404)

    def test_owner_page_has_real_composer_and_local_draft_truth(self):
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        body = self.client.get("/the-slate").get_data(as_text=True)
        self.assertIn("data-composer-form", body)
        self.assertIn("data-reply-attachment-input", body)
        self.assertIn("Draft · only you can see this", body)
        self.assertIn("Choose audience", body)
        self.assertIn("Published content is not sent to a generative model", body)
        self.assertIn("Optional Voice dictation sends a transient private recording to Speech", body)

    def test_boolean_revision_precondition_is_rejected_before_database_access(self):
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        response = self.client.delete(
            f"/api/v1/community/posts/{POST_KEY}",
            json={"expected_revision": True},
            headers={"X-PeerSlate-Request": "same-origin"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("revision precondition", response.get_json()["message"])

    def test_owner_draft_namespace_is_opaque_isolated_and_never_exposes_identity(self):
        app.config["PEERSLATE_OWNER_USER_KEYS"] = f"{OWNER_KEY},{OTHER_KEY}"
        namespaces = []
        for user_key in (OWNER_KEY, OTHER_KEY):
            app.config["PEERSLATE_DEV_USER_KEY"] = user_key
            body = self.client.get("/the-slate").get_data(as_text=True)
            match = re.search(r'data-draft-namespace="([0-9a-f]{64})"', body)
            self.assertIsNotNone(match)
            self.assertNotIn(user_key, body)
            namespaces.append(match.group(1))
        self.assertNotEqual(namespaces[0], namespaces[1])

    def test_community_datetimes_are_explicit_utc(self):
        self.assertEqual(
            _utc_json(datetime(2026, 7, 31, 12, 0)),
            "2026-07-31T12:00:00Z",
        )
        self.assertEqual(
            _utc_json("2026-07-31T08:00:00-04:00"),
            "2026-07-31T12:00:00Z",
        )

    @patch("app.community_media_maintenance.maybe_run")
    def test_health_check_never_runs_media_maintenance(self, maybe_run):
        app.config["TESTING"] = False
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        maybe_run.assert_not_called()

    @patch("community_api.community_feed_service.feed_page")
    def test_signed_out_public_feed_read_succeeds(self, feed_page):
        feed_page.return_value = {"items": [], "next_cursor": None, "caught_up": True}
        response = self.client.get("/api/v1/community/feed?limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["caught_up"])
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        feed_page.assert_called_once_with(
            None, page_size=12, viewer_user_key=None
        )

    @patch("community_api.community_feed_service.shelf_page")
    def test_signed_out_shelf_page_is_public_and_post_bound(self, shelf_page):
        shelf_page.return_value = {
            "items": [],
            "next_cursor": None,
            "caught_up": True,
        }
        response = self.client.get(
            f"/api/v1/community/posts/{POST_KEY}/shelf?cursor=signed-cursor"
        )
        self.assertEqual(response.status_code, 200)
        shelf_page.assert_called_once_with(
            POST_KEY, "signed-cursor", viewer_user_key=None
        )

    @patch("community_api.community_feed_service.selected_contribution")
    def test_selected_contribution_api_binds_post_and_viewer(self, selected):
        contribution_key = str(uuid4())
        selected.return_value = {
            "contribution": {"key": contribution_key},
            "ancestors": [],
        }
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        response = self.client.get(
            f"/api/v1/community/posts/{POST_KEY}/contributions/{contribution_key}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["contribution"]["key"], contribution_key)
        selected.assert_called_once_with(
            POST_KEY, contribution_key, viewer_user_key=OWNER_KEY
        )

    @patch("community_api.community_command_service.publish_post")
    def test_signed_out_and_non_owner_writes_are_denied(self, publish):
        payload = {"body": "hello"}
        headers = {"X-PeerSlate-Request": "same-origin"}
        response = self.client.post("/api/v1/community/posts", json=payload, headers=headers)
        self.assertEqual(response.status_code, 401)
        app.config["PEERSLATE_DEV_USER_KEY"] = OTHER_KEY
        response = self.client.post("/api/v1/community/posts", json=payload, headers=headers)
        self.assertEqual(response.status_code, 403)
        publish.assert_not_called()

    @patch("community_api.community_command_service.publish_post")
    def test_owner_write_uses_server_identity_and_same_origin_header(self, publish):
        publish.return_value = {"outcome": "created", "post_key": POST_KEY}
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        payload = {
            "body": "Published by the server-resolved owner",
            "intent": "post",
            "response_posture": "open_feedback",
            "audience": "public",
            "attachment_keys": [],
        }
        denied = self.client.post("/api/v1/community/posts", json=payload)
        self.assertEqual(denied.status_code, 403)
        accepted = self.client.post(
            "/api/v1/community/posts",
            json=payload,
            headers={
                "X-PeerSlate-Request": "same-origin",
                "Idempotency-Key": "community-command-0001",
            },
        )
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(publish.call_args.args[0], OWNER_KEY)

    def test_cross_origin_write_is_denied_before_command(self):
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        response = self.client.post(
            "/api/v1/community/posts",
            json={},
            headers={"X-PeerSlate-Request": "same-origin", "Origin": "https://attacker.example"},
        )
        self.assertEqual(response.status_code, 403)

    @patch("community_api.community_command_service.add_contribution")
    def test_reply_depth_validation_response_is_explicitly_non_retryable(
        self, add_contribution
    ):
        add_contribution.side_effect = CommunityValidationError(
            "Maximum reply depth reached. Add a top-level update instead."
        )
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        response = self.client.post(
            f"/api/v1/community/posts/{POST_KEY}/contributions",
            json={
                "body": "Too deep",
                "parent_key": str(uuid4()),
                "attachment_keys": [],
            },
            headers={
                "X-PeerSlate-Request": "same-origin",
                "Idempotency-Key": "community-command-0002",
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.get_json()["retryable"])
        self.assertIn("Maximum reply depth reached", response.get_json()["message"])

    @patch("community_api.community_media_service.reconcile")
    def test_attachment_status_is_protected_post_not_mutating_get(self, reconcile):
        reconcile.return_value = {"key": POST_KEY, "state": "ready"}
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        self.assertEqual(
            self.client.get(f"/api/v1/community/attachments/{POST_KEY}/status").status_code,
            405,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/community/attachments/{POST_KEY}/status", json={}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/community/attachments/{POST_KEY}/status",
                json={},
                headers={
                    "X-PeerSlate-Request": "same-origin",
                    "Origin": "https://attacker.example",
                },
            ).status_code,
            403,
        )
        app.config["PEERSLATE_DEV_USER_KEY"] = OTHER_KEY
        self.assertEqual(
            self.client.post(
                f"/api/v1/community/attachments/{POST_KEY}/status",
                json={},
                headers={"X-PeerSlate-Request": "same-origin"},
            ).status_code,
            403,
        )
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        accepted = self.client.post(
            f"/api/v1/community/attachments/{POST_KEY}/status",
            json={},
            headers={"X-PeerSlate-Request": "same-origin"},
        )
        self.assertEqual(accepted.status_code, 200)
        reconcile.assert_called_once_with(OWNER_KEY, POST_KEY)

    @patch("community_api.community_media_service.sweep_best_effort")
    @patch("community_api.community_command_service.delete_post")
    def test_post_delete_triggers_retryable_blob_cleanup(self, delete_post, sweep):
        delete_post.return_value = {"outcome": "deleted"}
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        response = self.client.delete(
            f"/api/v1/community/posts/{POST_KEY}",
            json={"expected_revision": 1},
            headers={"X-PeerSlate-Request": "same-origin"},
        )
        self.assertEqual(response.status_code, 200)
        sweep.assert_called_once_with(limit=20, post_key=POST_KEY)

    @patch("community_api.community_media_service.reserve_and_upload")
    def test_attachment_limit_override_does_not_raise_global_request_limit(self, upload):
        upload.return_value = {
            "key": str(uuid4()),
            "state": "processing",
            "display_name": "large.pdf",
        }
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        self.assertEqual(app.config["MAX_CONTENT_LENGTH"], 2 * 1024 * 1024)
        response = self.client.post(
            "/api/v1/community/attachments",
            data={"file": (BytesIO(b"x" * (3 * 1024 * 1024)), "large.pdf")},
            headers={"X-PeerSlate-Request": "same-origin"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 202)
        upload.assert_called_once()

    def test_flag_off_neutralizes_new_routes(self):
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = False
        self.assertEqual(self.client.get("/api/v1/community/feed").status_code, 404)
        self.assertEqual(self.client.get(f"/the-slate/posts/{POST_KEY}").status_code, 404)
        self.assertEqual(
            self.client.get(
                f"/the-slate/posts/{POST_KEY}/contributions/{uuid4()}"
            ).status_code,
            404,
        )

    def test_contribution_deep_link_is_validated_and_bootstraps_selected_reply(self):
        contribution_key = str(uuid4())
        response = self.client.get(
            f"/the-slate/posts/{POST_KEY}/contributions/{contribution_key}"
        )
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'data-post-key="{POST_KEY}"', body)
        self.assertIn(f'data-contribution-key="{contribution_key}"', body)
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow")
        for route in (
            "/the-slate/posts/not-a-key/contributions/not-a-key",
            f"/the-slate/posts/{POST_KEY}/contributions/not-a-key",
        ):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 404)

    def test_pilot_html_routes_are_private_no_store(self):
        for route in (
            f"/the-slate/posts/{POST_KEY}",
            f"/the-slate/posts/{POST_KEY}/contributions/{uuid4()}",
            "/the-slate/public-pilot",
        ):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    @patch("community_api.community_media_service.public_file")
    def test_full_feed_preview_burst_has_bounded_headroom(self, public_file):
        public_file.return_value = {
            "data": b"image",
            "content_type": "image/png",
            "display_name": "preview.png",
            "inline": True,
        }
        remote = {"REMOTE_ADDR": "198.51.100.96"}
        statuses = [
            self.client.get(
                f"/api/v1/community/attachments/{uuid4()}/preview",
                environ_overrides=remote,
            ).status_code
            for _ in range(120)
        ]
        self.assertEqual(set(statuses), {200})
        overflow = self.client.get(
            f"/api/v1/community/attachments/{uuid4()}/preview",
            environ_overrides=remote,
        )
        self.assertEqual(overflow.status_code, 429)
        self.assertEqual(public_file.call_count, 120)

    @patch("community_api.community_media_service.public_file")
    def test_unicode_attachment_disposition_has_ascii_and_utf8_filenames(self, public_file):
        media_key = str(uuid4())
        public_file.return_value = {
            "data": b"%PDF-1.7\n%%EOF",
            "content_type": "application/pdf",
            "display_name": "設計 résumé.pdf",
            "inline": False,
        }
        response = self.client.get(
            f"/api/v1/community/attachments/{media_key}/download"
        )
        self.assertEqual(response.status_code, 200)
        disposition = response.headers["Content-Disposition"]
        self.assertIn("filename=resume.pdf", disposition)
        self.assertIn("filename*=UTF-8''", disposition)
        self.assertIn("%E8%A8%AD%E8%A8%88%20r%C3%A9sum%C3%A9.pdf", disposition)


class CommunityFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "templates" / "community_feed.html").read_text(encoding="utf-8")
        cls.script = (ROOT / "static" / "js" / "community-v1.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "static" / "css" / "community-v1.css").read_text(encoding="utf-8")
        cls.policy = (ROOT / "templates" / "community_pilot_policy.html").read_text(encoding="utf-8")
        cls.app_source = (ROOT / "app.py").read_text(encoding="utf-8")
        cls.preview = (ROOT / "scripts" / "preview_community_primary_feed.py").read_text(encoding="utf-8")

    def test_primary_feed_uses_the_owner_corrected_desktop_rails_and_wider_center_stage(self):
        self.assertLess(
            self.template.index('class="cv1-main cv1-primary-feed-stage"'),
            self.template.index('class="cv1-rail cv1-rail--left"'),
        )
        self.assertIn('grid-template-areas: "left main right"', self.styles)
        self.assertIn('grid-template-columns: 234px minmax(0, 748px) 234px', self.styles)
        self.assertIn('.cv1-main { grid-area: main; width: 100%; max-width: 748px;', self.styles)
        self.assertIn('.cv1-rail { display: grid;', self.styles)
        self.assertIn('@media (max-width: 1288px)', self.styles)
        self.assertIn('.cv1-rail { display: none; }', self.styles)
        self.assertIn('.cv1-mobile-tools { display: grid;', self.styles)
        self.assertIn('.cv1-mobile-tool-control > span:nth-child(2) { flex: 0 0 auto; white-space: nowrap;', self.styles)
        self.assertIn('font-size: .84rem', self.styles)

    def test_owner_composer_bar_replaces_the_floating_new_post_button(self):
        self.assertIn('class="cv1-quick-compose"', self.template)
        self.assertIn('What’s on your mind, {{ (community_display_name or \'Pete\').split()[0] }}?', self.template)
        self.assertIn('class="cv1-quick-compose-action cv1-quick-compose-action--media"', self.template)
        self.assertIn('class="cv1-quick-compose-action cv1-quick-compose-action--voice"', self.template)
        self.assertIn('data-top-voice', self.template)
        self.assertNotIn('class="cv1-primary cv1-new-post"', self.template)
        self.assertIn('.cv1-quick-compose { display: grid;', self.styles)
        self.assertIn('grid-template-columns: 42px minmax(0, 1fr) 40px 40px', self.styles)
        self.assertIn("openComposer('post', null, false);", self.script)
        self.assertIn("composerVoiceController.start();", self.script)
        self.assertIn('.cv1-quick-compose-action--media { display: none; }', self.styles)

    def test_browser_draft_and_retry_keys_are_private_and_content_free(self):
        self.assertIn("legacyDraftKey + ':' + app.dataset.draftNamespace", self.script)
        self.assertIn("localStorage.removeItem(legacyDraftKey)", self.script)
        self.assertIn(
            "replyCommandStorageKey = draftKey ? draftKey + ':pending-reply-command' : null",
            self.script,
        )
        self.assertIn("localStorage.getItem(commandStorageKey)", self.script)
        self.assertIn(
            "stableCommandKey(payload, 'reply', state.currentPost.key + ':' + (state.replyParentKey || 'top-level'))",
            self.script,
        )
        self.assertIn("{key: state[keyField], signature: signature}", self.script)
        self.assertNotIn("JSON.stringify({key: state[keyField], payload:", self.script)
        self.assertEqual(
            self.script.count("localStorage.removeItem(replyCommandStorageKey)"),
            1,
        )
        self.assertIn("function formField(form, name)", self.script)
        self.assertIn("form.elements.namedItem(name)", self.script)

    def test_maximum_depth_reply_state_is_visible_guarded_and_non_retryable(self):
        self.assertIn("var maximumReplyDepth = 8", self.script)
        self.assertIn("limit.dataset.replyDepthLimit = ''", self.script)
        self.assertIn(
            "Maximum reply depth reached. Add a top-level update instead.",
            self.script,
        )
        self.assertIn(".cv1-reply-depth-limit", self.styles)
        self.assertIn(
            ".cv1-selected-contribution__actions .cv1-reply-depth-limit",
            self.styles,
        )
        self.assertIn("failure.retryable = payload.retryable !== false", self.script)
        self.assertIn("replyForm.hidden = false;", self.script)
        self.assertNotIn("replyForm.hidden = Boolean(selected)", self.script)
        reply_action = self.script.index(
            "if (action.dataset.action === 'reply-to')"
        )
        target = self.script.index("targetReply(replyTarget);", reply_action)
        self.assertGreater(target, reply_action)
        self.assertIn("state.replyParentKey = item.key", self.script)

    def test_shelf_selected_and_accessibility_runtime_contracts_are_present(self):
        for contract in (
            "/shelf?cursor=",
            "selectedContribution",
            "View all Replies & Updates",
            "contributionTombstone",
        ):
            self.assertIn(contract, self.script)
        self.assertIn("@media (forced-colors: active)", self.styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.styles)
        self.assertIn("width: 100vw; max-width: none; height: 100dvh", self.styles)

    def test_revised_mobile_state_and_selected_detail_contracts_are_present(self):
        self.assertIn("data-catchup-dialog", self.template)
        self.assertIn("data-activity-dialog", self.template)
        self.assertLess(
            self.template.index("data-catchup-dialog"),
            self.template.index("data-activity-dialog"),
        )
        self.assertIn("See all activity", self.template)
        self.assertIn("data-spark-prompt", self.template)
        self.assertIn(".cv1-mobile-activity { display: none; }", self.styles)
        self.assertIn("viewport-fit=cover", self.script)
        self.assertIn("width=device-width, initial-scale=1", self.script)
        self.assertIn("env(safe-area-inset-bottom)", self.styles)
        self.assertNotIn("message-unavailable", self.script)
        self.assertNotIn("Message", self.template)
        self.assertIn("Loading reply…", self.script)
        self.assertIn("conversationBody.setAttribute('aria-busy', 'true')", self.script)
        self.assertIn("communitySheet", self.script)
        self.assertIn("history.pushState(nextState", self.script)

    def test_media_actions_motion_and_deep_links_match_the_locked_shapes(self):
        for contract in (
            "cv1-image-gallery",
            "Copy link",
            "Show more",
            "contributionOwnerOverflow",
            "motionBehavior()",
            "'/contributions/' + encodeURIComponent",
        ):
            self.assertIn(contract, self.script)
        self.assertIn("min-height: 44px", self.styles)
        self.assertIn("--cv1-blue: #8db8ff", self.styles)
        self.assertIn("--cv1-danger: #ff9c9c", self.styles)

    def test_owner_action_menus_close_and_conversation_header_actions_are_live(self):
        self.assertIn("function closeContributionMenus(except)", self.script)
        self.assertIn("conversation.addEventListener('keydown', handlePostMenuKeydown)", self.script)
        self.assertIn("if (!event.target.closest('.cv1-contribution-owner-controls')) closeContributionMenus()", self.script)
        self.assertIn("event.target.closest('details.cv1-contribution-owner-controls[open]')", self.script)
        self.assertIn("conversationHeaderActions._communityPost || state.currentPost", self.script)
        self.assertIn("if (action.dataset.action === 'menu')", self.script)

    def test_feed_images_use_the_current_feed_full_width_landscape_treatment(self):
        self.assertIn("link.classList.add('cv1-attachment--image')", self.script)
        self.assertIn(".cv1-attachment--image { width: 100%; max-width: none; aspect-ratio: 16 / 7;", self.styles)
        self.assertIn("[data-primary-feed-card] .cv1-attachment--image { aspect-ratio: 16 / 8.5;", self.styles)
        self.assertIn(".cv1-image-gallery { width: 100%;", self.styles)

    def test_primary_card_uses_locked_closed_actions_without_duplicate_open_or_save(self):
        card_start = self.script.index("function cardNode(post, compact)")
        primary_start = self.script.index("if (!compact) {", card_start)
        primary_end = self.script.index("    var conversationCopy", primary_start)
        primary = self.script[primary_start:primary_end]

        self.assertIn("primaryPostCopy(post.body)", primary)
        self.assertIn("var lead = paragraphs.shift() || 'Community post'", self.script)
        self.assertIn("var leadCharacters = Array.from(lead)", self.script)
        self.assertIn("if (leadCharacters.length > 140)", self.script)
        self.assertIn("title = leadCharacters.slice(0, boundary).join('').trim()", self.script)
        self.assertIn("titleLink.dataset.action = 'conversation'", primary)
        self.assertIn("attachmentsNode(post.attachments, {", primary)
        self.assertIn("comment.dataset.action = 'conversation'", primary)
        self.assertIn("'Open conversation: ' + copy.title", primary)
        self.assertIn("primaryRespondControl(post)", primary)
        self.assertIn("primaryCommentComposer(post)", primary)
        self.assertNotIn("Open post", primary)
        self.assertNotIn("saveLabel", primary)
        self.assertIn("renderConversationShelf(post)", primary)
        self.assertLess(
            primary.index("primaryCommentComposer(post)"),
            primary.index("renderConversationShelf(post)"),
        )
        self.assertIn("selected ? 'Respond: ' + selected.label : 'Respond'", self.script)
        self.assertIn("cv1-respond-symbol", self.script)
        self.assertIn(".cv1-card-actions--primary .cv1-icon-action", self.styles)
        self.assertIn("min-width: 36px; width: 36px; height: 34px; min-height: 34px", self.styles)
        self.assertIn(".cv1-primary-feed-stage > .cv1-toolbar :is(button, a, input):focus-visible", self.styles)
        self.assertIn("[data-primary-feed-card] :is(button, a):focus-visible { outline-width: 2px; outline-offset: 2px; }", self.styles)
        self.assertIn("height: 44px", self.styles)

    def test_primary_response_uses_a_small_actual_emoji_hover_rail(self):
        for emoji in ("🎉", "❤️", "🤝", "🤔", "🙋"):
            self.assertIn(emoji, self.script)
        self.assertIn("wrapper.dataset.primaryResponseControl", self.script)
        respond_start = self.script.index("function primaryRespondControl")
        respond_end = self.script.index("function primaryCommentIcon", respond_start)
        self.assertNotIn("aria-haspopup", self.script[respond_start:respond_end])
        self.assertIn("wrapper.addEventListener('mouseenter'", self.script)
        self.assertIn("wrapper.addEventListener('focusin'", self.script)
        self.assertIn("event.key !== 'Escape'", self.script)
        self.assertIn("performPrimaryResponse", self.script)
        self.assertIn("removing ? 'DELETE' : 'PUT'", self.script)
        self.assertIn("Choose a private response", self.script)
        close_start = self.script.index("function closePrimaryResponsePicker")
        close_end = self.script.index("function schedulePrimaryResponseClose", close_start)
        close_picker = self.script[close_start:close_end]
        self.assertLess(
            close_picker.index("if (trigger && restoreFocus) trigger.focus()"),
            close_picker.index("if (picker) picker.hidden = true"),
        )
        self.assertIn(".cv1-response-picker { position: absolute;", self.styles)
        self.assertIn("min-width: 36px; width: 36px; height: 36px; min-height: 36px", self.styles)
        self.assertIn("font-size: 22px", self.styles)
        self.assertNotIn("setResponse(post, card);\n    }\n    if (action === 'save')", self.script)

    def test_primary_post_has_small_overflow_dots_and_compact_comment_entry(self):
        self.assertIn("menuButton.appendChild(el('span', 'cv1-overflow-dots', '•••'))", self.script)
        self.assertIn("font-size: .72rem", self.styles)
        self.assertIn("function primaryCommentComposer(post)", self.script)
        self.assertIn("input.rows = 1", self.script)
        self.assertIn("input.maxLength = 2000", self.script)
        self.assertIn("input.placeholder = 'Write a comment…'", self.script)
        self.assertIn("Math.min(input.scrollHeight, 112)", self.script)
        self.assertIn("primaryCommentStorageKey(post.key, 'draft')", self.script)
        self.assertIn("parent_key: null, attachment_keys: []", self.script)
        self.assertIn("primaryCommentCommandKey(form, post.key, payload)", self.script)
        self.assertIn("Start Voice comment recording", self.script)
        self.assertIn("new CommunityVoiceController({", self.script)
        self.assertIn("/api/v1/community/voice/transcriptions", self.script)
        self.assertIn("composer_context', this.context", self.script)
        self.assertIn("form.dataset.postKey = post.key", self.script)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 30px 30px", self.styles)
        self.assertIn("border-radius: 20px", self.styles)
        self.assertIn("width: 30px; height: 30px; min-height: 30px", self.styles)
        self.assertIn('font: 700 1.125rem/24px "Newsreader", serif', self.styles)
        self.assertIn("font-size: .875rem; line-height: 20px", self.styles)
        self.assertIn("font-size: .82rem; font-weight: 500; line-height: 18px", self.styles)
        self.assertIn("font-size: .75rem; line-height: 16px", self.styles)

    def test_local_primary_preview_is_visibly_truthful_and_service_isolated(self):
        self.assertIn("Pete-only sample content", self.template)
        self.assertIn("Sample content is not persisted or published", self.template)
        self.assertIn("community_preview=True", self.preview)
        self.assertIn("app.config.update(TESTING=True)", self.preview)
        self.assertIn("Only the primary Feed and its in-memory response/comment actions are available", self.preview)
        self.assertIn('request.method == "PUT"', self.preview)
        self.assertIn('request.method == "DELETE"', self.preview)
        self.assertIn('request.method == "POST"', self.preview)
        self.assertIn("fixture_response = intention", self.preview)
        self.assertIn("fixture_comment_count += 1", self.preview)
        self.assertIn('if request.path.startswith("/static/")', self.preview)
        self.assertIn("This local review serves only the closed primary Community Feed", self.preview)
        self.assertIn("status=404", self.preview)
        self.assertIn("An illustrative team reviewing a corkboard workflow", self.preview)
        self.assertIn('"byte_length": 2_320_474', self.preview)
        self.assertIn("def fixture_contributions(published_at)", self.preview)
        self.assertIn("vendor-handoff-decision-guide.xlsx", self.preview)
        self.assertIn('"kind": "author_update"', self.preview)
        self.assertNotIn("DatabaseService", self.preview)
        self.assertNotIn("from services.", self.preview)

    def test_motion_cards_have_locked_density_attachment_cues_and_owner_approved_color(self):
        self.assertIn("grid-auto-columns: 145px", self.styles)
        self.assertIn("grid-auto-columns: 96px", self.styles)
        self.assertIn("gap: 12px", self.styles)
        self.assertIn("linear-gradient(145deg, #f8fafd, #edf2f8)", self.styles)
        self.assertIn("background: #edf3ff", self.styles)
        self.assertIn("linear-gradient(145deg, #172c4b, #10213a)", self.styles)
        self.assertIn("fileLabel = 'XLSX'", self.script)
        self.assertIn("card.dataset.contributionKind", self.script)
        shelf_start = self.script.index("function appendShelfItems")
        shelf_end = self.script.index("function updateShelfControls", shelf_start)
        self.assertNotIn("Author update", self.script[shelf_start:shelf_end])
        self.assertIn("font-size: .82rem", self.styles)
        self.assertIn("[data-conversation-shelf-card] > strong", self.styles)

    def test_xlsx_is_selectable_but_described_as_a_public_download(self):
        self.assertEqual(self.template.count(XLSX_CONTENT_TYPE), 2)
        self.assertEqual(self.template.count(".xlsx"), 2)
        self.assertIn("macro-free XLSX", self.policy)
        self.assertIn("document properties become public", self.policy)

    def test_shelf_view_all_is_compact_but_keeps_explicit_accessible_name(self):
        self.assertIn("document.createTextNode('View all')", self.script)
        self.assertIn("viewAll.setAttribute('aria-label', 'View all Replies & Updates')", self.script)
        self.assertNotIn("cv1-view-all-long", self.script)

    def test_composer_matches_desktop_pairing_and_mobile_posture_order(self):
        self.assertLess(
            self.template.index('class="cv1-audience-field"'),
            self.template.index('class="cv1-response-posture-field"'),
        )
        self.assertIn('.cv1-composer .cv1-attachment-list { order: 4; }', self.styles)
        self.assertIn('.cv1-composer .cv1-response-posture-field { order: 5;', self.styles)
        self.assertIn(
            '.cv1-composer .cv1-dialog-head [data-close-composer] { grid-column: 1;',
            self.styles,
        )
        self.assertNotIn('class="cv1-intent-fieldset"', self.template)

    def test_owner_pilot_reply_composer_sends_no_client_contribution_kind(self):
        self.assertNotIn('name="kind"', self.template)
        self.assertNotIn('<select name="kind"', self.template)
        self.assertNotIn("formField(form, 'kind')", self.script)
        self.assertIn(
            "var payload = {body: body, parent_key: state.replyParentKey",
            self.script,
        )

    def test_locked_search_and_selected_reply_responsive_compositions_are_present(self):
        self.assertIn('class="cv1-mobile-search-head"', self.template)
        self.assertIn("document.body.classList.toggle('community-search-active'", self.script)
        self.assertIn("app.classList.add('cv1-search-error')", self.script)
        self.assertIn(
            "appBackToFeed && !feedList.contains(appBackToFeed)",
            self.script,
        )
        self.assertIn(
            'body.community-search-active .cv1-search-terminal { min-height:',
            self.styles,
        )
        self.assertIn(
            '.cv1-selected-contribution__destinations { display: none;',
            self.styles,
        )
        self.assertIn(
            '.cv1-selected-contribution__destinations { display: flex; }',
            self.styles,
        )
        self.assertIn('View all Replies & Updates', self.script)
        self.assertIn('--cv1-scrim: rgba(2, 8, 18, .78)', self.styles)

    def test_bounded_read_rates_cover_complete_feed_projection(self):
        for endpoint, limit in (
            ("community_api.feed", "120 per minute"),
            ("community_api.contribution_shelf", "120 per minute"),
            ("community_api.selected_contribution", "120 per minute"),
            ("community_api.preview_attachment", "120 per minute"),
        ):
            self.assertIn(f"'{endpoint}': '{limit}'", self.app_source)

    def test_community_signing_key_is_dedicated_and_flag_enablement_fails_closed(self):
        self.assertIn(
            "PEERSLATE_COMMUNITY_SIGNING_KEY=os.environ.get(",
            self.app_source,
        )
        self.assertIn(
            "PEERSLATE_COMMUNITY_SIGNING_KEY is required when the Community",
            self.app_source,
        )
        self.assertNotIn("peerslate-community-feed-v1:' + ANTHROPIC_API_KEY", self.app_source)

    def test_every_owner_mutation_has_an_explicit_route_limit(self):
        for endpoint in (
            "publish_post", "edit_post", "delete_post",
            "add_contribution", "edit_contribution", "delete_contribution",
            "set_response", "remove_response", "save_post", "unsave_post",
            "save_contribution", "unsave_contribution", "upload_attachment",
            "attachment_status", "delete_attachment",
        ):
            self.assertIn(f"'community_api.{endpoint}':", self.app_source)


class CommunityMigrationContractTests(unittest.TestCase):
    def test_schema_and_procedure_contract_is_complete_and_has_no_fixture_seed(self):
        migration = (ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql").read_text()
        for table in (
            "community_posts", "community_post_revisions", "community_contributions",
            "community_contribution_revisions", "community_responses", "community_saves",
            "community_media", "community_audit_events", "community_outbox",
        ):
            self.assertIn(f"dbo.{table}", migration)
        for procedure in (
            "usp_ListPublicCommunityFeed", "usp_ListPublicCommunityShelf",
            "usp_GetPublicCommunityPost", "usp_GetPublicCommunityContribution",
            "usp_SearchPublicCommunity", "usp_PublishPublicCommunityPost",
            "usp_EditPublicCommunityPost", "usp_DeletePublicCommunityPost",
            "usp_AddPublicCommunityContribution", "usp_SetPublicCommunityResponse",
            "usp_SetPublicCommunitySave", "usp_GetPublicCommunityMedia",
            "usp_RejectPublicCommunityMedia",
            "usp_CompensatePublicCommunityMediaCompletion",
            "usp_ClaimPublicCommunityMediaCleanup",
            "usp_CompletePublicCommunityMediaCleanup",
        ):
            self.assertIn(procedure, migration)
        self.assertNotIn("INSERT dbo.community_posts\n        VALUES", migration)
        self.assertIn("audience = N'public'", migration)
        self.assertIn("publication_state = N'published'", migration)
        self.assertIn("idempotency_hash binary(32) NOT NULL", migration)
        self.assertIn("idempotency_conflict", migration)
        self.assertIn("SAVE TRANSACTION CommunityPublish", migration)
        self.assertIn("@Audience IS NULL OR @Audience <> N''public''", migration)
        self.assertIn("@ExpectedRevision IS NULL OR @ExpectedRevision<1", migration)
        self.assertIn("SAVE TRANSACTION CommunityResponseSet", migration)
        self.assertIn("SAVE TRANSACTION CommunitySaveSet", migration)
        for procedure in (
            "usp_AddPublicCommunityContribution",
            "usp_SetPublicCommunityResponse",
            "usp_SetPublicCommunitySave",
        ):
            procedure_body = migration.split(
                f"CREATE OR ALTER PROCEDURE dbo.{procedure}", 1
            )[1].split("CREATE OR ALTER PROCEDURE dbo.", 1)[0]
            self.assertLess(
                procedure_body.index("BEGIN TRANSACTION"),
                procedure_body.index(
                    "post_author WITH(UPDLOCK,HOLDLOCK)"
                ),
            )
        self.assertIn("SAVE TRANSACTION CommunityMediaDelete", migration)
        self.assertIn("CK_community_contributions_shape", migration)
        contribution_procedure = migration.split(
            "CREATE OR ALTER PROCEDURE dbo.usp_AddPublicCommunityContribution", 1
        )[1].split("CREATE OR ALTER PROCEDURE dbo.", 1)[0]
        self.assertNotIn(
            "@ContributionKind nvarchar(30), @Body", contribution_procedure
        )
        derived_kind = (
            "SET @ContributionKind=CASE WHEN @ParentId IS NOT NULL THEN "
            "N''reply'' WHEN @PostAuthorId=@UserId THEN N''author_update'' "
            "ELSE N''comment'' END"
        )
        self.assertIn(derived_kind, contribution_procedure)
        self.assertLess(
            contribution_procedure.index(derived_kind),
            contribution_procedure.index("DECLARE @CommandHash binary(32)"),
        )
        self.assertIn("CK_community_media_clean_ready", migration)
        self.assertIn("scan_result IS NOT NULL AND scan_result = N'clean'", migration)
        self.assertIn("safe_byte_length IS NOT NULL", migration)
        self.assertIn("safe_sha256 IS NOT NULL", migration)
        self.assertIn("scan_result=N''clean''", migration)
        self.assertIn("FK_community_media_post_owner", migration)
        self.assertIn("FK_community_media_contribution_owner", migration)
        self.assertIn("contributor.active=1 AND contributor.account_status=N''active''", migration)
        self.assertIn("boundary_published_at_utc", migration)
        self.assertIn("boundary_contribution_key", migration)
        self.assertIn("SELECT TOP (@PageLimit + 1)", migration)
        self.assertIn(
            "@EmittedCandidateCount int=CASE WHEN @SelectedCandidateCount>@PageLimit THEN @PageLimit ELSE @SelectedCandidateCount END",
            migration,
        )
        self.assertIn(
            "SELECT @EmittedCandidateCount AS selected_candidate_count",
            migration,
        )
        self.assertIn(
            "CAST(CASE WHEN @SelectedCandidateCount>@PageLimit THEN 1 ELSE 0 END AS bit) AS has_more",
            migration,
        )
        self.assertGreaterEqual(
            migration.count("page_record.page_rank<=@PageLimit"), 4
        )
        self.assertIn("@PageSize+1", migration)
        self.assertIn("DECLARE @ContributionCandidates TABLE", migration)
        self.assertIn("WHERE candidate.page_rank<=@PageSize", migration)
        self.assertIn(
            "INSERT @ContributionPage(community_contribution_id)", migration
        )
        self.assertIn(
            "SELECT DISTINCT community_contribution_id FROM ProjectionTree",
            migration,
        )
        self.assertIn("@CurrentProjectionIds", migration)
        self.assertIn("N''unavailable''", migration)
        self.assertIn("SELECT N''depth_limit'' AS outcome", migration)
        self.assertNotIn("THROW 52433,''Maximum reply depth reached.''", migration)
        self.assertNotIn("@PageLimit int = 21", migration)
        for procedure in (
            "usp_ListPublicCommunityShelf",
            "usp_GetPublicCommunityContribution",
        ):
            self.assertEqual(
                migration.count(f"CREATE OR ALTER PROCEDURE dbo.{procedure}"),
                1,
            )
        self.assertEqual(
            migration.count("CREATE OR ALTER PROCEDURE dbo.usp_ClaimPublicCommunityMediaCleanup"),
            1,
        )
        self.assertEqual(
            migration.count("CREATE OR ALTER PROCEDURE dbo.usp_CompletePublicCommunityMediaCleanup"),
            1,
        )
        self.assertEqual(
            migration.count("CREATE OR ALTER PROCEDURE dbo.usp_CompensatePublicCommunityMediaCompletion"),
            1,
        )
        self.assertIn("N''cleanup_reopened'' AS outcome", migration)
        self.assertIn("blob_cleanup_completed_at_utc=NULL", migration)
        self.assertIn("media.media_state IN(N''rejected'',N''failed'',N''removed'')", migration)
        self.assertIn("media.expires_at_utc<=@Now", migration)

    def test_rollback_refuses_to_drop_populated_domain(self):
        rollback = (ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-COMMUNITY-PUBLIC-PILOT-001_community_rollback.sql").read_text()
        self.assertLess(rollback.index("EXISTS(SELECT 1 FROM dbo.community_posts)"), rollback.index("DROP TABLE IF EXISTS dbo.community_posts"))
        self.assertIn("Disable the feature flag", rollback)
        self.assertIn("EXISTS(SELECT 1 FROM dbo.community_audit_events)", rollback)
        self.assertIn("EXISTS(SELECT 1 FROM dbo.community_outbox)", rollback)
        self.assertIn("DROP PROCEDURE IF EXISTS dbo.usp_ClaimPublicCommunityMediaCleanup", rollback)
        self.assertIn("DROP PROCEDURE IF EXISTS dbo.usp_CompletePublicCommunityMediaCleanup", rollback)
        self.assertIn("DROP PROCEDURE IF EXISTS dbo.usp_CompensatePublicCommunityMediaCompletion", rollback)
        self.assertIn("DROP PROCEDURE IF EXISTS dbo.usp_ListPublicCommunityShelf", rollback)
        self.assertIn("DROP PROCEDURE IF EXISTS dbo.usp_GetPublicCommunityContribution", rollback)
        self.assertIn("DECLARE @CommunityObjectIds TABLE", rollback)
        self.assertIn(
            "dependency.referenced_id IN(SELECT object_id FROM @CommunityObjectIds)",
            rollback,
        )
        self.assertIn(
            "dependency.referencing_id NOT IN(SELECT object_id FROM @CommunityObjectIds)",
            rollback,
        )


if __name__ == "__main__":
    unittest.main()
