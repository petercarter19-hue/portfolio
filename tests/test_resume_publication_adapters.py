"""Trusted E adapters. Review ports never write."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from services.resume_publication_adapters import (
    CatalogGuardedMediaPort,
    SnapshotMediaPort,
    SnapshotPolicyPort,
    policy_snapshot_from_entries,
)
from services.resume_publication_contracts import ReadState
from services.resume_media_catalog_repository import (
    CatalogFenceDenied,
    InMemoryResumeCatalogRepository,
)
from tests.test_resume_publication_contracts import fixture


class ResumePublicationAdapterTests(unittest.TestCase):
    def test_snapshot_ports_fail_closed_on_missing_or_stale_versions(self):
        candidate, policy, media = fixture()
        policy_port = SnapshotPolicyPort(policy)
        self.assertIs(
            policy_port.read_current(candidate.context, candidate.prior.entries).state,
            ReadState.CURRENT,
        )
        self.assertIs(
            policy_port.read_current(candidate.context, ()).state,
            ReadState.STALE,
        )
        unavailable = SnapshotPolicyPort(type(policy)(ReadState.UNAVAILABLE))
        self.assertIs(
            unavailable.read_current(candidate.context, candidate.prior.entries).state,
            ReadState.UNAVAILABLE,
        )

    def test_catalog_guard_denies_withdrawn_generated_media(self):
        candidate, policy, media = fixture(media=True)
        catalog = InMemoryResumeCatalogRepository()
        inner = SnapshotMediaPort(media)
        port = CatalogGuardedMediaPort(inner, catalog)
        snapshot = port.read_current(candidate.context, candidate.placements)
        self.assertIs(snapshot.state, ReadState.CURRENT)
        generated = Mock()
        generated.ref.source_kind = "generated_illustration"
        generated.ref.source_key = "asset-1"
        generated.ref.asset_version = 1
        generated.ref.content_sha256 = "a" * 64
        generated.width = 1
        generated.height = 1
        generated.ready = True
        generated.active = True
        generated_media = type(media)(ReadState.CURRENT, media.versions, (generated,))
        denied = CatalogGuardedMediaPort(SnapshotMediaPort(generated_media), catalog)
        self.assertIs(
            denied.read_current(candidate.context, candidate.placements).state,
            ReadState.DENIED,
        )
        with self.assertRaises(CatalogFenceDenied):
            catalog.get_active("asset-1", 1)

    def test_policy_snapshot_from_entries_requires_access_revision(self):
        with self.assertRaises(KeyError):
            policy_snapshot_from_entries(
                subject_key="member-a",
                resume_key="resume-a",
                draft_revision=1,
                publication_revision=0,
                sharing_epoch=0,
                sharing_enabled=False,
                entries=[{"entry_key": "role:0", "content_token": "1"}],
            )
        snapshot = policy_snapshot_from_entries(
            subject_key="member-a",
            resume_key="resume-a",
            draft_revision=1,
            publication_revision=0,
            sharing_epoch=0,
            sharing_enabled=False,
            entries=[
                {
                    "entry_key": "role:0",
                    "content_token": "1",
                    "access_revision": 2,
                    "values": {"summary": "Led team"},
                    "resume_display": True,
                    "visitor_ai": False,
                    "lifecycle": "active",
                    "private_assistance_excluded": True,
                }
            ],
        )
        self.assertTrue(snapshot.entries[0].private_assistance_excluded)
        self.assertFalse(snapshot.entries[0].visitor_ai_allowed)

    def test_owner_policy_port_reads_list_entries_without_snapshot_load(self):
        from services.entry_policy_repository import InMemoryEntryPolicyRepository
        from services.entry_policy_service import EntryPolicyService
        from services.resume_publication_adapters import OwnerPolicyPort, build_owner_review_candidate
        from uuid import uuid4

        policy = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        owner = "member-a"
        entry_key = str(uuid4())
        policy.commit(
            owner,
            {
                "type": "create",
                "request_id": str(uuid4()),
                "entry_key": entry_key,
                "canonical_type": "role",
                "values": {"role_title": "Lead", "employer_name": "PeerSlate", "summary": "Led team 0."},
            },
        )
        listed = policy.list_entries(owner)["entries"]
        candidate, policy_snapshot, media = build_owner_review_candidate(
            owner=owner,
            resume_key="resume-a",
            draft_revision=0,
            publication_revision=0,
            sharing_epoch=0,
            sharing_enabled=False,
            entries=listed,
        )
        port = OwnerPolicyPort(
            policy,
            resume_key="resume-a",
            draft_revision=0,
            publication_revision=0,
            sharing_epoch=0,
            sharing_enabled=False,
        )
        snapshot = port.read_current(candidate.context, candidate.prior.entries)
        self.assertIs(snapshot.state, ReadState.CURRENT)
        self.assertEqual(snapshot.entries[0].ref.entry_key, entry_key)

    def test_living_resume_catalog_lists_without_sql_snapshot_load(self):
        from services.entry_policy_repository import EntryPolicyStoreUnavailable
        from services.resume_draft_repository import LivingResumeCanonicalCatalog

        class Policy:
            def list_entries(self, owner):
                return [
                    {
                        "entry_key": "role-1",
                        "access_revision": 4,
                        "content_version": 2,
                        "resume_display": False,
                        "visitor_ai": False,
                        "private_assistance_excluded": False,
                    }
                ]

            def load_owner(self, owner):
                raise EntryPolicyStoreUnavailable("unused snapshot")

        class Editor:
            def get_editor(self, owner):
                return {
                    "roles": [
                        {
                            "record_key": "role-1",
                            "row_version": "aa",
                            "editable": True,
                            "role_title": "Lead",
                        }
                    ]
                }

        catalog = LivingResumeCanonicalCatalog(editor=Editor(), policy_repository=Policy())
        items = catalog.list_items("member-a")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["access_revision"], 4)
        self.assertTrue(items[0]["publication_eligible"])
        self.assertEqual(catalog.get_item("member-a", "role-1")["record_key"], "role-1")

        class PolicyMissing:
            def list_entries(self, owner):
                return []

            def load_owner(self, owner):
                raise EntryPolicyStoreUnavailable("unused snapshot")

        empty_policy = LivingResumeCanonicalCatalog(
            editor=Editor(), policy_repository=PolicyMissing()
        )
        listed = empty_policy.list_items("member-a")
        self.assertEqual(len(listed), 1)
        self.assertIsNone(listed[0]["access_revision"])
        self.assertFalse(listed[0]["publication_eligible"])

    def test_living_resume_catalog_accepts_service_list_entries_payload(self):
        from services.resume_draft_repository import LivingResumeCanonicalCatalog

        class Policy:
            def list_entries(self, owner):
                return {
                    "entries": [
                        {
                            "entry_key": "role-1",
                            "access_revision": 3,
                            "content_version": 1,
                            "resume_display": True,
                            "visitor_ai": False,
                            "private_assistance_excluded": False,
                        }
                    ]
                }

        class Editor:
            def get_editor(self, owner):
                return {"roles": [{"record_key": "role-1", "row_version": "aa", "editable": True}]}

        catalog = LivingResumeCanonicalCatalog(editor=Editor(), policy_repository=Policy())
        items = catalog.list_items("member-a")
        self.assertEqual(items[0]["access_revision"], 3)
        self.assertTrue(items[0]["publication_eligible"])


if __name__ == "__main__":
    unittest.main()
