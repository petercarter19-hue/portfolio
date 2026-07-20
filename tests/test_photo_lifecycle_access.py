from datetime import datetime, timedelta, timezone
import unittest

from app import app
from identity import PeerSlateIdentity
from services.photo_lifecycle_access_service import (
    PHOTO_ACCESS_INVALID,
    PHOTO_ACCESS_OFF,
    PHOTO_ACCESS_ORDINARY,
    PHOTO_ACCESS_PROOF,
    PhotoLifecycleAccessService,
)


OWNER_A = PeerSlateIdentity(
    user_key="owner-a",
    auth_provider="aad",
    auth_issuer="https://issuer.example/",
    auth_subject="subject-a",
    email="owner-a@example.test",
)
OWNER_B = PeerSlateIdentity(
    user_key="owner-b",
    auth_provider="aad",
    auth_issuer="https://issuer.example/",
    auth_subject="subject-b",
    email="owner-b@example.test",
)
OUTSIDER = PeerSlateIdentity(
    user_key="owner-c",
    auth_provider="aad",
    auth_issuer="https://issuer.example/",
    auth_subject="subject-c",
    email="owner-a@example.test",
)
CONFIG_NAMES = (
    "CAPTURE_PHOTO_ENABLED",
    "CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED",
    "CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS",
    "CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC",
    "CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID",
)


class PhotoLifecycleAccessServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = PhotoLifecycleAccessService()
        self.now = datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc)
        self.original = {
            name: (name in app.config, app.config.get(name)) for name in CONFIG_NAMES
        }
        app.config.update(
            CAPTURE_PHOTO_ENABLED=False,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=False,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS="",
            CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC="",
            CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID="",
        )
        self.context = app.app_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()
        for name, (existed, value) in self.original.items():
            if existed:
                app.config[name] = value
            else:
                app.config.pop(name, None)

    def enable_proof(self, *, expiry=None, keys="owner-a, owner-b", run_id=""):
        app.config.update(
            CAPTURE_PHOTO_ENABLED=False,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=True,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS=keys,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC=(
                expiry or self.now + timedelta(hours=1)
            ).isoformat().replace("+00:00", "Z"),
            CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID=run_id,
        )

    def test_both_flags_off_is_unavailable(self):
        configuration = self.service.configuration(self.now)

        self.assertEqual(configuration.mode, PHOTO_ACCESS_OFF)
        self.assertFalse(self.service.allows_identity(OWNER_A, configuration))

    def test_ordinary_release_preserves_signed_in_member_access(self):
        app.config["CAPTURE_PHOTO_ENABLED"] = True

        configuration = self.service.configuration(self.now)

        self.assertEqual(configuration.mode, PHOTO_ACCESS_ORDINARY)
        self.assertTrue(self.service.allows_identity(OWNER_A, configuration))
        self.assertTrue(self.service.allows_identity(OUTSIDER, configuration))

    def test_two_enabled_flags_fail_closed(self):
        self.enable_proof()
        app.config["CAPTURE_PHOTO_ENABLED"] = True

        configuration = self.service.configuration(self.now)

        self.assertEqual(configuration.mode, PHOTO_ACCESS_INVALID)
        self.assertFalse(self.service.allows_identity(OWNER_A, configuration))

    def test_proof_allows_only_exact_server_resolved_internal_keys(self):
        self.enable_proof(run_id="PS-CAPTURE-PHOTO-LIFECYCLE-001-run-1")

        configuration = self.service.configuration(self.now)

        self.assertEqual(configuration.mode, PHOTO_ACCESS_PROOF)
        self.assertTrue(self.service.allows_identity(OWNER_A, configuration))
        self.assertTrue(self.service.allows_identity(OWNER_B, configuration))
        self.assertFalse(self.service.allows_identity(OUTSIDER, configuration))
        self.assertEqual(
            configuration.run_id, "PS-CAPTURE-PHOTO-LIFECYCLE-001-run-1"
        )

    def test_email_never_grants_proof_access(self):
        self.enable_proof()
        configuration = self.service.configuration(self.now)

        self.assertEqual(OUTSIDER.email, OWNER_A.email)
        self.assertFalse(self.service.allows_identity(OUTSIDER, configuration))

    def test_invalid_cohort_shapes_fail_closed(self):
        for keys in (
            "owner-a",
            "owner-a owner-a",
            "owner-a,owner-b,owner-c",
            "owner-a,owner@example.test",
            "owner-a,bad/key",
            f"owner-a,{'x' * 201}",
        ):
            with self.subTest(keys=keys):
                self.enable_proof(keys=keys)
                self.assertEqual(
                    self.service.configuration(self.now).mode,
                    PHOTO_ACCESS_INVALID,
                )

    def test_expiry_must_be_future_utc_and_no_more_than_two_hours(self):
        invalid_expiries = (
            "",
            "not-a-date",
            "2026-07-20T16:00:00",
            "2026-07-20T16:00:00+01:00",
            (self.now - timedelta(seconds=1)).isoformat(),
            (self.now + timedelta(hours=2, seconds=1)).isoformat(),
        )
        for expiry in invalid_expiries:
            with self.subTest(expiry=expiry):
                app.config.update(
                    CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=True,
                    CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS="owner-a,owner-b",
                    CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC=expiry,
                )
                self.assertEqual(
                    self.service.configuration(self.now).mode,
                    PHOTO_ACCESS_INVALID,
                )

        self.enable_proof(expiry=self.now + timedelta(hours=2))
        self.assertEqual(self.service.configuration(self.now).mode, PHOTO_ACCESS_PROOF)

    def test_expired_configuration_fails_closed_without_operator_action(self):
        self.enable_proof(expiry=self.now + timedelta(minutes=5))

        self.assertEqual(
            self.service.configuration(self.now + timedelta(minutes=6)).mode,
            PHOTO_ACCESS_INVALID,
        )

    def test_invalid_optional_run_id_fails_closed(self):
        self.enable_proof(run_id="contains a space")

        self.assertEqual(
            self.service.configuration(self.now).mode,
            PHOTO_ACCESS_INVALID,
        )

    def test_disabled_proof_ignores_stale_cohort_values(self):
        app.config.update(
            CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=False,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS="stale-owner-a,stale-owner-b",
            CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC="invalid",
        )

        self.assertEqual(self.service.configuration(self.now).mode, PHOTO_ACCESS_OFF)


if __name__ == "__main__":
    unittest.main()
