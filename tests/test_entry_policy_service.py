"""Contract tests for entry-policy commands. Mock store only; no live SQL."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import copy
import unittest

from services.entry_policy_repository import InMemoryEntryPolicyRepository
from services.entry_policy_service import (
    COMMAND_TYPES,
    EntryPolicyConflictError,
    EntryPolicyNotFoundError,
    EntryPolicyService,
    EntryPolicyValidationError,
)


def key(n: int) -> str:
    return str(UUID(int=n, version=4))


class Clock:
    def __init__(self):
        self.now = datetime(2026, 9, 11, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


class EntryPolicyServiceTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.service = EntryPolicyService(
            repository=InMemoryEntryPolicyRepository(),
            clock=self.clock,
        )
        self.owner_a = "owner-a"
        self.owner_b = "owner-b"

    def create(self, owner, *, entry=1, canonical_type="role", parent=None, **values):
        payload = {
            "request_id": str(uuid4()),
            "type": "create",
            "entry_key": key(entry) if isinstance(entry, int) else entry,
            "canonical_type": canonical_type,
            "parent_key": key(parent) if isinstance(parent, int) else parent,
            "values": values,
        }
        if payload["parent_key"] is None:
            del payload["parent_key"]
        return self.service.commit(owner, payload)

    def test_two_members_cannot_read_or_mutate_each_other(self):
        self.create(self.owner_a, role_title="Engineer", employer_name="PeerSlate")
        listed = self.service.list_entries(self.owner_b)["entries"]
        self.assertEqual(listed, [])
        with self.assertRaises(EntryPolicyNotFoundError):
            self.service.commit(
                self.owner_b,
                {
                    "request_id": str(uuid4()),
                    "type": "edit",
                    "entry_key": key(1),
                    "expected_content_version": 1,
                    "values": {"role_title": "Stolen", "employer_name": "Other"},
                },
            )

    def test_foreign_and_forged_parents_are_neutral_not_found(self):
        self.create(self.owner_a, role_title="Engineer", employer_name="PeerSlate")
        with self.assertRaises(EntryPolicyNotFoundError):
            self.create(
                self.owner_b,
                entry=2,
                canonical_type="achievement",
                parent=1,
                wording="Forged parent",
            )
        with self.assertRaises(EntryPolicyValidationError):
            self.service.commit(
                self.owner_a,
                {
                    "request_id": str(uuid4()),
                    "type": "create",
                    "entry_key": key(3),
                    "canonical_type": "achievement",
                    "parent_key": "not-a-uuid",
                    "values": {"wording": "Bad parent"},
                },
            )

    def test_all_display_visitor_and_exclusion_combinations(self):
        self.create(self.owner_a, role_title="Engineer", employer_name="PeerSlate")
        combos = [
            (display, visitor, excluded)
            for display in (False, True)
            for visitor in (False, True)
            for excluded in (False, True)
        ]
        access = 1
        for display, visitor, excluded in combos:
            result = self.service.commit(
                self.owner_a,
                {
                    "request_id": str(uuid4()),
                    "type": "change_permissions",
                    "entry_key": key(1),
                    "expected_access_revision": access,
                    "permissions": {
                        "resume_display": display,
                        "visitor_ai": visitor,
                        "private_assistance_excluded": excluded,
                    },
                },
            )
            current = result["entries"][0]
            self.assertEqual(current["resume_display"], display)
            self.assertEqual(current["visitor_ai"], visitor)
            self.assertEqual(current["private_assistance_excluded"], excluded)
            access = current["access_revision"]

    def test_private_exclusion_blocks_assistance_without_changing_display(self):
        self.create(self.owner_a, role_title="Engineer", employer_name="PeerSlate")
        current = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "change_permissions",
                "entry_key": key(1),
                "expected_access_revision": 1,
                "permissions": {"private_assistance_excluded": True},
            },
        )["entries"][0]
        self.assertFalse(current["resume_display"])
        self.assertFalse(current["visitor_ai"])
        self.assertTrue(current["private_assistance_excluded"])

    def test_new_child_stays_private_when_parent_is_displayed(self):
        self.create(self.owner_a, role_title="Engineer", employer_name="PeerSlate")
        self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "change_permissions",
                "entry_key": key(1),
                "expected_access_revision": 1,
                "permissions": {"resume_display": True, "visitor_ai": True},
            },
        )
        child = self.create(
            self.owner_a,
            entry=2,
            canonical_type="achievement",
            parent=1,
            wording="Shipped the adapter",
        )["entries"][0]
        self.assertFalse(child["resume_display"])
        self.assertFalse(child["visitor_ai"])
        self.assertFalse(child["private_assistance_excluded"])
        parent = self.service.get_entry(self.owner_a, key(1))["entry"]
        self.assertTrue(parent["resume_display"])

    def test_standalone_achievement_has_owner_integrity_without_parent(self):
        created = self.create(
            self.owner_a,
            canonical_type="achievement",
            wording="Independent result",
        )["entries"][0]
        self.assertTrue(created["standalone"])
        self.assertIsNone(created["parent_key"])
        with self.assertRaises(EntryPolicyNotFoundError):
            self.create(
                self.owner_b,
                entry=2,
                canonical_type="achievement",
                parent=1,
                wording="Should not attach",
            )

    def test_selected_bulk_permission_change_is_atomic_on_conflict(self):
        self.create(self.owner_a, entry=1, role_title="One", employer_name="A")
        self.create(self.owner_a, entry=2, role_title="Two", employer_name="B")
        with self.assertRaises(EntryPolicyConflictError) as error:
            self.service.commit(
                self.owner_a,
                {
                    "request_id": str(uuid4()),
                    "type": "change_permissions",
                    "entry_key": key(1),
                    "entries": [
                        {
                            "entry_key": key(1),
                            "expected_access_revision": 1,
                            "permissions": {"resume_display": True},
                        },
                        {
                            "entry_key": key(2),
                            "expected_access_revision": 9,
                            "permissions": {"resume_display": True},
                        },
                    ],
                },
            )
        self.assertEqual(error.exception.error_code, "changed")
        listed = {row["entry_key"]: row for row in self.service.list_entries(self.owner_a)["entries"]}
        self.assertFalse(listed[key(1)]["resume_display"])
        self.assertFalse(listed[key(2)]["resume_display"])
        self.assertEqual(listed[key(1)]["access_revision"], 1)
        self.assertEqual(listed[key(2)]["access_revision"], 1)

    def test_delete_restore_and_expiry_keep_private_restore_defaults(self):
        self.create(self.owner_a, role_title="Engineer", employer_name="PeerSlate")
        self.create(
            self.owner_a,
            entry=2,
            canonical_type="achievement",
            parent=1,
            wording="Linked result",
        )
        self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "change_permissions",
                "entry_key": key(1),
                "expected_access_revision": 1,
                "permissions": {
                    "resume_display": True,
                    "visitor_ai": True,
                    "private_assistance_excluded": True,
                },
            },
        )
        with self.assertRaises(EntryPolicyConflictError) as error:
            self.service.commit(
                self.owner_a,
                {
                    "request_id": str(uuid4()),
                    "type": "delete",
                    "entry_key": key(1),
                    "expected_content_version": 1,
                    "expected_access_revision": 2,
                    "dependent_keys": [],
                },
            )
        self.assertEqual(error.exception.error_code, "scope_changed")
        deleted = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "delete",
                "entry_key": key(1),
                "expected_content_version": 1,
                "expected_access_revision": 2,
                "dependent_keys": [key(2)],
            },
        )["entries"]
        self.assertEqual(len(deleted), 2)
        self.assertTrue(all(item["lifecycle"] == "deleted" for item in deleted))
        restored = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "restore",
                "entry_key": key(1),
                "expected_access_revision": 3,
            },
        )["entries"]
        by_key = {item["entry_key"]: item for item in restored}
        self.assertFalse(by_key[key(1)]["resume_display"])
        self.assertFalse(by_key[key(1)]["visitor_ai"])
        self.assertTrue(by_key[key(1)]["private_assistance_excluded"])
        self.assertFalse(by_key[key(2)]["resume_display"])
        self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "delete",
                "entry_key": key(1),
                "expected_content_version": 1,
                "expected_access_revision": by_key[key(1)]["access_revision"],
                "dependent_keys": [key(2)],
            },
        )
        self.clock.now = self.clock.now + timedelta(days=30)
        swept = self.service.sweep_expired(self.owner_a)
        self.assertGreaterEqual(swept["expired_count"], 1)
        with self.assertRaises(EntryPolicyNotFoundError):
            self.service.commit(
                self.owner_a,
                {
                    "request_id": str(uuid4()),
                    "type": "restore",
                    "entry_key": key(1),
                    "expected_access_revision": 1,
                },
            )

    def test_present_exposes_the_lifecycle_timestamp(self):
        self.create(self.owner_a, role_title="Engineer", employer_name="PeerSlate")
        created = self.service.get_entry(self.owner_a, key(1))["entry"]
        self.assertIsNone(created["deleted_at"])
        deleted = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "delete",
                "entry_key": key(1),
                "expected_content_version": 1,
                "expected_access_revision": 1,
                "dependent_keys": [],
            },
        )["entries"][0]
        self.assertEqual(deleted["lifecycle"], "deleted")
        self.assertEqual(deleted["deleted_at"], "2026-09-11T00:00:00Z")
        # Deleting never rewrites the content timestamps.
        self.assertEqual(deleted["updated_at"], created["updated_at"])
        restored = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "restore",
                "entry_key": key(1),
                "expected_access_revision": 2,
            },
        )["entries"][0]
        self.assertIsNone(restored["deleted_at"])

    def test_unknown_command_is_refused_before_storage(self):
        store = InMemoryEntryPolicyRepository()
        service = EntryPolicyService(repository=store, clock=self.clock)
        with self.assertRaises(EntryPolicyValidationError):
            service.commit(
                self.owner_a,
                {
                    "request_id": str(uuid4()),
                    "type": "publish",
                    "entry_key": key(1),
                },
            )
        self.assertEqual(store.load_owner(self.owner_a)["entries"], {})

    def test_same_key_same_payload_replays_and_changed_payload_conflicts(self):
        request_id = str(uuid4())
        payload = {
            "request_id": request_id,
            "type": "create",
            "entry_key": key(1),
            "canonical_type": "project",
            "values": {"project_name": "Adapter", "project_status": "in_progress"},
        }
        first = self.service.commit(self.owner_a, payload)
        replay = self.service.commit(self.owner_a, payload)
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"]["request_digest"], first["receipt"]["request_digest"])
        with self.assertRaises(EntryPolicyConflictError) as error:
            self.service.commit(
                self.owner_a,
                {**payload, "values": {"project_name": "Different", "project_status": "completed"}},
            )
        self.assertEqual(error.exception.error_code, "request_conflict")
        self.assertEqual(len(self.service.list_entries(self.owner_a)["entries"]), 1)

    def test_stale_content_and_policy_versions_cannot_restore_revoked_grants(self):
        self.create(self.owner_a, role_title="Engineer", employer_name="PeerSlate")
        self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "change_permissions",
                "entry_key": key(1),
                "expected_access_revision": 1,
                "permissions": {"resume_display": True, "visitor_ai": True},
            },
        )
        self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "edit",
                "entry_key": key(1),
                "expected_content_version": 1,
                "values": {"role_title": "Staff engineer", "employer_name": "PeerSlate"},
            },
        )
        self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "change_permissions",
                "entry_key": key(1),
                "expected_access_revision": 2,
                "permissions": {"resume_display": False, "visitor_ai": False},
            },
        )
        with self.assertRaises(EntryPolicyConflictError):
            self.service.commit(
                self.owner_a,
                {
                    "request_id": str(uuid4()),
                    "type": "edit",
                    "entry_key": key(1),
                    "expected_content_version": 1,
                    "values": {"role_title": "Stale draft", "employer_name": "PeerSlate"},
                },
            )
        with self.assertRaises(EntryPolicyConflictError):
            self.service.commit(
                self.owner_a,
                {
                    "request_id": str(uuid4()),
                    "type": "change_permissions",
                    "entry_key": key(1),
                    "expected_access_revision": 2,
                    "permissions": {"resume_display": True, "visitor_ai": True},
                },
            )
        current = self.service.get_entry(self.owner_a, key(1))["entry"]
        self.assertEqual(current["values"]["role_title"], "Staff engineer")
        self.assertFalse(current["resume_display"])
        self.assertFalse(current["visitor_ai"])

    def test_direct_correction_does_not_require_an_ai_provider(self):
        capabilities = self.service.list_entries(self.owner_a)["capabilities"]
        self.assertFalse(capabilities["ai_provider_required"])
        self.assertEqual(set(capabilities["commands"]), COMMAND_TYPES)
        self.create(self.owner_a, role_title="Engineer", employer_name="PeerSlate")
        updated = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "edit",
                "entry_key": key(1),
                "expected_content_version": 1,
                "values": {"role_title": "Corrected", "employer_name": "PeerSlate"},
            },
        )["entries"][0]
        self.assertEqual(updated["values"]["role_title"], "Corrected")

    def test_client_cannot_supply_owner_or_permission_fields_on_create(self):
        with self.assertRaises(EntryPolicyValidationError):
            self.service.commit(
                self.owner_a,
                {
                    "request_id": str(uuid4()),
                    "type": "create",
                    "entry_key": key(1),
                    "canonical_type": "role",
                    "owner_user_key": self.owner_b,
                    "values": {"role_title": "Engineer", "employer_name": "PeerSlate"},
                },
            )
        with self.assertRaises(EntryPolicyValidationError):
            self.create(
                self.owner_a,
                role_title="Engineer",
                employer_name="PeerSlate",
                resume_display=True,
            )

    def test_resolve_match_equivalent_updates_canonical_without_granting_permissions(self):
        original = self.create(
            self.owner_a,
            entry=1,
            canonical_type="knowledge",
            title="About me",
            wording="First version",
            classification="personal",
        )["entries"][0]
        candidate = self.create(
            self.owner_a,
            entry=2,
            canonical_type="knowledge",
            title="About me",
            wording="Corrected wording",
            classification="personal",
        )["entries"][0]
        result = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "resolve_match",
                "entry_key": key(1),
                "candidate_key": key(2),
                "match_decision": "equivalent",
                "expected_content_version": original["content_version"],
            },
        )
        current = result["entries"][0]
        self.assertEqual(current["values"]["wording"], "Corrected wording")
        self.assertFalse(current["resume_display"])
        self.assertEqual(result["match"]["decision"], "equivalent")

    def test_resolve_match_equivalent_with_identical_values_stays_quiet(self):
        original = self.create(
            self.owner_a,
            entry=1,
            canonical_type="knowledge",
            title="About me",
            wording="Same wording",
            classification="personal",
        )["entries"][0]
        self.create(
            self.owner_a,
            entry=2,
            canonical_type="knowledge",
            title="About me",
            wording="Same wording",
            classification="personal",
        )
        self.clock.now = self.clock.now + timedelta(hours=1)
        current = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "resolve_match",
                "entry_key": key(1),
                "candidate_key": key(2),
                "match_decision": "equivalent",
                "expected_content_version": original["content_version"],
            },
        )["entries"][0]
        # Established contract holds: values adopted, version moves, no
        # permission grants. But nothing changed, so updated_at stays put
        # and Activity keeps reading this entry as added, not corrected.
        self.assertEqual(current["values"]["wording"], "Same wording")
        self.assertEqual(
            current["content_version"], original["content_version"] + 1
        )
        self.assertFalse(current["resume_display"])
        self.assertEqual(current["updated_at"], original["updated_at"])
        self.assertEqual(current["updated_at"], current["created_at"])

    def test_resolve_match_equivalent_with_new_values_moves_updated(self):
        original = self.create(
            self.owner_a,
            entry=1,
            canonical_type="knowledge",
            title="About me",
            wording="First version",
            classification="personal",
        )["entries"][0]
        self.create(
            self.owner_a,
            entry=2,
            canonical_type="knowledge",
            title="About me",
            wording="Corrected wording",
            classification="personal",
        )
        self.clock.now = self.clock.now + timedelta(hours=1)
        current = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "resolve_match",
                "entry_key": key(1),
                "candidate_key": key(2),
                "match_decision": "equivalent",
                "expected_content_version": original["content_version"],
            },
        )["entries"][0]
        self.assertEqual(current["values"]["wording"], "Corrected wording")
        self.assertNotEqual(current["updated_at"], original["updated_at"])
        self.assertNotEqual(current["updated_at"], current["created_at"])

    def test_recategorize_and_permanent_delete_are_closed_owner_commands(self):
        created = self.create(
            self.owner_a,
            canonical_type="knowledge",
            title="About me",
            wording="Private note",
            classification="personal",
        )["entries"][0]
        moved = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "recategorize",
                "entry_key": key(1),
                "expected_content_version": created["content_version"],
                "category": "personal",
            },
        )["entries"][0]
        self.assertEqual(moved["category"], "personal")
        self.assertEqual(moved["content_version"], created["content_version"] + 1)
        deleted = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "delete",
                "entry_key": key(1),
                "expected_content_version": moved["content_version"],
                "expected_access_revision": moved["access_revision"],
                "dependent_keys": [],
            },
        )["entries"][0]
        self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "permanently_delete",
                "entry_key": key(1),
                "expected_access_revision": deleted["access_revision"],
            },
        )
        with self.assertRaises(EntryPolicyNotFoundError):
            self.service.get_entry(self.owner_a, key(1))
        with self.assertRaises(EntryPolicyNotFoundError):
            self.service.get_entry(self.owner_b, key(1))

    def test_create_stamps_created_and_updated_together(self):
        created = self.create(
            self.owner_a, role_title="Engineer", employer_name="PeerSlate"
        )["entries"][0]

        self.assertEqual(created["created_at"], "2026-09-11T00:00:00Z")
        self.assertEqual(created["updated_at"], "2026-09-11T00:00:00Z")

    def test_direct_correction_moves_updated_but_keeps_created(self):
        created = self.create(
            self.owner_a, role_title="Engineer", employer_name="PeerSlate"
        )["entries"][0]
        self.clock.now = datetime(2026, 9, 12, 12, 30, tzinfo=timezone.utc)
        updated = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "edit",
                "entry_key": key(1),
                "expected_content_version": created["content_version"],
                "values": {"role_title": "Senior Engineer", "employer_name": "PeerSlate"},
            },
        )["entries"][0]

        self.assertEqual(updated["created_at"], "2026-09-11T00:00:00Z")
        self.assertEqual(updated["updated_at"], "2026-09-12T12:30:00Z")

    def test_recategorize_moves_updated_but_keeps_created(self):
        created = self.create(
            self.owner_a,
            canonical_type="knowledge",
            title="About me",
            wording="Private note",
            classification="personal",
        )["entries"][0]
        self.clock.now = datetime(2026, 9, 12, tzinfo=timezone.utc)
        moved = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "recategorize",
                "entry_key": key(1),
                "expected_content_version": created["content_version"],
                "category": "personal",
            },
        )["entries"][0]

        self.assertEqual(moved["created_at"], "2026-09-11T00:00:00Z")
        self.assertEqual(moved["updated_at"], "2026-09-12T00:00:00Z")

    def test_sharing_and_lifecycle_changes_do_not_read_as_corrections(self):
        created = self.create(
            self.owner_a, role_title="Engineer", employer_name="PeerSlate"
        )["entries"][0]
        self.clock.now = datetime(2026, 9, 12, tzinfo=timezone.utc)
        shared = self.service.commit(
            self.owner_a,
            {
                "request_id": str(uuid4()),
                "type": "change_permissions",
                "entry_key": key(1),
                "expected_access_revision": created["access_revision"],
                "permissions": {"resume_display": True},
            },
        )["entries"][0]

        self.assertTrue(shared["resume_display"])
        self.assertEqual(shared["updated_at"], "2026-09-11T00:00:00Z")

    def test_legacy_entries_without_stamps_stay_readable(self):
        repository = self.service.repository
        snapshot = repository.load_owner(self.owner_a)
        snapshot["entries"][key(9)] = {
            "entry_key": key(9),
            "canonical_type": "role",
            "category": "experience",
            "parent_key": None,
            "content_version": 1,
            "access_revision": 1,
            "resume_display": False,
            "visitor_ai": False,
            "private_assistance_excluded": False,
            "lifecycle": "active",
            "deleted_at": None,
            "recover_until": None,
            "values": {"role_title": "Legacy", "employer_name": "PeerSlate"},
        }
        repository.save_owner(self.owner_a, snapshot)

        listed = self.service.list_entries(self.owner_a)["entries"]

        self.assertEqual(len(listed), 1)
        self.assertIsNone(listed[0]["created_at"])
        self.assertIsNone(listed[0]["updated_at"])

    def test_sql_adapter_stays_fail_closed_against_the_current_allowlist(self):
        from services.entry_policy_repository import (
            EntryPolicyStoreUnavailable,
            SqlEntryPolicyRepository,
        )

        repository = SqlEntryPolicyRepository()
        with self.assertRaises(EntryPolicyStoreUnavailable):
            repository.load_owner(self.owner_a)
        with self.assertRaises(EntryPolicyStoreUnavailable):
            repository.save_owner(self.owner_a, {"entries": {}, "receipts": {}, "match_decisions": {}})

    def test_publication_linked_write_updates_guest_without_split_store(self):
        from services.resume_publication_service import memory_resume_publication_service

        publication = memory_resume_publication_service()
        publication.bind_slug(self.owner_a, "alice")
        service = EntryPolicyService(
            repository=InMemoryEntryPolicyRepository(),
            clock=self.clock,
            publication_service=publication,
        )
        publication.policy_service = service
        entry = key(21)
        service.commit(
            self.owner_a,
            {
                "type": "create",
                "request_id": str(uuid4()),
                "entry_key": entry,
                "canonical_type": "role",
                "values": {"role_title": "Lead", "employer_name": "PeerSlate", "summary": "Led team 0."},
            },
        )
        listed = service.list_entries(self.owner_a)["entries"]
        created = next(item for item in listed if item["entry_key"] == entry)
        service.commit(
            self.owner_a,
            {
                "type": "change_permissions",
                "request_id": str(uuid4()),
                "entry_key": entry,
                "expected_access_revision": created["access_revision"],
                "permissions": {"resume_display": True, "visitor_ai": False},
            },
        )
        reviewed = publication.review_for_owner(self.owner_a, {})
        self.assertIsNotNone(reviewed.reviewed)
        publication.commit(
            self.owner_a,
            {
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": reviewed.reviewed.digest,
                "slug": "alice",
            },
        )
        edited = service.get_entry(self.owner_a, entry)["entry"]
        service.commit(
            self.owner_a,
            {
                "type": "edit",
                "request_id": str(uuid4()),
                "entry_key": entry,
                "expected_content_version": edited["content_version"],
                "values": {
                    "role_title": "Lead",
                    "employer_name": "PeerSlate",
                    "summary": "Led a larger team.",
                },
            },
        )
        guest = publication.guest_read(slug="alice")
        self.assertEqual(guest["display"][entry]["wording"]["summary"], "Led a larger team.")
        self.assertNotIn("visitor_ai", guest)

    def test_publication_linked_write_restores_both_stores_together(self):
        from services.resume_publication_service import memory_resume_publication_service

        class FailingPolicy:
            def __init__(self, inner):
                self.inner = inner
                self.saved = []

            def save_owner(self, owner, snapshot):
                self.saved.append(copy.deepcopy(snapshot))
                if len(self.saved) == 1:
                    raise RuntimeError("forced linked-write failure")
                self.inner.save_owner(owner, snapshot)

            def load_owner(self, owner):
                return self.inner.load_owner(owner)

        publication = memory_resume_publication_service()
        publication.bind_slug(self.owner_a, "alice")
        inner = InMemoryEntryPolicyRepository()
        failing = FailingPolicy(inner)
        service = EntryPolicyService(
            repository=failing,
            clock=self.clock,
            publication_service=publication,
        )
        publication.policy_service = service
        with self.assertRaises(RuntimeError):
            service.commit(
                self.owner_a,
                {
                    "type": "create",
                    "request_id": str(uuid4()),
                    "entry_key": key(22),
                    "canonical_type": "role",
                    "values": {"role_title": "Lead", "employer_name": "PeerSlate", "summary": "Led team 0."},
                },
            )
        self.assertEqual(inner.load_owner(self.owner_a)["entries"], {})
        self.assertIsNone(publication.repository.load_owner(self.owner_a).get("current_revision"))


if __name__ == "__main__":
    unittest.main()
