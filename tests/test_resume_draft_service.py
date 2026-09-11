"""Resume draft overlay contracts. In-memory only — not a live database."""

from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from services.resume_draft_repository import InMemoryCanonicalCatalog, InMemoryResumeDraftRepository
from services.resume_draft_service import (
    ResumeDraftConflictError,
    ResumeDraftNotFoundError,
    ResumeDraftService,
    ResumeDraftUnavailableError,
    ResumeDraftValidationError,
)


OWNER_A = "owner-a"
OWNER_B = "owner-b"
ROLE_KEY = str(UUID(int=11, version=4))
EDU_KEY = str(UUID(int=12, version=4))


def role_values(**overrides):
    values = {
        "role_title": "Engineer",
        "employer_name": "PeerSlate",
        "location_text": None,
        "summary": "Built private tools",
        "start_date": "2026-09-01",
        "end_date": None,
        "date_precision": "month",
        "employment_type": "full_time",
        "current_role": True,
    }
    values.update(overrides)
    return values


def education_values(**overrides):
    values = {
        "title": "Undergraduate study",
        "institution_name": "Example University",
        "degree_name": None,
        "field_of_study": "History",
        "education_status": "in_progress",
        "grade_text": None,
        "location_text": None,
        "summary": "My own wording",
        "start_date": "2024-08-01",
        "end_date": None,
        "date_precision": "month",
    }
    values.update(overrides)
    return values


def published_role(owner_catalog, key=ROLE_KEY, **values):
    return owner_catalog.put_item(
        OWNER_A,
        {
            "record_key": key,
            "record_type": "role",
            "content_token": "1",
            "access_revision": 1,
            "editable": False,
            "blocked_reason": "published_or_history_bearing",
            "save_mode": "draft_overlay",
            "values": role_values(**values),
            "resume_display": True,
            "visitor_ai": True,
            "private_assistance_excluded": False,
        },
    )


