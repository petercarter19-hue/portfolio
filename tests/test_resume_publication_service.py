"""In-memory complete publication boundary. Not SQL engine proof."""

from __future__ import annotations

import copy
import hashlib
import json
from uuid import uuid4
from unittest.mock import Mock

import unittest

from services.resume_media_catalog_repository import (
    CatalogFenceDenied,
    InMemoryResumeCatalogRepository,
    SqlResumeCatalogRepository,
)
from services.resume_media_repository import CatalogAssetRecord
from services.resume_publication_adapters import SnapshotMediaPort, SnapshotPolicyPort
from services.resume_publication_repository import (
    InMemoryResumePublicationRepository,
    PublicationConflictError,
    PublicationDenied,
    PublicationStoreUnavailable,
    SqlResumePublicationRepository,
)
from services.resume_publication_service import (
    PublicationUnavailableError,
    PublicationValidationError,
    ResumePublicationService,
    memory_resume_publication_service,
)
from services.resume_publication_validation import validate_candidate
from tests.test_resume_publication_contracts import fixture
from tests.mvp1_acceptance_support import SharedMvp1Fixture


class IntegratedDraftPublicationTests(unittest.TestCase):
    def test_story_banner_is_hidden_without_displayed_story_and_restriction_removes_it(self):
        shared = SharedMvp1Fixture()
        owner, key = "member-a", str(uuid4())
        shared.policy.commit(owner, {"type": "create", "request_id": str(uuid4()),
            "entry_key": key, "canonical_type": "knowledge", "values": {
                "title": "My Story", "wording": "I enjoy building small useful tools.", "classification": "personal"}})
        from services.resume_media_repository import MediaPlacement, RequestReceipt, provenance_label_for
        from services.resume_media_service import centered_slot_crop
        photo = shared.seed_photo(owner)
        placement = MediaPlacement("story_banner", "owner_photo", photo.source_id,
            photo.version, photo.digest, centered_slot_crop(slot="story_banner", width=photo.width, height=photo.height),
            alt_text="Synthetic test image", provenance_label=provenance_label_for(source_kind="owner_photo"))
        shared.media.media_repository.commit_draft(owner_id=owner, expected_version=0,
            placements=(placement,), receipt=RequestReceipt(owner, "add", str(uuid4()), "b" * 64, "{}"))
        def publish(display):
            review = shared.publication.review_for_owner(owner, {"entries": [
                {"entry_key": key, "resume_display": display, "visitor_ai": False}]}).reviewed
            self.assertIsNotNone(review)
            shared.publication.commit(owner, {"type": "publish", "request_id": str(uuid4()), "slug": "alice",
                "profile_identity": None, "reviewed_digest": review.digest,
                "candidate": shared.publication.publish_candidate(review)})
        publish(False)
        self.assertNotIn("story_banner", shared.publication.guest_read(slug="alice")["media"])
        with self.assertRaises(PublicationDenied):
            shared.publication.deliver_guest_media(slug="alice", slot="story_banner")
        # An identical title never implicitly binds personal information.
        self.assertIsNone(shared.draft.get_workspace(owner)["story_entry_key"])
        item = shared.canonical.get_item(owner, key)
        shared.draft.commit(owner, {"type": "bind_story", "request_id": str(uuid4()), "record_key": key,
            "expected_content_token": item["content_token"], "expected_access_revision": item["access_revision"],
            "expected_draft_version": shared.draft.get_workspace(owner)["draft_version"]})
        publish(True)
        self.assertIn("story_banner", shared.publication.guest_read(slug="alice")["media"])
        row = shared.policy.list_entries(owner)["entries"][0]
        shared.policy.commit(owner, {"type": "change_permissions", "request_id": str(uuid4()),
            "entry_key": key, "expected_access_revision": row["access_revision"],
            "permissions": {"resume_display": False}})
        self.assertNotIn("story_banner", shared.publication.guest_read(slug="alice")["media"])
        with self.assertRaises(PublicationDenied):
            shared.publication.deliver_guest_media(slug="alice", slot="story_banner")

    def test_real_media_bytes_and_late_restriction_never_release_stale_bytes(self):
        shared, owner, key, _ = self._saved_edit()
        from services.resume_media_repository import MediaPlacement, RequestReceipt, provenance_label_for
        from services.resume_media_service import centered_slot_crop
        photo = shared.seed_photo(owner)
        placement = MediaPlacement("experience_support", "owner_photo", photo.source_id,
            photo.version, photo.digest, centered_slot_crop(slot="experience_support", width=photo.width, height=photo.height),
            alt_text="Synthetic blue test image", provenance_label=provenance_label_for(source_kind="owner_photo"))
        shared.media.media_repository.commit_draft(owner_id=owner, expected_version=1,
            placements=(placement,), receipt=RequestReceipt(owner, "add", str(uuid4()), "b" * 64, "{}"))
        reviewed = shared.publication.review_for_owner(owner, {"entries": [
            {"entry_key": key, "resume_display": True, "visitor_ai": False}]}).reviewed
        shared.publication.commit(owner, {"type": "publish", "request_id": str(uuid4()), "slug": "alice",
            "profile_identity": None, "reviewed_digest": reviewed.digest,
            "candidate": shared.publication.publish_candidate(reviewed)})
        read = shared.publication.deliver_guest_media(slug="alice", slot="experience_support")
        self.assertEqual(read["status"], 200)
        self.assertEqual(read["content_type"], "image/png")
        self.assertTrue(read["body"].startswith(b"\x89PNG"))
        shared.media_storage.on_open = lambda *args, **kwargs: shared.media_sources.update_owner_photo(
            owner_id=owner, source_id=photo.source_id, lifecycle="restricted")
        with self.assertRaises((PublicationDenied, PublicationUnavailableError)):
            shared.publication.deliver_guest_media(slug="alice", slot="experience_support")
        self.assertNotIn("experience_support", shared.publication.guest_read(slug="alice")["media"])

    def _saved_edit(self):
        shared = SharedMvp1Fixture()
        owner, key = "member-a", str(uuid4())
        shared.policy.commit(owner, {"type": "create", "request_id": str(uuid4()),
            "entry_key": key, "canonical_type": "role", "values": {
                "role_title": "Engineer", "employer_name": "Synthetic Company", "summary": "Original wording."}})
        item = shared.canonical.get_item(owner, key)
        shared.draft.commit(owner, {"type": "save_item", "request_id": str(uuid4()),
            "record_key": key, "record_type": "role", "expected_content_token": item["content_token"],
            "expected_access_revision": item["access_revision"], "expected_draft_version": 0,
            "values": {"summary": "Reviewed new wording."}})
        reviewed = shared.publication.review_for_owner(owner, {"entries": [
            {"entry_key": key, "resume_display": True, "visitor_ai": True}]}).reviewed
        self.assertIsNotNone(reviewed)
        envelope = shared.publication.publish_candidate(reviewed)
        return shared, owner, key, {"type": "publish", "request_id": str(uuid4()),
            "slug": "alice", "profile_identity": None,
            "reviewed_digest": reviewed.digest, "candidate": envelope}

    def test_complete_candidate_needs_no_pending_review_and_commits_only_reviewed_changes(self):
        shared, owner, key, payload = self._saved_edit()
        shared.publication._pending_reviews.clear()
        shared.publication.commit(owner, payload)
        row = shared.policy.list_entries(owner)["entries"][0]
        self.assertEqual(row["values"]["summary"], "Reviewed new wording.")
        self.assertEqual(row["values"]["employer_name"], "Synthetic Company")
        self.assertTrue(row["resume_display"])
        self.assertTrue(row["visitor_ai"])
        self.assertEqual(row["content_version"], 2)
        self.assertEqual(shared.draft.repository.load_owner(owner)["items"], {})
        self.assertEqual(shared.publication.guest_read(slug="alice")["display"][key]["wording"]["summary"], "Reviewed new wording.")
        shared.publication.commit(owner, {"type": "sharing_off", "request_id": str(uuid4())})
        self.assertTrue(shared.publication.commit(owner, copy.deepcopy(payload))["replayed"])
        self.assertFalse(shared.publication.owner_preview(owner)["sharing_enabled"])
        changed = copy.deepcopy(payload)
        changed["candidate"]["entries"][0]["visitor_ai"] = False
        with self.assertRaises(PublicationConflictError):
            shared.publication.commit(owner, changed)
        self.assertEqual(shared.policy.list_entries(owner)["entries"][0]["content_version"], 2)

    def test_changed_canonical_base_preserves_new_fact_and_private_draft(self):
        shared, owner, key, payload = self._saved_edit()
        shared.policy.commit(owner, {"type": "edit", "request_id": str(uuid4()), "entry_key": key,
            "expected_content_version": 1, "expected_access_revision": 1,
            "values": {"summary": "New canonical fact.", "role_title": "Engineer", "employer_name": "Synthetic Company"}})
        with self.assertRaises(PublicationConflictError):
            shared.publication.commit(owner, payload)
        self.assertEqual(shared.policy.list_entries(owner)["entries"][0]["values"]["summary"], "New canonical fact.")
        self.assertIn(key, shared.draft.repository.load_owner(owner)["items"])
        self.assertIsNone(shared.publication.owner_preview(owner)["current"])

    def test_forged_reviewed_delta_cannot_change_saved_overlay(self):
        shared, owner, key, payload = self._saved_edit()
        payload["candidate"]["entries"][0]["deltas"][0]["after"] = "Unreviewed injected wording"
        with self.assertRaises(PublicationConflictError):
            shared.publication.commit(owner, payload)
        self.assertEqual(shared.policy.list_entries(owner)["entries"][0]["values"]["summary"], "Original wording.")

    def test_failed_publication_save_restores_canonical_draft_and_receipt(self):
        shared, owner, key, payload = self._saved_edit()
        original_save = shared.publication.repository.save_owner
        calls = []
        def fail_once(who, snapshot):
            calls.append(who)
            if len(calls) == 1:
                raise PublicationStoreUnavailable("injected failure")
            return original_save(who, snapshot)
        shared.publication.repository.save_owner = fail_once
        with self.assertRaises(PublicationUnavailableError):
            shared.publication.commit(owner, payload)
        self.assertEqual(shared.policy.list_entries(owner)["entries"][0]["values"]["summary"], "Original wording.")
        self.assertIn(key, shared.draft.repository.load_owner(owner)["items"])
        self.assertEqual(shared.publication.repository.load_owner(owner)["receipts"], {})
        shared.publication.commit(owner, payload)
        self.assertEqual(shared.policy.list_entries(owner)["entries"][0]["content_version"], 2)

    def test_saved_photo_crop_is_reviewed_and_late_source_restriction_blocks_publish(self):
        shared, owner, key, _ = self._saved_edit()
        from services.resume_media_repository import MediaPlacement, RequestReceipt, provenance_label_for
        from services.resume_media_service import centered_slot_crop
        source_key = str(uuid4())
        shared.media_sources.seed_owner_photo(owner_id=owner, source_id=source_key,
            width=1800, height=600, digest="a" * 64)
        placement = MediaPlacement("experience_support", "owner_photo", source_key, 1, "a" * 64,
            centered_slot_crop(slot="experience_support", width=1800, height=600), 1, "Synthetic landscape", False,
            provenance_label_for(source_kind="owner_photo"), None)
        shared.media.media_repository.commit_draft(owner_id=owner, expected_version=1,
            placements=(placement,), receipt=RequestReceipt(owner, "add", str(uuid4()), "b" * 64, "{}"))
        result = shared.publication.review_for_owner(owner, {"entries": [
            {"entry_key": key, "resume_display": True, "visitor_ai": False}]})
        self.assertIsNotNone(result.reviewed, result.reason)
        envelope = shared.publication.publish_candidate(result.reviewed)
        self.assertEqual(envelope["placements"][0]["crop"], placement.crop.as_dict())
        command = {"type": "publish", "request_id": str(uuid4()), "slug": "alice",
            "reviewed_digest": result.reviewed.digest, "candidate": envelope, "profile_identity": None}
        shared.media_sources.update_owner_photo(owner_id=owner, source_id=source_key, lifecycle="restricted")
        with self.assertRaises(PublicationUnavailableError):
            shared.publication.commit(owner, command)
        self.assertIsNone(shared.publication.owner_preview(owner)["current"])
        self.assertEqual(shared.draft.repository.load_owner(owner)["draft_version"], 2)

    def test_saved_resume_editorial_delta_is_in_the_publication_review(self):
        shared = SharedMvp1Fixture()
        shared.canonical.token_for_version = lambda value: "0x" + format(value, "016x")
        owner, key = "member-a", str(uuid4())
        shared.policy.commit(owner, {"type": "create", "request_id": str(uuid4()),
            "entry_key": key, "canonical_type": "role", "values": {
                "role_title": "Engineer", "employer_name": "Synthetic Company", "summary": "Original wording."}})
        row = shared.policy.list_entries(owner)["entries"][0]
        shared.policy.commit(owner, {"type": "change_permissions", "request_id": str(uuid4()),
            "entry_key": key, "expected_access_revision": row["access_revision"],
            "permissions": {"resume_display": True, "visitor_ai": False}})
        item = shared.canonical.get_item(owner, key)
        shared.draft.commit(owner, {"type": "save_item", "request_id": str(uuid4()),
            "record_key": key, "record_type": "role", "expected_content_token": item["content_token"],
            "expected_access_revision": item["access_revision"], "expected_draft_version": 0,
            "values": {"summary": "Reviewed new wording."}})
        reviewed = shared.publication.review_for_owner(owner).reviewed
        self.assertIsNotNone(reviewed)
        values = {word.field: word.value for word in reviewed.display.entries[0].wording}
        self.assertEqual(values["summary"], "Reviewed new wording.")
        self.assertEqual(reviewed.candidate.draft_bases[0].canonical_token, "0x0000000000000001")
        self.assertEqual(reviewed.candidate.draft_bases[0].entry.content_revision, "1")
        self.assertEqual(shared.policy.list_entries(owner)["entries"][0]["values"]["summary"], "Original wording.")


