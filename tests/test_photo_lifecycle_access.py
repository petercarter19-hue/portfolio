from datetime import datetime, timedelta, timezone
import logging
import unittest
from unittest.mock import patch

from app import app
from identity import PeerSlateIdentity
from services.photo_lifecycle_access_service import (
    PHOTO_ACCESS_INVALID,
    PHOTO_ACCESS_OFF,
    PHOTO_ACCESS_ORDINARY,
    PHOTO_ACCESS_PROOF,
    PROOF_ADMISSION_UNSET_RUN_ID,
    PhotoLifecycleAccessService,
    photo_lifecycle_access_service,
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


class _RecordingHandler(logging.Handler):
    """Collect every record the application logger emits during one test."""

    def __init__(self):
        super().__init__(level=logging.NOTSET)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class PhotoLifecycleProofAuditTests(unittest.TestCase):
    """The proof window must leave a positive, identity-free server record.

    Without this line an attended production proof window would leave no
    server-side evidence that proof mode was active or that a cohort member was
    actually admitted, because every other Photo log call is an error branch.
    """

    RUN_ID = "PS-CAPTURE-PHOTO-LIFECYCLE-001-run-7"
    FORBIDDEN_FRAGMENTS = (
        "owner-a",
        "owner-b",
        "owner-c",
        "example.test",
        "cohort",
        "expires",
        "2026-07-20T",
    )

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
        self.handler = _RecordingHandler()
        app.logger.addHandler(self.handler)

    def tearDown(self):
        app.logger.removeHandler(self.handler)
        self.context.pop()
        for name, (existed, value) in self.original.items():
            if existed:
                app.config[name] = value
            else:
                app.config.pop(name, None)

    def enable_proof(self, *, expiry=None, keys="owner-a, owner-b", run_id=None):
        app.config.update(
            CAPTURE_PHOTO_ENABLED=False,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=True,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS=keys,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC=(
                expiry or self.now + timedelta(hours=1)
            ).isoformat().replace("+00:00", "Z"),
            CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID=(
                self.RUN_ID if run_id is None else run_id
            ),
        )

    def admit(self, identity=OWNER_A):
        configuration = self.service.configuration(self.now)
        return self.service.allows_identity(identity, configuration)

    @property
    def audit_records(self):
        return [
            record
            for record in self.handler.records
            if "proof admission" in record.getMessage()
        ]

    def test_proof_admission_writes_one_audit_record(self):
        self.enable_proof()

        self.assertTrue(self.admit())

        self.assertEqual(len(self.audit_records), 1)
        record = self.audit_records[0]
        self.assertEqual(record.levelno, logging.WARNING)
        self.assertEqual(
            record.getMessage(),
            "PeerSlate Photo lifecycle proof admission. "
            f"access_mode=proof run_id={self.RUN_ID}",
        )

    def test_audit_record_carries_no_user_key_or_configuration_value(self):
        self.enable_proof()

        self.assertTrue(self.admit(OWNER_A))
        self.assertTrue(self.admit(OWNER_B))

        rendered = " | ".join(record.getMessage() for record in self.audit_records)
        arguments = [
            str(value)
            for record in self.audit_records
            for value in (record.args or ())
        ]
        self.assertTrue(rendered)
        for fragment in self.FORBIDDEN_FRAGMENTS:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, rendered)
                self.assertNotIn(fragment, " | ".join(arguments))
        self.assertEqual(set(arguments), {PHOTO_ACCESS_PROOF, self.RUN_ID})

    def test_off_mode_writes_no_audit_record(self):
        self.assertEqual(self.service.configuration(self.now).mode, PHOTO_ACCESS_OFF)
        self.assertFalse(self.admit())

        self.assertEqual(self.audit_records, [])

    def test_invalid_mode_writes_no_audit_record(self):
        cases = {
            "both flags true": lambda: app.config.update(CAPTURE_PHOTO_ENABLED=True),
            "expired window": lambda: self.enable_proof(
                expiry=self.now - timedelta(minutes=1)
            ),
            "malformed cohort": lambda: self.enable_proof(keys="owner-a"),
            "malformed run id": lambda: self.enable_proof(run_id="contains a space"),
        }
        for label, arrange in cases.items():
            with self.subTest(case=label):
                self.enable_proof()
                arrange()
                self.assertEqual(
                    self.service.configuration(self.now).mode, PHOTO_ACCESS_INVALID
                )
                self.assertFalse(self.admit())

        self.assertEqual(self.audit_records, [])

    def test_ordinary_release_writes_no_proof_audit_record(self):
        app.config["CAPTURE_PHOTO_ENABLED"] = True

        self.assertEqual(
            self.service.configuration(self.now).mode, PHOTO_ACCESS_ORDINARY
        )
        self.assertTrue(self.admit())

        self.assertEqual(self.audit_records, [])

    def test_non_cohort_denial_writes_no_audit_record(self):
        self.enable_proof()

        self.assertFalse(self.admit(OUTSIDER))

        self.assertEqual(self.audit_records, [])

    def test_one_window_records_once_however_many_requests_it_admits(self):
        self.enable_proof()

        for _ in range(5):
            self.assertTrue(self.admit(OWNER_A))
            self.assertTrue(self.admit(OWNER_B))

        self.assertEqual(len(self.audit_records), 1)

    def test_a_second_window_is_never_attributed_to_the_first(self):
        self.enable_proof()
        self.assertTrue(self.admit())

        self.enable_proof(
            expiry=self.now + timedelta(minutes=30),
            run_id="PS-CAPTURE-PHOTO-LIFECYCLE-001-run-8",
        )
        self.assertTrue(self.admit())

        self.assertEqual(len(self.audit_records), 2)
        self.assertIn("run_id=PS-CAPTURE-PHOTO-LIFECYCLE-001-run-8", self.audit_records[1].getMessage())

    def test_optional_run_id_absent_is_recorded_as_unset(self):
        self.enable_proof(run_id="")

        self.assertTrue(self.admit())

        self.assertEqual(len(self.audit_records), 1)
        self.assertIn(
            f"run_id={PROOF_ADMISSION_UNSET_RUN_ID}",
            self.audit_records[0].getMessage(),
        )

    def test_reset_audit_state_allows_a_fresh_announcement(self):
        self.enable_proof()
        self.assertTrue(self.admit())
        self.assertTrue(self.admit())
        self.assertEqual(len(self.audit_records), 1)

        self.service.reset_audit_state()
        self.assertTrue(self.admit())

        self.assertEqual(len(self.audit_records), 2)