class ResumeDraftServiceTests(unittest.TestCase):
    def setUp(self):
        self.catalog = InMemoryCanonicalCatalog()
        self.repository = InMemoryResumeDraftRepository()
        self.service = ResumeDraftService(repository=self.repository, catalog=self.catalog)
        published_role(self.catalog)

    def test_owners_cannot_read_or_mutate_each_other(self):
        self.catalog.put_item(
            OWNER_B,
            {
                "record_key": ROLE_KEY,
                "record_type": "role",
                "content_token": "1",
                "access_revision": 1,
                "editable": False,
                "blocked_reason": "published_or_history_bearing",
                "save_mode": "draft_overlay",
                "values": role_values(summary="B wording"),
                "resume_display": True,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            },
        )
        saved = self.service.commit(
            OWNER_A,
            {
                "request_id": str(uuid4()),
                "type": "save_item",
                "record_key": ROLE_KEY,
                "record_type": "role",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": "A overlay"},
            },
        )
        self.assertEqual(saved["item"]["proposed_values"]["summary"], "A overlay")
        other = self.service.get_workspace(OWNER_B)
        self.assertEqual(other["items"][0]["values"]["summary"], "B wording")
        self.assertFalse(other["items"][0]["has_draft"])
        self.assertNotEqual(self.service.get_workspace(OWNER_A)["items"][0]["proposed_values"], None)

    def test_overlay_save_does_not_change_canonical_or_sharing(self):
        self.service.commit(
            OWNER_A,
            {
                "request_id": str(uuid4()),
                "type": "save_item",
                "record_key": ROLE_KEY,
                "record_type": "role",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": "Proposed only"},
                "intended_permission_expansions": {"resume_display": False},
            },
        )
        canonical = self.catalog.get_item(OWNER_A, ROLE_KEY)
        self.assertEqual(canonical["values"]["summary"], "Built private tools")
        self.assertTrue(canonical["resume_display"])
        workspace = self.service.get_workspace(OWNER_A)
        item = workspace["items"][0]
        self.assertEqual(item["proposed_values"]["summary"], "Proposed only")
        self.assertTrue(item["resume_display"])
        self.assertTrue(item["draft_does_not_change_sharing"])
        self.assertFalse(workspace["capabilities"]["publishes"])
        self.assertEqual(workspace["capabilities"]["persistence"], "in_memory_not_live_db")
        self.assertFalse(workspace["capabilities"]["schema_applied"])

    def test_stale_content_and_access_preserve_proposed_text(self):
        self.catalog.bump_content(OWNER_A, ROLE_KEY)
        with self.assertRaises(ResumeDraftConflictError) as raised:
            self.service.commit(
                OWNER_A,
                {
                    "request_id": str(uuid4()),
                    "type": "save_item",
                    "record_key": ROLE_KEY,
                    "record_type": "role",
                    "expected_content_token": "1",
                    "expected_access_revision": 1,
                    "values": {"summary": "Keep this wording"},
                },
            )
        self.assertEqual(raised.exception.error_code, "changed")
        self.assertEqual(raised.exception.proposed["summary"], "Keep this wording")

        self.catalog.put_item(OWNER_A, {**self.catalog.get_item(OWNER_A, ROLE_KEY), "content_token": "1"})
        self.catalog.bump_access(OWNER_A, ROLE_KEY)
        with self.assertRaises(ResumeDraftConflictError) as access:
            self.service.commit(
                OWNER_A,
                {
                    "request_id": str(uuid4()),
                    "type": "save_item",
                    "record_key": ROLE_KEY,
                    "record_type": "role",
                    "expected_content_token": "1",
                    "expected_access_revision": 1,
                    "values": {"summary": "Permission stale"},
                },
            )
        self.assertFalse(access.exception.conflicts[0]["permissions_restored"])
        self.assertEqual(access.exception.proposed["summary"], "Permission stale")
        self.assertFalse(self.catalog.get_item(OWNER_A, ROLE_KEY)["resume_display"])

    def test_same_body_replays_and_changed_payload_conflicts(self):
        request_id = str(uuid4())
        body = {
            "request_id": request_id,
            "type": "save_item",
            "record_key": ROLE_KEY,
            "record_type": "role",
            "expected_content_token": "1",
            "expected_access_revision": 1,
            "values": {"summary": "Once"},
        }
        first = self.service.commit(OWNER_A, body)
        replay = self.service.commit(OWNER_A, body)
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["outcome"], "saved")
        with self.assertRaises(ResumeDraftConflictError) as raised:
            self.service.commit(OWNER_A, {**body, "values": {"summary": "Different"}})
        self.assertEqual(raised.exception.error_code, "idempotency_conflict")

    def test_review_does_not_publish(self):
        result = self.service.commit(
            OWNER_A,
            {"request_id": str(uuid4()), "type": "review_candidate"},
        )
        self.assertEqual(result["outcome"], "reviewed")
        self.assertFalse(result["publishes"])
        self.assertIn("review_digest", result)
        self.assertTrue(self.catalog.get_item(OWNER_A, ROLE_KEY)["resume_display"])

    def test_stale_review_is_blocked_and_keeps_proposed_text(self):
        self.service.commit(
            OWNER_A,
            {
                "request_id": str(uuid4()),
                "type": "save_item",
                "record_key": ROLE_KEY,
                "record_type": "role",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": "Keep for review"},
            },
        )
        self.catalog.bump_content(OWNER_A, ROLE_KEY)
        with self.assertRaises(ResumeDraftConflictError) as raised:
            self.service.commit(
                OWNER_A,
                {"request_id": str(uuid4()), "type": "review_candidate"},
            )
        self.assertEqual(raised.exception.error_code, "changed")
        self.assertEqual(raised.exception.proposed["summary"], "Keep for review")
        self.assertEqual(
            self.service.get_workspace(OWNER_A)["items"][0]["proposed_values"]["summary"],
            "Keep for review",
        )

    def test_create_private_defaults_display_and_visitor_ai_off(self):
        created = self.service.commit(
            OWNER_A,
            {
                "request_id": str(uuid4()),
                "type": "create_private_item",
                "record_key": EDU_KEY,
                "record_type": "education",
                "values": education_values(),
            },
        )
        self.assertEqual(created["outcome"], "created")
        self.assertFalse(created["item"]["resume_display"])
        self.assertFalse(created["item"]["visitor_ai"])
        stored = self.catalog.get_item(OWNER_A, EDU_KEY)
        self.assertFalse(stored["resume_display"])
        self.assertTrue(stored["editable"])

    def test_zero_few_many_and_long_partial_education(self):
        empty = ResumeDraftService(
            repository=InMemoryResumeDraftRepository(),
            catalog=InMemoryCanonicalCatalog(),
        )
        self.assertEqual(empty.get_workspace(OWNER_A)["items"], [])
        for index in range(12):
            key = str(UUID(int=100 + index, version=4))
            self.catalog.put_item(
                OWNER_A,
                {
                    "record_key": key,
                    "record_type": "education",
                    "content_token": "1",
                    "access_revision": 1,
                    "editable": True,
                    "blocked_reason": None,
                    "save_mode": "canonical",
                    "values": education_values(title=f"Program {index}", summary=None),
                    "resume_display": False,
                    "visitor_ai": False,
                    "private_assistance_excluded": False,
                },
            )
        listed = self.service.get_workspace(OWNER_A)["items"]
        education = [item for item in listed if item["record_type"] == "education"]
        self.assertEqual(len(education), 12)
        long_summary = "Member wording: 😀 " + ("x" * 200)
        target = education[0]["record_key"]
        saved = self.service.commit(
            OWNER_A,
            {
                "request_id": str(uuid4()),
                "type": "save_item",
                "record_key": target,
                "record_type": "education",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": long_summary, "degree_name": None},
            },
        )
        self.assertEqual(saved["item"]["proposed_values"]["summary"], long_summary)
        self.assertIsNone(saved["item"]["proposed_values"]["degree_name"])

    def test_foreign_or_missing_record_is_not_found(self):
        with self.assertRaises(ResumeDraftNotFoundError):
            self.service.commit(
                OWNER_A,
                {
                    "request_id": str(uuid4()),
                    "type": "save_item",
                    "record_key": str(UUID(int=99, version=4)),
                    "record_type": "role",
                    "expected_content_token": "1",
                    "expected_access_revision": 1,
                    "values": {"summary": "nope"},
                },
            )

    def test_authority_fields_are_rejected(self):
        with self.assertRaises(ResumeDraftValidationError):
            self.service.commit(
                OWNER_A,
                {
                    "request_id": str(uuid4()),
                    "type": "save_item",
                    "record_key": ROLE_KEY,
                    "record_type": "role",
                    "owner_user_key": OWNER_B,
                    "expected_content_token": "1",
                    "expected_access_revision": 1,
                    "values": {"summary": "nope"},
                },
            )

    def test_in_memory_store_is_not_restart_or_engine_proof(self):
        self.service.commit(
            OWNER_A,
            {
                "request_id": str(uuid4()),
                "type": "save_item",
                "record_key": ROLE_KEY,
                "record_type": "role",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": "ephemeral"},
            },
        )
        restarted = ResumeDraftService(
            repository=InMemoryResumeDraftRepository(),
            catalog=self.catalog,
        )
        self.assertFalse(restarted.get_workspace(OWNER_A)["items"][0]["has_draft"])
        self.assertEqual(
            restarted.get_workspace(OWNER_A)["capabilities"]["persistence"],
            "in_memory_not_live_db",
        )


class UnavailableCatalogTests(unittest.TestCase):
    def test_create_private_preserves_input_when_canonical_source_is_down(self):
        class Down:
            def list_items(self, owner):
                from services.resume_draft_repository import CanonicalReadUnavailable

                raise CanonicalReadUnavailable()

            def get_item(self, owner, key):
                from services.resume_draft_repository import CanonicalReadUnavailable

                raise CanonicalReadUnavailable()

            def create_private(self, owner, item):
                from services.resume_draft_repository import CanonicalReadUnavailable

                raise CanonicalReadUnavailable()

        service = ResumeDraftService(
            repository=InMemoryResumeDraftRepository(),
            catalog=Down(),
        )
        with self.assertRaises(ResumeDraftUnavailableError) as raised:
            service.commit(
                OWNER_A,
                {
                    "request_id": str(uuid4()),
                    "type": "create_private_item",
                    "record_key": EDU_KEY,
                    "record_type": "education",
                    "values": education_values(),
                },
            )
        self.assertEqual(raised.exception.proposed["title"], "Undergraduate study")


if __name__ == "__main__":
    unittest.main()