def reviewed_for(owner="member-a"):
    candidate, policy, media = fixture()
    result = validate_candidate(
        candidate,
        Mock(read_current=Mock(return_value=policy)),
        Mock(read_current=Mock(return_value=media)),
    )
    assert result.reviewed is not None
    return result.reviewed


def catalog_record():
    digest = "a" * 64
    return CatalogAssetRecord(
        "asset-1",
        2,
        digest,
        "Leadership",
        "concept",
        ("Teamwork",),
        1800,
        600,
    )


class ResumePublicationServiceTests(unittest.TestCase):
    def setUp(self):
        self.catalog = InMemoryResumeCatalogRepository()
        self.service = memory_resume_publication_service(
            catalog=self.catalog, reserved_public_slugs={"petec"}
        )
        self.owner = "member-a"
        self.other = "member-b"
        self.service.bind_slug(self.owner, "alice")
        candidate, policy, media = fixture()
        self.service.policy_port = SnapshotPolicyPort(policy)
        self.service.media_port = SnapshotMediaPort(media)

    def _publish(self, owner=None, request_id=None, slug="alice"):
        owner = owner or self.owner
        reviewed = reviewed_for(owner)
        payload = {
            "type": "publish",
            "request_id": request_id or str(uuid4()),
            "reviewed_digest": reviewed.digest,
            "slug": slug,
            "expected_publication_revision": 0,
            "canonical_types": {reviewed.display.entries[0].ref.entry_key: "role"},
        }
        return self.service.commit(owner, payload, reviewed=reviewed), reviewed

    def test_owner_isolation_and_independent_display_ai_combinations(self):
        combinations = (
            (True, False),
            (False, True),
            (False, False),
            (True, True),
        )
        for display, visitor_ai in combinations:
            self.setUp()
            self._publish()
            reviewed = reviewed_for()
            entry = reviewed.display.entries[0].ref.entry_key
            if not display or not visitor_ai:
                self.service.commit(
                    self.owner,
                    {
                        "type": "change_permissions",
                        "request_id": str(uuid4()),
                        "entry_key": entry,
                        "resume_display": display,
                        "visitor_ai": visitor_ai,
                    },
                )
            guest = self.service.guest_read(slug="alice")
            if display:
                self.assertIn(entry, guest["display"])
            else:
                self.assertNotIn(entry, guest["display"])
            self.assertNotIn("visitor_ai", guest)
            preview = self.service.owner_preview(self.owner)
            if visitor_ai:
                self.assertIn(entry, preview["current"]["visitor_ai"])
            else:
                self.assertNotIn(entry, preview["current"]["visitor_ai"])
            if not display:
                self.assertNotIn("Led team 0.", json.dumps(guest["display"]))
        self.setUp()
        self._publish()
        self.service.bind_slug(self.other, "bob")
        with self.assertRaises(PublicationDenied):
            self.service.guest_read(slug="bob")
        other_preview = self.service.owner_preview(self.other)
        self.assertIsNone(other_preview["current"])

    def test_publish_then_guest_sees_result_then_private_edit_leaves_guest_unchanged(self):
        _, reviewed = self._publish()
        before = self.service.guest_read(slug="alice")
        snapshot = self.service.repository.load_owner(self.owner)
        snapshot["private_draft"] = {"summary": "Owner-only draft"}
        self.service.repository.save_owner(self.owner, snapshot)
        after = self.service.guest_read(slug="alice")
        self.assertEqual(after["etag"], before["etag"])
        self.assertEqual(after["display"], before["display"])
        self.assertEqual(after["cache_control"], "private,no-store")

    def test_my_data_correction_updates_permitted_guest_uses_immediately(self):
        published, reviewed = self._publish()
        entry = reviewed.display.entries[0].ref.entry_key
        self.service.apply_policy_command(
            self.owner,
            {
                "type": "edit",
                "request_id": str(uuid4()),
                "entry_key": entry,
                "values": {"summary": "Led a larger team."},
                "expected_content_version": 1,
                "expected_access_revision": 1,
            },
            {entry: {"values": {"summary": "Led a larger team."}}},
        )
        guest = self.service.guest_read(slug="alice")
        self.assertEqual(guest["display"][entry]["wording"]["summary"], "Led a larger team.")
        self.assertNotEqual(guest["etag"], reviewed.digest)

    def test_stale_publication_refuses_without_overwriting(self):
        first, reviewed = self._publish()
        before = self.service.guest_read(slug="alice")
        with self.assertRaises(PublicationConflictError):
            self.service.commit(
                self.owner,
                {
                    "type": "publish",
                    "request_id": str(uuid4()),
                    "reviewed_digest": reviewed.digest,
                    "slug": "alice",
                    "expected_publication_revision": 0,
                },
                reviewed=reviewed,
            )
        after = self.service.guest_read(slug="alice")
        self.assertEqual(after["etag"], before["etag"])
        self.assertEqual(first["publication_revision"], after["publication_revision"])

    def test_restriction_deletion_sharing_off_and_private_restore(self):
        _, reviewed = self._publish()
        entry = reviewed.display.entries[0].ref.entry_key
        self.service.commit(
            self.owner,
            {"type": "delete", "request_id": str(uuid4()), "entry_key": entry},
        )
        gone = self.service.guest_read(slug="alice")
        self.assertNotIn(entry, gone["display"])
        self.service.commit(
            self.owner,
            {"type": "restore", "request_id": str(uuid4()), "entry_key": entry},
        )
        restored = self.service.guest_read(slug="alice")
        self.assertNotIn(entry, restored["display"])
        self.service.commit(self.owner, {"type": "sharing_off", "request_id": str(uuid4())})
        with self.assertRaises(PublicationDenied):
            self.service.guest_read(slug="alice")
        preview = self.service.owner_preview(self.owner)
        self.assertFalse(preview["sharing_enabled"])
        self.assertIsNotNone(preview["current"])

    def test_exact_replay_changed_body_conflict_and_rollback(self):
        request_id = str(uuid4())
        first, reviewed = self._publish(request_id=request_id)
        replay_body = {
            "type": "publish",
            "request_id": request_id,
            "reviewed_digest": reviewed.digest,
            "slug": "alice",
            "expected_publication_revision": 0,
            "canonical_types": {reviewed.display.entries[0].ref.entry_key: "role"},
        }
        replay = self.service.commit(self.owner, replay_body, reviewed=reviewed)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"]["request_digest"], first["receipt"]["request_digest"])
        with self.assertRaises(PublicationConflictError):
            self.service.commit(
                self.owner,
                {
                    "type": "publish",
                    "request_id": request_id,
                    "reviewed_digest": reviewed.digest,
                    "slug": "changed",
                    "expected_publication_revision": 0,
                },
                reviewed=reviewed,
            )
        before = self.service.guest_read(slug="alice")
        failing = memory_resume_publication_service(repository=_FailingSave(self.service.repository))
        with self.assertRaises(RuntimeError):
            failing.commit(
                self.owner,
                {
                    "type": "correct",
                    "request_id": str(uuid4()),
                    "entry_key": reviewed.display.entries[0].ref.entry_key,
                    "values": {"summary": "Should roll back."},
                    "canonical_type": "role",
                },
            )
        after = self.service.guest_read(slug="alice")
        self.assertEqual(after["display"], before["display"])

    def test_review_does_not_write(self):
        candidate, policy, media = fixture()
        self.service.policy_port = SnapshotPolicyPort(policy)
        self.service.media_port = SnapshotMediaPort(media)
        before = self.service.repository.load_owner(self.owner)
        result = self.service.review(candidate)
        after = self.service.repository.load_owner(self.owner)
        self.assertEqual(before, after)
        self.assertEqual(result.reason, "reviewed_not_published")
        self.assertIsNotNone(result.reviewed)

    def test_pete_slug_stays_classified_and_unknown_slug_does_not_fallback(self):
        self._publish()
        with self.assertRaises(PublicationDenied):
            self.service.guest_read(slug="petec")
        with self.assertRaises(PublicationDenied):
            self.service.guest_read(slug="unknown-member")
        with self.assertRaises(PublicationValidationError):
            self.service.bind_slug(self.owner, "petec")

    def test_catalog_withdraw_and_media_restrict_deny_readers(self):
        record = catalog_record()
        self.catalog.put(record)
        _, reviewed = self._publish()
        self.service.commit(
            self.owner,
            {
                "type": "catalog_withdraw",
                "request_id": str(uuid4()),
                "asset_id": record.asset_id,
                "version": record.version,
            },
        )
        with self.assertRaises(CatalogFenceDenied):
            self.catalog.get_active(record.asset_id, record.version)
        self.service.commit(
            self.owner,
            {"type": "media_restrict", "request_id": str(uuid4()), "slot": "story_banner"},
        )
        with self.assertRaises(PublicationDenied):
            self.service.authorize_media(slug="alice", slot="story_banner")

    def test_conditional_guest_read_and_old_revision_media(self):
        first, _ = self._publish()
        current = self.service.guest_read(slug="alice")
        not_modified = self.service.guest_read(slug="alice", if_none_match=current["etag"])
        self.assertEqual(not_modified["read_state"], "not_modified")
        with self.assertRaises(PublicationDenied):
            self.service.authorize_media(
                slug="alice",
                slot="missing",
                publication_revision=first["publication_revision"],
            )

    def test_correction_does_not_keep_old_source_digest(self):
        published, reviewed = self._publish()
        entry = reviewed.display.entries[0].ref.entry_key
        old_digest = self.service.guest_read(slug="alice")["display"][entry]["evidence_sha256"]
        self.service.commit(
            self.owner,
            {
                "type": "correct",
                "request_id": str(uuid4()),
                "entry_key": entry,
                "values": {"summary": "Brand new wording."},
                "canonical_type": "role",
                "expected_publication_revision": published["publication_revision"],
            },
        )
        new_digest = self.service.guest_read(slug="alice")["display"][entry]["evidence_sha256"]
        self.assertNotEqual(old_digest, new_digest)

    def test_review_for_owner_uses_durable_policy_and_does_not_write(self):
        from services.entry_policy_repository import InMemoryEntryPolicyRepository
        from services.entry_policy_service import EntryPolicyService

        policy = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        policy.publication_service = self.service
        self.service.policy_service = policy
        entry_key = str(uuid4())
        policy.commit(
            self.owner,
            {
                "type": "create",
                "request_id": str(uuid4()),
                "entry_key": entry_key,
                "canonical_type": "role",
                "values": {"role_title": "Lead", "employer_name": "PeerSlate", "summary": "Led team 0."},
            },
        )
        listed = policy.list_entries(self.owner)["entries"]
        created = next(item for item in listed if item["entry_key"] == entry_key)
        policy.commit(
            self.owner,
            {
                "type": "change_permissions",
                "request_id": str(uuid4()),
                "entry_key": entry_key,
                "expected_access_revision": created["access_revision"],
                "permissions": {"resume_display": True, "visitor_ai": False},
            },
        )
        before = self.service.repository.load_owner(self.owner)
        result = self.service.review_for_owner(self.owner, {})
        after = self.service.repository.load_owner(self.owner)
        self.assertEqual(before, after)
        self.assertIsNotNone(result.reviewed)
        self.assertEqual(result.reason, "reviewed_not_published")

    def test_sql_guest_read_omits_visitor_ai_json(self):
        class SqlPort:
            def get_public_by_slug(self, slug):
                return {
                    "reviewed_digest": "a" * 64,
                    "publication_revision": 2,
                    "display_json": {"role": {"wording": {"summary": "Led team 0."}}},
                    "visitor_ai_json": {"role": {"wording": {"summary": "AI-only wording"}}},
                    "media_json": {},
                }

        self.service.sql_repository = SqlPort()
        guest = self.service.guest_read(slug="alice")
        self.assertNotIn("visitor_ai", guest)
        self.assertNotIn("AI-only wording", json.dumps(guest))
        self.assertEqual(guest["display"]["role"]["wording"]["summary"], "Led team 0.")

    def test_production_default_uses_sql_not_memory(self):
        service = ResumePublicationService()
        self.assertIsInstance(service.repository, SqlResumePublicationRepository)
        self.assertIsInstance(service.sql_repository, SqlResumePublicationRepository)
        self.assertIsInstance(service.catalog, SqlResumeCatalogRepository)
        self.assertNotIsInstance(service.repository, InMemoryResumePublicationRepository)

    def test_sql_publish_revalidates_review_and_does_not_bypass_commit(self):
        class SqlPort:
            def __init__(self):
                self.commands = []

            def commit_command(self, owner, request_id, command):
                self.commands.append((owner, request_id, dict(command)))
                return {
                    "committed": True,
                    "replayed": False,
                    "outcome": "published",
                    "request_digest": command.get("reviewed_digest"),
                    "read_state": "current",
                    "publication_revision": 1,
                }

        sql = SqlPort()
        blocked = memory_resume_publication_service()
        blocked.sql_repository = sql
        with self.assertRaises(PublicationUnavailableError):
            blocked.commit(
                self.owner,
                {
                    "type": "publish",
                    "request_id": str(uuid4()),
                    "reviewed_digest": "a" * 64,
                    "slug": "alice",
                },
            )
        self.assertEqual(sql.commands, [])

        from services.entry_policy_repository import InMemoryEntryPolicyRepository
        from services.entry_policy_service import EntryPolicyService

        policy = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        service = memory_resume_publication_service()
        service.sql_repository = sql
        service.policy_service = policy
        policy.publication_service = service
        entry_key = str(uuid4())
        policy.commit(
            self.owner,
            {
                "type": "create",
                "request_id": str(uuid4()),
                "entry_key": entry_key,
                "canonical_type": "role",
                "values": {"role_title": "Lead", "employer_name": "PeerSlate", "summary": "Led team 0."},
            },
        )
        created = next(item for item in policy.list_entries(self.owner)["entries"] if item["entry_key"] == entry_key)
        policy.commit(
            self.owner,
            {
                "type": "change_permissions",
                "request_id": str(uuid4()),
                "entry_key": entry_key,
                "expected_access_revision": created["access_revision"],
                "permissions": {"resume_display": True, "visitor_ai": False},
            },
        )
        reviewed = service.review_for_owner(self.owner, {})
        self.assertIsNotNone(reviewed.reviewed)
        result = service.commit(
            self.owner,
            {
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": reviewed.reviewed.digest,
                "slug": "alice",
            },
        )
        self.assertEqual(len(sql.commands), 1)
        self.assertEqual(sql.commands[0][2]["reviewed_digest"], reviewed.reviewed.digest)
        self.assertEqual(result["outcome"], "published")