class PhotoLifecycleProofAuditRouteTests(unittest.TestCase):
    """Prove the audit record reaches the log through a real Photo request."""

    def setUp(self):
        self.original = {
            name: (name in app.config, app.config.get(name)) for name in CONFIG_NAMES
        }
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        app.config.update(
            TESTING=True,
            CAPTURE_PHOTO_ENABLED=False,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED=True,
            CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS="owner-a,owner-b",
            CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC=expiry.isoformat().replace(
                "+00:00", "Z"
            ),
            CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID="PS-CAPTURE-PHOTO-LIFECYCLE-001-route",
        )
        self.client = app.test_client()
        self.handler = _RecordingHandler()
        app.logger.addHandler(self.handler)
        photo_lifecycle_access_service.reset_audit_state()

    def tearDown(self):
        patch.stopall()
        app.logger.removeHandler(self.handler)
        photo_lifecycle_access_service.reset_audit_state()
        for name, (existed, value) in self.original.items():
            if existed:
                app.config[name] = value
            else:
                app.config.pop(name, None)

    @property
    def audit_messages(self):
        return [
            record.getMessage()
            for record in self.handler.records
            if "proof admission" in record.getMessage()
        ]

    def test_cohort_request_through_a_direct_photo_route_is_recorded(self):
        patch(
            "owner_routes.get_current_identity", return_value=OWNER_A
        ).start()
        patch(
            "owner_routes.photo_capture_service.get_source", return_value=None
        ).start()

        response = self.client.get(
            "/app/capture/photo/11111111-1111-1111-1111-111111111111"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.audit_messages,
            [
                "PeerSlate Photo lifecycle proof admission. "
                "access_mode=proof run_id=PS-CAPTURE-PHOTO-LIFECYCLE-001-route"
            ],
        )
        self.assertNotIn("owner-a", self.audit_messages[0])

    def test_non_cohort_request_through_a_direct_photo_route_is_not_recorded(self):
        patch(
            "owner_routes.get_current_identity", return_value=OUTSIDER
        ).start()

        response = self.client.get(
            "/app/capture/photo/11111111-1111-1111-1111-111111111111"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Photo Capture is unavailable.")
        self.assertEqual(self.audit_messages, [])


if __name__ == "__main__":
    unittest.main()
