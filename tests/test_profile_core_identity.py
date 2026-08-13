from __future__ import annotations

from dataclasses import replace
import unittest

from services.profile_core_service import ProfileNotFound, ProfileUnavailableError
from services.profile_identity_service import (
    InMemoryProfileIdentityDirectory,
    ProfileIdentityRecord,
    ProfileIdentityService,
    TrustedActorIdentity,
)


class FailingDirectory:
    def profile_for_actor(self, identity):
        raise RuntimeError("database unavailable")

    def profile_for_slug(self, slug):
        raise RuntimeError("database unavailable")


class ProfileIdentityServiceTests(unittest.TestCase):
    def setUp(self):
        self.actor = TrustedActorIdentity("issuer.example", "subject-avery")
        self.record = ProfileIdentityRecord("ownerAlpha_123", "avery", True, "authEpoch_123")
        self.service = ProfileIdentityService(
            InMemoryProfileIdentityDirectory({("issuer.example", "subject-avery"): self.record})
        )

    def test_owner_context_is_derived_from_trusted_identity(self):
        context = self.service.owner_context(self.actor, purpose="html")
        self.assertTrue(context.is_owner)
        self.assertEqual(context.profile_slug, "avery")

    def test_public_context_is_anonymous_and_exact_slug(self):
        context = self.service.public_context(slug="avery")
        self.assertIsNone(context.actor_key)
        self.assertEqual(context.subject_owner_key, "ownerAlpha_123")

    def test_malformed_cross_shaped_directory_record_fails_neutrally(self):
        service = ProfileIdentityService(InMemoryProfileIdentityDirectory({
            ("issuer.example", "subject-avery"): ProfileIdentityRecord(
                "other", "avery", True, "authEpoch_123"
            )
        }))
        with self.assertRaises(ProfileNotFound):
            service.owner_context(self.actor, purpose="api")

    def test_dependency_failure_is_not_treated_as_missing_identity(self):
        service = ProfileIdentityService(FailingDirectory())
        with self.assertRaises(ProfileUnavailableError):
            service.public_context(slug="avery")

    def test_hostile_directory_field_types_fail_neutrally(self):
        for field, hostile in (
            ("owner_key", None), ("slug", 8), ("active", 1), ("auth_epoch", []),
        ):
            with self.subTest(field=field):
                record = replace(self.record, **{field: hostile})
                service = ProfileIdentityService(
                    InMemoryProfileIdentityDirectory({("issuer.example", "subject-avery"): record})
                )
                with self.assertRaises(ProfileNotFound):
                    service.owner_context(self.actor, purpose="api")


if __name__ == "__main__":
    unittest.main()