class _FailingSave:
    def __init__(self, inner):
        self._inner = inner
        self._owners = inner._owners

    def load_owner(self, owner):
        return self._inner.load_owner(owner)

    def save_owner(self, owner, snapshot):
        raise RuntimeError("forced rollback")


class SqlShapedPublicationPort:
    """One production-shaped owner store for both load_owner and commit_command.

    Pairing a memory repository with an unrelated fake SQL port is not SQL-path
    coverage. This port is the configured service repository and sql_repository.
    """

    def __init__(self):
        self._owners = {}
        self.commands = []

    def _empty(self):
        return {
            "sharing_enabled": False,
            "sharing_epoch": 0,
            "publication_revision": 0,
            "current_revision": None,
            "slug": None,
            "publications": {},
            "receipts": {},
            "revoked_media": set(),
            "read_epoch": 0,
        }

    def load_owner(self, owner):
        return copy.deepcopy(self._owners.get(owner) or self._empty())

    def save_owner(self, owner, snapshot):
        raise PublicationStoreUnavailable("SQL snapshot replace is unused")

    def get_receipt(self, owner, request_id):
        item = (self._owners.get(owner) or {}).get("receipts", {}).get(request_id)
        return copy.deepcopy(item) if item is not None else None

    def commit_command(self, owner, request_id, command):
        self.commands.append((owner, request_id, dict(command)))
        snapshot = self._owners.setdefault(owner, self._empty())
        body = {key: value for key, value in command.items() if key != "request_id"}
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        existing = snapshot["receipts"].get(request_id)
        if existing is not None:
            if existing["request_digest"] != digest:
                raise PublicationConflictError(
                    "request_conflict",
                    "That request already used a different payload.",
                )
            return {
                "committed": True,
                "replayed": True,
                "outcome": existing["receipt"]["outcome"],
                "request_digest": existing["request_digest"],
                "read_state": "current",
                "publication_revision": snapshot["publication_revision"],
                "receipt": dict(existing["receipt"]),
            }
        command_type = command.get("type")
        if command_type == "publish":
            snapshot["sharing_enabled"] = True
            snapshot["sharing_epoch"] = int(snapshot.get("sharing_epoch") or 0) + 1
            snapshot["publication_revision"] = int(snapshot.get("publication_revision") or 0) + 1
            snapshot["current_revision"] = snapshot["publication_revision"]
            snapshot["slug"] = command.get("slug")
            snapshot["publications"][snapshot["current_revision"]] = {
                "media": dict(command.get("media") or {}),
                "digest": command.get("reviewed_digest"),
            }
            outcome = "published"
        elif command_type == "sharing_off":
            snapshot["sharing_enabled"] = False
            snapshot["sharing_epoch"] = int(snapshot.get("sharing_epoch") or 0) + 1
            outcome = "restricted"
        else:
            outcome = "applied"
        receipt = {
            "request_id": request_id,
            "request_digest": digest,
            "type": command_type,
            "outcome": outcome,
            "publication_revision": snapshot["publication_revision"],
        }
        snapshot["receipts"][request_id] = {"request_digest": digest, "receipt": receipt}
        return {
            "committed": True,
            "replayed": False,
            "outcome": outcome,
            "request_digest": digest,
            "read_state": "current",
            "publication_revision": snapshot["publication_revision"],
            "receipt": receipt,
        }


