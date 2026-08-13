from __future__ import annotations
from dataclasses import replace
import unittest

from services.profile_core_service import ProfileNotFound, ProfileUnavailableError
from services.profile_relationship_service import ProfileRelationshipService, ProfileRelationshipSnapshot


class Reader:
    def __init__(self, value): self.value = value
    def current_snapshot(self, **kwargs): return self.value


class ProfileRelationshipTests(unittest.TestCase):
    def test_only_active_unblocked_exact_pair_is_eligible(self):
        value = ProfileRelationshipSnapshot(
            "viewerAlpha_123", "ownerBravo_456", "connected", "relationV_123", "blockEpoch_123", False
        )
        self.assertEqual(ProfileRelationshipService(Reader(value)).require_connection(
            actor_key="viewerAlpha_123", subject_owner_key="ownerBravo_456"), value)

    def test_block_precedence_and_missing_dependency_fail_closed(self):
        blocked = ProfileRelationshipSnapshot(
            "viewerAlpha_123", "ownerBravo_456", "connected", "relationV_123", "blockEpoch_123", True
        )
        with self.assertRaises(ProfileNotFound):
            ProfileRelationshipService(Reader(blocked)).require_connection(
                actor_key="viewerAlpha_123", subject_owner_key="ownerBravo_456")
        with self.assertRaises(ProfileUnavailableError):
            ProfileRelationshipService(None).require_connection(
                actor_key="viewerAlpha_123", subject_owner_key="ownerBravo_456")

    def test_hostile_relationship_field_types_fail_neutrally(self):
        valid = ProfileRelationshipSnapshot(
            "viewerAlpha_123", "ownerBravo_456", "connected",
            "relationV_123", "blockEpoch_123", False,
        )
        for field, hostile in (
            ("actor_key", None), ("subject_owner_key", 7), ("state", []),
            ("relationship_version", object()), ("block_epoch", {"epoch"}),
            ("blocked_either_direction", 0),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ProfileNotFound):
                    ProfileRelationshipService(Reader(replace(valid, **{field: hostile}))).require_connection(
                        actor_key="viewerAlpha_123", subject_owner_key="ownerBravo_456")

        with self.assertRaises(ProfileNotFound):
            ProfileRelationshipService(Reader(valid)).require_connection(
                actor_key=None, subject_owner_key="ownerBravo_456")


if __name__ == "__main__": unittest.main()