class SqlShapedPublicationReplayTests(unittest.TestCase):
    def setUp(self):
        from services.entry_policy_repository import InMemoryEntryPolicyRepository
        from services.entry_policy_service import EntryPolicyService

        self.owner = "member-a"
        self.port = SqlShapedPublicationPort()
        self.policy = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        self.service = ResumePublicationService(
            repository=self.port,
            sql_repository=self.port,
            catalog=InMemoryResumeCatalogRepository(),
        )
        self.service.policy_service = self.policy
        entry_key = str(uuid4())
        self.policy.commit(
            self.owner,
            {
                "type": "create",
                "request_id": str(uuid4()),
                "entry_key": entry_key,
                "canonical_type": "role",
                "values": {
                    "role_title": "Lead",
                    "employer_name": "PeerSlate",
                    "summary": "Led team 0.",
                },
            },
        )
        created = next(
            item
            for item in self.policy.list_entries(self.owner)["entries"]
            if item["entry_key"] == entry_key
        )
        self.policy.commit(
            self.owner,
            {
                "type": "change_permissions",
                "request_id": str(uuid4()),
                "entry_key": entry_key,
                "expected_access_revision": created["access_revision"],
                "permissions": {"resume_display": True, "visitor_ai": False},
            },
        )

    def _reviewed_publish_payload(self, request_id):
        reviewed = self.service.review_for_owner(self.owner, {})
        self.assertIsNotNone(reviewed.reviewed)
        return {
            "type": "publish",
            "request_id": request_id,
            "reviewed_digest": reviewed.reviewed.digest,
            "slug": "alice",
        }

    def test_sql_backed_identical_lost_response_replay_returns_prior_outcome(self):
        request_id = str(uuid4())
        payload = self._reviewed_publish_payload(request_id)
        first = self.service.commit(self.owner, payload)
        self.assertEqual(first["outcome"], "published")
        first_revision = first["publication_revision"]
        first_digest = first["request_digest"]
        replay = self.service.commit(self.owner, dict(payload))
        self.assertTrue(replay.get("replayed"))
        self.assertEqual(replay["outcome"], "published")
        self.assertEqual(replay["publication_revision"], first_revision)
        self.assertEqual(replay["request_digest"], first_digest)
        snapshot = self.port.load_owner(self.owner)
        self.assertEqual(snapshot["publication_revision"], first_revision)
        self.assertEqual(len(snapshot["receipts"]), 1)

    def test_sql_backed_changed_body_replay_conflicts(self):
        request_id = str(uuid4())
        payload = self._reviewed_publish_payload(request_id)
        self.service.commit(self.owner, payload)
        changed = dict(payload)
        changed["slug"] = "bob"
        with self.assertRaises(PublicationConflictError):
            self.service.commit(self.owner, changed)

    def test_historical_publish_receipt_does_not_restore_revoked_availability(self):
        request_id = str(uuid4())
        payload = self._reviewed_publish_payload(request_id)
        first = self.service.commit(self.owner, payload)
        self.service.commit(
            self.owner,
            {"type": "sharing_off", "request_id": str(uuid4())},
        )
        snapshot = self.port.load_owner(self.owner)
        self.assertFalse(snapshot["sharing_enabled"])
        replay = self.service.commit(self.owner, dict(payload))
        self.assertTrue(replay.get("replayed"))
        self.assertEqual(replay["outcome"], first["outcome"])
        after = self.port.load_owner(self.owner)
        self.assertFalse(after["sharing_enabled"])
        self.assertEqual(after["publication_revision"], first["publication_revision"])


if __name__ == "__main__":
    unittest.main()
